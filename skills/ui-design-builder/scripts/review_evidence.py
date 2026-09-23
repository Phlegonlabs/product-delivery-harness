"""Source-bound machine observations and frontend-design authoring records.

These checks establish consistency, not proof that an agent observed a browser.
Human direction and final visual decisions stay in ui-design.md.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

SHA = re.compile(r"^[0-9a-f]{64}$")
IDENTITY = re.compile(r"^(?P<path>[A-Za-z0-9._/-]+) @ sha256:(?P<sha256>[0-9a-f]{64})$")
MAX_BYTES = 32 * 1024 * 1024
RESULTS = {"PASS", "FAIL", "BLOCKED", "MISSING"}


def safe_path(root, relative):
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("artifact path must be repository-relative")
    parts = PurePosixPath(relative).parts
    if PurePosixPath(relative).is_absolute() or any(p in {".", ".."} for p in relative.split("/")):
        raise ValueError("artifact path escapes repository")
    path = Path(root).resolve()
    for part in parts:
        path = path / part
        if path.is_symlink() or (path.exists() and getattr(path.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("artifact must not traverse links or reparse points")
    return path


def read_identity(root, binding):
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"}:
        raise ValueError("artifact identity requires path and sha256")
    if not isinstance(binding["sha256"], str) or not SHA.fullmatch(binding["sha256"]):
        raise ValueError("artifact identity requires lowercase SHA-256")
    path = safe_path(root, binding["path"])
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("artifact is missing or exceeds read limit")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != binding["sha256"]:
        raise ValueError("artifact identity is stale: " + binding["path"])
    return data


def timestamp(value):
    value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if value.tzinfo is None or value > datetime.now(timezone.utc):
        raise ValueError("execution time must be timezone-aware and not in the future")
    return value


def author_rows(text):
    match = re.search(r"^### Frontend Design Usage\s*\n([\s\S]*?)(?=^#{1,3} |\Z)", text, re.M)
    if not match:
        return []
    rows = []
    fenced = False
    for line in match.group(1).splitlines():
        if re.match(r"^\s*(?:```|~~~)", line):
            fenced = not fenced
            continue
        if fenced:
            continue
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and (cells[0] == "Stage" or set(cells[0]) <= {"-", ":", " "}):
            continue
        rows.append(cells)
    return rows


def author_source(text):
    match = re.search(r"^### Frontend Design Usage\s*\n([\s\S]*?)(?=^#{1,3} |\Z)", text, re.M)
    if not match:
        return None
    fenced = False
    values = []
    for line in match.group(1).splitlines():
        if re.match(r"^\s*(?:```|~~~)", line):
            fenced = not fenced
            continue
        if not fenced and line.startswith("Frontend Design source:"):
            values.append(line.partition(":")[2].strip())
    if len(values) != 1:
        return None
    parsed = IDENTITY.fullmatch(values[0])
    return parsed.groupdict() if parsed else None


def author_usage_findings(text, *, require_hifi=False):
    errors = []
    rows = author_rows(text)
    source = author_source(text)
    if source is None or not source["path"].startswith("docs/design/") or not source["path"].endswith("/SKILL.md"):
        errors.append("Frontend Design Usage requires one repository snapshot of the observed frontend-design SKILL.md")
    required = {"wireframe", "direction", "hifi"} if require_hifi else {"wireframe"}
    seen = set()
    for cells in rows:
        if len(cells) != 4:
            errors.append("Frontend Design Usage requires Stage, Skill, Artifact, Application")
            continue
        stage, skill, artifact, application = cells
        if stage in seen or (stage not in {"wireframe", "direction", "hifi"} and not re.fullmatch(r"repair-[1-9]\d*", stage)):
            errors.append("Frontend Design Usage stage is duplicate or unknown")
        seen.add(stage)
        if not re.fullmatch(r"frontend-design @ sha256:[0-9a-f]{64}", skill):
            errors.append("Frontend Design Usage requires the observed frontend-design source digest")
        elif source is not None and skill.rsplit(":", 1)[1] != source["sha256"]:
            errors.append("Frontend Design Usage skill digest differs from the observed source snapshot")
        if not IDENTITY.fullmatch(artifact):
            errors.append("Frontend Design Usage artifact must have a path and SHA-256")
        if len(application) < 20 or re.search(r"<[^>]+>|\b(?:TBD|TODO|placeholder)\b", application, re.I):
            errors.append("Frontend Design Usage must describe concrete application to this artifact")
    if not required <= seen:
        errors.append("Frontend Design Usage is missing stages: " + ", ".join(sorted(required - seen)))
    return errors


def author_artifact_findings(root, text, *, require_hifi=False):
    errors = author_usage_findings(text, require_hifi=require_hifi)
    source = author_source(text)
    if source is not None:
        try:
            payload = read_identity(root, source).decode("utf-8")
            if re.search(r"^name:\s*frontend-design\s*$", payload, re.M) is None:
                errors.append("Frontend Design source snapshot must identify frontend-design")
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append("Frontend Design source snapshot: " + str(exc))
    for cells in author_rows(text):
        if len(cells) != 4:
            continue
        match = IDENTITY.fullmatch(cells[2])
        if match:
            try:
                read_identity(root, match.groupdict())
                expected_field = {"wireframe": "Wireframe", "hifi": "Connected HiFi reference"}.get(cells[0])
                if expected_field:
                    recorded = re.search(r"^" + expected_field + r":\s*(.+)$", text, re.M)
                    if not recorded or recorded.group(1).strip() != cells[2]:
                        errors.append("Frontend Design Usage must bind the current " + cells[0] + " candidate")
            except (OSError, ValueError) as exc:
                errors.append("Frontend Design Usage: " + str(exc))
    return errors


def _case_key(row):
    if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip() for k in ("surface", "state", "target")):
        raise ValueError("observation case requires surface, state and target")
    return tuple(row[k] for k in ("surface", "state", "target"))


def observed_result(output):
    matrix = output.get("matrix")
    rows = output.get("results")
    if not isinstance(matrix, dict) or set(matrix) != {"cases"} or not isinstance(matrix["cases"], list) or not matrix["cases"]:
        raise ValueError("observation requires an explicit expected case matrix")
    if not isinstance(rows, list):
        raise ValueError("observation results must be a list")
    expected = [_case_key(row) for row in matrix["cases"]]
    actual = [_case_key(row) for row in rows]
    if len(set(expected)) != len(expected) or len(set(actual)) != len(actual):
        raise ValueError("duplicate observation cases")
    if any(set(row) != {"surface", "state", "target", "result"} or row["result"] not in RESULTS for row in rows):
        raise ValueError("observation result must be PASS, FAIL, BLOCKED or MISSING")
    if set(actual) - set(expected):
        raise ValueError("observation results contain undeclared cases")
    statuses = {row["result"] for row in rows}
    if "FAIL" in statuses:
        return "FAIL"
    if "BLOCKED" in statuses:
        return "BLOCKED"
    if set(actual) != set(expected) or "MISSING" in statuses:
        return "MISSING"
    return "PASS"


def execution_findings(root, output, receipt, subject):
    errors = []
    if not isinstance(output, dict) or output.get("schema") != "ui-output/3":
        return ["machine evidence requires ui-output/3 observations"]
    execution = output.get("execution")
    if not isinstance(execution, dict) or set(execution) != {
        "startedAt", "finishedAt", "tool", "method", "environment", "artifacts"
    }:
        return ["machine output requires exact execution identity, environment and input artifacts"]
    try:
        if timestamp(execution["startedAt"]) > timestamp(execution["finishedAt"]):
            errors.append("execution finish precedes start")
        if execution["finishedAt"] != receipt.get("executedAt"):
            errors.append("receipt time must be the recorded execution finish")
        if any(execution[key] != receipt.get(key) for key in ("tool", "method")):
            errors.append("receipt tool/method differs from the actual execution")
        environment = execution["environment"]
        if not isinstance(environment, dict) or not environment or any(
            not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip()
            for k, v in environment.items()
        ):
            errors.append("execution environment must identify observed runtime versions")
        artifacts = execution["artifacts"]
        if not isinstance(artifacts, list) or not artifacts:
            raise ValueError("execution input identities are required")
        identities = {}
        for binding in artifacts:
            payload = read_identity(root, binding)
            if binding["path"].casefold() in identities:
                raise ValueError("duplicate execution input")
            identities[binding["path"].casefold()] = (binding, payload)
        subject_bytes = read_identity(root, subject)
        if identities.get(subject["path"].casefold(), (None,))[0] != subject:
            errors.append("execution must bind the reviewed artifact at capture time")
        # A HiFi entry binds every child. Entry-only observations are insufficient.
        if subject["path"].endswith(".html"):
            matches = re.findall(r'<script\s+id=["\']ui-hifi-manifest["\']\s+type=["\']application/json["\']\s*>([\s\S]*?)</script>', subject_bytes.decode("utf-8"))
            if matches:
                manifest = json.loads(matches[0])
                for page in manifest.get("pages", []):
                    name = str(PurePosixPath(subject["path"]).parent / page["path"])
                    expected = {"path": name, "sha256": page["sha256"]}
                    if identities.get(name.casefold(), (None,))[0] != expected:
                        errors.append("execution lacks HiFi child identity: " + name)
        observed_result(output)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        errors.append(str(exc))
    return errors


def assessment_findings(root, output):
    """Qualitative conclusions retain source captures and per-case observations."""
    check = output.get("check", "")
    if not any(part in check for part in ("grading", "critique", "audit")):
        return []
    value = output.get("assessment")
    if not isinstance(value, dict) or set(value) != {"scores", "observations", "blocks"}:
        return ["review output requires scores, observations and blocks"]
    errors = []
    if not isinstance(value["blocks"], list) or value["blocks"]:
        errors.append("review output has unresolved blocks")
    scores = value["scores"]
    expected = {"W" + str(i) for i in range(1, 6)} if check.startswith("wireframe-") else {"H" + str(i) for i in range(1, 10)}
    if "grading" in check:
        if not isinstance(scores, dict) or set(scores) != expected or any(type(n) is not int or not 0 <= n <= 100 for n in scores.values()):
            errors.append("grading requires every dimension score for this exact candidate")
    elif not isinstance(scores, dict):
        errors.append("assessment scores must be an object")
    rows = value["observations"]
    try:
        if not isinstance(rows, list) or not rows:
            raise ValueError("review must retain inspected observations")
        seen = []
        execution = output.get("execution")
        artifacts = execution.get("artifacts", []) if isinstance(execution, dict) else []
        inputs = {binding.get("path", "").casefold() for binding in artifacts
                  if isinstance(binding, dict) and isinstance(binding.get("path"), str)}
        subject = output.get("subject")
        if isinstance(subject, dict) and isinstance(subject.get("path"), str):
            inputs.add(subject["path"].casefold())
        captures = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"surface", "state", "target", "finding", "evidence"}:
                raise ValueError("review observation requires case, finding and capture identities")
            seen.append(_case_key(row))
            if not isinstance(row["finding"], str) or len(row["finding"].strip()) < 12:
                raise ValueError("review observation needs a concrete finding")
            if not isinstance(row["evidence"], list) or not row["evidence"]:
                raise ValueError("review observation needs inspected capture evidence")
            for binding in row["evidence"]:
                read_identity(root, binding)
                capture = binding["path"]
                if capture.casefold() in inputs:
                    raise ValueError("review capture must be separate from the reviewed artifact and source inputs")
                if PurePosixPath(capture).suffix.casefold() not in {".png", ".jpg", ".jpeg", ".webp", ".json", ".html"}:
                    raise ValueError("review capture must be a screenshot, DOM or native observation artifact")
                if capture.casefold() in captures:
                    raise ValueError("review cases must retain distinct inspected captures")
                captures.add(capture.casefold())
        expected_cases = [_case_key(row) for row in output["matrix"]["cases"]]
        if sorted(seen) != sorted(expected_cases):
            errors.append("review observations must cover the exact case matrix")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        errors.append(str(exc))
    return errors


def build_receipt(root, output_path):
    path = safe_path(root, output_path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("observation output exceeds read limit")
    payload = path.read_bytes()
    output = json.loads(payload.decode("utf-8"))
    if not isinstance(output, dict):
        raise ValueError("observation output must be an object")
    execution = output.get("execution", {})
    if not isinstance(execution, dict):
        raise ValueError("execution must be an object")
    receipt = {
        "tool": execution.get("tool"), "method": execution.get("method"),
        "matrix": output.get("matrix"), "results": output.get("results"),
        "outputArtifact": {"path": output_path, "sha256": hashlib.sha256(payload).hexdigest()},
        "executedAt": execution.get("finishedAt"),
    }
    problems = execution_findings(root, output, receipt, output.get("subject"))
    if problems:
        raise ValueError("; ".join(problems))
    result = observed_result(output)
    if result == "PASS" and assessment_findings(root, output):
        result = "BLOCKED"
    return {"schema": "ui-evidence/3", "check": output.get("check"), "result": result,
            "reviewedArtifact": output.get("subject"), "receipt": receipt}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-artifact", required=True)
    parser.add_argument("--receipt-out", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        root = args.repo_root.resolve()
        receipt = build_receipt(root, args.output_artifact)
        destination = safe_path(root, args.receipt_out)
        if destination == safe_path(root, args.output_artifact):
            raise ValueError("receipt must not overwrite its observation source")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w" if args.overwrite else "x", encoding="utf-8", newline="\n") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(json.dumps({"result": receipt["result"], "receipt": args.receipt_out}))
        return 0 if receipt["result"] == "PASS" else 1
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"result": "invalid", "error": str(exc)}))
        return 2




def score_findings(output, recorded):
    assessment = output.get("assessment")
    scores = assessment.get("scores") if isinstance(assessment, dict) else None
    if not isinstance(scores, dict):
        return ["grading requires actual dimension scores"]
    prefix = "W" if str(output.get("check", "")).startswith("wireframe-") else "H"
    count = 5 if prefix == "W" else 9
    if set(scores) != {prefix + str(n) for n in range(1, count + 1)} or any(
        type(value) is not int or not 0 <= value <= 100 for value in scores.values()
    ):
        return ["grading requires every actual dimension score"]
    family = "Wireframe" if prefix == "W" else "HiFi"
    expected = {family + " score": round(sum(scores.values()) / count),
                family + " lowest dimension": min(scores.values())}
    expected.update({key + " score": scores[key] for key in
                    (["W5"] if prefix == "W" else ["H2", "H4", "H5", "H7", "H8", "H9"])})
    return [] if expected == recorded else ["recorded grades differ from the actual assessment scores"]


if __name__ == "__main__":
    raise SystemExit(main())

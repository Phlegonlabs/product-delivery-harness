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
import sys

SHA = re.compile(r"^[0-9a-f]{64}$")
IDENTITY = re.compile(r"^(?P<path>[A-Za-z0-9._/-]+) @ sha256:(?P<sha256>[0-9a-f]{64})$")
MAX_BYTES = 32 * 1024 * 1024
RESULTS = {"PASS", "FAIL", "BLOCKED", "MISSING"}
# Shared with check_ui_design_contract so both read the same manifest tags.
HIFI_MANIFEST_RE = re.compile(
    r'<script\s+id=["\']ui-hifi-manifest["\']\s+type=["\']application/json["\']\s*>'
    r"(?P<data>[\s\S]*?)</script>",
    re.IGNORECASE,
)


def line_ending_hint(path: str) -> str:
    """Repair hint for bytes that differ from a pinned hash only by CRLF/LF conversion."""
    return (
        f"`{path}` differs only by line-ending conversion; check "
        f"`git check-attr text eol filter -- {path}` against "
        "delivery-harness/references/gitattributes-contract.md#converted-files; "
        "do not regenerate or re-pin"
    )


def line_ending_note(data: bytes, expected_sha256: object, path: str) -> str:
    """`; <hint>` when the bytes match the hash only after CRLF/LF conversion, else ''."""
    if not isinstance(expected_sha256, str):
        return ""
    lf = data.replace(b"\r\n", b"\n")
    for form in (lf, lf.replace(b"\n", b"\r\n")):
        if form != data and hashlib.sha256(form).hexdigest() == expected_sha256:
            return "; " + line_ending_hint(path)
    return ""


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
        raise ValueError("artifact identity is stale: " + binding["path"]
                         + line_ending_note(data, binding["sha256"], binding["path"]))
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


def author_usage_findings(text, *, require_hifi=False, require_wireframe=True):
    errors = []
    rows = author_rows(text)
    source = author_source(text)
    if source is None or not source["path"].startswith("docs/design/") or not source["path"].endswith("/SKILL.md"):
        errors.append("Frontend Design Usage requires one repository snapshot of the observed frontend-design SKILL.md")
    required = ({"wireframe"} if require_wireframe else set()) | ({"direction", "hifi"} if require_hifi else set())
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


def author_artifact_findings(root, text, *, require_hifi=False, require_wireframe=True):
    errors = author_usage_findings(text, require_hifi=require_hifi, require_wireframe=require_wireframe)
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
            matches = HIFI_MANIFEST_RE.findall(subject_bytes.decode("utf-8"))
            check = str(output.get("check", ""))
            if not matches and (check.startswith("hifi-") or check == "motion-preview"):
                errors.append("HiFi evidence subject has no ui-hifi/2 manifest")
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


def _end_targets(cases):
    """{surface: (smallest, largest) target}: viewport widths by value, size classes in their listed order."""
    targets = {}
    for surface, _, target in cases:
        targets.setdefault(surface, [])
        if target not in targets[surface]:
            targets[surface].append(target)

    def width(target):
        try:
            return float(target)
        except ValueError:
            return None
    ordered = {surface: (sorted(listed, key=float) if all(width(t) is not None for t in listed) else listed)
               for surface, listed in targets.items()}
    return {surface: (listed[0], listed[-1]) for surface, listed in ordered.items()}


def assessment_findings(root, output, *, allow_blocks=False):
    """Qualitative conclusions retain source captures and per-case observations."""
    check = output.get("check", "")
    if not any(part in check for part in ("grading", "critique", "audit")):
        return []
    value = output.get("assessment")
    if not isinstance(value, dict) or set(value) != {"scores", "observations", "blocks"}:
        return ["review output requires scores, observations and blocks"]
    errors = []
    if not isinstance(value["blocks"], list):
        errors.append("review output has unresolved blocks")
    elif value["blocks"] and not allow_blocks:
        errors.append("review output has unresolved blocks")
    elif any(not isinstance(block, str) or not block.strip() for block in value["blocks"]):
        errors.append("review blocks must contain concrete findings")
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
        # The author's matrix run covers every case by machine; a reviewer inspects a set by eye
        # (ui-grading-rubric.md Browser Inspection Procedure). It includes each surface at its smallest target and
        # the axis sample, which also takes the largest target.
        matrix_cases = [_case_key(row) for row in output["matrix"]["cases"]]
        if not set(seen) <= set(matrix_cases):
            errors.append("review observations must name cases of the reviewed matrix")
        for surface, ends in sorted(_end_targets(matrix_cases).items()):
            for label, target in dict.fromkeys(zip(("smallest", "largest"), ends)):
                if not any(case[0] == surface and case[2] == target for case in seen):
                    errors.append(f"review observations must inspect {surface} at its {label} target {target}")
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


# --- Readiness: the author's capture is complete before any review is spent ------------
A11Y_DISPOSITIONS = "a11y-dispositions.json"
DISPOSITION_KEYS = {"measure", "selector", "reason", "surface", "state", "target", "axis"}
LEDGER_STATUSES = {"open", "closed", "advisory", "block"}
RERUN = "rerun hifi_matrix_capture.py on the frozen bytes and never edit its output"


def _json_object(root, relative, label):
    path = safe_path(root, relative)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError(f"{label} is missing or exceeds read limit: {relative}")
    value = json.loads(path.read_bytes().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object: {relative}")
    return value


def _case_name(row):
    name = f"{row.get('surface')}/{row.get('state')}/{row.get('target')}"
    axis = row.get("axis")
    return name + (f" under {axis}" if axis and axis != "base" else "")


def _where(names):
    return ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")


# Reasons a hang or the driver gives, not the page: one rerun, then the owner decides (rubric Readiness gate).
# They cover every reason hifi_matrix_capture.py writes for a DriverTimeout or DriverError and every BLOCKED reason;
# "page did not open" is also the recovery reopen and each row of a page that never opened.
TOOL_LIMIT_MARKERS = ("restart limit", "could not restart", "timed out after", "driver error:", "could not be set up",
                      "page did not open", "screenshot failed:")
TOOL_LIMIT_FIX = ("a hang or a driver failure: fix what hangs and rerun the driver once; if the row fails the same way "
                  "again, it is a tool limit and the parent records the candidate blocked for the owner")


def _failed_rows(rows, name):
    """One problem per result and reason set, so one page-level cause on 300 cases is one line."""
    groups = {}
    for row in rows:
        if isinstance(row, dict) and row.get("result") != "PASS":
            key = (row.get("result"), tuple(str(reason) for reason in row.get("reasons") or ()))
            groups.setdefault(key, []).append(name(row))
    return [(f"{result}: {_where(names)} ({'; '.join(reasons) or 'no reason recorded'})",
             TOOL_LIMIT_FIX if any(marker in reason for reason in reasons for marker in TOOL_LIMIT_MARKERS)
             else "fix it and rerun the driver; the author's last capture is a clean run" if result == "FAIL"
             else "rerun the driver; this was not observed")
            for (result, reasons), names in groups.items()]


def _dispositions(root, relative):
    """The author's reasons for measured accessibility failures it keeps; no file means none."""
    if not safe_path(root, relative).is_file():
        return []
    data = _json_object(root, relative, "a11y dispositions")
    rows = data.get("dispositions")
    if set(data) != {"schema", "dispositions"} or data["schema"] != "a11y-dispositions/1" or not isinstance(rows, list):
        raise ValueError(f'{relative} must be {{"schema": "a11y-dispositions/1", "dispositions": [...]}}')
    for row in rows:
        if (not isinstance(row, dict) or not {"measure", "selector", "reason"} <= set(row) <= DISPOSITION_KEYS
                or any(not isinstance(value, str) or not value.strip() for value in row.values())):
            raise ValueError(f"{relative}: a disposition names measure, selector and a reason, "
                             "and may narrow by surface, state, target and axis")
    return rows


def _a11y_problems(root, a11y, dispositions_path):
    dispositions = _dispositions(root, dispositions_path)
    groups = {}
    for row in a11y.get("findings") or []:
        if not isinstance(row, dict) or row.get("level") != "fail":
            continue
        if any(all(row.get(key) == value for key, value in d.items() if key != "reason") for d in dispositions):
            continue
        groups.setdefault((row.get("measure"), row.get("selector")), []).append(_case_name(row))
    return [(f"{measure} fails on {selector} at {_where(names)} with no disposition",
             f"fix it, or record the reason in {dispositions_path}")
            for (measure, selector), names in groups.items()]


def _screenshot(record):
    return "fresh" if record.get("capture") else ("carried" if record.get("carriedFrom") else "none")


A11Y_LEVELS = ("fail", "note", "unmeasured")
CARRIED_KEYS = {"result", "pageSha256", "capture", "sourceOutput"}


def _is_identity(value):
    return (isinstance(value, dict) and set(value) == {"path", "sha256"} and isinstance(value["path"], str)
            and isinstance(value["sha256"], str) and SHA.fullmatch(value["sha256"]) is not None)


def _file_problem(root, bound, binding, label):
    """Why a screenshot binding is not a file inside the repository that hashes to it and the output binds, or None."""
    if not _is_identity(binding):
        return f"{label} is not a path and sha256"
    try:
        path = safe_path(root, binding["path"])
    except ValueError:
        return f"{label} lies outside the repository or crosses a link"
    if not path.is_file():
        return f"{label} file is missing"
    if hashlib.sha256(path.read_bytes()).hexdigest() != binding["sha256"]:
        return f"{label} bytes differ from its sha256"
    if bound.get(binding["path"]) != binding["sha256"]:
        return f"{label} is not bound in the output's execution artifacts"
    return None


def _record_problems(root, bound, record, fresh_path, recapture):
    """What in one case record's screenshot fields the driver does not write. ``fresh_path`` is where this run
    saves the case's screenshot (hifi_matrix_capture.capture_name); a carried capture has the same file name."""
    capture, carried = record.get("capture"), record.get("carriedFrom")
    found = []
    if capture is not None and carried is not None and not recapture:
        found.append("names both a capture and carriedFrom, without --recapture-carried")
    if capture is not None:
        found.append(_file_problem(root, bound, capture, "capture")
                     or (None if capture["path"] == fresh_path else "capture is not this run's screenshot"))
    if carried is not None:
        if (not isinstance(carried, dict) or set(carried) != CARRIED_KEYS or carried["result"] != "PASS"
                or not isinstance(carried["pageSha256"], str) or not SHA.fullmatch(carried["pageSha256"])
                or not _is_identity(carried["sourceOutput"])):
            found.append("carriedFrom is not the record the driver writes")
        else:
            found.append(_file_problem(root, bound, carried["capture"], "carried capture")
                         or (None if PurePosixPath(carried["capture"]["path"]).name == PurePosixPath(fresh_path).name
                             else "carried capture is not this case's screenshot"))
    return [phrase for phrase in found if phrase]


def _a11y_written(a11y):
    """True when ``a11y`` has the structure --measure-a11y writes and its summary counts its findings."""
    import hifi_matrix_capture as matrix
    if not isinstance(a11y, dict) or set(a11y) != {"summary", "notRun", "incomplete", "findings"}:
        return False
    summary = a11y["summary"]
    if (not isinstance(summary, dict) or set(summary) != set(matrix.A11Y_MEASURES)
            or any(not isinstance(a11y[key], list) for key in ("notRun", "incomplete", "findings"))):
        return False
    counts = {(name, level): 0 for name in matrix.A11Y_MEASURES for level in A11Y_LEVELS}
    for row in a11y["findings"]:
        if (not isinstance(row, dict) or (row.get("measure"), row.get("level")) not in counts
                or any(not isinstance(row.get(key), str) for key in ("surface", "state", "target", "axis"))):
            return False
        counts[(row["measure"], row["level"])] += 1
    return all(isinstance(summary[name], dict) and set(summary[name]) == {"checked", *A11Y_LEVELS}
               and all(type(value) is int and value >= 0 for value in summary[name].values())
               and all(summary[name][level] == counts[(name, level)] for level in A11Y_LEVELS)
               for name in matrix.A11Y_MEASURES)


def _sidecar_problems(root, output_rel, output, sidecar_rel, sidecar, bound):
    """Where a hash-bound sidecar disagrees with its output or holds a case record the driver does not write."""
    import hifi_matrix_capture as matrix
    problems = []
    execution = output.get("execution") if isinstance(output.get("execution"), dict) else {}
    run = sidecar.get("run") if isinstance(sidecar.get("run"), dict) else {}
    if ("subject" in sidecar and sidecar["subject"] != output.get("subject")) or any(
            run[key] != execution.get(key) for key in ("startedAt", "finishedAt") if key in run):
        problems.append((f"{sidecar_rel} names another subject or run than {output_rel}", RERUN))
    matrix_keys = [(c.get("surface"), c.get("state"), c.get("target"))
                   for c in (output.get("matrix") or {}).get("cases") or [] if isinstance(c, dict)]
    rows = sidecar.get("cases") if isinstance(sidecar.get("cases"), list) else []
    keys = [(r.get("surface"), r.get("state"), r.get("target")) if isinstance(r, dict) else None for r in rows]
    missing = [key for key in matrix_keys if key not in keys]
    if missing:
        problems.append((f"{sidecar_rel} has no case record for {len(missing)} of the output's cases, "
                         f"first {'/'.join(map(str, missing[0]))}", RERUN))
    extra = [key for index, key in enumerate(keys) if key not in matrix_keys or key in keys[:index]]
    if extra:
        problems.append((f"{sidecar_rel} has {len(extra)} case records that are not one each of the output's cases", RERUN))
    results = {(r.get("surface"), r.get("state"), r.get("target")): r.get("result")
               for r in output.get("results") or [] if isinstance(r, dict)}
    folder, recapture = PurePosixPath(output_rel).parent, run.get("recaptureCarried") is True
    groups = {}
    for record, key in zip(rows, keys):
        if key is None or key not in matrix_keys:
            continue
        fresh_path = str(folder / matrix.capture_name(matrix.Case(key[0], "", key[1], key[2])))
        found = _record_problems(root, bound, record, fresh_path, recapture)
        if record.get("result") != results.get(key):
            found.append("result differs from the output's")
        for phrase in found:
            groups.setdefault(phrase, []).append("/".join(key))
    return problems + [(f"{sidecar_rel} {_where(names)}: {phrase}", RERUN) for phrase, names in groups.items()]


def capture_problems(root, package_rel, package, output_rel):
    """(problems, shots) for one hifi_matrix_capture.py output against the frozen package bytes.

    ``shots`` maps each observed case to `fresh`, `carried` or `none`: whether this run
    took its screenshot. It is None when the capture is not of these bytes."""
    import hifi_matrix_capture as matrix     # imported here: the driver imports this module
    output = _json_object(root, output_rel, "capture")
    if output.get("schema") != "ui-output/3" or output.get("check") != matrix.CHECK:
        raise ValueError(f"{output_rel} is not a ui-output.json written by hifi_matrix_capture.py")
    index = f"{package_rel}/index.html"
    subject = output.get("subject") if isinstance(output.get("subject"), dict) else {}
    if subject.get("path") != index:
        return [(f"{output_rel} observed {subject.get('path')}, not the frozen package {index}",
                 "run the driver on the frozen package")], None
    execution = output.get("execution") if isinstance(output.get("execution"), dict) else {}
    artifacts = [b for b in execution.get("artifacts") or [] if isinstance(b, dict)]
    bound = {b.get("path"): b.get("sha256") for b in artifacts}
    bound[index] = subject.get("sha256")
    stale = []
    for name, digest in package.sha.items():
        seen = bound.get(f"{package_rel}/{name}")
        if seen != digest:
            stale.append((f"{output_rel} observed {name} at {f'sha256:{seen[:12]}' if isinstance(seen, str) else 'no hash'}, "
                          f"the frozen package has sha256:{digest[:12]}", RERUN))
    if stale:
        return stale, None
    binding = next((b for b in artifacts if str(b.get("path", "")).rsplit("/", 1)[-1] == matrix.SIDECAR_NAME), None)
    try:
        if binding is None:
            raise ValueError(f"it binds no {matrix.SIDECAR_NAME}")
        sidecar = json.loads(read_identity(root, binding).decode("utf-8"))
        if not isinstance(sidecar, dict) or sidecar.get("schema") != matrix.SIDECAR_SCHEMA:
            raise ValueError(f"{binding['path']} is not {matrix.SIDECAR_SCHEMA}")
    except (ValueError, UnicodeError) as error:
        return [(f"{output_rel}: {error}", RERUN)], None

    problems = [(f"{output_rel} fails the driver's own output check: {finding}", "fix what it names and rerun the driver")
                for finding in matrix.validate_output(root, safe_path(root, output_rel), output)]
    integrity = _sidecar_problems(root, output_rel, output, binding["path"], sidecar, bound)
    if integrity:       # its records cannot be trusted, so nothing more is read from them
        return problems + integrity, None
    run = sidecar.get("run") if isinstance(sidecar.get("run"), dict) else {}
    observed = {(c.get("surface"), c.get("state"), c.get("target"))
                for c in (output.get("matrix") or {}).get("cases") or [] if isinstance(c, dict)}
    derived = run.get("derived") if isinstance(run.get("derived"), dict) else None
    missing = [case.key for case in matrix.expand_matrix(package, None, derived) if case.key not in observed]
    if missing:
        problems.append((f"{output_rel} lacks {len(missing)} of the package's cases, first {'/'.join(missing[0])}",
                         "rerun the driver on the whole package, without --only"))
    records = {(r.get("surface"), r.get("state"), r.get("target")): r for r in sidecar.get("cases") or [] if isinstance(r, dict)}
    results = [dict(row, reasons=records.get((row.get("surface"), row.get("state"), row.get("target")), {}).get("reasons"))
               for row in output.get("results") or [] if isinstance(row, dict)]
    problems += _failed_rows(results, _case_name)
    problems += _failed_rows(sidecar.get("axes") or [], _case_name)
    problems += _failed_rows(sidecar.get("interactions") or [],
                             lambda r: f"interaction {r.get('id')} by {r.get('trigger')} at {r.get('target')}")
    problems += _failed_rows(sidecar.get("reviewer") or [], lambda r: f"reviewer pass on {r.get('page')}")
    sweep = run.get("intermediate")
    if isinstance(sweep, dict) and (sweep.get("fail") or sweep.get("interactionsFail") or sweep.get("findings")):
        problems.append((f"{sweep.get('output')}: the intermediate-width sweep has {sweep.get('fail')} failed cases, "
                         f"{sweep.get('interactionsFail')} failed interactions and {len(sweep.get('findings') or [])} "
                         "coverage findings", "fix them and rerun the driver"))
    a11y = sidecar.get("a11y")
    if a11y is None:
        problems.append((f"{output_rel} has no a11y measurements", "rerun the driver with --measure-a11y"))
    elif not _a11y_written(a11y):
        problems.append((f"{binding['path']}: its a11y object is not the one --measure-a11y writes", RERUN))
    else:
        problems += _a11y_problems(root, a11y, str(PurePosixPath(binding["path"]).parent / A11Y_DISPOSITIONS))
    return problems, {key: _screenshot(record) for key, record in records.items()}


def ledger_problems(root, ledger_rel, shots):
    """Each open or block ledger row needs a screenshot of every acceptance case taken on the repaired bytes."""
    ledger = _json_object(root, ledger_rel, "defect ledger")
    families = ledger.get("families")
    if ledger.get("schema") != "ui-defect-ledger/1" or not isinstance(families, list):
        raise ValueError(f"{ledger_rel} is not a ui-defect-ledger/1 file with families")
    problems = []
    for family in families:
        if (not isinstance(family, dict) or not isinstance(family.get("id"), str)
                or family.get("status") not in LEDGER_STATUSES or not isinstance(family.get("acceptanceCases"), list)):
            raise ValueError(f"{ledger_rel}: every family needs an id, a status and acceptanceCases")
        if family["status"] not in {"open", "block"}:
            continue
        if not family["acceptanceCases"]:
            problems.append((f"ledger row {family['id']} names no acceptance case, so it has no after-capture",
                             "the parent adds its acceptance cases to the ledger"))
        for case in family["acceptanceCases"]:
            key = _case_key(case)
            name = "/".join(key)
            if key not in shots:
                problems.append((f"ledger row {family['id']} case {name} is not in the capture",
                                 "rerun the driver on the whole package"))
            elif shots[key] == "carried":
                problems.append((f"ledger row {family['id']} has no after-capture for {name}: the case was carried, "
                                 "so its render did not change",
                                 "check that the repair reached it, or rerun the driver with --recapture-carried"))
            elif shots[key] == "none":
                problems.append((f"ledger row {family['id']} has no after-capture for {name}",
                                 "rerun the driver until the case is observed"))
    return problems


def review_readiness(root, package_rel, capture_rels, ledger_rel=None):
    """(problems, candidate): the frozen candidate is READY for review when problems is empty."""
    import hifi_matrix_capture as matrix
    try:
        package = matrix.read_package(safe_path(root, package_rel))
    except matrix.UsageError as error:
        raise ValueError(str(error)) from None
    package_rel = str(PurePosixPath(package_rel))
    rank = {"none": 0, "carried": 1, "fresh": 2}
    problems, shots, comparable = [], {}, True
    for capture_rel in capture_rels:
        found, cases = capture_problems(root, package_rel, package, capture_rel)
        problems += found
        if cases is None:
            comparable = False
            continue
        for key, shot in cases.items():
            shots[key] = max(shots.get(key, "none"), shot, key=rank.get)
    if ledger_rel is not None:
        found = ledger_problems(root, ledger_rel, shots)    # read even when unused: a malformed ledger is invalid input
        if comparable:
            problems += found
    return list(dict.fromkeys(problems)), {"path": f"{package_rel}/index.html", "sha256": package.sha["index.html"]}


def ready_main(argv):
    parser = argparse.ArgumentParser(
        prog="review_evidence.py ready",
        description="Before the wave or the re-review: is the author's capture of the frozen package complete?")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--package", required=True, help="frozen ui-hifi/2 package folder, repository-relative")
    parser.add_argument("--capture", action="append", required=True,
                        help="the author's ui-output.json from hifi_matrix_capture.py; repeat for each theme run")
    parser.add_argument("--ledger", help="defect-ledger.json, before the re-review and the fix exchange")
    args = parser.parse_args(argv)
    try:
        problems, candidate = review_readiness(args.repo_root.resolve(), args.package, args.capture, args.ledger)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"INVALID: {exc}")
        return 2
    if not problems:
        print(f"READY {candidate['path']} @ sha256:{candidate['sha256']}")
        return 0
    print(f"NOT READY: {len(problems)} problems; the candidate returns to its author and no review is spent")
    for problem, fix in problems:
        print(f"- {problem}. Fix: {fix}.")
    return 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["ready"]:
        return ready_main(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-artifact", required=True)
    parser.add_argument("--receipt-out", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
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
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())

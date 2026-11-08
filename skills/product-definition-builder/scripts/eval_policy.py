#!/usr/bin/env python3
"""PRD-owned evaluation policy. No runner execution or approval mutation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

from markdown_contract import active_text, exact_marker_lines, is_human_owner
from contract_utils import machine_block_span

START = "<!-- eval-policy:start -->"
END = "<!-- eval-policy:end -->"
MAX_BYTES = 16 * 1024 * 1024
HASH = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,79}\Z")
# A feature-file scenario id: `<TEST-ID>/<slug of the scenario name>`.
FEATURE_SCENARIO_ID = re.compile(r"(TEST-\d{3,})/[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class PolicyError(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError("duplicate JSON key")
        result[key] = value
    return result


def json_object(raw):
    try:
        obj = json.loads(raw, object_pairs_hook=unique_object,
                         parse_constant=lambda _: fail("non-finite JSON number"))
    except PolicyError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise PolicyError("invalid UTF-8 JSON object") from exc
    if not isinstance(obj, dict):
        raise PolicyError("expected JSON object")
    return obj


def fail(message):
    raise PolicyError(message)


def keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        fail(f"{label}: exact fields required")


def text(value, label):
    if (not isinstance(value, str) or not value.strip() or len(value) > 8000
            or re.search(r"(?i)\b(?:TODO|TBD|placeholder)\b|<[^>]+>|\[[^]]+\]", value)):
        fail(f"{label}: concrete text required")


def data_text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_BYTES:
        fail(f"{label}: nonempty bounded text required")


def integer(value, label, minimum=0, maximum=10**12):
    if type(value) is not int or not minimum <= value <= maximum:
        fail(f"{label}: integer out of range")


def identifier(value, label):
    if not isinstance(value, str) or not ID.fullmatch(value):
        fail(f"{label}: invalid identifier")


def safe_relative(value):
    if (not isinstance(value, str) or "\\" in value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        fail("artifact path must be POSIX repository-relative")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or path.as_posix() != value or ".." in path.parts:
        fail("artifact path must be normalized repository-relative")
    for part in path.parts:
        name = part.casefold()
        if (":" in part or name.rstrip(" .") != name or name in {".git", ".ssh", ".env"}
                or name.startswith(".env.") or name in {"credentials.json", "secrets.json", "id_rsa"}
                or name.endswith((".pem", ".key", ".p12", ".pfx"))
                or re.search(r"secret|password|credential|token|cookie|storage[-_]state", name)):
            fail("unsafe or secret-like artifact path")
    return value


def artifact(value, label):
    keys(value, "path sha256", label)
    safe_relative(value["path"])
    if not isinstance(value["sha256"], str) or not HASH.fullmatch(value["sha256"]):
        fail(f"{label}: lowercase SHA-256 required")


def read_artifact(root, relative):
    """Standalone Product IO; Harness uses its acceptance IO for the same inputs."""
    root = Path(root).resolve(strict=True)
    safe_relative(relative)
    path = root
    for part in PurePosixPath(relative).parts:
        path /= part
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            fail("artifact path traverses a link")
    if not path.resolve().is_relative_to(root):
        fail("artifact escapes repository")
    before = path.stat()
    if not path.is_file() or not 0 < before.st_size <= MAX_BYTES:
        fail("artifact must be a nonempty bounded regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        fail("artifact changed during read")
    if len(raw) != before.st_size or len(raw) > MAX_BYTES:
        fail("artifact size changed during read")
    return raw


def policy_digest(policy):
    return hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def parse_eval_policy(prd_text, *, required=False):
    starts, ends = exact_marker_lines(prd_text, START), exact_marker_lines(prd_text, END)
    if not starts and not ends:
        if required:
            fail("missing active eval-policy/1 declaration")
        return None
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        fail("eval policy requires one ordered active marker pair")
    approval_starts = exact_marker_lines(prd_text, "<!-- product-definition-approval:start -->")
    approval_ends = exact_marker_lines(prd_text, "<!-- product-definition-approval:end -->")
    if approval_starts or approval_ends:
        if (len(approval_starts) != 1 or len(approval_ends) != 1
                or approval_starts[0] >= approval_ends[0]):
            fail("eval policy requires an ordered active approval block when present")
        if starts[0] <= approval_ends[0] and approval_starts[0] <= ends[0]:
            fail("eval policy must not overlap the excluded approval block")
    normalized = prd_text.replace("\r\n", "\n")
    # Marker line numbers belong to raw splitlines. Map their raw offsets into
    # the once-normalized digest text; repeated CR bytes must not shift the range.
    lines = prd_text.splitlines(keepends=True)
    raw_start, raw_end = sum(map(len, lines[:starts[0] - 1])), sum(map(len, lines[:ends[0]]))
    policy_start = len(prd_text[:raw_start].replace("\r\n", "\n"))
    policy_end = len(prd_text[:raw_end].replace("\r\n", "\n"))
    excluded = machine_block_span(normalized, "<!-- product-definition-approval:start -->",
                                  "<!-- product-definition-approval:end -->")
    if excluded and policy_start < excluded[1] and excluded[0] < policy_end:
        fail("eval policy overlaps the raw approval digest exclusion")
    prefix = active_text("\n".join(prd_text.splitlines()[:starts[0] - 1]))
    headings = re.findall(r"^## .+$", prefix, re.M)
    if not headings or headings[-1] != "## AI and Automation":
        fail("eval policy must be in the AI and Automation section")
    body_start = sum(map(len, lines[:starts[0]]))
    body_end = sum(map(len, lines[:ends[0] - 1]))
    # Python's splitlines/strip recognize characters that do not delimit lines
    # or end HTML blocks in CommonMark. Keep them inside JSON strings only.
    before_body = prd_text[:body_start]
    if any(char in before_body for char in "\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029"):
        fail("eval policy prefix requires Markdown line endings")
    for line in before_body.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line and not line.strip() and line.strip(" \t"):
            fail("eval policy prefix requires Markdown blank lines")
    body = prd_text[body_start:body_end].replace("\r\n", "\n").replace("\r", "\n").strip(" \t\n")
    if not (body.startswith("```json\n") and body.endswith("\n```")):
        fail("eval policy body requires a json fence for visible review")
    return json_object(body[8:-4])


def rate(value, label):
    keys(value, "numerator denominator", label)
    integer(value["denominator"], label, 1)
    integer(value["numerator"], label, 0, value["denominator"])


def scenario(value, label):
    keys(value, "test_id scenario_id report", label)
    if not isinstance(value["test_id"], str) or not re.fullmatch(r"TEST-\d{3,}", value["test_id"]):
        fail(f"{label}: TEST ID required")
    feature = FEATURE_SCENARIO_ID.fullmatch(value["scenario_id"]) if isinstance(value["scenario_id"], str) else None
    if feature is None:
        identifier(value["scenario_id"], label)
    elif feature.group(1) != value["test_id"]:
        fail(f"{label}: a feature scenario id must start with its test_id")
    safe_relative(value["report"])


def validate_policy_shape(policy):
    if not isinstance(policy, dict):
        fail("policy must be an object")
    base = "schema applicability reason owner"
    required = ("quality handoff dataset rubric grader subject metric trials_per_case minimum_rate "
                "slices critical_rule retry_policy freshness limits delivery")
    keys(policy, base + (" " + required if policy.get("applicability") == "required" else ""), "policy")
    if policy["schema"] != "eval-policy/1" or policy["applicability"] not in {"required", "not_required"}:
        fail("unsupported evaluation schema or applicability")
    text(policy["reason"], "reason")
    if not isinstance(policy["owner"], str) or not is_human_owner(policy["owner"]):
        fail("evaluation decision needs a human owner")
    if policy["applicability"] == "not_required":
        return
    for name in ("quality", "handoff"):
        scenario(policy[name], name)
    if (policy["quality"]["test_id"] == policy["handoff"]["test_id"]
            or policy["quality"]["report"] == policy["handoff"]["report"]):
        fail("quality and handoff need distinct required TESTs and reports")
    for name in ("dataset", "rubric", "grader", "subject"):
        artifact(policy[name], name)
    if policy["metric"] not in {"case_all_trials", "trial_pass_rate"}:
        fail("unsupported eval metric")
    integer(policy["trials_per_case"], "trials_per_case", 1, 1000)
    rate(policy["minimum_rate"], "minimum_rate")
    if policy["critical_rule"] != "all_trials_pass" or policy["retry_policy"] != "none":
        fail("v1 requires all_trials_pass critical rule and no retries")
    if not isinstance(policy["slices"], list):
        fail("slices must be a list")
    seen = set()
    for row in policy["slices"]:
        keys(row, "id minimum_cases minimum_rate", "slice")
        identifier(row["id"], "slice")
        if row["id"] in seen:
            fail("duplicate slice")
        seen.add(row["id"])
        integer(row["minimum_cases"], "minimum_cases", 1)
        rate(row["minimum_rate"], "slice rate")
    keys(policy["freshness"], "max_age_seconds dependencies", "freshness")
    integer(policy["freshness"]["max_age_seconds"], "max_age_seconds", 1)
    dependencies = policy["freshness"]["dependencies"]
    if not isinstance(dependencies, dict):
        fail("dependencies must map IDs to expected identities")
    for name, identity in dependencies.items():
        identifier(name, "dependency")
        text(identity, "dependency identity")
    keys(policy["limits"], "trial_timeout_ms run_timeout_ms max_calls max_cost_microunits currency", "limits")
    for name in ("trial_timeout_ms", "run_timeout_ms", "max_calls", "max_cost_microunits"):
        integer(policy["limits"][name], name, 1 if name.endswith("timeout_ms") else 0)
    if not isinstance(policy["limits"]["currency"], str) or not re.fullmatch(r"[A-Z]{3}", policy["limits"]["currency"]):
        fail("currency must be an explicit three-letter code")
    keys(policy["delivery"], "runner grader lockfile runbook setup_argv full_argv", "delivery")
    for name in ("runner", "grader", "lockfile", "runbook"):
        safe_relative(policy["delivery"][name])
    for name in ("setup_argv", "full_argv"):
        argv = policy["delivery"][name]
        if not isinstance(argv, list) or not argv:
            fail("setup/full argv must be nonempty arrays")
        for arg in argv:
            data_text(arg, "command argument")
    if policy["delivery"]["runner"] not in policy["delivery"]["full_argv"]:
        fail("full argv must invoke the delivered runner")


def parse_inputs(policy, reader):
    """Verify approved bytes and return dataset, rubric, grader and subject."""
    values = {}
    for name in ("dataset", "rubric", "grader", "subject"):
        ref = policy[name]
        raw = reader(ref["path"])
        if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
            fail(f"{name}: bytes differ from approved policy")
        if name == "dataset":
            try:
                lines = raw.decode("utf-8").split("\n")
            except UnicodeError as exc:
                raise PolicyError("dataset must be UTF-8 JSONL") from exc
            values[name] = [json_object(line) for line in lines if line.strip()]
        else:
            values[name] = json_object(raw)
    cases = values["dataset"]
    if not cases or len(cases) > 100000:
        fail("dataset requires 1..100000 predeclared cases")
    if len(cases) * policy["trials_per_case"] > 100000:
        fail("v1 limits the planned population to 100000 trials")
    declared = {row["id"] for row in policy["slices"]}
    slice_counts = dict.fromkeys(declared, 0)
    seen = set()
    for case in cases:
        keys(case, "case_id split slices critical input expected", "case")
        identifier(case["case_id"], "case_id")
        if case["case_id"] in seen:
            fail("duplicate case_id")
        seen.add(case["case_id"])
        if case["split"] not in {"development", "heldout"} or type(case["critical"]) is not bool:
            fail("case split or critical flag invalid")
        if (not isinstance(case["slices"], list) or any(not isinstance(x, str) for x in case["slices"])
                or len(set(case["slices"])) != len(case["slices"]) or not set(case["slices"]) <= declared):
            fail("case slices must be unique declared IDs")
        data_text(case["input"], "case input")
        data_text(case["expected"], "case expected")
        for slice_id in case["slices"]:
            slice_counts[slice_id] += 1
    for row in policy["slices"]:
        if slice_counts[row["id"]] < row["minimum_cases"]:
            fail("slice has fewer cases than approved minimum")
    rubric = values["rubric"]
    keys(rubric, "schema dimensions prohibited_assertions", "rubric")
    if rubric["schema"] != "eval-rubric/1" or not isinstance(rubric["dimensions"], list) or not rubric["dimensions"]:
        fail("rubric requires dimensions")
    seen = set()
    for dimension in rubric["dimensions"]:
        keys(dimension, "id minimum maximum passing_score anchors", "dimension")
        identifier(dimension["id"], "dimension")
        if dimension["id"] in seen:
            fail("duplicate rubric dimension")
        seen.add(dimension["id"])
        integer(dimension["minimum"], "minimum", 0, 100)
        integer(dimension["maximum"], "maximum", dimension["minimum"], 100)
        integer(dimension["passing_score"], "passing_score", dimension["minimum"], dimension["maximum"])
        anchors = dimension["anchors"]
        if not isinstance(anchors, dict) or set(anchors) != {str(i) for i in range(dimension["minimum"], dimension["maximum"] + 1)}:
            fail("rubric requires an anchor for every integer score")
        for anchor in anchors.values():
            data_text(anchor, "rubric anchor")
    assertions = rubric["prohibited_assertions"]
    if not isinstance(assertions, dict) or not assertions:
        fail("rubric requires prohibited-outcome assertions")
    for name, signal in assertions.items():
        identifier(name, "assertion")
        data_text(signal, "prohibited assertion")
    grader = values["grader"]
    keys(grader, "schema kind identity instructions calibration", "grader definition")
    if grader["schema"] != "eval-grader/1" or grader["kind"] not in {"deterministic", "human", "model"}:
        fail("unsupported grader definition")
    text(grader["identity"], "grader identity")
    for name in ("instructions", "calibration"):
        data_text(grader[name], name)
    subject = values["subject"]
    keys(subject, "schema identity configuration", "subject")
    if subject["schema"] != "eval-subject/1":
        fail("unsupported subject definition")
    text(subject["identity"], "subject identity")
    data_text(subject["configuration"], "subject configuration")
    return values


def _test_obligations(prd_text):
    active = active_text(prd_text)
    headings = list(re.finditer(r"^## Test Obligations[ \t]*$", active, re.M))
    if len(headings) != 1:
        fail("evaluation requires one canonical Test Obligations section")
    section = re.split(r"^##[ \t]+", active[headings[0].end():], maxsplit=1, flags=re.M)[0]
    lines = section.splitlines()

    def cells(line):
        line = line.strip()
        return tuple(part.strip() for part in line[1:-1].split("|")) if line.startswith("|") and line.endswith("|") else ()

    header = ("test id", "obligation", "test type", "required", "upstream trace ids", "expected signal")
    tables = [index for index, line in enumerate(lines) if tuple(part.casefold() for part in cells(line)) == header]
    if len(tables) != 1:
        fail("evaluation requires one canonical Test Obligations table")
    index = tables[0]
    separator = cells(lines[index + 1]) if index + 1 < len(lines) else ()
    if len(separator) != 6 or not all(re.fullmatch(r":?-{3,}:?", part) for part in separator):
        fail("Test Obligations table needs its Markdown separator")
    rows = {}
    for line in lines[index + 2:]:
        row = cells(line)
        if not row:
            if rows:
                break
            continue
        if len(row) != 6 or not re.fullmatch(r"TEST-[A-Z0-9-]+", row[0], re.I):
            fail("invalid row in canonical Test Obligations table")
        test_id = row[0].upper()
        if test_id in rows:
            fail("duplicate TEST in evaluation obligations")
        rows[test_id] = row
    return rows


def validate_eval_policy(prd_text, *, required=False, repo_root=None):
    try:
        policy = parse_eval_policy(prd_text, required=required)
        if policy is None:
            return []
        validate_policy_shape(policy)
        ai_lines = re.findall(r"^AI and Automation Gate:\s*(required|not_required|blocked)\b", active_text(prd_text), re.M)
        if len(ai_lines) != 1 or ai_lines[0] == "blocked":
            fail("evaluation requires one resolved AI gate")
        if ai_lines[0] == "required" and policy["applicability"] != "required":
            fail("AI gate required cannot waive evaluation")
        if policy["applicability"] == "required":
            rows = _test_obligations(prd_text)
            for name in ("quality", "handoff"):
                row = rows.get(policy[name]["test_id"])
                if row is None or row[3].casefold() != "yes" or (ai_lines[0] == "required" and not re.search(r"\bAI-EVALUATION\b", row[4])):
                    fail("eval quality/handoff must join Required-Yes TESTs and AI-EVALUATION when applicable")
            if repo_root is not None:
                parse_inputs(policy, lambda path: read_artifact(repo_root, path))
        return []
    except (PolicyError, OSError, TypeError, KeyError, OverflowError, ValueError, RecursionError) as exc:
        return [f"eval-policy: {exc}" if isinstance(exc, PolicyError) else "eval-policy: invalid or unreadable input"]

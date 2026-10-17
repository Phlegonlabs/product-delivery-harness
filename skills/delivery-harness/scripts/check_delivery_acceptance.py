#!/usr/bin/env python3
"""Validate frozen delivery-acceptance evidence without executing tests."""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from delivery_acceptance_execution import concrete_text, execution, observations

from delivery_acceptance_io import (
    AcceptanceError, _read_bytes, _load_json, _safe_file, _sha256,
    _parse_required_prd_tests,
)
from harness_git import GitMetadataError, reject_object_substitution, run_git
from harness_schema import supported_coordination_path


CONTRACT_SCHEMA = "delivery-acceptance/1"
CONTRACT_SCHEMA_V2 = "delivery-acceptance/2"
RESULT_SCHEMA = "delivery-results/1"
RESULT_SCHEMA_V2 = "delivery-results/2"
CONTRACT_SCHEMAS = {CONTRACT_SCHEMA, CONTRACT_SCHEMA_V2}
RESULT_SCHEMAS = {RESULT_SCHEMA, RESULT_SCHEMA_V2}
CONTRACT_KEYS = {"schema", "prd_sha256", "tests"}
RESULT_KEYS = {"schema", "candidate_sha", "results"}
SCENARIO_KEYS = {"id", "platform", "auth_mode", "environment", "build", "fixtures", "execution"}
FIXTURE_KEYS = {
    "namespace",
    "setup_authority",
    "cleanup_authority",
    "owned_resources",
    "production",
    "auth_bypass",
}
ROW_KEYS = {
    "execution", "assertion_results", "fixture_cleanup",
    "test_id",
    "scenario_id",
    "platform",
    "auth_mode",
    "environment",
    "build",
    "status",
    "evidence",
}
EVIDENCE_KEYS = {"path", "sha256"}
PLATFORMS = {
    "web",
    "browser-extension",
    "ios",
    "android",
    "macos",
    "windows",
    "desktop",
    "agent",
    "api",
    "cli",
}
NATIVE_PLATFORMS = {"ios", "android", "macos", "windows"}
AUTH_MODES = {"mock", "real", "none"}
ENVIRONMENTS = {"local", "test", "preview", "staging", "production"}
STATUSES = {"pass", "fail", "blocked", "skipped", "unvalidated"}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
GIT_SHA_RE = re.compile(r"[0-9a-f]{40}")
TEST_ID_RE = re.compile(r"TEST-[A-Z0-9-]+")
NAMESPACE_RE = re.compile(r"synthetic-[a-z0-9][a-z0-9-]{7,127}")
def _string(value: Any, path: str, errors: list[str]) -> str:
    if not concrete_text(value):
        errors.append(f"{path} must be concrete non-placeholder text")
        return ""
    return value.strip()


def _enum(
    value: Any, path: str, allowed: set[str], errors: list[str]
) -> str:
    if isinstance(value, str) and value.strip() in allowed:
        return value.strip()
    errors.append(f"{path} must be one of {sorted(allowed)}")
    return ""


def _exact_keys(
    value: Any, expected: set[str], path: str, errors: list[str]
) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return False
    if set(value) != expected:
        errors.append(f"{path} keys must be exactly {sorted(expected)}")
        return False
    return True


def _build(
    value: Any, path: str, platform: str, environment: str, errors: list[str]
) -> dict[str, str] | None:
    if not isinstance(value, dict):
        errors.append(f"{path} must be an object")
        return None
    keys = set(value)
    if keys == {"not_applicable_reason"}:
        reason = _string(value["not_applicable_reason"], f"{path}.not_applicable_reason", errors)
        if len(reason) < 12:
            errors.append(f"{path}.not_applicable_reason must explain genuine non-applicability")
        if platform in NATIVE_PLATFORMS or environment != "local":
            errors.append(f"{path} identity is required for native and non-local scenarios")
        return {"not_applicable_reason": reason}
    if keys != {"build_id", "config_digest"}:
        errors.append(f"{path} must use build identity or one not-applicable reason")
        return None
    build_id = _string(value["build_id"], f"{path}.build_id", errors)
    digest = _string(value["config_digest"], f"{path}.config_digest", errors)
    if digest and SHA256_RE.fullmatch(digest) is None:
        errors.append(f"{path}.config_digest must be a lowercase SHA-256 hex digest")
        return None
    return {"build_id": build_id, "config_digest": digest}


def _fixtures(value: Any, environment: str, path: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{path} must be a list")
        return
    if environment == "production" and value:
        errors.append(f"{path} cannot declare synthetic fixtures for a production scenario")
    for index, fixture in enumerate(value):
        fixture_path = f"{path}[{index}]"
        if not _exact_keys(fixture, FIXTURE_KEYS, fixture_path, errors):
            continue
        namespace = _string(fixture["namespace"], f"{fixture_path}.namespace", errors).casefold()
        if namespace and NAMESPACE_RE.fullmatch(namespace) is None:
            errors.append(f"{fixture_path}.namespace must be an isolated synthetic-* namespace")
        _string(fixture["setup_authority"], f"{fixture_path}.setup_authority", errors)
        _string(fixture["cleanup_authority"], f"{fixture_path}.cleanup_authority", errors)
        resources = fixture["owned_resources"]
        if not isinstance(resources, list) or not resources:
            errors.append(f"{fixture_path}.owned_resources must be a non-empty list")
            resources = []
        normalized = [
            _string(resource, f"{fixture_path}.owned_resources[{resource_index}]", errors)
            for resource_index, resource in enumerate(resources)
        ]
        if any(resource and not resource.startswith("owned:") for resource in normalized):
            errors.append(f"{fixture_path}.owned_resources values must start with owned:")
        if any(not concrete_text(resource.removeprefix("owned:")) for resource in normalized):
            errors.append(f"{fixture_path}.owned_resources suffix must identify a real owned resource")
        if len(normalized) != len(set(normalized)):
            errors.append(f"{fixture_path}.owned_resources must be unique")
        for field in ("production", "auth_bypass"):
            if not isinstance(fixture[field], bool):
                errors.append(f"{fixture_path}.{field} must be boolean")
            elif fixture[field]:
                errors.append(f"{fixture_path}.{field} must be false")


def _contract(
    value: dict[str, Any], all_prd_tests: set[str], required_prd_tests: set[str]
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[str]]:
    errors: list[str] = []
    if not _exact_keys(value, CONTRACT_KEYS, "contract", errors):
        return {}, errors
    schema = value.get("schema")
    if schema not in CONTRACT_SCHEMAS:
        errors.append(f"contract.schema must be one of {sorted(CONTRACT_SCHEMAS)}")
        version = 0
    else:
        version = int(schema.rpartition("/")[2])
    tests = value.get("tests")
    if not isinstance(tests, list):
        errors.append("contract.tests must be a list")
        return {}, errors

    scenarios: dict[tuple[str, str], dict[str, Any]] = {}
    seen_tests: set[str] = set()
    for test_index, test in enumerate(tests):
        test_path = f"contract.tests[{test_index}]"
        if not _exact_keys(test, {"test_id", "scenarios"}, test_path, errors):
            continue
        test_id = _string(test.get("test_id") if isinstance(test, dict) else None, f"{test_path}.test_id", errors)
        if not test_id:
            continue
        if TEST_ID_RE.fullmatch(test_id) is None:
            errors.append(f"{test_path}.test_id has invalid TEST ID")
            continue
        if test_id in seen_tests:
            errors.append(f"{test_path}.test_id duplicates {test_id}")
            continue
        seen_tests.add(test_id)
        if test_id not in all_prd_tests:
            errors.append(f"{test_id} is not declared by the frozen PRD")
        raw_scenarios = test.get("scenarios") if isinstance(test, dict) else None
        if not isinstance(raw_scenarios, list):
            errors.append(f"{test_path}.scenarios must be a list")
            continue
        if test_id in required_prd_tests and not raw_scenarios:
            errors.append(f"required {test_id} has no frozen scenarios")
        for scenario_index, scenario in enumerate(raw_scenarios):
            scenario_path = f"{test_path}.scenarios[{scenario_index}]"
            if not _exact_keys(scenario, SCENARIO_KEYS, scenario_path, errors):
                continue
            scenario_id = _string(scenario["id"], f"{scenario_path}.id", errors)
            platform = _enum(scenario["platform"], f"{scenario_path}.platform", PLATFORMS, errors)
            auth_mode = _enum(scenario["auth_mode"], f"{scenario_path}.auth_mode", AUTH_MODES, errors)
            environment = _enum(
                scenario["environment"], f"{scenario_path}.environment", ENVIRONMENTS, errors
            )
            if environment == "production" and auth_mode == "mock":
                errors.append(f"{scenario_path} cannot use mock authentication in production")
            build = _build(scenario["build"], f"{scenario_path}.build", platform, environment, errors)
            _fixtures(scenario["fixtures"], environment, f"{scenario_path}.fixtures", errors)
            execution(
                scenario["execution"], f"{scenario_path}.execution", errors,
                browser=version == 2 and platform == "web",
            )
            key = (test_id, scenario_id)
            if not scenario_id or key in scenarios:
                errors.append(f"{scenario_path}.id must be unique within {test_id}")
                continue
            scenarios[key] = {
                "platform": platform,
                "auth_mode": auth_mode,
                "environment": environment,
                "build": build,
                "execution": scenario["execution"],
                "fixtures": scenario["fixtures"],
            }

    for test_id in sorted(required_prd_tests - seen_tests):
        errors.append(f"required {test_id} is absent from the frozen contract")
    return scenarios, errors


def evidence_root(results_path: str) -> str:
    """Evidence lives in ``evidence/`` next to the register."""

    return posixpath.join(posixpath.dirname(results_path), "evidence")


def _under_root(raw_path: str, root: str) -> bool:
    posix = Path(raw_path).as_posix()
    return ".." not in posix.split("/") and posix.startswith(root + "/")


def _evidence(
    root: Path, value: Any, path: str, errors: list[str], allowed_root: str,
    captured: dict[str, bytes] | None = None,
) -> bool:
    if not _exact_keys(value, EVIDENCE_KEYS, path, errors):
        return False
    raw_path = _string(value.get("path"), f"{path}.path", errors)
    expected_hash = _string(value.get("sha256"), f"{path}.sha256", errors)
    if expected_hash and SHA256_RE.fullmatch(expected_hash) is None:
        errors.append(f"{path}.sha256 must be a lowercase SHA-256 hex digest")
    if not raw_path:
        return False
    if Path(raw_path).is_absolute():
        errors.append(f"{path}.path must be repository-relative")
        return False

    try:
        payload = _read_bytes(Path(raw_path), "evidence", root)
    except AcceptanceError:
        errors.append(f"{path}.path cannot be read safely")
        return False
    if not _under_root(raw_path, allowed_root):
        errors.append(f"{path}.path {raw_path} must be under {allowed_root}/")
        return False
    if not payload:
        errors.append(f"{path}.path is empty")
        return False
    if _sha256(payload) != expected_hash:
        errors.append(f"{path}.sha256 does not match the evidence artifact")
        return False
    if captured is not None:
        normalized = Path(raw_path).as_posix()
        prior = captured.get(normalized)
        if prior is not None and prior != payload:
            errors.append(f"{path}.path {normalized} changed between result rows")
            return False
        captured[normalized] = payload
    return True


def _result_schema(contract_schema: Any) -> str:
    """The results schema paired with a contract schema by version."""

    if isinstance(contract_schema, str) and contract_schema in CONTRACT_SCHEMAS:
        return f"delivery-results/{contract_schema.rpartition('/')[2]}"
    return ""


def _results(
    value: dict[str, Any],
    scenarios: dict[tuple[str, str], dict[str, Any]],
    required_tests: set[str],
    candidate_sha: str,
    root: Path,
    allowed_root: str,
    captured: dict[str, bytes],
    contract_schema: str = CONTRACT_SCHEMA,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    if not _exact_keys(value, RESULT_KEYS, "results", errors):
        return [], errors
    schema = value.get("schema")
    if schema not in RESULT_SCHEMAS:
        errors.append(f"results.schema must be one of {sorted(RESULT_SCHEMAS)}")
    elif schema != _result_schema(contract_schema):
        errors.append(
            f"results.schema {schema!r} does not match contract schema {contract_schema!r}"
        )
    recorded_sha = _string(value.get("candidate_sha"), "results.candidate_sha", errors)
    if recorded_sha and GIT_SHA_RE.fullmatch(recorded_sha) is None:
        errors.append("results.candidate_sha must be a lowercase 40-character Git SHA")
    if recorded_sha != candidate_sha:
        errors.append("results.candidate_sha does not match the expected candidate")

    rows = value.get("results")
    if not isinstance(rows, list):
        errors.append("results.results must be a list")
        return [], errors

    seen_rows: set[tuple[Any, ...]] = set()
    matched: set[tuple[str, str]] = set()
    required_keys = {key for key in scenarios if key[0] in required_tests}
    for index, row in enumerate(rows):
        row_path = f"results.results[{index}]"
        if not _exact_keys(row, ROW_KEYS, row_path, errors):
            continue
        test_id = _string(row["test_id"], f"{row_path}.test_id", errors)
        scenario_id = _string(row["scenario_id"], f"{row_path}.scenario_id", errors)
        platform = _enum(row["platform"], f"{row_path}.platform", PLATFORMS, errors)
        auth_mode = _enum(row["auth_mode"], f"{row_path}.auth_mode", AUTH_MODES, errors)
        environment = _enum(
            row["environment"], f"{row_path}.environment", ENVIRONMENTS, errors
        )
        status = _enum(row["status"], f"{row_path}.status", STATUSES, errors)
        build = _build(row["build"], f"{row_path}.build", platform, environment, errors)
        evidence_ok = _evidence(
            root, row["evidence"], f"{row_path}.evidence", errors, allowed_root,
            captured,
        )
        identity = (
            test_id,
            scenario_id,
            platform,
            auth_mode,
            environment,
            json.dumps(build, sort_keys=True, separators=(",", ":")),
        )
        if all(isinstance(item, str) and item for item in identity[:5]):
            if identity in seen_rows:
                errors.append(f"{row_path} duplicates an earlier evidence identity")
            seen_rows.add(identity)
        key = (test_id, scenario_id)
        expected = scenarios.get(key)
        if expected is None:
            errors.append(f"{row_path} has no matching frozen scenario")
            continue
        actual = {
            "platform": platform,
            "auth_mode": auth_mode,
            "environment": environment,
            "build": build,
            "execution": row["execution"],
            "fixtures": expected["fixtures"],
        }
        if actual != expected:
            errors.append(f"{row_path} identity does not match frozen scenario {test_id}/{scenario_id}")
            continue
        observations(row, expected, row_path, errors)
        if test_id in required_tests:
            if status != "pass":
                errors.append(f"required {test_id}/{scenario_id} status must be pass")
            elif evidence_ok:
                matched.add(key)

    missing = sorted(required_keys - matched)
    for test_id, scenario_id in missing:
        errors.append(f"required {test_id}/{scenario_id} has no exact passing evidence")
    return sorted(f"{test_id}/{scenario_id}" for test_id, scenario_id in matched), errors


def _evidence_paths(value: dict[str, Any], allowed_root: str) -> set[str]:
    """Listed evidence paths under the evidence root; no other path is exempt."""

    rows = value.get("results")
    paths: set[str] = set()
    for row in rows if isinstance(rows, list) else []:
        evidence = row.get("evidence") if isinstance(row, dict) else None
        raw = evidence.get("path") if isinstance(evidence, dict) else None
        if isinstance(raw, str) and _under_root(raw.strip(), allowed_root):
            paths.add(Path(raw.strip()).as_posix())
    return paths


def _head_sha(root: Path) -> str:
    """Resolve the checked-out commit once for this gate invocation."""

    try:
        observed = run_git(root, "rev-parse", "--verify", "HEAD^{commit}")
    except (GitMetadataError, OSError, subprocess.SubprocessError) as exc:
        raise AcceptanceError(f"cannot resolve Git HEAD: {exc}") from exc
    if observed.returncode != 0 or GIT_SHA_RE.fullmatch(observed.stdout.strip()) is None:
        raise AcceptanceError("cannot resolve Git HEAD commit")
    return observed.stdout.strip()


def _committed_file_errors(root: Path, head_sha: str, path: str, payload: bytes) -> list[str]:
    """Require the exact bytes checked here to be a regular file at one HEAD."""

    try:
        entry = run_git(root, "ls-tree", "-z", head_sha, "--", path, text=False)
        if entry.returncode != 0:
            return [f"cannot inspect {path} in HEAD"]
        lines = [item for item in entry.stdout.split(b"\0") if item]
        if len(lines) != 1:
            return [f"{path} is not committed at HEAD"]
        metadata, separator, listed_path = lines[0].partition(b"\t")
        fields = metadata.split()
        if (not separator or listed_path != path.encode("utf-8") or
                len(fields) != 3 or fields[0] not in {b"100644", b"100755"} or
                fields[1] != b"blob"):
            return [f"{path} is not a regular file committed at HEAD"]
        actual = run_git(root, "hash-object", "--stdin", input=payload, text=False)
        if actual.returncode != 0:
            return [f"cannot hash {path} against HEAD"]
    except (GitMetadataError, OSError, subprocess.SubprocessError) as exc:
        return [f"cannot verify {path} against HEAD: {exc}"]
    if actual.stdout.strip() != fields[2]:
        return [
            f"{path} bytes differ from HEAD; check line-ending or Git filter conversion"
        ]
    return []


def _candidate_tree_errors(
    root: Path, candidate: str, head_sha: str, allowed: set[str]
) -> list[str]:
    """Bind the register's candidate to the checked-out HEAD.

    The candidate must be HEAD or an ancestor of it, and the commits after it
    may change only the register, the evidence files it lists under the
    evidence root and run coordination files. Any other change makes a new candidate whose
    scenarios have not run.
    """

    try:
        reject_object_substitution(root)
        kind = run_git(root, "cat-file", "-t", candidate)
        if kind.returncode != 0 or kind.stdout.strip() != "commit":
            return [f"results.candidate_sha {candidate} is not a commit in this checkout"]
        ancestor = run_git(root, "merge-base", "--is-ancestor", candidate, head_sha)
        if ancestor.returncode != 0:
            return [f"results.candidate_sha {candidate} is not an ancestor of HEAD"]
        diff = run_git(
            root, "diff", "--name-only", "-z", "--no-renames",
            "--ignore-submodules=none", candidate, head_sha,
            text=False,
        )
    except (GitMetadataError, OSError, subprocess.SubprocessError) as exc:
        return [f"cannot read Git state for the candidate: {exc}"]
    if diff.returncode != 0:
        return ["cannot read the changes after the candidate from Git"]
    changed = [path for path in diff.stdout.decode("utf-8", "replace").split("\0") if path]
    extra = sorted(
        path for path in changed
        if path not in allowed and not supported_coordination_path(path)
    )
    if extra:
        return [
            "files changed after the candidate other than the register and its "
            "evidence: " + ", ".join(extra)
        ]
    return []


def _response(errors: list[str], **fields: Any) -> dict[str, Any]:
    return {
        "status": "FAIL" if errors else "PASS",
        "errors": errors,
        **fields,
    }


def _run(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    if SHA256_RE.fullmatch(args.contract_sha256) is None:
        errors = ["--contract-sha256 must be a lowercase SHA-256 hex digest"]
        return 1, _response(errors)
    if args.candidate_sha is not None and GIT_SHA_RE.fullmatch(args.candidate_sha) is None:
        errors = ["--candidate-sha must be a lowercase 40-character Git SHA"]
        return 1, _response(errors)

    try:
        root = args.repo_root.resolve(strict=True)
        if not root.is_dir():
            raise AcceptanceError("repository root must be a directory")
        git_checkout = (root / ".git").exists()
        if args.candidate_from_head and not git_checkout:
            raise AcceptanceError("--candidate-from-head needs --repo-root to be a Git checkout root")
        head_sha = _head_sha(root) if git_checkout else None
        prd_bytes = _read_bytes(args.prd, "PRD", root)
        contract_bytes = _read_bytes(args.contract, "contract", root)
        result_bytes = _read_bytes(args.results, "results", root)
        results_path = _safe_file(root, str(args.results)).relative_to(root).as_posix()
        if _sha256(contract_bytes) != args.contract_sha256:
            return 1, _response(["contract bytes do not match --contract-sha256"])
        contract = _load_json(contract_bytes, "contract")
        results = _load_json(result_bytes, "results")
        all_tests, required_tests, errors = _parse_required_prd_tests(prd_bytes)
    except (AcceptanceError, OSError) as exc:
        return 1, _response([str(exc)])

    prd_hash = _sha256(prd_bytes)
    if contract.get("prd_sha256") != prd_hash:
        errors.append("contract.prd_sha256 does not match the actual PRD bytes")
    scenarios, contract_errors = _contract(contract, all_tests, required_tests)
    errors.extend(contract_errors)
    if errors:
        return 1, _response(errors)
    # With --candidate-from-head the register names the candidate, and Git
    # below must show that its product tree is exactly HEAD's.
    candidate_sha = args.candidate_sha
    if candidate_sha is None:
        recorded = results.get("candidate_sha")
        candidate_sha = recorded if isinstance(recorded, str) else ""
    allowed_root = evidence_root(results_path)
    captured_evidence: dict[str, bytes] = {}
    matched, result_errors = _results(
        results, scenarios, required_tests, candidate_sha, root, allowed_root,
        captured_evidence, contract.get("schema"),
    )
    errors.extend(result_errors)
    if head_sha is not None and GIT_SHA_RE.fullmatch(candidate_sha):
        errors.extend(_committed_file_errors(root, head_sha, results_path, result_bytes))
        for path, evidence_bytes in sorted(captured_evidence.items()):
            errors.extend(_committed_file_errors(root, head_sha, path, evidence_bytes))
        errors.extend(
            _candidate_tree_errors(
                root, candidate_sha, head_sha,
                {results_path} | _evidence_paths(results, allowed_root),
            )
        )
    if head_sha is not None:
        try:
            if _head_sha(root) != head_sha:
                errors.append("HEAD changed during acceptance check")
        except AcceptanceError as exc:
            errors.append(str(exc))
    payload = _response(
        errors,
        required_tests=sorted(required_tests),
        required_scenarios=sorted(
            f"{test_id}/{scenario_id}"
            for test_id, scenario_id in scenarios
            if test_id in required_tests
        ),
        matched_scenarios=matched,
        prd_sha256=prd_hash,
        contract_sha256=args.contract_sha256,
        candidate_sha=candidate_sha,
    )
    return (0 if not errors else 1), payload


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        print(json.dumps(_response([message]), ensure_ascii=False, sort_keys=True))
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    parser = JsonArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--prd", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--results", required=True, type=Path)
    candidate = parser.add_mutually_exclusive_group(required=True)
    candidate.add_argument("--candidate-sha")
    candidate.add_argument("--candidate-from-head", action="store_true")
    args = parser.parse_args(argv)
    status, payload = _run(args)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return status


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())

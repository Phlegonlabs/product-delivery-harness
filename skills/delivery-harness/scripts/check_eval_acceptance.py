#!/usr/bin/env python3
"""Check approved eval policy, two full reports and exact Git evidence read-only."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import sys

import check_delivery_acceptance as acceptance
from delivery_acceptance_io import AcceptanceError, _read_bytes, _load_json, _safe_file, _sha256, _parse_required_prd_tests
try:
    from eval_verification import ep, validate_contract, validate_report, QUALITY_ASSERTIONS, HANDOFF_ASSERTIONS
except (ImportError, OSError, SyntaxError):
    if __name__ == "__main__":
        print(json.dumps({"status": "FAIL", "errors": ["installed sibling eval policy parser unavailable"]}))
        sys.exit(1)
    raise
from harness_git import GitMetadataError, run_git, reject_object_substitution


def verify(root, *, prd, prd_sha256, contract, contract_sha256, delivery_contract,
           delivery_contract_sha256, results):
    root = Path(root).resolve(strict=True)
    for value in (prd_sha256, contract_sha256, delivery_contract_sha256):
        if not isinstance(value, str) or not ep.HASH.fullmatch(value):
            raise AcceptanceError("each frozen input needs a lowercase SHA-256")
    top = run_git(root, "rev-parse", "--show-toplevel")
    if top.returncode or Path(top.stdout.strip()).resolve() != root:
        raise AcceptanceError("repo-root must be the exact Git checkout root")
    reject_object_substitution(root)
    head = acceptance._head_sha(root)
    clean = run_git(root, "status", "--porcelain", "--untracked-files=all")
    if clean.returncode or clean.stdout.strip():
        raise AcceptanceError("eval gate requires a clean exact-head checkout")
    captured = {}
    candidate_bound = set()

    def read(path, label, *, at_candidate=False):
        safe = _safe_file(root, str(path))
        relative = safe.relative_to(root).as_posix()
        raw = _read_bytes(safe, label, root)
        prior = captured.get(relative)
        if prior is not None and prior != raw:
            raise AcceptanceError("input changed during eval check")
        captured[relative] = raw
        if at_candidate:
            candidate_bound.add(relative)
        return raw

    prd_bytes = read(prd, "PRD", at_candidate=True)
    eval_bytes = read(contract, "eval contract", at_candidate=True)
    delivery_bytes = read(delivery_contract, "delivery contract", at_candidate=True)
    result_bytes = read(results, "results")
    for raw, expected in ((prd_bytes, prd_sha256), (eval_bytes, contract_sha256), (delivery_bytes, delivery_contract_sha256)):
        if _sha256(raw) != expected:
            raise AcceptanceError("input differs from independently frozen hash")
    try:
        prd_text = prd_bytes.decode("utf-8")
    except UnicodeError as exc:
        raise AcceptanceError("PRD must be UTF-8") from exc
    errors = ep.validate_eval_policy(prd_text, required=True)
    if errors:
        return {"status": "FAIL", "errors": errors}
    policy = ep.parse_eval_policy(prd_text, required=True)
    if policy["applicability"] != "required":
        raise AcceptanceError("eval verifier requires an applicable policy")
    approved = ep.parse_inputs(policy, lambda path: read(path, "approved eval input", at_candidate=True))
    validate_contract(_load_json(eval_bytes, "eval contract"), policy, prd_sha256)
    delivery = _load_json(delivery_bytes, "delivery contract")
    register = _load_json(result_bytes, "results")
    all_tests, required_tests, errors = _parse_required_prd_tests(prd_bytes)
    if delivery.get("prd_sha256") != prd_sha256:
        errors.append("delivery contract differs from frozen PRD")
    scenarios, contract_errors = acceptance._contract(delivery, all_tests, required_tests)
    errors.extend(contract_errors)
    if errors:
        return {"status": "FAIL", "errors": errors}
    candidate = register.get("candidate_sha")
    if not isinstance(candidate, str) or not acceptance.GIT_SHA_RE.fullmatch(candidate):
        raise AcceptanceError("register needs a full candidate SHA")
    results_path = _safe_file(root, str(results)).relative_to(root).as_posix()
    evidence_root = acceptance.evidence_root(results_path)
    evidence = {}
    _, result_errors = acceptance._results(register, scenarios, required_tests, candidate,
                                           root, evidence_root, evidence)
    errors.extend(result_errors)
    if errors:
        return {"status": "FAIL", "errors": errors}
    for path, raw in evidence.items():
        if path in captured and captured[path] != raw:
            raise AcceptanceError("input changed during eval check")
        captured[path] = raw
    artifacts = {policy[name]["path"]: policy[name]["sha256"] for name in ("dataset", "rubric", "grader", "subject")}
    for name in ("runner", "grader", "lockfile", "runbook"):
        path = policy["delivery"][name]
        raw = read(path, "delivered eval artifact", at_candidate=True)
        artifacts[path] = _sha256(raw)
    summaries = {}
    reports = {}
    for purpose, assertions in (("quality", QUALITY_ASSERTIONS), ("handoff", HANDOFF_ASSERTIONS)):
        declared = policy[purpose]
        key = (declared["test_id"], declared["scenario_id"])
        expected = scenarios.get(key)
        rows = [row for row in register["results"] if (row["test_id"], row["scenario_id"]) == key]
        if (expected is None or len(rows) != 1 or set(expected["execution"]["assertions"]) != assertions
                or rows[0]["evidence"]["path"] != declared["report"]):
            raise AcceptanceError("eval scenario/assertion/report join differs from PRD policy")
        raw = evidence.get(declared["report"])
        if raw is None:
            raise AcceptanceError("report is not directly registered evidence")
        report = _load_json(raw, "eval report")
        reports[purpose] = report
        summaries[purpose] = validate_report(report, policy, approved, purpose=purpose,
            candidate_sha=candidate, contract_sha256=contract_sha256, prd_sha256=prd_sha256,
            execution=expected["execution"], artifacts=artifacts)
    if (reports["quality"]["run_id"] == reports["handoff"]["run_id"]
            or reports["quality"]["provenance"]["job_id"] == reports["handoff"]["provenance"]["job_id"]):
        raise AcceptanceError("quality and handoff require independent run/job identities")
    for path, raw in sorted(captured.items()):
        errors.extend(acceptance._committed_file_errors(root, head, path, raw))
    protected = run_git(root, "--literal-pathspecs", "diff", "--no-ext-diff",
        "--no-textconv", "--no-renames", "--ignore-submodules=none", "--name-only", "-z",
        candidate, head, "--", *sorted(candidate_bound), text=False)
    if protected.returncode:
        raise AcceptanceError("cannot compare protected eval paths with tested candidate H1")
    errors.extend("tested candidate H1: " + path.decode("utf-8") + " tree changed"
                  for path in protected.stdout.split(b"\0") if path)
    errors.extend(acceptance._candidate_tree_errors(root, candidate, head,
        {results_path} | acceptance._evidence_paths(register, evidence_root)))
    if acceptance._head_sha(root) != head:
        errors.append("HEAD changed during eval check")
    final_status = run_git(root, "status", "--porcelain", "--untracked-files=all")
    if final_status.returncode or final_status.stdout.strip():
        errors.append("checkout changed during eval check")
    return {"status": "FAIL" if errors else "PASS", "errors": errors,
            "candidate_sha": candidate, "checked_head_sha": head, "reports": summaries}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--prd", required=True)
    parser.add_argument("--prd-sha256", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--delivery-contract", required=True)
    parser.add_argument("--delivery-contract-sha256", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--candidate-from-head", action="store_true", required=True)
    config = parser.parse_args(argv)
    try:
        result = verify(config.repo_root, prd=config.prd, prd_sha256=config.prd_sha256,
            contract=config.contract, contract_sha256=config.contract_sha256,
            delivery_contract=config.delivery_contract,
            delivery_contract_sha256=config.delivery_contract_sha256, results=config.results)
    except (AcceptanceError, ep.PolicyError) as exc:
        result = {"status": "FAIL", "errors": [str(exc)]}
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError, GitMetadataError,
            subprocess.SubprocessError):
        result = {"status": "FAIL", "errors": ["invalid, unsafe or unreadable eval evidence"]}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())

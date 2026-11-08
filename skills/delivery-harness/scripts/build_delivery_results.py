#!/usr/bin/env python3
"""Build delivery-results.json from the frozen register and evidence files.

Each row copies its identity (TEST ID, scenario id, platform, auth_mode,
environment, build and execution) from the frozen `delivery-acceptance/1`
register. Status, assertion results and fixture cleanup come only from the
scenario sections of the `--evidence` files:

    ## <scenario_id> (<TEST-ID>) — row status: <status>
    fixture_cleanup: <cleaned|not_required|pending|failed>
    ### ASSERT-001 — <status>

A missing assertion becomes `unvalidated`, a missing cleanup line `pending`
(`not_required` when the scenario has no fixtures). The evidence path and
SHA-256 come from the file bytes. A scenario with no section is printed and
left out, so a required one then fails check_delivery_acceptance.py.

Writes only `--out`, whose evidence must sit in `evidence/` next to it under
`--repo-root`. Exits 0 on success, 1 with one line per finding, 2 on bad
arguments.
"""

from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path
from typing import Any

from check_delivery_acceptance import GIT_SHA_RE, RESULT_SCHEMA, SHA256_RE, STATUSES, _contract, evidence_root
from delivery_acceptance_io import AcceptanceError, _load_json, _parse_required_prd_tests, _sha256
from render_delivery_acceptance import register_bytes


SECTION_RE = re.compile(r"## (?P<scenario>.+?) \((?P<test>TEST-[A-Z0-9-]+)\) — row status: (?P<status>\S+)")
ASSERT_RE = re.compile(r"### (?P<key>[A-Za-z0-9][A-Za-z0-9_.-]*) — (?P<status>\S+)")
CLEANUP_RE = re.compile(r"fixture_cleanup: (?P<value>\S+)")
CLEANUP_VALUES = {"cleaned", "not_required", "pending", "failed"}


def parse_evidence(label: str, text: str, errors: list[str]) -> dict[tuple[str, str], dict[str, Any]]:
    """Return {(TEST ID, scenario id): section} for one evidence file."""

    sections: dict[tuple[str, str], dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        where = f"{label}:{number}"
        if line.startswith("## "):
            match = SECTION_RE.fullmatch(line)
            current = None
            if match is None:
                continue
            key = (match["test"], match["scenario"])
            if key in sections:
                errors.append(f"{where}: second section for {key[1]} ({key[0]})")
                continue
            if match["status"] not in STATUSES:
                errors.append(f"{where}: row status must be one of {sorted(STATUSES)}")
            current = sections[key] = {
                "where": where, "status": match["status"], "assertions": {}, "cleanup": None,
            }
        elif current is None:
            continue
        elif (match := ASSERT_RE.fullmatch(line)) is not None:
            if match["key"] in current["assertions"]:
                errors.append(f"{where}: second {match['key']} in this section")
            elif match["status"] not in STATUSES:
                errors.append(f"{where}: assertion status must be one of {sorted(STATUSES)}")
            current["assertions"][match["key"]] = match["status"]
        elif (match := CLEANUP_RE.fullmatch(line)) is not None:
            if current["cleanup"] is not None:
                errors.append(f"{where}: second fixture_cleanup in this section")
            elif match["value"] not in CLEANUP_VALUES:
                errors.append(f"{where}: fixture_cleanup must be one of {sorted(CLEANUP_VALUES)}")
            current["cleanup"] = match["value"]
    return sections


def build(
    contract: dict[str, Any], evidence: list[tuple[str, bytes]], candidate_sha: str,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Return (results, findings, scenarios left out)."""

    errors: list[str] = []
    sections: dict[tuple[str, str], tuple[dict[str, Any], str, str]] = {}
    for path, payload in evidence:
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"{path}: not UTF-8")
            continue
        for key, section in parse_evidence(path, text, errors).items():
            if key in sections:
                errors.append(f"{section['where']}: {key[1]} ({key[0]}) already has a section at {sections[key][0]['where']}")
                continue
            sections[key] = (section, path, _sha256(payload))

    rows: list[dict[str, Any]] = []
    left_out: list[str] = []
    frozen: set[tuple[str, str]] = set()
    for test in contract["tests"]:
        for scenario in test["scenarios"]:
            key = (test["test_id"], scenario["id"])
            frozen.add(key)
            if key not in sections:
                left_out.append(f"{key[1]} ({key[0]})")
                continue
            section, path, digest = sections[key]
            assertions = scenario["execution"]["assertions"]
            for name in sorted(set(section["assertions"]) - set(assertions)):
                errors.append(f"{section['where']}: {name} is not an assertion of {key[1]} ({key[0]})")
            cleanup = (section["cleanup"] or "pending") if scenario["fixtures"] else "not_required"
            rows.append({
                "test_id": key[0],
                "scenario_id": key[1],
                "platform": scenario["platform"],
                "auth_mode": scenario["auth_mode"],
                "environment": scenario["environment"],
                "build": copy.deepcopy(scenario["build"]),
                "execution": copy.deepcopy(scenario["execution"]),
                "status": section["status"],
                "assertion_results": {name: section["assertions"].get(name, "unvalidated") for name in assertions},
                "fixture_cleanup": cleanup,
                "evidence": {"path": path, "sha256": digest},
            })
    for key in sorted(set(sections) - frozen):
        errors.append(f"{sections[key][0]['where']}: {key[1]} ({key[0]}) is not a scenario in the register")
    return {"schema": RESULT_SCHEMA, "candidate_sha": candidate_sha, "results": rows}, errors, left_out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repository root (default: .)")
    parser.add_argument("--prd", required=True, type=Path, help="Frozen PRD.md")
    parser.add_argument("--contract", required=True, type=Path, help="Frozen delivery-acceptance.json")
    parser.add_argument("--contract-sha256", required=True, help="Recorded SHA-256 of the register")
    parser.add_argument("--candidate-sha", required=True, help="Exact candidate commit the evidence ran on")
    parser.add_argument("--evidence", required=True, type=Path, action="append",
                        help="Evidence file with scenario sections (repeatable)")
    parser.add_argument("--out", required=True, type=Path, help="Results file to write")
    args = parser.parse_args(argv)
    if SHA256_RE.fullmatch(args.contract_sha256) is None:
        parser.error("--contract-sha256 must be a lowercase SHA-256 hex digest")
    if GIT_SHA_RE.fullmatch(args.candidate_sha) is None:
        parser.error("--candidate-sha must be a lowercase 40-character Git SHA")
    root = args.repo_root.resolve()

    def relative(path: Path, flag: str) -> str:
        try:
            return path.resolve().relative_to(root).as_posix()
        except ValueError:
            parser.error(f"{flag} {path} is outside --repo-root {root}")

    out = relative(args.out, "--out")
    allowed = evidence_root(out)
    evidence_paths = [relative(path, "--evidence") for path in args.evidence]
    for path, given in zip(evidence_paths, args.evidence):
        if not given.is_file():
            parser.error(f"--evidence {given} is not an existing file")
        if not path.startswith(allowed + "/"):
            parser.error(f"--evidence {given} must be under {allowed}/ next to --out")
    if len(set(evidence_paths)) != len(evidence_paths):
        parser.error("--evidence lists the same file twice")

    try:
        prd_bytes = args.prd.read_bytes()
        contract_bytes = args.contract.read_bytes()
        evidence = [(path, (root / path).read_bytes()) for path in evidence_paths]
        if _sha256(contract_bytes) != args.contract_sha256:
            raise AcceptanceError("contract bytes do not match --contract-sha256")
        contract = _load_json(contract_bytes, "contract")
        all_tests, required_tests, errors = _parse_required_prd_tests(prd_bytes)
    except (AcceptanceError, OSError) as exc:
        print(exc)
        return 1
    if contract.get("prd_sha256") != _sha256(prd_bytes):
        errors.append("contract.prd_sha256 does not match the PRD bytes")
    errors.extend(_contract(contract, all_tests, required_tests)[1])
    if errors:
        print("\n".join(errors))
        return 1

    results, errors, left_out = build(contract, evidence, args.candidate_sha)
    if errors:
        print("\n".join(errors))
        return 1
    for scenario in left_out:
        print(f"no evidence section, left out: {scenario}")
    target = root / out
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(register_bytes(results))
    print(f"built {len(results['results'])} result rows to {out}; {len(left_out)} scenarios left out")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())

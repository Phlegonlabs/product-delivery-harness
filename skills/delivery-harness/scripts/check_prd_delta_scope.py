#!/usr/bin/env python3
"""Check a managed round's mission scope against its bound PRD delta.

Consumer-run planner check documented in
references/contract-and-traceability.md; it is not part of the skill's
Required Verification matrix. Read-only: exits 0 with a short summary,
1 with one line per violation, 2 on unreadable or malformed input.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

from check_document_sync import safe_path
from harness_core import ManifestError, load_plan


DELTA_KIND = re.compile(r"prd[- ]delta\Z", re.IGNORECASE)
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SEPARATOR_CELL = re.compile(r"-{3,}\Z")
CHANGES = ("new", "revised", "retired")
REQUIRED_YES = "(Required: Yes)"
TEST_ID = re.compile(r"TEST-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")
HEADING = "## Changed Requirements"
TEST_OBLIGATIONS_HEADING = "## Test Obligations"
PRD_SOURCE_KINDS = {"prd", "product requirement", "product requirements"}
DEFAULT_PRD_LOCATION = "docs/product/PRD.md"


def parse_changed_requirements(text: str) -> dict[str, Any]:
    """Parse the delta's Changed Requirements table into ID sets."""
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line.strip() == HEADING]
    if len(starts) != 1:
        raise ValueError("delta must contain exactly one '## Changed Requirements' heading")
    rows = []
    for line in lines[starts[0] + 1:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if not stripped.startswith("|"):
            if rows:
                break
            continue
        rows.append([cell.strip() for cell in stripped.strip("|").split("|")])
    if not rows or [cell.lower() for cell in rows[0][:2]] != ["id", "change"]:
        raise ValueError("Changed Requirements table must start with | ID | Change | columns")
    if len(rows[0]) < 5:
        raise ValueError("Changed Requirements table must have the | ID | Change | Before | After | TEST IDs | columns")
    parsed: dict[str, Any] = {change: set() for change in CHANGES}
    parsed["required_yes"] = set()
    parsed["test_ids"] = {}
    for cells in rows[1:]:
        if cells and SEPARATOR_CELL.fullmatch(cells[0]):
            continue
        if len(cells) < 5 or not all(cells[:2]):
            raise ValueError("Changed Requirements rows need ID, Change and TEST IDs cells")
        requirement, change = cells[0], cells[1].lower()
        if change not in CHANGES:
            raise ValueError(f"Changed Requirements Change value must be new, revised or retired: {cells[1]!r}")
        parsed[change].add(requirement)
        if change in {"new", "revised"}:
            parsed["test_ids"][requirement] = sorted(set(TEST_ID.findall(cells[4])))
            if REQUIRED_YES in cells[4]:
                parsed["required_yes"].add(requirement)
    return parsed


def parse_test_obligations(text: str) -> dict[str, bool]:
    """Parse the canonical PRD's Test Obligations table into required flags."""
    lines = text.splitlines()
    starts = [
        index for index, line in enumerate(lines)
        if line.strip() == TEST_OBLIGATIONS_HEADING
    ]
    if len(starts) != 1:
        raise ValueError("canonical PRD must contain exactly one '## Test Obligations' heading")
    rows = []
    for line in lines[starts[0] + 1:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if not stripped.startswith("|"):
            if rows:
                break
            continue
        rows.append([cell.strip() for cell in stripped.strip("|").split("|")])
    if (
        not rows
        or len(rows[0]) < 4
        or rows[0][0].lower() != "test id"
        or rows[0][3].lower() != "required"
    ):
        raise ValueError(
            "Test Obligations table must start with | TEST ID | Obligation | Test type | Required | columns"
        )
    obligations: dict[str, bool] = {}
    for cells in rows[1:]:
        if cells and SEPARATOR_CELL.fullmatch(cells[0]):
            continue
        if len(cells) < 4 or not cells[0]:
            raise ValueError("Test Obligations rows need TEST ID and Required cells")
        obligations[cells[0]] = cells[3].lower() == "yes"
    return obligations


def canonical_prd_location(plan: dict[str, Any]) -> str:
    """Return the frozen PRD location declared by the PLAN or the default path."""
    for source in plan.get("sources") or []:
        if not isinstance(source, dict):
            continue
        kind = re.sub(r"[-_]+", " ", str(source.get("kind", ""))).strip().lower()
        if kind not in PRD_SOURCE_KINDS:
            continue
        location = source.get("location")
        if isinstance(location, str) and location.strip() and "://" not in location:
            return location.strip()
    return DEFAULT_PRD_LOCATION


def trace_entries(plan: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (location, trace ID) for every mission and task trace entry."""
    entries = []
    for mission in plan.get("missions", []):
        if not isinstance(mission, dict):
            continue
        mission_id = str(mission.get("id", "<mission>"))
        for trace_id in mission.get("trace_ids") or []:
            if isinstance(trace_id, str):
                entries.append((mission_id, trace_id))
        for task in mission.get("tasks", []):
            if not isinstance(task, dict):
                continue
            task_id = f"{mission_id}/{task.get('id', '<task>')}"
            for trace_id in task.get("trace_ids") or []:
                if isinstance(trace_id, str):
                    entries.append((task_id, trace_id))
    return entries


def task_carried_ids(plan: dict[str, Any]) -> set[str]:
    """Return the trace IDs carried by at least one task."""
    carried = set()
    for mission in plan.get("missions", []):
        if not isinstance(mission, dict):
            continue
        for task in mission.get("tasks", []):
            if not isinstance(task, dict):
                continue
            for trace_id in task.get("trace_ids") or []:
                if isinstance(trace_id, str):
                    carried.add(trace_id)
    return carried


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="Path to PLAN.md")
    parser.add_argument("--repo-root", required=True, help="Repository root of the delta source location")
    args = parser.parse_args(argv)
    try:
        plan = load_plan(args.plan)
    except (OSError, ManifestError) as exc:
        print(f"invalid plan: {exc}")
        return 2
    sources = [
        source for source in plan.get("sources", [])
        if isinstance(source, dict) and DELTA_KIND.fullmatch(str(source.get("kind", "")).strip())
    ]
    if not sources:
        print("no prd-delta source")
        return 0
    if len(sources) > 1:
        print(f"plan declares {len(sources)} prd-delta sources; expected exactly one")
        return 2
    source = sources[0]
    violations: list[str] = []
    expected_sha = source.get("content_sha256")
    proceed = True
    if not isinstance(expected_sha, str) or SHA256.fullmatch(expected_sha) is None:
        violations.append("prd-delta source content_sha256 must be a lowercase SHA-256 digest")
        proceed = False
    location = source.get("location")
    if not isinstance(location, str) or not location.strip():
        violations.append("prd-delta source requires a location path")
        print("\n".join(violations))
        return 1
    root = Path(args.repo_root).resolve()
    try:
        delta_path = safe_path(root, location)
    except ValueError:
        violations.append(
            f"prd-delta source location must be a relative path inside the repository root: {location}"
        )
        print("\n".join(violations))
        return 1
    try:
        delta_bytes = delta_path.read_bytes()
    except OSError as exc:
        print(f"cannot read prd-delta {location} under --repo-root: {exc}")
        return 2
    if proceed:
        actual_sha = hashlib.sha256(delta_bytes).hexdigest()
        if actual_sha != expected_sha:
            violations.append(
                f"prd-delta {location}: bytes do not match content_sha256 {expected_sha}"
            )
            proceed = False
    if proceed:
        try:
            requirements = parse_changed_requirements(delta_bytes.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError) as exc:
            print(f"invalid prd-delta {location}: {exc}")
            return 2
        obligations: dict[str, bool] = {}
        if any(requirements["test_ids"].values()):
            prd_location = canonical_prd_location(plan)
            try:
                prd_path = safe_path(root, prd_location)
            except ValueError as exc:
                print(f"cannot read canonical PRD {prd_location} under --repo-root: {exc}")
                return 2
            try:
                prd_text = prd_path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeDecodeError) as exc:
                print(f"cannot read canonical PRD {prd_location} under --repo-root: {exc}")
                return 2
            try:
                obligations = parse_test_obligations(prd_text)
            except ValueError as exc:
                print(f"invalid canonical PRD {prd_location}: {exc}")
                return 2
        foundation = plan.get("foundation_trace_ids")
        foundation_ids: set[str] = set()
        if foundation is not None:
            if not isinstance(foundation, list) or not all(
                isinstance(item, str) and item.strip() for item in foundation
            ):
                violations.append("plan.foundation_trace_ids must be an array of non-empty strings")
            else:
                foundation_ids = set(foundation)
        allowed = requirements["new"] | requirements["revised"] | foundation_ids
        for owner, trace_id in trace_entries(plan):
            if trace_id in requirements["retired"]:
                violations.append(f"{owner}: trace {trace_id} is retired by the bound PRD delta")
            elif trace_id not in allowed:
                violations.append(
                    f"{owner}: trace {trace_id} is not a new/revised ID of the bound PRD delta "
                    "and is not listed in foundation_trace_ids"
                )
        required_yes = set(requirements["required_yes"])
        for requirement in sorted(requirements["new"] | requirements["revised"]):
            for test_id in requirements["test_ids"].get(requirement, []):
                if test_id not in obligations:
                    violations.append(
                        f"delta requirement {requirement} lists TEST {test_id} "
                        "with no row in the canonical PRD Test Obligations"
                    )
                elif obligations[test_id]:
                    required_yes.add(requirement)
        carrying = task_carried_ids(plan)
        for requirement in sorted(required_yes):
            if requirement not in carrying:
                violations.append(
                    f"delta requirement {requirement} carries a Required-Yes TEST but has no task"
                )
        if not violations:
            counts = ", ".join(
                f"{len(requirements[change])} {change}" for change in CHANGES
            )
            print(
                f"prd-delta {location}: {counts}; {len(foundation_ids)} foundation IDs; "
                f"{len(trace_entries(plan))} trace entries; scope ok"
            )
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())

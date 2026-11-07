#!/usr/bin/env python3
"""Check that a PRD's feature files and its Test Obligations cover each other.

Every scenario's @TEST tag names a Test Obligations row, and every
`Required: Yes` row whose Test type is E2E, integration or contract has a
scenario. Exit 0 on PASS, 1 on findings, 2 on bad arguments.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Module-attribute access only: check_product_package imports this module too,
# so nothing here may read either module at import time.
import check_product_package as cpp
import program_package
from contract_utils import safe_read_text
from feature_file import FeatureError, parse_feature_text

SCENARIO_TYPES = re.compile(r"(?<![\w-])(?:e2e|integration|contract)(?![\w-])", re.IGNORECASE)


def obligation_rows(prd_text: str) -> dict[str, tuple[str, ...]]:
    """TEST ID -> full-width row of the PRD's Test Obligations table."""

    section = cpp._section(prd_text, "## Test Obligations") or ""
    rows = cpp._find_table(section, cpp.TEST_OBLIGATIONS_HEADER) or []
    width = len(cpp.TEST_OBLIGATIONS_HEADER)
    return {row[0].strip().upper(): row for row in rows if len(row) == width}


def needs_scenario(row: tuple[str, ...]) -> bool:
    return row[3].strip().casefold() == "yes" and SCENARIO_TYPES.search(row[2]) is not None


def coverage_problems(rows: dict[str, tuple[str, ...]], features_dir: Path) -> list[str]:
    """Findings for every feature file in `features_dir` against these Test Obligations rows."""

    if not features_dir.is_dir():
        return [f"features directory not found: {features_dir}"]
    problems: list[str] = []
    covered: set[str] = set()
    first_seen: dict[str, str] = {}
    for path in sorted((entry for entry in features_dir.iterdir() if entry.is_file()), key=lambda entry: entry.name):
        label = path.as_posix()
        if path.name != path.name.lower() or not path.name.endswith(".feature"):
            problems.append(f"{label}: feature file names are lowercase and end in .feature")
            if not path.name.endswith(".feature"):
                continue
        text, error = safe_read_text(path)
        if error is not None:
            problems.append(error)
            continue
        try:
            feature = parse_feature_text(text.removeprefix("﻿"), label)
        except FeatureError as exc:
            problems.append(str(exc))
            continue
        for scenario in feature.scenarios:
            where = f"{label}:{scenario.line}"
            if scenario.test_id not in rows:
                problems.append(f"{where}: {scenario.test_id} is not a Test Obligations row")
            covered.add(scenario.test_id)
            if scenario.scenario_id in first_seen:
                problems.append(
                    f"{where}: duplicate scenario id {scenario.scenario_id} "
                    f"(first at {first_seen[scenario.scenario_id]})"
                )
            else:
                first_seen[scenario.scenario_id] = where
    for test_id, row in sorted(rows.items()):
        if needs_scenario(row) and test_id not in covered:
            problems.append(f"{test_id} is a required {row[2].strip()} obligation with no scenario")
    return problems


def feature_coverage_problems(
    prd_text: str, features_dir: Path, *, module_prds: tuple[str, ...] = ()
) -> list[str]:
    """Coverage findings for one package; a program passes its module PRDs too."""

    rows = obligation_rows(prd_text)
    for module_prd in module_prds:
        rows.update(obligation_rows(module_prd))
    return coverage_problems(rows, features_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prd", required=True, type=Path)
    parser.add_argument("--features", required=True, type=Path)
    args = parser.parse_args(argv)
    prd_text, error = safe_read_text(args.prd)
    if error is not None:
        print(f"FAIL {error}", file=sys.stderr)
        return 2
    if not args.features.is_dir():
        print(f"FAIL features directory not found: {args.features}", file=sys.stderr)
        return 2
    module_prds: tuple[str, ...] = ()
    if cpp._delivery_profile(prd_text) == "program":
        program = program_package.load_program(args.prd.parent)
        module_prds = tuple(prd for prd, _ in program.texts.values())
    problems = feature_coverage_problems(prd_text, args.features, module_prds=module_prds)
    if not obligation_rows(prd_text):
        problems.insert(0, f"{args.prd}: no Test Obligations rows")
    for problem in problems:
        print(f"FAIL {problem}", file=sys.stderr)
    if problems:
        return 1
    print("PASS feature files cover every required E2E, integration and contract Test Obligation")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())

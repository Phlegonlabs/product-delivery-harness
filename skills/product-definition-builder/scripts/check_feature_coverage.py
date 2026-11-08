#!/usr/bin/env python3
"""Check that a PRD's feature files and its Test Obligations cover each other.

Every scenario's @TEST tag names a Test Obligations row, and every
`Required: Yes` row has a scenario, because the delivery-acceptance register
freezes one scenario per Required TEST. Exit 0 on PASS, 1 on findings, 2 on
bad arguments.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Module-attribute access only: check_product_package imports this module too,
# so nothing here may read either module at import time.
import check_product_package as cpp
import eval_policy
import program_package
from contract_utils import safe_read_text
from feature_file import Feature, FeatureError, parse_feature_text

def obligation_rows(prd_text: str) -> dict[str, tuple[str, ...]]:
    """TEST ID -> full-width row of the PRD's Test Obligations table."""

    section = cpp._section(prd_text, "## Test Obligations") or ""
    rows = cpp._find_table(section, cpp.TEST_OBLIGATIONS_HEADER) or []
    width = len(cpp.TEST_OBLIGATIONS_HEADER)
    return {row[0].strip().upper(): row for row in rows if len(row) == width}


def needs_scenario(row: tuple[str, ...]) -> bool:
    return row[3].strip().casefold() == "yes"


def read_features(features_dir: Path) -> tuple[list[Feature], list[str]]:
    """The feature files in `features_dir` by name, and findings for files that fail to read or parse."""

    features: list[Feature] = []
    problems: list[str] = []
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
        features.append(feature)
    return features, problems


def coverage_problems(
    rows: dict[str, tuple[str, ...]], features_dir: Path, *, checked: set[str] | None = None
) -> list[str]:
    """Findings for every feature file in `features_dir` against these Test Obligations rows.

    `checked` limits which rows need a scenario; any row may be named by one.
    """

    if not features_dir.is_dir():
        return [f"features directory not found: {features_dir}"]
    features, problems = read_features(features_dir)
    covered: set[str] = set()
    first_seen: dict[str, str] = {}
    for feature in features:
        for scenario in feature.scenarios:
            where = f"{feature.path}:{scenario.line}"
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
        if (checked is None or test_id in checked) and needs_scenario(row) and test_id not in covered:
            problems.append(f"{test_id} is a required {row[2].strip()} obligation with no scenario")
    return problems


def feature_coverage_problems(prd_text: str, features_dir: Path) -> list[str]:
    """Coverage findings for a standard or mvp package."""

    return coverage_problems(obligation_rows(prd_text), features_dir)


def eval_scenario_problems(prd_text: str, features_dir: Path) -> list[str]:
    """Each `<TEST-ID>/<slug>` scenario id in the PRD's eval policy needs that
    scenario under that TEST in the feature files. Other ids are left alone."""

    try:
        policy = eval_policy.parse_eval_policy(prd_text)
    except eval_policy.PolicyError:
        return []  # validate_eval_policy reports it
    if policy is None or not features_dir.is_dir():
        return []
    features, _ = read_features(features_dir)  # coverage_problems reports unreadable files
    found = {
        scenario.scenario_id: f"{feature.path}:{scenario.line}"
        for feature in features
        for scenario in feature.scenarios
    }
    problems: list[str] = []
    for purpose in ("quality", "handoff"):
        entry = policy.get(purpose)
        scenario_id = entry.get("scenario_id") if isinstance(entry, dict) else None
        match = eval_policy.FEATURE_SCENARIO_ID.fullmatch(scenario_id) if isinstance(scenario_id, str) else None
        if match is None or scenario_id in found:
            continue
        slug = scenario_id.split("/", 1)[1]
        elsewhere = [
            f"@{other.split('/', 1)[0]} ({where})" for other, where in found.items() if other.split("/", 1)[1] == slug
        ]
        if elsewhere:
            problems.append(
                f"eval-policy {purpose} scenario {scenario_id} is tagged {', '.join(elsewhere)}; "
                f"expected @{match.group(1)}"
            )
        else:
            problems.append(
                f"eval-policy {purpose} scenario {scenario_id} is not in the feature files; "
                f"expected a scenario tagged @{match.group(1)}"
            )
    return problems


def program_coverage_problems(
    program: program_package.Program, features_dir: Path, *, module: str | None = None
) -> list[str]:
    """Coverage findings for a program: a scenario may name any module's TEST;
    `module` limits the required rows to the program's and that module's."""

    rows = obligation_rows(program.prd)
    checked = set(rows)
    for module_id, (prd, _) in program.texts.items():
        module_rows = obligation_rows(prd)
        rows.update(module_rows)
        if module in (None, module_id):
            checked.update(module_rows)
    return coverage_problems(rows, features_dir, checked=checked)


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
    if cpp._delivery_profile(prd_text) == "program":
        problems = program_coverage_problems(program_package.load_program(args.prd.parent), args.features)
    else:
        problems = feature_coverage_problems(prd_text, args.features)
    if not obligation_rows(prd_text):
        problems.insert(0, f"{args.prd}: no Test Obligations rows")
    for problem in problems:
        print(f"FAIL {problem}", file=sys.stderr)
    if problems:
        return 1
    print("PASS feature files cover every Required Test Obligation")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())

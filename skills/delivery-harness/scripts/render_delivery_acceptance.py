#!/usr/bin/env python3
"""Render the delivery-acceptance register from the PRD feature files.

Every scenario in `--features <dir>/*.feature` joins one run profile
(`acceptance-profile/1`) to become one `delivery-acceptance/1` scenario that
check_delivery_acceptance.py accepts. Writes only `--out`. Exits 0 on
success, 1 with one line per finding, 2 on bad arguments.

`--check` renders in memory and writes nothing. It exits 0 when `--out`
holds exactly the rendered bytes, and 1 naming the first drifted scenario
with its feature `path:line`.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from check_delivery_acceptance import (
    AUTH_MODES, CONTRACT_SCHEMA, ENVIRONMENTS, PLATFORMS, _build, _contract, _fixtures,
)
from delivery_acceptance_execution import concrete_text
from delivery_acceptance_io import AcceptanceError, _load_json, _parse_required_prd_tests, _sha256


PROFILE_SCHEMA = "acceptance-profile/1"
PROFILE_KEYS = {"schema", "platform", "auth_mode", "environment", "build", "execution", "fixtures"}
PROFILE_EXECUTION_KEYS = {
    "target", "device", "os", "persona", "initial_data", "expected_side_effects", "dependency_mode",
}
PROFILE_PERSONA_KEYS = {"tenant", "account_state"}
# A scenario tag `@<tag>:<value>` overrides one register field.
TAG_FIELDS = {
    "platform": ("platform", PLATFORMS),
    "auth": ("auth_mode", AUTH_MODES),
    "env": ("environment", ENVIRONMENTS),
}


def load_feature_reader() -> Any:
    """Load the shared reader from product-definition-builder next to this skill."""

    path = Path(__file__).resolve().parents[2] / "product-definition-builder" / "scripts" / "feature_file.py"
    name = "_harness_sibling_feature_file"
    spec = importlib.util.spec_from_file_location(name, path)
    if not path.is_file() or spec is None or spec.loader is None:
        raise AcceptanceError(
            f"cannot load the feature-file reader {path}; install "
            "product-definition-builder next to delivery-harness"
        )
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves the module by name while the class body runs.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def read_feature_dir(directory: Path, reader: Any) -> tuple[list[Any], list[str]]:
    """Parse every `*.feature` file in one directory, in name order."""

    features: list[Any] = []
    errors: list[str] = []
    for path in sorted(directory.glob("*.feature")):
        label = path.as_posix()
        try:
            features.append(reader.parse_feature_text(path.read_text(encoding="utf-8"), label))
        except UnicodeDecodeError:
            errors.append(f"{label}: not UTF-8")
        except OSError as exc:
            errors.append(f"{label}: cannot read ({exc})")
        except reader.FeatureError as exc:
            errors.append(str(exc))
    return features, errors


def profile_errors(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(profile) != PROFILE_KEYS:
        return [f"profile keys must be exactly {sorted(PROFILE_KEYS)}"]
    if profile["schema"] != PROFILE_SCHEMA:
        errors.append(f"profile.schema must be {PROFILE_SCHEMA!r}")
    for field, allowed in (("platform", PLATFORMS), ("auth_mode", AUTH_MODES),
                           ("environment", ENVIRONMENTS)):
        if not isinstance(profile[field], str) or profile[field] not in allowed:
            errors.append(f"profile.{field} must be one of {sorted(allowed)}")
    _build(profile["build"], "profile.build", profile["platform"], profile["environment"], errors)
    _fixtures(profile["fixtures"], profile["environment"], "profile.fixtures", errors)
    execution = profile["execution"]
    if not isinstance(execution, dict) or set(execution) != PROFILE_EXECUTION_KEYS:
        errors.append(f"profile.execution keys must be exactly {sorted(PROFILE_EXECUTION_KEYS)}")
        return errors
    for key in sorted(PROFILE_EXECUTION_KEYS - {"persona"}):
        if not concrete_text(execution[key]):
            errors.append(f"profile.execution.{key} must be concrete non-placeholder text")
    persona = execution["persona"]
    if not isinstance(persona, dict) or set(persona) != PROFILE_PERSONA_KEYS:
        errors.append(f"profile.execution.persona keys must be exactly {sorted(PROFILE_PERSONA_KEYS)}")
    else:
        for key in sorted(PROFILE_PERSONA_KEYS):
            if not concrete_text(persona[key]):
                errors.append(f"profile.execution.persona.{key} must be concrete non-placeholder text")
    return errors


def scenario_entry(feature: Any, scenario: Any, profile: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    """Map one scenario onto one register scenario; findings name `path:line`."""

    where = f"{feature.path}:{scenario.line}"
    for step in scenario.steps:
        if not concrete_text(step.text):
            errors.append(f"{feature.path}:{step.line}: step text must be concrete, not a placeholder")
    fields = {"platform": profile["platform"], "auth_mode": profile["auth_mode"],
              "environment": profile["environment"]}
    for tag, value in scenario.profile.items():
        field, allowed = TAG_FIELDS[tag]
        if value not in allowed:
            errors.append(f"{where}: @{tag}:{value} must be one of {sorted(allowed)}")
        fields[field] = value
    givens = [step.text for step in scenario.steps_for("Given")]
    if not givens:
        errors.append(f"{where}: scenario {scenario.name!r} needs a Given step naming the persona")
        givens = [""]
    run = profile["execution"]
    return {
        "id": scenario.scenario_id,
        **fields,
        "build": dict(profile["build"]),
        "execution": {
            "target": run["target"],
            "device": run["device"],
            "os": run["os"],
            "persona": {"role": givens[0], **run["persona"]},
            "initial_data": "; ".join(givens[1:]) or run["initial_data"],
            "actions": [step.text for step in scenario.steps_for("When")],
            "assertions": {
                f"ASSERT-{number:03d}": step.text
                for number, step in enumerate(scenario.steps_for("Then"), start=1)
            },
            "expected_side_effects": run["expected_side_effects"],
            "dependency_mode": run["dependency_mode"],
        },
        "fixtures": copy.deepcopy(profile["fixtures"]),
    }


def render(prd_bytes: bytes, features: list[Any], profile: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors = profile_errors(profile)
    try:
        all_tests, required_tests, prd_errors = _parse_required_prd_tests(prd_bytes)
    except AcceptanceError as exc:
        return {}, errors + [f"PRD: {exc}"]
    errors.extend(f"PRD: {error}" for error in prd_errors)
    if errors:
        return {}, errors

    grouped: dict[str, list[dict[str, Any]]] = {}
    first_seen: dict[str, str] = {}
    for feature in features:
        for scenario in feature.scenarios:
            where = f"{feature.path}:{scenario.line}"
            if scenario.test_id not in all_tests:
                errors.append(f"{where}: {scenario.test_id} is not a TEST ID in the PRD")
            if scenario.scenario_id in first_seen:
                errors.append(f"{where}: duplicate scenario id {scenario.scenario_id} (first at {first_seen[scenario.scenario_id]})")
                continue
            first_seen[scenario.scenario_id] = where
            grouped.setdefault(scenario.test_id, []).append(scenario_entry(feature, scenario, profile, errors))
    for test_id in sorted(required_tests - set(grouped)):
        errors.append(f"required {test_id} has no scenario in the feature files")
    if errors:
        return {}, errors

    register = {
        "schema": CONTRACT_SCHEMA,
        "prd_sha256": _sha256(prd_bytes),
        "tests": [{"test_id": test_id, "scenarios": grouped[test_id]} for test_id in sorted(grouped)],
    }
    _, contract_errors = _contract(register, all_tests, required_tests)
    return register, contract_errors


def register_bytes(register: dict[str, Any]) -> bytes:
    return (json.dumps(register, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _scenarios_by_id(register: Any) -> dict[str, tuple[Any, Any]]:
    """Map scenario id to (TEST ID, scenario); a malformed register maps to nothing."""

    found: dict[str, tuple[Any, Any]] = {}
    tests = register.get("tests") if isinstance(register, dict) else None
    for test in tests if isinstance(tests, list) else []:
        scenarios = test.get("scenarios") if isinstance(test, dict) else None
        for scenario in scenarios if isinstance(scenarios, list) else []:
            if isinstance(scenario, dict) and isinstance(scenario.get("id"), str):
                found.setdefault(scenario["id"], (test.get("test_id"), scenario))
    return found


def drift(expected: dict[str, Any], existing: bytes, where: dict[str, str], label: str) -> str | None:
    """Name the first difference between the rendered register and the file."""

    rendered = register_bytes(expected)
    if existing == rendered:
        return None
    if existing.replace(b"\r\n", b"\n") == rendered:
        return f"{label}: differs only in line endings; check it out byte for byte (-text) and re-render"
    try:
        current = json.loads(existing.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return f"{label}: is not valid UTF-8 JSON; re-render it"
    have = _scenarios_by_id(current)
    for scenario_id, entry in _scenarios_by_id(expected).items():
        if scenario_id not in have:
            return f"{label}: scenario {scenario_id} ({where[scenario_id]}) is missing; re-render it"
        if have[scenario_id] != entry:
            return f"{label}: scenario {scenario_id} ({where[scenario_id]}) differs from its feature file; re-render it"
    extra = sorted(set(have) - set(where))
    if extra:
        return f"{label}: scenario {extra[0]} is in no feature file; re-render it"
    for key in sorted(expected):
        if not isinstance(current, dict) or current.get(key) != expected[key]:
            return f"{label}: {key} differs from the rendered register; re-render it"
    return f"{label}: differs from the rendered bytes; re-render it"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prd", required=True, type=Path, help="Path to PRD.md")
    parser.add_argument("--features", required=True, type=Path, help="Directory of *.feature files")
    parser.add_argument("--profile", required=True, type=Path, help="Run profile JSON (acceptance-profile/1)")
    parser.add_argument("--out", required=True, type=Path, help="Register to write")
    parser.add_argument("--check", action="store_true",
                        help="Compare a fresh render with --out without writing; exit 1 on drift")
    args = parser.parse_args(argv)
    for flag, path, is_dir in (("--prd", args.prd, False), ("--features", args.features, True),
                               ("--profile", args.profile, False)):
        if not (path.is_dir() if is_dir else path.is_file()):
            parser.error(f"{flag} {path} is not an existing {'directory' if is_dir else 'file'}")

    try:
        reader = load_feature_reader()
        prd_bytes = args.prd.read_bytes()
        profile = _load_json(args.profile.read_bytes(), "profile")
    except (AcceptanceError, OSError) as exc:
        print(exc)
        return 1
    features, errors = read_feature_dir(args.features, reader)
    if not features and not errors:
        errors.append(f"{args.features.as_posix()}: no *.feature files")
    if not errors:
        register, errors = render(prd_bytes, features, profile)
    if errors:
        print("\n".join(errors))
        return 1

    count = sum(len(test["scenarios"]) for test in register["tests"])
    if args.check:
        label = args.out.as_posix()
        try:
            existing = args.out.read_bytes()
        except OSError as exc:
            print(f"{label}: cannot read ({exc})")
            return 1
        where = {
            scenario.scenario_id: f"{feature.path}:{scenario.line}"
            for feature in features for scenario in feature.scenarios
        }
        finding = drift(register, existing, where, label)
        if finding:
            print(finding)
            return 1
        print(f"{label} matches the {count} scenarios rendered from the feature files")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(register_bytes(register))
    print(f"rendered {count} scenarios under {len(register['tests'])} TEST IDs to {args.out.as_posix()}")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())

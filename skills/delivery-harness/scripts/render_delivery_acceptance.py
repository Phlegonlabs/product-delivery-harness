#!/usr/bin/env python3
"""Render the delivery-acceptance register from the PRD feature files.

Every scenario in `--features <dir>/*.feature` joins the run profile
(`acceptance-profile/1`) to become one `delivery-acceptance/1` scenario that
check_delivery_acceptance.py accepts. The profile's optional `assign` map
picks one of its named `variants` for a scenario id or a TEST ID (the
scenario id wins); other scenarios use the top-level profile, and
`@platform`, `@auth` and `@env` tags override either. When the PRD's
eval-policy is required, the Then steps of its quality and handoff scenarios
take the fixed eval assertion keys in order instead of ASSERT-NNN.

Writes only `--out`. Exits 0 on success, 1 with one line per finding, 2 on
bad arguments.

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
PROFILE_BODY_KEYS = PROFILE_KEYS - {"schema"}
PROFILE_OPTIONAL_KEYS = {"variants", "assign"}
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


def body_errors(body: dict[str, Any], label: str) -> list[str]:
    """Check one profile body: the top-level profile or one variant."""

    errors: list[str] = []
    for field, allowed in (("platform", PLATFORMS), ("auth_mode", AUTH_MODES),
                           ("environment", ENVIRONMENTS)):
        if not isinstance(body[field], str) or body[field] not in allowed:
            errors.append(f"{label}.{field} must be one of {sorted(allowed)}")
    _build(body["build"], f"{label}.build", body["platform"], body["environment"], errors)
    _fixtures(body["fixtures"], body["environment"], f"{label}.fixtures", errors)
    execution = body["execution"]
    if not isinstance(execution, dict) or set(execution) != PROFILE_EXECUTION_KEYS:
        errors.append(f"{label}.execution keys must be exactly {sorted(PROFILE_EXECUTION_KEYS)}")
        return errors
    for key in sorted(PROFILE_EXECUTION_KEYS - {"persona"}):
        if not concrete_text(execution[key]):
            errors.append(f"{label}.execution.{key} must be concrete non-placeholder text")
    persona = execution["persona"]
    if not isinstance(persona, dict) or set(persona) != PROFILE_PERSONA_KEYS:
        errors.append(f"{label}.execution.persona keys must be exactly {sorted(PROFILE_PERSONA_KEYS)}")
    else:
        for key in sorted(PROFILE_PERSONA_KEYS):
            if not concrete_text(persona[key]):
                errors.append(f"{label}.execution.persona.{key} must be concrete non-placeholder text")
    return errors


def profile_errors(profile: dict[str, Any]) -> list[str]:
    if not PROFILE_KEYS <= set(profile) <= PROFILE_KEYS | PROFILE_OPTIONAL_KEYS:
        return [f"profile keys must be exactly {sorted(PROFILE_KEYS)}, optionally with variants and assign"]
    errors: list[str] = []
    if profile["schema"] != PROFILE_SCHEMA:
        errors.append(f"profile.schema must be {PROFILE_SCHEMA!r}")
    errors.extend(body_errors(profile, "profile"))
    variants = profile.get("variants", {})
    if not isinstance(variants, dict):
        errors.append("profile.variants must map a variant name to a profile body")
        variants = {}
    for name, body in sorted(variants.items()):
        label = f"profile.variants.{name}"
        if not concrete_text(name):
            errors.append(f"{label}: the variant name must be concrete text")
        if not isinstance(body, dict) or set(body) != PROFILE_BODY_KEYS:
            errors.append(f"{label} keys must be exactly {sorted(PROFILE_BODY_KEYS)}")
        else:
            errors.extend(body_errors(body, label))
    assign = profile.get("assign", {})
    if not isinstance(assign, dict):
        errors.append("profile.assign must map a scenario id or TEST ID to a variant name")
    else:
        for key, name in sorted(assign.items()):
            if not isinstance(name, str) or name not in variants:
                errors.append(f"profile.assign.{key} names unknown variant {name!r}")
    return errors


def eval_scenario_keys(prd_bytes: bytes) -> dict[tuple[str, str], tuple[str, tuple[str, ...]]]:
    """Map a required eval policy's quality and handoff scenarios to their fixed keys."""

    try:
        import eval_verification
    except ImportError as exc:
        raise AcceptanceError(f"cannot load the eval policy parser: {exc}") from exc
    ep = eval_verification.ep
    try:
        policy = ep.parse_eval_policy(prd_bytes.decode("utf-8"))
        if policy is None:
            return {}
        ep.validate_policy_shape(policy)
    except ep.PolicyError as exc:
        raise AcceptanceError(f"eval-policy: {exc}") from exc
    if policy["applicability"] != "required":
        return {}
    return {
        (policy[purpose]["test_id"], policy[purpose]["scenario_id"]): (purpose, keys)
        for purpose, keys in (("quality", eval_verification.QUALITY_KEYS),
                              ("handoff", eval_verification.HANDOFF_KEYS))
    }


def scenario_entry(
    feature: Any, scenario: Any, profile: dict[str, Any], errors: list[str],
    eval_keys: tuple[str, tuple[str, ...]] | None = None,
) -> dict[str, Any]:
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
    thens = scenario.steps_for("Then")
    keys = [f"ASSERT-{number:03d}" for number in range(1, len(thens) + 1)]
    if eval_keys is not None:
        purpose, keys = eval_keys
        if len(thens) != len(keys):
            errors.append(f"{where}: eval {purpose} scenario needs exactly {len(keys)} Then steps, "
                          f"one per {', '.join(keys)} in that order")
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
            "assertions": {key: step.text for key, step in zip(keys, thens)},
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
    try:
        eval_keys = eval_scenario_keys(prd_bytes)
    except AcceptanceError as exc:
        errors.append(f"PRD: {exc}")
    if errors:
        return {}, errors

    grouped: dict[str, list[dict[str, Any]]] = {}
    first_seen: dict[str, str] = {}
    assign = profile.get("assign", {})
    for feature in features:
        for scenario in feature.scenarios:
            where = f"{feature.path}:{scenario.line}"
            if scenario.test_id not in all_tests:
                errors.append(f"{where}: {scenario.test_id} is not a TEST ID in the PRD")
            if scenario.scenario_id in first_seen:
                errors.append(f"{where}: duplicate scenario id {scenario.scenario_id} (first at {first_seen[scenario.scenario_id]})")
                continue
            first_seen[scenario.scenario_id] = where
            variant = assign.get(scenario.scenario_id, assign.get(scenario.test_id))
            body = profile if variant is None else profile["variants"][variant]
            grouped.setdefault(scenario.test_id, []).append(scenario_entry(
                feature, scenario, body, errors, eval_keys.get((scenario.test_id, scenario.scenario_id))))
    for test_id in sorted(required_tests - set(grouped)):
        errors.append(f"required {test_id} has no scenario in the feature files")
    for (test_id, scenario_id), (purpose, _) in sorted(eval_keys.items()):
        if scenario_id not in first_seen:
            errors.append(f"PRD: eval-policy {purpose} scenario {scenario_id} ({test_id}) is not a scenario in the feature files")
    for key in sorted(set(assign) - set(first_seen) - set(grouped)):
        errors.append(f"profile.assign.{key} matches no scenario id or TEST ID in the feature files")
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

#!/usr/bin/env python3
"""Self-contained validation for a frozen design-system Markdown/JSON pair."""

from __future__ import annotations

import json
import math
import re
from typing import Any


BEGIN_MARKER = "<!-- BEGIN GENERATED DESIGN SYSTEM CONTRACT -->"
END_MARKER = "<!-- END GENERATED DESIGN SYSTEM CONTRACT -->"
CONTRACT_FIELDS = (
    "schema",
    "product",
    "platform",
    "stylingMechanism",
    "enforcement",
    "tokenSources",
    "primitiveSources",
    "viewports",
    "sizeClasses",
    "tokens",
    "primitives",
    "productComponents",
    "signatureRules",
    "motionVariants",
    "stateMatrix",
)
GENERATED_BLOCK_RE = re.compile(
    rf"{re.escape(BEGIN_MARKER)}\s*```json\s*(.*?)\s*```\s*{re.escape(END_MARKER)}",
    re.DOTALL,
)
PLACEHOLDER_RE = re.compile(r"^<.*>$", re.DOTALL)
DS_COMPONENT_ID_RE = re.compile(r"^DS-COMP-[0-9]+$")
DS_PRIMITIVE_ID_RE = re.compile(r"^DS-[A-Z]+-[0-9]+$")
DS_RULE_ID_RE = re.compile(r"^DS-(?:[A-Z]+-)?[0-9]+$")
DS_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])DS-(?:[A-Z]+-)?[0-9]+(?![A-Za-z0-9_-])"
)
DS_LIKE_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])DS-[A-Za-z0-9_-]+(?![A-Za-z0-9_-])"
)


def is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER_RE.match(value.strip()))


def contract_inventory(registry: dict[str, Any]) -> dict[str, Any]:
    return {key: registry[key] for key in CONTRACT_FIELDS if key in registry}


def generated_contract_block(registry: dict[str, Any]) -> str:
    payload = json.dumps(
        contract_inventory(registry),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    return f"{BEGIN_MARKER}\n```json\n{payload}\n```\n{END_MARKER}"


def _string_list(
    problems: list[str], path: str, value: Any, *, nonempty: bool
) -> None:
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        qualifier = "non-empty " if nonempty else ""
        problems.append(
            f"design-system.json {path} must be a {qualifier}list of strings"
        )


def validate_design_system_registry(registry: dict[str, Any]) -> list[str]:
    """Validate the machine contract with the compiler's executable rules."""

    problems: list[str] = []
    if registry.get("schema") != "design-system/1":
        problems.append("design-system.json schema must be 'design-system/1'")

    product = registry.get("product")
    if not isinstance(product, str) or not product.strip():
        problems.append("design-system.json product must be a non-empty string")

    has_viewports = "viewports" in registry
    has_size_classes = "sizeClasses" in registry
    viewports = registry.get("viewports")
    size_classes = registry.get("sizeClasses")
    valid_viewports = (
        isinstance(viewports, list)
        and bool(viewports)
        and all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
            for value in viewports
        )
        and len(set(viewports)) == len(viewports)
    )
    valid_size_classes = (
        isinstance(size_classes, list)
        and bool(size_classes)
        and all(isinstance(value, str) and bool(value.strip()) for value in size_classes)
        and len(set(size_classes)) == len(size_classes)
    )
    if (
        has_viewports == has_size_classes
        or (has_viewports and not valid_viewports)
        or (has_size_classes and not valid_size_classes)
    ):
        problems.append(
            "design-system.json must declare exactly one non-empty unique responsive "
            "set: positive numeric viewports or string sizeClasses"
        )
    platform = registry.get("platform")
    if not isinstance(platform, str) or not platform.strip():
        problems.append("design-system.json platform must be a non-empty string")
    elif not (platform.startswith("<") and platform.endswith(">")):
        if has_viewports and platform != "web":
            problems.append("design-system.json viewports require platform 'web'")
        if has_size_classes and platform == "web":
            problems.append(
                "design-system.json platform 'web' requires viewports, not sizeClasses"
            )

    for key in ("tokens", "primitives"):
        if not isinstance(registry.get(key), dict):
            problems.append(f"design-system.json {key} must be an object")
    if "productComponents" in registry and not isinstance(
        registry["productComponents"], dict
    ):
        problems.append("design-system.json productComponents must be an object")

    if "motionVariants" in registry:
        _string_list(
            problems, "motionVariants", registry["motionVariants"], nonempty=False
        )
    _string_list(problems, "stateMatrix", registry.get("stateMatrix"), nonempty=True)
    _string_list(problems, "tokenSources", registry.get("tokenSources"), nonempty=True)
    _string_list(
        problems, "primitiveSources", registry.get("primitiveSources"), nonempty=False
    )

    primitives = registry.get("primitives")
    seen_ids: set[str] = set()
    if isinstance(primitives, dict):
        for name, spec in primitives.items():
            path = f"primitives.{name}"
            if not isinstance(spec, dict):
                problems.append(f"design-system.json {path} must be an object")
                continue
            if spec.get("layer") not in {
                "layout",
                "surface",
                "typography",
                "control",
            }:
                problems.append(
                    f"design-system.json {path}.layer must be layout, surface, "
                    "typography, or control"
                )
            if spec.get("dsId") is not None:
                ds_id = spec["dsId"]
                if not isinstance(ds_id, str) or not DS_PRIMITIVE_ID_RE.fullmatch(ds_id):
                    problems.append(
                        f"design-system.json {path}.dsId must match "
                        f"DS-<family>-<number>, got {ds_id!r}"
                    )
                elif ds_id in seen_ids:
                    problems.append(f"design-system.json {path}.dsId duplicates {ds_id}")
                else:
                    seen_ids.add(ds_id)

    components = registry.get("productComponents")
    if isinstance(components, dict):
        for name, spec in components.items():
            path = f"productComponents.{name}"
            if not isinstance(spec, dict):
                problems.append(f"design-system.json {path} must be an object")
                continue
            ds_id = spec.get("dsId")
            if not isinstance(ds_id, str) or not ds_id.strip():
                problems.append(f"design-system.json {path}.dsId must be a non-empty string")
            elif not DS_COMPONENT_ID_RE.fullmatch(ds_id):
                problems.append(
                    f"design-system.json {path}.dsId must match DS-COMP-<number>, "
                    f"got {ds_id!r}"
                )
            elif ds_id in seen_ids:
                problems.append(f"design-system.json {path}.dsId duplicates {ds_id}")
            else:
                seen_ids.add(ds_id)
            for field in ("requiredContentOrder", "composes", "states"):
                _string_list(problems, f"{path}.{field}", spec.get(field), nonempty=True)
            composes = spec.get("composes")
            if isinstance(composes, list) and isinstance(primitives, dict):
                for entry in composes:
                    if not isinstance(entry, str) or is_placeholder(entry):
                        continue
                    if entry.strip() not in primitives:
                        problems.append(
                            f"design-system.json {path}.composes names '{entry}', "
                            "which is not a key in primitives"
                        )

    if "signatureRules" in registry:
        rules = registry["signatureRules"]
        if not isinstance(rules, list):
            problems.append("design-system.json signatureRules must be a list")
        else:
            for rule in rules:
                if not isinstance(rule, str) or not DS_RULE_ID_RE.fullmatch(rule):
                    problems.append(
                        "design-system.json signatureRules entry must match "
                        f"DS-<number> or DS-<family>-<number>, got {rule!r}"
                    )
                elif rule in seen_ids:
                    problems.append(
                        f"design-system.json signatureRules entry duplicates {rule}"
                    )
                else:
                    seen_ids.add(rule)
    return problems


def unfilled_placeholders(value: Any, path: str = "design-system.json") -> list[str]:
    problems: list[str] = []
    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{path}.{key}"
            if is_placeholder(key):
                problems.append(f"{child} is an unfilled template placeholder")
            problems.extend(unfilled_placeholders(value[key], child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            problems.extend(unfilled_placeholders(item, f"{path}[{index}]"))
    elif isinstance(value, str) and is_placeholder(value):
        problems.append(f"{path} is an unfilled template placeholder")
    return problems


def _extract_generated_contract(
    markdown_text: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    begin_count = markdown_text.count(BEGIN_MARKER)
    end_count = markdown_text.count(END_MARKER)
    if begin_count != 1 or end_count != 1:
        return None, [
            "design-system.md must contain exactly one matched generated "
            "design-system contract marker pair"
        ]
    begin_at = markdown_text.find(BEGIN_MARKER)
    end_at = markdown_text.find(END_MARKER)
    if begin_at >= end_at:
        return None, [
            "design-system.md generated contract begin marker must precede its end marker"
        ]
    match = GENERATED_BLOCK_RE.search(markdown_text)
    if (
        match is None
        or match.start() != begin_at
        or match.end() != end_at + len(END_MARKER)
    ):
        return None, [
            "design-system.md generated contract must be a fenced json block "
            "between its markers"
        ]
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        return None, [f"design-system.md generated contract is not valid JSON: {error}"]
    if not isinstance(value, dict):
        return None, ["design-system.md generated contract must contain a JSON object"]
    return value, []


def _diff(expected: Any, actual: Any, path: str, problems: list[str]) -> None:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) - set(actual)):
            problems.append(f"{path}.{key} is missing from the generated Markdown contract")
        for key in sorted(set(actual) - set(expected)):
            problems.append(f"{path}.{key} exists only in the generated Markdown contract")
        for key in sorted(set(expected) & set(actual)):
            _diff(expected[key], actual[key], f"{path}.{key}", problems)
        return
    if isinstance(expected, list) and isinstance(actual, list):
        if expected != actual:
            problems.append(
                f"{path} differs: expected {json.dumps(expected, ensure_ascii=False)}, "
                f"got {json.dumps(actual, ensure_ascii=False)}"
            )
        return
    if expected != actual:
        problems.append(
            f"{path} differs: expected {json.dumps(expected, ensure_ascii=False)}, "
            f"got {json.dumps(actual, ensure_ascii=False)}"
        )


def compare_design_system_pair(
    markdown_text: str, registry: dict[str, Any]
) -> list[str]:
    """Require the same frozen-pair proof as the compiler's read-only gate."""

    problems = validate_design_system_registry(registry)
    problems.extend(unfilled_placeholders(registry))
    generated, parse_problems = _extract_generated_contract(markdown_text)
    problems.extend(parse_problems)
    if generated is not None:
        _diff(contract_inventory(registry), generated, "generated contract", problems)

    primitives = registry.get("primitives")
    components = registry.get("productComponents")
    registered = {
        spec.get("dsId")
        for spec in (primitives.values() if isinstance(primitives, dict) else [])
        if isinstance(spec, dict) and isinstance(spec.get("dsId"), str)
    } | {
        spec.get("dsId")
        for spec in (components.values() if isinstance(components, dict) else [])
        if isinstance(spec, dict) and isinstance(spec.get("dsId"), str)
    } | {
        rule
        for rule in (
            registry.get("signatureRules")
            if isinstance(registry.get("signatureRules"), list)
            else []
        )
        if isinstance(rule, str)
    }
    unregistered = sorted(
        {token for token in DS_TOKEN_RE.findall(markdown_text) if token not in registered}
    )
    if unregistered:
        problems.append(
            "design-system.md names DS ids missing from design-system.json: "
            + ", ".join(unregistered)
        )
    malformed = sorted(
        token
        for token in set(DS_LIKE_TOKEN_RE.findall(markdown_text))
        if DS_RULE_ID_RE.fullmatch(token) is None
    )
    if malformed:
        problems.append(
            "design-system.md contains malformed DS ids: " + ", ".join(malformed)
        )
    return problems

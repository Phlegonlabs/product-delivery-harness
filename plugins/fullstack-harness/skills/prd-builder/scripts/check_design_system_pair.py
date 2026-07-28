#!/usr/bin/env python3
"""Validate design-system.json and its generated Markdown contract view.

The JSON file is the sole structured authority. The Markdown carries rationale
and guardrails plus one generated JSON block that mirrors every field consumed
by implementation and conformance checks. This avoids guessing declarations
from arbitrary Markdown tables or headings.

Exit codes: 0 clean, 1 mismatch, 2 usage or parse error.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
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
    "motionVariants",
    "stateMatrix",
)
GENERATED_BLOCK_RE = re.compile(
    rf"{re.escape(BEGIN_MARKER)}\s*```json\s*(.*?)\s*```\s*{re.escape(END_MARKER)}",
    re.DOTALL,
)


def contract_inventory(registry: dict[str, Any]) -> dict[str, Any]:
    """Return the ordered, machine-owned subset published into Markdown."""
    return {key: registry[key] for key in CONTRACT_FIELDS if key in registry}


def generated_contract_block(registry: dict[str, Any]) -> str:
    payload = json.dumps(
        contract_inventory(registry),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    return f"{BEGIN_MARKER}\n```json\n{payload}\n```\n{END_MARKER}"


def _generated_contract_match(
    markdown_text: str,
    *,
    allow_absent: bool,
) -> re.Match[str] | None:
    begin_count = markdown_text.count(BEGIN_MARKER)
    end_count = markdown_text.count(END_MARKER)
    if begin_count == 0 and end_count == 0 and allow_absent:
        return None
    if begin_count != 1 or end_count != 1:
        raise ValueError(
            "design-system.md must contain exactly one matched generated "
            "design-system contract marker pair"
        )

    begin_at = markdown_text.find(BEGIN_MARKER)
    end_at = markdown_text.find(END_MARKER)
    if begin_at >= end_at:
        raise ValueError(
            "design-system.md generated contract begin marker must precede its end marker"
        )

    match = GENERATED_BLOCK_RE.search(markdown_text)
    if (
        match is None
        or match.start() != begin_at
        or match.end() != end_at + len(END_MARKER)
    ):
        raise ValueError(
            "design-system.md generated contract must be a fenced json block between its markers"
        )
    return match


def replace_generated_contract(markdown_text: str, registry: dict[str, Any]) -> str:
    """Replace the generated block, or append it when the document predates it."""
    block = generated_contract_block(registry)
    match = _generated_contract_match(markdown_text, allow_absent=True)
    if match is not None:
        return markdown_text[: match.start()] + block + markdown_text[match.end() :]
    return markdown_text.rstrip() + "\n\n## Generated Machine Contract\n\n" + block + "\n"


def _string_list(problems: list[str], path: str, value: Any, *, nonempty: bool) -> None:
    if (
        not isinstance(value, list)
        or (nonempty and not value)
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        qualifier = "non-empty " if nonempty else ""
        problems.append(f"design-system.json {path} must be a {qualifier}list of strings")


def validate_registry(registry: dict[str, Any]) -> list[str]:
    """Validate the structured fields the pair checker promises to mirror."""
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
        and all(
            isinstance(value, str) and bool(value.strip())
            for value in size_classes
        )
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
            problems.append(
                "design-system.json viewports require platform 'web'"
            )
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
            problems,
            "motionVariants",
            registry["motionVariants"],
            nonempty=False,
        )
    _string_list(problems, "stateMatrix", registry.get("stateMatrix"), nonempty=True)
    _string_list(problems, "tokenSources", registry.get("tokenSources"), nonempty=True)
    _string_list(problems, "primitiveSources", registry.get("primitiveSources"), nonempty=False)

    primitives = registry.get("primitives")
    if isinstance(primitives, dict):
        for name, spec in primitives.items():
            path = f"primitives.{name}"
            if not isinstance(spec, dict):
                problems.append(f"design-system.json {path} must be an object")
            elif spec.get("layer") not in {"layout", "surface", "typography", "control"}:
                problems.append(
                    f"design-system.json {path}.layer must be layout, surface, typography, or control"
                )

    components = registry.get("productComponents")
    if isinstance(components, dict):
        for name, spec in components.items():
            path = f"productComponents.{name}"
            if not isinstance(spec, dict):
                problems.append(f"design-system.json {path} must be an object")
                continue
            if not isinstance(spec.get("dsId"), str) or not spec["dsId"].strip():
                problems.append(f"design-system.json {path}.dsId must be a non-empty string")
            for field in ("requiredContentOrder", "composes", "states"):
                _string_list(
                    problems,
                    f"{path}.{field}",
                    spec.get(field),
                    nonempty=True,
                )
    return problems


def _extract_generated_contract(markdown_text: str) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        match = _generated_contract_match(markdown_text, allow_absent=False)
    except ValueError as error:
        return None, [str(error)]
    assert match is not None
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


def compare(markdown_text: str, registry: dict[str, Any]) -> list[str]:
    problems = validate_registry(registry)
    generated, parse_problems = _extract_generated_contract(markdown_text)
    problems.extend(parse_problems)
    if generated is not None:
        _diff(
            contract_inventory(registry),
            generated,
            "generated contract",
            problems,
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", required=True, type=Path, help="path to design-system.md")
    parser.add_argument("--registry", required=True, type=Path, help="path to design-system.json")
    parser.add_argument(
        "--write",
        action="store_true",
        help="replace or append the generated Markdown contract block before checking",
    )
    args = parser.parse_args(argv)

    for path in (args.markdown, args.registry):
        if not path.is_file():
            print(f"missing file: {path}", file=sys.stderr)
            return 2

    try:
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"{args.registry} is not valid JSON: {error}", file=sys.stderr)
        return 2
    if not isinstance(registry, dict):
        print(f"{args.registry} must contain a JSON object", file=sys.stderr)
        return 2

    markdown_text = args.markdown.read_text(encoding="utf-8")
    if args.write:
        try:
            markdown_text = replace_generated_contract(markdown_text, registry)
        except ValueError as error:
            print(error, file=sys.stderr)
            return 2
        args.markdown.write_text(markdown_text, encoding="utf-8")

    problems = compare(markdown_text, registry)
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        print(f"{len(problems)} pairing problem(s) between {args.markdown} and {args.registry}")
        return 1
    print(f"PASS generated design-system contract agrees with {args.registry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

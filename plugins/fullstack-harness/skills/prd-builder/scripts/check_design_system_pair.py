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
import re
import sys
from pathlib import Path
from typing import Any

BEGIN_MARKER = "<!-- BEGIN GENERATED DESIGN SYSTEM CONTRACT -->"
END_MARKER = "<!-- END GENERATED DESIGN SYSTEM CONTRACT -->"
CONTRACT_FIELDS = (
    "schema",
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


def replace_generated_contract(markdown_text: str, registry: dict[str, Any]) -> str:
    """Replace the generated block, or append it when the document predates it."""
    block = generated_contract_block(registry)
    matches = list(GENERATED_BLOCK_RE.finditer(markdown_text))
    if len(matches) > 1:
        raise ValueError("design-system.md contains more than one generated contract block")
    if matches:
        match = matches[0]
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

    responsive = [
        key
        for key in ("viewports", "sizeClasses")
        if isinstance(registry.get(key), list) and registry[key]
    ]
    if len(responsive) != 1:
        problems.append(
            "design-system.json must declare exactly one non-empty responsive set: "
            "viewports or sizeClasses"
        )

    for key in ("tokens", "primitives", "productComponents"):
        if not isinstance(registry.get(key), dict):
            problems.append(f"design-system.json {key} must be an object")

    _string_list(problems, "motionVariants", registry.get("motionVariants"), nonempty=False)
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
    marker_count = markdown_text.count(BEGIN_MARKER)
    end_count = markdown_text.count(END_MARKER)
    if marker_count != 1 or end_count != 1:
        return None, [
            "design-system.md must contain exactly one complete generated design-system contract block"
        ]
    match = GENERATED_BLOCK_RE.search(markdown_text)
    if match is None:
        return None, [
            "design-system.md generated contract must be a fenced json block between its markers"
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

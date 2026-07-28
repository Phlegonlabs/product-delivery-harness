#!/usr/bin/env python3
"""Check that design-system.md and design-system.json describe the same system.

The two files are published together and neither may carry a token, primitive,
variant, motion variant, product component, or state the other does not. The
JSON is the allowlist `fullstack-harness-engineering`'s UI contract check reads,
so a drift between them leaves that check pointing at a stale allowlist and
passing code that no longer conforms.

Direction that matters: every name the JSON declares must be documented in the
Markdown, and every design-system name the Markdown declares must exist in the
JSON. Prose that merely mentions a word is not a declaration - the Markdown side
is read from its tables and headings, not from sentences.

Exit codes: 0 clean, 1 mismatch, 2 usage or parse error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# `| Name | ...` table rows and `### Name` headings are declarations. A `##`
# heading names a section ("## Primitives"), not an entry, so it is not one.
TABLE_CELL_RE = re.compile(r"^\|\s*`?([A-Za-z][\w.-]*)`?\s*\|")
HEADING_RE = re.compile(r"^#{3,4}\s+`?([A-Za-z][\w.-]*)`?\s*$")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
PLACEHOLDER_RE = re.compile(r"^<.*>$")


def is_placeholder(name: str) -> bool:
    return bool(PLACEHOLDER_RE.match(name.strip()))


SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
ENTRY_SECTION_WORDS = ("primitive", "product component", "component")


def markdown_declarations(text: str) -> set[str]:
    """Entry names the Markdown declares.

    Only a `###`/`####` heading inside a primitives or product-components
    section counts. A table row label ("Medium", "Overlay", "Risk") is data,
    not a declaration, and treating it as one buries the real findings.
    """
    names: set[str] = set()
    in_fence = False
    in_entry_section = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("````"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        section = SECTION_RE.match(stripped)
        if section:
            title = section.group(1).lower()
            in_entry_section = any(word in title for word in ENTRY_SECTION_WORDS)
            continue
        if not in_entry_section:
            continue
        match = HEADING_RE.match(stripped)
        if match:
            names.add(match.group(1))
    return names


def markdown_table_labels(text: str) -> set[str]:
    """First-column labels from every table, used only as evidence a JSON name
    is documented somewhere."""
    names: set[str] = set()
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("````"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = TABLE_CELL_RE.match(stripped)
        if match:
            names.add(match.group(1))
    return names


WORD_RE = re.compile(r"[A-Za-z0-9][\w.-]*")


def markdown_mentions(text: str) -> set[str]:
    """Every name documented anywhere outside a fenced block.

    Used only for the JSON -> Markdown direction, which asks "is this allowlist
    entry written down at all". A design system documents a variant set several
    ways - a backticked token, a table cell, a comma list inside a placeholder
    (`<roles: display, heading, body, caption>`) - so this tokenizes to words
    rather than trying to guess the shape. It is deliberately permissive: the
    failure this guards is someone editing one file and forgetting the other,
    not someone documenting a variant in an unusual place.
    """
    names: set[str] = set()
    in_fence = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("````"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in BACKTICK_RE.finditer(line):
            names.add(match.group(1).strip())
        for match in WORD_RE.finditer(line):
            names.add(match.group(0))
    return names


def json_names(registry: dict) -> dict[str, set[str]]:
    """Every declared name in the JSON, grouped by kind."""
    groups: dict[str, set[str]] = {
        "token": set(),
        "primitive": set(),
        "variant": set(),
        "product component": set(),
        "motion variant": set(),
        "state": set(),
    }

    tokens = registry.get("tokens")
    if isinstance(tokens, dict):
        for group, values in tokens.items():
            if isinstance(values, dict):
                for key in values:
                    if not is_placeholder(key):
                        groups["token"].add(f"{group}.{key}")

    primitives = registry.get("primitives")
    if isinstance(primitives, dict):
        for name, spec in primitives.items():
            if is_placeholder(name):
                continue
            groups["primitive"].add(name)
            if not isinstance(spec, dict):
                continue
            for prop, values in spec.items():
                if prop in {"dsId", "layer", "composes", "states"}:
                    continue
                if isinstance(values, list):
                    for value in values:
                        if isinstance(value, str) and not is_placeholder(value):
                            groups["variant"].add(f"{name}.{prop}={value}")

    components = registry.get("productComponents")
    if isinstance(components, dict):
        for name in components:
            if not is_placeholder(name):
                groups["product component"].add(name)

    for name in registry.get("motionVariants", []) or []:
        if isinstance(name, str) and not is_placeholder(name):
            groups["motion variant"].add(name)

    for name in registry.get("stateMatrix", []) or []:
        if isinstance(name, str) and not is_placeholder(name):
            groups["state"].add(name)

    return groups


def compare(markdown_text: str, registry: dict) -> list[str]:
    problems: list[str] = []
    declared = markdown_declarations(markdown_text)
    mentioned = (
        markdown_mentions(markdown_text)
        | markdown_table_labels(markdown_text)
        | declared
    )
    groups = json_names(registry)

    for kind in ("token", "primitive", "product component", "motion variant", "state"):
        for name in sorted(groups[kind]):
            if name in mentioned:
                continue
            # A dotted token may be documented as its leaf name inside its group table.
            if "." in name and name.split(".", 1)[1] in mentioned:
                continue
            problems.append(
                f"design-system.json declares {kind} '{name}' but design-system.md never documents it"
            )

    for name in sorted(groups["variant"]):
        primitive, _, pair = name.partition(".")
        prop, _, value = pair.partition("=")
        if value in mentioned or f"{prop}={value}" in mentioned:
            continue
        problems.append(
            f"design-system.json declares {primitive} variant {prop}={value} "
            "but design-system.md never documents it"
        )

    json_entries = groups["primitive"] | groups["product component"]
    for name in sorted(declared):
        if name in json_entries or is_placeholder(name):
            continue
        problems.append(
            f"design-system.md declares '{name}' but design-system.json does not list it"
        )

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", required=True, type=Path, help="path to design-system.md")
    parser.add_argument("--registry", required=True, type=Path, help="path to design-system.json")
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

    problems = compare(args.markdown.read_text(encoding="utf-8"), registry)
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        print(f"{len(problems)} pairing problem(s) between {args.markdown} and {args.registry}")
        return 1
    print(f"PASS design-system.md and design-system.json agree ({args.registry})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

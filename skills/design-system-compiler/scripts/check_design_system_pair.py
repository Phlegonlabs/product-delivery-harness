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
import os
import re
import stat
import sys
import tempfile
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
    "signatureRules",
    "motionVariants",
    "stateMatrix",
)
GENERATED_BLOCK_RE = re.compile(
    rf"{re.escape(BEGIN_MARKER)}\s*```json\s*(.*?)\s*```\s*{re.escape(END_MARKER)}",
    re.DOTALL,
)
PLACEHOLDER_RE = re.compile(r"^<.*>$", re.DOTALL)
DS_COMP_ID_RE = re.compile(r"^DS-COMP-[0-9]+$")
DS_PRIMITIVE_ID_RE = re.compile(r"^DS-[A-Z]+-[0-9]+$")
DS_RULE_ID_RE = re.compile(r"^DS-(?:[A-Z]+-)?[0-9]+$")
DS_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])DS-(?:[A-Z]+-)?[0-9]+(?![A-Za-z0-9_-])"
)
DS_LIKE_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])DS-[A-Za-z0-9_-]+(?![A-Za-z0-9_-])"
)


class ConcurrentModificationError(RuntimeError):
    """Raised when the destination changed after it was read for a write."""


def is_placeholder(value: str) -> bool:
    """True for a `<...>`-shaped template slot nobody has filled in yet."""
    return bool(PLACEHOLDER_RE.match(value.strip()))


def contract_inventory(registry: dict[str, Any]) -> dict[str, Any]:
    """Return the ordered, machine-owned subset published into Markdown."""
    return {key: registry[key] for key in CONTRACT_FIELDS if key in registry}


def generated_contract_block(
    registry: dict[str, Any],
    *,
    newline: str = "\n",
) -> str:
    payload = json.dumps(
        contract_inventory(registry),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    block = f"{BEGIN_MARKER}\n```json\n{payload}\n```\n{END_MARKER}"
    return block.replace("\n", newline)


def _newline_sequence(text: str) -> str:
    match = re.search(r"\r\n|\r|\n", text)
    return match.group(0) if match is not None else "\n"


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
    newline = _newline_sequence(markdown_text)
    block = generated_contract_block(registry, newline=newline)
    match = _generated_contract_match(markdown_text, allow_absent=True)
    if match is not None:
        return markdown_text[: match.start()] + block + markdown_text[match.end() :]
    if not markdown_text:
        prefix = ""
    elif markdown_text.endswith(f"{newline}{newline}"):
        prefix = markdown_text
    elif markdown_text.endswith(("\r", "\n")):
        prefix = markdown_text + newline
    else:
        prefix = markdown_text + newline + newline
    return (
        prefix
        + "## Generated Machine Contract"
        + newline
        + newline
        + block
        + newline
    )


def _write_bytes_atomic(path: Path, payload: bytes, expected_bytes: bytes) -> None:
    """Replace ``path`` with ``payload`` without exposing a partial file."""
    original_stat = path.lstat()
    if stat.S_ISLNK(original_stat.st_mode):
        raise ConcurrentModificationError(
            f"{path} must not be a symbolic link for --write"
        )
    mode = stat.S_IMODE(original_stat.st_mode)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, mode)
        current_stat = path.lstat()
        if (
            stat.S_ISLNK(current_stat.st_mode)
            or not os.path.samestat(original_stat, current_stat)
            or path.read_bytes() != expected_bytes
        ):
            raise ConcurrentModificationError(
                f"{path} changed while preparing the generated contract"
            )
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


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
        and len(viewports) >= 3
        and all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
            for value in viewports
        )
        and len(set(viewports)) == len(viewports)
        and all(left < right for left, right in zip(viewports, viewports[1:]))
    )
    valid_size_classes = (
        isinstance(size_classes, list)
        and len(size_classes) >= 2
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
            "set: at least three ascending numeric viewports for web, or at least "
            "two unique string sizeClasses for native or desktop"
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
    seen_ds_ids: set[str] = set()
    if isinstance(primitives, dict):
        for name, spec in primitives.items():
            path = f"primitives.{name}"
            if not isinstance(spec, dict):
                problems.append(f"design-system.json {path} must be an object")
            elif spec.get("layer") not in {"layout", "surface", "typography", "control"}:
                problems.append(
                    f"design-system.json {path}.layer must be layout, surface, typography, or control"
                )
            if isinstance(spec, dict) and spec.get("dsId") is not None:
                ds_id = spec["dsId"]
                if not isinstance(ds_id, str) or not DS_PRIMITIVE_ID_RE.match(ds_id):
                    problems.append(
                        f"design-system.json {path}.dsId must match DS-<family>-<number>, "
                        f"got {ds_id!r}"
                    )
                elif ds_id in seen_ds_ids:
                    problems.append(f"design-system.json {path}.dsId duplicates {ds_id}")
                else:
                    seen_ds_ids.add(ds_id)

    components = registry.get("productComponents")
    if isinstance(components, dict):
        for name, spec in components.items():
            path = f"productComponents.{name}"
            if not isinstance(spec, dict):
                problems.append(f"design-system.json {path} must be an object")
                continue
            if not isinstance(spec.get("dsId"), str) or not spec["dsId"].strip():
                problems.append(f"design-system.json {path}.dsId must be a non-empty string")
            elif not DS_COMP_ID_RE.match(spec["dsId"]):
                problems.append(
                    f"design-system.json {path}.dsId must match DS-COMP-<number>, "
                    f"got {spec['dsId']!r}"
                )
            elif spec["dsId"] in seen_ds_ids:
                problems.append(
                    f"design-system.json {path}.dsId duplicates {spec['dsId']}"
                )
            else:
                seen_ds_ids.add(spec["dsId"])
            for field in ("requiredContentOrder", "composes", "states"):
                _string_list(
                    problems,
                    f"{path}.{field}",
                    spec.get(field),
                    nonempty=True,
                )
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
                if not isinstance(rule, str) or not DS_RULE_ID_RE.match(rule):
                    problems.append(
                        f"design-system.json signatureRules entry must match "
                        f"DS-<number> or DS-<family>-<number>, got {rule!r}"
                    )
                elif rule in seen_ds_ids:
                    problems.append(
                        f"design-system.json signatureRules entry duplicates {rule}"
                    )
                else:
                    seen_ds_ids.add(rule)
    return problems


def unfilled_placeholders(value: Any, path: str = "design-system.json") -> list[str]:
    """Report every `<...>` key or string value still left from the template."""
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


def compare(
    markdown_text: str,
    registry: dict[str, Any],
    *,
    require_filled: bool = False,
) -> list[str]:
    problems = validate_registry(registry)
    if require_filled:
        problems.extend(unfilled_placeholders(registry))
    generated, parse_problems = _extract_generated_contract(markdown_text)
    problems.extend(parse_problems)
    if generated is not None:
        _diff(
            contract_inventory(registry),
            generated,
            "generated contract",
            problems,
        )
    # Every DS-* id the Markdown names — prose, tables, or generated block —
    # must resolve to a registered id: a product component dsId, a primitive
    # dsId, or a signatureRules entry. The Markdown never mints ids.
    components = registry.get("productComponents")
    primitives = registry.get("primitives")
    registered = {
        spec.get("dsId")
        for spec in (components.values() if isinstance(components, dict) else [])
        if isinstance(spec, dict) and isinstance(spec.get("dsId"), str)
    } | {
        spec.get("dsId")
        for spec in (primitives.values() if isinstance(primitives, dict) else [])
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
        {
            token
            for token in DS_TOKEN_RE.findall(markdown_text)
            if token not in registered
        }
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", required=True, type=Path, help="path to design-system.md")
    parser.add_argument("--registry", required=True, type=Path, help="path to design-system.json")
    parser.add_argument(
        "--write",
        action="store_true",
        help="replace or append the generated Markdown contract block before checking",
    )
    parser.add_argument(
        "--require-filled",
        action="store_true",
        help="reject template placeholder keys and string values",
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

    original_markdown_bytes = args.markdown.read_bytes()
    original_markdown_text = original_markdown_bytes.decode("utf-8")
    markdown_text = original_markdown_text
    updated_markdown = markdown_text
    if args.write:
        try:
            updated_markdown = replace_generated_contract(markdown_text, registry)
        except ValueError as error:
            print(error, file=sys.stderr)
            return 2
        markdown_text = updated_markdown

    problems = compare(
        markdown_text,
        registry,
        require_filled=args.require_filled,
    )
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        print(f"{len(problems)} pairing problem(s) between {args.markdown} and {args.registry}")
        return 1

    if args.write and updated_markdown != original_markdown_text:
        try:
            _write_bytes_atomic(
                args.markdown,
                updated_markdown.encode("utf-8"),
                original_markdown_bytes,
            )
        except ConcurrentModificationError as error:
            print(f"cannot write {args.markdown}: {error}", file=sys.stderr)
            return 2
        except OSError as error:
            print(f"cannot write {args.markdown}: {error}", file=sys.stderr)
            return 2

    print(f"PASS generated design-system contract agrees with {args.registry}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

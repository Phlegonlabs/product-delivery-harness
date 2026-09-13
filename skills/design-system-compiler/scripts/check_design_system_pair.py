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
import hashlib
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

PRODUCT_BUILDER_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "product-definition-builder" / "scripts"
)
if str(PRODUCT_BUILDER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PRODUCT_BUILDER_SCRIPTS))
UI_BUILDER_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "ui-design-builder" / "scripts"
)
if str(UI_BUILDER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(UI_BUILDER_SCRIPTS))

from markdown_contract import active_text, exact_marker_lines  # noqa: E402
from ui_approval_digest import canonical_ui_approval_sha256  # noqa: E402


BEGIN_MARKER = "<!-- BEGIN GENERATED DESIGN SYSTEM CONTRACT -->"
END_MARKER = "<!-- END GENERATED DESIGN SYSTEM CONTRACT -->"
CONTRACT_FIELDS = (
    "schema",
    "product",
    "platform",
    "stylingMechanism",
    "enforcement",
    "sourceBindings",
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
SOURCE_BINDING_KEYS = (
    "prd",
    "architecture",
    "stack",
    "uiDesign",
    "wireframe",
    "hifi",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VALID_PLATFORMS = {"web", "ios", "android", "flutter", "react-native", "macos", "windows", "desktop"}
VALID_STYLING_MECHANISMS = {"utility CSS", "CSS-in-JS", "CSS modules", "plain CSS", "platform theme"}
VALID_ENFORCEMENT = {"blocking", "advisory"}




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
    begin_lines = exact_marker_lines(markdown_text, BEGIN_MARKER)
    end_lines = exact_marker_lines(markdown_text, END_MARKER)
    if not begin_lines and not end_lines and allow_absent:
        return None
    if len(begin_lines) != 1 or len(end_lines) != 1:
        raise ValueError(
            "design-system.md must contain exactly one matched generated "
            "design-system contract marker pair"
        )

    line_offsets = [0]
    for match in re.finditer(r"\n", markdown_text):
        line_offsets.append(match.end())
    begin_line = begin_lines[0]
    end_line = end_lines[0]
    begin_at = markdown_text.find(BEGIN_MARKER, line_offsets[begin_line - 1])
    end_at = markdown_text.find(END_MARKER, line_offsets[end_line - 1])
    if begin_at >= end_at:
        raise ValueError(
            "design-system.md generated contract begin marker must precede its end marker"
        )

    match = GENERATED_BLOCK_RE.search(markdown_text, begin_at, end_at + len(END_MARKER))
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


def _repo_relative(value: str) -> bool:
    return not (
        not value
        or value.startswith(("/", "\\"))
        or (len(value) > 1 and value[1] == ":")
        or any(part == ".." for part in Path(value).parts)
    )


def validate_registry(registry: dict[str, Any]) -> list[str]:
    """Validate the structured fields the pair checker promises to mirror."""
    problems: list[str] = []
    schema = registry.get("schema")
    if schema not in {"design-system/1", "design-system/2"}:
        problems.append(
            "design-system.json schema must be 'design-system/1' or 'design-system/2'"
        )

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
    elif not (platform.startswith("<") and platform.endswith(">")) and platform not in VALID_PLATFORMS:
        problems.append(
            "design-system.json platform must be one of: "
            + ", ".join(sorted(VALID_PLATFORMS))
        )
    elif not (platform.startswith("<") and platform.endswith(">")):
        if has_viewports and platform != "web":
            problems.append(
                "design-system.json viewports require platform 'web'"
            )
        if has_size_classes and platform == "web":
            problems.append(
                "design-system.json platform 'web' requires viewports, not sizeClasses"
            )

    styling = registry.get("stylingMechanism")
    if not isinstance(styling, str) or not styling.strip():
        problems.append("design-system.json stylingMechanism must be a non-empty string")
    elif not (styling.startswith("<") and styling.endswith(">")) and styling not in VALID_STYLING_MECHANISMS:
        problems.append(
            "design-system.json stylingMechanism must be one of: "
            + ", ".join(sorted(VALID_STYLING_MECHANISMS))
        )
    enforcement = registry.get("enforcement")
    if not isinstance(enforcement, str) or not enforcement.strip():
        problems.append("design-system.json enforcement must be a non-empty string")
    elif not (enforcement.startswith("<") and enforcement.endswith(">")) and enforcement not in VALID_ENFORCEMENT:
        problems.append(
            "design-system.json enforcement must be one of: "
            + ", ".join(sorted(VALID_ENFORCEMENT))
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

    if schema == "design-system/2":
        bindings = registry.get("sourceBindings")
        if not isinstance(bindings, dict):
            problems.append(
                "design-system.json sourceBindings must be an object with prd, "
                "architecture, stack, uiDesign, wireframe, and hifi"
            )
        else:
            expected = set(SOURCE_BINDING_KEYS)
            missing = sorted(expected - set(bindings))
            extra = sorted(set(bindings) - expected)
            if missing:
                problems.append(
                    "design-system.json sourceBindings is missing: " + ", ".join(missing)
                )
            if extra:
                problems.append(
                    "design-system.json sourceBindings names unexpected keys: "
                    + ", ".join(extra)
                )
            for key in SOURCE_BINDING_KEYS:
                binding = bindings.get(key)
                path_name = f"sourceBindings.{key}"
                if not isinstance(binding, dict):
                    problems.append(f"design-system.json {path_name} must be an object")
                    continue
                path = binding.get("path")
                digest = binding.get("sha256")
                if not isinstance(path, str) or not _repo_relative(path):
                    problems.append(
                        f"design-system.json {path_name}.path must be a repo-relative path"
                    )
                if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
                    problems.append(
                        f"design-system.json {path_name}.sha256 must be lowercase hex"
                    )
            paths = [
                bindings[key].get("path")
                for key in SOURCE_BINDING_KEYS
                if isinstance(bindings.get(key), dict)
            ]
            if len(paths) != len(set(paths)):
                problems.append("design-system.json sourceBindings paths must be distinct")
            semantic_suffixes = {
                "prd": "prd.md",
                "architecture": "architecture.md",
                "stack": "stack-decisions.md",
                "uiDesign": "ui-design.md",
                "wireframe": "wireframes.html",
            }
            for key, suffix in semantic_suffixes.items():
                binding = bindings.get(key)
                path = binding.get("path") if isinstance(binding, dict) else None
                if isinstance(path, str) and not path.casefold().endswith(suffix.casefold()):
                    problems.append(
                        f"design-system.json sourceBindings.{key}.path must identify {suffix}"
                    )
            hifi = bindings.get("hifi")
            hifi_path = hifi.get("path") if isinstance(hifi, dict) else None
            if isinstance(hifi_path, str) and hifi_path.casefold().endswith("wireframes.html"):
                problems.append("design-system.json sourceBindings.hifi.path must be a distinct HiFi target")

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


SOURCE_REF_RE = re.compile(
    r"^\s*(?P<label>PRD source|Architecture source|Stack source|Wireframe|"
    r"Connected HiFi reference|Approved target):\s*"
    r"(?P<path>[A-Za-z0-9._/-]+) @ sha256:(?P<sha256>[0-9a-f]{64})(?:;\s*scope=.*)?\s*$",
    re.MULTILINE,
)


def _ui_identity_bindings(
    bindings: dict[str, Any], *, repo_root: Path, problems: list[str], require_contract: bool = False
) -> None:
    """Cross-check pair source bindings against the UI contract they name."""

    ui_binding = bindings.get("uiDesign")
    if not isinstance(ui_binding, dict):
        return
    ui_path = ui_binding.get("path")
    if not isinstance(ui_path, str) or not _repo_relative(ui_path):
        return
    candidate = (repo_root / ui_path).resolve()
    if not candidate.is_file():
        return
    try:
        text = active_text(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        problems.append(f"design-system.json sourceBindings.uiDesign cannot be read: {exc}")
        return
    if "# UI Design Contract" not in text and "## Source Product Definition" not in text:
        # Legacy inspection fixtures may carry only opaque bytes. Enforce the
        # complete identity join once the file declares itself as a UI contract.
        if require_contract:
            problems.append("design-system.json sourceBindings.uiDesign must point to a complete UI Design Contract")
        return
    refs: dict[str, list[tuple[str, str]]] = {}
    for match in SOURCE_REF_RE.finditer(text):
        refs.setdefault(match.group("label"), []).append(
            (match.group("path"), match.group("sha256"))
        )
    mapping = {
        "prd": "PRD source",
        "architecture": "Architecture source",
        "stack": "Stack source",
        "wireframe": "Wireframe",
        "hifi": "Connected HiFi reference",
    }
    approved_match = re.search(
        r"^Approved target:\s*([A-Za-z0-9._/-]+) @ sha256:([0-9a-f]{64});\s*scope=.*$",
        text,
        re.MULTILINE,
    )
    if approved_match:
        refs.setdefault("Approved target", []).append(
            (approved_match.group(1), approved_match.group(2))
        )
    for key, label in mapping.items():
        binding = bindings.get(key)
        expected_values = refs.get(label, [])
        if label == "Connected HiFi reference" and refs.get("Approved target"):
            expected_values = refs["Approved target"]
        if not isinstance(binding, dict):
            problems.append(f"design-system.json sourceBindings.{key} is missing or not an object")
            continue
        if len(expected_values) != 1:
            problems.append(
                f"design-system.json sourceBindings.{key} requires exactly one active {label} identity"
            )
            continue
        expected = expected_values[0]
        if binding.get("path") != expected[0] or binding.get("sha256") != expected[1]:
            problems.append(
                f"design-system.json sourceBindings.{key} does not match {label} in ui-design.md"
            )

    # A current pair cannot silently accept a UI markdown file that only looks
    # like a source manifest. Run the exact UI checker when its contract is
    # present; otherwise fail the source join rather than minting identities.
    if "# UI Design Contract" in text or "## Source Product Definition" in text:
        try:
            ui_checker = __import__("check_ui_design_contract")
            source_binding = {
                key: bindings.get(key) for key in ("prd", "architecture", "stack", "wireframe", "hifi")
            }
            paths = {
                key: value.get("path")
                for key, value in source_binding.items()
                if isinstance(value, dict) and isinstance(value.get("path"), str)
            }
            ui_checker_problems = ui_checker.validate(
                candidate,
                repo_root=repo_root,
                prd_path=repo_root / paths["prd"] if "prd" in paths else None,
                wireframes_path=repo_root / paths["wireframe"] if "wireframe" in paths else None,
                hifi_path=repo_root / paths["hifi"] if "hifi" in paths else None,
                require_filled=True,
                require_wireframe_approved=True,
                require_visual_approved=True,
                verify_design_system_pair=False,
            )
            problems.extend(f"ui-design: {item}" for item in ui_checker_problems)
        except (ImportError, OSError, UnicodeError) as exc:
            problems.append(f"design-system.json cannot run exact UI checker: {exc}")


def compare(
    markdown_text: str,
    registry: dict[str, Any],
    *,
    require_filled: bool = False,
    repo_root: Path | None = None,
) -> list[str]:
    problems = validate_registry(registry)
    if require_filled:
        if registry.get("schema") != "design-system/2":
            problems.append(
                "current publication requires design-system/2; design-system/1 is inspection-only"
            )
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
    if registry.get("schema") == "design-system/2" and repo_root is None:
        problems.append("design-system.json source bindings require repo_root")
    elif registry.get("schema") == "design-system/2" and repo_root is not None:
        root = repo_root.resolve()
        bindings = registry.get("sourceBindings")
        if isinstance(bindings, dict):
            for key in SOURCE_BINDING_KEYS:
                binding = bindings.get(key)
                if not isinstance(binding, dict):
                    continue
                path = binding.get("path")
                digest = binding.get("sha256")
                if not isinstance(path, str) or not _repo_relative(path):
                    continue
                candidate = (root / path).resolve()
                try:
                    candidate.relative_to(root)
                except ValueError:
                    problems.append(
                        f"design-system.json sourceBindings.{key} path escapes repo_root"
                    )
                    continue
                if not candidate.is_file():
                    problems.append(
                        f"design-system.json sourceBindings.{key} path does not exist: {path}"
                    )
                else:
                    try:
                        actual_digest = (
                            canonical_ui_approval_sha256(candidate.read_text(encoding="utf-8"))
                            if key == "uiDesign"
                            else hashlib.sha256(candidate.read_bytes()).hexdigest()
                        )
                    except (OSError, UnicodeError) as exc:
                        problems.append(
                            f"design-system.json sourceBindings.{key} cannot read current bytes: {exc}"
                        )
                        continue
                    if not isinstance(digest, str) or actual_digest != digest:
                        problems.append(
                            f"design-system.json sourceBindings.{key} sha256 does not "
                            f"match current bytes: {path}"
                        )
            if isinstance(bindings, dict):
                _ui_identity_bindings(
                    bindings,
                    repo_root=root,
                    problems=problems,
                    require_contract=require_filled,
                )

    # Every DS-* id active Markdown names — prose or tables, never fences or
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
            for token in DS_TOKEN_RE.findall(active_text(markdown_text))
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
        for token in set(DS_LIKE_TOKEN_RE.findall(active_text(markdown_text)))
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
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="repository root used to resolve and hash design-system/2 source bindings",
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
        repo_root=args.repo_root,
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

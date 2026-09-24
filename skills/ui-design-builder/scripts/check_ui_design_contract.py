#!/usr/bin/env python3
"""Validate the staged UI design decision and approval contract."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import re
import stat
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import check_wireframe_html
from motion_evidence import motion_findings
from review_evidence import (
    assessment_findings,
    author_artifact_findings,
    author_usage_findings,
    execution_findings,
    score_findings,
)
from hifi_reviewer import ReviewerParser, has_current_reviewer_shell, product_control_findings, reviewer_contract, reviewer_evidence_findings

PRODUCT_BUILDER_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "product-definition-builder" / "scripts"
)
if str(PRODUCT_BUILDER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PRODUCT_BUILDER_SCRIPTS))
DESIGN_SYSTEM_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "design-system-compiler" / "scripts"
)
if str(DESIGN_SYSTEM_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DESIGN_SYSTEM_SCRIPTS))

from markdown_contract import active_text  # noqa: E402
from release_targets import parse_release_targets  # noqa: E402
from prd_ui_contract import parse_prd_ui_contract  # noqa: E402
from ui_approval_digest import canonical_ui_approval_sha256  # noqa: E402
from operation_coverage import coverage_findings  # noqa: E402


def is_structure_review(text: str) -> bool:
    """New design rounds validate structure; they do not mint wireframe approval."""
    return bool(re.search(r"^## Wireframe Validation\s*$", active_text(text), re.MULTILINE))


def wireframe_heading(text: str) -> str:
    return "## Wireframe Validation" if is_structure_review(text) else "## Wireframe Approval"


REQUIRED_HEADINGS = (
    "## Source Product Definition",
    "## UI Design Intake",
    "## Motion And Media Intent",
    "## Wireframe Approval",
    "## Style Integration",
    "## HiFi Review",
    "## Visual Approval",
    "## Design System Need Gate",
)
ANGLE_PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
SOURCE_RE = re.compile(r"^(?P<path>[A-Za-z0-9._/-]+) @ sha256:(?P<sha256>[0-9a-f]{64})$")
TARGET_SOURCE_RE = re.compile(
    r"^(?P<path>[A-Za-z0-9._/-]+) @ sha256:(?P<sha256>[0-9a-f]{64}); "
    r"scope=surfaces=(?P<surfaces>[^|;]+)\|routes=(?P<routes>[^|;]+)\|"
    r"states=(?P<states>[^|;]+)\|responsive=(?P<responsive>[^|;]+)\|"
    r"tolerance=(?P<tolerance>[^|;]+)\|allowedDeviations=(?P<deviations>[^|;]+)\|"
    r"captureMode=(?P<captureMode>hosted-browser|browser-extension|native|desktop|mixed)$"
)
PAIR_RE = re.compile(
    r"^(?P<markdown>[A-Za-z0-9._/-]+) @ sha256:(?P<markdown_sha256>[0-9a-f]{64})"
    r" and (?P<registry>[A-Za-z0-9._/-]+) @ sha256:(?P<registry_sha256>[0-9a-f]{64})$"
)
PENDING_PAIR_VALUE = "pending — design-system-compiler"
PAIR_DISPOSITION_RE = re.compile(
    r"^(?P<decision>none|retain|retire)\s+—\s+(?P<reason>[^;]+);\s*"
    r"owner=(?P<owner>[^;]+);\s*decided=(?P<date>\d{4}-\d{2}-\d{2})$",
    re.IGNORECASE,
)
EVIDENCE_RE = re.compile(
    r"^PASS\s+—\s+evidence=(?P<path>[A-Za-z0-9._/-]+)\s+@\s+"
    r"sha256:(?P<sha256>[0-9a-f]{64})$"
)
REPLACEMENT_RE = re.compile(
    r"^(?P<key>target|ui-design|wireframe|prd)="
    r"(?P<path>[A-Za-z0-9._/-]+) @ sha256:(?P<sha256>[0-9a-f]{64})$"
)
MM_ID_RE = re.compile(r"^MM-[A-Z0-9]+(?:-[A-Z0-9]+)*$")
MM_SCOPE_RE = re.compile(
    r"^(?P<screen>UI-[A-Z0-9]+(?:-[A-Z0-9]+)*)\s*/\s*(?P<region>[A-Za-z0-9][A-Za-z0-9 _-]*)$"
)
WIREFRAME_DATA_RE = re.compile(
    r'<script\s+id=["\']wireframe-data["\']\s+type=["\']application/json["\']\s*>'
    r"(?P<data>[\s\S]*?)</script>",
    re.IGNORECASE,
)
HIFI_MANIFEST_RE = re.compile(
    r'<script\s+id=["\']ui-hifi-manifest["\']\s+type=["\']application/json["\']\s*>'
    r"(?P<data>[\s\S]*?)</script>",
    re.IGNORECASE,
)
NON_HUMAN_OWNERS = {
    "ai",
    "agent",
    "assistant",
    "automation",
    "codex",
    "model",
    "system",
}
VALID_TREATMENTS = {"none", "image", "motion", "image + motion"}
VALID_MOTION_STATUSES = {"approved", "deferred"}
VALID_MOTION_DIRECTIONS = {"not_required", "functional_only", "expressive"}
VALID_WIREFRAME_DECISIONS = {"draft", "approved", "revision_requested", "blocked"}
VALID_DIRECTION_DECISIONS = {"approved", "selected", "mixed-and-approved"}
VALID_DIRECTION_MODES = {"one recommended direction", "three comparable directions"}
STACK_SEMANTIC_KEYS = {
    "platform",
    "renderingModel",
    "componentFoundation",
    "stylingMechanism",
}
STACK_PLATFORM_BY_SURFACE_CLASS = {
    "hosted_web": "web",
    "browser_extension": "web",
    "ios": "ios",
    "android": "android",
    "macos": "macos",
    "windows": "windows",
    "desktop": "desktop",
}
NON_HUMAN_TOKEN_RE = re.compile(
    r"(?<!\w)(?:ai|agent|assistant|automation|automated|model|bot|claude|codex|"
    r"system|machine)(?!\w)",
    re.IGNORECASE,
)
EVIDENCE_SCHEMA = "ui-evidence/2"
RECEIPT_TOOLS = {
    "playwright",
    "chrome-devtools",
    "playwright-extension",
    "xcode-simulator",
    "android-emulator",
    "desktop-browser",
    "impeccable",
    "rubric-grader",
    "platform-review",
}
RECEIPT_METHODS = {
    "browser-matrix",
    "extension-matrix",
    "native-matrix",
    "desktop-matrix",
    "rubric-grading",
    "mixed-platform-matrix",
    "impeccable-critique",
    "impeccable-audit",
    "sandboxed-offline-browser",
}
HIFI_SURFACE_RECEIPT_METHOD = "sandboxed-offline-browser"


def _receipt_contract(check: str | None) -> tuple[set[str], str] | None:
    if check is None:
        return None
    if check == "hifi-mixed":
        return {"platform-review"}, HIFI_SURFACE_RECEIPT_METHOD
    if check == "motion-preview":
        return {"playwright", "chrome-devtools"}, HIFI_SURFACE_RECEIPT_METHOD
    if check == "wireframe-mixed":
        return {"platform-review"}, "mixed-platform-matrix"
    if check in {"hifi-mixed-grading", "wireframe-mixed-grading"}:
        return {"rubric-grader"}, "rubric-grading"
    if check in {"hifi-browser", "hifi-extension", "hifi-native", "hifi-desktop"}:
        tool_by_check = {
            "hifi-browser": {"playwright", "chrome-devtools"},
            "hifi-extension": {"playwright-extension"},
            "hifi-native": {"xcode-simulator", "android-emulator"},
            "hifi-desktop": {"desktop-browser"},
        }
        return tool_by_check[check], HIFI_SURFACE_RECEIPT_METHOD
    if check.endswith("-browser"):
        return {"playwright", "chrome-devtools"}, "browser-matrix"
    if check.endswith("-extension"):
        return {"playwright-extension"}, "extension-matrix"
    if check.endswith("-native"):
        return {"xcode-simulator", "android-emulator"}, "native-matrix"
    if check.endswith("-desktop"):
        return {"desktop-browser"}, "desktop-matrix"
    if "-impeccable-critique" in check:
        return {"impeccable"}, "impeccable-critique"
    if "-impeccable-audit" in check:
        return {"impeccable"}, "impeccable-audit"
    if check.endswith("-grading"):
        return {"rubric-grader"}, "rubric-grading"
    return None
EVIDENCE_CHECKS = {
    "Responsive surface check": "wireframe-browser",
    "Wireframe UI grading": "wireframe-grading",
    "Impeccable critique verdict": "hifi-impeccable-critique",
    "Impeccable audit verdict": "hifi-impeccable-audit",
    "HiFi UI grading": "hifi-grading",
    "HiFi surface check": "hifi-browser",
}


def _add(problems: list[str], message: str) -> None:
    problems.append(f"ui-design: {message}")


def _section(text: str, heading: str) -> str | None:
    match = re.search(
        rf"^{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def _field_values(section: str, name: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in re.finditer(
            rf"^\s*{re.escape(name)}\s*:\s*(.+?)\s*$",
            section,
            re.IGNORECASE | re.MULTILINE,
        )
    ]


def _field(section: str, name: str) -> str | None:
    values = _field_values(section, name)
    return values[0] if values else None


def _filled(value: str | None) -> bool:
    if not value:
        return False
    stripped = value.strip()
    return not (
        (stripped.startswith("[") and stripped.endswith("]"))
        or ANGLE_PLACEHOLDER_RE.search(stripped)
        or stripped.casefold() in {"tbd", "todo", "unknown"}
    )


def _require_fields(
    section: str,
    names: tuple[str, ...],
    *,
    label: str,
    require_filled: bool,
    problems: list[str],
) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in names:
        field_values = _field_values(section, name)
        if not field_values:
            _add(problems, f"{label} is missing {name!r}")
            continue
        if len(field_values) != 1:
            _add(problems, f"{label} has duplicate {name!r} fields")
        value = field_values[0]
        values[name] = value
        if require_filled and not _filled(value):
            _add(problems, f"{label} field {name!r} is not filled")
    return values


def _human_owner(value: str | None) -> bool:
    if not _filled(value):
        return False
    normalized = value.strip().casefold().strip(".:-")
    return normalized not in NON_HUMAN_OWNERS and NON_HUMAN_TOKEN_RE.search(value) is None


def _date(value: str | None) -> bool:
    if value is None or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        return False
    try:
        date.fromisoformat(value.strip())
    except ValueError:
        return False
    return True


def _pass_evidence(value: str | None, label: str, problems: list[str]) -> dict[str, str] | None:
    """Parse a PASS line that is independently bound to a hashed evidence file."""

    match = EVIDENCE_RE.fullmatch((value or "").strip()) if value else None
    if match is None:
        _add(
            problems,
            f"{label} must use 'PASS — evidence=<repo-relative-path> @ "
            "sha256:<lowercase sha256>'",
        )
        return None
    return {
        "path": match.group("path"),
        "sha256": match.group("sha256"),
    }


def _replacement_parts(value: str | None, problems: list[str]) -> dict[str, str]:
    """Parse the exact not_required visual contract replacement inventory."""

    parts: dict[str, str] = {}
    if not value:
        return parts
    for raw in value.split(";"):
        match = REPLACEMENT_RE.fullmatch(raw.strip())
        if match is None:
            _add(
                problems,
                "Replacement visual contract when not_required must contain exactly "
                "target, ui-design, wireframe, and prd path/hash entries",
            )
            continue
        key = match.group("key")
        if key in parts:
            _add(problems, f"Replacement visual contract duplicates {key}")
        parts[key] = f"{match.group('path')} @ sha256:{match.group('sha256')}"
    if set(parts) != {"target", "ui-design", "wireframe", "prd"}:
        _add(
            problems,
            "Replacement visual contract when not_required must contain exactly "
            "target, ui-design, wireframe, and prd path/hash entries",
        )
    return parts


def _source_identity(value: str | None) -> dict[str, str] | None:
    """Return one parsed source identity without performing filesystem I/O.

    Harness and the design-system compiler need the exact identities already
    recorded by this contract.  Keeping this parser here avoids each consumer
    re-implementing regular expressions (and accidentally accepting a subtly
    different path or digest).
    """

    match = SOURCE_RE.fullmatch((value or "").strip()) if value else None
    if match is None:
        return None
    return {"path": match.group("path"), "sha256": match.group("sha256")}


def parse_ui_contract_view(text: str) -> tuple[dict[str, Any], list[str]]:
    """Return the read-only authority view consumed by downstream joins.

    This intentionally parses only values that are already part of the UI
    contract.  It does not approve, resolve, or mutate anything; callers still
    run :func:`validate` for the full publication gate.  The returned view is
    stable across consumers and includes source identities, the approved target
    and typed capture scope, the Design System Need Gate decision, pair or
    replacement linkage, and the canonical approval digest.
    """

    active = active_text(text)
    source_section = _section(active, "## Source Product Definition") or ""
    wireframe_section = _section(active, wireframe_heading(active)) or ""
    style_section = _section(active, "## Style Integration") or ""
    visual_section = _section(active, "## Visual Approval") or ""
    gate_section = _section(active, "## Design System Need Gate") or ""

    sources = {
        "prd": _source_identity(_field(source_section, "PRD source")),
        "architecture": _source_identity(
            _field(source_section, "Architecture source")
        ),
        "stack": _source_identity(_field(source_section, "Stack source")),
        "wireframe": _source_identity(_field(wireframe_section, "Wireframe")),
        "frozen_prd": _source_identity(
            _field(wireframe_section, "Frozen PRD basis")
        ),
        "hifi": _source_identity(
            _field(style_section, "Connected HiFi reference")
        ),
    }

    target_raw = _field(visual_section, "Approved target")
    target_match = TARGET_SOURCE_RE.fullmatch((target_raw or "").strip()) if target_raw else None
    parse_problems: list[str] = []
    target_scope = _target_scope(target_raw, "Approved target", parse_problems)
    approved_target = None
    if target_match is not None:
        approved_target = {
            "path": target_match.group("path"),
            "sha256": target_match.group("sha256"),
            "raw": target_raw,
            "scope": target_scope,
            "captureMode": target_match.group("captureMode"),
        }

    gate_decision = (_field(gate_section, "Decision") or "").strip().casefold()
    compiled_values = _field_values(gate_section, "Compiled design system pair")
    pending_pair = bool(
        compiled_values
        and compiled_values[0].strip().casefold() == PENDING_PAIR_VALUE.casefold()
    )
    disposition_value = _field(
        gate_section, "Existing design-system pair disposition"
    )
    disposition = None
    if disposition_value:
        disposition_match = PAIR_DISPOSITION_RE.fullmatch(disposition_value.strip())
        if disposition_match is not None:
            disposition = {
                "decision": disposition_match.group("decision").casefold(),
                "reason": disposition_match.group("reason").strip(),
                "owner": disposition_match.group("owner").strip(),
                "decidedOn": disposition_match.group("date"),
            }
    replacement_values = _field_values(
        gate_section, "Replacement visual contract when_not_required"
    ) or _field_values(gate_section, "Replacement visual contract when not_required")
    pair = None
    if compiled_values:
        pair_match = PAIR_RE.fullmatch(compiled_values[0].strip())
        if pair_match is not None:
            pair = {
                "markdown": {
                    "path": pair_match.group("markdown"),
                    "sha256": pair_match.group("markdown_sha256"),
                },
                "registry": {
                    "path": pair_match.group("registry"),
                    "sha256": pair_match.group("registry_sha256"),
                },
            }
    replacement = _replacement_parts(
        replacement_values[0] if replacement_values else None, parse_problems
    ) if replacement_values else {}

    view: dict[str, Any] = {
        "structure_review": is_structure_review(active),
        "source_identities": sources,
        # Short aliases keep the exported view ergonomic while the longer
        # names remain the canonical serialized shape.
        "sources": sources,
        "approved_target": approved_target,
        "target_scope": target_scope,
        "capture_mode": (
            target_scope.get("captureMode")
            if isinstance(target_scope, dict)
            else None
        ),
        "gate": {
            "decision": gate_decision or None,
            "pair": pair,
            "pending_pair": pending_pair,
            "existing_pair_disposition": disposition,
            "replacement": replacement,
        },
        "gate_decision": gate_decision or None,
        "design_system_pair": pair,
        "replacement": replacement,
        "canonical_ui_digest": canonical_ui_approval_sha256(text),
    }
    return view, parse_problems


# Public aliases for downstream skills that describe the result as a contract
# view rather than a parser. They intentionally point to the same read-only
# implementation so consumers cannot drift into separate regex grammars.
parse_ui_contract = parse_ui_contract_view
ui_contract_view = parse_ui_contract_view


def _score(value: str | None) -> int | None:
    if value is None or not re.fullmatch(r"\d{1,3}", value.strip()):
        return None
    score = int(value)
    return score if 0 <= score <= 100 else None


def _table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped[1:-1].split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        rows.append(cells)
    return rows


def _design_table(style: str, heading: str, columns: list[str], problems: list[str]) -> list[list[str]]:
    matches = list(re.finditer(rf"^{re.escape(heading)}\s*$", style, re.MULTILINE))
    if len(matches) != 1:
        _add(problems, f"Style Integration requires exactly one {heading!r}")
        return []
    body = re.split(r"^#{2,3} ", style[matches[0].end():], maxsplit=1, flags=re.MULTILINE)[0]
    normalized = []
    for line in body.splitlines():
        stripped = line.strip()
        if "|" in stripped:
            if not stripped.startswith("|"):
                stripped = "| " + stripped
            if not stripped.endswith("|"):
                stripped += " |"
        normalized.append(stripped)
    rows = _table_rows("\n".join(normalized))
    if not rows or rows[0] != columns or len(rows) == 1:
        _add(problems, f"{heading} requires its declared columns and at least one row")
        return []
    valid = []
    for row in rows[1:]:
        if len(row) != len(columns) or any(not _filled(cell) for cell in row):
            _add(problems, f"{heading} rows must fill every declared column")
        else:
            valid.append(row)
    return valid


def _direction_comparison(
    style: str, intake: str, scope: dict[str, Any] | None, problems: list[str],
    *, repo_root: Path | None = None,
) -> None:
    rows = _design_table(style, "### Direction comparison", [
        "Direction", "UI surface", "State", "Target", "Scenario", "Content basis", "Screenshot", "Rationale",
    ], problems)
    raw_surfaces = (scope or {}).get("surfaces", [])
    surfaces = {item["id"]: item for item in (raw_surfaces if isinstance(raw_surfaces, list) else [])
                if isinstance(item, dict) and isinstance(item.get("id"), str)}
    cases: dict[str, set[tuple[str, ...]]] = {}
    images: dict[str, set[str]] = {}
    for direction, surface_id, state, target, scenario, content, screenshot, _ in rows:
        if re.fullmatch(r"VD-R[1-9][0-9]*-[0-9]{2,}", direction) is None:
            _add(problems, "Direction comparison requires versioned VD-R<round>-<number> IDs")
        if scenario not in {"primary", "stress"}:
            _add(problems, "Direction comparison Scenario must be primary or stress")
        case = (surface_id, state, target, scenario, content)
        known = cases.setdefault(direction, set())
        if case in known:
            _add(problems, "Direction comparison duplicates a direction/case")
        known.add(case)
        surface = surfaces.get(surface_id)
        if scope is not None:
            responsive = surface.get("responsive", scope.get("responsive", {})) if surface else {}
            if (not surface or state not in surface.get("states", [])
                    or not isinstance(responsive, dict)
                    or not isinstance(responsive.get("targets"), list)
                    or target not in [str(value) for value in responsive.get("targets", [])]):
                _add(problems, "Direction comparison case is outside Approved target scope")
        if _source_syntax(screenshot, "Direction comparison Screenshot", problems):
            identity = SOURCE_RE.fullmatch(screenshot)
            if not identity.group("path").startswith("docs/design/directions/"):
                _add(problems, "Direction comparison Screenshot must be retained under docs/design/directions/")
            if Path(identity.group("path")).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                _add(problems, "Direction comparison Screenshot must name a PNG, JPEG, or WebP capture")
            images.setdefault(direction, set()).add(identity.group("sha256"))
            if repo_root is not None:
                before = len(problems)
                _resolve_source(screenshot, repo_root=repo_root, label="Direction comparison Screenshot", problems=problems)
                if len(problems) == before:
                    try:
                        from PIL import Image
                    except ImportError:
                        _add(problems, "Direction comparison Screenshot verification requires Pillow")
                        continue
                    try:
                        with Image.open(repo_root / identity.group("path")) as capture:
                            if capture.format not in {"PNG", "JPEG", "WEBP"}:
                                raise ValueError("unsupported capture format")
                            capture.verify()
                    except (OSError, ValueError, Image.DecompressionBombError) as exc:
                        _add(problems, f"Direction comparison Screenshot cannot be verified as an image: {exc}")
    expected = 3 if (_field(intake, "Direction mode") or "").casefold() == "three comparable directions" else 1
    if len(cases) != expected:
        _add(problems, f"Direction comparison requires exactly {expected} directions")
    selected = re.match(r"VD-R[1-9][0-9]*-[0-9]{2,}(?=\s|$)", _field(style, "Selected direction") or "")
    if selected is None or selected.group() not in cases:
        _add(problems, "Selected direction must name a compared direction")
    baseline = next(iter(cases.values()), set())
    for direction, direction_cases in cases.items():
        if direction_cases != baseline:
            _add(problems, "Direction comparison must use the same surface/state/target/scenario/content cases for every direction")
        if {case[3] for case in direction_cases} != {"primary", "stress"}:
            _add(problems, f"Direction comparison {direction} requires primary and stress cases")
        if scope is not None:
            platforms = {_surface_platform(surface) for surface in surfaces.values()}
            for platform in platforms:
                covered = {case[3] for case in direction_cases
                           if case[0] in surfaces and _surface_platform(surfaces[case[0]]) == platform}
                if covered != {"primary", "stress"}:
                    _add(problems, f"Direction comparison {direction} requires primary and stress cases for platform {platform}")
    image_sets = list(images.values())
    if any(left & right for i, left in enumerate(image_sets) for right in image_sets[i + 1:]):
        _add(problems, "Direction comparison cannot reuse an identical screenshot across directions")


def _surface_platform(surface: dict[str, Any]) -> str:
    semantics = surface.get("stackSemantics")
    if isinstance(semantics, dict) and isinstance(semantics.get("platform"), str):
        return semantics["platform"]
    return STACK_PLATFORM_BY_SURFACE_CLASS.get(surface.get("surfaceClass"), surface.get("captureMode", "web"))


def _platform_rules(style: str, scope: dict[str, Any] | None, problems: list[str]) -> None:
    rows = _design_table(style, "### Platform rules", [
        "Platform", "Navigation and input", "Typography", "Icons", "Density and layout",
        "Feedback and motion", "Native proof", "Sources",
    ], problems)
    platforms = set()
    for platform, _, typography, icons, _, _, native_proof, _ in rows:
        if platform in platforms:
            _add(problems, f"Platform rules duplicates {platform}")
        platforms.add(platform)
        if platform == "ios":
            if not all(term in typography.casefold() for term in ("system text styles", "dynamic type")):
                _add(problems, "iOS Platform rules Typography must address system text styles and Dynamic Type")
            if "sf symbols" not in icons.casefold():
                _add(problems, "iOS Platform rules Icons must address SF Symbols")
        expected_proof = "not_applicable" if platform == "web" else "required before expansion"
        if native_proof != expected_proof:
            _add(problems, f"Platform rules {platform} Native proof must be {expected_proof}")
    if scope is not None:
        expected = {_surface_platform(surface) for surface in scope["surfaces"]}
        if platforms != expected:
            _add(problems, "Platform rules must exactly cover Approved target platforms")


def _validate_motion_table(
    section: str, *, require_filled: bool, problems: list[str]
) -> dict[str, dict[str, str]]:
    rows = _table_rows(section)
    expected = [
        "intent id",
        "ui scope / region",
        "treatment",
        "purpose",
        "trigger",
        "draft prompt",
        "source",
        "static / reduced-motion fallback",
        "generation route",
        "status",
        "generation status",
    ]
    intents: dict[str, dict[str, str]] = {}
    if not rows or [cell.casefold() for cell in rows[0]] != expected:
        _add(problems, "Motion And Media Intent has no canonical eleven-column table")
        return intents
    if require_filled and not rows[1:]:
        _add(problems, "Motion And Media Intent has no decision row")
    seen: set[str] = set()
    for row in rows[1:]:
        if len(row) != len(expected):
            _add(problems, "Motion And Media Intent row has the wrong width")
            continue
        intent_id = row[0]
        if not MM_ID_RE.fullmatch(intent_id):
            _add(problems, f"invalid Motion And Media Intent ID {intent_id!r}")
        elif intent_id in seen:
            _add(problems, f"duplicate Motion And Media Intent ID {intent_id}")
        seen.add(intent_id)
        scope_match = MM_SCOPE_RE.fullmatch(row[1])
        if scope_match is None:
            _add(
                problems,
                f"{intent_id} UI scope / region must be 'UI-* / explicit region'",
            )
        if row[2].casefold() not in VALID_TREATMENTS:
            _add(problems, f"{intent_id} has invalid treatment {row[2]!r}")
        if require_filled and any(not _filled(cell) for cell in row):
            _add(problems, f"{intent_id} contains an empty value or placeholder")
        if require_filled and row[8].strip().casefold() == "authorized provider":
            _add(problems, f"{intent_id} requires a concrete generation route, not authorized provider")
        if require_filled and "motion" in row[2].casefold() and row[8].strip().casefold() == "none":
            _add(problems, f"{intent_id} motion requires an implementation or media route, not none")
        status = row[9].casefold()
        if status == "blocked" or (
            require_filled and status not in VALID_MOTION_STATUSES
        ):
            _add(problems, f"{intent_id} has invalid status {row[9]!r}")
        if require_filled and row[10].casefold() != "deferred":
            _add(problems, f"{intent_id} has invalid generation status {row[10]!r}")
        else:
            intents[intent_id] = {
                "scope": row[1].strip(),
                "treatment": row[2],
                "purpose": row[3],
                "trigger": row[4],
                "draftPrompt": row[5],
                "source": row[6],
                "fallback": row[7],
                "generationRoute": row[8],
                "status": row[9],
                "generationStatus": row[10],
            }
    return intents


def _source_syntax(value: str | None, label: str, problems: list[str]) -> bool:
    if not _filled(value) or SOURCE_RE.fullmatch(value.strip()) is None:
        _add(
            problems,
            f"{label} must use '<repo-relative-path> @ sha256:<lowercase sha256>'",
        )
        return False
    return True


def _target_source_syntax(value: str | None, label: str, problems: list[str]) -> bool:
    match = TARGET_SOURCE_RE.fullmatch(value.strip()) if value else None
    if not _filled(value) or match is None:
        _add(
            problems,
            f"{label} must use '<repo-relative-path> @ sha256:<lowercase sha256>; "
            "scope=<one-line JSON scope contract>'",
        )
        return False
    if any(not match.group(name).strip() for name in ("surfaces", "routes", "states", "responsive", "tolerance", "deviations")):
        _add(problems, f"{label} scope fields must be concrete and non-empty")
        return False
    return True


def _target_scope(value: str | None, label: str, problems: list[str]) -> dict[str, Any] | None:
    match = TARGET_SOURCE_RE.fullmatch((value or "").strip()) if value else None
    if match is None:
        return None
    try:
        scope = {
            "surfaces": json.loads(match.group("surfaces")),
            "responsive": json.loads(match.group("responsive")),
            "tolerance": json.loads(match.group("tolerance")),
            "allowedDeviations": json.loads(match.group("deviations")),
            "captureMode": match.group("captureMode"),
            "routes": json.loads(match.group("routes")),
            "states": json.loads(match.group("states")),
        }
    except json.JSONDecodeError as exc:
        _add(problems, f"{label} scope fields must be one-line JSON values: {exc}")
        return None
    if set(scope) != {"surfaces", "responsive", "tolerance", "allowedDeviations", "captureMode", "routes", "states"}:
        _add(problems, f"{label} scope has unexpected keys")
        return None
    surfaces = scope["surfaces"]
    allowed_surface_keys = {
        "id",
        "route",
        "states",
        "surfaceClass",
        "releaseSurface",
        "captureMode",
        "responsive",
        "stackSemantics",
    }
    if (
        not isinstance(surfaces, list)
        or not surfaces
        or any(
            not isinstance(item, dict)
            or not set(item).issubset(allowed_surface_keys)
            or not {"id", "route", "states"}.issubset(set(item))
            or not isinstance(item.get("id"), str)
            or not isinstance(item.get("route"), str)
            or not isinstance(item.get("states"), list)
            or any(not isinstance(state, str) for state in item.get("states", []))
            for item in surfaces
        )
        or len({item["id"] for item in surfaces if isinstance(item, dict)}) != len(surfaces)
    ):
        _add(problems, f"{label} scope surfaces must be unique objects with id, route, and states")
    responsive = scope["responsive"]
    if not isinstance(responsive, dict) or set(responsive) != {"kind", "targets"}:
        _add(problems, f"{label} scope responsive must contain kind and ordered targets")
    elif responsive.get("kind") not in {"viewports", "sizeClasses", "per-surface"} or not isinstance(responsive.get("targets"), list) or (responsive.get("kind") != "per-surface" and not responsive["targets"]):
        _add(problems, f"{label} scope responsive kind/targets are invalid")
    elif responsive.get("kind") == "viewports":
        targets = responsive["targets"]
        if (
            len(targets) < 3
            or any(not isinstance(item, (int, float)) or isinstance(item, bool) or item <= 0 for item in targets)
            or any(left >= right for left, right in zip(targets, targets[1:]))
        ):
            _add(problems, f"{label} scope viewports must be at least three ascending positive numbers")
    elif responsive.get("kind") == "sizeClasses":
        targets = responsive["targets"]
        if len(targets) < 2 or any(not isinstance(item, str) or not item.strip() for item in targets) or len(set(targets)) != len(targets):
            _add(problems, f"{label} scope sizeClasses must be at least two unique strings")
    for item in surfaces if isinstance(surfaces, list) else []:
        if not isinstance(item, dict):
            continue
        if "surfaceClass" in item and (not isinstance(item["surfaceClass"], str) or not item["surfaceClass"].strip()):
            _add(problems, f"{label} surfaceClass must be a non-empty string")
        if "releaseSurface" in item and (not isinstance(item["releaseSurface"], str) or not item["releaseSurface"].strip()):
            _add(problems, f"{label} releaseSurface must be a non-empty string")
        if "captureMode" in item and item["captureMode"] not in {"hosted-browser", "browser-extension", "native", "desktop"}:
            _add(problems, f"{label} surface captureMode is invalid")
        if "stackSemantics" in item and (
            not isinstance(item["stackSemantics"], dict)
            or set(item["stackSemantics"]) != STACK_SEMANTIC_KEYS
            or any(not isinstance(item["stackSemantics"].get(key), str) or not item["stackSemantics"][key].strip() for key in STACK_SEMANTIC_KEYS)
        ):
            _add(problems, f"{label} surface stackSemantics must contain exactly four non-empty string fields")
        if "responsive" in item:
            item_responsive = item["responsive"]
            if not isinstance(item_responsive, dict) or set(item_responsive) != {"kind", "targets"}:
                _add(problems, f"{label} surface responsive must contain kind and targets")
            elif item_responsive.get("kind") not in {"viewports", "sizeClasses"} or not isinstance(item_responsive.get("targets"), list) or not item_responsive["targets"]:
                _add(problems, f"{label} surface responsive kind/targets are invalid")
            elif item_responsive.get("kind") == "viewports":
                targets = item_responsive["targets"]
                if len(targets) < 3 or any(not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0 for value in targets) or any(left >= right for left, right in zip(targets, targets[1:])):
                    _add(problems, f"{label} surface viewports must be at least three ascending positive numbers")
            else:
                targets = item_responsive["targets"]
                if len(targets) < 2 or any(not isinstance(value, str) or not value.strip() for value in targets) or len(set(targets)) != len(targets):
                    _add(problems, f"{label} surface sizeClasses must be at least two unique strings")
    hybrid_surface_contract = (
        scope.get("captureMode") == "mixed"
        or any(
            isinstance(item, dict)
            and any(key in item for key in ("surfaceClass", "releaseSurface", "captureMode", "responsive"))
            for item in surfaces if isinstance(surfaces, list)
        )
    )
    if hybrid_surface_contract and isinstance(surfaces, list):
        required_hybrid_fields = {"releaseSurface", "surfaceClass", "captureMode", "responsive"}
        for item in surfaces:
            if isinstance(item, dict) and not required_hybrid_fields.issubset(item):
                _add(problems, f"{label} hybrid surfaces require releaseSurface, surfaceClass, captureMode, and responsive")
        modes = {item.get("captureMode") for item in surfaces if isinstance(item, dict)}
        if len(modes) > 1 and scope.get("captureMode") != "mixed":
            _add(problems, f"{label} hybrid surfaces with multiple capture modes require captureMode=mixed")
    if not isinstance(scope["routes"], list) or not isinstance(scope["states"], list):
        _add(problems, f"{label} scope routes and states must be JSON arrays")
    elif len([route for route in scope["routes"] if isinstance(route, str) and route.casefold() not in {"n/a", "na"}]) != len({route for route in scope["routes"] if isinstance(route, str) and route.casefold() not in {"n/a", "na"}}):
        _add(problems, f"{label} scope routes must not duplicate non-n/a routes")
    if not isinstance(scope["tolerance"], str) or not scope["tolerance"].strip():
        _add(problems, f"{label} scope tolerance must be non-empty")
    if not isinstance(scope["allowedDeviations"], list) or any(not isinstance(item, str) for item in scope["allowedDeviations"]):
        _add(problems, f"{label} scope allowedDeviations must be a string array")
    return scope


def _pair_syntax(value: str | None, problems: list[str]) -> bool:
    if not _filled(value) or PAIR_RE.fullmatch(value.strip()) is None:
        _add(
            problems,
            "Compiled design system pair must use '<markdown path> @ sha256:<lowercase "
            "sha256> and <json path> @ sha256:<lowercase sha256>'",
        )
        return False
    return True


def _resolve_source(
    value: str | None,
    *,
    repo_root: Path,
    label: str,
    problems: list[str],
) -> None:
    match = SOURCE_RE.fullmatch((value or "").strip()) if value else None
    if match is None:
        return
    relative = match.group("path")
    parts = relative.split("/")
    if relative != relative.strip() or "\\" in relative or any(
        part in {"", ".", ".."} for part in parts
    ):
        _add(problems, f"{label} path must use canonical POSIX segments: {relative}")
        return
    candidate = repo_root / relative
    cursor = repo_root
    for part in parts:
        cursor = cursor / part
        try:
            info = cursor.lstat()
        except OSError as exc:
            _add(problems, f"{label} path cannot be inspected: {exc}")
            return
        if stat.S_ISLNK(info.st_mode) or bool(
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            _add(problems, f"{label} path must not traverse a symlink or reparse point")
            return
    try:
        candidate.resolve(strict=False).relative_to(repo_root.resolve())
    except ValueError:
        _add(problems, f"{label} path escapes repo-root: {relative}")
        return
    if not candidate.is_file():
        _add(problems, f"{label} path does not exist: {relative}")
        return
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != match.group("sha256"):
        _add(problems, f"{label} sha256 does not match current bytes: {relative}")


def _resolve_ui_design_digest(
    ui_design_path: Path,
    *,
    repo_root: Path,
    expected_digest: str,
    label: str,
    problems: list[str],
) -> None:
    try:
        text = ui_design_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _add(problems, f"{label} cannot read UI design source: {exc}")
        return
    if canonical_ui_approval_sha256(text) != expected_digest:
        _add(problems, f"{label} canonical UI approval sha256 does not match current bytes")


class _HiFiSurfaceParser(HTMLParser):
    """Collect only markers nested inside each explicit HiFi surface container."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.surfaces: dict[str, dict[str, Any]] = {}
        self.counts: dict[str, int] = {}
        self.nested: list[tuple[str, str]] = []
        self._stack: list[str] = []
        self._elements: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value for name, value in attrs}
        surface_id = values.get("data-ui-surface")
        if isinstance(surface_id, str):
            if self._stack:
                self.nested.append((self._stack[-1], surface_id))
            self.counts[surface_id] = self.counts.get(surface_id, 0) + 1
            self.surfaces.setdefault(
                surface_id,
                {
                    "route": set(),
                    "states": set(),
                    "targets": set(),
                    "cases": set(),
                    "navigation": set(),
                    "controls": set(),
                    "text": [],
                },
            )
            self._stack.append(surface_id)
        self._elements.append((tag.lower(), surface_id if isinstance(surface_id, str) else None))
        if not self._stack:
            return
        current = self.surfaces[self._stack[-1]]
        for attr, key in (
            ("data-state", "states"),
            ("data-responsive-target", "targets"),
        ):
            value = values.get(attr)
            if isinstance(value, str) and value.strip():
                current[key].add(value.strip())
        route = values.get("data-ui-route")
        if isinstance(surface_id, str) and isinstance(route, str) and route.strip():
            current["route"].add(route.strip())
        role = (values.get("role") or "").casefold()
        nav_valid = tag.lower() in {"a", "nav"} or role in {"link", "navigation", "menuitem", "tab"}
        control_valid = tag.lower() in {"button", "input", "select", "textarea"} or role in {
            "button", "checkbox", "combobox", "radio", "slider", "spinbutton", "switch", "tab", "textbox"
        }
        if nav_valid and isinstance(values.get("data-navigation-id"), str) and values["data-navigation-id"].strip():
            current["navigation"].add(values["data-navigation-id"].strip())
        if control_valid and isinstance(values.get("data-control-id"), str) and values["data-control-id"].strip():
            current["controls"].add(values["data-control-id"].strip())
        state_value = values.get("data-state")
        target_value = values.get("data-responsive-target")
        if isinstance(state_value, str) and state_value.strip() and isinstance(target_value, str) and target_value.strip():
            current["cases"].add((state_value.strip(), target_value.strip()))

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        for index in range(len(self._elements) - 1, -1, -1):
            element_tag, surface_id = self._elements[index]
            if element_tag != tag_name:
                continue
            self._elements = self._elements[:index]
            if surface_id is not None and self._stack and self._stack[-1] == surface_id:
                self._stack.pop()
            break

    def handle_data(self, data: str) -> None:
        if self._stack:
            self.surfaces[self._stack[-1]]["text"].append(data)


class _HiFiProductControls(HTMLParser):
    """Collect product controls; reviewer controls outside surfaces do not count."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, str | None]] = []
        self.controls: dict[tuple[str, str], list[dict[str, str | None]]] = {}
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        surface = values.get("data-ui-surface") or (self.stack[-1][1] if self.stack else None)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, surface))
        interactive = tag in {"a", "button", "select", "textarea", "input"} or values.get("role") in {"tab", "button", "link", "menuitem"}
        if surface and interactive:
            control = values.get("data-navigation-id") or values.get("data-control-id")
            if not control:
                self.errors.append(f"HiFi product control in {surface} needs a navigation/control ID")
            else:
                self.controls.setdefault((surface, control), []).append(dict(values, tag=tag))
        if tag == "a" and values.get("target") not in {None, "", "_self"}:
            self.errors.append("HiFi links must stay in the current review page")

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def _hifi_bundle_documents(path: Path, html: str, manifest: dict[str, Any]) -> dict[str, str]:
    """Bind sibling page bytes through the approved entry hash, without recursion."""
    if path.name != "index.html" or set(manifest) != {"schema", "surfaces", "pages", "interactions"}:
        raise ValueError("HiFi ui-hifi/2 requires index.html, surfaces, pages, and interactions")
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        raise ValueError("HiFi bundle pages must be an array")
    documents = {"index.html": html}
    for component in (path, *path.parents):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("HiFi entry must not cross symlinks or reparse points")
    seen = {"index.html"}
    for row in pages:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            raise ValueError("HiFi page must contain only path and sha256")
        name, digest = row.get("path"), row.get("sha256")
        if not isinstance(name, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*\.html", name) is None or name.casefold() in seen:
            raise ValueError("HiFi page paths must be unique sibling HTML filenames")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("HiFi page sha256 is invalid")
        seen.add(name.casefold())
        page = path.parent / name
        for component in (page, *page.parents):
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("HiFi page paths must not cross symlinks or reparse points")
        contents = page.read_bytes()
        if hashlib.sha256(contents).hexdigest() != digest:
            raise ValueError(f"HiFi page is stale: {name}")
        text = contents.decode("utf-8")
        if HIFI_MANIFEST_RE.search(text):
            raise ValueError("Only index.html may contain the HiFi bundle manifest")
        documents[name] = text
    return documents


def _validate_hifi_bundle(
    path: Path, html: str, manifest: dict[str, Any], problems: list[str], scope: dict[str, Any] | None,
    *, require_reviewer: bool = False, require_reviewer_v3: bool = False,
) -> None:
    try:
        documents = _hifi_bundle_documents(path, html, manifest)
    except (OSError, UnicodeError, ValueError) as exc:
        _add(problems, str(exc))
        return
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        _add(problems, "HiFi bundle surfaces must be non-empty")
        return
    by_id: dict[str, dict[str, Any]] = {}
    for surface in surfaces:
        if (
            not isinstance(surface, dict)
            or set(surface) - {"platformGroup"} != {"id", "page", "route", "states", "responsive", "navigation", "controls"}
            or not isinstance(surface.get("id"), str)
            or surface["id"] in by_id
            or not isinstance(surface.get("page"), str)
            or surface["page"] not in documents
        ):
            _add(problems, "HiFi bundle has an invalid, duplicate, or unmapped surface")
            return
        if "platformGroup" in surface and surface["platformGroup"] not in {"App", "Web", "Admin"}:
            _add(problems, "HiFi platformGroup must be App, Web or Admin")
        responsive = surface.get("responsive")
        if (
            not surface["id"].strip()
            or not isinstance(surface.get("route"), str)
            or not surface["route"].strip()
            or any(not isinstance(surface.get(key), list) or not surface[key] or any(not isinstance(value, str) or not value.strip() for value in surface[key]) for key in ("states", "navigation", "controls"))
            or not isinstance(responsive, dict)
            or set(responsive) != {"kind", "targets"}
            or responsive.get("kind") not in ("viewports", "sizeClasses")
            or not isinstance(responsive.get("targets"), list)
            or not responsive["targets"]
            or any(isinstance(value, bool) or not isinstance(value, (str, int)) for value in responsive["targets"])
        ):
            _add(problems, "HiFi bundle surface fields must be typed non-empty scope values")
            return
        by_id[surface["id"]] = surface
    if scope is not None and set(by_id) != {row.get("id") for row in scope.get("surfaces", [])}:
        _add(problems, "HiFi bundle surfaces must exactly match Approved target scope")
    # Historical schema-2 pages remain statically inspectable; a fresh connected
    # check still requires the current shell through require_reviewer below.
    current_reviewer = has_current_reviewer_shell(documents)
    if require_reviewer or current_reviewer:
        reviewer_errors, _ = reviewer_contract(documents, manifest)
        problems.extend(reviewer_errors)
    problems.extend(product_control_findings(documents))
    if require_reviewer_v3:
        for name, page_html in documents.items():
            parser = ReviewerParser()
            parser.feed(page_html)
            parser.close()
            shells = [attrs for tag, attrs, _ in parser.nodes
                      if tag == "aside" and "data-hifi-reviewer-shell" in attrs]
            if len(shells) != 1 or shells[0].get("data-hifi-reviewer-version") != "3":
                _add(problems, f"HiFi {name} requires reviewer shell version 3 for new Visual Approval")
    product_controls: dict[tuple[str, str], list[dict[str, str | None]]] = {}
    for name, page_html in documents.items():
        page_surfaces = [{key: value for key, value in row.items() if key not in {"page", "platformGroup"}} for row in surfaces if row["page"] == name]
        if not page_surfaces:
            _add(problems, f"HiFi bundle page has no product surface: {name}")
            continue
        legacy_manifest = '<script id="ui-hifi-manifest" type="application/json">' + json.dumps({"schema": "ui-hifi/1", "surfaces": page_surfaces}) + '</script>'
        checked_html = HIFI_MANIFEST_RE.sub(lambda _: legacy_manifest, page_html) if name == "index.html" else page_html + legacy_manifest
        page_scope = dict(scope or {}, surfaces=[row for row in (scope or {}).get("surfaces", page_surfaces) if row.get("id") in {item["id"] for item in page_surfaces}])
        # Each page validates its own surface targets, not the global hybrid set.
        page_scope.pop("responsive", None)
        page_scope["surfaces"] = [dict(row, responsive=row.get("responsive", (scope or {}).get("responsive"))) for row in page_scope["surfaces"]]
        _validate_hifi_html(checked_html, problems, page_scope, local_pages=set(documents))
        parser = _HiFiProductControls()
        parser.feed(page_html)
        parser.close()
        problems.extend(parser.errors)
        for key, values in parser.controls.items():
            product_controls.setdefault(key, []).extend(values)
    if problems:
        return
    interactions = manifest.get("interactions")
    if not isinstance(interactions, list) or not interactions:
        _add(problems, "HiFi bundle requires product interactions")
        return
    ids: set[str] = set()
    covered: set[tuple[str, str]] = set()
    for action in interactions:
        if not isinstance(action, dict) or set(action) != {"id", "source", "control", "kind", "destination"}:
            _add(problems, "HiFi interaction key set is invalid")
            continue
        identifier, control = action.get("id"), action.get("control")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in ids or not isinstance(control, str):
            _add(problems, "HiFi interaction IDs must be unique and control must be a string")
            continue
        ids.add(identifier)
        valid = True
        for endpoint in (action.get("source"), action.get("destination")):
            if not isinstance(endpoint, dict) or set(endpoint) != {"surface", "state"} or not isinstance(endpoint.get("surface"), str) or endpoint["surface"] not in by_id or endpoint.get("state") not in by_id[endpoint["surface"]]["states"]:
                _add(problems, f"HiFi interaction {identifier} has an unknown endpoint")
                valid = False
        if not valid:
            continue
        source = by_id[action["source"]["surface"]]
        destination = by_id[action["destination"]["surface"]]
        key = (source["id"], control)
        controls = product_controls.get(key, [])
        covered.add(key)
        if not controls or control not in source["navigation"] + source["controls"]:
            _add(problems, f"HiFi interaction {identifier} is not bound to a product control")
        if action["kind"] == "navigate":
            if any(item.get("tag") != "a" or item.get("href") != destination["page"] for item in controls):
                _add(problems, f"HiFi interaction {identifier} link must reach its declared page")
        elif action["kind"] == "state":
            if source["page"] != destination["page"]:
                _add(problems, "HiFi state interaction must stay on the same page")
            if action["source"] == action["destination"]:
                _add(problems, "HiFi state interaction must declare an observable destination state")
        else:
            _add(problems, "HiFi interaction kind must be navigate or state")
    declared = {(row["id"], control) for row in surfaces for control in row["navigation"] + row["controls"]}
    if covered != declared or set(product_controls) != declared:
        _add(problems, "HiFi interactions must cover every declared and rendered product control")
    reachable = {"index.html"}
    for _ in documents:
        for action in interactions:
            if isinstance(action, dict) and action.get("kind") == "navigate":
                source = action.get("source", {})
                destination = action.get("destination", {})
                if isinstance(source, dict) and isinstance(destination, dict):
                    start = by_id.get(str(source.get("surface")), {}).get("page")
                    end = by_id.get(str(destination.get("surface")), {}).get("page")
                    if start in reachable and end in documents:
                        reachable.add(end)
    if reachable != set(documents):
        _add(problems, "HiFi pages must be reachable from index.html through product navigation")


def _validate_hifi_surface(
    path: Path, problems: list[str], scope: dict[str, Any] | None = None,
    *, require_connected: bool = False, require_reviewer_v3: bool = False,
) -> None:
    try:
        html = path.read_text(encoding="utf-8")
        matches = list(HIFI_MANIFEST_RE.finditer(html))
        manifest = json.loads(matches[0].group("data")) if len(matches) == 1 else None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(problems, f"Connected HiFi reference cannot be read: {exc}")
        return
    if isinstance(manifest, dict) and manifest.get("schema") == "ui-hifi/2":
        _validate_hifi_bundle(path, html, manifest, problems, scope,
                              require_reviewer=require_connected, require_reviewer_v3=require_reviewer_v3)
    else:
        if require_connected:
            _add(problems, "Visual approval requires ui-hifi/2; schema-1 HiFi is inspection-only")
        _validate_hifi_html(html, problems, scope)


def _validate_hifi_html(
    html: str, problems: list[str], scope: dict[str, Any] | None = None,
    *, local_pages: set[str] | None = None,
) -> None:
    """Apply only the generic self-contained HTML safety rules to HiFi."""

    if re.search(r"<html\b", html, re.IGNORECASE) is None or re.search(r"<body\b", html, re.IGNORECASE) is None:
        _add(problems, "Connected HiFi reference must contain meaningful <html> and <body> elements")
    visible = re.sub(r"<script\b[\s\S]*?</script>|<style\b[\s\S]*?</style>|<[^>]+>", " ", html, flags=re.IGNORECASE)
    if len(re.sub(r"\s+", "", visible)) < 20:
        _add(problems, "Connected HiFi reference must contain meaningful visible content")
    if scope is not None:
        if re.search(r"<(?:nav|button|a)\b", html, re.IGNORECASE) is None:
            _add(problems, "Connected HiFi reference must expose reviewer navigation/state controls")
        for surface in scope.get("surfaces", []):
            surface_id = surface.get("id") if isinstance(surface, dict) else None
            if not isinstance(surface_id, str) or re.search(
                rf"data-ui-surface=[\"']{re.escape(surface_id)}[\"']", html, re.IGNORECASE
            ) is None:
                _add(problems, f"Connected HiFi reference is missing surface coverage for {surface_id}")
            for state in surface.get("states", []) if isinstance(surface, dict) else []:
                if re.search(rf"data-state=[\"']{re.escape(str(state))}[\"']", html, re.IGNORECASE) is None:
                    _add(problems, f"Connected HiFi reference is missing state coverage for {surface_id}/{state}")
        responsive = scope.get("responsive", {})
        for target in responsive.get("targets", []) if isinstance(responsive, dict) else []:
            if re.search(rf"data-responsive-target=[\"']{re.escape(str(target))}[\"']", html, re.IGNORECASE) is None:
                _add(problems, f"Connected HiFi reference is missing responsive target coverage for {target}")
    class BundleResourceParser(check_wireframe_html.ResourceParser):
        def _record_url(self, tag: str, name: str, value: str) -> None:
            if tag == "a" and name == "href" and local_pages is not None and (value in local_pages or ("index.html" in local_pages and value in {"index.html#overview", "index.html#design-tokens"})):
                return
            super()._record_url(tag, name, value)

    parser = BundleResourceParser()
    parser.feed(html)
    parser.close()
    for finding in parser.csp_document_errors:
        _add(problems, finding)
    if len(parser.content_security_policies) != 1:
        _add(
            problems,
            "Connected HiFi reference must contain exactly one canonical restrictive CSP meta",
        )
    else:
        policy = parser.content_security_policies[0]
        if local_pages is not None:
            expected = check_wireframe_html.REQUIRED_HIFI_CSP.replace("navigate-to 'none'", "navigate-to 'self'")
            if policy != expected:
                _add(problems, "Connected HiFi bundle must use the exact local-page CSP policy")
            policy = policy.replace("navigate-to 'self'", "navigate-to 'none'")
        for finding in check_wireframe_html.validate_hifi_csp_policy(policy):
            _add(problems, finding)
    if parser.duplicate_attributes:
        _add(problems, "Connected HiFi reference has duplicate HTML attributes")
    if parser.link_tags:
        _add(problems, "Connected HiFi reference must not contain <link> resources")
    resources = parser.external_resources + parser.external_css_resources
    if resources:
        _add(problems, "Connected HiFi reference must not load external resources: " + ", ".join(resources))
    if parser.css_imports:
        _add(problems, "Connected HiFi reference must not contain CSS @import")
    if parser.active_security_surfaces:
        _add(
            problems,
            "Connected HiFi reference must not contain active external or executable surfaces: "
            + ", ".join(parser.active_security_surfaces),
        )
    manifest_matches = list(HIFI_MANIFEST_RE.finditer(html))
    if len(manifest_matches) != 1:
        _add(problems, "Connected HiFi reference must contain exactly one ui-hifi/1 manifest")
        return
    try:
        manifest = json.loads(manifest_matches[0].group("data"))
    except json.JSONDecodeError as exc:
        _add(problems, f"Connected HiFi ui-hifi/1 manifest is invalid JSON: {exc}")
        return
    if not isinstance(manifest, dict) or set(manifest) != {"schema", "surfaces"} or manifest.get("schema") != "ui-hifi/1":
        _add(problems, "Connected HiFi manifest must be ui-hifi/1 with only surfaces")
        return
    manifest_surfaces = manifest.get("surfaces")
    if not isinstance(manifest_surfaces, list):
        _add(problems, "Connected HiFi manifest surfaces must be an array")
        return
    manifest_by_id: dict[str, dict[str, Any]] = {}
    for item in manifest_surfaces:
        if not isinstance(item, dict) or set(item) != {"id", "route", "states", "responsive", "navigation", "controls"}:
            _add(problems, "Connected HiFi manifest surface has an invalid key set")
            continue
        surface_id = item.get("id")
        if not isinstance(surface_id, str) or surface_id in manifest_by_id:
            _add(problems, "Connected HiFi manifest surface IDs must be unique strings")
            continue
        if not isinstance(item.get("states"), list) or any(not isinstance(state, str) for state in item["states"]):
            _add(problems, f"Connected HiFi manifest {surface_id} states must be string array")
        responsive = item.get("responsive")
        if not isinstance(responsive, dict) or set(responsive) != {"kind", "targets"} or not isinstance(responsive.get("targets"), list):
            _add(problems, f"Connected HiFi manifest {surface_id} responsive is invalid")
        for key in ("navigation", "controls"):
            if not isinstance(item.get(key), list) or not item[key] or any(not isinstance(value, str) or not value.strip() for value in item[key]):
                _add(problems, f"Connected HiFi manifest {surface_id} {key} coverage must be non-empty strings")
        manifest_by_id[surface_id] = item
    if scope is not None:
        expected_by_id = {item.get("id"): item for item in scope.get("surfaces", []) if isinstance(item, dict)}
        if set(manifest_by_id) != set(expected_by_id):
            _add(problems, "Connected HiFi manifest surfaces must exactly match Approved target scope")
        dom_parser = _HiFiSurfaceParser()
        dom_parser.feed(html)
        dom_parser.close()
        if set(dom_parser.counts) != set(expected_by_id):
            _add(problems, "Connected HiFi DOM surfaces must exactly match the surfaces assigned to this page")
        for parent_surface, nested_surface in dom_parser.nested:
            _add(problems, f"Connected HiFi DOM must not nest surface {nested_surface} inside {parent_surface}")
        for surface_id, expected in expected_by_id.items():
            actual = manifest_by_id.get(surface_id)
            if actual is None:
                continue
            expected_responsive = expected.get("responsive") or scope.get("responsive")
            if actual.get("route") != expected.get("route") or actual.get("states") != expected.get("states") or actual.get("responsive") != expected_responsive:
                _add(problems, f"Connected HiFi manifest {surface_id} does not match Approved target scope")
            container = dom_parser.surfaces.get(surface_id)
            if dom_parser.counts.get(surface_id, 0) != 1:
                _add(problems, f"Connected HiFi DOM must contain exactly one non-nested container for {surface_id}")
            if container is None:
                _add(problems, f"Connected HiFi DOM is missing a container for {surface_id}")
                continue
            expected_targets = {str(item) for item in expected_responsive.get("targets", [])} if isinstance(expected_responsive, dict) else set()
            if container["route"] != {expected.get("route")}:
                _add(problems, f"Connected HiFi DOM route binding is wrong for {surface_id}")
            if container["states"] != {str(item) for item in expected.get("states", [])}:
                _add(problems, f"Connected HiFi DOM state coverage is wrong for {surface_id}")
            if container["targets"] != expected_targets:
                _add(problems, f"Connected HiFi DOM responsive target coverage is wrong for {surface_id}")
            expected_cases = {
                (str(state), str(target))
                for state in expected.get("states", [])
                for target in (
                    expected_responsive.get("targets", [])
                    if isinstance(expected_responsive, dict)
                    else []
                )
            }
            if container["cases"] != expected_cases:
                _add(problems, f"Connected HiFi DOM state/target case coverage is wrong for {surface_id}")
            if not set(actual.get("navigation", [])) <= container["navigation"]:
                _add(problems, f"Connected HiFi DOM navigation coverage is incomplete for {surface_id}")
            if not set(actual.get("controls", [])) <= container["controls"]:
                _add(problems, f"Connected HiFi DOM control coverage is incomplete for {surface_id}")
            if len("".join(container["text"]).strip()) < 20:
                _add(problems, f"Connected HiFi DOM content is not meaningful for {surface_id}")


def _read_wireframe_data(path: Path, problems: list[str]) -> dict[str, Any] | None:
    try:
        html = path.read_text(encoding="utf-8")
        match = WIREFRAME_DATA_RE.search(html)
        if match is None:
            _add(problems, "wireframe-data is missing from the recorded wireframe")
            return None
        value = json.loads(match.group("data"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(problems, f"cannot read recorded wireframe data: {exc}")
        return None
    if not isinstance(value, dict):
        _add(problems, "recorded wireframe data must be a JSON object")
        return None
    return value


def _approved_stack_semantics(stack_text: str) -> dict[str, dict[str, str]]:
    """Normalize executable Stack layer selections by target family."""

    active = active_text(stack_text)
    layer_map = {
        "rendering model": "renderingModel",
        "component foundation": "componentFoundation",
        "styling approach": "stylingMechanism",
        "client strategy": "renderingModel",
        "framework": "componentFoundation",
    }
    sections = {
        "frontend": "Frontend Technology Decision",
        "mobile": "Mobile/Desktop Technology Decision",
    }
    result: dict[str, dict[str, str]] = {}
    for family, heading in sections.items():
        match = re.search(
            rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s|\Z)",
            active,
            re.MULTILINE,
        )
        if match is None:
            continue
        rows = re.findall(
            r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
            match.group(1),
            re.MULTILINE,
        )
        values: dict[str, str] = {}
        for layer, selection, status in rows:
            key = layer.strip().casefold()
            if key not in layer_map or status.strip().casefold() not in {"required", "selected", "approved"}:
                continue
            normalized_key = layer_map[key]
            if key in {"rendering model", "component foundation", "styling approach"} or normalized_key not in values:
                values[normalized_key] = selection.strip()
        if values:
            result[family] = values
    return result


def _validate_stack_semantics_join(
    scope: dict[str, Any],
    *,
    stack_text: str,
    problems: list[str],
) -> None:
    """Require Approved target stackSemantics to equal approved Stack rows."""

    approved = _approved_stack_semantics(stack_text)
    if not approved:
        _add(problems, "Approved target stackSemantics cannot be derived from approved Stack selections")
        return
    surfaces = scope.get("surfaces") if isinstance(scope.get("surfaces"), list) else []
    for surface in surfaces:
        if not isinstance(surface, dict):
            continue
        surface_id = surface.get("id")
        surface_class = str(surface.get("surfaceClass", "")).casefold()
        family = "mobile" if surface_class in {"ios", "android", "macos", "windows", "desktop"} else "frontend"
        selected = approved.get(family)
        if selected is None:
            _add(problems, f"Approved target surface {surface_id} has no approved {family} Stack selections")
            continue
        recorded = surface.get("stackSemantics")
        if not isinstance(recorded, dict) or set(recorded) != STACK_SEMANTIC_KEYS:
            _add(
                problems,
                f"Approved target surface {surface_id} stackSemantics must contain exactly "
                "platform, renderingModel, componentFoundation, and stylingMechanism",
            )
            continue
        expected_platform = STACK_PLATFORM_BY_SURFACE_CLASS.get(surface_class)
        if expected_platform and recorded.get("platform") != expected_platform:
            _add(problems, f"Approved target surface {surface_id} stackSemantics.platform does not match surfaceClass")
        for key in ("renderingModel", "componentFoundation", "stylingMechanism"):
            value = recorded.get(key)
            if not isinstance(value, str) or not value.strip():
                _add(problems, f"Approved target surface {surface_id} stackSemantics.{key} must be non-empty")
            elif key not in selected:
                _add(problems, f"Approved Stack has no executable selection for {key} on surface {surface_id}")
            elif value.strip().casefold() != selected[key].strip().casefold():
                _add(problems, f"Approved target surface {surface_id} stackSemantics.{key} does not match approved Stack selection")


def _validate_target_scope_join(
    scope: dict[str, Any],
    *,
    prd_path: Path,
    wireframes_path: Path,
    stack_text: str,
    architecture_text: str,
    problems: list[str],
) -> None:
    try:
        prd_text = prd_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        _add(problems, f"cannot read PRD for Approved target scope join: {exc}")
        return
    wireframe_data = _read_wireframe_data(wireframes_path, problems)
    if wireframe_data is None:
        return
    _validate_stack_semantics_join(scope, stack_text=stack_text, problems=problems)
    prd_surfaces, prd_findings = parse_prd_ui_contract(
        prd_text,
        require_responsive=True,
        require_copy=wireframe_data.get("schema") in {"wireframes/4", "wireframes/5"},
        web_floor=3 if wireframe_data.get("schema") in check_wireframe_html.INTERACTIVE_WIREFRAME_SCHEMAS else 2,
    )
    problems.extend(f"target scope PRD: {finding}" for finding in prd_findings)
    target_by_id = {item.get("id"): item for item in scope.get("surfaces", []) if isinstance(item, dict)}
    if set(target_by_id) != set(prd_surfaces):
        _add(problems, "Approved target surfaces must exactly match PRD UI-* identities")
    screens = {
        item.get("id"): item
        for item in (wireframe_data.get("screens") or [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if set(target_by_id) != set(screens):
        _add(problems, "Approved target surfaces must exactly match wireframe screen identities")
    for surface_id, target in target_by_id.items():
        prd = prd_surfaces.get(surface_id)
        screen = screens.get(surface_id)
        if prd is None or screen is None:
            continue
        expected_states = list(prd.get("states", []))
        if target.get("route") != (prd.get("routes") or [None])[0] or target.get("states") != expected_states:
            _add(problems, f"Approved target surface {surface_id} route/states differ from PRD")
        for target_field, prd_field in (
            ("releaseSurface", "releaseSurface"),
            ("surfaceClass", "surfaceClass"),
            ("captureMode", "captureMode"),
        ):
            if target_field in target and target.get(target_field) != prd.get(prd_field):
                _add(
                    problems,
                    f"Approved target surface {surface_id} {target_field} differs from PRD",
                )
        target_responsive = target.get("responsive")
        if isinstance(target_responsive, dict):
            expected_responsive = {
                "kind": prd.get("responsiveKind"),
                "targets": [
                    int(value) if isinstance(value, str) and value.isdigit() else value
                    for value in prd.get("responsiveTargets", [])
                ],
            }
            if target_responsive != expected_responsive:
                _add(problems, f"Approved target surface {surface_id} responsive set differs from PRD")
        if target.get("route") != screen.get("route") or {str(item).casefold() for item in target.get("states", [])} != _screen_state_ids(screen):
            _add(problems, f"Approved target surface {surface_id} route/states differ from wireframe")
        if isinstance(wireframe_data.get("responsiveBySurface"), dict):
            wireframe_responsive = wireframe_data["responsiveBySurface"].get(surface_id)
            comparable_wireframe_responsive = (
                {
                    "kind": wireframe_responsive.get("kind"),
                    "targets": wireframe_responsive.get("targets"),
                }
                if isinstance(wireframe_responsive, dict)
                else None
            )
            if target.get("responsive") != comparable_wireframe_responsive:
                _add(problems, f"Approved target surface {surface_id} responsive set differs from wireframe")
    expected_routes = [target.get("route") for target in scope.get("surfaces", [])]
    expected_states = sorted({str(state) for target in scope.get("surfaces", []) for state in target.get("states", [])})
    if scope.get("routes") != expected_routes:
        _add(problems, "Approved target routes array must equal the ordered surface route union")
    if scope.get("states") != expected_states:
        _add(problems, "Approved target states array must equal the sorted surface state union")
    responsive = scope.get("responsive")
    responsive_by_surface = wireframe_data.get("responsiveBySurface") if isinstance(wireframe_data.get("responsiveBySurface"), dict) else None
    wire_kind = "viewports" if isinstance(wireframe_data.get("viewports"), list) else "sizeClasses"
    wire_targets = wireframe_data.get(wire_kind) or []
    wire_targets = [int(value) if isinstance(value, float) and value.is_integer() else value for value in wire_targets]
    prd_sets = {(entry.get("responsiveKind"), tuple(entry.get("responsiveTargets", []))) for entry in prd_surfaces.values()}
    expected_prd = next(iter(prd_sets), (None, ()))
    target_targets = responsive.get("targets") if isinstance(responsive, dict) else None
    if scope.get("captureMode") != "mixed" and responsive_by_surface is None:
        if not isinstance(responsive, dict) or responsive.get("kind") != wire_kind or list(target_targets or []) != list(wire_targets):
            _add(problems, "Approved target responsive kind/targets must match wireframe")
        if expected_prd[0] != wire_kind or [str(item) for item in expected_prd[1]] != [str(item) for item in wire_targets]:
            _add(problems, "Approved target responsive kind/targets must match PRD")
    capture = scope.get("captureMode")
    release_contract, release_findings = parse_release_targets(architecture_text)
    problems.extend(f"target scope Release Targets: {finding}" for finding in release_findings)
    release_classes = {
        surface_class
        for target in release_contract.targets
        for surface_class in [_release_surface_class(target)]
        if surface_class is not None
    }
    release_by_surface = {
        target.surface: target
        for target in release_contract.targets
        if isinstance(getattr(target, "surface", None), str)
    }
    expected_modes_by_class = {
        "hosted_web": "hosted-browser",
        "browser_extension": "browser-extension",
        "ios": "native",
        "android": "native",
        "react-native": "native",
        "flutter": "native",
        "macos": "desktop",
        "windows": "desktop",
        "desktop": "desktop",
    }
    expected = {expected_modes_by_class[item] for item in release_classes if item in expected_modes_by_class}
    surface_contracts = [item for item in scope.get("surfaces", []) if isinstance(item, dict) and "surfaceClass" in item]
    if surface_contracts:
        if len(surface_contracts) != len(scope.get("surfaces", [])):
            _add(problems, "Hybrid Approved target requires surfaceClass on every surface")
        for item in surface_contracts:
            surface_class = str(item.get("surfaceClass", "")).casefold()
            mode = item.get("captureMode")
            release_surface = item.get("releaseSurface")
            release_target = release_by_surface.get(release_surface)
            if release_target is None:
                _add(problems, f"Approved target surface {item.get('id')} releaseSurface is absent from Release Targets")
            elif _release_surface_class(release_target) != surface_class:
                _add(problems, f"Approved target surface {item.get('id')} surfaceClass does not match releaseSurface")
            expected_mode = expected_modes_by_class.get(surface_class)
            if expected_mode and mode != expected_mode:
                _add(problems, f"Approved target surface {item.get('id')} captureMode does not match surfaceClass")
            item_responsive = item.get("responsive")
            if isinstance(item_responsive, dict):
                expected_kind = "sizeClasses" if mode in {"native", "desktop"} else "viewports"
                if item_responsive.get("kind") != expected_kind:
                    _add(problems, f"Approved target surface {item.get('id')} responsive kind does not match captureMode")
    else:
        if len(expected) != 1:
            _add(problems, "Approved target must resolve exactly one typed ReleaseTarget capture mode")
        elif capture not in expected:
            _add(problems, "Approved target captureMode must match the typed ReleaseTarget surface class")
        expected_kind = "sizeClasses" if capture in {"native", "desktop"} else "viewports"
        if capture in {"hosted-browser", "browser-extension", "native", "desktop"} and wire_kind != expected_kind:
            _add(problems, "Approved target responsive kind must match captureMode platform")


def _screen_state_ids(screen: dict[str, Any]) -> set[str]:
    return {
        str(item.get("id")).casefold()
        for item in (screen.get("states") or [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _release_surface_class(target: Any) -> str | None:
    value = getattr(target, "surface_class", None)
    return value.casefold() if isinstance(value, str) else None


def _relative_cli_path(path: Path, repo_root: Path, label: str, problems: list[str]) -> str | None:
    """Return a normalized repo-relative CLI path, rejecting outside paths."""

    root = repo_root.resolve()
    candidate = path.resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        _add(problems, f"{label} must be inside repo-root")
        return None
    return relative.as_posix()


def _require_exact_cli_path(
    argument: Path | None,
    recorded: str | None,
    *,
    repo_root: Path,
    label: str,
    problems: list[str],
) -> Path | None:
    if argument is None:
        _add(problems, f"approved validation requires --{label.lower().replace(' ', '-')}")
        return None
    if recorded is None:
        return None
    relative = _relative_cli_path(argument, repo_root, label, problems)
    if relative is None:
        return None
    match = SOURCE_RE.fullmatch(recorded.strip()) or TARGET_SOURCE_RE.fullmatch(recorded.strip())
    if match is None:
        return None
    expected = match.group("path")
    if relative.casefold() != expected.casefold():
        _add(problems, f"{label} CLI path must exactly match recorded path {expected}")
        return None
    return repo_root / expected


def _resolve_evidence(
    value: str | None,
    *,
    repo_root: Path,
    label: str,
    problems: list[str],
    expected_artifact: str | None = None,
    expected_check: str | None = None,
    expected_matrix: dict[str, list[str]] | None = None,
    expected_motion: dict[str, Any] | None = None,
    require_machine: bool = False,
    recorded_scores: dict[str, int | None] | None = None,
    required_inputs: list[dict[str, str]] | None = None,
) -> None:
    parsed = _pass_evidence(value, label, problems)
    if parsed is None:
        return
    evidence_path = (repo_root / parsed["path"]).resolve()
    try:
        evidence_path.relative_to(repo_root.resolve())
    except ValueError:
        _add(problems, f"{label} evidence path escapes repo-root")
        return
    if not evidence_path.is_file():
        _add(problems, f"{label} evidence path does not exist: {parsed['path']}")
        return
    if hashlib.sha256(evidence_path.read_bytes()).hexdigest() != parsed["sha256"]:
        _add(problems, f"{label} evidence sha256 does not match current bytes")
        return
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _add(problems, f"{label} evidence must be valid UTF-8 JSON: {exc}")
        return
    if not isinstance(evidence, dict):
        _add(problems, f"{label} evidence must be a JSON object")
        return
    machine = evidence.get("schema") == "ui-evidence/3"
    if require_machine and not machine:
        _add(problems, f"{label} requires ui-evidence/3 machine observation, separate from human approval")
    evidence_keys = {"schema", "check", "result", "reviewedArtifact", "receipt"}
    if not machine:
        evidence_keys.update({"attestation", "owner"})
    if set(evidence) != evidence_keys:
        _add(problems, f"{label} evidence has an invalid ui-evidence/2 key set")
        return
    expected_check = expected_check or EVIDENCE_CHECKS.get(label)
    if evidence.get("schema") != ("ui-evidence/3" if machine else EVIDENCE_SCHEMA) or evidence.get("result") != "PASS":
        _add(problems, f"{label} evidence must record schema ui-evidence/2 and result PASS")
    if expected_check is None or evidence.get("check") != expected_check:
        _add(problems, f"{label} evidence check must be {expected_check}")
    receipt_contract = _receipt_contract(expected_check)
    artifact = evidence.get("reviewedArtifact")
    receipt = evidence.get("receipt")
    if not isinstance(artifact, dict) or set(artifact) != {"path", "sha256"}:
        _add(problems, f"{label} evidence reviewedArtifact must contain path and sha256")
    else:
        artifact_path = artifact.get("path")
        artifact_sha = artifact.get("sha256")
        if not isinstance(artifact_path, str) or SOURCE_RE.fullmatch(
            f"{artifact_path} @ sha256:{artifact_sha}"
        ) is None:
            _add(problems, f"{label} evidence reviewedArtifact path and sha256 are invalid")
        else:
            reviewed = (repo_root / artifact_path).resolve()
            try:
                reviewed.relative_to(repo_root.resolve())
            except ValueError:
                _add(problems, f"{label} evidence reviewedArtifact escapes repo-root")
            else:
                if not reviewed.is_file():
                    _add(problems, f"{label} evidence reviewedArtifact does not exist: {artifact_path}")
                elif hashlib.sha256(reviewed.read_bytes()).hexdigest() != artifact_sha:
                    _add(problems, f"{label} evidence reviewedArtifact sha256 does not match current bytes")
                if expected_artifact is not None and artifact_path.casefold() != expected_artifact.casefold():
                    _add(problems, f"{label} evidence reviewedArtifact must be {expected_artifact}")
    if not machine and evidence.get("attestation") != "human-attested":
        _add(problems, f"{label} evidence must be explicitly human-attested")
    if not isinstance(receipt, dict) or set(receipt) != {"tool", "method", "matrix", "results", "outputArtifact", "executedAt"}:
        _add(problems, f"{label} evidence receipt must contain tool, method, matrix, results, outputArtifact, and executedAt")
    else:
        if receipt.get("tool") not in RECEIPT_TOOLS:
            _add(problems, f"{label} evidence receipt.tool is not an approved tool")
        if receipt.get("method") not in RECEIPT_METHODS:
            _add(problems, f"{label} evidence receipt.method is not an approved method")
        if receipt_contract is not None and (
            receipt.get("tool") not in receipt_contract[0]
            or receipt.get("method") != receipt_contract[1]
        ):
            _add(problems, f"{label} evidence receipt tool/method does not match check {expected_check}")
        matrix = receipt.get("matrix")
        if (
            not isinstance(matrix, dict)
            or set(matrix) != {"cases"}
            or not isinstance(matrix.get("cases"), list)
            or not matrix["cases"]
            or any(
                not isinstance(item, dict)
                or set(item) != {"surface", "state", "target"}
                or not all(isinstance(item.get(key), str) and item.get(key).strip() for key in ("surface", "state", "target"))
                for item in matrix.get("cases", [])
            )
        ):
            _add(problems, f"{label} evidence receipt.matrix must contain exact surface/state/target cases")
        elif expected_matrix is not None and matrix != expected_matrix:
            _add(problems, f"{label} evidence receipt.matrix must exactly match Approved target scope")
        results = receipt.get("results")
        if (
            not isinstance(results, list)
            or not results
            or any(
                not isinstance(item, dict)
                or set(item) != {"surface", "state", "target", "result"}
                or not all(isinstance(item.get(key), str) and item.get(key).strip() for key in ("surface", "state", "target"))
                or item.get("result") != "PASS"
                for item in results
            )
        ):
            _add(problems, f"{label} evidence receipt.results must contain one PASS surface/state/target row per matrix case")
        elif expected_matrix is not None:
            expected_rows = [dict(case, result="PASS") for case in expected_matrix["cases"]]
            if results != expected_rows:
                _add(problems, f"{label} evidence receipt.results must contain exactly one PASS row per matrix cross-product")
        output = receipt.get("outputArtifact")
        if not isinstance(output, dict) or set(output) != {"path", "sha256"}:
            _add(problems, f"{label} evidence receipt.outputArtifact must contain path and sha256")
        else:
            output_path = output.get("path")
            output_sha = output.get("sha256")
            if not isinstance(output_path, str) or SOURCE_RE.fullmatch(f"{output_path} @ sha256:{output_sha}") is None:
                _add(problems, f"{label} evidence receipt.outputArtifact path and sha256 are invalid")
            else:
                output_file = (repo_root / output_path).resolve()
                try:
                    output_file.relative_to(repo_root.resolve())
                except ValueError:
                    _add(problems, f"{label} evidence receipt.outputArtifact escapes repo-root")
                else:
                    if not output_file.is_file() or hashlib.sha256(output_file.read_bytes()).hexdigest() != output_sha:
                        _add(problems, f"{label} evidence receipt.outputArtifact is missing or stale")
                    else:
                        try:
                            output_json = json.loads(output_file.read_text(encoding="utf-8"))
                        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                            _add(problems, f"{label} evidence receipt.outputArtifact must be JSON: {exc}")
                        else:
                            offline = receipt.get("method") == HIFI_SURFACE_RECEIPT_METHOD
                            bundle = None
                            review_contract = None
                            if offline and expected_artifact:
                                candidate = repo_root / expected_artifact
                                try:
                                    candidate.resolve().relative_to(repo_root.resolve())
                                    matches = list(HIFI_MANIFEST_RE.finditer(candidate.read_text(encoding="utf-8")))
                                    parsed_manifest = json.loads(matches[0].group("data")) if len(matches) == 1 else None
                                    if isinstance(parsed_manifest, dict) and parsed_manifest.get("schema") == "ui-hifi/2":
                                        bundle = parsed_manifest
                                        documents = _hifi_bundle_documents(candidate, candidate.read_text(encoding="utf-8"), bundle)
                                        # Only a current shell contributes a reviewer receipt. Legacy
                                        # schema-2 shells keep their inspection-only output shape;
                                        # _validate_hifi_surface(require_connected=True) is the fresh gate.
                                        if has_current_reviewer_shell(documents):
                                            review_errors, review_contract = reviewer_contract(documents, bundle)
                                            problems.extend(review_errors)
                                except (OSError, UnicodeError, ValueError):
                                    _add(problems, "HiFi evidence bundle manifest cannot be read")
                            expected_output_keys = {
                                "schema",
                                "check",
                                "subject",
                                "matrix",
                                "results",
                                "sandbox",
                                "console",
                                "network",
                                "navigation",
                                "popups",
                                "forms",
                                "popupAttempts",
                                "formAttempts",
                            } if offline else {
                                "schema",
                                "check",
                                "subject",
                                "matrix",
                                "results",
                            }
                            if bundle is not None:
                                expected_output_keys.add("interactions")
                            if review_contract is not None:
                                expected_output_keys.add("reviewer")
                            if expected_motion is not None:
                                expected_output_keys.add("motion")
                            if machine:
                                expected_output_keys.add("execution")
                                if any(term in str(expected_check) for term in ("grading", "critique", "audit")):
                                    expected_output_keys.add("assessment")
                            if not isinstance(output_json, dict) or set(output_json) != expected_output_keys:
                                _add(
                                    problems,
                                    f"{label} output artifact must use the "
                                    + ("sandboxed offline ui-output/1 transcript schema" if offline else "ui-output/1 schema"),
                                )
                            elif (
                                output_json.get("schema") != ("ui-output/3" if machine else ("ui-output/2" if bundle is not None else "ui-output/1"))
                                or output_json.get("check") != evidence.get("check")
                                or output_json.get("subject") != evidence.get("reviewedArtifact")
                                or output_json.get("matrix") != receipt.get("matrix")
                                or output_json.get("results") != receipt.get("results")
                            ):
                                _add(problems, f"{label} output artifact does not exactly match its receipt")
                            elif offline:
                                findings = _bundle_transcript_findings(output_json, bundle) if bundle is not None else _offline_transcript_findings(output_json)
                                for finding in findings:
                                    _add(problems, finding)
                                if review_contract is not None:
                                    for finding in reviewer_evidence_findings(output_json.get("reviewer"), review_contract):
                                        _add(problems, finding)
                            if machine and isinstance(output_json, dict):
                                problems.extend(f"{label}: {item}" for item in execution_findings(repo_root, output_json, receipt, artifact))
                                problems.extend(f"{label}: {item}" for item in assessment_findings(repo_root, output_json))
                                captured = output_json.get("execution", {}).get("artifacts", []) if isinstance(output_json.get("execution"), dict) else []
                                if any(binding not in captured for binding in (required_inputs or [])):
                                    _add(problems, f"{label} execution must bind the current product and structural inputs")
                                if recorded_scores is not None:
                                    problems.extend(f"{label}: {item}" for item in score_findings(output_json, recorded_scores))
                            if expected_motion is not None and isinstance(output_json, dict):
                                motion = output_json.get("motion")
                                for finding in motion_findings(motion, expected_motion):
                                    _add(problems, f"{label}: {finding}")
                                asset = motion.get("asset") if isinstance(motion, dict) else None
                                if isinstance(asset, dict):
                                    authorization = asset.get("authorization")
                                    if isinstance(authorization, dict) and not _human_owner(authorization.get("owner") if isinstance(authorization.get("owner"), str) else None):
                                        _add(problems, f"{label} asset authorization owner must be human")
                                    source = f"{asset.get('path', '')} @ sha256:{asset.get('sha256', '')}"
                                    if _source_syntax(source, label, problems):
                                        _resolve_source(source, repo_root=repo_root, label=label, problems=problems)
        timestamp = receipt.get("executedAt")
        try:
            parsed_time = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if parsed_time.tzinfo is None:
                raise ValueError("timestamp must include timezone")
            if parsed_time > datetime.now(timezone.utc):
                _add(problems, f"{label} evidence executedAt cannot be in the future")
        except (TypeError, ValueError):
            _add(problems, f"{label} evidence executedAt must be a past ISO-8601 timestamp")
    owner = evidence.get("owner")
    if not machine and (not isinstance(owner, str) or not _human_owner(owner)):
        _add(problems, f"{label} evidence owner must be human")


def _evidence_check(label: str, capture_mode: str | None) -> str | None:
    suffix = {
        "hosted-browser": "browser",
        "browser-extension": "extension",
        "native": "native",
        "desktop": "desktop",
        "mixed": "mixed",
    }.get(capture_mode or "")
    if suffix is None:
        return EVIDENCE_CHECKS.get(label)
    if label in {"Responsive surface check", "Wireframe UI grading"}:
        return f"wireframe-{suffix}" if label.startswith("Responsive") else f"wireframe-{suffix}-grading"
    if label == "motion":
        return "motion-preview"
    if label in {"HiFi surface check", "HiFi UI grading", "Impeccable critique", "Impeccable audit", "Impeccable critique verdict", "Impeccable audit verdict"}:
        if label == "HiFi surface check":
            return f"hifi-{suffix}"
        if label == "HiFi UI grading":
            return f"hifi-{suffix}-grading"
        return f"hifi-{suffix}-impeccable-{'critique' if 'critique' in label.casefold() else 'audit'}"


def _bundle_transcript_findings(output: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    """Check attested click/key outcomes against the hash-bound interaction map."""
    baseline = dict(output, navigation=[], sandbox={"network": "disabled", "topNavigation": "blocked", "popups": "blocked", "forms": "blocked"})
    findings = _offline_transcript_findings(baseline)
    expected_sandbox = dict(baseline["sandbox"], topNavigation="allowlisted-local-pages")
    if output.get("sandbox") != expected_sandbox:
        findings.append("HiFi bundle requires the allowlisted-local-pages offline sandbox")
    try:
        by_id = {row["id"]: row for row in manifest["surfaces"]}
        expected = []
        navigation = []
        for action in manifest["interactions"]:
            source = by_id[action["source"]["surface"]]
            destination = by_id[action["destination"]["surface"]]
            for target in source["responsive"]["targets"]:
                for trigger in ("click", "keyboard"):
                    expected.append({
                        "id": action["id"], "target": str(target), "trigger": trigger,
                        "source": action["source"], "destination": action["destination"],
                        "control": action["control"], "visible": True, "focusCorrect": True, "result": "PASS",
                    })
                    if action["kind"] == "navigate":
                        navigation.append({"id": action["id"], "target": str(target), "trigger": trigger, "from": source["page"], "to": destination["page"]})
        def rows_equal(actual: Any, required: list[dict[str, Any]]) -> bool:
            return isinstance(actual, list) and sorted(json.dumps(row, sort_keys=True) for row in actual) == sorted(json.dumps(row, sort_keys=True) for row in required)
        if not rows_equal(output.get("interactions"), expected):
            findings.append("HiFi interaction evidence must exactly cover click and keyboard destination, visibility, and focus results at every target")
        if not rows_equal(output.get("navigation"), navigation):
            findings.append("HiFi navigation transcript must exactly match declared local-page transitions; extra or missing attempts fail")
    except (KeyError, TypeError, ValueError):
        findings.append("HiFi bundle interaction manifest is invalid")
    return findings


def _offline_transcript_findings(output: dict[str, Any]) -> list[str]:
    """Validate the retained sandbox transcript without claiming JS analysis."""

    findings: list[str] = []
    expected_sandbox = {
        "network": "disabled",
        "topNavigation": "blocked",
        "popups": "blocked",
        "forms": "blocked",
    }
    if output.get("sandbox") != expected_sandbox:
        findings.append(
            "HiFi offline output artifact sandbox must record disabled network, "
            "blocked top navigation/popups/forms"
        )
    console = output.get("console")
    network = output.get("network")
    navigation = output.get("navigation")
    popups = output.get("popups")
    forms = output.get("forms")
    popup_attempts = output.get("popupAttempts")
    form_attempts = output.get("formAttempts")
    if (
        not isinstance(console, list)
        or not isinstance(network, list)
        or not isinstance(navigation, list)
        or not isinstance(popups, list)
        or not isinstance(forms, list)
        or not isinstance(popup_attempts, int)
        or isinstance(popup_attempts, bool)
        or not isinstance(form_attempts, int)
        or isinstance(form_attempts, bool)
    ):
        findings.append(
            "HiFi offline output artifact must contain console, network, navigation, "
            "popups, and forms transcript arrays plus integer attempt counts"
        )
        return findings
    if popup_attempts != len(popups) or form_attempts != len(forms):
        findings.append(
            "HiFi offline transcript popupAttempts/formAttempts must equal the "
            "corresponding transcript lengths"
        )
    for event in console:
        if isinstance(event, dict):
            level = str(event.get("level", "")).casefold()
            message = str(event.get("message", ""))
            if level in {"error", "exception", "uncaught"} or re.search(r"\b(?:error|exception|uncaught)\b", message, re.I):
                findings.append("HiFi offline transcript contains a console error")
        elif re.search(r"\b(?:error|exception|uncaught)\b", str(event), re.I):
            findings.append("HiFi offline transcript contains a console error")
    if network:
        findings.append("HiFi offline transcript recorded a network request")
    if navigation:
        findings.append("HiFi offline transcript recorded a navigation or popup attempt")
    if popups:
        findings.append("HiFi offline transcript recorded a popup attempt")
    if forms:
        findings.append("HiFi offline transcript recorded a form attempt")
    return sorted(set(findings))


def _resolve_target_source(
    value: str | None,
    *,
    repo_root: Path,
    label: str,
    problems: list[str],
) -> None:
    match = TARGET_SOURCE_RE.fullmatch((value or "").strip()) if value else None
    if match is None:
        return
    _resolve_source(
        f"{match.group('path')} @ sha256:{match.group('sha256')}",
        repo_root=repo_root,
        label=label,
        problems=problems,
    )


def _resolve_pair(
    value: str | None,
    *,
    repo_root: Path,
    label: str,
    problems: list[str],
) -> None:
    match = PAIR_RE.fullmatch((value or "").strip()) if value else None
    if match is None:
        return
    for relative, digest, part_label in (
        (match.group("markdown"), match.group("markdown_sha256"), "Markdown"),
        (match.group("registry"), match.group("registry_sha256"), "JSON"),
    ):
        _resolve_source(
            f"{relative} @ sha256:{digest}",
            repo_root=repo_root,
            label=f"{label} {part_label}",
            problems=problems,
        )


def _wireframe_media_intents(
    wireframes_path: Path, problems: list[str]
) -> list[dict[str, Any]]:
    try:
        html = wireframes_path.read_text(encoding="utf-8")
        match = WIREFRAME_DATA_RE.search(html)
        if match is None:
            raise ValueError("wireframe-data script is missing")
        value = json.loads(match.group("data"))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        _add(problems, f"cannot read wireframe media intents: {exc}")
        return []
    if not isinstance(value, dict) or value.get("schema") not in {"wireframes/4", "wireframes/5"}:
        return []
    found: list[dict[str, Any]] = []

    def visit(node: Any, owner_path: str, screen_id: str | None = None, region_id: str | None = None) -> None:
        if isinstance(node, dict):
            current_screen = screen_id
            current_region = region_id
            direct_screen_node = bool(re.fullmatch(r"wireframe-data\.screens\[\d+\]", owner_path))
            direct_region_node = bool(re.search(r"\.regions\[\d+\]$", owner_path))
            if direct_screen_node:
                candidate = node.get("id")
                current_screen = candidate if isinstance(candidate, str) else current_screen
                current_region = None
            if direct_region_node:
                candidate = node.get("id")
                current_region = candidate if isinstance(candidate, str) else current_region
            intent = node.get("mediaIntent")
            if isinstance(intent, dict):
                intent_id = intent.get("id")
                direct_screen = direct_screen_node
                direct_region = direct_region_node
                if not isinstance(intent_id, str) or not MM_ID_RE.fullmatch(intent_id):
                    _add(problems, f"{owner_path}.mediaIntent.id must be a valid MM-* ID")
                elif not direct_screen and not direct_region:
                    _add(
                        problems,
                        f"{owner_path}.mediaIntent must be attached directly to an explicit screen or region",
                    )
                elif not isinstance(current_screen, str) or not current_screen.strip():
                    _add(
                        problems,
                        f"{owner_path}.mediaIntent must be attached to an explicit screen or region",
                    )
                else:
                    if direct_region and not isinstance(current_region, str):
                        _add(
                            problems,
                            f"{owner_path}.mediaIntent must be attached to an explicit screen or region",
                        )
                    scope = f"{current_screen} / {current_region or 'screen'}"
                    if any(item["id"] == intent_id for item in found):
                        _add(problems, f"duplicate wireframe mediaIntent ID {intent_id}")
                    found.append(
                        {
                            "id": intent_id,
                            "scope": scope,
                            "screen": current_screen,
                            "region": current_region,
                            **intent,
                        }
                    )
            for key, child in node.items():
                if key != "mediaIntent":
                    child_path = f"{owner_path}.{key}"
                    visit(child, child_path, current_screen, current_region)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, f"{owner_path}[{index}]", screen_id, region_id)

    visit(value.get("screens"), "wireframe-data.screens")
    return found


def _join_motion_intents(
    intents: dict[str, dict[str, str]],
    wireframes_path: Path,
    *,
    problems: list[str],
) -> None:
    projected = _wireframe_media_intents(wireframes_path, problems)
    projected_by_id: dict[str, list[dict[str, Any]]] = {}
    for intent in projected:
        intent_id = str(intent.get("id", ""))
        projected_by_id.setdefault(intent_id, []).append(intent)

    for intent_id, intent in intents.items():
        matches = projected_by_id.get(intent_id, [])
        if not matches:
            _add(problems, f"{intent_id} has no wireframe mediaIntent")
            continue
        if len(matches) != 1:
            _add(problems, f"{intent_id} has duplicate wireframe mediaIntents")
        for projected_intent in matches:
            if projected_intent.get("scope", "").casefold() != intent.get("scope", "").casefold():
                _add(problems, f"{intent_id} screen/region scope differs from the wireframe")
            if projected_intent.get("treatment") != intent.get("treatment"):
                _add(problems, f"{intent_id} treatment differs from the wireframe")
            if projected_intent.get("purpose") != intent.get("purpose"):
                _add(problems, f"{intent_id} purpose differs from the wireframe")
            if projected_intent.get("trigger") != intent.get("trigger"):
                _add(problems, f"{intent_id} trigger differs from the wireframe")
            if projected_intent.get("draftPrompt") != intent.get("draftPrompt"):
                _add(problems, f"{intent_id} draft prompt differs from the wireframe")
            if projected_intent.get("source") != intent.get("source"):
                _add(problems, f"{intent_id} source differs from the wireframe")
            if projected_intent.get("reducedMotionFallback") != intent.get("fallback", intent.get("reducedMotionFallback")):
                _add(problems, f"{intent_id} reduced-motion fallback differs from the wireframe")
            if projected_intent.get("generationRoute") != intent.get("generationRoute"):
                _add(
                    problems,
                    f"{intent_id} generation route authority differs from the wireframe",
                )
            if projected_intent.get("generationStatus") != intent.get("generationStatus"):
                _add(problems, f"{intent_id} generation status differs from the wireframe")
            if "status" in projected_intent and projected_intent.get("status") != intent.get("status"):
                _add(problems, f"{intent_id} status differs from the wireframe")

    for intent_id in sorted(set(projected_by_id) - set(intents)):
        _add(
            problems,
            f"wireframe mediaIntent {intent_id} has no Motion And Media Intent row",
        )


def _motion_effect_evidence(
    style: str,
    motion_intents: dict[str, dict[str, str]],
    problems: list[str],
) -> dict[str, dict[str, str]]:
    """Validate and return recorded evidence for every required effect."""

    required_ids = {
        intent_id
        for intent_id, intent in motion_intents.items()
        if "motion" in intent.get("treatment", "").casefold()
    }
    if not required_ids and "### Required motion evidence" not in style:
        return {}
    for intent_id in required_ids:
        if motion_intents[intent_id].get("status", "").casefold() != "approved":
            _add(problems, f"{intent_id} requires an approved motion intent before Visual Approval")
    rows = _design_table(style, "### Required motion evidence", [
        "Intent ID", "UI scope / region", "Trigger observed", "End state observed",
        "Normal-motion evidence", "Reduced-motion evidence", "Verdict",
    ], problems)
    recorded: dict[str, dict[str, str]] = {}
    seen: set[str] = set()
    for intent_id, scope, trigger, end_state, normal, reduced, verdict in rows:
        if intent_id in seen:
            _add(problems, f"Required motion evidence duplicates {intent_id}")
        seen.add(intent_id)
        if intent_id not in required_ids:
            _add(problems, f"Required motion evidence names non-required intent {intent_id}")
            continue
        if scope != motion_intents[intent_id].get("scope", ""):
            _add(problems, f"{intent_id} motion evidence scope differs from Motion And Media Intent")
        if not _filled(trigger) or not _filled(end_state):
            _add(problems, f"{intent_id} motion trigger and end state must be observed")
        if trigger != motion_intents[intent_id].get("trigger"):
            _add(problems, f"{intent_id} observed trigger must match the approved motion intent")
        normal_ok = _pass_evidence(normal, f"{intent_id} normal-motion evidence", problems)
        reduced_ok = _pass_evidence(reduced, f"{intent_id} reduced-motion evidence", problems)
        if normal_ok is not None:
            normal_ok.update(trigger=trigger, endState=end_state)
            recorded[intent_id + ":normal"] = normal_ok
        if reduced_ok is not None:
            reduced_ok.update(trigger=trigger, endState=motion_intents[intent_id].get("fallback", ""))
            recorded[intent_id + ":reduced"] = reduced_ok
        if verdict.casefold() != "pass":
            _add(problems, f"{intent_id} motion evidence verdict must be PASS")
    missing = sorted(required_ids - seen)
    if missing:
        _add(problems, "Required motion evidence is missing for: " + ", ".join(missing))
    extra = sorted(seen - required_ids)
    if extra:
        _add(problems, "Required motion evidence names non-required intents: " + ", ".join(extra))
    return recorded


def _resolve_motion_effect_evidence(
    recorded: dict[str, dict[str, str]],
    motion_intents: dict[str, dict[str, str]],
    target_scope: dict[str, Any] | None,
    recorded_hifi: str | None,
    *,
    repo_root: Path,
    problems: list[str],
    require_machine: bool = False,
    required_inputs: list[dict[str, str]] | None = None,
) -> None:
    for evidence_key, evidence in recorded.items():
        intent_id, motion_case = evidence_key.rsplit(":", 1)
        intent = motion_intents.get(intent_id, {})
        surface_id = intent.get("scope", "").split(" / ", 1)[0]
        surface = next(
            (
                item
                for item in (target_scope or {}).get("surfaces", [])
                if isinstance(item, dict) and item.get("id") == surface_id
            ),
            None,
        )
        if surface is None:
            _add(problems, f"{intent_id} motion surface is outside the Approved target")
            continue
        responsive = (
            surface.get("responsive", (target_scope or {}).get("responsive", {}))
            if surface
            else (target_scope or {}).get("responsive", {})
        )
        targets = responsive.get("targets", []) if isinstance(responsive, dict) else []
        cases = [
            {"surface": surface_id, "state": "normal" if motion_case == "normal" else "reduced-motion", "target": str(target)}
            for target in targets
        ]
        capture_mode = (
            surface.get("captureMode", (target_scope or {}).get("captureMode"))
            if surface
            else (target_scope or {}).get("captureMode")
        )
        _resolve_evidence(
            f"PASS — evidence={evidence['path']} @ sha256:{evidence['sha256']}",
            repo_root=repo_root,
            label=f"{intent_id} {motion_case} motion evidence",
            problems=problems,
            expected_artifact=(
                SOURCE_RE.fullmatch((recorded_hifi or "").strip()).group("path")
                if SOURCE_RE.fullmatch((recorded_hifi or "").strip())
                else None
            ),
            expected_check=_evidence_check("motion", capture_mode),
            expected_matrix={"cases": cases},
            require_machine=require_machine,
            required_inputs=required_inputs,
            expected_motion={
                "intent": intent_id, "scope": intent.get("scope"), "mode": motion_case,
                "trigger": intent.get("trigger"), "endState": evidence.get("endState"),
                "states": surface.get("states", []), "targets": [str(t) for t in targets],
                "provider": intent.get("generationRoute") if intent.get("generationRoute", "").casefold() not in {
                    "css-waapi", "gsap", "native-framework", "none", "existing asset"
                } else None,
                "assetAction": "reuse" if intent.get("generationRoute", "").casefold() == "existing asset" else None,
                "assetRequired": intent.get("treatment", "").casefold() == "image + motion" or intent.get("generationRoute", "").casefold() not in {
                    "css-waapi", "gsap", "native-framework", "none"
                },
            },
        )


def validate_text(
    text: str,
    *,
    require_filled: bool = False,
    require_wireframe_approved: bool = False,
    require_structure_validated: bool = False,
    require_visual_approved: bool = False,
    allow_pending_design_system_pair: bool = False,
) -> list[str]:
    text = active_text(text)
    problems: list[str] = []
    positions: list[int] = []
    sections: dict[str, str] = {}
    modern = is_structure_review(text)
    structural_gate = require_structure_validated or require_wireframe_approved or require_visual_approved
    if modern and require_wireframe_approved:
        _add(problems, "--require-wireframe-approved is a legacy gate; use --require-structure-validated")
    if require_structure_validated and not modern:
        _add(problems, "--require-structure-validated requires Wireframe Validation")
    headings = tuple(wireframe_heading(text) if item == "## Wireframe Approval" else item for item in REQUIRED_HEADINGS)
    for heading in headings:
        matches = list(re.finditer(rf"^{re.escape(heading)}\s*$", text, re.MULTILINE))
        if len(matches) != 1:
            _add(problems, f"requires exactly one {heading!r} heading")
            continue
        positions.append(matches[0].start())
        section = _section(text, heading)
        if section is not None:
            sections[heading] = section
    if len(positions) == len(REQUIRED_HEADINGS) and positions != sorted(positions):
        _add(problems, "required headings are out of order")

    source = sections.get("## Source Product Definition")
    if source is not None:
        values = _require_fields(
            source,
            (
                "PRD source",
                "Architecture source",
                "Stack source",
                "Product Definition Approval",
                "Stack Decision Checkpoint",
            ),
            label="Source Product Definition",
            require_filled=require_filled or require_structure_validated or require_wireframe_approved or require_visual_approved,
            problems=problems,
        )
        if require_filled or require_structure_validated or require_wireframe_approved or require_visual_approved:
            for name in ("PRD source", "Architecture source", "Stack source"):
                _source_syntax(values.get(name), name, problems)
        for name in ("Product Definition Approval", "Stack Decision Checkpoint"):
            if (require_filled or require_structure_validated or require_wireframe_approved or require_visual_approved) and values.get(name, "").casefold() != "approved":
                _add(problems, f"{name} must be exactly approved")

    intake = sections.get("## UI Design Intake")
    if intake is not None:
        values = _require_fields(
            intake,
            ("Decision owner", "Decided on", "Visual Preference Brief", "Direction mode"),
            label="UI Design Intake",
            require_filled=require_filled,
            problems=problems,
        )
        if require_filled and not _human_owner(values.get("Decision owner")):
            _add(problems, "UI Design Intake Decision owner must be human")
        if require_filled and not _date(values.get("Decided on")):
            _add(problems, "UI Design Intake Decided on must be a real YYYY-MM-DD date")
        direction_mode = (values.get("Direction mode") or "").strip().casefold()
        if (require_filled or require_structure_validated or require_wireframe_approved or require_visual_approved) and direction_mode not in VALID_DIRECTION_MODES:
            _add(
                problems,
                "UI Design Intake Direction mode must be one of "
                + ", ".join(sorted(VALID_DIRECTION_MODES)),
            )

    motion_intents: dict[str, dict[str, str]] = {}
    motion = sections.get("## Motion And Media Intent")
    if motion is not None:
        motion_values = _require_fields(
            motion,
            ("Motion direction",),
            label="Motion And Media Intent",
            require_filled=require_filled,
            problems=problems,
        )
        raw_direction = motion_values.get("Motion direction", "")
        direction_parts = [part.strip() for part in raw_direction.split("—", 1)]
        direction = direction_parts[0].casefold()
        if (require_filled or require_structure_validated or require_wireframe_approved or require_visual_approved) and direction not in VALID_MOTION_DIRECTIONS:
            _add(
                problems,
                "Motion And Media Intent Motion direction must be one of "
                + ", ".join(sorted(VALID_MOTION_DIRECTIONS)),
            )
        if require_filled or require_structure_validated or require_wireframe_approved or require_visual_approved:
            if len(direction_parts) != 2 or not _human_owner(direction_parts[1]):
                _add(problems, "Motion And Media Intent Motion direction must include a human owner")
        motion_intents = _validate_motion_table(
            motion, require_filled=require_filled, problems=problems
        )

    wireframe = sections.get(wireframe_heading(text))
    wireframe_source_ok = False
    wireframe_path: Path | None = None
    if wireframe is not None:
        values = _require_fields(
            wireframe,
            (
                "Wireframe", "Frozen PRD basis", "Copy locale",
                "Responsive surface check", "UI grading", "Wireframe score",
                "W5 score", "Wireframe lowest dimension", "Wireframe blocks",
                "Structure validation",
            ) if modern else (
                "Wireframe", "Frozen PRD basis", "Copy Freeze", "Copy owner",
                "Copy locale", "Copy approved on", "Responsive surface check",
                "UI grading", "Wireframe score", "W5 score",
                "Wireframe lowest dimension", "Wireframe blocks",
                "Decision", "Decision owner", "Decided on",
            ),
            label="Wireframe Approval",
            require_filled=require_filled or require_structure_validated or require_wireframe_approved or require_visual_approved,
            problems=problems,
        )
        wireframe_value = values.get("Wireframe")
        wireframe_source_ok = _source_syntax(wireframe_value, "Wireframe", problems) if (require_filled or require_structure_validated or require_wireframe_approved or require_visual_approved) else False
        if wireframe_source_ok and wireframe_value:
            wireframe_path = Path(wireframe_value.split(" @ ", 1)[0])
        if require_filled or require_structure_validated or require_wireframe_approved or require_visual_approved:
            _source_syntax(values.get("Frozen PRD basis"), "Frozen PRD basis", problems)
            prd_identity = SOURCE_RE.fullmatch(
                (_field(source, "PRD source") or "").strip()
            )
            frozen_identity = SOURCE_RE.fullmatch(
                (values.get("Frozen PRD basis") or "").strip()
            )
            if prd_identity is not None and frozen_identity is not None and (
                prd_identity.group("path") != frozen_identity.group("path")
                or prd_identity.group("sha256") != frozen_identity.group("sha256")
            ):
                _add(problems, "Frozen PRD basis must exactly match Source Product Definition PRD source")
        if structural_gate:
            if modern:
                if values.get("Structure validation", "").casefold() != "validated":
                    _add(problems, "Wireframe Validation Structure validation must be validated")
                if not check_wireframe_html.LOCALE_RE.fullmatch(values.get("Copy locale", "").strip()):
                    _add(problems, "Wireframe Validation Copy locale must be a BCP 47 locale")
                for name in ("Copy Freeze", "Copy owner", "Copy approved on", "Decision owner", "Decided on"):
                    if _field(wireframe, name) is not None:
                        _add(problems, f"Wireframe Validation must not contain legacy approval field {name}")
            else:
                if values.get("Decision", "").casefold() not in VALID_WIREFRAME_DECISIONS:
                    _add(
                        problems,
                        "Wireframe Approval Decision must be one of "
                        + ", ".join(sorted(VALID_WIREFRAME_DECISIONS)),
                    )
                if values.get("Decision", "").casefold() != "approved":
                    _add(problems, "Wireframe Approval Decision must be approved")
                if values.get("Copy Freeze", "").casefold() != "approved":
                    _add(problems, "Wireframe Approval Copy Freeze must be approved")
                if not _human_owner(values.get("Copy owner")):
                    _add(problems, "Wireframe Approval Copy owner must be human")
                if not check_wireframe_html.LOCALE_RE.fullmatch(
                    values.get("Copy locale", "").strip()
                ):
                    _add(problems, "Wireframe Approval Copy locale must be a BCP 47 locale")
                if not _date(values.get("Copy approved on")):
                    _add(
                        problems,
                        "Wireframe Approval Copy approved on must be a real YYYY-MM-DD date",
                    )
                if not _human_owner(values.get("Decision owner")):
                    _add(problems, "Wireframe Approval Decision owner must be human")
                if not _date(values.get("Decided on")):
                    _add(
                        problems,
                        "Wireframe Approval Decided on must be a real YYYY-MM-DD date",
                    )
            _pass_evidence(
                values.get("Responsive surface check"),
                "Responsive surface check",
                problems,
            )
            _pass_evidence(values.get("UI grading"), "Wireframe UI grading", problems)
            overall = _score(values.get("Wireframe score"))
            lowest = _score(values.get("Wireframe lowest dimension"))
            if (_score(values.get("W5 score")) or 0) < 80:
                _add(problems, "W5 score must be an integer from 80 to 100")
            if overall is None or overall < 80:
                _add(problems, "Wireframe score must be an integer from 80 to 100")
            if lowest is None or lowest < 60:
                _add(
                    problems,
                    "Wireframe lowest dimension must be an integer from 60 to 100",
                )
            if values.get("Wireframe blocks", "").casefold().strip() != "none":
                _add(problems, "Wireframe blocks must be none")

    if modern and (require_filled or structural_gate):
        problems.extend(author_usage_findings(text, require_hifi=require_visual_approved))

    if require_visual_approved:
        style = sections.get("## Style Integration", "")
        style_values = _require_fields(
            style,
            (
                "Design author",
                "Selected direction",
                "Direction decision",
                "Direction decision owner",
                "Direction decided on",
                "Candidate theme",
                "Review medium",
                "Connected HiFi reference",
            ),
            label="Style Integration",
            require_filled=True,
            problems=problems,
        )
        if style_values.get("Design author", "").casefold() != "frontend-design":
            _add(problems, "Style Integration Design author must be frontend-design")
        if style_values.get("Review medium") != "HTML projection only":
            _add(problems, "Style Integration Review medium must be HTML projection only; it is not native verification")
        if style_values.get("Direction decision", "").casefold() not in VALID_DIRECTION_DECISIONS:
            _add(problems, "Style Integration Direction decision is not approved")
        if not _human_owner(style_values.get("Direction decision owner")):
            _add(problems, "Style Integration Direction decision owner must be human")
        if not _date(style_values.get("Direction decided on")):
            _add(
                problems,
                "Style Integration Direction decided on must be a real YYYY-MM-DD date",
            )
        _source_syntax(
            style_values.get("Connected HiFi reference"),
            "Connected HiFi reference",
            problems,
        )

        review = sections.get("## HiFi Review", "")
        review_values = _require_fields(
            review,
            (
                "Impeccable critique",
                "Impeccable audit",
                "UI grading",
                "HiFi surface check",
                "HiFi score",
                "H2 score",
                "H4 score",
                "H5 score",
                "H7 score",
                "H8 score",
                "H9 score",
                "HiFi lowest dimension",
                "HiFi blocks or disputes",
            ),
            label="HiFi Review",
            require_filled=True,
            problems=problems,
        )
        _pass_evidence(
            review_values.get("Impeccable critique"),
            "Impeccable critique verdict",
            problems,
        )
        _pass_evidence(
            review_values.get("Impeccable audit"), "Impeccable audit verdict", problems
        )
        _pass_evidence(review_values.get("UI grading"), "HiFi UI grading", problems)
        _pass_evidence(
            review_values.get("HiFi surface check"), "HiFi surface check", problems
        )
        for name, minimum in (
            ("HiFi score", 90),
            ("H2 score", 90),
            ("H4 score", 90),
            ("H5 score", 80),
            ("H7 score", 80),
            ("H8 score", 90),
            ("H9 score", 80),
            ("HiFi lowest dimension", 60),
        ):
            score = _score(review_values.get(name))
            if score is None or score < minimum:
                _add(problems, f"{name} must be an integer from {minimum} to 100")
        if (review_values.get("HiFi blocks or disputes") or "").casefold().strip() != "none":
            _add(problems, "HiFi blocks or disputes must be none")

        visual = sections.get("## Visual Approval", "")
        visual_values = _require_fields(
            visual,
            ("Decision", "Decision owner", "Decided on", "Approved target"),
            label="Visual Approval",
            require_filled=True,
            problems=problems,
        )
        if visual_values.get("Decision", "").casefold() != "approved":
            _add(problems, "Visual Approval Decision must be approved")
        if not _human_owner(visual_values.get("Decision owner")):
            _add(problems, "Visual Approval Decision owner must be human")
        if not _date(visual_values.get("Decided on")):
            _add(problems, "Visual Approval Decided on must be a real YYYY-MM-DD date")
        _target_source_syntax(
            visual_values.get("Approved target"), "Approved target", problems
        )
        scope_errors_before = len(problems)
        scope = _target_scope(visual_values.get("Approved target"), "Approved target", problems)
        valid_scope = scope if len(problems) == scope_errors_before else None
        _direction_comparison(style, sections.get("## UI Design Intake", ""), valid_scope, problems)
        _motion_effect_evidence(style, motion_intents, problems)
        _platform_rules(style, valid_scope, problems)
        connected = SOURCE_RE.fullmatch(
            (style_values.get("Connected HiFi reference") or "").strip()
        )
        approved = TARGET_SOURCE_RE.fullmatch(
            (visual_values.get("Approved target") or "").strip()
        )
        if connected is not None and approved is not None:
            if (
                connected.group("path") != approved.group("path")
                or connected.group("sha256") != approved.group("sha256")
            ):
                _add(
                    problems,
                    "Connected HiFi reference must exactly match Visual Approval "
                    "Approved target path and sha256",
                )

        gate = sections.get("## Design System Need Gate", "")
        gate_values = _require_fields(
            gate,
            (
                "Decision",
                "Decision owner",
                "Decided on",
                "Reason",
                "Existing design-system pair disposition",
            ),
            label="Design System Need Gate",
            require_filled=True,
            problems=problems,
        )
        gate_decision = gate_values.get("Decision", "").casefold()
        if gate_decision not in {"required", "not_required"}:
            _add(problems, "Design System Need Gate must be required or not_required")
        if not _human_owner(gate_values.get("Decision owner")):
            _add(problems, "Design System Need Gate Decision owner must be human")
        if not _date(gate_values.get("Decided on")):
            _add(
                problems,
                "Design System Need Gate Decided on must be a real YYYY-MM-DD date",
            )

        compiled = _field_values(gate, "Compiled design system pair")
        replacement = _field_values(gate, "Replacement visual contract when_not_required")
        if not replacement:
            replacement = _field_values(gate, "Replacement visual contract when not_required")
        if gate_decision == "required":
            if len(compiled) != 1:
                _add(
                    problems,
                    "required Design System Need Gate is missing exactly one compiled pair field",
                )
            else:
                if (
                    allow_pending_design_system_pair
                    and compiled[0].strip().casefold()
                    == PENDING_PAIR_VALUE.casefold()
                ):
                    pass
                elif compiled[0].strip().casefold() == PENDING_PAIR_VALUE.casefold():
                    _add(
                        problems,
                        "required Design System Need Gate pending pair marker is only valid during the exact compiler preflight",
                    )
                else:
                    _pair_syntax(compiled[0], problems)
            if replacement:
                _add(
                    problems,
                    "required Design System Need Gate must not name a not_required replacement",
                )
        elif gate_decision == "not_required":
            if len(replacement) != 1:
                _add(
                    problems,
                    "not_required Design System Need Gate is missing exactly one replacement field",
                )
            if compiled:
                _add(
                    problems,
                    "not_required Design System Need Gate must not name a compiled pair",
                )
            if len(replacement) == 1:
                _replacement_parts(replacement[0], problems)

        disposition = gate_values.get("Existing design-system pair disposition", "")
        disposition_match = PAIR_DISPOSITION_RE.fullmatch(disposition.strip())
        if disposition_match is None:
            _add(
                problems,
                "Design System Need Gate Existing design-system pair disposition must use "
                "'none|retain|retire — reason; owner=<human>; decided=<YYYY-MM-DD>'",
            )
        else:
            if not _human_owner(disposition_match.group("owner")):
                _add(problems, "Design System Need Gate existing pair disposition owner must be human")
            if not _date(disposition_match.group("date")):
                _add(problems, "Design System Need Gate existing pair disposition decided date must be real")
            if not disposition_match.group("reason").strip():
                _add(problems, "Design System Need Gate existing pair disposition reason must be filled")

    if (
        (require_structure_validated or require_wireframe_approved or require_visual_approved)
        and wireframe_path is not None
        and wireframe_source_ok
        and wireframe_path.exists()
    ):
        _join_motion_intents(motion_intents, wireframe_path, problems=problems)
    return problems


def _validate_impl(
    ui_design_path: Path,
    *,
    repo_root: Path | None = None,
    prd_path: Path | None = None,
    wireframes_path: Path | None = None,
    hifi_path: Path | None = None,
    design_system_markdown_path: Path | None = None,
    design_system_registry_path: Path | None = None,
    _allow_pending_design_system_pair: bool = False,
    require_filled: bool = False,
    require_wireframe_approved: bool = False,
    require_structure_validated: bool = False,
    require_visual_approved: bool = False,
) -> list[str]:
    try:
        text = ui_design_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"ui-design: cannot read UTF-8 file {ui_design_path}: {exc}"]
    problems = validate_text(
        text,
        require_filled=require_filled,
        require_wireframe_approved=require_wireframe_approved,
        require_structure_validated=require_structure_validated,
        require_visual_approved=require_visual_approved,
        allow_pending_design_system_pair=_allow_pending_design_system_pair,
    )

    active = active_text(text)
    modern = is_structure_review(active)
    needs_repo_root = require_filled or require_structure_validated or require_wireframe_approved or require_visual_approved
    approved_gate = require_structure_validated or require_wireframe_approved or require_visual_approved
    if needs_repo_root and repo_root is None:
        _add(problems, "source verification requires --repo-root")
        return problems

    if repo_root is None:
        return problems

    root = repo_root.resolve()
    source = _section(active, "## Source Product Definition") or ""
    wireframe = _section(active, wireframe_heading(active)) or ""
    style = _section(active, "## Style Integration") or ""
    visual = _section(active, "## Visual Approval") or ""
    gate = _section(active, "## Design System Need Gate") or ""
    source_values = {
        name: _field(source, name)
        for name in ("PRD source", "Architecture source", "Stack source")
    }
    recorded_wireframe = _field(wireframe, "Wireframe")
    recorded_prd = source_values.get("PRD source")
    recorded_hifi = _field(style, "Connected HiFi reference")
    recorded_target = _field(visual, "Approved target")
    for name, value in source_values.items():
        _resolve_source(value, repo_root=root, label=name, problems=problems)
    _resolve_source(recorded_wireframe, repo_root=root, label="Wireframe", problems=problems)
    _resolve_source(
        _field(wireframe, "Frozen PRD basis"),
        repo_root=root,
        label="Frozen PRD basis",
        problems=problems,
    )
    if not modern or require_visual_approved:
        _resolve_source(recorded_hifi, repo_root=root, label="Connected HiFi reference", problems=problems)
        _resolve_target_source(recorded_target, repo_root=root, label="Approved target", problems=problems)

    if require_visual_approved:
        _direction_comparison(style, _section(active, "## UI Design Intake") or "", None, problems, repo_root=root)

    if approved_gate:
        product_matches = [
            SOURCE_RE.fullmatch((source_values.get(name) or "").strip())
            for name in ("PRD source", "Architecture source", "Stack source")
        ]
        if all(product_matches):
            try:
                import check_product_package

                product_problems = check_product_package.validate(
                    *(root / match.group("path") for match in product_matches if match is not None),
                    require_filled=True,
                    require_approved=True,
                    repo_root=root,
                )
                problems.extend(f"product-definition: {item}" for item in product_problems)
            except (ImportError, OSError, UnicodeError) as exc:
                _add(problems, f"cannot run the Product Definition checker: {exc}")

    # Approved publication always checks the exact files named by the contract;
    # callers cannot substitute a convenient sibling or a stale staging copy.
    checked_prd = _require_exact_cli_path(
        prd_path,
        recorded_prd,
        repo_root=root,
        label="PRD",
        problems=problems,
    ) if approved_gate else prd_path
    checked_wireframe = _require_exact_cli_path(
        wireframes_path,
        recorded_wireframe,
        repo_root=root,
        label="Wireframe",
        problems=problems,
    ) if approved_gate else wireframes_path

    target_scope_for_evidence = _target_scope(recorded_target, "Approved target", problems) if approved_gate and (not modern or require_visual_approved) else None
    capture_mode = (
        target_scope_for_evidence.get("captureMode")
        if isinstance(target_scope_for_evidence, dict)
        else None
    )
    evidence_matrix = None
    if isinstance(target_scope_for_evidence, dict):
        responsive = target_scope_for_evidence.get("responsive", {})
        responsive_targets = [str(item) for item in responsive.get("targets", [])] if isinstance(responsive, dict) else []
        evidence_matrix = {
            "cases": [
                {"surface": str(surface.get("id")), "state": str(state), "target": target}
                for surface in target_scope_for_evidence.get("surfaces", [])
                if isinstance(surface, dict)
                for state in surface.get("states", [])
                for target in (
                    [str(item) for item in surface.get("responsive", {}).get("targets", [])]
                    if isinstance(surface.get("responsive"), dict)
                    else responsive_targets
                )
            ]
        }
    if modern and checked_wireframe is not None and evidence_matrix is None:
        data_for_matrix = _read_wireframe_data(checked_wireframe, problems)
        if isinstance(data_for_matrix, dict):
            evidence_matrix = {"cases": [
                {"surface": screen["id"], "state": state["id"], "target": str(target)}
                for screen in data_for_matrix.get("screens", [])
                for state in screen.get("states", [])
                for target in (data_for_matrix.get("responsiveBySurface", {}).get(screen["id"], {}).get("targets")
                               or data_for_matrix.get("viewports") or data_for_matrix.get("sizeClasses") or [])
            ]}
            capture_mode = "mixed" if data_for_matrix.get("responsiveBySurface") else (
                "hosted-browser" if data_for_matrix.get("viewports") else "native")
    if modern and approved_gate:
        problems.extend(author_artifact_findings(root, active, require_hifi=require_visual_approved))
    if require_visual_approved:
        checked_hifi = _require_exact_cli_path(
            hifi_path,
            recorded_target,
            repo_root=root,
            label="HiFi",
            problems=problems,
        )
        if checked_hifi is not None:
            _validate_hifi_surface(checked_hifi, problems, target_scope_for_evidence,
                                   require_connected=True, require_reviewer_v3=modern)
            _resolve_source(
                recorded_hifi,
                repo_root=root,
                label="Connected HiFi reference",
                problems=problems,
            )
        motion_intents_for_evidence = _validate_motion_table(
            _section(active, "## Motion And Media Intent") or "",
            require_filled=True,
            problems=problems,
        )
        motion_effect_evidence = _motion_effect_evidence(
            style,
            motion_intents_for_evidence,
            problems,
        )
        for field_name in (
            "Impeccable critique",
            "Impeccable audit",
            "UI grading",
            "HiFi surface check",
        ):
            _resolve_evidence(
                _field(_section(active, "## HiFi Review") or "", field_name),
                repo_root=root,
                label=field_name,
                problems=problems,
                expected_artifact=(
                    TARGET_SOURCE_RE.fullmatch((recorded_target or "").strip()).group("path")
                    if TARGET_SOURCE_RE.fullmatch((recorded_target or "").strip())
                    else None
                ),
                expected_check=_evidence_check("HiFi UI grading" if field_name == "UI grading" else field_name, capture_mode),
                expected_matrix=evidence_matrix,
                require_machine=modern,
                required_inputs=[identity for value in [*source_values.values(), recorded_wireframe] if (identity := _source_identity(value)) is not None],
                recorded_scores={name: _score(_field(_section(active, "## HiFi Review") or "", name)) for name in ("HiFi score", "HiFi lowest dimension", "H2 score", "H4 score", "H5 score", "H7 score", "H8 score", "H9 score")} if field_name == "UI grading" else None,
            )
        _resolve_motion_effect_evidence(
            motion_effect_evidence,
            motion_intents_for_evidence,
            target_scope_for_evidence,
            recorded_hifi,
            repo_root=root,
            problems=problems,
            require_machine=modern,
            required_inputs=[identity for value in [*source_values.values(), recorded_wireframe]
                             if (identity := _source_identity(value)) is not None],
        )
        if checked_hifi is not None:
            target_match = TARGET_SOURCE_RE.fullmatch((recorded_target or "").strip())
            hifi_match = SOURCE_RE.fullmatch((recorded_hifi or "").strip())
            if target_match and hifi_match and (
                target_match.group("path") != hifi_match.group("path")
                or target_match.group("sha256") != hifi_match.group("sha256")
            ):
                _add(problems, "Connected HiFi reference and Approved target must be identical")

    if approved_gate:
        for field_name in ("Responsive surface check", "UI grading"):
            _resolve_evidence(
                _field(wireframe, field_name),
                repo_root=root,
                label=field_name,
                problems=problems,
                expected_artifact=(
                    SOURCE_RE.fullmatch((recorded_wireframe or "").strip()).group("path")
                    if SOURCE_RE.fullmatch((recorded_wireframe or "").strip())
                    else None
                ),
                expected_check=_evidence_check("Wireframe UI grading" if field_name == "UI grading" else field_name, capture_mode),
                expected_matrix=evidence_matrix,
                require_machine=modern,
                required_inputs=[identity for value in source_values.values()
                                 if (identity := _source_identity(value)) is not None],
                recorded_scores={name: _score(_field(wireframe, name)) for name in ("Wireframe score", "Wireframe lowest dimension", "W5 score")} if field_name == "UI grading" else None,
            )

    architecture_value = source_values.get("Architecture source")
    architecture_match = SOURCE_RE.fullmatch(architecture_value or "")
    if architecture_match:
        architecture_path = root / architecture_match.group("path")
        try:
            architecture_text = architecture_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            _add(problems, f"cannot read Architecture source for release targets: {exc}")
        else:
            contract, release_findings = parse_release_targets(architecture_text)
            problems.extend(f"ui-design: {finding}" for finding in release_findings)
            if require_visual_approved and contract.explicit_none_reason is not None:
                _add(problems, "a UI-bearing product requires architecture Release Targets")

    if checked_wireframe is not None:
        problems.extend(
            check_wireframe_html.validate(
                checked_wireframe,
                require_filled=require_filled,
                require_approved=approved_gate and not modern,
                require_structure_validated=approved_gate and modern,
                prd_path=checked_prd,
            )
        )

    if modern and approved_gate and checked_prd is not None and checked_wireframe is not None:
        try:
            wf_data = _read_wireframe_data(checked_wireframe, problems)
            manifest = None
            if require_visual_approved and checked_hifi is not None:
                matches = list(HIFI_MANIFEST_RE.finditer(checked_hifi.read_text(encoding="utf-8")))
                manifest = json.loads(matches[0].group("data")) if len(matches) == 1 else {}
            if isinstance(wf_data, dict):
                problems.extend(coverage_findings(checked_prd.read_text(encoding="utf-8"), wf_data, manifest))
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            _add(problems, f"operation coverage cannot be established: {exc}")

    if require_visual_approved and checked_prd is not None and checked_wireframe is not None:
        scope = _target_scope(recorded_target, "Approved target", problems)
        architecture_match = SOURCE_RE.fullmatch((source_values.get("Architecture source") or "").strip())
        stack_match = SOURCE_RE.fullmatch((source_values.get("Stack source") or "").strip())
        if scope is not None and architecture_match is not None and stack_match is not None:
            try:
                architecture_text = (root / architecture_match.group("path")).read_text(encoding="utf-8")
                stack_text = (root / stack_match.group("path")).read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                _add(problems, f"cannot read architecture/stack for Approved target scope join: {exc}")
            else:
                _validate_target_scope_join(
                    scope,
                    prd_path=checked_prd,
                    wireframes_path=checked_wireframe,
                    stack_text=stack_text,
                    architecture_text=architecture_text,
                    problems=problems,
                )

    if require_visual_approved:
        gate_decision = (_field(gate, "Decision") or "").strip().casefold()
        compiled = _field(gate, "Compiled design system pair")
        replacement = _field(gate, "Replacement visual contract when_not_required") or _field(
            gate, "Replacement visual contract when not_required"
        )
        if gate_decision == "required" and not _allow_pending_design_system_pair:
            pair_match = PAIR_RE.fullmatch((compiled or "").strip()) if compiled else None
            if design_system_markdown_path is None or design_system_registry_path is None:
                _add(problems, "required Design System Need Gate requires --design-system-markdown and --design-system-registry")
            if pair_match is not None:
                _resolve_pair(
                    compiled,
                    repo_root=root,
                    label="Compiled design system pair",
                    problems=problems,
                )
                expected_md = pair_match.group("markdown")
                expected_json = pair_match.group("registry")
                for arg, expected, label in (
                    (design_system_markdown_path, expected_md, "Design system Markdown"),
                    (design_system_registry_path, expected_json, "Design system registry"),
                ):
                    if arg is None:
                        continue
                    relative = _relative_cli_path(arg, root, label, problems)
                    if relative is not None and relative.casefold() != expected.casefold():
                        _add(problems, f"{label} CLI path must exactly match recorded path {expected}")
                    if relative is not None and arg.is_file():
                        actual_digest = hashlib.sha256(arg.read_bytes()).hexdigest()
                        expected_digest = (
                            pair_match.group("markdown_sha256")
                            if label == "Design system Markdown"
                            else pair_match.group("registry_sha256")
                        )
                        if actual_digest != expected_digest:
                            _add(problems, f"{label} sha256 does not match the recorded pair")
                if design_system_markdown_path is not None and design_system_registry_path is not None:
                    try:
                        from check_design_system_pair import compare as compare_pair
                        pair_markdown = design_system_markdown_path.read_text(encoding="utf-8")
                        pair_registry = json.loads(design_system_registry_path.read_text(encoding="utf-8"))
                    except (OSError, UnicodeError, json.JSONDecodeError, ImportError) as exc:
                        _add(problems, f"cannot read compiled design system pair: {exc}")
                    else:
                        if isinstance(pair_registry, dict):
                            pair_problems = compare_pair(
                                pair_markdown,
                                pair_registry,
                                require_filled=True,
                                repo_root=root,
                            )
                            problems.extend(f"design-system pair: {item}" for item in pair_problems)
                            bindings = pair_registry.get("sourceBindings")
                            expected_bindings = {
                                "prd": recorded_prd,
                                "architecture": source_values.get("Architecture source"),
                                "stack": source_values.get("Stack source"),
                                "uiDesign": None,
                                "wireframe": recorded_wireframe,
                                "hifi": recorded_hifi,
                            }
                            ui_relative = _relative_cli_path(ui_design_path, root, "UI design", problems)
                            if ui_relative is not None:
                                try:
                                    ui_digest = canonical_ui_approval_sha256(
                                        ui_design_path.read_text(encoding="utf-8")
                                    )
                                except (OSError, UnicodeError):
                                    ui_digest = ""
                                expected_bindings["uiDesign"] = f"{ui_relative} @ sha256:{ui_digest}"
                            for key, expected_value in expected_bindings.items():
                                expected_match = SOURCE_RE.fullmatch((expected_value or "").strip())
                                actual = bindings.get(key) if isinstance(bindings, dict) else None
                                if expected_match is None or not isinstance(actual, dict):
                                    continue
                                if actual.get("path") != expected_match.group("path") or actual.get("sha256") != expected_match.group("sha256"):
                                    _add(problems, f"compiled pair sourceBindings.{key} does not match UI/Product identities")
        elif gate_decision == "not_required":
            parts = _replacement_parts(replacement, problems)
            if design_system_markdown_path is not None or design_system_registry_path is not None:
                _add(problems, "not_required Design System Need Gate must not receive compiled pair CLI paths")
            expected_values = {
                "prd": recorded_prd,
                "wireframe": recorded_wireframe,
                "target": None,
                "ui-design": None,
            }
            target_match = TARGET_SOURCE_RE.fullmatch((recorded_target or "").strip())
            if target_match is not None:
                expected_values["target"] = (
                    f"{target_match.group('path')} @ sha256:{target_match.group('sha256')}"
                )
            ui_relative = _relative_cli_path(ui_design_path, root, "UI design", problems)
            if ui_relative is not None:
                try:
                    ui_digest = canonical_ui_approval_sha256(ui_design_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError):
                    ui_digest = ""
                expected_values["ui-design"] = f"{ui_relative} @ sha256:{ui_digest}"
            for key, expected_value in expected_values.items():
                if key not in parts or parts[key] != expected_value:
                    _add(problems, f"not_required replacement {key} must exactly match the recorded source")

        # A retained formal pair and a not_required gate are mutually
        # exclusive unless the owner has recorded an explicit disposition.
        # The disposition is machine-bound to the canonical pair paths so a
        # stale pair cannot silently remain executable.
        if gate_decision == "not_required":
            disposition = _field(gate, "Existing design-system pair disposition") or ""
            disposition_match = PAIR_DISPOSITION_RE.fullmatch(disposition.strip())
            pair_paths = (
                root / "docs/design/design-system.md",
                root / "docs/design/design-system.json",
            )
            pair_present = any(path.exists() for path in pair_paths)
            if disposition_match is not None:
                decision = disposition_match.group("decision").casefold()
                if decision == "none" and pair_present:
                    _add(problems, "not_required existing pair disposition none conflicts with an existing design-system pair")
                elif decision == "retain" and not all(path.is_file() for path in pair_paths):
                    _add(problems, "not_required existing pair disposition retain requires both canonical pair files")
                elif decision == "retire" and pair_present:
                    _add(problems, "not_required existing pair disposition retire requires the canonical pair to be archived before publication")
    return problems


def validate(
    ui_design_path: Path,
    *,
    repo_root: Path | None = None,
    prd_path: Path | None = None,
    wireframes_path: Path | None = None,
    hifi_path: Path | None = None,
    design_system_markdown_path: Path | None = None,
    design_system_registry_path: Path | None = None,
    require_filled: bool = False,
    require_wireframe_approved: bool = False,
    require_structure_validated: bool = False,
    require_visual_approved: bool = False,
) -> list[str]:
    """Validate a UI contract for normal publication.

    Pair verification is deliberately not a caller-selectable boolean.  The
    only pair-less route is the exact compiler preflight below, which requires
    the pending marker and all upstream approval gates.
    """

    return _validate_impl(
        ui_design_path,
        repo_root=repo_root,
        prd_path=prd_path,
        wireframes_path=wireframes_path,
        hifi_path=hifi_path,
        design_system_markdown_path=design_system_markdown_path,
        design_system_registry_path=design_system_registry_path,
        require_filled=require_filled,
        require_wireframe_approved=require_wireframe_approved,
        require_structure_validated=require_structure_validated,
        require_visual_approved=require_visual_approved,
    )


def _validate_for_design_system_preflight(
    ui_design_path: Path,
    *,
    repo_root: Path,
    prd_path: Path,
    wireframes_path: Path,
    hifi_path: Path,
) -> list[str]:
    """Validate an exact required-gate candidate immediately before compile.

    This is intentionally the sole internal pair-less entry point.  It is not
    exposed as a CLI switch and refuses to run without every upstream source
    and the final visual gate.
    """

    return _validate_impl(
        ui_design_path,
        repo_root=repo_root,
        prd_path=prd_path,
        wireframes_path=wireframes_path,
        hifi_path=hifi_path,
        require_filled=True,
        require_wireframe_approved=not is_structure_review(ui_design_path.read_text(encoding="utf-8")),
        require_structure_validated=is_structure_review(ui_design_path.read_text(encoding="utf-8")),
        require_visual_approved=True,
        _allow_pending_design_system_pair=True,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui-design", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--prd", type=Path)
    parser.add_argument("--wireframes", type=Path)
    parser.add_argument("--hifi", type=Path)
    parser.add_argument("--design-system-markdown", type=Path)
    parser.add_argument("--design-system-registry", type=Path)
    parser.add_argument("--require-filled", action="store_true")
    parser.add_argument("--require-wireframe-approved", action="store_true")
    parser.add_argument("--require-structure-validated", action="store_true")
    parser.add_argument("--require-visual-approved", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    problems = validate(
        args.ui_design,
        repo_root=args.repo_root,
        prd_path=args.prd,
        wireframes_path=args.wireframes,
        hifi_path=args.hifi,
        design_system_markdown_path=args.design_system_markdown,
        design_system_registry_path=args.design_system_registry,
        require_filled=args.require_filled,
        require_wireframe_approved=args.require_wireframe_approved,
        require_structure_validated=args.require_structure_validated,
        require_visual_approved=args.require_visual_approved,
    )
    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        return 1
    print("PASS UI design contract is complete for the requested gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate the staged UI design decision and approval contract."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import check_wireframe_html

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
    r"scope=(?P<scope>[^;]+)$"
)
PAIR_RE = re.compile(
    r"^(?P<markdown>[A-Za-z0-9._/-]+) @ sha256:(?P<markdown_sha256>[0-9a-f]{64})"
    r" and (?P<registry>[A-Za-z0-9._/-]+) @ sha256:(?P<registry_sha256>[0-9a-f]{64})$"
)
EVIDENCE_RE = re.compile(
    r"^PASS\s+—\s+evidence=(?P<path>[A-Za-z0-9._/-]+)\s+@\s+"
    r"sha256:(?P<sha256>[0-9a-f]{64})(?:;\s*(?P<details>.+))?$"
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
VALID_MOTION_DIRECTIONS = {"not_required", "functional_only", "expressive", "recommend"}
VALID_WIREFRAME_DECISIONS = {"draft", "approved", "revision_requested", "blocked"}
VALID_DIRECTION_DECISIONS = {"approved", "selected", "mixed-and-approved"}


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
    return normalized not in NON_HUMAN_OWNERS


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
            "sha256:<lowercase sha256>; <details>'",
        )
        return None
    return {
        "path": match.group("path"),
        "sha256": match.group("sha256"),
        "details": match.group("details") or "",
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


def _validate_motion_table(
    section: str, *, require_filled: bool, problems: list[str]
) -> dict[str, dict[str, str]]:
    rows = _table_rows(section)
    expected = [
        "intent id",
        "ui scope / region",
        "treatment",
        "purpose and trigger",
        "static / reduced-motion fallback",
        "generation route",
        "status",
    ]
    intents: dict[str, dict[str, str]] = {}
    if not rows or [cell.casefold() for cell in rows[0]] != expected:
        _add(problems, "Motion And Media Intent has no canonical seven-column table")
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
        status = row[6].casefold()
        if status == "blocked" or (
            require_filled and status not in VALID_MOTION_STATUSES
        ):
            _add(problems, f"{intent_id} has invalid status {row[6]!r}")
        else:
            intents[intent_id] = {
                "scope": row[1].strip(),
                "treatment": row[2],
                "purpose": row[3],
                "fallback": row[4],
                "generationRoute": row[5],
                "status": row[6],
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
    if not _filled(value) or TARGET_SOURCE_RE.fullmatch(value.strip()) is None:
        _add(
            problems,
            f"{label} must use '<repo-relative-path> @ sha256:<lowercase sha256>; "
            "scope=<exact scope>'",
        )
        return False
    return True


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
    candidate = (repo_root / relative).resolve()
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError:
        _add(problems, f"{label} path escapes repo-root: {relative}")
        return
    if not candidate.is_file():
        _add(problems, f"{label} path does not exist: {relative}")
        return
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != match.group("sha256"):
        _add(problems, f"{label} sha256 does not match current bytes: {relative}")


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
) -> None:
    parsed = _pass_evidence(value, label, problems)
    if parsed is None:
        return
    _resolve_source(
        f"{parsed['path']} @ sha256:{parsed['sha256']}",
        repo_root=repo_root,
        label=f"{label} evidence",
        problems=problems,
    )


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
    if not isinstance(value, dict) or value.get("schema") != check_wireframe_html.WIREFRAME_SCHEMA:
        return []
    found: list[dict[str, Any]] = []

    def visit(node: Any, owner_path: str, screen_id: str | None = None, region_id: str | None = None) -> None:
        if isinstance(node, dict):
            current_screen = screen_id
            current_region = region_id
            if owner_path.startswith("wireframe-data.screens["):
                candidate = node.get("id")
                current_screen = candidate if isinstance(candidate, str) else current_screen
            if ".regions[" in owner_path:
                candidate = node.get("id")
                current_region = candidate if isinstance(candidate, str) else current_region
            intent = node.get("mediaIntent")
            if isinstance(intent, dict):
                intent_id = intent.get("id")
                if not isinstance(intent_id, str) or not MM_ID_RE.fullmatch(intent_id):
                    _add(problems, f"{owner_path}.mediaIntent.id must be a valid MM-* ID")
                elif not isinstance(current_screen, str) or not current_screen.strip():
                    _add(
                        problems,
                        f"{owner_path}.mediaIntent must be attached to an explicit screen or region",
                    )
                else:
                    if current_region is None and not owner_path.startswith("wireframe-data.screens["):
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
                    child_path = f"{owner_path}.{key}" if key != "regions" else owner_path
                    visit(child, child_path, current_screen, current_region)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, f"{owner_path}[{index}]")

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
            if projected_intent.get("reducedMotionFallback") != intent.get("fallback"):
                _add(problems, f"{intent_id} reduced-motion fallback differs from the wireframe")
            if projected_intent.get("generationRoute") != intent.get("generationRoute"):
                _add(
                    problems,
                    f"{intent_id} generation route authority differs from the wireframe",
                )

    for intent_id in sorted(set(projected_by_id) - set(intents)):
        _add(
            problems,
            f"wireframe mediaIntent {intent_id} has no Motion And Media Intent row",
        )


def validate_text(
    text: str,
    *,
    require_filled: bool = False,
    require_wireframe_approved: bool = False,
    require_visual_approved: bool = False,
) -> list[str]:
    text = active_text(text)
    problems: list[str] = []
    positions: list[int] = []
    sections: dict[str, str] = {}
    for heading in REQUIRED_HEADINGS:
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
            require_filled=require_filled or require_wireframe_approved or require_visual_approved,
            problems=problems,
        )
        if require_filled or require_wireframe_approved or require_visual_approved:
            for name in ("PRD source", "Architecture source", "Stack source"):
                _source_syntax(values.get(name), name, problems)
        for name in ("Product Definition Approval", "Stack Decision Checkpoint"):
            if (require_filled or require_wireframe_approved or require_visual_approved) and values.get(name, "").casefold() != "approved":
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
        direction = motion_values.get("Motion direction", "").split("—", 1)[0].strip().casefold()
        if (require_filled or require_wireframe_approved or require_visual_approved) and direction not in VALID_MOTION_DIRECTIONS:
            _add(
                problems,
                "Motion And Media Intent Motion direction must be one of "
                + ", ".join(sorted(VALID_MOTION_DIRECTIONS)),
            )
        motion_intents = _validate_motion_table(
            motion, require_filled=require_filled, problems=problems
        )

    wireframe = sections.get("## Wireframe Approval")
    wireframe_source_ok = False
    wireframe_path: Path | None = None
    if wireframe is not None:
        values = _require_fields(
            wireframe,
            (
                "Wireframe",
                "Frozen PRD basis",
                "Copy Freeze",
                "Copy owner",
                "Copy locale",
                "Copy approved on",
                "Responsive browser check",
                "UI grading",
                "Wireframe score",
                "Wireframe lowest dimension",
                "Wireframe blocks",
                "Decision",
                "Decision owner",
                "Decided on",
            ),
            label="Wireframe Approval",
            require_filled=require_filled or require_wireframe_approved or require_visual_approved,
            problems=problems,
        )
        wireframe_value = values.get("Wireframe")
        wireframe_source_ok = _source_syntax(wireframe_value, "Wireframe", problems) if (require_filled or require_wireframe_approved or require_visual_approved) else False
        if wireframe_source_ok and wireframe_value:
            wireframe_path = Path(wireframe_value.split(" @ ", 1)[0])
        if require_filled or require_wireframe_approved or require_visual_approved:
            _source_syntax(values.get("Frozen PRD basis"), "Frozen PRD basis", problems)
        if require_wireframe_approved or require_visual_approved:
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
                values.get("Responsive browser check"),
                "Responsive browser check",
                problems,
            )
            _pass_evidence(values.get("UI grading"), "Wireframe UI grading", problems)
            overall = _score(values.get("Wireframe score"))
            lowest = _score(values.get("Wireframe lowest dimension"))
            if overall is None or overall < 80:
                _add(problems, "Wireframe score must be an integer from 80 to 100")
            if lowest is None or lowest < 60:
                _add(
                    problems,
                    "Wireframe lowest dimension must be an integer from 60 to 100",
                )
            if values.get("Wireframe blocks", "").casefold().strip() != "none":
                _add(problems, "Wireframe blocks must be none")

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
                "Connected HiFi reference",
            ),
            label="Style Integration",
            require_filled=True,
            problems=problems,
        )
        if style_values.get("Design author", "").casefold() != "frontend-design":
            _add(problems, "Style Integration Design author must be frontend-design")
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
                "HiFi browser check",
                "HiFi score",
                "H2 score",
                "H4 score",
                "H8 score",
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
            review_values.get("HiFi browser check"), "HiFi browser check", problems
        )
        for name, minimum in (
            ("HiFi score", 90),
            ("H2 score", 90),
            ("H4 score", 90),
            ("H8 score", 90),
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
            ("Decision", "Decision owner", "Decided on", "Reason"),
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
        replacement = _field_values(gate, "Replacement visual contract when not_required")
        if gate_decision == "required":
            if len(compiled) != 1:
                _add(
                    problems,
                    "required Design System Need Gate is missing exactly one compiled pair field",
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

    if (
        (require_wireframe_approved or require_visual_approved)
        and wireframe_path is not None
        and wireframe_source_ok
        and wireframe_path.exists()
    ):
        _join_motion_intents(motion_intents, wireframe_path, problems=problems)
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
        require_visual_approved=require_visual_approved,
    )

    active = active_text(text)
    needs_repo_root = require_filled or require_wireframe_approved or require_visual_approved
    approved_gate = require_wireframe_approved or require_visual_approved
    if needs_repo_root and repo_root is None:
        _add(problems, "source verification requires --repo-root")
        return problems

    if repo_root is None:
        return problems

    root = repo_root.resolve()
    source = _section(active, "## Source Product Definition") or ""
    wireframe = _section(active, "## Wireframe Approval") or ""
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
    _resolve_source(recorded_hifi, repo_root=root, label="Connected HiFi reference", problems=problems)
    _resolve_target_source(recorded_target, repo_root=root, label="Approved target", problems=problems)

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

    if require_visual_approved:
        checked_hifi = _require_exact_cli_path(
            hifi_path,
            recorded_target,
            repo_root=root,
            label="HiFi",
            problems=problems,
        )
        if checked_hifi is not None:
            _resolve_source(
                recorded_hifi,
                repo_root=root,
                label="Connected HiFi reference",
                problems=problems,
            )
        for field_name in (
            "Impeccable critique",
            "Impeccable audit",
            "UI grading",
            "HiFi browser check",
        ):
            _resolve_evidence(
                _field(_section(active, "## HiFi Review") or "", field_name),
                repo_root=root,
                label=field_name,
                problems=problems,
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
        for field_name in ("Responsive browser check", "UI grading"):
            _resolve_evidence(
                _field(wireframe, field_name),
                repo_root=root,
                label=field_name,
                problems=problems,
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
                require_approved=approved_gate,
                prd_path=checked_prd,
            )
        )

    if require_visual_approved:
        gate_decision = (_field(gate, "Decision") or "").strip().casefold()
        compiled = _field(gate, "Compiled design system pair")
        replacement = _field(gate, "Replacement visual contract when not_required")
        if gate_decision == "required":
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
                                ui_digest = hashlib.sha256(ui_design_path.read_bytes()).hexdigest()
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
                expected_values["ui-design"] = f"{ui_relative} @ sha256:{hashlib.sha256(ui_design_path.read_bytes()).hexdigest()}"
            for key, expected_value in expected_values.items():
                if key not in parts or parts[key] != expected_value:
                    _add(problems, f"not_required replacement {key} must exactly match the recorded source")
    return problems


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

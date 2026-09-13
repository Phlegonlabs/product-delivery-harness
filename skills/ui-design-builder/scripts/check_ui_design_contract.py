#!/usr/bin/env python3
"""Validate the staged UI design decision and approval contract."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import check_wireframe_html


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
    return bool(value and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()))


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
) -> None:
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
    if not rows or [cell.casefold() for cell in rows[0]] != expected:
        _add(problems, "Motion And Media Intent has no canonical seven-column table")
        return
    data_rows = rows[1:]
    if require_filled and not data_rows:
        _add(problems, "Motion And Media Intent has no decision row")
    seen: set[str] = set()
    for row in data_rows:
        if len(row) != len(expected):
            _add(problems, "Motion And Media Intent row has the wrong width")
            continue
        intent_id = row[0]
        if not re.fullmatch(r"MM-[A-Z0-9]+(?:-[A-Z0-9]+)*", intent_id):
            _add(problems, f"invalid Motion And Media Intent ID {intent_id!r}")
        elif intent_id in seen:
            _add(problems, f"duplicate Motion And Media Intent ID {intent_id}")
        seen.add(intent_id)
        if row[2].casefold() not in VALID_TREATMENTS:
            _add(problems, f"{intent_id} has invalid treatment {row[2]!r}")
        if require_filled and any(not _filled(cell) for cell in row):
            _add(problems, f"{intent_id} contains an empty value or placeholder")
        if row[6].casefold() == "blocked":
            _add(problems, f"{intent_id} remains blocked")


def validate_text(
    text: str,
    *,
    require_filled: bool = False,
    require_wireframe_approved: bool = False,
    require_visual_approved: bool = False,
) -> list[str]:
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
            require_filled=require_filled,
            problems=problems,
        )
        for name in ("Product Definition Approval", "Stack Decision Checkpoint"):
            if require_filled and not values.get(name, "").casefold().startswith("approved"):
                _add(problems, f"{name} must be approved")

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
            _add(problems, "UI Design Intake Decided on must use YYYY-MM-DD")

    motion = sections.get("## Motion And Media Intent")
    if motion is not None:
        _require_fields(
            motion,
            ("Motion direction",),
            label="Motion And Media Intent",
            require_filled=require_filled,
            problems=problems,
        )
        _validate_motion_table(motion, require_filled=require_filled, problems=problems)

    wireframe = sections.get("## Wireframe Approval")
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
            require_filled=require_filled or require_wireframe_approved,
            problems=problems,
        )
        if require_wireframe_approved and values.get("Decision", "").casefold() != "approved":
            _add(problems, "Wireframe Approval Decision must be approved")
        if require_wireframe_approved and values.get("Copy Freeze", "").casefold() != "approved":
            _add(problems, "Wireframe Approval Copy Freeze must be approved")
        if require_wireframe_approved and not _human_owner(values.get("Copy owner")):
            _add(problems, "Wireframe Approval Copy owner must be human")
        if require_wireframe_approved and not check_wireframe_html.LOCALE_RE.fullmatch(
            values.get("Copy locale", "").strip()
        ):
            _add(problems, "Wireframe Approval Copy locale must be a BCP 47 locale")
        if require_wireframe_approved and not _date(values.get("Copy approved on")):
            _add(problems, "Wireframe Approval Copy approved on must use YYYY-MM-DD")
        if require_wireframe_approved and not _human_owner(values.get("Decision owner")):
            _add(problems, "Wireframe Approval Decision owner must be human")
        if require_wireframe_approved and not _date(values.get("Decided on")):
            _add(problems, "Wireframe Approval Decided on must use YYYY-MM-DD")
        if require_wireframe_approved:
            overall = _score(values.get("Wireframe score"))
            lowest = _score(values.get("Wireframe lowest dimension"))
            if overall is None or overall < 80:
                _add(problems, "Wireframe score must be an integer from 80 to 100")
            if lowest is None or lowest < 60:
                _add(
                    problems,
                    "Wireframe lowest dimension must be an integer from 60 to 100",
                )
            if not values.get("Wireframe blocks", "").casefold().startswith("none"):
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
        if style_values.get("Direction decision", "").casefold() not in {
            "approved",
            "selected",
            "mixed-and-approved",
        }:
            _add(problems, "Style Integration Direction decision is not approved")
        if not _human_owner(style_values.get("Direction decision owner")):
            _add(problems, "Style Integration Direction decision owner must be human")
        if not _date(style_values.get("Direction decided on")):
            _add(problems, "Style Integration Direction decided on must use YYYY-MM-DD")

        review = sections.get("## HiFi Review", "")
        _require_fields(
            review,
            (
                "Impeccable critique",
                "Impeccable audit",
                "UI grading",
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
        review_values = {
            name: _field(review, name)
            for name in (
                "HiFi score",
                "H2 score",
                "H4 score",
                "H8 score",
                "HiFi lowest dimension",
                "HiFi blocks or disputes",
            )
        }
        for name, minimum in (
            ("HiFi score", 90),
            ("H2 score", 90),
            ("H4 score", 90),
            ("H8 score", 90),
            ("HiFi lowest dimension", 60),
        ):
            score = _score(review_values[name])
            if score is None or score < minimum:
                _add(problems, f"{name} must be an integer from {minimum} to 100")
        if not (review_values["HiFi blocks or disputes"] or "").casefold().startswith(
            "none"
        ):
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
            _add(problems, "Visual Approval Decided on must use YYYY-MM-DD")

        gate = sections.get("## Design System Need Gate", "")
        gate_values = _require_fields(
            gate,
            ("Decision", "Decision owner", "Reason"),
            label="Design System Need Gate",
            require_filled=True,
            problems=problems,
        )
        gate_decision = gate_values.get("Decision", "").casefold()
        if gate_decision not in {"required", "not_required"}:
            _add(problems, "Design System Need Gate must be required or not_required")
        if not _human_owner(gate_values.get("Decision owner")):
            _add(problems, "Design System Need Gate Decision owner must be human")

    return problems


def validate(
    ui_design_path: Path,
    *,
    prd_path: Path | None = None,
    wireframes_path: Path | None = None,
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
    if wireframes_path is not None:
        problems.extend(
            check_wireframe_html.validate(
                wireframes_path,
                require_filled=require_filled,
                require_approved=require_wireframe_approved or require_visual_approved,
                prd_path=prd_path,
            )
        )
    elif require_wireframe_approved or require_visual_approved:
        _add(problems, "approved validation requires --wireframes")
    return problems


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui-design", required=True, type=Path)
    parser.add_argument("--prd", type=Path)
    parser.add_argument("--wireframes", type=Path)
    parser.add_argument("--require-filled", action="store_true")
    parser.add_argument("--require-wireframe-approved", action="store_true")
    parser.add_argument("--require-visual-approved", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    problems = validate(
        args.ui_design,
        prd_path=args.prd,
        wireframes_path=args.wireframes,
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

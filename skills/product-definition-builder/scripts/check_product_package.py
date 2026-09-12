#!/usr/bin/env python3
"""Validate the core Product Definition package and its owner approvals."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

from prd_ui_contract import parse_prd_ui_contract


PRODUCT_APPROVAL_START = "<!-- product-definition-approval:start -->"
PRODUCT_APPROVAL_END = "<!-- product-definition-approval:end -->"
STACK_CHECKPOINT_START = "<!-- stack-decision-checkpoint:start -->"
STACK_CHECKPOINT_END = "<!-- stack-decision-checkpoint:end -->"

VALID_DECISIONS = {"approved", "revision_requested", "blocked"}
VALID_STACK_STATUSES = {
    "required",
    "selected",
    "approved",
    "recommended",
    "provisional",
}
EXECUTABLE_STACK_STATUSES = {"required", "selected", "approved"}

REQUIRED_PRD_HEADINGS = (
    "## At a Glance",
    "## Problem Statement",
    "## Goals",
    "## Non-Goals",
    "## Users and Personas",
    "## User Journeys",
    "## Functional Requirements",
    "## Non-Functional Requirements",
    "## UX Requirements",
    "## Data and Integration Requirements",
    "## Data and Trust",
    "## AI and Automation",
    "## Business Rules",
    "## Monetization and Partner Channels",
    "## Metrics",
    "## Risks",
    "## Assumptions",
    "## Open Questions",
    "## Test Obligations",
    "## Product Definition Decisions",
)

REQUIRED_ARCHITECTURE_HEADINGS = (
    "## Architecture Summary",
    "## Product Archetype",
    "## System Context",
    "## Component Architecture",
    "## Data Model",
    "## API and Interface Contracts",
    "## Workflow and Data Flow",
    "## Auth, Permissions, and Security",
    "## Data and Trust Architecture",
    "## AI and Automation Architecture",
    "## Integrations",
    "## Deployment and Operations",
    "## Observability",
    "## Scaling and Reliability",
    "## Technical Risks and Tradeoffs",
    "## Architecture Trace Index",
)

METRICS_HEADER = (
    "metric",
    "definition",
    "baseline",
    "target / guardrail",
    "measurement window",
    "source / method",
    "owner",
)

ASSUMPTIONS_HEADER = (
    "assumption",
    "impact if wrong",
    "validation",
    "owner",
    "decision date",
    "status",
)

OPEN_QUESTIONS_HEADER = (
    "question",
    "why it matters",
    "owner",
    "decision deadline",
    "blocks approval",
    "status / resolution",
)

ENHANCEMENT_IMPACT_HEADER = (
    "area",
    "impact",
    "affected ids / decisions",
    "required refresh",
)

REQUIRED_ENHANCEMENT_AREAS = {
    "product scope / behavior",
    "ui structure / style",
    "data / integrations",
    "architecture / stack",
    "data trust / ai",
    "monetization / partner",
    "release / operations",
}

STACK_OPTIONS_HEADER = (
    "option id",
    "area",
    "complete bundle",
    "best fit",
    "tradeoffs / ownership",
    "disposition",
)

STACK_LAYER_HEADER = (
    "layer",
    "selection",
    "status",
    "authority / evidence",
    "why it fits",
    "constraint / follow-up",
)

STACK_SECTION_LAYERS = {
    "Frontend Technology Decision": (
        "deployment / runtime",
        "rendering model",
        "language",
        "package manager",
        "framework",
        "ui library",
        "component foundation",
        "styling approach",
        "build tool",
        "routing and data",
        "testing",
    ),
    "Mobile/Desktop Technology Decision": (
        "target operating systems",
        "client strategy",
        "framework",
        "toolchain",
        "navigation and state",
        "local persistence",
        "secure storage",
        "offline sync",
        "push and native modules",
        "backend/api integration",
        "distribution mechanism",
        "testing",
    ),
    "Backend and Data Technology Decision": (
        "service topology",
        "backend runtime / framework",
        "database category",
        "database engine",
        "auth strategy",
        "auth provider",
        "api style",
        "background jobs / queue",
        "file / object storage",
    ),
    "AI and Automation Technology Decision": (
        "model / automation provider",
        "model and version policy",
        "context / retrieval",
        "tool execution and approvals",
        "evaluation and output validation",
        "observability and cost controls",
        "fallback and shutoff",
    ),
    "Monetization and Partner Channel Technology Decision": (
        "store commerce / billing",
        "subscription and entitlement source",
        "paywall / checkout",
        "merchant of record / tax",
        "affiliate / referral / reseller platform",
        "attribution, commission, payout, and reseller operations",
    ),
}

STACK_SECTION_AREAS = {
    "Frontend Technology Decision": "frontend",
    "Mobile/Desktop Technology Decision": "mobile or desktop",
    "Backend and Data Technology Decision": "backend or data",
    "AI and Automation Technology Decision": "ai or automation",
    "Monetization and Partner Channel Technology Decision": "commercial",
}

NON_HUMAN_OWNERS = {
    "ai",
    "agent",
    "assistant",
    "automation",
    "claude",
    "codex",
    "model",
    "system",
}

COMMERCIAL_DECISIONS_HEADER = (
    "decision",
    "selection",
    "product rationale / evidence",
    "status",
    "trace ids",
)

MOTION_GATE_HEADER = (
    "ui scope",
    "gate",
    "purpose and trigger",
    "decision source",
    "reduced-motion fallback",
)

FUNCTIONAL_REQUIREMENTS_HEADER = (
    "id",
    "requirement",
    "priority",
    "acceptance criteria",
)

NFR_HEADER = (
    "id",
    "quality attribute",
    "scope / requirement",
    "measure",
    "target / threshold",
    "test ids",
)

TEST_OBLIGATIONS_HEADER = (
    "test id",
    "obligation",
    "test type",
    "required",
    "upstream trace ids",
    "expected signal",
)


def _add(problems: list[str], path: str, message: str) -> None:
    problems.append(f"{path}: {message}")


def _has_heading(text: str, heading: str) -> bool:
    return re.search(rf"^{re.escape(heading)}\s*$", text, re.MULTILINE) is not None


def _validate_heading_sequence(
    text: str, headings: tuple[str, ...], *, path: str, problems: list[str]
) -> None:
    positions: list[int] = []
    for heading in headings:
        matches = list(re.finditer(rf"^{re.escape(heading)}\s*$", text, re.MULTILINE))
        if not matches:
            _add(problems, path, f"missing required heading {heading!r}")
        elif len(matches) > 1:
            _add(problems, path, f"duplicate required heading {heading!r}")
        else:
            positions.append(matches[0].start())
    if len(positions) == len(headings) and positions != sorted(positions):
        _add(problems, path, "required headings are out of canonical order")


def _extract_machine_block(
    text: str,
    start: str,
    end: str,
    *,
    path: str,
    label: str,
    problems: list[str],
) -> str | None:
    start_count = text.count(start)
    end_count = text.count(end)
    if start_count != 1 or end_count != 1:
        _add(
            problems,
            path,
            f"must contain exactly one matched {label} marker pair",
        )
        return None
    start_index = text.index(start) + len(start)
    end_index = text.index(end)
    if end_index <= start_index:
        _add(problems, path, f"has an invalid {label} marker order")
        return None
    block = text[start_index:end_index].strip()
    if not block:
        _add(problems, path, f"has an empty {label} block")
        return None
    return block


def _bullet_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in re.finditer(r"^\s*-\s*([^:\n]+):\s*(.*?)\s*$", block, re.MULTILINE):
        fields[match.group(1).strip().casefold()] = match.group(2).strip()
    return fields


def _duplicate_bullet_fields(block: str) -> list[str]:
    keys = [
        match.group(1).strip().casefold()
        for match in re.finditer(
            r"^\s*-\s*([^:\n]+):\s*(.*?)\s*$", block, re.MULTILINE
        )
    ]
    return sorted(key for key, count in Counter(keys).items() if count > 1)


def _require_fields(
    fields: dict[str, str],
    names: tuple[str, ...],
    *,
    path: str,
    problems: list[str],
    require_filled: bool,
) -> None:
    for name in names:
        value = fields.get(name.casefold())
        if value is None:
            _add(problems, path, f"missing required field {name!r}")
            continue
        if not value:
            _add(problems, path, f"field {name!r} must not be empty")
        if require_filled and (
            (value.startswith("[") and value.endswith("]"))
            or "<placeholder" in value.casefold()
            or value.casefold() in {"tbd", "todo"}
        ):
            _add(problems, path, f"field {name!r} contains an unfilled placeholder")


def _section(text: str, heading: str) -> str | None:
    match = re.search(
        rf"^{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def _subsection(text: str, heading: str) -> str | None:
    match = re.search(
        rf"^{re.escape(heading)}\s*$([\s\S]*?)(?=^###\s+|^##\s+|\Z)",
        text,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def _table_cells(line: str) -> tuple[str, ...] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return tuple(cell.strip() for cell in stripped[1:-1].split("|"))


def _is_separator_row(cells: tuple[str, ...]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _placeholder_cell(cell: str) -> bool:
    stripped = cell.strip()
    return (
        (stripped.startswith("[") and stripped.endswith("]"))
        or "<placeholder" in stripped.casefold()
        or stripped.casefold() in {"tbd", "todo"}
    )


def _validate_table_rows(
    rows: list[tuple[str, ...]],
    width: int,
    *,
    label: str,
    require_filled: bool,
    problems: list[str],
    path: str = "prd",
) -> None:
    for row in rows:
        if len(row) != width:
            _add(problems, path, f"{label} row has {len(row)} cells, expected {width}")
        elif require_filled and (
            any(not cell.strip() for cell in row)
            or any(_placeholder_cell(cell) for cell in row)
        ):
            _add(problems, path, f"{label} row contains an empty value or placeholder")


def _find_table(
    text: str, expected_header: tuple[str, ...]
) -> list[tuple[str, ...]] | None:
    lines = text.splitlines()
    expected = tuple(cell.casefold() for cell in expected_header)
    for index, line in enumerate(lines):
        cells = _table_cells(line)
        if cells is None or tuple(cell.casefold() for cell in cells) != expected:
            continue
        rows: list[tuple[str, ...]] = []
        for candidate in lines[index + 1 :]:
            candidate_cells = _table_cells(candidate)
            if candidate_cells is None:
                if rows:
                    break
                continue
            if _is_separator_row(candidate_cells):
                continue
            rows.append(candidate_cells)
        return rows
    return None


def _stack_areas(value: str) -> set[str]:
    normalized = value.casefold()
    areas: set[str] = set()
    if "frontend" in normalized:
        areas.add("frontend")
    if "mobile" in normalized or "desktop" in normalized:
        areas.add("mobile or desktop")
    if "backend" in normalized or re.search(r"\bdata\b", normalized):
        areas.add("backend or data")
    if re.search(r"\bai\b", normalized) or "automation" in normalized:
        areas.add("ai or automation")
    if (
        "commercial" in normalized
        or "monetization" in normalized
        or "partner" in normalized
    ):
        areas.add("commercial")
    return areas


def _invalid_human_owner(value: str) -> bool:
    normalized = value.strip().casefold().strip(".:-")
    return (
        not normalized
        or _placeholder_cell(value)
        or normalized in {"none", "unknown", "n/a"}
        or normalized in NON_HUMAN_OWNERS
    )


def _validate_stack_tables(
    stack_text: str,
    *,
    require_filled: bool,
    require_approved: bool,
    required_areas: set[str],
    problems: list[str],
) -> set[str]:
    approved_areas: set[str] = set()
    present_areas: set[str] = set()
    for section_name, required_layers in STACK_SECTION_LAYERS.items():
        section = _section(stack_text, f"## {section_name}")
        if section is None:
            continue
        area = STACK_SECTION_AREAS[section_name]
        present_areas.add(area)
        recorded = _subsection(section, "### Recorded or Approved Stack")
        if recorded is None:
            if area != "commercial" or area in required_areas:
                _add(
                    problems,
                    "stack-decisions",
                    f"{section_name} is missing Recorded or Approved Stack",
                )
            continue
        rows = _find_table(recorded, STACK_LAYER_HEADER)
        if rows is None:
            if area != "commercial" or area in required_areas:
                _add(
                    problems,
                    "stack-decisions",
                    f"{section_name} must use the exact six-column layer table",
                )
            continue
        if require_filled and not rows:
            _add(
                problems,
                "stack-decisions",
                f"{section_name} layer table must contain rows",
            )
        _validate_table_rows(
            rows,
            len(STACK_LAYER_HEADER),
            label=f"{section_name} layer",
            require_filled=require_filled,
            problems=problems,
            path="stack-decisions",
        )
        seen_layers: set[str] = set()
        for cells in rows:
            if len(cells) != len(STACK_LAYER_HEADER):
                continue
            layer = cells[0].casefold()
            if layer in seen_layers:
                _add(
                    problems,
                    "stack-decisions",
                    f"{section_name} has duplicate layer {cells[0]!r}",
                )
            seen_layers.add(layer)
            status = cells[2].casefold()
            if status == "approved":
                approved_areas.add(area)
            if status not in VALID_STACK_STATUSES:
                _add(
                    problems,
                    "stack-decisions",
                    f"layer {cells[0]!r} has invalid status {cells[2]!r}",
                )
            elif require_approved and status not in EXECUTABLE_STACK_STATUSES:
                _add(
                    problems,
                    "stack-decisions",
                    f"layer {cells[0]!r} remains {cells[2]!r}; owner approval is required",
                )
        missing_layers = sorted(set(required_layers) - seen_layers)
        if missing_layers:
            _add(
                problems,
                "stack-decisions",
                f"{section_name} is missing layers: " + ", ".join(missing_layers),
            )
    for area in sorted(required_areas - present_areas):
        _add(
            problems,
            "stack-decisions",
            f"missing required {area} technology decision section",
        )
    return approved_areas


def _gate_record(text: str, label: str) -> tuple[str, str, str] | None:
    match = re.search(
        rf"^{re.escape(label)}:\s*(required|not_required|blocked)\s+—\s+"
        rf"(.+),\s*decided by\s+(.+?)\s*$",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if match is None:
        return None
    return match.group(1).casefold(), match.group(2).strip(), match.group(3).strip()


def _research_gate(text: str) -> tuple[str, str] | None:
    match = re.search(
        r"^Research Gate:\s*(go|clarify|stop|skipped)\b(.*?)$",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if match is None:
        return None
    return match.group(1).casefold(), match.group(2).strip()


def _ids(cell: str, prefix: str) -> set[str]:
    return {
        match.group(0).upper()
        for match in re.finditer(rf"\b{re.escape(prefix)}-[A-Z0-9-]+\b", cell, re.I)
    }


def validate_texts(
    prd_text: str,
    architecture_text: str,
    stack_text: str,
    *,
    require_filled: bool = False,
    require_approved: bool = False,
) -> list[str]:
    """Validate already-decoded core product-package texts."""

    problems: list[str] = []

    _validate_heading_sequence(
        prd_text, REQUIRED_PRD_HEADINGS, path="prd", problems=problems
    )
    _validate_heading_sequence(
        architecture_text,
        REQUIRED_ARCHITECTURE_HEADINGS,
        path="architecture",
        problems=problems,
    )
    if not re.search(r"^#\s+PRD(?::|\s*$)", prd_text, re.MULTILINE):
        _add(problems, "prd", "missing PRD title")
    if not re.search(r"^#\s+Architecture(?::|\s*$)", architecture_text, re.MULTILINE):
        _add(problems, "architecture", "missing Architecture title")
    if not re.search(r"^#\s+Stack Decisions(?::|\s*$)", stack_text, re.MULTILINE):
        _add(problems, "stack-decisions", "missing Stack Decisions title")

    ui_surfaces, ui_contract_errors = parse_prd_ui_contract(
        prd_text, require_responsive=True, web_floor=3
    )
    problems.extend(ui_contract_errors)
    required_stack_areas: set[str] = set()
    for surface in ui_surfaces.values():
        if surface.get("responsiveKind") == "viewports":
            required_stack_areas.add("frontend")
        elif surface.get("responsiveKind") == "sizeClasses":
            required_stack_areas.add("mobile or desktop")

    functional = _section(prd_text, "## Functional Requirements")
    functional_rows = (
        _find_table(functional, FUNCTIONAL_REQUIREMENTS_HEADER)
        if functional is not None
        else None
    )
    if functional_rows is None:
        _add(problems, "prd", "Functional Requirements must use the canonical table")
        functional_rows = []
    else:
        _validate_table_rows(
            functional_rows,
            len(FUNCTIONAL_REQUIREMENTS_HEADER),
            label="Functional Requirements",
            require_filled=require_filled,
            problems=problems,
        )

    nfr = _section(prd_text, "## Non-Functional Requirements")
    nfr_rows = _find_table(nfr, NFR_HEADER) if nfr is not None else None
    if nfr_rows is None:
        _add(problems, "prd", "Non-Functional Requirements must use the canonical table")
        nfr_rows = []
    else:
        _validate_table_rows(
            nfr_rows,
            len(NFR_HEADER),
            label="Non-Functional Requirements",
            require_filled=require_filled,
            problems=problems,
        )

    tests = _section(prd_text, "## Test Obligations")
    test_rows = (
        _find_table(tests, TEST_OBLIGATIONS_HEADER) if tests is not None else None
    )
    if test_rows is None:
        _add(problems, "prd", "Test Obligations must use the canonical table")
        test_rows = []
    else:
        _validate_table_rows(
            test_rows,
            len(TEST_OBLIGATIONS_HEADER),
            label="Test Obligations",
            require_filled=require_filled,
            problems=problems,
        )

    required_coverage: set[str] = set()
    known_test_ids: set[str] = set()
    for row in test_rows:
        if len(row) != len(TEST_OBLIGATIONS_HEADER):
            continue
        test_ids = _ids(row[0], "TEST")
        if len(test_ids) != 1:
            _add(problems, "prd", f"invalid Test Obligations ID {row[0]!r}")
            continue
        test_id = next(iter(test_ids))
        if test_id in known_test_ids:
            _add(problems, "prd", f"duplicate Test Obligations ID {test_id}")
        known_test_ids.add(test_id)
        required = row[3].casefold()
        if required not in {"yes", "no"}:
            _add(problems, "prd", f"{test_id} Required must be Yes or No")
        if required == "yes":
            upstream = _ids(row[4], "PRD")
            if not upstream:
                _add(problems, "prd", f"{test_id} names no upstream PRD ID")
            required_coverage.update(upstream)

    requirement_ids: set[str] = set()
    must_ids: set[str] = set()
    for row in functional_rows:
        if len(row) != len(FUNCTIONAL_REQUIREMENTS_HEADER):
            continue
        prd_ids = _ids(row[0], "PRD")
        if len(prd_ids) != 1:
            _add(problems, "prd", f"invalid Functional Requirement ID {row[0]!r}")
            continue
        requirement_id = next(iter(prd_ids))
        if requirement_id in requirement_ids:
            _add(problems, "prd", f"duplicate requirement ID {requirement_id}")
        requirement_ids.add(requirement_id)
        if row[2].casefold() == "must":
            must_ids.add(requirement_id)
    applicable_nfr_ids: set[str] = set()
    for row in nfr_rows:
        if len(row) != len(NFR_HEADER) or row[0].casefold() == "n/a":
            continue
        prd_ids = _ids(row[0], "PRD")
        if len(prd_ids) != 1:
            _add(problems, "prd", f"invalid Non-Functional Requirement ID {row[0]!r}")
            continue
        requirement_id = next(iter(prd_ids))
        if requirement_id in requirement_ids:
            _add(problems, "prd", f"duplicate requirement ID {requirement_id}")
        requirement_ids.add(requirement_id)
        applicable_nfr_ids.add(requirement_id)
        declared_tests = _ids(row[5], "TEST")
        if not declared_tests:
            _add(problems, "prd", f"{requirement_id} names no TEST ID")
        for test_id in declared_tests - known_test_ids:
            _add(problems, "prd", f"{requirement_id} references unknown {test_id}")
    for requirement_id in sorted((must_ids | applicable_nfr_ids) - required_coverage):
        _add(
            problems,
            "prd",
            f"{requirement_id} has no required Test Obligations coverage",
        )

    metrics = _section(prd_text, "## Metrics")
    if metrics is not None:
        metric_rows = _find_table(metrics, METRICS_HEADER)
        if metric_rows is None:
            _add(problems, "prd", "Metrics must use the measurable seven-column contract")
        elif require_filled and not metric_rows:
            _add(problems, "prd", "Metrics must contain at least one measurable row")
        else:
            _validate_table_rows(
                metric_rows,
                len(METRICS_HEADER),
                label="Metrics",
                require_filled=require_filled,
                problems=problems,
            )

    assumptions = _section(prd_text, "## Assumptions")
    if assumptions is not None:
        assumption_rows = _find_table(assumptions, ASSUMPTIONS_HEADER)
        if assumption_rows is None:
            _add(problems, "prd", "Assumptions must use the owner/validation table")
        else:
            _validate_table_rows(
                assumption_rows,
                len(ASSUMPTIONS_HEADER),
                label="Assumptions",
                require_filled=require_filled,
                problems=problems,
            )

    open_questions = _section(prd_text, "## Open Questions")
    if open_questions is not None:
        rows = _find_table(open_questions, OPEN_QUESTIONS_HEADER)
        if rows is None:
            _add(problems, "prd", "Open Questions must use the decision-owner table")
        else:
            _validate_table_rows(
                rows,
                len(OPEN_QUESTIONS_HEADER),
                label="Open Questions",
                require_filled=require_filled,
                problems=problems,
            )
        if rows is not None and require_approved:
            for row in rows:
                if len(row) < len(OPEN_QUESTIONS_HEADER):
                    _add(problems, "prd", "Open Questions row is incomplete")
                    continue
                blocks = row[4].casefold()
                status = row[5].casefold()
                if blocks == "yes" and not status.startswith(
                    ("resolved", "closed", "n/a")
                ):
                    _add(
                        problems,
                        "prd",
                        f"blocking open question remains unresolved: {row[0]!r}",
                    )

    commercial = _section(prd_text, "## Monetization and Partner Channels")
    if commercial is not None:
        commercial_rows = _find_table(commercial, COMMERCIAL_DECISIONS_HEADER)
        if commercial_rows is None:
            _add(
                problems,
                "prd",
                "Monetization and Partner Channels must use the decision table",
            )
        else:
            _validate_table_rows(
                commercial_rows,
                len(COMMERCIAL_DECISIONS_HEADER),
                label="Monetization and Partner Channels",
                require_filled=require_filled,
                problems=problems,
            )
            rows_by_decision = {
                row[0].casefold(): row
                for row in commercial_rows
                if len(row) == len(COMMERCIAL_DECISIONS_HEADER)
            }
            for gate_name in (
                "monetization infrastructure gate",
                "partner channel gate",
            ):
                row = rows_by_decision.get(gate_name)
                if row is None:
                    _add(problems, "prd", f"missing {gate_name.title()} row")
                    continue
                selection = row[1].casefold()
                status = row[3].casefold()
                if selection not in {"required", "not_required", "blocked"}:
                    _add(
                        problems,
                        "prd",
                        f"{row[0]} has invalid selection {row[1]!r}",
                    )
                if require_approved and selection == "blocked":
                    _add(problems, "prd", f"{row[0]} is blocked")
                if require_approved and status not in {"selected", "approved"}:
                    _add(
                        problems,
                        "prd",
                        f"{row[0]} remains {row[3]!r}; owner approval is required",
                    )
                if selection == "required":
                    required_stack_areas.add("commercial")

    ui_bearing = (
        "<!-- ui-surface-contract:start -->" in prd_text
        or "<!-- ui-surface-contract:end -->" in prd_text
    )
    builder_ux = _section(prd_text, "## Builder UX Direction Decision")
    if ui_bearing and builder_ux is None:
        _add(problems, "prd", "UI-bearing package is missing Builder UX Direction Decision")
    if builder_ux is not None:
        motion_rows = _find_table(builder_ux, MOTION_GATE_HEADER)
        if motion_rows is None:
            _add(problems, "prd", "Builder UX Direction is missing the Motion Need Gate table")
        else:
            _validate_table_rows(
                motion_rows,
                len(MOTION_GATE_HEADER),
                label="Motion Need Gate",
                require_filled=require_filled,
                problems=problems,
            )
            if require_approved:
                for row in motion_rows:
                    if len(row) != len(MOTION_GATE_HEADER):
                        continue
                    motion_gate = row[1].casefold()
                    if motion_gate == "blocked":
                        _add(
                            problems,
                            "prd",
                            f"Motion Need Gate remains blocked for {row[0]!r}",
                        )
                    if motion_gate == "recommended" and not any(
                        marker in row[3].casefold() for marker in ("owner", "accepted")
                    ):
                        _add(
                            problems,
                            "prd",
                            f"recommended motion for {row[0]!r} lacks owner acceptance",
                        )
    for gate_label in ("Data and Trust Gate", "AI and Automation Gate"):
        gate_record = _gate_record(prd_text, gate_label)
        if gate_record is None:
            _add(
                problems,
                "prd",
                f"missing complete {gate_label} status, reason, or decision owner",
            )
            continue
        gate, reason, owner = gate_record
        if require_filled and (_placeholder_cell(reason) or _invalid_human_owner(owner)):
            _add(problems, "prd", f"{gate_label} has an unfilled reason or owner")
        if require_approved and gate == "blocked":
            _add(problems, "prd", f"{gate_label} is blocked")
        if gate_label == "AI and Automation Gate" and gate == "required":
            required_stack_areas.add("ai or automation")

    research_gate = _research_gate(prd_text)
    if research_gate is None:
        _add(problems, "prd", "missing Research Gate decision")
    else:
        research_status, research_detail = research_gate
        if require_approved and research_status in {"clarify", "stop"}:
            _add(
                problems,
                "prd",
                f"Research Gate is {research_status!r} and cannot be approved",
            )
        research_owner = re.search(
            r"\bdecided by\s+(.+?)\s*$", research_detail, re.IGNORECASE
        )
        if require_filled and (
            research_owner is None
            or _invalid_human_owner(research_owner.group(1))
        ):
            _add(problems, "prd", "Research Gate must name its human decision owner")
        if research_status == "skipped" and (
            not research_detail
            or (require_filled and "[" in research_detail and "]" in research_detail)
        ):
            _add(problems, "prd", "skipped Research Gate requires a reason")

    product_block = _extract_machine_block(
        prd_text,
        PRODUCT_APPROVAL_START,
        PRODUCT_APPROVAL_END,
        path="prd",
        label="product-definition approval",
        problems=problems,
    )
    if product_block is not None:
        for duplicate in _duplicate_bullet_fields(product_block):
            _add(problems, "prd approval", f"duplicate field {duplicate!r}")
        product_fields = _bullet_fields(product_block)
        _require_fields(
            product_fields,
            (
                "Package mode",
                "Package revision",
                "Decision",
                "Decision owner",
                "Decided on",
                "Approved artifacts",
                "Market research reconciliation",
                "Stack Decision Checkpoint",
                "Accepted assumptions and non-blocking questions",
                "Blocking items",
            ),
            path="prd approval",
            problems=problems,
            require_filled=require_filled,
        )
        decision = product_fields.get("decision", "").casefold()
        if decision and decision not in VALID_DECISIONS:
            _add(problems, "prd approval", f"invalid decision {decision!r}")
        if require_approved and decision != "approved":
            _add(problems, "prd approval", "Decision must be approved")
        owner = product_fields.get("decision owner", "")
        if require_filled and _invalid_human_owner(owner):
            _add(problems, "prd approval", "Decision owner must name a human owner")
        decided_on = product_fields.get("decided on", "")
        if decided_on and re.fullmatch(r"\d{4}-\d{2}-\d{2}", decided_on) is None:
            _add(problems, "prd approval", "Decided on must use YYYY-MM-DD")
        approved_artifacts = product_fields.get("approved artifacts", "").casefold()
        for filename in ("prd.md", "architecture.md", "stack-decisions.md"):
            if approved_artifacts and filename not in approved_artifacts:
                _add(problems, "prd approval", f"Approved artifacts must include {filename}")
        checkpoint = product_fields.get("stack decision checkpoint", "").casefold()
        if require_approved and checkpoint != "approved":
            _add(problems, "prd approval", "Stack Decision Checkpoint must be approved")
        reconciliation = product_fields.get(
            "market research reconciliation", ""
        ).casefold()
        if reconciliation and not reconciliation.startswith(("completed", "skipped", "blocked")):
            _add(problems, "prd approval", "invalid market research reconciliation")
        if require_approved and reconciliation.startswith("blocked"):
            _add(problems, "prd approval", "market research reconciliation is blocked")
        blockers = product_fields.get("blocking items", "").casefold()
        if require_approved and blockers and not blockers.startswith(("none", "n/a")):
            _add(problems, "prd approval", "Blocking items must be none")
        mode = product_fields.get("package mode", "").casefold()
        if mode and mode not in {"new", "enhancement"}:
            _add(problems, "prd approval", f"invalid Package mode {mode!r}")
        if mode == "enhancement" and not _has_heading(
            prd_text, "## Enhancement Impact Record"
        ):
            _add(
                problems,
                "prd",
                "enhancement package is missing Enhancement Impact Record",
            )
        elif mode == "enhancement":
            impact_section = _section(prd_text, "## Enhancement Impact Record")
            impact_rows = (
                _find_table(impact_section, ENHANCEMENT_IMPACT_HEADER)
                if impact_section is not None
                else None
            )
            if impact_rows is None:
                _add(problems, "prd", "Enhancement Impact Record has no impact table")
            else:
                _validate_table_rows(
                    impact_rows,
                    len(ENHANCEMENT_IMPACT_HEADER),
                    label="Enhancement Impact Record",
                    require_filled=require_filled,
                    problems=problems,
                )
                present = {
                    row[0].casefold()
                    for row in impact_rows
                    if len(row) == len(ENHANCEMENT_IMPACT_HEADER)
                }
                missing = sorted(REQUIRED_ENHANCEMENT_AREAS - present)
                if missing:
                    _add(
                        problems,
                        "prd",
                        "Enhancement Impact Record is missing areas: "
                        + ", ".join(missing),
                    )

    stack_block = _extract_machine_block(
        stack_text,
        STACK_CHECKPOINT_START,
        STACK_CHECKPOINT_END,
        path="stack-decisions",
        label="stack-decision checkpoint",
        problems=problems,
    )
    if stack_block is not None:
        for duplicate in _duplicate_bullet_fields(stack_block):
            _add(problems, "stack checkpoint", f"duplicate field {duplicate!r}")
        stack_fields = _bullet_fields(stack_block)
        _require_fields(
            stack_fields,
            (
                "Decision",
                "Decision owner",
                "Decided on",
                "Approved areas",
                "Delegated choices",
                "Open areas",
            ),
            path="stack checkpoint",
            problems=problems,
            require_filled=require_filled,
        )
        decision = stack_fields.get("decision", "").casefold()
        if decision and decision not in VALID_DECISIONS:
            _add(problems, "stack checkpoint", f"invalid decision {decision!r}")
        if require_approved and decision != "approved":
            _add(problems, "stack checkpoint", "Decision must be approved")
        owner = stack_fields.get("decision owner", "")
        if require_filled and _invalid_human_owner(owner):
            _add(problems, "stack checkpoint", "Decision owner must name a human owner")
        decided_on = stack_fields.get("decided on", "")
        if decided_on and re.fullmatch(r"\d{4}-\d{2}-\d{2}", decided_on) is None:
            _add(problems, "stack checkpoint", "Decided on must use YYYY-MM-DD")
        open_areas = stack_fields.get("open areas", "").casefold()
        if require_approved and open_areas and not open_areas.startswith(("none", "n/a")):
            _add(problems, "stack checkpoint", "Open areas must be none")
        required_stack_areas.update(
            _stack_areas(stack_fields.get("approved areas", ""))
        )

    approved_stack_areas = _validate_stack_tables(
        stack_text,
        require_filled=require_filled,
        require_approved=require_approved,
        required_areas=required_stack_areas,
        problems=problems,
    )
    option_rows = _find_table(stack_text, STACK_OPTIONS_HEADER)
    if approved_stack_areas and not option_rows:
        _add(
            problems,
            "stack-decisions",
            "Approved layers require a non-empty Coherent Options Presented table",
        )
    elif option_rows:
        _validate_table_rows(
            option_rows,
            len(STACK_OPTIONS_HEADER),
            label="Coherent Options Presented",
            require_filled=require_filled,
            problems=problems,
            path="stack-decisions",
        )
        seen_option_ids: set[str] = set()
        options_by_area: dict[str, list[tuple[str, ...]]] = {}
        for row in option_rows:
            if len(row) != len(STACK_OPTIONS_HEADER):
                continue
            option_ids = _ids(row[0], "OPT")
            if len(option_ids) != 1:
                _add(problems, "stack-decisions", f"invalid option ID {row[0]!r}")
            else:
                option_id = next(iter(option_ids))
                if option_id in seen_option_ids:
                    _add(
                        problems,
                        "stack-decisions",
                        f"duplicate option ID {option_id}",
                    )
                seen_option_ids.add(option_id)
            disposition = row[5].casefold()
            if disposition not in {"recommended", "approved", "rejected"}:
                _add(
                    problems,
                    "stack-decisions",
                    f"option {row[0]!r} has invalid disposition {row[5]!r}",
                )
            areas = _stack_areas(row[1])
            if not areas:
                _add(
                    problems,
                    "stack-decisions",
                    f"option {row[0]!r} has an unrecognized area {row[1]!r}",
                )
            for area in areas:
                options_by_area.setdefault(area, []).append(row)
        for area in sorted(approved_stack_areas):
            area_options = options_by_area.get(area, [])
            if not 2 <= len(area_options) <= 3:
                _add(
                    problems,
                    "stack-decisions",
                    f"approved {area} choices require two or three coherent options; "
                    f"found {len(area_options)}",
                )
            if not any(row[5].casefold() == "approved" for row in area_options):
                _add(
                    problems,
                    "stack-decisions",
                    f"Coherent Options Presented must retain the approved {area} option",
                )
    return problems


def validate(
    prd_path: Path,
    architecture_path: Path,
    stack_path: Path,
    *,
    require_filled: bool = False,
    require_approved: bool = False,
) -> list[str]:
    """Read and validate the three canonical core package files."""

    texts: list[str] = []
    for label, path in (
        ("prd", prd_path),
        ("architecture", architecture_path),
        ("stack-decisions", stack_path),
    ):
        try:
            texts.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            return [f"{label}: cannot read UTF-8 file {path}: {exc}"]
    return validate_texts(
        texts[0],
        texts[1],
        texts[2],
        require_filled=require_filled,
        require_approved=require_approved,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prd", required=True, type=Path)
    parser.add_argument("--architecture", required=True, type=Path)
    parser.add_argument("--stack-decisions", required=True, type=Path)
    parser.add_argument("--require-filled", action="store_true")
    parser.add_argument("--require-approved", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    problems = validate(
        args.prd,
        args.architecture,
        args.stack_decisions,
        require_filled=args.require_filled,
        require_approved=args.require_approved,
    )
    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        return 1
    print("PASS core Product Definition package is complete and owner-approved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

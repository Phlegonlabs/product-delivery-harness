#!/usr/bin/env python3
"""Validate the core Product Definition package and its owner approvals."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from markdown_contract import active_markdown_lines, active_text, active_machine_block
from prd_ui_contract import parse_prd_ui_contract
from release_targets import parse_release_targets


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
    "## UI Design Handoff Status",
    "## Product Definition Decisions",
)

REQUIRED_ARCHITECTURE_HEADINGS = (
    "## Architecture Summary",
    "## Product Archetype",
    "## System Context",
    "## Component Architecture",
    "## Frontend Architecture",
    "## Backend Architecture",
    "## Data Model",
    "## API and Interface Contracts",
    "## Workflow and Data Flow",
    "## Auth, Permissions, and Security",
    "## Data and Trust Architecture",
    "## AI and Automation Architecture",
    "## Integrations",
    "## Monetization and Partner Channel Architecture",
    "## Deployment and Operations",
    "## Release Targets",
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


FUNCTIONAL_REQUIREMENTS_HEADER = (
    "id",
    "requirement",
    "priority",
    "acceptance criteria",
)

RELEASE_TARGET_FIELDS = (
    "Surface",
    "Surface class",
    "Public discoverability",
    "Surface suffix",
    "Release name",
    "Provider",
    "Stage",
    "Source policy",
    "Artifact kind",
    "Signing requirement",
    "Exact channel / track",
    "Submission / promotion / review / manual approval path",
    "Availability signal",
    "Rollout",
    "Rollback / forward-fix",
)
SURFACE_CLASSES = {
    "hosted_web",
    "hosted_api",
    "browser_extension",
    "ios",
    "android",
    "macos",
    "windows",
    "worker",
    "job",
    "webhook",
    "realtime",
    "cli",
    "agent",
    "other_nonpublic",
}
PUBLIC_DISCOVERABILITY = {"yes", "no"}

RELEASE_TARGET_START = "### Release Target:"
EXPECTED_SURFACES_PREFIX = "Expected deployable surfaces:"

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

GATE_DECISION_HEADER = ("area", "decision", "owner / evidence", "test ids")
DATA_TRUST_AREAS = {
    "classification and ownership",
    "residency and vendor processing",
    "retention, deletion, and export",
    "consent and policy basis",
    "human and administrative access",
    "incident and residual risk",
}
AI_AUTOMATION_AREAS = {
    "capability and provider boundary",
    "input, context, and retention",
    "tool and side-effect permissions",
    "evaluation and prohibited outcomes",
    "cost, latency, and observability",
    "fallback, shutoff, and incident path",
    "injection and output validation",
}
GATE_AREA_TRACES = {
    "Data and Trust Gate": {
        "classification and ownership": "TRUST-CLASSIFICATION",
        "residency and vendor processing": "TRUST-RESIDENCY",
        "retention, deletion, and export": "TRUST-RETENTION",
        "consent and policy basis": "TRUST-CONSENT",
        "human and administrative access": "TRUST-ACCESS",
        "incident and residual risk": "TRUST-INCIDENT",
    },
    "AI and Automation Gate": {
        "capability and provider boundary": "AI-CAPABILITY",
        "input, context, and retention": "AI-CONTEXT",
        "tool and side-effect permissions": "AI-SIDE-EFFECTS",
        "evaluation and prohibited outcomes": "AI-EVALUATION",
        "cost, latency, and observability": "AI-OPERATIONS",
        "fallback, shutoff, and incident path": "AI-FALLBACK",
        "injection and output validation": "AI-VALIDATION",
    },
}
ARCHITECTURE_TABLE_HEADERS = {
    "## Component Architecture": (
        "arch id",
        "component",
        "responsibility",
        "upstream trace ids",
        "notes",
    ),
    "## Data Model": ("entity", "key fields", "relationships", "notes"),
    "## API and Interface Contracts": (
        "arch id",
        "interface",
        "method or trigger",
        "input",
        "output",
        "errors",
        "test ids",
    ),
    "## Integrations": (
        "system",
        "purpose",
        "data exchanged",
        "auth / scopes",
        "contract / limits",
        "failure / recovery",
        "owner",
    ),
    "## Technical Risks and Tradeoffs": (
        "decision",
        "options considered",
        "recommendation",
        "reason",
    ),
    "## Architecture Trace Index": (
        "arch id",
        "contract or decision",
        "upstream prd / ux ids",
        "downstream ui / test ids",
    ),
}
OPTIONAL_ARCHITECTURE_SECTIONS = {
    "## Frontend Architecture",
    "## Backend Architecture",
    "## Data Model",
    "## API and Interface Contracts",
    "## Data and Trust Architecture",
    "## AI and Automation Architecture",
    "## Integrations",
    "## Monetization and Partner Channel Architecture",
}
STACK_SELECTED_EVIDENCE_RE = re.compile(
    r"\brepository:(?P<path>(?!/)(?![A-Za-z]:)(?![^@]*\.\.)"
    r"[A-Za-z0-9._/-]+)@(?P<revision>[0-9a-f]{40}|sha256:[0-9a-f]{64})\b"
)
ENHANCEMENT_ARTIFACT_RE = re.compile(
    r"\b(?:PRD|architecture|stack-decisions|wireframes|ui-design|design-system|"
    r"DEPLOYMENT|ACTIVATION|OUTCOME_REVIEW|SEO_REVIEW)\.(?:md|json|html)\b",
    re.IGNORECASE,
)
ENHANCEMENT_REFRESH_REQUIREMENTS = {
    "product scope / behavior": (
        {"prd.md"},
        {"product definition approval"},
    ),
    "data / integrations": (
        {"prd.md", "architecture.md"},
        {"product definition approval"},
    ),
    "architecture / stack": (
        {"architecture.md", "stack-decisions.md"},
        {"stack decision checkpoint", "product definition approval"},
    ),
    "data trust / ai": (
        {"prd.md", "architecture.md", "stack-decisions.md"},
        {"product definition approval", "stack decision checkpoint"},
    ),
    "monetization / partner": (
        {"prd.md", "architecture.md", "stack-decisions.md"},
        {"product definition approval", "stack decision checkpoint"},
    ),
    "release / operations": (
        {"architecture.md", "deployment.md"},
        {"product definition approval", "deployment checker"},
    ),
}
AT_A_GLANCE_HEADER = ("", "")
AT_A_GLANCE_ROWS = {
    "what it is",
    "primary user",
    "why now",
    "success looks like",
    "biggest risk",
}
PERSONAS_HEADER = ("persona", "need", "key workflow", "success signal")
UX_REQUIREMENTS_HEADER = (
    "id",
    "user / task",
    "requirement",
    "success and failure signal",
    "evidence status",
)
RISKS_HEADER = ("risk", "impact", "mitigation")


def _add(problems: list[str], path: str, message: str) -> None:
    problems.append(f"{path}: {message}")


def _has_heading(text: str, heading: str) -> bool:
    return (
        re.search(
            rf"^{re.escape(heading)}\s*$",
            active_text(text),
            re.MULTILINE,
        )
        is not None
    )


def _is_kebab(value: str) -> bool:
    return re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) is not None


def _meaningful(value: str, *, minimum: int = 10) -> bool:
    stripped = value.strip()
    if len(stripped) < minimum or _placeholder_cell(stripped):
        return False
    lowered = stripped.casefold().strip(" .")
    return lowered not in {
        "n/a",
        "none",
        "same",
        "works",
        "yes",
        "done",
        "as described",
        "see above",
    }


def _real_date(value: str) -> bool:
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _contains_non_human_owner(value: str) -> bool:
    return bool(
        re.search(
            r"(?<!\w)(?:ai|agent|assistant|automation|automated|model|"
            r"bot|claude|codex|system|machine)(?!\w)",
            value.casefold(),
        )
    )


def _validate_heading_sequence(
    text: str, headings: tuple[str, ...], *, path: str, problems: list[str]
) -> None:
    text = active_text(text)
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
    block, error = active_machine_block(text, start, end)
    if error is not None:
        _add(problems, path, f"has {error} {label} marker content")
        return None
    if block is None:
        _add(
            problems,
            path,
            f"must contain exactly one active exact standalone {label} marker pair",
        )
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
        if require_filled and _placeholder_cell(value):
            _add(problems, path, f"field {name!r} contains an unfilled placeholder")


def _section(text: str, heading: str) -> str | None:
    text = active_text(text)
    match = re.search(
        rf"^{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def _subsection(text: str, heading: str) -> str | None:
    text = active_text(text)
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
    if not stripped:
        return False
    return bool(
        (stripped.startswith("[") and stripped.endswith("]"))
        or "<placeholder" in stripped.casefold()
        or re.search(r"<[^>\s]+>", stripped)
        or re.search(r"\b(?:tbd|tbc|todo|placeholder)\b", stripped, re.IGNORECASE)
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
    lines = active_text(text).splitlines()
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


def _explicit_absence_reason(value: str) -> str | None:
    match = re.fullmatch(
        r"\s*(?:not_required|n/a|none)\s*(?:—|-)\s*(.+?)\s*",
        value,
        re.IGNORECASE | re.DOTALL,
    )
    return match.group(1).strip() if match else None


def _validate_architecture_sections(
    architecture_text: str, *, problems: list[str]
) -> None:
    for heading in REQUIRED_ARCHITECTURE_HEADINGS:
        if heading == "## Release Targets":
            continue
        section = _section(architecture_text, heading)
        if section is None:
            continue
        reason = _explicit_absence_reason(section)
        if reason is not None:
            if heading not in OPTIONAL_ARCHITECTURE_SECTIONS:
                _add(
                    problems,
                    "architecture",
                    f"{heading} is mandatory and cannot be not_required",
                )
            elif not _meaningful(reason, minimum=15):
                _add(
                    problems,
                    "architecture",
                    f"{heading} not_required reason is not concrete",
                )
            continue
        expected_header = ARCHITECTURE_TABLE_HEADERS.get(heading)
        if expected_header is not None:
            rows = _find_table(section, expected_header)
            if rows is None or not rows:
                _add(
                    problems,
                    "architecture",
                    f"{heading} requires a populated canonical table or an explicit "
                    "not_required reason",
                )
                continue
            _validate_table_rows(
                rows,
                len(expected_header),
                label=heading.removeprefix("## "),
                require_filled=True,
                problems=problems,
                path="architecture",
            )
            continue
        if not _meaningful(section, minimum=25):
            _add(
                problems,
                "architecture",
                f"{heading} requires substantive implementation content or an "
                "explicit not_required reason",
            )


def _validate_prd_core_sections(
    prd_text: str,
    *,
    has_ui: bool,
    problems: list[str],
) -> None:
    at_a_glance = _section(prd_text, "## At a Glance")
    glance_rows = _find_table(at_a_glance or "", AT_A_GLANCE_HEADER)
    if glance_rows is None:
        _add(problems, "prd", "At a Glance must use the canonical two-column table")
    else:
        _validate_table_rows(
            glance_rows,
            2,
            label="At a Glance",
            require_filled=True,
            problems=problems,
        )
        label_values = [row[0].casefold() for row in glance_rows if len(row) == 2]
        labels = set(label_values)
        if (
            len(glance_rows) != len(AT_A_GLANCE_ROWS)
            or len(label_values) != len(set(label_values))
            or labels != AT_A_GLANCE_ROWS
        ):
            _add(problems, "prd", "At a Glance must use exactly its five canonical rows")
        for row in glance_rows:
            if len(row) == 2 and not _meaningful(row[1], minimum=8):
                _add(problems, "prd", f"At a Glance row {row[0]!r} is not meaningful")

    for heading, minimum in (
        ("## Problem Statement", 20),
        ("## Data and Integration Requirements", 15),
        ("## Business Rules", 15),
    ):
        section = _section(prd_text, heading)
        reason = _explicit_absence_reason(section or "")
        if not _meaningful(section or "", minimum=minimum) and not (
            reason is not None and _meaningful(reason, minimum=12)
        ):
            _add(problems, "prd", f"{heading} requires substantive product content")

    for heading in ("## Goals", "## Non-Goals"):
        section = _section(prd_text, heading) or ""
        bullets = re.findall(r"^\s*-\s+(.+?)\s*$", section, re.MULTILINE)
        if not bullets or any(not _meaningful(item, minimum=6) for item in bullets):
            _add(problems, "prd", f"{heading} requires at least one meaningful bullet")

    personas = _section(prd_text, "## Users and Personas") or ""
    persona_rows = _find_table(personas, PERSONAS_HEADER)
    if persona_rows is None or not persona_rows:
        _add(problems, "prd", "Users and Personas requires a populated canonical table")
    else:
        _validate_table_rows(
            persona_rows,
            len(PERSONAS_HEADER),
            label="Users and Personas",
            require_filled=True,
            problems=problems,
        )

    journeys = _section(prd_text, "## User Journeys") or ""
    if re.search(r"^###\s+Journey\s+\d+:", journeys, re.MULTILINE) is None or len(
        re.findall(r"^\s*\d+\.\s+\S", journeys, re.MULTILINE)
    ) < 2:
        _add(problems, "prd", "User Journeys requires a named journey with at least two steps")

    ux = _section(prd_text, "## UX Requirements") or ""
    ux_rows = _find_table(ux, UX_REQUIREMENTS_HEADER)
    ux_absence = _explicit_absence_reason(ux)
    if has_ui:
        if ux_rows is None or not ux_rows:
            _add(problems, "prd", "UI-bearing products require populated UX Requirements")
        else:
            _validate_table_rows(
                ux_rows,
                len(UX_REQUIREMENTS_HEADER),
                label="UX Requirements",
                require_filled=True,
                problems=problems,
            )
    elif not (ux_absence is not None and _meaningful(ux_absence, minimum=12)):
        _add(problems, "prd", "headless UX Requirements needs not_required with a reason")

    risks = _section(prd_text, "## Risks") or ""
    risk_rows = _find_table(risks, RISKS_HEADER)
    if risk_rows is None or not risk_rows:
        _add(problems, "prd", "Risks requires a populated canonical table")
    else:
        _validate_table_rows(
            risk_rows,
            len(RISKS_HEADER),
            label="Risks",
            require_filled=True,
            problems=problems,
        )


def _validate_gate_decisions(
    section: str,
    *,
    label: str,
    expected_areas: set[str],
    known_required_tests: set[str],
    required_test_upstreams: dict[str, set[str]],
    problems: list[str],
) -> None:
    rows = _find_table(section, GATE_DECISION_HEADER)
    if rows is None:
        _add(problems, "prd", f"required {label} must use its canonical decision table")
        return
    _validate_table_rows(
        rows,
        len(GATE_DECISION_HEADER),
        label=label,
        require_filled=True,
        problems=problems,
    )
    seen: set[str] = set()
    for row in rows:
        if len(row) != len(GATE_DECISION_HEADER):
            continue
        area = row[0].casefold()
        if area in seen:
            _add(problems, "prd", f"{label} has duplicate area {row[0]!r}")
        seen.add(area)
        if not _meaningful(row[1], minimum=12):
            _add(problems, "prd", f"{label} area {row[0]!r} needs a concrete decision")
        if not _meaningful(row[2], minimum=4) or _contains_non_human_owner(row[2]):
            _add(
                problems,
                "prd",
                f"{label} area {row[0]!r} needs human-owned evidence",
            )
        test_ids = _ids(row[3], "TEST")
        if not test_ids:
            _add(problems, "prd", f"{label} area {row[0]!r} names no TEST ID")
        for test_id in sorted(test_ids - known_required_tests):
            _add(
                problems,
                "prd",
                f"{label} area {row[0]!r} references non-required or unknown {test_id}",
            )
        expected_trace = GATE_AREA_TRACES[label].get(area)
        if expected_trace is not None and not any(
            expected_trace in required_test_upstreams.get(test_id, set())
            for test_id in test_ids
        ):
            _add(
                problems,
                "prd",
                f"{label} area {row[0]!r} requires a Required Yes test whose "
                f"upstream traces include {expected_trace}",
            )
    missing = sorted(expected_areas - seen)
    extra = sorted(seen - expected_areas)
    if missing or extra:
        _add(
            problems,
            "prd",
            f"required {label} must use exactly its canonical areas; missing: "
            + (", ".join(missing) or "none")
            + "; extra: "
            + (", ".join(extra) or "none"),
        )


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
        or _contains_non_human_owner(value)
    )


def _hash_path(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    for candidate in sorted(item for item in path.rglob("*") if item.is_file()):
        relative = candidate.relative_to(path).as_posix().encode("utf-8")
        content = candidate.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _verify_selected_evidence(
    evidence: str,
    *,
    repo_root: Path | None,
    label: str,
    problems: list[str],
) -> None:
    match = STACK_SELECTED_EVIDENCE_RE.search(evidence)
    if match is None:
        _add(
            problems,
            "stack-decisions",
            f"Selected layer {label!r} must cite "
            "repository:<path>@<40-sha or sha256:64> evidence",
        )
        return
    if repo_root is None:
        _add(
            problems,
            "stack-decisions",
            f"Selected layer {label!r} repository evidence cannot be verified "
            "without repo_root",
        )
        return
    root = repo_root.resolve()
    relative = match.group("path")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        _add(problems, "stack-decisions", f"Selected layer {label!r} path escapes repo_root")
        return
    if not candidate.exists():
        _add(
            problems,
            "stack-decisions",
            f"Selected layer {label!r} repository path does not exist: {relative}",
        )
        return
    revision = match.group("revision")
    if revision.startswith("sha256:"):
        expected = revision.removeprefix("sha256:")
        actual = _hash_path(candidate)
        if actual != expected:
            _add(
                problems,
                "stack-decisions",
                f"Selected layer {label!r} repository sha256 does not match {relative}",
            )
        return
    try:
        commit = subprocess.run(
            ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
            cwd=root,
            capture_output=True,
            timeout=10,
        )
        blob = subprocess.run(
            ["git", "cat-file", "-e", f"{revision}:{relative}"],
            cwd=root,
            capture_output=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _add(
            problems,
            "stack-decisions",
            f"Selected layer {label!r} repository revision cannot be verified: {exc}",
        )
        return
    if commit.returncode != 0 or blob.returncode != 0:
        _add(
            problems,
            "stack-decisions",
            f"Selected layer {label!r} repository revision/path is not real: "
            f"{revision}:{relative}",
        )


def _validate_stack_tables(
    stack_text: str,
    *,
    require_filled: bool,
    require_approved: bool,
    required_areas: set[str],
    repo_root: Path | None,
    problems: list[str],
) -> set[str]:
    approved_areas: set[str] = set()
    present_areas: set[str] = set()
    active_stack = active_text(stack_text)
    for section_name, required_layers in STACK_SECTION_LAYERS.items():
        heading = f"## {section_name}"
        heading_count = len(
            re.findall(rf"^{re.escape(heading)}\s*$", active_stack, re.MULTILINE)
        )
        if heading_count > 1:
            _add(
                problems,
                "stack-decisions",
                f"duplicate technology decision section {section_name!r}",
            )
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
            if status == "selected":
                _verify_selected_evidence(
                    cells[3],
                    repo_root=repo_root,
                    label=cells[0],
                    problems=problems,
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
    text = active_text(text)
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
    text = active_text(text)
    match = re.search(
        r"^Research Gate:\s*(go|clarify|stop|skipped)\b(.*?)$",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if match is None:
        return None
    return match.group(1).casefold(), match.group(2).strip()


def _validate_release_targets_legacy(
    architecture_text: str, *, problems: list[str]
) -> None:
    active = active_markdown_lines(architecture_text)
    inventory_lines = [
        line
        for _, line in active
        if line.strip().startswith(EXPECTED_SURFACES_PREFIX)
    ]
    if len(inventory_lines) != 1:
        problems.append(
            "architecture: Release Targets must contain exactly one "
            "expected deployable-surface inventory"
        )
        return

    inventory = inventory_lines[0][len(EXPECTED_SURFACES_PREFIX) :].strip()
    explicit_none = re.match(r"^none\s*(?:—|-)\s*(.+)$", inventory, re.I)
    expected: set[str] = set()
    if explicit_none is not None:
        if not _meaningful(explicit_none.group(1), minimum=15):
            problems.append(
                "architecture: explicit none deployable-surface inventory "
                "requires a concrete reason"
            )
    else:
        expected = {
            value.strip()
            for value in inventory.split(",")
            if value.strip()
        }
        if not expected:
            problems.append("architecture: expected surface inventory is empty")
        invalid_surfaces = sorted(
            surface for surface in expected if not _is_kebab(surface)
        )
        if invalid_surfaces:
            problems.append(
                "architecture: expected surfaces use lowercase kebab-case IDs: "
                + ", ".join(invalid_surfaces)
            )

    starts = [
        index
        for index, (_, line) in enumerate(active)
        if line.strip().startswith(RELEASE_TARGET_START)
    ]
    targets: list[tuple[str, str, dict[str, str]]] = []
    seen_target_ids: set[str] = set()
    for target_index, start in enumerate(starts):
        _, start_line = active[start]
        target_id = start_line.split(":", 1)[1].strip()
        if not _is_kebab(target_id):
            problems.append(
                f"architecture: invalid release-target ID {target_id!r}"
            )
        if target_id in seen_target_ids:
            problems.append(
                f"architecture: duplicate release-target ID {target_id!r}"
            )
        seen_target_ids.add(target_id)
        end = (
            starts[target_index + 1]
            if target_index + 1 < len(starts)
            else len(active)
        )
        fields: dict[str, str] = {}
        field_keys: list[str] = []
        for _, line in active[start + 1 : end]:
            match = re.match(r"^\s*-\s*([^:\n]+):\s*(.*?)\s*$", line)
            if match:
                key = match.group(1).strip().casefold()
                fields[key] = match.group(2).strip()
                field_keys.append(key)
        duplicates = sorted(
            key for key, count in Counter(field_keys).items() if count > 1
        )
        if duplicates:
            problems.append(
                f"architecture: release target {target_id!r} has duplicate fields: "
                + ", ".join(duplicates)
            )
        missing_fields = [
            field
            for field in RELEASE_TARGET_FIELDS
            if field.casefold() not in fields
        ]
        if missing_fields:
            problems.append(
                f"architecture: release target {target_id!r} is missing fields: "
                + ", ".join(missing_fields)
            )
            continue
        if any(not fields[field.casefold()] for field in RELEASE_TARGET_FIELDS):
            problems.append(
                f"architecture: release target {target_id!r} has an empty field"
            )
            continue
        invalid_values = [
            field
            for field in RELEASE_TARGET_FIELDS
            if field not in {"Stage", "Surface class", "Public discoverability"}
            and not _meaningful(fields[field.casefold()])
        ]
        if invalid_values:
            problems.append(
                f"architecture: release target {target_id!r} has meaningless "
                "fields: " + ", ".join(invalid_values)
            )

        surface = fields["surface"]
        surface_class = fields["surface class"].casefold()
        discoverability = fields["public discoverability"].casefold()
        suffix = fields["surface suffix"]
        release_name = fields["release name"]
        stage = fields["stage"].casefold()
        if surface not in expected and explicit_none is None:
            problems.append(
                f"architecture: release target {target_id!r} names unexpected "
                f"surface {surface!r}"
            )
        if surface_class not in SURFACE_CLASSES:
            problems.append(
                f"architecture: release target {target_id!r} has invalid Surface class {fields['surface class']!r}"
            )
        if discoverability not in PUBLIC_DISCOVERABILITY:
            problems.append(
                f"architecture: release target {target_id!r} has invalid Public discoverability {fields['public discoverability']!r}"
            )
        if discoverability == "yes" and surface_class != "hosted_web":
            problems.append(
                f"architecture: release target {target_id!r} Public discoverability=yes requires Surface class hosted_web"
            )
        if explicit_none is not None:
            problems.append(
                f"architecture: none deployable-surface inventory has target "
                f"{target_id!r}"
            )
        if not _is_kebab(suffix):
            problems.append(
                f"architecture: release target {target_id!r} surface suffix "
                f"{suffix!r} is not lowercase kebab-case"
            )
        if not _is_kebab(release_name):
            problems.append(
                f"architecture: release target {target_id!r} release name "
                f"{release_name!r} is not lowercase kebab-case"
            )
        if stage not in {"development", "production"}:
            problems.append(
                f"architecture: release target {target_id!r} has invalid stage "
                f"{fields['stage']!r}"
            )
        availability = fields["availability signal"].casefold()
        if "smoke" not in availability:
            problems.append(
                f"architecture: release target {target_id!r} availability must "
                "name its smoke or acceptance check"
            )
        targets.append((target_id, stage, fields))

    if expected and not targets:
        problems.append(
            "architecture: every expected deployable surface requires release targets"
        )
        return

    release_name_owners: dict[str, str] = {}
    by_surface_stage: dict[tuple[str, str], tuple[str, dict[str, str]]] = {}
    for target_id, stage, fields in targets:
        surface = fields["surface"]
        pair = (surface, stage)
        if pair in by_surface_stage:
            problems.append(
                f"architecture: surface {surface!r} has duplicate {stage} targets"
            )
        by_surface_stage[pair] = (target_id, fields)
        release_name = fields["release name"]
        owner = release_name_owners.setdefault(release_name, surface)
        if owner != surface:
            problems.append(
                f"architecture: release name {release_name!r} is reused by "
                f"{surface!r} and {owner!r}"
            )

    for surface in sorted(expected):
        missing_stages = [
            stage
            for stage in ("development", "production")
            if (surface, stage) not in by_surface_stage
        ]
        if missing_stages:
            problems.append(
                f"architecture: expected surface {surface!r} is missing "
                + " and ".join(missing_stages)
                + " release targets"
            )

    for surface in sorted(set(fields["surface"] for _, _, fields in targets)):
        development = by_surface_stage.get((surface, "development"))
        production = by_surface_stage.get((surface, "production"))
        if development is None or production is None:
            continue
        development_name = development[1]["release name"]
        production_name = production[1]["release name"]
        suffix = production[1]["surface suffix"]
        if development[1]["surface class"].casefold() != production[1]["surface class"].casefold():
            problems.append(
                f"architecture: surface {surface!r} development and production targets must use the same Surface class"
            )
        if development[1]["public discoverability"].casefold() != production[1]["public discoverability"].casefold():
            problems.append(
                f"architecture: surface {surface!r} development and production targets must use the same Public discoverability value"
            )
        canonical = production_name.removesuffix("-prod")
        if production_name.endswith("-prod"):
            problems.append(
                f"architecture: production release {production_name!r} must not "
                "end in -prod"
            )
        if not canonical.endswith(f"-{suffix}") or (
            development_name != f"{canonical}-dev"
        ):
            problems.append(
                f"architecture: surface {surface!r} release names are not a "
                f"canonical {suffix!r} development/production pair"
            )


def _validate_release_targets(
    architecture_text: str, *, problems: list[str]
) -> None:
    _, findings = parse_release_targets(architecture_text)
    problems.extend(findings)


def _ids(cell: str, prefix: str) -> set[str]:
    return {
        match.group(0).upper()
        for match in re.finditer(rf"\b{re.escape(prefix)}-[A-Z0-9-]+\b", cell, re.I)
    }


def _architecture_ids(architecture_text: str) -> set[str]:
    ids: set[str] = set()
    for heading, header in (
        ("## Component Architecture", ARCHITECTURE_TABLE_HEADERS["## Component Architecture"]),
        ("## API and Interface Contracts", ARCHITECTURE_TABLE_HEADERS["## API and Interface Contracts"]),
        ("## Architecture Trace Index", ARCHITECTURE_TABLE_HEADERS["## Architecture Trace Index"]),
    ):
        section = _section(architecture_text, heading)
        rows = _find_table(section or "", header)
        for row in rows or []:
            if row:
                ids.update(_ids(row[0], "ARCH"))
    return ids


def validate_texts(
    prd_text: str,
    architecture_text: str,
    stack_text: str,
    *,
    require_filled: bool = False,
    require_approved: bool = False,
    repo_root: Path | None = None,
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
    if not re.search(r"^#\s+PRD(?::|\s*$)", active_text(prd_text), re.MULTILINE):
        _add(problems, "prd", "missing PRD title")
    if not re.search(
        r"^#\s+Architecture(?::|\s*$)", active_text(architecture_text), re.MULTILINE
    ):
        _add(problems, "architecture", "missing Architecture title")
    if not re.search(
        r"^#\s+Stack Decisions(?::|\s*$)", active_text(stack_text), re.MULTILINE
    ):
        _add(problems, "stack-decisions", "missing Stack Decisions title")

    ui_surfaces, ui_contract_errors = parse_prd_ui_contract(
        prd_text,
        require_responsive=True,
        require_copy=True,
        require_complete=True,
        web_floor=3,
    )
    problems.extend(ui_contract_errors)
    if require_filled:
        _validate_prd_core_sections(
            prd_text, has_ui=bool(ui_surfaces), problems=problems
        )
    required_stack_areas: set[str] = set()
    for surface in ui_surfaces.values():
        if surface.get("responsiveKind") == "viewports":
            required_stack_areas.add("frontend")
        elif surface.get("responsiveKind") == "sizeClasses":
            required_stack_areas.add("mobile or desktop")

    _validate_release_targets(
        architecture_text,
        problems=problems,
    )
    release_contract, _release_findings = parse_release_targets(architecture_text)
    capture_mode_by_class = {
        "hosted_web": "hosted-browser",
        "browser_extension": "browser-extension",
        "ios": "native",
        "android": "native",
        "macos": "desktop",
        "windows": "desktop",
    }
    for surface_id, surface in ui_surfaces.items():
        binding_fields = ("releaseSurface", "surfaceClass", "captureMode")
        if require_filled:
            for field in binding_fields:
                if not surface.get(field):
                    _add(
                        problems,
                        f"prd.{surface_id}.{field}",
                        "is required for an implementation-ready UI surface",
                    )
        release_surface = surface.get("releaseSurface")
        surface_class = surface.get("surfaceClass")
        capture_mode = surface.get("captureMode")
        if not release_surface:
            continue
        matching_targets = [
            target
            for target in release_contract.targets
            if target.surface == release_surface
        ]
        if not matching_targets:
            _add(
                problems,
                f"prd.{surface_id}.releaseSurface",
                "does not resolve to an architecture Release Target surface",
            )
            continue
        release_classes = {target.surface_class for target in matching_targets}
        if len(release_classes) != 1 or surface_class not in release_classes:
            _add(
                problems,
                f"prd.{surface_id}.surfaceClass",
                "must equal the architecture Release Target surface class",
            )
            continue
        expected_capture = capture_mode_by_class.get(surface_class)
        if expected_capture is None:
            _add(
                problems,
                f"prd.{surface_id}.surfaceClass",
                "does not identify a supported shipped UI capture class",
            )
        elif capture_mode != expected_capture:
            _add(
                problems,
                f"prd.{surface_id}.captureMode",
                f"must be {expected_capture!r} for surfaceClass {surface_class!r}",
            )
    if require_filled:
        _validate_architecture_sections(architecture_text, problems=problems)

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
        if require_filled and not functional_rows:
            _add(
                problems,
                "prd",
                "Functional Requirements must contain at least one requirement",
            )
            _add(
                problems,
                "prd",
                "Functional Requirements has no meaningful requirement and "
                "acceptance criteria",
            )
        for row in functional_rows:
            if len(row) != len(FUNCTIONAL_REQUIREMENTS_HEADER):
                continue
            if not _meaningful(row[1]) or not _meaningful(row[3], minimum=15):
                _add(
                    problems,
                    "prd",
                    f"{row[0]} needs a meaningful requirement and observable "
                    "acceptance criteria",
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
    if require_filled and not nfr_rows:
        _add(
            problems,
            "prd",
            "Non-Functional Requirements must contain at least one measurable "
            "row or a reasoned N/A row",
        )
    if require_filled and not test_rows:
        _add(problems, "prd", "Test Obligations must contain at least one test")

    required_coverage: set[str] = set()
    known_test_ids: set[str] = set()
    known_required_test_ids: set[str] = set()
    required_test_upstreams: dict[str, set[str]] = {}
    for row in test_rows:
        if len(row) != len(TEST_OBLIGATIONS_HEADER):
            continue
        test_ids = _ids(row[0], "TEST")
        if len(test_ids) != 1 or not re.fullmatch(
            r"TEST-[A-Z0-9-]+", row[0], re.IGNORECASE
        ):
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
            known_required_test_ids.add(test_id)
            required_test_upstreams[test_id] = {
                match.group(0).upper()
                for match in re.finditer(
                    r"\b(?:PRD|TRUST|AI)-[A-Z0-9-]+\b", row[4], re.IGNORECASE
                )
            }
            upstream = _ids(row[4], "PRD")
            if not upstream:
                _add(problems, "prd", f"{test_id} names no upstream PRD ID")
            required_coverage.update(upstream)
        if not _meaningful(row[1], minimum=8):
            _add(problems, "prd", f"{test_id} needs a concrete test obligation")
        if not _meaningful(row[2], minimum=3):
            _add(problems, "prd", f"{test_id} needs a concrete test type")
        if not _meaningful(row[5], minimum=8):
            _add(problems, "prd", f"{test_id} needs an observable expected signal")

    requirement_ids: set[str] = set()
    must_ids: set[str] = set()
    for row in functional_rows:
        if len(row) != len(FUNCTIONAL_REQUIREMENTS_HEADER):
            continue
        prd_ids = _ids(row[0], "PRD")
        if len(prd_ids) != 1 or not re.fullmatch(
            r"PRD-[A-Z0-9-]+", row[0], re.IGNORECASE
        ):
            _add(problems, "prd", f"invalid Functional Requirement ID {row[0]!r}")
            continue
        requirement_id = next(iter(prd_ids))
        if requirement_id in requirement_ids:
            _add(problems, "prd", f"duplicate requirement ID {requirement_id}")
        requirement_ids.add(requirement_id)
        priority = row[2].casefold()
        if priority not in {"must", "should", "could"}:
            _add(
                problems,
                "prd",
                f"{requirement_id} Priority must be Must, Should, or Could",
            )
        if priority == "must":
            must_ids.add(requirement_id)
    if require_filled and not must_ids:
        _add(problems, "prd", "Functional Requirements must include at least one Must")
    applicable_nfr_ids: set[str] = set()
    for row in nfr_rows:
        if len(row) != len(NFR_HEADER):
            continue
        if row[0].casefold() == "n/a":
            if not _meaningful(" ".join(row[1:]), minimum=20):
                _add(problems, "prd", "N/A NFR row needs a concrete applicability reason")
            continue
        prd_ids = _ids(row[0], "PRD")
        if len(prd_ids) != 1 or not re.fullmatch(
            r"PRD-[A-Z0-9-]+", row[0], re.IGNORECASE
        ):
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
        if any(
            not _meaningful(value, minimum=minimum)
            for value, minimum in zip(row[1:5], (4, 8, 4, 2))
        ):
            _add(
                problems,
                "prd",
                f"{requirement_id} must define a measurable quality requirement",
            )
    for row in test_rows:
        if len(row) != len(TEST_OBLIGATIONS_HEADER):
            continue
        for unknown in sorted(_ids(row[4], "PRD") - requirement_ids):
            _add(problems, "prd", f"{row[0]} references unknown upstream {unknown}")
    for requirement_id in sorted((must_ids | applicable_nfr_ids) - required_coverage):
        _add(
            problems,
            "prd",
            f"{requirement_id} has no required Test Obligations coverage",
        )
    if require_filled and not any(
        len(row) == len(TEST_OBLIGATIONS_HEADER) and row[3].casefold() == "yes"
        for row in test_rows
    ):
        _add(problems, "prd", "Test Obligations must include at least one Required Yes test")

    ux_section = _section(prd_text, "## UX Requirements") or ""
    ux_rows = _find_table(ux_section, UX_REQUIREMENTS_HEADER) or []
    ux_ids = {
        next(iter(found))
        for row in ux_rows
        if row
        for found in [_ids(row[0], "UX")]
        if len(found) == 1
    }
    architecture_ids = _architecture_ids(architecture_text)
    trace_authorities = {
        "PRD": requirement_ids,
        "UX": ux_ids,
        "ARCH": architecture_ids,
        "TEST": known_test_ids,
    }
    for surface_id, surface in ui_surfaces.items():
        fields = surface.get("contractFields")
        trace_value = fields.get("Trace IDs", "") if isinstance(fields, dict) else ""
        for prefix, known_ids in trace_authorities.items():
            for unknown in sorted(_ids(trace_value, prefix) - known_ids):
                _add(
                    problems,
                    "prd",
                    f"UI surface {surface_id} Trace IDs reference unknown {unknown}",
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
            seen_metrics: set[str] = set()
            for row in metric_rows:
                if len(row) != len(METRICS_HEADER):
                    continue
                metric = row[0].casefold()
                if metric in seen_metrics:
                    _add(problems, "prd", f"duplicate metric {row[0]!r}")
                seen_metrics.add(metric)
                if _invalid_human_owner(row[6]):
                    _add(problems, "prd", f"metric {row[0]!r} must name a human owner")
                if not _meaningful(row[1], minimum=8) or not _meaningful(
                    row[5], minimum=4
                ):
                    _add(
                        problems,
                        "prd",
                        f"metric {row[0]!r} needs a concrete definition and source",
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
            for row in assumption_rows:
                if len(row) != len(ASSUMPTIONS_HEADER):
                    continue
                if row[4] and not _real_date(row[4]):
                    _add(
                        problems,
                        "prd",
                        f"assumption {row[0]!r} decision date must be a real date",
                    )
                if _invalid_human_owner(row[3]):
                    _add(
                        problems,
                        "prd",
                        f"assumption {row[0]!r} must name a human owner",
                    )
                if row[5].casefold() not in {"open", "accepted", "validated", "rejected"}:
                    _add(
                        problems,
                        "prd",
                        f"assumption {row[0]!r} has invalid status {row[5]!r}",
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
            for row in rows:
                if len(row) != len(OPEN_QUESTIONS_HEADER):
                    continue
                if row[3] and not _real_date(row[3]):
                    _add(
                        problems,
                        "prd",
                        f"open question {row[0]!r} deadline must be a real date",
                    )
                if _invalid_human_owner(row[2]):
                    _add(
                        problems,
                        "prd",
                        f"open question {row[0]!r} must name a human owner",
                    )
                blocks = row[4].casefold()
                if blocks not in {"yes", "no"}:
                    _add(
                        problems,
                        "prd",
                        f"open question {row[0]!r} Blocks approval must be Yes or No",
                    )
                status = row[5].strip()
                closed_match = re.fullmatch(
                    r"(?:resolved|closed|n/a)\s*(?:—|-)\s*(.+)",
                    status,
                    re.IGNORECASE,
                )
                if status.casefold() != "open" and (
                    closed_match is None
                    or not _meaningful(closed_match.group(1), minimum=6)
                ):
                    _add(
                        problems,
                        "prd",
                        f"open question {row[0]!r} has invalid status/resolution",
                    )
        if rows is not None and require_approved:
            for row in rows:
                if len(row) < len(OPEN_QUESTIONS_HEADER):
                    _add(problems, "prd", "Open Questions row is incomplete")
                    continue
                blocks = row[4].casefold()
                status = row[5].casefold()
                closed = bool(
                    re.fullmatch(
                        r"(?:resolved|closed|n/a)\s*(?:—|-)\s*.+",
                        status,
                        re.IGNORECASE,
                    )
                )
                if blocks == "yes" and not closed:
                    _add(
                        problems,
                        "prd",
                        f"blocking open question remains unresolved: {row[0]!r}",
                    )

    rows_by_decision: dict[str, tuple[str, ...]] = {}
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
            seen_decisions: set[str] = set()
            rows_by_decision: dict[str, tuple[str, ...]] = {}
            for row in commercial_rows:
                if len(row) != len(COMMERCIAL_DECISIONS_HEADER):
                    continue
                decision = row[0].casefold()
                if decision in seen_decisions:
                    _add(
                        problems,
                        "prd",
                        f"duplicate commercial decision row {row[0]!r}",
                    )
                seen_decisions.add(decision)
                rows_by_decision[decision] = row
                status = row[3].casefold()
                if status not in {
                    "selected",
                    "approved",
                    "recommended",
                    "provisional",
                    "assumed",
                }:
                    _add(problems, "prd", f"{row[0]} has invalid status {row[3]!r}")
                if require_approved and status not in {"selected", "approved"}:
                    _add(
                        problems,
                        "prd",
                        f"{row[0]} remains {row[3]!r}; owner approval is required",
                    )
            if require_filled and not commercial_rows:
                _add(problems, "prd", "Monetization and Partner Channels must contain rows")
            required_commercial_rows = {
                "monetization model",
                "monetization infrastructure gate",
                "pricing and offer",
                "purchase and entitlement",
                "merchant of record / tax owner",
                "partner channel gate",
                "partner motion",
                "partner economics and operations",
            }
            if seen_decisions != required_commercial_rows:
                missing_commercial = sorted(required_commercial_rows - seen_decisions)
                extra_commercial = sorted(seen_decisions - required_commercial_rows)
                _add(
                    problems,
                    "prd",
                    "Monetization and Partner Channels must use exactly the canonical "
                    "decision rows; missing: "
                    + (", ".join(missing_commercial) or "none")
                    + "; extra: "
                    + (", ".join(extra_commercial) or "none"),
                )
            for gate_name in (
                "monetization infrastructure gate",
                "partner channel gate",
            ):
                row = rows_by_decision.get(gate_name)
                if row is None:
                    _add(problems, "prd", f"missing {gate_name.title()} row")
                    continue
                selection = row[1].casefold()
                if selection not in {"required", "not_required", "blocked"}:
                    _add(
                        problems,
                        "prd",
                        f"{row[0]} has invalid selection {row[1]!r}",
                    )
                if require_approved and selection == "blocked":
                    _add(problems, "prd", f"{row[0]} is blocked")
                if selection == "required":
                    required_stack_areas.add("commercial")

            monetization_required = (
                rows_by_decision.get("monetization infrastructure gate", ("", ""))[1]
                .casefold()
                == "required"
            )
            partner_required = (
                rows_by_decision.get("partner channel gate", ("", ""))[1]
                .casefold()
                == "required"
            )
            dependent_rows = set()
            if monetization_required:
                dependent_rows.update(
                    {
                        "monetization model",
                        "pricing and offer",
                        "purchase and entitlement",
                        "merchant of record / tax owner",
                    }
                )
            if partner_required:
                dependent_rows.update(
                    {"partner motion", "partner economics and operations"}
                )
            for decision in sorted(dependent_rows):
                row = rows_by_decision.get(decision)
                if row is None:
                    continue
                selection = row[1].casefold().strip()
                if selection in {"none", "n/a", "not_required", "undecided"}:
                    _add(
                        problems,
                        "prd",
                        f"required commercial gate is incompatible with {row[0]} "
                        f"selection {row[1]!r}",
                    )
                if not _meaningful(row[1], minimum=4) or not _meaningful(
                    row[2], minimum=8
                ):
                    _add(
                        problems,
                        "prd",
                        f"required commercial row {row[0]} needs a concrete selection "
                        "and rationale",
                    )
                trace_tests = _ids(row[4], "TEST")
                if not trace_tests or not trace_tests.issubset(known_required_test_ids):
                    _add(
                        problems,
                        "prd",
                        f"required commercial row {row[0]} must trace to Required Yes "
                        "TEST IDs",
                    )

    commercial_gate_required = any(
        gate_name in rows_by_decision
        and rows_by_decision[gate_name][1].casefold() == "required"
        for gate_name in (
            "monetization infrastructure gate",
            "partner channel gate",
        )
    )
    if commercial_gate_required:
        commercial_architecture = _section(
            architecture_text, "## Monetization and Partner Channel Architecture"
        )
        if commercial_architecture is None or not _meaningful(
            commercial_architecture, minimum=25
        ):
            _add(
                problems,
                "architecture",
                "required commercial gate needs concrete monetization or partner "
                "architecture obligations",
            )
        if commercial_architecture is not None and _explicit_absence_reason(
            commercial_architecture
        ) is not None:
            _add(
                problems,
                "architecture",
                "required commercial gate cannot mark its architecture not_required",
            )
        required_commercial_terms = [
            ("purchase", "billing", "payment"),
            ("entitlement",),
            ("refund", "chargeback"),
            ("reconciliation",),
        ]
        if rows_by_decision.get("partner channel gate", ("", ""))[1].casefold() == "required":
            required_commercial_terms.extend(
                [("attribution",), ("commission", "payout"), ("provision",), ("termination",)]
            )
        normalized_architecture = (commercial_architecture or "").casefold()
        if any(
            not any(term in normalized_architecture for term in alternatives)
            for alternatives in required_commercial_terms
        ):
            _add(
                problems,
                "architecture",
                "required commercial gate architecture is missing purchase, entitlement, "
                "recovery, reconciliation, or partner-operation obligations",
            )
        if not ui_surfaces:
            _add(
                problems,
                "prd",
                "required commercial gate must define the affected customer, partner, "
                "or administration UI surfaces",
            )

    # Product Definition owns the UI surface contract but not UI direction,
    # wireframes, motion/media treatment, or visual approval. Require an
    # explicit downstream handoff instead of making those later decisions a
    # prerequisite for Product Definition Approval.
    ui_handoff = _section(prd_text, "## UI Design Handoff Status")
    if ui_handoff is not None:
        status_matches = list(re.finditer(
            r"^UI design:\s*(.+?)\s*$", ui_handoff, re.IGNORECASE | re.MULTILINE
        ))
        owner_matches = list(re.finditer(
            r"^UI decision owner:\s*(.+?)\s*$",
            ui_handoff,
            re.IGNORECASE | re.MULTILINE,
        ))
        status_match = status_matches[0] if len(status_matches) == 1 else None
        owner_match = owner_matches[0] if len(owner_matches) == 1 else None
        status = status_match.group(1).strip() if status_match else ""
        owner = owner_match.group(1).strip() if owner_match else ""
        if len(status_matches) != 1:
            _add(
                problems,
                "prd",
                "UI Design Handoff Status requires exactly one UI design line",
            )
        if len(owner_matches) != 1:
            _add(
                problems,
                "prd",
                "UI Design Handoff Status requires exactly one UI decision owner line",
            )
        if ui_surfaces:
            if require_filled and status.casefold() != (
                "pending explicit ui-design-builder request"
            ):
                _add(
                    problems,
                    "prd",
                    "UI-bearing package must defer UI design to ui-design-builder",
                )
            if require_filled and _invalid_human_owner(owner):
                _add(problems, "prd", "UI decision owner must name a human owner")
        else:
            headless_status = re.fullmatch(
                r"not_required\s*(?:—|-)\s*(.+)", status, re.IGNORECASE
            )
            if require_filled and headless_status is None:
                _add(problems, "prd", "headless package must record UI design not_required")
            if require_filled and headless_status is not None:
                reason = headless_status.group(1).strip()
                if not _meaningful(reason, minimum=10):
                    _add(problems, "prd", "headless UI design status needs a concrete reason")
    gate_records: dict[str, tuple[str, str, str]] = {}
    for gate_label in ("Data and Trust Gate", "AI and Automation Gate"):
        gate_line_count = len(
            re.findall(
                rf"^{re.escape(gate_label)}:\s*.*$",
                active_text(prd_text),
                re.IGNORECASE | re.MULTILINE,
            )
        )
        gate_record = _gate_record(prd_text, gate_label) if gate_line_count == 1 else None
        if gate_line_count != 1:
            _add(
                problems,
                "prd",
                f"{gate_label} requires exactly one active status line",
            )
        if gate_record is not None:
            gate_records[gate_label] = gate_record
        if gate_record is None:
            _add(
                problems,
                "prd",
                f"missing complete {gate_label} status, reason, or decision owner",
            )
            continue
        gate, reason, owner = gate_record
        if require_filled and (
            not _meaningful(reason, minimum=12) or _invalid_human_owner(owner)
        ):
            _add(problems, "prd", f"{gate_label} has an unfilled reason or owner")
        if require_approved and gate == "blocked":
            _add(problems, "prd", f"{gate_label} is blocked")
        if gate_label == "Data and Trust Gate" and gate == "required":
            required_stack_areas.add("backend or data")
        if gate_label == "AI and Automation Gate" and gate == "required":
            required_stack_areas.add("ai or automation")

    required_gate_details = (
        (
            "Data and Trust Gate",
            "## Data and Trust",
            DATA_TRUST_AREAS,
            "## Data and Trust Architecture",
            (
                ("classification", "ownership", "source of truth"),
                ("residency", "region", "vendor"),
                ("encryption", "access", "audit"),
                ("retention", "deletion", "export"),
                ("consent", "policy"),
                ("backup", "recovery"),
                ("incident",),
            ),
        ),
        (
            "AI and Automation Gate",
            "## AI and Automation",
            AI_AUTOMATION_AREAS,
            "## AI and Automation Architecture",
            (
                ("model", "provider", "version"),
                ("context", "retrieval"),
                ("prompt", "tool", "approval"),
                ("evaluation", "validation"),
                ("cost", "latency"),
                ("observability",),
                ("fallback", "shutoff"),
                ("incident",),
            ),
        ),
    )
    for (
        gate_label,
        prd_heading,
        expected_areas,
        architecture_heading,
        architecture_term_groups,
    ) in required_gate_details:
        record = gate_records.get(gate_label)
        if record is None or record[0] != "required":
            continue
        prd_gate_section = _section(prd_text, prd_heading)
        if prd_gate_section is not None:
            _validate_gate_decisions(
                prd_gate_section,
                label=gate_label,
                expected_areas=expected_areas,
                known_required_tests=known_required_test_ids,
                required_test_upstreams=required_test_upstreams,
                problems=problems,
            )
        section = _section(architecture_text, architecture_heading)
        if section is None or not _meaningful(section, minimum=25):
            _add(
                problems,
                "architecture",
                f"required {gate_label} needs concrete architecture obligations",
            )
        if section is not None and _explicit_absence_reason(section) is not None:
            _add(
                problems,
                "architecture",
                f"required {gate_label} cannot mark its architecture not_required",
            )
        normalized_section = (section or "").casefold()
        if any(
            not any(term in normalized_section for term in alternatives)
            for alternatives in architecture_term_groups
        ):
            _add(
                problems,
                "architecture",
                f"required {gate_label} architecture is missing one or more mandatory "
                "trust or automation controls",
            )

    research_gate = _research_gate(prd_text)
    research_gate_count = len(
        re.findall(
            r"^Research Gate:\s*.*$",
            active_text(prd_text),
            re.IGNORECASE | re.MULTILINE,
        )
    )
    if research_gate_count != 1:
        research_gate = None
        _add(problems, "prd", "Research Gate requires exactly one active decision line")
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
        assessed_dates = re.findall(
            r"\bassessed\s+(\d{4}-\d{2}-\d{2})\b",
            research_detail,
            re.IGNORECASE,
        )
        if require_filled and (
            len(assessed_dates) != 1 or not _real_date(assessed_dates[0])
        ):
            _add(problems, "prd", "Research Gate must name one real assessed YYYY-MM-DD date")
        if require_filled and not _meaningful(research_detail, minimum=20):
            _add(problems, "prd", "Research Gate must record concrete assessment evidence")
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
        if decided_on and not _real_date(decided_on):
            _add(problems, "prd approval", "Decided on must be a real YYYY-MM-DD date")
        approved_artifacts = [
            value.strip().casefold()
            for value in product_fields.get("approved artifacts", "").split(",")
            if value.strip()
        ]
        required_artifacts = ["prd.md", "architecture.md", "stack-decisions.md"]
        if approved_artifacts and approved_artifacts != required_artifacts:
            _add(
                problems,
                "prd approval",
                "Approved artifacts must be exactly, once and in order: "
                "PRD.md, architecture.md, stack-decisions.md",
            )
        checkpoint = product_fields.get("stack decision checkpoint", "").casefold()
        if require_approved and checkpoint != "approved":
            _add(problems, "prd approval", "Stack Decision Checkpoint must be approved")
        reconciliation = product_fields.get(
            "market research reconciliation", ""
        ).casefold()
        reconciliation_state = re.match(r"^(completed|skipped|blocked)\b", reconciliation)
        if reconciliation and reconciliation_state is None:
            _add(problems, "prd approval", "invalid market research reconciliation")
        elif reconciliation_state is not None and reconciliation_state.group(1) in {
            "skipped",
            "blocked",
        }:
            reason = reconciliation[reconciliation_state.end() :].strip(" —-:")
            if require_filled and (not reason or _placeholder_cell(reason)):
                _add(
                    problems,
                    "prd approval",
                    f"{reconciliation_state.group(1)} market research reconciliation "
                    "requires a concrete reason",
                )
        if require_approved and reconciliation.startswith("blocked"):
            _add(problems, "prd approval", "market research reconciliation is blocked")
        blockers = product_fields.get("blocking items", "").casefold()
        if require_approved and blockers not in {"none", "n/a"}:
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
                seen_areas: set[str] = set()
                for row in impact_rows:
                    if len(row) != len(ENHANCEMENT_IMPACT_HEADER):
                        continue
                    area = row[0].casefold()
                    if area in seen_areas:
                        _add(
                            problems,
                            "prd",
                            f"Enhancement Impact Record has duplicate area {row[0]!r}",
                        )
                    seen_areas.add(area)
                    impact = row[1].casefold()
                    if area == "ui structure / style":
                        valid_impacts = {"none", "structure", "style", "both"}
                    else:
                        valid_impacts = {"unchanged", "changed"}
                    if impact not in valid_impacts:
                        _add(
                            problems,
                            "prd",
                            f"{row[0]} has invalid enhancement impact {row[1]!r}",
                        )
                    changed = impact in {"changed", "structure", "style", "both"}
                    if changed:
                        if not (
                            re.search(
                                r"\b(?:PRD|UX|UI|ARCH|TEST|MR|RA)-[A-Z0-9-]+\b",
                                row[2],
                                re.IGNORECASE,
                            )
                            or re.search(r"\bdecision:\s*\S", row[2], re.IGNORECASE)
                        ):
                            _add(
                                problems,
                                "prd",
                                f"changed enhancement row {row[0]} must name structured "
                                "affected IDs or decision:<name> entries",
                            )
                        refresh = row[3].casefold()
                        invalid_refresh = (
                            not _meaningful(row[3])
                            or refresh in {"none", "n/a"}
                            or refresh.startswith(("none ", "none —", "none-", "n/a "))
                            or ENHANCEMENT_ARTIFACT_RE.search(row[3]) is None
                        )
                        required_artifacts: set[str]
                        required_gates: set[str]
                        if area == "ui structure / style":
                            if impact == "style":
                                required_artifacts = {"ui-design.md"}
                                required_gates = {"visual approval"}
                            else:
                                required_artifacts = {"wireframes.html", "ui-design.md"}
                                required_gates = {
                                    "copy freeze",
                                    "wireframe approval",
                                    "visual approval",
                                }
                        else:
                            required_artifacts, required_gates = (
                                ENHANCEMENT_REFRESH_REQUIREMENTS.get(area, (set(), set()))
                            )
                        missing_refresh_artifacts = sorted(
                            artifact
                            for artifact in required_artifacts
                            if artifact not in refresh
                        )
                        missing_refresh_gates = sorted(
                            gate for gate in required_gates if gate not in refresh
                        )
                        if invalid_refresh or missing_refresh_artifacts or missing_refresh_gates:
                            _add(
                                problems,
                                "prd",
                                f"changed enhancement row {row[0]} must record a non-none "
                                "area-specific refresh; missing artifacts: "
                                + (", ".join(missing_refresh_artifacts) or "none")
                                + "; missing gates: "
                                + (", ".join(missing_refresh_gates) or "none"),
                            )
                present = seen_areas
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
        if decided_on and not _real_date(decided_on):
            _add(problems, "stack checkpoint", "Decided on must be a real YYYY-MM-DD date")
        open_areas = stack_fields.get("open areas", "").casefold()
        if require_approved and open_areas not in {"none", "n/a"}:
            _add(problems, "stack checkpoint", "Open areas must be none")
        required_stack_areas.update(
            _stack_areas(stack_fields.get("approved areas", ""))
        )

    approved_stack_areas = _validate_stack_tables(
        stack_text,
        require_filled=require_filled,
        require_approved=require_approved,
        required_areas=required_stack_areas,
        repo_root=repo_root,
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
    repo_root: Path | None = None,
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
        repo_root=repo_root,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prd", required=True, type=Path)
    parser.add_argument("--architecture", required=True, type=Path)
    parser.add_argument("--stack-decisions", required=True, type=Path)
    parser.add_argument("--require-filled", action="store_true")
    parser.add_argument("--require-approved", action="store_true")
    parser.add_argument("--repo-root", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    problems = validate(
        args.prd,
        args.architecture,
        args.stack_decisions,
        require_filled=args.require_filled,
        require_approved=args.require_approved,
        repo_root=args.repo_root,
    )
    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        return 1
    print("PASS core Product Definition package is complete and owner-approved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate the core Product Definition package and its owner approvals."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

from markdown_contract import active_text, active_machine_block
from platform_delivery import parse_platform_delivery, PROTOCOL
from prd_operations import operation_graph_findings, required_operations
from prd_ui_contract import parse_prd_ui_contract
from release_targets import parse_release_targets
from git_evidence import GitEvidenceError, verify_revision_path
from eval_policy import validate_eval_policy
from contract_utils import (
    _without_machine_block,
    canonical_product_bytes,
    canonical_stack_bytes,
    parse_digest,
    product_identity,
    release_area_requirements,
    sha256_text,
)


# Wireframe-free UI contracts that use the direct PRD-to-HiFi preflight.
CURRENT_UI_CONTRACTS = ("ui-design/2", "ui-design/3")
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
    "## Security Requirements",
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
    "security",
    "monetization / partner",
    "release / operations",
}

DELTA_METADATA_HEADER = ("", "")
DELTA_METADATA_KEYS = ("epic", "baseline prd", "result prd", "status", "ambition rung")
DELTA_FILENAME_RE = re.compile(r"PRD-DELTA-(EPIC-\d+)\.md")
DELTA_LATEST_LINE_RE = re.compile(r"(?m)^\s*Latest delta:\s*(\S+)\s*$")
DELTA_LATEST_PATH_RE = re.compile(r"docs/product/deltas/PRD-DELTA-(EPIC-\d+)\.md")
DELTA_EPIC_PATH_RE = re.compile(r"docs/epics/(EPIC-\d+)-[a-z0-9][a-z0-9-]*\.md", re.I)
DELTA_HEADINGS = (
    "## Why",
    "## Enhancement Impact Record",
    "## Changed Requirements",
    "## Decisions",
    "## Approval",
)
CHANGED_REQUIREMENTS_HEADER = ("id", "change", "before", "after", "test ids")
VALID_DELTA_CHANGES = {"new", "revised", "retired"}
VALID_DELTA_STATUSES = {"draft", "approved"}
VALID_DELTA_TRACE_ID_RE = r"(?:PRD|UX|UI|ARCH)-[A-Z0-9-]+"
HEADING_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

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
    "CLI and Toolchain Decision": (
        "language",
        "toolchain",
        "distribution mechanism",
        "testing",
    ),
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
        "styling approach",
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
    "CLI and Toolchain Decision": "toolchain",
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
SECURITY_PRD_HEADING = "## Security Requirements"
SECURITY_GATE_LABEL = "Security Requirements Gate"
SECURITY_SCOPE_LABEL = "Security scope"
SECURITY_REQUIREMENTS_HEADER = (
    "prd id",
    "asset / trust boundary",
    "abuse case",
    "control / safe failure",
    "test ids",
    "owner",
    "residual risk",
)
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
ARCHITECTURE_AREA_SECTIONS = {
    "frontend": {"## Frontend Architecture"},
    "mobile or desktop": {"## Frontend Architecture"},
    "backend or data": {
        "## Backend Architecture",
        "## Data Model",
        "## API and Interface Contracts",
    },
    "ai or automation": {"## AI and Automation Architecture"},
    "commercial": {"## Monetization and Partner Channel Architecture"},
}
STACK_SELECTED_EVIDENCE_RE = re.compile(
    r"\brepository:(?P<path>(?!/)(?![A-Za-z]:)(?![^@]*\.\.)"
    r"[A-Za-z0-9._/-]+)@(?P<revision>[0-9a-f]{40}|sha256:[0-9a-f]{64})\b"
)
ENHANCEMENT_ARTIFACT_RE = re.compile(
    r"\b(?:(?:PRD|architecture|stack-decisions|wireframes|ui-design|design-system|"
    r"DEPLOYMENT|ACTIVATION|OUTCOME_REVIEW|SEO_REVIEW)\.(?:md|json|html)|HiFi)\b",
    re.IGNORECASE,
)
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


def _not_future_date(value: str) -> bool:
    return _real_date(value) and datetime.date.fromisoformat(value) <= datetime.date.today()


def _duration_days(value: str) -> int | None:
    match = re.fullmatch(r"\s*(\d+)\s*(day|days|week|weeks)\s*", value, re.I)
    if match is None:
        return None
    amount = int(match.group(1))
    if amount <= 0:
        return None
    return amount * (7 if match.group(2).casefold().startswith("week") else 1)


def _valid_measurement_value(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"", "tbd", "tbc", "todo", "pending", "unknown", "baseline", "target"}:
        return False
    return not _placeholder_cell(value)


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


def _latest_delta_reference(prd_text: str) -> str | None:
    decisions = _section(prd_text, "## Product Definition Decisions")
    if decisions is None:
        return None
    match = DELTA_LATEST_LINE_RE.search(decisions)
    return match.group(1).strip() if match else None


def _validate_enhancement_impact_record(
    artifact_text: str,
    *,
    known_ids: set[str],
    require_filled: bool,
    problems: list[str],
    path: str = "prd",
) -> None:
    impact_section = _section(artifact_text, "## Enhancement Impact Record")
    impact_rows = (
        _find_table(impact_section, ENHANCEMENT_IMPACT_HEADER)
        if impact_section is not None
        else None
    )
    if impact_rows is None:
        _add(problems, path, "Enhancement Impact Record has no impact table")
        return
    _validate_table_rows(
        impact_rows,
        len(ENHANCEMENT_IMPACT_HEADER),
        label="Enhancement Impact Record",
        require_filled=require_filled,
        problems=problems,
        path=path,
    )
    seen_areas: set[str] = set()
    for row in impact_rows:
        if len(row) != len(ENHANCEMENT_IMPACT_HEADER):
            continue
        area = row[0].casefold()
        if area in seen_areas:
            _add(problems, path, f"Enhancement Impact Record has duplicate area {row[0]!r}")
        seen_areas.add(area)
        impact = row[1].casefold()
        if area == "ui structure / style":
            valid_impacts = {"none", "structure", "style", "both"}
        else:
            valid_impacts = {"unchanged", "changed"}
        if impact not in valid_impacts:
            _add(problems, path, f"{row[0]} has invalid enhancement impact {row[1]!r}")
        changed = impact in {"changed", "structure", "style", "both"}
        if changed:
            referenced_ids = {
                match.group(0).upper()
                for match in re.finditer(
                    r"\b(?:PRD|UX|ARCH|TEST|MR|RA)-[A-Z0-9-]+\b",
                    row[2],
                    re.IGNORECASE,
                )
            }
            unknown_ids = sorted(referenced_ids - known_ids)
            if unknown_ids:
                _add(
                    problems,
                    path,
                    f"changed enhancement row {row[0]} references unknown IDs: "
                    + ", ".join(unknown_ids),
                )
            if not (
                re.search(r"\b(?:PRD|UX|UI|ARCH|TEST|MR|RA)-[A-Z0-9-]+\b", row[2], re.IGNORECASE)
                or re.search(r"\bdecision:\s*\S", row[2], re.IGNORECASE)
            ):
                _add(
                    problems,
                    path,
                    f"changed enhancement row {row[0]} must name structured "
                    "affected IDs or decision:<name> entries",
                )
            refresh = row[3].casefold()
            if (
                not _meaningful(row[3])
                or refresh in {"none", "n/a"}
                or refresh.startswith(("none ", "none —", "none-", "n/a "))
                or ENHANCEMENT_ARTIFACT_RE.search(row[3]) is None
            ):
                _add(
                    problems,
                    path,
                    f"changed enhancement row {row[0]} must record a non-none "
                    "refresh",
                )
    missing = sorted(REQUIRED_ENHANCEMENT_AREAS - seen_areas)
    if missing:
        _add(
            problems,
            path,
            "Enhancement Impact Record is missing areas: " + ", ".join(missing),
        )


def _validate_delta_file(
    delta_path: Path,
    delta_text: str,
    *,
    latest: bool,
    repo_root: Path | None,
    require_filled: bool,
    require_approved: bool,
    current_prd_digest: str,
    known_requirement_ids: set[str],
    known_test_ids: set[str],
    impact_known_ids: set[str],
    problems: list[str],
) -> None:
    label = f"delta {delta_path.name}"
    filename_match = DELTA_FILENAME_RE.fullmatch(delta_path.name)
    epic_id = filename_match.group(1) if filename_match else None
    title = re.search(r"(?m)^# PRD Delta (EPIC-\d+): (.+)$", active_text(delta_text))
    if epic_id is None:
        _add(
            problems,
            label,
            "delta filename must match PRD-DELTA-<EPIC-ID>.md with EPIC-<digits>",
        )
    elif title is None:
        _add(problems, label, "missing '# PRD Delta <EPIC-ID>: <outcome>' title")
    elif title.group(1) != epic_id:
        _add(
            problems,
            label,
            f"title epic {title.group(1)!r} does not match filename {delta_path.name!r}",
        )
    elif require_filled and _placeholder_cell(title.group(2)):
        _add(problems, label, "delta title outcome contains an unfilled placeholder")

    _validate_heading_sequence(delta_text, DELTA_HEADINGS, path=label, problems=problems)
    _extract_machine_block(
        delta_text,
        PRODUCT_APPROVAL_START,
        PRODUCT_APPROVAL_END,
        path=label,
        label="product-definition approval",
        problems=problems,
    )

    meta_rows = _find_table(delta_text, DELTA_METADATA_HEADER)
    meta: dict[str, str] = {}
    if meta_rows is None:
        _add(
            problems,
            label,
            "delta must open with the two-column metadata table (Epic, "
            "Baseline PRD, Result PRD, Status, Ambition rung)",
        )
    else:
        for row in meta_rows:
            if len(row) != len(DELTA_METADATA_HEADER):
                _add(problems, label, f"delta metadata row has {len(row)} cells, expected 2")
                continue
            key = row[0].casefold()
            if key in meta:
                _add(problems, label, f"duplicate delta metadata key {row[0]!r}")
            meta[key] = row[1]
        for key in DELTA_METADATA_KEYS:
            if key not in meta:
                _add(problems, label, f"delta metadata is missing {key!r}")

    epic_value = meta.get("epic", "")
    epic_path_match = DELTA_EPIC_PATH_RE.fullmatch(epic_value.strip())
    if "epic" in meta:
        if epic_path_match is None:
            _add(
                problems,
                label,
                "delta metadata Epic must reference docs/epics/<EPIC-ID>-<slug>.md",
            )
        elif epic_id is not None and epic_path_match.group(1).upper() != epic_id:
            _add(problems, label, "delta metadata Epic ID does not match the delta filename")
        elif (
            latest
            and repo_root is not None
            and not (repo_root / epic_value.strip()).is_file()
        ):
            _add(
                problems,
                label,
                f"delta metadata Epic path does not exist: {epic_value.strip()}",
            )
    if "baseline prd" in meta and parse_digest(meta["baseline prd"]) is None:
        _add(problems, label, "delta metadata Baseline PRD must use sha256:<64 lowercase hex>")
    if "result prd" in meta:
        result_digest = parse_digest(meta["result prd"])
        if result_digest is None:
            if meta["result prd"].strip().casefold() != "pending":
                _add(
                    problems,
                    label,
                    "delta metadata Result PRD must use sha256:<64 lowercase hex> or pending",
                )
            elif latest and require_approved:
                _add(problems, label, "approved delta metadata Result PRD must not stay pending")
        elif latest and result_digest != current_prd_digest:
            _add(
                problems,
                label,
                "delta metadata Result PRD hash does not match the current PRD.md content",
            )
    if "status" in meta:
        status = meta["status"].strip().casefold()
        if status not in VALID_DELTA_STATUSES:
            _add(problems, label, "delta metadata Status must be draft or approved")
        elif latest and require_approved and status != "approved":
            _add(problems, label, "delta metadata Status must be approved")
    if "ambition rung" in meta:
        rung_match = re.fullmatch(r"\s*([123])\s*(?:—|-)\s*(.+?)\s*", meta["ambition rung"])
        if rung_match is None:
            _add(
                problems,
                label,
                "delta metadata Ambition rung must use '1 / 2 / 3 — <one line>'",
            )
        elif require_filled and _placeholder_cell(rung_match.group(2)):
            _add(problems, label, "delta metadata Ambition rung contains an unfilled placeholder")

    changed_rows = _find_table(delta_text, CHANGED_REQUIREMENTS_HEADER)
    if changed_rows is None:
        _add(
            problems,
            label,
            "delta must contain the Changed Requirements table "
            "(ID | Change | Before | After | TEST IDs)",
        )
    else:
        _validate_table_rows(
            changed_rows,
            len(CHANGED_REQUIREMENTS_HEADER),
            label="Changed Requirements",
            require_filled=require_filled,
            problems=problems,
            path=label,
        )
        for row in changed_rows:
            if len(row) != len(CHANGED_REQUIREMENTS_HEADER):
                continue
            change = row[1].casefold()
            if change not in VALID_DELTA_CHANGES:
                _add(
                    problems,
                    label,
                    f"Changed Requirements row {row[0]!r} Change must be new, revised or retired",
                )
            if not re.fullmatch(VALID_DELTA_TRACE_ID_RE, row[0].strip(), re.IGNORECASE):
                _add(
                    problems,
                    label,
                    f"Changed Requirements ID {row[0]!r} must be a PRD-/UX-/UI-/ARCH- trace ID",
                )
                continue
            trace_id = row[0].strip().upper()
            test_ids = _ids(row[4], "TEST")
            if not test_ids and row[4].strip().casefold() not in {"none", "n/a"}:
                _add(
                    problems,
                    label,
                    f"Changed Requirements row {row[0]!r} TEST IDs must list TEST IDs or none",
                )
            if not latest:
                continue
            if change in {"new", "revised"}:
                if trace_id not in known_requirement_ids:
                    _add(
                        problems,
                        label,
                        f"Changed Requirements {change} ID {trace_id} is absent from PRD.md",
                    )
                for test_id in sorted(test_ids - known_test_ids):
                    _add(
                        problems,
                        label,
                        f"Changed Requirements row {trace_id} references unknown {test_id}",
                    )
            elif change == "retired" and trace_id in known_requirement_ids:
                _add(
                    problems,
                    label,
                    f"Changed Requirements retired ID {trace_id} is still present in PRD.md",
                )

    impact_section = _section(delta_text, "## Enhancement Impact Record")
    if impact_section is not None:
        impact_rows = _find_table(impact_section, ENHANCEMENT_IMPACT_HEADER)
        if impact_rows is None:
            _add(problems, label, "Enhancement Impact Record has no impact table")
        elif not latest:
            _validate_table_rows(
                impact_rows,
                len(ENHANCEMENT_IMPACT_HEADER),
                label="Enhancement Impact Record",
                require_filled=require_filled,
                problems=problems,
                path=label,
            )
    if latest:
        _validate_enhancement_impact_record(
            delta_text,
            known_ids=impact_known_ids,
            require_filled=require_filled,
            problems=problems,
            path=label,
        )


def _validate_deltas(
    prd_text: str,
    deltas_dir: Path | None,
    *,
    require_filled: bool,
    require_approved: bool,
    repo_root: Path | None,
    known_requirement_ids: set[str],
    known_test_ids: set[str],
    impact_known_ids: set[str],
    problems: list[str],
) -> None:
    for line in active_text(prd_text).splitlines():
        if re.match(r"^#{1,6}\s", line) and HEADING_DATE_RE.search(line):
            _add(problems, "prd", f"delta mode forbids dated heading {line.strip()!r}")
    if _has_heading(prd_text, "## Enhancement Impact Record"):
        _add(
            problems,
            "prd",
            "delta mode records the Enhancement Impact Record in PRD deltas, not PRD.md",
        )
    latest_reference = _latest_delta_reference(prd_text)
    latest_name: str | None = None
    if latest_reference is None:
        _add(
            problems,
            "prd",
            "Product Definition Decisions must record 'Latest delta: "
            "docs/product/deltas/PRD-DELTA-<EPIC-ID>.md'",
        )
    else:
        latest_match = DELTA_LATEST_PATH_RE.fullmatch(latest_reference)
        if latest_match is None:
            _add(
                problems,
                "prd",
                "Latest delta must reference docs/product/deltas/PRD-DELTA-<EPIC-ID>.md",
            )
        else:
            latest_name = f"PRD-DELTA-{latest_match.group(1)}.md"
    if deltas_dir is None:
        _add(
            problems,
            "prd",
            "delta mode requires the docs/product/deltas directory to validate the recorded delta",
        )
        return
    if not deltas_dir.is_dir():
        _add(problems, "prd", f"delta mode requires the deltas directory {deltas_dir}")
        return
    delta_files = sorted(
        path for path in deltas_dir.glob("*.md") if DELTA_FILENAME_RE.fullmatch(path.name)
    )
    if latest_name is not None and latest_name not in {path.name for path in delta_files}:
        _add(problems, "prd", f"Latest delta file {latest_reference} is missing")
    current_prd_digest = sha256_text(
        _without_machine_block(prd_text, PRODUCT_APPROVAL_START, PRODUCT_APPROVAL_END)
    )
    for delta_path in delta_files:
        try:
            delta_text = delta_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            _add(
                problems,
                f"delta {delta_path.name}",
                f"cannot read UTF-8 file {delta_path}: {exc}",
            )
            continue
        _validate_delta_file(
            delta_path,
            delta_text,
            latest=delta_path.name == latest_name,
            repo_root=repo_root,
            require_filled=require_filled,
            require_approved=require_approved,
            current_prd_digest=current_prd_digest,
            known_requirement_ids=known_requirement_ids,
            known_test_ids=known_test_ids,
            impact_known_ids=impact_known_ids,
            problems=problems,
        )


def _validate_architecture_sections(
    architecture_text: str,
    *,
    problems: list[str],
    required_areas: set[str] | None = None,
) -> None:
    required_areas = required_areas or set()
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
    for area in sorted(required_areas):
        headings = ARCHITECTURE_AREA_SECTIONS.get(area, set())
        if not headings or any(
            (
                (section := _section(architecture_text, heading)) is not None
                and _explicit_absence_reason(section) is None
                and _meaningful(section, minimum=25)
            )
            for heading in headings
        ):
            continue
        _add(
            problems,
            "architecture",
            f"release surfaces require substantive {area} architecture; it cannot be not_required",
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
    if re.search(r"\b(?:cli|toolchain)\b", normalized):
        areas.add("toolchain")
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
        verify_revision_path(root, revision, relative)
    except GitEvidenceError as exc:
        _add(
            problems,
            "stack-decisions",
            f"Selected layer {label!r} repository revision cannot be verified safely: {exc}",
        )
        return


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


def security_negative_evidence_valid(value: object) -> bool:
    """Require explicit, observable denial and unchanged-state assertions."""

    if not isinstance(value, str):
        return False
    match = re.fullmatch(
        r"denial:\s*rejected\s*\(([^();\n]+)\);\s*"
        r"no unauthorized side effects:\s*unchanged\s*\(([^();\n]+)\)",
        value.strip(), re.IGNORECASE,
    )
    return bool(match) and all(
        _meaningful(signal, minimum=12) and not _placeholder_cell(signal)
        and signal.strip().casefold() not in {
            "observable signal", "observable rejection signal",
            "observable state evidence", "state evidence",
        }
        for signal in match.groups()
    )


def parse_security_requirements(
    prd_text: str,
) -> tuple[dict[str, object], list[str]]:
    """Parse the active PRD Security Requirements contract.

    Cross-artifact ID, test, architecture, and release checks remain in
    ``validate_texts`` after those contracts have been parsed.
    """

    empty_contract: dict[str, object] = {
        "status": "",
        "scope": "",
        "requirements": [],
    }
    if not isinstance(prd_text, str):
        return empty_contract, ["prd: Security Requirements input must be text"]

    errors: list[str] = []
    active = active_text(prd_text)
    section_matches = list(
        re.finditer(
            rf"^{re.escape(SECURITY_PRD_HEADING)}\s*$",
            active,
            re.MULTILINE,
        )
    )
    gate_matches = list(
        re.finditer(
            rf"^{re.escape(SECURITY_GATE_LABEL)}:\s*.*$",
            active,
            re.IGNORECASE | re.MULTILINE,
        )
    )
    scope_matches = list(
        re.finditer(
            rf"^{re.escape(SECURITY_SCOPE_LABEL)}:\s*.*$",
            active,
            re.IGNORECASE | re.MULTILINE,
        )
    )
    expected_security_header = tuple(
        cell.casefold() for cell in SECURITY_REQUIREMENTS_HEADER
    )
    table_header_matches = [
        line
        for line in active.splitlines()
        if _table_cells(line) is not None
        and tuple(cell.casefold() for cell in _table_cells(line) or ())
        == expected_security_header
    ]

    section = _section(prd_text, SECURITY_PRD_HEADING)
    if section is None:
        _add(errors, "prd", "Security Requirements section is required")
        if gate_matches or scope_matches or table_header_matches:
            _add(
                errors,
                "prd",
                "Security Requirements authority must be inside its own section",
            )
        return empty_contract, errors

    section_table_header_matches = [
        line
        for line in active_text(section).splitlines()
        if _table_cells(line) is not None
        and tuple(cell.casefold() for cell in _table_cells(line) or ())
        == expected_security_header
    ]

    if len(section_matches) != 1:
        _add(errors, "prd", "duplicate Security Requirements section")
    if len(gate_matches) != 1:
        _add(
            errors,
            "prd",
            "Security Requirements Gate requires exactly one active status line",
        )
    if len(scope_matches) != 1:
        _add(
            errors,
            "prd",
            "Security scope requires exactly one active executable or "
            "documentation_only line",
        )
    if len(table_header_matches) > 1:
        _add(errors, "prd", "duplicate Security Requirements table header")
    if len(table_header_matches) != len(section_table_header_matches):
        _add(
            errors,
            "prd",
            "Security Requirements table must stay inside its own section",
        )
    if sum(
        1
        for _
        in re.finditer(
            rf"^{re.escape(SECURITY_GATE_LABEL)}:\s*.*$",
            section,
            re.IGNORECASE | re.MULTILINE,
        )
    ) != 1 or sum(
        1
        for _
        in re.finditer(
            rf"^{re.escape(SECURITY_SCOPE_LABEL)}:\s*.*$",
            section,
            re.IGNORECASE | re.MULTILINE,
        )
    ) != 1:
        _add(
            errors,
            "prd",
            "Security gate and scope must be inside the Security Requirements section",
        )

    security_position = section_matches[0].start()
    data_trust_position = re.search(
        r"^## Data and Trust\s*$", active, re.MULTILINE
    )
    ai_position = re.search(r"^## AI and Automation\s*$", active, re.MULTILINE)
    if data_trust_position is not None and security_position < data_trust_position.start():
        _add(errors, "prd", "Security Requirements must follow Data and Trust")
    if ai_position is not None and security_position > ai_position.start():
        _add(errors, "prd", "Security Requirements must precede AI and Automation")

    gate_record = _gate_record(section, SECURITY_GATE_LABEL)
    status = gate_record[0] if gate_record is not None else ""
    scope_match = re.fullmatch(
        r"(executable|documentation_only)",
        next(
            (
                match.group(1).casefold()
                for match in re.finditer(
                    rf"^{re.escape(SECURITY_SCOPE_LABEL)}:\s*(.*?)\s*$",
                    section,
                    re.IGNORECASE | re.MULTILINE,
                )
            ),
            "",
        ),
    )
    if gate_record is None:
        _add(
            errors,
            "prd",
            "missing complete Security Requirements Gate reason or decision owner",
        )
    if scope_match is None:
        _add(errors, "prd", "Security scope must be executable or documentation_only")

    requirements: list[dict[str, object]] = []
    rows = (
        _find_table(section, SECURITY_REQUIREMENTS_HEADER)
        if len(section_table_header_matches) == 1
        else None
    )
    if status == "required" and rows is None:
        _add(
            errors,
            "prd",
            "required Security Requirements Gate must use its canonical table",
        )
    if rows is not None:
        _validate_table_rows(
            rows,
            len(SECURITY_REQUIREMENTS_HEADER),
            label="Security Requirements",
            require_filled=True,
            problems=errors,
        )
        seen_prd_ids: set[str] = set()
        for row in rows:
            if len(row) != len(SECURITY_REQUIREMENTS_HEADER):
                continue
            prd_ids = _ids(row[0], "PRD")
            if len(prd_ids) != 1 or not re.fullmatch(
                r"PRD-[A-Z0-9-]+", row[0], re.IGNORECASE
            ):
                _add(errors, "prd", f"invalid Security Requirements ID {row[0]!r}")
                continue
            prd_id = next(iter(prd_ids))
            if prd_id in seen_prd_ids:
                _add(errors, "prd", f"duplicate Security Requirements ID {prd_id}")
            seen_prd_ids.add(prd_id)
            test_ids = list(
                dict.fromkeys(
                    match.group(0).upper()
                    for match in re.finditer(
                        r"\bTEST-[A-Z0-9-]+\b", row[4], re.IGNORECASE
                    )
                )
            )
            if not test_ids:
                _add(errors, "prd", f"{prd_id} Security Requirements row names no TEST ID")
            requirements.append(
                {
                    "prd_id": prd_id,
                    "asset_trust_boundary": row[1],
                    "abuse_case": row[2],
                    "control_safe_failure": row[3],
                    "test_ids": test_ids,
                    "owner": row[5],
                    "residual_risk": row[6],
                }
            )
        if status == "required" and not requirements:
            _add(errors, "prd", "required Security Requirements table must contain rows")
    if status == "not_required" and requirements:
        _add(errors, "prd", "not_required Security Requirements Gate cannot have rows")
    if status == "not_required" and scope_match is not None:
        if scope_match.group(1) != "documentation_only":
            _add(
                errors,
                "prd",
                "not_required Security Requirements Gate requires documentation_only scope",
            )

    if errors:
        return empty_contract, errors
    return (
        {
            "status": status,
            "scope": scope_match.group(1) if scope_match is not None else "",
            "requirements": requirements,
        },
        errors,
    )


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
    ui_contract: str | None = None,
    eval_policy: str | None = None,
    platform_delivery: str | None = None,
    deltas_dir: Path | None = None,
    notes: list[str] | None = None,
) -> list[str]:
    """Validate already-decoded core product-package texts."""

    if ui_contract is not None and ui_contract not in CURRENT_UI_CONTRACTS:
        raise ValueError(
            "unsupported --ui-contract value; current contracts are "
            + " and ".join(CURRENT_UI_CONTRACTS)
        )

    if eval_policy not in (None, "eval-policy/1"):
        raise ValueError("unsupported --eval-policy value")
    if platform_delivery is not None and platform_delivery != PROTOCOL:
        raise ValueError("unsupported --platform-delivery value")
    problems: list[str] = validate_eval_policy(
        prd_text, required=eval_policy is not None, repo_root=repo_root,
    )
    delta_mode = (_latest_delta_reference(prd_text) is not None) or (
        deltas_dir is not None and deltas_dir.is_dir()
    )

    prd_required_headings = (
        REQUIRED_PRD_HEADINGS
        if require_approved
        else tuple(
            heading
            for heading in REQUIRED_PRD_HEADINGS
            if heading != SECURITY_PRD_HEADING
        )
    )
    _validate_heading_sequence(
        prd_text, prd_required_headings, path="prd", problems=problems
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
    if ui_contract in CURRENT_UI_CONTRACTS:
        # Parse operations from the active contract.  Reusing the parser also
        # checks one operation anchor per surface and its declared endpoints.
        operations, operation_errors = required_operations(prd_text)
        seen = set(problems)
        problems.extend(error for error in operation_errors if error not in seen)
        # ui-design/3 also applies the HiFi entry reachability rule here, so a
        # dead end fails at Product Definition Approval, not at HiFi preflight.
        if ui_contract == "ui-design/3" and not operation_errors:
            problems.extend(operation_graph_findings(ui_surfaces, operations))
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
    required_stack_areas.update(release_area_requirements(release_contract.targets))
    platform_contract, platform_findings = parse_platform_delivery(
        architecture_text,
        prd_text,
        require=platform_delivery is not None,
    )
    problems.extend(platform_findings)
    if (
        require_approved
        and platform_contract is not None
        and platform_contract.decision_status != "approved"
    ):
        _add(
            problems,
            "architecture",
            "platform delivery Decision status must be approved for implementation",
        )
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
        expected_responsive = (
            "sizeClasses"
            if capture_mode in {"native", "desktop"}
            else "viewports"
        )
        responsive_kind = surface.get("responsiveKind")
        if responsive_kind and responsive_kind != expected_responsive:
            _add(
                problems,
                f"prd.{surface_id}.responsive",
                f"must use {expected_responsive!r} responsive data for captureMode {capture_mode!r}",
            )
    if require_filled:
        _validate_architecture_sections(
            architecture_text,
            problems=problems,
            required_areas=required_stack_areas,
        )

    identities = {
        "PRD": product_identity(prd_text, kind="prd"),
        "architecture": product_identity(architecture_text, kind="architecture"),
        "stack-decisions": product_identity(stack_text, kind="stack"),
    }
    explicit_identities = {value for value in identities.values() if value}
    if require_approved:
        for label, identity in identities.items():
            if not identity:
                _add(
                    problems,
                    "package",
                    f"{label} must contain a non-empty canonical product identity",
                )
    if len(explicit_identities) > 1:
        _add(
            problems,
            "package",
            "PRD, architecture, and stack-decisions product identities must match exactly",
        )

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
    test_rows_by_id: dict[str, tuple[str, ...]] = {}
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
        test_rows_by_id[test_id] = row
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
                if not _valid_measurement_value(row[2]):
                    _add(problems, "prd", f"metric {row[0]!r} baseline must be concrete")
                if not _valid_measurement_value(row[3]):
                    _add(problems, "prd", f"metric {row[0]!r} target / guardrail must be concrete")
                if _duration_days(row[4]) is None:
                    _add(
                        problems,
                        "prd",
                        f"metric {row[0]!r} measurement window must use a positive day/week duration",
                    )
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
        required_commercial_terms: list[tuple[str, ...]] = []
        if rows_by_decision.get("monetization infrastructure gate", ("", ""))[1].casefold() == "required":
            required_commercial_terms.extend(
                [
                    ("purchase", "billing", "payment"),
                    ("entitlement",),
                    ("refund", "chargeback"),
                    ("reconciliation",),
                ]
            )
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
        # A paid API, webhook, job, or partner-only surface can be commercial
        # without shipping a UI.  The architecture and interface contracts
        # above are the applicability evidence for headless purchase flows.

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

    if any(target.surface_class == "agent" for target in release_contract.targets):
        agent_gate = gate_records.get("AI and Automation Gate")
        if agent_gate is None or agent_gate[0] != "required":
            _add(
                problems,
                "prd",
                "agent release targets require an AI and Automation Gate marked required",
            )

    security_contract, security_errors = parse_security_requirements(prd_text)
    security_section_present = re.search(
        rf"^{re.escape(SECURITY_PRD_HEADING)}\s*$",
        active_text(prd_text),
        re.MULTILINE,
    ) is not None
    missing_security_section_only = (
        not security_section_present
        and security_errors == ["prd: Security Requirements section is required"]
    )
    if require_approved or not missing_security_section_only:
        problems.extend(security_errors)

    security_section = _section(prd_text, SECURITY_PRD_HEADING)
    security_gate = (
        _gate_record(security_section, SECURITY_GATE_LABEL)
        if security_section is not None
        else None
    )
    if security_gate is not None:
        _, security_reason, security_owner = security_gate
        if not _meaningful(security_reason, minimum=12) or _invalid_human_owner(
            security_owner
        ):
            _add(
                problems,
                "prd",
                "Security Requirements Gate needs a concrete reason and human owner",
            )
        if require_approved and security_gate[0] == "blocked":
            _add(problems, "prd", "Security Requirements Gate is blocked")

    security_status = str(security_contract.get("status", ""))
    security_scope = str(security_contract.get("scope", ""))
    deployable_surfaces = bool(
        release_contract.expected_surfaces or release_contract.targets
    )
    if not security_errors:
        if security_status == "not_required":
            archetype = (_section(architecture_text, "## Product Archetype") or "").strip()
            identity_rows = _find_table(_section(prd_text, "## At a Glance") or "", ("", "")) or []
            descriptions = [row[1] for row in identity_rows if len(row) == 2 and row[0].casefold() == "what it is"]
            documentation_archetype = re.fullmatch(
                r"documentation_only\s+—\s+(.+)", archetype,
            )
            runtime_sections_absent = all(
                _explicit_absence_reason(_section(architecture_text, heading) or "")
                for heading in (
                    "## Frontend Architecture", "## Backend Architecture",
                    "## API and Interface Contracts", "## AI and Automation Architecture",
                    "## Data Model",
                )
            )
            # A concrete document inventory proves output scope without guessing
            # executable meaning from words in a human's description.
            components = _find_table(
                _section(architecture_text, "## Component Architecture") or "",
                ARCHITECTURE_TABLE_HEADERS["## Component Architecture"],
            ) or []
            documentation_outputs = bool(components) and all(
                len(row) == 5
                and re.fullmatch(
                    r"(?:docs/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+|README(?:\.[A-Za-z-]+)?)"
                    r"\.(?:md|rst|txt)", row[1], re.IGNORECASE,
                )
                for row in components
            )
            documentation_workflow = all(
                re.fullmatch(
                    rf"{kind}\s+—\s+[^\n]{{20,}}",
                    (_section(architecture_text, heading) or "").strip(),
                )
                for heading, kind in (
                    ("## Workflow and Data Flow", "human_review"),
                    ("## Deployment and Operations", "document_distribution"),
                )
            )
            if (
                not documentation_archetype
                or not _meaningful(documentation_archetype.group(1), minimum=20)
                or len(descriptions) != 1
                or not re.match(r"(?:a\s+)?documentation-only\b", descriptions[0], re.IGNORECASE)
                or ui_surfaces
                or not runtime_sections_absent
                or not documentation_outputs
                or not documentation_workflow
                or gate_records.get("AI and Automation Gate", ("",))[0] == "required"
            ):
                _add(
                    problems, "prd",
                    "not_required Security Requirements Gate needs a documentation-only "
                    "product description, a documentation_only — reason Product Archetype, "
                    "and no executable product or architecture scope",
                )
        if security_scope == "executable" and security_status not in {
            "required",
            "blocked",
        }:
            _add(
                problems,
                "prd",
                "executable Security scope requires the Security Requirements Gate "
                "to be required; blocked remains draft-inspectable",
            )
        if deployable_surfaces and security_status not in {"required", "blocked"}:
            _add(
                problems,
                "prd",
                "expected or actual deployable surfaces require the Security "
                "Requirements Gate to be required; blocked remains draft-inspectable",
            )
        if security_status == "not_required" and deployable_surfaces:
            _add(
                problems,
                "prd",
                "not_required Security Requirements Gate cannot have deployable surfaces",
            )

    security_requirements = security_contract.get("requirements", [])
    if not security_errors:
        referenced_security_tests = {
            test_id for requirement in security_requirements
            for test_id in requirement.get("test_ids", [])
        }
        for test_id, test_row in test_rows_by_id.items():
            if test_row[3].casefold() != "yes" or test_row[2].casefold() != "security":
                continue
            if test_id not in referenced_security_tests:
                _add(problems, "prd", f"required security {test_id} must be referenced by a Security Requirements row")
            if not security_negative_evidence_valid(test_row[5]):
                _add(
                    problems, "prd",
                    f"{test_id} security Expected signal must declare "
                    "denial: rejected (observable signal); no unauthorized side "
                    "effects: unchanged (observable state evidence)",
                )
    if not security_errors and security_status == "required":
        allowed_requirement_ids = must_ids | applicable_nfr_ids
        for requirement in security_requirements:
            if not isinstance(requirement, dict):
                continue
            prd_id = str(requirement.get("prd_id", ""))
            if prd_id not in allowed_requirement_ids:
                _add(
                    problems,
                    "prd",
                    f"Security Requirements row {prd_id} must reference one existing "
                    "Must or applicable NFR PRD ID",
                )
            for field_name in (
                "asset_trust_boundary",
                "abuse_case",
                "control_safe_failure",
            ):
                if not _meaningful(str(requirement.get(field_name, "")), minimum=12):
                    _add(
                        problems,
                        "prd",
                        f"{prd_id} Security Requirements row needs substantive "
                        f"{field_name.replace('_', ' ')} text",
                    )
            if _invalid_human_owner(str(requirement.get("owner", ""))):
                _add(
                    problems,
                    "prd",
                    f"{prd_id} Security Requirements row must name a human owner",
                )
            residual_risk = str(requirement.get("residual_risk", ""))
            normalized_residual = residual_risk.strip().casefold()
            residual_decision = re.fullmatch(
                r"(none|accepted)\s*(?:—|-)\s*(.+)",
                residual_risk,
                re.IGNORECASE,
            )
            residual_is_decision = (
                normalized_residual == "none"
                or (
                    residual_decision is not None
                    and _meaningful(residual_decision.group(2), minimum=8)
                    and not _placeholder_cell(residual_decision.group(2))
                )
            )
            if not residual_is_decision:
                _add(
                    problems,
                    "prd",
                    f"{prd_id} Security Requirements residual risk must be an explicit "
                    "decision; use 'none', 'none — reason', or "
                    "'accepted — rationale' (hyphen accepted)",
                )
            for test_id in requirement.get("test_ids", []):
                test_row = test_rows_by_id.get(test_id)
                if test_row is None:
                    _add(
                        problems,
                        "prd",
                        f"{prd_id} Security Requirements row references optional or "
                        f"unknown {test_id}",
                    )
                    continue
                if test_row[3].casefold() != "yes":
                    _add(
                        problems,
                        "prd",
                        f"{prd_id} Security Requirements row references optional "
                        f"{test_id}",
                    )
                if test_row[2].casefold() != "security":
                    _add(
                        problems,
                        "prd",
                        f"{test_id} must have Test type security",
                    )
                if prd_id not in required_test_upstreams.get(test_id, set()):
                    _add(
                        problems,
                        "prd",
                        f"{test_id} upstream traces must name the same {prd_id}",
                    )

        architecture_security = _section(
            architecture_text, "## Auth, Permissions, and Security"
        )
        if architecture_security is None:
            _add(
                problems,
                "architecture",
                "required Security Requirements Gate needs Auth, Permissions, and "
                "Security architecture obligations",
            )
        elif _explicit_absence_reason(architecture_security) is not None:
            _add(
                problems,
                "architecture",
                "required Security Requirements Gate cannot mark Auth, Permissions, "
                "and Security not_required",
            )
        elif not _meaningful(architecture_security, minimum=50):
            _add(
                problems,
                "architecture",
                "required Security Requirements Gate needs substantive enforcement "
                "narrative",
            )
        else:
            active_architecture_security = active_text(architecture_security)

            def substantive_architecture_join(identifier: str, prefix: str) -> bool:
                return any(
                    identifier in _ids(line, prefix)
                    and _meaningful(
                        line.replace(identifier, " "),
                        minimum=15,
                    )
                    for line in active_architecture_security.splitlines()
                )

            for requirement in security_requirements:
                if not isinstance(requirement, dict):
                    continue
                prd_id = str(requirement.get("prd_id", ""))
                if not substantive_architecture_join(prd_id, "PRD"):
                    _add(
                        problems,
                        "architecture",
                        f"required Security Requirements row {prd_id} needs an active "
                        "substantive Auth, Permissions, and Security join",
                    )
                for test_id in requirement.get("test_ids", []):
                    if not substantive_architecture_join(str(test_id), "TEST"):
                        _add(
                            problems,
                            "architecture",
                            f"{test_id} needs an active substantive Auth, Permissions, "
                            "and Security join",
                        )

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

    impact_known_ids = (
        requirement_ids
        | ux_ids
        | architecture_ids
        | known_test_ids
        | _ids(prd_text, "MR")
        | _ids(prd_text, "RA")
    )

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
        if require_approved and "package digest" not in product_fields:
            _add(problems, "prd approval", "missing required field 'Package digest'")
        package_digest = product_fields.get("package digest", "")
        package_revision = product_fields.get("package revision", "")
        revision_digest = re.fullmatch(
            r"PD-R[0-9]+@(?P<digest>sha256:[0-9a-f]{64})",
            package_revision,
            re.I,
        )
        if require_approved:
            expected_digest = sha256_text(
                canonical_product_bytes(prd_text, architecture_text, stack_text)
            )
            supplied_digest = parse_digest(package_digest)
            if supplied_digest is None and revision_digest is not None:
                supplied_digest = parse_digest(revision_digest.group("digest"))
            if supplied_digest is None:
                _add(
                    problems,
                    "prd approval",
                    "Package digest must use sha256:<64 lowercase hex>",
                )
            elif supplied_digest != expected_digest:
                _add(
                    problems,
                    "prd approval",
                    "Package digest does not match the approved PRD/architecture/stack bytes",
                )
            if revision_digest is None:
                _add(
                    problems,
                    "prd approval",
                    "Package revision must exactly match PD-R<integer>@sha256:<the exact package digest>",
                )
            elif supplied_digest is not None:
                revision_value = parse_digest(revision_digest.group("digest"))
                if revision_value != supplied_digest:
                    _add(
                        problems,
                        "prd approval",
                        "Package revision digest must equal Package digest",
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
        elif decided_on and not _not_future_date(decided_on):
            _add(problems, "prd approval", "Decided on cannot be in the future")
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
        if mode == "enhancement" and not delta_mode:
            if not _has_heading(prd_text, "## Enhancement Impact Record"):
                _add(
                    problems,
                    "prd",
                    "enhancement package is missing Enhancement Impact Record",
                )
            else:
                _validate_enhancement_impact_record(
                    prd_text,
                    known_ids=impact_known_ids,
                    require_filled=require_filled,
                    problems=problems,
                )

    if delta_mode:
        _validate_deltas(
            prd_text,
            deltas_dir,
            require_filled=require_filled,
            require_approved=require_approved,
            repo_root=repo_root,
            known_requirement_ids=requirement_ids
            | ux_ids
            | architecture_ids
            | set(ui_surfaces),
            known_test_ids=known_test_ids,
            impact_known_ids=impact_known_ids,
            problems=problems,
        )
    elif notes is not None:
        notes.append(
            "legacy package: no docs/product/deltas directory; delta checks skipped"
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
                *(
                    ("Checkpoint digest",)
                    if require_approved
                    else ()
                ),
            ),
            path="stack checkpoint",
            problems=problems,
            require_filled=require_filled,
        )
        checkpoint_digest = stack_fields.get("checkpoint digest", "")
        if checkpoint_digest and require_approved:
            expected_checkpoint = sha256_text(canonical_stack_bytes(stack_text))
            supplied_checkpoint = parse_digest(checkpoint_digest)
            if supplied_checkpoint is None:
                _add(
                    problems,
                    "stack checkpoint",
                    "Checkpoint digest must use sha256:<64 lowercase hex>",
                )
            elif supplied_checkpoint != expected_checkpoint:
                _add(
                    problems,
                    "stack checkpoint",
                    "Checkpoint digest does not match the approved stack bytes",
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
        elif decided_on and not _not_future_date(decided_on):
            _add(problems, "stack checkpoint", "Decided on cannot be in the future")
        open_areas = stack_fields.get("open areas", "").casefold()
        if require_approved and open_areas not in {"none", "n/a"}:
            _add(problems, "stack checkpoint", "Open areas must be none")

    approved_stack_areas = _validate_stack_tables(
        stack_text,
        require_filled=require_filled,
        require_approved=require_approved,
        required_areas=required_stack_areas,
        repo_root=repo_root,
        problems=problems,
    )
    if "toolchain" in required_stack_areas:
        toolchain_section = _section(stack_text, "## CLI and Toolchain Decision")
        if toolchain_section is None or not _meaningful(toolchain_section, minimum=25):
            _add(
                problems,
                "stack-decisions",
                "CLI and non-public release targets require a substantive CLI and Toolchain Decision",
            )
    if require_approved:
        approved_value = stack_fields.get("approved areas", "") if stack_block is not None else ""
        approved = _stack_areas(approved_value)
        if approved != required_stack_areas:
            _add(
                problems,
                "stack checkpoint",
                "Approved areas must exactly match release-surface and gate applicability",
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
    ui_contract: str | None = None,
    eval_policy: str | None = None,
    platform_delivery: str | None = None,
    notes: list[str] | None = None,
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
        ui_contract=ui_contract,
        eval_policy=eval_policy,
        platform_delivery=platform_delivery,
        deltas_dir=prd_path.parent / "deltas",
        notes=notes,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prd", required=True, type=Path)
    parser.add_argument("--architecture", required=True, type=Path)
    parser.add_argument("--stack-decisions", required=True, type=Path)
    parser.add_argument("--require-filled", action="store_true")
    parser.add_argument("--require-approved", action="store_true")
    parser.add_argument(
        "--ui-contract",
        choices=CURRENT_UI_CONTRACTS,
        help="select the current wireframe-free PRD preflight",
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--eval-policy", choices=("eval-policy/1",))
    parser.add_argument(
        "--platform-delivery",
        choices=(PROTOCOL,),
        help="require the opt-in platform-delivery/1 architecture contract",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    notes: list[str] = []
    problems = validate(
        args.prd,
        args.architecture,
        args.stack_decisions,
        require_filled=args.require_filled,
        require_approved=args.require_approved,
        repo_root=args.repo_root,
        ui_contract=args.ui_contract,
        eval_policy=args.eval_policy,
        platform_delivery=args.platform_delivery,
        notes=notes,
    )
    for note in notes:
        print(f"INFO {note}")
    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        return 1
    if args.require_filled and args.require_approved:
        print("PASS core Product Definition package is complete and owner-approved")
    elif args.require_approved:
        print("PASS core Product Definition package approval checked (completeness not checked)")
    else:
        print("PASS core Product Definition package structure (approval not checked)")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())

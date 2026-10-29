#!/usr/bin/env python3
"""Join frozen product artifacts to the executable PLAN projection."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import math
import stat
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Any

from harness_git import GitMetadataError, _path_has_reparse_or_link, reject_object_substitution, run_git
from harness_schema import run_required_harness_version, version_at_least
from harness_ui_evidence import validate_ui_surface_design_registry
from delivery_acceptance_io import AcceptanceError, parse_required_prd_test_authority
from branch_policy import validate_branch_policy_join
from platform_delivery_contract import validate_feature_acceptance, validate_platform_delivery


FROZEN_SOURCE_STATUSES = {"frozen", "delta_accepted", "delta accepted"}
PRD_SOURCE_KINDS = {"prd", "product requirement", "product requirements"}
WIREFRAME_SOURCE_KINDS = {"wireframe", "wireframes", "approved wireframe"}
ARCHITECTURE_SOURCE_KINDS = {"architecture", "product architecture"}
DESIGN_SYSTEM_JSON_SOURCE_KINDS = {
    "design system json",
    "design system machine",
}
DESIGN_SYSTEM_MARKDOWN_SOURCE_KINDS = {
    "design system",
    "design system markdown",
}
JOINED_CONTRACT_FILENAMES = {
    "prd.md",
    "architecture.md",
    "stack-decisions.md",
    "ui-design.md",
    "wireframes.html",
    "design-system.md",
    "design-system.json",
}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
FULL_SHA_RE = re.compile(r"[0-9a-f]{40}")
PRD_UI_HEADING_RE = re.compile(
    r"^###\s+(UI-[A-Z0-9]+(?:-[A-Z0-9]+)*)\b.*$", re.MULTILINE
)
PRD_ROUTE_RE = re.compile(
    r"^\s*-\s*`route`\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
PRD_STATES_RE = re.compile(
    r"^\s*-\s*`states`\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
PRD_RESPONSIVE_RE = re.compile(
    r"^\s*-\s*`responsive`\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
PRD_MACHINE_BLOCK_RE = re.compile(
    r"<!--\s*ui-surface-contract:start\s*-->([\s\S]*?)"
    r"<!--\s*ui-surface-contract:end\s*-->",
    re.IGNORECASE,
)
PRD_ENGLISH_SECTION_RE = re.compile(
    r"^##\s+UI Surface Contract\s*$([\s\S]*?)(?=^##\s|\Z)",
    re.MULTILINE,
)
WIREFRAME_DATA_RE = re.compile(
    r'<script\s+id=["\']wireframe-data["\']\s+'
    r'type=["\']application/json["\']\s*>'
    r"([\s\S]*?)</script>",
    re.IGNORECASE,
)


def normalized_kind(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.replace("_", " ").replace("-", " ").casefold().split())


def frozen_sources(
    plan: dict[str, Any], *, kinds: set[str], filenames: set[str]
) -> list[dict[str, Any]]:
    """Select one artifact family without swallowing canonical sibling files."""

    if plan.get("schema_version") != 6:
        return []
    matches: list[dict[str, Any]] = []
    for source in plan.get("sources") or []:
        if (
            not isinstance(source, dict)
            or source.get("status") not in FROZEN_SOURCE_STATUSES
        ):
            continue
        location = str(source.get("location", "")).replace("\\", "/")
        filename = location.rsplit("/", 1)[-1].casefold()
        if filename in JOINED_CONTRACT_FILENAMES:
            matched = filename in filenames
        else:
            matched = normalized_kind(source.get("kind")) in kinds
        if matched:
            matches.append(source)
    return matches


def _strict_source_rows(
    plan: dict[str, Any], key: str
) -> tuple[list[dict[str, Any]], list[str]]:
    """Find one exact current source family for the 0.38 authority join.

    Matching both the declared kind and the canonical path family is
    intentional: a row with a right-looking filename but a wrong kind (or the
    reverse) is a contradictory source, not a second way to name the same
    contract.
    """

    spec = _STRICT_SOURCE_SPECS[key]
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    sources = plan.get("sources")
    if not isinstance(sources, list):
        return rows, errors
    for source in sources:
        if not isinstance(source, dict):
            continue
        location = source.get("location")
        kind = normalized_kind(source.get("kind"))
        if not isinstance(location, str):
            continue
        normalized = location.replace("\\", "/").strip()
        segments = normalized.split("/")
        if normalized != location.strip() or any(
            segment in {"", ".", ".."} for segment in segments
        ):
            errors.append(
                f"plan.sources: {key} source location must use canonical POSIX path segments"
            )
            rows.append(source)
            continue
        filename = normalized.rsplit("/", 1)[-1]
        canonical = str(spec["canonical"])
        if key == "approved-target":
            suffix = normalized[len(canonical) :] if normalized.startswith(canonical) else ""
            family_match = (
                normalized.startswith(canonical)
                and suffix.count("/") == 1
                and suffix.split("/", 1)[0]
                and filename == spec["filename"]
            )
        else:
            family_match = normalized == canonical
        kind_match = kind == spec["kind"]
        if not (family_match or kind_match):
            continue
        rows.append(source)
        if kind != spec["kind"]:
            errors.append(
                f"plan.sources: {key} source must use canonical kind "
                f"{spec['kind']!r}"
            )
        if not family_match:
            errors.append(
                f"plan.sources: {key} source location must be a canonical "
                f"{canonical} path"
            )
        if source.get("status") not in FROZEN_SOURCE_STATUSES:
            errors.append(
                f"plan.sources: {key} source must be frozen or delta_accepted"
            )
    if len(rows) > 1:
        errors.append(
            f"plan.sources: {key} requires exactly one frozen current source; "
            f"found {len(rows)}"
        )
    return rows, sorted(set(errors))


def _strict_source_inventory(plan: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    inventory: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []
    for key in _STRICT_SOURCE_SPECS:
        if key in {"eval-contract", "delivery-acceptance"}:
            continue  # Eval adoption owns these joins; legacy pins keep their source contract.
        rows, row_errors = _strict_source_rows(plan, key)
        inventory[key] = rows
        errors.extend(row_errors)
    return inventory, sorted(set(errors))


def _frozen_maintenance_record(plan: dict[str, Any], root: Path) -> tuple[bool, list[str]]:
    """A frozen task record can retain historical design for a small UI repair."""

    rows = [row for row in plan.get("sources", []) if isinstance(row, dict)
            and normalized_kind(row.get("kind")) == "task record"]
    if not rows:
        return False, []
    if len(rows) != 1:
        return False, ["plan.sources: maintenance needs exactly one frozen task record"]
    row = rows[0]
    location = row.get("location")
    if not isinstance(location, str) or re.fullmatch(r"docs/epics/EPIC-[A-Za-z0-9._-]+\.md", location) is None:
        return False, ["plan.sources: maintenance task record must be an Epic under docs/epics/"]
    if row.get("status") != "frozen" or not isinstance(row.get("source_revision"), str) or FULL_SHA_RE.fullmatch(row["source_revision"]) is None:
        return False, ["plan.sources: maintenance task record needs frozen status and a full Git source_revision"]
    payload, errors = _resolve_source_bytes(row, root, label="maintenance task record", strict=True)
    if errors or payload is None:
        return False, errors
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return False, ["plan.sources: maintenance task record must be UTF-8"]
    # Classification must be a live top-level line, not a sample in a code block.
    active = []
    fenced = False
    for line in text.splitlines():
        if re.match(r"^\s*(?:```|~~~)", line):
            fenced = not fenced
        elif not fenced:
            active.append(line)
    body = "\n".join(active)
    workflows = re.findall(r"^Design workflow:\s*(\S+)\s*$", body, re.M)
    impacts = re.findall(r"^UI impact:\s*(\S+)\s*$", body, re.M)
    if len(workflows) == 1 and workflows[0] in {"initial_design", "enhancement", "full_redesign"}:
        return False, []
    if workflows != ["maintenance"] or len(impacts) != 1 or impacts[0] not in {"none", "style"}:
        return False, ["plan.sources: maintenance task record needs Design workflow: maintenance and UI impact: none|style"]
    plan_ids = re.findall(r"^Plan ID:\s*(\S+)\s*$", body, re.M)
    objectives = re.findall(r"^Plan objective:\s*(.+?)\s*$", body, re.M)
    if plan_ids != [plan.get("plan_id")] or objectives != [plan.get("objective")]:
        return False, ["plan.sources: maintenance task record must bind the current PLAN ID and objective"]

    def references(field):
        values = re.findall(r"^" + re.escape(field) + r":\s*(.+?)\s*$", body, re.M)
        if len(values) != 1:
            return []
        return [item.strip().strip("`") for item in values[0].split(",") if item.strip()]

    record_refs = references("Requirement refs")
    record_surfaces = references("UI scope")
    if not record_refs or len(record_refs) != len(set(record_refs)) or not record_surfaces or len(record_surfaces) != len(set(record_surfaces)):
        return False, ["plan.sources: maintenance task record needs unique Requirement refs and UI scope"]
    ui_surfaces = [surface for surface in plan.get("ui_surfaces", []) if isinstance(surface, dict)]
    ui_refs = {ref for surface in ui_surfaces for ref in surface.get("trace_ids", []) if isinstance(ref, str)}
    active_refs = {ref for mission in plan.get("missions", []) if isinstance(mission, dict)
                   for ref in mission.get("trace_ids", []) if ref in ui_refs}
    active_surfaces = {surface.get("id") for surface in ui_surfaces
                       if any(ref in active_refs for ref in surface.get("trace_ids", []))}
    if set(record_refs) != active_refs or set(record_surfaces) != active_surfaces:
        return False, ["plan.sources: maintenance task record requirement refs and UI scope differ from current PLAN missions"]
    traces = {trace.get("id"): trace for trace in plan.get("traces", []) if isinstance(trace, dict)}
    if any(row.get("id") not in (traces.get(ref, {}).get("source_ids") or []) for ref in record_refs):
        return False, ["plan.sources: each maintenance requirement trace must reference the frozen task record source"]
    return True, []


def contract_values(value: str) -> list[str]:
    stripped = value.strip()
    try:
        decoded = json.loads(stripped)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, list) and all(isinstance(item, str) for item in decoded):
        return [item.strip() for item in decoded if item.strip()]
    if stripped.startswith("[") and stripped.endswith("]"):
        stripped = stripped[1:-1]
    return [
        item.strip().strip("`").strip()
        for item in stripped.split(",")
        if item.strip().strip("`").strip()
    ]


def normalized_state(value: str) -> str:
    state = value.strip().strip("`").strip()
    name, separator, marker = state.partition(":")
    if separator and marker.strip().casefold().startswith("n/a"):
        return f"{name.strip()}:n/a"
    return state


def normalized_responsive(
    value: str,
) -> tuple[str | None, list[str], str | None]:
    kind, separator, raw_values = value.strip().partition(":")
    if not separator or kind not in {"viewports", "sizeClasses"}:
        return (
            None,
            [],
            "must use `viewports: ...` for web or `sizeClasses: ...` "
            "for native or desktop",
        )
    values = contract_values(raw_values)
    normalized: list[str] = []
    if kind == "viewports":
        for item in values:
            try:
                number = float(item)
            except ValueError:
                return None, [], f"contains non-numeric viewport {item!r}"
            if not math.isfinite(number) or number <= 0:
                return None, [], f"contains invalid viewport {item!r}"
            normalized.append(str(int(number)) if number.is_integer() else str(number))
    else:
        normalized = values
    if len(normalized) < 2:
        return kind, normalized, "must declare at least two responsive targets"
    if len(normalized) != len(set(normalized)):
        return kind, normalized, "must not contain duplicate responsive targets"
    if kind == "viewports" and any(
        float(left) >= float(right)
        for left, right in zip(normalized, normalized[1:])
    ):
        return kind, normalized, "must list viewports in ascending order"
    return kind, normalized, None


# 0.55.1 is the release that adds the UI checker's dated current-HiFi rule
# to the UI and pair joins. A RUN frozen under 0.55.0 keeps its old meaning.
CURRENT_HIFI_EVIDENCE_VERSION = (0, 55, 1)


_STRICT_SOURCE_SPECS: dict[str, dict[str, Any]] = {
    "eval-contract": {
        "kind": "eval contract", "filename": "eval-contract.json",
        "canonical": "docs/verification/eval-contract.json",
    },
    "delivery-acceptance": {
        "kind": "delivery acceptance", "filename": "delivery-acceptance.json",
        "canonical": "docs/verification/delivery-acceptance.json",
    },
    "prd": {
        "kind": "prd",
        "filename": "prd.md",
        "canonical": "docs/product/PRD.md",
    },
    "architecture": {
        "kind": "architecture",
        "filename": "architecture.md",
        "canonical": "docs/product/architecture.md",
    },
    "stack": {
        "kind": "stack decisions",
        "filename": "stack-decisions.md",
        "canonical": "docs/product/stack-decisions.md",
    },
    "ui-design": {
        "kind": "ui design",
        "filename": "ui-design.md",
        "canonical": "docs/design/ui-design.md",
    },
    "wireframes": {
        "kind": "wireframe",
        "filename": "wireframes.html",
        "canonical": "docs/design/wireframes.html",
    },
    "approved-target": {
        "kind": "approved ui target",
        "filename": "index.html",
        "canonical": "docs/design/ui-references/",
    },
    "design-system.md": {
        "kind": "design system",
        "filename": "design-system.md",
        "canonical": "docs/design/design-system.md",
    },
    "design-system.json": {
        "kind": "design system json",
        "filename": "design-system.json",
        "canonical": "docs/design/design-system.json",
    },
    # Harness 0.59+ ui-design/3 packages also freeze the derived HTML package.
    "design-system-preview": {
        "kind": "design system preview",
        "filename": "design-system-preview.html",
        "canonical": "docs/design/design-system-preview.html",
    },
}
UI_DESIGN_V3_VERSION = (0, 59, 0)
CURRENT_UI_CONTRACTS = ("ui-design/2", "ui-design/3")
DESIGN_SYSTEM_SCHEMA_BY_UI = {"ui-design/3": "design-system/4", "ui-design/2": "design-system/3"}




def wireframe_free_required(run: dict[str, Any] | None) -> bool:
    """Only a pinned 0.56+ RUN selects the new UI source family."""
    return bool(isinstance(run, dict) and version_at_least(
        run_required_harness_version(run), (0, 56, 0)))


def ui_design_v3_required(run: dict[str, Any] | None) -> bool:
    """A pinned 0.59+ RUN requires ui-design/3 for new full UI delivery."""
    return bool(isinstance(run, dict) and version_at_least(
        run_required_harness_version(run), UI_DESIGN_V3_VERSION))


def _ui_contract_version_errors(version: str, *, run: dict[str, Any] | None, current: bool,
                                retained: bool) -> list[str]:
    """Select the one UI contract a RUN may consume."""
    if not current:
        return [] if version == "legacy" else [f"ui-design: pinned legacy RUN cannot consume {version}"]
    if version not in CURRENT_UI_CONTRACTS:
        return ["ui-design: Harness 0.56+ requires UI contract: ui-design/2"]
    if run is None:
        return []  # PLAN-only checks accept either current contract.
    if ui_design_v3_required(run):
        if version == "ui-design/2" and not retained:
            return ["ui-design: Harness 0.59+ new full UI delivery requires UI contract: ui-design/3"]
        return []
    return ["ui-design: pinned pre-0.59 RUN cannot consume ui-design/3"] if version == "ui-design/3" else []


def _frozen_preview_errors(inventory: dict[str, list[dict[str, Any]]], paths: dict[str, Path],
                           root: Path) -> list[str]:
    """ui-design/3 freezes exactly one derived HTML package equal to a fresh render."""
    if len(inventory["design-system-preview"]) != 1:
        return ["plan.sources: ui-design/3 requires exactly one frozen design-system-preview.html"]
    if not all(key in paths for key in ("design-system-preview", "design-system.md", "design-system.json")):
        return []
    scripts = Path(__file__).resolve().parents[2] / "design-system-compiler" / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        from render_design_system_preview import render_view
        expected = render_view(paths["design-system.json"].read_bytes(), paths["design-system.md"].read_bytes(), root)
    except Exception as exc:
        return [f"design-system: cannot render the frozen HTML package: {type(exc).__name__}: {exc}"]
    finally:
        try:
            sys.path.remove(str(scripts))
        except ValueError:
            pass
    if paths["design-system-preview"].read_bytes() != expected.encode("utf-8"):
        return ["plan.sources: frozen design-system-preview.html is stale or modified; regenerate it from the frozen pair"]
    return []


def web_viewport_floor_required(run: dict[str, Any] | None) -> bool:
    """Current joins require three responsive targets; older pins use their bundle."""
    return True


def prd_web_viewport_floor_errors(prd_text: str) -> list[str]:
    """Floor errors for web responsive sets in the PRD UI surface anchors."""

    errors: list[str] = []
    entries, _ = parse_prd_ui_contract(prd_text)
    for surface_id in sorted(entries):
        entry = entries[surface_id]
        targets = entry["responsiveTargets"]
        if entry["responsiveKind"] == "viewports" and len(targets) < 3:
            errors.append(
                f"prd: UI surface {surface_id} `responsive` web responsive set "
                "needs at least three ascending viewports (harness 0.34.0+)"
            )
    return errors


def registry_web_viewport_floor_errors(registry: dict[str, Any]) -> list[str]:
    """Floor error for the design-system registry's web responsive set."""

    viewports = registry.get("viewports")
    if isinstance(viewports, list) and len(viewports) < 3:
        return [
            "design_system: web responsive set needs at least three ascending "
            "viewports (harness 0.34.0+)"
        ]
    return []


def breakpoint_matches_viewport(breakpoint: str, viewport: str) -> bool:
    return re.search(rf"(?:^|[-_\s]){re.escape(viewport)}$", breakpoint) is not None


def parse_prd_ui_contract(
    prd_text: str,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Read invariant UI IDs, routes, states, and responsive sets from a PRD."""

    blocks = list(PRD_MACHINE_BLOCK_RE.finditer(prd_text))
    start_count = len(
        re.findall(r"<!--\s*ui-surface-contract:start\s*-->", prd_text, re.I)
    )
    end_count = len(
        re.findall(r"<!--\s*ui-surface-contract:end\s*-->", prd_text, re.I)
    )
    legacy_block = PRD_ENGLISH_SECTION_RE.search(prd_text)
    has_ui_entry = PRD_UI_HEADING_RE.search(prd_text) is not None
    if not blocks and not (start_count or end_count or has_ui_entry):
        return {}, []
    errors: list[str] = []
    if len(blocks) != 1 or start_count != 1 or end_count != 1:
        errors.append(
            "prd: UI surface contract requires exactly one matched "
            "ui-surface-contract boundary pair"
        )
    if blocks:
        body = blocks[0].group(1)
    elif legacy_block is not None:
        body = legacy_block.group(1)
    else:
        body = prd_text
    all_headings = list(PRD_UI_HEADING_RE.finditer(prd_text))
    if len(blocks) == 1:
        body_start = blocks[0].start(1)
        body_end = blocks[0].end(1)
        outside_ids = sorted(
            {
                heading.group(1)
                for heading in all_headings
                if not body_start <= heading.start() < body_end
            }
        )
        if outside_ids:
            errors.append(
                "prd: UI surface headings outside the ui-surface-contract boundary: "
                + ", ".join(outside_ids)
            )
    headings = list(PRD_UI_HEADING_RE.finditer(body))
    if blocks and not headings:
        errors.append("prd: ui-surface-contract boundary contains no UI surface entries")
    entries: dict[str, dict[str, Any]] = {}
    for index, heading in enumerate(headings):
        surface_id = heading.group(1)
        if surface_id in entries:
            errors.append(f"prd: duplicate UI surface heading {surface_id}")
            continue
        block_end = (
            headings[index + 1].start() if index + 1 < len(headings) else len(body)
        )
        surface_block = body[heading.end() : block_end]
        route_matches = list(PRD_ROUTE_RE.finditer(surface_block))
        states_matches = list(PRD_STATES_RE.finditer(surface_block))
        responsive_matches = list(PRD_RESPONSIVE_RE.finditer(surface_block))
        routes = (
            contract_values(route_matches[0].group(1))
            if len(route_matches) == 1
            else []
        )
        states = (
            [
                normalized_state(item)
                for item in contract_values(states_matches[0].group(1))
            ]
            if len(states_matches) == 1
            else []
        )
        if len(route_matches) != 1:
            errors.append(
                f"prd: UI surface {surface_id} requires exactly one `route` anchor; "
                f"found {len(route_matches)}"
            )
        if len(routes) != 1:
            errors.append(
                f"prd: UI surface {surface_id} requires exactly one route value; "
                f"found {len(routes)}"
            )
        if len(states_matches) != 1:
            errors.append(
                f"prd: UI surface {surface_id} requires exactly one `states` anchor; "
                f"found {len(states_matches)}"
            )
        if not states:
            errors.append(f"prd: UI surface {surface_id} has no states value")
        responsive_kind: str | None = None
        responsive_targets: list[str] = []
        if len(responsive_matches) != 1:
            errors.append(
                f"prd: UI surface {surface_id} requires exactly one `responsive` "
                f"anchor; found {len(responsive_matches)}"
            )
        else:
            responsive_kind, responsive_targets, responsive_error = normalized_responsive(
                responsive_matches[0].group(1)
            )
            if responsive_error:
                errors.append(
                    f"prd: UI surface {surface_id} `responsive` {responsive_error}"
                )
        entries[surface_id] = {
            "routes": routes,
            "states": states,
            "responsiveKind": responsive_kind,
            "responsiveTargets": responsive_targets,
        }
    return entries, errors


def parse_wireframe_data(
    html: str, *, label: str = "wireframes"
) -> tuple[dict[str, Any] | None, list[str]]:
    match = WIREFRAME_DATA_RE.search(html)
    if match is None:
        return None, [f"{label}: has no wireframe-data JSON block"]
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return None, [f"{label}: wireframe-data is invalid JSON: {exc}"]
    if not isinstance(data, dict):
        return None, [f"{label}: wireframe-data must be a JSON object"]
    return data, []


def _plan_surfaces(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        surface.get("id"): surface
        for surface in (plan.get("ui_surfaces") or [])
        if isinstance(surface, dict) and isinstance(surface.get("id"), str)
    }


def validate_plan_prd_text(
    plan: dict[str, Any],
    prd_text: str,
    *,
    parser: Any | None = None,
) -> list[str]:
    """Join PLAN surfaces to PRD UI anchors using the selected parser.

    Legacy schema joins keep the local compatibility parser.  Harness 0.38
    passes the sibling Product Definition Builder parser explicitly so fenced
    or commented examples cannot become executable UI authority.
    """

    parse = parser or parse_prd_ui_contract
    parsed = parse(prd_text)
    if not isinstance(parsed, tuple) or len(parsed) != 2:
        raise ValueError("canonical PRD UI parser returned an invalid result")
    prd_surfaces, errors = parsed
    if not isinstance(prd_surfaces, dict) or not isinstance(errors, list):
        raise ValueError("canonical PRD UI parser returned invalid surfaces/errors")
    plan_surfaces = _plan_surfaces(plan)
    prd_ids = set(prd_surfaces)
    plan_ids = set(plan_surfaces)
    missing = sorted(prd_ids - plan_ids)
    extra = sorted(plan_ids - prd_ids)
    if missing:
        errors.append(
            "plan.ui_surfaces: PRD surfaces absent from the PLAN: " + ", ".join(missing)
        )
    if extra:
        errors.append(
            "plan.ui_surfaces: PLAN surfaces absent from the PRD UI contract: "
            + ", ".join(extra)
        )
    for surface_id in sorted(prd_ids & plan_ids):
        plan_surface = plan_surfaces[surface_id]
        prd_surface = prd_surfaces[surface_id]
        routes = prd_surface["routes"]
        if len(routes) == 1 and plan_surface.get("route") != routes[0]:
            errors.append(
                f"plan.ui_surfaces: surface {surface_id} route "
                f"{plan_surface.get('route')!r} differs from the PRD route {routes[0]!r}"
            )
        plan_states = {
            normalized_state(state)
            for state in (plan_surface.get("states") or [])
            if isinstance(state, str)
        }
        prd_states = set(prd_surface["states"])
        if plan_states != prd_states:
            errors.append(
                f"plan.ui_surfaces: surface {surface_id} states "
                f"{sorted(plan_states)} differ from the PRD states {sorted(prd_states)}"
            )
        plan_breakpoints = [
            value.strip()
            for value in (plan_surface.get("breakpoints") or [])
            if isinstance(value, str) and value.strip()
        ]
        responsive_kind = prd_surface["responsiveKind"]
        responsive_targets = prd_surface["responsiveTargets"]
        if responsive_kind == "viewports":
            missing = [
                target
                for target in responsive_targets
                if not any(
                    breakpoint_matches_viewport(breakpoint, target)
                    for breakpoint in plan_breakpoints
                )
            ]
            extras = [
                breakpoint
                for breakpoint in plan_breakpoints
                if not any(
                    breakpoint_matches_viewport(breakpoint, target)
                    for target in responsive_targets
                )
            ]
        elif responsive_kind == "sizeClasses":
            missing = sorted(set(responsive_targets) - set(plan_breakpoints))
            extras = sorted(set(plan_breakpoints) - set(responsive_targets))
        else:
            missing = []
            extras = []
        if responsive_kind and (
            missing or extras or len(plan_breakpoints) != len(responsive_targets)
        ):
            errors.append(
                f"plan.ui_surfaces: surface {surface_id} breakpoints "
                f"{sorted(plan_breakpoints)} differ from the PRD responsive targets "
                f"{responsive_kind} {sorted(responsive_targets)}"
            )
    return errors


def validate_plan_security_requirements(
    plan: dict[str, Any], security_contract: Any
) -> list[str]:
    """Join a validated PRD security contract to existing PLAN coverage."""

    errors: list[str] = []
    if not isinstance(plan, dict):
        errors.append("security requirements: plan must be an object")
    if not isinstance(security_contract, dict):
        errors.append("security requirements: parser contract must be an object")
        return errors

    status = security_contract.get("status")
    scope = security_contract.get("scope")
    if not isinstance(status, str) or status not in {
        "required",
        "not_required",
        "blocked",
    }:
        errors.append(
            "security requirements: contract status must be "
            "required, not_required, or blocked"
        )
    if not isinstance(scope, str) or scope not in {
        "executable",
        "documentation_only",
    }:
        errors.append(
            "security requirements: contract scope must be "
            "executable or documentation_only"
        )

    requirements = security_contract.get("requirements")
    if not isinstance(requirements, list):
        errors.append("security requirements: requirements must be a list")
        return errors

    parsed_requirements: list[tuple[str, list[str]]] = []
    seen_requirement_ids: set[str] = set()
    for index, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            errors.append(
                f"security requirements: requirements[{index}] must be an object"
            )
            continue
        prd_id = requirement.get("prd_id")
        test_ids = requirement.get("test_ids")
        if (
            not isinstance(prd_id, str)
            or re.fullmatch(r"PRD-[A-Z0-9-]+", prd_id) is None
        ):
            errors.append(
                f"security requirements: requirements[{index}].prd_id "
                "must be a valid PRD ID"
            )
            continue
        if prd_id in seen_requirement_ids:
            errors.append(
                f"security requirements: {prd_id} appears more than once in the PRD"
            )
            continue
        if not isinstance(test_ids, list):
            errors.append(
                f"security requirements: {prd_id} test_ids must be a list"
            )
            continue
        valid_test_ids = [
            test_id
            for test_id in test_ids
            if isinstance(test_id, str)
            and re.fullmatch(r"TEST-[A-Z0-9-]+", test_id) is not None
        ]
        if (
            not valid_test_ids
            or len(valid_test_ids) != len(test_ids)
            or len(valid_test_ids) != len(set(valid_test_ids))
        ):
            errors.append(
                f"security requirements: {prd_id} test_ids must contain "
                "unique valid TEST IDs"
            )
            continue
        seen_requirement_ids.add(prd_id)
        parsed_requirements.append((prd_id, valid_test_ids))

    if status == "not_required":
        if scope != "documentation_only":
            errors.append(
                "security requirements: not_required scope must be documentation_only"
            )
        if requirements:
            errors.append(
                "security requirements: not_required contract must have no rows"
            )
        return errors
    if status == "blocked":
        errors.append("security requirements: blocked contract must block execution")
        return errors
    if status != "required" or errors:
        return errors
    if not parsed_requirements:
        errors.append(
            "security requirements: required contract must contain at least one row"
        )
        return errors
    if not isinstance(plan, dict):
        return errors

    try:
        evidence_valid = _load_product_security_attribute(
            sibling_builder_scripts_dir(), "security_negative_evidence_valid"
        )
    except Exception as exc:
        return [f"security requirements: negative-evidence validator failed safely: {exc}"]
    if not callable(evidence_valid):
        return ["security requirements: canonical negative-evidence validator is unavailable"]

    traces = plan.get("traces")
    missions = plan.get("missions")
    if not isinstance(traces, list):
        errors.append("security requirements: plan.traces must be a list")
    if not isinstance(missions, list):
        errors.append("security requirements: plan.missions must be a list")
    if not isinstance(traces, list) or not isinstance(missions, list):
        return errors

    tasks: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for mission_index, mission in enumerate(missions):
        if not isinstance(mission, dict):
            errors.append(
                f"security requirements: missions[{mission_index}] must be an object"
            )
            continue
        if not isinstance(mission.get("trace_ids"), list):
            errors.append(
                f"security requirements: missions[{mission_index}].trace_ids "
                "must be a list"
            )
        mission_tasks = mission.get("tasks")
        if not isinstance(mission_tasks, list):
            errors.append(
                f"security requirements: missions[{mission_index}].tasks "
                "must be a list"
            )
            continue
        for task in mission_tasks:
            if not isinstance(task, dict):
                errors.append(
                    f"security requirements: missions[{mission_index}].tasks "
                    "entries must be objects"
                )
                continue
            if not isinstance(task.get("trace_ids"), list):
                task_id = task.get("id")
                task_label = task_id if isinstance(task_id, str) else "<unknown>"
                errors.append(
                    f"security requirements: task {task_label} trace_ids "
                    "must be a list"
                )
            tasks.append((mission, task))

    for trace_index, trace in enumerate(traces):
        if not isinstance(trace, dict):
            errors.append(
                f"security requirements: traces[{trace_index}] must be an object"
            )

    def trace_ids(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]

    for prd_id, required_tests in parsed_requirements:
        matching_traces = [
            trace
            for trace in traces
            if isinstance(trace, dict) and trace.get("id") == prd_id
        ]
        if not matching_traces:
            errors.append(
                f"security requirements: {prd_id} must appear exactly once in plan.traces"
            )
            continue
        if len(matching_traces) != 1:
            errors.append(
                f"security requirements: {prd_id} appears "
                f"{len(matching_traces)} times in plan.traces"
            )
            continue

        trace = matching_traces[0]
        disposition = trace.get("disposition")
        if (
            not isinstance(disposition, str)
            or disposition not in ("planned", "deferred", "out_of_scope")
        ):
            errors.append(
                f"security requirements: {prd_id} trace has no explicit supported disposition"
            )
            continue

        carrying_missions = [
            mission
            for mission in missions
            if isinstance(mission, dict) and prd_id in trace_ids(mission.get("trace_ids"))
        ]
        carrying_tasks = [
            (mission, task)
            for mission, task in tasks
            if prd_id in trace_ids(task.get("trace_ids"))
        ]

        for test_id in required_tests:
            for _mission, task in tasks:
                if prd_id in trace_ids(task.get("trace_ids")):
                    continue
                acceptance = task.get("acceptance_matrix")
                if not isinstance(acceptance, list):
                    continue
                if any(
                    isinstance(row, dict) and row.get("test_id") == test_id
                    for row in acceptance
                ):
                    errors.append(
                        f"security requirements: {test_id} is used by a task "
                        f"that does not carry {prd_id}"
                    )

        if disposition != "planned":
            rationale = trace.get("rationale")
            if not isinstance(rationale, str) or not rationale.strip():
                errors.append(
                    f"security requirements: {prd_id} {disposition} rationale is required"
                )
            if carrying_missions or carrying_tasks:
                errors.append(
                    f"security requirements: {prd_id} {disposition} must not be "
                    "carried by an executable mission or task"
                )
            continue

        if not carrying_tasks:
            errors.append(
                f"security requirements: planned {prd_id} has no carrying task"
            )
            continue

        for _mission, task in carrying_tasks:
            verifiers = task.get("verifiers")
            if not isinstance(verifiers, list) or not verifiers:
                errors.append(
                    f"security requirements: task carrying {prd_id} must declare a verifier"
                )
            task_id = task.get("id")
            task_label = task_id if isinstance(task_id, str) else "<unknown>"
            acceptance = task.get("acceptance_matrix")
            if not isinstance(acceptance, list):
                errors.append(
                    f"security requirements: task {task_label} acceptance_matrix "
                    "must be a list"
                )
                continue
            for test_id in required_tests:
                matching_rows = [
                    row for row in acceptance if isinstance(row, dict)
                    and row.get("test_id") == test_id
                    and prd_id in trace_ids(row.get("trace_ids"))
                ]
                if not matching_rows:
                    errors.append(
                        f"security requirements: planned {prd_id} task {task_label} "
                        f"is missing required security {test_id} on its acceptance row"
                    )
                for row in matching_rows:
                    if not evidence_valid(row.get("criterion")):
                        errors.append(
                            f"security requirements: {test_id} task {task_label} criterion "
                            "must declare denial: rejected (observable signal); no unauthorized "
                            "side effects: unchanged (observable state evidence)"
                        )

    return errors


def product_security_requirements_join_errors(
    plan: dict[str, Any],
    prd_text: str,
    *,
    parser: Any = None,
    sibling_scripts: Path | None = None,
    parser_required: bool = False,
) -> list[str]:
    """Parse frozen PRD security authority and join it to the PLAN."""

    if parser is None:
        if not parser_required:
            return []
        scripts = sibling_scripts or sibling_builder_scripts_dir()
        try:
            parser = _load_product_security_requirements_parser(scripts)
        except Exception as exc:
            return [
                "security requirements: canonical parser loader failed safely: "
                f"{type(exc).__name__}: {exc}"
            ]
        if parser is None:
            return [
                "security requirements: canonical parser is unavailable — install "
                "product-definition-builder next to delivery-harness"
            ]

    if not callable(parser):
        return ["security requirements: canonical parser is not callable"]
    try:
        parsed = parser(prd_text)
    except Exception as exc:
        return [
            "security requirements: canonical parser failed safely: "
            f"{type(exc).__name__}: {exc}"
        ]
    if not isinstance(parsed, tuple) or len(parsed) != 2:
        return ["security requirements: canonical parser returned an invalid result"]
    security_contract, parser_errors = parsed
    if not isinstance(parser_errors, list) or any(
        not isinstance(error, str) for error in parser_errors
    ):
        return ["security requirements: canonical parser returned invalid errors"]
    if parser_errors:
        return list(parser_errors)

    errors: list[str] = []
    try:
        errors.extend(validate_plan_security_requirements(plan, security_contract))
    except Exception as exc:
        errors.append(
            "security requirements: PLAN join failed safely: "
            f"{type(exc).__name__}: {exc}"
        )
    return errors


def _wireframe_screens(
    data: dict[str, Any], *, label: str = "wireframes"
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    screens_by_id: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    screens = data.get("screens")
    if not isinstance(screens, list):
        return {}, [f"{label}: wireframe-data.screens must be a list"]
    for screen in screens:
        if not isinstance(screen, dict) or not isinstance(screen.get("id"), str):
            continue
        screen_id = screen["id"]
        if screen_id in screens_by_id:
            errors.append(f"{label}: duplicate screen id {screen_id}")
        screens_by_id[screen_id] = screen
    return screens_by_id, errors


def _screen_states(screen: dict[str, Any]) -> set[str]:
    return {
        normalized_state(state["id"])
        for state in (screen.get("states") or [])
        if isinstance(state, dict) and isinstance(state.get("id"), str)
    }


def validate_plan_wireframe_data(
    plan: dict[str, Any], data: dict[str, Any]
) -> list[str]:
    plan_surfaces = _plan_surfaces(plan)
    screens, errors = _wireframe_screens(data)
    responsive_kind = "viewports" if "viewports" in data else "sizeClasses"
    responsive_targets = [
        str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
        for value in (data.get(responsive_kind) or [])
    ]
    for missing in sorted(set(plan_surfaces) - set(screens)):
        errors.append(f"plan.ui_surfaces: surface {missing} has no wireframes.html screen")
    for extra in sorted(set(screens) - set(plan_surfaces)):
        errors.append(f"wireframes: screen {extra} is absent from the PLAN ui_surfaces")
    for surface_id in sorted(set(plan_surfaces) & set(screens)):
        surface = plan_surfaces[surface_id]
        screen = screens[surface_id]
        if surface.get("route") != screen.get("route"):
            errors.append(
                f"plan.ui_surfaces: surface {surface_id} route "
                f"{surface.get('route')!r} differs from the wireframe route "
                f"{screen.get('route')!r}"
            )
        plan_states = {
            normalized_state(state)
            for state in (surface.get("states") or [])
            if isinstance(state, str)
        }
        wireframe_states = _screen_states(screen)
        if plan_states != wireframe_states:
            errors.append(
                f"plan.ui_surfaces: surface {surface_id} states "
                f"{sorted(plan_states)} differ from the wireframe states "
                f"{sorted(wireframe_states)}"
            )
        plan_breakpoints = [
            value.strip()
            for value in (surface.get("breakpoints") or [])
            if isinstance(value, str) and value.strip()
        ]
        if responsive_kind == "viewports":
            matches = (
                len(plan_breakpoints) == len(responsive_targets)
                and all(
                    any(
                        breakpoint_matches_viewport(breakpoint, target)
                        for breakpoint in plan_breakpoints
                    )
                    for target in responsive_targets
                )
            )
        else:
            matches = set(plan_breakpoints) == set(responsive_targets) and len(
                plan_breakpoints
            ) == len(responsive_targets)
        if not matches:
            errors.append(
                f"plan.ui_surfaces: surface {surface_id} breakpoints "
                f"{sorted(plan_breakpoints)} differ from the wireframe responsive "
                f"targets {responsive_kind} {sorted(responsive_targets)}"
            )
    return errors


def required_design_system_source_errors(plan: dict[str, Any]) -> list[str]:
    """Require both frozen design-system rows when either half is in scope."""

    if plan.get("schema_version") != 6:
        return []
    design_json_sources = frozen_sources(
        plan,
        kinds=DESIGN_SYSTEM_JSON_SOURCE_KINDS,
        filenames={"design-system.json"},
    )
    design_markdown_sources = frozen_sources(
        plan,
        kinds=DESIGN_SYSTEM_MARKDOWN_SOURCE_KINDS,
        filenames={"design-system.md"},
    )
    has_ds_trace = any(
        isinstance(trace, dict)
        and isinstance(trace.get("id"), str)
        and trace["id"].startswith("DS-")
        for trace in (plan.get("traces") or [])
    )
    if (has_ds_trace or design_json_sources or design_markdown_sources) and (
        len(design_json_sources) != 1 or len(design_markdown_sources) != 1
    ):
        return [
            "plan.sources: design-system work requires one frozen design-system.md row "
            "and one frozen design-system.json row"
        ]
    return []


def _resolve_source_bytes(
    source: dict[str, Any],
    repo_root: str | Path,
    *,
    label: str,
    strict: bool = False,
) -> tuple[bytes | None, list[str]]:
    expected_hash = source.get("content_sha256")
    if not isinstance(expected_hash, str) or SHA256_RE.fullmatch(expected_hash) is None:
        return None, [
            f"plan.sources: frozen {label} contract source requires content_sha256"
        ]
    location = source.get("location")
    if (
        not isinstance(location, str)
        or not location.strip()
        or "://" in location
        or location.startswith(("/", "\\"))
        or bool(PureWindowsPath(location).drive)
        or "\\" in location
    ):
        return None, [
            f"plan.sources: frozen {label} join requires a repository-relative POSIX path"
        ]
    path_parts = location.split("/")
    if location != location.strip() or any(
        part in {"", ".", ".."} for part in path_parts
    ):
        return None, [
            f"plan.sources: frozen {label} join requires canonical POSIX path segments"
        ]
    root = Path(repo_root).resolve()
    source_candidate = root / location
    source_path = source_candidate.resolve()
    try:
        relative = source_path.relative_to(root).as_posix()
    except ValueError:
        return None, [f"plan.sources: frozen {label} path resolves outside --repo-root"]
    # A frozen authority must be a real file below the root, not a symlink
    # whose target can change independently of the recorded path.
    if strict:
        cursor = root
        for component in path_parts:
            cursor = cursor / component
            try:
                component_stat = cursor.stat(follow_symlinks=False)
            except (OSError, TypeError) as exc:
                return None, [
                    f"plan.sources: cannot inspect frozen {label} path component ({exc})"
                ]
            attributes = getattr(component_stat, "st_file_attributes", 0)
            if stat.S_ISLNK(component_stat.st_mode) or bool(
                attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            ):
                return None, [
                    f"plan.sources: frozen {label} path must not traverse a symlink or reparse point"
                ]
    revision = source.get("source_revision")
    current_contents: bytes | None = None
    if strict:
        if not source_path.is_file():
            return None, [f"plan.sources: cannot read frozen {label} source"]
        try:
            current_contents = source_path.read_bytes()
        except OSError as exc:
            return None, [f"plan.sources: cannot read frozen {label} source ({exc})"]
    if isinstance(revision, str) and revision:
        if FULL_SHA_RE.fullmatch(revision) is None:
            return None, [
                f"plan.sources: frozen {label} source_revision must be a full Git SHA"
            ]
        try:
            reject_object_substitution(root)
            result = run_git(
                root,
                "show",
                f"{revision}:{relative}",
                text=False,
                timeout=30,
            )
        except (GitMetadataError, OSError, subprocess.SubprocessError) as exc:
            return None, [
                f"plan.sources: cannot read frozen {label} bytes at "
                f"{revision}:{relative} ({exc})"
            ]
        if result.returncode != 0:
            return None, [
                f"plan.sources: cannot read frozen {label} bytes at {revision}:{relative}"
            ]
        contents = result.stdout
        if strict and current_contents != contents:
            return None, [
                f"plan.sources: frozen {label} current bytes differ from "
                f"source_revision {revision}"
            ]
    else:
        if current_contents is not None:
            contents = current_contents
        else:
            try:
                contents = source_path.read_bytes()
            except OSError as exc:
                return None, [f"plan.sources: cannot read frozen {label} source ({exc})"]
    actual_hash = hashlib.sha256(contents).hexdigest()
    if actual_hash != expected_hash:
        return None, [
            f"plan.sources: frozen {label} bytes do not match content_sha256 "
            f"(expected {expected_hash}, actual {actual_hash})"
        ]
    if strict and label == "approved UI target" and isinstance(revision, str) and revision:
        # The entry hash binds the page manifest; read children from that same
        # historical revision as well as checking their current bytes.
        try:
            html = contents.decode("utf-8")
            matches = list(re.finditer(
                r'<script\s+id=["\']ui-hifi-manifest["\']\s+type=["\']application/json["\']\s*>([\s\S]*?)</script>',
                html, re.IGNORECASE,
            ))
            manifest = json.loads(matches[0].group(1)) if len(matches) == 1 else None
            if isinstance(manifest, dict) and manifest.get("schema") == "ui-hifi/2":
                pages = manifest.get("pages")
                if not isinstance(pages, list):
                    raise ValueError("HiFi pages must be an array")
                for page in pages:
                    if not isinstance(page, dict) or not isinstance(page.get("path"), str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*\.html", page["path"]) is None:
                        raise ValueError("HiFi page path must be a sibling HTML filename")
                    child_location = (Path(location).parent / page["path"]).as_posix()
                    tree = run_git(root, "ls-tree", revision, "--", child_location, text=True, timeout=30)
                    if tree.returncode or not re.match(r"100(?:644|755) blob [0-9a-f]+\t", tree.stdout):
                        raise ValueError(f"HiFi page must be a regular tracked blob at source_revision: {child_location}")
                    _, child_errors = _resolve_source_bytes(
                        {"location": child_location, "content_sha256": page.get("sha256"), "source_revision": revision},
                        root, label="HiFi page", strict=True,
                    )
                    if child_errors:
                        return None, child_errors
        except (OSError, UnicodeError, ValueError, GitMetadataError, subprocess.SubprocessError) as exc:
            return None, [f"plan.sources: cannot verify HiFi pages at source_revision ({exc})"]
    return contents, []


_FULL_WIREFRAME_CHECKERS: dict[Path, Any] = {}
_FULL_UI_DESIGN_CHECKERS: dict[Path, Any] = {}
_FULL_PRODUCT_PACKAGE_CHECKERS: dict[Path, Any] = {}
_PRODUCT_SECURITY_REQUIREMENT_PARSERS: dict[Path, Any] = {}
_FULL_DESIGN_SYSTEM_CHECKERS: dict[Path, Any] = {}
_UI_CONTRACT_VIEWS: dict[Path, Any] = {}
_SIBLING_MODULES: dict[tuple[Path, str], Any] = {}


def sibling_builder_scripts_dir() -> Path:
    """The product-definition-builder scripts dir shipped next to this skill."""

    return Path(__file__).resolve().parents[2] / "product-definition-builder" / "scripts"


def _load_sibling(
    sibling_scripts: Path,
    module_name: str,
    aliases: tuple[str, ...] = ("markdown_contract",),
) -> Any:
    """Load one Product Definition module under a private name, or return None.

    The sibling module imports its helpers by top-level name. Each alias is
    loaded first from the verified sibling directory and bound to that import
    name only while the module executes, so a same-name module already in the
    host process is never used. Results are cached per directory and module.
    """

    key = sibling_scripts.resolve()
    if (key, module_name) in _SIBLING_MODULES:
        return _SIBLING_MODULES[(key, module_name)]
    names = (*aliases, module_name)
    paths = {name: key / f"{name}.py" for name in names}
    module: Any = None
    if all(candidate.is_file() for candidate in paths.values()):
        tag = hashlib.sha256(str(key).encode("utf-8")).hexdigest()[:16]
        private = {name: f"_harness_sibling_{name}_{tag}" for name in names}
        previous = {name: sys.modules.get(name) for name in aliases}
        try:
            for name in names:
                spec = importlib.util.spec_from_file_location(private[name], paths[name])
                if spec is None or spec.loader is None:
                    raise ImportError("canonical sibling module spec is unavailable")
                loaded = importlib.util.module_from_spec(spec)
                sys.modules[private[name]] = loaded
                if name in aliases:
                    sys.modules[name] = loaded
                spec.loader.exec_module(loaded)
            if Path(str(getattr(loaded, "__file__", ""))).resolve() != paths[module_name].resolve():
                raise ImportError("canonical sibling module path does not match sibling source")
            module = loaded
        except Exception:
            module = None
        finally:
            for name, before in previous.items():
                if before is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = before
            for name in names:
                sys.modules.pop(private[name], None)
    _SIBLING_MODULES[(key, module_name)] = module
    return module


def _load_release_source_contract(sibling_scripts: Path) -> Any:
    """Load the canonical active-Markdown release parser without host aliasing."""

    return _load_sibling(sibling_scripts, "release_targets")


def _load_canonical_prd_ui_contract_parser(sibling_scripts: Path) -> Any:
    """Load the Product Definition Builder's active-Markdown UI parser safely.

    Harness can be installed without its sibling skills.  The strict 0.38
    authority join therefore fails closed when this parser is unavailable;
    it must never fall back to the legacy regex parser for an executable join.
    """

    module = _load_sibling(sibling_scripts, "prd_ui_contract")
    return getattr(module, "parse_prd_ui_contract", None)


def _load_platform_delivery_parser(sibling_scripts: Path) -> Any:
    """Load Product Definition's canonical platform-delivery parser safely."""

    return _load_sibling(
        sibling_scripts, "platform_delivery", ("markdown_contract", "release_targets")
    )


def sibling_ui_design_scripts_dir() -> Path:
    """The ui-design-builder scripts dir shipped next to this skill."""

    return Path(__file__).resolve().parents[2] / "ui-design-builder" / "scripts"


def _load_full_wireframe_checker(sibling_scripts: Path) -> Any:
    """Import the sibling skill's canonical checker once per resolved dir."""

    key = sibling_scripts
    if key in _FULL_WIREFRAME_CHECKERS:
        return _FULL_WIREFRAME_CHECKERS[key]
    checker: Any = None
    if (key / "check_wireframe_html.py").is_file():
        sys.path.insert(0, str(key))
        try:
            import check_wireframe_html as checker_module
        finally:
            try:
                sys.path.remove(str(key))
            except ValueError:
                pass
        checker = checker_module.validate
    _FULL_WIREFRAME_CHECKERS[key] = checker
    return checker


def _load_full_ui_design_checker(sibling_scripts: Path) -> Any:
    """Import ui-design-builder's canonical package checker once."""

    key = sibling_scripts
    if key in _FULL_UI_DESIGN_CHECKERS:
        return _FULL_UI_DESIGN_CHECKERS[key]
    checker: Any = None
    if (key / "check_ui_design_contract.py").is_file():
        sys.path.insert(0, str(key))
        try:
            import check_ui_design_contract as checker_module
        finally:
            try:
                sys.path.remove(str(key))
            except ValueError:
                pass
        checker = checker_module.validate
    _FULL_UI_DESIGN_CHECKERS[key] = checker
    return checker


def _load_full_product_package_checker(sibling_scripts: Path) -> Any:
    """Import the sibling skill's canonical core-package checker once."""

    key = sibling_scripts
    if key in _FULL_PRODUCT_PACKAGE_CHECKERS:
        return _FULL_PRODUCT_PACKAGE_CHECKERS[key]
    checker: Any = None
    if (key / "check_product_package.py").is_file():
        sys.path.insert(0, str(key))
        try:
            import check_product_package as checker_module
        finally:
            try:
                sys.path.remove(str(key))
            except ValueError:
                pass
        checker = checker_module.validate_texts
    _FULL_PRODUCT_PACKAGE_CHECKERS[key] = checker
    return checker


def _load_product_security_requirements_parser(sibling_scripts: Path) -> Any:
    """Load the canonical Product security-contract parser once per directory."""

    key = sibling_scripts.resolve()
    if key in _PRODUCT_SECURITY_REQUIREMENT_PARSERS:
        return _PRODUCT_SECURITY_REQUIREMENT_PARSERS[key]
    parser = _load_product_security_attribute(key, "parse_security_requirements")
    _PRODUCT_SECURITY_REQUIREMENT_PARSERS[key] = parser
    return parser


def _load_product_security_attribute(sibling_scripts: Path, name: str) -> Any:
    """Use the same canonical sibling source for parsing and evidence checks."""

    key = sibling_scripts.resolve()
    checker_path = key / "check_product_package.py"
    if checker_path.is_file():
        sys.path.insert(0, str(key))
        try:
            import check_product_package as checker_module
        finally:
            try:
                sys.path.remove(str(key))
            except ValueError:
                pass
        loaded_path = Path(str(getattr(checker_module, "__file__", ""))).resolve()
        if loaded_path != checker_path.resolve():
            raise ImportError("Product security parser path does not match sibling source")
        return getattr(checker_module, name, None)
    return None


def _load_ui_contract_view(sibling_scripts: Path) -> Any:
    key = sibling_scripts
    if key in _UI_CONTRACT_VIEWS:
        return _UI_CONTRACT_VIEWS[key]
    parser: Any = None
    if (key / "check_ui_design_contract.py").is_file():
        sys.path.insert(0, str(key))
        try:
            import check_ui_design_contract as checker_module
        finally:
            try:
                sys.path.remove(str(key))
            except ValueError:
                pass
        parser = checker_module.parse_ui_contract_view
    _UI_CONTRACT_VIEWS[key] = parser
    return parser


def _load_full_design_system_checker(sibling_scripts: Path) -> Any:
    """Import the design-system compiler's canonical pair checker once."""

    key = sibling_scripts
    if key in _FULL_DESIGN_SYSTEM_CHECKERS:
        return _FULL_DESIGN_SYSTEM_CHECKERS[key]
    checker: Any = None
    if (key / "check_design_system_pair.py").is_file():
        sys.path.insert(0, str(key))
        try:
            import check_design_system_pair as checker_module
        finally:
            try:
                sys.path.remove(str(key))
            except ValueError:
                pass
        checker = checker_module.compare
    _FULL_DESIGN_SYSTEM_CHECKERS[key] = checker
    return checker


def full_wireframe_checker_errors(
    wireframe_bytes: bytes,
    prd_bytes: bytes | None = None,
    *,
    sibling_scripts: Path | None = None,
) -> list[str]:
    """Run ui-design-builder's full wireframe checker on frozen bytes.

    The harness's own PLAN-side join stays; this adds the checker's wireframe
    structure, reviewer-shell, self-containment, approval, and PRD join rules
    so "approved wireframes.html" means the same thing in both skills. The
    check runs on the resolved bytes written to a temp file, so a source
    frozen at a git revision is still checked as frozen, not as the working
    tree.
    """

    scripts = sibling_scripts or sibling_ui_design_scripts_dir()
    try:
        validate_wireframes = _load_full_wireframe_checker(scripts)
    except Exception as exc:
        return [
            "wireframes: canonical checker loader failed safely: "
            f"{type(exc).__name__}: {exc}"
        ]
    if validate_wireframes is None:
        return [
            "wireframes: the full wireframe checker is unavailable — install "
            "ui-design-builder next to delivery-harness "
            f"(missing {scripts / 'check_wireframe_html.py'})"
        ]
    with tempfile.TemporaryDirectory() as directory:
        html_path = Path(directory) / "wireframes.html"
        html_path.write_bytes(wireframe_bytes)
        prd_path: Path | None = None
        if prd_bytes is not None:
            prd_path = Path(directory) / "PRD.md"
            prd_path.write_bytes(prd_bytes)
        try:
            problems = validate_wireframes(
                html_path,
                require_filled=True,
                **({"require_structure_validated": True} if (parse_wireframe_data(wireframe_bytes.decode("utf-8"))[0] or {}).get("schema") == "wireframes/5" else {"require_approved": True}),
                prd_path=prd_path,
            )
        except Exception as exc:
            return [
                "wireframes: canonical checker failed safely: "
                f"{type(exc).__name__}: {exc}"
            ]
    rewritten: list[str] = []
    for problem in problems:
        problem = problem.replace(f"{html_path}: ", "wireframes: ")
        if prd_path is not None:
            problem = problem.replace(f"{prd_path}: ", "prd: ")
        rewritten.append(problem)
    return rewritten


def full_ui_design_checker_errors(
    ui_design_bytes: bytes,
    wireframe_bytes: bytes,
    prd_bytes: bytes,
    *,
    architecture_bytes: bytes | None = None,
    stack_bytes: bytes | None = None,
    hifi_bytes: bytes | None = None,
    source_root: Path | None = None,
    sibling_scripts: Path | None = None,
) -> list[str]:
    """Run the UI checker in a temporary repository-shaped legacy adapter.

    Older Harness joins used temporary basenames, which bypassed the checker
    once it required ``--repo-root`` and an exact HiFi/pair context.  The
    adapter preserves every recorded repo-relative identity and copies only
    the frozen bytes plus retained evidence needed by the checker.
    """

    scripts = sibling_scripts or sibling_ui_design_scripts_dir()
    validate_ui_design = _load_full_ui_design_checker(scripts)
    if validate_ui_design is None:
        return [
            "ui-design: the full UI design checker is unavailable — install "
            "ui-design-builder next to delivery-harness "
            f"(missing {scripts / 'check_ui_design_contract.py'})"
        ]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        try:
            view, _ = _load_ui_contract_view(scripts)(ui_design_bytes.decode("utf-8"))
        except Exception:
            view = {}
        identities = view.get("source_identities", {}) if isinstance(view, dict) else {}

        def relative_identity(key: str, fallback: str) -> str:
            item = identities.get(key) if isinstance(identities, dict) else None
            value = item.get("path") if isinstance(item, dict) else None
            return value if isinstance(value, str) and value else fallback

        paths = {
            "ui": relative_identity("uiDesign", "docs/design/ui-design.md"),
            "wireframe": relative_identity("wireframe", "docs/design/wireframes.html"),
            "prd": relative_identity("prd", "docs/product/PRD.md"),
            "architecture": relative_identity("architecture", "docs/product/architecture.md"),
            "stack": relative_identity("stack", "docs/product/stack-decisions.md"),
        }
        target = view.get("approved_target") if isinstance(view, dict) else None
        hifi_relative = target.get("path") if isinstance(target, dict) else None
        if not isinstance(hifi_relative, str) or not hifi_relative:
            hifi_relative = "docs/design/ui-references/run-1/index.html"

        def write_relative(relative: str, payload: bytes) -> Path:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            return destination

        ui_design_path = write_relative(paths["ui"], ui_design_bytes)
        wireframes_path = write_relative(paths["wireframe"], wireframe_bytes)
        prd_path = write_relative(paths["prd"], prd_bytes)
        if architecture_bytes is not None:
            architecture_path = write_relative(paths["architecture"], architecture_bytes)
        else:
            architecture_path = root / paths["architecture"]
        if stack_bytes is not None:
            stack_path = write_relative(paths["stack"], stack_bytes)
        else:
            stack_path = root / paths["stack"]
        if hifi_bytes is not None:
            hifi_path = write_relative(hifi_relative, hifi_bytes)
        else:
            hifi_path = root / hifi_relative
        if source_root is not None:
            directions = source_root / "docs/design/directions"
            if directions.exists() or directions.is_symlink():
                if _path_has_reparse_or_link(directions) or any(
                    _path_has_reparse_or_link(path) for path in directions.rglob("*")
                ):
                    return ["ui-design: direction captures must not traverse a symlink or reparse point"]
                if not directions.is_dir():
                    return ["ui-design: docs/design/directions must be a directory"]
                shutil.copytree(directions, root / "docs/design/directions", symlinks=True)
            for relative in ("docs/evidence", "docs/design/ui-references"):
                source = source_root / relative
                destination = root / relative
                if source.is_dir():
                    shutil.copytree(source, destination, dirs_exist_ok=True)
            for relative, destination in (
                (paths["architecture"], architecture_path),
                (paths["stack"], stack_path),
                (hifi_relative, hifi_path),
            ):
                source = source_root / relative
                if destination.exists() or not source.is_file():
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        try:
            return validate_ui_design(
                ui_design_path,
                repo_root=root,
                prd_path=prd_path,
                wireframes_path=wireframes_path,
                hifi_path=hifi_path,
                require_filled=True,
                **({"require_structure_validated": True} if view.get("structure_review") else {"require_wireframe_approved": True}),
                require_visual_approved=True,
            )
        except Exception as exc:
            return [
                "ui-design: canonical checker failed safely: "
                f"{type(exc).__name__}: {exc}"
            ]


def full_product_package_checker_errors(
    prd_bytes: bytes,
    architecture_bytes: bytes,
    stack_bytes: bytes,
    *,
    sibling_scripts: Path | None = None,
    repo_root: str | Path | None = None,
    ui_contract: str | None = None,
) -> list[str]:
    """Run Product Definition's approval checker on frozen core-package bytes."""

    scripts = sibling_scripts or sibling_builder_scripts_dir()
    try:
        validate_package = _load_full_product_package_checker(scripts)
    except Exception as exc:
        return [
            "product package: canonical checker loader failed safely: "
            f"{type(exc).__name__}: {exc}"
        ]
    if validate_package is None:
        return [
            "product package: the full Product Definition checker is unavailable — "
            "install product-definition-builder next to delivery-harness "
            f"(missing {scripts / 'check_product_package.py'})"
        ]
    try:
        prd_text = prd_bytes.decode("utf-8")
        architecture_text = architecture_bytes.decode("utf-8")
        stack_text = stack_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [f"product package: core artifact is not valid UTF-8 ({exc})"]
    kwargs: dict[str, Any] = {
        "require_filled": True,
        "require_approved": True,
    }
    if repo_root is not None and "repo_root" in inspect.signature(validate_package).parameters:
        kwargs["repo_root"] = Path(repo_root)
    if ui_contract is not None:
        kwargs["ui_contract"] = ui_contract
    try:
        return validate_package(
            prd_text,
            architecture_text,
            stack_text,
            **kwargs,
        )
    except Exception as exc:
        return [
            "product package: canonical checker failed safely: "
            f"{type(exc).__name__}: {exc}"
        ]


def full_ui_design_checker_errors_at_paths(
    ui_design_path: Path,
    *,
    repo_root: Path,
    prd_path: Path,
    wireframes_path: Path | None,
    hifi_path: Path,
    design_system_markdown_path: Path | None = None,
    design_system_registry_path: Path | None = None,
    sibling_scripts: Path | None = None,
    apply_current_hifi_cutover: bool = False,
) -> list[str]:
    """Run the canonical UI checker against the actual repository paths.

    ``apply_current_hifi_cutover`` (set for Harness 0.55.1+ RUNs) applies the
    UI checker's dated rule: a legacy-heading Visual Approval decided on or
    after the 0.55.0 cutover, or backed by a HiFi receipt from then on, must
    carry current HiFi evidence.
    """

    scripts = sibling_scripts or sibling_ui_design_scripts_dir()
    try:
        validate_ui_design = _load_full_ui_design_checker(scripts)
    except Exception as exc:
        return [
            "ui-design: canonical checker loader failed safely: "
            f"{type(exc).__name__}: {exc}"
        ]
    if validate_ui_design is None:
        return [
            "ui-design: the full UI design checker is unavailable — install "
            "ui-design-builder next to delivery-harness "
            f"(missing {scripts / 'check_ui_design_contract.py'})"
        ]
    try:
        view, findings = _load_ui_contract_view(scripts)(ui_design_path.read_text(encoding="utf-8"))
        if findings:
            return findings
        legacy_flags = {} if view.get("contract_version") in CURRENT_UI_CONTRACTS else (
            {"require_structure_validated": True} if view.get("structure_review")
            else {"require_wireframe_approved": True})
        return validate_ui_design(
            ui_design_path,
            repo_root=repo_root,
            prd_path=prd_path,
            wireframes_path=wireframes_path,
            hifi_path=hifi_path,
            design_system_markdown_path=design_system_markdown_path,
            design_system_registry_path=design_system_registry_path,
            require_filled=True,
            **legacy_flags,
            require_visual_approved=True,
            apply_current_hifi_cutover=apply_current_hifi_cutover,
        )
    except Exception as exc:
        return [
            "ui-design: canonical checker failed safely: "
            f"{type(exc).__name__}: {exc}"
        ]


def full_design_system_checker_errors_at_paths(
    markdown_path: Path,
    registry_path: Path,
    *,
    repo_root: Path,
    sibling_scripts: Path | None = None,
    apply_current_hifi_cutover: bool = False,
) -> list[str]:
    """Run the compiler's canonical design-system pair checker on real files.

    ``apply_current_hifi_cutover`` passes to the compiler's UI preflight, with
    the same RUN version gate as the UI join.
    """

    scripts = sibling_scripts or (
        Path(__file__).resolve().parents[2] / "design-system-compiler" / "scripts"
    )
    try:
        compare = _load_full_design_system_checker(scripts)
    except Exception as exc:
        return [
            "design-system: canonical checker loader failed safely: "
            f"{type(exc).__name__}: {exc}"
        ]
    if compare is None:
        return [
            "design-system: the canonical pair checker is unavailable — install "
            "design-system-compiler next to delivery-harness "
            f"(missing {scripts / 'check_design_system_pair.py'})"
        ]
    try:
        markdown_text = markdown_path.read_text(encoding="utf-8")
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"design-system: cannot read canonical pair ({exc})"]
    if not isinstance(registry, dict):
        return ["design-system: design-system.json must contain an object"]
    try:
        return compare(
            markdown_text,
            registry,
            require_filled=True,
            repo_root=repo_root,
            apply_current_hifi_cutover=apply_current_hifi_cutover,
        )
    except Exception as exc:
        return [
            "design-system: canonical checker failed safely: "
            f"{type(exc).__name__}: {exc}"
        ]


def _strict_ui_surface_errors(
    plan: dict[str, Any], view: dict[str, Any]
) -> list[str]:
    """Join PLAN UI surfaces to the parser's single approved-target view."""

    errors: list[str] = []
    scope = view.get("target_scope")
    if not isinstance(scope, dict):
        return ["ui-design: approved target scope is missing"]
    target_surfaces = {
        item.get("id"): item
        for item in scope.get("surfaces", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    plan_surfaces = _plan_surfaces(plan)
    if set(target_surfaces) != set(plan_surfaces):
        errors.append("ui-design: approved target surfaces must exactly match PLAN ui_surfaces")
    responsive = scope.get("responsive")
    target_kind = responsive.get("kind") if isinstance(responsive, dict) else None
    target_values = responsive.get("targets") if isinstance(responsive, dict) else []
    target_values = [str(item) for item in target_values] if isinstance(target_values, list) else []
    capture_mode = view.get("capture_mode")
    hybrid = capture_mode == "mixed" or any(
        isinstance(item, dict) and ("captureMode" in item or "responsive" in item)
        for item in target_surfaces.values()
    )
    if not hybrid:
        if capture_mode not in {"hosted-browser", "browser-extension", "native", "desktop"}:
            errors.append("ui-design: approved target captureMode is missing or invalid")
        expected_kind = "sizeClasses" if capture_mode in {"native", "desktop"} else "viewports"
        if target_kind != expected_kind:
            errors.append("ui-design: approved target responsive kind does not match captureMode")
    for surface_id in sorted(set(target_surfaces) & set(plan_surfaces)):
        target = target_surfaces[surface_id]
        plan_surface = plan_surfaces[surface_id]
        target_class = target.get("surfaceClass")
        plan_class = plan_surface.get("surface_class")
        if target_class is not None and plan_class != target_class:
            errors.append(
                f"plan.ui_surfaces: surface {surface_id} surface_class must equal approved target surfaceClass"
            )
        target_release_surface = target.get("releaseSurface")
        if target_release_surface is not None and plan_surface.get("release_surface") != target_release_surface:
            errors.append(
                f"plan.ui_surfaces: surface {surface_id} release_surface must equal approved target releaseSurface"
            )
        if plan_surface.get("route") != target.get("route"):
            errors.append(f"plan.ui_surfaces: surface {surface_id} route differs from approved target")
        target_states = {
            normalized_state(item) for item in target.get("states", []) if isinstance(item, str)
        }
        plan_states = {
            normalized_state(item) for item in plan_surface.get("states", []) if isinstance(item, str)
        }
        if plan_states != target_states:
            errors.append(f"plan.ui_surfaces: surface {surface_id} states differ from approved target")
        surface_capture = target.get("captureMode", capture_mode)
        surface_responsive = target.get("responsive", responsive)
        surface_kind = surface_responsive.get("kind") if isinstance(surface_responsive, dict) else target_kind
        surface_values = surface_responsive.get("targets", []) if isinstance(surface_responsive, dict) else target_values
        surface_values = [str(item) for item in surface_values] if isinstance(surface_values, list) else []
        if surface_capture not in {"hosted-browser", "browser-extension", "native", "desktop"}:
            errors.append(f"ui-design: approved target surface {surface_id} captureMode is missing or invalid")
        expected_surface_kind = "sizeClasses" if surface_capture in {"native", "desktop"} else "viewports"
        if surface_kind != expected_surface_kind:
            errors.append(f"ui-design: approved target surface {surface_id} responsive kind does not match captureMode")
        breakpoints = [str(item).strip() for item in plan_surface.get("breakpoints", []) if isinstance(item, str)]
        if surface_kind == "viewports":
            if len(breakpoints) != len(surface_values) or any(
                not any(breakpoint_matches_viewport(item, target_value) for item in breakpoints)
                for target_value in surface_values
            ):
                errors.append(f"plan.ui_surfaces: surface {surface_id} breakpoints differ from approved target")
        elif set(breakpoints) != set(surface_values) or len(breakpoints) != len(surface_values):
            errors.append(f"plan.ui_surfaces: surface {surface_id} size classes differ from approved target")
        capture = plan_surface.get("capture_mode")
        if capture != surface_capture:
            errors.append(
                f"plan.ui_surfaces: surface {surface_id} capture_mode must equal approved target captureMode"
            )
    return sorted(set(errors))


def _frozen_ui_contract_version(rows: list[dict[str, Any]], root: Path) -> str | None:
    """Read the frozen ui-design contract version, or None when unreadable."""

    if len(rows) != 1:
        return None
    contents, errors = _resolve_source_bytes(rows[0], root, label="ui-design", strict=True)
    parser = _load_ui_contract_view(sibling_ui_design_scripts_dir())
    if errors or contents is None or parser is None:
        return None
    try:
        view, _parser_errors = parser(contents.decode("utf-8"))
    except Exception:
        return None
    return view.get("contract_version") if isinstance(view, dict) else None


def _platform_and_feature_acceptance_errors(
    plan: dict[str, Any],
    prd_bytes: bytes | None,
    architecture_bytes: bytes | None,
    *,
    architecture_declared: bool = False,
) -> list[str]:
    """Join one exact PRD/architecture pair to platform and feature gates."""

    errors: list[str] = []
    declared_mapping = plan.get("platform_delivery") is not None
    declared_acceptance = any(
        isinstance(trace, dict) and "acceptance_gate_ids" in trace
        for trace in plan.get("traces", [])
    )
    prd_text_valid = False
    if prd_bytes is None:
        if declared_mapping or declared_acceptance:
            errors.append(
                "prd: adopted platform or feature authority requires frozen PRD bytes"
            )
        prd_text = ""
    else:
        try:
            prd_text = prd_bytes.decode("utf-8")
            prd_text_valid = True
        except UnicodeDecodeError as exc:
            errors.append(f"prd: is not valid UTF-8 ({exc})")
            prd_text = ""
    if architecture_bytes is None:
        if declared_mapping or architecture_declared:
            errors.append(
                "plan.sources: declared frozen architecture requires readable bytes"
            )
        architecture_text = ""
    else:
        try:
            architecture_text = architecture_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"architecture: is not valid UTF-8 ({exc})")
            architecture_text = ""

    platform_module = _load_platform_delivery_parser(sibling_builder_scripts_dir())
    platform_contract: Any | None = None
    platform_findings: list[str] = []
    if platform_module is None:
        if declared_mapping or architecture_bytes is not None or architecture_declared:
            errors.append(
                "platform delivery: canonical parser is unavailable — install "
                "product-definition-builder next to delivery-harness"
            )
    else:
        try:
            platform_contract, platform_findings = platform_module.parse_platform_delivery(
                architecture_text,
                prd_text,
                require=declared_mapping,
            )
        except Exception as exc:
            errors.append(
                "platform delivery: canonical parser failed safely: "
                f"{type(exc).__name__}: {exc}"
            )
    errors.extend(platform_findings)

    feature_test_authority: dict[str, set[str]] | None = None
    adopted_authority = (
        platform_contract is not None
        or declared_mapping
        or declared_acceptance
    )
    if adopted_authority:
        if prd_bytes is None or not prd_text_valid:
            errors.append(
                "prd: adopted platform or feature authority requires readable frozen PRD bytes"
            )
            return errors
        try:
            feature_test_authority = parse_required_prd_test_authority(prd_bytes)
        except AcceptanceError as exc:
            errors.append(f"prd: canonical feature TEST authority failed safely: {exc}")
            return errors
    if platform_contract is not None and platform_contract.decision_status != "approved":
        errors.append(
            "architecture: adopted platform-delivery/1 requires an approved decision"
        )

    required_test_ids = (
        set().union(*feature_test_authority.values())
        if feature_test_authority
        else set()
    )
    if platform_contract is not None or declared_mapping:
        errors.extend(validate_platform_delivery(
            plan,
            platform_contract,
            required_test_ids=required_test_ids,
            feature_test_authority=feature_test_authority,
        ))
    else:
        errors.extend(validate_feature_acceptance(
            plan,
            feature_test_authority=feature_test_authority,
        ))
    return errors


def _validate_strict_frozen_contract_joins(
    plan: dict[str, Any], repo_root: str | Path, *, run: dict[str, Any] | None,
    current_ui: bool = False,
) -> list[str]:
    """Enforce the 0.38 source authority and UI/design-system XOR contract."""

    inventory, errors = _strict_source_inventory(plan)
    has_ui = bool(plan.get("ui_surfaces"))
    current = current_ui or wireframe_free_required(run)
    maintenance, maintenance_errors = _frozen_maintenance_record(plan, Path(repo_root).resolve())
    if maintenance and not maintenance_errors and (
        inventory["wireframes"]
        or has_ui and _frozen_ui_contract_version(inventory["ui-design"], Path(repo_root).resolve()) == "legacy"
    ):
        # A recorded maintenance round preserves its frozen historical design.
        # Only new design work must migrate the whole contract together. A
        # legacy contract without its wireframe row then reports that row.
        current = False
    required_keys = {"prd", "architecture", "stack"}
    if has_ui:
        required_keys.update({"ui-design", "approved-target"})
        if current:
            if inventory["wireframes"]:
                errors.append("plan.sources: Harness 0.56+ UI delivery must not freeze a wireframe source")
        else:
            required_keys.add("wireframes")
    for key in sorted(required_keys):
        rows = inventory[key]
        if len(rows) != 1:
            errors.append(
                f"plan.sources: Harness 0.38+ requires exactly one frozen {key} source"
            )
    if not has_ui:
        for key in ("ui-design", "wireframes", "approved-target", "design-system.md", "design-system.json",
                    "design-system-preview"):
            if inventory[key]:
                errors.append(f"plan.sources: headless PLAN must not freeze {key} source")

    resolved: dict[str, bytes] = {}
    paths: dict[str, Path] = {}
    root = Path(repo_root).resolve()
    labels = {
        "prd": "PRD",
        "architecture": "architecture",
        "stack": "stack-decisions",
        "ui-design": "ui-design",
        "wireframes": "wireframes",
        "approved-target": "approved UI target",
        "design-system.md": "design-system.md",
        "design-system.json": "design-system.json",
        "design-system-preview": "design-system-preview.html",
    }
    for key, rows in inventory.items():
        if len(rows) != 1 or key not in required_keys and key not in {
            "design-system.md", "design-system.json", "design-system-preview",
        }:
            continue
        if not rows:
            continue
        contents, source_errors = _resolve_source_bytes(
            rows[0], root, label=labels[key], strict=True
        )
        errors.extend(source_errors)
        if contents is not None:
            resolved[key] = contents
            paths[key] = root / str(rows[0]["location"])

    if not all(key in resolved for key in ("prd", "architecture", "stack")):
        return sorted(set(errors))
    try:
        prd_text = resolved["prd"].decode("utf-8")
        resolved["architecture"].decode("utf-8")
        resolved["stack"].decode("utf-8")
    except UnicodeDecodeError as exc:
        errors.append(f"product package: core artifact is not valid UTF-8 ({exc})")
        return sorted(set(errors))

    errors.extend(_platform_and_feature_acceptance_errors(
        plan,
        resolved["prd"],
        resolved["architecture"],
    ))

    release_contract = _load_release_source_contract(sibling_builder_scripts_dir())
    if release_contract is None or not callable(getattr(release_contract, "active_text", None)):
        errors.append(
            "architecture: canonical active-Markdown release contract parser is unavailable"
        )
    else:
        errors.extend(
            validate_branch_policy_join(
                plan,
                resolved["architecture"].decode("utf-8"),
                root,
                run=run,
                active_text=release_contract.active_text,
            )
        )

    errors.extend(
        product_security_requirements_join_errors(
            plan, prd_text, parser_required=True
        )
    )
    canonical_prd_parser = _load_canonical_prd_ui_contract_parser(
        sibling_builder_scripts_dir()
    )
    if canonical_prd_parser is None:
        errors.append(
            "prd: canonical active-Markdown UI contract parser is unavailable — "
            "install product-definition-builder next to delivery-harness"
        )
    else:
        try:
            errors.extend(
                validate_plan_prd_text(plan, prd_text, parser=canonical_prd_parser)
            )
        except Exception as exc:
            errors.append(
                "prd: canonical active-Markdown UI contract parser failed safely: "
                f"{type(exc).__name__}: {exc}"
            )
    frozen_version = (
        _frozen_ui_contract_version(inventory["ui-design"], root) if has_ui else None
    )
    errors.extend(
        full_product_package_checker_errors(
            resolved["prd"], resolved["architecture"], resolved["stack"], repo_root=root,
            **({"ui_contract": frozen_version if frozen_version in CURRENT_UI_CONTRACTS else "ui-design/2"}
               if current and has_ui else {})
        )
    )
    if not has_ui:
        return sorted(set(errors))

    if not required_keys.issubset(resolved):
        return sorted(set(errors))
    parser = _load_ui_contract_view(sibling_ui_design_scripts_dir())
    if parser is None:
        errors.append("ui-design: shared UI contract parser is unavailable")
        return sorted(set(errors))
    try:
        ui_text = resolved["ui-design"].decode("utf-8")
        try:
            view, parser_errors = parser(ui_text)
        except Exception as exc:
            errors.append(
                "ui-design: shared contract parser failed safely: "
                f"{type(exc).__name__}: {exc}"
            )
            return sorted(set(errors))
    except UnicodeDecodeError as exc:
        errors.append(f"ui-design: is not valid UTF-8 ({exc})")
        return sorted(set(errors))
    errors.extend(parser_errors)
    version = view.get("contract_version", "legacy")
    # Only a validated maintenance record may keep a retained ui-design/2
    # package. An enhancement label is never retention evidence.
    retained = bool(maintenance and not maintenance_errors)
    errors.extend(_ui_contract_version_errors(version, run=run, current=current, retained=retained))
    errors.extend(_strict_ui_surface_errors(plan, view))

    errors.extend(maintenance_errors)
    if maintenance:
        # The current approved Product Definition and PLAN still own routes,
        # states and targets. Historical design bytes stay frozen, but their
        # older PRD binding does not turn a same-surface repair into redesign.
        target = view.get("approved_target") if isinstance(view, dict) else None
        target_row = inventory["approved-target"][0]
        if not isinstance(target, dict) or target.get("path") != target_row.get("location") or target.get("sha256") != target_row.get("content_sha256"):
            errors.append("plan.sources: retained approved UI target differs from ui-design Approved target")
        gate = view.get("gate") if isinstance(view, dict) else None
        if isinstance(gate, dict) and gate.get("decision") == "required" and (
            len(inventory["design-system.md"]) != 1 or len(inventory["design-system.json"]) != 1
        ):
            errors.append("plan.sources: retained required design-system pair must include both frozen files")
        if bool(inventory["design-system.md"]) != bool(inventory["design-system.json"]):
            errors.append("plan.sources: retained design-system pair must include both frozen files")
        return sorted(set(errors))

    source_identity_map = view.get("source_identities") if isinstance(view, dict) else None
    for view_key, source_key in (
        ("prd", "prd"),
        ("architecture", "architecture"),
        ("stack", "stack"),
        ("wireframe", "wireframes"),
    ):
        if current and view_key == "wireframe":
            continue
        identity = source_identity_map.get(view_key) if isinstance(source_identity_map, dict) else None
        row = inventory[source_key][0]
        if not isinstance(identity, dict) or identity.get("path") != row.get("location") or identity.get("sha256") != row.get("content_sha256"):
            errors.append(
                f"ui-design: {view_key} source identity must exactly match the frozen PLAN source"
            )
    frozen_prd = source_identity_map.get("frozen_prd") if isinstance(source_identity_map, dict) else None
    if isinstance(frozen_prd, dict) and (
        frozen_prd.get("path") != inventory["prd"][0].get("location")
        or frozen_prd.get("sha256") != inventory["prd"][0].get("content_sha256")
    ):
        errors.append("ui-design: Frozen PRD basis must exactly match the frozen PLAN PRD source")

    target = view.get("approved_target") if isinstance(view, dict) else None
    target_row = inventory["approved-target"][0]
    if not isinstance(target, dict):
        errors.append("ui-design: approved target identity is missing")
    else:
        if target.get("path") != target_row.get("location") or target.get("sha256") != target_row.get("content_sha256"):
            errors.append("plan.sources: approved UI target source does not match ui-design Approved target")
    apply_cutover = version_at_least(
        run_required_harness_version(run), CURRENT_HIFI_EVIDENCE_VERSION
    )
    errors.extend(
        full_ui_design_checker_errors_at_paths(
            paths["ui-design"],
            repo_root=root,
            prd_path=paths["prd"],
            wireframes_path=paths.get("wireframes"),
            hifi_path=paths["approved-target"],
            design_system_markdown_path=paths.get("design-system.md"),
            design_system_registry_path=paths.get("design-system.json"),
            apply_current_hifi_cutover=apply_cutover,
        )
    )

    gate = view.get("gate") if isinstance(view, dict) else None
    decision = gate.get("decision") if isinstance(gate, dict) else None
    if version == "ui-design/3":
        errors.extend(_frozen_preview_errors(inventory, paths, root))
    ds_rows_present = bool(inventory["design-system.md"] or inventory["design-system.json"])
    ds_trace_present = any(
        isinstance(trace, dict)
        and isinstance(trace.get("id"), str)
        and trace["id"].startswith("DS-")
        for trace in (plan.get("traces") or [])
    )
    if decision == "required":
        if len(inventory["design-system.md"]) != 1 or len(inventory["design-system.json"]) != 1:
            errors.append("plan.sources: required Design System Need Gate needs exactly one design-system.md and design-system.json")
        elif paths.get("design-system.md") and paths.get("design-system.json"):
            errors.extend(
                full_design_system_checker_errors_at_paths(
                    paths["design-system.md"],
                    paths["design-system.json"],
                    repo_root=root,
                    apply_current_hifi_cutover=apply_cutover,
                )
            )
            try:
                registry = json.loads(
                    paths["design-system.json"].read_text(encoding="utf-8")
                )
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"design-system: cannot read registry for PLAN join: {exc}")
            else:
                try:
                    expected_schema = DESIGN_SYSTEM_SCHEMA_BY_UI.get(version, "design-system/3") if current else "design-system/2"
                    if registry.get("schema") != expected_schema:
                        errors.append(f"design-system: this RUN requires {expected_schema}")
                    errors.extend(validate_ui_surface_design_registry(plan, registry))
                except Exception as exc:
                    errors.append(
                        "design-system: PLAN registry join failed safely: "
                        f"{type(exc).__name__}: {exc}"
                    )
    elif decision == "not_required":
        if ds_rows_present or ds_trace_present:
            errors.append("plan.sources: not_required Design System Need Gate must have no design-system rows or DS traces")
        replacement = gate.get("replacement") if isinstance(gate, dict) else None
        replacement_keys = {"target", "ui-design", "prd"} | (set() if current else {"wireframe"})
        if not isinstance(replacement, dict) or set(replacement) != replacement_keys:
            errors.append("ui-design: not_required Design System Need Gate replacement must name the exact visual contract")
    else:
        errors.append("ui-design: Design System Need Gate must be required or not_required")
    return sorted(set(errors))


def validate_frozen_contract_joins(plan, repo_root, *, run=None):
    """Join eval authority before any legacy/current Product/UI early return."""
    try:
        from eval_plan_contract import validate_eval_plan
    except (ImportError, OSError, SyntaxError):
        return ["eval-plan: installed sibling eval policy parser unavailable"]
    errors = validate_eval_plan(plan, repo_root, run=run,
        source_rows=_strict_source_rows, resolve_source=_resolve_source_bytes)
    return sorted(set(errors + _validate_product_frozen_contract_joins(plan, repo_root, run=run)))


def _validate_product_frozen_contract_joins(
    plan: dict[str, Any],
    repo_root: str | Path,
    *,
    run: dict[str, Any] | None = None,
) -> list[str]:
    """Resolve frozen Product/UI authority through the current strict join."""
    if plan.get("schema_version") != 6:
        return []
    return _validate_strict_frozen_contract_joins(
        plan, repo_root, run=run, current_ui=run is None,
    )

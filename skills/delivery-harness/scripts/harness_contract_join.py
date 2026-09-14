#!/usr/bin/env python3
"""Join frozen product artifacts to the executable PLAN projection."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Any

from harness_design_contract import compare_design_system_pair
from harness_git import GitMetadataError, reject_object_substitution, run_git
from harness_schema import run_required_harness_version, version_at_least
from harness_ui_evidence import validate_ui_surface_design_registry


FROZEN_SOURCE_STATUSES = {"frozen", "delta_accepted", "delta accepted"}
PRD_SOURCE_KINDS = {"prd", "product requirement", "product requirements"}
UI_DESIGN_SOURCE_KINDS = {"ui design", "ui design contract", "approved ui design"}
WIREFRAME_SOURCE_KINDS = {"wireframe", "wireframes", "approved wireframe"}
ARCHITECTURE_SOURCE_KINDS = {"architecture", "product architecture"}
STACK_DECISION_SOURCE_KINDS = {
    "stack decision",
    "stack decisions",
    "technology decision",
    "technology decisions",
}
DESIGN_SYSTEM_JSON_SOURCE_KINDS = {
    "design system json",
    "design system machine",
}
DESIGN_SYSTEM_MARKDOWN_SOURCE_KINDS = {
    "design system",
    "design system markdown",
}
APPROVED_UI_TARGET_SOURCE_KINDS = {"approved ui target"}
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
        rows, row_errors = _strict_source_rows(plan, key)
        inventory[key] = rows
        errors.extend(row_errors)
    return inventory, sorted(set(errors))


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


WEB_VIEWPORT_FLOOR_VERSION = (0, 34, 0)
UI_DESIGN_CONTRACT_REQUIRED_VERSION = (0, 37, 0)
STRICT_UI_AUTHORITY_VERSION = (0, 38, 0)


_STRICT_SOURCE_SPECS: dict[str, dict[str, Any]] = {
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
}


def strict_ui_authority_required(run: dict[str, Any] | None) -> bool:
    """Return whether the paired RUN opts into the 0.38 authority join."""

    return bool(
        isinstance(run, dict)
        and version_at_least(
            run_required_harness_version(run), STRICT_UI_AUTHORITY_VERSION
        )
    )


def web_viewport_floor_required(run: dict[str, Any] | None) -> bool:
    """True when the paired RUN pins harness 0.34.0 or later.

    The documented contract raises the web responsive floor to three
    ascending viewports from harness 0.34.0. Unpinned and older RUNs keep
    the historical two-target floor so in-flight and legacy pairs stay
    valid: the low-level parsers keep enforcing two, and this gate is
    applied only at the join layer that has the RUN's version context.
    """

    if not isinstance(run, dict):
        return False
    return version_at_least(
        run_required_harness_version(run), WEB_VIEWPORT_FLOOR_VERSION
    )


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


def validate_prd_wireframe_data(prd_text: str, data: dict[str, Any]) -> list[str]:
    prd_surfaces, errors = parse_prd_ui_contract(prd_text)
    screens, screen_errors = _wireframe_screens(data)
    errors.extend(screen_errors)
    responsive_kind = "viewports" if "viewports" in data else "sizeClasses"
    responsive_targets = [
        str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
        for value in (data.get(responsive_kind) or [])
    ]
    prd_ids = set(prd_surfaces)
    screen_ids = set(screens)
    missing = sorted(prd_ids - screen_ids)
    extra = sorted(screen_ids - prd_ids)
    if missing:
        errors.append("prd: UI surfaces absent from the wireframe: " + ", ".join(missing))
    if extra:
        errors.append(
            "wireframes: screens absent from the PRD UI surface contract: "
            + ", ".join(extra)
        )
    for surface_id in sorted(prd_ids & screen_ids):
        routes = prd_surfaces[surface_id]["routes"]
        if len(routes) == 1 and routes[0] != screens[surface_id].get("route"):
            errors.append(
                f"wireframes: screen {surface_id} route {screens[surface_id].get('route')!r} "
                f"differs from the PRD route {routes[0]!r}"
            )
        prd_states = set(prd_surfaces[surface_id]["states"])
        wireframe_states = _screen_states(screens[surface_id])
        if prd_states != wireframe_states:
            errors.append(
                f"wireframes: screen {surface_id} states {sorted(wireframe_states)} "
                f"differ from the PRD states {sorted(prd_states)}"
            )
        prd_kind = prd_surfaces[surface_id]["responsiveKind"]
        prd_targets = prd_surfaces[surface_id]["responsiveTargets"]
        if prd_kind and (
            prd_kind != responsive_kind or prd_targets != responsive_targets
        ):
            errors.append(
                f"wireframes: screen {surface_id} responsive set "
                f"{responsive_kind} {responsive_targets} differs from the PRD "
                f"{prd_kind} {prd_targets}"
            )
    return errors


def required_contract_source_errors(plan: dict[str, Any]) -> list[str]:
    """Require the source families needed by an executable current PLAN."""

    if plan.get("schema_version") != 6:
        return []
    errors: list[str] = []
    has_ui = bool(plan.get("ui_surfaces"))
    prd_sources = frozen_sources(
        plan, kinds=PRD_SOURCE_KINDS, filenames={"prd.md"}
    )
    wireframe_sources = frozen_sources(
        plan, kinds=WIREFRAME_SOURCE_KINDS, filenames={"wireframes.html"}
    )
    if (has_ui or prd_sources) and len(prd_sources) != 1:
        errors.append(
            "plan.sources: a joined current PLAN requires exactly one frozen PRD source"
        )
    if (has_ui or wireframe_sources) and len(wireframe_sources) != 1:
        errors.append(
            "plan.sources: UI-bearing or wireframe-backed current PLAN requires exactly "
            "one frozen wireframes.html source"
        )
    errors.extend(required_design_system_source_errors(plan))
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
        for component in PureWindowsPath(location.replace("/", "\\")).parts:
            if component in {".", ""}:
                continue
            cursor = cursor / component
            if cursor.is_symlink():
                return None, [
                    f"plan.sources: frozen {label} path must not traverse a symlink"
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
    return contents, []


_FULL_WIREFRAME_CHECKERS: dict[Path, Any] = {}
_FULL_UI_DESIGN_CHECKERS: dict[Path, Any] = {}
_FULL_PRODUCT_PACKAGE_CHECKERS: dict[Path, Any] = {}
_FULL_DESIGN_SYSTEM_CHECKERS: dict[Path, Any] = {}
_UI_CONTRACT_VIEWS: dict[Path, Any] = {}
_PRD_UI_CONTRACT_PARSERS: dict[Path, Any] = {}


def sibling_builder_scripts_dir() -> Path:
    """The product-definition-builder scripts dir shipped next to this skill."""

    return Path(__file__).resolve().parents[2] / "product-definition-builder" / "scripts"


def _load_canonical_prd_ui_contract_parser(sibling_scripts: Path) -> Any:
    """Load the Product Definition Builder's active-Markdown UI parser safely.

    Harness can be installed without its sibling skills.  The strict 0.38
    authority join therefore fails closed when this parser is unavailable;
    it must never fall back to the legacy regex parser for an executable join.
    """

    key = sibling_scripts.resolve()
    if key in _PRD_UI_CONTRACT_PARSERS:
        return _PRD_UI_CONTRACT_PARSERS[key]
    parser: Any = None
    parser_path = key / "prd_ui_contract.py"
    markdown_path = key / "markdown_contract.py"
    if parser_path.is_file() and markdown_path.is_file():
        # The sibling parser uses a top-level ``markdown_contract`` import.
        # Load both files under private names and temporarily bind that import
        # to the verified sibling module.  This avoids accepting a poisoned
        # same-name module already present in the host process.
        tag = hashlib.sha256(str(key).encode("utf-8")).hexdigest()[:16]
        markdown_name = f"_harness_prd_markdown_contract_{tag}"
        parser_name = f"_harness_prd_ui_contract_{tag}"
        previous_markdown = sys.modules.get("markdown_contract")
        try:
            markdown_spec = importlib.util.spec_from_file_location(
                markdown_name, markdown_path
            )
            parser_spec = importlib.util.spec_from_file_location(
                parser_name, parser_path
            )
            if (
                markdown_spec is None
                or markdown_spec.loader is None
                or parser_spec is None
                or parser_spec.loader is None
            ):
                raise ImportError("canonical PRD parser module spec is unavailable")
            markdown_module = importlib.util.module_from_spec(markdown_spec)
            parser_module = importlib.util.module_from_spec(parser_spec)
            sys.modules[markdown_name] = markdown_module
            sys.modules["markdown_contract"] = markdown_module
            markdown_spec.loader.exec_module(markdown_module)
            sys.modules[parser_name] = parser_module
            parser_spec.loader.exec_module(parser_module)
            loaded_path = Path(str(getattr(parser_module, "__file__", ""))).resolve()
            if loaded_path != parser_path.resolve():
                raise ImportError("canonical PRD parser path does not match sibling source")
            parser = getattr(parser_module, "parse_prd_ui_contract", None)
        except Exception:
            parser = None
        finally:
            if previous_markdown is None:
                sys.modules.pop("markdown_contract", None)
            else:
                sys.modules["markdown_contract"] = previous_markdown
            sys.modules.pop(markdown_name, None)
            sys.modules.pop(parser_name, None)
    _PRD_UI_CONTRACT_PARSERS[key] = parser
    return parser


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
                require_approved=True,
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
    sibling_scripts: Path | None = None,
) -> list[str]:
    """Run ui-design-builder's approved visual-contract checker on frozen bytes."""

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
        ui_design_path = root / "ui-design.md"
        wireframes_path = root / "wireframes.html"
        prd_path = root / "PRD.md"
        ui_design_path.write_bytes(ui_design_bytes)
        wireframes_path.write_bytes(wireframe_bytes)
        prd_path.write_bytes(prd_bytes)
        try:
            return validate_ui_design(
                ui_design_path,
                prd_path=prd_path,
                wireframes_path=wireframes_path,
                require_filled=True,
                require_wireframe_approved=True,
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
    wireframes_path: Path,
    hifi_path: Path,
    design_system_markdown_path: Path | None = None,
    design_system_registry_path: Path | None = None,
    sibling_scripts: Path | None = None,
) -> list[str]:
    """Run the canonical UI checker against the actual repository paths."""

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
        return validate_ui_design(
            ui_design_path,
            repo_root=repo_root,
            prd_path=prd_path,
            wireframes_path=wireframes_path,
            hifi_path=hifi_path,
            design_system_markdown_path=design_system_markdown_path,
            design_system_registry_path=design_system_registry_path,
            require_filled=True,
            require_wireframe_approved=True,
            require_visual_approved=True,
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
) -> list[str]:
    """Run the compiler's canonical design-system pair checker on real files."""

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


def _validate_strict_frozen_contract_joins(
    plan: dict[str, Any], repo_root: str | Path, *, run: dict[str, Any]
) -> list[str]:
    """Enforce the 0.38 source authority and UI/design-system XOR contract."""

    inventory, errors = _strict_source_inventory(plan)
    has_ui = bool(plan.get("ui_surfaces"))
    required_keys = {"prd", "architecture", "stack"}
    if has_ui:
        required_keys.update({"ui-design", "wireframes", "approved-target"})
    for key in sorted(required_keys):
        rows = inventory[key]
        if len(rows) != 1:
            errors.append(
                f"plan.sources: Harness 0.38+ requires exactly one frozen {key} source"
            )
    if not has_ui:
        for key in ("ui-design", "wireframes", "approved-target", "design-system.md", "design-system.json"):
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
    }
    for key, rows in inventory.items():
        if len(rows) != 1 or key not in required_keys and key not in {"design-system.md", "design-system.json"}:
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
    errors.extend(
        full_product_package_checker_errors(
            resolved["prd"], resolved["architecture"], resolved["stack"], repo_root=root
        )
    )
    if not has_ui:
        return sorted(set(errors))

    if not all(key in resolved for key in ("ui-design", "wireframes", "approved-target")):
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
    errors.extend(_strict_ui_surface_errors(plan, view))

    source_identity_map = view.get("source_identities") if isinstance(view, dict) else None
    for view_key, source_key in (
        ("prd", "prd"),
        ("architecture", "architecture"),
        ("stack", "stack"),
        ("wireframe", "wireframes"),
    ):
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
    errors.extend(
        full_ui_design_checker_errors_at_paths(
            paths["ui-design"],
            repo_root=root,
            prd_path=paths["prd"],
            wireframes_path=paths["wireframes"],
            hifi_path=paths["approved-target"],
            design_system_markdown_path=paths.get("design-system.md"),
            design_system_registry_path=paths.get("design-system.json"),
        )
    )

    gate = view.get("gate") if isinstance(view, dict) else None
    decision = gate.get("decision") if isinstance(gate, dict) else None
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
                    paths["design-system.md"], paths["design-system.json"], repo_root=root
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
        if not isinstance(replacement, dict) or set(replacement) != {"target", "ui-design", "wireframe", "prd"}:
            errors.append("ui-design: not_required Design System Need Gate replacement must name the exact visual contract")
    else:
        errors.append("ui-design: Design System Need Gate must be required or not_required")
    return sorted(set(errors))


def validate_frozen_contract_joins(
    plan: dict[str, Any],
    repo_root: str | Path,
    *,
    run: dict[str, Any] | None = None,
) -> list[str]:
    """Resolve frozen bytes and enforce joins on every execution validation.

    When ``run`` is the paired RUN manifest and its version gate pins harness
    0.34.0+, web responsive sets in the PRD anchors and the design-system
    registry must carry three ascending viewports; unpinned or older RUNs
    keep the two-target floor.
    """

    if plan.get("schema_version") != 6:
        return []
    if strict_ui_authority_required(run):
        return _validate_strict_frozen_contract_joins(plan, repo_root, run=run)
    errors = required_contract_source_errors(plan)
    has_ui = bool(plan.get("ui_surfaces"))
    prd_sources = frozen_sources(
        plan, kinds=PRD_SOURCE_KINDS, filenames={"prd.md"}
    )
    wireframe_sources = frozen_sources(
        plan, kinds=WIREFRAME_SOURCE_KINDS, filenames={"wireframes.html"}
    )
    ui_design_sources = frozen_sources(
        plan, kinds=UI_DESIGN_SOURCE_KINDS, filenames={"ui-design.md"}
    )
    architecture_sources = frozen_sources(
        plan, kinds=ARCHITECTURE_SOURCE_KINDS, filenames={"architecture.md"}
    )
    stack_sources = frozen_sources(
        plan, kinds=STACK_DECISION_SOURCE_KINDS, filenames={"stack-decisions.md"}
    )
    design_markdown_sources = frozen_sources(
        plan,
        kinds=DESIGN_SYSTEM_MARKDOWN_SOURCE_KINDS,
        filenames={"design-system.md"},
    )
    design_json_sources = frozen_sources(
        plan,
        kinds=DESIGN_SYSTEM_JSON_SOURCE_KINDS,
        filenames={"design-system.json"},
    )
    has_design_contract = bool(design_markdown_sources or design_json_sources) or any(
        isinstance(trace, dict)
        and isinstance(trace.get("id"), str)
        and trace["id"].startswith("DS-")
        for trace in (plan.get("traces") or [])
    )
    required_version = run_required_harness_version(run) if run is not None else None
    ui_design_required = bool(
        has_ui
        and required_version
        and version_at_least(required_version, UI_DESIGN_CONTRACT_REQUIRED_VERSION)
    )
    if ui_design_required and len(ui_design_sources) != 1:
        errors.append(
            "plan.sources: Harness 0.37.0+ UI delivery requires exactly one "
            "frozen ui-design.md source"
        )
    families: list[tuple[str, list[dict[str, Any]]]] = []
    if has_ui or prd_sources:
        families.append(("PRD", prd_sources))
    if has_ui or wireframe_sources:
        families.append(("wireframes", wireframe_sources))
    if ui_design_required or ui_design_sources:
        families.append(("ui-design", ui_design_sources))
    if has_design_contract:
        families.extend(
            [
                ("design-system.md", design_markdown_sources),
                ("design-system.json", design_json_sources),
            ]
        )
    resolved: dict[str, bytes] = {}
    for label, sources in families:
        if len(sources) != 1:
            continue
        contents, source_errors = _resolve_source_bytes(
            sources[0], repo_root, label=label
        )
        errors.extend(source_errors)
        if contents is not None:
            resolved[label] = contents
    viewports_floor = web_viewport_floor_required(run)
    prd_text: str | None = None
    if "PRD" in resolved:
        try:
            prd_text = resolved["PRD"].decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"prd: is not valid UTF-8 ({exc})")
        else:
            errors.extend(validate_plan_prd_text(plan, prd_text))
            if viewports_floor:
                errors.extend(prd_web_viewport_floor_errors(prd_text))
            if (
                "<!-- product-definition-approval:start -->" in prd_text
                or "<!-- product-definition-approval:end -->" in prd_text
            ):
                if len(architecture_sources) != 1:
                    errors.append(
                        "plan.sources: an approved Product Definition package requires "
                        "exactly one frozen architecture.md source"
                    )
                if len(stack_sources) != 1:
                    errors.append(
                        "plan.sources: an approved Product Definition package requires "
                        "exactly one frozen stack-decisions.md source"
                    )
                if len(architecture_sources) == 1:
                    contents, source_errors = _resolve_source_bytes(
                        architecture_sources[0], repo_root, label="architecture"
                    )
                    errors.extend(source_errors)
                    if contents is not None:
                        resolved["architecture"] = contents
                if len(stack_sources) == 1:
                    contents, source_errors = _resolve_source_bytes(
                        stack_sources[0], repo_root, label="stack-decisions"
                    )
                    errors.extend(source_errors)
                    if contents is not None:
                        resolved["stack-decisions"] = contents
                if "architecture" in resolved and "stack-decisions" in resolved:
                    errors.extend(
                        full_product_package_checker_errors(
                            resolved["PRD"],
                            resolved["architecture"],
                            resolved["stack-decisions"],
                            repo_root=repo_root,
                        )
                    )
    if "wireframes" in resolved:
        try:
            wireframe_text = resolved["wireframes"].decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"wireframes: is not valid UTF-8 ({exc})")
        else:
            data, parse_errors = parse_wireframe_data(wireframe_text)
            errors.extend(parse_errors)
            if data is not None:
                errors.extend(validate_plan_wireframe_data(plan, data))
            errors.extend(
                full_wireframe_checker_errors(
                    resolved["wireframes"], resolved.get("PRD")
                )
            )
    if all(name in resolved for name in ("ui-design", "wireframes", "PRD")):
        errors.extend(
            full_ui_design_checker_errors(
                resolved["ui-design"],
                resolved["wireframes"],
                resolved["PRD"],
            )
        )
    registry: Any = None
    if "design-system.json" in resolved:
        try:
            registry = json.loads(resolved["design-system.json"].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"design_system: is not valid JSON ({exc})")
        else:
            try:
                errors.extend(validate_ui_surface_design_registry(plan, registry))
            except Exception as exc:
                errors.append(
                    "design_system: PLAN registry join failed safely: "
                    f"{type(exc).__name__}: {exc}"
                )
            if viewports_floor and isinstance(registry, dict):
                errors.extend(registry_web_viewport_floor_errors(registry))
    if isinstance(registry, dict) and "design-system.md" in resolved:
        try:
            markdown_text = resolved["design-system.md"].decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"design-system.md: is not valid UTF-8 ({exc})")
        else:
            try:
                errors.extend(compare_design_system_pair(markdown_text, registry))
            except Exception as exc:
                errors.append(
                    "design_system: canonical pair adapter failed safely: "
                    f"{type(exc).__name__}: {exc}"
                )
    return sorted(set(errors))

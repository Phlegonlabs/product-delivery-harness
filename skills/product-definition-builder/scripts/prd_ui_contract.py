#!/usr/bin/env python3
"""Parse and compare the Product Definition Builder's invariant UI contract anchors."""

from __future__ import annotations

import json
import math
import re
from typing import Any


UI_HEADING_RE = re.compile(
    r"^###\s+(UI-[A-Z0-9]+(?:-[A-Z0-9]+)*)\b.*$", re.MULTILINE
)
ROUTE_RE = re.compile(
    r"^\s*-\s*`route`\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
STATES_RE = re.compile(
    r"^\s*-\s*`states`\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
RESPONSIVE_RE = re.compile(
    r"^\s*-\s*`responsive`\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
MACHINE_BLOCK_RE = re.compile(
    r"<!--\s*ui-surface-contract:start\s*-->([\s\S]*?)"
    r"<!--\s*ui-surface-contract:end\s*-->",
    re.IGNORECASE,
)
ENGLISH_SECTION_RE = re.compile(
    r"^##\s+UI Surface Contract\s*$([\s\S]*?)(?=^##\s|\Z)", re.MULTILINE
)


def _values(value: str) -> list[str]:
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


def _state(value: str) -> str:
    state = value.strip().strip("`").strip()
    name, separator, marker = state.partition(":")
    if separator and marker.strip().casefold().startswith("n/a"):
        return f"{name.strip()}:n/a"
    return state


def _responsive(value: str) -> tuple[str | None, list[str], str | None]:
    kind, separator, raw_values = value.strip().partition(":")
    if not separator or kind not in {"viewports", "sizeClasses"}:
        return (
            None,
            [],
            "must use `viewports: ...` for web or `sizeClasses: ...` "
            "for native or desktop",
        )
    values = _values(raw_values)
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


def parse_prd_ui_contract(
    text: str,
    *,
    require_responsive: bool = False,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    blocks = list(MACHINE_BLOCK_RE.finditer(text))
    start_count = len(
        re.findall(r"<!--\s*ui-surface-contract:start\s*-->", text, re.I)
    )
    end_count = len(
        re.findall(r"<!--\s*ui-surface-contract:end\s*-->", text, re.I)
    )
    legacy_block = ENGLISH_SECTION_RE.search(text)
    has_ui_entry = UI_HEADING_RE.search(text) is not None
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
        body = text
    all_headings = list(UI_HEADING_RE.finditer(text))
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
    headings = list(UI_HEADING_RE.finditer(body))
    if blocks and not headings:
        errors.append("prd: ui-surface-contract boundary contains no UI surface entries")
    entries: dict[str, dict[str, Any]] = {}
    for index, heading in enumerate(headings):
        surface_id = heading.group(1)
        if surface_id in entries:
            errors.append(f"prd: duplicate UI surface heading {surface_id}")
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        surface_block = body[heading.end() : end]
        route_matches = list(ROUTE_RE.finditer(surface_block))
        states_matches = list(STATES_RE.finditer(surface_block))
        responsive_matches = list(RESPONSIVE_RE.finditer(surface_block))
        routes = _values(route_matches[0].group(1)) if len(route_matches) == 1 else []
        states = (
            [_state(item) for item in _values(states_matches[0].group(1))]
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
        if len(responsive_matches) == 1:
            responsive_kind, responsive_targets, responsive_error = _responsive(
                responsive_matches[0].group(1)
            )
            if responsive_error:
                errors.append(
                    f"prd: UI surface {surface_id} `responsive` {responsive_error}"
                )
        elif require_responsive or responsive_matches:
            errors.append(
                f"prd: UI surface {surface_id} requires exactly one `responsive` "
                f"anchor; found {len(responsive_matches)}"
            )
        entries[surface_id] = {
            "routes": routes,
            "states": states,
            "responsiveKind": responsive_kind,
            "responsiveTargets": responsive_targets,
        }
    if require_responsive:
        responsive_sets = {
            (
                entry["responsiveKind"],
                tuple(entry["responsiveTargets"]),
            )
            for entry in entries.values()
            if entry["responsiveKind"] is not None
        }
        if len(responsive_sets) > 1:
            errors.append(
                "prd: every UI surface must use the same ordered responsive set"
            )
    return entries, errors


def _screens(data: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    screens: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for screen in data.get("screens") or []:
        if not isinstance(screen, dict) or not isinstance(screen.get("id"), str):
            continue
        screen_id = screen["id"]
        if screen_id in screens:
            errors.append(f"wireframes: duplicate screen id {screen_id}")
        screens[screen_id] = screen
    return screens, errors


def _screen_states(screen: dict[str, Any]) -> set[str]:
    return {
        _state(item["id"])
        for item in (screen.get("states") or [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def validate_prd_wireframe_data(text: str, data: dict[str, Any]) -> list[str]:
    prd_surfaces, errors = parse_prd_ui_contract(text, require_responsive=True)
    screens, screen_errors = _screens(data)
    errors.extend(screen_errors)
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
        screen = screens[surface_id]
        if len(routes) == 1 and routes[0] != screen.get("route"):
            errors.append(
                f"wireframes: screen {surface_id} route {screen.get('route')!r} "
                f"differs from the PRD route {routes[0]!r}"
            )
        prd_states = set(prd_surfaces[surface_id]["states"])
        wireframe_states = _screen_states(screen)
        if prd_states != wireframe_states:
            errors.append(
                f"wireframes: screen {surface_id} states {sorted(wireframe_states)} "
                f"differ from the PRD states {sorted(prd_states)}"
            )
        has_viewports = isinstance(data.get("viewports"), list)
        has_size_classes = isinstance(data.get("sizeClasses"), list)
        if has_viewports == has_size_classes:
            continue
        responsive_kind = "viewports" if has_viewports else "sizeClasses"
        raw_targets = data.get(responsive_kind)
        wireframe_targets = [
            str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
            for value in raw_targets or []
        ]
        prd_targets = prd_surfaces[surface_id]["responsiveTargets"]
        if (
            prd_surfaces[surface_id]["responsiveKind"] != responsive_kind
            or prd_targets != wireframe_targets
        ):
            errors.append(
                f"wireframes: screen {surface_id} responsive set "
                f"{responsive_kind} {wireframe_targets} differs from the PRD "
                f"{prd_surfaces[surface_id]['responsiveKind']} "
                f"{prd_targets}"
            )
    return errors

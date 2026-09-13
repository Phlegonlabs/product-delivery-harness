#!/usr/bin/env python3
"""Parse and compare the Product Definition Builder's invariant UI contract anchors."""

from __future__ import annotations

import json
import math
import re
from typing import Any

from markdown_contract import active_markdown_lines, exact_marker_lines

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
COPY_RE = re.compile(
    r"^\s*-\s*`copy`\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
COMPLETE_FIELD_PATTERNS = {
    "Main purpose": re.compile(
        r"^\s*-\s*Main purpose\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE
    ),
    "Content responsibilities": re.compile(
        r"^\s*-\s*Content responsibilities\s*:\s*(.+)$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "Actions and transitions": re.compile(
        r"^\s*-\s*Actions and transitions\s*:\s*(.+)$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "Responsive obligations": re.compile(
        r"^\s*-\s*Responsive obligations\s*:\s*(.+)$",
        re.IGNORECASE | re.MULTILINE,
    ),
    "Accessibility": re.compile(
        r"^\s*-\s*Accessibility\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE
    ),
    "SEO metadata": re.compile(
        r"^\s*-\s*SEO metadata\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE
    ),
    "Trace IDs": re.compile(
        r"^\s*-\s*Trace IDs\s*:\s*(.+)$", re.IGNORECASE | re.MULTILINE
    ),
}
VALID_COPY_STATUSES = {"draft", "approved", "revision_requested", "blocked"}
UI_START_MARKER = "<!-- ui-surface-contract:start -->"
UI_END_MARKER = "<!-- ui-surface-contract:end -->"


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


def _duplicate_values(values: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value.casefold()] = counts.get(value.casefold(), 0) + 1
    return sorted(
        value for value, count in counts.items() if count > 1
    )


def _copy_status(value: str) -> str:
    status = re.split(r"\s+(?:—|-)\s+", value.strip(), maxsplit=1)[0]
    return status.strip().strip("`").casefold()


def _meaningful(value: str, minimum: int) -> bool:
    stripped = value.strip()
    return (
        len(stripped) >= minimum
        and not re.search(r"\[[^\]]+\]|<[^>]+>|\b(?:tbd|todo)\b", stripped, re.I)
    )


def _responsive(
    value: str, *, web_floor: int = 2
) -> tuple[str | None, list[str], str | None]:
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
    floor_words = {2: "two", 3: "three"}
    minimum = web_floor if kind == "viewports" else 2
    if len(normalized) < minimum:
        if kind == "viewports":
            return (
                kind,
                normalized,
                "must declare at least "
                f"{floor_words.get(minimum, str(minimum))} responsive viewports for web",
            )
        return kind, normalized, "must declare at least two responsive size classes"
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
    require_copy: bool = False,
    require_complete: bool = False,
    web_floor: int = 2,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    active = active_markdown_lines(text)
    start_lines = exact_marker_lines(text, UI_START_MARKER)
    end_lines = exact_marker_lines(text, UI_END_MARKER)
    start_count = len(start_lines)
    end_count = len(end_lines)
    has_ui_entry = UI_HEADING_RE.search("\n".join(line for _, line in active)) is not None
    if not (start_count or end_count or has_ui_entry):
        ui_pending = re.search(
            r"^UI design:\s*pending explicit ui-design-builder request",
            "\n".join(line for _, line in active),
            re.IGNORECASE | re.MULTILINE,
        )
        if not ui_pending:
            return {}, []
    errors: list[str] = []
    if start_count != 1 or end_count != 1:
        errors.append(
            "prd: UI surface contract requires exactly one matched "
            "ui-surface-contract boundary pair"
        )
    body = ""
    headings_in_boundary = 0
    if start_count == 1 and end_count == 1:
        start_line = start_lines[0]
        end_line = end_lines[0]
        body = "\n".join(
            line for number, line in active if start_line < number < end_line
        )
        heading_lines = {
            number
            for number, line in active
            if start_line < number < end_line
            and UI_HEADING_RE.match(line)
        }
        headings_in_boundary = len(heading_lines)
        outside_ids = sorted(
            {
                UI_HEADING_RE.match(line).group(1)
                for number, line in active
                if (number <= start_line or number >= end_line)
                and UI_HEADING_RE.match(line)
            }
        )
        if outside_ids:
            errors.append(
                "prd: UI surface headings outside the ui-surface-contract boundary: "
                + ", ".join(outside_ids)
            )
    headings = list(UI_HEADING_RE.finditer(body))
    if start_count == 1 and end_count == 1 and headings_in_boundary == 0:
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
        copy_matches = list(COPY_RE.finditer(surface_block))
        complete_matches = {
            label: list(pattern.finditer(surface_block))
            for label, pattern in COMPLETE_FIELD_PATTERNS.items()
        }
        routes = _values(route_matches[0].group(1)) if len(route_matches) == 1 else []
        raw_states = (
            _values(states_matches[0].group(1))
            if len(states_matches) == 1
            else []
        )
        states = (
            [_state(item) for item in raw_states]
            if len(states_matches) == 1
            else []
        )
        duplicate_states = _duplicate_values(states)
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
        if require_complete and re.fullmatch(
            rf"###\s+{re.escape(surface_id)}\s+(?:—|-)\s+\S.*",
            heading.group(0),
            re.IGNORECASE,
        ) is None:
            errors.append(
                f"prd: UI surface {surface_id} heading must include a meaningful name"
            )
        if len(states_matches) != 1:
            errors.append(
                f"prd: UI surface {surface_id} requires exactly one `states` anchor; "
                f"found {len(states_matches)}"
            )
        if not states:
            errors.append(f"prd: UI surface {surface_id} has no states value")
        if duplicate_states:
            errors.append(
                f"prd: UI surface {surface_id} has duplicate states: "
                + ", ".join(duplicate_states)
            )
        responsive_kind: str | None = None
        responsive_targets: list[str] = []
        if len(responsive_matches) == 1:
            responsive_kind, responsive_targets, responsive_error = _responsive(
                responsive_matches[0].group(1), web_floor=web_floor
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
        copy_status: str | None = None
        if len(copy_matches) == 1:
            copy_status = _copy_status(copy_matches[0].group(1))
            if copy_status not in VALID_COPY_STATUSES:
                errors.append(
                    f"prd: UI surface {surface_id} `copy` must start with one of "
                    f"{sorted(VALID_COPY_STATUSES)}"
                )
        elif require_copy or copy_matches:
            errors.append(
                f"prd: UI surface {surface_id} requires exactly one `copy` "
                f"anchor; found {len(copy_matches)}"
            )
        complete_values: dict[str, str] = {}
        if require_complete:
            for label, matches in complete_matches.items():
                if len(matches) != 1:
                    errors.append(
                        f"prd: UI surface {surface_id} requires exactly one {label!r} "
                        f"field; found {len(matches)}"
                    )
                    continue
                complete_values[label] = matches[0].group(1).strip()
            minimums = {
                "Main purpose": 12,
                "Content responsibilities": 30,
                "Actions and transitions": 20,
                "Responsive obligations": 25,
                "Accessibility": 15,
                "SEO metadata": 15,
            }
            for label, minimum in minimums.items():
                value = complete_values.get(label)
                if value is not None and not _meaningful(value, minimum):
                    errors.append(
                        f"prd: UI surface {surface_id} {label!r} is not implementation-ready"
                    )
            content = complete_values.get("Content responsibilities", "").casefold()
            if content and not all(
                term in content
                for term in ("source", "order", "format", "count", "length", "fallback")
            ):
                errors.append(
                    f"prd: UI surface {surface_id} Content responsibilities must name "
                    "source/order/format/count/length/fallback bounds"
                )
            actions = complete_values.get("Actions and transitions", "").casefold()
            if actions and not ("success" in actions and "failure" in actions):
                errors.append(
                    f"prd: UI surface {surface_id} Actions and transitions must name "
                    "success and failure behavior"
                )
            responsive_value = complete_values.get("Responsive obligations", "").casefold()
            if responsive_value and "never drop" not in responsive_value:
                errors.append(
                    f"prd: UI surface {surface_id} Responsive obligations must name "
                    "never-drop content/actions"
                )
            trace_value = complete_values.get("Trace IDs", "")
            for prefix in ("PRD", "UX", "ARCH", "TEST"):
                if re.search(rf"\b{prefix}-[A-Z0-9-]+\b", trace_value, re.I) is None:
                    errors.append(
                        f"prd: UI surface {surface_id} Trace IDs must include {prefix}-*"
                    )
        entries[surface_id] = {
            "routes": routes,
            "states": states,
            "responsiveKind": responsive_kind,
            "responsiveTargets": responsive_targets,
            "copyStatus": copy_status,
            "contractFields": complete_values,
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
    route_owners: dict[str, str] = {}
    for surface_id, entry in entries.items():
        route = entry.get("routes", [None])[0] if entry.get("routes") else None
        if not isinstance(route, str) or route.casefold() in {"n/a", "na"}:
            continue
        previous = route_owners.get(route)
        if previous is not None:
            errors.append(
                f"prd: duplicate non-n/a route {route!r} is used by {previous} and {surface_id}"
            )
        else:
            route_owners[route] = surface_id
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


def validate_prd_wireframe_data(
    text: str, data: dict[str, Any], *, web_floor: int = 2
) -> list[str]:
    copy_contract = data.get("schema") == "wireframes/4"
    prd_surfaces, errors = parse_prd_ui_contract(
        text,
        require_responsive=True,
        require_copy=copy_contract,
        web_floor=web_floor,
    )
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
        if copy_contract:
            prd_status = prd_surfaces[surface_id]["copyStatus"]
            wireframe_status = screen.get("copyStatus")
            copy_advances_from_draft = (
                prd_status == "draft"
                and wireframe_status == "approved"
            )
            if prd_status in {"revision_requested", "blocked"}:
                errors.append(
                    f"wireframes: screen {surface_id} cannot proceed while the PRD "
                    f"copy status is {prd_status!r}"
                )
            elif not copy_advances_from_draft and prd_status != wireframe_status:
                errors.append(
                    f"wireframes: screen {surface_id} copy status "
                    f"{screen.get('copyStatus')!r} differs from the PRD copy status "
                    f"{prd_surfaces[surface_id]['copyStatus']!r}"
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

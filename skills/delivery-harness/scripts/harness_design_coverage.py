#!/usr/bin/env python3
"""Shared validation and capture projection for PLAN design coverage."""

from __future__ import annotations

from typing import Any


DESIGN_COVERAGE_SCHEMA = "ui-design-coverage/1"
DESIGN_COVERAGE_CONDITIONS = ("long-content", "reduced-motion", "mobile-reflow")


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def state_marker(state: str) -> tuple[str, bool]:
    """Keep the existing state/n/a spelling rules in every projection."""

    name, separator, marker = state.partition(":")
    return name.strip(), bool(separator and marker.strip().casefold().startswith("n/a"))


def _product_state_names(states: Any) -> tuple[set[str], set[str]]:
    """Return all declared names and names available as condition bases."""

    names: set[str] = set()
    active: set[str] = set()
    if not isinstance(states, list):
        return names, active
    for state in states:
        if not _nonempty_string(state):
            continue
        name, excluded = state_marker(state)
        names.add(name)
        if not excluded:
            active.add(name)
    return names, active


def _entry_errors(
    items: Any,
    *,
    kind: str,
    required_keys: set[str],
    path: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        errors.append(f"{path}.{kind}: must be a list")
        return []
    entries: list[dict[str, Any]] = []
    identity: dict[str, str] = {}
    for index, item in enumerate(items):
        item_path = f"{path}.{kind}[{index}]"
        if not isinstance(item, dict) or set(item) != required_keys:
            errors.append(
                f"{item_path}: must be an object with "
                + ", ".join(sorted(required_keys))
            )
            continue
        identifier = item["id" if kind == "conditions" else "state"]
        if not _nonempty_string(identifier):
            errors.append(f"{item_path}.{'id' if kind == 'conditions' else 'state'}: must be a non-empty string")
            continue
        canonical = identifier.strip()
        if identifier != canonical:
            errors.append(f"{item_path}: identity must not have surrounding whitespace")
        if canonical in identity:
            errors.append(
                f"{path}.{kind}: duplicates {identifier!r} from "
                f"{identity[canonical]}"
            )
            continue
        identity[canonical] = item_path
        if kind == "not_applicable":
            reason = item["reason"]
            if (
                not _nonempty_string(reason)
                or len(reason.strip()) < 12
                or (reason.strip().startswith("<") and reason.strip().endswith(">"))
                or reason.strip().casefold() in {"todo", "tbd", "pending", "n/a", "unknown"}
            ):
                errors.append(f"{item_path}.reason: must be a filled explanation of at least 12 characters")
        entries.append(item)
    return entries


def validate_design_coverage(
    surface: dict[str, Any],
    required_states: set[str] | None = None,
    *,
    base_path: str = "design_coverage",
) -> list[str]:
    """Validate one surface's optional design-coverage projection.

    ``required_states`` is the design system's global state matrix. Without it,
    this proves shape and local joins only; callers with the frozen registry
    also get missing, unknown, and exclusion checks. Product-state authority
    remains with the unchanged PRD and approved-target joins.
    """

    errors: list[str] = []
    coverage = surface.get("design_coverage")
    if "design_coverage" not in surface:
        if required_states is not None:
            legacy_path = (
                base_path[: -len(".design_coverage")]
                if base_path.endswith(".design_coverage")
                else base_path
            )
            state_names, _active_states = _product_state_names(surface.get("states"))
            surface_label = surface.get("id")
            route = surface.get("route")
            location = (
                f"surface {surface_label} route {route} "
                if _nonempty_string(surface_label) and _nonempty_string(route)
                else ""
            )
            for state in sorted(required_states - state_names):
                errors.append(
                    f"{legacy_path}: {location}omits state {state} required "
                    "by the design system's stateMatrix; list it as "
                    f"{state}:n/a when the surface cannot have it"
                )
        return errors
    if not isinstance(coverage, dict):
        errors.append(f"{base_path}: must be an object when present")
        return errors
    if coverage.get("schema") != DESIGN_COVERAGE_SCHEMA:
        errors.append(
            f"{base_path}.schema: must equal {DESIGN_COVERAGE_SCHEMA!r}"
        )
    if set(coverage) != {"schema", "conditions", "not_applicable"}:
        errors.append(f"{base_path}: must contain only schema, conditions, and not_applicable")
    state_names, active_states = _product_state_names(surface.get("states"))
    condition_entries = _entry_errors(
        coverage.get("conditions"),
        kind="conditions",
        required_keys={"id", "base_state"},
        path=base_path,
        errors=errors,
    )
    exclusion_entries = _entry_errors(
        coverage.get("not_applicable"),
        kind="not_applicable",
        required_keys={"state", "reason"},
        path=base_path,
        errors=errors,
    )
    if errors:
        return errors

    condition_ids = {item["id"].strip() for item in condition_entries}
    for index, item in enumerate(condition_entries):
        condition = item["id"].strip()
        base = item["base_state"]
        item_path = f"{base_path}.conditions[{index}]"
        if condition not in DESIGN_COVERAGE_CONDITIONS:
            errors.append(
                f"{item_path}.id: {condition!r} is outside the closed vocabulary "
                f"{'|'.join(DESIGN_COVERAGE_CONDITIONS)}"
            )
        if not _nonempty_string(base):
            errors.append(f"{item_path}.base_state: must be a non-empty string")
        elif base != base.strip() or base not in active_states:
            errors.append(
                f"{item_path}.base_state: {base.strip()!r} is not an active "
                "product state on this surface"
            )

    condition_identities = condition_ids
    excluded_names = {item["state"].strip() for item in exclusion_entries}
    if excluded_names & state_names:
        errors.append(
            f"{base_path}: exclusions collide with product states: "
            + ", ".join(sorted(excluded_names & state_names))
        )
    if condition_identities & excluded_names:
        conflicts = ", ".join(sorted(condition_identities & excluded_names))
        errors.append(
            f"{base_path}: conditions and exclusions conflict: {conflicts}"
        )
    if condition_identities & state_names:
        conflicts = ", ".join(sorted(condition_identities & state_names))
        errors.append(
            f"{base_path}: condition IDs collide with product states: {conflicts}"
        )

    if required_states is None:
        return errors
    covered = state_names | condition_ids | excluded_names
    for state in sorted(required_states - covered):
        errors.append(
            f"{base_path}: surface omits state {state} required by the design "
            "system; account for it with a product state, condition, or reasoned "
            "exclusion"
        )
    unknown = sorted((condition_ids | excluded_names) - required_states)
    if unknown:
        errors.append(
            f"{base_path}: unknown design-system states or conditions: "
            + ", ".join(unknown)
        )
    for condition in sorted(set(DESIGN_COVERAGE_CONDITIONS) & required_states - condition_ids):
        errors.append(f"{base_path}: required universal condition {condition!r} must be an applicable condition")
    for condition in sorted(
        set(DESIGN_COVERAGE_CONDITIONS) & excluded_names & required_states
    ):
        errors.append(
            f"{base_path}.not_applicable: {condition!r} is a required universal "
            "condition and cannot be excluded"
        )
    return errors


def design_coverage_capture_rows(surface: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Return applicable condition rows for one surface, or shape errors."""

    errors = validate_design_coverage(surface)
    if errors or "design_coverage" not in surface:
        return [], errors
    rows: list[dict[str, Any]] = []
    coverage = surface["design_coverage"]
    for breakpoint in surface.get("breakpoints") or []:
        for item in coverage.get("conditions") or []:
            rows.append(
                {
                    "surface_id": surface.get("id"),
                    "route": surface.get("route"),
                    "breakpoint": str(breakpoint),
                    "state": item["id"],
                    "base_state": item["base_state"],
                    "kind": "design-condition",
                }
            )
    return rows, errors


def surface_capture_rows(surface: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Return product rows and condition rows, excluding reasoned n/a states."""

    rows: list[dict[str, Any]] = []
    for breakpoint in surface.get("breakpoints") or []:
        for state in surface.get("states") or []:
            if not _nonempty_string(state):
                continue
            name, excluded = state_marker(state)
            if excluded:
                continue
            rows.append(
                {
                    "surface_id": surface.get("id"),
                    "route": surface.get("route"),
                    "breakpoint": str(breakpoint),
                    "state": name,
                    "kind": "product-state",
                }
            )
    condition_rows, errors = design_coverage_capture_rows(surface)
    return [*rows, *condition_rows], errors

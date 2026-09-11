#!/usr/bin/env python3
"""Join frozen product artifacts to the executable PLAN projection."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path, PureWindowsPath
from typing import Any

from harness_design_contract import compare_design_system_pair
from harness_ui_evidence import validate_ui_surface_design_registry


FROZEN_SOURCE_STATUSES = {"frozen", "delta_accepted", "delta accepted"}
PRD_SOURCE_KINDS = {"prd", "product requirement", "product requirements"}
WIREFRAME_SOURCE_KINDS = {"wireframe", "wireframes", "approved wireframe"}
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
        if len(responsive_matches) > 1:
            errors.append(
                f"prd: UI surface {surface_id} requires exactly one `responsive` "
                f"anchor; found {len(responsive_matches)}"
            )
        elif len(responsive_matches) == 1:
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


def validate_plan_prd_text(plan: dict[str, Any], prd_text: str) -> list[str]:
    prd_surfaces, errors = parse_prd_ui_contract(prd_text)
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
    source: dict[str, Any], repo_root: str | Path, *, label: str
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
    source_path = (root / location).resolve()
    try:
        relative = source_path.relative_to(root).as_posix()
    except ValueError:
        return None, [f"plan.sources: frozen {label} path resolves outside --repo-root"]
    revision = source.get("source_revision")
    if isinstance(revision, str) and revision:
        if FULL_SHA_RE.fullmatch(revision) is None:
            return None, [
                f"plan.sources: frozen {label} source_revision must be a full Git SHA"
            ]
        result = subprocess.run(
            ["git", "show", f"{revision}:{relative}"],
            cwd=root,
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None, [
                f"plan.sources: cannot read frozen {label} bytes at {revision}:{relative}"
            ]
        contents = result.stdout
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


def sibling_builder_scripts_dir() -> Path:
    """The product-definition-builder scripts dir shipped next to this skill."""

    return Path(__file__).resolve().parents[2] / "product-definition-builder" / "scripts"


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


def full_wireframe_checker_errors(
    wireframe_bytes: bytes,
    prd_bytes: bytes | None = None,
    *,
    sibling_scripts: Path | None = None,
) -> list[str]:
    """Run product-definition-builder's full wireframe checker on frozen bytes.

    The harness's own PLAN-side join stays; this adds the checker's wireframe
    structure, reviewer-shell, self-containment, approval, and PRD join rules
    so "approved wireframes.html" means the same thing in both skills. The
    check runs on the resolved bytes written to a temp file, so a source
    frozen at a git revision is still checked as frozen, not as the working
    tree.
    """

    scripts = sibling_scripts or sibling_builder_scripts_dir()
    validate_wireframes = _load_full_wireframe_checker(scripts)
    if validate_wireframes is None:
        return [
            "wireframes: the full wireframe checker is unavailable — install "
            "product-definition-builder next to delivery-harness "
            f"(missing {scripts / 'check_wireframe_html.py'})"
        ]
    with tempfile.TemporaryDirectory() as directory:
        html_path = Path(directory) / "wireframes.html"
        html_path.write_bytes(wireframe_bytes)
        prd_path: Path | None = None
        if prd_bytes is not None:
            prd_path = Path(directory) / "PRD.md"
            prd_path.write_bytes(prd_bytes)
        problems = validate_wireframes(
            html_path,
            require_filled=True,
            require_approved=True,
            prd_path=prd_path,
        )
    rewritten: list[str] = []
    for problem in problems:
        problem = problem.replace(f"{html_path}: ", "wireframes: ")
        if prd_path is not None:
            problem = problem.replace(f"{prd_path}: ", "prd: ")
        rewritten.append(problem)
    return rewritten


def validate_frozen_contract_joins(
    plan: dict[str, Any], repo_root: str | Path
) -> list[str]:
    """Resolve frozen bytes and enforce joins on every execution validation."""

    if plan.get("schema_version") != 6:
        return []
    errors = required_contract_source_errors(plan)
    has_ui = bool(plan.get("ui_surfaces"))
    prd_sources = frozen_sources(
        plan, kinds=PRD_SOURCE_KINDS, filenames={"prd.md"}
    )
    wireframe_sources = frozen_sources(
        plan, kinds=WIREFRAME_SOURCE_KINDS, filenames={"wireframes.html"}
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
    families: list[tuple[str, list[dict[str, Any]]]] = []
    if has_ui or prd_sources:
        families.append(("PRD", prd_sources))
    if has_ui or wireframe_sources:
        families.append(("wireframes", wireframe_sources))
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
    if "PRD" in resolved:
        try:
            errors.extend(validate_plan_prd_text(plan, resolved["PRD"].decode("utf-8")))
        except UnicodeDecodeError as exc:
            errors.append(f"prd: is not valid UTF-8 ({exc})")
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
    registry: Any = None
    if "design-system.json" in resolved:
        try:
            registry = json.loads(resolved["design-system.json"].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"design_system: is not valid JSON ({exc})")
        else:
            errors.extend(validate_ui_surface_design_registry(plan, registry))
    if isinstance(registry, dict) and "design-system.md" in resolved:
        try:
            markdown_text = resolved["design-system.md"].decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"design-system.md: is not valid UTF-8 ({exc})")
        else:
            errors.extend(compare_design_system_pair(markdown_text, registry))
    return sorted(set(errors))

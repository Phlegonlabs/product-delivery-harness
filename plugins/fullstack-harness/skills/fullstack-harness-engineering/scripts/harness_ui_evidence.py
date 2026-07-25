#!/usr/bin/env python3
"""UI screenshot evidence validation and live-Git integration-head cross-checks."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from harness_core import (
    _add,
    _keys,
    _nonempty_string,
    _optional_sha,
    is_full_sha,
)
from harness_schema import (
    GATE_VALUES,
    SHA256_RE,
    UI_EVIDENCE_IMAGE_SUFFIXES,
)


def _valid_ui_artifact_path(value: Any) -> bool:
    if not _nonempty_string(value) or "\\" in value or value.startswith("/"):
        return False
    if re.match(r"^[A-Za-z]:", value):
        return False
    parts = value.split("/")
    return (
        len(parts) >= 4
        and parts[:3] == ["docs", "goal", "evidence"]
        and all(part not in {"", ".", ".."} for part in parts)
        and Path(value).suffix.lower() in UI_EVIDENCE_IMAGE_SUFFIXES
    )


def _has_ui_image_signature(path: Path) -> bool:
    with path.open("rb") as handle:
        header = handle.read(12)
    suffix = path.suffix.lower()
    if suffix == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in {".jpg", ".jpeg"}:
        return header.startswith(b"\xff\xd8\xff")
    return suffix == ".webp" and header[:4] == b"RIFF" and header[8:12] == b"WEBP"


def _validate_ui_evidence(
    errors: list[str], plan: dict[str, Any], run: dict[str, Any]
) -> None:
    evidence_items = run["ui_evidence"]
    if not isinstance(evidence_items, list):
        _add(errors, "run.ui_evidence", "must be a list")
        return

    plan_surfaces = plan.get("ui_surfaces", [])
    if not isinstance(plan_surfaces, list):
        plan_surfaces = []
    surfaces = {
        surface["id"]: surface
        for surface in plan_surfaces
        if isinstance(surface, dict) and _nonempty_string(surface.get("id"))
    }
    seen: set[tuple[str, str, str, str]] = set()
    passed: set[tuple[str, str, str, str]] = set()
    evidence_keys = {
        "surface_id",
        "route",
        "breakpoint",
        "state",
        "artifact_path",
        "artifact_sha256",
        "head_sha",
        "status",
    }
    integration = run.get("integration")
    integration_head = (
        integration.get("integration_head_sha")
        if isinstance(integration, dict)
        else None
    )
    for index, item in enumerate(evidence_items):
        path = f"run.ui_evidence[{index}]"
        if not _keys(errors, path, item, evidence_keys):
            continue
        scalar_fields_valid = True
        for key in ("surface_id", "route", "breakpoint", "state"):
            if not _nonempty_string(item[key]):
                _add(errors, f"{path}.{key}", "must be a non-empty string")
                scalar_fields_valid = False
        if not scalar_fields_valid:
            continue
        surface = surfaces.get(item["surface_id"])
        if surface is None:
            _add(errors, f"{path}.surface_id", "does not match a PLAN UI surface")
        else:
            surface_route = surface.get("route")
            surface_breakpoints = surface.get("breakpoints")
            surface_states = surface.get("states")
            if not _nonempty_string(surface_route) or item["route"] != surface_route:
                _add(errors, f"{path}.route", "does not match the PLAN UI surface")
            if (
                not isinstance(surface_breakpoints, list)
                or item["breakpoint"] not in surface_breakpoints
            ):
                _add(errors, f"{path}.breakpoint", "is not planned for this UI surface")
            if not isinstance(surface_states, list) or item["state"] not in surface_states:
                _add(errors, f"{path}.state", "is not planned for this UI surface")
        key = (
            item["surface_id"],
            item["route"],
            item["breakpoint"],
            item["state"],
        )
        if key in seen:
            _add(errors, path, "duplicates a UI surface/route/breakpoint/state record")
        seen.add(key)
        if not _valid_ui_artifact_path(item["artifact_path"]):
            _add(
                errors,
                f"{path}.artifact_path",
                "must be a repo-relative image under docs/goal/evidence/",
            )
        if not _nonempty_string(item["artifact_sha256"]) or not SHA256_RE.fullmatch(
            item["artifact_sha256"]
        ):
            _add(errors, f"{path}.artifact_sha256", "must be a lowercase SHA-256")
        _optional_sha(errors, f"{path}.head_sha", item["head_sha"])
        if not isinstance(item["status"], str) or item["status"] not in GATE_VALUES:
            _add(errors, f"{path}.status", "has an unsupported gate value")
        elif item["status"] == "PASS":
            if not is_full_sha(item["head_sha"]):
                _add(errors, path, "PASS UI evidence requires head_sha")
            elif not is_full_sha(integration_head) or item["head_sha"] != integration_head:
                _add(errors, path, "PASS UI evidence must match integration_head_sha")
            else:
                passed.add(key)

    if run.get("status") != "complete":
        return
    required: set[tuple[str, str, str, str]] = set()
    for surface in surfaces.values():
        route = surface.get("route")
        breakpoints = surface.get("breakpoints")
        states = surface.get("states")
        if (
            surface.get("evidence_gate") != "required"
            or not _nonempty_string(route)
            or not isinstance(breakpoints, list)
            or not isinstance(states, list)
        ):
            continue
        required.update(
            (surface["id"], route, breakpoint, state)
            for breakpoint in breakpoints
            if _nonempty_string(breakpoint)
            for state in states
            if _nonempty_string(state)
        )
    for key in sorted(required - passed):
        _add(
            errors,
            "run.ui_evidence",
            f"required UI screenshot coverage is missing {'|'.join(key)}",
        )


def validate_ui_surface_recipe_coverage(
    plan: dict[str, Any], ui_registry: str | Path
) -> list[str]:
    """Cross-check the PLAN's UI surfaces against the design package's recipes.

    Required screenshot coverage is otherwise derived only from the PLAN's own
    `ui_surfaces[].states`, so a PLAN that lists `ready` alone validates clean
    and reaches a PASS closeout with one state of eleven. The recipes in
    `ui-registry.json` are the frozen contract, so they decide what a route owes
    (TEST-VIS-021). A state the route genuinely cannot have belongs in the
    recipe as `n/a` with a reason, not omitted from the PLAN.
    """
    errors: list[str] = []
    path = Path(ui_registry)
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        _add(errors, "ui_registry", f"cannot be read ({exc})")
        return errors
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _add(errors, "ui_registry", f"is not valid JSON ({exc})")
        return errors
    if not isinstance(registry, dict):
        _add(errors, "ui_registry", "must be a JSON object")
        return errors
    recipes = registry.get("recipes")
    if not isinstance(recipes, dict):
        _add(errors, "ui_registry.recipes", "must be an object")
        return errors

    surfaces = plan.get("ui_surfaces")
    by_route: dict[str, set[str]] = {}
    if isinstance(surfaces, dict):
        surface_values: Any = surfaces.values()
    elif isinstance(surfaces, list):
        surface_values = surfaces
    else:
        surface_values = []
    for surface in surface_values:
        if not isinstance(surface, dict):
            continue
        route = surface.get("route")
        states = surface.get("states")
        if not _nonempty_string(route):
            continue
        covered = by_route.setdefault(route, set())
        if isinstance(states, list):
            covered.update(state for state in states if _nonempty_string(state))

    for route, recipe in sorted(recipes.items()):
        if not isinstance(recipe, dict):
            continue
        required = recipe.get("requiredStates")
        if not isinstance(required, list):
            continue
        wanted = {
            state
            for state in required
            if _nonempty_string(state) and state.strip().lower() != "n/a"
        }
        if not wanted:
            continue
        if route not in by_route:
            _add(
                errors,
                "plan.ui_surfaces",
                f"has no surface for route {route} required by ui-registry.json",
            )
            continue
        for state in sorted(wanted - by_route[route]):
            _add(
                errors,
                "plan.ui_surfaces",
                f"route {route} omits state {state} required by its recipe",
            )
    return errors


def validate_ui_evidence_files(
    run: dict[str, Any], repo_root: str | Path
) -> list[str]:
    """Verify schema-v9 screenshot files and hashes without mutating the workspace."""

    if run.get("schema_version") != 9 or not isinstance(run.get("ui_evidence"), list):
        return []
    errors: list[str] = []
    root = Path(repo_root).resolve()
    for index, item in enumerate(run["ui_evidence"]):
        if not isinstance(item, dict) or not _valid_ui_artifact_path(
            item.get("artifact_path")
        ):
            continue
        path = f"run.ui_evidence[{index}].artifact_path"
        artifact = (root / item["artifact_path"]).resolve()
        if not artifact.is_relative_to(root):
            _add(errors, path, "resolves outside the repository root")
        elif not artifact.is_file():
            _add(errors, path, f"does not exist: {item['artifact_path']}")
        elif artifact.stat().st_size == 0:
            _add(errors, path, "must not be empty")
        elif not _has_ui_image_signature(artifact):
            _add(errors, path, "content does not match the image file extension")
        elif _nonempty_string(item.get("artifact_sha256")):
            actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
            if actual != item["artifact_sha256"]:
                _add(errors, path, "sha256 does not match artifact_sha256")
    return sorted(set(errors))


def validate_integration_head_against_git(
    run: dict[str, Any], repo_root: str | Path
) -> list[str]:
    """Cross-check run.integration.integration_head_sha against the live Git branch head."""

    integration = run.get("integration")
    if not isinstance(integration, dict):
        return []
    recorded = integration.get("integration_head_sha")
    if recorded is None:
        return []
    path = "run.integration.integration_head_sha"
    errors: list[str] = []
    branch = integration.get("branch")
    if not _nonempty_string(branch):
        _add(errors, path, "could not be verified against live Git: run.integration.branch is not set")
        return sorted(set(errors))
    try:
        result = subprocess.run(
            ["git", "rev-parse", branch],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _add(errors, path, f"could not be verified against live Git: {exc}")
        return sorted(set(errors))
    if result.returncode != 0:
        reason = result.stderr.strip() or f"git rev-parse exited {result.returncode}"
        _add(errors, path, f"could not be verified against live Git: {reason}")
        return sorted(set(errors))
    actual = result.stdout.strip()
    if actual != recorded:
        _add(
            errors,
            path,
            f"({recorded}) does not match the live Git head of branch '{branch}' ({actual}) - RUN.md is stale",
        )
    return sorted(set(errors))

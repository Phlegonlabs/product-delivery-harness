#!/usr/bin/env python3
"""UI screenshot evidence validation and live-Git integration-head cross-checks."""

from __future__ import annotations

import hashlib
import io
import json
import math
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


def _state_marker(state: str) -> tuple[str, bool]:
    """Split a declared state into its name and whether it is marked n/a.

    A surface declares a state it genuinely cannot have as `<state>:n/a`, with an
    optional reason after the marker (`offline:n/a - always online`). Design
    coverage and the closeout screenshot matrix must agree on this, or the only
    honest way to declare an impossible state becomes the one that blocks
    closeout.
    """

    name, separator, marker = state.partition(":")
    if not separator:
        return state.strip(), False
    return name.strip(), marker.strip().lower().startswith("n/a")


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


_UI_IMAGE_FORMATS = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
}
Image: Any = None


def _image_module() -> Any:
    global Image
    if Image is None:
        try:
            from PIL import Image as pillow_image
        except ImportError as exc:
            raise RuntimeError(
                "UI image evidence decoding requires Pillow; install the engineering test dependencies"
            ) from exc
        Image = pillow_image
    return Image


def _ui_image_decode_error(contents: bytes, artifact_path: str | Path) -> str | None:
    """Decode image bytes without reopening a mutable working-tree path."""

    path = Path(artifact_path)
    expected_format = _UI_IMAGE_FORMATS[path.suffix.lower()]
    try:
        image_module = _image_module()
    except RuntimeError as exc:
        # Pillow being unavailable is an environment gap, not evidence corruption.
        # Report it verbatim instead of folding it into "cannot be decoded" below,
        # so an operator (and the gate reason) can tell the two apart.
        return str(exc)
    try:
        with image_module.open(io.BytesIO(contents)) as image:
            decoded_format = image.format
            dimensions = image.size
            image.verify()
        with image_module.open(io.BytesIO(contents)) as image:
            image.load()
    except Exception as exc:
        return f"cannot be decoded as an image ({exc})"
    if decoded_format != expected_format:
        return (
            f"decoded format {decoded_format or 'unknown'} does not match "
            f"the {path.suffix.lower()} file extension"
        )
    if dimensions[0] <= 0 or dimensions[1] <= 0:
        return "decoded image must have non-zero dimensions"
    return None


def _read_git_artifact_blob(
    root: Path, revision: str, artifact_path: str
) -> tuple[bytes | None, str | None]:
    """Read an accepted UI artifact from one Git commit/ref, never the worktree."""

    try:
        result = subprocess.run(
            ["git", "show", "--no-ext-diff", "--format=", f"{revision}:{artifact_path}"],
            cwd=root,
            capture_output=True,
            text=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    if result.returncode != 0:
        reason = result.stderr.decode("utf-8", errors="replace").lower()
        if "not a git repository" in reason:
            return None, (
                f"--repo-root {root} is not a Git checkout "
                "(pass the correct --repo-root)"
            )
        return None, (
            f"accepted Git commit/ref {revision!r} does not contain a readable "
            f"artifact blob at {artifact_path}"
        )
    return result.stdout, None


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
        if run.get("schema_version") in {10, 11} and item["status"] != "PASS" and not is_full_sha(
            item["head_sha"]
        ):
            _add(
                errors,
                path,
                "RUN-v11 UI evidence requires a recorded accepted Git commit/ref in head_sha",
            )
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
        # A state a surface genuinely cannot have is declared as `<state>:n/a`.
        # It still counts as considered for design coverage, but there is no
        # screenshot to capture for it, so it is not required evidence here.
        required.update(
            (surface["id"], route, breakpoint, state)
            for breakpoint in breakpoints
            if _nonempty_string(breakpoint)
            for state in states
            if _nonempty_string(state) and not _state_marker(state)[1]
        )
    for key in sorted(required - passed):
        _add(
            errors,
            "run.ui_evidence",
            f"required UI screenshot coverage is missing {'|'.join(key)}",
        )


def _viewport_label(value: int | float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def _breakpoint_matches_viewport(breakpoint: str, viewport: str) -> bool:
    return re.search(rf"(?:^|[-_\s]){re.escape(viewport)}$", breakpoint) is not None


def validate_ui_surface_design_coverage(
    plan: dict[str, Any], design_system: str | Path
) -> list[str]:
    """Cross-check every in-scope PLAN UI surface against the frozen design system.

    Two obligations are machine-checkable here: a surface covers every state in
    the design system's `stateMatrix`, and it covers every entry in the
    responsive verification set. A state a surface genuinely cannot have is
    covered by listing it as `<state>:n/a`, so an unconsidered state and a
    deliberate exclusion never look the same.
    """

    errors: list[str] = []
    path = Path(design_system)
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        _add(errors, "design_system", f"cannot be read ({exc})")
        return errors
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _add(errors, "design_system", f"is not valid JSON ({exc})")
        return errors
    if not isinstance(registry, dict):
        _add(errors, "design_system", "must be a JSON object")
        return errors
    state_matrix = registry.get("stateMatrix")
    if (
        not isinstance(state_matrix, list)
        or not state_matrix
        or any(not _nonempty_string(state) for state in state_matrix)
    ):
        _add(errors, "design_system.stateMatrix", "must be a non-empty string list")
        return errors
    required_states = {state.strip() for state in state_matrix}

    has_viewports = "viewports" in registry
    has_size_classes = "sizeClasses" in registry
    viewports = registry.get("viewports")
    size_classes = registry.get("sizeClasses")
    valid_viewports = (
        isinstance(viewports, list)
        and bool(viewports)
        and all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
            for value in viewports
        )
        and len(set(viewports)) == len(viewports)
    )
    valid_size_classes = (
        isinstance(size_classes, list)
        and bool(size_classes)
        and all(_nonempty_string(value) for value in size_classes)
        and len(set(size_classes)) == len(size_classes)
    )
    responsive_kind: str | None = None
    responsive_values: list[str] = []
    if (
        has_viewports == has_size_classes
        or (has_viewports and not valid_viewports)
        or (has_size_classes and not valid_size_classes)
    ):
        _add(
            errors,
            "design_system",
            "must define exactly one non-empty unique responsive set: viewports or sizeClasses",
        )
    elif has_viewports:
        responsive_kind = "viewports"
        responsive_values = [_viewport_label(value) for value in viewports]
    else:
        responsive_kind = "sizeClasses"
        responsive_values = list(size_classes)

    surfaces = plan.get("ui_surfaces")
    if isinstance(surfaces, dict):
        surface_values: list[Any] = list(surfaces.values())
    elif isinstance(surfaces, list):
        surface_values = surfaces
    else:
        surface_values = []

    for index, surface in enumerate(surface_values):
        if not isinstance(surface, dict):
            continue
        surface_id = surface.get("id")
        route = surface.get("route")
        if not _nonempty_string(route):
            continue
        surface_label = surface_id if _nonempty_string(surface_id) else str(index)
        plan_path = f"plan.ui_surfaces[{surface_label}]"

        states = surface.get("states")
        covered_states: set[str] = set()
        if isinstance(states, list):
            for state in states:
                if _nonempty_string(state):
                    covered_states.add(_state_marker(state)[0])
        for state in sorted(required_states - covered_states):
            _add(
                errors,
                plan_path,
                f"surface {surface_label} route {route} omits state {state} required "
                f"by the design system's stateMatrix; list it as {state}:n/a when the "
                f"surface cannot have it",
            )

        breakpoints = surface.get("breakpoints")
        covered_breakpoints = (
            [value for value in breakpoints if _nonempty_string(value)]
            if isinstance(breakpoints, list)
            else []
        )
        if responsive_kind == "viewports":
            missing_responsive = [
                value
                for value in responsive_values
                if not any(
                    _breakpoint_matches_viewport(breakpoint, value)
                    for breakpoint in covered_breakpoints
                )
            ]
        elif responsive_kind == "sizeClasses":
            missing_responsive = [
                value for value in responsive_values if value not in covered_breakpoints
            ]
        else:
            missing_responsive = []
        for responsive_value in missing_responsive:
            _add(
                errors,
                plan_path,
                f"surface {surface_label} route {route} omits responsive target "
                f"{responsive_value} required by design-system.json",
            )
    return errors


def validate_ui_evidence_files(
    run: dict[str, Any], repo_root: str | Path
) -> list[str]:
    """Verify screenshot bytes and hashes for RUN-v9/v10.

    RUN-v9 retains its historical working-tree binding. RUN-v11 reads the
    artifact blob from each row's accepted ``head_sha`` first, then decodes and
    hashes those immutable bytes; a working-tree-only or mutated screenshot is
    never accepted for the current evidence contract.
    """

    schema_version = run.get("schema_version")
    if schema_version not in {9, 10, 11} or not isinstance(
        run.get("ui_evidence"), list
    ):
        return []
    errors: list[str] = []
    root = Path(repo_root).resolve()
    for index, item in enumerate(run["ui_evidence"]):
        if not isinstance(item, dict) or not _valid_ui_artifact_path(
            item.get("artifact_path")
        ):
            continue
        path = f"run.ui_evidence[{index}].artifact_path"
        artifact_bytes: bytes | None = None
        if schema_version in {10, 11}:
            head_sha = item.get("head_sha")
            if not isinstance(head_sha, str) or not is_full_sha(head_sha):
                _add(
                    errors,
                    path,
                    "RUN-v11 evidence requires a recorded accepted Git commit/ref in head_sha",
                )
                continue
            artifact_bytes, reason = _read_git_artifact_blob(
                root, head_sha, item["artifact_path"]
            )
            if artifact_bytes is None:
                _add(
                    errors,
                    path,
                    f"artifact does not exist in accepted Git commit/ref {head_sha!r}: "
                    f"{reason or 'git show could not read the blob'}",
                )
                continue
        else:
            artifact = (root / item["artifact_path"]).resolve()
            if not artifact.is_relative_to(root):
                _add(errors, path, "resolves outside the repository root")
                continue
            if not artifact.is_file():
                _add(errors, path, f"does not exist: {item['artifact_path']}")
                continue
            try:
                artifact_bytes = artifact.read_bytes()
            except OSError as exc:
                _add(errors, path, f"cannot read artifact: {exc}")
                continue

        if not artifact_bytes:
            _add(errors, path, "must not be empty")
            continue
        if image_error := _ui_image_decode_error(artifact_bytes, item["artifact_path"]):
            _add(errors, path, image_error)
        elif _nonempty_string(item.get("artifact_sha256")):
            actual = hashlib.sha256(artifact_bytes).hexdigest()
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
    if not isinstance(branch, str) or not _nonempty_string(branch):
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
        # Git's own wording for "no repository here" is stable across versions
        # ("fatal: not a git repository ..."). Surfacing that distinctly, instead
        # of the generic wrapper, turns a wrong --repo-root/cwd into an accurate,
        # actionable cause rather than looking like an ordinary rev-parse failure
        # (e.g. an unknown branch) on a real checkout.
        if "not a git repository" in reason:
            _add(
                errors,
                path,
                f"could not be verified against live Git: --repo-root {repo_root} "
                "is not a Git checkout (pass the correct --repo-root)",
            )
        else:
            _add(errors, path, f"could not be verified against live Git: {reason}")
        return sorted(set(errors))
    actual = result.stdout.strip()
    if actual != recorded and run.get("schema_version") == 11:
        ancestry = subprocess.run(
            ["git", "merge-base", "--is-ancestor", recorded, actual],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        changed = subprocess.run(
            ["git", "diff", "--name-only", f"{recorded}..{actual}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        coordination_paths = set(integration.get("coordination_paths", []))
        changed_paths = {
            line.strip().replace("\\", "/")
            for line in changed.stdout.splitlines()
            if line.strip()
        }
        if ancestry.returncode == 0 and changed.returncode == 0 and changed_paths.issubset(coordination_paths):
            return []
    if actual != recorded:
        _add(
            errors,
            path,
            f"({recorded}) does not match the live Git head of branch '{branch}' ({actual}) - RUN.md is stale",
        )
    return sorted(set(errors))

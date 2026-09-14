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

from harness_design_contract import validate_design_system_registry
from harness_git import GitMetadataError, reject_object_substitution, run_git
from harness_core import (
    _add,
    read_git_blob,
    _keys,
    _nonempty_string,
    _optional_sha,
    is_full_sha,
)
from harness_schema import (
    GATE_VALUES,
    SHA256_RE,
    UI_EVIDENCE_IMAGE_SUFFIXES,
    run_required_harness_version,
    version_at_least,
)


DS_TRACE_ID_RE = re.compile(r"^DS-(?:[A-Z]+-)?[0-9]+$")


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

    payload, reason = read_git_blob(
        root,
        revision,
        artifact_path,
        (
            f"accepted Git commit/ref {revision!r} does not contain a readable "
            f"artifact blob at {artifact_path}"
        ),
    )
    if payload is None and reason == "--repo-root is not a Git checkout":
        return None, (
            f"--repo-root {root} is not a Git checkout "
            "(pass the correct --repo-root)"
        )
    return payload, reason


UI_TARGET_COMPARISON_BASELINES = {"html_target", "design_system"}
UI_TARGET_COMPARISON_VERDICTS = {"pass", "deviation"}
UI_EVIDENCE_REQUIRED_VERSION = (0, 38, 0)
UI_CAPTURE_MODES = {
    "hosted-browser",
    "browser-extension",
    "native",
    "desktop",
}
UI_CAPTURE_METHODS = {
    "hosted-browser": {"browser"},
    "browser-extension": {"browser-extension"},
    "native": {"native-ui-test", "manual-native"},
    "desktop": {"desktop-ui-test", "manual-desktop"},
}


def _strict_ui_evidence_required(run: dict[str, Any]) -> bool:
    """Whether the current RUN requires platform-bound v0.38 evidence.

    Older RUN-v11 files remain readable for recovery.  The stricter capture
    and immutable baseline contract is activated only by an explicit version
    pin, so a legacy archive operation cannot be made invalid merely by
    importing this module.
    """

    return run.get("schema_version") == 11 and version_at_least(
        run_required_harness_version(run), UI_EVIDENCE_REQUIRED_VERSION
    )


def _valid_source_path(value: Any) -> bool:
    """Accept only repository-relative POSIX source paths."""

    if not _nonempty_string(value) or "\\" in value or value.startswith("/"):
        return False
    if re.match(r"^[A-Za-z]:", value):
        return False
    parts = value.split("/")
    return all(part not in {"", ".", ".."} for part in parts)


def _source_rows(plan: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(plan, dict) or not isinstance(plan.get("sources"), list):
        return []
    return [row for row in plan["sources"] if isinstance(row, dict)]


def _source_identity(row: dict[str, Any]) -> dict[str, str] | None:
    """Convert a frozen PLAN source row to the evidence identity shape."""

    path = row.get("location")
    digest = row.get("content_sha256")
    if not _valid_source_path(path) or not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        return None
    return {"path": path, "sha256": digest}


def _expected_authority_sources(
    plan: dict[str, Any] | None, baseline: str
) -> list[dict[str, str]] | None:
    """Resolve the exact frozen visual authority rows for a baseline.

    Harness 0.38 freezes the approved target as an explicit ``approved ui
    target`` PLAN source.  A required design system uses the two pair rows in
    semantic order (Markdown first, then JSON); it never accepts an arbitrary
    contract-check key.
    """

    rows = _source_rows(plan)
    if not rows:
        return None
    if baseline == "html_target":
        matches = [row for row in rows if row.get("kind") == "approved ui target"]
        if len(matches) != 1:
            return []
        identity = _source_identity(matches[0])
        return [identity] if identity is not None else []
    if baseline == "design_system":
        markdown = [
            row
            for row in rows
            if row.get("kind") in {"design system markdown", "design system"}
        ]
        registry = [
            row
            for row in rows
            if row.get("kind") in {"design system machine", "design system json"}
        ]
        if len(markdown) != 1 or len(registry) != 1:
            return []
        identities = [_source_identity(markdown[0]), _source_identity(registry[0])]
        return [identity for identity in identities if identity is not None] \
            if all(identity is not None for identity in identities) else []
    return None


def _surface_for_evidence(
    plan: dict[str, Any] | None, item: dict[str, Any]
) -> dict[str, Any] | None:
    if not isinstance(plan, dict) or not isinstance(plan.get("ui_surfaces"), list):
        return None
    surface_id = item.get("surface_id")
    return next(
        (
            surface
            for surface in plan["ui_surfaces"]
            if isinstance(surface, dict) and surface.get("id") == surface_id
        ),
        None,
    )

UI_LAYOUT_CHECK_PREFIXES = ("fail", "manual", "n/a")
UI_LAYOUT_CHECK_REQUIRED_VERSION = (0, 34, 0)
UI_DEVIATION_LEDGER_REQUIRED_VERSION = (0, 35, 0)
UI_IMPACT_VALUES = {"none", "style", "structure", "both"}


def _layout_check_required(run: dict[str, Any]) -> bool:
    """RUN-v11 files pinned to harness 0.34.0+ carry layout_check on every row.

    Runs without the version gate, or pinned to an older harness, keep their
    frozen row shape so in-flight RUN files stay valid.
    """

    return run.get("schema_version") == 11 and version_at_least(
        run_required_harness_version(run), UI_LAYOUT_CHECK_REQUIRED_VERSION
    )


def _validate_layout_check(
    errors: list[str], path: str, item: dict[str, Any], *, required: bool
) -> None:
    """Check one ui_evidence row's recorded layout geometry result.

    `pass` comes from a real-browser DOM geometry scan (or native UI-test
    layout assertions); `fail — …` records the offending selectors, and a
    PASS row carrying it is a contradiction that blocks the gate;
    `manual — …` and `n/a — …` record their basis or reason.
    """

    if not required and "layout_check" not in item:
        return
    value = item.get("layout_check")
    if not _nonempty_string(value):
        _add(errors, f"{path}.layout_check", "must be a non-empty string")
        return
    if value == "pass":
        return
    if any(value.startswith(f"{prefix} — ") for prefix in UI_LAYOUT_CHECK_PREFIXES):
        return
    _add(
        errors,
        f"{path}.layout_check",
        "must be `pass`, or `fail — <selectors>`, `manual — <basis>`, "
        "or `n/a — <reason>`",
    )


UI_DEVIATION_LEDGER_ROW_KEYS = {
    "surface_id",
    "route",
    "breakpoint",
    "state",
    "difference",
    "citation",
}


def _deviation_ledger_required(run: dict[str, Any]) -> bool:
    """RUN-v11 files pinned to harness 0.35.0+ carry the deviation ledger.

    Runs without the version gate, or pinned to an older harness, keep
    their frozen shape so in-flight RUN files stay valid.
    """

    return run.get("schema_version") == 11 and version_at_least(
        run_required_harness_version(run), UI_DEVIATION_LEDGER_REQUIRED_VERSION
    )


def validate_deviation_ledger(run: dict[str, Any]) -> list[str]:
    """Cross-check run.deviation_ledger against every accepted deviation.

    Every difference behind a `deviation` target_comparison verdict must
    appear in one ledger row carrying the allowed-deviation citation that
    admits it, and every ledger row must trace back to a real deviation —
    an orphan row is a fabricated citation, not extra bookkeeping.
    """

    errors: list[str] = []
    if not _deviation_ledger_required(run):
        return errors
    deviations: dict[tuple[str, str, str, str], list[str]] = {}
    evidence_items = run.get("ui_evidence")
    if isinstance(evidence_items, list):
        for item in evidence_items:
            if not isinstance(item, dict):
                continue
            comparison = item.get("target_comparison")
            if not isinstance(comparison, dict):
                continue
            if comparison.get("verdict") != "deviation":
                continue
            key = (
                item.get("surface_id"),
                item.get("route"),
                item.get("breakpoint"),
                item.get("state"),
            )
            differences = [
                difference
                for difference in (comparison.get("differences") or [])
                if _nonempty_string(difference)
            ]
            deviations.setdefault(key, []).extend(differences)
    ledger = run.get("deviation_ledger")
    if deviations and ledger is None:
        _add(
            errors,
            "run.deviation_ledger",
            "accepted deviations require a deviation ledger with one cited "
            "row per difference",
        )
        return errors
    if ledger is None:
        return errors
    if not isinstance(ledger, list):
        _add(errors, "run.deviation_ledger", "must be a list")
        return errors
    covered: set[tuple[tuple[str, str, str, str], str]] = set()
    for index, row in enumerate(ledger):
        path = f"run.deviation_ledger[{index}]"
        if not isinstance(row, dict):
            _add(errors, path, "must be an object")
            continue
        if not _keys(errors, path, row, UI_DEVIATION_LEDGER_ROW_KEYS, ()):
            continue
        scalars_valid = True
        for field in sorted(UI_DEVIATION_LEDGER_ROW_KEYS):
            if not _nonempty_string(row.get(field)):
                _add(errors, f"{path}.{field}", "must be a non-empty string")
                scalars_valid = False
        if not scalars_valid:
            continue
        key = (
            row["surface_id"],
            row["route"],
            row["breakpoint"],
            row["state"],
        )
        entry = (key, row["difference"])
        if entry in covered:
            _add(errors, path, "duplicates an earlier ledger row")
            continue
        covered.add(entry)
        if row["difference"] not in deviations.get(key, []):
            _add(
                errors,
                path,
                "has no matching deviation verdict for this surface, route, "
                "breakpoint, state, and difference",
            )
    for key in sorted(deviations):
        for difference in deviations[key]:
            if (key, difference) not in covered:
                _add(
                    errors,
                    "run.deviation_ledger",
                    "required ledger row is missing "
                    f"{'|'.join(key)}|{difference}",
                )
    return errors


def _validate_target_comparison(
    errors: list[str],
    path: str,
    item: dict[str, Any],
    *,
    plan: dict[str, Any] | None = None,
    run: dict[str, Any] | None = None,
) -> None:
    """Check one RUN-v11 ui_evidence row's Final Visual Parity Loop record.

    Every v11 row must state what it was compared against (an approved HTML
    reference render, or the frozen design-system contract) and the verdict;
    a deviation that lists no differences cannot be judged against the PRD
    handoff's allowed deviations.
    """

    comparison = item.get("target_comparison")
    comparison_path = f"{path}.target_comparison"
    if not isinstance(comparison, dict):
        _add(errors, comparison_path, "must be an object")
        return
    strict = _strict_ui_evidence_required(run or {})
    if strict:
        required_keys = {
            "baseline",
            "authority_sources",
            "baseline_artifact",
            "baseline_artifact_sha256",
            "verdict",
            "differences",
        }
        if not _keys(errors, comparison_path, comparison, required_keys):
            return
    baseline = comparison.get("baseline")
    if not isinstance(baseline, str) or baseline not in UI_TARGET_COMPARISON_BASELINES:
        _add(
            errors,
            f"{comparison_path}.baseline",
            f"must be one of {'|'.join(sorted(UI_TARGET_COMPARISON_BASELINES))}",
        )
        return
    baseline_artifact = comparison.get("baseline_artifact")
    if strict or baseline == "html_target":
        if not _valid_ui_artifact_path(baseline_artifact):
            _add(
                errors,
                f"{comparison_path}.baseline_artifact",
                "must be a repo-relative image under docs/goal/evidence/",
            )
    elif not _nonempty_string(baseline_artifact):
        _add(
            errors,
            f"{comparison_path}.baseline_artifact",
            "must be a non-empty contract-check evidence key",
        )
    if strict:
        baseline_digest = comparison.get("baseline_artifact_sha256")
        if not isinstance(baseline_digest, str) or not SHA256_RE.fullmatch(
            baseline_digest
        ):
            _add(
                errors,
                f"{comparison_path}.baseline_artifact_sha256",
                "must be a lowercase SHA-256",
            )
        authority = comparison.get("authority_sources")
        if not isinstance(authority, list) or not authority:
            _add(
                errors,
                f"{comparison_path}.authority_sources",
                "must be a non-empty list of exact frozen source identities",
            )
        else:
            seen_paths: set[str] = set()
            for index, source in enumerate(authority):
                source_path = f"{comparison_path}.authority_sources[{index}]"
                if not _keys(errors, source_path, source, {"path", "sha256"}):
                    continue
                if not _valid_source_path(source.get("path")):
                    _add(
                        errors,
                        f"{source_path}.path",
                        "must be a repository-relative POSIX path",
                    )
                source_sha256 = source.get("sha256")
                if not isinstance(source_sha256, str) or not SHA256_RE.fullmatch(
                    source_sha256
                ):
                    _add(
                        errors,
                        f"{source_path}.sha256",
                        "must be a lowercase SHA-256",
                    )
                source_location = source.get("path")
                if isinstance(source_location, str):
                    if source_location in seen_paths:
                        _add(errors, source_path, "duplicates an earlier authority source")
                    seen_paths.add(source_location)
            expected = _expected_authority_sources(plan, baseline)
            if expected is not None and authority != expected:
                _add(
                    errors,
                    f"{comparison_path}.authority_sources",
                    "must exactly match the frozen PLAN authority source identities",
                )
        surface = _surface_for_evidence(plan, item)
        if surface is not None:
            capture_mode = surface.get("capture_mode")
            if not isinstance(capture_mode, str) or capture_mode not in UI_CAPTURE_MODES:
                _add(
                    errors,
                    f"plan.ui_surfaces[{item.get('surface_id')}].capture_mode",
                    "must be one of browser-extension|desktop|hosted-browser|native",
                )
            elif baseline in UI_TARGET_COMPARISON_BASELINES:
                has_ds_pair = bool(_expected_authority_sources(plan, "design_system"))
                expected_baseline = "design_system" if has_ds_pair else "html_target"
                if baseline != expected_baseline:
                    _add(
                        errors,
                        f"{comparison_path}.baseline",
                        f"must be {expected_baseline} for the frozen Design System Need gate",
                    )
    verdict = comparison.get("verdict")
    if not isinstance(verdict, str) or verdict not in UI_TARGET_COMPARISON_VERDICTS:
        _add(
            errors,
            f"{comparison_path}.verdict",
            f"must be one of {'|'.join(sorted(UI_TARGET_COMPARISON_VERDICTS))}",
        )
        return
    differences = comparison.get("differences")
    has_differences = isinstance(differences, list) and any(
        _nonempty_string(difference) for difference in differences
    )
    if verdict == "deviation" and not has_differences:
        _add(
            errors,
            f"{comparison_path}.differences",
            "a deviation verdict must list every observed difference",
        )
    if verdict == "pass" and differences not in (None, []):
        _add(
            errors,
            f"{comparison_path}.differences",
            "a pass verdict must not list differences",
        )


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
    strict = _strict_ui_evidence_required(run)
    if strict:
        evidence_keys = evidence_keys | {"capture_method", "target_comparison"}
    layout_required = _layout_check_required(run)
    if layout_required:
        evidence_keys = evidence_keys | {"layout_check"}
    integration = run.get("integration")
    integration_head = (
        integration.get("integration_head_sha")
        if isinstance(integration, dict)
        else None
    )
    for index, item in enumerate(evidence_items):
        path = f"run.ui_evidence[{index}]"
        # RUN-v11 adds the Final Visual Parity Loop's target_comparison record
        # to each row; older schemas keep their frozen key set.
        optional_keys = (
            ("target_comparison",) if run.get("schema_version") == 11 else ()
        )
        if strict:
            optional_keys = tuple(key for key in optional_keys if key != "target_comparison")
        if not layout_required:
            optional_keys = tuple(optional_keys) + ("layout_check",)
        if not _keys(errors, path, item, evidence_keys, optional_keys):
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
                "RUN-v10/v11 UI evidence requires a recorded accepted Git commit/ref in head_sha",
            )
        if run.get("schema_version") == 11:
            _validate_target_comparison(errors, path, item, plan=plan, run=run)
        if strict:
            surface = _surface_for_evidence(plan, item)
            capture_mode = surface.get("capture_mode") if surface else None
            capture_method = item.get("capture_method")
            if capture_mode not in UI_CAPTURE_MODES:
                _add(
                    errors,
                    f"{path}.capture_method",
                    "cannot be validated because the PLAN capture_mode is missing or invalid",
                )
            elif not isinstance(capture_method, str) or capture_method not in UI_CAPTURE_METHODS[capture_mode]:
                expected = "|".join(sorted(UI_CAPTURE_METHODS[capture_mode]))
                _add(
                    errors,
                    f"{path}.capture_method",
                    f"must be {expected} for PLAN capture_mode {capture_mode}",
                )
        _validate_layout_check(errors, path, item, required=layout_required)
        if (
            layout_required
            and item["status"] == "PASS"
            and isinstance(item.get("layout_check"), str)
            and item["layout_check"].startswith("fail")
        ):
            _add(
                errors,
                f"{path}.layout_check",
                "a PASS row with a failed layout check is a contradiction; "
                "repair the surface and recapture the matrix entry",
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

    path = Path(design_system)
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        errors: list[str] = []
        _add(errors, "design_system", f"cannot be read ({exc})")
        return errors
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors = []
        _add(errors, "design_system", f"is not valid JSON ({exc})")
        return errors
    return validate_ui_surface_design_registry(plan, registry)


def validate_ui_surface_design_registry(
    plan: dict[str, Any], registry: Any
) -> list[str]:
    """Validate an already byte-bound design-system registry against PLAN."""

    errors: list[str] = []
    if not isinstance(registry, dict):
        _add(errors, "design_system", "must be a JSON object")
        return errors
    errors.extend(validate_design_system_registry(registry))

    registered_ds_ids: dict[str, str] = {}

    def register_ds_id(value: Any, source: str) -> None:
        if not isinstance(value, str):
            return
        if DS_TRACE_ID_RE.fullmatch(value) is None:
            _add(errors, source, f"contains malformed design-system id {value!r}")
            return
        prior = registered_ds_ids.get(value)
        if prior is not None:
            _add(
                errors,
                source,
                f"duplicates design-system id {value!r} already registered at {prior}",
            )
            return
        registered_ds_ids[value] = source

    for namespace in ("primitives", "productComponents"):
        entries = registry.get(namespace)
        if not isinstance(entries, dict):
            continue
        for name, spec in entries.items():
            if isinstance(spec, dict) and spec.get("dsId") is not None:
                register_ds_id(spec.get("dsId"), f"design_system.{namespace}.{name}.dsId")
    signature_rules = registry.get("signatureRules")
    if isinstance(signature_rules, list):
        for index, rule in enumerate(signature_rules):
            register_ds_id(rule, f"design_system.signatureRules[{index}]")

    for index, trace in enumerate(plan.get("traces") or []):
        if not isinstance(trace, dict):
            continue
        trace_id = trace.get("id")
        if not isinstance(trace_id, str) or not trace_id.startswith("DS-"):
            continue
        if DS_TRACE_ID_RE.fullmatch(trace_id) is None:
            _add(
                errors,
                f"plan.traces[{index}].id",
                f"contains malformed design-system trace {trace_id!r}",
            )
        elif trace_id not in registered_ds_ids:
            _add(
                errors,
                f"plan.traces[{index}].id",
                f"design-system trace {trace_id!r} is absent from design-system.json",
            )
    state_matrix = registry.get("stateMatrix")
    if (
        not isinstance(state_matrix, list)
        or not state_matrix
        or any(not _nonempty_string(state) for state in state_matrix)
    ):
        _add(errors, "design_system.stateMatrix", "must be a non-empty string list")
        return errors
    required_states = {state.strip() for state in state_matrix}

    surface_contracts = registry.get("surfaceContracts")
    has_viewports = "viewports" in registry
    has_size_classes = "sizeClasses" in registry
    viewports = registry.get("viewports")
    size_classes = registry.get("sizeClasses")
    valid_viewports = (
        isinstance(viewports, list)
        and len(viewports) >= 2
        and all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
            for value in viewports
        )
        and len(set(viewports)) == len(viewports)
        and all(left < right for left, right in zip(viewports, viewports[1:]))
    )
    valid_size_classes = (
        isinstance(size_classes, list)
        and len(size_classes) >= 2
        and all(_nonempty_string(value) for value in size_classes)
        and len(set(size_classes)) == len(size_classes)
    )
    responsive_kind: str | None = None
    responsive_values: list[str] = []
    if not isinstance(surface_contracts, dict) and (
        has_viewports == has_size_classes
        or (has_viewports and not valid_viewports)
        or (has_size_classes and not valid_size_classes)
    ):
        _add(
            errors,
            "design_system",
            "must define exactly one non-empty unique responsive set with at least "
            "two targets: viewports or sizeClasses",
        )
    elif not isinstance(surface_contracts, dict) and has_viewports:
        responsive_kind = "viewports"
        responsive_values = [_viewport_label(value) for value in viewports]
    elif not isinstance(surface_contracts, dict):
        responsive_kind = "sizeClasses"
        responsive_values = list(size_classes)

    if isinstance(surface_contracts, dict):
        responsive_kind = None
        responsive_values = []

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
        surface_responsive_kind = responsive_kind
        surface_responsive_values = responsive_values
        if isinstance(surface_contracts, dict):
            contract = surface_contracts.get(surface_id)
            if not isinstance(contract, dict):
                _add(errors, plan_path, "surface is missing from design-system.json surfaceContracts")
            else:
                for plan_key, contract_key in (
                    ("release_surface", "releaseSurface"),
                    ("surface_class", "surfaceClass"),
                    ("capture_mode", "captureMode"),
                ):
                    if plan_key in surface and surface.get(plan_key) != contract.get(contract_key):
                        _add(errors, plan_path, f"{plan_key} differs from design-system.json surfaceContracts")
                responsive = contract.get("responsive")
                if isinstance(responsive, dict):
                    surface_responsive_kind = responsive.get("kind")
                    values = responsive.get("targets")
                    surface_responsive_values = (
                        [_viewport_label(value) for value in values]
                        if surface_responsive_kind == "viewports" and isinstance(values, list)
                        else list(values) if isinstance(values, list) else []
                    )

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
        if surface_responsive_kind == "viewports":
            missing_responsive = [
                value
                for value in surface_responsive_values
                if not any(
                    _breakpoint_matches_viewport(breakpoint, value)
                    for breakpoint in covered_breakpoints
                )
            ]
            extra_responsive = [
                breakpoint
                for breakpoint in covered_breakpoints
                if not any(
                    _breakpoint_matches_viewport(breakpoint, value)
                for value in surface_responsive_values
                )
            ]
        elif surface_responsive_kind == "sizeClasses":
            missing_responsive = [
                value for value in surface_responsive_values if value not in covered_breakpoints
            ]
            extra_responsive = [
                value for value in covered_breakpoints if value not in surface_responsive_values
            ]
        else:
            missing_responsive = []
            extra_responsive = []
        for responsive_value in missing_responsive:
            _add(
                errors,
                plan_path,
                f"surface {surface_label} route {route} omits responsive target "
                f"{responsive_value} required by design-system.json",
            )
        for responsive_value in extra_responsive:
            _add(
                errors,
                plan_path,
                f"surface {surface_label} route {route} adds responsive target "
                f"{responsive_value} absent from design-system.json",
            )
    return errors


def validate_ui_evidence_files(
    plan_or_run: dict[str, Any],
    run_or_repo_root: dict[str, Any] | str | Path,
    repo_root: str | Path | None = None,
) -> list[str]:
    """Verify screenshot bytes and hashes for RUN-v9/v10/v11.

    RUN-v9 retains its historical working-tree binding. RUN-v11 reads the
    artifact blob from each row's accepted ``head_sha`` first, then decodes and
    hashes those immutable bytes; a working-tree-only or mutated screenshot is
    never accepted for the current evidence contract.  The preferred v0.38
    signature is ``(plan, run, repo_root)``.  ``(run, repo_root)`` remains
    accepted for archive/recovery callers and retains legacy shape checks.
    """

    if repo_root is None:
        run = plan_or_run
        root_arg = run_or_repo_root
    else:
        run = run_or_repo_root if isinstance(run_or_repo_root, dict) else {}
        root_arg = repo_root

    schema_version = run.get("schema_version")
    if schema_version not in {9, 10, 11} or not isinstance(
        run.get("ui_evidence"), list
    ):
        return []
    errors: list[str] = []
    root = Path(root_arg).resolve()
    # File validation remains strict even for legacy callers that cannot pass
    # the PLAN (archive_run/older closeout paths).  The PLAN-aware schema join
    # separately proves that the authority list is the exact frozen source
    # identity; this pass still verifies every listed blob and digest.
    strict = _strict_ui_evidence_required(run)
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
                    "RUN-v10/v11 evidence requires a recorded accepted Git commit/ref in head_sha",
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
        if strict:
            artifact_digest = item.get("artifact_sha256")
            if not isinstance(artifact_digest, str) or not SHA256_RE.fullmatch(
                artifact_digest
            ):
                _add(errors, path, "artifact_sha256 must be a lowercase SHA-256")
        if image_error := _ui_image_decode_error(artifact_bytes, item["artifact_path"]):
            _add(errors, path, image_error)
        elif _nonempty_string(item.get("artifact_sha256")):
            actual = hashlib.sha256(artifact_bytes).hexdigest()
            if actual != item["artifact_sha256"]:
                _add(errors, path, "sha256 does not match artifact_sha256")

        # The Final Visual Parity Loop's reference render gets the same
        # immutable-blob treatment as the actual screenshot: read it from the
        # recorded accepted commit and decode those bytes, never the worktree.
        comparison = item.get("target_comparison")
        if (
            schema_version == 11
            and isinstance(comparison, dict)
            and _valid_ui_artifact_path(comparison.get("baseline_artifact"))
            and (strict or comparison.get("baseline") == "html_target")
        ):
            baseline_path = (
                f"run.ui_evidence[{index}].target_comparison.baseline_artifact"
            )
            baseline_bytes, reason = _read_git_artifact_blob(
                root, head_sha, comparison["baseline_artifact"]
            )
            if baseline_bytes is None:
                _add(
                    errors,
                    baseline_path,
                    f"does not exist in accepted Git commit/ref {head_sha!r}: "
                    f"{reason or 'git show could not read the blob'}",
                )
            elif not baseline_bytes:
                _add(errors, baseline_path, "must not be empty")
            elif baseline_error := _ui_image_decode_error(
                baseline_bytes, comparison["baseline_artifact"]
            ):
                _add(errors, baseline_path, baseline_error)
            elif strict:
                baseline_digest = comparison.get("baseline_artifact_sha256")
                actual_baseline_digest = hashlib.sha256(baseline_bytes).hexdigest()
                if baseline_digest != actual_baseline_digest:
                    _add(
                        errors,
                        baseline_path,
                        "sha256 does not match baseline_artifact_sha256",
                    )

        if strict and isinstance(comparison, dict):
            authority = comparison.get("authority_sources")
            if isinstance(authority, list):
                for authority_index, source in enumerate(authority):
                    source_path = (
                        f"run.ui_evidence[{index}].target_comparison."
                        f"authority_sources[{authority_index}]"
                    )
                    if not isinstance(source, dict):
                        continue
                    authority_location = source.get("path")
                    authority_digest = source.get("sha256")
                    if not _valid_source_path(authority_location):
                        continue
                    authority_bytes, reason = _read_git_artifact_blob(
                        root, head_sha, authority_location
                    )
                    if authority_bytes is None:
                        _add(
                            errors,
                            source_path,
                            f"does not exist in accepted Git commit/ref {head_sha!r}: "
                            f"{reason or 'git show could not read the blob'}",
                        )
                        continue
                    actual_authority_digest = hashlib.sha256(authority_bytes).hexdigest()
                    if authority_digest != actual_authority_digest:
                        _add(
                            errors,
                            source_path,
                            "sha256 does not match authority source bytes",
                        )
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

    try:
        reject_object_substitution(Path(repo_root))
    except (GitMetadataError, OSError) as exc:
        detail = str(exc)
        if "not a git repository" in detail.casefold():
            detail = (
                f"--repo-root {repo_root} is not a Git checkout "
                "(pass the correct --repo-root)"
            )
        _add(
            errors,
            path,
            f"could not be verified against live Git: {detail}",
        )
        return sorted(set(errors))

    def _run_git(*args: str) -> subprocess.CompletedProcess[str] | None:
        # Every git call on this path must degrade into an error entry, never a
        # traceback: this validator's whole job is to report problems as data.
        try:
            return run_git(
                Path(repo_root),
                *args,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            _add(errors, path, f"could not be verified against live Git: {exc}")
            return None

    branch = integration.get("branch")
    if not isinstance(branch, str) or not _nonempty_string(branch):
        _add(errors, path, "could not be verified against live Git: run.integration.branch is not set")
        return sorted(set(errors))
    result = _run_git("rev-parse", branch)
    if result is None:
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
        ancestry = _run_git("merge-base", "--is-ancestor", recorded, actual)
        changed = _run_git("diff", "--name-only", f"{recorded}..{actual}")
        if ancestry is None or changed is None:
            return sorted(set(errors))
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

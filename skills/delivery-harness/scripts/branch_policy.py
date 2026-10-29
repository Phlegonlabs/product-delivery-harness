#!/usr/bin/env python3
"""Validate version-pinned PLAN-v6 release policies."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from harness_git import run_git
from harness_core import ManifestError, is_full_sha
from harness_schema import parse_harness_version, run_required_harness_version


MAIN_PREVIEW_PROTOCOL = "main-preview/1"
MAIN_PREVIEW_VERSION = (0, 63, 0)
RELEASE_MARKER_LINE_RE = re.compile(r"^Release source policy:[ \t]*(.*?)[ \t]*$", re.MULTILINE)


def branch_policy_required(run: dict[str, Any] | None) -> bool:
    """Only a valid historical pin can select historical policy rules."""

    if not isinstance(run, dict):
        return False
    pin = parse_harness_version(run_required_harness_version(run))
    if pin is None:
        return run.get("schema_version") == 11
    return pin >= MAIN_PREVIEW_VERSION


def validate_branch_policy_shape(
    plan: dict[str, Any], *, run: dict[str, Any] | None = None
) -> list[str]:
    """Return exact-shape findings without consulting Git."""

    if run is not None and not branch_policy_required(run):
        return []
    errors: list[str] = []
    policy = plan.get("branch_policy")
    path = "plan.branch_policy"
    if not isinstance(policy, dict):
        return [f"{path}: Harness 0.63+ requires a branch policy object"]
    if set(policy) != {"protocol", "kind", "base_ref", "base_sha"}:
        return [
            f"{path}: must contain exactly protocol, kind, base_ref, and base_sha"
        ]
    protocol = policy["protocol"]
    if protocol != MAIN_PREVIEW_PROTOCOL:
        errors.append(f"{path}.protocol: Harness 0.63+ requires {MAIN_PREVIEW_PROTOCOL!r}")
    if run is not None and parse_harness_version(run_required_harness_version(run)) is None:
        errors.append(f"{path}: requires a valid Harness version pin")
    kind = policy["kind"]
    base_ref = policy["base_ref"]
    if not isinstance(kind, str) or kind not in {"ordinary", "hotfix"}:
        errors.append(f"{path}.kind: must be ordinary or hotfix")
        return errors
    if not isinstance(base_ref, str) or re.fullmatch(
        r"refs/remotes/([a-z0-9][a-z0-9._-]*)/main", base_ref
    ) is None:
        errors.append(f"{path}.base_ref: must name refs/remotes/<remote>/main")
    if not is_full_sha(policy["base_sha"]):
        errors.append(f"{path}.base_sha: must be a full lowercase Git SHA")
    return errors


def initial_or_candidate_head(run: dict[str, Any] | None) -> str | None:
    """Prefer the current candidate; fall back to the observed initial head."""

    if not isinstance(run, dict):
        return None
    integration = run.get("integration")
    if not isinstance(integration, dict):
        return None
    for key in ("integration_head_sha", "batch_base_sha"):
        value = integration.get(key)
        if is_full_sha(value):
            return value
    return None


def archive_ancestry_base(
    plan: dict[str, Any] | None, run: dict[str, Any], expected_main: str
) -> str:
    """Use the frozen delivery base, retaining historical main-based pins."""

    if not branch_policy_required(run):
        return expected_main
    issues = validate_branch_policy_shape(plan if isinstance(plan, dict) else {}, run=run)
    if issues:
        raise ManifestError("invalid archive branch policy: " + "; ".join(issues))
    return plan["branch_policy"]["base_sha"]


def validate_branch_policy_ancestry(
    plan: dict[str, Any],
    repo_root: str | Path,
    *,
    run: dict[str, Any] | None = None,
) -> list[str]:
    """Prove the frozen base is local and ancestral to the first candidate."""

    shape_errors = validate_branch_policy_shape(plan, run=run)
    if shape_errors:
        return shape_errors
    base_sha = plan["branch_policy"]["base_sha"]
    head_sha = initial_or_candidate_head(run)
    if head_sha is None:
        return []
    result = run_git(
        Path(repo_root),
        "merge-base",
        "--is-ancestor",
        base_sha,
        head_sha,
        timeout=30,
    )
    if result.returncode == 0:
        return []
    detail = result.stderr.strip() or "git merge-base --is-ancestor failed"
    return [
        "plan.branch_policy.base_sha: is not an ancestor of the initial or "
        f"candidate head {head_sha} ({detail})"
    ]


def validate_branch_policy_join(
    plan: dict[str, Any],
    architecture_text: str,
    repo_root: str | Path,
    *,
    run: dict[str, Any] | None = None,
    active_text: Callable[[str], str] | None = None,
) -> list[str]:
    """Validate marker compatibility and the exact policy for any valid pin."""
    if run is not None and not branch_policy_required(run):
        # Historical policy fields remain opaque. Finish those runs on their pinned bundle.
        return []
    active = architecture_text if active_text is None else active_text(architecture_text)
    errors: list[str] = []
    markers = RELEASE_MARKER_LINE_RE.findall(active)
    supported = {MAIN_PREVIEW_PROTOCOL}
    if any(marker not in supported for marker in markers):
        errors.append(
            "architecture: the only supported Release source policy marker is main-preview/1"
        )
    if len(markers) > 1:
        errors.append(
            "architecture: Release Targets must contain at most one active "
            "Release source policy marker"
        )
    has_marker = len(markers) == 1 and markers[0] in supported
    requires_policy = branch_policy_required(run) or (
        run is None and (has_marker or "branch_policy" in plan)
    )
    pin = parse_harness_version(run_required_harness_version(run)) if run is not None else None
    if run is not None and pin is None and branch_policy_required(run):
        errors.append("branch policy: requires a valid Harness version pin")
    if requires_policy and (not has_marker or markers[0] != MAIN_PREVIEW_PROTOCOL):
        errors.append(
            "architecture: Harness 0.63+ current joins require an active "
            f"{'Release source policy: ' + MAIN_PREVIEW_PROTOCOL!r} marker"
        )
    if requires_policy:
        errors.extend(validate_branch_policy_shape(plan, run=run))
        errors.extend(
            validate_branch_policy_ancestry(plan, repo_root, run=run)
        )
    return errors

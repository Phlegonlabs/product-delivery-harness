#!/usr/bin/env python3
"""Shared, stdlib-only manifest schema constants, enums, and regular expressions."""

from __future__ import annotations

import re
from typing import Any


PLAN_HEADING = "## Harness Plan Manifest"
RUN_HEADING = "## Harness Run State"
WORKER_HEADING = "## Worker Result Manifest"

AUTHORIZATION_KEYS = (
    "invoke_external_runtime",
    "spawn_subagents",
    "create_user_owned_tasks",
    "create_local_worktrees",
    "create_app_managed_worktrees",
    "create_local_branches",
    "create_local_commits",
    "integrate_locally",
    "push",
    "archive_worker_tasks",
    "remove_worktrees",
    "delete_branches",
)

MISSION_PHASES = {
    "queued",
    "ready",
    "leased",
    "worker_running",
    "worker_passed",
    "integrating",
    "integrated",
    "blocked",
    "worker_failed",
    "integration_failed",
    "superseded",
}
TASK_PHASES = {
    "queued",
    "ready",
    "running",
    "worker_passed",
    "mission_recorded",
    "blocked",
    "worker_failed",
    "superseded",
}
WORKER_PHASES = {
    "leased",
    "worker_running",
    "worker_passed",
    "blocked",
    "worker_failed",
    "superseded",
}
GATE_VALUES = {"planned", "PASS", "FAIL", "BLOCKED", "UNVALIDATED"}
SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]{0,63}$")
TASK_ID_RE = re.compile(r"^([A-Z][A-Z0-9_-]{0,63})/([A-Z][A-Z0-9_-]{0,63})$")
TARGET_RE = re.compile(r"^(?:worker|task|worktree|branch|runtime):.+$")

# A target prefix is part of an action's type. PLAN graph and RUN ledger
# validation both consume this table so they cannot disagree about which exact
# target a lifecycle action accepts.
ACTION_TARGET_RULES = {
    "invoke_external_runtime": ("runtime",),
    "spawn_subagents": ("worker",),
    "create_user_owned_tasks": ("task",),
    "create_local_worktrees": ("worktree",),
    "create_app_managed_worktrees": ("worktree",),
    "create_local_branches": ("branch",),
    "create_local_commits": ("branch",),
    "integrate_locally": ("branch",),
    "push": ("branch",),
    "archive_worker_tasks": ("task",),
    "remove_worktrees": ("worktree",),
    "delete_branches": ("branch",),
}


def action_target_kind_allowed(action: str, target: str) -> bool:
    """Return whether an exact target has the kind allowed for this action."""
    if target == "*":
        return True
    if TARGET_RE.fullmatch(target) is None:
        return False
    return target.split(":", 1)[0] in ACTION_TARGET_RULES.get(action, ())


def action_target_kind_description(action: str) -> str:
    """Return the legal target shapes for validation messages."""
    return " or ".join(
        f"{name}:<identity>" for name in ACTION_TARGET_RULES.get(action, ())
    )


EXPIRY_BOUNDARIES = {"wave_closed", "run_complete", "explicit_revocation"}
# Only these lifecycle states may produce production dispatch directives. A
# blocked/complete run can retain historical authorization, but must not be
# resumed by a selector until its parent explicitly transitions it back.
RUN_DISPATCH_STATUSES = {"ready", "running"}
NESTED_SUBAGENT_ROLES = {"explorer", "researcher", "reviewer", "tester"}
PERMISSION_SELECTED_MODES = {
    "ask_for_approval",
    "approve_for_me",
    "full_access",
    "named_profile",
    "unknown",
}
PERMISSION_APPROVAL_POLICIES = {
    "untrusted",
    "on-request",
    "never",
    "granular",
    "unknown",
}
PERMISSION_FILESYSTEM_SCOPES = {
    "read_only",
    "workspace",
    "custom",
    "unrestricted",
    "unknown",
}
PERMISSION_NETWORK_SCOPES = {"disabled", "filtered", "open", "unknown"}
PERMISSION_LOCAL_BINDINGS = {"allowed", "blocked", "unknown"}
PERMISSION_INHERITANCE = {"inherited", "not_inherited", "unknown"}
PERMISSION_STATUSES = {"ready", "may_prompt", "blocked", "unknown"}
SUPPORTED_RUN_SCHEMA_VERSIONS = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11}
CURRENT_PLAN_SCHEMA_VERSION = 6
CURRENT_RUN_SCHEMA_VERSION = 11
CURRENT_SCHEMA_PAIR = (CURRENT_PLAN_SCHEMA_VERSION, CURRENT_RUN_SCHEMA_VERSION)
ARCHIVE_FIRST_HARNESS_VERSION = (0, 38, 0)


def parse_harness_version(value: Any) -> tuple[int, int, int] | None:
    """Parse the same three-part release core used by ``version_at_least``."""

    if not isinstance(value, str):
        return None
    core = value.split("+", 1)[0].split("-", 1)[0]
    parts = core.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def required_harness_version(run: dict[str, Any]) -> tuple[int, int, int] | None:
    """Read the RUN's immutable required Harness version pin."""

    capabilities = run.get("runtime_capabilities")
    adapter = capabilities.get("runtime_adapter") if isinstance(capabilities, dict) else None
    gate = adapter.get("version_gate") if isinstance(adapter, dict) else None
    value = gate.get("required_harness_version") if isinstance(gate, dict) else None
    return parse_harness_version(value)


def archive_first_required(run: dict[str, Any]) -> bool:
    """Return true when the RUN is pinned to archive-first push semantics."""

    version = required_harness_version(run)
    return version is not None and version >= ARCHIVE_FIRST_HARNESS_VERSION


def schema_pair_of(plan: object, run: object) -> tuple[object, object]:
    """Read the (plan, run) schema-version pair, tolerating non-dict input."""

    if isinstance(plan, dict) and isinstance(run, dict):
        return (plan.get("schema_version"), run.get("schema_version"))
    return (None, None)


def is_current_pair(plan: object, run: object) -> bool:
    """True only when the pair is the current authoring pair (now PLAN v6 / RUN v11)."""

    return schema_pair_of(plan, run) == CURRENT_SCHEMA_PAIR
RUN_CONTROL_STATES = {"running", "paused", "cancelled"}
UI_EVIDENCE_IMAGE_SUFFIXES = {".jpeg", ".jpg", ".png", ".webp"}
# `push` is the only action bound to an exact head SHA: it publishes one verified
# commit. Every other action either mutates local state or cleans it up.
HEAD_BOUND_AUTHORIZATION_ACTIONS = {"push"}
# Cleanup lifecycle nodes must name the exact task, worktree, or branch they
# act on. A run-wide "*" grant may still cover them, but the node attempt and
# its result must record which object was archived, removed, or deleted.
EXACT_TARGET_LIFECYCLE_ACTIONS = {
    "archive_worker_tasks",
    "remove_worktrees",
    "delete_branches",
}


# RUN coordination paths name run bookkeeping files only. Product source and
# frozen PLAN inputs never qualify, because a coordination-only commit after
# the recorded integration head must not hide product changes.
_COORDINATION_PATH_RES = (
    re.compile(r"docs/(?:tasks|DOCUMENTS)\.md"),
    re.compile(
        r"docs/goal/(?:[^/]+/)?(?:PLAN|RUN|DECISIONS|REFINEMENT_BACKLOG|tasks)\.md"
    ),
    re.compile(r"docs/epics/[^/]+\.md"),
)


def supported_coordination_path(path: object) -> bool:
    """Return whether ``path`` is an allowed run coordination file."""

    return isinstance(path, str) and any(
        pattern.fullmatch(path) is not None for pattern in _COORDINATION_PATH_RES
    )


def frozen_coordination_path(path: object, plan: object = None) -> bool:
    """Return whether ``path`` is a frozen product/design or PLAN source."""

    if not isinstance(path, str):
        return False
    if path.startswith(("docs/product/", "docs/design/")):
        return True
    sources = plan.get("sources", []) if isinstance(plan, dict) else []
    if not isinstance(sources, list):
        return False
    for source in sources:
        location = source.get("location") if isinstance(source, dict) else None
        if (
            isinstance(location, str)
            and location == path
            and "://" not in location
            and not location.startswith("/")
            and "\\" not in location
        ):
            return True
    return False
# Provider IDs record the current host identity, never a capability or model catalog.
PROVIDER_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def is_valid_provider_id(value: object) -> bool:
    return isinstance(value, str) and PROVIDER_ID_RE.match(value) is not None
RUNTIME_REASONING_EFFORTS = {
    "none",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
    "ultra",
}
MODEL_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
RUNTIME_DRIVERS = {
    "app_threads",
    "subagents",
    "sequential_parent",
}
RUNTIME_DETECTION_SOURCES = {"observed", "explicit", "fallback"}
RUNTIME_VERSION_STATUSES = {
    "unobserved",
    "adopted",
    "current",
    "compatible_old",
    "upgrade_required",
    "restart_required",
}
CAPABILITY_PROBE_STATUSES = {"available", "unavailable", "unobserved"}
CAPABILITY_PROBE_KEYS = (
    "app_project_list",
    "app_thread_create",
    "app_thread_read",
    "app_thread_message",
    "app_thread_wait",
    "app_managed_worktree",
    "direct_subagent_spawn",
    "direct_agent_result",
)
DRIVER_CAPABILITY_REQUIREMENTS = {
    "app_threads": (
        "app_project_list",
        "app_thread_create",
        "app_thread_read",
        "app_thread_message",
        "app_thread_wait",
        "app_managed_worktree",
    ),
    "subagents": (
        "direct_subagent_spawn",
        "direct_agent_result",
    ),
}
GRAPH_NODE_KINDS = {"mission", "verifier", "approval", "external_wait", "lifecycle"}
GRAPH_EXECUTORS = {
    "runtime_worker",
    "harness_parent",
    "local_command",
    "external_system",
    "human",
}
GRAPH_OUTCOMES = {
    "pass",
    "fix_required",
    "retryable_failure",
    "blocked",
    "contract_gap",
}
GRAPH_NODE_PHASES = {
    "dormant",
    "ready",
    "running",
    "succeeded",
    "failed",
    "blocked",
    "skipped",
    "superseded",
}
GRAPH_EDGE_PHASES = {"dormant", "eligible", "traversed", "exhausted", "skipped"}
RUNTIME_REVIEW_TYPES = {"frontend_code", "backend_code", "visual", "security"}
# A review node with `lenses` sets `type` to its widest lens in this order, so
# every security and visual rule keyed on `type` still applies to it.
REVIEW_LENS_ORDER = ("security", "visual", "frontend_code", "backend_code")
# An absent PLAN `review_policy` means per_mission, the rule of every older PLAN.
REVIEW_POLICIES = {"per_mission", "final_candidate"}
REVIEWER_TOOL_KEYS = {"chrome_devtools"}
REVIEWER_TOOL_STATUSES = {"available", "unavailable", "unobserved"}
REVIEWER_TOOL_PROBE_SCOPES = {"reviewer_session", "parent_session", "unobserved"}


def review_lenses(review: object) -> set[str]:
    """Return a review's lenses; a review without `lenses` has one, its type."""

    if not isinstance(review, dict):
        return set()
    lenses = review.get("lenses")
    if isinstance(lenses, list):
        return {lens for lens in lenses if isinstance(lens, str)}
    review_type = review.get("type")
    return {review_type} if isinstance(review_type, str) else set()


def review_policy(plan: object) -> str:
    value = plan.get("review_policy") if isinstance(plan, dict) else None
    return value if isinstance(value, str) else "per_mission"


def security_result_decision(review: object, outcome: object, result: object) -> object:
    """Return the decision a review's security result must carry.

    On a combined node another lens may fail while the security lens passes.
    """

    if (
        len(review_lenses(review)) > 1
        and outcome != "pass"
        and isinstance(result, dict)
        and result.get("decision") == "pass"
    ):
        return "pass"
    return outcome


def run_required_harness_version(run: object) -> str | None:
    """Read the RUN version gate's required harness version defensively."""

    runtime = run.get("runtime_capabilities") if isinstance(run, dict) else None
    adapter = runtime.get("runtime_adapter") if isinstance(runtime, dict) else None
    gate = adapter.get("version_gate") if isinstance(adapter, dict) else None
    version = gate.get("required_harness_version") if isinstance(gate, dict) else None
    return version if isinstance(version, str) else None


def version_at_least(value: object, minimum: tuple[int, int, int]) -> bool:
    """Compare a release string to `minimum` under one strict rule.

    One pre-release (`-rc.1`) or build (`+build.5`) suffix is stripped, then
    the core must be exactly three numeric dot-parts. Anything else -- short
    forms like `0.35`, four-part numbers, junk, None -- fails the gate so a
    malformed pin never widens what a RUN file must carry.
    """

    if not isinstance(value, str):
        return False
    core = value.split("+", 1)[0].split("-", 1)[0]
    parts = core.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        return False
    return tuple(int(part) for part in parts) >= minimum

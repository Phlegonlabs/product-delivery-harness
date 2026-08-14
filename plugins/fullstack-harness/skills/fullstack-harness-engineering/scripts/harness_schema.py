#!/usr/bin/env python3
"""Shared, stdlib-only manifest schema constants, enums, and regular expressions."""

from __future__ import annotations

import re


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
SUPPORTED_RUN_SCHEMA_VERSIONS = {2, 3, 4, 5, 6, 7, 8, 9, 10}
UI_EVIDENCE_IMAGE_SUFFIXES = {".jpeg", ".jpg", ".png", ".webp"}
# `push` is the only action bound to an exact head SHA: it publishes one verified
# commit. Every other action either mutates local state or cleans it up.
HEAD_BOUND_AUTHORIZATION_ACTIONS = {"push"}
RUNTIME_PROVIDERS = {"codex", "claude_code", "pi", "generic"}
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
    "dynamic_workflow",
    "subagents",
    "sequential_parent",
}
RUNTIME_DETECTION_SOURCES = {"observed", "explicit", "fallback"}
CAPABILITY_PROBE_STATUSES = {"available", "unavailable", "unobserved"}
CODEX_CAPABILITY_PROBE_KEYS = (
    "app_project_list",
    "app_thread_create",
    "app_thread_read",
    "app_thread_message",
    "app_thread_wait",
    "app_managed_worktree",
    "direct_subagent_spawn",
    "direct_agent_result",
)
CODEX_DRIVER_CAPABILITY_REQUIREMENTS = {
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
WORKFLOW_TOOL_PROFILES = {
    "mission_write",
    "code_review_readonly",
    "visual_review_readonly",
}
WORKFLOW_RUN_STATUSES = {"running", "completed", "failed", "stopped"}
WORKFLOW_RUN_DRIVERS_BY_PROVIDER = {
    "claude_code": {"dynamic_workflow"},
}
RUNTIME_DRIVER_PRIORITY = {
    "codex": ("app_threads", "subagents", "sequential_parent"),
    "claude_code": ("dynamic_workflow", "subagents", "sequential_parent"),
    "pi": ("subagents", "sequential_parent"),
    "generic": ("subagents", "sequential_parent"),
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
RUNTIME_REVIEW_TYPES = {"frontend_code", "backend_code", "visual"}

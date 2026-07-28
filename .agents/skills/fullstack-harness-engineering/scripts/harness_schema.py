#!/usr/bin/env python3
"""Shared, stdlib-only manifest schema constants, enums, and regular expressions."""

from __future__ import annotations

import re


PLAN_HEADING = "## Harness Plan Manifest"
RUN_HEADING = "## Harness Run State"
WORKER_HEADING = "## Worker Result Manifest"

AUTHORIZATION_KEYS_V2 = (
    "spawn_subagents",
    "create_user_owned_tasks",
    "create_local_worktrees",
    "create_app_managed_worktrees",
    "create_local_branches",
    "create_local_commits",
    "integrate_locally",
    "push",
    "create_pr",
    "deploy",
    "archive_worker_tasks",
    "remove_worktrees",
    "delete_branches",
)

AUTHORIZATION_KEYS = AUTHORIZATION_KEYS_V2 + (
    "configure_repository",
    "manage_pr_review",
    "merge_pr",
)

AUTHORIZATION_KEYS_V8 = AUTHORIZATION_KEYS + ("invoke_external_runtime",)

AUTHORIZATION_KEYS_V10 = AUTHORIZATION_KEYS_V8 + (
    "trigger_remote_ci",
    "provision_cloud_resources",
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
TARGET_RE = re.compile(
    r"^(?:worker|task|worktree|branch|remote|pr|repository|environment|release|runtime|workflow|cloud-resource):.+$"
)
CLOUD_RESOURCE_TARGET_RE = re.compile(
    r"^cloud-resource:[^:\s]+:[^:\s]+:[^:\s]+:[^:\s]+$"
)
FUTURE_PR_TARGET_RE = re.compile(
    r"^future-pr:(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+):"
    r"base=(?P<base>[^:\s]+):head=(?P<head>[^:\s]+)$"
)
GITHUB_PR_URL_RE = re.compile(
    r"^https://github\.com/(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/"
    r"pull/[1-9][0-9]*/?$"
)
EXPIRY_BOUNDARIES = {"wave_closed", "run_complete", "explicit_revocation"}
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
CLEANUP_STATUSES = {"not_started", "ready", "complete", "deferred", "not_applicable"}
CLEANUP_WORKTREE_STATUSES = {
    "not_applicable",
    "pending",
    "removed",
    "platform_managed",
    "deferred",
}
CLEANUP_BRANCH_STATUSES = {
    "pending",
    "deleted",
    "preserved",
    "deferred",
    "not_applicable",
}
SUPPORTED_RUN_SCHEMA_VERSIONS = {2, 3, 4, 5, 6, 7, 8, 9, 10}
UI_EVIDENCE_IMAGE_SUFFIXES = {".jpeg", ".jpg", ".png", ".webp"}
# Deployment target for plan.release / run.deployments. Unrelated to RUNTIME_PROVIDERS below,
# which selects the agent runtime that executes PLAN nodes, not where the product deploys.
DEPLOYMENT_PROVIDERS = {"cloudflare", "vercel", "aws", "self_hosted", "other"}
RELEASE_STAGES = {"development", "production"}
RELEASE_SOURCES = {"pr_head", "integration_head", "production_head", "merged_main"}
RELEASE_DATA_MODES = {"isolated_non_production", "production"}
RELEASE_TRIGGERS = {"manual", "merge"}
MIGRATION_CLASSIFICATIONS = {None, "not_applicable", "additive", "destructive"}
HEAD_BOUND_AUTHORIZATION_ACTIONS = {
    "push",
    "create_pr",
    "manage_pr_review",
    "merge_pr",
    "deploy",
}
# Actions one execution-intent instruction covers, but only for a bounded set of
# targets: the resolved integration branch, a PR whose base is that branch, and
# the development release target. Any other target on these actions is a
# separate authorization moment and records its own source in `target_sources`.
EXECUTION_INTENT_SCOPED_ACTIONS = {
    "push",
    "merge_pr",
    "deploy",
}
RUNTIME_PROVIDERS = {"codex", "claude_code", "generic"}
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

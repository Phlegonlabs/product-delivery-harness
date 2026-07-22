#!/usr/bin/env python3
"""Shared, stdlib-only manifest validation and conflict helpers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


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
    r"^(?:worker|task|worktree|branch|remote|pr|repository|environment|runtime):.+$"
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
SUPPORTED_RUN_SCHEMA_VERSIONS = {2, 3, 4, 5, 6, 7, 8, 9}
UI_EVIDENCE_IMAGE_SUFFIXES = {".jpeg", ".jpg", ".png", ".webp"}
# Deployment target for plan.release / run.deployments. Unrelated to RUNTIME_PROVIDERS below,
# which selects the agent runtime that executes PLAN nodes, not where the product deploys.
DEPLOYMENT_PROVIDERS = {"cloudflare", "vercel", "aws", "self_hosted", "other"}
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


class ManifestError(ValueError):
    """Raised when a canonical manifest cannot be extracted or decoded."""


def route_runtime_driver(runtime: dict[str, Any]) -> str:
    """Select one deterministic execution driver from observed capabilities."""

    adapter = runtime.get("runtime_adapter")
    if not isinstance(adapter, dict):
        return {
            "parent": "sequential_parent",
            "subagent": "subagents",
            "app_task": "app_threads",
        }.get(runtime.get("worker_runtime"), "sequential_parent")

    available = adapter.get("available_drivers")
    if not isinstance(available, list):
        return "sequential_parent"
    provider = adapter.get("provider")
    priority = RUNTIME_DRIVER_PRIORITY.get(provider, ()) if isinstance(provider, str) else ()
    for driver in priority:
        if driver in available:
            return driver
    return "sequential_parent"


def resolve_runtime_options(policy: dict[str, Any], provider: str) -> dict[str, Any]:
    """Resolve one provider's PLAN options without inventing external Codex overrides."""

    raw_options = policy.get("provider_options")
    provider_options = raw_options if isinstance(raw_options, dict) else {}
    configured = provider_options.get(provider)
    default_model = "sonnet" if provider == "claude_code" else None
    if isinstance(configured, dict):
        return {
            "model": configured.get("model") or default_model,
            "reasoning_effort": configured.get("reasoning_effort"),
            "option_source": "plan_provider_options",
        }
    return {
        "model": default_model,
        "reasoning_effort": None,
        "option_source": "provider_default",
    }


def extract_json_manifest(path: str | Path, heading: str, wrapper: str) -> dict[str, Any]:
    """Load the unique exact-heading JSON fence and return its wrapped object."""

    source = Path(path)
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    positions = [index for index, line in enumerate(lines) if line.strip() == heading]
    if len(positions) != 1:
        raise ManifestError(
            f"{source}: expected exactly one {heading!r}, found {len(positions)}"
        )
    index = positions[0] + 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or lines[index].strip() != "```json":
        raise ManifestError(f"{source}: first content after {heading!r} must be ```json")
    start = index + 1
    index = start
    while index < len(lines) and lines[index].strip() != "```":
        index += 1
    if index >= len(lines):
        raise ManifestError(f"{source}: unterminated JSON fence after {heading!r}")
    try:
        decoded = json.loads("\n".join(lines[start:index]))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"{source}: invalid JSON: {exc}") from exc
    if not isinstance(decoded, dict) or set(decoded) != {wrapper}:
        raise ManifestError(f"{source}: JSON root must contain only {wrapper!r}")
    value = decoded[wrapper]
    if not isinstance(value, dict):
        raise ManifestError(f"{source}: {wrapper!r} must be an object")
    return value


def load_plan(path: str | Path) -> dict[str, Any]:
    return extract_json_manifest(path, PLAN_HEADING, "harness_plan")


def load_run(path: str | Path) -> dict[str, Any]:
    return extract_json_manifest(path, RUN_HEADING, "harness_run")


def load_worker_result(path: str | Path) -> dict[str, Any]:
    return extract_json_manifest(path, WORKER_HEADING, "worker_result")


def _canonicalize(value: Any, parent_key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {key: _canonicalize(value[key], key) for key in sorted(value)}
    if isinstance(value, list):
        normalized = [_canonicalize(item, parent_key) for item in value]
        if parent_key == "argv":
            return normalized
        if all(isinstance(item, dict) and isinstance(item.get("id"), str) for item in normalized):
            return sorted(normalized, key=lambda item: item["id"])
        if all(isinstance(item, dict) and isinstance(item.get("key"), str) for item in normalized):
            return sorted(normalized, key=lambda item: (item["key"], item.get("access", "")))
        if all(item is None or isinstance(item, (str, int, float, bool)) for item in normalized):
            return sorted(
                normalized,
                key=lambda item: json.dumps(item, ensure_ascii=False, separators=(",", ":")),
            )
        return normalized
    return value


def plan_digest(plan: dict[str, Any]) -> str:
    normalized = _canonicalize(plan)
    encoded = json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def is_full_sha(value: Any) -> bool:
    return isinstance(value, str) and SHA_RE.fullmatch(value) is not None


def is_safe_model_token(value: Any) -> bool:
    return isinstance(value, str) and MODEL_TOKEN_RE.fullmatch(value) is not None


def validate_scope_claim(claim: Any) -> str | None:
    if not isinstance(claim, str) or not claim:
        return "must be a non-empty string"
    if claim.startswith("/") or "\\" in claim:
        return "must be a repository-relative POSIX path"
    if claim != claim.strip() or "//" in claim:
        return "must use canonical path spelling"
    if claim.startswith("!") or any(char in claim for char in "?[]{}"):
        return "contains unsupported glob syntax"
    wildcard_count = claim.count("*")
    if wildcard_count and not (claim.endswith("/**") and wildcard_count == 2):
        return "only one terminal /** wildcard is supported"
    base = claim[:-3] if claim.endswith("/**") else claim
    if not base or base.endswith("/"):
        return "has an empty or trailing path segment"
    segments = base.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        return "contains an empty, . or .. path segment"
    return None


def _claim_parts(claim: str, *, casefold: bool = False) -> tuple[tuple[str, ...], bool]:
    subtree = claim.endswith("/**")
    base = claim[:-3] if subtree else claim
    if casefold:
        base = base.casefold()
    return tuple(base.split("/")), subtree


def _parts_prefix(prefix: tuple[str, ...], value: tuple[str, ...]) -> bool:
    return len(prefix) <= len(value) and value[: len(prefix)] == prefix


def scope_overlap(left: str, right: str, *, casefold: bool = False) -> bool:
    left_parts, left_tree = _claim_parts(left, casefold=casefold)
    right_parts, right_tree = _claim_parts(right, casefold=casefold)
    if not left_tree and not right_tree:
        return left_parts == right_parts
    if left_tree and right_tree:
        return _parts_prefix(left_parts, right_parts) or _parts_prefix(right_parts, left_parts)
    if left_tree:
        return _parts_prefix(left_parts, right_parts)
    return _parts_prefix(right_parts, left_parts)


def scope_contains(parent: str, child: str) -> bool:
    parent_parts, parent_tree = _claim_parts(parent)
    child_parts, child_tree = _claim_parts(child)
    if not parent_tree:
        return not child_tree and parent_parts == child_parts
    if child_tree:
        return _parts_prefix(parent_parts, child_parts)
    return _parts_prefix(parent_parts, child_parts)


def path_in_scopes(path: str, scopes: Iterable[str]) -> bool:
    return any(scope_contains(scope, path) for scope in scopes)


def parent_owned_path(path: str) -> bool:
    base = path[:-3] if path.endswith("/**") else path
    name = base.rsplit("/", 1)[-1].casefold()
    return name in {"plan.md", "run.md"}


def mission_conflicts(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    reasons: set[str] = set()
    for left_scope in left.get("write_scope", []):
        for right_scope in right.get("write_scope", []):
            if scope_overlap(left_scope, right_scope):
                reasons.add("scope_overlap")
            elif scope_overlap(left_scope, right_scope, casefold=True):
                reasons.add("case_scope_collision")
    if set(left.get("serialized_resources", [])) & set(right.get("serialized_resources", [])):
        reasons.add("serialized_resource_conflict")
    left_resources = {item["key"]: item["access"] for item in left.get("runtime_resources", [])}
    right_resources = {item["key"]: item["access"] for item in right.get("runtime_resources", [])}
    for key in set(left_resources) & set(right_resources):
        if "exclusive" in {left_resources[key], right_resources[key]}:
            reasons.add("runtime_resource_conflict")
    return sorted(reasons)


def mission_dependencies(plan: dict[str, Any]) -> dict[str, list[str]]:
    """Return the canonical mission dependency projection for every PLAN schema."""

    missions = {
        mission["id"]: mission
        for mission in plan.get("missions", [])
        if isinstance(mission, dict) and isinstance(mission.get("id"), str)
    }
    if plan.get("schema_version") != 4:
        return {
            mission_id: list(mission.get("depends_on", []))
            for mission_id, mission in missions.items()
        }

    graph = plan.get("graph", {})
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    node_to_mission = {
        node.get("id"): node.get("ref")
        for node in nodes
        if isinstance(node, dict)
        and isinstance(node.get("id"), str)
        and node.get("kind") == "mission"
        and isinstance(node.get("ref"), str)
        and node.get("ref") in missions
    }
    dependencies = {mission_id: [] for mission_id in missions}
    edges = graph.get("edges", []) if isinstance(graph, dict) else []
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("kind") != "dependency":
            continue
        source_id = edge.get("from")
        target_id = edge.get("to")
        source = node_to_mission.get(source_id) if isinstance(source_id, str) else None
        target = node_to_mission.get(target_id) if isinstance(target_id, str) else None
        if source is not None and target is not None:
            dependencies[target].append(source)
    return {
        mission_id: sorted(set(values))
        for mission_id, values in dependencies.items()
    }


def topological_levels(plan: dict[str, Any]) -> dict[str, int]:
    missions = {mission["id"]: mission for mission in plan.get("missions", [])}
    dependency_map = mission_dependencies(plan)
    levels: dict[str, int] = {}

    def visit(mission_id: str, stack: set[str]) -> int:
        if mission_id in levels:
            return levels[mission_id]
        if mission_id in stack:
            raise ManifestError("mission dependency cycle")
        stack.add(mission_id)
        dependencies = dependency_map.get(mission_id, [])
        level = 0 if not dependencies else 1 + max(visit(dep, stack) for dep in dependencies)
        stack.remove(mission_id)
        levels[mission_id] = level
        return level

    for mission_id in sorted(missions):
        visit(mission_id, set())
    return levels


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _add(errors: list[str], path: str, message: str) -> None:
    errors.append(f"{path}: {message}")


def _keys(
    errors: list[str],
    path: str,
    value: Any,
    required: Iterable[str],
    optional: Iterable[str] = (),
) -> bool:
    if not isinstance(value, dict):
        _add(errors, path, "must be an object")
        return False
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        _add(errors, path, f"missing keys: {', '.join(missing)}")
    if unknown:
        _add(errors, path, f"unknown keys: {', '.join(unknown)}")
    return not missing and not unknown


def _strings(
    errors: list[str], path: str, value: Any, *, nonempty: bool = False
) -> list[str]:
    if not isinstance(value, list) or any(not _nonempty_string(item) for item in value):
        _add(errors, path, "must be a list of non-empty strings")
        return []
    if nonempty and not value:
        _add(errors, path, "must not be empty")
    if len(value) != len(set(value)):
        _add(errors, path, "must not contain duplicates")
    return value


def _validate_verifier(
    errors: list[str],
    path: str,
    value: Any,
    *,
    selection_scopes: Iterable[str] | None = None,
    cache_allowed: bool = True,
) -> None:
    required = {"id", "cwd", "argv", "pass_signal"}
    optional = {"selection", "cache"}
    if not _keys(errors, path, value, required, optional):
        return
    for key in ("id", "cwd", "pass_signal"):
        if not _nonempty_string(value[key]):
            _add(errors, f"{path}.{key}", "must be a non-empty string")
    _strings(errors, f"{path}.argv", value["argv"], nonempty=True)

    selection = value.get("selection")
    if selection is not None:
        selection_path = f"{path}.selection"
        if _keys(errors, selection_path, selection, {"mode", "scopes"}):
            mode = selection["mode"]
            if mode not in {"always", "changed_files"}:
                _add(errors, f"{selection_path}.mode", "must be always or changed_files")
            scopes = _validate_scope_list(
                errors,
                f"{selection_path}.scopes",
                selection["scopes"],
                nonempty=mode == "changed_files",
            )
            if mode == "always" and scopes:
                _add(errors, f"{selection_path}.scopes", "must be empty for always mode")
            if mode == "changed_files":
                if selection_scopes is None:
                    _add(errors, selection_path, "changed_files is allowed only for task and worker verifiers")
                else:
                    owner_scopes = list(selection_scopes)
                    for claim in scopes:
                        if not any(scope_contains(owner, claim) for owner in owner_scopes):
                            _add(
                                errors,
                                f"{selection_path}.scopes",
                                f"claim {claim!r} escapes the owning write scope",
                            )

    cache = value.get("cache")
    if cache is not None:
        cache_path = f"{path}.cache"
        if _keys(errors, cache_path, cache, {"mode", "environment_keys"}):
            mode = cache["mode"]
            if mode not in {"disabled", "session_exact"}:
                _add(errors, f"{cache_path}.mode", "must be disabled or session_exact")
            environment_keys = _strings(
                errors,
                f"{cache_path}.environment_keys",
                cache["environment_keys"],
            )
            if any(not key.strip() for key in environment_keys):
                _add(errors, f"{cache_path}.environment_keys", "contains an empty key")
            if mode == "disabled" and environment_keys:
                _add(errors, f"{cache_path}.environment_keys", "must be empty when cache is disabled")
            if mode == "session_exact" and not cache_allowed:
                _add(errors, cache_path, "session_exact is not allowed for this verifier")
            if mode == "session_exact" and value.get("pass_signal") != "exit 0":
                _add(errors, f"{path}.pass_signal", "session_exact requires the literal pass signal exit 0")


def _validate_release(errors: list[str], value: Any) -> None:
    path = "plan.release"
    if not _keys(errors, path, value, {"provider", "targets"}):
        return
    provider = value["provider"]
    if provider not in DEPLOYMENT_PROVIDERS:
        _add(errors, f"{path}.provider", f"must be one of {sorted(DEPLOYMENT_PROVIDERS)}")
        return
    if provider == "cloudflare":
        _validate_cloudflare_release_targets(errors, path, value["targets"])
    else:
        _validate_generic_release_targets(errors, path, value["targets"])


def _validate_generic_release_targets(errors: list[str], path: str, targets_value: Any) -> None:
    if not isinstance(targets_value, list) or not targets_value:
        _add(errors, f"{path}.targets", "must be a non-empty list")
        return

    target_keys = {
        "id",
        "prerequisites",
        "migration_command",
        "deploy_command",
        "smoke_verifiers",
    }
    seen_ids: set[str] = set()
    for index, target in enumerate(targets_value):
        target_path = f"{path}.targets[{index}]"
        if not _keys(errors, target_path, target, target_keys):
            continue
        target_id = target["id"]
        if not _nonempty_string(target_id):
            _add(errors, f"{target_path}.id", "must be a non-empty string")
        elif target_id in seen_ids:
            _add(errors, f"{target_path}.id", "must be unique")
        else:
            seen_ids.add(target_id)
        _strings(
            errors,
            f"{target_path}.prerequisites",
            target["prerequisites"],
            nonempty=True,
        )
        if target["migration_command"] is not None:
            _validate_verifier(
                errors,
                f"{target_path}.migration_command",
                target["migration_command"],
                cache_allowed=False,
            )
        _validate_verifier(
            errors,
            f"{target_path}.deploy_command",
            target["deploy_command"],
            cache_allowed=False,
        )
        smoke = target["smoke_verifiers"]
        if not isinstance(smoke, list) or not smoke:
            _add(errors, f"{target_path}.smoke_verifiers", "must be a non-empty list")
        else:
            for verifier_index, verifier in enumerate(smoke):
                _validate_verifier(
                    errors,
                    f"{target_path}.smoke_verifiers[{verifier_index}]",
                    verifier,
                    cache_allowed=False,
                )


def _validate_cloudflare_release_targets(errors: list[str], path: str, targets_value: Any) -> None:
    if not isinstance(targets_value, list) or len(targets_value) != 2:
        _add(errors, f"{path}.targets", "must contain development and production")
        return

    targets: dict[str, dict[str, Any]] = {}
    target_keys = {
        "id",
        "source",
        "worker_name",
        "wrangler_config_path",
        "wrangler_environment",
        "data_mode",
        "payment_mode",
        "auth_mode",
        "prerequisites",
        "migration_command",
        "deploy_command",
        "smoke_verifiers",
    }
    for index, target in enumerate(targets_value):
        target_path = f"{path}.targets[{index}]"
        if not _keys(errors, target_path, target, target_keys):
            continue
        target_id = target["id"]
        if not isinstance(target_id, str) or target_id not in (
            "development",
            "production",
        ):
            _add(errors, f"{target_path}.id", "must be development or production")
            continue
        if target_id in targets:
            _add(errors, f"{target_path}.id", "must be unique")
        targets[target_id] = target
        for key in ("worker_name", "wrangler_config_path", "wrangler_environment"):
            if not _nonempty_string(target[key]):
                _add(errors, f"{target_path}.{key}", "must be a non-empty string")
        config_path = target["wrangler_config_path"]
        config_problem = validate_scope_claim(config_path)
        if config_problem or (isinstance(config_path, str) and config_path.endswith("/**")):
            _add(
                errors,
                f"{target_path}.wrangler_config_path",
                config_problem or "must be an exact repository-relative path",
            )
        if target["wrangler_environment"] != target_id:
            _add(errors, f"{target_path}.wrangler_environment", "must match id")
        _strings(
            errors,
            f"{target_path}.prerequisites",
            target["prerequisites"],
            nonempty=True,
        )
        if target["migration_command"] is not None:
            _validate_verifier(
                errors,
                f"{target_path}.migration_command",
                target["migration_command"],
                cache_allowed=False,
            )
        _validate_verifier(
            errors,
            f"{target_path}.deploy_command",
            target["deploy_command"],
            cache_allowed=False,
        )
        smoke = target["smoke_verifiers"]
        if not isinstance(smoke, list) or not smoke:
            _add(errors, f"{target_path}.smoke_verifiers", "must be a non-empty list")
        else:
            for verifier_index, verifier in enumerate(smoke):
                _validate_verifier(
                    errors,
                    f"{target_path}.smoke_verifiers[{verifier_index}]",
                    verifier,
                    cache_allowed=False,
                )

    if set(targets) != {"development", "production"}:
        _add(errors, f"{path}.targets", "must contain development and production")
        return
    development = targets["development"]
    production = targets["production"]
    if development["source"] != "pr_head":
        _add(errors, f"{path}.targets.development.source", "must equal pr_head")
    if production["source"] != "merged_main":
        _add(errors, f"{path}.targets.production.source", "must equal merged_main")
    if development["data_mode"] != "isolated_non_production":
        _add(
            errors,
            f"{path}.targets.development.data_mode",
            "must equal isolated_non_production",
        )
    if production["data_mode"] != "production":
        _add(errors, f"{path}.targets.production.data_mode", "must equal production")
    if development["payment_mode"] not in ("sandbox", "not_applicable"):
        _add(
            errors,
            f"{path}.targets.development.payment_mode",
            "must be sandbox or not_applicable",
        )
    if production["payment_mode"] not in ("live", "not_applicable"):
        _add(
            errors,
            f"{path}.targets.production.payment_mode",
            "must be live or not_applicable",
        )
    if development["auth_mode"] not in ("development", "not_applicable"):
        _add(
            errors,
            f"{path}.targets.development.auth_mode",
            "must be development or not_applicable",
        )
    if production["auth_mode"] not in ("production", "not_applicable"):
        _add(
            errors,
            f"{path}.targets.production.auth_mode",
            "must be production or not_applicable",
        )
    if development["worker_name"] == production["worker_name"]:
        _add(errors, f"{path}.targets", "development and production worker_name must differ")
    development_prerequisites = development["prerequisites"]
    if not isinstance(development_prerequisites, list) or (
        "current_head_ci" not in development_prerequisites
    ):
        _add(
            errors,
            f"{path}.targets.development.prerequisites",
            "must include current_head_ci",
        )
    production_prerequisites = production["prerequisites"]
    for prerequisite in ("development_pass", "merged_main"):
        if not isinstance(production_prerequisites, list) or (
            prerequisite not in production_prerequisites
        ):
            _add(
                errors,
                f"{path}.targets.production.prerequisites",
                f"must include {prerequisite}",
            )


def _validate_scope_list(
    errors: list[str], path: str, value: Any, *, nonempty: bool = False
) -> list[str]:
    claims = _strings(errors, path, value, nonempty=nonempty)
    for index, claim in enumerate(claims):
        problem = validate_scope_claim(claim)
        if problem:
            _add(errors, f"{path}[{index}]", problem)
    return claims


def _cycle_nodes(edges: dict[str, list[str]]) -> set[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cyclic: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visiting:
            try:
                cyclic.update(trail[trail.index(node) :])
            except ValueError:
                cyclic.add(node)
            return
        if node in visited:
            return
        visiting.add(node)
        trail.append(node)
        for dependency in edges.get(node, []):
            if dependency in edges:
                visit(dependency, trail)
        trail.pop()
        visiting.remove(node)
        visited.add(node)

    for node in sorted(edges):
        visit(node, [])
    return cyclic


def _validate_graph(
    errors: list[str],
    value: Any,
    missions: dict[str, dict[str, Any]],
    verifier_ids: set[str],
) -> None:
    path = "plan.graph"
    if not _keys(errors, path, value, {"entry_nodes", "nodes", "edges"}):
        return

    entry_nodes = _strings(errors, f"{path}.entry_nodes", value["entry_nodes"], nonempty=True)
    nodes: dict[str, dict[str, Any]] = {}
    mission_nodes: dict[str, str] = {}
    node_keys = {
        "id",
        "kind",
        "ref",
        "executor",
        "allowed_outcomes",
        "max_attempts",
        "runtime",
    }
    if not isinstance(value["nodes"], list) or not value["nodes"]:
        _add(errors, f"{path}.nodes", "must be a non-empty list")
    else:
        for index, node in enumerate(value["nodes"]):
            node_path = f"{path}.nodes[{index}]"
            if not _keys(errors, node_path, node, node_keys, {"review"}):
                continue
            node_id = node["id"]
            if not _nonempty_string(node_id) or not ID_RE.fullmatch(node_id):
                _add(errors, f"{node_path}.id", "must be a flat uppercase identifier")
                continue
            if node_id in nodes:
                _add(errors, f"{node_path}.id", "must be unique")
                continue
            nodes[node_id] = node
            kind = node["kind"]
            if not isinstance(kind, str) or kind not in GRAPH_NODE_KINDS:
                _add(errors, f"{node_path}.kind", "has an unsupported value")
                kind = None
            executor = node["executor"]
            if not isinstance(executor, str) or executor not in GRAPH_EXECUTORS:
                _add(errors, f"{node_path}.executor", "has an unsupported value")
                executor = None
            outcomes = _strings(
                errors,
                f"{node_path}.allowed_outcomes",
                node["allowed_outcomes"],
                nonempty=True,
            )
            unknown_outcomes = sorted(set(outcomes) - GRAPH_OUTCOMES)
            if unknown_outcomes:
                _add(
                    errors,
                    f"{node_path}.allowed_outcomes",
                    f"unsupported outcomes: {', '.join(unknown_outcomes)}",
                )
            if not _is_int(node["max_attempts"]) or not 1 <= node["max_attempts"] <= 3:
                _add(errors, f"{node_path}.max_attempts", "must be an integer from 1 to 3")
            if executor in {"runtime_worker", "harness_parent"} and not set(outcomes).intersection(
                {"retryable_failure", "blocked"}
            ):
                _add(
                    errors,
                    f"{node_path}.allowed_outcomes",
                    "runtime or parent execution requires retryable_failure or blocked for failure",
                )

            ref = node["ref"]
            valid_ref = _nonempty_string(ref)
            if not valid_ref:
                _add(errors, f"{node_path}.ref", "must be a non-empty string")
            if kind == "mission":
                if valid_ref and ref not in missions:
                    _add(errors, f"{node_path}.ref", "must reference a PLAN mission")
                elif valid_ref and ref in mission_nodes:
                    _add(errors, f"{node_path}.ref", "each mission must have exactly one graph node")
                elif valid_ref:
                    mission_nodes[ref] = node_id
                if executor not in {"runtime_worker", "harness_parent"}:
                    _add(errors, f"{node_path}.executor", "mission requires runtime_worker or harness_parent")
            elif kind == "verifier":
                if valid_ref and ref not in verifier_ids:
                    _add(errors, f"{node_path}.ref", "must reference a declared verifier")
                if executor not in {"runtime_worker", "harness_parent", "local_command"}:
                    _add(errors, f"{node_path}.executor", "verifier has an incompatible executor")
                review = node.get("review")
                if executor == "runtime_worker":
                    review_path = f"{node_path}.review"
                    if _keys(
                        errors,
                        review_path,
                        review,
                        {"type", "mission_ids", "scope", "required_evidence"},
                    ):
                        if not isinstance(review["type"], str) or review["type"] not in RUNTIME_REVIEW_TYPES:
                            _add(errors, f"{review_path}.type", "has an unsupported review type")
                        review_missions = _strings(
                            errors,
                            f"{review_path}.mission_ids",
                            review["mission_ids"],
                            nonempty=True,
                        )
                        for mission_id in review_missions:
                            if mission_id not in missions:
                                _add(
                                    errors,
                                    f"{review_path}.mission_ids",
                                    f"unknown mission {mission_id!r}",
                                )
                        _validate_scope_list(
                            errors,
                            f"{review_path}.scope",
                            review["scope"],
                            nonempty=True,
                        )
                        _strings(
                            errors,
                            f"{review_path}.required_evidence",
                            review["required_evidence"],
                            nonempty=True,
                        )
                elif review is not None:
                    _add(
                        errors,
                        f"{node_path}.review",
                        "must be omitted unless a verifier uses runtime_worker",
                    )
            elif kind == "approval" and executor != "human":
                _add(errors, f"{node_path}.executor", "approval requires human")
            elif kind == "external_wait" and executor != "external_system":
                _add(errors, f"{node_path}.executor", "external_wait requires external_system")
            elif kind == "lifecycle":
                if executor != "harness_parent":
                    _add(errors, f"{node_path}.executor", "lifecycle requires harness_parent")
                if valid_ref and ref not in AUTHORIZATION_KEYS_V8:
                    _add(errors, f"{node_path}.ref", "must reference an authorization action")
            if kind != "verifier" and node.get("review") is not None:
                _add(
                    errors,
                    f"{node_path}.review",
                    "must be omitted unless a verifier uses runtime_worker",
                )

            runtime = node["runtime"]
            if executor == "runtime_worker":
                runtime_path = f"{node_path}.runtime"
                if _keys(
                    errors,
                    runtime_path,
                    runtime,
                    {"preferred_provider", "allowed_providers"},
                    {"provider_options"},
                ):
                    # allowed_providers is intentionally schema-valid even when it excludes
                    # whatever provider happens to host the current RUN: a PLAN may target a
                    # host chosen later. No further "can this ever run anywhere" check is
                    # added beyond nonempty + RUNTIME_PROVIDERS membership (just below):
                    # every member of RUNTIME_PROVIDERS has a native driver in
                    # RUNTIME_DRIVER_PRIORITY, so there is no provider combination that is
                    # structurally unrunnable on every host. A host/provider mismatch is a
                    # RUN-time "runtime_unavailable" outcome (see select_ready_nodes.py),
                    # not a PLAN authoring error.
                    providers = _strings(
                        errors,
                        f"{runtime_path}.allowed_providers",
                        runtime["allowed_providers"],
                        nonempty=True,
                    )
                    unknown_providers = sorted(set(providers) - RUNTIME_PROVIDERS)
                    if unknown_providers:
                        _add(
                            errors,
                            f"{runtime_path}.allowed_providers",
                            f"unsupported providers: {', '.join(unknown_providers)}",
                        )
                    preferred = runtime["preferred_provider"]
                    if preferred is not None and preferred not in providers:
                        _add(
                            errors,
                            f"{runtime_path}.preferred_provider",
                            "must be null or one of allowed_providers",
                        )
                    provider_options = runtime.get("provider_options", {})
                    if not isinstance(provider_options, dict):
                        _add(errors, f"{runtime_path}.provider_options", "must be an object")
                    else:
                        unknown_option_providers = sorted(set(provider_options) - set(providers))
                        if unknown_option_providers:
                            _add(
                                errors,
                                f"{runtime_path}.provider_options",
                                "contains providers not present in allowed_providers: "
                                + ", ".join(unknown_option_providers),
                            )
                        for provider, options in provider_options.items():
                            option_path = f"{runtime_path}.provider_options.{provider}"
                            if not _keys(
                                errors,
                                option_path,
                                options,
                                {"model", "reasoning_effort"},
                            ):
                                continue
                            model = options["model"]
                            if model is not None and not is_safe_model_token(model):
                                _add(errors, f"{option_path}.model", "must be null or a safe model token")
                            effort = options["reasoning_effort"]
                            if effort is not None and effort not in RUNTIME_REASONING_EFFORTS:
                                _add(
                                    errors,
                                    f"{option_path}.reasoning_effort",
                                    "must be null or a supported reasoning effort",
                                )
                            if provider not in {"codex", "claude_code"} and effort is not None:
                                _add(
                                    errors,
                                    f"{option_path}.reasoning_effort",
                                    "must be null unless the provider supports selectable effort",
                                )
            elif runtime is not None:
                _add(errors, f"{node_path}.runtime", "must be null unless executor is runtime_worker")

    for entry in entry_nodes:
        if entry not in nodes:
            _add(errors, f"{path}.entry_nodes", f"unknown node {entry!r}")
    if set(mission_nodes) != set(missions):
        missing = sorted(set(missions) - set(mission_nodes))
        if missing:
            _add(errors, f"{path}.nodes", f"missing mission nodes: {', '.join(missing)}")

    edges: dict[str, dict[str, Any]] = {}
    dependency_map = {node_id: [] for node_id in nodes}
    combined_map = {node_id: [] for node_id in nodes}
    outgoing = {node_id: [] for node_id in nodes}
    incoming = {node_id: [] for node_id in nodes}
    edge_keys = {"id", "kind", "from", "to", "on_outcomes", "max_traversals"}
    if not isinstance(value["edges"], list):
        _add(errors, f"{path}.edges", "must be a list")
        return
    for index, edge in enumerate(value["edges"]):
        edge_path = f"{path}.edges[{index}]"
        if not _keys(errors, edge_path, edge, edge_keys):
            continue
        edge_id = edge["id"]
        valid_edge_id = _nonempty_string(edge_id) and ID_RE.fullmatch(edge_id) is not None
        if not valid_edge_id:
            _add(errors, f"{edge_path}.id", "must be a flat uppercase identifier")
        elif edge_id in edges:
            _add(errors, f"{edge_path}.id", "must be unique")
            valid_edge_id = False
        else:
            edges[edge_id] = edge
        source = edge["from"]
        target = edge["to"]
        valid_source = _nonempty_string(source)
        valid_target = _nonempty_string(target)
        if not valid_source:
            _add(errors, f"{edge_path}.from", "must be a non-empty string")
        elif source not in nodes:
            _add(errors, f"{edge_path}.from", "references an unknown node")
        if not valid_target:
            _add(errors, f"{edge_path}.to", "must be a non-empty string")
        elif target not in nodes:
            _add(errors, f"{edge_path}.to", "references an unknown node")
        if valid_source and valid_target and source == target:
            _add(errors, edge_path, "self edges are forbidden")
        outcomes = _strings(errors, f"{edge_path}.on_outcomes", edge["on_outcomes"], nonempty=True)
        if valid_source and source in nodes:
            invalid = sorted(set(outcomes) - set(nodes[source].get("allowed_outcomes", [])))
            if invalid:
                _add(
                    errors,
                    f"{edge_path}.on_outcomes",
                    f"source node does not declare: {', '.join(invalid)}",
                )
        if edge["kind"] == "dependency":
            if outcomes != ["pass"]:
                _add(errors, f"{edge_path}.on_outcomes", "dependency requires exactly ['pass']")
            if edge["max_traversals"] is not None:
                _add(errors, f"{edge_path}.max_traversals", "dependency must be null")
            if valid_source and valid_target and source in nodes and target in nodes:
                dependency_map[target].append(source)
        elif edge["kind"] == "route":
            bound = edge["max_traversals"]
            if bound is not None and (not _is_int(bound) or not 1 <= bound <= 3):
                _add(errors, f"{edge_path}.max_traversals", "must be null or an integer from 1 to 3")
        else:
            _add(errors, f"{edge_path}.kind", "must be dependency or route")
        if valid_source and valid_target and source in nodes and target in nodes:
            combined_map[target].append(source)
            outgoing[source].append(target)
            incoming[target].append(source)

    cyclic_dependencies = _cycle_nodes(dependency_map)
    if cyclic_dependencies:
        _add(
            errors,
            f"{path}.edges",
            f"dependency cycle includes {', '.join(sorted(cyclic_dependencies))}",
        )

    cyclic_nodes = _cycle_nodes(combined_map)
    if cyclic_nodes:
        for edge_id, edge in edges.items():
            if (
                edge.get("kind") == "route"
                and edge.get("from") in cyclic_nodes
                and edge.get("to") in cyclic_nodes
                and edge.get("max_traversals") is None
            ):
                _add(
                    errors,
                    f"{path}.edges.{edge_id}.max_traversals",
                    "route cycles require an explicit traversal bound",
                )
        if not any(
            source in cyclic_nodes and target not in cyclic_nodes
            for source, targets in outgoing.items()
            for target in targets
        ):
            _add(errors, f"{path}.edges", "route cycles require an exit edge")

    roots = {node_id for node_id, sources in incoming.items() if not sources}
    if set(entry_nodes) != roots:
        _add(errors, f"{path}.entry_nodes", "must exactly match graph root nodes")
    reachable = set(entry_nodes)
    pending = list(entry_nodes)
    while pending:
        source = pending.pop()
        for target in outgoing.get(source, []):
            if target not in reachable:
                reachable.add(target)
                pending.append(target)
    unreachable = sorted(set(nodes) - reachable)
    if unreachable:
        _add(errors, f"{path}.nodes", f"unreachable nodes: {', '.join(unreachable)}")


def validate_plan(plan: dict[str, Any]) -> list[str]:
    """Return deterministic validation errors for a harness_plan object."""

    errors: list[str] = []
    top_keys = {
        "schema_version",
        "plan_id",
        "revision",
        "objective",
        "max_parallel_workers",
        "sources",
        "traces",
        "ui_surfaces",
        "risks",
        "batch_verifiers",
        "final_gates",
        "missions",
    }
    schema_version = plan.get("schema_version") if isinstance(plan, dict) else None
    if schema_version == 4:
        top_keys.update({"graph", "required_reviews"})
    optional_keys = {"release"} if schema_version in {3, 4} else set()
    if not _keys(errors, "plan", plan, top_keys, optional_keys):
        return sorted(errors)
    if plan["schema_version"] not in {2, 3, 4}:
        _add(errors, "plan.schema_version", "must equal 2, 3, or 4")
    if not _nonempty_string(plan["plan_id"]):
        _add(errors, "plan.plan_id", "must be a non-empty string")
    if not _is_int(plan["revision"]) or plan["revision"] < 1:
        _add(errors, "plan.revision", "must be a positive integer")
    if not _nonempty_string(plan["objective"]):
        _add(errors, "plan.objective", "must be a non-empty string")
    if (
        not _is_int(plan["max_parallel_workers"])
        or not 1 <= plan["max_parallel_workers"] <= 3
    ):
        _add(errors, "plan.max_parallel_workers", "must be an integer from 1 to 3")

    required_reviews: list[str] = []
    if schema_version == 4:
        required_reviews = _strings(
            errors,
            "plan.required_reviews",
            plan["required_reviews"],
        )
        if len(required_reviews) != len(set(required_reviews)):
            _add(errors, "plan.required_reviews", "must not contain duplicates")
        unknown_reviews = sorted(set(required_reviews) - RUNTIME_REVIEW_TYPES)
        if unknown_reviews:
            _add(
                errors,
                "plan.required_reviews",
                f"unsupported review types: {', '.join(unknown_reviews)}",
            )

    sources: dict[str, dict[str, Any]] = {}
    if not isinstance(plan["sources"], list) or not plan["sources"]:
        _add(errors, "plan.sources", "must be a non-empty list")
    else:
        source_keys = {"id", "kind", "location", "owner", "status", "notes"}
        if schema_version == 4:
            source_keys.update({"content_sha256", "source_revision"})
        for index, source in enumerate(plan["sources"]):
            path = f"plan.sources[{index}]"
            if not _keys(errors, path, source, source_keys):
                continue
            for key in {"id", "kind", "location", "owner", "status", "notes"}:
                if not _nonempty_string(source[key]):
                    _add(errors, f"{path}.{key}", "must be a non-empty string")
            if schema_version == 4:
                content_sha = source["content_sha256"]
                source_revision = source["source_revision"]
                if content_sha is not None and (
                    not isinstance(content_sha, str) or SHA256_RE.fullmatch(content_sha) is None
                ):
                    _add(errors, f"{path}.content_sha256", "must be null or a lowercase SHA-256 digest")
                if source_revision is not None and not _nonempty_string(source_revision):
                    _add(errors, f"{path}.source_revision", "must be null or a non-empty immutable revision")
                if content_sha is None and source_revision is None:
                    _add(
                        errors,
                        path,
                        "schema v4 sources require content_sha256 or source_revision",
                    )
            source_id = source["id"]
            if source_id in sources:
                _add(errors, f"{path}.id", f"duplicate source ID {source_id!r}")
            sources[source_id] = source

    traces: dict[str, dict[str, Any]] = {}
    if not isinstance(plan["traces"], list) or not plan["traces"]:
        _add(errors, "plan.traces", "must be a non-empty list")
    else:
        trace_keys = {
            "id",
            "source_ids",
            "priority",
            "requirement",
            "disposition",
            "rationale",
        }
        for index, trace in enumerate(plan["traces"]):
            path = f"plan.traces[{index}]"
            if not _keys(errors, path, trace, trace_keys):
                continue
            trace_id = trace["id"]
            if not _nonempty_string(trace_id) or not ID_RE.fullmatch(trace_id):
                _add(errors, f"{path}.id", "must be a flat uppercase identifier")
            if trace_id in traces:
                _add(errors, f"{path}.id", f"duplicate trace ID {trace_id!r}")
            traces[trace_id] = trace
            source_ids = _strings(errors, f"{path}.source_ids", trace["source_ids"], nonempty=True)
            for source_id in source_ids:
                if source_id not in sources:
                    _add(errors, f"{path}.source_ids", f"unknown source {source_id!r}")
            if trace["priority"] not in {"must", "should", "could"}:
                _add(errors, f"{path}.priority", "must be must, should, or could")
            if trace["disposition"] not in {"planned", "deferred", "out_of_scope"}:
                _add(errors, f"{path}.disposition", "has an unsupported value")
            if not _nonempty_string(trace["requirement"]):
                _add(errors, f"{path}.requirement", "must be a non-empty string")
            if trace["disposition"] != "planned" and not _nonempty_string(trace["rationale"]):
                _add(errors, f"{path}.rationale", "is required when not planned")
            if trace["disposition"] == "planned" and trace["rationale"] is not None and not _nonempty_string(trace["rationale"]):
                _add(errors, f"{path}.rationale", "must be null or a non-empty string")

    if not isinstance(plan["ui_surfaces"], list):
        _add(errors, "plan.ui_surfaces", "must be a list")
    else:
        seen_ui: set[str] = set()
        ui_keys = {"id", "trace_ids", "route", "breakpoints", "states", "evidence_gate"}
        for index, surface in enumerate(plan["ui_surfaces"]):
            path = f"plan.ui_surfaces[{index}]"
            if not _keys(errors, path, surface, ui_keys):
                continue
            if not _nonempty_string(surface["id"]):
                _add(errors, f"{path}.id", "must be a non-empty string")
            elif surface["id"] in seen_ui:
                _add(errors, f"{path}.id", "must be unique")
            seen_ui.add(surface["id"])
            for trace_id in _strings(errors, f"{path}.trace_ids", surface["trace_ids"], nonempty=True):
                if trace_id not in traces:
                    _add(errors, f"{path}.trace_ids", f"unknown trace {trace_id!r}")
                elif traces[trace_id]["disposition"] != "planned":
                    _add(errors, f"{path}.trace_ids", f"trace {trace_id!r} is not planned")
            if not _nonempty_string(surface["route"]):
                _add(errors, f"{path}.route", "must be a non-empty string")
            _strings(errors, f"{path}.breakpoints", surface["breakpoints"], nonempty=True)
            _strings(errors, f"{path}.states", surface["states"], nonempty=True)
            if surface["evidence_gate"] not in {"required", "optional", "n/a"}:
                _add(errors, f"{path}.evidence_gate", "has an unsupported value")

    if not isinstance(plan["risks"], list):
        _add(errors, "plan.risks", "must be a list")
    else:
        seen_risks: set[str] = set()
        risk_keys = {"id", "description", "impact", "mitigation", "stop_condition"}
        for index, risk in enumerate(plan["risks"]):
            path = f"plan.risks[{index}]"
            if not _keys(errors, path, risk, risk_keys):
                continue
            for key in ("id", "description", "mitigation", "stop_condition"):
                if not _nonempty_string(risk[key]):
                    _add(errors, f"{path}.{key}", "must be a non-empty string")
            if risk["id"] in seen_risks:
                _add(errors, f"{path}.id", "must be unique")
            seen_risks.add(risk["id"])
            if risk["impact"] not in {"high", "medium", "low"}:
                _add(errors, f"{path}.impact", "must be high, medium, or low")

    declared_verifier_ids: set[str] = set()
    for group in ("batch_verifiers", "final_gates"):
        if not isinstance(plan[group], list) or not plan[group]:
            _add(errors, f"plan.{group}", "must be a non-empty list")
        else:
            ids: set[str] = set()
            for index, verifier in enumerate(plan[group]):
                _validate_verifier(
                    errors,
                    f"plan.{group}[{index}]",
                    verifier,
                    cache_allowed=False,
                )
                if isinstance(verifier, dict) and isinstance(verifier.get("id"), str):
                    if verifier["id"] in ids:
                        _add(errors, f"plan.{group}[{index}].id", "must be unique")
                    ids.add(verifier["id"])
                    declared_verifier_ids.add(verifier["id"])

    if plan["schema_version"] in {3, 4} and "release" in plan:
        _validate_release(errors, plan["release"])

    missions: dict[str, dict[str, Any]] = {}
    if not isinstance(plan["missions"], list) or not plan["missions"]:
        _add(errors, "plan.missions", "must be a non-empty list")
        return sorted(set(errors))
    mission_keys = {
        "id",
        "alias",
        "objective",
        "priority",
        "merge_rank",
        "trace_ids",
        "write_scope",
        "deny_scope",
        "resource_inventory_complete",
        "serialized_resources",
        "runtime_resources",
        "worktree_eligible",
        "stop_conditions",
        "worker_verifiers",
        "integration_verifiers",
        "tasks",
    }
    if plan["schema_version"] != 4:
        mission_keys.add("depends_on")
    for index, mission in enumerate(plan["missions"]):
        path = f"plan.missions[{index}]"
        if not _keys(errors, path, mission, mission_keys):
            continue
        mission_id = mission["id"]
        if not _nonempty_string(mission_id) or not ID_RE.fullmatch(mission_id):
            _add(errors, f"{path}.id", "must be a flat uppercase identifier")
        if mission_id in missions:
            _add(errors, f"{path}.id", f"duplicate mission ID {mission_id!r}")
        missions[mission_id] = mission

    task_records: dict[str, tuple[str, dict[str, Any], str]] = {}
    task_keys = {
        "id",
        "alias",
        "objective",
        "acceptance_matrix",
        "trace_ids",
        "depends_on",
        "parent_task",
        "legacy_task_ids",
        "replaced_by",
        "split_reason",
        "refinement_generation",
        "write_scope",
        "verifiers",
    }
    for index, mission in enumerate(plan["missions"]):
        if not isinstance(mission, dict) or not set(mission_keys).issubset(mission):
            continue
        mission_path = f"plan.missions[{index}]"
        mission_id = mission["id"]
        for key in ("alias", "objective"):
            if not _nonempty_string(mission[key]):
                _add(errors, f"{mission_path}.{key}", "must be a non-empty string")
        for key in ("priority", "merge_rank"):
            if not _is_int(mission[key]):
                _add(errors, f"{mission_path}.{key}", "must be an integer")
        if plan["schema_version"] != 4:
            _strings(errors, f"{mission_path}.depends_on", mission["depends_on"])
        mission_trace_ids = _strings(
            errors, f"{mission_path}.trace_ids", mission["trace_ids"], nonempty=True
        )
        for trace_id in mission_trace_ids:
            if trace_id not in traces:
                _add(errors, f"{mission_path}.trace_ids", f"unknown trace {trace_id!r}")
            elif traces[trace_id]["disposition"] != "planned":
                _add(errors, f"{mission_path}.trace_ids", f"trace {trace_id!r} is not planned")
        mission_write = _validate_scope_list(
            errors, f"{mission_path}.write_scope", mission["write_scope"], nonempty=True
        )
        mission_deny = _validate_scope_list(errors, f"{mission_path}.deny_scope", mission["deny_scope"])
        for claim in mission_write:
            if parent_owned_path(claim) and not any(scope_contains(deny, claim) for deny in mission_deny):
                _add(errors, f"{mission_path}.write_scope", f"parent-owned claim {claim!r}")
        if not isinstance(mission["resource_inventory_complete"], bool):
            _add(errors, f"{mission_path}.resource_inventory_complete", "must be boolean")
        serialized = _strings(
            errors, f"{mission_path}.serialized_resources", mission["serialized_resources"]
        )
        if any(not item.strip() for item in serialized):
            _add(errors, f"{mission_path}.serialized_resources", "contains an empty key")
        if not isinstance(mission["runtime_resources"], list):
            _add(errors, f"{mission_path}.runtime_resources", "must be a list")
        else:
            resource_map: dict[str, str] = {}
            for resource_index, resource in enumerate(mission["runtime_resources"]):
                resource_path = f"{mission_path}.runtime_resources[{resource_index}]"
                if not _keys(errors, resource_path, resource, {"key", "access"}):
                    continue
                if not _nonempty_string(resource["key"]):
                    _add(errors, f"{resource_path}.key", "must be a non-empty string")
                if resource["access"] not in {"exclusive", "shared_read"}:
                    _add(errors, f"{resource_path}.access", "has an unsupported value")
                if resource["key"] in resource_map:
                    _add(errors, f"{resource_path}.key", "must be unique")
                resource_map[resource["key"]] = resource["access"]
        if not isinstance(mission["worktree_eligible"], bool):
            _add(errors, f"{mission_path}.worktree_eligible", "must be boolean")
        _strings(errors, f"{mission_path}.stop_conditions", mission["stop_conditions"], nonempty=True)
        for verifier_group in ("worker_verifiers", "integration_verifiers"):
            values = mission[verifier_group]
            if not isinstance(values, list) or not values:
                _add(errors, f"{mission_path}.{verifier_group}", "must be a non-empty list")
            else:
                ids: set[str] = set()
                for verifier_index, verifier in enumerate(values):
                    _validate_verifier(
                        errors,
                        f"{mission_path}.{verifier_group}[{verifier_index}]",
                        verifier,
                        selection_scopes=(
                            mission_write if verifier_group == "worker_verifiers" else None
                        ),
                        cache_allowed=verifier_group != "integration_verifiers",
                    )
                    if isinstance(verifier, dict) and isinstance(verifier.get("id"), str):
                        if verifier["id"] in ids:
                            _add(errors, f"{mission_path}.{verifier_group}[{verifier_index}].id", "must be unique")
                        ids.add(verifier["id"])
                        declared_verifier_ids.add(verifier["id"])
        if not isinstance(mission["tasks"], list) or not mission["tasks"]:
            _add(errors, f"{mission_path}.tasks", "must be a non-empty list")
            continue
        for task_index, task in enumerate(mission["tasks"]):
            task_path = f"{mission_path}.tasks[{task_index}]"
            if not _keys(errors, task_path, task, task_keys):
                continue
            task_id = task["id"]
            match = TASK_ID_RE.fullmatch(task_id) if isinstance(task_id, str) else None
            if not match or match.group(1) != mission_id:
                _add(errors, f"{task_path}.id", "must be a flat ID prefixed by its mission")
            if task_id in task_records:
                _add(errors, f"{task_path}.id", f"duplicate task ID {task_id!r}")
            task_records[task_id] = (mission_id, task, task_path)

    mission_edges = mission_dependencies(plan)
    for mission_id, mission in missions.items():
        for dependency in mission_edges[mission_id]:
            if dependency not in missions:
                _add(errors, f"mission {mission_id}.depends_on", f"unknown mission {dependency!r}")
            if dependency == mission_id:
                _add(errors, f"mission {mission_id}.depends_on", "cannot depend on itself")
    cyclic_missions = _cycle_nodes(mission_edges)
    if cyclic_missions:
        _add(errors, "plan.missions", f"dependency cycle includes {', '.join(sorted(cyclic_missions))}")

    task_edges: dict[str, list[str]] = {}
    parent_edges: dict[str, list[str]] = {}
    legacy_owner: dict[str, str] = {}
    planned_trace_coverage: set[str] = set()
    for task_id, (mission_id, task, path) in task_records.items():
        for key in ("alias", "objective"):
            if not _nonempty_string(task[key]):
                _add(errors, f"{path}.{key}", "must be a non-empty string")
        _strings(errors, f"{path}.acceptance_matrix", task["acceptance_matrix"])
        trace_ids = _strings(errors, f"{path}.trace_ids", task["trace_ids"], nonempty=True)
        for trace_id in trace_ids:
            if trace_id not in traces:
                _add(errors, f"{path}.trace_ids", f"unknown trace {trace_id!r}")
            elif traces[trace_id]["disposition"] != "planned":
                _add(errors, f"{path}.trace_ids", f"trace {trace_id!r} is not planned")
            else:
                planned_trace_coverage.add(trace_id)
            mission_trace_set = set(missions.get(mission_id, {}).get("trace_ids", []))
            if trace_id not in mission_trace_set:
                _add(errors, f"{path}.trace_ids", f"trace {trace_id!r} is not declared by its mission")
        dependencies = _strings(errors, f"{path}.depends_on", task["depends_on"])
        task_edges[task_id] = dependencies
        for dependency in dependencies:
            if dependency not in task_records:
                _add(errors, f"{path}.depends_on", f"unknown task {dependency!r}")
            elif task_records[dependency][0] != mission_id:
                _add(errors, f"{path}.depends_on", "cross-mission task dependency is forbidden")
        legacy_ids = _strings(errors, f"{path}.legacy_task_ids", task["legacy_task_ids"])
        for legacy_id in legacy_ids:
            if legacy_id in legacy_owner:
                _add(errors, f"{path}.legacy_task_ids", f"legacy ID also owned by {legacy_owner[legacy_id]}")
            legacy_owner[legacy_id] = task_id
        replacements = _strings(errors, f"{path}.replaced_by", task["replaced_by"])
        generation = task["refinement_generation"]
        if not _is_int(generation) or generation not in {0, 1}:
            _add(errors, f"{path}.refinement_generation", "must be 0 or 1")
        parent = task["parent_task"]
        if generation == 0:
            if parent is not None or task["split_reason"] is not None:
                _add(errors, path, "generation-0 task must have null parent_task and split_reason")
        elif generation == 1:
            if not _nonempty_string(parent) or not _nonempty_string(task["split_reason"]):
                _add(errors, path, "generation-1 task requires parent_task and split_reason")
            if replacements:
                _add(errors, f"{path}.replaced_by", "generation-1 task cannot be split again")
        parent_edges[task_id] = [parent] if isinstance(parent, str) else []
        if isinstance(parent, str):
            if parent not in task_records:
                _add(errors, f"{path}.parent_task", f"unknown task {parent!r}")
            elif task_records[parent][0] != mission_id:
                _add(errors, f"{path}.parent_task", "must be in the same mission")
            elif task_id not in task_records[parent][1].get("replaced_by", []):
                _add(errors, f"{path}.parent_task", "parent does not list this replacement")
        for replacement in replacements:
            if replacement not in task_records:
                _add(errors, f"{path}.replaced_by", f"unknown task {replacement!r}")
            elif task_records[replacement][0] != mission_id:
                _add(errors, f"{path}.replaced_by", "replacement must be in the same mission")
            elif task_records[replacement][1].get("parent_task") != task_id:
                _add(errors, f"{path}.replaced_by", f"replacement {replacement!r} does not point back")
        task_scopes = _validate_scope_list(errors, f"{path}.write_scope", task["write_scope"], nonempty=True)
        mission = missions.get(mission_id, {})
        mission_scopes = mission.get("write_scope", []) if isinstance(mission, dict) else []
        mission_denies = mission.get("deny_scope", []) if isinstance(mission, dict) else []
        for claim in task_scopes:
            if not any(scope_contains(parent_scope, claim) for parent_scope in mission_scopes):
                _add(errors, f"{path}.write_scope", f"claim {claim!r} escapes mission scope")
            if any(scope_overlap(deny, claim) for deny in mission_denies):
                _add(errors, f"{path}.write_scope", f"claim {claim!r} overlaps mission deny scope")
        if not isinstance(task["verifiers"], list) or not task["verifiers"]:
            _add(errors, f"{path}.verifiers", "must be a non-empty list")
        else:
            verifier_ids: set[str] = set()
            for verifier_index, verifier in enumerate(task["verifiers"]):
                _validate_verifier(
                    errors,
                    f"{path}.verifiers[{verifier_index}]",
                    verifier,
                    selection_scopes=task_scopes,
                )
                if isinstance(verifier, dict) and isinstance(verifier.get("id"), str):
                    if verifier["id"] in verifier_ids:
                        _add(errors, f"{path}.verifiers[{verifier_index}].id", "must be unique")
                    verifier_ids.add(verifier["id"])
                    declared_verifier_ids.add(verifier["id"])

    for task_id, dependencies in task_edges.items():
        for dependency in dependencies:
            if dependency in task_records and task_records[dependency][1].get("replaced_by"):
                _add(errors, f"task {task_id}.depends_on", f"cannot target superseded task {dependency!r}")
    cyclic_tasks = _cycle_nodes(task_edges)
    if cyclic_tasks:
        _add(errors, "plan.tasks", f"dependency cycle includes {', '.join(sorted(cyclic_tasks))}")
    cyclic_parents = _cycle_nodes(parent_edges)
    if cyclic_parents:
        _add(errors, "plan.tasks", f"parent cycle includes {', '.join(sorted(cyclic_parents))}")

    for legacy_id, owner in legacy_owner.items():
        if legacy_id in task_records:
            _add(errors, f"task {owner}.legacy_task_ids", f"legacy ID collides with canonical task {legacy_id!r}")

    for trace_id, trace in traces.items():
        if trace.get("disposition") == "planned" and trace_id not in planned_trace_coverage:
            _add(errors, f"trace {trace_id}", "planned trace has no task coverage")

    if plan["schema_version"] == 4:
        _validate_graph(errors, plan["graph"], missions, declared_verifier_ids)
        declared_reviews = {
            node.get("review", {}).get("type")
            for node in plan["graph"].get("nodes", [])
            if isinstance(node, dict)
            and node.get("kind") == "verifier"
            and node.get("executor") == "runtime_worker"
            and isinstance(node.get("review"), dict)
        }
        missing_reviews = sorted(set(required_reviews) - declared_reviews)
        if missing_reviews:
            _add(
                errors,
                "plan.required_reviews",
                "missing runtime review nodes: " + ", ".join(missing_reviews),
            )

    return sorted(set(errors))


def _optional_string(errors: list[str], path: str, value: Any) -> None:
    if value is not None and not _nonempty_string(value):
        _add(errors, path, "must be null or a non-empty string")


def _optional_sha(errors: list[str], path: str, value: Any) -> None:
    if value is not None and not is_full_sha(value):
        _add(errors, path, "must be null or a full lowercase Git SHA")


def _optional_nonnegative_int(errors: list[str], path: str, value: Any) -> None:
    if value is not None and (not _is_int(value) or value < 0):
        _add(errors, path, "must be null or a non-negative integer")


def _validate_landing(errors: list[str], value: Any, schema_version: int) -> None:
    path = "run.landing"
    keys = {
        "mode",
        "remote",
        "head_branch",
        "base_branch",
        "pushed_head_sha",
        "pr_number",
        "pr_url",
        "pr_state",
        "pr_head_sha",
        "checks_status",
        "checks_head_sha",
        "review_status",
        "review_head_sha",
        "blocking_findings",
        "unresolved_threads",
        "merge_status",
        "merged_sha",
    }
    if schema_version >= 4:
        keys.update({"auto_merge_requested", "auto_merge_head_sha"})
    if not _keys(errors, path, value, keys):
        return

    if value["mode"] not in {"local_only", "pull_request"}:
        _add(errors, f"{path}.mode", "must be local_only or pull_request")
    for key in ("remote", "head_branch", "base_branch", "pr_url"):
        _optional_string(errors, f"{path}.{key}", value[key])
    for key in (
        "pushed_head_sha",
        "pr_head_sha",
        "checks_head_sha",
        "review_head_sha",
        "merged_sha",
    ):
        _optional_sha(errors, f"{path}.{key}", value[key])
    if schema_version >= 4:
        if not isinstance(value["auto_merge_requested"], bool):
            _add(errors, f"{path}.auto_merge_requested", "must be boolean")
        _optional_sha(errors, f"{path}.auto_merge_head_sha", value["auto_merge_head_sha"])
    _optional_nonnegative_int(errors, f"{path}.blocking_findings", value["blocking_findings"])
    _optional_nonnegative_int(errors, f"{path}.unresolved_threads", value["unresolved_threads"])

    if value["pr_number"] is not None and (
        not _is_int(value["pr_number"]) or value["pr_number"] < 1
    ):
        _add(errors, f"{path}.pr_number", "must be null or a positive integer")
    if value["pr_state"] not in {"not_created", "draft", "open", "closed", "merged"}:
        _add(errors, f"{path}.pr_state", "has an unsupported value")
    if value["checks_status"] not in {"not_started", "pending", "PASS", "FAIL", "BLOCKED"}:
        _add(errors, f"{path}.checks_status", "has an unsupported value")
    if value["review_status"] not in {
        "not_requested",
        "pending",
        "PASS",
        "CHANGES_REQUESTED",
        "BLOCKED",
    }:
        _add(errors, f"{path}.review_status", "has an unsupported value")
    if value["merge_status"] not in {"not_ready", "ready", "merged", "closed_unmerged"}:
        _add(errors, f"{path}.merge_status", "has an unsupported value")

    if (
        _nonempty_string(value["head_branch"])
        and _nonempty_string(value["base_branch"])
        and value["head_branch"] == value["base_branch"]
    ):
        _add(errors, path, "head_branch and base_branch must differ")

    created_states = {"draft", "open", "closed", "merged"}
    if value["pr_state"] in created_states:
        required_created = (
            "remote",
            "head_branch",
            "base_branch",
            "pushed_head_sha",
            "pr_number",
            "pr_url",
            "pr_head_sha",
        )
        if any(value[key] is None for key in required_created):
            _add(errors, path, "created PR state is missing remote, branch, URL, number, or head data")
        if value["pr_head_sha"] != value["pushed_head_sha"]:
            _add(errors, path, "pr_head_sha must match pushed_head_sha")
    elif value["pr_state"] == "not_created":
        if any(value[key] is not None for key in ("pr_number", "pr_url", "pr_head_sha")):
            _add(errors, path, "not_created PR must not record number, URL, or PR head")

    if value["mode"] == "local_only" and value["pr_state"] != "not_created":
        _add(errors, path, "local_only mode cannot record a created PR")
    if value["mode"] == "local_only" and value["pushed_head_sha"] is not None:
        _add(errors, path, "local_only mode cannot record a pushed head")
    if value["checks_status"] == "PASS" and (
        value["pr_state"] not in created_states
        or value["checks_head_sha"] is None
        or value["checks_head_sha"] != value["pr_head_sha"]
    ):
        _add(errors, path, "PASS checks must bind to a created PR's current head")
    if value["review_status"] == "PASS":
        if (
            value["pr_state"] not in created_states
            or value["review_head_sha"] is None
            or value["review_head_sha"] != value["pr_head_sha"]
        ):
            _add(errors, path, "PASS review must bind to a created PR's current head")
        if value["blocking_findings"] != 0 or value["unresolved_threads"] != 0:
            _add(errors, path, "PASS review requires zero blocking findings and unresolved threads")
    if value["merge_status"] in {"ready", "merged"} and (
        value["pr_state"] != ("open" if value["merge_status"] == "ready" else "merged")
        or value["checks_status"] != "PASS"
        or value["review_status"] != "PASS"
        or value["checks_head_sha"] != value["pr_head_sha"]
        or value["review_head_sha"] != value["pr_head_sha"]
    ):
        _add(
            errors,
            path,
            f"{value['merge_status']} status requires the matching PR state with current-head PASS checks and review",
        )
    if value["merge_status"] == "merged" and (
        value["pr_state"] != "merged" or value["merged_sha"] is None
    ):
        _add(errors, path, "merged status requires a merged PR and merged_sha")
    if value["pr_state"] == "merged" and value["merge_status"] != "merged":
        _add(errors, path, "merged PR requires merge_status merged")
    if value["merge_status"] == "closed_unmerged" and value["pr_state"] != "closed":
        _add(errors, path, "closed_unmerged requires a closed PR")
    if value["pr_state"] == "closed" and value["merge_status"] != "closed_unmerged":
        _add(errors, path, "closed PR requires merge_status closed_unmerged")
    if value["merge_status"] != "merged" and value["merged_sha"] is not None:
        _add(errors, path, "only merged status may record merged_sha")
    if schema_version >= 4:
        if value["auto_merge_requested"]:
            if (
                value["mode"] != "pull_request"
                or value["merge_status"] not in {"ready", "merged"}
                or value["auto_merge_head_sha"] is None
                or value["auto_merge_head_sha"] != value["pr_head_sha"]
            ):
                _add(
                    errors,
                    path,
                    "auto_merge_requested requires a ready or merged current-head PR",
                )
        elif value["auto_merge_head_sha"] is not None:
            _add(
                errors,
                f"{path}.auto_merge_head_sha",
                "must be null when auto_merge_requested is false",
            )


def _validate_deployments(
    errors: list[str], value: Any, run: dict[str, Any], plan: dict[str, Any]
) -> None:
    path = "run.deployments"
    if not _keys(errors, path, value, {"provider", "development", "production"}):
        return
    provider = value["provider"]
    if provider not in DEPLOYMENT_PROVIDERS:
        _add(errors, f"{path}.provider", f"must be one of {sorted(DEPLOYMENT_PROVIDERS)}")

    release = plan.get("release")
    release_targets: dict[str, dict[str, Any]] = {}
    if plan.get("schema_version") not in {3, 4} or not isinstance(release, dict):
        _add(errors, path, "deployment state requires a PLAN release contract")
    elif release.get("provider") != value["provider"]:
        _add(errors, f"{path}.provider", "must match PLAN release provider")
    elif isinstance(release.get("targets"), list):
        release_targets = {
            target["id"]: target
            for target in release["targets"]
            if isinstance(target, dict)
            and target.get("id") in ("development", "production")
        }

    status_values = ("not_started", "pending", "PASS", "FAIL", "BLOCKED")
    migration_values = status_values + ("not_required",)
    target_keys = {
        "status",
        "source_sha",
        "worker_name",
        "url",
        "version_id",
        "migration_status",
        "verification_status",
        "rollback_version",
        "evidence",
    }
    targets: dict[str, dict[str, Any]] = {}
    for target_id in ("development", "production"):
        target = value[target_id]
        target_path = f"{path}.{target_id}"
        if not _keys(errors, target_path, target, target_keys):
            continue
        targets[target_id] = target
        if target["status"] not in status_values:
            _add(errors, f"{target_path}.status", "has an unsupported value")
        if target["migration_status"] not in migration_values:
            _add(errors, f"{target_path}.migration_status", "has an unsupported value")
        if target["verification_status"] not in status_values:
            _add(errors, f"{target_path}.verification_status", "has an unsupported value")
        _optional_sha(errors, f"{target_path}.source_sha", target["source_sha"])
        for key in ("worker_name", "url", "version_id", "rollback_version"):
            _optional_string(errors, f"{target_path}.{key}", target[key])
        declared_target = release_targets.get(target_id)
        if (
            target["worker_name"] is not None
            and declared_target is not None
            and target["worker_name"] != declared_target.get("worker_name")
        ):
            _add(errors, f"{target_path}.worker_name", "must match PLAN release target")
        evidence = _strings(errors, f"{target_path}.evidence", target["evidence"])
        if target["status"] == "not_started":
            if any(
                target[key] is not None
                for key in (
                    "source_sha",
                    "worker_name",
                    "url",
                    "version_id",
                    "rollback_version",
                )
            ):
                _add(errors, target_path, "not_started deployment must not record release data")
            if target["migration_status"] != "not_started":
                _add(errors, target_path, "not_started deployment requires migration_status not_started")
            if target["verification_status"] != "not_started":
                _add(errors, target_path, "not_started deployment requires verification_status not_started")
            if evidence:
                _add(errors, target_path, "not_started deployment must not record evidence")
        if target["status"] == "PASS":
            if provider == "cloudflare":
                if any(
                    not _nonempty_string(target[key])
                    for key in ("worker_name", "url", "version_id")
                ) or not is_full_sha(target["source_sha"]):
                    _add(errors, target_path, "PASS requires source SHA, worker, URL, and version ID")
            elif not is_full_sha(target["source_sha"]):
                _add(errors, target_path, "PASS requires a source SHA")
            if target["migration_status"] not in ("PASS", "not_required"):
                _add(errors, target_path, "PASS requires migration PASS or not_required")
            if target["verification_status"] != "PASS":
                _add(errors, target_path, "PASS requires verification_status PASS")
            if not evidence:
                _add(errors, target_path, "PASS requires retained evidence")
            mission_states = run.get("mission_states", {})
            mission_ids = list(mission_states) if isinstance(mission_states, dict) else []
            if not mission_ids or any(
                not authorization_covers(
                    run,
                    "deploy",
                    mission_id,
                    f"environment:{target_id}",
                    preserve_completed_run_expiry=True,
                )
                for mission_id in mission_ids
            ):
                _add(
                    errors,
                    target_path,
                    f"PASS requires deploy authorization for environment:{target_id}",
                )

    landing = run.get("landing")
    development = targets.get("development")
    production = targets.get("production")
    if isinstance(landing, dict) and development is not None and development["status"] == "PASS":
        if (
            landing.get("pr_state") not in ("draft", "open", "merged")
            or development["source_sha"] != landing.get("pr_head_sha")
            or landing.get("checks_status") != "PASS"
            or landing.get("checks_head_sha") != development["source_sha"]
        ):
            _add(
                errors,
                f"{path}.development",
                "PASS must bind to the current PR head after current-head CI passes",
            )
    if isinstance(landing, dict) and production is not None and production["status"] == "PASS":
        if development is None or development.get("status") != "PASS":
            _add(errors, f"{path}.production", "PASS requires development PASS first")
        if (
            landing.get("pr_state") != "merged"
            or landing.get("merge_status") != "merged"
            or production["source_sha"] != landing.get("merged_sha")
        ):
            _add(
                errors,
                f"{path}.production",
                "PASS must bind to the merged main SHA",
            )
    if run.get("status") == "complete" and (
        development is None
        or production is None
        or development.get("status") != "PASS"
        or production.get("status") != "PASS"
    ):
        _add(errors, path, "complete run requires development and production PASS")


def _validate_post_merge_cleanup(
    errors: list[str], value: Any, run: dict[str, Any]
) -> None:
    path = "run.post_merge_cleanup"
    if not _keys(
        errors,
        path,
        value,
        {"status", "base", "worktree", "local_branch", "evidence", "deferred_reason"},
    ):
        return

    status = value["status"]
    if status not in CLEANUP_STATUSES:
        _add(errors, f"{path}.status", "has an unsupported value")

    base = value["base"]
    if _keys(
        errors,
        f"{path}.base",
        base,
        {"branch", "head_sha", "merged_sha_reachable"},
    ):
        _optional_string(errors, f"{path}.base.branch", base["branch"])
        _optional_sha(errors, f"{path}.base.head_sha", base["head_sha"])
        if base["merged_sha_reachable"] is not None and not isinstance(
            base["merged_sha_reachable"], bool
        ):
            _add(
                errors,
                f"{path}.base.merged_sha_reachable",
                "must be null or boolean",
            )

    worktree = value["worktree"]
    if _keys(
        errors,
        f"{path}.worktree",
        worktree,
        {"path", "branch_ref", "head_sha", "dirty", "managed_by", "status"},
    ):
        _optional_string(errors, f"{path}.worktree.path", worktree["path"])
        _optional_string(errors, f"{path}.worktree.branch_ref", worktree["branch_ref"])
        _optional_sha(errors, f"{path}.worktree.head_sha", worktree["head_sha"])
        if worktree["dirty"] is not None and not isinstance(worktree["dirty"], bool):
            _add(errors, f"{path}.worktree.dirty", "must be null or boolean")
        if worktree["managed_by"] not in {None, "parent", "app"}:
            _add(errors, f"{path}.worktree.managed_by", "must be null, parent, or app")
        if worktree["status"] not in CLEANUP_WORKTREE_STATUSES:
            _add(errors, f"{path}.worktree.status", "has an unsupported value")

    local_branch = value["local_branch"]
    if _keys(
        errors,
        f"{path}.local_branch",
        local_branch,
        {"ref", "head_sha", "status"},
    ):
        _optional_string(errors, f"{path}.local_branch.ref", local_branch["ref"])
        _optional_sha(errors, f"{path}.local_branch.head_sha", local_branch["head_sha"])
        if local_branch["status"] not in CLEANUP_BRANCH_STATUSES:
            _add(errors, f"{path}.local_branch.status", "has an unsupported value")

    evidence = _strings(errors, f"{path}.evidence", value["evidence"])
    _optional_string(errors, f"{path}.deferred_reason", value["deferred_reason"])

    if not all(isinstance(item, dict) for item in (base, worktree, local_branch)):
        return

    landing = run.get("landing")
    if not isinstance(landing, dict):
        return

    expected_branch_ref = (
        f"refs/heads/{landing['head_branch']}"
        if _nonempty_string(landing.get("head_branch"))
        and not landing["head_branch"].startswith("refs/heads/")
        else landing.get("head_branch")
    )
    observed = run.get("observed")
    observed_git = observed.get("git") if isinstance(observed, dict) else None
    parent_worktree_path = (
        observed_git.get("parent_worktree_path")
        if isinstance(observed_git, dict)
        else None
    )
    observed_worktrees = (
        observed_git.get("worktrees", [])
        if isinstance(observed_git, dict)
        and isinstance(observed_git.get("worktrees", []), list)
        else []
    )

    worktree_status = worktree.get("status")
    worktree_manager = worktree.get("managed_by")
    if worktree_status in {"pending", "removed"} and worktree_manager != "parent":
        _add(
            errors,
            f"{path}.worktree.managed_by",
            "manual cleanup worktrees must be parent-managed",
        )
    if worktree_status == "platform_managed" and worktree_manager != "app":
        _add(
            errors,
            f"{path}.worktree.managed_by",
            "platform-managed worktrees must be app-managed",
        )
    if worktree_status == "not_applicable" and worktree_manager is not None:
        _add(
            errors,
            f"{path}.worktree.managed_by",
            "must be null when no linked worktree applies",
        )
    if (
        run.get("status") == "complete"
        and landing.get("mode") == "pull_request"
        and status in {"not_started", "ready"}
    ):
        _add(errors, path, "a completed pull-request run must complete or defer cleanup")

    if status == "not_applicable":
        if run.get("status") == "complete":
            if not isinstance(observed, dict) or not _nonempty_string(
                observed.get("captured_at")
            ):
                _add(
                    errors,
                    "run.observed.captured_at",
                    "is required for terminal not-applicable cleanup",
                )
            if not _nonempty_string(parent_worktree_path):
                _add(
                    errors,
                    "run.observed.git.parent_worktree_path",
                    "is required for terminal not-applicable cleanup",
                )
            if any(
                isinstance(item, dict)
                and item.get("path") != parent_worktree_path
                and item.get("branch_ref") == expected_branch_ref
                for item in observed_worktrees
            ):
                _add(
                    errors,
                    f"{path}.worktree.status",
                    "not_applicable requires no matching linked worktree in the current observation",
                )
        if landing.get("mode") == "pull_request" and landing.get("pr_state") not in {
            "closed",
            "not_created",
        }:
            _add(
                errors,
                path,
                "not_applicable is valid only before PR creation, after an unmerged close, or in local-only mode",
            )
        return

    if status == "not_started":
        if value["deferred_reason"] is not None:
            _add(errors, f"{path}.deferred_reason", "must be null unless cleanup is deferred")
        return

    if status == "deferred":
        if not _nonempty_string(value["deferred_reason"]):
            _add(errors, f"{path}.deferred_reason", "is required when cleanup is deferred")
        return

    if value["deferred_reason"] is not None:
        _add(errors, f"{path}.deferred_reason", "must be null unless cleanup is deferred")

    if landing.get("merge_status") != "merged" or landing.get("pr_state") != "merged":
        _add(errors, path, "ready or complete cleanup requires a merged pull request")

    base_branch = landing.get("base_branch")
    if base.get("branch") != base_branch:
        _add(errors, f"{path}.base.branch", "must match landing.base_branch")
    if base.get("head_sha") is None:
        _add(errors, f"{path}.base.head_sha", "is required for cleanup")
    if base.get("merged_sha_reachable") is not True:
        _add(
            errors,
            f"{path}.base.merged_sha_reachable",
            "must be true after observing the merged SHA on the base branch",
        )
    if local_branch.get("ref") != expected_branch_ref:
        _add(errors, f"{path}.local_branch.ref", "must match the merged PR head branch")
    if local_branch.get("head_sha") != landing.get("pr_head_sha"):
        _add(errors, f"{path}.local_branch.head_sha", "must match the merged PR head SHA")

    if not isinstance(observed, dict) or not _nonempty_string(observed.get("captured_at")):
        _add(errors, "run.observed.captured_at", "is required before cleanup")
    if not isinstance(observed_git, dict) or observed_git.get("parent_dirty") is not False:
        _add(errors, "run.observed.git.parent_dirty", "must be false before cleanup")
    if not _nonempty_string(parent_worktree_path):
        _add(errors, "run.observed.git.parent_worktree_path", "is required before cleanup")
    parent_branch = observed_git.get("parent_branch") if isinstance(observed_git, dict) else None
    parent_branch_ref = (
        f"refs/heads/{parent_branch}"
        if _nonempty_string(parent_branch) and not parent_branch.startswith("refs/heads/")
        else parent_branch
    )
    if (
        parent_branch_ref == local_branch.get("ref")
        and isinstance(observed_git, dict)
        and observed_git.get("parent_head_sha") != landing.get("pr_head_sha")
    ):
        _add(
            errors,
            "run.observed.git.parent_head_sha",
            "must match the merged PR head while the primary checkout is on the cleanup branch",
        )

    mission_states = run.get("mission_states")
    if not isinstance(mission_states, dict) or not mission_states or any(
        not isinstance(state, dict) or state.get("phase") != "integrated"
        for state in mission_states.values()
    ):
        _add(errors, path, "cleanup requires every run mission to be integrated")
        mission_ids: list[str] = []
    else:
        mission_ids = list(mission_states)

    branch_target = (
        f"branch:{local_branch['ref']}"
        if _nonempty_string(local_branch.get("ref"))
        else None
    )
    preserve_expiry = status == "complete"
    if branch_target is None or any(
        not authorization_covers(
            run,
            "delete_branches",
            mission_id,
            branch_target,
            preserve_completed_run_expiry=preserve_expiry,
        )
        for mission_id in mission_ids
    ):
        _add(
            errors,
            path,
            "cleanup requires matching delete_branches authorization for the exact local branch",
        )

    if worktree_status in {"pending", "removed"}:
        required_worktree = ("path", "branch_ref", "head_sha", "dirty")
        if any(worktree.get(key) is None for key in required_worktree):
            _add(errors, f"{path}.worktree", "manual cleanup requires path, branch, head, and dirty state")
        if worktree.get("branch_ref") != local_branch.get("ref"):
            _add(errors, f"{path}.worktree.branch_ref", "must match the local cleanup branch")
        if worktree.get("head_sha") != landing.get("pr_head_sha"):
            _add(errors, f"{path}.worktree.head_sha", "must match the merged PR head SHA")
        if worktree.get("dirty") is not False:
            _add(errors, f"{path}.worktree.dirty", "must be false before removal")
        if worktree.get("path") == parent_worktree_path:
            _add(errors, f"{path}.worktree.path", "must not target the primary checkout")
        worktree_target = (
            f"worktree:{worktree['path']}"
            if _nonempty_string(worktree.get("path"))
            else None
        )
        if worktree_target is None or any(
            not authorization_covers(
                run,
                "remove_worktrees",
                mission_id,
                worktree_target,
                preserve_completed_run_expiry=preserve_expiry,
            )
            for mission_id in mission_ids
        ):
            _add(
                errors,
                path,
                "cleanup requires matching remove_worktrees authorization for the exact path",
            )

        matching_worktrees = [
            item
            for item in observed_worktrees
            if isinstance(item, dict) and item.get("path") == worktree.get("path")
        ]
        if status == "ready" and not any(
            item.get("branch_ref") == worktree.get("branch_ref")
            and item.get("head_sha") == worktree.get("head_sha")
            and item.get("managed_by") == "parent"
            and item.get("dirty") is False
            for item in matching_worktrees
        ):
            _add(
                errors,
                f"{path}.worktree",
                "ready cleanup must match an observed clean parent-managed worktree",
            )
        if status == "complete" and matching_worktrees:
            _add(errors, f"{path}.worktree", "removed worktree must be absent from the refreshed observation")
    elif any(
        worktree.get(key) is not None for key in ("path", "branch_ref", "head_sha", "dirty")
    ):
        _add(
            errors,
            f"{path}.worktree",
            "non-manual worktree status must not record manual cleanup fields",
        )

    matching_linked_worktrees = [
        item
        for item in observed_worktrees
        if isinstance(item, dict)
        and item.get("path") != parent_worktree_path
        and item.get("branch_ref") == local_branch.get("ref")
    ]
    if (
        status in {"ready", "complete"}
        and worktree_status == "not_applicable"
        and matching_linked_worktrees
    ):
        _add(
            errors,
            f"{path}.worktree.status",
            "not_applicable requires no matching linked worktree in the current observation",
        )

    if status == "ready":
        if local_branch.get("status") != "pending":
            _add(errors, f"{path}.local_branch.status", "must be pending when cleanup is ready")
        if worktree_status not in {"pending", "not_applicable"}:
            _add(errors, f"{path}.worktree.status", "must be pending or not_applicable when cleanup is ready")
    elif status == "complete":
        if local_branch.get("status") != "deleted":
            _add(errors, f"{path}.local_branch.status", "must be deleted when cleanup is complete")
        if worktree_status not in {"removed", "not_applicable"}:
            _add(errors, f"{path}.worktree.status", "must be removed or not_applicable when cleanup is complete")
        if not evidence:
            _add(errors, f"{path}.evidence", "must record cleanup verification evidence")
        if isinstance(observed_git, dict):
            parent_branch = observed_git.get("parent_branch")
            if _nonempty_string(parent_branch):
                parent_branch = parent_branch.removeprefix("refs/heads/")
            if parent_branch != base_branch:
                _add(errors, "run.observed.git.parent_branch", "must be the base branch after cleanup")
            if observed_git.get("parent_head_sha") != base.get("head_sha"):
                _add(errors, "run.observed.git.parent_head_sha", "must match the observed base head after cleanup")


def _validate_authorization_scope(
    errors: list[str],
    path: str,
    value: Any,
    *,
    action: bool,
    action_name: str | None = None,
    allow_future_pr: bool = False,
) -> None:
    required = {"run_id", "mission_ids", "targets"} if action else {"run_id", "mission_ids", "expires_when"}
    if not _keys(errors, path, value, required):
        return
    if not _nonempty_string(value["run_id"]):
        _add(errors, f"{path}.run_id", "must be a non-empty string")
    _strings(errors, f"{path}.mission_ids", value["mission_ids"], nonempty=True)
    if action:
        targets = _strings(errors, f"{path}.targets", value["targets"], nonempty=True)
        for target in targets:
            if target == "*":
                continue
            if target.startswith("future-pr:"):
                if (
                    not allow_future_pr
                    or action_name not in {"manage_pr_review", "merge_pr"}
                    or not FUTURE_PR_TARGET_RE.fullmatch(target)
                ):
                    _add(errors, f"{path}.targets", f"unsupported target {target!r}")
                continue
            if not TARGET_RE.fullmatch(target):
                _add(errors, f"{path}.targets", f"unsupported target {target!r}")
            elif action_name == "invoke_external_runtime" and not target.startswith(
                "runtime:"
            ):
                _add(
                    errors,
                    f"{path}.targets",
                    "invoke_external_runtime requires runtime:<provider> targets",
                )
    else:
        if value["expires_when"] not in EXPIRY_BOUNDARIES:
            _add(
                errors,
                f"{path}.expires_when",
                "must be wave_closed, run_complete, or explicit_revocation",
            )


def authorization_covers(
    run: dict[str, Any],
    action: str,
    mission_id: str,
    target: str | None = None,
    *,
    preserve_completed_run_expiry: bool = False,
) -> bool:
    authorizations = run.get("authorizations")
    if not isinstance(authorizations, dict):
        return False
    entry = authorizations.get(action, {})
    if not isinstance(entry, dict) or entry.get("authorized") is not True:
        return False
    scope = entry.get("scope")
    if not isinstance(scope, dict) or scope.get("run_id") != run.get("run_id"):
        return False
    missions = scope.get("mission_ids", [])
    if mission_id not in missions and "*" not in missions:
        return False
    targets = scope.get("targets", [])
    if target is not None and target not in targets and "*" not in targets:
        return False
    boundary = entry.get("expires_when")
    expiry_is_preserved = (
        preserve_completed_run_expiry
        and boundary == "run_complete"
        and run.get("status") == "complete"
    )
    return _nonempty_string(entry.get("source")) and (
        expiry_is_preserved or _authorization_not_expired(run, boundary)
    )


def _landing_future_pr_target(landing: dict[str, Any]) -> str | None:
    pr_url = landing.get("pr_url")
    base_branch = landing.get("base_branch")
    head_branch = landing.get("head_branch")
    if (
        not _nonempty_string(pr_url)
        or not _nonempty_string(base_branch)
        or not _nonempty_string(head_branch)
    ):
        return None
    match = GITHUB_PR_URL_RE.fullmatch(pr_url)
    if match is None:
        return None
    return (
        f"future-pr:{match.group('repository')}:"
        f"base={base_branch}:head={head_branch}"
    )


def execution_covers(run: dict[str, Any], mission_id: str) -> bool:
    if run.get("execution_authorized") is not True:
        return False
    if not _nonempty_string(run.get("execution_authorization_source")):
        return False
    scope = run.get("execution_authorization_scope")
    if not isinstance(scope, dict) or scope.get("run_id") != run.get("run_id"):
        return False
    missions = scope.get("mission_ids", [])
    return (mission_id in missions or "*" in missions) and _authorization_not_expired(
        run, scope.get("expires_when")
    )


def _authorization_not_expired(run: dict[str, Any], boundary: Any) -> bool:
    if boundary == "explicit_revocation":
        return True
    if boundary == "run_complete":
        return run.get("status") != "complete"
    if boundary == "wave_closed":
        return run.get("active_wave", {}).get("status") not in {"closed", "superseded"}
    return False


def _validate_graph_state(
    errors: list[str], plan: dict[str, Any], run: dict[str, Any]
) -> None:
    path = "run.graph_state"
    value = run.get("graph_state")
    if not _keys(errors, path, value, {"graph_revision", "node_states", "edge_states"}):
        return
    if value["graph_revision"] != plan.get("revision"):
        _add(errors, f"{path}.graph_revision", "must match PLAN revision")

    graph = plan.get("graph", {})
    graph_nodes = {
        node["id"]: node
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    graph_edges = {
        edge["id"]: edge
        for edge in graph.get("edges", [])
        if isinstance(edge, dict) and isinstance(edge.get("id"), str)
    }
    mission_states = run.get("mission_states", {})

    node_states = value["node_states"]
    node_state_keys = {
        "phase",
        "attempts",
        "last_attempt_id",
        "last_outcome",
        "bound_worker_id",
        "blockers",
    }
    if not isinstance(node_states, dict):
        _add(errors, f"{path}.node_states", "must be an object")
    else:
        if set(node_states) != set(graph_nodes):
            _add(errors, f"{path}.node_states", "keys must exactly match PLAN graph nodes")
        for node_id, state in node_states.items():
            state_path = f"{path}.node_states.{node_id}"
            if node_id not in graph_nodes or not _keys(errors, state_path, state, node_state_keys):
                continue
            node = graph_nodes[node_id]
            phase = state["phase"]
            valid_phase = isinstance(phase, str) and phase in GRAPH_NODE_PHASES
            if not valid_phase:
                _add(errors, f"{state_path}.phase", "has an unsupported value")
            attempts = state["attempts"]
            if not _is_int(attempts) or attempts < 0:
                _add(errors, f"{state_path}.attempts", "must be a non-negative integer")
            elif attempts > node.get("max_attempts", 0):
                _add(errors, f"{state_path}.attempts", "exceeds PLAN max_attempts")
            for key in ("last_attempt_id", "bound_worker_id"):
                _optional_string(errors, f"{state_path}.{key}", state[key])
            outcome = state["last_outcome"]
            if outcome is not None and (
                not isinstance(outcome, str)
                or outcome not in node.get("allowed_outcomes", [])
            ):
                _add(errors, f"{state_path}.last_outcome", "is not declared by the PLAN node")
            blockers = _strings(errors, f"{state_path}.blockers", state["blockers"])
            if valid_phase and phase in {"succeeded", "failed", "blocked"} and (
                not _nonempty_string(state["last_attempt_id"])
                or outcome is None
                or attempts < 1
            ):
                _add(errors, state_path, "terminal node requires attempt identity, outcome, and attempts")
            if phase == "blocked" and not blockers:
                _add(errors, f"{state_path}.blockers", "blocked node requires a blocker")
            if phase == "running" and node.get("executor") == "runtime_worker" and not _nonempty_string(
                state["bound_worker_id"]
            ):
                _add(errors, f"{state_path}.bound_worker_id", "is required for a running runtime worker")

            if node.get("kind") == "mission" and node.get("ref") in mission_states:
                mission_state = mission_states[node["ref"]]
                mission_phase = mission_state.get("phase") if isinstance(mission_state, dict) else None
                if phase == "succeeded" and (
                    outcome != "pass"
                    or mission_phase != "integrated"
                    or mission_state.get("integration_gate") != "PASS"
                ):
                    _add(errors, state_path, "succeeded mission node requires integrated mission PASS")
                if mission_phase == "integrated" and (
                    phase != "succeeded" or outcome != "pass"
                ):
                    _add(errors, state_path, "integrated mission must be a succeeded pass node")
                if phase == "running" and mission_phase not in {
                    "leased",
                    "worker_running",
                    "worker_passed",
                    "integrating",
                }:
                    _add(errors, state_path, "running mission node does not match mission phase")
                if phase == "ready" and mission_phase not in {"queued", "ready"}:
                    _add(errors, state_path, "ready mission node does not match mission phase")

    edge_states = value["edge_states"]
    edge_state_keys = {"status", "traversals", "source_attempt_id"}
    if not isinstance(edge_states, dict):
        _add(errors, f"{path}.edge_states", "must be an object")
    else:
        if set(edge_states) != set(graph_edges):
            _add(errors, f"{path}.edge_states", "keys must exactly match PLAN graph edges")
        for edge_id, state in edge_states.items():
            state_path = f"{path}.edge_states.{edge_id}"
            if edge_id not in graph_edges or not _keys(errors, state_path, state, edge_state_keys):
                continue
            status = state["status"]
            if not isinstance(status, str) or status not in GRAPH_EDGE_PHASES:
                _add(errors, f"{state_path}.status", "has an unsupported value")
            traversals = state["traversals"]
            if not _is_int(traversals) or traversals < 0:
                _add(errors, f"{state_path}.traversals", "must be a non-negative integer")
            bound = graph_edges[edge_id].get("max_traversals")
            if _is_int(traversals) and _is_int(bound) and traversals > bound:
                _add(errors, f"{state_path}.traversals", "exceeds PLAN max_traversals")
            _optional_string(errors, f"{state_path}.source_attempt_id", state["source_attempt_id"])
            if state["status"] == "traversed" and (
                not _is_int(traversals)
                or traversals < 1
                or not _nonempty_string(state["source_attempt_id"])
            ):
                _add(errors, state_path, "traversed edge requires traversal count and source attempt")


def _validate_gate_results(
    errors: list[str],
    plan: dict[str, Any],
    run: dict[str, Any],
    *,
    plan_key: str,
    run_key: str,
    label: str,
) -> None:
    results = run[run_key]
    root_path = f"run.{run_key}"
    plan_gates = plan.get(plan_key)
    expected_ids = (
        {
            gate["id"]
            for gate in plan_gates
            if isinstance(gate, dict) and _nonempty_string(gate.get("id"))
        }
        if isinstance(plan_gates, list)
        else set()
    )
    if not isinstance(results, list):
        _add(errors, root_path, "must be a list")
        return

    seen: set[str] = set()
    valid_results: list[dict[str, Any]] = []
    result_keys = {"id", "status", "head_sha", "evidence"}
    integration = run.get("integration")
    integration_head = (
        integration.get("integration_head_sha")
        if isinstance(integration, dict)
        else None
    )
    for index, result in enumerate(results):
        path = f"{root_path}[{index}]"
        if not _keys(errors, path, result, result_keys):
            continue
        gate_id = result["id"]
        if not _nonempty_string(gate_id):
            _add(errors, f"{path}.id", "must be a non-empty string")
        else:
            if gate_id not in expected_ids:
                _add(errors, f"{path}.id", f"unknown {label} {gate_id!r}")
            elif gate_id in seen:
                _add(errors, f"{path}.id", "must be unique")
            seen.add(gate_id)
        if not isinstance(result["status"], str) or result["status"] not in GATE_VALUES:
            _add(errors, f"{path}.status", "has an unsupported gate value")
        _optional_sha(errors, f"{path}.head_sha", result["head_sha"])
        evidence = _strings(errors, f"{path}.evidence", result["evidence"])
        if result["status"] == "PASS" and (
            result["head_sha"] is None or not evidence
        ):
            _add(errors, path, "PASS requires head_sha and non-empty evidence")
        if result["status"] == "PASS" and result["head_sha"] != integration_head:
            _add(errors, path, f"PASS {label} must match integration_head_sha")
        valid_results.append(result)

    if seen != expected_ids:
        _add(errors, root_path, f"IDs must exactly match PLAN {plan_key}")

    if run.get("status") != "complete":
        return
    if any(result.get("status") != "PASS" for result in valid_results):
        _add(errors, root_path, f"complete run requires every {label} to PASS")
    if any(result.get("head_sha") != integration_head for result in valid_results):
        _add(
            errors,
            root_path,
            f"complete run {label} results must match integration_head_sha",
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


def _validate_workflow_runs(
    errors: list[str], plan: dict[str, Any], run: dict[str, Any]
) -> None:
    value = run.get("workflow_runs")
    if value is None:
        return
    if not isinstance(value, list):
        _add(errors, "run.workflow_runs", "must be a list")
        return
    graph_nodes = {
        node["id"]: node
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict) and _nonempty_string(node.get("id"))
    }
    seen_ids: set[str] = set()
    active_attempts: set[tuple[str, str]] = set()
    entry_keys = {
        "workflow_run_id",
        "workflow_task_id",
        "resume_from_run_id",
        "script_path",
        "script_sha256",
        "run_id",
        "plan_revision",
        "plan_digest_sha256",
        "graph_revision",
        "batch_base_sha",
        "node_ids",
        "attempt_ids",
        "provider",
        "driver",
        "tool_profile",
        "status",
        "result_evidence",
        "metrics",
    }
    for index, item in enumerate(value):
        path = f"run.workflow_runs[{index}]"
        if not _keys(errors, path, item, entry_keys):
            continue
        workflow_run_id = item["workflow_run_id"]
        if not _nonempty_string(workflow_run_id):
            _add(errors, f"{path}.workflow_run_id", "must be a non-empty string")
        elif workflow_run_id in seen_ids:
            _add(errors, f"{path}.workflow_run_id", "must be unique")
        else:
            seen_ids.add(workflow_run_id)
        _optional_string(errors, f"{path}.workflow_task_id", item["workflow_task_id"])
        _optional_string(errors, f"{path}.resume_from_run_id", item["resume_from_run_id"])
        if not _nonempty_string(item["script_path"]):
            _add(errors, f"{path}.script_path", "must be a non-empty string")
        if not _nonempty_string(item["script_sha256"]) or not SHA256_RE.fullmatch(
            item["script_sha256"]
        ):
            _add(errors, f"{path}.script_sha256", "must be a lowercase SHA-256")
        if item["run_id"] != run.get("run_id"):
            _add(errors, f"{path}.run_id", "must match run.run_id")
        if not _is_int(item["plan_revision"]) or item["plan_revision"] < 1:
            _add(errors, f"{path}.plan_revision", "must be a positive integer")
        if not _nonempty_string(item["plan_digest_sha256"]) or not SHA256_RE.fullmatch(
            item["plan_digest_sha256"]
        ):
            _add(errors, f"{path}.plan_digest_sha256", "must be a lowercase SHA-256")
        if not _is_int(item["graph_revision"]) or item["graph_revision"] < 1:
            _add(errors, f"{path}.graph_revision", "must be a positive integer")
        if not isinstance(item["batch_base_sha"], str) or not SHA_RE.fullmatch(
            item["batch_base_sha"]
        ):
            _add(errors, f"{path}.batch_base_sha", "must be a full Git SHA")
        node_ids = _strings(errors, f"{path}.node_ids", item["node_ids"], nonempty=True)
        if len(node_ids) != len(set(node_ids)):
            _add(errors, f"{path}.node_ids", "must not contain duplicates")
        raw_attempt_ids = item["attempt_ids"]
        attempt_ids: dict[str, str] = {}
        if not isinstance(raw_attempt_ids, dict):
            _add(errors, f"{path}.attempt_ids", "must be an object keyed by node ID")
        else:
            for node_id, attempt_id in raw_attempt_ids.items():
                if not _nonempty_string(node_id) or not _nonempty_string(attempt_id):
                    _add(errors, f"{path}.attempt_ids", "keys and values must be non-empty strings")
                    continue
                attempt_ids[node_id] = attempt_id
            if set(attempt_ids) != set(node_ids):
                _add(errors, f"{path}.attempt_ids", "keys must exactly match node_ids")
        provider = item["provider"]
        allowed_drivers = WORKFLOW_RUN_DRIVERS_BY_PROVIDER.get(provider)
        if allowed_drivers is None:
            _add(errors, f"{path}.provider", "has an unsupported workflow provider")
        driver = item["driver"]
        if not isinstance(driver, str) or (
            allowed_drivers is not None and driver not in allowed_drivers
        ):
            _add(errors, f"{path}.driver", "does not match the workflow provider")
        profile = item["tool_profile"]
        if not isinstance(profile, str) or profile not in WORKFLOW_TOOL_PROFILES:
            _add(errors, f"{path}.tool_profile", "has an unsupported value")
        status = item["status"]
        if not isinstance(status, str) or status not in WORKFLOW_RUN_STATUSES:
            _add(errors, f"{path}.status", "has an unsupported value")
        _strings(errors, f"{path}.result_evidence", item["result_evidence"])
        metrics = item["metrics"]
        if _keys(errors, f"{path}.metrics", metrics, {"duration_ms", "token_count"}):
            for metric in ("duration_ms", "token_count"):
                current = metrics[metric]
                if current is not None and (not _is_int(current) or current < 0):
                    _add(errors, f"{path}.metrics.{metric}", "must be null or a non-negative integer")
        if status == "running":
            unknown_nodes = sorted(set(node_ids) - set(graph_nodes))
            if unknown_nodes:
                _add(
                    errors,
                    f"{path}.node_ids",
                    f"running workflow contains unknown graph nodes: {', '.join(unknown_nodes)}",
                )
            if profile == "mission_write" and any(
                graph_nodes.get(node_id, {}).get("kind") != "mission" for node_id in node_ids
            ):
                _add(errors, f"{path}.tool_profile", "mission_write requires only mission nodes")
            if profile in {"code_review_readonly", "visual_review_readonly"}:
                review_types: set[Any] = set()
                for node_id in node_ids:
                    review = graph_nodes.get(node_id, {}).get("review")
                    review_types.add(review.get("type") if isinstance(review, dict) else None)
                allowed_reviews = (
                    {"visual"}
                    if profile == "visual_review_readonly"
                    else {"frontend_code", "backend_code"}
                )
                if not review_types or not review_types.issubset(allowed_reviews):
                    _add(errors, f"{path}.tool_profile", "does not match its review node types")
            if item["plan_revision"] != plan.get("revision"):
                _add(errors, f"{path}.plan_revision", "running workflow must match PLAN")
            if item["plan_digest_sha256"] != plan_digest(plan):
                _add(errors, f"{path}.plan_digest_sha256", "running workflow must match PLAN")
            raw_graph_state = run.get("graph_state")
            graph_state = raw_graph_state if isinstance(raw_graph_state, dict) else {}
            if item["graph_revision"] != graph_state.get("graph_revision"):
                _add(errors, f"{path}.graph_revision", "running workflow is stale")
            raw_integration = run.get("integration")
            integration = raw_integration if isinstance(raw_integration, dict) else {}
            if item["batch_base_sha"] != integration.get("batch_base_sha"):
                _add(errors, f"{path}.batch_base_sha", "running workflow must match RUN")
            for node_id in node_ids:
                attempt_id = attempt_ids.get(node_id)
                state = graph_state.get("node_states", {}).get(node_id, {})
                if state.get("phase") != "running" or state.get("last_attempt_id") != attempt_id:
                    _add(errors, f"{path}.attempt_ids.{node_id}", "must match the active running node attempt")
                elif (node_id, attempt_id) in active_attempts:
                    _add(errors, f"{path}.attempt_ids.{node_id}", "is already bound to another running workflow")
                else:
                    active_attempts.add((node_id, attempt_id))
                node = graph_nodes.get(node_id, {})
                raw_policy = node.get("runtime")
                policy = raw_policy if isinstance(raw_policy, dict) else {}
                raw_allowed = policy.get("allowed_providers")
                allowed_providers = raw_allowed if isinstance(raw_allowed, list) else []
                if provider not in allowed_providers:
                    _add(errors, f"{path}.provider", f"node {node_id} does not allow {provider}")
            if run.get("status") == "complete":
                _add(errors, path, "complete RUN cannot retain a running workflow")


def validate_run(plan: dict[str, Any], run: dict[str, Any]) -> list[str]:
    """Validate a plan-backed harness_run object and cross-plan consistency."""

    errors: list[str] = []
    run_keys = {
        "schema_version",
        "run_id",
        "plan",
        "status",
        "intent",
        "plan_readiness",
        "execution_authorized",
        "execution_authorization_source",
        "execution_authorization_scope",
        "authorizations",
        "runtime_capabilities",
        "observed",
        "integration",
        "mission_states",
        "task_states",
        "active_wave",
        "workers",
        "attempt_log",
    }
    schema_version = run.get("schema_version") if isinstance(run, dict) else None
    plan_declares_release = (
        plan.get("schema_version") in {3, 4} and "release" in plan
    )
    graph_run = plan.get("schema_version") == 4 and schema_version in {8, 9}
    if graph_run:
        run_keys.update({"graph_state", "review_workers"})
    if schema_version in {3, 4, 5, 6, 7, 8, 9}:
        run_keys.add("landing")
    if schema_version in {5, 6, 7, 8, 9}:
        run_keys.add("post_merge_cleanup")
    if schema_version in {7, 8, 9} and plan_declares_release:
        run_keys.add("deployments")
    if schema_version == 9:
        run_keys.update({"batch_gate_results", "final_gate_results", "ui_evidence"})
    if schema_version not in SUPPORTED_RUN_SCHEMA_VERSIONS:
        _add(errors, "run.schema_version", "must equal 2, 3, 4, 5, 6, 7, 8, or 9")
    if plan.get("schema_version") == 4 and schema_version not in {8, 9}:
        _add(errors, "run.schema_version", "must equal 8 or 9 for a schema v4 graph PLAN")
    elif schema_version == 8 and plan.get("schema_version") != 4:
        _add(errors, "run.schema_version", "schema v8 requires a schema v4 graph PLAN")
    elif (
        plan_declares_release
        and plan.get("schema_version") == 3
        and schema_version not in {7, 9}
    ):
        _add(
            errors,
            "run.schema_version",
            "must equal 7 or 9 when a schema v3 PLAN declares release",
        )
    optional_run_keys = {"deployments"} if schema_version in {7, 8, 9} else set()
    if graph_run:
        optional_run_keys.add("workflow_runs")
    if not _keys(errors, "run", run, run_keys, optional_run_keys):
        return sorted(errors)
    if not _nonempty_string(run["run_id"]):
        _add(errors, "run.run_id", "must be a non-empty string")
    if run["status"] not in {"draft", "ready", "running", "blocked", "complete"}:
        _add(errors, "run.status", "has an unsupported value")
    if run["intent"] not in {
        "plan-only",
        "plan-then-stop",
        "plan-then-execute",
        "execute-ready-plan",
    }:
        _add(errors, "run.intent", "has an unsupported value")
    if run["plan_readiness"] not in {"draft", "ready", "blocked"}:
        _add(errors, "run.plan_readiness", "has an unsupported value")
    if not isinstance(run["execution_authorized"], bool):
        _add(errors, "run.execution_authorized", "must be boolean")
    if run["execution_authorized"]:
        if not _nonempty_string(run["execution_authorization_source"]):
            _add(errors, "run.execution_authorization_source", "is required when authorized")
        _validate_authorization_scope(
            errors,
            "run.execution_authorization_scope",
            run["execution_authorization_scope"],
            action=False,
        )
        if isinstance(run["execution_authorization_scope"], dict) and run["execution_authorization_scope"].get("run_id") != run["run_id"]:
            _add(errors, "run.execution_authorization_scope.run_id", "must match run_id")
    else:
        _optional_string(
            errors, "run.execution_authorization_source", run["execution_authorization_source"]
        )
        if run["execution_authorization_scope"] is not None:
            _add(errors, "run.execution_authorization_scope", "must be null when unauthorized")

    if _keys(errors, "run.plan", run["plan"], {"id", "revision", "digest_sha256"}):
        if run["plan"]["id"] != plan.get("plan_id"):
            _add(errors, "run.plan.id", "does not match PLAN")
        if run["plan"]["revision"] != plan.get("revision"):
            _add(errors, "run.plan.revision", "does not match PLAN")
        digest = plan_digest(plan)
        if run["plan"]["digest_sha256"] != digest:
            _add(errors, "run.plan.digest_sha256", f"does not match semantic PLAN digest {digest}")

    authorization_keys = (
        AUTHORIZATION_KEYS_V8
        if schema_version in {8, 9}
        else AUTHORIZATION_KEYS
        if schema_version in {3, 4, 5, 6, 7, 8, 9}
        else AUTHORIZATION_KEYS_V2
    )
    authorizations = run["authorizations"]
    if not isinstance(authorizations, dict):
        _add(errors, "run.authorizations", "must be an object")
    else:
        missing = sorted(set(authorization_keys) - set(authorizations))
        unknown = sorted(set(authorizations) - set(authorization_keys))
        if missing:
            _add(errors, "run.authorizations", f"missing keys: {', '.join(missing)}")
        if unknown:
            _add(errors, "run.authorizations", f"unknown keys: {', '.join(unknown)}")
        for action in authorization_keys:
            if action not in authorizations:
                continue
            entry = authorizations[action]
            path = f"run.authorizations.{action}"
            if not _keys(errors, path, entry, {"authorized", "source"}, {"scope", "expires_when"}):
                continue
            if not isinstance(entry["authorized"], bool):
                _add(errors, f"{path}.authorized", "must be boolean")
            if entry["authorized"]:
                if not _nonempty_string(entry["source"]):
                    _add(errors, f"{path}.source", "is required when authorized")
                if "scope" not in entry or "expires_when" not in entry:
                    _add(errors, path, "authorized action requires scope and expires_when")
                else:
                    _validate_authorization_scope(
                        errors,
                        f"{path}.scope",
                        entry["scope"],
                        action=True,
                        action_name=action,
                        allow_future_pr=(schema_version in {6, 7, 8, 9}),
                    )
                    if isinstance(entry["scope"], dict) and entry["scope"].get("run_id") != run["run_id"]:
                        _add(errors, f"{path}.scope.run_id", "must match run_id")
                    if entry["expires_when"] not in EXPIRY_BOUNDARIES:
                        _add(
                            errors,
                            f"{path}.expires_when",
                            "must be wave_closed, run_complete, or explicit_revocation",
                        )
            else:
                if entry["source"] is not None:
                    _add(errors, f"{path}.source", "must be null when unauthorized")
                if "scope" in entry or "expires_when" in entry:
                    _add(errors, path, "unauthorized action must omit scope and expires_when")

    if schema_version in {3, 4, 5, 6, 7, 8, 9}:
        _validate_landing(errors, run["landing"], schema_version)
    if (
        schema_version in {4, 5, 6, 7, 8, 9}
        and isinstance(run["landing"], dict)
        and run["landing"].get("auto_merge_requested") is True
    ):
        pr_url = run["landing"].get("pr_url")
        mission_states = run.get("mission_states")
        if (
            not _nonempty_string(pr_url)
            or not isinstance(mission_states, dict)
            or not mission_states
            or any(
                not authorization_covers(
                    run,
                    "merge_pr",
                    mission_id,
                    f"pr:{pr_url}",
                    preserve_completed_run_expiry=(
                        run["landing"].get("merge_status") == "merged"
                    ),
                )
                for mission_id in mission_states
            )
        ):
            _add(
                errors,
                "run.landing",
                "auto_merge_requested requires matching merge_pr authorization for the exact PR",
            )
        authorizations = run.get("authorizations", {})
        merge_entry = authorizations.get("merge_pr", {}) if isinstance(authorizations, dict) else {}
        merge_scope = merge_entry.get("scope", {}) if isinstance(merge_entry, dict) else {}
        merge_targets = merge_scope.get("targets", []) if isinstance(merge_scope, dict) else []
        future_targets = {
            target
            for target in merge_targets
            if isinstance(target, str) and FUTURE_PR_TARGET_RE.fullmatch(target)
        }
        if future_targets and _landing_future_pr_target(run["landing"]) not in future_targets:
            _add(
                errors,
                "run.landing",
                "auto_merge_requested exact PR does not match its authorized future PR binding",
            )
    if schema_version in {5, 6, 7, 8, 9}:
        _validate_post_merge_cleanup(errors, run["post_merge_cleanup"], run)
    if schema_version in {7, 8, 9} and "deployments" in run:
        _validate_deployments(errors, run["deployments"], run, plan)

    runtime_keys = {
        "worker_runtime",
        "workspace_mode",
        "completion_channel",
        "max_parallel_workers",
        "platform_lifecycle",
    }
    if schema_version in {6, 7, 8, 9}:
        runtime_keys.add("runtime_adapter")
    runtime = run["runtime_capabilities"]
    if _keys(
        errors,
        "run.runtime_capabilities",
        runtime,
        runtime_keys,
        {"nested_subagents", "permission_boundary"},
    ):
        if runtime["worker_runtime"] not in {"parent", "subagent", "app_task"}:
            _add(errors, "run.runtime_capabilities.worker_runtime", "has an unsupported value")
        if runtime["workspace_mode"] not in {
            "shared_checkout",
            "parent_managed_worktree",
            "app_managed_worktree",
        }:
            _add(errors, "run.runtime_capabilities.workspace_mode", "has an unsupported value")
        if runtime["completion_channel"] not in {
            "agent_result",
            "thread_poll",
            "report_file",
            "user_relay",
        }:
            _add(errors, "run.runtime_capabilities.completion_channel", "has an unsupported value")
        if not _is_int(runtime["max_parallel_workers"]) or not 1 <= runtime["max_parallel_workers"] <= 3:
            _add(errors, "run.runtime_capabilities.max_parallel_workers", "must be 1..3")
        adapter = runtime.get("runtime_adapter")
        adapter_path = "run.runtime_capabilities.runtime_adapter"
        if schema_version in {6, 7, 8, 9} and adapter is None:
            _add(errors, adapter_path, "must be an object")
        elif adapter is not None and _keys(
            errors,
            adapter_path,
            adapter,
            {
                "provider",
                "available_drivers",
                "detection_source",
            },
        ):
            provider = adapter["provider"]
            provider_valid = isinstance(provider, str) and provider in RUNTIME_PROVIDERS
            if not provider_valid:
                _add(errors, f"{adapter_path}.provider", "has an unsupported value")
            drivers = _strings(
                errors,
                f"{adapter_path}.available_drivers",
                adapter["available_drivers"],
                nonempty=True,
            )
            unknown_drivers = sorted(set(drivers) - RUNTIME_DRIVERS)
            if unknown_drivers:
                _add(
                    errors,
                    f"{adapter_path}.available_drivers",
                    f"unsupported drivers: {', '.join(unknown_drivers)}",
                )
            allowed_drivers = set(RUNTIME_DRIVER_PRIORITY.get(provider, ())) if provider_valid else set()
            incompatible_drivers = sorted(set(drivers) - allowed_drivers)
            if provider_valid and incompatible_drivers:
                _add(
                    errors,
                    f"{adapter_path}.available_drivers",
                    f"drivers do not match provider: {', '.join(incompatible_drivers)}",
                )
            if "sequential_parent" not in drivers:
                _add(
                    errors,
                    f"{adapter_path}.available_drivers",
                    "must include sequential_parent as the safe fallback",
                )
            detection_source = adapter["detection_source"]
            if not isinstance(detection_source, str) or detection_source not in RUNTIME_DETECTION_SOURCES:
                _add(errors, f"{adapter_path}.detection_source", "has an unsupported value")

            selected_driver = route_runtime_driver(runtime)
            if selected_driver == "app_threads" and (
                provider != "codex"
                or runtime["worker_runtime"] != "app_task"
                or runtime["workspace_mode"] != "app_managed_worktree"
                or runtime["completion_channel"] != "thread_poll"
            ):
                _add(errors, adapter_path, "app_threads requires codex app_task/app_managed_worktree/thread_poll")
            elif selected_driver == "dynamic_workflow" and (
                provider != "claude_code"
                or runtime["worker_runtime"] != "subagent"
                or runtime["workspace_mode"] != "parent_managed_worktree"
                or runtime["completion_channel"] != "agent_result"
            ):
                _add(
                    errors,
                    adapter_path,
                    "dynamic_workflow requires claude_code subagent/parent_managed_worktree/agent_result",
                )
            elif selected_driver == "subagents" and (
                runtime["worker_runtime"] != "subagent"
                or runtime["workspace_mode"] not in {"shared_checkout", "parent_managed_worktree"}
                or runtime["completion_channel"] not in {"agent_result", "report_file"}
            ):
                _add(errors, adapter_path, "subagents requires a supported subagent workspace and result channel")
            elif selected_driver == "sequential_parent" and (
                runtime["worker_runtime"] != "parent"
                or runtime["workspace_mode"] != "shared_checkout"
                or runtime["completion_channel"] != "agent_result"
            ):
                _add(errors, adapter_path, "sequential_parent requires parent/shared_checkout/agent_result")
            if selected_driver == "dynamic_workflow" and runtime.get("nested_subagents") is not None:
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents",
                    "must be omitted for flat dynamic-workflow orchestration",
                )
        permission = runtime.get("permission_boundary")
        if permission is not None and _keys(
            errors,
            "run.runtime_capabilities.permission_boundary",
            permission,
            {
                "selected_mode",
                "profile_name",
                "approval_policy",
                "filesystem_scope",
                "network_scope",
                "local_binding",
                "worker_inheritance",
                "status",
            },
        ):
            permission_path = "run.runtime_capabilities.permission_boundary"
            if permission["selected_mode"] not in PERMISSION_SELECTED_MODES:
                _add(errors, f"{permission_path}.selected_mode", "has an unsupported value")
            profile_name = permission["profile_name"]
            if permission["selected_mode"] == "named_profile":
                if not _nonempty_string(profile_name):
                    _add(errors, f"{permission_path}.profile_name", "is required for named_profile")
            elif profile_name is not None:
                _add(errors, f"{permission_path}.profile_name", "must be null unless selected_mode is named_profile")
            if permission["approval_policy"] not in PERMISSION_APPROVAL_POLICIES:
                _add(errors, f"{permission_path}.approval_policy", "has an unsupported value")
            if permission["filesystem_scope"] not in PERMISSION_FILESYSTEM_SCOPES:
                _add(errors, f"{permission_path}.filesystem_scope", "has an unsupported value")
            if permission["network_scope"] not in PERMISSION_NETWORK_SCOPES:
                _add(errors, f"{permission_path}.network_scope", "has an unsupported value")
            if permission["local_binding"] not in PERMISSION_LOCAL_BINDINGS:
                _add(errors, f"{permission_path}.local_binding", "has an unsupported value")
            if permission["worker_inheritance"] not in PERMISSION_INHERITANCE:
                _add(errors, f"{permission_path}.worker_inheritance", "has an unsupported value")
            if permission["status"] not in PERMISSION_STATUSES:
                _add(errors, f"{permission_path}.status", "has an unsupported value")
            if permission["status"] == "ready" and "unknown" in {
                permission["selected_mode"],
                permission["approval_policy"],
                permission["filesystem_scope"],
                permission["network_scope"],
                permission["local_binding"],
                permission["worker_inheritance"],
            }:
                _add(errors, permission_path, "cannot be ready while a boundary field is unknown")
            if permission["selected_mode"] == "full_access" and (
                permission["approval_policy"] != "never"
                or permission["filesystem_scope"] != "unrestricted"
                or permission["network_scope"] != "open"
                or permission["local_binding"] != "allowed"
            ):
                _add(
                    errors,
                    permission_path,
                    "full_access requires never, unrestricted filesystem, open network, and allowed local binding",
                )
        nested = runtime.get("nested_subagents")
        if nested is not None and _keys(
            errors,
            "run.runtime_capabilities.nested_subagents",
            nested,
            {
                "available",
                "max_depth",
                "max_children_per_worker",
                "allowed_roles",
                "write_policy",
                "completion_channel",
            },
        ):
            if not isinstance(nested["available"], bool):
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents.available",
                    "must be boolean",
                )
            if nested["max_depth"] != 1:
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents.max_depth",
                    "must equal 1",
                )
            if (
                not _is_int(nested["max_children_per_worker"])
                or not 1 <= nested["max_children_per_worker"] <= 3
            ):
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents.max_children_per_worker",
                    "must be 1..3",
                )
            roles = _strings(
                errors,
                "run.runtime_capabilities.nested_subagents.allowed_roles",
                nested["allowed_roles"],
                nonempty=True,
            )
            unknown_roles = sorted(set(roles) - NESTED_SUBAGENT_ROLES)
            if unknown_roles:
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents.allowed_roles",
                    f"unsupported roles: {', '.join(unknown_roles)}",
                )
            if nested["write_policy"] != "read_only":
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents.write_policy",
                    "must equal read_only",
                )
            if nested["completion_channel"] != "agent_result":
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents.completion_channel",
                    "must equal agent_result",
                )
        lifecycle = runtime["platform_lifecycle"]
        if _keys(
            errors,
            "run.runtime_capabilities.platform_lifecycle",
            lifecycle,
            {"owner", "automatic_retention_cleanup_possible", "durable_branch_required_before_unique_work"},
        ):
            if lifecycle["owner"] not in {"parent", "app"}:
                _add(errors, "run.runtime_capabilities.platform_lifecycle.owner", "must be parent or app")
            for key in ("automatic_retention_cleanup_possible", "durable_branch_required_before_unique_work"):
                if not isinstance(lifecycle[key], bool):
                    _add(errors, f"run.runtime_capabilities.platform_lifecycle.{key}", "must be boolean")

    observed = run["observed"]
    if _keys(errors, "run.observed", observed, {"captured_at", "git", "runtime"}):
        _optional_string(errors, "run.observed.captured_at", observed["captured_at"])
        git = observed["git"]
        observed_git_keys = {
            "parent_branch",
            "parent_head_sha",
            "parent_dirty",
            "worktrees",
        }
        if schema_version in {5, 6, 7, 8, 9}:
            observed_git_keys.add("parent_worktree_path")
        if _keys(errors, "run.observed.git", git, observed_git_keys):
            if schema_version in {5, 6, 7, 8, 9}:
                _optional_string(
                    errors,
                    "run.observed.git.parent_worktree_path",
                    git["parent_worktree_path"],
                )
            _optional_string(errors, "run.observed.git.parent_branch", git["parent_branch"])
            _optional_sha(errors, "run.observed.git.parent_head_sha", git["parent_head_sha"])
            if git["parent_dirty"] is not None and not isinstance(git["parent_dirty"], bool):
                _add(errors, "run.observed.git.parent_dirty", "must be null or boolean")
            if not isinstance(git["worktrees"], list):
                _add(errors, "run.observed.git.worktrees", "must be a list")
            else:
                for index, worktree in enumerate(git["worktrees"]):
                    path = f"run.observed.git.worktrees[{index}]"
                    if _keys(errors, path, worktree, {"path", "branch_ref", "head_sha", "managed_by", "dirty"}):
                        if not _nonempty_string(worktree["path"]):
                            _add(errors, f"{path}.path", "must be a non-empty string")
                        _optional_string(errors, f"{path}.branch_ref", worktree["branch_ref"])
                        _optional_sha(errors, f"{path}.head_sha", worktree["head_sha"])
                        if worktree["managed_by"] not in {"parent", "app"}:
                            _add(errors, f"{path}.managed_by", "must be parent or app")
                        if not isinstance(worktree["dirty"], bool):
                            _add(errors, f"{path}.dirty", "must be boolean")
        observed_runtime = observed["runtime"]
        if _keys(errors, "run.observed.runtime", observed_runtime, {"available_worker_slots", "isolation_capacity", "completion_channel_available"}):
            for key in ("available_worker_slots", "isolation_capacity"):
                if not _is_int(observed_runtime[key]) or observed_runtime[key] < 0:
                    _add(errors, f"run.observed.runtime.{key}", "must be a non-negative integer")
            if not isinstance(observed_runtime["completion_channel_available"], bool):
                _add(errors, "run.observed.runtime.completion_channel_available", "must be boolean")

    integration = run["integration"]
    if _keys(errors, "run.integration", integration, {"branch", "batch_base_sha", "integration_head_sha"}):
        _optional_string(errors, "run.integration.branch", integration["branch"])
        _optional_sha(errors, "run.integration.batch_base_sha", integration["batch_base_sha"])
        _optional_sha(errors, "run.integration.integration_head_sha", integration["integration_head_sha"])
        if (
            schema_version in {3, 4, 5, 6, 7, 8, 9}
            and isinstance(run["landing"], dict)
            and run["landing"].get("mode") == "pull_request"
            and _nonempty_string(run["landing"].get("head_branch"))
            and (
                not _nonempty_string(integration["branch"])
                or integration["branch"].removeprefix("refs/heads/")
                != run["landing"]["head_branch"].removeprefix("refs/heads/")
            )
        ):
            _add(
                errors,
                "run.landing",
                "pull_request mode requires integration.branch to match head_branch",
            )
        if (
            schema_version in {3, 4, 5, 6, 7, 8, 9}
            and isinstance(run["landing"], dict)
            and (
                run["landing"].get("checks_status") == "PASS"
                or run["landing"].get("review_status") == "PASS"
            )
            and run["landing"].get("pr_head_sha") != integration["integration_head_sha"]
        ):
            _add(
                errors,
                "run.landing",
                "PASS landing evidence requires the current PR head to match integration_head_sha",
            )

    mission_ids = {mission["id"] for mission in plan.get("missions", []) if isinstance(mission, dict) and "id" in mission}
    task_ids = {
        task["id"]
        for mission in plan.get("missions", [])
        if isinstance(mission, dict)
        for task in mission.get("tasks", [])
        if isinstance(task, dict) and "id" in task
    }
    mission_states = run["mission_states"]
    mission_state_keys = {
        "phase",
        "lease_id",
        "lease_plan_revision",
        "lease_plan_digest_sha256",
        "worker_id",
        "base_sha",
        "head_sha",
        "integration_gate",
        "integrated_sha",
        "blockers",
        "report_path",
    }
    if not isinstance(mission_states, dict):
        _add(errors, "run.mission_states", "must be an object")
    else:
        if set(mission_states) != mission_ids:
            _add(errors, "run.mission_states", "keys must exactly match PLAN missions")
        for mission_id, state in mission_states.items():
            path = f"run.mission_states.{mission_id}"
            if not _keys(errors, path, state, mission_state_keys):
                continue
            if state["phase"] not in MISSION_PHASES:
                _add(errors, f"{path}.phase", "has an unsupported value")
            for key in ("lease_id", "worker_id", "report_path"):
                _optional_string(errors, f"{path}.{key}", state[key])
            if state["lease_plan_revision"] is not None and (
                not _is_int(state["lease_plan_revision"]) or state["lease_plan_revision"] < 1
            ):
                _add(errors, f"{path}.lease_plan_revision", "must be null or positive integer")
            for key in ("lease_plan_digest_sha256", "base_sha", "head_sha", "integrated_sha"):
                _optional_sha(errors, f"{path}.{key}", state[key])
            if state["integration_gate"] not in GATE_VALUES:
                _add(errors, f"{path}.integration_gate", "has an unsupported gate value")
            _strings(errors, f"{path}.blockers", state["blockers"])
            leased = state["phase"] in {"leased", "worker_running", "worker_passed", "integrating"}
            if leased and any(
                state[key] is None
                for key in ("lease_id", "lease_plan_revision", "lease_plan_digest_sha256", "worker_id", "base_sha")
            ):
                _add(errors, path, "leased/running mission is missing lease bindings")
            if state["phase"] == "integrated" and (
                state["integration_gate"] != "PASS" or state["integrated_sha"] is None
            ):
                _add(errors, path, "integrated mission requires PASS gate and integrated_sha")

    if graph_run:
        _validate_graph_state(errors, plan, run)
        _validate_workflow_runs(errors, plan, run)

    task_states = run["task_states"]
    task_state_keys = {
        "phase",
        "attempts",
        "commit_sha",
        "verifier_status",
        "blockers",
        "refinement_request",
    }
    if not isinstance(task_states, dict):
        _add(errors, "run.task_states", "must be an object")
    else:
        if set(task_states) != task_ids:
            _add(errors, "run.task_states", "keys must exactly match PLAN tasks")
        for task_id, state in task_states.items():
            path = f"run.task_states.{task_id}"
            if not _keys(errors, path, state, task_state_keys):
                continue
            if state["phase"] not in TASK_PHASES:
                _add(errors, f"{path}.phase", "has an unsupported value")
            if not _is_int(state["attempts"]) or state["attempts"] < 0:
                _add(errors, f"{path}.attempts", "must be a non-negative integer")
            _optional_sha(errors, f"{path}.commit_sha", state["commit_sha"])
            if state["verifier_status"] not in GATE_VALUES:
                _add(errors, f"{path}.verifier_status", "has an unsupported gate value")
            _strings(errors, f"{path}.blockers", state["blockers"])
            if state["refinement_request"] is not None and not isinstance(
                state["refinement_request"], dict
            ):
                _add(errors, f"{path}.refinement_request", "must be null or an object")

    wave = run["active_wave"]
    wave_keys = {
        "wave_id",
        "status",
        "plan_revision",
        "plan_digest_sha256",
        "batch_base_sha",
        "selected_missions",
        "deferred_missions",
        "conflict_edges",
    }
    if _keys(errors, "run.active_wave", wave, wave_keys):
        _optional_string(errors, "run.active_wave.wave_id", wave["wave_id"])
        if wave["status"] not in {"idle", "proposed", "active", "closed", "superseded"}:
            _add(errors, "run.active_wave.status", "has an unsupported value")
        if not _is_int(wave["plan_revision"]) or wave["plan_revision"] < 1:
            _add(errors, "run.active_wave.plan_revision", "must be positive integer")
        _optional_sha(errors, "run.active_wave.plan_digest_sha256", wave["plan_digest_sha256"])
        _optional_sha(errors, "run.active_wave.batch_base_sha", wave["batch_base_sha"])
        for mission_id in _strings(errors, "run.active_wave.selected_missions", wave["selected_missions"]):
            if mission_id not in mission_ids:
                _add(errors, "run.active_wave.selected_missions", f"unknown mission {mission_id!r}")
        if not isinstance(wave["deferred_missions"], list):
            _add(errors, "run.active_wave.deferred_missions", "must be a list")
        else:
            for index, item in enumerate(wave["deferred_missions"]):
                path = f"run.active_wave.deferred_missions[{index}]"
                if _keys(errors, path, item, {"mission_id", "reason_codes", "conflicts_with"}):
                    if item["mission_id"] not in mission_ids:
                        _add(errors, f"{path}.mission_id", "is unknown")
                    _strings(errors, f"{path}.reason_codes", item["reason_codes"], nonempty=True)
                    _strings(errors, f"{path}.conflicts_with", item["conflicts_with"])
        if not isinstance(wave["conflict_edges"], list):
            _add(errors, "run.active_wave.conflict_edges", "must be a list")
        else:
            for index, edge in enumerate(wave["conflict_edges"]):
                path = f"run.active_wave.conflict_edges[{index}]"
                if _keys(errors, path, edge, {"left", "right", "reason_codes"}):
                    if edge["left"] not in mission_ids or edge["right"] not in mission_ids:
                        _add(errors, path, "references an unknown mission")
                    if edge["left"] >= edge["right"]:
                        _add(errors, path, "endpoints must be lexical left < right")
                    _strings(errors, f"{path}.reason_codes", edge["reason_codes"], nonempty=True)

    worker_ids: set[str] = set()
    workers = run["workers"]
    graph_nodes_by_mission = {
        node.get("ref"): node
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict) and node.get("kind") == "mission"
    } if plan.get("schema_version") == 4 and isinstance(plan.get("graph"), dict) else {}
    worker_keys = {
        "worker_id",
        "mission_id",
        "lease_id",
        "plan_revision",
        "plan_digest_sha256",
        "batch_base_sha",
        "worker_runtime",
        "workspace_mode",
        "completion_channel",
        "task_thread_id",
        "worktree_path",
        "branch_ref",
        "report_path",
        "phase",
        "worker_head_sha",
    }
    if not isinstance(workers, list):
        _add(errors, "run.workers", "must be a list")
    else:
        for index, worker in enumerate(workers):
            path = f"run.workers[{index}]"
            if not _keys(
                errors,
                path,
                worker,
                worker_keys,
                {"nested_subagent_policy", "runtime_binding"},
            ):
                continue
            for key in ("worker_id", "mission_id", "lease_id", "plan_digest_sha256", "batch_base_sha"):
                if not _nonempty_string(worker[key]):
                    _add(errors, f"{path}.{key}", "must be a non-empty string")
            if worker["worker_id"] in worker_ids:
                _add(errors, f"{path}.worker_id", "must be unique")
            worker_ids.add(worker["worker_id"])
            if worker["mission_id"] not in mission_ids:
                _add(errors, f"{path}.mission_id", "is unknown")
            if not _is_int(worker["plan_revision"]) or worker["plan_revision"] < 1:
                _add(errors, f"{path}.plan_revision", "must be positive integer")
            _optional_sha(errors, f"{path}.plan_digest_sha256", worker["plan_digest_sha256"])
            _optional_sha(errors, f"{path}.batch_base_sha", worker["batch_base_sha"])
            _optional_sha(errors, f"{path}.worker_head_sha", worker["worker_head_sha"])
            if worker["worker_runtime"] not in {"parent", "subagent", "app_task"}:
                _add(errors, f"{path}.worker_runtime", "has an unsupported value")
            if worker["workspace_mode"] not in {"shared_checkout", "parent_managed_worktree", "app_managed_worktree"}:
                _add(errors, f"{path}.workspace_mode", "has an unsupported value")
            if worker["completion_channel"] not in {"agent_result", "thread_poll", "report_file", "user_relay"}:
                _add(errors, f"{path}.completion_channel", "has an unsupported value")
            for key in ("task_thread_id", "worktree_path", "branch_ref", "report_path"):
                _optional_string(errors, f"{path}.{key}", worker[key])
            if worker["phase"] not in WORKER_PHASES:
                _add(errors, f"{path}.phase", "has an unsupported value")
            runtime_binding = worker.get("runtime_binding")
            if graph_run and worker["mission_id"] in graph_nodes_by_mission and runtime_binding is None:
                _add(
                    errors,
                    f"{path}.runtime_binding",
                    "is required for a PLAN-v4 graph worker",
                )
            if runtime_binding is not None and _keys(
                errors,
                f"{path}.runtime_binding",
                runtime_binding,
                {
                    "provider",
                    "driver",
                    "source",
                    "model",
                    "reasoning_effort",
                    "option_source",
                },
            ):
                if runtime_binding["provider"] not in RUNTIME_PROVIDERS:
                    _add(errors, f"{path}.runtime_binding.provider", "has an unsupported value")
                if not _nonempty_string(runtime_binding["driver"]):
                    _add(errors, f"{path}.runtime_binding.driver", "must be a non-empty string")
                if runtime_binding["source"] != "host":
                    _add(errors, f"{path}.runtime_binding.source", "has an unsupported value")
                if runtime_binding["option_source"] not in {
                    "plan_provider_options",
                    "provider_default",
                }:
                    _add(errors, f"{path}.runtime_binding.option_source", "has an unsupported value")
                model = runtime_binding["model"]
                if model is not None and not is_safe_model_token(model):
                    _add(errors, f"{path}.runtime_binding.model", "must be null or a safe model token")
                effort = runtime_binding["reasoning_effort"]
                if effort is not None and effort not in RUNTIME_REASONING_EFFORTS:
                    _add(
                        errors,
                        f"{path}.runtime_binding.reasoning_effort",
                        "must be null or a supported reasoning effort",
                    )
                if runtime_binding["provider"] not in {"codex", "claude_code"} and effort is not None:
                    _add(
                        errors,
                        f"{path}.runtime_binding.reasoning_effort",
                        "must be null unless the provider supports selectable effort",
                    )
                graph_node = graph_nodes_by_mission.get(worker["mission_id"])
                policy = graph_node.get("runtime") if isinstance(graph_node, dict) else None
                if isinstance(policy, dict):
                    provider = runtime_binding["provider"]
                    if provider not in policy.get("allowed_providers", []):
                        _add(
                            errors,
                            f"{path}.runtime_binding.provider",
                            "must be allowed by the matching PLAN node",
                        )
                    expected_options = resolve_runtime_options(policy, provider)
                    if runtime_binding["model"] != expected_options["model"]:
                        _add(
                            errors,
                            f"{path}.runtime_binding.model",
                            "must match the matching PLAN provider option",
                        )
                    if (
                        runtime_binding["reasoning_effort"]
                        != expected_options["reasoning_effort"]
                    ):
                        _add(
                            errors,
                            f"{path}.runtime_binding.reasoning_effort",
                            "must match the matching PLAN provider option",
                        )
                    if runtime_binding["option_source"] != expected_options["option_source"]:
                        _add(
                            errors,
                            f"{path}.runtime_binding.option_source",
                            "must identify the matching PLAN option source",
                        )
            if worker["completion_channel"] == "report_file" and not _nonempty_string(worker["report_path"]):
                _add(errors, f"{path}.report_path", "is required for report_file")
            nested_policy = worker.get("nested_subagent_policy")
            if (
                schema_version in {6, 7, 8, 9}
                and isinstance(runtime, dict)
                and route_runtime_driver(runtime) == "dynamic_workflow"
                and nested_policy is not None
            ):
                _add(
                    errors,
                    f"{path}.nested_subagent_policy",
                    "must be omitted for flat dynamic-workflow orchestration",
                )
            if (
                worker["worker_runtime"] == "app_task"
                and isinstance(runtime, dict)
                and "nested_subagents" in runtime
                and nested_policy is None
            ):
                _add(
                    errors,
                    f"{path}.nested_subagent_policy",
                    "is required for app_task workers when runtime nested_subagents is recorded",
                )
            if nested_policy is not None and _keys(
                errors,
                f"{path}.nested_subagent_policy",
                nested_policy,
                {
                    "enabled",
                    "max_children",
                    "allowed_roles",
                    "write_policy",
                    "completion_channel",
                },
            ):
                if not isinstance(nested_policy["enabled"], bool):
                    _add(
                        errors,
                        f"{path}.nested_subagent_policy.enabled",
                        "must be boolean",
                    )
                if nested_policy["write_policy"] != "read_only":
                    _add(
                        errors,
                        f"{path}.nested_subagent_policy.write_policy",
                        "must equal read_only",
                    )
                if nested_policy["completion_channel"] != "agent_result":
                    _add(
                        errors,
                        f"{path}.nested_subagent_policy.completion_channel",
                        "must equal agent_result",
                    )
                policy_roles = _strings(
                    errors,
                    f"{path}.nested_subagent_policy.allowed_roles",
                    nested_policy["allowed_roles"],
                    nonempty=bool(nested_policy["enabled"]),
                )
                runtime_nested = (
                    runtime.get("nested_subagents")
                    if isinstance(runtime, dict)
                    else None
                )
                if nested_policy["enabled"]:
                    if worker["worker_runtime"] != "app_task":
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.enabled",
                            "may be true only for app_task workers",
                        )
                    if worker["workspace_mode"] != "app_managed_worktree":
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.enabled",
                            "requires an app_managed_worktree",
                        )
                    if not isinstance(runtime_nested, dict) or runtime_nested.get("available") is not True:
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.enabled",
                            "requires an available runtime nested-subagent capability",
                        )
                    runtime_limit = (
                        runtime_nested.get("max_children_per_worker")
                        if isinstance(runtime_nested, dict)
                        else None
                    )
                    if (
                        not _is_int(nested_policy["max_children"])
                        or not 1 <= nested_policy["max_children"] <= 3
                        or (_is_int(runtime_limit) and nested_policy["max_children"] > runtime_limit)
                    ):
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.max_children",
                            "must be 1..3 and not exceed the runtime limit",
                        )
                    runtime_roles = (
                        set(runtime_nested.get("allowed_roles", []))
                        if isinstance(runtime_nested, dict)
                        else set()
                    )
                    if set(policy_roles) - runtime_roles:
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.allowed_roles",
                            "must be a subset of runtime allowed_roles",
                        )
                    if not authorization_covers(
                        run,
                        "spawn_subagents",
                        worker["mission_id"],
                        f"worker:{worker['worker_id']}",
                    ):
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.enabled",
                            "requires matching spawn_subagents authorization",
                        )
                else:
                    if nested_policy["max_children"] != 0:
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.max_children",
                            "must equal 0 when disabled",
                        )
                    if policy_roles:
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.allowed_roles",
                            "must be empty when disabled",
                        )

    if graph_run:
        review_workers = run["review_workers"]
        review_nodes = {
            node.get("id"): node
            for node in plan.get("graph", {}).get("nodes", [])
            if isinstance(node, dict)
            and node.get("kind") == "verifier"
            and node.get("executor") == "runtime_worker"
        }
        review_worker_keys = {
            "worker_id",
            "node_id",
            "attempt_id",
            "plan_revision",
            "plan_digest_sha256",
            "graph_revision",
            "reviewed_sha",
            "review_path",
            "worker_runtime",
            "completion_channel",
            "runtime_binding",
            "task_thread_id",
            "report_path",
            "phase",
        }
        if not isinstance(review_workers, list):
            _add(errors, "run.review_workers", "must be a list")
        else:
            for index, worker in enumerate(review_workers):
                path = f"run.review_workers[{index}]"
                if not _keys(errors, path, worker, review_worker_keys):
                    continue
                for key in (
                    "worker_id",
                    "node_id",
                    "attempt_id",
                    "plan_digest_sha256",
                    "reviewed_sha",
                    "review_path",
                ):
                    if not _nonempty_string(worker[key]):
                        _add(errors, f"{path}.{key}", "must be a non-empty string")
                if worker["worker_id"] in worker_ids:
                    _add(errors, f"{path}.worker_id", "must be unique across all workers")
                worker_ids.add(worker["worker_id"])
                node = review_nodes.get(worker["node_id"])
                if node is None:
                    _add(errors, f"{path}.node_id", "must reference a runtime-worker verifier")
                if not _is_int(worker["plan_revision"]) or worker["plan_revision"] < 1:
                    _add(errors, f"{path}.plan_revision", "must be a positive integer")
                if worker["plan_revision"] != plan.get("revision"):
                    _add(errors, f"{path}.plan_revision", "must match the current PLAN")
                _optional_sha(errors, f"{path}.plan_digest_sha256", worker["plan_digest_sha256"])
                if worker["plan_digest_sha256"] != plan_digest(plan):
                    _add(errors, f"{path}.plan_digest_sha256", "must match the current PLAN")
                if worker["graph_revision"] != run["graph_state"]["graph_revision"]:
                    _add(errors, f"{path}.graph_revision", "must match the current graph revision")
                _optional_sha(errors, f"{path}.reviewed_sha", worker["reviewed_sha"])
                current_reviewable_shas = {
                    sha
                    for sha in (
                        run.get("integration", {}).get("integration_head_sha"),
                        run.get("landing", {}).get("pr_head_sha"),
                        *(
                            state.get("integrated_sha")
                            for state in run.get("mission_states", {}).values()
                            if isinstance(state, dict)
                        ),
                    )
                    if is_full_sha(sha)
                }
                if worker["reviewed_sha"] not in current_reviewable_shas:
                    _add(errors, f"{path}.reviewed_sha", "must identify a current integrated or PR head")
                if worker["worker_runtime"] not in {"parent", "subagent", "app_task"}:
                    _add(errors, f"{path}.worker_runtime", "has an unsupported value")
                if worker["completion_channel"] not in {
                    "agent_result",
                    "thread_poll",
                    "report_file",
                    "user_relay",
                }:
                    _add(errors, f"{path}.completion_channel", "has an unsupported value")
                for key in ("task_thread_id", "report_path"):
                    _optional_string(errors, f"{path}.{key}", worker[key])
                if worker["completion_channel"] == "report_file" and not _nonempty_string(
                    worker["report_path"]
                ):
                    _add(errors, f"{path}.report_path", "is required for report_file")
                if worker["phase"] not in WORKER_PHASES:
                    _add(errors, f"{path}.phase", "has an unsupported value")
                state = run["graph_state"]["node_states"].get(worker["node_id"], {})
                if worker["phase"] in {"worker_running", "worker_passed"} and (
                    state.get("bound_worker_id") != worker["worker_id"]
                    or state.get("last_attempt_id") != worker["attempt_id"]
                ):
                    _add(errors, path, "active review worker must match the bound graph attempt")
                binding = worker["runtime_binding"]
                if _keys(
                    errors,
                    f"{path}.runtime_binding",
                    binding,
                    {
                        "provider",
                        "driver",
                        "source",
                        "model",
                        "reasoning_effort",
                        "option_source",
                    },
                ):
                    provider = binding["provider"]
                    policy = node.get("runtime") if isinstance(node, dict) else None
                    if provider not in RUNTIME_PROVIDERS:
                        _add(errors, f"{path}.runtime_binding.provider", "has an unsupported value")
                    if not isinstance(policy, dict) or provider not in policy.get(
                        "allowed_providers", []
                    ):
                        _add(
                            errors,
                            f"{path}.runtime_binding.provider",
                            "must be allowed by the matching review node",
                        )
                    if not _nonempty_string(binding["driver"]):
                        _add(errors, f"{path}.runtime_binding.driver", "must be a non-empty string")
                    if binding["source"] != "host":
                        _add(errors, f"{path}.runtime_binding.source", "has an unsupported value")
                    expected_options = (
                        resolve_runtime_options(policy, provider)
                        if isinstance(policy, dict)
                        else {
                            "model": None,
                            "reasoning_effort": None,
                            "option_source": "provider_default",
                        }
                    )
                    if binding["model"] is not None and not is_safe_model_token(binding["model"]):
                        _add(errors, f"{path}.runtime_binding.model", "must be null or a safe model token")
                    if binding["model"] != expected_options["model"]:
                        _add(errors, f"{path}.runtime_binding.model", "must match the review node")
                    if binding["reasoning_effort"] != expected_options["reasoning_effort"]:
                        _add(
                            errors,
                            f"{path}.runtime_binding.reasoning_effort",
                            "must match the review node",
                        )
                    if binding["option_source"] != expected_options["option_source"]:
                        _add(
                            errors,
                            f"{path}.runtime_binding.option_source",
                            "must identify the matching PLAN option source",
                        )

    if not isinstance(run["attempt_log"], list):
        _add(errors, "run.attempt_log", "must be a list")
    else:
        attempt_keys = {"attempt_id", "mission_id", "task_id", "lease_id", "kind", "result", "evidence"}
        for index, attempt in enumerate(run["attempt_log"]):
            path = f"run.attempt_log[{index}]"
            if not _keys(errors, path, attempt, attempt_keys):
                continue
            for key in ("attempt_id", "mission_id", "kind", "result"):
                if not _nonempty_string(attempt[key]):
                    _add(errors, f"{path}.{key}", "must be a non-empty string")
            if attempt["mission_id"] not in mission_ids:
                _add(errors, f"{path}.mission_id", "is unknown")
            for key in ("task_id", "lease_id"):
                _optional_string(errors, f"{path}.{key}", attempt[key])
            if attempt["task_id"] is not None and attempt["task_id"] not in task_ids:
                _add(errors, f"{path}.task_id", "is unknown")
            _strings(errors, f"{path}.evidence", attempt["evidence"])

    if schema_version == 9:
        _validate_gate_results(
            errors,
            plan,
            run,
            plan_key="batch_verifiers",
            run_key="batch_gate_results",
            label="batch gate",
        )
        _validate_gate_results(
            errors,
            plan,
            run,
            plan_key="final_gates",
            run_key="final_gate_results",
            label="final gate",
        )
        _validate_ui_evidence(errors, plan, run)

    if schema_version in {8, 9} and run.get("status") == "complete":
        if run.get("intent") not in {"plan-then-execute", "execute-ready-plan"}:
            _add(errors, "run.intent", "complete run requires execution intent")
        if run.get("plan_readiness") != "ready":
            _add(errors, "run.plan_readiness", "complete run requires ready plan")
        plan_sources = plan.get("sources")
        if isinstance(plan_sources, list) and any(
            source.get("status") not in {"frozen", "delta accepted"}
            for source in plan_sources
            if isinstance(source, dict)
        ):
            _add(
                errors,
                "plan.sources",
                "complete run requires every source to be frozen or delta accepted",
            )
        if not isinstance(integration, dict) or integration.get("integration_head_sha") is None:
            _add(
                errors,
                "run.integration.integration_head_sha",
                "complete run requires an integration head",
            )
        landing = run.get("landing")
        if (
            isinstance(landing, dict)
            and landing.get("mode") == "pull_request"
            and (
                landing.get("pr_state") != "merged"
                or landing.get("merge_status") != "merged"
            )
        ):
            _add(
                errors,
                "run.landing",
                "complete pull-request run requires merged current-head landing",
            )
        if isinstance(landing, dict) and landing.get("mode") == "pull_request":
            pr_url = landing.get("pr_url")
            authorizations = run.get("authorizations")
            merge_authorization = (
                authorizations.get("merge_pr")
                if isinstance(authorizations, dict)
                else None
            )
            merge_scope = (
                merge_authorization.get("scope")
                if isinstance(merge_authorization, dict)
                else None
            )
            merge_targets = (
                merge_scope.get("targets") if isinstance(merge_scope, dict) else None
            )
            if (
                not _nonempty_string(pr_url)
                or not isinstance(merge_targets, list)
                or f"pr:{pr_url}" not in merge_targets
                or not isinstance(mission_states, dict)
                or not mission_states
                or any(
                    not authorization_covers(
                        run,
                        "merge_pr",
                        mission_id,
                        f"pr:{pr_url}",
                        preserve_completed_run_expiry=True,
                    )
                    for mission_id in mission_states
                )
            ):
                _add(
                    errors,
                    "run.authorizations.merge_pr",
                    "complete pull-request run requires merge authorization for the exact PR",
                )
        if graph_run:
            graph_state = run.get("graph_state")
            node_states = (
                graph_state.get("node_states", {})
                if isinstance(graph_state, dict)
                else {}
            )
            edge_states = (
                graph_state.get("edge_states", {})
                if isinstance(graph_state, dict)
                else {}
            )
            if not isinstance(node_states, dict) or any(
                not isinstance(state, dict)
                or state.get("phase")
                not in {"succeeded", "skipped", "superseded"}
                for state in node_states.values()
            ):
                _add(
                    errors,
                    "run.graph_state.node_states",
                    "complete graph run requires every node to succeed, skip, or be superseded",
                )
            if isinstance(node_states, dict) and any(
                isinstance(state, dict) and bool(state.get("blockers"))
                for state in node_states.values()
            ):
                _add(
                    errors,
                    "run.graph_state.node_states",
                    "complete graph run cannot retain node blockers",
                )
            if isinstance(node_states, dict) and any(
                isinstance(state, dict)
                and state.get("phase") == "succeeded"
                and state.get("last_outcome") != "pass"
                for state in node_states.values()
            ):
                _add(
                    errors,
                    "run.graph_state.node_states",
                    "complete graph run requires every succeeded node to have pass outcome",
                )
            if not isinstance(edge_states, dict) or any(
                not isinstance(state, dict)
                or state.get("status") not in {"traversed", "exhausted", "skipped"}
                for state in edge_states.values()
            ):
                _add(
                    errors,
                    "run.graph_state.edge_states",
                    "complete graph run requires every edge to be terminal",
                )
        if not isinstance(mission_states, dict) or any(
            not isinstance(state, dict)
            or state.get("phase") not in {"integrated", "superseded"}
            for state in mission_states.values()
        ):
            _add(
                errors,
                "run.mission_states",
                "complete run requires every mission to be integrated or superseded",
            )
        if isinstance(mission_states, dict) and any(
            isinstance(state, dict) and bool(state.get("blockers"))
            for state in mission_states.values()
        ):
            _add(errors, "run.mission_states", "complete run cannot retain mission blockers")

        superseded_mission_ids = (
            {
                mission_id
                for mission_id, state in mission_states.items()
                if isinstance(state, dict) and state.get("phase") == "superseded"
            }
            if isinstance(mission_states, dict)
            else set()
        )
        superseded_task_ids = {
            item["id"]
            for current_mission in plan.get("missions", [])
            if isinstance(current_mission, dict)
            for item in current_mission.get("tasks", [])
            if (
                isinstance(item, dict)
                and _nonempty_string(item.get("id"))
                and (
                    item.get("replaced_by")
                    or current_mission.get("id") in superseded_mission_ids
                )
            )
        }
        task_closeout_invalid = not isinstance(task_states, dict)
        if isinstance(task_states, dict):
            for task_id, state in task_states.items():
                expected_phase = (
                    "superseded" if task_id in superseded_task_ids else "mission_recorded"
                )
                if not isinstance(state, dict) or state.get("phase") != expected_phase:
                    task_closeout_invalid = True
                    break
        if task_closeout_invalid:
            _add(
                errors,
                "run.task_states",
                "complete run requires every task to be mission_recorded or superseded",
            )
        if isinstance(task_states, dict) and any(
            isinstance(state, dict)
            and state.get("phase") == "mission_recorded"
            and state.get("verifier_status") != "PASS"
            for state in task_states.values()
        ):
            _add(
                errors,
                "run.task_states",
                "complete run requires every recorded task verifier to PASS",
            )
        if isinstance(task_states, dict) and any(
            isinstance(state, dict) and bool(state.get("blockers"))
            for state in task_states.values()
        ):
            _add(errors, "run.task_states", "complete run cannot retain task blockers")
        if isinstance(wave, dict) and wave.get("status") in {"proposed", "active"}:
            _add(errors, "run.active_wave", "complete run cannot retain an open wave")
        if isinstance(workers, list) and any(
            isinstance(worker, dict)
            and worker.get("phase") in {"leased", "worker_running", "blocked"}
            for worker in workers
        ):
            _add(errors, "run.workers", "complete run cannot retain active or blocked workers")
        review_workers = run.get("review_workers")
        if graph_run and isinstance(review_workers, list) and any(
            isinstance(worker, dict)
            and worker.get("phase") in {"leased", "worker_running", "blocked"}
            for worker in review_workers
        ):
            _add(
                errors,
                "run.review_workers",
                "complete run cannot retain active or blocked review workers",
            )

    return sorted(set(errors))

#!/usr/bin/env python3
"""Select a deterministic typed-graph frontier and runtime bindings."""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path
from typing import Any

from harness_core import classify_execution_route
from harness_manifest import (
    ManifestError,
    authorization_covers,
    execution_covers,
    load_plan,
    load_run,
    mission_conflicts,
    plan_digest,
    resolve_runtime_options,
    route_runtime_driver,
    validate_current_plan_run,


    validate_plan,
    validate_run,
)

# Test patch seams: tests patch these module attributes by name, so the
# imports stay although this module calls only validate_current_plan_run.
_ = (validate_plan, validate_run)

from harness_schema import HEAD_BOUND_AUTHORIZATION_ACTIONS, RUN_DISPATCH_STATUSES


class GraphSelectionError(ValueError):
    """Raised when canonical graph state cannot produce a safe frontier."""


def _tool_profile(node: dict[str, Any]) -> str:
    if node["kind"] == "mission":
        return "mission_write"
    if node["kind"] == "verifier" and node.get("review", {}).get("type") == "visual":
        return "visual_review_readonly"
    if node["kind"] == "verifier" and node.get("review") is not None:
        return "code_review_readonly"
    raise GraphSelectionError(f"runtime node {node['id']} has no supported tool profile")


def _failure_outcome(node: dict[str, Any]) -> str:
    outcomes = node.get("allowed_outcomes", [])
    if "retryable_failure" in outcomes:
        return "retryable_failure"
    if "blocked" in outcomes:
        return "blocked"
    raise GraphSelectionError(f"runtime node {node['id']} has no workflow failure outcome")


def _reviewer_tool_reasons(
    node: dict[str, Any], runtime: dict[str, Any]
) -> set[str]:
    review = node.get("review")
    if not isinstance(review, dict):
        return set()
    capabilities = runtime.get("reviewer_tools")
    if not isinstance(capabilities, dict):
        capabilities = {}
    reasons: set[str] = set()
    for tool_name in review.get("required_tools", []):
        capability = capabilities.get(tool_name)
        if not isinstance(capability, dict) or capability.get("status") == "unobserved":
            reasons.add(f"reviewer_tool_unobserved:{tool_name}")
        elif capability.get("status") != "available":
            reasons.add(f"reviewer_tool_unavailable:{tool_name}")
    return reasons


def _validation_error(kind: str, errors: list[str]) -> GraphSelectionError:
    return GraphSelectionError(
        f"{kind} validation failed:\n" + "\n".join(f"- {error}" for error in errors)
    )


def _node_levels(plan: dict[str, Any]) -> dict[str, int]:
    graph = plan["graph"]
    dependencies = {node["id"]: [] for node in graph["nodes"]}
    for edge in graph["edges"]:
        if edge["kind"] == "dependency":
            dependencies[edge["to"]].append(edge["from"])
    levels: dict[str, int] = {}

    def visit(node_id: str) -> int:
        if node_id in levels:
            return levels[node_id]
        sources = dependencies[node_id]
        level = 0 if not sources else 1 + max(visit(source) for source in sources)
        levels[node_id] = level
        return level

    for node_id in sorted(dependencies):
        visit(node_id)
    return levels


def _runtime_binding(
    node: dict[str, Any],
    runtime: dict[str, Any],
) -> dict[str, Any] | None:
    """Bind a runtime_worker node to the current host, or report it unavailable.

    A node's required provider must match whatever host is actually running
    it: there is no cross-runtime fallback. If the node's declared
    ``allowed_providers`` does not include the current host's provider, the
    node simply cannot run here (the caller surfaces this as the
    ``runtime_unavailable`` dispatch reason) rather than being bridged to a
    different runtime.
    """

    policy = node.get("runtime")
    if node.get("executor") != "runtime_worker" or not isinstance(policy, dict):
        return None
    allowed = policy.get("allowed_providers", [])
    host_provider = runtime.get("runtime_adapter", {}).get("provider")
    if host_provider not in allowed:
        return None
    options = resolve_runtime_options(policy, host_provider)
    return {
        "provider": host_provider,
        "driver": route_runtime_driver(runtime),
        "source": "host",
        **options,
    }


def _incoming(plan: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    dependencies = {node["id"]: [] for node in plan["graph"]["nodes"]}
    routes = {node["id"]: [] for node in plan["graph"]["nodes"]}
    for edge in plan["graph"]["edges"]:
        target = dependencies if edge["kind"] == "dependency" else routes
        target[edge["to"]].append(edge)
    return dependencies, routes


def _preintegration_review_source_ready(
    node: dict[str, Any],
    source_node: dict[str, Any] | None,
    run: dict[str, Any],
) -> bool:
    review = node.get("review")
    if (
        run.get("schema_version") not in {10, 11}
        or node.get("kind") != "verifier"
        or node.get("executor") != "runtime_worker"
        or not isinstance(review, dict)
        or review.get("stage", "preintegration") != "preintegration"
        or len(review.get("mission_ids", [])) != 1
        or not isinstance(source_node, dict)
        or source_node.get("kind") != "mission"
        or source_node.get("ref") not in review.get("mission_ids", [])
    ):
        return False
    mission_state = run.get("mission_states", {}).get(source_node["ref"])
    if (
        not isinstance(mission_state, dict)
        or mission_state.get("phase") != "worker_passed"
        or not isinstance(mission_state.get("head_sha"), str)
    ):
        return False
    source_state = (
        run.get("graph_state", {})
        .get("node_states", {})
        .get(source_node["id"])
    )
    if not isinstance(source_state, dict) or source_state.get("phase") != "running":
        return False
    matching_worker = next(
        (
            worker
            for worker in run.get("workers", [])
            if isinstance(worker, dict)
            and worker.get("worker_id") == mission_state.get("worker_id")
            and worker.get("mission_id") == source_node["ref"]
        ),
        None,
    )
    if (
        not isinstance(matching_worker, dict)
        or matching_worker.get("phase") != "worker_passed"
        or matching_worker.get("worker_head_sha") != mission_state.get("head_sha")
    ):
        return False
    nested_policy = matching_worker.get("nested_subagent_policy")
    return not (
        isinstance(nested_policy, dict)
        and nested_policy.get("enabled") is True
    )


def _preintegration_review_head_matches_current(
    node: dict[str, Any],
    plan: dict[str, Any],
    run: dict[str, Any],
    dependencies: dict[str, list[dict[str, Any]]],
) -> bool | None:
    state = run["graph_state"]["node_states"][node["id"]]
    if state.get("attempts", 0) == 0:
        return None
    nodes_by_id = {
        graph_node["id"]: graph_node for graph_node in plan["graph"]["nodes"]
    }
    ready_sources = [
        nodes_by_id[edge["from"]]
        for edge in dependencies[node["id"]]
        if _preintegration_review_source_ready(
            node,
            nodes_by_id.get(edge["from"]),
            run,
        )
    ]
    if len(ready_sources) != 1:
        return None
    mission_id = ready_sources[0]["ref"]
    current_head = run["mission_states"][mission_id]["head_sha"]
    prior_review = next(
        (
            worker
            for worker in run.get("review_workers", [])
            if isinstance(worker, dict)
            and worker.get("node_id") == node["id"]
            and worker.get("attempt_id") == state.get("last_attempt_id")
        ),
        None,
    )
    if not isinstance(prior_review, dict):
        return None
    return prior_review.get("reviewed_sha") == current_head


def _current_review_result_matches_worker(
    node: dict[str, Any], run: dict[str, Any]
) -> bool | None:
    """Check the current runtime-review node against its bound worker result.

    Historical/superseded worker records are deliberately ignored.  Only the
    worker identified by the current node's attempt and binding may authorize a
    route, and a non-pass finding cannot be represented as a node PASS.
    """

    if node.get("kind") != "verifier" or node.get("executor") != "runtime_worker":
        return None
    review = node.get("review")
    review_stage = review.get("stage", "preintegration") if isinstance(review, dict) else "preintegration"
    if review_stage not in {"preintegration", "integration"}:
        return None
    raw_graph_state = run.get("graph_state")
    node_states = (
        raw_graph_state.get("node_states")
        if isinstance(raw_graph_state, dict)
        else None
    )
    state = node_states.get(node.get("id")) if isinstance(node_states, dict) else None
    if not isinstance(state, dict) or state.get("attempts", 0) < 1:
        return None
    phase = state.get("phase")
    if phase not in {"running", "succeeded", "failed", "blocked"}:
        return None
    worker_id = state.get("bound_worker_id")
    attempt_id = state.get("last_attempt_id")
    if not isinstance(worker_id, str) or not worker_id or not isinstance(attempt_id, str) or not attempt_id:
        # A failed/blocked review may be between attempts while its bounded
        # repair route re-arms the same node.  There is no current worker result
        # to reconcile in that state.  Pre-integration records also retain the
        # historical parent-side result shape with no bound review worker; only
        # an actual current binding is checked here.
        if review_stage == "preintegration":
            return None
        if state.get("phase") in {"failed", "blocked"} and state.get(
            "last_outcome"
        ) in {"fix_required", "blocked", "retryable_failure", "contract_gap"}:
            return None
        return False
    review_workers = run.get("review_workers")
    current_worker = next(
        (
            worker
            for worker in (review_workers if isinstance(review_workers, list) else [])
            if isinstance(worker, dict)
            and worker.get("node_id") == node.get("id")
            and worker.get("worker_id") == worker_id
            and worker.get("attempt_id") == attempt_id
        ),
        None,
    )
    if not isinstance(current_worker, dict):
        return False
    outcome = current_worker.get("outcome")
    if outcome != state.get("last_outcome"):
        return False
    findings = current_worker.get("findings")
    if not isinstance(findings, list):
        return False
    if outcome == "pass":
        return not findings
    if findings:
        return outcome in {"fix_required", "blocked"}
    return True


# A node of these kinds cannot write to the repository, so running it during an
# active wave cannot perturb a live writer, change a head, or race integration.
READ_ONLY_NODE_KINDS = {"verifier", "approval", "external_wait"}


def _active_wave_allows_streaming_review(
    node: dict[str, Any], run: dict[str, Any]
) -> bool:
    """Whether an active wave still permits dispatching this node.

    Writers and lifecycle actions wait for the wave to close. Read-only nodes do
    not: blocking them only idles the parent while a straggling writer finishes,
    and they hold no lease, produce no commit, and move no head.
    """

    active_wave = run.get("active_wave")
    if (
        not isinstance(active_wave, dict)
        or active_wave.get("status") != "active"
        or run.get("schema_version") not in {10, 11}
    ):
        return False
    kind = node.get("kind")
    if kind not in READ_ONLY_NODE_KINDS:
        return False
    review = node.get("review")
    if not isinstance(review, dict):
        # An approval or external wait blocks on a human or an outside system
        # and touches nothing, so it may proceed. A verifier node without a
        # review binding is a deterministic gate, and route edges are
        # ANY-matched: letting one through would fire a batch/integration gate
        # as soon as any streamed review passed, while writers are still live
        # and the mission is not integrated. Those wait for wave close.
        return kind in {"approval", "external_wait"}
    if (
        review.get("stage", "preintegration") != "preintegration"
        or len(review.get("mission_ids", [])) != 1
    ):
        # A batch or integration-stage review binds an integrated head, which
        # does not exist until the wave closes.
        return False
    mission_id = review["mission_ids"][0]
    mission_state = run.get("mission_states", {}).get(mission_id)
    return (
        mission_id in active_wave.get("selected_missions", [])
        and isinstance(mission_state, dict)
        and mission_state.get("phase") == "worker_passed"
    )


def _incoming_route_matched(
    node: dict[str, Any],
    run: dict[str, Any],
    dependencies: dict[str, list[dict[str, Any]]],
    routes: dict[str, list[dict[str, Any]]],
    node_states: dict[str, Any],
    nodes_by_id: dict[str, Any],
) -> bool | None:
    """Whether an incoming route has activated this node.

    Returns None when the node has no incoming routes at all, so callers can
    tell "not route-gated" apart from "route-gated and not yet activated".
    """

    node_id = node["id"]
    incoming_routes = routes[node_id]
    if not incoming_routes:
        return None
    state = run["graph_state"]["node_states"][node_id]
    edge_states = run["graph_state"]["edge_states"]
    for edge in incoming_routes:
        source = node_states[edge["from"]]
        edge_state = edge_states[edge["id"]]
        bound = edge["max_traversals"]
        source_node = nodes_by_id.get(edge["from"])
        if (
            source["last_outcome"] in edge["on_outcomes"]
            and source["phase"] in {"succeeded", "failed", "blocked"}
            and (
                not isinstance(source_node, dict)
                or _current_review_result_matches_worker(source_node, run) is not False
            )
            and (bound is None or edge_state["traversals"] < bound)
        ):
            return True
        if (
            "pass" in edge["on_outcomes"]
            and _preintegration_review_source_ready(
                node,
                nodes_by_id.get(edge["from"]),
                run,
            )
            and (bound is None or edge_state["traversals"] < bound)
        ):
            return True
    if state["attempts"] == 0 and any(
        _preintegration_review_source_ready(
            node,
            nodes_by_id.get(edge["from"]),
            run,
        )
        for edge in dependencies[node_id]
    ):
        return True
    return False


def _logical_reasons(
    node: dict[str, Any],
    plan: dict[str, Any],
    run: dict[str, Any],
    dependencies: dict[str, list[dict[str, Any]]],
    routes: dict[str, list[dict[str, Any]]],
) -> list[str]:
    reasons: set[str] = set()
    node_id = node["id"]
    state = run["graph_state"]["node_states"][node_id]
    preintegration_head_matches = _preintegration_review_head_matches_current(
        node,
        plan,
        run,
        dependencies,
    )
    stale_preintegration_pass = (
        state["phase"] == "succeeded"
        and state.get("last_outcome") == "pass"
        and preintegration_head_matches is False
    )
    node_states = run["graph_state"]["node_states"]
    nodes_by_id = {
        graph_node["id"]: graph_node
        for graph_node in plan["graph"]["nodes"]
    }
    route_matched = _incoming_route_matched(
        node, run, dependencies, routes, node_states, nodes_by_id
    )
    review = node.get("review")
    lineage_exhausted = False
    uses_lineage_budget = (
        run.get("schema_version") == 11
        and node.get("kind") == "verifier"
        and isinstance(review, dict)
    )
    if uses_lineage_budget:
        lineage = run.get("review_lineages", {}).get(review.get("lineage_id"))
        if isinstance(lineage, dict):
            allowance = lineage.get("base_allowance", 0) + lineage.get("additional_allowance", 0)
            lineage_exhausted = lineage.get("consumed_attempts", 0) >= allowance
    if _current_review_result_matches_worker(node, run) is False:
        reasons.add("review_result_dissent")
    # A post-integration review that returned fix_required parks in `failed`.
    # Once its bounded repair route completes and routes back, the review has to
    # run again on the new head, so it re-arms here the same way a stale
    # pre-integration pass does. Without this the loop drawn in the flow diagram
    # has no path back to `ready` and the frontier silently empties.
    repair_return_rearm = (
        node["kind"] == "verifier"
        and state["phase"] == "failed"
        and state.get("last_outcome") == "fix_required"
        and route_matched is True
        and not lineage_exhausted
        and (
            run.get("schema_version") == 11
            or state["attempts"] < node["max_attempts"]
        )
    )
    if run.get("schema_version") == 11:
        desired_state = run.get("control", {}).get("desired_state")
        if desired_state == "paused":
            reasons.add("run_paused")
        elif desired_state == "cancelled":
            reasons.add("run_cancelled")
    if run.get("plan_readiness") != "ready":
        reasons.add("plan_not_ready")
    if run.get("status") not in RUN_DISPATCH_STATUSES:
        reasons.add("run_status_not_dispatchable")
    if run.get("execution_authorized") is not True:
        reasons.add("execution_not_authorized")
    if (
        state["phase"] not in {"dormant", "ready"}
        and not stale_preintegration_pass
        and not repair_return_rearm
    ):
        reasons.add("node_phase_not_ready")
    if state["blockers"]:
        reasons.add("blocker_present")
    if lineage_exhausted:
        reasons.add("review_lineage_exhausted")
    elif not uses_lineage_budget and state["attempts"] >= node["max_attempts"]:
        reasons.add("attempts_exhausted")

    for edge in dependencies[node_id]:
        source = node_states[edge["from"]]
        if (
            source["phase"] != "succeeded"
            or source["last_outcome"] != "pass"
        ) and not _preintegration_review_source_ready(
            node,
            nodes_by_id.get(edge["from"]),
            run,
        ):
            reasons.add("dependency_not_satisfied")

    if (
        state.get("last_outcome") == "fix_required"
        and preintegration_head_matches is True
    ):
        reasons.add("review_head_unchanged")

    if route_matched is False:
        reasons.add("route_not_activated")

    if (
        node.get("kind") == "verifier"
        and isinstance(review, dict)
        and review.get("stage", "preintegration") == "integration"
    ):
        mission_states = run.get("mission_states", {})
        if (
            not isinstance(mission_states, dict)
            or any(
                not isinstance(mission_states.get(mission_id), dict)
                or mission_states[mission_id].get("phase") != "integrated"
                for mission_id in review.get("mission_ids", [])
            )
            or not run.get("integration", {}).get("integration_head_sha")
        ):
            reasons.add("integration_not_unified")

    if node["kind"] == "mission":
        mission_state = run["mission_states"][node["ref"]]
        if mission_state["phase"] not in {"queued", "ready"}:
            reasons.add("mission_phase_not_ready")
    return sorted(reasons)


def _current_authorized_head(run: dict[str, Any]) -> str | None:
    """Resolve the live candidate head for one head-bound lifecycle action.

    `push` is the only head-bound action, and the only head it can publish is
    the current integration head.
    """
    integration = run.get("integration")
    if isinstance(integration, dict):
        return integration.get("integration_head_sha")
    return None


def _write_launch_reasons(run: dict[str, Any]) -> set[str]:
    reasons: set[str] = set()
    integration = run.get("integration", {})
    observed = run.get("observed", {})
    observed_git = observed.get("git", {})
    if not observed.get("captured_at"):
        reasons.add("parent_state_unreconciled")
    batch_base = integration.get("batch_base_sha")
    integration_head = integration.get("integration_head_sha")
    if not batch_base:
        reasons.add("batch_base_missing")
    else:
        if integration_head and batch_base != integration_head:
            reasons.add("batch_base_stale")
        if (
            observed_git.get("parent_branch") == integration.get("branch")
            and observed_git.get("parent_head_sha")
            and batch_base != observed_git.get("parent_head_sha")
        ):
            reasons.add("batch_base_stale")
    if observed_git.get("parent_dirty") is not False:
        reasons.add("parent_state_unreconciled")
    return reasons


def _resume_reconciliation_reasons(run: dict[str, Any]) -> list[str]:
    if run.get("status") != "running":
        return []
    reasons: set[str] = set()
    observed = run.get("observed")
    observed_git = observed.get("git") if isinstance(observed, dict) else None
    if not isinstance(observed_git, dict):
        return sorted(reasons | {"parent_state_unreconciled"})
    for field in ("parent_worktree_path", "parent_branch", "parent_head_sha"):
        if not observed_git.get(field):
            reasons.add("parent_state_unreconciled")
    if observed_git.get("parent_dirty") is not False:
        reasons.add("parent_state_unreconciled")

    worktrees = observed_git.get("worktrees")
    if not isinstance(worktrees, list):
        return sorted(reasons | {"worktree_state_unreconciled"})
    observed_by_path: dict[str, dict[str, Any]] = {}
    for worktree in worktrees:
        if not isinstance(worktree, dict) or not worktree.get("path"):
            reasons.add("worktree_state_unreconciled")
            continue
        path = worktree["path"]
        if path in observed_by_path:
            reasons.add("worktree_state_unreconciled")
        observed_by_path[path] = worktree
        if worktree.get("dirty") is not False or not worktree.get("branch_ref") or not worktree.get("head_sha"):
            reasons.add("worktree_state_unreconciled")

    workers = run.get("workers")
    if not isinstance(workers, list):
        return sorted(reasons | {"worker_state_unreconciled"})
    worker_paths = {
        worker.get("worktree_path")
        for worker in workers
        if isinstance(worker, dict) and worker.get("worktree_path")
    }
    parent_path = observed_git.get("parent_worktree_path")
    if any(path != parent_path and path not in worker_paths for path in observed_by_path):
        reasons.add("worktree_state_unreconciled")

    for worker in workers:
        if not isinstance(worker, dict) or worker.get("phase") in {"worker_failed", "superseded"}:
            continue
        if worker.get("workspace_mode") not in {
            "parent_managed_worktree",
            "app_managed_worktree",
        }:
            reasons.add("worker_state_unreconciled")
            continue
        path = worker.get("worktree_path")
        worktree = observed_by_path.get(path)
        if worktree is None:
            reasons.add("worker_state_unreconciled")
            continue
        if worktree.get("branch_ref") != worker.get("branch_ref"):
            reasons.add("worker_state_unreconciled")
        recorded_head = worker.get("worker_head_sha")
        if recorded_head is not None and worktree.get("head_sha") != recorded_head:
            reasons.add("worker_state_unreconciled")
    return sorted(reasons)


def _required_actions(
    node: dict[str, Any],
    binding: dict[str, Any],
    runtime: dict[str, Any],
    schema_version: int,
) -> list[str]:
    read_only_review = node["kind"] == "verifier"
    driver = binding["driver"]
    actions: list[str] = []
    if driver in {"subagents", "dynamic_workflow"}:
        actions.append("spawn_subagents")
    elif driver == "app_threads":
        actions.append("create_user_owned_tasks")
        # RUN-v11 records nested capability separately from the worker's
        # explicit nested policy.  Capability discovery alone must not grant
        # or require a child-spawn action; an enabled policy is validated when
        # its worker result is recorded.  Keep the legacy inference for
        # pre-v10 runs so their historical action contract remains stable.
        nested = runtime.get("nested_subagents")
        if not read_only_review and schema_version not in {10, 11}:
            nested_spawn_required = (
                isinstance(nested, dict)
                and nested.get("available") is True
            )
            if nested_spawn_required:
                actions.append("spawn_subagents")
    if read_only_review:
        return actions
    workspace = runtime.get("workspace_mode")
    if workspace == "parent_managed_worktree":
        actions.extend(["create_local_worktrees", "create_local_branches", "create_local_commits"])
    elif workspace == "app_managed_worktree":
        if "create_user_owned_tasks" not in actions:
            actions.append("create_user_owned_tasks")
        actions.extend(
            ["create_app_managed_worktrees", "create_local_branches", "create_local_commits"]
        )
    return actions


def _dispatch_reasons(
    node: dict[str, Any],
    binding: dict[str, Any] | None,
    plan: dict[str, Any],
    run: dict[str, Any],
    missions: dict[str, dict[str, Any]],
) -> list[str]:
    reasons: set[str] = set()
    runtime = run["runtime_capabilities"]
    observed_runtime = run["observed"]["runtime"]
    if (
        run.get("active_wave", {}).get("status") == "active"
        and not _active_wave_allows_streaming_review(node, run)
    ):
        reasons.add("blocker_present")
    permission = runtime.get("permission_boundary")
    if permission is not None and permission.get("status") != "ready":
        reasons.add("permission_boundary_not_ready")
    if node["executor"] == "runtime_worker":
        version_gate = runtime.get("runtime_adapter", {}).get("version_gate")
        if version_gate is None and run.get("schema_version") in {10, 11}:
            reasons.add("runtime_version_unobserved")
        elif isinstance(version_gate, dict):
            version_status = version_gate.get("status")
            if version_status == "unobserved":
                reasons.add("runtime_version_unobserved")
            elif version_status == "upgrade_required":
                reasons.add("runtime_upgrade_required")
            elif version_status == "restart_required":
                reasons.add("runtime_restart_required")
            elif (
                version_status == "compatible_old"
                and run.get("active_wave", {}).get("status") != "active"
            ):
                reasons.add("runtime_upgrade_pending")
            if run.get("schema_version") == 11:
                loaded = version_gate.get("loaded_contract_digest")
                installed = version_gate.get("installed_contract_digest")
                if loaded is None or installed is None:
                    reasons.add("runtime_contract_unobserved")
                elif loaded != installed:
                    reasons.add("runtime_restart_required")
        # Deferral reasons are not short-circuited elsewhere in this module (see
        # _logical_reasons), so a missing binding does not return early either:
        # doing so hid every other applicable reason (e.g. action_not_authorized)
        # behind runtime_unavailable, so fixing one blocker just exposed the
        # next one instead of clearing the node. The checks below that need a
        # real binding already guard on `binding is not None`.
        if binding is None:
            reasons.add("runtime_unavailable")
        else:
            if (
                node["kind"] == "verifier"
                and isinstance(node.get("review"), dict)
                and binding["driver"] == "sequential_parent"
            ):
                reasons.add("independent_reviewer_unavailable")
            if observed_runtime.get("completion_channel_available") is not True:
                reasons.add("completion_channel_unavailable")
            if observed_runtime.get("available_worker_slots", 0) <= 0:
                reasons.add("runtime_capacity_unavailable")
            if node["kind"] == "verifier":
                reasons.update(_reviewer_tool_reasons(node, runtime))
    if node["kind"] in {"mission", "lifecycle"}:
        # mission nodes spawn workers/commits and lifecycle nodes push or
        # clean up: both mutate real state derived from the parent's current git
        # position, so both need a reconciled parent and a known batch base
        # before launch. verifier, approval, and external_wait nodes are
        # read-only with respect to that state and do not need this gate.
        reasons.update(_write_launch_reasons(run))
    if node["kind"] == "mission":
        workspace_mode = runtime["workspace_mode"]
        if workspace_mode == "shared_checkout":
            reasons.add("workspace_not_isolated")
        if node.get("executor") == "harness_parent":
            reasons.add("workspace_not_isolated")
        plan_mission = missions.get(node["ref"], {})
        if plan_mission:
            if plan_mission.get("resource_inventory_complete") is not True:
                reasons.add("incomplete_resource_inventory")
            if plan_mission.get("worktree_eligible") is not True:
                reasons.add("worktree_ineligible")
            if observed_runtime.get("isolation_capacity", 0) <= 0:
                reasons.add("runtime_capacity_unavailable")
    authorization_missions: list[str] = []
    if node["kind"] == "mission":
        authorization_missions = [node["ref"]]
        if not execution_covers(run, node["ref"]):
            reasons.add("execution_not_authorized")
    elif node["kind"] == "verifier" and node["executor"] == "runtime_worker":
        authorization_missions = node["review"]["mission_ids"]
        if any(not execution_covers(run, mission_id) for mission_id in authorization_missions):
            reasons.add("execution_not_authorized")
    if authorization_missions and binding is not None:
        for action in _required_actions(
            node,
            binding,
            run["runtime_capabilities"],
            run["schema_version"],
        ):
            target = "*"
            if any(
                not authorization_covers(run, action, mission_id, target)
                for mission_id in authorization_missions
            ):
                reasons.add("action_not_authorized")
    if node["kind"] == "lifecycle":
        # A bare "*" target is unreachable for `push`: schema v10 rejects a
        # wildcard scope for every HEAD_BOUND_AUTHORIZATION_ACTIONS entry
        # (harness_authorization.py). node["target"], when the PLAN declares
        # one, is the exact target the RUN ledger was actually granted against.
        # Falling back to "*" when it is absent keeps already-valid PLANs
        # (authored before this field existed) unchanged.
        target = node.get("target") or "*"
        mission_ids = sorted(run["mission_states"])
        current_head = _current_authorized_head(run)
        if any(
            not authorization_covers(run, node["ref"], mission_id, target)
            for mission_id in mission_ids
        ):
            reasons.add("action_not_authorized")
        elif (
            run.get("schema_version") in {10, 11}
            and node["ref"] in HEAD_BOUND_AUTHORIZATION_ACTIONS
            and (
                not isinstance(current_head, str)
                or any(
                    not authorization_covers(
                        run,
                        node["ref"],
                        mission_id,
                        target,
                        required_head_sha=current_head,
                    )
                    for mission_id in mission_ids
                )
            )
        ):
            reasons.add("authorization_head_stale")
    return sorted(reasons)


def _directive(
    node: dict[str, Any], binding: dict[str, Any] | None, run: dict[str, Any]
) -> dict[str, Any]:
    base = {"node_id": node["id"], "kind": node["kind"], "ref": node["ref"]}
    if node["kind"] == "approval":
        return {**base, "launch_kind": "await_approval"}
    if node["kind"] == "external_wait":
        return {**base, "launch_kind": "poll_external"}
    if node["kind"] == "lifecycle":
        return {
            **base,
            "launch_kind": "run_lifecycle_action",
            "required_actions": [node["ref"]],
            "target": node.get("target") or "*",
        }
    if node["kind"] == "verifier" and node["executor"] != "runtime_worker":
        return {**base, "launch_kind": "run_verifier"}
    if binding is None:
        return {**base, "launch_kind": "unavailable"}
    driver = binding["driver"]
    launch_kind = {
        "app_threads": "create_thread",
        "subagents": "spawn_subagent",
        "sequential_parent": "run_parent",
        "dynamic_workflow": "run_dynamic_workflow",
    }[driver]
    directive = {
        **base,
        "launch_kind": launch_kind,
        "runtime_provider": binding["provider"],
        "runtime_driver": driver,
        "runtime_source": binding["source"],
        "runtime_binding": binding,
        "tool_profile": _tool_profile(node),
        "failure_outcome": _failure_outcome(node),
        "required_actions": _required_actions(
            node,
            binding,
            run["runtime_capabilities"],
            run["schema_version"],
        ),
    }
    runtime = run["runtime_capabilities"]
    if node["kind"] == "verifier":
        directive["review"] = node["review"]
        required_tools = node["review"].get("required_tools", [])
        directive["reviewer_tool_capabilities"] = {
            tool_name: runtime.get("reviewer_tools", {}).get(tool_name)
            for tool_name in required_tools
        }
    directive.update(
        {
            "worker_runtime": runtime["worker_runtime"],
            "workspace_mode": runtime["workspace_mode"],
            "completion_channel": runtime["completion_channel"],
        }
    )
    return directive


def select_ready_nodes(
    plan: dict[str, Any],
    run: dict[str, Any],
    *,
    repo_root: str | Path | None = None,
    manifest_already_validated: bool = False,
) -> dict[str, Any]:
    # Callers that just validated the identical on-disk pair (for example the
    # reserve transition, which validates once before selection and once after
    # its mutation) pass the flag to skip the redundant walk. The load-bearing
    # post-mutation gate still refuses to write an invalid RUN.
    validation_errors = (
        []
        if manifest_already_validated
        else validate_current_plan_run(plan, run, repo_root=repo_root)
    )
    if validation_errors:
        schema_pair = (
            plan.get("schema_version") if isinstance(plan, dict) else None,
            run.get("schema_version") if isinstance(run, dict) else None,
        )
        if schema_pair != (6, 11):
            raise GraphSelectionError(
                "typed graph selection requires PLAN v6 with RUN v11"
            )
        raise _validation_error("PLAN/RUN", validation_errors)

    dependencies, routes = _incoming(plan)
    levels = _node_levels(plan)
    missions = {mission["id"]: mission for mission in plan["missions"]}
    nodes = sorted(
        plan["graph"]["nodes"],
        key=lambda node: (
            levels[node["id"]],
            -missions.get(node["ref"], {}).get("priority", 0),
            missions.get(node["ref"], {}).get("merge_rank", 0),
            node["id"],
        ),
    )

    logical_ready: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    reconciliation_reasons = _resume_reconciliation_reasons(run)
    for node in nodes:
        reasons = sorted(
            set(_logical_reasons(node, plan, run, dependencies, routes))
            | set(reconciliation_reasons)
        )
        if reasons:
            deferred.append({"node_id": node["id"], "reason_codes": reasons})
        else:
            binding = _runtime_binding(node, run["runtime_capabilities"])
            logical_ready.append({"node": node, "binding": binding})

    dispatch_ready: list[dict[str, Any]] = []
    for item in logical_ready:
        reasons = _dispatch_reasons(
            item["node"],
            item["binding"],
            plan,
            run,
            missions,
        )
        if reasons:
            deferred.append({"node_id": item["node"]["id"], "reason_codes": reasons})
        else:
            dispatch_ready.append(item)

    write_candidates = [
        item for item in dispatch_ready if item["node"]["kind"] == "mission"
    ]
    selected_write: list[dict[str, Any]] = []
    conflict_edges: list[dict[str, Any]] = []
    for left, right in combinations(write_candidates, 2):
        reasons = set(
            mission_conflicts(
                missions[left["node"]["ref"]], missions[right["node"]["ref"]]
            )
        )
        if run["runtime_capabilities"]["workspace_mode"] == "shared_checkout":
            reasons.add("workspace_not_isolated")
        if reasons:
            conflict_edges.append(
                {
                    "left": left["node"]["id"],
                    "right": right["node"]["id"],
                    "reason_codes": sorted(reasons),
                }
            )
    runtime_driver = route_runtime_driver(run["runtime_capabilities"])
    configured_write_budget = min(
        plan["max_parallel_workers"],
        run["runtime_capabilities"]["max_parallel_workers"],
    )
    if runtime_driver == "sequential_parent":
        configured_write_budget = min(configured_write_budget, 1)
    isolated_write_budget = min(
        configured_write_budget,
        run["observed"]["runtime"]["available_worker_slots"],
        run["observed"]["runtime"]["isolation_capacity"],
    )
    # A budget of one looks like a deliberate cap, but it is also what an
    # unprobed host looks like: new_run.py seeds observation fields with 1 and
    # `detection_source: "fallback"`, and nothing forces the parent to replace
    # them. A run that never probed then executes every mission sequentially and
    # reports only `over_budget`, which reads as "your limit", not "nobody
    # looked". Name that case so it is visible in the proposal.
    capability_unprobed = (
        run["runtime_capabilities"].get("runtime_adapter", {}).get("detection_source")
        == "fallback"
    )

    def budget_reasons() -> list[str]:
        return ["over_budget", "capability_unprobed"] if capability_unprobed else ["over_budget"]

    conflict_pairs = {
        frozenset((edge["left"], edge["right"])) for edge in conflict_edges
    }
    isolated_write_count = 0
    for item in write_candidates:
        node_id = item["node"]["id"]
        if any(
            frozenset((node_id, selected["node"]["id"])) in conflict_pairs
            for selected in selected_write
        ):
            deferred.append({"node_id": node_id, "reason_codes": ["write_conflict"]})
            continue
        if len(selected_write) >= configured_write_budget:
            deferred.append({"node_id": node_id, "reason_codes": budget_reasons()})
            continue
        if run["runtime_capabilities"]["workspace_mode"] != "shared_checkout":
            if isolated_write_count >= isolated_write_budget:
                deferred.append({"node_id": node_id, "reason_codes": budget_reasons()})
                continue
            isolated_write_count += 1
        selected_write.append(item)

    selected_ids = {item["node"]["id"] for item in selected_write}
    authorized_candidates = [
        item
        for item in dispatch_ready
        if item["node"]["kind"] != "mission" or item["node"]["id"] in selected_ids
    ]

    runtime_budget = min(
        plan["max_parallel_workers"],
        run["runtime_capabilities"]["max_parallel_workers"],
        run["observed"]["runtime"]["available_worker_slots"],
    )
    if runtime_driver == "sequential_parent":
        runtime_budget = min(runtime_budget, 1)
    # One budget for every runtime worker, writer or reviewer. A reviewer is an
    # agent and occupies a host slot exactly like a writer does, so a separate
    # counter would let the parent launch twice what the host reported. Reviews
    # genuinely do not consume *isolation* capacity, but that is a different
    # field (`isolation_capacity`) already spent only on the write budget above;
    # `available_worker_slots` is what this counter spends, and there is no
    # second pool of those.
    runtime_count = 0
    runtime_worker_node_ids = {
        item["node"]["id"]
        for item in authorized_candidates
        if item["node"]["executor"] == "runtime_worker"
    }
    dispatchable: list[dict[str, Any]] = []
    for item in authorized_candidates:
        node = item["node"]
        if node["executor"] == "runtime_worker":
            if runtime_count >= runtime_budget:
                deferred.append(
                    {"node_id": node["id"], "reason_codes": ["over_runtime_budget"]}
                )
                continue
            runtime_count += 1
        dispatchable.append(_directive(node, item["binding"], run))

    # A wave that runs one mission at a time is often correct: a dependency
    # chain, overlapping write scopes, no isolation, or a host with no way to
    # spawn isolated writers. Every one of those states its own reason.
    #
    # It is not correct when independent, conflict-free, authorized missions
    # were held back only by a budget nobody ever measured. `fallback` means the
    # capability was never determined, so running sequentially on it is a guess
    # presented as a decision -- and it looks identical to a deliberate cap.
    # Withhold the proposal and make the parent say which it is: probe the host
    # (`observed`) or declare the route on purpose (`explicit`).
    withheld_for_unprobed_capability = capability_unprobed and any(
        "capability_unprobed" in entry["reason_codes"] for entry in deferred
    )
    if withheld_for_unprobed_capability:
        # Withhold only what unmeasured capability actually governs. A local
        # command, an approval, or an external wait needs no worker slot and no
        # isolated workspace, so blocking it here would report a reason that is
        # not its reason. A lifecycle action stays withheld: it pushes or cleans
        # up, and that should not proceed while the route is undecided.
        held, released = [], []
        for directive in dispatchable:
            governed = (
                directive.get("launch_kind") == "run_lifecycle_action"
                or directive["node_id"] in runtime_worker_node_ids
            )
            (held if governed else released).append(directive)
        for directive in held:
            deferred.append(
                {
                    "node_id": directive["node_id"],
                    "reason_codes": ["capability_unprobed"],
                }
            )
        dispatchable = released

    execution_route = classify_execution_route(
        managed_artifacts=True,
        selected_safe_write_missions=sum(
            1 for directive in dispatchable if directive["kind"] == "mission"
        ),
    )
    return {
        "plan_id": plan["plan_id"],
        "plan_revision": plan["revision"],
        "plan_digest_sha256": plan_digest(plan),
        "graph_revision": run["graph_state"]["graph_revision"],
        "execution_route": execution_route,
        "ready_frontier": [item["node"]["id"] for item in logical_ready],
        "dispatchable_nodes": dispatchable,
        "deferred_nodes": sorted(deferred, key=lambda item: item["node_id"]),
        "conflict_edges": conflict_edges,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select typed graph nodes and bind them to observed runtimes."
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Optional repository root used to bind PLAN-v6 sources",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = select_ready_nodes(
            load_plan(args.plan), load_run(args.run), repo_root=args.repo_root
        )
    except (ManifestError, OSError, GraphSelectionError) as exc:
        print(json.dumps({"status": "ERROR", "errors": [str(exc)]}, sort_keys=True, indent=2))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

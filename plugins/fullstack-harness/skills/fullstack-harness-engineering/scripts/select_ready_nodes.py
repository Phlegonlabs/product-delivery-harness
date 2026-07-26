#!/usr/bin/env python3
"""Select a deterministic typed-graph frontier and runtime bindings."""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

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
    validate_plan,
    validate_run,
)


class GraphSelectionError(ValueError):
    """Raised when canonical graph state cannot produce a safe frontier."""


TOOL_PROFILES = {
    "mission_write",
    "code_review_readonly",
    "visual_review_readonly",
}


def _tool_profile(node: dict[str, Any]) -> str:
    if node["kind"] == "mission":
        return "mission_write"
    if node["kind"] == "verifier" and node.get("review", {}).get("type") == "visual":
        return "visual_review_readonly"
    if node["kind"] == "verifier" and node.get("review") is not None:
        return "code_review_readonly"
    raise GraphSelectionError(f"runtime node {node['id']} has no supported tool profile")


def _workspace_mode_for(
    item: dict[str, Any], run: dict[str, Any]
) -> str:
    return run["runtime_capabilities"]["workspace_mode"]


def _failure_outcome(node: dict[str, Any]) -> str:
    outcomes = node.get("allowed_outcomes", [])
    if "retryable_failure" in outcomes:
        return "retryable_failure"
    if "blocked" in outcomes:
        return "blocked"
    raise GraphSelectionError(f"runtime node {node['id']} has no workflow failure outcome")


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
        run.get("schema_version") != 10
        or node.get("kind") != "verifier"
        or node.get("executor") != "runtime_worker"
        or not isinstance(review, dict)
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
    if run.get("plan_readiness") != "ready":
        reasons.add("plan_not_ready")
    if run.get("execution_authorized") is not True:
        reasons.add("execution_not_authorized")
    if (
        state["phase"] not in {"dormant", "ready"}
        and not stale_preintegration_pass
    ):
        reasons.add("node_phase_not_ready")
    if state["blockers"]:
        reasons.add("blocker_present")
    if state["attempts"] >= node["max_attempts"]:
        reasons.add("attempts_exhausted")

    node_states = run["graph_state"]["node_states"]
    nodes_by_id = {
        graph_node["id"]: graph_node
        for graph_node in plan["graph"]["nodes"]
    }
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

    incoming_routes = routes[node_id]
    if incoming_routes:
        edge_states = run["graph_state"]["edge_states"]
        matched = False
        for edge in incoming_routes:
            source = node_states[edge["from"]]
            edge_state = edge_states[edge["id"]]
            bound = edge["max_traversals"]
            if (
                source["last_outcome"] in edge["on_outcomes"]
                and source["phase"] in {"succeeded", "failed", "blocked"}
                and (bound is None or edge_state["traversals"] < bound)
            ):
                matched = True
            elif (
                "pass" in edge["on_outcomes"]
                and _preintegration_review_source_ready(
                    node,
                    nodes_by_id.get(edge["from"]),
                    run,
                )
                and (bound is None or edge_state["traversals"] < bound)
            ):
                matched = True
        if not matched and state["attempts"] == 0 and any(
            _preintegration_review_source_ready(
                node,
                nodes_by_id.get(edge["from"]),
                run,
            )
            for edge in dependencies[node_id]
        ):
            matched = True
        if not matched:
            reasons.add("route_not_activated")

    if node["kind"] == "mission":
        mission_state = run["mission_states"][node["ref"]]
        if mission_state["phase"] not in {"queued", "ready"}:
            reasons.add("mission_phase_not_ready")
    return sorted(reasons)


def _action_authorized(
    run: dict[str, Any], action: str, mission_id: str, target: str = "*"
) -> bool:
    return authorization_covers(run, action, mission_id, target)


def _write_launch_reasons(run: dict[str, Any]) -> set[str]:
    reasons: set[str] = set()
    integration = run.get("integration", {})
    observed_git = run.get("observed", {}).get("git", {})
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
        nested = runtime.get("nested_subagents")
        if not read_only_review:
            nested_spawn_required = (
                isinstance(nested, dict)
                and nested.get("available") is True
                and (
                    schema_version != 10
                    or "reviewer" in set(nested.get("allowed_roles", []))
                )
            ) or (
                schema_version == 10
                and not isinstance(nested, dict)
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
    run: dict[str, Any],
    missions: dict[str, dict[str, Any]],
) -> list[str]:
    reasons: set[str] = set()
    runtime = run["runtime_capabilities"]
    observed_runtime = run["observed"]["runtime"]
    if run.get("active_wave", {}).get("status") == "active":
        reasons.add("blocker_present")
    permission = runtime.get("permission_boundary")
    if permission is not None and permission.get("status") != "ready":
        reasons.add("permission_boundary_not_ready")
    if node["executor"] == "runtime_worker":
        if binding is None:
            reasons.add("runtime_unavailable")
            return sorted(reasons)
        if observed_runtime.get("completion_channel_available") is not True:
            reasons.add("completion_channel_unavailable")
        if observed_runtime.get("available_worker_slots", 0) <= 0:
            reasons.add("runtime_capacity_unavailable")
    if node["kind"] == "mission":
        reasons.update(_write_launch_reasons(run))
        workspace_mode = _workspace_mode_for({"node": node, "binding": binding}, run)
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
                not _action_authorized(run, action, mission_id, target)
                for mission_id in authorization_missions
            ):
                reasons.add("action_not_authorized")
    if node["kind"] == "lifecycle":
        mission_ids = sorted(run["mission_states"])
        if any(not _action_authorized(run, node["ref"], mission_id) for mission_id in mission_ids):
            reasons.add("action_not_authorized")
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
        return {**base, "launch_kind": "run_lifecycle_action", "required_actions": [node["ref"]]}
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
    if node["kind"] == "verifier":
        directive["review"] = node["review"]
    runtime = run["runtime_capabilities"]
    directive.update(
        {
            "worker_runtime": runtime["worker_runtime"],
            "workspace_mode": runtime["workspace_mode"],
            "completion_channel": runtime["completion_channel"],
        }
    )
    return directive


def select_ready_nodes(plan: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    plan_errors = validate_plan(plan)
    if plan_errors:
        raise _validation_error("PLAN", plan_errors)
    run_errors = validate_run(plan, run)
    if run_errors:
        raise _validation_error("RUN", run_errors)
    schema_pair = (plan.get("schema_version"), run.get("schema_version"))
    if schema_pair not in {(4, 8), (4, 9), (5, 10)}:
        raise GraphSelectionError(
            "typed graph selection requires PLAN v4 with RUN v8/v9 or PLAN v5 with RUN v10"
        )

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
        reasons = _dispatch_reasons(item["node"], item["binding"], run, missions)
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
        if (
            _workspace_mode_for(left, run) == "shared_checkout"
            and _workspace_mode_for(right, run) == "shared_checkout"
        ):
            reasons.add("workspace_not_isolated")
        if reasons:
            conflict_edges.append(
                {
                    "left": left["node"]["id"],
                    "right": right["node"]["id"],
                    "reason_codes": sorted(reasons),
                }
            )
    configured_write_budget = min(
        plan["max_parallel_workers"],
        run["runtime_capabilities"]["max_parallel_workers"],
    )
    isolated_write_budget = min(
        configured_write_budget,
        run["observed"]["runtime"]["available_worker_slots"],
        run["observed"]["runtime"]["isolation_capacity"],
    )
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
            deferred.append({"node_id": node_id, "reason_codes": ["over_budget"]})
            continue
        if _workspace_mode_for(item, run) != "shared_checkout":
            if isolated_write_count >= isolated_write_budget:
                deferred.append({"node_id": node_id, "reason_codes": ["over_budget"]})
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
    runtime_count = 0
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

    return {
        "plan_id": plan["plan_id"],
        "plan_revision": plan["revision"],
        "plan_digest_sha256": plan_digest(plan),
        "graph_revision": run["graph_state"]["graph_revision"],
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = select_ready_nodes(load_plan(args.plan), load_run(args.run))
    except (ManifestError, OSError, GraphSelectionError) as exc:
        print(json.dumps({"status": "ERROR", "errors": [str(exc)]}, sort_keys=True, indent=2))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

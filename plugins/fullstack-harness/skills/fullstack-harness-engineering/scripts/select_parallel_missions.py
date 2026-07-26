#!/usr/bin/env python3
"""Produce a deterministic, launch-gated parallel mission proposal."""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

from harness_manifest import (
    ManifestError,
    authorization_covers,
    execution_covers,
    load_plan,
    load_run,
    mission_conflicts,
    parent_owned_path,
    plan_digest,
    route_runtime_driver,
    topological_levels,
    validate_plan,
    validate_run,
    validate_scope_claim,
)


PAIRWISE_REASON_CODES = {
    "scope_overlap",
    "case_scope_collision",
    "serialized_resource_conflict",
    "runtime_resource_conflict",
    "workspace_not_isolated",
}

UNARY_REASON_CODES = {
    "plan_not_ready",
    "execution_not_authorized",
    "action_not_authorized",
    "mission_phase_not_ready",
    "dependency_not_integrated",
    "dependency_gate_not_pass",
    "dependency_ancestry_unconfirmed",
    "plan_digest_mismatch",
    "batch_base_missing",
    "batch_base_stale",
    "incomplete_resource_inventory",
    "unsupported_scope",
    "parent_owned_scope",
    "worktree_ineligible",
    "runtime_capacity_unavailable",
    "completion_channel_unavailable",
    "permission_boundary_not_ready",
    "blocker_present",
    "platform_lifecycle_unknown",
    "over_budget",
}

_DIGEST_ERROR_PREFIX = "run.plan.digest_sha256: does not match semantic PLAN digest"

class SelectionError(ValueError):
    """Raised when manifests cannot safely be used for selection."""


def _required_actions(runtime: dict[str, Any]) -> tuple[str, ...]:
    actions: list[str] = []
    runtime_driver = route_runtime_driver(runtime)
    workspace_mode = runtime.get("workspace_mode")

    if runtime_driver in {"subagents", "dynamic_workflow"}:
        actions.append("spawn_subagents")
    elif runtime_driver == "app_threads":
        actions.extend(("create_user_owned_tasks", "spawn_subagents"))

    if workspace_mode == "parent_managed_worktree":
        actions.extend(
            ("create_local_worktrees", "create_local_branches", "create_local_commits")
        )
    elif workspace_mode == "app_managed_worktree":
        if "create_user_owned_tasks" not in actions:
            actions.append("create_user_owned_tasks")
        actions.extend(
            (
                "create_app_managed_worktrees",
                "create_local_branches",
                "create_local_commits",
            )
        )
    return tuple(actions)


def _launch_directive(
    mission_id: str, runtime: dict[str, Any]
) -> dict[str, Any]:
    worker_runtime = runtime["worker_runtime"]
    runtime_driver = route_runtime_driver(runtime)
    launch_kind = {
        "sequential_parent": "run_parent",
        "subagents": "spawn_subagent",
        "app_threads": "create_thread",
        "dynamic_workflow": "run_dynamic_workflow",
    }[runtime_driver]

    nested_policy: dict[str, Any] = {
        "mode": "not_applicable",
        "max_children": 0,
        "allowed_roles": [],
        "write_policy": "read_only",
        "completion_channel": "agent_result",
    }
    if runtime_driver == "app_threads":
        nested = runtime.get("nested_subagents")
        if isinstance(nested, dict) and nested.get("available") is True:
            nested_policy = {
                "mode": "enabled_read_only",
                "max_children": min(nested["max_children_per_worker"], 3),
                "allowed_roles": sorted(nested["allowed_roles"]),
                "write_policy": "read_only",
                "completion_channel": "agent_result",
            }
        else:
            nested_policy["mode"] = "capability_handshake"

    directive = {
        "mission_id": mission_id,
        "launch_kind": launch_kind,
        "worker_runtime": worker_runtime,
        "workspace_mode": runtime["workspace_mode"],
        "completion_channel": runtime["completion_channel"],
        "required_actions": list(_required_actions(runtime)),
        "nested_subagent_policy": nested_policy,
        "worker_prompt_template": "assets/templates/WORKER_GOAL.template.md",
    }
    adapter = runtime.get("runtime_adapter")
    if isinstance(adapter, dict):
        directive["runtime_provider"] = adapter["provider"]
        directive["runtime_driver"] = runtime_driver
    if runtime_driver == "dynamic_workflow":
        directive["workflow_policy"] = {
            "mode": "flat_wave",
            "mid_run_user_input": False,
            "result_channel": "agent_result",
            "script_path": "assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js",
        }
    return directive


def _action_covers_mission(run: dict[str, Any], action: str, mission_id: str) -> bool:
    """Require mission scope plus explicit target-wide pre-allocation approval."""

    entry = run.get("authorizations", {}).get(action, {})
    scope = entry.get("scope", {}) if isinstance(entry, dict) else {}
    targets = scope.get("targets", []) if isinstance(scope, dict) else []
    # Exact worker/task/branch/worktree identities do not exist at selection time.
    # Never substitute a mission ID for one of those concrete targets. The parent
    # must check the allocated target again immediately before the mutation.
    return "*" in targets and authorization_covers(run, action, mission_id)


def _lifecycle_known(runtime: dict[str, Any]) -> bool:
    mode = runtime.get("workspace_mode")
    lifecycle = runtime.get("platform_lifecycle")
    if not isinstance(lifecycle, dict):
        return False
    expected_owner = "app" if mode == "app_managed_worktree" else "parent"
    if lifecycle.get("owner") != expected_owner:
        return False
    if not isinstance(lifecycle.get("automatic_retention_cleanup_possible"), bool):
        return False
    if not isinstance(lifecycle.get("durable_branch_required_before_unique_work"), bool):
        return False
    if mode in {"parent_managed_worktree", "app_managed_worktree"}:
        return lifecycle.get("durable_branch_required_before_unique_work") is True
    return True


def _mission_structure_reasons(mission: dict[str, Any]) -> list[str]:
    reasons: set[str] = set()
    if mission.get("resource_inventory_complete") is not True:
        reasons.add("incomplete_resource_inventory")
    for claim in mission.get("write_scope", []):
        if validate_scope_claim(claim):
            reasons.add("unsupported_scope")
        elif parent_owned_path(claim):
            reasons.add("parent_owned_scope")
    return sorted(reasons)


def _base_reasons(run: dict[str, Any]) -> set[str]:
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
    # RUN does not contain dirty-path attribution. Defer conservatively and let the
    # parent replace this broad blocker with a fresh path-level observation.
    if observed_git.get("parent_dirty") is True:
        reasons.add("blocker_present")
    return reasons


def _dependency_reasons(
    mission: dict[str, Any], mission_states: dict[str, Any]
) -> set[str]:
    reasons: set[str] = set()
    for dependency_id in mission.get("depends_on", []):
        state = mission_states.get(dependency_id, {})
        if state.get("phase") != "integrated":
            reasons.add("dependency_not_integrated")
            continue
        if state.get("integration_gate") != "PASS":
            reasons.add("dependency_gate_not_pass")
            continue
        if not state.get("integrated_sha"):
            reasons.add("dependency_ancestry_unconfirmed")
    return reasons


def _global_launch_reasons(
    plan: dict[str, Any],
    run: dict[str, Any],
    *,
    runtime_slots: int,
    isolation_capacity: int,
) -> set[str]:
    reasons: set[str] = set()
    if run.get("plan_readiness") != "ready":
        reasons.add("plan_not_ready")
    if run.get("plan", {}).get("digest_sha256") != plan_digest(plan):
        reasons.add("plan_digest_mismatch")
    reasons.update(_base_reasons(run))
    if runtime_slots <= 0 or isolation_capacity <= 0:
        reasons.add("runtime_capacity_unavailable")
    if run.get("observed", {}).get("runtime", {}).get(
        "completion_channel_available"
    ) is not True:
        reasons.add("completion_channel_unavailable")
    if not _lifecycle_known(run.get("runtime_capabilities", {})):
        reasons.add("platform_lifecycle_unknown")
    permission = run.get("runtime_capabilities", {}).get("permission_boundary")
    if permission is not None and permission.get("status") != "ready":
        reasons.add("permission_boundary_not_ready")
    if run.get("active_wave", {}).get("status") == "active":
        reasons.add("blocker_present")
    return reasons


def _mission_launch_reasons(
    mission: dict[str, Any],
    run: dict[str, Any],
    global_reasons: set[str],
) -> list[str]:
    mission_id = mission["id"]
    runtime = run["runtime_capabilities"]
    state = run["mission_states"].get(mission_id, {})
    reasons = set(global_reasons)
    missing_actions: list[str] = []

    reasons.update(_mission_structure_reasons(mission))
    if not execution_covers(run, mission_id):
        reasons.add("execution_not_authorized")
    if state.get("phase") not in {"queued", "ready"}:
        reasons.add("mission_phase_not_ready")
    if state.get("blocker") or state.get("blockers"):
        reasons.add("blocker_present")
    reasons.update(_dependency_reasons(mission, run["mission_states"]))

    workspace_mode = runtime.get("workspace_mode")
    if workspace_mode != "shared_checkout" and mission.get("worktree_eligible") is not True:
        reasons.add("worktree_ineligible")

    for action in _required_actions(runtime):
        if not _action_covers_mission(run, action, mission_id):
            missing_actions.append(action)
    if missing_actions:
        reasons.add("action_not_authorized")

    return sorted(reasons)


def _conflict_edges(
    missions: Iterable[dict[str, Any]], workspace_mode: str
) -> list[dict[str, Any]]:
    structurally_valid = [
        mission for mission in missions if not _mission_structure_reasons(mission)
    ]
    edges: list[dict[str, Any]] = []
    for left, right in combinations(sorted(structurally_valid, key=lambda item: item["id"]), 2):
        reasons = set(mission_conflicts(left, right))
        if workspace_mode == "shared_checkout":
            reasons.add("workspace_not_isolated")
        unknown = reasons - PAIRWISE_REASON_CODES
        if unknown:
            raise SelectionError(
                "shared conflict helper returned unsupported reason code(s): "
                + ", ".join(sorted(unknown))
            )
        if reasons:
            edges.append(
                {
                    "left": left["id"],
                    "right": right["id"],
                    "reason_codes": sorted(reasons),
                }
            )
    return edges


def _edge_index(edges: Iterable[dict[str, Any]]) -> dict[frozenset[str], list[str]]:
    return {
        frozenset((edge["left"], edge["right"])): edge["reason_codes"]
        for edge in edges
    }


def _conflicts_with_selected(
    mission_id: str,
    selected: Iterable[str],
    edges: dict[frozenset[str], list[str]],
) -> tuple[list[str], list[str]]:
    conflicts_with: list[str] = []
    reasons: set[str] = set()
    for selected_id in selected:
        edge_reasons = edges.get(frozenset((mission_id, selected_id)), [])
        if edge_reasons:
            conflicts_with.append(selected_id)
            reasons.update(edge_reasons)
    return sorted(conflicts_with), sorted(reasons)


def _ordered_missions(plan: dict[str, Any]) -> list[dict[str, Any]]:
    levels = topological_levels(plan)
    return sorted(
        plan["missions"],
        key=lambda mission: (
            levels[mission["id"]],
            -mission["priority"],
            mission["merge_rank"],
            mission["id"],
        ),
    )


def _validation_error(kind: str, errors: Iterable[str]) -> SelectionError:
    return SelectionError(f"{kind} validation failed:\n" + "\n".join(f"- {e}" for e in errors))


def select_parallel_missions(
    plan: dict[str, Any],
    run: dict[str, Any],
    *,
    runtime_slots: int | None = None,
    isolation_capacity: int | None = None,
) -> dict[str, Any]:
    """Return a pure deterministic proposal from canonical inner manifests."""

    if plan.get("schema_version") in {4, 5}:
        raise SelectionError(
            "schema v4/v5 typed graphs must use select_ready_nodes.py"
        )
    plan_errors = validate_plan(plan)
    if plan_errors:
        raise _validation_error("PLAN", plan_errors)

    run_errors = validate_run(plan, run)
    fatal_run_errors = [
        error for error in run_errors if not error.startswith(_DIGEST_ERROR_PREFIX)
    ]
    if fatal_run_errors:
        raise _validation_error("RUN", fatal_run_errors)

    observed_runtime = run["observed"]["runtime"]
    slots = (
        observed_runtime["available_worker_slots"]
        if runtime_slots is None
        else runtime_slots
    )
    isolation = (
        observed_runtime["isolation_capacity"]
        if isolation_capacity is None
        else isolation_capacity
    )
    if isinstance(slots, bool) or not isinstance(slots, int) or slots < 0:
        raise SelectionError("runtime_slots must be a non-negative integer")
    if isinstance(isolation, bool) or not isinstance(isolation, int) or isolation < 0:
        raise SelectionError("isolation_capacity must be a non-negative integer")

    runtime = run["runtime_capabilities"]
    if runtime["workspace_mode"] == "shared_checkout":
        isolation = min(isolation, 1)

    ordered = _ordered_missions(plan)
    conflict_edges = _conflict_edges(ordered, runtime["workspace_mode"])
    edges = _edge_index(conflict_edges)
    global_reasons = _global_launch_reasons(
        plan, run, runtime_slots=slots, isolation_capacity=isolation
    )

    ready: list[str] = []
    unary_deferred: dict[str, dict[str, Any]] = {}
    for mission in ordered:
        reason_codes = _mission_launch_reasons(mission, run, global_reasons)
        if reason_codes:
            item: dict[str, Any] = {
                "mission_id": mission["id"],
                "reason_codes": reason_codes,
                "conflicts_with": [],
            }
            unary_deferred[mission["id"]] = item
        else:
            ready.append(mission["id"])

    admitted_without_cap: list[str] = []
    for mission_id in ready:
        conflicts_with, _ = _conflicts_with_selected(
            mission_id, admitted_without_cap, edges
        )
        if not conflicts_with:
            admitted_without_cap.append(mission_id)

    configured_maximum = min(
        plan["max_parallel_workers"], runtime["max_parallel_workers"]
    )
    effective_budget = min(
        configured_maximum,
        slots,
        isolation,
        len(admitted_without_cap),
    )

    selected: list[str] = []
    selection_deferred: dict[str, dict[str, Any]] = {}
    for mission_id in ready:
        conflicts_with, reason_codes = _conflicts_with_selected(
            mission_id, selected, edges
        )
        if conflicts_with:
            selection_deferred[mission_id] = {
                "mission_id": mission_id,
                "reason_codes": reason_codes,
                "conflicts_with": conflicts_with,
            }
            continue
        if len(selected) >= effective_budget:
            selection_deferred[mission_id] = {
                "mission_id": mission_id,
                "reason_codes": ["over_budget"],
                "conflicts_with": [],
            }
            continue
        selected.append(mission_id)

    deferred_by_id = {**unary_deferred, **selection_deferred}
    deferred = [
        deferred_by_id[mission["id"]]
        for mission in ordered
        if mission["id"] in deferred_by_id
    ]

    for item in deferred:
        unknown = set(item["reason_codes"]) - (UNARY_REASON_CODES | PAIRWISE_REASON_CODES)
        if unknown:
            raise SelectionError(
                "selector produced unsupported reason code(s): "
                + ", ".join(sorted(unknown))
            )

    result = {
        "batch_base_sha": run["integration"]["batch_base_sha"],
        "candidate_order": ready,
        "conflict_edges": conflict_edges,
        "deferred_missions": deferred,
        "effective_worker_budget": effective_budget,
        "launch_directives": [
            _launch_directive(mission_id, runtime) for mission_id in selected
        ],
        "plan_digest_sha256": plan_digest(plan),
        "plan_id": plan["plan_id"],
        "plan_revision": plan["revision"],
        "ready_frontier": ready,
        "selected_missions": selected,
    }
    adapter = runtime.get("runtime_adapter")
    if isinstance(adapter, dict):
        runtime_driver = route_runtime_driver(runtime)
        result["runtime_route"] = {
            "provider": adapter["provider"],
            "driver": runtime_driver,
            "detection_source": adapter["detection_source"],
        }
        if runtime_driver == "dynamic_workflow" and selected:
            result["wave_launch"] = {
                "launch_kind": "run_dynamic_workflow",
                "mission_ids": selected,
                "script_path": "assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js",
                "args_source": "accepted_wave",
            }
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select a deterministic launch-gated wave from PLAN.md and RUN.md."
    )
    parser.add_argument("--plan", required=True, type=Path, help="canonical PLAN.md path")
    parser.add_argument("--run", required=True, type=Path, help="canonical RUN.md path")
    parser.add_argument(
        "--runtime-slots",
        type=int,
        help="fresh observed worker-slot capacity; defaults to RUN",
    )
    parser.add_argument(
        "--isolation-capacity",
        type=int,
        help="fresh observed workspace isolation capacity; defaults to RUN",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        proposal = select_parallel_missions(
            load_plan(args.plan),
            load_run(args.run),
            runtime_slots=args.runtime_slots,
            isolation_capacity=args.isolation_capacity,
        )
    except (ManifestError, OSError, SelectionError) as exc:
        sys.stdout.write(
            json.dumps(
                {"errors": [str(exc)], "status": "ERROR"},
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
        return 2
    sys.stdout.write(json.dumps(proposal, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

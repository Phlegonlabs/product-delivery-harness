#!/usr/bin/env python3
"""Validate a canonical external-Codex preflight or allocated mission wave."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from harness_manifest import (
    authorization_covers,
    execution_covers,
    load_plan,
    load_run,
    plan_digest,
    resolve_runtime_options,
    validate_plan,
    validate_run,
)


class CodexWaveError(ValueError):
    """Raised when canonical state cannot safely launch external Codex."""


def _fail(errors: list[str]) -> None:
    raise CodexWaveError("\n".join(sorted(set(errors))))


def _exact_authorized(run: dict[str, Any], action: str, mission_id: str, target: str) -> bool:
    """Require a live authorization whose mission and target are both concrete."""

    if not authorization_covers(run, action, mission_id, target):
        return False
    entry = run.get("authorizations", {}).get(action, {})
    scope = entry.get("scope", {}) if isinstance(entry, dict) else {}
    missions = scope.get("mission_ids", []) if isinstance(scope, dict) else []
    targets = scope.get("targets", []) if isinstance(scope, dict) else []
    return mission_id in missions and target in targets


def _external_codex_record(
    run: dict[str, Any], *, require_available: bool
) -> dict[str, Any] | None:
    """Return the unique observed cc-codex record for this launch phase."""

    adapter = run.get("runtime_capabilities", {}).get("runtime_adapter", {})
    records = adapter.get("external_runtimes", []) if isinstance(adapter, dict) else []
    matches = [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("provider") == "codex"
        and record.get("driver") == "codex_rescue_agent"
        and record.get("command") == "agent:codex:codex-rescue"
        and isinstance(record.get("version"), str)
        and record.get("version")
        and record.get("completion_channel") == "agent_result"
        and (
            not require_available
            or (
                record.get("status") == "available"
                and record.get("contract_version") == "harness-node-result-v1"
            )
        )
    ]
    return matches[0] if len(matches) == 1 else None


def _mission_nodes(plan: dict[str, Any], node_ids: list[str]) -> list[dict[str, Any]]:
    nodes = {node["id"]: node for node in plan["graph"]["nodes"]}
    errors: list[str] = []
    selected: list[dict[str, Any]] = []
    if not node_ids or len(node_ids) != len(set(node_ids)):
        errors.append("node IDs must be a non-empty unique list")
    for node_id in node_ids:
        node = nodes.get(node_id)
        if node is None:
            errors.append(f"unknown graph node {node_id}")
        elif node.get("kind") != "mission" or node.get("executor") != "runtime_worker":
            errors.append(f"node {node_id} is not an external-Codex mission")
        else:
            selected.append(node)
    if errors:
        _fail(errors)
    return selected


def _base_checks(
    plan: dict[str, Any], run: dict[str, Any], *, require_available: bool
) -> dict[str, Any]:
    errors = [f"PLAN: {error}" for error in validate_plan(plan)]
    errors.extend(f"RUN: {error}" for error in validate_run(plan, run))
    if plan.get("schema_version") != 4:
        errors.append("external Codex requires PLAN schema v4")
    if run.get("schema_version") != 9:
        errors.append("external Codex requires RUN schema v9")
    if run.get("status") != "running" or run.get("plan_readiness") != "ready":
        errors.append("RUN must be running and ready")
    runtime = run.get("runtime_capabilities", {})
    if runtime.get("permission_boundary", {}).get("status") != "ready":
        errors.append("runtime permission boundary must be ready")
    codex_record = _external_codex_record(run, require_available=require_available)
    if codex_record is None:
        errors.append(
            "exact external Codex capability is not available"
            if require_available
            else "cc-codex plugin metadata is not observed"
        )
    integration = run.get("integration", {})
    observed_git = run.get("observed", {}).get("git", {})
    base = integration.get("batch_base_sha")
    if not base or base != integration.get("integration_head_sha"):
        errors.append("integration batch base is stale")
    if observed_git.get("parent_dirty") is not False or observed_git.get("parent_head_sha") != base:
        errors.append("observed parent Git state is not a clean batch base")
    if errors:
        _fail(errors)
    assert codex_record is not None
    return codex_record


def _ensure_codex_policy(node: dict[str, Any]) -> dict[str, Any]:
    policy = node.get("runtime")
    if not isinstance(policy, dict) or "codex" not in policy.get("allowed_providers", []):
        _fail([f"node {node['id']} does not allow Codex"])
    return resolve_runtime_options(policy, "codex")


def _validate_preflight(plan: dict[str, Any], run: dict[str, Any], nodes: list[dict[str, Any]]) -> None:
    errors: list[str] = []
    for node in nodes:
        mission_id = node["ref"]
        _ensure_codex_policy(node)
        state = run["graph_state"]["node_states"].get(node["id"], {})
        mission = run["mission_states"].get(mission_id, {})
        if state.get("phase") not in {"dormant", "ready"} or state.get("blockers"):
            errors.append(f"node {node['id']} is not ready for Codex preflight")
        if mission.get("phase") not in {"queued", "ready"}:
            errors.append(f"mission {mission_id} is not ready for Codex preflight")
        if not execution_covers(run, mission_id):
            errors.append(f"mission {mission_id} lacks execution authorization")
        if not _exact_authorized(run, "invoke_external_runtime", mission_id, "runtime:codex"):
            errors.append(f"mission {mission_id} lacks exact Codex runtime authorization")
        if not _exact_authorized(run, "spawn_subagents", mission_id, "worker:preallocation"):
            errors.append(f"mission {mission_id} lacks preallocation subagent authorization")
    if errors:
        _fail(errors)


def _worker_for(run: dict[str, Any], worker_id: str) -> dict[str, Any] | None:
    matches = [worker for worker in run.get("workers", []) if worker.get("worker_id") == worker_id]
    return matches[0] if len(matches) == 1 else None


def _wave_node(plan: dict[str, Any], run: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    mission_id = node["ref"]
    mission = next(mission for mission in plan["missions"] if mission["id"] == mission_id)
    state = run["graph_state"]["node_states"].get(node["id"], {})
    mission_state = run["mission_states"].get(mission_id, {})
    worker_id = state.get("bound_worker_id")
    worker = _worker_for(run, worker_id) if isinstance(worker_id, str) else None
    digest = plan_digest(plan)
    base = run["integration"]["batch_base_sha"]
    errors: list[str] = []
    if state.get("phase") != "running" or state.get("blockers"):
        errors.append(f"node {node['id']} is not a running unblocked attempt")
    attempt_id = state.get("last_attempt_id")
    if not isinstance(attempt_id, str) or not attempt_id:
        errors.append(f"node {node['id']} has no active attempt")
    if mission_state.get("phase") != "worker_running":
        errors.append(f"mission {mission_id} is not worker_running")
    if (
        mission_state.get("worker_id") != worker_id
        or mission_state.get("lease_plan_revision") != plan["revision"]
        or mission_state.get("lease_plan_digest_sha256") != digest
        or mission_state.get("base_sha") != base
        or not mission_state.get("lease_id")
    ):
        errors.append(f"mission {mission_id} lease does not match the active graph attempt")
    if not isinstance(worker, dict):
        errors.append(f"node {node['id']} has no unique bound worker")
    else:
        binding = worker.get("runtime_binding", {})
        expected = _ensure_codex_policy(node)
        if (
            worker.get("mission_id") != mission_id
            or worker.get("lease_id") != mission_state.get("lease_id")
            or worker.get("plan_revision") != plan["revision"]
            or worker.get("plan_digest_sha256") != digest
            or worker.get("batch_base_sha") != base
            or worker.get("worker_runtime") != "subagent"
            or worker.get("workspace_mode") != "app_managed_worktree"
            or worker.get("completion_channel") != "agent_result"
            or worker.get("phase") not in {"leased", "worker_running"}
            or binding.get("provider") != "codex"
            or binding.get("driver") != "external_codex_agent"
            or binding.get("source") != "external_agent"
            or binding.get("model") != expected["model"]
            or binding.get("reasoning_effort") != expected["reasoning_effort"]
            or binding.get("option_source") != expected["option_source"]
        ):
            errors.append(f"worker {worker_id} is not the canonical external Codex allocation")
        worktree_path = worker.get("worktree_path")
        branch_ref = worker.get("branch_ref")
        if not isinstance(worktree_path, str) or not worktree_path:
            errors.append(f"worker {worker_id} lacks an allocated worktree path")
        if not isinstance(branch_ref, str) or not branch_ref:
            errors.append(f"worker {worker_id} lacks an allocated branch ref")
        if not execution_covers(run, mission_id):
            errors.append(f"mission {mission_id} lacks execution authorization")
        for action, target in (
            ("invoke_external_runtime", "runtime:codex"),
            ("spawn_subagents", f"worker:{worker_id}"),
            ("create_app_managed_worktrees", f"worktree:{worktree_path}"),
            ("create_local_branches", f"branch:{branch_ref}"),
            ("create_local_commits", f"branch:{branch_ref}"),
        ):
            if not _exact_authorized(run, action, mission_id, target):
                errors.append(f"mission {mission_id} lacks exact {action} authorization for {target}")
    if errors:
        _fail(errors)
    task_ids = [task["id"] for task in mission["tasks"] if not task.get("replaced_by")]
    verifier_ids = [
        verifier["id"]
        for task in mission["tasks"]
        if task["id"] in task_ids
        for verifier in task["verifiers"]
    ] + [verifier["id"] for verifier in mission["worker_verifiers"]]
    prompt = "\n".join([mission["objective"], *[task["objective"] for task in mission["tasks"] if task["id"] in task_ids]])
    return {
        "node_id": node["id"],
        "attempt_id": attempt_id,
        "node_kind": "mission",
        "mission_id": mission_id,
        "lease_id": mission_state["lease_id"],
        "failure_outcome": "retryable_failure" if "retryable_failure" in node["allowed_outcomes"] else "blocked",
        "worker_prompt": prompt,
        "write_scope": mission["write_scope"],
        "deny_scope": mission["deny_scope"],
        "task_ids": task_ids,
        "verifier_ids": verifier_ids,
    }


def validate_codex_wave(
    plan: dict[str, Any], run: dict[str, Any], node_ids: list[str], *, mode: str = "wave"
) -> dict[str, Any]:
    """Return canonical Workflow arguments without changing PLAN, RUN, Git, or runtime."""

    if mode not in {"preflight", "wave"}:
        _fail(["mode must be preflight or wave"])
    codex_record = _base_checks(plan, run, require_available=mode == "wave")
    nodes = _mission_nodes(plan, node_ids)
    if mode == "preflight":
        _validate_preflight(plan, run, nodes)
        return {
            "contract_version": "harness-node-result-v1",
            "plugin_version": codex_record["version"],
        }
    wave = run.get("active_wave", {})
    digest = plan_digest(plan)
    if (
        wave.get("status") != "active"
        or wave.get("plan_revision") != plan["revision"]
        or wave.get("plan_digest_sha256") != digest
        or wave.get("batch_base_sha") != run["integration"]["batch_base_sha"]
    ):
        _fail(["active wave does not match canonical PLAN/RUN state"])
    if any(node["ref"] not in wave.get("selected_missions", []) for node in nodes):
        _fail(["active wave does not select every requested mission"])
    wave_nodes = [_wave_node(plan, run, node) for node in nodes]
    options = _ensure_codex_policy(nodes[0])
    if any(_ensure_codex_policy(node) != options for node in nodes[1:]):
        _fail(["Codex wave nodes must share canonical provider options"])
    return {
        "run_id": run["run_id"],
        "plan_id": plan["plan_id"],
        "plan_revision": plan["revision"],
        "plan_digest_sha256": digest,
        "graph_revision": run["graph_state"]["graph_revision"],
        "batch_base_sha": run["integration"]["batch_base_sha"],
        "tool_profile": "mission_write",
        "model": options["model"],
        "reasoning_effort": options["reasoning_effort"],
        "nodes": wave_nodes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--node-id", action="append", dest="node_ids", required=True)
    parser.add_argument("--mode", choices=("preflight", "wave"), default="wave")
    args = parser.parse_args()
    try:
        workflow_args = validate_codex_wave(
            load_plan(Path(args.plan)), load_run(Path(args.run)), args.node_ids, mode=args.mode
        )
    except (CodexWaveError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(workflow_args, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

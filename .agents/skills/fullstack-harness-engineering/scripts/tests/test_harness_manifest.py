#!/usr/bin/env python3
"""Focused tests for the canonical harness manifest contract."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import (  # noqa: E402
    AUTHORIZATION_KEYS,
    ManifestError,
    load_plan,
    load_run,
    mission_conflicts,
    plan_digest,
    route_runtime_driver,
    scope_overlap,
    topological_levels,
    validate_plan,
    validate_run,
    validate_ui_evidence_files,
    validate_scope_claim,
)
from harness_authorization import authorization_covers  # noqa: E402
from harness_schema import action_target_kind_allowed  # noqa: E402


SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40


def verifier(identifier: str, *argv: str) -> dict[str, object]:
    return {
        "id": identifier,
        "cwd": ".",
        "argv": list(argv) or ["python3", "-m", "unittest"],
        "pass_signal": "exit 0",
    }


def task(
    mission_id: str,
    number: int,
    trace_id: str,
    path: str,
    *,
    depends_on: list[str] | None = None,
) -> dict[str, object]:
    task_id = f"{mission_id}/T{number:02d}"
    return {
        "id": task_id,
        "alias": f"task-{number}",
        "objective": f"Complete {task_id}",
        "acceptance_matrix": [
            {
                "test_id": f"TEST-{mission_id}-{number:02d}",
                "trace_ids": [trace_id],
                "criterion": f"{task_id} passes",
            }
        ],
        "trace_ids": [trace_id],
        "depends_on": list(depends_on or []),
        "parent_task": None,
        "legacy_task_ids": [],
        "replaced_by": [],
        "split_reason": None,
        "refinement_generation": 0,
        "write_scope": [path],
        "verifiers": [verifier(f"verify-{mission_id.lower()}-{number}", "tool", task_id)],
    }


def mission(
    mission_id: str,
    trace_id: str,
    write_scope: str,
    tasks: list[dict[str, object]],
    *,
    depends_on: list[str] | None = None,
    priority: int = 100,
    merge_rank: int = 10,
) -> dict[str, object]:
    return {
        "id": mission_id,
        "alias": mission_id.lower(),
        "objective": f"Deliver {mission_id}",
        "priority": priority,
        "merge_rank": merge_rank,
        "trace_ids": [trace_id],
        "write_scope": [write_scope],
        "deny_scope": ["docs/goal/PLAN.md", "docs/goal/RUN.md"],
        "resource_inventory_complete": True,
        "serialized_resources": [],
        "runtime_resources": [],
        "worktree_eligible": True,
        "required_skills": [],
        "stop_conditions": ["Stop on contract conflict"],
        "worker_verifiers": [verifier(f"worker-{mission_id.lower()}", "tool", "worker")],
        "integration_verifiers": [
            verifier(f"integrate-{mission_id.lower()}", "tool", "integration")
        ],
        "tasks": tasks,
    }


def graph_node(
    node_id: str,
    kind: str,
    ref: str,
    executor: str,
    outcomes: list[str],
) -> dict[str, object]:
    return {
        "id": node_id,
        "kind": kind,
        "ref": ref,
        "executor": executor,
        "allowed_outcomes": outcomes,
        "max_attempts": 2,
        "runtime": (
            {"preferred_provider": None, "allowed_providers": ["codex", "claude_code"]}
            if executor == "runtime_worker"
            else None
        ),
    }


def graph_for(*missions: dict[str, object]) -> dict[str, object]:
    """A mission chain, one singleton review per mission, one final gate.

    v10 needs every write-scope mission to have its own direct singleton
    pre-integration review, and v5 needs each review's `pass` to route into a
    deterministic gate. A review that covers exactly the one mission it depends
    on satisfies bounded repair through same-worktree correction, so no repair
    route is needed.
    """
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    previous: str | None = None
    for item in missions:
        mission_id = item["id"]
        node_id = f"N-{mission_id}"
        review_id = f"N-REVIEW-{mission_id}"
        review_pass_id = f"N-REVIEW-PASS-{mission_id}"
        nodes.append(
            graph_node(
                node_id,
                "mission",
                mission_id,
                "runtime_worker",
                ["pass", "retryable_failure", "blocked", "contract_gap"],
            )
        )
        review = graph_node(
            review_id,
            "verifier",
            "batch",
            "runtime_worker",
            ["pass", "fix_required", "retryable_failure", "blocked", "contract_gap"],
        )
        review["review"] = {
            "type": "backend_code",
            "mission_ids": [mission_id],
            "scope": list(item["write_scope"]),
            "required_evidence": ["reviewed_sha", "findings"],
        }
        nodes.append(review)
        nodes.append(
            graph_node(
                review_pass_id,
                "verifier",
                "batch",
                "local_command",
                ["pass", "blocked"],
            )
        )
        edges.append(
            {
                "id": f"E-{mission_id}-REVIEW",
                "kind": "dependency",
                "from": node_id,
                "to": review_id,
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        edges.append(
            {
                "id": f"E-{mission_id}-REVIEW-PASS",
                "kind": "route",
                "from": review_id,
                "to": review_pass_id,
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        edges.append(
            {
                "id": f"E-{mission_id}-REVIEW-PASS-FINAL",
                "kind": "dependency",
                "from": review_pass_id,
                "to": "N-FINAL",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        if previous is not None:
            edges.append(
                {
                    "id": f"E-{previous}-{mission_id}",
                    "kind": "dependency",
                    "from": f"N-{previous}",
                    "to": node_id,
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                }
            )
        previous = mission_id
    nodes.append(
        graph_node("N-FINAL", "verifier", "final", "local_command", ["pass", "blocked"])
    )
    return {
        "entry_nodes": [f"N-{missions[0]['id']}"],
        "nodes": nodes,
        "edges": edges,
    }


def valid_plan() -> dict[str, object]:
    m1_tasks = [
        task("M1", 1, "REQ-001", "src/a/one.py"),
        task(
            "M1",
            2,
            "REQ-001",
            "src/a/two.py",
            depends_on=["M1/T01"],
        ),
    ]
    m1 = mission("M1", "REQ-001", "src/a/**", m1_tasks)
    m1["runtime_resources"] = [
        {"key": "port:3000", "access": "exclusive"},
        {"key": "db:test", "access": "shared_read"},
    ]
    m1["serialized_resources"] = ["migration:primary", "fixture:users"]

    m2 = mission(
        "M2",
        "REQ-002",
        "src/ab/**",
        [task("M2", 1, "REQ-002", "src/ab/one.py")],
        depends_on=["M1"],
        priority=80,
        merge_rank=20,
    )
    m2["runtime_resources"] = [{"key": "port:3001", "access": "exclusive"}]
    return {
        "schema_version": 5,
        "plan_id": "PLAN-TEST",
        "revision": 1,
        "objective": "Deliver a deterministic test plan",
        "max_parallel_workers": 3,
        "sources": [
            {
                "id": "SRC-001",
                "kind": "prd",
                "location": "docs/product/prd.md",
                "owner": "product",
                "status": "frozen",
                "content_sha256": "f" * 64,
                "source_revision": None,
                "staged_revision": None,
                "notes": "product contract",
            },
            {
                "id": "SRC-002",
                "kind": "architecture",
                "location": "docs/product/architecture.md",
                "owner": "engineering",
                "status": "frozen",
                "content_sha256": "e" * 64,
                "source_revision": None,
                "staged_revision": None,
                "notes": "technical contract",
            },
        ],
        "traces": [
            {
                "id": "REQ-001",
                "source_ids": ["SRC-002", "SRC-001"],
                "priority": "must",
                "requirement": "Deliver the first capability",
                "disposition": "planned",
                "rationale": None,
            },
            {
                "id": "REQ-002",
                "source_ids": ["SRC-001"],
                "priority": "should",
                "requirement": "Deliver the second capability",
                "disposition": "planned",
                "rationale": None,
            },
        ],
        "ui_surfaces": [],
        "risks": [],
        "batch_verifiers": [verifier("batch", "tool", "batch")],
        "final_gates": [verifier("final", "tool", "final")],
        "required_reviews": ["backend_code"],
        "graph": graph_for(m1, m2),
        "missions": [m1, m2],
    }


def legacy_plan(schema_version: int = 2) -> dict[str, object]:
    """Build a valid non-graph PLAN using an explicitly supported old schema."""
    if schema_version not in {2, 3}:
        raise ValueError("legacy non-graph PLAN schema must be 2 or 3")
    plan = valid_plan()
    plan["schema_version"] = schema_version
    plan.pop("graph")
    plan.pop("required_reviews")
    for source in plan["sources"]:
        source.pop("content_sha256")
        source.pop("source_revision")
        source.pop("staged_revision")
    dependencies = {"M1": [], "M2": ["M1"]}
    for current_mission in plan["missions"]:
        current_mission["depends_on"] = dependencies[current_mission["id"]]
        for current_task in current_mission["tasks"]:
            current_task["acceptance_matrix"] = [
                row["criterion"] for row in current_task["acceptance_matrix"]
            ]
    return plan


def legacy_graph_plan() -> dict[str, object]:
    """Build the readable PLAN-v4 form of the canonical typed graph."""
    plan = valid_plan()
    plan["schema_version"] = 4
    for source in plan["sources"]:
        source.pop("staged_revision")
    for current_mission in plan["missions"]:
        for current_task in current_mission["tasks"]:
            current_task["acceptance_matrix"] = [
                row["criterion"] for row in current_task["acceptance_matrix"]
            ]
    return plan








def valid_run(plan: dict[str, object]) -> dict[str, object]:
    digest = plan_digest(plan)
    mission_ids = [item["id"] for item in plan["missions"]]
    task_ids = [
        item["id"]
        for current_mission in plan["missions"]
        for item in current_mission["tasks"]
    ]
    return {
        "schema_version": 10,
        "run_id": "RUN-TEST",
        "plan": {
            "id": plan["plan_id"],
            "revision": plan["revision"],
            "digest_sha256": digest,
        },
        "status": "draft",
        "intent": "plan-only",
        "plan_readiness": "draft",
        "execution_authorized": False,
        "execution_authorization_source": None,
        "execution_authorization_scope": None,
        "authorizations": {
            key: {"authorized": False, "source": None}
            for key in AUTHORIZATION_KEYS
        },
        "runtime_capabilities": {
            "worker_runtime": "parent",
            "workspace_mode": "shared_checkout",
            "completion_channel": "agent_result",
            "max_parallel_workers": 1,
            "runtime_adapter": {
                "provider": "codex",
                "available_drivers": ["sequential_parent"],
                "detection_source": "fallback",
            },
            "platform_lifecycle": {
                "owner": "parent",
                "automatic_retention_cleanup_possible": False,
                "durable_branch_required_before_unique_work": True,
            },
        },
        "observed": {
            "captured_at": None,
            "git": {
                "parent_worktree_path": "C:/repo/fullstack-goal-dev",
                "parent_branch": "main",
                "parent_head_sha": SHA_A,
                "parent_dirty": False,
                "worktrees": [],
            },
            "runtime": {
                "available_worker_slots": 1,
                "isolation_capacity": 1,
                "completion_channel_available": True,
            },
        },
        "integration": {
            "branch": "codex/test",
            "batch_base_sha": SHA_A,
            "integration_head_sha": SHA_A,
        },
        "landing": {
            "mode": "local_only",
            "remote": "origin",
            "pushed_head_sha": None,
            "continuity": None,
        },
        "mission_states": {
            mission_id: {
                "phase": "queued",
                "lease_id": None,
                "lease_plan_revision": None,
                "lease_plan_digest_sha256": None,
                "worker_id": None,
                "base_sha": None,
                "head_sha": None,
                "integration_gate": "planned",
                "integrated_sha": None,
                "blockers": [],
                "report_path": None,
            }
            for mission_id in mission_ids
        },
        "task_states": {
            task_id: {
                "phase": "queued",
                "attempts": 0,
                "commit_sha": None,
                "verifier_status": "planned",
                "blockers": [],
                "refinement_request": None,
            }
            for task_id in task_ids
        },
        "active_wave": {
            "wave_id": None,
            "status": "idle",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "batch_base_sha": None,
            "selected_missions": [],
            "deferred_missions": [],
            "conflict_edges": [],
        },
        "workers": [],
        "review_workers": [],
        "attempt_log": [],
        "batch_gate_results": [
            {"id": gate["id"], "status": "planned", "head_sha": None, "evidence": []}
            for gate in plan["batch_verifiers"]
        ],
        "final_gate_results": [
            {"id": gate["id"], "status": "planned", "head_sha": None, "evidence": []}
            for gate in plan["final_gates"]
        ],
        "ui_evidence": [],
        "verifier_executions": [],
        "graph_state": {
            "graph_revision": plan["revision"],
            "node_states": {
                node["id"]: {
                    "phase": "dormant",
                    "attempts": 0,
                    "last_attempt_id": None,
                    "last_outcome": None,
                    "bound_worker_id": None,
                    "blockers": [],
                }
                for node in plan["graph"]["nodes"]
            },
            "edge_states": {
                edge["id"]: {
                    "status": "dormant",
                    "traversals": 0,
                    "source_attempt_id": None,
                }
                for edge in plan["graph"]["edges"]
            },
        },
    }


def legacy_run(plan: dict[str, object], schema_version: int) -> dict[str, object]:
    """Build a RUN whose body, not only version number, matches an old schema."""
    if schema_version not in {5, 6, 7, 8, 9}:
        raise ValueError("legacy RUN schema must be 5 through 9")
    run = valid_run(valid_plan())
    digest = plan_digest(plan)
    run["schema_version"] = schema_version
    run["plan"] = {
        "id": plan["plan_id"],
        "revision": plan["revision"],
        "digest_sha256": digest,
    }
    run["active_wave"]["plan_revision"] = plan["revision"]
    run["active_wave"]["plan_digest_sha256"] = digest
    run.pop("verifier_executions")
    graph_run = plan["schema_version"] == 4 and schema_version in {8, 9}
    if not graph_run:
        run.pop("graph_state")
        run.pop("review_workers")
    if schema_version != 9:
        run.pop("batch_gate_results")
        run.pop("final_gate_results")
        run.pop("ui_evidence")
    if schema_version == 5:
        run["runtime_capabilities"].pop("runtime_adapter")
    return run


def legacy_graph_run(
    plan: dict[str, object], schema_version: int = 8
) -> dict[str, object]:
    if plan.get("schema_version") != 4 or schema_version not in {8, 9}:
        raise ValueError("legacy graph RUN requires PLAN v4 with RUN v8 or v9")
    run = valid_run(plan)
    run["schema_version"] = schema_version
    run.pop("verifier_executions")
    if schema_version == 8:
        run.pop("batch_gate_results")
        run.pop("final_gate_results")
        run.pop("ui_evidence")
    return run


def mark_legacy_complete(plan: dict[str, object], run: dict[str, object]) -> None:
    """Complete a legacy RUN without adding RUN-v10 verifier executions."""
    run["status"] = "complete"
    run["intent"] = "plan-then-execute"
    run["plan_readiness"] = "ready"
    for state in run["mission_states"].values():
        state["phase"] = "integrated"
        state["integration_gate"] = "PASS"
        state["integrated_sha"] = run["integration"]["integration_head_sha"]
    for state in run["task_states"].values():
        state["phase"] = "mission_recorded"
        state["verifier_status"] = "PASS"
    for results in (
        run.get("batch_gate_results", []),
        run.get("final_gate_results", []),
    ):
        for result in results:
            result["status"] = "PASS"
            result["head_sha"] = run["integration"]["integration_head_sha"]
            result["evidence"] = ["gate passed"]
    run["landing"]["continuity"] = {
        "status": "preserved",
        "branch_ref": "refs/heads/"
        + run["integration"]["branch"].removeprefix("refs/heads/"),
        "head_sha": run["integration"]["integration_head_sha"],
        "reason": None,
    }


def valid_closeout_run(plan: dict[str, object]) -> dict[str, object]:
    """The canonical RUN staged for closeout: local-only, gates still planned."""
    run = valid_run(plan)
    run["landing"]["mode"] = "local_only"
    return run


def mark_complete(plan: dict[str, object], run: dict[str, object]) -> None:
    digest = plan_digest(plan)
    integration_head = run["integration"]["integration_head_sha"]
    batch_base = run["integration"]["batch_base_sha"]
    mission_ids = [mission["id"] for mission in plan["missions"]]
    worker_heads = {
        mission_id: head
        for mission_id, head in zip(mission_ids, (SHA_B, SHA_C), strict=True)
    }
    integrated_heads = {
        mission_id: head
        for mission_id, head in zip(
            mission_ids,
            (SHA_D, integration_head),
            strict=True,
        )
    }
    authorize_execution(run, mission_ids, status="complete")
    run["runtime_capabilities"].update(
        {
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": len(mission_ids),
            "runtime_adapter": {
                "provider": "codex",
                "available_drivers": ["subagents", "sequential_parent"],
                "detection_source": "fallback",
            },
        }
    )
    run["observed"]["runtime"].update(
        {
            "available_worker_slots": len(mission_ids),
            "isolation_capacity": len(mission_ids),
        }
    )
    graph_state = run.get("graph_state")
    if isinstance(graph_state, dict):
        node_attempts: dict[str, str] = {}
        mission_nodes: dict[str, dict[str, object]] = {}
        review_nodes: list[dict[str, object]] = []
        for index, node in enumerate(plan["graph"]["nodes"], start=1):
            node_id = node["id"]
            attempt_id = f"ATT-{index:02d}-{node_id}"
            node_attempts[node_id] = attempt_id
            state = graph_state["node_states"][node_id]
            state.update(
                {
                    "phase": "succeeded",
                    "attempts": 1,
                    "last_attempt_id": attempt_id,
                    "last_outcome": "pass",
                }
            )
            if node["kind"] == "mission":
                mission_nodes[node["ref"]] = node
                state["bound_worker_id"] = f"W-{node['ref']}"
            elif node["executor"] == "runtime_worker":
                review_nodes.append(node)
                state["bound_worker_id"] = f"RW-{node_id}"
        for edge in plan["graph"]["edges"]:
            graph_state["edge_states"][edge["id"]].update(
                {
                    "status": "traversed",
                    "traversals": 1,
                    "source_attempt_id": node_attempts[edge["from"]],
                }
            )

        run["workers"] = []
        for mission_id, node in mission_nodes.items():
            worker_id = f"W-{mission_id}"
            lease_id = f"LEASE-{mission_id}"
            worktree_path = f"C:/repo/worktrees/{mission_id.lower()}"
            branch_ref = f"refs/heads/codex/{mission_id.lower()}"
            worker_head = worker_heads[mission_id]
            run["workers"].append(
                {
                    "worker_id": worker_id,
                    "mission_id": mission_id,
                    "lease_id": lease_id,
                    "plan_revision": plan["revision"],
                    "plan_digest_sha256": digest,
                    "batch_base_sha": batch_base,
                    "worker_runtime": "subagent",
                    "workspace_mode": "parent_managed_worktree",
                    "completion_channel": "agent_result",
                    "runtime_binding": {
                        "provider": "codex",
                        "driver": "subagents",
                        "source": "host",
                        "model": None,
                        "reasoning_effort": None,
                        "option_source": "provider_default",
                    },
                    "task_thread_id": None,
                    "worktree_path": worktree_path,
                    "branch_ref": branch_ref,
                    "report_path": None,
                    "phase": "worker_passed",
                    "worker_head_sha": worker_head,
                }
            )
            run["observed"]["git"]["worktrees"].append(
                {
                    "path": worktree_path,
                    "branch_ref": branch_ref,
                    "head_sha": worker_head,
                    "managed_by": "parent",
                    "dirty": False,
                }
            )
            run["mission_states"][mission_id].update(
                {
                    "phase": "integrated",
                    "lease_id": lease_id,
                    "lease_plan_revision": plan["revision"],
                    "lease_plan_digest_sha256": digest,
                    "worker_id": worker_id,
                    "base_sha": batch_base,
                    "head_sha": worker_head,
                    "integration_gate": "PASS",
                    "integrated_sha": integrated_heads[mission_id],
                }
            )
            run["attempt_log"].append(
                {
                    "attempt_id": node_attempts[node["id"]],
                    "mission_id": mission_id,
                    "task_id": None,
                    "lease_id": lease_id,
                    "kind": "worker_verifier",
                    "result": "PASS",
                    "evidence": [],
                }
            )

        run["review_workers"] = []
        for node in review_nodes:
            review = node["review"]
            mission_id = review["mission_ids"][0]
            node_id = node["id"]
            mission_worker = next(
                worker
                for worker in run["workers"]
                if worker["mission_id"] == mission_id
            )
            run["review_workers"].append(
                {
                    "worker_id": f"RW-{node_id}",
                    "node_id": node_id,
                    "attempt_id": node_attempts[node_id],
                    "plan_revision": plan["revision"],
                    "plan_digest_sha256": digest,
                    "graph_revision": graph_state["graph_revision"],
                    "reviewed_sha": run["mission_states"][mission_id]["head_sha"],
                    "review_path": mission_worker["worktree_path"],
                    "worker_runtime": "parent",
                    "completion_channel": "agent_result",
                    "runtime_binding": {
                        "provider": "codex",
                        "driver": "sequential_parent",
                        "source": "host",
                        "model": None,
                        "reasoning_effort": None,
                        "option_source": "provider_default",
                    },
                    "task_thread_id": None,
                    "report_path": None,
                    "phase": "worker_passed",
                    "outcome": "pass",
                    "findings": [],
                }
            )

    worker_paths = [
        f"worktree:{worker['worktree_path']}" for worker in run["workers"]
    ]
    worker_branches = [
        f"branch:{worker['branch_ref']}" for worker in run["workers"]
    ]
    worker_targets = [f"worker:{worker['worker_id']}" for worker in run["workers"]]
    authorize_action(
        run,
        "spawn_subagents",
        mission_ids,
        worker_targets,
    )
    authorize_action(
        run,
        "create_local_worktrees",
        mission_ids,
        worker_paths,
    )
    authorize_action(
        run,
        "create_local_branches",
        mission_ids,
        worker_branches,
    )
    authorize_action(
        run,
        "create_local_commits",
        mission_ids,
        worker_branches,
    )
    authorize_action(
        run,
        "integrate_locally",
        mission_ids,
        [f"branch:{run['integration']['branch']}"],
    )

    superseded = {
        item["id"]
        for current_mission in plan["missions"]
        for item in current_mission["tasks"]
        if item["replaced_by"]
    }
    for task_id, state in run["task_states"].items():
        state["phase"] = "superseded" if task_id in superseded else "mission_recorded"
        state["verifier_status"] = "PASS"
        if state["phase"] == "mission_recorded":
            mission_id = task_id.split("/", 1)[0]
            worker = next(
                worker
                for worker in run["workers"]
                if worker["mission_id"] == mission_id
            )
            state["commit_sha"] = worker["worker_head_sha"]
            attempt_id = f"ATT-{task_id.replace('/', '-')}"
            run["attempt_log"].append(
                {
                    "attempt_id": attempt_id,
                    "mission_id": mission_id,
                    "task_id": task_id,
                    "lease_id": worker["lease_id"],
                    "kind": "task_verifier",
                    "result": "PASS",
                    "evidence": [],
                }
            )

    execution_index = 1
    for mission in plan["missions"]:
        mission_id = mission["id"]
        worker = next(
            worker
            for worker in run["workers"]
            if worker["mission_id"] == mission_id
        )
        worker_attempt = next(
            attempt
            for attempt in run["attempt_log"]
            if attempt["mission_id"] == mission_id and attempt["task_id"] is None
        )
        for task_declaration in mission["tasks"]:
            task_id = task_declaration["id"]
            if run["task_states"][task_id]["phase"] != "mission_recorded":
                continue
            task_attempt = next(
                attempt
                for attempt in run["attempt_log"]
                if attempt["task_id"] == task_id
            )
            for declaration in task_declaration["verifiers"]:
                run["verifier_executions"].append(
                    retained_gate_execution(
                        plan,
                        run,
                        declaration,
                        layer="task",
                        execution_id=f"EXEC-TASK-{execution_index:02d}",
                        mission_id=mission_id,
                        task_id=task_id,
                        attempt_id=task_attempt["attempt_id"],
                        lease_id=worker["lease_id"],
                        head_sha=worker["worker_head_sha"],
                        checkout_role="worker",
                    )
                )
                execution_index += 1
        for declaration in mission["worker_verifiers"]:
            run["verifier_executions"].append(
                retained_gate_execution(
                    plan,
                    run,
                    declaration,
                    layer="worker",
                    execution_id=f"EXEC-WORKER-{execution_index:02d}",
                    mission_id=mission_id,
                    attempt_id=worker_attempt["attempt_id"],
                    lease_id=worker["lease_id"],
                    head_sha=worker["worker_head_sha"],
                    checkout_role="worker",
                )
            )
            execution_index += 1
        for declaration in mission["integration_verifiers"]:
            run["verifier_executions"].append(
                retained_gate_execution(
                    plan,
                    run,
                    declaration,
                    layer="mission_integration",
                    execution_id=f"EXEC-INTEGRATION-{execution_index:02d}",
                    mission_id=mission_id,
                    head_sha=run["mission_states"][mission_id]["integrated_sha"],
                )
            )
            execution_index += 1

    for layer, plan_key, run_key in (
        ("batch", "batch_verifiers", "batch_gate_results"),
        ("final", "final_gates", "final_gate_results"),
    ):
        for index, (declaration, result) in enumerate(
            zip(plan[plan_key], run.get(run_key, [])),
            start=1,
        ):
            execution = retained_gate_execution(
                plan,
                run,
                declaration,
                layer=layer,
                execution_id=f"EXEC-{layer.upper()}-{index:02d}",
            )
            run["verifier_executions"].append(execution)
            result["status"] = "PASS"
            result["head_sha"] = integration_head
            result["evidence"] = [execution["evidence_key"]]
    # A complete run keeps its branch at the head it verified, so the user can
    # read it and land it.
    run["landing"]["continuity"] = {
        "status": "preserved",
        "branch_ref": "refs/heads/" + run["integration"]["branch"].removeprefix("refs/heads/"),
        "head_sha": run["integration"]["integration_head_sha"],
        "reason": None,
    }


def retained_gate_execution(
    plan: dict[str, object],
    run: dict[str, object],
    declaration: dict[str, object],
    *,
    layer: str,
    execution_id: str,
    mission_id: str | None = None,
    task_id: str | None = None,
    attempt_id: str | None = None,
    lease_id: str | None = None,
    head_sha: str | None = None,
    checkout_role: str = "integration",
) -> dict[str, object]:
    changed_files: list[str] = []
    execution_head = head_sha or run["integration"]["integration_head_sha"]
    context = {
        "run_id": run["run_id"],
        "plan_revision": run["plan"]["revision"],
        "plan_digest_sha256": run["plan"]["digest_sha256"],
        "graph_revision": run["graph_state"]["graph_revision"],
        "batch_base_sha": run["integration"]["batch_base_sha"],
        "head_sha": execution_head,
        "changed_files": changed_files,
        "trust_domain": "parent_local",
        "checkout_role": checkout_role,
        "checkout_dirty": False,
        "cache_safe": False,
        "layer": layer,
        "mission_id": mission_id,
        "task_id": task_id,
        "attempt_id": attempt_id,
        "lease_id": lease_id,
    }
    declared_cache = declaration.get(
        "cache",
        {"mode": "disabled", "environment_keys": []},
    )
    normalized_verifier = {
        "id": declaration["id"],
        "cwd": declaration["cwd"],
        "argv": declaration["argv"],
        "pass_signal": declaration["pass_signal"],
        "cache": declared_cache,
    }
    key_document = {
        "protocol": "harness-verifier-execution-v1",
        "verifier_id": declaration["id"],
        "layer": layer,
        "mission_id": mission_id,
        "task_id": task_id,
        "attempt_id": attempt_id,
        "lease_id": lease_id,
        "run_id": context["run_id"],
        "plan_revision": context["plan_revision"],
        "plan_digest_sha256": context["plan_digest_sha256"],
        "graph_revision": context["graph_revision"],
        "batch_base_sha": context["batch_base_sha"],
        "head_sha": context["head_sha"],
        "changed_files_digest": hashlib.sha256(b"[]").hexdigest(),
        "trust_domain": context["trust_domain"],
        "checkout_role": context["checkout_role"],
        "checkout_dirty": context["checkout_dirty"],
        "cache_safe": context["cache_safe"],
        "cwd": declaration["cwd"],
        "argv": declaration["argv"],
        "pass_signal": declaration["pass_signal"],
        "cache_mode": declared_cache["mode"],
        "environment_keys": sorted(declared_cache["environment_keys"]),
        "platform": {"system": "test", "machine": "test"},
        "executable_identity": {
            "path": "C:/python",
            "size": 1,
            "mtime_ns": 1,
            "device": 1,
            "inode": 1,
        },
        "environment_digests": {},
    }
    execution_key = hashlib.sha256(
        json.dumps(
            key_document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    empty_digest = hashlib.sha256(b"").hexdigest()
    return {
        "execution_id": execution_id,
        "verifier_id": declaration["id"],
        "layer": layer,
        "mission_id": mission_id,
        "task_id": task_id,
        "attempt_id": attempt_id,
        "lease_id": lease_id,
        "protocol": "harness-verifier-execution-v1",
        "execution_key": execution_key,
        "evidence_key": execution_key,
        "key_document": key_document,
        "verifier": normalized_verifier,
        "context": context,
        "status": "PASS",
        "exit_code": 0,
        "cache_status": "bypassed",
        "cache_reason": "cache_disabled",
        "duration_ms": 1,
        "metrics": {"executed": 1, "reused": 0},
        "stdout_sha256": empty_digest,
        "stderr_sha256": empty_digest,
        "evidence_paths": [],
    }








def authorize_execution(
    run: dict[str, object],
    mission_ids: list[str],
    *,
    status: str = "running",
    plan: dict[str, object] | None = None,
    digest: str | None = None,
) -> None:
    """Authorize execution for exactly `mission_ids`.

    The scope always binds the plan revision and digest the RUN records, since
    v10 requires it. `plan`/`digest` override that for the drift tests.
    """
    run_plan = run.get("plan", {})
    scope: dict[str, object] = {
        "run_id": run["run_id"],
        "plan_revision": plan["revision"] if plan is not None else run_plan.get("revision"),
        "plan_digest_sha256": digest if digest is not None else run_plan.get("digest_sha256"),
        "mission_ids": mission_ids,
        "expires_when": "run_complete",
    }
    # An authorized run must keep its branch, so continuity is planned by then.
    continuity = run.get("landing", {}).get("continuity")
    if continuity is None:
        run["landing"]["continuity"] = {
            "status": "planned",
            "branch_ref": "refs/heads/" + run["integration"]["branch"].removeprefix("refs/heads/"),
            "head_sha": None,
            "reason": None,
        }
    run.update(
        {
            "status": status,
            "intent": "plan-then-execute",
            "plan_readiness": "ready",
            "execution_authorized": True,
            "execution_authorization_source": "user requested execution",
            "execution_authorization_scope": scope,
        }
    )


def authorize_action(
    run: dict[str, object],
    action: str,
    mission_ids: list[str],
    targets: list[str],
) -> None:
    run["authorizations"][action] = {
        "authorized": True,
        "source": "user requested lifecycle action",
        "scope": {
            "run_id": run["run_id"],
            "plan_revision": run["plan"]["revision"],
            "plan_digest_sha256": run["plan"]["digest_sha256"],
            "mission_ids": mission_ids,
            "targets": targets,
        },
        "expires_when": "run_complete",
    }
















def markdown(heading: str, wrapper: str, value: dict[str, object]) -> str:
    payload = json.dumps({wrapper: value}, indent=2, ensure_ascii=False)
    return f"# Fixture\n\n{heading}\n\n```json\n{payload}\n```\n"


class ManifestExtractionTests(unittest.TestCase):
    def test_loads_unique_exact_plan_and_run_manifests(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "PLAN.md"
            run_path = root / "RUN.md"
            plan_path.write_text(
                markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path.write_text(
                markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            self.assertEqual(load_plan(plan_path), plan)
            self.assertEqual(load_run(run_path), run)

    def test_rejects_wrong_heading_malformed_json_and_duplicate_heading(self) -> None:
        cases = (
            "## Harness Plan Manifest extra\n\n```json\n{}\n```\n",
            "## Harness Plan Manifest\n\n```json\n{broken\n```\n",
            (
                "## Harness Plan Manifest\n\n```json\n{\"harness_plan\": {}}\n```\n"
                "## Harness Plan Manifest\n\n```json\n{\"harness_plan\": {}}\n```\n"
            ),
            "## Harness Plan Manifest\n\nprose\n```json\n{}\n```\n",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "PLAN.md"
            for content in cases:
                with self.subTest(content=content[:40]):
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaises(ManifestError):
                        load_plan(path)


class DigestTests(unittest.TestCase):
    def test_semantic_set_reordering_is_stable(self) -> None:
        original = valid_plan()
        reordered = copy.deepcopy(original)
        reordered["sources"].reverse()
        reordered["traces"].reverse()
        reordered["missions"].reverse()
        for current_mission in reordered["missions"]:
            current_mission["tasks"].reverse()
            current_mission["runtime_resources"].reverse()
            current_mission["serialized_resources"].reverse()
            current_mission["trace_ids"].reverse()
        self.assertEqual(plan_digest(original), plan_digest(reordered))

    def test_argv_order_is_semantic(self) -> None:
        original = valid_plan()
        changed = copy.deepcopy(original)
        changed["batch_verifiers"][0]["argv"].reverse()
        self.assertNotEqual(plan_digest(original), plan_digest(changed))


class PlanValidationTests(unittest.TestCase):
    def assert_error_contains(self, plan: dict[str, object], fragment: str) -> None:
        errors = validate_plan(plan)
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected {fragment!r} in {errors!r}",
        )

    def test_valid_plan_and_topological_levels(self) -> None:
        plan = valid_plan()
        self.assertEqual(validate_plan(plan), [])
        self.assertEqual(topological_levels(plan), {"M1": 0, "M2": 1})

    def test_planned_trace_needs_a_verification_row_not_just_a_task(self) -> None:
        # contract-and-traceability.md requires every must-have trace to have a
        # downstream task AND a verification row. Task coverage alone let an
        # implemented-but-unverified contract reach closeout as covered.
        plan = valid_plan()
        self.assertEqual(validate_plan(plan), [])

        for task_entry in plan["missions"][0]["tasks"]:
            task_entry["acceptance_matrix"] = []
        self.assert_error_contains(plan, "planned trace has no verification row")

        # One task carrying the trace with a real acceptance matrix is enough.
        plan["missions"][0]["tasks"][0]["acceptance_matrix"] = [
            {
                "test_id": "TEST-M1-01",
                "trace_ids": ["REQ-001"],
                "criterion": "M1/T01 passes",
            }
        ]
        self.assertEqual(validate_plan(plan), [])

    def test_required_skills_accepts_empty_and_populated_lists(self) -> None:
        plan = valid_plan()
        self.assertEqual(validate_plan(plan), [])
        plan["missions"][0]["required_skills"] = ["frontend-design", "feature-dev"]
        self.assertEqual(validate_plan(plan), [])

    def test_product_design_builder_requires_frontend_design(self) -> None:
        plan = valid_plan()
        plan["missions"][0]["required_skills"] = ["product-design-builder"]
        self.assert_error_contains(plan, "frontend-design")

        plan = valid_plan()
        plan["missions"][0]["required_skills"] = [
            "product-design-builder",
            "frontend-design",
        ]
        self.assertEqual(validate_plan(plan), [])

        plan = valid_plan()
        plan["missions"][0]["required_skills"] = ["frontend-design"]
        self.assertEqual(validate_plan(plan), [])

    def test_design_source_write_scope_requires_the_exact_skill_pair(self) -> None:
        plan = valid_plan()
        design_scopes = [
            "docs/product/wireframes.md",
            "docs/product/design-system.md",
            "docs/product/design-system.json",
        ]
        mission = plan["missions"][0]
        mission["write_scope"] = design_scopes
        mission["tasks"][0]["write_scope"] = [design_scopes[0]]
        mission["tasks"][1]["write_scope"] = [design_scopes[1]]
        for node in plan["graph"]["nodes"]:
            review = node.get("review")
            if isinstance(review, dict) and review.get("mission_ids") == ["M1"]:
                review["scope"] = design_scopes

        self.assert_error_contains(plan, "design-source write scope must include both")

        mission["required_skills"] = ["product-design-builder", "frontend-design"]
        self.assertEqual(validate_plan(plan), [])

        mission["required_skills"] = ["frontend-design"]
        self.assert_error_contains(plan, "design-source write scope must include both")

    def test_staged_design_source_write_scope_requires_the_exact_skill_pair(self) -> None:
        for staging_scope in (
            "docs/product/.prd-staging/run-001/**",
            "docs/product/.design-staging/run-001/**",
            "docs/product/.prd-staging/run-001/wireframes.md",
            "docs/product/.prd-staging/run-001/design-system.md",
            "docs/product/.prd-staging/run-001/design-system.json",
        ):
            with self.subTest(staging_scope=staging_scope):
                plan = valid_plan()
                mission = plan["missions"][0]
                mission["write_scope"].append(staging_scope)

                self.assert_error_contains(
                    plan, "design-source write scope must include both"
                )

                mission["required_skills"] = [
                    "product-design-builder",
                    "frontend-design",
                ]
                self.assertEqual(validate_plan(plan), [])

        plan = valid_plan()
        plan["missions"][0]["write_scope"].append(
            "docs/product/.prd-staging/run-001/PRD.md"
        )
        self.assertEqual(validate_plan(plan), [])

    def test_required_skills_rejects_non_list_and_missing_key(self) -> None:
        plan = valid_plan()
        plan["missions"][0]["required_skills"] = "frontend-design"
        self.assert_error_contains(plan, "required_skills")
        plan = valid_plan()
        del plan["missions"][0]["required_skills"]
        self.assert_error_contains(plan, "missing keys: required_skills")

    def test_targeted_verifier_metadata_is_bounded(self) -> None:
        plan = valid_plan()
        task_verifier = plan["missions"][0]["tasks"][0]["verifiers"][0]
        task_verifier["selection"] = {
            "mode": "changed_files",
            "scopes": ["src/a/one.py"],
        }
        task_verifier["cache"] = {
            "mode": "session_exact",
            "environment_keys": ["CI"],
        }
        worker_verifier = plan["missions"][0]["worker_verifiers"][0]
        worker_verifier["selection"] = {
            "mode": "changed_files",
            "scopes": ["src/a/**"],
        }
        self.assertEqual(validate_plan(plan), [])

        escaped = copy.deepcopy(plan)
        escaped["missions"][0]["tasks"][0]["verifiers"][0]["selection"][
            "scopes"
        ] = ["src/ab/**"]
        self.assert_error_contains(escaped, "escapes the owning write scope")

        integration = copy.deepcopy(plan)
        integration["missions"][0]["integration_verifiers"][0]["selection"] = {
            "mode": "changed_files",
            "scopes": ["src/a/**"],
        }
        self.assert_error_contains(
            integration,
            "changed_files is allowed only for task and worker verifiers",
        )

        cached_nonzero = copy.deepcopy(plan)
        cached_nonzero["missions"][0]["tasks"][0]["verifiers"][0][
            "pass_signal"
        ] = "custom success"
        self.assert_error_contains(
            cached_nonzero,
            "session_exact requires the literal pass signal exit 0",
        )


    def test_integration_batch_and_final_verifiers_cannot_use_session_cache(self) -> None:
        cache = {"mode": "session_exact", "environment_keys": []}

        batch_plan = valid_plan()
        batch_plan["batch_verifiers"][0]["cache"] = cache
        self.assert_error_contains(
            batch_plan, "session_exact is not allowed for this verifier"
        )

        final_plan = valid_plan()
        final_plan["final_gates"][0]["cache"] = cache
        self.assert_error_contains(
            final_plan, "session_exact is not allowed for this verifier"
        )

        integration_plan = valid_plan()
        integration_plan["missions"][0]["integration_verifiers"][0]["cache"] = cache
        self.assert_error_contains(
            integration_plan, "session_exact is not allowed for this verifier"
        )

        worker_plan = valid_plan()
        worker_plan["missions"][0]["worker_verifiers"][0]["cache"] = cache
        self.assertEqual(validate_plan(worker_plan), [])











    def test_strict_unknown_keys(self) -> None:
        plan = valid_plan()
        plan["unexpected"] = True
        self.assert_error_contains(plan, "unknown keys: unexpected")

        plan = valid_plan()
        plan["missions"][0]["tasks"][0]["unexpected"] = True
        self.assert_error_contains(plan, "unknown keys: unexpected")

    def test_mission_and_task_cycles(self) -> None:
        plan = valid_plan()
        reverse_edge = copy.deepcopy(
            next(
            edge
            for edge in plan["graph"]["edges"]
            if edge["from"] == "N-M1" and edge["to"] == "N-M2"
            )
        )
        reverse_edge.update(
            {
                "id": "E-M2-M1",
                "from": "N-M2",
                "to": "N-M1",
            }
        )
        plan["graph"]["edges"].append(reverse_edge)
        self.assert_error_contains(plan, "dependency cycle includes N-M1, N-M2")

        plan = valid_plan()
        plan["missions"][0]["tasks"][0]["depends_on"] = ["M1/T02"]
        self.assert_error_contains(plan, "dependency cycle includes M1/T01, M1/T02")

        plan = legacy_plan()
        plan["missions"][0]["depends_on"] = ["M2"]
        self.assert_error_contains(plan, "dependency cycle includes M1, M2")

    def test_task_dependency_must_stay_in_mission(self) -> None:
        plan = valid_plan()
        plan["missions"][1]["tasks"][0]["depends_on"] = ["M1/T02"]
        self.assert_error_contains(plan, "cross-mission task dependency is forbidden")

    def test_dependency_cannot_target_superseded_task(self) -> None:
        plan = valid_plan()
        tasks = plan["missions"][0]["tasks"]
        parent = tasks[0]
        child = task("M1", 3, "REQ-001", "src/a/three.py")
        parent["replaced_by"] = ["M1/T03"]
        child["parent_task"] = "M1/T01"
        child["split_reason"] = "Bound the worker result"
        child["refinement_generation"] = 1
        tasks.append(child)
        self.assert_error_contains(plan, "cannot target superseded task 'M1/T01'")

    def test_refinement_generation_is_bounded(self) -> None:
        plan = valid_plan()
        plan["missions"][0]["tasks"][0]["refinement_generation"] = 2
        self.assert_error_contains(plan, "must be 0 or 1")

    def test_scope_grammar_and_boundary(self) -> None:
        self.assertTrue(scope_overlap("src/a/**", "src/a/file.py"))
        self.assertFalse(scope_overlap("src/a/**", "src/ab/**"))
        self.assertIsNone(validate_scope_claim("src/a/**"))
        self.assertIsNotNone(validate_scope_claim("src/*/file.py"))
        self.assertIsNotNone(validate_scope_claim("../outside/**"))

        plan = valid_plan()
        plan["missions"][0]["write_scope"] = ["src/*/bad.py"]
        self.assert_error_contains(plan, "only one terminal /** wildcard is supported")

    def test_case_serialized_and_runtime_conflicts(self) -> None:
        left = copy.deepcopy(valid_plan()["missions"][0])
        right = copy.deepcopy(valid_plan()["missions"][1])
        left["write_scope"] = ["Src/Case/**"]
        right["write_scope"] = ["src/case/**"]
        self.assertIn("case_scope_collision", mission_conflicts(left, right))

        left["write_scope"] = ["src/left/**"]
        right["write_scope"] = ["src/right/**"]
        left["serialized_resources"] = ["migration:primary"]
        right["serialized_resources"] = ["migration:primary"]
        self.assertIn("serialized_resource_conflict", mission_conflicts(left, right))

        left["serialized_resources"] = []
        right["serialized_resources"] = []
        left["runtime_resources"] = [{"key": "db:test", "access": "shared_read"}]
        right["runtime_resources"] = [{"key": "db:test", "access": "shared_read"}]
        self.assertNotIn("runtime_resource_conflict", mission_conflicts(left, right))
        right["runtime_resources"][0]["access"] = "exclusive"
        self.assertIn("runtime_resource_conflict", mission_conflicts(left, right))

    def test_incomplete_inventory_is_explicit_but_schema_valid(self) -> None:
        plan = valid_plan()
        plan["missions"][0]["resource_inventory_complete"] = False
        self.assertEqual(validate_plan(plan), [])

        plan["missions"][0]["resource_inventory_complete"] = "unknown"
        self.assert_error_contains(plan, "resource_inventory_complete: must be boolean")


class RunValidationTests(unittest.TestCase):
    def assert_run_error_contains(
        self, plan: dict[str, object], run: dict[str, object], fragment: str
    ) -> None:
        errors = validate_run(plan, run)
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected {fragment!r} in {errors!r}",
        )

    def test_matching_plan_run_digest(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        self.assertEqual(validate_run(plan, run), [])

        run["plan"]["digest_sha256"] = "0" * 64
        self.assert_run_error_contains(plan, run, "does not match semantic PLAN digest")


    def test_integration_retention_accepts_known_values_only(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        self.assertEqual(validate_run(plan, run), [])

        run["integration"]["retention"] = "persistent"
        self.assertEqual(validate_run(plan, run), [])

        run["integration"]["retention"] = "ephemeral"
        self.assertEqual(validate_run(plan, run), [])

        run["integration"]["retention"] = None
        self.assertEqual(validate_run(plan, run), [])

        run["integration"]["retention"] = "forever"
        self.assert_run_error_contains(
            plan,
            run,
            "run.integration.retention: must be null, persistent, or ephemeral",
        )


    def test_complete_run_rejects_unfinished_missions_and_tasks(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        run["status"] = "complete"
        run["intent"] = "plan-then-execute"
        run["plan_readiness"] = "ready"
        for results in (run["batch_gate_results"], run["final_gate_results"]):
            for result in results:
                result["status"] = "PASS"
                result["head_sha"] = run["integration"]["integration_head_sha"]
                result["evidence"] = ["gate passed"]

        self.assert_run_error_contains(
            plan, run, "complete run requires every mission to be integrated or superseded"
        )
        self.assert_run_error_contains(
            plan, run, "complete run requires every task to be mission_recorded or superseded"
        )

    def test_complete_run_accepts_current_head_closeout_evidence(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)

        self.assertEqual(validate_run(plan, run), [])

        run["batch_gate_results"][0].update(
            {"status": "planned", "head_sha": None, "evidence": []}
        )
        self.assert_run_error_contains(
            plan, run, "complete run requires every batch gate to PASS"
        )
        run["batch_gate_results"][0].update(
            {"status": "PASS", "head_sha": SHA_A, "evidence": ["gate passed"]}
        )
        run["final_gate_results"][0].update(
            {"status": "planned", "head_sha": None, "evidence": []}
        )
        self.assert_run_error_contains(
            plan, run, "complete run requires every final gate to PASS"
        )

    def test_complete_run_requires_retained_execution_authorization(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        run.update(
            {
                "execution_authorized": False,
                "execution_authorization_source": None,
                "execution_authorization_scope": None,
            }
        )

        self.assert_run_error_contains(
            plan,
            run,
            "complete RUN requires a retained overall execution grant",
        )

    def test_plan_v5_write_worker_rejects_shared_checkout(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        run["workers"][0]["workspace_mode"] = "shared_checkout"

        self.assert_run_error_contains(
            plan,
            run,
            "PLAN-v5 write mission requires an isolated managed worktree",
        )

    def test_recorded_lifecycle_requires_each_exact_action_grant(self) -> None:
        plan = valid_plan()
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
            "integrate_locally",
        ):
            with self.subTest(action=action):
                run = valid_closeout_run(plan)
                mark_complete(plan, run)
                run["authorizations"][action] = {
                    "authorized": False,
                    "source": None,
                }
                errors = validate_run(plan, run)
                self.assertTrue(
                    any(
                        f"run.authorizations.{action}: must exactly authorize"
                        in error
                        for error in errors
                    ),
                    errors,
                )

        app_run = valid_closeout_run(plan)
        mark_complete(plan, app_run)
        app_run["workers"][0]["workspace_mode"] = "app_managed_worktree"
        app_run["observed"]["git"]["worktrees"][0]["managed_by"] = "app"
        self.assert_run_error_contains(
            plan,
            app_run,
            "run.authorizations.create_app_managed_worktrees: must exactly authorize",
        )

        app_task_run = valid_closeout_run(plan)
        mark_complete(plan, app_task_run)
        app_worker = app_task_run["workers"][0]
        app_worker.update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "task_thread_id": "THREAD-M1",
            }
        )
        app_worker["runtime_binding"]["driver"] = "app_threads"
        app_task_run["observed"]["git"]["worktrees"][0]["managed_by"] = "app"
        authorize_action(
            app_task_run,
            "create_app_managed_worktrees",
            ["M1"],
            [f"worktree:{app_worker['worktree_path']}"],
        )
        self.assert_run_error_contains(
            plan,
            app_task_run,
            "run.authorizations.create_user_owned_tasks: must exactly authorize",
        )

    def test_exact_recorded_action_scope_requires_mission_and_target(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        spawn_scope = run["authorizations"]["spawn_subagents"]["scope"]
        spawn_scope["mission_ids"] = ["*"]
        spawn_scope["targets"] = ["*"]
        self.assert_run_error_contains(
            plan,
            run,
            "run.authorizations.spawn_subagents: must exactly authorize",
        )

        exact_with_prelaunch = valid_closeout_run(plan)
        mark_complete(plan, exact_with_prelaunch)
        exact_spawn_scope = exact_with_prelaunch["authorizations"][
            "spawn_subagents"
        ]["scope"]
        exact_spawn_scope["targets"].append("*")
        self.assertEqual([], validate_run(plan, exact_with_prelaunch))

    def test_singleton_preintegration_review_requires_the_mission_worktree(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        run["review_workers"][0]["review_path"] = "C:/repo/other-worktree"

        self.assert_run_error_contains(
            plan,
            run,
            "review_path: must match the singleton mission worker worktree_path",
        )

    def test_mission_integration_evidence_uses_each_integrated_sha(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        self.assertNotEqual(
            run["mission_states"]["M1"]["integrated_sha"],
            run["integration"]["integration_head_sha"],
        )
        declaration = plan["missions"][0]["integration_verifiers"][0]
        original = next(
            execution
            for execution in run["verifier_executions"]
            if execution["verifier_id"] == declaration["id"]
        )
        wrong_head_execution = retained_gate_execution(
            plan,
            run,
            declaration,
            layer="mission_integration",
            execution_id=original["execution_id"],
            mission_id="M1",
            head_sha=run["integration"]["integration_head_sha"],
        )
        run["verifier_executions"] = [
            (
                wrong_head_execution
                if execution["execution_id"] == original["execution_id"]
                else execution
            )
            for execution in run["verifier_executions"]
        ]

        self.assert_run_error_contains(
            plan,
            run,
            "context.head_sha: must match the mission integrated_sha",
        )

    def test_terminal_states_require_task_worker_and_integration_evidence(self) -> None:
        plan = valid_plan()
        for layer, expected in (
            ("task", "missing retained PASS execution for task verifier"),
            ("worker", "missing retained PASS execution for worker verifier"),
            (
                "mission_integration",
                "missing retained PASS execution for mission integration verifier",
            ),
        ):
            with self.subTest(layer=layer):
                run = valid_closeout_run(plan)
                mark_complete(plan, run)
                run["verifier_executions"] = [
                    execution
                    for execution in run["verifier_executions"]
                    if execution["layer"] != layer
                ]
                self.assert_run_error_contains(plan, run, expected)

    def test_passed_gate_results_must_match_the_current_integration_head(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        run["status"] = "running"
        run["batch_gate_results"][0].update(
            {
                "status": "PASS",
                "head_sha": SHA_B,
                "evidence": ["gate passed on an older head"],
            }
        )

        self.assert_run_error_contains(
            plan,
            run,
            "PASS batch gate must match integration_head_sha",
        )

    def test_prior_head_shas_cannot_contain_the_current_integration_head(self) -> None:
        """The head still in use is not a superseded one.

        This rule had no test: disabling it left the whole suite green, which is
        how a later cleanup could delete it without noticing. It also guards the
        shared `integration_prior_heads` name in validate_run, whose first
        binding is the empty-set fallback the check reads when a run records no
        history — split that name and this rule silently stops firing.
        """
        root = SCRIPTS_DIR.parent
        plan = load_plan(root / "assets/templates/HARNESS_PLAN.template.md")
        run = load_run(root / "assets/templates/MISSION_RUNBOOK.template.md")
        run["integration"]["integration_head_sha"] = SHA_A
        run["integration"]["prior_head_shas"] = [SHA_B, SHA_A]

        self.assert_run_error_contains(
            plan,
            run,
            "must contain only superseded integration heads",
        )

        run["integration"]["prior_head_shas"] = [SHA_B]
        self.assertEqual([], validate_run(plan, run))

    def test_complete_run_allows_tasks_of_a_superseded_mission(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        run["mission_states"]["M2"].update(
            {
                "phase": "superseded",
                "integration_gate": "planned",
                "integrated_sha": None,
            }
        )
        run["graph_state"]["node_states"]["N-M2"]["phase"] = "superseded"
        for task in plan["missions"][1]["tasks"]:
            run["task_states"][task["id"]]["phase"] = "superseded"

        self.assertEqual(validate_run(plan, run), [])


    def test_schema_v9_rejects_unhashable_gate_ids_without_crashing(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 9)
        run["batch_gate_results"][0]["id"] = []

        errors = validate_run(plan, run)

        self.assertTrue(any("must be a non-empty string" in error for error in errors))
        self.assertTrue(any("IDs must exactly match" in error for error in errors))

        run = legacy_run(plan, 9)
        run["batch_gate_results"][0]["status"] = []
        errors = validate_run(plan, run)
        self.assertTrue(any(".status: has an unsupported gate value" in error for error in errors))

    def test_schema_v9_rejects_malformed_plan_gate_lists_without_crashing(self) -> None:
        for field in ("batch_verifiers", "final_gates"):
            with self.subTest(field=field):
                plan = legacy_plan()
                run = legacy_run(plan, 9)
                plan[field] = None

                self.assertTrue(validate_plan(plan))
                self.assertTrue(validate_run(plan, run))

    def test_schema_v9_rejects_unhashable_ui_evidence_scalars_without_crashing(self) -> None:
        plan = legacy_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded"],
                "evidence_gate": "required",
            }
        ]
        run = legacy_run(plan, 9)
        run["ui_evidence"] = [
            {
                "surface_id": "dashboard",
                "route": "/dashboard",
                "breakpoint": "desktop",
                "state": "loaded",
                "artifact_path": "docs/goal/evidence/dashboard-desktop-loaded.png",
                "artifact_sha256": "c" * 64,
                "head_sha": run["integration"]["integration_head_sha"],
                "status": "PASS",
            }
        ]

        for field in ("surface_id", "route", "breakpoint", "state", "status"):
            with self.subTest(field=field):
                malformed = copy.deepcopy(run)
                malformed["ui_evidence"][0][field] = []
                errors = validate_run(plan, malformed)
                self.assertTrue(any(f".{field}:" in error for error in errors))

        malformed = copy.deepcopy(run)
        malformed["integration"] = []
        errors = validate_run(plan, malformed)
        self.assertTrue(any("run.integration: must be an object" in error for error in errors))

    def test_schema_v9_rejects_malformed_plan_ui_surfaces_without_crashing(self) -> None:
        plan = legacy_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded"],
                "evidence_gate": "required",
            }
        ]
        evidence = {
            "surface_id": "dashboard",
            "route": "/dashboard",
            "breakpoint": "desktop",
            "state": "loaded",
            "artifact_path": "docs/goal/evidence/dashboard-desktop-loaded.png",
            "artifact_sha256": "c" * 64,
            "head_sha": SHA_A,
            "status": "PASS",
        }

        for missing_field in ("route", "breakpoints", "states"):
            with self.subTest(missing_field=missing_field):
                malformed_plan = copy.deepcopy(plan)
                del malformed_plan["ui_surfaces"][0][missing_field]
                malformed_run = legacy_run(malformed_plan, 9)
                malformed_run["ui_evidence"] = [copy.deepcopy(evidence)]
                self.assertTrue(validate_plan(malformed_plan))
                self.assertTrue(validate_run(malformed_plan, malformed_run))

    def test_complete_run_requires_ready_sources(self) -> None:
        plan = valid_plan()
        plan["sources"][0]["status"] = "missing"
        run = valid_closeout_run(plan)
        mark_complete(plan, run)

        self.assert_run_error_contains(
            plan, run, "complete run requires every source to be frozen or delta accepted"
        )

    def test_complete_run_rejects_malformed_plan_sources_without_crashing(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        plan["sources"] = None

        self.assertTrue(validate_plan(plan))
        self.assertIsInstance(validate_run(plan, run), list)

    def test_na_states_need_no_screenshot_at_closeout(self) -> None:
        """`<state>:n/a` is the documented way to declare an impossible state.

        The design-coverage check strips the suffix, so the closeout matrix has
        to as well — otherwise the only honest way to declare a state a surface
        cannot have is also the one that blocks closeout.
        """
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded", "expired:n/a - session never expires"],
                "evidence_gate": "required",
            }
        ]
        run = valid_closeout_run(plan)
        mark_complete(plan, run)

        errors = validate_run(plan, run)

        self.assertTrue(
            any("missing dashboard|/dashboard|desktop|loaded" in error for error in errors),
            errors,
        )
        self.assertFalse(
            any("expired:n/a" in error for error in errors),
            errors,
        )

    def test_bare_na_marker_is_also_exempt_at_closeout(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded", "expired:n/a"],
                "evidence_gate": "required",
            }
        ]
        run = valid_closeout_run(plan)
        mark_complete(plan, run)

        self.assertFalse(
            any("expired" in error for error in validate_run(plan, run)),
            validate_run(plan, run),
        )

    def test_complete_run_requires_full_ui_screenshot_matrix(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop", "mobile"],
                "states": ["loaded", "empty"],
                "evidence_gate": "required",
            }
        ]
        run = valid_closeout_run(plan)
        mark_complete(plan, run)

        self.assert_run_error_contains(
            plan,
            run,
            "required UI screenshot coverage is missing dashboard|/dashboard|desktop|loaded",
        )

        for breakpoint in ("desktop", "mobile"):
            for state in ("loaded", "empty"):
                run["ui_evidence"].append(
                    {
                        "surface_id": "dashboard",
                        "route": "/dashboard",
                        "breakpoint": breakpoint,
                        "state": state,
                        "artifact_path": (
                            f"docs/goal/evidence/dashboard-{breakpoint}-{state}.png"
                        ),
                        "artifact_sha256": "c" * 64,
                        "head_sha": run["integration"]["integration_head_sha"],
                        "status": "PASS",
                    }
                )
        self.assertEqual(validate_run(plan, run), [])

        run["ui_evidence"][0]["head_sha"] = SHA_B
        self.assert_run_error_contains(
            plan, run, "PASS UI evidence must match integration_head_sha"
        )

    def test_running_ui_evidence_pass_requires_exact_head_sha(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded"],
                "evidence_gate": "required",
            }
        ]
        run = valid_closeout_run(plan)
        run["integration"]["integration_head_sha"] = None
        run["ui_evidence"] = [
            {
                "surface_id": "dashboard",
                "route": "/dashboard",
                "breakpoint": "desktop",
                "state": "loaded",
                "artifact_path": "docs/goal/evidence/dashboard-desktop-loaded.png",
                "artifact_sha256": "c" * 64,
                "head_sha": None,
                "status": "PASS",
            }
        ]

        self.assert_run_error_contains(plan, run, "PASS UI evidence requires head_sha")

    def test_ui_evidence_files_must_exist_and_match_sha256(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded"],
                "evidence_gate": "required",
            }
        ]
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        buffer = io.BytesIO()
        Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
        contents = buffer.getvalue()
        digest = hashlib.sha256(contents).hexdigest()
        run["ui_evidence"] = [
            {
                "surface_id": "dashboard",
                "route": "/dashboard",
                "breakpoint": "desktop",
                "state": "loaded",
                "artifact_path": "docs/goal/evidence/dashboard-desktop-loaded.png",
                "artifact_sha256": digest,
                "head_sha": run["integration"]["integration_head_sha"],
                "status": "PASS",
            }
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "docs" / "goal" / "evidence" / "dashboard-desktop-loaded.png"
            self.assertTrue(
                any("does not exist" in error for error in validate_ui_evidence_files(run, root))
            )
            evidence.parent.mkdir(parents=True)
            evidence.write_bytes(contents)
            self.assertEqual(validate_ui_evidence_files(run, root), [])
            run["ui_evidence"][0]["artifact_sha256"] = "d" * 64
            self.assertTrue(
                any("sha256 does not match" in error for error in validate_ui_evidence_files(run, root))
            )
            invalid_contents = b"not an image"
            evidence.write_bytes(invalid_contents)
            run["ui_evidence"][0]["artifact_sha256"] = hashlib.sha256(
                invalid_contents
            ).hexdigest()
            self.assertTrue(
                any(
                    "cannot be decoded" in error
                    for error in validate_ui_evidence_files(run, root)
                )
            )




    def test_run_schema_v5_remains_compatible(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 5)
        self.assertEqual(validate_run(plan, run), [])

    def test_schema_v6_routes_claude_dynamic_workflow(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 6)
        run["runtime_capabilities"] = {
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": 3,
            "runtime_adapter": {
                "provider": "claude_code",
                "available_drivers": [
                    "dynamic_workflow",
                    "subagents",
                    "sequential_parent",
                ],
                "detection_source": "observed",
            },
            "platform_lifecycle": {
                "owner": "parent",
                "automatic_retention_cleanup_possible": False,
                "durable_branch_required_before_unique_work": True,
            },
        }

        self.assertEqual(validate_run(plan, run), [])
        self.assertEqual(
            route_runtime_driver(run["runtime_capabilities"]),
            "dynamic_workflow",
        )

        run["workers"].append(
            {
                "worker_id": "W1",
                "mission_id": "M1",
                "lease_id": "LEASE-1",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "batch_base_sha": SHA_A,
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "task_thread_id": None,
                "worktree_path": "C:/repo/worktrees/M1",
                "branch_ref": "refs/heads/codex/test-m1",
                "report_path": None,
                "phase": "leased",
                "worker_head_sha": None,
                "nested_subagent_policy": {
                    "enabled": False,
                    "max_children": 0,
                    "allowed_roles": [],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
            }
        )
        self.assert_run_error_contains(
            plan,
            run,
            "must be omitted for flat dynamic-workflow orchestration",
        )



    def test_schema_v6_rejects_provider_driver_and_axis_mismatches(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 6)
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter.update(
            provider="claude_code",
            available_drivers=["app_threads", "sequential_parent"],
            detection_source="observed",
        )
        self.assert_run_error_contains(plan, run, "drivers do not match provider: app_threads")

        adapter["available_drivers"] = ["dynamic_workflow", "sequential_parent"]
        self.assert_run_error_contains(
            plan,
            run,
            "dynamic_workflow requires claude_code subagent/parent_managed_worktree/agent_result",
        )

    def test_schema_v6_rejects_malformed_runtime_adapter_without_crashing(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 6)
        run["runtime_capabilities"]["runtime_adapter"] = None
        self.assert_run_error_contains(
            plan,
            run,
            "run.runtime_capabilities.runtime_adapter: must be an object",
        )

        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": {},
            "available_drivers": ["sequential_parent"],
            "detection_source": [],
        }
        errors = validate_run(plan, run)
        self.assertTrue(any("provider: has an unsupported value" in error for error in errors))
        self.assertTrue(any("detection_source: has an unsupported value" in error for error in errors))
        self.assertEqual(route_runtime_driver(run["runtime_capabilities"]), "sequential_parent")

    def test_runtime_adapter_rejects_external_runtimes_key(self) -> None:
        # The guarded cross-runtime escape hatch (Codex <-> Claude Code) is
        # fully removed: runtime_adapter no longer has any concept of an
        # "external runtime" to record, so the key itself is now unknown.
        plan = valid_plan()
        run = valid_closeout_run(plan)
        self.assertEqual([], validate_run(plan, run))

        run["runtime_capabilities"]["runtime_adapter"]["external_runtimes"] = []
        self.assert_run_error_contains(
            plan,
            run,
            "run.runtime_capabilities.runtime_adapter: unknown keys: external_runtimes",
        )

    def test_worker_runtime_binding_source_must_equal_host(self) -> None:
        # A node's required provider must match whatever host actually runs
        # it: there is no bridged/guarded external source anymore, so
        # runtime_binding.source is exactly "host" or rejected.
        plan = valid_plan()
        run = valid_run(plan)
        digest = plan_digest(plan)
        authorize_execution(run, ["M1"])
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": ["subagents", "sequential_parent"],
                    "detection_source": "fallback",
                },
            }
        )
        worker = {
            "worker_id": "W-M1",
            "mission_id": "M1",
            "lease_id": "LEASE-M1",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "batch_base_sha": SHA_A,
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "runtime_binding": {
                "provider": "codex",
                "driver": "subagents",
                "source": "host",
                "model": None,
                "reasoning_effort": None,
                "option_source": "provider_default",
            },
            "task_thread_id": None,
            "worktree_path": "C:/repo/worktrees/m1",
            "branch_ref": "refs/heads/codex/m1",
            "report_path": None,
            "phase": "leased",
            "worker_head_sha": None,
        }
        run["workers"].append(worker)
        run["observed"]["git"]["worktrees"].append(
            {
                "path": worker["worktree_path"],
                "branch_ref": worker["branch_ref"],
                "head_sha": SHA_A,
                "managed_by": "parent",
                "dirty": False,
            }
        )
        authorize_action(
            run,
            "spawn_subagents",
            ["M1"],
            [f"worker:{worker['worker_id']}"],
        )
        authorize_action(
            run,
            "create_local_worktrees",
            ["M1"],
            [f"worktree:{worker['worktree_path']}"],
        )
        authorize_action(
            run,
            "create_local_branches",
            ["M1"],
            [f"branch:{worker['branch_ref']}"],
        )
        authorize_action(
            run,
            "create_local_commits",
            ["M1"],
            [f"branch:{worker['branch_ref']}"],
        )
        self.assertEqual([], validate_run(plan, run))

        for stale_source in ("external_bridge", "external_agent", "guest", ""):
            with self.subTest(source=stale_source):
                invalid = copy.deepcopy(run)
                invalid["workers"][0]["runtime_binding"]["source"] = stale_source
                self.assert_run_error_contains(
                    plan,
                    invalid,
                    "run.workers[0].runtime_binding.source: has an unsupported value",
                )


































    def test_local_only_landing_rejects_a_pushed_head(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["landing"].update(
            {
                "mode": "local_only",
                "pushed_head_sha": SHA_A,
            }
        )
        self.assert_run_error_contains(
            plan,
            run,
            "local_only mode cannot record a pushed head",
        )

    def test_execution_authorization_requires_source_and_scope(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["execution_authorized"] = True
        self.assert_run_error_contains(run=run, plan=plan, fragment="execution_authorization_source")

        run["execution_authorization_source"] = "user: explicit prompt"
        run["execution_authorization_scope"] = {
            "run_id": "RUN-TEST",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "mission_ids": ["M1", "M2"],
            "expires_when": "run_complete",
        }
        run["landing"]["continuity"] = {
            "status": "planned",
            "branch_ref": "refs/heads/codex/test",
            "head_sha": None,
            "reason": None,
        }
        self.assertEqual(validate_run(plan, run), [])





    def test_action_authorization_requires_scoped_source(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        entry = run["authorizations"]["create_local_commits"]
        entry.update({"authorized": True, "source": "user: explicit prompt"})
        self.assert_run_error_contains(plan, run, "requires scope and expires_when")

        entry["scope"] = {
            "run_id": "RUN-TEST",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "mission_ids": ["M1"],
            "targets": ["branch:codex/test"],
        }
        entry["expires_when"] = "wave_closed"
        self.assertEqual(validate_run(plan, run), [])

        entry["scope"]["targets"] = ["untyped-target"]
        self.assert_run_error_contains(plan, run, "unsupported target 'untyped-target'")

    def test_run_schema_rejects_unknown_key(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["runtime_capabilities"]["unexpected"] = True
        self.assert_run_error_contains(plan, run, "unknown keys: unexpected")

    def test_non_graph_schema_v9_rejects_workflow_runs(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 9)
        run["workflow_runs"] = []
        self.assert_run_error_contains(plan, run, "unknown keys: workflow_runs")

    def test_non_graph_schema_v8_is_rejected(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 8)
        run["workflow_runs"] = []
        errors = validate_run(plan, run)
        self.assertTrue(
            any("schema v8 requires a schema v4 graph PLAN" in error for error in errors)
        )
        self.assertTrue(any("unknown keys: workflow_runs" in error for error in errors))



    def test_permission_boundary_accepts_ready_full_access_and_rejects_unknown_ready(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["runtime_capabilities"]["permission_boundary"] = {
            "selected_mode": "full_access",
            "profile_name": None,
            "approval_policy": "never",
            "filesystem_scope": "unrestricted",
            "network_scope": "open",
            "local_binding": "allowed",
            "worker_inheritance": "inherited",
            "status": "ready",
        }
        self.assertEqual(validate_run(plan, run), [])

        run["runtime_capabilities"]["permission_boundary"]["network_scope"] = "unknown"
        self.assert_run_error_contains(
            plan,
            run,
            "cannot be ready while a boundary field is unknown",
        )

    def test_named_permission_profile_requires_profile_name(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["runtime_capabilities"]["permission_boundary"] = {
            "selected_mode": "named_profile",
            "profile_name": None,
            "approval_policy": "on-request",
            "filesystem_scope": "custom",
            "network_scope": "filtered",
            "local_binding": "allowed",
            "worker_inheritance": "inherited",
            "status": "ready",
        }
        self.assert_run_error_contains(plan, run, "is required for named_profile")

    def test_app_task_accepts_authorized_bounded_nested_subagents(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        digest = plan_digest(plan)
        authorize_execution(run, ["M1"])
        run["runtime_capabilities"] = {
            "worker_runtime": "app_task",
            "workspace_mode": "app_managed_worktree",
            "completion_channel": "thread_poll",
            "max_parallel_workers": 3,
            "runtime_adapter": {
                "provider": "codex",
                "available_drivers": [
                    "app_threads",
                    "subagents",
                    "sequential_parent",
                ],
                "detection_source": "observed",
            },
            "nested_subagents": {
                "available": True,
                "max_depth": 1,
                "max_children_per_worker": 3,
                "allowed_roles": ["explorer", "researcher", "reviewer", "tester"],
                "write_policy": "read_only",
                "completion_channel": "agent_result",
            },
            "platform_lifecycle": {
                "owner": "app",
                "automatic_retention_cleanup_possible": True,
                "durable_branch_required_before_unique_work": True,
            },
        }
        run["authorizations"]["spawn_subagents"] = {
            "authorized": True,
            "source": "user: explicit nested-subagent request",
            "scope": {
                "run_id": "RUN-TEST",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "mission_ids": ["M1"],
                "targets": ["worker:W1"],
            },
            "expires_when": "run_complete",
        }
        run["mission_states"]["M1"].update(
            {
                "phase": "leased",
                "lease_id": "LEASE1",
                "lease_plan_revision": 1,
                "lease_plan_digest_sha256": digest,
                "worker_id": "W1",
                "base_sha": SHA_A,
            }
        )
        run["workers"] = [
            {
                "worker_id": "W1",
                "mission_id": "M1",
                "lease_id": "LEASE1",
                "plan_revision": 1,
                "plan_digest_sha256": digest,
                "batch_base_sha": SHA_A,
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "runtime_binding": {
                    "provider": "codex",
                    "driver": "app_threads",
                    "source": "host",
                    "model": None,
                    "reasoning_effort": None,
                    "option_source": "provider_default",
                },
                "nested_subagent_policy": {
                    "enabled": True,
                    "max_children": 3,
                    "allowed_roles": ["explorer", "reviewer", "tester"],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
                "task_thread_id": "THREAD1",
                "worktree_path": "/tmp/app-m1",
                "branch_ref": "refs/heads/codex/app-m1",
                "report_path": None,
                "phase": "leased",
                "worker_head_sha": None,
            }
        ]
        run["observed"]["git"]["worktrees"] = [
            {
                "path": "/tmp/app-m1",
                "branch_ref": "refs/heads/codex/app-m1",
                "head_sha": SHA_A,
                "managed_by": "app",
                "dirty": False,
            }
        ]
        authorize_action(
            run,
            "create_app_managed_worktrees",
            ["M1"],
            ["worktree:/tmp/app-m1"],
        )
        authorize_action(
            run,
            "create_user_owned_tasks",
            ["M1"],
            ["task:THREAD1"],
        )
        authorize_action(
            run,
            "create_local_branches",
            ["M1"],
            ["branch:refs/heads/codex/app-m1"],
        )
        authorize_action(
            run,
            "create_local_commits",
            ["M1"],
            ["branch:refs/heads/codex/app-m1"],
        )
        self.assertEqual(validate_run(plan, run), [])

        legacy_app_plan = legacy_plan()
        legacy_app_run = legacy_run(legacy_app_plan, 6)
        legacy_digest = plan_digest(legacy_app_plan)
        legacy_app_run["runtime_capabilities"] = copy.deepcopy(
            run["runtime_capabilities"]
        )
        legacy_app_run["authorizations"]["spawn_subagents"] = copy.deepcopy(
            run["authorizations"]["spawn_subagents"]
        )
        legacy_scope = legacy_app_run["authorizations"]["spawn_subagents"]["scope"]
        legacy_scope.pop("plan_revision")
        legacy_scope.pop("plan_digest_sha256")
        legacy_app_run["mission_states"]["M1"].update(
            {
                "phase": "leased",
                "lease_id": "LEASE1",
                "lease_plan_revision": legacy_app_plan["revision"],
                "lease_plan_digest_sha256": legacy_digest,
                "worker_id": "W1",
                "base_sha": SHA_A,
            }
        )
        legacy_worker = copy.deepcopy(run["workers"][0])
        legacy_worker["plan_revision"] = legacy_app_plan["revision"]
        legacy_worker["plan_digest_sha256"] = legacy_digest
        legacy_worker["nested_subagent_policy"]["allowed_roles"] = [
            "explorer",
            "tester",
        ]
        legacy_app_run["workers"] = [legacy_worker]
        self.assertEqual(
            [],
            validate_run(legacy_app_plan, legacy_app_run),
            "legacy RUN v6 keeps its previously valid enabled-role policy",
        )

        del run["workers"][0]["nested_subagent_policy"]
        self.assert_run_error_contains(
            plan,
            run,
            "is required for app_task workers when runtime nested_subagents is recorded",
        )
        run["workers"][0]["nested_subagent_policy"] = {
            "enabled": True,
            "max_children": 3,
            "allowed_roles": ["explorer", "reviewer", "tester"],
            "write_policy": "read_only",
            "completion_channel": "agent_result",
        }

        run["authorizations"]["spawn_subagents"] = {
            "authorized": False,
            "source": None,
        }
        self.assert_run_error_contains(
            plan,
            run,
            "requires matching spawn_subagents authorization",
        )


if __name__ == "__main__":
    unittest.main()

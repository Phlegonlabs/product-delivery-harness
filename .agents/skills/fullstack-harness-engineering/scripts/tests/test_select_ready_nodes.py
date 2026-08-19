#!/usr/bin/env python3
"""Dedicated tests for select_ready_nodes.py."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import (  # noqa: E402
    load_plan,
    load_run,
    plan_digest,
    validate_run,
)
from select_ready_nodes import (  # noqa: E402
    GraphSelectionError,
    _incoming,
    _logical_reasons,
    _preintegration_review_source_ready,
    _required_actions,
    select_ready_nodes,
)
from verifier_runtime import execution_key_from_document  # noqa: E402
from test_graph_orchestration import (  # noqa: E402
    detach_mission_edges,
    valid_graph_plan,
    valid_graph_run,
)
from test_harness_manifest import (  # noqa: E402
    authorize_action,
    authorize_execution,
    codex_capability_probe,
    current_version_gate,
    retained_gate_execution,
)


def retain_current_worker_state(
    plan: dict[str, object],
    run: dict[str, object],
    *,
    managed_by: str = "parent",
) -> None:
    """Bind the recorded worker checkout, grants, and PASS to its current head."""
    worker = run["workers"][0]
    mission_id = worker["mission_id"]
    worktree_action = (
        "create_app_managed_worktrees"
        if managed_by == "app"
        else "create_local_worktrees"
    )
    if worker.get("worker_runtime") == "subagent":
        spawn_entry = run["authorizations"].get("spawn_subagents")
        spawn_scope = (
            spawn_entry.get("scope")
            if isinstance(spawn_entry, dict)
            and spawn_entry.get("authorized") is True
            else None
        )
        retained_targets = (
            spawn_scope.get("targets", [])
            if isinstance(spawn_scope, dict)
            else []
        )
        authorize_action(
            run,
            "spawn_subagents",
            [mission_id],
            list(
                dict.fromkeys(
                    [*retained_targets, f"worker:{worker['worker_id']}"]
                )
            ),
        )
    elif worker.get("worker_runtime") == "app_task":
        task_entry = run["authorizations"].get("create_user_owned_tasks")
        task_scope = (
            task_entry.get("scope")
            if isinstance(task_entry, dict)
            and task_entry.get("authorized") is True
            else None
        )
        retained_targets = (
            task_scope.get("targets", [])
            if isinstance(task_scope, dict)
            else []
        )
        authorize_action(
            run,
            "create_user_owned_tasks",
            [mission_id],
            list(
                dict.fromkeys(
                    [
                        *retained_targets,
                        f"task:{worker['task_thread_id']}",
                    ]
                )
            ),
        )
    run["observed"]["git"]["worktrees"] = [
        {
            "path": worker["worktree_path"],
            "branch_ref": worker["branch_ref"],
            "head_sha": worker["worker_head_sha"],
            "managed_by": managed_by,
            "dirty": False,
        }
    ]
    authorize_action(
        run,
        worktree_action,
        [mission_id],
        [f"worktree:{worker['worktree_path']}"],
    )
    for action in ("create_local_branches", "create_local_commits"):
        authorize_action(
            run,
            action,
            [mission_id],
            [f"branch:{worker['branch_ref']}"],
        )
    attempt_id = f"ATT-WORKER-{mission_id}"
    run["attempt_log"] = [
        attempt
        for attempt in run["attempt_log"]
        if attempt.get("attempt_id") != attempt_id
    ]
    run["attempt_log"].append(
        {
            "attempt_id": attempt_id,
            "mission_id": mission_id,
            "task_id": None,
            "lease_id": worker["lease_id"],
            "kind": "worker_verifier",
            "result": "PASS",
            "evidence": [],
        }
    )
    run["verifier_executions"] = [
        execution
        for execution in run["verifier_executions"]
        if execution.get("layer") != "worker"
    ]
    mission = next(
        mission
        for mission in plan["missions"]
        if mission["id"] == mission_id
    )
    run["verifier_executions"].append(
        retained_gate_execution(
            plan,
            run,
            mission["worker_verifiers"][0],
            layer="worker",
            execution_id=f"EXEC-WORKER-{mission_id}",
            mission_id=mission_id,
            attempt_id=attempt_id,
            lease_id=worker["lease_id"],
            head_sha=worker["worker_head_sha"],
            checkout_role="worker",
        )
    )


def authorized_parent_run(plan: dict[str, object]) -> dict[str, object]:
    run = valid_graph_run(plan)
    authorize_execution(run, ["M1"])
    run["observed"]["captured_at"] = "2026-07-25T00:00:00Z"
    run["observed"]["runtime"].update(
        {"available_worker_slots": 0, "isolation_capacity": 0}
    )
    return run


def current_preintegration_review_state() -> tuple[dict[str, object], dict[str, object]]:
    fixture_root = TESTS_DIR / "fixtures"
    plan = json.loads(
        (fixture_root / "legacy_ui_template_plan.json").read_text(encoding="utf-8")
    )["harness_plan"]
    run = json.loads(
        (fixture_root / "legacy_ui_template_run.json").read_text(encoding="utf-8")
    )["harness_run"]
    digest = plan_digest(plan)
    authorize_execution(run, ["M1"], status="ready", plan=plan, digest=digest)
    run["runtime_capabilities"].update(
        {
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": 2,
            "runtime_adapter": {
                "provider": "codex",
                "available_drivers": ["subagents", "sequential_parent"],
                "detection_source": "observed",
                "capability_probe": codex_capability_probe(subagents=True),
                "version_gate": current_version_gate(),
            },
            "permission_boundary": {
                "selected_mode": "ask_for_approval",
                "profile_name": None,
                "approval_policy": "on-request",
                "filesystem_scope": "workspace",
                "network_scope": "filtered",
                "local_binding": "allowed",
                "worker_inheritance": "inherited",
                "status": "ready",
            },
        }
    )
    run["observed"]["captured_at"] = "2026-07-26T00:00:00Z"
    run["observed"]["runtime"].update(
        {
            "available_worker_slots": 2,
            "isolation_capacity": 2,
            "completion_channel_available": True,
        }
    )
    run["observed"]["git"].update(
        {
            "parent_worktree_path": "C:/repo",
            "parent_branch": "refs/heads/development",
            "parent_head_sha": "a" * 40,
            "parent_dirty": False,
        }
    )
    run["integration"].update(
        {
            "batch_base_sha": "a" * 40,
            "integration_head_sha": "a" * 40,
        }
    )
    run["mission_states"]["M1"].update(
        {
            "phase": "worker_passed",
            "lease_id": "LEASE-M1",
            "lease_plan_revision": plan["revision"],
            "lease_plan_digest_sha256": digest,
            "worker_id": "W-M1",
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "integration_gate": "planned",
            "integrated_sha": None,
        }
    )
    run["workers"] = [
        {
            "worker_id": "W-M1",
            "mission_id": "M1",
            "lease_id": "LEASE-M1",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "batch_base_sha": "a" * 40,
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "runtime_binding": {
                "provider": "codex",
                "driver": "subagents",
                "source": "host",
                "model": "gpt-5.6-sol",
                "reasoning_effort": "high",
                "option_source": "plan_provider_options",
            },
            "task_thread_id": None,
            "worktree_path": "C:/repo/worktrees/M1",
            "branch_ref": "refs/heads/codex/m1",
            "report_path": None,
            "phase": "worker_passed",
            "worker_head_sha": "b" * 40,
        }
    ]
    run["graph_state"]["node_states"]["N-M1"].update(
        {
            "phase": "running",
            "attempts": 1,
            "last_attempt_id": "ATT-M1",
            "last_outcome": None,
            "bound_worker_id": "W-M1",
            "blockers": [],
        }
    )
    run["authorizations"]["spawn_subagents"] = {
        "authorized": True,
        "source": "user authorized review",
        "scope": {
            "run_id": run["run_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "mission_ids": ["M1"],
            "targets": ["*"],
        },
        "expires_when": "run_complete",
    }
    retain_current_worker_state(plan, run)
    return plan, run


def fanout_preintegration_review_state(
) -> tuple[dict[str, object], dict[str, object], str]:
    plan, run = current_preintegration_review_state()
    run["runtime_capabilities"]["max_parallel_workers"] = 3
    run["observed"]["runtime"].update(
        {"available_worker_slots": 3, "isolation_capacity": 3}
    )
    review_node = next(
        node
        for node in plan["graph"]["nodes"]
        if node["id"] == "N-FRONTEND-REVIEW"
    )
    dependency_edge = next(
        edge
        for edge in plan["graph"]["edges"]
        if edge["id"] == "E-M1-FRONTEND-REVIEW"
    )
    pass_route = next(
        edge
        for edge in plan["graph"]["edges"]
        if edge["id"] == "E-FRONTEND-VISUAL-REVIEW"
    )
    for suffix in ("SECOND", "THIRD"):
        review_node_id = f"N-FRONTEND-REVIEW-{suffix}"
        additional_review_node = copy.deepcopy(review_node)
        additional_review_node["id"] = review_node_id
        plan["graph"]["nodes"].append(additional_review_node)

        additional_dependency_edge = copy.deepcopy(dependency_edge)
        additional_dependency_edge["id"] = (
            f"E-M1-FRONTEND-REVIEW-{suffix}"
        )
        additional_dependency_edge["to"] = review_node_id
        plan["graph"]["edges"].append(additional_dependency_edge)

        additional_pass_route = copy.deepcopy(pass_route)
        additional_pass_route["id"] = (
            f"E-FRONTEND-REVIEW-{suffix}-FINAL-GATE"
        )
        additional_pass_route["from"] = review_node_id
        plan["graph"]["edges"].append(additional_pass_route)

        run["graph_state"]["node_states"][review_node_id] = copy.deepcopy(
            run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"]
        )
        run["graph_state"]["edge_states"][
            additional_dependency_edge["id"]
        ] = copy.deepcopy(
            run["graph_state"]["edge_states"]["E-M1-FRONTEND-REVIEW"]
        )
        run["graph_state"]["edge_states"][
            additional_pass_route["id"]
        ] = copy.deepcopy(
            run["graph_state"]["edge_states"]["E-FRONTEND-VISUAL-REVIEW"]
        )

    digest = plan_digest(plan)
    run["plan"]["digest_sha256"] = digest
    run["execution_authorization_scope"]["plan_digest_sha256"] = digest
    run["authorizations"]["spawn_subagents"]["scope"][
        "plan_digest_sha256"
    ] = digest
    run["mission_states"]["M1"]["lease_plan_digest_sha256"] = digest
    run["workers"][0]["plan_digest_sha256"] = digest
    retain_current_worker_state(plan, run)
    return plan, run, digest


def exact_head_review_worker(
    *,
    node_id: str,
    worker_id: str,
    attempt_id: str,
    digest: str,
    plan: dict[str, object],
    run: dict[str, object],
    outcome: str = "pass",
) -> dict[str, object]:
    review_node = next(
        node for node in plan["graph"]["nodes"] if node["id"] == node_id
    )
    reviewed_mission_ids = review_node.get("review", {}).get(
        "mission_ids", []
    )
    review_path = "C:/repo/worktrees/M1"
    if len(reviewed_mission_ids) == 1:
        mission_state = run["mission_states"].get(reviewed_mission_ids[0])
        mission_worker = next(
            (
                worker
                for worker in run["workers"]
                if isinstance(mission_state, dict)
                and worker.get("worker_id") == mission_state.get("worker_id")
            ),
            None,
        )
        if isinstance(mission_worker, dict):
            review_path = mission_worker["worktree_path"]
    return {
        "worker_id": worker_id,
        "node_id": node_id,
        "attempt_id": attempt_id,
        "plan_revision": plan["revision"],
        "plan_digest_sha256": digest,
        "graph_revision": run["graph_state"]["graph_revision"],
        "reviewed_sha": "b" * 40,
        "review_path": review_path,
        "worker_runtime": "subagent",
        "completion_channel": "agent_result",
        "runtime_binding": {
            "provider": "codex",
            "driver": "subagents",
            "source": "host",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "medium",
            "option_source": "plan_provider_options",
        },
        "task_thread_id": None,
        "report_path": None,
        "phase": "worker_passed" if outcome == "pass" else "worker_failed",
        "outcome": outcome,
        "findings": [] if outcome == "pass" else ["src/example/file.ts:1 fix required"],
    }


def configure_flat_app_task(
    plan: dict[str, object],
    run: dict[str, object],
) -> dict[str, object]:
    run["runtime_capabilities"].update(
        {
            "worker_runtime": "app_task",
            "workspace_mode": "app_managed_worktree",
            "completion_channel": "thread_poll",
            "runtime_adapter": {
                "provider": "codex",
                "available_drivers": [
                    "app_threads",
                    "subagents",
                    "sequential_parent",
                ],
                "detection_source": "observed",
                "capability_probe": codex_capability_probe(
                    app_threads=True,
                    subagents=True,
                ),
                "version_gate": current_version_gate(),
            },
            "nested_subagents": {
                "available": True,
                "max_depth": 1,
                "max_children_per_worker": 3,
                "allowed_roles": ["reviewer"],
                "write_policy": "read_only",
                "completion_channel": "agent_result",
            },
            "platform_lifecycle": {
                "owner": "app",
                "automatic_retention_cleanup_possible": True,
                "durable_branch_required_before_unique_work": True,
            },
        }
    )
    worker = run["workers"][0]
    worker.update(
        {
            "worker_runtime": "app_task",
            "workspace_mode": "app_managed_worktree",
            "completion_channel": "thread_poll",
            "task_thread_id": "THREAD-M1",
            "nested_subagent_policy": {
                "enabled": False,
                "max_children": 0,
                "allowed_roles": [],
                "write_policy": "read_only",
                "completion_channel": "agent_result",
            },
        }
    )
    worker["runtime_binding"]["driver"] = "app_threads"
    retain_current_worker_state(plan, run, managed_by="app")
    return worker


class SelectReadyNodesTests(unittest.TestCase):
    def test_integration_stage_review_waits_for_unified_integration(self) -> None:
        plan, run = current_preintegration_review_state()
        review_node = next(
            node for node in plan["graph"]["nodes"]
            if node["id"] == "N-VISUAL-REVIEW"
        )
        run["graph_state"]["node_states"]["N-M1"].update(
            {"phase": "succeeded", "last_outcome": "pass"}
        )
        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
            {"phase": "succeeded", "last_outcome": "pass"}
        )

        before = _logical_reasons(review_node, plan, run, *_incoming(plan))
        self.assertIn("integration_not_unified", before)

        run["mission_states"]["M1"]["phase"] = "integrated"
        run["mission_states"]["M1"]["integrated_sha"] = "c" * 40
        run["integration"]["integration_head_sha"] = "c" * 40
        after = _logical_reasons(review_node, plan, run, *_incoming(plan))
        self.assertNotIn("integration_not_unified", after)

    def test_integration_stage_review_requires_a_fresh_reviewer_identity(self) -> None:
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        run["graph_state"]["node_states"]["N-M1"].update(
            {"phase": "succeeded", "last_outcome": "pass"}
        )
        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-PRE",
                "last_outcome": "pass",
                "bound_worker_id": "RW-PRE",
            }
        )
        pre_review = exact_head_review_worker(
            node_id="N-FRONTEND-REVIEW",
            worker_id="RW-PRE",
            attempt_id="ATT-PRE",
            digest=digest,
            plan=plan,
            run=run,
        )
        run["mission_states"]["M1"].update(
            {"phase": "integrated", "integration_gate": "PASS", "integrated_sha": "c" * 40}
        )
        run["integration"]["integration_head_sha"] = "c" * 40
        run["graph_state"]["node_states"]["N-VISUAL-REVIEW"].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-INTEGRATION",
                "last_outcome": "pass",
                "bound_worker_id": "W-M1",
            }
        )
        integration_review = exact_head_review_worker(
            node_id="N-VISUAL-REVIEW",
            worker_id="W-M1",
            attempt_id="ATT-INTEGRATION",
            digest=digest,
            plan=plan,
            run=run,
        )
        integration_review["reviewed_sha"] = "c" * 40
        integration_review["review_path"] = "C:/repo"
        run["review_workers"] = [pre_review, integration_review]

        errors = validate_run(plan, run)
        self.assertTrue(
            any("must use a fresh reviewer" in error for error in errors),
            errors,
        )

    def _integration_stage_dissent_state(self) -> tuple[dict[str, object], dict[str, object]]:
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        run["mission_states"]["M1"].update(
            {"phase": "integrated", "integration_gate": "PASS", "integrated_sha": "c" * 40}
        )
        run["integration"]["integration_head_sha"] = "c" * 40
        run["graph_state"]["node_states"]["N-VISUAL-REVIEW"].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-INTEGRATION-DISSENT",
                "last_outcome": "pass",
                "bound_worker_id": "RW-INTEGRATION-DISSENT",
            }
        )
        dissent = exact_head_review_worker(
            node_id="N-VISUAL-REVIEW",
            worker_id="RW-INTEGRATION-DISSENT",
            attempt_id="ATT-INTEGRATION-DISSENT",
            digest=digest,
            plan=plan,
            run=run,
            outcome="fix_required",
        )
        dissent["reviewed_sha"] = "c" * 40
        dissent["review_path"] = "C:/repo"
        dissent["phase"] = "worker_passed"
        run["review_workers"] = [dissent]
        return plan, run

    def test_integration_stage_current_dissent_blocks_validation_and_route(self) -> None:
        plan, run = self._integration_stage_dissent_state()

        errors = validate_run(plan, run)
        self.assertTrue(
            any("current review node result must match" in error for error in errors),
            errors,
        )
        review_node = next(
            node for node in plan["graph"]["nodes"] if node["id"] == "N-VISUAL-REVIEW"
        )
        with patch("select_ready_nodes.validate_current_plan_run", return_value=[]):
            reasons = _logical_reasons(review_node, plan, run, *_incoming(plan))
        self.assertIn("review_result_dissent", reasons)

    def test_preintegration_current_pass_findings_block_validation_and_route(self) -> None:
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        review_node = next(
            node for node in plan["graph"]["nodes"] if node["id"] == "N-FRONTEND-REVIEW"
        )
        run["graph_state"]["node_states"][review_node["id"]].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-PRE-FINDINGS",
                "last_outcome": "pass",
                "bound_worker_id": "RW-PRE-FINDINGS",
            }
        )
        review_worker = exact_head_review_worker(
            node_id=review_node["id"],
            worker_id="RW-PRE-FINDINGS",
            attempt_id="ATT-PRE-FINDINGS",
            digest=digest,
            plan=plan,
            run=run,
        )
        review_worker["findings"] = ["informational note without a severity field"]
        run["review_workers"] = [review_worker]

        errors = validate_run(plan, run)
        self.assertTrue(
            any("current PASS review result must not contain findings" in error for error in errors),
            errors,
        )
        downstream_node = next(
            node for node in plan["graph"]["nodes"] if node["id"] == "N-VISUAL-REVIEW"
        )
        with patch("select_ready_nodes.validate_current_plan_run", return_value=[]):
            reasons = _logical_reasons(downstream_node, plan, run, *_incoming(plan))
        self.assertIn("route_not_activated", reasons)

    def test_complete_run_cannot_close_with_current_integration_dissent(self) -> None:
        plan, run = self._integration_stage_dissent_state()
        run["status"] = "complete"

        errors = validate_run(plan, run)
        self.assertTrue(
            any("current review node result must match" in error for error in errors),
            errors,
        )

    def test_complete_run_cannot_close_with_current_pass_findings(self) -> None:
        plan, run = self._integration_stage_dissent_state()
        run["graph_state"]["node_states"]["N-VISUAL-REVIEW"]["last_outcome"] = "pass"
        run["review_workers"][0]["outcome"] = "pass"
        run["review_workers"][0]["findings"] = ["informational note without a severity field"]
        run["status"] = "complete"

        errors = validate_run(plan, run)
        self.assertTrue(
            any("current PASS review result must not contain findings" in error for error in errors),
            errors,
        )

    def test_non_executable_run_statuses_never_dispatch_nodes(self) -> None:
        plan = valid_graph_plan()

        draft = valid_graph_run(plan)
        blocked = valid_graph_run(plan)
        authorize_execution(blocked, ["M1", "M2"], status="blocked")

        for status, run in (("draft", draft), ("blocked", blocked)):
            result = select_ready_nodes(plan, run)
            self.assertEqual([], result["dispatchable_nodes"], status)
            self.assertTrue(
                all(
                    "run_status_not_dispatchable" in item["reason_codes"]
                    for item in result["deferred_nodes"]
                ),
                (status, result["deferred_nodes"]),
            )

        # A valid complete RUN is terminal and normally has no ready graph
        # nodes. Keep this selector regression independent of closeout fixture
        # construction so the lifecycle guard itself remains covered.
        complete = copy.deepcopy(blocked)
        complete["status"] = "complete"
        with patch("select_ready_nodes.validate_current_plan_run", return_value=[]):
            result = select_ready_nodes(plan, complete)
        self.assertEqual([], result["dispatchable_nodes"])
        self.assertTrue(
            all(
                "run_status_not_dispatchable" in item["reason_codes"]
                for item in result["deferred_nodes"]
            )
        )

    def test_legacy_app_task_requires_spawn_without_reviewer_role(
        self,
    ) -> None:
        node = {"kind": "mission"}
        binding = {"driver": "app_threads"}
        runtime = {
            "workspace_mode": "app_managed_worktree",
            "nested_subagents": {
                "available": True,
                "allowed_roles": ["explorer", "tester"],
            },
        }

        self.assertIn(
            "spawn_subagents",
            _required_actions(node, binding, runtime, 8),
        )
        self.assertNotIn(
            "spawn_subagents",
            _required_actions(node, binding, runtime, 10),
        )

        runtime.pop("nested_subagents")
        self.assertNotIn(
            "spawn_subagents",
            _required_actions(node, binding, runtime, 10),
        )

    def test_v10_app_task_does_not_infer_nested_spawn_from_capability(self) -> None:
        node = {"kind": "mission"}
        binding = {"driver": "app_threads"}
        runtime = {
            "workspace_mode": "app_managed_worktree",
            "nested_subagents": {
                "available": True,
                "allowed_roles": ["reviewer"],
            },
        }

        self.assertEqual(
            [
                "create_user_owned_tasks",
                "create_app_managed_worktrees",
                "create_local_branches",
                "create_local_commits",
            ],
            _required_actions(node, binding, runtime, 10),
        )

    def test_visual_repair_mission_has_a_preintegration_review_path(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        template_run = load_run(
            SCRIPTS_DIR.parent / "assets/templates/MISSION_RUNBOOK.template.md"
        )
        active_state = copy.deepcopy(run["mission_states"]["M1"])
        active_node_state = copy.deepcopy(
            run["graph_state"]["node_states"]["N-M1"]
        )
        worker = run["workers"][0]

        run["mission_states"]["M1"] = copy.deepcopy(
            template_run["mission_states"]["M1"]
        )
        run["mission_states"]["M3"] = active_state
        run["mission_states"]["M3"].update(
            {
                "lease_id": "LEASE-M3",
                "worker_id": "W-M3",
            }
        )
        run["graph_state"]["node_states"]["N-M1"] = copy.deepcopy(
            template_run["graph_state"]["node_states"]["N-M1"]
        )
        run["graph_state"]["node_states"]["N-VISUAL-REPAIR"] = (
            active_node_state
        )
        run["graph_state"]["node_states"]["N-VISUAL-REPAIR"].update(
            {
                "last_attempt_id": "ATT-M3",
                "bound_worker_id": "W-M3",
            }
        )
        worker.update(
            {
                "worker_id": "W-M3",
                "mission_id": "M3",
                "lease_id": "LEASE-M3",
                "worktree_path": "C:/repo/worktrees/M3",
                "branch_ref": "refs/heads/codex/m3",
            }
        )
        run["observed"]["git"]["worktrees"] = [
            {
                "path": "C:/repo/worktrees/M3",
                "branch_ref": "refs/heads/codex/m3",
                "head_sha": "b" * 40,
                "managed_by": "parent",
                "dirty": False,
            }
        ]
        run["execution_authorization_scope"]["mission_ids"] = ["M3"]
        run["authorizations"]["spawn_subagents"]["scope"]["mission_ids"] = [
            "M3"
        ]
        retain_current_worker_state(plan, run)
        self.assertEqual([], validate_run(plan, run))

        selected = select_ready_nodes(plan, run)
        self.assertIn(
            "N-VISUAL-REPAIR-CODE-REVIEW",
            [item["node_id"] for item in selected["dispatchable_nodes"]],
        )

        run["mission_states"]["M3"]["phase"] = "integrating"
        blocked_errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "every planned pre-integration review node" in error
                for error in blocked_errors
            ),
            blocked_errors,
        )

        review_node_id = "N-VISUAL-REPAIR-CODE-REVIEW"
        review_worker_id = "RW-M3"
        review_attempt_id = "ATT-REVIEW-M3"
        run["graph_state"]["node_states"][review_node_id].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": review_attempt_id,
                "last_outcome": "pass",
                "bound_worker_id": review_worker_id,
                "blockers": [],
            }
        )
        run["review_workers"] = [
            exact_head_review_worker(
                node_id=review_node_id,
                worker_id=review_worker_id,
                attempt_id=review_attempt_id,
                digest=plan_digest(plan),
                plan=plan,
                run=run,
            )
        ]

        self.assertEqual([], validate_run(plan, run))

        run["mission_states"]["M3"].update(
            {
                "phase": "integrated",
                "integration_gate": "PASS",
                "integrated_sha": "c" * 40,
            }
        )
        run["graph_state"]["node_states"]["N-VISUAL-REPAIR"].update(
            {
                "phase": "succeeded",
                "last_outcome": "pass",
            }
        )
        run["integration"]["integration_head_sha"] = "c" * 40
        run["observed"]["git"]["parent_head_sha"] = "c" * 40
        authorize_action(
            run,
            "integrate_locally",
            ["M3"],
            [f"branch:{run['integration']['branch']}"],
        )
        visual_repair = next(
            mission for mission in plan["missions"] if mission["id"] == "M3"
        )
        run["verifier_executions"].append(
            retained_gate_execution(
                plan,
                run,
                visual_repair["integration_verifiers"][0],
                layer="mission_integration",
                execution_id="EXEC-INTEGRATION-M3",
                mission_id="M3",
            )
        )

        self.assertEqual([], validate_run(plan, run))

    def test_current_review_dispatches_before_integration_and_gates_transition(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": [
                        "app_threads",
                        "subagents",
                        "sequential_parent",
                    ],
                    "detection_source": "observed",
                    "capability_probe": codex_capability_probe(
                        app_threads=True,
                        subagents=True,
                    ),
                    "version_gate": current_version_gate(),
                },
                "nested_subagents": {
                    "available": True,
                    "max_depth": 1,
                    "max_children_per_worker": 3,
                    "allowed_roles": ["explorer", "tester"],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
                "platform_lifecycle": {
                    "owner": "app",
                    "automatic_retention_cleanup_possible": True,
                    "durable_branch_required_before_unique_work": True,
                },
            }
        )
        mission_worker = run["workers"][0]
        mission_worker.update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "task_thread_id": "THREAD-M1",
                "nested_subagent_policy": {
                    "enabled": False,
                    "max_children": 0,
                    "allowed_roles": [],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
            }
        )
        mission_worker["runtime_binding"]["driver"] = "app_threads"
        run["observed"]["git"]["worktrees"] = [
            {
                "path": "C:/repo/worktrees/M1",
                "branch_ref": "refs/heads/codex/m1",
                "head_sha": "b" * 40,
                "managed_by": "app",
                "dirty": False,
            }
        ]
        run["authorizations"]["create_user_owned_tasks"] = {
            "authorized": True,
            "source": "user authorized review task",
            "scope": {
                "run_id": run["run_id"],
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "mission_ids": ["M1"],
                "targets": ["*"],
            },
            "expires_when": "run_complete",
        }
        run["authorizations"]["spawn_subagents"] = {
            "authorized": False,
            "source": None,
        }
        retain_current_worker_state(plan, run, managed_by="app")
        self.assertEqual([], validate_run(plan, run))

        selected = select_ready_nodes(plan, run)

        self.assertIn(
            "N-FRONTEND-REVIEW",
            [item["node_id"] for item in selected["dispatchable_nodes"]],
        )
        review_directive = next(
            item
            for item in selected["dispatchable_nodes"]
            if item["node_id"] == "N-FRONTEND-REVIEW"
        )
        self.assertEqual("create_thread", review_directive["launch_kind"])
        self.assertEqual(
            ["create_user_owned_tasks"],
            review_directive["required_actions"],
        )

        digest = plan_digest(plan)
        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-M1",
                "last_outcome": "pass",
                "bound_worker_id": "RW-M1",
                "blockers": [],
            }
        )
        run["review_workers"] = [
            {
                "worker_id": "RW-M1",
                "node_id": "N-FRONTEND-REVIEW",
                "attempt_id": "ATT-REVIEW-M1",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "graph_revision": run["graph_state"]["graph_revision"],
                "reviewed_sha": "b" * 40,
                "review_path": "C:/repo/worktrees/M1",
                "worker_runtime": "app_task",
                "completion_channel": "thread_poll",
                "runtime_binding": {
                    "provider": "codex",
                    "driver": "app_threads",
                    "source": "host",
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "medium",
                    "option_source": "plan_provider_options",
                },
                "task_thread_id": "THREAD-REVIEW-M1",
                "report_path": None,
                "phase": "worker_passed",
                "outcome": "pass",
                "findings": [],
            }
        ]
        run["mission_states"]["M1"]["phase"] = "integrating"

        self.assertEqual([], validate_run(plan, run))

    def test_reconciled_node_cannot_override_only_fix_required_review(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-ONLY",
                "last_outcome": "pass",
                "bound_worker_id": "RW-ONLY",
                "blockers": [],
            }
        )
        run["review_workers"] = [
            exact_head_review_worker(
                node_id="N-FRONTEND-REVIEW",
                worker_id="RW-ONLY",
                attempt_id="ATT-REVIEW-ONLY",
                digest=digest,
                plan=plan,
                run=run,
                outcome="fix_required",
            )
        ]
        run["mission_states"]["M1"]["phase"] = "integrating"

        errors = validate_run(plan, run)
        self.assertTrue(
            any("every planned pre-integration review node" in error for error in errors),
            errors,
        )

    def test_failed_review_worker_cannot_satisfy_integration_gate(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-FAILED",
                "last_outcome": "pass",
                "bound_worker_id": "RW-FAILED",
                "blockers": [],
            }
        )
        failed_worker = exact_head_review_worker(
            node_id="N-FRONTEND-REVIEW",
            worker_id="RW-FAILED",
            attempt_id="ATT-REVIEW-FAILED",
            digest=digest,
            plan=plan,
            run=run,
        )
        failed_worker["phase"] = "worker_failed"
        run["review_workers"] = [failed_worker]
        run["mission_states"]["M1"]["phase"] = "integrating"

        errors = validate_run(plan, run)
        self.assertTrue(
            any("every planned pre-integration review node" in error for error in errors),
            errors,
        )

    def test_integration_waits_for_every_planned_preintegration_review(
        self,
    ) -> None:
        plan, run, digest = fanout_preintegration_review_state()

        first_state = run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"]
        first_state.update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-FIRST",
                "last_outcome": "pass",
                "bound_worker_id": "RW-FIRST",
                "blockers": [],
            }
        )
        run["review_workers"] = [
            exact_head_review_worker(
                node_id="N-FRONTEND-REVIEW",
                worker_id="RW-FIRST",
                attempt_id="ATT-REVIEW-FIRST",
                digest=digest,
                plan=plan,
                run=run,
            )
        ]
        run["mission_states"]["M1"]["phase"] = "integrating"

        errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "every planned pre-integration review node" in error
                for error in errors
            ),
            errors,
        )

        second_state = run["graph_state"]["node_states"][
            "N-FRONTEND-REVIEW-SECOND"
        ]
        second_state.update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-SECOND",
                "last_outcome": "pass",
                "bound_worker_id": "RW-SECOND",
                "blockers": [],
            }
        )
        run["review_workers"].append(
            exact_head_review_worker(
                node_id="N-FRONTEND-REVIEW-SECOND",
                worker_id="RW-SECOND",
                attempt_id="ATT-REVIEW-SECOND",
                digest=digest,
                plan=plan,
                run=run,
                outcome="fix_required",
            )
        )
        run["review_workers"][-1]["phase"] = "worker_passed"
        third_state = run["graph_state"]["node_states"][
            "N-FRONTEND-REVIEW-THIRD"
        ]
        third_state.update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-THIRD",
                "last_outcome": "pass",
                "bound_worker_id": "RW-THIRD",
                "blockers": [],
            }
        )
        run["review_workers"].append(
            exact_head_review_worker(
                node_id="N-FRONTEND-REVIEW-THIRD",
                worker_id="RW-THIRD",
                attempt_id="ATT-REVIEW-THIRD",
                digest=digest,
                plan=plan,
                run=run,
            )
        )

        errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "every planned pre-integration review node" in error
                for error in errors
            ),
            errors,
        )

    def test_repaired_head_rearms_every_stale_preintegration_review(
        self,
    ) -> None:
        plan, run, digest = fanout_preintegration_review_state()
        first_state = run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"]
        first_state.update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-FIRST",
                "last_outcome": "pass",
                "bound_worker_id": "RW-FIRST",
                "blockers": [],
            }
        )
        second_state = run["graph_state"]["node_states"][
            "N-FRONTEND-REVIEW-SECOND"
        ]
        second_state.update(
            {
                "phase": "ready",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-SECOND",
                "last_outcome": "fix_required",
                "bound_worker_id": None,
                "blockers": [],
            }
        )
        third_state = run["graph_state"]["node_states"][
            "N-FRONTEND-REVIEW-THIRD"
        ]
        third_state.update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-THIRD",
                "last_outcome": "pass",
                "bound_worker_id": "RW-THIRD",
                "blockers": [],
            }
        )
        run["review_workers"] = [
            exact_head_review_worker(
                node_id="N-FRONTEND-REVIEW",
                worker_id="RW-FIRST",
                attempt_id="ATT-REVIEW-FIRST",
                digest=digest,
                plan=plan,
                run=run,
            ),
            exact_head_review_worker(
                node_id="N-FRONTEND-REVIEW-SECOND",
                worker_id="RW-SECOND",
                attempt_id="ATT-REVIEW-SECOND",
                digest=digest,
                plan=plan,
                run=run,
                outcome="fix_required",
            ),
            exact_head_review_worker(
                node_id="N-FRONTEND-REVIEW-THIRD",
                worker_id="RW-THIRD",
                attempt_id="ATT-REVIEW-THIRD",
                digest=digest,
                plan=plan,
                run=run,
            ),
        ]
        self.assertEqual([], validate_run(plan, run))

        run["mission_states"]["M1"]["prior_head_shas"] = ["b" * 40]
        run["mission_states"]["M1"]["head_sha"] = "c" * 40
        run["workers"][0]["worker_head_sha"] = "c" * 40
        retain_current_worker_state(plan, run)

        self.assertEqual([], validate_run(plan, run))
        selected = select_ready_nodes(plan, run)
        dispatchable_ids = {
            item["node_id"] for item in selected["dispatchable_nodes"]
        }
        self.assertIn("N-FRONTEND-REVIEW", dispatchable_ids)
        self.assertIn("N-FRONTEND-REVIEW-SECOND", dispatchable_ids)
        self.assertIn("N-FRONTEND-REVIEW-THIRD", dispatchable_ids)

    def test_preintegration_fix_returns_to_original_worktree_before_rereview(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
            {
                "phase": "ready",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-OLD",
                "last_outcome": "fix_required",
                "bound_worker_id": None,
                "blockers": [],
            }
        )
        run["review_workers"] = [
            {
                "worker_id": "RW-OLD",
                "node_id": "N-FRONTEND-REVIEW",
                "attempt_id": "ATT-REVIEW-OLD",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "graph_revision": run["graph_state"]["graph_revision"],
                "reviewed_sha": "b" * 40,
                "review_path": "C:/repo/worktrees/M1",
                "worker_runtime": "subagent",
                "completion_channel": "agent_result",
                "runtime_binding": {
                    "provider": "codex",
                    "driver": "subagents",
                    "source": "host",
                    "model": "gpt-5.6-sol",
                    "reasoning_effort": "medium",
                    "option_source": "plan_provider_options",
                },
                "task_thread_id": None,
                "report_path": None,
                "phase": "worker_failed",
                "outcome": "fix_required",
                "findings": ["src/example/file.ts:1 fix required"],
            }
        ]
        self.assertEqual([], validate_run(plan, run))

        unchanged = select_ready_nodes(plan, run)
        deferred = {
            item["node_id"]: item["reason_codes"]
            for item in unchanged["deferred_nodes"]
        }
        self.assertIn("review_head_unchanged", deferred["N-FRONTEND-REVIEW"])

        original_worker = run["workers"][0]
        original_identity = (
            original_worker["worker_id"],
            original_worker["worktree_path"],
            original_worker["branch_ref"],
        )
        run["mission_states"]["M1"]["prior_head_shas"] = ["b" * 40]
        run["mission_states"]["M1"]["head_sha"] = "c" * 40
        original_worker["worker_head_sha"] = "c" * 40
        retain_current_worker_state(plan, run)

        selected = select_ready_nodes(plan, run)
        directives = {
            item["node_id"]: item for item in selected["dispatchable_nodes"]
        }

        self.assertIn("N-FRONTEND-REVIEW", directives)
        self.assertEqual(
            original_identity,
            (
                original_worker["worker_id"],
                original_worker["worktree_path"],
                original_worker["branch_ref"],
            ),
        )
        self.assertNotIn("M2", {mission["id"] for mission in plan["missions"]})
        self.assertNotIn(
            "N-M1-REPAIR",
            {node["id"] for node in plan["graph"]["nodes"]},
        )
        self.assertFalse(
            any(
                item["kind"] == "mission"
                for item in selected["dispatchable_nodes"]
            )
        )

    def test_fix_required_review_rejects_unrelated_sha_without_history(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
            {
                "phase": "ready",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-UNRELATED",
                "last_outcome": "fix_required",
                "bound_worker_id": None,
                "blockers": [],
            }
        )
        run["review_workers"] = [
            exact_head_review_worker(
                node_id="N-FRONTEND-REVIEW",
                worker_id="RW-UNRELATED",
                attempt_id="ATT-REVIEW-UNRELATED",
                digest=digest,
                plan=plan,
                run=run,
                outcome="fix_required",
            )
        ]
        run["review_workers"][0]["reviewed_sha"] = "f" * 40

        errors = validate_run(plan, run)

        self.assertTrue(
            any(
                "reviewed_sha: must identify the direct singleton pre-integration worktree or integrated head"
                in error
                for error in errors
            ),
            errors,
        )

    def test_historical_review_attempt_requires_recorded_sha_history(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
            {
                "phase": "ready",
                "attempts": 2,
                "last_attempt_id": "ATT-REVIEW-NEW",
                "last_outcome": "fix_required",
                "bound_worker_id": None,
                "blockers": [],
            }
        )
        historical_worker = exact_head_review_worker(
            node_id="N-FRONTEND-REVIEW",
            worker_id="RW-HISTORICAL",
            attempt_id="ATT-REVIEW-OLD",
            digest=digest,
            plan=plan,
            run=run,
            outcome="fix_required",
        )
        historical_worker["reviewed_sha"] = "f" * 40
        run["review_workers"] = [historical_worker]

        errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "reviewed_sha: must identify the direct singleton pre-integration worktree or integrated head"
                in error
                for error in errors
            ),
            errors,
        )

        run["mission_states"]["M1"]["prior_head_shas"] = ["f" * 40]
        self.assertEqual([], validate_run(plan, run))

    def test_batch_pass_review_rejects_a_superseded_integration_head(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        node_id = "N-VISUAL-REVIEW"
        attempt_id = "ATT-VISUAL-REVIEW-OLD"
        run["graph_state"]["node_states"][node_id].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": attempt_id,
                "last_outcome": "pass",
                "bound_worker_id": "RW-VISUAL-OLD",
                "blockers": [],
            }
        )
        review_worker = exact_head_review_worker(
            node_id=node_id,
            worker_id="RW-VISUAL-OLD",
            attempt_id=attempt_id,
            digest=digest,
            plan=plan,
            run=run,
        )
        review_worker["reviewed_sha"] = "a" * 40
        review_worker["review_path"] = "C:/repo"
        run["review_workers"] = [review_worker]
        self.assertEqual([], validate_run(plan, run))

        run["integration"]["prior_head_shas"] = ["a" * 40]
        run["integration"]["integration_head_sha"] = "c" * 40

        errors = validate_run(plan, run)

        self.assertTrue(
            any(
                "reviewed_sha: must identify the direct singleton pre-integration worktree or integrated head"
                in error
                for error in errors
            ),
            errors,
        )

    def test_batch_review_pass_bound_to_an_integrated_sha_goes_stale_on_a_new_head(
        self,
    ) -> None:
        """A batch review may not keep a PASS alive via a mission's integrated_sha.

        integrated_sha is a permanent historical value. Before this was scoped to
        direct singleton pre-integration reviews, a batch review that passed on the
        head right after M1 landed stayed valid forever, so a later repair could
        land and the run would close out carrying a review of an older head.
        """
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        node_id = "N-VISUAL-REVIEW"
        attempt_id = "ATT-VISUAL-REVIEW-BATCH"
        nodes = {node["id"]: node for node in plan["graph"]["nodes"]}
        # Two missions makes this a batch review, not a direct singleton one.
        nodes[node_id]["review"]["mission_ids"] = ["M1", "M3"]
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["execution_authorization_scope"]["plan_digest_sha256"] = digest
        for authorization in run["authorizations"].values():
            scope = authorization.get("scope") if isinstance(authorization, dict) else None
            if isinstance(scope, dict) and "plan_digest_sha256" in scope:
                scope["plan_digest_sha256"] = digest
        run["mission_states"]["M1"]["lease_plan_digest_sha256"] = digest
        run["workers"][0]["plan_digest_sha256"] = digest
        for execution in run.get("verifier_executions", []):
            context = execution.get("context") if isinstance(execution, dict) else None
            if isinstance(context, dict):
                context["plan_digest_sha256"] = digest
            key_document = execution.get("key_document") if isinstance(execution, dict) else None
            if isinstance(key_document, dict):
                key_document["plan_digest_sha256"] = digest
                execution["execution_key"] = execution_key_from_document(key_document)
                execution["evidence_key"] = execution["execution_key"]
        run["graph_state"]["node_states"][node_id].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": attempt_id,
                "last_outcome": "pass",
                "bound_worker_id": "RW-VISUAL-BATCH",
                "blockers": [],
            }
        )
        integrated_sha = "c" * 40
        run["mission_states"]["M1"]["integrated_sha"] = integrated_sha
        run["integration"]["integration_head_sha"] = integrated_sha
        review_worker = exact_head_review_worker(
            node_id=node_id,
            worker_id="RW-VISUAL-BATCH",
            attempt_id=attempt_id,
            digest=digest,
            plan=plan,
            run=run,
        )
        review_worker["reviewed_sha"] = integrated_sha
        review_worker["review_path"] = "C:/repo"
        run["review_workers"] = [review_worker]

        # While the integration head still equals that SHA the PASS is current.
        self.assertEqual([], validate_run(plan, run))

        # A repair lands: the head moves on, so the batch PASS is now stale.
        run["integration"]["prior_head_shas"] = [integrated_sha]
        run["integration"]["integration_head_sha"] = "f" * 40

        errors = validate_run(plan, run)

        self.assertTrue(
            any(
                "reviewed_sha: must identify the direct singleton pre-integration "
                "worktree or integrated head" in error
                for error in errors
            ),
            errors,
        )

    def test_complete_run_cannot_supersede_a_review_that_found_a_defect(self) -> None:
        """Superseding a fix_required review must not be an escape from the loop."""
        plan, run = current_preintegration_review_state()
        node_id = "N-VISUAL-REVIEW"
        run["graph_state"]["node_states"][node_id].update(
            {
                "phase": "superseded",
                "attempts": 1,
                "last_outcome": "fix_required",
                "blockers": [],
            }
        )
        run["status"] = "complete"

        errors = validate_run(plan, run)

        self.assertTrue(
            any(
                "cannot supersede a review node that returned fix_required" in error
                for error in errors
            ),
            errors,
        )

    def test_post_integration_review_rearms_after_its_repair_routes_back(self) -> None:
        """The fix_required correction loop must actually close.

        N-VISUAL-REVIEW returns fix_required and parks in `failed`. Its bounded
        repair route runs N-VISUAL-REPAIR, whose code review passes and routes
        back. The review then has to become selectable again on the new head —
        otherwise the frontier empties with no blocker and the run stalls.
        """
        plan, run = current_preintegration_review_state()
        node_states = run["graph_state"]["node_states"]
        edge_states = run["graph_state"]["edge_states"]

        # The visual review already ran and asked for a repair.
        node_states["N-VISUAL-REVIEW"].update(
            {
                "phase": "failed",
                "attempts": 1,
                "last_attempt_id": "ATT-VISUAL-1",
                "last_outcome": "fix_required",
                "bound_worker_id": None,
                "blockers": [],
            }
        )

        # Before the repair's review passes, the node must stay parked.
        parked = _logical_reasons(
            next(n for n in plan["graph"]["nodes"] if n["id"] == "N-VISUAL-REVIEW"),
            plan,
            run,
            *_incoming(plan),
        )
        self.assertIn("node_phase_not_ready", parked)

        # The repair lands and its code review passes, traversing the return route.
        node_states["N-VISUAL-REPAIR-CODE-REVIEW"].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REPAIR-REVIEW-1",
                "last_outcome": "pass",
                "bound_worker_id": None,
                "blockers": [],
            }
        )
        edge_states["E-VISUAL-REPAIR-REREVIEW"].update(
            {"status": "traversed", "traversals": 1, "source_attempt_id": "ATT-REPAIR-REVIEW-1"}
        )

        rearmed = _logical_reasons(
            next(n for n in plan["graph"]["nodes"] if n["id"] == "N-VISUAL-REVIEW"),
            plan,
            run,
            *_incoming(plan),
        )
        self.assertNotIn("node_phase_not_ready", rearmed)
        self.assertNotIn("route_not_activated", rearmed)

    def test_a_rearmed_review_still_stops_when_its_attempt_budget_is_spent(self) -> None:
        plan, run = current_preintegration_review_state()
        node_states = run["graph_state"]["node_states"]
        edge_states = run["graph_state"]["edge_states"]
        node_states["N-VISUAL-REVIEW"].update(
            {
                "phase": "failed",
                "attempts": 2,
                "last_attempt_id": "ATT-VISUAL-2",
                "last_outcome": "fix_required",
                "bound_worker_id": None,
                "blockers": [],
            }
        )
        node_states["N-VISUAL-REPAIR-CODE-REVIEW"].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REPAIR-REVIEW-1",
                "last_outcome": "pass",
                "bound_worker_id": None,
                "blockers": [],
            }
        )
        edge_states["E-VISUAL-REPAIR-REREVIEW"].update(
            {"status": "traversed", "traversals": 1, "source_attempt_id": "ATT-REPAIR-REVIEW-1"}
        )

        reasons = _logical_reasons(
            next(n for n in plan["graph"]["nodes"] if n["id"] == "N-VISUAL-REVIEW"),
            plan,
            run,
            *_incoming(plan),
        )
        self.assertIn("attempts_exhausted", reasons)
        self.assertIn("node_phase_not_ready", reasons)

    def test_traversed_edge_requires_an_outcome_the_edge_declares(self) -> None:
        """A pass-only edge may not be traversed from a fix_required attempt.

        This is the mechanism behind "it never routes straight past the review
        gate": without it, a run can record the closeout route as traversed from
        the very attempt that asked for a repair.
        """
        plan, run = current_preintegration_review_state()
        run["graph_state"]["node_states"]["N-VISUAL-REVIEW"].update(
            {
                "phase": "failed",
                "attempts": 1,
                "last_attempt_id": "ATT-VISUAL-1",
                "last_outcome": "fix_required",
                "blockers": [],
            }
        )
        # E-VISUAL-FINAL-GATE declares on_outcomes ["pass"].
        run["graph_state"]["edge_states"]["E-VISUAL-FINAL-GATE"].update(
            {"status": "traversed", "traversals": 1, "source_attempt_id": "ATT-VISUAL-1"}
        )

        errors = validate_run(plan, run)

        self.assertTrue(
            any(
                "traversed edge requires a source outcome the edge declares" in error
                for error in errors
            ),
            errors,
        )

    def test_multi_mission_review_cannot_authorize_preintegration_coverage(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        nodes = {node["id"]: node for node in plan["graph"]["nodes"]}
        review = nodes["N-FRONTEND-REVIEW"]
        review["review"]["mission_ids"] = ["M1", "M3"]

        self.assertFalse(
            _preintegration_review_source_ready(
                review,
                nodes["N-M1"],
                run,
            )
        )

        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["execution_authorization_scope"]["plan_digest_sha256"] = digest
        run["authorizations"]["spawn_subagents"]["scope"][
            "plan_digest_sha256"
        ] = digest
        run["mission_states"]["M1"]["lease_plan_digest_sha256"] = digest
        run["workers"][0]["plan_digest_sha256"] = digest

        errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "no direct singleton pre-integration review node: M1" in error
                for error in errors
            ),
            errors,
        )

    def test_review_without_pass_cannot_authorize_preintegration_coverage(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        review = next(
            node
            for node in plan["graph"]["nodes"]
            if node["id"] == "N-FRONTEND-REVIEW"
        )
        review["allowed_outcomes"] = [
            "fix_required",
            "blocked",
            "contract_gap",
        ]

        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["execution_authorization_scope"]["plan_digest_sha256"] = digest
        run["authorizations"]["spawn_subagents"]["scope"][
            "plan_digest_sha256"
        ] = digest
        run["mission_states"]["M1"]["lease_plan_digest_sha256"] = digest
        run["workers"][0]["plan_digest_sha256"] = digest

        errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "no direct singleton pre-integration review node: M1" in error
                for error in errors
            ),
            errors,
        )

    def test_malformed_current_mission_states_return_validation_errors(self) -> None:
        plan, run = current_preintegration_review_state()
        run["mission_states"] = None

        errors = validate_run(plan, run)

        self.assertTrue(
            any("run.mission_states: must be an object" in error for error in errors)
        )

    def test_malformed_review_node_state_returns_validation_errors(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        run["mission_states"]["M1"]["phase"] = "integrating"
        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"] = []
        run["review_workers"] = [
            exact_head_review_worker(
                node_id="N-FRONTEND-REVIEW",
                worker_id="RW-MALFORMED-STATE",
                attempt_id="ATT-MALFORMED-STATE",
                digest=digest,
                plan=plan,
                run=run,
            )
        ]

        errors = validate_run(plan, run)

        self.assertTrue(
            any(
                "run.graph_state.node_states.N-FRONTEND-REVIEW: must be an object"
                in error
                for error in errors
            ),
            errors,
        )

    def test_v10_flat_app_task_requires_parent_owned_preintegration_review(
        self,
    ) -> None:
        plan, run = current_preintegration_review_state()
        worker = configure_flat_app_task(plan, run)
        worker["nested_subagent_policy"].update(
            {"enabled": True, "max_children": 1, "allowed_roles": ["reviewer"]}
        )
        self.assertTrue(
            any(
                "RUN-v10 forbids worker-owned delegation" in error
                for error in validate_run(plan, run)
            )
        )
        worker["nested_subagent_policy"].update(
            {"enabled": False, "max_children": 0, "allowed_roles": []}
        )
        run["mission_states"]["M1"]["phase"] = "integrating"

        errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "every planned pre-integration review node"
                in error
                for error in errors
            )
        )

        run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-NESTED-REVIEW-M1",
                "last_outcome": "pass",
                "bound_worker_id": "A-REVIEW-M1",
                "blockers": [],
            }
        )
        run["review_workers"] = [
            exact_head_review_worker(
                node_id="N-FRONTEND-REVIEW",
                worker_id="A-REVIEW-M1",
                attempt_id="ATT-NESTED-REVIEW-M1",
                digest=plan_digest(plan),
                plan=plan,
                run=run,
            )
        ]

        self.assertEqual([], validate_run(plan, run))

    def test_integration_rejects_a_worker_from_another_mission(self) -> None:
        plan, run = current_preintegration_review_state()
        run["workers"][0]["mission_id"] = "M3"
        run["mission_states"]["M1"]["phase"] = "integrating"

        errors = validate_run(plan, run)

        self.assertTrue(
            any(
                "worker_id: transition to integrating requires a worker belonging to the same mission"
                in error
                for error in errors
            ),
            errors,
        )

    def test_parent_review_fanout_accepts_distinct_sibling_reviewers(
        self,
    ) -> None:
        plan, run, digest = fanout_preintegration_review_state()
        configure_flat_app_task(plan, run)
        run["mission_states"]["M1"]["phase"] = "integrating"
        review_specs = (
            ("N-FRONTEND-REVIEW", "A-REVIEW-M1", "ATT-REVIEW-FIRST"),
            (
                "N-FRONTEND-REVIEW-SECOND",
                "A-REVIEW-M1-SECOND",
                "ATT-REVIEW-SECOND",
            ),
            (
                "N-FRONTEND-REVIEW-THIRD",
                "A-REVIEW-M1-THIRD",
                "ATT-REVIEW-THIRD",
            ),
        )
        run["review_workers"] = []
        for node_id, worker_id, attempt_id in review_specs:
            run["graph_state"]["node_states"][node_id].update(
                {
                    "phase": "succeeded",
                    "attempts": 1,
                    "last_attempt_id": attempt_id,
                    "last_outcome": "pass",
                    "bound_worker_id": worker_id,
                    "blockers": [],
                }
            )
            run["review_workers"].append(
                exact_head_review_worker(
                    node_id=node_id,
                    worker_id=worker_id,
                    attempt_id=attempt_id,
                    digest=digest,
                    plan=plan,
                    run=run,
                )
            )

        self.assertEqual([], validate_run(plan, run))

        run["review_workers"][0]["outcome"] = "fix_required"
        run["review_workers"][0]["findings"] = ["src/example/app.ts:1 blocking issue"]
        errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "every planned pre-integration review node" in error
                for error in errors
            ),
            errors,
        )

        run["review_workers"][1]["outcome"] = "fix_required"
        run["review_workers"][1]["findings"] = ["src/example/app.ts:2 second blocking issue"]
        errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "every planned pre-integration review node" in error
                for error in errors
            ),
            errors,
        )

    def test_plan_backed_parent_write_is_not_dispatched_in_shared_checkout(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = authorized_parent_run(plan)

        result = select_ready_nodes(plan, run)

        self.assertEqual([], result["dispatchable_nodes"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("workspace_not_isolated", deferred["N-M1"])

    def _authorized_conflict_free_pair(self) -> tuple[dict[str, object], dict[str, object]]:
        plan = valid_graph_plan()
        detach_mission_edges(plan)
        plan["max_parallel_workers"] = 2
        run = valid_graph_run(plan)
        authorize_execution(run, ["M1", "M2"], status="ready")
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "max_parallel_workers": 2,
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": ["subagents", "sequential_parent"],
                    "detection_source": "observed",
                    "capability_probe": codex_capability_probe(subagents=True),
                    "version_gate": current_version_gate(),
                },
            }
        )
        run["observed"]["runtime"].update(
            {
                "available_worker_slots": 2,
                "isolation_capacity": 2,
                "completion_channel_available": True,
            }
        )
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize_action(run, action, ["M1", "M2"], ["*"])
        return plan, run

    def test_authorized_conflict_free_pair_selects_two_parallel_directives(self) -> None:
        plan, run = self._authorized_conflict_free_pair()

        result = select_ready_nodes(plan, run)

        self.assertEqual("parallel_graph", result["execution_route"])
        self.assertEqual(
            ["N-M1", "N-M2"],
            [item["node_id"] for item in result["dispatchable_nodes"]],
        )
        self.assertEqual(
            {"N-M1", "N-M2"},
            {item["node_id"] for item in result["dispatchable_nodes"]},
        )

    def test_effective_write_budget_one_selects_one_managed_directive(self) -> None:
        plan, run = self._authorized_conflict_free_pair()
        run["runtime_capabilities"]["max_parallel_workers"] = 1
        run["observed"]["runtime"]["available_worker_slots"] = 1
        run["observed"]["runtime"]["isolation_capacity"] = 1

        result = select_ready_nodes(plan, run)

        self.assertEqual("managed_sequential", result["execution_route"])
        self.assertEqual(["N-M1"], [item["node_id"] for item in result["dispatchable_nodes"]])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("over_budget", deferred["N-M2"])

    def _unprobed_pair(self):
        plan, run = self._authorized_conflict_free_pair()
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter["detection_source"] = "fallback"
        adapter.pop("capability_probe", None)
        run["runtime_capabilities"]["max_parallel_workers"] = 1
        run["observed"]["runtime"]["available_worker_slots"] = 1
        run["observed"]["runtime"]["isolation_capacity"] = 1
        return plan, run

    def test_unprobed_capability_withholds_a_silently_sequential_wave(self) -> None:
        # Independent, conflict-free, authorized missions held back only by a
        # budget nobody measured. Running one of them anyway would present a
        # guess as a decision, and it is indistinguishable from a deliberate cap.
        plan, run = self._unprobed_pair()

        result = select_ready_nodes(plan, run)

        self.assertEqual([], result["dispatchable_nodes"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("capability_unprobed", deferred["N-M1"])
        self.assertIn("capability_unprobed", deferred["N-M2"])

    def test_declaring_the_route_explicitly_is_allowed_to_proceed(self) -> None:
        # `explicit` is the escape hatch: sequential on purpose, not by accident.
        plan, run = self._unprobed_pair()
        run["runtime_capabilities"]["runtime_adapter"]["detection_source"] = "explicit"

        result = select_ready_nodes(plan, run)

        self.assertEqual(["N-M1"], [item["node_id"] for item in result["dispatchable_nodes"]])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertNotIn("capability_unprobed", deferred["N-M2"])

    def test_observed_capacity_of_one_is_a_real_answer_and_proceeds(self) -> None:
        # A host that genuinely has one slot is not the same as an unmeasured
        # one, and must not be blocked.
        plan, run = self._authorized_conflict_free_pair()
        run["runtime_capabilities"]["max_parallel_workers"] = 1
        run["observed"]["runtime"]["available_worker_slots"] = 1
        run["observed"]["runtime"]["isolation_capacity"] = 1

        result = select_ready_nodes(plan, run)

        self.assertEqual(
            "observed",
            run["runtime_capabilities"]["runtime_adapter"]["detection_source"],
        )
        self.assertEqual(["N-M1"], [item["node_id"] for item in result["dispatchable_nodes"]])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertNotIn("capability_unprobed", deferred["N-M2"])

    def test_sequential_parent_caps_write_and_runtime_budgets_at_one(self) -> None:
        plan = valid_graph_plan()
        detach_mission_edges(plan)
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["active_wave"]["plan_digest_sha256"] = digest
        authorize_execution(
            run,
            ["M1", "M2"],
            plan=plan,
            digest=digest,
        )
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "parent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "max_parallel_workers": 4,
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": ["sequential_parent"],
                    "detection_source": "observed",
                    "capability_probe": codex_capability_probe(),
                    "version_gate": current_version_gate(),
                },
            }
        )
        run["observed"]["runtime"].update(
            {
                "available_worker_slots": 4,
                "isolation_capacity": 4,
                "completion_channel_available": True,
            }
        )
        for action in (
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize_action(run, action, ["M1", "M2"], ["*"])

        result = select_ready_nodes(plan, run)

        self.assertEqual(["N-M1"], [item["node_id"] for item in result["dispatchable_nodes"]])
        directive = result["dispatchable_nodes"][0]
        self.assertEqual("run_parent", directive["launch_kind"])
        self.assertEqual(
            [
                "create_local_worktrees",
                "create_local_branches",
                "create_local_commits",
            ],
            directive["required_actions"],
        )
        self.assertNotIn("spawn_subagents", directive["required_actions"])
        deferred = {
            item["node_id"]: item["reason_codes"]
            for item in result["deferred_nodes"]
        }
        self.assertIn("over_budget", deferred["N-M2"])

    def test_sequential_parent_selection_records_parent_worker_lifecycle(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        authorize_execution(run, ["M1"], plan=plan, digest=digest)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "parent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "max_parallel_workers": 2,
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": ["sequential_parent"],
                    "detection_source": "observed",
                    "capability_probe": codex_capability_probe(),
                    "version_gate": current_version_gate(),
                },
            }
        )
        run["observed"]["runtime"].update(
            {
                "available_worker_slots": 2,
                "isolation_capacity": 2,
                "completion_channel_available": True,
            }
        )
        worktree_path = "C:/repo/worktrees/M1"
        branch_ref = "refs/heads/codex/m1"
        for action, target in (
            ("create_local_worktrees", f"worktree:{worktree_path}"),
            ("create_local_branches", f"branch:{branch_ref}"),
            ("create_local_commits", f"branch:{branch_ref}"),
        ):
            authorize_action(run, action, ["M1"], ["*"])

        result = select_ready_nodes(plan, run)

        self.assertEqual(["N-M1"], [item["node_id"] for item in result["dispatchable_nodes"]])
        directive = result["dispatchable_nodes"][0]
        self.assertEqual("runtime_worker", next(node for node in plan["graph"]["nodes"] if node["id"] == "N-M1")["executor"])
        self.assertEqual("run_parent", directive["launch_kind"])
        self.assertEqual("parent", directive["worker_runtime"])
        self.assertEqual("parent_managed_worktree", directive["workspace_mode"])
        self.assertNotIn("spawn_subagents", directive["required_actions"])
        self.assertFalse(run["authorizations"]["spawn_subagents"]["authorized"])

        # A launch directive uses the broad action contract; once the parent
        # allocates the worker, retain exact worktree and branch targets.
        for action, target in (
            ("create_local_worktrees", f"worktree:{worktree_path}"),
            ("create_local_branches", f"branch:{branch_ref}"),
            ("create_local_commits", f"branch:{branch_ref}"),
        ):
            authorize_action(run, action, ["M1"], [target])

        worker_id = "W-M1"
        lease_id = "LEASE-M1"
        attempt_id = "ATT-M1-1"
        run["mission_states"]["M1"].update(
            {
                "phase": "worker_running",
                "lease_id": lease_id,
                "lease_plan_revision": plan["revision"],
                "lease_plan_digest_sha256": digest,
                "worker_id": worker_id,
                "base_sha": run["integration"]["batch_base_sha"],
            }
        )
        run["graph_state"]["node_states"]["N-M1"].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": attempt_id,
                "last_outcome": None,
                "bound_worker_id": worker_id,
                "blockers": [],
            }
        )
        run["workers"] = [
            {
                "worker_id": worker_id,
                "mission_id": "M1",
                "lease_id": lease_id,
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "batch_base_sha": run["integration"]["batch_base_sha"],
                "worker_runtime": "parent",
                "workspace_mode": "parent_managed_worktree",
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
                "worktree_path": worktree_path,
                "branch_ref": branch_ref,
                "report_path": None,
                "phase": "worker_running",
                "worker_head_sha": None,
            }
        ]
        run["observed"]["git"]["worktrees"] = [
            {
                "path": worktree_path,
                "branch_ref": branch_ref,
                "head_sha": None,
                "managed_by": "parent",
                "dirty": False,
            }
        ]

        self.assertEqual([], validate_run(plan, run))

    def test_sequential_parent_shared_checkout_is_rejected_before_dispatch(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        authorize_execution(run, ["M1"])
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "parent",
                "workspace_mode": "shared_checkout",
                "completion_channel": "agent_result",
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": ["sequential_parent"],
                    "detection_source": "observed",
                    "capability_probe": codex_capability_probe(),
                    "version_gate": current_version_gate(),
                },
            }
        )

        with self.assertRaises(GraphSelectionError) as raised:
            select_ready_nodes(plan, run)

        self.assertIn(
            "sequential_parent requires parent/parent_managed_worktree/agent_result",
            str(raised.exception),
        )

    def test_dependent_node_stays_deferred_until_its_edge_fires(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = authorized_parent_run(plan)

        result = select_ready_nodes(plan, run)

        self.assertNotIn(
            "N-M2", [item["node_id"] for item in result["dispatchable_nodes"]]
        )

    def test_running_resume_fails_closed_on_unknown_parent_state(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = authorized_parent_run(plan)
        run["observed"]["captured_at"] = None
        run["observed"]["git"]["parent_dirty"] = None

        result = select_ready_nodes(plan, run)

        self.assertEqual([], result["ready_frontier"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("parent_state_unreconciled", deferred["N-M1"])

    def test_missing_captured_at_alone_defers_the_write_launch(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = authorized_parent_run(plan)
        run["observed"]["git"]["parent_dirty"] = False
        run["observed"]["captured_at"] = None

        result = select_ready_nodes(plan, run)

        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("parent_state_unreconciled", deferred["N-M1"])
        self.assertNotIn(
            "N-M1", [item["node_id"] for item in result["dispatchable_nodes"]]
        )

    def test_running_resume_reconciles_every_linked_worktree(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = authorized_parent_run(plan)
        run["observed"]["git"]["worktrees"] = [
            {
                "path": "C:/repo/untracked-worker",
                "branch_ref": "refs/heads/untracked",
                "head_sha": "b" * 40,
                "managed_by": "parent",
                "dirty": False,
            }
        ]

        result = select_ready_nodes(plan, run)

        self.assertEqual([], result["ready_frontier"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("worktree_state_unreconciled", deferred["N-M1"])

    def test_active_wave_streams_ready_preintegration_review(self) -> None:
        plan, run = current_preintegration_review_state()
        baseline = select_ready_nodes(plan, run)
        self.assertIn(
            "N-FRONTEND-REVIEW",
            [item["node_id"] for item in baseline["dispatchable_nodes"]],
        )

        run["active_wave"] = {
            "wave_id": "B01",
            "status": "active",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "batch_base_sha": "a" * 40,
            "selected_missions": ["M1"],
            "deferred_missions": [],
            "conflict_edges": [],
        }
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"] = {
            "host_version": "0.146.0",
            "minimum_host_version": None,
            "harness_version": "0.5.0",
            "required_harness_version": "0.6.0",
            "status": "compatible_old",
            "evidence": "old runtime remains compatible for the active wave",
        }
        self.assertEqual([], validate_run(plan, run))

        selected = select_ready_nodes(plan, run)
        self.assertIn(
            "N-FRONTEND-REVIEW",
            [item["node_id"] for item in selected["dispatchable_nodes"]],
        )

    def test_old_runtime_blocks_the_next_wave_until_upgrade_and_restart(self) -> None:
        for status, expected_reason in (
            ("compatible_old", "runtime_upgrade_pending"),
            ("upgrade_required", "runtime_upgrade_required"),
            ("restart_required", "runtime_restart_required"),
            ("unobserved", "runtime_version_unobserved"),
        ):
            with self.subTest(status=status):
                plan, run = self._authorized_conflict_free_pair()
                run["runtime_capabilities"]["runtime_adapter"]["version_gate"] = {
                    "host_version": "0.146.0",
                    "minimum_host_version": None,
                    "harness_version": "0.5.0",
                    "required_harness_version": "0.6.0",
                    "status": status,
                    "evidence": f"test version state: {status}",
                }

                selected = select_ready_nodes(plan, run)

                self.assertEqual([], selected["dispatchable_nodes"])
                deferred = {
                    item["node_id"]: item["reason_codes"]
                    for item in selected["deferred_nodes"]
                }
                self.assertIn(expected_reason, deferred["N-M1"])

    def test_legacy_v10_run_without_a_version_gate_must_be_observed(self) -> None:
        plan, run = self._authorized_conflict_free_pair()
        run["runtime_capabilities"]["runtime_adapter"].pop("version_gate")
        self.assertEqual([], validate_run(plan, run))

        selected = select_ready_nodes(plan, run)

        self.assertEqual([], selected["dispatchable_nodes"])
        deferred = {
            item["node_id"]: item["reason_codes"]
            for item in selected["deferred_nodes"]
        }
        self.assertIn("runtime_version_unobserved", deferred["N-M1"])

    def test_active_wave_still_defers_new_writer_nodes(self) -> None:
        plan = valid_graph_plan()
        run = authorized_parent_run(plan)
        run["active_wave"] = {
            "wave_id": "B01",
            "status": "active",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "batch_base_sha": "a" * 40,
            "selected_missions": ["M1"],
            "deferred_missions": [],
            "conflict_edges": [],
        }

        with patch("select_ready_nodes.validate_run", return_value=[]):
            selected = select_ready_nodes(plan, run)

        deferred = {
            item["node_id"]: item["reason_codes"]
            for item in selected["deferred_nodes"]
        }
        self.assertIn("blocker_present", deferred["N-M1"])

    def test_schema_mismatch_is_rejected_before_selection(self) -> None:
        # Structural validation normally rejects the pair first. Stub it so
        # this test guards select_ready_nodes's own defense-in-depth gate.
        plan = valid_graph_plan()
        run = valid_graph_run(plan)

        for plan_version, run_version in [(5, 6), (4, 8), (4, 9)]:
            with self.subTest(plan_version=plan_version, run_version=run_version):
                plan["schema_version"] = plan_version
                run["schema_version"] = run_version

                with patch("select_ready_nodes.validate_plan", return_value=[]), patch(
                    "select_ready_nodes.validate_run", return_value=[]
                ):
                    with self.assertRaises(GraphSelectionError) as ctx:
                        select_ready_nodes(plan, run)

                self.assertIn(
                    "typed graph selection requires PLAN v5 with RUN v10",
                    str(ctx.exception),
                )



if __name__ == "__main__":
    unittest.main()

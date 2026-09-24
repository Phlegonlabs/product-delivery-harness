#!/usr/bin/env python3
"""Regression tests for historical verifier evidence and current coverage."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import validate_run  # noqa: E402
import manifest_fixtures as mf  # noqa: E402


def _replace_execution(
    run: dict[str, object], execution_id: str, replacement: dict[str, object]
) -> None:
    run["verifier_executions"] = [
        replacement if item.get("execution_id") == execution_id else item
        for item in run["verifier_executions"]
    ]


def _advance_m1_lease(
    plan: dict[str, object], run: dict[str, object], *, retain_current_pass: bool
) -> None:
    old_worker = next(
        worker for worker in run["workers"] if worker["mission_id"] == "M1"
    )
    new_worker = copy.deepcopy(old_worker)
    new_worker.update({"worker_id": "W-M1-RETRY", "lease_id": "LEASE-M1-RETRY"})
    run["workers"].append(new_worker)

    mission_state = run["mission_states"]["M1"]
    mission_state.update(
        {"worker_id": new_worker["worker_id"], "lease_id": new_worker["lease_id"]}
    )
    mission_node = next(
        node
        for node in plan["graph"]["nodes"]
        if node["kind"] == "mission" and node["ref"] == "M1"
    )
    worker_attempt_id = "ATT-M1-RETRY"
    node_state = run["graph_state"]["node_states"][mission_node["id"]]
    node_state.update(
        {
            "attempts": node_state["attempts"] + 1,
            "last_attempt_id": worker_attempt_id,
            "bound_worker_id": new_worker["worker_id"],
        }
    )
    run["attempt_log"].append(
        {
            "attempt_id": worker_attempt_id,
            "mission_id": "M1",
            "task_id": None,
            "lease_id": new_worker["lease_id"],
            "kind": "worker_verifier",
            "result": "PASS",
            "evidence": [],
        }
    )
    run["authorizations"]["spawn_subagents"]["scope"]["targets"].append(
        f"worker:{new_worker['worker_id']}"
    )

    if not retain_current_pass:
        return

    mission = next(item for item in plan["missions"] if item["id"] == "M1")
    for index, task in enumerate(mission["tasks"], start=1):
        task_attempt_id = f"ATT-M1-RETRY-T{index}"
        run["attempt_log"].append(
            {
                "attempt_id": task_attempt_id,
                "mission_id": "M1",
                "task_id": task["id"],
                "lease_id": new_worker["lease_id"],
                "kind": "task_verifier",
                "result": "PASS",
                "evidence": [],
            }
        )
        for verifier in task["verifiers"]:
            run["verifier_executions"].append(
                mf.retained_gate_execution(
                    plan,
                    run,
                    verifier,
                    layer="task",
                    execution_id=f"EXEC-M1-RETRY-{task['id']}-{verifier['id']}",
                    mission_id="M1",
                    task_id=task["id"],
                    attempt_id=task_attempt_id,
                    lease_id=new_worker["lease_id"],
                    head_sha=run["task_states"][task["id"]]["commit_sha"],
                    checkout_role="worker",
                )
            )
    for verifier in mission["worker_verifiers"]:
        run["verifier_executions"].append(
            mf.retained_gate_execution(
                plan,
                run,
                verifier,
                layer="worker",
                execution_id=f"EXEC-M1-RETRY-{verifier['id']}",
                mission_id="M1",
                attempt_id=worker_attempt_id,
                lease_id=new_worker["lease_id"],
                head_sha=new_worker["worker_head_sha"],
                checkout_role="worker",
            )
        )


class HistoricalVerifierEvidenceTests(unittest.TestCase):
    def complete_pair(self) -> tuple[dict[str, object], dict[str, object]]:
        plan = mf.valid_plan()
        run = mf.valid_closeout_run(plan)
        mf.mark_complete(plan, run)
        self.assertEqual([], validate_run(plan, run))
        return plan, run

    def assert_error_contains(
        self, plan: dict[str, object], run: dict[str, object], expected: str
    ) -> None:
        errors = validate_run(plan, run)
        self.assertTrue(
            any(expected in error for error in errors),
            f"expected {expected!r} in {errors!r}",
        )

    def test_task_checkpoint_may_precede_worker_final_head(self) -> None:
        plan, run = self.complete_pair()
        task_id = "M1/T01"
        execution = next(
            item
            for item in run["verifier_executions"]
            if item["layer"] == "task" and item["task_id"] == task_id
        )
        declaration = next(
            task["verifiers"][0]
            for mission in plan["missions"]
            if mission["id"] == "M1"
            for task in mission["tasks"]
            if task["id"] == task_id
        )
        run["task_states"][task_id]["commit_sha"] = mf.SHA_D
        replacement = mf.retained_gate_execution(
            plan,
            run,
            declaration,
            layer="task",
            execution_id=execution["execution_id"],
            mission_id="M1",
            task_id=task_id,
            attempt_id=execution["attempt_id"],
            lease_id=execution["lease_id"],
            head_sha=mf.SHA_D,
            checkout_role="worker",
        )
        _replace_execution(run, execution["execution_id"], replacement)

        worker = next(item for item in run["workers"] if item["mission_id"] == "M1")
        self.assertNotEqual(run["task_states"][task_id]["commit_sha"], worker["worker_head_sha"])
        self.assertEqual([], validate_run(plan, run))

    def test_rekeyed_arbitrary_task_head_does_not_cover_current_checkpoint(self) -> None:
        plan, run = self.complete_pair()
        execution = next(
            item
            for item in run["verifier_executions"]
            if item["layer"] == "task" and item["task_id"] == "M1/T01"
        )
        declaration = next(
            task["verifiers"][0]
            for mission in plan["missions"]
            if mission["id"] == "M1"
            for task in mission["tasks"]
            if task["id"] == "M1/T01"
        )
        replacement = mf.retained_gate_execution(
            plan,
            run,
            declaration,
            layer="task",
            execution_id=execution["execution_id"],
            mission_id="M1",
            task_id="M1/T01",
            attempt_id=execution["attempt_id"],
            lease_id=execution["lease_id"],
            head_sha=mf.SHA_D,
            checkout_role="worker",
        )
        _replace_execution(run, execution["execution_id"], replacement)

        self.assert_error_contains(
            plan,
            run,
            "missing retained PASS execution for task verifier",
        )

    def test_historical_batch_and_final_heads_remain_valid(self) -> None:
        plan, run = self.complete_pair()
        run["integration"]["prior_head_shas"] = [mf.SHA_B]
        for layer, declarations in (
            ("batch", plan["batch_verifiers"]),
            ("final", plan["final_gates"]),
        ):
            for declaration in declarations:
                run["verifier_executions"].append(
                    mf.retained_gate_execution(
                        plan,
                        run,
                        declaration,
                        layer=layer,
                        execution_id=f"EXEC-HISTORICAL-{layer}-{declaration['id']}",
                        head_sha=mf.SHA_B,
                    )
                )

        self.assertEqual([], validate_run(plan, run))

    def test_pending_mission_integration_evidence_binds_current_observed_head(
        self,
    ) -> None:
        plan, run = self.complete_pair()
        mission_state = run["mission_states"]["M1"]
        mission_state.update(
            {
                "phase": "worker_passed",
                "head_sha": mf.SHA_B,
                "integrated_sha": None,
                "integration_gate": "planned",
            }
        )
        run["status"] = "running"
        run["observed"]["git"]["parent_head_sha"] = mf.SHA_C
        mission_node = next(
            node
            for node in plan["graph"]["nodes"]
            if node["kind"] == "mission" and node["ref"] == "M1"
        )
        run["graph_state"]["node_states"][mission_node["id"]].update(
            {"phase": "running", "last_outcome": None}
        )
        for edge in plan["graph"]["edges"]:
            if edge["from"] == mission_node["id"]:
                run["graph_state"]["edge_states"][edge["id"]].update(
                    {
                        "status": "dormant",
                        "traversals": 0,
                        "source_attempt_id": None,
                    }
                )
        runtime_adapter = run["runtime_capabilities"]["runtime_adapter"]
        runtime_adapter["detection_source"] = "observed"
        runtime_adapter["capability_probe"] = mf.native_capability_probe(
            subagents=True
        )
        execution = next(
            item
            for item in run["verifier_executions"]
            if item["layer"] == "mission_integration" and item["mission_id"] == "M1"
        )
        declaration = plan["missions"][0]["integration_verifiers"][0]
        pending = mf.retained_gate_execution(
            plan,
            run,
            declaration,
            layer="mission_integration",
            execution_id=execution["execution_id"],
            mission_id="M1",
            head_sha=mf.SHA_C,
        )
        _replace_execution(run, execution["execution_id"], pending)

        self.assertEqual([], validate_run(plan, run))

        arbitrary = mf.retained_gate_execution(
            plan,
            run,
            declaration,
            layer="mission_integration",
            execution_id=execution["execution_id"],
            mission_id="M1",
            head_sha=mf.SHA_D,
        )
        _replace_execution(run, execution["execution_id"], arbitrary)
        self.assert_error_contains(
            plan,
            run,
            "context.head_sha: must match the mission integrated_sha",
        )

        mission_state.update(
            {
                "phase": "integrated",
                "integration_gate": "PASS",
                "integrated_sha": mf.SHA_C,
            }
        )
        run["observed"]["git"]["parent_head_sha"] = mf.SHA_D
        finalized_wrong_head = mf.retained_gate_execution(
            plan,
            run,
            declaration,
            layer="mission_integration",
            execution_id=execution["execution_id"],
            mission_id="M1",
            head_sha=mf.SHA_D,
        )
        _replace_execution(run, execution["execution_id"], finalized_wrong_head)
        self.assert_error_contains(
            plan,
            run,
            "context.head_sha: must match the mission integrated_sha",
        )

    def test_historical_gate_pass_cannot_cover_current_result(self) -> None:
        plan, run = self.complete_pair()
        run["integration"]["prior_head_shas"] = [mf.SHA_B]
        declaration = plan["batch_verifiers"][0]
        historical = mf.retained_gate_execution(
            plan,
            run,
            declaration,
            layer="batch",
            execution_id="EXEC-HISTORICAL-BATCH-STALE",
            head_sha=mf.SHA_B,
        )
        run["verifier_executions"].append(historical)
        run["batch_gate_results"][0].update(
            {
                "status": "PASS",
                "head_sha": mf.SHA_B,
                "evidence": [historical["evidence_key"]],
            }
        )

        self.assert_error_contains(
            plan,
            run,
            "PASS batch gate must match integration_head_sha",
        )

    def test_integrated_worker_history_survives_later_worktree_advance(self) -> None:
        plan, run = self.complete_pair()
        worker = next(item for item in run["workers"] if item["mission_id"] == "M1")
        observed = next(
            item
            for item in run["observed"]["git"]["worktrees"]
            if item["path"] == worker["worktree_path"]
        )
        observed["head_sha"] = mf.SHA_D

        self.assertEqual([], validate_run(plan, run))

    def test_current_passed_worker_requires_exact_live_observation(self) -> None:
        plan, run = self.complete_pair()
        run["status"] = "running"
        run["mission_states"]["M1"]["phase"] = "worker_passed"
        worker = next(item for item in run["workers"] if item["mission_id"] == "M1")
        observed = next(
            item
            for item in run["observed"]["git"]["worktrees"]
            if item["path"] == worker["worktree_path"]
        )
        observed["head_sha"] = mf.SHA_D

        self.assert_error_contains(
            plan,
            run,
            "requires one matching parent-observed isolated worktree and branch",
        )

    def test_old_lease_evidence_survives_when_current_lease_is_covered(self) -> None:
        plan, run = self.complete_pair()
        _advance_m1_lease(plan, run, retain_current_pass=True)

        self.assertEqual([], validate_run(plan, run))

    def test_old_lease_evidence_does_not_cover_the_current_lease(self) -> None:
        plan, run = self.complete_pair()
        _advance_m1_lease(plan, run, retain_current_pass=False)

        self.assert_error_contains(
            plan,
            run,
            "missing retained PASS execution for task verifier",
        )
        self.assert_error_contains(
            plan,
            run,
            "missing retained PASS execution for worker verifier",
        )

    def test_released_mission_waits_for_new_result_before_requiring_new_passes(
        self,
    ) -> None:
        plan, run = self.complete_pair()
        _advance_m1_lease(plan, run, retain_current_pass=False)
        mission_state = run["mission_states"]["M1"]
        worker = next(
            item for item in run["workers"] if item["worker_id"] == "W-M1-RETRY"
        )
        mission_state["phase"] = "worker_running"
        worker["phase"] = "worker_running"
        worker["worker_head_sha"] = None

        running_errors = validate_run(plan, run)
        self.assertFalse(
            any("missing retained PASS execution for task verifier" in error for error in running_errors),
            running_errors,
        )
        self.assertFalse(
            any("missing retained PASS execution for worker verifier" in error for error in running_errors),
            running_errors,
        )

        mission_state["phase"] = "worker_passed"
        worker["phase"] = "worker_passed"
        worker["worker_head_sha"] = mf.SHA_B
        self.assert_error_contains(
            plan,
            run,
            "missing retained PASS execution for task verifier",
        )
        self.assert_error_contains(
            plan,
            run,
            "missing retained PASS execution for worker verifier",
        )


if __name__ == "__main__":
    unittest.main()

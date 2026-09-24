"""Candidate-head reconciliation after every mission is integrated."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for candidate in (TESTS_DIR, SCRIPTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import harness_transition  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
from harness_core import ManifestError  # noqa: E402
from harness_manifest import validate_run  # noqa: E402


class CandidateResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = mf.valid_plan()
        final_node = next(
            node for node in self.plan["graph"]["nodes"] if node["id"] == "N-FINAL"
        )
        final_node["allowed_outcomes"].append("retryable_failure")
        self.run = mf.valid_run(self.plan)
        mf.mark_complete(self.plan, self.run)
        self.run["status"] = "running"
        self.run["active_wave"]["status"] = "idle"
        adapter = self.run["runtime_capabilities"]["runtime_adapter"]
        adapter["detection_source"] = "observed"
        adapter["capability_probe"] = mf.native_capability_probe(subagents=True)

        # The closeout fixture predates durable non-runtime reservation logs.
        # Retain its deterministic attempt identities so resetting their current
        # projections exercises the same historical-edge rule as a live RUN.
        nodes = {node["id"]: node for node in self.plan["graph"]["nodes"]}
        retained = {item["attempt_id"] for item in self.run["attempt_log"]}
        for node_id, state in self.run["graph_state"]["node_states"].items():
            attempt_id = state.get("last_attempt_id")
            node = nodes[node_id]
            if (
                isinstance(attempt_id, str)
                and attempt_id not in retained
                and node.get("executor") in {"local_command", "harness_parent"}
            ):
                self.run["attempt_log"].append(
                    {
                        "attempt_id": attempt_id,
                        "mission_id": None,
                        "task_id": None,
                        "lease_id": None,
                        "kind": "historical_graph_attempt",
                        "result": "pass",
                        "evidence": ["retained fixture graph attempt"],
                    }
                )
                retained.add(attempt_id)

        self.previous_head = self.run["integration"]["integration_head_sha"]
        final_state = self.run["graph_state"]["node_states"]["N-FINAL"]
        final_attempt_id = final_state["last_attempt_id"]
        self.repair_attempt_id = final_attempt_id
        final_state.update(
            {
                "phase": "failed",
                "last_outcome": "retryable_failure",
                "bound_worker_id": None,
                "blockers": [],
            }
        )
        final_result = self.run["final_gate_results"][0]
        final_result.update(
            {
                "status": "BLOCKED",
                "head_sha": self.previous_head,
                "evidence": ["final gate failure retained"],
            }
        )
        final_attempt = next(
            item
            for item in self.run["attempt_log"]
            if item.get("attempt_id") == final_attempt_id
        )
        final_request = {
            "node_id": "N-FINAL",
            "attempt_id": final_attempt_id,
            "branch": "codex/test",
            "head_sha": self.previous_head,
            "checkout_root": "C:/repo/product-delivery-harness",
            "reservation": {
                "node_id": "N-FINAL",
                "attempt_id": final_attempt_id,
                "nonce": "retained-final-gate-failure",
            },
        }
        final_attempt.update(
            {
                "kind": "node_attempt",
                "node_id": "N-FINAL",
                "result": "retryable_failure",
                "evidence": ["final gate found a task-scoped repair"],
                "verifier_dispatch": {
                    "branch": final_request["branch"],
                    "head_sha": final_request["head_sha"],
                    "checkout_root": final_request["checkout_root"],
                    "request_sha256": harness_transition._json_sha256(final_request),
                    "request": final_request,
                },
            }
        )
        commit_targets = self.run["authorizations"]["create_local_commits"][
            "scope"
        ]["targets"]
        if "branch:codex/test" not in commit_targets:
            commit_targets.append("branch:codex/test")

        self.candidate = "e" * 40
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name).resolve()
        self.run["observed"]["captured_at"] = "2026-09-24T00:00:00Z"
        self.run["observed"]["git"].update(
            {
                "parent_worktree_path": str(self.root),
                "parent_branch": "codex/test",
                "parent_head_sha": self.candidate,
                "parent_dirty": False,
            }
        )

    def args(self, **overrides: object) -> Namespace:
        values = {
            "repo_root": self.root,
            "run": None,
            "candidate_sha": self.candidate,
            "source": "post-integration repair commit verified by the parent",
            "repair_node_id": "N-FINAL",
            "repair_attempt_id": self.repair_attempt_id,
            "repair_task_id": "M1/T01",
        }
        values.update(overrides)
        return Namespace(**values)

    def git_out(self, _root: Path, *arguments: str) -> str:
        if arguments == ("rev-parse", "--show-toplevel"):
            return str(self.root) + "\n"
        if arguments == ("rev-parse", "--abbrev-ref", "HEAD"):
            return "codex/test\n"
        if arguments == ("rev-parse", "HEAD"):
            return self.candidate + "\n"
        if arguments and arguments[0] == "status":
            return ""
        raise AssertionError(arguments)

    def reconcile(self, **overrides: object) -> dict[str, object]:
        changed_paths = overrides.pop("changed_paths", ["src/a/one.py"])
        ancestor = overrides.pop("ancestor", True)
        git_out_side_effect = overrides.pop("git_out_side_effect", self.git_out)
        with (
            mock.patch.object(
                harness_transition, "_git_out", side_effect=git_out_side_effect
            ),
            mock.patch.object(
                harness_transition, "_git_is_ancestor", return_value=ancestor
            ),
            mock.patch.object(
                harness_transition,
                "_candidate_changed_paths",
                return_value=changed_paths,
            ),
        ):
            return harness_transition._reconcile_candidate_head(
                self.plan, self.run, self.args(**overrides)
            )

    def test_forward_repair_stays_in_run_and_rearms_current_gates(self) -> None:
        preserved = {
            key: copy.deepcopy(self.run[key])
            for key in (
                "mission_states",
                "task_states",
                "workers",
                "review_workers",
                "review_lineages",
                "verifier_executions",
                "authorizations",
            )
        }
        preserved_attempt_counts = {
            node_id: state["attempts"]
            for node_id, state in self.run["graph_state"]["node_states"].items()
        }

        receipt = self.reconcile()

        self.assertEqual("reconcile-candidate-head", receipt["command"])
        self.assertEqual(self.candidate, self.run["integration"]["integration_head_sha"])
        self.assertEqual(
            [self.previous_head], self.run["integration"]["prior_head_shas"]
        )
        for key, expected in preserved.items():
            self.assertEqual(expected, self.run[key], key)
        for result in [
            *self.run["batch_gate_results"],
            *self.run["final_gate_results"],
        ]:
            self.assertEqual(
                {"id": result["id"], "status": "planned", "head_sha": None, "evidence": []},
                result,
            )
        for node_id in receipt["revalidation_nodes"]:
            state = self.run["graph_state"]["node_states"][node_id]
            self.assertEqual("ready", state["phase"])
            self.assertEqual(preserved_attempt_counts[node_id], state["attempts"])
        self.assertEqual([], validate_run(self.plan, self.run))

        verifier_request = {
            "node_id": "N-REVIEW-PASS-M1",
            "attempt_id": "ATT-BATCH-REPAIR-2",
            "branch": "codex/test",
            "head_sha": self.candidate,
            "checkout_root": str(self.root),
            "reservation": {
                "node_id": "N-REVIEW-PASS-M1",
                "attempt_id": "ATT-BATCH-REPAIR-2",
                "nonce": "candidate-repair-reservation",
            },
        }
        with (
            mock.patch.object(
                harness_transition,
                "select_ready_nodes",
                return_value={
                    "dispatchable_nodes": [
                        {
                            "node_id": "N-REVIEW-PASS-M1",
                            "kind": "verifier",
                            "executor": "local_command",
                        }
                    ],
                    "deferred_nodes": [],
                },
            ),
            mock.patch.object(
                harness_transition,
                "_local_verifier_request",
                return_value=verifier_request,
            ),
        ):
            harness_transition._reserve_node_attempt(
                self.plan,
                self.run,
                Namespace(
                    node_id="N-REVIEW-PASS-M1",
                    attempt_id="ATT-BATCH-REPAIR-2",
                    evidence=["fresh batch check for repaired candidate"],
                    repo_root=self.root,
                    run=None,
                    request_out=None,
                ),
            )
        self.assertEqual(
            "running",
            self.run["graph_state"]["node_states"]["N-REVIEW-PASS-M1"]["phase"],
        )
        self.assertEqual([], validate_run(self.plan, self.run))

    def test_same_head_does_not_consume_another_attempt(self) -> None:
        self.run["observed"]["git"]["parent_head_sha"] = self.previous_head
        before = copy.deepcopy(self.run)
        with self.assertRaisesRegex(ManifestError, "no reconciliation is needed"):
            self.reconcile(candidate_sha=self.previous_head)
        self.assertEqual(before, self.run)

    def test_dirty_diverged_wrong_branch_wrong_repo_and_out_of_scope_refuse(self) -> None:
        cases = []

        dirty = copy.deepcopy(self.run)
        dirty["observed"]["git"]["parent_dirty"] = True
        cases.append((dirty, {}, "clean product tree"))

        wrong_branch = copy.deepcopy(self.run)
        wrong_branch["observed"]["git"]["parent_branch"] = "other"
        cases.append((wrong_branch, {}, "live and observed parent branch"))

        wrong_repo = copy.deepcopy(self.run)
        wrong_repo["observed"]["git"]["parent_worktree_path"] = str(
            self.root / "other"
        )
        cases.append((wrong_repo, {}, "not the observed parent worktree"))

        cases.append((copy.deepcopy(self.run), {"ancestor": False}, "not an ancestor"))
        cases.append(
            (
                copy.deepcopy(self.run),
                {"changed_paths": ["outside/repair.py"]},
                "outside declared mission/integration scopes",
            )
        )

        original = self.run
        try:
            for candidate_run, options, message in cases:
                with self.subTest(message=message):
                    self.run = candidate_run
                    before = copy.deepcopy(candidate_run)
                    with self.assertRaisesRegex(ManifestError, message):
                        self.reconcile(**options)
                    self.assertEqual(before, candidate_run)
        finally:
            self.run = original

    def test_active_work_and_exhausted_gate_budget_refuse(self) -> None:
        self.run["active_wave"].update(
            {
                "status": "active",
                "wave_id": "W-ACTIVE",
                "batch_base_sha": self.previous_head,
            }
        )
        with self.assertRaisesRegex(ManifestError, "active or proposed wave"):
            self.reconcile()

        self.run["active_wave"]["status"] = "idle"
        node = next(
            item
            for item in self.plan["graph"]["nodes"]
            if item["id"] == "N-FINAL"
        )
        self.run["graph_state"]["node_states"]["N-FINAL"]["attempts"] = node[
            "max_attempts"
        ]
        with self.assertRaisesRegex(ManifestError, "attempt budget is exhausted"):
            self.reconcile()

    def test_repair_requires_current_receipt_task_and_exact_action_grants(self) -> None:
        with self.assertRaisesRegex(ManifestError, "current terminal attempt"):
            self.reconcile(repair_attempt_id="ATT-OTHER")
        with self.assertRaisesRegex(ManifestError, "exactly one existing PLAN task"):
            self.reconcile(repair_task_id="M1/T99")

        repair_state = self.run["graph_state"]["node_states"]["N-FINAL"]
        repair_attempt = next(
            item
            for item in self.run["attempt_log"]
            if item.get("attempt_id") == self.repair_attempt_id
        )
        repair_state.update({"phase": "blocked", "last_outcome": "contract_gap"})
        repair_attempt["result"] = "contract_gap"
        with self.assertRaisesRegex(ManifestError, "does not match"):
            self.reconcile()
        repair_state.update(
            {"phase": "failed", "last_outcome": "retryable_failure"}
        )
        repair_attempt["result"] = "retryable_failure"

        targets = self.run["authorizations"]["create_local_commits"]["scope"][
            "targets"
        ]
        targets.remove("branch:codex/test")
        with self.assertRaisesRegex(ManifestError, "exact create_local_commits"):
            self.reconcile()

    def test_integration_security_review_is_fresh_and_history_is_immutable(self) -> None:
        node = {
            "id": "N-SECURITY",
            "kind": "verifier",
            "ref": "security",
            "executor": "runtime_worker",
            "max_attempts": 2,
            "review": {
                "type": "security",
                "stage": "integration",
                "lineage_id": "REVIEW-SECURITY",
            },
        }
        historical_worker = {
            "worker_id": "RW-SECURITY-1",
            "node_id": "N-SECURITY",
            "attempt_id": "ATT-SECURITY-1",
            "reviewed_sha": self.previous_head,
            "phase": "worker_passed",
            "outcome": "pass",
            "findings": [],
        }
        plan = {
            "batch_verifiers": [],
            "final_gates": [],
            "graph": {"nodes": [node], "edges": []},
        }
        run = {
            "integration": {
                "integration_head_sha": self.previous_head,
                "integration_tree_sha": "f" * 40,
            },
            "batch_gate_results": [],
            "final_gate_results": [],
            "ui_evidence": [],
            "review_workers": [copy.deepcopy(historical_worker)],
            "graph_state": {
                "node_states": {
                    "N-SECURITY": {
                        "phase": "succeeded",
                        "attempts": 1,
                        "last_attempt_id": "ATT-SECURITY-1",
                        "last_outcome": "pass",
                        "bound_worker_id": "RW-SECURITY-1",
                        "blockers": [],
                    }
                }
            },
        }

        harness_transition._invalidate_stale_current_projections(
            plan, run, self.previous_head, self.candidate
        )

        state = run["graph_state"]["node_states"]["N-SECURITY"]
        self.assertEqual("ready", state["phase"])
        self.assertEqual(1, state["attempts"])
        self.assertEqual([historical_worker], run["review_workers"])
        self.assertNotIn("integration_tree_sha", run["integration"])

    def test_inactive_skipped_integration_review_refuses_without_mutation(self) -> None:
        review_node = copy.deepcopy(
            next(
                node
                for node in self.plan["graph"]["nodes"]
                if node["id"] == "N-REVIEW-M2"
            )
        )
        review_node["id"] = "N-INTEGRATION-REVIEW"
        review_node["allowed_outcomes"] = ["pass", "blocked", "contract_gap"]
        review_node["review"].update(
            {"stage": "integration", "lineage_id": "REVIEW-INTEGRATION"}
        )
        self.plan["graph"]["nodes"].append(review_node)
        self.plan["graph"]["edges"].extend(
            [
                {
                    "id": "E-INACTIVE-INTEGRATION-REVIEW",
                    "kind": "route",
                    "from": "N-REVIEW-M2",
                    "to": "N-INTEGRATION-REVIEW",
                    "on_outcomes": ["blocked"],
                    "max_traversals": 1,
                },
                {
                    "id": "E-INTEGRATION-REVIEW-PASS",
                    "kind": "route",
                    "from": "N-INTEGRATION-REVIEW",
                    "to": "N-FINAL",
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
            ]
        )
        run = mf.valid_run(self.plan)
        mf.mark_complete(self.plan, run)
        run["status"] = "running"
        run["active_wave"]["status"] = "idle"
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter["detection_source"] = "observed"
        adapter["capability_probe"] = mf.native_capability_probe(subagents=True)
        skipped = run["graph_state"]["node_states"]["N-INTEGRATION-REVIEW"]
        skipped_attempt = skipped["last_attempt_id"]
        skipped.update(
            {
                "phase": "skipped",
                "attempts": 0,
                "last_attempt_id": None,
                "last_outcome": None,
                "bound_worker_id": None,
                "blockers": [],
            }
        )
        for edge_id in (
            "E-INACTIVE-INTEGRATION-REVIEW",
            "E-INTEGRATION-REVIEW-PASS",
        ):
            run["graph_state"]["edge_states"][edge_id].update(
                {"status": "skipped", "traversals": 0, "source_attempt_id": None}
            )
        run["integration"]["integration_tree_sha"] = "a" * 40
        preintegration_worker = next(
            worker
            for worker in run["review_workers"]
            if worker["node_id"] == "N-REVIEW-M2"
        )
        preintegration_worker["tree_sha"] = "a" * 40
        run["review_workers"] = [
            worker
            for worker in run["review_workers"]
            if worker["node_id"] != "N-INTEGRATION-REVIEW"
        ]
        run["attempt_log"] = [
            attempt
            for attempt in run["attempt_log"]
            if attempt["attempt_id"] != skipped_attempt
        ]
        run["review_lineages"]["REVIEW-INTEGRATION"]["consumed_attempts"] = 0
        self.assertEqual([], validate_run(self.plan, run))
        before = copy.deepcopy(run)
        self.run = run

        with self.assertRaisesRegex(ManifestError, "refine the recovery graph"):
            self.reconcile()

        self.assertEqual(before, self.run)

        integration_run = copy.deepcopy(run)
        integration_run["mission_states"]["M1"].update(
            {
                "phase": "worker_passed",
                "head_sha": self.candidate,
                "integration_gate": "planned",
                "integrated_sha": None,
            }
        )
        integration_run["observed"]["git"].update(
            {
                "parent_worktree_path": str(self.root),
                "parent_branch": "codex/test",
                "parent_head_sha": self.candidate,
                "parent_dirty": False,
            }
        )
        before_integration = copy.deepcopy(integration_run)
        self.run = integration_run
        with (
            mock.patch.object(harness_transition, "_git_out", side_effect=self.git_out),
            mock.patch.object(harness_transition, "_git_is_ancestor", return_value=True),
            mock.patch.object(
                harness_transition, "_candidate_changed_paths", return_value=[]
            ),
        ):
            with self.assertRaisesRegex(ManifestError, "refine the recovery graph"):
                harness_transition._record_integration(
                    self.plan,
                    self.run,
                    Namespace(
                        mission_id="M1",
                        integrated_sha=self.candidate,
                        repo_root=self.root,
                        run=None,
                    ),
                )
        self.assertEqual(before_integration, self.run)

    def test_second_live_git_read_rejects_concurrent_head_change(self) -> None:
        head_reads = 0

        def drifting_git_out(root: Path, *arguments: str) -> str:
            nonlocal head_reads
            if arguments == ("rev-parse", "HEAD"):
                head_reads += 1
                return (self.candidate if head_reads == 1 else "d" * 40) + "\n"
            return self.git_out(root, *arguments)

        before = copy.deepcopy(self.run)
        with self.assertRaisesRegex(ManifestError, "changed during"):
            self.reconcile(git_out_side_effect=drifting_git_out)
        self.assertEqual(before, self.run)

    def test_cli_registers_candidate_reconciliation_as_locked_checkpoint(self) -> None:
        args = harness_transition.build_parser().parse_args(
            [
                "--plan",
                "PLAN.md",
                "--run",
                "RUN.md",
                "--repo-root",
                str(self.root),
                "reconcile-candidate-head",
                "--candidate-sha",
                self.candidate,
                "--source",
                "repair",
                "--repair-node-id",
                "N-FINAL",
                "--repair-attempt-id",
                self.run["graph_state"]["node_states"]["N-FINAL"][
                    "last_attempt_id"
                ],
                "--repair-task-id",
                "M1/T01",
            ]
        )
        self.assertEqual("reconcile-candidate-head", args.command)
        self.assertIn(args.command, harness_transition.DISPATCH_COMMANDS)
        self.assertIn(args.command, harness_transition.TASK_VIEW_CHECKPOINTS)


if __name__ == "__main__":
    unittest.main()

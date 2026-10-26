"""Scoped repair reviews: recorded repair scopes and scoped review passes.

The owner decision (2026-10-26) is two full-scope reviews per candidate
(initial plus one re-check). Any later defect is repaired in isolation and
re-reviewed with a scoped review of the repair diff only; never another
full-scope review. These tests pin the transition, manifest, and packet
contract that makes the scoped route expressible.
"""

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
for path in (TESTS_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import harness_transition as harness_transition  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
from harness_manifest import ManifestError, validate_run  # noqa: E402
from verifier_runtime import execution_key_from_document  # noqa: E402


class RepairScopeRecordingTests(unittest.TestCase):
    """reconcile-candidate-head --repair-path records the scoped repair."""

    def setUp(self) -> None:
        self.plan = mf.valid_plan()
        self.plan["missions"][0]["tasks"][0]["write_scope"] = [
            "src/a/one.py",
            "src/a/two.py",
        ]
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

        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name).resolve()
        mf.init_repo(self.root, "README.md", default_branch="codex/test")
        repair_file = self.root / "src" / "a" / "one.py"
        repair_file.parent.mkdir(parents=True, exist_ok=True)
        repair_file.write_text("VALUE = 0\n", encoding="utf-8")
        mf.git(self.root, "add", "src/a/one.py")
        mf.git(self.root, "commit", "-qm", "integrated candidate")
        self.previous_head = mf.git(self.root, "rev-parse", "HEAD")
        repair_file.write_text("VALUE = 1\n", encoding="utf-8")
        mf.git(self.root, "commit", "-qam", "repair the finding")
        self.candidate = mf.git(self.root, "rev-parse", "HEAD")

        # Rebind the closeout fixture's synthetic integration head to the real
        # candidate head everywhere, so retained PASS projections stay valid.
        fixture_head = self.run["integration"]["integration_head_sha"]
        self._replace_sha(self.run, fixture_head, self.previous_head)
        self.run["integration"]["integration_head_sha"] = self.previous_head
        rekeyed: dict[str, str] = {}
        for execution in self.run["verifier_executions"]:
            document = execution.get("key_document")
            if isinstance(document, dict):
                old_key = execution.get("execution_key")
                key = execution_key_from_document(document)
                execution["execution_key"] = key
                execution["evidence_key"] = key
                if isinstance(old_key, str):
                    rekeyed[old_key] = key
        for result in [
            *self.run["batch_gate_results"],
            *self.run["final_gate_results"],
        ]:
            result["evidence"] = [
                rekeyed.get(item, item) for item in result.get("evidence", [])
            ]
        final_state = self.run["graph_state"]["node_states"]["N-FINAL"]
        self.repair_attempt_id = final_state["last_attempt_id"]
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
            if item.get("attempt_id") == self.repair_attempt_id
        )
        final_request = {
            "node_id": "N-FINAL",
            "attempt_id": self.repair_attempt_id,
            "branch": "codex/test",
            "head_sha": self.previous_head,
            "checkout_root": str(self.root),
            "reservation": {
                "node_id": "N-FINAL",
                "attempt_id": self.repair_attempt_id,
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
        self.run["observed"]["captured_at"] = "2026-10-26T00:00:00Z"
        self.run["observed"]["git"].update(
            {
                "parent_worktree_path": str(self.root),
                "parent_branch": "codex/test",
                "parent_head_sha": self.candidate,
                "parent_dirty": False,
            }
        )

    def _replace_sha(self, value: object, old: str, new: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if item == old:
                    value[key] = new
                else:
                    self._replace_sha(item, old, new)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if item == old:
                    value[index] = new
                else:
                    self._replace_sha(item, old, new)

    def args(self, **overrides: object) -> Namespace:
        values = {
            "repo_root": self.root,
            "run": None,
            "candidate_sha": self.candidate,
            "source": "post-integration repair commit verified by the parent",
            "repair_node_id": "N-FINAL",
            "repair_attempt_id": self.repair_attempt_id,
            "repair_task_id": "M1/T01",
            "repair_path": None,
            "trust_boundary": False,
        }
        values.update(overrides)
        return Namespace(**values)

    def reconcile(self, **overrides: object) -> dict[str, object]:
        with mock.patch.object(
            harness_transition, "_git_is_ancestor", return_value=True
        ):
            return harness_transition._reconcile_candidate_head(
                self.plan, self.run, self.args(**overrides)
            )

    def test_repair_path_records_the_scope_validated_against_the_real_diff(self) -> None:
        self.assertEqual([], validate_run(self.plan, self.run))
        receipt = self.reconcile(repair_path=["src/a/one.py"])

        self.assertEqual("reconcile-candidate-head", receipt["command"])
        self.assertEqual(
            [
                {
                    "candidate_sha": self.candidate,
                    "prior_head_sha": self.previous_head,
                    "repair_paths": ["src/a/one.py"],
                    "source": "post-integration repair commit verified by the parent",
                    "trust_boundary": False,
                }
            ],
            self.run["integration"]["repair_scopes"],
        )
        self.assertEqual(
            [self.previous_head], self.run["integration"]["prior_head_shas"]
        )
        self.assertEqual([], validate_run(self.plan, self.run))

    def test_multiple_repair_paths_cover_a_multi_file_real_diff(self) -> None:
        second = self.root / "src" / "a" / "two.py"
        second.write_text("TWO = 2\n", encoding="utf-8")
        mf.git(self.root, "add", "src/a/two.py")
        mf.git(self.root, "commit", "-qm", "second repair file")
        self.candidate = mf.git(self.root, "rev-parse", "HEAD")
        self.run["observed"]["git"]["parent_head_sha"] = self.candidate

        self.reconcile(repair_path=["src/a/one.py", "src/a/two.py"])

        self.assertEqual(
            ["src/a/one.py", "src/a/two.py"],
            self.run["integration"]["repair_scopes"][0]["repair_paths"],
        )
        self.assertEqual([], validate_run(self.plan, self.run))

    def test_trust_boundary_flag_is_recorded_on_the_entry(self) -> None:
        self.reconcile(repair_path=["src/a/one.py"], trust_boundary=True)

        self.assertIs(
            True, self.run["integration"]["repair_scopes"][0]["trust_boundary"]
        )

    def test_changed_path_outside_the_declared_scope_is_refused_by_name(self) -> None:
        before = copy.deepcopy(self.run)

        with self.assertRaisesRegex(ManifestError, "src/a/one.py"):
            self.reconcile(repair_path=["src/other.py"])

        self.assertEqual(before, self.run)
        self.assertNotIn("repair_scopes", self.run["integration"])

    def test_invalid_repair_paths_are_refused_before_mutation(self) -> None:
        for bad in ("/abs/path", "../escape.py", "src\\win.py", ""):
            with self.subTest(bad=bad):
                before = copy.deepcopy(self.run)
                with self.assertRaises(ManifestError):
                    self.reconcile(repair_path=[bad])
                self.assertEqual(before, self.run)

    def test_without_repair_path_no_scope_is_recorded(self) -> None:
        self.reconcile()

        self.assertNotIn("repair_scopes", self.run["integration"])
        self.assertEqual([], validate_run(self.plan, self.run))


if __name__ == "__main__":
    unittest.main()

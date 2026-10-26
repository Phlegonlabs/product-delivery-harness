"""Scoped repair reviews: recorded repair scopes and scoped review passes.

The owner decision (2026-10-26) is two full-scope reviews per candidate
(initial plus one re-check). Any later defect is repaired in isolation and
re-reviewed with a scoped review of the repair diff only; never another
full-scope review. These tests pin the transition, manifest, and packet
contract that makes the scoped route expressible.
"""

from __future__ import annotations

import copy
import json
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
from harness_manifest import ManifestError, plan_digest, validate_run  # noqa: E402
from render_review_packet import render_packet  # noqa: E402
from test_security_review_result import valid_result  # noqa: E402
from verifier_runtime import execution_key_from_document  # noqa: E402


def packet_contract(packet: str) -> dict[str, object]:
    block = packet.split("## Contract", 1)[1].split("```json", 1)[1]
    return json.loads(block.split("```", 1)[0])


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

    def test_scoped_repair_reconciles_past_the_exhausted_budget(self) -> None:
        self.run["graph_state"]["node_states"]["N-FINAL"]["attempts"] = 2

        with self.assertRaisesRegex(ManifestError, "attempt budget is exhausted"):
            self.reconcile()

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
        self.assertEqual([], validate_run(self.plan, self.run))


class ScopedReviewPassTests(unittest.TestCase):
    """record-review-attempt --scoped accepts the repair diff and refunds."""

    HEAD = "b" * 40
    PRIOR = "a" * 40
    REPAIR_PATHS = ["src/a/one.py"]

    def setUp(self) -> None:
        self.plan = mf.valid_plan()
        node = copy.deepcopy(self.plan["graph"]["nodes"][1])
        node["id"] = "N-EXTRA-REVIEW"
        node["allowed_outcomes"] = [
            "pass",
            "fix_required",
            "retryable_failure",
            "contract_gap",
            "blocked",
        ]
        node["review"].update(
            stage="integration", lineage_id="RL-EXTRA", mission_ids=["M1", "M2"]
        )
        self.review_node = node
        self.plan["graph"]["nodes"].append(node)
        self.plan["graph"]["edges"].extend(
            [
                {
                    "id": "E-EXTRA-READY",
                    "kind": "dependency",
                    "from": "N-M2",
                    "to": node["id"],
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
                {
                    "id": "E-EXTRA-PASS",
                    "kind": "route",
                    "from": node["id"],
                    "to": "N-FINAL",
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
            ]
        )
        self.run = mf.valid_run(self.plan)
        self.run["status"] = "running"
        self.run["integration"].update(
            {
                "integration_head_sha": self.HEAD,
                "prior_head_shas": [self.PRIOR],
                "repair_scopes": [
                    {
                        "candidate_sha": self.HEAD,
                        "prior_head_sha": self.PRIOR,
                        "repair_paths": list(self.REPAIR_PATHS),
                        "source": "isolated repair commit",
                        "trust_boundary": False,
                    }
                ],
            }
        )
        for edge in self.plan["graph"]["edges"]:
            self.run["graph_state"]["edge_states"].setdefault(
                edge["id"],
                {"status": "dormant", "traversals": 0, "source_attempt_id": None},
            )
        self.state = self.run["graph_state"]["node_states"][node["id"]]
        self.state.update(
            {
                "phase": "running",
                "attempts": 2,
                "last_attempt_id": "ATT-SCOPED",
                "last_outcome": None,
                "bound_worker_id": "RW-SCOPED",
                "blockers": [],
            }
        )
        self.worker = {
            "worker_id": "RW-SCOPED",
            "node_id": node["id"],
            "attempt_id": "ATT-SCOPED",
            "plan_revision": self.plan["revision"],
            "plan_digest_sha256": mf.valid_run(self.plan)["plan"]["digest_sha256"],
            "graph_revision": self.run["graph_state"]["graph_revision"],
            "reviewed_sha": self.HEAD,
            "review_path": "C:/repo",
            "worker_runtime": "parent",
            "completion_channel": "agent_result",
            "runtime_binding": {},
            "task_thread_id": None,
            "report_path": None,
            "phase": "leased",
            "outcome": None,
            "findings": [],
        }
        self.run["review_workers"].append(self.worker)

    def entry(self, **overrides: object) -> dict[str, object]:
        value = {
            "candidate_sha": self.HEAD,
            "prior_head_sha": self.PRIOR,
            "repair_paths": list(self.REPAIR_PATHS),
            "source": "isolated repair commit",
            "trust_boundary": False,
        }
        value.update(overrides)
        return value

    def record(self, **overrides: object) -> dict[str, object]:
        values = {
            "lineage": "RL-EXTRA",
            "attempt_id": "ATT-SCOPED",
            "worker_id": "RW-SCOPED",
            "mission_id": None,
            "result": "pass",
            "evidence": ["reviewed the scoped repair diff"],
            "finding": None,
            "note": None,
            "blocker_class": "review",
            "security_result": None,
            "tree_sha": None,
            "repo_root": None,
            "scoped": True,
        }
        values.update(overrides)
        return harness_transition._record_review_attempt(
            self.plan, self.run, Namespace(**values)
        )

    def set_security_review(self) -> None:
        review = self.review_node["review"]
        review["type"] = "security"
        review["lenses"] = ["security"]
        review["scope"] = ["src/**"]
        digest = plan_digest(self.plan)
        self.run["plan"]["digest_sha256"] = digest
        self.worker["base_sha"] = self.PRIOR
        self.worker["plan_digest_sha256"] = digest

    def test_scoped_pass_refunds_the_attempt_and_records_paths(self) -> None:
        receipt = self.record()

        self.assertTrue(receipt["refunded"], receipt)
        self.assertTrue(receipt["scoped"])
        self.assertEqual(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-SCOPED",
                "last_outcome": "pass",
                "bound_worker_id": "RW-SCOPED",
                "blockers": [],
            },
            self.state,
        )
        self.assertTrue(self.worker["scoped"])
        self.assertEqual(self.REPAIR_PATHS, self.worker["repair_paths"])
        attempt = next(
            item
            for item in self.run["attempt_log"]
            if item.get("attempt_id") == "ATT-SCOPED"
        )
        self.assertTrue(attempt["scoped"])
        self.assertEqual(self.REPAIR_PATHS, attempt["repair_paths"])
        self.assertEqual(
            "traversed",
            self.run["graph_state"]["edge_states"]["E-EXTRA-PASS"]["status"],
        )
        self.assertEqual([], validate_run(self.plan, self.run), validate_run(self.plan, self.run))

    def test_scoped_fix_required_still_consumes_the_attempt(self) -> None:
        receipt = self.record(
            result="fix_required", finding=["src/a/one.py:1 regression remains"]
        )

        self.assertFalse(receipt["refunded"], receipt)
        self.assertEqual("failed", self.state["phase"])
        self.assertEqual(2, self.state["attempts"])
        self.assertEqual("fix_required", self.state["last_outcome"])
        self.assertTrue(self.worker["scoped"])
        self.assertEqual(self.REPAIR_PATHS, self.worker["repair_paths"])
        self.assertEqual([], validate_run(self.plan, self.run))

    def test_scoped_requires_a_recorded_repair_scope(self) -> None:
        self.run["integration"]["repair_scopes"] = []

        with self.assertRaisesRegex(ManifestError, "--scoped requires"):
            self.record()

    def test_unscoped_worker_cannot_claim_repair_paths(self) -> None:
        self.record()
        self.worker["scoped"] = None

        errors = validate_run(self.plan, self.run)

        self.assertTrue(
            any("repair_paths" in item for item in errors), errors
        )

    def security_checkout_mocks(self, root: Path) -> dict[str, object]:
        self.run["observed"]["git"].update(
            {
                "parent_worktree_path": str(root),
                "parent_branch": "refs/heads/codex/test",
                "parent_head_sha": self.HEAD,
                "parent_dirty": False,
            }
        )
        return {
            "_git_branch_name": lambda _root: "refs/heads/codex/test",
            "_git_out": lambda _root, *args: (
                self.HEAD + "\n" if args == ("rev-parse", "HEAD") else ""
            ),
            "_git_tree": lambda *_args: "f" * 40,
            "_git_status_excluding_run": lambda *_args: "",
            "_git_is_ancestor": lambda *_args: True,
            "_reject_unplanned_candidate_paths": lambda *_args, **_kw: None,
        }

    def test_scoped_security_pass_needs_no_result_outside_trust_boundaries(
        self,
    ) -> None:
        self.set_security_review()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.multiple(
                harness_transition, **self.security_checkout_mocks(root)
            ):
                receipt = self.record(repo_root=root)

        self.assertTrue(receipt["refunded"], receipt)
        self.assertNotIn("security_result", self.worker)
        self.assertEqual(
            "not_applicable (scoped repair outside trust boundaries)",
            self.worker["security_scope"],
        )
        self.assertEqual([], validate_run(self.plan, self.run), validate_run(self.plan, self.run))

    def test_scoped_security_pass_with_trust_boundary_requires_result(self) -> None:
        self.set_security_review()
        self.run["integration"]["repair_scopes"] = [self.entry(trust_boundary=True)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.multiple(
                harness_transition, **self.security_checkout_mocks(root)
            ):
                with self.assertRaisesRegex(
                    ManifestError, "--security-result"
                ):
                    self.record(repo_root=root)

                result = valid_result(self.HEAD, self.PRIOR)
                result["scope"] = self.review_node["review"]["scope"]
                result_path = Path(directory) / "security-result.json"
                result_path.write_text(json.dumps(result), encoding="utf-8")
                receipt = self.record(
                    repo_root=root, security_result=result_path
                )

        self.assertFalse(receipt["refunded"], receipt)
        self.assertNotIn("security_scope", self.worker)
        self.assertEqual("pass", self.worker["security_result"]["decision"])


class ScopedCoverageChainTests(unittest.TestCase):
    """Closeout completeness for a review node whose latest PASS is scoped."""

    H0 = "a" * 40
    H1 = "b" * 40
    H2 = "c" * 40

    def build_run(self, *, security: bool = False) -> None:
        self.plan = mf.valid_plan()
        node = copy.deepcopy(self.plan["graph"]["nodes"][1])
        node["id"] = "N-EXTRA-REVIEW"
        node["allowed_outcomes"] = [
            "pass",
            "fix_required",
            "retryable_failure",
            "contract_gap",
            "blocked",
        ]
        review = {
            "stage": "integration",
            "lineage_id": "RL-EXTRA",
            "mission_ids": ["M1", "M2"],
        }
        if security:
            review.update(type="security", lenses=["security"], scope=["src/**"])
        node["review"].update(**review)
        self.plan["graph"]["nodes"].append(node)
        self.plan["graph"]["edges"].extend(
            [
                {
                    "id": "E-EXTRA-READY",
                    "kind": "dependency",
                    "from": "N-M2",
                    "to": node["id"],
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
                {
                    "id": "E-EXTRA-PASS",
                    "kind": "route",
                    "from": node["id"],
                    "to": "N-FINAL",
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
            ]
        )
        if security:
            self.plan["required_reviews"] = ["backend_code", "security"]
            self.plan["security_review"] = {
                "status": "required",
                "skill_slot": "code_security_verification",
                "reason": None,
            }
        self.run = mf.valid_run(self.plan)
        mf.mark_complete(self.plan, self.run)
        self.run["integration"].update(
            {
                "integration_head_sha": self.H2,
                "prior_head_shas": [self.H0, self.H1],
                "repair_scopes": [
                    {
                        "candidate_sha": self.H1,
                        "prior_head_sha": self.H0,
                        "repair_paths": ["src/a/one.py"],
                        "source": "isolated repair commit",
                        "trust_boundary": False,
                    },
                    {
                        "candidate_sha": self.H2,
                        "prior_head_sha": self.H1,
                        "repair_paths": ["src/a/two.py"],
                        "source": "isolated repair commit",
                        "trust_boundary": False,
                    },
                ],
            }
        )
        for edge in self.plan["graph"]["edges"]:
            self.run["graph_state"]["edge_states"].setdefault(
                edge["id"],
                {"status": "dormant", "traversals": 0, "source_attempt_id": None},
            )
        self.run["graph_state"]["edge_states"]["E-EXTRA-PASS"]["status"] = "traversed"
        state = self.run["graph_state"]["node_states"][node["id"]]
        state.update(
            {
                "phase": "succeeded",
                "attempts": 3,
                "last_attempt_id": "ATT-CHAIN-2",
                "last_outcome": "pass",
                "bound_worker_id": "RW-CHAIN-2",
                "blockers": [],
            }
        )
        for index, (head_sha, scoped, paths) in enumerate(
            [
                (self.H0, False, None),
                (self.H1, True, ["src/a/one.py"]),
                (self.H2, True, ["src/a/two.py"]),
            ]
        ):
            attempt_id = f"ATT-CHAIN-{index}"
            worker_id = f"RW-CHAIN-{index}"
            worker = {
                "worker_id": worker_id,
                "node_id": node["id"],
                "attempt_id": attempt_id,
                "plan_revision": self.plan["revision"],
                "plan_digest_sha256": self.run["plan"]["digest_sha256"],
                "graph_revision": self.run["graph_state"]["graph_revision"],
                "reviewed_sha": head_sha,
                "review_path": "C:/repo",
                "worker_runtime": "parent",
                "completion_channel": "agent_result",
                "runtime_binding": {},
                "task_thread_id": None,
                "report_path": None,
                "phase": "worker_passed",
                "outcome": "pass",
                "findings": [],
            }
            if scoped:
                worker["scoped"] = True
                worker["repair_paths"] = list(paths)
            self.run["review_workers"].append(worker)
            attempt_entry = {
                "attempt_id": attempt_id,
                "mission_id": None,
                "task_id": None,
                "lease_id": None,
                "kind": "review",
                "result": "pass",
                "evidence": [f"reviewed chain head {index}"],
                "review_lineage_id": "RL-EXTRA",
                "notes": [],
            }
            if scoped:
                attempt_entry["scoped"] = True
                attempt_entry["repair_paths"] = list(paths)
            self.run["attempt_log"].append(attempt_entry)

    def build_repo(self, root: Path, *, hidden_in_last_commit: bool) -> None:
        mf.init_repo(root, "README.md", default_branch="codex/test")
        one = root / "src" / "a" / "one.py"
        one.parent.mkdir(parents=True, exist_ok=True)
        one.write_text("VALUE = 0\n", encoding="utf-8")
        mf.git(root, "add", "src/a/one.py")
        mf.git(root, "commit", "-qm", "full-scope head")
        self.H0 = mf.git(root, "rev-parse", "HEAD")
        one.write_text("VALUE = 1\n", encoding="utf-8")
        mf.git(root, "commit", "-qam", "first repair")
        self.H1 = mf.git(root, "rev-parse", "HEAD")
        two = root / "src" / "a" / "two.py"
        two.write_text("TWO = 2\n", encoding="utf-8")
        mf.git(root, "add", "src/a/two.py")
        if hidden_in_last_commit:
            hidden = root / "src" / "a" / "hidden.py"
            hidden.write_text("HIDDEN = 3\n", encoding="utf-8")
            mf.git(root, "add", "src/a/hidden.py")
        mf.git(root, "commit", "-qm", "second repair")
        self.H2 = mf.git(root, "rev-parse", "HEAD")

    def chain_errors(self, **kwargs: object) -> list[str]:
        return [
            item
            for item in validate_run(self.plan, self.run, **kwargs)
            if "review coverage chain broken" in item
            and "required security integration review" not in item
        ]

    def test_full_chain_covers_the_real_diff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_repo(root, hidden_in_last_commit=False)
            self.build_run()

            self.assertEqual([], self.chain_errors(repo_root=root))

    def test_uncovered_changed_path_breaks_the_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_repo(root, hidden_in_last_commit=True)
            self.build_run()

            errors = self.chain_errors(repo_root=root)

            self.assertEqual(1, len(errors), errors)
            self.assertIn("uncovered path src/a/hidden.py", errors[0])

    def _fail_anchor(self) -> None:
        anchor = next(
            worker
            for worker in self.run["review_workers"]
            if worker.get("worker_id") == "RW-CHAIN-0"
        )
        anchor.update(
            {
                "phase": "worker_failed",
                "outcome": "fix_required",
                "findings": ["src/a/one.py:1 regression remains"],
            }
        )
        attempt = next(
            item
            for item in self.run["attempt_log"]
            if item.get("attempt_id") == "ATT-CHAIN-0"
        )
        attempt["result"] = "fix_required"

    def test_fix_required_anchor_chains_and_still_demands_full_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_repo(root, hidden_in_last_commit=True)
            self.build_run()
            self._fail_anchor()

            errors = self.chain_errors(repo_root=root)

            self.assertEqual(1, len(errors), errors)
            self.assertIn("uncovered path src/a/hidden.py", errors[0])

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_repo(root, hidden_in_last_commit=False)
            self.build_run()
            self._fail_anchor()

            self.assertEqual([], self.chain_errors(repo_root=root))

    def secure_security_workers(self) -> None:
        batch_base = self.run["integration"]["batch_base_sha"]
        bases = {
            "RW-CHAIN-0": batch_base,
            "RW-CHAIN-1": self.H0,
            "RW-CHAIN-2": self.H1,
        }
        for worker in self.run["review_workers"]:
            if worker.get("worker_id") not in bases:
                continue
            worker["base_sha"] = bases[worker["worker_id"]]
            if worker.get("scoped") is True:
                worker["security_scope"] = (
                    harness_transition.SCOPED_REPAIR_SECURITY_SCOPE
                )
        anchor = next(
            worker
            for worker in self.run["review_workers"]
            if worker.get("worker_id") == "RW-CHAIN-0"
        )
        node = next(
            item
            for item in self.plan["graph"]["nodes"]
            if item.get("id") == "N-EXTRA-REVIEW"
        )
        result = valid_result(self.H0, batch_base)
        result["scope"] = list(node["review"]["scope"])
        anchor["security_result"] = result

    def security_closeout_errors(self) -> list[str]:
        return [
            item
            for item in validate_run(self.plan, self.run)
            if "required security integration review" in item
        ]

    def test_security_node_closes_through_non_boundary_scoped_chain(self) -> None:
        self.build_run(security=True)
        self.secure_security_workers()

        self.assertEqual([], self.security_closeout_errors())

    def test_security_node_still_needs_results_behind_trust_boundaries(self) -> None:
        self.build_run(security=True)
        self.secure_security_workers()
        self.run["integration"]["repair_scopes"][1]["trust_boundary"] = True

        errors = self.security_closeout_errors()

        self.assertEqual(1, len(errors), errors)
        self.assertIn(
            "coverage chain broken: trust-boundary scoped PASS", errors[0]
        )

    def test_trust_boundary_scoped_pass_without_security_result_fails(self) -> None:
        self.build_run(security=True)
        self.run["integration"]["repair_scopes"][1]["trust_boundary"] = True

        errors = self.chain_errors()

        self.assertEqual(1, len(errors), errors)
        self.assertIn(
            f"trust-boundary scoped PASS at {self.H2} has no security_result",
            errors[0],
        )


class ScopedPacketRenderTests(unittest.TestCase):
    """render_packet scopes the packet to the recorded repair scope."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name).resolve()
        mf.init_repo(self.root, "file.txt", default_branch="codex/test")
        self.base = mf.git(self.root, "rev-parse", "HEAD")
        (self.root / "file.txt").write_text("feature\n", encoding="utf-8")
        mf.git(self.root, "commit", "-qam", "candidate feature")
        self.prior = mf.git(self.root, "rev-parse", "HEAD")
        (self.root / "file.txt").write_text("feature2\n", encoding="utf-8")
        (self.root / "repair.txt").write_text("fix\n", encoding="utf-8")
        mf.git(self.root, "add", "repair.txt")
        mf.git(self.root, "commit", "-qam", "isolated repair")
        self.head = mf.git(self.root, "rev-parse", "HEAD")

        self.plan = mf.valid_plan()
        self.run = mf.valid_run(self.plan)
        self.run["integration"]["batch_base_sha"] = self.base
        self.run["integration"]["integration_head_sha"] = self.head
        self.run["mission_states"]["M1"]["head_sha"] = self.head
        self.run["integration"]["repair_scopes"] = [
            {
                "candidate_sha": self.head,
                "prior_head_sha": self.prior,
                "repair_paths": ["repair.txt"],
                "source": "isolated repair commit",
                "trust_boundary": False,
            }
        ]
        self.run["review_workers"] = [
            {
                "worker_id": "RW-PRIOR",
                "node_id": "N-REVIEW-M1",
                "attempt_id": "ATT-PRIOR",
                "plan_revision": self.plan["revision"],
                "plan_digest_sha256": "0" * 64,
                "graph_revision": self.run["graph_state"]["graph_revision"],
                "reviewed_sha": self.prior,
                "review_path": str(self.root),
                "worker_runtime": "parent",
                "completion_channel": "agent_result",
                "runtime_binding": {},
                "task_thread_id": None,
                "report_path": None,
                "phase": "worker_failed",
                "outcome": "fix_required",
                "findings": ["repair.txt:1 header misses the accepted copy"],
            }
        ]

    def test_scoped_section_renders_only_scoped_paths_and_contract(self) -> None:
        packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)

        self.assertIn("## Scoped repair review", packet)
        self.assertNotIn("## Repair re-check", packet)
        self.assertNotIn("## Diff", packet)
        self.assertIn(f"Repair range: `{self.prior}..{self.head}`", packet)
        self.assertIn("A\trepair.txt", packet)
        self.assertNotIn("M\tfile.txt", packet)
        self.assertIn(
            "- F1: repair.txt:1 header misses the accepted copy", packet
        )
        self.assertIn("Trust boundary: no.", packet)
        self.assertIn(
            "Inspect only the repair paths and their direct consumers.", packet
        )
        contract = packet_contract(packet)
        self.assertEqual(
            {
                "prior_head_sha": self.prior,
                "candidate_sha": self.head,
                "repair_paths": ["repair.txt"],
                "trust_boundary": False,
            },
            contract["scoped_repair"],
        )
        self.assertIsNone(contract["recheck"])

    def test_no_scoped_section_without_a_recorded_entry(self) -> None:
        self.run["integration"]["repair_scopes"] = []

        packet = render_packet(self.plan, self.run, "N-REVIEW-M1", self.root)

        self.assertNotIn("## Scoped repair review", packet)
        self.assertIsNone(packet_contract(packet)["scoped_repair"])


if __name__ == "__main__":
    unittest.main()


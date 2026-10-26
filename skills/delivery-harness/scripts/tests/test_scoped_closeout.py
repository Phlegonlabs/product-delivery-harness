"""Scoped closeout chains: anchor recency, diff verification, and security.

These tests pin the scoped closeout contract against the holes found in
the 0.70.0 review: a fix_required anchor at the integration head closing
through an empty chain, a silent declared-path fallback when git diff
fails, and a security anchor whose fix_required decision never reaches
the scoped repair chain.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for path in (TESTS_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import harness_transition as harness_transition  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
from harness_manifest import validate_run  # noqa: E402
from test_security_review_result import valid_result  # noqa: E402


class ScopedCloseoutChainTests(unittest.TestCase):
    """Closeout completeness for a review node whose latest PASS is scoped."""

    H0 = "a" * 40
    H1 = "b" * 40
    H2 = "c" * 40

    def chain_workers(self) -> list[tuple[str, bool, list[str] | None, str]]:
        """One full PASS anchoring two scoped repair PASSes at H1 and H2."""

        return [
            (self.H0, False, None, "pass"),
            (self.H1, True, ["src/a/one.py"], "pass"),
            (self.H2, True, ["src/a/two.py"], "pass"),
        ]

    def chain_scopes(self) -> list[dict[str, object]]:
        return [
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
        ]

    def build_run(
        self,
        *,
        workers: list[tuple[str, bool, list[str] | None, str]] | None = None,
        scopes: list[dict[str, object]] | None = None,
        security: bool = False,
        lenses: list[str] | None = None,
    ) -> None:
        workers = self.chain_workers() if workers is None else workers
        scopes = self.chain_scopes() if scopes is None else scopes
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
        node["max_attempts"] = 3
        review = {
            "stage": "integration",
            "lineage_id": "RL-EXTRA",
            "mission_ids": ["M1", "M2"],
        }
        if security:
            review.update(
                type="security",
                lenses=lenses or ["security"],
                scope=["src/**"],
            )
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
        stale_head = self.run["integration"]["integration_head_sha"]
        self.run["integration"].update(
            {
                "integration_head_sha": self.H2,
                "prior_head_shas": [self.H0, self.H1],
                "repair_scopes": scopes,
            }
        )
        # mark_complete seeds a retained full-scope worker for every
        # review node; this fixture serialises its own chain instead.
        self.run["review_workers"] = [
            worker
            for worker in self.run["review_workers"]
            if worker.get("node_id") != node["id"]
        ]
        for execution in self.run["verifier_executions"]:
            if execution.get("layer") not in {"batch", "final"}:
                continue
            execution["context"]["head_sha"] = self.H2
            execution["key_document"]["head_sha"] = self.H2
            git_guard = execution["git_guard_attestation"]["git_guard"]
            git_guard["expected_head_sha"] = self.H2
            execution["git_guard_attestation"]["source_head_sha"] = self.H2
            execution_key = hashlib.sha256(
                json.dumps(
                    execution["key_document"],
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()
            execution["execution_key"] = execution_key
            execution["evidence_key"] = execution_key
        for layer, run_key in (
            ("batch", "batch_gate_results"),
            ("final", "final_gate_results"),
        ):
            gate_executions = [
                execution
                for execution in self.run["verifier_executions"]
                if execution.get("layer") == layer
            ]
            for gate_result, execution in zip(
                self.run[run_key], gate_executions
            ):
                gate_result["head_sha"] = self.H2
                gate_result["evidence"] = [execution["evidence_key"]]
        continuity = self.run["landing"]["continuity"]
        if isinstance(continuity, dict) and continuity.get("head_sha") == stale_head:
            continuity["head_sha"] = self.H2
        for edge in self.plan["graph"]["edges"]:
            self.run["graph_state"]["edge_states"].setdefault(
                edge["id"],
                {"status": "dormant", "traversals": 0, "source_attempt_id": None},
            )
        self.run["graph_state"]["edge_states"]["E-EXTRA-PASS"]["status"] = "traversed"
        state = self.run["graph_state"]["node_states"][node["id"]]
        last_index = len(workers) - 1
        state.update(
            {
                "phase": "succeeded",
                "attempts": len(workers),
                "last_attempt_id": f"ATT-CHAIN-{last_index}",
                "last_outcome": "pass",
                "bound_worker_id": f"RW-CHAIN-{last_index}",
                "blockers": [],
            }
        )
        self.run["graph_state"]["edge_states"]["E-EXTRA-PASS"][
            "source_attempt_id"
        ] = f"ATT-CHAIN-{last_index}"
        for index, (head_sha, scoped, paths, outcome) in enumerate(workers):
            attempt_id = f"ATT-CHAIN-{index}"
            worker_id = f"RW-CHAIN-{index}"
            passed = outcome == "pass"
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
                "phase": "worker_passed" if passed else "worker_failed",
                "outcome": outcome,
                "findings": [] if passed else [f"{head_sha} remaining finding"],
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
                "result": outcome,
                "evidence": [f"reviewed chain head {index}"],
                "review_lineage_id": "RL-EXTRA",
                "notes": [],
            }
            if scoped:
                attempt_entry["scoped"] = True
                attempt_entry["repair_paths"] = list(paths)
            self.run["attempt_log"].append(attempt_entry)
        self.review_node_id = node["id"]

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

    def security_closeout_errors(self) -> list[str]:
        return [
            item
            for item in validate_run(self.plan, self.run)
            if "required security integration review" in item
        ]

    def security_node(self) -> dict[str, object]:
        return next(
            item
            for item in self.plan["graph"]["nodes"]
            if item.get("id") == "N-EXTRA-REVIEW"
        )

    def test_fix_required_anchor_at_the_head_needs_a_repair_step(self) -> None:
        self.build_run(
            workers=[
                (self.H2, False, None, "fix_required"),
                (self.H2, True, ["src/a/one.py"], "pass"),
            ],
            scopes=[
                {
                    "candidate_sha": self.H2,
                    "prior_head_sha": self.H1,
                    "repair_paths": ["src/a/one.py"],
                    "source": "isolated repair commit",
                    "trust_boundary": False,
                }
            ],
        )

        errors = self.chain_errors()

        self.assertEqual(1, len(errors), errors)
        self.assertIn("no chained repair step", errors[0])

    def test_latest_full_review_anchors_the_chain(self) -> None:
        self.build_run(
            workers=[
                (self.H0, False, None, "pass"),
                (self.H1, False, None, "fix_required"),
                (self.H2, True, ["src/a/two.py"], "pass"),
            ],
            scopes=[
                {
                    "candidate_sha": self.H1,
                    "prior_head_sha": self.H0,
                    "repair_paths": ["src/a/one.py"],
                    "source": "isolated repair commit",
                    "trust_boundary": False,
                },
                {
                    "candidate_sha": self.H2,
                    "prior_head_sha": self.H0,
                    "repair_paths": ["src/a/two.py"],
                    "source": "isolated repair commit",
                    "trust_boundary": False,
                },
            ],
        )

        errors = self.chain_errors()

        self.assertEqual(1, len(errors), errors)
        self.assertIn(
            "no reviewed scoped chain reaches the integration head from a non-scoped review",
            errors[0],
        )

    def test_anchor_serialised_behind_a_newer_attempt_breaks_the_chain(
        self,
    ) -> None:
        self.build_run(
            workers=[
                (self.H0, False, None, "pass"),
                (self.H2, False, None, "fix_required"),
                (self.H2, True, ["src/a/one.py", "src/a/two.py"], "pass"),
            ],
            scopes=[
                {
                    "candidate_sha": self.H2,
                    "prior_head_sha": self.H0,
                    "repair_paths": ["src/a/one.py", "src/a/two.py"],
                    "source": "isolated repair commit",
                    "trust_boundary": False,
                }
            ],
        )
        # Serialised [A1, A0, A2] beside the attempt log's [A0, A1, A2]:
        # the stale PASS at H0 must not anchor over the newer fix_required
        # re-check at the integration head just because it is listed last.
        node_workers = [
            worker
            for worker in self.run["review_workers"]
            if worker.get("node_id") == self.review_node_id
        ]
        anchor_order = [1, 0, 2]
        self.run["review_workers"] = [
            node_workers[index] for index in anchor_order
        ]

        errors = self.chain_errors()

        self.assertEqual(1, len(errors), errors)
        self.assertIn(
            "anchor order inconsistent with the attempt log",
            errors[0],
        )

    def test_anchor_missing_from_the_attempt_log_breaks_the_chain(self) -> None:
        self.build_run(
            workers=[
                (self.H0, False, None, "fix_required"),
                (self.H1, True, ["src/a/one.py"], "pass"),
                (self.H2, True, ["src/a/two.py"], "pass"),
            ],
        )
        self.run["attempt_log"] = [
            attempt
            for attempt in self.run["attempt_log"]
            if attempt.get("attempt_id") != "ATT-CHAIN-0"
        ]

        errors = self.chain_errors()

        self.assertEqual(1, len(errors), errors)
        self.assertIn(
            "anchor order inconsistent with the attempt log",
            errors[0],
        )

    def test_newer_logged_full_review_without_a_worker_breaks_the_chain(
        self,
    ) -> None:
        self.build_run(
            workers=[
                (self.H0, False, None, "pass"),
                (self.H2, False, None, "fix_required"),
                (self.H2, True, ["src/a/one.py", "src/a/two.py"], "pass"),
            ],
            scopes=[
                {
                    "candidate_sha": self.H2,
                    "prior_head_sha": self.H0,
                    "repair_paths": ["src/a/one.py", "src/a/two.py"],
                    "source": "isolated repair commit",
                    "trust_boundary": False,
                }
            ],
        )
        # Drop the newer full fix_required worker record but keep its
        # attempt log entry: the stale PASS at H0 must still not anchor.
        self.run["review_workers"] = [
            worker
            for worker in self.run["review_workers"]
            if worker.get("attempt_id") != "ATT-CHAIN-1"
        ]

        errors = self.chain_errors()

        self.assertEqual(1, len(errors), errors)
        self.assertIn(
            "anchor order inconsistent with the attempt log",
            errors[0],
        )

    def test_orphaned_review_without_a_lineage_still_breaks_the_chain(
        self,
    ) -> None:
        self.build_run(
            workers=[
                (self.H0, False, None, "pass"),
                (self.H2, False, None, "fix_required"),
                (self.H2, True, ["src/a/one.py", "src/a/two.py"], "pass"),
            ],
            scopes=[
                {
                    "candidate_sha": self.H2,
                    "prior_head_sha": self.H0,
                    "repair_paths": ["src/a/one.py", "src/a/two.py"],
                    "source": "isolated repair commit",
                    "trust_boundary": False,
                }
            ],
        )
        self.run["review_workers"] = [
            worker
            for worker in self.run["review_workers"]
            if worker.get("attempt_id") != "ATT-CHAIN-1"
        ]
        for attempt in self.run["attempt_log"]:
            if attempt.get("attempt_id") == "ATT-CHAIN-1":
                attempt["review_lineage_id"] = None

        errors = self.chain_errors()

        self.assertEqual(1, len(errors), errors)
        self.assertIn(
            "anchor order inconsistent with the attempt log",
            errors[0],
        )

    def test_lineage_less_review_retained_by_another_node_is_not_an_orphan(
        self,
    ) -> None:
        self.build_run()
        # Another node's full PASS at the head, logged after this node's
        # anchor without a lineage id, is attributable through its retained
        # worker and must not break this node's chain.
        other = copy.deepcopy(
            next(
                worker
                for worker in self.run["review_workers"]
                if worker.get("attempt_id") == "ATT-CHAIN-0"
            )
        )
        other.update(
            {
                "worker_id": "RW-OTHER-NODE",
                "node_id": "N-OTHER-REVIEW",
                "attempt_id": "ATT-OTHER-0",
                "reviewed_sha": self.H2,
            }
        )
        self.run["review_workers"].append(other)
        self.run["attempt_log"].append(
            {
                "attempt_id": "ATT-OTHER-0",
                "mission_id": None,
                "task_id": None,
                "lease_id": None,
                "kind": "review",
                "result": "pass",
                "evidence": ["other node full review"],
                "review_lineage_id": None,
                "notes": [],
            }
        )

        self.assertEqual([], self.chain_errors())

    def test_git_diff_failure_fails_the_chain_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_repo(root, hidden_in_last_commit=True)
            self.build_run()

            failed = subprocess.CompletedProcess(
                args=["git"],
                returncode=128,
                stdout="",
                stderr=f"fatal: bad object {self.H0}",
            )
            with mock.patch("harness_manifest.run_git", return_value=failed):
                errors = self.chain_errors(repo_root=root)

            self.assertEqual(1, len(errors), errors)
            self.assertIn(
                f"git diff unavailable (exit 128: fatal: bad object {self.H0})",
                errors[0],
            )

            def raise_timeout(*args: object, **kwargs: object) -> object:
                raise subprocess.TimeoutExpired(cmd="git", timeout=30)

            with mock.patch("harness_manifest.run_git", side_effect=raise_timeout):
                timeout_errors = self.chain_errors(repo_root=root)

            self.assertEqual(1, len(timeout_errors), timeout_errors)
            self.assertIn("git diff unavailable (", timeout_errors[0])

        # Without a repo root the stored repair paths stand in for the diff,
        # so the same run still closes; nothing claims the diff was verified.
        self.assertEqual([], self.chain_errors())

    def secure_security_workers(self, *, anchor_decision: str) -> None:
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
        result = valid_result(self.H0, batch_base)
        result["decision"] = anchor_decision
        result["scope"] = list(self.security_node()["review"]["scope"])
        if anchor_decision != "pass":
            result["findings"] = [
                {
                    "severity": "high",
                    "confidence": "high",
                    "cwe": "CWE-798",
                    "location": "src/a/one.py:1",
                    "summary": "hard-coded deployment credential",
                    "source_to_sink": "constant feeds the client handshake",
                    "preconditions": "repository checkout",
                    "impact": "credential disclosure",
                    "counterevidence": "none recorded",
                    "remediation": "load the credential from a secret store",
                    "remediation_test": "tests/test_no_embedded_secret.py",
                }
            ]
        anchor["security_result"] = result
        anchor["outcome"] = anchor_decision
        anchor["phase"] = (
            "worker_passed" if anchor_decision == "pass" else "worker_failed"
        )
        if anchor_decision != "pass":
            anchor["findings"] = [f"{self.H0} remaining finding"]
        attempt = next(
            item
            for item in self.run["attempt_log"]
            if item.get("attempt_id") == "ATT-CHAIN-0"
        )
        attempt["result"] = anchor_decision

    def test_fix_required_security_anchor_needs_a_trust_boundary_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_repo(root, hidden_in_last_commit=False)
            self.build_run(security=True)
            self.secure_security_workers(anchor_decision="fix_required")

            errors = validate_run(self.plan, self.run, repo_root=root)

            self.assertEqual(2, len(errors), errors)
            for error in errors:
                self.assertIn(
                    "anchor security result is fix_required and no "
                    "trust-boundary scoped security pass covers it",
                    error,
                )

    def test_combined_anchor_failing_another_lens_keeps_its_security_pass(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_repo(root, hidden_in_last_commit=False)
            self.build_run(
                security=True,
                lenses=["security", "backend_code"],
            )
            self.secure_security_workers(anchor_decision="pass")
            anchor = next(
                worker
                for worker in self.run["review_workers"]
                if worker.get("worker_id") == "RW-CHAIN-0"
            )
            anchor["outcome"] = "fix_required"
            anchor["phase"] = "worker_failed"
            anchor["findings"] = [f"{self.H0} backend finding"]
            attempt = next(
                item
                for item in self.run["attempt_log"]
                if item.get("attempt_id") == "ATT-CHAIN-0"
            )
            attempt["result"] = "fix_required"

            self.assertEqual([], validate_run(self.plan, self.run, repo_root=root))

    def test_passing_security_anchor_closes_through_non_boundary_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_repo(root, hidden_in_last_commit=False)
            self.build_run(security=True)
            self.secure_security_workers(anchor_decision="pass")

            self.assertEqual([], self.chain_errors(repo_root=root))
            self.assertEqual([], self.security_closeout_errors())

    def test_non_scoped_security_pass_closeout_is_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_repo(root, hidden_in_last_commit=False)
            self.build_run(
                workers=[(self.H2, False, None, "pass")],
                scopes=self.chain_scopes(),
                security=True,
            )
            batch_base = self.run["integration"]["batch_base_sha"]
            state = self.run["graph_state"]["node_states"][self.review_node_id]
            worker = next(
                item
                for item in self.run["review_workers"]
                if item.get("node_id") == self.review_node_id
                and item.get("worker_id") == state.get("bound_worker_id")
                and item.get("attempt_id") == state.get("last_attempt_id")
            )
            worker["base_sha"] = batch_base
            result = valid_result(self.H2, batch_base)
            result["scope"] = list(self.security_node()["review"]["scope"])
            worker["security_result"] = result

            self.assertEqual([], self.security_closeout_errors())
            self.assertEqual([], self.chain_errors(repo_root=root))


if __name__ == "__main__":
    unittest.main()

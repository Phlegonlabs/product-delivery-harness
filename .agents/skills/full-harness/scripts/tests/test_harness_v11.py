#!/usr/bin/env python3
"""Regression tests for the PLAN-v6/RUN-v11 orchestration controls."""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_transition  # noqa: E402
import new_run  # noqa: E402
from harness_core import load_run, plan_digest  # noqa: E402
from harness_manifest import validate_run  # noqa: E402
from harness_ui_evidence import validate_integration_head_against_git  # noqa: E402
from manifest_fixtures import manifest_markdown  # noqa: E402
from render_review_packet import render_packet  # noqa: E402
from select_ready_nodes import select_ready_nodes  # noqa: E402
from test_harness_manifest import valid_plan, valid_run  # noqa: E402
from test_select_ready_nodes import current_preintegration_review_state  # noqa: E402
from verifier_runtime import execution_key_from_document  # noqa: E402


PLAN_TEMPLATE = SCRIPTS_DIR.parent / "assets" / "templates" / "HARNESS_PLAN.template.md"


class HarnessV11Tests(unittest.TestCase):
    def test_pause_is_a_durable_dispatch_gate(self) -> None:
        plan, run = current_preintegration_review_state()
        run["control"] = {
            "desired_state": "paused",
            "requested_at": "2026-08-23T00:00:00Z",
            "source": "user stopped the run",
            "acknowledged_at": "2026-08-23T00:00:00Z",
        }

        selected = select_ready_nodes(plan, run)

        self.assertEqual([], selected["dispatchable_nodes"])
        self.assertTrue(selected["deferred_nodes"])
        self.assertTrue(
            all("run_paused" in item["reason_codes"] for item in selected["deferred_nodes"])
        )

    def test_resume_rejects_an_active_review_worker(self) -> None:
        _plan, run = current_preintegration_review_state()
        run["review_workers"] = [{"phase": "worker_running"}]

        with self.assertRaises(harness_transition.ManifestError):
            harness_transition._control(run, "running", "user requested resume")

    def test_interrupted_integration_reviews_are_reconciled_atomically(self) -> None:
        plan, run = current_preintegration_review_state()
        digest = plan_digest(plan)
        node_id = "N-VISUAL-REVIEW"
        lineage_id = "REVIEW-N-VISUAL-REVIEW"
        worker_id = "RW-INTERRUPTED"
        attempt_id = "ATT-INTERRUPTED"
        for index in (1, 2):
            run["attempt_log"].append(
                {
                    "attempt_id": f"ATT-HISTORICAL-{index}",
                    "mission_id": None,
                    "task_id": None,
                    "lease_id": None,
                    "kind": "review",
                    "result": "pass",
                    "evidence": ["historical review"],
                    "review_lineage_id": lineage_id,
                    "failure_family_ids": [],
                }
            )
        review_worker = {
            "worker_id": worker_id,
            "node_id": node_id,
            "attempt_id": attempt_id,
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "graph_revision": plan["revision"],
            "reviewed_sha": "a" * 40,
            "review_path": "C:/repo",
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
            "phase": "worker_running",
            "outcome": None,
            "findings": [],
        }
        run["review_workers"] = [review_worker]
        run["graph_state"]["node_states"][node_id].update(
            {
                "phase": "running",
                "attempts": 0,
                "last_attempt_id": attempt_id,
                "last_outcome": None,
                "bound_worker_id": worker_id,
                "blockers": [],
            }
        )
        fake_edge = run["graph_state"]["edge_states"]["E-M1-VISUAL-REVIEW"]
        fake_edge.update(
            {
                "status": "traversed",
                "traversals": 1,
                "source_attempt_id": "ATT-M1-SKIP",
            }
        )

        before = validate_run(plan, run)
        self.assertTrue(any("every covered mission is integrated" in error for error in before))
        self.assertTrue(any("current attempt or a retained" in error for error in before))
        self.assertTrue(any("attempt_log lineage count" in error for error in before))

        harness_transition._reconcile_interrupted_reviews(
            plan,
            run,
            Namespace(
                worker_id=[worker_id],
                reason="user stopped review",
                source="user requested stop",
            ),
        )

        self.assertEqual([], validate_run(plan, run))
        self.assertEqual("paused", run["control"]["desired_state"])
        self.assertEqual("blocked", review_worker["phase"])
        self.assertEqual("dormant", run["graph_state"]["node_states"][node_id]["phase"])
        self.assertEqual("dormant", fake_edge["status"])
        self.assertEqual(3, run["review_lineages"][lineage_id]["consumed_attempts"])

    def test_review_lineage_survives_plan_revision(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        lineage_id = "REVIEW-M1"
        run["attempt_log"].append(
            {
                "attempt_id": "ATT-REVIEW-M1-1",
                "mission_id": "M1",
                "task_id": None,
                "lease_id": None,
                "kind": "review",
                "result": "fix_required",
                "evidence": ["one root-cause family"],
                "review_lineage_id": lineage_id,
                "failure_family_ids": ["FAMILY-MARKDOWN-PARSE"],
            }
        )
        run["review_lineages"][lineage_id]["consumed_attempts"] = 1
        self.assertEqual([], validate_run(plan, run))

        revised = copy.deepcopy(plan)
        revised["revision"] = 2
        run["plan"]["revision"] = 2
        run["plan"]["digest_sha256"] = plan_digest(revised)
        run["active_wave"]["plan_revision"] = 2
        run["graph_state"]["graph_revision"] = 2

        self.assertEqual([], validate_run(revised, run))
        self.assertEqual(1, run["review_lineages"][lineage_id]["consumed_attempts"])

    def test_contract_digest_mismatch_requires_restart(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        gate = run["runtime_capabilities"]["runtime_adapter"]["version_gate"]
        gate["installed_contract_digest"] = "b" * 64

        errors = validate_run(plan, run)
        self.assertTrue(any("digest mismatch requires restart_required" in error for error in errors))

        gate["status"] = "restart_required"
        self.assertEqual([], validate_run(plan, run))

    def test_coordination_only_tail_does_not_stale_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Harness Test"], cwd=root, check=True)
            (root / "src.txt").write_text("candidate\n", encoding="utf-8")
            subprocess.run(["git", "add", "src.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "candidate"], cwd=root, check=True)
            candidate = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            goal = root / "docs" / "goal"
            goal.mkdir(parents=True)
            (goal / "RUN.md").write_text("coordination\n", encoding="utf-8")
            subprocess.run(["git", "add", "docs/goal/RUN.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "record run"], cwd=root, check=True)
            branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()
            run = {
                "schema_version": 11,
                "integration": {
                    "branch": branch,
                    "integration_head_sha": candidate,
                    "coordination_paths": ["docs/goal/RUN.md"],
                },
            }

            self.assertEqual([], validate_integration_head_against_git(run, root))

            (root / "src.txt").write_text("changed after review\n", encoding="utf-8")
            subprocess.run(["git", "add", "src.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "code after review"], cwd=root, check=True)
            self.assertTrue(validate_integration_head_against_git(run, root))

    def test_review_packet_is_bounded(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Harness Test"], cwd=root, check=True)
            (root / "file.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "file.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
            base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            (root / "file.txt").write_text("changed\n" * 100, encoding="utf-8")
            subprocess.run(["git", "add", "file.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "head"], cwd=root, check=True)
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            run["integration"]["batch_base_sha"] = base
            run["integration"]["integration_head_sha"] = head
            run["mission_states"]["M1"]["head_sha"] = head

            packet = render_packet(plan, run, "N-REVIEW-M1", root, max_diff_bytes=64)

            self.assertIn("## Diff (truncated)", packet)
            self.assertIn("REVIEW-M1", packet)
            self.assertIn('"required_tools": []', packet)
            self.assertNotIn('"harness_plan"', packet)

            for node in plan["graph"]["nodes"]:
                if isinstance(node.get("review"), dict):
                    node["review"]["stage"] = "integration"
            integration_packet = render_packet(
                plan, run, "N-REVIEW-M1", root, max_diff_bytes=64
            )

            self.assertNotIn("## Integration focus", packet)
            self.assertIn("## Already-reviewed mission heads", integration_packet)
            self.assertIn("(passed exact-head pre-integration review)", integration_packet)
            self.assertIn("## Integration focus", integration_packet)
            self.assertIn("merge seams", integration_packet)
            self.assertIn("cross-mission interaction", integration_packet)

    def test_transition_command_pauses_generated_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_path = Path(temp) / "RUN.md"
            self.assertEqual(
                0,
                new_run.main(
                    [
                        "--plan",
                        str(PLAN_TEMPLATE),
                        "--run-id",
                        "RUN-transition-test",
                        "--branch",
                        "refs/heads/test-run",
                        "--out",
                        str(run_path),
                    ]
                ),
            )
            self.assertEqual(
                0,
                harness_transition.main(
                    [
                        "--plan",
                        str(PLAN_TEMPLATE),
                        "--run",
                        str(run_path),
                        "pause",
                        "--source",
                        "user requested stop",
                    ]
                ),
            )
            self.assertEqual("paused", load_run(run_path)["control"]["desired_state"])

    def test_review_result_requires_a_reserved_dispatch(self) -> None:
        plan, run = current_preintegration_review_state()

        with self.assertRaisesRegex(
            harness_transition.ManifestError, "no matching reserved dispatch receipt"
        ):
            harness_transition._record_review_attempt(
                plan,
                run,
                Namespace(
                    lineage="REVIEW-N-FRONTEND-REVIEW",
                    worker_id="RW-MISSING",
                    attempt_id="ATT-MISSING",
                    mission_id="M1",
                    result="pass",
                    evidence=["review passed"],
                    finding=None,
                    failure_family_id=None,
                    failure_primitive=None,
                    equivalence_class=None,
                    strategy=None,
                ),
            )

    def test_reserved_review_result_updates_one_atomic_attempt(self) -> None:
        plan, run = current_preintegration_review_state()
        receipt = harness_transition._reserve_review_dispatch(
            plan,
            run,
            Namespace(
                node_id="N-FRONTEND-REVIEW",
                worker_id="RW-REVIEW-1",
                attempt_id="ATT-REVIEW-1",
                report_path=None,
            ),
            repo_root=None,
        )

        self.assertEqual("b" * 40, receipt["dispatch_receipt"]["reviewed_sha"])
        self.assertEqual([], validate_run(plan, run))
        harness_transition._record_review_attempt(
            plan,
            run,
            Namespace(
                lineage="REVIEW-N-FRONTEND-REVIEW",
                worker_id="RW-REVIEW-1",
                attempt_id="ATT-REVIEW-1",
                mission_id="M1",
                result="fix_required",
                evidence=["parser variants failed"],
                finding=["src/example/app.ts:1 parser variants failed"],
                failure_family_id="FAMILY-MARKDOWN",
                failure_primitive="Markdown scanner",
                equivalence_class=["reference links", "fenced code"],
                strategy="replace regex patches with a fence-aware scanner",
            ),
        )

        self.assertEqual([], validate_run(plan, run))
        self.assertEqual("worker_failed", run["review_workers"][-1]["phase"])
        self.assertEqual(
            1,
            run["review_lineages"]["REVIEW-N-FRONTEND-REVIEW"][
                "consumed_attempts"
            ],
        )

    def test_reserved_review_pass_traverses_its_declared_route(self) -> None:
        plan, run = current_preintegration_review_state()
        harness_transition._reserve_review_dispatch(
            plan,
            run,
            Namespace(
                node_id="N-FRONTEND-REVIEW",
                worker_id="RW-REVIEW-PASS",
                attempt_id="ATT-REVIEW-PASS",
                report_path=None,
            ),
            repo_root=None,
        )

        harness_transition._record_review_attempt(
            plan,
            run,
            Namespace(
                lineage="REVIEW-N-FRONTEND-REVIEW",
                worker_id="RW-REVIEW-PASS",
                attempt_id="ATT-REVIEW-PASS",
                mission_id="M1",
                result="pass",
                evidence=["exact-head review passed"],
                finding=None,
                failure_family_id=None,
                failure_primitive=None,
                equivalence_class=None,
                strategy=None,
            ),
        )

        edge = run["graph_state"]["edge_states"]["E-FRONTEND-VISUAL-REVIEW"]
        self.assertEqual("traversed", edge["status"])
        self.assertEqual("ATT-REVIEW-PASS", edge["source_attempt_id"])
        self.assertEqual([], validate_run(plan, run))

    def test_owner_review_grant_is_exact_and_one_shot(self) -> None:
        plan, run = current_preintegration_review_state()
        lineage = run["review_lineages"]["REVIEW-N-FRONTEND-REVIEW"]
        for index in (1, 2):
            run["attempt_log"].append(
                {
                    "attempt_id": f"ATT-HISTORICAL-REVIEW-{index}",
                    "mission_id": "M1",
                    "task_id": None,
                    "lease_id": None,
                    "kind": "review",
                    "result": "fix_required",
                    "evidence": ["historical review defect"],
                    "review_lineage_id": "REVIEW-N-FRONTEND-REVIEW",
                    "failure_family_ids": ["FAMILY-MARKDOWN"],
                }
            )
        lineage["consumed_attempts"] = 2
        lineage["failure_families"] = [
            {
                "id": "FAMILY-MARKDOWN",
                "primitive": "Markdown scanner",
                "equivalence_classes": ["reference links", "fenced code"],
                "strategy": "replace regex patches with a fence-aware scanner",
                "status": "open",
            }
        ]
        args = Namespace(
            lineage="REVIEW-N-FRONTEND-REVIEW",
            decision_id="OWNER-REVIEW-1",
            source="I approve OWNER-REVIEW-1 for one additional review",
            source_ref="user_turn:turn-123",
            failure_family_id="FAMILY-MARKDOWN",
            strategy="structural scanner repair",
            acceptance=["all Markdown reference classes"],
            additional_attempts=1,
        )

        blanket = copy.copy(args)
        blanket.source = "User blanket approval to complete the phase"
        with self.assertRaisesRegex(
            harness_transition.ManifestError, "name the approved decision ID"
        ):
            harness_transition._grant(run, blanket)

        harness_transition._grant(run, args)

        self.assertEqual(1, lineage["additional_allowance"])
        self.assertEqual("user_turn:turn-123", lineage["owner_decisions"][0]["source_ref"])
        self.assertEqual([], validate_run(plan, run))
        with self.assertRaisesRegex(
            harness_transition.ManifestError, "already used its one owner-granted successor"
        ):
            harness_transition._grant(run, args)

    def test_manifest_rejects_a_backfilled_blanket_owner_grant(self) -> None:
        plan, run = current_preintegration_review_state()
        lineage = run["review_lineages"]["REVIEW-N-FRONTEND-REVIEW"]
        for index in (1, 2):
            run["attempt_log"].append(
                {
                    "attempt_id": f"ATT-HISTORICAL-REVIEW-{index}",
                    "mission_id": "M1",
                    "task_id": None,
                    "lease_id": None,
                    "kind": "review",
                    "result": "fix_required",
                    "evidence": ["historical review defect"],
                    "review_lineage_id": "REVIEW-N-FRONTEND-REVIEW",
                    "failure_family_ids": ["FAMILY-MARKDOWN"],
                }
            )
        lineage["consumed_attempts"] = 2
        lineage["additional_allowance"] = 2
        lineage["failure_families"] = [
            {
                "id": "FAMILY-MARKDOWN",
                "primitive": "Markdown scanner",
                "equivalence_classes": ["reference links"],
                "strategy": "structural scanner repair",
                "status": "open",
            }
        ]
        lineage["owner_decisions"] = [
            {
                "id": "OWNER-BLANKET",
                "source": "User blanket approval to complete the phase",
                "strategy": "continue repairing",
                "acceptance_matrix": ["try again"],
                "additional_review_attempts": 2,
            }
        ]

        errors = validate_run(plan, run)

        self.assertTrue(any("source_ref" in error for error in errors))
        self.assertTrue(any("failure_family_id" in error for error in errors))

    def test_sequential_parent_cannot_impersonate_an_independent_reviewer(self) -> None:
        plan, run = current_preintegration_review_state()
        run["runtime_capabilities"]["worker_runtime"] = "parent"
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter["available_drivers"] = ["sequential_parent"]
        adapter["detection_source"] = "explicit"
        adapter.pop("capability_probe", None)

        selected = select_ready_nodes(plan, run)

        self.assertEqual([], selected["dispatchable_nodes"])
        deferred = {
            item["node_id"]: item["reason_codes"]
            for item in selected["deferred_nodes"]
        }
        self.assertIn(
            "independent_reviewer_unavailable", deferred["N-FRONTEND-REVIEW"]
        )


    def test_cancel_blocks_dispatch_with_run_cancelled(self) -> None:
        plan, run = current_preintegration_review_state()
        harness_transition._control(run, "cancelled", "user requested stop")

        selected = select_ready_nodes(plan, run)

        self.assertEqual([], selected["dispatchable_nodes"])
        self.assertTrue(selected["deferred_nodes"])
        self.assertTrue(
            all(
                "run_cancelled" in item["reason_codes"]
                for item in selected["deferred_nodes"]
            )
        )

    def test_transition_command_cancels_generated_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_path = Path(temp) / "RUN.md"
            self.assertEqual(
                0,
                new_run.main(
                    [
                        "--plan",
                        str(PLAN_TEMPLATE),
                        "--run-id",
                        "RUN-cancel-test",
                        "--branch",
                        "refs/heads/test-run",
                        "--out",
                        str(run_path),
                    ]
                ),
            )
            self.assertEqual(
                0,
                harness_transition.main(
                    [
                        "--plan",
                        str(PLAN_TEMPLATE),
                        "--run",
                        str(run_path),
                        "cancel",
                        "--source",
                        "user requested stop",
                    ]
                ),
            )
            self.assertEqual("cancelled", load_run(run_path)["control"]["desired_state"])

    def _write_review_cli_fixture(self, root: Path) -> tuple[Path, Path]:
        """Persist the dispatchable preintegration review state under a real repo root."""
        plan, run = current_preintegration_review_state()
        prd = root / "docs" / "goal" / "PRD.md"
        prd.parent.mkdir(parents=True)
        prd.write_bytes(b"frozen prd bytes\n")
        plan["sources"] = [
            {
                "id": "SRC-001",
                "kind": "prd",
                "location": "docs/goal/PRD.md",
                "owner": "user",
                "status": "frozen",
                "content_sha256": hashlib.sha256(prd.read_bytes()).hexdigest(),
                "source_revision": None,
                "staged_revision": None,
                "notes": "frozen prd",
            }
        ]
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest

        def refresh_plan_bindings(value: object) -> None:
            if isinstance(value, dict):
                if "plan_digest_sha256" in value:
                    value["plan_digest_sha256"] = digest
                for child in value.values():
                    refresh_plan_bindings(child)
            elif isinstance(value, list):
                for child in value:
                    refresh_plan_bindings(child)

        refresh_plan_bindings(run)
        for execution in run.get("verifier_executions", []):
            if not isinstance(execution, dict):
                continue
            key_document = execution.get("key_document")
            if isinstance(key_document, dict):
                execution["execution_key"] = execution_key_from_document(key_document)
                execution["evidence_key"] = execution["execution_key"]

        plan_path = root / "PLAN.md"
        run_path = root / "RUN.md"
        plan_path.write_text(
            manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
            encoding="utf-8",
        )
        run_path.write_text(
            manifest_markdown("## Harness Run State", "harness_run", run),
            encoding="utf-8",
        )
        return plan_path, run_path

    def _git(self, root: Path, *arguments: str) -> None:
        subprocess.run(
            ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
        )

    def _reserve_frontend_review(self, plan_path: Path, run_path: Path) -> list[str]:
        return [
            "--plan",
            str(plan_path),
            "--run",
            str(run_path),
            "--repo-root",
            str(plan_path.parent),
            "reserve-review-dispatch",
            "--node-id",
            "N-FRONTEND-REVIEW",
            "--worker-id",
            "RW-REVIEW-1",
            "--attempt-id",
            "ATT-REVIEW-1",
        ]

    def test_cli_reserve_review_dispatch_requires_repo_root_and_binds_exact_target(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._git(root, "init", "-q")
            self._git(root, "config", "user.email", "test@example.com")
            self._git(root, "config", "user.name", "Harness Test")
            plan_path, run_path = self._write_review_cli_fixture(root)
            self._git(root, "add", "docs/goal/PRD.md", "PLAN.md", "RUN.md")
            self._git(root, "commit", "-qm", "fixture")
            before = run_path.read_text(encoding="utf-8")

            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                code = harness_transition.main(
                    [
                        "--plan",
                        str(plan_path),
                        "--run",
                        str(run_path),
                        "reserve-review-dispatch",
                        "--node-id",
                        "N-FRONTEND-REVIEW",
                        "--worker-id",
                        "RW-REVIEW-1",
                        "--attempt-id",
                        "ATT-REVIEW-1",
                    ]
                )
            self.assertEqual(2, code)
            self.assertIn("--repo-root", stderr.getvalue())
            self.assertEqual(before, run_path.read_text(encoding="utf-8"))

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = harness_transition.main(
                    self._reserve_frontend_review(plan_path, run_path)
                )
            self.assertEqual(0, code)
            receipt = json.loads(stdout.getvalue())["dispatch_receipt"]
            self.assertEqual("N-FRONTEND-REVIEW", receipt["node_id"])
            self.assertEqual("RW-REVIEW-1", receipt["worker_id"])
            self.assertEqual("ATT-REVIEW-1", receipt["attempt_id"])
            self.assertEqual("spawn_subagent", receipt["launch_kind"])
            self.assertEqual("b" * 40, receipt["reviewed_sha"])
            self.assertEqual("C:/repo/worktrees/M1", receipt["review_path"])

            run = load_run(run_path)
            worker = run["review_workers"][-1]
            self.assertEqual("leased", worker["phase"])
            self.assertEqual("ATT-REVIEW-1", worker["attempt_id"])
            self.assertEqual("b" * 40, worker["reviewed_sha"])
            state = run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"]
            self.assertEqual("running", state["phase"])
            self.assertEqual(1, state["attempts"])
            self.assertEqual("ATT-REVIEW-1", state["last_attempt_id"])
            self.assertEqual("RW-REVIEW-1", state["bound_worker_id"])

    def test_cli_record_review_attempt_closes_the_reserved_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._git(root, "init", "-q")
            self._git(root, "config", "user.email", "test@example.com")
            self._git(root, "config", "user.name", "Harness Test")
            plan_path, run_path = self._write_review_cli_fixture(root)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    0, harness_transition.main(
                        self._reserve_frontend_review(plan_path, run_path)
                    )
                )

            with contextlib.redirect_stdout(io.StringIO()):
                code = harness_transition.main(
                    [
                        "--plan",
                        str(plan_path),
                        "--run",
                        str(run_path),
                        "record-review-attempt",
                        "--lineage",
                        "REVIEW-N-FRONTEND-REVIEW",
                        "--worker-id",
                        "RW-REVIEW-1",
                        "--attempt-id",
                        "ATT-REVIEW-1",
                        "--mission-id",
                        "M1",
                        "--result",
                        "pass",
                        "--evidence",
                        "reviewed the exact reserved head",
                    ]
                )
            self.assertEqual(0, code)

            run = load_run(run_path)
            worker = run["review_workers"][-1]
            self.assertEqual("worker_passed", worker["phase"])
            self.assertEqual("pass", worker["outcome"])
            attempt = run["attempt_log"][-1]
            self.assertEqual("ATT-REVIEW-1", attempt["attempt_id"])
            self.assertEqual("review", attempt["kind"])
            self.assertEqual("pass", attempt["result"])
            self.assertEqual(
                "REVIEW-N-FRONTEND-REVIEW", attempt["review_lineage_id"]
            )
            self.assertEqual(
                1,
                run["review_lineages"]["REVIEW-N-FRONTEND-REVIEW"][
                    "consumed_attempts"
                ],
            )
            edge = run["graph_state"]["edge_states"]["E-FRONTEND-VISUAL-REVIEW"]
            self.assertEqual("traversed", edge["status"])
            self.assertEqual(1, edge["traversals"])
            self.assertEqual("ATT-REVIEW-1", edge["source_attempt_id"])

    def test_cli_grant_review_attempts_is_exact_and_one_shot(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan, run = current_preintegration_review_state()
            lineage = run["review_lineages"]["REVIEW-N-FRONTEND-REVIEW"]
            for index in (1, 2):
                run["attempt_log"].append(
                    {
                        "attempt_id": f"ATT-HISTORICAL-REVIEW-{index}",
                        "mission_id": "M1",
                        "task_id": None,
                        "lease_id": None,
                        "kind": "review",
                        "result": "fix_required",
                        "evidence": ["historical review defect"],
                        "review_lineage_id": "REVIEW-N-FRONTEND-REVIEW",
                        "failure_family_ids": ["FAMILY-MARKDOWN"],
                    }
                )
            lineage["consumed_attempts"] = 2
            lineage["failure_families"] = [
                {
                    "id": "FAMILY-MARKDOWN",
                    "primitive": "Markdown scanner",
                    "equivalence_classes": ["reference links", "fenced code"],
                    "strategy": "replace regex patches with a fence-aware scanner",
                    "status": "open",
                }
            ]
            plan_path = root / "PLAN.md"
            run_path = root / "RUN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path.write_text(
                manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            grant_arguments = [
                "--plan",
                str(plan_path),
                "--run",
                str(run_path),
                "grant-review-attempts",
                "--lineage",
                "REVIEW-N-FRONTEND-REVIEW",
                "--decision-id",
                "OWNER-REVIEW-1",
                "--source",
                "I approve OWNER-REVIEW-1 for one additional review",
                "--source-ref",
                "user_turn:turn-123",
                "--failure-family-id",
                "FAMILY-MARKDOWN",
                "--strategy",
                "structural scanner repair",
                "--acceptance",
                "all Markdown reference classes",
                "--acceptance",
                "fenced code renders identically",
                "--additional-attempts",
                "1",
            ]

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, harness_transition.main(grant_arguments))

            granted = load_run(run_path)["review_lineages"][
                "REVIEW-N-FRONTEND-REVIEW"
            ]
            self.assertEqual(1, granted["additional_allowance"])
            decision = granted["owner_decisions"][0]
            self.assertEqual("user_turn:turn-123", decision["source_ref"])
            self.assertEqual("FAMILY-MARKDOWN", decision["failure_family_id"])
            self.assertEqual("structural scanner repair", decision["strategy"])
            self.assertEqual(
                [
                    "all Markdown reference classes",
                    "fenced code renders identically",
                ],
                decision["acceptance_matrix"],
            )
            family = granted["failure_families"][0]
            self.assertEqual("repairing", family["status"])
            self.assertEqual("structural scanner repair", family["strategy"])

            before = run_path.read_text(encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                code = harness_transition.main(grant_arguments)
            self.assertEqual(2, code)
            self.assertIn("one owner-granted successor", stderr.getvalue())
            self.assertEqual(before, run_path.read_text(encoding="utf-8"))

    def test_interrupted_mission_worker_is_reconciled(self) -> None:
        plan, run = current_preintegration_review_state()
        worker_id = "W-INTERRUPTED"
        reason = "host stopped mid-mission"
        run["workers"] = [
            {
                "worker_id": worker_id,
                "mission_id": "M1",
                "lease_id": "LEASE-INTERRUPTED",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "batch_base_sha": run["integration"]["batch_base_sha"],
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "task_thread_id": None,
                "worktree_path": "C:/repo/worktrees/m1",
                "branch_ref": "refs/heads/codex/m1",
                "report_path": None,
                "phase": "worker_running",
                "worker_head_sha": None,
            }
        ]
        run["mission_states"]["M1"]["phase"] = "worker_running"
        run["graph_state"]["node_states"]["N-M1"].update(
            {
                "phase": "running",
                "bound_worker_id": worker_id,
                "last_attempt_id": "ATT-M1-INTERRUPTED",
            }
        )

        harness_transition._reconcile_interrupted(
            run,
            Namespace(worker_id=worker_id, reason=reason),
        )

        self.assertEqual("blocked", run["workers"][0]["phase"])
        self.assertEqual("blocked", run["mission_states"]["M1"]["phase"])
        self.assertIn(reason, run["mission_states"]["M1"]["blockers"])
        node_state = run["graph_state"]["node_states"]["N-M1"]
        self.assertEqual("blocked", node_state["phase"])
        self.assertEqual("blocked", node_state["last_outcome"])
        self.assertEqual(
            "interrupted_worker_reconciliation",
            run["attempt_log"][-1]["kind"],
        )
        self.assertEqual("blocked", run["attempt_log"][-1]["result"])


if __name__ == "__main__":
    unittest.main()

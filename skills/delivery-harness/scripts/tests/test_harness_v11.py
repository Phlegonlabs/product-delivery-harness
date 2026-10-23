#!/usr/bin/env python3
"""Regression tests for the PLAN-v6/RUN-v11 orchestration controls."""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from unittest import mock
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
UI_TESTS_DIR = Path(__file__).resolve().parents[3] / "ui-design-builder" / "scripts" / "tests"
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(UI_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(UI_TESTS_DIR))

import harness_transition  # noqa: E402
from harness_core import load_plan, load_run, plan_digest  # noqa: E402
from harness_manifest import validate_run  # noqa: E402
from harness_ui_evidence import validate_integration_head_against_git  # noqa: E402
from manifest_fixtures import manifest_markdown, materialize_plan_sources  # noqa: E402
from render_review_packet import render_packet  # noqa: E402
from select_ready_nodes import select_ready_nodes  # noqa: E402
from test_harness_manifest import valid_plan, valid_run  # noqa: E402
from test_select_ready_nodes import current_preintegration_review_state  # noqa: E402
from verifier_runtime import execution_key_from_document  # noqa: E402

while str(UI_TESTS_DIR) in sys.path:
    sys.path.remove(str(UI_TESTS_DIR))




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
        # reserve-review-dispatch records this exact spawn receipt.
        run["authorizations"]["spawn_subagents"]["scope"]["targets"].append(
            f"worker:{worker_id}"
        )
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
        self.assertEqual(1, run["graph_state"]["node_states"][node_id]["attempts"])


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

    def test_candidate_guard_rejects_parent_owned_and_coordination_paths(self) -> None:
        """A broad mission scope cannot authorize committed PLAN/RUN state."""

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", "-b", "integration"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Harness Test"],
                cwd=root,
                check=True,
            )
            source = root / "src.txt"
            source.write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "src.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
            base = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()

            goal = root / "docs" / "goal"
            goal.mkdir(parents=True)
            (goal / "RUN.md").write_text("parent coordination\n", encoding="utf-8")
            subprocess.run(["git", "add", "docs/goal/RUN.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "committed run"], cwd=root, check=True)
            candidate = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()

            plan = {"missions": [{"id": "M1", "write_scope": ["docs/goal/**"]}]}
            run = {"integration": {"coordination_paths": ["docs/goal/**"]}}
            with self.assertRaisesRegex(
                harness_transition.ManifestError,
                "RUN.md",
            ):
                harness_transition._reject_unplanned_candidate_paths(
                    plan,
                    run,
                    root,
                    base,
                    candidate,
                    allowed_scopes=["docs/goal/**"],
                )

            # The parent-owned filename remains blocked even when the RUN
            # snapshot forgot to list it as a coordination path.
            run["integration"]["coordination_paths"] = []
            with self.assertRaisesRegex(
                harness_transition.ManifestError,
                "RUN.md",
            ):
                harness_transition._reject_unplanned_candidate_paths(
                    plan,
                    run,
                    root,
                    base,
                    candidate,
                    allowed_scopes=["docs/goal/**"],
                )

    def test_documented_closeout_rewrites_do_not_stale_candidate(self) -> None:
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
            tasks = root / "docs" / "tasks.md"
            tasks.write_text("tasks view\n", encoding="utf-8")
            (goal / "REFINEMENT_BACKLOG.md").write_text("backlog\n", encoding="utf-8")
            subprocess.run(["git", "add", "docs/tasks.md", "docs/goal/REFINEMENT_BACKLOG.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "run records"], cwd=root, check=True)
            branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()
            run = {
                "schema_version": 11,
                "integration": {
                    "branch": branch,
                    "integration_head_sha": candidate,
                    "coordination_paths": [
                        "docs/goal/PLAN.md",
                        "docs/goal/RUN.md",
                        "docs/goal/DECISIONS.md",
                        "docs/goal/REFINEMENT_BACKLOG.md",
                        "docs/tasks.md",
                    ],
                },
            }

            self.assertEqual([], validate_integration_head_against_git(run, root))

            tasks.write_text("tasks view with closeout update log row\n", encoding="utf-8")
            subprocess.run(["git", "add", "docs/tasks.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "tasks update log"], cwd=root, check=True)
            self.assertEqual([], validate_integration_head_against_git(run, root))

            (root / "src.txt").write_text("changed after review\n", encoding="utf-8")
            subprocess.run(["git", "add", "src.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "code after review"], cwd=root, check=True)
            self.assertTrue(validate_integration_head_against_git(run, root))

    def test_product_path_listed_as_coordination_still_stales_candidate(self) -> None:
        """RUN cannot list product code as coordination to hide a newer head."""

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Harness Test"], cwd=root, check=True)
            source = root / "src" / "app.ts"
            source.parent.mkdir()
            source.write_text("candidate\n", encoding="utf-8")
            subprocess.run(["git", "add", "src/app.ts"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "candidate"], cwd=root, check=True)
            candidate = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            source.write_text("untested change\n", encoding="utf-8")
            subprocess.run(["git", "add", "src/app.ts"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "c2"], cwd=root, check=True)
            branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()
            run = {
                "schema_version": 11,
                "integration": {
                    "branch": branch,
                    "integration_head_sha": candidate,
                    "coordination_paths": ["docs/goal/RUN.md", "src/app.ts"],
                },
            }

            errors = validate_integration_head_against_git(run, root)
            self.assertTrue(any("RUN.md is stale" in error for error in errors))

    def test_product_file_renamed_onto_coordination_path_still_stales_candidate(self) -> None:
        """A rename must not hide the deleted product path from the check."""

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Harness Test"], cwd=root, check=True)
            source = root / "src" / "app.ts"
            source.parent.mkdir()
            source.write_text("export const app = 'candidate';\n" * 20, encoding="utf-8")
            subprocess.run(["git", "add", "src/app.ts"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "candidate"], cwd=root, check=True)
            candidate = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
            (root / "docs" / "epics").mkdir(parents=True)
            subprocess.run(["git", "mv", "src/app.ts", "docs/epics/EPIC-7.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "rename"], cwd=root, check=True)
            branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip()
            run = {
                "schema_version": 11,
                "integration": {
                    "branch": branch,
                    "integration_head_sha": candidate,
                    "coordination_paths": ["docs/goal/RUN.md", "docs/epics/EPIC-7.md"],
                },
            }

            errors = validate_integration_head_against_git(run, root)
            self.assertTrue(any("RUN.md is stale" in error for error in errors), errors)

    def test_validate_run_rejects_product_and_frozen_coordination_paths(self) -> None:
        # An older in-flight RUN keeps its recorded coordination_paths; the
        # allowlist checks apply to 0.55.0+ RUNs and to a null or malformed
        # pin.
        plan = valid_plan()
        run = valid_run(plan)
        self.assertEqual([], validate_run(plan, run))
        gate = run["runtime_capabilities"]["runtime_adapter"]["version_gate"]
        run["integration"]["coordination_paths"].append("docs/epics/EPIC-1.md")
        cases = (
            ("src/app.ts", "unsupported product-path coordination entries: src/app.ts"),
            ("docs/product/PRD.md", "frozen product/design sources cannot be coordination paths"),
        )
        for version, rejected in (
            ("0.54.5", False),
            ("0.55.0", True),
            (None, True),
            ("0.54", True),
        ):
            gate["required_harness_version"] = version
            run["integration"]["coordination_paths"][-1] = "docs/epics/EPIC-1.md"
            # The fixture has other version-gated gaps; compare against them.
            baseline = validate_run(plan, run)
            self.assertFalse(any("coordination_paths" in e for e in baseline), baseline)
            for path, message in cases:
                with self.subTest(version=version, path=path):
                    run["integration"]["coordination_paths"][-1] = path
                    errors = validate_run(plan, run)
                    if rejected:
                        self.assertTrue(any(message in e for e in errors), errors)
                    else:
                        self.assertEqual(baseline, errors)

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
            gate = run["runtime_capabilities"]["runtime_adapter"]["version_gate"]
            gate.update(
                {
                    "loaded_contract_digest": None,
                    "installed_contract_digest": "a" * 64,
                    "status": "adopted",
                    "contract_adoption": {
                        "session_id": gate["session_id"],
                        "adopted_at": "2026-09-27T00:00:00Z",
                        "contract_digest_sha256": "a" * 64,
                        "owner_source": "owner instruction in this task",
                        "reading_evidence": ["parent re-read the fixed contract"],
                    },
                }
            )

            packet = render_packet(plan, run, "N-REVIEW-M1", root, max_diff_bytes=64)

            self.assertIn("## Diff (truncated)", packet)
            self.assertIn("## Changed files\n\nfile.txt", packet)
            full_packet = render_packet(plan, run, "N-REVIEW-M1", root)
            self.assertNotIn("## Changed files", full_packet)
            self.assertNotIn("## Diff stat", full_packet)
            self.assertIn("diff --git a/file.txt b/file.txt", full_packet)
            self.assertEqual(packet.split("## Contract")[1].split("## Diff")[0],
                             full_packet.split("## Contract")[1].split("## Diff")[0])
            self.assertIn("- Attempts:", packet)
            self.assertIn('"required_tools": []', packet)
            self.assertNotIn('"contract_adoption"', packet)
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
            # No mission review precedes a final_candidate review.
            plan["review_policy"] = "final_candidate"
            final_packet = render_packet(plan, run, "N-REVIEW-M1", root, max_diff_bytes=64)
            self.assertNotIn("## Already-reviewed mission heads", final_packet)
            self.assertNotIn("## Integration focus", final_packet)
            del plan["review_policy"]

            review_node = next(
                node
                for node in plan["graph"]["nodes"]
                if node["id"] == "N-REVIEW-M1"
            )
            review_node["review"]["type"] = "security"
            review_node["review"]["mission_ids"] = ["M1", "M2"]
            run["review_lineages"]["REVIEW-M1"]["review_type"] = "security"
            run["review_lineages"]["REVIEW-M1"]["mission_ids"] = ["M1", "M2"]
            security_packet = render_packet(
                plan, run, "N-REVIEW-M1", root, max_diff_bytes=64
            )

            self.assertIn('"review_type": "security"', security_packet)
            self.assertIn(
                '"skill_binding_slot": "code_security_verification"',
                security_packet,
            )

    def test_transition_command_pauses_generated_run(self) -> None:
        # Intentionally legacy: this test covers the pause transition command,
        # not current 0.38 source readiness. Keep the old pin explicit.
        with tempfile.TemporaryDirectory() as temp:
            plan = valid_plan()
            for mission in plan.get("missions", []):
                mission["write_scope"] = ["docs/README.md"]
                for task in mission.get("tasks", []):
                    task["write_scope"] = ["docs/README.md"]
            plan["security_review"] = {
                "status": "not_applicable",
                "skill_slot": "code_security_verification",
                "reason": "documentation-only transition fixture with no implementation candidate",
            }
            run = valid_run(plan)
            run["runtime_capabilities"]["runtime_adapter"]["version_gate"][
                "required_harness_version"
            ] = "0.37.0"
            run["integration"]["branch"] = "refs/heads/test-run"
            run["landing"]["continuity"] = {
                "status": "planned",
                "branch_ref": "refs/heads/test-run",
                "head_sha": None,
                "reason": "legacy transition fixture",
            }
            run["plan"]["digest_sha256"] = plan_digest(plan)
            plan_path = Path(temp) / "PLAN.md"
            run_path = Path(temp) / "RUN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path.write_text(
                manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            self.assertEqual(
                0,
                harness_transition.main(
                    [
                        "--plan",
                        str(plan_path),
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
            run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"]["attempts"],
        )


    def test_subagent_review_reservation_records_exact_spawn_receipt(self) -> None:
        plan, run = current_preintegration_review_state()
        harness_transition._reserve_review_dispatch(
            plan,
            run,
            Namespace(
                node_id="N-FRONTEND-REVIEW",
                worker_id="RW-SPAWN",
                attempt_id="ATT-SPAWN",
                report_path=None,
            ),
            repo_root=None,
        )

        self.assertEqual("subagent", run["review_workers"][-1]["worker_runtime"])
        targets = run["authorizations"]["spawn_subagents"]["scope"]["targets"]
        self.assertIn("worker:RW-SPAWN", targets)
        self.assertEqual([], validate_run(plan, run))

        # The receipt survives the user narrowing the grant to exact targets.
        targets.remove("*")
        self.assertEqual([], validate_run(plan, run))

        # From Harness 0.55.0, a reviewer without the receipt has no exact
        # launch authorization.
        targets.remove("worker:RW-SPAWN")
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"][
            "required_harness_version"
        ] = "0.55.0"
        self.assertIn(
            "run.authorizations.spawn_subagents: must exactly authorize review target worker:RW-SPAWN",
            validate_run(plan, run),
        )

    def test_subagent_review_selection_agrees_with_reservation(self) -> None:
        # The selector offers a subagent reviewer only when reservation can
        # record a receipt that validate_run accepts.
        message = (
            "run.authorizations.spawn_subagents: "
            "must exactly authorize review target worker:RW-SEL"
        )
        cases = (
            ("0.54.5", ["*"], True),
            ("0.55.0", ["*"], False),
            ("0.55.0", None, True),
        )
        for version, mission_scope, dispatchable in cases:
            with self.subTest(version=version, mission_scope=mission_scope):
                plan, run = current_preintegration_review_state()
                if mission_scope is not None:
                    run["authorizations"]["spawn_subagents"]["scope"][
                        "mission_ids"
                    ] = mission_scope
                    # Mission workers carry their own exact-mission check;
                    # keep them out of this reviewer-only case.
                    for worker in run["workers"]:
                        worker["worker_runtime"] = "parent"
                run["runtime_capabilities"]["runtime_adapter"]["version_gate"][
                    "required_harness_version"
                ] = version
                # The fixture has no repo root, which a >= 0.38 RUN needs for
                # the current-pair check; validate_run is checked directly.
                with mock.patch.object(
                    harness_transition, "validate_current_plan_run", return_value=[]
                ):
                    selection = select_ready_nodes(
                        plan, run, manifest_already_validated=True
                    )
                    before = validate_run(plan, run)
                    reserve = lambda: harness_transition._reserve_review_dispatch(  # noqa: E731
                        plan,
                        run,
                        Namespace(
                            node_id="N-FRONTEND-REVIEW",
                            worker_id="RW-SEL",
                            attempt_id="ATT-SEL",
                            report_path=None,
                        ),
                        repo_root=None,
                    )
                    listed = [
                        item["node_id"] for item in selection["dispatchable_nodes"]
                    ]
                    if dispatchable:
                        self.assertIn("N-FRONTEND-REVIEW", listed)
                        reserve()
                        after = validate_run(plan, run)
                        self.assertNotIn(message, after)
                        self.assertEqual(before, after)
                    else:
                        self.assertNotIn("N-FRONTEND-REVIEW", listed)
                        with self.assertRaisesRegex(
                            harness_transition.ManifestError,
                            "not dispatchable: .*action_not_authorized",
                        ):
                            reserve()

    def test_subagent_review_receipt_is_not_required_before_0_55(self) -> None:
        # A RUN closed under 0.54.5 reserved its subagent reviewer without a
        # worker:<id> receipt. Its archived record must still validate.
        plan, run = current_preintegration_review_state()
        harness_transition._reserve_review_dispatch(
            plan,
            run,
            Namespace(
                node_id="N-FRONTEND-REVIEW",
                worker_id="RW-OLD",
                attempt_id="ATT-OLD",
                report_path=None,
            ),
            repo_root=None,
        )
        run["authorizations"]["spawn_subagents"]["scope"]["targets"].remove(
            "worker:RW-OLD"
        )
        run["status"] = "complete"
        gate = run["runtime_capabilities"]["runtime_adapter"]["version_gate"]
        message = (
            "run.authorizations.spawn_subagents: "
            "must exactly authorize review target worker:RW-OLD"
        )
        gate["required_harness_version"] = "0.54.5"
        old_errors = validate_run(plan, run)
        gate["required_harness_version"] = "0.55.0"
        new_errors = validate_run(plan, run)
        # Other version gates fire on this fixture at both versions; only the
        # receipt rule differs.
        self.assertNotIn(message, old_errors)
        self.assertEqual({message}, set(new_errors) - set(old_errors))

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
        # Intentionally legacy: this test covers the cancel transition command,
        # not current 0.38 source readiness. Keep the old pin explicit.
        with tempfile.TemporaryDirectory() as temp:
            plan = valid_plan()
            for mission in plan.get("missions", []):
                mission["write_scope"] = ["docs/README.md"]
                for task in mission.get("tasks", []):
                    task["write_scope"] = ["docs/README.md"]
            plan["security_review"] = {
                "status": "not_applicable",
                "skill_slot": "code_security_verification",
                "reason": "documentation-only transition fixture with no implementation candidate",
            }
            run = valid_run(plan)
            run["runtime_capabilities"]["runtime_adapter"]["version_gate"][
                "required_harness_version"
            ] = "0.37.0"
            run["integration"]["branch"] = "refs/heads/test-run"
            run["landing"]["continuity"] = {
                "status": "planned",
                "branch_ref": "refs/heads/test-run",
                "head_sha": None,
                "reason": "legacy transition fixture",
            }
            run["plan"]["digest_sha256"] = plan_digest(plan)
            plan_path = Path(temp) / "PLAN.md"
            run_path = Path(temp) / "RUN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path.write_text(
                manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            self.assertEqual(
                0,
                harness_transition.main(
                    [
                        "--plan",
                        str(plan_path),
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
        plan["ui_surfaces"] = []
        plan["sources"] = valid_plan()["sources"]
        materialize_plan_sources(root, plan)
        for edge in plan["graph"]["edges"]:
            run["graph_state"]["edge_states"].setdefault(edge["id"], {
                "status": "dormant", "traversals": 0, "source_attempt_id": None})
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

    def _bind_cli_fixture_to_git(self, root: Path, run_path: Path) -> None:
        """Bind the legacy review fixture to the real temporary checkout head."""

        run = load_run(run_path)
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=root, text=True
        ).strip()
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
        run["integration"].update(
            {
                "branch": f"refs/heads/{branch}",
                "batch_base_sha": head,
                "integration_head_sha": head,
            }
        )
        run["observed"]["git"].update(
            {
                "parent_branch": f"refs/heads/{branch}",
                "parent_head_sha": head,
                "parent_worktree_path": str(root),
                "parent_dirty": False,
            }
        )
        mission_state = run["mission_states"]["M1"]
        worker = next(
            item
            for item in run["workers"]
            if item["worker_id"] == mission_state["worker_id"]
        )
        worker_observation = next(
            item
            for item in run["observed"]["git"]["worktrees"]
            if item["path"] == worker["worktree_path"]
        )
        run["observed"]["git"]["worktrees"] = [
            {
                "path": str(root),
                "branch_ref": f"refs/heads/{branch}",
                "head_sha": head,
                "managed_by": "parent",
                "dirty": False,
            },
            worker_observation,
        ]
        run["landing"]["continuity"] = {
            "status": "planned",
            "branch_ref": f"refs/heads/{branch}",
            "head_sha": None,
            "reason": "review fixture",
        }
        self.assertEqual([], validate_run(load_plan(root / "PLAN.md"), run))
        run_path.write_text(
            manifest_markdown("## Harness Run State", "harness_run", run),
            encoding="utf-8",
        )

    def _acquire_review_lock(self, plan_path: Path, run_path: Path) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(
                0,
                harness_transition.main(
                    [
                        "--plan",
                        str(plan_path),
                        "--run",
                        str(run_path),
                        "--session-id",
                        "review-cli-tests",
                        "acquire-run-lock",
                    ]
                ),
            )

    def _reserve_frontend_review(self, plan_path: Path, run_path: Path) -> list[str]:
        return [
            "--plan",
            str(plan_path),
            "--run",
            str(run_path),
            "--session-id",
            "review-cli-tests",
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
            self._git(root, "checkout", "-b", "test-run")
            plan_path, run_path = self._write_review_cli_fixture(root)
            self._git(
                root,
                "add",
                "docs/product",
                "PLAN.md",
                "RUN.md",
            )
            self._git(root, "commit", "-qm", "fixture")
            self._bind_cli_fixture_to_git(root, run_path)
            self._acquire_review_lock(plan_path, run_path)
            before = run_path.read_text(encoding="utf-8")

            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                code = harness_transition.main(
                    [
                        "--plan",
                        str(plan_path),
                        "--run",
                        str(run_path),
                        "--session-id",
                        "review-cli-tests",
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
            self._git(root, "checkout", "-b", "test-run")
            plan_path, run_path = self._write_review_cli_fixture(root)
            self._git(
                root,
                "add",
                "docs/product",
                "PLAN.md",
                "RUN.md",
            )
            self._git(root, "commit", "-qm", "fixture")
            self._bind_cli_fixture_to_git(root, run_path)
            self._acquire_review_lock(plan_path, run_path)
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
                        "--session-id",
                        "review-cli-tests",
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
                run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"]["attempts"],
            )
            edge = run["graph_state"]["edge_states"]["E-FRONTEND-VISUAL-REVIEW"]
            self.assertEqual("traversed", edge["status"])
            self.assertEqual(1, edge["traversals"])
            self.assertEqual("ATT-REVIEW-1", edge["source_attempt_id"])



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

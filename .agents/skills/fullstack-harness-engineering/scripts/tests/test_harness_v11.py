#!/usr/bin/env python3
"""Regression tests for the PLAN-v6/RUN-v11 orchestration controls."""

from __future__ import annotations

import copy
import subprocess
import sys
import tempfile
import unittest
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
from render_review_packet import render_packet  # noqa: E402
from select_ready_nodes import select_ready_nodes  # noqa: E402
from test_harness_manifest import valid_plan, valid_run  # noqa: E402
from test_select_ready_nodes import current_preintegration_review_state  # noqa: E402


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
            self.assertNotIn('"harness_plan"', packet)

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

    def test_transition_command_records_family_and_owner_grant(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            run_path = Path(temp) / "RUN.md"
            self.assertEqual(
                0,
                new_run.main(
                    [
                        "--plan",
                        str(PLAN_TEMPLATE),
                        "--run-id",
                        "RUN-review-transition",
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
                        "--plan", str(PLAN_TEMPLATE),
                        "--run", str(run_path),
                        "record-review-attempt",
                        "--lineage", "REVIEW-M1",
                        "--attempt-id", "ATT-REVIEW-1",
                        "--mission-id", "M1",
                        "--result", "fix_required",
                        "--evidence", "parser variants failed",
                        "--failure-family-id", "FAMILY-MARKDOWN",
                        "--failure-primitive", "Markdown scanner",
                        "--equivalence-class", "reference links",
                        "--equivalence-class", "fenced code",
                        "--strategy", "replace regex patches with a fence-aware scanner",
                    ]
                ),
            )
            self.assertEqual(
                0,
                harness_transition.main(
                    [
                        "--plan", str(PLAN_TEMPLATE),
                        "--run", str(run_path),
                        "grant-review-attempts",
                        "--lineage", "REVIEW-M1",
                        "--decision-id", "OWNER-1",
                        "--source", "explicit owner decision",
                        "--strategy", "structural scanner repair",
                        "--acceptance", "all Markdown reference classes",
                        "--additional-attempts", "1",
                    ]
                ),
            )
            lineage = load_run(run_path)["review_lineages"]["REVIEW-M1"]
            self.assertEqual(1, lineage["consumed_attempts"])
            self.assertEqual(1, lineage["additional_allowance"])
            self.assertEqual("FAMILY-MARKDOWN", lineage["failure_families"][0]["id"])


if __name__ == "__main__":
    unittest.main()

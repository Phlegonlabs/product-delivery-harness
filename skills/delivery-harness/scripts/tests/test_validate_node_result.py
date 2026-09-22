#!/usr/bin/env python3
"""Dedicated tests for validate_node_result.py."""

from __future__ import annotations

import copy
import contextlib
import io
import json
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

from harness_manifest import plan_digest  # noqa: E402
from test_graph_orchestration import valid_graph_plan, valid_graph_run  # noqa: E402
from test_harness_manifest import authorize_execution  # noqa: E402
from manifest_fixtures import manifest_markdown  # noqa: E402
import test_harness_strict_authority as strict_authority_fixtures  # noqa: E402
from validate_node_result import main as validate_node_result_main, validate_node_result  # noqa: E402


def running_result(plan: dict[str, object], run: dict[str, object]) -> dict[str, object]:
    digest = plan_digest(plan)
    authorize_execution(
        run,
        ["M1"],
        status="running",
        plan=plan,
        digest=digest,
    )
    run["graph_state"]["node_states"]["N-M1"].update(
        {
            "phase": "running",
            "attempts": 1,
            "last_attempt_id": "ATT-N-M1-1",
            "bound_worker_id": "W-M1",
        }
    )
    run["mission_states"]["M1"].update(
        {
            "phase": "worker_running",
            "lease_id": "LEASE-M1-1",
            "lease_plan_revision": plan["revision"],
            "lease_plan_digest_sha256": digest,
            "worker_id": "W-M1",
            "base_sha": "a" * 40,
        }
    )
    return {
        "run_id": run["run_id"],
        "node_id": "N-M1",
        "attempt_id": "ATT-N-M1-1",
        "plan_id": plan["plan_id"],
        "plan_revision": plan["revision"],
        "plan_digest_sha256": digest,
        "graph_revision": run["graph_state"]["graph_revision"],
        "batch_base_sha": run["integration"]["batch_base_sha"],
        "status": "succeeded",
        "outcome": "pass",
        "worker_result": {"status": "PASS"},
        "refinement_request": None,
        "evidence_paths": ["worker-result.json"],
    }


from manifest_fixtures import native_capability_probe


class ValidateNodeResultTests(unittest.TestCase):
    def test_cli_accepts_repo_root_for_current_harness_038_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan, _run = strict_authority_fixtures.StrictAuthorityJoinTests._headless_fixture(root)
            plan["security_review"] = {
                "status": "not_applicable",
                "skill_slot": "code_security_verification",
                "reason": "documentation-only fixture",
            }
            for mission in plan["missions"]:
                mission["write_scope"] = ["docs/fixture.md"]
                for task in mission["tasks"]:
                    task["write_scope"] = ["docs/fixture.md"]
            run = strict_authority_fixtures.StrictAuthorityJoinTests._run(plan)
            subprocess.run(["git", "init", "-q", "-b", "codex/test"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Harness Test"],
                cwd=root,
                check=True,
            )
            subprocess.run(["git", "add", "docs/product"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "strict sources"], cwd=root, check=True)
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip()
            run["integration"].update(
                {
                    "branch": "codex/test",
                    "batch_base_sha": head,
                    "integration_head_sha": head,
                }
            )
            run["observed"]["git"].update(
                {
                    "parent_worktree_path": str(root.resolve()),
                    "parent_branch": "codex/test",
                    "parent_head_sha": head,
                    "parent_dirty": False,
                    "worktrees": [],
                }
            )
            result = running_result(plan, run)
            run["mission_states"]["M1"]["base_sha"] = head
            plan_path = root / "PLAN.md"
            run_path = root / "RUN.md"
            result_path = root / "result.json"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path.write_text(
                manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            result_path.write_text(json.dumps(result), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = validate_node_result_main(
                    [
                        "--plan", str(plan_path),
                        "--run", str(run_path),
                        "--result", str(result_path),
                        "--repo-root", str(root),
                    ]
                )
            self.assertEqual(0, code, output.getvalue())
            self.assertEqual("PASS", json.loads(output.getvalue())["status"])

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = validate_node_result_main(
                    [
                        "--plan", str(plan_path),
                        "--run", str(run_path),
                        "--result", str(result_path),
                    ]
                )
            self.assertEqual(2, code)
            self.assertIn(
                "current PLAN/RUN validation requires --repo-root for the Harness 0.38 authority join",
                output.getvalue(),
            )

    def test_matching_result_for_a_running_node_passes(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        result = running_result(plan, run)

        self.assertEqual([], validate_node_result(plan, run, result))

    def test_stale_attempt_id_is_rejected(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        result = running_result(plan, run)
        result["attempt_id"] = "ATT-STALE"

        errors = validate_node_result(plan, run, result)

        self.assertTrue(any("active attempt" in error for error in errors))

    def test_current_pass_review_result_rejects_findings_without_severity(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        authorize_execution(run, ["M1"], status="running", plan=plan, digest=digest)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
            }
        )
        run["runtime_capabilities"]["runtime_adapter"].update(
            {
                "capability_probe": native_capability_probe(subagents=True),
                "provider": "codex",
                "available_drivers": ["subagents", "sequential_parent"],
                "detection_source": "observed",
            }
        )
        review_node = next(
            node for node in plan["graph"]["nodes"] if node["id"] == "N-REVIEW-M1"
        )
        run["integration"]["integration_head_sha"] = "a" * 40
        run["graph_state"]["node_states"][review_node["id"]].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-M1-1",
                "bound_worker_id": "RW-REVIEW-M1-1",
            }
        )
        run["review_workers"] = [
            {
                "worker_id": "RW-REVIEW-M1-1",
                "node_id": review_node["id"],
                "attempt_id": "ATT-REVIEW-M1-1",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "graph_revision": run["graph_state"]["graph_revision"],
                "reviewed_sha": "a" * 40,
                "review_path": "C:/repo/review",
                "worker_runtime": "subagent",
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
                "report_path": None,
                "phase": "worker_running",
                "outcome": None,
                "findings": [],
            }
        ]
        result = {
            "run_id": run["run_id"],
            "node_id": review_node["id"],
            "attempt_id": "ATT-REVIEW-M1-1",
            "plan_id": plan["plan_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "graph_revision": run["graph_state"]["graph_revision"],
            "batch_base_sha": run["integration"]["batch_base_sha"],
            "status": "succeeded",
            "outcome": "pass",
            "worker_result": {
                "reviewed_sha": "a" * 40,
                "findings": ["informational note without a severity field"],
                "evidence_summary": "The review returned a finding.",
            },
            "refinement_request": None,
            "evidence_paths": ["review.json"],
        }

        errors = validate_node_result(plan, run, result)

        self.assertTrue(
            any("current PASS review result must not contain findings" in error for error in errors),
            errors,
        )

    def test_schema_mismatch_reports_the_required_versions(self) -> None:
        # Structural validation normally rejects the pair first. Stub it so
        # this test guards validate_node_result's own schema gate.
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        result = running_result(plan, run)

        for plan_version, run_version in [(5, 6), (4, 8), (4, 9)]:
            with self.subTest(plan_version=plan_version, run_version=run_version):
                plan["schema_version"] = plan_version
                run["schema_version"] = run_version

                errors = validate_node_result(plan, run, result)

                self.assertIn(
                    "node result validation requires PLAN v6 with RUN v11",
                    errors,
                )

    def test_plan_v6_run_v11_pair_uses_graph_node_result_validation(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        result = running_result(plan, run)

        errors = validate_node_result(plan, run, result)

        self.assertEqual([], errors)

    def test_contract_gap_outcome_requires_a_refinement_request(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        result = running_result(plan, run)
        result["status"] = "blocked"
        result["outcome"] = "contract_gap"
        result["worker_result"] = None

        errors = validate_node_result(plan, run, copy.deepcopy(result))

        self.assertTrue(any("refinement_request" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

"""Review triage: non-blocking notes and environment-blocked attempt refunds.

Consumer runs kept looping review -> repair -> review because every reviewer
observation became a blocking finding and every environment failure consumed
one of the two review attempts. These tests pin the triage contract: notes
never block, and an environment block refunds the node budget so the selector
mints a fresh attempt.
"""

from __future__ import annotations

import contextlib
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
import manifest_fixtures as mf  # noqa: E402
from harness_core import load_plan, load_run, plan_digest  # noqa: E402
from harness_manifest import validate_run  # noqa: E402
from harness_worker_result_transition import record_worker_result  # noqa: E402
from manifest_fixtures import manifest_markdown, materialize_plan_sources  # noqa: E402
from select_ready_nodes import select_ready_nodes  # noqa: E402
from test_harness_manifest import valid_plan  # noqa: E402
from test_select_ready_nodes import current_preintegration_review_state  # noqa: E402
from verifier_runtime import (  # noqa: E402
    execution_key_from_document,
    observe_plan_host_runtimes,
    run_verifier,
)


class ReviewNoteCliTests(unittest.TestCase):
    """Drive record-review-attempt through the real CLI on a real checkout."""

    def _git(self, root: Path, *arguments: str) -> None:
        subprocess.run(
            ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
        )

    def _prepare(self) -> tuple[Path, Path]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self._git(root, "init", "-q")
        self._git(root, "config", "user.email", "test@example.com")
        self._git(root, "config", "user.name", "Harness Test")
        self._git(root, "checkout", "-b", "test-run")
        plan_path, run_path = self._write_fixture(root)
        self._git(root, "add", "docs/product", "PLAN.md", "RUN.md")
        self._git(root, "commit", "-qm", "fixture")
        self._bind_fixture_to_git(root, run_path)
        self._acquire_lock(plan_path, run_path)
        return plan_path, run_path

    def _write_fixture(self, root: Path) -> tuple[Path, Path]:
        """Persist the dispatchable preintegration review state under root."""
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

    def _bind_fixture_to_git(self, root: Path, run_path: Path) -> None:
        """Bind the review fixture to the real temporary checkout head."""
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

    def _acquire_lock(self, plan_path: Path, run_path: Path) -> None:
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
                        "review-triage-tests",
                        "acquire-run-lock",
                    ]
                ),
            )

    def _reserve(self, plan_path: Path, run_path: Path) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return harness_transition.main(
                [
                    "--plan",
                    str(plan_path),
                    "--run",
                    str(run_path),
                    "--session-id",
                    "review-triage-tests",
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
            )

    def _record(self, plan_path: Path, run_path: Path, *extra: str) -> list[str]:
        return [
            "--plan",
            str(plan_path),
            "--run",
            str(run_path),
            "--session-id",
            "review-triage-tests",
            "record-review-attempt",
            "--lineage",
            "REVIEW-N-FRONTEND-REVIEW",
            "--worker-id",
            "RW-REVIEW-1",
            "--attempt-id",
            "ATT-REVIEW-1",
            "--mission-id",
            "M1",
            *extra,
        ]

    def test_pass_with_notes_records_notes_without_findings(self) -> None:
        plan_path, run_path = self._prepare()
        self.assertEqual(0, self._reserve(plan_path, run_path))

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = harness_transition.main(
                self._record(
                    plan_path,
                    run_path,
                    "--result",
                    "pass",
                    "--evidence",
                    "reviewed the exact reserved head",
                    "--note",
                    "decorative banner copy could move to the backlog",
                    "--note",
                    "consider extracting the repeated table renderer",
                )
            )
        self.assertEqual(0, code)
        receipt = json.loads(stdout.getvalue())
        self.assertEqual("pass", receipt["result"])
        self.assertIs(False, receipt["refunded"])

        run = load_run(run_path)
        plan = load_plan(plan_path)
        worker = run["review_workers"][-1]
        self.assertEqual("worker_passed", worker["phase"])
        self.assertEqual("pass", worker["outcome"])
        self.assertEqual([], worker["findings"])
        self.assertEqual(
            [
                "decorative banner copy could move to the backlog",
                "consider extracting the repeated table renderer",
            ],
            worker["notes"],
        )
        attempt = run["attempt_log"][-1]
        self.assertEqual("ATT-REVIEW-1", attempt["attempt_id"])
        self.assertEqual("review", attempt["kind"])
        self.assertEqual("pass", attempt["result"])
        self.assertEqual(worker["notes"], attempt["notes"])
        self.assertNotIn("blocker_class", attempt)
        state = run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"]
        self.assertEqual("succeeded", state["phase"])
        self.assertEqual([], state["blockers"])
        self.assertEqual([], validate_run(plan, run))

    def test_notes_never_substitute_for_blocking_findings(self) -> None:
        plan_path, run_path = self._prepare()
        self.assertEqual(0, self._reserve(plan_path, run_path))
        before = run_path.read_text(encoding="utf-8")

        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = harness_transition.main(
                self._record(
                    plan_path,
                    run_path,
                    "--result",
                    "pass",
                    "--evidence",
                    "reviewed the exact reserved head",
                    "--finding",
                    "missing authorization check on the export route",
                )
            )
        self.assertEqual(2, code)
        self.assertIn("a PASS review cannot contain findings", stderr.getvalue())

        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            code = harness_transition.main(
                self._record(
                    plan_path,
                    run_path,
                    "--result",
                    "fix_required",
                    "--evidence",
                    "reviewed the exact reserved head",
                    "--note",
                    "decorative banner copy could move to the backlog",
                )
            )
        self.assertEqual(2, code)
        self.assertIn(
            "a non-pass review requires at least one --finding", stderr.getvalue()
        )
        self.assertEqual(before, run_path.read_text(encoding="utf-8"))

        with contextlib.redirect_stdout(io.StringIO()):
            code = harness_transition.main(
                self._record(
                    plan_path,
                    run_path,
                    "--result",
                    "fix_required",
                    "--evidence",
                    "reviewed the exact reserved head",
                    "--finding",
                    "missing authorization check on the export route",
                    "--note",
                    "decorative banner copy could move to the backlog",
                )
            )
        self.assertEqual(0, code)

        run = load_run(run_path)
        plan = load_plan(plan_path)
        worker = run["review_workers"][-1]
        self.assertEqual("worker_failed", worker["phase"])
        self.assertEqual(
            ["missing authorization check on the export route"], worker["findings"]
        )
        self.assertEqual(
            ["decorative banner copy could move to the backlog"], worker["notes"]
        )
        state = run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"]
        self.assertEqual("failed", state["phase"])
        self.assertEqual("fix_required", state["last_outcome"])
        # Only a blocked result fills node blockers; fix_required parks empty.
        self.assertEqual([], state["blockers"])
        self.assertEqual([], validate_run(plan, run))

    def test_ordinary_blocked_still_consumes_the_attempt(self) -> None:
        plan_path, run_path = self._prepare()
        self.assertEqual(0, self._reserve(plan_path, run_path))

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = harness_transition.main(
                self._record(
                    plan_path,
                    run_path,
                    "--result",
                    "blocked",
                    "--evidence",
                    "reviewer runtime stopped before inspection finished",
                    "--finding",
                    "review could not complete: reviewer runtime stopped",
                )
            )
        self.assertEqual(0, code)
        receipt = json.loads(stdout.getvalue())
        self.assertIs(False, receipt["refunded"])
        self.assertEqual("review", receipt["blocker_class"])

        run = load_run(run_path)
        plan = load_plan(plan_path)
        state = run["graph_state"]["node_states"]["N-FRONTEND-REVIEW"]
        self.assertEqual("blocked", state["phase"])
        self.assertEqual(1, state["attempts"])
        self.assertEqual("ATT-REVIEW-1", state["last_attempt_id"])
        self.assertEqual(
            ["review could not complete: reviewer runtime stopped"], state["blockers"]
        )
        worker = run["review_workers"][-1]
        self.assertEqual("blocked", worker["phase"])
        attempt = run["attempt_log"][-1]
        self.assertEqual("blocked", attempt["result"])
        self.assertEqual("review", attempt["blocker_class"])
        self.assertEqual([], validate_run(plan, run))

        selection = select_ready_nodes(plan, run)
        deferred = {
            item["node_id"]: item["reason_codes"] for item in selection["deferred_nodes"]
        }
        self.assertIn("node_phase_not_ready", deferred["N-FRONTEND-REVIEW"])
        self.assertNotIn("N-FRONTEND-REVIEW", {
            item["node_id"] for item in selection["dispatchable_nodes"]
        })


class EnvironmentRefundJourneyTests(unittest.TestCase):
    """Drive a real combined security review through environment refunds."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.container = Path(self.temp.name)
        self.root = self.container / "integration"
        self.root.mkdir()
        mf.init_repo(self.root, "README.md", default_branch="integration")
        self.plan = mf.conditional_final_candidate_plan()
        for mission in self.plan["missions"]:
            mission["tasks"] = mission["tasks"][:1]
            task = mission["tasks"][0]
            for declaration in [
                *task["verifiers"],
                *mission["worker_verifiers"],
                *mission["integration_verifiers"],
            ]:
                declaration.update(
                    argv=[
                        sys.executable,
                        "-c",
                        "from pathlib import Path; assert Path('"
                        + task["write_scope"][0]
                        + "').is_file()",
                    ],
                    read_only=True,
                )
        mf.materialize_plan_sources(self.root, self.plan)
        mf.git(self.root, "add", "docs/product")
        mf.git(self.root, "commit", "-qm", "freeze approved sources")
        self.run = mf.valid_run(self.plan)
        mission_ids = [mission["id"] for mission in self.plan["missions"]]
        mf.authorize_execution(self.run, mission_ids)
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
            "integrate_locally",
        ):
            mf.authorize_action(
                self.run,
                action,
                mission_ids,
                ["*", "branch:integration"] if action == "integrate_locally" else ["*"],
            )
        runtime = self.run["runtime_capabilities"]
        runtime.update(worker_runtime="subagent", max_parallel_workers=1)
        runtime["runtime_adapter"].update(
            available_drivers=["subagents", "sequential_parent"],
            detection_source="observed",
        )
        self.run["integration"].update(
            branch="integration", batch_base_sha=None, integration_head_sha=None
        )
        self.run["landing"]["continuity"]["branch_ref"] = "refs/heads/integration"
        self.run["active_wave"].update(
            wave_id=None, status="idle", selected_missions=[], batch_base_sha=None
        )
        self.run["observed"]["captured_at"] = None
        self.run["observed"]["runtime"].update(
            available_worker_slots=1, isolation_capacity=1
        )

    def observe(self) -> None:
        harness_transition._record_observation(
            self.plan, self.run, Namespace(repo_root=self.root)
        )

    def integrate(self, mission_id: str) -> None:
        self.observe()
        base = mf.git(self.root, "rev-parse", "HEAD")
        harness_transition._accept_wave(
            self.plan,
            self.run,
            Namespace(
                wave_id="WAVE-" + mission_id,
                mission_id=[mission_id],
                batch_base_sha=base,
                repo_root=self.root,
            ),
        )
        checkout = self.container / mission_id
        branch = "worker-" + mission_id
        mf.git(self.root, "worktree", "add", "-qb", branch, str(checkout), base)
        lease, attempt, worker = (
            "L-" + mission_id,
            "A-" + mission_id,
            "W-" + mission_id,
        )
        harness_transition._lease_worker(
            self.plan,
            self.run,
            Namespace(
                mission_id=mission_id,
                node_id="N-" + mission_id,
                worker_id=worker,
                lease_id=lease,
                attempt_id=attempt,
                branch_ref="refs/heads/" + branch,
                worktree_path=checkout.as_posix(),
                report_path=None,
            ),
        )
        mission = next(
            item for item in self.plan["missions"] if item["id"] == mission_id
        )
        task = mission["tasks"][0]
        relative = task["write_scope"][0]
        source = checkout / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("VALUE = 1\n", encoding="utf-8")
        mf.git(checkout, "add", relative)
        mf.git(checkout, "commit", "-qm", "implement " + mission_id)
        head = mf.git(checkout, "rev-parse", "HEAD")
        declaration = task["verifiers"][0]
        preflights, errors = observe_plan_host_runtimes(
            {"final_gates": [declaration]}, checkout
        )
        self.assertEqual([], errors)
        context = {
            "run_id": self.run["run_id"],
            "plan_revision": self.plan["revision"],
            "plan_digest_sha256": plan_digest(self.plan),
            "graph_revision": self.run["graph_state"]["graph_revision"],
            "batch_base_sha": base,
            "head_sha": head,
            "changed_files": [relative],
            "trust_domain": "parent_local",
            "checkout_role": "worker",
            "checkout_dirty": False,
            "cache_safe": False,
            "layer": "task",
            "mission_id": mission_id,
            "task_id": task["id"],
            "attempt_id": "CHECK-" + mission_id,
            "lease_id": lease,
        }
        execution = run_verifier(
            declaration,
            context,
            checkout_root=checkout,
            timeout_seconds=15,
            host_preflight=preflights[0],
            git_guard={
                "expected_branch": branch,
                "expected_head_sha": head,
                "ignored_paths": [],
            },
        )
        self.assertEqual("PASS", execution["status"], execution["stderr"])
        worker_context = {
            **context,
            "layer": "worker",
            "task_id": None,
            "attempt_id": "WORKER-CHECK-" + mission_id,
        }
        worker_declaration = mission["worker_verifiers"][0]
        worker_execution = run_verifier(
            worker_declaration,
            worker_context,
            checkout_root=checkout,
            timeout_seconds=15,
            host_preflight=preflights[0],
            git_guard={
                "expected_branch": branch,
                "expected_head_sha": head,
                "ignored_paths": [],
            },
        )
        self.assertEqual("PASS", worker_execution["status"], worker_execution["stderr"])
        result = {
            "type": "WORKER_RESULT",
            "run_id": self.run["run_id"],
            "plan_id": self.plan["plan_id"],
            "mission_id": mission_id,
            "lease_id": lease,
            "status": "worker_passed",
            "current_task_id": None,
            "plan_revision": self.plan["revision"],
            "plan_digest_sha256": plan_digest(self.plan),
            "base_sha": base,
            "head_sha": head,
            "diff_summary": "Implement the assigned file.",
            "changed_files": [relative],
            "commits": [head],
            "evidence_paths": [],
            "blockers": [],
            "residual_risks": [],
            "integration_notes": "",
            "task_results": [
                {
                    "task_id": task["id"],
                    "status": "worker_passed",
                    "head_sha": head,
                    "verifier_ids": [declaration["id"]],
                    "commits": [head],
                    "evidence_paths": [],
                }
            ],
            "verifiers": [
                {
                    "id": item["verifier_id"],
                    "status": "PASS",
                    "evidence": item["execution_key"],
                }
                for item in (execution, worker_execution)
            ],
        }
        node_result = {
            "run_id": self.run["run_id"],
            "plan_id": self.plan["plan_id"],
            "node_id": "N-" + mission_id,
            "attempt_id": attempt,
            "plan_revision": self.plan["revision"],
            "plan_digest_sha256": plan_digest(self.plan),
            "graph_revision": context["graph_revision"],
            "batch_base_sha": base,
            "status": "succeeded",
            "outcome": "pass",
            "worker_result": result,
            "refinement_request": None,
            "evidence_paths": [],
        }
        node_path = self.container / (mission_id + ".json")
        verifier_path = self.container / (mission_id + "-execution.json")
        node_path.write_text(
            json.dumps({"node_result": node_result}), encoding="utf-8"
        )
        verifier_path.write_text(json.dumps(execution), encoding="utf-8")
        worker_verifier_path = self.container / (
            mission_id + "-worker-execution.json"
        )
        worker_verifier_path.write_text(
            json.dumps(worker_execution), encoding="utf-8"
        )
        self.observe()
        record_worker_result(
            self.plan,
            self.run,
            Namespace(
                repo_root=self.root,
                node_result=node_path,
                worker_result=None,
                verifier_result=[verifier_path, worker_verifier_path],
            ),
        )
        self.assertEqual(
            "worker_passed",
            self.run["mission_states"][mission_id]["phase"],
            self.run["mission_states"][mission_id],
        )
        mf.git(self.root, "merge", "--ff-only", branch)
        self.observe()
        integration_context = {
            **context,
            "layer": "mission_integration",
            "checkout_role": "integration",
            "task_id": None,
            "attempt_id": None,
            "lease_id": None,
        }
        integration_execution = run_verifier(
            mission["integration_verifiers"][0],
            integration_context,
            checkout_root=self.root,
            timeout_seconds=15,
            host_preflight=preflights[0],
            git_guard={
                "expected_branch": "integration",
                "expected_head_sha": head,
                "ignored_paths": sorted(
                    harness_transition._coordination_ignored_paths(
                        self.root, None, self.run
                    )
                ),
            },
        )
        self.assertEqual(
            "PASS", integration_execution["status"], integration_execution["stderr"]
        )
        integration_path = self.container / (
            mission_id + "-integration-execution.json"
        )
        integration_path.write_text(
            json.dumps(integration_execution), encoding="utf-8"
        )
        harness_transition._record_integration(
            self.plan,
            self.run,
            Namespace(
                mission_id=mission_id,
                integrated_sha=head,
                repo_root=self.root,
                verifier_result=[integration_path],
            ),
        )
        harness_transition._close_wave(
            self.run, Namespace(source="test integration finished")
        )

    def reserve_review(self, index: int) -> None:
        harness_transition._reserve_review_dispatch(
            self.plan,
            self.run,
            Namespace(
                node_id="N-FINAL-REVIEW",
                worker_id="RW-ENV-" + str(index),
                attempt_id="RA-ENV-" + str(index),
                report_path=None,
            ),
            repo_root=self.root,
        )

    def record_environment_block(self, index: int, note: list[str] | None = None):
        return harness_transition._record_review_attempt(
            self.plan,
            self.run,
            Namespace(
                lineage="REVIEW-FINAL",
                attempt_id="RA-ENV-" + str(index),
                worker_id="RW-ENV-" + str(index),
                result="blocked",
                blocker_class="environment",
                security_result=None,
                finding=[
                    f"reviewer sandbox denied git status before inspection ({index})"
                ],
                evidence=[
                    f"reviewer runtime never inspected the candidate ({index})"
                ],
                repo_root=self.root,
                mission_id=None,
                note=note or [],
                tree_sha=None,
            ),
        )

    @property
    def review_state(self) -> dict:
        return self.run["graph_state"]["node_states"]["N-FINAL-REVIEW"]

    def test_environment_block_refunds_and_rearms_the_review(self) -> None:
        for mission in ("M1", "M3", "M2"):
            self.integrate(mission)
        self.reserve_review(1)
        self.assertEqual("running", self.review_state["phase"])
        self.assertEqual(1, self.review_state["attempts"])

        receipt = self.record_environment_block(
            1, note=["host sandbox blocked every repository read"]
        )

        self.assertTrue(receipt["refunded"], receipt)
        self.assertEqual("environment", receipt["blocker_class"])
        self.assertNotIn("message", receipt)

        self.assertEqual("dormant", self.review_state["phase"])
        self.assertEqual(0, self.review_state["attempts"])
        self.assertIsNone(self.review_state["last_attempt_id"])
        self.assertIsNone(self.review_state["last_outcome"])
        self.assertIsNone(self.review_state["bound_worker_id"])
        self.assertEqual([], self.review_state["blockers"])

        worker = self.run["review_workers"][-1]
        self.assertEqual("blocked", worker["phase"])
        self.assertEqual("blocked", worker["outcome"])
        self.assertEqual(
            ["reviewer sandbox denied git status before inspection (1)"],
            worker["findings"],
        )
        self.assertEqual(
            ["host sandbox blocked every repository read"], worker["notes"]
        )
        self.assertNotIn("security_result", worker)

        attempt = self.run["attempt_log"][-1]
        self.assertEqual("review", attempt["kind"])
        self.assertEqual("blocked", attempt["result"])
        self.assertEqual("environment", attempt["blocker_class"])
        self.assertEqual(
            ["host sandbox blocked every repository read"], attempt["notes"]
        )
        self.assertEqual([], validate_run(self.plan, self.run))

        selection = select_ready_nodes(self.plan, self.run, repo_root=self.root)
        deferred = {
            item["node_id"]: item["reason_codes"] for item in selection["deferred_nodes"]
        }
        self.assertIn(
            "N-FINAL-REVIEW",
            [item["node_id"] for item in selection["dispatchable_nodes"]],
        )
        self.assertNotIn(
            "attempts_exhausted", deferred.get("N-FINAL-REVIEW", [])
        )
        self.assertNotIn(
            "node_phase_not_ready", deferred.get("N-FINAL-REVIEW", [])
        )

        self.reserve_review(2)
        self.assertEqual(1, self.review_state["attempts"])
        self.assertEqual("running", self.review_state["phase"])
        self.assertEqual([], validate_run(self.plan, self.run))

    def test_environment_refund_stops_at_two_per_node(self) -> None:
        for mission in ("M1", "M3", "M2"):
            self.integrate(mission)
        for index in (1, 2):
            self.reserve_review(index)
            receipt = self.record_environment_block(index)
            self.assertTrue(receipt["refunded"], receipt)
            self.assertEqual("dormant", self.review_state["phase"])
            self.assertEqual(0, self.review_state["attempts"])

        self.reserve_review(3)
        receipt = self.record_environment_block(3)

        self.assertFalse(receipt["refunded"], receipt)
        self.assertEqual("environment refund cap reached", receipt["message"])
        self.assertEqual("blocked", self.review_state["phase"])
        self.assertEqual(1, self.review_state["attempts"])
        self.assertEqual("RA-ENV-3", self.review_state["last_attempt_id"])
        self.assertEqual("blocked", self.review_state["last_outcome"])
        self.assertEqual(
            ["reviewer sandbox denied git status before inspection (3)"],
            self.review_state["blockers"],
        )
        worker = self.run["review_workers"][-1]
        self.assertEqual("blocked", worker["phase"])
        self.assertEqual(
            3,
            sum(
                1
                for item in self.run["attempt_log"]
                if item.get("blocker_class") == "environment"
            ),
        )
        self.assertEqual([], validate_run(self.plan, self.run))
        selection = select_ready_nodes(self.plan, self.run, repo_root=self.root)
        deferred = {
            item["node_id"]: item["reason_codes"] for item in selection["deferred_nodes"]
        }
        self.assertIn("node_phase_not_ready", deferred.get("N-FINAL-REVIEW", []))


if __name__ == "__main__":
    unittest.main()

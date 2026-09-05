#!/usr/bin/env python3
"""The close-wave lifecycle and the tightened write-path guards."""

from __future__ import annotations

import hashlib
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
from harness_authorization import execution_covers  # noqa: E402
from harness_core import ManifestError  # noqa: E402
import manifest_fixtures as mf  # noqa: E402


SESSION = "close-wave-tests"


def make_repo() -> tuple[tempfile.TemporaryDirectory, Path, str, str]:
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    mf.git(root, "init", "-q", "-b", "integration")
    mf.git(root, "config", "user.email", "t@example.com")
    mf.git(root, "config", "user.name", "T")
    (root / "file.txt").write_text("base\n", encoding="utf-8")
    mf.git(root, "add", ".")
    mf.git(root, "commit", "-qm", "base")
    base = mf.git(root, "rev-parse", "HEAD")
    (root / "file.txt").write_text("integrated\n", encoding="utf-8")
    mf.git(root, "add", ".")
    mf.git(root, "commit", "-qm", "work")
    head = mf.git(root, "rev-parse", "HEAD")
    return temp, root, base, head


def load_run_block(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    start = text.find("```json\n") + len("```json\n")
    end = text.find("\n```", start)
    return json.loads(text[start:end])["harness_run"]


def save_run_block(path: Path, run: dict) -> None:
    text = path.read_text(encoding="utf-8")
    start = text.find("```json\n")
    end = text.find("\n```", start)
    body = json.dumps({"harness_run": run}, indent=2, ensure_ascii=False)
    path.write_text(text[: start + len("```json\n")] + body + text[end:], encoding="utf-8")


class CloseWaveCliTests(unittest.TestCase):
    """Drive the real CLI main() across the full write path, then close."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        self.gitroot = self.root / "git"
        (self.gitroot / "docs" / "product").mkdir(parents=True)
        prd = self.gitroot / "docs" / "product" / "prd.md"
        arch = self.gitroot / "docs" / "product" / "architecture.md"
        prd.write_text("product contract\n", encoding="utf-8")
        arch.write_text("technical contract\n", encoding="utf-8")
        self.base = mf.init_repo(self.gitroot, "file.txt")
        mf.git(self.gitroot, "checkout", "-qb", "integration")
        (self.gitroot / "file.txt").write_text("work\n", encoding="utf-8")
        mf.git(self.gitroot, "add", ".")
        mf.git(self.gitroot, "commit", "-qm", "work")
        self.head = mf.git(self.gitroot, "rev-parse", "HEAD")
        self.wt1 = (self.root / "wt-m1").as_posix()

        self.plan = mf.valid_plan()
        self.plan["sources"][0]["content_sha256"] = hashlib.sha256(
            prd.read_bytes()
        ).hexdigest()
        self.plan["sources"][1]["content_sha256"] = hashlib.sha256(
            arch.read_bytes()
        ).hexdigest()
        run = mf.valid_run(self.plan)
        mf.authorize_execution(run, ["M1", "M2"])
        mf.authorize_action(
            run, "spawn_subagents", ["M1", "M2"],
            ["*", "worker:W-M1-A", "worker:RW-1"],
        )
        mf.authorize_action(
            run,
            "create_local_worktrees",
            ["M1", "M2"],
            ["*", f"worktree:{self.wt1}"],
        )
        mf.authorize_action(
            run,
            "create_local_branches",
            ["M1", "M2"],
            ["*", "branch:refs/heads/wt/m1"],
        )
        mf.authorize_action(
            run,
            "create_local_commits",
            ["M1", "M2"],
            ["*", "branch:refs/heads/wt/m1"],
        )
        mf.authorize_action(
            run, "integrate_locally", ["M1"], ["branch:integration"]
        )
        run["integration"]["branch"] = "integration"
        run["integration"]["integration_head_sha"] = None
        run["landing"]["continuity"]["branch_ref"] = "refs/heads/integration"
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter["available_drivers"] = ["sequential_parent", "subagents"]
        run["runtime_capabilities"]["worker_runtime"] = "subagent"
        run["runtime_capabilities"]["max_parallel_workers"] = 2
        self.plan_path = self.root / "PLAN.md"
        self.run_path = self.root / "RUN.md"
        self.plan_path.write_text(
            mf.manifest_markdown(
                "## Harness Plan Manifest", "harness_plan", self.plan
            ),
            encoding="utf-8",
        )
        self.run_path.write_text(
            mf.manifest_markdown("## Harness Run State", "harness_run", run),
            encoding="utf-8",
        )
        self.cli("--session-id", SESSION, "acquire-run-lock")
        self.cli("--repo-root", str(self.gitroot), "record-observation")

    def tearDown(self) -> None:
        self._temp.cleanup()

    def cli(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "harness_transition.py"),
                "--plan",
                str(self.plan_path),
                "--run",
                str(self.run_path),
                "--session-id",
                SESSION,
                *extra,
            ],
            capture_output=True,
            text=True,
        )

    def _prepare_worker_worktree(self) -> None:
        # Worktrees are created only after the selector-bound wave is accepted.
        # Re-observe before leasing so the concrete worker binding is present.
        if not Path(self.wt1).exists():
            mf.git(
                self.gitroot,
                "worktree",
                "add",
                "-b",
                "wt/m1",
                self.wt1,
                self.head,
            )
        result = self.cli(
            "--repo-root", str(self.gitroot), "record-observation"
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def _integrate_m1(self) -> None:
        result = self.cli(
            "--repo-root", str(self.gitroot),
            "accept-wave", "--wave-id", "W-1", "--mission-id", "M1",
            "--batch-base-sha", self.head,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self._prepare_worker_worktree()
        result = self.cli(
            "lease-worker",
            "--mission-id", "M1", "--node-id", "N-M1",
            "--worker-id", "W-M1-A", "--lease-id", "L-M1",
            "--attempt-id", "A-M1", "--branch-ref", "refs/heads/wt/m1",
            "--worktree-path", self.wt1,
            "--provider", "codex", "--driver", "subagents",
        )
        self.assertEqual(0, result.returncode, result.stderr)

        live = load_run_block(self.run_path)
        live["mission_states"]["M1"].update(
            {"phase": "worker_passed", "head_sha": self.head}
        )
        worker = next(w for w in live["workers"] if w["worker_id"] == "W-M1-A")
        worker.update({"phase": "worker_passed", "worker_head_sha": self.head})
        live["attempt_log"].append(
            {
                "attempt_id": "A-M1-RESULT",
                "mission_id": "M1",
                "task_id": None,
                "lease_id": "L-M1",
                "kind": "worker",
                "result": "pass",
                "evidence": ["worker passed"],
                "review_lineage_id": None,
                "failure_family_ids": [],
            }
        )
        live["verifier_executions"] = [
            mf.retained_gate_execution(
                self.plan, live, self.plan["missions"][0]["worker_verifiers"][0],
                layer="worker", execution_id="EXEC-W-M1", mission_id="M1",
                attempt_id="A-M1-RESULT", lease_id="L-M1", head_sha=self.head,
                checkout_role="worker",
            ),
            mf.retained_gate_execution(
                self.plan, live, self.plan["missions"][0]["integration_verifiers"][0],
                layer="mission_integration", execution_id="EXEC-I-M1",
                mission_id="M1", attempt_id=None, lease_id=None,
                head_sha=self.head,
            ),
        ]
        save_run_block(self.run_path, live)

        result = self.cli(
            "--repo-root", str(self.gitroot),
            "reserve-review-dispatch", "--node-id", "N-REVIEW-M1",
            "--worker-id", "RW-1", "--attempt-id", "RA-1",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        result = self.cli(
            "record-review-attempt", "--lineage", "REVIEW-M1",
            "--attempt-id", "RA-1", "--worker-id", "RW-1",
            "--mission-id", "M1", "--result", "pass", "--evidence", "reviewed",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        result = self.cli(
            "--repo-root", str(self.gitroot),
            "record-integration", "--mission-id", "M1",
            "--integrated-sha", self.head,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_close_wave_then_accept_the_next_wave(self) -> None:
        self._integrate_m1()
        result = self.cli("close-wave", "--source", "wave W-1 fully resolved")
        self.assertEqual(0, result.returncode, result.stderr)
        live = load_run_block(self.run_path)
        self.assertEqual("closed", live["active_wave"]["status"])
        self.assertEqual(
            [{"wave_id": "W-1", "batch_base_sha": self.head}],
            live["closed_waves"],
        )
        self.assertTrue(
            any(a["kind"] == "wave_close" for a in live["attempt_log"])
        )
        # The next wave may open on a fresh identity with the tombstone kept.
        result = self.cli(
            "--repo-root", str(self.gitroot),
            "accept-wave", "--wave-id", "W-2", "--mission-id", "M2",
            "--batch-base-sha", self.head,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        live = load_run_block(self.run_path)
        self.assertEqual("active", live["active_wave"]["status"])
        self.assertEqual(["M2"], live["active_wave"]["selected_missions"])
        self.assertEqual(1, len(live["closed_waves"]))

    def test_worker_passed_mission_closes_under_a_run_complete_boundary(self) -> None:
        self._integrate_m1()
        live = load_run_block(self.run_path)
        # Rewind M1 to worker_passed: its result is validated and the
        # execution grant is run_complete-bounded, so the wave may close with
        # integration still owed.
        live["mission_states"]["M1"]["phase"] = "worker_passed"
        live["mission_states"]["M1"]["integration_gate"] = "planned"
        live["mission_states"]["M1"]["integrated_sha"] = None
        live["integration"]["integration_head_sha"] = None
        live["graph_state"]["node_states"]["N-M1"]["phase"] = "running"
        live["graph_state"]["node_states"]["N-M1"]["last_outcome"] = None
        save_run_block(self.run_path, live)
        result = self.cli("close-wave", "--source", "results validated")
        self.assertEqual(0, result.returncode, result.stderr)
        live = load_run_block(self.run_path)
        self.assertEqual("closed", live["active_wave"]["status"])
        self.assertEqual("worker_passed", live["mission_states"]["M1"]["phase"])
        self.assertTrue(live["execution_authorized"])

    def test_close_wave_refuses_then_recovers_after_reconcile(self) -> None:
        result = self.cli(
            "--repo-root", str(self.gitroot),
            "accept-wave", "--wave-id", "W-1", "--mission-id", "M1",
            "--batch-base-sha", self.head,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self._prepare_worker_worktree()
        result = self.cli(
            "lease-worker",
            "--mission-id", "M1", "--node-id", "N-M1",
            "--worker-id", "W-M1-A", "--lease-id", "L-M1",
            "--attempt-id", "A-M1", "--branch-ref", "refs/heads/wt/m1",
            "--worktree-path", self.wt1,
            "--provider", "codex", "--driver", "subagents",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        result = self.cli("close-wave", "--source", "premature")
        self.assertEqual(2, result.returncode)
        self.assertIn("live workers", result.stderr)
        # Reconciling the interrupted worker resolves the mission to blocked,
        # which is a closeable terminal state: the wave closes and a fresh
        # wave may then re-select the mission.
        self.assertEqual(
            0,
            self.cli(
                "reconcile-interrupted", "--worker-id", "W-M1-A",
                "--reason", "interrupted",
            ).returncode,
        )
        result = self.cli("close-wave", "--source", "recovered after reconcile")
        self.assertEqual(0, result.returncode, result.stderr)
        live = load_run_block(self.run_path)
        self.assertEqual("closed", live["active_wave"]["status"])
        self.assertEqual(
            "blocked", live["mission_states"]["M1"]["phase"]
        )
        result = self.cli(
            "--repo-root", str(self.gitroot),
            "accept-wave", "--wave-id", "W-2", "--mission-id", "M1",
            "--batch-base-sha", self.head,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_dispatch_requires_this_sessions_lock(self) -> None:
        result = self.cli(
            "--repo-root", str(self.gitroot),
            "accept-wave", "--wave-id", "W-1", "--mission-id", "M1",
            "--batch-base-sha", self.head,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        # A second session takes over the stale lock through the watchdog and
        # must not be silently blocked; but a *fresh* foreign lock blocks any
        # mutation, and dispatch refuses outright without a held lock.
        live = load_run_block(self.run_path)
        live["run_lock"]["session_id"] = "OTHER"
        live["run_lock"]["heartbeat_at"] = "2020-01-01T00:00:00Z"
        save_run_block(self.run_path, live)
        result = subprocess.run(
            [
                sys.executable, str(SCRIPTS_DIR / "harness_transition.py"),
                "--plan", str(self.plan_path), "--run", str(self.run_path),
                "pause", "--source", "x",
            ],
            capture_output=True, text=True,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("run lock is held by session 'OTHER'", result.stderr)
        # Restore our own lock, release it, and dispatch must then refuse:
        # the write path is single-writer and requires a held lock.
        live = load_run_block(self.run_path)
        live["run_lock"] = {
            "session_id": SESSION,
            "acquired_at": "2026-01-01T00:00:00Z",
            "heartbeat_at": "2026-01-01T00:00:00Z",
        }
        save_run_block(self.run_path, live)
        self.assertEqual(
            0, self.cli("release-run-lock").returncode
        )
        result = self.cli(
            "--repo-root", str(self.gitroot),
            "accept-wave", "--wave-id", "W-9", "--mission-id", "M2",
            "--batch-base-sha", self.head,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("requires this session's run lock", result.stderr)


class AcceptWaveGuardTests(unittest.TestCase):
    """accept-wave refuses an unauthorized, unready, or unobserved RUN."""

    def setUp(self) -> None:
        self._temp, self.root, _, self.head = make_repo()
        self.plan = mf.valid_plan()
        for source, contents in zip(
            self.plan["sources"],
            (b"product contract\n", b"technical contract\n"),
        ):
            source_path = self.root / source["location"]
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_bytes(contents)
            source["content_sha256"] = hashlib.sha256(contents).hexdigest()
        mf.git(self.root, "add", "docs/product")
        mf.git(self.root, "commit", "-qm", "frozen contracts")
        self.head = mf.git(self.root, "rev-parse", "HEAD")
        self.run = mf.valid_run(self.plan)
        self.run["integration"].update(
            {
                "branch": "integration",
                "batch_base_sha": self.head,
                "integration_head_sha": None,
            }
        )
        self.run["landing"]["continuity"] = {
            "status": "planned",
            "branch_ref": "refs/heads/integration",
            "head_sha": None,
            "reason": None,
        }
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            mf.authorize_action(self.run, action, ["M1", "M2"], ["*"])
        adapter = self.run["runtime_capabilities"]["runtime_adapter"]
        adapter.update(
            {
                "available_drivers": ["subagents", "sequential_parent"],
                "detection_source": "observed",
                "capability_probe": mf.codex_capability_probe(subagents=True),
                "version_gate": mf.current_version_gate(),
            }
        )
        self.run["runtime_capabilities"].update(
            {"worker_runtime": "subagent", "max_parallel_workers": 2}
        )
        self.run["observed"]["runtime"].update(
            {
                "available_worker_slots": 2,
                "isolation_capacity": 2,
                "completion_channel_available": True,
            }
        )
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        self.args = dict(
            wave_id="W-1",
            mission_id=["M1"],
            batch_base_sha=self.head,
            repo_root=self.root,
        )

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_unauthorized_draft_paused_or_unbound_run_is_refused(self) -> None:
        run = self.run
        for field, value in (
            ("execution_authorized", False),
            ("status", "draft"),
            ("plan_readiness", "draft"),
        ):
            original = run[field]
            run[field] = value
            with self.assertRaises(ManifestError):
                harness_transition._accept_wave(
                    self.plan, run, Namespace(**self.args)
                )
            run[field] = original
        run["observed"]["captured_at"] = None
        with self.assertRaises(ManifestError):
            harness_transition._accept_wave(self.plan, run, Namespace(**self.args))
        # A paused or cancelled run accepts no wave.
        mf.authorize_execution(run, ["M1"])
        run["observed"]["captured_at"] = "2026-01-01T00:00:00Z"
        run["observed"]["git"]["parent_head_sha"] = self.head
        run["control"]["desired_state"] = "paused"
        with self.assertRaises(ManifestError) as caught:
            harness_transition._accept_wave(self.plan, run, Namespace(**self.args))
        self.assertIn("paused or cancelled", str(caught.exception))
        run["control"]["desired_state"] = "running"
        # The base must be the observed parent head, not any well-formed SHA.
        with self.assertRaises(ManifestError) as caught:
            harness_transition._accept_wave(
                self.plan, run, Namespace(**{**self.args, "batch_base_sha": "c" * 40})
            )
        self.assertIn("does not match the observed parent head", str(caught.exception))
        harness_transition._accept_wave(self.plan, run, Namespace(**self.args))

    def test_authorized_but_uncovered_mission_is_refused(self) -> None:
        mf.authorize_execution(self.run, ["M2"])
        self.run["observed"]["captured_at"] = "2026-01-01T00:00:00Z"
        with self.assertRaises(ManifestError):
            harness_transition._accept_wave(
                self.plan, self.run, Namespace(**self.args)
            )
        self.assertFalse(execution_covers(self.run, "M1"))


class LeaseWorkerGuardTests(unittest.TestCase):
    """lease-worker binds the mission's own node on a satisfied frontier."""

    def setUp(self) -> None:
        self.plan = mf.valid_plan()
        self.run = mf.valid_run(self.plan)
        mf.authorize_execution(self.run, ["M1", "M2"])
        self.run["active_wave"].update(
            {
                "wave_id": "W-1",
                "status": "active",
                "batch_base_sha": "a" * 40,
                "selected_missions": ["M1", "M2"],
            }
        )

    def lease(self, mission_id: str, node_id: str) -> None:
        harness_transition._lease_worker(
            self.plan,
            self.run,
            Namespace(
                mission_id=mission_id,
                node_id=node_id,
                worker_id=f"W-{mission_id}",
                lease_id=f"L-{mission_id}",
                attempt_id=f"A-{mission_id}",
                branch_ref=f"wt/{mission_id.lower()}",
                worktree_path=f"/tmp/{mission_id}",
                provider="codex",
                driver="subagents",
                worker_runtime="subagent",
                workspace_mode="parent_managed_worktree",
                completion_channel="agent_result",
            ),
        )

    def test_m2_is_refused_while_m1_is_unfinished(self) -> None:
        with self.assertRaises(ManifestError) as caught:
            self.lease("M2", "N-M2")
        self.assertIn("dependency", str(caught.exception))

    def test_foreign_node_is_refused(self) -> None:
        with self.assertRaises(ManifestError) as caught:
            self.lease("M1", "N-REVIEW-M1")
        self.assertIn("is not mission", str(caught.exception))

    def test_m1_leases_and_unblocks_m2(self) -> None:
        self.lease("M1", "N-M1")
        self.assertEqual(
            "worker_running", self.run["mission_states"]["M1"]["phase"]
        )
        with self.assertRaises(ManifestError):
            # M1 is leased but not integrated: the frontier still blocks M2.
            self.lease("M2", "N-M2")
        self.run["mission_states"]["M1"]["phase"] = "integrated"
        self.run["graph_state"]["node_states"]["N-M1"].update(
            {"phase": "succeeded", "last_outcome": "pass"}
        )
        self.lease("M2", "N-M2")
        self.assertEqual(
            "worker_running", self.run["mission_states"]["M2"]["phase"]
        )

    def test_conflicting_parallel_mission_is_refused(self) -> None:
        # Break the M1 -> M2 dependency so both are frontier-ready, then make
        # them compete for the same exclusive runtime resource.
        for mission in self.plan["missions"]:
            if mission["id"] == "M2":
                mission.pop("depends_on", None)
                mission["runtime_resources"] = [
                    {"key": "port:3000", "access": "exclusive"}
                ]
        self.plan["graph"]["edges"] = [
            edge
            for edge in self.plan["graph"]["edges"]
            if edge["id"] != "E-M1-M2"
        ]
        self.plan["graph"]["entry_nodes"] = ["N-M1", "N-M2"]
        self.lease("M1", "N-M1")
        with self.assertRaises(ManifestError) as caught:
            self.lease("M2", "N-M2")
        self.assertIn("conflicts with active mission", str(caught.exception))


class RecordIntegrationGuardTests(unittest.TestCase):
    """record-integration proves the SHA, branch, and tree against live Git."""

    def setUp(self) -> None:
        self._temp, self.root, self.base, self.head = make_repo()
        self.plan = mf.valid_plan()
        self.run = mf.valid_run(self.plan)
        mf.authorize_execution(self.run, ["M1"])
        self.run["integration"]["branch"] = "integration"
        self.run["integration"]["batch_base_sha"] = self.base
        self.run["integration"]["integration_head_sha"] = self.base
        self.run["observed"]["git"].update(
            {
                "parent_worktree_path": str(self.root),
                "parent_branch": "integration",
                "parent_head_sha": self.head,
                "parent_dirty": False,
            }
        )
        self.run["mission_states"]["M1"].update(
            {"phase": "worker_passed", "head_sha": self.head}
        )
        self.args = dict(mission_id="M1", integrated_sha=self.head)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def record(self, **overrides: object) -> None:
        harness_transition._record_integration(
            self.plan,
            self.run,
            Namespace(
                repo_root=self.root,
                **{**self.args, **overrides},
            ),
        )

    def test_missing_repo_root_is_refused(self) -> None:
        with self.assertRaises(ManifestError) as caught:
            harness_transition._record_integration(
                self.plan, self.run, Namespace(repo_root=None, **self.args)
            )
        self.assertIn("--repo-root", str(caught.exception))

    def test_wrong_branch_is_refused(self) -> None:
        mf.git(self.root, "checkout", "-q", "-b", "elsewhere")
        with self.assertRaises(ManifestError) as caught:
            self.record()
        self.assertIn("not the integration branch", str(caught.exception))

    def test_dirty_tree_is_refused(self) -> None:
        (self.root / "scratch.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaises(ManifestError) as caught:
            self.record()
        self.assertIn("dirty", str(caught.exception))

    def test_worker_head_outside_the_integration_is_refused(self) -> None:
        with self.assertRaises(ManifestError) as caught:
            self.record(integrated_sha=self.base)
        self.assertIn("is not contained in", str(caught.exception))

    def test_fabricated_batch_base_is_refused(self) -> None:
        self.run["integration"]["batch_base_sha"] = "f" * 40
        with self.assertRaises(ManifestError) as caught:
            self.record()
        self.assertIn("is not an ancestor of", str(caught.exception))

    def test_head_mismatch_is_refused(self) -> None:
        self.run["mission_states"]["M1"]["head_sha"] = self.base
        with self.assertRaises(ManifestError) as caught:
            self.record(integrated_sha=self.base)
        self.assertIn("HEAD", str(caught.exception))

    def test_prior_integration_head_on_another_branch_is_refused(self) -> None:
        mf.git(self.root, "checkout", "-q", "-b", "prior", self.base)
        (self.root / "prior.txt").write_text("prior\n", encoding="utf-8")
        mf.git(self.root, "add", "prior.txt")
        mf.git(self.root, "commit", "-qm", "prior integration")
        prior = mf.git(self.root, "rev-parse", "HEAD")
        mf.git(self.root, "checkout", "-q", "integration")
        self.run["integration"]["integration_head_sha"] = prior

        with self.assertRaisesRegex(ManifestError, "may only move forward"):
            self.record()


class CloseWaveUnitTests(unittest.TestCase):
    """close-wave resets wave-bounded grants and keeps run_complete ones."""

    def setUp(self) -> None:
        self.plan = mf.valid_plan()
        self.run = mf.valid_run(self.plan)
        mf.authorize_execution(self.run, ["M1"])
        base = "a" * 40
        self.run["active_wave"].update(
            {
                "wave_id": "W-1",
                "status": "active",
                "batch_base_sha": base,
                "selected_missions": ["M1"],
            }
        )
        self.run["mission_states"]["M1"]["phase"] = "integrated"
        self.run["authorizations"]["create_local_commits"] = {
            "authorized": True,
            "source": "user granted the wave",
            "scope": {
                "run_id": self.run["run_id"],
                "plan_revision": self.run["plan"]["revision"],
                "plan_digest_sha256": self.run["plan"]["digest_sha256"],
                "mission_ids": ["M1"],
                "targets": ["branch:refs/heads/wt/m1"],
                "wave_id": "W-1",
                "batch_base_sha": base,
            },
            "expires_when": "wave_closed",
        }
        self.base = base

    def close(self) -> None:
        harness_transition._close_wave(
            self.run, Namespace(source="test close")
        )

    def test_wave_closed_grants_reset_run_complete_grants_survive(self) -> None:
        self.close()
        self.assertEqual("closed", self.run["active_wave"]["status"])
        self.assertEqual(
            [{"wave_id": "W-1", "batch_base_sha": self.base}],
            self.run["closed_waves"],
        )
        self.assertEqual(
            {"authorized": False, "source": None},
            self.run["authorizations"]["create_local_commits"],
        )
        # authorize_execution wrote a run_complete boundary: it survives.
        self.assertTrue(self.run["execution_authorized"])

    def test_worker_passed_closes_under_run_complete_but_not_wave_closed(self):
        self.run["mission_states"]["M1"]["phase"] = "worker_passed"
        self.close()
        self.assertEqual("closed", self.run["active_wave"]["status"])
        self.assertTrue(self.run["execution_authorized"])

        # A wave_closed execution boundary cannot cover a pending integration
        # past its own expiry, so that combination is refused instead.
        self.run["active_wave"].update(
            {"wave_id": "W-2", "status": "active", "selected_missions": ["M1"]}
        )
        self.run["closed_waves"] = []
        self.run["mission_states"]["M1"]["phase"] = "worker_passed"
        scope = self.run["execution_authorization_scope"]
        scope["expires_when"] = "wave_closed"
        scope["wave_id"] = "W-2"
        scope["batch_base_sha"] = self.base
        with self.assertRaises(ManifestError) as caught:
            self.close()
        self.assertIn("still await integration", str(caught.exception))

    def test_wave_bounded_execution_authorization_clears(self) -> None:
        scope = self.run["execution_authorization_scope"]
        scope["expires_when"] = "wave_closed"
        scope["wave_id"] = "W-1"
        scope["batch_base_sha"] = self.base
        self.close()
        self.assertFalse(self.run["execution_authorized"])
        self.assertIsNone(self.run["execution_authorization_source"])
        self.assertIsNone(self.run["execution_authorization_scope"])

    def test_idle_wave_and_double_close_are_refused(self) -> None:
        self.close()
        with self.assertRaises(ManifestError):
            self.close()
        self.run["active_wave"].update(
            {"status": "idle", "wave_id": None, "batch_base_sha": None}
        )
        with self.assertRaises(ManifestError):
            self.close()

    def test_running_mission_blocks_close(self) -> None:
        self.run["mission_states"]["M1"]["phase"] = "worker_running"
        with self.assertRaises(ManifestError) as caught:
            self.close()
        self.assertIn("queued or running", str(caught.exception))


class RunLockGateTests(unittest.TestCase):
    """Mutations refuse foreign locks; replaces compare-and-swap."""

    def test_foreign_lock_blocks_regardless_of_age_or_parseability(self) -> None:
        run = {"run_lock": {"session_id": "OTHER", "acquired_at": "x",
                            "heartbeat_at": "not-a-date"}}
        with self.assertRaises(ManifestError):
            harness_transition._ensure_no_foreign_lock(run, "MINE")
        with self.assertRaises(ManifestError):
            harness_transition._ensure_no_foreign_lock(run, None)
        harness_transition._ensure_no_foreign_lock(
            {"run_lock": {"session_id": "MINE"}}, "MINE"
        )
        harness_transition._ensure_no_foreign_lock({}, None)

    def test_replace_refuses_when_the_document_changed_under_us(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "RUN.md"
            original = "# f\n\n## Harness Run State\n\n```json\n{}\n```\n"
            path.write_text(original, encoding="utf-8")
            with self.assertRaises(ManifestError) as caught:
                harness_transition._replace_run_document(
                    path, {"touched": True}, expected_text=original + "drift\n"
                )
            self.assertIn("changed during this transition", str(caught.exception))
            # The clobbered write never landed.
            self.assertEqual(original, path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

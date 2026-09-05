#!/usr/bin/env python3
"""The scripted write path: observation, wave accept, lease, integration."""

from __future__ import annotations

import hashlib
import sys
import subprocess
import tempfile
import time
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
from harness_core import ManifestError, plan_digest  # noqa: E402
from harness_manifest import load_run  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
from manifest_fixtures import git  # noqa: E402


def make_repo() -> tuple[tempfile.TemporaryDirectory, Path, str, str]:
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    git(root, "init", "-q", "-b", "integration")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "T")
    (root / "file.txt").write_text("base\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "base")
    base = git(root, "rev-parse", "HEAD")
    (root / "file.txt").write_text("integrated\n", encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-qm", "work")
    head = git(root, "rev-parse", "HEAD")
    return temp, root, base, head


class WritePathTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp, self.root, self.base, self.head = make_repo()
        plan = mf.valid_plan()
        run = mf.valid_run(plan)
        mf.authorize_execution(run, ["M1", "M2"])
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            mf.authorize_action(run, action, ["M1", "M2"], ["*"])
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter["available_drivers"] = ["subagents", "sequential_parent"]
        adapter["detection_source"] = "observed"
        adapter["capability_probe"] = mf.codex_capability_probe(subagents=True)
        adapter["version_gate"] = mf.current_version_gate()
        run["runtime_capabilities"]["worker_runtime"] = "subagent"
        run["runtime_capabilities"]["max_parallel_workers"] = 2
        run["observed"]["runtime"].update(
            {
                "available_worker_slots": 2,
                "isolation_capacity": 2,
                "completion_channel_available": True,
            }
        )
        source_contents = {
            "prd": b"# Test PRD\n",
            "architecture": b"# Test architecture\n",
        }
        for source in plan["sources"]:
            contents = source_contents[source["kind"]]
            source_path = self.root / source["location"]
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_bytes(contents)
            source["content_sha256"] = hashlib.sha256(contents).hexdigest()
        git(self.root, "add", "docs/product")
        git(self.root, "commit", "-qm", "contracts")
        self.head = git(self.root, "rev-parse", "HEAD")
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["execution_authorization_scope"]["plan_digest_sha256"] = digest
        for authorization in run["authorizations"].values():
            if isinstance(authorization, dict) and isinstance(
                authorization.get("scope"), dict
            ):
                authorization["scope"]["plan_digest_sha256"] = digest
        run["integration"]["branch"] = "integration"
        run["landing"]["continuity"]["branch_ref"] = "refs/heads/integration"
        run["integration"]["batch_base_sha"] = self.head
        run["integration"]["integration_head_sha"] = None
        run["active_wave"].update(
            {
                "wave_id": None,
                "status": "idle",
                "batch_base_sha": None,
                "selected_missions": [],
            }
        )
        run["observed"]["captured_at"] = None
        self.plan, self.run = plan, run

    def tearDown(self) -> None:
        self._temp.cleanup()

    def _sync_plan_digest(self) -> None:
        digest = plan_digest(self.plan)
        self.run["plan"]["digest_sha256"] = digest
        self.run["execution_authorization_scope"]["plan_digest_sha256"] = digest
        for authorization in self.run["authorizations"].values():
            if isinstance(authorization, dict) and isinstance(
                authorization.get("scope"), dict
            ):
                authorization["scope"]["plan_digest_sha256"] = digest

    def test_observation_wave_lease_and_integration_chain(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        observed = self.run["observed"]
        self.assertEqual(self.head, observed["git"]["parent_head_sha"])
        self.assertEqual("integration", observed["git"]["parent_branch"])
        self.assertFalse(observed["git"]["parent_dirty"])
        self.assertTrue(observed["captured_at"])

        self.run["active_wave"]["status"] = "idle"
        harness_transition._accept_wave(
            self.plan,
            self.run,
            Namespace(
                wave_id="B-1",
                mission_id=["M1"],
                batch_base_sha=self.head,
                repo_root=self.root,
            ),
        )
        wave = self.run["active_wave"]
        self.assertEqual("active", wave["status"])
        self.assertEqual(["M1"], wave["selected_missions"])
        self.assertEqual(self.head, self.run["integration"]["batch_base_sha"])

        self.run["mission_states"]["M1"]["phase"] = "queued"
        harness_transition._lease_worker(
            self.plan,
            self.run,
            Namespace(
                mission_id="M1",
                node_id="N-M1",
                worker_id="W-M1-A",
                lease_id="LEASE-M1-A",
                attempt_id="ATT-M1-A",
                branch_ref="feature/m1",
                worktree_path=str(self.root / "wt-m1"),
                provider="codex",
                driver="subagents",
                worker_runtime="subagent",
                workspace_mode="parent_managed_worktree",
                completion_channel="agent_result",
            ),
        )
        worker = self.run["workers"][-1]
        self.assertEqual("W-M1-A", worker["worker_id"])
        self.assertEqual("worker_running", self.run["mission_states"]["M1"]["phase"])
        node_state = self.run["graph_state"]["node_states"]["N-M1"]
        self.assertEqual("running", node_state["phase"])
        self.assertTrue(
            any(a["attempt_id"] == "ATT-M1-A" for a in self.run["attempt_log"])
        )

        self.run["mission_states"]["M1"]["phase"] = "worker_passed"
        self.run["mission_states"]["M1"]["head_sha"] = self.head
        harness_transition._record_integration(
            self.plan,
            self.run,
            Namespace(mission_id="M1", integrated_sha=self.head, repo_root=self.root),
        )
        mission = self.run["mission_states"]["M1"]
        self.assertEqual("integrated", mission["phase"])
        self.assertEqual("PASS", mission["integration_gate"])
        self.assertEqual(self.head, self.run["integration"]["integration_head_sha"])

    def test_guards_refuse_the_wrong_states(self) -> None:
        with self.assertRaises(ManifestError):
            harness_transition._record_observation(self.run, Namespace(repo_root=None))

        self.run["active_wave"].update({"status": "active", "wave_id": "B-OTHER"})
        with self.assertRaises(ManifestError):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

        self.run["active_wave"].update({"status": "idle", "wave_id": None})
        with self.assertRaises(ManifestError):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha="not-the-observed-head",
                    repo_root=self.root,
                ),
            )

        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        harness_transition._accept_wave(
            self.plan,
            self.run,
            Namespace(
                wave_id="B-1",
                mission_id=["M1"],
                batch_base_sha=self.head,
                repo_root=self.root,
            ),
        )
        self.run["mission_states"]["M1"]["phase"] = "queued"
        lease_args = dict(
            mission_id="M1",
            node_id="N-M1",
            worker_id="W-M1-A",
            branch_ref="b",
            worktree_path="w",
            provider="codex",
            driver="subagents",
            worker_runtime="subagent",
            workspace_mode="parent_managed_worktree",
            completion_channel="agent_result",
        )
        harness_transition._lease_worker(
            self.plan, self.run, Namespace(lease_id="L", attempt_id="A", **lease_args)
        )
        # duplicate worker id on a re-queued mission is refused
        self.run["mission_states"]["M1"]["phase"] = "queued"
        with self.assertRaises(ManifestError):
            harness_transition._lease_worker(
                self.plan,
                self.run,
                Namespace(lease_id="L2", attempt_id="A2", **lease_args),
            )

        with self.assertRaises(ManifestError):
            harness_transition._record_integration(
                self.plan,
                self.run,
                Namespace(
                    mission_id="M1", integrated_sha=self.head, repo_root=self.root
                ),
            )

    def test_accept_wave_uses_the_selector_frontier(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        with self.assertRaisesRegex(ManifestError, "selector's dispatchable"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-M2",
                    mission_id=["M2"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

        self.plan["missions"][0]["worktree_eligible"] = False
        self.run["plan"]["digest_sha256"] = plan_digest(self.plan)
        for action in self.run["authorizations"].values():
            if isinstance(action, dict) and isinstance(action.get("scope"), dict):
                action["scope"]["plan_digest_sha256"] = self.run["plan"][
                    "digest_sha256"
                ]
        self.run["execution_authorization_scope"]["plan_digest_sha256"] = self.run[
            "plan"
        ]["digest_sha256"]
        with self.assertRaisesRegex(ManifestError, "worktree_ineligible"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-M1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_lease_refuses_a_pause_after_wave_acceptance(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        harness_transition._accept_wave(
            self.plan,
            self.run,
            Namespace(
                wave_id="B-1",
                mission_id=["M1"],
                batch_base_sha=self.head,
                repo_root=self.root,
            ),
        )
        self.run["control"]["desired_state"] = "paused"
        with self.assertRaisesRegex(ManifestError, "lease-worker runs only"):
            harness_transition._lease_worker(
                self.plan,
                self.run,
                Namespace(
                    mission_id="M1",
                    node_id="N-M1",
                    worker_id="W-M1-A",
                    lease_id="LEASE-M1-A",
                    attempt_id="ATT-M1-A",
                    branch_ref="feature/m1",
                    worktree_path=str(self.root / "wt-m1"),
                    provider="codex",
                    driver="subagents",
                    worker_runtime="subagent",
                    workspace_mode="parent_managed_worktree",
                    completion_channel="agent_result",
                ),
            )

    def test_accept_wave_rejects_live_git_drift_after_observation(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        (self.root / "later.txt").write_text("later\n", encoding="utf-8")
        git(self.root, "add", "later.txt")
        git(self.root, "commit", "-qm", "later")
        with self.assertRaisesRegex(ManifestError, "differs from observed parent head"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_accept_wave_rejects_product_dirt_after_observation(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        (self.root / "dirty-product.txt").write_text("dirty\n", encoding="utf-8")

        with self.assertRaisesRegex(ManifestError, "clean live integration checkout"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_record_integration_rejects_a_different_checkout(self) -> None:
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )
        self.run["mission_states"]["M1"]["phase"] = "worker_passed"
        self.run["mission_states"]["M1"]["head_sha"] = self.head
        with tempfile.TemporaryDirectory() as directory:
            other_checkout = Path(directory)
            with self.assertRaisesRegex(ManifestError, "observed parent worktree"):
                harness_transition._record_integration(
                    self.plan,
                    self.run,
                    Namespace(
                        mission_id="M1",
                        integrated_sha=self.head,
                        repo_root=other_checkout,
                    ),
                )

    def test_record_integration_ignores_only_the_tracked_run_file(self) -> None:
        run_path = self.root / "docs/goal/RUN.md"
        run_path.parent.mkdir(parents=True, exist_ok=True)
        run_path.write_text("baseline\n", encoding="utf-8")
        git(self.root, "add", "docs/goal/RUN.md")
        git(self.root, "commit", "-qm", "track run state")
        self.head = git(self.root, "rev-parse", "HEAD")
        self.run["integration"]["batch_base_sha"] = self.head
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root, run=run_path)
        )
        run_path.write_text("transition update\n", encoding="utf-8")
        self.run["mission_states"]["M1"]["phase"] = "worker_passed"
        self.run["mission_states"]["M1"]["head_sha"] = self.head

        harness_transition._record_integration(
            self.plan,
            self.run,
            Namespace(
                mission_id="M1",
                integrated_sha=self.head,
                repo_root=self.root,
                run=run_path,
            ),
        )

        self.assertEqual("integrated", self.run["mission_states"]["M1"]["phase"])

    def test_accept_wave_blocks_a_missing_ui_contract_source(self) -> None:
        self.plan["ui_surfaces"] = [
            {
                "id": "UI-001",
                "trace_ids": ["REQ-001"],
                "route": "/home",
                "breakpoints": ["390"],
                "states": ["ready"],
                "evidence_gate": "required",
            }
        ]
        prd_path = self.root / self.plan["sources"][0]["location"]
        prd_text = (
            "<!-- ui-surface-contract:start -->\n"
            "## UI Surface Contract\n\n"
            "### UI-001 — Home\n\n"
            "- `route`: /home\n"
            "- `states`: ready\n"
            "<!-- ui-surface-contract:end -->\n"
        )
        prd_path.write_text(prd_text, encoding="utf-8")
        self.plan["sources"][0]["content_sha256"] = hashlib.sha256(
            prd_path.read_bytes()
        ).hexdigest()
        git(self.root, "add", "docs/product/prd.md")
        git(self.root, "commit", "-qm", "add UI contract")
        self.head = git(self.root, "rev-parse", "HEAD")
        self._sync_plan_digest()
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )

        with self.assertRaisesRegex(ManifestError, "frozen wireframes.html source"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_accept_wave_blocks_semantic_prd_route_drift(self) -> None:
        self.plan["ui_surfaces"] = [
            {
                "id": "UI-001",
                "trace_ids": ["REQ-001"],
                "route": "/home",
                "breakpoints": ["390"],
                "states": ["ready"],
                "evidence_gate": "required",
            }
        ]
        prd_path = self.root / self.plan["sources"][0]["location"]
        prd_path.write_text(
            "<!-- ui-surface-contract:start -->\n"
            "## UI Surface Contract\n\n"
            "### UI-001 — Home\n\n"
            "- `route`: /alias\n"
            "- `states`: ready\n"
            "<!-- ui-surface-contract:end -->\n",
            encoding="utf-8",
        )
        self.plan["sources"][0]["content_sha256"] = hashlib.sha256(
            prd_path.read_bytes()
        ).hexdigest()
        wireframe_path = self.root / "docs/product/wireframes.html"
        wireframe_path.write_text(
            mf.wireframes_html(
                [{"id": "UI-001", "route": "/home", "states": ["ready"]}]
            ),
            encoding="utf-8",
        )
        self.plan["sources"].append(
            {
                "id": "SRC-WIREFRAME",
                "kind": "wireframe",
                "location": "docs/product/wireframes.html",
                "owner": "product",
                "status": "frozen",
                "content_sha256": hashlib.sha256(
                    wireframe_path.read_bytes()
                ).hexdigest(),
                "source_revision": None,
                "staged_revision": None,
                "notes": "approved projection",
            }
        )
        git(self.root, "add", "docs/product")
        git(self.root, "commit", "-qm", "add drifted UI artifacts")
        self.head = git(self.root, "rev-parse", "HEAD")
        self._sync_plan_digest()
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )

        with self.assertRaisesRegex(ManifestError, "differs from the PRD route"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_accept_wave_cannot_hide_prd_ui_by_emptying_plan_surfaces(self) -> None:
        prd_path = self.root / self.plan["sources"][0]["location"]
        prd_path.write_text(
            "<!-- ui-surface-contract:start -->\n"
            "## 介面契約\n\n"
            "### UI-001 — 首頁\n\n"
            "- `route`: /home\n"
            "- `states`: ready\n"
            "<!-- ui-surface-contract:end -->\n",
            encoding="utf-8",
        )
        self.plan["sources"][0]["content_sha256"] = hashlib.sha256(
            prd_path.read_bytes()
        ).hexdigest()
        git(self.root, "add", "docs/product/prd.md")
        git(self.root, "commit", "-qm", "freeze UI contract")
        self.head = git(self.root, "rev-parse", "HEAD")
        self.run["integration"]["batch_base_sha"] = self.head
        self._sync_plan_digest()
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )

        with self.assertRaisesRegex(ManifestError, "PRD surfaces absent from the PLAN"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_accept_wave_rejects_ui_headings_outside_the_machine_boundary(
        self,
    ) -> None:
        prd_path = self.root / self.plan["sources"][0]["location"]
        prd_path.write_text(
            "<!-- ui-surface-contract:start -->\n"
            "## 介面契約\n"
            "<!-- ui-surface-contract:end -->\n"
            "### UI-001 — Outside\n\n"
            "- `route`: /home\n"
            "- `states`: ready\n",
            encoding="utf-8",
        )
        self.plan["sources"][0]["content_sha256"] = hashlib.sha256(
            prd_path.read_bytes()
        ).hexdigest()
        git(self.root, "add", "docs/product/prd.md")
        git(self.root, "commit", "-qm", "freeze malformed UI contract")
        self.head = git(self.root, "rev-parse", "HEAD")
        self.run["integration"]["batch_base_sha"] = self.head
        self._sync_plan_digest()
        harness_transition._record_observation(
            self.run, Namespace(repo_root=self.root)
        )

        with self.assertRaisesRegex(ManifestError, "headings outside"):
            harness_transition._accept_wave(
                self.plan,
                self.run,
                Namespace(
                    wave_id="B-1",
                    mission_id=["M1"],
                    batch_base_sha=self.head,
                    repo_root=self.root,
                ),
            )

    def test_tracked_run_cli_chain_works_from_a_linked_integration_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            container = Path(directory)
            main_root = container / "main"
            linked_root = container / "integration"
            main_root.mkdir()
            git(main_root, "init", "-q", "-b", "main")
            git(main_root, "config", "user.email", "t@example.com")
            git(main_root, "config", "user.name", "T")
            (main_root / "base.txt").write_text("base\n", encoding="utf-8")
            git(main_root, "add", "base.txt")
            git(main_root, "commit", "-qm", "base")
            git(main_root, "worktree", "add", "-q", "-b", "integration", str(linked_root))

            plan = mf.valid_plan()
            for source, contents in zip(
                plan["sources"],
                (b"# Product contract\n", b"# Architecture contract\n"),
            ):
                source_path = linked_root / source["location"]
                source_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.write_bytes(contents)
                source["content_sha256"] = hashlib.sha256(contents).hexdigest()
            run = mf.valid_run(plan)
            mf.authorize_execution(run, ["M1", "M2"])
            for action in (
                "spawn_subagents",
                "create_local_worktrees",
                "create_local_branches",
                "create_local_commits",
            ):
                mf.authorize_action(run, action, ["M1", "M2"], ["*"])
            adapter = run["runtime_capabilities"]["runtime_adapter"]
            adapter["available_drivers"] = ["subagents", "sequential_parent"]
            adapter["detection_source"] = "observed"
            adapter["capability_probe"] = mf.codex_capability_probe(subagents=True)
            adapter["version_gate"] = mf.current_version_gate()
            run["runtime_capabilities"]["worker_runtime"] = "subagent"
            run["runtime_capabilities"]["max_parallel_workers"] = 2
            run["observed"]["runtime"].update(
                {
                    "available_worker_slots": 2,
                    "isolation_capacity": 2,
                    "completion_channel_available": True,
                }
            )
            run["integration"].update(
                {
                    "branch": "integration",
                    "batch_base_sha": None,
                    "integration_head_sha": None,
                }
            )
            run["landing"]["continuity"]["branch_ref"] = "refs/heads/integration"
            run["active_wave"].update(
                {
                    "wave_id": None,
                    "status": "idle",
                    "batch_base_sha": None,
                    "selected_missions": [],
                }
            )
            run["observed"]["captured_at"] = None

            goal_root = linked_root / "docs" / "goal"
            goal_root.mkdir(parents=True, exist_ok=True)
            plan_path = goal_root / "PLAN.md"
            run_path = goal_root / "RUN.md"
            plan_path.write_text(
                mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path.write_text(
                mf.manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            git(linked_root, "add", ".")
            git(linked_root, "commit", "-qm", "tracked harness layout")
            head = git(linked_root, "rev-parse", "HEAD")

            base_command = [
                sys.executable,
                str(SCRIPTS_DIR / "harness_transition.py"),
                "--plan",
                str(plan_path),
                "--run",
                str(run_path),
                "--repo-root",
                str(linked_root),
                "--session-id",
                "tracked-layout",
            ]
            for command in (
                ["acquire-run-lock"],
                ["record-observation"],
                [
                    "accept-wave",
                    "--wave-id",
                    "B-1",
                    "--mission-id",
                    "M1",
                    "--batch-base-sha",
                    head,
                ],
            ):
                result = subprocess.run(
                    [*base_command, *command],
                    cwd=linked_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)

            live = load_run(run_path)
            self.assertTrue(
                harness_transition._same_path(
                    linked_root, live["observed"]["git"]["parent_worktree_path"]
                )
            )
            self.assertFalse(live["observed"]["git"]["parent_dirty"])
            self.assertEqual("active", live["active_wave"]["status"])
            self.assertEqual(["M1"], live["active_wave"]["selected_missions"])
            status = git(linked_root, "status", "--porcelain")
            self.assertEqual("M docs/goal/RUN.md", status.strip())

    def test_transition_lock_serializes_separate_processes(self) -> None:
        target = self.root / "RUN.md"
        script = (
            "import sys; from pathlib import Path; "
            f"sys.path.insert(0, {str(SCRIPTS_DIR)!r}); "
            "from harness_transition import _run_transition_lock; "
            "\nwith _run_transition_lock(Path(sys.argv[1])): print('acquired')"
        )
        with harness_transition._run_transition_lock(target):
            process = subprocess.Popen(
                [sys.executable, "-c", script, str(target)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            time.sleep(0.25)
            self.assertIsNone(process.poll())
        stdout, stderr = process.communicate(timeout=15)
        self.assertEqual(0, process.returncode, stderr)
        self.assertIn("acquired", stdout)


if __name__ == "__main__":
    unittest.main()

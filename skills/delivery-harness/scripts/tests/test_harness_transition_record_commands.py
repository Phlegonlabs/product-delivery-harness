#!/usr/bin/env python3
"""The record-only run lifecycle commands on harness_transition.py."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
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
import manifest_fixtures as mf  # noqa: E402


SESSION = "record-commands"
OTHER_SESSION = "someone-else"


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


class RecordCommandsFixture(unittest.TestCase):
    """Drive harness_transition.main() against a real generated-shape PLAN/RUN pair."""

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        mf.git(self.root, "init", "-q", "-b", "integration")
        mf.git(self.root, "config", "user.email", "t@example.com")
        mf.git(self.root, "config", "user.name", "T")
        (self.root / "file.txt").write_text("base\n", encoding="utf-8")
        mf.git(self.root, "add", ".")
        mf.git(self.root, "commit", "-qm", "base")
        self.base = mf.git(self.root, "rev-parse", "HEAD")
        self.plan = mf.valid_plan()
        mf.materialize_plan_sources(self.root, self.plan)
        mf.git(self.root, "add", "docs/product")
        mf.git(self.root, "commit", "-qm", "freeze contracts")
        self.head = mf.git(self.root, "rev-parse", "HEAD")
        self.run = mf.valid_run(self.plan)
        # A fresh generated RUN carries no integration head yet and plans
        # continuity on the run branch; the fixture seeds the same shape.
        self.run["integration"]["branch"] = "integration"
        self.run["integration"]["integration_head_sha"] = None
        self.run["integration"]["batch_base_sha"] = None
        self.run["landing"]["continuity"] = {
            "status": "planned",
            "branch_ref": "refs/heads/integration",
            "head_sha": None,
            "reason": "Keep the reviewed run branch so the user can read it",
        }
        self.plan_path = self.root / "PLAN.md"
        self.run_path = self.root / "RUN.md"
        self.rewrite_run()

    def rewrite_run(self) -> None:
        self.plan_path.write_text(
            mf.manifest_markdown("## Harness Plan Manifest", "harness_plan", self.plan),
            encoding="utf-8",
        )
        self.run_path.write_text(
            mf.manifest_markdown("## Harness Run State", "harness_run", self.run),
            encoding="utf-8",
        )

    def reload_run(self) -> dict:
        return load_run_block(self.run_path)

    def transition(self, *extra: str, session: str | None = SESSION) -> int:
        argv = ["--plan", str(self.plan_path), "--run", str(self.run_path)]
        if session is not None:
            argv += ["--session-id", session]
        return harness_transition.main([*argv, *extra])


class RecordGrantTests(RecordCommandsFixture):
    def test_records_an_action_grant_bound_to_the_run(self) -> None:
        self.assertEqual(0, self.transition("acquire-run-lock"))
        self.assertEqual(
            0,
            self.transition(
                "record-grant",
                "--action", "create_local_branches",
                "--target", "branch:refs/heads/integration",
                "--target", "branch:refs/heads/wt/m1",
                "--mission-id", "M1",
                "--mission-id", "M2",
                "--expires-when", "run_complete",
                "--source", "owner authorized branch creation",
            ),
        )
        live = self.reload_run()
        self.assertEqual(
            {
                "authorized": True,
                "source": "owner authorized branch creation",
                "scope": {
                    "run_id": live["run_id"],
                    "plan_revision": live["plan"]["revision"],
                    "plan_digest_sha256": live["plan"]["digest_sha256"],
                    "mission_ids": ["M1", "M2"],
                    "targets": [
                        "branch:refs/heads/integration",
                        "branch:refs/heads/wt/m1",
                    ],
                },
                "expires_when": "run_complete",
            },
            live["authorizations"]["create_local_branches"],
        )
        attempt = live["attempt_log"][-1]
        self.assertEqual("authorization_record", attempt["kind"])
        self.assertIn("owner authorized branch creation", attempt["evidence"])

    def test_refuses_push_and_writes_nothing(self) -> None:
        self.assertEqual(0, self.transition("acquire-run-lock"))
        before = self.run_path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = self.transition(
                "record-grant",
                "--action", "push",
                "--target", "branch:refs/heads/feature",
                "--mission-id", "M1",
                "--expires-when", "run_complete",
                "--source", "owner asks for a push",
            )
        self.assertEqual(2, code)
        self.assertIn("push", stderr.getvalue())
        self.assertEqual(before, self.run_path.read_bytes())

    def test_requires_the_held_run_lock(self) -> None:
        arguments = (
            "record-grant",
            "--action", "integrate_locally",
            "--target", "branch:integration",
            "--mission-id", "M1",
            "--expires-when", "run_complete",
            "--source", "owner authorized integration",
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(2, self.transition(*arguments))
        self.assertEqual(0, self.transition("acquire-run-lock"))
        before = self.run_path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(2, self.transition(*arguments, session=OTHER_SESSION))
        self.assertEqual(before, self.run_path.read_bytes())

    def test_wave_closed_grant_binds_the_active_wave(self) -> None:
        self.run["active_wave"] = {
            "wave_id": "W-1",
            "status": "proposed",
            "plan_revision": self.run["plan"]["revision"],
            "plan_digest_sha256": self.run["plan"]["digest_sha256"],
            "batch_base_sha": self.head,
            "selected_missions": ["M1"],
            "deferred_missions": [],
            "conflict_edges": [],
        }
        self.rewrite_run()
        self.assertEqual(0, self.transition("acquire-run-lock"))
        self.assertEqual(
            0,
            self.transition(
                "record-grant",
                "--action", "create_local_commits",
                "--target", "branch:refs/heads/integration",
                "--mission-id", "M1",
                "--expires-when", "wave_closed",
                "--source", "owner authorized one wave of commits",
            ),
        )
        live = self.reload_run()
        scope = live["authorizations"]["create_local_commits"]["scope"]
        self.assertEqual("W-1", scope["wave_id"])
        self.assertEqual(self.head, scope["batch_base_sha"])

    def test_refuses_wave_closed_without_a_live_wave(self) -> None:
        self.assertEqual(0, self.transition("acquire-run-lock"))
        before = self.run_path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = self.transition(
                "record-grant",
                "--action", "create_local_commits",
                "--target", "branch:refs/heads/integration",
                "--mission-id", "M1",
                "--expires-when", "wave_closed",
                "--source", "owner words",
            )
        self.assertEqual(2, code)
        self.assertIn("wave", stderr.getvalue())
        self.assertEqual(before, self.run_path.read_bytes())

    def test_execution_grant_fills_the_scope_without_targets(self) -> None:
        self.run["status"] = "ready"
        self.run["plan_readiness"] = "ready"
        self.run["intent"] = "plan-then-execute"
        self.rewrite_run()
        self.assertEqual(0, self.transition("acquire-run-lock"))
        self.assertEqual(
            0,
            self.transition(
                "record-grant",
                "--action", "execution",
                "--mission-id", "M1",
                "--mission-id", "M2",
                "--expires-when", "run_complete",
                "--source", "owner authorized execution",
            ),
        )
        live = self.reload_run()
        self.assertTrue(live["execution_authorized"])
        self.assertEqual("owner authorized execution", live["execution_authorization_source"])
        self.assertEqual(
            {
                "run_id": live["run_id"],
                "plan_revision": live["plan"]["revision"],
                "plan_digest_sha256": live["plan"]["digest_sha256"],
                "mission_ids": ["M1", "M2"],
                "expires_when": "run_complete",
            },
            live["execution_authorization_scope"],
        )
        self.assertNotIn("targets", live["execution_authorization_scope"])

    def test_refuses_a_target_on_the_execution_grant(self) -> None:
        self.run["status"] = "ready"
        self.run["plan_readiness"] = "ready"
        self.run["intent"] = "plan-then-execute"
        self.rewrite_run()
        self.assertEqual(0, self.transition("acquire-run-lock"))
        before = self.run_path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = self.transition(
                "record-grant",
                "--action", "execution",
                "--target", "branch:refs/heads/integration",
                "--mission-id", "M1",
                "--expires-when", "run_complete",
                "--source", "owner authorized execution",
            )
        self.assertEqual(2, code)
        self.assertIn("--target", stderr.getvalue())
        self.assertEqual(before, self.run_path.read_bytes())

    def test_validator_refuses_a_mismatched_target_kind(self) -> None:
        self.assertEqual(0, self.transition("acquire-run-lock"))
        before = self.run_path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = self.transition(
                "record-grant",
                "--action", "create_local_branches",
                "--target", "worker:W-1",
                "--mission-id", "M1",
                "--expires-when", "run_complete",
                "--source", "owner words",
            )
        self.assertEqual(2, code)
        self.assertIn("invalid RUN", stderr.getvalue())
        self.assertEqual(before, self.run_path.read_bytes())


class OpenRunTests(RecordCommandsFixture):
    def test_opens_a_draft_run_ready(self) -> None:
        self.assertEqual(0, self.transition("acquire-run-lock"))
        self.assertEqual(
            0,
            self.transition(
                "open-run",
                "--intent", "plan-then-execute",
                "--source", "owner opens the run for delivery",
            ),
        )
        live = self.reload_run()
        self.assertEqual("ready", live["status"])
        self.assertEqual("ready", live["plan_readiness"])
        self.assertEqual("plan-then-execute", live["intent"])
        self.assertFalse(live["execution_authorized"])
        attempt = live["attempt_log"][-1]
        self.assertEqual("run_open", attempt["kind"])
        self.assertIn("owner opens the run for delivery", attempt["evidence"])

    def test_execution_flags_authorize_execution(self) -> None:
        self.assertEqual(0, self.transition("acquire-run-lock"))
        self.assertEqual(
            0,
            self.transition(
                "open-run",
                "--intent", "execute-ready-plan",
                "--mission-id", "M1",
                "--mission-id", "M2",
                "--expires-when", "run_complete",
                "--source", "owner opens the run for execution",
            ),
        )
        live = self.reload_run()
        self.assertTrue(live["execution_authorized"])
        self.assertEqual("owner opens the run for execution", live["execution_authorization_source"])
        self.assertEqual(
            {
                "run_id": live["run_id"],
                "plan_revision": live["plan"]["revision"],
                "plan_digest_sha256": live["plan"]["digest_sha256"],
                "mission_ids": ["M1", "M2"],
                "expires_when": "run_complete",
            },
            live["execution_authorization_scope"],
        )

    def test_refuses_execution_flags_on_a_plan_only_intent(self) -> None:
        self.assertEqual(0, self.transition("acquire-run-lock"))
        before = self.run_path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = self.transition(
                "open-run",
                "--intent", "plan-only",
                "--mission-id", "M1",
                "--expires-when", "run_complete",
                "--source", "owner words",
            )
        self.assertEqual(2, code)
        self.assertIn("cannot authorize execution", stderr.getvalue())
        self.assertEqual(before, self.run_path.read_bytes())

    def test_refuses_to_open_a_running_or_complete_run(self) -> None:
        self.run["status"] = "running"
        self.rewrite_run()
        self.assertEqual(0, self.transition("acquire-run-lock"))
        before = self.run_path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = self.transition(
                "open-run", "--intent", "plan-then-execute", "--source", "owner words"
            )
        self.assertEqual(2, code)
        self.assertIn("running", stderr.getvalue())
        self.assertEqual(before, self.run_path.read_bytes())
        self.run["status"] = "complete"
        self.rewrite_run()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(
                2,
                self.transition(
                    "open-run", "--intent", "plan-then-execute", "--source", "owner words"
                ),
            )


class CloseRunTests(RecordCommandsFixture):
    """close-run completes an integrated run and preserves its branch."""

    def setUp(self) -> None:
        super().setUp()
        self.run["observed"]["git"].update(
            {
                "parent_worktree_path": self.root.as_posix(),
                "parent_branch": "integration",
                "parent_head_sha": self.head,
                "parent_dirty": False,
            }
        )
        self.run["integration"].update(
            {
                "branch": "integration",
                "batch_base_sha": self.base,
                "integration_head_sha": self.head,
            }
        )
        mf.mark_complete(self.plan, self.run)
        # Step back to the state close-run starts from: the work is fully
        # integrated, but the close itself is not recorded yet.
        self.run["status"] = "running"
        self.run["landing"]["continuity"] = {
            "status": "planned",
            "branch_ref": "refs/heads/integration",
            "head_sha": None,
            "reason": "Keep the reviewed run branch so the user can read it",
        }
        self.rewrite_run()

    def test_closes_an_integrated_run(self) -> None:
        self.assertEqual(0, self.transition("acquire-run-lock"))
        self.assertEqual(
            0,
            self.transition("close-run", "--source", "owner closes the delivered run"),
        )
        live = self.reload_run()
        self.assertEqual("complete", live["status"])
        self.assertEqual("preserved", live["landing"]["continuity"]["status"])
        self.assertEqual(self.head, live["landing"]["continuity"]["head_sha"])
        attempt = live["attempt_log"][-1]
        self.assertEqual("run_closed", attempt["kind"])
        self.assertIn("owner closes the delivered run", attempt["evidence"])

    def test_refuses_an_unintegrated_run(self) -> None:
        # Only a fresh draft run validates without an integration head; a
        # running pair without one is already refused by acquire-run-lock.
        self.run = mf.valid_run(self.plan)
        self.run["integration"]["branch"] = "integration"
        self.run["integration"]["batch_base_sha"] = None
        self.run["integration"]["integration_head_sha"] = None
        self.run["landing"]["continuity"] = {
            "status": "planned",
            "branch_ref": "refs/heads/integration",
            "head_sha": None,
            "reason": "Keep the reviewed run branch so the user can read it",
        }
        self.rewrite_run()
        self.assertEqual(0, self.transition("acquire-run-lock"))
        before = self.run_path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = self.transition("close-run", "--source", "owner words")
        self.assertEqual(2, code)
        self.assertIn("integration head", stderr.getvalue())
        self.assertEqual(before, self.run_path.read_bytes())

    def test_refuses_when_continuity_cannot_be_preserved(self) -> None:
        # Blocked continuity cannot pass acquire-run-lock beside authorized
        # execution, so the refusal runs _close_run on the in-memory pair
        # while the validating pair stays on disk.
        self.rewrite_run()
        before = self.run_path.read_bytes()
        self.run["landing"]["continuity"] = {
            "status": "blocked",
            "branch_ref": "refs/heads/integration",
            "head_sha": self.head,
            "reason": "the run branch was deleted after integration",
        }
        arguments = argparse.Namespace(
            source="owner words", repo_root=None, run=self.run_path
        )
        with self.assertRaises(harness_transition.ManifestError) as raised:
            harness_transition._close_run(self.plan, self.run, arguments)
        self.assertIn("continuity", str(raised.exception))
        self.assertEqual(before, self.run_path.read_bytes())

    def test_requires_the_held_run_lock(self) -> None:
        arguments = ("close-run", "--source", "owner closes the run")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(2, self.transition(*arguments))
        self.assertEqual(0, self.transition("acquire-run-lock"))
        before = self.run_path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(2, self.transition(*arguments, session=OTHER_SESSION))
        self.assertEqual(before, self.run_path.read_bytes())


class RecordRuntimeTests(RecordCommandsFixture):
    """record-runtime writes the observed adapter surface and version gate."""

    def record_runtime(self, *extra: str) -> int:
        return self.transition(
            "record-runtime",
            "--provider", "codex",
            "--driver", "sequential_parent",
            *extra,
        )

    def test_records_the_observed_adapter_and_gate(self) -> None:
        self.assertEqual(0, self.transition("acquire-run-lock"))
        self.assertEqual(
            0,
            self.record_runtime(
                "--route-caps",
                '{"sequential_parent": {"wall_clock_seconds": 900, '
                '"tool_turns": 50, "max_message_bytes": 48000}}',
                "--loaded-digest", "b" * 64,
            ),
        )
        live = self.reload_run()
        adapter = live["runtime_capabilities"]["runtime_adapter"]
        self.assertEqual("codex", adapter["provider"])
        self.assertEqual(["sequential_parent"], adapter["available_drivers"])
        self.assertEqual("observed", adapter["detection_source"])
        gate = adapter["version_gate"]
        self.assertEqual("unobserved", gate["status"])
        self.assertEqual("b" * 64, gate["loaded_contract_digest"])
        self.assertIsNone(gate["installed_contract_digest"])
        self.assertEqual(SESSION, gate["session_id"])
        attempt = live["attempt_log"][-1]
        self.assertEqual("runtime_record", attempt["kind"])
        self.assertIn("sequential_parent.wall_clock_seconds=900", attempt["evidence"])

    def test_loaded_digest_stays_null_by_default(self) -> None:
        self.assertEqual(0, self.transition("acquire-run-lock"))
        self.assertEqual(
            0,
            self.record_runtime(
                "--route-caps", "sequential_parent=wall_clock_seconds=1800"
            ),
        )
        live = self.reload_run()
        gate = live["runtime_capabilities"]["runtime_adapter"]["version_gate"]
        self.assertIsNone(gate["loaded_contract_digest"])
        self.assertIsNone(gate["installed_contract_digest"])
        self.assertEqual("unobserved", gate["status"])
        attempt = live["attempt_log"][-1]
        self.assertIn("sequential_parent.wall_clock_seconds=1800", attempt["evidence"])

    def test_records_subagents_when_the_axes_support_it(self) -> None:
        runtime = self.run["runtime_capabilities"]
        runtime["worker_runtime"] = "subagent"
        runtime["completion_channel"] = "agent_result"
        # The on-disk pair must validate: route the recorded adapter to the
        # subagents driver the mutated axes support.
        runtime["runtime_adapter"]["available_drivers"] = [
            "subagents",
            "sequential_parent",
        ]
        self.rewrite_run()
        self.assertEqual(0, self.transition("acquire-run-lock"))
        self.assertEqual(
            0,
            self.transition(
                "record-runtime",
                "--provider", "codex",
                "--driver", "subagents",
                "--driver", "sequential_parent",
                "--route-caps", "subagents=tool_turns=40",
            ),
        )
        live = self.reload_run()
        adapter = live["runtime_capabilities"]["runtime_adapter"]
        self.assertEqual(
            ["subagents", "sequential_parent"], adapter["available_drivers"]
        )
        self.assertIn("subagents.tool_turns=40", live["attempt_log"][-1]["evidence"])

    def test_refuses_an_unknown_route_or_cap(self) -> None:
        self.assertEqual(0, self.transition("acquire-run-lock"))
        for caps in (
            "expires=wall_clock_seconds=900",
            "sequential_parent=expires=900",
        ):
            with self.subTest(caps=caps):
                before = self.run_path.read_bytes()
                with contextlib.redirect_stderr(io.StringIO()) as stderr:
                    code = self.record_runtime("--route-caps", caps)
                self.assertEqual(2, code)
                self.assertIn("unknown", stderr.getvalue())
                self.assertEqual(before, self.run_path.read_bytes())

    def test_validator_refuses_a_subagents_route_on_parent_axes(self) -> None:
        self.assertEqual(0, self.transition("acquire-run-lock"))
        before = self.run_path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = self.transition(
                "record-runtime",
                "--provider", "codex",
                "--driver", "subagents",
                "--driver", "sequential_parent",
                "--route-caps", "subagents=wall_clock_seconds=900",
            )
        self.assertEqual(2, code)
        self.assertIn("invalid RUN", stderr.getvalue())
        self.assertIn("subagents requires", stderr.getvalue())
        self.assertEqual(before, self.run_path.read_bytes())

    def test_requires_the_held_run_lock(self) -> None:
        arguments = (
            "record-runtime",
            "--provider", "codex",
            "--driver", "sequential_parent",
            "--route-caps", "sequential_parent=wall_clock_seconds=900",
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(2, self.transition(*arguments))
        self.assertEqual(0, self.transition("acquire-run-lock"))
        before = self.run_path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(2, self.transition(*arguments, session=OTHER_SESSION))
        self.assertEqual(before, self.run_path.read_bytes())


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Tests for build_verifier_request.py."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for directory in (SCRIPTS_DIR, TESTS_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import manifest_fixtures as mf  # noqa: E402
import test_validate_worker_result as fx  # noqa: E402
import verifier_runtime  # noqa: E402
from build_verifier_request import main as build_main  # noqa: E402
from harness_core import plan_digest  # noqa: E402
from harness_schema import PLAN_HEADING, RUN_HEADING  # noqa: E402


BRANCH = "codex/worker-m1"


class BuildVerifierRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.temp = Path(directory.name).resolve()
        self.repo = self.temp / "worker"
        self.repo.mkdir()
        self.base = mf.init_repo(self.repo, "README.md", default_branch=BRANCH)
        self.task_commit = self.commit("src/m1/feature.py")
        self.plan = fx.make_plan()
        mission = self.plan["missions"][0]
        for declaration in (mission["tasks"][0]["verifiers"][0], mission["worker_verifiers"][0]):
            declaration.update(argv=[sys.executable, "-c", "print('ok')"], read_only=True)
        self.run_state = fx.make_run(self.plan)
        self.out = self.temp / "requests" / "request.json"
        self.write_state()

    def commit(self, name: str) -> str:
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{name}\n", encoding="utf-8")
        mf.git(self.repo, "add", name)
        mf.git(self.repo, "commit", "-qm", f"add {name}")
        return mf.git(self.repo, "rev-parse", "HEAD")

    def write_state(self) -> None:
        digest = plan_digest(self.plan)
        worker = self.run_state["workers"][0]
        worker.update(worktree_path=str(self.repo), branch_ref=f"refs/heads/{BRANCH}",
                      batch_base_sha=self.base, attempt_id="ATT1", plan_digest_sha256=digest)
        self.run_state["plan"]["digest_sha256"] = digest
        (self.temp / "PLAN.md").write_text(mf.manifest_markdown(PLAN_HEADING, "harness_plan", self.plan), encoding="utf-8")
        (self.temp / "RUN.md").write_text(mf.manifest_markdown(RUN_HEADING, "harness_run", self.run_state), encoding="utf-8")

    def build(self, *extra: str, out: Path | None = None) -> tuple[int, str]:
        argv = ["--plan", str(self.temp / "PLAN.md"), "--run", str(self.temp / "RUN.md"),
                "--repo-root", str(self.repo), "--mission-id", "M1", "--out", str(out or self.out), *extra]
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                code = build_main(argv)
            except SystemExit as exc:
                code = exc.code
        return code, output.getvalue()

    def request(self) -> dict:
        return json.loads(self.out.read_text(encoding="utf-8"))

    def test_task_request_binds_the_task_commit_and_runs_in_verifier_runtime(self) -> None:
        self.commit("src/m1/second.py")
        second = mf.git(self.repo, "rev-parse", "HEAD")
        code, output = self.build("--verifier-id", "task-focused", "--task-id", "M1/T01",
                                  "--commit", self.task_commit, "--commit", second)
        self.assertEqual(0, code, output)
        context = self.request()["context"]
        self.assertEqual({
            "run_id": "RUN_TEST", "plan_revision": 1, "plan_digest_sha256": plan_digest(self.plan),
            "graph_revision": 1, "batch_base_sha": self.base, "head_sha": second,
            "changed_files": ["src/m1/feature.py", "src/m1/second.py"], "trust_domain": "parent_local",
            "checkout_role": "worker", "checkout_dirty": False, "cache_safe": False, "layer": "task",
            "mission_id": "M1", "task_id": "M1/T01", "attempt_id": "ATT1-T01", "lease_id": "LEASE1",
        }, context)
        self.assertEqual({"expected_branch": BRANCH, "expected_head_sha": second, "ignored_paths": []},
                         self.request()["git_guard"])
        with contextlib.redirect_stdout(io.StringIO()) as result:
            self.assertEqual(0, verifier_runtime.main(["--request", str(self.out)]))
        self.assertEqual("PASS", json.loads(result.getvalue())["status"])

    def test_worker_request_covers_the_whole_lease(self) -> None:
        self.commit("src/m1/other.py")
        code, output = self.build("--verifier-id", "mission-focused")
        self.assertEqual(0, code, output)
        context = self.request()["context"]
        self.assertEqual(("worker", None, "ATT1-W"), (context["layer"], context["task_id"], context["attempt_id"]))
        self.assertEqual(["src/m1/feature.py", "src/m1/other.py"], context["changed_files"])
        self.assertEqual(mf.git(self.repo, "rev-parse", "HEAD"), context["head_sha"])

    def test_refusals_exit_1_and_write_nothing(self) -> None:
        task = ("--verifier-id", "task-focused", "--task-id", "M1/T01", "--commit", self.task_commit)
        later = self.commit("src/m1/later.py")
        self.assertIn("live HEAD is not the last --commit", self.build(*task)[1])
        mf.git(self.repo, "reset", "-q", "--hard", self.task_commit)
        (self.repo / "scratch.txt").write_text("dirty\n", encoding="utf-8")
        self.assertIn("must be clean", self.build(*task)[1])
        (self.repo / "scratch.txt").unlink()
        cases = [
            ("--verifier-id", "mission-integration"),
            ("--verifier-id", "task-focused"),
            ("--verifier-id", "mission-focused", "--task-id", "M1/T01", "--commit", self.task_commit),
            ("--verifier-id", "task-focused", "--task-id", "M1/T01", "--commit", later),
        ]
        for extra in cases:
            with self.subTest(arguments=extra):
                self.assertEqual(1, self.build(*extra)[0])
        self.plan["revision"] = 2
        (self.temp / "PLAN.md").write_text(mf.manifest_markdown(PLAN_HEADING, "harness_plan", self.plan), encoding="utf-8")
        self.assertIn("not the revision the lease was granted on", self.build(*task)[1])
        self.plan["revision"] = 1
        self.run_state["mission_states"]["M1"]["phase"] = "worker_passed"
        self.write_state()
        self.assertIn("no live worker lease", self.build(*task)[1])
        self.assertFalse(self.out.exists())

    def test_bad_arguments_exit_2(self) -> None:
        cases = [
            (("--verifier-id", "task-focused", "--commit", self.task_commit), None),
            (("--verifier-id", "task-focused", "--task-id", "M1/T01", "--commit", "abc123"), None),
            (("--verifier-id", "mission-focused"), self.repo / "request.json"),
        ]
        for extra, out in cases:
            with self.subTest(arguments=extra):
                self.assertEqual(2, self.build(*extra, out=out)[0])
        (self.temp / "PLAN.md").unlink()
        self.assertEqual(2, self.build("--verifier-id", "mission-focused")[0])
        self.assertFalse(self.out.exists())
        self.assertFalse((self.repo / "request.json").exists())


if __name__ == "__main__":
    unittest.main()

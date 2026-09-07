#!/usr/bin/env python3
"""Live-checkout guards for the required integration security review."""

from __future__ import annotations

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
from harness_core import ManifestError  # noqa: E402
from harness_manifest import load_plan  # noqa: E402


PLAN_TEMPLATE = SCRIPTS_DIR.parent / "assets" / "templates" / "HARNESS_PLAN.template.md"


class SecurityIntegrationCheckoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.repo_temp.cleanup)
        self.root = Path(self.repo_temp.name)
        self._git("init", "-q", "-b", "security-check")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "Harness Test")
        source = self.root / "src" / "example" / "app.py"
        source.parent.mkdir(parents=True)
        source.write_text("print('fixture')\n", encoding="utf-8")
        self._git("add", "src/example/app.py")
        self._git("commit", "-qm", "security fixture")
        self.head = self._git_out("rev-parse", "HEAD")
        self.plan = load_plan(PLAN_TEMPLATE)
        self.run = new_run.build_run(
            self.plan,
            run_id="RUN-security-checkout",
            branch="refs/heads/security-check",
        )
        self.run["integration"].update(
            {"batch_base_sha": self.head, "integration_head_sha": self.head}
        )
        self.run["observed"]["git"].update(
            {
                "parent_worktree_path": str(self.root),
                "parent_branch": "security-check",
                "parent_head_sha": self.head,
                "parent_dirty": False,
            }
        )
        self.node = next(
            node
            for node in self.plan["graph"]["nodes"]
            if node.get("id") == "N-SECURITY-REVIEW"
        )

    def _git(self, *args: str) -> None:
        subprocess.run(
            ["git", *args], cwd=self.root, check=True, capture_output=True, text=True
        )

    def _git_out(self, *args: str) -> str:
        return subprocess.check_output(
            ["git", *args], cwd=self.root, text=True
        ).strip()

    def _check(self, root: Path | None = None, *, operation: str = "reserve") -> None:
        harness_transition._validate_security_integration_checkout(
            self.plan,
            self.run,
            self.node,
            root if root is not None else self.root,
            operation=operation,
        )

    def test_reservation_rejects_wrong_root(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaisesRegex(ManifestError, "observed parent worktree"):
                self._check(Path(other))

    def test_reservation_rejects_detached_or_wrong_branch(self) -> None:
        self._git("checkout", "--detach", "HEAD")
        with self.assertRaisesRegex(ManifestError, "detached HEAD"):
            self._check()

        self._git("switch", "-c", "wrong-security-branch")
        with self.assertRaisesRegex(ManifestError, "not the integration branch"):
            self._check()

    def test_reservation_rejects_head_drift_and_dirty_checkout(self) -> None:
        source = self.root / "src" / "example" / "app.py"
        source.write_text("print('drifted')\n", encoding="utf-8")
        self._git("add", "src/example/app.py")
        self._git("commit", "-qm", "drift")
        with self.assertRaisesRegex(ManifestError, "current integration head"):
            self._check()

        self.run["integration"]["integration_head_sha"] = self._git_out("rev-parse", "HEAD")
        source.write_text("print('dirty')\n", encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "product tree is dirty"):
            self._check()

    def test_record_rechecks_drift_after_a_successful_reservation_check(self) -> None:
        self._check(operation="reserve")
        source = self.root / "src" / "example" / "app.py"
        source.write_text("print('changed after reserve')\n", encoding="utf-8")
        with self.assertRaisesRegex(ManifestError, "product tree is dirty"):
            self._check(operation="record")


if __name__ == "__main__":
    unittest.main()

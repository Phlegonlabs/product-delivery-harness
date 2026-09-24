import copy
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = SKILL_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import inspect_harness_run


class InspectParentDriftTests(unittest.TestCase):
    def git(self, root: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()

    def init_repo(self, root: Path) -> str:
        self.git(root, "init", "-q", "-b", "runtime-repair")
        self.git(root, "config", "user.email", "tests@example.invalid")
        self.git(root, "config", "user.name", "Harness Tests")
        (root / "tracked.txt").write_text("first\n", encoding="utf-8")
        self.git(root, "add", "tracked.txt")
        self.git(root, "commit", "-q", "-m", "first")
        return self.git(root, "rev-parse", "HEAD")

    def advance_repo(self, root: Path) -> str:
        (root / "tracked.txt").write_text("second\n", encoding="utf-8")
        self.git(root, "add", "tracked.txt")
        self.git(root, "commit", "-q", "-m", "second")
        return self.git(root, "rev-parse", "HEAD")

    def run_state(self, integration_head: str) -> dict:
        return {
            "schema_version": 11,
            "run_id": "RUN-PARENT",
            "status": "running",
            "integration": {
                "branch": "refs/heads/runtime-repair",
                "integration_head_sha": integration_head,
            },
            "observed": {
                "git": {
                    "parent_worktree_path": "recorded-parent",
                    "parent_branch": "runtime-repair",
                    "parent_head_sha": integration_head,
                    "parent_dirty": False,
                }
            },
            "mission_states": {},
            "workers": [],
        }

    def test_aligned_parent_reports_exact_identity_without_mutating_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            run = self.run_state(head)
            original = copy.deepcopy(run)

            summary = inspect_harness_run.summarize_run(root, run)

        parent = summary["parent_git"]
        self.assertEqual("aligned", parent["comparison_state"])
        self.assertEqual("runtime-repair", parent["live_branch"])
        self.assertEqual(head, parent["live_head_sha"])
        self.assertTrue(parent["integration_object_exists"])
        self.assertTrue(parent["branch_matches_integration"])
        self.assertTrue(parent["head_matches_integration"])
        self.assertFalse(parent["needs_reconciliation"])
        self.assertEqual("unknown", parent["runtime_process_liveness"])
        self.assertEqual([], summary["warnings"])
        self.assertEqual(original, run)
        self.assertIn("Parent Git: aligned", inspect_harness_run.render_text(summary))

    def test_advanced_parent_head_is_a_warning_and_keeps_exit_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            integration_head = self.init_repo(root)
            live_head = self.advance_repo(root)
            run = self.run_state(integration_head)

            summary = inspect_harness_run.summarize_run(root, run)
            with patch.object(inspect_harness_run, "load_run", return_value=run):
                with redirect_stdout(io.StringIO()):
                    exit_code = inspect_harness_run.main(
                        ["--repo-root", str(root), "--run", str(root / "RUN.md")]
                    )

        parent = summary["parent_git"]
        self.assertEqual("mismatch", parent["comparison_state"])
        self.assertEqual(live_head, parent["live_head_sha"])
        self.assertTrue(parent["integration_object_exists"])
        self.assertTrue(parent["branch_matches_integration"])
        self.assertFalse(parent["head_matches_integration"])
        self.assertEqual(
            [
                "parent: live HEAD "
                f"{live_head} differs from integration head {integration_head}"
            ],
            summary["warnings"],
        )
        self.assertEqual(1, exit_code)

    def test_missing_canonical_integration_object_is_explicit(self) -> None:
        missing = "f" * 40
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            live_head = self.init_repo(root)
            summary = inspect_harness_run.summarize_run(root, self.run_state(missing))

        parent = summary["parent_git"]
        self.assertFalse(parent["integration_object_exists"])
        self.assertFalse(parent["head_matches_integration"])
        self.assertIn(
            f"parent: live HEAD {live_head} differs from integration head {missing}",
            summary["warnings"],
        )
        self.assertIn(
            f"parent: canonical integration object {missing} is missing locally",
            summary["warnings"],
        )
        self.assertIn(
            "integration_object=missing", inspect_harness_run.render_text(summary)
        )

    def test_missing_integration_head_still_compares_recorded_parent_head(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            recorded_parent_head = self.init_repo(root)
            live_head = self.advance_repo(root)
            run = self.run_state(recorded_parent_head)
            run["integration"]["integration_head_sha"] = None

            summary = inspect_harness_run.summarize_run(root, run)

        parent = summary["parent_git"]
        self.assertIsNone(parent["integration_head_sha"])
        self.assertIsNone(parent["head_matches_integration"])
        self.assertFalse(parent["head_matches_recorded_parent"])
        self.assertIsNone(parent["integration_object_exists"])
        self.assertEqual("mismatch", parent["comparison_state"])
        self.assertIn(
            "parent: live HEAD "
            f"{live_head} differs from recorded parent head {recorded_parent_head}",
            summary["warnings"],
        )

    def test_unavailable_git_is_unknown_instead_of_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = inspect_harness_run.summarize_run(
                root, self.run_state("a" * 40)
            )

        parent = summary["parent_git"]
        self.assertEqual("unknown", parent["comparison_state"])
        self.assertIsNone(parent["live_branch"])
        self.assertIsNone(parent["live_head_sha"])
        self.assertIsNone(parent["live_dirty"])
        self.assertIsNone(parent["integration_object_exists"])
        self.assertFalse(parent["needs_reconciliation"])
        self.assertEqual([], summary["warnings"])

    def test_guarded_git_configuration_is_a_bounded_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            head = self.init_repo(root)
            self.git(root, "config", "core.hookspath", ".githooks")
            run = self.run_state(head)

            summary = inspect_harness_run.summarize_run(root, run)
            with patch.object(inspect_harness_run, "load_run", return_value=run):
                with redirect_stdout(io.StringIO()):
                    exit_code = inspect_harness_run.main(
                        ["--repo-root", str(root), "--run", str(root / "RUN.md")]
                    )

        parent = summary["parent_git"]
        self.assertEqual("blocked", parent["comparison_state"])
        self.assertEqual("blocked", parent["git_observation_status"])
        self.assertTrue(parent["needs_reconciliation"])
        self.assertEqual(
            ["parent: Git observation blocked by metadata/configuration guard"],
            summary["warnings"],
        )
        self.assertNotIn(".githooks", " ".join(summary["warnings"]))
        self.assertEqual(1, exit_code)

    def test_integrated_worker_drift_remains_historical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            historical_head = self.init_repo(root)
            integration_head = self.advance_repo(root)
            run = self.run_state(integration_head)
            run["mission_states"] = {
                "M1": {"phase": "integrated", "head_sha": historical_head}
            }
            run["workers"] = [{"mission_id": "M1", "worktree_path": str(root)}]

            summary = inspect_harness_run.summarize_run(root, run)

        mission = summary["missions"][0]
        self.assertTrue(mission["needs_reconciliation"])
        self.assertEqual("superseded_or_historical", mission["drift_class"])
        self.assertEqual(
            ["M1: superseded or historical head drift"], summary["warnings"]
        )
        self.assertNotEqual("active", mission["drift_class"])
        self.assertEqual("aligned", summary["parent_git"]["comparison_state"])


if __name__ == "__main__":
    unittest.main()

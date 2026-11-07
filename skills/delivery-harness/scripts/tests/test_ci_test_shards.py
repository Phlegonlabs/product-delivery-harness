from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ci_test_shards import SERIAL_FILES, CommandError, candidate_files, discover_files, run_suite, split_files


class CITestShardTests(unittest.TestCase):
    def test_split_is_round_robin_over_sorted_files_without_overlap(self) -> None:
        files = ["a.py", "b.py", "c.py", "d.py", "e.py"]
        shards = split_files(files, 2)
        self.assertEqual([["a.py", "c.py", "e.py"], ["b.py", "d.py"]], shards)
        self.assertEqual(files, sorted(name for shard in shards for name in shard))

    def test_zero_shards_are_rejected(self) -> None:
        with self.assertRaises(CommandError):
            split_files(["a.py"], 0)

    def test_native_platforms_select_only_the_explicit_list(self) -> None:
        discovered = ["tests/test_harness_git.py", "tests/test_unrelated.py"]
        with self.assertRaises(CommandError) as context:
            candidate_files("harness", "windows", discovered)
        self.assertIn("no longer discovered", str(context.exception))
        self.assertEqual(discovered, candidate_files("harness", "linux", discovered))
        self.assertEqual(discovered, candidate_files("ui", "windows", discovered))

    def test_discovery_requires_the_suite_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(CommandError):
                discover_files(Path(temporary), "harness")

    def test_native_discovery_keeps_publication_coverage_after_helper_retirement(self) -> None:
        discovered = [
            name for name in discover_files(SCRIPTS_DIR.parents[2], "harness")
            if Path(name).name != "test_trusted_host_publication.py"
        ]
        for platform in ("windows", "macos"):
            with self.subTest(platform=platform):
                selected = {
                    Path(name).name
                    for name in candidate_files("harness", platform, discovered)
                }
                self.assertIn("test_push_archived_candidate.py", selected)
                self.assertNotIn("test_trusted_host_publication.py", selected)

    def test_native_discovery_keeps_current_safety_and_host_journeys(self) -> None:
        discovered = discover_files(SCRIPTS_DIR.parents[2], "harness")
        for platform in ("windows", "macos"):
            with self.subTest(platform=platform):
                selected = [Path(name).name for name in candidate_files("harness", platform, discovered)]
                for required in ("test_conditional_review_journey.py", "test_current_host_admission.py",
                                 "test_document_write.py", "test_worktree_path_identity.py"):
                    self.assertEqual(1, selected.count(required))


if __name__ == "__main__":
    unittest.main()


def _module(body_lines: list[str]) -> str:
    return "\n".join(["import unittest", "", "", "class T(unittest.TestCase):", *body_lines, ""])


class RunSuiteTests(unittest.TestCase):
    def test_run_suite_runs_modules_in_parallel_and_reports_failures(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / "skills/design-system-compiler/scripts/tests"
            tests.mkdir(parents=True)
            (tests / "test_alpha.py").write_text(
                _module(["    def test_ok(self):", "        self.assertTrue(True)"]), encoding="utf-8"
            )
            (tests / "test_beta.py").write_text(
                _module(["    def test_bad(self):", "        self.fail('expected')"]), encoding="utf-8"
            )
            log_dir = root / "logs"
            self.assertEqual(1, run_suite(root, "design-system", 2, log_dir))
            self.assertIn("expected", (log_dir / "test_beta.py.log").read_text(encoding="utf-8"))
            (tests / "test_beta.py").write_text(
                _module(["    def test_ok(self):", "        pass"]), encoding="utf-8"
            )
            self.assertEqual(0, run_suite(root, "design-system", 2, log_dir))

    def test_run_suite_rejects_zero_workers(self) -> None:
        from pathlib import Path

        with self.assertRaises(CommandError):
            run_suite(Path("."), "design-system", 0, Path("unused"))

    def test_install_script_module_runs_serially(self) -> None:
        self.assertIn("test_install_script.py", SERIAL_FILES)


def _git_repo(root: Path) -> str:
    import subprocess

    (root / "skills").mkdir()
    (root / "skills" / "a.txt").write_text("a\n", encoding="utf-8")
    for command in (["init", "-q"], ["add", "-A"],
                    ["-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "c"]):
        subprocess.run(["git", *command], cwd=root, check=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()


class MatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        import argparse

        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name) / "repo"
        self.root.mkdir()
        self.head = _git_repo(self.root)
        self.args = lambda log: argparse.Namespace(base="HEAD", log_dir=str(log), workers=2)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def summary(self, log: Path) -> list[str]:
        return (log / "summary.txt").read_text(encoding="utf-8").splitlines()

    def test_steps_require_browsers_golden_path_and_a_ranged_diff(self) -> None:
        import ci_test_shards

        steps = ci_test_shards.matrix_steps(self.root, "b" * 40)
        self.assertEqual(
            ["check_skill_spec", "pyflakes", "docs_weight", "harness", "golden_path",
             "product", "ui", "design-system", "diff_check"],
            [name for name, _, _ in steps],
        )
        by_name = {name: (command, env) for name, command, env in steps}
        self.assertIsNone(by_name["harness"][0])
        self.assertEqual({"HARNESS_GOLDEN_PATH": "1"}, by_name["golden_path"][1])
        for name in ("ui", "design-system"):
            self.assertEqual("1", by_name[name][1]["PDH_REQUIRE_BROWSER_TESTS"])
            self.assertEqual(str(self.root / "node_modules" / "playwright"), by_name[name][1]["PLAYWRIGHT_MODULE"])
        self.assertEqual(["git", "diff", "--check", "b" * 40, "HEAD"], by_name["diff_check"][0])
        self.assertEqual(4, len([part for part in by_name["pyflakes"][0] if part.startswith("skills/")]))

    def test_summary_records_every_step_and_any_failure_fails_the_run(self) -> None:
        from unittest import mock

        import ci_test_shards

        python = sys.executable
        steps = [
            ("env", [python, "-c", "import os, sys; sys.exit(os.environ['X'] != '1')"], {"X": "1"}),
            ("harness", None, {}),
            ("bad", [python, "-c", "raise SystemExit(3)"], {}),
        ]
        log = Path(self._temp.name) / "fail"
        with mock.patch.object(ci_test_shards, "matrix_steps", return_value=steps), \
                mock.patch.object(ci_test_shards, "run_suite", return_value=0):
            self.assertEqual(1, ci_test_shards.run_matrix(self.root, self.args(log)))
        lines = self.summary(log)
        self.assertEqual([f"head: {self.head}", f"base: {self.head}", "dirty: no"], lines[:3])
        self.assertEqual(["env exit=0", "harness exit=0", "bad exit=3"], [line.split(" seconds=")[0] for line in lines[3:6]])
        self.assertEqual("result: fail", lines[-1])
        self.assertTrue((log / "bad.log").is_file())

        log = Path(self._temp.name) / "pass"
        with mock.patch.object(ci_test_shards, "matrix_steps", return_value=steps[:2]), \
                mock.patch.object(ci_test_shards, "run_suite", return_value=0):
            self.assertEqual(0, ci_test_shards.run_matrix(self.root, self.args(log)))
        self.assertEqual("result: pass", self.summary(log)[-1])

    def test_an_interrupted_run_says_so(self) -> None:
        from unittest import mock

        import ci_test_shards

        log = Path(self._temp.name) / "stop"
        with mock.patch.object(ci_test_shards, "matrix_steps", return_value=[("harness", None, {})]), \
                mock.patch.object(ci_test_shards, "run_suite", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                ci_test_shards.run_matrix(self.root, self.args(log))
        self.assertEqual("result: interrupted", self.summary(log)[-1])

    def test_bad_arguments_exit_2_before_any_step(self) -> None:
        import subprocess

        script = SCRIPTS_DIR / "ci_test_shards.py"
        used = Path(self._temp.name) / "used"
        used.mkdir()
        (used / "summary.txt").write_text("old\n", encoding="utf-8")
        for extra in (["--base", "no-such-commit", "--log-dir", "new1"],
                      ["--base", "HEAD", "--log-dir", "new2", "--workers", "0"],
                      ["--base", "HEAD", "--log-dir", str(used)],
                      ["--log-dir", "new3"]):
            with self.subTest(arguments=extra):
                completed = subprocess.run(
                    [sys.executable, str(script), "--repo-root", str(self.root), "matrix", *extra],
                    cwd=self._temp.name, capture_output=True, text=True,
                )
                self.assertEqual(2, completed.returncode, completed.stderr)
        self.assertEqual("old\n", (used / "summary.txt").read_text(encoding="utf-8"))
        self.assertFalse((Path(self._temp.name) / "new1").exists())

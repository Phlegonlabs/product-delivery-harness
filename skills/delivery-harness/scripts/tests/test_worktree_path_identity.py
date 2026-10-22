"""Real worktree aliases exercise the retained worker-context join."""

import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import harness_manifest as manifest  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
from verifier_runtime import execution_key_from_document  # noqa: E402


class WorktreePathIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.container = Path(self.temp.name)
        self.root = self.container / "integration"
        self.root.mkdir()
        self.head = mf.init_repo(self.root, "README.md", default_branch="integration")
        self.checkout = self.container / "MixedCaseWorktree"
        mf.git(self.root, "worktree", "add", "-qb", "worker-M1", str(self.checkout), self.head)
        self.plan = mf.valid_plan()
        self.run = mf.valid_closeout_run(self.plan)
        mf.mark_complete(self.plan, self.run)
        self.run["mission_states"]["M1"]["phase"] = "worker_passed"
        worker = next(item for item in self.run["workers"] if item["mission_id"] == "M1")
        old_path = worker["worktree_path"]
        worker.update(worktree_path=str(self.checkout), branch_ref="refs/heads/worker-M1", worker_head_sha=self.head)
        self.observed = next(item for item in self.run["observed"]["git"]["worktrees"] if item["path"] == old_path)
        self.observed.update(path=str(self.checkout), branch_ref=worker["branch_ref"], head_sha=self.head)
        for execution in self.run["verifier_executions"]:
            if execution["mission_id"] != "M1" or execution["layer"] not in {"task", "worker"}:
                continue
            execution["context"]["head_sha"] = self.head
            execution["key_document"]["head_sha"] = self.head
            guard = execution["git_guard_attestation"]
            guard.update(checkout_root=str(self.checkout), source_head_sha=self.head)
            guard["git_guard"].update(expected_branch="worker-M1", expected_head_sha=self.head)
            execution["execution_key"] = execution_key_from_document(execution["key_document"])
            execution["evidence_key"] = execution["execution_key"]
        self.assertEqual([], self.errors())

    def errors(self):
        errors = []
        manifest._validate_verifier_executions(errors, self.plan, self.run)
        return errors

    def assert_alias(self, alias):
        self.assertTrue(os.path.samefile(self.checkout, alias), "controlled example must identify the same actual worktree")
        self.observed["path"] = str(alias)
        self.assertEqual([], self.errors())

    def test_existing_dot_segment_alias_matches(self):
        intermediate = self.container / "intermediate"
        intermediate.mkdir()
        self.assert_alias(str(intermediate) + os.sep + ".." + os.sep + self.checkout.name)

    @unittest.skipUnless(os.name == "nt", "Windows path spelling")
    def test_windows_slash_and_case_aliases_match(self):
        for alias in (self.checkout.as_posix(), str(self.checkout).swapcase()):
            with self.subTest(alias=alias):
                self.assert_alias(alias)

    @unittest.skipUnless(os.name == "nt", "Windows short-name alias")
    def test_windows_short_name_alias_matches_when_available(self):
        import ctypes
        buffer = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetShortPathNameW(str(self.checkout), buffer, len(buffer))
        if not length or buffer.value == str(self.checkout):
            self.skipTest("filesystem has no distinct short-name alias")
        self.assert_alias(buffer.value)

    def test_other_worktree_or_repository_never_matches(self):
        other = self.container / "other-worktree"
        mf.git(self.root, "worktree", "add", "-qb", "other-worker", str(other), self.head)
        separate = self.container / "separate-repository"
        separate.mkdir()
        mf.init_repo(separate, "README.md", default_branch="worker-M1")
        for path in (other, self.root, separate):
            with self.subTest(path=path):
                self.observed["path"] = str(path)
                self.assertTrue(any("one matching parent-observed worktree" in error for error in self.errors()))

    def test_wrong_branch_head_dirty_and_duplicate_observations_are_rejected(self):
        original = copy.deepcopy(self.observed)
        for mutation in ("branch", "head", "dirty", "duplicate"):
            with self.subTest(mutation=mutation):
                self.observed.clear()
                self.observed.update(original)
                if mutation == "branch": self.observed["branch_ref"] = "refs/heads/integration"
                elif mutation == "head": self.observed["head_sha"] = "f" * 40
                elif mutation == "dirty": self.observed["dirty"] = True
                else: self.run["observed"]["git"]["worktrees"].append(copy.deepcopy(self.observed))
                self.assertTrue(self.errors())

    def test_reparse_alias_is_rejected(self):
        alias = self.container / "linked-worktree"
        if os.name == "nt":
            result = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-Command",
                "New-Item -ItemType Junction -Path $env:PDH_ALIAS_LINK -Target $env:PDH_ALIAS_TARGET -ErrorAction Stop | Out-Null"],
                env={**os.environ, "PDH_ALIAS_LINK": str(alias), "PDH_ALIAS_TARGET": str(self.checkout)},
                capture_output=True, text=True, timeout=15)
            self.assertEqual(0, result.returncode, result.stderr)
        else:
            alias.symlink_to(self.checkout, target_is_directory=True)
        self.assertTrue(os.path.samefile(self.checkout, alias))
        self.observed["path"] = str(alias)
        self.assertTrue(any("one matching parent-observed worktree" in error for error in self.errors()))

    def test_malformed_paths_do_not_escape_validation(self):
        for invalid in (None, "", [], "bad\x00path"):
            with self.subTest(path=invalid):
                self.assertFalse(manifest.same_worktree_path(invalid, str(self.checkout)))


if __name__ == "__main__":
    unittest.main()

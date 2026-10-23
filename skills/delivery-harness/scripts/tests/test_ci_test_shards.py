from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ci_test_shards import CommandError, candidate_files, discover_files, split_files


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

from __future__ import annotations

import sys
import subprocess
import json
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ci_test_shards import balance_files, candidate_files, discover_files


SCRIPT = SCRIPTS_DIR / "ci_test_shards.py"


def find_repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / ".github/workflows/harness-ci.yml").is_file():
            return candidate
    raise AssertionError("source workflow is unavailable")


class CICandidateGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = find_repo_root()
        self.workflow = (self.repo_root / ".github/workflows/harness-ci.yml").read_text(
            encoding="utf-8"
        )

    def test_feature_push_and_pr_do_not_duplicate_ci(self) -> None:
        trigger = self.workflow.split("jobs:", 1)[0]
        self.assertIn("pull_request:", trigger)
        self.assertIn("merge_group:", trigger)
        self.assertIn("- main", trigger)
        self.assertNotIn("- development", trigger)
        self.assertNotIn("- '**'", trigger)

    def test_all_events_share_one_canonical_candidate(self) -> None:
        self.assertIn(
            "CANDIDATE_SHA: ${{ inputs.candidate_sha || github.event.pull_request.head.sha || github.sha }}",
            self.workflow,
        )
        self.assertEqual(10, self.workflow.count("ref: ${{ env.CANDIDATE_SHA }}"))
        self.assertEqual(7, self.workflow.count('test "$(git rev-parse HEAD)" = "$CANDIDATE_SHA"'))
        self.assertEqual(2, self.workflow.count('-ne $env:CANDIDATE_SHA'))
        self.assertIn("Full 40-character commit SHA", self.workflow)
        self.assertIn("^[0-9a-f]{40}$", self.workflow)

    def test_release_concurrency_is_frozen_by_candidate_sha(self) -> None:
        concurrency = self.workflow.split("concurrency:", 1)[1].split("env:", 1)[0]
        self.assertIn("inputs.candidate_sha", concurrency)
        self.assertIn("format('pr-{0}', github.event.pull_request.number)", concurrency)
        self.assertIn("github.ref", concurrency)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", concurrency)

    def test_diff_uses_actual_event_base(self) -> None:
        self.assertIn("github.event.pull_request.base.sha", self.workflow)
        self.assertIn("github.event.merge_group.base_sha", self.workflow)
        self.assertIn("base_sha:", self.workflow)
        self.assertIn("Full 40-character ancestor commit", self.workflow)
        self.assertIn("required: true", self.workflow)
        self.assertIn(
            "github.event_name == 'workflow_dispatch' && inputs.base_sha ||",
            self.workflow,
        )
        self.assertIn("ci_diff_base.py resolve", self.workflow)
        self.assertIn('git diff --check "$diff_base" "$actual_sha"', self.workflow)
        self.assertNotIn("origin/$GITHUB_REF_NAME...HEAD", self.workflow)
        self.assertNotIn('base="origin/main"', self.workflow)
        self.assertNotIn("        git diff --check\n", self.workflow)

    def test_validate_requires_every_matrix_result(self) -> None:
        validate = self.workflow.split("\n  validate:\n", 1)[1]
        required_jobs = [
            "quality",
            "linux-harness",
            "linux-other",
            "linux-browser",
            "golden-path",
            "macos-harness",
            "macos-other",
            "windows-native",
            "windows-installer",
        ]
        for job in required_jobs:
            with self.subTest(job=job):
                self.assertIn(f"- {job}", validate)
                self.assertIn(f"_RESULT: ${{{{ needs.{job}.result }}}}", validate)
        self.assertIn("if: always()", validate)
        self.assertIn("ci_test_shards.py gate", validate)

    def test_browser_and_macos_suite_coverage_matches_original_matrix(self) -> None:
        linux_browser = self.workflow.split("\n  linux-browser:\n", 1)[1].split(
            "\n  golden-path:\n", 1
        )[0]
        linux_other = self.workflow.split("\n  linux-other:\n", 1)[1].split(
            "\n  linux-browser:\n", 1
        )[0]
        macos_other = self.workflow.split("\n  macos-other:\n", 1)[1].split(
            "\n  windows-native:\n", 1
        )[0]
        for env in ("PDH_REQUIRE_BROWSER_TESTS: \"1\"", "PLAYWRIGHT_MODULE:"):
            self.assertIn(env, linux_browser)
        self.assertIn("skills/ui-design-builder/scripts/tests -v", linux_browser)
        self.assertIn("skills/design-system-compiler/scripts/tests -v", linux_browser)
        self.assertNotIn("skills/design-system-compiler/scripts/tests -v", linux_other)
        self.assertIn("skills/ui-design-builder/scripts/tests -v", macos_other)
        self.assertNotIn("PDH_REQUIRE_BROWSER_TESTS", macos_other)

    def test_posix_shards_discover_harness_files_exactly_once(self) -> None:
        discovered = discover_files(self.repo_root, "harness")
        timings = {
            name: float(index + 1)
            for index, name in enumerate(sorted(discovered, reverse=True))
        }
        shards = balance_files(discovered, timings, 4)
        planned = [name for shard in shards for name in shard]
        self.assertEqual(discovered, sorted(planned))
        self.assertEqual(len(discovered), len(set(planned)))
        self.assertEqual(4, len(shards))
        self.assertTrue(all(shards))

    def test_actual_repository_plans_cover_discovered_files(self) -> None:
        discovered = {Path(name).name for name in discover_files(self.repo_root, "harness")}
        planned: set[str] = set()
        for platform in ("linux", "macos"):
            for shard_index in range(4):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--repo-root",
                        str(self.repo_root),
                        "plan",
                        "--suite",
                        "harness",
                        "--platform",
                        platform,
                        "--shard-count",
                        "4",
                        "--shard-index",
                        str(shard_index),
                        "--timings",
                        str(self.repo_root / "skills/delivery-harness/ci-test-timings.json"),
                        "--allow-unmeasured",
                        "--format",
                        "names",
                    ],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=30,
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                names = [name for name in result.stdout.splitlines() if name]
                self.assertTrue(names)
                self.assertEqual(len(names), len(set(names)))
                planned.update(names)
        self.assertEqual(discovered, planned)

    def test_actual_windows_plan_selects_the_explicit_native_set(self) -> None:
        planned: set[str] = set()
        for shard_index in range(4):
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo-root",
                    str(self.repo_root),
                    "plan",
                    "--suite",
                    "harness",
                    "--platform",
                    "windows",
                    "--shard-count",
                    "4",
                    "--shard-index",
                    str(shard_index),
                    "--timings",
                    str(self.repo_root / "skills/delivery-harness/ci-test-timings.json"),
                    "--allow-unmeasured",
                    "--format",
                    "names",
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            names = [name for name in result.stdout.splitlines() if name]
            self.assertTrue(names)
            self.assertEqual(len(names), len(set(names)))
            planned.update(names)
        selected = {Path(name).name for name in candidate_files(
            self.repo_root, "harness", "windows", discover_files(self.repo_root, "harness")
        )}
        self.assertEqual(13, len(selected))
        self.assertEqual(selected, planned)

    def test_workflow_launches_a_positive_count_for_every_shard_file(self) -> None:
        self.assertEqual(2, self.workflow.count("grep -Eq '^Ran [1-9][0-9]* tests?'"))
        self.assertEqual(2, self.workflow.count("suite_status=\"${PIPESTATUS[0]}\""))
        self.assertNotIn('suite_output="$(', self.workflow)
        self.assertNotIn("$suiteOutput = & python", self.workflow)
        windows_step = self.workflow.split("Run measured native Harness shard", 1)[1].split(
            "  windows-installer:", 1
        )[0]
        self.assertIn("$planJson = python", windows_step)
        self.assertIn("$plannerStatus = $LASTEXITCODE", windows_step)
        self.assertIn("if ($plannerStatus -ne 0) {", windows_step)
        self.assertIn("$plan = $planJson | ConvertFrom-Json", windows_step)
        self.assertLess(
            windows_step.index("$plannerStatus = $LASTEXITCODE"),
            windows_step.index("$plan = $planJson | ConvertFrom-Json"),
        )
        self.assertLess(
            windows_step.index("if ($plannerStatus -ne 0) {"),
            windows_step.index("$plan = $planJson | ConvertFrom-Json"),
        )
        self.assertIn("& python -m unittest discover", windows_step)
        self.assertIn("*> $suiteLog", windows_step)
        self.assertIn(
            "Select-String -LiteralPath $suiteLog -Pattern '^Ran [1-9][0-9]* tests?' -Quiet",
            windows_step,
        )
        self.assertLess(
            windows_step.index("$suiteSummary = Get-Content"),
            windows_step.index("$hasRunSummary = Select-String"),
        )
        self.assertLess(
            windows_step.index("$suiteStatus = $LASTEXITCODE"),
            windows_step.index("if ($suiteStatus -ne 0) {"),
        )
        self.assertIn("throw \"discovered test file ran zero tests: $testFile\"", self.workflow)
        self.assertIn("^Ran [1-9][0-9]* tests?", self.workflow)

    def test_planned_failing_file_executes_and_fails_the_pipeline(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            test_dir = root / "skills/delivery-harness/scripts/tests"
            test_dir.mkdir(parents=True)
            (root / "timings.json").write_text(
                json.dumps({"version": 1, "timings": {}}), encoding="utf-8"
            )
            (test_dir / "test_boom.py").write_text(
                "import unittest\n"
                "class Boom(unittest.TestCase):\n"
                "    def test_fails(self) -> None:\n"
                "        self.fail('coverage proof')\n",
                encoding="utf-8",
            )
            plan = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo-root",
                    str(root),
                    "plan",
                    "--suite",
                    "harness",
                    "--platform",
                    "linux",
                    "--shard-count",
                    "1",
                    "--shard-index",
                    "0",
                    "--timings",
                    str(root / "timings.json"),
                    "--allow-unmeasured",
                    "--format",
                    "names",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
                check=False,
            )
            self.assertEqual(0, plan.returncode, plan.stderr)
            self.assertEqual(["test_boom.py"], plan.stdout.splitlines())
            run = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    str(test_dir),
                    "-p",
                    "test_boom.py",
                    "-v",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertNotEqual(0, run.returncode)
            self.assertIn("Ran 1 test", run.stderr)
            self.assertIn("FAILED", run.stderr)

    def test_windows_native_shard_set_is_explicit_and_complete(self) -> None:
        discovered = discover_files(self.repo_root, "harness")
        selected = candidate_files(self.repo_root, "harness", "windows", discovered)
        timings = {name: 1.0 for name in selected}
        shards = balance_files(selected, timings, 4)
        planned = [name for shard in shards for name in shard]
        self.assertEqual(13, len(selected))
        self.assertEqual(sorted(selected), sorted(planned))
        self.assertTrue(all(shards))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import subprocess
import unittest
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ci_test_shards import candidate_files, discover_files, split_files


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

    def test_one_run_per_candidate_without_push_events(self) -> None:
        trigger = self.workflow.split("jobs:", 1)[0]
        self.assertIn("pull_request:", trigger)
        self.assertIn("merge_group:", trigger)
        self.assertIn("workflow_dispatch:", trigger)
        self.assertNotIn("push:", trigger)
        self.assertNotIn("- main", trigger)

    def test_all_events_share_one_canonical_candidate(self) -> None:
        self.assertIn(
            "CANDIDATE_SHA: ${{ inputs.candidate_sha || github.event.pull_request.head.sha || github.sha }}",
            self.workflow,
        )
        jobs = yaml.safe_load(self.workflow)["jobs"]
        # Every job except the aggregate checks out and verifies the candidate.
        self.assertEqual(len(jobs) - 1, self.workflow.count("ref: ${{ env.CANDIDATE_SHA }}"))
        self.assertEqual(5, self.workflow.count('test "$(git rev-parse HEAD)" = "$CANDIDATE_SHA"'))
        self.assertEqual(1, self.workflow.count('-ne $env:CANDIDATE_SHA'))
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
        self.assertIn('git merge-base "$DIFF_BASE_SHA" "$actual_sha"', self.workflow)
        self.assertNotIn("github.event.before", self.workflow)
        self.assertNotIn("ci_diff_base", self.workflow)
        self.assertIn('git diff --check "$diff_base" "$actual_sha"', self.workflow)
        self.assertNotIn("origin/$GITHUB_REF_NAME...HEAD", self.workflow)
        self.assertNotIn('base="origin/main"', self.workflow)
        self.assertNotIn("        git diff --check\n", self.workflow)

    def test_validate_requires_every_job_result(self) -> None:
        jobs = yaml.safe_load(self.workflow)["jobs"]
        validate = jobs["validate"]
        self.assertEqual(
            sorted(name for name in jobs if name != "validate"), sorted(validate["needs"])
        )
        self.assertEqual("always()", validate["if"])
        results = list(validate["steps"][0]["env"].values())
        for job in validate["needs"]:
            with self.subTest(job=job):
                self.assertIn(f"${{{{ needs.{job}.result }}}}", results)
        script = validate["steps"][0]["run"]
        self.assertIn('[ "$result" != success ]', script)
        self.assertIn('exit "$failed"', script)

    def test_pr_run_has_one_macos_job_and_no_installer_job(self) -> None:
        jobs = yaml.safe_load(self.workflow)["jobs"]
        self.assertEqual("macos-latest", jobs["macos-native"]["runs-on"])
        self.assertNotIn("strategy", jobs["macos-native"])
        self.assertEqual([0, 1, 2, 3], jobs["windows-native"]["strategy"]["matrix"]["shard"])
        self.assertEqual([0, 1, 2, 3], jobs["linux-harness"]["strategy"]["matrix"]["shard"])
        self.assertNotIn("windows-installer", jobs)

    def test_browser_and_macos_suite_coverage_matches_original_matrix(self) -> None:
        linux_browser = self.workflow.split("\n  linux-browser:\n", 1)[1].split(
            "\n  golden-path:\n", 1
        )[0]
        linux_other = self.workflow.split("\n  linux-other:\n", 1)[1].split(
            "\n  linux-browser:\n", 1
        )[0]
        macos = self.workflow.split("\n  macos-native:\n", 1)[1].split(
            "\n  windows-native:\n", 1
        )[0]
        for env in ("PDH_REQUIRE_BROWSER_TESTS: \"1\"", "PLAYWRIGHT_MODULE:"):
            self.assertIn(env, linux_browser)
        self.assertIn("skills/ui-design-builder/scripts/tests -v", linux_browser)
        self.assertIn("skills/design-system-compiler/scripts/tests -v", linux_browser)
        self.assertNotIn("skills/design-system-compiler/scripts/tests -v", linux_other)
        self.assertIn("--platform macos", macos)
        self.assertIn("test_golden_path.py", macos)
        self.assertIn("test_check_design_system_pair.py", macos)
        self.assertNotIn("PDH_REQUIRE_BROWSER_TESTS", macos)

    def plan(self, root: Path, platform: str, count: int, index: int) -> list[str]:
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), "--repo-root", str(root), "plan",
                "--suite", "harness", "--platform", platform,
                "--shard-count", str(count), "--shard-index", str(index),
            ],
            cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return [name for name in result.stdout.splitlines() if name]

    def test_linux_shards_cover_every_harness_file_once(self) -> None:
        discovered = {Path(name).name for name in discover_files(self.repo_root, "harness")}
        shards = [self.plan(self.repo_root, "linux", 4, index) for index in range(4)]
        planned = [name for shard in shards for name in shard]
        self.assertEqual(discovered, set(planned))
        self.assertEqual(len(planned), len(set(planned)))
        self.assertTrue(all(shards))

    def test_native_shards_select_the_explicit_native_set(self) -> None:
        selected = {Path(name).name for name in candidate_files(
            "harness", "windows", discover_files(self.repo_root, "harness")
        )}
        self.assertEqual(13, len(selected))
        for platform, count in (("windows", 4), ("macos", 1)):
            with self.subTest(platform=platform):
                planned = [
                    name for index in range(count)
                    for name in self.plan(self.repo_root, platform, count, index)
                ]
                self.assertEqual(selected, set(planned))
                self.assertEqual(len(planned), len(set(planned)))
        self.assertTrue(all(split_files(sorted(selected), 4)))

    def test_workflow_launches_a_positive_count_for_every_shard_file(self) -> None:
        self.assertEqual(2, self.workflow.count("grep -Eq '^Ran [1-9][0-9]* tests?'"))
        self.assertEqual(2, self.workflow.count("suite_status=\"${PIPESTATUS[0]}\""))
        self.assertNotIn('suite_output="$(', self.workflow)
        self.assertNotIn("$suiteOutput = & python", self.workflow)
        windows_step = self.workflow.split("Run native Harness shard", 1)[1].split(
            "      - name: Run native design-system contract", 1
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
            (test_dir / "test_boom.py").write_text(
                "import unittest\n"
                "class Boom(unittest.TestCase):\n"
                "    def test_fails(self) -> None:\n"
                "        self.fail('coverage proof')\n",
                encoding="utf-8",
            )
            self.assertEqual(["test_boom.py"], self.plan(root, "linux", 1, 0))
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


if __name__ == "__main__":
    unittest.main()

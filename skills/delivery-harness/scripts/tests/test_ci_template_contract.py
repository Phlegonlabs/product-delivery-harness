from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


TEMPLATE = (
    Path(__file__).resolve().parents[2]
    / "assets/templates/PROJECT_CI.template.yml"
)


class ProjectCITemplateContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.template = TEMPLATE.read_text(encoding="utf-8")

    def test_feature_pushes_verify_once_through_pull_request(self) -> None:
        triggers = self.template.split("permissions:", 1)[0]
        self.assertIn("pull_request:", triggers)
        self.assertIn("merge_group:", triggers)
        self.assertIn("- main", triggers)
        self.assertNotIn("- development", triggers)
        self.assertIn("workflow_dispatch:", triggers)
        self.assertNotIn("- '**'", triggers)

    def test_manual_release_binds_a_canonical_full_sha(self) -> None:
        self.assertIn("release_sha:", self.template)
        self.assertIn("Full 40-character commit SHA", self.template)
        self.assertIn(
            "CANDIDATE_SHA: ${{ inputs.release_sha || github.event.pull_request.head.sha || github.sha }}",
            self.template,
        )
        self.assertEqual(2, self.template.count("ref: ${{ env.CANDIDATE_SHA }}"))
        self.assertIn("^[0-9a-f]{40}$", self.template)
        self.assertEqual(1, self.template.count('test "$(git rev-parse HEAD)" = "$CANDIDATE_SHA"'))

    def test_release_concurrency_is_frozen_by_sha(self) -> None:
        concurrency = self.template.split("concurrency:", 1)[1].split("env:", 1)[0]
        self.assertIn("inputs.release_sha", concurrency)
        self.assertIn("format('pr-{0}', github.event.pull_request.number)", concurrency)
        self.assertIn("github.ref", concurrency)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", concurrency)

    def test_diff_base_comes_from_the_event(self) -> None:
        self.assertIn("github.event.pull_request.base.sha", self.template)
        self.assertIn("github.event.merge_group.base_sha", self.template)
        self.assertIn("base_sha:", self.template)
        self.assertIn("Full 40-character ancestor commit", self.template)
        self.assertIn("required: true", self.template)
        self.assertIn(
            "github.event_name == 'workflow_dispatch' && inputs.base_sha ||",
            self.template,
        )
        self.assertIn("require_commit() {", self.template)
        self.assertIn("git merge-base \"$event_base\" \"$actual_sha\"", self.template)
        self.assertIn("git mktree </dev/null", self.template)
        self.assertIn('git diff --check "$diff_base" "$actual_sha"', self.template)
        self.assertNotIn("ci_diff_base.py", self.template)
        self.assertNotIn("python skills/", self.template)
        self.assertNotIn("origin/$GITHUB_REF_NAME...HEAD", self.template)
        self.assertNotIn('base="origin/main"', self.template)
        self.assertNotIn("          git diff --check\n", self.template)

    def test_verify_is_a_stable_strict_aggregate(self) -> None:
        verify = self.template.split("\n  verify:\n", 1)[1]
        self.assertIn("needs: [checks, e2e]", verify)
        self.assertIn("if: always()", verify)
        self.assertIn("CHECKS_RESULT: ${{ needs.checks.result }}", verify)
        self.assertIn("E2E_RESULT: ${{ needs.e2e.result }}", verify)
        self.assertIn('[ "$result" != success ]', verify)

    def test_template_stays_consumer_neutral(self) -> None:
        self.assertIn("<verification-command>", self.template)
        self.assertIn("<e2e-command>", self.template)
        self.assertIn("<e2e-artifact-path>", self.template)
        self.assertNotIn("product-delivery-harness/scripts", self.template)
        self.assertNotIn("PDH_REQUIRE_BROWSER_TESTS", self.template)
        self.assertNotIn("claude", self.template.casefold())
        self.assertNotIn("glm-", self.template.casefold())

    def diff_script(self) -> str:
        segment = self.template.split(
            "- name: Check candidate diff against a meaningful base", 1
        )[1]
        block = segment.split("run: |", 1)[1]
        lines = []
        for line in block.splitlines()[1:]:
            if line.strip() and not line.startswith("          "):
                break
            lines.append(line[10:] if len(line) >= 10 else "")
        return "\n".join(lines)

    def run_diff_script(
        self,
        root: Path,
        event: str,
        candidate: str,
        base: str,
    ) -> subprocess.CompletedProcess[str]:
        script_path = root / "template-diff-check.sh"
        script_path.write_text(self.diff_script(), encoding="utf-8", newline="\n")
        bash_candidates = [
            Path(r"C:\Program Files\Git\bin\bash.exe"),
            Path(r"C:\Program Files\Git\usr\bin\bash.exe"),
        ]
        discovered_bash = shutil.which("bash")
        if discovered_bash and "system32" not in discovered_bash.casefold():
            bash_candidates.append(Path(discovered_bash))
        bash = next((path for path in bash_candidates if path.is_file()), None)
        if bash is None:
            self.skipTest("Git bash is required to execute the GitHub shell script")
        environment = os.environ.copy()
        environment.update(
            {
                "GITHUB_EVENT_NAME": event,
                "CANDIDATE_SHA": candidate,
                "DIFF_BASE_SHA": base,
            }
        )
        return subprocess.run(
            [
                str(bash),
                "--noprofile",
                "--norc",
                "-eo",
                "pipefail",
                script_path.as_posix(),
            ],
            cwd=root,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )

    def test_template_diff_script_uses_merge_base_without_skills(self) -> None:
        if shutil.which("bash") is None:
            self.skipTest("bash is required to execute the GitHub shell script")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()

            def git(*arguments: str) -> str:
                result = subprocess.run(
                    ["git", *arguments],
                    cwd=root,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                return result.stdout.strip()

            git("init", "-q", "-b", "main")
            git("config", "user.email", "template@example.com")
            git("config", "user.name", "Template Test")
            (root / "clean.txt").write_text("clean\n", encoding="utf-8", newline="\n")
            git("add", "clean.txt")
            git("commit", "-m", "base")
            base = git("rev-parse", "HEAD")
            git("checkout", "-q", "-b", "candidate")
            (root / "dirty.txt").write_text(
                "candidate with trailing spaces   \n", encoding="utf-8", newline="\n"
            )
            git("add", "dirty.txt")
            git("commit", "-m", "candidate")
            candidate = git("rev-parse", "HEAD")
            git("checkout", "-q", "main")
            (root / "base_only.txt").write_text(
                "advanced on base with trailing spaces   \n",
                encoding="utf-8",
                newline="\n",
            )
            git("add", "base_only.txt")
            git("commit", "-m", "advanced base")
            advanced_base = git("rev-parse", "HEAD")
            git("checkout", "-q", "candidate")

            pull_request = self.run_diff_script(
                root, "pull_request", candidate, advanced_base
            )
            self.assertNotEqual(0, pull_request.returncode)
            self.assertIn("dirty.txt", pull_request.stdout + pull_request.stderr)
            self.assertNotIn("base_only.txt", pull_request.stdout + pull_request.stderr)

            manual_check = self.run_diff_script(root, "workflow_dispatch", candidate, base)
            self.assertNotEqual(0, manual_check.returncode)
            self.assertIn("dirty.txt", manual_check.stdout + manual_check.stderr)
            self.assertNotIn("base_only.txt", manual_check.stdout + manual_check.stderr)

            initial_push = self.run_diff_script(root, "push", candidate, "0" * 40)
            self.assertNotEqual(0, initial_push.returncode)
            self.assertIn("dirty.txt", initial_push.stdout + initial_push.stderr)

            missing_manual = self.run_diff_script(
                root, "workflow_dispatch", candidate, ""
            )
            self.assertNotEqual(0, missing_manual.returncode)
            self.assertIn("requires base_sha", missing_manual.stderr)


if __name__ == "__main__":
    unittest.main()

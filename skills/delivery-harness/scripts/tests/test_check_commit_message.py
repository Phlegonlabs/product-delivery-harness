"""Tests for check_commit_message.py: mechanical commit-convention checks."""

from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_commit_message  # noqa: E402

GOOD_DIRECT = "feat(harness): add commit message check"
GOOD_MANAGED = (
    "feat(auth): implement password login\n"
    "\n"
    "Task: M2/T03\n"
    "Trace: PRD-012, ARCH-004\n"
    "Verified: pnpm test --filter auth (exit 0)\n"
)
GOOD_INTEGRATION = (
    "chore(integration): integrate mission M2\n"
    "\n"
    "Mission: M2\n"
    "Plan-Revision: 3\n"
    "Integrated-Head: 8f14e45fceea167a5a36dedd4bea2543657059\n"
    "Verified: harness verify --mission M2 (exit 0)\n"
)


class CheckCommitMessageTests(unittest.TestCase):
    def run_checker(self, *args: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = check_commit_message.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def check(self, message: str, *extra: str) -> tuple[int, str, str]:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", suffix=".txt", delete=False
        ) as handle:
            handle.write(message)
            path = handle.name
        self.addCleanup(Path(path).unlink, missing_ok=True)
        return self.run_checker("--message-file", path, *extra)

    def test_passing_direct_subject(self) -> None:
        code, out, _err = self.check(GOOD_DIRECT + "\n")
        self.assertEqual(0, code, out)
        self.assertEqual(f"OK: {GOOD_DIRECT}\n", out)

    def test_passing_direct_subject_keeps_trailers_optional(self) -> None:
        code, out, _err = self.check(
            "fix(dashboard): correct save-button copy\n\nTrace: HARNESS\n"
        )
        self.assertEqual(0, code, out)
        self.assertEqual("OK: fix(dashboard): correct save-button copy\n", out)

    def test_check1_subject_without_the_shape(self) -> None:
        code, out, _err = self.check("add a commit message check\n")
        self.assertEqual(1, code, out)
        self.assertEqual(
            ['ERROR: the subject is not in the "<type>(<scope>): <summary>" shape with an '
             'optional "!" directly before the colon. Rewrite the first line as, for example, '
             '"feat(harness): add commit message check".'],
            out.strip().splitlines(),
        )

    def test_check1_subject_prefix_does_not_parse(self) -> None:
        code, out, _err = self.check("feat(harness: add a check\n")
        self.assertEqual(1, code, out)
        self.assertEqual(
            ['ERROR: the subject prefix "feat(harness" does not match "<type>(<scope>)" with '
             'an optional "!" directly before the colon. Rewrite the first line as, for '
             'example, "feat(harness): add commit message check".'],
            out.strip().splitlines(),
        )

    def test_check1_double_bang_rejected(self) -> None:
        code, out, _err = self.check("feat(harness)!!: drop the api\n")
        self.assertEqual(1, code, out)
        self.assertIn('does not match "<type>(<scope>)"', out)

    def test_check2_type_not_allowed(self) -> None:
        code, out, _err = self.check("feature(auth): add login\n")
        self.assertEqual(1, code, out)
        self.assertEqual(
            ['ERROR: type "feature" is not allowed. '
             "Use one of: feat, fix, refactor, test, docs, chore, perf, build, ci."],
            out.strip().splitlines(),
        )

    def test_check3_missing_scope(self) -> None:
        code, out, _err = self.check("feat: add a check\n")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR: the subject has no scope. Add a product or engineering area", out)

    def test_check3_scope_violates_pattern(self) -> None:
        code, out, _err = self.check("feat(Dashboard): fix save\n")
        self.assertEqual(1, code, out)
        self.assertEqual(
            ['ERROR: scope "Dashboard" does not match [a-z0-9][a-z0-9_-]*. Use a lowercase '
             "product or engineering area such as "
             "auth, billing, api, db, dashboard, ui, harness or prd."],
            out.strip().splitlines(),
        )

    def test_check3_scope_that_is_a_filename(self) -> None:
        code, out, _err = self.check("chore(scripts/main.py): tidy imports\n")
        self.assertEqual(1, code, out)
        self.assertEqual(
            ['ERROR: scope "scripts/main.py" contains "." or "/". A scope is a product or '
             "engineering area, not a filename; use an area such as "
             "auth, billing, api, db, dashboard, ui, harness or prd."],
            out.strip().splitlines(),
        )

    def test_check4_subject_over_72_characters(self) -> None:
        prefix = "feat(harness): "
        subject = prefix + "a" * (73 - len(prefix))
        self.assertEqual(73, len(subject))
        code, out, _err = self.check(subject + "\n")
        self.assertEqual(1, code, out)
        self.assertEqual(
            ["ERROR: the subject is 73 characters long; the maximum is 72. Shorten the first "
             "line so the whole subject is 72 characters or fewer."],
            out.strip().splitlines(),
        )

    def test_check4_boundary_72_characters_passes(self) -> None:
        prefix = "feat(harness): "
        subject = prefix + "a" * (72 - len(prefix))
        self.assertEqual(72, len(subject))
        code, out, _err = self.check(subject + "\n")
        self.assertEqual(0, code, out)

    def test_check5_subject_ends_with_period(self) -> None:
        code, out, _err = self.check("feat(harness): add a check.\n")
        self.assertEqual(1, code, out)
        self.assertEqual(
            ["ERROR: the subject ends with a period. Remove the final period from the summary."],
            out.strip().splitlines(),
        )

    def test_check6_empty_summary(self) -> None:
        code, out, _err = self.check("feat(harness):\n")
        self.assertEqual(1, code, out)
        self.assertEqual(
            ["ERROR: the summary is empty. Write an imperative summary after the colon, as in "
             '"feat(harness): add commit message check".'],
            out.strip().splitlines(),
        )

    def test_check7_second_line_not_blank(self) -> None:
        code, out, _err = self.check("feat(harness): add a check\nbody right away\n")
        self.assertEqual(1, code, out)
        self.assertEqual(
            ["ERROR: the second line of the message is not blank. Separate the subject from "
             "the body with one blank line."],
            out.strip().splitlines(),
        )

    def test_check8_breaking_subject_without_paragraph(self) -> None:
        code, out, _err = self.check("feat(api)!: drop the legacy endpoint\n")
        self.assertEqual(1, code, out)
        self.assertEqual(
            ['ERROR: the subject marks a breaking change with "!" but no body paragraph '
             'starts with "BREAKING CHANGE:" followed by text. Add a body paragraph starting '
             'with "BREAKING CHANGE: " that describes what breaks and how to migrate.'],
            out.strip().splitlines(),
        )

    def test_check8_breaking_subject_with_paragraph_passes(self) -> None:
        message = (
            "feat(api)!: drop the legacy endpoint\n"
            "\n"
            "BREAKING CHANGE: the /v1 endpoints are gone; use /v2.\n"
        )
        code, out, _err = self.check(message)
        self.assertEqual(0, code, out)
        self.assertEqual("OK: feat(api)!: drop the legacy endpoint\n", out)

    def test_several_problems_are_reported_together(self) -> None:
        code, out, _err = self.check("feature(Dashboard): Fix the save button.\n")
        self.assertEqual(1, code, out)
        self.assertEqual(3, len(out.strip().splitlines()), out)
        self.assertIn('ERROR: type "feature" is not allowed. '
                      "Use one of: feat, fix, refactor, test, docs, chore, perf, build, ci.",
                      out)
        self.assertIn('ERROR: scope "Dashboard" does not match', out)
        self.assertIn("ERROR: the subject ends with a period.", out)

    def test_a_message_file_is_never_exempt_as_a_merge(self) -> None:
        # Text cannot prove that its commit is a merge.
        for extra in ((), ("--managed",)):
            code, out, _err = self.check("Merge anything\n", *extra)
            self.assertEqual(1, code, out)
            self.assertIn("ERROR: the subject is not in the", out)

    def test_scope_may_hold_an_underscore(self) -> None:
        code, out, _err = self.check("fix(user_profile): restore editing\n")
        self.assertEqual(0, code, out)

    def test_missing_space_after_the_colon(self) -> None:
        code, out, _err = self.check("feat(auth):add login\n")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR: there is no space after the colon.", out)

    def test_empty_breaking_change_marker_is_not_a_paragraph(self) -> None:
        code, out, _err = self.check("feat(api)!: remove legacy\n\nBREAKING CHANGE:\n")
        self.assertEqual(1, code, out)
        self.assertIn('"BREAKING CHANGE:" followed by text', out)

    def test_managed_task_commit_passes(self) -> None:
        code, out, _err = self.check(GOOD_MANAGED, "--managed")
        self.assertEqual(0, code, out)
        self.assertEqual("OK: feat(auth): implement password login\n", out)

    def test_managed_missing_task_trailer(self) -> None:
        message = GOOD_MANAGED.replace("Task: M2/T03\n", "")
        code, out, _err = self.check(message, "--managed")
        self.assertEqual(1, code, out)
        self.assertIn(
            'ERROR: the Task trailer is missing. Add "Task: M2/T03" on its own line.', out
        )

    def test_managed_missing_trace_trailer(self) -> None:
        message = GOOD_MANAGED.replace("Trace: PRD-012, ARCH-004\n", "")
        code, out, _err = self.check(message, "--managed")
        self.assertEqual(1, code, out)
        self.assertIn(
            'ERROR: the Trace trailer is missing. Add "Trace: PRD-012, ARCH-004" on its own '
            "line.", out
        )

    def test_managed_missing_verified_trailer(self) -> None:
        message = GOOD_MANAGED.replace("Verified: pnpm test --filter auth (exit 0)\n", "")
        code, out, _err = self.check(message, "--managed")
        self.assertEqual(1, code, out)
        self.assertIn(
            "ERROR: the Verified trailer is missing. Add "
            '"Verified: pnpm test --filter auth (exit 0)" on its own line.', out
        )

    def test_managed_empty_trailer_value(self) -> None:
        message = GOOD_MANAGED.replace(
            "Verified: pnpm test --filter auth (exit 0)", "Verified:"
        )
        code, out, _err = self.check(message, "--managed")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR: the Verified trailer is empty.", out)

    def test_managed_task_trailer_with_two_ids(self) -> None:
        message = GOOD_MANAGED.replace("Task: M2/T03", "Task: M2/T03, M2/T04")
        code, out, _err = self.check(message, "--managed")
        self.assertEqual(1, code, out)
        self.assertEqual(
            ['ERROR: the Task trailer "M2/T03, M2/T04" holds more than one task ID. Split '
             'the task so each commit holds exactly one task ID, as in "Task: M2/T03".'],
            out.strip().splitlines(),
        )

    def test_managed_two_task_trailer_lines(self) -> None:
        message = GOOD_MANAGED.replace("Task: M2/T03", "Task: M2/T03\nTask: M2/T04")
        code, out, _err = self.check(message, "--managed")
        self.assertEqual(1, code, out)
        self.assertIn(
            "ERROR: the message carries more than one Task trailer. Split the work into "
            "separate tasks so each commit holds exactly one task ID.", out
        )

    def test_managed_integration_commit_passes_without_task(self) -> None:
        code, out, _err = self.check(GOOD_INTEGRATION, "--managed")
        self.assertEqual(0, code, out)
        self.assertEqual("OK: chore(integration): integrate mission M2\n", out)

    def test_managed_integration_commit_missing_mission(self) -> None:
        message = GOOD_INTEGRATION.replace("Mission: M2\n", "")
        code, out, _err = self.check(message, "--managed")
        self.assertEqual(1, code, out)
        self.assertEqual(
            ['ERROR: the Mission trailer is missing. Add "Mission: M2" on its own line.'],
            out.strip().splitlines(),
        )
        self.assertNotIn("Task trailer", out)

    def test_managed_integration_commit_missing_plan_and_head(self) -> None:
        message = GOOD_INTEGRATION.replace("Plan-Revision: 3\n", "").replace(
            "Integrated-Head: 8f14e45fceea167a5a36dedd4bea2543657059\n", ""
        )
        code, out, _err = self.check(message, "--managed")
        self.assertEqual(1, code, out)
        self.assertEqual(2, len(out.strip().splitlines()), out)
        self.assertIn(
            'ERROR: the Plan-Revision trailer is missing. Add "Plan-Revision: 3" on its own '
            "line.", out
        )
        self.assertIn(
            "ERROR: the Integrated-Head trailer is missing. Add "
            '"Integrated-Head: 8f14e45fceea167a5a36dedd4bea2543657059" on its own line.', out
        )

    def test_crlf_message_file_passes(self) -> None:
        message = "fix(dashboard): correct save-button copy\r\n\r\nTrace: HARNESS\r\n"
        code, out, _err = self.check(message)
        self.assertEqual(0, code, out)
        self.assertEqual("OK: fix(dashboard): correct save-button copy\n", out)

    def test_invalid_utf8_message_file_exits_2(self) -> None:
        with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as handle:
            handle.write(b"\xff\xfe not utf-8")
            path = handle.name
        self.addCleanup(Path(path).unlink, missing_ok=True)
        code, _out, err = self.run_checker("--message-file", path)
        self.assertEqual(2, code)
        self.assertIn("cannot read", err)

    def test_missing_message_file_exits_2(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as handle:
            path = Path(handle.name)
        path.unlink()
        code, _out, err = self.run_checker("--message-file", str(path))
        self.assertEqual(2, code)
        self.assertIn("cannot read", err)

    def test_neither_input_exits_2(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:
                check_commit_message.main([])
        self.assertEqual(2, caught.exception.code)
        self.assertIn("exactly one of --message-file or --rev", stderr.getvalue())

    def test_both_inputs_exit_2(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            check_commit_message.main(["--message-file", "x.txt", "--rev", "HEAD"])
        self.assertEqual(2, caught.exception.code)


class RevModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        return result.stdout

    def commit_with_message(self, message: str) -> None:
        with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as handle:
            handle.write(message.encode("utf-8"))
            message_path = handle.name
        self.addCleanup(Path(message_path).unlink, missing_ok=True)
        (self.root / "file.txt").write_text("content\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-F", message_path)

    def run_rev(self, rev: str, *extra: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = check_commit_message.main(
                ["--rev", rev, "--repo-root", str(self.root), *extra]
            )
        return code, stdout.getvalue(), stderr.getvalue()

    def test_rev_reads_a_passing_message_from_git(self) -> None:
        self.commit_with_message("feat(harness): add commit message check\n")
        code, out, _err = self.run_rev("HEAD")
        self.assertEqual(0, code, out)
        self.assertEqual("OK: feat(harness): add commit message check\n", out)

    def test_rev_reports_problems_from_git(self) -> None:
        self.commit_with_message("feature(auth): add login.\n")
        code, out, _err = self.run_rev("HEAD")
        self.assertEqual(1, code, out)
        self.assertIn('ERROR: type "feature" is not allowed.', out)
        self.assertIn("ERROR: the subject ends with a period.", out)

    def test_rev_merge_commit_is_exempt(self) -> None:
        self.commit_with_message("feat(harness): first task\n")
        self.git("checkout", "-q", "-b", "feature-x")
        self.commit_with_message("feat(harness): second task\n")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--no-ff", "--no-edit", "feature-x")
        code, out, _err = self.run_rev("HEAD")
        self.assertEqual(0, code, out)
        self.assertIn("OK (merge commit): Merge", out)
        # A managed integration merge must carry the mission-level body.
        code, out, _err = self.run_rev("HEAD", "--managed")
        self.assertEqual(1, code, out)

    def test_rev_merge_subject_on_an_ordinary_commit_is_checked(self) -> None:
        self.commit_with_message("Merge anything\n")
        code, out, _err = self.run_rev("HEAD")
        self.assertEqual(1, code, out)
        self.assertIn("ERROR: the subject is not in the", out)

    def test_rev_unknown_revision_exits_2(self) -> None:
        code, _out, err = self.run_rev("no-such-revision")
        self.assertEqual(2, code)
        self.assertIn("git log failed for no-such-revision", err)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import subprocess
import json
import os
import re
import shutil
import unittest
from pathlib import Path

import yaml

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


GITHUB_TEMPLATE_PATTERN = re.compile(r"\$\{\{(.*?)\}\}")

GITHUB_TOKEN_PATTERN = re.compile(
    r"""
    (?P<whitespace>\s+)
    |(?P<string>'(?:[^']|'')*')
    |(?P<name>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)
    |(?P<operator>==|!=|&&|\|\||[(),])
    """,
    re.VERBOSE,
)


def _tokenize_github_expression(expression: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    position = 0
    while position < len(expression):
        match = GITHUB_TOKEN_PATTERN.match(expression, position)
        if match is None:
            raise ValueError(
                f"unsupported syntax at {position} in expression: {expression[position:]!r}"
            )
        position = match.end()
        if match.lastgroup != "whitespace":
            tokens.append((match.lastgroup, match.group()))
    return tokens


def _github_truthy(value: object) -> bool:
    return value is not None and value is not False and value != ""


def _stringify_github_value(value: object) -> str:
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


class _GithubExpressionParser:
    """Recursive-descent evaluator for the expression subset the gate uses."""

    def __init__(self, expression: str, context: dict) -> None:
        self.expression = expression
        self.tokens = _tokenize_github_expression(expression)
        self.position = 0
        self.context = context

    def parse(self) -> object:
        value = self._parse_or()
        if self.position != len(self.tokens):
            raise ValueError(f"trailing tokens in expression: {self.expression!r}")
        return value

    def _parse_or(self) -> object:
        value = self._parse_and()
        while self._accept("||"):
            right = self._parse_and()
            value = value if _github_truthy(value) else right
        return value

    def _parse_and(self) -> object:
        value = self._parse_equality()
        while self._accept("&&"):
            right = self._parse_equality()
            value = right if _github_truthy(value) else value
        return value

    def _parse_equality(self) -> object:
        value = self._parse_primary()
        while self._peek() in ("==", "!="):
            operator = self._next()[1]
            right = self._parse_primary()
            equal = self._values_equal(value, right)
            value = equal if operator == "==" else not equal
        return value

    def _values_equal(self, left: object, right: object) -> bool:
        # GitHub compares strings ignoring case and never coerces across
        # types, so a mixed-type comparison means the expression is not
        # modeled here instead of silently matching or missing.
        if isinstance(left, str) and isinstance(right, str):
            return left.casefold() == right.casefold()
        if type(left) is type(right):
            return left == right
        raise ValueError(
            f"incomparable types {type(left).__name__!r} and "
            f"{type(right).__name__!r} in expression: {self.expression!r}"
        )

    def _parse_primary(self) -> object:
        kind, text = self._next()
        if kind == "string":
            return text[1:-1].replace("''", "'")
        if kind == "name":
            if text == "true":
                return True
            if text == "false":
                return False
            if text == "null":
                return None
            return self._parse_call(text) if self._accept("(") else self._lookup(text)
        if text == "(":
            value = self._parse_or()
            if not self._accept(")"):
                raise ValueError(f"missing ')' in expression: {self.expression!r}")
            return value
        raise ValueError(f"unsupported token {text!r} in expression: {self.expression!r}")

    def _parse_call(self, name: str) -> object:
        if name != "format":
            raise ValueError(
                f"unsupported function {name!r} in expression: {self.expression!r}"
            )
        arguments = []
        if self._peek() != ")":
            arguments.append(self._parse_or())
            while self._accept(","):
                arguments.append(self._parse_or())
        if not self._accept(")"):
            raise ValueError(f"missing ')' in expression: {self.expression!r}")
        if not arguments or not isinstance(arguments[0], str):
            raise ValueError(
                f"format() needs a string pattern in expression: {self.expression!r}"
            )
        try:
            return arguments[0].format(*arguments[1:])
        except (IndexError, KeyError, ValueError) as error:
            raise ValueError(f"unsupported format() usage: {error}") from error

    def _lookup(self, name: str) -> object:
        if name not in ("github", "inputs") and not name.startswith(
            ("github.", "inputs.")
        ):
            raise ValueError(
                f"unsupported context name {name!r} in expression: {self.expression!r}"
            )
        value: object = self.context
        for part in name.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    def _peek(self) -> str | None:
        if self.position < len(self.tokens):
            return self.tokens[self.position][1]
        return None

    def _accept(self, text: str) -> bool:
        if self._peek() == text:
            self.position += 1
            return True
        return False

    def _next(self) -> tuple[str, str]:
        if self.position >= len(self.tokens):
            raise ValueError(f"unexpected end of expression: {self.expression!r}")
        token = self.tokens[self.position]
        self.position += 1
        return token


def evaluate_github_template(template: str, context: dict) -> object:
    """Evaluate a GitHub Actions ``${{ }}`` template the way the runner would.

    Literal text is kept and every ``${{ expression }}`` is replaced by the
    string form of its value. A template that is exactly one expression
    returns the raw value instead, because GitHub keeps the type there (so
    ``cancel-in-progress`` stays a boolean). Only the syntax the concurrency
    block uses is supported; any other token raises ValueError.
    """
    if template.count("${{") != template.count("}}"):
        raise ValueError(f"unbalanced template delimiters: {template!r}")
    pieces = GITHUB_TEMPLATE_PATTERN.split(template)
    if len(pieces) == 3 and not pieces[0] and not pieces[2]:
        return _GithubExpressionParser(pieces[1], context).parse()
    return "".join(
        piece
        if index % 2 == 0
        else _stringify_github_value(_GithubExpressionParser(piece, context).parse())
        for index, piece in enumerate(pieces)
    )


class CICandidateGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = find_repo_root()
        self.workflow = (self.repo_root / ".github/workflows/harness-ci.yml").read_text(
            encoding="utf-8"
        )

    def test_feature_push_and_pr_do_not_duplicate_ci(self) -> None:
        trigger = self.workflow.split("jobs:", 1)[0]
        self.assertIn("pull_request:", trigger)
        self.assertIn("types: [opened, synchronize, reopened, ready_for_review]", trigger)
        self.assertIn("merge_group:", trigger)
        self.assertIn("- main", trigger)
        self.assertNotIn("- development", trigger)
        self.assertNotIn("- '**'", trigger)

    def test_draft_pull_requests_run_only_linux_jobs(self) -> None:
        boundaries = {
            "quality": "\n  linux-harness:\n",
            "linux-harness": "\n  linux-other:\n",
            "linux-other": "\n  linux-browser:\n",
            "linux-browser": "\n  golden-path:\n",
            "golden-path": "\n  macos-harness:\n",
            "macos-harness": "\n  macos-other:\n",
            "macos-other": "\n  windows-native:\n",
            "windows-native": "\n  windows-installer:\n",
            "windows-installer": "\n  validate:\n",
        }
        headers = {
            job: self.workflow.split(f"\n  {job}:\n", 1)[1]
            .split(boundary, 1)[0]
            .split("\n    steps:\n", 1)[0]
            for job, boundary in boundaries.items()
        }
        draft_if = (
            "    if: github.event_name != 'pull_request' || !github.event.pull_request.draft"
        )
        for job in ("macos-harness", "macos-other", "windows-native", "windows-installer"):
            with self.subTest(job=job):
                self.assertIn(draft_if, headers[job])
        for job in ("quality", "linux-harness", "linux-other", "linux-browser", "golden-path"):
            with self.subTest(job=job):
                job_if_lines = [
                    line for line in headers[job].splitlines() if line.startswith("    if:")
                ]
                self.assertEqual([], job_if_lines, headers[job])
        self.assertIn(
            "        platform: ${{ fromJSON(github.event_name == 'pull_request' && "
            "github.event.pull_request.draft && '[\"linux\"]' || '[\"linux\", \"macos\"]') }}",
            self.workflow,
        )

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
        document = yaml.safe_load(self.workflow)
        concurrency = document["concurrency"]
        # A change to the concurrency block must update these pinned strings
        # together with the behavior cases below.
        group_template = re.sub(r"\s+", " ", concurrency["group"])
        cancel_template = re.sub(r"\s+", " ", concurrency["cancel-in-progress"])
        self.assertEqual(
            "${{ github.workflow }}-${{ github.event_name == 'workflow_dispatch' "
            "&& inputs.candidate_sha || github.event_name == 'pull_request' && "
            "format('pr-{0}-{1}', github.event.pull_request.number, "
            "github.event.pull_request.draft && 'draft' || 'ready') || github.ref }}",
            group_template,
        )
        self.assertEqual(
            "${{ github.event_name == 'pull_request' }}", cancel_template
        )

        def context(
            event_name: str,
            *,
            ref: str | None = None,
            inputs: dict | None = None,
            **event: object,
        ) -> dict:
            github: dict = {"workflow": document["name"], "event_name": event_name}
            if ref is not None:
                github["ref"] = ref
            if event:
                github["event"] = event
            return {"github": github, "inputs": inputs or {}}

        draft = context("pull_request", pull_request={"number": 145, "draft": True})
        ready = context("pull_request", pull_request={"number": 145, "draft": False})
        draft_group = evaluate_github_template(group_template, draft)
        ready_group = evaluate_github_template(group_template, ready)
        self.assertTrue(draft_group.endswith("pr-145-draft"), draft_group)
        self.assertTrue(ready_group.endswith("pr-145-ready"), ready_group)
        self.assertNotEqual(draft_group, ready_group)
        self.assertTrue(evaluate_github_template(cancel_template, draft))
        self.assertTrue(evaluate_github_template(cancel_template, ready))
        # Two ready runs of one pull request share a group, so the newer cancels the older.
        rerun = context("pull_request", pull_request={"number": 145, "draft": False})
        self.assertEqual(ready_group, evaluate_github_template(group_template, rerun))
        other_pull_request = context(
            "pull_request", pull_request={"number": 146, "draft": False}
        )
        self.assertNotEqual(
            ready_group, evaluate_github_template(group_template, other_pull_request)
        )

        push = context("push", ref="refs/heads/main")
        push_group = evaluate_github_template(group_template, push)
        self.assertTrue(push_group.endswith("refs/heads/main"), push_group)
        self.assertFalse(evaluate_github_template(cancel_template, push))

        queue_ref = "refs/heads/gh-readonly-queue/main/pr-145-abc"
        queue = context("merge_group", ref=queue_ref)
        queue_group = evaluate_github_template(group_template, queue)
        self.assertTrue(queue_group.endswith(queue_ref), queue_group)
        self.assertFalse(evaluate_github_template(cancel_template, queue))

        candidate_sha = "a1b2c3d4" * 5
        release = context(
            "workflow_dispatch",
            ref="refs/heads/main",
            inputs={"candidate_sha": candidate_sha},
        )
        release_group = evaluate_github_template(group_template, release)
        self.assertTrue(release_group.endswith(candidate_sha), release_group)
        self.assertFalse(evaluate_github_template(cancel_template, release))

        # Mutation self-check: flipping the pull_request guard collapses the
        # draft and ready pull request runs into one group, so the assertions
        # above that separate them would fail for that change.
        guard = "github.event_name == 'pull_request' && format"
        self.assertEqual(1, group_template.count(guard), group_template)
        mutated_template = group_template.replace(
            guard, "github.event_name != 'pull_request' && format"
        )
        self.assertEqual(
            evaluate_github_template(mutated_template, draft),
            evaluate_github_template(mutated_template, ready),
        )
        # A cancel-in-progress that also cancels non-pull-request runs must
        # evaluate truthy for push, so the assertFalse above fails for it.
        for mutated_cancel in (
            "${{ github.event_name == 'pull_request' || true }}",
            "${{ github.event_name == 'pull_request' || github.event_name == 'PUSH' }}",
        ):
            self.assertTrue(
                evaluate_github_template(mutated_cancel, push), mutated_cancel
            )

    def test_github_template_evaluator_rejects_unsupported_syntax(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_github_template(
                "${{ github.ref > 'a' }}", {"github": {"ref": "refs/heads/main"}}
            )

    def test_github_template_evaluator_reads_boolean_and_null_literals(self) -> None:
        context: dict = {"github": {"ref": "refs/heads/main"}, "inputs": {}}
        self.assertIs(True, evaluate_github_template("${{ true }}", context))
        self.assertIs(False, evaluate_github_template("${{ false }}", context))
        self.assertIsNone(evaluate_github_template("${{ null }}", context))

    def test_github_template_evaluator_compares_strings_without_case(self) -> None:
        context: dict = {"github": {"event_name": "push"}, "inputs": {}}
        self.assertIs(
            True, evaluate_github_template("${{ 'PUSH' == github.event_name }}", context)
        )
        self.assertIs(
            False,
            evaluate_github_template("${{ 'PUSH' != github.event_name }}", context),
        )

    def test_github_template_evaluator_rejects_unmodeled_names_and_types(self) -> None:
        context: dict = {"github": {"event_name": "push"}, "inputs": {}}
        for expression in ("env.SOMETHING", "TRUE", "'push' == true"):
            with self.subTest(expression=expression):
                with self.assertRaises(ValueError):
                    evaluate_github_template(f"${{{{{expression}}}}}", context)

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
        self.assertIn(
            "    name: ${{ github.event_name == 'pull_request' && "
            "github.event.pull_request.draft && 'validate-draft' || 'validate' }}",
            validate,
        )
        self.assertIn(
            "DRAFT_PULL_REQUEST: ${{ github.event_name == 'pull_request' && "
            "github.event.pull_request.draft }}",
            validate,
        )
        self.assertIn('if [ "$DRAFT_PULL_REQUEST" != "true" ]; then', validate)

    @unittest.skipIf(
        os.name == "nt" or shutil.which("bash") is None,
        "bash execution of the validate gate requires a POSIX host",
    )
    def test_validate_script_requires_the_jobs_each_run_selects(self) -> None:
        document = yaml.safe_load(self.workflow)
        step = next(
            step
            for step in document["jobs"]["validate"]["steps"]
            if step["name"].startswith("Require every selected")
        )
        script = step["run"].replace(
            "python skills/delivery-harness/scripts/ci_test_shards.py",
            f"'{sys.executable}' skills/delivery-harness/scripts/ci_test_shards.py",
            1,
        )
        succeeded, skipped = "success", "skipped"
        results = {
            "QUALITY_RESULT": succeeded,
            "LINUX_HARNESS_RESULT": succeeded,
            "LINUX_OTHER_RESULT": succeeded,
            "LINUX_BROWSER_RESULT": succeeded,
            "GOLDEN_PATH_RESULT": succeeded,
            "MACOS_HARNESS_RESULT": skipped,
            "MACOS_OTHER_RESULT": skipped,
            "WINDOWS_NATIVE_RESULT": skipped,
            "WINDOWS_INSTALLER_RESULT": skipped,
        }

        def gate(draft: str, overrides: dict[str, str] | None = None):
            environment = {**os.environ, **results, **(overrides or {}), "DRAFT_PULL_REQUEST": draft}
            return subprocess.run(
                ["bash", "-c", script],
                cwd=self.repo_root,
                env=environment,
                capture_output=True,
                encoding="utf-8",
                timeout=60,
                check=False,
            )

        self.assertEqual(0, gate("true").returncode)
        self.assertNotEqual(0, gate("false").returncode)
        self.assertNotEqual(0, gate("").returncode)
        self.assertNotEqual(
            0, gate("true", {"LINUX_BROWSER_RESULT": "failure"}).returncode
        )
        self.assertEqual(
            0, gate("false", {name: succeeded for name in results}).returncode
        )

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

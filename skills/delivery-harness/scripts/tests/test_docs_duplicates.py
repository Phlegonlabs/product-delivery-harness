"""Tests for docs_duplicates.py: repeated and near-repeated sentences across skill docs."""

from __future__ import annotations

import contextlib
import io
import json
import random
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import docs_duplicates  # noqa: E402

RULE = "Never push to the remote without explicit approval from the owner."  # 11 words
PLAN = (
    "The parent must record the observed head and the plan revision "
    "before it selects any ready node for launch."
)  # 19 words
PLAN_VARIANT = PLAN.replace("launch.", "start.")


def texts(document: str) -> list[tuple[int, str]]:
    return [(item.line, item.text) for item in docs_duplicates.parse_document(document)]


class NormalizeTests(unittest.TestCase):
    def test_strips_markup_and_trailing_punctuation(self) -> None:
        raw = "**Never** push to [the remote](remote.md), see `git push --force`!"
        self.assertEqual(
            "never push to the remote, see git push --force",
            docs_duplicates.normalize(raw),
        )

    def test_collapses_whitespace_and_keeps_identifiers(self) -> None:
        self.assertEqual(
            "run harness_step.py then stop",
            docs_duplicates.normalize("Run   harness_step.py\n  then   stop..."),
        )

    def test_emphasis_and_images_reduce_to_text(self) -> None:
        self.assertEqual(
            "this is very clear see the chart",
            docs_duplicates.normalize("This is _very_ *clear* see ![the chart](c.png)"),
        )

    def test_normalizing_twice_changes_nothing(self) -> None:
        once = docs_duplicates.normalize("**Do** [this](a.md#b) now, `x.y`.")
        self.assertEqual(once, docs_duplicates.normalize(once))


class ParseTests(unittest.TestCase):
    def test_fenced_code_is_skipped_and_prose_resumes(self) -> None:
        document = (
            "Before the fence there is one sentence.\n\n"
            "```text\nInside the fence this sentence must be ignored.\n```\n\n"
            "~~~~\nTilde fence with a ``` line inside stays closed.\n```\n"
            "Still inside the tilde fence here.\n~~~~\n\n"
            "After the fence prose is read again.\n"
        )
        self.assertEqual(
            ["before the fence there is one sentence", "after the fence prose is read again"],
            [text for _, text in texts(document)],
        )

    def test_front_matter_comments_headings_and_rules_are_skipped(self) -> None:
        document = (
            "---\nname: demo\ndescription: Hidden front matter sentence here.\n---\n\n"
            "# A heading with enough words to count\n\n"
            "<!-- one line comment -->\n"
            "<!--\nmulti line comment sentence hidden\n-->\n"
            "---\n"
            "Body sentence stays.\n"
        )
        self.assertEqual([(13, "body sentence stays")], texts(document))

    def test_table_header_and_separator_rows_are_skipped(self) -> None:
        document = (
            "| Header A | Header B |\n| --- | :---: |\n| cell one text | cell \\| two text |\n\n"
            "Text between tables.\n\n"
            "| Other header |\n|---|\n| other cell |\n"
        )
        self.assertEqual(
            [
                (3, "cell one text"),
                (3, "cell | two text"),
                (5, "text between tables"),
                (9, "other cell"),
            ],
            texts(document),
        )

    def test_line_numbers_follow_the_sentence_start(self) -> None:
        document = (
            "# Title\n\nFirst one. Second one spans\ntwo lines. Third starts on line four.\n\n"
            "- A list item sits here.\n> A quoted sentence is kept.\n"
        )
        self.assertEqual(
            [
                (3, "first one"),
                (3, "second one spans two lines"),
                (4, "third starts on line four"),
                (6, "a list item sits here"),
                (7, "a quoted sentence is kept"),
            ],
            texts(document),
        )

    def test_abbreviations_code_spans_and_bold_do_not_break_sentences(self) -> None:
        document = (
            "Use a tool, e.g. Git, for this task. Run `a. B` now.\n"
            "**Never push.** Always ask first.\n"
            "The devs. Next one starts here.\n"
        )
        self.assertEqual(
            [
                "use a tool, e.g. git, for this task",
                "run a. b now",
                "never push",
                "always ask first",
                "the devs",
                "next one starts here",
            ],
            [text for _, text in texts(document)],
        )


class CorpusCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def scan(self, **options):
        return docs_duplicates.scan(self.root, **options)

    def run_main(self, *args: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = docs_duplicates.main(["--repo-root", str(self.root), *args])
        return code, stdout.getvalue()


class SelectionTests(CorpusCase):
    def test_selects_skill_and_nested_reference_markdown_only(self) -> None:
        for relative in (
            "skills/alpha/SKILL.md",
            "skills/alpha/references/a.md",
            "skills/alpha/references/nested/deep.md",
            "skills/alpha/references/legacy/old.md",
            "skills/alpha/references/legacy/nested/older.md",
            "skills/alpha/references/notes.txt",
            "skills/alpha/scripts/guide.md",
            "skills/alpha/assets/guide.md",
            "skills/beta/SKILL.md",
            "skills/loose.md",
            "other/references/x.md",
        ):
            self.write(relative, "Some words.")
        found = [
            path.relative_to(self.root).as_posix()
            for path in docs_duplicates.document_paths(self.root)
        ]
        self.assertEqual(
            [
                "skills/alpha/SKILL.md",
                "skills/alpha/references/a.md",
                "skills/alpha/references/nested/deep.md",
                "skills/beta/SKILL.md",
            ],
            found,
        )

    def test_missing_skills_folder_is_an_empty_scan(self) -> None:
        self.assertEqual(0, self.scan()["summary"]["duplicated_words"])


class ExactTests(CorpusCase):
    def test_sentence_in_two_files_is_a_group(self) -> None:
        self.write("skills/alpha/SKILL.md", f"Intro here.\n\n{RULE}\n")
        self.write("skills/alpha/references/a.md", f"# A\n\n- **{RULE[:-1]}**\n")
        group = self.scan()["exact"][0]
        self.assertEqual(11, group["words"])
        self.assertEqual(11, group["duplicated_words"])
        self.assertEqual(
            [("skills/alpha/SKILL.md", 3), ("skills/alpha/references/a.md", 3)],
            [(entry["file"], entry["line"]) for entry in group["occurrences"]],
        )

    def test_three_copies_count_two_extras(self) -> None:
        for name in ("a", "b", "c"):
            self.write(f"skills/alpha/references/{name}.md", RULE)
        group = self.scan()["exact"][0]
        self.assertEqual(22, group["duplicated_words"])

    def test_one_file_short_sentence_and_fenced_copy_do_not_count(self) -> None:
        self.write("skills/alpha/SKILL.md", f"{RULE}\n\n{RULE}\n")
        self.write("skills/alpha/references/a.md", f"```\n{RULE}\n```\n")
        self.write("skills/alpha/references/b.md", "Do not push.\n")
        self.write("skills/alpha/references/c.md", "Do not push.\n")
        self.assertEqual([], self.scan()["exact"])

    def test_min_words_sets_the_shortest_sentence(self) -> None:
        self.write("skills/alpha/references/a.md", "Do not push to main.\n")
        self.write("skills/alpha/references/b.md", "Do not push to main.\n")
        self.assertEqual([], self.scan()["exact"])
        self.assertEqual(1, len(self.scan(min_words=5)["exact"]))

    def test_allowlist_hides_a_standard_sentence(self) -> None:
        self.write("skills/alpha/references/a.md", RULE)
        self.write("skills/alpha/references/b.md", RULE)
        allowlist_path = self.root / "allow.txt"
        allowlist_path.write_text(f"# standard phrases\n\n{RULE}\n", encoding="utf-8")
        allowlist = docs_duplicates.load_allowlist(allowlist_path)
        self.assertEqual([], self.scan(allowlist=allowlist)["exact"])
        self.assertEqual(frozenset({docs_duplicates.normalize(RULE)}), allowlist)


class NearTests(CorpusCase):
    def test_changed_last_word_is_a_near_group(self) -> None:
        self.write("skills/alpha/references/a.md", PLAN)
        self.write("skills/alpha/references/b.md", PLAN_VARIANT)
        result = self.scan()
        self.assertEqual([], result["exact"])
        group = result["near"][0]
        self.assertEqual(2, len(group["variants"]))
        self.assertEqual(19, group["duplicated_words"])
        self.assertGreaterEqual(group["similarity"], 0.85)

    def test_threshold_rejects_a_weaker_match(self) -> None:
        self.write("skills/alpha/references/a.md", PLAN)
        self.write("skills/alpha/references/b.md", PLAN_VARIANT)
        self.assertEqual([], self.scan(threshold=0.95)["near"])

    def test_same_file_short_and_unrelated_sentences_are_not_near(self) -> None:
        self.write("skills/alpha/references/a.md", f"{PLAN}\n\n{PLAN_VARIANT}\n")
        self.write("skills/alpha/references/b.md", "Read the short rule. Then stop.\n")
        self.write("skills/alpha/references/c.md", "Read the short rule. Then stop now.\n")
        self.write(
            "skills/alpha/references/d.md",
            "Every worker keeps its own checkout and never edits files that another writer owns today.\n",
        )
        self.assertEqual([], self.scan()["near"])

    def test_allowlisted_sentence_is_not_matched_as_near(self) -> None:
        self.write("skills/alpha/references/a.md", PLAN)
        self.write("skills/alpha/references/b.md", PLAN_VARIANT)
        allowlist = frozenset({docs_duplicates.normalize(PLAN)})
        self.assertEqual([], self.scan(allowlist=allowlist)["near"])

    def test_prefix_index_matches_brute_force(self) -> None:
        rng = random.Random(7)
        vocabulary = [f"w{index}" for index in range(40)]
        bases: list[list[str]] = []
        for _ in range(120):
            if bases and rng.random() < 0.5:
                base = list(rng.choice(bases))  # a near copy of an earlier sentence
                for _ in range(rng.randint(1, 3)):
                    base[rng.randrange(len(base))] = rng.choice(vocabulary)
            else:
                base = [rng.choice(vocabulary) for _ in range(rng.randint(5, 40))]
            bases.append(base)
        sets = [docs_duplicates._shingles(" ".join(base)) for base in bases]
        for threshold in (0.3, 0.6, 0.85):
            expected = {
                (first, second)
                for first in range(len(sets))
                for second in range(first + 1, len(sets))
                if sets[first]
                and sets[second]
                and len(sets[first] & sets[second]) / len(sets[first] | sets[second])
                >= threshold - 1e-12
            }
            found = {
                (first, second)
                for first, second, _ in docs_duplicates._similar_pairs(sets, threshold)
            }
            self.assertEqual(expected, found, threshold)


class SummaryTests(CorpusCase):
    def test_totals_per_skill_and_per_file(self) -> None:
        self.write("skills/alpha/SKILL.md", RULE)
        self.write("skills/beta/SKILL.md", RULE)
        self.write("skills/beta/references/b.md", f"Unique text only appears in this one place.\n\n{RULE}\n")
        summary = self.scan()["summary"]
        self.assertEqual(3, summary["files"])
        self.assertEqual(22, summary["duplicated_words"])
        self.assertEqual(
            {"files": 1, "sentences": 1, "words_in_duplicates": 11}, summary["per_skill"]["alpha"]
        )
        self.assertEqual(
            {"files": 2, "sentences": 2, "words_in_duplicates": 22}, summary["per_skill"]["beta"]
        )
        self.assertEqual(
            {"sentences": 1, "words_in_duplicates": 11}, summary["per_file"]["skills/beta/SKILL.md"]
        )
        self.assertEqual(11, summary["per_file"]["skills/beta/references/b.md"]["words_in_duplicates"])

    def test_exact_copies_inside_a_near_group_are_not_counted_twice(self) -> None:
        self.write("skills/alpha/references/a.md", PLAN)
        self.write("skills/alpha/references/b.md", PLAN)
        self.write("skills/alpha/references/c.md", PLAN_VARIANT)
        summary = self.scan()["summary"]
        self.assertEqual(19, summary["exact_duplicated_words"])
        self.assertEqual(19, summary["near_duplicated_words"])
        self.assertEqual(38, summary["duplicated_words"])
        self.assertEqual(57, sum(item["words_in_duplicates"] for item in summary["per_file"].values()))


class CommandLineTests(CorpusCase):
    def setUp(self) -> None:
        super().setUp()
        self.write("skills/alpha/references/a.md", RULE)
        self.write("skills/alpha/references/b.md", RULE)

    def test_report_mode_exits_zero_and_lists_groups(self) -> None:
        code, out = self.run_main()
        self.assertEqual(0, code)
        self.assertIn("[E1] 11 words x 2 = 11 duplicated", out)
        self.assertIn("skills/alpha/references/a.md:1", out)
        self.assertIn("DUPLICATED WORDS: 11", out)

    def test_summary_flag_prints_counts_without_groups(self) -> None:
        code, out = self.run_main("--summary")
        self.assertEqual(0, code)
        self.assertNotIn("[E1]", out)
        self.assertIn("DUPLICATED WORDS: 11", out)
        self.assertIn("alpha: 22 words", out)

    def test_json_output_parses(self) -> None:
        code, out = self.run_main("--json")
        payload = json.loads(out)
        self.assertEqual(0, code)
        self.assertEqual(11, payload["summary"]["duplicated_words"])
        self.assertEqual(1, len(payload["exact"]))
        code, out = self.run_main("--json", "--summary")
        payload = json.loads(out)
        self.assertEqual({"parameters", "summary"}, set(payload))

    def test_fail_over_compares_the_duplicated_word_total(self) -> None:
        self.assertEqual(1, self.run_main("--fail-over", "10")[0])
        self.assertEqual(0, self.run_main("--fail-over", "11")[0])
        self.assertEqual(0, self.run_main()[0])

    def test_flags_reach_the_scan(self) -> None:
        allow = self.root / "allow.txt"
        allow.write_text(RULE, encoding="utf-8")
        self.assertIn("DUPLICATED WORDS: 0", self.run_main("--allowlist", str(allow))[1])
        self.assertIn("DUPLICATED WORDS: 0", self.run_main("--min-words", "12")[1])
        self.assertIn("near groups 0", self.run_main("--threshold", "0.9")[1])

    def test_missing_allowlist_is_an_error(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code, _ = self.run_main("--allowlist", str(self.root / "missing.txt"))
        self.assertEqual(2, code)
        self.assertIn("error:", stderr.getvalue())


class RealRepositoryTests(unittest.TestCase):
    def test_real_scan_finishes_and_returns_a_summary(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        started = time.monotonic()
        result = docs_duplicates.scan(repo_root)
        self.assertLess(time.monotonic() - started, 30)
        summary = result["summary"]
        self.assertGreater(summary["files"], 5)
        self.assertGreater(summary["sentences"], 1000)
        self.assertGreaterEqual(summary["duplicated_words"], 0)
        self.assertEqual(
            summary["duplicated_words"],
            summary["exact_duplicated_words"] + summary["near_duplicated_words"],
        )
        self.assertIn("delivery-harness", summary["per_skill"])


if __name__ == "__main__":
    unittest.main()

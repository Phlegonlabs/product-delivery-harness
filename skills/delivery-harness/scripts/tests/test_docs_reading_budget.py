"""Tests for docs_reading_budget.py: words an agent must read per entry point."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import docs_reading_budget as budget  # noqa: E402

SKILL = "skills/alpha/SKILL.md"
CARDS = budget.STAGE_CARDS


def filler(count: int, tag: str = "w") -> str:
    return " ".join(f"{tag}{index}" for index in range(count))


def words(text: str) -> int:
    return len(text.split())


class CorpusCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def reference(self, name: str, text: str) -> None:
        self.write(f"skills/alpha/references/{name}.md", text)

    def measure(self, entry: str = "alpha", depth: int = 2, **options: Any) -> dict[str, Any]:
        corpus = budget.Corpus(self.root, **options)
        for name, path, spans in corpus.entries():
            if name == entry:
                return budget.measure(corpus, path, spans, depth)
        raise AssertionError(f"no entry {entry}")

    def links(self, path: str = SKILL, **options: Any) -> list[budget.Link]:
        return budget.Corpus(self.root, **options).doc(path).links

    def run_main(self, *args: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = budget.main(["--repo-root", str(self.root), *args])
        return code, stdout.getvalue()


class ExtractionTests(CorpusCase):
    def test_finds_markdown_links_and_backticked_paths_only_where_they_are_prose(self) -> None:
        self.write(
            SKILL,
            "Before work, read [Guide](references/guide.md#part) and `references/other.md`.\n"
            "See [site](https://example.com/x.md) and [dir](references/option-library/).\n"
            "Code `[example](references/ignored.md)` and `bare.md` stay out.\n\n"
            "```text\n[fenced](references/ignored.md)\n```\n",
        )
        for name in ("guide", "other", "ignored"):
            self.reference(name, "# Guide\n\n## Part\n\ntext\n")
        found = [(l.kind, l.target, l.anchor, l.status) for l in self.links()]
        self.assertEqual(
            [
                ("link", "skills/alpha/references/guide.md", "part", "ok"),
                ("path", "skills/alpha/references/other.md", "", "ok"),
            ],
            found,
        )

    def test_markdown_links_only_drops_backticked_paths(self) -> None:
        self.write(SKILL, "Read [A](references/a.md) and `references/b.md`.\n")
        self.reference("a", "a")
        self.reference("b", "b")
        found = [l.target for l in self.links(paths=False)]
        self.assertEqual(["skills/alpha/references/a.md"], found)

    def test_legacy_missing_and_outside_links_are_listed_but_not_followed(self) -> None:
        self.write(
            SKILL,
            "Read [old](references/legacy/old.md), [gone](references/gone.md) "
            "and [doc](../../docs/note.md).\n",
        )
        self.write("skills/alpha/references/legacy/old.md", filler(50))
        self.write("docs/note.md", filler(50))
        self.assertEqual(["legacy", "missing", "outside"], [l.status for l in self.links()])
        result = self.measure()
        self.assertEqual(0, result["mandatory_words"])
        self.assertEqual(0, result["conditional_depth1_words"])

    def test_pure_anchor_link_points_into_the_same_file(self) -> None:
        self.write(SKILL, "Read [below](#part).\n\n## Part\n\ntext\n")
        self.assertEqual([(SKILL, "part")], [(l.target, l.anchor) for l in self.links()])

    def test_table_cells_are_judged_apart(self) -> None:
        self.write(SKILL, "| Step | Link |\n| --- | --- |\n| Read [A](references/a.md) | See [B](references/b.md) |\n")
        self.reference("a", "a")
        self.reference("b", "b")
        self.assertEqual(["mandatory", "conditional"], [l.cls for l in self.links()])


class ClassifyTests(CorpusCase):
    def kind(self, clause: str, titles: list[str] | None = None, text: str = "", target: str = "") -> str:
        return budget.classify(clause, titles or [], text, target)[0]

    def test_obligation_words_make_a_link_mandatory(self) -> None:
        for clause in (
            "Before work, read ___",
            "Follow ___ for the rest",
            "Apply ___ here",
            "You must use ___",
            "Run ___ now",
            "The complete ___ is required",
            "Read the whole ___",
        ):
            self.assertEqual("mandatory", self.kind(clause), clause)

    def test_conditional_words_win_over_obligation_words(self) -> None:
        for clause in (
            "Read ___ only when it is needed",
            "If the card names it, read ___",
            "Optionally read ___",
            "Read ___ unless the run is small",
            "For a package pinned to an older version, read ___",
            "Apply the conditional ___",
            "For a web app, also read ___",
        ):
            self.assertEqual("conditional", self.kind(clause), clause)

    def test_no_marker_is_conditional_and_says_so(self) -> None:
        self.assertEqual(("conditional", "no marker"), budget.classify("See ___", [], "", ""))

    def test_required_headings_make_unmarked_links_mandatory(self) -> None:
        for title in ("Required Reading", "Required Skills And Inputs", "Managed Stage Routing", "Mandatory Governance Routes"):
            self.assertEqual("mandatory", self.kind("See ___", ["Top", title]), title)
        self.assertEqual("conditional", self.kind("See ___", ["Other"]))

    def test_enhancement_and_legacy_count_in_the_link_not_the_sentence(self) -> None:
        self.assertEqual("mandatory", self.kind("Before a definition or enhancement starts, read ___"))
        self.assertEqual("conditional", self.kind("Read ___", text="Enhancement notes"))
        self.assertEqual("conditional", self.kind("Read ___", target="skills/a/enhancement-recommendations.md"))

    def test_run_as_a_document_name_or_a_quoted_title_is_not_a_verb(self) -> None:
        self.write(SKILL, "The RUN lists `references/a.md`.\n- `references/b.md` — \"Run Lock And Watchdog\"\n")
        self.reference("a", "a")
        self.reference("b", "b")
        self.assertEqual(["conditional", "conditional"], [l.cls for l in self.links()])

    def test_clauses_split_at_semicolons_and_abbreviations_hold(self) -> None:
        self.write(
            SKILL,
            "Start from `references/a.md`; read the rest in `references/b.md` when stuck.\n"
            "Use a tool, e.g. Git, and read `references/c.md`.\n",
        )
        for name in "abc":
            self.reference(name, name)
        self.assertEqual(
            ["conditional", "conditional", "mandatory"], [l.cls for l in self.links()]
        )

    def test_link_records_the_deciding_words_and_clause(self) -> None:
        self.write(SKILL, "Before the plan, read [A](references/a.md).\n")
        self.reference("a", "a")
        link = self.links()[0]
        self.assertEqual("obligation word 'before'", link.why)
        self.assertIn("Before the plan, read", link.excerpt)


class WordTests(CorpusCase):
    def test_own_words_match_the_whole_file_split(self) -> None:
        text = f"---\nname: alpha\n---\n\n# Alpha\n\n{filler(30)}\n"
        self.write(SKILL, text)
        self.assertEqual(words(text), self.measure()["own_words"])

    def test_an_anchor_counts_only_its_section(self) -> None:
        guide = f"# Guide\n\n{filler(5, 'a')}\n\n## Part\n\n{filler(7, 'p')}\n\n### Sub\n\n{filler(3, 's')}\n\n## Other\n\n{filler(9, 'o')}\n"
        self.write(SKILL, "Read [Part](references/guide.md#part).\n")
        self.reference("guide", guide)
        expected = words(f"## Part\n\n{filler(7, 'p')}\n\n### Sub\n\n{filler(3, 's')}")
        result = self.measure()
        self.assertEqual(expected, result["mandatory_words"])
        self.assertEqual(
            [{"file": "skills/alpha/references/guide.md", "words_read": expected,
              "file_words": words(guide), "depth": 1, "whole_file": False}],
            result["heaviest"],
        )

    def test_a_missing_anchor_reads_the_whole_file(self) -> None:
        self.write(SKILL, "Read [X](references/guide.md#nope).\n")
        self.reference("guide", f"# Guide\n\n{filler(12)}\n")
        result = self.measure()
        self.assertEqual(words(f"# Guide\n\n{filler(12)}"), result["mandatory_words"])
        self.assertTrue(result["heaviest"][0]["whole_file"])

    def test_duplicate_headings_get_numbered_slugs(self) -> None:
        self.write(SKILL, "Read [Second](references/guide.md#part-1).\n")
        self.reference("guide", f"## Part\n\n{filler(2, 'a')}\n\n## Part\n\n{filler(4, 'b')}\n")
        self.assertEqual(words(f"## Part\n\n{filler(4, 'b')}"), self.measure()["mandatory_words"])

    def test_a_whole_file_link_absorbs_section_links_without_double_counting(self) -> None:
        guide = f"# Guide\n\n## Part\n\n{filler(8)}\n"
        self.write(SKILL, "Read [Part](references/guide.md#part) and [all](references/guide.md).\n")
        self.reference("guide", guide)
        result = self.measure()
        self.assertEqual(words(guide), result["mandatory_words"])
        self.assertTrue(result["heaviest"][0]["whole_file"])
        self.assertIn("d1 whole skills/alpha/references/guide.md", self.run_main()[1])
        self.write(SKILL, "Read [Part](references/guide.md#part).\n")
        self.assertIn("d1 part  skills/alpha/references/guide.md", self.run_main()[1])

    def test_skip_section_removes_words_and_links(self) -> None:
        self.write(SKILL, f"# Alpha\n\nIntro words.\n\n## Managed Stage Routing\n\nRead [A](references/a.md) {filler(10)}\n")
        self.reference("a", filler(40))
        kept = self.measure()
        skipped = self.measure(skip=("managed-stage-routing",))
        self.assertEqual(40, kept["mandatory_words"])
        self.assertEqual(0, skipped["mandatory_words"])
        self.assertEqual(words("# Alpha\n\nIntro words.\n\n"), skipped["own_words"])
        self.assertEqual([], self.links(skip=("managed-stage-routing",)))


class DepthTests(CorpusCase):
    def setUp(self) -> None:
        super().setUp()
        self.write(SKILL, f"Read [A](references/a.md). {filler(3)}\n")
        self.reference("a", f"Read [B](b.md). {filler(5, 'a')}\n")
        self.reference("b", f"Read [C](c.md). {filler(7, 'b')}\n")
        self.reference("c", filler(11, "c"))

    def test_depth_limits_the_transitive_total_but_not_depth_one(self) -> None:
        sizes = {"a": words(f"Read [B](b.md). {filler(5, 'a')}"), "b": words(f"Read [C](c.md). {filler(7, 'b')}"), "c": 11}
        expected = {1: sizes["a"], 2: sizes["a"] + sizes["b"], 3: sum(sizes.values()), 9: sum(sizes.values())}
        for depth, total in expected.items():
            result = self.measure(depth=depth)
            self.assertEqual(sizes["a"], result["mandatory_depth1_words"], depth)
            self.assertEqual(total, result["mandatory_words"], depth)

    def test_depth_zero_reads_nothing_beyond_the_entry(self) -> None:
        result = self.measure(depth=0)
        self.assertEqual((0, 0), (result["mandatory_depth1_words"], result["mandatory_words"]))

    def test_heaviest_lists_files_by_words_with_the_depth_first_reached(self) -> None:
        rows = [(row["file"].rsplit("/", 1)[1], row["depth"]) for row in self.measure(depth=3)["heaviest"]]
        self.assertEqual([("c.md", 3), ("b.md", 2), ("a.md", 1)], rows)

    def test_only_ten_heaviest_are_listed(self) -> None:
        links = " ".join(f"[F{n}](references/f{n}.md)" for n in range(12))
        self.write(SKILL, f"Read {links}.\n")
        for n in range(12):
            self.reference(f"f{n}", filler(10 + n))
        heaviest = self.measure()["heaviest"]
        self.assertEqual(10, len(heaviest))
        self.assertEqual(21, heaviest[0]["words_read"])

    def test_cycles_end_and_nothing_is_counted_twice(self) -> None:
        self.write(SKILL, "Read [A](references/a.md) and `references/a.md`.\n")
        self.reference("a", "Read [skill](../SKILL.md) and [self](a.md) and [b](b.md). x\n")
        self.reference("b", "Read [a](a.md). y\n")
        result = self.measure(depth=9)
        self.assertEqual(words("Read [skill](../SKILL.md) and [self](a.md) and [b](b.md). x") + words("Read [a](a.md). y"), result["mandatory_words"])

    def test_conditional_links_are_counted_apart_and_not_followed(self) -> None:
        self.write(
            SKILL,
            "Read [A](references/a.md) when stuck.\nRead [D](references/d.md).\nSee [D again](references/d.md).\n",
        )
        self.reference("a", "Read [C](c.md). a\n")
        self.reference("d", filler(6, "d"))
        result = self.measure(depth=3)
        self.assertEqual(6, result["mandatory_words"])
        self.assertEqual(words("Read [C](c.md). a"), result["conditional_depth1_words"])


class StageCardTests(CorpusCase):
    def test_each_card_is_an_entry_that_includes_the_lead(self) -> None:
        lead = f"# Cards\n\n{filler(4, 'lead')}\n\n"
        card1 = f"## Card 1: First\n\nBefore work, read [A](../a.md). {filler(5)}\n\n"
        card2 = f"## Card 2: Second\n\n{filler(6)}\n"
        self.write(CARDS, lead + card1 + card2)
        self.write("skills/delivery-harness/references/a.md", filler(9, "a"))
        self.write("skills/delivery-harness/SKILL.md", "Skill.\n")
        corpus = budget.Corpus(self.root)
        names = [name for name, _path, _spans in corpus.entries()]
        self.assertEqual(["delivery-harness", "stage-cards#card-1-first", "stage-cards#card-2-second"], names)
        first = self.measure("stage-cards#card-1-first")
        second = self.measure("stage-cards#card-2-second")
        self.assertEqual(words(lead + card1.rstrip()), first["own_words"])
        self.assertEqual(9, first["mandatory_words"])
        self.assertEqual(words(lead + card2.rstrip()), second["own_words"])
        self.assertEqual(0, second["mandatory_words"])


class CommandLineTests(CorpusCase):
    def setUp(self) -> None:
        super().setUp()
        self.write(SKILL, "Before work, read [A](references/a.md).\n")
        self.write("skills/beta/SKILL.md", "Beta words here.\n")
        self.reference("a", filler(100))

    def test_report_lists_every_entry_and_exits_zero(self) -> None:
        code, out = self.run_main()
        self.assertEqual(0, code)
        self.assertIn("alpha ", out)
        self.assertIn("beta ", out)
        self.assertIn("100 / 100", out)

    def test_budget_exits_one_only_above_the_limit(self) -> None:
        code, out = self.run_main("--budget", "99")
        self.assertEqual(1, code)
        self.assertIn("over budget: alpha 100 > 99", out)
        self.assertNotIn("over budget: beta", out)
        self.assertEqual(0, self.run_main("--budget", "100")[0])
        self.assertEqual(0, self.run_main("--depth", "0", "--budget", "0")[0])

    def test_entry_matches_exactly_then_by_part_and_rejects_unknown(self) -> None:
        self.assertNotIn("beta ", self.run_main("--entry", "alpha")[1])
        self.assertNotIn("alpha ", self.run_main("--entry", "BET")[1])
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code, _ = self.run_main("--entry", "missing")
        self.assertEqual(2, code)
        self.assertIn("error:", stderr.getvalue())

    def test_links_prints_class_and_deciding_words(self) -> None:
        code, out = self.run_main("--links")
        self.assertEqual(0, code)
        self.assertIn(f"{SKILL}:1 [mandatory] link -> skills/alpha/references/a.md", out)
        self.assertIn("obligation word 'before': Before work, read [A](references/a.md).", out)

    def test_links_with_an_entry_only_lists_links_in_the_lines_read(self) -> None:
        self.write("skills/beta/SKILL.md", "Read [B](references/b.md).\n")
        self.write("skills/beta/references/b.md", "b\n")
        out = self.run_main("--links", "--entry", "alpha")[1]
        self.assertIn("alpha/SKILL.md", out)
        self.assertNotIn("beta", out)

    def test_json_output_parses(self) -> None:
        code, out = self.run_main("--json", "--entry", "alpha")
        payload = json.loads(out)
        self.assertEqual(0, code)
        self.assertEqual({"depth": 2, "budget": None}, payload["parameters"])
        entry = payload["entries"][0]
        self.assertEqual(("alpha", 100), (entry["name"], entry["mandatory_words"]))
        self.assertEqual({"skills/alpha/references/a.md": 100}, entry["reads"])
        self.assertNotIn("covered", entry)

    def test_markdown_links_only_flag_reaches_the_scan(self) -> None:
        self.write(SKILL, "Read `references/a.md`.\n")
        self.assertIn("100 / 100", self.run_main()[1])
        self.assertNotIn("100 / 100", self.run_main("--markdown-links-only")[1])

    def test_negative_depth_is_a_usage_error(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            self.run_main("--depth", "-1")
        self.assertEqual(2, raised.exception.code)


class RealRepositoryTests(unittest.TestCase):
    def test_real_run_finishes_and_lists_every_skill_entry(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        corpus = budget.Corpus(repo_root)
        started = time.monotonic()
        entries = corpus.entries()
        results = {name: budget.measure(corpus, path, spans, 2) for name, path, spans in entries}
        self.assertLess(time.monotonic() - started, 30)
        skills = sorted(path.parent.name for path in repo_root.glob("skills/*/SKILL.md"))
        self.assertGreater(len(skills), 4)
        for skill in skills:
            self.assertIn(skill, results)
        cards = [line for line in (repo_root / CARDS).read_text(encoding="utf-8").splitlines() if line.startswith("## ")]
        self.assertEqual(len(cards), len([name for name in results if name.startswith("stage-cards#")]))
        harness = results["delivery-harness"]
        text = (repo_root / "skills/delivery-harness/SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(words(text), harness["own_words"])
        self.assertGreater(harness["mandatory_words"], harness["mandatory_depth1_words"] // 2)
        for result in results.values():
            for row in result["heaviest"]:
                self.assertNotIn("/references/legacy/", row["file"])

    def test_cli_runs_on_the_real_repository(self) -> None:
        repo_root = Path(__file__).resolve().parents[4]
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = budget.main(["--repo-root", str(repo_root)])
        self.assertEqual(0, code)
        for skill in repo_root.glob("skills/*/SKILL.md"):
            self.assertIn(skill.parent.name, stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

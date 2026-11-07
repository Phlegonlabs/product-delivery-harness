"""The UI review matrix and repair-loop rules are written once, in the rubric."""

import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
RUBRIC = "references/ui-grading-rubric.md"
POINTERS = ("references/ui-design-pass.md", "references/stages/ui-design.md")


def read(relative):
    return (SKILL_ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n")


def section(text, heading):
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


class ReviewMatrixDocsTests(unittest.TestCase):
    def test_sampling_rule_lives_in_the_rubric_axes_and_is_only_pointed_at(self):
        axes = section(read(RUBRIC), "## First-Wave Audit Axes")
        for phrase in (
            "every non-`n/a`, non-derived state",
            "A derived state (PRD `derivedStates`) is captured once, at its surface's smallest responsive target",
            "its densest non-derived state, each at the smallest and largest approved target",
            "Run reduced motion only on pages with a motion region or a required motion intent",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, axes)
        for source in POINTERS:
            with self.subTest(source=source):
                text = read(source)
                self.assertIn("ui-grading-rubric.md#first-wave-audit-axes", text)
                self.assertNotIn("densest", text)
                self.assertNotIn("smallest and largest", text)

    def test_repair_loop_is_capped_and_names_the_carry_forward_and_diff_first_rules(self):
        rubric = read(RUBRIC)
        scope = section(rubric, "## Repair Re-review Scope")
        for phrase in (
            "at most two scoped re-reviews in total may follow",
            "a block still blocks",
            "[Render fingerprint carry-forward]",
            "[Diff-first re-review]",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, scope)
        self.assertEqual(1, rubric.count("at most two scoped re-reviews"))
        self.assertNotIn("a block still blocks", section(rubric, "## Reporting And Reconciliation"))
        self.assertNotIn("record one scoped re-review of those pages", rubric)
        for source in POINTERS:
            with self.subTest(source=source):
                self.assertIn("ui-grading-rubric.md#repair-re-review-scope", read(source))


if __name__ == "__main__":
    unittest.main()

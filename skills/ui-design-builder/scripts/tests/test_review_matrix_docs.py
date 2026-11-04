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


if __name__ == "__main__":
    unittest.main()

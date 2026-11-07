"""The skill's fill-in templates parse with the checkers and carry the named fields."""

import re
import sys
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = SKILL_ROOT / "assets" / "templates"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import check_ui_design_contract as checker  # noqa: E402

# Problems about a missing or misshapen heading, field or table, as opposed to an unfilled value.
STRUCTURAL = re.compile(
    r"UI contract marker|heading|is missing '|duplicate '|requires exactly one '|declared columns"
    r"|eleven-column|Stage, Skill, Artifact, Application"
)


def read(name):
    return (TEMPLATES / name).read_text(encoding="utf-8")


class UiDesignTemplateTests(unittest.TestCase):
    def setUp(self):
        self.text = read("UI_DESIGN.template.md")

    def test_template_passes_the_checker_structural_parse(self):
        self.assertEqual("ui-design/3", checker.ui_contract_version(self.text))
        self.assertEqual([], checker.validate_text(self.text))

    def test_template_carries_every_heading_field_and_table_the_visual_gate_reads(self):
        mvp = self.text
        for field, value in (("Direction mode", "one recommended direction (mvp)"),
                             ("Direction decision", "deferred to Visual Approval (mvp)")):
            mvp, count = re.subn(rf"^{field}: \[.*\]$", f"{field}: {value}", mvp, flags=re.MULTILINE)
            self.assertEqual(1, count, field)
        for text, profile in ((self.text, None), (mvp, "mvp")):
            with self.subTest(profile=profile):
                problems = checker.validate_text(text, require_visual_approved=True, delivery_profile=profile)
                self.assertTrue(problems)
                self.assertEqual([], [problem for problem in problems if STRUCTURAL.search(problem)])
        for removed in ("Candidate theme:", "### Direction studies", "Covers direction:"):
            with self.subTest(removed=removed):
                broken = mvp.replace(removed, "Removed:")
                problems = checker.validate_text(broken, require_visual_approved=True, delivery_profile="mvp")
                self.assertTrue([problem for problem in problems if STRUCTURAL.search(problem)])


if __name__ == "__main__":
    unittest.main()

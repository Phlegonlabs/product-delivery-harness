"""Pin the author-side UI rules: three layers, kit and pilot, craft floor, checks per journey."""

import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
HARNESS_ROOT = SKILL_ROOT.parent / "delivery-harness"


def read(relative: str) -> str:
    return " ".join((SKILL_ROOT / relative).read_text(encoding="utf-8").split())


class AuthorSideDocsTests(unittest.TestCase):
    def test_intake_asks_for_impeccable_authorization_once(self):
        intake = read("references/ui-design-intake.md")
        self.assertIn("whether the Impeccable `critique` and `audit` may run on the HiFi", intake)
        self.assertIn("Impeccable workflow authorization: granted | declined", intake)
        self.assertIn("a declined answer leaves the wave `blocked`", intake)

    def test_hifi_has_three_layers_and_one_product_stylesheet(self):
        pass_guide = read("references/ui-design-pass.md")
        self.assertIn("A HiFi package has three layers.", pass_guide)
        for layer in ("**Kit:**", "**Composition:**", "**Art:**"):
            self.assertIn(layer, pass_guide)
        self.assertIn("A page that needs a new control adds it to the kit with every state", pass_guide)
        self.assertIn("The kit holds no cards-as-layout, section recipes or page patterns", pass_guide)
        self.assertIn("holds no required text and no control", pass_guide)
        self.assertIn("measured against that static frame", pass_guide)
        self.assertIn("assemble_ui_review.py --product-css <file>", pass_guide)

    def test_stage_builds_kit_and_pilot_then_locks_the_kit(self):
        stage = read("references/stages/ui-design.md")
        for phrase in (
            "kit and pilot first",
            "The pilot is the core-loop journey plus the landing surface",
            "No kit component is drawn without a pilot page that uses it with real content",
            "the matrix driver with `--only` and `--measure-a11y`",
            "return findings only: no receipts and no score gate",
            "this is a look, not a gate, and no reply means continue",
            "then lock the kit",
            "needs a recorded reason and a rerun of the scripts on every consumer",
            "The author runs the checks after each journey, not once at the end",
            "Skip the pilot diagnosis when the product has one journey or about six pages or fewer",
            "An enhancement assembles from the existing kit or design system and has no pilot",
        ):
            self.assertIn(phrase, stage)
        self.assertLess(stage.index("**Kit and pilot.**"), stage.index("**One batch, then the kit lock.**"))
        self.assertLess(stage.index("**One batch, then the kit lock.**"), stage.index("**Remaining journeys**"))

    def test_craft_floor_is_read_not_run(self):
        stage = read("references/stages/ui-design.md")
        pass_guide = read("references/ui-design-pass.md")
        self.assertIn("reads its `reference/craft-floor.md` after `frontend-design`, right before authoring or repairing", stage)
        self.assertIn("Reading runs no Impeccable command and writes nothing, so it needs no execution authorization", stage)
        self.assertIn("the selected direction, the Design Brief and the PRD win over the craft floor", stage)
        self.assertIn("Reading its craft floor is not running a command", pass_guide)
        self.assertIn("Do not run Impeccable build/refine commands or another visual author on the same candidate in parallel.", pass_guide)
        inputs = read("../delivery-harness/references/frontend-visual-inputs.md")
        self.assertIn("craft-floor.md", inputs)

    def test_author_measures_accessibility_and_owns_the_one_capture(self):
        stage = read("references/stages/ui-design.md")
        pass_guide = read("references/ui-design-pass.md")
        self.assertIn("`--measure-a11y` measurements (contrast, target size, text clip, text split, focus visible, text growth) change no case result",
                      stage)
        self.assertIn("records a disposition with a reason", stage)
        self.assertIn("an undisposed measured failure is a finding", stage)
        self.assertIn("is the candidate's one matrix capture. Nobody captures the same bytes again", stage)
        self.assertIn("The wave uses the author's capture; reviewers do not capture the matrix", stage)
        self.assertIn("the driver with `--carry-from` and `--measure-a11y`", stage)
        self.assertIn("an after-capture for every ledger row", stage)
        self.assertIn("no review is spent", stage)
        self.assertIn("The last clean run on the frozen bytes is the candidate's one matrix capture", pass_guide)
        self.assertIn("The author runs the matrix driver; reviewers do not", pass_guide)


if __name__ == "__main__":
    unittest.main()

"""Contract tests for the UI Design Builder skill."""

import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]


class UiDesignBuilderSkillContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (SKILL_ROOT / relative).read_text(encoding="utf-8")

    def test_skill_owns_ui_after_product_approval(self):
        skill = self.read("SKILL.md")
        self.assertIn("name: ui-design-builder", skill)
        self.assertIn("Product Definition Approval", skill)
        self.assertIn("docs/design/ui-design.md", skill)
        self.assertIn("docs/design/wireframes.html", skill)
        self.assertIn("Do not use for product scope, backend architecture", skill)

    def test_human_intake_precedes_wireframe_and_style(self):
        skill = self.read("SKILL.md")
        intake = skill.index("Run the **UI Design Intake Gate**")
        wireframe = skill.index("Use `frontend-design` in structural mode")
        style = skill.index("Run **Style Integration** with `frontend-design`")
        review = skill.index("Run the **Impeccable HiFi Review")
        self.assertLess(intake, wireframe)
        self.assertLess(wireframe, style)
        self.assertLess(style, review)
        self.assertIn("End the turn and wait", skill)

    def test_frontend_design_authors_and_impeccable_reviews(self):
        skill = self.read("SKILL.md")
        pass_guide = self.read("references/ui-design-pass.md")
        rubric = self.read("references/ui-grading-rubric.md")
        for content in (skill, pass_guide):
            self.assertIn("`frontend-design`", content)
            self.assertIn("`impeccable critique`", content)
            self.assertIn("`impeccable audit`", content)
        self.assertIn("single design author", skill)
        self.assertIn("Impeccable", rubric)
        self.assertIn("`H1`–`H9`", pass_guide)

    def test_motion_and_media_router_is_conditional(self):
        router = self.read("references/motion-and-media-routing.md")
        for marker in (
            "`none`",
            "`image`",
            "`motion`",
            "`image + motion`",
            "`gsap-core`",
            "`gsap-timeline`",
            "`gsap-scrolltrigger`",
            "Higgsfield MCP",
            "exact provider/action authorization",
        ):
            self.assertIn(marker, router)
        self.assertIn("Do not add GSAP merely because motion exists", router)

    def test_new_wireframes_use_schema_four(self):
        checker = self.read("scripts/check_wireframe_html.py")
        template = self.read("assets/templates/WIREFRAMES.template.html")
        guide = self.read("references/wireframe-guide.md")
        for content in (checker, template, guide):
            self.assertIn("wireframes/4", content)
        self.assertIn("wireframes/3", checker)
        self.assertIn("Higgsfield MCP", template)

    def test_copy_freeze_precedes_structural_approval(self):
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        guide = self.read("references/wireframe-guide.md")
        self.assertLess(
            skill.index("Run the **Copy Freeze Gate**"),
            skill.index("Obtain explicit human Wireframe Approval"),
        )
        for marker in ("Copy Freeze:", "Copy owner:", "Copy locale:", "Copy approved on:"):
            self.assertIn(marker, contract)
        self.assertIn("--require-copy-approved", guide)

    def test_output_contract_keeps_tokens_after_visual_approval(self):
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        self.assertLess(
            skill.index("Human Visual Approval"),
            skill.index("Run the **Design System Need Gate** only after"),
        )
        self.assertIn("Design author: frontend-design", contract)
        self.assertIn("Direction decision owner:", contract)
        self.assertIn("Impeccable critique:", contract)
        self.assertIn("Impeccable audit:", contract)
        self.assertIn("Wireframe score:", contract)
        self.assertIn("HiFi score:", contract)
        self.assertIn("H2 score:", contract)
        self.assertIn("H4 score:", contract)
        self.assertIn("H8 score:", contract)
        self.assertIn("docs/design/design-system.md", contract)


if __name__ == "__main__":
    unittest.main()

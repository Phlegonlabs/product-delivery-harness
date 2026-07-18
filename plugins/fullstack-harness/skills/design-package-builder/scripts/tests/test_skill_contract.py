import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


class DesignPackageSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def test_skill_requires_product_specific_visual_thesis(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/visual-decision-guide.md")

        self.assertIn("product-specific visual thesis", skill.lower())
        self.assertIn("## Product-Specific Visual Thesis", guide)
        self.assertIn("## Anti-Generic Review", guide)

    def test_output_contract_and_templates_include_taste_review(self) -> None:
        output_contract = self.read("references/output-contract.md")
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        ui_mockups = self.read("assets/templates/UI_MOCKUPS.template.md")
        visual_acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")

        self.assertIn("## Taste & Anti-Slop Review Checklist", output_contract)
        self.assertIn("## Product-Specific Visual Thesis", design_system)
        self.assertIn("### Product-Specific Design Decisions", ui_mockups)
        self.assertIn("Taste and anti-slop review", visual_acceptance)
        self.assertIn("Rendered visual review loop", visual_acceptance)
        self.assertIn("Spec-only review path", visual_acceptance)
        self.assertIn("````markdown\n# Design System: [Product Name]", output_contract)
        self.assertIn("## Open Questions\n- [Question]\n````", output_contract)

    def test_icon_system_is_routed_and_required_by_templates(self) -> None:
        skill = self.read("SKILL.md")
        icon_guide = self.read("references/icon-system-guide.md")
        output_contract = self.read("references/output-contract.md")
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        ui_mockups = self.read("assets/templates/UI_MOCKUPS.template.md")
        visual_acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")

        self.assertIn("references/icon-system-guide.md", skill)
        self.assertIn("## Current Market Shortlist", icon_guide)
        self.assertIn("## Iconography System", output_contract)
        self.assertIn("## Iconography System", design_system)
        self.assertIn("### Example Icon Usage Code", output_contract)
        self.assertIn("### Example Icon Usage Code", design_system)
        self.assertIn("### Icon Usage", ui_mockups)
        self.assertIn("Icon system conformance", visual_acceptance)

    def test_motion_system_supports_hero_choreography_and_runnable_demo(self) -> None:
        skill = self.read("SKILL.md")
        agent = self.read("agents/openai.yaml")
        motion_guide = self.read("references/motion-system-guide.md")
        output_contract = self.read("references/output-contract.md")
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        ui_mockups = self.read("assets/templates/UI_MOCKUPS.template.md")
        visual_acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")
        motion_showcase = self.read("assets/templates/MOTION_SHOWCASE.template.html")

        self.assertIn("references/motion-system-guide.md", skill)
        self.assertIn("## Hero Section Blueprint", motion_guide)
        self.assertIn("## Motion System", output_contract)
        self.assertIn("### Hero Choreography", design_system)
        self.assertIn("### Motion & Choreography", ui_mockups)
        self.assertIn("Motion system conformance", visual_acceptance)
        self.assertIn('id="reduced-motion"', motion_showcase)
        self.assertIn("Element.prototype.animate", motion_showcase)
        self.assertIn("runnable motion demos when requested", agent)
        self.assertNotIn("runnable hero demos", agent)

    def test_landing_pages_stay_simple_and_trace_media_and_motion(self) -> None:
        skill = self.read("SKILL.md")
        agent = self.read("agents/openai.yaml")
        guide = self.read("references/visual-decision-guide.md")
        output_contract = self.read("references/output-contract.md")
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        ui_mockups = self.read("assets/templates/UI_MOCKUPS.template.md")
        visual_acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")

        self.assertIn("default to KISS", skill)
        self.assertIn("approved or draft exact wording", skill)
        self.assertIn("bounded display contract", skill)
        self.assertIn("Do not mirror the whole PRD on the landing page", guide)
        self.assertIn("colored side rail or accent stripe", guide)
        self.assertIn("supplied exact wording", guide)
        self.assertIn("## Landing Page Simplicity & Media Plan", output_contract)
        self.assertIn("Exact wording / display contract", output_contract)
        self.assertIn("Container and border purpose", output_contract)
        self.assertIn("## Landing Page Simplicity & Media Plan", design_system)
        self.assertIn("### Content Budget", ui_mockups)
        self.assertIn("exact copy / display contract", ui_mockups)
        self.assertIn("required / optional / none", ui_mockups)
        self.assertIn("Content specificity", visual_acceptance)
        self.assertIn("Container and border purpose", visual_acceptance)
        self.assertIn("Landing-page simplicity", visual_acceptance)
        self.assertIn("Media and motion traceability", visual_acceptance)
        self.assertIn("keeps landing pages KISS", agent)
        self.assertIn("preserves exact wording or bounded display contracts", agent)
        self.assertIn("avoids nested frames and decorative accent rails", agent)

    def test_taste_and_border_guardrails_are_required(self) -> None:
        skill = self.read("SKILL.md")
        agent = self.read("agents/openai.yaml")
        guide = self.read("references/visual-decision-guide.md")
        output_contract = self.read("references/output-contract.md")
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        ui_mockups = self.read("assets/templates/UI_MOCKUPS.template.md")
        visual_acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")

        self.assertIn("one-sentence taste statement", skill)
        self.assertIn("## Taste & Anti-Slop Guardrails", guide)
        self.assertIn("### Container & Border Decision Rules", guide)
        self.assertIn("Use the removal test", guide)
        self.assertIn("## Taste & Anti-Slop Guardrails", output_contract)
        self.assertIn("### Container & Border Rules", output_contract)
        self.assertIn("one primary grouping cue", output_contract)
        self.assertIn("Taste statement:", design_system)
        self.assertIn("Ordinary content section | open", design_system)
        self.assertIn("Container and border treatment", ui_mockups)
        self.assertIn("Container and border purpose", visual_acceptance)
        self.assertIn("defaults ordinary regions to open layouts", agent)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
UI_SKILL_ROOT = SKILL_ROOT.parent / "ui-design-builder"


class DesignSystemCompilerSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def read_ui(self, relative_path: str) -> str:
        return (UI_SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def test_compilation_requires_approved_product_stack_and_ui(self) -> None:
        skill = self.read("SKILL.md")
        for marker in (
            "Product Definition Approval",
            "Stack Decision Checkpoint",
            "docs/design/ui-design.md",
            "approved Wireframe and Visual decisions",
            "Design System Need Gate: required",
            "check_product_package.py",
        ):
            self.assertIn(marker, skill)

    def test_product_and_ui_ownership_are_separate(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        self.assertIn("`PRD.md` owns product behavior", skill)
        self.assertIn("`ui-design-builder` owns", skill)
        self.assertIn("docs/design/ui-design.md", contract)
        self.assertIn("docs/design/wireframes.html", lifecycle)
        self.assertIn("docs/design/design-system.md", lifecycle)
        self.assertIn("Legacy `docs/product/wireframes.html`", lifecycle)

    def test_compilation_uses_frontend_design_without_reopening_direction(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/design-system-guide.md")
        agent = self.read("agents/openai.yaml")

        for content in (skill, guide, agent):
            self.assertIn("frontend-design", content)
        self.assertIn("## Compilation Skills Gate", skill)
        self.assertIn("If `frontend-design` cannot be loaded, stop", skill)
        self.assertIn("Do not rerun `frontend-design`, Impeccable", guide)
        self.assertIn("returns to `ui-design-builder`", skill)
        self.assertNotIn("$impeccable", agent)
        self.assertNotIn("$design-taste-frontend", agent)

    def test_direction_reopen_routes_to_ui_design_builder(self) -> None:
        skill = self.read("SKILL.md")
        route = self.read("references/visual-direction-guide.md")
        retired = self.read("references/impeccable-concept-generation.md")

        self.assertIn("stop compilation and invoke `../ui-design-builder/SKILL.md`", skill)
        self.assertIn("no longer owns visual-direction exploration", route)
        self.assertIn("frontend-design` as the single design author", retired)
        self.assertIn("Impeccable runs afterward in evaluate mode", retired)

    def test_motion_variants_follow_ui_design_intent(self) -> None:
        skill = self.read("SKILL.md")
        self.assertIn("Motion and Media Intent", skill)
        self.assertIn("registered variant plus reduced-motion behavior", skill)
        self.assertIn("Higgsfield", skill)
        self.assertIn("media sources, not UI-state implementations", skill)

    def test_visual_reference_protocol_is_owned_upstream(self) -> None:
        references = self.read_ui("references/design-reference-guide.md")
        ui_pass = self.read_ui("references/ui-design-pass.md")

        for marker in ("`REF-*`", "`RP-*`", "Adopt / Adapt / Avoid", "`VD-R<round>-<number>`"):
            self.assertIn(marker, references)
        self.assertIn("end the turn for confirmation", ui_pass)
        self.assertIn("one product-specific direction", ui_pass)
        self.assertIn("exactly three materially different directions", ui_pass)
        self.assertIn("Impeccable does not generate directions", references)

    def test_design_pair_is_minimal_and_reconciled_to_approved_sources(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/design-system-guide.md")
        contract = self.read("references/output-contract.md")
        template_md = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        template_json = self.read("assets/templates/DESIGN_SYSTEM.template.json")

        self.assertIn("PRD UI Surface Contract", skill)
        self.assertIn("docs/design/ui-design.md", guide)
        self.assertIn("Every required PRD element maps to the final registry", contract)
        self.assertIn("Approved UI design contract", template_md)
        self.assertIn("Style Integration and HiFi evidence", template_md)
        self.assertIn('"schema": "design-system/1"', template_json)
        self.assertIn('"requiredContentOrder"', template_json)

    def test_templates_and_checker_commands_belong_to_this_skill(self) -> None:
        skill = self.read("SKILL.md")
        self.assertIn("Run these from the repository root", skill)
        self.assertIn("skills/design-system-compiler/scripts/check_design_system_pair.py", skill)
        self.assertIn("scripts/check_color_contrast.py", skill)
        self.assertIn("scripts/check_type_scale.py", skill)

    def test_responsive_contract_matches_approved_sources_and_blocks_overlap(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/design-system-guide.md")
        contract = self.read("references/output-contract.md")
        template_md = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        template_json = self.read("assets/templates/DESIGN_SYSTEM.template.json")

        for content in (skill, guide, contract, template_md, template_json):
            self.assertIn("at least two", content)
        self.assertIn("matches the PRD and approved wireframe set", skill)
        self.assertIn("Copy the exact approved PRD and wireframe set", guide)
        self.assertIn("Unintended overlap, clipping, occlusion", guide)
        self.assertIn("passing browser-matrix evidence", contract)
        self.assertIn("named stacking, focus, and dismissal", template_md)


if __name__ == "__main__":
    unittest.main()

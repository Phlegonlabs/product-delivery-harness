import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


class DesignSystemCompilerSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def test_pair_compilation_requires_frontend_design_and_skips_reexploration(self) -> None:
        skill = self.read("SKILL.md")
        directions = self.read("references/visual-direction-guide.md")
        design_system = self.read("references/design-system-guide.md")
        agent = self.read("agents/openai.yaml")

        for content in (skill, design_system, agent):
            self.assertIn("frontend-design", content)
        self.assertIn("## Compilation Skills Gate", skill)
        self.assertIn(
            "If `frontend-design` cannot be loaded, stop",
            skill,
        )
        self.assertIn("Do not draft, revise, or validate", skill)
        self.assertIn("Do not rerun visual-direction generation", design_system)
        self.assertIn("only when the human owner explicitly asks", directions)
        self.assertNotIn("$impeccable", agent)
        self.assertNotIn("$design-taste-frontend", agent)

    def test_prd_and_wireframes_own_structure_and_design_builder_owns_only_the_pair(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        for content in (skill, contract):
            self.assertIn("`PRD.md` owns", content)
            self.assertIn("`wireframes.html`", content)
            self.assertNotIn("wireframes.md", content)
            self.assertIn("`design-system.md`", content)
            self.assertIn("`design-system.json`", content)
        self.assertIn("Publish the two design-system files", lifecycle)
        self.assertIn("approved wireframe HTML", lifecycle)
        self.assertIn("wireframes.html", lifecycle)
        self.assertIn("outside `docs/product/`", lifecycle)

    def test_human_owner_controls_assumptions_before_drafting(self) -> None:
        skill = self.read("SKILL.md")
        directions = self.read("references/visual-direction-guide.md")

        self.assertIn("approved `### UI Design Handoff`", skill)
        self.assertIn("the agent cannot self-authorize it", directions)
        self.assertIn("return the bounded decision update to `product-definition-builder`", directions)
        self.assertIn("Do not edit `PRD.md` from this skill", directions)

    def test_named_required_sources_must_be_readable(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn("If a required source is named but missing or unreadable, stop", skill)
        self.assertIn("is not a substitute for reading it", skill)

    def test_style_intake_pauses_before_reference_informed_directions(self) -> None:
        directions = self.read("references/visual-direction-guide.md")

        self.assertIn("### Style And Reference Intake", directions)
        self.assertIn("### Reference-Informed Direction Recommendations", directions)
        self.assertLess(
            directions.index("### Style And Reference Intake"),
            directions.index("### Reference-Informed Direction Recommendations"),
        )
        self.assertIn("End the turn and wait for the answer", directions)
        self.assertIn("exactly three materially different, product-specific style directions", directions)
        self.assertIn("Do not add a fourth", directions)
        self.assertIn("explicitly asks", directions)

    def test_market_design_evidence_is_traceable_and_does_not_overclaim(self) -> None:
        directions = self.read("references/visual-direction-guide.md")

        self.assertIn("`MR-*` and `S-*` source IDs", directions)
        self.assertIn("Use only `sourced` or `reported` findings", directions)
        self.assertIn("Treat `UNVALIDATED` rows as open questions, not evidence", directions)
        self.assertIn("Label every resulting design implication as an inference", directions)
        self.assertIn("Do not claim that a recommendation is market-research-backed", directions)

    def test_creation_mode_requires_the_exact_skill_set(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn(
            "`required_skills` must contain `design-system-compiler` and `frontend-design`",
            skill,
        )
        self.assertIn("distinct from Harness UI implementation conformance mode", skill)

    def test_ui_preview_gate_is_provider_neutral_and_noncanonical(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("../product-definition-builder/references/ui-design-pass.md")
        contract = self.read("references/output-contract.md")

        self.assertIn("../product-definition-builder/references/ui-design-pass.md", skill)
        self.assertIn("rendered HTML or temporary React", guide)
        self.assertIn("imagegen-frontend-web", guide)
        self.assertIn("another named image-generation", guide)
        self.assertIn("does not require Codex", guide)
        self.assertIn("approved UI Design Handoff", contract)

    def test_taste_applicability_and_optional_brandkit_are_bounded(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("../product-definition-builder/references/ui-design-pass.md")

        self.assertIn("Do not reload `design-taste-frontend`", skill)
        self.assertIn("Do not load `gpt-taste` by default", guide)
        self.assertIn("never combine it with `design-taste-frontend`", guide)
        self.assertIn("Optional `brandkit` exploration", guide)
        self.assertIn("explicitly authorizes", guide)

    def test_impeccable_generation_is_bounded_by_canonical_sources(self) -> None:
        skill = self.read("SKILL.md")
        bridge = self.read("references/impeccable-concept-generation.md")
        directions = self.read("references/visual-direction-guide.md")
        design_system = self.read("references/design-system-guide.md")
        contract = self.read("references/output-contract.md")

        self.assertIn("references/impeccable-concept-generation.md", skill)
        self.assertIn("surface-mode, cultural-world, and challenger pass", directions)
        self.assertIn("Do not create `PRODUCT.md`, `DESIGN.md`, `.impeccable/`", bridge)
        self.assertIn("Do not run `concept-seed.mjs` directly here", bridge)
        self.assertIn("Normalize the result into exactly three materially distinct", bridge)
        for marker in ("surface mode", "concept thesis", "named visual world"):
            self.assertIn(marker, design_system)
            self.assertIn(marker, contract)

    def test_visual_references_require_confirmed_principles(self) -> None:
        directions = self.read("references/visual-direction-guide.md")
        references = self.read("references/design-reference-guide.md")
        design_system = self.read("references/design-system-guide.md")

        self.assertIn("`Adopt / Adapt / Avoid`", directions)
        self.assertIn("Only confirmed `RP-*` items", references)
        self.assertIn("end the turn for confirmation", directions)
        self.assertIn("confirmed `RP-*` `Adopt / Adapt / Avoid` principles", design_system)

    def test_visual_reference_evidence_is_source_specific(self) -> None:
        skill = self.read("SKILL.md")
        references = self.read("references/design-reference-guide.md")

        self.assertIn("Only when the owner explicitly asks to reopen direction", skill)
        self.assertIn("references/design-reference-guide.md", skill)
        for marker in ("`MR-*`", "`S-*`", "`REF-*`", "`RP-*`"):
            self.assertIn(marker, references)
        self.assertIn("record protocol also governs the `product-definition-builder` UI Design Pass", references)
        self.assertIn("keeps its own one-direction default and preview gate", references)
        self.assertIn("Do not fabricate references, URLs, access dates, or observed traits", references)
        self.assertIn("never invoke them automatically", references)

    def test_design_pair_is_minimal_and_reconciled_to_prd(self) -> None:
        skill = self.read("SKILL.md")
        design_system = self.read("references/design-system-guide.md")
        contract = self.read("references/output-contract.md")
        template_md = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        template_json = self.read("assets/templates/DESIGN_SYSTEM.template.json")

        self.assertIn("PRD UI surface contract", skill)
        self.assertIn("PRD UI surface contract", design_system)
        self.assertIn("`wireframes.html` has explicit human-owner approval", design_system)
        self.assertIn("Every required PRD element maps to the final registry", contract)
        self.assertIn("PRD UI surface contract", template_md)
        self.assertIn("Approved wireframe", template_md)
        self.assertIn('"schema": "design-system/1"', template_json)
        self.assertIn('"requiredContentOrder"', template_json)

    def test_templates_and_checker_commands_belong_to_this_skill(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn("Run these from the repository root", skill)
        self.assertIn(
            ".agents/skills/design-system-compiler/scripts/check_design_system_pair.py",
            skill,
        )
        self.assertIn("scripts/check_color_contrast.py", skill)
        self.assertIn("scripts/check_type_scale.py", skill)


if __name__ == "__main__":
    unittest.main()

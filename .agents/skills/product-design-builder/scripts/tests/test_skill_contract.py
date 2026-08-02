import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


class ProductDesignBuilderSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def test_frontend_design_is_a_fail_closed_dependency(self) -> None:
        skill = self.read("SKILL.md")
        wireframes = self.read("references/wireframe-guide.md")
        design_system = self.read("references/design-system-guide.md")
        agent = self.read("agents/openai.yaml")

        for content in (skill, wireframes, design_system, agent):
            self.assertIn("frontend-design", content)
        self.assertIn("## Mandatory Frontend Design Gate", skill)
        self.assertIn("If `frontend-design` is unavailable or cannot be loaded, stop", skill)
        self.assertIn("Do not draft, revise, or validate", skill)
        self.assertIn("If `frontend-design` is unavailable, stop", wireframes)
        self.assertIn("If `frontend-design` is unavailable, stop", design_system)
        self.assertNotIn("optional `frontend-design`", skill)
        self.assertNotIn("fallback design path is allowed", skill)

    def test_frontend_design_gate_precedes_every_design_step(self) -> None:
        skill = self.read("SKILL.md")

        gate = skill.index("## Mandatory Frontend Design Gate")
        workflow = skill.index("## Workflow")
        self.assertLess(gate, workflow)
        self.assertIn("1. Pass the Mandatory Frontend Design Gate.", skill)
        self.assertIn(
            "Before creating or revising any wireframe, visual direction, token, primitive, component, motion rule, or responsive rule",
            skill,
        )

    def test_human_owner_controls_assumptions_before_drafting(self) -> None:
        skill = self.read("SKILL.md")
        wireframes = self.read("references/wireframe-guide.md")

        self.assertIn("verify its Builder UX Direction Gate", skill)
        self.assertIn("Every `assumed` answer requires that owner's explicit authorization", skill)
        self.assertIn("the agent cannot self-authorize it", wireframes)
        self.assertIn("return the bounded decision update to `prd-builder`", wireframes)
        self.assertIn("Do not edit `PRD.md` from this skill", wireframes)

    def test_named_required_sources_must_be_readable(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn("If a required source is named but missing or unreadable, stop", skill)
        self.assertIn("is not a substitute for reading it", skill)

    def test_style_and_reference_intake_is_one_pause_before_directions(self) -> None:
        skill = self.read("SKILL.md")
        wireframes = self.read("references/wireframe-guide.md")

        self.assertIn("combined Style And Reference Intake", skill)
        self.assertIn("### Style And Reference Intake", wireframes)
        self.assertIn("what style they want and whether they already have visual references in one combined", wireframes)
        self.assertIn("End the turn and wait for the answer", wireframes)
        self.assertLess(
            wireframes.index("### Style And Reference Intake"),
            wireframes.index("### Reference-Informed Direction Recommendations"),
        )

    def test_style_questions_pause_before_three_reference_informed_recommendations(self) -> None:
        skill = self.read("SKILL.md")
        wireframes = self.read("references/wireframe-guide.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("`market-research.md` and the `MR-*` citations", skill)
        self.assertIn("### Reference-Informed Direction Recommendations", wireframes)
        self.assertIn("Ask the human owner what style they want and whether they already have visual references", wireframes)
        self.assertIn("End the turn and wait for the answer", wireframes)
        self.assertIn("exactly three materially different, product-specific style directions", wireframes)
        self.assertIn("Do not add a fourth", wireframes)
        self.assertIn("ask once for my style and visual references", agent)
        self.assertIn("exactly three product-specific directions", agent)

    def test_market_design_evidence_is_traceable_and_does_not_overclaim(self) -> None:
        skill = self.read("SKILL.md")
        wireframes = self.read("references/wireframe-guide.md")

        self.assertIn("Market Design Evidence Brief", skill)
        self.assertIn("`MR-*` and `S-*` source IDs", wireframes)
        self.assertIn("Use only `sourced` or `reported` findings", wireframes)
        self.assertIn("Treat `UNVALIDATED` rows as open questions, not evidence", wireframes)
        self.assertIn("label every resulting design implication as an inference", wireframes)
        self.assertIn("Do not claim that a recommendation is market-research-backed", wireframes)

    def test_creation_mode_requires_the_exact_skill_pair(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn("`required_skills` must contain both `product-design-builder` and `frontend-design`", skill)
        self.assertIn("This is distinct from Harness UI implementation conformance mode", skill)
        self.assertIn("creation mode", skill)

    def test_design_artifacts_have_one_owner_and_one_lifecycle(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        for name in ("wireframes.md", "design-system.md", "design-system.json"):
            self.assertIn(name, skill)
            self.assertIn(name, contract)
            self.assertIn(name, lifecycle)
        self.assertIn("Publish the three files as one reconciled set", lifecycle)
        self.assertIn("Publish or revise them together", contract)
        self.assertIn("`design-system.json` for the machine-readable", skill)

    def test_visual_directions_keep_product_structure_frozen(self) -> None:
        skill = self.read("SKILL.md")
        wireframes = self.read("references/wireframe-guide.md")

        self.assertIn("exactly three materially different product-specific directions", skill)
        self.assertIn("same representative screens, structure, content responsibilities, states, and trace IDs", skill)
        self.assertIn("scope, routes, content responsibilities, interaction behavior, and trace IDs are frozen", wireframes)
        self.assertIn("Candidate and selected HTML are non-canonical design-stage evidence", wireframes)

    def test_visual_references_require_confirmed_principles(self) -> None:
        wireframes = self.read("references/wireframe-guide.md")
        references = self.read("references/design-reference-guide.md")
        design_system = self.read("references/design-system-guide.md")

        self.assertIn("`Adopt / Adapt / Avoid`", wireframes)
        self.assertIn("Only confirmed `RP-*` items", references)
        self.assertIn("end the turn for confirmation", wireframes)
        self.assertIn("confirmed `RP-*` `Adopt / Adapt / Avoid` principles", design_system)
        self.assertIn("do not become final token values", design_system)

    def test_visual_reference_evidence_is_separate_and_source_specific(self) -> None:
        skill = self.read("SKILL.md")
        references = self.read("references/design-reference-guide.md")

        for trigger in ("image/screenshot/URL/Figma/named-product", "current public design-reference discovery"):
            self.assertIn(trigger, skill)
        for marker in ("`MR-*`", "`S-*`", "`REF-*`", "`RP-*`"):
            self.assertIn(marker, references)
        for source_type in (
            "Attached image or screenshot",
            "Figma view",
            "Live URL",
            "Named product",
            "Agent-discovered reference",
        ):
            self.assertIn(source_type, references)
        for evidence_status in ("`observed`", "`measured`", "`inferred`", "`not observable`"):
            self.assertIn(evidence_status, references)
        self.assertIn("Never add `REF-*` or `RP-*` rows to `market-research.md`", references)
        self.assertIn("proposed `RP-*` items resolving to those inspected sources", references)
        self.assertIn("Preserve existing `REF-*`, `RP-*`, and selected `VD-*` identities", references)
        self.assertIn("never reuse a retired ID", references)
        self.assertIn("at most two related representative pages", references)
        self.assertIn("Compare desktop and mobile", references)
        self.assertIn("Never bypass permissions", references)

    def test_static_and_blocked_sources_cannot_create_fabricated_evidence(self) -> None:
        references = self.read("references/design-reference-guide.md")

        self.assertIn("A static image cannot establish motion, responsive behavior, hover, focus, or interaction transitions", references)
        self.assertIn("A single viewport cannot establish responsive behavior", references)
        self.assertIn("Do not fabricate references, URLs, access dates, or observed traits", references)
        self.assertIn("do not fall back to unaided design", references)

    def test_three_directions_have_current_references_and_adaptive_modern_coverage(self) -> None:
        skill = self.read("SKILL.md")
        wireframes = self.read("references/wireframe-guide.md")
        references = self.read("references/design-reference-guide.md")

        self.assertIn("exactly three materially different product-specific directions", skill)
        self.assertIn("one current public visual reference for every direction", skill)
        self.assertIn("one contemporary/modern direction by default", skill)
        self.assertIn("a second only when preference, product constraints, and valid evidence support", skill)
        self.assertIn("VD-R1-01", references)
        self.assertIn("Do not add a fourth", wireframes)
        self.assertIn("not a fixed catalog entry or `modern-minimal` default", wireframes)

    def test_lightweight_direction_pass_is_owner_initiated_only(self) -> None:
        skill = self.read("SKILL.md")
        wireframes = self.read("references/wireframe-guide.md")
        references = self.read("references/design-reference-guide.md")

        self.assertIn("lightweight direction pass", skill)
        self.assertIn("never initiate that reduction yourself", skill)
        self.assertIn("Lightweight exception", references)
        self.assertIn("one direction with one inspected current public reference", references)
        self.assertIn("must not propose or initiate the reduction", references)
        self.assertIn("Record that request in the Builder UX Direction decision", references)
        self.assertIn("every other rule in this guide still applies", references)
        self.assertIn("owner-requested lightweight direction pass", wireframes)
        self.assertIn("which the agent never proposes", wireframes)

    def test_selection_and_reference_revision_keep_tokens_unfixed(self) -> None:
        skill = self.read("SKILL.md")
        references = self.read("references/design-reference-guide.md")

        for action in ("`Select`", "`Mix`", "`Reject`", "`Check This`"):
            self.assertIn(action, references)
        self.assertIn("versioned revised set of exactly three directions", skill)
        self.assertIn("VD-R2-01", references)
        self.assertIn("when some directions are rejected", references)
        self.assertIn("complete versioned set of exactly three rather than appending candidates", references)
        self.assertIn("If all are rejected", references)
        self.assertIn("Do not fix tokens, primitives, components, or motion variants", references)
        self.assertIn("explicitly confirmed", skill)

    def test_selected_direction_keeps_compact_reference_provenance(self) -> None:
        design_system = self.read("references/design-system-guide.md")
        contract = self.read("references/output-contract.md")
        template_md = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        template_json = self.read("assets/templates/DESIGN_SYSTEM.template.json")

        for marker in ("`VD-*`", "`MR-*`", "`REF-*`", "`RP-*`"):
            self.assertIn(marker, design_system)
        self.assertIn("## Reference Influence", template_md)
        self.assertIn("full extraction history remains outside the package", contract)
        self.assertIn('"schema": "design-system/1"', template_json)
        self.assertNotIn('"references"', template_json)

    def test_reference_extraction_does_not_auto_start_clone_workflows(self) -> None:
        references = self.read("references/design-reference-guide.md")

        self.assertIn("`image-to-code` and `url-to-code` are separate", references)
        self.assertIn("never invoke them automatically", references)
        for protected in ("HTML/CSS", "exact copy", "distinctive composition"):
            self.assertIn(protected, references)

    def test_templates_and_checker_commands_belong_to_this_skill(self) -> None:
        skill = self.read("SKILL.md")
        template_md = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        template_json = self.read("assets/templates/DESIGN_SYSTEM.template.json")

        self.assertIn("Run these from the repository root", skill)
        self.assertIn(
            ".agents/skills/product-design-builder/scripts/check_design_system_pair.py",
            skill,
        )
        self.assertNotIn("Run these from the skill directory", skill)
        self.assertIn("scripts/check_color_contrast.py", skill)
        self.assertIn("scripts/check_type_scale.py", skill)
        self.assertIn("This design system is the frontend implementation contract", template_md)
        self.assertIn('"schema": "design-system/1"', template_json)
        self.assertIn('"requiredContentOrder"', template_json)


if __name__ == "__main__":
    unittest.main()

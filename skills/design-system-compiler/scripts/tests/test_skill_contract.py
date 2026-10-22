import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
UI_SKILL_ROOT = SKILL_ROOT.parent / "ui-design-builder"
STAGE = "references/stages/design-compilation.md"


class DesignSystemCompilerSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def read_ui(self, relative_path: str) -> str:
        return (UI_SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def stage_headings(self, text: str) -> set[str]:
        headings = set()
        for line in text.splitlines():
            if not line.startswith("#"):
                continue
            heading = line.lstrip("#").strip().lower()
            heading = re.sub(r"[^a-z0-9\s-]", "", heading)
            heading = re.sub(r"\s+", "-", heading.strip())
            headings.add(heading)
        return headings

    def test_compilation_requires_approved_product_stack_and_ui(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(STAGE)
        for marker in (
            "Product Definition Approval",
            "Stack Decision Checkpoint",
            "docs/design/ui-design.md",
            "complete approved `ui-hifi/2` package",
            "Visual Approval",
            "Design System Need Gate: required",
        ):
            self.assertIn(marker, skill)
        self.assertIn("check_product_package.py", stage)
        self.assertIn(
            "`sourceBindings.uiDesign.sha256` uses the canonical UI approval digest",
            skill,
        )
        self.assertIn("Package action: compile|update|reuse", skill)

    def test_product_and_ui_ownership_are_separate(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(STAGE)
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        self.assertIn("`PRD.md` owns product behavior", skill)
        self.assertIn("`ui-design-builder` owns", skill)
        self.assertIn("Product scope", stage)
        self.assertIn("gaps return to `product-definition-builder`", stage)
        self.assertIn("HiFi-package gaps return to `ui-design-builder`", stage)
        self.assertIn("docs/design/ui-design.md", contract)
        self.assertIn("approved HiFi target", lifecycle)
        self.assertIn("docs/design/design-system.md", lifecycle)
        self.assertIn("Legacy `docs/product/wireframes.html`", lifecycle)

    def test_compilation_uses_frontend_design_without_reopening_direction(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(STAGE)
        guide = self.read("references/design-system-guide.md")
        agent = self.read("agents/openai.yaml")

        for content in (skill, stage, guide, agent):
            self.assertIn("frontend-design", content)
        self.assertIn("## Compilation Skills Gate", stage)
        self.assertIn("If `frontend-design` cannot be loaded, stop", stage)
        self.assertIn("Do not rerun `frontend-design`, Impeccable", guide)
        self.assertIn("returns to `ui-design-builder`", stage)
        self.assertIn("`frontend-design` is required without a fallback", skill)
        self.assertNotIn("$impeccable", agent)
        self.assertNotIn("$design-taste-frontend", agent)

    def test_direction_reopen_routes_to_ui_design_builder(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(STAGE)
        route = self.read("references/visual-direction-guide.md")
        retired = self.read("references/impeccable-concept-generation.md")

        self.assertIn("compilation does not reopen direction", skill)
        self.assertIn(
            "stop compilation and invoke `../ui-design-builder/SKILL.md`",
            stage,
        )
        self.assertIn("no longer owns visual-direction exploration", route)
        self.assertIn("frontend-design` as the single design author", retired)
        self.assertIn("Impeccable runs afterward for critique and audit", retired)

    def test_motion_variants_follow_ui_design_intent(self) -> None:
        stage = self.read(STAGE)
        self.assertIn("Motion and Media Intent", stage)
        self.assertIn("registered variant plus reduced-motion behavior", stage)
        self.assertIn("Higgsfield", stage)
        self.assertIn("media sources, not UI-state implementations", stage)

    def test_visual_reference_protocol_is_owned_upstream(self) -> None:
        references = self.read_ui("references/design-reference-guide.md")
        ui_pass = self.read_ui("references/ui-design-pass.md")

        for marker in ("`REF-*`", "`RP-*`", "Adopt / Adapt / Avoid", "`VD-R<round>-<number>`"):
            self.assertIn(marker, references)
        self.assertIn("end the turn for confirmation", ui_pass)
        self.assertIn("one product-specific direction", ui_pass)
        self.assertIn("Direction mode: one recommended direction", ui_pass)
        self.assertIn("this applies to `ui-design/3` and `ui-design/2` alike", ui_pass)
        self.assertIn("Continuing uncertainty or silence never converts into that instruction", ui_pass)
        self.assertIn("exactly three materially different directions", ui_pass)
        self.assertIn("Impeccable does not generate directions", references)

    def test_design_pair_is_minimal_and_reconciled_to_approved_sources(self) -> None:
        stage = self.read(STAGE)
        guide = self.read("references/design-system-guide.md")
        contract = self.read("references/output-contract.md")
        template_md = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        template_json = self.read("assets/templates/DESIGN_SYSTEM.template.json")

        self.assertIn("PRD UI Surface Contract", stage)
        self.assertIn("stable `UI-*`, `UX-*`, `DS-*`, and `DS-COMP-*` IDs", stage)
        self.assertIn("docs/design/ui-design.md", guide)
        self.assertIn("Every required PRD element maps to the final registry", contract)
        self.assertIn("Approved UI design contract", template_md)
        self.assertIn("Style Integration and HiFi evidence", template_md)
        self.assertIn('"schema": "design-system/3"', template_json)
        self.assertIn('"sourceBindings"', template_json)
        self.assertIn('"hifi"', template_json)
        self.assertIn('"requiredContentOrder"', template_json)

    def test_inputs_name_the_sections_compilation_reads(self) -> None:
        stage = self.read(STAGE)
        inputs = stage.split("## Inputs And Ownership", 1)[1].split("\n## ", 1)[0]

        self.assertNotIn("Read the current sources in full", inputs)
        self.assertIn("read only these sections of the current sources", inputs)
        self.assertIn("checkers still join each complete source", inputs)
        for section in (
            "`UI Surface Contract`",
            "`Frontend Delivery Requirements`",
            "`Motion And Media Intent`",
            "`HiFi Review` result and score lines",
            "`Design System Need Gate`",
            "`Frontend Architecture` and `Release Targets`",
            "`Stack Decision Checkpoint`",
        ):
            self.assertIn(section, inputs)
        self.assertIn("Skip the reviewer shell and inline asset data", inputs)
        self.assertIn("Read another section when a finding", inputs)

    def test_preview_browser_inspection_is_conditional_on_live_treatments(self) -> None:
        contract = self.read("references/output-contract.md")

        self.assertNotIn("Inspect the generated view in a browser and link", contract)
        self.assertIn(
            "When the pair registers a motion variant or a `pseudo` state row, or the preview has Surface plates "
            "that run product scripts, inspect those plates in a browser",
            contract,
        )
        self.assertIn("`verify_runtime_motion.py` still closes source-runtime rows", contract)
        self.assertIn("Close compilation only after", contract)
        self.assertIn("Link the view with the pair in the handoff", contract)

    def test_templates_and_checker_commands_belong_to_this_skill(self) -> None:
        stage = self.read(STAGE)
        self.assertIn("Run these from the repository root", stage)
        self.assertIn(
            "<design-system-compiler-skill-root>/scripts/check_design_system_pair.py",
            stage,
        )
        self.assertIn("scripts/check_color_contrast.py", stage)
        self.assertIn("scripts/check_type_scale.py", stage)

    def test_pair_less_preflight_runs_inside_the_pair_checker(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(STAGE)
        guide = self.read("references/design-system-guide.md")
        self.assertIn(
            "pair-less preflight has no separate command; it runs inside `check_design_system_pair.py --repo-root`",
            stage,
        )
        self.assertIn("there is no separate preflight command", guide)
        self.assertIn("Design System Need Gate", skill)
        self.assertNotIn("Run the UI builder's exact pair-less preflight", skill)

    def test_responsive_contract_matches_approved_sources_and_blocks_overlap(self) -> None:
        stage = self.read(STAGE)
        guide = self.read("references/design-system-guide.md")
        contract = self.read("references/output-contract.md")
        template_md = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        template_json = self.read("assets/templates/DESIGN_SYSTEM.template.json")

        for content in (stage, guide, contract, template_md, template_json):
            self.assertIn("at least two", content)
        self.assertIn("all sets match the PRD, approved HiFi scope, and stack", stage)
        self.assertIn("Copy the exact approved PRD and HiFi set", guide)
        self.assertIn("Unintended overlap, clipping, occlusion", guide)
        self.assertIn("passing browser-matrix evidence", contract)
        self.assertIn("named stacking, focus, and dismissal", template_md)

    def test_template_responsive_set_comes_from_prd_and_hifi(self) -> None:
        template_md = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        responsive = next(
            line for line in template_md.splitlines() if line.startswith("- Responsive set:")
        )
        self.assertIn("exact approved PRD and HiFi manifest viewports or sizeClasses", responsive)
        self.assertIn("wireframe JSON only for a legacy design-system/2 pair", responsive)
        self.assertNotIn("PRD and wireframe JSON", responsive)

    def test_stage_routing_is_conditional_and_targets_exist(self) -> None:
        entry = self.read("SKILL.md")
        stage = self.read(STAGE)
        lifecycle_path = SKILL_ROOT / "references/artifact-lifecycle.md"
        lifecycle = lifecycle_path.read_text(encoding="utf-8")
        anchors = self.stage_headings(stage)

        self.assertTrue((SKILL_ROOT / STAGE).is_file())
        for trigger, anchor in (
            ("compile or update", "compilation-skills-gate"),
            ("compile or update", "inputs-and-ownership"),
            ("compile or update", "workflow"),
            ("compile or update", "validation"),
            ("compile or update", "output-rules"),
            ("validate or reuse", "compilation-skills-gate"),
            ("validate or reuse", "inputs-and-ownership"),
            ("validate or reuse", "validation"),
            ("publication", "output-rules"),
            ("domain decision or reference route", "reference-routing"),
        ):
            with self.subTest(trigger=trigger, anchor=anchor):
                self.assertIn(trigger, entry)
                self.assertRegex(entry, rf"\({re.escape(STAGE)}#{anchor}\)")
                self.assertIn(anchor, anchors)

        self.assertRegex(
            entry,
            r"\(references/artifact-lifecycle.md#design-system-artifact-lifecycle\)",
        )
        self.assertIn("# Design System Artifact Lifecycle", lifecycle)
        self.assertIn("Do not reselect the stack or visual direction", entry)
        self.assertIn("Validation includes mutating `--write` commands", entry)
        self.assertIn("does not auto-authorize publication", entry)

        for document_name, document in (("SKILL.md", entry), (STAGE, stage)):
            document_path = SKILL_ROOT / document_name
            for link_target in re.findall(r"\[[^]]+\]\(([^)]+)\)", document):
                path_text, separator, anchor = link_target.partition("#")
                target = document_path if not path_text else (document_path.parent / path_text).resolve()
                self.assertTrue(target.exists(), (document_name, link_target))
                if separator:
                    self.assertIn(anchor, self.stage_headings(target.read_text(encoding="utf-8")), (document_name, link_target))

    def test_missing_route_or_anchor_fails_closed(self) -> None:
        entry = self.read("SKILL.md")
        stage = self.read(STAGE)
        anchors = self.stage_headings(stage)

        missing_route = entry.replace(
            " [Artifact Lifecycle](references/artifact-lifecycle.md#design-system-artifact-lifecycle)",
            "",
        )
        self.assertNotRegex(
            missing_route,
            r"\(references/artifact-lifecycle.md#design-system-artifact-lifecycle\)",
        )

        missing_anchor = stage.replace("## Output Rules", "## Publication")
        self.assertNotIn("output-rules", self.stage_headings(missing_anchor))

        broken_pointer = entry.replace(
            "design-compilation.md#workflow", "design-compilation.md#missing-workflow"
        )
        self.assertNotRegex(
            broken_pointer,
            rf"\({re.escape(STAGE)}#workflow\)",
        )
        self.assertIn("#missing-workflow", broken_pointer)
        self.assertIn("workflow", anchors)

    def test_stage_is_not_a_concatenation_of_reference_sources(self) -> None:
        entry = self.read("SKILL.md")
        stage = self.read(STAGE)

        self.assertLess(len(entry.split()), 1000)
        self.assertLess(len(stage.split()), 2200)
        for heading in (
            "## Compilation Skills Gate",
            "## Inputs And Ownership",
            "## Workflow",
            "## Validation",
            "## Reference Routing",
            "## Output Rules",
        ):
            self.assertIn(heading, stage)
        for foreign_marker in (
            "## Drafting Order",
            "## Approved Input Quality Check",
            "Publish or archive the Markdown and JSON files together",
        ):
            self.assertNotIn(foreign_marker, stage)


if __name__ == "__main__":
    unittest.main()

import json
import re
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


class SpecimenContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.specimens: list[list[str]] = []
        self.specimens_by_section: dict[str, list[list[str]]] = {}
        self._section_id: str | None = None
        self._article_depth = 0
        self._fields: list[str] | None = None
        self._in_contract = False
        self._capture_dt = False
        self._dt_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "section":
            self._section_id = attributes.get("id")
        if tag == "article":
            if self._fields is not None:
                self._article_depth += 1
            elif "specimen" in classes:
                self._fields = []
                self._article_depth = 1
        if self._fields is not None and tag == "dl" and "contract" in classes:
            self._in_contract = True
        if self._in_contract and tag == "dt":
            self._capture_dt = True
            self._dt_text = []

    def handle_data(self, data: str) -> None:
        if self._capture_dt:
            self._dt_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "dt" and self._capture_dt:
            assert self._fields is not None
            self._fields.append("".join(self._dt_text).strip())
            self._capture_dt = False
        elif tag == "dl" and self._in_contract:
            self._in_contract = False
        elif tag == "article" and self._fields is not None:
            self._article_depth -= 1
            if self._article_depth == 0:
                self.specimens.append(self._fields)
                if self._section_id is not None:
                    self.specimens_by_section.setdefault(self._section_id, []).append(self._fields)
                self._fields = None
        elif tag == "section":
            self._section_id = None


class UiArchitectureSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def run_dynamic_workflow(
        self,
        workflow_args: dict[str, object],
        runtime_prelude: str = "",
    ) -> subprocess.CompletedProcess[str]:
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required to execute the Dynamic Workflow template")

        workflow_source = self.read(
            "assets/templates/CLAUDE_DESIGN_WORKFLOW.template.js"
        ).replace("export const meta =", "const meta =", 1)
        script = (
            f"const args = {json.dumps(json.dumps(workflow_args))};\n"
            f"{runtime_prelude}\n"
            "const result = await (async () => {\n"
            f"{workflow_source}\n"
            "})();\n"
            "console.log(JSON.stringify(result));"
        )
        return subprocess.run(
            [node, "--input-type=module", "--eval", script],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )

    def test_skill_requires_product_specific_visual_thesis(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/visual-decision-guide.md")

        self.assertIn("product-specific visual thesis", skill.lower())
        self.assertIn("## Product-Specific Visual Thesis", guide)
        self.assertIn("## Anti-Generic Review", guide)

    def test_output_contract_and_templates_include_taste_review(self) -> None:
        output_contract = self.read("references/output-contract.md")
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        page_recipes = self.read("assets/templates/PAGE_RECIPES.template.md")
        visual_acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")

        self.assertIn("## Taste & Anti-Slop Review Checklist", output_contract)
        self.assertIn("## Product-Specific Visual Thesis", design_system)
        self.assertIn("Product-specific decisions:", page_recipes)
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
        visual_acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")

        self.assertIn("references/icon-system-guide.md", skill)
        self.assertIn("## Current Market Shortlist", icon_guide)
        self.assertIn("## Iconography System", output_contract)
        self.assertIn("## Iconography System", design_system)
        self.assertIn("### Example Icon Usage Code", output_contract)
        self.assertIn("### Example Icon Usage Code", design_system)
        self.assertIn("Icon system conformance", visual_acceptance)

    def test_motion_system_supports_hero_choreography_and_runnable_demo(self) -> None:
        skill = self.read("SKILL.md")
        agent = self.read("agents/openai.yaml")
        motion_guide = self.read("references/motion-system-guide.md")
        output_contract = self.read("references/output-contract.md")
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        page_recipes = self.read("assets/templates/PAGE_RECIPES.template.md")
        visual_acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")
        motion_showcase = self.read("assets/templates/MOTION_SHOWCASE.template.html")

        self.assertIn("references/motion-system-guide.md", skill)
        self.assertIn("## Hero Section Blueprint", motion_guide)
        self.assertIn("## Motion System", output_contract)
        self.assertIn("### Hero Choreography", design_system)
        self.assertIn("Motion choreography:", page_recipes)
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
        page_recipes = self.read("assets/templates/PAGE_RECIPES.template.md")
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
        self.assertIn("Content budget (landing/content-heavy pages only):", page_recipes)
        self.assertIn("exact copy / display contract", page_recipes)
        self.assertIn("required / optional / none", page_recipes)
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
        page_recipes = self.read("assets/templates/PAGE_RECIPES.template.md")
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
        self.assertIn("Container and border treatment", page_recipes)
        self.assertIn("Container and border purpose", visual_acceptance)
        self.assertIn("defaults ordinary regions to open layouts", agent)

    def test_builder_ux_direction_is_preserved_without_claiming_usability(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/design-interview-guide.md")
        guide = self.read("references/visual-decision-guide.md")
        contract = self.read("references/output-contract.md")
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        visual_acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")
        agent = self.read("agents/openai.yaml")

        for content in (skill, interview, guide, contract, design_system, visual_acceptance, agent):
            self.assertIn("Builder UX Direction", content)
        self.assertIn("selected`, `provisional`, or `assumed`", skill)
        self.assertIn("Builder approval proves direction conformance only", contract)
        self.assertIn("does not prove usability", guide)
        self.assertIn("Builder UX Direction conformance", visual_acceptance)

    def test_trace_ids_and_safe_artifact_lifecycle_are_required(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        page_recipes = self.read("assets/templates/PAGE_RECIPES.template.md")
        acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")

        for trace_prefix in ("`PRD-*`", "`ARCH-*`", "`UI-*`", "`UX-*`", "`TEST-*`", "`DS-*`"):
            self.assertIn(trace_prefix, skill)
        self.assertIn("| DS ID | Cue / signature decision", contract)
        self.assertIn(
            "| UI ID | Route / screen | Recipe | Mockup HTML | Upstream trace IDs | DS IDs",
            page_recipes,
        )
        self.assertIn("| TEST ID | Gate | Required | Upstream trace IDs", acceptance)
        self.assertIn("docs/product/.design-staging/<run-id>/", lifecycle)
        self.assertIn("Passing validation does not authorize overwrite, move, or archive", lifecycle)
        self.assertIn("ask one explicit yes/no publication question", skill)
        self.assertIn("execute the canonical publish moves in the same run", skill)
        self.assertIn("Exploration evidence:", design_system)
        self.assertIn("exact final archive or retained", design_system)
        self.assertIn("Exploration evidence:", contract)
        self.assertIn("exact final archive or retained", contract)
        self.assertNotIn(
            "screen names and docs/product/.design-staging",
            design_system,
        )
        candidate_move = lifecycle.index("3. Apply the approved exploration-evidence disposition:")
        provenance_rewrite = lifecycle.index(
            "4. Rewrite staged `design-system.md`'s `Exploration evidence`",
            candidate_move,
        )
        revalidate = lifecycle.index(
            "revalidate the canonical staged package",
            provenance_rewrite,
        )
        publish = lifecycle.index(
            "5. Move the revalidated staged artifacts",
            revalidate,
        )
        self.assertLess(candidate_move, provenance_rewrite)
        self.assertLess(provenance_rewrite, revalidate)
        self.assertLess(revalidate, publish)

    def test_enhancement_mode_freezes_baseline_and_checks_non_regression(self) -> None:
        skill = self.read("SKILL.md")
        lifecycle = self.read("references/artifact-lifecycle.md")
        contract = self.read("references/output-contract.md")
        architecture = self.read("assets/templates/UI_ARCHITECTURE.template.md")
        acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")
        agent = self.read("agents/openai.yaml")

        for content in (skill, lifecycle, contract, architecture, agent):
            self.assertIn("enhancement baseline", content.lower())
        self.assertIn("## Enhancement Baseline & Delta", architecture)
        self.assertIn("| Delta ID | Action | Target IDs / artifacts", architecture)
        self.assertIn("seed staging", lifecycle.lower())
        self.assertIn("preserve every untouched", skill.lower())
        self.assertIn("apply only accepted add/modify/remove delta", agent)
        self.assertIn("package enhancement", skill)
        self.assertIn("implementation adoption mode", skill)
        self.assertIn("Do not run the fresh-generation Dynamic Workflow", skill)
        self.assertIn("Validate the complete staged package", skill)
        self.assertIn("TEST-VIS-025 | Enhancement non-regression", acceptance)
        self.assertIn("baseline-to-staged diff / full package validation", acceptance)
        self.assertIn("TEST-VIS-025 | Enhancement non-regression", contract)

    def test_frontend_design_explores_html_before_human_approved_extraction(self) -> None:
        skill = self.read("SKILL.md")
        architecture = self.read("references/ui-architecture-guide.md")
        guide = self.read("references/visual-decision-guide.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")
        workflow = self.read("references/dynamic-workflow.md")
        workflow_template = self.read(
            "assets/templates/CLAUDE_DESIGN_WORKFLOW.template.js"
        )
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        agent = self.read("agents/openai.yaml")

        for content in (skill, guide, contract, design_system, agent):
            self.assertIn("Frontend Design Preference & HTML Exploration", content)
        for content in (skill, architecture, guide, contract, lifecycle, design_system):
            self.assertIn("non-canonical", content)
        for content in (skill, guide, contract, lifecycle, agent):
            self.assertIn("exactly two or three", content)
            self.assertIn("same one or two", content)
        self.assertIn("Purpose, Tone, Constraints, and Differentiation", skill)
        self.assertIn("Never present a fixed catalog of styles", skill)
        self.assertIn("host's Ask User tool", skill)
        self.assertIn("invoke `frontend-design` separately", skill)
        self.assertIn("complete dependency-free HTML", skill)
        self.assertIn("at least three relevant axes", skill)
        self.assertIn("Candidate-local CSS values", skill)
        for content in (skill, architecture, guide, contract, lifecycle, design_system):
            self.assertIn("visual-directions/selected/", content)
        self.assertIn("Selection by an agent, including delegated selection", skill)
        self.assertIn("does not unlock token extraction", skill)
        self.assertIn("explicitly approved selected HTML", skill)
        self.assertLess(
            architecture.index("**Dynamic Visual Preference Discovery.**"),
            architecture.index("**Two or three candidate HTML directions.**"),
        )
        self.assertLess(
            architecture.index("**Human comparison and selected HTML.**"),
            architecture.index("**Token extraction.**"),
        )
        self.assertIn(
            "docs/product/.design-staging/<run-id>/visual-directions/<direction-id>/",
            lifecycle,
        )
        self.assertIn("Implementation consumes the extracted package", contract)
        self.assertIn("selected-HTML consolidation, or approval is still pending", workflow)
        self.assertIn('visual_direction_pass.status: "not used"', workflow)
        self.assertIn("visual_direction_pass: visualDirectionPass", workflow_template)
        self.assertIn("status not used, approved, or rejected", workflow_template)
        self.assertIn(
            "Status: <not used / preference discovery / candidates awaiting comparison / selected HTML awaiting approval / approved / rejected>",
            design_system,
        )
        self.assertIn(
            "Status: [not used / preference discovery / candidates awaiting comparison / selected HTML awaiting approval / approved / rejected]",
            contract,
        )
        self.assertIn("Limit preference questions, representative screens, candidate directions, and selected HTML to the accepted delta", guide)
        self.assertIn("TEST-VIS-027 | HTML direction comparison and approval", contract)
        self.assertIn("TEST-VIS-028 | Approved-HTML extraction fidelity", contract)
        self.assertNotIn("Offer `frontend-design` only for the small pieces", skill)

    def test_dynamic_workflow_rejects_missing_visual_direction_pass_at_runtime(self) -> None:
        workflow_args = {
            "run_id": "RUN-TEST",
            "product_name": "Test Product",
            "product_archetype": "web_app",
            "source_paths": [],
            "icons_in_scope": False,
            "motion_in_scope": False,
            "tool_profile": "builder_readonly",
        }
        result = self.run_dynamic_workflow(workflow_args)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "requires args.visual_direction_pass status not used, approved, or rejected",
            result.stderr,
        )

    def test_dynamic_workflow_accepts_documented_not_used_status_at_runtime(self) -> None:
        workflow_args = {
            "run_id": "RUN-TEST",
            "product_name": "Test Product",
            "product_archetype": "web_app",
            "source_paths": [],
            "icons_in_scope": False,
            "motion_in_scope": False,
            "tool_profile": "builder_readonly",
            "visual_direction_pass": {"status": "not used"},
        }
        runtime_prelude = """
const phase = () => {};
const parallel = async (tasks) => Promise.all(tasks.map((task) => task()));
const agent = async (_prompt, options) => {
  const role = options.label.replace("design:", "");
  if (role === "synthesis") return {};
  if (options.phase === "Analyze") return { role, status: "complete" };
  return { role, decision: "pass" };
};
"""
        result = self.run_dynamic_workflow(workflow_args, runtime_prelude)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "candidate_ready")

    def test_dynamic_workflow_rejects_approved_status_without_human_evidence(self) -> None:
        workflow_args = {
            "run_id": "RUN-TEST",
            "product_name": "Test Product",
            "product_archetype": "web_app",
            "source_paths": [],
            "icons_in_scope": False,
            "motion_in_scope": False,
            "tool_profile": "builder_readonly",
            "visual_direction_pass": {"status": "approved"},
        }
        result = self.run_dynamic_workflow(workflow_args)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "requires non-empty args.visual_direction_pass.selected_html_path",
            result.stderr,
        )

    def test_dynamic_workflow_rejects_approved_status_without_candidate_html(self) -> None:
        workflow_args = {
            "run_id": "RUN-TEST",
            "product_name": "Test Product",
            "product_archetype": "web_app",
            "source_paths": [],
            "icons_in_scope": False,
            "motion_in_scope": False,
            "tool_profile": "builder_readonly",
            "visual_direction_pass": {
                "status": "approved",
                "selected_html_path": "visual-directions/selected/index.html",
                "approval_owner": "Human owner",
                "approval_evidence": "Approved in Ask User response",
                "representative_ui_ids": ["UI-001"],
                "candidate_directions": [
                    {"direction_id": "A", "html_paths": ["a.html"]},
                    {"direction_id": "B", "html_paths": []},
                ],
            },
        }
        result = self.run_dynamic_workflow(workflow_args)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "one non-empty html_path per representative UI ID",
            result.stderr,
        )

    def test_interview_uses_three_dependency_waves_and_portable_closed_choices(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/design-interview-guide.md")
        agent = self.read("agents/openai.yaml")

        for content in (skill, interview, agent):
            self.assertIn("at most three dependency waves", content)
            self.assertIn("at most four", content)
            self.assertIn("platform-independent", content)
            self.assertIn("conditional platform resolution", content.lower())
            self.assertIn("structured closed-choice", content)
            self.assertIn("numbered", content)
            self.assertIn("Other", content)
        self.assertIn("Never ask styling, theming, or runtime questions", interview)
        self.assertIn("without selecting a default or converting", skill)
        self.assertNotIn("one or two `AskUserQuestion` calls", interview)
        self.assertNotIn("never opening a third call", agent)

    def test_motion_purpose_vocabulary_is_canonical(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/motion-system-guide.md")
        contract = self.read("references/output-contract.md")
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")

        canonical = "feedback, continuity, processing, or storytelling"
        self.assertIn(canonical, skill)
        self.assertIn(canonical, guide)
        self.assertIn(canonical, contract)
        self.assertIn(canonical, design_system)
        self.assertNotIn("feedback, orientation, continuity, emphasis, or storytelling", design_system)
        self.assertNotIn("decorative/ambient", guide)
        hero_section = guide.split("## Hero Section Blueprint", 1)[1].split(
            "## Non-Hero Choreography Blueprints", 1
        )[0]
        self.assertEqual(hero_section.count("storytelling —"), 5)
        self.assertIn("There is no decorative or ambient exception", contract)

    def test_rendered_design_system_is_fixed_complete_and_derived(self) -> None:
        skill = self.read("SKILL.md")
        lifecycle = self.read("references/artifact-lifecycle.md")
        contract = self.read("references/output-contract.md")
        architecture = self.read("assets/templates/UI_ARCHITECTURE.template.md")
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        showcase = self.read("assets/templates/DESIGN_SYSTEM_SHOWCASE.template.html")
        acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")
        agent = self.read("agents/openai.yaml")

        fixed_path = "docs/product/design/design-system.html"
        self.assertIn(f"`{fixed_path}` (always", lifecycle)
        self.assertIn(f"`{fixed_path}` (always)", skill)
        self.assertIn(f"## `{fixed_path}`", contract)
        self.assertIn("## Rendered Design System", architecture)
        self.assertIn("## Rendered HTML Projection", design_system)
        for content in (skill, lifecycle, contract, architecture, design_system, showcase, agent):
            lowered = content.lower()
            self.assertTrue(
                "second authority" in lowered
                or "semantic source" in lowered
                or "semantic authority" in lowered
                or "second source of truth" in lowered
            )
        for section_id in (
            "tokens",
            "type",
            "buttons",
            "forms",
            "states",
            "surfaces",
            "navigation",
            "status",
            "icons",
            "layout",
            "motion",
            "responsive",
        ):
            with self.subTest(section=section_id):
                self.assertIn(f'id="{section_id}"', showcase)
        for required in (
            "Typography hierarchy",
            "Buttons: variants, sizes, and states",
            "Form controls and field messaging",
            "Cards and surfaces",
            "Alerts and status",
            "Spacing and layout primitives",
            "Motion and reduced motion",
            "Responsive behavior",
            "<dt>IDs</dt>",
            "<dt>Parameters</dt>",
        ):
            with self.subTest(required=required):
                self.assertIn(required, showcase)
        self.assertIn("preserve this file unchanged", contract.lower())
        self.assertIn("rebuild", lifecycle.lower())
        self.assertIn("TEST-VIS-026 | Rendered design-system parity", acceptance)
        self.assertIn("TEST-VIS-026 | Rendered design-system parity", contract)

    def test_every_design_system_specimen_has_reproduction_metadata(self) -> None:
        showcase = self.read("assets/templates/DESIGN_SYSTEM_SHOWCASE.template.html")
        parser = SpecimenContractParser()
        parser.feed(showcase)

        required_fields = [
            "IDs",
            "Parameters",
            "States",
            "Responsive",
            "Accessibility",
            "Use",
            "Do not use",
        ]
        required_sections = {
            "tokens",
            "type",
            "buttons",
            "forms",
            "states",
            "surfaces",
            "navigation",
            "status",
            "icons",
            "layout",
            "motion",
            "responsive",
        }
        self.assertGreater(len(parser.specimens), 0)
        for section_id in required_sections:
            with self.subTest(section=section_id):
                self.assertGreater(len(parser.specimens_by_section.get(section_id, [])), 0)
        for index, fields in enumerate(parser.specimens, start=1):
            with self.subTest(specimen=index):
                self.assertEqual(fields, required_fields)

        self.assertIn('id="states"', showcase)
        for state in ("Loading", "Disabled", "Error", "Empty"):
            with self.subTest(state=state):
                self.assertIn(f">{state}<", showcase)
        self.assertIn("aria-busy", showcase)
        self.assertIn('role="alert"', showcase)
        self.assertIn("prefers-reduced-motion", showcase)

    def test_design_system_showcase_uses_only_derived_tokens_below_the_token_block(self) -> None:
        showcase = self.read("assets/templates/DESIGN_SYSTEM_SHOWCASE.template.html")
        css = showcase.split("<style>", 1)[1].split("</style>", 1)[0]
        token_block, rendered_rules = css.split("/* END DERIVED TOKEN BLOCK */", 1)

        raw_value_pattern = re.compile(
            r"#[0-9a-fA-F]{3,8}\b|"
            r"(?:rgba?|hsla?)\([^)]*\)|"
            r"(?<![-\w])(?:transparent|white|black)(?![-\w])|"
            r"(?<![-\w.])-?(?:\d*\.\d+|\d+)"
            r"(?:px|rem|em|ms|s|vh|vw|vmin|vmax|%|fr|deg|rad|turn)\b"
        )
        self.assertEqual(raw_value_pattern.findall(rendered_rules), [])

        without_variable_names = re.sub(r"var\(--[a-z0-9-]+\)", "", rendered_rules)
        raw_unitless_number = re.compile(
            r"(?<![-\w.])-?(?:\d*\.\d+|\d+)(?![-\w.])"
        )
        self.assertEqual(raw_unitless_number.findall(without_variable_names), [])

        declared = set(re.findall(r"--([a-z0-9-]+)\s*:", token_block))
        referenced = set(re.findall(r"var\(--([a-z0-9-]+)\)", rendered_rules))
        self.assertEqual(referenced - declared, set())
        self.assertIn("--projection-border-width:", token_block)
        self.assertIn("--projection-motion-transform:", token_block)

    def test_showcase_focus_token_has_non_text_contrast_and_fields_are_described(self) -> None:
        showcase = self.read("assets/templates/DESIGN_SYSTEM_SHOWCASE.template.html")

        def token(name: str) -> str:
            match = re.search(rf"{re.escape(name)}:\s*(#[0-9a-fA-F]{{6}});", showcase)
            self.assertIsNotNone(match, name)
            assert match is not None
            return match.group(1)

        def luminance(color: str) -> float:
            channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [
                value / 12.92
                if value <= 0.04045
                else ((value + 0.055) / 1.055) ** 2.4
                for value in channels
            ]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        def contrast(first: str, second: str) -> float:
            lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
            return (lighter + 0.05) / (darker + 0.05)

        focus = token("--color-focus")
        for adjacent_token in ("--color-surface", "--color-background", "--color-accent"):
            with self.subTest(adjacent=adjacent_token):
                self.assertGreaterEqual(contrast(focus, token(adjacent_token)), 3.0)

        self.assertIn('aria-describedby="field-help"', showcase)
        self.assertIn('id="field-help" class="field-help"', showcase)
        self.assertIn('aria-describedby="invalid-field-help field-error"', showcase)
        self.assertIn('id="invalid-field-help" class="field-help"', showcase)
        self.assertIn('id="field-error" class="field-error"', showcase)

    def test_visual_acceptance_resolves_the_platform_responsive_set(self) -> None:
        acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")
        contract = self.read("references/output-contract.md")

        for content in (acceptance, contract):
            self.assertIn("Responsive set verified:", content)
            self.assertIn("web `viewports`", content)
            self.assertIn("native `sizeClasses` and safe areas", content)
            self.assertIn("named desktop window sizes", content)
        self.assertNotIn(
            "Viewports verified: 390 / 768 / 1200 / 1440 px.",
            acceptance,
        )

    def test_motion_contract_separates_mechanism_and_global_reduced_motion(self) -> None:
        contract = self.read("references/output-contract.md")
        design_system = self.read("assets/templates/DESIGN_SYSTEM.template.md")
        acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")

        for content in (contract, design_system):
            self.assertIn("| Mechanism | Technology | Owns |", content)
            self.assertNotIn("| Layer / purpose | Technology |", content)
            self.assertIn("### Global Reduced-Motion Configuration", content)
            self.assertIn("| Motion ID | Surface / component | Mechanism | Purpose |", content)
            self.assertIn("| Configuration point | Location | Normal behavior", content)
            self.assertIn("route-level opt-out", content.lower())
            self.assertIn("Call sites do not query reduced-motion preferences", content)
        self.assertIn("mechanism separately from approved purpose", acceptance)
        self.assertIn("global reduced-motion configuration", acceptance)

    def test_design_acceptance_preserves_upstream_test_identity(self) -> None:
        skill = self.read("SKILL.md")
        acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")
        contract = self.read("references/output-contract.md")

        self.assertIn("generic `TEST-*` IDs", skill)
        self.assertIn("mint only `TEST-VIS-*` IDs", skill)
        self.assertIn("preserved upstream TEST-*", acceptance)
        self.assertIn("upstream TEST identities are preserved", contract)

    def test_dynamic_workflow_uses_design_org_roles_and_parent_staging(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/dynamic-workflow.md")
        workflow = self.read("assets/templates/CLAUDE_DESIGN_WORKFLOW.template.js")
        contract = self.read("references/output-contract.md")

        self.assertIn("stable design roles as an org graph", skill)
        self.assertIn("The stable org graph", guide)
        self.assertIn("The temporary work graph", guide)
        self.assertIn('typeof args === "string" ? JSON.parse(args) : args', workflow)
        self.assertIn('phase("Analyze")', workflow)
        self.assertIn("await parallel", workflow)
        self.assertIn('phase("Synthesize")', workflow)
        self.assertIn('phase("Verify")', workflow)
        self.assertIn("workflow-agent-null", workflow)
        self.assertIn("workflow-role-mismatch", workflow)
        self.assertIn("builder_readonly", workflow)
        self.assertIn("machine-enforced `builder_readonly`", guide)
        self.assertIn("Read only. Do not edit, create, move, or publish files", workflow)
        self.assertIn("does not create production images", guide)
        self.assertIn("Workflow output is a candidate", contract)


class UiArchitectureContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def test_architecture_guide_owns_the_layer_model_and_binding_rule(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/ui-architecture-guide.md")
        contract = self.read("references/output-contract.md")

        self.assertIn("references/ui-architecture-guide.md", skill)
        self.assertIn("A page cannot be freely designed", skill)
        self.assertIn("A page cannot be freely designed", guide)
        self.assertIn("## Layer Model", guide)
        self.assertIn("## Source Of Truth Precedence", guide)
        self.assertIn("## Derivation Method", guide)
        self.assertIn("## Closed Variant Sets", guide)
        self.assertIn("Page-specific preference", guide)
        self.assertIn("page cannot be freely designed", contract)

    def test_package_declares_the_new_artifact_set(self) -> None:
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        for artifact in (
            "`ui-architecture.md`",
            "`ui-registry.json`",
            "`design-system.md`",
            "`docs/product/design/design-system.html`",
            "`page-recipes.md`",
            "`visual-acceptance.md`",
            "`mockups/catalog.html`",
        ):
            self.assertIn(artifact, contract)
        self.assertIn("ui-registry.json", lifecycle)
        self.assertIn("Do not produce `page-ui-matrix.md` or `ui-mockups.md`", contract)

    def test_templates_exist_for_every_required_artifact(self) -> None:
        for template in (
            "assets/templates/UI_ARCHITECTURE.template.md",
            "assets/templates/UI_REGISTRY.template.json",
            "assets/templates/DESIGN_SYSTEM.template.md",
            "assets/templates/DESIGN_SYSTEM_SHOWCASE.template.html",
            "assets/templates/PAGE_RECIPES.template.md",
            "assets/templates/VISUAL_ACCEPTANCE.template.md",
            "assets/templates/MOCKUP_PAGE.template.html",
            "assets/templates/CATALOG.template.html",
        ):
            with self.subTest(template=template):
                self.assertTrue((SKILL_ROOT / template).is_file())

        for retired in (
            "assets/templates/UI_MOCKUPS.template.md",
            "assets/templates/PAGE_UI_MATRIX.template.md",
        ):
            with self.subTest(retired=retired):
                self.assertFalse((SKILL_ROOT / retired).exists())

    def test_registry_template_is_a_valid_closed_allowlist(self) -> None:
        registry = json.loads(self.read("assets/templates/UI_REGISTRY.template.json"))

        self.assertIn("tokenSources", registry)
        self.assertIs(registry["rawValuesAllowedOutsideTokens"], False)
        self.assertIs(registry["inlineLayoutStylesAllowed"], False)
        self.assertIs(registry["pageLocalControlStylingAllowed"], False)
        self.assertEqual(registry["viewports"], [390, 768, 1200, 1440])
        self.assertEqual(len(registry["stateMatrix"]), 11)
        for name, spec in registry["primitives"].items():
            with self.subTest(primitive=name):
                self.assertIn("layer", spec)
                self.assertIs(spec["rawStylesAllowed"], False)
        for name, spec in registry["productComponents"].items():
            with self.subTest(component=name):
                self.assertIn("contract", spec)
                self.assertIn("requiredContentOrder", spec)
                self.assertIs(spec["reorderable"], False)
        for route, recipe in registry["recipes"].items():
            with self.subTest(route=route):
                for field in (
                    "container",
                    "sectionDensity",
                    "sections",
                    "allowedSurfaces",
                    "forbiddenPatterns",
                    "requiredStates",
                ):
                    self.assertIn(field, recipe)

    def test_architecture_template_carries_contracts_states_and_guardrails(self) -> None:
        architecture = self.read("assets/templates/UI_ARCHITECTURE.template.md")

        for section in (
            "## Layer Model",
            "## Source Of Truth Precedence",
            "## Content Contracts",
            "## Primitive Contracts",
            "### Layout Primitives",
            "### Surface Primitives",
            "### Typography Primitives",
            "### Control Primitives",
            "## Product Components",
            "## Motion Architecture",
            "### Registered Motion Variants",
            "## State Matrix",
            "## Registry",
            "## Rendered Design System",
            "## Catalog",
            "## Automated Guardrails",
            "## Definition Of Done",
            "## Adoption Sequence",
        ):
            with self.subTest(section=section):
                self.assertIn(section, architecture)
        self.assertIn("Closed variants", architecture)
        self.assertIn("Required content order is binding", architecture)
        self.assertIn("390 / 768 / 1200 / 1440", architecture)

    def test_recipes_are_binding_and_carry_forbidden_patterns(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        recipes = self.read("assets/templates/PAGE_RECIPES.template.md")
        guide = self.read("references/ui-architecture-guide.md")

        self.assertIn("blocker", skill)
        self.assertIn("## Page Recipes", guide)
        self.assertIn("Forbidden patterns", recipes)
        self.assertIn("## Forbidden Patterns Registry", recipes)
        self.assertIn("Must render without JavaScript", recipes)
        self.assertIn("Forbidden patterns carry as much weight", contract)

    def test_mockups_and_catalog_must_obey_the_architecture(self) -> None:
        contract = self.read("references/output-contract.md")
        mockup = self.read("assets/templates/MOCKUP_PAGE.template.html")
        catalog = self.read("assets/templates/CATALOG.template.html")

        self.assertIn("read the route's recipe", contract)
        self.assertIn("registry-named", contract)
        self.assertIn("prefers-reduced-motion", mockup)
        for viewport in ("390", "768", "1200", "1440"):
            with self.subTest(viewport=viewport):
                self.assertIn(viewport, mockup)
        self.assertIn("ui-registry.json", mockup)
        self.assertIn("ui-registry.json", catalog)

    def test_guardrails_are_specified_here_and_run_by_the_harness(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/ui-architecture-guide.md")
        architecture = self.read("assets/templates/UI_ARCHITECTURE.template.md")

        # The contract check runs at implementation time, against real source.
        # This skill specifies the guardrails; it does not ship or run the check.
        self.assertFalse((SKILL_ROOT / "scripts/check_ui_contract.py").exists())
        harness_script = (
            SKILL_ROOT.parent
            / "fullstack-harness-engineering"
            / "scripts"
            / "check_ui_contract.py"
        )
        self.assertTrue(harness_script.is_file())
        self.assertIn("## Automated Guardrails", guide)
        self.assertIn("fullstack-harness-engineering", guide)
        self.assertIn("Specifying them is this skill's job", skill)
        self.assertIn("## Automated Guardrails", architecture)
        self.assertIn("not run against this package's mockups", architecture)

    def test_acceptance_gates_exist(self) -> None:
        contract = self.read("references/output-contract.md")
        acceptance = self.read("assets/templates/VISUAL_ACCEPTANCE.template.md")

        for gate in (
            "Registry conformance",
            "Page recipe conformance",
            "Content contract conformance",
            "State matrix coverage",
            "Contract check",
            "Catalog completeness",
            "No-JavaScript path",
            "Rendered design-system parity",
        ):
            with self.subTest(gate=gate):
                self.assertIn(gate, acceptance)
                self.assertIn(gate, contract)


class PackageParityTests(unittest.TestCase):
    """Mechanical parity between files that must describe the same system.

    Name-only assertions let the contract and its template drift on substance
    while staying green, so these compare whole rows and whole key sets.
    """

    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    @staticmethod
    def _gate_rows(text: str) -> dict[str, str]:
        rows: dict[str, str] = {}
        for line in text.splitlines():
            match = re.match(r"\|\s*(TEST-VIS-\d+)\s*\|(.*)$", line.strip())
            if match:
                cells = [cell.strip() for cell in match.group(2).split("|")]
                rows[match.group(1)] = " | ".join(cell for cell in cells if cell)
        return rows

    def test_acceptance_gate_rows_match_the_contract(self) -> None:
        contract = self._gate_rows(self.read("references/output-contract.md"))
        template = self._gate_rows(self.read("assets/templates/VISUAL_ACCEPTANCE.template.md"))

        self.assertEqual(sorted(contract), sorted(template))
        for gate_id, row in contract.items():
            with self.subTest(gate=gate_id):
                self.assertEqual(row, template[gate_id])

    @staticmethod
    def _slug(name: str) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "-", name.strip("<>")).lower()

    def _registry_classes(self) -> tuple[set[str], set[str]]:
        """Base classes and every modifier class the registry implies.

        A value the registry marks as an axis default is realized as the bare
        base class, so it yields no modifier. Bracketed values are template
        placeholders, not class names.
        """
        registry = json.loads(self.read("assets/templates/UI_REGISTRY.template.json"))
        bases: set[str] = set()
        classes: set[str] = set()
        skip = {
            "layer",
            "class",
            "defaults",
            "rawStylesAllowed",
            "minTargetPx",
            "requiresAccessibleName",
        }
        for name, spec in registry["primitives"].items():
            base = spec.get("class", self._slug(name))
            defaults = spec.get("defaults", {})
            bases.add(base)
            classes.add(base)
            for axis, values in spec.items():
                if axis in skip or not isinstance(values, list):
                    continue
                for value in values:
                    raw = str(value)
                    if "<" in raw or " " in raw or raw == defaults.get(axis):
                        continue
                    slug = self._slug(raw)
                    if axis == "gaps":
                        classes.add(f"gap-{slug}")
                    else:
                        classes.update({f"{base}--{slug}", f"{base}-{slug}"})
        return bases, classes

    @staticmethod
    def _used_classes(markup: str) -> set[str]:
        used: set[str] = set()
        for match in re.finditer(r'class="([^"]*)"', markup):
            used.update(match.group(1).split())
        return used

    def test_html_templates_use_registered_primitives(self) -> None:
        bases, registered = self._registry_classes()
        for template in ("MOCKUP_PAGE", "CATALOG"):
            used = self._used_classes(self.read(f"assets/templates/{template}.template.html"))
            with self.subTest(template=template):
                # Scaffolding is allowed, but it may never squat on a registered
                # primitive's variant namespace — that reads as an unregistered
                # variant of a real primitive.
                squatting = {
                    name
                    for name in used - registered
                    if "--" in name and name.split("--", 1)[0] in bases
                }
                self.assertEqual(squatting, set())

    def test_every_registered_variant_appears_in_the_catalog(self) -> None:
        _, registered = self._registry_classes()
        catalog = self._used_classes(self.read("assets/templates/CATALOG.template.html"))
        modifiers = {name for name in registered if "--" in name}

        # The catalog is the two-way reference: every registered variant must be
        # visible there. Both spellings are generated per axis, so a variant
        # counts as shown when either form appears.
        missing = {
            name
            for name in modifiers
            if name not in catalog and name.replace("--", "-") not in catalog
        }
        self.assertEqual(missing, set())

    def test_workflow_roles_match_the_role_graph(self) -> None:
        graph = self.read("references/dynamic-workflow.md")
        workflow = self.read("assets/templates/CLAUDE_DESIGN_WORKFLOW.template.js")

        documented = {
            match.group(1)
            for match in re.finditer(r"^\|\s*([a-z][a-z-]+)\s*\|", graph, re.M)
        }
        # A role is implemented either as a fan-out entry with a `key`, or as a
        # single labeled agent call in its own phase (synthesis).
        coded = set(re.findall(r'key:\s*"([a-z][a-z-]+)"', workflow))
        coded |= set(re.findall(r'label:\s*"design:([a-z][a-z-]+)"', workflow))

        self.assertEqual(documented, coded)


if __name__ == "__main__":
    unittest.main()

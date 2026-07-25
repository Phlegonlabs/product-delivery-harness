import json
import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


class UiArchitectureSkillContractTests(unittest.TestCase):
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
        self.assertIn("execute the approved publish and archive moves in the same run", skill)

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

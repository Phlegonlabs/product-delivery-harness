import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


class PrdBuilderSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def test_skill_routes_browser_products_to_frontend_selection(self) -> None:
        skill = self.read("SKILL.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("references/frontend-stack-selection.md", skill)
        self.assertIn("recommend one explicit stack", skill)
        self.assertIn("recommendation is not misrepresented as a fixed requirement", skill)
        self.assertIn("Cloudflare is a deployment/runtime platform", skill)
        self.assertIn("when the product has a browser surface", agent)

    def test_completed_prd_offers_opt_in_design_package_handoff(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn(
            "ask whether the user wants to run the `design-package-builder` skill next",
            skill,
        )
        self.assertIn("Do not invoke the design skill without an explicit yes", skill)
        self.assertIn(
            "do not offer the handoff while the PRD workflow is incomplete",
            skill,
        )

    def test_selection_guide_separates_layers_and_product_patterns(self) -> None:
        guide = self.read("references/frontend-stack-selection.md")

        self.assertIn("## First Separate the Layers", guide)
        self.assertIn("## Product-Fit Patterns", guide)
        self.assertIn("Astro + React islands", guide)
        self.assertIn("React + Vite", guide)
        self.assertIn("Cloudflare Workers with Static Assets", guide)
        self.assertIn("## Official Sources to Recheck", guide)

    def test_output_contract_requires_decision_and_verification(self) -> None:
        contract = self.read("references/output-contract.md")

        self.assertIn("## Frontend Delivery Requirements", contract)
        self.assertIn("## Frontend Technology Decision", contract)
        self.assertIn("Decision status: [Required / Selected / Recommended / Provisional]", contract)
        self.assertIn("### Recorded or Recommended Stack", contract)
        self.assertIn("### Rendering and Route Strategy", contract)
        self.assertIn("### Platform Compatibility Verification", contract)
        self.assertIn("### Unresolved Decision Protocol", contract)
        self.assertIn("a bare `TBD` does not pass validation", contract)

    def test_discovery_and_architecture_capture_selection_evidence(self) -> None:
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")

        self.assertIn("content-led, interaction-led", interview)
        self.assertIn("rendering needs", interview)
        self.assertIn(
            "For products with a browser frontend, frontend technology layers",
            architecture,
        )
        self.assertIn("official-source verification date", architecture)

    def test_platform_is_resolved_via_askuserquestion_not_defaulted(self) -> None:
        skill = self.read("SKILL.md")
        architecture = self.read("references/architecture-playbook.md")
        frontend = self.read("references/frontend-stack-selection.md")
        contract = self.read("references/output-contract.md")
        agent = self.read("agents/openai.yaml")

        self.assertNotIn("default the deployment platform to Cloudflare", skill)
        self.assertNotIn("## Default Cloudflare Release Pattern", architecture)
        self.assertNotIn("organization default", agent)
        self.assertIn("resolve the deployment platform explicitly via the interview's platform `AskUserQuestion` step", skill)
        self.assertIn("## Development-to-Production Release Pattern", architecture)
        self.assertIn("never default to one silently", architecture)
        self.assertIn("AskUserQuestion", agent)
        self.assertIn("one repository and one codebase", architecture)
        self.assertIn("separately named development and production Workers", frontend)
        self.assertIn("Current PR head after current-head CI", contract)
        self.assertIn("Exact merged base-branch SHA after development PASS", contract)
        for content in (skill, architecture, frontend, contract, agent):
            self.assertIn("development", content.lower())
            self.assertIn("production", content.lower())
            self.assertIn("cloudflare", content.lower())

    def test_interview_marks_closed_set_questions_for_askuserquestion(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")

        self.assertIn(
            "Bullets marked `(AskUserQuestion)` are a closed, enumerable set",
            interview,
        )
        for marked_bullet in (
            "or a hybrid? (AskUserQuestion)",
            "Cloudflare, Vercel, AWS, or self-hosted? (AskUserQuestion",
            "recurring usability benchmarking? (AskUserQuestion)",
            "or an existing brand reference. (AskUserQuestion",
        ):
            self.assertIn(marked_bullet, interview)
        self.assertIn("Immediately follow it with the `AskUserQuestion` batch(es)", skill)
        self.assertIn(
            "goal, users/roles, workflows, data/integrations, business rules, delivery constraints, success metrics, confirmation/recovery",
            skill,
        )

    def test_skill_routes_backend_products_to_backend_selection(self) -> None:
        skill = self.read("SKILL.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("references/backend-stack-selection.md", skill)
        self.assertIn("references/backend-stack-selection.md", architecture)
        for content in (skill, architecture, contract):
            self.assertIn("backend, persistent data, or auth requirement", content)
        self.assertIn("database category (Relational, Document, Key-value or cache only, or None)", agent)
        self.assertIn(
            "auth strategy (Build custom, Managed third-party provider, Platform-native, or No auth needed)",
            agent,
        )
        self.assertIn("via AskUserQuestion unless the user or repository already names them", agent)

    def test_backend_selection_guide_separates_layers_and_product_patterns(self) -> None:
        guide = self.read("references/backend-stack-selection.md")

        for heading in (
            "## First Separate the Layers",
            "## Collect Decision Evidence",
            "## Product-Fit Patterns",
            "## Data and Auth Decision Rules",
            "## Selection Procedure",
            "## Required Architecture Record",
            "## Official Sources to Recheck",
            "## Failure Modes",
        ):
            self.assertIn(heading, guide)
        self.assertIn("Database category", guide)
        self.assertIn("Auth strategy", guide)
        for option in ("Relational", "Document", "key-value or cache only", "Build custom", "managed third-party"):
            self.assertIn(option, guide)

    def test_isolated_development_is_seeded_with_mock_content_data(self) -> None:
        architecture = self.read("references/architecture-playbook.md")
        backend = self.read("references/backend-stack-selection.md")

        for content in (architecture, backend):
            self.assertIn("Isolation does not mean development stays empty", content)
            self.assertIn("explicitly authorizes and scopes", content)
        self.assertIn("seed the development environment with representative mock/sample data", architecture)
        self.assertIn("seed development with representative mock/sample data", backend)
        self.assertIn(
            "Do not let a development environment access production customer data, production sessions, or live payment mutations.",
            architecture,
        )
        self.assertIn(
            "Never let development access production customer data or live sessions.",
            backend,
        )

    def test_output_contract_adds_backend_and_data_technology_decision(self) -> None:
        contract = self.read("references/output-contract.md")

        self.assertIn("## Backend and Data Technology Decision", contract)
        self.assertIn("### Data Entity to Store Mapping", contract)
        self.assertIn("### Platform and Vendor Compatibility Verification", contract)
        self.assertIn(
            "database category and auth strategy trace back to the interview's `AskUserQuestion` answers",
            contract,
        )

    def test_interview_marks_backend_and_auth_questions_for_askuserquestion(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")

        self.assertIn("or no persistent database? (AskUserQuestion)", interview)
        self.assertIn("or no auth needed? (AskUserQuestion)", interview)
        self.assertIn("database category and auth strategy", skill)
        self.assertIn(
            "the resolved database category and auth strategy, and the evidence needed to recommend a backend framework, database engine, and auth provider",
            interview,
        )

    def test_skill_gates_the_backend_askuserquestion_call(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn(
            "Skip this call only when the product provably has no backend, persistent data, or auth surface",
            skill,
        )
        self.assertIn(
            "Do not silently pick a database category or auth strategy on the user's behalf.",
            skill,
        )

    def test_wireframes_keep_landing_pages_simple_and_label_media(self) -> None:
        skill = self.read("SKILL.md")
        agent = self.read("agents/openai.yaml")
        interview = self.read("references/interview-guide.md")
        guide = self.read("references/wireframe-guide.md")
        contract = self.read("references/output-contract.md")

        self.assertIn("one job per section", skill)
        self.assertIn("exact UI wording or a bounded display contract", skill)
        self.assertIn("## Content Specificity Rules", guide)
        self.assertIn("## Style And Anti-Slop Structure Rules", guide)
        self.assertIn("colored side rail or accent stripe", guide)
        self.assertIn("A box in an ASCII wireframe must mean real grouping", guide)
        self.assertIn("`Exact copy`", guide)
        self.assertIn("`Display contract`", guide)
        self.assertIn("Do not leave `Main content`", guide)
        self.assertIn("## KISS Landing Page Rules", guide)
        self.assertIn("Do not turn every PRD requirement", guide)
        self.assertIn("### Content, Style, Media & Motion Notes", guide)
        self.assertIn("Style direction", guide)
        self.assertIn("required / optional / none", guide)
        self.assertIn("### Content, Style, Media & Motion Notes", contract)
        self.assertIn("Exact wording or display contract", contract)
        self.assertNotIn("| Main content", contract)
        self.assertIn("KISS landing-page wireframes", agent)
        self.assertIn("bounded display contracts", agent)
        self.assertIn("explicit style/image/media/motion labels", agent)
        self.assertIn("restrained container use", agent)
        self.assertIn("already have approved wording", interview)
        self.assertIn("bounded display responsibilities", interview)
        self.assertIn("specific style direction or animation", interview)
        self.assertIn("Required style and motion intent", interview)

    def test_wireframes_ask_for_style_and_define_a_simple_fallback(self) -> None:
        skill = self.read("SKILL.md")
        agent = self.read("agents/openai.yaml")
        interview = self.read("references/interview-guide.md")
        guide = self.read("references/wireframe-guide.md")
        contract = self.read("references/output-contract.md")

        self.assertIn("ask what overall style the user wants", skill)
        self.assertIn("What overall visual character", interview)
        self.assertIn("If the answer is only `modern`", interview)
        self.assertIn("## Direction And Configuration", guide)
        self.assertIn("record `modern-minimal` as provisional", guide)
        self.assertIn("Do not accept `modern` as a complete layout decision", guide)
        self.assertIn("Dashboard or monitoring screen", guide)
        self.assertIn("## Wireframe Direction", contract)
        self.assertIn("Layout pattern:", contract)
        self.assertIn("modern-minimal assumption", agent)

    def test_builder_ux_direction_precedes_wireframes_without_claiming_validation(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        guide = self.read("references/wireframe-guide.md")
        contract = self.read("references/output-contract.md")
        agent = self.read("agents/openai.yaml")

        for content in (skill, interview, guide, contract, agent):
            self.assertIn("Builder UX Direction", content)
        self.assertIn("before drafting wireframes", skill)
        self.assertIn("guided or flexible", interview)
        self.assertIn("## Builder UX Direction Gate", guide)
        self.assertIn("selected / provisional / assumed", contract)
        self.assertIn("not usability proof", agent)

    def test_trace_ids_and_publish_approval_are_explicit(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        for trace_prefix in ("`PRD-*`", "`ARCH-*`", "`UI-*`", "`UX-*`", "`TEST-*`"):
            self.assertIn(trace_prefix, skill)
        self.assertIn("## Architecture Trace Index", contract)
        self.assertIn("UI ID: UI-001", contract)
        self.assertIn("| TEST ID | Test Type", contract)
        self.assertIn("Passing validation does not authorize an overwrite, move, or archive", lifecycle)
        self.assertIn("keep the staged package", lifecycle)
        self.assertIn("ask one explicit yes/no publication question", skill)
        self.assertIn("execute the approved publish and archive moves in the same run", skill)

    def test_dynamic_workflow_uses_org_roles_and_parent_owned_staging(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/dynamic-workflow.md")
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")
        contract = self.read("references/output-contract.md")

        self.assertIn("stable PRD roles as an org graph", skill)
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
        self.assertIn("## Harness Handoff Signals", contract)
        self.assertIn("not a canonical Harness PLAN or RUN graph", contract)


if __name__ == "__main__":
    unittest.main()

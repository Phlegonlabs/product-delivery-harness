import json
import shutil
import subprocess
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]


class PrdBuilderSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def run_workflow(self, workflow_args: dict) -> dict:
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required for workflow behavior tests")
        workflow_path = SKILL_ROOT / "assets/templates/CLAUDE_PRD_WORKFLOW.template.js"
        runner = r'''
const fs = require("fs");
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const source = fs.readFileSync(process.argv[1], "utf8").replace(
  "export const meta =",
  "const meta =",
);
const workflowArgs = JSON.parse(fs.readFileSync(0, "utf8"));
function phase() {}
async function parallel(tasks) {
  return Promise.all(tasks.map((task) => task()));
}
async function agent(_prompt, options) {
  const role = options.label.replace("prd:", "");
  if (role === "synthesis") {
    return {
      prd_markdown: "# PRD",
      architecture_markdown: "# Architecture",
      stack_decisions_markdown: "# Stack Decisions",
      wireframes_markdown: "# Wireframes",
      implementation_plan_markdown: null,
      trace_index: [],
      assumptions: [],
      open_questions: [],
      unresolved_conflicts: [],
    };
  }
  if (role.endsWith("verifier")) {
    return { role, decision: "pass", findings: [], evidence: [] };
  }
  return {
    role,
    status: "complete",
    sections: [],
    trace_ids: [],
    assumptions: [],
    open_questions: [],
    evidence: [],
  };
}
(async () => {
  try {
    const workflow = new AsyncFunction("args", "phase", "parallel", "agent", source);
    const result = await workflow(workflowArgs, phase, parallel, agent);
    process.stdout.write(JSON.stringify({ ok: true, status: result.status }));
  } catch (error) {
    process.stdout.write(JSON.stringify({ ok: false, error: error.message }));
  }
})();
'''
        completed = subprocess.run(
            [node, "-e", runner, str(workflow_path)],
            input=json.dumps(workflow_args),
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def release_target(
        self,
        target_id: str,
        surface: str,
        provider: str,
        stage: str,
        source_policy: str,
    ) -> dict:
        return {
            "id": target_id,
            "surface": surface,
            "provider": provider,
            "stage": stage,
            "source_policy": source_policy,
            "artifact_kind": "signed app bundle",
            "signing_requirement": "release signing",
            "channel": f"{provider}-{stage}",
            "release_path": "build, approve, release",
            "availability_signal": "intended audience installs and smoke passes",
            "rollout": "staged",
            "rollback_or_forward_fix": "halt rollout and ship signed forward-fix",
        }

    def base_workflow_args(self) -> dict:
        return {
            "run_id": "test-run",
            "product_name": "Local Notes",
            "interview_summary": "A native notes app with local persistence.",
            "product_archetypes": ["mobile app"],
            "source_paths": [],
            "browser_frontend": False,
            "ui_bearing": True,
            "has_backend": True,
            "deployable": True,
            "hosted_deployable": False,
            "deployable_surfaces": ["ios-app"],
            "release_targets": [
                self.release_target("ios-development", "ios-app", "TestFlight", "development", "pr_head"),
                self.release_target("ios-production", "ios-app", "App Store", "production", "merged_main"),
            ],
            "has_public_marketing_content": False,
            "include_implementation_plan": False,
            "tool_profile": "builder_readonly",
            "builder_ux_direction": "Guided, balanced-density native workflow.",
            "mobile_desktop_platform": "native iOS",
        }

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
            "ask whether the user wants to run the `ui-architecture-builder` skill next",
            skill,
        )
        self.assertIn("Do not invoke the design skill without an explicit yes", skill)
        self.assertIn(
            "do not offer the handoff while the PRD workflow is incomplete",
            skill,
        )
        self.assertIn(
            "approval to run `ui-architecture-builder` alone does not authorize it",
            skill,
        )

    def test_wireframes_remain_canonical_across_optional_visual_direction_pass(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/wireframe-guide.md")
        contract = self.read("references/output-contract.md")

        for content in (skill, guide, contract):
            self.assertIn("canonical", content)
            self.assertIn("non-canonical", content)
            self.assertIn("explicitly authoriz", content)
            self.assertIn("bounded wireframe revision", content)
        self.assertIn("## Optional Frontend Design Visual Direction Handoff", guide)
        self.assertIn("low-fidelity wireframes remain canonical for structure and flow", guide)
        self.assertIn("usually one to three screens", guide)
        self.assertIn("selected `UI-*` screen and region IDs", guide)
        self.assertIn("Keep it outside the staged and published PRD package", guide)
        self.assertIn(
            "No `frontend-design` prototype, render, high-fidelity HTML",
            contract,
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
        self.assertIn(
            "| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |",
            contract,
        )
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
        self.assertIn("`pr_head` after current-head CI", contract)
        self.assertIn("`merged_main` after development PASS", contract)
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
            "Skip the database-category and auth-strategy pair only when the product provably has no backend, persistent data, or auth surface",
            skill,
        )
        self.assertIn("Skip the whole call only when none of its questions apply.", skill)
        self.assertIn(
            "Do not silently pick a database category or auth strategy on the user's behalf.",
            skill,
        )

    def test_archetype_dependent_questions_come_after_the_archetype_answer(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")

        self.assertIn("Keep the deployment platform out of this call", skill)
        self.assertIn("depend on step 4's archetype answer", skill)
        self.assertIn("see Workflow step 6, after the archetype is known", skill)
        self.assertIn("The closed-set questions fit three `AskUserQuestion` calls", interview)
        self.assertIn("Never ask a call-3 question in call 1", interview)
        for slotted_bullet in (
            "React Native (cross-platform), or undecided and need a recommendation? (AskUserQuestion, in call 3",
            "cross-platform (e.g. Electron or Tauri), or undecided and need a recommendation? (AskUserQuestion, in call 3",
            "Cloudflare, Vercel, AWS, or self-hosted? (AskUserQuestion, in call 3",
        ):
            self.assertIn(slotted_bullet, interview)
        self.assertIn("first to drop when the closed-set budget is full", interview)
        self.assertIn("Deployment platform, database category, and auth strategy never drop", interview)

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

    def test_prd_contract_requires_measurable_nfrs_and_test_obligations(self) -> None:
        contract = self.read("references/output-contract.md")
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        agent = self.read("agents/openai.yaml")

        self.assertLess(
            contract.index("## Functional Requirements"),
            contract.index("## Non-Functional Requirements"),
        )
        self.assertLess(
            contract.index("## Non-Functional Requirements"),
            contract.index("## UX Requirements"),
        )
        self.assertLess(
            contract.index("## Open Questions"),
            contract.index("## Test Obligations"),
        )
        self.assertLess(
            contract.index("## Test Obligations"),
            contract.index("## Builder UX Direction Decision"),
        )
        self.assertIn(
            "| ID | Quality attribute | Scope / requirement | Measure | Target / threshold | TEST IDs |",
            contract,
        )
        self.assertIn(
            "| TEST ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |",
            contract,
        )
        self.assertIn("units, tested population or traffic shape, measurement window, and percentile", contract)
        self.assertIn("non-applicable categories are explicitly `N/A` with a reason", contract)
        self.assertIn("Every `Must` functional requirement and every applicable non-functional requirement", contract)
        self.assertIn("at least one `TEST-*` row marked `Required: Yes`", contract)
        self.assertIn("Keep `## Non-Functional Requirements` in every `PRD.md`", skill)
        self.assertIn("Keep `## Test Obligations` in every `PRD.md`", skill)
        self.assertIn("The PRD assigns stable `TEST-*` IDs during synthesis", interview)
        self.assertIn("always-present measurable Non-Functional Requirements", agent)

    def test_test_ids_are_reused_and_preserved_in_enhancements(self) -> None:
        contract = self.read("references/output-contract.md")
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")

        self.assertIn("Reuse the canonical `TEST-*` IDs from `PRD.md`", contract)
        self.assertIn("must not create anonymous replacements or duplicate TEST identities", skill)
        self.assertIn("Preserve existing `TEST-*` IDs for unchanged obligations", interview)
        self.assertIn("mint new TEST IDs only for newly uncovered obligations", skill)
        self.assertIn("new TEST IDs cover only obligations that were previously uncovered", contract)
        self.assertIn("reuse those TEST IDs rather than creating anonymous replacements", workflow)
        self.assertIn("every Must functional requirement and every applicable NFR", workflow)

    def test_stack_rows_record_per_layer_status_and_cited_authority(self) -> None:
        contract = self.read("references/output-contract.md")
        frontend = self.read("references/frontend-stack-selection.md")
        backend = self.read("references/backend-stack-selection.md")
        mobile = self.read("references/mobile-stack-selection.md")

        header = "| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |"
        self.assertEqual(3, contract.count(header))
        for status_rule in (
            "`Required` means a user, organization, or hard external constraint",
            "`Selected` means the current product or repository already adopted it",
            "`Recommended` is evidence-backed advice not yet accepted",
            "`Provisional` is a leading choice pending named evidence",
        ):
            self.assertIn(status_rule, contract)
        self.assertIn("A section may mix statuses", contract)
        self.assertIn("Authority is not another status label", contract)
        for guide in (frontend, backend, mobile):
            self.assertIn("Assign status per layer; one section may mix statuses", guide)
            self.assertIn("Authority is the cited source, not a status label", guide)
            self.assertIn("Selection, status, cited authority/evidence", guide)

    def test_service_topology_is_the_first_backend_layer_everywhere(self) -> None:
        contract = self.read("references/output-contract.md")
        backend = self.read("references/backend-stack-selection.md")
        architecture = self.read("references/architecture-playbook.md")
        skill = self.read("SKILL.md")
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")
        agent = self.read("agents/openai.yaml")

        backend_section = contract[contract.index("## Backend and Data Technology Decision") :]
        self.assertLess(
            backend_section.index("| Service topology |"),
            backend_section.index("| Backend runtime / framework |"),
        )
        layers = backend[backend.index("## First Separate the Layers") : backend.index("## Service Topology Decision")]
        self.assertLess(layers.index("| Service topology |"), layers.index("| Backend runtime / framework |"))
        self.assertIn("backend technology layers in this order: service topology", architecture)
        self.assertIn("Record service topology first", skill)
        self.assertIn("Decide service topology first", workflow)
        self.assertIn("record service topology first", agent)
        for content in (contract, backend, architecture, skill, workflow, agent):
            self.assertIn("monolith", content.lower())
            self.assertIn("monorepo", content.lower())
            self.assertIn("polyrepo", content.lower())

    def test_release_discovery_is_provider_neutral_and_complete(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")
        agent = self.read("agents/openai.yaml")

        self.assertIn("## Provider-Neutral Release Target Pattern", architecture)
        self.assertIn("## Release Targets", contract)
        for field in (
            "stable target ID",
            "development",
            "production",
            "Source policy",
            "Artifact kind",
            "Signing requirement",
            "Exact channel / track",
            "Submission / promotion / review / manual approval path",
            "Availability signal",
            "Rollout",
            "Rollback / forward-fix",
        ):
            self.assertIn(field, contract)
        self.assertIn("complete inventory of expected deployable web, API, mobile, or desktop surfaces", interview)
        self.assertIn("For every deployable web, API, mobile, or desktop surface", skill)
        self.assertIn("For every deployable web, API, mobile, or desktop surface", agent)
        self.assertIn("at least one `development` target and one `production` target", contract)
        self.assertIn("Expected deployable surfaces:", contract)
        self.assertIn("- Surface: [Stable expected surface ID]", contract)
        self.assertIn("- Provider: [Stage-specific hosting, store, or distribution provider]", contract)
        self.assertIn("Different providers by stage are valid for the same surface", contract)
        self.assertIn("Preserve stable release target IDs for unchanged targets", interview)
        self.assertIn("stable release target IDs from the prior package", contract)

    def test_release_availability_and_native_recovery_are_explicit(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")
        agent = self.read("agents/openai.yaml")

        for content in (skill, interview, architecture, contract, workflow, agent):
            self.assertIn("not availability", content.lower())
            self.assertIn("forward-fix", content.lower())
        self.assertIn("Do not use this two-row hosted-environment table for native", contract)
        self.assertIn("Do not force TestFlight, Play tracks", architecture)
        self.assertIn("never force native targets into the hosted two-row environment table", workflow)
        self.assertIn("actually installable or downloadable", contract)
        self.assertIn("halting a phased or staged rollout", contract)

    def test_workflow_requires_stable_release_targets_for_each_stage(self) -> None:
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")

        self.assertIn('throw new Error("prd-builder-graph requires boolean args.deployable");', workflow)
        self.assertIn('throw new Error("prd-builder-graph requires args.release_targets as an array");', workflow)
        for field in (
            '"id"',
            '"surface"',
            '"provider"',
            '"stage"',
            '"source_policy"',
            '"artifact_kind"',
            '"signing_requirement"',
            '"channel"',
            '"release_path"',
            '"availability_signal"',
            '"rollout"',
            '"rollback_or_forward_fix"',
        ):
            self.assertIn(field, workflow)
        self.assertIn("requires unique release target ID", workflow)
        self.assertIn("requires unique deployable surface", workflow)
        self.assertIn("requires development and production release targets for expected surface", workflow)
        self.assertIn("uses unexpected surface", workflow)
        self.assertIn("deployable_surfaces: workflowArgs.deployable_surfaces,", workflow)
        self.assertIn("release_targets: workflowArgs.release_targets,", workflow)
        self.assertIn("preserve the supplied stable release target IDs", workflow)
        self.assertIn("Upload or submission is not availability", workflow)

    def test_release_sources_match_plan_v5_vocabulary(self) -> None:
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")
        frontend = self.read("references/frontend-stack-selection.md")
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")

        for content in (interview, architecture, contract, frontend, workflow):
            for source in ("pr_head", "integration_head", "merged_main"):
                self.assertIn(source, content)
        for content in (interview, architecture, contract):
            self.assertIn("unresolved", content.lower())
            self.assertIn("signed tag", content.lower())
        self.assertIn('!["pr_head", "integration_head", "merged_main"].includes(target.source_policy)', workflow)
        self.assertIn('target.source_policy !== "merged_main"', workflow)

    def test_migration_order_maps_to_plan_v5_fields(self) -> None:
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")

        for content in (architecture, contract):
            self.assertIn("`migration_classification`", content)
            self.assertIn("`commands.migrate`", content)
            self.assertIn("`prerequisites`", content)
            self.assertNotIn("`migration_command`", content)

    def test_workflow_accepts_native_local_data_without_hosting_platform(self) -> None:
        workflow_args = self.base_workflow_args()

        self.assertNotIn("deployment_platform", workflow_args)
        result = self.run_workflow(workflow_args)

        self.assertEqual({"ok": True, "status": "candidate_ready"}, result)

    def test_workflow_rejects_hybrid_missing_expected_surface(self) -> None:
        workflow_args = self.base_workflow_args()
        workflow_args.update(
            {
                "product_archetypes": ["hybrid"],
                "browser_frontend": True,
                "hosted_deployable": True,
                "deployment_platform": "Cloudflare",
                "deployable_surfaces": ["web-app", "ios-app"],
            }
        )

        result = self.run_workflow(workflow_args)

        self.assertFalse(result["ok"])
        self.assertIn(
            "requires development and production release targets for expected surface web-app",
            result["error"],
        )

    def test_workflow_accepts_different_stage_providers_for_same_surface(self) -> None:
        workflow_args = self.base_workflow_args()
        workflow_args.update(
            {
                "product_name": "Hosted Dashboard",
                "product_archetypes": ["web app"],
                "browser_frontend": True,
                "hosted_deployable": True,
                "deployment_platform": "development=Cloudflare; production=AWS",
                "deployable_surfaces": ["web-app"],
                "release_targets": [
                    self.release_target("web-development", "web-app", "Cloudflare", "development", "pr_head"),
                    self.release_target("web-production", "web-app", "AWS", "production", "merged_main"),
                ],
            }
        )

        result = self.run_workflow(workflow_args)

        self.assertEqual({"ok": True, "status": "candidate_ready"}, result)

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

    def test_workflow_lanes_receive_resolved_platform_and_ux_direction(self) -> None:
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")

        self.assertIn(
            'throw new Error("prd-builder-graph requires boolean args.ui_bearing");',
            workflow,
        )
        self.assertIn(
            "requires non-empty args.builder_ux_direction for a ui_bearing product",
            workflow,
        )
        self.assertIn(
            'throw new Error("prd-builder-graph requires boolean args.hosted_deployable");',
            workflow,
        )
        self.assertIn(
            "requires non-empty args.deployment_platform for a hosted deployable web, API, or backend surface",
            workflow,
        )
        self.assertNotIn("workflowArgs.browser_frontend || workflowArgs.has_backend", workflow)
        self.assertIn("deployment_platform: workflowArgs.deployment_platform || null,", workflow)
        self.assertIn("hosted_deployable: workflowArgs.hosted_deployable,", workflow)
        self.assertIn("ui_bearing: workflowArgs.ui_bearing,", workflow)
        self.assertIn("never substitute or invent a platform or provider", workflow)

    def test_lifecycle_keeps_the_package_in_docs_product_not_flat_docs(self) -> None:
        lifecycle = self.read("references/artifact-lifecycle.md")

        self.assertIn(
            "Never publish PRD artifacts at the repository root or flat in `docs/` by default.",
            lifecycle,
        )
        self.assertIn("They belong in `docs/product/`.", lifecycle)
        self.assertIn(
            "in `docs/product/`, the repository root, or a legacy flat `docs/` directory",
            lifecycle,
        )
        self.assertNotIn("or under `docs/product/` by default", lifecycle)
        self.assertNotIn("or a legacy `docs/product/` directory", lifecycle)


if __name__ == "__main__":
    unittest.main()

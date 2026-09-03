import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]


class PrdBuilderSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def read_agent_prompt(self) -> str:
        return " ".join(self.read("agents/openai.yaml").split())

    def run_workflow(self, workflow_args: dict) -> dict:
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required for workflow behavior tests")
        workflow_path = SKILL_ROOT / "assets/templates/CLAUDE_PRD_WORKFLOW.template.js"
        runner = r"""
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
      wireframes_html_data_json: '{"screens":[]}',
      architecture_markdown: "# Architecture",
      stack_decisions_markdown: "# Stack Decisions",
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
  if (role === "market-research") {
    return {
      role,
      status: "complete",
      market_research_markdown: "# Market Research",
      mr_ids: ["MR-001"],
      findings: [],
      sources: [],
      unresolved: [],
      evidence: [],
    };
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
    process.stdout.write(JSON.stringify({ ok: true, status: result.status, research: result.research }));
  } catch (error) {
    process.stdout.write(JSON.stringify({ ok: false, error: error.message }));
  }
})();
"""
        completed = subprocess.run(
            [node, "-e", " ".join(runner.splitlines()), str(workflow_path)],
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
                self.release_target(
                    "ios-development",
                    "ios-app",
                    "TestFlight",
                    "development",
                    "integration branch head",
                ),
                self.release_target(
                    "ios-production",
                    "ios-app",
                    "App Store",
                    "production",
                    "default branch head",
                ),
            ],
            "has_public_marketing_content": False,
            "include_implementation_plan": False,
            "market_research": True,
            "tool_profile": "builder_readonly",
            "multi_agent_authorized": True,
            "builder_ux_direction": "Guided, balanced-density native workflow.",
            "mobile_desktop_platform": "native iOS",
        }

    def test_skill_routes_browser_products_to_frontend_selection(self) -> None:
        skill = self.read("SKILL.md")
        agent = self.read_agent_prompt()

        self.assertIn("references/frontend-stack-selection.md", skill)
        self.assertIn("recommend one explicit stack", skill)
        self.assertIn(
            "recommendation is not misrepresented as a fixed requirement", skill
        )
        self.assertIn("Cloudflare is a deployment/runtime platform", skill)
        self.assertIn("when the product has a browser surface", agent)

    def test_completed_wireframe_stage_stops_before_harness(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn("An approved `wireframes.html` completes the wireframe stage", skill)
        self.assertIn("do not invoke or automatically offer either", skill)
        self.assertIn("If the owner later requests Harness work", skill)

    def test_publish_uses_distinct_repository_context_templates(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn(
            "<full-harness-skill-root>/scripts/"
            "configure_project_context.py --root <target-root> --check",
            skill,
        )
        self.assertIn("PROJECT_AGENTS.template.md` for `AGENTS.md`", skill)
        self.assertIn("PROJECT_CLAUDE.template.md` for `CLAUDE.md`", skill)
        self.assertIn("Never copy one template to both files", skill)
        self.assertNotIn(
            "both files exist before any implementation run starts", skill
        )

    def test_ui_design_pass_is_explicit_and_pair_compilation_is_conditional(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        agent = self.read_agent_prompt()

        for content in (skill, contract, agent):
            self.assertIn("product-design-builder", content)
            self.assertIn("frontend-design", content)
            self.assertIn("design-taste-frontend", content)
        self.assertIn(
            "Only when the result is `required`, load `product-design-builder`",
            skill,
        )
        self.assertIn("define routes, screen structure, flows", skill)
        self.assertIn("Only when the owner explicitly continues into visual design", agent)
        self.assertIn("later optional visual-design phase", contract)
        self.assertIn("## UI Surface Contract", contract)
        self.assertNotIn("wireframes.md", contract)
        self.assertIn("Wireframe Approval Gate", skill)
        self.assertIn("Design System Need Gate", contract)

    def test_prd_builder_owns_approved_low_fidelity_wireframes(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")
        guide = self.read("references/wireframe-guide.md")
        html_template = self.read("assets/templates/WIREFRAMES.template.html")
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")

        for content in (skill, contract, lifecycle):
            self.assertIn("wireframes.html", content)
            self.assertNotIn("wireframes.md", content)
        self.assertFalse((SKILL_ROOT / "assets/templates/WIREFRAMES.template.md").exists())
        self.assertIn("`prd-builder` owns one low-fidelity deliverable", guide)
        self.assertIn("Create one screen for every `UI-*` entry", guide)
        self.assertIn("## HTML Requirements", guide)
        self.assertIn("Generate one self-contained file", guide)
        self.assertIn("an all-pages overview plus a page switcher", guide)
        self.assertIn("## Wireframe Approval Gate", guide)
        self.assertIn("PRD.md` wins", contract)
        self.assertIn("Visual design phase: not requested", contract)

        payload = html_template.split(
            '<script id="wireframe-data" type="application/json">', 1
        )[1].split("</script>", 1)[0]
        data = json.loads(payload)
        self.assertEqual([screen["id"] for screen in data["screens"]], ["UI-001", "UI-002"])
        self.assertIn('data-viewport="expanded"', html_template)
        self.assertIn('id="state-controls"', html_template)
        self.assertIn('id="page-list"', html_template)
        self.assertIn("All pages", html_template)
        self.assertIn("Hero Section", html_template)
        self.assertIn("textContent", html_template)
        self.assertNotIn("https://", html_template)
        self.assertIn("wireframes_html_data_json", workflow)

        checker = SKILL_ROOT / "scripts/check_wireframe_html.py"
        result = subprocess.run(
            [sys.executable, str(checker), "--html", str(SKILL_ROOT / "assets/templates/WIREFRAMES.template.html")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            external = Path(tmp) / "wireframes.html"
            external.write_text(
                html_template.replace(
                    "<title>",
                    '<script src="https://example.com/reviewer.js"></script><title>',
                    1,
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(checker), "--html", str(external)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must not load external resources", result.stderr)

    def run_checker_with_data(
        self, data: dict, extra_args: list[str] | None = None
    ) -> subprocess.CompletedProcess:
        html_template = self.read("assets/templates/WIREFRAMES.template.html")
        marker = '<script id="wireframe-data" type="application/json">'
        original_payload = html_template.split(marker, 1)[1].split("</script>", 1)[0]
        modified = html_template.replace(
            original_payload, "\n" + json.dumps(data) + "\n", 1
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wireframes.html"
            path.write_text(modified, encoding="utf-8")
            return subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts/check_wireframe_html.py"),
                    "--html",
                    str(path),
                    *(extra_args or []),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

    def minimal_wireframe_data(self) -> dict:
        return {
            "product": "P",
            "approvalStatus": "draft",
            "source": "PRD.md#UI-Surface-Contract",
            "screens": [
                {
                    "id": "UI-001",
                    "name": "N",
                    "route": "/",
                    "goal": "G",
                    "traces": ["UX-001"],
                    "regions": [
                        {
                            "id": "r1",
                            "section": "S",
                            "purpose": "P",
                            "priority": "primary",
                            "span": 12,
                            "elements": [
                                "Exact copy",
                                {"label": "L", "contract": {"source": "S"}},
                            ],
                            "actions": [],
                            "traces": ["UX-001"],
                        }
                    ],
                    "compactOrder": ["r1"],
                    "states": [{"id": "ready", "label": "Ready", "treatments": {}}],
                }
            ],
            "flows": [{"from": "UI-001", "trigger": "T", "to": "UI-001"}],
        }

    def test_wireframe_template_projects_flows_traces_and_display_contracts(
        self,
    ) -> None:
        guide = self.read("references/wireframe-guide.md")
        html_template = self.read("assets/templates/WIREFRAMES.template.html")
        payload = html_template.split(
            '<script id="wireframe-data" type="application/json">', 1
        )[1].split("</script>", 1)[0]
        data = json.loads(payload)

        self.assertIn("`flows` lists each flow", guide)
        self.assertIsInstance(data["flows"], list)
        self.assertTrue(data["flows"])
        screen_ids = {screen["id"] for screen in data["screens"]}
        for flow in data["flows"]:
            for key in ("from", "trigger", "to"):
                self.assertIsInstance(flow[key], str)
                self.assertTrue(flow[key].strip())
            self.assertIn(flow["from"], screen_ids)
        self.assertTrue(any(screen.get("traces") for screen in data["screens"]))
        self.assertTrue(
            any(
                region.get("traces")
                for screen in data["screens"]
                for region in screen["regions"]
            )
        )
        elements = [
            item
            for screen in data["screens"]
            for region in screen["regions"]
            for item in region["elements"]
        ]
        self.assertTrue(any(isinstance(item, dict) for item in elements))
        for marker in ("flow-panel", "display-contract", "flowTarget", "Traces"):
            self.assertIn(marker, html_template)

        self.assertEqual(self.run_checker_with_data(self.minimal_wireframe_data()).returncode, 0)

        missing_label = self.minimal_wireframe_data()
        missing_label["screens"][0]["regions"][0]["elements"] = [
            {"contract": {"source": "S"}}
        ]
        result = self.run_checker_with_data(missing_label)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("elements", result.stderr)

        unknown_flow = self.minimal_wireframe_data()
        unknown_flow["flows"][0]["from"] = "UI-999"
        result = self.run_checker_with_data(unknown_flow)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("references unknown screen ID", result.stderr)

        bad_traces = self.minimal_wireframe_data()
        bad_traces["screens"][0]["traces"] = "UX-001"
        result = self.run_checker_with_data(bad_traces)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("traces", result.stderr)

    def test_require_filled_rejects_unfilled_placeholders(self) -> None:
        unfilled = self.minimal_wireframe_data()
        unfilled["screens"][0]["regions"][0]["elements"].append("<feature name>")
        result = self.run_checker_with_data(unfilled, extra_args=["--require-filled"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contains an unfilled <placeholder>", result.stderr)

        clean = self.run_checker_with_data(
            self.minimal_wireframe_data(), extra_args=["--require-filled"]
        )
        self.assertEqual(clean.returncode, 0, clean.stderr)

    def test_require_approved_blocks_unapproved_wireframes(self) -> None:
        result = self.run_checker_with_data(
            self.minimal_wireframe_data(), extra_args=["--require-approved"]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be 'approved'", result.stderr)

        approved = self.minimal_wireframe_data()
        approved["approvalStatus"] = "approved"
        result = self.run_checker_with_data(
            approved, extra_args=["--require-approved"]
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_approval_status_uses_the_gate_decision_vocabulary(self) -> None:
        for retired in ("provisional", "revise"):
            data = self.minimal_wireframe_data()
            data["approvalStatus"] = retired
            result = self.run_checker_with_data(data)
            self.assertNotEqual(result.returncode, 0, retired)

        for decision in ("revision_requested", "blocked"):
            data = self.minimal_wireframe_data()
            data["approvalStatus"] = decision
            result = self.run_checker_with_data(data)
            self.assertEqual(result.returncode, 0, f"{decision}: {result.stderr}")

    def test_ui_design_handoff_has_taste_and_provider_neutral_preview_gates(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        guide = self.read("references/ui-design-pass.md")

        for content in (skill, contract, guide):
            self.assertIn("design-taste-frontend", content)
            self.assertIn("UI Preview Gate", content)
        self.assertIn("record `applicable`, `partially_applicable`, or `n/a: <reason>`", skill)
        self.assertIn("Skill Bindings table in its `AGENTS.md`", skill)
        self.assertIn(
            "list the locally installed skills visible to this session", skill
        )
        self.assertIn(
            "confirm the bindings with the owner in one `AskUserQuestion`", skill
        )
        self.assertIn("stay at the bundled default", skill)
        self.assertIn("never reopened for this", skill)
        self.assertIn("imagegen-frontend-web", guide)
        self.assertIn("imagegen-frontend-mobile", guide)
        self.assertIn("provider/model", guide)
        self.assertIn("Optional `brandkit` exploration", guide)
        self.assertIn("An approved preview becomes an implementation target", guide)
        self.assertIn("## Design System Need Gate", guide)

    def test_ui_design_pass_records_provenance_and_retention_consequences(self) -> None:
        guide = self.read("references/ui-design-pass.md")
        contract = self.read("references/output-contract.md")
        references = self.read(
            "../product-design-builder/references/design-reference-guide.md"
        )

        self.assertIn("design-reference-guide.md", guide)
        self.assertIn("`VD-*` ID", guide)
        self.assertIn("`REF-*` record", guide)
        self.assertIn("`RP-*` record", guide)
        self.assertIn(
            "visual authority then reverts to `PRD.md` plus approved `wireframes.html`",
            guide,
        )
        self.assertIn("A durable target binding requires retention", guide)
        self.assertIn(
            "Selected direction: [VD-* ID and one-line visual intent, "
            "with confirmed REF-* / RP-* IDs or none]",
            contract,
        )
        self.assertIn(
            "optional `flows`, `UX-*` traces, and element display contracts", contract
        )
        self.assertIn(
            "record protocol also governs the `prd-builder` UI Design Pass", references
        )

    def test_market_research_precedes_style_aware_design_handoff(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")

        research = skill.index("13. Run the market-research gap pass")
        design = skill.index("14. Only when the owner explicitly requests visual design")
        self.assertLess(research, design)
        self.assertIn("valid `MR-*` evidence", skill)
        self.assertIn("Ask the human owner once for style preferences and visual references", skill)
        self.assertIn("produce one recommended product-specific direction by default", skill)
        self.assertIn("Produce three comparable directions only when", skill)
        self.assertIn(
            "A direction may call itself market-supported only when valid `MR-*` evidence applies",
            skill,
        )
        self.assertIn("a market-research URL is not visual evidence", skill)
        self.assertIn("`design inspiration` or `page-faithful target`", contract)
        self.assertIn("do not infer faithful-copy intent", contract)
        self.assertIn("Stop after the human owner approves `wireframes.html`", contract)
        interview = self.read("references/interview-guide.md")
        self.assertIn("produces one recommended product-specific direction by default", interview)
        self.assertIn("three comparable directions only when the owner asks", interview)

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
        agent = self.read_agent_prompt()

        self.assertNotIn("default the deployment platform to Cloudflare", skill)
        self.assertNotIn("## Default Cloudflare Release Pattern", architecture)
        self.assertNotIn("organization default", agent)
        self.assertIn(
            "resolve the deployment platform explicitly via the interview's platform `AskUserQuestion` step",
            skill,
        )
        self.assertIn("## Development-to-Production Release Pattern", architecture)
        self.assertIn("never default to one silently", architecture)
        self.assertIn("AskUserQuestion", agent)
        self.assertIn("one repository and one codebase", architecture)
        self.assertIn("separately named development and production Workers", frontend)
        self.assertIn(
            "The pushed integration-branch head after current-head CI", contract
        )
        self.assertIn("The default-branch head after development PASS", contract)
        for content in (skill, architecture, frontend, contract, agent):
            self.assertIn("development", content.lower())
            self.assertIn("production", content.lower())
            self.assertIn("cloudflare", content.lower())

    def test_interview_marks_closed_set_questions_for_askuserquestion(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")

        self.assertIn(
            "Bullets marked `(AskUserQuestion)` are a closed, enumerable set", interview
        )
        for marked_bullet in (
            "or a hybrid? (AskUserQuestion)",
            "Cloudflare, Vercel, AWS, or self-hosted? (AskUserQuestion",
            "recurring usability benchmarking? (AskUserQuestion)",
        ):
            self.assertIn(marked_bullet, interview)
        self.assertNotIn("existing brand reference. (AskUserQuestion", interview)
        self.assertIn(
            "Do not call `AskUserQuestion` during any free-text segment",
            skill,
        )
        self.assertIn(
            "start the closed questions only after every applicable segment has a reply",
            interview,
        )
        self.assertNotIn(
            "Immediately follow it with the `AskUserQuestion` batch(es)", skill
        )
        self.assertNotIn("immediately after the free-text interview message", interview)

    def test_open_ended_interview_has_three_adaptive_segments(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        agent = self.read_agent_prompt()
        headings = (
            "### Segment 1 — Product and users",
            "### Segment 2 — Workflows, data, and rules",
            "### Segment 3 — Delivery, success, and risk",
        )

        self.assertIn("three bounded free-text turns", skill)
        self.assertIn("exactly three planned free-text turns", interview)
        self.assertIn("three bounded free-text turns", agent)
        self.assertEqual(3, sum(interview.count(heading) for heading in headings))
        self.assertLess(interview.index(headings[0]), interview.index(headings[1]))
        self.assertLess(interview.index(headings[1]), interview.index(headings[2]))
        user_facing = interview.split("## Segmented Free-Text Sequence", 1)[1].split(
            "## Question Routing Reference", 1
        )[0]
        self.assertNotIn("(AskUserQuestion)", user_facing)
        segments = user_facing.split("### Segment ")[1:]
        self.assertEqual(3, len(segments))
        for segment in segments:
            prompts = [
                line
                for line in segment.split("Capture internally:", 1)[0].splitlines()
                if line.startswith("- ")
            ]
            self.assertGreaterEqual(len(prompts), 2)
            self.assertLessEqual(len(prompts), 4)
            for prompt in prompts:
                self.assertLessEqual(len(prompt), 160)
        self.assertIn("Ask only one segment per turn", interview)
        self.assertIn("remove prompts", interview)
        self.assertIn("run only the segments touched or reopened", interview)
        self.assertIn("one compact targeted free-text follow-up", interview)
        self.assertIn("Begin the closed `AskUserQuestion` phase only after", interview)
        self.assertNotIn("ask one organized free-text interview message", skill.lower())

    def test_skill_routes_backend_products_to_backend_selection(self) -> None:
        skill = self.read("SKILL.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")
        agent = self.read_agent_prompt()

        self.assertIn("references/backend-stack-selection.md", skill)
        self.assertIn("references/backend-stack-selection.md", architecture)
        for content in (skill, architecture, contract):
            self.assertIn("backend, persistent data, or auth requirement", content)
        self.assertIn(
            "database category (Relational, Document, Key-value or cache only, or None)",
            agent,
        )
        self.assertIn(
            "auth strategy (Build custom, Managed third-party provider, Platform-native, or No auth needed)",
            agent,
        )
        self.assertIn(
            "via AskUserQuestion unless the user or repository already names them",
            agent,
        )

    def test_backend_selection_guide_separates_layers_and_product_patterns(
        self,
    ) -> None:
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
        for option in (
            "Relational",
            "Document",
            "key-value or cache only",
            "Build custom",
            "managed third-party",
        ):
            self.assertIn(option, guide)

    def test_isolated_development_is_seeded_with_mock_content_data(self) -> None:
        architecture = self.read("references/architecture-playbook.md")
        backend = self.read("references/backend-stack-selection.md")

        for content in (architecture, backend):
            self.assertIn("Isolation does not mean development stays empty", content)
            self.assertIn("explicitly authorizes and scopes", content)
        self.assertIn(
            "seed the development environment with representative mock/sample data",
            architecture,
        )
        self.assertIn("seed development with representative mock/sample data", backend)
        self.assertIn(
            "Do not let a development environment access production customer data",
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
            "database category and auth strategy trace back to the interview's",
            contract,
        )

    def test_interview_marks_backend_and_auth_questions_for_askuserquestion(
        self,
    ) -> None:
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
            "auth-strategy pair only when the product provably has no backend", skill
        )
        self.assertIn(
            "Skip the whole call only when none of its questions apply.", skill
        )
        self.assertIn(
            "Do not silently pick a database category or auth strategy on the user's behalf.",
            skill,
        )

    def test_archetype_dependent_questions_come_after_the_archetype_answer(
        self,
    ) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")

        self.assertIn("Keep the deployment platform out of this call", skill)
        self.assertIn("depend on step 4's archetype answer", skill)
        self.assertIn("see Workflow step 6, after the archetype is known", skill)
        self.assertIn(
            "The closed-set questions fit three `AskUserQuestion` calls", interview
        )
        self.assertIn("Never ask a call-3 question in call 1", interview)
        for slotted_bullet in (
            "React Native (cross-platform), or undecided and need a recommendation? (AskUserQuestion, in call 3",
            "cross-platform (e.g. Electron or Tauri), or undecided and need a recommendation? (AskUserQuestion, in call 3",
            "Cloudflare, Vercel, AWS, or self-hosted? (AskUserQuestion, in call 3",
        ):
            self.assertIn(slotted_bullet, interview)
        self.assertIn("first to drop when the closed-set budget is full", interview)
        self.assertIn(
            "Deployment platform, database category, and auth strategy never drop",
            interview,
        )

    def test_trace_ids_and_publish_approval_are_explicit(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        for trace_prefix in ("`PRD-*`", "`ARCH-*`", "`UX-*`", "`TEST-*`"):
            self.assertIn(trace_prefix, skill)
        self.assertIn("## Architecture Trace Index", contract)
        self.assertIn("`product-design-builder`", contract)
        self.assertIn("`UI-*`", contract)
        self.assertIn("| TEST ID | Test Type", contract)
        self.assertIn(
            "Passing validation does not authorize an overwrite, move, or archive",
            lifecycle,
        )
        self.assertIn("keep the staged package", lifecycle)
        self.assertIn("ask one explicit yes/no publication question", skill)
        self.assertIn(
            "execute the approved publish and archive moves in the same run", skill
        )

    def test_prd_contract_requires_measurable_nfrs_and_test_obligations(self) -> None:
        contract = self.read("references/output-contract.md")
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        agent = self.read_agent_prompt()

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
        self.assertIn(
            "units, tested population or traffic shape, measurement window, and percentile",
            contract,
        )
        self.assertIn(
            "non-applicable categories are explicitly `N/A` with a reason", contract
        )
        self.assertIn(
            "Every `Must` functional requirement and every applicable non-functional requirement",
            contract,
        )
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
        self.assertIn(
            "must not create anonymous replacements or duplicate TEST identities", skill
        )
        self.assertIn(
            "Preserve existing `TEST-*` IDs for unchanged obligations", interview
        )
        self.assertIn("mint new TEST IDs only for newly uncovered obligations", skill)
        self.assertIn(
            "new TEST IDs cover only obligations that were previously uncovered",
            contract,
        )
        self.assertIn(
            "reuse those TEST IDs rather than creating anonymous replacements", workflow
        )
        self.assertIn(
            "every Must functional requirement and every applicable NFR", workflow
        )

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
            self.assertIn(
                "Assign status per layer; one section may mix statuses", guide
            )
            self.assertIn("Authority is the cited source, not a status label", guide)
            self.assertIn("Selection, status, cited authority/evidence", guide)

    def test_service_topology_is_the_first_backend_layer_everywhere(self) -> None:
        contract = self.read("references/output-contract.md")
        backend = self.read("references/backend-stack-selection.md")
        architecture = self.read("references/architecture-playbook.md")
        skill = self.read("SKILL.md")
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")
        agent = self.read_agent_prompt()

        backend_section = contract[
            contract.index("## Backend and Data Technology Decision") :
        ]
        self.assertLess(
            backend_section.index("| Service topology |"),
            backend_section.index("| Backend runtime / framework |"),
        )
        layers = backend[
            backend.index("## First Separate the Layers") : backend.index(
                "## Service Topology Decision"
            )
        ]
        self.assertLess(
            layers.index("| Service topology |"),
            layers.index("| Backend runtime / framework |"),
        )
        self.assertIn(
            "backend technology layers in this order: service topology", architecture
        )
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
        agent = self.read_agent_prompt()

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
        self.assertIn(
            "complete inventory of expected deployable web, API, mobile, or desktop surfaces",
            interview,
        )
        self.assertIn(
            "For every deployable web, API, mobile, or desktop surface", skill
        )
        self.assertIn(
            "For every deployable web, API, mobile, or desktop surface", agent
        )
        self.assertIn(
            "at least one `development` target and one `production` target", contract
        )
        self.assertIn("Expected deployable surfaces:", contract)
        self.assertIn("- Surface: [Stable expected surface ID]", contract)
        self.assertIn(
            "- Provider: [Stage-specific hosting, store, or distribution provider]",
            contract,
        )
        self.assertIn(
            "Different providers by stage are valid for the same surface", contract
        )
        self.assertIn(
            "Preserve stable release target IDs for unchanged targets", interview
        )
        self.assertIn("stable release target IDs from the prior package", contract)

    def test_release_availability_and_native_recovery_are_explicit(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")
        agent = self.read_agent_prompt()

        for content in (skill, interview, architecture, contract, workflow, agent):
            self.assertIn("not availability", content.lower())
            self.assertIn("forward-fix", content.lower())
        self.assertIn(
            "Do not use this two-row hosted-environment table for native", contract
        )
        self.assertIn("Do not force TestFlight, Play tracks", architecture)
        self.assertIn(
            "never force native targets into the hosted two-row environment table",
            workflow,
        )
        self.assertIn("actually installable or downloadable", contract)
        self.assertIn("halting a phased or staged rollout", contract)

    def test_workflow_requires_stable_release_targets_for_each_stage(self) -> None:
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")

        self.assertIn(
            'throw new Error("prd-builder-graph requires boolean args.deployable");',
            workflow,
        )
        self.assertIn(
            'throw new Error("prd-builder-graph requires args.release_targets as an array");',
            workflow,
        )
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
        self.assertIn(
            "requires development and production release targets for expected surface",
            workflow,
        )
        self.assertIn("uses unexpected surface", workflow)
        self.assertIn(
            "deployable_surfaces: workflowArgs.deployable_surfaces,", workflow
        )
        self.assertIn("release_targets: workflowArgs.release_targets,", workflow)
        self.assertIn("preserve the supplied stable release target IDs", workflow)
        self.assertIn("Upload or submission is not availability", workflow)

    def test_release_sources_name_exact_branch_or_ref(self) -> None:
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")
        frontend = self.read("references/frontend-stack-selection.md")
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")

        for content in (interview, architecture, contract, frontend, workflow):
            for retired in (
                "PLAN-v5",
                "pr_head",
                "integration_head`",
                "production_head",
                "merged_main",
            ):
                self.assertNotIn(retired, content)
        for content in (interview, architecture, contract, workflow):
            self.assertIn("branch or ref", content)
        for content in (interview, architecture, contract):
            self.assertIn("signed tag", content.lower())

    def test_migration_order_drops_plan_v5_field_mapping(self) -> None:
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")

        for content in (architecture, contract):
            self.assertNotIn("`migration_classification`", content)
            self.assertNotIn("`commands.migrate`", content)
            self.assertNotIn("`prerequisites`", content)
            self.assertNotIn("`migration_command`", content)

    def test_workflow_accepts_native_local_data_without_hosting_platform(self) -> None:
        workflow_args = self.base_workflow_args()

        self.assertNotIn("deployment_platform", workflow_args)
        result = self.run_workflow(workflow_args)

        self.assertTrue(result["ok"])
        self.assertEqual("candidate_ready", result["status"])

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
                    self.release_target(
                        "web-development",
                        "web-app",
                        "Cloudflare",
                        "development",
                        "integration branch head",
                    ),
                    self.release_target(
                        "web-production",
                        "web-app",
                        "AWS",
                        "production",
                        "default branch head",
                    ),
                ],
            }
        )

        result = self.run_workflow(workflow_args)

        self.assertTrue(result["ok"])
        self.assertEqual("candidate_ready", result["status"])

    def test_workflow_requires_an_explicit_market_research_decision(self) -> None:
        workflow_args = self.base_workflow_args()
        del workflow_args["market_research"]

        result = self.run_workflow(workflow_args)

        self.assertFalse(result["ok"])
        self.assertIn("requires boolean args.market_research", result["error"])

    def test_market_research_lane_runs_by_default_and_can_be_turned_off(self) -> None:
        enabled = self.run_workflow(self.base_workflow_args())

        self.assertTrue(enabled["ok"])
        self.assertEqual("market-research", enabled["research"]["role"])
        self.assertEqual("complete", enabled["research"]["status"])
        self.assertEqual(["MR-001"], enabled["research"]["mr_ids"])

        disabled_args = self.base_workflow_args()
        disabled_args["market_research"] = False
        disabled = self.run_workflow(disabled_args)

        self.assertTrue(disabled["ok"])
        self.assertIsNone(disabled["research"])
        self.assertEqual("candidate_ready", disabled["status"])

    def test_market_research_delegation_requires_explicit_authorization(self) -> None:
        skill = self.read("SKILL.md")
        dynamic = self.read("references/dynamic-workflow.md")
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")

        self.assertIn(
            "a single read-only subagent only when the parent has a separate explicit subagent/delegation authorization",
            skill,
        )
        self.assertIn("no delegation authorization is present", skill)
        self.assertIn("args.multi_agent_authorized: true", dynamic)
        self.assertIn(
            "single read-only subagent only when the parent has a separate explicit delegation authorization",
            dynamic,
        )
        self.assertIn("requires explicit args.multi_agent_authorized=true", workflow)
        self.assertIn(
            "workflowArgs.single_agent_only === true || workflowArgs.sequential_only === true",
            workflow,
        )

        unauthorized = self.base_workflow_args()
        unauthorized["multi_agent_authorized"] = False
        result = self.run_workflow(unauthorized)
        self.assertFalse(result["ok"])
        self.assertIn(
            "requires explicit args.multi_agent_authorized=true", result["error"]
        )

    def test_dynamic_workflow_rejects_single_agent_or_sequential_only_constraints(
        self,
    ) -> None:
        for constraint in ("single_agent_only", "sequential_only"):
            workflow_args = self.base_workflow_args()
            workflow_args[constraint] = True
            result = self.run_workflow(workflow_args)
            self.assertFalse(result["ok"])
            self.assertIn(
                "cannot run when single-agent or sequential-only execution is required",
                result["error"],
            )

    def test_dynamic_workflow_rejects_non_boolean_execution_constraints(self) -> None:
        for constraint in ("single_agent_only", "sequential_only"):
            workflow_args = self.base_workflow_args()
            workflow_args[constraint] = "false"
            result = self.run_workflow(workflow_args)
            self.assertFalse(result["ok"])
            self.assertIn(
                f"requires boolean args.{constraint} when provided", result["error"]
            )

    def test_market_research_never_blocks_the_package(self) -> None:
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")

        status_expression = workflow[
            workflow.index("status: lanes.some") : workflow.index("lanes,\n  draft,")
        ]
        self.assertNotIn("research", status_expression)
        self.assertIn(
            'unresolved: ["The market-research workflow agent returned no result',
            workflow,
        )
        self.assertIn(
            'evidence: [rawResearch ? "workflow-role-mismatch" : "workflow-agent-null"]',
            workflow,
        )

    def test_market_research_role_forbids_fabricated_evidence(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/market-research-guide.md")
        contract = self.read("references/output-contract.md")
        workflow = self.read("assets/templates/CLAUDE_PRD_WORKFLOW.template.js")
        dynamic = self.read("references/dynamic-workflow.md")

        for content in (skill, guide, contract, workflow):
            self.assertIn("UNVALIDATED", content)
        self.assertIn("## Source Rules", guide)
        self.assertIn("Never state an unsourced claim as fact", guide)
        self.assertIn(
            "Do not invent competitor names, pricing, funding, user counts", guide
        )
        self.assertIn("| `sourced` |", guide)
        self.assertIn("| `reported` |", guide)
        self.assertIn("## Blocked Path", guide)
        self.assertIn("publisher, URL, and retrieval date", workflow)
        self.assertIn(
            "Do not present vendor marketing copy as verified capability", workflow
        )
        self.assertIn("never invent a competitor, price, or market figure", skill)
        self.assertIn("| market-research |", dynamic)
        self.assertIn("it never blocks the package on its own", dynamic)

    def test_market_research_artifact_is_contracted_and_published(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        self.assertIn("references/market-research-guide.md", skill)
        self.assertIn("`MR-*` for market-research findings", skill)
        self.assertIn("## `market-research.md`", contract)
        self.assertIn(
            "| MR ID | Finding | Lands in | Recommended change | Confidence | Sources |",
            contract,
        )
        self.assertIn(
            "| Source ID | Publisher | Title | URL | Retrieved | Type |", contract
        )
        self.assertIn(
            "`docs/product/market-research.md` when the market-research gap pass produced it",
            lifecycle,
        )
        self.assertIn(
            'is also this package\'s own artifact, not the general "research"',
            lifecycle,
        )
        self.assertIn("do not archive a prior `market-research.md` at all", lifecycle)
        self.assertIn("the market context is unvalidated", contract)

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
        self.assertIn(
            "`builder_readonly` launch profile, asserted via `args.tool_profile`", guide
        )
        self.assertIn(
            "Read only. Do not edit, create, move, or publish files", workflow
        )
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
        self.assertNotIn(
            "workflowArgs.browser_frontend || workflowArgs.has_backend", workflow
        )
        self.assertIn(
            "deployment_platform: workflowArgs.deployment_platform || null,", workflow
        )
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

    def test_design_system_not_required_is_a_normal_ui_outcome(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")

        self.assertIn(
            "Mark it `not_required` for a small or single-surface UI",
            skill,
        )
        self.assertIn(
            "`not_required` is a normal result for a small or single-surface UI",
            contract,
        )
        self.assertIn("publish no placeholder pair", skill)

    def test_call_three_drop_order_drops_exactly_one_question(self) -> None:
        interview = self.read("references/interview-guide.md")
        skill = self.read("SKILL.md")

        self.assertIn("four-question cap means exactly one question drops", interview)
        self.assertIn(
            "No archetype combination produces a sixth call-3 question", interview
        )
        self.assertIn("five against a four-question cap drops exactly one", skill)

    def test_browser_extension_is_a_supported_archetype(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        frontend = self.read("references/frontend-stack-selection.md")

        self.assertIn(
            "web app, mobile app, desktop app, browser extension, internal tool",
            skill,
        )
        self.assertIn(
            "browser extension, internal tool, automation or agent workflow, API, or a hybrid? (AskUserQuestion)",
            interview,
        )
        self.assertIn(
            "not a separate `AskUserQuestion` platform question", interview
        )
        self.assertIn(
            "An extension also skips the deployment-platform question", interview
        )
        self.assertIn(
            "or a browser-extension surface, whose release path is an app store, a signed installer, or a browser add-on store",
            interview,
        )
        self.assertIn("## Browser Extension Pattern", architecture)
        for marker in (
            "Manifest V3",
            "service worker",
            "Content scripts",
            "extension pages",
            "Permissions model",
            "chrome.runtime",
            "Chrome Web Store",
        ):
            self.assertIn(marker, architecture)
        self.assertIn("## Browser Extension Stacks", frontend)
        for marker in ("CRXJS", "WXT", "UI framework: optional", "Manifest V3"):
            self.assertIn(marker, frontend)

    def test_market_research_findings_can_land_in_stack_decisions(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/market-research-guide.md")

        self.assertIn(
            "Evidence that strengthens or contradicts a named technology choice",
            guide,
        )
        self.assertIn(
            "`stack-decisions.md` `Frontend Technology Decision`, "
            "`Mobile/Desktop Technology Decision`, or `Backend and Data Technology Decision` "
            "table (Why It Fits), citing the `MR-*` ID",
            guide,
        )
        self.assertIn(
            "| An alternative the market evidence speaks to | "
            "`stack-decisions.md` shared `Alternatives Considered` table",
            guide,
        )
        self.assertIn(
            "including evidence that strengthens or contradicts a "
            "`stack-decisions.md` layer row or alternative",
            skill,
        )

    def test_architecture_contract_has_frontend_and_backend_sections(self) -> None:
        contract = self.read("references/output-contract.md")

        component = contract.index("## Component Architecture")
        frontend = contract.index("## Frontend Architecture")
        backend = contract.index("## Backend Architecture")
        data_model = contract.index("## Data Model")
        self.assertLess(component, frontend)
        self.assertLess(frontend, backend)
        self.assertLess(backend, data_model)

        architecture_block = contract[component:data_model]
        for marker in (
            "surface composition",
            "state and data-fetch approach",
            "routing",
            "build/bundling",
            "`stack-decisions.md`",
        ):
            self.assertIn(marker, architecture_block)
        self.assertIn("Omit this section only when the product ships no frontend", architecture_block)
        self.assertIn("service boundaries, API style, data access, and background jobs", architecture_block)
        self.assertIn("one line stating that there is no backend and why", architecture_block)

    def test_provisional_stack_rows_gate_publication(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")

        self.assertIn(
            "every `stack-decisions.md` layer row must be `Required`, `Selected`, or `Recommended`",
            skill,
        )
        self.assertIn(
            "a `Provisional` row blocks publication until it is resolved with the user "
            "or the user explicitly accepts it as `Provisional`",
            skill,
        )
        self.assertIn(
            "that acceptance is recorded in `stack-decisions.md`", skill
        )
        self.assertIn(
            "Before publishing, every `stack-decisions.md` layer row is "
            "`Required`, `Selected`, or `Recommended`",
            contract,
        )
        self.assertIn(
            "explicitly accepted it as `Provisional`, and that acceptance is recorded in "
            "`stack-decisions.md`",
            contract,
        )

    def test_wireframe_reference_pass_consults_comparable_structures(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/wireframe-guide.md")
        contract = self.read("references/output-contract.md")

        self.assertIn("## Reference Pass", guide)
        for marker in (
            "two to four of the best-known live products",
            "A fetched real page outranks any secondhand summary of it",
            "design gallery such as Dribbble",
            "A gallery shot ranks below a live mainstream product",
            "structural pattern adopted or rejected",
            "They never create scope",
            "override the Builder UX Direction Decision",
            "UNVALIDATED",
        ):
            self.assertIn(marker, guide)
        self.assertIn(
            "Run `references/wireframe-guide.md`'s Reference Pass before drafting the HTML",
            skill,
        )
        self.assertIn(
            "fetch the structures of mainstream comparable sites", skill
        )
        self.assertIn(
            "record them in `PRD.md`'s `### Wireframe Approval` as "
            "`Wireframe references consulted:`",
            skill,
        )
        self.assertIn("Wireframe references consulted:", contract)
        self.assertIn(
            "reason the Reference Pass was skipped",
            contract,
        )

    def test_enhancement_classifies_ui_impact_before_drafting(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        guide = self.read("references/wireframe-guide.md")
        contract = self.read("references/output-contract.md")

        self.assertIn(
            "classify the delta's UI impact explicitly with the owner", interview
        )
        self.assertIn(
            "`none` (no UI change), `structure` (screens, regions, flows, or states "
            "change), `style` (the visual direction or design system is affected), "
            "or `both`",
            interview,
        )
        self.assertIn(
            "Never assume `none` because the request reads backend- or data-side",
            interview,
        )
        self.assertIn("## Enhancement Revisions", guide)
        for marker in (
            "re-run the Wireframe Approval Gate on the changed scope",
            "re-run `references/ui-design-pass.md` for the affected scope",
            "a stale visual contract never publishes silently",
        ):
            self.assertIn(marker, guide)
        self.assertIn(
            "first classify the delta's UI impact with the owner", skill
        )
        self.assertIn(
            "a stale visual contract never publishes silently", skill
        )
        self.assertIn(
            "An enhancement package records its UI-impact classification", contract
        )
        self.assertIn(
            "a style-impacting enhancement with an unchanged handoff or design-system "
            "pair and no recorded owner decision does not validate",
            contract,
        )

    def test_iconography_is_researched_not_remembered(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/ui-design-pass.md")
        contract = self.read("references/output-contract.md")

        for marker in (
            "Choose iconography through an online lookup, not from memory",
            "currently maintained icon libraries",
            "license, framework support, and maintenance status",
            "one primary icon set plus a named fallback",
            "mark an unevidenced pick `UNVALIDATED`",
            "never silently default to a remembered library",
        ):
            self.assertIn(marker, guide)
        self.assertIn(
            "Choose iconography through `references/ui-design-pass.md`'s online lookup",
            skill,
        )
        self.assertIn("Iconography:", contract)
        self.assertIn(
            "a visual package with no iconography line does not validate",
            contract,
        )


if __name__ == "__main__":
    unittest.main()

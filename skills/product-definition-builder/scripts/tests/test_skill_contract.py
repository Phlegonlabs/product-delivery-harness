import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
UI_SKILL_ROOT = SKILL_ROOT.parent / "ui-design-builder"


class ProductDefinitionBuilderSkillContractTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        path = SKILL_ROOT / relative_path
        if not path.is_file():
            path = UI_SKILL_ROOT / relative_path
        return path.read_text(encoding="utf-8")

    def read_ui(self, relative_path: str) -> str:
        return (UI_SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def read_agent_prompt(self) -> str:
        return " ".join(self.read("agents/openai.yaml").split())

    def run_workflow(self, workflow_args: dict) -> dict:
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required for workflow behavior tests")
        workflow_path = SKILL_ROOT / "scripts/product_agent_graph.cjs"
        runner = r"""
const fs = require("fs");
const { createProductAgentGraph } = require(process.argv[1]);
const workflowArgs = JSON.parse(fs.readFileSync(0, "utf8"));
const calls = [];
function phase() {}
async function parallel(tasks) {
  return Promise.all(tasks.map((task) => task()));
}
async function agent(_prompt, options) {
  const role = options.label.replace("prd:", "");
  calls.push({ role, prompt: _prompt });
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
      market_research_markdown: "# Market Research\n## Platform Optimization Recommendations\nSimplify onboarding; evidence RA-001; decision pending.",
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
    const graph = createProductAgentGraph(workflowArgs);
    const execute = (item) => agent(item.prompt, item);
    const lanes = await Promise.all(graph.analyze().map(execute));
    const draft = await execute(graph.synthesize(lanes));
    const reviews = await Promise.all(graph.review(draft).map(execute));
    const result = graph.finish(lanes, draft, reviews);
    process.stdout.write(JSON.stringify({ ok: true, status: result.status, research: result.research, draft: result.draft, calls }));
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
        release_name: str | None = None,
    ) -> dict:
        suffixes = {
            "web-app": "web",
            "public-api": "api",
            "ios-app": "ios",
            "android-app": "android",
            "macos-app": "macos",
            "windows-app": "windows",
            "browser-extension": "extension",
        }
        canonical_name = f"fixture-{suffixes.get(surface, surface)}"
        return {
            "id": target_id,
            "surface": surface,
            "surface_class": {
                "web-app": "hosted_web",
                "public-api": "hosted_api",
                "ios-app": "ios",
                "android-app": "android",
                "macos-app": "macos",
                "windows-app": "windows",
                "browser-extension": "browser_extension",
            }.get(surface, "other_nonpublic"),
            "public_discoverability": "yes" if surface == "web-app" else "no",
            "surface_suffix": suffixes.get(surface, surface),
            "release_name": release_name
            or (f"{canonical_name}-dev" if stage == "development" else canonical_name),
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
                    "exact candidate branch head after verification",
                ),
                self.release_target(
                    "ios-production",
                    "ios-app",
                    "App Store",
                    "production",
                    "main branch head after exact candidate PASS",
                ),
            ],
            "has_public_marketing_content": False,
            "monetization_model": "none",
            "partner_channel_model": "none",
            "stack_decision_mode": "review_recommendation",
            "data_trust_gate": "not_required",
            "security_requirements_gate": "required",
            "security_scope": "executable",
            "ai_automation_gate": "not_required",
            "include_implementation_plan": False,
            "market_research": True,
            "tool_profile": "builder_readonly",
            "multi_agent_authorized": True,
            "ui_design_owner": "Product owner",
            "mobile_desktop_platform": "native iOS",
        }

    def test_completeness_lenses_cover_native_ui_without_browser_lane(self) -> None:
        result = self.run_workflow(self.base_workflow_args())
        self.assertTrue(result["ok"], result)
        prompts = {call["role"]: call["prompt"] for call in result["calls"]}
        self.assertIn("product-level UI completeness lens", prompts["requirements"])
        self.assertIn("cross-screen handoffs", prompts["requirements"])
        self.assertIn("Do not create wireframes", prompts["requirements"])
        self.assertIn("technical completeness lens", prompts["architecture"])
        self.assertIn("technical completeness lens", prompts["backend"])
        self.assertIn("technical completeness lens", prompts["frontend-platform"])
        self.assertIn("duplicate effects", prompts["architecture"])
        self.assertIn("same journeys", prompts["backend"])
        self.assertIn("same journeys", prompts["frontend-platform"])
        self.assertNotIn("ui-designer", prompts)
        self.assertNotIn("ui-design-builder", {call["role"] for call in result["calls"]})

    def test_completeness_lens_does_not_add_ui_to_headless_product(self) -> None:
        workflow_args = self.base_workflow_args()
        workflow_args.update({
            "ui_bearing": False,
            "ui_design_owner": None,
            "mobile_desktop_platform": None,
            "deployable": False,
            "deployable_surfaces": [],
            "release_targets": [],
            "product_archetypes": ["automation"],
        })
        result = self.run_workflow(workflow_args)
        self.assertTrue(result["ok"], result)
        prompts = {call["role"]: call["prompt"] for call in result["calls"]}
        self.assertIn("caller or operator journeys", prompts["requirements"])
        self.assertNotIn("product-level UI completeness lens", prompts["requirements"])
        self.assertNotIn("frontend-platform", prompts)
        self.assertIn("technical completeness lens", prompts["architecture"])
        self.assertIn("technical completeness lens", prompts["backend"])

    def test_completeness_findings_reach_candidate_review_without_approval(self) -> None:
        result = self.run_workflow(self.base_workflow_args())
        self.assertTrue(result["ok"], result)
        prompts = {call["role"]: call["prompt"] for call in result["calls"]}
        self.assertIn("same candidate", prompts["synthesis"])
        self.assertIn("essential unresolved gap blocks approval", prompts["synthesis"])
        self.assertIn("remain blocked in this candidate", prompts["synthesis"])
        self.assertIn("Draft package:", prompts["consistency-verifier"])
        self.assertIn("cross-feature dependencies", prompts["consistency-verifier"])
        self.assertIn("without silently approving deferral", prompts["consistency-verifier"])
        self.assertIn("blocked when a human decision", prompts["consistency-verifier"])

    def test_skill_routes_browser_products_to_frontend_selection(self) -> None:
        skill = self.read("SKILL.md")
        agent = self.read_agent_prompt()

        self.assertIn("references/frontend-stack-selection.md", skill)
        self.assertIn("produce coherent bundles rather than disconnected menus", skill)
        self.assertIn(
            "`Recommended` and `Provisional` are non-executable draft states", skill
        )
        self.assertIn("Cloudflare is a deployment/runtime platform", skill)
        self.assertIn("component foundation such as shadcn/ui", agent)

    def test_product_definition_stops_before_ui_design_or_harness(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn("After step 15 passes, create no UI artifact", skill)
        self.assertIn("later explicit `ui-design-builder` request", skill)
        self.assertIn("UI design and implementation are separate optional phases", skill)

    def test_deployment_document_seeds_the_human_configuration_handoff(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        for phrase in (
            "Required Secrets and Variables",
            "External Console Setup",
            "Record names and destinations only, never values",
            "delivery-harness` to reconcile from the finished code",
        ):
            self.assertIn(phrase, skill)
        self.assertIn("Which secret and variable names go where", contract)
        self.assertIn("contain secret names only and no secret values", contract)
        self.assertIn("before a deployable push", lifecycle)

    def test_publish_uses_distinct_repository_context_templates(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn(
            "<delivery-harness-skill-root>/scripts/"
            'configure_project_context.py" --root <target-root> --check',
            skill,
        )
        self.assertIn("PROJECT_AGENTS.template.md` for `AGENTS.md`", skill)
        self.assertIn("PROJECT_CLAUDE.template.md` for `CLAUDE.md`", skill)
        self.assertIn("never copy one template to both files", skill)
        self.assertNotIn(
            "both files exist before any implementation run starts", skill
        )

    def test_ui_design_is_an_explicit_downstream_skill(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        agent = self.read_agent_prompt()

        for content in (skill, contract, agent):
            self.assertIn("ui-design-builder", content)
        self.assertNotIn("design-taste-frontend", skill)
        self.assertIn("complete frontend and backend architecture", contract)
        self.assertIn("A later explicit UI request invokes `ui-design-builder`", skill)
        self.assertIn("## UI Surface Contract", contract)
        self.assertIn("<!-- ui-surface-contract:start -->", contract)
        self.assertIn("<!-- ui-surface-contract:end -->", contract)
        self.assertIn("- `route`: [One literal route value", contract)
        self.assertIn("- `states`: [Comma-separated state IDs", contract)
        self.assertIn("- `responsive`: [This surface's exact responsive set", contract)
        self.assertIn("- `releaseSurface`:", contract)
        self.assertIn("- `surfaceClass`:", contract)
        self.assertIn("- `captureMode`:", contract)
        self.assertIn("invariant machine anchors", contract)
        self.assertNotIn("wireframes.md", contract)
        self.assertIn("## UI Design Handoff Status", contract)

    def test_seo_metadata_is_part_of_the_ui_surface_contract(self) -> None:
        contract = self.read("references/output-contract.md")

        self.assertIn(
            "- SEO metadata: [Per-route `<title>` and meta description", contract
        )
        self.assertIn(
            "canonical URL or `n/a — <reason>`", contract
        )
        self.assertIn("not an implementation-time invention", contract)
        self.assertIn("unique `<title>` and meta description", contract)
        self.assertIn("sitemap and robots policy", contract)
        self.assertIn("traces to its own `TEST-*` row", contract)

    def test_ui_design_builder_owns_wireframe_deliverable(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")
        guide = self.read("references/wireframe-guide.md")
        html_template = self.read("assets/templates/WIREFRAMES.template.html")
        workflow = self.read("scripts/product_agent_graph.cjs")

        for content in (skill, contract, lifecycle):
            self.assertIn("ui-design-builder", content)
        self.assertFalse((UI_SKILL_ROOT / "assets/templates/WIREFRAMES.template.md").exists())
        self.assertIn("`ui-design-builder` owns one wireframe deliverable", guide)
        self.assertIn("Create one screen for every `UI-*` entry", guide)
        self.assertIn("## HTML Requirements", guide)
        self.assertIn("Generate one self-contained file", guide)
        self.assertIn("an all-pages overview plus a page switcher", guide)
        self.assertIn("## Wireframe Validation Gate (wireframes/5)", guide)
        self.assertIn("## Historical Wireframe Approval", guide)
        self.assertIn("Later UI artifacts never override", contract)

        payload = html_template.split(
            '<script id="wireframe-data" type="application/json">', 1
        )[1].split("</script>", 1)[0]
        data = json.loads(payload)
        self.assertEqual(data["schema"], "wireframes/5")
        self.assertEqual(data["structureStatus"], "draft")
        self.assertIn("locale", data["copyInventory"])
        self.assertGreaterEqual(len(data["viewports"]), 3)
        self.assertEqual(
            set(data["canvasWidths"]), {str(value) for value in data["viewports"]}
        )
        self.assertEqual([screen["id"] for screen in data["screens"]], ["UI-001", "UI-002"])
        self.assertIn('id="responsive-controls"', html_template)
        self.assertIn("responsiveLayouts", html_template)
        self.assertIn("runLayoutQa", html_template)
        self.assertIn('id="state-controls"', html_template)
        self.assertIn('id="page-list"', html_template)
        self.assertIn('"Overview"', html_template)
        self.assertIn("Hero Section", html_template)
        self.assertIn("textContent", html_template)
        self.assertNotIn("https://", html_template)
        self.assertNotIn("wireframes_html_data_json", workflow)
        self.assertIn("do not create wireframe data", workflow)
        for screen in data["screens"]:
            self.assertTrue(screen["neverDrop"])
            self.assertEqual(
                set(screen["responsiveLayouts"]),
                {str(value) for value in data["viewports"]},
            )

        checker = UI_SKILL_ROOT / "scripts/check_wireframe_html.py"
        result = subprocess.run(
            [sys.executable, str(checker), "--html", str(UI_SKILL_ROOT / "assets/templates/WIREFRAMES.template.html")],
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
                    str(UI_SKILL_ROOT / "scripts/check_wireframe_html.py"),
                    "--html",
                    str(path),
                    *(extra_args or []),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_prd_cross_check_requires_matching_ui_sets(self) -> None:
        data = self.minimal_wireframe_data()
        with tempfile.TemporaryDirectory() as tmp:
            html_template = self.read("assets/templates/WIREFRAMES.template.html")
            marker = '<script id="wireframe-data" type="application/json">'
            original_payload = html_template.split(marker, 1)[1].split(
                "</script>", 1
            )[0]
            modified = html_template.replace(
                original_payload, "\n" + json.dumps(data) + "\n", 1
            )
            html_path = Path(tmp) / "wireframes.html"
            html_path.write_text(modified, encoding="utf-8")
            prd_path = Path(tmp) / "PRD.md"
            prd_path.write_text(
                "<!-- ui-surface-contract:start -->\n"
                "## 使用者介面契約\n\n"
                "### UI-001 — 儀表板\n\n"
                "- `route`: /\n"
                "- `states`: ready\n"
                "- `responsive`: viewports: 390, 768, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(UI_SKILL_ROOT / "scripts/check_wireframe_html.py"),
                    "--html", str(html_path),
                    "--prd", str(prd_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            prd_path.write_text(
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Dashboard\n\n"
                "- `route`: /different\n"
                "- `states`: ready\n"
                "- `responsive`: viewports: 390, 768, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(UI_SKILL_ROOT / "scripts/check_wireframe_html.py"),
                    "--html", str(html_path),
                    "--prd", str(prd_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("differs from the PRD route", result.stderr)

            prd_path.write_text(
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Dashboard\n\n"
                "- `route`: /\n"
                "- `states`: ready, empty\n"
                "- `responsive`: viewports: 390, 768, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(UI_SKILL_ROOT / "scripts/check_wireframe_html.py"),
                    "--html", str(html_path),
                    "--prd", str(prd_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("differ from the PRD states", result.stderr)

            prd_path.write_text(
                "<!-- ui-surface-contract:start -->\n"
                "## UI Surface Contract\n\n"
                "### UI-001 — Dashboard\n\n"
                "- `route`: /\n"
                "- `states`: ready\n\n"
                "- `responsive`: viewports: 390, 768, 1200\n"
                "### UI-002 — Settings\n\n"
                "- `route`: /settings\n"
                "- `states`: ready\n"
                "- `responsive`: viewports: 390, 768, 1200\n"
                "<!-- ui-surface-contract:end -->\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(UI_SKILL_ROOT / "scripts/check_wireframe_html.py"),
                    "--html", str(html_path),
                    "--prd", str(prd_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("absent from the wireframe", result.stderr)

    def test_prd_cross_check_rejects_ambiguous_machine_anchors(self) -> None:
        data = self.minimal_wireframe_data()
        valid_block = (
            "<!-- ui-surface-contract:start -->\n"
            "## 介面契約\n\n"
            "### UI-001 — 儀表板\n\n"
            "- `route`: /\n"
            "- `states`: ready\n"
            "- `responsive`: viewports: 390, 768, 1200\n"
            "<!-- ui-surface-contract:end -->\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            html_template = self.read("assets/templates/WIREFRAMES.template.html")
            marker = '<script id="wireframe-data" type="application/json">'
            original_payload = html_template.split(marker, 1)[1].split(
                "</script>", 1
            )[0]
            html_path = Path(tmp) / "wireframes.html"
            html_path.write_text(
                html_template.replace(
                    original_payload, "\n" + json.dumps(data) + "\n", 1
                ),
                encoding="utf-8",
            )
            prd_path = Path(tmp) / "PRD.md"
            cases = (
                (
                    "missing boundary",
                    "## UI Surface Contract\n\n### UI-001 — Dashboard\n\n"
                    "- `route`: /\n- `states`: ready\n",
                    "boundary pair",
                ),
                ("duplicate boundary", valid_block + valid_block, "boundary pair"),
                (
                    "heading outside boundary",
                    "<!-- ui-surface-contract:start -->\n"
                    "## 介面契約\n"
                    "<!-- ui-surface-contract:end -->\n"
                    "### UI-001 — Outside\n\n"
                    "- `route`: /\n"
                    "- `states`: ready\n"
                    "- `responsive`: viewports: 390, 768, 1200\n",
                    "headings outside the ui-surface-contract boundary",
                ),
                (
                    "duplicate fields",
                    valid_block.replace(
                        "- `states`: ready\n",
                        "- `route`: /alias\n"
                        "- `states`: ready\n"
                        "- `states`: empty\n",
                    ),
                    "exactly one `route` anchor",
                ),
            )
            for label, prd_text, expected in cases:
                with self.subTest(label=label):
                    prd_path.write_text(prd_text, encoding="utf-8")
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(UI_SKILL_ROOT / "scripts/check_wireframe_html.py"),
                            "--html",
                            str(html_path),
                            "--prd",
                            str(prd_path),
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn(expected, result.stderr)
                    if label == "duplicate fields":
                        self.assertIn("exactly one `states` anchor", result.stderr)

    def minimal_wireframe_data(self) -> dict:
        return {
            "schema": "wireframes/3",
            "product": "P",
            "approvalStatus": "draft",
            "source": "PRD.md#UI-Surface-Contract",
            "viewports": [390, 768, 1200],
            "canvasWidths": {"390": 390, "768": 768, "1200": 1200},
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
                            "actions": ["T"],
                            "traces": ["UX-001"],
                        }
                    ],
                    "neverDrop": ["r1"],
                    "responsiveLayouts": {
                        "390": {
                            "order": ["r1"],
                            "hidden": [],
                            "columns": 1,
                            "spans": {"r1": 1},
                            "reflow": "Stack in one column",
                            "interaction": "Use touch-sized controls",
                        },
                        "768": {
                            "order": ["r1"],
                            "hidden": [],
                            "columns": 6,
                            "spans": {"r1": 6},
                            "reflow": "Use the medium grid",
                            "interaction": "Keep touch and pointer controls reachable",
                        },
                        "1200": {
                            "order": ["r1"],
                            "hidden": [],
                            "columns": 12,
                            "spans": {"r1": 12},
                            "reflow": "Use the expanded grid",
                            "interaction": "Support pointer and keyboard input",
                        },
                    },
                    "states": [{"id": "ready", "label": "Ready", "treatments": {}}],
                }
            ],
            "flows": [
                {
                    "from": "UI-001",
                    "trigger": "T",
                    "to": "UI-001",
                    "presentation": "page",
                }
            ],
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

        self.assertIn("each flow keeps `{from, trigger, to, presentation}`", guide)
        self.assertIn("`sourceState`, `control`, and `destination:{surface,state}`", guide)
        self.assertIsInstance(data["flows"], list)
        self.assertTrue(data["flows"])
        screen_ids = {screen["id"] for screen in data["screens"]}
        for flow in data["flows"]:
            for key in ("from", "trigger", "to", "presentation"):
                self.assertIsInstance(flow[key], str)
                self.assertTrue(flow[key].strip())
            self.assertIn(flow["from"], screen_ids)
            self.assertIn(flow["presentation"], {"page", "overlay", "feedback"})
            if flow["presentation"] in {"page", "overlay"}:
                self.assertIn(flow["to"], screen_ids)
        visible_actions = {
            (screen["id"], action["label"])
            for screen in data["screens"]
            for region in screen["regions"]
            for action in region["actions"]
        }
        flow_actions = {(flow["from"], flow["trigger"]) for flow in data["flows"]}
        self.assertEqual(visible_actions, flow_actions)
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

    def test_require_approved_blocks_draft_and_legacy_wireframes(self) -> None:
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
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be 'wireframes/4'", result.stderr)

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

    def test_ui_design_builder_has_frontend_design_and_impeccable_gates(self) -> None:
        skill = self.read_ui("SKILL.md")
        contract = self.read_ui("references/output-contract.md")
        guide = self.read_ui("references/ui-design-pass.md")

        for content in (skill, guide):
            self.assertIn("frontend-design", content)
            self.assertIn("Impeccable", content)
            self.assertNotIn("design-taste-frontend` leads", content)
        self.assertIn("Connected HiFi reference:", contract)
        self.assertIn("connected `ui-hifi/2` HTML package", guide)
        self.assertIn(
            "generationStatus: deferred",
            self.read_ui("references/wireframe-guide.md"),
        )
        self.assertIn("## Impeccable Quality Review And PRD-Bound Grading", guide)
        self.assertIn("Render every page-target-state", guide)
        self.assertIn("Design System Need Gate", guide)

    def test_ui_design_pass_records_provenance_and_retention_consequences(self) -> None:
        guide = self.read_ui("references/ui-design-pass.md")
        contract = self.read_ui("references/output-contract.md")
        references = self.read_ui("references/design-reference-guide.md")

        self.assertIn("design-reference-guide.md", guide)
        self.assertIn("`VD-*` ID", guide)
        self.assertIn("`REF-*` sources", guide)
        self.assertIn("`RP-*` principles", guide)
        self.assertIn("Archive superseded references", guide)
        self.assertIn("Selected direction: [VD-* ID", contract)
        self.assertIn("Record every inspected source with a stable `REF-*` ID", references)

    def test_market_research_precedes_style_aware_design_handoff(self) -> None:
        skill = self.read("SKILL.md")
        ui_skill = self.read_ui("SKILL.md")
        intake = self.read_ui("references/ui-design-intake.md")

        research = skill.index("13. Run the post-draft market-research reconciliation")
        approval = skill.index("15. Run Product Definition Approval")
        self.assertLess(research, approval)
        self.assertIn("after `product-definition-builder`", ui_skill)
        self.assertIn("Wait only when an unanswered preference blocks authoring", intake)
        self.assertIn("one recommended direction or three comparable directions", intake)

    def test_product_approval_presents_and_waits_on_the_complete_candidate(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        self.assertIn(
            "verified absolute Markdown links to the complete actual current PRD",
            skill,
        )
        for marker in (
            "Use staging paths while the candidate remains staged",
            "ask explicitly for Product Definition Approval",
            "Opening a file or browser panel is convenience only",
            "presenting the package is not approval",
            "published canonical absolute Markdown links",
            "if publication is deferred, report the actual staging links instead",
            "Wait for the owner's explicit decision before continuing",
        ):
            self.assertIn(marker, skill)
        self.assertIn("#### Human Review Presentation", contract)
        self.assertIn(
            "complete current PRD, architecture, and stack source",
            contract,
        )
        for marker in (
            "Link the staging location while the candidate remains staged",
            "canonical locations after publication",
            "plain path cannot replace those links",
            "do not claim approval readiness",
        ):
            self.assertIn(marker, contract)
        self.assertIn("awaiting explicit approval", lifecycle)

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
        self.assertIn("### Recorded or Approved Stack", contract)
        self.assertIn("### Rendering and Route Strategy", contract)
        self.assertIn("### Platform Compatibility Verification", contract)
        self.assertIn("### Unresolved Decision Protocol", contract)
        self.assertIn("A bare `TBD` does not pass validation", contract)

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
            "an evidence-narrowed deployment-platform choice for hosted surfaces",
            skill,
        )
        self.assertIn("## Candidate-to-Production Release Pattern", architecture)
        self.assertIn("never default to one silently", architecture)
        self.assertIn("AskUserQuestion", agent)
        self.assertIn("one repository and one codebase", architecture)
        self.assertIn("separately named development and production Workers", frontend)
        self.assertIn("Exact candidate run branch/ref", contract)
        self.assertIn("Exact remote `main` head", contract)
        self.assertIn("same verified candidate SHA", contract)
        self.assertIn("both initial delivery and enhancements start from observed remote `main`", skill)
        self.assertIn("candidate run branch/SHA", architecture)
        self.assertIn(
            "Source policy: [`stage=development; ref=run.integration.branch; ",
            contract,
        )
        self.assertIn("main-only branch model", agent)
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
            "[AQ-DEPLOYMENT-PLATFORM] For a deployable web, API, or hosted backend target",
            "recurring usability benchmarking? (AskUserQuestion)",
        ):
            self.assertIn(marked_bullet, interview)
        self.assertNotIn("existing brand reference. (AskUserQuestion", interview)
        self.assertIn(
            "do not call `AskUserQuestion` during any free-text segment",
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
            "Resolve database category separately from engine",
            agent,
        )
        self.assertIn(
            "auth strategy separately from provider",
            agent,
        )
        self.assertIn(
            "with AskUserQuestion and an evidence-backed recommendation route",
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

        self.assertIn("no persistent database, or an evidence-backed recommendation? (AskUserQuestion)", interview)
        self.assertIn("no auth, or an evidence-backed recommendation? (AskUserQuestion)", interview)
        self.assertIn("database category and auth strategy", skill)
        self.assertIn(
            "the resolved database category and auth strategy (or explicit recommendation request)",
            interview,
        )

    def test_skill_gates_the_backend_askuserquestion_call(self) -> None:
        skill = self.read("SKILL.md")

        self.assertIn(
            "skip database/auth questions only when the product provably has no backend", skill
        )
        self.assertIn(
            "Skip resolved or inapplicable questions", skill
        )
        self.assertIn(
            "Do not silently select a provider, framework, component system, CSS approach, database/auth implementation",
            skill,
        )

    def test_archetype_dependent_questions_come_after_the_archetype_answer(
        self,
    ) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")

        self.assertIn("Keep deployment and UI design preferences out of this call", skill)
        self.assertIn("depends on step 5's archetype answer", skill)
        self.assertIn("see Workflow step 7, after the archetype is known", skill)
        self.assertIn("question tool's actual per-call question and option limits", interview)
        self.assertIn("There is no host-specific or cross-phase total-call cap", interview)
        self.assertIn(
            "Never ask a final-phase question in the archetype call", interview
        )
        for slotted_bullet in (
            "[AQ-MOBILE-TARGETS] If the answer includes a mobile app",
            "[AQ-DESKTOP-TARGETS] If the answer includes a desktop app",
            "[AQ-CLIENT-STRATEGY] For a mobile or desktop client",
            "[AQ-BROWSER-TARGETS] If the answer is browser extension",
            "[AQ-STACK-DECISION-MODE] How should unresolved implementation technology be decided",
        ):
            self.assertIn(slotted_bullet, interview)
        self.assertIn(
            "Never drop an applicable decision",
            interview,
        )

    def test_trace_ids_and_publish_approval_are_explicit(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        for trace_prefix in ("`PRD-*`", "`ARCH-*`", "`UX-*`", "`TEST-*`"):
            self.assertIn(trace_prefix, skill)
        self.assertIn("## Architecture Trace Index", contract)
        self.assertIn("`design-system-compiler`", contract)
        self.assertIn("`UI-*`", contract)
        self.assertIn("| TEST ID | Test Type", contract)
        self.assertIn(
            "Passing validation also does not authorize an overwrite, move, or archive",
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
            contract.index("## UI Design Handoff Status"),
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
        workflow = self.read("scripts/product_agent_graph.cjs")

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
        monetization = self.read("references/monetization-and-partner-channel-guide.md")

        header = "| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |"
        self.assertEqual(6, contract.count(header))
        self.assertIn("## CLI and Toolchain Decision", contract)
        for status_rule in (
            "`Required` means a user, organization, or hard external constraint",
            "`Selected` means the current product or repository already adopted it",
            "`Approved` means the human owner accepted a new choice",
            "`Recommended` is evidence-backed advice not yet accepted",
            "`Provisional` is a leading choice pending named evidence",
        ):
            self.assertIn(status_rule, contract)
        self.assertIn("A section may mix statuses", contract)
        self.assertIn("Authority is not another status label", contract)
        for guide in (frontend, backend, mobile, monetization):
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
        workflow = self.read("scripts/product_agent_graph.cjs")
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
        self.assertIn("Record service topology first", agent)
        for content in (contract, backend, architecture, skill, workflow, agent):
            self.assertIn("monolith", content.lower())
            self.assertIn("monorepo", content.lower())
            self.assertIn("polyrepo", content.lower())

    def test_release_discovery_is_provider_neutral_and_complete(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")
        workflow = self.read("scripts/product_agent_graph.cjs")
        agent = self.read_agent_prompt()

        self.assertIn("## Provider-Neutral Release Target Pattern", architecture)
        self.assertIn("## Release Targets", contract)
        for field in (
            "stable target ID",
            "Surface class",
            "Public discoverability",
            "Surface suffix",
            "Release name",
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
            "complete inventory of expected deployable web, API, mobile, desktop, or browser-extension surfaces",
            interview,
        )
        self.assertIn(
            "For every deployable web, API, mobile, desktop, or browser-extension surface", skill
        )
        self.assertIn(
            "For every deployable web, API, mobile, desktop, or browser-extension surface", agent
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
        for content in (skill, interview, architecture, contract, agent):
            self.assertIn("<product-slug>-<surface-suffix>", content)
            self.assertIn("-dev", content)
            self.assertIn("-prod", content)
        self.assertIn("`web`, `api`, and `extension`", architecture)
        self.assertIn("`ios`, `android`, `macos`, or `windows`", architecture)
        self.assertIn("Chrome, Firefox", architecture)
        self.assertIn("public listing title may differ", architecture.lower())
        for content in (skill, interview, architecture, contract):
            self.assertIn("release name", content.lower())
            self.assertIn("surface", content.lower())
        self.assertIn("releaseNameSurfaces", workflow)
        self.assertIn(
            "Preserve stable release target IDs for unchanged targets", interview
        )
        self.assertIn("stable release target IDs from the prior package", contract)

    def test_release_availability_and_native_recovery_are_explicit(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")
        workflow = self.read("scripts/product_agent_graph.cjs")
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
        workflow = self.read("scripts/product_agent_graph.cjs")

        self.assertIn(
            'throw new Error("product-definition-builder-graph requires boolean args.deployable");',
            workflow,
        )
        self.assertIn(
            'throw new Error("product-definition-builder-graph requires args.release_targets as an array");',
            workflow,
        )
        for field in (
            '"id"',
            '"surface"',
            '"surface_suffix"',
            '"release_name"',
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
        self.assertIn(
            "preserve the supplied stable release target IDs, surface suffixes, and release names",
            workflow,
        )
        self.assertIn("preserve each supplied surface_suffix and release_name", workflow)
        self.assertIn("Upload or submission is not availability", workflow)

    def test_workflow_enforces_release_name_stage_pair(self) -> None:
        workflow_args = self.base_workflow_args()
        workflow_args["release_targets"][0]["release_name"] = "local-notes-ios-development"

        result = self.run_workflow(workflow_args)

        self.assertFalse(result["ok"])
        self.assertIn("must end release_name with -dev", result["error"])

        workflow_args = self.base_workflow_args()
        workflow_args["release_targets"][1]["release_name"] = "fixture-ios-prod"

        result = self.run_workflow(workflow_args)

        self.assertFalse(result["ok"])
        self.assertIn("must use the canonical surface name without -prod", result["error"])

        workflow_args = self.base_workflow_args()
        workflow_args["release_targets"][0]["surface_suffix"] = "app"

        result = self.run_workflow(workflow_args)

        self.assertFalse(result["ok"])
        self.assertIn(
            "canonical release_name must end with surface_suffix app", result["error"]
        )

    def test_workflow_accepts_extension_surface_release_names(self) -> None:
        workflow_args = self.base_workflow_args()
        workflow_args.update(
            {
                "product_archetypes": ["browser extension"],
                "deployable_surfaces": ["browser-extension"],
                "release_targets": [
                    self.release_target(
                        "extension-development",
                        "browser-extension",
                        "Chrome Web Store test group",
                        "development",
                        "exact candidate run branch head",
                        "fixture-extension-dev",
                    ),
                    self.release_target(
                        "extension-production",
                        "browser-extension",
                        "Chrome Web Store",
                        "production",
                        "main branch head after candidate PASS",
                        "fixture-extension",
                    ),
                ],
            }
        )

        result = self.run_workflow(workflow_args)

        self.assertTrue(result["ok"])
        self.assertEqual("candidate_ready", result["status"])

    def test_workflow_accepts_web_ios_hybrid_release_targets(self) -> None:
        workflow_args = self.base_workflow_args()
        workflow_args.update(
            {
                "product_archetypes": ["hybrid"],
                "browser_frontend": True,
                "hosted_deployable": True,
                "deployment_platform": "Cloudflare",
                "deployable_surfaces": ["web-app", "ios-app"],
                "mobile_desktop_platform": "native iOS",
                "release_targets": [
                    self.release_target("web-development", "web-app", "Cloudflare", "development", "exact candidate run branch head", "fixture-web-dev"),
                    self.release_target("web-production", "web-app", "Cloudflare", "production", "main branch head after candidate PASS", "fixture-web"),
                    self.release_target("ios-development", "ios-app", "TestFlight", "development", "exact candidate run branch head", "fixture-ios-dev"),
                    self.release_target("ios-production", "ios-app", "App Store", "production", "main branch head after candidate PASS", "fixture-ios"),
                ],
            }
        )
        result = self.run_workflow(workflow_args)
        self.assertTrue(result["ok"])
        self.assertEqual("candidate_ready", result["status"])

    def test_workflow_accepts_web_extension_hybrid_release_targets(self) -> None:
        workflow_args = self.base_workflow_args()
        workflow_args.update(
            {
                "product_archetypes": ["hybrid"],
                "browser_frontend": True,
                "hosted_deployable": True,
                "deployment_platform": "Cloudflare",
                "deployable_surfaces": ["web-app", "browser-extension"],
                "release_targets": [
                    self.release_target("web-development", "web-app", "Cloudflare", "development", "exact candidate run branch head", "fixture-web-dev"),
                    self.release_target("web-production", "web-app", "Cloudflare", "production", "main branch head after candidate PASS", "fixture-web"),
                    self.release_target("extension-development", "browser-extension", "Chrome Web Store test group", "development", "exact candidate run branch head", "fixture-extension-dev"),
                    self.release_target("extension-production", "browser-extension", "Chrome Web Store", "production", "main branch head after candidate PASS", "fixture-extension"),
                ],
            }
        )
        result = self.run_workflow(workflow_args)
        self.assertTrue(result["ok"])
        self.assertEqual("candidate_ready", result["status"])

    def test_workflow_accepts_api_android_and_desktop_release_targets(self) -> None:
        workflow_args = self.base_workflow_args()
        workflow_args.update(
            {
                "product_archetypes": ["hybrid"],
                "browser_frontend": True,
                "hosted_deployable": True,
                "deployment_platform": "Cloudflare",
                "deployable_surfaces": ["public-api", "android-app", "macos-app", "windows-app"],
                "mobile_desktop_platform": "native Android; native macOS; native Windows",
                "release_targets": [
                    self.release_target("api-development", "public-api", "Cloudflare", "development", "exact candidate run branch head", "fixture-api-dev"),
                    self.release_target("api-production", "public-api", "Cloudflare", "production", "main branch head after candidate PASS", "fixture-api"),
                    self.release_target("android-development", "android-app", "Play Console", "development", "exact candidate run branch head", "fixture-android-dev"),
                    self.release_target("android-production", "android-app", "Google Play", "production", "main branch head after candidate PASS", "fixture-android"),
                    self.release_target("macos-development", "macos-app", "Developer ID", "development", "exact candidate run branch head", "fixture-macos-dev"),
                    self.release_target("macos-production", "macos-app", "Mac App Store", "production", "main branch head after candidate PASS", "fixture-macos"),
                    self.release_target("windows-development", "windows-app", "MSIX signing", "development", "exact candidate run branch head", "fixture-windows-dev"),
                    self.release_target("windows-production", "windows-app", "Microsoft Store", "production", "main branch head after candidate PASS", "fixture-windows"),
                ],
            }
        )
        result = self.run_workflow(workflow_args)
        self.assertTrue(result["ok"])
        self.assertEqual("candidate_ready", result["status"])

    def test_workflow_rejects_release_name_reuse_across_surfaces(self) -> None:
        workflow_args = self.base_workflow_args()
        workflow_args.update(
            {
                "product_archetypes": ["hybrid"],
                "browser_frontend": True,
                "hosted_deployable": True,
                "deployment_platform": "Cloudflare",
                "deployable_surfaces": ["web-app", "marketing-web"],
                "release_targets": [
                    self.release_target(
                        "web-development",
                        "web-app",
                        "Cloudflare",
                        "development",
                        "exact candidate run branch head",
                        "fixture-web-dev",
                    ),
                    self.release_target(
                        "web-production",
                        "web-app",
                        "Cloudflare",
                        "production",
                        "main branch head after candidate PASS",
                        "fixture-web",
                    ),
                    self.release_target(
                        "marketing-development",
                        "marketing-web",
                        "Cloudflare",
                        "development",
                        "exact candidate run branch head",
                        "fixture-web-dev",
                    ),
                    self.release_target(
                        "marketing-production",
                        "marketing-web",
                        "Cloudflare",
                        "production",
                        "main branch head after candidate PASS",
                        "fixture-web",
                    ),
                ],
            }
        )
        for target in workflow_args["release_targets"]:
            target["surface_suffix"] = "web"

        result = self.run_workflow(workflow_args)

        self.assertFalse(result["ok"])
        self.assertIn(
            "release_name fixture-web-dev is reused across surfaces web-app and marketing-web",
            result["error"],
        )

    def test_release_sources_enforce_candidate_branch_and_main_only(self) -> None:
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")
        frontend = self.read("references/frontend-stack-selection.md")
        workflow = self.read("scripts/product_agent_graph.cjs")

        for content in (interview, architecture, contract, frontend, workflow):
            for retired in (
                "PLAN-v5",
                "pr_head",
                "integration_head`",
                "production_head",
                "merged_main",
            ):
                self.assertNotIn(retired, content)
        for content in (interview, architecture, workflow):
            self.assertTrue("branch or ref" in content or "branch/ref" in content)
        for content in (interview, architecture):
            self.assertIn("refs/heads/main", content)
            self.assertTrue(
                "signed tag" in content.lower()
                or "tags and alternative production refs are rejected" in content.lower()
            )
        self.assertIn("promotion.verified_main_sha", contract)

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
                        "exact candidate run branch head",
                    ),
                    self.release_target(
                        "web-production",
                        "web-app",
                        "AWS",
                        "production",
                        "main branch head after candidate PASS",
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
        work_graph = self.read("references/agent-work-graph.md")
        workflow = self.read("scripts/product_agent_graph.cjs")

        self.assertIn(
            "a single read-only subagent only when the parent has a separate explicit subagent/delegation authorization",
            skill,
        )
        self.assertIn("no delegation authorization is present", skill)
        self.assertIn("args.multi_agent_authorized: true", work_graph)
        self.assertIn(
            "single read-only subagent only when the parent has a separate explicit delegation authorization",
            work_graph,
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

    def test_agent_work_graph_rejects_single_agent_or_sequential_only_constraints(
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

    def test_agent_work_graph_rejects_non_boolean_execution_constraints(self) -> None:
        for constraint in ("single_agent_only", "sequential_only"):
            workflow_args = self.base_workflow_args()
            workflow_args[constraint] = "false"
            result = self.run_workflow(workflow_args)
            self.assertFalse(result["ok"])
            self.assertIn(
                f"requires boolean args.{constraint} when provided", result["error"]
            )

    def test_market_research_never_blocks_the_package(self) -> None:
        workflow = self.read("scripts/product_agent_graph.cjs")

        status_match = re.search(r"status: lanes\.some.*?(?=\n\s*lanes,)", workflow, re.S)
        self.assertIsNotNone(status_match)
        status_expression = status_match.group(0)
        self.assertNotIn("research", status_expression)
        self.assertIn(
            'unresolved: ["The market-research analysis agent returned no result',
            workflow,
        )
        self.assertIn(
            'evidence: [rawResearch ? "analysis-role-mismatch" : "analysis-agent-null"]',
            workflow,
        )

    def test_market_research_role_forbids_fabricated_evidence(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/market-research-guide.md")
        contract = self.read("references/output-contract.md")
        workflow = self.read("scripts/product_agent_graph.cjs")
        work_graph = self.read("references/agent-work-graph.md")

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
        self.assertIn("| market-research |", work_graph)
        self.assertIn("it never blocks the package on its own", work_graph)

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

    def test_research_first_gate_runs_before_any_closed_set_decision(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/research-first-guide.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")
        market = self.read("references/market-research-guide.md")

        # The assessment is its own workflow step, ordered between the
        # free-text interview and the first AskUserQuestion batch.
        self.assertIn("4. Run the research-first assessment", skill)
        interview_at = skill.index("Conduct exactly three bounded free-text turns")
        assessment_at = skill.index("4. Run the research-first assessment")
        first_batch_at = skill.index("5. After all applicable free-text segments")
        self.assertLess(interview_at, assessment_at)
        self.assertLess(assessment_at, first_batch_at)
        self.assertIn(
            "before any closed-set decision", skill,
        )
        self.assertIn("In enhancement mode, skip this step entirely", skill)

        # The gate vocabulary, owner, and stop behavior are pinned.
        self.assertIn("`go | clarify | stop`", skill)
        self.assertIn("The researcher recommends; the human owner decides", guide)
        self.assertIn("Draft nothing. Report the findings", guide)
        self.assertIn("recorded as `clarify` with the decisive question stated", guide)

        # Source discipline is reused from the market-research guide, not duplicated.
        self.assertIn(
            "Apply `references/market-research-guide.md`'s Source Rules", guide
        )
        self.assertIn("never invent a competitor, price, user count, or market figure", guide)

        # The artifact, its publish path, and its trace family are contracted.
        self.assertIn("`RA-*` for research-first assessment findings", skill)
        self.assertIn("## `research-assessment.md`", contract)
        self.assertIn("| RA ID | Finding | Confidence | Sources |", contract)
        self.assertIn(
            "`docs/product/research-assessment.md` when the research-first assessment produced it",
            lifecycle,
        )
        self.assertIn("never while keeping a `PRD.md` that cites its `RA-*` IDs", lifecycle)
        self.assertIn("`RA-*` IDs follow the `MR-*` discipline", guide)

        # PRD records the gate; a silently missing gate does not validate.
        self.assertIn("### Research Gate", contract)
        self.assertIn(
            "Research Gate: [go / clarify / stop / skipped]",
            contract,
        )
        self.assertIn("A silently missing Research Gate", contract)
        self.assertIn("every retained `docs/product/outcomes/*.md` record in full", skill)

        # The post-draft pass reconciles the assessment instead of
        # researching the same ground twice.
        self.assertIn("plus `research-assessment.md` when the pre-draft pass ran", skill)
        self.assertIn("The pass is a reconciliation", skill)
        self.assertIn(
            "`research-assessment.md` when the pre-draft research-first assessment ran",
            market,
        )
        self.assertIn("carry still-valid `RA-*` findings", market)

    def test_research_draft_recommendations_owner_choice_then_final_approvals(
        self,
    ) -> None:
        skill = self.read("SKILL.md")
        work_graph = self.read("references/agent-work-graph.md")

        order = [
            skill.index("4. Run the research-first assessment"),
            skill.index("12. Draft or repair the core Markdown package"),
            skill.index("Produce evidence-based Platform Optimization Recommendations"),
            skill.index("14. Run the Stack Decision Checkpoint"),
            skill.index("15. Run Product Definition Approval"),
        ]
        self.assertEqual(order, sorted(order))
        self.assertIn(
            "present the complete candidate and every recommendation to the owner",
            skill,
        )
        self.assertIn(
            "Apply only an owner-recorded accepted proposal",
            skill,
        )
        self.assertIn("Recommendations stay `pending`", work_graph)
        self.assertIn(
            "records explicit owner decisions, and applies only accepted proposals",
            work_graph,
        )

    def test_research_reuses_assessment_and_limits_new_search(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/research-first-guide.md")
        market = self.read("references/market-research-guide.md")
        contract = self.read("references/output-contract.md")

        for content in (skill, contract):
            self.assertIn(
                "feature baseline, differentiation, pricing/business-model baseline, and category benchmarks",
                content,
            )
        for heading in (
            "## Feature Baseline And Differentiation",
            "## Pricing And Business Model Baseline",
            "## Category Benchmarks",
        ):
            self.assertIn(heading, guide)
        self.assertIn(
            "Record these as evidence inputs, not speculative final requirements",
            guide,
        )
        self.assertIn(
            "research only newly raised, stale, or `UNVALIDATED` gaps",
            market,
        )
        self.assertIn(
            "research only newly raised, stale, or `UNVALIDATED` gaps",
            skill,
        )
        self.assertIn(
            "do not re-research settled market context or force a full market rerun",
            market,
        )

    def test_platform_optimization_recommendations_require_evidence_and_owner_decision(
        self,
    ) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/market-research-guide.md")
        contract = self.read("references/output-contract.md")
        work_graph = self.read("references/agent-work-graph.md")

        for content in (guide, contract):
            self.assertIn("## Platform Optimization Recommendations", content)
            self.assertIn("at most five useful", content)
            self.assertIn("None — [evidence-backed reason]", content)
            self.assertIn("Expected benefit hypothesis", content)
            self.assertIn(
                "`pending | accepted | revise | deferred | rejected`",
                content,
            )
        self.assertIn("Affected PRD: [sections and existing", guide)
        self.assertIn("Affected PRD: [section names and existing", contract)
        self.assertIn("never a measured-benefit claim", guide)
        self.assertIn("no measured-benefit claim", contract)
        self.assertIn("Never infer approval from silence", skill)
        self.assertIn("cannot erase an approval-blocking gap", skill)
        self.assertIn(
            "Deferral or rejection never clears an approval-blocking gap",
            contract,
        )
        self.assertIn("the role never applies them", work_graph)

    def test_approval_presents_complete_prd_and_recommendation_links(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")

        self.assertIn(
            "complete actual current PRD, architecture, stack decisions, every produced market/research artifact, and its Platform Optimization Recommendations",
            skill,
        )
        self.assertIn(
            "complete current PRD, architecture, and stack source; include every produced market/research artifact, its Platform Optimization Recommendations and decision statuses",
            contract,
        )
        self.assertIn("verified absolute Markdown links", skill)
        self.assertIn("plain path cannot replace those links", contract)

    def test_workflow_reconciles_after_drafting_without_applying_recommendations(self) -> None:
        args = self.base_workflow_args()
        args["source_paths"] = ["docs/product/.prd-staging/test/research-assessment.md"]
        args["source_summary"] = "RA-001: existing interviews found onboarding friction."
        result = self.run_workflow(args)
        self.assertTrue(result["ok"], result)
        roles = [call["role"] for call in result["calls"]]
        self.assertLess(roles.index("synthesis"), roles.index("market-research"))
        for role in ("requirements", "synthesis", "market-research"):
            prompt = next(call["prompt"] for call in result["calls"] if call["role"] == role)
            self.assertIn(args["source_summary"], prompt)
            self.assertIn(args["source_paths"][0], prompt)
        self.assertEqual("# PRD", result["draft"]["prd_markdown"])
        self.assertEqual("candidate_ready", result["status"])
        self.assertIn("decision pending", result["research"]["market_research_markdown"])
        self.assertNotIn("decision pending", result["draft"]["prd_markdown"])

        args["market_research"] = False
        skipped = self.run_workflow(args)
        self.assertTrue(skipped["ok"], skipped)
        self.assertIsNone(skipped["research"])
        self.assertNotIn("market-research", [call["role"] for call in skipped["calls"]])

    def test_recommendation_choices_receive_links_and_revisions_need_acceptance(self) -> None:
        skill = self.read("SKILL.md")
        step = skill.split("13. Run the post-draft market-research reconciliation", 1)[1].split("14. Run", 1)[0]
        self.assertIn("verified absolute Markdown links", step)
        self.assertLess(step.index("Verify the links"), step.index("wait for an explicit owner choice"))
        self.assertIn("explicit acceptance before changing the PRD", step)
        self.assertIn("no-recommendation result needs no proposal-choice round", step)

    def test_outcome_review_closes_the_loop_after_deployment(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")
        template = self.read("assets/templates/OUTCOME_REVIEW.template.md")

        # The review is an owner-initiated post-publish step with a closed
        # verdict vocabulary and real measurement windows.
        self.assertIn("24. When the owner asks for an outcome review", skill)
        self.assertIn("`no_change`, `enhancement`, or `incident`", skill)
        self.assertIn("never leave a run open waiting for adoption", skill)
        self.assertIn("Verdict: [no_change / enhancement / incident]", contract)
        self.assertIn(
            "| Metric | Baseline | Target | Window | Actual | Source |", contract
        )
        self.assertIn(
            "The measurement window is real elapsed time after deployment", contract
        )
        self.assertIn(
            'A review written at deploy time with "pending" actuals is a stub',
            contract,
        )

        # It publishes under an immutable dated path and feeds the next enhancement run.
        self.assertIn(
            "`docs/product/outcomes/YYYY-MM-DD-<release-set>.md` after each deployed release-set outcome review",
            lifecycle,
        )
        self.assertIn("every retained `docs/product/outcomes/*.md` record in full", skill)
        self.assertIn("`docs/product/outcomes/` contains immutable post-deployment records", lifecycle)
        self.assertIn("Activation source status:", contract)
        self.assertIn("matching verified `MS-*` sources", skill)
        self.assertIn("exact numeric window duration/start-after-deployment checks", skill)
        self.assertIn("targets listed by Activation Outcome Coverage", skill)
        self.assertIn("--require-verified-sources", contract)
        fence_open = False
        architecture_active = False
        for line in contract.splitlines():
            if line.startswith("```"):
                fence_open = not fence_open
            if line.strip() == "## `architecture.md`":
                architecture_active = not fence_open
        self.assertFalse(fence_open, "output contract Markdown fences must be balanced")
        self.assertTrue(architecture_active, "architecture output section must remain active Markdown")
        active_template = re.sub(r"```[^\n]*\n[\s\S]*?```", "", template)
        self.assertIn("| Incident | Containment | Human owner |", active_template)
        self.assertNotIn("| Incident | Release target | Containment |", active_template)
        self.assertIn("| Incident | Release target | Containment |", template)

    def test_activation_seed_is_create_once_and_owned_downstream(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")
        agent = self.read_agent_prompt()

        for source in (skill, contract, lifecycle, agent):
            self.assertIn("ACTIVATION.md", source)
            self.assertIn("product-activation", source)
        self.assertIn("does not already exist", skill)
        self.assertIn("preserve it byte-for-byte", skill)
        self.assertIn("one Outcome Coverage row for every PRD metric", skill)
        self.assertIn("any release target with an activation scope", skill)
        self.assertIn("api / backend", skill)
        self.assertIn("android", skill)
        self.assertIn("macos", skill)
        self.assertIn("windows", skill)
        self.assertIn("including hybrids", skill)
        self.assertIn('check_activation.py" --activation', skill)
        self.assertIn("--architecture <staged architecture.md>", skill)
        self.assertIn("never falls back to a bundled default", skill)
        self.assertIn("creates it only when absent", contract)
        self.assertIn("never stages, overwrites, archives, resets", contract)
        self.assertIn("Exclude it from the superseded-document inventory", lifecycle)

    def test_agent_work_graph_uses_org_roles_and_parent_owned_staging(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read("references/agent-work-graph.md")
        workflow = self.read("scripts/product_agent_graph.cjs")
        contract = self.read("references/output-contract.md")

        self.assertIn("stable PRD roles as an org graph", skill)
        self.assertIn("The stable org graph", guide)
        self.assertIn("The temporary work graph", guide)
        self.assertIn("current session's observed native tools", guide)
        self.assertIn("Preserve installed roles", guide)
        self.assertIn("Do not use a bundled launch script", guide)
        self.assertIn('typeof args === "string" ? JSON.parse(args) : args', workflow)
        self.assertIn('function analyze()', workflow)
        self.assertIn("function synthesize(rawLanes)", workflow)
        self.assertIn('function review(draft)', workflow)
        self.assertIn('function finish(rawLanes, draft, verifyResults)', workflow)
        self.assertIn("analysis-agent-null", workflow)
        self.assertIn("analysis-role-mismatch", workflow)
        self.assertIn("builder_readonly", workflow)
        self.assertIn(
            "`builder_readonly` launch profile, asserted via `args.tool_profile`", guide
        )
        self.assertIn(
            "Read only. Do not edit, create, move, or publish files", workflow
        )
        self.assertIn("## Harness Handoff Signals", contract)
        self.assertIn("not a canonical Harness PLAN or RUN graph", contract)

    def test_workflow_lanes_receive_resolved_platform_and_ui_owner(self) -> None:
        workflow = self.read("scripts/product_agent_graph.cjs")

        self.assertIn(
            'throw new Error("product-definition-builder-graph requires boolean args.ui_bearing");',
            workflow,
        )
        self.assertIn(
            "requires non-empty args.ui_design_owner for a ui_bearing product",
            workflow,
        )
        self.assertIn(
            'throw new Error("product-definition-builder-graph requires boolean args.hosted_deployable");',
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
        self.assertIn("ui_design_owner: workflowArgs.ui_design_owner || null,", workflow)
        self.assertIn("Never substitute or invent a platform or provider", workflow)

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
        skill = self.read_ui("SKILL.md")
        contract = self.read_ui("references/output-contract.md")

        self.assertIn("`not_required` uses the approved HiFi/UI/PRD contract", skill)
        self.assertIn("Decision: [required / not_required / blocked]", contract)
        self.assertIn(
            "publish no placeholder pair",
            self.read_ui("references/ui-design-pass.md"),
        )

    def test_closed_questions_batch_without_dropping_decisions(self) -> None:
        interview = self.read("references/interview-guide.md")
        skill = self.read("SKILL.md")

        self.assertNotIn("Codex CLI caps", skill)
        self.assertNotIn("drop order", interview)
        self.assertIn("minimum number of calls", interview)
        self.assertIn("do not drop an applicable decision", skill)
        rows = re.findall(
            r"^\| (AQ-[A-Z-]+) \| (independent|final) \| ([^|]+?) \|$",
            interview,
            re.MULTILINE,
        )
        expected = [
            ("AQ-ARCHETYPE", "independent", "Product archetype"),
            ("AQ-VALIDATION-DEPTH", "independent", "Validation depth"),
            ("AQ-DEPLOYMENT-PLATFORM", "final", "Deployment platform"),
            ("AQ-MOBILE-TARGETS", "final", "Mobile target operating systems"),
            ("AQ-DESKTOP-TARGETS", "final", "Desktop target operating systems"),
            ("AQ-CLIENT-STRATEGY", "final", "Native versus cross-platform client strategy"),
            ("AQ-BROWSER-TARGETS", "final", "Browser-extension targets"),
            ("AQ-MONETIZATION-MODEL", "final", "Monetization model"),
            ("AQ-PARTNER-CHANNEL", "final", "Partner channel"),
            ("AQ-DATABASE-CATEGORY", "final", "Database category"),
            ("AQ-AUTH-STRATEGY", "final", "Auth strategy"),
            ("AQ-STACK-DECISION-MODE", "final", "How the owner wants unresolved technology choices decided"),
        ]
        self.assertEqual(expected, rows)

        marked_bullets = [
            line
            for line in interview.splitlines()
            if re.match(r"^\s+- .*\(AskUserQuestion(?:,|\))", line)
        ]
        bullet_ids = [
            match.group(1)
            for line in marked_bullets
            if (match := re.match(r"^\s+- \[(AQ-[A-Z-]+)\]", line))
        ]
        inventory_ids = [row[0] for row in rows]
        self.assertEqual(len(inventory_ids), len(set(inventory_ids)))
        self.assertEqual(len(inventory_ids), len(marked_bullets))
        self.assertCountEqual(inventory_ids, bullet_ids)
        for question_id in inventory_ids:
            self.assertEqual(1, bullet_ids.count(question_id))

        for per_call_limit in range(1, 6):
            flattened: list[str] = []
            for phase in ("independent", "final"):
                phase_ids = [row[0] for row in rows if row[1] == phase]
                batches = [
                    phase_ids[start : start + per_call_limit]
                    for start in range(0, len(phase_ids), per_call_limit)
                ]
                flattened.extend(item for batch in batches for item in batch)
            self.assertEqual(inventory_ids, flattened)

    def test_monetization_and_partner_channels_are_separate_current_decisions(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        guide = self.read("references/monetization-and-partner-channel-guide.md")
        contract = self.read("references/output-contract.md")
        architecture = self.read("references/architecture-playbook.md")
        workflow = self.read("scripts/product_agent_graph.cjs")
        agent = self.read_agent_prompt()

        self.assertIn("references/monetization-and-partner-channel-guide.md", skill)
        self.assertIn("AQ-MONETIZATION-MODEL", interview)
        self.assertIn("AQ-PARTNER-CHANNEL", interview)
        self.assertIn("does not select RevenueCat or any other provider automatically", interview)
        self.assertIn("Monetization Infrastructure Gate", contract)
        self.assertIn("Partner Channel Gate", contract)
        self.assertIn("## Monetization and Partner Channel Technology Decision", contract)
        self.assertIn("A pricing strategy makes the gates applicable; it does not make RevenueCat automatically required", guide)
        self.assertIn("StoreKit may be sufficient", architecture)
        for provider in (
            "RevenueCat",
            "Qonversion",
            "Adapty",
            "Superwall",
            "Stripe Billing",
            "Paddle Billing",
            "Lemon Squeezy",
            "PartnerStack",
            "Rewardful",
            "FirstPromoter",
        ):
            self.assertIn(provider, guide)
        for motion in ("Affiliate", "Referral", "Reseller"):
            self.assertIn(f"**{motion}:**", guide)
        self.assertIn("monetization_model", workflow)
        self.assertIn("partner_channel_model", workflow)
        self.assertIn('key: "monetization-channel"', workflow)
        self.assertIn("Pricing does not automatically select RevenueCat", agent)

        commercial = self.base_workflow_args()
        commercial["monetization_model"] = "subscription"
        commercial["partner_channel_model"] = "reseller"
        result = self.run_workflow(commercial)
        self.assertTrue(result["ok"])
        self.assertEqual("candidate_ready", result["status"])

        for missing_field in ("monetization_model", "partner_channel_model"):
            workflow_args = self.base_workflow_args()
            workflow_args.pop(missing_field)
            result = self.run_workflow(workflow_args)
            self.assertFalse(result["ok"])
            self.assertIn(f"requires args.{missing_field}", result["error"])

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
            "[AQ-BROWSER-TARGETS] If the answer is browser extension", interview
        )
        self.assertIn(
            "A browser extension skips the hosted deployment-platform question",
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
        self.assertIn("The applicable `stack-decisions.md` technology table", guide)
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

    def test_unapproved_stack_rows_gate_product_approval_and_delivery(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")

        self.assertIn(
            "only `Required`, `Selected`, or `Approved` executable stack rows",
            skill,
        )
        self.assertIn(
            "`Recommended`, `Provisional`, or a blocked checkpoint remains staged and cannot enter Harness",
            skill,
        )
        self.assertIn(
            "Explicit delegation is recorded in the checkpoint", contract
        )
        self.assertIn(
            "only `Required`, `Selected`, or `Approved` executable rows",
            contract,
        )
        self.assertIn(
            "`Recommended` and `Provisional` may remain in a staged candidate but block Product Definition Approval and Harness",
            contract,
        )

    def test_wireframe_reference_pass_consults_comparable_structures(self) -> None:
        skill = self.read_ui("SKILL.md")
        guide = self.read_ui("references/wireframe-guide.md")
        contract = self.read_ui("references/output-contract.md")

        self.assertIn("## Reference Pass", guide)
        for marker in (
            "Inspect two to four useful sources in total",
            "A real reachable flow outranks a marketing screenshot",
            "design gallery only as a supplemental composition source",
            "Never let an isolated gallery image outrank a working product flow",
            "stable `WREF-*` entry",
            "exact screen or flow",
            "Adopt / Adapt / Avoid",
            "They never create scope",
            "override the approved UI Design Intake",
            "UNVALIDATED",
        ):
            self.assertIn(marker, guide)
        self.assertIn(
            "references/wireframe-guide.md",
            skill,
        )
        self.assertIn("Wireframe references consulted:", contract)
        self.assertIn(
            "or skip reason",
            contract,
        )

    def test_enhancement_classifies_ui_impact_before_drafting(self) -> None:
        skill = self.read("SKILL.md")
        interview = self.read("references/interview-guide.md")
        guide = self.read_ui("references/wireframe-guide.md")
        contract = self.read("references/output-contract.md")

        self.assertIn(
            "classify the delta's UI impact explicitly with the owner", interview
        )
        self.assertIn(
            "`style`-only request routes to `ui-design-builder`",
            interview,
        )
        self.assertIn("## Enhancement Revisions", guide)
        for marker in (
            "re-run Wireframe Validation on the changed scope",
            "re-run `references/ui-design-pass.md` for the affected scope",
            "A stale visual contract never publishes silently",
        ):
            self.assertIn(marker, guide)
        self.assertIn(
            "record the complete Enhancement Impact Record first", skill
        )
        self.assertIn(
            "stale product, stack, data, commercial, release, wireframe, or visual contracts never publish silently", skill
        )
        self.assertIn(
            "An enhancement package records the complete Enhancement Impact Record", contract
        )
        self.assertIn(
            "Each changed row names affected IDs/decisions, refreshed artifacts, and rerun gates",
            contract,
        )

    def test_iconography_is_researched_not_remembered(self) -> None:
        skill = self.read_ui("SKILL.md")
        guide = self.read_ui("references/ui-design-pass.md")
        contract = self.read_ui("references/output-contract.md")

        for marker in (
            "Choose iconography through current official-source lookup",
            "Lucide, Phosphor, Heroicons, and Tabler",
            "select one primary and one named fallback",
            "license, framework support, maintenance evidence",
            "never silently choose from memory",
        ):
            self.assertIn(marker, guide)
        self.assertIn("Style Integration", skill)
        self.assertIn("imagery, and motion rules", contract)

    def test_typography_color_and_styling_layers_are_decided_with_evidence(self) -> None:
        skill = self.read("SKILL.md")
        guide = self.read_ui("references/ui-design-pass.md")
        contract = self.read_ui("references/output-contract.md")
        frontend = self.read("references/frontend-stack-selection.md")

        for marker in (
            "Choose typography with the same evidence discipline",
            "Latin and CJK coverage",
            "fallback order",
            "loading strategy",
            "palette derivation",
            "dark mode",
        ):
            self.assertIn(marker, guide)
        self.assertIn("Candidate theme:", contract)
        self.assertIn("component foundation (including shadcn/ui when chosen), styling approach", skill)
        self.assertIn("| Styling approach |", frontend)
        self.assertIn(
            "Record component foundation and styling as separate layer rows", frontend
        )

    def test_design_reference_preview_is_interactive_auth_free_and_generation_deferred(self) -> None:
        guide = self.read_ui("references/ui-design-pass.md")
        contract = self.read_ui("references/output-contract.md")

        lowered = guide.lower()
        self.assertIn("connected `ui-hifi/2` html package", lowered)
        self.assertIn("login, registration, recovery", lowered)
        self.assertIn(
            "generationstatus: deferred",
            self.read_ui("references/wireframe-guide.md").lower(),
        )
        for marker in (
            "A product tab or page link uses a real anchor",
            "Buttons change a declared local state, including overlays and feedback",
            "calls no live backend, credential, identity provider, or unapproved generation provider",
            "Generated output cannot add copy, controls, states, routes, or claims",
        ):
            self.assertIn(marker, guide)
        for forbidden in (
            "Clicking a login or sign-in action immediately switches",
            "auth-related UI states remain directly selectable",
            "imagegen-frontend-web",
            "imagegen-frontend-mobile",
            "embed each retained image as a data URI",
        ):
            self.assertNotIn(forbidden, guide)
        for marker in (
            "PRD source:",
            "Motion And Media Intent",
            "Connected HiFi reference:",
            "Impeccable critique:",
            "Approved target:",
        ):
            self.assertIn(marker, contract)

    def test_multi_agent_ui_grading_is_prd_bound_authorized_and_capability_optional(self) -> None:
        skill = self.read_ui("SKILL.md")
        wireframe = self.read_ui("references/wireframe-guide.md")
        guide = self.read_ui("references/ui-design-pass.md")
        rubric = self.read_ui("references/ui-grading-rubric.md")
        contract = self.read_ui("references/output-contract.md")

        for marker in (
            "exact PRD and `ui-design.md` paths",
            "Capability does not grant permission",
            "grading gate is blocked",
            "matching current RUN `spawn_subagents` grant",
            "one complete diagnostic wave",
            "Default to one fresh lead grader",
            "at most two fresh specialist sibling graders",
            "integer score from `0` to `100`",
            "`80–100 — pass`",
            "`60–79 — advisory`",
            "`0–59 — block`",
            "wireframe overall score",
            "overall score is at least `80`",
            "design-reference overall score",
            "overall score is at least `90`",
            "each score at least `90`",
            "`H2 Layout safety`, `H4 Responsive and edge states`, and `H8 Accessibility`",
            "Any such failure on required content is a `block`",
            "`W1 PRD conformance`",
            "`W5 Structural clarity and evidence`",
            "`H3 Interaction wiring`",
            "`H6 Media and motion fit`",
            "`H7 Creative distinction`",
            "`H8 Accessibility`",
            "`H9 Design consistency`",
            "## Technical Hard Gate",
            "no uncaught console error",
            "without duplicate event effects or stale state",
            "run a DOM geometry scan",
            "With one grader, use its score directly",
            "reconciled numeric value for each dimension is their median score",
            "differ by more than 20 points",
            "mark it `disputed`",
            "one consolidated defect ledger",
            "one repair batch",
            "one re-review",
            "stop at `blocked`",
            "explicit owner decision",
            "not a new grading or repair round",
            "new revision cycle",
            "Do not present a below-threshold candidate",
            "earns no credit by adding unapproved scope",
        ):
            self.assertIn(marker, rubric)
        self.assertNotIn("graders: parent-only", rubric)
        self.assertIn("Impeccable critique:", contract)
        self.assertIn("one consolidated repair batch", skill)
        self.assertIn("one re-review", skill)
        self.assertIn("one consolidated repair batch", wireframe)
        self.assertIn("complete rubric once", guide)

    def test_motion_and_media_gate_separates_ui_motion_from_generated_assets(self) -> None:
        skill = self.read_ui("SKILL.md")
        interview = self.read("references/interview-guide.md")
        wireframe = self.read_ui("references/wireframe-guide.md")
        guide = self.read_ui("references/ui-design-pass.md")
        rubric = self.read_ui("references/ui-grading-rubric.md")
        contract = self.read_ui("references/output-contract.md")
        router = self.read_ui("references/motion-and-media-routing.md")

        for content in (skill, guide, rubric, contract):
            self.assertIn("motion and media intent", content.lower())
        self.assertIn("`mediaIntent`", router)
        for treatment in ("`none`", "`image`", "`motion`", "`image + motion`"):
            self.assertIn(treatment, router)
        self.assertIn("GSAP", router)
        self.assertIn("Higgsfield MCP", router)
        self.assertIn("reduced-motion", router)
        self.assertIn("Do not ask about preferred density", interview)
        self.assertIn("generationStatus: deferred", wireframe)
        self.assertIn("implements no final image or animation", wireframe)

    def test_wireframe_actions_and_media_handoffs_are_executable_and_validated(self) -> None:
        wireframe = self.read_ui("references/wireframe-guide.md")
        template = self.read_ui("assets/templates/WIREFRAMES.template.html")
        checker = self.read_ui("scripts/check_wireframe_html.py")

        for content in (wireframe, template):
            self.assertIn("page", content)
            self.assertIn("overlay", content)
            self.assertIn("feedback", content)
        for marker in (
            '"presentation": "page"',
            '"presentation": "overlay"',
            '"presentation": "feedback"',
            "dialog.showModal()",
            "dataset.flowTrigger = label",
            '"generationStatus": "deferred"',
            '"generationRoute"',
            '"reducedMotionFallback"',
        ):
            self.assertIn(marker, template)
        for marker in (
            "VALID_FLOW_PRESENTATIONS",
            "VALID_MEDIA_TREATMENTS",
            "_validate_media_intent",
            "must bind the visible product action ID and trigger",
            "must name a declared source screen state",
            "must name a declared destination screen state",
            "must match exactly one visible region action",
        ):
            self.assertIn(marker, checker)
        self.assertIn("wireframes/4", checker)
        self.assertIn("Higgsfield MCP", template)

    def test_wireframe_reviewer_javascript_parses(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required for wireframe JavaScript validation")
        template_path = UI_SKILL_ROOT / "assets/templates/WIREFRAMES.template.html"
        runner = r"""
const fs = require("fs");
const html = fs.readFileSync(process.argv[1], "utf8");
const scripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)];
if (scripts.length < 2) throw new Error("reviewer script missing");
new Function(scripts.at(-1)[1]);
"""
        completed = subprocess.run(
            [node, "-e", " ".join(runner.splitlines()), str(template_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_visual_phase_uses_frontend_design_then_impeccable(self) -> None:
        skill = self.read_ui("SKILL.md")
        guide = self.read_ui("references/ui-design-pass.md")

        self.assertIn("`frontend-design` is the single design author", skill)
        self.assertIn("Load `frontend-design`", guide)
        self.assertIn("Do not load `design-taste-frontend`", guide)
        self.assertIn("Run `impeccable critique` and `impeccable audit`", guide)
        self.assertLess(
            guide.index("## Frontend Design Style Integration"),
            guide.index("## Impeccable Quality Review"),
        )

    def test_product_definition_approval_precedes_ui_design_builder(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        ui_skill = self.read_ui("SKILL.md")
        wireframe = self.read_ui("references/wireframe-guide.md")

        order = [
            skill.index("12. Draft or repair the core Markdown package"),
            skill.index("13. Run the post-draft market-research reconciliation"),
            skill.index("14. Run the Stack Decision Checkpoint"),
            skill.index("15. Run Product Definition Approval"),
            skill.index("16. After step 15 passes, create no UI artifact"),
        ]
        self.assertEqual(order, sorted(order))
        for marker in (
            "<!-- product-definition-approval:start -->",
            "<!-- product-definition-approval:end -->",
            "## Product Definition Decisions",
            "### Product Definition Approval",
            "Package revision:",
            "Stack Decision Checkpoint:",
        ):
            self.assertIn(marker, contract)
        self.assertIn("check_product_package.py", skill)
        self.assertIn("including headless products", skill)
        self.assertIn("only after the core Product Definition package passes", wireframe)
        self.assertIn("only after `product-definition-builder`", ui_skill)

    def test_full_hifi_copy_review_does_not_require_a_circular_prd_rewrite(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        for content in (skill, contract, lifecycle):
            self.assertIn("full HiFi approval", content)
        self.assertIn(
            "A full HiFi approval may advance a PRD `draft` responsibility "
            "to approved exact copy without rewriting the PRD status",
            contract,
        )
        self.assertIn(
            "full HiFi approval may confirm validated schema-5 wireframe copy without a circular PRD rewrite",
            lifecycle,
        )
        self.assertIn(
            "PRD `revision_requested` or `blocked` copy stops UI work",
            skill,
        )
        self.assertNotIn(
            "any applicable Wireframe Approval, passing checkers",
            lifecycle,
        )

    def test_stack_checkpoint_separates_and_approves_implementation_layers(self) -> None:
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        frontend = self.read("references/frontend-stack-selection.md")

        for marker in (
            "<!-- stack-decision-checkpoint:start -->",
            "<!-- stack-decision-checkpoint:end -->",
            "## Stack Decision Checkpoint",
            "### Coherent Options Presented",
            "| Option ID | Area | Complete bundle | Best fit | Tradeoffs / ownership | Disposition |",
            "| Language |",
            "| Package manager |",
            "| Component foundation |",
            "| Styling approach |",
            "## AI and Automation Technology Decision",
        ):
            self.assertIn(marker, contract)
        self.assertIn("React and shadcn/ui are not peers", frontend)
        self.assertIn("two or three coherent stack bundles", frontend)
        self.assertIn("Mark accepted new choices `Approved`", frontend)
        self.assertIn("`Recommended` or `Provisional` blocks", skill)

    def test_data_trust_ai_metrics_and_open_questions_are_owner_decisions(self) -> None:
        skill = self.read("SKILL.md")
        work_graph = self.read("references/agent-work-graph.md")
        contract = self.read("references/output-contract.md")
        interview = self.read("references/interview-guide.md")
        workflow = self.read("scripts/product_agent_graph.cjs")

        for marker in (
            "Data and Trust Gate:",
            "AI and Automation Gate:",
            "| Metric | Definition | Baseline | Target / guardrail | Measurement window | Source / method | Owner |",
            "| Question | Why it matters | Owner | Decision deadline | Blocks approval | Status / resolution |",
            "## Data and Trust Architecture",
            "## AI and Automation Architecture",
        ):
            self.assertIn(marker, contract)
        self.assertIn("Which data is sensitive", interview)
        self.assertIn("For AI/automation", interview)
        self.assertIn("data_trust_gate", workflow)
        self.assertIn("Security Requirements Gate and Security scope", skill)
        self.assertIn("args.security_requirements_gate", work_graph)
        self.assertIn("args.security_scope", work_graph)
        self.assertIn("security_requirements_gate", workflow)
        self.assertIn("security_scope", workflow)
        self.assertIn("human residual-risk decision", workflow)
        self.assertIn("ai_automation_gate", workflow)
        self.assertIn('key: "ai-automation"', workflow)

    def test_workflow_requires_stack_and_trust_decision_inputs(self) -> None:
        for field in (
            "stack_decision_mode",
            "data_trust_gate",
            "security_requirements_gate",
            "security_scope",
            "ai_automation_gate",
        ):
            workflow_args = self.base_workflow_args()
            workflow_args.pop(field)
            result = self.run_workflow(workflow_args)
            self.assertFalse(result["ok"])
            self.assertIn(f"requires args.{field}", result["error"])

        blocked = self.base_workflow_args()
        blocked["data_trust_gate"] = "blocked"
        result = self.run_workflow(blocked)
        self.assertFalse(result["ok"])
        self.assertIn("cannot run while args.data_trust_gate is blocked", result["error"])

        security_blocked = self.base_workflow_args()
        security_blocked["security_requirements_gate"] = "blocked"
        result = self.run_workflow(security_blocked)
        self.assertFalse(result["ok"])
        self.assertIn(
            "cannot run while args.security_requirements_gate is blocked",
            result["error"],
        )

        executable_not_required = self.base_workflow_args()
        executable_not_required["security_requirements_gate"] = "not_required"
        result = self.run_workflow(executable_not_required)
        self.assertFalse(result["ok"])
        self.assertIn(
            "requires args.security_requirements_gate required when args.security_scope is executable",
            result["error"],
        )

        documentation_required = self.base_workflow_args()
        documentation_required["security_requirements_gate"] = "required"
        documentation_required["security_scope"] = "documentation_only"
        documentation_required["deployable"] = False
        documentation_required["deployable_surfaces"] = []
        documentation_required["release_targets"] = []
        result = self.run_workflow(documentation_required)
        self.assertTrue(result["ok"])
        self.assertEqual("candidate_ready", result["status"])

        deployable_not_required = self.base_workflow_args()
        deployable_not_required["security_requirements_gate"] = "not_required"
        deployable_not_required["security_scope"] = "documentation_only"
        result = self.run_workflow(deployable_not_required)
        self.assertFalse(result["ok"])
        self.assertIn(
            "requires args.security_requirements_gate required for deployable release targets",
            result["error"],
        )

    def test_mobile_destinations_are_separate_from_client_strategy(self) -> None:
        interview = self.read("references/interview-guide.md")
        mobile = self.read("references/mobile-stack-selection.md")

        for question_id in (
            "AQ-MOBILE-TARGETS",
            "AQ-DESKTOP-TARGETS",
            "AQ-CLIENT-STRATEGY",
            "AQ-BROWSER-TARGETS",
        ):
            self.assertIn(question_id, interview)
        self.assertIn("This decides destinations, not framework", interview)
        self.assertIn("Target operating systems", mobile)
        self.assertIn("Target operating systems, code-sharing strategy", mobile)


if __name__ == "__main__":
    unittest.main()

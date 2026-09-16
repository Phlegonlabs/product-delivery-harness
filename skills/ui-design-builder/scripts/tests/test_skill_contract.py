"""Contract tests for the UI Design Builder skill."""

import shutil
import subprocess
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]


class UiDesignBuilderSkillContractTests(unittest.TestCase):
    def test_wireframe_runtime_uses_target_context_and_discards_stale_qa(self):
        template = self.read("assets/templates/WIREFRAMES.template.html")
        self.assertIn("targetResponsiveTarget", template)
        self.assertIn("targetCanvasWidth", template)
        self.assertIn("regionOrder(target, targetResponsiveTarget)", template)
        self.assertIn("qaGeneration", template)
        self.assertIn("generation !== qaGeneration", template)
        self.assertIn("canvas.isConnected", template)

    def test_wireframe_runtime_executes_hybrid_fallback_and_stale_qa_guard(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required for wireframe runtime validation")
        template = SKILL_ROOT / "assets" / "templates" / "WIREFRAMES.template.html"
        runner = r'''
const fs = require("fs");
const vm = require("vm");
const html = fs.readFileSync(process.argv[1], "utf8");
const slice = (startMarker, endMarker) => {
  const start = html.indexOf(startMarker);
  const end = html.indexOf(endMarker, start);
  if (start < 0 || end < 0) throw new Error(`missing runtime marker ${startMarker}`);
  return html.slice(start, end);
};
const fixture = {
  responsiveBySurface: {
    "UI-WEB": {kind: "viewports", targets: [390, 1200], canvasWidths: {"390": 390, "1200": 1200}},
    "UI-IOS": {kind: "sizeClasses", targets: ["compact", "regular"], canvasWidths: {compact: 390, regular: 768}}
  },
  screens: [
    {id: "UI-WEB", regions: [{id: "W1"}, {id: "W2"}], responsiveLayouts: {"390": {order: ["W1", "W2"]}, "1200": {order: ["W2", "W1"]}}},
    {id: "UI-IOS", regions: [{id: "I1"}], responsiveLayouts: {compact: {order: ["I1"]}, regular: {order: ["I1"]}}}
  ]
};
const callbacks = [];
const context = {
  data: fixture,
  state: {page: "UI-WEB", responsiveTarget: "1200", screenState: "ready"},
  requestAnimationFrame: callback => callbacks.push(callback),
  getComputedStyle: () => ({overflowX: "visible", overflowY: "visible"}),
  window: {},
  console
};
vm.createContext(context);
const program = [
  slice("const responsiveSpecFor", "const initialPage"),
  "const currentScreen = () => data.screens.find((screen) => screen.id === state.page);",
  slice("const targetFor", "const appendList"),
  slice("const rectanglesOverlap", "const renderScreenFlows"),
  "globalThis.api = {responsiveSpecFor, targetFor, activeLayout, regionOrder, runLayoutQa};"
].join("\n");
vm.runInContext(program, context);
const web = fixture.screens[0];
const ios = fixture.screens[1];
if (context.api.targetFor(ios, "1200") !== "regular") throw new Error("native fallback did not use target-local default");
if (context.api.activeLayout(ios, "1200") !== ios.responsiveLayouts.regular) throw new Error("native layout used a web target");
if (context.api.regionOrder(web, "1200").map(item => item.id).join(",") !== "W2,W1") throw new Error("target-local region order failed");
const canvas = {isConnected: true, scrollWidth: 768, clientWidth: 768, querySelectorAll: () => []};
const shell = {isConnected: true, width: 1200, getBoundingClientRect() { return {width: this.width}; }};
const panel = {isConnected: true, setAttribute() {}, textContent: ""};
context.api.runLayoutQa(canvas, shell, panel, web);
context.state.page = "UI-IOS";
context.state.responsiveTarget = "regular";
shell.width = 768;
context.api.runLayoutQa(canvas, shell, panel, ios);
callbacks[0]();
if (context.window.wireframeQaResults) throw new Error("stale QA callback wrote a result");
callbacks[1]();
const keys = Object.keys(context.window.wireframeQaResults || {});
if (keys.length !== 1 || keys[0] !== "UI-IOS|regular|ready") throw new Error(`wrong QA key ${keys.join(",")}`);
if (context.window.wireframeQaResults[keys[0]].status !== "pass") throw new Error("current QA callback did not pass");
'''
        completed = subprocess.run(
            [node, "-e", runner, str(template)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)

    def read(self, relative: str) -> str:
        return (SKILL_ROOT / relative).read_text(encoding="utf-8")

    def test_skill_owns_ui_after_product_approval(self):
        skill = self.read("SKILL.md")
        self.assertIn("name: ui-design-builder", skill)
        self.assertIn("Product Definition Approval", skill)
        self.assertIn("docs/design/ui-design.md", skill)
        self.assertIn("docs/design/wireframes.html", skill)
        self.assertIn("Do not use for product scope, backend architecture", skill)

    def test_human_intake_precedes_wireframe_and_style(self):
        skill = self.read("SKILL.md")
        intake = skill.index("Run the **UI Design Intake Gate**")
        wireframe = skill.index("Use `frontend-design` as the frontend-authoring resource")
        style = skill.index("Run **Style Integration** with `frontend-design`")
        review = skill.index("Run the **Impeccable Quality Review")
        self.assertLess(intake, wireframe)
        self.assertLess(wireframe, style)
        self.assertLess(style, review)
        self.assertIn("End the turn and wait", skill)

    def test_frontend_design_authors_and_impeccable_reviews(self):
        skill = self.read("SKILL.md")
        pass_guide = self.read("references/ui-design-pass.md")
        rubric = self.read("references/ui-grading-rubric.md")
        for content in (skill, pass_guide):
            self.assertIn("`frontend-design`", content)
            self.assertIn("`impeccable critique`", content)
            self.assertIn("`impeccable audit`", content)
        self.assertIn("single design author", skill)
        self.assertIn("Impeccable", rubric)
        self.assertIn("`H1`–`H9`", pass_guide)

    def test_motion_and_media_router_is_conditional(self):
        router = self.read("references/motion-and-media-routing.md")
        for marker in (
            "`none`",
            "`image`",
            "`motion`",
            "`image + motion`",
            "`gsap-core`",
            "`gsap-timeline`",
            "`gsap-scrolltrigger`",
            "Higgsfield MCP",
            "exact provider/action authorization",
        ):
            self.assertIn(marker, router)
        self.assertIn("Do not add GSAP merely because motion exists", router)

    def test_new_wireframes_use_schema_four(self):
        checker = self.read("scripts/check_wireframe_html.py")
        template = self.read("assets/templates/WIREFRAMES.template.html")
        guide = self.read("references/wireframe-guide.md")
        for content in (checker, template, guide):
            self.assertIn("wireframes/4", content)
        self.assertIn("wireframes/3", checker)
        self.assertIn("Higgsfield MCP", template)

    def test_copy_freeze_precedes_structural_approval(self):
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        guide = self.read("references/wireframe-guide.md")
        self.assertLess(
            skill.index("Run the **Copy Freeze Gate**"),
            skill.index("Obtain explicit human Wireframe Approval"),
        )
        for marker in ("Copy Freeze:", "Copy owner:", "Copy locale:", "Copy approved on:"):
            self.assertIn(marker, contract)
        self.assertIn("--require-copy-approved", guide)

    def test_ui_gate_presentations_are_visible_complete_and_blocking(self):
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        guide = self.read("references/wireframe-guide.md")
        visual_pass = self.read("references/ui-design-pass.md")

        self.assertLess(
            skill.index("verified absolute Markdown links to the complete interactive"),
            skill.index("Obtain explicit human Wireframe Approval"),
        )
        self.assertIn(
            "verified absolute Markdown links to the complete current HiFi entrypoint",
            skill,
        )
        self.assertIn("every manifest-listed sibling page", skill)
        self.assertIn("affected `ui-design.md` design handoff", skill)
        self.assertIn("complete actual candidate", contract)
        for document in (skill, contract, guide, visual_pass):
            with self.subTest(document=document[:50]):
                self.assertIn("final logical paths in the authorized publication checkout", document)
                self.assertIn("canonical files in the source checkout", document)
                self.assertIn("Do not collect approval on `.ui-staging` paths", document)
                self.assertNotIn("Use staging paths for an unapproved staged draft", document)
        self.assertIn("Wait for the owner's explicit decision before continuing", contract)
        self.assertIn("A changed candidate reopens the affected approval", contract)
        self.assertIn("plain path cannot replace the links", contract)
        self.assertIn("blocks approval readiness", contract)
        self.assertIn("complete interactive current `wireframes.html`", guide)
        self.assertIn("affected `ui-design.md` scope", guide)
        self.assertIn("ask explicitly for Wireframe Approval", guide)
        self.assertIn("every manifest-listed sibling page", visual_pass)
        self.assertIn("ask explicitly for Visual Approval", visual_pass)

    def test_output_contract_keeps_tokens_after_visual_approval(self):
        skill = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")
        self.assertLess(
            skill.index("Human Visual Approval"),
            skill.index("Run the **Design System Need Gate** only after"),
        )
        self.assertIn("Design author: frontend-design", contract)
        self.assertIn("Direction decision owner:", contract)
        self.assertIn("Impeccable critique:", contract)
        self.assertIn("Impeccable audit:", contract)
        self.assertIn("Wireframe score:", contract)
        self.assertIn("HiFi score:", contract)
        self.assertIn("H2 score:", contract)
        self.assertIn("H4 score:", contract)
        self.assertIn("H5 score:", contract)
        self.assertIn("H7 score:", contract)
        self.assertIn("H8 score:", contract)
        self.assertIn("H9 score:", contract)
        self.assertIn("docs/design/design-system.md", contract)


if __name__ == "__main__":
    unittest.main()

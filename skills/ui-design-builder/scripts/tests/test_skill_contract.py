"""Contract tests for the UI Design Builder skill."""

import shutil
import subprocess
import unittest
import re
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
UI_STAGE = "references/stages/ui-design.md"


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
const html = fs.readFileSync(process.argv[2], "utf8");
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
const canvas = {isConnected: true, scrollWidth: 768, clientWidth: 768, querySelectorAll: () => [], getBoundingClientRect() { return {width: this.clientWidth}; }};
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
canvas.clientWidth = 700;
context.api.runLayoutQa(canvas, shell, panel, ios);
callbacks[2]();
const mismatch = context.window.wireframeQaResults[keys[0]];
if (mismatch.status !== "fail" || !mismatch.canvasWidthMismatch) throw new Error("incorrect product width was accepted");
console.log("hybrid fallback and stale QA assertions completed");
'''
        completed = subprocess.run(
            [node, "-", str(template)],
            input=runner,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("hybrid fallback and stale QA assertions completed", completed.stdout)

    def read(self, relative: str) -> str:
        return (SKILL_ROOT / relative).read_text(encoding="utf-8")

    def test_skill_owns_ui_after_product_approval(self):
        skill = self.read("SKILL.md")
        self.assertIn("name: ui-design-builder", skill)
        self.assertIn("approved Product Definition", skill)
        self.assertIn("docs/design/ui-design.md", skill)
        self.assertIn("ui-design/2", skill)
        self.assertIn("Do not use for product scope, backend architecture", skill)

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

    def test_ui_stage_routing_is_conditional_and_targets_exist(self):
        entry = self.read("SKILL.md")
        stage = self.read(UI_STAGE)
        anchors = self.stage_headings(stage)

        self.assertTrue((SKILL_ROOT / UI_STAGE).is_file())
        for trigger, anchor in (
            ("UI research or authorship", "required-skills-and-inputs"),
            ("directions, HiFi or design repair", "workflow"),
            ("Full initial authoring follows the complete required procedure", "workflow"),
            ("handoff self-review", "author-self-review-before-handoff"),
            ("unresolved visual, motion, reference or platform decisions", "reference-routing"),
        ):
            with self.subTest(trigger=trigger, anchor=anchor):
                self.assertIn(trigger, entry)
                self.assertRegex(entry, rf"\({re.escape(UI_STAGE)}#{anchor}\)")
                self.assertIn(anchor, anchors)

        self.assertIn("approved Product Definition and Stack Decision Checkpoint", entry)
        self.assertIn("Agent configuration designates the UI author", entry)
        self.assertIn("complete pinned `frontend-design`", entry)
        self.assertIn("Enhancements author only added or changed pages", entry)
        self.assertIn("Routine maintenance does not rebuild historical HiFi", entry)
        self.assertIn("one human Visual Approval", entry)
        self.assertIn("## Installed Commands", entry)
        self.assertIn("## Purpose", entry)
        self.assertIn("## Design Lifecycle", entry)
        self.assertIn("## Review And Repair Boundaries", entry)

        missing_anchor = stage.replace("## Reference Routing", "## Optional Guides")
        with self.assertRaises(AssertionError):
            self.assertIn("reference-routing", self.stage_headings(missing_anchor))
        missing_pointer = entry.replace("#reference-routing", "#missing-reference-routing")
        self.assertNotRegex(missing_pointer, rf"\({re.escape(UI_STAGE)}#reference-routing\)")
        self.assertIn("#missing-reference-routing", missing_pointer)

    def test_human_intake_precedes_wireframe_and_style(self):
        stage = self.read(UI_STAGE)
        intake = stage.index("Combine unanswered design, imagery and motion questions into one intake")
        wireframe = stage.index("produce direction studies")
        style = stage.index("author the complete connected `ui-hifi/2` package")
        review = stage.index("Run Impeccable critique/audit under the existing authorization")
        self.assertLess(intake, wireframe)
        self.assertLess(wireframe, style)
        self.assertLess(style, review)
        self.assertIn("Wait for the explicit human decision", stage)

    def test_frontend_design_authors_and_impeccable_reviews(self):
        skill = self.read("SKILL.md")
        stage = self.read(UI_STAGE)
        pass_guide = self.read("references/ui-design-pass.md")
        rubric = self.read("references/ui-grading-rubric.md")
        for content in (skill, stage, pass_guide):
            self.assertIn("`frontend-design`", content)
            self.assertIn("Impeccable", content)
        self.assertIn("one `critique` and one `audit`", stage)
        self.assertIn("single design author", skill)
        self.assertIn("Impeccable", rubric)
        self.assertIn("`H1`–`H9`", pass_guide)

    def test_impeccable_is_required_and_declined_authorization_blocks(self):
        skill = self.read("SKILL.md")
        stage = self.read(UI_STAGE)
        pass_guide = self.read("references/ui-design-pass.md")
        for content in (skill, stage, pass_guide):
            self.assertNotIn("publication gate", content)
            self.assertIn("`blocked`", content)
        self.assertIn("required HiFi quality review", stage)
        self.assertIn("Impeccable critique/audit", skill)

    def test_frontend_design_is_admitted_before_both_authoring_stages(self):
        prompt = self.read("agents/openai.yaml")
        stage = self.read(UI_STAGE)
        wireframe = self.read("references/wireframe-guide.md")
        hifi = self.read("references/ui-design-pass.md")
        binding = (
            'python "<delivery-harness-skill-root>/scripts/check_skill_bindings.py" '
            "--agents-md <target-AGENTS.md> --stage ui-design"
        )

        self.assertLess(prompt.index("$frontend-design"), prompt.index("directions"))
        self.assertIn("actual design author for directions", prompt)
        self.assertIn("Before each authoring stage", prompt)
        for document, authoring_marker in (
            (stage, "produce direction studies"),
            (wireframe, "## Wireframe Validation Gate (wireframes/5)"),
            (hifi, "## Frontend Design Style Integration"),
        ):
            with self.subTest(authoring_marker=authoring_marker):
                self.assertIn(binding, document)
                self.assertLess(document.index(binding), document.index(authoring_marker))

        authoring_contract = "\n".join((stage, wireframe, hifi))
        self.assertIn("actual writer", authoring_contract)
        self.assertIn("parent read", authoring_contract.lower())
        self.assertIn("silently replace the binding", authoring_contract)
        self.assertIn("grants no spawn action", authoring_contract)
        self.assertNotIn("parent may author", authoring_contract)
        for document in (stage, wireframe, hifi):
            self.assertIn("Agent configuration designates", document)
        self.assertIn("shell construction and validation", authoring_contract)

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
            "route `Motion`",
            "route `Three.js`",
            "## HiFi Embedding Limits",
            "never rename, strip or obfuscate library code",
        ):
            self.assertIn(marker, router)
        self.assertIn("Do not add GSAP merely because motion exists", router)

    def test_new_wireframes_use_schema_five_and_keep_legacy_readability(self):
        checker = self.read("scripts/check_wireframe_html.py")
        template = self.read("assets/templates/WIREFRAMES.template.html")
        guide = self.read("references/wireframe-guide.md")
        for content in (checker, template, guide):
            self.assertIn("wireframes/5", content)
        self.assertIn("wireframes/4", checker)
        self.assertIn("wireframes/4", guide)
        self.assertIn("wireframes/3", checker)
        self.assertIn("Higgsfield MCP", template)

    def test_new_wireframe_validation_has_no_human_copy_or_structure_gate(self):
        stage = self.read(UI_STAGE)
        contract = self.read("references/output-contract.md")
        guide = self.read("references/wireframe-guide.md")
        self.assertLess(
            stage.index("run a cheap machine completeness check"),
            stage.index("Present the complete current HiFi entry"),
        )
        for marker in ("UI contract: ui-design/2", "ui-hifi-copy/1", "### Frontend Design Usage"):
            self.assertIn(marker, contract)
        self.assertNotIn("Copy Freeze:", contract)
        self.assertNotIn("## Wireframe Approval", contract)
        self.assertIn("Schema 5 has no human Copy Freeze or Wireframe Approval", guide)
        self.assertIn("--require-copy-approved", guide)

    def test_ui_gate_presentations_are_visible_complete_and_blocking(self):
        skill = self.read("SKILL.md")
        stage = self.read(UI_STAGE)
        contract = self.read("references/output-contract.md")
        visual_pass = self.read("references/ui-design-pass.md")

        self.assertIn("one human Visual Approval", skill)
        self.assertLess(stage.index("run a cheap machine completeness check"), stage.index("Present the complete current HiFi entry"))
        self.assertIn("verified absolute Markdown links", stage)
        self.assertIn("every manifest-listed sibling page", stage)
        self.assertIn("affected `ui-design.md` handoff", stage)
        self.assertIn("complete HiFi candidate", contract)
        for document in (stage, visual_pass):
            with self.subTest(document=document[:50]):
                self.assertIn("final logical paths in the authorized publication checkout", document)
                self.assertTrue("source checkout" in document or "canonical source paths" in document)
                self.assertIn("Do not collect approval on `.ui-staging` paths", document)
                self.assertNotIn("Use staging paths for an unapproved staged draft", document)
        self.assertIn("`stages/ui-design.md#workflow` step 7", contract)
        self.assertIn("at final repository paths on the task branch", contract)
        self.assertIn("never `.ui-staging` paths", contract)
        self.assertIn("Wait for the explicit human decision", stage)
        self.assertIn("a changed candidate reopens the affected decision", contract)
        self.assertIn("plain path cannot replace the links", contract)
        self.assertIn("Missing or stale pages/evidence block readiness", stage)
        self.assertIn("every manifest-listed sibling page", visual_pass)
        self.assertIn("ask explicitly for Visual Approval", visual_pass)

    def test_output_contract_keeps_tokens_after_visual_approval(self):
        stage = self.read(UI_STAGE)
        contract = self.read("references/output-contract.md")
        self.assertLess(stage.index("Request one **Visual Approval**"), stage.index("Apply the **Design System Need Gate** after Visual Approval"))
        self.assertIn("Design author: frontend-design", contract)
        self.assertIn("Direction decision owner:", contract)
        self.assertIn("Impeccable critique:", contract)
        self.assertIn("Impeccable audit:", contract)
        self.assertNotIn("Wireframe score:", contract)
        self.assertIn("HiFi score:", contract)
        self.assertIn("H2 score:", contract)
        self.assertIn("H4 score:", contract)
        self.assertIn("H5 score:", contract)
        self.assertIn("H7 score:", contract)
        self.assertIn("H8 score:", contract)
        self.assertIn("H9 score:", contract)
        self.assertIn("docs/design/design-system.md", contract)

    def test_repair_review_preserves_mandatory_checks_and_current_evidence(self):
        rubric = self.read("references/ui-grading-rubric.md")
        scope = rubric.split("## Repair Re-review Scope", 1)[1]
        self.assertIn("initial diagnostic wave covers the complete approved scope and every First-Wave Audit Axis", scope)
        self.assertIn("Run Impeccable critique and audit again on the affected pages and states", scope)
        self.assertIn("complete required browser matrix on the current candidate", scope)
        self.assertIn("complete current `H1`–`H9` assessment", scope)
        self.assertIn("it never grants another repair round", scope)
        self.assertNotIn("and the full rubric once", rubric)
        self.assertNotIn("expands the affected scope", rubric)
        for source in ("references/ui-design-pass.md", "references/review-workflow.md",
                       "references/review-evidence.md", UI_STAGE):
            with self.subTest(source=source):
                self.assertIn("ui-grading-rubric.md#repair-re-review-scope", self.read(source))

    def test_first_wave_axes_and_scoped_re_review(self):
        rubric = self.read("references/ui-grading-rubric.md")
        axes = rubric.split("## First-Wave Audit Axes", 1)[1].split("\n## ", 1)[0]
        for axis in ("320 CSS px reflow", "each theme in scope", "200%", "`clamp()`", "forced colors",
                     "keyboard-only use", "accessible names", "placeholders", "live regions", "reduced motion"):
            with self.subTest(axis=axis):
                self.assertIn(axis, axes)
        self.assertIn("A re-review adds no axis", axes)
        scope = rubric.split("## Repair Re-review Scope", 1)[1]
        self.assertIn("A copy or metadata repair changes only", scope)
        self.assertIn("Every other repair is a visual repair", scope)
        self.assertIn("goes into the ledger as a next-round advisory", scope)
        for block in ("a PRD contradiction", "a dead control", "an inaccessible required flow",
                      "overlaps, clips or is unreachable"):
            self.assertIn(block, scope)
        self.assertIn("Impeccable severity alone does not decide readiness", rubric)
        contract = self.read("references/output-contract.md")
        self.assertIn("may carry forward into the new receipt with its original capture", contract)
        self.assertIn("names each carried row's source receipt and page SHA-256", contract)
        for source in ("SKILL.md", UI_STAGE):
            self.assertIn("ui-grading-rubric.md#first-wave-audit-axes", self.read(source))

    def test_default_review_staffing_and_grader_packet(self):
        rubric = self.read("references/ui-grading-rubric.md")
        self.assertIn("the wave has two fresh reviewers: a lead grader who also produces the browser receipt, "
                      "and one Impeccable operator who runs critique and audit", rubric)
        self.assertIn("Neither reviews its own work", rubric)
        self.assertIn("Add one only on an owner request or a recorded high risk", rubric)
        self.assertIn("A grader packet carries this rubric", rubric)
        self.assertIn("the Impeccable operator produces the critique and audit receipts",
                      self.read("references/review-evidence.md"))

    def test_bindings_and_frontend_design_read_are_per_session(self):
        stage = self.read(UI_STAGE)
        self.assertIn("Before a repair, rerun it only when a bound skill's tree hash changed in this session", stage)
        self.assertIn("document-sync-contract.md#same-session-source-reading-reuse", stage)
        sync = (SKILL_ROOT.parent / "delivery-harness/references/document-sync-contract.md").read_text(encoding="utf-8")
        self.assertIn("same-session-source-reading-reuse", self.stage_headings(sync))
        for source in ("references/ui-design-pass.md", "references/review-workflow.md"):
            with self.subTest(source=source):
                self.assertIn("stages/ui-design.md#required-skills-and-inputs", self.read(source))
                self.assertNotIn("or any repair, run", self.read(source))

    def test_direction_modification_is_one_revised_study(self):
        pass_guide = self.read("references/ui-design-pass.md")
        contract = self.read("references/output-contract.md")
        self.assertIn("A mix or modification produces one revised study of the selected direction", pass_guide)
        self.assertIn("A rejection starts a complete new set", pass_guide)
        self.assertIn("adds one revised study of the selected direction to the same round folder", contract)
        for document in (pass_guide, contract):
            self.assertNotIn("complete revised direction set", document)
            self.assertNotIn("renewed complete study set", document)

    def test_only_final_candidate_evidence_is_committed(self):
        evidence = self.read("references/review-evidence.md")
        self.assertIn("Only the final candidate's receipts and the captures they cite", evidence)
        self.assertIn("Do not commit evidence of earlier attempts", evidence)


if __name__ == "__main__":
    unittest.main()

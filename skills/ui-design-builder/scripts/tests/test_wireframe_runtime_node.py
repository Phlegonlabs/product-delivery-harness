"""Executable DOM smoke test for the canonical overlay runtime."""

from __future__ import annotations

import shutil
import re
import subprocess
import unittest
from pathlib import Path


class WireframeRuntimeNodeTests(unittest.TestCase):
    def test_product_width_is_not_reduced_by_reviewer_frame(self) -> None:
        template = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"
        html = template.read_text(encoding="utf-8")
        frame = re.search(r"\.canvas-shell\s*\{([^}]+)\}", html).group(1)
        self.assertRegex(frame, r"padding:\s*0;")
        self.assertRegex(frame, r"border:\s*0;")
        self.assertIn("const actualCanvasWidth = canvas.getBoundingClientRect().width", html)
        self.assertNotRegex(html, r"\.sidebar\s*\{\s*position:\s*static")
        self.assertIn('.copy-item[data-copy-role="media placeholder"]', html)

    def test_node_stdin_reports_failures_after_the_first_line(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is unavailable")
        result = subprocess.run([node, "-"], input='console.log("started");\nthrow Error("late assertion reached");',
                                capture_output=True, text=True, timeout=15)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("late assertion reached", result.stderr)

    def test_primary_page_default_preserves_explicit_review_links(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is unavailable")
        template = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"
        script = r'''
const fs = require("fs"), vm = require("vm");
const html = fs.readFileSync(process.argv[2], "utf8").replace(/\r\n/g, "\n");
const source = html.match(/const resolvePage = [\s\S]*?\n      const initialPage/)[0].replace(/\n\s*const initialPage$/, "");
const context = {data:{screens:[{id:"UI-001"},{id:"UI-002"}]}};
vm.runInNewContext(source + "\nthis.resolve = resolvePage;", context);
for (const [hash, expected] of [["","UI-001"],["#unknown","UI-001"],["#UI-002","UI-002"],["#overview","overview"],["#design-system","design-system"]]) {
  if (context.resolve(hash) !== expected) throw Error(`Wrong page for ${hash}`);
}
if (!html.includes("state.page = resolvePage(location.hash)")) throw Error("hashchange bypasses shared routing");
'''
        result = subprocess.run([node, "-", str(template)], input=script, capture_output=True, text=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_composition_runtime_uses_semantic_content_without_losing_copy(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is unavailable")
        template = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"
        script = r'''
const fs = require("fs");
const vm = require("vm");
const html = fs.readFileSync(process.argv[2], "utf8").replace(/\r\n/g, "\n");
const source = html.match(/const renderRegionContent = [\s\S]*?\n      const flowTarget/)[0].replace(/\n\s*const flowTarget$/, "");
class Node {
  constructor(tag, cls, text) { this.tag = tag; this.cls = cls; this.text = text; this.children = []; this.attrs = {}; this.dataset = {}; this.style = {setProperty(){}}; this.events = {}; }
  append(...items) { this.children.push(...items); }
  setAttribute(key, value) { this.attrs[key] = value; }
  querySelector(tag) { return this.children.find(child => child.tag === tag); }
  addEventListener(name, callback) { this.events[name] = callback; }
}
const context = {
  element: (tag, cls, text) => new Node(tag, cls, text),
  copyRole: item => item.role,
  copyText: item => item.text,
  renderCopyItem: item => new Node("div", "copy-item", item.text),
};
vm.runInNewContext(source + "\nthis.render = renderRegionContent;", context);
const item = (role, text) => ({role, text});
const root = () => new Node("div");
let parent = root();
context.render(parent, {presentation:"table", elements:[item("table header", "Name"), item("table header", "Status"), item("table cell", "Alpha"), item("table cell", "Ready"), item("table cell", "Beta"), item("table cell", "Waiting")]});
const table = parent.children[0];
if (table.tag !== "table" || table.children[0].tag !== "thead" || table.children[1].children.length !== 2) throw Error("table lost semantic rows");
if (table.children[0].children[0].children[0].attrs.scope !== "col") throw Error("column header lost scope");
if (table.children[1].children[1].children[1].children[0].text !== "Waiting") throw Error("table reordered copy");
parent = root();
context.render(parent, {presentation:"form", elements:[item("field label", "Workspace"),item("field value", "<script>literal</script>")]});
const label = parent.children[0], input = label.children[1];
if (label.tag !== "label" || input.tag !== "input" || input.value !== "<script>literal</script>" || input.readOnly || !input.events.input) throw Error("field lost label, literal value, or editable local binding");
parent = root();
context.render(parent, {presentation:"list", elements:[item("section heading", "Pending"), item("list item", "Review"), item("list item", "Approve")]});
if (parent.children[1].tag !== "ul" || parent.children[1].children.length !== 2 || parent.children[1].children[0].tag !== "li") throw Error("list lost semantic items");
parent = root();
context.render(parent, {elements:[item("body", "Legacy content")]});
if (parent.children[0].text !== "Legacy content") throw Error("legacy content lost");
let followed = null;
context.actionLabel = item => item.label;
context.outgoingFlow = (screen, label) => ({from:screen, trigger:label});
context.runFlow = flow => { followed = flow; };
context.renderRegionContent = context.render;
vm.runInNewContext(html.match(/const appendActions = [\s\S]*?\n      const setInspectorOpen/)[0].replace(/\n\s*const setInspectorOpen$/, "") + "\nthis.region = renderRegion;", context);
const region = {id:"projects", presentation:"table", elements:[item("table header","Name"),item("table cell","Stale project")], actions:[{label:"Refresh"},{label:"Help"}], primaryAction:"Refresh"};
const result = context.region("UI-001", region, {treatments:{projects:{copy:[item("empty status","No projects")]}}}, {spans:{projects:12}}, false);
const content = result.children[1];
if (content.children.some(child => child.tag === "table")) throw Error("empty state retained stale table");
if (content.children.at(-1).children[0].text !== "No projects") throw Error("empty state copy lost");
const actions = content.children[0].children;
if (actions[0].dataset.emphasis !== "primary" || actions[1].dataset.emphasis !== "secondary") throw Error("explicit action priority lost");
actions[0].events.click({stopPropagation(){}});
if (followed.from !== "UI-001" || followed.trigger !== "Refresh") throw Error("action flow changed");
let toggleClick, renders = 0, closed = 0;
context.document = {body:{dataset:{}}};
context.annotationToggle = {addEventListener(name, fn){ toggleClick = fn; },setAttribute(name,value){this[name]=value;},focus(){this.focused=true;}};
context.currentScreen = () => ({id:"UI-001"});
context.renderScreen = () => {renders++;};
context.setInspectorOpen = () => {closed++;};
vm.runInNewContext(html.match(/annotationToggle.addEventListener\("click", [\s\S]*?\n      \}\);/)[0], context);
toggleClick();
if (context.document.body.dataset.annotations !== "true" || context.annotationToggle["aria-pressed"] !== "true") throw Error("annotations did not enable");
toggleClick();
if (context.document.body.dataset.annotations !== "false" || renders !== 2 || closed !== 1) throw Error("annotations did not disable and refresh QA");
if (!context.annotationToggle.focused) throw Error("annotation toggle lost keyboard focus");
'''
        result = subprocess.run([node, "-", str(template)], input=script, capture_output=True, text=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_open_flow_dialog_binds_cross_class_width_and_state(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is unavailable")
        template = (
            Path(__file__).resolve().parents[2] / "assets" / "templates" / "WIREFRAMES.template.html"
        )
        script = r'''
const fs = require("fs");
const vm = require("vm");
const html = fs.readFileSync(process.argv[2], "utf8").replace(/\r\n/g, "\n");
const match = html.match(/const openFlowDialog = \(flow\) => \{[\s\S]*?\n      \};\n\n      const runFlow/);
if (!match) throw new Error("openFlowDialog was not found in the canonical template");
class Node {
  constructor(tag, className, text) { this.tagName = tag; this.className = className; this.textContent = text || ""; this.children = []; this.style = {}; this.attributes = {}; this.dataset = {}; this.open = false; }
  append(...items) { this.children.push(...items.filter(Boolean)); }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  addEventListener() {}
  showModal() { this.open = true; }
  close() { this.open = false; }
  remove() { this.removed = true; }
}
const body = new Node("body", "", "");
const context = {
  console,
  data: { screens: [{ id: "UI-002", name: "Native screen", goal: "Native task", responsiveLayouts: { compact: { columns: 2, hidden: [] } }, states: [{ id: "loading" }], regions: [{ id: "region" }] }] },
  state: { responsiveTarget: "compact" },
  element: (tag, className, text) => new Node(tag, className, text),
  responsiveSpecFor: () => ({ kind: "sizeClasses", targets: ["compact"], canvasWidths: { compact: 1200 } }),
  targetFor: () => "compact",
  regionOrder: () => [{ id: "region" }],
  renderRegion: () => new Node("section", "region", "content"),
  document: { body },
};
vm.runInNewContext(match[0].replace(/\n\s*const runFlow[\s\S]*$/, "") + "\nthis.openFlowDialog = openFlowDialog;", context);
context.openFlowDialog({ to: "UI-002" });
if (body.children.length !== 1) throw new Error("overlay dialog was not appended");
const dialog = body.children[0];
if (dialog.className !== "flow-dialog" || !dialog.open) throw new Error("overlay dialog is not open");
const canvas = dialog.children[0].children.find((item) => item.className === "wireframe");
if (!canvas || canvas.style.width !== "1200px" || canvas.style.maxWidth !== "none") throw new Error("overlay width did not use the target class");
if (dialog.style.width !== "min(calc(100vw - 32px), 1242px)" || dialog.style.maxWidth !== "calc(100vw - 32px)") throw new Error("overlay dialog did not fit the selected canvas plus body padding");
if (!String(canvas.attributes["aria-label"]).includes("compact") || !String(canvas.attributes["aria-label"]).includes("loading")) throw new Error("overlay state/class context is stale");
'''
        result = subprocess.run(
            [node, "-", str(template)],
            input=script,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_local_search_controls_filter_rows_and_render_declared_states(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is unavailable")
        template = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"
        script = r'''
const fs = require("fs"), vm = require("vm");
const html = fs.readFileSync(process.argv[2], "utf8").replace(/\r\n/g, "\n");
const helper = html.match(/const localSearchConfigFor = [\s\S]*?\n      \/\/ Presentation uses existing copy records/)[0]
  .replace(/\n\s*\/\/ Presentation uses existing copy records$/, "");
const results = html.match(/const renderLocalSearchResults = [\s\S]*?\n      const flowTarget/)[0]
  .replace(/\n\s*const flowTarget$/, "");
const actions = html.match(/const appendActions = [\s\S]*?\n      const setInspectorOpen/)[0]
  .replace(/\n\s*const setInspectorOpen$/, "");
class Node {
  constructor(tag, cls, text) {
    this.tag = tag; this.className = cls || ""; this.textContent = text || "";
    this.children = []; this.attrs = {}; this.dataset = {}; this.events = {};
    this.style = {setProperty(){}}; this.value = ""; this.type = ""; this.focused = false;
  }
  append(...items) { this.children.push(...items.filter(Boolean)); }
  setAttribute(key, value) { this.attrs[key] = String(value); if (key.startsWith("data-")) this.dataset[key.slice(5)] = String(value); }
  addEventListener(name, callback) { this.events[name] = callback; }
  focus() { this.focused = true; }
  querySelector(selector) {
    if (selector.includes("data-local-search-query")) return this.query;
    return null;
  }
}
const item = (role, text) => ({kind:"static", role, text, status:"approved", source:"test"});
const dynamic = (text) => ({kind:"dynamic", role:"list item", example:text, status:"approved", source:"test", contract:{source:"test", order:"curated", format:"title", count:"bounded", length:"short", fallback:"No result"}});
const config = {
  formRegion:"search-form", resultsRegion:"search-results",
  queryLabel:item("field label", "Search"), languageLabel:item("field label", "Language"),
  languageOptions:[{value:"all",copy:item("select option", "All languages")},{value:"en",copy:item("select option", "English")},{value:"zh-Hant",copy:item("select option", "Traditional Chinese")}],
  submitAction:"Search", clearAction:"Clear", states:{initial:"ready",results:"results",empty:"no-results"},
  items:[{language:"en",copy:dynamic("Welcome guide"),searchText:"Welcome guide account"},{language:"zh-Hant",copy:dynamic("使用指南"),searchText:"使用指南帳戶"}]
};
const screen = {id:"UI-001", localSearch:config};
const resultState = {id:"results", treatments:{"search-results":{copy:[item("result count", "Matching results")]}}};
const emptyState = {id:"no-results", treatments:{"search-results":{copy:[item("empty state", "No matching results")]}}};
const content = new Node("main");
let currentInput = null, renders = 0, followed = null;
const context = {
  data:{screens:[screen]}, state:{page:"UI-001", localSearch:Object.create(null), fieldValues:Object.create(null), screenState:"ready", screenStates:{}},
  content, element:(tag, cls, text) => new Node(tag, cls, text),
  copyRole:value => value.role, copyText:value => value.text || value.example || value.label || "",
  actionLabel:value => value.label || value,
  renderCopyItem:value => new Node("span", "copy-item", value.text || value.example),
  renderStateControls:() => {}, renderScreen:() => { renders += 1; },
  outgoingFlow:() => ({from:"UI-001", trigger:"flow"}), runFlow:flow => { followed = flow; },
};
content.querySelector = () => currentInput;
vm.runInNewContext(helper + "\n" + results + "\n" + actions + "\nthis.controls = renderLocalSearchControls; this.results = renderLocalSearchResults; this.append = appendActions; this.reset = resetLocalSearch;", context);
const controlsRoot = new Node("div");
context.controls(controlsRoot, "UI-001", config);
const controls = controlsRoot.children[0];
const queryInput = controls.children[0].children[1];
const languageSelect = controls.children[1].children[1];
currentInput = queryInput;
queryInput.value = "guide";
queryInput.events.input();
let prevented = false;
queryInput.events.keydown({key:"Enter", preventDefault(){prevented = true;}});
if (!prevented || context.state.screenState !== "results" || renders !== 1 || !queryInput.focused) throw Error("Enter did not submit local search or preserve focus");
languageSelect.value = "zh-Hant";
languageSelect.events.change();
if (context.state.screenState !== "no-results") throw Error("language change did not filter to empty state");
const resultRoot = new Node("div");
context.results(resultRoot, {id:"search-results", presentation:"list", elements:[item("section heading", "Results"), item("list item", "stale baseline")]}, "UI-001", config, resultState, "results");
const renderedList = resultRoot.children.find(child => child.className.includes("local-search-results"));
if (!renderedList || renderedList.children.length !== 0) throw Error("result state rendered rows for the wrong language");
context.state.localSearch["UI-001"].query = "guide";
context.state.localSearch["UI-001"].language = "all";
const matchingRoot = new Node("div");
context.results(matchingRoot, {id:"search-results", presentation:"list", elements:[item("section heading", "Results"), item("list item", "stale baseline")]}, "UI-001", config, resultState, "results");
const matchingList = matchingRoot.children.find(child => child.className.includes("local-search-results"));
if (!matchingList || matchingList.children.length !== 1 || matchingList.children[0].children[0].textContent !== "Welcome guide") throw Error("matching result row was not rendered");
const emptyRoot = new Node("div");
context.results(emptyRoot, {id:"search-results", presentation:"list", elements:[item("section heading", "Results"), item("list item", "stale baseline")]}, "UI-001", config, emptyState, "empty");
if (!emptyRoot.children.some(child => child.textContent === "No matching results")) throw Error("declared empty copy was not rendered");
const actionRoot = new Node("div");
context.append(actionRoot, "UI-001", [{label:"Search"},{label:"Clear"}], "Search", config);
const actionList = actionRoot.children[0];
actionList.children[0].events.click({stopPropagation(){}});
if (followed !== null) throw Error("local Search fell through to a page flow");
actionList.children[1].events.click({stopPropagation(){}});
if (context.state.screenState !== "ready" || context.state.localSearch["UI-001"].query !== "") throw Error("local Clear did not reset initial state");
'''
        result = subprocess.run([node, "-", str(template)], input=script, capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_editable_form_values_survive_re_render(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is unavailable")
        template = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"
        script = r'''
const fs = require("fs"), vm = require("vm");
const html = fs.readFileSync(process.argv[2], "utf8").replace(/\r\n/g, "\n");
const source = html.match(/const renderRegionContent = [\s\S]*?\n      const flowTarget/)[0].replace(/\n\s*const flowTarget$/, "");
class Node {
  constructor(tag, cls, text) { this.tag = tag; this.className = cls || ""; this.text = text || ""; this.children = []; this.attrs = {}; this.dataset = {}; this.events = {}; this.value = ""; }
  append(...items) { this.children.push(...items.filter(Boolean)); }
  setAttribute(key, value) { this.attrs[key] = value; }
  addEventListener(name, callback) { this.events[name] = callback; }
}
const context = {
  state: {fieldValues: Object.create(null)},
  element: (tag, cls, text) => new Node(tag, cls, text),
  copyRole: item => item.role,
  copyText: item => item.text,
  renderCopyItem: item => new Node("span", "copy-item", item.text),
};
vm.runInNewContext(source + "\nthis.render = renderRegionContent;", context);
const region = {id:"settings", presentation:"form", elements:[{role:"field label", text:"Workspace"},{role:"field value", text:"Studio"}]};
const first = new Node("div");
context.render(first, region);
const firstInput = first.children[0].children[1];
if (firstInput.value !== "Studio") throw Error("initial form value missing");
firstInput.value = "Edited locally";
firstInput.events.input();
const second = new Node("div");
context.render(second, region);
if (second.children[0].children[1].value !== "Edited locally") throw Error("form value was not retained");
'''
        result = subprocess.run([node, "-", str(template)], input=script, capture_output=True, text=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_page_switch_retains_valid_target_and_page_state(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is unavailable")
        template = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"
        script = r'''
const fs = require("fs"), vm = require("vm");
const html = fs.readFileSync(process.argv[2], "utf8").replace(/\r\n/g, "\n");
const match = html.match(/const selectPage = \(page\) => \{[\s\S]*?\n      \};\n\n      const makePageButton/);
if (!match) throw Error("selectPage was not found");
const screens = [
  {id:"UI-001", states:[{id:"ready"}], responsive:{targets:["390","768","1200"]}},
  {id:"UI-002", states:[{id:"ready"},{id:"empty"}], responsive:{targets:["390","768","1200"]}},
];
const context = {
  state:{page:"UI-001", responsiveTarget:"768", screenState:"ready", screenStates:{"UI-002":"empty"}, selectedRegion:"R1", inspectorOpen:true},
  currentScreen:() => screens.find(screen => screen.id === context.state.page),
  responsiveSpecFor:screen => screen.responsive,
  location:{hash:"#UI-001"},
  render:() => {},
  content:{focus:() => {}}
};
vm.runInNewContext(match[0].replace(/\n\s*const makePageButton[\s\S]*$/, "") + "\nthis.select = selectPage;", context);
context.select("UI-002");
if (context.state.responsiveTarget !== "768") throw Error("valid target was reset on page switch");
if (context.state.screenState !== "empty") throw Error("page state was not retained");
'''
        result = subprocess.run([node, "-", str(template)], input=script, capture_output=True, text=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()

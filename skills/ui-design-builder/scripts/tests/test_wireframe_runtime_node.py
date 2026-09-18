"""Executable DOM smoke test for the canonical overlay runtime."""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path


class WireframeRuntimeNodeTests(unittest.TestCase):
    def test_composition_runtime_uses_semantic_content_without_losing_copy(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is unavailable")
        template = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"
        script = r'''
const fs = require("fs");
const vm = require("vm");
const html = fs.readFileSync(process.argv[1], "utf8");
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
if (label.tag !== "label" || input.tag !== "input" || input.value !== "<script>literal</script>" || !input.readOnly) throw Error("field lost label, literal value, or read-only boundary");
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
        result = subprocess.run([node, "-e", script, str(template)], capture_output=True, text=True, timeout=15)
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
const html = fs.readFileSync(process.argv[1], "utf8");
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
  responsiveSpecFor: () => ({ kind: "sizeClasses", targets: ["compact"], canvasWidths: { compact: 640 } }),
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
if (!canvas || canvas.style.maxWidth !== "640px") throw new Error("overlay width did not use the target class");
if (!String(canvas.attributes["aria-label"]).includes("compact") || !String(canvas.attributes["aria-label"]).includes("loading")) throw new Error("overlay state/class context is stale");
'''
        result = subprocess.run(
            [node, "-e", script, str(template)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()

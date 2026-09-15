"""Executable DOM smoke test for the canonical overlay runtime."""

from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path


class WireframeRuntimeNodeTests(unittest.TestCase):
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

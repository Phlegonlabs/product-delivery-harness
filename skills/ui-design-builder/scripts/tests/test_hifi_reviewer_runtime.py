"""Node smoke tests for the reusable inline HiFi reviewer runtime."""

from __future__ import annotations

import shutil
import subprocess
import base64
import os
import unittest
from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[2] / "assets/templates/HIFI_REVIEWER.template.html"


class HiFiReviewerRuntimeTests(unittest.TestCase):
    def test_template_uses_exact_width_container_queries_without_scaling(self) -> None:
        self.assertTrue(TEMPLATE.is_file(), "reusable HiFi reviewer template is missing")
        html = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('data-hifi-canvas', html)
        self.assertIn("container-type:inline-size", html)
        self.assertIn("@container", html)
        self.assertIn('width:390px', html)
        self.assertIn('width:768px', html)
        self.assertIn('width:1200px', html)
        self.assertNotIn("@media", html)
        self.assertNotIn("transform:scale", html.replace(" ", "").lower())
        self.assertNotIn("<iframe", html.lower())
        self.assertNotIn("fetch(", html)

    def test_runtime_keeps_target_and_product_values_across_navigation(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is unavailable")
        html = TEMPLATE.read_text(encoding="utf-8")
        source = html.split('<script id="hifi-reviewer-runtime">', 1)[1].split("</script>", 1)[0]
        source_b64 = base64.b64encode(source.encode("utf-8")).decode("ascii")
        script = r'''
const vm = require("vm");
const storage = new Map();
const input = {value: "Retained project", selected: false};
const selected = {value: "settings", selected: true};
const context = {
  window: {},
  sessionStorage: {
    getItem: key => storage.has(key) ? storage.get(key) : null,
    setItem: (key, value) => storage.set(key, String(value)),
  },
};
vm.runInNewContext(Buffer.from(process.env.HIFI_RUNTIME_SOURCE_B64, "base64").toString("utf8"), context);
const runtime = context.window.createHifiReviewerRuntime({
  storage: context.sessionStorage,
  pages: ["index.html", "details.html"],
  targets: ["390", "768", "1200"],
});
runtime.selectTarget("768");
runtime.openView("overview");
if (runtime.snapshot().target !== "768" || runtime.snapshot().view !== "overview") throw Error("review switch lost state");
runtime.showProduct();
runtime.setPage("details.html");
const snapshot = runtime.snapshot();
if (snapshot.page !== "details.html" || snapshot.target !== "768" || snapshot.view !== "product") throw Error("navigation lost retained review state");
runtime.selectTarget("390");
if (input.value !== "Retained project" || selected.value !== "settings") throw Error("runtime touched product values");
if (runtime.snapshot().target !== "390" || storage.get("hifi-reviewer:target") !== "390") throw Error("target was not persisted");
let rejected = false;
try { runtime.selectTarget("999"); } catch (_) { rejected = true; }
if (!rejected) throw Error("unknown target was accepted");
'''
        runtime_env = dict(os.environ, HIFI_RUNTIME_SOURCE_B64=source_b64)
        result = subprocess.run([node, "-"], input=script, capture_output=True, text=True, timeout=15, env=runtime_env)
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_connected_runtime_applies_target_and_surface_selection_without_storage(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is unavailable")
        html = TEMPLATE.read_text(encoding="utf-8")
        source = html.split('<script id="hifi-reviewer-runtime">', 1)[1].split("</script>", 1)[0]
        source_b64 = base64.b64encode(source.encode("utf-8")).decode("ascii")
        script = r'''
const vm = require("vm");
class Node {
  constructor(tag, attrs = {}) {
    this.tagName = tag.toUpperCase(); this.attrs = {...attrs}; this.dataset = {};
    for (const [key, value] of Object.entries(attrs)) if (key.startsWith("data-")) this.dataset[key.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = value;
    this.hidden = false; this.listeners = {}; this.children = []; this.parentNode = null;
  }
  append(child) { child.parentNode = this; this.children.push(child); return child; }
  setAttribute(name, value) { this.attrs[name] = String(value); if (name.startsWith("data-")) this.dataset[name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = String(value); }
  getAttribute(name) { return Object.prototype.hasOwnProperty.call(this.attrs, name) ? this.attrs[name] : null; }
  removeAttribute(name) { delete this.attrs[name]; if (name.startsWith("data-")) delete this.dataset[name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())]; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  click() { if (this.listeners.click) this.listeners.click({target: this}); }
  focus() { this.focused = true; }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  querySelectorAll(selector) {
    const result = [];
    const visit = node => { for (const child of node.children) { if (matches(child, selector)) result.push(child); visit(child); } };
    visit(this); return result;
  }
}
function matches(node, selector) {
  if (selector === "[data-hifi-canvas]") return node.attrs["data-hifi-canvas"] !== undefined;
  if (selector === "[data-ui-surface]") return node.attrs["data-ui-surface"] !== undefined;
  if (selector === "[data-hifi-panel]") return node.attrs["data-hifi-panel"] !== undefined;
  if (selector === "[data-hifi-target-control]") return node.attrs["data-hifi-target-control"] !== undefined;
  if (selector === "[data-hifi-state-coverage]") return node.attrs["data-hifi-state-coverage"] !== undefined;
  if (selector === "[data-hifi-page-nav] a") return node.tagName === "A" && node.parentNode && node.parentNode.attrs["data-hifi-page-nav"] !== undefined;
  return false;
}
const root = new Node("document");
root.body = new Node("body", {"data-hifi-default-surface": "UI-001"}); root.append(root.body);
const shell = root.body.append(new Node("aside", {"data-hifi-reviewer-shell": "", "data-hifi-reviewer-version": "2"}));
const nav = shell.append(new Node("nav", {"data-hifi-page-nav": ""}));
nav.append(new Node("a", {href: "index.html"})); nav.append(new Node("a", {href: "details.html"}));
const overview = shell.append(new Node("a", {"data-hifi-review-view": "overview", href: "index.html#overview"}));
const tokens = shell.append(new Node("a", {"data-hifi-review-view": "design-tokens", href: "index.html#design-tokens"}));
const fieldset = shell.append(new Node("fieldset", {"data-hifi-responsive-controls": ""}));
const target390 = fieldset.append(new Node("button", {"data-hifi-target-control": "390", "aria-pressed": "true"}));
const target768 = fieldset.append(new Node("button", {"data-hifi-target-control": "768", "aria-pressed": "false"}));
const canvas = root.body.append(new Node("div", {"data-hifi-canvas": "", "data-hifi-targets": "390 768", "data-hifi-target": "390"}));
const surface1 = canvas.append(new Node("main", {"data-ui-surface": "UI-001"})); surface1.append(new Node("h1"));
const surface2 = canvas.append(new Node("main", {"data-ui-surface": "UI-015"})); surface2.append(new Node("h1"));
const panelOverview = root.body.append(new Node("section", {"data-hifi-panel": "overview"})); panelOverview.append(new Node("h1"));
const panelTokens = root.body.append(new Node("section", {"data-hifi-panel": "design-tokens"})); panelTokens.append(new Node("h1"));
root.readyState = "complete";
const throwingStorage = {getItem() { throw Error("file storage blocked"); }, setItem() { throw Error("file storage blocked"); }};
const context = {
  window: {location: {pathname: "/index.html", hash: ""}, addEventListener() {}},
  document: root,
};
vm.runInNewContext(Buffer.from(process.env.HIFI_RUNTIME_SOURCE_B64, "base64").toString("utf8"), context);
const runtime = context.window.connectHifiReviewer({root, storage: throwingStorage});
if (runtime.snapshot().target !== "390" || canvas.dataset.hifiTarget !== "390") throw Error("initial target was not applied");
if (surface1.hidden || !surface2.hidden) throw Error("initial product surface visibility is not exclusive");
runtime.openView("overview");
if (!canvas.hidden || !surface1.hidden || panelOverview.hidden || !panelTokens.hidden) throw Error("openView did not apply panel visibility");
runtime.showProduct();
if (canvas.hidden || surface1.hidden || !panelOverview.hidden) throw Error("showProduct did not restore product visibility");
target768.click();
if (runtime.snapshot().target !== "768" || canvas.dataset.hifiTarget !== "768" || target768.getAttribute("aria-pressed") !== "true") throw Error("target click did not apply to canvas");
runtime.selectSurface("UI-015");
if (surface1.hidden !== true || surface2.hidden !== false) throw Error("surface selection did not apply to DOM");
let rejected = false; try { runtime.selectSurface("unknown"); } catch (_) { rejected = true; }
if (!rejected) throw Error("unknown surface was accepted");
'''
        runtime_env = dict(os.environ, HIFI_RUNTIME_SOURCE_B64=source_b64)
        result = subprocess.run([node, "-"], input=script, capture_output=True, text=True, timeout=15, env=runtime_env)
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_runtime_falls_back_to_destination_page_target_family(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is unavailable")
        html = TEMPLATE.read_text(encoding="utf-8")
        source = html.split('<script id="hifi-reviewer-runtime">', 1)[1].split("</script>", 1)[0]
        source_b64 = base64.b64encode(source.encode("utf-8")).decode("ascii")
        script = r'''
const vm = require("vm");
const storage = new Map();
const context = {window: {}};
vm.runInNewContext(Buffer.from(process.env.HIFI_RUNTIME_SOURCE_B64, "base64").toString("utf8"), context);
const runtime = context.window.createHifiReviewerRuntime({
  storage: {getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, String(value))},
  pages: ["index.html", "ios.html"],
  targets: ["390", "768", "1200", "compact", "regular"],
  targetsByPage: {"index.html": ["390", "768", "1200"], "ios.html": ["compact", "regular"]},
  page: "index.html",
});
runtime.selectTarget("768");
runtime.setPage("ios.html");
if (runtime.snapshot().target !== "compact") throw Error("destination did not fall back to its first target");
let rejected = false; try { runtime.selectTarget("768"); } catch (_) { rejected = true; }
if (!rejected) throw Error("destination accepted a target from another family");
runtime.setPage("index.html");
if (runtime.snapshot().target !== "390" || storage.get("hifi-reviewer:target") !== "390") throw Error("return navigation did not restore a valid web target");
'''
        runtime_env = dict(os.environ, HIFI_RUNTIME_SOURCE_B64=source_b64)
        result = subprocess.run([node, "-"], input=script, capture_output=True, text=True, timeout=15, env=runtime_env)
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()

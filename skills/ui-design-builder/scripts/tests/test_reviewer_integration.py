"""Focused tests for wireframes/5, reviewer v3, controls and assembly."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import assemble_ui_review
import hifi_reviewer
import reviewer_shell
from hifi_review_fixture import add_shell, _source_html
from test_wireframe_contract import render_html, validate_html, wireframe_data


WIREFRAME_V5 = SCRIPTS_DIR.parents[0] / "assets/templates/WIREFRAMES.template.html"
HIFI_TEMPLATE = SCRIPTS_DIR.parents[0] / "assets/templates/HIFI_REVIEWER.template.html"


def schema5_data():
    data = wireframe_data()
    data["schema"] = "wireframes/5"
    data["structureStatus"] = "validated"
    data["copyInventory"] = {"locale": "en-US"}
    data.pop("approvalStatus")
    data.pop("copyFreeze")
    controls = {}
    for screen in data["screens"]:
        for region in screen["regions"]:
            for action in region["actions"]:
                action["id"] = re.sub(r"[^a-z0-9]+", "-", action["label"].lower()).strip("-")
                controls[(screen["id"], action["label"])] = action["id"]
    for flow in data["flows"]:
        flow["sourceState"] = "ready"
        flow["control"] = controls[(flow["from"], flow["trigger"])]
        if flow["presentation"] == "feedback":
            flow["to"] = flow["feedback"]["text"]
            destination_surface = flow["from"]
        else:
            destination_surface = flow["to"]
        flow["destination"] = {"surface": destination_surface, "state": "ready"}
    return data


class WireframeSchema5Tests(unittest.TestCase):
    def test_schema5_validated_template_and_strict_flag_pass(self):
        self.assertEqual([], validate_html(render_html(schema5_data())))
        self.assertEqual(
            [],
            validate_html(
                render_html(schema5_data()),
                require_filled=True,
                require_structure_validated=True,
            ),
        )

    def test_schema5_draft_is_not_structure_validated(self):
        data = schema5_data()
        data["structureStatus"] = "draft"
        problems = validate_html(
            render_html(data), require_structure_validated=True
        )
        self.assertIn("wireframe-data.structureStatus: must be 'validated'", problems)

    def test_schema5_rejects_v4_human_fields_and_bad_locale(self):
        for key, value in (
            ("approvalStatus", "approved"),
            ("copyFreeze", {"status": "approved"}),
        ):
            data = schema5_data()
            data[key] = value
            problems = validate_html(render_html(data))
            self.assertTrue(any(key in problem for problem in problems), problems)
        data = schema5_data()
        data["copyInventory"] = {"locale": "English_US"}
        problems = validate_html(render_html(data))
        self.assertTrue(any("BCP 47" in problem for problem in problems), problems)

    def test_v4_approval_still_uses_historical_shell_and_requires_copy_freeze(self):
        data = wireframe_data()
        self.assertEqual(
            [],
            validate_html(
                render_html(data),
                require_filled=True,
                require_copy_approved=True,
                require_approved=True,
            ),
        )
        data["copyFreeze"]["status"] = "draft"
        problems = validate_html(
            render_html(data), require_copy_approved=True
        )
        self.assertIn(
            "wireframe-data.copyFreeze.status: must be 'approved' before structural approvalStatus can be 'approved'",
            problems,
        )

    def test_v5_navigation_controls_are_bounded(self):
        data = schema5_data()
        region = data["screens"][0]["regions"][0]
        state = data["screens"][0]["states"][0]
        region["controls"] = {
            "menus": [{
                "id": "menu",
                "label": {"kind": "static", "role": "navigation toggle", "text": "Menu", "status": "approved", "source": "PRD"},
                "items": ["Refresh balance"],
                "targets": ["390"],
                "defaultOpen": False,
            }],
            "tabs": [{
                "id": "ready-tab",
                "label": {"kind": "static", "role": "tab", "text": "Ready", "status": "approved", "source": "PRD"},
                "state": "ready",
            }],
        }
        self.assertEqual([], validate_html(render_html(data)))
        bad = copy.deepcopy(data)
        bad["screens"][0]["regions"][0]["controls"]["menus"][0]["items"] = ["Invented action"]
        self.assertTrue(
            any("distinct actions" in item for item in validate_html(render_html(bad)))
        )
        self.assertIn(state["id"], "ready")

    def test_v5_flows_bind_control_and_declared_endpoint_states(self):
        data = schema5_data()
        empty_state = copy.deepcopy(data["screens"][0]["states"][0])
        empty_state.update(id="empty", label="Empty")
        empty_state["treatments"] = {data["screens"][0]["regions"][0]["id"]: {
            "layout": "Retain the region height",
            "copy": [{"kind": "static", "role": "status", "text": "No items", "status": "approved", "source": "PRD"}],
        }}
        data["screens"][0]["states"].append(empty_state)
        data["flows"][0]["destination"]["state"] = "empty"
        self.assertEqual([], validate_html(render_html(data)))
        cases = (
            (lambda item: item["flows"][0].update(sourceState="invented"), "sourceState"),
            (lambda item: item["flows"][0].update(control="invented"), "control"),
            (lambda item: item["flows"][0]["destination"].update(state="invented"), "destination.state"),
            (lambda item: item["flows"][0]["destination"].update(surface="UI-999"), "destination.state"),
            (lambda item: item["flows"][0].update(to="Invented result"), "exact feedback copy"),
            (lambda item: item["screens"][0]["regions"][0]["actions"][0].pop("id"), ".id"),
        )
        for change, expected in cases:
            with self.subTest(expected=expected):
                bad = copy.deepcopy(data)
                change(bad)
                self.assertTrue(any(expected in issue for issue in validate_html(render_html(bad))))


class ReviewerV3Tests(unittest.TestCase):
    def test_v3_requires_product_state_sources_and_token_purpose(self):
        manifest = {"schema": "ui-hifi/2", "surfaces": [{
            "id": "UI-001", "page": "index.html", "route": "/", "states": ["ready", "loading"],
            "responsive": {"targets": [390, 768]},
        }]}
        html = add_shell(_source_html(manifest["surfaces"][0], version=3), manifest, version=3)
        self.assertEqual([], hifi_reviewer.reviewer_contract({"index.html": html}, manifest)[0])
        missing_state = html.replace('data-hifi-state-view="loading"', 'data-state-view="loading"')
        self.assertTrue(any("requires a visible-state source" in issue for issue in
                            hifi_reviewer.reviewer_contract({"index.html": missing_state}, manifest)[0]))
        missing_purpose = html.replace(' data-token-purpose="Readable product text"', '')
        self.assertTrue(any("named purpose" in issue for issue in
                            hifi_reviewer.reviewer_contract({"index.html": missing_purpose}, manifest)[0]))

    def test_shared_css_is_exact_and_product_isolated(self):
        html = HIFI_TEMPLATE.read_text(encoding="utf-8")
        self.assertEqual([], reviewer_shell.shared_css_drift(html))
        self.assertEqual([], reviewer_shell.shared_css_drift(WIREFRAME_V5.read_text(encoding="utf-8")))
        css = reviewer_shell.css_segment(html)
        self.assertIn('"Noto Sans CJK TC"', css)
        self.assertIn("var(--review-sidebar-width)", css)
        self.assertNotIn("[data-ui-surface]", css)
        self.assertNotIn(".product-", css)
        drifted = html.replace("--review-sidebar-width:236px", "--review-sidebar-width:240px")
        self.assertTrue(reviewer_shell.shared_css_drift(drifted))

    def test_v2_and_v3_shells_are_current_and_bad_shell_is_rejected(self):
        self.assertTrue(hifi_reviewer.has_current_reviewer_shell({
            "index.html": '<aside data-hifi-reviewer-shell data-hifi-reviewer-version="2"></aside>'
        }))
        self.assertTrue(hifi_reviewer.has_current_reviewer_shell({
            "index.html": '<aside data-hifi-reviewer-shell data-hifi-reviewer-version="3"></aside>'
        }))

    def test_declared_product_controls_must_bind_product_panels(self):
        good = (
            '<main data-ui-surface="UI-001">'
            '<button data-product-menu aria-controls="menu" aria-expanded="false"></button>'
            '<div id="menu" hidden></div>'
            "</main>"
        )
        self.assertEqual([], hifi_reviewer.product_control_findings({"index.html": good}))
        shell = (
            '<aside data-hifi-reviewer-shell><button data-product-menu aria-controls="menu" aria-expanded="false"></button></aside>'
            + good
        )
        self.assertTrue(hifi_reviewer.product_control_findings({"index.html": shell}))
        bad = good.replace('aria-controls="menu"', 'aria-controls="missing"')
        self.assertTrue(any("bind an existing panel" in item for item in hifi_reviewer.product_control_findings({"index.html": bad})))


class ReviewerRuntimeNodeTests(unittest.TestCase):
    def run_node(self, source, *, env=None):
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable")
        merged_env = dict(os.environ, **(env or {}))
        return subprocess.run(
            [node, "-"],
            input=source,
            capture_output=True,
            text=True,
            timeout=15,
            env=merged_env,
        )

    def test_runtime_isolates_targets_by_package_and_page(self):
        html = HIFI_TEMPLATE.read_text(encoding="utf-8")
        source = html.split('<script id="hifi-reviewer-runtime">', 1)[1].split("</script>", 1)[0]
        encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
        result = self.run_node(r'''
const vm=require("vm");
const storage={map:new Map(),getItem(key){return this.map.has(key)?this.map.get(key):null},setItem(key,value){this.map.set(key,String(value))}};
const context={window:{}};
vm.runInNewContext(Buffer.from(process.env.SOURCE_B64,"base64").toString("utf8"),context);
const make=(page,platform)=>context.window.createHifiReviewerRuntime({
  storage, packageId:"bundle-a", platform, page,
  pages:["index.html","ios.html"],
  targets:["390","768","1200","compact","regular"],
  targetsByPage:{"index.html":["390","768","1200"],"ios.html":["compact","regular"]}
});
const web=make("index.html","Web"); web.selectTarget("768");
const native=make("ios.html","App"); native.selectTarget("regular");
if(web.snapshot().target!=="768") throw Error("second package view changed web target");
web.setPage("ios.html");
if(web.snapshot().target!=="compact") throw Error("destination crossed platform storage boundary");
web.setPage("index.html");
if(web.snapshot().target!=="768") throw Error("web target was not restored per page: "+JSON.stringify({snapshot:web.snapshot(),keys:Array.from(storage.map)}));
if(!storage.map.has("hifi-reviewer:target:bundle-a:Web:index.html")) throw Error("package/platform/page storage key missing");
if(storage.map.has("hifi-reviewer:target:bundle-a:App:index.html")) throw Error("platform state leaked");
if(storage.map.has("hifi-reviewer:target")) throw Error("legacy key was created for a package runtime");
''', env={"SOURCE_B64": encoded})
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_connected_product_menus_and_tabs_change_state_with_keyboard(self):
        html = HIFI_TEMPLATE.read_text(encoding="utf-8")
        source = html.split('<script id="hifi-reviewer-runtime">', 1)[1].split("</script>", 1)[0]
        encoded = base64.b64encode(source.encode("utf-8")).decode("ascii")
        result = self.run_node(r'''
const vm=require("vm");
class Node {
  constructor(tag,attrs={},text=""){this.tagName=tag.toUpperCase();this.attrs={...attrs};this.children=[];this.parentNode=null;this.hidden=false;this.listeners={};this.focused=false;this.text=text;
    if(text){this.textContent=text;}
    for(const [k,v] of Object.entries(attrs)) if(k.startsWith("data-")) this.dataset??={}, this.dataset[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=v;}
  append(...children){for(const child of children){child.parentNode=this;this.children.push(child);}return children[0];}
  setAttribute(k,v){this.attrs[k]=String(v);}
  getAttribute(k){return Object.prototype.hasOwnProperty.call(this.attrs,k)?this.attrs[k]:null;}
  addEventListener(k,fn){(this.listeners[k]??=[]).push(fn);}
  emit(k,event={}){(this.listeners[k]||[]).forEach(fn=>fn(event));}
  focus(){this.focused=true;}
  closest(selector){let current=this;while(current){if(selector==="[role='tablist']"&&current.getAttribute("role")==="tablist")return current;current=current.parentNode;}return null;}
  querySelectorAll(selector){const out=[];const visit=n=>{for(const child of n.children){if(selector==="[data-product-menu]"&&child.getAttribute("data-product-menu")!==null)out.push(child);if(selector==="[data-product-tab]"&&child.getAttribute("data-product-tab")!==null)out.push(child);if(selector==="[role='menuitem']"&&child.getAttribute("role")==="menuitem")out.push(child);if(selector==="[role='menuitem']"&&child.getAttribute("role")==="menuitem")out.push(child);visit(child);}};visit(this);return out;}
  querySelector(selector){if(selector.startsWith("#")){const id=selector.slice(1);const visit=n=>{for(const child of n.children){if(child.getAttribute("id")===id)return child;const found=visit(child);if(found)return found;}return null;};return visit(this);}const all=this.querySelectorAll(selector);return all[0]||null;}
}
const CSS={escape:v=>v};
const document={activeElement:null};
const surface=new Node("main",{"data-ui-surface":"UI-001"});
const toggle=new Node("button",{"data-product-menu":"","aria-controls":"menu","aria-expanded":"false"});
const menu=new Node("div",{id:"menu",hidden:""}); const item=new Node("button",{role:"menuitem"},"Action"); menu.append(item);
const tablist=new Node("div",{role:"tablist"});
const tab1=new Node("button",{"data-product-tab":"","aria-controls":"panel1","aria-selected":"true"}); const panel1=new Node("section",{id:"panel1"});
const tab2=new Node("button",{"data-product-tab":"","aria-controls":"panel2","aria-selected":"false"}); const panel2=new Node("section",{id:"panel2",hidden:""});
tablist.append(tab1,tab2); surface.append(toggle,menu,tablist,panel1,panel2);
const root=new Node("body");root.append(surface);
const context={window:{},document,CSS};
vm.runInNewContext(Buffer.from(process.env.SOURCE_B64,"base64").toString("utf8"),context);
const controls=context.window.connectProductControls(root);
const menuMatches=root.querySelectorAll("[data-product-menu]").length, tabMatches=root.querySelectorAll("[data-product-tab]").length;
if(controls.menus.length!==1||controls.tabs.length!==2)throw Error("declared controls were not connected: "+JSON.stringify({menuMatches,tabMatches,menus:controls.menus.length,tabs:controls.tabs.length,host:root.children.length,surface:surface.children.length}));
toggle.emit("click"); if(toggle.getAttribute("aria-expanded")!=="true"||menu.hidden)throw Error("click did not open menu");
if(!(menu.listeners.keydown||[]).length)throw Error("menu keydown not connected:"+JSON.stringify({listeners:Object.keys(menu.listeners)}));
document.activeElement=item; menu.emit("keydown",{key:"Escape",preventDefault(){}}); if(toggle.getAttribute("aria-expanded")!=="false"||!menu.hidden||!toggle.focused)throw Error("Escape did not close and return focus");
tab2.emit("click"); if(tab2.getAttribute("aria-selected")!=="true"||tab1.getAttribute("aria-selected")!=="false"||!panel1.hidden||panel2.hidden)throw Error("tab click did not change content state");
tab2.emit("keydown",{key:"ArrowLeft",preventDefault(){}}); if(!tab1.focused||tab1.getAttribute("aria-selected")!=="true")throw Error("tab arrow key did not move selection: "+JSON.stringify({focused:tab1.focused,selected:tab1.getAttribute("aria-selected"),listeners:(tab2.listeners.keydown||[]).length}));
''', env={"SOURCE_B64": encoded})
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)


class AssembleUiReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.manifest_path = root / "manifest.json"
        self.sources = root / "sources"
        self.output = root / "bundle"
        self.sources.mkdir()
        self.manifest = {
            "schema": "ui-hifi/2",
            "surfaces": [
                {"id": "UI-001", "page": "index.html", "route": "/", "states": ["ready"], "responsive": {"targets": [390, 768]}, "platformGroup": "Web"},
                {"id": "UI-002", "page": "details.html", "route": "/details", "states": ["ready"], "responsive": {"targets": [768]}},
            ],
        }
        self.entry = (
            '<html><head><title>Entry</title></head><body>'
            '<div data-hifi-canvas data-hifi-targets="390 768" data-hifi-target="390"><main data-ui-surface="UI-001">Entry</main></div>'
            '<section data-hifi-panel="overview" hidden><h1>Overview</h1></section>'
            '<section data-hifi-panel="design-tokens" hidden><h1>Tokens</h1></section>'
            '<script id="ui-hifi-manifest" type="application/json">' + json.dumps(self.manifest) + '</script>'
            "</body></html>"
        )
        self.child = (
            '<html><head><title>Details</title></head><body>'
            '<div data-hifi-canvas data-hifi-targets="768" data-hifi-target="768"><main data-ui-surface="UI-002">Details</main></div>'
            "</body></html>"
        )

    def tearDown(self):
        self.temp.cleanup()

    def write_sources(self):
        (self.sources / "index.html").write_text(self.entry, encoding="utf-8")
        (self.sources / "details.html").write_text(self.child, encoding="utf-8")
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")

    def assemble(self, overwrite=False):
        return assemble_ui_review.assemble(
            self.manifest_path,
            [f"index.html={self.sources / 'index.html'}", f"details.html={self.sources / 'details.html'}"],
            self.output,
            overwrite=overwrite,
        )

    def test_assembles_exact_shell_runtime_css_and_child_hashes(self):
        self.write_sources()
        paths = self.assemble()
        self.assertEqual(2, len(paths))
        entry = (self.output / "index.html").read_text(encoding="utf-8")
        child = (self.output / "details.html").read_text(encoding="utf-8")
        self.assertEqual([], reviewer_shell.shared_css_drift(entry))
        self.assertEqual([], reviewer_shell.shared_css_drift(child))
        self.assertIn('data-hifi-reviewer-version="3"', entry)
        self.assertIn('<span data-hifi-platform-group="Web">Web</span>', entry)
        self.assertNotIn("data-hifi-platform-group", child.split("</nav>", 1)[1])
        self.assertIn('connectHifiReviewer({"packageId"', entry)
        manifest = json.loads(entry.split('<script id="ui-hifi-manifest" type="application/json">', 1)[1].split("</script>", 1)[0])
        child_hash = manifest["pages"][0]
        self.assertEqual({"path": "details.html", "sha256": hashlib.sha256((self.output / "details.html").read_bytes()).hexdigest()}, child_hash)

    def test_rejects_case_collision_stale_sources_and_overwrite(self):
        self.write_sources()
        self.assemble()
        with self.assertRaises(SystemExit):
            self.assemble()
        self.assemble(overwrite=True)
        self.manifest["pages"] = [{"path": "details.html", "sha256": "0" * 64}]
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        with self.assertRaises(SystemExit):
            assemble_ui_review.assemble(
                self.manifest_path,
                [f"index.html={self.sources / 'index.html'}", f"details.html={self.sources / 'details.html'}"],
                Path(self.temp.name) / "second",
            )
        with self.assertRaises(SystemExit):
            assemble_ui_review._parse_sources(["Index.html=x.html", "index.html=y.html"])

    def test_identical_manifest_in_distinct_bundle_locations_has_distinct_package_identity(self):
        self.write_sources()
        first = self.assemble()
        second_dir = Path(self.temp.name) / "other-bundle"
        assemble_ui_review.assemble(
            self.manifest_path,
            [f"index.html={self.sources / 'index.html'}", f"details.html={self.sources / 'details.html'}"],
            second_dir,
        )
        first_html = Path(first[0]).read_text(encoding="utf-8")
        second_html = (second_dir / "index.html").read_text(encoding="utf-8")
        first_id = re.search(r'connectHifiReviewer\(\{"packageId":\s*"([^"]+)"\}\)', first_html).group(1)
        second_id = re.search(r'connectHifiReviewer\(\{"packageId":\s*"([^"]+)"\}\)', second_html).group(1)
        self.assertNotEqual(first_id, second_id)
        with self.assertRaises(SystemExit):
            assemble_ui_review.assemble(
                self.manifest_path,
                [f"index.html={self.sources / 'index.html'}", f"details.html={self.sources / 'details.html'}"],
                self.sources,
                overwrite=True,
            )


if __name__ == "__main__":
    unittest.main()

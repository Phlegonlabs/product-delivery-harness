"""Design handoff extensions preserve old inputs and reject false evidence."""

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from test_wireframe_contract import render_html, validate_html, wireframe_data
from check_design_freshness import inspect


class ReadingAndMotionTests(unittest.TestCase):
    def test_paired_copy_is_frozen_and_language_bound(self):
        data = wireframe_data()
        item = data["screens"][0]["regions"][0]["elements"][0]
        item["locale"] = "en-US"
        translation = dict(item, locale="zh-Hant", text="可用餘額")
        item["parallel"] = [translation]
        self.assertEqual([], validate_html(render_html(data), require_filled=True, require_approved=True))
        for key, value, message in (("status", "draft", "copy is frozen"),
                                    ("locale", "EN-us", "distinct"),
                                    ("direction", "sideways", "ltr, rtl or auto"),
                                    ("role", "button", "preserve role"),
                                    ("parallel", [], "without nested")):
            candidate = copy.deepcopy(data)
            candidate["screens"][0]["regions"][0]["elements"][0]["parallel"][0][key] = value
            self.assertIn(message, "\n".join(validate_html(render_html(candidate))))

    def test_action_appearance_does_not_add_destinations(self):
        data = wireframe_data()
        action = data["screens"][0]["regions"][0]["actions"][0]
        action.update(variant="tertiary", size="large", fullWidth=True)
        self.assertEqual([], validate_html(render_html(data), require_filled=True, require_approved=True))
        action["fullWidth"] = "true"
        self.assertIn("must be boolean", "\n".join(validate_html(render_html(data))))

    def test_motion_scope_is_complete_but_legacy_intent_remains_readable(self):
        data = wireframe_data()
        intent = dict(treatment="motion", purpose="Explain progress", trigger="click",
                      draftPrompt="Show local task progress", source="Synthetic intent",
                      reducedMotionFallback="Static progress", generationRoute="CSS-WAAPI",
                      generationStatus="deferred")
        data["screens"][0]["regions"][0]["mediaIntent"] = intent
        self.assertEqual([], validate_html(render_html(data)))
        intent["motionSpec"] = {key: "Recorded local intent" for key in
                                ("scope", "behavior", "space", "compact", "playback", "cost")}
        self.assertEqual([], validate_html(render_html(data)))
        del intent["motionSpec"]["compact"]
        self.assertIn("must contain scope", "\n".join(validate_html(render_html(data))))

    def test_disclosure_requires_navigation_and_approved_target_label(self):
        data = wireframe_data()
        region = data["screens"][0]["regions"][0]
        region["presentation"] = "navigation"
        region["disclosure"] = {"targets": ["390"], "label": {"kind": "static", "role": "navigation label",
                                  "text": "Menu", "status": "approved", "source": "Synthetic approved copy"}}
        self.assertEqual([], validate_html(render_html(data), require_filled=True, require_approved=True))
        region["disclosure"]["targets"] = ["ipad"]
        self.assertIn("declared responsive targets", "\n".join(validate_html(render_html(data))))
        region["disclosure"]["targets"] = ["390"]
        region["disclosure"]["label"]["status"] = "draft"
        self.assertIn("copy is frozen", "\n".join(validate_html(render_html(data))))

    def test_unrenderable_language_pairs_and_malformed_motion_fail_closed(self):
        data = wireframe_data()
        item = data["screens"][0]["regions"][0]["elements"][0]
        item.update(role="select option", locale="en-US", parallel=[dict(item, role="select option", locale="zh-Hant")])
        self.assertIn("cannot display stacked", "\n".join(validate_html(render_html(data))))
        data["screens"][0]["regions"][0]["mediaIntent"] = {"treatment": {"motion": True}}
        self.assertTrue(validate_html(render_html(data)))

    def test_iphone_targets_do_not_require_ipad(self):
        data = wireframe_data()
        data.pop("viewports")
        data["sizeClasses"] = ["iphone-small", "iphone-large"]
        data["canvasWidths"] = {"iphone-small": 375, "iphone-large": 430}
        screen = data["screens"][0]
        compact = screen["responsiveLayouts"]["390"]
        screen["responsiveLayouts"] = {"iphone-small": compact, "iphone-large": copy.deepcopy(compact)}
        self.assertEqual([], validate_html(render_html(data), require_filled=True, require_approved=True))

    def test_recipe_library_has_bounded_complete_geometry(self):
        path = Path(__file__).resolve().parents[2] / "assets/templates/composition-patterns.json"
        patterns = json.loads(path.read_text(encoding="utf-8"))["patterns"]
        self.assertEqual(7, len({item["id"] for item in patterns}))
        self.assertEqual(4, sum(p["platform"] == "web" for p in patterns))
        for pattern in patterns:
            self.assertTrue(set(pattern["neverDropRoles"]) <= set(pattern["roles"]))
            for layout in pattern["layouts"].values():
                self.assertEqual(set(pattern["roles"]), set(layout["spans"]))
                self.assertEqual(pattern["roles"], layout["order"])
                self.assertTrue(all(0 < span <= layout["columns"] for span in layout["spans"].values()))
            self.assertTrue(pattern["avoidWhen"] and pattern["stressCases"])

    def test_disclosure_retains_review_state_and_escape_restores_focus(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node unavailable")
        template = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"
        script = r'''
const fs=require('fs'),vm=require('vm');
const html=fs.readFileSync(process.argv[2],'utf8').replace(/\r\n/g,'\n');
const source=html.match(/const renderRegion = [\s\S]*?\n      const setInspectorOpen/)[0].replace(/\n\s*const setInspectorOpen$/,'');
class N {constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.events={};this.style={setProperty(){}};this.isConnected=true;}append(...v){this.children.push(...v);}setAttribute(){}addEventListener(k,v){this.events[k]=v;}closest(){return null;}focus(){this.focused=true;}}
const layout={spans:{nav:1}},screen={id:'UI-1',responsiveLayouts:{phone:layout}};
const region={id:'nav',presentation:'navigation',section:'Navigation',actions:[],disclosure:{targets:['phone'],label:{text:'Menu'}}};
const context={data:{screens:[screen]},state:{},element:tag=>new N(tag),localSearchConfigFor:()=>null,renderRegionContent(){},appendActions(){},renderCopyItem:()=>new N('span'),currentScreen:()=>screen,content:{querySelector:()=>null}};
vm.runInNewContext(source+'\nthis.render=renderRegion;',context);
let details=context.render('UI-1',region,null,layout).children.find(n=>n.tag==='details');
details.open=true;details.events.toggle();
details=context.render('UI-1',region,null,layout).children.find(n=>n.tag==='details');
if(!details.open)throw Error('Review redraw lost open navigation');
details.events.keydown({key:'Escape',preventDefault(){}});
if(details.open||!details.children[0].focused)throw Error('Escape did not close and restore summary focus');
'''
        result = subprocess.run([node, "-", str(template)], input=script, capture_output=True,
                                text=True, encoding="utf-8", timeout=15)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_layout_qa_skips_only_closed_navigation_content(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node unavailable")
        template = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"
        script = r'''
const fs=require('fs'),vm=require('vm');
const html=fs.readFileSync(process.argv[2],'utf8').replace(/\r\n/g,'\n');
const source=html.match(/const runLayoutQa = [\s\S]*?\n      const renderScreenFlows/)[0].replace(/\n\s*const renderScreenFlows$/,'');
let closed=true;
const region={dataset:{region:'nav'},getBoundingClientRect:()=>({left:0,right:100,top:0,bottom:44})};
const disclosure={querySelector:()=>({contains:()=>false})};
const item={closest:s=>s==='[data-region]'?region:closed?disclosure:null,getBoundingClientRect:()=>({left:0,right:100,top:44,bottom:80}),dataset:{copyRole:'label'},matches:()=>false};
const canvas={isConnected:true,scrollWidth:100,clientWidth:100,getBoundingClientRect:()=>({width:100}),querySelectorAll:s=>s.startsWith(':scope')?[region]:[item]};
const panel={isConnected:true,setAttribute(k,v){this.status=v;}};
const screen={id:'UI-1'};
const context={qaGeneration:0,state:{screenState:'ready'},currentScreen:()=>screen,targetFor:()=> 'phone',requestAnimationFrame:f=>f(),rectanglesOverlap:()=>false,getComputedStyle:()=>({overflowX:'visible',overflowY:'visible'}),responsiveSpecFor:()=>({canvasWidths:{phone:100}}),window:{}};
vm.runInNewContext(source+'\nthis.run=runLayoutQa;',context);
context.run(canvas,{isConnected:true},panel,screen);
if(panel.status!=='pass')throw Error('Closed navigation falsely fails QA');
closed=false;
context.run(canvas,{isConnected:true},panel,screen);
if(panel.status!=='fail')throw Error('Open overflowing navigation falsely passes QA');
'''
        result = subprocess.run([node, "-", str(template)], input=script, capture_output=True,
                                text=True, encoding="utf-8", timeout=15)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_renderer_stacks_literal_copy_with_language_and_direction(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node unavailable")
        template = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"
        script = r'''
const fs=require('fs'), vm=require('vm');
const html=fs.readFileSync(process.argv[2],'utf8').replace(/\r\n/g,'\n');
const source=html.match(/const renderCopyItem = [\s\S]*?\n      const localSearchConfigFor/)[0].replace(/\n\s*const localSearchConfigFor$/,'');
class N { constructor(tag,cls,text){this.tag=tag;this.textContent=text;this.children=[];this.dataset={};this.attrs={};} append(...v){this.children.push(...v);} setAttribute(k,v){this.attrs[k]=v;} }
const context={element:(...v)=>new N(...v),copyCategory:()=> 'display',copyRole:v=>v.role,copyText:v=>v.text};
vm.runInNewContext(source+'\nthis.render=renderCopyItem;',context);
const output=context.render({role:'heading',text:'<script>literal</script>',locale:'en-US',parallel:[{role:'heading',text:'內容',locale:'zh-Hant',direction:'ltr'}]});
if(output.tag!=='h2'||output.children.length!==2)throw Error('Lost semantic bilingual pair');
if(output.children[0].textContent!=='<script>literal</script>')throw Error('Copy interpreted as markup');
if(output.children[1].attrs.lang!=='zh-Hant'||output.children[1].attrs.dir!=='ltr')throw Error('Lost assistive reading language');
const inventorySource=html.match(/const copyRecords = [\s\S]*?\n      const renderCopyInventory/)[0].replace(/\n\s*const renderCopyInventory$/,'');
const sample={kind:'static',role:'heading',text:'Read',locale:'en-US',parallel:[{kind:'static',role:'heading',text:'閱讀',locale:'zh-Hant',status:'draft',source:'Translation owner'}]};
const inventoryContext={data:{screens:[{id:'UI-1',regions:[{id:'body',elements:[sample],actions:[]}],states:[]}],flows:[]},localSearchConfigFor:()=>null};
vm.runInNewContext(inventorySource+'\nthis.records=copyRecords;',inventoryContext);
const records=inventoryContext.records();
if(records.length!==2||records[1].value.status!=='draft'||records[1].value.source!=='Translation owner')throw Error('Inventory hid translation approval');

'''
        result = subprocess.run([node, "-", str(template)], input=script, capture_output=True,
                                text=True, encoding="utf-8", timeout=15)
        self.assertEqual(0, result.returncode, result.stderr)


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("docs/product/PRD.md", "docs/design/wireframes.html", "docs/design/ui-references/r/index.html"):
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(name, encoding="utf-8")
        self.skill = "a" * 64
        self.wire = "docs/design/wireframes.html"
        self.hifi = "docs/design/ui-references/r/index.html"
        self.prd = "docs/product/PRD.md"
        self.baseline = {"schema": "design-observation/1", "skillDigest": self.skill,
                         "implementation": "not_started", "implementationEvidence": "Owner and scoped code inventory",
                         "artifacts": [dict(self.binding(self.wire), inputs=[self.binding(self.prd)]),
                                       dict(self.binding(self.hifi), inputs=[self.binding(self.wire)])]}

    def binding(self, name):
        return {"path": name, "sha256": hashlib.sha256((self.root/name).read_bytes()).hexdigest()}

    def run_check(self, **kwargs):
        return inspect(self.root, self.baseline, kwargs.get("installed", self.skill), kwargs.get("loaded", self.skill))

    def test_unchanged_is_not_approval(self):
        report = self.run_check()
        self.assertEqual("bytes_unchanged", report["status"])
        self.assertIn("verify full package coverage", report["meaning"])

    def test_changed_prd_propagates_to_unchanged_hifi(self):
        (self.root/self.prd).write_text("new requirement", encoding="utf-8")
        report = self.run_check()
        self.assertEqual("review_required", report["status"])
        self.assertTrue(any("upstream_review_required" in reason for reason in report["artifacts"][1]["reasons"]))

    def test_unknown_and_installed_only_update_never_pass(self):
        self.assertIn("skill_identity_unknown", self.run_check(loaded=None)["findings"])
        self.assertIn("restart_required", self.run_check(installed="b"*64)["findings"])
        self.baseline["artifacts"][0]["sha256"] = None
        self.assertEqual("review_required", self.run_check()["status"])

    def test_missing_child_is_not_current(self):
        self.baseline["artifacts"][1]["path"] = "docs/design/ui-references/r/missing.html"
        self.assertIn("artifact_missing", self.run_check()["artifacts"][1]["reasons"])

    def test_bad_paths_hashes_and_cycles_are_rejected(self):
        original = copy.deepcopy(self.baseline)
        for name in ("../secret.md", "docs/design/../../secret.md", "docs/design/.env.json", "C:/secret.md", "docs/design/test.exe"):
            self.baseline = copy.deepcopy(original)
            self.baseline["artifacts"][0]["path"] = name
            with self.assertRaises(ValueError):
                self.run_check()
        self.baseline = copy.deepcopy(original)
        self.baseline["artifacts"][0]["inputs"] = [self.binding(self.hifi)]
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.run_check()
        self.baseline = copy.deepcopy(original)
        self.baseline["skillDigest"] = "newest"
        with self.assertRaises(ValueError):
            self.run_check()


if __name__ == "__main__":
    unittest.main()

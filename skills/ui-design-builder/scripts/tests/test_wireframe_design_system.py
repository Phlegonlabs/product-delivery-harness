"""Execute the draft view with renderer and computed-style doubles."""

from pathlib import Path
import re
import shutil
import subprocess
import unittest


TEMPLATE = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"


class WireframeDesignSystemTests(unittest.TestCase):
    def test_each_listed_value_is_declared_and_used_by_canvas_css(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        names = set(re.findall(r"--wf-([a-z-]+):", html))
        used = set(re.findall(r"var\(--wf-([a-z-]+)\)", html))
        block = html.split("const tokens = [", 1)[1].split("];", 1)[0]
        displayed = set(re.findall(r'\["([a-z-]+)",', block))
        self.assertEqual(names, used)
        self.assertEqual(names, displayed)

    def test_draft_view_uses_actual_values_and_keeps_examples_out_of_product_data(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable")
        script = r'''
const fs = require("fs"), vm = require("vm");
const html = fs.readFileSync(process.argv[2], "utf8").replace(/\r\n/g, "\n");
class Node {
  constructor(tag, cls, text) { this.tag=tag; this.className=cls||""; this.textContent=text||""; this.children=[]; this.dataset={}; this.events={}; this.style={}; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children=nodes; }
  setAttribute(name,value) { this[name]=value; }
  addEventListener(name,fn) { this.events[name]=fn; }
  querySelectorAll() { return this.children.flatMap(n=>[...(/copy-item|field-input|action-button/.test(n.className)?[n]:[]),...n.querySelectorAll()]); }
}
const content = new Node("main"), pageList = new Node("nav"), product={screens:[{id:"UI-001", name:"Home", route:"/"}]};
const before=JSON.stringify(product), uses=[], context={
  content, pageList, data:product, document:{documentElement:{}},
  element:(tag,cls,text)=>new Node(tag,cls,text),
  makePageButton:(id,title,detail)=>({id,title,detail}),
  getComputedStyle:()=>({fontSize:"19px", getPropertyValue:name=>{uses.push(name);return name==="--wf-body"?"19px":name==="--wf-ink"?"#123456":"computed";}}),
  renderRegionContent:(parent,region)=>{parent.append(new Node("p","",region.elements.map(x=>x.text).join(" ")));}
};
vm.runInNewContext(html.match(/const renderDesignSystem = [\s\S]*?\n      const render =/)[0].replace(/\n\s*const render =$/, "")+"\nthis.show=renderDesignSystem;",context);
context.show();
const flatten=n=>[n,...n.children.flatMap(flatten)];
let nodes=flatten(content);
if (!nodes.some(n=>n.textContent.includes("--wf-body: 19px"))) throw Error("values are not read from actual CSS");
if (!nodes.some(n=>n.style.backgroundColor==="#123456")) throw Error("swatch does not use actual CSS");
if (!nodes.some(n=>n.textContent.includes("size: 19px"))) throw Error("specimen measurement missing");
if (!nodes.some(n=>n.textContent.includes("Wireframe Draft"))) throw Error("draft boundary absent");
if (JSON.stringify(product)!==before) throw Error("review samples changed product data");
const primary=nodes.find(n=>n.dataset.emphasis==="primary");
primary.events.click();
if (!nodes.some(n=>n.textContent==="primary specimen selected.")) throw Error("specimen button is dead");
context.show();
if(content.children.length!==1)throw Error("repeat render duplicated view");
vm.runInNewContext(html.match(/const renderNavigation = [\s\S]*?\n      const targetFor/)[0].replace(/\n\s*const targetFor$/, "")+"\nthis.nav=renderNavigation;",context);
context.nav();
if(!pageList.children.some(n=>n.id==="design-system"))throw Error("draft view not reachable");
if(pageList.children.filter(n=>n.id.startsWith("UI-")).length!==1)throw Error("draft view minted a product screen");
context.state={page:"design-system"};
context.currentScreen=()=>context.state.page==="UI-001"?product.screens[0]:undefined;
context.renderNavigation=()=>{};context.renderResponsiveControls=()=>{};context.renderStateControls=()=>{};
context.responsiveControls={parentElement:{}};context.stateControls={parentElement:{}};context.annotationToggle={};
let rendered="";
context.renderScreen=()=>{rendered="screen";};context.renderOverview=()=>{rendered="overview";};
vm.runInNewContext(html.match(/const render = [\s\S]*?\n      annotationToggle.addEventListener/)[0].replace(/\n\s*annotationToggle.addEventListener$/, "")+"\nthis.render=render;",context);
context.render();
if(context.state.page!=="design-system"||!context.responsiveControls.parentElement.hidden)throw Error("draft route fell back or controls remained visible");
context.state.page="UI-001";context.render();
if(rendered!=="screen"||context.responsiveControls.parentElement.hidden||context.annotationToggle.disabled)throw Error("product navigation did not restore controls");
context.state.page="unknown";context.render();
if(rendered!=="screen"||context.state.page!=="UI-001")throw Error("unknown route must restore the primary product page");
'''
        result = subprocess.run([node, "-", str(TEMPLATE)], input=script, capture_output=True, text=True, timeout=15)
        self.assertEqual(0, result.returncode, result.stderr)


if __name__ == "__main__":
    unittest.main()

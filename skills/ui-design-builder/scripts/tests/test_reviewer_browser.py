"""Real browser checks for the reusable reviewer boundary and controls."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assemble_ui_review import assemble


TEMPLATE = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"

def playwright_module(node: str) -> str | None:
    candidates = [
        Path(os.environ["PLAYWRIGHT_MODULE"]) if os.environ.get("PLAYWRIGHT_MODULE") else None,
        Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright",
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return str(candidate)
    result = subprocess.run([node, "-p", "require.resolve('playwright')"],
                            text=True, capture_output=True, timeout=5)
    return result.stdout.strip() if result.returncode == 0 else None


class ReviewerBrowserTests(unittest.TestCase):
    def require_browser(self) -> tuple[str, str]:
        node = shutil.which("node")
        if not node:
            self.browser_unavailable("Node.js is unavailable")
        playwright = playwright_module(node)
        if not playwright:
            self.browser_unavailable("Node Playwright is unavailable")
        return node, playwright

    def browser_unavailable(self, reason: str) -> None:
        message = f"Required browser test prerequisite missing: {reason}"
        if os.environ.get("PDH_REQUIRE_BROWSER_TESTS") == "1":
            self.fail(message)
        self.skipTest(message)

    def run_hifi_test_without_node(self, required: bool) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary:
            empty_path = Path(temporary) / "empty-path"
            empty_path.mkdir()
            env = os.environ.copy()
            if required:
                env["PDH_REQUIRE_BROWSER_TESTS"] = "1"
            else:
                env.pop("PDH_REQUIRE_BROWSER_TESTS", None)
            env["PATH"] = str(empty_path)
            env["PLAYWRIGHT_MODULE"] = str(Path(temporary) / "missing-playwright")
            return subprocess.run(
                [sys.executable, "-B", str(Path(__file__).resolve()),
                 "ReviewerBrowserTests.test_hifi_product_css_cannot_change_shell_and_state_controls_work"],
                capture_output=True,
                text=True,
                env=env,
                timeout=15,
            )

    def test_required_browser_mode_fails_when_node_is_missing(self):
        result = self.run_hifi_test_without_node(required=True)
        self.assertNotEqual(0, result.returncode, result.stdout)
        self.assertIn("Required browser test prerequisite missing: Node.js is unavailable", result.stderr)

    def test_optional_browser_mode_skips_when_node_is_missing(self):
        result = self.run_hifi_test_without_node(required=False)
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assertIn("OK (skipped=1)", result.stderr)

    def test_hifi_product_css_cannot_change_shell_and_state_controls_work(self):
        node, playwright = self.require_browser()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            bundle = root / "bundle"
            manifest = {"schema": "ui-hifi/2", "surfaces": [
                {"id": "UI-001", "page": "index.html", "route": "/", "states": ["ready", "loading"],
                 "platformGroup": "App", "responsive": {"targets": ["compact", "regular"]}},
                {"id": "UI-002", "page": "details.html", "route": "/details", "states": ["ready", "empty"],
                 "platformGroup": "Web", "responsive": {"targets": ["390", "1200"]}},
                {"id": "UI-003", "page": "settings.html", "route": "/settings", "states": ["ready", "error"],
                 "platformGroup": "App", "responsive": {"targets": ["compact", "regular"]}},
            ]}
            css = ('<style>:root{--ink:rgb(12,34,56)}body{background:black!important}aside,section{background:rgb(255,0,0)!important}'
                   'button,section{font:32px serif!important}'
                   '.product-button{font-size:14px!important;color:var(--ink)}'
                   '[data-hifi-canvas][data-hifi-target="regular"]{--ink:rgb(90,80,70)}'
                   '[data-hifi-canvas][data-hifi-target="regular"] .product-button{font-size:22px!important}'
                   '[data-ui-surface][data-hifi-state="loading"] .product-button{font-weight:700!important}'
                   '[data-hifi-canvas][data-hifi-target="compact"],'
                   '[data-hifi-canvas][data-hifi-target="390"]{width:390px}'
                   '[data-hifi-canvas][data-hifi-target="regular"]{width:768px}'
                   '[data-hifi-canvas][data-hifi-target="1200"]{width:1200px}'
                   '@container (max-width:600px){.product{padding:12px}}'
                   '@container (min-width:600px){.product-button{letter-spacing:3px!important}}</style>')
            product = ('<main data-ui-surface="UI-001" class="product"><h1>App</h1>'
                       '<input aria-label="Project" value="Retained project">'
                       '<button type="button" class="product-button">Save</button>'
                       '<button type="button" data-product-menu aria-controls="menu" aria-expanded="false">Menu</button>'
                       '<div id="menu" role="menu" hidden><button role="menuitem">Action</button></div>'
                       '<div role="tablist"><button data-product-tab role="tab" aria-controls="tab-one" aria-selected="true">One</button>'
                       '<button data-product-tab role="tab" aria-controls="tab-two" aria-selected="false">Two</button></div>'
                       '<section id="tab-one" role="tabpanel">First</section><section id="tab-two" role="tabpanel" hidden>Second</section>'
                       '<p data-hifi-state-view="ready">Ready content</p><p data-hifi-state-view="loading" hidden>Loading content</p></main>')
            entry = ('<html><head>' + css + '</head><body data-hifi-default-surface="UI-001">'
                     '<div data-hifi-canvas data-hifi-targets="compact regular" data-hifi-target="compact">' + product + '</div>'
                     '<section data-hifi-panel="overview" hidden><h1>Overview</h1>'
                     '<a data-hifi-state-coverage="UI-001 loading" data-state-destination="loading" href="index.html">Open loading</a>'
                     '<a data-hifi-state-coverage="UI-001 ready" data-state-destination="ready" href="index.html">Open ready</a>'
                     '<a data-hifi-state-coverage="UI-002 empty" data-state-destination="empty" href="details.html">Open empty</a></section>'
                     '<section data-hifi-panel="design-tokens" hidden><h1>Tokens</h1>'
                     '<article data-hifi-spec="token" data-source=":root" data-token-preview="color" data-property="--ink" '
                     'data-token-purpose="Readable product text"><span data-hifi-specimen-content="Ink">Ink</span><output></output></article>'
                     '<article data-hifi-spec="component" data-source-page="index.html" data-source=".product-button" '
                     'data-property="font-size"><button class="product-button" data-hifi-specimen-content="Save">Save</button><output></output></article></section>'
                     '<script id="ui-hifi-manifest" type="application/json">' + json.dumps(manifest) + '</script></body></html>')
            child = ('<html><head>' + css + '</head><body><div data-hifi-canvas data-hifi-targets="390 1200" '
                     'data-hifi-target="390"><main data-ui-surface="UI-002"><h1>Web</h1>'
                     '<p data-hifi-state-view="ready">Ready</p><p data-hifi-state-view="empty" hidden>Empty</p>'
                     '</main></div></body></html>')
            (source / "index.html").write_text(entry, encoding="utf-8")
            (source / "details.html").write_text(child, encoding="utf-8")
            settings = ('<html><head>' + css + '</head><body><div data-hifi-canvas data-hifi-targets="compact regular" '
                        'data-hifi-target="compact"><main data-ui-surface="UI-003"><h1>Settings</h1>'
                        '<p data-hifi-state-view="ready">Ready</p><p data-hifi-state-view="error" hidden>Error</p>'
                        '</main></div></body></html>')
            (source / "settings.html").write_text(settings, encoding="utf-8")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            assemble(manifest_path, [f"index.html={source / 'index.html'}", f"details.html={source / 'details.html'}",
                                     f"settings.html={source / 'settings.html'}"], bundle)
            script = r'''
const {chromium}=require(process.argv[3]);
const {pathToFileURL}=require('url');
(async()=>{
 let browser;
 try {browser=await chromium.launch({channel:'msedge',headless:true});}
 catch (_) {browser=await chromium.launch({headless:true});}
 try {
  const page=await browser.newPage();
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(pathToFileURL(process.argv[2]).href);
  await page.locator('reviewer-shell').waitFor();
  const shell=page.locator('reviewer-shell').locator('aside');
  const style=await shell.evaluate(node=>({width:node.getBoundingClientRect().width,background:getComputedStyle(node).backgroundColor,font:getComputedStyle(node).fontSize}));
  if(style.width!==236||style.background==='rgb(255, 0, 0)'||style.font==='32px')throw Error('product CSS crossed HiFi shell: '+JSON.stringify(style));
  const chrome=async (openPage,asideSelector,controlSelector)=>openPage.locator('reviewer-shell').locator(asideSelector).evaluate((node,selector)=>{
    const sidebar=getComputedStyle(node),control=getComputedStyle(node.querySelector(selector));
    return {width:node.getBoundingClientRect().width,padding:sidebar.padding,font:sidebar.fontFamily,fontSize:sidebar.fontSize,
      lineHeight:sidebar.lineHeight,background:sidebar.backgroundColor,controlPadding:control.padding,
      controlHeight:control.minHeight,controlRadius:control.borderRadius,controlFont:control.fontFamily,controlSize:control.fontSize};
  },controlSelector);
  const hifiChrome=await chrome(page,'aside','[data-hifi-target-control]');
  const wfPage=await browser.newPage();
  await wfPage.goto(pathToFileURL(process.argv[4]).href);
  await wfPage.locator('reviewer-shell').waitFor();
  const wfChrome=await chrome(wfPage,'aside','#responsive-controls button');
  if(JSON.stringify(hifiChrome)!==JSON.stringify(wfChrome))throw Error('WF5 and HiFi3 chrome differs: '+JSON.stringify({hifiChrome,wfChrome}));
  await wfPage.close();
  await page.locator('reviewer-shell').locator('[data-hifi-review-view="overview"]').click();
  const panelStyle=await page.locator('[data-hifi-panel="overview"]').evaluate(node=>({background:getComputedStyle(node).backgroundColor,font:getComputedStyle(node).fontSize}));
  if(panelStyle.background!=='rgb(255, 255, 255)'||panelStyle.font!=='14px')throw Error('product CSS crossed review panel: '+JSON.stringify(panelStyle));
  await page.locator('[data-hifi-state-coverage="UI-001 loading"]').click();
  if(!page.url().endsWith('#hifi-state=UI-001/loading'))throw Error('same-page state link did not create a route');
  if(await page.locator('[data-hifi-state-view="loading"]').isHidden()||!await page.locator('[data-hifi-panel="overview"]').isHidden())
    throw Error('same-page state link did not show the product state');
  if(!await page.locator('[data-ui-surface="UI-001"] h1').evaluate(node=>node===document.activeElement))
    throw Error('same-page state link did not focus the product heading');
  await page.goBack();
  await page.locator('[data-hifi-panel="overview"]').waitFor({state:'visible'});
  if(!page.url().endsWith('#overview'))throw Error('Back did not restore Overview route');
  if(!await page.locator('[data-hifi-panel="overview"] h1').evaluate(node=>node===node.getRootNode().activeElement))
    throw Error('Back did not focus Overview heading');
  await page.goForward();
  await page.locator('[data-hifi-state-view="loading"]').waitFor({state:'visible'});
  if(!page.url().endsWith('#hifi-state=UI-001/loading'))throw Error('Forward did not restore the state route');
  if(!await page.locator('[data-ui-surface="UI-001"] h1').evaluate(node=>node===document.activeElement))
    throw Error('Forward did not focus the product heading');
  await page.reload();
  if(!page.url().endsWith('#hifi-state=UI-001/loading')||await page.locator('[data-hifi-state-view="loading"]').isHidden())
    throw Error('reload did not restore the routed state');
  await page.locator('reviewer-shell').locator('[data-hifi-review-view="overview"]').click();
  await page.locator('[data-hifi-state-coverage="UI-001 ready"]').click();
  if(!page.url().endsWith('#hifi-state=UI-001/ready')||await page.locator('[data-hifi-state-view="ready"]').isHidden())
    throw Error('second same-page state route did not show Ready');
  await page.goBack();
  await page.locator('[data-hifi-panel="overview"]').waitFor({state:'visible'});
  await page.goBack();
  await page.locator('[data-hifi-state-view="loading"]').waitFor({state:'visible'});
  if(!page.url().endsWith('#hifi-state=UI-001/loading')||await page.locator('[data-ui-surface="UI-001"]').getAttribute('data-hifi-state')!=='loading')
    throw Error('Back did not restore the earlier encoded state');
  await page.locator('reviewer-shell').locator('[data-hifi-review-view="design-tokens"]').click();
  await page.waitForFunction(()=>Boolean(document.querySelector('reviewer-panels')?.shadowRoot.querySelector('[data-hifi-spec="token"] output')?.textContent),null,{timeout:3000});
  const tokenText=await page.locator('[data-hifi-spec="token"] output').textContent();
  if(tokenText!=='rgb(12,34,56)')throw Error('product token value was not preserved inside isolated panel: '+tokenText);
  await page.locator('reviewer-shell').locator('[data-hifi-target-control="regular"]').click();
  const responsiveToken=await page.locator('[data-hifi-spec="token"] output').textContent();
  if(responsiveToken!=='rgb(90,80,70)'){
    const values=await page.evaluate(()=>({target:document.querySelector('[data-hifi-canvas]').dataset.hifiTarget,
      product:getComputedStyle(document.querySelector('[data-ui-surface]')).getPropertyValue('--ink'),
      sample:document.querySelector('reviewer-panels').shadowRoot.querySelector('[data-hifi-spec="token"] [data-hifi-specimen-content]').style.getPropertyValue('--ink')}));
    throw Error('responsive product token did not refresh: '+JSON.stringify({responsiveToken,values}));
  }
  if(await page.locator('[data-hifi-spec="component"] [data-hifi-specimen-content]').evaluate(node=>getComputedStyle(node).fontSize)!=='22px')throw Error('responsive component specimen did not refresh');
  const specimenSpacing=await page.locator('[data-hifi-spec="component"] [data-hifi-specimen-content]').evaluate(node=>getComputedStyle(node).letterSpacing);
  if(specimenSpacing!=='3px')throw Error('hidden product container style was not measured at regular width: '+specimenSpacing);
  await page.evaluate(()=>{location.hash=''});
  await page.locator('[data-hifi-canvas]').waitFor({state:'visible'});
  const actualSpacing=await page.locator('[data-hifi-canvas] .product-button').evaluate(node=>getComputedStyle(node).letterSpacing);
  if(actualSpacing!==specimenSpacing)throw Error('token specimen differs from visible product source: '+JSON.stringify({specimenSpacing,actualSpacing}));
  if(await page.locator('input[aria-label="Project"]').inputValue()!=='Retained project')throw Error('review measurement lost product input state');
  await page.locator('reviewer-shell').locator('[data-hifi-review-view="design-tokens"]').click();
  await page.locator('reviewer-shell').locator('[data-hifi-state-control="loading"]').click();
  if(await page.locator('[data-hifi-spec="component"] [data-hifi-specimen-content]').evaluate(node=>getComputedStyle(node).fontWeight)!=='700')throw Error('state component specimen did not refresh');
  await page.locator('reviewer-shell').locator('[data-hifi-target-control="compact"]').click();
  await page.locator('reviewer-shell').locator('[data-hifi-state-control="ready"]').click();
  await page.locator('reviewer-shell').locator('[data-hifi-page-nav] a[href="settings.html"]').click();
  await page.locator('[data-ui-surface="UI-003"]').waitFor();
  await page.locator('reviewer-shell').locator('[data-hifi-target-control="regular"]').click();
  await page.locator('reviewer-shell').locator('[data-hifi-state-control="error"]').click();
  await page.locator('reviewer-shell').locator('[data-hifi-page-nav] a[href="index.html"]').click();
  await page.locator('[data-ui-surface="UI-001"]').waitFor();
  await page.locator('reviewer-shell').locator('[data-hifi-target-control="compact"]').click();
  await page.locator('reviewer-shell').locator('[data-hifi-page-nav] a[href="settings.html"]').click();
  await page.locator('[data-ui-surface="UI-003"]').waitFor();
  if(await page.locator('[data-hifi-canvas]').getAttribute('data-hifi-target')!=='regular'||
     await page.locator('[data-ui-surface="UI-003"]').getAttribute('data-hifi-state')!=='error')
    throw Error('same-platform child selection was overwritten before navigation');
  if(await page.locator('reviewer-shell').locator('[data-hifi-page-nav] a[href="settings.html"]').getAttribute('aria-current')!=='page')
    throw Error('child sidebar current page was lost');
  if(!await page.locator('[data-ui-surface="UI-003"] h1').evaluate(node=>node===document.activeElement))
    throw Error('child product heading did not receive focus');
  await page.goBack();
  await page.locator('[data-ui-surface="UI-001"]').waitFor();
  if(await page.locator('[data-hifi-canvas]').getAttribute('data-hifi-target')!=='compact'||
     await page.locator('[data-ui-surface="UI-001"]').getAttribute('data-hifi-state')!=='ready')
    throw Error('Back did not restore source page selection');
  if(!await page.locator('[data-ui-surface="UI-001"] h1').evaluate(node=>node===document.activeElement))
    throw Error('Back did not focus the source heading');
  await page.locator('reviewer-shell').locator('[data-hifi-review-view="overview"]').click();
  await page.locator('[data-hifi-state-coverage="UI-002 empty"]').click();
  await page.locator('[data-ui-surface="UI-002"]').waitFor();
  if(!page.url().endsWith('details.html#hifi-state=UI-002/empty'))throw Error('cross-page state route changed');
  if(await page.locator('[data-ui-surface="UI-002"]').getAttribute('data-hifi-state')!=='empty')throw Error('state coverage did not open requested child state');
  await page.goto(pathToFileURL(process.argv[2]).href);
  const target=page.locator('reviewer-shell').locator('[data-hifi-target-control="regular"]');
  await target.click();
  if(await page.locator('[data-hifi-canvas]').evaluate(node=>node.getBoundingClientRect().width)!==768)throw Error('regular target width not applied');
  await page.locator('reviewer-shell').locator('[data-hifi-state-control="loading"]').click();
  if(await page.locator('[data-hifi-state-view="loading"]').isHidden()||!await page.locator('[data-hifi-state-view="ready"]').isHidden())throw Error('product state did not switch');
  await page.locator('[data-product-menu]').click();
  await page.locator('[role="menuitem"]').focus();
  await page.keyboard.press('Escape');
  if(await page.locator('[data-product-menu]').getAttribute('aria-expanded')!=='false'||!await page.locator('[data-product-menu]').evaluate(node=>node===document.activeElement))throw Error('menu Escape did not close and return focus');
  await page.locator('[data-product-tab]').last().click();
  if(await page.locator('#tab-two').isHidden()||!await page.locator('#tab-one').isHidden())throw Error('tab did not change product content');
  await page.reload();
  if(await page.locator('[data-hifi-canvas]').getAttribute('data-hifi-target')!=='regular'||await page.locator('[data-ui-surface]').getAttribute('data-hifi-state')!=='loading')throw Error('package/platform review selection not restored');
  await page.locator('reviewer-shell').locator('[data-hifi-page-nav] a[href="details.html"]').click();
  await page.locator('[data-ui-surface="UI-002"]').waitFor();
  if(await page.locator('[data-hifi-canvas]').getAttribute('data-hifi-target')!=='390')throw Error('App target leaked into Web');
  await page.locator('reviewer-shell').locator('[data-hifi-target-control="1200"]').click();
  await page.locator('reviewer-shell').locator('[data-hifi-page-nav] a[href="index.html"]').click();
  await page.locator('[data-ui-surface="UI-001"]').waitFor();
  if(await page.locator('[data-hifi-canvas]').getAttribute('data-hifi-target')!=='regular')throw Error('App target was lost after Web navigation');
  if(errors.length)throw Error(errors.join('\n'));
  console.log(JSON.stringify(style));
 } finally {await browser.close();}
})().catch(error=>{console.error(error.stack);process.exitCode=1});
'''
            result = subprocess.run([node, "-", str(bundle / "index.html"), playwright, str(TEMPLATE)], input=script,
                                    text=True, capture_output=True, timeout=45)
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)

    def test_wireframe_shell_is_isolated_and_selection_survives_reload(self):
        node, playwright = self.require_browser()
        with tempfile.TemporaryDirectory() as temporary:
            page_path = Path(temporary) / "wireframes.html"
            html = TEMPLATE.read_text(encoding="utf-8")
            data_match = re.search(r'(<script id="wireframe-data" type="application/json">)(.*?)(</script>)', html, re.S)
            data = json.loads(data_match.group(2))
            region = data["screens"][0]["regions"][0]
            region["controls"] = {
                "menus": [{"id": "mobile-nav", "label": {"kind": "static", "role": "navigation toggle", "text": "Menu"},
                           "items": [region["actions"][0]["label"]], "targets": ["390"], "defaultOpen": False}],
                "tabs": [{"id": "ready", "label": {"kind": "static", "role": "tab", "text": "Ready"}, "state": "ready"},
                         {"id": "loading", "label": {"kind": "static", "role": "tab", "text": "Loading"}, "state": "loading"}],
            }
            data["flows"][0]["destination"]["state"] = "empty"
            html = html[:data_match.start(2)] + json.dumps(data) + html[data_match.end(2):]
            html = html.replace(
                "</head>",
                '<style>aside{background:rgb(255,0,0)!important;font:32px serif!important}'
                'button{font:32px serif!important}</style></head>',
                1,
            )
            page_path.write_text(html, encoding="utf-8")
            script = r'''
const {chromium}=require(process.argv[3]);
const {pathToFileURL}=require('url');
(async()=>{
  let browser;
  try {browser=await chromium.launch({channel:'msedge',headless:true});}
  catch (_) {browser=await chromium.launch({headless:true});}
  try {
    const page=await browser.newPage();
    const errors=[]; page.on('pageerror',error=>errors.push(error.message));
    await page.goto(pathToFileURL(process.argv[2]).href);
    await page.locator('reviewer-shell').waitFor();
    const shell=page.locator('reviewer-shell').locator('aside');
    const before=await shell.evaluate(node=>({width:node.getBoundingClientRect().width,
      background:getComputedStyle(node).backgroundColor,font:getComputedStyle(node).fontSize}));
    if(before.width!==236||before.background==='rgb(255, 0, 0)'||before.font==='32px')
      throw Error('product CSS crossed shell boundary: '+JSON.stringify(before));
    const controls=page.locator('reviewer-shell').locator('#responsive-controls button');
    if(await controls.count()<2) throw Error('responsive controls missing');
    await controls.first().click();
    const target=await controls.first().getAttribute('aria-pressed');
    if(target!=='true') throw Error('responsive target did not select');
    if(await page.locator('.wireframe').evaluate(node=>node.getBoundingClientRect().width)!==390)throw Error('mobile wireframe target did not render at 390px');
    const toggle=page.locator('.nav-toggle');
    await toggle.focus();await page.keyboard.press('Enter');
    if(await toggle.getAttribute('aria-expanded')!=='true')throw Error('keyboard did not open product menu');
    await page.keyboard.press('ArrowDown');
    if(!await page.locator('.nav-toggle + .action-list button').evaluate(node=>node===document.activeElement))throw Error('menu arrow navigation did not focus action');
    await page.keyboard.press('Escape');
    if(await toggle.getAttribute('aria-expanded')!=='false'||!await toggle.evaluate(node=>node===document.activeElement))throw Error('Escape did not close menu and return focus');
    await page.locator('[data-product-tab="ready"]').focus();
    await page.keyboard.press('ArrowRight');
    if(await page.locator('[data-product-tab="loading"]').getAttribute('aria-selected')!=='true')throw Error('tab arrow did not select loading state');
    if(!await page.locator('#content').textContent().then(value=>value.includes('<Exact loading announcement>')))throw Error('tab did not change product state content');
    if(!await page.locator('[data-product-tab="loading"]').evaluate(node=>node===document.activeElement))throw Error('tab arrow did not restore focus');
    await controls.nth(1).click();
    if(await page.locator('.nav-toggle').count()!==0)throw Error('mobile menu leaked to desktop target');
    if(await page.locator('.wireframe').evaluate(node=>node.getBoundingClientRect().width)!==768)throw Error('desktop wireframe target did not render at 768px');
    await page.locator('reviewer-shell').locator('#responsive-controls button').first().click();
    await page.reload();
    if(await page.locator('reviewer-shell').locator('#responsive-controls button').first().getAttribute('aria-pressed')!=='true')
      throw Error('review target was not restored');
    if(await page.locator('[data-product-tab="loading"]').getAttribute('aria-selected')!=='true')throw Error('product state was not restored');
    await page.locator('[data-product-tab="loading"]').focus();
    await page.keyboard.press('ArrowLeft');
    await page.locator('.nav-toggle').click();
    await page.locator('.nav-toggle + .action-list button').click();
    if(!page.url().endsWith('#UI-002'))throw Error('product menu action did not reach its declared screen');
    if(await page.locator('reviewer-shell').locator('[data-screen-state="empty"]').getAttribute('aria-pressed')!=='true')
      throw Error('product menu action did not land in its declared destination state');
    if(errors.length) throw Error(errors.join('\n'));
    console.log(JSON.stringify(before));
  } finally {await browser.close();}
})().catch(error=>{console.error(error.stack);process.exitCode=1});
'''
            result = subprocess.run(
                [node, "-", str(page_path), playwright],
                input=script,
                text=True,
                capture_output=True,
                timeout=35,
            )
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()

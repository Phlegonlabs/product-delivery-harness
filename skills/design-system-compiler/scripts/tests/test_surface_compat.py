"""ds-showcase/2 Surface plates run the page's own reviewer infrastructure.

Synthetic Kiln Timer fixture with the genuine canonical UI-builder reviewer
runtime and shell plus one minimal product control that selects a state through
the public runtime, as approved products do. Not an approved product. Browser
cases are required when PDH_REQUIRE_BROWSER_TESTS=1.
"""

import base64
import hashlib
import html as html_lib
import json
from pathlib import Path
import re
import sys
import unittest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parents[0]))
sys.path.append(str(TESTS))

import design_system_showcase as showcase  # noqa: E402
import runtime_fixture as fixture  # noqa: E402
import surface_adapter  # noqa: E402
import test_runtime_motion_browser as base  # noqa: E402
from design_system_gallery_assets import FRAME_RUNTIME  # noqa: E402
from test_runtime_motion_browser import HELPERS  # noqa: E402

GO_SCRIPT = ('(function () { document.addEventListener("click", event => { const button = event.target.closest && '
             'event.target.closest("[data-go-state]"); if (button) document.__hifiReviewerRuntime.selectState(button.dataset.goState); }); })();')
GO_BUTTON = '<button type="button" class="go" data-go-state="running">Start firing</button>'
CONNECT = 'connectHifiReviewer({"packageId": "ui-hifi/2:kiln", "page": "index.html", "storage": null})'


def kiln(change=None):
    page = fixture.pages(scripts_after=f"<script>{GO_SCRIPT}</script>")["index.html"]
    page = page.replace('<div class="kiln-side"', GO_BUTTON + '<div class="kiln-side"')
    return {"index.html": change(page) if change else page}


def frames(document):
    return [(attrs, html_lib.unescape(src)) for attrs, src in re.findall(r'<iframe ([^>]*?) srcdoc="([^"]*)"></iframe>', document)]


def markup(frame):
    """Frame markup without script bodies: the genuine runtime text names reviewer selectors."""
    return re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "<script></script>", frame)


def digest(script):
    return "'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"


def findings(page_set):
    manifest = json.loads(showcase.MANIFEST_RE.search(page_set["index.html"]).group("data"))
    trees = {name: showcase.SourceTree(html) for name, html in page_set.items()}
    return "\n".join(surface_adapter.resolve_surfaces(trees, manifest)[1])


class SurfaceStaticTests(unittest.TestCase):
    def test_surface_plate_carries_hidden_source_controls_and_one_public_connect(self):
        document = fixture.render(kiln())
        surface = [src for attrs, src in frames(document) if "data-ds-surface-frame" in attrs]
        self.assertEqual(1, len(surface))
        frame = surface[0]
        box = re.search(r'<div data-ds-reviewer-infrastructure hidden inert aria-hidden="true" style="display:none!important">'
                        r"([\s\S]*?)</div><script>", frame)
        self.assertIsNotNone(box)
        self.assertLess(frame.index("</section>"), box.start(), "outside the copied product surface")
        controls = box.group(1)
        for needle in ('data-hifi-state-control="ready"', 'data-hifi-state-control="running"', 'data-hifi-target-control="390"',
                       'data-hifi-target-control="768"', "<nav data-hifi-page-nav"):
            self.assertIn(needle, controls)
        for absent in ("data-hifi-reviewer-shell", "data-hifi-review-view", "data-hifi-panel", "data-hifi-reviewer-css", "Design Tokens"):
            self.assertNotIn(absent, markup(frame), "no reviewer shell root, views, panels or reviewer CSS")
        self.assertEqual(1, frame.count("connectHifiReviewer({"))
        self.assertIn(f"<script>{CONNECT}</script>", frame)
        self.assertNotIn('<script>connectHifiReviewer({"packageId": "ui-hifi/2:kiln"})</script>', frame)
        self.assertLess(frame.index('id="hifi-reviewer-runtime"') if 'id="hifi-reviewer-runtime"' in frame else frame.index("function connectHifiReviewer"),
                        frame.index(CONNECT))
        self.assertLess(box.end(), frame.index(CONNECT), "connect runs after the required markup exists")
        self.assertLess(frame.index(CONNECT), frame.index(surface_adapter.SURFACE_FRAME))
        self.assertNotIn(FRAME_RUNTIME, frame, "no legacy direct showState or target writes")
        self.assertIn('"kind": "surface", "state": "ready", "surface": "UI-001", "target": "390"', frame)
        policy = html_lib.unescape(re.search(r'Content-Security-Policy" content="([^"]+)"', document).group(1))
        for script in (surface_adapter.SURFACE_FRAME, surface_adapter.SURFACE_GALLERY, CONNECT, GO_SCRIPT):
            self.assertIn(digest(script), policy)
        self.assertIn("connect-src 'none'", policy)
        self.assertIn(f"<script>{surface_adapter.SURFACE_GALLERY}</script>", document)
        self.assertRegex(document, r'<iframe data-ds-frame="plate-\d+" data-ds-surface-frame title="UI-001 live surface" sandbox="allow-scripts" ')

    def test_component_and_motion_plates_stay_reviewer_free(self):
        for attrs, frame in frames(fixture.render(kiln())):
            if "data-ds-surface-frame" in attrs:
                continue
            with self.subTest(attrs[:40]):
                self.assertNotIn("data-ds-reviewer-infrastructure", frame)
                self.assertNotIn("connectHifiReviewer({", frame)
                self.assertNotIn(surface_adapter.SURFACE_FRAME, frame)
                self.assertNotIn("data-hifi-state-control", markup(frame))
                self.assertNotIn("data-hifi-page-nav", markup(frame))

    def test_missing_duplicate_wrong_and_unsupported_infrastructure_fail_closed(self):
        running = '<button type="button" data-hifi-state-control="running" data-hifi-state-surface="UI-001" aria-pressed="false">running</button>'
        target = '<button type="button" data-hifi-target-control="768" aria-pressed="false">768px</button>'
        call = '<script>connectHifiReviewer({"packageId": "ui-hifi/2:kiln"})</script>'
        cases = {
            "missing state": (lambda p: p.replace(running, ""), "state controls must be enabled buttons"),
            "duplicate state": (lambda p: p.replace(running, running * 2), "state controls must be enabled buttons"),
            "disabled state": (lambda p: p.replace(running, running.replace('type="button"', 'type="button" disabled')), "state controls"),
            "wrong surface": (lambda p: p.replace(running, running.replace("UI-001", "UI-009")), "state controls"),
            "missing target": (lambda p: p.replace(target, ""), "target controls must be enabled buttons"),
            "invented target": (lambda p: p.replace(target, target + target.replace("768", "1024")), "target controls"),
            "missing page nav": (lambda p: re.sub(r"<nav data-hifi-page-nav[\s\S]*?</nav>", "", p), "data-hifi-page-nav"),
            "wrong page metadata": (lambda p: p.replace('<a href="index.html" aria-current="page">', '<a href="other.html">'), "page navigation"),
            "controls inside product": (lambda p: p.replace('<div data-hifi-state-view="ready" data-responsive-target="390">',
                                                            '<div data-hifi-state-view="ready" data-responsive-target="390"><nav data-hifi-page-nav></nav>', 1),
                                        "exactly one data-hifi-page-nav"),
            "unsupported connector": (lambda p: p.replace("const TARGET_KEY", "window.extra = 1; const TARGET_KEY", 1), "supported public reviewer runtime"),
            "missing connect": (lambda p: p.replace(call, ""), "found 0"),
            "duplicate connect": (lambda p: p.replace(call, call * 2), "found 2"),
            "code in connect": (lambda p: p.replace(call, "<script>connectHifiReviewer({storage: window.localStorage})</script>"),
                                "closed literal packageId"),
            "call in connect": (lambda p: p.replace(call, '<script>connectHifiReviewer({"packageId": String(1)})</script>'),
                                "not the supported public call shape"),
            "open connect options": (lambda p: p.replace(call, '<script>connectHifiReviewer({"packageId": "k", "root": "x"})</script>'),
                                     "closed literal packageId"),
        }
        self.assertEqual("", findings(kiln()))
        for label, (change, expected) in cases.items():
            with self.subTest(label):
                page_set = kiln(change)
                self.assertNotEqual(page_set, kiln(), "the mutation applies")
                self.assertIn(expected, findings(page_set))
                with self.assertRaisesRegex(ValueError, re.escape(expected)):
                    fixture.render(page_set)

    def test_supported_runtime_pin_is_the_canonical_template_runtime(self):
        body = re.search(r'<script id="hifi-reviewer-runtime">([\s\S]*?)</script>', fixture.REVIEWER_RUNTIME).group(1)
        self.assertIn(hashlib.sha256(body.encode()).hexdigest(), surface_adapter.SUPPORTED_REVIEWER_RUNTIMES)

    def test_legacy_schema_one_and_committed_demo_bytes_are_unchanged(self):
        from showcase_fixture import DEMO_DIR, render_demo

        legacy = render_demo()[0]
        self.assertEqual((DEMO_DIR / "design-system-preview.html").read_bytes(), legacy.encode("utf-8"))
        for marker in ("data-ds-surface-frame", "data-ds-reviewer-infrastructure", surface_adapter.SURFACE_GALLERY[:60]):
            self.assertNotIn(marker, legacy)

    def test_renderer_receipt_names_the_adapter_module(self):
        import verify_runtime_motion

        self.assertIn("surface_adapter.py", verify_runtime_motion.RENDERER_MODULES)


SURFACE = HELPERS + r"""
(async () => {
  const browser = await chromium.launch();
  const r = {};
  try {
    const context = await browser.newContext({viewport: {width: 1280, height: 800}});
    const page = await context.newPage();
    watch(context, page, r);
    await page.goto(cases.url);
    await page.waitForTimeout(1200);
    r.loadFocus = await page.evaluate(() => [document.activeElement && document.activeElement.tagName, Math.round(window.scrollY)]);
    const plate = "#s-ui-001 + figure";
    await page.$eval(plate, item => item.scrollIntoView({block: "start"}));
    await page.focus("a.skip");
    const frame = await (await page.$(plate + " iframe")).contentFrame();
    const status = () => page.$eval(plate + " .status", item => item.textContent);
    const gallery = () => page.$eval(plate, figure => [figure.querySelector("select").value,
      Array.from(figure.querySelectorAll("button[data-ds-target]")).filter(item => item.getAttribute("aria-pressed") === "true").map(item => item.dataset.dsTarget)]);
    const source = () => frame.evaluate(() => {
      const snap = document.__hifiReviewerRuntime.snapshot();
      const view = Array.from(document.querySelectorAll("[data-hifi-state-view]")).filter(item => !item.hidden).map(item => item.dataset.hifiStateView + "@" + item.dataset.responsiveTarget);
      const canvas = document.querySelector("[data-hifi-canvas]");
      return [snap.productState, snap.target, view, canvas.getAttribute("data-hifi-target"), canvas.style.width];
    });
    const settle = () => page.waitForTimeout(350);
    await settle();
    r.initial = [await gallery(), await source(), await status()];
    r.infra = await frame.evaluate(() => {
      const box = document.querySelector("[data-ds-reviewer-infrastructure]");
      return [getComputedStyle(box).display, box.inert, box.getAttribute("aria-hidden"), box.closest("[data-ui-surface]") === null,
        document.querySelectorAll("reviewer-shell, reviewer-stage, reviewer-panels, [data-hifi-reviewer-shell]").length];
    });
    r.aria = await frame.locator("body").ariaSnapshot();
    await page.selectOption(plate + " select", "running"); await settle();
    r.focusAfterSelect = await page.evaluate(() => document.activeElement && document.activeElement.tagName);
    r.selected = [await gallery(), await source()];
    r.counting = [await frame.evaluate(() => document.querySelector("[data-hifi-state-view]:not([hidden]) .belt-count").textContent)];
    await page.waitForTimeout(1300);
    r.counting.push(await frame.evaluate(() => document.querySelector("[data-hifi-state-view]:not([hidden]) .belt-count").textContent));
    await page.click(plate + ' button[data-ds-target="768"]'); await settle();
    r.wide = [await gallery(), await source()];
    await page.$eval(plate + " input[type=range]", item => { item.value = "600"; item.dispatchEvent(new Event("input", {bubbles: true})); }); await settle();
    r.between = [await gallery(), await source(), await page.$eval(plate + " iframe", item => item.style.width)];
    await page.click(plate + ' button[data-ds-target="390"]'); await settle();
    await page.focus(plate + " select"); await page.keyboard.press("ArrowUp"); await settle();
    r.keyboardSelect = [await gallery(), await source()];
    await frame.click("[data-hifi-state-view]:not([hidden]) .go"); await settle();
    r.productClick = [await gallery(), await source(), await status()];
    await page.selectOption(plate + " select", "ready"); await settle();
    await frame.focus("[data-hifi-state-view]:not([hidden]) .go"); await page.keyboard.press("Enter"); await settle();
    r.productKey = [await gallery(), await source()];
    await page.selectOption(plate + " select", "ready"); await settle();
    const tabbed = [];
    await frame.focus("[data-hifi-state-view]:not([hidden]) h1").catch(() => {});
    for (let i = 0; i < 8; i++) { await page.keyboard.press("Tab"); tabbed.push(await frame.evaluate(() => {
      const item = document.activeElement; return item ? (item.closest("[data-ds-reviewer-infrastructure]") ? "INFRA" : item.tagName) : null; })); }
    r.tabbed = tabbed;
    await frame.click("[data-hifi-state-view]:not([hidden]) input.field");
    r.userFocus = await frame.evaluate(() => { const h = document.querySelector("[data-hifi-state-view]:not([hidden]) h1");
      h.setAttribute("tabindex", "-1"); h.focus(); return document.activeElement === h; });
    const motion = await (await page.$("#m-kiln-rise + figure iframe")).contentFrame();
    await motion.evaluate(() => { for (let i = 0; i < parent.frames.length; i++) {
      parent.frames[i].postMessage({type: "ds-state", state: "running"}, "*");
      parent.postMessage({type: "ds-surface", id: "plate-999", state: "running", target: "768", error: ""}, "*"); } });
    const id = await page.$eval(plate + " iframe", item => item.dataset.dsFrame);
    await motion.evaluate(plate => parent.postMessage({type: "ds-surface", id: plate, state: "running", target: "768", error: "forged"}, "*"), id);
    await settle();
    r.foreign = [await gallery(), await source(), await status()];
    await frame.click('[data-hifi-state-view]:not([hidden]) a[href="log.html"]'); await settle();
    r.contained = [frame.url(), await status()];
    r.motionClean = await motion.evaluate(() => [Boolean(document.__hifiReviewerRuntime), document.querySelectorAll("[data-ds-reviewer-infrastructure]").length]);
  } finally { console.log(JSON.stringify(r)); await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
"""


class SurfaceBrowserTests(unittest.TestCase):
    setUpClass = classmethod(base.RuntimeBrowserTests.setUpClass.__func__)
    tearDownClass = classmethod(base.RuntimeBrowserTests.tearDownClass.__func__)
    require, run_node = base.RuntimeBrowserTests.require, base.RuntimeBrowserTests.run_node

    def test_gallery_and_product_operations_share_one_source_runtime(self):
        self.require()
        path = self.folder / "surface.html"
        path.write_text(fixture.render(kiln(), fixture.registry()), encoding="utf-8")
        r = self.run_node(SURFACE, {"url": path.resolve().as_uri()})
        self.assertEqual(([], [], []), (r["errors"], r["requests"], r["popups"]))
        self.assertEqual([["ready", ["390"]], ["ready", "390", ["ready@390"], "390", ""]], r["initial"][:2])
        self.assertIn("Source state ready at approved target 390.", r["initial"][2])
        self.assertEqual(["none", True, "true", True, 0], r["infra"], "hidden, inert, outside product, no reviewer chrome")
        for absent in ("Product screens", "Responsive target", "Product state", "768px"):
            self.assertNotIn(absent, r["aria"])
        self.assertEqual("A", r["focusAfterSelect"], "a gallery command never moves gallery focus into the frame")
        self.assertEqual(["BODY", 0], r["loadFocus"], "loading never moves gallery focus or scroll into a plate")
        self.assertTrue(r["userFocus"], "a user operation inside the plate keeps the source focus behavior")
        self.assertEqual([["running", ["390"]], ["running", "390", ["running@390"], "390", ""]], r["selected"])
        self.assertGreater(int(r["counting"][1]), int(r["counting"][0]), "the real product run started")
        self.assertEqual([["running", ["768"]], ["running", "768", ["running@768"], "768", ""]], r["wide"])
        self.assertEqual([["running", []], ["running", "390", ["running@390"], "390", "600px"], "600px"], r["between"],
                         "an intermediate width keeps the approved 390 identity")
        self.assertEqual([["ready", ["390"]], ["ready", "390", ["ready@390"], "390", ""]], r["keyboardSelect"])
        self.assertEqual([["running", ["390"]], ["running", "390", ["running@390"], "390", ""]], r["productClick"][:2])
        self.assertIn("Source state running", r["productClick"][2])
        self.assertEqual([["running", ["390"]], ["running", "390", ["running@390"], "390", ""]], r["productKey"])
        self.assertNotIn("INFRA", r["tabbed"])
        self.assertEqual(["ready", ["390"]], r["foreign"][0], "sibling and forged messages are ignored")
        self.assertEqual("ready", r["foreign"][1][0])
        self.assertNotIn("forged", r["foreign"][2])
        self.assertEqual("about:srcdoc", r["contained"][0])
        self.assertIn("Product link to log.html", r["contained"][1])
        self.assertEqual([False, 0], r["motionClean"])


if __name__ == "__main__":
    unittest.main()

"""ds-showcase/2 Surface plates deny the clipboard before any product script runs.

Synthetic Kiln Timer fixture with one product copy control whose own rejection
path selects a state through the public runtime. Not an approved product.
Browser cases are required when PDH_REQUIRE_BROWSER_TESTS=1. The browser cases
install a labelled native Clipboard API spy: it counts native method calls to
verify the denial. It never reads the operating-system clipboard and proves
nothing about it.
"""

import base64
import hashlib
from html import escape
import html as html_lib
from pathlib import Path
import re
import sys
import unittest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parents[0]))
sys.path.append(str(TESTS))

import runtime_fixture as fixture  # noqa: E402
import source_script_order as script_order  # noqa: E402
import surface_adapter  # noqa: E402
import test_runtime_motion_browser as base  # noqa: E402
from test_runtime_motion_browser import HELPERS  # noqa: E402

GUARD = surface_adapter.SURFACE_CLIPBOARD_GUARD
COPY_BUTTON = '<button type="button" class="copy" data-copy-url="https://kiln.example/r/14">Copy firing link</button>'
# Product-owned feedback: a rejection selects another state through the public runtime, as approved products do.
COPY_SCRIPT = ('(function () { window.__copies = []; document.addEventListener("click", function (event) { '
               'var button = event.target.closest && event.target.closest("[data-copy-url]"); if (!button) return; var p; '
               'try { p = navigator.clipboard.writeText(button.dataset.copyUrl); } catch (error) { window.__copies.push("threw " + error.name); return; } '
               'p.then(function () { window.__copies.push("copied"); }, function (error) { window.__copies.push(error.name + ": " + error.message); '
               'var runtime = document.__hifiReviewerRuntime; if (runtime) runtime.selectState("running"); }); }); })();')
CONNECT = 'connectHifiReviewer({"packageId": "ui-hifi/2:kiln", "page": "index.html", "storage": null})'
# Fail-closed tamper: a context whose clipboard property is already locked to the native getter.
LOCKED = 'Object.defineProperty(Navigator.prototype, "clipboard", {configurable: false});' + GUARD


def kiln():
    page = fixture.pages(scripts_after=f"<script>{COPY_SCRIPT}</script>")["index.html"]
    return {"index.html": page.replace('<div class="kiln-side"', COPY_BUTTON + '<div class="kiln-side"')}


def frames(document):
    return [(attrs, html_lib.unescape(src)) for attrs, src in re.findall(r'<iframe ([^>]*?) srcdoc="([^"]*)"></iframe>', document)]


def token(script):
    return "sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()


class CapabilityStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = fixture.render(kiln(), fixture.registry())
        cls.frames = frames(cls.document)

    def surface(self):
        found = [frame for attrs, frame in self.frames if "data-ds-surface-frame" in attrs]
        self.assertEqual(1, len(found))
        return found[0]

    def test_guard_runs_once_in_the_surface_head_before_every_other_plate_script(self):
        frame = self.surface()
        self.assertEqual(1, frame.count(GUARD))
        guard = frame.index(f"<script>{GUARD}</script>")
        self.assertLess(guard, frame.index("</head>"))
        scripts = [match.start() for match in re.finditer(r"<script(?:>| type=\"text/x-ds-source-slot\")", frame)]
        self.assertEqual([guard], [offset for offset in scripts if offset >= guard][:1])
        self.assertEqual([frame.index(f"<script>{surface_adapter.SURFACE_FOCUS_GUARD}</script>")],
                         [offset for offset in scripts if offset < guard], "only the pinned focus guard runs earlier")
        definitions = re.search(r"<script[^>]*>([\s\S]*?)</script>", fixture.REVIEWER_RUNTIME).group(1)
        for later in (definitions, CONNECT, surface_adapter.SURFACE_FRAME, script_order.LOADER):
            self.assertLess(guard, frame.index(later))
        self.assertLess(guard, frame.index('<script type="text/x-ds-source-slot"'), "before every product slot")

    def test_guard_is_surface_only(self):
        kinds = set()
        for attrs, frame in self.frames:
            if "data-ds-surface-frame" in attrs:
                continue
            kinds.add("runtime" if "data-ds-runtime-frame" in attrs else "component")
            with self.subTest(attrs[:40]):
                self.assertNotIn(GUARD, frame)
        self.assertEqual({"runtime", "component"}, kinds)
        self.assertNotIn(f"<script>{GUARD}</script>", self.document, "the gallery document never runs the guard")
        self.assertEqual(1, self.document.count(escape(GUARD, quote=True)))

    def test_policy_pins_the_guard_and_the_sandbox_stays_closed(self):
        policy = html_lib.unescape(re.search(r'Content-Security-Policy" content="([^"]+)"', self.document).group(1))
        self.assertIn(f"'{token(GUARD)}'", policy)
        self.assertIn("connect-src 'none'", policy)
        self.assertNotIn("unsafe-eval", policy)
        self.assertNotIn("'unsafe-inline'", policy.split("script-src", 1)[1])
        for attrs in re.findall(r"<iframe ([^>]*?) srcdoc=", self.document):
            with self.subTest(attrs[:40]):
                self.assertIn('sandbox="allow-scripts"', attrs)
                self.assertNotIn(" allow=", attrs, "no permissions delegation")

    def test_product_bodies_stay_unchanged_source_slots(self):
        frame = self.surface()
        bodies = re.findall(r'<script type="text/x-ds-source-slot" data-ds-source-slot="\d+">([\s\S]*?)</script>', frame)
        self.assertEqual([fixture.PRODUCT_SCRIPT, COPY_SCRIPT], bodies)
        self.assertEqual(1, frame.count(COPY_SCRIPT))
        self.assertNotIn(f"<script>{COPY_SCRIPT}</script>", frame, "no unguarded executable copy")
        self.assertIn(COPY_BUTTON, frame)

    def test_denial_is_fixed_frozen_and_never_reaches_the_native_api(self):
        self.assertIn('new DOMException("The design-system Surface plate denies clipboard access.", "NotAllowedError")', GUARD)
        self.assertIn("Object.freeze({read: deny, readText: deny, write: deny, writeText: deny})", GUARD)
        self.assertIn('Object.defineProperty(Navigator.prototype, "clipboard", {configurable: false', GUARD)
        for absent in ("Clipboard.prototype", "getOwnPropertyDescriptor", ".call(", ".apply(", "console", "resolve("):
            self.assertNotIn(absent, GUARD, "the guard keeps no native reference and never reports success")
        self.assertIn('error = !denied ? "the clipboard denial is not established"', surface_adapter.SURFACE_FRAME)
        self.assertIn('document.getElementById("ds-source-order"); if (order) order.remove();', surface_adapter.SURFACE_FRAME)

    def test_legacy_schema_one_and_committed_demo_bytes_are_unchanged(self):
        from showcase_fixture import DEMO_DIR, render_demo

        legacy = render_demo()[0]
        self.assertEqual((DEMO_DIR / "design-system-preview.html").read_bytes(), legacy.encode("utf-8"))
        self.assertNotIn(token(GUARD), legacy)
        self.assertNotIn(escape(GUARD, quote=True), legacy)


SPY = r"""
// DENIAL-VERIFICATION SPY (test instrumentation): counts native Clipboard API method calls in every frame.
// It forwards each call unchanged and never reads the operating-system clipboard.
const SPY = () => {
  window.__nativeClipboardCalls = 0;
  if (typeof Clipboard !== "function") return;
  for (const name of ["read", "readText", "write", "writeText"]) {
    const native = Clipboard.prototype[name];
    if (typeof native === "function") Clipboard.prototype[name] = function (...args) { window.__nativeClipboardCalls += 1; return native.apply(this, args); };
  }
};
"""

CAPABILITY = HELPERS + SPY + r"""
const PLATE = "#s-ui-001 + figure";
(async () => {
  const browser = await chromium.launch();
  const out = {};
  try {
    for (const item of cases.items) {
      const context = await browser.newContext({viewport: {width: 1280, height: 800}});
      await context.addInitScript(SPY);
      const r = out[item.name] = {};
      try {
        const page = await context.newPage();
        watch(context, page, r);
        await page.goto(item.url);
        await page.waitForTimeout(1200);
        await page.$eval(PLATE, node => node.scrollIntoView({block: "start"}));
        const frame = await (await page.$(PLATE + " iframe")).contentFrame();
        const settle = () => page.waitForTimeout(350);
        const status = () => page.$eval(PLATE + " .status", node => node.textContent);
        const read = () => frame.evaluate(() => ({spy: window.__nativeClipboardCalls, copies: window.__copies || null,
          state: document.__hifiReviewerRuntime ? document.__hifiReviewerRuntime.snapshot().productState : null,
          view: Array.from(document.querySelectorAll("[data-hifi-state-view]")).filter(v => !v.hidden).map(v => v.dataset.hifiStateView + "@" + v.dataset.responsiveTarget),
          pending: document.querySelectorAll('script[type="text/x-ds-source-slot"]').length, inventory: Boolean(document.getElementById("ds-source-order"))}));
        const gallery = () => page.$eval(PLATE, f => f.querySelector("select").value);
        const copy = "[data-hifi-state-view]:not([hidden]) .copy";
        await settle();
        r.status = await status();
        r.initial = await read();
        if (!item.full) {
          await frame.click(copy); await settle();
          r.afterClick = await read();
          continue;
        }
        r.denial = await frame.evaluate(async () => {
          const held = Object.getOwnPropertyDescriptor(Navigator.prototype, "clipboard"), board = navigator.clipboard;
          let redefine = "allowed"; try { Object.defineProperty(Navigator.prototype, "clipboard", {value: null}); } catch (error) { redefine = error.name; }
          try { board.writeText = null; } catch (_) {}
          const names = [];
          for (const name of ["read", "readText", "write", "writeText"]) await board[name]("x").then(() => names.push("resolved"), error => names.push(error.name));
          return {configurable: held.configurable, setter: Boolean(held.set), frozen: Object.isFrozen(board), methodFrozen: Object.isFrozen(board.writeText),
            native: typeof Clipboard === "function" && board instanceof Clipboard, same: navigator.clipboard === board, redefine,
            writeText: typeof board.writeText, names, spy: window.__nativeClipboardCalls, spyInstalled: typeof window.__nativeClipboardCalls === "number"};
        });
        r.actions = [];
        for (const [mode, width] of [["click", "390"], ["Enter", "390"], [" ", "390"], ["click", "768"]]) {
          await page.click(PLATE + ' button[data-ds-target="' + width + '"]'); await settle();
          await page.selectOption(PLATE + " select", "ready"); await settle();
          if (mode === "click") await frame.click(copy); else { await frame.focus(copy); await page.keyboard.press(mode); }
          await settle();
          r.actions.push({mode, width, gallery: await gallery(), status: await status(), frame: await read()});
        }
        // Positive control: the motion plate has no guard, so the same product control reaches the native API.
        const before = r.errors.length;
        const motion = await (await page.$("#m-kiln-rise + figure iframe")).contentFrame();
        await page.$eval("#m-kiln-rise + figure", node => node.scrollIntoView({block: "center"})); await settle();
        await motion.click(copy); await page.waitForTimeout(600);
        r.control = await motion.evaluate(() => ({spy: window.__nativeClipboardCalls, copies: window.__copies,
          native: typeof Clipboard === "function" && navigator.clipboard instanceof Clipboard}));
        r.controlErrors = r.errors.splice(before);
      } finally { await context.close(); }
    }
  } finally { console.log(JSON.stringify(out)); await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
"""

DENIED = "NotAllowedError: The design-system Surface plate denies clipboard access."


class CapabilityBrowserTests(unittest.TestCase):
    setUpClass = classmethod(base.RuntimeBrowserTests.setUpClass.__func__)
    tearDownClass = classmethod(base.RuntimeBrowserTests.tearDownClass.__func__)
    require, run_node = base.RuntimeBrowserTests.require, base.RuntimeBrowserTests.run_node

    def book(self, name, tamper=None, **extra):
        document = fixture.render(kiln(), fixture.registry())
        if tamper:
            changed = tamper(document)
            self.assertNotEqual(document, changed, "the tamper applies")
            document = changed
        path = self.folder / f"capability-{name}.html"
        path.write_text(document, encoding="utf-8")
        return dict(name=name, url=path.resolve().as_uri(), **extra)

    def test_product_copy_meets_the_denial_and_owns_its_feedback(self):
        self.require()
        r = self.run_node(CAPABILITY, {"items": [self.book("exact", full=True)]})["exact"]
        self.assertEqual(([], [], []), (r["errors"], r["requests"], r["popups"]), "no clipboard console error, network or popup")
        self.assertIn("Source state ready at approved target 390.", r["status"])
        self.assertEqual({"spy": 0, "copies": [], "state": "ready", "view": ["ready@390"], "pending": 0, "inventory": True}, r["initial"])
        self.assertEqual({"configurable": False, "setter": False, "frozen": True, "methodFrozen": True, "native": False, "same": True,
                          "redefine": "TypeError", "writeText": "function", "names": ["NotAllowedError"] * 4, "spy": 0,
                          "spyInstalled": True}, r["denial"])
        for index, action in enumerate(r["actions"]):
            with self.subTest(action["mode"] + "@" + action["width"]):
                frame = action["frame"]
                self.assertEqual(0, frame["spy"], "the native clipboard API is never called")
                self.assertEqual([DENIED] * (index + 1), frame["copies"], "one rejection per operation: no duplicate handler")
                self.assertEqual(["running", ["running@" + action["width"]]], [frame["state"], frame["view"]])
                self.assertEqual("running", action["gallery"])
                self.assertIn(f"Source state running at approved target {action['width']}.", action["status"])
        self.assertTrue(r["control"]["native"], "the motion plate keeps the native clipboard")
        self.assertGreaterEqual(r["control"]["spy"], 1, "the spy counts a real native call")
        self.assertEqual(1, len(r["control"]["copies"]))
        self.assertNotIn("design-system Surface plate", r["control"]["copies"][0])

    def test_missing_or_unestablished_denial_fails_closed_before_product_activation(self):
        self.require()
        guard = escape(f"<script>{GUARD}</script>", quote=True)
        locked = lambda d: d.replace(guard, escape(f"<script>{LOCKED}</script>", quote=True)).replace(token(GUARD), token(LOCKED))  # noqa: E731
        out = self.run_node(CAPABILITY, {"items": [self.book("missing", lambda d: d.replace(guard, "")), self.book("locked", locked)]})
        for name in ("missing", "locked"):
            with self.subTest(name):
                r = out[name]
                self.assertIn("Surface unavailable: the clipboard denial is not established", r["status"])
                self.assertEqual({"spy": 0, "copies": None, "state": "ready", "view": ["ready@390"], "pending": 2, "inventory": False},
                                 r["initial"], "no product script ran")
                self.assertEqual(r["initial"], r["afterClick"], "an unguarded product control has no handler and makes no native call")
                self.assertEqual(([], []), (r["requests"], r["popups"]))
        self.assertEqual([], out["missing"]["errors"])
        self.assertTrue(out["locked"]["errors"] and all("Cannot redefine property: clipboard" in text for text in out["locked"]["errors"]),
                        out["locked"]["errors"])


if __name__ == "__main__":
    unittest.main()

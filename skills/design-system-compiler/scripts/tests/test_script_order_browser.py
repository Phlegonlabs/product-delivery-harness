"""Chromium behavior of ds-showcase/2 source script order.

Synthetic Kiln Timer fixture with recording scripts, not an approved product.
Required when PDH_REQUIRE_BROWSER_TESTS=1. Each source occurrence runs once,
natively, in source order, after the plate bootstrap, with its source
currentScript context. Tampered plates (missing or repeated slots, a refused
or throwing script) fail closed visibly.
"""

import base64
import hashlib
from html import escape
from pathlib import Path
import sys
import unittest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parents[0]))
sys.path.append(str(TESTS))

import runtime_fixture as fixture  # noqa: E402
import source_script_order as script_order  # noqa: E402
import test_runtime_motion_browser as base  # noqa: E402
from test_runtime_motion_browser import HELPERS  # noqa: E402
from test_script_order_static import FOCUS, RECORD, ordered_pages  # noqa: E402

ORDER = HELPERS + r"""
const SURFACE = "#s-ui-001 + figure";
(async () => {
  const browser = await chromium.launch();
  const out = {};
  try {
    for (const item of cases.items) {
      const context = await browser.newContext({viewport: {width: 1280, height: 800}});
      try {
        const page = await context.newPage();
        const r = {};
        watch(context, page, r);
        await page.goto(item.url);
        await page.waitForTimeout(1000);
        const {status, frame, wait, show} = tools(page);
        const read = f => f.evaluate(() => ({order: window.__order || [], focused: window.__focused || [], clicks: window.__clicks || 0,
          pending: document.querySelectorAll('script[type="text/x-ds-source-slot"]').length, scripts: document.scripts.length,
          template: window.__template || 0, inert: document.getElementById("inert-data") ? document.getElementById("inert-data").type : null}));
        r.load = await page.evaluate(() => [document.activeElement && document.activeElement.tagName, Math.round(window.scrollY)]);
        r.surfaceStatus = await page.$eval(SURFACE + " .status", node => node.textContent);
        const surface = await (await page.$(SURFACE + " iframe")).contentFrame();
        r.surface = await read(surface);
        if (item.full) {
          await page.$eval(SURFACE, node => node.scrollIntoView({block: "start"}));
          await surface.click("[data-hifi-state-view]:not([hidden]) h1"); await page.waitForTimeout(250);
          r.clicked = await read(surface);
          for (const variant of ["belt-step", "kiln-rise"]) {
            await show(variant);
            r[variant] = {phase: await wait(variant, ["settled", "invalid"], 9000), frame: await read(await frame(variant))};
          }
          await page.$eval(fig("belt-step") + ' button[data-ds-runtime-target="768"]', node => node.click());
          await show("belt-step");
          r.wide = {phase: await wait("belt-step", ["settled", "invalid"], 9000), frame: await read(await frame("belt-step"))};
        } else {
          await show("kiln-rise");
          r.motion = await wait("kiln-rise", ["invalid", "settled"], 6000);
          r.motionStatus = await status("kiln-rise");
          r.motionFrame = await read(await frame("kiln-rise"));
        }
        out[item.name] = r;
      } finally { await context.close(); }
    }
  } finally { console.log(JSON.stringify(out)); await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
"""


def token(script):
    return "sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()


def entry(parent, prev, next_, view, target, pending, runtime):
    return {"parent": parent, "prev": prev, "next": next_, "attrs": 0, "own": len(RECORD), "view": view, "target": target,
            "inert": 'application/json {"kind": "inert"}', "pending": pending, "runtime": runtime}


class ScriptOrderBrowserTests(unittest.TestCase):
    setUpClass = classmethod(base.RuntimeBrowserTests.setUpClass.__func__)
    tearDownClass = classmethod(base.RuntimeBrowserTests.tearDownClass.__func__)
    require, run_node = base.RuntimeBrowserTests.require, base.RuntimeBrowserTests.run_node

    def book(self, name, page_set=None, tamper=None):
        document = fixture.render(page_set or ordered_pages(), fixture.registry())
        if tamper:
            changed = tamper(document)
            self.assertNotEqual(document, changed, "the tamper applies")
            document = changed
        path = self.folder / f"order-{name}.html"
        path.write_text(document, encoding="utf-8")
        return {"name": name, "url": path.resolve().as_uri()}

    def test_each_occurrence_runs_once_in_source_order_with_its_source_context(self):
        self.require()
        out = self.run_node(ORDER, {"items": [dict(self.book("exact"), full=True)]})["exact"]
        self.assertEqual(([], [], []), (out["errors"], out["requests"], out["popups"]))
        self.assertEqual(["BODY", 0], out["load"], "loading never moves gallery focus or scroll")
        self.assertIn("Source state ready at approved target 390.", out["surfaceStatus"])
        surface = out["surface"]
        self.assertEqual([entry("body", None, "main", "ready@390", "390", 5, True),
                          entry("section[surface]", "ready@390", "script", "ready@390", "390", 4, True),
                          entry("section[surface]", "running@390", "running@768", "ready@390", "390", 2, True)], surface["order"],
                         "source parent, siblings and order, after connect and source-control selection, with the DOM complete")
        self.assertEqual(["ready@390"], surface["focused"], "the focus script ran once on the selected state and target")
        self.assertEqual([0, 0, "application/json"], [surface["pending"], surface["template"], surface["inert"]])
        self.assertEqual(1, out["clicked"]["clicks"], "one click reaches one handler: no duplicate execution")
        self.assertEqual(3, len(out["clicked"]["order"]))
        for variant, view in (("belt-step", "running@390"), ("kiln-rise", "ready@390")):
            with self.subTest(variant):
                motion = out[variant]
                self.assertEqual("settled", motion["phase"][-1], motion)
                self.assertEqual([view] * 3, [row["view"] for row in motion["frame"]["order"]])
                self.assertEqual([False] * 3, [row["runtime"] for row in motion["frame"]["order"]], "motion plates never connect")
                self.assertEqual([view], motion["frame"]["focused"])
                self.assertEqual([5, 4, 2], [row["pending"] for row in motion["frame"]["order"]])
        self.assertEqual("settled", out["wide"]["phase"][-1], out["wide"])
        self.assertEqual(["running@768"] * 3, [row["view"] for row in out["wide"]["frame"]["order"]], "a remount runs at the new target")
        self.assertEqual(["running@768"], out["wide"]["frame"]["focused"])

    def test_tampered_or_failing_slots_fail_closed(self):
        self.require()
        loader = escape(f"<script>{script_order.LOADER}</script>", quote=True)
        throwing = ordered_pages(focus='throw new Error("slot failed");')
        items = [self.book("missing", tamper=lambda d: d.replace("data-ds-source-slot=&quot;2&quot;", "data-ds-source-slot=&quot;9&quot;")),
                 self.book("repeated", tamper=lambda d: d.replace(loader, loader + loader)),
                 self.book("refused", tamper=lambda d: d.replace(token(FOCUS), token("void 0;"))),
                 self.book("throwing", page_set=throwing)]
        out = self.run_node(ORDER, {"items": items})
        missing, repeated, refused, failing = (out[name] for name in ("missing", "repeated", "refused", "throwing"))
        self.assertIn("Surface unavailable: source script markers are missing, repeated or out of order", missing["surfaceStatus"])
        self.assertEqual([], missing["surface"]["order"], "no product script runs from an inconsistent plate")
        self.assertEqual("invalid", missing["motion"][-1])
        self.assertIn("missing, repeated or out of order", missing["motionStatus"])
        self.assertIn("Surface unavailable: source script markers are missing, repeated or out of order", repeated["surfaceStatus"])
        self.assertEqual(3, len(repeated["surface"]["order"]), "a repeated loader never runs a source script twice")
        self.assertEqual([], repeated["errors"])
        self.assertIn("Surface unavailable: the content security policy refused a source script", refused["surfaceStatus"])
        self.assertEqual([], refused["surface"]["focused"])
        self.assertTrue(refused["errors"] and all("violates the following Content Security Policy directive 'script-src" in text
                                                  for text in refused["errors"]), refused["errors"])
        self.assertEqual("invalid", refused["motion"][-1])
        self.assertIn("Surface unavailable: source script 2 failed: Uncaught Error: slot failed", failing["surfaceStatus"])
        self.assertEqual(2, len(failing["surface"]["order"]), "activation stops at the failing slot")
        self.assertEqual("invalid", failing["motion"][-1])
        self.assertIn("source script error: Uncaught Error: slot failed", failing["motionStatus"])


if __name__ == "__main__":
    unittest.main()

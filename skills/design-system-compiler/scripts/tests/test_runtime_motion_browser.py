"""Real Chromium behavior of ds-showcase/2 source-runtime plates.

Required when PDH_REQUIRE_BROWSER_TESTS=1. Every gallery here is rendered from
the synthetic Kiln Timer fixture, not an approved product.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parents[0]))
sys.path.append(str(TESTS))
sys.path.append(str(TESTS.parents[2] / "ui-design-builder/scripts/tests"))

import design_system_showcase as showcase  # noqa: E402
import runtime_fixture as fixture  # noqa: E402
import showcase_runtime  # noqa: E402
import verify_runtime_motion  # noqa: E402

TIMEOUT = 240
HELPERS = r"""
const [,, module, input] = process.argv;
const {chromium} = require(module);
const cases = JSON.parse(input);
const fig = variant => "#m-" + variant + " + figure";
const tools = page => {
  const phase = variant => page.$eval(fig(variant), item => item.getAttribute("data-ds-phase"));
  const status = variant => page.$eval(fig(variant) + " .status", item => item.textContent);
  const press = selector => page.$eval(selector, item => item.click());
  const act = (variant, action) => press(fig(variant) + ' button[data-ds-runtime="' + action + '"]');
  const frame = async variant => (await page.$(fig(variant) + " iframe")).contentFrame();
  const inFrame = async (variant, fn, arg) => (await frame(variant)).evaluate(fn, arg);
  const wait = async (variant, wanted, limit) => {
    const end = Date.now() + limit, seen = [];
    while (Date.now() < end) {
      const value = await phase(variant);
      if (seen[seen.length - 1] !== value) seen.push(value);
      if (wanted.includes(value)) return seen;
      await page.waitForTimeout(30);
    }
    seen.push("timeout");
    return seen;
  };
  const running = variant => inFrame(variant, () => document.getAnimations().filter(item => item.playState === "running").length);
  // Chromium throttles offscreen cross-origin frames, so a driven plate must be on screen.
  const show = variant => page.$eval(fig(variant), item => item.scrollIntoView({block: "center"}));
  return {phase, status, press, act, frame, inFrame, wait, running, show};
};
const watch = (context, page, report) => {
  report.errors = []; report.requests = []; report.popups = [];
  page.on("pageerror", error => report.errors.push(String(error)));
  page.on("console", message => { if (message.type() === "error") report.errors.push(message.text()); });
  context.on("request", request => { if (!/^(file|about|data):/.test(request.url())) report.requests.push(request.url()); });
  page.on("popup", popup => report.popups.push(popup.url()));
};
"""

POSITIVE = HELPERS + r"""
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({viewport: {width: 1280, height: 700}});
  const page = await context.newPage();
  const r = {};
  watch(context, page, r);
  await page.goto(cases.url);
  const {phase, status, press, act, inFrame, wait, running, show} = tools(page);
  await page.waitForTimeout(1200);
  r.offscreen = await page.$eval(fig("kiln-rise"), item => item.getBoundingClientRect().top > innerHeight);
  r.waiting = [await phase("kiln-rise"), await status("kiln-rise"), await inFrame("kiln-rise", () => [document.documentElement.dataset.kilnArm || null, document.getAnimations().length])];
  r.mounts = await inFrame("kiln-rise", () => [document.documentElement.dataset.reviewer || null, document.documentElement.dataset.controls || null]);
  await page.$eval(fig("kiln-rise"), item => item.scrollIntoView({block: "center"}));
  r.entered = await wait("kiln-rise", ["settled", "invalid"], 8000);
  r.enteredStatus = await status("kiln-rise");
  r.finalFrame = await inFrame("kiln-rise", () => [document.documentElement.dataset.kilnDone || null,
    Array.from(document.querySelectorAll("[data-ds-motion-subject] .kiln-mark")).filter(item => !item.closest("[hidden]")).map(item => getComputedStyle(item).opacity)]);
  await page.evaluate(() => window.scrollTo(0, 0)); await page.waitForTimeout(400);
  await page.$eval(fig("kiln-rise"), item => item.scrollIntoView({block: "center"})); await page.waitForTimeout(700);
  r.once = [await phase("kiln-rise"), await inFrame("kiln-rise", () => document.getAnimations().length)];
  await act("kiln-rise", "replay"); r.replay1 = await wait("kiln-rise", ["settled", "invalid"], 8000);
  await act("kiln-rise", "replay"); r.replay2 = await wait("kiln-rise", ["settled", "invalid"], 8000);
  await act("kiln-rise", "replay"); await wait("kiln-rise", ["playing"], 4000);
  const started = Date.now();
  await inFrame("kiln-rise", () => { document.querySelector("[data-hifi-canvas]").style.width = "330px"; });
  r.resize = await wait("kiln-rise", ["settled", "invalid"], 4000); r.resizeMs = Date.now() - started;
  await act("kiln-rise", "replay"); await wait("kiln-rise", ["playing"], 4000);
  await press(fig("kiln-rise") + ' button[data-ds-runtime-target="768"]');
  r.sizeSwitch = [await wait("kiln-rise", ["settled", "invalid"], 8000), await inFrame("kiln-rise", () =>
    [document.querySelector("[data-hifi-canvas]").getAttribute("data-hifi-target"), JSON.parse(document.getElementById("ds-mount").textContent).target])];
  await press(fig("kiln-rise") + ' button[data-ds-runtime-target="390"]'); await wait("kiln-rise", ["settled", "invalid"], 8000);
  await act("kiln-rise", "replay"); await act("kiln-rise", "stop");
  r.stopEarly = await wait("kiln-rise", ["stopped"], 4000); await page.waitForTimeout(1500);
  r.stopEarlyAfter = [await phase("kiln-rise"), await running("kiln-rise"), await inFrame("kiln-rise", () => document.documentElement.dataset.kilnDone || null)];
  await act("kiln-rise", "replay"); await wait("kiln-rise", ["playing"], 4000); await act("kiln-rise", "stop");
  r.stopMid = await wait("kiln-rise", ["stopped"], 3000); await page.waitForTimeout(1500);
  r.stopMidAfter = [await phase("kiln-rise"), await running("kiln-rise"),
    await inFrame("kiln-rise", () => [document.getAnimations().filter(item => item.playState === "paused").length, document.documentElement.dataset.kilnDone || null, document.body.inert])];
  await act("kiln-rise", "replay"); await wait("kiln-rise", ["settled"], 8000); await act("kiln-rise", "stop");
  r.stopLate = await wait("kiln-rise", ["stopped"], 3000);
  await act("kiln-rise", "replay"); r.stopThenReplay = await wait("kiln-rise", ["settled", "invalid"], 8000);
  await show("belt-step");
  await act("belt-step", "replay"); r.beltPlaying = await wait("belt-step", ["playing"], 4000); await act("belt-step", "stop");
  await wait("belt-step", ["stopped"], 3000);
  const count = () => inFrame("belt-step", () => document.querySelector("[data-ds-motion-subject] .belt-count").textContent);
  const first = await count(); await page.waitForTimeout(1600);
  r.beltFrozen = [first, await count(), await inFrame("belt-step", () => document.querySelector("[data-ds-motion-subject]").hasAttribute("data-belt-spent"))];
  await act("belt-step", "replay"); r.beltSettled = await wait("belt-step", ["settled", "invalid"], 6000);
  await show("belt-stripes");
  await act("belt-stripes", "replay"); r.stripes = await wait("belt-stripes", ["settled", "invalid"], 8000);
  r.stripesStatus = await status("belt-stripes");
  await act("belt-stripes", "replay"); await wait("belt-stripes", ["playing"], 3000); await act("belt-stripes", "stop");
  await wait("belt-stripes", ["stopped"], 3000);
  r.stripesStopped = await inFrame("belt-stripes", () => document.getAnimations().map(item => item.playState));
  await press(fig("belt-stripes") + ' button[data-ds-runtime-target="768"]');
  r.wide = await wait("belt-stripes", ["settled", "invalid"], 8000);
  r.wideSizes = [await page.$eval(fig("belt-stripes") + " iframe", item => Math.round(item.getBoundingClientRect().width)),
    await inFrame("belt-stripes", () => document.querySelector("[data-hifi-canvas]").getAttribute("data-hifi-target"))];
  await show("kiln-rise");
  await act("kiln-rise", "replay"); await wait("kiln-rise", ["playing"], 4000);
  await press("[data-ds-reduced-toggle]");
  r.reduced = [await wait("kiln-rise", ["reduced", "invalid"], 4000), await wait("belt-step", ["reduced", "invalid"], 4000),
    await wait("belt-stripes", ["reduced", "invalid"], 4000)];
  r.reducedFrame = await inFrame("kiln-rise", () => [document.documentElement.dataset.kilnArm || null, document.documentElement.dataset.kilnDone || null,
    document.getAnimations().length, document.querySelector("style[data-ds-reduced]").media]);
  r.reducedBelt = await inFrame("belt-stripes", () => document.getAnimations().length);
  r.reducedStatus = await status("belt-stripes");
  await press("[data-ds-reduced-toggle]");
  await show("belt-stripes");
  r.restored = await wait("belt-stripes", ["playing", "settled"], 4000);
  await inFrame("belt-step", () => document.querySelector("[data-ds-motion-subject]").closest("[data-hifi-state-view]").querySelector('a[href="log.html"]').click());
  await page.waitForTimeout(300);
  r.contained = [(await (await page.$(fig("belt-step") + " iframe")).contentFrame()).url(), await status("belt-step")];
  await show("kiln-rise");
  await act("kiln-rise", "replay"); await wait("kiln-rise", ["settled"], 8000);
  const mount = await inFrame("kiln-rise", () => [JSON.parse(document.getElementById("ds-frame-config").textContent).id,
    JSON.parse(document.getElementById("ds-mount").textContent).generation]);
  await inFrame("belt-step", target => { for (let i = 0; i < parent.frames.length; i++)
    parent.frames[i].postMessage({type: "ds-runtime-stop", id: target[0], generation: target[1]}, "*"); }, mount);
  await page.waitForTimeout(400);
  r.siblingStop = await phase("kiln-rise");
  console.log(JSON.stringify(r));
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
"""

SYSTEM = HELPERS + r"""
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({viewport: {width: 1280, height: 700}, reducedMotion: "reduce"});
  const page = await context.newPage();
  const r = {};
  watch(context, page, r);
  await page.goto(cases.url);
  const {phase, status, inFrame, wait} = tools(page);
  r.phases = [await wait("kiln-rise", ["reduced", "invalid"], 4000), await wait("belt-step", ["reduced", "invalid"], 4000),
    await wait("belt-stripes", ["reduced", "invalid"], 4000)];
  r.firstPaint = await inFrame("kiln-rise", () => [document.documentElement.dataset.kilnArm || null, document.documentElement.dataset.kilnDone || null,
    document.getAnimations().length, document.querySelector("style[data-ds-reduced]").media]);
  r.status = await status("kiln-rise");
  r.toggle = await page.$eval("[data-ds-reduced-toggle]", item => item.getAttribute("aria-pressed"));
  const id = await page.$eval(fig("kiln-rise") + " iframe", item => item.dataset.dsFrame);
  await page.evaluate(plate => window.postMessage({type: "ds-runtime", id: plate, generation: 0, phase: "settled", evidence: [], target: "390"}, "*"), id);
  await page.waitForTimeout(250);
  r.hostileTop = await phase("kiln-rise");
  await inFrame("kiln-rise", plate => parent.postMessage({type: "ds-runtime", id: plate, generation: 9, phase: "invalid", error: "stale"}, "*"), id);
  await page.waitForTimeout(250);
  r.stale = await phase("kiln-rise");
  await inFrame("kiln-rise", plate => parent.postMessage({type: "ds-runtime", id: plate, generation: 0, phase: "invalid",
    target: "<img src=x onerror=alert(1)>", error: "<b>bold</b>"}, "*"), id);
  await page.waitForTimeout(250);
  r.markup = [await status("kiln-rise"), await page.$eval(fig("kiln-rise") + " .status", item => item.children.length)];
  const field = await page.$("#c-primitive-textfield ~ .plates iframe");
  await field.scrollIntoViewIfNeeded();
  await page.focus("#c-primitive-textfield ~ .plates iframe");
  await page.keyboard.press("Tab");
  r.focus = await (await field.contentFrame()).evaluate(() => {
    const item = document.activeElement, style = getComputedStyle(item);
    return [item.className, item.matches(":focus-visible"), style.outlineStyle, style.outlineWidth, style.outlineColor];
  });
  console.log(JSON.stringify(r));
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
"""

NEGATIVE = HELPERS + r"""
(async () => {
  const browser = await chromium.launch();
  const out = {};
  for (let start = 0; start < cases.items.length; start += 4) {
    await Promise.all(cases.items.slice(start, start + 4).map(async item => {
      const context = await browser.newContext({viewport: {width: 1280, height: 700}});
      const page = await context.newPage();
      const r = {};
      watch(context, page, r);
      await page.goto(item.url);
      const {status, wait} = tools(page);
      if (!item.stay) await page.$eval(fig(item.variant), node => node.scrollIntoView({block: "center"}));
      r.seen = await wait(item.variant, ["invalid", "settled"], 9000);
      r.status = await status(item.variant);
      out[item.name] = r;
      await context.close();
    }));
  }
  console.log(JSON.stringify(out));
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
"""


def browser():
    from test_reviewer_browser import playwright_module

    node = shutil.which("node")
    module = playwright_module(node) if node else None
    return node, module


def negative_sources():
    css, script, play = fixture.PRODUCT_CSS, fixture.PRODUCT_SCRIPT, 'stage.querySelectorAll(".kiln-mark")'
    stripes = "animation:belt-move 400ms linear 6"
    arm = "    if (!stages.length) return;\n"
    return {
        "sibling": ("kiln-rise", script.replace(play, "[stage.previousElementSibling]"), css, False),
        "detached": ("kiln-rise", script.replace(play, '[document.createElement("span")]'), css, False),
        "hidden copy": ("kiln-rise", script.replace(play, """document.querySelectorAll('[data-responsive-target="768"] .kiln-mark')"""), css, False),
        "no-op": ("kiln-rise", "void 0;", css, False),
        "comment only": ("kiln-rise", "/* the kiln rises when it is seen */", css, False),
        "exception": ("kiln-rise", 'throw new Error("kiln source failed");\n' + script, css, False),
        "played offscreen": ("kiln-rise", script.replace(arm, arm + "    rise(stages.find(stage => !stage.closest(\"[hidden]\"))); return;\n"), css, True),
        "waapi row with css only": ("belt-step", script.replace(fixture.BELT_STEP, ""), css, False),
        "css row with waapi only": ("belt-stripes", script, css.replace(";" + stripes, ""), False),
        "missing keyframes": ("belt-stripes", script, css.replace(stripes, "animation:belt-ghost 400ms linear 6"), False),
        "zero duration": ("belt-stripes", script, css.replace(stripes, "animation:belt-move 0s linear 6"), False),
        "infinite": ("belt-stripes", script, css.replace(stripes, "animation:belt-move 400ms linear infinite"), False),
        "wrong pseudo owner": ("belt-stripes", script, css.replace(";" + stripes, "") + '.belt-note::after{content:"";display:inline-block;'
                               "width:20px;height:4px;background:var(--glow);" + stripes + "}", False),
    }


class RuntimeBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node, cls.module = browser()
        cls.folder = Path(tempfile.mkdtemp(prefix="pdh-runtime-motion-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.folder, ignore_errors=True)

    def require(self):
        if not self.node or not self.module:
            if os.environ.get("PDH_REQUIRE_BROWSER_TESTS") == "1":
                self.fail("Node.js and PLAYWRIGHT_MODULE are required for the source-runtime browser tests")
            self.skipTest("Node Playwright is unavailable")

    def gallery(self, name, script=fixture.PRODUCT_SCRIPT, css=fixture.PRODUCT_CSS):
        page_set = fixture.pages(script, css=css)
        path = self.folder / f"{name.replace(' ', '-')}.html"
        path.write_text(fixture.render(page_set, fixture.registry(script)), encoding="utf-8")
        return path

    def run_node(self, script, payload):
        completed = subprocess.run([self.node, "-", self.module, json.dumps(payload)], input=script, text=True, encoding="utf-8",
                                   capture_output=True, timeout=TIMEOUT)
        self.assertEqual(0, completed.returncode, completed.stderr[-3000:])
        return json.loads(completed.stdout.strip().splitlines()[-1])

    def test_viewport_entry_replay_stop_resize_and_reduced(self):
        self.require()
        r = self.run_node(POSITIVE, {"url": self.gallery("positive").resolve().as_uri()})
        self.assertEqual(([], [], []), (r["errors"], r["requests"], r["popups"]))
        self.assertTrue(r["offscreen"])
        self.assertEqual("pending", r["waiting"][0])
        self.assertIn("has not entered the viewport", r["waiting"][1])
        self.assertEqual(["1", 0], r["waiting"][2], "armed with no motion before entry")
        self.assertEqual([None, "1"], r["mounts"], "product controls connect; the reviewer shell never mounts")
        self.assertEqual("settled", r["entered"][-1], r["entered"])
        self.assertIn("playing", r["entered"])
        self.assertIn("3 source animations on span.kiln-mark (opacity,transform) finished", r["enteredStatus"])
        self.assertEqual(["1", ["1", "1", "1"]], r["finalFrame"], "source CSS end state after cancel")
        self.assertEqual(["settled", 0], r["once"], "no second play on re-entry")
        for key in ("replay1", "replay2", "stopThenReplay", "beltSettled", "stripes", "wide"):
            self.assertEqual("settled", r[key][-1], (key, r[key]))
        self.assertEqual("settled", r["resize"][-1])
        self.assertLess(r["resizeMs"], 700, "product ResizeObserver finished the measured effects")
        self.assertEqual("settled", r["sizeSwitch"][0][-1], r["sizeSwitch"])
        self.assertEqual(["768", "768"], r["sizeSwitch"][1], "a size change remounts a fresh realm at that target")
        for key in ("stopEarly", "stopMid", "stopLate"):
            self.assertEqual("stopped", r[key][-1], (key, r[key]))
        self.assertEqual(["stopped", 0, None], r["stopEarlyAfter"])
        self.assertEqual("stopped", r["stopMidAfter"][0])
        self.assertEqual(0, r["stopMidAfter"][1])
        self.assertGreater(r["stopMidAfter"][2][0], 0)
        self.assertEqual([None, True], r["stopMidAfter"][2][1:], "late promises and timers did not finish the stopped run")
        self.assertEqual("playing", r["beltPlaying"][-1])
        self.assertEqual(r["beltFrozen"][0], r["beltFrozen"][1], "intervals are halted")
        self.assertFalse(r["beltFrozen"][2], "the stopped timeout never fired")
        self.assertIn("belt-move", r["stripesStatus"])
        self.assertIn("div.belt-bar::before", r["stripesStatus"])
        self.assertTrue(r["stripesStopped"] and set(r["stripesStopped"]) == {"paused"}, r["stripesStopped"])
        self.assertEqual([768, "768"], r["wideSizes"])
        self.assertEqual([["reduced"], ["reduced"], ["reduced"]], [seen[-1:] for seen in r["reduced"]])
        self.assertEqual([None, "1", 0, "all"], r["reducedFrame"], "no arming, source end state, reduced CSS applied")
        self.assertEqual(0, r["reducedBelt"])
        self.assertIn("gallery request", r["reducedStatus"])
        self.assertIn(r["restored"][-1], ("playing", "settled"))
        self.assertEqual("about:srcdoc", r["contained"][0])
        self.assertIn("Product link to log.html stays on this plate", r["contained"][1])
        self.assertEqual("settled", r["siblingStop"], "a sibling frame cannot stop another plate")

    def test_system_reduced_first_paint_hostile_messages_and_keyboard_focus(self):
        self.require()
        r = self.run_node(SYSTEM, {"url": self.gallery("system").resolve().as_uri()})
        self.assertEqual(([], [], []), (r["errors"], r["requests"], r["popups"]))
        self.assertEqual([["reduced"], ["reduced"], ["reduced"]], [seen[-1:] for seen in r["phases"]])
        self.assertTrue(all("playing" not in seen for seen in r["phases"]), r["phases"])
        self.assertEqual([None, "1", 0, "not all"], r["firstPaint"], "system preference applies before product execution")
        self.assertIn("system preference", r["status"])
        self.assertEqual("true", r["toggle"])
        self.assertEqual("reduced", r["hostileTop"])
        self.assertEqual("reduced", r["stale"])
        self.assertIn("<b>bold</b>", r["markup"][0])
        self.assertEqual(0, r["markup"][1], "message fields render as text only")
        self.assertEqual(["field", True, "solid", "3px", "rgb(217, 130, 43)"], r["focus"])

    def test_invalid_sources_stay_visibly_invalid(self):
        self.require()
        items = [{"name": name, "variant": variant, "stay": stay,
                  "url": self.gallery("neg-" + name, script, css).resolve().as_uri()}
                 for name, (variant, script, css, stay) in negative_sources().items()]
        out = self.run_node(NEGATIVE, {"items": items})
        for name in negative_sources():
            with self.subTest(name):
                self.assertEqual("invalid", out[name]["seen"][-1], (out[name]["seen"], out[name]["status"]))
                self.assertNotIn("settled", out[name]["seen"])
                self.assertEqual([], out[name]["requests"])
        self.assertIn("source script error: Uncaught Error: kiln source failed", out["exception"]["status"])

    def test_closeout_acceptance_binds_exact_preview_and_fails_invalid_motion(self):
        self.require()
        os.environ.setdefault("PLAYWRIGHT_MODULE", self.module)
        page_set = fixture.pages()
        manifest = json.loads(showcase.MANIFEST_RE.search(page_set["index.html"]).group("data"))
        runtime, problems = showcase_runtime.resolve_runtime(fixture.registry(), page_set, manifest, fixture.reader(fixture.repo_files()))
        self.assertEqual([], problems)
        plan = verify_runtime_motion.acceptance_plan(fixture.registry(), runtime)
        self.assertEqual([["390", "768"]] * 3, [row["targets"] for row in plan])
        report = verify_runtime_motion.run_acceptance(self.gallery("closeout"), plan)
        self.assertEqual("PASS", report["verdict"], json.dumps(report["results"], indent=1)[:3000])
        self.assertEqual(12, len(report["results"]), "every target runs a normal and a system-reduced case")
        self.assertTrue(report["processes"] and all(item["exited"] for item in report["processes"]), report["processes"])
        self.assertTrue(report["startedAt"] < report["finishedAt"])
        failing = verify_runtime_motion.run_acceptance(self.gallery("closeout-noop", "void 0;"), plan[:1])
        self.assertEqual("FAIL", failing["verdict"])
        self.assertTrue(all(item["first"] == "invalid" for item in failing["results"] if item["mode"] == "normal"))


if __name__ == "__main__":
    unittest.main()

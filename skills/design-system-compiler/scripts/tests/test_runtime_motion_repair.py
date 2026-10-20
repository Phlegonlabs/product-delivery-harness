"""Chromium regressions for the AK-COMPILER-REPAIR-001 runtime findings.

Synthetic Kiln Timer fixture only. Required when PDH_REQUIRE_BROWSER_TESTS=1:
constant, hidden and detached effects never earn credit; delayed reduced-motion
violations fail; the requested target/state exists before the first product
script; Stop gates Animation playback; and acceptance cleans its owned tree.
Inline scripts inside the surface run from source slots (test_script_order_*).
"""

import base64
import hashlib
import html as html_lib
import os
from pathlib import Path
import re
import sys
import unittest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parents[0]))
sys.path.append(str(TESTS))

import runtime_fixture as fixture  # noqa: E402
import verify_runtime_motion  # noqa: E402
from design_system_runtime_assets import RUNTIME_BOOT, RUNTIME_FRAME, STOPPED_CSS  # noqa: E402
from runtime_acceptance_process import AcceptanceRunError  # noqa: E402
from source_script_order import LOADER  # noqa: E402
import test_runtime_motion_browser as base  # noqa: E402
from test_runtime_motion_browser import HELPERS, NEGATIVE  # noqa: E402

KEYS = '[{transform: "translateY(90px)", opacity: 0}, {transform: "none", opacity: 1}]'
MARKS = 'const marks = Array.from(stage.querySelectorAll(".kiln-mark"));'
SETTLE = "return Promise.all(anims.map(a => a.finished))"
REDUCED_ARM = 'if (reduced() || typeof IntersectionObserver !== "function") { document.documentElement.dataset.kilnDone = "1"; return; }'
REDUCED_SCOPE = "[data-ui-surface] *,[data-ui-surface] *::before,[data-ui-surface] *::after"
LATE_WAAPI = REDUCED_ARM.replace("return; }", 'setTimeout(() => stages.forEach(stage => stage.querySelectorAll(".kiln-mark").forEach('
                                 "mark => mark.animate([{opacity: 0}, {opacity: 1}], {duration: 900}))), 500); return; }")
LATE_CSS = REDUCED_ARM.replace("return; }", 'setTimeout(() => stages.forEach(stage => stage.classList.add("late")), 500); return; }')

INIT_SCRIPT = """(function () {
  "use strict";
  const canvas = document.querySelector("[data-hifi-canvas]");
  const view = Array.from(document.querySelectorAll("[data-hifi-state-view]")).find(item => !item.hidden);
  document.documentElement.dataset.initTarget = canvas ? canvas.getAttribute("data-hifi-target") : "none";
  document.documentElement.dataset.initView = view ? view.dataset.hifiStateView + "@" + view.dataset.responsiveTarget : "none";
  if (view && view.dataset.hifiStateView === "running" && !matchMedia("(prefers-reduced-motion: reduce)").matches)
    view.querySelectorAll(".belt-bar").forEach(bar => bar.animate([{transform: "scaleX(.2)"}, {transform: "none"}], {duration: 700}));
})();"""

RACE_SCRIPT = """(function () {
  "use strict";
  window.raceAnims = [];
  document.addEventListener("DOMContentLoaded", () => {
    const view = Array.from(document.querySelectorAll("[data-hifi-state-view]")).find(item => !item.hidden);
    if (!view || view.dataset.hifiStateView !== "running" || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    view.querySelectorAll(".belt-bar").forEach(bar => {
      const anim = bar.animate([{transform: "scaleX(.2)"}, {transform: "none"}], {duration: 2400, fill: "both"});
      window.raceAnims.push(anim);
      anim.ready.then(() => anim.play());
      anim.finished.then(() => bar.animate([{opacity: 0.3}, {opacity: 1}], {duration: 500}));
    });
  });
})();"""

REDUCED = HELPERS + r"""
(async () => {
  const browser = await chromium.launch();
  const out = {};
  try {
    for (const item of cases.items) {
      const context = await browser.newContext(item.system ? {viewport: {width: 1280, height: 700}, reducedMotion: "reduce"}
        : {viewport: {width: 1280, height: 700}});
      try {
        const page = await context.newPage();
        const r = {};
        watch(context, page, r);
        await page.goto(item.url);
        const {status, press, wait, show} = tools(page);
        await show("kiln-rise");
        if (!item.system) await press("[data-ds-reduced-toggle]");
        r.first = await wait("kiln-rise", ["reduced", "invalid"], 4000);
        r.later = await wait("kiln-rise", ["invalid"], 3500);
        r.status = await status("kiln-rise");
        out[item.name] = r;
      } finally { await context.close(); }
    }
  } finally { console.log(JSON.stringify(out)); await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
"""

INIT = HELPERS + r"""
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await (await browser.newContext({viewport: {width: 1280, height: 700}})).newPage();
    const r = {};
    await page.goto(cases.url);
    const {press, wait, inFrame, show} = tools(page);
    const seen = () => inFrame("belt-step", () => [document.documentElement.dataset.initTarget, document.documentElement.dataset.initView]);
    await show("belt-step");
    r.first = [await wait("belt-step", ["settled", "invalid"], 6000), await seen()];
    await press(fig("belt-step") + ' button[data-ds-runtime-target="768"]');
    r.wide = [await wait("belt-step", ["settled", "invalid"], 6000), await seen()];
    console.log(JSON.stringify(r));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
"""

RACE = HELPERS + r"""
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await (await browser.newContext({viewport: {width: 1280, height: 700}})).newPage();
    const r = {};
    await page.goto(cases.url);
    const {phase, act, inFrame, wait, show} = tools(page);
    const look = () => inFrame("belt-step", () => {
      const bar = document.querySelector("[data-ds-motion-subject] .belt-bar");
      return [getComputedStyle(bar).transform, getComputedStyle(bar).opacity,
        document.getAnimations().filter(item => item.playState === "running").length];
    });
    // Product continuations holding retained, returned and constructed animations try every playback path.
    const poke = () => inFrame("belt-step", () => {
      const bar = document.querySelector("[data-ds-motion-subject] .belt-bar");
      for (const anim of window.raceAnims) { anim.play(); anim.reverse(); anim.updatePlaybackRate(4); anim.currentTime = 50; anim.startTime = 0; anim.finish(); }
      const late = bar.animate([{transform: "translateX(40px)"}, {transform: "none"}], {duration: 800});
      late.play();
      const made = new Animation(new KeyframeEffect(bar, [{opacity: 0}, {opacity: 1}], 800), document.timeline);
      made.play();
      return [window.raceAnims.length, late.playState, made.playState];
    });
    const race = async (label, before) => {
      await show("belt-step");
      await act("belt-step", "replay");
      await before();
      await act("belt-step", "stop");
      const stopped = await wait("belt-step", ["stopped"], 3000);
      await page.waitForTimeout(500);
      const held = await look();
      const poked = await poke();
      await page.waitForTimeout(900);
      r[label] = {stopped, held, poked, after: await look(), phase: await phase("belt-step")};
    };
    await race("early", async () => {});
    await race("mid", () => wait("belt-step", ["playing"], 4000));
    await race("late", () => wait("belt-step", ["settled"], 9000));
    await act("belt-step", "replay"); r.replay1 = await wait("belt-step", ["settled", "invalid"], 9000);
    await act("belt-step", "replay"); r.replay2 = await wait("belt-step", ["settled", "invalid"], 9000);
    console.log(JSON.stringify(r));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
"""


def no_credit_sources():
    css, script = fixture.PRODUCT_CSS, fixture.PRODUCT_SCRIPT
    stripes = "@keyframes belt-move{to{transform:translateX(16px)}}"
    return {
        "constant opacity waapi": ("kiln-rise", script.replace(KEYS, "[{opacity: 1}, {opacity: 1}]"), css),
        "empty keyframes": ("kiln-rise", script.replace(KEYS, "[{}, {}]"), css),
        "no-op transform": ("kiln-rise", script.replace(KEYS, '[{transform: "none"}, {transform: "translateX(0px)"}]'), css),
        "constant css keyframes": ("belt-stripes", script, css.replace(stripes, "@keyframes belt-move{from{transform:none}to{transform:translateX(0px)}}")),
        "hidden attribute descendants": ("kiln-rise", script.replace(MARKS, MARKS + " marks.forEach(mark => { mark.hidden = true; });"), css),
        "display none descendants": ("kiln-rise", script, css + ".kiln-mark{display:none}"),
        "detached after capture": ("kiln-rise", script.replace(SETTLE, "marks.forEach(mark => mark.remove()); " + SETTLE), css),
    }


class RuntimeRepairStaticTests(unittest.TestCase):
    def test_bootstrap_precedes_product_scripts_and_is_pinned(self):
        document = fixture.render()
        policy = html_lib.unescape(re.search(r'Content-Security-Policy" content="([^"]+)"', document).group(1))
        digest = "'sha256-" + base64.b64encode(hashlib.sha256(RUNTIME_BOOT.encode()).digest()).decode() + "'"
        self.assertIn(digest, policy)
        frames = [html_lib.unescape(src) for attrs, src in re.findall(r'<iframe ([^>]*?) srcdoc="([^"]*)"></iframe>', document)
                  if "data-ds-runtime-frame" in attrs]
        for frame in frames:
            boot = frame.index(f"<script>{RUNTIME_BOOT}</script>")
            self.assertLess(frame.index(RUNTIME_FRAME), boot)
            self.assertLess(frame.rindex('data-ds-motion-subject="768"'), boot, "the bootstrap follows the copied markup")
            # The product script keeps its source slot as an inert marker; only the loader after the bootstrap runs it.
            self.assertEqual(1, frame.count(f'<script type="text/x-ds-source-slot" data-ds-source-slot="0">{fixture.PRODUCT_SCRIPT}</script>'))
            self.assertEqual(1, frame.count(fixture.PRODUCT_SCRIPT))
            self.assertLess(boot, frame.index(f"<script>{LOADER}</script>"), "the bootstrap precedes the source script loader")
            self.assertIn(f'<style data-ds-stopped media="not all">{STOPPED_CSS}</style>', frame)


class RuntimeRepairBrowserTests(unittest.TestCase):
    setUpClass = classmethod(base.RuntimeBrowserTests.setUpClass.__func__)
    tearDownClass = classmethod(base.RuntimeBrowserTests.tearDownClass.__func__)
    require, gallery, run_node = (base.RuntimeBrowserTests.require, base.RuntimeBrowserTests.gallery,
                                  base.RuntimeBrowserTests.run_node)

    def test_constant_hidden_and_detached_effects_never_earn_credit(self):
        self.require()
        items = [{"name": name, "variant": variant, "stay": False, "url": self.gallery("credit-" + name, script, css).resolve().as_uri()}
                 for name, (variant, script, css) in no_credit_sources().items()]
        out = self.run_node(NEGATIVE, {"items": items})
        for name in no_credit_sources():
            with self.subTest(name):
                self.assertEqual("invalid", out[name]["seen"][-1], (out[name]["seen"], out[name]["status"]))
                self.assertNotIn("settled", out[name]["seen"])
                self.assertNotIn("playing", out[name]["seen"])
                self.assertEqual([], out[name]["errors"])

    def test_delayed_reduced_motion_violations_fail_after_an_initial_reduced_report(self):
        self.require()
        # The source keeps a reduced-motion rule, but it no longer covers the late kiln animation.
        css = fixture.PRODUCT_CSS.replace(REDUCED_SCOPE, ".belt-bar::before") + ".kiln.late .kiln-mark{animation:belt-move 900ms linear 2}"
        waapi = fixture.PRODUCT_SCRIPT.replace(REDUCED_ARM, LATE_WAAPI)
        state = fixture.PRODUCT_SCRIPT.replace(REDUCED_ARM, LATE_CSS)
        items = [{"name": "waapi system", "system": True, "url": self.gallery("late-waapi-system", waapi).resolve().as_uri()},
                 {"name": "waapi toggle", "system": False, "url": self.gallery("late-waapi-toggle", waapi).resolve().as_uri()},
                 {"name": "css state system", "system": True, "url": self.gallery("late-css-system", state, css).resolve().as_uri()},
                 {"name": "compliant system", "system": True, "url": self.gallery("late-compliant").resolve().as_uri()}]
        out = self.run_node(REDUCED, {"items": items})
        for name in ("waapi system", "waapi toggle", "css state system"):
            with self.subTest(name):
                self.assertEqual("reduced", out[name]["first"][-1], out[name])
                self.assertEqual("invalid", out[name]["later"][-1], out[name])
        self.assertIn("source motion ran under reduced motion on span.kiln-mark belt-move", out["css state system"]["status"])
        self.assertEqual(["reduced", "timeout"], out["compliant system"]["later"][-2:], "a compliant source stays reduced")

    def test_requested_target_and_state_exist_before_the_first_product_script(self):
        self.require()
        r = self.run_node(INIT, {"url": self.gallery("immediate-init", INIT_SCRIPT).resolve().as_uri()})
        self.assertEqual("settled", r["first"][0][-1], r)
        self.assertEqual(["390", "running@390"], r["first"][1])
        self.assertEqual("settled", r["wide"][0][-1], r)
        self.assertEqual(["768", "running@768"], r["wide"][1], "a synchronous script sees the nondefault target and state")

    def test_stop_gates_retained_returned_and_constructed_animations(self):
        self.require()
        r = self.run_node(RACE, {"url": self.gallery("stop-race", RACE_SCRIPT).resolve().as_uri()})
        for label in ("early", "mid", "late"):
            with self.subTest(label):
                item = r[label]
                self.assertEqual("stopped", item["stopped"][-1], item)
                self.assertEqual("stopped", item["phase"])
                self.assertEqual(0, item["held"][2])
                self.assertEqual(["idle", "idle"], item["poked"][1:], item)
                self.assertEqual(item["held"], item["after"], "no animation resumed or advanced while stopped")
        self.assertGreater(r["mid"]["poked"][0], 0, "mid race holds retained animations")
        self.assertEqual("settled", r["replay1"][-1], r["replay1"])
        self.assertEqual("settled", r["replay2"][-1], r["replay2"])

    def test_cli_rejects_constant_motion_and_delayed_reduced_violations(self):
        self.require()
        os.environ.setdefault("PLAYWRIGHT_MODULE", self.module)
        row = {"variant": "kiln-rise", "slug": "kiln-rise", "activation": "viewport", "targets": ["390"]}
        constant = verify_runtime_motion.run_acceptance(
            self.gallery("cli-constant", fixture.PRODUCT_SCRIPT.replace(KEYS, "[{opacity: 1}, {opacity: 1}]")), [row])
        self.assertEqual("FAIL", constant["verdict"])
        self.assertEqual("invalid", next(item for item in constant["results"] if item["mode"] == "normal")["first"])
        late = verify_runtime_motion.run_acceptance(
            self.gallery("cli-late", fixture.PRODUCT_SCRIPT.replace(REDUCED_ARM, LATE_WAAPI)), [row])
        self.assertEqual("FAIL", late["verdict"])
        normal = next(item for item in late["results"] if item["mode"] == "normal")
        system = next(item for item in late["results"] if item["mode"] == "system")
        self.assertEqual(("settled", "settled", "stopped"), (normal["first"], normal["replay"], normal["stop"]), normal)
        self.assertEqual("reduced", normal["reducedFirst"]["value"])
        self.assertFalse(normal["reducedHeld"], normal["reducedSeen"])
        self.assertFalse(system["pass"])
        self.assertIn("invalid", system["first"]["seen"] + system.get("window", {}).get("seen", []), system)
        for report in (constant, late):
            self.assertTrue(all(item["exited"] for item in report["processes"]), report["processes"])

    def test_acceptance_timeout_and_exception_leave_no_owned_process(self):
        self.require()
        os.environ.setdefault("PLAYWRIGHT_MODULE", self.module)
        row = {"variant": "kiln-rise", "slug": "kiln-rise", "activation": "viewport", "targets": ["390", "768"]}
        with self.assertRaisesRegex(AcceptanceRunError, "timed out") as timed:
            verify_runtime_motion.run_acceptance(self.gallery("cli-timeout"), [row] * 3, timeout=14)
        missing = {"variant": "absent", "slug": "absent-plate", "activation": "viewport", "targets": ["390"]}
        with self.assertRaisesRegex(AcceptanceRunError, "failed to run") as failed:
            verify_runtime_motion.run_acceptance(self.gallery("cli-exception"), [missing])
        for error in (timed.exception, failed.exception):
            roles = {item["role"] for item in error.processes}
            self.assertIn("node", roles)
            self.assertIn("chromium-browser", roles, error.processes)
            for item in error.processes:
                self.assertTrue(item["exited"], item)
                self.assertTrue(item["pid"] > 0 and item["started"] and item["expiry"] and item["purpose"])


if __name__ == "__main__":
    unittest.main()

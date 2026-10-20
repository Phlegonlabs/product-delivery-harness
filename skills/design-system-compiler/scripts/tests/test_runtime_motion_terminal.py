"""Terminal lifecycle regressions for source-review-003 finding 1 (same-object restart)
and finding 2 (an effect captured outside the subject, then retargeted inside: the _scope cases),
plus source-review-004 F1 (style-driven native CSS frame or timing changes: the css_drift cases).

SYNTHETIC Kiln Timer fixtures only, never an approved product. Browser cases are
required when PDH_REQUIRE_BROWSER_TESTS=1 and drive the real run_acceptance probe.
Two cases pass a labelled TEST PROBE variant to run_acceptance: one shortens the
first settle deadline, one presses Replay during the first quiet period.
"""

import json
import math
from pathlib import Path
import sys
import unittest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parents[0]))
sys.path.append(str(TESTS))

import runtime_fixture as fixture  # noqa: E402
import test_runtime_motion_acceptance as acc  # noqa: E402
import verify_runtime_motion  # noqa: E402
from test_runtime_motion_browser import HELPERS  # noqa: E402

AFTER = "Promise.all(anims.map(a => a.finished)).then(() => { " + acc.DONE + " anims.forEach(a => { %s }); });"
# The reviewer reproduction: three genuine finite effects finish, then the same objects restart infinitely.
RESTART_INFINITE = acc.rise(AFTER % "a.effect.updateTiming({iterations: Infinity}); a.currentTime = 0; a.play();")
REUSED = {
    "infinite restart": RESTART_INFINITE,
    "finite restart": acc.rise(AFTER % "a.currentTime = 0; a.play();"),
    "play-only restart": acc.rise(AFTER % "a.play();"),
    "reverse after the end": acc.rise(AFTER % "a.reverse();"),
    "currentTime revival after cleanup": acc.rise(AFTER % "a.cancel(); a.currentTime = 0;"),
    "startTime revival after cleanup": acc.rise(AFTER % "a.cancel(); a.startTime = document.timeline.currentTime;"),
    # The default easing is linear, so this is a real change; a same-value update stays harmless.
    "timing changed after the end": acc.rise(AFTER % 'a.effect.updateTiming({easing: "ease-in"});'),
    "keyframes changed after the end": acc.rise(AFTER % "a.effect.setKeyframes([{opacity: 0.2}, {opacity: 1}]);"),
    # Restarted and finished again in one task: no sample ever sees it running.
    "restart finished between ticks": acc.rise(AFTER % "a.currentTime = 0; a.play(); a.finish();"),
    "new effect on the old animation after the end": acc.rise(
        AFTER % "a.effect = new KeyframeEffect(a.effect.target, [{opacity: 0.5}, {opacity: 1}], 600);"),
    "timing changed before the end": acc.rise(acc.MIDFLIGHT % "a.effect.updateTiming({iterations: 2});" + acc.END),
}
# The source retains its CSSAnimation and replays the same object when it finishes; its own handler runs before capture's.
CSS_RESTART = acc.edit(fixture.PRODUCT_SCRIPT, fixture.BELT_SPEND,
                       "(belt.getAnimations({subtree: true}).forEach(a => a.finished.then(() => a.play())), " + fixture.BELT_SPEND + ")")
DELAYED_RESTART = acc.rise("return Promise.all(anims.map(a => a.finished)).then(() => { " + acc.DONE
                           + " setTimeout(() => anims.forEach(a => { a.currentTime = 0; a.play(); }), 700); });")
# Fresh finite objects after visible gaps shorter than the 1500 ms quiet period; the last stage is brief.
SEQUENTIAL = acc.rise("return Promise.all(anims.map(a => a.finished)).then(() => { " + acc.DONE + """
      const stage = () => marks.map(mark => mark.animate([{opacity: 0.5}, {opacity: 1}], {duration: 400}));
      setTimeout(() => Promise.all(stage().map(a => a.finished)).then(() => setTimeout(() =>
        marks.forEach(mark => mark.animate([{opacity: 0.4}, {opacity: 1}], {duration: 60, fill: "both"})), 700)), 700);
    });""")
# Source-review-003 finding 2, exactly: an infinite effect captured outside the subject is retargeted inside it.
RETARGET_INFINITE = acc.extra('const borrowed = document.querySelector(".kiln-side").animate([{transform:"translateX(0px)"},'
                              '{transform:"translateX(60px)"}], {duration:600,iterations:Infinity}); borrowed.effect.target=marks[0];')
SIDE = 'document.querySelector(".kiln-side")'


def borrowed(timing, then):
    """An effect captured on .kiln-side, outside the bound .kiln; ``then`` runs with ``side``, ``borrowed`` and ``marks``."""
    return acc.extra(f"const side = {SIDE}, borrowed = side.animate([{{transform: \"translateX(0px)\"}}, "
                     f"{{transform: \"translateX(60px)\"}}], {timing}); {then}")


INFINITE_SIDE, FINITE_SIDE = "{duration: 600, iterations: Infinity}", "{duration: 600}"
# Once an effect enters the subject (original owner or current target), it stays relevant for the generation.
SCOPE_RETARGETED = {
    "outside infinite retargeted inside": RETARGET_INFINITE,
    "outside finite retargeted inside before its end": borrowed(FINITE_SIDE, "borrowed.effect.target = marks[0];"),
    "outside finite retargeted inside after its end": borrowed("{duration: 200}",
                                                               "borrowed.finished.then(() => { borrowed.effect.target = marks[0]; });"),
    "outside in and back out in one task": borrowed(FINITE_SIDE, "borrowed.effect.target = marks[0]; borrowed.effect.target = side;"),
    "outside animation given an inside effect": borrowed(INFINITE_SIDE,
                                                         "borrowed.effect = new KeyframeEffect(marks[0], [{opacity: 0.5}, {opacity: 1}], 600);"),
    # Material retarget to a loose node, which the source then moves into the subject: no setter sees the entry.
    "outside effect target later moved into the subject": borrowed(INFINITE_SIDE, 'const loose = document.createElement("span"); '
                                                                   "borrowed.effect.target = loose; "
                                                                   "setTimeout(() => marks[0].parentElement.appendChild(loose), 250);"),
}
SCOPE_INVALID = dict(SCOPE_RETARGETED, **{
    "inside effect escapes outside before its end": acc.rise(acc.MIDFLIGHT % f"a.effect.target = {SIDE};" + acc.END),
    # DOM entry of the original owner joins the ordinary obligation; this infinite effect fails it.
    "outside owner moved into the subject": borrowed(INFINITE_SIDE, "setTimeout(() => marks[0].parentElement.appendChild(side), 250);"),
})
OUTSIDE_RETARGET = borrowed(INFINITE_SIDE, 'borrowed.effect.target = document.querySelector(".intro");')
SCOPE_CONTROLS = {
    "control: infinite effect always outside": acc.SIBLING,
    "control: outside-only retarget": OUTSIDE_RETARGET,
    "control: outside same effect and target assigned": borrowed(INFINITE_SIDE,
                                                                 "borrowed.effect.target = borrowed.effect.target; borrowed.effect = borrowed.effect;"),
    "control: inside same effect and target assigned": acc.ATTACHED["same effect and target assigned"],
    "control: natural end then null cleanup": acc.ATTACHED["natural end then detach"],
    "control: ordinary finite reveal": fixture.PRODUCT_SCRIPT,
}
FIRST = "const first = await settle(20000);"
SHORT_DEADLINE = FIRST.replace("20000", "2500")
REMOUNT = ("const remount = until([\"settled\"], 8000).then(() => page.waitForTimeout(500))"
           ".then(() => press(figure + ' button[data-ds-runtime=\"replay\"]')); " + FIRST + " await remount;")
# Watches each plate for a fixed window: an after-end reuse may follow a correct, briefly shown settled phase.
WATCH = HELPERS + r"""
(async () => {
  const browser = await chromium.launch();
  const out = {};
  try {
    for (let start = 0; start < cases.items.length; start += 4) {
      await Promise.all(cases.items.slice(start, start + 4).map(async item => {
        const context = await browser.newContext({viewport: {width: 1280, height: 700}});
        const page = await context.newPage();
        const r = {};
        watch(context, page, r);
        await page.goto(item.url);
        const {status, wait} = tools(page);
        await page.$eval(fig(item.variant), node => node.scrollIntoView({block: "center"}));
        r.seen = await wait(item.variant, ["invalid"], 6000);
        r.status = await status(item.variant);
        out[item.name] = r;
        await context.close();
      }));
    }
  } finally { console.log(JSON.stringify(out)); await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
"""
STOP = HELPERS + r"""
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await (await browser.newContext({viewport: {width: 1280, height: 700}})).newPage();
    const r = {};
    await page.goto(cases.url);
    const {phase, act, inFrame, wait, show, running} = tools(page);
    const look = () => inFrame("kiln-rise", () => (window.kilnAnims || []).map(a => [a.playState,
      a.currentTime === null ? null : Math.round(a.currentTime), a.effect ? String(a.effect.getTiming().iterations) : null]));
    // Product code holding the retained reveal tries timing, keyframes, seek and playback calls while stopped.
    const poke = () => inFrame("kiln-rise", () => (window.kilnAnims || []).forEach(a => {
      a.effect.updateTiming({iterations: Infinity}); a.effect.setKeyframes([{opacity: 0}, {opacity: 1}]);
      a.currentTime = 0; a.startTime = 0; a.play(); a.reverse(); }));
    await show("kiln-rise");
    for (const [label, before] of [["early", null], ["mid", ["playing"]], ["late", ["settled"]]]) {
      await act("kiln-rise", "replay");
      if (before) await wait("kiln-rise", before, 9000);
      await act("kiln-rise", "stop");
      const stopped = await wait("kiln-rise", ["stopped"], 3000);
      await page.waitForTimeout(300);
      const held = await look();
      await poke();
      await page.waitForTimeout(600);
      r[label] = {stopped, held, after: await look(), phase: await phase("kiln-rise"), running: await running("kiln-rise")};
    }
    await act("kiln-rise", "replay");
    r.replay = await wait("kiln-rise", ["settled", "invalid"], 9000);
    console.log(JSON.stringify(r));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
"""


# Source-review-004 F1: the source changes a custom property the captured CSS stripes resolve, 700 ms into their 2.4 s run.
# The native object, frame count and counted timing fields stay the same; the resolved frames, easing or fill do not.
CSS_DRIFT = acc.edit(fixture.PRODUCT_CSS, "@keyframes belt-move{to{transform:translateX(16px)}}",
                     "@keyframes belt-move{from{transform:translateX(0px)}to{transform:translateX(var(--stride,16px))}}"
                     ) + ".belt-bar::before{animation-timing-function:var(--belt-ease,linear);animation-fill-mode:var(--belt-fill,none)}"


def drifted(name, value):
    return acc.edit(fixture.PRODUCT_SCRIPT, "const ends = performance.now() + 2400;", "const ends = performance.now() + 2400; "
                    f'setTimeout(() => {{ document.documentElement.style.setProperty("{name}", "{value}"); '
                    'document.documentElement.dataset.cssDrift = "1"; }, 700);')


CSS_DRIFTED = {"endpoint custom property": drifted("--stride", "0px"), "easing custom property": drifted("--belt-ease", "steps(2)"),
               "fill custom property": drifted("--belt-fill", "forwards")}
CSS_STEADY = {"control: static custom property": fixture.PRODUCT_SCRIPT, "control: same-value custom property": drifted("--stride", "16px")}
# Native CSSAnimation facts before and after the source update, then the runtime phase over a fixed window.
NATIVE_DRIFT = HELPERS + r"""
(async () => {
  const browser = await chromium.launch();
  const out = {};
  try {
    for (const item of cases.items) {
      const context = await browser.newContext({viewport: {width: 1280, height: 700}});
      const page = await context.newPage();
      const r = {};
      watch(context, page, r);
      await page.goto(item.url);
      const {status, wait, inFrame, show} = tools(page);
      const native = () => inFrame("belt-stripes", () => ({drift: document.documentElement.dataset.cssDrift || null,
        items: document.getAnimations().filter(a => a instanceof CSSAnimation && a.playState !== "idle")
          .map(a => ({state: a.playState, timing: a.effect.getTiming(), frames: a.effect.getKeyframes()}))}));
      await show("belt-stripes");
      await wait("belt-stripes", ["playing"], 3000);
      r.before = await native();
      await page.waitForTimeout(900);
      r.after = await native();
      r.seen = await wait("belt-stripes", ["invalid"], 6000);
      r.status = await status("belt-stripes");
      out[item.name] = r;
      await context.close();
    }
  } finally { console.log(JSON.stringify(out)); await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
"""


def reduced_window(lifecycle):
    """The unchanged acceptance formula: max(3200, ceil(lifecycle + max(1600, lifecycle / 3)))."""
    return max(3200, math.ceil(lifecycle + max(1600, lifecycle / 3)))


class TerminalLifecycleTests(unittest.TestCase):
    setUpClass = classmethod(acc.AcceptanceBrowserTests.setUpClass.__func__)
    tearDownClass = classmethod(acc.AcceptanceBrowserTests.tearDownClass.__func__)
    require, gallery, run_node, phases, accept, assert_invalid = (
        acc.AcceptanceBrowserTests.require, acc.AcceptanceBrowserTests.gallery, acc.AcceptanceBrowserTests.run_node,
        acc.AcceptanceBrowserTests.phases, acc.AcceptanceBrowserTests.accept, acc.AcceptanceBrowserTests.assert_invalid)

    def probe(self, name, script, old, new):
        self.require()
        probe = verify_runtime_motion.PROBE.replace(old, new)
        self.assertNotEqual(verify_runtime_motion.PROBE, probe, "TEST PROBE variant must change the probe")
        report = verify_runtime_motion.run_acceptance(self.gallery("terminal-probe-" + name, script), [acc.KILN], probe=probe)
        self.assertTrue(report["processes"] and all(item["exited"] for item in report["processes"]), report["processes"])
        return report, {item["mode"]: item for item in report["results"]}

    def test_reviewer_infinite_restart_after_natural_end_fails_acceptance(self):
        self.require()
        report, modes = self.accept("restart-infinite", RESTART_INFINITE)
        self.assertEqual("FAIL", report["verdict"], json.dumps(report["results"])[:3000])
        self.assertFalse(modes["normal"]["pass"], modes["normal"])
        self.assertEqual("invalid", modes["normal"]["first"], modes["normal"])
        self.assertRegex(modes["normal"]["firstStatus"], "span.kiln-mark (restarted after its end|changed its timing or keyframes)")
        self.assertNotIn("lifecycleMs", modes["normal"], "no reduced window derives from an unproven lifecycle")

    def test_same_object_reuse_after_or_mutation_before_the_end_is_invalid(self):
        self.require()
        cases = {name: ("kiln-rise", script, acc.CSS) for name, script in REUSED.items()}
        cases["css retained animation replayed"] = ("belt-stripes", CSS_RESTART, acc.CSS)
        controls = {"control: ordinary finite reveal": ("kiln-rise", fixture.PRODUCT_SCRIPT, acc.CSS),
                    "control: natural end then detach": ("kiln-rise", acc.ATTACHED["natural end then detach"], acc.CSS),
                    "control: natural end then idle constructor": ("kiln-rise", acc.TAKEN_AFTER_END, acc.CSS),
                    "control: finish then cancel": ("kiln-rise", acc.FINISHED["finish then cancel"], acc.CSS),
                    "control: same-value timing after the end": ("kiln-rise", acc.rise(AFTER % 'a.effect.updateTiming({easing: "linear"});'), acc.CSS),
                    "control: stripes cleanup after the end": ("belt-stripes", fixture.PRODUCT_SCRIPT, acc.CSS),
                    "control: waapi steps beside css stripes": ("belt-step", fixture.PRODUCT_SCRIPT, acc.CSS)}
        items = [{"name": name, "variant": variant, "url": self.gallery("terminal-" + name, script, css).resolve().as_uri()}
                 for name, (variant, script, css) in {**cases, **controls}.items()]
        out = self.run_node(WATCH, {"items": items})
        for name in cases:
            with self.subTest(name):
                self.assertEqual("invalid", out[name]["seen"][-1], out[name])
                self.assertRegex(out[name]["status"], "(restarted after its end|changed its timing or keyframes|reattached after its end)"
                                 "; one Animation proves one finite run")
                self.assertEqual([], out[name]["errors"])
        for name in controls:
            with self.subTest(name):
                self.assertEqual(["settled", "timeout"], out[name]["seen"][-2:], out[name])
                self.assertNotIn("invalid", out[name]["seen"])
                self.assertEqual([], out[name]["errors"])

    def test_delayed_restart_inside_the_quiet_period_revokes_settled(self):
        self.require()
        report, modes = self.accept("restart-delayed", DELAYED_RESTART)
        normal = modes["normal"]
        self.assertEqual("FAIL", report["verdict"])
        self.assertIn("settled", normal["firstSeen"], normal)
        self.assertEqual("invalid", normal["first"], normal)
        self.assertFalse(normal["firstComplete"])

    def test_sequential_new_objects_reset_quiet_and_feed_the_final_lifecycle(self):
        self.require()
        report, modes = self.accept("sequential-stages", SEQUENTIAL)
        normal, system = modes["normal"], modes["system"]
        self.assertEqual("PASS", report["verdict"], json.dumps(report["results"])[:3000])
        self.assertTrue(normal["firstComplete"] and normal["replayComplete"], normal)
        # Reveal 900 ms, 700 ms gap, 400 ms stage, 700 ms gap, then a 60 ms stage that can fall between parent polls.
        self.assertGreaterEqual(normal["lifecycleMs"], 2600, normal)
        self.assertEqual(reduced_window(normal["lifecycleMs"]), normal["reducedWindowMs"])
        self.assertEqual(normal["reducedWindowMs"], system["reducedWindowMs"])
        self.assertGreaterEqual(normal["reducedObservedMs"], normal["reducedWindowMs"])

    def test_deadline_inside_an_unfinished_quiet_period_fails(self):
        report, modes = self.probe("deadline", fixture.PRODUCT_SCRIPT, FIRST, SHORT_DEADLINE)
        normal = modes["normal"]
        self.assertEqual("FAIL", report["verdict"])
        self.assertEqual("settled", normal["first"], normal)
        self.assertFalse(normal["firstComplete"], normal)
        self.assertNotIn("lifecycleMs", normal)
        self.assertFalse(modes["system"]["pass"])

    def test_generation_change_during_the_quiet_period_fails(self):
        report, modes = self.probe("remount", fixture.PRODUCT_SCRIPT, FIRST, REMOUNT)
        normal = modes["normal"]
        self.assertEqual("FAIL", report["verdict"])
        self.assertTrue(normal["firstRemounted"], normal)
        self.assertFalse(normal["firstComplete"], normal)

    def test_stop_holds_attempted_mutations_and_replay_starts_clean(self):
        self.require()
        r = self.run_node(STOP, {"url": self.gallery("terminal-stop", acc.RETAINED).resolve().as_uri()})
        for label in ("early", "mid", "late"):
            with self.subTest(label):
                item = r[label]
                self.assertEqual("stopped", item["stopped"][-1], item)
                self.assertEqual("stopped", item["phase"], item)
                self.assertEqual(0, item["running"], item)
                self.assertEqual(item["held"], item["after"], "no stopped call changed timing, time or playback")
        self.assertTrue(r["mid"]["held"], "mid Stop holds the retained reveal")
        self.assertEqual("settled", r["replay"][-1], r["replay"])

    def test_scope_entry_keeps_an_effect_relevant_and_outside_effects_stay_ignored(self):
        self.require()
        cases = {name: ("kiln-rise", script, acc.CSS) for name, script in {**SCOPE_INVALID, **SCOPE_CONTROLS}.items()}
        items = [{"name": name, "variant": variant, "url": self.gallery("scope-" + name, script, css).resolve().as_uri()}
                 for name, (variant, script, css) in cases.items()]
        out = self.run_node(WATCH, {"items": items})
        for name in SCOPE_INVALID:
            with self.subTest(name):
                self.assertEqual("invalid", out[name]["seen"][-1], out[name])
                self.assertEqual([], out[name]["errors"])
        for name in SCOPE_RETARGETED:
            with self.subTest(name):
                self.assertRegex(out[name]["status"], r"div\.kiln-side was retargeted into the subject; one Animation proves one finite run")
        for name in SCOPE_CONTROLS:
            with self.subTest(name):
                self.assertEqual(["settled", "timeout"], out[name]["seen"][-2:], out[name])
                self.assertNotIn("invalid", out[name]["seen"])
                self.assertEqual([], out[name]["errors"])

    def test_scope_retargeted_or_escaped_effects_fail_acceptance(self):
        self.require()
        for name in ("outside infinite retargeted inside", "outside finite retargeted inside before its end",
                     "outside in and back out in one task", "outside effect target later moved into the subject",
                     "inside effect escapes outside before its end"):
            with self.subTest(name):
                report, modes = self.accept("scope-" + name.replace(" ", "-"), SCOPE_INVALID[name])
                normal = modes["normal"]
                self.assertEqual("FAIL", report["verdict"], json.dumps(report["results"])[:3000])
                # The runtime book itself reads invalid; a verifier-only failure after a shown settled is not enough.
                self.assertEqual("invalid", normal["first"], normal)
                self.assertNotIn("settled", normal["firstSeen"], normal)
                self.assertNotIn("lifecycleMs", normal)

    def test_css_drift_of_native_frames_or_timing_invalidates_and_steady_values_settle(self):
        self.require()
        items = [{"name": name, "url": self.gallery("css-drift-" + name, script, CSS_DRIFT).resolve().as_uri()}
                 for name, script in {**CSS_DRIFTED, **CSS_STEADY}.items()]
        out = self.run_node(NATIVE_DRIFT, {"items": items})
        for name in {**CSS_DRIFTED, **CSS_STEADY}:
            with self.subTest(name):
                before, after = out[name]["before"], out[name]["after"]
                self.assertEqual([], out[name]["errors"])
                # The same three native CSSAnimations are still running before their end in both observations.
                self.assertEqual((3, 3), (len(before["items"]), len(after["items"])), out[name])
                self.assertEqual(["running"] * 6, [item["state"] for item in before["items"] + after["items"]], out[name])
                self.assertIsNone(before["drift"])
        native = {name: (out[name]["before"]["items"][0], out[name]["after"]["items"][0]) for name in out}
        endpoint, easing, fill = (native[name] for name in CSS_DRIFTED)
        self.assertEqual(["translateX(16px)", "translateX(0px)"], [side["frames"][-1]["transform"] for side in endpoint])
        self.assertEqual(endpoint[0]["timing"], endpoint[1]["timing"])
        self.assertNotEqual(easing[0]["frames"], easing[1]["frames"])
        self.assertEqual(["none", "forwards"], [side["timing"]["fill"] for side in fill])
        for name in CSS_DRIFTED:
            with self.subTest(name):
                self.assertEqual("1", out[name]["after"]["drift"])
                self.assertEqual("invalid", out[name]["seen"][-1], out[name])
                self.assertRegex(out[name]["status"], r"div\.belt-bar::before changed its timing or keyframes; one Animation proves one finite run")
        for name in CSS_STEADY:
            with self.subTest(name):
                self.assertEqual(native[name][0], native[name][1], "steady native frames and timing")
                self.assertEqual(["settled", "timeout"], out[name]["seen"][-2:], out[name])
                self.assertNotIn("invalid", out[name]["seen"])

    def test_css_drift_fails_ordinary_acceptance_and_static_custom_property_passes(self):
        self.require()
        for name in CSS_DRIFTED:
            with self.subTest(name):
                report, modes = self.accept("css-drift-" + name.replace(" ", "-"), CSS_DRIFTED[name], CSS_DRIFT, acc.STRIPES)
                normal = modes["normal"]
                self.assertEqual("FAIL", report["verdict"], json.dumps(report["results"])[:3000])
                self.assertEqual("invalid", normal["first"], normal)
                self.assertNotIn("settled", normal["firstSeen"], normal)
                self.assertNotIn("lifecycleMs", normal)
        # Static custom-property resolution with the source's genuine end cleanup (the stripes are removed after their end).
        report, modes = self.accept("css-drift-static", fixture.PRODUCT_SCRIPT, CSS_DRIFT, acc.STRIPES)
        self.assertEqual("PASS", report["verdict"], json.dumps(report["results"])[:3000])
        self.assertEqual(("settled", "settled"), (modes["normal"]["first"], modes["normal"]["replay"]), modes["normal"])

    def test_scope_outside_only_retarget_and_end_cleanup_pass_acceptance(self):
        self.require()
        for name, script in (("outside-only retarget", OUTSIDE_RETARGET),
                             ("natural end then null cleanup", acc.ATTACHED["natural end then detach"])):
            with self.subTest(name):
                report, modes = self.accept("scope-" + name.replace(" ", "-"), script)
                self.assertEqual("PASS", report["verdict"], json.dumps(report["results"])[:3000])
                self.assertEqual(("settled", "settled"), (modes["normal"]["first"], modes["normal"]["replay"]), modes["normal"])


if __name__ == "__main__":
    unittest.main()

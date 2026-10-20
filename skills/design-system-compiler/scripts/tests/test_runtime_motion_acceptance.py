"""Regressions for the source-review-002 runtime acceptance findings.

SYNTHETIC Kiln Timer fixtures only, never an approved product. Browser cases are
required when PDH_REQUIRE_BROWSER_TESTS=1 and drive the real run_acceptance probe
with its full windows. The input-race cases call the real main() with two
labelled TEST DOUBLES: the pair checker (the synthetic pair is not a complete
publication) and the browser boundary, which mutates a named input mid-run.
"""

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parents[0]))
sys.path.append(str(TESTS))

import check_design_system_pair  # noqa: E402
import runtime_fixture as fixture  # noqa: E402
import verify_runtime_motion  # noqa: E402
import test_runtime_motion_browser as base  # noqa: E402
from test_runtime_motion_browser import NEGATIVE  # noqa: E402

KEYS = '[{transform: "translateY(90px)", opacity: 0}, {transform: "none", opacity: 1}]'
SETTLE = "return Promise.all(anims.map(a => a.finished))"
REDUCED_ARM = 'if (reduced() || typeof IntersectionObserver !== "function") { document.documentElement.dataset.kilnDone = "1"; return; }'
KILN = {"variant": "kiln-rise", "slug": "kiln-rise", "activation": "viewport", "targets": ["390"]}


def edit(text, old, new):
    changed = text.replace(old, new)
    assert changed != text, old
    return changed


def rise(after):
    """A three-mark reveal without stagger; ``after`` is product code run with ``anims`` in scope."""
    return edit(fixture.PRODUCT_SCRIPT, fixture.KILN_PLAY, "function rise(stage) {\n"
                '    const marks = Array.from(stage.querySelectorAll(".kiln-mark"));\n'
                f'    const anims = marks.map(mark => mark.animate({KEYS}, {{duration: 900, fill: "both"}}));\n'
                f"    {after}\n  }}")


def extra(code):
    return edit(fixture.PRODUCT_SCRIPT, SETTLE, code + " " + SETTLE)


CSS = fixture.PRODUCT_CSS
TRANSPARENT = {
    "transparent owner": ("kiln-rise", fixture.PRODUCT_SCRIPT, CSS + ".kiln-mark{opacity:0!important}"),
    "transparent subject": ("kiln-rise", fixture.PRODUCT_SCRIPT, CSS + ".kiln{opacity:0}"),
    "transparent outer ancestor": ("kiln-rise", fixture.PRODUCT_SCRIPT, CSS + ".shell{opacity:0}"),
    "transparent pseudo": ("belt-stripes", fixture.PRODUCT_SCRIPT, CSS + ".belt-bar::before{opacity:0}"),
    "hidden pseudo": ("belt-stripes", fixture.PRODUCT_SCRIPT, CSS + ".belt-bar::before{visibility:hidden}"),
}
INFINITE = "marks.forEach(mark => mark.animate([{opacity: 0.3}, {opacity: 1}], {duration: 650, iterations: Infinity}));"
MIXED = {
    "finite plus infinite": extra(INFINITE),
    "finite plus zero duration": extra("marks.forEach(mark => mark.animate([{opacity: 0.5}, {opacity: 1}], {duration: 0}));"),
    "finite plus empty keyframes": extra("marks.forEach(mark => mark.animate([], {duration: 600}));"),
}
SIBLING = extra('document.querySelectorAll(".kiln-side").forEach(side => side.animate([{opacity: 0.4}, {opacity: 1}], '
                "{duration: 650, iterations: Infinity}));")
DONE = 'document.documentElement.dataset.kilnDone = "1";'
CANCELLED = {
    "all cancelled midflight": ("kiln-rise", rise("setTimeout(() => anims.forEach(a => a.cancel()), 250);\n"
                                                  "    return Promise.all(anims.map(a => a.finished)).catch(() => {});")),
    "one cancelled midflight": ("kiln-rise", rise("setTimeout(() => anims[0].cancel(), 250);\n"
                                                  "    return Promise.all(anims.map(a => a.finished.catch(() => {}))).then(() => { "
                                                  + DONE + " });")),
    "css removed midflight": ("belt-stripes", edit(fixture.PRODUCT_SCRIPT, fixture.BELT_SPEND,
                                                   'setTimeout(() => belt.setAttribute("data-belt-spent", ""), 1000)')),
}
# Source removes the stripes early, then dispatches its own cancel event claiming the full 2.4s ran.
UNTRUSTED = edit(fixture.PRODUCT_SCRIPT, fixture.BELT_SPEND, """setTimeout(() => {
      belt.setAttribute("data-belt-spent", ""); belt.getAnimations({subtree:true});
      belt.querySelectorAll(".belt-bar").forEach(bar => bar.dispatchEvent(new AnimationEvent("animationcancel", {
        bubbles:true, animationName:"belt-move", pseudoElement:"::before", elapsedTime:2.4
      })));
    }, 500)""")
STRIPES = {"variant": "belt-stripes", "slug": "belt-stripes", "activation": "state", "targets": ["390"]}
FINISHED = {
    "finish then cancel": rise("setTimeout(() => { anims.forEach(a => a.finish()); anims.forEach(a => a.cancel()); }, 250);\n"
                               "    return Promise.all(anims.map(a => a.finished)).then(() => { " + DONE + " });"),
    # Seeking to the end finishes the effect before its promise settles; the same-task cancel still follows a finish.
    "seek to end then cancel": rise("setTimeout(() => anims.forEach(a => { a.currentTime = 900; a.cancel(); }), 250);\n"
                                    "    return Promise.all(anims.map(a => a.finished)).catch(() => {}).then(() => { " + DONE + " });"),
}
END = "\n    return Promise.all(anims.map(a => a.finished)).then(() => { " + DONE + " });"
MIDFLIGHT = "setTimeout(() => anims.forEach((a, i) => { %s }), 250);"
# Detaching an effect before its end makes the browser report it finished without a cancel; that is never a finish.
DETACHED = {
    "effect cleared midflight": rise(MIDFLIGHT % "a.effect = null;" + "\n    return Promise.all(anims.map(a => a.finished)).then(() => {});"),
    "effect cleared midflight with end state": rise(MIDFLIGHT % "a.effect = null;" + END),
    "effect replaced midflight": rise(MIDFLIGHT % f"a.effect = new KeyframeEffect(marks[i], {KEYS}, {{duration: 900, fill: \"both\"}});" + END),
    "target cleared midflight": rise(MIDFLIGHT % "a.effect.target = null;" + END),
    "target moved midflight": rise(MIDFLIGHT % "a.effect.target = marks[(i + 1) % marks.length];" + END),
    "pseudo target moved midflight": rise(MIDFLIGHT % 'a.effect.pseudoElement = "::after";' + END),
}
ATTACHED = {
    "finish then detach": rise('setTimeout(() => { anims.forEach(a => a.finish()); anims.forEach(a => { a.effect = null; }); }, 250);' + END),
    "natural end then detach": rise("return Promise.all(anims.map(a => a.finished)).then(() => { " + DONE
                                    + " anims.forEach(a => { a.effect.target = null; a.effect = null; }); });"),
    "same effect and target assigned": rise(MIDFLIGHT % "a.effect = a.effect; a.effect.target = a.effect.target;" + END),
}
# The Animation constructor takes an effect from its animation without a setter; before an observed end that is unsupported.
TAKE = "new Animation(a.effect, document.timeline)"
CONSTRUCTED = {
    "idle constructor takes effect midflight": rise(MIDFLIGHT % (TAKE + ";") + "\n    return Promise.all(anims.map(a => a.finished)).then(() => {});"),
    "idle constructor takes effect midflight with end state": rise(MIDFLIGHT % (TAKE + ";") + END),
    "playing constructor takes effect midflight": rise(MIDFLIGHT % (TAKE + ".play();") + END),
    "playing constructor takes effect midflight with no end state": rise(MIDFLIGHT % (TAKE + ".play();")
                                                                         + "\n    return Promise.all(anims.map(a => a.finished)).then(() => {});"),
}
TAKEN_AFTER_END = rise("return Promise.all(anims.map(a => a.finished)).then(() => { " + DONE + " anims.forEach(a => { " + TAKE + "; }); });")
# Product code retains its reveal; after Stop it tries to retarget, clear, replace and remove the paused effects.
RETAINED = rise("window.kilnAnims = anims;" + END)
STOP_SETTERS = base.HELPERS + r"""
(async () => {
  const browser = await chromium.launch();
  try {
    const page = await (await browser.newContext({viewport: {width: 1280, height: 700}})).newPage();
    const r = {};
    await page.goto(cases.url);
    const {phase, act, inFrame, wait, show} = tools(page);
    const look = () => inFrame("kiln-rise", () => {
      const marks = Array.from(document.querySelectorAll("[data-ds-motion-subject] .kiln-mark"));
      return [(window.kilnAnims || []).map(a => [a.playState, a.effect ? marks.indexOf(a.effect.target) : -2, a.effect ? a.effect.pseudoElement : "none"]),
        marks.map(mark => getComputedStyle(mark).opacity + " " + getComputedStyle(mark).transform),
        document.getAnimations().filter(item => item.playState === "running").length];
    });
    await show("kiln-rise");
    r.playing = await wait("kiln-rise", ["playing"], 6000);
    await act("kiln-rise", "stop");
    r.stopped = await wait("kiln-rise", ["stopped"], 3000);
    await page.waitForTimeout(300);
    r.held = await look();
    r.poked = await inFrame("kiln-rise", () => {
      const anims = window.kilnAnims || [], stage = anims.length ? anims[0].effect.target.parentElement : null;
      anims.forEach(a => { a.effect.target = stage; });
      anims.forEach(a => { a.effect.pseudoElement = "::after"; });
      anims.forEach(a => { a.effect.target = null; });
      anims.forEach(a => { a.effect = new KeyframeEffect(stage, [{opacity: 0}, {opacity: 1}], 800); });
      anims.forEach(a => { a.effect = null; });
      return anims.length;
    });
    await page.waitForTimeout(700);
    r.after = await look();
    r.phase = await phase("kiln-rise");
    await act("kiln-rise", "replay");
    r.replay = await wait("kiln-rise", ["settled", "invalid"], 9000);
    console.log(JSON.stringify(r));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
"""
LONG = edit(fixture.PRODUCT_SCRIPT, "duration: 900, delay: i * 150", "duration: 5000, delay: i * 150")
LATE_REDUCED = edit(LONG, REDUCED_ARM, REDUCED_ARM.replace("return; }", (
    'setTimeout(() => stages.forEach(stage => stage.querySelectorAll(".kiln-mark").forEach('
    "mark => mark.animate([{opacity: 0}, {opacity: 1}], {duration: 900}))), 4000); return; }")))


class AcceptanceBrowserTests(unittest.TestCase):
    setUpClass = classmethod(base.RuntimeBrowserTests.setUpClass.__func__)
    tearDownClass = classmethod(base.RuntimeBrowserTests.tearDownClass.__func__)
    require, gallery, run_node = (base.RuntimeBrowserTests.require, base.RuntimeBrowserTests.gallery,
                                  base.RuntimeBrowserTests.run_node)

    def phases(self, cases):
        """cases: name -> (variant, script, css); returns NEGATIVE observations per name."""
        items = [{"name": name, "variant": variant, "stay": False,
                  "url": self.gallery("accept-" + name, script, css).resolve().as_uri()}
                 for name, (variant, script, css) in cases.items()]
        return self.run_node(NEGATIVE, {"items": items})

    def accept(self, name, script, css=CSS, row=KILN):
        self.require()
        os.environ.setdefault("PLAYWRIGHT_MODULE", self.module)
        report = verify_runtime_motion.run_acceptance(self.gallery("accept-run-" + name, script, css), [row])
        self.assertTrue(report["processes"] and all(item["exited"] for item in report["processes"]), report["processes"])
        return report, {item["mode"]: item for item in report["results"]}

    def assert_invalid(self, out, names):
        for name in names:
            with self.subTest(name):
                self.assertEqual("invalid", out[name]["seen"][-1], (out[name]["seen"], out[name]["status"]))
                self.assertNotIn("settled", out[name]["seen"])
                self.assertEqual([], out[name]["errors"])

    def test_transparent_owner_ancestor_and_pseudo_never_earn_credit(self):
        self.require()
        self.assert_invalid(self.phases(TRANSPARENT), TRANSPARENT)
        report, modes = self.accept("transparent-subject", *TRANSPARENT["transparent subject"][1:])
        self.assertEqual("FAIL", report["verdict"])
        self.assertEqual("invalid", modes["normal"]["first"], modes["normal"])

    def test_opacity_reveal_from_zero_still_earns_credit(self):
        self.require()
        script = edit(fixture.PRODUCT_SCRIPT, KEYS, "[{opacity: 0}, {opacity: 1}]")
        out = self.phases({"opacity reveal": ("kiln-rise", script, CSS)})
        self.assertEqual("settled", out["opacity reveal"]["seen"][-1], out["opacity reveal"])
        self.assertIn("3 source animations on span.kiln-mark (opacity) finished", out["opacity reveal"]["status"])
        report, _ = self.accept("opacity-reveal", script)
        self.assertEqual("PASS", report["verdict"], json.dumps(report["results"])[:3000])

    def test_infinite_or_structurally_invalid_effects_on_bound_owners_fail(self):
        self.require()
        cases = {name: ("kiln-rise", script, CSS) for name, script in MIXED.items()}
        # The CSS row: finite stripes plus an infinite CSS animation on another owner inside the same subject.
        cases["css finite plus infinite"] = ("belt-stripes", fixture.PRODUCT_SCRIPT,
                                             CSS + ".belt-count{display:inline-block;animation:belt-move 400ms linear infinite}")
        cases["infinite sibling outside the subject"] = ("kiln-rise", SIBLING, CSS)
        out = self.phases(cases)
        self.assert_invalid(out, list(MIXED) + ["css finite plus infinite"])
        self.assertEqual("settled", out["infinite sibling outside the subject"]["seen"][-1], out["infinite sibling outside the subject"])
        report, modes = self.accept("finite-plus-infinite", MIXED["finite plus infinite"])
        self.assertEqual("FAIL", report["verdict"])
        self.assertEqual("invalid", modes["normal"]["first"], modes["normal"])

    def test_cancellation_before_the_end_fails_and_finish_then_cancel_passes(self):
        self.require()
        cases = {name: (variant, script, CSS) for name, (variant, script) in CANCELLED.items()}
        cases.update({name: ("kiln-rise", script, CSS) for name, script in FINISHED.items()})
        # The fixture removes its stripes only after they ran to the end; the first load is a cold start.
        for index in range(2):
            cases[f"stripes cleanup after the end {index}"] = ("belt-stripes", fixture.PRODUCT_SCRIPT, CSS)
        out = self.phases(cases)
        self.assert_invalid(out, CANCELLED)
        for name in [name for name in cases if name not in CANCELLED]:
            with self.subTest(name):
                self.assertEqual("settled", out[name]["seen"][-1], out[name])
        report, modes = self.accept("cancelled-midflight", CANCELLED["all cancelled midflight"][1])
        self.assertEqual("FAIL", report["verdict"])
        self.assertEqual("invalid", modes["normal"]["first"], modes["normal"])

    def test_source_dispatched_cancel_event_cannot_lend_completion(self):
        self.require()
        out = self.phases({"untrusted cancel": ("belt-stripes", UNTRUSTED, CSS),
                           "stripes cleanup after the end": ("belt-stripes", fixture.PRODUCT_SCRIPT, CSS)})
        self.assert_invalid(out, ["untrusted cancel"])
        self.assertEqual("settled", out["stripes cleanup after the end"]["seen"][-1], out["stripes cleanup after the end"])
        report, modes = self.accept("untrusted-cancel", UNTRUSTED, row=STRIPES)
        self.assertEqual("FAIL", report["verdict"])
        self.assertEqual("invalid", modes["normal"]["first"], modes["normal"])

    def test_detachment_before_the_end_fails_and_detach_after_the_end_passes(self):
        self.require()
        cases = {name: ("kiln-rise", script, CSS) for name, script in {**DETACHED, **ATTACHED}.items()}
        out = self.phases(cases)
        self.assert_invalid(out, DETACHED)
        for name in ATTACHED:
            with self.subTest(name):
                self.assertEqual("settled", out[name]["seen"][-1], out[name])
                self.assertEqual([], out[name]["errors"])
        report, modes = self.accept("effect-cleared-midflight", DETACHED["effect cleared midflight with end state"])
        self.assertEqual("FAIL", report["verdict"])
        self.assertEqual("invalid", modes["normal"]["first"], modes["normal"])
        report, modes = self.accept("finish-then-detach", ATTACHED["finish then detach"])
        self.assertEqual("PASS", report["verdict"], json.dumps(report["results"])[:3000])
        self.assertEqual(("settled", "settled"), (modes["normal"]["first"], modes["normal"]["replay"]), modes["normal"])

    def test_constructor_taking_a_tracked_effect_before_its_end_fails(self):
        self.require()
        cases = {name: ("kiln-rise", script, CSS) for name, script in CONSTRUCTED.items()}
        cases.update({"natural end then constructor": ("kiln-rise", TAKEN_AFTER_END, CSS),
                      "control: all cancelled midflight": CANCELLED["all cancelled midflight"] + (CSS,),
                      "control: ordinary finite reveal": ("kiln-rise", fixture.PRODUCT_SCRIPT, CSS)})
        out = self.phases(cases)
        self.assert_invalid(out, list(CONSTRUCTED) + ["control: all cancelled midflight"])
        for name in ("natural end then constructor", "control: ordinary finite reveal"):
            with self.subTest(name):
                self.assertEqual("settled", out[name]["seen"][-1], out[name])
                self.assertEqual([], out[name]["errors"])
        report, modes = self.accept("constructor-midflight", CONSTRUCTED["idle constructor takes effect midflight with end state"])
        self.assertEqual("FAIL", report["verdict"])
        self.assertEqual("invalid", modes["normal"]["first"], modes["normal"])

    def test_stopped_effect_and_target_assignments_cannot_move_owned_motion(self):
        self.require()
        r = self.run_node(STOP_SETTERS, {"url": self.gallery("stop-setters", RETAINED).resolve().as_uri()})
        self.assertEqual("playing", r["playing"][-1], r)
        self.assertEqual("stopped", r["stopped"][-1], r)
        self.assertEqual(3, r["poked"], "the product retained its three reveal animations")
        self.assertEqual({"paused"}, {item[0] for item in r["held"][0]}, r["held"])
        self.assertEqual(0, r["held"][2])
        self.assertEqual(r["held"], r["after"], "no stopped assignment moved, cleared or replaced an effect")
        self.assertEqual("stopped", r["phase"])
        self.assertEqual("settled", r["replay"][-1], r["replay"])

    def test_reduced_window_spans_the_observed_normal_lifecycle(self):
        self.require()
        report, modes = self.accept("late-reduced", LATE_REDUCED)
        normal, system = modes["normal"], modes["system"]
        self.assertEqual("FAIL", report["verdict"])
        self.assertEqual(("settled", "settled"), (normal["first"], normal["replay"]), normal)
        self.assertGreaterEqual(normal["lifecycleMs"], 5000, normal)
        self.assertGreaterEqual(normal["reducedWindowMs"], max(3200, normal["lifecycleMs"] + 1600))
        self.assertEqual(normal["reducedWindowMs"], system["reducedWindowMs"])
        self.assertIn("invalid", normal["reducedSeen"], normal)
        for key in ("window", "toggleWindow"):
            with self.subTest(key):
                self.assertIn("invalid", system[key]["seen"], system)
                self.assertTrue(system[key]["sameGeneration"], system[key])
        report, modes = self.accept("long-compliant", LONG)
        normal, system = modes["normal"], modes["system"]
        self.assertEqual("PASS", report["verdict"], json.dumps(report["results"])[:3000])
        self.assertGreaterEqual(normal["reducedWindowMs"], normal["lifecycleMs"] + 1600)
        self.assertGreaterEqual(normal["reducedObservedMs"], normal["reducedWindowMs"])
        for key in ("window", "toggleWindow"):
            self.assertGreaterEqual(system[key]["observedMs"], system["reducedWindowMs"])
            self.assertTrue(system[key]["sameGeneration"])


class AcceptanceInputRaceTests(unittest.TestCase):
    """Real main(); TEST DOUBLES replace the pair checker and the browser boundary only."""

    def build(self, root):
        files = fixture.repo_files()
        for path, payload in files.items():
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_bytes(payload)
        data = fixture.registry()
        data["sourceBindings"]["hifi"]["sha256"] = hashlib.sha256(files[fixture.HIFI]).hexdigest()
        from render_design_system_preview import render_view

        (root / "design-system.json").write_bytes(json.dumps(data).encode("utf-8"))
        (root / "design-system.md").write_bytes(b"# Kiln Timer (synthetic fixture)\n")
        (root / "preview.html").write_bytes(render_view((root / "design-system.json").read_bytes(),
                                                        (root / "design-system.md").read_bytes(), root).encode("utf-8"))

    def run_main(self, mutate):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build(root)
            receipt = root / "receipt.json"

            def browser(preview, plan, **_):  # TEST DOUBLE: a passing observation that races one named input
                self.assertEqual(3, len(plan))
                if mutate:
                    mutate(root)
                return {"results": [{"variant": row["variant"], "pass": True} for row in plan], "verdict": "PASS",
                        "browser": "test-double", "processes": []}

            err = io.StringIO()
            with mock.patch.object(check_design_system_pair, "compare", return_value=[]), \
                    mock.patch.object(verify_runtime_motion, "run_acceptance", side_effect=browser), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                code = verify_runtime_motion.main(["--repo-root", str(root), "--registry", str(root / "design-system.json"),
                                                   "--markdown", str(root / "design-system.md"),
                                                   "--preview", str(root / "preview.html"), "--receipt", str(receipt)])
            return code, err.getvalue(), json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else None

    def test_unchanged_inputs_write_a_bound_pass_receipt(self):
        code, err, receipt = self.run_main(None)
        self.assertEqual(0, code, err)
        self.assertEqual("PASS", receipt["verdict"])
        self.assertEqual({"docs/design/evidence/mm-00%d-%s.json" % (n, case) for n in (1, 2, 3) for case in ("normal", "reduced")},
                         {row["path"] for row in receipt["evidence"].values()})
        self.assertEqual({"hifi", "uiDesign"}, set(receipt["sources"]))

    def test_evidence_changed_or_removed_during_playback_refuses_pass(self):
        for path in sorted(fixture.evidence_files()):
            def stale(root, path=path):
                (root / path).write_bytes(b'{"synthetic_mutated_evidence": true}')

            def removed(root, path=path):
                (root / path).unlink()
            for label, mutate in (("changed", stale), ("removed", removed)):
                with self.subTest(path=path, mutation=label):
                    code, err, receipt = self.run_main(mutate)
                    self.assertEqual((1, None), (code, receipt), err)
                    self.assertIn("stale", err)

    def test_evidence_symlink_substitution_refuses_pass(self):
        path = "docs/design/evidence/mm-001-reduced.json"

        def aliased(root):
            # Identical bytes behind a link: the safe path guard refuses the alias, so the evidence is stale.
            target = root / "alias-target.json"
            target.write_bytes((root / path).read_bytes())
            (root / path).unlink()
            os.symlink(target, root / path)
        try:
            with tempfile.TemporaryDirectory() as directory:
                os.symlink(Path(directory) / "probe", Path(directory) / "link")
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"symlinks unavailable here: {error}")
        code, err, receipt = self.run_main(aliased)
        self.assertEqual((1, None), (code, receipt), err)
        self.assertIn("stale", err)

    def test_hifi_source_changed_during_playback_refuses_pass(self):
        def edited(root):
            path = root / fixture.HIFI
            path.write_bytes(path.read_bytes() + b"\n")
        code, err, receipt = self.run_main(edited)
        self.assertEqual((1, None), (code, receipt), err)
        self.assertIn("stale", err)

    def test_ui_design_approval_changed_during_playback_refuses_pass(self):
        def edited(root):
            path = root / fixture.UI
            path.write_bytes(edit(path.read_text(encoding="utf-8"), "owner Fixture Owner", "owner Another Owner").encode("utf-8"))
        code, err, receipt = self.run_main(edited)
        self.assertEqual((1, None), (code, receipt), err)
        self.assertIn("stale", err)


if __name__ == "__main__":
    unittest.main()

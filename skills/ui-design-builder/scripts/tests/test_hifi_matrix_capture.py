"""hifi_matrix_capture: unit tests with a fake driver, plus one real-browser run.

The browser run needs Node Playwright and is required when PDH_REQUIRE_BROWSER_TESTS=1.
Synthetic fixture pages only; nothing here is real product evidence.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import hifi_matrix_capture as m  # noqa: E402
from assemble_ui_review import assemble  # noqa: E402
from review_evidence import build_receipt  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures/matrix-hifi"
HAS_PILLOW = importlib.util.find_spec("PIL") is not None
PACKAGE_DIR = "docs/design/ui-references/matrix"


def build_package(root, details_extra="", manifest_edit=None):
    """Assemble the fixture (two surfaces, two targets, three states each) under root."""
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    if manifest_edit:
        manifest_edit(manifest)
    source = root / "_src"
    source.mkdir(parents=True, exist_ok=True)
    (source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    entry = (FIXTURE / "index.html").read_text(encoding="utf-8").replace("__MANIFEST__", json.dumps(manifest))
    (source / "index.html").write_text(entry, encoding="utf-8")
    details = (FIXTURE / "details.html").read_text(encoding="utf-8").replace("</main>", details_extra + "</main>", 1)
    (source / "details.html").write_text(details, encoding="utf-8")
    package = root / PACKAGE_DIR
    assemble(source / "manifest.json", [f"index.html={source / 'index.html'}", f"details.html={source / 'details.html'}"],
             package, overwrite=True)
    return package


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FakeDriver:
    """Same call(op, **fields) surface as NodeDriver, answering from a script."""

    def __init__(self):
        self.environment = {"playwright": "fake", "chromium": "fake", "node": "fake"}
        self.calls, self.restarts, self.axis = [], 0, None
        self.overrides = {}      # (surface, state, target) -> {"geometry": {...}, "events": {...}, "raise": exc, "style": text}
        self.open_events = {}    # page -> events
        self.open_error = {}     # page -> exception
        self.axis_events = {}    # axis -> events
        self.paint = {}          # capture name -> text that changes its pixels

    def start(self):
        pass

    def stop(self):
        pass

    def restart(self):
        self.restarts += 1

    def count(self, op):
        return sum(1 for name, _ in self.calls if name == op)

    def call(self, op, timeout=None, **fields):
        self.calls.append((op, fields))
        return getattr(self, "_" + op)(fields)

    def _open(self, fields):
        if fields["page"] in self.open_error:
            raise self.open_error[fields["page"]]
        return {"result": {}, "events": self.open_events.get(fields["page"], {})}

    def _axis(self, fields):
        self.axis = None if fields["name"] == "none" else fields["name"]
        return {"result": {}, "events": {}}

    def _case(self, fields):
        key = (fields["surface"], fields["state"], fields["target"])
        script = self.overrides.get(key, {})
        if "raise" in script:
            raise script["raise"]
        geometry = {
            "canvasWidth": float(fields["target"]) if fields["target"].isdigit() else 0.0,
            "surface": {"x": 0, "y": 0, "width": 390, "height": 300}, "scrollWidth": 390, "clientWidth": 390,
            "scrollHeight": 300, "clientHeight": 300, "overflowX": 0, "elementCount": 3 + len(fields["state"]),
            "scanned": 3, "overlapCount": 0, "overlaps": [], "stateViews": 1,
        }
        geometry.update(script.get("geometry", {}))
        events = dict(script.get("events", {}))
        if self.axis in self.axis_events:
            events = self.axis_events[self.axis]
        probe = {"geometry": geometry, "rectsSha256": sha("rects" + "".join(key)),
                 "styleSha256": sha("style" + script.get("style", "") + (self.axis or ""))}
        return {"result": {"problems": script.get("problems", []), "probe": None if script.get("problems") else probe,
                           "settle": {"waitedMs": 0, "finished": 0, "paused": 0, "capped": False}}, "events": events}

    def _shot(self, fields):
        path = Path(fields["path"])
        name = path.name
        if HAS_PILLOW:
            from PIL import Image
            shade = int(sha(name + self.paint.get(name, ""))[:2], 16)
            Image.new("RGB", (6, 4), (shade, 40, 90)).save(path)
        else:
            path.write_bytes(name.encode("utf-8"))
        return {"result": {}, "events": {}}


class Cli:
    """Run main() against a temporary repository root with a fake driver."""

    def __init__(self, test):
        self.test = test
        self.tmp = tempfile.TemporaryDirectory()
        test.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = build_package(self.root)
        self.runs = 0

    def run(self, driver, *extra, out=None, package=None):
        self.runs += 1
        out = out or f"docs/evidence/run{self.runs}"
        argv = ["--repo-root", str(self.root), "--package", str(package or self.package), "--out", out, *extra]
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = m.main(argv, make_driver=lambda package, root, scratch: driver)
        text = buffer.getvalue().strip().splitlines()
        return code, json.loads(text[-1]) if text else {}, self.root / out

    def load(self, out):
        return (json.loads((out / m.OUTPUT_NAME).read_text(encoding="utf-8")),
                json.loads((out / m.SIDECAR_NAME).read_text(encoding="utf-8")))


class MatrixExpansionTests(unittest.TestCase):
    def package(self, surfaces, widths=None):
        widths = widths or {"index.html": {"390": 390, "1200": 1200}}
        return m.Package({"surfaces": surfaces}, {}, {}, {}, widths)

    def surface(self, ident="UI-001", states=("ready", "loading"), targets=(390, 1200), page="index.html"):
        return {"id": ident, "page": page, "route": "/", "states": list(states), "responsive": {"targets": list(targets)}}

    def test_cases_follow_manifest_order_and_skip_not_applicable_states(self):
        package = self.package([self.surface(states=("ready", "error:n/a", "loading")), self.surface("UI-002", ("ready",))])
        cases = m.expand_matrix(package)
        self.assertEqual([("UI-001", "ready", "390"), ("UI-001", "ready", "1200"), ("UI-001", "loading", "390"),
                          ("UI-001", "loading", "1200"), ("UI-002", "ready", "390"), ("UI-002", "ready", "1200")],
                         [c.key for c in cases])

    def test_only_keeps_the_named_surfaces(self):
        package = self.package([self.surface(), self.surface("UI-002", ("ready",))])
        self.assertEqual({"UI-002"}, {c.surface for c in m.expand_matrix(package, only={"UI-002"})})

    def test_derived_states_are_observed_once_at_the_smallest_target(self):
        package = self.package([self.surface(states=("ready", "toast"), targets=("compact", "regular"))],
                               {"index.html": {"compact": 390, "regular": 820}})
        cases = m.expand_matrix(package, derived={"UI-001": ["toast"]})
        self.assertEqual([("ready", "compact"), ("ready", "regular"), ("toast", "compact")],
                         [(c.state, c.target) for c in cases])

    def test_representative_targets_follow_the_checker_list_rule(self):
        # Numeric widths compare by value whatever their order; size classes keep listed order.
        self.assertEqual(("390", "1200"), m.representative_targets(["768", "1200", "390"]))
        self.assertEqual(("regular", "compact"), m.representative_targets(["regular", "compact"]))
        from check_ui_design_contract import representative_targets as checker_rule
        for targets in (["768", "1200", "390"], ["regular", "compact"], ["phone-small", "phone-large"]):
            self.assertEqual(checker_rule(targets), m.representative_targets(targets))

    def test_axis_sample_is_ready_plus_the_busiest_state_at_the_extreme_targets(self):
        rows = [self.surface(states=("ready", "loading", "empty"), targets=(768, 390, 1200))]
        widths = {"390": 390, "768": 768, "1200": 1200}
        counts = {("UI-001", "ready"): 9, ("UI-001", "loading"): 4, ("UI-001", "empty"): 30}
        sampled = m.sample_axis_cases(rows, "index.html", widths, counts)
        self.assertEqual([("ready", "390"), ("ready", "1200"), ("empty", "390"), ("empty", "1200")],
                         [(c.state, c.target) for c in sampled])

    def test_axis_sample_does_not_repeat_ready_and_falls_back_to_the_first_state(self):
        widths = {"390": 390, "1200": 1200}
        busy_ready = m.sample_axis_cases([self.surface(states=("ready", "empty"))], "index.html", widths,
                                         {("UI-001", "ready"): 50, ("UI-001", "empty"): 2})
        self.assertEqual(2, len(busy_ready))
        no_ready = m.sample_axis_cases([self.surface(states=("idle", "busy:n/a"))], "index.html", widths, {})
        self.assertEqual({"idle"}, {c.state for c in no_ready})


class NamingAndFingerprintTests(unittest.TestCase):
    def test_capture_name_carries_a_stable_tuple_hash(self):
        case = m.Case("UI-001", "index.html", "ready", "390")
        name = m.capture_name(case)
        self.assertRegex(name, r"^UI-001-ready-390-[0-9a-f]{10}\.png$")
        self.assertEqual(name, m.capture_name(m.Case("UI-001", "index.html", "ready", "390")))
        self.assertNotEqual(name, m.capture_name(m.Case("UI-001", "index.html", "ready", "1200")))
        self.assertRegex(m.capture_name(replace(case, axis="dark")), r"^UI-001-ready-390-dark-[0-9a-f]{10}\.png$")

    def test_names_that_slug_alike_still_differ(self):
        a = m.capture_name(m.Case("UI-001", "index.html", "needs review", "390"))
        b = m.capture_name(m.Case("UI-001", "index.html", "needs/review", "390"))
        self.assertTrue(a.startswith("UI-001-needs_review-390-"))
        self.assertNotEqual(a, b)

    def test_render_fingerprint_tracks_geometry_rects_and_styles(self):
        probe = {"geometry": {"a": 1, "b": 2}, "rectsSha256": "r" * 64, "styleSha256": "s" * 64}
        fingerprint = m.render_fingerprint(probe)
        self.assertRegex(fingerprint, r"^[0-9a-f]{64}$")
        self.assertEqual(fingerprint, m.render_fingerprint(dict(probe, geometry={"b": 2, "a": 1})))
        for change in ({"geometry": {"a": 2, "b": 2}}, {"rectsSha256": "x" * 64}, {"styleSha256": "x" * 64}):
            self.assertNotEqual(fingerprint, m.render_fingerprint(dict(probe, **change)))

    def test_entry_page_identity_ignores_manifest_page_hashes_only(self):
        manifest = {"schema": "ui-hifi/2", "surfaces": [{"id": "UI-001"}], "pages": [{"path": "a.html", "sha256": "1" * 64}]}
        html = '<html><script id="ui-hifi-manifest" type="application/json">' + json.dumps(manifest) + "</script></html>"
        moved = dict(manifest, pages=[{"path": "a.html", "sha256": "2" * 64}])
        moved_html = html.replace("1" * 64, "2" * 64)
        self.assertEqual(m.page_key("index.html", html, manifest, html.encode()),
                         m.page_key("index.html", moved_html, moved, moved_html.encode()))
        edited = html.replace("</html>", "<p>edit</p></html>")
        self.assertNotEqual(m.page_key("index.html", html, manifest, html.encode()),
                            m.page_key("index.html", edited, manifest, edited.encode()))
        self.assertEqual(hashlib.sha256(b"child").hexdigest(), m.page_key("a.html", "child", manifest, b"child"))


class RunOutputTests(unittest.TestCase):
    def test_a_clean_run_writes_a_receipt_ready_ui_output_3(self):
        cli = Cli(self)
        code, summary, out = cli.run(FakeDriver())
        self.assertEqual(0, code, summary)
        output, sidecar = cli.load(out)
        self.assertEqual(["schema", "check", "subject", "matrix", "results", "sandbox", "console", "network",
                          "navigation", "popups", "forms", "popupAttempts", "formAttempts", "execution"], list(output))
        self.assertEqual(("ui-output/3", "hifi-browser"), (output["schema"], output["check"]))
        self.assertEqual({"path": f"{PACKAGE_DIR}/index.html", "sha256": hashlib.sha256(
            (cli.package / "index.html").read_bytes()).hexdigest()}, output["subject"])
        self.assertEqual(12, len(output["matrix"]["cases"]))
        self.assertEqual(output["matrix"]["cases"], [{k: r[k] for k in ("surface", "state", "target")} for r in output["results"]])
        self.assertEqual({"PASS"}, {r["result"] for r in output["results"]})
        self.assertEqual({"network": "disabled", "topNavigation": "allowlisted-local-pages", "popups": "blocked",
                          "forms": "blocked"}, output["sandbox"])
        execution = output["execution"]
        self.assertEqual(("playwright", "sandboxed-offline-browser"), (execution["tool"], execution["method"]))
        self.assertLessEqual(datetime.fromisoformat(execution["startedAt"]), datetime.fromisoformat(execution["finishedAt"]))
        self.assertTrue(execution["environment"]["python"] and execution["environment"]["chromium"])
        paths = [a["path"] for a in execution["artifacts"]]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertIn(f"{PACKAGE_DIR}/details.html", paths)
        self.assertIn(f"docs/evidence/run1/{m.SIDECAR_NAME}", paths)
        self.assertEqual(12, sum(1 for p in paths if p.endswith(".png")))
        for record in sidecar["cases"]:
            self.assertRegex(record["renderFingerprint"], r"^[0-9a-f]{64}$")
            self.assertTrue(record["geometry"]["elementCount"] and isinstance(record["durationMs"], int))
            self.assertLessEqual(datetime.fromisoformat(record["startedAt"]), datetime.fromisoformat(record["finishedAt"]))
            self.assertIsNone(record["carriedFrom"])
            self.assertEqual(hashlib.sha256((cli.root / record["capture"]["path"]).read_bytes()).hexdigest(),
                             record["capture"]["sha256"])
        receipt = build_receipt(cli.root, f"docs/evidence/run1/{m.OUTPUT_NAME}")
        self.assertEqual("PASS", receipt["result"])
        self.assertEqual("hifi-browser", receipt["check"])

    def test_each_page_opens_once_and_cases_never_reload(self):
        cli, driver = Cli(self), FakeDriver()
        cli.run(driver)
        self.assertEqual(["index.html", "details.html"], [f["page"] for op, f in driver.calls if op == "open"])
        self.assertEqual(12, driver.count("case"))

    def test_only_writes_a_partial_matrix(self):
        cli = Cli(self)
        code, _, out = cli.run(FakeDriver(), "--only", "UI-002")
        output, sidecar = cli.load(out)
        self.assertEqual(0, code)
        self.assertEqual({"UI-002"}, {c["surface"] for c in output["matrix"]["cases"]})
        self.assertEqual(["UI-002"], sidecar["run"]["only"])

    def test_derived_once_drops_the_larger_targets_of_derived_states(self):
        cli = Cli(self)
        derived = cli.root / "derived.json"
        derived.write_text(json.dumps({"UI-001": ["empty"]}), encoding="utf-8")
        code, _, out = cli.run(FakeDriver(), "--derived-once", "--derived", str(derived))
        output, sidecar = cli.load(out)
        self.assertEqual(0, code)
        empty = [c["target"] for c in output["matrix"]["cases"] if c["surface"] == "UI-001" and c["state"] == "empty"]
        self.assertEqual(["390"], empty)
        self.assertTrue(sidecar["run"]["derivedOnce"])
        self.assertEqual(11, len(output["matrix"]["cases"]))


class CarryTests(unittest.TestCase):
    def first_run(self, cli, driver=None):
        driver = driver or FakeDriver()
        code, _, out = cli.run(driver)
        self.assertEqual(0, code)
        return out

    def test_unchanged_cases_are_carried_without_a_new_screenshot(self):
        cli = Cli(self)
        first = self.first_run(cli)
        driver = FakeDriver()
        code, summary, out = cli.run(driver, "--carry-from", str(first / m.OUTPUT_NAME))
        output, sidecar = cli.load(out)
        _, previous = cli.load(first)
        self.assertEqual((0, 12), (code, summary["carried"]))
        self.assertEqual(0, driver.count("shot"))
        self.assertEqual([], [p for p in (a["path"] for a in output["execution"]["artifacts"]) if p.startswith("docs/evidence/run2/") and p.endswith(".png")])
        source = {"path": f"docs/evidence/run1/{m.OUTPUT_NAME}",
                  "sha256": hashlib.sha256((first / m.OUTPUT_NAME).read_bytes()).hexdigest()}
        for record, before in zip(sidecar["cases"], previous["cases"]):
            self.assertIsNone(record["capture"])
            self.assertEqual({"result": "PASS", "pageSha256": before["pageSha256"], "capture": before["capture"],
                              "sourceOutput": source}, record["carriedFrom"])
        self.assertEqual("PASS", build_receipt(cli.root, f"docs/evidence/run2/{m.OUTPUT_NAME}")["result"])
        self.assertEqual({"PASS"}, {r["result"] for r in output["results"]})

    def test_carried_captures_stay_bound_in_the_execution_artifacts(self):
        cli = Cli(self)
        first = self.first_run(cli)
        _, _, out = cli.run(FakeDriver(), "--carry-from", str(first / m.OUTPUT_NAME))
        output, _ = cli.load(out)
        carried = [a["path"] for a in output["execution"]["artifacts"] if a["path"].endswith(".png")]
        self.assertEqual(12, len(carried))
        self.assertTrue(all(p.startswith("docs/evidence/run1/") for p in carried))

    def test_recapture_carried_takes_a_new_screenshot_and_keeps_the_carry_record(self):
        cli = Cli(self)
        first = self.first_run(cli)
        driver = FakeDriver()
        _, summary, out = cli.run(driver, "--carry-from", str(first / m.OUTPUT_NAME), "--recapture-carried")
        _, sidecar = cli.load(out)
        self.assertEqual((12, 12), (summary["carried"], driver.count("shot")))
        self.assertTrue(all(r["capture"] and r["carriedFrom"] for r in sidecar["cases"]))

    def test_a_changed_fingerprint_is_not_carried(self):
        cli = Cli(self)
        first = self.first_run(cli)
        driver = FakeDriver()
        driver.overrides[("UI-001", "loading", "390")] = {"style": "new colour"}
        _, summary, out = cli.run(driver, "--carry-from", str(first / m.OUTPUT_NAME))
        _, sidecar = cli.load(out)
        changed = [r for r in sidecar["cases"] if r["carriedFrom"] is None]
        self.assertEqual((11, 1), (summary["carried"], len(changed)))
        self.assertEqual(("UI-001", "loading", "390"), (changed[0]["surface"], changed[0]["state"], changed[0]["target"]))
        self.assertTrue(changed[0]["capture"])
        self.assertEqual(1, driver.count("shot"))

    def test_an_edited_page_with_an_unchanged_fingerprint_still_carries(self):
        cli = Cli(self)
        first = self.first_run(cli)
        build_package(cli.root, details_extra="<p>edit</p>")   # new page bytes, same render fingerprint
        driver = FakeDriver()
        _, summary, out = cli.run(driver, "--carry-from", str(first / m.OUTPUT_NAME))
        _, sidecar = cli.load(out)
        self.assertEqual((12, 0), (summary["carried"], driver.count("shot")))
        self.assertTrue(all(record["carriedFrom"] is not None for record in sidecar["cases"]))

    def test_a_failed_previous_row_or_a_tampered_capture_is_not_carried(self):
        cli = Cli(self)
        driver = FakeDriver()
        driver.overrides[("UI-002", "error", "1200")] = {"geometry": {"overflowX": 30}}
        code, _, first = cli.run(driver)
        self.assertEqual(1, code)
        _, previous = cli.load(first)
        tampered = next(r for r in previous["cases"] if (r["surface"], r["state"], r["target"]) == ("UI-001", "ready", "390"))
        (cli.root / tampered["capture"]["path"]).write_bytes(b"changed after the fact")
        _, _, out = cli.run(FakeDriver(), "--carry-from", str(first / m.OUTPUT_NAME))
        _, sidecar = cli.load(out)
        not_carried = {(r["surface"], r["state"], r["target"]) for r in sidecar["cases"] if r["carriedFrom"] is None}
        self.assertEqual({("UI-002", "error", "1200"), ("UI-001", "ready", "390")}, not_carried)

    def test_a_carry_source_that_is_not_this_tools_output_is_refused(self):
        cli = Cli(self)
        bogus = cli.root / "other.json"
        bogus.write_text(json.dumps({"schema": "ui-output/3", "execution": {"artifacts": []}}), encoding="utf-8")
        code, summary, _ = cli.run(FakeDriver(), "--carry-from", str(bogus))
        self.assertEqual(2, code)
        self.assertIn(m.SIDECAR_NAME, summary["error"])

    @unittest.skipUnless(HAS_PILLOW, "Pillow is not installed")
    def test_diff_against_records_identical_and_changed_pixels(self):
        cli = Cli(self)
        first = self.first_run(cli)
        driver = FakeDriver()
        name = m.capture_name(m.Case("UI-001", "index.html", "ready", "390"))
        driver.paint[name] = "different"
        _, _, out = cli.run(driver, "--diff-against", str(first))
        _, sidecar = cli.load(out)
        diffs = {(r["surface"], r["state"], r["target"]): r["pixelDiff"] for r in sidecar["cases"]}
        self.assertEqual("changed", diffs[("UI-001", "ready", "390")]["status"])
        self.assertGreater(diffs[("UI-001", "ready", "390")]["ratio"], 0)
        self.assertEqual(("identical", 0.0), tuple(diffs[("UI-001", "ready", "1200")][k] for k in ("status", "ratio")))


class AxisTests(unittest.TestCase):
    def test_axes_run_on_the_sampled_cases_and_stay_out_of_the_matrix(self):
        cli, driver = Cli(self), FakeDriver()
        code, summary, out = cli.run(driver, "--axes", "dark,zoom-200")
        output, sidecar = cli.load(out)
        self.assertEqual(0, code)
        self.assertEqual(12, len(output["matrix"]["cases"]))
        # per surface: ready + the busiest state (loading, most nodes), smallest and largest target, two axes
        self.assertEqual(2 * 2 * 4, len(sidecar["axes"]))
        self.assertEqual(16, summary["axisCases"])
        self.assertEqual({"dark", "zoom-200"}, {r["axis"] for r in sidecar["axes"]})
        names = [r["capture"]["path"].rsplit("/", 1)[1] for r in sidecar["axes"]]
        self.assertTrue(all("-dark-" in n or "-zoom-200-" in n for n in names))
        base = {(r["surface"], r["state"], r["target"]): r["renderFingerprint"] for r in sidecar["cases"]}
        dark = next(r for r in sidecar["axes"] if r["axis"] == "dark")
        self.assertNotEqual(base[(dark["surface"], dark["state"], dark["target"])], dark["renderFingerprint"])
        applied = [f["name"] for op, f in driver.calls if op == "axis"]
        self.assertEqual(["dark", "none", "zoom-200", "none"] * 2, applied)
        self.assertEqual("PASS", build_receipt(cli.root, f"docs/evidence/run1/{m.OUTPUT_NAME}")["result"])

    def test_axis_artifacts_are_bound_in_the_execution_block(self):
        cli = Cli(self)
        _, _, out = cli.run(FakeDriver(), "--axes", "dark")
        output, sidecar = cli.load(out)
        paths = {a["path"] for a in output["execution"]["artifacts"]}
        self.assertTrue({r["capture"]["path"] for r in sidecar["axes"]} <= paths)

    def test_an_axis_failure_fails_the_run_but_not_the_base_transcript(self):
        cli, driver = Cli(self), FakeDriver()
        driver.axis_events["forced-colors"] = {"console": [{"source": "javascript", "level": "exception", "message": "Uncaught x"}]}
        code, summary, out = cli.run(driver, "--axes", "forced-colors")
        output, sidecar = cli.load(out)
        self.assertEqual((1, 8), (code, summary["axisFail"]))
        self.assertEqual({"PASS"}, {r["result"] for r in output["results"]})
        self.assertEqual([], output["console"])
        self.assertTrue(all("console exception" in r["reasons"][0] for r in sidecar["axes"]))

    def test_the_four_axes_are_supported_and_others_refused(self):
        self.assertEqual(("dark", "reduced-motion", "forced-colors", "zoom-200"), m.AXES)
        code, summary, _ = Cli(self).run(FakeDriver(), "--axes", "sepia")
        self.assertEqual(2, code)
        self.assertIn("sepia", summary["error"])


class FailureTests(unittest.TestCase):
    def results(self, driver, *extra):
        cli = Cli(self)
        code, summary, out = cli.run(driver, *extra)
        output, sidecar = cli.load(out)
        return code, summary, output, {(r["surface"], r["state"], r["target"]): r for r in sidecar["cases"]}

    def test_console_errors_fail_the_case_but_the_mandated_csp_row_does_not(self):
        driver = FakeDriver()
        csp = {"source": "security", "level": "error", "message": "Unrecognized Content-Security-Policy directive 'navigate-to'."}
        driver.overrides[("UI-001", "ready", "390")] = {"events": {"console": [csp]}}
        driver.overrides[("UI-001", "ready", "1200")] = {"events": {"console": [
            {"source": "console-api", "level": "error", "message": "boom"}]}}
        code, _, output, cases = self.results(driver)
        self.assertEqual(1, code)
        self.assertEqual("PASS", cases[("UI-001", "ready", "390")]["result"])
        self.assertEqual("FAIL", cases[("UI-001", "ready", "1200")]["result"])
        self.assertIn("boom", cases[("UI-001", "ready", "1200")]["reasons"][0])
        self.assertEqual(2, len(output["console"]))
        self.assertIn("FAIL", {r["result"] for r in output["results"]})

    def test_external_requests_navigations_popups_and_forms_fail_the_case(self):
        events = {"network": [{"url": "https://example.com/a.png"}], "navigation": [{"url": "https://example.com/"}],
                  "popups": [{"url": "https://example.com/p"}], "forms": [{"action": "https://example.com/post"}]}
        driver = FakeDriver()
        driver.overrides[("UI-002", "loading", "390")] = {"events": events}
        code, _, output, cases = self.results(driver)
        reasons = " | ".join(cases[("UI-002", "loading", "390")]["reasons"])
        self.assertEqual(1, code)
        for word in ("external request", "navigation attempt", "popup attempt", "form attempt"):
            self.assertIn(word, reasons)
        self.assertEqual((1, 1), (output["popupAttempts"], output["formAttempts"]))
        self.assertEqual("PASS", cases[("UI-002", "loading", "1200")]["result"])

    def test_page_load_errors_fail_every_case_on_that_page(self):
        driver = FakeDriver()
        driver.open_events["details.html"] = {"console": [{"source": "javascript", "level": "exception", "message": "Uncaught"}]}
        _, _, _, cases = self.results(driver)
        self.assertEqual({"FAIL"}, {r["result"] for k, r in cases.items() if k[0] == "UI-002"})
        self.assertEqual({"PASS"}, {r["result"] for k, r in cases.items() if k[0] == "UI-001"})
        self.assertTrue(cases[("UI-002", "ready", "390")]["reasons"][0].startswith("page load:"))

    def test_horizontal_overflow_and_a_missing_state_view_fail_the_case(self):
        driver = FakeDriver()
        driver.overrides[("UI-001", "empty", "390")] = {"geometry": {"overflowX": 40}}
        driver.overrides[("UI-001", "empty", "1200")] = {"geometry": {"stateViews": 0}}
        _, _, _, cases = self.results(driver)
        self.assertIn("horizontal overflow 40px", cases[("UI-001", "empty", "390")]["reasons"][0])
        self.assertIn("data-hifi-state-view", cases[("UI-001", "empty", "1200")]["reasons"][0])

    def test_missing_controls_fail_the_case_without_a_fingerprint(self):
        driver = FakeDriver()
        driver.overrides[("UI-001", "ready", "390")] = {"problems": ["state control missing: UI-001 ready"]}
        _, _, _, cases = self.results(driver)
        record = cases[("UI-001", "ready", "390")]
        self.assertEqual(("FAIL", None, None), (record["result"], record["renderFingerprint"], record["capture"]))

    def test_a_hung_case_fails_the_case_restarts_the_browser_and_carries_on(self):
        driver = FakeDriver()
        driver.overrides[("UI-001", "loading", "390")] = {"raise": m.DriverTimeout("case gave no reply within 40s")}
        code, summary, _, cases = self.results(driver)
        self.assertEqual((1, 1), (code, summary["restarts"]))
        self.assertEqual("FAIL", cases[("UI-001", "loading", "390")]["result"])
        self.assertIn("timed out", cases[("UI-001", "loading", "390")]["reasons"][0])
        self.assertEqual(11, sum(1 for r in cases.values() if r["result"] == "PASS"))
        self.assertEqual(1, driver.restarts)
        reopened = [f["page"] for op, f in driver.calls if op == "open"]
        self.assertEqual(["index.html", "index.html", "details.html"], reopened)

    def test_too_many_restarts_block_the_remaining_cases(self):
        driver = FakeDriver()
        for state in ("ready", "loading", "empty"):
            for target in ("390", "1200"):
                driver.overrides[("UI-001", state, target)] = {"raise": m.DriverTimeout("no reply")}
        code, _, output, cases = self.results(driver)
        results = [r["result"] for r in output["results"]]
        self.assertEqual(1, code)
        self.assertEqual(["FAIL"] * 4 + ["BLOCKED"] * 8, results)
        self.assertIn("restart limit", cases[("UI-002", "ready", "390")]["reasons"][0])

    def test_cases_after_an_aborted_run_do_not_reopen_pages(self):
        driver = FakeDriver()
        for state in ("ready", "loading", "empty"):
            for target in ("390", "1200"):
                driver.overrides[("UI-001", state, target)] = {"raise": m.DriverTimeout("no reply")}
        self.results(driver)
        self.assertNotIn("details.html", [f["page"] for op, f in driver.calls if op == "open"])

    def test_a_driver_error_fails_only_that_case(self):
        driver = FakeDriver()
        driver.overrides[("UI-002", "ready", "390")] = {"raise": m.DriverError("locator.click: Timeout 30000ms exceeded.")}
        _, summary, _, cases = self.results(driver)
        self.assertEqual("FAIL", cases[("UI-002", "ready", "390")]["result"])
        self.assertIn("driver error", cases[("UI-002", "ready", "390")]["reasons"][0])
        self.assertEqual(0, summary["restarts"])

    def test_a_page_that_will_not_open_fails_its_cases(self):
        driver = FakeDriver()
        driver.open_error["details.html"] = m.DriverError("page did not load: details.html")
        _, _, _, cases = self.results(driver)
        self.assertEqual({"FAIL"}, {r["result"] for k, r in cases.items() if k[0] == "UI-002"})
        self.assertTrue(cases[("UI-002", "ready", "390")]["reasons"][0].startswith("page did not open"))
        self.assertEqual(6, driver.count("case"))   # the unopened page is never driven


class UsageTests(unittest.TestCase):
    def test_bad_arguments_exit_2_before_any_browser_work(self):
        cli = Cli(self)
        driver = FakeDriver()
        derived = cli.root / "derived.json"
        derived.write_text("{}", encoding="utf-8")
        cases = [
            (("--only", "UI-999"), "unknown surfaces"),
            (("--derived-once",), "--derived"),
            (("--derived", str(derived)), "--derived-once"),
        ]
        for extra, message in cases:
            code, summary, _ = cli.run(driver, *extra)
            self.assertEqual(2, code, extra)
            self.assertIn(message, summary["error"])
        self.assertEqual([], driver.calls)

    def test_out_must_be_new_unless_overwrite_is_given(self):
        cli = Cli(self)
        self.assertEqual(0, cli.run(FakeDriver(), out="docs/evidence/same")[0])
        code, summary, _ = cli.run(FakeDriver(), out="docs/evidence/same")
        self.assertEqual(2, code)
        self.assertIn("--overwrite", summary["error"])
        self.assertEqual(0, cli.run(FakeDriver(), "--overwrite", out="docs/evidence/same")[0])

    def test_package_and_out_must_be_inside_the_repository(self):
        cli = Cli(self)
        with tempfile.TemporaryDirectory() as elsewhere:
            code, summary, _ = cli.run(FakeDriver(), out=str(Path(elsewhere) / "evidence"))
        self.assertEqual(2, code)
        self.assertIn("inside --repo-root", summary["error"])

    def test_a_package_that_differs_from_its_manifest_hash_is_refused(self):
        cli = Cli(self)
        details = cli.package / "details.html"
        details.write_text(details.read_text(encoding="utf-8") + "<!-- edited -->", encoding="utf-8")
        code, summary, _ = cli.run(FakeDriver())
        self.assertEqual(2, code)
        self.assertIn("manifest hash", summary["error"])

    def test_a_missing_shell_width_map_for_named_targets_is_refused(self):
        cli = Cli(self)
        shutil.rmtree(cli.root / "docs")
        build_package(cli.root, manifest_edit=lambda manifest: manifest["surfaces"][1]["responsive"].update(targets=["compact", "regular"]))
        code, summary, _ = cli.run(FakeDriver())
        self.assertEqual(2, code)
        self.assertIn("data-hifi-target-widths", summary["error"])


class RealBrowserTests(unittest.TestCase):
    """Real Chromium over the fixture package: two surfaces, two targets, three states, a dark axis."""

    def playwright(self):
        node = shutil.which("node")
        module = os.environ.get("PLAYWRIGHT_MODULE")
        if not module:
            candidate = SCRIPTS.parents[2] / "node_modules" / "playwright"
            module = str(candidate) if candidate.exists() else None
        if not node or not module or not Path(module).exists():
            message = "Required browser test prerequisite missing: Node.js and PLAYWRIGHT_MODULE"
            if os.environ.get("PDH_REQUIRE_BROWSER_TESTS") == "1":
                self.fail(message)
            self.skipTest(message)
        return module

    def test_matrix_capture_in_real_chromium(self):
        module = self.playwright()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = build_package(root)
            base = ["--repo-root", str(root), "--package", str(package)]

            def run(*extra):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer), mock.patch.dict(os.environ, {"PLAYWRIGHT_MODULE": module}):
                    code = m.main(base + list(extra))
                return code, buffer.getvalue()

            code, text = run("--out", "docs/evidence/first", "--axes", "dark,reduced-motion")
            self.assertEqual(0, code, text)
            first = root / "docs/evidence/first"
            output = json.loads((first / m.OUTPUT_NAME).read_text(encoding="utf-8"))
            sidecar = json.loads((first / m.SIDECAR_NAME).read_text(encoding="utf-8"))
            self.assertEqual(12, len(output["results"]))
            self.assertEqual({"PASS"}, {r["result"] for r in output["results"]})
            self.assertEqual("PASS", build_receipt(root, f"docs/evidence/first/{m.OUTPUT_NAME}")["result"])
            self.assertEqual([], output["network"] + output["navigation"] + output["popups"] + output["forms"])
            for row in output["console"]:
                self.assertEqual("Unrecognized Content-Security-Policy directive 'navigate-to'.", row["message"])
            cases = {(r["surface"], r["state"], r["target"]): r for r in sidecar["cases"]}
            self.assertEqual(12, len(cases))
            self.assertEqual(390, cases[("UI-001", "ready", "390")]["geometry"]["canvasWidth"])
            self.assertEqual(1200, cases[("UI-002", "error", "1200")]["geometry"]["canvasWidth"])
            self.assertEqual(1, cases[("UI-001", "loading", "390")]["settle"]["paused"])   # the spinner never settles
            self.assertEqual(len({r["renderFingerprint"] for r in cases.values()}), 12)
            for record in cases.values():
                self.assertEqual(b"\x89PNG", (root / record["capture"]["path"]).read_bytes()[:4])
            dark = [r for r in sidecar["axes"] if r["axis"] == "dark"]
            self.assertEqual(4, len(dark))   # ready is the busiest state here: two surfaces x two targets
            for record in dark:
                self.assertNotEqual(cases[(record["surface"], record["state"], record["target"])]["renderFingerprint"],
                                    record["renderFingerprint"])
            reduced = next(r for r in sidecar["axes"] if r["axis"] == "reduced-motion")
            self.assertEqual(cases[(reduced["surface"], reduced["state"], reduced["target"])]["renderFingerprint"],
                             reduced["renderFingerprint"])

            code, text = run("--out", "docs/evidence/second", "--carry-from", str(first / m.OUTPUT_NAME))
            self.assertEqual(0, code, text)
            second = json.loads((root / "docs/evidence/second" / m.SIDECAR_NAME).read_text(encoding="utf-8"))
            self.assertEqual(12, second["run"]["carried"])
            self.assertEqual([], list((root / "docs/evidence/second").glob("*.png")))

            details = package / "details.html"
            details.write_text(details.read_text(encoding="utf-8").replace("Next arrival 18:40.", "Next arrival 19:15."), encoding="utf-8")
            self.assertEqual(2, run("--out", "docs/evidence/stale")[0])   # the edited page no longer matches its manifest hash


if __name__ == "__main__":
    unittest.main()

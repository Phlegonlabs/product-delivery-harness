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
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.parse
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import check_ui_design_contract as checker  # noqa: E402
import hifi_matrix_capture as m  # noqa: E402
from assemble_ui_review import assemble  # noqa: E402
from review_evidence import build_receipt  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures/matrix-hifi"
HAS_PILLOW = importlib.util.find_spec("PIL") is not None
PACKAGE_DIR = "docs/design/ui-references/matrix"
# The navigate interactions the fixture pages really support: one product anchor per surface's ready view.
INTERACTIONS = [
    {"id": "UI-001-to-details", "source": {"surface": "UI-001", "state": "ready"},
     "control": "to-details", "kind": "navigate", "destination": {"surface": "UI-002", "state": "ready"}},
    {"id": "UI-002-to-desk", "source": {"surface": "UI-002", "state": "ready"},
     "control": "to-desk", "kind": "navigate", "destination": {"surface": "UI-001", "state": "ready"}},
]


def build_interactions_package(root, interactions=INTERACTIONS, **kwargs):
    """The fixture with its real product anchors declared as manifest interactions."""
    return build_package(root, manifest_edit=lambda manifest: manifest.update(interactions=interactions), **kwargs)


def size_classes(html):
    """Rename the fixture's 390/1200 targets to the size classes compact/regular, with their width map."""
    return (html.replace('data-hifi-targets="390 1200" data-hifi-target="390"',
                         'data-hifi-targets="compact regular" data-hifi-target="compact" '
                         "data-hifi-target-widths='{\"compact\":390,\"regular\":1200}'")
            .replace('[data-hifi-target="390"]', '[data-hifi-target="compact"]')
            .replace('[data-hifi-target="1200"]', '[data-hifi-target="regular"]'))


def build_package(root, details_extra="", manifest_edit=None, page_edit=None):
    """Assemble the fixture (two surfaces, two targets, three states each) under root.

    page_edit rewrites both fixture pages before the manifest is embedded."""
    page_edit = page_edit or (lambda html: html)
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    if manifest_edit:
        manifest_edit(manifest)
    source = root / "_src"
    source.mkdir(parents=True, exist_ok=True)
    (source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    entry = page_edit((FIXTURE / "index.html").read_text(encoding="utf-8")).replace("__MANIFEST__", json.dumps(manifest))
    (source / "index.html").write_text(entry, encoding="utf-8")
    details = page_edit((FIXTURE / "details.html").read_text(encoding="utf-8")).replace("</main>", details_extra + "</main>", 1)
    (source / "details.html").write_text(details, encoding="utf-8")
    package = root / PACKAGE_DIR
    assemble(source / "manifest.json", [f"index.html={source / 'index.html'}", f"details.html={source / 'details.html'}"],
             package, overwrite=True)
    return package


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def data_svg(color):
    svg = f"<svg xmlns='http://www.w3.org/2000/svg' width='4' height='4'><rect width='4' height='4' fill='{color}'/></svg>"
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe="")


def write_ui_design(root, derived, relative="docs/design/ui-design.md"):
    """A ui-design.md whose Approved target covers the fixture package; `derived` is {surface: {child: parent}}."""
    surfaces = [{"id": "UI-001", "route": "/", "states": ["ready", "loading", "empty"]},
                {"id": "UI-002", "route": "/details", "states": ["ready", "loading", "error"]}]
    for surface in surfaces:
        if surface["id"] in derived:
            surface["derivedStates"] = derived[surface["id"]]
    target = (f"{PACKAGE_DIR}/index.html @ sha256:{'a' * 64}; scope=surfaces={json.dumps(surfaces, separators=(',', ':'))}"
              '|routes=["/","/details"]|states=["empty","error","loading","ready"]'
              '|responsive={"kind":"viewports","targets":[390,1200]}|tolerance="exact"|allowedDeviations=[]|captureMode=hosted-browser')
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# UI Design\n\n## Visual Approval\n\nApproved target: {target}\n", encoding="utf-8")
    return path


def make_dir_link(link, target):
    """A directory symlink, or a junction on Windows without symlink rights. False when neither can be made."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return True
    except (OSError, NotImplementedError):
        if os.name == "nt":
            return subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, check=False).returncode == 0
    return False


class FakeDriver:
    """Same call(op, **fields) surface as NodeDriver, answering from a script."""

    def __init__(self):
        self.environment = {"playwright": "fake", "chromium": "fake", "node": "fake"}
        self.calls, self.restarts, self.axis = [], 0, None
        self.overrides = {}      # (surface, state, target) -> {"geometry", "events", "raise", "style", "inputs", "incomplete"}
        self.interact_scripts = {}   # (id, target, trigger) -> {"problems", "visible", "focusCorrect", "arrivedTo", "raise", "events"}
        self.open_events = {}    # page -> events
        self.open_error = {}     # page -> exception
        self.axis_events = {}    # axis -> events
        self.axis_error = {}     # axis name (or "none") -> exception raised by the axis op
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
        if fields["name"] in self.axis_error:
            raise self.axis_error[fields["name"]]
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
                 "styleSha256": sha("style" + script.get("style", "") + (self.axis or "")),
                 "inputsSha256": sha("inputs" + script.get("inputs", "")), "incomplete": script.get("incomplete", False)}
        return {"result": {"problems": script.get("problems", []), "probe": None if script.get("problems") else probe,
                           "settle": {"waitedMs": 0, "finished": 0, "paused": 0, "capped": False}}, "events": events}

    def _interact(self, fields):
        script = self.interact_scripts.get((fields["id"], fields["target"], fields["trigger"]), {})
        if "raise" in script:
            raise script["raise"]
        events = dict(script.get("events", {}))
        if fields["kind"] == "navigate":
            events.setdefault("navigation", [{"url": "https://hifi.invalid/pkg/" + fields["destinationPage"],
                                              "method": "GET", "resourceType": "document", "allowlisted": True}])
        problems = script.get("problems", [])
        result = {"problems": problems, "visible": script.get("visible", not problems),
                  "focusCorrect": script.get("focusCorrect", None if problems else True),
                  "arrivedTo": script.get("arrivedTo", fields["destinationPage"] if fields["kind"] == "navigate" else None)}
        return {"result": result, "events": events}

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

    def test_axis_sample_never_picks_a_derived_state(self):
        widths = {"390": 390, "1200": 1200}
        rows = [self.surface(states=("ready", "loading", "toast"))]
        counts = {("UI-001", "ready"): 3, ("UI-001", "loading"): 4, ("UI-001", "toast"): 99}
        self.assertEqual({"ready", "toast"}, {c.state for c in m.sample_axis_cases(rows, "index.html", widths, counts)})
        sampled = m.sample_axis_cases(rows, "index.html", widths, counts, derived={"UI-001": ["toast"]})
        self.assertEqual({"ready", "loading"}, {c.state for c in sampled})
        first = m.sample_axis_cases([self.surface(states=("toast", "idle"))], "index.html", widths, {}, derived={"UI-001": ["toast"]})
        self.assertEqual({"idle"}, {c.state for c in first})

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

    def test_render_fingerprint_tracks_geometry_rects_styles_and_image_inputs(self):
        probe = {"geometry": {"a": 1, "b": 2}, "rectsSha256": "r" * 64, "styleSha256": "s" * 64, "inputsSha256": "i" * 64}
        fingerprint = m.render_fingerprint(probe)
        self.assertRegex(fingerprint, r"^[0-9a-f]{64}$")
        self.assertEqual(fingerprint, m.render_fingerprint(dict(probe, geometry={"b": 2, "a": 1})))
        for change in ({"geometry": {"a": 2, "b": 2}}, {"rectsSha256": "x" * 64}, {"styleSha256": "x" * 64},
                       {"inputsSha256": "x" * 64}):
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
        self.assertEqual(["schema", "check", "subject", "matrix", "results", "interactions", "sandbox", "console",
                          "network", "navigation", "popups", "forms", "popupAttempts", "formAttempts", "execution"],
                         list(output))
        self.assertEqual(("ui-output/3", "hifi-browser"), (output["schema"], output["check"]))
        self.assertEqual({"path": f"{PACKAGE_DIR}/index.html", "sha256": hashlib.sha256(
            (cli.package / "index.html").read_bytes()).hexdigest()}, output["subject"])
        self.assertEqual(12, len(output["matrix"]["cases"]))
        self.assertEqual(output["matrix"]["cases"], [{k: r[k] for k in ("surface", "state", "target")} for r in output["results"]])
        self.assertEqual({"PASS"}, {r["result"] for r in output["results"]})
        self.assertEqual(([], []), (output["interactions"], output["navigation"]))
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


    def test_ui_design_names_the_derived_states_and_the_matrix_is_the_one_the_checker_expects(self):
        cli = Cli(self)
        design = write_ui_design(cli.root, {"UI-001": {"empty": "ready"}})
        code, _, out = cli.run(FakeDriver(), "--derived-once", "--ui-design", str(design))
        output, sidecar = cli.load(out)
        scope = checker.parse_ui_contract_view(design.read_text(encoding="utf-8"))[0]["target_scope"]
        self.assertEqual(0, code)
        self.assertEqual(checker._evidence_matrix(scope)["cases"], output["matrix"]["cases"])
        self.assertEqual(11, len(output["matrix"]["cases"]))
        self.assertEqual(({"UI-001": ["empty"]}, "--ui-design"), (sidecar["run"]["derived"], sidecar["run"]["derivedFrom"]))

    def test_derived_json_replaces_the_ui_design_set(self):
        cli = Cli(self)
        design = write_ui_design(cli.root, {"UI-001": {"empty": "ready"}})
        override = cli.root / "derived.json"
        override.write_text(json.dumps({"UI-002": ["error"]}), encoding="utf-8")
        code, _, out = cli.run(FakeDriver(), "--derived-once", "--ui-design", str(design), "--derived", str(override))
        output, sidecar = cli.load(out)
        targets = {(c["surface"], c["state"]): [] for c in output["matrix"]["cases"]}
        for c in output["matrix"]["cases"]:
            targets[(c["surface"], c["state"])].append(c["target"])
        self.assertEqual(0, code)
        self.assertEqual((["390", "1200"], ["390"]), (targets[("UI-001", "empty")], targets[("UI-002", "error")]))
        self.assertEqual(("--derived", {"UI-002": ["error"]}), (sidecar["run"]["derivedFrom"], sidecar["run"]["derived"]))

    def test_a_derived_state_takes_no_stress_axis_even_when_it_is_the_densest(self):
        cli, driver = Cli(self), FakeDriver()
        driver.overrides[("UI-001", "empty", "390")] = {"geometry": {"elementCount": 99}}
        design = write_ui_design(cli.root, {"UI-001": {"empty": "ready"}})
        _, _, plain = cli.run(driver, "--axes", "dark")
        self.assertIn("empty", {r["state"] for r in cli.load(plain)[1]["axes"] if r["surface"] == "UI-001"})
        driver = FakeDriver()
        driver.overrides[("UI-001", "empty", "390")] = {"geometry": {"elementCount": 99}}
        _, _, out = cli.run(driver, "--axes", "dark", "--derived-once", "--ui-design", str(design))
        axis_states = {r["state"] for r in cli.load(out)[1]["axes"] if r["surface"] == "UI-001"}
        self.assertEqual({"ready", "loading"}, axis_states)


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

    def test_a_changed_image_input_is_not_carried(self):
        cli = Cli(self)
        first = self.first_run(cli)
        driver = FakeDriver()
        driver.overrides[("UI-002", "ready", "1200")] = {"inputs": "img src changed"}
        _, summary, out = cli.run(driver, "--carry-from", str(first / m.OUTPUT_NAME))
        _, sidecar = cli.load(out)
        changed = [r for r in sidecar["cases"] if r["carriedFrom"] is None]
        self.assertEqual((11, 1), (summary["carried"], len(changed)))
        self.assertEqual(("UI-002", "ready", "1200"), (changed[0]["surface"], changed[0]["state"], changed[0]["target"]))
        self.assertEqual(1, driver.count("shot"))

    def test_an_incomplete_fingerprint_is_marked_and_never_carried(self):
        cli = Cli(self)
        capped = ("UI-001", "empty", "390")
        driver = FakeDriver()
        driver.overrides[capped] = {"incomplete": True}
        _, _, first = cli.run(driver)
        _, previous = cli.load(first)
        self.assertEqual([capped], [(r["surface"], r["state"], r["target"]) for r in previous["cases"]
                                    if r["fingerprintIncomplete"]])
        # still incomplete on the rerun: same fingerprint, but a fresh screenshot is taken and judged
        again = FakeDriver()
        again.overrides[capped] = {"incomplete": True}
        _, summary, out = cli.run(again, "--carry-from", str(first / m.OUTPUT_NAME))
        _, sidecar = cli.load(out)
        self.assertEqual((11, 1), (summary["carried"], again.count("shot")))
        self.assertIsNone(next(r for r in sidecar["cases"] if (r["surface"], r["state"], r["target"]) == capped)["carriedFrom"])
        # complete now, but the earlier observation was capped: still not carried
        _, summary, _ = cli.run(FakeDriver(), "--carry-from", str(first / m.OUTPUT_NAME))
        self.assertEqual(11, summary["carried"])

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

    def test_overwrite_never_writes_over_around_or_inside_the_carry_source(self):
        cli = Cli(self)
        first = self.first_run(cli)                       # docs/evidence/run1
        _, _, second = cli.run(FakeDriver(), "--carry-from", str(first / m.OUTPUT_NAME))   # carries run1's captures
        source = (first / m.OUTPUT_NAME).read_bytes()
        for label, out, carry in (("equal", "docs/evidence/run1", first), ("inside", "docs/evidence/run1/sub", first),
                                  ("holding", "docs/evidence", first),
                                  ("a carried capture's folder", "docs/evidence/run1", second)):
            driver = FakeDriver()
            code, summary, _ = cli.run(driver, "--carry-from", str(carry / m.OUTPUT_NAME), "--overwrite", out=out)
            self.assertEqual(2, code, label)
            self.assertIn("--carry-from", summary["error"], label)
            self.assertEqual([], driver.calls, label)
            self.assertEqual(source, (first / m.OUTPUT_NAME).read_bytes(), label)
        self.assertFalse((first / "sub").exists())
        code, _, _ = cli.run(FakeDriver(), "--carry-from", str(first / m.OUTPUT_NAME), "--overwrite", out="docs/evidence/elsewhere")
        self.assertEqual(0, code)

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


@unittest.skipUnless(HAS_PILLOW, "Pillow is not installed")
class PixelDiffTests(unittest.TestCase):
    def png(self, directory, name, pixel, mode="RGB"):
        from PIL import Image
        path = Path(directory) / name
        image = Image.new(mode, (6, 4), (10, 20, 30) if mode == "RGB" else (10, 20, 30, 255))
        image.putpixel((2, 1), pixel)
        image.save(path)
        return path

    def test_any_single_channel_step_counts_as_a_change(self):
        with tempfile.TemporaryDirectory() as directory:
            base = self.png(directory, "base.png", (10, 20, 30))
            for label, pixel in (("red", (11, 20, 30)), ("green", (10, 21, 30)), ("blue", (10, 20, 31))):
                diff = m.pixel_diff(base, self.png(directory, label + ".png", pixel))
                self.assertEqual(("changed", round(1 / 24, 6)), (diff["status"], diff["ratio"]), label)
            self.assertEqual(("identical", 0.0), tuple(m.pixel_diff(base, self.png(directory, "same.png", (10, 20, 30)))[k]
                                                       for k in ("status", "ratio")))

    def test_an_alpha_only_change_counts_and_modes_may_differ(self):
        with tempfile.TemporaryDirectory() as directory:
            base = self.png(directory, "base.png", (10, 20, 30, 255), mode="RGBA")
            self.assertEqual("changed", m.pixel_diff(base, self.png(directory, "alpha.png", (10, 20, 30, 254), mode="RGBA"))["status"])
            self.assertEqual("identical", m.pixel_diff(base, self.png(directory, "rgb.png", (10, 20, 30), mode="RGB"))["status"])

    def test_a_different_size_is_a_full_change(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as directory:
            base = self.png(directory, "base.png", (10, 20, 30))
            Image.new("RGB", (7, 4)).save(Path(directory) / "wide.png")
            self.assertEqual(("changed", 1.0), tuple(m.pixel_diff(base, Path(directory) / "wide.png")[k] for k in ("status", "ratio")))


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

    def axis_rows(self, driver, *extra):
        cli = Cli(self)
        code, summary, out = cli.run(driver, *extra)
        output, sidecar = cli.load(out)
        return code, summary, output, sidecar["axes"]

    def test_an_axis_that_cannot_be_set_up_gives_blocked_rows_and_a_failing_exit(self):
        driver = FakeDriver()
        driver.axis_error["forced-colors"] = m.DriverError("page.emulateMedia: forced colors are not supported")
        code, summary, output, axes = self.axis_rows(driver, "--axes", "dark,forced-colors")
        forced = [r for r in axes if r["axis"] == "forced-colors"]
        self.assertEqual(1, code)
        self.assertEqual((16, 8), (summary["axisCases"], summary["axisFail"]))
        self.assertEqual({"PASS"}, {r["result"] for r in axes if r["axis"] == "dark"})
        self.assertEqual(8, len(forced))
        self.assertEqual({"BLOCKED"}, {r["result"] for r in forced})
        self.assertTrue(all("forced-colors could not be set up" in r["reasons"][0] and "not supported" in r["reasons"][0]
                            and r["capture"] is None for r in forced))
        self.assertEqual({"PASS"}, {r["result"] for r in output["results"]})
        # the next axis and page still start from the base state
        self.assertEqual(["dark", "none", "forced-colors", "none"] * 2, [f["name"] for op, f in driver.calls if op == "axis"])

    def test_an_axis_that_cannot_be_reset_restarts_the_browser_and_still_reports_every_row(self):
        driver = FakeDriver()
        driver.axis_error["none"] = m.DriverError("page.emulateMedia: target closed")
        code, summary, _, axes = self.axis_rows(driver, "--axes", "dark,reduced-motion,zoom-200")
        self.assertEqual(1, code)
        self.assertEqual(2 * 3 * 4, len(axes))          # pages x axes x sampled cases: nothing is dropped
        self.assertGreaterEqual(summary["restarts"], 1)
        blocked = [r for r in axes if r["result"] == "BLOCKED"]
        self.assertTrue(blocked)
        self.assertTrue(all("restart limit" in r["reasons"][0] for r in blocked))

    def test_axes_on_a_page_that_did_not_open_are_blocked_not_omitted(self):
        driver = FakeDriver()
        driver.open_error["details.html"] = m.DriverError("page did not load: details.html")
        code, summary, _, axes = self.axis_rows(driver, "--axes", "dark")
        ui2 = [r for r in axes if r["surface"] == "UI-002"]
        self.assertEqual(1, code)
        self.assertEqual((6, 2), (summary["axisCases"], summary["axisFail"]))   # ready at two targets for UI-002: no base geometry
        self.assertEqual(2, len(ui2))
        self.assertEqual({"BLOCKED"}, {r["result"] for r in ui2})
        self.assertIn("page did not open", ui2[0]["reasons"][0])

    def test_axes_after_an_aborted_run_are_blocked_not_omitted(self):
        driver = FakeDriver()
        for state in ("ready", "loading", "empty"):
            for target in ("390", "1200"):
                driver.overrides[("UI-001", state, target)] = {"raise": m.DriverTimeout("no reply")}
        code, summary, _, axes = self.axis_rows(driver, "--axes", "dark")
        self.assertEqual(1, code)
        self.assertEqual((4, 4), (summary["axisCases"], summary["axisFail"]))
        self.assertTrue(all(r["result"] == "BLOCKED" and "restart limit" in r["reasons"][0] for r in axes))

    def test_the_four_axes_are_supported_and_others_refused(self):
        self.assertEqual(("dark", "reduced-motion", "forced-colors", "zoom-200"), m.AXES)
        code, summary, _ = Cli(self).run(FakeDriver(), "--axes", "sepia")
        self.assertEqual(2, code)
        self.assertIn("sepia", summary["error"])


class InteractionTests(unittest.TestCase):
    def package(self, interactions, surfaces=None):
        rows = surfaces or [
            {"id": "UI-001", "page": "index.html", "states": ["ready", "loading"], "responsive": {"targets": [390, 1200]}},
            {"id": "UI-002", "page": "details.html", "states": ["ready", "error"], "responsive": {"targets": [390, 1200]}}]
        return m.Package({"surfaces": rows, "interactions": interactions}, {}, {}, {}, {})

    def cli(self):
        cli = Cli(self)
        cli.package = build_interactions_package(cli.root)
        return cli

    def test_the_plan_follows_manifest_order_and_the_source_targets(self):
        actions = [dict(INTERACTIONS[0]), {"id": "UI-001-show", "source": {"surface": "UI-001", "state": "ready"},
                                           "control": "show", "kind": "state",
                                           "destination": {"surface": "UI-001", "state": "loading"}}]
        plan = m.interaction_plan(self.package(actions))
        self.assertEqual(["UI-001-to-details", "UI-001-show"], [a["id"] for a in plan])
        self.assertEqual(("index.html", "details.html"), (plan[0]["page"], plan[0]["destinationPage"]))
        self.assertEqual(["390", "1200"], plan[0]["targets"])
        self.assertEqual({"surface": "UI-001", "state": "ready"}, plan[0]["source"])

    def test_only_keeps_the_selected_surfaces_interactions(self):
        self.assertEqual(["UI-002-to-desk"], [a["id"] for a in m.interaction_plan(self.package(INTERACTIONS), only={"UI-002"})])

    def test_a_malformed_manifest_refuses_before_any_browser_work(self):
        good = dict(INTERACTIONS[0])
        cases = [
            (None, "interactions list"),
            ([dict(good, id="")], "needs id, source, control, kind and destination"),
            ([dict(good, control=" ")], "needs id, source, control, kind and destination"),
            ([{"source": good["source"], "control": "c", "kind": "navigate", "destination": good["destination"]}],
             "needs id, source, control, kind and destination"),
            ([dict(good, kind="hover")], "unknown kind"),
            ([dict(good, source={"surface": "UI-009", "state": "ready"})], "unknown source surface state"),
            ([dict(good, destination={"surface": "UI-002", "state": "nope"})], "unknown destination surface state"),
            ([good, dict(good, control="other")], "duplicate interaction id"),
        ]
        driver = FakeDriver()
        for interactions, message in cases:
            with self.subTest(message=message):
                cli = Cli(self)
                cli.package = build_interactions_package(cli.root, interactions=interactions)
                code, summary, _ = cli.run(driver)
                self.assertEqual(2, code, message)
                self.assertIn(message, summary["error"], message)
        self.assertEqual([], driver.calls)

    def test_the_default_run_writes_the_rows_the_checker_expects(self):
        cli, driver = self.cli(), FakeDriver()
        code, summary, out = cli.run(driver)
        output, sidecar = cli.load(out)
        manifest = json.loads(m.HIFI_MANIFEST_RE.search((cli.package / "index.html").read_text(encoding="utf-8")).group("data"))
        expected, navigation = checker._interaction_expectations(manifest)
        self.assertEqual(0, code, summary)
        self.assertEqual((expected, navigation), (output["interactions"], output["navigation"]))
        self.assertEqual((8, 0), (summary["interactions"], summary["interactionsFail"]))
        self.assertEqual([("UI-001-to-details", "390", "click"), ("UI-001-to-details", "390", "keyboard"),
                          ("UI-001-to-details", "1200", "click"), ("UI-001-to-details", "1200", "keyboard"),
                          ("UI-002-to-desk", "390", "click"), ("UI-002-to-desk", "390", "keyboard"),
                          ("UI-002-to-desk", "1200", "click"), ("UI-002-to-desk", "1200", "keyboard")],
                         [(f["id"], f["target"], f["trigger"]) for op, f in driver.calls if op == "interact"])
        first = next(f for op, f in driver.calls if op == "interact")
        self.assertEqual(("UI-001", "ready", "to-details", "navigate", "UI-002", "details.html", "click"),
                         (first["surface"], first["state"], first["control"], first["kind"],
                          first["destination"]["surface"], first["destinationPage"], first["trigger"]))
        self.assertEqual(8, len(sidecar["interactions"]))
        self.assertEqual({"PASS"}, {r["result"] for r in sidecar["interactions"]})
        self.assertEqual({"details.html", "index.html"}, {r["arrived"] for r in sidecar["interactions"]})
        self.assertTrue(all(isinstance(r["durationMs"], int) and r["startedAt"] <= r["finishedAt"]
                            for r in sidecar["interactions"]))
        self.assertEqual("PASS", build_receipt(cli.root, f"docs/evidence/run1/{m.OUTPUT_NAME}")["result"])

    def test_a_failed_attempt_is_recorded_and_fails_the_run(self):
        cli, driver = self.cli(), FakeDriver()
        driver.interact_scripts[("UI-001-to-details", "390", "click")] = {
            "visible": False, "problems": ["product control is missing or not unique: to-details"]}
        code, summary, out = cli.run(driver)
        output, sidecar = cli.load(out)
        failed = next(r for r in output["interactions"] if r["result"] != "PASS")
        self.assertEqual(1, code)
        self.assertEqual(("FAIL", False, None), (failed["result"], failed["visible"], failed["focusCorrect"]))
        self.assertIn("not unique", sidecar["interactions"][0]["reasons"][0])
        self.assertEqual((8, 1), (summary["interactions"], summary["interactionsFail"]))

    def test_an_undeclared_navigation_during_an_interaction_stays_raw_and_fails(self):
        cli, driver = self.cli(), FakeDriver()
        row = {"url": "https://hifi.invalid/pkg/missing.html", "method": "GET", "resourceType": "document", "allowlisted": True}
        driver.interact_scripts[("UI-002-to-desk", "1200", "keyboard")] = {"events": {"navigation": [row]}}
        code, _, out = cli.run(driver)
        output, sidecar = cli.load(out)
        self.assertEqual(1, code)
        self.assertIn(dict(row, page="details.html"), output["navigation"])
        self.assertEqual(7, len([r for r in output["navigation"] if set(r) == {"id", "target", "trigger", "from", "to"}]))
        record = next(r for r in sidecar["interactions"] if (r["id"], r["target"], r["trigger"])
                      == ("UI-002-to-desk", "1200", "keyboard"))
        self.assertEqual("FAIL", record["result"])
        self.assertIn("the destination page did not load", record["reasons"])
        self.assertIn("navigation attempt", " | ".join(record["reasons"]))

    def test_interactions_on_a_page_that_did_not_open_are_blocked_not_omitted(self):
        cli, driver = self.cli(), FakeDriver()
        driver.open_error["details.html"] = m.DriverError("page did not load: details.html")
        code, summary, out = cli.run(driver)
        output, sidecar = cli.load(out)
        blocked = [r for r in sidecar["interactions"] if r["surface"] == "UI-002"]
        self.assertEqual(1, code)
        self.assertEqual(4, len(blocked))
        self.assertEqual({"BLOCKED"}, {r["result"] for r in blocked})
        self.assertIn("page did not open", blocked[0]["reasons"][0])
        self.assertEqual({"UI-001-to-details"}, {f["id"] for op, f in driver.calls if op == "interact"})

    def test_only_narrows_the_interaction_pass(self):
        cli, driver = self.cli(), FakeDriver()
        code, summary, out = cli.run(driver, "--only", "UI-001")
        output, _ = cli.load(out)
        self.assertEqual((0, 4), (code, summary["interactions"]))
        self.assertEqual({"UI-001-to-details"}, {r["id"] for r in output["interactions"]})

    def test_an_interaction_timeout_fails_the_attempt_and_restarts(self):
        cli, driver = self.cli(), FakeDriver()
        driver.interact_scripts[("UI-001-to-details", "390", "keyboard")] = {"raise": m.DriverTimeout("no reply")}
        code, summary, out = cli.run(driver)
        _, sidecar = cli.load(out)
        record = next(r for r in sidecar["interactions"]
                      if (r["id"], r["target"], r["trigger"]) == ("UI-001-to-details", "390", "keyboard"))
        self.assertEqual((1, 1), (code, summary["restarts"]))
        self.assertEqual("FAIL", record["result"])
        self.assertIn("timed out", record["reasons"][0])
        self.assertIn("index.html", [f["page"] for op, f in driver.calls if op == "open"])   # the browser reopened it

    def test_carry_never_skips_the_interaction_pass(self):
        cli = self.cli()
        _, _, first = cli.run(FakeDriver())
        driver = FakeDriver()
        _, summary, _ = cli.run(driver, "--carry-from", str(first / m.OUTPUT_NAME))
        self.assertEqual((12, 8, 8), (summary["carried"], summary["interactions"], driver.count("interact")))


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

    def test_an_allowlisted_navigation_stays_in_the_transcript_and_fails_the_case(self):
        row = {"url": "https://hifi.invalid/pkg/index.html", "method": "GET", "resourceType": "document", "allowlisted": True}
        driver = FakeDriver()
        driver.overrides[("UI-002", "ready", "390")] = {"events": {"navigation": [row]}}
        code, _, output, cases = self.results(driver)
        self.assertEqual(1, code)
        self.assertEqual([dict(row, page="details.html")], output["navigation"])
        self.assertEqual(["navigation attempt: https://hifi.invalid/pkg/index.html"], cases[("UI-002", "ready", "390")]["reasons"])

    def test_page_load_errors_fail_every_case_on_that_page(self):
        driver = FakeDriver()
        driver.open_events["details.html"] = {"console": [{"source": "javascript", "level": "exception", "message": "Uncaught"}]}
        _, _, _, cases = self.results(driver)
        self.assertEqual({"FAIL"}, {r["result"] for k, r in cases.items() if k[0] == "UI-002"})
        self.assertEqual({"PASS"}, {r["result"] for k, r in cases.items() if k[0] == "UI-001"})
        self.assertTrue(cases[("UI-002", "ready", "390")]["reasons"][0].startswith("page load:"))

    def test_a_viewport_case_at_the_wrong_canvas_width_fails_with_the_measured_width(self):
        driver = FakeDriver()
        driver.overrides[("UI-001", "ready", "1200")] = {"geometry": {"canvasWidth": 1100.0}}
        driver.overrides[("UI-001", "ready", "390")] = {"geometry": {"canvasWidth": 391.0}}       # 1 px rounding is allowed
        driver.overrides[("UI-001", "loading", "390")] = {"geometry": {"canvasWidth": 391.5}}
        code, _, _, cases = self.results(driver)
        self.assertEqual(1, code)
        self.assertEqual("PASS", cases[("UI-001", "ready", "390")]["result"])
        wide = cases[("UI-001", "ready", "1200")]
        self.assertEqual("FAIL", wide["result"])
        self.assertIn("1100.0px wide", wide["reasons"][0])
        self.assertIn("declared 1200px", wide["reasons"][0])
        self.assertEqual("FAIL", cases[("UI-001", "loading", "390")]["result"])

    def test_the_canvas_width_of_a_size_class_is_recorded_not_judged(self):
        cli = Cli(self)
        shutil.rmtree(cli.root / "docs")
        cli.package = build_package(cli.root, page_edit=size_classes, manifest_edit=lambda manifest: [
            row["responsive"].update(kind="sizeClasses", targets=["compact", "regular"]) for row in manifest["surfaces"]])
        driver = FakeDriver()
        driver.overrides[("UI-001", "ready", "compact")] = {"geometry": {"canvasWidth": 377.5}}
        code, _, out = cli.run(driver)
        _, sidecar = cli.load(out)
        cases = {(r["surface"], r["state"], r["target"]): r for r in sidecar["cases"]}
        self.assertEqual(0, code)
        self.assertEqual(12, len(cases))
        self.assertEqual({"PASS"}, {r["result"] for r in cases.values()})
        self.assertEqual(377.5, cases[("UI-001", "ready", "compact")]["geometry"]["canvasWidth"])

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
        design = write_ui_design(cli.root, {"UI-001": {"empty": "ready"}})
        no_target = cli.root / "plain.md"
        no_target.write_text("# UI Design\n\nNothing approved yet.\n", encoding="utf-8")
        cases = [
            (("--only", "UI-999"), "unknown surfaces"),
            (("--derived-once",), "--ui-design"),
            (("--derived-once",), "--derived"),
            (("--derived", str(derived)), "--derived-once"),
            (("--ui-design", str(design)), "--derived-once"),
            (("--derived-once", "--ui-design", str(cli.root / "missing.md")), "cannot read --ui-design"),
            (("--derived-once", "--ui-design", str(no_target)), "no readable Approved target scope"),
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

    def set_first_page(self, cli, **fields):
        entry = cli.package / "index.html"
        html = entry.read_text(encoding="utf-8")
        match = m.HIFI_MANIFEST_RE.search(html)
        manifest = json.loads(match.group("data"))
        manifest["pages"][0] = fields
        entry.write_text(html[:match.start("data")] + json.dumps(manifest) + html[match.end("data"):], encoding="utf-8")

    def test_manifest_paths_that_leave_the_package_are_refused_before_any_read(self):
        cli = Cli(self)
        (cli.package.parent / "outside.html").write_text("<html></html>", encoding="utf-8")
        original, reads = Path.read_bytes, []

        def spy(path):
            reads.append(path.name)
            return original(path)

        for bad in ("../outside.html", "a/../details.html", "./details.html", "/outside.html", "C:/outside.html",
                    "sub\\details.html", 5):
            self.set_first_page(cli, path=bad, sha256="0" * 64)
            with mock.patch.object(Path, "read_bytes", spy):
                code, summary, _ = cli.run(FakeDriver())
            self.assertEqual(2, code, bad)
            self.assertIn("unsafe package path", summary["error"], bad)
        self.assertNotIn("outside.html", reads)
        self.set_first_page(cli, sha256="0" * 64)
        code, summary, _ = cli.run(FakeDriver())
        self.assertEqual(2, code)
        self.assertIn("path and a sha256", summary["error"])

    def test_a_manifest_page_behind_a_link_is_refused(self):
        cli = Cli(self)
        elsewhere = cli.root / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "page.html").write_text("<html></html>", encoding="utf-8")
        if not make_dir_link(cli.package / "linked", elsewhere):
            self.skipTest("neither symlinks nor junctions can be created here")
        self.set_first_page(cli, path="linked/page.html", sha256="0" * 64)
        code, summary, _ = cli.run(FakeDriver())
        self.assertEqual(2, code)
        self.assertIn("unsafe package path", summary["error"])
        self.assertIn("links", summary["error"])

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

    def run_main(self, module, root, package, *extra):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), mock.patch.dict(os.environ, {"PLAYWRIGHT_MODULE": module}):
            code = m.main(["--repo-root", str(root), "--package", str(package), *extra])
        return code, buffer.getvalue()

    def test_matrix_capture_in_real_chromium(self):
        module = self.playwright()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = build_package(root)

            def run(*extra):
                return self.run_main(module, root, package, *extra)

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

    def test_a_page_that_renders_the_wrong_width_fails_in_real_chromium(self):
        module = self.playwright()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = build_package(root, page_edit=lambda html: html.replace(
                '[data-hifi-target="1200"]{width:1200px}', '[data-hifi-target="1200"]{width:1000px}'))
            code, text = self.run_main(module, root, package, "--out", "docs/evidence/width", "--only", "UI-001")
            sidecar = json.loads((root / "docs/evidence/width" / m.SIDECAR_NAME).read_text(encoding="utf-8"))
            cases = {(r["surface"], r["state"], r["target"]): r for r in sidecar["cases"]}
            self.assertEqual(1, code, text)
            self.assertEqual({"PASS"}, {r["result"] for k, r in cases.items() if k[2] == "390"})
            wide = [r for k, r in cases.items() if k[2] == "1200"]
            self.assertEqual({"FAIL"}, {r["result"] for r in wide})
            self.assertTrue(all(1000 == r["geometry"]["canvasWidth"] and "1000" in r["reasons"][0] for r in wide))

    def test_the_drivers_own_open_is_not_a_navigation_but_a_later_allowlisted_one_is(self):
        module = self.playwright()
        leave = "<script>setTimeout(() => { location.href = 'index.html'; }, 300);</script>"
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as scratch:
            package = build_package(Path(temporary), details_extra=leave)
            driver = m.NodeDriver(shutil.which("node"), module, m.read_package(package).files, scratch)
            driver.start()
            try:
                opened = driver.call("open", page="details.html", timeoutMs=30000)
                self.assertEqual([], opened["events"]["navigation"])
                time.sleep(1.5)                      # the page leaves for an allowlisted page after 300 ms
                later = driver.call("axis", name="none")
                self.assertEqual([{"url": "https://hifi.invalid/pkg/index.html", "method": "GET", "resourceType": "document",
                                   "allowlisted": True}], later["events"]["navigation"])
                reopened = driver.call("open", page="index.html", timeoutMs=30000)
                self.assertEqual([], reopened["events"]["navigation"])
            finally:
                driver.stop()

    def test_a_canvas_paint_change_changes_the_fingerprint_and_is_not_carried(self):
        module = self.playwright()
        red = lambda text: text.replace("[data-hifi-canvas]{container-type:inline-size;background:var(--paper)}",
                                        "[data-hifi-canvas]{container-type:inline-size;background:#ff0000}", 1)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = build_package(root)
            code, text = self.run_main(module, root, package, "--out", "docs/evidence/a", "--only", "UI-002")
            self.assertEqual(0, code, text)
            before = json.loads((root / "docs/evidence/a" / m.SIDECAR_NAME).read_text(encoding="utf-8"))
            package = build_package(root, page_edit=red)
            code, text = self.run_main(module, root, package, "--out", "docs/evidence/b", "--only", "UI-002",
                                       "--carry-from", "docs/evidence/a/" + m.OUTPUT_NAME)
            self.assertEqual(0, code, text)
            after = json.loads((root / "docs/evidence/b" / m.SIDECAR_NAME).read_text(encoding="utf-8"))
            key = lambda r: (r["surface"], r["state"], r["target"])
            first = {key(r): r for r in before["cases"]}
            for row in after["cases"]:
                self.assertNotEqual(first[key(row)]["renderFingerprint"], row["renderFingerprint"], key(row))
                self.assertIsNone(row["carriedFrom"], key(row))

    def test_interactions_in_real_chromium(self):
        module = self.playwright()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = build_interactions_package(root)
            code, text = self.run_main(module, root, package, "--out", "docs/evidence/interactions")
            self.assertEqual(0, code, text)
            output = json.loads((root / "docs/evidence/interactions" / m.OUTPUT_NAME).read_text(encoding="utf-8"))
            sidecar = json.loads((root / "docs/evidence/interactions" / m.SIDECAR_NAME).read_text(encoding="utf-8"))
            manifest = json.loads(m.HIFI_MANIFEST_RE.search((package / "index.html").read_text(encoding="utf-8")).group("data"))
            expected, navigation = checker._interaction_expectations(manifest)
            self.assertEqual(expected, output["interactions"])
            self.assertEqual(navigation, output["navigation"])
            self.assertEqual([], checker._bundle_transcript_findings(output, manifest))
            self.assertEqual("PASS", build_receipt(root, "docs/evidence/interactions/" + m.OUTPUT_NAME)["result"])
            self.assertEqual(8, len(sidecar["interactions"]))
            self.assertTrue(all(r["result"] == "PASS" and r["visible"] and r["focusCorrect"] and r["arrived"]
                                for r in sidecar["interactions"]), sidecar["interactions"])
            arrivals = {(r["id"], r["target"], r["trigger"]): r["arrived"] for r in sidecar["interactions"]}
            self.assertEqual("details.html", arrivals[("UI-001-to-details", "1200", "keyboard")])
            self.assertEqual("index.html", arrivals[("UI-002-to-desk", "390", "click")])
            for row in output["console"]:
                self.assertEqual("Unrecognized Content-Security-Policy directive 'navigate-to'.", row["message"])
            self.assertEqual([], output["network"] + output["popups"] + output["forms"])

    def test_a_state_interaction_in_real_chromium(self):
        module = self.playwright()
        button = ('<button type="button" class="card" data-control-id="report">Report an issue</button>'
                  '<script>(function () {'
                  'document.querySelector("[data-control-id=report]").addEventListener("click", function () {'
                  'document.__hifiReviewerRuntime.selectState("error");'
                  '});})();</script>')
        actions = INTERACTIONS + [{"id": "UI-002-report", "source": {"surface": "UI-002", "state": "ready"},
                                   "control": "report", "kind": "state",
                                   "destination": {"surface": "UI-002", "state": "error"}}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = build_package(root, details_extra=button,
                                    manifest_edit=lambda manifest: manifest.update(interactions=actions))
            code, text = self.run_main(module, root, package, "--out", "docs/evidence/state")
            self.assertEqual(0, code, text)
            output = json.loads((root / "docs/evidence/state" / m.OUTPUT_NAME).read_text(encoding="utf-8"))
            sidecar = json.loads((root / "docs/evidence/state" / m.SIDECAR_NAME).read_text(encoding="utf-8"))
            manifest = json.loads(m.HIFI_MANIFEST_RE.search((package / "index.html").read_text(encoding="utf-8")).group("data"))
            expected, navigation = checker._interaction_expectations(manifest)
            self.assertEqual(expected, output["interactions"])
            self.assertEqual(navigation, output["navigation"])
            self.assertEqual([], checker._bundle_transcript_findings(output, manifest))
            self.assertEqual(12, len(sidecar["interactions"]))
            self.assertEqual({"PASS"}, {r["result"] for r in sidecar["interactions"]})
            self.assertTrue(all(r["focusCorrect"] for r in sidecar["interactions"]), sidecar["interactions"])

    def test_a_missing_product_control_fails_in_real_chromium(self):
        module = self.playwright()
        actions = [{"id": "UI-001-ghost", "source": {"surface": "UI-001", "state": "ready"},
                    "control": "ghost", "kind": "state", "destination": {"surface": "UI-001", "state": "loading"}}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = build_package(root, manifest_edit=lambda manifest: manifest.update(interactions=actions))
            code, text = self.run_main(module, root, package, "--out", "docs/evidence/ghost")
            self.assertEqual(1, code, text)
            sidecar = json.loads((root / "docs/evidence/ghost" / m.SIDECAR_NAME).read_text(encoding="utf-8"))
            self.assertEqual(4, len(sidecar["interactions"]))
            self.assertEqual({"FAIL"}, {r["result"] for r in sidecar["interactions"]})
            self.assertIn("missing or not unique", sidecar["interactions"][0]["reasons"][0])

    def test_every_image_input_changes_the_fingerprint_and_a_capped_probe_is_incomplete(self):
        module = self.playwright()
        red, blue = data_svg("red"), data_svg("blue")
        box = "width:40px;height:40px"
        pairs = {
            "same": ("<p>x</p>", "<p>x</p>"),
            "img-src": (f'<img width="40" height="40" src="{red}">', f'<img width="40" height="40" src="{blue}">'),
            "img-srcset": (f'<img width="40" height="40" src="{red}" srcset="{red} 1x">',
                           f'<img width="40" height="40" src="{red}" srcset="{blue} 1x">'),
            "picture-source": (f'<picture><source srcset="{red}"><img width="40" height="40" src="{red}"></picture>',
                               f'<picture><source srcset="{blue}"><img width="40" height="40" src="{red}"></picture>'),
            "video-poster": (f'<video width="40" height="40" poster="{red}"></video>',
                             f'<video width="40" height="40" poster="{blue}"></video>'),
            "svg-fill": ('<svg width="40" height="40"><rect width="40" height="40" fill="red"/></svg>',
                         '<svg width="40" height="40"><rect width="40" height="40" fill="blue"/></svg>'),
            "svg-stroke-width": ('<svg width="40" height="40"><rect width="40" height="40" fill="none" stroke="red" stroke-width="2"/></svg>',
                                 '<svg width="40" height="40"><rect width="40" height="40" fill="none" stroke="red" stroke-width="4"/></svg>'),
            "use-href": ('<svg width="40" height="40"><use href="#sym-a"/></svg>', '<svg width="40" height="40"><use href="#sym-b"/></svg>'),
            "background-image": (f'<div style="{box};background-image:url({red})"></div>',
                                 f'<div style="{box};background-image:url({blue})"></div>'),
            "mask-image": (f'<div style="{box};background:#000;mask-image:url({red})"></div>',
                           f'<div style="{box};background:#000;mask-image:url({blue})"></div>'),
            "border-image": (f'<div style="{box};border:4px solid;border-image:url({red}) 1 / 4px"></div>',
                             f'<div style="{box};border:4px solid;border-image:url({blue}) 1 / 4px"></div>'),
        }
        names = [f"{kind}-{side}" for kind in pairs for side in "ab"] + ["capped"]
        views = "".join(f'<section class="card" data-hifi-state-view="{kind}-{side}" hidden>{html}</section>'
                        for kind, (a, b) in pairs.items() for side, html in (("a", a), ("b", b)))
        views += ('<svg width="0" height="0" style="position:absolute"><symbol id="sym-a"><rect width="9" height="9" fill="red"/></symbol>'
                  '<symbol id="sym-b"><circle r="4" fill="red"/></symbol></svg>')
        views += '<section class="card" data-hifi-state-view="capped" hidden>' + '<b style="display:inline-block;width:2px;height:2px"></b>' * 450 + "</section>"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = build_package(root, details_extra=views, manifest_edit=lambda manifest: manifest["surfaces"][1].update(
                states=["ready", *names]))
            code, text = self.run_main(module, root, package, "--out", "docs/evidence/inputs", "--only", "UI-002")
            sidecar = json.loads((root / "docs/evidence/inputs" / m.SIDECAR_NAME).read_text(encoding="utf-8"))
            cases = {(r["surface"], r["state"], r["target"]): r for r in sidecar["cases"]}
            failed = {key: r["reasons"] for key, r in cases.items() if r["result"] != "PASS"}
            self.assertEqual({}, failed, text)
            for target in ("390", "1200"):
                fingerprint = lambda state: cases[("UI-002", state, target)]["renderFingerprint"]
                self.assertEqual(fingerprint("same-a"), fingerprint("same-b"))
                for kind in pairs:
                    if kind != "same":
                        self.assertNotEqual(fingerprint(f"{kind}-a"), fingerprint(f"{kind}-b"), f"{kind} at {target}")
                self.assertEqual(["capped"], [s for s in names if cases[("UI-002", s, target)]["fingerprintIncomplete"]])


if __name__ == "__main__":
    unittest.main()

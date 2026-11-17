"""hifi_matrix_capture --workers: the split is static, the merged output matches the serial run, every driver stops.

Fake drivers for the logic, real Chromium for the output. Synthetic fixture pages only.
"""

from __future__ import annotations

import _thread
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_hifi_matrix_capture as base  # noqa: E402

m = base.m
SEQUENCE_KEYS = ("page", "surface", "state", "target", "name", "interaction", "trigger")


class TrackedDriver(base.FakeDriver):
    def __init__(self):
        super().__init__()
        self.starts = self.stops = 0
        self.start_error = None
        self.case_error = None

    def start(self):
        self.starts += 1
        if self.start_error:
            raise self.start_error

    def stop(self):
        self.stops += 1

    def _case(self, fields):
        if self.case_error:
            raise self.case_error
        return super()._case(fields)

    def sequence(self):
        return [(op, tuple(fields.get(key) for key in SEQUENCE_KEYS)) for op, fields in self.calls if op != "shot"]


class Fleet(base.Cli):
    """A Cli on the interactions fixture that gives every worker its own configured driver."""

    def __init__(self, test, configure=None):
        super().__init__(test)
        self.package = base.build_interactions_package(self.root)
        self.configure = configure or (lambda driver: None)
        self.drivers = []

    def make_driver(self, package, root, scratch, color_scheme="light"):
        driver = TrackedDriver()
        self.configure(driver)
        self.drivers.append(driver)
        return driver

    def go(self, *extra, **kwargs):
        return self.run(None, *extra, **kwargs)


def load(folder):
    return (json.loads((folder / m.OUTPUT_NAME).read_text(encoding="utf-8")),
            json.loads((folder / m.SIDECAR_NAME).read_text(encoding="utf-8")))


def strip_times(value):
    if isinstance(value, dict):
        return {k: strip_times(v) for k, v in value.items() if k not in ("startedAt", "finishedAt", "durationMs")}
    if isinstance(value, list):
        return [strip_times(item) for item in value]
    return value


def comparable(folder):
    """What a run decided: no clocks, no worker count, no transcript lists (a parallel run loads pages more often)."""
    output, sidecar = load(folder)
    run = {k: v for k, v in strip_times(sidecar["run"]).items() if k != "workers"}
    result = {"output": {k: output[k] for k in ("matrix", "results", "interactions", "reviewer", "navigation")},
              "artifacts": sorted(a["path"] for a in output["execution"]["artifacts"] if not a["path"].endswith(m.SIDECAR_NAME)),
              "run": run, "sidecar": {k: strip_times(sidecar[k]) for k in ("cases", "axes", "interactions", "reviewer")}}
    if (folder / m.INTERMEDIATE_DIR).is_dir():
        result["intermediate"] = comparable(folder / m.INTERMEDIATE_DIR)
    return result


def relabel(value, old, new):
    return json.loads(json.dumps(value).replace(old, new))


def drop_clock_and_encoding(value):
    """The settle wait is a clock reading of the page's animations, and Chromium may encode the same pixels as
    different PNG bytes, so a capture is compared by its path here and by its pixels below."""
    if isinstance(value, dict):
        return {k: drop_clock_and_encoding(v) for k, v in value.items()
                if k != "waitedMs" and not (k == "sha256" and "path" in value)}
    if isinstance(value, list):
        return [drop_clock_and_encoding(item) for item in value]
    return value


class PartitionTests(unittest.TestCase):
    def test_every_item_lands_in_one_share_in_order_and_the_split_never_changes(self):
        items = [(index, 1 + index % 3) for index in range(40)]
        for workers in (1, 2, 3, 7, 40, 99):
            with self.subTest(workers=workers):
                shares = m.partition(items, workers)
                self.assertEqual(list(range(40)), [item for share in shares for item in share])
                self.assertTrue(all(shares) and len(shares) <= workers)
                self.assertEqual(shares, m.partition(list(items), workers))

    def test_equal_items_split_evenly_so_one_big_page_still_scales(self):
        shares = m.partition([(index, 1) for index in range(100)], 4)
        self.assertEqual([25] * 4, [len(share) for share in shares])

    def test_more_workers_than_items_gives_one_item_per_share(self):
        self.assertEqual([[0], [1], [2]], m.partition([(0, 1), (1, 1), (2, 1)], 10))

    def test_a_heavy_item_never_leaves_an_empty_share(self):
        shares = m.partition([("a", 1), ("b", 1), ("c", 30)], 3)
        self.assertEqual(["a", "b", "c"], [item for share in shares for item in share])
        self.assertTrue(all(shares))


class FakeWorkersTests(unittest.TestCase):
    AXES = ("--axes", "dark,reflow-320")

    def test_the_merged_output_equals_the_serial_one(self):
        fleet = Fleet(self)
        code, _, out = fleet.go(*self.AXES, out="docs/evidence/serial")
        self.assertEqual(0, code)
        expected = comparable(out)
        self.assertEqual(8, len(expected["sidecar"]["interactions"]))
        self.assertTrue(expected["sidecar"]["axes"] and expected["sidecar"]["reviewer"])
        for workers in (2, 3, m.MAX_WORKERS):
            with self.subTest(workers=workers):
                fleet.drivers = []
                label = f"docs/evidence/w{workers}"
                code, summary, out = fleet.go(*self.AXES, "--workers", str(workers), out=label)
                output, sidecar = load(out)
                self.assertEqual(0, code, summary)
                self.assertEqual(expected, relabel(comparable(out), label, "docs/evidence/serial"))
                self.assertEqual(len(fleet.drivers), sidecar["run"]["workers"])
                self.assertTrue(1 < len(fleet.drivers) <= workers)
                self.assertEqual(0, summary["restarts"])
                self.assertEqual([], m.validate_output(fleet.root, out / m.OUTPUT_NAME, output))
                self.assertEqual("PASS", m.build_receipt(fleet.root, f"{label}/{m.OUTPUT_NAME}")["result"])

    def test_one_worker_starts_one_driver_and_writes_no_worker_count(self):
        fleet = Fleet(self)
        code, _, out = fleet.go()
        self.assertEqual((0, 1, 1), (code, len(fleet.drivers), fleet.drivers[0].starts))
        self.assertNotIn("workers", load(out)[1]["run"])

    def test_more_workers_than_work_starts_no_idle_drivers(self):
        fleet = Fleet(self)
        with mock.patch.object(m, "MAX_WORKERS", 50):      # the plain limit is checked on its own below
            code, summary, out = fleet.go("--only", "UI-001", "--workers", "50")
        items = 6 + 4 + 2    # UI-001's cases and interaction attempts, then the reviewer pass of both pages
        self.assertEqual(0, code, summary)
        self.assertEqual(items, len(fleet.drivers))
        self.assertEqual(items, load(out)[1]["run"]["workers"])
        self.assertEqual([1] * items, [d.starts for d in fleet.drivers])

    def test_the_same_package_and_count_give_the_same_assignment(self):
        first, second = Fleet(self), Fleet(self)
        first.go(*self.AXES, "--workers", "3")
        second.go(*self.AXES, "--workers", "3")
        self.assertEqual([d.sequence() for d in first.drivers], [d.sequence() for d in second.drivers])

    def test_a_later_phase_gets_a_fresh_browser_on_each_driver_it_uses(self):
        fleet = Fleet(self)
        fleet.go("--axes", "dark", "--workers", "2")
        self.assertEqual([1, 1], [d.starts for d in fleet.drivers])
        self.assertTrue(all(d.restarts == 1 for d in fleet.drivers if any(op == "axis" for op, _ in d.calls)))

    def test_every_driver_is_stopped_once(self):
        fleet = Fleet(self)
        fleet.go(*self.AXES, "--workers", "4")
        self.assertGreater(len(fleet.drivers), 1)
        self.assertEqual([1] * len(fleet.drivers), [d.stops for d in fleet.drivers])

    def test_a_driver_that_raises_stops_them_all_and_the_error_surfaces(self):
        for error in (RuntimeError("worker blew up"), KeyboardInterrupt("worker blew up")):
            with self.subTest(error=type(error).__name__):
                def configure(driver):
                    driver.case_error = None if fleet.drivers else error

                fleet = Fleet(self, configure)
                with self.assertRaisesRegex(type(error), "worker blew up"):
                    fleet.go("--workers", "3")
                self.assertGreater(len(fleet.drivers), 1)
                self.assertEqual([1] * len(fleet.drivers), [d.stops for d in fleet.drivers])

    def test_a_driver_that_cannot_start_fails_the_run_with_exit_2_and_all_are_stopped(self):
        def configure(driver):
            driver.start_error = m.DriverError("chromium is missing")

        fleet = Fleet(self, configure)
        code, summary, _ = fleet.go("--workers", "3")
        self.assertEqual(2, code)
        self.assertIn("browser could not start", summary["error"])
        self.assertEqual([1] * len(fleet.drivers), [d.stops for d in fleet.drivers])

    def test_a_driver_out_of_restarts_blocks_only_its_own_share(self):
        def configure(driver):
            for state in ("ready", "loading", "empty"):
                for target in ("390", "1200"):
                    driver.overrides[("UI-001", state, target)] = {"raise": m.DriverTimeout("no reply")}

        fleet = Fleet(self, configure)
        code, summary, out = fleet.go("--workers", "2")
        output, sidecar = load(out)
        # The first share holds UI-001's cases and interactions and the first three UI-002 cases. It runs out of
        # restarts on its fourth timeout; the second share (the rest of UI-002 and the reviewer pass) is untouched.
        self.assertEqual(["FAIL"] * 4 + ["BLOCKED"] * 5 + ["PASS"] * 3, [r["result"] for r in output["results"]])
        self.assertEqual((1, m.MAX_RESTARTS + 1), (code, summary["restarts"]))
        blocked = next(r for r in sidecar["cases"] if (r["surface"], r["state"], r["target"]) == ("UI-002", "ready", "390"))
        self.assertIn("restart limit", blocked["reasons"][0])
        self.assertEqual({"BLOCKED"}, {r["result"] for r in sidecar["interactions"] if r["page"] == "index.html"})
        self.assertEqual({"PASS"}, {r["result"] for r in sidecar["interactions"] if r["page"] == "details.html"})
        self.assertEqual({"PASS"}, {r["result"] for r in sidecar["reviewer"]})

    def test_workers_outside_one_to_the_maximum_are_refused_before_any_browser_work(self):
        self.assertEqual(4, m.MAX_WORKERS)
        for value in ("0", "-1", str(m.MAX_WORKERS + 1), "50"):
            with self.subTest(workers=value):
                fleet = Fleet(self)
                code, summary, _ = fleet.go("--workers", value)
                self.assertEqual((2, []), (code, fleet.drivers))
                self.assertEqual("--workers must be from 1 to 4", summary["error"])

    def test_a_repeated_axis_is_refused_before_any_browser_starts_for_every_worker_count(self):
        for workers in ("1", "2", "4"):
            with self.subTest(workers=workers):
                fleet = Fleet(self)
                code, summary, _ = fleet.go("--axes", "dark,reflow-320,dark", "--workers", workers)
                self.assertEqual((2, []), (code, fleet.drivers))
                self.assertEqual("axis dark is repeated; name each axis once", summary["error"])

    def test_carry_only_derived_diff_recapture_intermediate_and_dark_work_under_workers(self):
        fleet = Fleet(self)
        _, _, first = fleet.go(out="docs/evidence/first")
        carry = str(first / m.OUTPUT_NAME)
        derived = fleet.root / "derived.json"
        derived.write_text(json.dumps({"UI-001": ["empty"]}), encoding="utf-8")
        combinations = [["--carry-from", carry], ["--carry-from", carry, "--recapture-carried"], ["--only", "UI-002"],
                        ["--intermediate"], ["--color-scheme", "dark"], ["--derived-once", "--derived", str(derived)]]
        if base.HAS_PILLOW:
            combinations.append(["--diff-against", str(first)])
        for index, extra in enumerate(combinations):
            with self.subTest(extra=extra):
                serial_code, _, serial = fleet.go(*extra, out=f"docs/evidence/s{index}")
                parallel_code, _, parallel = fleet.go(*extra, "--workers", "3", out=f"docs/evidence/p{index}")
                self.assertEqual(serial_code, parallel_code)
                self.assertEqual(comparable(serial), relabel(comparable(parallel), f"docs/evidence/p{index}", f"docs/evidence/s{index}"))
        carried = load(fleet.root / "docs/evidence/p0")[1]["run"]
        self.assertEqual(12, carried["carried"])


class RealBrowserWorkersTests(unittest.TestCase):
    playwright = base.RealBrowserTests.playwright
    run_main = base.RealBrowserTests.run_main

    def test_two_workers_match_one_in_real_chromium(self):
        module = self.playwright()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = base.build_interactions_package(root)
            axes = ("--axes", "dark,reflow-320")
            code, text = self.run_main(module, root, package, "--out", "docs/evidence/one", *axes)
            self.assertEqual(0, code, text)
            code, text = self.run_main(module, root, package, "--out", "docs/evidence/two", *axes, "--workers", "2")
            self.assertEqual(0, code, text)
            one, two = root / "docs/evidence/one", root / "docs/evidence/two"
            output, sidecar = load(two)
            self.assertEqual(2, sidecar["run"]["workers"])
            self.assertEqual({"PASS"}, {r["result"] for r in output["results"]})
            self.assertEqual((8, 8), (len(output["interactions"]), len(sidecar["interactions"])))
            self.assertEqual(4, sum(1 for r in sidecar["axes"] if r["axis"] == "dark"))
            self.assertEqual(drop_clock_and_encoding(comparable(one)),
                             relabel(drop_clock_and_encoding(comparable(two)), "docs/evidence/two", "docs/evidence/one"))
            self.assertEqual([], m.validate_output(root, two / m.OUTPUT_NAME, output))
            self.assertEqual("PASS", base.build_receipt(root, f"docs/evidence/two/{m.OUTPUT_NAME}")["result"])
            self.assertEqual([], output["network"] + output["popups"] + output["forms"])
            for row in output["console"]:
                self.assertEqual("Unrecognized Content-Security-Policy directive 'navigate-to'.", row["message"])
            self.assertEqual(sorted(p.name for p in one.glob("*.png")), sorted(p.name for p in two.glob("*.png")))
            if base.HAS_PILLOW:
                from PIL import Image, ImageChops
                for png in one.glob("*.png"):
                    with Image.open(png) as left, Image.open(two / png.name) as right:
                        self.assertIsNone(ImageChops.difference(left.convert("RGBA"), right.convert("RGBA")).getbbox(), png.name)

    def test_carry_and_intermediate_in_real_chromium_under_workers(self):
        module = self.playwright()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = base.build_interactions_package(root)
            code, text = self.run_main(module, root, package, "--out", "docs/evidence/first", "--workers", "2")
            self.assertEqual(0, code, text)
            code, text = self.run_main(module, root, package, "--out", "docs/evidence/second", "--workers", "2",
                                       "--carry-from", str(root / "docs/evidence/first" / m.OUTPUT_NAME), "--intermediate")
            self.assertEqual(0, code, text)
            second = root / "docs/evidence/second"
            _, sidecar = load(second)
            self.assertEqual(12, sidecar["run"]["carried"])
            self.assertEqual([], list(second.glob("*.png")))
            self.assertEqual("PASS", base.build_receipt(root, f"docs/evidence/second/{m.OUTPUT_NAME}")["result"])
            inter, inter_sidecar = load(second / m.INTERMEDIATE_DIR)
            self.assertEqual({"PASS"}, {r["result"] for r in inter["results"]})
            self.assertEqual(8, len(inter_sidecar["interactions"]))
            self.assertEqual("PASS", base.build_receipt(
                root, f"docs/evidence/second/{m.INTERMEDIATE_DIR}/{m.OUTPUT_NAME}")["result"])

    def test_no_driver_process_outlives_the_run(self):
        module = self.playwright()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = base.build_interactions_package(root)
            started = []
            original = m.NodeDriver.start

            def spy(driver):
                original(driver)
                started.append(driver.proc)

            with mock.patch.object(m.NodeDriver, "start", spy):
                code, text = self.run_main(module, root, package, "--out", "docs/evidence/stop", "--workers", "2")
            self.assertEqual(0, code, text)
            self.assertEqual(2, len(started))
            self.assertTrue(all(proc.poll() is not None for proc in started))


    def test_an_interrupt_in_the_main_thread_stops_every_driver(self):
        module = self.playwright()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = base.build_interactions_package(root)
            started = []
            original = m.NodeDriver.start

            def spy(driver):
                original(driver)
                started.append(driver.proc)
                if len(started) == 2:
                    _thread.interrupt_main()     # what Ctrl-C does, once every browser is up and working

            with mock.patch.object(m.NodeDriver, "start", spy), self.assertRaises(KeyboardInterrupt):
                self.run_main(module, root, package, "--out", "docs/evidence/interrupt", "--workers", "2")
            self.assertEqual(2, len(started))
            self.assertTrue(all(proc.poll() is not None for proc in started))


if __name__ == "__main__":
    unittest.main()

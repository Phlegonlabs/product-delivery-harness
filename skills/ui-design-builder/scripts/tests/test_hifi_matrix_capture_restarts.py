"""hifi_matrix_capture: one stuck operation or one failed restart blocks only the work that depends on it.

Fake drivers for the logic, one real Chromium run for a control that freezes its page. Synthetic fixture pages only.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_hifi_matrix_capture as base  # noqa: E402
import test_hifi_matrix_capture_workers as workers  # noqa: E402

m = base.m
# A sign-out operation that never settles, listed before a working operation on the same page.
SIGN_OUT = {"id": "UI-001-sign-out", "source": {"surface": "UI-001", "state": "ready"},
            "control": "sign-out", "kind": "feedback", "destination": {"surface": "UI-001", "state": "ready"}}


def rows(records):
    return [(r["id"], r["target"], r["trigger"], r["result"]) for r in records]


class StuckOperationTests(unittest.TestCase):
    def test_a_stuck_operation_blocks_only_its_own_remaining_attempts(self):
        def configure(driver):
            for target in ("390", "1200"):
                for trigger in m.TRIGGERS:
                    driver.interact_scripts[(SIGN_OUT["id"], target, trigger)] = {"raise": m.DriverTimeout("no reply")}

        fleet = workers.Fleet(self, configure)
        fleet.package = base.build_interactions_package(fleet.root, interactions=[SIGN_OUT] + base.INTERACTIONS)
        seen = {}
        for count in ("1", "2", "3", "4"):      # at 4 the split falls inside the stuck operation's attempts
            with self.subTest(workers=count), mock.patch.object(m, "MAX_RESTARTS", 1):
                fleet.drivers = []
                code, summary, out = fleet.go("--axes", "dark", "--workers", count, out=f"docs/evidence/w{count}")
                output, sidecar = workers.load(out)
                self.assertEqual((1, 2, []), (code, summary["restarts"], summary["problems"]))
                stuck = [r for r in sidecar["interactions"] if r["id"] == SIGN_OUT["id"]]
                self.assertEqual(["FAIL", "FAIL", "BLOCKED", "BLOCKED"], [r["result"] for r in stuck])
                self.assertTrue(all("interaction timed out" in r["reasons"][0] for r in stuck[:2]))
                self.assertEqual([["operation browser driver restart limit (1) reached: UI-001-sign-out"]] * 2,
                                 [r["reasons"] for r in stuck[2:]])
                # Its page's other operation, reviewer row and axis rows still run, and so does the other page.
                others = [r for r in sidecar["interactions"] if r["id"] != SIGN_OUT["id"]]
                self.assertEqual({"PASS"}, {r["result"] for r in others + sidecar["reviewer"] + sidecar["axes"]})
                self.assertEqual({"PASS"}, {r["result"] for r in output["results"]})
                self.assertEqual({"index.html", "details.html"}, {r["page"] for r in others + sidecar["axes"]})
                seen[count] = rows(sidecar["interactions"])
        self.assertEqual([seen["1"]] * 4, list(seen.values()))


def hang_then_fail_one_restart(case):
    """A Fleet configure: this case hangs, and the fleet's first restart, the one after it, cannot start a browser."""
    failures = [m.DriverError("chromium did not start")]

    def configure(driver):
        driver.overrides[case] = {"raise": m.DriverTimeout("hung case")}
        restart = driver.restart

        def flaky_restart():
            restart()
            if failures:
                raise failures.pop()

        driver.restart = flaky_restart
    return configure


class FailedRestartTests(unittest.TestCase):
    def test_a_browser_that_cannot_restart_blocks_only_the_rest_of_its_page(self):
        for count in ("1", "2"):
            with self.subTest(workers=count):
                fleet = workers.Fleet(self, hang_then_fail_one_restart(("UI-001", "ready", "390")))
                code, _, out = fleet.go("--workers", count)
                output, sidecar = workers.load(out)
                self.assertEqual(1, code)
                self.assertEqual(["FAIL"] + ["BLOCKED"] * 5 + ["PASS"] * 6, [r["result"] for r in output["results"]])
                self.assertIn("timed out", sidecar["cases"][0]["reasons"][0])
                blocked = [r for r in sidecar["cases"] + sidecar["interactions"] if r["result"] == "BLOCKED"]
                self.assertEqual({"index.html"}, {r["page"] for r in blocked})
                self.assertEqual({"browser driver could not restart: chromium did not start"},
                                 {r["reasons"][0] for r in blocked})
                # The next page starts a fresh browser: its cases, operations and every reviewer row pass.
                self.assertEqual({"PASS"}, {r["result"] for r in sidecar["interactions"] if r["page"] == "details.html"})
                self.assertEqual({"PASS"}, {r["result"] for r in sidecar["reviewer"]})

    def test_a_browser_that_cannot_restart_for_the_next_phase_does_not_stop_the_run(self):
        failures = [m.DriverError("chromium did not start")]

        def configure(driver):
            restart = driver.restart

            def flaky_restart():
                restart()
                if failures:
                    raise failures.pop()

            driver.restart = flaky_restart

        # No case hangs, so the first restart is a worker's fresh browser for the axis phase, and it fails.
        code, summary, out = workers.Fleet(self, configure).go("--axes", "dark", "--workers", "2")
        _, sidecar = workers.load(out)
        self.assertEqual((0, 1), (code, summary["restarts"]))     # its first page started a fresh browser
        self.assertEqual({"PASS"}, {r["result"] for r in sidecar["axes"]})

    def test_a_worker_whose_browser_is_down_at_the_end_of_a_phase_runs_the_next_phase(self):
        # The first worker's last base item hangs and its browser cannot restart. In the axis phase that worker
        # owns index.html, so its rows show whether it started a fresh browser.
        fleet = workers.Fleet(self, hang_then_fail_one_restart(("UI-002", "loading", "390")))
        code, _, out = fleet.go("--axes", "dark", "--workers", "2")
        _, sidecar = workers.load(out)
        self.assertEqual(1, code)
        self.assertIn("timed out", next(r for r in sidecar["cases"] if r["state"] == "loading"
                                        and r["surface"] == "UI-002" and r["target"] == "390")["reasons"][0])
        rows_on_index = [r for r in sidecar["axes"] if r["page"] == "index.html"]
        self.assertEqual(["PASS"] * 4, [r["result"] for r in rows_on_index])


class RealBrowserStuckOperationTests(unittest.TestCase):
    playwright = base.RealBrowserTests.playwright
    run_main = base.RealBrowserTests.run_main

    def test_a_control_that_freezes_its_page_blocks_only_its_own_operation_in_real_chromium(self):
        module = self.playwright()
        sign_out = dict(SIGN_OUT, id="UI-002-sign-out", source={"surface": "UI-002", "state": "ready"},
                        destination={"surface": "UI-002", "state": "ready"})
        button = '<button type="button" class="card" data-control-id="sign-out" onclick="for (;;) {}">Sign out</button>'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = base.build_package(root, details_extra=button, manifest_edit=lambda manifest: manifest.update(
                interactions=[base.INTERACTIONS[0], sign_out, base.INTERACTIONS[1]]))
            trees, original = [], m.NodeDriver.start

            def spy(driver):
                original(driver)
                trees.append(workers.process_tree(driver.proc.pid))     # the Node driver and the Chromium below it

            with mock.patch.object(m.NodeDriver, "start", spy), mock.patch.object(m, "MAX_RESTARTS", 1), \
                    mock.patch.dict(m.Runner.__init__.__kwdefaults__, {"case_timeout_s": 5}):
                code, text = self.run_main(module, root, package, "--out", "docs/evidence/stuck")
            _, sidecar = workers.load(root / "docs/evidence/stuck")
            self.assertEqual(1, code, text)
            self.assertEqual([("UI-001-to-details", "390", "click", "PASS"), ("UI-001-to-details", "390", "keyboard", "PASS"),
                              ("UI-001-to-details", "1200", "click", "PASS"), ("UI-001-to-details", "1200", "keyboard", "PASS"),
                              ("UI-002-sign-out", "390", "click", "FAIL"), ("UI-002-sign-out", "390", "keyboard", "FAIL"),
                              ("UI-002-sign-out", "1200", "click", "BLOCKED"), ("UI-002-sign-out", "1200", "keyboard", "BLOCKED"),
                              ("UI-002-to-desk", "390", "click", "PASS"), ("UI-002-to-desk", "390", "keyboard", "PASS"),
                              ("UI-002-to-desk", "1200", "click", "PASS"), ("UI-002-to-desk", "1200", "keyboard", "PASS")],
                             rows(sidecar["interactions"]))
            self.assertEqual({"PASS"}, {r["result"] for r in sidecar["cases"] + sidecar["reviewer"]})
            self.assertEqual(3, len(trees))                     # the first browser and one per stuck attempt
            self.assertTrue(all(len(tree) > 1 for tree in trees), trees)
            self.assertEqual([], workers.survivors(trees))      # every frozen browser was stopped


if __name__ == "__main__":
    unittest.main()

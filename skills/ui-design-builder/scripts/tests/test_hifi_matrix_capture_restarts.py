"""hifi_matrix_capture: one stuck operation blocks only its own remaining attempts.

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
        for count in ("1", "2"):
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
        self.assertEqual(seen["1"], seen["2"])


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

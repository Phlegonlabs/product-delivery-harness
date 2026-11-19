"""review_evidence.py ready: the parent's check before the wave and before the re-review.

Each capture is a real hifi_matrix_capture.py output recorded with the fake browser
from test_hifi_matrix_capture; no test starts a browser. Synthetic fixtures only.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hifi_matrix_capture as m  # noqa: E402
import review_evidence as evidence  # noqa: E402
from test_hifi_matrix_capture import PACKAGE_DIR, Cli, FakeDriver, build_package  # noqa: E402


def clean_a11y(fields, axis):
    """Every requested measurement ran and found nothing."""
    return {"rows": [], "checked": {name: 1 for name in fields["a11y"]["measures"]}, "incomplete": False, "fonts": None}


def low_contrast_price(fields, axis):
    """One contrast failure on the UI-001 ready view, at every target."""
    reply = clean_a11y(fields, axis)
    if fields["surface"] == "UI-001" and fields["state"] == "ready" and "contrast" in fields["a11y"]["measures"]:
        reply["rows"] = [{"measure": "contrast", "selector": "p#price", "level": "fail", "ratio": 3.1, "limit": 4.5}]
    return reply


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.cli = Cli(self)
        self.root = self.cli.root

    def capture(self, *extra, driver=None, a11y=clean_a11y, measure=True):
        """Run the driver as the author does; return the repository-relative ui-output.json path."""
        driver = driver or FakeDriver()
        driver.a11y_script = a11y
        _, _, out = self.cli.run(driver, *(("--measure-a11y",) if measure else ()), *extra)
        return (out / m.OUTPUT_NAME).relative_to(self.root).as_posix()

    def ready(self, *captures, package=PACKAGE_DIR, ledger=None):
        argv = ["ready", "--repo-root", str(self.root), "--package", package]
        for capture in captures:
            argv += ["--capture", capture]
        if ledger:
            argv += ["--ledger", ledger]
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = evidence.main(argv)
        return code, buffer.getvalue()

    def write_json(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return relative

    def test_a_clean_capture_of_the_frozen_bytes_is_ready(self):
        code, text = self.ready(self.capture())
        entry = self.root / PACKAGE_DIR / "index.html"
        self.assertEqual(0, code, text)
        self.assertEqual(f"READY {PACKAGE_DIR}/index.html @ sha256:{hashlib.sha256(entry.read_bytes()).hexdigest()}\n", text)

    def test_blocked_and_failed_cases_are_not_ready(self):
        driver = FakeDriver()
        for state in ("ready", "loading", "empty"):
            for target in ("390", "1200"):
                driver.overrides[("UI-001", state, target)] = {"raise": m.DriverTimeout("no reply")}
        code, text = self.ready(self.capture(driver=driver))
        self.assertEqual(1, code, text)
        self.assertIn("NOT READY", text)
        self.assertIn("- BLOCKED: UI-001/empty/390, UI-001/empty/1200 (", text)
        self.assertIn("restart limit", text)
        self.assertIn("- FAIL: UI-001/ready/390, UI-001/ready/1200, UI-001/loading/390 and 1 more (case timed out", text)
        # A hang gets one rerun, then goes to the owner: no endless reruns for a tool limit.
        self.assertIn("Fix: a hang or a driver failure: fix what hangs and rerun the driver once; if the row fails the "
                      "same way again, it is a tool limit and the parent records the candidate blocked for the owner.", text)
        self.assertNotIn("this was not observed", text)

    def test_a_blocked_axis_row_is_not_ready(self):
        driver = FakeDriver()
        driver.axis_error["forced-colors"] = m.DriverError("page.emulateMedia: forced colors are not supported")
        code, text = self.ready(self.capture("--axes", "forced-colors", driver=driver))
        self.assertEqual(1, code, text)
        self.assertIn("- BLOCKED: UI-001/ready/390 under forced-colors", text)
        self.assertIn("forced colors are not supported", text)
        self.assertIn("it is a tool limit and the parent records the candidate blocked for the owner", text)

    def test_a_page_that_never_opens_is_a_tool_limit_and_a_page_defect_is_not(self):
        class ShotFails(FakeDriver):
            def _shot(self, fields):
                if Path(fields["path"]).name.startswith("UI-002-loading-1200-"):
                    raise m.DriverError("page.screenshot: Target closed")
                return super()._shot(fields)

        driver = ShotFails()
        driver.open_error["index.html"] = m.DriverTimeout("open gave no reply within 40s")
        driver.overrides[("UI-002", "ready", "390")] = {"geometry": {"overflowX": 30}}
        code, text = self.ready(self.capture(driver=driver))
        self.assertEqual(1, code, text)
        lines = text.splitlines()

        def line(reason):
            return next((row for row in lines if reason in row), f"no line for {reason!r} in:\n{text}")
        for reason in ("(page did not open: open gave no reply within 40s)",
                       "reviewer pass on index.html (page did not open, so its reviewer rows were not measured)",
                       "UI-002/loading/1200 (screenshot failed: page.screenshot: Target closed)"):
            self.assertIn("Fix: a hang or a driver failure: fix what hangs and rerun the driver once;", line(reason))
        self.assertIn("UI-002/ready/390 (horizontal overflow 30px). Fix: fix it and rerun the driver; "
                      "the author's last capture is a clean run.", text)

    def test_a_partial_capture_is_not_ready(self):
        code, text = self.ready(self.capture("--only", "UI-001"))
        self.assertEqual(1, code, text)
        self.assertIn("lacks 6 of the package's cases, first UI-002/ready/390", text)
        self.assertIn("Fix: rerun the driver on the whole package, without --only.", text)

    def test_a_capture_of_other_bytes_is_not_ready(self):
        capture = self.capture()
        build_package(self.root, details_extra="<p>Edited after the capture.</p>")
        code, text = self.ready(capture)
        self.assertEqual(1, code, text)
        self.assertIn("observed details.html at sha256:", text)
        self.assertIn("observed index.html at sha256:", text)
        self.assertIn("Fix: rerun hifi_matrix_capture.py on the frozen bytes and never edit its output.", text)

    def test_a_capture_of_another_package_is_not_ready(self):
        capture = self.capture()
        shutil.copytree(self.root / PACKAGE_DIR, self.root / "docs/design/ui-references/other")
        code, text = self.ready(capture, package="docs/design/ui-references/other")
        self.assertEqual(1, code, text)
        self.assertIn(f"observed {PACKAGE_DIR}/index.html, not the frozen package docs/design/ui-references/other/index.html",
                      text)

    def test_an_edited_sidecar_is_not_ready(self):
        capture = self.capture()
        sidecar = self.root / capture.replace(m.OUTPUT_NAME, m.SIDECAR_NAME)
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        data["cases"][0]["result"] = "PASS "
        sidecar.write_text(json.dumps(data), encoding="utf-8")
        code, text = self.ready(capture)
        self.assertEqual(1, code, text)
        self.assertIn("artifact identity is stale", text)
        self.assertIn(m.SIDECAR_NAME, text)

    def reseal(self, capture, edit):
        """Edit a capture's sidecar and bind its new hash in the output, as a hand edit that hides itself would."""
        output_path = self.root / capture
        output = json.loads(output_path.read_text(encoding="utf-8"))
        binding = next(b for b in output["execution"]["artifacts"] if b["path"].endswith("/" + m.SIDECAR_NAME))
        sidecar_path = self.root / binding["path"]
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        edit(sidecar, capture.rsplit("/", 1)[0])
        data = json.dumps(sidecar).encode("utf-8")
        sidecar_path.write_bytes(data)
        binding["sha256"] = hashlib.sha256(data).hexdigest()
        output_path.write_text(json.dumps(output), encoding="utf-8")

    def test_a_resealed_sidecar_must_hold_what_the_driver_wrote(self):
        """Each edit keeps every hash consistent; only the records disagree with what the driver writes."""
        def ready_case(sidecar):        # the UI-001/ready/390 record, the ledger row's acceptance case
            return sidecar["cases"][0]

        def both(sidecar, folder):
            record = ready_case(sidecar)
            record["carriedFrom"] = {"result": "PASS", "pageSha256": record["pageSha256"], "capture": dict(record["capture"]),
                                     "sourceOutput": {"path": "docs/evidence/run0/ui-output.json", "sha256": "1" * 64}}

        def old_as_fresh(sidecar, folder):
            record = ready_case(sidecar)
            record["capture"], record["carriedFrom"] = record["carriedFrom"]["capture"], None

        def other_case(sidecar, folder):
            ready_case(sidecar)["carriedFrom"]["capture"] = dict(sidecar["cases"][1]["carriedFrom"]["capture"])

        def set_capture(**fields):
            return lambda sidecar, folder: ready_case(sidecar)["capture"].update(
                {key: value.format(folder=folder) for key, value in fields.items()})
        rerun = "Fix: rerun hifi_matrix_capture.py on the frozen bytes and never edit its output."
        # (edit, the line it gives, carried run, open ledger row on the edited case)
        edits = {
            "outside path": (set_capture(path="../../outside.png"),
                             "UI-001/ready/390: capture lies outside the repository", False, True),
            "missing file": (set_capture(path="{folder}/UI-001-ready-390-none.png"),
                             "UI-001/ready/390: capture file is missing", False, True),
            "other bytes": (set_capture(sha256="0" * 64),
                            "UI-001/ready/390: capture bytes differ from its sha256", False, True),
            "capture and carriedFrom": (both, "UI-001/ready/390: names both a capture and carriedFrom", False, True),
            "earlier screenshot as fresh": (old_as_fresh,
                                            "UI-001/ready/390: capture is not this run's screenshot", True, True),
            "another case carried": (other_case,
                                     "UI-001/ready/390: carried capture is not this case's screenshot", True, False),
            "case dropped": (lambda sidecar, folder: sidecar["cases"].pop(),
                             "has no case record for 1 of the output's cases", False, False),
            "empty a11y": (lambda sidecar, folder: sidecar.update(a11y={}),
                           "its a11y object is not the one --measure-a11y writes", False, False),
            "other run": (lambda sidecar, folder: sidecar["run"].update(finishedAt="2020-01-01T00:00:00+00:00"),
                          "names another subject or run than", False, False),
            "subject dropped": (lambda sidecar, folder: sidecar.pop("subject"),
                                "names another subject or run than", False, False),
            "run times dropped": (lambda sidecar, folder: [sidecar["run"].pop(key) for key in ("startedAt", "finishedAt")],
                                  "names another subject or run than", False, False),
            "PASS without a screenshot": (lambda sidecar, folder: ready_case(sidecar).update(capture=None),
                                          "UI-001/ready/390: is PASS without a screenshot of this run or a carried one",
                                          False, False),
        }
        ledger = self.ledger([self.family("DF-001", "open", "UI-001", "ready", "390")])
        code, text = self.ready(self.capture(), ledger=ledger)
        self.assertEqual(0, code, "a fresh screenshot of this run is the after-capture: " + text)
        for name, (edit, expected, carried, with_ledger) in edits.items():
            with self.subTest(edit=name):
                capture = self.capture("--carry-from", self.capture(), driver=FakeDriver()) if carried else self.capture()
                self.reseal(capture, edit)
                code, text = self.ready(capture, ledger=ledger if with_ledger else None)
                self.assertEqual(1, code, text)
                line = next((row for row in text.splitlines() if expected in row), None)
                self.assertIsNotNone(line, f"{expected!r} not in:\n{text}")
                self.assertTrue(line.endswith(rerun), line)

    def test_a_capture_without_measured_accessibility_is_not_ready(self):
        code, text = self.ready(self.capture(measure=False))
        self.assertEqual(1, code, text)
        self.assertIn("has no a11y measurements. Fix: rerun the driver with --measure-a11y.", text)

    def test_a_measured_accessibility_failure_needs_a_disposition(self):
        capture = self.capture(a11y=low_contrast_price)
        dispositions = capture.replace(m.OUTPUT_NAME, evidence.A11Y_DISPOSITIONS)
        code, text = self.ready(capture)
        self.assertEqual(1, code, text)
        self.assertIn("- contrast fails on p#price at UI-001/ready/390, UI-001/ready/1200 with no disposition. "
                      f"Fix: fix it, or record the reason in {dispositions}.", text)

        reason = "The price sits on the brand plate the owner approved; contrast is checked there by eye."
        self.write_json(dispositions, {"schema": "a11y-dispositions/1", "dispositions": [
            {"measure": "contrast", "selector": "p#price", "surface": "UI-002", "reason": reason}]})
        code, text = self.ready(capture)
        self.assertEqual(1, code, "a disposition narrowed to another surface does not cover UI-001")

        self.write_json(dispositions, {"schema": "a11y-dispositions/1", "dispositions": [
            {"measure": "contrast", "selector": "p#price", "surface": "UI-001", "reason": reason}]})
        code, text = self.ready(capture)
        self.assertEqual(0, code, text)

        self.write_json(dispositions, {"schema": "a11y-dispositions/1", "dispositions": [
            {"measure": "contrast", "selector": "p#price", "reason": " "}]})
        code, text = self.ready(capture)
        self.assertEqual(2, code, text)
        self.assertTrue(text.startswith("INVALID: "), text)

    def ledger(self, families):
        return self.write_json("docs/design/evidence/matrix/defect-ledger.json",
                               {"schema": "ui-defect-ledger/1", "families": families})

    def family(self, ident, status, surface, state, target):
        return {"id": ident, "status": status,
                "acceptanceCases": [{"surface": surface, "state": state, "target": target}]}

    def test_re_review_needs_an_after_capture_for_every_open_ledger_row(self):
        first = self.capture()
        repaired = FakeDriver()
        repaired.overrides[("UI-001", "loading", "390")] = {"style": "repaired spacing"}
        carried = self.capture("--carry-from", first, driver=repaired)
        ledger = self.ledger([self.family("DF-001", "open", "UI-001", "loading", "390"),
                              self.family("DF-002", "block", "UI-002", "ready", "1200"),
                              self.family("DF-003", "advisory", "UI-002", "ready", "390"),
                              self.family("DF-004", "closed", "UI-002", "loading", "390")])
        code, text = self.ready(carried, ledger=ledger)
        self.assertEqual(1, code, text)
        self.assertIn("- ledger row DF-002 has no after-capture for UI-002/ready/1200: the case was carried", text)
        self.assertIn("--recapture-carried", text)
        for settled in ("DF-001", "DF-003", "DF-004"):
            self.assertNotIn(settled, text)

        again = FakeDriver()
        again.overrides[("UI-001", "loading", "390")] = {"style": "repaired spacing"}
        recaptured = self.capture("--carry-from", first, "--recapture-carried", driver=again)
        code, text = self.ready(recaptured, ledger=ledger)
        self.assertEqual(0, code, text)

    def test_a_ledger_row_without_acceptance_cases_is_not_ready(self):
        ledger = self.ledger([{"id": "DF-001", "status": "open", "acceptanceCases": []}])
        code, text = self.ready(self.capture(), ledger=ledger)
        self.assertEqual(1, code, text)
        self.assertIn("ledger row DF-001 names no acceptance case", text)

    def test_unreadable_or_malformed_input_is_invalid(self):
        capture = self.capture()
        cases = {
            "missing capture": dict(captures=("docs/evidence/none/ui-output.json",)),
            "not a capture": dict(captures=(self.write_json("docs/evidence/other.json", {"schema": "ui-output/3"}),)),
            "missing package": dict(captures=(capture,), package="docs/design/ui-references/none"),
            "ledger schema": dict(captures=(capture,), ledger=self.write_json("docs/ledger.json", {"families": []})),
            "ledger case": dict(captures=(capture,), ledger=self.ledger([{"id": "DF-001", "status": "open",
                                                                          "acceptanceCases": [{"surface": "UI-001"}]}])),
        }
        for name, case in cases.items():
            with self.subTest(name=name):
                code, text = self.ready(*case["captures"], package=case.get("package", PACKAGE_DIR),
                                        ledger=case.get("ledger"))
                self.assertEqual(2, code, text)
                self.assertTrue(text.startswith("INVALID: "), text)

    def test_the_receipt_command_is_unchanged(self):
        capture = self.capture()
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = evidence.main(["--repo-root", str(self.root), "--output-artifact", capture,
                                  "--receipt-out", "docs/evidence/receipt.json"])
        self.assertEqual((0, "PASS"), (code, json.loads(buffer.getvalue())["result"]))


if __name__ == "__main__":
    unittest.main()

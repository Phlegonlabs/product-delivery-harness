"""PRD operations retain observable proof when HiFi accepts more product forms."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_ui_design_contract as checker
import hifi_matrix_capture as capture
import test_hifi_matrix_capture as matrix_tests
import test_ui_design_contract as contract_tests
from operation_coverage import hifi_coverage_findings
from test_operation_coverage import prd


def write_manifest(path, manifest):
    html = path.read_text(encoding="utf-8")
    path.write_text(checker.HIFI_MANIFEST_RE.sub(
        lambda _: '<script id="ui-hifi-manifest" type="application/json">'
        + json.dumps(manifest) + '</script>', html), encoding="utf-8")


class FeedbackContractTests(unittest.TestCase):
    def test_operation_kind_depends_on_presentation_and_endpoints(self):
        operation = {"id": "save", "trigger": "Save", "control": "save", "sourceState": "ready",
                     "destination": {"surface": "UI-001", "state": "ready"}, "presentation": "feedback"}
        for presentation in ("feedback", "state", "overlay", "tab", "page"):
            operation["presentation"] = presentation
            for equal in (True, False):
                operation["destination"]["state"] = "ready" if equal else "updated"
                product = prd(operation).replace('`: ready\n', '`: ready, updated\n')
                kind = "navigate" if presentation == "page" else "feedback" if equal else "state"
                action = {"id": "save", "control": "save", "kind": kind,
                          "source": {"surface": "UI-001", "state": "ready"},
                          "destination": copy.deepcopy(operation["destination"])}
                self.assertEqual([], hifi_coverage_findings(product, {"interactions": [action]}))
                action["kind"] = "state" if kind != "state" else "feedback"
                self.assertTrue(hifi_coverage_findings(product, {"interactions": [action]}))

    def test_feedback_accepts_equal_endpoints_and_state_still_rejects_them(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, manifest, scope = contract_tests.materialize_hifi_bundle(Path(temporary))
            action = manifest["interactions"][1]
            action["destination"] = dict(action["source"])
            for kind, passes in (("feedback", True), ("state", False)):
                action["kind"] = kind
                write_manifest(path, manifest)
                findings = []
                checker._validate_hifi_surface(path, findings, scope)
                self.assertEqual(passes, not findings, findings)
            action["kind"] = "feedback"
            action["destination"]["state"] = "updated"
            write_manifest(path, manifest)
            findings = []
            checker._validate_hifi_surface(path, findings, scope)
            self.assertIn("must keep its source", "\n".join(findings))

    def test_receipts_keep_old_rows_and_validate_optional_observations(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, manifest, _ = contract_tests.materialize_hifi_bundle(Path(temporary))
            output = contract_tests.bundle_output(manifest)
            self.assertEqual([], checker._bundle_transcript_findings(output, manifest))
            action = manifest["interactions"][1]
            action.update(kind="feedback", destination=dict(action["source"]))
            output = contract_tests.bundle_output(manifest)
            self.assertTrue(checker._bundle_transcript_findings(output, manifest))
            for row in output["interactions"]:
                if row["id"] == action["id"]:
                    row["observed"] = {"change": {"beforeSha256": "a" * 64, "afterSha256": "b" * 64}}
            self.assertEqual([], checker._bundle_transcript_findings(output, manifest))
            for bad in (None, {"unknown": True}, {"change": {"beforeSha256": "a" * 64, "afterSha256": "a" * 64}}):
                broken = copy.deepcopy(output)
                broken["interactions"][2]["observed"] = bad
                self.assertTrue(checker._bundle_transcript_findings(broken, manifest))


class OperationBrowserTests(unittest.TestCase):
    playwright = matrix_tests.RealBrowserTests.playwright

    def driver(self, extra="", edit=None):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        scratch = self.enterContext(tempfile.TemporaryDirectory())
        package = matrix_tests.build_interactions_package(root, details_extra=extra, page_edit=edit)
        driver = capture.NodeDriver(shutil.which("node"), self.playwright(), capture.read_package(package).files, scratch)
        self.addCleanup(driver.stop)
        driver.start()
        return driver

    def attempt(self, driver, control="save", kind="feedback", destination=None, page="details.html", **extra):
        driver.call("open", page=page, timeoutMs=2000)
        return driver.call("interact", page=page, interaction="operation", surface="UI-002", state="ready",
                           target="390", control=control, kind=kind,
                           destination=destination or {"surface": "UI-002", "state": "ready"},
                           destinationPage=page, trigger="click", timeoutMs=2000, **extra)

    def test_feedback_requires_product_change_and_ignores_focus_alone(self):
        for handler, passes in (("this.textContent += ' saved'", True),
                                ("this.previousElementSibling.value += 'x'", True),
                                ("this.focus()", False)):
            with self.subTest(handler=handler):
                driver = self.driver('<input value="draft"><button data-control-id="save" onclick="'
                                     + handler + '">Save</button>')
                reply = self.attempt(driver)
                self.assertEqual(passes, not reply["result"]["problems"], reply)
                change = reply["result"]["observed"]["change"]
                self.assertEqual(passes, change["beforeSha256"] != change["afterSha256"])
                driver.stop()


if __name__ == "__main__":
    unittest.main()

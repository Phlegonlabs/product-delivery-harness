"""Real product navigation, selection, entry and timeout regressions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import test_hifi_operation_alignment as alignment
import test_hifi_matrix_capture as matrix
import test_ui_design_contract as contract
import check_ui_design_contract as checker


class NavigateContractTests(unittest.TestCase):
    def test_every_navigate_link_must_name_the_destination_state(self):
        for state, href, passes in (
            ("ready", "details.html", True),
            ("ready", "details.html#hifi-state=UI-002/ready", True),
            ("updated", "details.html#hifi-state=UI-002/updated", True),
            ("updated", "details.html", False),
            ("updated", "details.html#hifi-state=UI-002/ready", False),
            ("updated", "details.html#hifi-state=UI-001/updated", False),
        ):
            with self.subTest(state=state, href=href), tempfile.TemporaryDirectory() as temporary:
                path, manifest, scope = contract.materialize_hifi_bundle(Path(temporary))
                manifest["interactions"][0]["destination"]["state"] = state
                alignment.write_manifest(path, manifest)
                html = path.read_text(encoding="utf-8").replace(
                    'data-navigation-id="next" href="details.html"',
                    'data-navigation-id="next" href="' + href + '"')
                path.write_text(html, encoding="utf-8")
                findings = []
                checker._validate_hifi_surface(path, findings, scope)
                self.assertEqual(passes, not findings, findings)


class NavigationBrowserTests(unittest.TestCase):
    playwright = alignment.OperationBrowserTests.playwright
    run_main = alignment.OperationBrowserTests.run_main
    driver = alignment.OperationBrowserTests.driver
    attempt = alignment.OperationBrowserTests.attempt
    def test_navigate_observes_default_explicit_and_same_page_arrivals(self):
        actions = copy.deepcopy(matrix.INTERACTIONS)
        for same_page, state, fragment, passes in (
            (False, "ready", "", True),
            (False, "error", "#hifi-state=UI-002/error", True),
            (False, "error", "", False),
            (False, "error", "#hifi-state=UI-002/ready", False),
            (True, "loading", "#hifi-state=UI-001/loading", True),
        ):
            with self.subTest(same_page=same_page, state=state, fragment=fragment), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                destination = "index.html" if same_page else "details.html"
                actions[0]["destination"] = {"surface": "UI-001" if same_page else "UI-002", "state": state}
                package = matrix.build_interactions_package(root, interactions=actions, page_edit=lambda html:
                    html.replace('href="details.html" data-navigation-id="to-details"',
                                 'href="' + destination + fragment + '" data-navigation-id="to-details"'))
                code, message = self.run_main(self.playwright(), root, package, "--out", "evidence", "--only", "UI-001")
                self.assertEqual(0 if passes else 1, code, message)
                output = json.loads((root / "evidence/ui-output.json").read_text(encoding="utf-8"))
                self.assertEqual({"PASS"} if passes else {"FAIL"}, {row["result"] for row in output["interactions"]})
                if passes:
                    self.assertEqual(4, len(output["navigation"]))

    def test_product_arrival_ignores_other_page_and_previous_visit_selections(self):
        # Seed both legacy shared state and the destination's own previous selection.
        seed = '<script>sessionStorage.setItem("hifi-reviewer:state", "error");' \
               'sessionStorage.setItem("hifi-reviewer:state:index.html", "error");</script>'
        driver = self.driver('<a data-navigation-id="back" href="index.html">Back</a>',
                             edit=lambda html: html.replace('<body', seed + '<body'))
        for trigger in ("click", "keyboard"):
            reply = self.attempt(driver, control="back", kind="navigate", trigger=trigger,
                                 destination={"surface": "UI-001", "state": "ready"}, destination_page="index.html")
            self.assertEqual([], reply["result"]["problems"], reply)
            self.assertEqual("index.html", reply["result"]["arrivedTo"])


if __name__ == "__main__":
    unittest.main()

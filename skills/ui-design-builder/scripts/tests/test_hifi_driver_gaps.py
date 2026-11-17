"""Real product navigation, selection, entry and timeout regressions."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import test_hifi_operation_alignment as alignment
import test_hifi_matrix_capture as matrix
import test_ui_design_contract as contract
import check_ui_design_contract as checker
import hifi_matrix_capture as capture
import test_hifi_matrix_capture_workers as workers


class NavigateContractTests(unittest.TestCase):
    def test_instance_index_requires_a_valid_visible_count(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, manifest, _ = contract.materialize_hifi_bundle(Path(temporary))
            for index, count, passes in ((0, 2, True), (1, 2, True), (-1, 2, False),
                                         (2, 2, False), (True, 2, False), (0, None, False)):
                output = contract.bundle_output(manifest)
                output["interactions"][0]["observed"] = {"instances": count, "instanceIndex": index}
                self.assertEqual(passes, not checker._bundle_transcript_findings(output, manifest))

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

    def test_f1_field_activation_can_hide_the_source_before_entry(self):
        transition = "document.__hifiReviewerRuntime.selectState('loading')"
        for mode in ("activation", "entry", "inert"):
            handler = ('onclick="' + transition + '" onkeydown="if(event.key===\' \'){'
                       'event.preventDefault();' + transition + '}"') if mode == "activation" else (
                       'oninput="' + transition + '"' if mode == "entry" else '')
            driver = self.driver('<section data-hifi-state-view="ready" data-responsive-target="390">'
                '<input data-control-id="save" value="draft" ' + handler + '></section>')
            for trigger in ("click", "keyboard"):
                with self.subTest(mode=mode, trigger=trigger):
                    result = self.attempt(driver, kind="state", trigger=trigger,
                        destination={"surface": "UI-002", "state": "loading"})["result"]
                    self.assertEqual(mode == "inert", bool(result["problems"]), result)
                    self.assertTrue(result["focusCorrect"], result)
            driver.stop()

    def test_same_page_state_hashes_keep_the_existing_non_navigation_contract(self):
        actions = copy.deepcopy(matrix.INTERACTIONS)
        actions[0].update(kind="state", destination={"surface": "UI-001", "state": "loading"})
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = matrix.build_interactions_package(root, interactions=actions, page_edit=lambda html:
                html.replace('href="details.html" data-navigation-id="to-details"',
                             'href="index.html#hifi-state=UI-001/loading" data-navigation-id="to-details"'))
            code, message = self.run_main(self.playwright(), root, package, "--out", "evidence", "--only", "UI-001")
            self.assertEqual(0, code, message)
            output = json.loads((root / "evidence/ui-output.json").read_text(encoding="utf-8"))
            self.assertEqual([], output["navigation"])
            self.assertEqual({"PASS"}, {row["result"] for row in output["interactions"]})

    def test_browser_load_timeout_is_bounded_and_a_fresh_browser_opens_the_next_page(self):
        driver = self.driver(edit=lambda html: html.replace('</head>',
            '<script>while(true){}</script></head>') if 'Harbor desk' in html else html)
        with self.assertRaises(capture.DriverTimeout):
            driver.call("open", page="index.html", timeoutMs=150, timeout=5)
        driver.restart()
        reply = driver.call("open", page="details.html", timeoutMs=2000)
        self.assertIn("390", reply["result"]["targets"])

    def test_data_entry_uses_values_and_retains_feedback_proof(self):
        for markup in ('<input data-control-id="save" value="draft">',
                       '<input data-control-id="save" value="HiFi probe">',
                       '<textarea data-control-id="save">draft</textarea>',
                       '<select data-control-id="save"><option disabled>Unavailable</option>'
                       '<option selected>HKD</option><option disabled>Disabled</option><option>USD</option></select>',
                       '<select data-control-id="save"><option>HKD</option><option selected>USD</option></select>'):
            with self.subTest(markup=markup):
                driver = self.driver(markup)
                for trigger in ("click", "keyboard"):
                    reply = self.attempt(driver, trigger=trigger)["result"]
                    self.assertEqual([], reply["problems"], reply)
                    self.assertTrue(reply["focusCorrect"], reply)
                    change = reply["observed"]["change"]
                    self.assertNotEqual(change["beforeSha256"], change["afterSha256"])
                driver.stop()

    def test_disabled_readonly_and_unchanged_fields_still_fail(self):
        for markup in ('<input data-control-id="save" disabled value="draft">',
                       '<textarea data-control-id="save" readonly>draft</textarea>',
                       '<select data-control-id="save" disabled><option>HKD</option><option>USD</option></select>',
                       '<input data-control-id="save" value="draft" oninput="this.value=\'draft\'">',
                       '<select data-control-id="save"><option>HKD</option></select>'):
            with self.subTest(markup=markup):
                driver = self.driver(markup)
                for trigger in ("click", "keyboard"):
                    reply = self.attempt(driver, trigger=trigger)["result"]
                    self.assertTrue(reply["problems"], reply)
                    if "change" in reply["observed"]:
                        change = reply["observed"]["change"]
                        self.assertEqual(change["beforeSha256"], change["afterSha256"])
                driver.stop()

    def test_repeated_controls_prefer_an_unselected_instance(self):
        for attribute, selected in (("aria-pressed", "true"), ("aria-selected", "true"),
                                    ("aria-checked", "true"), ("aria-current", "page")):
            for all_selected in (False, True):
                with self.subTest(attribute=attribute, all_selected=all_selected):
                    markup = ''.join('<button data-control-id="save" ' + attribute + '="' + value + '" '
                        'onclick="if(this.getAttribute(\'' + attribute + '\')===\'false\')this.textContent+=\' changed\'">'
                        'Segment</button>' for value in (selected, selected if all_selected else "false"))
                    driver = self.driver(markup)
                    for trigger in ("click", "keyboard"):
                        reply = self.attempt(driver, trigger=trigger)["result"]
                        self.assertEqual(all_selected, bool(reply["problems"]), reply)
                        self.assertEqual(0 if all_selected else 1, reply["observed"]["instanceIndex"])
                        self.assertEqual(2, reply["observed"]["instances"])
                        self.assertTrue(reply["focusCorrect"], reply)
                    driver.stop()
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


class PageRecoveryTests(unittest.TestCase):
    def test_f2_exhausted_page_stays_blocked_when_intermediate_work_changes_workers(self):
        def configure(driver):
            for target in ("390", "1200"):
                driver.overrides[("UI-001", "ready", target)] = {"raise": capture.DriverTimeout("slow page")}

        fleet = workers.Fleet(self, configure)
        entry = fleet.package / "index.html"
        manifest = capture.read_package(fleet.package).manifest
        manifest["interactions"] = []
        alignment.write_manifest(entry, manifest)
        with mock.patch.object(capture, "MAX_RESTARTS", 1):
            code, _, out = fleet.go("--workers", "4", "--intermediate")
        self.assertEqual(1, code)
        base, _ = workers.load(out)
        intermediate, details = workers.load(out / capture.INTERMEDIATE_DIR)
        self.assertIn("BLOCKED", {r["result"] for r in base["results"] if r["surface"] == "UI-001"})
        self.assertEqual({"BLOCKED"}, {r["result"] for r in intermediate["results"] if r["surface"] == "UI-001"})
        self.assertEqual({"PASS"}, {r["result"] for r in intermediate["results"] if r["surface"] == "UI-002"})
        self.assertTrue(all("restart limit" in r["reasons"][0]
                            for r in details["cases"] if r["surface"] == "UI-001"))
        # With no interactions, the three source-page intermediate cases span workers 0 and 1.
        shares = capture.partition([(("case", c.page, c), 1) for c in capture.intermediate_plan(
            capture.read_package(fleet.package))], 4)
        self.assertEqual({0, 1}, {i for i, share in enumerate(shares)
                                 if any(item[2].surface == "UI-001" for item in share)})

    def test_recovery_load_failure_does_not_abort_unrelated_pages(self):
        driver = matrix.FakeDriver()
        driver.overrides[("UI-001", "ready", "390")] = {"raise": capture.DriverTimeout("hung case")}
        original = driver._open

        def open_page(fields):
            if fields["page"] == "index.html" and driver.restarts:
                raise capture.DriverTimeout("recovery load timed out")
            return original(fields)

        driver._open = open_page
        cli = matrix.Cli(self)
        code, _, out = cli.run(driver)
        output, sidecar = cli.load(out)
        self.assertEqual(1, code)
        self.assertEqual({"FAIL"}, {r["result"] for r in output["results"] if r["surface"] == "UI-001"})
        self.assertEqual({"PASS"}, {r["result"] for r in output["results"] if r["surface"] == "UI-002"})
        self.assertIn("recovery page did not open", sidecar["cases"][1]["reasons"][0])

    def test_four_workers_keep_slow_page_rejection_and_deterministic_order(self):
        def configure(driver):
            for state in ("ready", "loading", "empty"):
                for target in ("390", "1200"):
                    driver.overrides[("UI-001", state, target)] = {"raise": capture.DriverTimeout("slow page")}

        fleet = workers.Fleet(self, configure)
        with mock.patch.object(capture, "MAX_RESTARTS", 1):
            code, _, first = fleet.go("--workers", "4", out="first")
            second_code, _, second = fleet.go("--workers", "4", out="second")
        self.assertEqual((1, 1), (code, second_code))
        one, two = (workers.load(path) for path in (first, second))
        for output, sidecar in (one, two):
            self.assertEqual({"PASS"}, {r["result"] for r in output["results"] if r["surface"] == "UI-002"})
            self.assertNotIn("PASS", {r["result"] for r in output["results"] if r["surface"] == "UI-001"})
            self.assertEqual({"PASS"}, {r["result"] for r in sidecar["interactions"] if r["page"] == "details.html"})
        for key in ("results", "interactions", "navigation"):
            self.assertEqual(one[0][key], two[0][key])


if __name__ == "__main__":
    unittest.main()

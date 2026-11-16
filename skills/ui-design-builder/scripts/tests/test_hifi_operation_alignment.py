"""PRD operations retain observable proof when HiFi accepts more product forms."""
import copy
import json
import re
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_ui_design_contract as checker
import hifi_matrix_capture as capture
import hifi_review_fixture
from hifi_reviewer import product_control_findings
import test_hifi_matrix_capture as matrix_tests
import test_ui_design_contract as contract_tests
from operation_coverage import hifi_coverage_findings
from test_operation_coverage import prd


def write_manifest(path, manifest):
    html = path.read_text(encoding="utf-8")
    path.write_text(checker.HIFI_MANIFEST_RE.sub(
        lambda _: '<script id="ui-hifi-manifest" type="application/json">'
        + json.dumps(manifest) + '</script>', html), encoding="utf-8")


def passive_component_specs(html, page, removed):
    """Remove retired control specimens and show the actual read-only status component."""
    classes = {"next": "product-link", "refresh": "product-button", "filter": "product-input", "view": "product-select"}
    def edit(match):
        article = match.group()
        if f'data-source-page="{page}"' not in article:
            return article
        if 'data-hifi-spec="component"' in article and any(f'data-source=".{classes[c]}"' in article for c in removed):
            return ''
        if 'data-hifi-spec="pattern"' in article:
            component = article.replace('data-hifi-spec="pattern"', 'data-hifi-spec="component"')
            component = component.replace('data-name="Feedback"', 'data-name="Status component"')
            return component.replace('data-shared-group="feedback"', 'data-shared-group="status"') + article
        return article
    return re.sub(r'<article\b[^>]*data-hifi-spec="[^"]+"[^>]*>[\s\S]*?</article>', edit, html)


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

    def test_instance_count_is_optional_but_must_be_a_positive_integer(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, manifest, _ = contract_tests.materialize_hifi_bundle(Path(temporary))
            for count, passes in ((3, True), (0, False), (True, False), ("3", False)):
                output = contract_tests.bundle_output(manifest)
                output["interactions"][0]["observed"] = {"instances": count}
                self.assertEqual(passes, not checker._bundle_transcript_findings(output, manifest))

    def test_opener_observations_are_an_ordered_list_of_distinct_panel_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, manifest, _ = contract_tests.materialize_hifi_bundle(Path(temporary))
            for panels, passes in ((["outer", "inner"], True), (["outer", "outer"], False),
                                   ([{}], False), ("outer", False), ([""], False)):
                output = contract_tests.bundle_output(manifest)
                output["interactions"][0]["observed"] = {"openers": panels}
                self.assertEqual(passes, not checker._bundle_transcript_findings(output, manifest))


class TerminalSurfaceTests(unittest.TestCase):
    def test_one_or_both_control_lists_may_be_empty_but_unwired_dom_still_fails(self):
        for empty in (("navigation",), ("controls",), ("navigation", "controls")):
            with self.subTest(empty=empty), tempfile.TemporaryDirectory() as temporary:
                path, manifest, scope = contract_tests.materialize_hifi_bundle(Path(temporary))
                row = manifest["surfaces"][1]
                removed = {control for key in empty for control in row[key]}
                for key in empty:
                    row[key] = []
                manifest["interactions"] = [a for a in manifest["interactions"]
                    if not (a["source"]["surface"] == row["id"] and a["control"] in removed)]
                child = path.parent / "details.html"
                original = child.read_text(encoding="utf-8")
                cleaned = original
                for control in removed:
                    cleaned = re.sub(r'<(a|button|select)\b[^>]*data-(?:navigation|control)-id="'
                        + control + r'"[^>]*>[\s\S]*?</\1>', '', cleaned)
                    cleaned = re.sub(r'<input\b[^>]*data-control-id="'+control+r'"[^>]*>', '', cleaned)
                entry_original = path.read_text(encoding="utf-8")
                for html, passes in ((cleaned, True), (original, False)):
                    child.write_text(html, encoding="utf-8")
                    manifest["pages"][0]["sha256"] = capture.sha256_bytes(child.read_bytes())
                    entry = passive_component_specs(entry_original, "details.html", removed) if passes else entry_original
                    path.write_text(entry, encoding="utf-8")
                    write_manifest(path, manifest)
                    findings = []
                    checker._validate_hifi_surface(path, findings, scope)
                    self.assertEqual(passes, not findings, findings)
                    if not passes:
                        self.assertIn("interactions must cover", "\n".join(findings))

    def test_a_whole_package_can_have_no_interactions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, manifest, scope = contract_tests.materialize_hifi_bundle(root)
            # Retain only the entry surface and its reviewer controls.
            manifest.update(surfaces=manifest["surfaces"][:1], pages=[], interactions=[])
            manifest["surfaces"][0].update(navigation=[], controls=[])
            html = path.read_text(encoding="utf-8")
            html = re.sub(r'<(a|button|select)\b[^>]*data-(?:navigation|control)-id="[^"]+"[^>]*>[\s\S]*?</\1>', '', html)
            html = re.sub(r'<input\b[^>]*data-control-id="[^"]+"[^>]*>', '', html)
            html = re.sub(r'<!-- reviewer:start -->[\s\S]*?<!-- reviewer:end -->', lambda _:
                '<!-- reviewer:start -->' + hifi_review_fixture.shell(manifest, component_types=()) + '<!-- reviewer:end -->', html)
            html = passive_component_specs(html, "index.html", set())
            path.write_text(html, encoding="utf-8")
            write_manifest(path, manifest)
            findings = []
            checker._validate_hifi_surface(path, findings, {"surfaces": scope["surfaces"][:1]})
            self.assertEqual([], findings)
            self.assertEqual([], checker._bundle_transcript_findings(contract_tests.bundle_output(manifest), manifest))


class OpenerContractTests(unittest.TestCase):
    def test_disclosures_keep_the_native_live_same_surface_panel_rules(self):
        good = ('<main data-ui-surface="UI-001"><button data-product-disclosure aria-controls="panel" '
                'aria-expanded="false">Open</button><div id="panel" hidden>Contents</div></main>')
        self.assertEqual([], product_control_findings({"index.html": good}))
        for bad in (good.replace('<button ', '<div ').replace('</button>', '</div>'),
                    good.replace('aria-expanded="false"', ''),
                    good.replace('id="panel"', 'id="other"'),
                    good.replace('<div id="panel"', '<template id="panel"').replace('Contents</div>', 'Contents</template>'),
                    good.replace('<button ', '<button id="panel" '),
                    good.replace('data-ui-surface="UI-001"', 'data-reviewer="UI-001"'),
                    good.replace('<div id="panel"', '</main><main data-ui-surface="UI-002"><div id="panel"')):
            self.assertTrue(product_control_findings({"index.html": bad}), bad)

    def test_openers_need_no_operation_but_unmarked_buttons_still_do(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, _, scope = contract_tests.materialize_hifi_bundle(Path(temporary))
            original = path.read_text(encoding="utf-8")
            for marker, passes in (('data-product-disclosure aria-controls="panel" aria-expanded="false"', True), ('', False)):
                path.write_text(original.replace('</main>', '<button class="product-button" data-specimen-variant="default" '
                    'data-specimen-state="default" '+marker+'>Open</button><div id="panel" hidden>Product content</div></main>', 1), encoding="utf-8")
                findings = []
                checker._validate_hifi_surface(path, findings, scope)
                self.assertEqual(passes, not findings, findings)


class SupportingFieldTests(unittest.TestCase):
    def test_supporting_field_needs_a_real_control_in_its_own_surface(self):
        for attribute, passes in (('data-control-for="refresh"', True),
                                  ('data-control-for="missing"', False), ('', False)):
            with self.subTest(attribute=attribute), tempfile.TemporaryDirectory() as temporary:
                path, _, scope = contract_tests.materialize_hifi_bundle(Path(temporary))
                # Exercise an additional supporting field without declaring an operation.
                html = path.read_text(encoding="utf-8").replace('</main>', '<input class="product-input" '
                    'data-specimen-variant="default" data-specimen-state="default" '+attribute+' value="Draft"></main>', 1)
                path.write_text(html, encoding="utf-8")
                findings = []
                checker._validate_hifi_surface(path, findings, scope)
                self.assertEqual(passes, not findings, findings)

    def test_other_surface_or_non_field_cannot_use_supporting_attribute(self):
        for html in ('<main data-ui-surface="UI-001"><input data-control-for="save"></main>'
                     '<main data-ui-surface="UI-002"><button data-control-id="save">Save</button></main>',
                     '<main data-ui-surface="UI-001"><button data-control-for="save">Unbound</button>'
                     '<button data-control-id="save">Save</button></main>'):
            parser = checker._HiFiProductControls()
            parser.feed(html)
            parser.close()
            self.assertTrue(parser.errors)


class NotApplicableStateTests(unittest.TestCase):
    def test_na_state_needs_no_product_marker_or_case_but_real_state_does(self):
        for state, passes in (("permission:n/a", True), ("permission", False)):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temporary:
                path, manifest, scope = contract_tests.materialize_hifi_bundle(Path(temporary))
                manifest["surfaces"][0]["states"].append(state)
                write_manifest(path, manifest)
                html = re.sub(r'<!-- reviewer:start -->[\s\S]*?<!-- reviewer:end -->',
                    lambda _: '<!-- reviewer:start -->' + hifi_review_fixture.shell(manifest) + '<!-- reviewer:end -->',
                    path.read_text(encoding="utf-8"))
                path.write_text(html, encoding="utf-8")
                findings = []
                checker._validate_hifi_surface(path, findings, scope)
                self.assertEqual(passes, not findings, findings)
                cases = checker._evidence_matrix(scope)["cases"]
                self.assertEqual(passes, not any(row["state"] == state for row in cases))


class CrossPageStateTests(unittest.TestCase):
    def test_cross_page_state_requires_every_anchor_to_name_the_exact_state(self):
        for href, tag, passes in (("details.html#hifi-state=UI-002/updated", "a", True),
                                  ("details.html", "a", False),
                                  ("details.html#hifi-state=UI-002/ready", "a", False),
                                  ("details.html#hifi-state=UI-002/updated", "button", False)):
            with self.subTest(href=href, tag=tag), tempfile.TemporaryDirectory() as temporary:
                path, manifest, scope = contract_tests.materialize_hifi_bundle(Path(temporary))
                manifest["interactions"][0].update(kind="state", destination={"surface": "UI-002", "state": "updated"})
                write_manifest(path, manifest)
                html = path.read_text(encoding="utf-8").replace('data-navigation-id="next" href="details.html"',
                    f'data-navigation-id="next" href="{href}"')
                if tag == "button":
                    html = html.replace('<a class="product-link"', '<button class="product-link"').replace('</a>', '</button>')
                path.write_text(html, encoding="utf-8")
                findings = []
                checker._validate_hifi_surface(path, findings, scope)
                self.assertEqual(passes, not findings, findings)

    def test_a_second_wrong_instance_cannot_hide_behind_a_valid_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            path, manifest, scope = contract_tests.materialize_hifi_bundle(Path(temporary))
            manifest["interactions"][0].update(kind="state", destination={"surface": "UI-002", "state": "updated"})
            write_manifest(path, manifest)
            html = path.read_text(encoding="utf-8").replace('data-navigation-id="next" href="details.html"',
                'data-navigation-id="next" href="details.html#hifi-state=UI-002/updated"')
            html = html.replace('</main>', '<a class="product-link" data-specimen-variant="default" '
                'data-specimen-state="default" data-navigation-id="next" href="details.html">Wrong row</a></main>')
            path.write_text(html, encoding="utf-8")
            findings = []
            checker._validate_hifi_surface(path, findings, scope)
            self.assertIn("cross-page state control", "\n".join(findings))


class OperationBrowserTests(unittest.TestCase):
    playwright = matrix_tests.RealBrowserTests.playwright
    run_main = matrix_tests.RealBrowserTests.run_main

    def driver(self, extra="", edit=None):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        scratch = self.enterContext(tempfile.TemporaryDirectory())
        package = matrix_tests.build_interactions_package(root, details_extra=extra, page_edit=edit)
        driver = capture.NodeDriver(shutil.which("node"), self.playwright(), capture.read_package(package).files, scratch)
        self.addCleanup(driver.stop)
        driver.start()
        return driver

    def attempt(self, driver, control="save", kind="feedback", destination=None, page="details.html", destination_page=None, trigger="click", **extra):
        driver.call("open", page=page, timeoutMs=2000)
        return driver.call("interact", page=page, interaction="operation", surface="UI-002", state="ready",
                           target="390", control=control, kind=kind,
                           destination=destination or {"surface": "UI-002", "state": "ready"},
                           destinationPage=destination_page or page, trigger=trigger, timeoutMs=2000, **extra)

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

    def test_openers_reveal_menu_and_nested_disclosures_in_order(self):
        save = '<button data-control-id="save" onclick="this.textContent += \' saved\'">Save</button>'
        menu = ('<button data-product-menu aria-controls="menu" aria-expanded="false">Actions</button>'
                '<div id="menu" hidden>' + save + '</div>')
        nested = ('<button data-product-disclosure aria-controls="outer" aria-expanded="false">Editor</button>'
                  '<div id="outer" hidden><button data-product-disclosure aria-controls="inner" '
                  'aria-expanded="false">Details</button><div id="inner" hidden>' + save + '</div></div>')
        for markup, openers in ((menu, ["menu"]), (nested, ["outer", "inner"])):
            driver = self.driver(markup)
            for trigger in ("click", "keyboard"):
                reply = self.attempt(driver, trigger=trigger)
                self.assertEqual([], reply["result"]["problems"], reply)
                self.assertTrue(reply["result"]["focusCorrect"], reply)
                self.assertEqual(openers, reply["result"]["observed"]["openers"])
            driver.stop()

    def test_unreachable_controls_and_opener_only_feedback_still_fail(self):
        for markup, reason in (('<div hidden><button data-control-id="save">Save</button></div>', 'missing or hidden'),
                               ('<button data-product-menu aria-controls="menu" aria-expanded="false">Actions</button>'
                                '<div id="menu" hidden><button data-control-id="save">Save</button></div>', 'feedback did not change')):
            driver = self.driver(markup)
            reply = self.attempt(driver)
            self.assertIn(reason, "\n".join(reply["result"]["problems"]), reply)
            driver.stop()

    def test_opener_exemption_does_not_allow_unrelated_product_focus(self):
        driver = self.driver('<button data-product-disclosure aria-controls="editor" aria-expanded="false">Editor</button>'
            '<div id="editor" hidden><button data-control-id="save" '
            'onclick="this.textContent += \' saved\'; document.querySelector(\'[data-control-id=thief]\').focus()">Save</button>'
            '<button data-control-id="thief">Other</button></div>')
        reply = self.attempt(driver)
        self.assertEqual([], reply["result"]["problems"], reply)
        self.assertFalse(reply["result"]["focusCorrect"], reply)

    def test_cross_page_state_observes_the_arrival_page_and_state(self):
        actions = copy.deepcopy(matrix_tests.INTERACTIONS)
        actions[0].update(kind="state", destination={"surface": "UI-002", "state": "error"})
        for fragment, passes in (("UI-002/error", True), ("UI-002/ready", False)):
            with self.subTest(fragment=fragment), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                package = matrix_tests.build_interactions_package(root, interactions=actions, page_edit=lambda html:
                    html.replace('href="details.html"', 'href="details.html#hifi-state=' + fragment + '"'))
                code, text = self.run_main(self.playwright(), root, package, "--out", "evidence", "--only", "UI-001")
                self.assertEqual(0 if passes else 1, code, text)
                output = json.loads((root / "evidence/ui-output.json").read_text(encoding="utf-8"))
                self.assertEqual({"PASS"} if passes else {"FAIL"}, {r["result"] for r in output["interactions"]})
                if passes:
                    self.assertEqual(4, len(output["navigation"]))
                    expected, navigation = checker._interaction_expectations(capture.read_package(package).manifest)
                    self.assertEqual(expected[:4], [{k: v for k, v in r.items() if k != "observed"} for r in output["interactions"]])
                    self.assertEqual(navigation[:4], output["navigation"])

    def test_repeated_rows_activate_the_first_visible_instance(self):
        for wrong, passes in ((False, True), (True, False)):
            with self.subTest(wrong=wrong):
                extra = ''.join('<a data-navigation-id="rows" href="' +
                    ('details.html' if wrong and index == 2 else 'index.html') + '">Row</a>' for index in range(3))
                driver = self.driver('<a data-navigation-id="rows" href="index.html" hidden>Hidden row</a>' + extra)
                reply = self.attempt(driver, control="rows", kind="navigate",
                                     destination={"surface": "UI-001", "state": "ready"}, destination_page="index.html")
                self.assertEqual(passes, not reply["result"]["problems"], reply)
                self.assertEqual(3, reply["result"]["observed"]["instances"])
                if passes:
                    self.assertTrue(reply["result"]["focusCorrect"])
                    self.assertEqual("index.html", reply["result"]["arrivedTo"])
                driver.stop()


if __name__ == "__main__":
    unittest.main()

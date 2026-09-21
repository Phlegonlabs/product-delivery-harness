"""Reviewer UI negative cases; fixtures do not prove native or service E2E."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from test_ui_design_contract import bundle_output, checker, materialize_hifi_bundle
from hifi_review_fixture import _source_html, add_shell, observations
from hifi_reviewer import _host_media_reflow, _target_widths, reviewer_contract, reviewer_evidence_findings


class HiFiReviewerTests(unittest.TestCase):
    def test_retained_browser_example_has_current_bundle_and_reviewer_sources(self):
        path = Path(__file__).parent / "fixtures/interactive-hifi/index.html"
        for page in path.parent.glob("*.html"):
            self.assertNotIn(b"\r\n", page.read_bytes(), "byte-bound fixture must retain LF across checkouts")
        problems = []
        checker._validate_hifi_surface(path, problems)
        self.assertEqual([], problems)
        checker._validate_hifi_surface(path, problems, require_connected=True)
        self.assertTrue(any("current version-2 reviewer shell" in item for item in problems), problems)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path, self.manifest, self.scope = materialize_hifi_bundle(Path(self.directory.name))
        self.documents = checker._hifi_bundle_documents(self.path, self.path.read_text(), self.manifest)

    def test_complete_source_bound_reviewer_contract(self):
        errors, expected = reviewer_contract(self.documents, self.manifest)
        self.assertEqual([], errors)
        self.assertEqual([], reviewer_evidence_findings(observations(self.manifest), expected))

    def test_sidebar_self_link_requires_its_own_current_page_marker(self):
        for page in self.documents:
            marked = f'<a href="{page}" aria-current="page">'
            self.assertEqual(1, self.documents[page].count(marked))
            for value in (None, "", "false", "true", "step"):
                with self.subTest(page=page, value=value):
                    docs = dict(self.documents)
                    marker = "" if value is None else f' aria-current="{value}"'
                    docs[page] = docs[page].replace(marked, f'<a href="{page}"{marker}>', 1)
                    errors, _ = reviewer_contract(docs, self.manifest)
                    self.assertIn(f"HiFi {page} sidebar must mark its current product screen", errors)

    def test_current_page_marker_outside_self_link_cannot_substitute(self):
        for page in self.documents:
            marked = f'<a href="{page}" aria-current="page">'
            for location in ("parent", "other-link", "outside-nav"):
                with self.subTest(page=page, location=location):
                    docs = dict(self.documents)
                    html = docs[page].replace(marked, f'<a href="{page}">', 1)
                    if location == "parent":
                        html = html.replace('<nav data-hifi-page-nav ', '<nav data-hifi-page-nav aria-current="page" ', 1)
                    elif location == "other-link":
                        other = next(name for name in self.documents if name != page)
                        html = html.replace(f'<a href="{other}">', f'<a href="{other}" aria-current="page">', 1)
                    else:
                        html = html.replace('</nav>', f'</nav><a href="{page}" aria-current="page">Outside</a>', 1)
                    docs[page] = html
                    errors, _ = reviewer_contract(docs, self.manifest)
                    self.assertIn(f"HiFi {page} sidebar must mark its current product screen", errors)

    def test_nested_sidebar_self_link_keeps_its_current_page_marker(self):
        docs = dict(self.documents)
        for page, html in docs.items():
            start = html.index('<nav data-hifi-page-nav ')
            end = html.index('</nav>', start)
            nav = html[start:end].replace('<a ', '<li><a ').replace('</a>', '</a></li>')
            docs[page] = html[:start] + nav.replace('>', '><ul>', 1) + '</ul>' + html[end:]
        self.assertEqual([], reviewer_contract(docs, self.manifest)[0])

    def test_reviewer_dom_requires_exact_container_and_real_responsive_controls(self):
        for old, new, message in (
            ('<div data-hifi-canvas ', '<div data-hifi-canvas-disabled ', "exact-width product container"),
            ('data-hifi-target-control="1200"', 'data-hifi-target-control="777"', "responsive target controls"),
            ('@container (max-width:779px)', '@media (max-width:779px)', "container queries"),
            ('container-type:inline-size', 'container-type:normal', "inline-size containment"),
            ('data-hifi-target-control="390" aria-pressed="true"', 'data-hifi-target-control="390" aria-pressed="false"', "one selected responsive target control"),
        ):
            with self.subTest(message=message):
                docs = dict(self.documents)
                docs["index.html"] = docs["index.html"].replace(old, new, 1)
                errors, _ = reviewer_contract(docs, self.manifest)
                self.assertTrue(any(message in error for error in errors), errors)

    def test_named_size_class_targets_use_explicit_width_map(self):
        manifest = copy.deepcopy(self.manifest)
        for row in manifest["surfaces"]:
            row["responsive"] = {"kind": "sizeClasses", "targets": ["compact", "regular"]}
        source_rows = {row["page"]: row for row in manifest["surfaces"]}
        docs = {page: add_shell(_source_html(row), manifest, page) for page, row in source_rows.items()}
        for page, html in list(docs.items()):
            html = html.replace('data-hifi-target="compact"', 'data-hifi-target="compact" data-hifi-target-widths="{&quot;compact&quot;:390,&quot;regular&quot;:1200}"')
            html = html.replace('[data-hifi-canvas][data-hifi-target="390"]', '[data-hifi-canvas][data-hifi-target="compact"]')
            html = html.replace('[data-hifi-canvas][data-hifi-target="1200"]', '[data-hifi-canvas][data-hifi-target="regular"]')
            docs[page] = html
        errors, _ = reviewer_contract(docs, manifest)
        self.assertEqual([], errors)
        broken = {page: html.replace(' data-hifi-target-widths="{&quot;compact&quot;:390,&quot;regular&quot;:1200}"', '') for page, html in docs.items()}
        errors, _ = reviewer_contract(broken, manifest)
        self.assertTrue(any("non-numeric responsive targets" in error for error in errors), errors)

    def test_hybrid_bundle_keeps_page_target_families_separate(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["surfaces"][0]["responsive"] = {"kind": "viewports", "targets": [390, 768, 1200]}
        manifest["surfaces"][1]["responsive"] = {"kind": "sizeClasses", "targets": ["compact", "regular"]}
        source_rows = {row["page"]: row for row in manifest["surfaces"]}
        docs = {page: add_shell(_source_html(row), manifest, page) for page, row in source_rows.items()}
        native = docs["details.html"].replace(
            'data-hifi-target="compact"',
            'data-hifi-target="compact" data-hifi-target-widths="{&quot;compact&quot;:390,&quot;regular&quot;:768}"',
            1,
        ).replace(
            "</style>",
            '[data-hifi-canvas][data-hifi-target="compact"]{width:390px}[data-hifi-canvas][data-hifi-target="regular"]{width:768px}</style>',
            1,
        )
        docs["details.html"] = native
        errors, expected = reviewer_contract(docs, manifest)
        self.assertEqual([], errors)
        self.assertEqual({"390", "768", "1200"}, {row["target"] for row in expected["views"] if row["from"] == "index.html"})
        self.assertEqual({"compact", "regular"}, {row["target"] for row in expected["views"] if row["from"] == "details.html"})
        destination_rows = [row for row in expected["navigation"] if row["from"] == "index.html" and row["to"] == "details.html"]
        self.assertEqual({"compact"}, {row["destinationTarget"] for row in destination_rows if row["target"] == "390"})

    def test_named_width_map_rejects_nonfinite_and_oversized_values(self):
        for value in ("NaN", "Infinity", "1e1000", "1000001"):
            with self.subTest(value=value):
                widths, error = _target_widths(
                    {"data-hifi-target-widths": '{"compact":' + value + ',"regular":768}'},
                    ["compact", "regular"],
                )
                self.assertIsNone(widths)
                self.assertIn("positive numbers", error)

    def test_host_media_reflow_rejects_modern_dimension_syntax(self):
        for condition in ("(width < 768px)", "(768px <= width)", "(width:768px)"):
            with self.subTest(condition=condition):
                self.assertTrue(_host_media_reflow("@media " + condition + " { .product { color: red; } }"))

    def test_width_rules_allow_css_whitespace_and_preference_media(self):
        docs = {
            page: html.replace(
                '[data-hifi-canvas][data-hifi-target="390"]{width:390px}',
                '[data-hifi-canvas] [data-hifi-target = \'390\'] { width: 390px; }',
            ).replace(
                '</style>',
                '@media (prefers-reduced-motion: reduce){:root{scroll-behavior:auto}} </style>',
                1,
            )
            for page, html in self.documents.items()
        }
        self.assertEqual([], reviewer_contract(docs, self.manifest)[0])

    def test_n_a_state_coverage_is_explanatory_not_a_fake_destination(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["surfaces"][0]["states"] = ["loading:n/a", "updated"]
        source_rows = {row["page"]: row for row in manifest["surfaces"]}
        docs = {page: add_shell(_source_html(row), manifest, page) for page, row in source_rows.items()}
        self.assertEqual([], reviewer_contract(docs, manifest)[0])

    def test_malformed_reviewer_evidence_rows_are_rejected_without_crashing(self):
        _, expected = reviewer_contract(self.documents, self.manifest)
        actual = observations(self.manifest)
        actual["retention"][0] = None
        self.assertTrue(reviewer_evidence_findings(actual, expected))
        actual = observations(self.manifest)
        actual["specimens"][0] = {"sourcePage": "index.html"}
        self.assertTrue(reviewer_evidence_findings(actual, expected))

    def test_typed_invalid_specimen_values_are_rejected_before_shared_grouping(self):
        _, expected = reviewer_contract(self.documents, self.manifest)
        for invalid in ([], {}, None):
            with self.subTest(invalid=invalid):
                actual = observations(self.manifest)
                row = actual["specimens"][0]
                row["sourceValue"] = invalid
                row["specimenValue"] = invalid
                row["displayValue"] = invalid
                findings = reviewer_evidence_findings(actual, expected)
                self.assertTrue(findings)

    def test_retention_rows_have_a_closed_key_set(self):
        _, expected = reviewer_contract(self.documents, self.manifest)
        actual = observations(self.manifest)
        actual["retention"][0]["extra"] = "accepted"
        self.assertTrue(reviewer_evidence_findings(actual, expected))

    def test_invalid_shared_group_identity_does_not_reach_aggregation(self):
        _, expected = reviewer_contract(self.documents, self.manifest)
        for invalid in (["bad"], {"bad": 1}, [], {}, None, 1, True):
            with self.subTest(invalid=invalid):
                actual = observations(self.manifest)
                actual["specimens"][0]["sharedGroup"] = invalid
                self.assertTrue(reviewer_evidence_findings(actual, expected))

    def test_text_input_cannot_impersonate_checked_selection(self):
        for attributes in ('aria-checked="true"', 'aria-selected="true" role="option"', 'checked role="checkbox"'):
            with self.subTest(attributes=attributes):
                docs = {page: html.replace('data-retention-input', 'type="text" data-retention-input data-retention-selected ' + attributes)
                        .replace('<select class="product-select" data-retention-selected', '<select class="product-select"')
                        for page, html in self.documents.items()}
                errors, expected = reviewer_contract(docs, self.manifest)
                self.assertEqual([], errors)
                self.assertTrue(all(row["selectedValueBefore"] == "ready" for row in expected["retention"]))

    def test_marked_product_anchor_requires_specimen_even_without_declared_anchor(self):
        component_types = ("button", "input", "select")
        docs = {row["page"]: add_shell(_source_html(row, component_types).replace(
            '</main>', '<a class="product-link" data-navigation-id="home" href="index.html">Home</a></main>'),
            self.manifest, row["page"], component_types) for row in self.manifest["surfaces"]}
        errors, _ = reviewer_contract(docs, self.manifest)
        self.assertTrue(any("source-bound component specimen" in error for error in errors), errors)

    def test_fresh_reviewer_requires_every_bound_product_variant_and_state_specimen(self):
        original = self.path.read_text(encoding="utf-8")
        self.assertIn("</main></div></main>", original)
        mutated = original.replace(
            "</main></div></main>",
            '<button type="button" class="product-danger" data-control-id="refresh" '
            'data-specimen-variant="danger" data-specimen-state="error">Delete</button>'
            "</main></div></main>",
            1,
        ).replace(
            "</style>",
            ".product-danger{background:#900;color:white}</style>",
            1,
        )
        self.path.write_text(mutated, encoding="utf-8")
        problems = []
        checker._validate_hifi_surface(self.path, problems, self.scope, require_connected=True)
        self.assertTrue(any("specimen" in item.lower() or "source-bound" in item.lower() for item in problems), problems)

    def test_retention_marker_on_text_input_cannot_override_real_select(self):
        original = self.path.read_text(encoding="utf-8")
        mutated = original.replace(
            'data-retention-input data-specimen-variant="default"',
            'data-retention-input data-retention-selected data-specimen-variant="default"',
            1,
        ).replace(
            '<select class="product-select" data-retention-selected',
            '<select class="product-select"',
            1,
        )
        self.path.write_text(mutated, encoding="utf-8")
        documents = checker._hifi_bundle_documents(self.path, mutated, self.manifest)
        errors, expected = reviewer_contract(documents, self.manifest)
        self.assertEqual([], errors)
        self.assertTrue(expected["retention"][0]["selectedApplicable"])
        self.assertEqual("ready", expected["retention"][0]["selectedValueBefore"])
        problems = []
        checker._validate_hifi_surface(self.path, problems, self.scope, require_connected=True)
        self.assertEqual([], problems)

    def test_retention_presence_is_distinct_from_an_absent_control(self):
        actual = observations(self.manifest, component_types=("button",))
        _, expected = reviewer_contract(
            {page: add_shell(_source_html(row, component_types=("button",)), self.manifest, page, ("button",))
             for page, row in {item["page"]: item for item in self.manifest["surfaces"]}.items()},
            self.manifest,
        )
        self.assertFalse(expected["retention"][0]["inputApplicable"])
        self.assertFalse(expected["retention"][0]["selectedApplicable"])
        self.assertEqual([], reviewer_evidence_findings(actual, expected))

        applicable = observations(self.manifest)
        applicable["retention"][0]["inputValueBefore"] = None
        applicable["retention"][0]["inputValueAfter"] = None
        self.assertTrue(reviewer_evidence_findings(applicable, self._expected_reviewer()))

    def _expected_reviewer(self):
        return reviewer_contract(self.documents, self.manifest)[1]

    def test_component_specimens_must_be_real_elements_with_visible_markers(self):
        docs = dict(self.documents)
        docs["index.html"] = docs["index.html"].replace('data-specimen-element="button"', 'data-specimen-element="div"', 1)
        errors, _ = reviewer_contract(docs, self.manifest)
        self.assertTrue(any("real styled element" in error for error in errors), errors)

    def test_shared_group_drift_does_not_waive_page_evidence(self):
        _, expected = reviewer_contract(self.documents, self.manifest)
        actual = observations(self.manifest)
        group = [row for row in actual["specimens"] if row["sharedGroup"] == "primary-button"]
        self.assertGreaterEqual(len(group), 2)
        for key in ("sourceValue", "specimenValue", "displayValue"):
            group[-1][key] = "#ff0000"
        findings = reviewer_evidence_findings(actual, expected)
        self.assertTrue(any("shared specimen group" in item for item in findings), findings)

        actual = observations(self.manifest)
        actual["specimens"] = [row for row in actual["specimens"] if row["sourcePage"] != "details.html"]
        findings = reviewer_evidence_findings(actual, expected)
        self.assertTrue(any("specimen coverage is incomplete" in item for item in findings), findings)

    def test_canvas_and_retention_observations_use_measured_values(self):
        _, expected = reviewer_contract(self.documents, self.manifest)
        for change in ("width", "surface", "target", "input", "selected", "missing"):
            with self.subTest(change=change):
                actual = observations(self.manifest)
                if change == "width":
                    actual["viewport"][0]["measuredProductWidth"] = 320
                elif change == "surface":
                    actual["viewport"][0]["visibleSurfaces"] = ["unrelated"]
                elif change == "target":
                    actual["retention"][0]["selectedTargetAfter"] = "1200"
                elif change == "input":
                    actual["retention"][0]["inputValueAfter"] = "changed"
                elif change == "selected":
                    actual["retention"][0]["selectedValueAfter"] = "changed"
                else:
                    actual.pop("retention")
                self.assertTrue(reviewer_evidence_findings(actual, expected))

    def test_evidence_parser_rejects_casing_bypass_and_empty_surfaces(self):
        original = self.path.read_text(encoding="utf-8")
        for change in ("uppercase", "empty"):
            with self.subTest(change=change):
                html = original.replace("data-hifi-reviewer-shell", "DATA-HIFI-REVIEWER-SHELL")
                if change == "empty":
                    empty = dict(self.manifest, surfaces=[])
                    html = checker.HIFI_MANIFEST_RE.sub(lambda _: '<script id="ui-hifi-manifest" type="application/json">' + json.dumps(empty) + '</script>', html)
                self.path.write_text(html, encoding="utf-8")
                subject = {"path": "index.html", "sha256": hashlib.sha256(self.path.read_bytes()).hexdigest()}
                matrix = {"cases": [{"surface": row["id"], "state": state, "target": str(target)} for row in self.manifest["surfaces"] for state in row["states"] for target in row["responsive"]["targets"]]}
                results = [dict(case, result="PASS") for case in matrix["cases"]]
                output = dict(bundle_output(self.manifest), schema="ui-output/2", check="hifi-browser", subject=subject, matrix=matrix, results=results)
                output.pop("reviewer")
                output_path = self.path.parent / "output.json"
                output_path.write_text(json.dumps(output), encoding="utf-8")
                evidence = {"schema": "ui-evidence/2", "check": "hifi-browser", "result": "PASS", "reviewedArtifact": subject,
                            "attestation": "human-attested", "owner": "Synthetic fixture owner", "receipt": {
                                "tool": "playwright", "method": "sandboxed-offline-browser", "matrix": matrix, "results": results,
                                "outputArtifact": {"path": "output.json", "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest()}, "executedAt": "2020-01-01T00:00:00Z"}}
                evidence_path = self.path.parent / "evidence.json"
                evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
                problems = []
                checker._resolve_evidence("PASS — evidence=evidence.json @ sha256:" + hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
                                          repo_root=self.path.parent, label="HiFi surface check", problems=problems, expected_artifact="index.html", expected_matrix=matrix)
                self.assertTrue(problems)

    def test_child_values_and_originating_view_pages_are_required(self):
        _, expected = reviewer_contract(self.documents, self.manifest)
        actual = observations(self.manifest)
        child = next(row for row in actual["specimens"] if row["sourcePage"] == "details.html" and row["kind"] == "token")
        # Simulate the actual child measurement after a child style change.
        child["sourceValue"] = "#ff0000"
        self.assertTrue(reviewer_evidence_findings(actual, expected))
        actual = observations(self.manifest)
        actual["views"] = [row for row in actual["views"] if row["from"] == "index.html"]
        self.assertTrue(reviewer_evidence_findings(actual, expected))

    def test_missing_and_failed_recovery_observations_are_rejected(self):
        _, expected = reviewer_contract(self.documents, self.manifest)
        for case in ("unknown-hash", "back-from-overview", "back-from-design-tokens", "final-default-restoration"):
            for failure in ("missing", "blank-product", "panel-visible", "wrong-surface"):
                with self.subTest(case=case, failure=failure):
                    actual = observations(self.manifest)
                    row = next(row for row in actual["recovery"] if row["case"] == case)
                    if failure == "missing":
                        actual["recovery"].remove(row)
                    elif failure == "blank-product":
                        row["productVisible"] = False
                    elif failure == "panel-visible":
                        row["panelsHidden"] = False
                    else:
                        row["surfaces"] = ["unrelated"]
                    self.assertTrue(reviewer_evidence_findings(actual, expected))
    def test_missing_shell_is_historical_inspection_only(self):
        import re
        for name, text in self.documents.items():
            stripped = re.sub(r'<!-- reviewer:start -->[\s\S]*?<!-- reviewer:end -->', '', text)
            (self.path.parent / name).write_text(stripped, encoding="utf-8")
        child = self.path.parent / "details.html"
        self.manifest["pages"][0]["sha256"] = hashlib.sha256(child.read_bytes()).hexdigest()
        self.path.write_text(checker.HIFI_MANIFEST_RE.sub(lambda _: '<script id="ui-hifi-manifest" type="application/json">' + json.dumps(self.manifest) + '</script>', self.path.read_text()), encoding="utf-8")
        problems = []
        checker._validate_hifi_surface(self.path, problems, self.scope)
        self.assertEqual([], problems)
        checker._validate_hifi_surface(self.path, problems, self.scope, require_connected=True)
        self.assertTrue(any("reviewer aside" in item for item in problems), problems)

    def test_wrong_overview_and_untracked_tokens_fail(self):
        for old, new, message in (
            ('data-route="/home"', 'data-route="/wrong"', "Overview"),
            ('--ink:#243447', '--ink:#243447;--spacing:12px', "CSS custom properties"),
            ('data-hifi-panel="design-tokens" hidden', 'data-hifi-panel="design-tokens"', "initially hidden"),
            ('data-hifi-default-surface="UI-001"', 'data-hifi-default-surface="UI-002"', "first product"),
            ('data-hifi-spec="pattern"', 'data-hifi-spec="component"', "pattern specimens"),
        ):
            with self.subTest(message=message):
                docs = dict(self.documents)
                docs["index.html"] = docs["index.html"].replace(old, new)
                errors, _ = reviewer_contract(docs, self.manifest)
                self.assertTrue(any(message in error for error in errors), errors)

    def test_css_comments_and_strings_are_not_live_tokens(self):
        for css in ('/* --retired-token: #fff; */',
                    '.example::after{content:";--example: red;"}',
                    ".example::after{content:'/* --example: red; */'}"):
            with self.subTest(css=css):
                docs = dict(self.documents)
                docs["details.html"] = docs["details.html"].replace('</style>', css + '</style>', 1)
                self.assertEqual([], reviewer_contract(docs, self.manifest)[0])
        docs = dict(self.documents)
        docs["details.html"] = docs["details.html"].replace('--ink:', r'--\69 nk:')
        self.assertEqual([], reviewer_contract(docs, self.manifest)[0])

    def test_sidebar_cannot_supply_product_controls(self):
        docs = dict(self.documents)
        docs["index.html"] = docs["index.html"].replace(
            '<nav data-hifi-page-nav aria-label="Product screens">',
            '<nav data-hifi-page-nav aria-label="Product screens" data-navigation-id="fake">',
        )
        errors, _ = reviewer_contract(docs, self.manifest)
        self.assertTrue(any("cannot count as product controls" in error for error in errors))

    def test_stale_computed_values_and_fake_observations_fail(self):
        _, expected = reviewer_contract(self.documents, self.manifest)
        for change in ("value", "source", "keyboard", "navigation", "default", "extra"):
            with self.subTest(change=change):
                actual = copy.deepcopy(observations(self.manifest))
                if change == "value":
                    actual["specimens"][0]["displayValue"] = "wrong"
                elif change == "source":
                    actual["specimens"][0]["source"] = ".unrelated"
                elif change == "keyboard":
                    actual["views"] = [row for row in actual["views"] if row["trigger"] == "click"]
                elif change == "navigation":
                    actual["navigation"][0]["focusCorrect"] = False
                elif change == "default":
                    actual["defaultVisible"] = False
                else:
                    actual["approval"] = True
                self.assertTrue(reviewer_evidence_findings(actual, expected))


if __name__ == "__main__":
    unittest.main()

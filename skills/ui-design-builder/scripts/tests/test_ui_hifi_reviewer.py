"""Reviewer UI negative cases; fixtures do not prove native or service E2E."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from test_ui_design_contract import bundle_output, checker, materialize_hifi_bundle
from hifi_review_fixture import observations
from hifi_reviewer import reviewer_contract, reviewer_evidence_findings


class HiFiReviewerTests(unittest.TestCase):
    def test_retained_browser_example_has_current_bundle_and_reviewer_sources(self):
        path = Path(__file__).parent / "fixtures/interactive-hifi/index.html"
        for page in path.parent.glob("*.html"):
            self.assertNotIn(b"\r\n", page.read_bytes(), "byte-bound fixture must retain LF across checkouts")
        problems = []
        checker._validate_hifi_surface(path, problems, require_connected=True)
        self.assertEqual([], problems)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path, self.manifest, self.scope = materialize_hifi_bundle(Path(self.directory.name))
        self.documents = checker._hifi_bundle_documents(self.path, self.path.read_text(), self.manifest)

    def test_complete_source_bound_reviewer_contract(self):
        errors, expected = reviewer_contract(self.documents, self.manifest)
        self.assertEqual([], errors)
        self.assertEqual([], reviewer_evidence_findings(observations(self.manifest), expected))

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
        docs["index.html"] = docs["index.html"].replace('<nav data-hifi-page-nav>', '<nav data-hifi-page-nav data-navigation-id="fake">')
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

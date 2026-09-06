"""Direct tests for the wireframe HTML checker and the PRD UI contract parser."""

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

check_wireframe_html = importlib.import_module("check_wireframe_html")
prd_ui_contract = importlib.import_module("prd_ui_contract")


def wireframe_data(**overrides):
    data = {
        "product": "Test Product",
        "approvalStatus": "approved",
        "source": "PRD.md#UI-Surface-Contract",
        "screens": [
            {
                "id": "UI-001",
                "name": "Home",
                "route": "/home",
                "goal": "Show the account dashboard",
                "regions": [
                    {
                        "id": "R1",
                        "section": "Summary",
                        "purpose": "Show the account balance",
                        "priority": "primary",
                        "span": 6,
                        "elements": ["Balance card"],
                        "actions": ["Refresh"],
                    }
                ],
                "compactOrder": ["R1"],
                "states": [
                    {
                        "id": "ready",
                        "label": "Ready",
                        "treatments": {"R1": "Show the balance"},
                    }
                ],
            }
        ],
        "flows": [{"from": "UI-001", "trigger": "open", "to": "UI-001"}],
    }
    data.update(overrides)
    return data


def render_html(data):
    payload = json.dumps(data, ensure_ascii=False)
    return (
        "<!doctype html><html><head><title>Wireframes</title></head><body>"
        '<script id="wireframe-data" type="application/json">' + payload + "</script>"
        '<nav id="page-list">All pages</nav>'
        '<div id="state-controls">textContent</div>'
        '<section data-viewport="expanded"></section>'
        '<section data-viewport="compact"></section>'
        "</body></html>"
    )


def prd_markdown(route="/home", states="ready", surface_id="UI-001"):
    return (
        "# PRD\n\n"
        "<!-- ui-surface-contract:start -->\n"
        "## UI Surface Contract\n\n"
        f"### {surface_id} — Home\n\n"
        f"- `route`: {route}\n"
        f"- `states`: {states}\n"
        "<!-- ui-surface-contract:end -->\n"
    )


def validate_html(html, **kwargs):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "wireframes.html"
        path.write_text(html, encoding="utf-8")
        return check_wireframe_html.validate(path, **kwargs)


class WireframeHtmlCheckerTests(unittest.TestCase):
    def test_valid_projection_passes_strict_checks(self):
        self.assertEqual(
            validate_html(
                render_html(wireframe_data()),
                require_filled=True,
                require_approved=True,
            ),
            [],
        )

    def test_missing_data_block_is_reported(self):
        problems = validate_html("<html><body><p>no data block here</p></body></html>")
        self.assertTrue(any("missing wireframe-data" in p for p in problems))

    def test_external_resources_are_rejected(self):
        html = render_html(wireframe_data()).replace(
            "<title>Wireframes</title>",
            "<title>Wireframes</title>"
            '<link rel="stylesheet" href="theme.css">'
            '<img src="https://cdn.example.com/logo.png">',
        )
        problems = validate_html(html)
        self.assertTrue(
            any("must not contain <link> resources" in p for p in problems)
        )
        self.assertTrue(
            any("must not load external resources" in p for p in problems)
        )

    def test_css_import_is_rejected(self):
        html = render_html(wireframe_data()).replace(
            "<title>", "<style>@import url(more.css)</style><title>"
        )
        problems = validate_html(html)
        self.assertTrue(any("must not contain CSS @import" in p for p in problems))

    def test_draft_status_requires_the_approval_flag(self):
        data = wireframe_data()
        data["approvalStatus"] = "draft"
        self.assertEqual(validate_html(render_html(data)), [])
        problems = validate_html(render_html(data), require_approved=True)
        self.assertTrue(any("must be 'approved'" in p for p in problems))

    def test_unfilled_placeholders_only_flagged_when_required(self):
        data = wireframe_data()
        data["screens"][0]["goal"] = "Show the <placeholder> value"
        self.assertEqual(validate_html(render_html(data)), [])
        problems = validate_html(render_html(data), require_filled=True)
        self.assertTrue(any("unfilled" in p for p in problems))

    def test_region_contract_violations_are_localized(self):
        data = wireframe_data()
        data["screens"][0]["regions"][0]["priority"] = "mega"
        data["screens"][0]["regions"][0]["span"] = 13
        data["screens"][0]["compactOrder"] = []
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("regions[0].priority", joined)
        self.assertIn("regions[0].span", joined)
        self.assertIn("compactOrder", joined)

    def test_prd_join_passes_on_matching_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            html_path = Path(directory) / "wireframes.html"
            prd_path = Path(directory) / "PRD.md"
            html_path.write_text(render_html(wireframe_data()), encoding="utf-8")
            prd_path.write_text(prd_markdown(), encoding="utf-8")
            self.assertEqual(
                check_wireframe_html.validate(
                    html_path, require_approved=True, prd_path=prd_path
                ),
                [],
            )

    def test_prd_join_detects_route_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            html_path = Path(directory) / "wireframes.html"
            prd_path = Path(directory) / "PRD.md"
            html_path.write_text(render_html(wireframe_data()), encoding="utf-8")
            prd_path.write_text(prd_markdown(route="/signin"), encoding="utf-8")
            problems = check_wireframe_html.validate(html_path, prd_path=prd_path)
            self.assertTrue(any("differs from the PRD route" in p for p in problems))

    def test_prd_join_detects_surface_missing_from_wireframe(self):
        with tempfile.TemporaryDirectory() as directory:
            html_path = Path(directory) / "wireframes.html"
            prd_path = Path(directory) / "PRD.md"
            html_path.write_text(render_html(wireframe_data()), encoding="utf-8")
            prd_path.write_text(prd_markdown(surface_id="UI-002"), encoding="utf-8")
            problems = check_wireframe_html.validate(html_path, prd_path=prd_path)
            self.assertTrue(
                any("absent from the wireframe" in p for p in problems)
            )


class PrdUiContractParserTests(unittest.TestCase):
    def test_valid_block_parses_one_surface(self):
        entries, errors = prd_ui_contract.parse_prd_ui_contract(prd_markdown())
        self.assertEqual(errors, [])
        self.assertEqual(set(entries), {"UI-001"})
        self.assertEqual(entries["UI-001"]["routes"], ["/home"])
        self.assertEqual(entries["UI-001"]["states"], ["ready"])

    def test_duplicate_boundary_pairs_are_rejected(self):
        entries, errors = prd_ui_contract.parse_prd_ui_contract(
            prd_markdown() + prd_markdown()
        )
        self.assertTrue(
            any("exactly one matched" in error for error in errors)
        )
        self.assertEqual(set(entries), {"UI-001"})

    def test_heading_outside_boundary_is_rejected(self):
        text = prd_markdown() + (
            "\n### UI-002 — Extra\n\n"
            "- `route`: /extra\n"
            "- `states`: ready\n"
        )
        entries, errors = prd_ui_contract.parse_prd_ui_contract(text)
        self.assertTrue(
            any(
                "outside the ui-surface-contract boundary" in error
                for error in errors
            )
        )
        self.assertEqual(set(entries), {"UI-001"})


if __name__ == "__main__":
    unittest.main()

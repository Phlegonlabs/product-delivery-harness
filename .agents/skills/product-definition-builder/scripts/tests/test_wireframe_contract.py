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
        "schema": "wireframes/2",
        "product": "Test Product",
        "approvalStatus": "approved",
        "source": "PRD.md#UI-Surface-Contract",
        "viewports": [390, 1200],
        "canvasWidths": {"390": 390, "1200": 1200},
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
                "neverDrop": ["R1"],
                "responsiveLayouts": {
                    "390": {
                        "order": ["R1"],
                        "hidden": [],
                        "columns": 1,
                        "spans": {"R1": 1},
                        "reflow": "Stack the summary in one column",
                        "interaction": "Use touch-sized controls",
                    },
                    "1200": {
                        "order": ["R1"],
                        "hidden": [],
                        "columns": 12,
                        "spans": {"R1": 6},
                        "reflow": "Keep the summary in the first six columns",
                        "interaction": "Support pointer and keyboard input",
                    },
                },
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
        '<div id="responsive-controls" data-responsive-target="390"></div>'
        '<div id="state-controls">textContent</div>'
        '<div data-layout-qa="pass"></div>'
        '<script>function runLayoutQa(){}</script>'
        "</body></html>"
    )


def prd_markdown(
    route="/home",
    states="ready",
    responsive="viewports: 390, 1200",
    surface_id="UI-001",
):
    return (
        "# PRD\n\n"
        "<!-- ui-surface-contract:start -->\n"
        "## UI Surface Contract\n\n"
        f"### {surface_id} — Home\n\n"
        f"- `route`: {route}\n"
        f"- `states`: {states}\n"
        f"- `responsive`: {responsive}\n"
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

    def test_duplicate_data_blocks_are_rejected(self):
        html = render_html(wireframe_data())
        payload = json.dumps(wireframe_data(), ensure_ascii=False)
        html += (
            '<script id="wireframe-data" type="application/json">'
            + payload
            + "</script>"
        )

        problems = validate_html(html)

        self.assertTrue(any("exactly one wireframe-data" in p for p in problems))

        unclosed = html + (
            '<script id="wireframe-data" type="application/json">' + payload
        )
        problems = validate_html(unclosed)
        self.assertTrue(any("exactly one wireframe-data" in p for p in problems))

    def test_duplicate_script_id_or_type_attributes_are_rejected_in_both_orders(self):
        data = wireframe_data()
        marker = '<script id="wireframe-data" type="application/json">'
        duplicate_openings = (
            '<script id="wireframe-data" id="other" type="application/json">',
            '<script id="other" id="wireframe-data" type="application/json">',
            '<script id="wireframe-data" type="application/json" type="text/plain">',
            '<script id="wireframe-data" type="text/plain" type="application/json">',
        )
        for opening in duplicate_openings:
            with self.subTest(opening=opening):
                html = render_html(data).replace(
                    marker,
                    opening,
                    1,
                )
                problems = validate_html(html)
                self.assertTrue(
                    any("duplicate HTML attributes" in problem for problem in problems),
                    problems,
                )

    def test_non_object_data_fails_cleanly_under_strict_flags(self):
        self.assertEqual(
            validate_html(render_html([]), require_approved=True),
            ["wireframe-data: must be a JSON object"],
        )
        with tempfile.TemporaryDirectory() as directory:
            html_path = Path(directory) / "wireframes.html"
            prd_path = Path(directory) / "PRD.md"
            html_path.write_text(render_html(["not", "an", "object"]), encoding="utf-8")
            prd_path.write_text(prd_markdown(), encoding="utf-8")

            problems = check_wireframe_html.validate(
                html_path,
                require_filled=True,
                require_approved=True,
                prd_path=prd_path,
            )

        self.assertEqual(problems, ["wireframe-data: must be a JSON object"])

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

        html = render_html(wireframe_data()).replace(
            "<title>", '<style>@import"https://cdn.example.com/theme.css"</style><title>'
        )
        problems = validate_html(html)
        self.assertTrue(any("must not contain CSS @import" in p for p in problems))

    def test_remote_css_urls_and_font_faces_are_rejected(self):
        html = render_html(wireframe_data()).replace(
            "<title>",
            "<style>"
            '.hero { background-image: url("https://cdn.example.com/hero.svg"); }'
            ".icon { background-image: url(//cdn.example.com/icon.svg); }"
            "@font-face { font-family: Remote; src: url('//fonts.example.com/remote.woff2'); }"
            "</style><title>",
        )

        problems = validate_html(html)

        self.assertTrue(any("must not load external resources" in p for p in problems))
        self.assertTrue(any("CSS url" in p for p in problems))

    def test_active_resource_attributes_and_image_set_urls_are_rejected(self):
        html = render_html(wireframe_data()).replace(
            "<title>",
            "<style>"
            '.hero { background-image: image-set("https://cdn.example.com/hero@1x.svg" 1x, '
            "'//cdn.example.com/hero@2x.svg' 2x); }"
            "</style>"
            '<img srcset="https://cdn.example.com/a.png 1x, //cdn.example.com/b.png 2x">'
            '<video poster="https://cdn.example.com/poster.png"></video>'
            '<object data="//cdn.example.com/object.svg"></object>'
            '<svg><image href="https://cdn.example.com/image.svg" '
            'xlink:href="//cdn.example.com/image-legacy.svg"></image></svg>'
            "<title>",
        )

        problems = validate_html(html)

        self.assertTrue(any("srcset" in p for p in problems), problems)
        self.assertTrue(any("poster" in p for p in problems), problems)
        self.assertTrue(any("data=" in p for p in problems), problems)
        self.assertTrue(any("xlink:href" in p for p in problems), problems)
        self.assertTrue(any("image-set" in p for p in problems), problems)

    def test_recorded_urls_in_json_do_not_count_as_external_resources(self):
        data = wireframe_data()
        data["recordedUrl"] = "url(https://example.com/recorded.svg)"
        data["flows"][0]["to"] = "https://example.com/next"
        data["recordedResources"] = {
            "srcset": "https://example.com/recorded.png 1x",
            "poster": "https://example.com/recorded-poster.png",
            "object": "https://example.com/recorded-object.svg",
            "svg": "//example.com/recorded-image.svg",
            "imageSet": 'image-set("https://example.com/recorded@2x.svg" 2x)',
        }

        self.assertEqual([], validate_html(render_html(data)))

    def test_css_comments_do_not_count_as_external_resources(self):
        html = render_html(wireframe_data()).replace(
            "<title>",
            "<style>"
            "/* url(https://cdn.example.com/comment.png) */"
            '/* image-set("//cdn.example.com/comment@2x.png" 2x) */'
            '/* @import"https://cdn.example.com/comment.css" */'
            "</style><title>",
        )

        self.assertEqual([], validate_html(html))

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
        data["screens"][0]["responsiveLayouts"]["390"]["order"] = []
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("regions[0].priority", joined)
        self.assertIn("regions[0].span", joined)
        self.assertIn("responsiveLayouts.390.order", joined)

    def test_responsive_contract_requires_two_complete_targets(self):
        data = wireframe_data()
        data["viewports"] = [390]
        data["canvasWidths"] = {"390": 390}
        data["screens"][0]["responsiveLayouts"] = {
            "390": data["screens"][0]["responsiveLayouts"]["390"]
        }
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("at least two unique targets", joined)

        data = wireframe_data()
        del data["screens"][0]["responsiveLayouts"]["1200"]
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("must contain exactly the responsive targets", joined)

        data = wireframe_data()
        data["canvasWidths"]["390"] = 768
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("must equal its web viewport target", joined)

        data = wireframe_data()
        data["canvasWidths"]["unexpected"] = 640
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("must contain exactly the responsive target keys", joined)

    def test_responsive_layout_cannot_hide_never_drop_regions(self):
        data = wireframe_data()
        data["screens"][0]["responsiveLayouts"]["390"]["hidden"] = ["R1"]
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("must not hide never-drop regions", joined)

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

    def test_prd_join_detects_responsive_set_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            html_path = Path(directory) / "wireframes.html"
            prd_path = Path(directory) / "PRD.md"
            html_path.write_text(render_html(wireframe_data()), encoding="utf-8")
            prd_path.write_text(
                prd_markdown(responsive="viewports: 390, 768"),
                encoding="utf-8",
            )
            problems = check_wireframe_html.validate(html_path, prd_path=prd_path)
            self.assertTrue(any("responsive set" in problem for problem in problems))

    def test_native_size_classes_pass_with_complete_layouts(self):
        data = wireframe_data()
        del data["viewports"]
        data["sizeClasses"] = ["compact", "regular"]
        data["canvasWidths"] = {"compact": 390, "regular": 768}
        layouts = data["screens"][0]["responsiveLayouts"]
        data["screens"][0]["responsiveLayouts"] = {
            "compact": layouts["390"],
            "regular": layouts["1200"],
        }
        with tempfile.TemporaryDirectory() as directory:
            html_path = Path(directory) / "wireframes.html"
            prd_path = Path(directory) / "PRD.md"
            html_path.write_text(render_html(data), encoding="utf-8")
            prd_path.write_text(
                prd_markdown(responsive="sizeClasses: compact, regular"),
                encoding="utf-8",
            )
            self.assertEqual(
                check_wireframe_html.validate(html_path, prd_path=prd_path),
                [],
            )

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
        self.assertEqual(entries["UI-001"]["responsiveKind"], "viewports")
        self.assertEqual(entries["UI-001"]["responsiveTargets"], ["390", "1200"])

    def test_strict_parser_rejects_missing_or_single_responsive_target(self):
        missing = prd_markdown().replace("- `responsive`: viewports: 390, 1200\n", "")
        _, errors = prd_ui_contract.parse_prd_ui_contract(
            missing, require_responsive=True
        )
        self.assertTrue(any("exactly one `responsive` anchor" in error for error in errors))

        _, errors = prd_ui_contract.parse_prd_ui_contract(
            prd_markdown(responsive="sizeClasses: compact"),
            require_responsive=True,
        )
        self.assertTrue(any("at least two responsive targets" in error for error in errors))

    def test_strict_parser_requires_one_package_responsive_set(self):
        text = prd_markdown()[:-1].replace(
            "<!-- ui-surface-contract:end -->",
            "### UI-002 — Settings\n\n"
            "- `route`: /settings\n"
            "- `states`: ready\n"
            "- `responsive`: viewports: 390, 768\n"
            "<!-- ui-surface-contract:end -->",
        )
        _, errors = prd_ui_contract.parse_prd_ui_contract(
            text, require_responsive=True
        )
        self.assertTrue(
            any("same ordered responsive set" in error for error in errors), errors
        )

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

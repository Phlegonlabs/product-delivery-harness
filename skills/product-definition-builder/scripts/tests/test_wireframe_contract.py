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
        "schema": "wireframes/4",
        "product": "Test Product",
        "approvalStatus": "approved",
        "copyFreeze": {
            "status": "approved",
            "owner": "Product owner",
            "locale": "en-US",
            "approvedOn": "2026-09-12",
        },
        "source": "PRD.md#UI-Surface-Contract",
        "viewports": [390, 768, 1200],
        "canvasWidths": {"390": 390, "768": 768, "1200": 1200},
        "screens": [
            {
                "id": "UI-001",
                "name": "Home",
                "route": "/home",
                "goal": "Show the account dashboard",
                "copyStatus": "approved",
                "regions": [
                    {
                        "id": "R1",
                        "section": "Summary",
                        "purpose": "Show the account balance",
                        "priority": "primary",
                        "span": 6,
                        "elements": [
                            {
                                "kind": "static",
                                "role": "heading",
                                "text": "Available balance",
                                "status": "approved",
                                "source": "Owner-approved wireframe copy",
                            },
                            {
                                "kind": "dynamic",
                                "role": "account balance",
                                "example": "$1,240.00",
                                "status": "approved",
                                "source": "Account balance display contract",
                                "contract": {
                                    "source": "account.available_balance",
                                    "order": "single value",
                                    "format": "localized currency",
                                    "count": "one",
                                    "length": "up to 18 characters",
                                    "fallback": "Balance unavailable",
                                },
                            },
                        ],
                        "actions": [
                            {
                                "label": "Refresh balance",
                                "status": "approved",
                                "source": "Owner-approved wireframe copy",
                            }
                        ],
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
                    "768": {
                        "order": ["R1"],
                        "hidden": [],
                        "columns": 6,
                        "spans": {"R1": 6},
                        "reflow": "Widen the summary to half the canvas",
                        "interaction": "Keep touch and pointer controls reachable",
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
                        "treatments": {},
                    }
                ],
            }
        ],
        "flows": [
            {
                "from": "UI-001",
                "trigger": "Refresh balance",
                "to": "Updated summary",
                "presentation": "feedback",
                "feedback": {
                    "kind": "static",
                    "role": "success status",
                    "text": "Your balance is up to date.",
                    "status": "approved",
                    "source": "Owner-approved feedback copy",
                },
            }
        ],
    }
    data.update(overrides)
    return data


def legacy_wireframe_data(schema):
    data = wireframe_data()
    data["schema"] = schema
    data.pop("copyFreeze")
    for flow in data.get("flows", []):
        flow.pop("feedback", None)
    for screen in data["screens"]:
        screen.pop("copyStatus")
        for region in screen["regions"]:
            region["elements"] = [
                item.get("text") or {"label": item["example"], "contract": item["contract"]}
                for item in region["elements"]
            ]
            region["actions"] = [item["label"] for item in region["actions"]]
        for screen_state in screen["states"]:
            screen_state["treatments"] = {
                region_id: treatment["layout"]
                for region_id, treatment in screen_state["treatments"].items()
            }
    return data


def render_html(data):
    payload = json.dumps(data, ensure_ascii=False)
    return (
        "<!doctype html><html><head><title>Wireframes</title></head><body>"
        '<script id="wireframe-data" type="application/json">' + payload + "</script>"
        '<nav id="page-list">All pages</nav>'
        '<div id="responsive-controls" data-responsive-target="390"></div>'
        '<div id="state-controls">textContent</div>'
        '<dialog id="copy-inventory"></dialog>'
        '<aside id="inspector"></aside>'
        '<div class="product-copy">copyFreeze</div>'
        '<div data-layout-qa="pass"></div>'
        '<script>function runLayoutQa(){}</script>'
        "</body></html>"
    )


def prd_markdown(
    route="/home",
    states="ready",
    responsive="viewports: 390, 768, 1200",
    copy_status="approved",
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
        f"- `copy`: {copy_status} — static copy is implementation-bound\n"
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

    def test_escaped_css_schemes_in_style_blocks_are_rejected(self):
        html = render_html(wireframe_data()).replace(
            "<title>",
            "<style>"
            '.hero { background-image: u\\72l("\\68 ttps://cdn.example.com/hero.svg"); }'
            '.icon { background-image: image-\\000073et("\\000068ttps://cdn.example.com/icon.svg" 1x); }'
            '@im\\70ort "\\000048ttps://cdn.example.com/theme.css";'
            "</style><title>",
        )

        problems = validate_html(html)

        self.assertTrue(any("CSS url" in problem for problem in problems), problems)
        self.assertTrue(any("image-set" in problem for problem in problems), problems)
        self.assertTrue(any("CSS @import" in problem for problem in problems), problems)

    def test_escaped_css_schemes_in_inline_style_attributes_are_rejected(self):
        html = render_html(wireframe_data()).replace(
            "<title>",
            '<div style="background-image: url(\\000048ttps://cdn.example.com/inline.svg)"></div>'
            "<title>",
        )

        problems = validate_html(html)

        self.assertTrue(any("CSS url" in problem for problem in problems), problems)

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
        data["escapedRecordedUrl"] = r'url("\68 ttps://example.com/escaped.svg")'
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

    def test_copy_freeze_requires_approved_copy_and_an_approval_date(self):
        data = wireframe_data()
        data["screens"][0]["regions"][0]["elements"][0]["status"] = "draft"
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("must be 'approved' when copy is frozen", joined)

        data = wireframe_data()
        data["copyFreeze"]["approvedOn"] = "pending"
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("must be an ISO YYYY-MM-DD date", joined)

        data = wireframe_data()
        data["copyFreeze"]["locale"] = "English_US"
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("must be a BCP 47-style language tag", joined)

        data = wireframe_data()
        data["copyFreeze"]["status"] = "draft"
        data["copyFreeze"]["approvedOn"] = "pending"
        data["approvalStatus"] = "draft"
        self.assertEqual([], validate_html(render_html(data)))
        joined = "\n".join(
            validate_html(render_html(data), require_approved=True)
        )
        self.assertIn("copyFreeze.status: must be 'approved'", joined)

    def test_copy_freeze_gate_precedes_structural_approval(self):
        data = wireframe_data()
        data["approvalStatus"] = "draft"
        self.assertEqual(
            [],
            validate_html(
                render_html(data),
                require_filled=True,
                require_copy_approved=True,
            ),
        )
        joined = "\n".join(
            validate_html(render_html(data), require_approved=True)
        )
        self.assertIn("approvalStatus: must be 'approved'", joined)

        data["copyFreeze"]["status"] = "draft"
        data["copyFreeze"]["approvedOn"] = "pending"
        joined = "\n".join(validate_html(render_html(data), require_copy_approved=True))
        self.assertIn("copyFreeze.status: must be 'approved'", joined)

        data["approvalStatus"] = "approved"
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("before structural approvalStatus", joined)

        legacy = legacy_wireframe_data("wireframes/3")
        joined = "\n".join(
            validate_html(render_html(legacy), require_copy_approved=True)
        )
        self.assertIn("must be 'wireframes/4' for the Copy Freeze Gate", joined)

    def test_dynamic_copy_requires_a_complete_display_contract(self):
        data = wireframe_data()
        del data["screens"][0]["regions"][0]["elements"][1]["contract"][
            "fallback"
        ]
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("contract.fallback", joined)

    def test_v4_rejects_unstructured_elements_actions_and_screen_copy_status(self):
        data = wireframe_data()
        data["screens"][0]["regions"][0]["elements"] = ["Untracked copy"]
        data["screens"][0]["regions"][0]["actions"] = ["Refresh balance"]
        data["screens"][0]["copyStatus"] = "draft"
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("elements[0]: must be an object in wireframes/4", joined)
        self.assertIn("actions[0]: must be an object in wireframes/4", joined)
        self.assertIn("copyStatus: must be 'approved' when copy is frozen", joined)

    def test_alternate_state_requires_explicit_product_or_assistive_copy(self):
        data = wireframe_data()
        data["screens"][0]["states"].append(
            {
                "id": "error",
                "label": "Error",
                "treatments": {
                    "R1": {
                        "layout": "Keep the balance visible and add recovery",
                        "copy": [],
                    }
                },
            }
        )
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("must include product or assistive copy", joined)

        data["screens"][0]["states"][1]["treatments"]["R1"]["copy"] = [
            {
                "kind": "static",
                "role": "error message",
                "text": "We could not refresh your balance. Try again.",
                "status": "approved",
                "source": "Owner-approved error copy",
            }
        ]
        self.assertEqual([], validate_html(render_html(data)))

    def test_v4_requires_ready_as_the_baseline_state(self):
        data = wireframe_data()
        data["screens"][0]["states"][0]["id"] = "default"
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("must be 'ready' as the schema-4 baseline state", joined)

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

    def test_media_intent_accepts_only_deferred_generation_handoffs(self):
        data = wireframe_data()
        data["screens"][0]["mediaIntent"] = {
            "treatment": "motion-led",
            "draftPrompt": "Animate the account total after refresh",
            "source": "Owner decision 2026-09-09",
            "generationStatus": "deferred",
        }
        data["screens"][0]["regions"][0]["mediaIntent"] = {
            "treatment": "imagery-led",
            "draftPrompt": "Account summary illustration for the balance region",
            "source": "Owner decision 2026-09-09",
            "generationStatus": "deferred",
        }
        self.assertEqual([], validate_html(render_html(data)))

        invalid_values = (
            ("not-an-object", "mediaIntent: must be an object"),
            (
                {
                    "treatment": "cinematic",
                    "draftPrompt": "Prompt",
                    "source": "Owner",
                    "generationStatus": "deferred",
                },
                "mediaIntent.treatment",
            ),
            (
                {
                    "treatment": "motion-led",
                    "draftPrompt": "",
                    "source": "Owner",
                    "generationStatus": "deferred",
                },
                "mediaIntent.draftPrompt",
            ),
            (
                {
                    "treatment": "motion-led",
                    "draftPrompt": "Prompt",
                    "source": "",
                    "generationStatus": "deferred",
                },
                "mediaIntent.source",
            ),
            (
                {
                    "treatment": "motion-led",
                    "draftPrompt": "Prompt",
                    "source": "Owner",
                    "generationStatus": "generated",
                },
                "mediaIntent.generationStatus",
            ),
        )
        for value, expected in invalid_values:
            with self.subTest(expected=expected):
                candidate = wireframe_data()
                candidate["screens"][0]["mediaIntent"] = value
                joined = "\n".join(validate_html(render_html(candidate)))
                self.assertIn(expected, joined)

    def test_legacy_v2_projection_remains_readable(self):
        data = legacy_wireframe_data("wireframes/2")
        data["flows"][0].pop("presentation")
        data["flows"][0]["trigger"] = "Historical trigger without a visible action"
        data["screens"][0]["mediaIntent"] = "historically ignored extension data"
        self.assertEqual([], validate_html(render_html(data)))

    def test_legacy_v3_projection_remains_readable(self):
        data = legacy_wireframe_data("wireframes/3")
        self.assertEqual([], validate_html(render_html(data)))

    def test_actions_and_flows_must_form_one_working_local_mapping(self):
        data = wireframe_data()
        data["flows"][0]["presentation"] = "popup"
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("flows[0].presentation", joined)

        data = wireframe_data()
        data["flows"][0] = {
            "from": "UI-001",
            "trigger": "Refresh balance",
            "to": "UI-999",
            "presentation": "overlay",
        }
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("overlay must target a known screen ID", joined)

        data = wireframe_data()
        data["flows"] = []
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("must match exactly one outgoing flow", joined)

        data = wireframe_data()
        data["flows"].append(dict(data["flows"][0]))
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("must match exactly one outgoing flow (found 2)", joined)

        data = wireframe_data()
        data["flows"][0]["trigger"] = "Unplaced action"
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("must match exactly one visible region action", joined)

        data = wireframe_data()
        del data["flows"][0]["feedback"]
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("flows[0].feedback: must be an object", joined)

    def test_responsive_contract_requires_three_complete_web_targets(self):
        data = wireframe_data()
        data["viewports"] = [390]
        data["canvasWidths"] = {"390": 390}
        data["screens"][0]["responsiveLayouts"] = {
            "390": data["screens"][0]["responsiveLayouts"]["390"]
        }
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("at least three ascending numeric viewports", joined)

        data = wireframe_data()
        data["viewports"] = [390, 1200]
        data["canvasWidths"] = {"390": 390, "1200": 1200}
        data["screens"][0]["responsiveLayouts"] = {
            "390": data["screens"][0]["responsiveLayouts"]["390"],
            "1200": data["screens"][0]["responsiveLayouts"]["1200"],
        }
        joined = "\n".join(validate_html(render_html(data)))
        self.assertIn("at least three ascending numeric viewports", joined)

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

    def test_prd_join_requires_and_matches_copy_status_for_v4(self):
        with tempfile.TemporaryDirectory() as directory:
            html_path = Path(directory) / "wireframes.html"
            prd_path = Path(directory) / "PRD.md"
            html_path.write_text(render_html(wireframe_data()), encoding="utf-8")
            prd_path.write_text(prd_markdown(copy_status="draft"), encoding="utf-8")
            problems = check_wireframe_html.validate(html_path, prd_path=prd_path)
            self.assertTrue(any("copy status" in problem for problem in problems))

            prd_path.write_text(
                prd_markdown().replace(
                    "- `copy`: approved — static copy is implementation-bound\n", ""
                ),
                encoding="utf-8",
            )
            problems = check_wireframe_html.validate(html_path, prd_path=prd_path)
            self.assertTrue(
                any("exactly one `copy` anchor" in problem for problem in problems)
            )

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
        self.assertEqual(entries["UI-001"]["responsiveTargets"], ["390", "768", "1200"])
        self.assertEqual(entries["UI-001"]["copyStatus"], "approved")

    def test_strict_parser_rejects_missing_or_incomplete_responsive_target(self):
        missing = prd_markdown().replace(
            "- `responsive`: viewports: 390, 768, 1200\n", ""
        )
        _, errors = prd_ui_contract.parse_prd_ui_contract(
            missing, require_responsive=True
        )
        self.assertTrue(any("exactly one `responsive` anchor" in error for error in errors))

        _, errors = prd_ui_contract.parse_prd_ui_contract(
            prd_markdown(responsive="sizeClasses: compact"),
            require_responsive=True,
        )
        self.assertTrue(any("at least two responsive size classes" in error for error in errors))

        _, errors = prd_ui_contract.parse_prd_ui_contract(
            prd_markdown(responsive="viewports: 390, 1200"),
            require_responsive=True,
            web_floor=3,
        )
        self.assertTrue(any("at least three responsive viewports" in error for error in errors))

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

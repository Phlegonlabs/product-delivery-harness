"""Composition data validation and a reusable browser-preview fixture."""

import copy
import re
import unittest
from pathlib import Path

from test_wireframe_contract import render_html, validate_html, wireframe_data


def composition_data():
    data = wireframe_data(product="Studio / Weekly work")
    data["flows"][0]["trigger"] = "Refresh projects"
    data["flows"][0]["feedback"]["text"] = "Your projects are up to date."
    screen = data["screens"][0]
    screen.update(name="Weekly workspace", goal="Review current work and the next decisions.")

    def item(role, text):
        return {"kind": "static", "role": role, "text": text,
                "status": "approved", "source": "Synthetic test fixture"}

    def region(identity, presentation, elements):
        return {"id": identity, "section": identity, "purpose": "Review weekly work",
                "priority": "secondary", "presentation": presentation, "span": 12,
                "elements": [item(*entry) for entry in elements], "actions": []}

    screen["regions"] = [
        region("navigation", "navigation", [("brand", "Studio"), ("navigation label", "Workspace")]),
        region("summary", "editorial", [("heading", "Make room for focused work."),
                                        ("supporting body", "Three projects. Two decisions. A clear plan for the week ahead.")]),
        region("projects", "table", [("section heading", "Current projects"),
                                     ("table header", "Project"), ("table header", "Stage"),
                                     ("table header", "Next review"),
                                     ("table cell", "Member experience"), ("table cell", "Design"), ("table cell", "Tuesday"),
                                     ("table cell", "Editorial platform"), ("table cell", "Research"), ("table cell", "Thursday"),
                                     ("table cell", "Account recovery"), ("table cell", "Verification"), ("table cell", "Friday")]),
        region("decisions", "list", [("section heading", "Needs your attention"),
                                     ("list item", "Review the compact navigation proposal."),
                                     ("list item", "Confirm the empty-state recovery path.")]),
        region("settings", "form", [("section heading", "Workspace details"),
                                    ("supporting body", "Read-only structural preview"),
                                    ("field label", "Workspace name"), ("field value", "Studio"),
                                    ("field label", "Review cadence"), ("field value", "Every Friday")]),
    ]
    screen["regions"][1]["actions"] = [{"label": "Refresh projects", "status": "approved", "source": "Synthetic test fixture"}]
    screen["regions"][1]["primaryAction"] = "Refresh projects"
    screen["neverDrop"] = ["navigation", "summary", "projects"]
    identities = [region["id"] for region in screen["regions"]]
    for target, layout in screen["responsiveLayouts"].items():
        layout.update(order=identities[:], hidden=[], spans={identity: layout["columns"] for identity in identities})
        if target == "1200":
            layout["spans"].update(projects=8, decisions=4, settings=8)
    screen["states"].append({"id": "empty", "label": "Empty", "treatments": {
        "projects": {"layout": "Show recovery guidance", "copy": [item("empty status", "No projects match this view. Refresh to try again.")]}
    }})
    return data


class CompositionTests(unittest.TestCase):
    def test_typed_composition_preserves_valid_copy_and_flows(self):
        self.assertEqual([], validate_html(render_html(composition_data()), require_filled=True, require_approved=True))

    def test_incomplete_table_rows_fail(self):
        data = composition_data()
        data["screens"][0]["regions"][2]["elements"].pop()
        self.assertIn("complete rows", "\n".join(validate_html(render_html(data))))

    def test_primary_action_cannot_invent_a_control(self):
        data = composition_data()
        data["screens"][0]["regions"][1]["primaryAction"] = "Publish"
        self.assertIn("must match exactly one existing action label", "\n".join(validate_html(render_html(data))))

    def test_form_value_requires_an_immediate_label(self):
        data = composition_data()
        data["screens"][0]["regions"][4]["elements"].pop(2)
        self.assertIn("immediately follow", "\n".join(validate_html(render_html(data))))

    def test_structured_content_cannot_silently_reorder_copy(self):
        for index, message in ((2, "introduction, headers"), (3, "introduction must precede")):
            data = composition_data()
            elements = data["screens"][0]["regions"][index]["elements"]
            elements.append(elements.pop(0))
            self.assertIn(message, "\n".join(validate_html(render_html(data))))

    def test_unknown_presentations_and_empty_typed_content_fail(self):
        for kind in ("tiles", [], {}, "list", "form", "table"):
            with self.subTest(kind=kind):
                data = wireframe_data()
                data["screens"][0]["regions"][0]["presentation"] = copy.deepcopy(kind)
                self.assertTrue(validate_html(render_html(data)))

    def test_template_palette_is_neutral(self):
        template = Path(__file__).resolve().parents[2] / "assets/templates/WIREFRAMES.template.html"
        css = template.read_text(encoding="utf-8").split("<style>")[1].split("</style>")[0]
        for color in re.findall(r"#([0-9a-f]{6}|[0-9a-f]{3})\b", css):
            channels = [color[index:index+2] for index in (0, 2, 4)] if len(color) == 6 else list(color)
            self.assertEqual(1, len(set(channels)), color)
        for channels in re.findall(r"rgb\((\d+) (\d+) (\d+)", css):
            self.assertEqual(1, len(set(channels)), channels)


if __name__ == "__main__":
    unittest.main()

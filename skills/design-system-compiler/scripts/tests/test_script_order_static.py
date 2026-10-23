"""ds-showcase/2 source script order: one occurrence inventory, inert source slots and fail-closed shapes.

Synthetic Kiln Timer fixture with extra recording scripts, not an approved
product. Browser behavior is in test_script_order_browser.py.
"""

import base64
import hashlib
import html as html_lib
import json
from pathlib import Path
import re
import sys
import unittest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parents[0]))
sys.path.append(str(TESTS))

import design_system_showcase as showcase  # noqa: E402
import runtime_fixture as fixture  # noqa: E402
import source_script_order as script_order  # noqa: E402
import surface_adapter  # noqa: E402
from design_system_runtime_assets import RUNTIME_BOOT, RUNTIME_FRAME  # noqa: E402

# One body, three occurrences: each records where and when the browser ran it.
RECORD = """(function () {
  var s = document.currentScript, near = function (n) { return !n ? null : n.hasAttribute("data-hifi-state-view")
    ? n.getAttribute("data-hifi-state-view") + "@" + n.getAttribute("data-responsive-target") : n.tagName.toLowerCase(); };
  var v = Array.from(document.querySelectorAll("[data-hifi-state-view]")).filter(function (x) { return !x.hidden; })[0];
  var data = document.getElementById("inert-data");
  (window.__order = window.__order || []).push({parent: s ? s.parentElement.tagName.toLowerCase() + (s.parentElement.hasAttribute("data-ui-surface") ? "[surface]" : "") : null,
    prev: s ? near(s.previousElementSibling) : null, next: s ? near(s.nextElementSibling) : null, attrs: s ? s.attributes.length : -1,
    own: s ? s.textContent.length : -1, view: v ? near(v) : null, target: document.querySelector("[data-hifi-canvas]").getAttribute("data-hifi-target"),
    inert: data ? data.type + " " + data.textContent : null, pending: document.querySelectorAll('script[type="text/x-ds-source-slot"]').length,
    runtime: Boolean(document.__hifiReviewerRuntime)});
})();"""
# Shaped like the approved heading-focus script; it also records which heading it focused.
FOCUS = ("(function () { var hs = document.querySelectorAll('[data-hifi-canvas] [data-hifi-state-view] h1'); for (var i = 0; i < hs.length; i++) "
         "{ if (hs[i].offsetParent !== null) { hs[i].setAttribute('tabindex', '-1'); hs[i].focus({preventScroll: true}); (window.__focused = "
         "window.__focused || []).push(hs[i].parentNode.dataset.hifiStateView + '@' + hs[i].parentNode.dataset.responsiveTarget); break; } } })();")
CLICKS = 'document.addEventListener("click", function () { window.__clicks = (window.__clicks || 0) + 1; });'
INERT = '<script type="application/json" id="inert-data">{"kind": "inert"}</script>'
TEMPLATE = "<template><script>window.__template = 1;</script></template>"
EXPECTED = [(RECORD, "before"), (RECORD, "surface"), (FOCUS, "surface"), (RECORD, "surface"), (fixture.PRODUCT_SCRIPT, "after"), (CLICKS, "after")]
VIEWS = {(state, target): fixture._view(state, target) for state in ("ready", "running") for target in ("390", "768")}


def ordered_pages(change=None, focus=FOCUS):
    record = f"<script>{RECORD}</script>"
    views = (VIEWS["ready", "390"] + record + INERT + f"<script>{focus}</script>" + TEMPLATE + VIEWS["ready", "768"]
             + VIEWS["running", "390"] + record + VIEWS["running", "768"])
    page = fixture.pages(views=views, scripts_after=f"<script>{CLICKS}</script>")["index.html"]
    page = page.replace("<main><div data-hifi-canvas", record + "<main><div data-hifi-canvas", 1)
    return {"index.html": change(page) if change else page}


def surface_findings(page_set):
    manifest = json.loads(showcase.MANIFEST_RE.search(page_set["index.html"]).group("data"))
    trees = {name: showcase.SourceTree(html) for name, html in page_set.items()}
    return "\n".join(surface_adapter.resolve_surfaces(trees, manifest)[1])


def plates(document):
    return [(attrs, html_lib.unescape(src)) for attrs, src in re.findall(r'<iframe ([^>]*?) srcdoc="([^"]*)"></iframe>', document)]


def digest(script):
    return "'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'"


def marker(index, body):
    return f'<script type="text/x-ds-source-slot" data-ds-source-slot="{index}">{body}</script>'


class InventoryTests(unittest.TestCase):
    def test_inventory_lists_every_classic_occurrence_in_source_order(self):
        tree = showcase.SourceTree(ordered_pages()["index.html"])
        surface = showcase.surface_node(tree, "UI-001")
        order, problems = script_order.inventory(tree, surface, "UI-001")
        self.assertEqual([], problems)
        self.assertEqual(EXPECTED, [(slot["body"], slot["place"]) for slot in order["slots"]])
        self.assertEqual(list(range(6)), [slot["index"] for slot in order["slots"]])
        self.assertEqual(sorted(slot["node"]["start"] for slot in order["slots"]), [slot["node"]["start"] for slot in order["slots"]])
        body = next(node for node in tree.nodes if node["tag"] == "body")
        self.assertEqual({body["index"]}, {slot["parent"] for slot in order["slots"] if slot["place"] != "surface"})
        self.assertEqual([hashlib.sha256(text.encode()).hexdigest() for text, _ in EXPECTED], [slot["sha256"] for slot in order["slots"]])

    def test_unsupported_shapes_fail_closed(self):
        inside = lambda markup: lambda page: page.replace(INERT, INERT + markup, 1)  # noqa: E731
        cases = {
            "external": (inside('<script src="later.js"></script>'), "is an external script"),
            "external outside": (lambda p: p.replace("</main>", '</main><script src="later.js"></script>', 1), "is an external script"),
            "module": (inside('<script type="module">void 0;</script>'), "is a module script"),
            "async": (inside("<script async>void 0;</script>"), "unsupported attributes (async)"),
            "defer": (inside("<script defer>void 0;</script>"), "unsupported attributes (defer)"),
            "nomodule": (inside("<script nomodule>void 0;</script>"), "unsupported attributes (nomodule)"),
            "attributed": (inside('<script id="named">void 0;</script>'), "unsupported attributes (id)"),
            "typed classic": (inside('<script type="text/javascript">void 0;</script>'), "unsupported attributes (type)"),
            "language": (inside('<script language="javascript">void 0;</script>'), "unsupported attributes (language)"),
            "svg": (inside("<svg><script>void 0;</script></svg>"), "inside SVG or MathML content"),
            "unretained parent": (lambda p: p.replace("<main><div", '<div class="aside"><script>void 0;</script></div><main><div', 1),
                                  "has no retained source parent"),
            "head": (lambda p: p.replace("</head>", "<script>void 0;</script></head>", 1), "has no retained source parent"),
            "connect inside": (inside('<script>connectHifiReviewer({"packageId": "ui-hifi/2:kiln"})</script>'),
                               "reviewer connect call inside the product surface"),
            "reserved type": (inside('<script type="text/x-ds-source-slot">void 0;</script>'), "reserved source slot marker"),
            "reserved attribute": (inside('<script type="text/plain" data-ds-source-slot="0">x</script>'), "reserved source slot marker"),
        }
        self.assertEqual("", surface_findings(ordered_pages()))
        for label, (change, expected) in cases.items():
            with self.subTest(label):
                page_set = ordered_pages(change)
                self.assertNotEqual(page_set, ordered_pages(), "the mutation applies")
                self.assertIn(expected, surface_findings(page_set))
                with self.assertRaisesRegex(ValueError, re.escape(expected)):
                    fixture.render(page_set)

    def test_data_template_and_unrelated_inert_scripts_are_not_activated(self):
        extra = lambda p: p.replace("<main><div", '<div class="aside"><script type="text/plain">notes</script></div><main><div', 1)  # noqa: E731
        page_set = ordered_pages(extra)
        self.assertEqual("", surface_findings(page_set))
        tree = showcase.SourceTree(page_set["index.html"])
        order, _ = script_order.inventory(tree, showcase.surface_node(tree, "UI-001"), "UI-001")
        self.assertEqual(6, len(order["slots"]))


class PlateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = fixture.render(ordered_pages())
        cls.plates = plates(cls.document)

    def ordered(self):
        return [frame for attrs, frame in self.plates if "data-ds-surface-frame" in attrs or "data-ds-runtime-frame" in attrs]

    def test_each_occurrence_stays_at_its_source_position_as_one_inert_slot(self):
        frames = self.ordered()
        self.assertEqual(4, len(frames), "one Surface plate and three motion plates")
        for frame in frames:
            with self.subTest(frame[:60]):
                slots = re.findall(r'<script type="text/x-ds-source-slot" data-ds-source-slot="(\d+)">', frame)
                self.assertEqual([str(index) for index in range(6)], slots, "document order is source order")
                for index, (body, _) in enumerate(EXPECTED):
                    self.assertIn(marker(index, body), frame)
                self.assertEqual(3, frame.count(RECORD), "identical bodies at different offsets stay separate occurrences")
                for body in (FOCUS, CLICKS, fixture.PRODUCT_SCRIPT):
                    self.assertEqual(1, frame.count(body))
                    self.assertNotIn(f"<script>{body}</script>", frame, "no duplicate executable copy")
                self.assertIn(INERT, frame)
                self.assertIn(TEMPLATE, frame)
                positions = [frame.index(marker(0, RECORD)), frame.index("<main>"), frame.index(VIEWS["ready", "390"][:60]),
                             frame.index(marker(1, RECORD)), frame.index(INERT), frame.index(marker(2, FOCUS)), frame.index(TEMPLATE),
                             frame.index(marker(3, RECORD)), frame.index("</main>"), frame.index(marker(4, fixture.PRODUCT_SCRIPT)),
                             frame.index(marker(5, CLICKS))]
                self.assertEqual(sorted(positions), positions)
                self.assertTrue(frame.endswith(f"<script>{script_order.LOADER}</script></body></html>"), "the loader runs last")
                inventory = json.loads(re.search(r'<script type="application/json" id="ds-source-order">([^<]*)</script>', frame).group(1))
                self.assertEqual({"count": 6, "sha256": [hashlib.sha256(body.encode()).hexdigest() for body, _ in EXPECTED]}, inventory)

    def test_only_fixed_infrastructure_is_parser_executable(self):
        definitions = re.search(r"<script[^>]*>([\s\S]*?)</script>", fixture.REVIEWER_RUNTIME).group(1)
        for attrs, frame in self.plates:
            executable = set(re.findall(r"<script>([\s\S]*?)</script>", frame)) - {"window.__template = 1;"}
            if "data-ds-surface-frame" in attrs:
                expected = {surface_adapter.SURFACE_FOCUS_GUARD, surface_adapter.SURFACE_CLIPBOARD_GUARD,
                            surface_adapter.SURFACE_FRAME, script_order.LOADER, definitions,
                            'connectHifiReviewer({"packageId": "ui-hifi/2:kiln", "page": "index.html", "storage": null})'}
                self.assertLess(frame.index(surface_adapter.SURFACE_FRAME), frame.index(script_order.LOADER),
                                "source-control selection precedes product activation")
            elif "data-ds-runtime-frame" in attrs:
                expected = {RUNTIME_FRAME, surface_adapter.SURFACE_FOCUS_GUARD, RUNTIME_BOOT, script_order.LOADER, definitions}
                self.assertLess(frame.index(RUNTIME_BOOT), frame.index(script_order.LOADER))
            else:
                self.assertNotIn("text/x-ds-source-slot", frame, "component plates are unchanged")
                self.assertNotIn(script_order.LOADER, frame)
                continue
            self.assertEqual(expected, executable)

    def test_policy_pins_the_loader_and_every_slot_body(self):
        policy = html_lib.unescape(re.search(r'Content-Security-Policy" content="([^"]+)"', self.document).group(1))
        for body in [script_order.LOADER] + [body for body, _ in EXPECTED]:
            self.assertIn(digest(body), policy)
        self.assertIn("connect-src 'none'", policy)
        self.assertNotIn("unsafe-eval", policy)
        self.assertNotIn("'unsafe-inline'", policy.split("script-src", 1)[1])


if __name__ == "__main__":
    unittest.main()

"""Where operation focus ends, layer entry and return, and complete product-focus recording."""
from pathlib import Path
import tempfile
import unittest

import test_hifi_operation_alignment as alignment
import test_ui_design_contract as contract
import check_ui_design_contract as checker
import hifi_matrix_capture as capture
from reviewer_shell import runtime_source


def historical_runtimes():
    previous = (Path(__file__).resolve().parents[4]
        / "skills/design-system-compiler/scripts/tests/fixtures/reviewer-runtime-0.87.0.html").read_text(encoding="utf-8")
    return (previous, previous.replace(
        '[...host.querySelectorAll("[data-product-menu]"), ...host.querySelectorAll("[data-product-disclosure]")]',
        'host.querySelectorAll("[data-product-menu]")'))


class FocusBrowserTests(unittest.TestCase):
    playwright = alignment.OperationBrowserTests.playwright
    driver = alignment.OperationBrowserTests.driver
    attempt = alignment.OperationBrowserTests.attempt

    def check_attempts(self, markup, passes, observation=None, panel="picker"):
        driver = self.driver(markup)
        for trigger in ("click", "keyboard"):
            with self.subTest(trigger=trigger):
                result = self.attempt(driver, trigger=trigger)["result"]
                self.assertEqual([], result["problems"], result)
                self.assertEqual(passes, result["focusCorrect"], result)
                if observation:
                    self.assertEqual(panel, result["observed"].get(observation), result)
                if not passes:
                    self.assertNotIn("focusReturn", result["observed"])
                    self.assertNotIn("focusEntry", result["observed"])
        driver.stop()

    def test_n1_a_return_to_the_opener_passes_whichever_comes_first(self):
        for close_first in (False, True):
            hide = "document.getElementById('picker').hidden=true;"
            focus = "document.getElementById('opener').focus();"
            handler = hide + focus if close_first else focus + hide
            with self.subTest(close_first=close_first):
                self.check_attempts('<button id="opener" data-product-disclosure aria-controls="picker" '
                    'aria-expanded="true">Pick</button><div id="picker">'
                    '<button data-control-id="save" onclick="' + handler + '">Cancel</button></div>',
                    True, "focusReturn")

    def test_n2_a_detour_before_the_return_still_ends_on_the_opener(self):
        for detour in (False, True):
            handler = "document.getElementById('picker').hidden=true;"
            if detour:
                handler += "document.getElementById('thief').focus();"
            handler += "document.getElementById('opener').focus();"
            with self.subTest(detour=detour):
                self.check_attempts('<button id="opener" data-product-disclosure aria-controls="picker" '
                    'aria-expanded="true">Pick</button><div id="picker">'
                    '<button data-control-id="save" onclick="' + handler + '">Cancel</button></div>'
                    '<div tabindex="-1" id="thief">Unrelated</div>', True, "focusReturn")

    def test_return_to_another_layers_opener_or_a_never_open_panel_fails(self):
        for other_open in (False, True):
            with self.subTest(other_open=other_open):
                self.check_attempts('<button id="opener" data-product-disclosure aria-controls="picker" '
                    'aria-expanded="true">Pick</button><div id="picker">'
                    '<button data-control-id="save" onclick="document.getElementById(\'picker\').hidden=true;'
                    'document.getElementById(\'other-opener\').focus()">Cancel</button></div>'
                    '<button id="other-opener" data-product-disclosure aria-controls="other" '
                    'aria-expanded="' + str(other_open).lower() + '">Other</button>'
                    '<div id="other"' + ('' if other_open else ' hidden') + '>Other panel</div>', False)

    def test_n3_closing_two_siblings_cannot_return_to_the_unrelated_opener(self):
        for move_control in (False, True):
            with self.subTest(move_control=move_control):
                move = "document.getElementById('other').append(this);" if move_control else ""
                self.check_attempts('<button id="opener" data-product-disclosure aria-controls="picker" '
                    'aria-expanded="true">Pick</button><div id="picker"><button data-control-id="save" '
                    'onclick="' + move + 'document.getElementById(\'picker\').hidden=true;'
                    'document.getElementById(\'other\').hidden=true;'
                    'document.getElementById(\'other-opener\').focus()">Cancel</button></div>'
                    '<button id="other-opener" data-product-disclosure aria-controls="other" '
                    'aria-expanded="true">Other</button><div id="other">Other panel</div>', False)

    def test_n3_return_to_the_containing_panel_leaves_the_sibling_open(self):
        self.check_attempts('<button id="opener" data-product-disclosure aria-controls="picker" '
            'aria-expanded="true">Pick</button><div id="picker"><button data-control-id="save" '
            'onclick="document.getElementById(\'picker\').hidden=true;'
            'document.getElementById(\'opener\').focus()">Cancel</button></div>'
            '<button id="other-opener" data-product-disclosure aria-controls="other" '
            'aria-expanded="true">Other</button><div id="other">Other panel</div>', True, "focusReturn")

    def test_n3_nested_returns_accept_closed_containing_panels_from_inner_to_outer(self):
        for close_outer in (False, True):
            with self.subTest(close_outer=close_outer):
                close = "document.getElementById('outer').hidden=true;" if close_outer else ""
                opener = "outer-opener" if close_outer else "opener"
                self.check_attempts('<button id="outer-opener" data-product-disclosure aria-controls="outer" '
                    'aria-expanded="true">Outer</button><div id="outer">'
                    '<button id="opener" data-product-disclosure aria-controls="picker" '
                    'aria-expanded="true">Inner</button><div id="picker"><button data-control-id="save" '
                    'onclick="document.getElementById(\'picker\').hidden=true;' + close
                    + 'document.getElementById(\'' + opener + '\').focus()">Cancel</button></div></div>',
                    True, "focusReturn", "outer" if close_outer else "picker")

    def test_opening_a_layer_may_end_focus_anywhere_new_inside_it(self):
        for semantic in (False, True):
            for field in (False, True):
                for mode in ("new", "already-open", "detour", "second-focus"):
                    with self.subTest(semantic=semantic, field=field, mode=mode):
                        reveal = "document.getElementById('picker').hidden=false;"
                        focus = "document.getElementById('inside').focus();"
                        handler = reveal + focus
                        if mode == "detour":
                            handler = "document.getElementById('thief').focus();" + handler
                        if mode == "second-focus":
                            handler += "document.getElementById('second').focus();"
                        declared = '' if semantic else (' data-product-disclosure aria-controls="picker" '
                            'aria-expanded="' + str(mode == "already-open").lower() + '"')
                        self.check_attempts('<button data-control-id="save"' + declared
                            + ' onclick="this.textContent+=\' changed\';' + handler + '">Open</button>'
                            '<div id="picker"' + (' role="dialog"' if semantic else '')
                            + ('' if mode == "already-open" else ' hidden') + '>'
                            + ('<input id="inside">' if field else '<h2 tabindex="-1" id="inside">Title</h2>')
                            + '<div tabindex="-1" id="second">Second</div></div>'
                            '<div tabindex="-1" id="thief">Unrelated</div>', mode != "already-open",
                            "focusEntry" if mode != "already-open" else None)

    def test_preparatory_opener_may_focus_its_new_layer_before_cancel(self):
        self.check_attempts('<button id="opener" data-product-disclosure aria-controls="picker" '
            'aria-expanded="false" onclick="document.getElementById(\'picker\').hidden=false;'
            'document.getElementById(\'inside\').focus()">Pick</button><div id="picker" hidden>'
            '<h2 tabindex="-1" id="inside">Title</h2><button data-control-id="save" '
            'onclick="document.getElementById(\'picker\').hidden=true;'
            'document.getElementById(\'opener\').focus()">Cancel</button></div>', True, "focusReturn")

    def test_product_heading_focus_is_not_reviewer_focus_even_in_a_function_named_apply(self):
        self.check_attempts('<button data-control-id="save" onclick="this.textContent+=\' changed\';apply()">Save</button>'
            '<script>function apply(){document.querySelector(\'[data-ui-surface="UI-002"] h1\').focus()}</script>', False)

    def test_historical_reviewers_keep_navigation_focus_separate(self):
        for runtime in historical_runtimes():
            driver = self.driver(edit=lambda html: html.replace('</body>', runtime
                + '<script>connectHifiReviewer()</script></body>'))
            for trigger in ("click", "keyboard"):
                with self.subTest(runtime=runtime[:80], trigger=trigger):
                    driver.call("open", page="index.html", timeoutMs=2000)
                    reply = driver.call("interact", page="index.html", surface="UI-001", state="ready", target="390",
                        control="to-details", kind="navigate", destination={"surface": "UI-002", "state": "ready"},
                        destinationPage="details.html", trigger=trigger, timeoutMs=2000)
                    self.assertEqual([], reply["result"]["problems"], reply)
                    self.assertTrue(reply["result"]["focusCorrect"], reply)
                    self.assertEqual([False, True], [event["reviewer"] for event in reply["events"]["focus"]])
            driver.stop()

    def test_a_page_the_operation_loads_keeps_its_own_initial_focus(self):
        driver = self.driver('<div tabindex="-1" id="thief">Unrelated</div><script>'
            'document.addEventListener("focusin",event=>{if(event.target.tagName==="H1")'
            'document.getElementById("thief").focus()})</script>')
        for trigger in ("click", "keyboard"):
            with self.subTest(trigger=trigger):
                driver.call("open", page="index.html", timeoutMs=2000)
                reply = driver.call("interact", page="index.html", surface="UI-001", state="ready", target="390",
                    control="to-details", kind="navigate", destination={"surface": "UI-002", "state": "ready"},
                    destinationPage="details.html", trigger=trigger, timeoutMs=2000)
                self.assertEqual([], reply["result"]["problems"], reply)
                self.assertTrue(reply["result"]["focusCorrect"], reply)
                self.assertEqual([False, True, False], [event["reviewer"] for event in reply["events"]["focus"]])
        driver.stop()

    def attempt_focus(self, markup, trigger):
        driver = self.driver(markup)
        result = self.attempt(driver, trigger=trigger)["result"]
        driver.stop()
        self.assertEqual([], result["problems"], result)
        return result

    def test_focus_may_follow_a_control_that_disappears_but_never_falls_to_the_page(self):
        cases = {
            "moves to the list": ('<div id="list" tabindex="-1"><button data-control-id="save" onclick="'
                'document.getElementById(\'list\').focus();this.remove()">Remove</button><p>Other item</p></div>', None),
            "moves to a new message": ('<button data-control-id="save" onclick="this.hidden=true;'
                'const note=document.getElementById(\'note\');note.hidden=false;note.focus()">Allow</button>'
                '<p id="note" tabindex="-1" hidden>Saved</p>', None),
            "falls to the page": ('<div id="list"><button data-control-id="save" onclick="this.remove()">Remove</button>'
                '<p>Other item</p></div>', "was lost"),
        }
        for label, (markup, problem) in cases.items():
            for trigger in ("click", "keyboard"):
                with self.subTest(case=label, trigger=trigger):
                    result = self.attempt_focus(markup, trigger)
                    self.assertEqual((problem is None, problem), (result["focusCorrect"], result["focusProblem"]), result)

    def test_focus_leaves_a_shown_control_only_for_content_the_activation_showed(self):
        cases = {
            "new note": ('<button data-control-id="save" onclick="this.textContent+=\' saved\';'
                'const note=document.getElementById(\'note\');note.hidden=false;note.focus()">Save</button>'
                '<p id="note" tabindex="-1" hidden>Saved</p>', None),
            "existing heading": ('<h2 id="title" tabindex="-1">Title</h2><button data-control-id="save" onclick="'
                'this.textContent+=\' saved\';document.getElementById(\'title\').focus()">Save</button>',
                "left the shown control for content that was already shown"),
        }
        for label, (markup, problem) in cases.items():
            for trigger in ("click", "keyboard"):
                with self.subTest(case=label, trigger=trigger):
                    result = self.attempt_focus(markup, trigger)
                    self.assertEqual((problem is None, problem), (result["focusCorrect"], result["focusProblem"]), result)

    def test_the_runtime_moves_focus_to_the_new_view_only_when_the_control_is_hidden(self):
        transition = "document.__hifiReviewerRuntime.selectState('loading')"
        cases = {"hidden with its view": ('<section data-hifi-state-view="ready" data-responsive-target="390">'
                                          '<button data-control-id="save" onclick="' + transition + '">Retry</button></section>', 2),
                 "still shown": ('<button data-control-id="save" onclick="' + transition + '">Retry</button>', 1)}
        for label, (markup, events) in cases.items():
            driver = self.driver(markup)
            for trigger in ("click", "keyboard"):
                with self.subTest(case=label, trigger=trigger):
                    reply = self.attempt(driver, kind="state", trigger=trigger,
                                         destination={"surface": "UI-002", "state": "loading"})
                    self.assertEqual(([], True), (reply["result"]["problems"], reply["result"]["focusCorrect"]), reply)
                    product = [event for event in reply["events"]["focus"] if not event["reviewer"]]
                    self.assertEqual(events, len(product), product)
            driver.stop()

    def test_a_closed_details_opens_through_its_summary(self):
        save = '<button data-control-id="save" onclick="this.textContent+=\' saved\'">Save</button>'
        hiding = '<style>details:not([open]) > nav { display: none }</style>'
        for markup in ('<details id="more"><summary>More</summary>' + save + '</details>',
                       hiding + '<details id="more"><summary>More</summary><nav>' + save + '</nav></details>'):
            for trigger in ("click", "keyboard"):
                with self.subTest(css=markup.startswith("<style>"), trigger=trigger):
                    result = self.attempt_focus(markup, trigger)
                    self.assertEqual((True, ["more"]), (result["focusCorrect"], result["observed"]["openers"]), result)
        # Without an id, the details is named by its place among the surface's details elements.
        result = self.attempt_focus('<details open><summary>Other</summary></details>'
                                    '<details><summary>More</summary>' + save + '</details>', "click")
        self.assertEqual((True, ["details:1"]), (result["focusCorrect"], result["observed"]["openers"]), result)


class FocusObservationTests(unittest.TestCase):
    def test_reviewer_focus_sites_require_exact_runtime_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            page = Path(temporary) / "index.html"
            for runtime in (runtime_source(), *historical_runtimes()):
                for changed in (False, True):
                    with self.subTest(changed=changed, runtime=runtime[:80]):
                        text = runtime.replace('heading.focus();', 'heading.focus(); /* altered */') if changed else runtime
                        page.write_text('<html>\n' + text + '</html>', encoding="utf-8")
                        self.assertEqual(not changed, bool(capture.reviewer_focus_sites({"index.html": page})))

    def test_focus_entry_is_optional_nonempty_and_excludes_a_return(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, manifest, _ = contract.materialize_hifi_bundle(Path(temporary))
            for observed, passes in (({}, True), ({"focusEntry": "picker"}, True),
                ({"focusEntry": ""}, False), ({"focusEntry": True}, False),
                ({"focusEntry": ["picker"]}, False), ({"focusEntry": "picker", "focusReturn": "picker"}, False)):
                with self.subTest(observed=observed):
                    output = contract.bundle_output(manifest)
                    output["interactions"][0]["observed"] = observed
                    self.assertEqual(passes, not checker._bundle_transcript_findings(output, manifest))


if __name__ == "__main__":
    unittest.main()

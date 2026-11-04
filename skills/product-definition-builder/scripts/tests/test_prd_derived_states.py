"""The optional `derivedStates` anchor of the PRD UI Surface Contract."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prd_ui_contract import derived_state_errors, parse_prd_ui_contract  # noqa: E402

STATES = "ready, confirm-discard, confirm-discard-loading, error:n/a — nothing to show"


def prd(derived=None, states=STATES, *, lines=None):
    anchor = [] if derived is None else ["- `derivedStates`: " + (derived if isinstance(derived, str) else json.dumps(derived))]
    return "\n".join([
        "<!-- ui-surface-contract:start -->",
        "### UI-001 — Editor",
        "- `route`: /editor",
        f"- `states`: {states}",
        *anchor,
        *(lines or []),
        "- `responsive`: viewports: 390, 768, 1200",
        "- `copy`: approved",
        "<!-- ui-surface-contract:end -->",
        "",
    ])


def parse(text):
    return parse_prd_ui_contract(text, require_responsive=True, require_copy=True, web_floor=3)


class DerivedStatesTests(unittest.TestCase):
    def test_surface_without_the_anchor_has_no_derived_states(self):
        entries, errors = parse(prd())
        self.assertEqual([], errors)
        self.assertEqual({}, entries["UI-001"]["derivedStates"])

    def test_derived_state_of_a_live_parent_parses(self):
        entries, errors = parse(prd({"confirm-discard-loading": "confirm-discard"}))
        self.assertEqual([], errors)
        self.assertEqual({"confirm-discard-loading": "confirm-discard"}, entries["UI-001"]["derivedStates"])
        self.assertIn("confirm-discard-loading", entries["UI-001"]["states"])

    def test_chain_of_derived_states_is_allowed(self):
        chain = {"confirm-discard": "ready", "confirm-discard-loading": "confirm-discard"}
        entries, errors = parse(prd(chain))
        self.assertEqual([], errors)
        self.assertEqual(chain, entries["UI-001"]["derivedStates"])

    def test_unknown_parent_fails(self):
        _, errors = parse(prd({"confirm-discard-loading": "missing"}))
        self.assertTrue(any("unknown or n/a parent 'missing'" in error for error in errors), errors)

    def test_na_parent_fails(self):
        _, errors = parse(prd({"confirm-discard-loading": "error"}))
        self.assertTrue(any("unknown or n/a parent 'error'" in error for error in errors), errors)

    def test_derived_state_must_be_a_live_state_of_the_surface(self):
        for child in ("not-listed", "error"):
            with self.subTest(child=child):
                _, errors = parse(prd({child: "ready"}))
                self.assertTrue(any(f"derived state {child!r} must be a non-n/a state" in error for error in errors), errors)

    def test_cycles_fail_once_each(self):
        for derived in ({"ready": "ready"},
                        {"confirm-discard": "confirm-discard-loading", "confirm-discard-loading": "confirm-discard"},
                        {"ready": "confirm-discard", "confirm-discard": "confirm-discard-loading",
                         "confirm-discard-loading": "ready"}):
            with self.subTest(derived=derived):
                _, errors = parse(prd(derived))
                self.assertEqual(1, sum("form a cycle" in error for error in errors), errors)

    def test_tail_into_a_cycle_reports_the_cycle_only(self):
        derived = {"ready": "confirm-discard", "confirm-discard": "confirm-discard-loading",
                   "confirm-discard-loading": "confirm-discard"}
        problems = derived_state_errors(derived, ["ready", "confirm-discard", "confirm-discard-loading"])
        self.assertEqual(["derived states form a cycle: confirm-discard -> confirm-discard-loading -> confirm-discard"],
                         problems)

    def test_malformed_values_fail(self):
        for value in ("confirm-discard-loading: confirm-discard", "[]", "{}", '{"a": 1}', "[\"a\"]"):
            with self.subTest(value=value):
                _, errors = parse(prd(value))
                self.assertTrue(any("`derivedStates`" in error for error in errors), (value, errors))

    def test_second_anchor_fails(self):
        text = prd({"confirm-discard-loading": "confirm-discard"},
                   lines=['- `derivedStates`: {"confirm-discard": "ready"}'])
        _, errors = parse(text)
        self.assertTrue(any("at most one `derivedStates` anchor" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()

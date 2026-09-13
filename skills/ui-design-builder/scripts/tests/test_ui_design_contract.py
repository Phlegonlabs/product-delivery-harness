"""Tests for the UI design contract checker."""

import importlib
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

checker = importlib.import_module("check_ui_design_contract")


def contract(*, wireframe="approved", visual="approved", author="frontend-design"):
    return f"""# UI Design Contract

## Source Product Definition

PRD source: docs/product/PRD.md @ abc
Architecture source: docs/product/architecture.md @ def
Stack source: docs/product/stack-decisions.md @ ghi
Product Definition Approval: approved — Owner, 2026-09-13
Stack Decision Checkpoint: approved — Owner, 2026-09-13

## UI Design Intake

Decision owner: Product owner
Decided on: 2026-09-13
Visual Preference Brief: Precise, calm, information-dense UI; avoid generic cards
Direction mode: one recommended direction

## Motion And Media Intent

Motion direction: functional_only — Product owner

| Intent ID | UI scope / region | Treatment | Purpose and trigger | Static / reduced-motion fallback | Generation route | Status |
| --- | --- | --- | --- | --- | --- | --- |
| MM-001 | UI-001 / hero | motion | Explain data flow on entry | Static diagram | CSS-WAAPI | approved |

## Wireframe Approval

Wireframe: docs/design/wireframes.html @ 0123
Frozen PRD basis: docs/product/PRD.md @ abc
Copy Freeze: approved
Copy owner: Product owner
Copy locale: en-US
Copy approved on: 2026-09-13
Responsive browser check: passed complete matrix
UI grading: W1 90 W2 90 W3 90 W4 90 W5 90 overall 90
Wireframe score: 90
Wireframe lowest dimension: 90
Wireframe blocks: none
Decision: {wireframe}
Decision owner: Product owner
Decided on: 2026-09-13

## Style Integration

Design author: {author}
Selected direction: VD-R1-01 precise operations
Direction decision: approved
Direction decision owner: Product owner
Direction decided on: 2026-09-13
Candidate theme: blue-gray palette, sans type, compact rhythm
Connected HiFi reference: docs/design/ui-references/run-1/index.html @ 4567

## HiFi Review

Impeccable critique: completed 32/40 with no blocking finding
Impeccable audit: completed 18/20 with no blocking finding
UI grading: H1-H9 overall 94; H2 95; H4 94; H8 96; no block or dispute
HiFi score: 94
H2 score: 95
H4 score: 94
H8 score: 96
HiFi lowest dimension: 88
HiFi blocks or disputes: none

## Visual Approval

Decision: {visual}
Decision owner: Product owner
Decided on: 2026-09-13
Approved target: docs/design/ui-references/run-1/index.html @ 4567; all routes and states

## Design System Need Gate

Decision: not_required
Decision owner: Product owner
Reason: One surface with a binding all-screens target
Replacement visual contract when not_required: approved target, ui-design.md, wireframes.html, PRD.md
"""


class UiDesignContractTests(unittest.TestCase):
    def test_complete_visual_contract_passes(self):
        self.assertEqual(
            [],
            checker.validate_text(
                contract(),
                require_filled=True,
                require_wireframe_approved=True,
                require_visual_approved=True,
            ),
        )

    def test_wireframe_approval_is_human_and_approved(self):
        problems = checker.validate_text(
            contract(wireframe="blocked").replace(
                "Decision owner: Product owner\nDecided on: 2026-09-13\n\n## Style Integration",
                "Decision owner: AI\nDecided on: later\n\n## Style Integration",
                1,
            ),
            require_filled=True,
            require_wireframe_approved=True,
        )
        joined = "\n".join(problems)
        self.assertIn("Wireframe Approval Decision must be approved", joined)
        self.assertIn("Decision owner must be human", joined)
        self.assertIn("must use YYYY-MM-DD", joined)

    def test_wireframe_approval_requires_copy_freeze_first(self):
        candidate = (
            contract()
            .replace("Copy Freeze: approved", "Copy Freeze: draft")
            .replace("Copy owner: Product owner", "Copy owner: AI")
            .replace("Copy locale: en-US", "Copy locale: not a locale")
            .replace("Copy approved on: 2026-09-13", "Copy approved on: later")
        )
        joined = "\n".join(
            checker.validate_text(candidate, require_wireframe_approved=True)
        )
        self.assertIn("Copy Freeze must be approved", joined)
        self.assertIn("Copy owner must be human", joined)
        self.assertIn("Copy locale must be a BCP 47 locale", joined)
        self.assertIn("Copy approved on must use YYYY-MM-DD", joined)

    def test_visual_contract_requires_frontend_design_and_impeccable(self):
        candidate = contract(author="design-taste-frontend").replace(
            "Impeccable critique: completed 32/40 with no blocking finding\n",
            "",
        )
        joined = "\n".join(
            checker.validate_text(candidate, require_visual_approved=True)
        )
        self.assertIn("Design author must be frontend-design", joined)
        self.assertIn("missing 'Impeccable critique'", joined)

    def test_visual_contract_requires_human_direction_selection(self):
        candidate = (
            contract()
            .replace("Direction decision: approved", "Direction decision: rejected")
            .replace("Direction decision owner: Product owner", "Direction decision owner: AI")
        )
        joined = "\n".join(
            checker.validate_text(candidate, require_visual_approved=True)
        )
        self.assertIn("Direction decision is not approved", joined)
        self.assertIn("Direction decision owner must be human", joined)

    def test_duplicate_approval_fields_are_rejected(self):
        candidate = contract().replace(
            "Decision: approved\nDecision owner: Product owner\nDecided on: 2026-09-13\nApproved target:",
            "Decision: approved\nDecision: revision_requested\n"
            "Decision owner: Product owner\nDecided on: 2026-09-13\nApproved target:",
        )
        joined = "\n".join(
            checker.validate_text(candidate, require_visual_approved=True)
        )
        self.assertIn("Visual Approval has duplicate 'Decision' fields", joined)

    def test_motion_treatment_is_closed(self):
        candidate = contract().replace("| motion |", "| cinematic |")
        joined = "\n".join(checker.validate_text(candidate, require_filled=True))
        self.assertIn("invalid treatment", joined)

    def test_blocked_motion_intent_fails(self):
        candidate = contract().replace("| CSS-WAAPI | approved |", "| CSS-WAAPI | blocked |")
        joined = "\n".join(checker.validate_text(candidate, require_filled=True))
        self.assertIn("remains blocked", joined)

    def test_scores_enforce_wireframe_and_hifi_thresholds(self):
        candidate = (
            contract()
            .replace("Wireframe score: 90", "Wireframe score: 79")
            .replace("H4 score: 94", "H4 score: 89")
            .replace("HiFi blocks or disputes: none", "HiFi blocks or disputes: H7 disputed")
        )
        joined = "\n".join(
            checker.validate_text(
                candidate,
                require_wireframe_approved=True,
                require_visual_approved=True,
            )
        )
        self.assertIn("Wireframe score must be an integer from 80 to 100", joined)
        self.assertIn("H4 score must be an integer from 90 to 100", joined)
        self.assertIn("HiFi blocks or disputes must be none", joined)

    def test_literal_brackets_inside_a_filled_value_are_allowed(self):
        candidate = contract().replace(
            "Plain synthetic fixture UI",
            "Use the existing [Human] review label in the connected UI",
        )
        self.assertEqual([], checker.validate_text(candidate, require_filled=True))


if __name__ == "__main__":
    unittest.main()

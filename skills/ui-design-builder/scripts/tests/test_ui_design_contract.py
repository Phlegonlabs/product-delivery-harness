"""Tests for the UI design contract checker."""

import importlib
import hashlib
import json
import sys
import unittest
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

checker = importlib.import_module("check_ui_design_contract")

A_HASH = hashlib.sha256(b"prd").hexdigest()
B_HASH = hashlib.sha256(b"architecture").hexdigest()
C_HASH = hashlib.sha256(b"stack").hexdigest()
D_HASH = hashlib.sha256(b"wireframes").hexdigest()
E_HASH = hashlib.sha256(b"hifi").hexdigest()
U_HASH = hashlib.sha256(b"ui-design").hexdigest()
EVIDENCE_HASH = "e" * 64


def contract(*, wireframe="approved", visual="approved", author="frontend-design"):
    return f"""# UI Design Contract

## Source Product Definition

PRD source: docs/product/PRD.md @ sha256:{A_HASH}
Architecture source: docs/product/architecture.md @ sha256:{B_HASH}
Stack source: docs/product/stack-decisions.md @ sha256:{C_HASH}
Product Definition Approval: approved
Stack Decision Checkpoint: approved

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

Wireframe: docs/design/wireframes.html @ sha256:{D_HASH}
Frozen PRD basis: docs/product/PRD.md @ sha256:{A_HASH}
Copy Freeze: approved
Copy owner: Product owner
Copy locale: en-US
Copy approved on: 2026-09-13
Responsive browser check: PASS — evidence=docs/evidence/wireframe-browser.json @ sha256:{EVIDENCE_HASH}; scope=complete matrix
UI grading: PASS — evidence=docs/evidence/wireframe-grading.json @ sha256:{EVIDENCE_HASH}; scope=W1-W5 overall 90
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
Connected HiFi reference: docs/design/ui-references/run-1/index.html @ sha256:{E_HASH}

## HiFi Review

Impeccable critique: PASS — evidence=docs/evidence/impeccable-critique.json @ sha256:{EVIDENCE_HASH}; scope=32/40 no blocking finding
Impeccable audit: PASS — evidence=docs/evidence/impeccable-audit.json @ sha256:{EVIDENCE_HASH}; scope=18/20 no blocking finding
UI grading: PASS — evidence=docs/evidence/hifi-grading.json @ sha256:{EVIDENCE_HASH}; scope=H1-H9 overall 94; H2 95; H4 94; H8 96; no block or dispute
HiFi browser check: PASS — evidence=docs/evidence/hifi-browser.json @ sha256:{EVIDENCE_HASH}; scope=complete page, state, and target matrix
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
Approved target: docs/design/ui-references/run-1/index.html @ sha256:{E_HASH}; scope=all routes and states, web targets 390/768/1200

## Design System Need Gate

Decision: not_required
Decision owner: Product owner
Decided on: 2026-09-13
Reason: One surface with a binding all-screens target
Replacement visual contract when not_required: target=docs/design/ui-references/run-1/index.html @ sha256:{E_HASH}; ui-design=docs/design/ui-design.md @ sha256:{U_HASH}; wireframe=docs/design/wireframes.html @ sha256:{D_HASH}; prd=docs/product/PRD.md @ sha256:{A_HASH}
"""

def wireframe_html(data: object) -> str:
    return (
        '<script id="wireframe-data" type="application/json">'
        + json.dumps(data)
        + "</script>"
    )


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
        self.assertIn("must be a real YYYY-MM-DD date", joined)

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
        self.assertIn("Copy approved on must be a real YYYY-MM-DD date", joined)

    def test_visual_contract_requires_frontend_design_and_impeccable(self):
        candidate = contract(author="design-taste-frontend").replace(
            f"Impeccable critique: PASS — evidence=docs/evidence/impeccable-critique.json @ sha256:{EVIDENCE_HASH}; scope=32/40 no blocking finding\n",
            "",
        )
        joined = "\n".join(
            checker.validate_text(candidate, require_visual_approved=True)
        )
        self.assertIn("Design author must be frontend-design", joined)
        self.assertIn("missing 'Impeccable critique'", joined)

    def test_inactive_markdown_does_not_create_approvals(self):
        candidate = contract().replace(
            "Decision: approved\nDecision owner: Product owner\nDecided on: 2026-09-13\nApproved target:",
            "Decision: approved\nDecision owner: Product owner\nDecided on: 2026-09-13\nApproved target:",
        )
        candidate = candidate.replace(
            "## Visual Approval",
            "<!--\n## Hidden Visual Approval\nDecision: blocked\nDecision owner: AI\nDecided on: 2026-09-13\n-->\n## Visual Approval",
        )
        joined = "\n".join(checker.validate_text(candidate, require_visual_approved=True))
        self.assertNotIn("Visual Approval has duplicate 'Decision' fields", joined)
        self.assertNotIn("Visual Approval Decision must be approved", joined)

    def test_fake_and_inactive_evidence_are_rejected(self):
        candidate = contract().replace(
            "Responsive browser check: PASS", "Responsive browser check: passed"
        )
        candidate = candidate.replace(
            "Impeccable audit: PASS", "<!-- Impeccable audit: PASS -->\nImpeccable audit: not run"
        )
        joined = "\n".join(checker.validate_text(candidate, require_visual_approved=True))
        self.assertIn("Responsive browser check must use", joined)
        self.assertIn("Impeccable audit verdict must use", joined)

    def test_design_system_gate_alternatives_are_exclusive(self):
        required = contract(visual="approved").replace(
            "Decision: not_required", "Decision: required"
        )
        joined = "\n".join(checker.validate_text(required, require_visual_approved=True))
        self.assertIn("missing exactly one compiled pair field", joined)

        both = required.replace(
            "Reason: One surface",
            "Compiled design system pair: docs/design/design-system.md @ "
            + "f" * 64
            + " and docs/design/design-system.json @ "
            + "0" * 64
            + "\nReason: One surface",
        )
        joined = "\n".join(checker.validate_text(both, require_visual_approved=True))
        self.assertIn("must not name a not_required replacement", joined)

    def test_connected_hifi_must_match_approved_target(self):
        candidate = contract().replace(
            "Approved target: docs/design/ui-references/run-1/index.html @ sha256:" + E_HASH,
            "Approved target: docs/design/ui-references/run-2/index.html @ sha256:" + ("f" * 64),
        )
        problems = checker.validate_text(candidate, require_visual_approved=True)
        self.assertTrue(any("Connected HiFi reference must exactly match" in item for item in problems))

    def test_not_required_replacement_is_structured_and_exact(self):
        candidate = contract().replace(
            "Replacement visual contract when not_required: target=docs/design/ui-references/run-1/index.html @ sha256:" + E_HASH,
            "Replacement visual contract when not_required: approved target, ui-design.md, wireframes.html, PRD.md",
        )
        problems = checker.validate_text(candidate, require_visual_approved=True)
        self.assertTrue(any("must contain exactly target, ui-design, wireframe, and prd" in item for item in problems))

    def test_structured_pass_requires_hashed_evidence(self):
        candidate = contract().replace(
            "Responsive browser check: PASS — evidence=docs/evidence/wireframe-browser.json @ sha256:" + EVIDENCE_HASH + "; scope=complete matrix",
            "Responsive browser check: PASS — complete matrix",
        )
        problems = checker.validate_text(candidate, require_wireframe_approved=True)
        self.assertTrue(any("Responsive browser check must use" in item for item in problems))

    def test_motion_join_rejects_missing_duplicate_and_mismatch(self):
        intent = {
            "id": "MM-001",
            "scope": "UI-001 / screen",
            "treatment": "motion",
            "purpose": "Explain data flow on entry",
            "trigger": "on entry",
            "reducedMotionFallback": "Static diagram",
            "generationRoute": "CSS-WAAPI",
            "draftPrompt": "A restrained data-flow motion placeholder",
            "source": "owner decision",
            "generationStatus": "deferred",
        }
        row = {"MM-001": intent}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "wireframes.html"
            path.write_text(
                wireframe_html({"schema": "wireframes/4", "screens": []}),
                encoding="utf-8",
            )
            problems = []
            checker._join_motion_intents(row, path, problems=problems)
            self.assertTrue(any("has no wireframe mediaIntent" in item for item in problems))

            path.write_text(
                wireframe_html(
                    {"schema": "wireframes/4", "screens": [{"id": "UI-001", "mediaIntent": intent}]}
                ),
                encoding="utf-8",
            )
            self.assertIsNone(checker._join_motion_intents(row, path, problems=[]))

            path.write_text(
                wireframe_html(
                    {
                        "schema": "wireframes/4",
                        "screens": [
                            {"id": "UI-001", "mediaIntent": intent},
                            {"id": "UI-002", "mediaIntent": intent},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            problems = []
            checker._join_motion_intents(row, path, problems=problems)
            self.assertTrue(any("duplicate wireframe mediaIntents" in item for item in problems))

            mismatched = dict(intent, generationRoute="GSAP")
            path.write_text(
                wireframe_html(
                    {"schema": "wireframes/4", "screens": [{"id": "UI-001", "mediaIntent": mismatched}]}
                ),
                encoding="utf-8",
            )
            problems = []
            checker._join_motion_intents(row, path, problems=problems)
            self.assertTrue(any("route authority differs" in item for item in problems))

            path.write_text(
                wireframe_html(
                    {"schema": "wireframes/4", "screens": [{"id": "UI-001", "mediaIntent": intent}]}
                ),
                encoding="utf-8",
            )
            problems = []
            checker._join_motion_intents({}, path, problems=problems)
            self.assertTrue(any("has no Motion And Media Intent row" in item for item in problems))

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
        self.assertIn("has invalid status", joined)

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

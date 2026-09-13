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

| Intent ID | UI scope / region | Treatment | Purpose | Trigger | Draft prompt | Source | Static / reduced-motion fallback | Generation route | Status | Generation status |
| --- | --- | --- | --- | --- | --- | --- |
| MM-001 | UI-001 / hero | motion | Explain data flow | on entry | A restrained data-flow motion placeholder | owner decision | Static diagram | CSS-WAAPI | approved | deferred |

## Wireframe Approval

Wireframe: docs/design/wireframes.html @ sha256:{D_HASH}
Frozen PRD basis: docs/product/PRD.md @ sha256:{A_HASH}
Copy Freeze: approved
Copy owner: Product owner
Copy locale: en-US
Copy approved on: 2026-09-13
Responsive surface check: PASS — evidence=docs/evidence/wireframe-browser.json @ sha256:{EVIDENCE_HASH}
UI grading: PASS — evidence=docs/evidence/wireframe-grading.json @ sha256:{EVIDENCE_HASH}
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

Impeccable critique: PASS — evidence=docs/evidence/impeccable-critique.json @ sha256:{EVIDENCE_HASH}
Impeccable audit: PASS — evidence=docs/evidence/impeccable-audit.json @ sha256:{EVIDENCE_HASH}
UI grading: PASS — evidence=docs/evidence/hifi-grading.json @ sha256:{EVIDENCE_HASH}
HiFi surface check: PASS — evidence=docs/evidence/hifi-browser.json @ sha256:{EVIDENCE_HASH}
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
Approved target: docs/design/ui-references/run-1/index.html @ sha256:{E_HASH}; scope=surfaces=[{{"id":"UI-001","route":"/home","states":["ready"]}}]|routes=["/home"]|states=["ready"]|responsive={{"kind":"viewports","targets":[390,768,1200]}}|tolerance="exact"|allowedDeviations=[]|captureMode=hosted-browser

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
            f"Impeccable critique: PASS — evidence=docs/evidence/impeccable-critique.json @ sha256:{EVIDENCE_HASH}\n",
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
            "Responsive surface check: PASS", "Responsive surface check: passed"
        )
        candidate = candidate.replace(
            "Impeccable audit: PASS", "<!-- Impeccable audit: PASS -->\nImpeccable audit: not run"
        )
        joined = "\n".join(checker.validate_text(candidate, require_visual_approved=True))
        self.assertIn("Responsive surface check must use", joined)
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
            "Responsive surface check: PASS — evidence=docs/evidence/wireframe-browser.json @ sha256:" + EVIDENCE_HASH,
            "Responsive surface check: PASS — complete matrix",
        )
        problems = checker.validate_text(candidate, require_wireframe_approved=True)
        self.assertTrue(any("Responsive surface check must use" in item for item in problems))

    def test_evidence_json_binds_check_artifact_and_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "wireframes.html"
            artifact.write_text("wireframe", encoding="utf-8")
            output = root / "output.txt"
            output.write_text("PASS output", encoding="utf-8")
            evidence = {
                "schema": "ui-evidence/2",
                "check": "wireframe-browser",
                "result": "PASS",
                "reviewedArtifact": {
                    "path": "wireframes.html",
                    "sha256": hashlib.sha256(b"wireframe").hexdigest(),
                },
                "receipt": {
                    "tool": "playwright",
                    "method": "browser-matrix",
                    "matrix": {"surfaces": ["UI-001"], "states": ["ready"], "targets": ["390"]},
                    "results": [{"case": "UI-001/ready/390", "result": "PASS"}],
                    "outputArtifact": {
                        "path": "output.txt",
                        "sha256": hashlib.sha256(b"PASS output").hexdigest(),
                    },
                    "executedAt": "2020-01-01T00:00:00Z",
                },
                "attestation": "human-attested",
                "owner": "Product owner",
            }
            evidence_path = root / "evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            line = "PASS — evidence=evidence.json @ sha256:" + hashlib.sha256(evidence_path.read_bytes()).hexdigest()
            problems: list[str] = []
            checker._resolve_evidence(
                line,
                repo_root=root,
                label="Responsive surface check",
                expected_artifact="wireframes.html",
                problems=problems,
            )
            self.assertEqual([], problems)
            reused: list[str] = []
            checker._resolve_evidence(
                line,
                repo_root=root,
                label="HiFi surface check",
                expected_artifact="wireframes.html",
                problems=reused,
            )
            self.assertTrue(any("check must be hifi-browser" in item for item in reused))

    def test_hifi_surface_rejects_external_and_network_surfaces(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "hifi.html"
            path.write_text("<html><body><nav>Pages</nav><main><h1>HiFi review surface</h1></main></body></html>", encoding="utf-8")
            problems: list[str] = []
            checker._validate_hifi_surface(path, problems)
            self.assertEqual([], problems)
            path.write_text(
                '<base href="https://example.test/"><script>fetch("https://example.test")</script>',
                encoding="utf-8",
            )
            problems = []
            checker._validate_hifi_surface(path, problems)
            self.assertTrue(any("active external or executable" in item for item in problems))

    def test_motion_join_rejects_missing_duplicate_and_mismatch(self):
        intent = {
            "id": "MM-001",
            "scope": "UI-001 / screen",
            "treatment": "motion",
            "purpose": "Explain data flow",
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

            region_intent = dict(intent, scope="UI-001 / hero")
            path.write_text(
                wireframe_html(
                    {
                        "schema": "wireframes/4",
                        "screens": [{"id": "UI-001", "regions": [{"id": "hero", "mediaIntent": region_intent}]}],
                    }
                ),
                encoding="utf-8",
            )
            self.assertIsNone(checker._join_motion_intents({"MM-001": region_intent}, path, problems=[]))

            path.write_text(
                wireframe_html(
                    {
                        "schema": "wireframes/4",
                        "screens": [{"id": "UI-001", "regions": [{"id": "hero", "elements": [{"mediaIntent": intent}]}]}],
                    }
                ),
                encoding="utf-8",
            )
            problems = []
            checker._join_motion_intents(row, path, problems=problems)
            self.assertTrue(any("attached directly" in item for item in problems))

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

    def test_direction_and_motion_enums_are_closed_and_human_owned(self):
        candidate = (
            contract()
            .replace("Direction mode: one recommended direction", "Direction mode: recommend")
            .replace("Motion direction: functional_only — Product owner", "Motion direction: recommend — AI")
        )
        joined = "\n".join(checker.validate_text(candidate, require_filled=True))
        self.assertIn("Direction mode must be one of", joined)
        self.assertIn("Motion direction must be one of", joined)
        self.assertIn("Motion direction must include a human owner", joined)

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

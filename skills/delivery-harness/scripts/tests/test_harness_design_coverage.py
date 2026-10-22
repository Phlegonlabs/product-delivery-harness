"""Focused regressions for separate product states and design coverage."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.append(str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

from manifest_fixtures import manifest_markdown  # noqa: E402
from harness_contract_join import (  # noqa: E402
    _strict_ui_surface_errors,
    validate_plan_prd_text,
)
from harness_design_coverage import DESIGN_COVERAGE_SCHEMA  # noqa: E402
from harness_manifest import _validate_plan_ui_surfaces  # noqa: E402
import harness_ui_evidence as evidence  # noqa: E402
import parity_capture as capture  # noqa: E402


STATE_MATRIX = [
    "ready",
    "submitting",
    "invalid_url",
    "rate_limited",
    "challenge_failed",
    "running",
    "summary",
    "partial",
    "blocked",
    "unreachable",
    "email_invalid",
    "system_error",
    "link_copied",
    "mail_scheduled",
    "mail_duplicate",
    "mail_limited",
    "long-content",
    "reduced-motion",
    "mobile-reflow",
]
CONDITIONS = ["long-content", "reduced-motion", "mobile-reflow"]
UNSET_COVERAGE = object()


def excluded_states(active: list[str]) -> list[dict[str, str]]:
    return [
        {
            "state": state,
            "reason": f"{state} is not a product state on this surface",
        }
        for state in STATE_MATRIX
        if state not in CONDITIONS and state not in active
    ]


def design_coverage(active: list[str], base: str) -> dict[str, object]:
    return {
        "schema": DESIGN_COVERAGE_SCHEMA,
        "conditions": [
            {"id": condition, "base_state": base} for condition in CONDITIONS
        ],
        "not_applicable": excluded_states(active),
    }


def surface(
    surface_id: str,
    active: list[str],
    base: str,
    *,
    coverage: object = UNSET_COVERAGE,
) -> dict[str, object]:
    result = {
        "id": surface_id,
        "trace_ids": ["REQ-001"],
        "route": f"/{surface_id.lower()}",
        "breakpoints": ["390", "1200"],
        "states": active,
        "evidence_gate": "required",
    }
    if coverage is UNSET_COVERAGE or coverage is True:
        result["design_coverage"] = design_coverage(active, base)
    elif coverage is not False:
        result["design_coverage"] = coverage
    return result


def realistic_surfaces() -> list[dict[str, object]]:
    return [
        surface(
            "UI-001",
            ["ready", "submitting", "invalid_url", "rate_limited", "challenge_failed"],
            "ready",
        ),
        surface(
            "UI-002",
            [
                "running",
                "summary",
                "partial",
                "blocked",
                "unreachable",
                "email_invalid",
                "system_error",
            ],
            "summary",
        ),
        surface(
            "UI-003",
            [
                "ready",
                "link_copied",
                "mail_scheduled",
                "mail_duplicate",
                "mail_limited",
            ],
            "ready",
        ),
        surface("UI-004", ["ready"], "ready"),
        surface("UI-005", ["ready"], "ready"),
    ]


def complete_registry(state_matrix: list[str] | None = None) -> dict[str, object]:
    return {
        "schema": "design-system/1",
        "product": "Fixture Product",
        "platform": "web",
        "stylingMechanism": "plain CSS",
        "enforcement": "blocking",
        "tokenSources": ["src/styles/tokens.css"],
        "primitiveSources": [],
        "tokens": {},
        "primitives": {},
        "productComponents": {},
        "signatureRules": [],
        "motionVariants": [],
        "viewports": [390, 1200],
        "stateMatrix": state_matrix or STATE_MATRIX,
    }


class DesignCoverageValidationTests(unittest.TestCase):
    def test_realistic_conjunction_passes_unequal_product_states(self) -> None:
        errors = evidence.validate_ui_surface_design_registry(
            {"ui_surfaces": realistic_surfaces()}, complete_registry()
        )
        self.assertEqual([], errors)

    def test_missing_and_extra_product_states_fail_both_frozen_joins(self) -> None:
        surfaces = [surface("UI-004", ["ready"], "ready")]
        surfaces[0]["states"] = ["submitting"]
        plan = {"ui_surfaces": surfaces}
        coverage_errors = evidence.validate_ui_surface_design_registry(
            plan, complete_registry()
        )
        self.assertTrue(any("omits state ready" in error for error in coverage_errors))
        self.assertTrue(any("not an active product state" in error for error in coverage_errors))

        prd = (
            "<!-- ui-surface-contract:start -->\n"
            "## UI Surface Contract\n\n### UI-004 — Privacy\n\n"
            "- `route`: /ui-004\n"
            "- `states`: ready\n"
            "- `responsive`: viewports: 390, 1200\n"
            "<!-- ui-surface-contract:end -->\n"
        )
        prd_errors = validate_plan_prd_text(plan, prd)
        target_errors = _strict_ui_surface_errors(
            plan,
            {
                "target_scope": {
                    "surfaces": [
                        {
                            "id": "UI-004",
                            "route": "/ui-004",
                            "states": ["ready"],
                        }
                    ]
                },
                "responsive": {"kind": "viewports", "targets": [390, 1200]},
                "capture_mode": "hosted-browser",
            },
        )
        self.assertTrue(any("states" in error for error in prd_errors))
        self.assertTrue(any("states differ" in error for error in target_errors))

    def test_unknown_missing_duplicate_conflict_inactive_base_and_universal_fail(self) -> None:
        cases = [
            (
                "missing",
                surface("UI-004", ["ready"], "ready"),
                lambda value: value["not_applicable"].pop(),
                "omits state",
            ),
            (
                "unknown",
                surface("UI-004", ["ready"], "ready"),
                lambda value: value["not_applicable"].append(
                    {"state": "offline", "reason": "Not in the matrix"}
                ),
                "unknown design-system states",
            ),
            (
                "duplicate",
                surface("UI-004", ["ready"], "ready"),
                lambda value: value["not_applicable"].append(
                    dict(value["not_applicable"][0])
                ),
                "duplicates",
            ),
            (
                "conflict",
                surface("UI-004", ["ready"], "ready"),
                lambda value: value["not_applicable"].append(
                    {"state": "reduced-motion", "reason": "This deliberately conflicts with the applicable condition"}
                ),
                "conditions and exclusions conflict",
            ),
            (
                "inactive-base",
                surface("UI-004", ["ready"], "ready"),
                lambda value: value["conditions"][0].update(base_state="submitting"),
                "is not an active product state",
            ),
            (
                "universal-exclusion",
                surface("UI-004", ["ready"], "ready"),
                lambda value: (
                    value["conditions"].pop(1),
                    value["not_applicable"].append(
                        {"state": "reduced-motion", "reason": "Owner exclusion"}
                    ),
                ),
                "required universal condition",
            ),
        ]
        for label, value, mutate, expected in cases:
            with self.subTest(case=label):
                mutate(value["design_coverage"])
                errors = evidence.validate_ui_surface_design_registry(
                    {"ui_surfaces": [value]}, complete_registry()
                )
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_manifest_parser_accepts_the_versioned_field_and_rejects_shape_errors(self) -> None:
        plan = {"traces": {"REQ-001": {"disposition": "planned"}}}
        valid = surface("UI-004", ["ready"], "ready")
        errors: list[str] = []
        _validate_plan_ui_surfaces(errors, {"ui_surfaces": [valid]}, plan["traces"])
        self.assertEqual([], errors)

        valid["design_coverage"]["schema"] = "ui-design-coverage/2"
        shape_errors: list[str] = []
        _validate_plan_ui_surfaces(
            shape_errors, {"ui_surfaces": [valid]}, plan["traces"]
        )
        self.assertTrue(any("must equal" in error for error in shape_errors))


class DesignCoverageEvidenceTests(unittest.TestCase):
    def evidence_item(
        self,
        surface_id: str,
        state: str,
        head: str,
    ) -> dict[str, object]:
        return {
            "surface_id": surface_id,
            "route": f"/{surface_id.lower()}",
            "breakpoint": "390",
            "state": state,
            "artifact_path": f"docs/goal/evidence/{surface_id}-{state}.png",
            "artifact_sha256": "a" * 64,
            "head_sha": head,
            "status": "PASS",
            "target_comparison": {
                "baseline": "design_system",
                "baseline_artifact": "check_ui_contract:clean-run",
                "verdict": "pass", "differences": [], "evidence": "fixture parity",
            },
        }

    def test_conditions_are_members_and_exclusions_make_no_screenshots(self) -> None:
        plan_surface = surface("UI-004", ["ready"], "ready")
        plan_surface["breakpoints"] = ["390"]
        plan = {"ui_surfaces": [plan_surface]}
        head = "b" * 40
        states = ["ready", *CONDITIONS]
        run = {
            "schema_version": 11,
            "status": "complete",
            "integration": {"integration_head_sha": head},
            "ui_evidence": [
                self.evidence_item("UI-004", state, head) for state in states
            ],
        }
        errors: list[str] = []
        evidence._validate_ui_evidence(errors, plan, run)
        self.assertEqual([], errors)

        projected = evidence.surface_capture_rows(plan["ui_surfaces"][0])[0]
        self.assertEqual(
            {(surface["id"], state) for surface in [plan["ui_surfaces"][0]] for state in states},
            {(row["surface_id"], row["state"]) for row in projected},
        )
        self.assertNotIn("submitting", {row["state"] for row in projected})

    def test_omitted_condition_screenshot_fails_completeness(self) -> None:
        plan_surface = surface("UI-004", ["ready"], "ready")
        plan_surface["breakpoints"] = ["390"]
        plan = {"ui_surfaces": [plan_surface]}
        head = "c" * 40
        run = {
            "schema_version": 11,
            "status": "complete",
            "integration": {"integration_head_sha": head},
            "ui_evidence": [
                self.evidence_item("UI-004", state, head)
                for state in ["ready", "long-content", "mobile-reflow"]
            ],
        }
        errors: list[str] = []
        evidence._validate_ui_evidence(errors, plan, run)
        self.assertTrue(any("reduced-motion" in error for error in errors), errors)

    def test_absent_field_retains_legacy_projection(self) -> None:
        legacy = surface("UI-004", ["ready", "submitting"], "ready", coverage=False)
        legacy["breakpoints"] = ["390"]
        rows, errors = evidence.surface_capture_rows(legacy)
        self.assertEqual([], errors)
        self.assertEqual(["ready", "submitting"], [row["state"] for row in rows])


class DesignCoverageCaptureTests(unittest.TestCase):
    def test_shoot_establishes_base_state_before_condition(self) -> None:
        calls: list[tuple[str, str | None]] = []

        def browser(cli: list[str], argv: list[str], *, stdin: str | None = None, timeout: int = 90):
            if argv[:1] == ["eval"]:
                calls.append((stdin or "", argv[0]))
            return mock.Mock(returncode=0, stdout="true", stderr="")

        with mock.patch.object(capture, "_run_browser", side_effect=browser):
            errors = capture._shoot(
                ["browser"],
                viewport=("390", 600),
                screenshot=Path(os.devnull),
                full_page=False,
                state_eval="window.fixtureState = 'ready'",
                condition_eval="window.fixtureContent = 'long'",
            )
        self.assertEqual([], errors)
        self.assertEqual(
            [
                ("window.fixtureState = 'ready'", "eval"),
                ("window.fixtureContent = 'long'", "eval"),
            ],
            calls,
        )

    def test_capture_matrix_keeps_condition_base_media_and_identity(self) -> None:
        rows = capture._matrix({"ui_surfaces": realistic_surfaces()}, "/ui-004")
        by_state = {row["state"]: row for row in rows}
        self.assertEqual("ready", by_state["long-content"]["base_state"])
        self.assertEqual("normal", by_state["long-content"]["media_preference"])
        self.assertEqual("reduced", by_state["reduced-motion"]["media_preference"])
        self.assertEqual("product-state", by_state["ready"]["kind"])
        self.assertEqual(
            8,
            len(
                {
                    json.dumps(row, sort_keys=True)
                    for row in rows
                }
            ),
        )

    def test_missing_long_content_setup_is_a_manifest_gap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "PLAN.md"
            plan.write_text(
                manifest_markdown(
                    "## Harness Plan Manifest",
                    "harness_plan",
                    {"ui_surfaces": [surface("UI-004", ["ready"], "ready")]},
                ),
                encoding="utf-8",
            )
            reference = root / "reference.html"
            reference.write_text("<html><body>Reference</body></html>", encoding="utf-8")
            args = argparse.Namespace(
                plan=plan,
                reference=reference,
                route_map=root / "routes.json",
                only="/ui-004",
                base_url="http://127.0.0.1:1",
                out=root / "evidence",
                session="design-coverage-test",
                height=600,
                full_page=False,
            )
            args.route_map.write_text("{}", encoding="utf-8")
            with (
                mock.patch.object(capture, "_resolve_cli", return_value=["browser"]),
                mock.patch.object(capture, "_run_browser") as browser,
            ):
                browser.return_value.returncode = 0
                browser.return_value.stdout = "true"
                browser.return_value.stderr = ""
                result = capture.capture(args)
            self.assertEqual(1, result)
            manifest = json.loads((args.out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("FAIL", manifest["status"])
            self.assertTrue(
                any(
                    item["state"] == "long-content"
                    and "reference_eval" in item["reason"]
                    for item in manifest["skipped"]
                ),
                manifest["skipped"],
            )


if __name__ == "__main__":
    unittest.main()

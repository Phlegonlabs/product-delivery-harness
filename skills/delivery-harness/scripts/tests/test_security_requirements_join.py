#!/usr/bin/env python3
"""Focused coverage for the canonical PRD security-to-PLAN join."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for candidate in (TESTS_DIR, SCRIPTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from harness_contract_join import (  # noqa: E402
    _load_product_security_requirements_parser,
    product_security_requirements_join_errors,
    validate_frozen_contract_joins,
    validate_plan_security_requirements,
)
from manifest_fixtures import carry_security_requirement, valid_plan  # noqa: E402
import test_harness_strict_authority as strict_authority  # noqa: E402


def security_contract(**overrides: object) -> dict[str, object]:
    contract: dict[str, object] = {
        "status": "required",
        "scope": "executable",
        "requirements": [
            {"prd_id": "PRD-003", "test_ids": ["TEST-003"]},
        ],
    }
    contract.update(overrides)
    return contract


def base_plan() -> dict[str, object]:
    plan = valid_plan()
    carry_security_requirement(plan)
    return plan


def parser(contract: dict[str, object] | None = None):
    value = security_contract() if contract is None else contract

    def parse(_text: str) -> tuple[dict[str, object] | None, list[str]]:
        return value, []

    return parse


class SecurityRequirementsJoinTests(unittest.TestCase):
    def test_valid_planned_control_and_matching_acceptance_pass(self) -> None:
        plan = base_plan()
        contract = security_contract(
            requirements=[
                {"prd_id": "PRD-003", "test_ids": ["TEST-003", "TEST-004"]},
            ]
        )
        task = plan["missions"][0]["tasks"][0]
        task["acceptance_matrix"].append(
            {
                "test_id": "TEST-004",
                "trace_ids": ["PRD-003"],
                "criterion": "No unauthorized side effect occurs",
            }
        )
        self.assertEqual([], validate_plan_security_requirements(plan, contract))
        self.assertEqual(
            [],
            validate_plan_security_requirements(
                base_plan(), security_contract(scope="documentation_only")
            ),
        )

    def test_contract_and_plan_inputs_fail_closed(self) -> None:
        for plan_value, contract in ((None, []), ({}, [])):
            with self.subTest(repr((plan_value, contract))):
                errors = validate_plan_security_requirements(plan_value, contract)
                self.assertIn("must be an object", " ".join(errors), errors)

        unhashable = security_contract(status=[], scope=[])
        joined = " ".join(
            validate_plan_security_requirements(base_plan(), unhashable)
        )
        self.assertIn("contract status", joined)
        self.assertIn("contract scope", joined)

        invalid_contracts = (
            security_contract(requirements=[]),
            security_contract(
                requirements=[{"prd_id": "PRD-003", "test_ids": []}]
            ),
            security_contract(
                requirements=[{"prd_id": "REQ-003", "test_ids": ["TEST-003"]}]
            ),
            security_contract(
                requirements=[{"prd_id": "PRD-003", "test_ids": ["CHECK-003"]}]
            ),
            security_contract(
                status="not_required", scope="executable", requirements=[]
            ),
            security_contract(
                status="not_required",
                scope="documentation_only",
                requirements=[{"prd_id": "PRD-003", "test_ids": ["TEST-003"]}],
            ),
        )
        for contract in invalid_contracts:
            with self.subTest(repr(contract)):
                self.assertNotEqual(
                    [],
                    validate_plan_security_requirements(base_plan(), contract),
                )

        self.assertEqual(
            [],
            validate_plan_security_requirements(
                base_plan(),
                security_contract(
                    status="not_required",
                    scope="documentation_only",
                    requirements=[],
                ),
            ),
        )
        self.assertIn(
            "blocked contract must block execution",
            " ".join(
                validate_plan_security_requirements(
                    base_plan(),
                    security_contract(
                        status="blocked",
                        scope="documentation_only",
                        requirements=[],
                    ),
                )
            ),
        )

        malformed_plans = {
            "traces": lambda plan: plan.update(traces={"PRD-003": None}),
            "missions": lambda plan: plan.update(missions="not-a-list"),
            "tasks": lambda plan: plan["missions"][0].update(
                tasks={"T01": plan["missions"][0]["tasks"]}
            ),
            "task trace_ids": lambda plan: plan["missions"][0]["tasks"][0].update(
                trace_ids=[["PRD-003"]]
            ),
            "acceptance": lambda plan: plan["missions"][0]["tasks"][0].update(
                acceptance_matrix={"TEST-003": None}
            ),
        }
        for label, mutate in malformed_plans.items():
            with self.subTest(label):
                plan = base_plan()
                mutate(plan)
                self.assertNotEqual(
                    [],
                    validate_plan_security_requirements(plan, security_contract()),
                )

    def test_each_carrying_task_must_own_required_security_tests(self) -> None:
        plan = base_plan()
        second_task = plan["missions"][0]["tasks"][1]
        second_task["trace_ids"].append("PRD-003")

        errors = validate_plan_security_requirements(plan, security_contract())
        joined = " ".join(errors)
        self.assertIn("task M1/T02", joined, errors)
        self.assertIn("missing required security TEST-003", joined, errors)

    def test_missing_or_mismatched_trace_task_acceptance_and_verifier_fail(self) -> None:
        def remove_security_task_link(plan: dict[str, object]) -> None:
            mission = plan["missions"][0]
            task = mission["tasks"][0]
            mission["trace_ids"].remove("PRD-003")
            task["trace_ids"].remove("PRD-003")
            task["acceptance_matrix"] = [
                row
                for row in task["acceptance_matrix"]
                if row.get("test_id") != "TEST-003"
            ]

        cases: dict[str, tuple[object, str]] = {
            "missing trace": (
                lambda plan: plan["traces"].pop(
                    next(
                        index
                        for index, trace in enumerate(plan["traces"])
                        if trace["id"] == "PRD-003"
                    )
                ),
                "must appear exactly once",
            ),
            "duplicate trace": (
                lambda plan: plan["traces"].append(
                    copy.deepcopy(
                        next(
                            trace
                            for trace in plan["traces"]
                            if trace["id"] == "PRD-003"
                        )
                    )
                ),
                "appears 2 times",
            ),
            "unknown disposition": (
                lambda plan: next(
                    trace for trace in plan["traces"] if trace["id"] == "PRD-003"
                ).__setitem__("disposition", "maybe"),
                "explicit supported disposition",
            ),
            "missing task trace": (
                remove_security_task_link,
                "has no carrying task",
            ),
            "acceptance omits PRD": (
                lambda plan: next(
                    row
                    for row in plan["missions"][0]["tasks"][0]["acceptance_matrix"]
                    if row["test_id"] == "TEST-003"
                )["trace_ids"].clear(),
                "missing required security TEST-003",
            ),
            "wrong acceptance test": (
                lambda plan: next(
                    row
                    for row in plan["missions"][0]["tasks"][0]["acceptance_matrix"]
                    if row["test_id"] == "TEST-003"
                ).__setitem__("test_id", "TEST-999"),
                "missing required security TEST-003",
            ),
            "missing acceptance": (
                lambda plan: plan["missions"][0]["tasks"][0][
                    "acceptance_matrix"
                ].pop(),
                "missing required security TEST-003",
            ),
            "missing verifier": (
                lambda plan: plan["missions"][0]["tasks"][0].__setitem__(
                    "verifiers", []
                ),
                "must declare a verifier",
            ),
        }
        for label, (mutate, expected) in cases.items():
            with self.subTest(label):
                plan = base_plan()
                mutate(plan)
                errors = validate_plan_security_requirements(
                    plan, security_contract()
                )
                self.assertIn(expected, " ".join(errors), errors)

    def test_final_gate_or_noncarrying_acceptance_cannot_satisfy_coverage(self) -> None:
        plan = base_plan()
        task = plan["missions"][0]["tasks"][0]
        task["acceptance_matrix"] = [
            row for row in task["acceptance_matrix"] if row["test_id"] != "TEST-003"
        ]
        plan["final_gates"][0]["id"] = "TEST-003"
        unrelated_task = plan["missions"][1]["tasks"][0]
        unrelated_task["acceptance_matrix"].append(
            {
                "test_id": "TEST-003",
                "trace_ids": ["REQ-002"],
                "criterion": "Unrelated acceptance cannot satisfy security",
            }
        )
        errors = validate_plan_security_requirements(plan, security_contract())
        joined = " ".join(errors)
        self.assertIn("missing required security TEST-003", joined, errors)
        self.assertIn("does not carry PRD-003", joined, errors)

    def test_explicit_unrelated_deferral_and_out_of_scope_pass(self) -> None:
        for disposition in ("deferred", "out_of_scope"):
            with self.subTest(disposition):
                plan = valid_plan()
                plan["traces"].append(
                    {
                        "id": "PRD-003",
                        "source_ids": ["SRC-001"],
                        "priority": "must",
                        "requirement": "Unrelated frozen security obligation",
                        "disposition": disposition,
                        "rationale": "Unrelated bounded enhancement; owner reviewed scope.",
                    }
                )
                self.assertEqual(
                    [],
                    validate_plan_security_requirements(plan, security_contract()),
                )

    def test_silent_omission_blank_rationale_and_carrying_deferral_fail(self) -> None:
        plan = base_plan()
        trace = next(trace for trace in plan["traces"] if trace["id"] == "PRD-003")
        trace["disposition"] = "deferred"
        trace["rationale"] = ""
        errors = validate_plan_security_requirements(plan, security_contract())
        joined = " ".join(errors)
        self.assertIn("rationale is required", joined, errors)
        self.assertIn("must not be carried", joined, errors)

        plan = valid_plan()
        self.assertIn(
            "must appear exactly once",
            " ".join(
                validate_plan_security_requirements(plan, security_contract())
            ),
        )

    def test_fenced_and_commented_decoys_use_only_the_canonical_parser(self) -> None:
        decoy = """
```markdown
### Security Requirements
| PRD ID | TEST IDs |
| --- | --- |
| PRD-003 | TEST-003 |
```

<!--
### Security Requirements
| PRD ID | TEST IDs |
| --- | --- |
| PRD-003 | TEST-003 |
-->
"""
        seen: list[str] = []

        def canonical_parse(
            text: str,
        ) -> tuple[dict[str, object], list[str]]:
            seen.append(text)
            return (
                security_contract(
                    status="not_required",
                    scope="documentation_only",
                    requirements=[],
                ),
                [],
            )

        errors = product_security_requirements_join_errors(
            base_plan(), decoy, parser=canonical_parse, parser_required=True
        )
        self.assertEqual([], errors)
        self.assertEqual([decoy], seen)

    def test_missing_or_malformed_parser_fails_closed_without_crashing(self) -> None:
        with patch(
            "harness_contract_join._load_product_security_requirements_parser",
            return_value=None,
        ) as loader:
            errors = product_security_requirements_join_errors(
                base_plan(), "# PRD\n", parser=None, parser_required=True
            )
        self.assertEqual(
            [
                "security requirements: canonical parser is unavailable — install "
                "product-definition-builder next to delivery-harness"
            ],
            errors,
        )
        loader.assert_called_once()
        self.assertIsNone(
            _load_product_security_requirements_parser(Path("nowhere") / "missing")
        )

        bad_results = (
            (security_contract(),),
            {"contract": security_contract(), "errors": []},
            (security_contract(), "errors"),
            (security_contract(), [42]),
        )
        for result in bad_results:
            with self.subTest(repr(result)):
                errors = product_security_requirements_join_errors(
                    base_plan(),
                    "# PRD\n",
                    parser=lambda _text, result=result: result,
                    parser_required=True,
                )
                self.assertTrue(errors)
                self.assertIn("invalid", "\n".join(errors), errors)

        errors = product_security_requirements_join_errors(
            base_plan(),
            "# PRD\n",
            parser=lambda _text: (None, []),
            parser_required=True,
        )
        self.assertEqual(
            ["security requirements: parser contract must be an object"], errors
        )

        def explode(_text: str) -> tuple[None, list[str]]:
            raise RuntimeError("security parser exploded")

        errors = product_security_requirements_join_errors(
            base_plan(), "# PRD\n", parser=explode, parser_required=True
        )
        self.assertIn("failed safely", " ".join(errors), errors)
        self.assertIn("RuntimeError", " ".join(errors), errors)

        def rejected(_text: str) -> tuple[dict[str, object], list[str]]:
            return {}, ["prd: security parser rejected this PRD"]

        self.assertEqual(
            ["prd: security parser rejected this PRD"],
            product_security_requirements_join_errors(
                base_plan(), "# PRD\n", parser=rejected, parser_required=True
            ),
        )

    def test_legacy_frozen_join_reports_a_security_acceptance_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, _run = strict_authority.StrictAuthorityJoinTests._headless_fixture(
                root
            )
            prd_path = root / "docs/product/PRD.md"
            self.assertIn(
                "<!-- product-definition-approval:start -->",
                prd_path.read_text(encoding="utf-8"),
            )
            next(
                row
                for row in plan["missions"][0]["tasks"][0]["acceptance_matrix"]
                if row["test_id"] == "TEST-003"
            )["test_id"] = "TEST-999"

            errors = validate_frozen_contract_joins(plan, root)
            self.assertTrue(
                any("missing required security TEST-003" in error for error in errors),
                errors,
            )

    def test_strict_frozen_join_reports_a_security_acceptance_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run = strict_authority.StrictAuthorityJoinTests._headless_fixture(root)
            next(
                row
                for row in plan["missions"][0]["tasks"][0]["acceptance_matrix"]
                if row["test_id"] == "TEST-003"
            )["test_id"] = "TEST-999"

            with patch(
                "harness_contract_join._load_product_security_requirements_parser",
                return_value=parser(),
            ), patch(
                "harness_contract_join.full_product_package_checker_errors",
                return_value=[],
            ):
                errors = validate_frozen_contract_joins(plan, root, run=run)
            self.assertTrue(
                any("missing required security TEST-003" in error for error in errors),
                errors,
            )


if __name__ == "__main__":
    unittest.main()

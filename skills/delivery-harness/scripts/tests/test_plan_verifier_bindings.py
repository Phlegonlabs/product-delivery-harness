#!/usr/bin/env python3
"""Focused tests for PLAN-v6 graph verifier-node bindings."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import load_plan, validate_plan  # noqa: E402
from manifest_fixtures import legacy_graph_plan, legacy_plan, valid_plan  # noqa: E402


class PlanVerifierNodeBindingTests(unittest.TestCase):
    @staticmethod
    def deterministic_nodes(plan: dict[str, object]) -> list[dict[str, object]]:
        return [
            node
            for node in plan["graph"]["nodes"]
            if isinstance(node, dict)
            and node.get("kind") == "verifier"
            and node.get("executor") in {"local_command", "harness_parent"}
        ]

    def assert_error_contains(
        self, plan: dict[str, object], fragment: str
    ) -> None:
        errors = validate_plan(plan)
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected {fragment!r} in {errors!r}",
        )

    def test_valid_fixture_shares_batch_gate_nodes(self) -> None:
        plan = valid_plan()
        self.assertEqual([], validate_plan(plan))
        self.assertEqual(
            {"batch"},
            {
                node["ref"]
                for node in self.deterministic_nodes(plan)[:2]
            },
        )

    def test_both_deterministic_executors_are_allowed(self) -> None:
        for executor in ("local_command", "harness_parent"):
            with self.subTest(executor=executor):
                plan = valid_plan()
                next(
                    node
                    for node in self.deterministic_nodes(plan)
                    if node["ref"] == "final"
                )["executor"] = executor
                self.assertEqual([], validate_plan(plan))

    def test_deterministic_node_rejects_task_worker_and_integration_refs(self) -> None:
        for executor in ("local_command", "harness_parent"):
            for ref in ("verify-m1-1", "worker-m1", "integrate-m1"):
                with self.subTest(executor=executor, ref=ref):
                    plan = valid_plan()
                    node = next(
                        node for node in self.deterministic_nodes(plan)
                        if node["ref"] == "batch"
                    )
                    node.update(ref=ref, executor=executor)
                    self.assert_error_contains(
                        plan,
                        "local_command and harness_parent nodes must reference "
                        "batch_verifiers or final_gates",
                    )

    def test_batch_declaration_requires_a_deterministic_node(self) -> None:
        plan = valid_plan()
        for node in self.deterministic_nodes(plan):
            if node["ref"] == "batch":
                node["ref"] = "final"
        self.assert_error_contains(
            plan,
            "plan.batch_verifiers: 'batch' has no local_command or "
            "harness_parent verifier node; a runtime_worker review cannot "
            "execute it or fill batch_gate_results",
        )

    def test_final_declaration_requires_a_deterministic_node(self) -> None:
        plan = valid_plan()
        next(node for node in self.deterministic_nodes(plan) if node["ref"] == "final")[
            "ref"
        ] = "batch"
        self.assert_error_contains(
            plan,
            "plan.final_gates: 'final' has no local_command or "
            "harness_parent verifier node; a runtime_worker review cannot "
            "execute it or fill final_gate_results",
        )

    def test_runtime_reviews_may_reference_gate_declarations(self) -> None:
        for ref in ("verify-m1-1", "worker-m1", "integrate-m1", "batch", "final"):
            with self.subTest(ref=ref):
                plan = valid_plan()
                for node in plan["graph"]["nodes"]:
                    if (
                        isinstance(node, dict)
                        and node.get("executor") == "runtime_worker"
                        and isinstance(node.get("review"), dict)
                    ):
                        node["ref"] = ref
                self.assertEqual([], validate_plan(plan))

    def test_singleton_plan_keeps_empty_batch(self) -> None:
        plan = load_plan(
            SCRIPTS_DIR.parent / "assets/templates/HARNESS_PLAN.template.md"
        )
        self.assertEqual([], plan["batch_verifiers"])
        self.assertEqual([], validate_plan(plan))

    def test_old_schema_recovery_is_not_restricted(self) -> None:
        for version in (2, 3):
            with self.subTest(version=version):
                self.assertEqual([], validate_plan(legacy_plan(version)))
        for version in (4, 5):
            with self.subTest(version=version):
                plan = legacy_graph_plan() if version == 4 else valid_plan()
                plan["schema_version"] = version
                for node in self.deterministic_nodes(plan):
                    node["ref"] = "integrate-m1"
                self.assertEqual([], validate_plan(plan))

    def test_malformed_values_report_existing_errors_without_crashing(self) -> None:
        cases = (
            lambda plan: plan["graph"].update(nodes=[]),
            lambda plan: plan["graph"].update(nodes="not-a-list"),
            lambda plan: plan["graph"]["nodes"].append(None),
            lambda plan: plan.update(batch_verifiers=None),
            lambda plan: plan["final_gates"][0].update(id=None),
        )
        for index, mutate in enumerate(cases):
            with self.subTest(case=index):
                plan = valid_plan()
                mutate(plan)
                errors = validate_plan(plan)
                self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()

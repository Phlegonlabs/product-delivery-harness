#!/usr/bin/env python3
"""Focused tests for the canonical harness manifest contract."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import (  # noqa: E402
    ManifestError,
    load_plan,
    load_run,
    mission_conflicts,
    plan_digest,
    route_runtime_driver,
    scope_overlap,
    topological_levels,
    validate_plan,
    validate_run,
    validate_ui_evidence_files,
    validate_scope_claim,
)
from harness_authorization import authorization_covers, execution_covers  # noqa: E402


# The PLAN/RUN fixture builders live in manifest_fixtures.py; they are
# re-exported here because other test files import them from this module.
from manifest_fixtures import (  # noqa: E402
    SHA_A,
    SHA_B,
    SHA_C,
    SHA_D,
    authorize_action,
    authorize_execution,
    codex_capability_probe,
    current_version_gate,
    legacy_graph_plan,
    legacy_graph_run,
    legacy_plan,
    legacy_run,
    mark_complete,
    mark_legacy_complete,
    retained_gate_execution,
    task,
    valid_closeout_run,
    valid_plan,
    valid_run,
)

# Downstream suites import these names from this module; __all__ documents the
# re-export and keeps the linters honest about it.
__all__ = [
    "SHA_A",
    "SHA_B",
    "SHA_C",
    "SHA_D",
    "authorize_action",
    "authorize_execution",
    "codex_capability_probe",
    "current_version_gate",
    "legacy_graph_plan",
    "legacy_graph_run",
    "legacy_plan",
    "legacy_run",
    "mark_complete",
    "mark_legacy_complete",
    "retained_gate_execution",
    "task",
    "valid_closeout_run",
    "valid_plan",
    "valid_run",
]


def markdown(heading: str, wrapper: str, value: dict[str, object]) -> str:
    payload = json.dumps({wrapper: value}, indent=2, ensure_ascii=False)
    return f"# Fixture\n\n{heading}\n\n```json\n{payload}\n```\n"


class ManifestExtractionTests(unittest.TestCase):
    def test_loads_unique_exact_plan_and_run_manifests(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "PLAN.md"
            run_path = root / "RUN.md"
            plan_path.write_text(
                markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path.write_text(
                markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            self.assertEqual(load_plan(plan_path), plan)
            self.assertEqual(load_run(run_path), run)

    def test_rejects_wrong_heading_malformed_json_and_duplicate_heading(self) -> None:
        cases = (
            "## Harness Plan Manifest extra\n\n```json\n{}\n```\n",
            "## Harness Plan Manifest\n\n```json\n{broken\n```\n",
            (
                "## Harness Plan Manifest\n\n```json\n{\"harness_plan\": {}}\n```\n"
                "## Harness Plan Manifest\n\n```json\n{\"harness_plan\": {}}\n```\n"
            ),
            "## Harness Plan Manifest\n\nprose\n```json\n{}\n```\n",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "PLAN.md"
            for content in cases:
                with self.subTest(content=content[:40]):
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaises(ManifestError):
                        load_plan(path)


class DigestTests(unittest.TestCase):
    def test_semantic_set_reordering_is_stable(self) -> None:
        original = valid_plan()
        reordered = copy.deepcopy(original)
        reordered["sources"].reverse()
        reordered["traces"].reverse()
        reordered["missions"].reverse()
        for current_mission in reordered["missions"]:
            current_mission["tasks"].reverse()
            current_mission["runtime_resources"].reverse()
            current_mission["serialized_resources"].reverse()
            current_mission["trace_ids"].reverse()
        self.assertEqual(plan_digest(original), plan_digest(reordered))

    def test_argv_order_is_semantic(self) -> None:
        original = valid_plan()
        changed = copy.deepcopy(original)
        changed["batch_verifiers"][0]["argv"].reverse()
        self.assertNotEqual(plan_digest(original), plan_digest(changed))


class PlanValidationTests(unittest.TestCase):
    def test_runtime_review_accepts_only_supported_required_tools(self) -> None:
        plan = valid_plan()
        review = next(
            node["review"]
            for node in plan["graph"]["nodes"]
            if isinstance(node.get("review"), dict)
        )
        review["required_tools"] = ["chrome_devtools"]
        self.assertEqual([], validate_plan(plan))

        review["required_tools"] = ["browser_magic"]
        self.assertTrue(
            any(
                "unsupported reviewer tools: browser_magic" in error
                for error in validate_plan(plan)
            )
        )

    def assert_error_contains(self, plan: dict[str, object], fragment: str) -> None:
        errors = validate_plan(plan)
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected {fragment!r} in {errors!r}",
        )

    def test_valid_plan_and_topological_levels(self) -> None:
        plan = valid_plan()
        self.assertEqual(validate_plan(plan), [])
        self.assertEqual(topological_levels(plan), {"M1": 0, "M2": 1})

    def test_shape_validator_keeps_batch_verifiers_nonempty_by_default(self) -> None:
        plan = valid_plan()
        plan["batch_verifiers"] = []
        self.assert_error_contains(plan, "plan.batch_verifiers: must be a non-empty list")
        self.assertIn(
            "plan.batch_verifiers: must be a non-empty list",
            validate_plan(plan),
        )

    def test_planned_trace_needs_a_verification_row_not_just_a_task(self) -> None:
        # contract-and-traceability.md requires every must-have trace to have a
        # downstream task AND a verification row. Task coverage alone let an
        # implemented-but-unverified contract reach closeout as covered.
        plan = valid_plan()
        self.assertEqual(validate_plan(plan), [])

        for task_entry in plan["missions"][0]["tasks"]:
            task_entry["acceptance_matrix"] = []
        self.assert_error_contains(plan, "planned trace has no verification row")

        # One task carrying the trace with a real acceptance matrix is enough.
        plan["missions"][0]["tasks"][0]["acceptance_matrix"] = [
            {
                "test_id": "TEST-M1-01",
                "trace_ids": ["REQ-001"],
                "criterion": "M1/T01 passes",
            }
        ]
        self.assertEqual(validate_plan(plan), [])

    def test_required_skills_accepts_empty_and_populated_lists(self) -> None:
        plan = valid_plan()
        self.assertEqual(validate_plan(plan), [])
        plan["missions"][0]["required_skills"] = ["frontend-design", "feature-dev"]
        self.assertEqual(validate_plan(plan), [])

    def test_design_system_compiler_requires_compilation_skill_set(self) -> None:
        plan = valid_plan()
        plan["missions"][0]["required_skills"] = ["design-system-compiler"]
        self.assert_error_contains(plan, "frontend-design")

        plan = valid_plan()
        plan["missions"][0]["required_skills"] = [
            "design-system-compiler",
            "frontend-design",
        ]
        self.assertEqual(validate_plan(plan), [])

        plan = valid_plan()
        plan["missions"][0]["required_skills"] = ["frontend-design"]
        self.assertEqual(validate_plan(plan), [])

    def test_design_source_write_scope_requires_the_exact_skill_set(self) -> None:
        plan = valid_plan()
        design_scopes = [
            "docs/product/design-system.md",
            "docs/product/design-system.json",
        ]
        mission = plan["missions"][0]
        mission["write_scope"] = design_scopes
        mission["tasks"][0]["write_scope"] = [design_scopes[0]]
        mission["tasks"][1]["write_scope"] = [design_scopes[1]]
        for node in plan["graph"]["nodes"]:
            review = node.get("review")
            if isinstance(review, dict) and review.get("mission_ids") == ["M1"]:
                review["scope"] = design_scopes

        self.assert_error_contains(plan, "design-source write scope must include")

        mission["required_skills"] = [
            "design-system-compiler",
            "frontend-design",
        ]
        self.assertEqual(validate_plan(plan), [])

        mission["required_skills"] = ["frontend-design"]
        self.assert_error_contains(plan, "design-source write scope must include")

    def test_staged_design_source_write_scope_requires_the_exact_skill_set(self) -> None:
        for staging_scope in (
            "docs/product/.prd-staging/run-001/**",
            "docs/product/.prd-staging/run-001/design-system.md",
            "docs/product/.prd-staging/run-001/design-system.json",
        ):
            with self.subTest(staging_scope=staging_scope):
                plan = valid_plan()
                mission = plan["missions"][0]
                mission["write_scope"].append(staging_scope)

                self.assert_error_contains(
                    plan, "design-source write scope must include"
                )

                mission["required_skills"] = [
                    "design-system-compiler",
                    "frontend-design",
                ]
                if staging_scope.endswith("/**"):
                    mission["required_skills"].append("product-definition-builder")
                self.assertEqual(validate_plan(plan), [])

        plan = valid_plan()
        plan["missions"][0]["write_scope"].append(
            "docs/product/.prd-staging/run-001/PRD.md"
        )
        self.assertEqual(validate_plan(plan), [])

        for non_design_scope in (
            "docs/product/.prd-staging/run-001/research/**",
        ):
            with self.subTest(non_design_scope=non_design_scope):
                plan = valid_plan()
                plan["missions"][0]["write_scope"].append(non_design_scope)
                self.assertEqual(validate_plan(plan), [])

    def test_registered_custom_design_sources_require_the_exact_skill_set(self) -> None:
        plan = valid_plan()
        plan["sources"].extend(
            [
                {
                    "id": "SRC-DESIGN-001",
                    "kind": "design system markdown",
                    "location": "specs/custom/design-rules.md",
                    "owner": "design",
                    "status": "frozen",
                    "content_sha256": "d" * 64,
                    "source_revision": None,
                    "staged_revision": None,
                    "notes": "custom named design system source",
                },
                {
                    "id": "SRC-DESIGN-002",
                    "kind": "design_system",
                    "location": "specs/custom/visual-contract.yml",
                    "owner": "design",
                    "status": "frozen",
                    "content_sha256": "c" * 64,
                    "source_revision": None,
                    "staged_revision": None,
                    "notes": "custom named design system source",
                },
                {
                    "id": "SRC-DESIGN-003",
                    "kind": "visual contract",
                    "location": "alternate-product-path/design-system.json",
                    "owner": "design",
                    "status": "frozen",
                    "content_sha256": "b" * 64,
                    "source_revision": None,
                    "staged_revision": None,
                    "notes": "default design filename outside the default folder",
                },
            ]
        )
        mission = plan["missions"][0]
        mission["write_scope"].extend(
            ["specs/custom/**", "alternate-product-path/**"]
        )

        self.assert_error_contains(plan, "design-source write scope must include")

        mission["required_skills"] = [
            "design-system-compiler",
            "frontend-design",
        ]
        self.assertEqual(validate_plan(plan), [])

    def test_wireframe_source_write_scope_requires_product_definition_builder(self) -> None:
        for wireframe_scope in (
            "docs/product/wireframes.html",
            "docs/product/.prd-staging/run-001/wireframes.html",
        ):
            with self.subTest(wireframe_scope=wireframe_scope):
                plan = valid_plan()
                mission = plan["missions"][0]
                mission["write_scope"].append(wireframe_scope)

                self.assert_error_contains(
                    plan, "wireframe-source write scope must include 'product-definition-builder'"
                )

                mission["required_skills"] = ["product-definition-builder"]
                self.assertEqual(validate_plan(plan), [])

    def test_registered_custom_wireframe_source_requires_product_definition_builder(self) -> None:
        plan = valid_plan()
        plan["sources"].append(
            {
                "id": "SRC-WIREFRAME-001",
                "kind": "low_fidelity_wireframe",
                "location": "specs/custom/layout-sketches.md",
                "owner": "product",
                "status": "frozen",
                "content_sha256": "a" * 64,
                "source_revision": None,
                "staged_revision": None,
                "notes": "custom approved wireframe source",
            }
        )
        mission = plan["missions"][0]
        mission["write_scope"].append("specs/custom/**")

        self.assert_error_contains(
            plan, "wireframe-source write scope must include 'product-definition-builder'"
        )

        mission["required_skills"] = ["product-definition-builder"]
        self.assertEqual(validate_plan(plan), [])

    def test_required_skills_rejects_non_list_and_missing_key(self) -> None:
        plan = valid_plan()
        plan["missions"][0]["required_skills"] = "frontend-design"
        self.assert_error_contains(plan, "required_skills")
        plan = valid_plan()
        del plan["missions"][0]["required_skills"]
        self.assert_error_contains(plan, "missing keys: required_skills")

    def test_targeted_verifier_metadata_is_bounded(self) -> None:
        plan = valid_plan()
        task_verifier = plan["missions"][0]["tasks"][0]["verifiers"][0]
        task_verifier["selection"] = {
            "mode": "changed_files",
            "scopes": ["src/a/one.py"],
        }
        task_verifier["cache"] = {
            "mode": "session_exact",
            "environment_keys": ["CI"],
        }
        worker_verifier = plan["missions"][0]["worker_verifiers"][0]
        worker_verifier["selection"] = {
            "mode": "changed_files",
            "scopes": ["src/a/**"],
        }
        self.assertEqual(validate_plan(plan), [])

        escaped = copy.deepcopy(plan)
        escaped["missions"][0]["tasks"][0]["verifiers"][0]["selection"][
            "scopes"
        ] = ["src/ab/**"]
        self.assert_error_contains(escaped, "escapes the owning write scope")

        integration = copy.deepcopy(plan)
        integration["missions"][0]["integration_verifiers"][0]["selection"] = {
            "mode": "changed_files",
            "scopes": ["src/a/**"],
        }
        self.assert_error_contains(
            integration,
            "changed_files is allowed only for task and worker verifiers",
        )

        cached_nonzero = copy.deepcopy(plan)
        cached_nonzero["missions"][0]["tasks"][0]["verifiers"][0][
            "pass_signal"
        ] = "custom success"
        self.assert_error_contains(
            cached_nonzero,
            "session_exact requires the literal pass signal exit 0",
        )


    def test_batch_and_final_gates_select_against_the_plan_write_union(self) -> None:
        plan = valid_plan()
        union = plan["missions"][0]["write_scope"][0]
        always_gate = copy.deepcopy(plan["final_gates"][0])
        always_gate["id"] = "final-always"
        plan["final_gates"].append(always_gate)
        plan["final_gates"][0]["selection"] = {
            "mode": "changed_files",
            "scopes": [union],
        }
        self.assertEqual([], validate_plan(plan))

        escaping = valid_plan()
        escaping["final_gates"][0]["selection"] = {
            "mode": "changed_files",
            "scopes": ["unrelated/**"],
        }
        self.assert_error_contains(escaping, "escapes the owning write scope")

    def test_batch_and_final_gates_keep_one_always_run_verifier(self) -> None:
        plan = valid_plan()
        union = plan["missions"][0]["write_scope"][0]
        for gate in plan["final_gates"]:
            gate["selection"] = {"mode": "changed_files", "scopes": [union]}
        self.assert_error_contains(
            plan, "must keep at least one always-run verifier"
        )

    def test_deterministic_local_attestation_unlocks_banned_layers(self) -> None:
        cache = {
            "mode": "session_exact",
            "environment_keys": [],
            "deterministic_local": True,
        }

        batch_plan = valid_plan()
        batch_plan["batch_verifiers"][0]["cache"] = cache
        self.assertEqual([], validate_plan(batch_plan))

        final_plan = valid_plan()
        final_plan["final_gates"][0]["cache"] = cache
        self.assertEqual([], validate_plan(final_plan))

        integration_plan = valid_plan()
        integration_plan["missions"][0]["integration_verifiers"][0]["cache"] = cache
        self.assertEqual([], validate_plan(integration_plan))

    def test_integration_batch_and_final_verifiers_need_explicit_attestation(self) -> None:
        cache = {"mode": "session_exact", "environment_keys": []}

        batch_plan = valid_plan()
        batch_plan["batch_verifiers"][0]["cache"] = cache
        self.assert_error_contains(
            batch_plan, "session_exact at this layer requires cache.deterministic_local: true"
        )

        final_plan = valid_plan()
        final_plan["final_gates"][0]["cache"] = cache
        self.assert_error_contains(
            final_plan, "session_exact at this layer requires cache.deterministic_local: true"
        )

        integration_plan = valid_plan()
        integration_plan["missions"][0]["integration_verifiers"][0]["cache"] = cache
        self.assert_error_contains(
            integration_plan, "session_exact at this layer requires cache.deterministic_local: true"
        )

        worker_plan = valid_plan()
        worker_plan["missions"][0]["worker_verifiers"][0]["cache"] = cache
        self.assertEqual(validate_plan(worker_plan), [])

    def test_verifier_parallel_execution_metadata_is_resource_bounded(self) -> None:
        plan = valid_plan()
        verifier = plan["missions"][0]["worker_verifiers"][0]
        verifier["execution"] = {
            "parallel_safe": True,
            "resources": [
                {"key": "database:test", "access": "shared_read"},
                {"key": "port:4173", "access": "exclusive"},
            ],
        }
        self.assertEqual(validate_plan(plan), [])

        duplicate = copy.deepcopy(plan)
        duplicate["missions"][0]["worker_verifiers"][0]["execution"]["resources"].append(
            {"key": "port:4173", "access": "shared_read"}
        )
        self.assert_error_contains(duplicate, "must be unique")

        invalid_access = copy.deepcopy(plan)
        invalid_access["missions"][0]["worker_verifiers"][0]["execution"]["resources"][0][
            "access"
        ] = "write"
        self.assert_error_contains(invalid_access, "must be shared_read or exclusive")











    def test_strict_unknown_keys(self) -> None:
        plan = valid_plan()
        plan["unexpected"] = True
        self.assert_error_contains(plan, "unknown keys: unexpected")

        plan = valid_plan()
        plan["missions"][0]["tasks"][0]["unexpected"] = True
        self.assert_error_contains(plan, "unknown keys: unexpected")

    def test_mission_and_task_cycles(self) -> None:
        plan = valid_plan()
        reverse_edge = copy.deepcopy(
            next(
            edge
            for edge in plan["graph"]["edges"]
            if edge["from"] == "N-M1" and edge["to"] == "N-M2"
            )
        )
        reverse_edge.update(
            {
                "id": "E-M2-M1",
                "from": "N-M2",
                "to": "N-M1",
            }
        )
        plan["graph"]["edges"].append(reverse_edge)
        self.assert_error_contains(plan, "dependency cycle includes N-M1, N-M2")

        plan = valid_plan()
        plan["missions"][0]["tasks"][0]["depends_on"] = ["M1/T02"]
        self.assert_error_contains(plan, "dependency cycle includes M1/T01, M1/T02")

        plan = legacy_plan()
        plan["missions"][0]["depends_on"] = ["M2"]
        self.assert_error_contains(plan, "dependency cycle includes M1, M2")

    def test_task_dependency_must_stay_in_mission(self) -> None:
        plan = valid_plan()
        plan["missions"][1]["tasks"][0]["depends_on"] = ["M1/T02"]
        self.assert_error_contains(plan, "cross-mission task dependency is forbidden")

    def test_dependency_cannot_target_superseded_task(self) -> None:
        plan = valid_plan()
        tasks = plan["missions"][0]["tasks"]
        parent = tasks[0]
        child = task("M1", 3, "REQ-001", "src/a/three.py")
        parent["replaced_by"] = ["M1/T03"]
        child["parent_task"] = "M1/T01"
        child["split_reason"] = "Bound the worker result"
        child["refinement_generation"] = 1
        tasks.append(child)
        self.assert_error_contains(plan, "cannot target superseded task 'M1/T01'")

    def test_refinement_generation_is_bounded(self) -> None:
        plan = valid_plan()
        plan["missions"][0]["tasks"][0]["refinement_generation"] = 2
        self.assert_error_contains(plan, "must be 0 or 1")

    def test_scope_grammar_and_boundary(self) -> None:
        self.assertTrue(scope_overlap("src/a/**", "src/a/file.py"))
        self.assertFalse(scope_overlap("src/a/**", "src/ab/**"))
        self.assertIsNone(validate_scope_claim("src/a/**"))
        self.assertIsNotNone(validate_scope_claim("src/*/file.py"))
        self.assertIsNotNone(validate_scope_claim("../outside/**"))

        plan = valid_plan()
        plan["missions"][0]["write_scope"] = ["src/*/bad.py"]
        self.assert_error_contains(plan, "only one terminal /** wildcard is supported")

    def test_case_serialized_and_runtime_conflicts(self) -> None:
        left = copy.deepcopy(valid_plan()["missions"][0])
        right = copy.deepcopy(valid_plan()["missions"][1])
        left["write_scope"] = ["Src/Case/**"]
        right["write_scope"] = ["src/case/**"]
        self.assertIn("case_scope_collision", mission_conflicts(left, right))

        left["write_scope"] = ["src/left/**"]
        right["write_scope"] = ["src/right/**"]
        left["serialized_resources"] = ["migration:primary"]
        right["serialized_resources"] = ["migration:primary"]
        self.assertIn("serialized_resource_conflict", mission_conflicts(left, right))

        left["serialized_resources"] = []
        right["serialized_resources"] = []
        left["runtime_resources"] = [{"key": "db:test", "access": "shared_read"}]
        right["runtime_resources"] = [{"key": "db:test", "access": "shared_read"}]
        self.assertNotIn("runtime_resource_conflict", mission_conflicts(left, right))
        right["runtime_resources"][0]["access"] = "exclusive"
        self.assertIn("runtime_resource_conflict", mission_conflicts(left, right))

    def test_incomplete_inventory_is_explicit_but_schema_valid(self) -> None:
        plan = valid_plan()
        plan["missions"][0]["resource_inventory_complete"] = False
        self.assertEqual(validate_plan(plan), [])

        plan["missions"][0]["resource_inventory_complete"] = "unknown"
        self.assert_error_contains(plan, "resource_inventory_complete: must be boolean")


class RunValidationTests(unittest.TestCase):
    def test_reviewer_tool_capability_requires_a_fresh_provider_session(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["runtime_capabilities"]["reviewer_tools"] = {
            "chrome_devtools": {
                "status": "available",
                "provider": "codex",
                "driver": "sequential_parent",
                "surface": "raw_cdp",
                "probe_scope": "parent_session",
                "session_id": None,
                "evidence": "Parent can call CDP, reviewer was not probed",
            }
        }
        errors = validate_run(plan, run)
        self.assertTrue(
            any("available capability requires a reviewer_session probe" in error for error in errors)
        )
        self.assertTrue(
            any("available capability requires a reviewer session id" in error for error in errors)
        )

        capability = run["runtime_capabilities"]["reviewer_tools"]["chrome_devtools"]
        capability["probe_scope"] = "reviewer_session"
        capability["session_id"] = "reviewer-codex-1"
        self.assertEqual([], validate_run(plan, run))

        capability["driver"] = "subagents"
        self.assertTrue(
            any(
                "available capability must match the selected runtime driver" in error
                for error in validate_run(plan, run)
            )
        )

    def test_integration_stage_review_does_not_replace_preintegration_coverage(self) -> None:
        plan = valid_plan()
        for node in plan["graph"]["nodes"]:
            review = node.get("review") if isinstance(node, dict) else None
            if isinstance(review, dict) and review.get("mission_ids") == ["M1"]:
                review["stage"] = "integration"
        run = valid_run(plan)
        authorize_execution(run, ["M1"])

        self.assert_run_error_contains(
            plan,
            run,
            "no direct singleton pre-integration review node: M1",
        )

    def assert_run_error_contains(
        self, plan: dict[str, object], run: dict[str, object], fragment: str
    ) -> None:
        errors = validate_run(plan, run)
        self.assertTrue(
            any(fragment in error for error in errors),
            f"expected {fragment!r} in {errors!r}",
        )

    def test_matching_plan_run_digest(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        self.assertEqual(validate_run(plan, run), [])

        run["plan"]["digest_sha256"] = "0" * 64
        self.assert_run_error_contains(plan, run, "does not match semantic PLAN digest")

    def test_v2_verifier_execution_omits_logical_gate_attribution(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        execution = run["verifier_executions"][0]
        execution["protocol"] = "harness-verifier-execution-v2"
        key_document = execution["key_document"]
        key_document["protocol"] = "harness-verifier-execution-v2"
        for key in (
            "verifier_id",
            "layer",
            "mission_id",
            "task_id",
            "attempt_id",
            "lease_id",
        ):
            key_document.pop(key)
        execution_key = hashlib.sha256(
            json.dumps(
                key_document,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        execution["execution_key"] = execution_key
        execution["evidence_key"] = execution_key

        self.assertEqual(validate_run(plan, run), [])

    def test_default_branch_observation_is_optional_without_a_schema_bump(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        self.assertEqual(validate_run(plan, run), [])

        run["observed"]["git"]["default_branch"] = "refs/heads/trunk"
        self.assertEqual(validate_run(plan, run), [])

        run["observed"]["git"]["default_branch"] = 42
        self.assert_run_error_contains(plan, run, "default_branch")

    def test_integration_branch_must_not_resolve_to_the_default_branch(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["integration"]["branch"] = "refs/heads/main"
        self.assert_run_error_contains(plan, run, "must not resolve to main")

        run["integration"]["branch"] = "refs/heads/release"
        run["observed"]["git"]["default_branch"] = "release"
        self.assert_run_error_contains(
            plan, run, "must not equal the observed repository default branch"
        )

    def test_v10_push_authorization_requires_explicit_remote_intent(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["authorizations"]["push"] = {
            "authorized": True,
            "source": "user: implement the approved plan",
            "authorized_head_sha": "a" * 40,
            "scope": {
                "run_id": run["run_id"],
                "plan_revision": run["plan"]["revision"],
                "plan_digest_sha256": run["plan"]["digest_sha256"],
                "mission_ids": ["M1"],
                "targets": ["branch:refs/heads/codex/test"],
            },
            "expires_when": "run_complete",
        }
        self.assert_run_error_contains(
            plan,
            run,
            "must explicitly request a remote push",
        )


    def test_integration_retention_accepts_known_values_only(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        self.assertEqual(validate_run(plan, run), [])

        run["integration"]["retention"] = "persistent"
        self.assertEqual(validate_run(plan, run), [])

        run["integration"]["retention"] = "ephemeral"
        self.assertEqual(validate_run(plan, run), [])

        run["integration"]["retention"] = None
        self.assertEqual(validate_run(plan, run), [])

        run["integration"]["retention"] = "forever"
        self.assert_run_error_contains(
            plan,
            run,
            "run.integration.retention: must be null, persistent, or ephemeral",
        )


    def test_complete_run_rejects_unfinished_missions_and_tasks(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        run["status"] = "complete"
        run["intent"] = "plan-then-execute"
        run["plan_readiness"] = "ready"
        for results in (run["batch_gate_results"], run["final_gate_results"]):
            for result in results:
                result["status"] = "PASS"
                result["head_sha"] = run["integration"]["integration_head_sha"]
                result["evidence"] = ["gate passed"]

        self.assert_run_error_contains(
            plan, run, "complete run requires every mission to be integrated or superseded"
        )
        self.assert_run_error_contains(
            plan, run, "complete run requires every task to be mission_recorded or superseded"
        )

    def test_complete_run_accepts_current_head_closeout_evidence(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)

        self.assertEqual(validate_run(plan, run), [])

        run["review_workers"][0]["findings"] = [
            "informational note without a severity field"
        ]
        self.assert_run_error_contains(
            plan,
            run,
            "current PASS review result must not contain findings",
        )
        run["review_workers"][0]["findings"] = []

        run["batch_gate_results"][0].update(
            {"status": "planned", "head_sha": None, "evidence": []}
        )
        self.assert_run_error_contains(
            plan, run, "complete run requires every batch gate to PASS"
        )
        run["batch_gate_results"][0].update(
            {"status": "PASS", "head_sha": SHA_A, "evidence": ["gate passed"]}
        )
        run["final_gate_results"][0].update(
            {"status": "planned", "head_sha": None, "evidence": []}
        )
        self.assert_run_error_contains(
            plan, run, "complete run requires every final gate to PASS"
        )

    def test_complete_run_requires_retained_execution_authorization(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        run.update(
            {
                "execution_authorized": False,
                "execution_authorization_source": None,
                "execution_authorization_scope": None,
            }
        )

        self.assert_run_error_contains(
            plan,
            run,
            "complete RUN requires a retained overall execution grant",
        )

    def test_plan_v5_write_worker_rejects_shared_checkout(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        run["workers"][0]["workspace_mode"] = "shared_checkout"

        self.assert_run_error_contains(
            plan,
            run,
            "PLAN-v6 write mission requires an isolated managed worktree",
        )

    def test_recorded_lifecycle_requires_each_exact_action_grant(self) -> None:
        plan = valid_plan()
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
            "integrate_locally",
        ):
            with self.subTest(action=action):
                run = valid_closeout_run(plan)
                mark_complete(plan, run)
                run["authorizations"][action] = {
                    "authorized": False,
                    "source": None,
                }
                errors = validate_run(plan, run)
                self.assertTrue(
                    any(
                        f"run.authorizations.{action}: must exactly authorize"
                        in error
                        for error in errors
                    ),
                    errors,
                )

        app_run = valid_closeout_run(plan)
        mark_complete(plan, app_run)
        app_run["workers"][0]["workspace_mode"] = "app_managed_worktree"
        app_run["observed"]["git"]["worktrees"][0]["managed_by"] = "app"
        self.assert_run_error_contains(
            plan,
            app_run,
            "run.authorizations.create_app_managed_worktrees: must exactly authorize",
        )

        app_task_run = valid_closeout_run(plan)
        mark_complete(plan, app_task_run)
        app_worker = app_task_run["workers"][0]
        app_worker.update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "task_thread_id": "THREAD-M1",
            }
        )
        app_worker["runtime_binding"]["driver"] = "app_threads"
        app_task_run["observed"]["git"]["worktrees"][0]["managed_by"] = "app"
        authorize_action(
            app_task_run,
            "create_app_managed_worktrees",
            ["M1"],
            [f"worktree:{app_worker['worktree_path']}"],
        )
        self.assert_run_error_contains(
            plan,
            app_task_run,
            "run.authorizations.create_user_owned_tasks: must exactly authorize",
        )

    def test_exact_recorded_action_scope_requires_mission_and_target(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        spawn_scope = run["authorizations"]["spawn_subagents"]["scope"]
        spawn_scope["mission_ids"] = ["*"]
        spawn_scope["targets"] = ["*"]
        self.assert_run_error_contains(
            plan,
            run,
            "run.authorizations.spawn_subagents: must exactly authorize",
        )

        exact_with_prelaunch = valid_closeout_run(plan)
        mark_complete(plan, exact_with_prelaunch)
        exact_spawn_scope = exact_with_prelaunch["authorizations"][
            "spawn_subagents"
        ]["scope"]
        exact_spawn_scope["targets"].append("*")
        self.assertEqual([], validate_run(plan, exact_with_prelaunch))

    def test_singleton_preintegration_review_requires_the_mission_worktree(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        run["review_workers"][0]["review_path"] = "C:/repo/other-worktree"

        self.assert_run_error_contains(
            plan,
            run,
            "review_path: must match the singleton mission worker worktree_path",
        )

    def test_mission_integration_evidence_uses_each_integrated_sha(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        self.assertNotEqual(
            run["mission_states"]["M1"]["integrated_sha"],
            run["integration"]["integration_head_sha"],
        )
        declaration = plan["missions"][0]["integration_verifiers"][0]
        original = next(
            execution
            for execution in run["verifier_executions"]
            if execution["verifier_id"] == declaration["id"]
        )
        wrong_head_execution = retained_gate_execution(
            plan,
            run,
            declaration,
            layer="mission_integration",
            execution_id=original["execution_id"],
            mission_id="M1",
            head_sha=run["integration"]["integration_head_sha"],
        )
        run["verifier_executions"] = [
            (
                wrong_head_execution
                if execution["execution_id"] == original["execution_id"]
                else execution
            )
            for execution in run["verifier_executions"]
        ]

        self.assert_run_error_contains(
            plan,
            run,
            "context.head_sha: must match the mission integrated_sha",
        )

    def test_terminal_states_require_task_worker_and_integration_evidence(self) -> None:
        plan = valid_plan()
        for layer, expected in (
            ("task", "missing retained PASS execution for task verifier"),
            ("worker", "missing retained PASS execution for worker verifier"),
            (
                "mission_integration",
                "missing retained PASS execution for mission integration verifier",
            ),
        ):
            with self.subTest(layer=layer):
                run = valid_closeout_run(plan)
                mark_complete(plan, run)
                run["verifier_executions"] = [
                    execution
                    for execution in run["verifier_executions"]
                    if execution["layer"] != layer
                ]
                self.assert_run_error_contains(plan, run, expected)

    def test_passed_gate_results_must_match_the_current_integration_head(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        run["status"] = "running"
        run["batch_gate_results"][0].update(
            {
                "status": "PASS",
                "head_sha": SHA_B,
                "evidence": ["gate passed on an older head"],
            }
        )

        self.assert_run_error_contains(
            plan,
            run,
            "PASS batch gate must match integration_head_sha",
        )

    def test_prior_head_shas_cannot_contain_the_current_integration_head(self) -> None:
        """The head still in use is not a superseded one.

        This rule had no test: disabling it left the whole suite green, which is
        how a later cleanup could delete it without noticing. It also guards the
        shared `integration_prior_heads` name in validate_run, whose first
        binding is the empty-set fallback the check reads when a run records no
        history — split that name and this rule silently stops firing.
        """
        root = SCRIPTS_DIR.parent
        plan = load_plan(root / "assets/templates/HARNESS_PLAN.template.md")
        run = load_run(root / "assets/templates/MISSION_RUNBOOK.template.md")
        # The current v10 sequential-parent contract requires the parent-owned
        # isolated worktree mode.  Keep this template-based regression focused
        # on integration history rather than its legacy shared-checkout value.
        run["runtime_capabilities"]["workspace_mode"] = "parent_managed_worktree"
        run["integration"]["integration_head_sha"] = SHA_A
        run["integration"]["prior_head_shas"] = [SHA_B, SHA_A]

        self.assert_run_error_contains(
            plan,
            run,
            "must contain only superseded integration heads",
        )

        run["integration"]["prior_head_shas"] = [SHA_B]
        self.assertEqual([], validate_run(plan, run))

    def test_complete_run_allows_tasks_of_a_superseded_mission(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        run["mission_states"]["M2"].update(
            {
                "phase": "superseded",
                "integration_gate": "planned",
                "integrated_sha": None,
            }
        )
        run["graph_state"]["node_states"]["N-M2"]["phase"] = "superseded"
        for superseded_task in plan["missions"][1]["tasks"]:
            run["task_states"][superseded_task["id"]]["phase"] = "superseded"

        self.assertEqual(validate_run(plan, run), [])


    def test_schema_v9_rejects_unhashable_gate_ids_without_crashing(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 9)
        run["batch_gate_results"][0]["id"] = []

        errors = validate_run(plan, run)

        self.assertTrue(any("must be a non-empty string" in error for error in errors))
        self.assertTrue(any("IDs must exactly match" in error for error in errors))

        run = legacy_run(plan, 9)
        run["batch_gate_results"][0]["status"] = []
        errors = validate_run(plan, run)
        self.assertTrue(any(".status: has an unsupported gate value" in error for error in errors))

    def test_schema_v9_rejects_malformed_plan_gate_lists_without_crashing(self) -> None:
        for field in ("batch_verifiers", "final_gates"):
            with self.subTest(field=field):
                plan = legacy_plan()
                run = legacy_run(plan, 9)
                plan[field] = None

                self.assertTrue(validate_plan(plan))
                self.assertTrue(validate_run(plan, run))

    def test_schema_v9_rejects_unhashable_ui_evidence_scalars_without_crashing(self) -> None:
        plan = legacy_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded"],
                "evidence_gate": "required",
            }
        ]
        run = legacy_run(plan, 9)
        run["ui_evidence"] = [
            {
                "surface_id": "dashboard",
                "route": "/dashboard",
                "breakpoint": "desktop",
                "state": "loaded",
                "artifact_path": "docs/goal/evidence/dashboard-desktop-loaded.png",
                "artifact_sha256": "c" * 64,
                "head_sha": run["integration"]["integration_head_sha"],
                "status": "PASS",
            }
        ]

        for field in ("surface_id", "route", "breakpoint", "state", "status"):
            with self.subTest(field=field):
                malformed = copy.deepcopy(run)
                malformed["ui_evidence"][0][field] = []
                errors = validate_run(plan, malformed)
                self.assertTrue(any(f".{field}:" in error for error in errors))

        malformed = copy.deepcopy(run)
        malformed["integration"] = []
        errors = validate_run(plan, malformed)
        self.assertTrue(any("run.integration: must be an object" in error for error in errors))

    def test_schema_v9_rejects_malformed_plan_ui_surfaces_without_crashing(self) -> None:
        plan = legacy_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded"],
                "evidence_gate": "required",
            }
        ]
        evidence = {
            "surface_id": "dashboard",
            "route": "/dashboard",
            "breakpoint": "desktop",
            "state": "loaded",
            "artifact_path": "docs/goal/evidence/dashboard-desktop-loaded.png",
            "artifact_sha256": "c" * 64,
            "head_sha": SHA_A,
            "status": "PASS",
        }

        for missing_field in ("route", "breakpoints", "states"):
            with self.subTest(missing_field=missing_field):
                malformed_plan = copy.deepcopy(plan)
                del malformed_plan["ui_surfaces"][0][missing_field]
                malformed_run = legacy_run(malformed_plan, 9)
                malformed_run["ui_evidence"] = [copy.deepcopy(evidence)]
                self.assertTrue(validate_plan(malformed_plan))
                self.assertTrue(validate_run(malformed_plan, malformed_run))

    def test_current_plan_ui_surfaces_require_two_unique_responsive_targets(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded"],
                "evidence_gate": "required",
            }
        ]
        self.assertTrue(
            any(
                "at least two responsive targets" in error
                for error in validate_plan(plan)
            )
        )

        plan["ui_surfaces"][0]["breakpoints"] = ["desktop", "desktop"]
        self.assertTrue(
            any(
                "duplicate responsive targets" in error
                for error in validate_plan(plan)
            )
        )

        plan["ui_surfaces"][0]["breakpoints"] = ["mobile", "desktop"]
        self.assertFalse(
            any("breakpoints" in error for error in validate_plan(plan))
        )

    def test_complete_run_requires_ready_sources(self) -> None:
        plan = valid_plan()
        plan["sources"][0]["status"] = "missing"
        run = valid_closeout_run(plan)
        mark_complete(plan, run)

        self.assert_run_error_contains(
            plan, run, "complete run requires every source to be frozen or delta accepted"
        )

    def test_complete_run_rejects_malformed_plan_sources_without_crashing(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        plan["sources"] = None

        self.assertTrue(validate_plan(plan))
        self.assertIsInstance(validate_run(plan, run), list)

    def test_na_states_need_no_screenshot_at_closeout(self) -> None:
        """`<state>:n/a` is the documented way to declare an impossible state.

        The design-coverage check strips the suffix, so the closeout matrix has
        to as well — otherwise the only honest way to declare a state a surface
        cannot have is also the one that blocks closeout.
        """
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded", "expired:n/a - session never expires"],
                "evidence_gate": "required",
            }
        ]
        run = valid_closeout_run(plan)
        mark_complete(plan, run)

        errors = validate_run(plan, run)

        self.assertTrue(
            any("missing dashboard|/dashboard|desktop|loaded" in error for error in errors),
            errors,
        )
        self.assertFalse(
            any("expired:n/a" in error for error in errors),
            errors,
        )

    def test_bare_na_marker_is_also_exempt_at_closeout(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded", "expired:n/a"],
                "evidence_gate": "required",
            }
        ]
        run = valid_closeout_run(plan)
        mark_complete(plan, run)

        self.assertFalse(
            any("expired" in error for error in validate_run(plan, run)),
            validate_run(plan, run),
        )

    def test_complete_run_requires_full_ui_screenshot_matrix(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop", "mobile"],
                "states": ["loaded", "empty"],
                "evidence_gate": "required",
            }
        ]
        run = valid_closeout_run(plan)
        mark_complete(plan, run)

        self.assert_run_error_contains(
            plan,
            run,
            "required UI screenshot coverage is missing dashboard|/dashboard|desktop|loaded",
        )

        for breakpoint in ("desktop", "mobile"):
            for state in ("loaded", "empty"):
                run["ui_evidence"].append(
                    {
                        "surface_id": "dashboard",
                        "route": "/dashboard",
                        "breakpoint": breakpoint,
                        "state": state,
                        "artifact_path": (
                            f"docs/goal/evidence/dashboard-{breakpoint}-{state}.png"
                        ),
                        "artifact_sha256": "c" * 64,
                        "head_sha": run["integration"]["integration_head_sha"],
                        "status": "PASS",
                        "target_comparison": {
                            "baseline": "design_system",
                            "baseline_artifact": "check_ui_contract:clean-run",
                            "verdict": "pass",
                        },
                    }
                )
        self.assertEqual(validate_run(plan, run), [])

        run["ui_evidence"][0]["head_sha"] = SHA_B
        self.assert_run_error_contains(
            plan, run, "PASS UI evidence must match integration_head_sha"
        )

    def test_running_ui_evidence_pass_requires_exact_head_sha(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded"],
                "evidence_gate": "required",
            }
        ]
        run = valid_closeout_run(plan)
        run["integration"]["integration_head_sha"] = None
        run["ui_evidence"] = [
            {
                "surface_id": "dashboard",
                "route": "/dashboard",
                "breakpoint": "desktop",
                "state": "loaded",
                "artifact_path": "docs/goal/evidence/dashboard-desktop-loaded.png",
                "artifact_sha256": "c" * 64,
                "head_sha": None,
                "status": "PASS",
            }
        ]

        self.assert_run_error_contains(plan, run, "PASS UI evidence requires head_sha")

    def test_ui_evidence_files_must_exist_and_match_sha256(self) -> None:
        plan = valid_plan()
        plan["ui_surfaces"] = [
            {
                "id": "dashboard",
                "trace_ids": ["REQ-001"],
                "route": "/dashboard",
                "breakpoints": ["desktop"],
                "states": ["loaded"],
                "evidence_gate": "required",
            }
        ]
        run = valid_closeout_run(plan)
        mark_complete(plan, run)
        buffer = io.BytesIO()
        Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
        contents = buffer.getvalue()
        digest = hashlib.sha256(contents).hexdigest()
        run["ui_evidence"] = [
            {
                "surface_id": "dashboard",
                "route": "/dashboard",
                "breakpoint": "desktop",
                "state": "loaded",
                "artifact_path": "docs/goal/evidence/dashboard-desktop-loaded.png",
                "artifact_sha256": digest,
                "head_sha": run["integration"]["integration_head_sha"],
                "status": "PASS",
            }
        ]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Harness Test"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "harness@example.invalid"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            (root / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "base"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            accepted_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            run["integration"]["integration_head_sha"] = accepted_sha
            run["ui_evidence"][0]["head_sha"] = accepted_sha
            evidence = root / "docs" / "goal" / "evidence" / "dashboard-desktop-loaded.png"
            self.assertTrue(
                any("accepted Git commit" in error for error in validate_ui_evidence_files(run, root))
            )
            evidence.parent.mkdir(parents=True)
            evidence.write_bytes(contents)
            subprocess.run(["git", "add", "docs"], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", "accept screenshot"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            accepted_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            run["integration"]["integration_head_sha"] = accepted_sha
            run["ui_evidence"][0]["head_sha"] = accepted_sha
            self.assertEqual(validate_ui_evidence_files(run, root), [])
            run["ui_evidence"][0]["artifact_sha256"] = "d" * 64
            self.assertTrue(
                any("sha256 does not match" in error for error in validate_ui_evidence_files(run, root))
            )
            invalid_contents = b"not an image"
            evidence.write_bytes(invalid_contents)
            run["ui_evidence"][0]["artifact_sha256"] = hashlib.sha256(
                invalid_contents
            ).hexdigest()
            self.assertTrue(
                any(
                    "sha256 does not match" in error
                    for error in validate_ui_evidence_files(run, root)
                )
            )




    def test_run_schema_v5_remains_compatible(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 5)
        self.assertEqual(validate_run(plan, run), [])

    def test_schema_v6_routes_claude_dynamic_workflow(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 6)
        run["runtime_capabilities"] = {
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": 3,
            "runtime_adapter": {
                "provider": "claude_code",
                "available_drivers": [
                    "dynamic_workflow",
                    "subagents",
                    "sequential_parent",
                ],
                "detection_source": "observed",
            },
            "platform_lifecycle": {
                "owner": "parent",
                "automatic_retention_cleanup_possible": False,
                "durable_branch_required_before_unique_work": True,
            },
        }

        self.assertEqual(validate_run(plan, run), [])
        self.assertEqual(
            route_runtime_driver(run["runtime_capabilities"]),
            "dynamic_workflow",
        )

        run["workers"].append(
            {
                "worker_id": "W1",
                "mission_id": "M1",
                "lease_id": "LEASE-1",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "batch_base_sha": SHA_A,
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "task_thread_id": None,
                "worktree_path": "C:/repo/worktrees/M1",
                "branch_ref": "refs/heads/codex/test-m1",
                "report_path": None,
                "phase": "leased",
                "worker_head_sha": None,
                "nested_subagent_policy": {
                    "enabled": False,
                    "max_children": 0,
                    "allowed_roles": [],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
            }
        )
        self.assert_run_error_contains(
            plan,
            run,
            "must be omitted for flat dynamic-workflow orchestration",
        )

    def test_schema_v10_routes_pi_subagents(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["runtime_capabilities"] = {
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": 2,
            "runtime_adapter": {
                "provider": "pi",
                "available_drivers": ["subagents", "sequential_parent"],
                "detection_source": "observed",
            },
            "platform_lifecycle": {
                "owner": "parent",
                "automatic_retention_cleanup_possible": False,
                "durable_branch_required_before_unique_work": True,
            },
        }

        self.assertEqual([], validate_run(plan, run))
        self.assertEqual(
            "subagents",
            route_runtime_driver(run["runtime_capabilities"]),
        )



    def test_schema_v6_rejects_provider_driver_and_axis_mismatches(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 6)
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter.update(
            provider="claude_code",
            available_drivers=["app_threads", "sequential_parent"],
            detection_source="observed",
        )
        self.assert_run_error_contains(plan, run, "drivers do not match provider: app_threads")

        adapter["available_drivers"] = ["dynamic_workflow", "sequential_parent"]
        self.assert_run_error_contains(
            plan,
            run,
            "dynamic_workflow requires claude_code subagent/parent_managed_worktree/agent_result",
        )

    def test_sequential_parent_accepts_parent_managed_worktree(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "parent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": ["sequential_parent"],
                    "detection_source": "observed",
                },
            }
        )

        self.assertEqual([], validate_run(plan, run))

        run["runtime_capabilities"]["completion_channel"] = "thread_poll"
        self.assert_run_error_contains(
            plan,
            run,
            "sequential_parent requires parent/parent_managed_worktree/agent_result",
        )

        run["runtime_capabilities"]["completion_channel"] = "agent_result"
        run["runtime_capabilities"]["workspace_mode"] = "shared_checkout"
        self.assert_run_error_contains(
            plan,
            run,
            "sequential_parent requires parent/parent_managed_worktree/agent_result",
        )

    def test_ready_parallel_codex_requires_complete_capability_probe(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        authorize_execution(run, ["M1", "M2"], status="ready")
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "max_parallel_workers": 2,
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": ["subagents", "sequential_parent"],
                    "detection_source": "observed",
                },
            }
        )
        run["observed"]["runtime"].update(
            {"available_worker_slots": 2, "isolation_capacity": 2}
        )

        self.assert_run_error_contains(
            plan,
            run,
            "capability_snapshot_incomplete",
        )

        run["plan_readiness"] = "blocked"
        self.assert_run_error_contains(
            plan,
            run,
            "capability_snapshot_incomplete",
        )

        run["plan_readiness"] = "ready"
        run["runtime_capabilities"]["runtime_adapter"]["capability_probe"] = (
            codex_capability_probe(unobserved={"app_thread_create"})
        )
        self.assert_run_error_contains(
            plan,
            run,
            "capability_snapshot_incomplete",
        )

    def test_ready_sequential_codex_does_not_require_parallel_probe_inventory(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        authorize_execution(run, ["M1", "M2"], status="ready")
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "parent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "max_parallel_workers": 1,
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": ["sequential_parent"],
                    "detection_source": "observed",
                },
            }
        )
        run["observed"]["runtime"].update(
            {"available_worker_slots": 1, "isolation_capacity": 1}
        )

        self.assertEqual([], validate_run(plan, run))

    def test_codex_probe_prevents_omitting_available_app_threads(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        authorize_execution(run, ["M1", "M2"], status="ready")
        adapter = run["runtime_capabilities"]["runtime_adapter"]
        adapter.update(
            available_drivers=["sequential_parent"],
            detection_source="observed",
            capability_probe=codex_capability_probe(app_threads=True),
        )

        self.assert_run_error_contains(
            plan,
            run,
            "must exactly match capability_probe in provider priority order: app_threads, sequential_parent",
        )

    def test_codex_probe_rejects_malformed_status_without_crashing(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        authorize_execution(run, ["M1", "M2"], status="ready")
        probe = codex_capability_probe()
        probe["app_thread_create"]["status"] = []
        run["runtime_capabilities"]["runtime_adapter"].update(
            detection_source="observed",
            capability_probe=probe,
        )

        self.assert_run_error_contains(
            plan,
            run,
            "app_thread_create.status: has an unsupported value",
        )

    def test_codex_probe_prevents_claiming_unavailable_app_threads(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        authorize_execution(run, ["M1", "M2"], status="ready")
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
            }
        )
        run["runtime_capabilities"]["runtime_adapter"].update(
            available_drivers=["app_threads", "sequential_parent"],
            detection_source="observed",
            capability_probe=codex_capability_probe(),
        )

        self.assert_run_error_contains(
            plan,
            run,
            "must exactly match capability_probe in provider priority order: sequential_parent",
        )

    def test_complete_codex_probe_routes_app_threads_before_subagents(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        authorize_execution(run, ["M1", "M2"], status="ready")
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
            }
        )
        run["runtime_capabilities"]["runtime_adapter"].update(
            available_drivers=["app_threads", "subagents", "sequential_parent"],
            detection_source="observed",
            capability_probe=codex_capability_probe(
                app_threads=True,
                subagents=True,
            ),
        )

        self.assertEqual([], validate_run(plan, run))
        self.assertEqual(
            "app_threads",
            route_runtime_driver(run["runtime_capabilities"]),
        )

    def test_schema_v6_rejects_malformed_runtime_adapter_without_crashing(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 6)
        run["runtime_capabilities"]["runtime_adapter"] = None
        self.assert_run_error_contains(
            plan,
            run,
            "run.runtime_capabilities.runtime_adapter: must be an object",
        )

        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": {},
            "available_drivers": ["sequential_parent"],
            "detection_source": [],
        }
        errors = validate_run(plan, run)
        self.assertTrue(any("provider: has an unsupported value" in error for error in errors))
        self.assertTrue(any("detection_source: has an unsupported value" in error for error in errors))
        self.assertEqual(route_runtime_driver(run["runtime_capabilities"]), "sequential_parent")

    def test_market_provider_ids_run_validate_with_generic_ladder(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 6)
        adapter = {
            "provider": "gemini_cli",
            # The generic ladder must supply this fallback: an unknown
            # provider with an empty ladder would reject every driver.
            "available_drivers": ["sequential_parent"],
            "detection_source": "observed",
        }
        run["runtime_capabilities"]["runtime_adapter"] = adapter
        errors = validate_run(plan, run)
        self.assertFalse(
            any("runtime_adapter" in error for error in errors), errors
        )
        self.assertEqual(
            "sequential_parent", route_runtime_driver(run["runtime_capabilities"])
        )

        adapter["available_drivers"] = ["app_threads"]
        errors = validate_run(plan, run)
        self.assertTrue(
            any("drivers do not match provider" in error for error in errors)
        )

        adapter["provider"] = "Gemini CLI"
        adapter["available_drivers"] = ["subagents", "sequential_parent"]
        errors = validate_run(plan, run)
        self.assertTrue(
            any("provider: has an unsupported value" in error for error in errors)
        )

    def test_runtime_adapter_rejects_external_runtimes_key(self) -> None:
        # The guarded cross-runtime escape hatch (Codex <-> Claude Code) is
        # fully removed: runtime_adapter no longer has any concept of an
        # "external runtime" to record, so the key itself is now unknown.
        plan = valid_plan()
        run = valid_closeout_run(plan)
        self.assertEqual([], validate_run(plan, run))

        run["runtime_capabilities"]["runtime_adapter"]["external_runtimes"] = []
        self.assert_run_error_contains(
            plan,
            run,
            "run.runtime_capabilities.runtime_adapter: unknown keys: external_runtimes",
        )

    def test_runtime_version_gate_validates_status_and_evidence(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        gate = run["runtime_capabilities"]["runtime_adapter"]["version_gate"]

        gate["status"] = "silently_upgrade"
        self.assert_run_error_contains(
            plan,
            run,
            "run.runtime_capabilities.runtime_adapter.version_gate.status: has an unsupported value",
        )

        gate["status"] = []
        self.assert_run_error_contains(
            plan,
            run,
            "run.runtime_capabilities.runtime_adapter.version_gate.status: has an unsupported value",
        )

        gate["status"] = "upgrade_required"
        gate["evidence"] = ""
        self.assert_run_error_contains(
            plan,
            run,
            "run.runtime_capabilities.runtime_adapter.version_gate.evidence: must be a non-empty string",
        )

    def test_worker_runtime_binding_source_must_equal_host(self) -> None:
        # A node's required provider must match whatever host actually runs
        # it: there is no bridged/guarded external source anymore, so
        # runtime_binding.source is exactly "host" or rejected.
        plan = valid_plan()
        run = valid_run(plan)
        digest = plan_digest(plan)
        authorize_execution(run, ["M1"])
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "runtime_adapter": {
                    "provider": "codex",
                    "available_drivers": ["subagents", "sequential_parent"],
                    "detection_source": "fallback",
                },
            }
        )
        worker = {
            "worker_id": "W-M1",
            "mission_id": "M1",
            "lease_id": "LEASE-M1",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "batch_base_sha": SHA_A,
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "runtime_binding": {
                "provider": "codex",
                "driver": "subagents",
                "source": "host",
                "model": None,
                "reasoning_effort": None,
                "option_source": "provider_default",
            },
            "task_thread_id": None,
            "worktree_path": "C:/repo/worktrees/m1",
            "branch_ref": "refs/heads/codex/m1",
            "report_path": None,
            "phase": "leased",
            "worker_head_sha": None,
        }
        run["workers"].append(worker)
        run["observed"]["git"]["worktrees"].append(
            {
                "path": worker["worktree_path"],
                "branch_ref": worker["branch_ref"],
                "head_sha": SHA_A,
                "managed_by": "parent",
                "dirty": False,
            }
        )
        authorize_action(
            run,
            "spawn_subagents",
            ["M1"],
            [f"worker:{worker['worker_id']}"],
        )
        authorize_action(
            run,
            "create_local_worktrees",
            ["M1"],
            [f"worktree:{worker['worktree_path']}"],
        )
        authorize_action(
            run,
            "create_local_branches",
            ["M1"],
            [f"branch:{worker['branch_ref']}"],
        )
        authorize_action(
            run,
            "create_local_commits",
            ["M1"],
            [f"branch:{worker['branch_ref']}"],
        )
        self.assertEqual([], validate_run(plan, run))

        for stale_source in ("external_bridge", "external_agent", "guest", ""):
            with self.subTest(source=stale_source):
                invalid = copy.deepcopy(run)
                invalid["workers"][0]["runtime_binding"]["source"] = stale_source
                self.assert_run_error_contains(
                    plan,
                    invalid,
                    "run.workers[0].runtime_binding.source: has an unsupported value",
                )


































    def test_local_only_landing_rejects_a_pushed_head(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["landing"].update(
            {
                "mode": "local_only",
                "pushed_head_sha": SHA_A,
            }
        )
        self.assert_run_error_contains(
            plan,
            run,
            "local_only mode cannot record a pushed head",
        )

    def test_execution_authorization_requires_source_and_scope(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["execution_authorized"] = True
        self.assert_run_error_contains(run=run, plan=plan, fragment="execution_authorization_source")

        run["execution_authorization_source"] = "user: explicit prompt"
        run["status"] = "ready"
        run["plan_readiness"] = "ready"
        run["execution_authorization_scope"] = {
            "run_id": "RUN-TEST",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "mission_ids": ["M1", "M2"],
            "expires_when": "run_complete",
        }
        run["landing"]["continuity"] = {
            "status": "planned",
            "branch_ref": "refs/heads/codex/test",
            "head_sha": None,
            "reason": None,
        }
        self.assertEqual(validate_run(plan, run), [])

    def test_wave_execution_grant_is_bound_to_the_current_wave(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        authorize_execution(run, ["M1"], status="running")
        run["active_wave"].update(
            {
                "wave_id": "B01",
                "status": "proposed",
                "batch_base_sha": SHA_A,
            }
        )
        run["execution_authorization_scope"]["expires_when"] = "wave_closed"
        self.assert_run_error_contains(
            plan,
            run,
            "run.execution_authorization_scope: missing keys: batch_base_sha, wave_id",
        )
        run["execution_authorization_scope"].update(
            {
                "expires_when": "wave_closed",
                "wave_id": "B01",
                "batch_base_sha": SHA_A,
            }
        )
        self.assertEqual(validate_run(plan, run), [])
        self.assertTrue(execution_covers(run, "M1"))

        run["active_wave"]["wave_id"] = "B02"
        self.assert_run_error_contains(
            plan,
            run,
            "wave_closed scope must match the current active_wave wave_id and batch_base_sha and must not be listed in closed_waves",
        )

    def test_wave_execution_grant_cannot_replay_after_close_and_reopen(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        authorize_execution(run, ["M1"], status="running")
        run["active_wave"].update(
            {
                "wave_id": "B01",
                "status": "proposed",
                "batch_base_sha": SHA_A,
            }
        )
        run["execution_authorization_scope"].update(
            {
                "expires_when": "wave_closed",
                "wave_id": "B01",
                "batch_base_sha": SHA_A,
            }
        )
        self.assertEqual(validate_run(plan, run), [])
        self.assertTrue(execution_covers(run, "M1"))

        # Closing appends a durable tombstone. Re-proposing the same pair is
        # invalid and the old execution grant remains unusable.
        run["closed_waves"].append({"wave_id": "B01", "batch_base_sha": SHA_A})
        self.assert_run_error_contains(
            plan,
            run,
            "proposed or active wave reuses a closed wave identity",
        )
        self.assertFalse(execution_covers(run, "M1"))

        # A renewed base identity is a new wave and accepts a fresh scope.
        run["active_wave"]["batch_base_sha"] = SHA_B
        run["execution_authorization_scope"]["batch_base_sha"] = SHA_B
        self.assertEqual(validate_run(plan, run), [])
        self.assertTrue(execution_covers(run, "M1"))

    def test_closed_wave_requires_identity_and_idle_keeps_the_tombstone(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["active_wave"].update(
            {
                "wave_id": None,
                "status": "closed",
                "batch_base_sha": None,
            }
        )
        self.assert_run_error_contains(
            plan,
            run,
            "closed or superseded wave requires wave_id and batch_base_sha",
        )

        run["active_wave"].update(
            {
                "wave_id": "B01",
                "status": "closed",
                "batch_base_sha": SHA_A,
            }
        )
        run["closed_waves"].append({"wave_id": "B01", "batch_base_sha": SHA_A})
        self.assertEqual(validate_run(plan, run), [])

        run["active_wave"].update(
            {"wave_id": None, "status": "idle", "batch_base_sha": None}
        )
        self.assertEqual(validate_run(plan, run), [])
        run["active_wave"].update(
            {"wave_id": "B01", "status": "proposed", "batch_base_sha": SHA_A}
        )
        self.assert_run_error_contains(
            plan,
            run,
            "proposed or active wave reuses a closed wave identity",
        )

    def test_draft_run_cannot_authorize_execution(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run.update(
            {
                "execution_authorized": True,
                "execution_authorization_source": "user: execute",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "plan_revision": run["plan"]["revision"],
                    "plan_digest_sha256": run["plan"]["digest_sha256"],
                    "mission_ids": ["M1"],
                    "expires_when": "run_complete",
                },
            }
        )
        self.assert_run_error_contains(
            plan,
            run,
            "draft run cannot authorize execution; use ready or running",
        )





    def test_action_authorization_requires_scoped_source(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        entry = run["authorizations"]["create_local_commits"]
        entry.update({"authorized": True, "source": "user: explicit prompt"})
        self.assert_run_error_contains(plan, run, "requires scope and expires_when")

        entry["scope"] = {
            "run_id": "RUN-TEST",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "mission_ids": ["M1"],
            "targets": ["branch:codex/test"],
        }
        run["active_wave"].update(
            {
                "wave_id": "B01",
                "status": "proposed",
                "batch_base_sha": SHA_A,
            }
        )
        entry["scope"].update({"wave_id": "B01", "batch_base_sha": SHA_A})
        entry["expires_when"] = "wave_closed"
        self.assertEqual(validate_run(plan, run), [])

        entry["scope"]["targets"] = ["untyped-target"]
        self.assert_run_error_contains(plan, run, "unsupported target 'untyped-target'")

    def test_action_wave_grant_fails_after_closed_pair_is_reproposed(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        entry = run["authorizations"]["create_local_commits"]
        entry.update(
            {
                "authorized": True,
                "source": "user: explicit prompt",
                "expires_when": "wave_closed",
                "scope": {
                    "run_id": run["run_id"],
                    "plan_revision": plan["revision"],
                    "plan_digest_sha256": plan_digest(plan),
                    "mission_ids": ["M1"],
                    "targets": ["branch:codex/test"],
                    "wave_id": "B01",
                    "batch_base_sha": SHA_A,
                },
            }
        )
        run["active_wave"].update(
            {
                "wave_id": "B01",
                "status": "proposed",
                "batch_base_sha": SHA_A,
            }
        )
        self.assertEqual(validate_run(plan, run), [])
        self.assertTrue(
            authorization_covers(run, "create_local_commits", "M1", "branch:codex/test")
        )

        run["closed_waves"].append({"wave_id": "B01", "batch_base_sha": SHA_A})
        self.assert_run_error_contains(
            plan,
            run,
            "proposed or active wave reuses a closed wave identity",
        )
        self.assertFalse(
            authorization_covers(run, "create_local_commits", "M1", "branch:codex/test")
        )

    def test_malformed_closed_wave_history_fails_action_and_execution_coverage(self) -> None:
        malformed_histories = [
            [{}],
            ["bad"],
            [{"wave_id": "B01", "batch_base_sha": "not-a-sha"}],
            [{"wave_id": "B01", "batch_base_sha": SHA_A, "extra": True}],
            [
                {"wave_id": "B01", "batch_base_sha": SHA_A},
                {"wave_id": "B01", "batch_base_sha": SHA_A},
            ],
        ]
        for history in malformed_histories:
            with self.subTest(history=history):
                plan = valid_plan()
                run = valid_run(plan)
                authorize_execution(run, ["M1"], status="running")
                run["active_wave"].update(
                    {
                        "wave_id": "B01",
                        "status": "proposed",
                        "batch_base_sha": SHA_A,
                    }
                )
                run["execution_authorization_scope"].update(
                    {
                        "expires_when": "wave_closed",
                        "wave_id": "B01",
                        "batch_base_sha": SHA_A,
                    }
                )
                entry = run["authorizations"]["create_local_commits"]
                entry.update(
                    {
                        "authorized": True,
                        "source": "user: explicit prompt",
                        "expires_when": "wave_closed",
                        "scope": {
                            "run_id": run["run_id"],
                            "plan_revision": plan["revision"],
                            "plan_digest_sha256": plan_digest(plan),
                            "mission_ids": ["M1"],
                            "targets": ["branch:codex/test"],
                            "wave_id": "B01",
                            "batch_base_sha": SHA_A,
                        },
                    }
                )
                run["closed_waves"] = history
                self.assertFalse(execution_covers(run, "M1"))
                self.assertFalse(
                    authorization_covers(
                        run,
                        "create_local_commits",
                        "M1",
                        "branch:codex/test",
                    )
                )

    def test_run_schema_rejects_unknown_key(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["runtime_capabilities"]["unexpected"] = True
        self.assert_run_error_contains(plan, run, "unknown keys: unexpected")

    def test_runtime_metrics_accept_machine_events_and_reject_invalid_counts(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["runtime_metrics"] = {
            "target_reduction_percent": {"minimum": 75, "stretch": 85},
            "baseline_wall_time_ms": 1000,
            "run_wall_time_ms": None,
            "critical_path_ms": None,
            "events": [
                {
                    "event_id": "E-001",
                    "provider": "codex",
                    "node_id": "N-M1",
                    "attempt_id": "A-001",
                    "phase": "dispatch",
                    "status": "complete",
                    "started_at": "2026-08-18T00:00:00Z",
                    "completed_at": "2026-08-18T00:00:01Z",
                    "duration_ms": 1000,
                    "wait_ms": 0,
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "cached_input_tokens": 80,
                    "context_bytes": 4096,
                }
            ],
        }
        self.assertEqual(validate_run(plan, run), [])

        run["runtime_metrics"]["events"][0]["cached_input_tokens"] = 101
        self.assert_run_error_contains(plan, run, "must not exceed input_tokens")

    def test_non_graph_schema_v9_rejects_workflow_runs(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 9)
        run["workflow_runs"] = []
        self.assert_run_error_contains(plan, run, "unknown keys: workflow_runs")

    def test_non_graph_schema_v8_is_rejected(self) -> None:
        plan = legacy_plan()
        run = legacy_run(plan, 8)
        run["workflow_runs"] = []
        errors = validate_run(plan, run)
        self.assertTrue(
            any("schema v8 requires a schema v4 graph PLAN" in error for error in errors)
        )
        self.assertTrue(any("unknown keys: workflow_runs" in error for error in errors))



    def test_permission_boundary_accepts_ready_full_access_and_rejects_unknown_ready(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["runtime_capabilities"]["permission_boundary"] = {
            "selected_mode": "full_access",
            "profile_name": None,
            "approval_policy": "never",
            "filesystem_scope": "unrestricted",
            "network_scope": "open",
            "local_binding": "allowed",
            "worker_inheritance": "inherited",
            "status": "ready",
        }
        self.assertEqual(validate_run(plan, run), [])

        run["runtime_capabilities"]["permission_boundary"]["network_scope"] = "unknown"
        self.assert_run_error_contains(
            plan,
            run,
            "cannot be ready while a boundary field is unknown",
        )

    def test_named_permission_profile_requires_profile_name(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["runtime_capabilities"]["permission_boundary"] = {
            "selected_mode": "named_profile",
            "profile_name": None,
            "approval_policy": "on-request",
            "filesystem_scope": "custom",
            "network_scope": "filtered",
            "local_binding": "allowed",
            "worker_inheritance": "inherited",
            "status": "ready",
        }
        self.assert_run_error_contains(plan, run, "is required for named_profile")

    def test_v10_app_task_forbids_nested_delegation_but_legacy_remains_readable(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        digest = plan_digest(plan)
        authorize_execution(run, ["M1"])
        run["runtime_capabilities"] = {
            "worker_runtime": "app_task",
            "workspace_mode": "app_managed_worktree",
            "completion_channel": "thread_poll",
            "max_parallel_workers": 3,
            "runtime_adapter": {
                "provider": "codex",
                "available_drivers": [
                    "app_threads",
                    "subagents",
                    "sequential_parent",
                ],
                "detection_source": "observed",
                "capability_probe": codex_capability_probe(
                    app_threads=True,
                    subagents=True,
                ),
            },
            "nested_subagents": {
                "available": True,
                "max_depth": 1,
                "max_children_per_worker": 3,
                "allowed_roles": ["explorer", "researcher", "reviewer", "tester"],
                "write_policy": "read_only",
                "completion_channel": "agent_result",
            },
            "platform_lifecycle": {
                "owner": "app",
                "automatic_retention_cleanup_possible": True,
                "durable_branch_required_before_unique_work": True,
            },
        }
        run["authorizations"]["spawn_subagents"] = {
            "authorized": True,
            "source": "user: explicit nested-subagent request",
            "scope": {
                "run_id": "RUN-TEST",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "mission_ids": ["M1"],
                "targets": ["worker:W1"],
            },
            "expires_when": "run_complete",
        }
        run["mission_states"]["M1"].update(
            {
                "phase": "leased",
                "lease_id": "LEASE1",
                "lease_plan_revision": 1,
                "lease_plan_digest_sha256": digest,
                "worker_id": "W1",
                "base_sha": SHA_A,
            }
        )
        run["workers"] = [
            {
                "worker_id": "W1",
                "mission_id": "M1",
                "lease_id": "LEASE1",
                "plan_revision": 1,
                "plan_digest_sha256": digest,
                "batch_base_sha": SHA_A,
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "runtime_binding": {
                    "provider": "codex",
                    "driver": "app_threads",
                    "source": "host",
                    "model": None,
                    "reasoning_effort": None,
                    "option_source": "provider_default",
                },
                "nested_subagent_policy": {
                    "enabled": True,
                    "max_children": 3,
                    "allowed_roles": ["explorer", "reviewer", "tester"],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
                "task_thread_id": "THREAD1",
                "worktree_path": "/tmp/app-m1",
                "branch_ref": "refs/heads/codex/app-m1",
                "report_path": None,
                "phase": "leased",
                "worker_head_sha": None,
            }
        ]
        run["observed"]["git"]["worktrees"] = [
            {
                "path": "/tmp/app-m1",
                "branch_ref": "refs/heads/codex/app-m1",
                "head_sha": SHA_A,
                "managed_by": "app",
                "dirty": False,
            }
        ]
        authorize_action(
            run,
            "create_app_managed_worktrees",
            ["M1"],
            ["worktree:/tmp/app-m1"],
        )
        authorize_action(
            run,
            "create_user_owned_tasks",
            ["M1"],
            ["task:THREAD1"],
        )
        authorize_action(
            run,
            "create_local_branches",
            ["M1"],
            ["branch:refs/heads/codex/app-m1"],
        )
        authorize_action(
            run,
            "create_local_commits",
            ["M1"],
            ["branch:refs/heads/codex/app-m1"],
        )
        self.assert_run_error_contains(
            plan,
            run,
            "must be false because RUN-v11 forbids worker-owned delegation",
        )

        legacy_app_plan = legacy_plan()
        legacy_app_run = legacy_run(legacy_app_plan, 6)
        legacy_digest = plan_digest(legacy_app_plan)
        legacy_app_run["runtime_capabilities"] = copy.deepcopy(
            run["runtime_capabilities"]
        )
        legacy_app_run["runtime_capabilities"]["runtime_adapter"].pop(
            "capability_probe"
        )
        legacy_app_run["authorizations"]["spawn_subagents"] = copy.deepcopy(
            run["authorizations"]["spawn_subagents"]
        )
        legacy_scope = legacy_app_run["authorizations"]["spawn_subagents"]["scope"]
        legacy_scope.pop("plan_revision")
        legacy_scope.pop("plan_digest_sha256")
        legacy_app_run["mission_states"]["M1"].update(
            {
                "phase": "leased",
                "lease_id": "LEASE1",
                "lease_plan_revision": legacy_app_plan["revision"],
                "lease_plan_digest_sha256": legacy_digest,
                "worker_id": "W1",
                "base_sha": SHA_A,
            }
        )
        legacy_worker = copy.deepcopy(run["workers"][0])
        legacy_worker["plan_revision"] = legacy_app_plan["revision"]
        legacy_worker["plan_digest_sha256"] = legacy_digest
        legacy_worker["nested_subagent_policy"]["allowed_roles"] = [
            "explorer",
            "tester",
        ]
        legacy_app_run["workers"] = [legacy_worker]
        self.assertEqual(
            [],
            validate_run(legacy_app_plan, legacy_app_run),
            "legacy RUN v6 keeps its previously valid enabled-role policy",
        )

        legacy_scope["targets"] = ["*"]
        self.assertEqual(
            [],
            validate_run(legacy_app_plan, legacy_app_run),
            "legacy RUN v6 keeps wildcard nested spawn authorization compatibility",
        )
        legacy_scope["targets"] = ["worker:W1"]
        del legacy_worker["nested_subagent_policy"]
        self.assert_run_error_contains(
            legacy_app_plan,
            legacy_app_run,
            "is required for app_task workers when runtime nested_subagents is recorded",
        )

        del run["workers"][0]["nested_subagent_policy"]
        self.assertEqual(
            [],
            validate_run(plan, run),
            "an omitted nested policy is the disabled app-task path",
        )
        run["workers"][0]["nested_subagent_policy"] = {
            "enabled": False,
            "max_children": 0,
            "allowed_roles": [],
            "write_policy": "read_only",
            "completion_channel": "agent_result",
        }
        run["authorizations"]["spawn_subagents"] = {
            "authorized": False,
            "source": None,
        }
        self.assertEqual(
            [],
            validate_run(plan, run),
            "an explicitly disabled nested policy needs no spawn grant",
        )


if __name__ == "__main__":
    unittest.main()

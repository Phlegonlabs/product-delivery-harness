#!/usr/bin/env python3
"""Focused, stdlib-only tests for the canonical harness manifest contract."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import (  # noqa: E402
    AUTHORIZATION_KEYS,
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
    validate_scope_claim,
)


SHA_A = "a" * 40
SHA_B = "b" * 40


def verifier(identifier: str, *argv: str) -> dict[str, object]:
    return {
        "id": identifier,
        "cwd": ".",
        "argv": list(argv) or ["python3", "-m", "unittest"],
        "pass_signal": "exit 0",
    }


def task(
    mission_id: str,
    number: int,
    trace_id: str,
    path: str,
    *,
    depends_on: list[str] | None = None,
) -> dict[str, object]:
    task_id = f"{mission_id}/T{number:02d}"
    return {
        "id": task_id,
        "alias": f"task-{number}",
        "objective": f"Complete {task_id}",
        "acceptance_matrix": [f"{task_id} passes"],
        "trace_ids": [trace_id],
        "depends_on": list(depends_on or []),
        "parent_task": None,
        "legacy_task_ids": [],
        "replaced_by": [],
        "split_reason": None,
        "refinement_generation": 0,
        "write_scope": [path],
        "verifiers": [verifier(f"verify-{mission_id.lower()}-{number}", "tool", task_id)],
    }


def mission(
    mission_id: str,
    trace_id: str,
    write_scope: str,
    tasks: list[dict[str, object]],
    *,
    depends_on: list[str] | None = None,
    priority: int = 100,
    merge_rank: int = 10,
) -> dict[str, object]:
    return {
        "id": mission_id,
        "alias": mission_id.lower(),
        "objective": f"Deliver {mission_id}",
        "priority": priority,
        "merge_rank": merge_rank,
        "depends_on": list(depends_on or []),
        "trace_ids": [trace_id],
        "write_scope": [write_scope],
        "deny_scope": ["docs/goal/PLAN.md", "docs/goal/RUN.md"],
        "resource_inventory_complete": True,
        "serialized_resources": [],
        "runtime_resources": [],
        "worktree_eligible": True,
        "stop_conditions": ["Stop on contract conflict"],
        "worker_verifiers": [verifier(f"worker-{mission_id.lower()}", "tool", "worker")],
        "integration_verifiers": [
            verifier(f"integrate-{mission_id.lower()}", "tool", "integration")
        ],
        "tasks": tasks,
    }


def valid_plan() -> dict[str, object]:
    m1_tasks = [
        task("M1", 1, "REQ-001", "src/a/one.py"),
        task(
            "M1",
            2,
            "REQ-001",
            "src/a/two.py",
            depends_on=["M1/T01"],
        ),
    ]
    m1 = mission("M1", "REQ-001", "src/a/**", m1_tasks)
    m1["runtime_resources"] = [
        {"key": "port:3000", "access": "exclusive"},
        {"key": "db:test", "access": "shared_read"},
    ]
    m1["serialized_resources"] = ["migration:primary", "fixture:users"]

    m2 = mission(
        "M2",
        "REQ-002",
        "src/ab/**",
        [task("M2", 1, "REQ-002", "src/ab/one.py")],
        depends_on=["M1"],
        priority=80,
        merge_rank=20,
    )
    m2["runtime_resources"] = [{"key": "port:3001", "access": "exclusive"}]
    return {
        "schema_version": 2,
        "plan_id": "PLAN-TEST",
        "revision": 1,
        "objective": "Deliver a deterministic test plan",
        "max_parallel_workers": 3,
        "sources": [
            {
                "id": "SRC-001",
                "kind": "prd",
                "location": "docs/prd.md",
                "owner": "product",
                "status": "frozen",
                "notes": "product contract",
            },
            {
                "id": "SRC-002",
                "kind": "architecture",
                "location": "docs/architecture.md",
                "owner": "engineering",
                "status": "frozen",
                "notes": "technical contract",
            },
        ],
        "traces": [
            {
                "id": "REQ-001",
                "source_ids": ["SRC-002", "SRC-001"],
                "priority": "must",
                "requirement": "Deliver the first capability",
                "disposition": "planned",
                "rationale": None,
            },
            {
                "id": "REQ-002",
                "source_ids": ["SRC-001"],
                "priority": "should",
                "requirement": "Deliver the second capability",
                "disposition": "planned",
                "rationale": None,
            },
        ],
        "ui_surfaces": [],
        "risks": [],
        "batch_verifiers": [verifier("batch", "tool", "batch")],
        "final_gates": [verifier("final", "tool", "final")],
        "missions": [m1, m2],
    }


def cloudflare_release() -> dict[str, object]:
    return {
        "provider": "cloudflare",
        "targets": [
            {
                "id": "development",
                "source": "pr_head",
                "worker_name": "test-app-development",
                "wrangler_config_path": "apps/web/wrangler.jsonc",
                "wrangler_environment": "development",
                "data_mode": "isolated_non_production",
                "payment_mode": "sandbox",
                "auth_mode": "development",
                "prerequisites": ["current_head_ci"],
                "migration_command": None,
                "deploy_command": verifier(
                    "deploy-development",
                    "npx",
                    "wrangler",
                    "deploy",
                    "--env",
                    "development",
                ),
                "smoke_verifiers": [
                    verifier("smoke-development", "tool", "smoke-development")
                ],
            },
            {
                "id": "production",
                "source": "merged_main",
                "worker_name": "test-app-production",
                "wrangler_config_path": "apps/web/wrangler.jsonc",
                "wrangler_environment": "production",
                "data_mode": "production",
                "payment_mode": "live",
                "auth_mode": "production",
                "prerequisites": ["development_pass", "merged_main"],
                "migration_command": None,
                "deploy_command": verifier(
                    "deploy-production",
                    "npx",
                    "wrangler",
                    "deploy",
                    "--env",
                    "production",
                ),
                "smoke_verifiers": [
                    verifier("smoke-production", "tool", "smoke-production")
                ],
            },
        ],
    }


def valid_release_plan() -> dict[str, object]:
    plan = valid_plan()
    plan["schema_version"] = 3
    plan["release"] = cloudflare_release()
    return plan


def valid_run(plan: dict[str, object]) -> dict[str, object]:
    digest = plan_digest(plan)
    mission_ids = [item["id"] for item in plan["missions"]]
    task_ids = [
        item["id"]
        for current_mission in plan["missions"]
        for item in current_mission["tasks"]
    ]
    return {
        "schema_version": 6,
        "run_id": "RUN-TEST",
        "plan": {
            "id": plan["plan_id"],
            "revision": plan["revision"],
            "digest_sha256": digest,
        },
        "status": "draft",
        "intent": "plan-only",
        "plan_readiness": "draft",
        "execution_authorized": False,
        "execution_authorization_source": None,
        "execution_authorization_scope": None,
        "authorizations": {
            key: {"authorized": False, "source": None}
            for key in AUTHORIZATION_KEYS
        },
        "runtime_capabilities": {
            "worker_runtime": "parent",
            "workspace_mode": "shared_checkout",
            "completion_channel": "agent_result",
            "max_parallel_workers": 1,
            "runtime_adapter": {
                "provider": "generic",
                "available_drivers": ["sequential_parent"],
                "detection_source": "fallback",
            },
            "platform_lifecycle": {
                "owner": "parent",
                "automatic_retention_cleanup_possible": False,
                "durable_branch_required_before_unique_work": True,
            },
        },
        "observed": {
            "captured_at": None,
            "git": {
                "parent_worktree_path": "C:/repo/fullstack-goal-dev",
                "parent_branch": "main",
                "parent_head_sha": SHA_A,
                "parent_dirty": False,
                "worktrees": [],
            },
            "runtime": {
                "available_worker_slots": 1,
                "isolation_capacity": 1,
                "completion_channel_available": True,
            },
        },
        "integration": {
            "branch": "codex/test",
            "batch_base_sha": SHA_A,
            "integration_head_sha": SHA_A,
        },
        "landing": {
            "mode": "pull_request",
            "remote": "origin",
            "head_branch": "codex/test",
            "base_branch": "main",
            "pushed_head_sha": None,
            "pr_number": None,
            "pr_url": None,
            "pr_state": "not_created",
            "pr_head_sha": None,
            "checks_status": "not_started",
            "checks_head_sha": None,
            "review_status": "not_requested",
            "review_head_sha": None,
            "blocking_findings": None,
            "unresolved_threads": None,
            "merge_status": "not_ready",
            "merged_sha": None,
            "auto_merge_requested": False,
            "auto_merge_head_sha": None,
        },
        "post_merge_cleanup": {
            "status": "not_started",
            "base": {
                "branch": "main",
                "head_sha": None,
                "merged_sha_reachable": None,
            },
            "worktree": {
                "path": None,
                "branch_ref": None,
                "head_sha": None,
                "dirty": None,
                "managed_by": None,
                "status": "not_applicable",
            },
            "local_branch": {
                "ref": None,
                "head_sha": None,
                "status": "pending",
            },
            "evidence": [],
            "deferred_reason": None,
        },
        "mission_states": {
            mission_id: {
                "phase": "queued",
                "lease_id": None,
                "lease_plan_revision": None,
                "lease_plan_digest_sha256": None,
                "worker_id": None,
                "base_sha": None,
                "head_sha": None,
                "integration_gate": "planned",
                "integrated_sha": None,
                "blockers": [],
                "report_path": None,
            }
            for mission_id in mission_ids
        },
        "task_states": {
            task_id: {
                "phase": "queued",
                "attempts": 0,
                "commit_sha": None,
                "verifier_status": "planned",
                "blockers": [],
                "refinement_request": None,
            }
            for task_id in task_ids
        },
        "active_wave": {
            "wave_id": None,
            "status": "idle",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "batch_base_sha": None,
            "selected_missions": [],
            "deferred_missions": [],
            "conflict_edges": [],
        },
        "workers": [],
        "attempt_log": [],
    }


def valid_release_run(plan: dict[str, object]) -> dict[str, object]:
    run = valid_run(plan)
    run["schema_version"] = 7
    run["deployments"] = {
        "provider": "cloudflare",
        "development": {
            "status": "not_started",
            "source_sha": None,
            "worker_name": None,
            "url": None,
            "version_id": None,
            "migration_status": "not_started",
            "verification_status": "not_started",
            "rollback_version": None,
            "evidence": [],
        },
        "production": {
            "status": "not_started",
            "source_sha": None,
            "worker_name": None,
            "url": None,
            "version_id": None,
            "migration_status": "not_started",
            "verification_status": "not_started",
            "rollback_version": None,
            "evidence": [],
        },
    }
    return run


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

    def test_schema_v3_cloudflare_release_contract(self) -> None:
        plan = valid_release_plan()
        self.assertEqual(validate_plan(plan), [])

        same_worker = copy.deepcopy(plan)
        same_worker["release"]["targets"][1]["worker_name"] = (
            same_worker["release"]["targets"][0]["worker_name"]
        )
        self.assert_error_contains(same_worker, "worker_name must differ")

        live_development = copy.deepcopy(plan)
        live_development["release"]["targets"][0]["payment_mode"] = "live"
        self.assert_error_contains(live_development, "must be sandbox or not_applicable")

        missing_promotion_gate = copy.deepcopy(plan)
        missing_promotion_gate["release"]["targets"][1]["prerequisites"] = [
            "merged_main"
        ]
        self.assert_error_contains(missing_promotion_gate, "must include development_pass")

    def test_schema_v3_release_rejects_malformed_values_without_crashing(self) -> None:
        malformed_id = valid_release_plan()
        malformed_id["release"]["targets"][0]["id"] = {}
        self.assert_error_contains(malformed_id, "must be development or production")

        malformed_config = valid_release_plan()
        malformed_config["release"]["targets"][0]["wrangler_config_path"] = {}
        self.assert_error_contains(malformed_config, "must be a non-empty string")

        malformed_prerequisites = valid_release_plan()
        malformed_prerequisites["release"]["targets"][0]["prerequisites"] = None
        self.assert_error_contains(
            malformed_prerequisites,
            "must be a list of non-empty strings",
        )

    def test_strict_unknown_keys(self) -> None:
        plan = valid_plan()
        plan["unexpected"] = True
        self.assert_error_contains(plan, "unknown keys: unexpected")

        plan = valid_plan()
        plan["missions"][0]["tasks"][0]["unexpected"] = True
        self.assert_error_contains(plan, "unknown keys: unexpected")

    def test_mission_and_task_cycles(self) -> None:
        plan = valid_plan()
        plan["missions"][0]["depends_on"] = ["M2"]
        self.assert_error_contains(plan, "dependency cycle includes M1, M2")

        plan = valid_plan()
        plan["missions"][0]["tasks"][0]["depends_on"] = ["M1/T02"]
        self.assert_error_contains(plan, "dependency cycle includes M1/T01, M1/T02")

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

    def test_schema_v7_promotes_exact_cloudflare_shas(self) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self.assertEqual(validate_run(plan, run), [])

        run["authorizations"]["deploy"] = {
            "authorized": True,
            "source": "user: deploy development and production for this run",
            "scope": {
                "run_id": "RUN-TEST",
                "mission_ids": ["M1", "M2"],
                "targets": [
                    "environment:development",
                    "environment:production",
                ],
            },
            "expires_when": "run_complete",
        }
        run["landing"].update(
            {
                "pushed_head_sha": SHA_A,
                "pr_number": 7,
                "pr_url": "https://github.com/example/repo/pull/7",
                "pr_state": "open",
                "pr_head_sha": SHA_A,
                "checks_status": "PASS",
                "checks_head_sha": SHA_A,
            }
        )
        run["deployments"]["development"].update(
            {
                "status": "PASS",
                "source_sha": SHA_A,
                "worker_name": "test-app-development",
                "url": "https://test-app-development.example.workers.dev",
                "version_id": "dev-version-1",
                "migration_status": "not_required",
                "verification_status": "PASS",
                "evidence": ["artifact:development-smoke"],
            }
        )
        self.assertEqual(validate_run(plan, run), [])

        run["deployments"]["production"].update(
            {
                "status": "PASS",
                "source_sha": SHA_B,
                "worker_name": "test-app-production",
                "url": "https://test-app-production.example.workers.dev",
                "version_id": "prod-version-1",
                "migration_status": "not_required",
                "verification_status": "PASS",
                "evidence": ["artifact:production-smoke"],
            }
        )
        self.assert_run_error_contains(plan, run, "bind to the merged main SHA")

        run["landing"].update(
            {
                "pr_state": "merged",
                "review_status": "PASS",
                "review_head_sha": SHA_A,
                "blocking_findings": 0,
                "unresolved_threads": 0,
                "merge_status": "merged",
                "merged_sha": SHA_B,
            }
        )
        self.assertEqual(validate_run(plan, run), [])

        run["deployments"]["production"]["worker_name"] = "wrong-production"
        self.assert_run_error_contains(plan, run, "must match PLAN release target")

    def test_release_plan_requires_schema_v7_run(self) -> None:
        plan = valid_release_plan()
        run = valid_run(plan)
        self.assert_run_error_contains(
            plan,
            run,
            "must equal 7 when a schema v3 PLAN declares release",
        )

        run["schema_version"] = 7
        self.assert_run_error_contains(plan, run, "missing keys: deployments")

    def test_schema_v3_and_v7_do_not_enable_release_fields_by_version_alone(self) -> None:
        plan = valid_plan()
        plan["schema_version"] = 3
        self.assertEqual(validate_plan(plan), [])

        run = valid_run(plan)
        run["schema_version"] = 7
        self.assertEqual(validate_run(plan, run), [])

        release_run = valid_release_run(valid_release_plan())
        run["deployments"] = release_run["deployments"]
        self.assert_run_error_contains(
            plan,
            run,
            "deployment state requires a PLAN release contract",
        )

    def test_schema_v7_rejects_malformed_deployment_values_without_crashing(self) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        run["deployments"]["development"].update(
            {
                "status": {},
                "source_sha": [],
                "worker_name": {},
                "migration_status": [],
                "verification_status": {},
                "evidence": None,
            }
        )
        errors = validate_run(plan, run)
        self.assertTrue(any("has an unsupported value" in error for error in errors))
        self.assertTrue(any("must be null or a non-empty string" in error for error in errors))

    def test_run_schema_v2_remains_compatible(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["schema_version"] = 2
        del run["runtime_capabilities"]["runtime_adapter"]
        del run["landing"]
        del run["post_merge_cleanup"]
        del run["observed"]["git"]["parent_worktree_path"]
        for action in ("configure_repository", "manage_pr_review", "merge_pr"):
            del run["authorizations"][action]
        self.assertEqual(validate_run(plan, run), [])

    def test_run_schema_v3_remains_compatible(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["schema_version"] = 3
        del run["runtime_capabilities"]["runtime_adapter"]
        del run["post_merge_cleanup"]
        del run["observed"]["git"]["parent_worktree_path"]
        del run["landing"]["auto_merge_requested"]
        del run["landing"]["auto_merge_head_sha"]
        self.assertEqual(validate_run(plan, run), [])

    def test_run_schema_v4_remains_compatible(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["schema_version"] = 4
        del run["runtime_capabilities"]["runtime_adapter"]
        del run["post_merge_cleanup"]
        del run["observed"]["git"]["parent_worktree_path"]
        self.assertEqual(validate_run(plan, run), [])

    def test_run_schema_v5_remains_compatible(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["schema_version"] = 5
        del run["runtime_capabilities"]["runtime_adapter"]
        self.assertEqual(validate_run(plan, run), [])

    def test_schema_v6_routes_claude_dynamic_workflow(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
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
        self.assertEqual(route_runtime_driver(run["runtime_capabilities"]), "dynamic_workflow")

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

    def test_schema_v6_rejects_provider_driver_and_axis_mismatches(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
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

    def test_schema_v6_rejects_malformed_runtime_adapter_without_crashing(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
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

    def test_post_merge_cleanup_binds_to_merged_pr_and_exact_branch(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["integration"]["integration_head_sha"] = SHA_A
        run["landing"].update(
            {
                "pushed_head_sha": SHA_A,
                "pr_number": 7,
                "pr_url": "https://github.com/example/repo/pull/7",
                "pr_state": "merged",
                "pr_head_sha": SHA_A,
                "checks_status": "PASS",
                "checks_head_sha": SHA_A,
                "review_status": "PASS",
                "review_head_sha": SHA_A,
                "blocking_findings": 0,
                "unresolved_threads": 0,
                "merge_status": "merged",
                "merged_sha": SHA_B,
            }
        )
        for state in run["mission_states"].values():
            state.update(
                {
                    "phase": "integrated",
                    "integration_gate": "PASS",
                    "integrated_sha": SHA_A,
                }
            )
        run["observed"].update(
            {
                "captured_at": "2026-07-15T08:00:00Z",
                "git": {
                    "parent_worktree_path": "C:/repo/fullstack-goal-dev",
                    "parent_branch": "codex/test",
                    "parent_head_sha": SHA_A,
                    "parent_dirty": False,
                    "worktrees": [],
                },
            }
        )
        run["authorizations"]["delete_branches"] = {
            "authorized": True,
            "source": "user: remove the merged local feature branch",
            "scope": {
                "run_id": "RUN-TEST",
                "mission_ids": ["M1", "M2"],
                "targets": ["branch:refs/heads/codex/test"],
            },
            "expires_when": "run_complete",
        }
        run["post_merge_cleanup"] = {
            "status": "ready",
            "base": {
                "branch": "main",
                "head_sha": SHA_B,
                "merged_sha_reachable": True,
            },
            "worktree": {
                "path": None,
                "branch_ref": None,
                "head_sha": None,
                "dirty": None,
                "managed_by": None,
                "status": "not_applicable",
            },
            "local_branch": {
                "ref": "refs/heads/codex/test",
                "head_sha": SHA_A,
                "status": "pending",
            },
            "evidence": [],
            "deferred_reason": None,
        }
        self.assertEqual(validate_run(plan, run), [])

        run["status"] = "complete"
        self.assert_run_error_contains(
            plan,
            run,
            "a completed pull-request run must complete or defer cleanup",
        )
        run["status"] = "draft"

        run["observed"]["git"]["parent_head_sha"] = SHA_B
        self.assert_run_error_contains(
            plan,
            run,
            "parent_head_sha: must match the merged PR head while the primary checkout is on the cleanup branch",
        )
        run["observed"]["git"]["parent_head_sha"] = SHA_A

        run["post_merge_cleanup"]["local_branch"]["head_sha"] = SHA_B
        self.assert_run_error_contains(
            plan,
            run,
            "local_branch.head_sha: must match the merged PR head SHA",
        )
        run["post_merge_cleanup"]["local_branch"]["head_sha"] = SHA_A

        run["post_merge_cleanup"].update(
            {
                "status": "complete",
                "local_branch": {
                    "ref": "refs/heads/codex/test",
                    "head_sha": SHA_A,
                    "status": "deleted",
                },
                "evidence": [
                    "git worktree list --porcelain: no linked target",
                    "git branch --list codex/test: absent",
                ],
            }
        )
        run["observed"]["git"].update(
            {
                "parent_branch": "main",
                "parent_head_sha": SHA_B,
            }
        )
        run["status"] = "complete"
        self.assertEqual(validate_run(plan, run), [])

        run["observed"]["git"]["worktrees"] = [
            {
                "path": "C:/tmp/still-linked",
                "branch_ref": "refs/heads/codex/test",
                "head_sha": SHA_A,
                "managed_by": "parent",
                "dirty": False,
            }
        ]
        self.assert_run_error_contains(
            plan,
            run,
            "not_applicable requires no matching linked worktree",
        )
        run["observed"]["git"]["worktrees"][0]["head_sha"] = SHA_B
        self.assert_run_error_contains(
            plan,
            run,
            "not_applicable requires no matching linked worktree",
        )
        run["observed"]["git"]["worktrees"] = []

    def test_post_merge_cleanup_requires_clean_observed_worktree(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["integration"]["integration_head_sha"] = SHA_A
        run["landing"].update(
            {
                "pushed_head_sha": SHA_A,
                "pr_number": 7,
                "pr_url": "https://github.com/example/repo/pull/7",
                "pr_state": "merged",
                "pr_head_sha": SHA_A,
                "checks_status": "PASS",
                "checks_head_sha": SHA_A,
                "review_status": "PASS",
                "review_head_sha": SHA_A,
                "blocking_findings": 0,
                "unresolved_threads": 0,
                "merge_status": "merged",
                "merged_sha": SHA_B,
            }
        )
        for state in run["mission_states"].values():
            state.update(
                {
                    "phase": "integrated",
                    "integration_gate": "PASS",
                    "integrated_sha": SHA_A,
                }
            )
        path = "C:/tmp/fullstack-goal-dev-cleanup"
        run["observed"] = {
            "captured_at": "2026-07-15T08:00:00Z",
            "git": {
                "parent_worktree_path": "C:/repo/fullstack-goal-dev",
                "parent_branch": "main",
                "parent_head_sha": SHA_B,
                "parent_dirty": False,
                "worktrees": [
                    {
                        "path": path,
                        "branch_ref": "refs/heads/codex/test",
                        "head_sha": SHA_A,
                        "managed_by": "parent",
                        "dirty": False,
                    }
                ],
            },
            "runtime": {
                "available_worker_slots": 1,
                "isolation_capacity": 1,
                "completion_channel_available": True,
            },
        }
        for action, target in (
            ("delete_branches", "branch:refs/heads/codex/test"),
            ("remove_worktrees", f"worktree:{path}"),
        ):
            run["authorizations"][action] = {
                "authorized": True,
                "source": f"user: authorize {action}",
                "scope": {
                    "run_id": "RUN-TEST",
                    "mission_ids": ["M1", "M2"],
                    "targets": [target],
                },
                "expires_when": "run_complete",
            }
        run["post_merge_cleanup"] = {
            "status": "ready",
            "base": {
                "branch": "main",
                "head_sha": SHA_B,
                "merged_sha_reachable": True,
            },
            "worktree": {
                "path": path,
                "branch_ref": "refs/heads/codex/test",
                "head_sha": SHA_A,
                "dirty": False,
                "managed_by": "parent",
                "status": "pending",
            },
            "local_branch": {
                "ref": "refs/heads/codex/test",
                "head_sha": SHA_A,
                "status": "pending",
            },
            "evidence": [],
            "deferred_reason": None,
        }
        self.assertEqual(validate_run(plan, run), [])

        run["observed"]["git"]["worktrees"][0]["managed_by"] = "app"
        self.assert_run_error_contains(
            plan,
            run,
            "ready cleanup must match an observed clean parent-managed worktree",
        )
        run["observed"]["git"]["worktrees"][0]["managed_by"] = "parent"

        run["post_merge_cleanup"]["worktree"]["dirty"] = True
        self.assert_run_error_contains(plan, run, "worktree.dirty: must be false before removal")
        run["post_merge_cleanup"]["worktree"]["dirty"] = False

        run["post_merge_cleanup"]["worktree"]["path"] = "C:/repo/fullstack-goal-dev"
        self.assert_run_error_contains(plan, run, "worktree.path: must not target the primary checkout")
        run["post_merge_cleanup"]["worktree"]["path"] = path

        run["post_merge_cleanup"]["status"] = "complete"
        run["post_merge_cleanup"]["worktree"]["status"] = "removed"
        run["post_merge_cleanup"]["local_branch"]["status"] = "deleted"
        run["post_merge_cleanup"]["evidence"] = ["worktree and local branch absent"]
        run["observed"]["git"]["worktrees"] = []
        run["status"] = "complete"
        self.assertEqual(validate_run(plan, run), [])

        run["post_merge_cleanup"]["worktree"]["managed_by"] = "app"
        self.assert_run_error_contains(
            plan,
            run,
            "manual cleanup worktrees must be parent-managed",
        )

    def test_post_merge_cleanup_not_applicable_rejects_linked_worktree(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["status"] = "complete"
        run["post_merge_cleanup"]["status"] = "not_applicable"
        run["observed"]["captured_at"] = "2026-07-15T08:00:00Z"
        run["observed"]["git"]["worktrees"] = [
            {
                "path": "C:/tmp/still-linked",
                "branch_ref": "refs/heads/codex/test",
                "head_sha": SHA_B,
                "managed_by": "parent",
                "dirty": False,
            }
        ]
        self.assert_run_error_contains(
            plan,
            run,
            "not_applicable requires no matching linked worktree in the current observation",
        )

    def test_post_merge_cleanup_can_be_deferred_for_platform_lifecycle(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["status"] = "complete"
        run["post_merge_cleanup"].update(
            {
                "status": "deferred",
                "worktree": {
                    "path": None,
                    "branch_ref": None,
                    "head_sha": None,
                    "dirty": None,
                    "managed_by": "app",
                    "status": "platform_managed",
                },
                "local_branch": {
                    "ref": None,
                    "head_sha": None,
                    "status": "deferred",
                },
                "deferred_reason": "Codex manages this worktree through app retention",
            }
        )
        self.assertEqual(validate_run(plan, run), [])

    def test_landing_ready_binds_checks_and_review_to_current_pr_head(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["landing"].update(
            {
                "pushed_head_sha": SHA_A,
                "pr_number": 7,
                "pr_url": "https://github.com/example/repo/pull/7",
                "pr_state": "open",
                "pr_head_sha": SHA_A,
                "checks_status": "PASS",
                "checks_head_sha": SHA_A,
                "review_status": "PASS",
                "review_head_sha": SHA_A,
                "blocking_findings": 0,
                "unresolved_threads": 0,
                "merge_status": "ready",
            }
        )
        self.assertEqual(validate_run(plan, run), [])

        run["integration"]["branch"] = "main"
        self.assert_run_error_contains(
            plan,
            run,
            "pull_request mode requires integration.branch to match head_branch",
        )
        run["integration"]["branch"] = "codex/test"

        run["landing"]["review_head_sha"] = SHA_B
        self.assert_run_error_contains(plan, run, "PASS review must bind to a created PR's current head")

        run["landing"]["review_head_sha"] = SHA_A
        run["landing"]["merge_status"] = "not_ready"
        run["integration"]["integration_head_sha"] = SHA_B
        self.assert_run_error_contains(
            plan,
            run,
            "PASS landing evidence requires the current PR head to match integration_head_sha",
        )

        run["integration"]["integration_head_sha"] = SHA_A
        run["landing"].update(
            {
                "pr_state": "merged",
                "merge_status": "merged",
                "merged_sha": SHA_B,
            }
        )
        self.assertEqual(validate_run(plan, run), [])

        run["landing"]["checks_status"] = "not_started"
        run["landing"]["checks_head_sha"] = None
        self.assert_run_error_contains(
            plan,
            run,
            "merged status requires the matching PR state with current-head PASS checks and review",
        )

        run["landing"].update(
            {
                "pr_state": "closed",
                "checks_status": "not_started",
                "checks_head_sha": None,
                "review_status": "not_requested",
                "review_head_sha": None,
                "blocking_findings": None,
                "unresolved_threads": None,
                "merge_status": "closed_unmerged",
                "merged_sha": None,
            }
        )
        self.assertEqual(validate_run(plan, run), [])

        run["landing"]["merged_sha"] = SHA_B
        self.assert_run_error_contains(
            plan,
            run,
            "only merged status may record merged_sha",
        )

        run["landing"]["merged_sha"] = None
        run["landing"]["merge_status"] = "not_ready"
        self.assert_run_error_contains(
            plan,
            run,
            "closed PR requires merge_status closed_unmerged",
        )

        run = valid_run(plan)
        run["landing"].update(
            {
                "checks_status": "PASS",
                "review_status": "PASS",
                "blocking_findings": 0,
                "unresolved_threads": 0,
            }
        )
        self.assert_run_error_contains(plan, run, "PASS checks must bind to a created PR's current head")

    def test_repository_configuration_has_its_own_authorization_target(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["authorizations"]["configure_repository"] = {
            "authorized": True,
            "source": "user: configure GitHub review flow",
            "scope": {
                "run_id": "RUN-TEST",
                "mission_ids": ["M1", "M2"],
                "targets": ["repository:example/repo"],
            },
            "expires_when": "run_complete",
        }
        self.assertEqual(validate_run(plan, run), [])

        malformed = copy.deepcopy(run)
        malformed["post_merge_cleanup"]["base"] = []
        malformed_errors = validate_run(plan, malformed)
        self.assertTrue(
            any("run.post_merge_cleanup.base: must be an object" in error for error in malformed_errors)
        )

    def test_schema_v6_accepts_only_bounded_future_pr_authorization(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        future_target = "future-pr:example/repo:base=main:head=codex/test"
        for action in ("manage_pr_review", "merge_pr"):
            run["authorizations"][action] = {
                "authorized": True,
                "source": "user: land the planned pull request",
                "scope": {
                    "run_id": "RUN-TEST",
                    "mission_ids": ["M1", "M2"],
                    "targets": [future_target],
                },
                "expires_when": "run_complete",
            }
        self.assertEqual(validate_run(plan, run), [])

        malformed = copy.deepcopy(run)
        malformed["authorizations"]["merge_pr"]["scope"]["targets"] = [
            "future-pr:example/repo:head=codex/test"
        ]
        self.assert_run_error_contains(plan, malformed, "unsupported target")

        unrelated = copy.deepcopy(run)
        unrelated["authorizations"]["push"] = copy.deepcopy(
            unrelated["authorizations"]["merge_pr"]
        )
        self.assert_run_error_contains(plan, unrelated, "unsupported target")

        legacy = copy.deepcopy(run)
        legacy["schema_version"] = 5
        self.assert_run_error_contains(plan, legacy, "unsupported target")

    def test_future_pr_authorization_resolves_to_the_matching_exact_pr(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["landing"].update(
            {
                "pushed_head_sha": SHA_A,
                "pr_number": 7,
                "pr_url": "https://github.com/example/repo/pull/7",
                "pr_state": "open",
                "pr_head_sha": SHA_A,
                "checks_status": "PASS",
                "checks_head_sha": SHA_A,
                "review_status": "PASS",
                "review_head_sha": SHA_A,
                "blocking_findings": 0,
                "unresolved_threads": 0,
                "merge_status": "ready",
                "auto_merge_requested": True,
                "auto_merge_head_sha": SHA_A,
            }
        )
        run["authorizations"]["merge_pr"] = {
            "authorized": True,
            "source": "user: land the planned pull request",
            "scope": {
                "run_id": "RUN-TEST",
                "mission_ids": ["M1", "M2"],
                "targets": ["future-pr:example/repo:base=main:head=codex/test"],
            },
            "expires_when": "run_complete",
        }
        self.assert_run_error_contains(
            plan,
            run,
            "auto_merge_requested requires matching merge_pr authorization for the exact PR",
        )

        run["authorizations"]["merge_pr"]["scope"]["targets"].append(
            "pr:https://github.com/example/repo/pull/7"
        )
        self.assertEqual(validate_run(plan, run), [])

        run["authorizations"]["merge_pr"]["scope"]["targets"][0] = (
            "future-pr:example/repo:base=main:head=codex/other"
        )
        self.assert_run_error_contains(
            plan,
            run,
            "auto_merge_requested exact PR does not match its authorized future PR binding",
        )

    def test_auto_merge_requires_a_ready_current_head(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["landing"].update(
            {
                "pushed_head_sha": SHA_A,
                "pr_number": 7,
                "pr_url": "https://github.com/example/repo/pull/7",
                "pr_state": "open",
                "pr_head_sha": SHA_A,
                "checks_status": "PASS",
                "checks_head_sha": SHA_A,
                "review_status": "PASS",
                "review_head_sha": SHA_A,
                "blocking_findings": 0,
                "unresolved_threads": 0,
                "merge_status": "ready",
                "auto_merge_requested": True,
                "auto_merge_head_sha": SHA_A,
            }
        )
        self.assert_run_error_contains(
            plan,
            run,
            "auto_merge_requested requires matching merge_pr authorization for the exact PR",
        )
        run["authorizations"]["merge_pr"] = {
            "authorized": True,
            "source": "user: auto-merge ready PR",
            "scope": {
                "run_id": "RUN-TEST",
                "mission_ids": ["M1", "M2"],
                "targets": ["pr:https://github.com/example/repo/pull/7"],
            },
            "expires_when": "run_complete",
        }
        self.assertEqual(validate_run(plan, run), [])

        malformed = copy.deepcopy(run)
        malformed["authorizations"] = []
        malformed_errors = validate_run(plan, malformed)
        self.assertTrue(
            any("run.authorizations: must be an object" in error for error in malformed_errors)
        )
        self.assertTrue(
            any(
                "auto_merge_requested requires matching merge_pr authorization for the exact PR"
                in error
                for error in malformed_errors
            )
        )

        run["authorizations"]["merge_pr"]["scope"]["targets"] = [
            "pr:https://github.com/example/repo/pull/8"
        ]
        self.assert_run_error_contains(
            plan,
            run,
            "auto_merge_requested requires matching merge_pr authorization for the exact PR",
        )
        run["authorizations"]["merge_pr"]["scope"]["targets"] = [
            "pr:https://github.com/example/repo/pull/7"
        ]

        run["status"] = "complete"
        self.assert_run_error_contains(
            plan,
            run,
            "auto_merge_requested requires matching merge_pr authorization for the exact PR",
        )
        run["status"] = "draft"

        run["landing"].update(
            {
                "pr_state": "merged",
                "merge_status": "merged",
                "merged_sha": SHA_B,
            }
        )
        self.assertEqual(validate_run(plan, run), [])
        run["status"] = "complete"
        run["post_merge_cleanup"]["status"] = "deferred"
        run["post_merge_cleanup"]["deferred_reason"] = "cleanup authorization is tested separately"
        self.assertEqual(validate_run(plan, run), [])
        run["authorizations"]["merge_pr"]["expires_when"] = "wave_closed"
        run["active_wave"]["status"] = "closed"
        self.assert_run_error_contains(
            plan,
            run,
            "auto_merge_requested requires matching merge_pr authorization for the exact PR",
        )
        run["authorizations"]["merge_pr"]["expires_when"] = "run_complete"
        run["active_wave"]["status"] = "idle"
        run["status"] = "draft"
        run["post_merge_cleanup"]["status"] = "not_started"
        run["post_merge_cleanup"]["deferred_reason"] = None
        run["landing"].update(
            {
                "pr_state": "open",
                "merge_status": "ready",
                "merged_sha": None,
            }
        )

        run["landing"]["auto_merge_head_sha"] = SHA_B
        self.assert_run_error_contains(
            plan,
            run,
            "auto_merge_requested requires a ready or merged current-head PR",
        )

        run["landing"]["auto_merge_head_sha"] = SHA_A
        run["landing"]["merge_status"] = "not_ready"
        self.assert_run_error_contains(
            plan,
            run,
            "auto_merge_requested requires a ready or merged current-head PR",
        )

        run["landing"]["auto_merge_requested"] = False
        self.assert_run_error_contains(
            plan,
            run,
            "auto_merge_head_sha: must be null when auto_merge_requested is false",
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
        run["execution_authorization_scope"] = {
            "run_id": "RUN-TEST",
            "mission_ids": ["M1", "M2"],
            "expires_when": "run_complete",
        }
        self.assertEqual(validate_run(plan, run), [])

    def test_action_authorization_requires_scoped_source(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        entry = run["authorizations"]["create_local_commits"]
        entry.update({"authorized": True, "source": "user: explicit prompt"})
        self.assert_run_error_contains(plan, run, "requires scope and expires_when")

        entry["scope"] = {
            "run_id": "RUN-TEST",
            "mission_ids": ["M1"],
            "targets": ["branch:codex/test"],
        }
        entry["expires_when"] = "wave_closed"
        self.assertEqual(validate_run(plan, run), [])

        entry["scope"]["targets"] = ["untyped-target"]
        self.assert_run_error_contains(plan, run, "unsupported target 'untyped-target'")

    def test_run_schema_rejects_unknown_key(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["runtime_capabilities"]["unexpected"] = True
        self.assert_run_error_contains(plan, run, "unknown keys: unexpected")

    def test_invalid_run_schema_does_not_crash_auto_merge_validation(self) -> None:
        plan = valid_plan()

        string_schema = valid_run(plan)
        string_schema["schema_version"] = "6"
        self.assert_run_error_contains(
            plan,
            string_schema,
            "run.schema_version: must equal 2, 3, 4, 5, 6, 7, or 8",
        )

        unsupported_schema = valid_run(plan)
        unsupported_schema["schema_version"] = 9
        del unsupported_schema["landing"]
        del unsupported_schema["post_merge_cleanup"]
        self.assert_run_error_contains(
            plan,
            unsupported_schema,
            "run.schema_version: must equal 2, 3, 4, 5, 6, 7, or 8",
        )

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

    def test_app_task_accepts_authorized_bounded_nested_subagents(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        digest = plan_digest(plan)
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
        self.assertEqual(validate_run(plan, run), [])

        del run["workers"][0]["nested_subagent_policy"]
        self.assert_run_error_contains(
            plan,
            run,
            "is required for app_task workers when runtime nested_subagents is recorded",
        )
        run["workers"][0]["nested_subagent_policy"] = {
            "enabled": True,
            "max_children": 3,
            "allowed_roles": ["explorer", "reviewer", "tester"],
            "write_policy": "read_only",
            "completion_channel": "agent_result",
        }

        run["authorizations"]["spawn_subagents"] = {
            "authorized": False,
            "source": None,
        }
        self.assert_run_error_contains(
            plan,
            run,
            "requires matching spawn_subagents authorization",
        )


if __name__ == "__main__":
    unittest.main()

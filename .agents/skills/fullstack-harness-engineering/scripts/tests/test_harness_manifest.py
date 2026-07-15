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


def valid_run(plan: dict[str, object]) -> dict[str, object]:
    digest = plan_digest(plan)
    mission_ids = [item["id"] for item in plan["missions"]]
    task_ids = [
        item["id"]
        for current_mission in plan["missions"]
        for item in current_mission["tasks"]
    ]
    return {
        "schema_version": 3,
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
            "platform_lifecycle": {
                "owner": "parent",
                "automatic_retention_cleanup_possible": False,
                "durable_branch_required_before_unique_work": True,
            },
        },
        "observed": {
            "captured_at": None,
            "git": {
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
            "branch": "main",
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

    def test_run_schema_v2_remains_compatible(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["schema_version"] = 2
        del run["landing"]
        for action in ("configure_repository", "manage_pr_review", "merge_pr"):
            del run["authorizations"][action]
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

        run["landing"]["review_head_sha"] = SHA_B
        self.assert_run_error_contains(plan, run, "PASS review must bind to a created PR's current head")

        run["landing"]["review_head_sha"] = SHA_A
        run["integration"]["integration_head_sha"] = SHA_B
        self.assert_run_error_contains(
            plan,
            run,
            "ready or merged status requires the current PR head to match integration_head_sha",
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

#!/usr/bin/env python3
"""Focused tests for the canonical harness manifest contract."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


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
    validate_ui_evidence_files,
    validate_scope_claim,
)
from harness_authorization import authorization_covers  # noqa: E402
from harness_schema import action_target_kind_allowed  # noqa: E402


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
        "required_skills": [],
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
                "location": "docs/product/prd.md",
                "owner": "product",
                "status": "frozen",
                "notes": "product contract",
            },
            {
                "id": "SRC-002",
                "kind": "architecture",
                "location": "docs/product/architecture.md",
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
            "mode": "local_only",
            "remote": "origin",
            "pushed_head_sha": None,
            "continuity": None,
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


def valid_closeout_run(plan: dict[str, object]) -> dict[str, object]:
    run = valid_run(plan)
    run["schema_version"] = 9
    run["landing"]["mode"] = "local_only"
    run["authorizations"]["invoke_external_runtime"] = {
        "authorized": False,
        "source": None,
    }
    run["batch_gate_results"] = [
        {
            "id": gate["id"],
            "status": "planned",
            "head_sha": None,
            "evidence": [],
        }
        for gate in plan["batch_verifiers"]
    ]
    run["final_gate_results"] = [
        {
            "id": gate["id"],
            "status": "planned",
            "head_sha": None,
            "evidence": [],
        }
        for gate in plan["final_gates"]
    ]
    run["ui_evidence"] = []
    return run






def mark_complete(plan: dict[str, object], run: dict[str, object]) -> None:
    run["status"] = "complete"
    run["intent"] = "plan-then-execute"
    run["plan_readiness"] = "ready"
    for state in run["mission_states"].values():
        state["phase"] = "integrated"
        state["integration_gate"] = "PASS"
        state["integrated_sha"] = run["integration"]["integration_head_sha"]
    superseded = {
        item["id"]
        for current_mission in plan["missions"]
        for item in current_mission["tasks"]
        if item["replaced_by"]
    }
    for task_id, state in run["task_states"].items():
        state["phase"] = "superseded" if task_id in superseded else "mission_recorded"
        state["verifier_status"] = "PASS"
    for results in (
        run.get("batch_gate_results", []),
        run.get("final_gate_results", []),
    ):
        for result in results:
            result["status"] = "PASS"
            result["head_sha"] = run["integration"]["integration_head_sha"]
            result["evidence"] = ["gate passed"]
    # A complete run keeps its branch at the head it verified, so the user can
    # read it and land it.
    run["landing"]["continuity"] = {
        "status": "preserved",
        "branch_ref": "refs/heads/" + run["integration"]["branch"].removeprefix("refs/heads/"),
        "head_sha": run["integration"]["integration_head_sha"],
        "reason": None,
    }


def retained_gate_execution(
    plan: dict[str, object],
    run: dict[str, object],
    declaration: dict[str, object],
    *,
    layer: str,
    execution_id: str,
) -> dict[str, object]:
    changed_files: list[str] = []
    context = {
        "run_id": run["run_id"],
        "plan_revision": run["plan"]["revision"],
        "plan_digest_sha256": run["plan"]["digest_sha256"],
        "graph_revision": run["graph_state"]["graph_revision"],
        "batch_base_sha": run["integration"]["batch_base_sha"],
        "head_sha": run["integration"]["integration_head_sha"],
        "changed_files": changed_files,
        "trust_domain": "parent_local",
        "checkout_role": "integration",
        "checkout_dirty": False,
        "cache_safe": False,
        "layer": layer,
        "mission_id": None,
        "task_id": None,
        "attempt_id": None,
        "lease_id": None,
    }
    normalized_verifier = {
        "id": declaration["id"],
        "cwd": declaration["cwd"],
        "argv": declaration["argv"],
        "pass_signal": declaration["pass_signal"],
        "cache": {"mode": "disabled", "environment_keys": []},
    }
    key_document = {
        "protocol": "harness-verifier-execution-v1",
        "verifier_id": declaration["id"],
        "layer": layer,
        "mission_id": None,
        "task_id": None,
        "attempt_id": None,
        "lease_id": None,
        "run_id": context["run_id"],
        "plan_revision": context["plan_revision"],
        "plan_digest_sha256": context["plan_digest_sha256"],
        "graph_revision": context["graph_revision"],
        "batch_base_sha": context["batch_base_sha"],
        "head_sha": context["head_sha"],
        "changed_files_digest": hashlib.sha256(b"[]").hexdigest(),
        "trust_domain": context["trust_domain"],
        "checkout_role": context["checkout_role"],
        "checkout_dirty": context["checkout_dirty"],
        "cache_safe": context["cache_safe"],
        "cwd": declaration["cwd"],
        "argv": declaration["argv"],
        "pass_signal": declaration["pass_signal"],
        "cache_mode": "disabled",
        "environment_keys": [],
        "platform": {"system": "test", "machine": "test"},
        "executable_identity": {
            "path": "C:/python",
            "size": 1,
            "mtime_ns": 1,
            "device": 1,
            "inode": 1,
        },
        "environment_digests": {},
    }
    execution_key = hashlib.sha256(
        json.dumps(
            key_document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    empty_digest = hashlib.sha256(b"").hexdigest()
    return {
        "execution_id": execution_id,
        "verifier_id": declaration["id"],
        "layer": layer,
        "mission_id": None,
        "task_id": None,
        "attempt_id": None,
        "lease_id": None,
        "protocol": "harness-verifier-execution-v1",
        "execution_key": execution_key,
        "evidence_key": execution_key,
        "key_document": key_document,
        "verifier": normalized_verifier,
        "context": context,
        "status": "PASS",
        "exit_code": 0,
        "cache_status": "bypassed",
        "cache_reason": "cache_disabled",
        "duration_ms": 1,
        "metrics": {"executed": 1, "reused": 0},
        "stdout_sha256": empty_digest,
        "stderr_sha256": empty_digest,
        "evidence_paths": [],
    }








def authorize_execution(
    run: dict[str, object],
    mission_ids: list[str],
    *,
    status: str = "running",
    plan: dict[str, object] | None = None,
    digest: str | None = None,
) -> None:
    """Authorize execution for exactly `mission_ids`.

    Pass `plan`/`digest` to also bind the scope to that plan revision and
    digest, which the pinned-scope tests rely on.
    """
    scope: dict[str, object] = {"run_id": run["run_id"]}
    if plan is not None:
        scope["plan_revision"] = plan["revision"]
    if digest is not None:
        scope["plan_digest_sha256"] = digest
    scope["mission_ids"] = mission_ids
    scope["expires_when"] = "run_complete"
    run.update(
        {
            "status": status,
            "intent": "plan-then-execute",
            "plan_readiness": "ready",
            "execution_authorized": True,
            "execution_authorization_source": "user requested execution",
            "execution_authorization_scope": scope,
        }
    )
















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
        plan["missions"][0]["tasks"][0]["acceptance_matrix"] = ["M1/T01 passes"]
        self.assertEqual(validate_plan(plan), [])

    def test_required_skills_accepts_empty_and_populated_lists(self) -> None:
        plan = valid_plan()
        self.assertEqual(validate_plan(plan), [])
        plan["missions"][0]["required_skills"] = ["frontend-design", "feature-dev"]
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


    def test_integration_batch_and_final_verifiers_cannot_use_session_cache(self) -> None:
        cache = {"mode": "session_exact", "environment_keys": []}

        batch_plan = valid_plan()
        batch_plan["batch_verifiers"][0]["cache"] = cache
        self.assert_error_contains(
            batch_plan, "session_exact is not allowed for this verifier"
        )

        final_plan = valid_plan()
        final_plan["final_gates"][0]["cache"] = cache
        self.assert_error_contains(
            final_plan, "session_exact is not allowed for this verifier"
        )

        integration_plan = valid_plan()
        integration_plan["missions"][0]["integration_verifiers"][0]["cache"] = cache
        self.assert_error_contains(
            integration_plan, "session_exact is not allowed for this verifier"
        )

        worker_plan = valid_plan()
        worker_plan["missions"][0]["worker_verifiers"][0]["cache"] = cache
        self.assertEqual(validate_plan(worker_plan), [])











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

    def integration_pull_request_v10(
        self,
    ) -> tuple[dict[str, object], dict[str, object], str]:
        root = SCRIPTS_DIR.parent
        plan = load_plan(root / "assets/templates/HARNESS_PLAN.template.md")
        run = load_run(root / "assets/templates/MISSION_RUNBOOK.template.md")
        # The default templates are main-only: one production target, no
        # persistent integration branch. This fixture is the other supported
        # shape — a repository that defines its own integration branch and keeps
        # a preview environment watching it — so it declares that target itself.
        development = copy.deepcopy(
            next(
                target
                for target in plan["release"]["targets"]
                if target["stage"] == "production"
            )
        )
        development.update(
            {
                "id": "web-development",
                "stage": "development",
                "source": "integration_head",
                "channel": "workers-development",
                "data_mode": "isolated_non_production",
                "trigger": "merge",
                "prerequisites": ["current_head_ci"],
            }
        )
        development["commands"]["publish"] = None
        # Verifier and command IDs are globally unique across the PLAN.
        development["commands"]["build"]["id"] = "build-web-development"
        development["smoke_verifiers"][0]["id"] = "smoke-web-development"
        plan["release"]["targets"].insert(0, development)
        run["targets"][development["id"]] = copy.deepcopy(
            run["targets"]["web-production"]
        )
        run["integration"]["branch"] = "refs/heads/development"
        run["integration"]["retention"] = "persistent"
        run["plan"]["digest_sha256"] = plan_digest(plan)

        pr_head = SHA_A
        pr_url = "https://github.com/example/repo/pull/7"
        future_pr = (
            "future-pr:example/repo:"
            "base=refs/heads/development:head=refs/heads/codex/feature"
        )
        run["landing"].update(
            {
                "mode": "integration_pull_request",
                "head_branch": "refs/heads/codex/feature",
                "base_branch": "refs/heads/development",
                "base_branch_protection": {
                    "branch_ref": "refs/heads/development",
                    "status": "unprotected",
                    "source": "repository: AGENTS.md integration branch policy",
                },
                "pushed_head_sha": pr_head,
                "pr_number": 7,
                "pr_url": pr_url,
                "pr_state": "open",
                "pr_head_sha": pr_head,
                "checks_status": "PASS",
                "checks_head_sha": pr_head,
                "review_status": "PASS",
                "review_head_sha": pr_head,
                "blocking_findings": 0,
                "unresolved_threads": 0,
                "merge_status": "ready",
                "auto_merge_requested": True,
                "auto_merge_head_sha": pr_head,
                "continuity": {
                    "status": "planned",
                    "branch_ref": "refs/heads/development",
                    "head_sha": None,
                    "reason": "retain the integration branch for later promotion",
                },
            }
        )
        run["authorizations"]["merge_pr"] = {
            "authorized": True,
            "source": "user: merge the exact integration pull request",
            "scope": {
                "run_id": run["run_id"],
                "plan_revision": run["plan"]["revision"],
                "plan_digest_sha256": run["plan"]["digest_sha256"],
                "mission_ids": list(run["mission_states"]),
                "targets": [future_pr, f"pr:{pr_url}"],
            },
            "expires_when": "run_complete",
            "authorized_head_sha": pr_head,
        }
        return plan, run, development["id"]

    def authorize_merge_triggered_development_release(
        self,
        run: dict[str, object],
        target_id: str,
    ) -> None:
        release_target = f"release:{target_id}"
        run["authorizations"]["merge_pr"]["scope"]["targets"].append(release_target)
        deploy_source = "user: deploy the development release from this exact merge"
        run["authorizations"]["merge_pr"]["target_sources"] = {
            release_target: deploy_source,
        }
        run["authorizations"]["deploy"] = {
            "authorized": True,
            "source": "user: run the authorized development deploy",
            "target_sources": {
                release_target: deploy_source,
            },
            "scope": {
                "run_id": run["run_id"],
                "plan_revision": run["plan"]["revision"],
                "plan_digest_sha256": run["plan"]["digest_sha256"],
                "mission_ids": list(run["mission_states"]),
                "targets": [release_target],
            },
            "expires_when": "run_complete",
            "authorized_head_sha": run["landing"]["pr_head_sha"],
        }

    def merged_pull_request_v10(
        self,
        mode: str,
    ) -> tuple[dict[str, object], dict[str, object]]:
        plan, run, development_target_id = self.integration_pull_request_v10()
        pr_head = run["landing"]["pr_head_sha"]
        pr_url = run["landing"]["pr_url"]
        run["landing"]["auto_merge_requested"] = False
        run["landing"]["auto_merge_head_sha"] = None

        if mode == "integration_pull_request":
            self.authorize_merge_triggered_development_release(
                run, development_target_id
            )
            merged_sha = SHA_B
            run["integration"]["integration_head_sha"] = merged_sha
            run["landing"]["continuity"].update(
                {
                    "status": "preserved",
                    "head_sha": merged_sha,
                }
            )
        else:
            production = next(
                target
                for target in plan["release"]["targets"]
                if target["stage"] == "production"
            )
            release_target = f"release:{production['id']}"
            future_pr = (
                "future-pr:example/repo:"
                "base=refs/heads/production:head=refs/heads/development"
            )
            run["landing"].update(
                {
                    "mode": "pull_request",
                    "head_branch": "refs/heads/development",
                    "base_branch": "refs/heads/production",
                    "base_branch_protection": {
                        "branch_ref": "refs/heads/production",
                        "status": "protected",
                        "source": "repository: AGENTS.md protected branch policy",
                    },
                    "continuity": {
                        "status": "not_required",
                        "branch_ref": None,
                        "head_sha": None,
                        "reason": None,
                    },
                }
            )
            run["integration"]["integration_head_sha"] = pr_head
            run["authorizations"]["merge_pr"] = {
                "authorized": True,
                "source": "user: merge the exact production pull request",
                "scope": {
                    "run_id": run["run_id"],
                    "plan_revision": run["plan"]["revision"],
                    "plan_digest_sha256": run["plan"]["digest_sha256"],
                    "mission_ids": list(run["mission_states"]),
                    "targets": [
                        future_pr,
                        f"pr:{pr_url}",
                        release_target,
                    ],
                },
                "target_sources": {
                    future_pr: "user: open this exact production promotion",
                    f"pr:{pr_url}": "user: merge this exact production PR",
                    release_target: "user: publish from this production merge",
                },
                "expires_when": "run_complete",
                "authorized_head_sha": pr_head,
            }
            run["authorizations"]["deploy"] = {
                "authorized": True,
                "source": "user: deploy the exact production release",
                "scope": {
                    "run_id": run["run_id"],
                    "plan_revision": run["plan"]["revision"],
                    "plan_digest_sha256": run["plan"]["digest_sha256"],
                    "mission_ids": list(run["mission_states"]),
                    "targets": [release_target],
                },
                "target_sources": {
                    release_target: "user: deploy this production target",
                },
                "expires_when": "run_complete",
                "authorized_head_sha": pr_head,
            }
            merged_sha = SHA_B

        run["landing"].update(
            {
                "pr_state": "merged",
                "merge_status": "merged",
                "merged_sha": merged_sha,
            }
        )
        return plan, run

    def test_matching_plan_run_digest(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        self.assertEqual(validate_run(plan, run), [])

        run["plan"]["digest_sha256"] = "0" * 64
        self.assert_run_error_contains(plan, run, "does not match semantic PLAN digest")


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

















    def _authorize_and_pass_production(self, plan, run) -> None:
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
        authorize_deploy(run, "development", "production")
        merged_landing(run)
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
        for task in plan["missions"][1]["tasks"]:
            run["task_states"][task["id"]]["phase"] = "superseded"

        self.assertEqual(validate_run(plan, run), [])


    def test_schema_v9_rejects_unhashable_gate_ids_without_crashing(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        run["batch_gate_results"][0]["id"] = []

        errors = validate_run(plan, run)

        self.assertTrue(any("must be a non-empty string" in error for error in errors))
        self.assertTrue(any("IDs must exactly match" in error for error in errors))

        run = valid_closeout_run(plan)
        run["batch_gate_results"][0]["status"] = []
        errors = validate_run(plan, run)
        self.assertTrue(any(".status: has an unsupported gate value" in error for error in errors))

    def test_schema_v9_rejects_malformed_plan_gate_lists_without_crashing(self) -> None:
        for field in ("batch_verifiers", "final_gates"):
            with self.subTest(field=field):
                plan = valid_plan()
                run = valid_closeout_run(plan)
                plan[field] = None

                self.assertTrue(validate_plan(plan))
                self.assertTrue(validate_run(plan, run))

    def test_schema_v9_rejects_unhashable_ui_evidence_scalars_without_crashing(self) -> None:
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
                malformed_run = valid_closeout_run(malformed_plan)
                malformed_run["ui_evidence"] = [copy.deepcopy(evidence)]
                self.assertTrue(validate_plan(malformed_plan))
                self.assertTrue(validate_run(malformed_plan, malformed_run))

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
            evidence = root / "docs" / "goal" / "evidence" / "dashboard-desktop-loaded.png"
            self.assertTrue(
                any("does not exist" in error for error in validate_ui_evidence_files(run, root))
            )
            evidence.parent.mkdir(parents=True)
            evidence.write_bytes(contents)
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
                    "cannot be decoded" in error
                    for error in validate_ui_evidence_files(run, root)
                )
            )




    def test_run_schema_v5_remains_compatible(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["schema_version"] = 5
        del run["runtime_capabilities"]["runtime_adapter"]
        self.assertEqual(validate_run(plan, run), [])


    def test_schema_v6_routes_claude_dynamic_workflow(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["schema_version"] = 6
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

    def test_worker_runtime_binding_source_must_equal_host(self) -> None:
        # A node's required provider must match whatever host actually runs
        # it: there is no bridged/guarded external source anymore, so
        # runtime_binding.source is exactly "host" or rejected.
        plan = valid_plan()
        run = valid_run(plan)
        digest = plan_digest(plan)
        worker = {
            "worker_id": "W-M1",
            "mission_id": "M1",
            "lease_id": "LEASE-M1",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "batch_base_sha": SHA_A,
            "worker_runtime": "parent",
            "workspace_mode": "shared_checkout",
            "completion_channel": "agent_result",
            "runtime_binding": {
                "provider": "generic",
                "driver": "sequential_parent",
                "source": "host",
                "model": None,
                "reasoning_effort": None,
                "option_source": "provider_default",
            },
            "task_thread_id": None,
            "worktree_path": None,
            "branch_ref": None,
            "report_path": None,
            "phase": "leased",
            "worker_head_sha": None,
        }
        run["workers"].append(worker)
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

    def test_non_graph_schema_v9_rejects_workflow_runs(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        run["workflow_runs"] = []
        self.assert_run_error_contains(plan, run, "unknown keys: workflow_runs")

    def test_non_graph_schema_v8_is_rejected(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        run["schema_version"] = 8
        run["workflow_runs"] = []
        errors = validate_run(plan, run)
        self.assertTrue(any("schema v8 requires a schema v4 graph PLAN" in error for error in errors))
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

        run["workers"][0]["nested_subagent_policy"]["allowed_roles"] = [
            "explorer",
            "tester",
        ]
        self.assertEqual(
            [],
            validate_run(plan, run),
            "legacy RUN v6 keeps its previously valid enabled-role policy",
        )
        for schema_version in range(2, 10):
            legacy_run = copy.deepcopy(run)
            legacy_run["schema_version"] = schema_version
            self.assertFalse(
                any(
                    "must include reviewer when enabled" in error
                    for error in validate_run(plan, legacy_run)
                ),
                f"RUN v{schema_version} must retain its enabled-role policy",
            )
        run["workers"][0]["nested_subagent_policy"]["allowed_roles"] = [
            "explorer",
            "reviewer",
            "tester",
        ]

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

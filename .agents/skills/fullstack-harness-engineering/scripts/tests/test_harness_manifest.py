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
    DEPLOYMENT_PROVIDERS,
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
from harness_authorization import (  # noqa: E402
    execution_intent_target_in_scope,
    validate_target_sources,
)
from harness_schema import ACTION_TARGET_CONTRACT, action_target_kind_allowed  # noqa: E402


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


def generic_release(provider: str) -> dict[str, object]:
    return {
        "provider": provider,
        "targets": [
            {
                "id": "primary",
                "data_mode": "isolated_non_production",
                "prerequisites": ["ci_pass"],
                "migration_command": None,
                "deploy_command": verifier("deploy-primary", "npm", "run", "deploy"),
                "smoke_verifiers": [verifier("smoke-primary", "tool", "smoke-primary")],
            },
            {
                "id": "secondary",
                "data_mode": "production",
                "prerequisites": ["ci_pass"],
                "migration_command": None,
                "deploy_command": verifier("deploy-secondary", "npm", "run", "deploy"),
                "smoke_verifiers": [verifier("smoke-secondary", "tool", "smoke-secondary")],
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


def generic_release_run(plan: dict[str, object], provider: str) -> dict[str, object]:
    run = valid_run(plan)
    run["schema_version"] = 7
    target = {
        "status": "not_started",
        "source_sha": None,
        "worker_name": None,
        "url": None,
        "version_id": None,
        "migration_status": "not_started",
        "verification_status": "not_started",
        "rollback_version": None,
        "evidence": [],
    }
    run["deployments"] = {
        "provider": provider,
        "development": copy.deepcopy(target),
        "production": copy.deepcopy(target),
    }
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
    if run["post_merge_cleanup"]["status"] == "not_started":
        run["post_merge_cleanup"]["status"] = "deferred"
        run["post_merge_cleanup"]["deferred_reason"] = "fixture cleanup is deferred"


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


def mark_observed_merge_complete_v10(
    plan: dict[str, object], run: dict[str, object]
) -> None:
    run["status"] = "complete"
    run["intent"] = "plan-then-execute"
    run["plan_readiness"] = "ready"
    run["integration"]["batch_base_sha"] = SHA_A
    for source in plan["sources"]:
        source["status"] = "frozen"
    for state in run["mission_states"].values():
        state.update(
            {
                "phase": "superseded",
                "integration_gate": "planned",
                "integrated_sha": None,
                "blockers": [],
            }
        )
    for state in run["task_states"].values():
        state.update(
            {
                "phase": "superseded",
                "verifier_status": "PASS",
                "blockers": [],
            }
        )
    node_kinds = {
        node["id"]: node["kind"]
        for node in plan["graph"]["nodes"]
    }
    for node_id, state in run["graph_state"]["node_states"].items():
        state.update(
            {
                "phase": (
                    "superseded" if node_kinds[node_id] == "mission" else "skipped"
                ),
                "blockers": [],
            }
        )
    for state in run["graph_state"]["edge_states"].values():
        state.update(
            {
                "status": "skipped",
                "traversals": 0,
                "source_attempt_id": None,
            }
        )

    declarations = [
        *((item, "batch") for item in plan["batch_verifiers"]),
        *((item, "final") for item in plan["final_gates"]),
    ]
    run["verifier_executions"] = [
        retained_gate_execution(
            plan,
            run,
            declaration,
            layer=layer,
            execution_id=f"VX-CLOSEOUT-{index}",
        )
        for index, (declaration, layer) in enumerate(declarations, start=1)
    ]
    executions = {
        execution["verifier_id"]: execution
        for execution in run["verifier_executions"]
    }
    for results in (run["batch_gate_results"], run["final_gate_results"]):
        for result in results:
            execution = executions[result["id"]]
            result.update(
                {
                    "status": "PASS",
                    "head_sha": run["integration"]["integration_head_sha"],
                    "evidence": [execution["execution_key"]],
                }
            )

    run["ui_evidence"] = [
        {
            "surface_id": surface["id"],
            "route": surface["route"],
            "breakpoint": breakpoint,
            "state": state,
            "artifact_path": (
                f"docs/goal/evidence/{surface['id']}-{breakpoint}-{state}.png"
            ),
            "artifact_sha256": "c" * 64,
            "head_sha": run["integration"]["integration_head_sha"],
            "status": "PASS",
        }
        for surface in plan["ui_surfaces"]
        if surface["evidence_gate"] == "required"
        for breakpoint in surface["breakpoints"]
        for state in surface["states"]
    ]
    run["post_merge_cleanup"].update(
        {
            "status": "deferred",
            "deferred_reason": "human-managed cleanup",
            "evidence": [],
        }
    )


def authorize_merge(run: dict[str, object], pr_url: str) -> None:
    run["authorizations"]["merge_pr"] = {
        "authorized": True,
        "source": "user: merge the reviewed pull request",
        "scope": {
            "run_id": run["run_id"],
            "mission_ids": list(run["mission_states"]),
            "targets": [f"pr:{pr_url}"],
        },
        "expires_when": "run_complete",
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


def open_pr_landing(run: dict[str, object], *, pr_number: int = 7) -> None:
    """Record an open PR whose checks passed at SHA_A."""
    run["landing"].update(
        {
            "pushed_head_sha": SHA_A,
            "pr_number": pr_number,
            "pr_url": f"https://github.com/example/repo/pull/{pr_number}",
            "pr_state": "open",
            "pr_head_sha": SHA_A,
            "checks_status": "PASS",
            "checks_head_sha": SHA_A,
        }
    )


def authorize_deploy(run: dict[str, object], *environments: str) -> None:
    """Grant `deploy` for exactly the named release environments."""
    listed = " and ".join(environments)
    run["authorizations"]["deploy"] = {
        "authorized": True,
        "source": f"user: deploy {listed} for this run",
        "scope": {
            "run_id": "RUN-TEST",
            "mission_ids": ["M1", "M2"],
            "targets": [f"environment:{name}" for name in environments],
        },
        "expires_when": "run_complete",
    }


def ready_landing(
    run: dict[str, object], *, pr_number: int = 7, auto_merge: bool = False
) -> None:
    """Record an open PR that is merge-ready: checks and review PASS at SHA_A."""
    run["landing"].update(
        {
            "pushed_head_sha": SHA_A,
            "pr_number": pr_number,
            "pr_url": f"https://github.com/example/repo/pull/{pr_number}",
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
    if auto_merge:
        run["landing"].update(
            {"auto_merge_requested": True, "auto_merge_head_sha": SHA_A}
        )


def merged_landing(run: dict[str, object], *, pr_number: int = 7) -> None:
    """Record a merged PR whose checks and review both passed at SHA_A."""
    run["landing"].update(
        {
            "pushed_head_sha": SHA_A,
            "pr_number": pr_number,
            "pr_url": f"https://github.com/example/repo/pull/{pr_number}",
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


def integrated_merged_run(pr_number: int = 7) -> tuple[dict[str, object], dict[str, object]]:
    """PLAN/RUN whose missions are integrated at SHA_A behind a merged PR."""
    plan = valid_plan()
    run = valid_run(plan)
    run["integration"]["integration_head_sha"] = SHA_A
    merged_landing(run, pr_number=pr_number)
    for state in run["mission_states"].values():
        state.update(
            {
                "phase": "integrated",
                "integration_gate": "PASS",
                "integrated_sha": SHA_A,
            }
        )
    return plan, run


def authorize_cleanup(run: dict[str, object], action: str, target: str) -> None:
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


def ready_cleanup_run(pr_number: int = 7) -> tuple[dict[str, object], dict[str, object]]:
    """Merged-PR run parked on its feature branch with cleanup ready to run."""
    plan, run = integrated_merged_run(pr_number)
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
    authorize_cleanup(run, "delete_branches", "branch:refs/heads/codex/test")
    run["authorizations"]["delete_branches"]["source"] = (
        "user: remove the merged local feature branch"
    )
    authorize_merge(run, f"https://github.com/example/repo/pull/{pr_number}")
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
    return plan, run


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

    def test_release_verifiers_cannot_use_session_cache(self) -> None:
        plan = valid_release_plan()
        plan["release"]["targets"][0]["deploy_command"]["cache"] = {
            "mode": "session_exact",
            "environment_keys": [],
        }
        self.assert_error_contains(
            plan,
            "session_exact is not allowed for this verifier",
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

    def test_schema_v3_cloudflare_release_accepts_integration_head_development_source(
        self,
    ) -> None:
        plan = valid_release_plan()
        plan["release"]["targets"][0]["source"] = "integration_head"
        self.assertEqual(validate_plan(plan), [])

    def test_schema_v3_cloudflare_release_rejects_unknown_development_source(self) -> None:
        plan = valid_release_plan()
        plan["release"]["targets"][0]["source"] = "something_else"
        self.assert_error_contains(plan, "must equal pr_head or integration_head")

    def test_schema_v3_accepts_non_cloudflare_release_providers(self) -> None:
        for provider in sorted(DEPLOYMENT_PROVIDERS - {"cloudflare"}):
            plan = valid_plan()
            plan["schema_version"] = 3
            plan["release"] = generic_release(provider)
            self.assertEqual(validate_plan(plan), [], f"provider={provider}")

    def test_schema_v3_release_rejects_unknown_provider(self) -> None:
        plan = valid_plan()
        plan["schema_version"] = 3
        plan["release"] = generic_release("gcp")
        self.assert_error_contains(plan, "must be one of")

    def test_schema_v3_generic_release_rejects_cloudflare_only_fields(self) -> None:
        plan = valid_plan()
        plan["schema_version"] = 3
        plan["release"] = generic_release("vercel")
        plan["release"]["targets"][0]["worker_name"] = "should-not-be-allowed"
        self.assert_error_contains(plan, "unknown keys: worker_name")

    def test_schema_v3_generic_release_rejects_missing_generic_fields(self) -> None:
        plan = valid_plan()
        plan["schema_version"] = 3
        plan["release"] = generic_release("vercel")
        del plan["release"]["targets"][0]["deploy_command"]
        self.assert_error_contains(plan, "missing keys: deploy_command")

    def test_schema_v3_generic_release_requires_isolated_and_production_data_modes(
        self,
    ) -> None:
        single_target = valid_plan()
        single_target["schema_version"] = 3
        release = generic_release("vercel")
        release["targets"] = release["targets"][:1]
        single_target["release"] = release
        self.assert_error_contains(
            single_target,
            "must include at least one isolated_non_production and one production data_mode",
        )

        both_isolated = valid_plan()
        both_isolated["schema_version"] = 3
        release = generic_release("vercel")
        release["targets"][1]["data_mode"] = "isolated_non_production"
        both_isolated["release"] = release
        self.assert_error_contains(
            both_isolated,
            "must include at least one isolated_non_production and one production data_mode",
        )

    def test_schema_v3_generic_release_rejects_invalid_data_mode(self) -> None:
        plan = valid_plan()
        plan["schema_version"] = 3
        plan["release"] = generic_release("vercel")
        plan["release"]["targets"][0]["data_mode"] = "staging"
        self.assert_error_contains(
            plan, "must be isolated_non_production or production"
        )

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

    def test_schema_v7_promotes_exact_cloudflare_shas(self) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self.assertEqual(validate_run(plan, run), [])

        authorize_deploy(run, "development", "production")
        open_pr_landing(run)
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
                "authorized_head_sha": SHA_A,
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

    def test_run_template_defaults_to_ephemeral_per_run_branch(self) -> None:
        root = SCRIPTS_DIR.parent
        plan = load_plan(root / "assets/templates/HARNESS_PLAN.template.md")
        run = load_run(root / "assets/templates/MISSION_RUNBOOK.template.md")

        self.assertEqual("refs/heads/codex/<short-name>", run["integration"]["branch"])
        self.assertEqual("ephemeral", run["integration"]["retention"])
        self.assertEqual([], validate_run(plan, run))

        run["integration"]["branch"] = "refs/heads/development"
        run["integration"]["retention"] = "persistent"
        run["landing"]["head_branch"] = "refs/heads/development"
        run["landing"]["continuity"]["branch_ref"] = "refs/heads/development"
        self.assertEqual([], validate_run(plan, run))

    def test_schema_v7_integration_head_development_binds_to_integration_branch(
        self,
    ) -> None:
        plan = valid_release_plan()
        plan["release"]["targets"][0]["source"] = "integration_head"
        run = valid_release_run(plan)
        run["integration"]["integration_head_sha"] = SHA_A
        run["integration"]["retention"] = "persistent"

        authorize_deploy(run, "development")
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

        run["deployments"]["development"]["source_sha"] = SHA_B
        self.assert_run_error_contains(
            plan,
            run,
            "PASS must bind to the current integration branch head (run.integration.integration_head_sha)",
        )

    def test_schema_v7_integration_head_development_requires_persistent_retention(
        self,
    ) -> None:
        plan = valid_release_plan()
        plan["release"]["targets"][0]["source"] = "integration_head"
        run = valid_release_run(plan)
        run["integration"]["integration_head_sha"] = SHA_A
        run["integration"]["retention"] = "persistent"
        self.assertEqual(validate_run(plan, run), [])

        run["integration"]["retention"] = "ephemeral"
        self.assert_run_error_contains(
            plan,
            run,
            "run.integration.retention: must be persistent when development release source is integration_head",
        )

        run["integration"]["retention"] = None
        self.assert_run_error_contains(
            plan,
            run,
            "run.integration.retention: must be persistent when development release source is integration_head",
        )

    def test_schema_v7_accepts_non_cloudflare_deployment_providers(self) -> None:
        for provider in sorted(DEPLOYMENT_PROVIDERS - {"cloudflare"}):
            plan = valid_plan()
            plan["schema_version"] = 3
            plan["release"] = generic_release(provider)
            run = generic_release_run(plan, provider)
            self.assertEqual(validate_run(plan, run), [], f"provider={provider}")

    def test_schema_v7_deployments_rejects_unknown_provider(self) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        run["deployments"]["provider"] = "gcp"
        self.assert_run_error_contains(plan, run, "must be one of")

    def test_schema_v7_matching_invalid_providers_skip_the_mismatch_error(self) -> None:
        # PLAN release.provider and RUN deployments.provider carry the identical,
        # equally-invalid provider string. validate_run must not early-return on
        # the unrecognized provider (that would hide real per-target problems),
        # but it also must not pile on a spurious "must match PLAN release
        # provider" error when both sides already agree with each other.
        plan = valid_plan()
        plan["schema_version"] = 3
        plan["release"] = generic_release("gcp")
        run = generic_release_run(plan, "gcp")
        expected_provider_error = (
            f"run.deployments.provider: must be one of {sorted(DEPLOYMENT_PROVIDERS)}"
        )
        self.assertEqual(validate_run(plan, run), [expected_provider_error])

    def test_schema_v7_unrecognized_provider_pass_target_excluded_from_lenient_sha_check(
        self,
    ) -> None:
        # The generic (non-cloudflare) PASS-state source_sha requirement is
        # narrowed to providers in DEPLOYMENT_PROVIDERS. An unrecognized
        # provider like "gcp" must not trip that per-target check (it isn't a
        # recognized generic provider), but it must still fail overall via the
        # top-level provider error -- no crash, and no false accept.
        plan = valid_plan()
        plan["schema_version"] = 3
        plan["release"] = generic_release("gcp")
        run = generic_release_run(plan, "gcp")
        run["deployments"]["development"]["status"] = "PASS"
        run["deployments"]["development"]["migration_status"] = "not_required"
        run["deployments"]["development"]["verification_status"] = "PASS"
        run["deployments"]["development"]["evidence"] = ["artifact:development-smoke"]
        # source_sha stays None: a recognized generic provider would fail with
        # "PASS requires a source SHA" here; an unrecognized one must not.

        errors = validate_run(plan, run)

        self.assertFalse(
            any("PASS requires a source SHA" in error for error in errors),
            f"unrecognized provider must not use the generic-provider SHA check: {errors!r}",
        )
        self.assertTrue(
            any("run.deployments.provider: must be one of" in error for error in errors),
            f"unrecognized provider must still be rejected overall: {errors!r}",
        )

    def test_schema_v7_deployments_provider_must_match_plan_release_provider(self) -> None:
        plan = valid_plan()
        plan["schema_version"] = 3
        plan["release"] = generic_release("vercel")
        run = generic_release_run(plan, "aws")
        self.assert_run_error_contains(plan, run, "must match PLAN release provider")

    def test_schema_v7_cloudflare_deployments_still_require_worker_fields(self) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        run["deployments"]["development"].update(
            {
                "status": "PASS",
                "source_sha": SHA_A,
                "migration_status": "not_required",
                "verification_status": "PASS",
                "evidence": ["artifact:development-smoke"],
            }
        )
        self.assert_run_error_contains(
            plan, run, "PASS requires source SHA, worker, URL, and version ID"
        )

    def test_schema_v7_generic_deployments_pass_requires_source_and_evidence(self) -> None:
        plan = valid_plan()
        plan["schema_version"] = 3
        plan["release"] = generic_release("vercel")
        run = generic_release_run(plan, "vercel")
        run["deployments"]["development"]["status"] = "PASS"
        run["deployments"]["development"]["migration_status"] = "not_required"
        run["deployments"]["development"]["verification_status"] = "PASS"
        self.assert_run_error_contains(plan, run, "PASS requires a source SHA")

        authorize_deploy(run, "development")
        open_pr_landing(run)
        run["deployments"]["development"]["source_sha"] = SHA_A
        run["deployments"]["development"]["evidence"] = ["artifact:development-smoke"]
        # Worker/url/version_id stay None: a generic provider's PASS does not require them.
        self.assertEqual(validate_run(plan, run), [])

    def test_integration_push_records_the_pushed_head_without_a_pr(self) -> None:
        """The ordinary development loop pushes its integration branch.

        `local_only` cannot record a pushed head, so before `integration_push`
        existed there was no honest way to record "everyone pushes development,
        nobody opens a PR" — which is the default branch model.
        """
        plan = valid_plan()
        run = valid_run(plan)
        landing = run["landing"]
        landing["mode"] = "integration_push"
        landing["pushed_head_sha"] = run["integration"]["integration_head_sha"]
        run["authorizations"]["push"] = {
            "authorized": True,
            "source": "user asked for the development push",
            "scope": {
                "run_id": run["run_id"],
                "mission_ids": list(run["mission_states"]),
                "targets": [f"branch:{landing['head_branch']}"],
            },
            "expires_when": "run_complete",
        }

        self.assertEqual([], validate_run(plan, run))

        # The pushed head must be the current integration head, or a later local
        # integration leaves the run claiming a head the remote never received.
        landing["pushed_head_sha"] = "9" * 40
        self.assert_run_error_contains(
            plan, run, "must equal integration.integration_head_sha"
        )
        landing["pushed_head_sha"] = run["integration"]["integration_head_sha"]

        # And the push has to actually be authorized.
        run["authorizations"]["push"] = {"authorized": False, "source": None}
        self.assert_run_error_contains(
            plan, run, "requires an authorized push covering the integration branch"
        )
        run["authorizations"]["push"] = {
            "authorized": True,
            "source": "user asked for the development push",
            "scope": {
                "run_id": run["run_id"],
                "mission_ids": list(run["mission_states"]),
                "targets": [f"branch:{landing['head_branch']}"],
            },
            "expires_when": "run_complete",
        }

        # A pushed head is required in this mode: it is what the watching
        # deployment builds from.
        landing["pushed_head_sha"] = None
        self.assert_run_error_contains(
            plan, run, "integration_push mode requires the pushed integration head"
        )

    def test_integration_push_cannot_record_a_pr_or_remote_gates(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        landing = run["landing"]
        landing["mode"] = "integration_push"
        landing["pushed_head_sha"] = run["integration"]["integration_head_sha"]
        landing["pr_state"] = "open"

        self.assert_run_error_contains(
            plan, run, "integration_push mode cannot record a created PR"
        )

    def test_local_only_cannot_authorize_execution_for_a_release_plan(self) -> None:
        # A release PLAN's production target requires a merged PR; local_only can
        # never record one, so the run could never reach complete. Catch it at
        # authorization instead of at closeout, after every mission is built.
        plan = valid_release_plan()
        run = valid_closeout_run(plan)
        run["deployments"] = valid_release_run(plan)["deployments"]
        self.assertEqual(run["landing"]["mode"], "local_only")
        self.assertEqual(validate_run(plan, run), [])

        authorize_execution(run, ["M1", "M2"])
        self.assert_run_error_contains(
            plan, run, "release PLAN in local_only mode"
        )

        run["landing"]["mode"] = "pull_request"
        self.assertEqual(
            [error for error in validate_run(plan, run) if "local_only" in error],
            [],
        )

    def test_release_plan_requires_schema_v7_or_v9_run(self) -> None:
        plan = valid_release_plan()
        run = valid_run(plan)
        self.assert_run_error_contains(
            plan,
            run,
            "must equal 7 or 9 when a schema v3 PLAN declares release",
        )

        run["schema_version"] = 7
        self.assert_run_error_contains(plan, run, "missing keys: deployments")

        run = valid_closeout_run(plan)
        run["deployments"] = valid_release_run(plan)["deployments"]
        self.assertEqual(validate_run(plan, run), [])

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

    def test_schema_v7_production_past_not_started_requires_authorized_head_sha(
        self,
    ) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self._authorize_and_pass_production(plan, run)
        self.assert_run_error_contains(
            plan,
            run,
            "production deployment past not_started requires authorized_head_sha",
        )

    def test_schema_v7_production_pass_with_valid_authorized_head_sha_accepted(
        self,
    ) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self._authorize_and_pass_production(plan, run)
        run["deployments"]["production"]["authorized_head_sha"] = SHA_A
        self.assertEqual(validate_run(plan, run), [])

    def test_schema_v7_production_malformed_authorized_head_sha_rejected(self) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self._authorize_and_pass_production(plan, run)
        run["deployments"]["production"]["authorized_head_sha"] = "not-a-sha"
        self.assert_run_error_contains(
            plan,
            run,
            "run.deployments.production.authorized_head_sha: must be null or a full lowercase Git SHA",
        )

    def test_schema_v7_development_authorized_head_sha_is_always_optional(self) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self.assertEqual(validate_run(plan, run), [])

        run["deployments"]["development"]["authorized_head_sha"] = SHA_A
        self.assertEqual(validate_run(plan, run), [])

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
                "authorized_head_sha": None,
            }
        )
        authorize_deploy(run, "development")
        open_pr_landing(run)
        self.assertFalse(
            any(
                "authorized_head_sha" in error
                for error in validate_run(plan, run)
            )
        )

    def test_schema_v7_production_migration_past_not_started_requires_classification(
        self,
    ) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self._authorize_and_pass_production(plan, run)
        run["deployments"]["production"]["authorized_head_sha"] = SHA_A
        run["deployments"]["production"]["migration_status"] = "PASS"
        self.assert_run_error_contains(
            plan,
            run,
            "production migration past not_started/not_required requires migration_classification",
        )

    def test_schema_v7_production_additive_migration_without_confirmed_sha_accepted(
        self,
    ) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self._authorize_and_pass_production(plan, run)
        run["deployments"]["production"]["authorized_head_sha"] = SHA_A
        run["deployments"]["production"]["migration_status"] = "PASS"
        run["deployments"]["production"]["migration_classification"] = "additive"
        self.assertEqual(validate_run(plan, run), [])

    def test_schema_v7_production_destructive_migration_without_confirmed_sha_rejected(
        self,
    ) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self._authorize_and_pass_production(plan, run)
        run["deployments"]["production"]["authorized_head_sha"] = SHA_A
        run["deployments"]["production"]["migration_status"] = "PASS"
        run["deployments"]["production"]["migration_classification"] = "destructive"
        self.assert_run_error_contains(
            plan,
            run,
            "destructive migration_classification requires destructive_migration_confirmed_sha",
        )

    def test_schema_v7_production_destructive_migration_with_confirmed_sha_accepted(
        self,
    ) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self._authorize_and_pass_production(plan, run)
        run["deployments"]["production"]["authorized_head_sha"] = SHA_A
        run["deployments"]["production"]["migration_status"] = "PASS"
        run["deployments"]["production"]["migration_classification"] = "destructive"
        run["deployments"]["production"]["destructive_migration_confirmed_sha"] = SHA_A
        self.assertEqual(validate_run(plan, run), [])

    def test_schema_v7_production_additive_migration_with_confirmed_sha_rejected(
        self,
    ) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self._authorize_and_pass_production(plan, run)
        run["deployments"]["production"]["authorized_head_sha"] = SHA_A
        run["deployments"]["production"]["migration_status"] = "PASS"
        run["deployments"]["production"]["migration_classification"] = "additive"
        run["deployments"]["production"]["destructive_migration_confirmed_sha"] = SHA_A
        self.assert_run_error_contains(
            plan,
            run,
            "destructive_migration_confirmed_sha requires destructive migration_classification",
        )

    def test_schema_v7_production_malformed_migration_classification_rejected(
        self,
    ) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self._authorize_and_pass_production(plan, run)
        run["deployments"]["production"]["authorized_head_sha"] = SHA_A
        run["deployments"]["production"]["migration_status"] = "PASS"
        run["deployments"]["production"]["migration_classification"] = "maybe"
        self.assert_run_error_contains(
            plan,
            run,
            "run.deployments.production.migration_classification: must be null, additive, or destructive",
        )

    def test_schema_v7_development_migration_classification_never_required(self) -> None:
        plan = valid_release_plan()
        run = valid_release_run(plan)
        self.assertEqual(validate_run(plan, run), [])

        run["deployments"]["development"].update(
            {
                "status": "PASS",
                "source_sha": SHA_A,
                "worker_name": "test-app-development",
                "url": "https://test-app-development.example.workers.dev",
                "version_id": "dev-version-1",
                "migration_status": "PASS",
                "verification_status": "PASS",
                "evidence": ["artifact:development-smoke"],
            }
        )
        authorize_deploy(run, "development")
        open_pr_landing(run)
        self.assertFalse(
            any(
                "migration_classification" in error
                for error in validate_run(plan, run)
            )
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

    def test_complete_pull_request_run_requires_merged_current_head(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        run["landing"]["mode"] = "pull_request"
        mark_complete(plan, run)

        self.assert_run_error_contains(
            plan,
            run,
            "complete pull-request run requires merged current-head landing",
        )

        merged_landing(run, pr_number=21)

        self.assert_run_error_contains(
            plan,
            run,
            "complete pull-request run requires merge authorization for the exact PR",
        )
        authorize_merge(run, "https://github.com/example/repo/pull/22")
        self.assert_run_error_contains(
            plan,
            run,
            "complete pull-request run requires merge authorization for the exact PR",
        )
        authorize_merge(run, "https://github.com/example/repo/pull/21")
        self.assertEqual(validate_run(plan, run), [])

        run["authorizations"]["merge_pr"]["scope"]["targets"] = ["*"]
        self.assert_run_error_contains(
            plan,
            run,
            "complete pull-request run requires merge authorization for the exact PR",
        )

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
        run["status"] = "complete"
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

    def test_completed_run_schema_v2_through_v7_remains_compatible(self) -> None:
        plan = valid_plan()
        for version in range(2, 8):
            with self.subTest(version=version):
                run = valid_run(plan)
                run["landing"]["mode"] = "local_only"
                mark_complete(plan, run)
                run["schema_version"] = version
                if version < 6:
                    del run["runtime_capabilities"]["runtime_adapter"]
                if version < 5:
                    del run["post_merge_cleanup"]
                    del run["observed"]["git"]["parent_worktree_path"]
                if version < 4:
                    del run["landing"]["auto_merge_requested"]
                    del run["landing"]["auto_merge_head_sha"]
                if version < 3:
                    del run["landing"]
                    for action in (
                        "configure_repository",
                        "manage_pr_review",
                        "merge_pr",
                    ):
                        del run["authorizations"][action]
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

    def test_post_merge_cleanup_binds_to_merged_pr_and_exact_branch(self) -> None:
        plan, run = ready_cleanup_run()
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
        mark_complete(plan, run)
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

    def test_post_merge_cleanup_persistent_retention_forbids_deleted_branch(
        self,
    ) -> None:
        plan, run = ready_cleanup_run()
        run["integration"]["retention"] = "persistent"
        self.assertEqual(validate_run(plan, run), [])

        run["post_merge_cleanup"]["local_branch"]["status"] = "deleted"
        self.assert_run_error_contains(
            plan,
            run,
            "run.post_merge_cleanup.local_branch.status: must not be deleted when run.integration.retention is persistent",
        )

        # "not_started" has no fixed branch-status requirement, unlike ready/complete.
        run["post_merge_cleanup"]["status"] = "not_started"
        run["post_merge_cleanup"]["local_branch"]["status"] = "preserved"
        self.assertEqual(validate_run(plan, run), [])

        # "complete" normally requires "deleted", but a persistent-retention branch
        # must reach "complete" via "preserved" instead — "deleted" stays rejected.
        run["post_merge_cleanup"]["status"] = "complete"
        run["post_merge_cleanup"]["evidence"] = ["artifact:cleanup"]
        run["observed"]["git"]["parent_branch"] = "main"
        run["observed"]["git"]["parent_head_sha"] = SHA_B
        self.assertEqual(validate_run(plan, run), [])

        run["post_merge_cleanup"]["local_branch"]["status"] = "deleted"
        self.assert_run_error_contains(
            plan,
            run,
            "run.post_merge_cleanup.local_branch.status: must be preserved when cleanup is complete",
        )
        run["post_merge_cleanup"]["local_branch"]["status"] = "preserved"

        run["integration"]["retention"] = "ephemeral"
        run["post_merge_cleanup"]["local_branch"]["status"] = "deleted"
        self.assertEqual(validate_run(plan, run), [])

        run["integration"]["retention"] = None
        self.assertEqual(validate_run(plan, run), [])

    def test_post_merge_cleanup_requires_clean_observed_worktree(self) -> None:
        plan, run = integrated_merged_run()
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
        authorize_cleanup(run, "delete_branches", "branch:refs/heads/codex/test")
        authorize_cleanup(run, "remove_worktrees", f"worktree:{path}")
        authorize_merge(run, "https://github.com/example/repo/pull/7")
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
        mark_complete(plan, run)
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
        mark_complete(plan, run)
        merged_landing(run, pr_number=21)
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
        authorize_merge(run, "https://github.com/example/repo/pull/21")
        self.assertEqual(validate_run(plan, run), [])

    def test_landing_ready_binds_checks_and_review_to_current_pr_head(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        ready_landing(run)
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
        run["schema_version"] = 6
        future_target = "future-pr:example/repo:base=main:head=codex/test"
        for action in ("create_pr", "manage_pr_review", "merge_pr"):
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

    def test_legacy_run_preserves_historical_exact_action_targets(self) -> None:
        plan = valid_plan()
        run = valid_closeout_run(plan)
        run["authorizations"]["create_local_commits"] = {
            "authorized": True,
            "source": "user: preserve the legacy exact target",
            "scope": {
                "run_id": "RUN-TEST",
                "mission_ids": ["M1", "M2"],
                "targets": ["task:legacy-exact-target"],
            },
            "expires_when": "run_complete",
        }

        self.assertEqual(validate_run(plan, run), [])
        self.assertTrue(
            action_target_kind_allowed(
                "create_local_commits",
                "task:legacy-exact-target",
                10,
            )
        )
        self.assertFalse(
            action_target_kind_allowed(
                "create_local_commits",
                "task:legacy-exact-target",
                10,
                strict=True,
            )
        )

    def test_future_pr_authorization_resolves_to_the_matching_exact_pr(self) -> None:
        plan = valid_plan()
        run = valid_run(plan)
        ready_landing(run, auto_merge=True)
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
        ready_landing(run, auto_merge=True)
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
        mark_complete(plan, run)
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

    def test_integration_pull_request_auto_merge_requires_development_release_grants(
        self,
    ) -> None:
        plan, run, development_target_id = self.integration_pull_request_v10()

        errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "merge authorization must include its auto-deploy release targets"
                in error
                and development_target_id in error
                for error in errors
            ),
            errors,
        )
        self.assertTrue(
            any(
                "auto-merge requires separate exact deploy authorization"
                in error
                and development_target_id in error
                for error in errors
            ),
            errors,
        )

        self.authorize_merge_triggered_development_release(
            run, development_target_id
        )
        self.assertEqual([], validate_run(plan, run))

    def test_integration_pull_request_direct_merge_requires_release_grants(
        self,
    ) -> None:
        plan, run, development_target_id = self.integration_pull_request_v10()
        run["landing"]["auto_merge_requested"] = False
        run["landing"]["auto_merge_head_sha"] = None

        awaiting_authorization = copy.deepcopy(run)
        awaiting_authorization["authorizations"]["merge_pr"] = {
            "authorized": False,
            "source": None,
        }
        self.assertEqual([], validate_run(plan, awaiting_authorization))

        planning = copy.deepcopy(run)
        planning["landing"]["merge_status"] = "not_ready"
        self.assertEqual([], validate_run(plan, planning))

        errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "merge authorization must include its auto-deploy release targets"
                in error
                and development_target_id in error
                for error in errors
            ),
            errors,
        )
        self.assertTrue(
            any(
                "direct merge requires separate exact deploy authorization"
                in error
                and development_target_id in error
                for error in errors
            ),
            errors,
        )

        merged = copy.deepcopy(run)
        merged_sha = "c" * 40
        merged["landing"].update(
            {
                "pr_state": "merged",
                "merge_status": "merged",
                "merged_sha": merged_sha,
            }
        )
        merged["integration"]["integration_head_sha"] = merged_sha
        merged["landing"]["continuity"].update(
            {
                "status": "preserved",
                "head_sha": merged_sha,
            }
        )
        merged_errors = validate_run(plan, merged)
        self.assertTrue(
            any(
                "merge authorization must include its auto-deploy release targets"
                in error
                and development_target_id in error
                for error in merged_errors
            ),
            merged_errors,
        )
        self.assertTrue(
            any(
                "direct merge requires separate exact deploy authorization"
                in error
                and development_target_id in error
                for error in merged_errors
            ),
            merged_errors,
        )

        self.authorize_merge_triggered_development_release(
            run, development_target_id
        )
        self.assertEqual([], validate_run(plan, run))

    def test_v10_merged_landing_distinguishes_observed_and_authorized_merges(
        self,
    ) -> None:
        for mode in ("pull_request", "integration_pull_request"):
            with self.subTest(mode=mode):
                plan, run = self.merged_pull_request_v10(mode)
                # A harness-initiated direct merge retains exact current-head
                # authorization for every mission.
                self.assertEqual([], validate_run(plan, run))

                observed = copy.deepcopy(run)
                observed["authorizations"]["merge_pr"] = {
                    "authorized": False,
                    "source": None,
                }
                self.assertEqual([], validate_run(plan, observed))
                self.assertTrue(observed["authorizations"]["deploy"]["authorized"])

                completed_observation = copy.deepcopy(observed)
                mark_observed_merge_complete_v10(plan, completed_observation)
                self.assertEqual([], validate_run(plan, completed_observation))

                variants = {}
                stale = copy.deepcopy(run)
                stale["authorizations"]["merge_pr"]["authorized_head_sha"] = (
                    "f" * 40
                )
                variants["stale_head"] = stale

                partial = copy.deepcopy(run)
                partial["authorizations"]["merge_pr"]["scope"][
                    "mission_ids"
                ] = [next(iter(run["mission_states"]))]
                variants["partial_missions"] = partial

                for variant, invalid in variants.items():
                    with self.subTest(variant=variant):
                        errors = validate_run(plan, invalid)
                        merge_errors = [
                            error
                            for error in errors
                            if (
                                "merged pull-request landing requires merge "
                                "authorization for the exact PR, current PR "
                                "head, and every mission"
                            )
                            in error
                        ]
                        self.assertEqual(1, len(merge_errors), errors)
                        self.assertFalse(
                            any(
                                "requires separate exact deploy authorization"
                                in error
                                for error in errors
                            ),
                            errors,
                        )

    def test_v10_merge_triggered_production_pass_distinguishes_merge_actor(
        self,
    ) -> None:
        plan, run = self.merged_pull_request_v10("pull_request")
        plan["release"]["targets"] = [
            target
            for target in plan["release"]["targets"]
            if target["stage"] == "production"
        ]
        run["targets"].pop("web-development")
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        for entry in run["authorizations"].values():
            if isinstance(entry, dict) and entry.get("authorized") is True:
                entry["scope"]["plan_digest_sha256"] = digest

        def retained_evidence(subject: str) -> dict[str, object]:
            return {
                "subject": subject,
                "retained_reference": f"artifact:{subject}",
                "evidence_sha256": "d" * 64,
            }

        target = run["targets"]["web-production"]
        target.update(
            {
                "status": "PASS",
                "source_sha": run["landing"]["merged_sha"],
                "authorized_head_sha": run["landing"]["pr_head_sha"],
                "artifact": {
                    **retained_evidence("production-artifact"),
                    "build_id": "build-production-1",
                    "version": "1",
                    "signing_status": "not_required",
                },
                "channel": {
                    **retained_evidence("production-channel"),
                    "name": "workers-production",
                },
                "promotion": {
                    **retained_evidence("production-promotion"),
                    "status": "PASS",
                },
                "availability": {
                    **retained_evidence("production-availability"),
                    "status": "PASS",
                },
                "migration_status": "not_required",
                "verification_status": "PASS",
            }
        )

        # A harness-performed merge has exact merge and deploy grants.
        self.assertEqual([], validate_run(plan, run))

        # A human merge is observed state, so only the independent deploy grant
        # applies to the resulting production PASS.
        observed = copy.deepcopy(run)
        observed["authorizations"]["merge_pr"] = {
            "authorized": False,
            "source": None,
        }
        self.assertEqual([], validate_run(plan, observed))

        missing_deploy = copy.deepcopy(observed)
        missing_deploy["authorizations"]["deploy"] = {
            "authorized": False,
            "source": None,
        }
        missing_deploy_errors = validate_run(plan, missing_deploy)
        self.assertTrue(
            any(
                "PASS requires exact deploy authorization for "
                "release:web-production at the authorized event head"
                in error
                for error in missing_deploy_errors
            ),
            missing_deploy_errors,
        )
        self.assertFalse(
            any(
                "PASS requires exact merge_pr authorization" in error
                for error in missing_deploy_errors
            ),
            missing_deploy_errors,
        )

        stale_harness_merge = copy.deepcopy(run)
        stale_harness_merge["authorizations"]["merge_pr"]["authorized_head_sha"] = (
            "f" * 40
        )
        stale_errors = validate_run(plan, stale_harness_merge)
        self.assertTrue(
            any(
                "PASS requires exact merge_pr authorization for "
                "release:web-production at the authorized event head"
                in error
                for error in stale_errors
            ),
            stale_errors,
        )

        unauthorized_auto_merge = copy.deepcopy(observed)
        unauthorized_auto_merge["landing"]["auto_merge_requested"] = True
        unauthorized_auto_merge["landing"]["auto_merge_head_sha"] = (
            unauthorized_auto_merge["landing"]["pr_head_sha"]
        )
        auto_merge_errors = validate_run(plan, unauthorized_auto_merge)
        self.assertTrue(
            any(
                "PASS requires exact merge_pr authorization for "
                "release:web-production at the authorized event head"
                in error
                for error in auto_merge_errors
            ),
            auto_merge_errors,
        )

    def test_v10_auto_merge_still_requires_exact_merge_authorization(
        self,
    ) -> None:
        plan, run, development_target_id = self.integration_pull_request_v10()
        self.authorize_merge_triggered_development_release(
            run, development_target_id
        )
        run["authorizations"]["merge_pr"] = {
            "authorized": False,
            "source": None,
        }

        self.assert_run_error_contains(
            plan,
            run,
            "auto_merge_requested requires matching merge_pr authorization for the exact PR",
        )

    def test_v10_promotion_gates_bind_to_the_integration_head(self) -> None:
        root = SCRIPTS_DIR.parent
        plan = load_plan(root / "assets/templates/HARNESS_PLAN.template.md")
        run = load_run(root / "assets/templates/MISSION_RUNBOOK.template.md")
        run["integration"]["integration_head_sha"] = SHA_B
        run["landing"].update(
            {
                "mode": "pull_request",
                "pushed_head_sha": SHA_A,
                "pr_number": 7,
                "pr_url": "https://github.com/example/repo/pull/7",
                "pr_state": "open",
                "pr_head_sha": SHA_A,
            }
        )
        run["landing"]["continuity"].update(
            {
                "status": "not_required",
                "branch_ref": None,
                "head_sha": None,
                "reason": None,
            }
        )

        gate_states = (
            (
                "checks",
                {
                    "checks_status": "PASS",
                    "checks_head_sha": SHA_A,
                },
            ),
            (
                "review",
                {
                    "review_status": "PASS",
                    "review_head_sha": SHA_A,
                    "blocking_findings": 0,
                    "unresolved_threads": 0,
                },
            ),
            (
                "ready",
                {
                    "checks_status": "PASS",
                    "checks_head_sha": SHA_A,
                    "review_status": "PASS",
                    "review_head_sha": SHA_A,
                    "blocking_findings": 0,
                    "unresolved_threads": 0,
                    "merge_status": "ready",
                },
            ),
        )
        for gate, landing_state in gate_states:
            with self.subTest(gate=gate):
                stale = copy.deepcopy(run)
                stale["landing"].update(landing_state)
                self.assert_run_error_contains(
                    plan,
                    stale,
                    "promotion pull_request CI, review, ready, and final evidence "
                    "must match the current integration head",
                )

        current = copy.deepcopy(run)
        current["landing"].update(
            {
                "pushed_head_sha": SHA_B,
                "pr_head_sha": SHA_B,
                "checks_status": "PASS",
                "checks_head_sha": SHA_B,
                "review_status": "PASS",
                "review_head_sha": SHA_B,
                "blocking_findings": 0,
                "unresolved_threads": 0,
                "merge_status": "ready",
            }
        )
        self.assertEqual([], validate_run(plan, current))

    def test_v10_integration_pr_uses_feature_head_then_merged_base_head(
        self,
    ) -> None:
        plan, run, development_target_id = self.integration_pull_request_v10()
        self.authorize_merge_triggered_development_release(
            run, development_target_id
        )

        run["integration"]["integration_head_sha"] = SHA_B
        self.assertEqual([], validate_run(plan, run))

        merged_sha = "c" * 40
        run["landing"].update(
            {
                "pr_state": "merged",
                "merge_status": "merged",
                "merged_sha": merged_sha,
            }
        )
        run["integration"]["integration_head_sha"] = merged_sha
        run["landing"]["continuity"].update(
            {
                "status": "preserved",
                "head_sha": merged_sha,
            }
        )
        self.assertEqual([], validate_run(plan, run))

        run["landing"]["merged_sha"] = SHA_B
        self.assert_run_error_contains(
            plan,
            run,
            "merged integration_pull_request must become the current integration head",
        )

    def test_merge_pr_scope_requires_the_exact_landing_identity(self) -> None:
        plan, run, development_target_id = self.integration_pull_request_v10()
        self.authorize_merge_triggered_development_release(
            run, development_target_id
        )
        self.assertEqual([], validate_run(plan, run))

        mismatches = (
            (
                0,
                "future-pr:other/repo:"
                "base=development:head=codex/feature",
            ),
            (
                0,
                "future-pr:example/repo:"
                "base=production:head=codex/feature",
            ),
            (
                0,
                "future-pr:example/repo:"
                "base=development:head=codex/other",
            ),
            (1, "pr:https://github.com/other/repo/pull/7"),
            (1, "pr:https://github.com/example/repo/pull/8"),
        )
        for target_index, target in mismatches:
            with self.subTest(target=target):
                mismatched = copy.deepcopy(run)
                mismatched["authorizations"]["merge_pr"]["scope"]["targets"][
                    target_index
                ] = target

                errors = validate_run(plan, mismatched)

                self.assertTrue(
                    any(
                        f"target_sources.{target}:" in error
                        and "requires its own recorded authorization source" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_merge_pr_exact_target_requires_its_future_identity_sibling(
        self,
    ) -> None:
        plan, run, development_target_id = self.integration_pull_request_v10()
        self.authorize_merge_triggered_development_release(
            run, development_target_id
        )
        self.assertEqual([], validate_run(plan, run))

        exact_only = copy.deepcopy(run)
        exact_target = f"pr:{exact_only['landing']['pr_url']}"
        exact_only["authorizations"]["merge_pr"]["scope"]["targets"] = [
            exact_target,
            f"release:{development_target_id}",
        ]
        errors = validate_run(plan, exact_only)
        self.assertTrue(
            any(
                f"target_sources.{exact_target}:" in error
                and "requires its own recorded authorization source" in error
                for error in errors
            ),
            errors,
        )

        tampered = copy.deepcopy(exact_only)
        tampered_url = "https://github.com/other/repo/pull/99"
        tampered_target = f"pr:{tampered_url}"
        tampered["landing"]["pr_url"] = tampered_url
        tampered["landing"]["pr_number"] = 99
        tampered["authorizations"]["merge_pr"]["scope"]["targets"][0] = (
            tampered_target
        )
        errors = validate_run(plan, tampered)
        self.assertTrue(
            any(
                f"target_sources.{tampered_target}:" in error
                and "requires its own recorded authorization source" in error
                for error in errors
            ),
            errors,
        )

    def test_unmarked_v10_fails_closed_while_active_but_keeps_completed_history(
        self,
    ) -> None:
        """Active unmarked v10 dispatch fails closed without breaking history."""
        plan, run, development_target_id = self.integration_pull_request_v10()
        self.authorize_merge_triggered_development_release(
            run, development_target_id
        )
        exact_target = f"pr:{run['landing']['pr_url']}"
        run["authorizations"]["merge_pr"]["scope"]["targets"] = [
            exact_target,
            f"release:{development_target_id}",
        ]
        run["authorizations"]["merge_pr"].pop("target_sources")
        plan.pop("action_target_contract")
        run.pop("action_target_contract")
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        for entry in run["authorizations"].values():
            if entry.get("authorized") is True:
                entry["scope"]["plan_digest_sha256"] = digest

        errors = validate_run(plan, run)
        self.assertTrue(
            any(
                f"target_sources.{exact_target}:" in error
                and "requires its own recorded authorization source" in error
                for error in errors
            ),
            errors,
        )

        historical = copy.deepcopy(run)
        historical["status"] = "complete"
        historical_errors = validate_run(plan, historical)
        self.assertFalse(
            any("target_sources" in error for error in historical_errors),
            historical_errors,
        )

        opted_in = copy.deepcopy(run)
        opted_in["authorizations"]["merge_pr"]["target_sources"] = {}
        errors = validate_run(plan, opted_in)
        self.assertTrue(
            any(
                f"target_sources.{exact_target}:" in error
                and "requires its own recorded authorization source" in error
                for error in errors
            ),
            errors,
        )

        sourced = copy.deepcopy(run)
        sourced["authorizations"]["merge_pr"]["target_sources"] = {
            exact_target: "user: merge pull request 7 now that review passed",
            f"release:{development_target_id}": (
                "user: deploy the development release from this exact merge"
            ),
        }
        self.assertEqual([], validate_run(plan, sourced))

    def test_execution_intent_never_pushes_the_resolved_protected_base(self) -> None:
        for protected in ("main", "release"):
            with self.subTest(branch=protected):
                run = {
                    "integration": {"branch": f"refs/heads/{protected}"},
                    "landing": {
                        "mode": "pull_request",
                        "base_branch": protected,
                        "head_branch": f"refs/heads/{protected}",
                        "pr_url": None,
                    },
                }
                self.assertFalse(
                    execution_intent_target_in_scope(
                        {}, run, "push", f"branch:refs/heads/{protected}"
                    )
                )

        ordinary = {
            "integration": {"branch": "refs/heads/codex/feature"},
            "landing": {
                "mode": "local_only",
                "base_branch": "main",
                "head_branch": "refs/heads/codex/feature",
                "pr_url": None,
            },
        }
        self.assertTrue(
            execution_intent_target_in_scope(
                {}, ordinary, "push", "branch:refs/heads/codex/feature"
            )
        )

    def test_complete_integration_run_rejects_a_null_integration_object(self) -> None:
        """validate_run used to raise AttributeError instead of reporting."""
        plan = valid_plan()
        run = valid_run(plan)
        run["status"] = "complete"
        run["landing"]["mode"] = "integration_pull_request"
        run["landing"]["merge_status"] = "merged"
        run["integration"] = None

        errors = validate_run(plan, run)
        self.assertTrue(errors)

    def test_merge_pr_future_repository_identity_is_case_insensitive(self) -> None:
        plan, run, development_target_id = self.integration_pull_request_v10()
        self.authorize_merge_triggered_development_release(
            run, development_target_id
        )
        run["authorizations"]["merge_pr"]["scope"]["targets"][0] = (
            "future-pr:Example/Repo:"
            "base=development:head=codex/feature"
        )

        self.assertEqual([], validate_run(plan, run))

    def test_integration_pull_request_mode_always_treats_main_as_protected(
        self,
    ) -> None:
        plan, run, _ = self.integration_pull_request_v10()
        run["integration"]["branch"] = "refs/heads/main"
        run["landing"]["base_branch"] = "main"
        future_pr = (
            "future-pr:example/repo:"
            "base=main:head=refs/heads/codex/feature"
        )

        self.assertFalse(
            execution_intent_target_in_scope(
                plan, run, "push", "branch:refs/heads/main"
            )
        )
        self.assertFalse(
            execution_intent_target_in_scope(plan, run, "merge_pr", future_pr)
        )

    def test_integration_pull_request_mode_does_not_guess_custom_protection(
        self,
    ) -> None:
        integration_branch = "release"
        plan, run, development_target_id = self.integration_pull_request_v10()
        self.authorize_merge_triggered_development_release(
            run, development_target_id
        )
        run["integration"]["branch"] = f"refs/heads/{integration_branch}"
        run["landing"]["base_branch"] = integration_branch
        run["landing"]["base_branch_protection"]["branch_ref"] = (
            f"refs/heads/{integration_branch}"
        )
        run["landing"]["continuity"]["branch_ref"] = (
            f"refs/heads/{integration_branch}"
        )
        future_pr = (
            "future-pr:example/repo:"
            f"base={integration_branch}:head=refs/heads/codex/feature"
        )
        run["authorizations"]["merge_pr"]["scope"]["targets"][0] = future_pr
        self.assertEqual([], validate_run(plan, run))

    def test_integration_pull_request_requires_recorded_unprotected_base(
        self,
    ) -> None:
        plan, run, _ = self.integration_pull_request_v10()
        integration_branch = run["integration"]["branch"]
        push_target = f"branch:{integration_branch}"
        future_pr = run["authorizations"]["merge_pr"]["scope"]["targets"][0]

        del run["landing"]["base_branch_protection"]
        self.assertFalse(
            execution_intent_target_in_scope(plan, run, "push", push_target)
        )
        self.assertFalse(
            execution_intent_target_in_scope(plan, run, "merge_pr", future_pr)
        )
        missing_errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "integration_pull_request auto-merge requires exact repository evidence"
                in error
                for error in missing_errors
            ),
            missing_errors,
        )

        run["landing"]["base_branch_protection"] = {
            "branch_ref": integration_branch,
            "status": "protected",
            "source": "repository: AGENTS.md protected branch policy",
        }
        self.assertFalse(
            execution_intent_target_in_scope(plan, run, "push", push_target)
        )
        self.assertFalse(
            execution_intent_target_in_scope(plan, run, "merge_pr", future_pr)
        )
        protected_errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "integration_pull_request requires an unprotected base" in error
                for error in protected_errors
            ),
            protected_errors,
        )

        run["landing"]["base_branch_protection"]["status"] = "unprotected"
        self.assertTrue(
            execution_intent_target_in_scope(plan, run, "push", push_target)
        )
        self.assertTrue(
            execution_intent_target_in_scope(plan, run, "merge_pr", future_pr)
        )

        run["landing"]["base_branch_protection"]["branch_ref"] = "development"
        self.assertFalse(
            execution_intent_target_in_scope(plan, run, "push", push_target)
        )
        malformed_errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "base_branch_protection.branch_ref: must be a full local branch ref"
                in error
                for error in malformed_errors
            ),
            malformed_errors,
        )

        run["landing"]["base_branch_protection"]["branch_ref"] = "refs/heads/other"
        self.assertFalse(
            execution_intent_target_in_scope(plan, run, "push", push_target)
        )
        mismatch_errors = validate_run(plan, run)
        self.assertTrue(
            any(
                "base_branch_protection.branch_ref: must match landing.base_branch"
                in error
                for error in mismatch_errors
            ),
            mismatch_errors,
        )

    def test_completed_integration_pr_preserves_pre_evidence_readability(
        self,
    ) -> None:
        plan, run = self.merged_pull_request_v10("integration_pull_request")
        run["landing"]["auto_merge_requested"] = True
        run["landing"]["auto_merge_head_sha"] = run["landing"]["pr_head_sha"]
        mark_observed_merge_complete_v10(plan, run)
        del run["landing"]["base_branch_protection"]
        integration_branch = run["integration"]["branch"]
        future_pr = run["authorizations"]["merge_pr"]["scope"]["targets"][0]

        self.assertEqual([], validate_run(plan, run))
        self.assertTrue(
            execution_intent_target_in_scope(
                plan, run, "push", f"branch:{integration_branch}"
            )
        )
        self.assertTrue(
            execution_intent_target_in_scope(plan, run, "merge_pr", future_pr)
        )

    def test_pull_request_into_a_protected_branch_cannot_use_auto_merge(
        self,
    ) -> None:
        for protected in ("main", "release"):
            with self.subTest(branch=protected):
                plan, run = self.merged_pull_request_v10("pull_request")
                old_future_pr = next(
                    target
                    for target in run["authorizations"]["merge_pr"]["scope"]["targets"]
                    if target.startswith("future-pr:")
                )
                protected_future_pr = old_future_pr.replace(
                    "base=refs/heads/production",
                    f"base={protected}",
                )
                targets = run["authorizations"]["merge_pr"]["scope"]["targets"]
                targets[targets.index(old_future_pr)] = protected_future_pr
                target_sources = run["authorizations"]["merge_pr"]["target_sources"]
                target_sources[protected_future_pr] = target_sources.pop(old_future_pr)
                run["landing"].update(
                    {
                        "base_branch": protected,
                        "base_branch_protection": {
                            "branch_ref": f"refs/heads/{protected}",
                            "status": "protected",
                            "source": "repository: AGENTS.md protected branch policy",
                        },
                        "pr_state": "open",
                        "merge_status": "ready",
                        "merged_sha": None,
                        "auto_merge_requested": True,
                        "auto_merge_head_sha": run["landing"]["pr_head_sha"],
                    }
                )

                self.assert_run_error_contains(
                    plan,
                    run,
                    "pull_request into the resolved protected base cannot use "
                    "auto-merge",
                )

                run["landing"]["auto_merge_requested"] = False
                run["landing"]["auto_merge_head_sha"] = None
                self.assertEqual([], validate_run(plan, run))

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

    def test_merge_pr_scope_keeps_matching_future_identity_before_pr_creation(
        self,
    ) -> None:
        plan: dict[str, object] = {}
        run = {
            "integration": {"branch": "refs/heads/development"},
            "landing": {
                "mode": "integration_pull_request",
                "base_branch": "development",
                "head_branch": "refs/heads/codex/feature",
                "pr_url": None,
                "base_branch_protection": {
                    "branch_ref": "refs/heads/development",
                    "status": "unprotected",
                    "source": "repository: AGENTS.md integration branch policy",
                },
            },
        }
        matching = (
            "future-pr:example/repo:"
            "base=refs/heads/development:head=codex/feature"
        )

        self.assertTrue(
            execution_intent_target_in_scope(plan, run, "merge_pr", matching)
        )
        for target in (
            "future-pr:example/repo:base=production:head=codex/feature",
            "future-pr:example/repo:base=development:head=codex/other",
        ):
            with self.subTest(target=target):
                self.assertFalse(
                    execution_intent_target_in_scope(
                        plan, run, "merge_pr", target
                    )
                )

    def test_merge_pr_scope_normalizes_equivalent_branch_refs(self) -> None:
        plan: dict[str, object] = {}
        exact_pr = "pr:https://github.com/example/repo/pull/7"
        for integration_branch, landing_base in (
            ("refs/heads/development", "development"),
            ("development", "refs/heads/development"),
        ):
            with self.subTest(
                integration_branch=integration_branch,
                landing_base=landing_base,
            ):
                run = {
                    "integration": {"branch": integration_branch},
                    "landing": {
                        "mode": "integration_pull_request",
                        "base_branch": landing_base,
                        "head_branch": "refs/heads/codex/feature",
                        "pr_url": "https://github.com/example/repo/pull/7",
                        "base_branch_protection": {
                            "branch_ref": "refs/heads/development",
                            "status": "unprotected",
                            "source": "repository: AGENTS.md integration branch policy",
                        },
                    },
                }
                future_pr = (
                    "future-pr:example/repo:"
                    f"base={landing_base}:head=codex/feature"
                )
                run["authorizations"] = {
                    "merge_pr": {
                        "scope": {"targets": [future_pr, exact_pr]}
                    }
                }
                self.assertTrue(
                    execution_intent_target_in_scope(
                        plan, run, "merge_pr", future_pr
                    )
                )
                self.assertTrue(
                    execution_intent_target_in_scope(
                        plan, run, "merge_pr", exact_pr
                    )
                )

    def test_merge_pr_scope_keeps_main_out_of_scope_after_normalization(self) -> None:
        plan: dict[str, object] = {}
        exact_pr = "pr:https://github.com/example/repo/pull/7"
        for integration_branch, landing_base in (
            ("refs/heads/main", "main"),
            ("main", "refs/heads/main"),
        ):
            with self.subTest(
                integration_branch=integration_branch,
                landing_base=landing_base,
            ):
                run = {
                    "integration": {"branch": integration_branch},
                    "landing": {
                        "mode": "pull_request",
                        "base_branch": landing_base,
                        "head_branch": integration_branch,
                        "pr_url": "https://github.com/example/repo/pull/7",
                    },
                }
                future_pr = (
                    "future-pr:example/repo:"
                    f"base={landing_base}:head=codex/feature"
                )
                self.assertFalse(
                    execution_intent_target_in_scope(
                        plan, run, "merge_pr", future_pr
                    )
                )
                self.assertFalse(
                    execution_intent_target_in_scope(
                        plan, run, "merge_pr", exact_pr
                    )
                )

    def test_target_sources_use_resolved_landing_model_and_fail_closed(self) -> None:
        plan: dict[str, object] = {}

        custom_protected = {
            "integration": {"branch": "refs/heads/codex/feature"},
            "landing": {
                "mode": "pull_request",
                "base_branch": "refs/heads/release",
                "head_branch": "refs/heads/codex/feature",
                "pr_url": "https://github.com/example/repo/pull/7",
            },
        }
        protected_future_pr = (
            "future-pr:example/repo:"
            "base=refs/heads/release:head=refs/heads/codex/feature"
        )
        protected_push = {
            "source": "user: execute the development loop",
            "scope": {
                "targets": [
                    "branch:refs/heads/codex/feature",
                    "branch:refs/heads/release",
                ]
            },
        }
        errors: list[str] = []
        validate_target_sources(
            errors,
            "run.authorizations.push",
            protected_push,
            plan=plan,
            run=custom_protected,
            action="push",
        )
        self.assertTrue(
            any("target_sources.branch:refs/heads/release" in error for error in errors),
            errors,
        )
        protected_merge = {
            "source": "user: execute the development loop",
            "scope": {"targets": [protected_future_pr]},
        }
        errors = []
        validate_target_sources(
            errors,
            "run.authorizations.merge_pr",
            protected_merge,
            plan=plan,
            run=custom_protected,
            action="merge_pr",
        )
        self.assertTrue(
            any(f"target_sources.{protected_future_pr}" in error for error in errors),
            errors,
        )

        default_main = copy.deepcopy(custom_protected)
        default_main["landing"]["base_branch"] = "main"
        main_future_pr = protected_future_pr.replace(
            "refs/heads/release", "refs/heads/main"
        )
        self.assertFalse(
            execution_intent_target_in_scope(
                plan, default_main, "merge_pr", main_future_pr
            )
        )
        self.assertTrue(
            execution_intent_target_in_scope(
                plan,
                default_main,
                "push",
                "branch:refs/heads/codex/feature",
            )
        )

        non_protected = {
            "integration": {"branch": "refs/heads/development"},
            "landing": {
                "mode": "integration_pull_request",
                "base_branch": "development",
                "head_branch": "refs/heads/codex/feature",
                "pr_url": None,
                "base_branch_protection": {
                    "branch_ref": "refs/heads/development",
                    "status": "unprotected",
                    "source": "repository: AGENTS.md integration branch policy",
                },
            },
        }
        integration_future_pr = (
            "future-pr:example/repo:"
            "base=refs/heads/development:head=refs/heads/codex/feature"
        )
        self.assertTrue(
            execution_intent_target_in_scope(
                plan,
                non_protected,
                "push",
                "branch:refs/heads/development",
            )
        )
        self.assertTrue(
            execution_intent_target_in_scope(
                plan, non_protected, "merge_pr", integration_future_pr
            )
        )

        unknown = copy.deepcopy(non_protected)
        unknown["landing"]["mode"] = None
        self.assertFalse(
            execution_intent_target_in_scope(
                plan,
                unknown,
                "push",
                "branch:refs/heads/development",
            )
        )
        errors = []
        validate_target_sources(
            errors,
            "run.authorizations.push",
            {
                "source": "user: execute the development loop",
                "scope": {"targets": ["branch:refs/heads/development"]},
            },
            plan=plan,
            run=unknown,
            action="push",
        )
        self.assertTrue(
            any("requires its own recorded authorization source" in error for error in errors),
            errors,
        )

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

    def test_invalid_run_schema_does_not_crash_auto_merge_validation(self) -> None:
        plan = valid_plan()

        string_schema = valid_run(plan)
        string_schema["schema_version"] = "7"
        self.assert_run_error_contains(
            plan,
            string_schema,
            "run.schema_version: must equal 2 through 10",
        )

        complete_string_schema = valid_run(plan)
        complete_string_schema["schema_version"] = "9"
        complete_string_schema["status"] = "complete"
        del complete_string_schema["runtime_capabilities"]["runtime_adapter"]
        del complete_string_schema["landing"]
        del complete_string_schema["post_merge_cleanup"]
        del complete_string_schema["observed"]["git"]["parent_worktree_path"]
        for action in ("configure_repository", "manage_pr_review", "merge_pr"):
            del complete_string_schema["authorizations"][action]
        self.assert_run_error_contains(
            plan,
            complete_string_schema,
            "run.schema_version: must equal 2 through 10",
        )

        unsupported_schema = valid_run(plan)
        unsupported_schema["schema_version"] = 10
        del unsupported_schema["landing"]
        del unsupported_schema["post_merge_cleanup"]
        self.assert_run_error_contains(
            plan,
            unsupported_schema,
            "run.schema_version: schema v10 requires a schema v5 graph PLAN",
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

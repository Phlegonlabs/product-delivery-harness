#!/usr/bin/env python3
"""Typed graph orchestration tests (host-native provider binding only)."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import mission_dependencies, resolve_runtime_options  # noqa: E402
from harness_graph import _validate_graph  # noqa: E402
from harness_manifest import (  # noqa: E402
    AUTHORIZATION_KEYS,
    load_plan,
    load_run,
    plan_digest,
    topological_levels,
    validate_plan,
    validate_run,
)
from select_ready_nodes import (  # noqa: E402
    GraphSelectionError,
    _current_authorized_head,
    _runtime_binding,
    select_ready_nodes,
)
from test_harness_manifest import (  # noqa: E402
    authorize_action,
    authorize_execution,
    codex_capability_probe,
    current_version_gate,
    legacy_graph_plan,
    legacy_graph_run,
    mark_legacy_complete,
    mark_complete,
    retained_gate_execution,
    valid_plan,
    valid_run,
)
from validate_node_result import validate_node_result  # noqa: E402


def graph_node(
    node_id: str,
    kind: str,
    ref: str,
    executor: str,
    outcomes: list[str],
    *,
    providers: list[str] | None = None,
    preferred: str | None = None,
    provider_options: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": node_id,
        "kind": kind,
        "ref": ref,
        "executor": executor,
        "allowed_outcomes": outcomes,
        "max_attempts": 2,
        "runtime": (
            {
                "preferred_provider": preferred,
                "allowed_providers": providers or ["codex", "claude_code"],
                **({"provider_options": provider_options} if provider_options is not None else {}),
            }
            if executor == "runtime_worker"
            else None
        ),
    }


def lifecycle_node(ref: str, **extra: object) -> dict[str, object]:
    """A minimal harness-parent lifecycle node; `extra` sets `target` when given."""
    return {
        "id": "N-LIFECYCLE",
        "kind": "lifecycle",
        "ref": ref,
        "executor": "harness_parent",
        "allowed_outcomes": ["pass", "blocked"],
        "max_attempts": 1,
        "runtime": None,
        **extra,
    }


def start_mission(
    run: dict[str, object],
    plan: dict[str, object],
    digest: str,
    mission_id: str = "M1",
    *,
    base_sha: str | None = None,
) -> None:
    """Put one mission's graph node and mission state into the running shape."""
    current_scope = run.get("execution_authorization_scope")
    current_missions = (
        current_scope.get("mission_ids", [])
        if isinstance(current_scope, dict)
        else []
    )
    authorize_execution(
        run,
        sorted(set(current_missions) | {mission_id}),
        status="running",
        plan=plan,
        digest=digest,
    )
    run["graph_state"]["node_states"][f"N-{mission_id}"].update(
        {
            "phase": "running",
            "attempts": 1,
            "last_attempt_id": f"ATT-N-{mission_id}-1",
            "bound_worker_id": f"W-{mission_id}",
        }
    )
    run["mission_states"][mission_id].update(
        {
            "phase": "worker_running",
            "lease_id": f"LEASE-{mission_id}-1",
            "lease_plan_revision": plan["revision"],
            "lease_plan_digest_sha256": digest,
            "worker_id": f"W-{mission_id}",
            "base_sha": (
                base_sha if base_sha is not None else run["integration"]["batch_base_sha"]
            ),
        }
    )


def one_node_graph_errors(
    node: dict[str, object],
    missions: dict[str, object] | None = None,
    **kwargs: object,
) -> list[str]:
    """Validate a single-node, edgeless graph and return the errors it raised."""
    errors: list[str] = []
    _validate_graph(
        errors,
        {"entry_nodes": [node["id"]], "nodes": [node], "edges": []},
        missions or {},
        set(),
        require_bounded_review_repair=True,
        **kwargs,
    )
    return errors


def valid_graph_plan() -> dict[str, object]:
    """The canonical PLAN. It has been graph-backed since v5 became the only one."""
    return valid_plan()


def detach_mission_edges(plan: dict[str, object]) -> None:
    """Make M1 and M2 independent roots while keeping their reviews wired."""
    plan["graph"]["entry_nodes"] = ["N-M1", "N-M2"]
    plan["graph"]["edges"] = [
        edge for edge in plan["graph"]["edges"] if edge["id"] != "E-M1-M2"
    ]


def mission_nodes(plan: dict[str, object]) -> list[dict[str, object]]:
    return [node for node in plan["graph"]["nodes"] if node["kind"] == "mission"]


def attach_single_mission_review(
    plan: dict[str, object],
    review: dict[str, object],
    mission_id: str = "M1",
) -> None:
    """Attach a same-worktree review and route PASS to the deterministic final gate."""
    plan["graph"]["nodes"].append(review)
    plan["graph"]["edges"].extend(
        [
            {
                "id": f"E-{mission_id}-{review['id']}",
                "kind": "dependency",
                "from": f"N-{mission_id}",
                "to": review["id"],
                "on_outcomes": ["pass"],
                "max_traversals": None,
            },
            {
                "id": f"E-{review['id']}-FINAL",
                "kind": "route",
                "from": review["id"],
                "to": "N-FINAL",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            },
        ]
    )


def record_worker_passed_mission_with_review(
    plan: dict[str, object],
    run: dict[str, object],
    mission_id: str,
    *,
    provider: str,
    driver: str,
) -> None:
    """Record a worker-passed mission and its current exact-head singleton review."""
    digest = plan_digest(plan)
    head_sha = "b" * 40
    worker_id = f"W-{mission_id}"
    lease_id = f"LEASE-{mission_id}"
    review_node_id = f"N-REVIEW-{mission_id}"
    review_worker_id = f"RW-{mission_id}"
    review_attempt_id = f"ATT-REVIEW-{mission_id}"
    mission_node = next(
        node
        for node in plan["graph"]["nodes"]
        if node["kind"] == "mission" and node["ref"] == mission_id
    )
    review_node = next(
        node for node in plan["graph"]["nodes"] if node["id"] == review_node_id
    )

    def binding(node: dict[str, object]) -> dict[str, object]:
        options = resolve_runtime_options(node["runtime"], provider)
        return {
            "provider": provider,
            "driver": driver,
            "source": "host",
            **options,
        }

    run["graph_state"]["node_states"][f"N-{mission_id}"].update(
        {
            "phase": "running",
            "attempts": 1,
            "last_attempt_id": f"ATT-{mission_id}",
            "last_outcome": None,
            "bound_worker_id": worker_id,
        }
    )
    run["mission_states"][mission_id].update(
        {
            "phase": "worker_passed",
            "lease_id": lease_id,
            "lease_plan_revision": plan["revision"],
            "lease_plan_digest_sha256": digest,
            "worker_id": worker_id,
            "base_sha": run["integration"]["batch_base_sha"],
            "head_sha": head_sha,
            "integration_gate": "planned",
            "integrated_sha": None,
        }
    )
    run["workers"].append(
        {
            "worker_id": worker_id,
            "mission_id": mission_id,
            "lease_id": lease_id,
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "batch_base_sha": run["integration"]["batch_base_sha"],
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "runtime_binding": binding(mission_node),
            "task_thread_id": None,
            "worktree_path": f"C:/repo/worktrees/{mission_id}",
            "branch_ref": f"refs/heads/codex/{mission_id.lower()}",
            "report_path": None,
            "phase": "worker_passed",
            "worker_head_sha": head_sha,
        }
    )
    run["observed"]["git"]["worktrees"] = [
        {
            "path": f"C:/repo/worktrees/{mission_id}",
            "branch_ref": f"refs/heads/codex/{mission_id.lower()}",
            "head_sha": head_sha,
            "managed_by": "parent",
            "dirty": False,
        }
    ]
    authorize_action(
        run,
        "spawn_subagents",
        [mission_id],
        [f"worker:{worker_id}"],
    )
    authorize_action(
        run,
        "create_local_worktrees",
        [mission_id],
        [f"worktree:C:/repo/worktrees/{mission_id}"],
    )
    authorize_action(
        run,
        "create_local_branches",
        [mission_id],
        [f"branch:refs/heads/codex/{mission_id.lower()}"],
    )
    authorize_action(
        run,
        "create_local_commits",
        [mission_id],
        [f"branch:refs/heads/codex/{mission_id.lower()}"],
    )
    worker_attempt_id = f"ATT-{mission_id}"
    run["attempt_log"].append(
        {
            "attempt_id": worker_attempt_id,
            "mission_id": mission_id,
            "task_id": None,
            "lease_id": lease_id,
            "kind": "worker_verifier",
            "result": "PASS",
            "evidence": [],
        }
    )
    declaration = next(
        mission
        for mission in plan["missions"]
        if mission["id"] == mission_id
    )["worker_verifiers"][0]
    run["verifier_executions"].append(
        retained_gate_execution(
            plan,
            run,
            declaration,
            layer="worker",
            execution_id=f"EXEC-WORKER-{mission_id}",
            mission_id=mission_id,
            attempt_id=worker_attempt_id,
            lease_id=lease_id,
            head_sha=head_sha,
            checkout_role="worker",
        )
    )
    run["graph_state"]["node_states"][review_node_id].update(
        {
            "phase": "succeeded",
            "attempts": 1,
            "last_attempt_id": review_attempt_id,
            "last_outcome": "pass",
            "bound_worker_id": review_worker_id,
        }
    )
    run["review_workers"].append(
        {
            "worker_id": review_worker_id,
            "node_id": review_node_id,
            "attempt_id": review_attempt_id,
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "graph_revision": run["graph_state"]["graph_revision"],
            "reviewed_sha": head_sha,
            "review_path": f"C:/repo/worktrees/{mission_id}",
            "worker_runtime": "subagent",
            "completion_channel": "agent_result",
            "runtime_binding": binding(review_node),
            "task_thread_id": None,
            "report_path": None,
            "phase": "worker_passed",
            "outcome": "pass",
            "findings": [],
        }
    )


def valid_graph_run(plan: dict[str, object]) -> dict[str, object]:
    """The canonical RUN with a live observation, ready for node selection."""
    run = valid_run(plan)
    run["observed"]["captured_at"] = "2026-07-25T00:00:00Z"
    return run


def authorize(
    run: dict[str, object], action: str, mission_ids: list[str], target: str
) -> None:
    existing = run["authorizations"].get(action)
    existing_scope = (
        existing.get("scope")
        if isinstance(existing, dict) and existing.get("authorized") is True
        else None
    )
    retained_missions = (
        existing_scope.get("mission_ids", [])
        if isinstance(existing_scope, dict)
        else []
    )
    retained_targets = (
        existing_scope.get("targets", [])
        if isinstance(existing_scope, dict)
        else []
    )
    run["authorizations"][action] = {
        "authorized": True,
        "source": "user requested graph execution and Claude trial",
        "scope": {
            "run_id": run["run_id"],
            "plan_revision": run["plan"]["revision"],
            "plan_digest_sha256": run["plan"]["digest_sha256"],
            "mission_ids": sorted(set(retained_missions) | set(mission_ids)),
            "targets": list(dict.fromkeys([*retained_targets, target])),
        },
        "expires_when": "run_complete",
    }


def authorize_recorded_worker(
    run: dict[str, object], worker: dict[str, object]
) -> None:
    """Retain the exact lifecycle grants and observed checkout for one worker."""
    mission_id = worker["mission_id"]
    worktree_path = worker["worktree_path"]
    branch_ref = worker["branch_ref"]
    managed_by = (
        "app"
        if worker["workspace_mode"] == "app_managed_worktree"
        else "parent"
    )
    worktree_action = (
        "create_app_managed_worktrees"
        if managed_by == "app"
        else "create_local_worktrees"
    )
    run["observed"]["git"]["worktrees"].append(
        {
            "path": worktree_path,
            "branch_ref": branch_ref,
            "head_sha": worker["worker_head_sha"] or worker["batch_base_sha"],
            "managed_by": managed_by,
            "dirty": False,
        }
    )
    if worker["worker_runtime"] == "app_task":
        authorize_action(
            run,
            "create_user_owned_tasks",
            [mission_id],
            [f"task:{worker['task_thread_id']}"],
        )
    authorize_action(
        run,
        worktree_action,
        [mission_id],
        [f"worktree:{worktree_path}"],
    )
    for action in ("create_local_branches", "create_local_commits"):
        authorize_action(
            run,
            action,
            [mission_id],
            [f"branch:{branch_ref}"],
        )


class GraphManifestTests(unittest.TestCase):
    def test_review_stage_accepts_only_preintegration_or_integration(self) -> None:
        plan = valid_plan()
        review = next(
            node for node in plan["graph"]["nodes"]
            if node.get("review") is not None
        )
        review["review"]["stage"] = "after_everything"

        self.assertTrue(
            any("must be preintegration or integration" in error for error in validate_plan(plan))
        )

    def test_runtime_review_allows_at_most_two_attempts(self) -> None:
        plan = valid_plan()
        review = next(
            node for node in plan["graph"]["nodes"]
            if node.get("review") is not None
        )
        review["max_attempts"] = 3

        errors = validate_plan(plan)

        self.assertTrue(
            any("runtime review allows at most 2 attempts" in error for error in errors),
            errors,
        )







    def test_lifecycle_node_target_rejects_wildcard_and_bad_format(self) -> None:
        for target in ("*", "not-a-target", ""):
            with self.subTest(target=target):
                errors = one_node_graph_errors(lifecycle_node("push", target=target))
                self.assertTrue(
                    any(
                        "must be null or an exact non-wildcard authorization target" in error
                        for error in errors
                    ),
                    f"expected a target error for {target!r} in {errors!r}",
                )

    def test_lifecycle_node_target_is_optional_for_backward_compatibility(self) -> None:
        # A PLAN authored before the `target` field existed omits it entirely;
        # that must stay valid so this addition never breaks an already-valid
        # PLAN (select_ready_nodes.py falls back to the "*" default for it).
        self.assertEqual([], one_node_graph_errors(lifecycle_node("push")))

    def test_target_field_is_rejected_outside_lifecycle_nodes(self) -> None:
        errors = one_node_graph_errors(
            {
                "id": "N-M1",
                "kind": "mission",
                "ref": "M1",
                "executor": "runtime_worker",
                "allowed_outcomes": ["pass", "retryable_failure", "blocked"],
                "max_attempts": 1,
                "runtime": {
                    "preferred_provider": None,
                    "allowed_providers": ["codex"],
                },
                "target": "branch:codex/example",
            },
            {"M1": {"id": "M1"}},
        )
        self.assertTrue(
            any(
                "must be omitted unless the node is lifecycle" in error
                for error in errors
            ),
            errors,
        )

    def test_market_provider_ids_plan_validate_without_schema_changes(self) -> None:
        plan = valid_graph_plan()
        for node in mission_nodes(plan):
            node["runtime"]["allowed_providers"] = ["gemini_cli", "generic"]

        self.assertEqual([], validate_plan(plan))

        plan = valid_graph_plan()
        for node in mission_nodes(plan):
            node["runtime"]["allowed_providers"] = ["Gemini CLI", "copilot"]
        errors = validate_plan(plan)
        self.assertTrue(
            any("providers must be lowercase ids" in error for error in errors)
        )

    def test_plan_v4_and_v5_project_the_same_graph_dependencies(self) -> None:
        current_plan = valid_graph_plan()
        expected = mission_dependencies(current_plan)
        self.assertTrue(any(expected.values()))

        legacy_plan = legacy_graph_plan()

        self.assertEqual(expected, mission_dependencies(legacy_plan))

    def test_schema_v4_and_v8_are_valid_and_keep_mission_topology(self) -> None:
        plan = legacy_graph_plan()
        run = legacy_graph_run(plan, 8)

        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_run(plan, run))
        self.assertEqual({"M1": 0, "M2": 1}, topological_levels(plan))

    def test_workflow_run_binding_is_optional_and_validated(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        start_mission(run, plan, digest)
        run["workflow_runs"] = [
            {
                "workflow_run_id": "wf_test",
                "workflow_task_id": "task-test",
                "resume_from_run_id": None,
                "script_path": "assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js",
                "script_sha256": "c" * 64,
                "run_id": run["run_id"],
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "graph_revision": run["graph_state"]["graph_revision"],
                "batch_base_sha": run["integration"]["batch_base_sha"],
                "node_ids": ["N-M1"],
                "attempt_ids": {"N-M1": "ATT-N-M1-1"},
                "provider": "claude_code",
                "driver": "dynamic_workflow",
                "tool_profile": "mission_write",
                "status": "running",
                "result_evidence": [],
                "metrics": {"duration_ms": None, "token_count": None},
            }
        ]

        self.assertEqual([], validate_run(plan, run))
        run["workflow_runs"][0]["batch_base_sha"] = "b" * 40
        self.assertTrue(
            any("running workflow must match RUN" in error for error in validate_run(plan, run))
        )
        run["workflow_runs"][0]["batch_base_sha"] = run["integration"]["batch_base_sha"]
        run["workflow_runs"][0]["attempt_ids"]["N-M1"] = "ATT-STALE"
        self.assertTrue(
            any("active running node attempt" in error for error in validate_run(plan, run))
        )
        run["workflow_runs"][0]["attempt_ids"]["N-M1"] = "ATT-N-M1-1"
        run["status"] = "complete"
        self.assertTrue(
            any("complete RUN cannot retain a running workflow" in error for error in validate_run(plan, run))
        )
        run["status"] = "draft"
        run["workflow_runs"][0]["tool_profile"] = "visual_review_readonly"
        self.assertTrue(
            any("does not match its review node types" in error for error in validate_run(plan, run))
        )
        run["workflow_runs"][0].update(
            {
                "status": "completed",
                "tool_profile": "mission_write",
                "node_ids": ["N-HISTORICAL"],
                "attempt_ids": {"N-HISTORICAL": "ATT-HISTORICAL-1"},
            }
        )
        self.assertFalse(
            any("unknown graph nodes" in error for error in validate_run(plan, run))
        )

    def test_workflow_runs_are_claude_code_only(self) -> None:
        # A Codex-hosted graph RUN never produces workflow_runs entries: the
        # guarded external-Codex-agent workflow driver is fully removed, and
        # provider "codex" has no allowed workflow driver at all anymore.
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["runtime"] = {
            "preferred_provider": "claude_code",
            "allowed_providers": ["claude_code"],
        }
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        start_mission(run, plan, digest)
        workflow = {
            "workflow_run_id": "wf_test",
            "workflow_task_id": "task-test",
            "resume_from_run_id": None,
            "script_path": "assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js",
            "script_sha256": "d" * 64,
            "run_id": run["run_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "graph_revision": run["graph_state"]["graph_revision"],
            "batch_base_sha": run["integration"]["batch_base_sha"],
            "node_ids": ["N-M1"],
            "attempt_ids": {"N-M1": "ATT-N-M1-1"},
            "provider": "claude_code",
            "driver": "dynamic_workflow",
            "tool_profile": "mission_write",
            "status": "running",
            "result_evidence": [],
            "metrics": {"duration_ms": None, "token_count": None},
        }
        run["workflow_runs"] = [workflow]

        self.assertEqual([], validate_run(plan, run))

        codex_workflow = copy.deepcopy(run)
        codex_workflow["workflow_runs"][0]["provider"] = "codex"
        self.assertTrue(
            any(
                "unsupported workflow provider" in error
                for error in validate_run(plan, codex_workflow)
            )
        )

        codex_driver = copy.deepcopy(run)
        codex_driver["workflow_runs"][0]["provider"] = "codex"
        codex_driver["workflow_runs"][0]["driver"] = "app_threads"
        self.assertTrue(
            any(
                "unsupported workflow provider" in error
                for error in validate_run(plan, codex_driver)
            )
        )

    def test_one_workflow_run_may_cover_nodes_with_different_models(self) -> None:
        # workflow_runs no longer carries its own model/reasoning_effort: each
        # node's resolved model already lives on its own workers[]/
        # review_workers[] runtime_binding, so one live Workflow invocation
        # may freely mix models across the node_ids it covers.
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["runtime"]["allowed_providers"] = ["claude_code"]
        plan["graph"]["nodes"][0]["runtime"]["provider_options"] = {
            "claude_code": {"model": "sonnet", "reasoning_effort": None}
        }
        plan["graph"]["nodes"][1]["runtime"]["allowed_providers"] = ["claude_code"]
        plan["graph"]["nodes"][1]["runtime"]["provider_options"] = {
            "claude_code": {"model": "haiku", "reasoning_effort": None}
        }
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        start_mission(run, plan, digest, "M1")
        start_mission(run, plan, digest, "M2")
        run["workflow_runs"] = [
            {
                "workflow_run_id": "wf_test",
                "workflow_task_id": "task-test",
                "resume_from_run_id": None,
                "script_path": "assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js",
                "script_sha256": "d" * 64,
                "run_id": run["run_id"],
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "graph_revision": run["graph_state"]["graph_revision"],
                "batch_base_sha": run["integration"]["batch_base_sha"],
                "node_ids": ["N-M1", "N-M2"],
                "attempt_ids": {"N-M1": "ATT-N-M1-1", "N-M2": "ATT-N-M2-1"},
                "provider": "claude_code",
                "driver": "dynamic_workflow",
                "tool_profile": "mission_write",
                "status": "running",
                "result_evidence": [],
                "metrics": {"duration_ms": None, "token_count": None},
            }
        ]

        self.assertEqual([], validate_run(plan, run))

        with_model_key = copy.deepcopy(run)
        with_model_key["workflow_runs"][0]["model"] = "sonnet"
        self.assertTrue(
            any(
                "unknown keys: model" in error
                for error in validate_run(plan, with_model_key)
            )
        )

    def test_schema_v4_and_v9_closeout_preserves_graph_state(self) -> None:
        plan = legacy_graph_plan()
        run = legacy_graph_run(plan, 9)
        mark_legacy_complete(plan, run)

        errors = validate_run(plan, run)
        self.assertTrue(
            any("every node to succeed, skip, or be superseded" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("every edge to be terminal" in error for error in errors),
            errors,
        )

        attempt_by_node: dict[str, str] = {}
        for index, node in enumerate(plan["graph"]["nodes"], start=1):
            attempt_id = f"ATTEMPT-{index}"
            attempt_by_node[node["id"]] = attempt_id
            run["graph_state"]["node_states"][node["id"]].update(
                {
                    "phase": "succeeded",
                    "attempts": 1,
                    "last_attempt_id": attempt_id,
                    "last_outcome": "pass",
                }
            )
        for edge in plan["graph"]["edges"]:
            run["graph_state"]["edge_states"][edge["id"]].update(
                {
                    "status": "traversed",
                    "traversals": 1,
                    "source_attempt_id": attempt_by_node[edge["from"]],
                }
            )

        self.assertEqual([], validate_run(plan, run))
        run["graph_state"]["node_states"]["N-FINAL"].update(
            {
                "phase": "failed",
                "last_outcome": "retryable_failure",
            }
        )
        self.assertTrue(
            any(
                "every node to succeed, skip, or be superseded" in error
                for error in validate_run(plan, run)
            )
        )
        run["graph_state"]["node_states"]["N-FINAL"].update(
            {
                "phase": "succeeded",
                "last_outcome": "retryable_failure",
            }
        )
        self.assertTrue(
            any(
                "every succeeded node to have pass outcome" in error
                for error in validate_run(plan, run)
            )
        )


    def test_malformed_graph_scalars_return_errors_without_crashing(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["id"] = []
        self.assertTrue(any("flat uppercase identifier" in error for error in validate_plan(plan)))

        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["kind"] = []
        self.assertTrue(any("unsupported value" in error for error in validate_plan(plan)))

        for field, location in (
            ("ref", "nodes[0]"),
            ("id", "edges[0]"),
            ("from", "edges[0]"),
            ("to", "edges[0]"),
        ):
            for malformed in ([], {}):
                with self.subTest(field=field, malformed=type(malformed).__name__):
                    plan = valid_graph_plan()
                    collection = (
                        plan["graph"]["nodes"]
                        if location.startswith("nodes")
                        else plan["graph"]["edges"]
                    )
                    collection[0][field] = malformed
                    errors = validate_plan(plan)
                    self.assertTrue(any(f"plan.graph.{location}.{field}" in error for error in errors))

        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        run["graph_state"] = []
        self.assertTrue(any("run.graph_state" in error for error in validate_run(plan, run)))

        for field in ("phase", "last_outcome"):
            for malformed in ([], {}):
                with self.subTest(field=field, malformed=type(malformed).__name__):
                    run = valid_graph_run(plan)
                    run["graph_state"]["node_states"]["N-M1"][field] = malformed
                    errors = validate_run(plan, run)
                    self.assertTrue(
                        any(f"run.graph_state.node_states.N-M1.{field}" in error for error in errors)
                    )

        edge_id = plan["graph"]["edges"][0]["id"]
        for malformed in ([], {}):
            with self.subTest(field="status", malformed=type(malformed).__name__):
                run = valid_graph_run(plan)
                run["graph_state"]["edge_states"][edge_id]["status"] = malformed
                errors = validate_run(plan, run)
                self.assertTrue(
                    any(
                        f"run.graph_state.edge_states.{edge_id}.status" in error
                        for error in errors
                    )
                )

    def test_schema_v4_source_content_is_bound_into_the_plan_digest(self) -> None:
        plan = legacy_graph_plan()
        original_digest = plan_digest(plan)
        plan["sources"][0]["content_sha256"] = "e" * 64

        self.assertNotEqual(original_digest, plan_digest(plan))
        plan["sources"][0]["content_sha256"] = None
        plan["sources"][0]["source_revision"] = None
        self.assertTrue(
            any("require content_sha256 or source_revision" in error for error in validate_plan(plan))
        )

    def test_runtime_nodes_require_a_declared_workflow_failure_outcome(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["allowed_outcomes"] = ["pass"]

        self.assertTrue(
            any(
                "runtime or parent execution requires retryable_failure or blocked" in error
                for error in validate_plan(plan)
            )
        )

    def test_required_review_type_needs_a_matching_runtime_review_node(self) -> None:
        plan = valid_graph_plan()
        plan["required_reviews"] = ["frontend_code"]

        self.assertTrue(
            any("missing runtime review nodes: frontend_code" in error for error in validate_plan(plan))
        )

    def test_provider_options_validate_and_bind_model_policy(self) -> None:
        plan = valid_graph_plan()
        node = plan["graph"]["nodes"][0]
        node["runtime"]["provider_options"] = {
            "codex": {
                "model": "gpt-5.6-terra",
                "reasoning_effort": "medium",
            },
            "claude_code": {
                "model": "sonnet",
                "reasoning_effort": None,
            },
        }
        self.assertEqual([], validate_plan(plan))

        runtime = valid_graph_run(plan)["runtime_capabilities"]
        runtime["runtime_adapter"].update(
            {
                "provider": "codex",
                "available_drivers": ["app_threads", "sequential_parent"],
                "detection_source": "observed",
            }
        )
        binding = _runtime_binding(node, runtime)
        self.assertEqual("gpt-5.6-terra", binding["model"])
        self.assertEqual("medium", binding["reasoning_effort"])
        self.assertEqual("plan_provider_options", binding["option_source"])

        node["runtime"]["provider_options"]["claude_code"]["reasoning_effort"] = "high"
        self.assertEqual([], validate_plan(plan))
        node["runtime"]["provider_options"]["generic"] = {
            "model": None,
            "reasoning_effort": "high",
        }
        node["runtime"]["allowed_providers"].append("generic")
        self.assertTrue(any("supports selectable effort" in error for error in validate_plan(plan)))

    def test_pi_provider_uses_subagents_with_host_owned_model_routing(self) -> None:
        plan = valid_graph_plan()
        node = plan["graph"]["nodes"][0]
        node["runtime"]["preferred_provider"] = "pi"
        node["runtime"]["allowed_providers"].append("pi")
        node["runtime"]["provider_options"] = {
            "pi": {"model": None, "reasoning_effort": "high"}
        }
        self.assertEqual([], validate_plan(plan))

        runtime = valid_graph_run(plan)["runtime_capabilities"]
        runtime.update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
            }
        )
        runtime["runtime_adapter"].update(
            {
                "provider": "pi",
                "available_drivers": ["subagents", "sequential_parent"],
                "detection_source": "observed",
            }
        )
        binding = _runtime_binding(node, runtime)
        self.assertEqual("pi", binding["provider"])
        self.assertEqual("subagents", binding["driver"])
        self.assertIsNone(binding["model"])
        self.assertEqual("high", binding["reasoning_effort"])
        self.assertEqual("plan_provider_options", binding["option_source"])

        node["runtime"]["provider_options"]["pi"]["reasoning_effort"] = "unsupported"
        self.assertTrue(any("supported reasoning effort" in error for error in validate_plan(plan)))
        node["runtime"]["provider_options"]["pi"]["reasoning_effort"] = "medium"
        self.assertEqual([], validate_plan(plan))
        node["runtime"]["provider_options"]["pi"]["model"] = "gpt-5.6-sol"
        self.assertTrue(any("Pi role configuration owns model selection" in error for error in validate_plan(plan)))

    def test_run_worker_binding_must_match_plan_provider_options(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["runtime"]["provider_options"] = {
            "codex": {
                "model": "gpt-5.6-terra",
                "reasoning_effort": "medium",
            }
        }
        run = valid_graph_run(plan)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
            }
        )
        run["runtime_capabilities"]["runtime_adapter"].update(
            {
                "provider": "codex",
                "available_drivers": ["app_threads", "sequential_parent"],
                "detection_source": "observed",
            }
        )
        run["workers"].append(
            {
                "worker_id": "W-M1",
                "mission_id": "M1",
                "lease_id": "LEASE-M1",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "batch_base_sha": "a" * 40,
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "runtime_binding": {
                    "provider": "codex",
                    "driver": "app_threads",
                    "source": "host",
                    "model": "gpt-5.6-terra",
                    "reasoning_effort": "medium",
                    "option_source": "plan_provider_options",
                },
                "task_thread_id": "THREAD-M1",
                "worktree_path": "C:/repo/worktrees/M1",
                "branch_ref": "refs/heads/codex/m1",
                "report_path": None,
                "phase": "leased",
                "worker_head_sha": None,
            }
        )
        authorize_recorded_worker(run, run["workers"][0])

        self.assertEqual([], validate_run(plan, run))
        run["workers"][0]["runtime_binding"]["reasoning_effort"] = "high"
        self.assertTrue(
            any("must match the matching PLAN provider option" in error for error in validate_run(plan, run))
        )

    def test_pi_run_worker_binding_accepts_plan_reasoning_effort(self) -> None:
        plan = valid_graph_plan()
        node = plan["graph"]["nodes"][0]
        node["runtime"]["preferred_provider"] = "pi"
        node["runtime"]["allowed_providers"].append("pi")
        node["runtime"]["provider_options"] = {
            "pi": {"model": None, "reasoning_effort": "high"}
        }
        run = valid_graph_run(plan)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
            }
        )
        run["runtime_capabilities"]["runtime_adapter"].update(
            {
                "provider": "pi",
                "available_drivers": ["subagents", "sequential_parent"],
                "detection_source": "observed",
            }
        )
        worker = {
            "worker_id": "W-M1-PI",
            "mission_id": "M1",
            "lease_id": "LEASE-M1-PI",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "batch_base_sha": "a" * 40,
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "runtime_binding": {
                "provider": "pi",
                "driver": "subagents",
                "source": "host",
                "model": None,
                "reasoning_effort": "high",
                "option_source": "plan_provider_options",
            },
            "task_thread_id": "pi-run-m1",
            "worktree_path": "C:/repo/worktrees/M1",
            "branch_ref": "refs/heads/codex/m1",
            "report_path": None,
            "phase": "leased",
            "worker_head_sha": None,
        }
        run["workers"].append(worker)
        authorize_recorded_worker(run, worker)
        authorize_action(
            run,
            "spawn_subagents",
            ["M1"],
            ["worker:W-M1-PI"],
        )

        self.assertEqual([], validate_run(plan, run))

        claude_rebind = copy.deepcopy(run)
        claude_rebind["workers"][0]["runtime_binding"] = {
            "provider": "claude_code",
            "driver": "dynamic_workflow",
            "source": "host",
            "model": "sonnet",
            "reasoning_effort": None,
            "option_source": "provider_default",
        }
        errors = validate_run(plan, claude_rebind)
        self.assertIn(
            "run.workers[0].runtime_binding.provider: must match the current RUN runtime adapter provider",
            errors,
        )
        self.assertIn(
            "run.workers[0].runtime_binding.driver: must match the current RUN runtime adapter driver",
            errors,
        )

        wrong_pi_driver = copy.deepcopy(run)
        wrong_pi_driver["workers"][0]["runtime_binding"]["driver"] = "dynamic_workflow"
        self.assertIn(
            "run.workers[0].runtime_binding.driver: must match the current RUN runtime adapter driver",
            validate_run(plan, wrong_pi_driver),
        )

    def test_codex_worker_runtime_binding_rejects_non_host_source(self) -> None:
        # The guarded external-Codex-agent driver/source pair is gone: a
        # worker's runtime_binding.source is always exactly "host", so the
        # old external_agent axis-consistency contract no longer applies.
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
            }
        )
        run["runtime_capabilities"]["runtime_adapter"].update(
            {
                "provider": "codex",
                "available_drivers": ["app_threads", "sequential_parent"],
                "detection_source": "explicit",
            }
        )
        worker = {
            "worker_id": "W-M1-CODEX",
            "mission_id": "M1",
            "lease_id": "LEASE-M1-CODEX",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "batch_base_sha": "a" * 40,
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
            "task_thread_id": "thread-codex-1",
            "worktree_path": "C:/repo/worktrees/M1",
            "branch_ref": "refs/heads/codex/m1",
            "report_path": None,
            "phase": "leased",
            "worker_head_sha": None,
        }
        run["workers"].append(worker)
        authorize_recorded_worker(run, worker)
        self.assertEqual([], validate_run(plan, run))

        run["workers"][0]["runtime_binding"]["source"] = "external_agent"
        self.assertTrue(
            any(
                "runtime_binding.source: has an unsupported value" in error
                for error in validate_run(plan, run)
            )
        )

    def test_dependency_cycles_and_unbounded_route_cycles_are_rejected(self) -> None:
        dependency_cycle = valid_graph_plan()
        dependency_cycle["graph"]["edges"].append(
            {
                "id": "E-M2-M1",
                "kind": "dependency",
                "from": "N-M2",
                "to": "N-M1",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        self.assertTrue(any("dependency cycle" in error for error in validate_plan(dependency_cycle)))

        route_cycle = valid_graph_plan()
        route_cycle["graph"] = {
            "entry_nodes": ["N-M1"],
            "nodes": [
                route_cycle["graph"]["nodes"][0],
                graph_node(
                    "N-REVIEW",
                    "verifier",
                    "batch",
                    "local_command",
                    ["pass", "fix_required", "blocked"],
                ),
                graph_node(
                    "N-FIX",
                    "verifier",
                    "final",
                    "local_command",
                    ["pass", "blocked"],
                ),
                graph_node(
                    "N-END",
                    "mission",
                    "M2",
                    "runtime_worker",
                    ["pass", "blocked"],
                ),
            ],
            "edges": [
                {
                    "id": "E-START",
                    "kind": "dependency",
                    "from": "N-M1",
                    "to": "N-REVIEW",
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
                {
                    "id": "E-FIX",
                    "kind": "route",
                    "from": "N-REVIEW",
                    "to": "N-FIX",
                    "on_outcomes": ["fix_required"],
                    "max_traversals": None,
                },
                {
                    "id": "E-REVIEW",
                    "kind": "route",
                    "from": "N-FIX",
                    "to": "N-REVIEW",
                    "on_outcomes": ["pass"],
                    "max_traversals": 2,
                },
                {
                    "id": "E-EXIT",
                    "kind": "route",
                    "from": "N-REVIEW",
                    "to": "N-END",
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
            ],
        }
        errors = validate_plan(route_cycle)
        self.assertTrue(any("route cycles require an explicit traversal bound" in error for error in errors))

    def test_harness_parent_mission_is_deferred_without_write_isolation(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = valid_graph_run(plan)
        authorize_execution(run, ["M1"])

        run["observed"]["runtime"].update(
            {"available_worker_slots": 0, "isolation_capacity": 0}
        )

        result = select_ready_nodes(plan, run)

        self.assertEqual([], result["dispatchable_nodes"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("workspace_not_isolated", deferred["N-M1"])

    def test_execution_authorization_requires_review_coverage_per_write_scope(self) -> None:
        # contract-and-traceability.md requires every mission write scope to be
        # covered by a review-type node regardless of landing.mode. local_only
        # gets no GitHub review, so an uncovered scope means no review at all.
        # The gate is execution authorization, not plan structure: an upgraded
        # v3 projection stays a valid PLAN, it just cannot be executed until
        # the review nodes are authored.
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        authorize_execution(run, ["M1", "M2"])
        self.assertEqual(validate_run(plan, run), [])

        uncovered = valid_graph_plan()
        removed_node_ids = {"N-REVIEW-M2", "N-REVIEW-PASS-M2"}
        uncovered["graph"]["nodes"] = [
            node
            for node in uncovered["graph"]["nodes"]
            if node["id"] not in removed_node_ids
        ]
        uncovered["graph"]["edges"] = [
            edge
            for edge in uncovered["graph"]["edges"]
            if edge["from"] not in removed_node_ids and edge["to"] not in removed_node_ids
        ]
        uncovered_run = valid_graph_run(uncovered)
        authorize_execution(uncovered_run, ["M1", "M2"])
        errors = validate_run(uncovered, uncovered_run)
        self.assertTrue(
            any(
                "these missions have a write scope and no direct singleton pre-integration review node: M2"
                in error
                for error in errors
            ),
            f"expected an uncovered-M2 error in {errors!r}",
        )

        # An unauthorized run is still valid: the plan may legitimately be a
        # draft that has not authored its review nodes yet.
        draft = dict(uncovered_run)
        draft["execution_authorized"] = False
        draft["execution_authorization_source"] = None
        draft["execution_authorization_scope"] = None
        draft["status"] = "draft"
        self.assertEqual(
            [
                error
                for error in validate_run(uncovered, draft)
                if "no review node" in error
            ],
            [],
        )

    def test_shared_checkout_defers_all_plan_backed_parent_writers(self) -> None:
        plan = valid_graph_plan()
        detach_mission_edges(plan)
        plan["max_parallel_workers"] = 2
        for node in mission_nodes(plan):
            node["executor"] = "harness_parent"
            node["runtime"] = None
        run = valid_graph_run(plan)
        authorize_execution(run, ["M1", "M2"])
        run["runtime_capabilities"]["max_parallel_workers"] = 2
        run["observed"]["runtime"].update(
            {"available_worker_slots": 0, "isolation_capacity": 0}
        )

        result = select_ready_nodes(plan, run)

        self.assertEqual([], result["dispatchable_nodes"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("workspace_not_isolated", deferred["N-M1"])
        self.assertIn("workspace_not_isolated", deferred["N-M2"])

    def test_unauthorized_mission_does_not_consume_write_budget(self) -> None:
        plan = valid_graph_plan()
        detach_mission_edges(plan)
        run = valid_graph_run(plan)
        run.update(
            {
                "status": "running",
                "intent": "plan-then-execute",
                "plan_readiness": "ready",
                "execution_authorized": True,
                "execution_authorization_source": "user requested M2 execution",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "plan_revision": run["plan"]["revision"],
                    "plan_digest_sha256": run["plan"]["digest_sha256"],
                    "mission_ids": ["M2"],
                    "expires_when": "run_complete",
                },
            }
        )
        run["landing"]["continuity"] = {
            "status": "planned",
            "branch_ref": "refs/heads/codex/test",
            "head_sha": None,
            "reason": None,
        }
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "max_parallel_workers": 1,
            }
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "claude_code",
            "available_drivers": ["dynamic_workflow", "sequential_parent"],
            "detection_source": "observed",
            "version_gate": current_version_gate(),
        }
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, ["M2"], "*")

        result = select_ready_nodes(plan, run)

        self.assertEqual(["N-M2"], [item["node_id"] for item in result["dispatchable_nodes"]])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("execution_not_authorized", deferred["N-M1"])

    def test_codex_parent_cannot_bridge_a_claude_code_only_node(self) -> None:
        # A Codex parent has no mechanism to invoke Claude Code anymore: a
        # node whose allowed_providers is claude_code-only is simply
        # unavailable on a Codex host, with no fallback, regardless of how
        # much authorization is granted or how the adapter is observed.
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["runtime"] = {
            "preferred_provider": "claude_code",
            "allowed_providers": ["claude_code"],
            "provider_options": {
                "claude_code": {
                    "model": "opus",
                    "reasoning_effort": None,
                }
            },
        }
        run = valid_graph_run(plan)
        mission_ids = ["M1", "M2"]
        authorize_execution(run, mission_ids)
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "codex",
            "available_drivers": ["sequential_parent"],
            "detection_source": "observed",
            "capability_probe": codex_capability_probe(),
        }
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, mission_ids, "*")

        result = select_ready_nodes(plan, run)

        self.assertEqual(["N-M1"], result["ready_frontier"])
        self.assertEqual([], result["dispatchable_nodes"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("runtime_unavailable", deferred["N-M1"])
        self.assertNotIn("wave_launches", result)

        # Widening the host's own native driver set (still never claude_code)
        # or otherwise proving capacity never resurrects the node: there is
        # no cross-host preflight or probe path left to take.
        run["runtime_capabilities"]["runtime_adapter"]["available_drivers"] = [
            "sequential_parent"
        ]
        run["observed"]["runtime"]["available_worker_slots"] = 3
        still_unavailable = select_ready_nodes(plan, run)
        deferred = {
            item["node_id"]: item["reason_codes"]
            for item in still_unavailable["deferred_nodes"]
        }
        self.assertIn("runtime_unavailable", deferred["N-M1"])

    def test_claude_parent_cannot_bridge_codex_only_nodes_in_isolated_worktrees(
        self,
    ) -> None:
        plan = valid_graph_plan()
        detach_mission_edges(plan)
        plan["max_parallel_workers"] = 2
        for node in mission_nodes(plan):
            node["runtime"] = {
                "preferred_provider": "codex",
                "allowed_providers": ["codex"],
            }
        run = valid_graph_run(plan)
        mission_ids = ["M1", "M2"]
        authorize_execution(run, mission_ids)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "max_parallel_workers": 2,
            }
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "claude_code",
            "available_drivers": ["dynamic_workflow", "sequential_parent"],
            "detection_source": "observed",
            "version_gate": current_version_gate(),
        }
        run["observed"]["runtime"].update(
            {"available_worker_slots": 2, "isolation_capacity": 2}
        )
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, mission_ids, "*")

        unavailable = select_ready_nodes(plan, run)
        unavailable_reasons = {
            item["node_id"]: item["reason_codes"]
            for item in unavailable["deferred_nodes"]
        }
        self.assertEqual([], unavailable["dispatchable_nodes"])
        self.assertIn("runtime_unavailable", unavailable_reasons["N-M1"])
        self.assertIn("runtime_unavailable", unavailable_reasons["N-M2"])
        self.assertNotIn("wave_launches", unavailable)

        for node in mission_nodes(plan):
            node["runtime"]["allowed_providers"] = ["codex", "claude_code"]
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["active_wave"]["plan_digest_sha256"] = digest
        authorize_execution(run, mission_ids)
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, mission_ids, "*")

        native = select_ready_nodes(plan, run)
        self.assertEqual(
            ["run_dynamic_workflow", "run_dynamic_workflow"],
            [item["launch_kind"] for item in native["dispatchable_nodes"]],
        )
        self.assertTrue(
            all(
                item["runtime_provider"] == "claude_code"
                and item["runtime_source"] == "host"
                for item in native["dispatchable_nodes"]
            )
        )


    def test_codex_only_review_defers_on_a_claude_code_host(self) -> None:
        plan = valid_graph_plan()
        review = graph_node(
            "N-BACKEND-REVIEW",
            "verifier",
            "batch",
            "runtime_worker",
            ["pass", "fix_required", "retryable_failure", "blocked", "contract_gap"],
            providers=["codex"],
            preferred="codex",
        )
        review["review"] = {
            "type": "backend_code",
            "lineage_id": "REVIEW-CODEX-ONLY",
            "mission_ids": ["M1"],
            "scope": ["src/a/**"],
            "required_evidence": ["reviewed_sha", "findings"],
        }
        attach_single_mission_review(plan, review)
        plan["required_reviews"] = ["backend_code"]
        run = valid_graph_run(plan)
        run.update(
            {
                "status": "running",
                "intent": "plan-then-execute",
                "plan_readiness": "ready",
                "execution_authorized": True,
                "execution_authorization_source": "user requested review",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "plan_revision": run["plan"]["revision"],
                    "plan_digest_sha256": run["plan"]["digest_sha256"],
                    "mission_ids": ["M1"],
                    "expires_when": "run_complete",
                },
            }
        )
        run["landing"]["continuity"] = {
            "status": "planned",
            "branch_ref": "refs/heads/codex/test",
            "head_sha": None,
            "reason": None,
        }
        run["graph_state"]["node_states"]["N-M2"].update(
            {
                "phase": "blocked",
                "attempts": 1,
                "last_attempt_id": "A-M2",
                "last_outcome": "blocked",
                "blockers": ["not selected"],
            }
        )
        run["mission_states"]["M2"]["phase"] = "blocked"
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
            }
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "claude_code",
            "available_drivers": ["dynamic_workflow", "sequential_parent"],
            "detection_source": "observed",
            "version_gate": current_version_gate(),
        }
        record_worker_passed_mission_with_review(
            plan,
            run,
            "M1",
            provider="claude_code",
            driver="dynamic_workflow",
        )
        authorize(run, "spawn_subagents", ["M1"], "worker:preallocation")

        result = select_ready_nodes(plan, run)

        self.assertNotIn(
            "N-BACKEND-REVIEW",
            [item["node_id"] for item in result["dispatchable_nodes"]],
        )
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("runtime_unavailable", deferred["N-BACKEND-REVIEW"])
        self.assertNotIn("wave_launches", result)

    def test_runtime_reviews_require_authorization_and_share_runtime_capacity(self) -> None:
        plan = valid_graph_plan()
        reviews = []
        for node_id, ref, review_type in (
            ("N-FRONTEND-REVIEW", "batch", "frontend_code"),
            ("N-VISUAL-REVIEW", "final", "visual"),
        ):
            node = graph_node(
                node_id,
                "verifier",
                ref,
                "runtime_worker",
                ["pass", "fix_required", "blocked", "contract_gap"],
                providers=["claude_code"],
                preferred="claude_code",
                provider_options={
                    "claude_code": {
                        "model": "claude-fable-5",
                        "reasoning_effort": "xhigh" if review_type == "frontend_code" else "high",
                    }
                },
            )
            node["review"] = {
                "type": review_type,
                "lineage_id": f"REVIEW-{node['id']}",
                "mission_ids": ["M1"],
                "scope": ["src/a/**"],
                "required_evidence": ["reviewed_sha", "findings"],
            }
            reviews.append(node)
        for review in reviews:
            attach_single_mission_review(plan, review)
        plan["required_reviews"] = ["frontend_code", "visual"]
        run = valid_graph_run(plan)
        authorize_execution(run, ["M1", "M2"])
        run["graph_state"]["node_states"]["N-M2"].update(
            {
                "phase": "blocked",
                "attempts": 1,
                "last_attempt_id": "A-M2",
                "last_outcome": "blocked",
                "blockers": ["not in this review wave"],
            }
        )
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["mission_states"]["M2"]["phase"] = "blocked"
        run["integration"]["integration_head_sha"] = "a" * 40
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
            }
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "claude_code",
            "available_drivers": ["dynamic_workflow", "sequential_parent"],
            "detection_source": "observed",
            "version_gate": current_version_gate(),
        }
        record_worker_passed_mission_with_review(
            plan,
            run,
            "M1",
            provider="claude_code",
            driver="dynamic_workflow",
        )

        unauthorized = select_ready_nodes(plan, run)
        review_deferred = {
            item["node_id"]: item["reason_codes"] for item in unauthorized["deferred_nodes"]
        }
        self.assertIn("action_not_authorized", review_deferred["N-FRONTEND-REVIEW"])
        self.assertIn("action_not_authorized", review_deferred["N-VISUAL-REVIEW"])

        authorize(run, "spawn_subagents", ["M1"], "*")
        selected = select_ready_nodes(plan, run)
        runtime_reviews = [
            item
            for item in selected["dispatchable_nodes"]
            if item["node_id"] in {"N-FRONTEND-REVIEW", "N-VISUAL-REVIEW"}
        ]
        self.assertEqual(1, len(runtime_reviews))
        selected_review = runtime_reviews[0]
        self.assertEqual("N-FRONTEND-REVIEW", selected_review["node_id"])
        self.assertEqual(
            "claude-fable-5",
            selected_review["runtime_binding"]["model"],
        )
        self.assertEqual(
            "xhigh",
            selected_review["runtime_binding"]["reasoning_effort"],
        )
        self.assertEqual(
            "host",
            selected_review["runtime_binding"]["source"],
        )
        self.assertEqual(
            ["spawn_subagents"],
            selected_review["required_actions"],
        )
        self.assertEqual(
            "code_review_readonly",
            selected_review["tool_profile"],
        )
        review_deferred = {
            item["node_id"]: item["reason_codes"] for item in selected["deferred_nodes"]
        }
        self.assertEqual(["over_runtime_budget"], review_deferred["N-VISUAL-REVIEW"])

    def test_review_worker_and_result_are_bound_to_exact_reviewed_sha(self) -> None:
        plan = valid_graph_plan()
        review = graph_node(
            "N-FRONTEND-REVIEW",
            "verifier",
            "batch",
            "runtime_worker",
            ["pass", "fix_required", "blocked", "contract_gap"],
            providers=["claude_code"],
            preferred="claude_code",
            provider_options={
                "claude_code": {"model": "claude-fable-5", "reasoning_effort": "xhigh"}
            },
        )
        review["review"] = {
            "type": "frontend_code",
            "lineage_id": "REVIEW-EXACT-SHA",
            "mission_ids": ["M1"],
            "scope": ["src/a/**"],
            "required_evidence": ["reviewed_sha", "findings"],
        }
        attach_single_mission_review(plan, review)
        plan["required_reviews"] = ["frontend_code"]
        run = valid_graph_run(plan)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
            }
        )
        run["runtime_capabilities"]["runtime_adapter"].update(
            {
                "provider": "claude_code",
                "available_drivers": ["dynamic_workflow", "sequential_parent"],
                "detection_source": "observed",
            }
        )
        run["integration"]["integration_head_sha"] = "a" * 40
        run["graph_state"]["node_states"][review["id"]].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-1",
                "bound_worker_id": "RW-1",
            }
        )
        run["review_workers"] = [
            {
                "worker_id": "RW-1",
                "node_id": review["id"],
                "attempt_id": "ATT-REVIEW-1",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "graph_revision": run["graph_state"]["graph_revision"],
                "reviewed_sha": "a" * 40,
                "review_path": "C:/repo/review",
                "worker_runtime": "subagent",
                "completion_channel": "agent_result",
                "runtime_binding": {
                    "provider": "claude_code",
                    "driver": "dynamic_workflow",
                    "source": "host",
                    "model": "claude-fable-5",
                    "reasoning_effort": "xhigh",
                    "option_source": "plan_provider_options",
                },
                "task_thread_id": None,
                "report_path": None,
                "phase": "worker_running",
                "outcome": None,
                "findings": [],
            }
        ]
        self.assertEqual([], validate_run(plan, run))

        pi_host_mismatch = copy.deepcopy(run)
        pi_host_mismatch["runtime_capabilities"]["runtime_adapter"].update(
            {
                "provider": "pi",
                "available_drivers": ["subagents", "sequential_parent"],
            }
        )
        errors = validate_run(plan, pi_host_mismatch)
        self.assertIn(
            "run.review_workers[0].runtime_binding.provider: must match the current RUN runtime adapter provider",
            errors,
        )
        self.assertIn(
            "run.review_workers[0].runtime_binding.driver: must match the current RUN runtime adapter driver",
            errors,
        )

        historical_claude_review = copy.deepcopy(pi_host_mismatch)
        historical_claude_review["graph_state"]["node_states"][review["id"]].update(
            {"phase": "succeeded", "last_outcome": "pass"}
        )
        historical_claude_review["review_workers"][0].update(
            {"phase": "worker_passed", "outcome": "pass"}
        )
        self.assertEqual([], validate_run(plan, historical_claude_review))

        run["mission_states"]["M1"]["head_sha"] = "b" * 40
        run["review_workers"][0]["reviewed_sha"] = "b" * 40
        self.assertEqual([], validate_run(plan, run))
        malformed_reviews = copy.deepcopy(run)
        malformed_reviews["review_workers"] = None
        self.assertTrue(
            any(
                "run.review_workers: must be a list" in error
                for error in validate_run(plan, malformed_reviews)
            )
        )
        run["mission_states"]["M2"]["head_sha"] = "c" * 40
        run["review_workers"][0]["reviewed_sha"] = "c" * 40
        self.assertTrue(
            any(
                "must identify the direct singleton pre-integration worktree"
                in error
                for error in validate_run(plan, run)
            )
        )
        run["mission_states"]["M2"]["head_sha"] = None
        run["mission_states"]["M1"]["head_sha"] = None
        run["review_workers"][0]["reviewed_sha"] = "a" * 40
        run["status"] = "complete"
        self.assertTrue(
            any(
                "cannot retain active or blocked review workers" in error
                for error in validate_run(plan, run)
            )
        )
        run["status"] = "draft"
        result = {
            "run_id": run["run_id"],
            "node_id": review["id"],
            "attempt_id": "ATT-REVIEW-1",
            "plan_id": plan["plan_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "graph_revision": run["graph_state"]["graph_revision"],
            "batch_base_sha": run["integration"]["batch_base_sha"],
            "status": "succeeded",
            "outcome": "pass",
            "worker_result": {
                "reviewed_sha": "a" * 40,
                "findings": [],
                "evidence_summary": "No blocking frontend findings.",
            },
            "refinement_request": None,
            "evidence_paths": ["review.json"],
        }
        self.assertEqual([], validate_node_result(plan, run, result))
        result["worker_result"]["reviewed_sha"] = "b" * 40
        self.assertTrue(
            any("does not match the review worker" in error for error in validate_node_result(plan, run, result))
        )

    def _frontend_review_node(self) -> dict[str, object]:
        review = graph_node(
            "N-FRONTEND-REVIEW",
            "verifier",
            "batch",
            "runtime_worker",
            ["pass", "fix_required", "blocked", "contract_gap"],
            providers=["claude_code"],
            preferred="claude_code",
            provider_options={
                "claude_code": {"model": "claude-fable-5", "reasoning_effort": "xhigh"}
            },
        )
        review["review"] = {
            "type": "frontend_code",
            "lineage_id": "REVIEW-INDEPENDENT",
            "mission_ids": ["M1"],
            "scope": ["src/a/**"],
            "required_evidence": ["reviewed_sha", "findings"],
        }
        return review

    def _review_worker_runtime_binding(self) -> dict[str, object]:
        return {
            "provider": "claude_code",
            "driver": "dynamic_workflow",
            "source": "host",
            "model": "claude-fable-5",
            "reasoning_effort": "xhigh",
            "option_source": "plan_provider_options",
        }

    def test_review_worker_outcome_and_findings_are_validated_per_reviewer(self) -> None:
        plan = valid_graph_plan()
        review = self._frontend_review_node()
        attach_single_mission_review(plan, review)
        plan["required_reviews"] = ["frontend_code"]
        run = valid_graph_run(plan)
        run["integration"]["integration_head_sha"] = "a" * 40
        run["graph_state"]["node_states"][review["id"]].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-1",
                "last_outcome": "pass",
                "bound_worker_id": "RW-1",
            }
        )
        base_worker = {
            "worker_id": "RW-1",
            "node_id": review["id"],
            "attempt_id": "ATT-REVIEW-1",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "graph_revision": run["graph_state"]["graph_revision"],
            "reviewed_sha": "a" * 40,
            "review_path": "C:/repo/review",
            "worker_runtime": "subagent",
            "completion_channel": "agent_result",
            "runtime_binding": self._review_worker_runtime_binding(),
            "task_thread_id": None,
            "report_path": None,
            "phase": "worker_passed",
            "outcome": "pass",
            "findings": [],
        }

        run["review_workers"] = [copy.deepcopy(base_worker)]
        self.assertEqual([], validate_run(plan, run))

        bad_outcome = copy.deepcopy(run)
        bad_outcome["review_workers"][0]["outcome"] = "not_a_declared_outcome"
        self.assertTrue(
            any(
                "is not declared by the reviewed node" in error
                for error in validate_run(plan, bad_outcome)
            )
        )

        missing_findings = copy.deepcopy(run)
        missing_findings["review_workers"][0]["outcome"] = "fix_required"
        self.assertTrue(
            any(
                "is required when outcome is not pass" in error
                for error in validate_run(plan, missing_findings)
            )
        )

        with_findings = copy.deepcopy(run)
        with_findings["review_workers"][0]["outcome"] = "fix_required"
        with_findings["review_workers"][0]["findings"] = ["missing null check on line 42"]
        self.assertEqual([], validate_run(plan, with_findings))

        current_pass_with_findings = copy.deepcopy(run)
        current_pass_with_findings["review_workers"][0]["findings"] = [
            "informational note without a severity field"
        ]
        self.assertTrue(
            any(
                "current PASS review result must not contain findings" in error
                for error in validate_run(plan, current_pass_with_findings)
            )
        )

    def test_multiple_reviewers_on_same_node_keep_independent_outcomes(self) -> None:
        plan = valid_graph_plan()
        review = self._frontend_review_node()
        attach_single_mission_review(plan, review)
        plan["required_reviews"] = ["frontend_code"]
        run = valid_graph_run(plan)
        run["integration"]["integration_head_sha"] = "a" * 40
        run["graph_state"]["node_states"][review["id"]].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-1",
                "last_outcome": "pass",
                "bound_worker_id": "RW-1",
            }
        )
        passing_reviewer = {
            "worker_id": "RW-1",
            "node_id": review["id"],
            "attempt_id": "ATT-REVIEW-1",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "graph_revision": run["graph_state"]["graph_revision"],
            "reviewed_sha": "a" * 40,
            "review_path": "C:/repo/review-1",
            "worker_runtime": "subagent",
            "completion_channel": "agent_result",
            "runtime_binding": self._review_worker_runtime_binding(),
            "task_thread_id": None,
            "report_path": None,
            "phase": "worker_passed",
            "outcome": "pass",
            "findings": [],
        }
        dissenting_reviewer = {
            "worker_id": "RW-2",
            "node_id": review["id"],
            "attempt_id": "ATT-REVIEW-2",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "graph_revision": run["graph_state"]["graph_revision"],
            "reviewed_sha": "a" * 40,
            "review_path": "C:/repo/review-2",
            "worker_runtime": "subagent",
            "completion_channel": "agent_result",
            "runtime_binding": self._review_worker_runtime_binding(),
            "task_thread_id": None,
            "report_path": None,
            "phase": "superseded",
            "outcome": "fix_required",
            "findings": ["missing null check on line 42"],
        }
        run["review_workers"] = [passing_reviewer, dissenting_reviewer]

        # A superseded dissent remains historical evidence and does not block
        # the current passing attempt.
        self.assertEqual([], validate_run(plan, run))
        self.assertEqual(
            "pass", run["graph_state"]["node_states"][review["id"]]["last_outcome"]
        )
        self.assertEqual("pass", run["review_workers"][0]["outcome"])
        self.assertEqual("fix_required", run["review_workers"][1]["outcome"])

    def test_node_result_is_bound_to_the_active_graph_attempt(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        start_mission(run, plan, digest, base_sha="a" * 40)
        result = {
            "run_id": run["run_id"],
            "node_id": "N-M1",
            "attempt_id": "ATT-N-M1-1",
            "plan_id": plan["plan_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "graph_revision": run["graph_state"]["graph_revision"],
            "batch_base_sha": run["integration"]["batch_base_sha"],
            "status": "succeeded",
            "outcome": "pass",
            "worker_result": {"status": "PASS"},
            "refinement_request": None,
            "evidence_paths": ["worker-result.json"],
        }

        self.assertEqual([], validate_node_result(plan, run, result))
        malformed = copy.deepcopy(result)
        malformed["node_id"] = []
        self.assertTrue(
            any("must be a non-empty string" in error for error in validate_node_result(plan, run, malformed))
        )
        malformed = copy.deepcopy(result)
        malformed["status"] = []
        self.assertTrue(
            any("unsupported value" in error for error in validate_node_result(plan, run, malformed))
        )
        result["attempt_id"] = "ATT-STALE"
        self.assertTrue(
            any("active attempt" in error for error in validate_node_result(plan, run, result))
        )
        result["attempt_id"] = "ATT-N-M1-1"
        result["run_id"] = "RUN-STALE"
        self.assertTrue(
            any("does not match RUN" in error for error in validate_node_result(plan, run, result))
        )
        result["run_id"] = run["run_id"]
        result["batch_base_sha"] = "b" * 40
        self.assertTrue(
            any("batch_base_sha" in error for error in validate_node_result(plan, run, result))
        )

    def test_native_claude_code_nodes_carry_their_own_plan_selected_model(self) -> None:
        # Wave grouping (by model/effort/tool profile) is no longer a
        # graph-selector concern: select_ready_nodes never returns a
        # "wave_launches" key, and grouping same-host Dynamic Workflow
        # launches now belongs entirely to the Claude Code adapter. Each
        # dispatchable node still carries its own exact PLAN-selected
        # runtime_binding so the adapter can group them itself.
        plan = valid_graph_plan()
        detach_mission_edges(plan)
        for node, model in zip(mission_nodes(plan), ("sonnet", "opus"), strict=True):
            node["runtime"] = {
                "preferred_provider": "claude_code",
                "allowed_providers": ["claude_code"],
                "provider_options": {
                    "claude_code": {
                        "model": model,
                        "reasoning_effort": None,
                    }
                },
            }
        run = valid_graph_run(plan)
        mission_ids = ["M1", "M2"]
        authorize_execution(run, mission_ids)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "max_parallel_workers": 2,
            }
        )
        run["observed"]["runtime"].update(
            {"available_worker_slots": 2, "isolation_capacity": 2}
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "claude_code",
            "available_drivers": ["dynamic_workflow", "sequential_parent"],
            "detection_source": "observed",
            "version_gate": current_version_gate(),
        }
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, mission_ids, "*")

        result = select_ready_nodes(plan, run)

        self.assertNotIn("wave_launches", result)
        self.assertEqual(
            ["N-M1", "N-M2"],
            [item["node_id"] for item in result["dispatchable_nodes"]],
        )
        self.assertEqual(
            ["sonnet", "opus"],
            [item["runtime_binding"]["model"] for item in result["dispatchable_nodes"]],
        )
        self.assertTrue(
            all(
                item["launch_kind"] == "run_dynamic_workflow"
                and item["runtime_provider"] == "claude_code"
                and item["runtime_source"] == "host"
                for item in result["dispatchable_nodes"]
            )
        )








    def test_approval_node_does_not_require_a_reconciled_parent(self) -> None:
        # Contrast with the lifecycle case above: an approval gate does not
        # mutate parent git state, so an unreconciled parent must not defer
        # it the way it defers a mission or lifecycle node.
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        plan["graph"]["nodes"].append(
            graph_node("N-APPROVAL", "approval", "final-signoff", "human", ["pass", "blocked"])
        )
        plan["graph"]["entry_nodes"].append("N-APPROVAL")
        run["plan"]["digest_sha256"] = plan_digest(plan)
        run["graph_state"]["node_states"]["N-APPROVAL"] = {
            "phase": "dormant",
            "attempts": 0,
            "last_attempt_id": None,
            "last_outcome": None,
            "bound_worker_id": None,
            "blockers": [],
        }
        authorize_execution(run, ["*"], status="ready")
        run["integration"]["batch_base_sha"] = None
        run["observed"]["git"]["parent_dirty"] = None

        result = select_ready_nodes(plan, run)

        dispatchable = {item["node_id"] for item in result["dispatchable_nodes"]}
        self.assertIn("N-APPROVAL", dispatchable)

    def test_runtime_unavailable_does_not_mask_other_deferral_reasons(self) -> None:
        # Previously a missing binding returned early, so an agent that fixed
        # runtime_unavailable would then discover batch_base_missing on the
        # next run instead of seeing both at once.
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["runtime"]["allowed_providers"] = ["codex"]
        run = valid_graph_run(plan)
        authorize_execution(run, ["M1", "M2"])
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "claude_code",
            "available_drivers": ["sequential_parent"],
            "detection_source": "observed",
        }
        run["integration"]["batch_base_sha"] = None

        result = select_ready_nodes(plan, run)

        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("runtime_unavailable", deferred["N-M1"])
        self.assertIn("batch_base_missing", deferred["N-M1"])


if __name__ == "__main__":
    unittest.main()

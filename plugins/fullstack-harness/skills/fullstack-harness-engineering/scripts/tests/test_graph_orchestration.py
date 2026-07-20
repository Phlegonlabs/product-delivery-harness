#!/usr/bin/env python3
"""Typed graph and external Claude runtime tests."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import claude_runtime_bridge as bridge  # noqa: E402
from harness_manifest import (  # noqa: E402
    AUTHORIZATION_KEYS_V8,
    plan_digest,
    topological_levels,
    validate_plan,
    validate_run,
)
from select_ready_nodes import (  # noqa: E402
    _external_wave_launches,
    _runtime_binding,
    select_ready_nodes,
)
from test_harness_manifest import markdown, mark_complete, valid_plan, valid_run  # noqa: E402
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


def valid_graph_plan() -> dict[str, object]:
    plan = valid_plan()
    plan["schema_version"] = 4
    plan["required_reviews"] = []
    for source in plan["sources"]:
        source.update({"content_sha256": "f" * 64, "source_revision": None})
    for item in plan["missions"]:
        item.pop("depends_on")
    plan["graph"] = {
        "entry_nodes": ["N-M1"],
        "nodes": [
            graph_node(
                "N-M1",
                "mission",
                "M1",
                "runtime_worker",
                ["pass", "retryable_failure", "blocked", "contract_gap"],
            ),
            graph_node(
                "N-M2",
                "mission",
                "M2",
                "runtime_worker",
                ["pass", "retryable_failure", "blocked", "contract_gap"],
            ),
        ],
        "edges": [
            {
                "id": "E-M1-M2",
                "kind": "dependency",
                "from": "N-M1",
                "to": "N-M2",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        ],
    }
    return plan


def valid_graph_run(plan: dict[str, object]) -> dict[str, object]:
    run = valid_run(plan)
    run["schema_version"] = 8
    run["authorizations"] = {
        key: {"authorized": False, "source": None} for key in AUTHORIZATION_KEYS_V8
    }
    run["runtime_capabilities"]["runtime_adapter"]["external_runtimes"] = []
    run["review_workers"] = []
    run["graph_state"] = {
        "graph_revision": plan["revision"],
        "node_states": {
            node["id"]: {
                "phase": "dormant",
                "attempts": 0,
                "last_attempt_id": None,
                "last_outcome": None,
                "bound_worker_id": None,
                "blockers": [],
            }
            for node in plan["graph"]["nodes"]
        },
        "edge_states": {
            edge["id"]: {
                "status": "dormant",
                "traversals": 0,
                "source_attempt_id": None,
            }
            for edge in plan["graph"]["edges"]
        },
    }
    return run


def authorize(
    run: dict[str, object], action: str, mission_ids: list[str], target: str
) -> None:
    run["authorizations"][action] = {
        "authorized": True,
        "source": "user requested graph execution and Claude trial",
        "scope": {
            "run_id": run["run_id"],
            "mission_ids": mission_ids,
            "targets": [target],
        },
        "expires_when": "run_complete",
    }


class GraphManifestTests(unittest.TestCase):
    def test_schema_v4_and_v8_are_valid_and_keep_mission_topology(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)

        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_run(plan, run))
        self.assertEqual({"M1": 0, "M2": 1}, topological_levels(plan))

    def test_workflow_run_binding_is_optional_and_validated(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        run["graph_state"]["node_states"]["N-M1"].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": "ATT-N-M1-1",
                "bound_worker_id": "W-M1",
            }
        )
        run["mission_states"]["M1"].update(
            {
                "phase": "worker_running",
                "lease_id": "LEASE-M1-1",
                "lease_plan_revision": plan["revision"],
                "lease_plan_digest_sha256": digest,
                "worker_id": "W-M1",
                "base_sha": run["integration"]["batch_base_sha"],
            }
        )
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
                "model": "sonnet",
                "reasoning_effort": None,
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

    def test_external_codex_workflow_run_binds_provider_options_and_attempt(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["runtime"] = {
            "preferred_provider": "codex",
            "allowed_providers": ["codex"],
        }
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        run["graph_state"]["node_states"]["N-M1"].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": "ATT-N-M1-CODEX-1",
                "bound_worker_id": "W-M1-CODEX",
            }
        )
        run["mission_states"]["M1"].update(
            {
                "phase": "worker_running",
                "lease_id": "LEASE-M1-CODEX-1",
                "lease_plan_revision": plan["revision"],
                "lease_plan_digest_sha256": digest,
                "worker_id": "W-M1-CODEX",
                "base_sha": run["integration"]["batch_base_sha"],
            }
        )
        run["runtime_capabilities"]["runtime_adapter"]["external_runtimes"] = [
            {
                "provider": "codex",
                "driver": "codex_rescue_agent",
                "status": "available",
                "command": "agent:codex:codex-rescue",
                "version": "1.0.4",
                "contract_version": "harness-node-result-v1",
                "completion_channel": "agent_result",
                "evidence": ["foreground preflight passed"],
            }
        ]
        workflow = {
            "workflow_run_id": "wf_codex_test",
            "workflow_task_id": "task-codex-test",
            "resume_from_run_id": None,
            "script_path": "assets/templates/CLAUDE_CODEX_GRAPH_WORKFLOW.template.js",
            "script_sha256": "d" * 64,
            "run_id": run["run_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "graph_revision": run["graph_state"]["graph_revision"],
            "batch_base_sha": run["integration"]["batch_base_sha"],
            "node_ids": ["N-M1"],
            "attempt_ids": {"N-M1": "ATT-N-M1-CODEX-1"},
            "provider": "codex",
            "driver": "external_codex_agent",
            "model": None,
            "reasoning_effort": None,
            "tool_profile": "mission_write",
            "status": "running",
            "result_evidence": [],
            "metrics": {"duration_ms": None, "token_count": None},
        }
        run["workflow_runs"] = [workflow]

        self.assertEqual([], validate_run(plan, run))

        workflow["driver"] = "external_dynamic_workflow"
        self.assertTrue(
            any("does not match the workflow provider" in error for error in validate_run(plan, run))
        )
        workflow["driver"] = "external_codex_agent"
        workflow["model"] = "gpt-5.6-terra"
        self.assertTrue(
            any("does not match node N-M1" in error for error in validate_run(plan, run))
        )
        workflow["model"] = None
        workflow["attempt_ids"]["N-M1"] = "ATT-STALE"
        self.assertTrue(
            any("active running node attempt" in error for error in validate_run(plan, run))
        )

        explicit_plan = valid_graph_plan()
        explicit_plan["graph"]["nodes"][0]["runtime"] = {
            "preferred_provider": "codex",
            "allowed_providers": ["codex"],
            "provider_options": {
                "codex": {
                    "model": "gpt-5.6-terra",
                    "reasoning_effort": "xhigh",
                }
            },
        }
        explicit_run = valid_graph_run(explicit_plan)
        explicit_digest = plan_digest(explicit_plan)
        explicit_run["graph_state"]["node_states"]["N-M1"].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": "ATT-N-M1-CODEX-2",
                "bound_worker_id": "W-M1-CODEX-2",
            }
        )
        explicit_run["mission_states"]["M1"].update(
            {
                "phase": "worker_running",
                "lease_id": "LEASE-M1-CODEX-2",
                "lease_plan_revision": explicit_plan["revision"],
                "lease_plan_digest_sha256": explicit_digest,
                "worker_id": "W-M1-CODEX-2",
                "base_sha": explicit_run["integration"]["batch_base_sha"],
            }
        )
        explicit_workflow = copy.deepcopy(workflow)
        explicit_workflow.update(
            {
                "workflow_run_id": "wf_codex_explicit",
                "workflow_task_id": "task-codex-explicit",
                "run_id": explicit_run["run_id"],
                "plan_revision": explicit_plan["revision"],
                "plan_digest_sha256": explicit_digest,
                "graph_revision": explicit_run["graph_state"]["graph_revision"],
                "batch_base_sha": explicit_run["integration"]["batch_base_sha"],
                "attempt_ids": {"N-M1": "ATT-N-M1-CODEX-2"},
                "model": "gpt-5.6-terra",
                "reasoning_effort": "xhigh",
            }
        )
        explicit_run["workflow_runs"] = [explicit_workflow]
        self.assertEqual([], validate_run(explicit_plan, explicit_run))

    def test_schema_v4_and_v9_closeout_preserves_graph_state(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"].append(
            graph_node(
                "N-FINAL",
                "verifier",
                "final",
                "local_command",
                ["pass", "retryable_failure"],
            )
        )
        plan["graph"]["edges"].append(
            {
                "id": "E-M2-FINAL",
                "kind": "dependency",
                "from": "N-M2",
                "to": "N-FINAL",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        run = valid_graph_run(plan)
        run["schema_version"] = 9
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
        run["landing"]["mode"] = "local_only"
        mark_complete(plan, run)
        errors = validate_run(plan, run)
        self.assertTrue(
            any("every node to succeed, skip, or be superseded" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("every edge to be terminal" in error for error in errors),
            errors,
        )
        for index, node in enumerate(plan["graph"]["nodes"], start=1):
            run["graph_state"]["node_states"][node["id"]].update(
                {
                    "phase": "succeeded",
                    "attempts": 1,
                    "last_attempt_id": f"ATTEMPT-{index}",
                    "last_outcome": "pass",
                }
            )
        attempt_by_node = {
            node["id"]: f"ATTEMPT-{index}"
            for index, node in enumerate(plan["graph"]["nodes"], start=1)
        }
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
        plan = valid_graph_plan()
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
                "task_thread_id": None,
                "worktree_path": None,
                "branch_ref": None,
                "report_path": None,
                "phase": "leased",
                "worker_head_sha": None,
            }
        )

        self.assertEqual([], validate_run(plan, run))
        run["workers"][0]["runtime_binding"]["reasoning_effort"] = "high"
        self.assertTrue(
            any("must match the matching PLAN provider option" in error for error in validate_run(plan, run))
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

    def test_harness_parent_mission_emits_parent_directive(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = valid_graph_run(plan)
        run.update(
            {
                "status": "running",
                "intent": "plan-then-execute",
                "plan_readiness": "ready",
                "execution_authorized": True,
                "execution_authorization_source": "user requested execution",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "mission_ids": ["M1"],
                    "expires_when": "run_complete",
                },
            }
        )

        run["observed"]["runtime"].update(
            {"available_worker_slots": 0, "isolation_capacity": 0}
        )

        result = select_ready_nodes(plan, run)

        self.assertEqual("run_parent", result["dispatchable_nodes"][0]["launch_kind"])
        self.assertEqual("parent", result["dispatchable_nodes"][0]["worker_runtime"])

    def test_shared_checkout_caps_parent_writers_at_one(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["entry_nodes"] = ["N-M1", "N-M2"]
        plan["graph"]["edges"] = []
        plan["max_parallel_workers"] = 2
        for node in plan["graph"]["nodes"]:
            node["executor"] = "harness_parent"
            node["runtime"] = None
        run = valid_graph_run(plan)
        run.update(
            {
                "status": "running",
                "intent": "plan-then-execute",
                "plan_readiness": "ready",
                "execution_authorized": True,
                "execution_authorization_source": "user requested execution",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "mission_ids": ["M1", "M2"],
                    "expires_when": "run_complete",
                },
            }
        )
        run["runtime_capabilities"]["max_parallel_workers"] = 2
        run["observed"]["runtime"].update(
            {"available_worker_slots": 0, "isolation_capacity": 0}
        )

        result = select_ready_nodes(plan, run)

        self.assertEqual(["N-M1"], [item["node_id"] for item in result["dispatchable_nodes"]])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("write_conflict", deferred["N-M2"])
        self.assertIn("workspace_not_isolated", result["conflict_edges"][0]["reason_codes"])

    def test_unauthorized_mission_does_not_consume_write_budget(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["entry_nodes"] = ["N-M1", "N-M2"]
        plan["graph"]["edges"] = []
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
                    "mission_ids": ["M2"],
                    "expires_when": "run_complete",
                },
            }
        )
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
            "external_runtimes": [],
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

    def test_codex_parent_selects_external_claude_graph_wave(self) -> None:
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
        run.update(
            {
                "status": "running",
                "intent": "plan-then-execute",
                "plan_readiness": "ready",
                "execution_authorized": True,
                "execution_authorization_source": "user requested execution",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "mission_ids": mission_ids,
                    "expires_when": "run_complete",
                },
            }
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "codex",
            "available_drivers": ["sequential_parent"],
            "detection_source": "observed",
            "external_runtimes": [
                {
                    "provider": "claude_code",
                    "driver": "dynamic_workflow",
                    "status": "available",
                    "command": "claude",
                    "version": "2.1.214",
                    "completion_channel": "agent_result",
                    "evidence": ["protocol-v1 preflight passed"],
                }
            ],
        }
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, mission_ids, "*")
        authorize(run, "invoke_external_runtime", mission_ids, "runtime:claude_code")

        result = select_ready_nodes(plan, run)

        self.assertEqual(["N-M1"], result["ready_frontier"])
        self.assertEqual("run_external_dynamic_workflow", result["dispatchable_nodes"][0]["launch_kind"])
        self.assertEqual("claude_code", result["dispatchable_nodes"][0]["runtime_provider"])
        self.assertEqual("mission_write", result["dispatchable_nodes"][0]["tool_profile"])
        self.assertEqual("retryable_failure", result["dispatchable_nodes"][0]["failure_outcome"])
        self.assertEqual("opus", result["dispatchable_nodes"][0]["runtime_binding"]["model"])
        self.assertEqual("opus", result["wave_launches"][0]["model"])
        self.assertEqual(["N-M1"], result["wave_launches"][0]["node_ids"])
        self.assertEqual("mission_write", result["wave_launches"][0]["tool_profile"])

        run["observed"]["runtime"]["completion_channel_available"] = False
        blocked = select_ready_nodes(plan, run)
        self.assertIn(
            "completion_channel_unavailable",
            {item["node_id"]: item["reason_codes"] for item in blocked["deferred_nodes"]}["N-M1"],
        )
        run["observed"]["runtime"]["completion_channel_available"] = True
        run["runtime_capabilities"]["permission_boundary"] = {
            "selected_mode": "unknown",
            "profile_name": None,
            "approval_policy": "unknown",
            "filesystem_scope": "unknown",
            "network_scope": "unknown",
            "local_binding": "unknown",
            "worker_inheritance": "unknown",
            "status": "blocked",
        }
        blocked = select_ready_nodes(plan, run)
        self.assertIn(
            "permission_boundary_not_ready",
            {item["node_id"]: item["reason_codes"] for item in blocked["deferred_nodes"]}["N-M1"],
        )
        del run["runtime_capabilities"]["permission_boundary"]
        plan["missions"][0]["resource_inventory_complete"] = False
        run["plan"]["digest_sha256"] = plan_digest(plan)
        blocked = select_ready_nodes(plan, run)
        self.assertIn(
            "incomplete_resource_inventory",
            {item["node_id"]: item["reason_codes"] for item in blocked["deferred_nodes"]}["N-M1"],
        )
        plan["missions"][0]["resource_inventory_complete"] = True
        run["plan"]["digest_sha256"] = plan_digest(plan)
        run["observed"]["git"]["parent_dirty"] = True
        blocked = select_ready_nodes(plan, run)
        self.assertIn(
            "blocker_present",
            {item["node_id"]: item["reason_codes"] for item in blocked["deferred_nodes"]}["N-M1"],
        )

    def test_claude_parent_selects_external_codex_agents_in_isolated_worktrees(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["entry_nodes"] = ["N-M1", "N-M2"]
        plan["graph"]["edges"] = []
        plan["max_parallel_workers"] = 2
        for node in plan["graph"]["nodes"]:
            node["runtime"] = {
                "preferred_provider": "codex",
                "allowed_providers": ["codex"],
            }
        run = valid_graph_run(plan)
        mission_ids = ["M1", "M2"]
        run.update(
            {
                "status": "running",
                "intent": "plan-then-execute",
                "plan_readiness": "ready",
                "execution_authorized": True,
                "execution_authorization_source": "user requested execution",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "mission_ids": mission_ids,
                    "expires_when": "run_complete",
                },
            }
        )
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
            "external_runtimes": [
                {
                    "provider": "codex",
                    "driver": "codex_rescue_agent",
                    "status": "available",
                    "command": "agent:codex:codex-rescue",
                    "version": "1.0.4",
                    "contract_version": "harness-node-result-v1",
                    "completion_channel": "agent_result",
                    "evidence": ["foreground preflight passed"],
                }
            ],
        }
        run["observed"]["runtime"].update(
            {"available_worker_slots": 2, "isolation_capacity": 2}
        )
        for action in (
            "spawn_subagents",
            "create_app_managed_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, mission_ids, "*")
        authorize(run, "invoke_external_runtime", mission_ids, "runtime:codex")

        result = select_ready_nodes(plan, run)

        self.assertEqual(["N-M1", "N-M2"], result["ready_frontier"])
        self.assertEqual(
            ["run_external_codex_agent", "run_external_codex_agent"],
            [item["launch_kind"] for item in result["dispatchable_nodes"]],
        )
        for directive in result["dispatchable_nodes"]:
            self.assertEqual("codex:codex-rescue", directive["agent_type"])
            self.assertEqual("app_managed_worktree", directive["workspace_mode"])
            self.assertEqual("agent_result", directive["completion_channel"])
            self.assertEqual(None, directive["runtime_binding"]["model"])
            self.assertEqual(None, directive["runtime_binding"]["reasoning_effort"])
            self.assertEqual("external_agent", directive["runtime_binding"]["source"])
            self.assertEqual(
                [
                    "invoke_external_runtime",
                    "spawn_subagents",
                    "create_app_managed_worktrees",
                    "create_local_branches",
                    "create_local_commits",
                ],
                directive["required_actions"],
            )
            self.assertNotIn("create_user_owned_tasks", directive["required_actions"])
        self.assertEqual(1, len(result["wave_launches"]))
        self.assertEqual("run_external_codex_agent", result["wave_launches"][0]["launch_kind"])
        self.assertEqual(["N-M1", "N-M2"], result["wave_launches"][0]["node_ids"])
        self.assertEqual("codex:codex-rescue", result["wave_launches"][0]["agent_type"])

        run["runtime_capabilities"]["runtime_adapter"]["external_runtimes"][0][
            "status"
        ] = "unavailable"
        unavailable = select_ready_nodes(plan, run)
        deferred = {
            item["node_id"]: item["reason_codes"]
            for item in unavailable["deferred_nodes"]
        }
        self.assertIn("runtime_unavailable", deferred["N-M1"])
        self.assertIn("runtime_unavailable", deferred["N-M2"])

    def test_external_codex_review_requires_no_write_authorization(self) -> None:
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
            "mission_ids": ["M1"],
            "scope": ["src/a/**"],
            "required_evidence": ["reviewed_sha", "findings"],
        }
        plan["graph"]["nodes"].append(review)
        plan["graph"]["edges"].append(
            {
                "id": "E-M1-BACKEND-REVIEW",
                "kind": "dependency",
                "from": "N-M1",
                "to": review["id"],
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
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
                    "mission_ids": ["M1"],
                    "expires_when": "run_complete",
                },
            }
        )
        run["graph_state"]["node_states"]["N-M1"].update(
            {"phase": "succeeded", "attempts": 1, "last_attempt_id": "A-M1", "last_outcome": "pass"}
        )
        run["graph_state"]["node_states"]["N-M2"].update(
            {
                "phase": "blocked",
                "attempts": 1,
                "last_attempt_id": "A-M2",
                "last_outcome": "blocked",
                "blockers": ["not selected"],
            }
        )
        run["mission_states"]["M1"].update(
            {"phase": "integrated", "integration_gate": "PASS", "integrated_sha": "a" * 40}
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
            "external_runtimes": [
                {
                    "provider": "codex",
                    "driver": "codex_rescue_agent",
                    "status": "available",
                    "command": "agent:codex:codex-rescue",
                    "version": "1.0.4",
                    "contract_version": "harness-node-result-v1",
                    "completion_channel": "agent_result",
                    "evidence": ["foreground preflight passed"],
                }
            ],
        }
        authorize(run, "invoke_external_runtime", ["M1"], "runtime:codex")
        authorize(run, "spawn_subagents", ["M1"], "*")

        result = select_ready_nodes(plan, run)

        directive = result["dispatchable_nodes"][0]
        self.assertEqual("run_external_codex_agent", directive["launch_kind"])
        self.assertEqual("shared_checkout", directive["workspace_mode"])
        self.assertEqual(
            ["invoke_external_runtime", "spawn_subagents"],
            directive["required_actions"],
        )

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
                "mission_ids": ["M1"],
                "scope": ["src/a/**"],
                "required_evidence": ["reviewed_sha", "findings"],
            }
            reviews.append(node)
        plan["graph"]["nodes"].extend(reviews)
        plan["required_reviews"] = ["frontend_code", "visual"]
        plan["graph"]["entry_nodes"].extend([node["id"] for node in reviews])
        run = valid_graph_run(plan)
        run.update(
            {
                "status": "running",
                "intent": "plan-then-execute",
                "plan_readiness": "ready",
                "execution_authorized": True,
                "execution_authorization_source": "user requested execution",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "mission_ids": ["M1", "M2"],
                    "expires_when": "run_complete",
                },
            }
        )
        run["graph_state"]["node_states"]["N-M1"].update(
            {"phase": "succeeded", "attempts": 1, "last_attempt_id": "A-M1", "last_outcome": "pass"}
        )
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
        run["mission_states"]["M1"].update(
            {"phase": "integrated", "integration_gate": "PASS", "integrated_sha": "a" * 40}
        )
        run["mission_states"]["M2"]["phase"] = "blocked"
        run["integration"]["integration_head_sha"] = "a" * 40
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "codex",
            "available_drivers": ["sequential_parent"],
            "detection_source": "observed",
            "external_runtimes": [
                {
                    "provider": "claude_code",
                    "driver": "dynamic_workflow",
                    "status": "available",
                    "command": "claude",
                    "version": "2.1.214",
                    "completion_channel": "agent_result",
                    "evidence": ["protocol-v1 preflight passed"],
                }
            ],
        }

        unauthorized = select_ready_nodes(plan, run)
        review_deferred = {
            item["node_id"]: item["reason_codes"] for item in unauthorized["deferred_nodes"]
        }
        self.assertIn("action_not_authorized", review_deferred["N-FRONTEND-REVIEW"])
        self.assertIn("action_not_authorized", review_deferred["N-VISUAL-REVIEW"])

        authorize(run, "spawn_subagents", ["M1"], "*")
        authorize(run, "invoke_external_runtime", ["M1"], "runtime:claude_code")
        selected = select_ready_nodes(plan, run)
        self.assertEqual(1, len(selected["dispatchable_nodes"]))
        self.assertEqual("N-FRONTEND-REVIEW", selected["dispatchable_nodes"][0]["node_id"])
        self.assertEqual(
            "claude-fable-5",
            selected["dispatchable_nodes"][0]["runtime_binding"]["model"],
        )
        self.assertEqual(
            "xhigh",
            selected["dispatchable_nodes"][0]["runtime_binding"]["reasoning_effort"],
        )
        self.assertEqual(
            ["invoke_external_runtime", "spawn_subagents"],
            selected["dispatchable_nodes"][0]["required_actions"],
        )
        self.assertEqual(
            "code_review_readonly",
            selected["dispatchable_nodes"][0]["tool_profile"],
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
            "mission_ids": ["M1"],
            "scope": ["src/a/**"],
            "required_evidence": ["reviewed_sha", "findings"],
        }
        plan["graph"]["nodes"].append(review)
        plan["required_reviews"] = ["frontend_code"]
        plan["graph"]["entry_nodes"].append(review["id"])
        run = valid_graph_run(plan)
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
                    "driver": "external_dynamic_workflow",
                    "source": "external_bridge",
                    "model": "claude-fable-5",
                    "reasoning_effort": "xhigh",
                    "option_source": "plan_provider_options",
                },
                "task_thread_id": None,
                "report_path": None,
                "phase": "worker_running",
            }
        ]
        self.assertEqual([], validate_run(plan, run))
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

    def test_node_result_is_bound_to_the_active_graph_attempt(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        run["graph_state"]["node_states"]["N-M1"].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": "ATT-N-M1-1",
                "bound_worker_id": "W-M1",
            }
        )
        run["mission_states"]["M1"].update(
            {
                "phase": "worker_running",
                "lease_id": "LEASE-M1-1",
                "lease_plan_revision": plan["revision"],
                "lease_plan_digest_sha256": digest,
                "worker_id": "W-M1",
                "base_sha": "a" * 40,
            }
        )
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

    def test_external_claude_waves_split_by_tool_profile(self) -> None:
        binding = {
            "provider": "claude_code",
            "driver": "external_dynamic_workflow",
            "source": "external_bridge",
            "model": "sonnet",
            "reasoning_effort": "high",
            "option_source": "plan_provider_options",
        }
        launches = _external_wave_launches(
            [
                {
                    "launch_kind": "run_external_dynamic_workflow",
                    "node_id": "N-CODE-REVIEW",
                    "runtime_binding": binding,
                    "tool_profile": "code_review_readonly",
                },
                {
                    "launch_kind": "run_external_dynamic_workflow",
                    "node_id": "N-VISUAL-REVIEW",
                    "runtime_binding": binding,
                    "tool_profile": "visual_review_readonly",
                },
            ]
        )

        self.assertEqual(
            ["code_review_readonly", "visual_review_readonly"],
            [launch["tool_profile"] for launch in launches],
        )
        self.assertEqual(
            [["N-CODE-REVIEW"], ["N-VISUAL-REVIEW"]],
            [launch["node_ids"] for launch in launches],
        )

    def test_external_claude_nodes_are_grouped_by_plan_selected_model(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["entry_nodes"] = ["N-M1", "N-M2"]
        plan["graph"]["edges"] = []
        for node, model in zip(plan["graph"]["nodes"], ("sonnet", "opus"), strict=True):
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
        run.update(
            {
                "status": "running",
                "intent": "plan-then-execute",
                "plan_readiness": "ready",
                "execution_authorized": True,
                "execution_authorization_source": "user requested execution",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "mission_ids": mission_ids,
                    "expires_when": "run_complete",
                },
            }
        )
        run["runtime_capabilities"]["max_parallel_workers"] = 2
        run["observed"]["runtime"].update(
            {"available_worker_slots": 2, "isolation_capacity": 2}
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "codex",
            "available_drivers": ["sequential_parent"],
            "detection_source": "observed",
            "external_runtimes": [
                {
                    "provider": "claude_code",
                    "driver": "dynamic_workflow",
                    "status": "available",
                    "command": "claude",
                    "version": "2.1.214",
                    "completion_channel": "agent_result",
                    "evidence": ["protocol-v1 preflight passed"],
                }
            ],
        }
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, mission_ids, "*")
        authorize(run, "invoke_external_runtime", mission_ids, "runtime:claude_code")

        result = select_ready_nodes(plan, run)

        self.assertEqual(["opus", "sonnet"], [wave["model"] for wave in result["wave_launches"]])
        self.assertEqual([["N-M2"], ["N-M1"]], [wave["node_ids"] for wave in result["wave_launches"]])
        self.assertEqual(
            ["mission_write", "mission_write"],
            [wave["tool_profile"] for wave in result["wave_launches"]],
        )


class ClaudeBridgeTests(unittest.TestCase):
    def write_bridge_fixture(
        self,
        root: Path,
        plan: dict[str, object],
        run: dict[str, object],
        request: dict[str, object],
    ) -> tuple[Path, Path, Path]:
        plan_path = root / "PLAN.md"
        run_path = root / "RUN.md"
        request_path = root / "wave.json"
        plan_path.write_text(
            markdown("## Harness Plan Manifest", "harness_plan", plan),
            encoding="utf-8",
        )
        run_path.write_text(
            markdown("## Harness Run State", "harness_run", run),
            encoding="utf-8",
        )
        request_path.write_text(json.dumps(request), encoding="utf-8")
        return plan_path, run_path, request_path

    def workflow_stream_result(
        self,
        wrapper: dict[str, object],
        request: dict[str, object],
        *,
        runtime_overrides: dict[str, object] | None = None,
        tool_overrides: dict[str, object] | None = None,
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        workflow_args = {
            key: value
            for key, value in request.items()
            if key
            not in {
                "allowed_tools",
                "permission_mode",
                "model",
                "reasoning_effort",
            }
        }
        runtime_result = {
            "status": "async_launched",
            "taskId": wrapper.get("workflow_task_id"),
            "taskType": "local_workflow",
            "runId": wrapper.get("workflow_run_id"),
            "scriptPath": str(bridge.DEFAULT_GRAPH_WORKFLOW),
            "error": wrapper.get("workflow_error"),
        }
        if runtime_overrides:
            runtime_result.update(runtime_overrides)
        tool_input = {
            "scriptPath": str(bridge.DEFAULT_GRAPH_WORKFLOW),
            "args": workflow_args,
        }
        if tool_overrides:
            tool_input.update(tool_overrides)
        return wrapper, runtime_result, tool_input

    def mission_bridge_fixture(
        self, root: Path
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        plan = valid_graph_plan()
        node = plan["graph"]["nodes"][0]
        node["runtime"] = {
            "preferred_provider": "claude_code",
            "allowed_providers": ["claude_code"],
            "provider_options": {
                "claude_code": {"model": "sonnet", "reasoning_effort": "high"}
            },
        }
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        batch_base_sha = run["integration"]["batch_base_sha"]
        worktree_path = str((root / "worktree-m1").resolve())
        repository_path = str(root.resolve())
        branch_ref = "refs/heads/claude/test-m1"
        binding = {
            "provider": "claude_code",
            "driver": "external_dynamic_workflow",
            "source": "external_bridge",
            "model": "sonnet",
            "reasoning_effort": "high",
            "option_source": "plan_provider_options",
        }
        run.update(
            {
                "status": "running",
                "intent": "plan-then-execute",
                "plan_readiness": "ready",
                "execution_authorized": True,
                "execution_authorization_source": "user requested execution",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "mission_ids": ["M1"],
                    "expires_when": "run_complete",
                },
            }
        )
        run["runtime_capabilities"].update(
            {
                "permission_boundary": {
                    "selected_mode": "named_profile",
                    "profile_name": "claude-wave",
                    "approval_policy": "on-request",
                    "filesystem_scope": "custom",
                    "network_scope": "filtered",
                    "local_binding": "allowed",
                    "worker_inheritance": "inherited",
                    "status": "ready",
                },
            }
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "codex",
            "available_drivers": ["sequential_parent"],
            "detection_source": "observed",
            "external_runtimes": [
                {
                    "provider": "claude_code",
                    "driver": "dynamic_workflow",
                    "status": "available",
                    "command": "claude",
                    "version": "2.1.214",
                    "completion_channel": "agent_result",
                    "evidence": ["protocol-v1 preflight passed"],
                }
            ],
        }
        run["observed"]["git"]["parent_worktree_path"] = repository_path
        run["graph_state"]["node_states"]["N-M1"].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": "ATT-N-M1-1",
                "bound_worker_id": "W-M1",
            }
        )
        run["mission_states"]["M1"].update(
            {
                "phase": "worker_running",
                "lease_id": "LEASE-M1-1",
                "lease_plan_revision": plan["revision"],
                "lease_plan_digest_sha256": digest,
                "worker_id": "W-M1",
                "base_sha": batch_base_sha,
            }
        )
        run["workers"] = [
            {
                "worker_id": "W-M1",
                "mission_id": "M1",
                "lease_id": "LEASE-M1-1",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "batch_base_sha": batch_base_sha,
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "runtime_binding": binding,
                "task_thread_id": None,
                "worktree_path": worktree_path,
                "branch_ref": branch_ref,
                "report_path": None,
                "phase": "worker_running",
                "worker_head_sha": None,
            }
        ]
        authorize(run, "invoke_external_runtime", ["M1"], "runtime:claude_code")
        authorize(run, "spawn_subagents", ["M1"], "worker:W-M1")
        authorize(run, "create_local_worktrees", ["M1"], f"worktree:{worktree_path}")
        authorize(run, "create_local_branches", ["M1"], f"branch:{branch_ref}")
        authorize(run, "create_local_commits", ["M1"], f"branch:{branch_ref}")
        request = {
            "run_id": run["run_id"],
            "plan_id": plan["plan_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "graph_revision": run["graph_state"]["graph_revision"],
            "batch_base_sha": batch_base_sha,
            "nodes": [
                {
                    "node_kind": "mission",
                    "node_id": "N-M1",
                    "attempt_id": "ATT-N-M1-1",
                    "mission_id": "M1",
                    "lease_id": "LEASE-M1-1",
                    "branch_ref": branch_ref,
                    "worktree_path": worktree_path,
                    "failure_outcome": "retryable_failure",
                    "worker_prompt": "Complete M1",
                }
            ],
            "tool_profile": "mission_write",
            "allowed_tools": sorted(bridge.TOOL_PROFILE_REQUIREMENTS["mission_write"]),
            "permission_mode": "dontAsk",
            "model": "sonnet",
            "reasoning_effort": "high",
        }
        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_run(plan, run))
        return plan, run, request

    def review_bridge_fixture(
        self, root: Path
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
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
            "mission_ids": ["M1"],
            "scope": ["src/a/**"],
            "required_evidence": ["reviewed_sha", "findings"],
        }
        plan["graph"]["nodes"].append(review)
        plan["graph"]["entry_nodes"].append(review["id"])
        plan["required_reviews"] = ["frontend_code"]
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        reviewed_sha = "b" * 40
        review_path = str((root / "review").resolve())
        repository_path = str(root.resolve())
        binding = {
            "provider": "claude_code",
            "driver": "external_dynamic_workflow",
            "source": "external_bridge",
            "model": "claude-fable-5",
            "reasoning_effort": "xhigh",
            "option_source": "plan_provider_options",
        }
        run.update(
            {
                "status": "running",
                "intent": "plan-then-execute",
                "plan_readiness": "ready",
                "execution_authorized": True,
                "execution_authorization_source": "user requested review",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "mission_ids": ["M1"],
                    "expires_when": "run_complete",
                },
            }
        )
        run["runtime_capabilities"].update(
            {
                "permission_boundary": {
                    "selected_mode": "named_profile",
                    "profile_name": "claude-review",
                    "approval_policy": "on-request",
                    "filesystem_scope": "custom",
                    "network_scope": "filtered",
                    "local_binding": "allowed",
                    "worker_inheritance": "inherited",
                    "status": "ready",
                },
            }
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "codex",
            "available_drivers": ["sequential_parent"],
            "detection_source": "observed",
            "external_runtimes": [
                {
                    "provider": "claude_code",
                    "driver": "dynamic_workflow",
                    "status": "available",
                    "command": "claude",
                    "version": "2.1.214",
                    "completion_channel": "agent_result",
                    "evidence": ["protocol-v1 preflight passed"],
                }
            ],
        }
        run["observed"]["git"]["parent_worktree_path"] = repository_path
        run["integration"]["integration_head_sha"] = reviewed_sha
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
                "plan_digest_sha256": digest,
                "graph_revision": run["graph_state"]["graph_revision"],
                "reviewed_sha": reviewed_sha,
                "review_path": review_path,
                "worker_runtime": "subagent",
                "completion_channel": "agent_result",
                "runtime_binding": binding,
                "task_thread_id": None,
                "report_path": None,
                "phase": "worker_running",
            }
        ]
        authorize(run, "invoke_external_runtime", ["M1"], "runtime:claude_code")
        authorize(run, "spawn_subagents", ["M1"], "worker:RW-1")
        request = {
            "run_id": run["run_id"],
            "plan_id": plan["plan_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "graph_revision": run["graph_state"]["graph_revision"],
            "batch_base_sha": run["integration"]["batch_base_sha"],
            "nodes": [
                {
                    "node_kind": "review",
                    "node_id": review["id"],
                    "attempt_id": "ATT-REVIEW-1",
                    "review_id": "batch",
                    "review_type": "frontend_code",
                    "reviewed_sha": reviewed_sha,
                    "review_path": review_path,
                    "review_scope": ["src/a/**"],
                    "required_evidence": ["reviewed_sha", "findings"],
                    "failure_outcome": "blocked",
                    "worker_prompt": "Review the frontend changes",
                }
            ],
            "tool_profile": "code_review_readonly",
            "allowed_tools": sorted(
                bridge.TOOL_PROFILE_REQUIREMENTS["code_review_readonly"]
            ),
            "permission_mode": "dontAsk",
            "model": "claude-fable-5",
            "reasoning_effort": "xhigh",
        }
        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_run(plan, run))
        return plan, run, request

    def test_extracts_structured_output_and_requires_workflow_tool(self) -> None:
        self.assertEqual(
            {"status": "available"},
            bridge._extract_structured('{"structured_output":{"status":"available"}}'),
        )
        wrapper = {
            "workflow_task_id": "task-1",
            "workflow_run_id": "wf-1",
            "workflow_script_path": str(bridge.DEFAULT_GRAPH_WORKFLOW),
            "workflow_error": None,
            "results": [],
        }
        runtime_result = {
            "status": "async_launched",
            "taskId": "task-1",
            "taskType": "local_workflow",
            "runId": "wf-1",
            "scriptPath": str(bridge.DEFAULT_GRAPH_WORKFLOW),
        }
        events = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu-1",
                            "name": "Workflow",
                            "input": {"scriptPath": "workflow.js", "args": {}},
                        }
                    ]
                },
            },
            {
                "type": "user",
                "message": {
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu-1",
                            "content": "complete",
                        }
                    ]
                },
                "tool_use_result": runtime_result,
            },
            {"type": "result", "structured_output": wrapper},
        ]
        self.assertEqual(
            (wrapper, runtime_result, {"scriptPath": "workflow.js", "args": {}}),
            bridge._extract_workflow_stream("\n".join(json.dumps(event) for event in events)),
        )
        fallback_metadata = copy.deepcopy(events)
        del fallback_metadata[1]["tool_use_result"]
        fallback_metadata[1]["message"]["content"][0]["content"] = json.dumps(
            runtime_result
        )
        self.assertEqual(
            (wrapper, runtime_result, {"scriptPath": "workflow.js", "args": {}}),
            bridge._extract_workflow_stream(
                "\n".join(json.dumps(event) for event in fallback_metadata)
            ),
        )

        with self.assertRaisesRegex(bridge.BridgeError, "runtime metadata is unavailable"):
            missing_metadata = copy.deepcopy(events)
            del missing_metadata[1]["tool_use_result"]
            bridge._extract_workflow_stream(
                "\n".join(json.dumps(event) for event in missing_metadata)
            )

        with self.assertRaisesRegex(bridge.BridgeError, "exactly one Workflow tool call"):
            duplicate_call = copy.deepcopy(events)
            duplicate_call.insert(1, copy.deepcopy(duplicate_call[0]))
            bridge._extract_workflow_stream(
                "\n".join(json.dumps(event) for event in duplicate_call)
            )

        with self.assertRaisesRegex(bridge.BridgeError, "no other tool calls"):
            extra_tool = copy.deepcopy(events)
            extra_tool[0]["message"]["content"].append(
                {
                    "type": "tool_use",
                    "id": "toolu-edit",
                    "name": "Edit",
                    "input": {"file_path": "parent.txt"},
                }
            )
            bridge._extract_workflow_stream(
                "\n".join(json.dumps(event) for event in extra_tool)
            )

        with self.assertRaisesRegex(bridge.BridgeError, "occurred before its tool call"):
            result_before_call = [
                copy.deepcopy(events[1]),
                copy.deepcopy(events[0]),
                copy.deepcopy(events[2]),
            ]
            bridge._extract_workflow_stream(
                "\n".join(json.dumps(event) for event in result_before_call)
            )

        with self.assertRaisesRegex(bridge.BridgeError, "final result occurred before"):
            final_before_result = [
                copy.deepcopy(events[0]),
                copy.deepcopy(events[2]),
                copy.deepcopy(events[1]),
            ]
            bridge._extract_workflow_stream(
                "\n".join(json.dumps(event) for event in final_before_result)
            )

        with self.assertRaisesRegex(bridge.BridgeError, "duplicate Workflow tool result blocks"):
            duplicate_result = copy.deepcopy(events)
            duplicate_result[1]["message"]["content"].append(
                copy.deepcopy(duplicate_result[1]["message"]["content"][0])
            )
            bridge._extract_workflow_stream(
                "\n".join(json.dumps(event) for event in duplicate_result)
            )

        with self.assertRaisesRegex(bridge.BridgeError, "must allow the Workflow tool"):
            bridge._build_command(
                command="claude",
                prompt="test",
                schema=bridge.PREFLIGHT_SCHEMA,
                allowed_tools=[],
                permission_mode="dontAsk",
                max_budget_usd=0.1,
            )
        command = bridge._build_command(
            command="claude",
            prompt="test",
            schema=bridge.PREFLIGHT_SCHEMA,
            allowed_tools=["Workflow"],
            permission_mode="dontAsk",
            max_budget_usd=0.1,
        )
        self.assertEqual("sonnet", command[command.index("--model") + 1])

        bypass_command = bridge._build_command(
            command="claude",
            prompt="test",
            schema=bridge.PREFLIGHT_SCHEMA,
            allowed_tools=["Workflow"],
            permission_mode="bypassPermissions",
            max_budget_usd=0.1,
        )
        self.assertIn("--dangerously-skip-permissions", bypass_command)
        self.assertNotIn("--permission-mode", bypass_command)

    @mock.patch.object(bridge, "_invoke")
    @mock.patch.object(bridge, "_claude_version", return_value="2.1.214 (Claude Code)")
    @mock.patch.object(bridge, "_resolve_claude", return_value="C:/bin/claude.exe")
    def test_preflight_returns_recordable_runtime_evidence(
        self,
        _resolve: mock.Mock,
        _version: mock.Mock,
        invoke: mock.Mock,
    ) -> None:
        invoke.return_value = {
            "provider": "claude_code",
            "driver": "dynamic_workflow",
            "protocol_version": 1,
            "status": "available",
            "probe_count": 2,
            "probe_labels": ["probe-a", "probe-b"],
        }
        result = bridge.preflight(
            claude="claude",
            script=bridge.DEFAULT_PREFLIGHT,
            cwd=Path.cwd(),
            timeout=30,
            max_budget_usd=0.1,
        )
        self.assertEqual("PASS", result["status"])
        self.assertEqual("dynamic_workflow", result["runtime"]["driver"])
        command = invoke.call_args.args[0]
        self.assertEqual("haiku", command[command.index("--model") + 1])

    def test_tool_profiles_require_enter_worktree_and_reject_review_writes(self) -> None:
        mission = [{"node_kind": "mission"}]
        mission_tools = sorted(bridge.TOOL_PROFILE_REQUIREMENTS["mission_write"])
        bridge._validate_tool_profile("mission_write", mission_tools, mission)
        with self.assertRaisesRegex(bridge.BridgeError, "EnterWorktree"):
            bridge._validate_tool_profile(
                "mission_write",
                [tool for tool in mission_tools if tool != "EnterWorktree"],
                mission,
            )

        review = [{"node_kind": "review", "review_type": "frontend_code"}]
        review_tools = sorted(bridge.TOOL_PROFILE_REQUIREMENTS["code_review_readonly"])
        bridge._validate_tool_profile("code_review_readonly", review_tools, review)
        with self.assertRaisesRegex(bridge.BridgeError, "EnterWorktree"):
            bridge._validate_tool_profile(
                "code_review_readonly",
                [tool for tool in review_tools if tool != "EnterWorktree"],
                review,
            )
        with self.assertRaisesRegex(bridge.BridgeError, "write-capable tools"):
            bridge._validate_tool_profile(
                "code_review_readonly",
                [*review_tools, "Edit"],
                review,
            )
        with self.assertRaisesRegex(bridge.BridgeError, "unexpected tools"):
            bridge._validate_tool_profile(
                "code_review_readonly",
                [*review_tools, "mcp__filesystem__write_file"],
                review,
            )

    def test_wave_request_rejects_missing_runtime_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wave.json"
            path.write_text(json.dumps({"nodes": []}), encoding="utf-8")
            with self.assertRaisesRegex(bridge.BridgeError, "top-level fields"):
                bridge._load_wave_request(path)

    def test_workflow_templates_accept_stringified_args_and_bind_results(self) -> None:
        workflow = bridge.DEFAULT_GRAPH_WORKFLOW.read_text(encoding="utf-8")
        preflight = bridge.DEFAULT_PREFLIGHT.read_text(encoding="utf-8")
        legacy = (
            bridge.DEFAULT_GRAPH_WORKFLOW.parent / "CLAUDE_DYNAMIC_WORKFLOW.template.js"
        ).read_text(encoding="utf-8")

        for content in (workflow, preflight, legacy):
            self.assertIn('typeof args === "string" ? JSON.parse(args) : args', content)
        self.assertIn("pipeline(workflowArgs.nodes", workflow)
        self.assertIn('"run_id"', workflow)
        self.assertIn('"batch_base_sha"', workflow)
        self.assertIn("call EnterWorktree with that exact path", workflow)
        self.assertIn("call EnterWorktree with that exact review path", workflow)
        self.assertIn("does not enter that exact path", workflow)
        self.assertIn("workflow-agent-null", workflow)
        self.assertIn('"tool_profile"', workflow)
        self.assertIn('phase: phaseName', workflow)
        self.assertIn('const labels = ["probe-a", "probe-b"]', preflight)
        self.assertIn("pipeline(labels", preflight)

    @mock.patch.object(bridge, "_invoke")
    @mock.patch.object(bridge, "_claude_version", return_value="2.1.214 (Claude Code)")
    @mock.patch.object(bridge, "_resolve_claude", return_value="C:/bin/claude.exe")
    def test_wave_prompt_requires_workflow_args_to_remain_an_object(
        self,
        _resolve: mock.Mock,
        _version: mock.Mock,
        invoke: mock.Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, request = self.mission_bridge_fixture(root)
            wrapper = {
                "workflow_run_id": "wf-test",
                "workflow_task_id": "task-test",
                "workflow_script_path": str(bridge.DEFAULT_GRAPH_WORKFLOW),
                "workflow_error": None,
                "results": [{"node_result": {"node_id": "N-M1"}}],
            }
            invoke.return_value = self.workflow_stream_result(wrapper, request)
            plan_path, run_path, request_path = self.write_bridge_fixture(
                root, plan, run, request
            )
            with mock.patch.object(bridge, "_validate_checkout"):
                result = bridge.run_wave(
                    claude="claude",
                    script=bridge.DEFAULT_GRAPH_WORKFLOW,
                    plan_path=plan_path,
                    run_path=run_path,
                    request_path=request_path,
                    cwd=Path.cwd(),
                    timeout=30,
                    max_budget_usd=0.1,
                )

        prompt = invoke.call_args.args[0][-1]
        self.assertIn("Do not use any other tool", prompt)
        self.assertIn("actual object, not as a JSON-encoded string", prompt)
        command = invoke.call_args.args[0]
        self.assertEqual("sonnet", command[command.index("--model") + 1])
        self.assertEqual("high", command[command.index("--effort") + 1])
        self.assertEqual("stream-json", command[command.index("--output-format") + 1])
        self.assertIn("--verbose", command)
        self.assertNotIn("--json-schema", command)
        self.assertEqual("wf-test", result["runtime"]["workflow_run_id"])
        self.assertEqual("task-test", result["runtime"]["workflow_task_id"])
        self.assertEqual(
            hashlib.sha256(bridge.DEFAULT_GRAPH_WORKFLOW.read_bytes()).hexdigest(),
            result["runtime"]["workflow_script_sha256"],
        )
        self.assertEqual("mission_write", result["runtime"]["tool_profile"])

    @mock.patch.object(bridge, "_invoke")
    @mock.patch.object(bridge, "_claude_version", return_value="2.1.214 (Claude Code)")
    @mock.patch.object(bridge, "_resolve_claude", return_value="C:/bin/claude.exe")
    def test_valid_review_wave_reaches_claude_invocation(
        self,
        _resolve: mock.Mock,
        _version: mock.Mock,
        invoke: mock.Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, request = self.review_bridge_fixture(root)
            wrapper = {
                "workflow_run_id": "wf-review",
                "workflow_task_id": "task-review",
                "workflow_script_path": str(bridge.DEFAULT_GRAPH_WORKFLOW),
                "workflow_error": None,
                "results": [{"node_result": {"node_id": "N-FRONTEND-REVIEW"}}],
            }
            invoke.return_value = self.workflow_stream_result(wrapper, request)
            plan_path, run_path, request_path = self.write_bridge_fixture(
                root, plan, run, request
            )
            with mock.patch.object(bridge, "_validate_checkout") as checkout:
                result = bridge.run_wave(
                    claude="claude",
                    script=bridge.DEFAULT_GRAPH_WORKFLOW,
                    plan_path=plan_path,
                    run_path=run_path,
                    request_path=request_path,
                    cwd=Path.cwd(),
                    timeout=30,
                    max_budget_usd=0.1,
                )

        checkout.assert_called_once()
        invoke.assert_called_once()
        command = invoke.call_args.args[0]
        allowed_tools = command[command.index("--allowedTools") + 1].split(",")
        self.assertIn("EnterWorktree", allowed_tools)
        self.assertNotIn("Edit", allowed_tools)
        self.assertNotIn("Write", allowed_tools)
        self.assertEqual("wf-review", result["runtime"]["workflow_run_id"])
        self.assertEqual("code_review_readonly", result["runtime"]["tool_profile"])

    def test_wave_binding_rejects_stale_plan_and_run_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, request = self.mission_bridge_fixture(root)
            for field, stale in (
                ("plan_digest_sha256", "f" * 64),
                ("graph_revision", request["graph_revision"] + 1),
                ("batch_base_sha", "f" * 40),
            ):
                with self.subTest(field=field):
                    stale_request = copy.deepcopy(request)
                    stale_request[field] = stale
                    with self.assertRaisesRegex(bridge.BridgeError, field):
                        bridge._validate_current_wave_binding(stale_request, plan, run)

    def test_wave_binding_requires_current_execution_and_action_authorizations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, request = self.mission_bridge_fixture(root)
            unauthorized = copy.deepcopy(run)
            unauthorized.update(
                {
                    "execution_authorized": False,
                    "execution_authorization_source": None,
                    "execution_authorization_scope": None,
                }
            )
            with self.assertRaisesRegex(bridge.BridgeError, "Execution authorization"):
                bridge._validate_current_wave_binding(request, plan, unauthorized)

            missing_action = copy.deepcopy(run)
            missing_action["authorizations"]["spawn_subagents"] = {
                "authorized": False,
                "source": None,
            }
            with self.assertRaisesRegex(bridge.BridgeError, "spawn_subagents"):
                bridge._validate_current_wave_binding(request, plan, missing_action)

    def test_wave_binding_requires_ready_permission_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, request = self.mission_bridge_fixture(root)
            missing = copy.deepcopy(run)
            del missing["runtime_capabilities"]["permission_boundary"]
            with self.assertRaisesRegex(bridge.BridgeError, "permission boundary is not ready"):
                bridge._validate_current_wave_binding(request, plan, missing)

            bypass = copy.deepcopy(request)
            bypass["permission_mode"] = "bypassPermissions"
            with self.assertRaisesRegex(bridge.BridgeError, "full_access"):
                bridge._validate_current_wave_binding(bypass, plan, run)

    def test_wave_binding_rejects_stale_attempt_and_mission_lease(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, request = self.mission_bridge_fixture(root)
            stale_attempt = copy.deepcopy(request)
            stale_attempt["nodes"][0]["attempt_id"] = "ATT-STALE"
            with self.assertRaisesRegex(bridge.BridgeError, "active graph attempt"):
                bridge._validate_current_wave_binding(stale_attempt, plan, run)

            stale_lease = copy.deepcopy(request)
            stale_lease["nodes"][0]["lease_id"] = "LEASE-STALE"
            with self.assertRaisesRegex(bridge.BridgeError, "current lease"):
                bridge._validate_current_wave_binding(stale_lease, plan, run)

    def test_review_wave_rejects_contract_and_checkout_head_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, request = self.review_bridge_fixture(root)
            stale_contract = copy.deepcopy(request)
            stale_contract["nodes"][0]["review_scope"] = ["src/other/**"]
            with self.assertRaisesRegex(bridge.BridgeError, "review contract"):
                bridge._validate_current_wave_binding(stale_contract, plan, run)

            review_path = Path(request["nodes"][0]["review_path"])
            common_dir = str((root / ".git").resolve())

            def fake_git_output(cwd: Path, *args: str, timeout: int = 30) -> str:
                del timeout
                if args == ("rev-parse", "--show-toplevel"):
                    return str(cwd.resolve())
                if args == ("rev-parse", "--path-format=absolute", "--git-common-dir"):
                    return common_dir
                if args == ("rev-parse", "HEAD"):
                    return "c" * 40
                raise AssertionError(f"Unexpected git command: {args}")

            with mock.patch.object(bridge, "_git_output", side_effect=fake_git_output):
                with self.assertRaisesRegex(bridge.BridgeError, "HEAD does not match"):
                    bridge._validate_current_wave_binding(request, plan, run)
            self.assertEqual(review_path, Path(request["nodes"][0]["review_path"]))

    @mock.patch.object(bridge, "_invoke")
    @mock.patch.object(bridge, "_claude_version", return_value="2.1.214 (Claude Code)")
    @mock.patch.object(bridge, "_resolve_claude", return_value="C:/bin/claude.exe")
    def test_wave_requires_a_real_workflow_run_id(
        self,
        _resolve: mock.Mock,
        _version: mock.Mock,
        invoke: mock.Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, request = self.mission_bridge_fixture(root)
            plan_path, run_path, request_path = self.write_bridge_fixture(
                root, plan, run, request
            )
            for run_id in (None, "", "   "):
                with self.subTest(run_id=run_id):
                    wrapper = {
                        "workflow_run_id": run_id,
                        "workflow_task_id": "task-test",
                        "workflow_script_path": str(bridge.DEFAULT_GRAPH_WORKFLOW),
                        "workflow_error": None,
                        "results": [{"node_result": {"node_id": "N-M1"}}],
                    }
                    invoke.return_value = self.workflow_stream_result(wrapper, request)
                    with mock.patch.object(bridge, "_validate_checkout"):
                        with self.assertRaisesRegex(
                            bridge.BridgeError, "runtime did not return a runId"
                        ):
                            bridge.run_wave(
                                claude="claude",
                                script=bridge.DEFAULT_GRAPH_WORKFLOW,
                                plan_path=plan_path,
                                run_path=run_path,
                                request_path=request_path,
                                cwd=Path.cwd(),
                                timeout=30,
                                max_budget_usd=0.1,
                            )

    @mock.patch.object(bridge, "_invoke")
    @mock.patch.object(bridge, "_claude_version", return_value="2.1.214 (Claude Code)")
    @mock.patch.object(bridge, "_resolve_claude", return_value="C:/bin/claude.exe")
    def test_wave_rejects_a_run_id_not_confirmed_by_runtime_evidence(
        self,
        _resolve: mock.Mock,
        _version: mock.Mock,
        invoke: mock.Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, request = self.mission_bridge_fixture(root)
            wrapper = {
                "workflow_run_id": "wf-invented",
                "workflow_task_id": "task-test",
                "workflow_script_path": str(bridge.DEFAULT_GRAPH_WORKFLOW),
                "workflow_error": None,
                "results": [{"node_result": {"node_id": "N-M1"}}],
            }
            invoke.return_value = self.workflow_stream_result(
                wrapper,
                request,
                runtime_overrides={"runId": "wf-runtime"},
            )
            plan_path, run_path, request_path = self.write_bridge_fixture(
                root, plan, run, request
            )
            with mock.patch.object(bridge, "_validate_checkout"):
                with self.assertRaisesRegex(
                    bridge.BridgeError, "run ID does not match runtime evidence"
                ):
                    bridge.run_wave(
                        claude="claude",
                        script=bridge.DEFAULT_GRAPH_WORKFLOW,
                        plan_path=plan_path,
                        run_path=run_path,
                        request_path=request_path,
                        cwd=Path.cwd(),
                        timeout=30,
                        max_budget_usd=0.1,
                    )

    def test_wave_rejects_untrusted_workflow_runtime_evidence(self) -> None:
        script_path = bridge.DEFAULT_GRAPH_WORKFLOW.resolve()
        workflow_args = {"run_id": "RUN-1"}
        wrapper = {
            "workflow_task_id": "task-1",
            "workflow_run_id": "wf-1",
            "workflow_script_path": str(script_path),
            "workflow_error": None,
            "results": [],
        }
        runtime_result = {
            "status": "async_launched",
            "taskId": "task-1",
            "taskType": "local_workflow",
            "runId": "wf-1",
            "scriptPath": str(script_path),
            "error": None,
        }
        tool_input = {"scriptPath": str(script_path), "args": workflow_args}

        cases = (
            (
                "task ID does not match runtime evidence",
                {**runtime_result, "taskId": "task-runtime"},
                tool_input,
            ),
            (
                "did not launch a local workflow",
                {**runtime_result, "taskType": "remote_workflow"},
                tool_input,
            ),
            (
                "did not launch a local workflow",
                {key: value for key, value in runtime_result.items() if key != "taskType"},
                tool_input,
            ),
            (
                "runtime used a different scriptPath",
                {**runtime_result, "scriptPath": "C:/other/workflow.js"},
                tool_input,
            ),
            (
                "changed the wave arguments",
                runtime_result,
                {**tool_input, "args": {"run_id": "RUN-OTHER"}},
            ),
            (
                "tool call used a different scriptPath",
                runtime_result,
                {**tool_input, "scriptPath": "C:/other/workflow.js"},
            ),
        )
        for message, runtime_evidence, call_input in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(bridge.BridgeError, message):
                    bridge._validate_workflow_evidence(
                        wrapper,
                        runtime_evidence,
                        call_input,
                        workflow_script_path=script_path,
                        workflow_args=workflow_args,
                    )

    @mock.patch.object(bridge, "_invoke")
    @mock.patch.object(bridge, "_claude_version", return_value="2.1.214 (Claude Code)")
    @mock.patch.object(bridge, "_resolve_claude", return_value="C:/bin/claude.exe")
    def test_wave_rejects_a_different_workflow_script_path(
        self,
        _resolve: mock.Mock,
        _version: mock.Mock,
        invoke: mock.Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, request = self.mission_bridge_fixture(root)
            wrapper = {
                "workflow_run_id": "wf-test",
                "workflow_task_id": "task-test",
                "workflow_script_path": "C:/other/workflow.js",
                "workflow_error": None,
                "results": [{"node_result": {"node_id": "N-M1"}}],
            }
            invoke.return_value = self.workflow_stream_result(wrapper, request)
            plan_path, run_path, request_path = self.write_bridge_fixture(
                root, plan, run, request
            )
            with mock.patch.object(bridge, "_validate_checkout"):
                with self.assertRaisesRegex(
                    bridge.BridgeError, "script path does not match runtime evidence"
                ):
                    bridge.run_wave(
                        claude="claude",
                        script=bridge.DEFAULT_GRAPH_WORKFLOW,
                        plan_path=plan_path,
                        run_path=run_path,
                        request_path=request_path,
                        cwd=Path.cwd(),
                        timeout=30,
                        max_budget_usd=0.1,
                    )

    def test_run_wave_cli_requires_plan_and_run_paths(self) -> None:
        parser = bridge.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["run-wave", "--request", "wave.json"])

    @mock.patch.object(bridge, "_invoke")
    @mock.patch.object(bridge, "_claude_version", return_value="2.1.214 (Claude Code)")
    @mock.patch.object(bridge, "_resolve_claude", return_value="C:/bin/claude.exe")
    def test_wave_rejects_a_cli_model_that_disagrees_with_plan(
        self,
        _resolve: mock.Mock,
        _version: mock.Mock,
        _invoke: mock.Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, request = self.mission_bridge_fixture(root)
            plan_path, run_path, request_path = self.write_bridge_fixture(
                root, plan, run, request
            )
            with self.assertRaisesRegex(bridge.BridgeError, "must match"):
                bridge.run_wave(
                    claude="claude",
                    script=bridge.DEFAULT_GRAPH_WORKFLOW,
                    plan_path=plan_path,
                    run_path=run_path,
                    request_path=request_path,
                    cwd=Path.cwd(),
                    timeout=30,
                    max_budget_usd=0.1,
                    model="opus",
                )


if __name__ == "__main__":
    unittest.main()

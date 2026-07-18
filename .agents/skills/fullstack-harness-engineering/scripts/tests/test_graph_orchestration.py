#!/usr/bin/env python3
"""Typed graph and external Claude runtime tests."""

from __future__ import annotations

import copy
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
from select_ready_nodes import _runtime_binding, select_ready_nodes  # noqa: E402
from test_harness_manifest import valid_plan, valid_run  # noqa: E402
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
        self.assertEqual("opus", result["dispatchable_nodes"][0]["runtime_binding"]["model"])
        self.assertEqual("opus", result["wave_launches"][0]["model"])
        self.assertEqual(["N-M1"], result["wave_launches"][0]["node_ids"])

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
        result = {
            "node_id": review["id"],
            "attempt_id": "ATT-REVIEW-1",
            "plan_id": plan["plan_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "graph_revision": run["graph_state"]["graph_revision"],
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
            "node_id": "N-M1",
            "attempt_id": "ATT-N-M1-1",
            "plan_id": plan["plan_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "graph_revision": run["graph_state"]["graph_revision"],
            "status": "succeeded",
            "outcome": "pass",
            "worker_result": {"status": "PASS"},
            "refinement_request": None,
            "evidence_paths": ["worker-result.json"],
        }

        self.assertEqual([], validate_node_result(plan, run, result))
        result["attempt_id"] = "ATT-STALE"
        self.assertTrue(
            any("active attempt" in error for error in validate_node_result(plan, run, result))
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


class ClaudeBridgeTests(unittest.TestCase):
    def test_extracts_structured_output_and_requires_workflow_tool(self) -> None:
        self.assertEqual(
            {"status": "available"},
            bridge._extract_structured('{"structured_output":{"status":"available"}}'),
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

    def test_wave_request_rejects_missing_runtime_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wave.json"
            path.write_text(json.dumps({"nodes": []}), encoding="utf-8")
            with self.assertRaisesRegex(bridge.BridgeError, "top-level fields"):
                bridge._load_wave_request(path)

    def test_graph_workflow_accepts_runtime_stringified_args(self) -> None:
        workflow = bridge.DEFAULT_GRAPH_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('typeof args === "string" ? JSON.parse(args) : args', workflow)
        self.assertIn("pipeline(workflowArgs.nodes", workflow)

    @mock.patch.object(bridge, "_invoke")
    @mock.patch.object(bridge, "_claude_version", return_value="2.1.214 (Claude Code)")
    @mock.patch.object(bridge, "_resolve_claude", return_value="C:/bin/claude.exe")
    def test_wave_prompt_requires_workflow_args_to_remain_an_object(
        self,
        _resolve: mock.Mock,
        _version: mock.Mock,
        invoke: mock.Mock,
    ) -> None:
        invoke.return_value = {
            "results": [{"node_result": {"node_id": "N-M1"}}]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wave.json"
            path.write_text(
                json.dumps(
                    {
                        "run_id": "RUN-TEST",
                        "plan_id": "PLAN-TEST",
                        "plan_revision": 1,
                        "plan_digest_sha256": "a" * 64,
                        "graph_revision": 1,
                        "batch_base_sha": "b" * 40,
                        "nodes": [
                            {
                                "node_kind": "mission",
                                "node_id": "N-M1",
                                "attempt_id": "ATT-1",
                                "mission_id": "M1",
                                "lease_id": "LEASE-1",
                                "branch_ref": "refs/heads/codex/test",
                                "worktree_path": "C:/repo/worktree",
                                "worker_prompt": "Do the task",
                            }
                        ],
                        "allowed_tools": ["Workflow"],
                        "permission_mode": "dontAsk",
                        "model": "sonnet",
                        "reasoning_effort": "high",
                    }
                ),
                encoding="utf-8",
            )
            bridge.run_wave(
                claude="claude",
                script=bridge.DEFAULT_GRAPH_WORKFLOW,
                request_path=path,
                cwd=Path.cwd(),
                timeout=30,
                max_budget_usd=0.1,
            )

        prompt = invoke.call_args.args[0][-1]
        self.assertIn("actual object, not as a JSON-encoded string", prompt)
        command = invoke.call_args.args[0]
        self.assertEqual("sonnet", command[command.index("--model") + 1])
        self.assertEqual("high", command[command.index("--effort") + 1])

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
            path = Path(directory) / "wave.json"
            request = {
                "run_id": "RUN-TEST",
                "plan_id": "PLAN-TEST",
                "plan_revision": 1,
                "plan_digest_sha256": "a" * 64,
                "graph_revision": 1,
                "batch_base_sha": "b" * 40,
                "nodes": [
                    {
                        "node_kind": "mission",
                        "node_id": "N-M1",
                        "attempt_id": "ATT-1",
                        "mission_id": "M1",
                        "lease_id": "LEASE-1",
                        "branch_ref": "refs/heads/codex/test",
                        "worktree_path": "C:/repo/worktree",
                        "worker_prompt": "Do the task",
                    }
                ],
                "allowed_tools": ["Workflow"],
                "permission_mode": "dontAsk",
                "model": "sonnet",
                "reasoning_effort": None,
            }
            path.write_text(json.dumps(request), encoding="utf-8")
            with self.assertRaisesRegex(bridge.BridgeError, "must match"):
                bridge.run_wave(
                    claude="claude",
                    script=bridge.DEFAULT_GRAPH_WORKFLOW,
                    request_path=path,
                    cwd=Path.cwd(),
                    timeout=30,
                    max_budget_usd=0.1,
                    model="opus",
                )


if __name__ == "__main__":
    unittest.main()

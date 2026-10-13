#!/usr/bin/env python3
"""Focused tests for versioned parent-owned role dispatch and launch receipts."""

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

from agent_launch_records import validate_launch_record_shape
from role_contract_fixtures import retain_failure
from agent_role_bindings import resolve_runtime_binding
from harness_manifest import validate_plan, validate_run
from harness_transition import ManifestError, _lease_worker, _record_launch_observation
from manifest_fixtures import (
    authorize_action,
    valid_plan,
    valid_run,
)
from select_ready_nodes import (
    _reviewer_tool_reasons,
    _runtime_binding,
    select_ready_nodes,
)


from role_contract_fixtures import (
    bridge_binding,
    refresh_plan_binding,
    configure_role_run,
    authorize_selection,
    native_reviewer_binding,
)


class AgentRoleContractTests(unittest.TestCase):
    def test_mixed_native_and_bridge_select_per_node_routes(self) -> None:
        plan = valid_plan()
        run = configure_role_run(plan, valid_run(plan))
        authorize_selection(run)
        errors = validate_plan(plan) + validate_run(plan, run)
        self.assertEqual([], errors)
        selection = select_ready_nodes(plan, run, manifest_already_validated=True)
        self.assertEqual(
            ["N-M1", "N-M2"],
            [item["node_id"] for item in selection["dispatchable_nodes"]],
        )
        routes = {
            item["node_id"]: item["runtime_binding"]["source"]
            for item in selection["dispatchable_nodes"]
        }
        self.assertEqual(
            {"N-M1": "external_bridge", "N-M2": "host"}, routes
        )
        self.assertEqual("external_bridge", selection["dispatchable_nodes"][0]["runtime_driver"])

    def test_external_bridge_requires_both_action_grants(self) -> None:
        for remove in ("spawn_subagents", "invoke_external_runtime"):
            with self.subTest(action=remove):
                plan = valid_plan()
                run = configure_role_run(plan, valid_run(plan))
                authorize_selection(run)
                run["authorizations"][remove] = {
                    "authorized": False,
                    "source": None,
                }
                if remove == "invoke_external_runtime":
                    run["authorizations"]["spawn_subagents"]["scope"]["mission_ids"] = ["*"]
                selection = select_ready_nodes(
                    plan, run, manifest_already_validated=True
                )
                self.assertNotIn(
                    "N-M1",
                    [item["node_id"] for item in selection["dispatchable_nodes"]],
                )
                self.assertIn(
                    "action_not_authorized",
                    next(
                        item["reason_codes"]
                        for item in selection["deferred_nodes"]
                        if item["node_id"] == "N-M1"
                    ),
                )

    def test_ui_mission_requires_frontend_role_binding(self) -> None:
        plan = valid_plan()
        run = configure_role_run(plan, valid_run(plan))
        mission = next(item for item in plan["missions"] if item["id"] == "M1")
        mission["required_skills"] = ["ui-design-builder", "frontend-design"]
        node = next(item for item in plan["graph"]["nodes"] if item["id"] == "N-M1")
        node["runtime"]["worker_role"] = "frontend_worker"
        refresh_plan_binding(plan, run)
        authorize_selection(run)
        selection = select_ready_nodes(plan, run, manifest_already_validated=True)
        self.assertIn(
            "mandatory_role_binding_missing",
            next(
                item["reason_codes"]
                for item in selection["deferred_nodes"]
                if item["node_id"] == "N-M1"
            ),
        )

    def test_empty_bindings_defer_only_mandatory_node(self) -> None:
        plan = valid_plan()
        run = configure_role_run(plan, valid_run(plan))
        run["runtime_capabilities"]["runtime_adapter"]["role_bindings"] = {}
        mission = next(item for item in plan["missions"] if item["id"] == "M1")
        mission["required_skills"] = ["ui-design-builder", "frontend-design"]
        node = next(item for item in plan["graph"]["nodes"] if item["id"] == "N-M1")
        node["runtime"]["worker_role"] = "frontend_worker"
        native_node = next(
            item for item in plan["graph"]["nodes"] if item["id"] == "N-M2"
        )
        native_node["runtime"].pop("worker_role")
        refresh_plan_binding(plan, run)
        authorize_selection(run)
        selection = select_ready_nodes(plan, run, manifest_already_validated=True)
        self.assertIn("N-M2", [item["node_id"] for item in selection["dispatchable_nodes"]])
        self.assertIn(
            "mandatory_role_binding_missing",
            next(
                item["reason_codes"]
                for item in selection["deferred_nodes"]
                if item["node_id"] == "N-M1"
            ),
        )

    def test_malformed_or_old_pin_rejects_role_fields(self) -> None:
        plan = valid_plan()
        run = configure_role_run(plan, valid_run(plan))
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"][
            "required_harness_version"
        ] = "0.57.0"
        errors = validate_plan(plan) + validate_run(plan, run)
        self.assertTrue(any("unknown keys: role_bindings" in item for item in errors))
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"][
            "required_harness_version"
        ] = "junk"
        errors = validate_plan(plan) + validate_run(plan, run)
        self.assertTrue(any("role_bindings" in item for item in errors))

    def test_malformed_worker_role_returns_validation_error(self) -> None:
        plan = valid_plan()
        node = next(item for item in plan["graph"]["nodes"] if item["id"] == "N-M1")
        node["runtime"]["worker_role"] = ["frontend_worker"]
        errors = validate_plan(plan)
        self.assertIn(
            "plan.graph.nodes[0].runtime.worker_role: must be a lowercase "
            "host-safe logical role id",
            errors,
        )

    def test_generic_undeclared_mission_retains_native_binding(self) -> None:
        plan = valid_plan()
        run = configure_role_run(plan, valid_run(plan))
        node = next(item for item in plan["graph"]["nodes"] if item["id"] == "N-M2")
        node["runtime"].pop("worker_role")
        binding = resolve_runtime_binding(node, run["runtime_capabilities"])
        self.assertIsNone(binding)
        binding = _runtime_binding(node, run["runtime_capabilities"])
        self.assertEqual(
            {
                "provider": "codex",
                "driver": "subagents",
                "source": "host",
                "model": None,
                "reasoning_effort": None,
                "option_source": "provider_default",
            },
            binding,
        )

    def test_lease_uses_reserved_bridge_axes_and_rejects_wildcard(self) -> None:
        plan = valid_plan()
        run = configure_role_run(plan, valid_run(plan))
        authorize_selection(run)
        selection = select_ready_nodes(plan, run, manifest_already_validated=True)
        directive = selection["dispatchable_nodes"][0]
        run["active_wave"].update(
            {
                "wave_id": "W1",
                "status": "active",
                "batch_base_sha": "a" * 40,
                "selected_missions": ["M1", "M2"],
            }
        )
        run["integration"]["batch_base_sha"] = "a" * 40
        for action in ("spawn_subagents", "invoke_external_runtime"):
            run["authorizations"][action]["scope"]["mission_ids"] = ["*"]
        run["mission_states"]["M1"].update({"phase": "ready", "base_sha": "a" * 40})
        run["observed"]["git"]["parent_head_sha"] = "a" * 40
        args = type(
            "LeaseArgs",
            (),
            {
                "mission_id": "M1",
                "node_id": directive["node_id"],
                "worker_id": "worker-1",
                "lease_id": "lease-1",
                "attempt_id": "attempt-1",
                "branch_ref": "refs/heads/codex/m1",
                "worktree_path": "C:/repo/worktrees/m1",
                "provider": "codex",
                "driver": "external_bridge",
                "model": "claude-opus-5-5",
                "reasoning_effort": "xhigh",
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "task_thread_id": None,
                "report_path": None,
            },
        )()
        with self.assertRaises(ManifestError):
            _lease_worker(plan, run, args)

    def test_launch_record_requires_revision_digest_and_positive_fallback(self) -> None:
        base = {
            "plan_revision": 1,
            "plan_digest_sha256": "f" * 64,
            "assignment_kind": "mission",
            "assignment_id": "lease-1",
            "node_id": "N-M1",
            "attempt_id": "attempt-2",
            "worker_id": "worker-2",
            "worker_role": "contract_writer",
            "resolved_role": "contract_writer",
            "source_sha": "a" * 40,
            "base_sha": None,
            "reviewed_sha": None,
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "requested_model": None,
            "requested_reasoning_effort": None,
            "model_provider": "claude_code",
            "model": "claude-opus-5-5",
            "reasoning_effort": "high",
            "session_id": "actual-session-2",
            "launch_observation": "parent observed bridge dispatch and terminal session creation",
            "host_observation": "parent host attestation for the exact bridge invocation",
        }
        self.assertEqual([], validate_launch_record_shape(base, "run.launch_records"))
        malformed_digest = copy.deepcopy(base)
        malformed_digest["plan_digest_sha256"] = "not-a-digest"
        self.assertTrue(validate_launch_record_shape(malformed_digest, "run.launch_records"))
        fallback = copy.deepcopy(base)
        fallback.update(
            {
                "fallback_from_role": "contract_writer",
                "availability": {
                    "classification": "model_provider_unavailable",
                    "observed_error": "bridge returned model provider unavailable for requested model",
                    "policy_source": "host policy v3",
                },
                "predecessor": {
                    "worker_id": "worker-1",
                    "stopped": True,
                    "stop_evidence": "process exit observed",
                },
                "partial_work": {"status": "reconciled", "evidence": "dirty tree retained"},
                "configured_fallback": {
                    "role": "contract_writer",
                    "model_provider": "claude_code",
                    "model": None,
                    "reasoning_effort": None,
                    "policy_source": "host policy v3",
                },
                "predecessor_attempt_id": "attempt-1",
            }
        )
        self.assertEqual([], validate_launch_record_shape(fallback, "run.launch_records"))
        bad_fallback = copy.deepcopy(fallback)
        bad_fallback["availability"]["classification"] = "timeout"
        self.assertTrue(validate_launch_record_shape(bad_fallback, "run.launch_records"))
        arbitrary = copy.deepcopy(fallback)
        arbitrary["availability"]["classification"] = "banana"
        self.assertTrue(validate_launch_record_shape(arbitrary, "run.launch_records"))

    def test_explicit_fallback_reservation_uses_declared_target(self) -> None:
        plan = valid_plan()
        run = configure_role_run(plan, valid_run(plan))
        authorize_selection(run)
        run["active_wave"].update(
            {
                "wave_id": "W1",
                "status": "active",
                "batch_base_sha": "a" * 40,
                "selected_missions": ["M1"],
            }
        )
        run["integration"]["batch_base_sha"] = "a" * 40
        run["mission_states"]["M1"].update({"phase": "ready", "base_sha": "a" * 40})
        for action, target in (
            ("spawn_subagents", "worker:worker-1"),
            ("invoke_external_runtime", "runtime:host-bridge-1"),
            ("create_local_worktrees", "worktree:C:/repo/worktrees/m1"),
            ("create_local_branches", "branch:refs/heads/codex/m1"),
            ("create_local_commits", "branch:refs/heads/codex/m1"),
        ):
            authorize_action(run, action, ["M1"], [target])
        primary_args = type(
            "LeaseArgs",
            (),
            {
                "mission_id": "M1", "node_id": "N-M1", "worker_id": "worker-1",
                "lease_id": "lease-1", "attempt_id": "attempt-1",
                "branch_ref": "refs/heads/codex/m1",
                "worktree_path": "C:/repo/worktrees/m1", "provider": "codex",
                "driver": "external_bridge", "model": "claude-opus-5-5",
                "reasoning_effort": "high", "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result", "task_thread_id": None,
                "report_path": None, "fallback_record": None,
            },
        )()
        _lease_worker(plan, run, primary_args)
        primary = run["workers"][0]
        run.setdefault("launch_records", []).append(
            {
                "plan_revision": 1,
                "plan_digest_sha256": run["plan"]["digest_sha256"],
                "assignment_kind": "mission",
                "assignment_id": "lease-1",
                "node_id": "N-M1",
                "attempt_id": "attempt-1",
                "worker_id": "worker-1",
                "worker_role": "contract_writer",
                "resolved_role": "contract_writer",
                "source_sha": "a" * 40,
                "base_sha": None,
                "reviewed_sha": None,
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "requested_model": "claude-opus-5-5",
                "requested_reasoning_effort": "high",
                "model_provider": "claude_code",
                "model": "claude-opus-5-5",
                "reasoning_effort": "high",
                "session_id": "primary-session-1",
                "launch_observation": "parent observed primary bridge dispatch",
                "host_observation": "parent host attestation for primary dispatch",
            }
        )
        primary["phase"] = "worker_failed"
        run["mission_states"]["M1"]["phase"] = "worker_failed"
        run["graph_state"]["node_states"]["N-M1"].update(
            {
                "phase": "failed",
                "last_outcome": "retryable_failure",
                "last_attempt_id": "attempt-1",
                "bound_worker_id": "worker-1",
            }
        )
        for action in ("spawn_subagents", "create_local_worktrees", "create_local_branches", "create_local_commits"):
            authorize_action(run, action, ["M1"], ["*"])
        evidence = {
            "fallback_from_role": "contract_writer",
            "availability": {
                "classification": "model_provider_unavailable",
                "observed_error": "provider returned requested model unavailable",
                "policy_source": "host fallback policy",
            },
            "predecessor": {
                "worker_id": "worker-1",
                "stopped": True,
                "stop_evidence": "parent confirmed worker process exit",
            },
            "partial_work": {"status": "none", "evidence": "clean exact-base worktree"},
            "configured_fallback": {
                "role": "backend_worker",
                "model_provider": "codex",
                "model": "gpt-6-sol",
                "reasoning_effort": "high",
                "policy_source": "host fallback policy",
            },
            "predecessor_attempt_id": "attempt-1",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            primary["failure_receipt"] = retain_failure(temp_dir, primary, evidence, session="primary-session-1")
            fallback_path = Path(temp_dir) / "fallback.json"
            fallback_path.write_text(json.dumps(evidence), encoding="utf-8")
            fallback_args = type(
                "LeaseArgs",
                (),
                {
                    "mission_id": "M1", "node_id": "N-M1", "worker_id": "worker-2",
                    "lease_id": "lease-2", "attempt_id": "attempt-2",
                    "branch_ref": "refs/heads/codex/m1-retry",
                    "worktree_path": "C:/repo/worktrees/m1-retry",
                    "provider": "codex", "driver": "subagents",
                    "model": "gpt-6-sol", "reasoning_effort": "high",
                    "worker_runtime": "subagent",
                    "workspace_mode": "parent_managed_worktree",
                    "completion_channel": "agent_result",
                    "task_thread_id": None, "report_path": None,
                    "fallback_record": fallback_path,
                },
            )()
            _lease_worker(plan, run, fallback_args)
            launch_args = type("LaunchArgs", (), {
                "assignment_kind": "mission", "assignment_id": "lease-2", "node_id": "N-M1",
                "worker_id": "worker-2", "attempt_id": "attempt-2", "model_provider": "codex",
                "model": "gpt-6-sol", "reasoning_effort": "high", "worker_session_id": "fallback-session-2",
                "launch_observation": "actual fallback launch", "host_observation": "parent observation",
                "fallback_record": fallback_path,
            })()
            _record_launch_observation(plan, run, launch_args)
            self.assertEqual("lease-2", run["launch_records"][-1]["assignment_id"])
        fallback = run["workers"][-1]
        self.assertEqual("contract_writer", fallback["runtime_binding"]["worker_role"])
        self.assertEqual("backend_worker", fallback["runtime_binding"]["resolved_role"])
        self.assertEqual("contract_writer", fallback["runtime_binding"]["fallback_from_role"])

    def test_reviewer_browser_capability_binds_bridge_probe(self) -> None:
        node = {
            "kind": "verifier",
            "review": {"required_tools": ["chrome_devtools"]},
        }
        runtime = {
            "reviewer_tools": {
                "chrome_devtools": {
                    "status": "available",
                    "provider": "claude_code",
                    "driver": "external_bridge",
                    "surface": "chromium",
                    "probe_scope": "reviewer_session",
                    "session_id": "wrong-probe",
                    "evidence": "bridge reviewer inspected DOM",
                }
            }
        }
        binding = bridge_binding("reviewer")
        binding["provider"] = "codex"
        binding["driver"] = "external_bridge"
        binding["workspace_mode"] = "shared_checkout"
        self.assertEqual(
            {"reviewer_tool_unavailable:chrome_devtools"},
            _reviewer_tool_reasons(node, runtime, binding),
        )

    def test_native_reviewer_browser_capability_binds_host(self) -> None:
        node = {
            "kind": "verifier",
            "review": {"required_tools": ["chrome_devtools"]},
        }
        runtime = {
            "reviewer_tools": {
                "chrome_devtools": {
                    "status": "available",
                    "provider": "codex",
                    "driver": "subagents",
                    "surface": "chromium",
                    "probe_scope": "reviewer_session",
                    "session_id": "native-probe-1",
                    "evidence": "native reviewer inspected DOM",
                }
            }
        }
        binding = native_reviewer_binding()
        binding["model_provider"] = "openai"
        binding["provider"] = "codex"
        binding["driver"] = "subagents"
        self.assertEqual(set(), _reviewer_tool_reasons(node, runtime, binding))

    def test_native_reviewer_browser_capability_rejects_identity_mismatch(self) -> None:
        node = {
            "kind": "verifier",
            "review": {"required_tools": ["chrome_devtools"]},
        }
        binding = native_reviewer_binding()
        binding["model_provider"] = "openai"
        binding["provider"] = "codex"
        binding["driver"] = "subagents"
        mismatches = (
            ("provider", "claude_code", "subagents"),
            ("driver", "codex", "external_bridge"),
        )
        for field, provider, driver in mismatches:
            with self.subTest(field=field):
                runtime = {
                    "reviewer_tools": {
                        "chrome_devtools": {
                            "status": "available",
                            "provider": provider,
                            "driver": driver,
                            "surface": "chromium",
                            "probe_scope": "reviewer_session",
                            "session_id": "native-probe-1",
                            "evidence": "native reviewer inspected DOM",
                        }
                    }
                }
                self.assertEqual(
                    {"reviewer_tool_unavailable:chrome_devtools"},
                    _reviewer_tool_reasons(node, runtime, binding),
                )

    def test_bridge_reviewer_browser_capability_rejects_provider_and_driver(self) -> None:
        node = {
            "kind": "verifier",
            "review": {"required_tools": ["chrome_devtools"]},
        }
        binding = bridge_binding("reviewer")
        binding["provider"] = "codex"
        binding["driver"] = "external_bridge"
        binding["workspace_mode"] = "shared_checkout"
        mismatches = (
            ("provider", "codex", "external_bridge"),
            ("driver", "claude_code", "subagents"),
        )
        for field, provider, driver in mismatches:
            with self.subTest(field=field):
                runtime = {
                    "reviewer_tools": {
                        "chrome_devtools": {
                            "status": "available",
                            "provider": provider,
                            "driver": driver,
                            "surface": "chromium",
                            "probe_scope": "reviewer_session",
                            "session_id": "bridge-probe-1",
                            "evidence": "bridge reviewer inspected DOM",
                        }
                    }
                }
                self.assertEqual(
                    {"reviewer_tool_unavailable:chrome_devtools"},
                    _reviewer_tool_reasons(node, runtime, binding),
                )

if __name__ == "__main__":
    unittest.main()

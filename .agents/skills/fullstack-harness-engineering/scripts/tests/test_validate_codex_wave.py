from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import plan_digest, validate_run  # noqa: E402
from select_ready_nodes import _runtime_binding  # noqa: E402
from test_graph_orchestration import authorize, valid_graph_plan, valid_graph_run  # noqa: E402
from validate_codex_wave import CodexWaveError, validate_codex_wave  # noqa: E402


class ValidateCodexWaveTests(unittest.TestCase):
    def canonical_wave(self) -> tuple[dict[str, object], dict[str, object]]:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["runtime"] = {
            "preferred_provider": "codex",
            "allowed_providers": ["codex"],
        }
        run = valid_graph_run(plan)
        run["schema_version"] = 9
        run["batch_gate_results"] = [
            {"id": item["id"], "status": "planned", "head_sha": None, "evidence": []}
            for item in plan["batch_verifiers"]
        ]
        run["final_gate_results"] = [
            {"id": item["id"], "status": "planned", "head_sha": None, "evidence": []}
            for item in plan["final_gates"]
        ]
        run["ui_evidence"] = []
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
        digest = plan_digest(plan)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
            }
        )
        run["runtime_capabilities"]["permission_boundary"] = {
            "selected_mode": "named_profile",
            "profile_name": "workspace-write",
            "approval_policy": "never",
            "filesystem_scope": "workspace",
            "network_scope": "filtered",
            "local_binding": "allowed",
            "worker_inheritance": "inherited",
            "status": "ready",
        }
        run["runtime_capabilities"]["runtime_adapter"].update(
            {
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
        )
        run["graph_state"]["node_states"]["N-M1"].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": "ATT-M1-1",
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
        run["active_wave"].update(
            {
                "wave_id": "WAVE-1",
                "status": "active",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "batch_base_sha": run["integration"]["batch_base_sha"],
                "selected_missions": ["M1"],
            }
        )
        binding = _runtime_binding(plan["graph"]["nodes"][0], run["runtime_capabilities"])
        self.assertIsNotNone(binding)
        run["workers"] = [
            {
                "worker_id": "W-M1",
                "mission_id": "M1",
                "lease_id": "LEASE-M1-1",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "batch_base_sha": run["integration"]["batch_base_sha"],
                "worker_runtime": "subagent",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "agent_result",
                "task_thread_id": None,
                "worktree_path": "C:/repo/worktrees/W-M1",
                "branch_ref": "refs/heads/codex/W-M1",
                "report_path": None,
                "phase": "worker_running",
                "worker_head_sha": None,
                "runtime_binding": binding,
            }
        ]
        for action, target in (
            ("invoke_external_runtime", "runtime:codex"),
            ("spawn_subagents", "worker:W-M1"),
            ("create_app_managed_worktrees", "worktree:C:/repo/worktrees/W-M1"),
            ("create_local_branches", "branch:refs/heads/codex/W-M1"),
            ("create_local_commits", "branch:refs/heads/codex/W-M1"),
        ):
            authorize(run, action, ["M1"], target)
        return plan, run

    def test_derives_canonical_workflow_args(self) -> None:
        plan, run = self.canonical_wave()
        self.assertEqual([], validate_run(plan, run))

        args = validate_codex_wave(plan, run, ["N-M1"])

        self.assertEqual("mission_write", args["tool_profile"])
        self.assertEqual(None, args["model"])
        self.assertEqual("ATT-M1-1", args["nodes"][0]["attempt_id"])
        self.assertEqual("LEASE-M1-1", args["nodes"][0]["lease_id"])
        self.assertEqual(["M1/T01", "M1/T02"], args["nodes"][0]["task_ids"])

    def test_rejects_stale_attempt_lease_base_and_worker_binding(self) -> None:
        plan, run = self.canonical_wave()
        cases = [
            ("attempt", lambda value: value["graph_state"]["node_states"]["N-M1"].update({"last_attempt_id": None})),
            ("lease", lambda value: value["mission_states"]["M1"].update({"lease_id": "STALE"})),
            ("base", lambda value: value["active_wave"].update({"batch_base_sha": "b" * 40})),
            ("binding", lambda value: value["workers"][0]["runtime_binding"].update({"driver": "subagents"})),
            ("unsafe_model", lambda value: value["workers"][0]["runtime_binding"].update({"model": "gpt --effort max"})),
        ]
        for name, mutate in cases:
            with self.subTest(name=name):
                invalid = copy.deepcopy(run)
                mutate(invalid)
                with self.assertRaises(CodexWaveError):
                    validate_codex_wave(plan, invalid, ["N-M1"])

    def test_requires_exact_wave_authorizations(self) -> None:
        plan, run = self.canonical_wave()
        for action in (
            "invoke_external_runtime",
            "spawn_subagents",
            "create_app_managed_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            with self.subTest(action=action):
                invalid = copy.deepcopy(run)
                invalid["authorizations"][action]["scope"]["targets"] = ["*"]
                with self.assertRaises(CodexWaveError):
                    validate_codex_wave(plan, invalid, ["N-M1"])

    def test_preflight_rejects_invoke_only_authorization(self) -> None:
        plan, run = self.canonical_wave()
        run["active_wave"]["status"] = "idle"
        run["graph_state"]["node_states"]["N-M1"].update(
            {"phase": "ready", "attempts": 0, "last_attempt_id": None, "bound_worker_id": None}
        )
        run["mission_states"]["M1"].update(
            {"phase": "ready", "lease_id": None, "lease_plan_revision": None,
             "lease_plan_digest_sha256": None, "worker_id": None, "base_sha": None}
        )
        run["workers"] = []
        authorize(run, "spawn_subagents", ["M1"], "worker:preallocation")
        self.assertIsInstance(validate_codex_wave(plan, run, ["N-M1"], mode="preflight"), dict)
        run["authorizations"]["spawn_subagents"] = {"authorized": False, "source": None}
        with self.assertRaises(CodexWaveError):
            validate_codex_wave(plan, run, ["N-M1"], mode="preflight")


if __name__ == "__main__":
    unittest.main()

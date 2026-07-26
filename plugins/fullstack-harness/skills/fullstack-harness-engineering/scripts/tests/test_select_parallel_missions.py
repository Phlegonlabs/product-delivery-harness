from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import AUTHORIZATION_KEYS, plan_digest, validate_plan, validate_run
from select_parallel_missions import SelectionError, select_parallel_missions


SHA = "a" * 40


def verifier(verifier_id: str) -> dict[str, object]:
    return {
        "id": verifier_id,
        "cwd": ".",
        "argv": ["python3", "-m", "unittest"],
        "pass_signal": "exit_code_0",
    }


def mission(
    mission_id: str,
    *,
    priority: int,
    merge_rank: int,
    depends_on: list[str] | None = None,
    write_scope: str | None = None,
) -> dict[str, object]:
    scope = write_scope or f"src/{mission_id.lower()}/**"
    return {
        "id": mission_id,
        "alias": f"mission-{mission_id.lower()}",
        "objective": f"Deliver {mission_id}",
        "priority": priority,
        "merge_rank": merge_rank,
        "depends_on": list(depends_on or []),
        "trace_ids": ["REQ-001"],
        "write_scope": [scope],
        "deny_scope": ["docs/goal/PLAN.md", "docs/goal/RUN.md"],
        "resource_inventory_complete": True,
        "serialized_resources": [],
        "runtime_resources": [],
        "worktree_eligible": True,
        "required_skills": [],
        "stop_conditions": ["contract changes"],
        "worker_verifiers": [verifier(f"worker-{mission_id.lower()}")],
        "integration_verifiers": [verifier(f"integration-{mission_id.lower()}")],
        "tasks": [
            {
                "id": f"{mission_id}/T01",
                "alias": f"task-{mission_id.lower()}",
                "objective": f"Implement {mission_id}",
                "acceptance_matrix": ["focused behavior passes"],
                "trace_ids": ["REQ-001"],
                "depends_on": [],
                "parent_task": None,
                "legacy_task_ids": [],
                "replaced_by": [],
                "split_reason": None,
                "refinement_generation": 0,
                "write_scope": [scope],
                "verifiers": [verifier(f"task-{mission_id.lower()}")],
            }
        ],
    }


def make_plan(missions: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": 2,
        "plan_id": "PLAN-SELECTOR",
        "revision": 1,
        "objective": "Select safe deterministic waves",
        "max_parallel_workers": 3,
        "sources": [
            {
                "id": "SRC-001",
                "kind": "prd",
                "location": "docs/product/PRD.md",
                "owner": "team",
                "status": "frozen",
                "notes": "canonical",
            }
        ],
        "traces": [
            {
                "id": "REQ-001",
                "source_ids": ["SRC-001"],
                "priority": "must",
                "requirement": "Deliver the selected work",
                "disposition": "planned",
                "rationale": None,
            }
        ],
        "ui_surfaces": [],
        "risks": [],
        "batch_verifiers": [verifier("batch")],
        "final_gates": [verifier("final")],
        "missions": missions,
    }


def authorization(run_id: str, mission_ids: list[str]) -> dict[str, object]:
    return {
        "authorized": True,
        "source": "user-message-1",
        "scope": {
            "run_id": run_id,
            "mission_ids": mission_ids,
            "targets": ["*"],
        },
        "expires_when": "run_complete",
    }


def make_run(plan: dict[str, object]) -> dict[str, object]:
    run_id = "RUN-SELECTOR"
    mission_ids = [item["id"] for item in plan["missions"]]
    authorizations = {
        key: {"authorized": False, "source": None} for key in AUTHORIZATION_KEYS
    }
    for key in (
        "spawn_subagents",
        "create_local_worktrees",
        "create_local_branches",
        "create_local_commits",
    ):
        authorizations[key] = authorization(run_id, mission_ids)

    mission_states = {
        item["id"]: {
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
        for item in plan["missions"]
    }
    task_states = {
        task["id"]: {
            "phase": "queued",
            "attempts": 0,
            "commit_sha": None,
            "verifier_status": "planned",
            "blockers": [],
            "refinement_request": None,
        }
        for item in plan["missions"]
        for task in item["tasks"]
    }
    digest = plan_digest(plan)
    return {
        "schema_version": 3,
        "run_id": run_id,
        "plan": {
            "id": plan["plan_id"],
            "revision": plan["revision"],
            "digest_sha256": digest,
        },
        "status": "running",
        "intent": "plan-then-execute",
        "plan_readiness": "ready",
        "execution_authorized": True,
        "execution_authorization_source": "user-message-1",
        "execution_authorization_scope": {
            "run_id": run_id,
            "mission_ids": mission_ids,
            "expires_when": "run_complete",
        },
        "authorizations": authorizations,
        "runtime_capabilities": {
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": 3,
            "platform_lifecycle": {
                "owner": "parent",
                "automatic_retention_cleanup_possible": False,
                "durable_branch_required_before_unique_work": True,
            },
        },
        "observed": {
            "captured_at": "2026-07-13T00:00:00Z",
            "git": {
                "parent_branch": "codex/integration",
                "parent_head_sha": SHA,
                "parent_dirty": False,
                "worktrees": [],
            },
            "runtime": {
                "available_worker_slots": 3,
                "isolation_capacity": 3,
                "completion_channel_available": True,
            },
        },
        "integration": {
            "branch": "codex/integration",
            "batch_base_sha": SHA,
            "integration_head_sha": SHA,
        },
        "landing": {
            "mode": "pull_request",
            "remote": "origin",
            "head_branch": "codex/integration",
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
        "mission_states": mission_states,
        "task_states": task_states,
        "active_wave": {
            "wave_id": None,
            "status": "idle",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "batch_base_sha": SHA,
            "selected_missions": [],
            "deferred_missions": [],
            "conflict_edges": [],
        },
        "workers": [],
        "attempt_log": [],
    }


def configure_app_task_fanout(
    run: dict[str, object], mission_ids: list[str]
) -> None:
    run_id = run["run_id"]
    run["runtime_capabilities"] = {
        "worker_runtime": "app_task",
        "workspace_mode": "app_managed_worktree",
        "completion_channel": "thread_poll",
        "max_parallel_workers": 3,
        "nested_subagents": {
            "available": True,
            "max_depth": 1,
            "max_children_per_worker": 3,
            "allowed_roles": ["tester", "explorer", "reviewer", "researcher"],
            "write_policy": "read_only",
            "completion_channel": "agent_result",
        },
        "platform_lifecycle": {
            "owner": "app",
            "automatic_retention_cleanup_possible": True,
            "durable_branch_required_before_unique_work": True,
        },
    }
    for key in (
        "spawn_subagents",
        "create_user_owned_tasks",
        "create_app_managed_worktrees",
        "create_local_branches",
        "create_local_commits",
    ):
        run["authorizations"][key] = authorization(run_id, mission_ids)


def upgrade_to_schema_v6(
    run: dict[str, object], provider: str, available_drivers: list[str]
) -> None:
    run["schema_version"] = 6
    run["runtime_capabilities"]["runtime_adapter"] = {
        "provider": provider,
        "available_drivers": available_drivers,
        "detection_source": "observed",
    }
    run["observed"]["git"]["parent_worktree_path"] = "C:/repo/fullstack-goal-dev"
    run["landing"]["auto_merge_requested"] = False
    run["landing"]["auto_merge_head_sha"] = None
    run["post_merge_cleanup"] = {
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
    }


def manifest_markdown(heading: str, wrapper: str, value: dict[str, object]) -> str:
    encoded = json.dumps({wrapper: value}, sort_keys=True, indent=2)
    return f"# Harness fixture\n\n{heading}\n\n```json\n{encoded}\n```\n"


class SelectorTests(unittest.TestCase):
    def test_graph_plan_versions_must_use_ready_node_selector(self) -> None:
        for schema_version in (4, 5):
            with self.subTest(schema_version=schema_version):
                plan = make_plan([mission("M1", priority=10, merge_rank=10)])
                run = make_run(plan)
                plan["schema_version"] = schema_version
                with self.assertRaisesRegex(
                    SelectionError,
                    "schema v4/v5 typed graphs must use select_ready_nodes.py",
                ):
                    select_parallel_missions(plan, run)

    def assert_valid(self, plan: dict[str, object], run: dict[str, object]) -> None:
        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_run(plan, run))

    def test_orders_by_topology_priority_merge_rank_and_id(self) -> None:
        plan = make_plan(
            [
                mission("M3", priority=999, merge_rank=1, depends_on=["M0"]),
                mission("M2", priority=20, merge_rank=30),
                mission("M1", priority=20, merge_rank=10),
                mission("M0", priority=1, merge_rank=1),
            ]
        )
        run = make_run(plan)
        run["mission_states"]["M0"].update(
            phase="integrated", integration_gate="PASS", integrated_sha=SHA
        )
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)

        self.assertEqual(["M1", "M2", "M3"], result["candidate_order"])
        self.assertEqual(["M1", "M2", "M3"], result["selected_missions"])

    def test_app_task_wave_emits_thread_launch_directives_with_nested_policy(self) -> None:
        plan = make_plan(
            [
                mission("M2", priority=10, merge_rank=20),
                mission("M1", priority=20, merge_rank=10),
            ]
        )
        run = make_run(plan)
        configure_app_task_fanout(run, ["M1", "M2"])
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)

        self.assertEqual(["M1", "M2"], result["selected_missions"])
        self.assertEqual(
            [
                {
                    "mission_id": mission_id,
                    "launch_kind": "create_thread",
                    "worker_runtime": "app_task",
                    "workspace_mode": "app_managed_worktree",
                    "completion_channel": "thread_poll",
                    "required_actions": [
                        "create_user_owned_tasks",
                        "spawn_subagents",
                        "create_app_managed_worktrees",
                        "create_local_branches",
                        "create_local_commits",
                    ],
                    "nested_subagent_policy": {
                        "mode": "enabled_read_only",
                        "max_children": 3,
                        "allowed_roles": [
                            "explorer",
                            "researcher",
                            "reviewer",
                            "tester",
                        ],
                        "write_policy": "read_only",
                        "completion_channel": "agent_result",
                    },
                    "worker_prompt_template": "assets/templates/WORKER_GOAL.template.md",
                }
                for mission_id in ("M1", "M2")
            ],
            result["launch_directives"],
        )

    def test_schema_v6_routes_claude_wave_to_one_dynamic_workflow(self) -> None:
        plan = make_plan(
            [
                mission("M2", priority=10, merge_rank=20),
                mission("M1", priority=20, merge_rank=10),
            ]
        )
        run = make_run(plan)
        upgrade_to_schema_v6(
            run,
            "claude_code",
            ["sequential_parent", "subagents", "dynamic_workflow"],
        )
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)

        self.assertEqual(
            {
                "provider": "claude_code",
                "driver": "dynamic_workflow",
                "detection_source": "observed",
            },
            result["runtime_route"],
        )
        self.assertEqual(
            {
                "launch_kind": "run_dynamic_workflow",
                "mission_ids": ["M1", "M2"],
                "script_path": "assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js",
                "args_source": "accepted_wave",
            },
            result["wave_launch"],
        )
        for directive in result["launch_directives"]:
            self.assertEqual("run_dynamic_workflow", directive["launch_kind"])
            self.assertEqual("claude_code", directive["runtime_provider"])
            self.assertEqual("dynamic_workflow", directive["runtime_driver"])
            self.assertEqual("flat_wave", directive["workflow_policy"]["mode"])
            self.assertEqual(
                "assets/templates/CLAUDE_DYNAMIC_WORKFLOW.template.js",
                directive["workflow_policy"]["script_path"],
            )
            self.assertEqual("not_applicable", directive["nested_subagent_policy"]["mode"])

    def test_schema_v6_claude_falls_back_to_direct_subagents(self) -> None:
        plan = make_plan([mission("M1", priority=20, merge_rank=10)])
        run = make_run(plan)
        upgrade_to_schema_v6(
            run,
            "claude_code",
            ["subagents", "sequential_parent"],
        )
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)

        self.assertEqual("subagents", result["runtime_route"]["driver"])
        self.assertEqual("spawn_subagent", result["launch_directives"][0]["launch_kind"])
        self.assertNotIn("wave_launch", result)

    def test_schema_v6_routes_codex_wave_to_app_threads(self) -> None:
        plan = make_plan([mission("M1", priority=20, merge_rank=10)])
        run = make_run(plan)
        configure_app_task_fanout(run, ["M1"])
        upgrade_to_schema_v6(
            run,
            "codex",
            ["sequential_parent", "subagents", "app_threads"],
        )
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)

        self.assertEqual("app_threads", result["runtime_route"]["driver"])
        self.assertEqual("create_thread", result["launch_directives"][0]["launch_kind"])
        self.assertEqual("codex", result["launch_directives"][0]["runtime_provider"])

    def test_app_task_wave_requires_nested_subagent_authorization(self) -> None:
        plan = make_plan([mission("M1", priority=20, merge_rank=10)])
        run = make_run(plan)
        configure_app_task_fanout(run, ["M1"])
        run["authorizations"]["spawn_subagents"] = {
            "authorized": False,
            "source": None,
        }
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)

        self.assertEqual([], result["selected_missions"])
        self.assertEqual([], result["launch_directives"])
        self.assertEqual(
            ["action_not_authorized"],
            result["deferred_missions"][0]["reason_codes"],
        )

    def test_app_task_wave_uses_no_edit_handshake_when_capability_is_unobserved(self) -> None:
        plan = make_plan([mission("M1", priority=20, merge_rank=10)])
        run = make_run(plan)
        configure_app_task_fanout(run, ["M1"])
        run["runtime_capabilities"]["nested_subagents"]["available"] = False
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)

        policy = result["launch_directives"][0]["nested_subagent_policy"]
        self.assertEqual("capability_handshake", policy["mode"])
        self.assertEqual(0, policy["max_children"])
        self.assertEqual([], policy["allowed_roles"])

    def test_static_edges_include_nonready_missions_but_unary_codes_do_not(self) -> None:
        plan = make_plan(
            [
                mission("M1", priority=20, merge_rank=10, write_scope="src/shared/**"),
                mission("M2", priority=10, merge_rank=20, write_scope="src/shared/file.py"),
            ]
        )
        run = make_run(plan)
        run["mission_states"]["M2"]["phase"] = "blocked"
        run["mission_states"]["M2"]["blockers"] = ["waiting for contract"]
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)

        self.assertEqual(
            [{"left": "M1", "right": "M2", "reason_codes": ["scope_overlap"]}],
            result["conflict_edges"],
        )
        deferred = {item["mission_id"]: item for item in result["deferred_missions"]}
        self.assertEqual(
            ["blocker_present", "mission_phase_not_ready"],
            deferred["M2"]["reason_codes"],
        )
        self.assertNotIn("blocker_present", result["conflict_edges"][0]["reason_codes"])

    def test_worker_passed_dependency_does_not_unlock_downstream(self) -> None:
        plan = make_plan(
            [
                mission("M1", priority=20, merge_rank=10),
                mission("M2", priority=10, merge_rank=20, depends_on=["M1"]),
            ]
        )
        run = make_run(plan)
        run["mission_states"]["M1"].update(
            phase="worker_passed",
            lease_id="LEASE-1",
            lease_plan_revision=1,
            lease_plan_digest_sha256=plan_digest(plan),
            worker_id="W1",
            base_sha=SHA,
            head_sha=SHA,
        )
        run["workers"].append(
            {
                "worker_id": "W1",
                "mission_id": "M1",
                "lease_id": "LEASE-1",
                "plan_revision": 1,
                "plan_digest_sha256": plan_digest(plan),
                "batch_base_sha": SHA,
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "task_thread_id": None,
                "worktree_path": "/tmp/worktree-m1",
                "branch_ref": "codex/m1",
                "report_path": None,
                "phase": "worker_passed",
                "worker_head_sha": SHA,
            }
        )
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)
        deferred = {item["mission_id"]: item for item in result["deferred_missions"]}

        self.assertEqual(["mission_phase_not_ready"], deferred["M1"]["reason_codes"])
        self.assertEqual(["dependency_not_integrated"], deferred["M2"]["reason_codes"])

    def test_budget_is_minimum_and_ready_remainder_is_over_budget(self) -> None:
        plan = make_plan(
            [
                mission("M1", priority=30, merge_rank=10),
                mission("M2", priority=20, merge_rank=20),
                mission("M3", priority=10, merge_rank=30),
            ]
        )
        run = make_run(plan)
        run["runtime_capabilities"]["max_parallel_workers"] = 2
        self.assert_valid(plan, run)

        result = select_parallel_missions(
            plan, run, runtime_slots=3, isolation_capacity=3
        )

        self.assertEqual(2, result["effective_worker_budget"])
        self.assertEqual(["M1", "M2"], result["selected_missions"])
        deferred = {item["mission_id"]: item for item in result["deferred_missions"]}
        self.assertEqual(["over_budget"], deferred["M3"]["reason_codes"])

    def test_semantic_reordering_is_byte_stable_and_has_no_timestamp(self) -> None:
        plan = make_plan(
            [
                mission("M2", priority=10, merge_rank=20),
                mission("M1", priority=20, merge_rank=10),
            ]
        )
        run = make_run(plan)
        first = select_parallel_missions(plan, run)

        reordered_plan = copy.deepcopy(plan)
        reordered_plan["missions"].reverse()
        reordered_plan["traces"][0]["source_ids"].reverse()
        reordered_run = copy.deepcopy(run)
        reordered_run["plan"]["digest_sha256"] = plan_digest(reordered_plan)
        reordered_run["active_wave"]["plan_digest_sha256"] = plan_digest(reordered_plan)
        reordered_run["mission_states"] = dict(
            reversed(list(reordered_run["mission_states"].items()))
        )
        self.assert_valid(reordered_plan, reordered_run)
        second = select_parallel_missions(reordered_plan, reordered_run)

        encoded_first = json.dumps(first, sort_keys=True, separators=(",", ":"))
        encoded_second = json.dumps(second, sort_keys=True, separators=(",", ":"))
        self.assertEqual(encoded_first, encoded_second)
        self.assertNotIn("timestamp", encoded_first.lower())

    def test_execution_scope_is_launch_gated_per_mission(self) -> None:
        plan = make_plan(
            [
                mission("M1", priority=20, merge_rank=10),
                mission("M2", priority=10, merge_rank=20),
            ]
        )
        run = make_run(plan)
        run["execution_authorization_scope"]["mission_ids"] = ["M1"]
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)
        deferred = {item["mission_id"]: item for item in result["deferred_missions"]}

        self.assertEqual(["M1"], result["selected_missions"])
        self.assertEqual(
            ["execution_not_authorized"], deferred["M2"]["reason_codes"]
        )
        self.assertEqual(
            {"mission_id", "reason_codes", "conflicts_with"},
            set(deferred["M2"]),
        )

    def test_mission_id_is_not_a_concrete_action_target(self) -> None:
        plan = make_plan([mission("M1", priority=10, merge_rank=10)])
        run = make_run(plan)
        run["authorizations"]["create_local_branches"]["scope"]["targets"] = [
            "branch:M1"
        ]
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)

        self.assertEqual([], result["selected_missions"])
        self.assertEqual(
            [
                {
                    "mission_id": "M1",
                    "reason_codes": ["action_not_authorized"],
                    "conflicts_with": [],
                }
            ],
            result["deferred_missions"],
        )

    def test_conflict_reason_precedes_over_budget(self) -> None:
        plan = make_plan(
            [
                mission("M1", priority=30, merge_rank=10, write_scope="src/shared/**"),
                mission("M2", priority=20, merge_rank=20, write_scope="src/shared/file.py"),
                mission("M3", priority=10, merge_rank=30),
            ]
        )
        run = make_run(plan)
        run["runtime_capabilities"]["max_parallel_workers"] = 1
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)
        deferred = {item["mission_id"]: item for item in result["deferred_missions"]}

        self.assertEqual(["M1"], result["selected_missions"])
        self.assertEqual(["scope_overlap"], deferred["M2"]["reason_codes"])
        self.assertEqual(["M1"], deferred["M2"]["conflicts_with"])
        self.assertEqual(["over_budget"], deferred["M3"]["reason_codes"])
        self.assertEqual([], deferred["M3"]["conflicts_with"])

    def test_active_wave_blocks_a_new_proposal(self) -> None:
        plan = make_plan([mission("M1", priority=10, merge_rank=10)])
        run = make_run(plan)
        run["active_wave"]["status"] = "active"
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)

        self.assertEqual([], result["selected_missions"])
        self.assertEqual([], result["ready_frontier"])
        self.assertEqual(
            [
                {
                    "mission_id": "M1",
                    "reason_codes": ["blocker_present"],
                    "conflicts_with": [],
                }
            ],
            result["deferred_missions"],
        )

    def test_unready_permission_boundary_blocks_launch(self) -> None:
        plan = make_plan([mission("M1", priority=10, merge_rank=10)])
        run = make_run(plan)
        run["runtime_capabilities"]["permission_boundary"] = {
            "selected_mode": "ask_for_approval",
            "profile_name": None,
            "approval_policy": "on-request",
            "filesystem_scope": "workspace",
            "network_scope": "filtered",
            "local_binding": "blocked",
            "worker_inheritance": "inherited",
            "status": "may_prompt",
        }
        self.assert_valid(plan, run)

        result = select_parallel_missions(plan, run)

        self.assertEqual([], result["selected_missions"])
        self.assertEqual(
            ["permission_boundary_not_ready"],
            result["deferred_missions"][0]["reason_codes"],
        )

    def test_named_cli_outputs_canonical_json_without_mutating_inputs(self) -> None:
        plan = make_plan([mission("M1", priority=10, merge_rank=10)])
        run = make_run(plan)
        plan_text = manifest_markdown(
            "## Harness Plan Manifest", "harness_plan", plan
        )
        run_text = manifest_markdown("## Harness Run State", "harness_run", run)

        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "PLAN.md"
            run_path = Path(directory) / "RUN.md"
            plan_path.write_text(plan_text, encoding="utf-8")
            run_path.write_text(run_text, encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "select_parallel_missions.py"),
                    "--plan",
                    str(plan_path),
                    "--run",
                    str(run_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual("", completed.stderr)
            decoded = json.loads(completed.stdout)
            self.assertEqual(
                json.dumps(decoded, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
                completed.stdout,
            )
            self.assertNotIn("timestamp", completed.stdout.lower())
            self.assertEqual(plan_text, plan_path.read_text(encoding="utf-8"))
            self.assertEqual(run_text, run_path.read_text(encoding="utf-8"))

    def test_cli_manifest_error_is_canonical_json(self) -> None:
        plan = make_plan([mission("M1", priority=10, merge_rank=10)])
        run = make_run(plan)
        run_text = manifest_markdown("## Harness Run State", "harness_run", run)

        with tempfile.TemporaryDirectory() as directory:
            plan_path = Path(directory) / "PLAN.md"
            run_path = Path(directory) / "RUN.md"
            plan_path.write_text("# Missing canonical manifest\n", encoding="utf-8")
            run_path.write_text(run_text, encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "select_parallel_missions.py"),
                    "--plan",
                    str(plan_path),
                    "--run",
                    str(run_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, completed.returncode)
        self.assertEqual("", completed.stderr)
        decoded = json.loads(completed.stdout)
        self.assertEqual("ERROR", decoded["status"])
        self.assertEqual(1, len(decoded["errors"]))
        self.assertIn("expected exactly one", decoded["errors"][0])
        self.assertEqual(
            json.dumps(decoded, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
            completed.stdout,
        )


if __name__ == "__main__":
    unittest.main()

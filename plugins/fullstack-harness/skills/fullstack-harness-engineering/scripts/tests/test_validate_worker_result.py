from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import (  # noqa: E402
    AUTHORIZATION_KEYS,
    ManifestError,
    load_worker_result,
    plan_digest,
    validate_plan,
    validate_run,
)
import validate_worker_result as subject  # noqa: E402


BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
BRANCH_REF = "refs/heads/codex/worker-m1"
CHANGED_FILE = "src/m1/feature.py"


def verifier(verifier_id: str) -> dict[str, object]:
    return {
        "id": verifier_id,
        "cwd": ".",
        "argv": ["python3", "-m", "unittest"],
        "pass_signal": "exit_code_0",
    }


def make_plan() -> dict[str, object]:
    return {
        "schema_version": 2,
        "plan_id": "PLAN_TEST",
        "revision": 1,
        "objective": "Deliver the test mission with a verified result.",
        "max_parallel_workers": 3,
        "sources": [
            {
                "id": "SRC1",
                "kind": "prd",
                "location": "docs/requirements.md",
                "owner": "test",
                "status": "frozen",
                "notes": "test fixture",
            }
        ],
        "traces": [
            {
                "id": "REQ1",
                "source_ids": ["SRC1"],
                "priority": "must",
                "requirement": "Implement the bounded behavior.",
                "disposition": "planned",
                "rationale": None,
            }
        ],
        "ui_surfaces": [],
        "risks": [],
        "batch_verifiers": [verifier("batch")],
        "final_gates": [verifier("final")],
        "missions": [
            {
                "id": "M1",
                "alias": "mission-one",
                "objective": "Implement mission one.",
                "priority": 100,
                "merge_rank": 10,
                "depends_on": [],
                "trace_ids": ["REQ1"],
                "write_scope": ["src/m1/**"],
                "deny_scope": ["docs/goal/PLAN.md", "docs/goal/RUN.md"],
                "resource_inventory_complete": True,
                "serialized_resources": [],
                "runtime_resources": [],
                "worktree_eligible": True,
                "stop_conditions": ["scope escape"],
                "worker_verifiers": [verifier("mission-focused")],
                "integration_verifiers": [verifier("mission-integration")],
                "tasks": [
                    {
                        "id": "M1/T01",
                        "alias": "task-one",
                        "objective": "Implement the focused behavior.",
                        "acceptance_matrix": ["focused behavior passes"],
                        "trace_ids": ["REQ1"],
                        "depends_on": [],
                        "parent_task": None,
                        "legacy_task_ids": [],
                        "replaced_by": [],
                        "split_reason": None,
                        "refinement_generation": 0,
                        "write_scope": ["src/m1/**"],
                        "verifiers": [verifier("task-focused")],
                    }
                ],
            }
        ],
    }


def authorization(
    action: str,
    *,
    enabled: bool,
    target: str = "*",
) -> dict[str, object]:
    if not enabled:
        return {"authorized": False, "source": None}
    return {
        "authorized": True,
        "source": "test user authorization",
        "scope": {
            "run_id": "RUN_TEST",
            "mission_ids": ["M1"],
            "targets": [target],
        },
        "expires_when": "run_complete",
    }


def make_run(plan: dict[str, object]) -> dict[str, object]:
    digest = plan_digest(plan)
    authorizations = {
        action: authorization(action, enabled=False) for action in AUTHORIZATION_KEYS
    }
    authorizations["create_local_commits"] = authorization(
        "create_local_commits", enabled=True, target=f"branch:{BRANCH_REF}"
    )
    return {
        "schema_version": 3,
        "run_id": "RUN_TEST",
        "plan": {
            "id": "PLAN_TEST",
            "revision": 1,
            "digest_sha256": digest,
        },
        "status": "running",
        "intent": "execute-ready-plan",
        "plan_readiness": "ready",
        "execution_authorized": True,
        "execution_authorization_source": "test user authorization",
        "execution_authorization_scope": {
            "run_id": "RUN_TEST",
            "mission_ids": ["M1"],
            "expires_when": "run_complete",
        },
        "authorizations": authorizations,
        "runtime_capabilities": {
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": 1,
            "platform_lifecycle": {
                "owner": "parent",
                "automatic_retention_cleanup_possible": False,
                "durable_branch_required_before_unique_work": True,
            },
        },
        "observed": {
            "captured_at": "test-observation",
            "git": {
                "parent_branch": "refs/heads/codex/integration",
                "parent_head_sha": BASE_SHA,
                "parent_dirty": False,
                "worktrees": [
                    {
                        "path": "/tmp/worker-m1",
                        "branch_ref": BRANCH_REF,
                        "head_sha": HEAD_SHA,
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
        },
        "integration": {
            "branch": "refs/heads/codex/integration",
            "batch_base_sha": BASE_SHA,
            "integration_head_sha": BASE_SHA,
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
        "mission_states": {
            "M1": {
                "phase": "worker_running",
                "lease_id": "LEASE1",
                "lease_plan_revision": 1,
                "lease_plan_digest_sha256": digest,
                "worker_id": "W1",
                "base_sha": BASE_SHA,
                "head_sha": None,
                "integration_gate": "planned",
                "integrated_sha": None,
                "blockers": [],
                "report_path": None,
            }
        },
        "task_states": {
            "M1/T01": {
                "phase": "running",
                "attempts": 1,
                "commit_sha": None,
                "verifier_status": "planned",
                "blockers": [],
                "refinement_request": None,
            }
        },
        "active_wave": {
            "wave_id": "B01",
            "status": "active",
            "plan_revision": 1,
            "plan_digest_sha256": digest,
            "batch_base_sha": BASE_SHA,
            "selected_missions": ["M1"],
            "deferred_missions": [],
            "conflict_edges": [],
        },
        "workers": [
            {
                "worker_id": "W1",
                "mission_id": "M1",
                "lease_id": "LEASE1",
                "plan_revision": 1,
                "plan_digest_sha256": digest,
                "batch_base_sha": BASE_SHA,
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "task_thread_id": "THREAD1",
                "worktree_path": "/tmp/worker-m1",
                "branch_ref": BRANCH_REF,
                "report_path": None,
                "phase": "worker_running",
                "worker_head_sha": None,
            }
        ],
        "attempt_log": [],
    }


def make_result(plan: dict[str, object]) -> dict[str, object]:
    return {
        "type": "WORKER_RESULT",
        "run_id": "RUN_TEST",
        "plan_id": "PLAN_TEST",
        "mission_id": "M1",
        "lease_id": "LEASE1",
        "status": "worker_passed",
        "current_task_id": None,
        "plan_revision": 1,
        "plan_digest_sha256": plan_digest(plan),
        "base_sha": BASE_SHA,
        "head_sha": HEAD_SHA,
        "diff_summary": "Implemented the focused behavior and its tests.",
        "changed_files": [CHANGED_FILE],
        "task_results": [
            {
                "task_id": "M1/T01",
                "status": "worker_passed",
                "head_sha": HEAD_SHA,
                "verifier_ids": ["task-focused"],
                "commits": [HEAD_SHA],
                "evidence_paths": ["evidence/task.txt"],
            }
        ],
        "verifiers": [
            {
                "id": "task-focused",
                "status": "PASS",
                "evidence": "python3 -m unittest: exit 0",
            },
            {
                "id": "mission-focused",
                "status": "PASS",
                "evidence": "python3 -m unittest: exit 0",
            },
        ],
        "commits": [HEAD_SHA],
        "evidence_paths": ["evidence/mission.txt"],
        "blockers": [],
        "residual_risks": [],
        "integration_notes": "",
    }


def validate(
    plan: dict[str, object],
    run: dict[str, object],
    result: dict[str, object],
    *,
    observed_files: list[str] | None = None,
    observed_head: str = HEAD_SHA,
    ancestry: bool = True,
    observed_worktree_path: str | None = None,
    observed_branch_ref: str | None = None,
    git_common_dir_confirmed: bool = False,
) -> list[dict[str, str]]:
    return subject.validate_worker_result_data(
        plan,
        run,
        result,
        observed_head_sha=observed_head,
        observed_changed_files=[CHANGED_FILE] if observed_files is None else observed_files,
        ancestry_confirmed=ancestry,
        observed_worktree_path=observed_worktree_path,
        observed_branch_ref=observed_branch_ref,
        git_common_dir_confirmed=git_common_dir_confirmed,
    )


def error_codes(errors: list[dict[str, str]]) -> set[str]:
    return {error["code"] for error in errors}


class ValidateWorkerResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = make_plan()
        self.run = make_run(self.plan)
        self.result = make_result(self.plan)

    def test_fixtures_and_valid_isolated_result(self) -> None:
        self.assertEqual(validate_plan(self.plan), [])
        self.assertEqual(validate_run(self.plan, self.run), [])
        self.assertEqual(validate(self.plan, self.run, self.result), [])

    def test_parent_observed_diff_selects_required_verifiers(self) -> None:
        plan = copy.deepcopy(self.plan)
        selection = {
            "mode": "changed_files",
            "scopes": ["src/m1/backend/**"],
        }
        plan["missions"][0]["tasks"][0]["verifiers"][0]["selection"] = selection
        plan["missions"][0]["worker_verifiers"][0]["selection"] = selection
        run = make_run(plan)
        result = make_result(plan)
        result["task_results"][0]["verifier_ids"] = []
        result["verifiers"] = []
        self.assertEqual(validate(plan, run, result), [])

        applicable = copy.deepcopy(plan)
        applicable_selection = {
            "mode": "changed_files",
            "scopes": ["src/m1/**"],
        }
        applicable["missions"][0]["tasks"][0]["verifiers"][0][
            "selection"
        ] = applicable_selection
        applicable["missions"][0]["worker_verifiers"][0][
            "selection"
        ] = applicable_selection
        applicable_run = make_run(applicable)
        applicable_result = make_result(applicable)
        applicable_result["task_results"][0]["verifier_ids"] = []
        applicable_result["verifiers"] = []
        self.assertIn(
            "required_verifier_missing",
            error_codes(validate(applicable, applicable_run, applicable_result)),
        )

    def test_worker_claim_does_not_control_verifier_selection(self) -> None:
        plan = copy.deepcopy(self.plan)
        selection = {
            "mode": "changed_files",
            "scopes": ["src/m1/backend/**"],
        }
        plan["missions"][0]["tasks"][0]["verifiers"][0]["selection"] = selection
        plan["missions"][0]["worker_verifiers"][0]["selection"] = selection
        run = make_run(plan)
        result = make_result(plan)
        result["changed_files"] = ["src/m1/backend/feature.py"]
        result["task_results"][0]["verifier_ids"] = []
        result["verifiers"] = []
        codes = error_codes(validate(plan, run, result))
        self.assertIn("observed_diff_mismatch", codes)
        self.assertNotIn("required_verifier_missing", codes)

    def test_stale_binding_observed_diff_and_ancestry_are_rejected(self) -> None:
        result = copy.deepcopy(self.result)
        result["lease_id"] = "STALE"
        errors = validate(
            self.plan,
            self.run,
            result,
            observed_files=["src/m1/other.py"],
            observed_head="c" * 40,
            ancestry=False,
        )
        self.assertTrue(
            {
                "worker_record_mismatch",
                "stale_binding",
                "observed_diff_mismatch",
                "observed_head_mismatch",
                "ancestry_unconfirmed",
            }.issubset(error_codes(errors))
        )

    def test_scope_escape_and_parent_owned_files_are_rejected(self) -> None:
        result = copy.deepcopy(self.result)
        result["changed_files"] = ["src/other/file.py", "docs/goal/RUN.md"]
        errors = validate(
            self.plan,
            self.run,
            result,
            observed_files=["src/other/file.py", "docs/goal/RUN.md"],
        )
        self.assertIn("scope_escape", error_codes(errors))
        self.assertIn("parent_owned_file", error_codes(errors))

    def test_only_exact_assigned_report_path_escapes_mission_scope(self) -> None:
        run = copy.deepcopy(self.run)
        worker = run["workers"][0]
        worker["completion_channel"] = "report_file"
        worker["report_path"] = "docs/goal/evidence/M1/REPORT.md"
        run["runtime_capabilities"]["completion_channel"] = "report_file"
        run["mission_states"]["M1"]["report_path"] = worker["report_path"]

        result = copy.deepcopy(self.result)
        result["changed_files"] = [CHANGED_FILE, worker["report_path"]]
        self.assertEqual(
            validate(
                self.plan,
                run,
                result,
                observed_files=[CHANGED_FILE, worker["report_path"]],
            ),
            [],
        )

        result["changed_files"] = [CHANGED_FILE, "docs/goal/evidence/M2/REPORT.md"]
        errors = validate(
            self.plan,
            run,
            result,
            observed_files=[CHANGED_FILE, "docs/goal/evidence/M2/REPORT.md"],
        )
        self.assertIn("scope_escape", error_codes(errors))

    def test_missing_verifier_incomplete_tasks_and_uncommitted_handoff_fail(self) -> None:
        result = copy.deepcopy(self.result)
        result["verifiers"] = []
        result["task_results"] = []
        result["commits"] = []
        errors = validate(self.plan, self.run, result)
        self.assertTrue(
            {
                "required_verifier_missing",
                "incomplete_task_results",
                "uncommitted_handoff",
            }.issubset(error_codes(errors))
        )

    def test_task_head_must_be_reachable_through_its_reported_commit(self) -> None:
        result = copy.deepcopy(self.result)
        result["task_results"][0]["head_sha"] = "c" * 40
        errors = validate(self.plan, self.run, result)
        self.assertIn("task_head_unreachable", error_codes(errors))

    def test_commit_authorization_must_cover_the_worker_branch(self) -> None:
        run = copy.deepcopy(self.run)
        run["authorizations"]["create_local_commits"]["scope"]["targets"] = [
            "branch:refs/heads/codex/different"
        ]
        errors = validate(self.plan, run, self.result)
        self.assertIn("commit_not_authorized", error_codes(errors))

    def test_external_codex_handoff_rechecks_launch_authorizations(self) -> None:
        run = copy.deepcopy(self.run)
        worker = run["workers"][0]
        worker.update(
            {
                "workspace_mode": "app_managed_worktree",
                "runtime_binding": {
                    "provider": "codex",
                    "driver": "external_codex_agent",
                    "source": "external_agent",
                    "model": None,
                    "reasoning_effort": None,
                    "option_source": "provider_default",
                },
                "task_thread_id": None,
            }
        )
        run["observed"]["git"]["worktrees"][0]["managed_by"] = "app"
        targets = {
            "invoke_external_runtime": "runtime:codex",
            "spawn_subagents": "worker:W1",
            "create_app_managed_worktrees": "worktree:/tmp/worker-m1",
            "create_local_branches": f"branch:{BRANCH_REF}",
        }
        for action, target in targets.items():
            run["authorizations"][action] = authorization(
                action, enabled=True, target=target
            )
        observations = {
            "observed_worktree_path": "/tmp/worker-m1",
            "observed_branch_ref": BRANCH_REF,
            "git_common_dir_confirmed": True,
        }
        result = copy.deepcopy(self.result)
        result["subagent_activity"] = {
            "status": "not_applicable",
            "skip_reason": "external_codex_agent uses flat parent orchestration",
            "children": [],
        }
        self.assertEqual(validate(self.plan, run, result, **observations), [])

        missing_activity = copy.deepcopy(result)
        del missing_activity["subagent_activity"]
        errors = validate(self.plan, run, missing_activity, **observations)
        self.assertTrue(
            any(
                error["code"] == "missing_field"
                and error["path"] == "worker_result.subagent_activity"
                for error in errors
            )
        )

        wrong_activity = copy.deepcopy(result)
        wrong_activity["subagent_activity"]["skip_reason"] = "nested work was skipped"
        errors = validate(self.plan, run, wrong_activity, **observations)
        self.assertTrue(
            any(
                error["code"] == "invalid_value"
                and error["path"] == "worker_result.subagent_activity"
                for error in errors
            )
        )

        for action in targets:
            with self.subTest(action=action):
                unauthorized = copy.deepcopy(run)
                unauthorized["authorizations"][action] = authorization(
                    action, enabled=False
                )
                errors = validate(self.plan, unauthorized, result, **observations)
                self.assertIn("external_launch_not_authorized", error_codes(errors))
                self.assertTrue(
                    any(
                        error["path"] == f"harness_run.authorizations.{action}"
                        for error in errors
                    )
                )

    def test_external_codex_handoff_requires_parent_observed_allocation(self) -> None:
        run = copy.deepcopy(self.run)
        worker = run["workers"][0]
        worker.update(
            {
                "workspace_mode": "app_managed_worktree",
                "runtime_binding": {
                    "provider": "codex",
                    "driver": "external_codex_agent",
                    "source": "external_agent",
                    "model": None,
                    "reasoning_effort": None,
                    "option_source": "provider_default",
                },
                "task_thread_id": None,
            }
        )
        run["observed"]["git"]["worktrees"][0]["managed_by"] = "app"
        for action, target in {
            "invoke_external_runtime": "runtime:codex",
            "spawn_subagents": "worker:W1",
            "create_app_managed_worktrees": "worktree:/tmp/worker-m1",
            "create_local_branches": f"branch:{BRANCH_REF}",
        }.items():
            run["authorizations"][action] = authorization(
                action, enabled=True, target=target
            )

        missing = validate(self.plan, run, self.result)
        self.assertTrue(
            {
                "observed_worktree_missing",
                "observed_branch_missing",
                "git_common_dir_unconfirmed",
            }.issubset(error_codes(missing))
        )

        mismatched = validate(
            self.plan,
            run,
            self.result,
            observed_worktree_path="/tmp/different",
            observed_branch_ref="refs/heads/codex/different",
            git_common_dir_confirmed=True,
        )
        self.assertTrue(
            {
                "observed_worktree_mismatch",
                "observed_branch_mismatch",
            }.issubset(error_codes(mismatched))
        )

    def test_unknown_result_field_is_rejected(self) -> None:
        result = copy.deepcopy(self.result)
        result["unexpected"] = True
        errors = validate(self.plan, self.run, result)
        self.assertIn("unknown_field", error_codes(errors))

    def test_completed_activity_requires_an_enabled_policy(self) -> None:
        result = copy.deepcopy(self.result)
        result["subagent_activity"] = {
            "status": "completed",
            "skip_reason": None,
            "children": [
                {
                    "agent_id": "A1",
                    "role": "explorer",
                    "task": "Trace the affected request path.",
                    "status": "completed",
                    "summary": "The path is isolated to the planned module.",
                    "evidence_paths": ["src/m1/file.py"],
                }
            ],
        }
        errors = validate(self.plan, self.run, result)
        self.assertIn("invalid_value", error_codes(errors))

    def test_enabled_nested_policy_requires_and_validates_activity(self) -> None:
        run = copy.deepcopy(self.run)
        worker = run["workers"][0]
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "nested_subagents": {
                    "available": True,
                    "max_depth": 1,
                    "max_children_per_worker": 3,
                    "allowed_roles": ["explorer", "researcher", "reviewer", "tester"],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
            }
        )
        run["runtime_capabilities"]["platform_lifecycle"] = {
            "owner": "app",
            "automatic_retention_cleanup_possible": True,
            "durable_branch_required_before_unique_work": True,
        }
        worker.update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "nested_subagent_policy": {
                    "enabled": True,
                    "max_children": 2,
                    "allowed_roles": ["explorer", "reviewer"],
                    "write_policy": "read_only",
                    "completion_channel": "agent_result",
                },
            }
        )
        run["observed"]["git"]["worktrees"][0]["managed_by"] = "app"
        run["authorizations"]["spawn_subagents"] = {
            "authorized": True,
            "source": "test user authorization",
            "scope": {
                "run_id": "RUN_TEST",
                "mission_ids": ["M1"],
                "targets": ["worker:W1"],
            },
            "expires_when": "run_complete",
        }

        errors = validate(self.plan, run, copy.deepcopy(self.result))
        self.assertIn("missing_field", error_codes(errors))

        result = copy.deepcopy(self.result)
        result["subagent_activity"] = {
            "status": "completed",
            "skip_reason": None,
            "children": [
                {
                    "agent_id": "A1",
                    "role": "explorer",
                    "task": "Trace the affected request path.",
                    "status": "completed",
                    "summary": "The change is isolated to the planned module.",
                    "evidence_paths": ["src/m1/file.py"],
                },
                {
                    "agent_id": "A2",
                    "role": "reviewer",
                    "task": "Review the proposed behavior and tests.",
                    "status": "completed",
                    "summary": "No additional correctness gaps found.",
                    "evidence_paths": ["evidence/task.txt"],
                },
            ],
        }
        self.assertEqual(validate(self.plan, run, result), [])

    def test_shared_loader_requires_exact_heading_and_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "REPORT.md"
            path.write_text(
                "## Worker Result Manifest\n\n```json\n"
                + json.dumps({"worker_result": self.result})
                + "\n```\n",
                encoding="utf-8",
            )
            self.assertEqual(load_worker_result(path), self.result)
            path.write_text(
                "## Wrong Heading\n\n```json\n"
                + json.dumps({"worker_result": self.result})
                + "\n```\n",
                encoding="utf-8",
            )
            with self.assertRaises(ManifestError):
                load_worker_result(path)

    def test_cli_outputs_sorted_json_and_nonzero_on_invalid_observation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "PLAN.md"
            run_path = root / "RUN.md"
            result_path = root / "REPORT.md"
            plan_path.write_text(
                "## Harness Plan Manifest\n\n```json\n"
                + json.dumps({"harness_plan": self.plan})
                + "\n```\n",
                encoding="utf-8",
            )
            run_path.write_text(
                "## Harness Run State\n\n```json\n"
                + json.dumps({"harness_run": self.run})
                + "\n```\n",
                encoding="utf-8",
            )
            result_path.write_text(
                "## Worker Result Manifest\n\n```json\n"
                + json.dumps({"worker_result": self.result})
                + "\n```\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = subject.main(
                    [
                        "--plan",
                        str(plan_path),
                        "--run",
                        str(run_path),
                        "--result",
                        str(result_path),
                        "--observed-head-sha",
                        HEAD_SHA,
                        "--observed-changed-file",
                        CHANGED_FILE,
                        "--ancestry-confirmed",
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload, {"errors": [], "mission_id": "M1", "status": "PASS"})
            self.assertEqual(output.getvalue().strip(), json.dumps(payload, sort_keys=True, separators=(",", ":")))

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = subject.main(
                    [
                        "--plan",
                        str(plan_path),
                        "--run",
                        str(run_path),
                        "--result",
                        str(result_path),
                        "--observed-head-sha",
                        HEAD_SHA,
                        "--observed-changed-file",
                        "src/m1/different.py",
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["status"], "FAIL")
            self.assertIn("ancestry_unconfirmed", {item["code"] for item in payload["errors"]})


if __name__ == "__main__":
    unittest.main()

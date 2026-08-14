from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
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
TASK_EXECUTION_KEY = "c" * 64
MISSION_EXECUTION_KEY = "d" * 64


def verifier(verifier_id: str) -> dict[str, object]:
    return {
        "id": verifier_id,
        "cwd": ".",
        "argv": ["python3", "-m", "unittest"],
        "pass_signal": "exit_code_0",
    }


def retained_verifier_result(
    verifier_id: str,
    plan: dict[str, object],
    changed_files: list[str] | None = None,
) -> dict[str, object]:
    changed_files = sorted([CHANGED_FILE] if changed_files is None else changed_files)
    is_task = verifier_id == "task-focused"
    context = {
        "run_id": "RUN_TEST",
        "plan_revision": 1,
        "plan_digest_sha256": plan_digest(plan),
        "graph_revision": None,
        "batch_base_sha": BASE_SHA,
        "head_sha": HEAD_SHA,
        "changed_files": changed_files,
        "trust_domain": "parent_local",
        "checkout_role": "worker",
        "checkout_dirty": False,
        "cache_safe": True,
        "layer": "task" if is_task else "worker",
        "mission_id": "M1",
        "task_id": "M1/T01" if is_task else None,
        "attempt_id": "ATTEMPT_TASK" if is_task else "ATTEMPT_WORKER",
        "lease_id": "LEASE1",
    }
    declaration = verifier(verifier_id)
    key_document = {
        "protocol": "harness-verifier-execution-v1",
        "verifier_id": verifier_id,
        "layer": context["layer"],
        "mission_id": context["mission_id"],
        "task_id": context["task_id"],
        "attempt_id": context["attempt_id"],
        "lease_id": context["lease_id"],
        "run_id": context["run_id"],
        "plan_revision": context["plan_revision"],
        "plan_digest_sha256": context["plan_digest_sha256"],
        "graph_revision": context["graph_revision"],
        "batch_base_sha": context["batch_base_sha"],
        "head_sha": context["head_sha"],
        "changed_files_digest": hashlib.sha256(
            json.dumps(changed_files, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
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
            "path": "C:/python3",
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
    return {
        "protocol": "harness-verifier-execution-v1",
        "verifier_id": verifier_id,
        "status": "PASS",
        "exit_code": 0,
        "stdout": "",
        "stderr": "",
        "execution_key": execution_key,
        "evidence_key": execution_key,
        "verifier": {
            "id": verifier_id,
            "cwd": declaration["cwd"],
            "argv": declaration["argv"],
            "pass_signal": declaration["pass_signal"],
            "cache": {"mode": "disabled", "environment_keys": []},
        },
        "context": context,
        "key_document": key_document,
        "cache_status": "bypassed",
        "cache_reason": "cache_disabled",
        "duration_ms": 1,
        "metrics": {"executed": 1, "reused": 0},
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
                "required_skills": [],
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
            "mode": "local_only",
            "remote": "origin",
            "pushed_head_sha": None,
            "continuity": None,
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
        "attempt_log": [
            {
                "attempt_id": "ATTEMPT_TASK",
                "mission_id": "M1",
                "task_id": "M1/T01",
                "lease_id": "LEASE1",
                "kind": "task_verifier",
                "result": "PASS",
                "evidence": [],
            },
            {
                "attempt_id": "ATTEMPT_WORKER",
                "mission_id": "M1",
                "task_id": None,
                "lease_id": "LEASE1",
                "kind": "worker_verifier",
                "result": "PASS",
                "evidence": [],
            },
        ],
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
                "evidence": retained_verifier_result("task-focused", plan)["execution_key"],
            },
            {
                "id": "mission-focused",
                "status": "PASS",
                "evidence": retained_verifier_result("mission-focused", plan)["execution_key"],
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
    retained: list[dict[str, object]] | None = None,
) -> list[dict[str, str]]:
    effective_observed_files = [CHANGED_FILE] if observed_files is None else observed_files
    verifier_changed_files = [
        path
        for path in effective_observed_files
        if not (
            run["workers"][0].get("completion_channel") == "report_file"
            and path == run["workers"][0].get("report_path")
        )
    ]
    if retained is None:
        retained = [
            retained_verifier_result(item["id"], plan, verifier_changed_files)
            for item in result.get("verifiers", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]
    return subject.validate_worker_result_data(
        plan,
        run,
        result,
        observed_head_sha=observed_head,
        observed_changed_files=effective_observed_files,
        ancestry_confirmed=ancestry,
        retained_verifier_results=retained,
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
        # Every declared verifier's scopes miss the observed change, so the
        # mission would hand back `worker_passed` having run nothing. That is a
        # gap in the plan's verifier coverage, not a clean run.
        self.assertEqual(
            error_codes(validate(plan, run, result)), {"no_applicable_verifier"}
        )

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

    def test_wave_not_active_rejects_the_worker_result(self) -> None:
        run = copy.deepcopy(self.run)
        run["active_wave"]["status"] = "closed"
        errors = validate(self.plan, run, self.result)
        self.assertIn("wave_not_active", error_codes(errors))

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

    def test_verifier_evidence_must_match_a_parent_retained_result(self) -> None:
        retained = [
            retained_verifier_result("task-focused", self.plan),
            retained_verifier_result("mission-focused", self.plan),
        ]
        self.assertEqual(validate(self.plan, self.run, self.result, retained=retained), [])

    def test_failed_history_is_retained_when_a_later_exact_execution_passes(self) -> None:
        task_pass = retained_verifier_result("task-focused", self.plan)
        task_fail = copy.deepcopy(task_pass)
        task_fail["status"] = "FAIL"
        task_fail["exit_code"] = 1
        retained = [
            task_fail,
            task_pass,
            retained_verifier_result("mission-focused", self.plan),
        ]

        self.assertEqual(validate(self.plan, self.run, self.result, retained=retained), [])

        retained[0], retained[1] = retained[1], retained[0]
        self.assertIn(
            "retained_verifier_not_pass",
            error_codes(validate(self.plan, self.run, self.result, retained=retained)),
        )

    def test_dirty_isolated_worker_worktree_cannot_supply_verifier_evidence(self) -> None:
        run = copy.deepcopy(self.run)
        run["observed"]["git"]["worktrees"][0]["dirty"] = True

        errors = validate(self.plan, run, self.result)

        self.assertIn("dirty_worker_handoff", error_codes(errors))
        self.assertIn("retained_verifier_context_mismatch", error_codes(errors))

    def test_empty_verifiers_still_run_the_dirty_worktree_gate(self) -> None:
        """`verifiers: []` must not skip the retained-evidence gates.

        The dirty-worktree gate, the worktree identity match, and the
        parent-retained-evidence requirement all live in one helper that used to
        be skipped entirely when the worker reported no verifiers — so a handoff
        from a dirty worktree with nothing executed validated clean.
        """
        run = copy.deepcopy(self.run)
        run["observed"]["git"]["worktrees"][0]["dirty"] = True
        result = copy.deepcopy(self.result)
        result["verifiers"] = []
        for task_result in result["task_results"]:
            task_result["verifier_ids"] = []

        codes = error_codes(validate(self.plan, run, result))

        self.assertIn("dirty_worker_handoff", codes)

    def test_fabricated_hash_is_rejected_without_a_matching_retained_result(self) -> None:
        result = copy.deepcopy(self.result)
        result["verifiers"][0]["evidence"] = TASK_EXECUTION_KEY
        errors = validate(self.plan, self.run, result)
        self.assertIn("retained_verifier_result_mismatch", error_codes(errors))

    def test_missing_retained_result_is_rejected(self) -> None:
        errors = validate(self.plan, self.run, self.result, retained=[])
        self.assertIn("retained_verifier_result_missing", error_codes(errors))

    def test_forged_or_mismatched_retained_result_is_rejected(self) -> None:
        retained = [
            retained_verifier_result("task-focused", self.plan),
            retained_verifier_result("mission-focused", self.plan),
        ]
        retained[0]["execution_key"] = "f" * 64
        retained[1]["context"]["head_sha"] = "c" * 40
        codes = error_codes(validate(self.plan, self.run, self.result, retained=retained))
        self.assertIn("retained_verifier_key_mismatch", codes)
        self.assertIn("retained_verifier_context_mismatch", codes)

    def test_retained_result_requires_exact_id_declaration_and_pass_status(self) -> None:
        retained = [
            retained_verifier_result("task-focused", self.plan),
            retained_verifier_result("mission-focused", self.plan),
        ]
        retained[0]["verifier_id"] = "other-verifier"
        retained[1]["status"] = "FAIL"
        retained[1]["exit_code"] = 1
        retained[1]["verifier"]["argv"] = ["python3", "unexpected.py"]

        codes = error_codes(validate(self.plan, self.run, self.result, retained=retained))

        self.assertIn("retained_verifier_result_missing", codes)
        self.assertIn("retained_verifier_mismatch", codes)
        self.assertIn("retained_verifier_not_pass", codes)

    def test_retained_key_document_must_encode_the_declared_verifier(self) -> None:
        result = copy.deepcopy(self.result)
        retained = [
            retained_verifier_result("task-focused", self.plan),
            retained_verifier_result("mission-focused", self.plan),
        ]
        retained[0]["key_document"]["argv"] = ["python3", "forged.py"]
        execution_key = hashlib.sha256(
            json.dumps(
                retained[0]["key_document"],
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        retained[0]["execution_key"] = execution_key
        retained[0]["evidence_key"] = execution_key
        result["verifiers"][0]["evidence"] = execution_key

        codes = error_codes(validate(self.plan, self.run, result, retained=retained))

        self.assertIn("retained_verifier_mismatch", codes)

    def test_verifier_evidence_rejects_free_form_text(self) -> None:
        result = copy.deepcopy(self.result)
        result["verifiers"][0]["evidence"] = "tests passed"
        errors = validate(self.plan, self.run, result)
        self.assertIn("invalid_execution_key", error_codes(errors))

    def test_verifier_evidence_rejects_missing_or_empty_value(self) -> None:
        for missing_value in (None, ""):
            with self.subTest(missing_value=missing_value):
                result = copy.deepcopy(self.result)
                result["verifiers"][0]["evidence"] = missing_value
                errors = validate(self.plan, self.run, result)
                self.assertIn("invalid_type", error_codes(errors))

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

    def test_cli_no_longer_accepts_removed_external_codex_observation_flags(self) -> None:
        # The guarded external-Codex handoff (and its parent-observed
        # worktree/branch/git-common-dir reconciliation) is fully removed:
        # the CLI must reject these now-unknown flags rather than silently
        # accepting and ignoring them.
        parser = subject._parser()
        for flag, value in (
            ("--observed-worktree-path", "/tmp/worker-m1"),
            ("--observed-branch-ref", BRANCH_REF),
            ("--git-common-dir-confirmed", None),
        ):
            with self.subTest(flag=flag):
                argv = [
                    "--plan",
                    "PLAN.md",
                    "--run",
                    "RUN.md",
                    "--result",
                    "REPORT.md",
                    "--observed-head-sha",
                    HEAD_SHA,
                    flag,
                ]
                if value is not None:
                    argv.append(value)
                with self.assertRaises(SystemExit):
                    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                        parser.parse_args(argv)

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

    def test_v10_forbids_nested_activity_and_legacy_contract_remains_readable(self) -> None:
        run = copy.deepcopy(self.run)
        run["schema_version"] = 10
        run["execution_authorization_scope"].update(
            {
                "plan_revision": self.plan["revision"],
                "plan_digest_sha256": plan_digest(self.plan),
            }
        )
        run["authorizations"]["create_local_commits"]["scope"].update(
            {
                "plan_revision": self.plan["revision"],
                "plan_digest_sha256": plan_digest(self.plan),
            }
        )
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
                "plan_revision": self.plan["revision"],
                "plan_digest_sha256": plan_digest(self.plan),
                "mission_ids": ["M1"],
                "targets": ["worker:W1"],
            },
            "expires_when": "run_complete",
        }

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
                    "reviewed_sha": result["head_sha"],
                    "decision": "PASS",
                },
            ],
        }
        v10_codes = error_codes(validate(self.plan, run, result))
        self.assertIn("nested_delegation_forbidden", v10_codes)

        legacy_run = copy.deepcopy(run)
        legacy_run["schema_version"] = 9
        self.assertNotIn(
            "nested_delegation_forbidden",
            error_codes(validate(self.plan, legacy_run, result)),
        )

        worker["nested_subagent_policy"] = {
            "enabled": False,
            "max_children": 0,
            "allowed_roles": [],
            "write_policy": "read_only",
            "completion_channel": "agent_result",
        }
        result["subagent_activity"] = {
            "status": "not_applicable",
            "skip_reason": "flat parent-owned topology",
            "children": [],
        }
        self.assertEqual(validate(self.plan, run, result), [])

    def test_disabled_nested_policy_defers_parent_review_to_integration(self) -> None:
        plan = copy.deepcopy(self.plan)
        review_node = {
            "id": "N-M1-PREINTEGRATION-REVIEW",
            "kind": "verifier",
            "executor": "runtime_worker",
            "review": {
                "type": "backend_code",
                "mission_ids": ["M1"],
                "scope": ["src/m1/**"],
                "required_evidence": ["reviewed_sha", "decision"],
            },
        }
        plan["graph"] = {"nodes": [review_node], "edges": []}
        run = copy.deepcopy(self.run)
        result = copy.deepcopy(self.result)
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["mission_states"]["M1"]["lease_plan_digest_sha256"] = digest
        run["mission_states"]["M1"]["head_sha"] = HEAD_SHA
        run["active_wave"]["plan_digest_sha256"] = digest
        run["workers"][0]["plan_digest_sha256"] = digest
        run["workers"][0]["nested_subagent_policy"] = {
            "enabled": False,
            "max_children": 0,
            "allowed_roles": [],
            "write_policy": "read_only",
            "completion_channel": "agent_result",
        }
        result["plan_digest_sha256"] = digest
        for verifier_result in result["verifiers"]:
            verifier_result["evidence"] = retained_verifier_result(
                verifier_result["id"],
                plan,
            )["execution_key"]
        result["subagent_activity"] = {
            "status": "not_applicable",
            "skip_reason": "flat parent-owned topology",
            "children": [],
        }

        self.assertEqual(validate(plan, run, result), [])

    def test_absent_nested_policy_defers_parent_review_to_integration(self) -> None:
        plan = copy.deepcopy(self.plan)
        review_node = {
            "id": "N-M1-PREINTEGRATION-REVIEW",
            "kind": "verifier",
            "executor": "runtime_worker",
            "review": {
                "type": "backend_code",
                "mission_ids": ["M1"],
                "scope": ["src/m1/**"],
                "required_evidence": ["reviewed_sha", "decision"],
            },
        }
        plan["graph"] = {"nodes": [review_node], "edges": []}
        run = copy.deepcopy(self.run)
        result = copy.deepcopy(self.result)
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["mission_states"]["M1"]["lease_plan_digest_sha256"] = digest
        run["mission_states"]["M1"]["head_sha"] = HEAD_SHA
        run["active_wave"]["plan_digest_sha256"] = digest
        run["workers"][0]["plan_digest_sha256"] = digest
        run["workers"][0].pop("nested_subagent_policy", None)
        run["review_workers"] = []
        result["plan_digest_sha256"] = digest
        for verifier_result in result["verifiers"]:
            verifier_result["evidence"] = retained_verifier_result(
                verifier_result["id"],
                plan,
            )["execution_key"]

        self.assertEqual(validate(plan, run, result), [])

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
            task_verifier_path = root / "task-verifier.json"
            mission_verifier_path = root / "mission-verifier.json"
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
            task_verifier_path.write_text(
                json.dumps(retained_verifier_result("task-focused", self.plan)),
                encoding="utf-8",
            )
            mission_verifier_path.write_text(
                json.dumps(retained_verifier_result("mission-focused", self.plan)),
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
                        "--verifier-result",
                        str(task_verifier_path),
                        "--verifier-result",
                        str(mission_verifier_path),
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
                        "--verifier-result",
                        str(task_verifier_path),
                        "--verifier-result",
                        str(mission_verifier_path),
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["status"], "FAIL")
            self.assertIn("ancestry_unconfirmed", {item["code"] for item in payload["errors"]})


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Validate a worker result against canonical PLAN/RUN state and observations."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Iterable

from harness_manifest import (
    ManifestError,
    NESTED_SUBAGENT_ROLES,
    authorization_covers,
    execution_covers,
    load_plan,
    load_run,
    load_worker_result,
    parent_owned_path,
    path_in_scopes,
    plan_digest,
    validate_scope_claim,
    validate_plan,
    validate_run,
)


SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

WORKER_RESULT_FIELDS = {
    "type",
    "run_id",
    "plan_id",
    "mission_id",
    "lease_id",
    "status",
    "current_task_id",
    "plan_revision",
    "plan_digest_sha256",
    "base_sha",
    "head_sha",
    "diff_summary",
    "changed_files",
    "task_results",
    "verifiers",
    "commits",
    "evidence_paths",
    "blockers",
    "residual_risks",
    "integration_notes",
}
TASK_RESULT_FIELDS = {
    "task_id",
    "status",
    "head_sha",
    "verifier_ids",
    "commits",
    "evidence_paths",
}
VERIFIER_RESULT_FIELDS = {"id", "status", "evidence"}
SUBAGENT_ACTIVITY_FIELDS = {"status", "skip_reason", "children"}
SUBAGENT_CHILD_FIELDS = {
    "agent_id",
    "role",
    "task",
    "status",
    "summary",
    "evidence_paths",
}
ISOLATED_WORKSPACES = {"parent_managed_worktree", "app_managed_worktree"}


def _issue(
    errors: list[dict[str, str]], code: str, path: str, message: str
) -> None:
    errors.append({"code": code, "path": path, "message": message})


def _sorted_errors(errors: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(errors, key=lambda item: (item["code"], item["path"], item["message"]))


def _check_exact_fields(
    value: Any,
    expected: set[str],
    path: str,
    errors: list[dict[str, str]],
    *,
    optional: set[str] | None = None,
) -> bool:
    if not isinstance(value, dict):
        _issue(errors, "invalid_type", path, "must be an object")
        return False
    actual = set(value)
    for field in sorted(expected - actual):
        _issue(errors, "missing_field", f"{path}.{field}", "required field is missing")
    allowed_optional = optional or set()
    for field in sorted(actual - expected - allowed_optional):
        _issue(errors, "unknown_field", f"{path}.{field}", "unknown field is not allowed")
    return expected.issubset(actual) and actual.issubset(expected | allowed_optional)


def _validate_subagent_activity(
    value: Any,
    *,
    policy: dict[str, Any] | None,
    errors: list[dict[str, str]],
) -> None:
    path = "worker_result.subagent_activity"
    if not _check_exact_fields(value, SUBAGENT_ACTIVITY_FIELDS, path, errors):
        return
    status = _require_string(value.get("status"), f"{path}.status", errors)
    if status not in {"completed", "partial", "unavailable", "not_applicable"}:
        _issue(errors, "invalid_value", f"{path}.status", "has an unsupported value")
    skip_reason = value.get("skip_reason")
    if skip_reason is not None:
        _require_string(skip_reason, f"{path}.skip_reason", errors)
    children = value.get("children")
    if not isinstance(children, list):
        _issue(errors, "invalid_type", f"{path}.children", "must be an array")
        return
    child_statuses: list[str] = []
    child_roles: list[str] = []
    agent_ids: list[str] = []
    for index, child in enumerate(children):
        child_path = f"{path}.children[{index}]"
        if not _check_exact_fields(child, SUBAGENT_CHILD_FIELDS, child_path, errors):
            continue
        agent_id = _require_string(child.get("agent_id"), f"{child_path}.agent_id", errors)
        role = _require_string(child.get("role"), f"{child_path}.role", errors)
        _require_string(child.get("task"), f"{child_path}.task", errors)
        child_status = _require_string(child.get("status"), f"{child_path}.status", errors)
        _require_string(child.get("summary"), f"{child_path}.summary", errors)
        _require_string_list(child.get("evidence_paths"), f"{child_path}.evidence_paths", errors)
        if agent_id is not None:
            agent_ids.append(agent_id)
        if role is not None:
            child_roles.append(role)
            if role not in NESTED_SUBAGENT_ROLES:
                _issue(errors, "invalid_value", f"{child_path}.role", "has an unsupported value")
        if child_status is not None:
            child_statuses.append(child_status)
            if child_status not in {"completed", "failed", "stopped"}:
                _issue(errors, "invalid_value", f"{child_path}.status", "has an unsupported value")
    if len(agent_ids) != len(set(agent_ids)):
        _issue(errors, "duplicate_value", f"{path}.children", "agent_id values must be unique")
    enabled = isinstance(policy, dict) and policy.get("enabled") is True
    if enabled:
        if status == "not_applicable":
            _issue(errors, "invalid_value", f"{path}.status", "cannot be not_applicable when policy is enabled")
        limit = policy.get("max_children")
        if isinstance(limit, int) and not isinstance(limit, bool) and len(children) > limit:
            _issue(errors, "over_budget", f"{path}.children", "exceeds worker nested-subagent limit")
        allowed_roles = set(policy.get("allowed_roles", []))
        if set(child_roles) - allowed_roles:
            _issue(errors, "invalid_value", f"{path}.children", "contains a role outside the worker policy")
    elif status in {"completed", "partial"}:
        _issue(
            errors,
            "invalid_value",
            f"{path}.status",
            "requires an enabled worker nested-subagent policy",
        )
    if status == "completed":
        if not children:
            _issue(errors, "missing_field", f"{path}.children", "completed activity requires at least one child")
        if any(item != "completed" for item in child_statuses):
            _issue(errors, "invalid_value", f"{path}.children", "completed activity requires completed children")
        if skip_reason is not None:
            _issue(errors, "invalid_value", f"{path}.skip_reason", "must be null when completed")
    elif status == "partial":
        if not children or all(item == "completed" for item in child_statuses):
            _issue(errors, "invalid_value", f"{path}.children", "partial activity requires a failed or stopped child")
        if not isinstance(skip_reason, str) or not skip_reason:
            _issue(errors, "missing_field", f"{path}.skip_reason", "partial activity requires an explanation")
    elif status in {"unavailable", "not_applicable"}:
        if children:
            _issue(errors, "invalid_value", f"{path}.children", "must be empty for this status")
        if not isinstance(skip_reason, str) or not skip_reason:
            _issue(errors, "missing_field", f"{path}.skip_reason", "requires a concrete reason")


def _require_string(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
    *,
    allow_empty: bool = False,
) -> str | None:
    if not isinstance(value, str) or (not allow_empty and not value):
        qualifier = "a string" if allow_empty else "a non-empty string"
        _issue(errors, "invalid_type", path, f"must be {qualifier}")
        return None
    return value


def _require_string_list(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
    *,
    unique: bool = True,
) -> list[str] | None:
    if not isinstance(value, list):
        _issue(errors, "invalid_type", path, "must be an array")
        return None
    result: list[str] = []
    for index, item in enumerate(value):
        checked = _require_string(item, f"{path}[{index}]", errors)
        if checked is not None:
            result.append(checked)
    if unique and len(result) != len(set(result)):
        _issue(errors, "duplicate_value", path, "must not contain duplicates")
    return result


def _require_sha(
    value: Any,
    path: str,
    errors: list[dict[str, str]],
    *,
    digest: bool = False,
) -> str | None:
    checked = _require_string(value, path, errors)
    if checked is None:
        return None
    pattern = DIGEST_RE if digest else SHA_RE
    if not pattern.fullmatch(checked):
        expected = "64 lowercase hexadecimal characters" if digest else "40 or 64 lowercase hexadecimal characters"
        _issue(errors, "invalid_sha", path, f"must contain {expected}")
        return None
    return checked


def _canonical_changed_path(
    value: Any, path: str, errors: list[dict[str, str]]
) -> str | None:
    checked = _require_string(value, path, errors)
    if checked is None:
        return None
    problem = validate_scope_claim(checked)
    if problem:
        _issue(errors, "invalid_changed_path", path, problem)
        return None
    if checked.endswith("/**"):
        _issue(errors, "invalid_changed_path", path, "changed files must be exact paths, not subtrees")
        return None
    return checked


def _find_mission(plan: dict[str, Any], mission_id: Any) -> dict[str, Any] | None:
    if not isinstance(mission_id, str):
        return None
    matches = [
        mission
        for mission in plan.get("missions", [])
        if isinstance(mission, dict) and mission.get("id") == mission_id
    ]
    return matches[0] if len(matches) == 1 else None


def _report_exception(path: str, worker: dict[str, Any]) -> bool:
    report_path = worker.get("report_path")
    if worker.get("completion_channel") != "report_file" or not isinstance(report_path, str):
        return False
    if validate_scope_claim(report_path) is not None or report_path.endswith("/**"):
        return False
    return report_path == path and report_path.rsplit("/", 1)[-1] == "REPORT.md"


def validate_worker_result_data(
    plan: dict[str, Any],
    run: dict[str, Any],
    result: dict[str, Any],
    *,
    observed_head_sha: str | None,
    observed_changed_files: list[str] | None,
    ancestry_confirmed: bool,
    observed_worktree_path: str | None = None,
    observed_branch_ref: str | None = None,
    git_common_dir_confirmed: bool = False,
) -> list[dict[str, str]]:
    """Return deterministic validation issues for one integration candidate."""

    errors: list[dict[str, str]] = []
    _check_exact_fields(
        result,
        WORKER_RESULT_FIELDS,
        "worker_result",
        errors,
        optional={"subagent_activity"},
    )

    result_type = _require_string(result.get("type"), "worker_result.type", errors)
    run_id = _require_string(result.get("run_id"), "worker_result.run_id", errors)
    result_plan_id = _require_string(result.get("plan_id"), "worker_result.plan_id", errors)
    mission_id = _require_string(result.get("mission_id"), "worker_result.mission_id", errors)
    lease_id = _require_string(result.get("lease_id"), "worker_result.lease_id", errors)
    status = _require_string(result.get("status"), "worker_result.status", errors)
    result_digest = _require_sha(
        result.get("plan_digest_sha256"),
        "worker_result.plan_digest_sha256",
        errors,
        digest=True,
    )
    base_sha = _require_sha(result.get("base_sha"), "worker_result.base_sha", errors)
    head_sha = _require_sha(result.get("head_sha"), "worker_result.head_sha", errors)
    _require_string(result.get("diff_summary"), "worker_result.diff_summary", errors)
    _require_string(result.get("integration_notes"), "worker_result.integration_notes", errors, allow_empty=True)

    if result_type is not None and result_type != "WORKER_RESULT":
        _issue(errors, "invalid_value", "worker_result.type", "must be WORKER_RESULT")
    if status is not None and status != "worker_passed":
        _issue(errors, "not_integration_candidate", "worker_result.status", "must be worker_passed")
    if result.get("current_task_id") is not None:
        _issue(errors, "current_task_present", "worker_result.current_task_id", "must be null for worker_passed")
    if not isinstance(result.get("plan_revision"), int) or isinstance(result.get("plan_revision"), bool):
        _issue(errors, "invalid_type", "worker_result.plan_revision", "must be an integer")

    blockers = _require_string_list(result.get("blockers"), "worker_result.blockers", errors)
    _require_string_list(result.get("residual_risks"), "worker_result.residual_risks", errors, unique=False)
    _require_string_list(result.get("evidence_paths"), "worker_result.evidence_paths", errors)
    commits = _require_string_list(result.get("commits"), "worker_result.commits", errors)
    if blockers:
        _issue(errors, "blockers_present", "worker_result.blockers", "worker_passed cannot contain blockers")
    if commits is not None:
        for index, commit in enumerate(commits):
            _require_sha(commit, f"worker_result.commits[{index}]", errors)

    expected_digest = plan_digest(plan)
    plan_id = plan.get("plan_id")
    plan_revision = plan.get("revision")
    run_plan = run.get("plan", {})

    comparisons = [
        (run_id, run.get("run_id"), "run_id", "RUN"),
        (result_plan_id, plan_id, "plan_id", "PLAN"),
        (result_plan_id, run_plan.get("id"), "plan_id", "RUN plan"),
        (result.get("plan_revision"), plan_revision, "plan_revision", "PLAN"),
        (result.get("plan_revision"), run_plan.get("revision"), "plan_revision", "RUN plan"),
        (result_digest, expected_digest, "plan_digest_sha256", "computed PLAN digest"),
        (result_digest, run_plan.get("digest_sha256"), "plan_digest_sha256", "RUN plan digest"),
    ]
    for actual, expected, field, source in comparisons:
        if actual is not None and actual != expected:
            _issue(
                errors,
                "stale_binding",
                f"worker_result.{field}",
                f"does not match {source}",
            )

    mission = _find_mission(plan, mission_id)
    if mission is None:
        _issue(errors, "unknown_mission", "worker_result.mission_id", "mission is not uniquely defined in PLAN")
    elif not execution_covers(run, mission_id):
        _issue(
            errors,
            "execution_not_authorized",
            "harness_run.execution_authorization_scope",
            "execution authorization does not cover this mission",
        )

    mission_state = run.get("mission_states", {}).get(mission_id) if mission_id else None
    if not isinstance(mission_state, dict):
        _issue(errors, "missing_mission_state", f"harness_run.mission_states.{mission_id}", "mission state is required")
        mission_state = {}
    elif mission_state.get("phase") not in {"worker_running", "worker_passed"}:
        _issue(
            errors,
            "invalid_mission_phase",
            f"harness_run.mission_states.{mission_id}.phase",
            "must be worker_running or worker_passed while validating a result",
        )

    workers = run.get("workers", [])
    worker_matches = [
        worker
        for worker in workers
        if isinstance(worker, dict)
        and worker.get("mission_id") == mission_id
        and worker.get("lease_id") == lease_id
    ] if isinstance(workers, list) else []
    if len(worker_matches) != 1:
        _issue(errors, "worker_record_mismatch", "harness_run.workers", "exactly one mission/lease worker record is required")
        worker: dict[str, Any] = {}
    else:
        worker = worker_matches[0]

    nested_policy = (
        worker.get("nested_subagent_policy") if isinstance(worker, dict) else None
    )
    if isinstance(nested_policy, dict):
        if "subagent_activity" not in result:
            _issue(
                errors,
                "missing_field",
                "worker_result.subagent_activity",
                "is required when the worker records a nested-subagent policy",
            )
    if "subagent_activity" in result:
        _validate_subagent_activity(
            result.get("subagent_activity"),
            policy=nested_policy if isinstance(nested_policy, dict) else None,
            errors=errors,
        )

    worker_id = mission_state.get("worker_id")
    binding_checks = [
        (lease_id, mission_state.get("lease_id"), "lease_id", "mission state"),
        (result.get("plan_revision"), mission_state.get("lease_plan_revision"), "plan_revision", "mission lease"),
        (result_digest, mission_state.get("lease_plan_digest_sha256"), "plan_digest_sha256", "mission lease"),
        (base_sha, mission_state.get("base_sha"), "base_sha", "mission state"),
        (worker_id, worker.get("worker_id"), "worker_id", "worker record"),
        (result.get("plan_revision"), worker.get("plan_revision"), "plan_revision", "worker record"),
        (result_digest, worker.get("plan_digest_sha256"), "plan_digest_sha256", "worker record"),
        (base_sha, worker.get("batch_base_sha"), "base_sha", "worker record"),
        (base_sha, run.get("integration", {}).get("batch_base_sha"), "base_sha", "RUN integration base"),
        (base_sha, run.get("active_wave", {}).get("batch_base_sha"), "base_sha", "active wave"),
        (result.get("plan_revision"), run.get("active_wave", {}).get("plan_revision"), "plan_revision", "active wave"),
        (result_digest, run.get("active_wave", {}).get("plan_digest_sha256"), "plan_digest_sha256", "active wave"),
    ]
    for actual, expected, field, source in binding_checks:
        if actual is not None and actual != expected:
            _issue(errors, "stale_binding", f"worker_result.{field}", f"does not match {source}")

    if worker and worker.get("phase") not in {"worker_running", "worker_passed"}:
        _issue(errors, "invalid_worker_phase", "harness_run.workers.phase", "must be worker_running or worker_passed")
    if worker and mission_state.get("worker_id") != worker.get("worker_id"):
        _issue(errors, "worker_record_mismatch", "harness_run.mission_states.worker_id", "does not match worker record")
    runtime_capabilities = run.get("runtime_capabilities", {})
    runtime_binding = worker.get("runtime_binding") if worker else None
    external_codex = (
        isinstance(runtime_binding, dict)
        and runtime_binding.get("driver") == "external_codex_agent"
    )
    if external_codex:
        expected_runtime_axes = {
            "worker_runtime": "subagent",
            "workspace_mode": "app_managed_worktree",
            "completion_channel": "agent_result",
        }
    else:
        expected_runtime_axes = runtime_capabilities
    for field in ("worker_runtime", "workspace_mode", "completion_channel"):
        if worker and worker.get(field) != expected_runtime_axes.get(field):
            source = "external Codex runtime binding" if expected_runtime_axes is not runtime_capabilities else "RUN runtime capabilities"
            _issue(
                errors,
                "worker_record_mismatch",
                f"harness_run.workers.{field}",
                f"does not match {source}",
            )

    active_wave = run.get("active_wave", {})
    if not isinstance(active_wave, dict) or active_wave.get("status") != "active":
        _issue(errors, "wave_not_active", "harness_run.active_wave.status", "must be active")
    elif mission_id not in active_wave.get("selected_missions", []):
        _issue(errors, "mission_not_selected", "harness_run.active_wave.selected_missions", "mission is not in the active wave")

    observed_checked = _require_sha(observed_head_sha, "observed.head_sha", errors)
    if head_sha is not None and observed_checked is not None and head_sha != observed_checked:
        _issue(errors, "observed_head_mismatch", "worker_result.head_sha", "does not match parent-observed head")
    for source, recorded in (
        ("mission state", mission_state.get("head_sha")),
        ("worker record", worker.get("worker_head_sha")),
    ):
        if recorded is not None and head_sha is not None and recorded != head_sha:
            _issue(errors, "observed_head_mismatch", "worker_result.head_sha", f"does not match {source}")
    if not ancestry_confirmed:
        _issue(errors, "ancestry_unconfirmed", "observed.ancestry", "parent must confirm base is an ancestor of head")
    if base_sha is not None and head_sha is not None and base_sha == head_sha:
        _issue(errors, "empty_handoff", "worker_result.head_sha", "must differ from base SHA")

    reported_paths_raw = result.get("changed_files")
    reported_paths: list[str] = []
    if isinstance(reported_paths_raw, list):
        for index, value in enumerate(reported_paths_raw):
            canonical = _canonical_changed_path(value, f"worker_result.changed_files[{index}]", errors)
            if canonical is not None:
                reported_paths.append(canonical)
        if len(reported_paths) != len(set(reported_paths)):
            _issue(errors, "duplicate_value", "worker_result.changed_files", "must not contain duplicates")
    else:
        _issue(errors, "invalid_type", "worker_result.changed_files", "must be an array")

    observed_paths: list[str] = []
    if observed_changed_files is None:
        _issue(errors, "observed_diff_missing", "observed.changed_files", "parent-observed changed files are required")
    else:
        for index, value in enumerate(observed_changed_files):
            canonical = _canonical_changed_path(value, f"observed.changed_files[{index}]", errors)
            if canonical is not None:
                observed_paths.append(canonical)
        if len(observed_paths) != len(set(observed_paths)):
            _issue(errors, "duplicate_value", "observed.changed_files", "must not contain duplicates")
        if set(reported_paths) != set(observed_paths):
            _issue(errors, "observed_diff_mismatch", "worker_result.changed_files", "must exactly match parent-observed changed files")

    if mission is not None:
        write_scope = mission.get("write_scope", [])
        deny_scope = mission.get("deny_scope", [])
        for index, changed_path in enumerate(reported_paths):
            item_path = f"worker_result.changed_files[{index}]"
            if parent_owned_path(changed_path):
                _issue(errors, "parent_owned_file", item_path, "PLAN.md and RUN.md are always parent-owned")
                continue
            if _report_exception(changed_path, worker):
                continue
            denied = path_in_scopes(changed_path, deny_scope)
            allowed = path_in_scopes(changed_path, write_scope)
            if denied:
                _issue(errors, "denied_path", item_path, "changed path is denied by the mission")
            elif not allowed:
                _issue(errors, "scope_escape", item_path, "changed path is outside mission write scope")

    verifier_results_raw = result.get("verifiers")
    verifier_results: dict[str, dict[str, Any]] = {}
    if not isinstance(verifier_results_raw, list):
        _issue(errors, "invalid_type", "worker_result.verifiers", "must be an array")
    else:
        for index, verifier in enumerate(verifier_results_raw):
            item_path = f"worker_result.verifiers[{index}]"
            _check_exact_fields(verifier, VERIFIER_RESULT_FIELDS, item_path, errors)
            if not isinstance(verifier, dict):
                continue
            verifier_id = _require_string(verifier.get("id"), f"{item_path}.id", errors)
            verifier_status = _require_string(verifier.get("status"), f"{item_path}.status", errors)
            _require_string(verifier.get("evidence"), f"{item_path}.evidence", errors)
            if verifier_id is not None:
                if verifier_id in verifier_results:
                    _issue(errors, "duplicate_verifier", f"{item_path}.id", "verifier ID must be unique")
                else:
                    verifier_results[verifier_id] = verifier
            if verifier_status is not None and verifier_status != "PASS":
                _issue(errors, "verifier_not_pass", f"{item_path}.status", "all reported verifiers must be PASS")

    task_results_raw = result.get("task_results")
    task_results: dict[str, dict[str, Any]] = {}
    if not isinstance(task_results_raw, list):
        _issue(errors, "invalid_type", "worker_result.task_results", "must be an array")
    else:
        for index, task_result in enumerate(task_results_raw):
            item_path = f"worker_result.task_results[{index}]"
            _check_exact_fields(task_result, TASK_RESULT_FIELDS, item_path, errors)
            if not isinstance(task_result, dict):
                continue
            task_id = _require_string(task_result.get("task_id"), f"{item_path}.task_id", errors)
            task_status = _require_string(task_result.get("status"), f"{item_path}.status", errors)
            task_head = _require_sha(task_result.get("head_sha"), f"{item_path}.head_sha", errors)
            verifier_ids = _require_string_list(task_result.get("verifier_ids"), f"{item_path}.verifier_ids", errors)
            task_commits = _require_string_list(task_result.get("commits"), f"{item_path}.commits", errors)
            _require_string_list(task_result.get("evidence_paths"), f"{item_path}.evidence_paths", errors)
            if task_id is not None:
                if task_id in task_results:
                    _issue(errors, "duplicate_task_result", f"{item_path}.task_id", "task result must be unique")
                else:
                    task_results[task_id] = task_result
            if task_status is not None and task_status != "worker_passed":
                _issue(errors, "task_not_passed", f"{item_path}.status", "must be worker_passed")
            if task_commits is not None:
                for commit_index, commit in enumerate(task_commits):
                    _require_sha(commit, f"{item_path}.commits[{commit_index}]", errors)
                if task_head is not None and task_commits and task_head != task_commits[-1]:
                    _issue(errors, "task_head_unreachable", f"{item_path}.head_sha", "must equal the task's final reported commit")
                if commits is not None and not set(task_commits).issubset(set(commits)):
                    _issue(errors, "task_commit_mismatch", f"{item_path}.commits", "must be a subset of worker commits")
            if verifier_ids is not None:
                for verifier_id in verifier_ids:
                    if verifier_id not in verifier_results:
                        _issue(errors, "verifier_evidence_missing", f"{item_path}.verifier_ids", f"no PASS evidence for {verifier_id}")

    if mission is not None:
        executable_tasks = {
            task.get("id"): task
            for task in mission.get("tasks", [])
            if isinstance(task, dict) and not task.get("replaced_by")
        }
        if set(task_results) != set(executable_tasks):
            _issue(
                errors,
                "incomplete_task_results",
                "worker_result.task_results",
                "must contain every executable non-superseded mission task exactly once",
            )
        required_worker_verifiers = {
            verifier.get("id")
            for verifier in mission.get("worker_verifiers", [])
            if isinstance(verifier, dict) and isinstance(verifier.get("id"), str)
        }
        for verifier_id in sorted(required_worker_verifiers):
            verifier = verifier_results.get(verifier_id)
            if verifier is None or verifier.get("status") != "PASS":
                _issue(errors, "required_verifier_missing", "worker_result.verifiers", f"required worker verifier {verifier_id} is not PASS")
        for task_id, task in executable_tasks.items():
            task_result = task_results.get(task_id)
            if task_result is None:
                continue
            required_task_verifiers = {
                verifier.get("id")
                for verifier in task.get("verifiers", [])
                if isinstance(verifier, dict) and isinstance(verifier.get("id"), str)
            }
            reported_ids = set(task_result.get("verifier_ids", []))
            for verifier_id in sorted(required_task_verifiers - reported_ids):
                _issue(errors, "required_verifier_missing", f"worker_result.task_results.{task_id}.verifier_ids", f"required task verifier {verifier_id} is missing")
            for verifier_id in sorted(required_task_verifiers):
                verifier = verifier_results.get(verifier_id)
                if verifier is None or verifier.get("status") != "PASS":
                    _issue(errors, "required_verifier_missing", "worker_result.verifiers", f"required task verifier {verifier_id} is not PASS")

    workspace_mode = worker.get("workspace_mode")
    if workspace_mode in ISOLATED_WORKSPACES:
        worktree_path = worker.get("worktree_path")
        if not isinstance(worktree_path, str) or not worktree_path:
            _issue(errors, "isolated_handoff_incomplete", "harness_run.workers.worktree_path", "isolated worker needs a worktree path")
        branch_ref = worker.get("branch_ref")
        if not isinstance(branch_ref, str) or not branch_ref:
            _issue(errors, "isolated_handoff_incomplete", "harness_run.workers.branch_ref", "isolated worker needs a durable branch/ref")
        branch_target = f"branch:{branch_ref}" if isinstance(branch_ref, str) and branch_ref else None
        if external_codex:
            if not isinstance(observed_worktree_path, str) or not observed_worktree_path:
                _issue(
                    errors,
                    "observed_worktree_missing",
                    "observed.worktree_path",
                    "parent-observed worktree path is required for external Codex",
                )
            elif observed_worktree_path != worktree_path:
                _issue(
                    errors,
                    "observed_worktree_mismatch",
                    "harness_run.workers.worktree_path",
                    "does not match the parent-observed external Codex worktree",
                )
            if not isinstance(observed_branch_ref, str) or not observed_branch_ref:
                _issue(
                    errors,
                    "observed_branch_missing",
                    "observed.branch_ref",
                    "parent-observed branch ref is required for external Codex",
                )
            elif observed_branch_ref != branch_ref:
                _issue(
                    errors,
                    "observed_branch_mismatch",
                    "harness_run.workers.branch_ref",
                    "does not match the parent-observed external Codex branch",
                )
            if not git_common_dir_confirmed:
                _issue(
                    errors,
                    "git_common_dir_unconfirmed",
                    "observed.git_common_dir",
                    "parent must confirm the external Codex worktree belongs to this repository",
                )
            external_actions = [
                ("invoke_external_runtime", "runtime:codex"),
                (
                    "spawn_subagents",
                    f"worker:{worker_id}" if isinstance(worker_id, str) and worker_id else None,
                ),
                (
                    "create_app_managed_worktrees",
                    f"worktree:{worktree_path}"
                    if isinstance(worktree_path, str) and worktree_path
                    else None,
                ),
                ("create_local_branches", branch_target),
            ]
            for action, target in external_actions:
                if mission_id is None or target is None or not authorization_covers(
                    run, action, mission_id, target
                ):
                    _issue(
                        errors,
                        "external_launch_not_authorized",
                        f"harness_run.authorizations.{action}",
                        f"external Codex handoff requires {action} authorization covering {target or 'its allocation'}",
                    )
        if mission_id is None or not authorization_covers(
            run, "create_local_commits", mission_id, branch_target
        ):
            _issue(
                errors,
                "commit_not_authorized",
                "harness_run.authorizations.create_local_commits",
                "isolated handoff requires commit authorization covering its branch",
            )
        if not commits:
            _issue(errors, "uncommitted_handoff", "worker_result.commits", "isolated handoff requires task commits")
        elif head_sha is not None and head_sha != commits[-1]:
            _issue(errors, "worker_head_unreachable", "worker_result.head_sha", "must equal the final worker commit")
        task_commit_lists = [
            task_result.get("commits", [])
            for task_result in task_results.values()
            if isinstance(task_result.get("commits"), list)
        ]
        if any(not task_commits for task_commits in task_commit_lists):
            _issue(errors, "uncommitted_task", "worker_result.task_results", "every task in an isolated handoff requires a commit")
        flattened = [commit for task_commits in task_commit_lists for commit in task_commits]
        if len(flattened) != len(set(flattened)):
            _issue(errors, "commit_reused", "worker_result.task_results", "one commit cannot satisfy multiple tasks")
        if commits is not None and set(flattened) != set(commits):
            _issue(errors, "unattributed_commit", "worker_result.commits", "every worker commit must belong to exactly one task result")

    return _sorted_errors(errors)


def _result_document(status: str, errors: list[dict[str, str]], result: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "errors": _sorted_errors(errors),
        "mission_id": result.get("mission_id") if isinstance(result, dict) else None,
        "status": status,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="Path to canonical PLAN.md")
    parser.add_argument("--run", required=True, help="Path to canonical RUN.md")
    parser.add_argument("--result", required=True, help="Path to worker-result Markdown")
    parser.add_argument("--observed-head-sha", required=True, help="Parent-observed worker head SHA")
    parser.add_argument(
        "--observed-changed-file",
        action="append",
        default=None,
        help="Parent-observed changed file; repeat for every path",
    )
    parser.add_argument(
        "--ancestry-confirmed",
        action="store_true",
        help="Assert the parent observed base as an ancestor of the worker head",
    )
    parser.add_argument(
        "--observed-worktree-path",
        help="Parent-observed retained worker worktree path",
    )
    parser.add_argument(
        "--observed-branch-ref",
        help="Parent-observed retained worker branch ref",
    )
    parser.add_argument(
        "--git-common-dir-confirmed",
        action="store_true",
        help="Assert the retained worktree belongs to the parent repository",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    errors: list[dict[str, str]] = []
    result: dict[str, Any] | None = None
    try:
        plan = load_plan(args.plan)
        run = load_run(args.run)
        result = load_worker_result(args.result)
    except (ManifestError, OSError, ValueError) as exc:
        _issue(errors, "manifest_load_failed", "input", str(exc))
        print(json.dumps(_result_document("FAIL", errors), sort_keys=True, separators=(",", ":")))
        return 1

    for message in validate_plan(plan):
        _issue(errors, "invalid_plan", "harness_plan", message)
    for message in validate_run(plan, run):
        _issue(errors, "invalid_run", "harness_run", message)
    if not errors:
        errors.extend(
            validate_worker_result_data(
                plan,
                run,
                result,
                observed_head_sha=args.observed_head_sha,
                observed_changed_files=args.observed_changed_file,
                ancestry_confirmed=args.ancestry_confirmed,
                observed_worktree_path=args.observed_worktree_path,
                observed_branch_ref=args.observed_branch_ref,
                git_common_dir_confirmed=args.git_common_dir_confirmed,
            )
        )

    status = "PASS" if not errors else "FAIL"
    print(json.dumps(_result_document(status, errors, result), sort_keys=True, separators=(",", ":")))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

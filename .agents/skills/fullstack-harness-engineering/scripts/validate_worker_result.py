#!/usr/bin/env python3
"""Validate a worker result against canonical PLAN/RUN state and observations."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
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
from select_verifiers import (
    VerifierSelectionError,
    applicable_targeted_verifiers,
    canonical_changed_path,
)
from verifier_runtime import PROTOCOL as VERIFIER_PROTOCOL, execution_key_from_document


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
SUBAGENT_REVIEW_FIELDS = {"reviewed_sha", "decision"}
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
    expected_head_sha: str | None,
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
    completed_reviewer = False
    for index, child in enumerate(children):
        child_path = f"{path}.children[{index}]"
        if not _check_exact_fields(
            child,
            SUBAGENT_CHILD_FIELDS,
            child_path,
            errors,
            optional=SUBAGENT_REVIEW_FIELDS,
        ):
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
        if role == "reviewer":
            if "reviewed_sha" not in child:
                _issue(errors, "missing_field", f"{child_path}.reviewed_sha", "reviewer must bind the reviewed head")
                reviewed_sha = None
            else:
                reviewed_sha = _require_sha(child.get("reviewed_sha"), f"{child_path}.reviewed_sha", errors)
            if reviewed_sha is not None and expected_head_sha is not None and reviewed_sha != expected_head_sha:
                _issue(errors, "stale_binding", f"{child_path}.reviewed_sha", "does not match worker_result.head_sha")
            if "decision" not in child:
                _issue(errors, "missing_field", f"{child_path}.decision", "reviewer must report a decision")
                decision = None
            else:
                decision = _require_string(child.get("decision"), f"{child_path}.decision", errors)
            if decision is not None and decision not in {"PASS", "fix_required"}:
                _issue(errors, "invalid_value", f"{child_path}.decision", "must be PASS or fix_required")
            if (
                child_status == "completed"
                and reviewed_sha is not None
                and reviewed_sha == expected_head_sha
                and decision == "PASS"
            ):
                completed_reviewer = True
        elif set(child) & SUBAGENT_REVIEW_FIELDS:
            _issue(
                errors,
                "invalid_value",
                child_path,
                "reviewed_sha and decision are allowed only for reviewer children",
            )
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
        if not completed_reviewer:
            _issue(
                errors,
                "missing_review",
                f"{path}.children",
                "enabled activity requires a completed exact-head PASS reviewer",
            )
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


def _require_execution_key(
    value: Any, path: str, errors: list[dict[str, str]]
) -> str | None:
    checked = _require_string(value, path, errors)
    if checked is None:
        return None
    if not DIGEST_RE.fullmatch(checked):
        _issue(
            errors,
            "invalid_execution_key",
            path,
            "must be the execution_key produced by verifier_runtime.py "
            "(64 lowercase hexadecimal characters), not free-form text",
        )
        return None
    return checked


def _canonical_changed_path(
    value: Any, path: str, errors: list[dict[str, str]]
) -> str | None:
    try:
        return canonical_changed_path(value)
    except VerifierSelectionError as exc:
        _issue(errors, "invalid_changed_path", path, str(exc))
        return None


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


def _declared_verifiers(
    mission: dict[str, Any] | None,
) -> dict[str, tuple[dict[str, Any], str, str | None]]:
    declared: dict[str, tuple[dict[str, Any], str, str | None]] = {}
    if not isinstance(mission, dict):
        return declared
    for verifier in mission.get("worker_verifiers", []):
        if isinstance(verifier, dict) and isinstance(verifier.get("id"), str):
            declared.setdefault(verifier["id"], (verifier, "worker", None))
    for task in mission.get("tasks", []):
        if not isinstance(task, dict) or task.get("replaced_by"):
            continue
        for verifier in task.get("verifiers", []):
            if isinstance(verifier, dict) and isinstance(verifier.get("id"), str):
                declared.setdefault(
                    verifier["id"], (verifier, "task", task.get("id"))
                )
    return declared


def _retained_verifier_results(
    values: list[dict[str, Any]] | None,
    *,
    run: dict[str, Any],
    result: dict[str, Any],
    mission: dict[str, Any] | None,
    observed_head_sha: str | None,
    observed_changed_files: list[str],
    errors: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    retained: dict[str, dict[str, Any]] = {}
    if not isinstance(values, list):
        _issue(
            errors,
            "retained_verifier_results_missing",
            "observed.verifier_results",
            "parent-retained verifier results are required",
        )
        return retained
    declarations = _declared_verifiers(mission)
    expected_checkout_dirty: bool | None = None
    workers = run.get("workers", [])
    worker_matches = [
        worker
        for worker in workers
        if isinstance(worker, dict)
        and worker.get("mission_id") == result.get("mission_id")
        and worker.get("lease_id") == result.get("lease_id")
    ] if isinstance(workers, list) else []
    worker = worker_matches[0] if len(worker_matches) == 1 else None
    observed_git = run.get("observed", {}).get("git", {})
    if isinstance(worker, dict) and worker.get("workspace_mode") in ISOLATED_WORKSPACES:
        observed_worktrees = (
            observed_git.get("worktrees", []) if isinstance(observed_git, dict) else []
        )
        matching_worktrees = [
            worktree
            for worktree in observed_worktrees
            if isinstance(worktree, dict)
            and worktree.get("path") == worker.get("worktree_path")
            and worktree.get("branch_ref") == worker.get("branch_ref")
            and worktree.get("head_sha") == observed_head_sha
        ]
        if len(matching_worktrees) != 1:
            _issue(
                errors,
                "worker_worktree_mismatch",
                "observed.git.worktrees",
                "exactly one parent-observed worker worktree must match path, branch, and head",
            )
        else:
            dirty = matching_worktrees[0].get("dirty")
            if not isinstance(dirty, bool):
                _issue(
                    errors,
                    "worker_worktree_mismatch",
                    "observed.git.worktrees.dirty",
                    "must be boolean",
                )
            else:
                expected_checkout_dirty = dirty
                if dirty:
                    _issue(
                        errors,
                        "dirty_worker_handoff",
                        "observed.git.worktrees.dirty",
                        "dirty isolated worker worktrees cannot produce accepted verifier evidence",
                    )
    elif isinstance(observed_git, dict) and isinstance(
        observed_git.get("parent_dirty"), bool
    ):
        expected_checkout_dirty = observed_git["parent_dirty"]

    expected_context = {
        "run_id": run.get("run_id"),
        "plan_revision": result.get("plan_revision"),
        "plan_digest_sha256": result.get("plan_digest_sha256"),
        "graph_revision": run.get("graph_state", {}).get("graph_revision"),
        "batch_base_sha": worker.get("batch_base_sha") if isinstance(worker, dict) else result.get("base_sha"),
        "head_sha": observed_head_sha,
        "changed_files": sorted(observed_changed_files),
        "trust_domain": "parent_local",
        "checkout_role": "worker",
        "checkout_dirty": expected_checkout_dirty,
    }
    for index, item in enumerate(values):
        path = f"observed.verifier_results[{index}]"
        if not isinstance(item, dict):
            _issue(errors, "invalid_type", path, "must be an object")
            continue
        verifier_id = item.get("verifier_id")
        if not isinstance(verifier_id, str) or not verifier_id:
            _issue(errors, "retained_verifier_mismatch", f"{path}.verifier_id", "must identify the verifier")
            continue
        retained[verifier_id] = item
        if item.get("protocol") != VERIFIER_PROTOCOL:
            _issue(errors, "retained_verifier_mismatch", f"{path}.protocol", "does not match verifier runtime protocol")
        key_document = item.get("key_document")
        execution_key = item.get("execution_key")
        if not isinstance(key_document, dict) or not isinstance(execution_key, str):
            _issue(
                errors,
                "retained_verifier_mismatch",
                path,
                "must retain the execution key document and key",
            )
        elif execution_key_from_document(key_document) != execution_key:
            _issue(
                errors,
                "retained_verifier_key_mismatch",
                f"{path}.execution_key",
                "does not match the retained key document",
            )
        elif key_document.get("protocol") != VERIFIER_PROTOCOL:
            _issue(
                errors,
                "retained_verifier_mismatch",
                f"{path}.key_document.protocol",
                "does not match verifier runtime protocol",
            )
        if item.get("evidence_key") != execution_key:
            _issue(errors, "retained_verifier_key_mismatch", f"{path}.evidence_key", "does not match execution_key")
        status = item.get("status")
        exit_code = item.get("exit_code")
        if status not in {"PASS", "FAIL", "TIMEOUT", "ERROR"}:
            _issue(errors, "retained_verifier_mismatch", f"{path}.status", "has an unsupported value")
        elif status == "PASS" and exit_code != 0:
            _issue(errors, "retained_verifier_mismatch", f"{path}.exit_code", "PASS requires exit code 0")
        elif status == "FAIL" and (
            not isinstance(exit_code, int) or isinstance(exit_code, bool) or exit_code == 0
        ):
            _issue(errors, "retained_verifier_mismatch", f"{path}.exit_code", "FAIL requires a nonzero integer exit code")
        elif status in {"TIMEOUT", "ERROR"} and exit_code is not None:
            _issue(errors, "retained_verifier_mismatch", f"{path}.exit_code", f"{status} requires null exit code")
        declaration_binding = declarations.get(verifier_id)
        declaration = declaration_binding[0] if declaration_binding is not None else None
        expected_layer = declaration_binding[1] if declaration_binding is not None else None
        expected_task_id = declaration_binding[2] if declaration_binding is not None else None
        context = item.get("context")
        if not isinstance(context, dict):
            _issue(errors, "retained_verifier_mismatch", f"{path}.context", "must retain verifier context")
        else:
            for field, expected in expected_context.items():
                if context.get(field) != expected:
                    _issue(errors, "retained_verifier_context_mismatch", f"{path}.context.{field}", "does not match parent-observed validation context")
            expected_identity = {
                "layer": expected_layer,
                "mission_id": result.get("mission_id"),
                "task_id": expected_task_id,
                "lease_id": result.get("lease_id"),
            }
            for field, expected in expected_identity.items():
                if context.get(field) != expected:
                    _issue(
                        errors,
                        "retained_verifier_context_mismatch",
                        f"{path}.context.{field}",
                        "does not match the declared verifier and worker lease",
                    )
            attempt_id = context.get("attempt_id")
            if not isinstance(attempt_id, str) or not attempt_id:
                _issue(
                    errors,
                    "retained_verifier_context_mismatch",
                    f"{path}.context.attempt_id",
                    "must bind a retained worker attempt",
                )
            else:
                matching_attempts = [
                    attempt
                    for attempt in run.get("attempt_log", [])
                    if isinstance(attempt, dict)
                    and attempt.get("attempt_id") == attempt_id
                    and attempt.get("mission_id") == result.get("mission_id")
                    and attempt.get("task_id") == expected_task_id
                    and attempt.get("lease_id") == result.get("lease_id")
                ]
                if len(matching_attempts) != 1:
                    _issue(
                        errors,
                        "retained_verifier_context_mismatch",
                        f"{path}.context.attempt_id",
                        "must reference the exact retained mission/task/lease attempt",
                    )
            if isinstance(key_document, dict):
                key_context = {
                    field: key_document.get(field)
                    for field in (
                        "run_id",
                        "plan_revision",
                        "plan_digest_sha256",
                        "graph_revision",
                        "batch_base_sha",
                        "head_sha",
                        "trust_domain",
                        "checkout_role",
                        "checkout_dirty",
                        "cache_safe",
                        "layer",
                        "mission_id",
                        "task_id",
                        "attempt_id",
                        "lease_id",
                    )
                }
                retained_context = {field: context.get(field) for field in key_context}
                changed_digest = hashlib.sha256(
                    json.dumps(
                        context.get("changed_files"),
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).hexdigest()
                if key_context != retained_context or key_document.get("changed_files_digest") != changed_digest:
                    _issue(errors, "retained_verifier_context_mismatch", f"{path}.key_document", "does not encode the retained verifier context")
        normalized = item.get("verifier")
        declared_cache = (
            declaration.get("cache")
            if isinstance(declaration, dict) and isinstance(declaration.get("cache"), dict)
            else {"mode": "disabled", "environment_keys": []}
        )
        if declaration is None or not isinstance(normalized, dict):
            _issue(errors, "retained_verifier_mismatch", f"{path}.verifier", "does not match a declared verifier")
        elif (
            normalized.get("id") != verifier_id
            or normalized.get("cwd") != declaration.get("cwd")
            or normalized.get("argv") != declaration.get("argv")
            or normalized.get("pass_signal") != declaration.get("pass_signal")
            or normalized.get("cache") != declared_cache
            or not isinstance(key_document, dict)
            or key_document.get("verifier_id") != verifier_id
            or key_document.get("cwd") != normalized.get("cwd")
            or key_document.get("argv") != normalized.get("argv")
            or key_document.get("pass_signal") != normalized.get("pass_signal")
            or key_document.get("cache_mode") != declared_cache.get("mode")
            or key_document.get("environment_keys")
            != sorted(declared_cache.get("environment_keys", []))
        ):
            _issue(
                errors,
                "retained_verifier_mismatch",
                f"{path}.verifier",
                "does not exactly match the declared and executed verifier",
            )
    return retained


def validate_worker_result_data(
    plan: dict[str, Any],
    run: dict[str, Any],
    result: dict[str, Any],
    *,
    observed_head_sha: str | None,
    observed_changed_files: list[str] | None,
    ancestry_confirmed: bool,
    retained_verifier_results: list[dict[str, Any]] | None = None,
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
    if isinstance(nested_policy, dict) and "subagent_activity" not in result:
        _issue(
            errors,
            "missing_field",
            "worker_result.subagent_activity",
            "is required because the worker records a nested-subagent policy",
        )
    if "subagent_activity" in result:
        _validate_subagent_activity(
            result.get("subagent_activity"),
            policy=nested_policy if isinstance(nested_policy, dict) else None,
            expected_head_sha=head_sha,
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
    for field in ("worker_runtime", "workspace_mode", "completion_channel"):
        if worker and worker.get(field) != runtime_capabilities.get(field):
            _issue(
                errors,
                "worker_record_mismatch",
                f"harness_run.workers.{field}",
                "does not match RUN runtime capabilities",
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
    retained_results: dict[str, dict[str, Any]] = {}
    if isinstance(verifier_results_raw, list) and verifier_results_raw:
        retained_results = _retained_verifier_results(
            retained_verifier_results,
            run=run,
            result=result,
            mission=mission,
            observed_head_sha=observed_checked,
            observed_changed_files=[
                path for path in observed_paths if not _report_exception(path, worker)
            ],
            errors=errors,
        )
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
            evidence_key = _require_execution_key(verifier.get("evidence"), f"{item_path}.evidence", errors)
            if verifier_id is not None:
                if verifier_id in verifier_results:
                    _issue(errors, "duplicate_verifier", f"{item_path}.id", "verifier ID must be unique")
                else:
                    verifier_results[verifier_id] = verifier
                retained = retained_results.get(verifier_id)
                if retained is None:
                    _issue(errors, "retained_verifier_result_missing", item_path, f"parent retained no result for {verifier_id}")
                else:
                    if retained.get("status") != "PASS" or retained.get("exit_code") != 0:
                        _issue(
                            errors,
                            "retained_verifier_not_pass",
                            item_path,
                            "latest exact retained execution must be PASS with exit code 0",
                        )
                    if verifier_status != retained.get("status"):
                        _issue(errors, "retained_verifier_result_mismatch", f"{item_path}.status", "does not match the parent-retained result")
                    if evidence_key != retained.get("execution_key"):
                        _issue(errors, "retained_verifier_result_mismatch", f"{item_path}.evidence", "does not match the parent-retained execution key")
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
        required_task_verifiers = {
            task_id: {
                verifier.get("id")
                for verifier in task.get("verifiers", [])
                if isinstance(verifier, dict) and isinstance(verifier.get("id"), str)
            }
            for task_id, task in executable_tasks.items()
        }
        observed_diff_is_valid = (
            observed_changed_files is not None
            and len(observed_paths) == len(observed_changed_files)
            and len(observed_paths) == len(set(observed_paths))
        )
        if observed_diff_is_valid:
            try:
                applicability = applicable_targeted_verifiers(mission, observed_paths)
                required_worker_verifiers = set(applicability["worker_verifier_ids"])
                required_task_verifiers = {
                    task_id: set(verifier_ids)
                    for task_id, verifier_ids in applicability[
                        "task_verifier_ids"
                    ].items()
                }
            except VerifierSelectionError as exc:
                _issue(
                    errors,
                    "invalid_verifier_selection",
                    "harness_plan.missions",
                    str(exc),
                )
        for verifier_id in sorted(required_worker_verifiers):
            verifier = verifier_results.get(verifier_id)
            if verifier is None or verifier.get("status") != "PASS":
                _issue(errors, "required_verifier_missing", "worker_result.verifiers", f"required worker verifier {verifier_id} is not PASS")
        for task_id in executable_tasks:
            task_result = task_results.get(task_id)
            if task_result is None:
                continue
            task_verifier_ids = required_task_verifiers.get(task_id, set())
            reported_ids = set(task_result.get("verifier_ids", []))
            for verifier_id in sorted(task_verifier_ids - reported_ids):
                _issue(errors, "required_verifier_missing", f"worker_result.task_results.{task_id}.verifier_ids", f"required task verifier {verifier_id} is missing")
            for verifier_id in sorted(task_verifier_ids):
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
        "--verifier-result",
        action="append",
        default=[],
        help="Parent-retained verifier_runtime.py JSON result; repeat for each verifier",
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
        retained_verifier_results = [
            json.loads(Path(path).read_text(encoding="utf-8"))
            for path in args.verifier_result
        ]
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
                retained_verifier_results=retained_verifier_results,
            )
        )

    status = "PASS" if not errors else "FAIL"
    print(json.dumps(_result_document(status, errors, result), sort_keys=True, separators=(",", ":")))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

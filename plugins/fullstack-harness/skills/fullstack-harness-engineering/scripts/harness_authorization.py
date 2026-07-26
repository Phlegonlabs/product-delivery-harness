#!/usr/bin/env python3
"""Authorization-ledger validation and coverage checks for harness RUN state."""

from __future__ import annotations

from typing import Any

from harness_core import (
    _add,
    _is_int,
    _keys,
    _nonempty_string,
    _strings,
)
from harness_schema import (
    CLOUD_RESOURCE_TARGET_RE,
    EXPIRY_BOUNDARIES,
    FUTURE_PR_TARGET_RE,
    GITHUB_PR_URL_RE,
    SHA256_RE,
    TARGET_RE,
)


def _validate_authorization_scope(
    errors: list[str],
    path: str,
    value: Any,
    *,
    action: bool,
    action_name: str | None = None,
    allow_future_pr: bool = False,
    require_plan_binding: bool = False,
) -> None:
    required = (
        {"run_id", "mission_ids", "targets"}
        if action
        else {"run_id", "mission_ids", "expires_when"}
    )
    if require_plan_binding:
        required.update({"plan_revision", "plan_digest_sha256"})
    if not _keys(errors, path, value, required):
        return
    if not _nonempty_string(value["run_id"]):
        _add(errors, f"{path}.run_id", "must be a non-empty string")
    if require_plan_binding:
        if not _is_int(value["plan_revision"]) or value["plan_revision"] < 1:
            _add(errors, f"{path}.plan_revision", "must be a positive integer")
        digest = value["plan_digest_sha256"]
        if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
            _add(errors, f"{path}.plan_digest_sha256", "must be a lowercase SHA-256 digest")
    _strings(errors, f"{path}.mission_ids", value["mission_ids"], nonempty=True)
    if action:
        targets = _strings(errors, f"{path}.targets", value["targets"], nonempty=True)
        for target in targets:
            if target == "*":
                if action_name in {"trigger_remote_ci", "provision_cloud_resources"}:
                    _add(
                        errors,
                        f"{path}.targets",
                        f"{action_name} requires exact targets, not *",
                    )
                continue
            if target.startswith("future-pr:"):
                if (
                    not allow_future_pr
                    or action_name not in {"manage_pr_review", "merge_pr"}
                    or not FUTURE_PR_TARGET_RE.fullmatch(target)
                ):
                    _add(errors, f"{path}.targets", f"unsupported target {target!r}")
                continue
            if not TARGET_RE.fullmatch(target):
                _add(errors, f"{path}.targets", f"unsupported target {target!r}")
            elif action_name == "invoke_external_runtime" and not target.startswith(
                "runtime:"
            ):
                _add(
                    errors,
                    f"{path}.targets",
                    "invoke_external_runtime requires runtime:<provider> targets",
                )
            elif action_name == "trigger_remote_ci" and not target.startswith("workflow:"):
                _add(
                    errors,
                    f"{path}.targets",
                    "trigger_remote_ci requires workflow:<identity> targets",
                )
            elif action_name == "provision_cloud_resources" and not CLOUD_RESOURCE_TARGET_RE.fullmatch(
                target
            ):
                _add(
                    errors,
                    f"{path}.targets",
                    "provision_cloud_resources requires cloud-resource:<provider>:<environment>:<kind>:<logical-name> targets",
                )
    else:
        if value["expires_when"] not in EXPIRY_BOUNDARIES:
            _add(
                errors,
                f"{path}.expires_when",
                "must be wave_closed, run_complete, or explicit_revocation",
            )


def _scope_matches_plan(run: dict[str, Any], scope: dict[str, Any]) -> bool:
    if run.get("schema_version") != 10:
        return True
    plan = run.get("plan")
    return (
        isinstance(plan, dict)
        and scope.get("plan_revision") == plan.get("revision")
        and scope.get("plan_digest_sha256") == plan.get("digest_sha256")
    )


def authorization_covers(
    run: dict[str, Any],
    action: str,
    mission_id: str,
    target: str | None = None,
    *,
    preserve_completed_run_expiry: bool = False,
) -> bool:
    authorizations = run.get("authorizations")
    if not isinstance(authorizations, dict):
        return False
    entry = authorizations.get(action, {})
    if not isinstance(entry, dict) or entry.get("authorized") is not True:
        return False
    scope = entry.get("scope")
    if (
        not isinstance(scope, dict)
        or scope.get("run_id") != run.get("run_id")
        or not _scope_matches_plan(run, scope)
    ):
        return False
    missions = scope.get("mission_ids", [])
    if mission_id not in missions and "*" not in missions:
        return False
    targets = scope.get("targets", [])
    if target is not None and target not in targets and "*" not in targets:
        return False
    boundary = entry.get("expires_when")
    expiry_is_preserved = (
        preserve_completed_run_expiry
        and boundary == "run_complete"
        and run.get("status") == "complete"
    )
    return _nonempty_string(entry.get("source")) and (
        expiry_is_preserved or _authorization_not_expired(run, boundary)
    )


def _landing_future_pr_target(landing: dict[str, Any]) -> str | None:
    pr_url = landing.get("pr_url")
    base_branch = landing.get("base_branch")
    head_branch = landing.get("head_branch")
    if (
        not _nonempty_string(pr_url)
        or not _nonempty_string(base_branch)
        or not _nonempty_string(head_branch)
    ):
        return None
    match = GITHUB_PR_URL_RE.fullmatch(pr_url)
    if match is None:
        return None
    return (
        f"future-pr:{match.group('repository')}:"
        f"base={base_branch}:head={head_branch}"
    )


def execution_covers(run: dict[str, Any], mission_id: str) -> bool:
    if run.get("execution_authorized") is not True:
        return False
    if not _nonempty_string(run.get("execution_authorization_source")):
        return False
    scope = run.get("execution_authorization_scope")
    if (
        not isinstance(scope, dict)
        or scope.get("run_id") != run.get("run_id")
        or not _scope_matches_plan(run, scope)
    ):
        return False
    missions = scope.get("mission_ids", [])
    return (mission_id in missions or "*" in missions) and _authorization_not_expired(
        run, scope.get("expires_when")
    )


def _authorization_not_expired(run: dict[str, Any], boundary: Any) -> bool:
    if boundary == "explicit_revocation":
        return True
    if boundary == "run_complete":
        return run.get("status") != "complete"
    if boundary == "wave_closed":
        return run.get("active_wave", {}).get("status") not in {"closed", "superseded"}
    return False

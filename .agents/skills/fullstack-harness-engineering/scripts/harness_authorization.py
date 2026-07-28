#!/usr/bin/env python3
"""Authorization-ledger validation and coverage checks for harness RUN state."""

from __future__ import annotations

from typing import Any

from harness_core import (
    _add,
    _is_int,
    _keys,
    _nonempty_string,
    _normalized_branch,
    _strings,
)
from harness_schema import (
    EXPIRY_BOUNDARIES,
    SHA256_RE,
    TARGET_RE,
    action_target_kind_allowed,
    action_target_kind_description,
)


def _is_main_branch_target(target: Any) -> bool:
    """Return whether an exact branch target resolves to main."""

    return (
        isinstance(target, str)
        and target.startswith("branch:")
        and _normalized_branch(target.split(":", 1)[1]) == "main"
    )


def _integration_branch(run: dict[str, Any]) -> str | None:
    integration = run.get("integration")
    if isinstance(integration, dict) and _nonempty_string(integration.get("branch")):
        return integration["branch"]
    return None


def _validate_authorization_scope(
    errors: list[str],
    path: str,
    value: Any,
    *,
    action: bool,
    action_name: str | None = None,
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
    if not action:
        if value["expires_when"] not in EXPIRY_BOUNDARIES:
            _add(
                errors,
                f"{path}.expires_when",
                "must be wave_closed, run_complete, or explicit_revocation",
            )
        return
    targets = _strings(errors, f"{path}.targets", value["targets"], nonempty=True)
    for target in targets:
        if target == "*":
            continue
        if TARGET_RE.fullmatch(target) is None:
            _add(errors, f"{path}.targets", f"unsupported target {target!r}")
        elif not action_target_kind_allowed(action_name, target):
            _add(
                errors,
                f"{path}.targets",
                f"{action_name or 'action'} target kind must be "
                f"{action_target_kind_description(action_name or '')}; got {target!r}",
            )
        if action_name == "push" and _is_main_branch_target(target):
            _add(
                errors,
                f"{path}.targets",
                "direct push to main is forbidden; land on main yourself",
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


def _covers_target(targets: Any, target: str | None) -> bool:
    """Whether an exact target is listed, comparing branch refs by identity."""

    if not isinstance(targets, list):
        # A malformed scope covers nothing. Without this guard a bare string
        # would fall through to `in` and match on any substring.
        return False
    if target is None or "*" in targets:
        return True
    if target in targets:
        return True
    if not target.startswith("branch:"):
        return False
    # `codex/x` and `refs/heads/codex/x` name one branch. Comparing the raw
    # strings made an otherwise valid grant unusable over a spelling difference.
    wanted = _normalized_branch(target.split(":", 1)[1])
    return wanted is not None and any(
        isinstance(item, str)
        and item.startswith("branch:")
        and _normalized_branch(item.split(":", 1)[1]) == wanted
        for item in targets
    )


def authorization_covers(
    run: dict[str, Any],
    action: str,
    mission_id: str,
    target: str | None = None,
    *,
    preserve_completed_run_expiry: bool = False,
    required_head_sha: str | None = None,
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
    missions = scope.get("mission_ids")
    if not isinstance(missions, list) or (
        mission_id not in missions and "*" not in missions
    ):
        return False
    targets = scope.get("targets")
    if action == "push" and (
        _normalized_branch(_integration_branch(run)) == "main"
        or _is_main_branch_target(target)
        or (isinstance(targets, list) and any(_is_main_branch_target(t) for t in targets))
    ):
        return False
    if not _covers_target(targets, target):
        return False
    if (
        required_head_sha is not None
        and entry.get("authorized_head_sha") != required_head_sha
    ):
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
    missions = scope.get("mission_ids")
    if not isinstance(missions, list):
        return False
    return (mission_id in missions or "*" in missions) and _authorization_not_expired(
        run, scope.get("expires_when")
    )


def _authorization_not_expired(run: dict[str, Any], boundary: Any) -> bool:
    if boundary == "explicit_revocation":
        return True
    if boundary == "run_complete":
        return run.get("status") != "complete"
    if boundary == "wave_closed":
        # `or {}` rather than a get() default: the key is often present as null.
        wave = run.get("active_wave") or {}
        return isinstance(wave, dict) and wave.get("status") not in {
            "closed",
            "superseded",
        }
    return False

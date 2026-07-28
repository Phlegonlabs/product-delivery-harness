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
    is_full_sha,
)
from harness_schema import (
    EXTERNAL_MERGE_CONTRACT,
    EXPIRY_BOUNDARIES,
    FUTURE_PR_TARGET_RE,
    GITHUB_PR_URL_RE,
    SHA256_RE,
    TARGET_RE,
    action_target_kind_allowed,
    action_target_kind_description,
)


def is_external_human_merge(run: Any) -> bool:
    """Return whether RUN retains exact actor/event proof of an external merge."""

    if not isinstance(run, dict) or run.get("schema_version") != 10:
        return False
    landing = run.get("landing")
    authorizations = run.get("authorizations")
    if not isinstance(landing, dict) or not isinstance(authorizations, dict):
        return False
    merge_entry = authorizations.get("merge_pr")
    observation = landing.get("external_merge_observation")
    return (
        landing.get("mode") in {"pull_request", "integration_pull_request"}
        and landing.get("pr_state") == "merged"
        and landing.get("merge_status") == "merged"
        and landing.get("auto_merge_requested") is False
        and isinstance(merge_entry, dict)
        and merge_entry.get("authorized") is False
        and isinstance(observation, dict)
        and set(observation)
        == {
            "kind",
            "actor",
            "event_ref",
            "pr_url",
            "pr_head_sha",
            "merged_sha",
        }
        and observation.get("kind") == "external_human"
        and _nonempty_string(observation.get("actor"))
        and _nonempty_string(observation.get("event_ref"))
        and observation.get("pr_url") == landing.get("pr_url")
        and is_full_sha(observation.get("pr_head_sha"))
        and observation.get("pr_head_sha") == landing.get("pr_head_sha")
        and is_full_sha(observation.get("merged_sha"))
        and observation.get("merged_sha") == landing.get("merged_sha")
    )


def is_legacy_completed_external_merge(run: Any) -> bool:
    """Allow only completed v10 history created before actor evidence existed."""

    if not isinstance(run, dict):
        return False
    landing = run.get("landing")
    return (
        run.get("schema_version") == 10
        and run.get("status") == "complete"
        and run.get("external_merge_contract") != EXTERNAL_MERGE_CONTRACT
        and isinstance(landing, dict)
        and landing.get("external_merge_observation") is None
    )


def is_legacy_completed_unmarked_run(run: Any) -> bool:
    """Return whether completed v10 history predates the current contract marker."""

    return (
        isinstance(run, dict)
        and run.get("schema_version") == 10
        and run.get("status") == "complete"
        and "action_target_contract" not in run
    )


def _validate_authorization_scope(
    errors: list[str],
    path: str,
    value: Any,
    *,
    action: bool,
    action_name: str | None = None,
    require_plan_binding: bool = False,
    schema_version: int | None = None,
    strict_action_targets: bool = False,
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
        resolved_schema_version = schema_version or 5
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
            malformed_future_pr = (
                target.startswith("future-pr:")
                and FUTURE_PR_TARGET_RE.fullmatch(target) is None
            )
            if (
                (not target.startswith("future-pr:") and TARGET_RE.fullmatch(target) is None)
                or malformed_future_pr
                or (
                    target.startswith("future-pr:")
                    and (
                        resolved_schema_version < 6
                        or action_name
                        not in {"create_pr", "manage_pr_review", "merge_pr"}
                    )
                )
            ):
                _add(errors, f"{path}.targets", f"unsupported target {target!r}")
            elif not action_target_kind_allowed(
                action_name,
                target,
                resolved_schema_version,
                strict=strict_action_targets,
            ):
                if action_name == "trigger_remote_ci":
                    message = "trigger_remote_ci requires workflow:<identity> targets"
                elif action_name == "provision_cloud_resources":
                    message = (
                        "provision_cloud_resources requires "
                        "cloud-resource:<provider>:<environment>:<kind>:<logical-name> targets"
                    )
                else:
                    message = (
                        f"{action_name or 'action'} target kind must be "
                        f"{action_target_kind_description(action_name or '', resolved_schema_version)}; "
                        f"got {target!r}"
                    )
                _add(errors, f"{path}.targets", message)
    else:
        if value["expires_when"] not in EXPIRY_BOUNDARIES:
            _add(
                errors,
                f"{path}.expires_when",
                "must be wave_closed, run_complete, or explicit_revocation",
            )


def _integration_branch(run: dict[str, Any]) -> str | None:
    integration = run.get("integration")
    if isinstance(integration, dict) and _nonempty_string(integration.get("branch")):
        return integration["branch"]
    return None


def future_pr_target_matches_landing(
    target: str,
    landing: Any,
    *,
    integration_branch: Any = None,
) -> bool:
    """Whether a future PR target describes the same landing identity."""
    future_pr = FUTURE_PR_TARGET_RE.fullmatch(target)
    if future_pr is None or not isinstance(landing, dict):
        return False
    target_base = _normalized_branch(future_pr.group("base"))
    landing_base = _normalized_branch(landing.get("base_branch"))
    if target_base != landing_base:
        return False
    if (
        integration_branch is not None
        and target_base != _normalized_branch(integration_branch)
    ):
        return False
    if _normalized_branch(future_pr.group("head")) != _normalized_branch(
        landing.get("head_branch")
    ):
        return False
    landing_pr_url = landing.get("pr_url")
    if not _nonempty_string(landing_pr_url):
        return True
    landing_pr = GITHUB_PR_URL_RE.fullmatch(landing_pr_url)
    return (
        landing_pr is not None
        and future_pr.group("repository").casefold()
        == landing_pr.group("repository").casefold()
    )


def _resolved_branch_protection(run: dict[str, Any], branch: Any) -> bool | None:
    """Resolve branch protection from the recorded landing model.

    Repository policy always protects `main`, even if a malformed or stale RUN
    labels it as an integration branch. A non-`main` integration PR base is
    treated as unprotected only when RUN carries a repository-sourced protection
    record bound to that exact branch.
    `pull_request` and the non-PR modes record a protected landing base beside
    the run's non-protected integration head. `integration_pull_request`
    instead records a genuine non-protected integration base. Missing or
    internally inconsistent state is unknown and therefore fails closed.
    """
    landing = run.get("landing")
    integration = run.get("integration")
    if not isinstance(landing, dict) or not isinstance(integration, dict):
        return None
    mode = landing.get("mode")
    normalized_branch = _normalized_branch(branch)
    normalized_base = _normalized_branch(landing.get("base_branch"))
    normalized_head = _normalized_branch(landing.get("head_branch"))
    normalized_integration = _normalized_branch(integration.get("branch"))
    if normalized_branch == "main":
        return True
    if (
        normalized_branch is None
        or normalized_base is None
        or normalized_head is None
        or normalized_integration is None
    ):
        return None
    if mode == "integration_pull_request":
        if (
            normalized_base != normalized_integration
            or normalized_head == normalized_integration
        ):
            return None
        protection = landing.get("base_branch_protection")
        if (
            normalized_branch != normalized_integration
            or not isinstance(protection, dict)
            or not _nonempty_string(protection.get("branch_ref"))
            or not str(protection.get("branch_ref")).startswith("refs/heads/")
            or _normalized_branch(protection.get("branch_ref")) != normalized_base
            or not _nonempty_string(protection.get("source"))
        ):
            # Only explicitly unmarked completed history predates this evidence.
            # Current-contract runs fail closed even after completion so their
            # retained target provenance cannot launder a protected base.
            return False if is_legacy_completed_unmarked_run(run) else None
        if protection.get("status") == "protected":
            return True
        if protection.get("status") == "unprotected":
            return False
        return None
    if mode not in {"local_only", "integration_push", "pull_request"}:
        return None
    if (
        normalized_head != normalized_integration
        or normalized_head == normalized_base
    ):
        return None
    if normalized_branch == normalized_base:
        return True
    if normalized_branch == normalized_integration:
        return False
    return None


def execution_intent_target_in_scope(
    plan: dict[str, Any], run: dict[str, Any], action: str, target: str
) -> bool:
    """Whether one execution-intent instruction can cover this exact target.

    The grouped development-loop bundle is scoped, not general: it reaches the
    resolved integration branch and a PR merging into that branch. Everything
    else — the protected landing branch, a promotion PR, or any deploy target —
    is its own authorization moment. Unknown state fails closed, because a target
    we cannot prove is in-scope is exactly the one that needs a separate recorded
    instruction.
    """
    if target == "*":
        return False
    branch = _integration_branch(run)
    normalized_integration_branch = _normalized_branch(branch)
    if normalized_integration_branch is None:
        return False
    if action == "push":
        # The loop may push only a resolved non-protected integration branch.
        # A protected base or unresolved branch model needs its own instruction.
        if _resolved_branch_protection(run, branch) is not False:
            return False
        return target == f"branch:{branch}"
    if action == "merge_pr":
        future_pr = FUTURE_PR_TARGET_RE.fullmatch(target)
        landing = run.get("landing")
        landing_base = (
            landing.get("base_branch") if isinstance(landing, dict) else None
        )
        landing_pr_url = (
            landing.get("pr_url") if isinstance(landing, dict) else None
        )
        landing_pr = (
            GITHUB_PR_URL_RE.fullmatch(landing_pr_url)
            if _nonempty_string(landing_pr_url)
            else None
        )
        target_base = future_pr.group("base") if future_pr is not None else landing_base
        if (
            not isinstance(landing, dict)
            or landing.get("mode") != "integration_pull_request"
            or _resolved_branch_protection(run, target_base) is not False
        ):
            # Only a PR into the resolved non-protected integration branch can
            # ride the development loop. Protected and unknown bases stay out.
            return False
        if future_pr is not None:
            return future_pr_target_matches_landing(
                target,
                landing,
                integration_branch=branch,
            )
        if target.startswith("pr:"):
            exact_target_matches = (
                landing_pr is not None
                and target == f"pr:{landing_pr_url}"
                and _normalized_branch(landing_base)
                == normalized_integration_branch
            )
            # A `pr:` target names a PR that already exists, so the generic
            # instruction can only have covered it if the same entry also carries
            # the matching `future-pr:` identity the grant was written against.
            # That sibling is what binds the exact PR to one repository.
            authorizations = run.get("authorizations")
            merge_entry = (
                authorizations.get("merge_pr")
                if isinstance(authorizations, dict)
                else None
            )
            scope = (
                merge_entry.get("scope") if isinstance(merge_entry, dict) else None
            )
            scope_targets = (
                scope.get("targets") if isinstance(scope, dict) else None
            )
            return exact_target_matches and isinstance(scope_targets, list) and any(
                isinstance(sibling, str)
                and future_pr_target_matches_landing(
                    sibling,
                    landing,
                    integration_branch=branch,
                )
                for sibling in scope_targets
            )
        # A merge-triggered release records the release consequence on the merge
        # itself, but deployment never rides the development-loop instruction.
        # Its exact release target retains the separate authorization source.
        if target.startswith("release:"):
            return False
        return False
    if action == "deploy":
        return False
    return False


def validate_target_sources(
    errors: list[str],
    path: str,
    entry: dict[str, Any],
    *,
    plan: dict[str, Any],
    run: dict[str, Any],
    action: str,
) -> None:
    """Require a separate recorded source for every out-of-scope target.

    Without this, one "build it" recorded as the entry `source` silently covers
    a push to the protected branch, a merge of the promotion PR, or a production
    deploy, because the entry has a single `source` for a whole target list.
    """
    scope = entry.get("scope")
    targets = scope.get("targets", []) if isinstance(scope, dict) else []
    if not isinstance(targets, list):
        return
    raw = entry.get("target_sources")
    target_sources: dict[str, Any] = {}
    if raw is not None:
        if not isinstance(raw, dict):
            _add(
                errors,
                f"{path}.target_sources",
                "must be an object mapping an exact target to its own authorization source",
            )
            return
        target_sources = raw

    for target, source in target_sources.items():
        if target not in targets:
            _add(
                errors,
                f"{path}.target_sources",
                f"{target!r} is not listed in scope.targets",
            )
        elif not _nonempty_string(source):
            _add(
                errors,
                f"{path}.target_sources.{target}",
                "must be a non-empty authorization source",
            )
        elif source == entry.get("source"):
            _add(
                errors,
                f"{path}.target_sources.{target}",
                "must record the separate instruction that authorized this target, "
                "not repeat the entry source",
            )

    for target in targets:
        if execution_intent_target_in_scope(plan, run, action, target):
            continue
        if not _nonempty_string(target_sources.get(target)):
            _add(
                errors,
                f"{path}.target_sources.{target}",
                f"{target!r} is outside what one execution-intent instruction covers "
                f"for {action} and requires its own recorded authorization source",
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
    missions = scope.get("mission_ids", [])
    if mission_id not in missions and "*" not in missions:
        return False
    targets = scope.get("targets", [])
    if target is not None and target not in targets and "*" not in targets:
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

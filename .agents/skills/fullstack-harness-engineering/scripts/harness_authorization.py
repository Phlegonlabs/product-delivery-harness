#!/usr/bin/env python3
"""Authorization-ledger validation and coverage checks for harness RUN state."""

from __future__ import annotations

import re
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
    SHA_RE,
    TARGET_RE,
    action_target_kind_allowed,
    action_target_kind_description,
)


_REMOTE_ACTION_RE = re.compile(r"\b(?:push|publish)\b", re.IGNORECASE)
_REMOTE_ACTION_WORDS = r"(?:push(?:ing)?|publish(?:ing)?)"
_NEGATED_OR_FORBIDDEN_REMOTE_RE = re.compile(
    rf"(?:"
    rf"\b(?:do\s+not|don't|dont|never|without|no|not|cannot|can't|cant|"
    rf"won't|wouldn't|shouldn't|not\s+permitted|not\s+allowed)\b"
    rf"[^.!?\n]{{0,120}}\b(?:{_REMOTE_ACTION_WORDS}|remote)\b"
    rf"|\b(?:{_REMOTE_ACTION_WORDS}|remote)\b"
    rf"[^.!?\n]{{0,120}}\b(?:forbidden|prohibited|disallowed|unauthorized|"
    rf"not\s+authorized|not\s+approved|not\s+requested)\b"
    rf")",
    re.IGNORECASE,
)
# Conditional/descriptive nouns do not grant a remote action.  In particular,
# ``permission is needed to publish`` and ``publish after approval`` describe
# a gate rather than authorizing the action.  Requests are handled separately
# so the positive verb in ``request a publish`` remains usable.
_CONDITIONAL_REMOTE_NOUN_RE = re.compile(
    rf"(?:"
    rf"\b(?:approval|permission|authorization|consent|clearance|access|"
    rf"ability|option|condition|requirement)\b[^.!?\n]{{0,120}}"
    rf"\b(?:{_REMOTE_ACTION_WORDS})\b"
    rf"|\b(?:{_REMOTE_ACTION_WORDS})\b[^.!?\n]{{0,120}}"
    rf"\b(?:approval|permission|authorization|consent|clearance|access|"
    rf"ability|option|condition|requirement)\b"
    rf"|\b(?:the|a|an|this|that|your|their|our|my)\s+request\b"
    rf"[^.!?\n]{{0,120}}\b(?:{_REMOTE_ACTION_WORDS})\b"
    rf"|\brequest\b\s+(?:is|are|was|were|pending|required|needed|"
    rf"awaiting)\b[^.!?\n]{{0,120}}\b(?:{_REMOTE_ACTION_WORDS})\b"
    rf")",
    re.IGNORECASE,
)
_CONDITIONAL_REMOTE_RE = re.compile(
    rf"(?:"
    rf"\b(?:if|when|unless|after|before|once|until|provided|pending|"
    rf"subject\s+to)\b[^.!?\n]{{0,120}}\b(?:{_REMOTE_ACTION_WORDS})\b"
    rf"|\b(?:{_REMOTE_ACTION_WORDS})\b[^.!?\n]{{0,120}}"
    rf"\b(?:if|when|unless|after|before|once|until|provided|pending|"
    rf"required|needed|subject\s+to)\b"
    rf")",
    re.IGNORECASE,
)
# A bare noun such as ``the push endpoint`` or ``remote API`` is not an
# instruction.  Imperatives may appear at the start of a source statement or
# after a short conjunction, which covers common ``implement and push``
# wording without treating arbitrary prose as permission.
_PUSH_PUBLISH_IMPERATIVE_RE = re.compile(
    r"(?:^|[:;,]|\b(?:and|then|please)\s+)\s*(?:push|publish)\b",
    re.IGNORECASE,
)
_NON_IMPERATIVE_REMOTE_RE = re.compile(
    r"\b(?:push|publish)\b(?:\s+\w+){0,4}\s+"
    r"\b(?:is|are|was|were|endpoint|api|access|permission|status|available|allowed|enabled|disabled)\b",
    re.IGNORECASE,
)
# Only positive authorize/approve/request verbs are attestations.  Nouns such
# as ``approval`` and ``permission`` are intentionally absent.  Inflected
# forms are accepted when a subject makes them verbs; the imperative branch
# accepts concise ``approve the push`` / ``request a publish`` statements.
_REMOTE_AUTHORIZATION_VERBS = (
    r"(?:authori[sz](?:e|es|ed|ing)|approv(?:e|es|ed|ing)|"
    r"request(?:s|ed|ing)?)"
)
_REMOTE_AUTHORIZATION_BASE_VERBS = r"(?:authori[sz]e|approve|request)"
_PUSH_PUBLISH_ATTESTATION_RE = re.compile(
    rf"(?:"
    rf"(?:^|[:;,]|\b(?:I|we|you|user|human|parent)\s+)\s*"
    rf"(?:hereby\s+)?{_REMOTE_AUTHORIZATION_VERBS}\b"
    rf"[^.!?\n]{{0,120}}\b(?:{_REMOTE_ACTION_WORDS})\b"
    rf"|(?:^|[:;,]|\b(?:and|then|please)\s+)\s*"
    rf"{_REMOTE_AUTHORIZATION_BASE_VERBS}\b"
    rf"[^.!?\n]{{0,120}}\b(?:{_REMOTE_ACTION_WORDS})\b"
    rf")",
    re.IGNORECASE,
)


def is_explicit_remote_intent(source: Any) -> bool:
    """Return whether ``source`` is an unambiguous push authorization.

    Remote nouns (``remote``/``ship``), API descriptions, and ordinary local
    implementation prose are not intent.  A source must contain a push or
    publish imperative, or an explicit positive authorize/approve/request
    verb.  Any negated, forbidden, or conditional remote statement poisons the
    whole source so a later positive-looking phrase cannot turn a refusal into
    permission.
    """

    if not isinstance(source, str) or not source.strip():
        return False
    statement = " ".join(source.split())
    if (
        _NEGATED_OR_FORBIDDEN_REMOTE_RE.search(statement)
        or _CONDITIONAL_REMOTE_NOUN_RE.search(statement)
        or _CONDITIONAL_REMOTE_RE.search(statement)
        or _NON_IMPERATIVE_REMOTE_RE.search(statement)
    ):
        return False
    return bool(
        _PUSH_PUBLISH_IMPERATIVE_RE.search(statement)
        or _PUSH_PUBLISH_ATTESTATION_RE.search(statement)
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
    expires_when: str | None = None,
) -> None:
    required = (
        {"run_id", "mission_ids", "targets"}
        if action
        else {"run_id", "mission_ids", "expires_when"}
    )
    if require_plan_binding:
        required.update({"plan_revision", "plan_digest_sha256"})
    if expires_when == "wave_closed":
        required.update({"wave_id", "batch_base_sha"})
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
    if expires_when == "wave_closed":
        if not _nonempty_string(value["wave_id"]):
            _add(errors, f"{path}.wave_id", "must be a non-empty string")
        if not isinstance(value["batch_base_sha"], str) or SHA_RE.fullmatch(
            value["batch_base_sha"]
        ) is None:
            _add(errors, f"{path}.batch_base_sha", "must be a full Git SHA")
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
    if run.get("schema_version") not in {10, 11}:
        return True
    plan = run.get("plan")
    return (
        isinstance(plan, dict)
        and scope.get("plan_revision") == plan.get("revision")
        and scope.get("plan_digest_sha256") == plan.get("digest_sha256")
    )


def observed_default_branch(run: dict[str, Any]) -> str | None:
    """Return an observed default branch when one was captured.

    ``observed.git.default_branch`` is the canonical optional location.  The
    two legacy-shaped aliases are read defensively so a parent handoff from an
    older tool can still be interpreted without a schema migration.
    """

    observed = run.get("observed")
    if not isinstance(observed, dict):
        return None
    git = observed.get("git")
    candidates = (
        (git, "default_branch"),
        (git, "default_branch_ref"),
        (observed, "default_branch"),
        (observed, "default_branch_ref"),
    )
    for container, key in candidates:
        if isinstance(container, dict) and _nonempty_string(container.get(key)):
            return container[key]
    return None


def _target_branch(target: Any) -> str | None:
    if not isinstance(target, str) or not target.startswith("branch:"):
        return None
    return _normalized_branch(target.split(":", 1)[1])


def _v10_push_is_current_and_safe(
    run: dict[str, Any], entry: dict[str, Any], target: str | None
) -> bool:
    """Require a current, exact, non-default branch push in RUN-v11."""

    integration_branch = _integration_branch(run)
    requested_branch = _target_branch(target)
    if integration_branch is None or requested_branch is None:
        return False
    resolved_integration = _normalized_branch(integration_branch)
    if resolved_integration is None or requested_branch != resolved_integration:
        return False

    default_branch = observed_default_branch(run)
    # A current push must fail closed when the repository's default branch is
    # unknown.  This gate is intentionally scoped to push; local actions remain
    # usable while the parent gathers the optional observation.
    if default_branch is None:
        return False
    normalized_default = _normalized_branch(default_branch)
    if normalized_default is None or resolved_integration == normalized_default:
        return False

    scope = entry.get("scope")
    targets = scope.get("targets") if isinstance(scope, dict) else None
    if not isinstance(targets, list) or len(targets) != 1:
        return False
    scoped_branch = _target_branch(targets[0])
    if scoped_branch != resolved_integration:
        return False

    authorized_head = entry.get("authorized_head_sha")
    integration = run.get("integration")
    current_head = (
        integration.get("integration_head_sha")
        if isinstance(integration, dict)
        else None
    )
    if not isinstance(authorized_head, str) or SHA_RE.fullmatch(authorized_head) is None:
        return False
    if not isinstance(current_head, str) or SHA_RE.fullmatch(current_head) is None:
        return False
    return authorized_head == current_head


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
    require_exact_target: bool = False,
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
    if not isinstance(missions, list):
        return False
    if require_exact_target:
        if "*" in missions or mission_id not in missions:
            return False
    elif mission_id not in missions and "*" not in missions:
        return False
    targets = scope.get("targets")
    if action == "push" and (
        _normalized_branch(_integration_branch(run)) == "main"
        or _is_main_branch_target(target)
        or (isinstance(targets, list) and any(_is_main_branch_target(t) for t in targets))
    ):
        return False
    historical_completed_push = (
        action == "push"
        and preserve_completed_run_expiry
        and run.get("status") == "complete"
        and entry.get("expires_when") == "run_complete"
    )
    if action == "push" and run.get("schema_version") in {10, 11}:
        # A completed RUN may retain a run_complete grant as historical
        # evidence, but that expiry exception never relaxes remote intent or
        # the current exact branch/default/head safety gates.
        if not is_explicit_remote_intent(entry.get("source")):
            return False
        if not _v10_push_is_current_and_safe(run, entry, target):
            return False
    checked_targets = targets
    if require_exact_target:
        if target is None or not isinstance(targets, list):
            return False
        checked_targets = [item for item in targets if item != "*"]
    if not _covers_target(checked_targets, target):
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
        expiry_is_preserved or _authorization_not_expired(run, boundary, scope)
    )


def execution_covers(
    run: dict[str, Any],
    mission_id: str,
    *,
    preserve_completed_run_expiry: bool = False,
) -> bool:
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
    boundary = scope.get("expires_when")
    expiry_is_preserved = (
        preserve_completed_run_expiry
        and boundary == "run_complete"
        and run.get("status") == "complete"
    )
    return (mission_id in missions or "*" in missions) and (
        expiry_is_preserved or _authorization_not_expired(run, boundary, scope)
    )


def _closed_wave_pairs(run: dict[str, Any]) -> set[tuple[str, str]] | None:
    """Validate and normalize the v10 closed-wave tombstone list.

    Coverage must fail closed independently of ``validate_run``. Otherwise a
    malformed member (or duplicate) could be ignored here while a matching
    current pair still appeared live to an execution/action caller.
    """
    closed_waves = run.get("closed_waves")
    if not isinstance(closed_waves, list):
        return None
    pairs: set[tuple[str, str]] = set()
    for item in closed_waves:
        if not isinstance(item, dict) or set(item) != {"wave_id", "batch_base_sha"}:
            return None
        wave_id = item.get("wave_id")
        batch_base_sha = item.get("batch_base_sha")
        if (
            not _nonempty_string(wave_id)
            or not isinstance(batch_base_sha, str)
            or SHA_RE.fullmatch(batch_base_sha) is None
        ):
            return None
        pair = (wave_id, batch_base_sha)
        if pair in pairs:
            return None
        pairs.add(pair)
    return pairs


def _wave_scope_matches_current(run: dict[str, Any], scope: Any) -> bool:
    """Return whether a wave-scoped grant is bound to the live wave identity.

    A wave grant is intentionally tied to both the wave ID and the immutable
    batch base. ``closed_waves`` is a durable tombstone list: checking only the
    wave status lets a stale grant become live again when a later RUN update
    re-proposes the same wave pair.
    """
    wave = run.get("active_wave")
    if run.get("schema_version") not in {10, 11}:
        # Legacy RUNs retain their historical status-only expiry semantics.
        # The pair binding and durable tombstones are v10 additions.
        return isinstance(wave, dict) and wave.get("status") not in {
            "closed",
            "superseded",
        }
    if not isinstance(wave, dict) or wave.get("status") not in {"proposed", "active"}:
        return False
    if not isinstance(scope, dict) or not _nonempty_string(scope.get("wave_id")):
        return False
    wave_id = wave.get("wave_id")
    batch_base_sha = wave.get("batch_base_sha")
    if (
        not _nonempty_string(wave_id)
        or not isinstance(batch_base_sha, str)
        or SHA_RE.fullmatch(batch_base_sha) is None
        or scope.get("wave_id") != wave_id
        or not isinstance(scope.get("batch_base_sha"), str)
        or SHA_RE.fullmatch(scope["batch_base_sha"]) is None
        or scope.get("batch_base_sha") != batch_base_sha
    ):
        return False

    # A v10 RUN must carry this list. Fail closed when an older/malformed
    # object asks for wave-scoped coverage instead of silently treating a
    # missing history as an empty list.
    closed_pairs = _closed_wave_pairs(run)
    if closed_pairs is None:
        return False
    return (wave_id, batch_base_sha) not in closed_pairs


def wave_scope_matches_current(run: dict[str, Any], scope: Any) -> bool:
    """Public validation helper for a wave-closed authorization scope."""

    return _wave_scope_matches_current(run, scope)


def _authorization_not_expired(
    run: dict[str, Any], boundary: Any, scope: dict[str, Any] | None = None
) -> bool:
    if boundary == "explicit_revocation":
        return True
    if boundary == "run_complete":
        return run.get("status") != "complete"
    if boundary == "wave_closed":
        return _wave_scope_matches_current(run, scope)
    return False

#!/usr/bin/env python3
"""Apply guarded PLAN-v6/RUN-v11 state transitions.

This replaces ad-hoc JSON editing for durable control, owner review grants,
and interrupted-worker reconciliation. It validates the complete manifest pair
before atomically replacing RUN.md.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from harness_core import (
    _normalized_branch,
    _nonempty_string,
    extract_json_manifest_text,
    is_full_sha,
    mission_conflicts,
    parent_owned_path,
    plan_digest,
    path_in_scopes,
    validate_changed_path,
)
from harness_git import GitMetadataError, reject_object_substitution, run_git
from harness_graph import (
    merge_chain_skip_allowed,
    review_covers_ui_acceptance,
    reviewed_merge_chain_covers,
    ui_acceptance_evidence_present,
    ui_acceptance_review,
    repair_scope_entry,
)
from harness_manifest import (
    _verifier_owners,
    INTERRUPTED_REVIEW_RECEIPT,
    ManifestError,
    UI_AUTHORING_REQUIRED_SKILLS,
    authorization_covers,
    execution_covers,
    load_plan,
    load_run,
    mission_has_ui_authoring_action,
    validate_current_plan_run,
)
from harness_schema import EXACT_TARGET_LIFECYCLE_ACTIONS, RUN_DISPATCH_STATUSES, RUN_HEADING
from harness_schema import review_lenses, security_result_decision
from harness_schema import frozen_coordination_path, supported_coordination_path
from verifier_runtime import host_executable_identity, observe_plan_host_runtimes
from harness_worker_result_transition import (
    record_worker_result,
    reject_worker_result,
    verify_worker_observation,
)
from select_ready_nodes import (
    GraphSelectionError,
    select_ready_nodes,
)
from select_ready_nodes import _runtime_binding
from check_launch_packet import InvalidMessageBudgetError, check_message
from security_review_result import (
    SecurityReviewResultError,
    load_security_review_result,
    security_result_finding_summaries,
    validate_security_review_result,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    try:
        reject_object_substitution(root)
        result = run_git(root, "merge-base", "--is-ancestor", ancestor, descendant)
    except GitMetadataError as exc:
        raise ManifestError(str(exc)) from exc
    return result.returncode == 0


def _literal_pathspec_diff_paths(
    root: Path, base_sha: str, head_sha: str, repair_paths: list[str]
) -> set[str]:
    """Changed paths Git itself reports under the repair paths as pathspecs.

    Recorded scopes are replayed as pathspecs by the scoped review packet, so
    the reconcile subset check re-reads the candidate diff through the same
    ``--literal-pathspecs`` invocation: pathspec magic recorded by an older
    run can never hide a changed path from the scoped review.
    """

    try:
        reject_object_substitution(root)
        result = run_git(
            root,
            "--literal-pathspecs",
            "diff",
            "--name-only",
            "-z",
            "--no-renames",
            f"{base_sha}..{head_sha}",
            "--",
            *repair_paths,
            text=False,
        )
    except GitMetadataError as exc:
        raise ManifestError(str(exc)) from exc
    if result.returncode != 0:
        raise ManifestError("cannot observe the scoped repair diff from Git")
    try:
        output = result.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ManifestError("scoped repair paths are not valid UTF-8") from exc
    paths = output.split("\0")
    if paths[-1:] == [""]:
        paths.pop()
    return set(paths)


def _candidate_changed_paths(root: Path, base_sha: str, head_sha: str) -> list[str]:
    try:
        reject_object_substitution(root)
        result = run_git(
            root,
            "diff",
            "--name-only",
            "-z",
            "--no-renames",
            f"{base_sha}..{head_sha}",
            text=False,
        )
    except GitMetadataError as exc:
        raise ManifestError(str(exc)) from exc
    if result.returncode != 0:
        raise ManifestError("cannot observe candidate changed paths from Git")
    try:
        output = result.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ManifestError("candidate changed paths are not valid UTF-8") from exc
    paths = output.split("\0")
    if paths[-1:] == [""]:
        paths.pop()
    for path in paths:
        reason = validate_changed_path(path)
        if reason:
            raise ManifestError(f"candidate changed path {path!r} {reason}")
    return sorted(set(paths))


def _coordination_commit_changes(
    root: Path, base_sha: str, head_sha: str
) -> list[tuple[str, str]]:
    """Return literal path/status pairs for one coordination bookkeeping commit."""

    try:
        reject_object_substitution(root)
        result = run_git(
            root,
            "diff",
            "--name-status",
            "-z",
            "--no-renames",
            f"{base_sha}..{head_sha}",
            text=False,
        )
    except GitMetadataError as exc:
        raise ManifestError(str(exc)) from exc
    if result.returncode != 0:
        raise ManifestError("cannot observe coordination commit paths from Git")
    try:
        output = result.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ManifestError("coordination commit paths are not valid UTF-8") from exc
    fields = output.split("\0")
    if fields[-1:] == [""]:
        fields.pop()
    if not fields or len(fields) % 2:
        raise ManifestError("coordination commit path observation is malformed")
    changes: list[tuple[str, str]] = []
    for index in range(0, len(fields), 2):
        status, path = fields[index], fields[index + 1]
        reason = validate_changed_path(path)
        if reason:
            raise ManifestError(f"coordination commit path {path!r} {reason}")
        changes.append((status, path))
    return changes


def _git_entry_mode(root: Path, commit_sha: str, path: str) -> str | None:
    output = _git_out(root, "ls-tree", commit_sha, "--", path).strip()
    if not output:
        return None
    entry = output.split("\0", 1)[0].split(" ", 1)[0]
    return entry if entry else None


def _require_regular_coordination_entries(
    root: Path, old_head: str, new_head: str, paths: set[str]
) -> None:
    for path in sorted(paths):
        old_mode = _git_entry_mode(root, old_head, path)
        new_mode = _git_entry_mode(root, new_head, path)
        if old_mode is not None and new_mode is not None and old_mode != new_mode:
            raise ManifestError(
                f"coordination entry {path!r} changed Git mode or type"
            )
        if new_mode != "100644":
            raise ManifestError(
                f"coordination entry {path!r} must be a regular file in the checkpoint"
            )


def _require_generated_task_views(
    root: Path, run: dict[str, Any], paths: set[str]
) -> None:
    from render_tasks_view import GENERATED_MARKER

    expected_identity = f"Human view of run `{run.get('run_id')}` "
    for path in sorted(paths):
        if not path.endswith("/tasks.md") and path != "docs/tasks.md":
            continue
        try:
            content = (root / Path(path)).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ManifestError(f"generated tasks view {path!r} is unreadable") from exc
        if GENERATED_MARKER not in content or expected_identity not in content:
            raise ManifestError(
                f"tasks view {path!r} lacks this RUN's generated identity"
            )


def _require_observed_plan_identity(
    plan: dict[str, Any], run: dict[str, Any], operation: str
) -> None:
    expected_revision = plan.get("revision")
    expected_digest = plan_digest(plan)
    run_plan = run.get("plan")
    if not isinstance(run_plan, dict) or (
        run_plan.get("id") != plan.get("plan_id")
        or run_plan.get("revision") != expected_revision
        or run_plan.get("digest_sha256") != expected_digest
    ):
        raise ManifestError(f"{operation} requires RUN and live PLAN identities to match")

    observed = run.get("observed")
    if not isinstance(observed, dict) or not _nonempty_string(observed.get("captured_at")):
        raise ManifestError(f"{operation} requires a fresh parent observation")


def _candidate_allowed_scopes(plan: dict[str, Any], run: dict[str, Any]) -> list[str]:
    scopes: list[str] = []
    for mission in plan.get("missions", []):
        if isinstance(mission, dict) and isinstance(mission.get("write_scope"), list):
            scopes.extend(item for item in mission["write_scope"] if isinstance(item, str))
    return sorted(set(scopes))


def _reject_unplanned_candidate_paths(
    plan: dict[str, Any], run: dict[str, Any], root: Path, base_sha: str, head_sha: str,
    *, allowed_scopes: list[str] | None = None,
) -> None:
    changed = _candidate_changed_paths(root, base_sha, head_sha)
    allowed = _candidate_allowed_scopes(plan, run) if allowed_scopes is None else allowed_scopes
    integration = run.get("integration") if isinstance(run, dict) else None
    coordination_paths = (
        integration.get("coordination_paths", [])
        if isinstance(integration, dict)
        else []
    )
    if not isinstance(coordination_paths, list):
        coordination_paths = []
    # PLAN/RUN are parent-owned coordination state, never product changes.
    # A coordination scope is likewise a protected exception for guard
    # snapshots, not an authorization to commit those files in an integration
    # candidate.  Reject both before applying mission write scopes so a broad
    # scope such as ``docs/goal/**`` cannot smuggle committed RUN/PLAN state.
    unplanned = [
        path
        for path in changed
        if parent_owned_path(path)
        or path_in_scopes(path, coordination_paths)
        or not path_in_scopes(path, allowed)
    ]
    if unplanned:
        raise ManifestError(
            "candidate changed paths are outside declared mission/integration scopes: "
            + ", ".join(unplanned)
        )


DEFAULT_LOCK_STALE_MINUTES = 15

# Dispatching the write path is single-writer work: these commands require
# the calling session to already hold the run lock.
DISPATCH_COMMANDS = {
    "accept-wave",
    "lease-worker",
    "record-worker-result",
    "reject-worker-result",
    "reserve-review-dispatch",
    "record-integration",
    "reconcile-candidate-head",
    "reconcile-coordination-head",
    "close-wave",
    "reserve-node-attempt",
    "record-node-result",
}
@contextmanager
def _run_transition_lock(path: Path) -> Iterator[None]:
    """Serialize the complete read/validate/write transaction for one RUN.

    The durable ``run_lock`` controls which parent session may dispatch. This
    short operating-system lock prevents two processes from that same session
    from loading one snapshot and then replacing each other's updates.
    """

    lock_root = Path(tempfile.gettempdir()) / "product-delivery-harness-transition-locks"
    lock_root.mkdir(parents=True, exist_ok=True)
    identity = os.path.normcase(str(path.resolve())).encode("utf-8")
    lock_path = lock_root / f"{hashlib.sha256(identity).hexdigest()}.lock"
    handle = lock_path.open("a+b")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    except OSError as exc:
        handle.close()
        raise ManifestError(f"cannot lock RUN transition for {path}: {exc}") from exc

    try:
        yield
    finally:
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # A naive stamp cannot be compared against now(timezone.utc); treat it as
    # unparseable so the gate fails closed (stale) rather than crashing.
    if parsed.tzinfo is None:
        return None
    return parsed


def _lock_age_minutes(run: dict[str, Any]) -> float | None:
    lock = run.get("run_lock")
    if not isinstance(lock, dict):
        return None
    heartbeat = _parse_ts(lock.get("heartbeat_at"))
    if heartbeat is None:
        return None
    return (datetime.now(timezone.utc) - heartbeat).total_seconds() / 60


def _ensure_run_lock_free(
    run: dict[str, Any], session_id: str | None, stale_after: float = DEFAULT_LOCK_STALE_MINUTES
) -> None:
    """Refuse to mutate a RUN another live parent session holds.

    A missing lock is the historical behavior and stays valid; a fresh lock
    with a different session blocks the transition so two parents can never
    dispatch against the same state.
    """

    lock = run.get("run_lock")
    if not isinstance(lock, dict):
        return
    holder = lock.get("session_id")
    if not isinstance(holder, str) or not holder:
        return
    if session_id is not None and holder == session_id:
        return
    age = _lock_age_minutes(run)
    if age is not None and age <= stale_after:
        raise ManifestError(
            f"run lock is held by session {holder!r} "
            f"(heartbeat {age:.1f}m ago, stale after {stale_after:.0f}m); "
            "pass --session-id <id> before the subcommand or release the lock"
        )


def _ensure_no_foreign_lock(run: dict[str, Any], session_id: str | None) -> None:
    """Mutating transitions refuse any foreign lock, fresh or stale.

    Stale takeover is an explicit operator action (``watchdog --reclaim`` or
    ``acquire-run-lock``), never a side effect of an ordinary transition, so
    an unparseable or aged-out heartbeat still blocks instead of failing open.
    """

    lock = run.get("run_lock")
    if not isinstance(lock, dict):
        return
    holder = lock.get("session_id")
    if not isinstance(holder, str) or not holder:
        return
    if session_id is not None and holder == session_id:
        return
    raise ManifestError(
        f"run lock is held by session {holder!r}; mutations require that session "
        "or an explicit watchdog --reclaim / acquire-run-lock takeover"
    )


def _require_held_run_lock(run: dict[str, Any], args: argparse.Namespace) -> None:
    if not getattr(args, "session_id", None):
        raise ManifestError(
            f"{args.command} requires --session-id <id>, placed before the subcommand"
        )
    lock = run.get("run_lock")
    if not isinstance(lock, dict) or lock.get("session_id") != args.session_id:
        raise ManifestError(
            f"{args.command} requires this session's run lock; take it with "
            "--session-id <id> acquire-run-lock first"
        )


def _acquire_run_lock(run: dict[str, Any], args: argparse.Namespace) -> None:
    _require_session_id(args)
    _ensure_run_lock_free(run, args.session_id)
    now = _now()
    lock = {
        "session_id": args.session_id,
        "acquired_at": now,
        "heartbeat_at": now,
    }
    if args.owner:
        lock["owner"] = args.owner
    run["run_lock"] = lock


def _release_run_lock(run: dict[str, Any], args: argparse.Namespace) -> None:
    _require_session_id(args)
    lock = run.get("run_lock")
    if not isinstance(lock, dict):
        raise ManifestError("run has no lock to release")
    if lock.get("session_id") != args.session_id:
        raise ManifestError(
            f"run lock is held by session {lock.get('session_id')!r}, not {args.session_id!r}"
        )
    del run["run_lock"]


def _require_session_id(args: argparse.Namespace) -> None:
    if not getattr(args, "session_id", None):
        raise ManifestError(
            "lock commands require --session-id <id>, placed before the subcommand"
        )


def _heartbeat_run_lock(run: dict[str, Any], args: argparse.Namespace) -> None:
    _require_session_id(args)
    lock = run.get("run_lock")
    if not isinstance(lock, dict):
        raise ManifestError("run has no lock to heartbeat")
    if lock.get("session_id") != args.session_id:
        raise ManifestError(
            f"run lock is held by session {lock.get('session_id')!r}, not {args.session_id!r}"
        )
    lock["heartbeat_at"] = _now()


def _watchdog_report(run: dict[str, Any], stale_after: float) -> list[str]:
    lines: list[str] = []
    age = _lock_age_minutes(run)
    lock = run.get("run_lock")
    if isinstance(lock, dict):
        if age is None:
            lines.append(
                f"lock: session {lock.get('session_id')!r} has an unparseable heartbeat; treat as stale and reclaim"
            )
        elif age > stale_after:
            lines.append(
                f"lock: session {lock.get('session_id')!r} heartbeat is {age:.1f}m old (stale after {stale_after:.0f}m); safe to reclaim"
            )
        else:
            lines.append(f"lock: session {lock.get('session_id')!r} is live ({age:.1f}m)")
    else:
        lines.append("lock: none")
    stale_parent = not isinstance(lock, dict) or age is None or age > stale_after
    running = [
        node_id
        for node_id, state in run.get("graph_state", {}).get("node_states", {}).items()
        if isinstance(state, dict) and state.get("phase") == "running"
    ]
    if running and stale_parent:
        lines.append(
            "interrupted-work candidates (no live parent heartbeat): "
            + ", ".join(sorted(running))
        )
        lines.append(
            "reconcile them with reconcile-interrupted / reconcile-interrupted-reviews or "
            "record-node-result --outcome blocked after reclaiming the lock"
        )
    elif running:
        lines.append("running nodes (parent live): " + ", ".join(sorted(running)))
    return lines




def _git_out(repo_root: Path, *args: str) -> str:
    try:
        reject_object_substitution(repo_root)
        result = run_git(repo_root, *args, text=True, timeout=30)
    except GitMetadataError as exc:
        raise ManifestError(str(exc)) from exc
    if result.returncode != 0:
        raise ManifestError(f"git {' '.join(args)} failed in {repo_root}")
    return result.stdout


def _git_branch_name(repo_root: Path) -> str:
    branch = _git_out(repo_root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if not branch or branch == "HEAD":
        raise ManifestError(f"{repo_root} is in detached HEAD state")
    return branch


def _coordination_ignored_paths(
    repo_root: Path, run_path: str | Path | None, run: dict[str, Any] | None = None,
) -> list[str]:
    """Exclude RUN and its declared generated view, never arbitrary docs."""

    paths: list[str] = []
    if run_path is None and run is None:
        return paths
    if run_path is not None:
        try:
            paths.append(Path(run_path).resolve().relative_to(repo_root.resolve()).as_posix())
        except (OSError, ValueError):
            pass
    try:
        if run is None:
            run = load_run(Path(run_path))
        integration = run.get("integration", {})
        if "docs/tasks.md" not in integration.get("coordination_paths", []):
            return paths
        view = repo_root / "docs" / "tasks.md"
        _assert_non_reparse_path(view)
        from render_tasks_view import GENERATED_MARKER

        content = view.read_text(encoding="utf-8")
        if (GENERATED_MARKER in content
                and f"Human view of run `{run.get('run_id')}` " in content):
            paths.append("docs/tasks.md")
    except (ManifestError, OSError, ValueError, TypeError, AttributeError):
        # Missing, foreign, or retargeted views remain ordinary dirty files.
        pass
    return paths


def _git_status_excluding_run(
    repo_root: Path, run_path: str | Path | None, run: dict[str, Any] | None = None,
) -> str:
    """Observe product dirt without counting the run's generated coordination view."""

    arguments = ["status", "--porcelain", "--untracked-files=all", "--", "."]
    arguments.extend(
        f":(exclude,top,literal){path}"
        for path in _coordination_ignored_paths(repo_root, run_path, run)
    )
    return _git_out(repo_root, *arguments)


def _git_status_excluding_run_or_none(
    repo_root: Path, run_path: str | Path | None, run: dict[str, Any] | None = None,
) -> str | None:
    try:
        return _git_status_excluding_run(repo_root, run_path, run)
    except (GitMetadataError, ManifestError, OSError, subprocess.SubprocessError):
        return None


def _same_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(os.path.realpath(left)) == os.path.normcase(
        os.path.realpath(right)
    )


def _remote_default_branch(repo_root: Path) -> str | None:
    try:
        reject_object_substitution(repo_root)
        result = run_git(repo_root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD", text=True, timeout=30)
    except GitMetadataError:
        return None
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    prefix = "refs/remotes/origin/"
    if not value.startswith(prefix) or value == prefix:
        return None
    return f"refs/heads/{value.removeprefix(prefix)}"


def _require_non_default_integration_branch(run: dict[str, Any]) -> str:
    integration = run.get("integration")
    raw_branch = integration.get("branch") if isinstance(integration, dict) else None
    branch = _normalized_branch(raw_branch)
    if branch is None:
        raise ManifestError("run.integration.branch must name a branch")
    observed = run.get("observed")
    observed_git = observed.get("git") if isinstance(observed, dict) else None
    default_branch = (
        _normalized_branch(observed_git.get("default_branch"))
        if isinstance(observed_git, dict)
        else None
    )
    if branch.casefold() in {"main", "development"} or (
        default_branch is not None and branch == default_branch
    ):
        raise ManifestError(
            f"integration branch {raw_branch!r} resolves to a protected or retired branch; "
            "use a separate run branch"
        )
    return branch




def _validate_security_integration_checkout(
    plan: dict[str, Any],
    run: dict[str, Any],
    node: dict[str, Any],
    repo_root: Path | None,
    *,
    operation: str,
    run_path: str | Path | None = None,
) -> None:
    """Bind a security integration review to the live parent checkout.

    Security review dispatches are the final review of the unified candidate,
    so their reservation and result recording both re-read branch, HEAD,
    cleanliness, and base ancestry from Git.  This keeps a reviewer from being
    reserved (or certified) against a detached, retargeted, dirty, or drifted
    checkout. RUN and its declared generated tasks view are the expected
    coordination artifacts; verifier dispatches also protect their exact bytes.
    """

    review = node.get("review")
    if not (
        isinstance(review, dict)
        and review.get("type") == "security"
        and review.get("stage", "preintegration") == "integration"
    ):
        return
    if repo_root is None:
        raise ManifestError(
            f"{operation} security integration review requires --repo-root"
        )
    observed = run.get("observed")
    observed_git = observed.get("git") if isinstance(observed, dict) else None
    observed_path = (
        observed_git.get("parent_worktree_path")
        if isinstance(observed_git, dict)
        else None
    )
    if not isinstance(observed_path, str) or not _same_path(repo_root, observed_path):
        raise ManifestError(
            f"--repo-root {repo_root} is not the observed parent worktree "
            f"{observed_path!r}; {operation} security integration review from the observed checkout"
        )
    expected_branch = _require_non_default_integration_branch(run)
    live_branch = _git_branch_name(repo_root)
    if _normalized_branch(live_branch) != expected_branch:
        raise ManifestError(
            f"--repo-root is on branch {live_branch!r}, not the integration branch "
            f"{run.get('integration', {}).get('branch')!r}"
        )
    integration = run.get("integration")
    integration_head = (
        integration.get("integration_head_sha")
        if isinstance(integration, dict)
        else None
    )
    if not is_full_sha(integration_head):
        raise ManifestError(
            f"{operation} security integration review requires a full integration head SHA"
        )
    live_head = _git_out(repo_root, "rev-parse", "HEAD").strip()
    if live_head != integration_head:
        raise ManifestError(
            f"integration branch HEAD is {live_head}, not {integration_head}; "
            f"{operation} security integration review requires the current integration head"
        )
    if _git_status_excluding_run(repo_root, run_path, run).strip():
        raise ManifestError(
            f"--repo-root product tree is dirty; {operation} security integration review "
            "allows only RUN and its declared generated tasks view"
        )
    batch_base = integration.get("batch_base_sha") if isinstance(integration, dict) else None
    if not is_full_sha(batch_base):
        raise ManifestError(
            f"{operation} security integration review requires a full batch_base_sha"
        )
    if not _git_is_ancestor(repo_root, batch_base, live_head):
        raise ManifestError(
            f"batch base {batch_base} is not an ancestor of integration head {live_head}; "
            f"{operation} security integration review cannot proceed"
        )
    _reject_unplanned_candidate_paths(plan, run, repo_root, batch_base, live_head)


def _record_observation(
    plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace
) -> None:
    """Write exactly what the parent observes: live Git facts plus a timestamp.

    This replaces hand-transcribing `harness_step.py`'s printed snapshot into
    RUN.observed — the observation `_write_launch_reasons` requires before any
    write dispatch clears.
    """

    if args.repo_root is None:
        raise ManifestError("record-observation requires --repo-root")
    capacity_values = (
        getattr(args, "available_worker_slots", None),
        getattr(args, "isolation_capacity", None),
        getattr(args, "capacity_evidence", None),
    )
    update_capacity = any(value is not None for value in capacity_values)
    if update_capacity:
        slots, isolation, evidence = capacity_values
        if (
            type(slots) is not int or slots < 0
            or type(isolation) is not int or isolation < 0
            or not isinstance(evidence, str) or not evidence.strip()
        ):
            raise ManifestError(
                "capacity observation requires non-negative --available-worker-slots, "
                "--isolation-capacity and non-empty --capacity-evidence together"
            )
    root = args.repo_root
    repo_top_level = Path(_git_out(root, "rev-parse", "--show-toplevel").strip())
    head = _git_out(root, "rev-parse", "HEAD").strip()
    branch = _git_branch_name(root)
    porcelain = _git_status_excluding_run_or_none(
        repo_top_level, getattr(args, "run", None), run
    )
    worktrees_raw = _git_out(root, "worktree", "list", "--porcelain")

    worktrees: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in worktrees_raw.splitlines():
        if line.startswith("worktree "):
            if current is not None:
                worktrees.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif current is not None and line.startswith("HEAD "):
            current["head_sha"] = line.split(" ", 1)[1]
        elif current is not None and line.startswith("branch "):
            current["branch_ref"] = line.split(" ", 1)[1]
    if current is not None:
        worktrees.append(current)
    # managed_by derives from the recorded workers' workspace modes, not a
    # blanket assumption.
    app_managed_paths = {
        worker.get("worktree_path")
        for worker in run.get("workers", [])
        if isinstance(worker, dict)
        and worker.get("workspace_mode") == "app_managed_worktree"
    }
    for entry in worktrees:
        path = entry.get("path")
        dirty: bool | None = False
        if isinstance(path, str):
            if _same_path(path, repo_top_level):
                entry["dirty"] = None if porcelain is None else bool(porcelain.strip())
                entry.setdefault("head_sha", None)
                entry.setdefault("branch_ref", None)
                entry["managed_by"] = "parent"
                continue
            try:
                reject_object_substitution(Path(path))
                status = run_git(Path(path), "status", "--porcelain")
                dirty = None if status.returncode != 0 else bool(status.stdout.strip())
            except GitMetadataError as exc:
                raise ManifestError(str(exc)) from exc
            except (OSError, subprocess.SubprocessError):
                # A pruned/dead worktree must not abort the mandatory
                # observation; record it as unavailable rather than crash.
                dirty = None
        entry.setdefault("head_sha", None)
        entry.setdefault("branch_ref", None)
        entry["managed_by"] = (
            "app" if path in app_managed_paths else "parent"
        )
        entry["dirty"] = dirty

    captured_at = _now()
    run["observed"]["captured_at"] = captured_at
    # The parent worktree is recorded exactly as `git worktree list` prints
    # it, so the selector's path-identity comparison against the sibling
    # entries matches on every platform (a resolved local Path string would
    # differ from Git's own spelling on Windows).
    parent_entry = next(
        (
            entry
            for entry in worktrees
            if isinstance(entry.get("path"), str)
            and _same_path(entry["path"], repo_top_level)
        ),
        None,
    )
    parent_path = (
        parent_entry["path"]
        if isinstance(parent_entry, dict)
        else str(repo_top_level.resolve())
    )
    run["observed"]["git"].update(
        {
            "parent_worktree_path": parent_path,
            "parent_branch": branch,
            "parent_head_sha": head,
            "parent_dirty": None if porcelain is None else bool(porcelain.strip()),
            "worktrees": worktrees,
        }
    )
    default_branch = _remote_default_branch(root)
    if default_branch is not None:
        run["observed"]["git"]["default_branch"] = default_branch
    if update_capacity:
        run["observed"]["runtime"].update({
            "available_worker_slots": slots,
            "isolation_capacity": isolation,
        })
        run["attempt_log"].append({
            "attempt_id": f"CAPACITY-{captured_at}-{len(run['attempt_log']) + 1}",
            "mission_id": None, "task_id": None, "lease_id": None,
            "kind": "runtime_capacity_observation", "result": "observed",
            "evidence": [
                f"{captured_at}: available_worker_slots={slots}; isolation_capacity={isolation}",
                evidence.strip(),
            ],
        })


def _accept_wave(plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace) -> None:
    wave = run.get("active_wave")
    if not isinstance(wave, dict):
        raise ManifestError("run has no active_wave object")
    if wave.get("status") == "active":
        # Refuse regardless of wave_id: re-accepting the same id would rewrite
        # selected_missions and batch_base_sha under live workers.
        raise ManifestError(
            f"wave {wave.get('wave_id')!r} is still active; close it before accepting another"
        )
    if run.get("execution_authorized") is not True:
        raise ManifestError("accept-wave requires overall execution authorization")
    if run.get("status") not in RUN_DISPATCH_STATUSES:
        raise ManifestError(
            f"run status is {run.get('status')!r}; a wave is accepted only on a ready or running run"
        )
    control = run.get("control")
    desired_state = control.get("desired_state") if isinstance(control, dict) else None
    if desired_state != "running":
        raise ManifestError(
            f"run control desired_state is {desired_state!r}; "
            "a wave is accepted only while the run is not paused or cancelled"
        )
    if run.get("plan_readiness") != "ready":
        raise ManifestError("accept-wave requires plan_readiness ready")
    observed = run.get("observed")
    captured_at = observed.get("captured_at") if isinstance(observed, dict) else None
    if not isinstance(captured_at, str) or not captured_at:
        raise ManifestError(
            "accept-wave requires a recorded observation; run record-observation first"
        )
    observed_git = observed.get("git") if isinstance(observed, dict) else None
    observed_head = (
        observed_git.get("parent_head_sha") if isinstance(observed_git, dict) else None
    )
    if not is_full_sha(observed_head):
        raise ManifestError(
            "accept-wave requires the observation's parent head SHA; "
            "run record-observation first"
        )
    repo_root = getattr(args, "repo_root", None)
    if repo_root is None:
        raise ManifestError("accept-wave requires --repo-root")
    expected_branch = _require_non_default_integration_branch(run)
    observed_path = (
        observed_git.get("parent_worktree_path")
        if isinstance(observed_git, dict)
        else None
    )
    if not isinstance(observed_path, str) or not _same_path(repo_root, observed_path):
        raise ManifestError(
            f"--repo-root {repo_root} is not the observed parent worktree {observed_path!r}; "
            "record a fresh observation from the integration checkout"
        )
    observed_branch = _normalized_branch(observed_git.get("parent_branch"))
    if observed_branch != expected_branch:
        raise ManifestError(
            f"observed parent branch {observed_git.get('parent_branch')!r} is not "
            f"integration branch {run.get('integration', {}).get('branch')!r}"
        )
    if observed_git.get("parent_dirty") is not False:
        raise ManifestError("accept-wave requires an observed clean parent checkout")
    live_branch = _git_branch_name(repo_root)
    if _normalized_branch(live_branch) != expected_branch:
        raise ManifestError(
            f"--repo-root is on branch {live_branch!r}, not integration branch "
            f"{run.get('integration', {}).get('branch')!r}"
        )
    live_head = _git_out(repo_root, "rev-parse", "HEAD").strip()
    if live_head != observed_head:
        raise ManifestError(
            f"live integration head {live_head} differs from observed parent head "
            f"{observed_head}; record a fresh observation"
        )
    if _git_status_excluding_run(repo_root, getattr(args, "run", None), run).strip():
        raise ManifestError(
            "accept-wave requires a clean live integration checkout apart from "
            "RUN and its declared generated tasks view"
        )
    integration_head = run.get("integration", {}).get("integration_head_sha")
    if is_full_sha(integration_head) and integration_head != live_head:
        raise ManifestError(
            f"live integration head {live_head} differs from the recorded integration "
            f"head {integration_head}"
        )
    if args.batch_base_sha != observed_head:
        raise ManifestError(
            f"batch base {args.batch_base_sha} does not match the observed parent "
            f"head {observed_head}; re-observe before accepting a wave"
        )
    if len(args.mission_id) != len(set(args.mission_id)):
        raise ManifestError("accept-wave mission ids must be unique")
    plan_missions = {
        item.get("id")
        for item in plan.get("missions", [])
        if isinstance(item, dict)
    }
    unknown = [mid for mid in args.mission_id if mid not in plan_missions]
    if unknown:
        raise ManifestError(f"accept-wave names unknown missions: {', '.join(unknown)}")
    integrated = {
        mid
        for mid, state in run.get("mission_states", {}).items()
        if isinstance(state, dict) and state.get("phase") == "integrated"
    }
    already = [mid for mid in args.mission_id if mid in integrated]
    if already:
        raise ManifestError(f"accept-wave selects already-integrated missions: {', '.join(already)}")

    # Bind acceptance to the selector's current safe frontier. The candidate
    # batch base is applied in memory first because selection intentionally
    # refuses writer nodes until that base exists and matches observation.
    run["integration"]["batch_base_sha"] = args.batch_base_sha
    try:
        selection = select_ready_nodes(
            plan,
            run,
            repo_root=repo_root,
        )
    except GraphSelectionError as exc:
        raise ManifestError(f"accept-wave could not select a safe frontier: {exc}") from exc
    mission_nodes = {
        node.get("id"): node.get("ref")
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict) and node.get("kind") == "mission"
    }
    selected_missions = [
        directive["ref"]
        for directive in selection["dispatchable_nodes"]
        if directive.get("kind") == "mission"
    ]
    requested = set(args.mission_id)
    selected = set(selected_missions)
    if requested != selected:
        deferred_by_mission = {
            mission_nodes.get(item.get("node_id")): item.get("reason_codes", [])
            for item in selection["deferred_nodes"]
            if mission_nodes.get(item.get("node_id")) is not None
        }
        details = "; ".join(
            f"{mission_id}: {', '.join(deferred_by_mission.get(mission_id, ['not selected']))}"
            for mission_id in sorted(requested - selected)
        )
        missing = sorted(selected - requested)
        suffix = f"; selector also proposed {', '.join(missing)}" if missing else ""
        raise ManifestError(
            "accept-wave mission set does not equal the selector's dispatchable "
            f"mission frontier ({details or 'requested set omitted selected missions'}{suffix})"
        )

    conflict_map: dict[str, set[str]] = {mission_id: set() for mission_id in plan_missions}
    conflict_edges: list[dict[str, Any]] = []
    seen_conflicts: set[tuple[str, str]] = set()
    for edge in selection["conflict_edges"]:
        left_mission = mission_nodes.get(edge.get("left"))
        right_mission = mission_nodes.get(edge.get("right"))
        if left_mission is None or right_mission is None:
            continue
        left, right = sorted((left_mission, right_mission))
        conflict_map[left].add(right)
        conflict_map[right].add(left)
        pair = (left, right)
        if pair in seen_conflicts:
            continue
        seen_conflicts.add(pair)
        conflict_edges.append(
            {"left": left, "right": right, "reason_codes": edge["reason_codes"]}
        )
    deferred_missions = []
    for item in selection["deferred_nodes"]:
        mission_id = mission_nodes.get(item.get("node_id"))
        if mission_id is None:
            continue
        deferred_missions.append(
            {
                "mission_id": mission_id,
                "reason_codes": item["reason_codes"],
                "conflicts_with": sorted(conflict_map[mission_id]),
            }
        )
    wave.update(
        {
            "wave_id": args.wave_id,
            "status": "active",
            "plan_revision": plan.get("revision"),
            "plan_digest_sha256": (run.get("plan") or {}).get("digest_sha256"),
            "batch_base_sha": args.batch_base_sha,
            "selected_missions": selected_missions,
            "deferred_missions": sorted(
                deferred_missions, key=lambda item: item["mission_id"]
            ),
            "conflict_edges": sorted(
                conflict_edges, key=lambda item: (item["left"], item["right"])
            ),
        }
    )


def _close_wave(run: dict[str, Any], args: argparse.Namespace) -> None:
    """Retire the current wave at its `wave_closed` authorization boundary.

    Appends the durable tombstone, flips the wave to `closed`, and resets every
    wave-bounded grant to the unauthorized shape, exactly as
    `references/execution-state-model.md` describes. `run_complete` grants are
    retained as closeout evidence.
    """

    wave = run.get("active_wave")
    if not isinstance(wave, dict):
        raise ManifestError("run has no active_wave object")
    if wave.get("status") not in {"active", "proposed"}:
        raise ManifestError(
            f"wave {wave.get('wave_id')!r} is {wave.get('status')!r}; "
            "only an active or proposed wave can close"
        )
    wave_id = wave.get("wave_id")
    batch_base_sha = wave.get("batch_base_sha")
    if not isinstance(wave_id, str) or not wave_id:
        raise ManifestError("close-wave requires the wave's wave_id")
    if not is_full_sha(batch_base_sha):
        raise ManifestError("close-wave requires the wave's full batch_base_sha")
    closed_waves = run.setdefault("closed_waves", [])
    if any(
        isinstance(item, dict)
        and item.get("wave_id") == wave_id
        and item.get("batch_base_sha") == batch_base_sha
        for item in closed_waves
    ):
        raise ManifestError(
            f"wave pair ({wave_id}, {batch_base_sha}) is already recorded in closed_waves"
        )
    live_workers = sorted(
        worker.get("worker_id")
        for worker in [*run.get("workers", []), *run.get("review_workers", [])]
        if isinstance(worker, dict) and worker.get("phase") in {"leased", "worker_running"}
    )
    if live_workers:
        raise ManifestError(
            "cannot close a wave with live workers; reconcile them first: "
            + ", ".join(live_workers)
        )
    graph_states = run.get("graph_state", {}).get("node_states", {})
    live_parent_nodes = sorted(
        node_id
        for node_id, state in graph_states.items()
        if isinstance(state, dict)
        and state.get("phase") == "running"
        and not state.get("bound_worker_id")
    )
    if live_parent_nodes:
        raise ManifestError(
            "cannot close a wave with live parent-owned node attempts; record their "
            "results first: "
            + ", ".join(live_parent_nodes)
        )
    # A `worker_passed` mission still owes integration, and the validator
    # requires retained execution coverage for it. A `run_complete` boundary
    # survives the close and keeps covering it; a `wave_closed` boundary dies
    # at close, so those missions must integrate, fail, or reconcile first.
    scope = run.get("execution_authorization_scope")
    wave_bounded_execution = (
        run.get("execution_authorized")
        and isinstance(scope, dict)
        and scope.get("expires_when") == "wave_closed"
    )

    def mission_phase(mission_id: str) -> Any:
        state = run.get("mission_states", {}).get(mission_id)
        return state.get("phase") if isinstance(state, dict) else None

    unresolved = [
        mission_id
        for mission_id in wave.get("selected_missions", [])
        if mission_phase(mission_id)
        not in {"integrated", "worker_failed", "blocked", "worker_passed"}
    ]
    if unresolved:
        raise ManifestError(
            "cannot close a wave whose selected missions are still queued or "
            "running (validate their worker results first): " + ", ".join(unresolved)
        )
    if wave_bounded_execution:
        pending_integration = [
            mission_id
            for mission_id in wave.get("selected_missions", [])
            if mission_phase(mission_id) == "worker_passed"
        ]
        if pending_integration:
            raise ManifestError(
                "cannot clear a wave_closed execution boundary while missions "
                "still await integration: " + ", ".join(pending_integration)
            )
    closed_waves.append({"wave_id": wave_id, "batch_base_sha": batch_base_sha})
    wave["status"] = "closed"
    for action, entry in list(run.get("authorizations", {}).items()):
        if (
            isinstance(entry, dict)
            and entry.get("authorized")
            and entry.get("expires_when") == "wave_closed"
        ):
            run["authorizations"][action] = {"authorized": False, "source": None}
    if wave_bounded_execution:
        run["execution_authorized"] = False
        run["execution_authorization_source"] = None
        run["execution_authorization_scope"] = None
    run["attempt_log"].append(
        {
            "attempt_id": f"WAVE-CLOSE-{wave_id}-{len(run['attempt_log']) + 1}",
            "mission_id": None,
            "task_id": None,
            "lease_id": None,
            "kind": "wave_close",
            "result": "closed",
            "evidence": [f"closed wave {wave_id} at base {batch_base_sha}", args.source],
        }
    )


def _graph_node(plan: dict[str, Any], node_id: str) -> dict[str, Any]:
    """Resolve one graph node by exact ID for parent-owned transitions."""

    matches = [
        node
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict) and node.get("id") == node_id
    ]
    if len(matches) != 1:
        raise ManifestError(
            f"node {node_id!r} must identify exactly one PLAN graph node; found {len(matches)}"
        )
    return matches[0]


def _attempt_id_available(run: dict[str, Any], attempt_id: str) -> None:
    if not isinstance(attempt_id, str) or not attempt_id.strip():
        raise ManifestError("node attempt requires a non-empty --attempt-id")
    if any(
        isinstance(item, dict) and item.get("attempt_id") == attempt_id
        for item in [
            *run.get("attempt_log", []),
            *run.get("workers", []),
            *run.get("review_workers", []),
        ]
    ):
        raise ManifestError(f"duplicate attempt ID {attempt_id!r}")


def _node_attempt_log(
    run: dict[str, Any], node_id: str, attempt_id: str
) -> dict[str, Any] | None:
    matches = [
        item
        for item in run.get("attempt_log", [])
        if isinstance(item, dict)
        and item.get("kind") == "node_attempt"
        and item.get("node_id") == node_id
        and item.get("attempt_id") == attempt_id
    ]
    if len(matches) > 1:
        raise ManifestError(
            f"node attempt {attempt_id!r} for {node_id!r} is ambiguous"
        )
    return matches[0] if matches else None


def _declared_host_identity(
    declaration: dict[str, Any], repo_root: Path
) -> dict[str, str]:
    """Resolve the declared host argv against its exact checkout cwd."""

    try:
        cwd = repo_root.resolve() / declaration["cwd"]
        resolved = cwd.resolve()
        resolved.relative_to(repo_root.resolve())
        argv = declaration["argv"]
        if not isinstance(argv, list) or not argv:
            raise ManifestError("host verifier requires a non-empty argv")
        return host_executable_identity(
            str(argv[0]),
            resolved,
            os.environ,
        )
    except (OSError, ValueError) as exc:
        raise ManifestError(f"cannot resolve host verifier executable: {exc}") from exc


def _local_verifier_request(
    plan: dict[str, Any],
    run: dict[str, Any],
    node: dict[str, Any],
    *,
    attempt_id: str,
    repo_root: Path | None,
    run_path: Path | None = None,
) -> dict[str, Any]:
    """Build the exact parent-local verifier request for a reserved gate."""

    if repo_root is None:
        raise ManifestError(
            "reserve-node-attempt local verifier requires --repo-root"
        )
    repo_root = repo_root.resolve()
    observed_git = run.get("observed", {}).get("git", {})
    if not isinstance(observed_git, dict):
        raise ManifestError("local verifier request requires observed Git facts")
    observed_path = observed_git.get("parent_worktree_path")
    if not isinstance(observed_path, str) or not _same_path(repo_root, observed_path):
        raise ManifestError(
            "local verifier request root is not the observed integration checkout"
        )
    integration = run.get("integration")
    if not isinstance(integration, dict):
        raise ManifestError("local verifier request requires integration state")
    expected_branch = (
        integration.get("branch")
    )
    live_branch = _git_branch_name(repo_root)
    if _normalized_branch(live_branch) != _normalized_branch(expected_branch):
        raise ManifestError(
            "local verifier request checkout is not on the integration branch"
        )
    live_head = _git_out(repo_root, "rev-parse", "HEAD").strip()
    if live_head != integration.get("integration_head_sha"):
        raise ManifestError(
            "local verifier request checkout head differs from integration_head_sha"
        )
    dirty = _git_status_excluding_run(repo_root, run_path, run)
    if dirty.strip():
        raise ManifestError(
            "local verifier request requires a clean integration checkout"
        )
    owner = _verifier_owners(plan).get(node.get("ref"))
    if owner is None:
        raise ManifestError(
            f"local verifier node references unknown verifier {node.get('ref')!r}"
        )
    layer, mission_id, task_id, declaration = owner
    if layer not in {"batch", "final"}:
        raise ManifestError(
            f"local verifier node {node.get('id')!r} must reference a batch or final verifier"
        )
    head_sha = integration.get("integration_head_sha")
    batch_base_sha = integration.get("batch_base_sha")
    if not is_full_sha(head_sha) or not is_full_sha(batch_base_sha):
        raise ManifestError(
            "local verifier request requires full integration and batch-base SHAs"
        )
    if observed_git.get("parent_dirty") is not False:
        raise ManifestError(
            "local verifier request requires an observed clean integration checkout"
        )
    checkout_dirty = False
    ignored_paths = _coordination_ignored_paths(repo_root, run_path, run)
    context = {
        "run_id": run.get("run_id"),
        "plan_revision": plan.get("revision"),
        "plan_digest_sha256": plan_digest(plan),
        "graph_revision": run.get("graph_state", {}).get("graph_revision"),
        "batch_base_sha": batch_base_sha,
        "head_sha": head_sha,
        "changed_files": sorted(
            line.strip()
            for line in _git_out(
                repo_root, "diff", "--name-only", f"{batch_base_sha}..{head_sha}"
            ).splitlines()
            if line.strip()
        ),
        "trust_domain": "parent_local",
        "checkout_role": "integration",
        "checkout_dirty": checkout_dirty,
        "cache_safe": False,
        "layer": layer,
        "mission_id": mission_id,
        "task_id": task_id,
        # Gate executions remain unbound in the retained execution record; the
        # graph attempt ID is carried by attempt_log/node_dispatch instead.
        "attempt_id": None,
        "lease_id": None,
    }
    reservation = {
        "node_id": node.get("id"),
        "attempt_id": attempt_id,
        "nonce": _json_sha256(
            {
                "run_id": run.get("run_id"),
                "plan_digest_sha256": plan_digest(plan),
                "node_id": node.get("id"),
                "attempt_id": attempt_id,
                "head_sha": head_sha,
            }
        ),
    }
    host_entries, host_errors = observe_plan_host_runtimes({"final_gates": [declaration]}, repo_root)
    if host_errors:
        raise ManifestError("local verifier host preflight failed: " + "; ".join(host_errors))
    executable_identity = _declared_host_identity(declaration, repo_root)
    host_preflight = next((copy.deepcopy(entry) for entry in host_entries
        if entry.get("argv0") == declaration["argv"][0]
        and entry.get("executable") == executable_identity["executable"]
        and entry.get("executable_sha256") == executable_identity["executable_sha256"]), None)
    if host_preflight is None:
        raise ManifestError("local verifier request requires the exact PLAN-bound host preflight entry")
    return {
        "protocol": "harness-verifier-request-v1",
        "run_id": run.get("run_id"),
        "plan_id": plan.get("plan_id"),
        "plan_revision": plan.get("revision"),
        "plan_digest_sha256": plan_digest(plan),
        "graph_revision": context["graph_revision"],
        "node_id": node.get("id"),
        "attempt_id": attempt_id,
        "layer": layer,
        "branch": _normalized_branch(expected_branch),
        "checkout_root": str(repo_root.resolve()),
        "head_sha": head_sha,
        "batch_base_sha": batch_base_sha,
        "verifier": copy.deepcopy(declaration),
        "context": context,
        "reservation": reservation,
        "git_guard": {
            "expected_branch": _normalized_branch(expected_branch),
            "expected_head_sha": head_sha,
            "ignored_paths": ignored_paths,
        },
        "host_preflight": host_preflight,
    }


def _materialize_authorized_target(
    run: dict[str, Any], action: str, mission_id: str, target: str
) -> None:
    """Materialize an exact target from an active wildcard grant.

    Wildcards remain in the ledger as the user's durable scope.  The exact
    target is an execution receipt required by RUN-v11 validators; it may only
    be appended when the same action already has an unexpired wildcard grant.
    """

    if run.get("schema_version") != 11:
        return
    entry = run.get("authorizations", {}).get(action)
    if not isinstance(entry, dict) or entry.get("authorized") is not True:
        raise ManifestError(f"{action} is not authorized for {mission_id!r}")
    scope = entry.get("scope")
    targets = scope.get("targets") if isinstance(scope, dict) else None
    if not isinstance(targets, list):
        raise ManifestError(
            f"{action} exact target {target!r} cannot be materialized from a malformed scope"
        )
    # A caller may have already recorded this exact identity.  Preserve that
    # narrow grant even when the original wildcard has since been removed; the
    # materializer must not require a wildcard for an exact target that is
    # already active.
    if target in targets and authorization_covers(run, action, mission_id, target):
        return
    if "*" not in targets:
        raise ManifestError(
            f"{action} exact target {target!r} cannot be materialized without an active wildcard grant"
        )
    if not authorization_covers(run, action, mission_id, "*"):
        raise ManifestError(
            f"{action} wildcard grant for {mission_id!r} is not active"
        )
    if target not in targets:
        targets.append(target)


def _reserve_node_attempt(
    plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    """Reserve a non-runtime graph node before its external side effect.

    Approval, external-wait, lifecycle, and deterministic local verifier nodes
    have no worker lease to prove that their launch was planned.  This receipt
    is their durable attempt identity; the matching ``record-node-result``
    transition is the only operation that can terminate it.
    """

    node = _graph_node(plan, args.node_id)
    if node.get("kind") == "mission" or (
        node.get("kind") == "verifier" and node.get("executor") == "runtime_worker"
    ):
        raise ManifestError(
            "reserve-node-attempt is only for approval, external_wait, lifecycle, "
            "or non-runtime verifier nodes"
        )
    if node.get("kind") not in {"approval", "external_wait", "lifecycle", "verifier"}:
        raise ManifestError(f"node {args.node_id!r} is not reservable")
    if node.get("kind") == "verifier" and node.get("executor") not in {
        "local_command",
        "harness_parent",
    }:
        raise ManifestError(
            "reserve-node-attempt requires a local_command or harness_parent verifier"
        )
    _attempt_id_available(run, args.attempt_id)
    state = run.get("graph_state", {}).get("node_states", {}).get(args.node_id)
    if not isinstance(state, dict):
        raise ManifestError(f"no graph state for node {args.node_id!r}")
    if state.get("phase") not in {"dormant", "ready", "failed", "blocked"}:
        raise ManifestError(
            f"node {args.node_id!r} is {state.get('phase')!r}; reserve requires a dormant, "
            "ready, failed, or blocked node"
        )
    if int(state.get("attempts") or 0) >= int(node.get("max_attempts") or 0):
        raise ManifestError(f"node {args.node_id!r} has exhausted its attempt budget")

    # Selection is the logical readiness authority.  Reserve a node only when
    # the exact current frontier contains its dispatch directive.  This also
    # enforces dependency/route activation, plan/run status, and action grants.
    try:
        selection = select_ready_nodes(
            plan, run, repo_root=getattr(args, "repo_root", None)
        )
    except GraphSelectionError as exc:
        raise ManifestError(f"reserve-node-attempt could not select a safe frontier: {exc}") from exc
    directive = next(
        (
            item
            for item in selection.get("dispatchable_nodes", [])
            if isinstance(item, dict) and item.get("node_id") == args.node_id
        ),
        None,
    )
    if directive is None:
        deferred = next(
            (
                item
                for item in selection.get("deferred_nodes", [])
                if isinstance(item, dict) and item.get("node_id") == args.node_id
            ),
            None,
        )
        reasons = deferred.get("reason_codes", []) if isinstance(deferred, dict) else []
        detail = ", ".join(reasons) if reasons else "not in dispatchable frontier"
        raise ManifestError(
            f"node {args.node_id!r} is not dispatchable ({detail})"
        )

    evidence = getattr(args, "evidence", None) or []
    if not isinstance(evidence, list) or any(
        not isinstance(item, str) or not item.strip() for item in evidence
    ):
        raise ManifestError("node attempt evidence must be non-empty strings")
    node_dispatch = None
    verifier_dispatch = None
    verifier_request = None
    if node.get("kind") == "verifier" and node.get("executor") in {
        "local_command",
        "harness_parent",
    }:
        verifier_request = _local_verifier_request(
            plan,
            run,
            node,
            attempt_id=args.attempt_id,
            repo_root=getattr(args, "repo_root", None),
            run_path=getattr(args, "run", None),
        )
        verifier_dispatch = {
            "branch": verifier_request["branch"],
            "head_sha": verifier_request["head_sha"],
            "checkout_root": verifier_request["checkout_root"],
            "request_sha256": _json_sha256(verifier_request),
            "request": copy.deepcopy(verifier_request),
        }
    if node.get("kind") == "lifecycle":
        entry = run.get("authorizations", {}).get(node.get("ref"))
        if not isinstance(entry, dict) or entry.get("authorized") is not True:
            raise ManifestError(
                f"lifecycle action {node.get('ref')!r} is not currently authorized"
            )
        if node.get("ref") in EXACT_TARGET_LIFECYCLE_ACTIONS and not node.get("target"):
            raise ManifestError(
                f"{node.get('ref')} lifecycle node must declare an exact PLAN target"
            )
        if node.get("ref") == "push":
            raise ManifestError("RUN publication is a separate post-archive action")
        node_dispatch = {
            "target": node.get("target") or "*",
            "authorized_head_sha": entry.get("authorized_head_sha"),
        }
    state.update(
        {
            "phase": "running",
            "attempts": int(state.get("attempts") or 0) + 1,
            "last_attempt_id": args.attempt_id,
            "last_outcome": None,
            "bound_worker_id": None,
            "blockers": [],
        }
    )
    attempt = {
        "attempt_id": args.attempt_id,
        "node_id": args.node_id,
        "mission_id": None,
        "task_id": None,
        "lease_id": None,
        "kind": "node_attempt",
        "result": "reserved",
        "evidence": list(dict.fromkeys(evidence)),
    }
    if node_dispatch is not None:
        attempt["node_dispatch"] = node_dispatch
    if verifier_dispatch is not None:
        attempt["verifier_dispatch"] = verifier_dispatch
    run.setdefault("attempt_log", []).append(attempt)
    return {
        "command": "reserve-node-attempt",
        "node_id": args.node_id,
        "attempt_id": args.attempt_id,
        "kind": node.get("kind"),
        "executor": node.get("executor"),
        "phase": "running",
        "attempts": state["attempts"],
        "evidence": list(attempt["evidence"]),
        "directive": copy.deepcopy(directive),
        **({"verifier_request": copy.deepcopy(verifier_request)} if verifier_request is not None else {}),
    }


def _parse_node_result_args(
    args: argparse.Namespace,
) -> tuple[str, str, str | None, list[str], list[str]]:
    node_id = getattr(args, "node_id", None)
    attempt_id = getattr(args, "attempt_id", None)
    outcome = getattr(args, "outcome", None)
    evidence = getattr(args, "evidence", None) or []
    blockers = getattr(args, "blocker", None) or []
    if not isinstance(node_id, str) or not node_id.strip():
        raise ManifestError("record-node-result requires --node-id")
    if not isinstance(attempt_id, str) or not attempt_id.strip():
        raise ManifestError("record-node-result requires --attempt-id")
    for label, values in (("evidence", evidence), ("blocker", blockers)):
        if not isinstance(values, list) or any(
            not isinstance(item, str) or not item.strip() for item in values
        ):
            raise ManifestError(f"node result {label} values must be non-empty strings")
    return (
        node_id,
        attempt_id,
        outcome,
        list(dict.fromkeys(evidence)),
        list(dict.fromkeys(blockers)),
    )


def _record_node_result(
    plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    """Terminate a reserved non-runtime node and traverse matching routes."""

    node_id, attempt_id, outcome, evidence, blockers = _parse_node_result_args(args)
    node = _graph_node(plan, node_id)
    if node.get("kind") == "mission" or (
        node.get("kind") == "verifier" and node.get("executor") == "runtime_worker"
    ):
        raise ManifestError(
            "record-node-result is only for approval, external_wait, lifecycle, "
            "or non-runtime verifier nodes"
        )
    if outcome not in node.get("allowed_outcomes", []):
        raise ManifestError(
            f"outcome {outcome!r} is not declared by node {node_id!r}"
        )
    if not evidence:
        raise ManifestError("record-node-result requires at least one --evidence value")
    if outcome in {"blocked", "contract_gap"} and not blockers:
        raise ManifestError(
            f"record-node-result outcome {outcome!r} requires at least one --blocker"
        )
    state = run.get("graph_state", {}).get("node_states", {}).get(node_id)
    if not isinstance(state, dict):
        raise ManifestError(f"no graph state for node {node_id!r}")
    if (
        state.get("phase") != "running"
        or state.get("last_attempt_id") != attempt_id
    ):
        raise ManifestError(
            "record-node-result requires the matching reserved running attempt"
        )
    attempt = _node_attempt_log(run, node_id, attempt_id)
    if attempt is None:
        raise ManifestError(
            "record-node-result has no matching reserve-node-attempt receipt"
        )
    if attempt.get("result") != "reserved":
        raise ManifestError(f"node attempt {attempt_id!r} is already terminal")

    if node.get("kind") == "lifecycle":
        dispatch = attempt.get("node_dispatch")
        if not isinstance(dispatch, dict):
            raise ManifestError(
                "lifecycle result has no durable reservation target; reserve the node again"
            )
        expected_target = node.get("target") or "*"
        if dispatch.get("target") != expected_target:
            raise ManifestError(
                "lifecycle reservation target is stale; reserve a fresh node attempt"
            )
        action = node.get("ref")
        reserved_head = dispatch.get("authorized_head_sha")
        if action == "push":
            raise ManifestError("RUN publication is a separate post-archive action")
        # A successful or retryable lifecycle result still needs the exact
        # current grant and head. A blocked/contract-gap result is recovery for
        # an uncertain attempt and must remain recordable after revocation or
        # head drift so the node does not stay permanently running.
        if outcome not in {"blocked", "contract_gap"}:
            if action in EXACT_TARGET_LIFECYCLE_ACTIONS and expected_target == "*":
                raise ManifestError(
                    f"{action} lifecycle result requires an exact PLAN target; "
                    "record the attempt as blocked"
                )
            current_entry = run.get("authorizations", {}).get(action)
            if (
                not isinstance(current_entry, dict)
                or current_entry.get("authorized") is not True
            ):
                raise ManifestError(
                    "lifecycle authorization is no longer active; reserve a fresh node attempt"
                )
            if current_entry.get("authorized_head_sha") != reserved_head:
                raise ManifestError(
                    "lifecycle authorized head changed after reservation; reserve a fresh node attempt"
                )
            current_head = run.get("integration", {}).get("integration_head_sha")
            for mission_id in sorted(run.get("mission_states", {})):
                if not authorization_covers(
                    run,
                    action,
                    mission_id,
                    expected_target,
                    required_head_sha=reserved_head,
                ):
                    raise ManifestError(
                        "lifecycle authorization target or head is stale; reserve a fresh node attempt"
                    )
            if reserved_head is not None and current_head != reserved_head:
                raise ManifestError(
                    "lifecycle integration head changed after reservation; reserve a fresh node attempt"
                )
    # Local verifier execution files are retained before the gate projection is
    # written.  The worker-result transition owns the strict execution shape;
    # import lazily to keep the transition module's existing import graph
    # acyclic.
    verifier_paths = [Path(path) for path in (getattr(args, "verifier_result", []) or [])]
    retained_results: list[dict[str, Any]] = []
    for path in verifier_paths:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"cannot read verifier result: {exc}") from exc
        if isinstance(value, dict) and set(value) == {"verifier_execution"}:
            value = value["verifier_execution"]
        if not isinstance(value, dict):
            raise ManifestError("each retained verifier result must be an object")
        retained_results.append(value)
    from harness_worker_result_transition import record_local_node_verifier

    retained_records: list[dict[str, Any]] = []
    local_verifier = node.get("kind") == "verifier" and node.get("executor") in {
        "local_command",
        "harness_parent",
    }
    expected_request: dict[str, Any] | None = None
    protected_paths_at_execution: dict[str, str | None] | None = None
    if local_verifier and retained_results:
        dispatch = attempt.get("verifier_dispatch")
        if not isinstance(dispatch, dict):
            raise ManifestError(
                "local verifier result has no durable reservation binding"
            )
        repo_root = getattr(args, "repo_root", None)
        if repo_root is None:
            raise ManifestError(
                "record-node-result with verifier evidence requires --repo-root"
            )
        resolved_root = Path(repo_root).resolve()
        for path in verifier_paths:
            try:
                path.resolve().relative_to(resolved_root)
            except ValueError:
                continue
            raise ManifestError(
                "local verifier result files must live outside the reviewed checkout"
            )
        expected_request = _local_verifier_request(
            plan,
            run,
            node,
            attempt_id=attempt_id,
            repo_root=resolved_root,
            run_path=getattr(args, "run", None),
        )
        if (
            dispatch.get("branch") != expected_request["branch"]
            or dispatch.get("head_sha") != expected_request["head_sha"]
            or not _same_path(
                dispatch.get("checkout_root", ""),
                expected_request["checkout_root"],
            )
            or dispatch.get("request_sha256") != _json_sha256(expected_request)
            or dispatch.get("request") != expected_request
        ):
            raise ManifestError(
                "local verifier reservation no longer matches the current exact request"
            )
        if retained_results[0].get("context") != expected_request["context"]:
            raise ManifestError(
                "retained verifier context does not match the current exact checkout request"
            )
        if retained_results[0].get("reservation") != expected_request["reservation"]:
            raise ManifestError(
                "retained verifier reservation does not match the active node attempt"
            )
        retained_attestation = retained_results[0].get("dispatch_attestation")
        protected_paths_at_execution = (
            retained_attestation.get("protected_path_sha256")
            if isinstance(retained_attestation, dict)
            else None
        )
        expected_attestation = {
            "request_sha256": dispatch["request_sha256"],
            "checkout_root": expected_request["checkout_root"],
            "git_guard": expected_request["git_guard"],
            "protected_path_sha256": protected_paths_at_execution,
        }
        if retained_attestation != expected_attestation:
            raise ManifestError(
                "retained verifier dispatch attestation does not match the reserved checkout and request"
            )
        from verifier_runtime import protected_path_sha256

        current_protected_paths = protected_path_sha256(
            resolved_root,
            expected_request["git_guard"]["ignored_paths"],
        )
        if current_protected_paths != protected_paths_at_execution:
            raise ManifestError(
                "protected coordination files changed during or after verifier execution"
            )
        from verifier_runtime import (
            _git_guard_snapshot, build_execution_key, execution_retention_binding_errors,
        )

        retained = retained_results[0]
        if retained.get("status") == "PASS":
            binding_errors = execution_retention_binding_errors(retained, require_host_evidence=True)
            expected_key, expected_document = build_execution_key(
                expected_request["verifier"], expected_request["context"],
                checkout_root=resolved_root, host_preflight=expected_request["host_preflight"],
            )
            if (retained.get("key_document") != expected_document
                    or retained.get("execution_key") != expected_key
                    or retained.get("evidence_key") != expected_key):
                binding_errors.append("host execution key/preflight does not match the reserved request")
            git_attestation = retained.get("git_guard_attestation")
            snapshot = _git_guard_snapshot(resolved_root, expected_request["git_guard"])
            if not isinstance(git_attestation, dict) or any(
                git_attestation.get(key) != value for key, value in {
                    "checkout_root": expected_request["checkout_root"],
                    "git_guard": expected_request["git_guard"],
                    "source_head_sha": expected_request["head_sha"],
                    **{key: snapshot[key] for key in ("tracked_files", "protected_path_sha256")},
                }.items()
            ):
                binding_errors.append("host Git attestation does not match the reserved checkout")
            if binding_errors:
                raise ManifestError("; ".join(binding_errors))
    elif local_verifier and not isinstance(attempt.get("verifier_dispatch"), dict):
        raise ManifestError(
            "local verifier result has no durable reservation binding"
        )
    if local_verifier:
        retained_records = record_local_node_verifier(
            plan,
            run,
            node,
            attempt_id=attempt_id,
            outcome=outcome,
            retained_results=retained_results,
        )
    elif retained_results:
        raise ManifestError(
            "verifier execution evidence is only valid for local verifier nodes"
        )
    if expected_request is not None:
        # Recheck after parsing and retaining the result so a non-cooperating
        # checkout mutation during this short transaction cannot certify stale
        # bytes under the reserved head.
        _local_verifier_request(
            plan,
            run,
            node,
            attempt_id=attempt_id,
            repo_root=Path(args.repo_root),
            run_path=getattr(args, "run", None),
        )
        from verifier_runtime import protected_path_sha256

        if protected_path_sha256(
            Path(args.repo_root),
            expected_request["git_guard"]["ignored_paths"],
        ) != protected_paths_at_execution:
            raise ManifestError(
                "protected coordination files changed before recording verifier result"
            )

    phase = "succeeded" if outcome == "pass" else (
        "blocked" if outcome in {"blocked", "contract_gap"} else "failed"
    )
    state.update(
        {
            "phase": phase,
            "last_outcome": outcome,
            "bound_worker_id": None,
            "blockers": blockers if phase == "blocked" else [],
        }
    )
    attempt["result"] = outcome
    attempt["evidence"] = list(dict.fromkeys([*attempt.get("evidence", []), *evidence]))
    attempt["evidence"] = list(
        dict.fromkeys(
            [
                *attempt["evidence"],
                *[
                    item.get("evidence_key")
                    for item in retained_records
                    if isinstance(item.get("evidence_key"), str)
                ],
            ]
        )
    )
    if blockers:
        attempt["evidence"] = list(dict.fromkeys([*attempt["evidence"], *blockers]))

    edge_receipts: list[str] = []
    for edge in plan.get("graph", {}).get("edges", []):
        if (
            not isinstance(edge, dict)
            or edge.get("from") != node_id
            or edge.get("kind") != "route"
            or outcome not in edge.get("on_outcomes", [])
        ):
            continue
        edge_state = run["graph_state"]["edge_states"][edge["id"]]
        traversals = int(edge_state.get("traversals") or 0)
        bound = edge.get("max_traversals")
        if isinstance(bound, int) and traversals >= bound:
            edge_state["status"] = "exhausted"
        else:
            edge_state["status"] = "traversed"
            edge_state["traversals"] = traversals + 1
        edge_state["source_attempt_id"] = attempt_id
        edge_receipts.append(edge["id"])

    # A retry is a fresh reservation.  Clear the prior blocker only after a
    # terminal outcome has been durably recorded; selector re-arm is guarded by
    # the matching traversed route and remaining node budget.
    return {
        "command": "record-node-result",
        "node_id": node_id,
        "attempt_id": attempt_id,
        "outcome": outcome,
        "phase": phase,
        "evidence": list(attempt["evidence"]),
        "blockers": list(blockers),
        "traversed_edges": edge_receipts,
    }


def _lease_worker(plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace) -> None:
    wave = run.get("active_wave")
    if not isinstance(wave, dict) or wave.get("status") != "active":
        raise ManifestError("lease-worker requires an accepted active wave")
    desired_state = (run.get("control") or {}).get("desired_state")
    if desired_state != "running":
        raise ManifestError(
            f"run control desired_state is {desired_state!r}; "
            "lease-worker runs only while the run is running"
        )
    if args.mission_id not in wave.get("selected_missions", []):
        raise ManifestError("lease-worker mission is not in the active wave")
    report_path = getattr(args, "report_path", None)
    runtime_axes = run.get("runtime_capabilities", {})
    worker_runtime = getattr(args, "worker_runtime", None) or runtime_axes.get(
        "worker_runtime"
    )
    workspace_mode = getattr(args, "workspace_mode", None) or runtime_axes.get(
        "workspace_mode"
    )
    completion_channel = getattr(args, "completion_channel", None) or runtime_axes.get(
        "completion_channel"
    )
    if completion_channel == "report_file" and not (
        isinstance(report_path, str) and report_path.strip()
    ):
        raise ManifestError("lease-worker with report_file requires --report-path")
    if any(
        isinstance(item, dict) and item.get("worker_id") == args.worker_id
        for item in run.get("workers", [])
    ):
        raise ManifestError(f"worker id {args.worker_id!r} already exists")
    if any(
        isinstance(item, dict) and item.get("lease_id") == args.lease_id
        for item in run.get("workers", [])
    ):
        raise ManifestError(f"lease id {args.lease_id!r} already exists")
    if any(
        isinstance(item, dict) and item.get("attempt_id") == args.attempt_id
        for item in [*run.get("attempt_log", []), *run.get("review_workers", [])]
    ):
        raise ManifestError(f"duplicate attempt ID {args.attempt_id!r}")
    # A mission lease binds the mission's own graph node; node ids are only
    # conventionally N-<MISSION>, so resolve the node by kind+ref and require
    # the exact match instead of trusting the caller's node id.
    mission_node_ids = [
        node.get("id")
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict)
        and node.get("kind") == "mission"
        and node.get("ref") == args.mission_id
    ]
    if len(mission_node_ids) != 1:
        raise ManifestError(
            f"mission {args.mission_id!r} must map to exactly one graph mission node; "
            f"found {len(mission_node_ids)}"
        )
    if args.node_id != mission_node_ids[0]:
        raise ManifestError(
            f"node {args.node_id!r} is not mission {args.mission_id!r}'s node "
            f"{mission_node_ids[0]!r}"
        )
    mission_node = next(
        node
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict) and node.get("id") == args.node_id
    )
    mission_record = next(
        (
            mission
            for mission in plan.get("missions", [])
            if isinstance(mission, dict) and mission.get("id") == args.mission_id
        ),
        None,
    )
    # The selector is the sole source of runtime/provider/driver decisions.
    # Keep optional CLI identity fields as assertions for older launchers, but
    # derive the binding and execution axes from the current PLAN/RUN pair.
    expected_binding = _runtime_binding(
        mission_node,
        run.get("runtime_capabilities", {}),
        mission_record,
        next((row.get("impact") for row in run.get("ui_impact_summary", [])
              if isinstance(row, dict) and row.get("mission_id") == args.mission_id), None),
    )
    if expected_binding is None:
        raise ManifestError(
            f"mission {args.mission_id!r} has no runtime binding on the observed host"
        )
    for key in ("provider", "driver", "model", "reasoning_effort",
                "worker_runtime", "workspace_mode", "completion_channel"):
        supplied = getattr(args, key, None)
        expected = expected_binding.get(key, runtime_axes.get(key))
        if supplied is not None and supplied != expected:
            raise ManifestError(f"lease-worker {key} {supplied!r} does not match selector binding {expected!r}")
    worker_runtime = expected_binding.get("worker_runtime", runtime_axes["worker_runtime"])
    workspace_mode = expected_binding.get("workspace_mode", runtime_axes["workspace_mode"])
    completion_channel = expected_binding.get("completion_channel", runtime_axes["completion_channel"])
    task_thread_id = args.worker_id if worker_runtime == "app_task" else None
    node_states = run.get("graph_state", {}).get("node_states", {})
    node_state = node_states.get(args.node_id)
    if not isinstance(node_state, dict):
        raise ManifestError(f"no graph state for node {args.node_id!r}")
    mission_state = run.get("mission_states", {}).get(args.mission_id)
    if not isinstance(mission_state, dict):
        raise ManifestError(f"no mission state for {args.mission_id!r}")
    mission_phase = mission_state.get("phase")
    if mission_phase not in {"queued", "ready", "worker_failed", "blocked"}:
        raise ManifestError(
            f"mission {args.mission_id!r} is {mission_phase!r}; "
            "only queued, ready, worker_failed, or blocked missions accept a new lease"
        )
    if mission_phase in {"worker_failed", "blocked"}:
        latest_mission_attempt = next(
            (
                attempt
                for attempt in reversed(run.get("attempt_log", []))
                if isinstance(attempt, dict)
                and attempt.get("mission_id") == args.mission_id
            ),
            None,
        )
        retryable_failure = (
            mission_phase == "worker_failed"
            and node_state.get("phase") == "failed"
            and node_state.get("last_outcome") == "retryable_failure"
        )
        reconciled_interrupt = (
            mission_phase == "blocked"
            and node_state.get("phase") == "blocked"
            and node_state.get("last_outcome") == "blocked"
            and isinstance(latest_mission_attempt, dict)
            and latest_mission_attempt.get("kind")
            == "interrupted_worker_reconciliation"
            and latest_mission_attempt.get("result") == "blocked"
        )
        if not (retryable_failure or reconciled_interrupt):
            raise ManifestError(
                f"mission {args.mission_id!r} cannot be re-leased from "
                f"{mission_phase!r}; only retryable_failure or an interrupted "
                "worker reconciliation may retry without PLAN refinement"
            )
    # The dependency frontier must actually be ready: every graph dependency
    # into this mission node must have succeeded, and every mission-level
    # dependency must be integrated.
    for edge in plan.get("graph", {}).get("edges", []):
        if (
            not isinstance(edge, dict)
            or edge.get("kind") != "dependency"
            or edge.get("to") != args.node_id
        ):
            continue
        source_state = node_states.get(edge.get("from"))
        if not isinstance(source_state, dict) or source_state.get("phase") != "succeeded":
            raise ManifestError(
                f"dependency {edge.get('from')!r} -> {args.node_id!r} is not satisfied; "
                "the frontier is not ready for this lease"
            )
    mission_record = next(
        (
            mission
            for mission in plan.get("missions", [])
            if isinstance(mission, dict) and mission.get("id") == args.mission_id
        ),
        None,
    )
    if not isinstance(mission_record, dict):
        raise ManifestError(f"no PLAN mission for {args.mission_id!r}")
    if mission_has_ui_authoring_action(plan, mission_record):
        declared_skills = mission_record.get("required_skills", [])
        missing_skills = [
            skill
            for skill in UI_AUTHORING_REQUIRED_SKILLS
            if skill not in declared_skills
        ]
        if missing_skills:
            raise ManifestError(
                f"lease-worker mission {args.mission_id!r} can author UI source "
                "bytes and requires both 'ui-design-builder' and "
                f"'frontend-design'; missing {', '.join(missing_skills)}"
            )
    for dependency in (mission_record or {}).get("depends_on", []):
        dependency_state = run.get("mission_states", {}).get(dependency)
        if (
            not isinstance(dependency_state, dict)
            or dependency_state.get("phase") != "integrated"
        ):
            raise ManifestError(
                f"mission {dependency!r} must be integrated before leasing {args.mission_id!r}"
            )
    # The wave may not run two conflicting writers at once: check the leased
    # mission against every mission with a live worker, using the same
    # conflict rules the selector applies (write-scope overlap, serialized
    # resources, exclusive runtime resources).
    plan_missions = {
        item.get("id"): item
        for item in plan.get("missions", [])
        if isinstance(item, dict)
    }
    active_mission_ids = {
        worker.get("mission_id")
        for worker in run.get("workers", [])
        if isinstance(worker, dict)
        and worker.get("phase") in {"leased", "worker_running"}
    }
    for other_id in sorted(active_mission_ids):
        other_mission = plan_missions.get(other_id)
        if other_mission is None or other_id == args.mission_id:
            continue
        reasons = mission_conflicts(mission_record or {}, other_mission)
        if reasons:
            raise ManifestError(
                f"mission {args.mission_id!r} conflicts with active mission "
                f"{other_id!r} ({', '.join(reasons)}); the wave may not run both at once"
            )
    base_sha = wave.get("batch_base_sha")
    digest = (run.get("plan") or {}).get("digest_sha256")
    task_id = next(
        (
            tid
            for tid, state in run.get("task_states", {}).items()
            if tid in {
                task.get("id")
                for mission in plan.get("missions", [])
                if isinstance(mission, dict) and mission.get("id") == args.mission_id
                for task in mission.get("tasks", [])
                if isinstance(task, dict)
            }
            if isinstance(state, dict) and state.get("phase") in {"queued", "ready"}
        ),
        None,
    )
    # Materialize concrete authorization receipts only after every lease guard
    # has passed. A rejected phase, dependency, or conflict must not touch even
    # this in-memory copy of the authorization ledger.
    if run.get("schema_version") == 11:
        receipts: list[tuple[str, str]] = []
        if worker_runtime == "subagent":
            receipts.append(("spawn_subagents", f"worker:{args.worker_id}"))
            if expected_binding.get("source") == "external_bridge":
                receipts.append(
                    ("invoke_external_runtime", f"runtime:{expected_binding['bridge_identity']}")
                )
        elif worker_runtime == "app_task":
            receipts.append(("create_user_owned_tasks", f"task:{task_thread_id}"))
        if workspace_mode == "parent_managed_worktree":
            worktree_action = "create_local_worktrees"
        elif workspace_mode == "app_managed_worktree":
            worktree_action = "create_app_managed_worktrees"
        else:
            worktree_action = None
        if worktree_action is not None:
            receipts.append((worktree_action, f"worktree:{args.worktree_path}"))
            for action in ("create_local_branches", "create_local_commits"):
                receipts.append((action, f"branch:{args.branch_ref}"))
        # validate_run checks every receipt against exact mission ids at
        # every version, so a "*" mission scope would record a receipt it
        # then rejects. The selector defers these launches; refuse here too.
        for action, _target in receipts:
            scope = (run.get("authorizations", {}).get(action) or {}).get("scope")
            missions = scope.get("mission_ids") if isinstance(scope, dict) else None
            if isinstance(missions, list) and "*" in missions:
                raise ManifestError(
                    f"{action} grant has mission_ids '*'; lease-worker needs "
                    f"exact mission ids including {args.mission_id!r}"
                )
        for action, target in receipts:
            _materialize_authorized_target(run, action, args.mission_id, target)
    node_state.update(
        {
            "phase": "running",
            "attempts": int(node_state.get("attempts") or 0) + 1,
            "last_attempt_id": args.attempt_id,
            "bound_worker_id": args.worker_id,
            # A fresh attempt clears the prior attempt's terminal residue,
            # mirroring the review reservation's reset.
            "last_outcome": None,
            "blockers": [],
        }
    )
    mission_state.update(
        {
            "phase": "worker_running",
            "lease_id": args.lease_id,
            "lease_plan_revision": plan.get("revision"),
            "lease_plan_digest_sha256": digest,
            "worker_id": args.worker_id,
            "base_sha": base_sha,
            "head_sha": None,
            "blockers": [],
        }
    )
    if task_id is not None:
        task_state = run["task_states"][task_id]
        task_state.update(
            {"phase": "running", "attempts": int(task_state.get("attempts") or 0) + 1}
        )
    run["workers"].append(
        {
            "worker_id": args.worker_id,
            "mission_id": args.mission_id,
            "lease_id": args.lease_id,
            "plan_revision": plan.get("revision"),
            "plan_digest_sha256": digest,
            "batch_base_sha": base_sha,
            "worker_runtime": worker_runtime,
            "workspace_mode": workspace_mode,
            "completion_channel": completion_channel,
            "runtime_binding": copy.deepcopy(expected_binding),
            "task_thread_id": task_thread_id,
            "worktree_path": args.worktree_path,
            "branch_ref": args.branch_ref,
            "report_path": report_path,
            "phase": "worker_running",
            "worker_head_sha": None,
            "attempt_id": args.attempt_id,
        }
    )
    run["attempt_log"].append(
        {
            "attempt_id": args.attempt_id,
            "mission_id": args.mission_id,
            "task_id": task_id,
            "lease_id": args.lease_id,
            "kind": "dispatch",
            "result": "dispatched",
            "evidence": [f"leased worker {args.worker_id} on {args.branch_ref}"],
        }
    )


def _record_integration(plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace) -> None:
    mission_state = run.get("mission_states", {}).get(args.mission_id)
    if not isinstance(mission_state, dict):
        raise ManifestError(f"no mission state for {args.mission_id!r}")
    if mission_state.get("phase") not in {"worker_passed", "integrating"}:
        raise ManifestError(
            f"mission {args.mission_id!r} is {mission_state.get('phase')!r}; "
            "integration records require worker_passed or integrating"
        )
    if not is_full_sha(args.integrated_sha):
        raise ManifestError("record-integration requires a full integrated SHA")
    if args.repo_root is None:
        raise ManifestError("record-integration requires --repo-root")
    observed = run.get("observed")
    observed_git = observed.get("git") if isinstance(observed, dict) else None
    observed_path = (
        observed_git.get("parent_worktree_path")
        if isinstance(observed_git, dict)
        else None
    )
    if not isinstance(observed_path, str) or not _same_path(
        args.repo_root, observed_path
    ):
        raise ManifestError(
            f"--repo-root {args.repo_root} is not the observed parent worktree "
            f"{observed_path!r}; record integration from the observed checkout"
        )
    expected_branch = _require_non_default_integration_branch(run)
    live_branch = _git_branch_name(args.repo_root)
    if _normalized_branch(live_branch) != expected_branch:
        raise ManifestError(
            f"--repo-root is on branch {live_branch!r}, not the integration branch "
            f"{run.get('integration', {}).get('branch')!r}"
        )
    if _git_status_excluding_run(
        args.repo_root, getattr(args, "run", None), run
    ).strip():
        raise ManifestError(
            "--repo-root product tree is dirty; record integration from a checkout "
            "whose only allowed change is RUN and its declared generated tasks view"
        )
    worker_head = mission_state.get("head_sha")
    if not is_full_sha(worker_head):
        raise ManifestError("record-integration requires the mission's worker head SHA")
    if worker_head != args.integrated_sha:
        if not _git_is_ancestor(args.repo_root, worker_head, args.integrated_sha):
            raise ManifestError(
                f"worker head {worker_head} is not contained in {args.integrated_sha}; "
                "integrate the mission's work first"
            )
    batch_base_sha = run.get("integration", {}).get("batch_base_sha")
    if not is_full_sha(batch_base_sha):
        raise ManifestError("record-integration requires the run's integration batch_base_sha")
    previous_integration_head = run.get("integration", {}).get(
        "integration_head_sha"
    )
    if previous_integration_head is not None and not is_full_sha(
        previous_integration_head
    ):
        raise ManifestError(
            "record-integration requires a full prior integration_head_sha when present"
        )
    integration_parent = previous_integration_head or batch_base_sha
    if not _git_is_ancestor(args.repo_root, integration_parent, args.integrated_sha):
        raise ManifestError(
            f"prior integration head {integration_parent} is not an ancestor of "
            f"{args.integrated_sha}; record-integration may only move forward"
        )
    if not _git_is_ancestor(args.repo_root, batch_base_sha, args.integrated_sha):
        raise ManifestError(
            f"batch base {batch_base_sha} is not an ancestor of {args.integrated_sha}"
        )
    mission_contract = next(
        (
            mission
            for mission in plan.get("missions", [])
            if isinstance(mission, dict) and mission.get("id") == args.mission_id
        ),
        None,
    )
    integration_scopes = list(
        mission_contract.get("write_scope", []) if isinstance(mission_contract, dict) else []
    )
    _reject_unplanned_candidate_paths(
        plan, run, args.repo_root, integration_parent, args.integrated_sha,
        allowed_scopes=sorted(set(integration_scopes)),
    )
    live_head = _git_out(args.repo_root, "rev-parse", "HEAD").strip()
    if live_head != args.integrated_sha:
        raise ManifestError(
            f"integration branch HEAD is {live_head}, not {args.integrated_sha}; "
            "integrate first, then record"
        )
    from harness_integration_results import retain_integration_results

    retain_integration_results(plan, run, args)
    previous_head = run.get("integration", {}).get("integration_head_sha")
    if is_full_sha(previous_head) and previous_head != args.integrated_sha:
        inactive_skips = _inactive_skipped_integration_reviews(plan, run)
        if inactive_skips:
            raise ManifestError(
                "record-integration cannot preserve inactive skipped integration "
                "reviews across a new candidate tree; refine the recovery graph first: "
                + ", ".join(inactive_skips)
            )
        # A new head re-arms every gate and integration review; refuse now
        # rather than leave one re-armed with no budget to run again.
        _require_candidate_revalidation_budget(plan, run)
        prior_heads = run["integration"].setdefault("prior_head_shas", [])
        if previous_head not in prior_heads:
            prior_heads.append(previous_head)
        _invalidate_stale_current_projections(plan, run, previous_head, args.integrated_sha)
    mission_state.update(
        {
            "phase": "integrated",
            "integration_gate": "PASS",
            "integrated_sha": args.integrated_sha,
        }
    )
    # Resolve the mission's node from the PLAN graph by kind+ref — node ids
    # are only conventionally N-<MISSION>, never enforced by the schema.
    mission_node_ids = [
        node.get("id")
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict)
        and node.get("kind") == "mission"
        and node.get("ref") == args.mission_id
    ]
    if len(mission_node_ids) != 1:
        raise ManifestError(
            f"mission {args.mission_id!r} must map to exactly one graph mission node; "
            f"found {len(mission_node_ids)}"
        )
    node_state = run.get("graph_state", {}).get("node_states", {}).get(
        mission_node_ids[0]
    )
    if isinstance(node_state, dict):
        node_state.update({"phase": "succeeded", "last_outcome": "pass"})
    run["integration"]["integration_head_sha"] = args.integrated_sha


def _invalidate_stale_current_projections(
    plan: dict[str, Any],
    run: dict[str, Any],
    previous_head: str,
    new_head: str,
) -> None:
    """Reset current PASS projections invalidated by a forward candidate move.

    Retained executions, failed attempts, review records, grants, and head
    history are immutable. Only the current result projection and the current
    graph binding become stale; later gates must run fresh against the new
    exact candidate.
    """

    del previous_head
    for result in [
        *run.get("batch_gate_results", []),
        *run.get("final_gate_results", []),
    ]:
        if isinstance(result, dict):
            result["status"] = "planned"
            result["head_sha"] = None
            result["evidence"] = []

    for evidence in run.get("ui_evidence", []):
        if isinstance(evidence, dict) and evidence.get("status") == "PASS":
            # Keep the accepted artifact and its old exact head for audit.  The
            # row is the current matrix projection, so only its PASS status is
            # re-armed for recapture on the new candidate.
            evidence["status"] = "planned"

    gate_ids = {
        verifier.get("id")
        for group in ("batch_verifiers", "final_gates")
        for verifier in plan.get(group, [])
        if isinstance(verifier, dict) and _nonempty_string(verifier.get("id"))
    }
    for node in plan.get("graph", {}).get("nodes", []):
        if not isinstance(node, dict) or node.get("kind") != "verifier":
            continue
        state = run.get("graph_state", {}).get("node_states", {}).get(node.get("id"))
        if not isinstance(state, dict):
            continue
        if (
            node.get("executor") in {"local_command", "harness_parent"}
            and node.get("ref") in gate_ids
            and state.get("phase") in {"succeeded", "failed", "blocked"}
        ):
            state.update(
                {
                    "phase": "ready",
                    "last_attempt_id": None,
                    "last_outcome": None,
                    "bound_worker_id": None,
                }
            )
            continue
        review = node.get("review")
        if (
            isinstance(review, dict)
            and review.get("stage", "preintegration") == "integration"
            and state.get("phase") in {"succeeded", "failed", "blocked", "skipped"}
        ):
            current_worker = next(
                (
                    worker
                    for worker in run.get("review_workers", [])
                    if isinstance(worker, dict)
                    and worker.get("node_id") == node.get("id")
                    and worker.get("worker_id") == state.get("bound_worker_id")
                    and worker.get("attempt_id") == state.get("last_attempt_id")
                ),
                None,
            )
            if (
                not isinstance(current_worker, dict)
                or current_worker.get("reviewed_sha") != new_head
            ):
                state.update(
                    {
                        "phase": "ready",
                        "last_attempt_id": None,
                        "last_outcome": None,
                        "bound_worker_id": None,
                    }
                )

    integration = run.get("integration")
    if isinstance(integration, dict):
        integration.pop("integration_tree_sha", None)
        integration.pop("reviewed_merge_chain", None)


def _integration_review_route_active(
    plan: dict[str, Any], run: dict[str, Any], node_id: Any
) -> bool:
    incoming_routes = [
        edge
        for edge in plan.get("graph", {}).get("edges", [])
        if isinstance(edge, dict)
        and edge.get("kind") == "route"
        and edge.get("to") == node_id
    ]
    if not incoming_routes:
        return True
    node_states = run.get("graph_state", {}).get("node_states", {})
    edge_states = run.get("graph_state", {}).get("edge_states", {})
    for edge in incoming_routes:
        source = node_states.get(edge.get("from")) if isinstance(node_states, dict) else None
        edge_state = edge_states.get(edge.get("id")) if isinstance(edge_states, dict) else None
        if (
            isinstance(source, dict)
            and source.get("phase") in {"succeeded", "failed", "blocked"}
            and source.get("last_outcome") in edge.get("on_outcomes", [])
            and (not isinstance(edge_state, dict) or edge_state.get("status") != "exhausted")
        ):
            return True
    return False


def _candidate_revalidation_nodes(
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    gate_ids = {
        verifier.get("id")
        for group in ("batch_verifiers", "final_gates")
        for verifier in plan.get(group, [])
        if isinstance(verifier, dict) and _nonempty_string(verifier.get("id"))
    }
    nodes: list[dict[str, Any]] = []
    for node in plan.get("graph", {}).get("nodes", []):
        if not (
            isinstance(node, dict)
            and node.get("kind") == "verifier"
            and (
                (
                    node.get("executor") in {"local_command", "harness_parent"}
                    and node.get("ref") in gate_ids
                )
                or (
                    node.get("executor") == "runtime_worker"
                    and isinstance(node.get("review"), dict)
                    and node["review"].get("stage", "preintegration")
                    == "integration"
                )
            )
        ):
            continue
        nodes.append(node)
    return nodes


def _inactive_skipped_integration_reviews(
    plan: dict[str, Any], run: dict[str, Any]
) -> list[str]:
    node_states = run.get("graph_state", {}).get("node_states", {})
    return sorted(
        str(node.get("id"))
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict)
        and node.get("kind") == "verifier"
        and node.get("executor") == "runtime_worker"
        and isinstance(node.get("review"), dict)
        and node["review"].get("stage", "preintegration") == "integration"
        and isinstance(node_states, dict)
        and isinstance(node_states.get(node.get("id")), dict)
        and node_states[node.get("id")].get("phase") == "skipped"
        and not _integration_review_route_active(plan, run, node.get("id"))
    )


def _require_candidate_revalidation_budget(
    plan: dict[str, Any], run: dict[str, Any]
) -> None:
    edge_states = run.get("graph_state", {}).get("edge_states", {})
    node_states = run.get("graph_state", {}).get("node_states", {})
    for node in _candidate_revalidation_nodes(plan):
        node_id = node.get("id")
        state = node_states.get(node_id) if isinstance(node_states, dict) else None
        if not isinstance(state, dict):
            raise ManifestError(f"candidate reconciliation has no graph state for {node_id!r}")
        if int(state.get("attempts") or 0) >= int(node.get("max_attempts") or 0):
            raise ManifestError(
                f"candidate reconciliation cannot re-arm {node_id!r}; "
                "its node attempt budget is exhausted"
            )

        for edge in plan.get("graph", {}).get("edges", []):
            if (
                not isinstance(edge, dict)
                or edge.get("kind") != "route"
                or edge.get("from") != node_id
                or "pass" not in edge.get("on_outcomes", [])
            ):
                continue
            edge_state = edge_states.get(edge.get("id")) if isinstance(edge_states, dict) else None
            bound = edge.get("max_traversals")
            traversals = (
                int(edge_state.get("traversals") or 0)
                if isinstance(edge_state, dict)
                else 0
            )
            if isinstance(bound, int) and traversals >= bound:
                raise ManifestError(
                    f"candidate reconciliation cannot re-arm {node_id!r}; "
                    f"pass route {edge.get('id')!r} exhausted its traversal budget"
                )


def _reconcile_candidate_head(
    plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    """Bind one already-committed, in-scope repair to the current RUN.

    This transition changes no Git state and grants no action.  It advances the
    candidate only after every mission is integrated, then re-arms exact-head
    integration reviews and deterministic gates without changing their history
    or attempt budgets.
    """

    if run.get("schema_version") != 11 or plan.get("schema_version") != 6:
        raise ManifestError("reconcile-candidate-head requires PLAN v6 and RUN v11")
    if args.repo_root is None:
        raise ManifestError("reconcile-candidate-head requires --repo-root")
    if not _nonempty_string(getattr(args, "source", None)):
        raise ManifestError("reconcile-candidate-head requires a non-empty --source")
    candidate_sha = getattr(args, "candidate_sha", None)
    if not is_full_sha(candidate_sha):
        raise ManifestError("reconcile-candidate-head requires a full --candidate-sha")
    if run.get("status") not in RUN_DISPATCH_STATUSES:
        raise ManifestError("reconcile-candidate-head requires a ready or running RUN")
    if run.get("control", {}).get("desired_state") != "running":
        raise ManifestError("reconcile-candidate-head requires desired_state running")

    integration = run.get("integration")
    current_head = (
        integration.get("integration_head_sha")
        if isinstance(integration, dict)
        else None
    )
    if not is_full_sha(current_head):
        raise ManifestError("reconcile-candidate-head requires a current integration head")
    if candidate_sha == current_head:
        raise ManifestError(
            "candidate SHA already equals integration_head_sha; no reconciliation is needed"
        )
    inactive_skips = _inactive_skipped_integration_reviews(plan, run)
    if inactive_skips:
        raise ManifestError(
            "candidate reconciliation cannot preserve inactive skipped integration "
            "reviews across a new candidate tree; refine the recovery graph first: "
            + ", ".join(inactive_skips)
        )

    repair_node_id = getattr(args, "repair_node_id", None)
    repair_attempt_id = getattr(args, "repair_attempt_id", None)
    repair_task_id = getattr(args, "repair_task_id", None)
    repair_node = _graph_node(plan, repair_node_id)
    repair_state = run.get("graph_state", {}).get("node_states", {}).get(
        repair_node_id
    )
    if not isinstance(repair_state, dict) or repair_state.get("phase") not in {
        "failed",
        "blocked",
    }:
        raise ManifestError(
            "candidate reconciliation requires a current failed or blocked repair node"
        )
    if repair_state.get("last_attempt_id") != repair_attempt_id:
        raise ManifestError(
            "--repair-attempt-id must equal the repair node's current terminal attempt"
        )
    repair_outcome = repair_state.get("last_outcome")
    review = repair_node.get("review")
    deterministic_repair = (
        repair_node.get("kind") == "verifier"
        and repair_node.get("executor") in {"local_command", "harness_parent"}
        and any(
            isinstance(item, dict) and item.get("id") == repair_node.get("ref")
            for group in ("batch_verifiers", "final_gates")
            for item in plan.get(group, [])
        )
    )
    integration_review_repair = (
        repair_node.get("kind") == "verifier"
        and repair_node.get("executor") == "runtime_worker"
        and isinstance(review, dict)
        and review.get("stage", "preintegration") == "integration"
    )
    if not deterministic_repair and not integration_review_repair:
        raise ManifestError(
            "repair node must be an integration-stage review or batch/final verifier"
        )
    retained_attempt = next(
        (
            item
            for item in run.get("attempt_log", [])
            if isinstance(item, dict)
            and item.get("attempt_id") == repair_attempt_id
        ),
        None,
    )
    if not isinstance(retained_attempt, dict):
        raise ManifestError("repair attempt is not retained in attempt_log")
    if integration_review_repair:
        if repair_outcome != "fix_required":
            raise ManifestError(
                "integration review repair requires a retained fix_required outcome"
            )
        lineage_id = review.get("lineage_id")
        if (
            retained_attempt.get("kind") != "review"
            or retained_attempt.get("result") != "fix_required"
            or retained_attempt.get("review_lineage_id") != lineage_id
        ):
            raise ManifestError(
                "repair attempt does not match the integration review failure receipt"
            )
        retained_worker = next(
            (
                worker
                for worker in run.get("review_workers", [])
                if isinstance(worker, dict)
                and worker.get("node_id") == repair_node_id
                and worker.get("attempt_id") == repair_attempt_id
                and worker.get("outcome") == "fix_required"
            ),
            None,
        )
        if not isinstance(retained_worker, dict):
            raise ManifestError(
                "repair attempt has no matching fix_required review worker"
            )
    elif (
        repair_outcome not in {"fix_required", "retryable_failure"}
        or retained_attempt.get("kind") != "node_attempt"
        or retained_attempt.get("node_id") != repair_node_id
        or retained_attempt.get("result") != repair_outcome
    ):
        raise ManifestError(
            "repair attempt does not match the batch/final verifier failure receipt"
        )

    declared_repair_paths = list(getattr(args, "repair_path", None) or [])
    for repair_path in declared_repair_paths:
        reason = validate_changed_path(repair_path)
        if reason is None and repair_path.startswith(":"):
            reason = "must not start with Git pathspec magic"
        if reason is None and "[" in repair_path:
            reason = "contains unsupported glob syntax"
        if reason:
            raise ManifestError(
                "--repair-path must be a literal repository-relative file path: "
                f"{repair_path!r} {reason}"
            )
    task_matches = [
        (mission, task)
        for mission in plan.get("missions", [])
        if isinstance(mission, dict)
        for task in mission.get("tasks", [])
        if isinstance(task, dict) and task.get("id") == repair_task_id
    ]
    if len(task_matches) != 1:
        raise ManifestError(
            "--repair-task-id must identify exactly one existing PLAN task"
        )
    repair_mission, repair_task = task_matches[0]
    repair_mission_id = repair_mission.get("id")
    if integration_review_repair and repair_mission_id not in review.get(
        "mission_ids", []
    ):
        raise ManifestError(
            "repair task mission is not covered by the failed integration review"
        )
    branch_target = f"branch:{integration.get('branch')}"
    if not execution_covers(run, repair_mission_id):
        raise ManifestError(
            "repair task mission is not covered by current execution authorization"
        )
    for action in ("create_local_commits", "integrate_locally"):
        if not authorization_covers(
            run,
            action,
            repair_mission_id,
            branch_target,
            require_exact_target=True,
        ):
            raise ManifestError(
                f"candidate reconciliation requires pre-existing exact {action} "
                f"authorization for {repair_mission_id!r} and {branch_target!r}"
            )

    root = Path(args.repo_root).resolve()
    repo_top_level = Path(_git_out(root, "rev-parse", "--show-toplevel").strip()).resolve()
    if not _same_path(root, repo_top_level):
        raise ManifestError("--repo-root must be the exact repository top-level checkout")
    observed = run.get("observed")
    observed_git = observed.get("git") if isinstance(observed, dict) else None
    if not isinstance(observed, dict) or not observed.get("captured_at"):
        raise ManifestError("reconcile-candidate-head requires a fresh parent observation")
    observed_path = (
        observed_git.get("parent_worktree_path")
        if isinstance(observed_git, dict)
        else None
    )
    if not isinstance(observed_path, str) or not _same_path(root, observed_path):
        raise ManifestError(
            f"--repo-root {root} is not the observed parent worktree {observed_path!r}"
        )
    expected_branch = _require_non_default_integration_branch(run)
    live_branch = _git_branch_name(root)
    observed_branch = (
        _normalized_branch(observed_git.get("parent_branch"))
        if isinstance(observed_git, dict)
        else None
    )
    if _normalized_branch(live_branch) != expected_branch or observed_branch != expected_branch:
        raise ManifestError(
            "reconcile-candidate-head requires the live and observed parent branch "
            "to equal the non-default integration branch"
        )
    live_head = _git_out(root, "rev-parse", "HEAD").strip()
    observed_head = (
        observed_git.get("parent_head_sha")
        if isinstance(observed_git, dict)
        else None
    )
    if live_head != candidate_sha or observed_head != candidate_sha:
        raise ManifestError(
            "reconcile-candidate-head requires --candidate-sha to equal both the "
            "live and freshly observed parent HEAD"
        )
    if (
        not isinstance(observed_git, dict)
        or observed_git.get("parent_dirty") is not False
        or _git_status_excluding_run(root, getattr(args, "run", None), run).strip()
    ):
        raise ManifestError(
            "reconcile-candidate-head requires a clean product tree apart from RUN "
            "and its declared generated tasks view"
        )
    if not _git_is_ancestor(root, current_head, candidate_sha):
        raise ManifestError(
            f"current candidate {current_head} is not an ancestor of {candidate_sha}"
        )
    batch_base = integration.get("batch_base_sha")
    if not is_full_sha(batch_base) or not _git_is_ancestor(root, batch_base, candidate_sha):
        raise ManifestError("candidate repair must retain the run batch base as an ancestor")

    incomplete_missions: list[str] = []
    for mission_id, state in run.get("mission_states", {}).items():
        integrated_sha = state.get("integrated_sha") if isinstance(state, dict) else None
        if (
            not isinstance(state, dict)
            or state.get("phase") != "integrated"
            or state.get("integration_gate") != "PASS"
            or not is_full_sha(integrated_sha)
            or not _git_is_ancestor(root, integrated_sha, candidate_sha)
        ):
            incomplete_missions.append(str(mission_id))
    if incomplete_missions:
        raise ManifestError(
            "reconcile-candidate-head requires every mission's integrated PASS to be "
            "reachable from the repair candidate: " + ", ".join(sorted(incomplete_missions))
        )

    wave = run.get("active_wave")
    if isinstance(wave, dict) and wave.get("status") in {"proposed", "active"}:
        raise ManifestError("reconcile-candidate-head refuses an active or proposed wave")
    live_workers = sorted(
        str(worker.get("worker_id"))
        for worker in [*run.get("workers", []), *run.get("review_workers", [])]
        if isinstance(worker, dict) and worker.get("phase") in {"leased", "worker_running"}
    )
    running_nodes = sorted(
        str(node_id)
        for node_id, state in run.get("graph_state", {}).get("node_states", {}).items()
        if isinstance(state, dict) and state.get("phase") == "running"
    )
    if live_workers or running_nodes:
        details = ", ".join([*live_workers, *running_nodes])
        raise ManifestError(
            "reconcile-candidate-head refuses active work; reconcile first: " + details
        )

    repair_scopes = [
        scope for scope in repair_task.get("write_scope", []) if isinstance(scope, str)
    ]
    if not repair_scopes:
        raise ManifestError("repair task has no declared write scope")
    _reject_unplanned_candidate_paths(
        plan,
        run,
        root,
        current_head,
        candidate_sha,
        allowed_scopes=repair_scopes,
    )
    if integration_review_repair:
        review_scopes = [
            scope for scope in review.get("scope", []) if isinstance(scope, str)
        ]
        if not review_scopes:
            raise ManifestError("failed integration review has no declared scope")
        _reject_unplanned_candidate_paths(
            plan,
            run,
            root,
            current_head,
            candidate_sha,
            allowed_scopes=review_scopes,
        )
    if declared_repair_paths:
        changed_paths = _candidate_changed_paths(root, current_head, candidate_sha)
        outside_scopes = [
            path for path in changed_paths if path not in declared_repair_paths
        ]
        if outside_scopes:
            raise ManifestError(
                "repair changed paths outside --repair-path scope: "
                + ", ".join(outside_scopes)
            )
        scoped_view = _literal_pathspec_diff_paths(
            root, current_head, candidate_sha, declared_repair_paths
        )
        hidden = [path for path in changed_paths if path not in scoped_view]
        if hidden:
            raise ManifestError(
                "--repair-path scope would hide changed candidate paths: "
                + ", ".join(hidden)
            )
        for repair_path in declared_repair_paths:
            if repair_path in changed_paths:
                continue
            probe = run_git(
                root, "cat-file", "-e", f"{candidate_sha}:{repair_path}"
            )
            if probe.returncode != 0:
                raise ManifestError(
                    "--repair-path must name a file the candidate changes or "
                    f"a file present in the candidate tree: {repair_path!r}"
                )
    if not declared_repair_paths:
        # An isolated --repair-path repair re-arms the review node for a scoped
        # review whose PASS refunds the attempt, so only an ordinary repair
        # stays bound by the revalidation budget here.
        _require_candidate_revalidation_budget(plan, run)

    # The scope and budget checks above may take time.  Bind the mutation to a
    # second live Git observation so a concurrent commit, checkout, or product
    # edit cannot be adopted under the first observation.
    final_branch = _git_branch_name(root)
    final_head = _git_out(root, "rev-parse", "HEAD").strip()
    final_dirty = _git_status_excluding_run(
        root, getattr(args, "run", None), run
    ).strip()
    if (
        _normalized_branch(final_branch) != expected_branch
        or final_head != candidate_sha
        or final_dirty
    ):
        raise ManifestError(
            "repository branch, HEAD, or product tree changed during candidate "
            "reconciliation; refresh observation and retry"
        )
    authorizations_before = copy.deepcopy(run.get("authorizations"))
    execution_authorization_before = (
        run.get("execution_authorized"),
        copy.deepcopy(run.get("execution_authorization_scope")),
        run.get("execution_authorization_source"),
    )
    prior_heads = integration.setdefault("prior_head_shas", [])
    if current_head not in prior_heads:
        prior_heads.append(current_head)
    if declared_repair_paths:
        integration.setdefault("repair_scopes", []).append(
            {
                "candidate_sha": candidate_sha,
                "prior_head_sha": current_head,
                "repair_paths": list(declared_repair_paths),
                "source": args.source,
                "trust_boundary": bool(getattr(args, "trust_boundary", False)),
            }
        )
    _invalidate_stale_current_projections(plan, run, current_head, candidate_sha)
    integration["integration_head_sha"] = candidate_sha
    continuity = run.get("landing", {}).get("continuity")
    if isinstance(continuity, dict) and continuity.get("status") == "preserved":
        continuity["head_sha"] = candidate_sha
    if run.get("authorizations") != authorizations_before or (
        run.get("execution_authorized"),
        run.get("execution_authorization_scope"),
        run.get("execution_authorization_source"),
    ) != execution_authorization_before:
        raise ManifestError("candidate reconciliation must not change authorization")
    event_id = f"CANDIDATE-HEAD-{candidate_sha[:12]}-{len(run.get('attempt_log', [])) + 1}"
    run.setdefault("attempt_log", []).append(
        {
            "attempt_id": event_id,
            "mission_id": None,
            "task_id": None,
            "lease_id": None,
            "kind": "candidate_head_reconciliation",
            "result": "recorded",
            "evidence": [
                args.source,
                f"advanced integration head from {current_head} to {candidate_sha}",
                f"repair receipt {repair_node_id}/{repair_attempt_id}",
                f"repair task {repair_task_id}",
            ],
        }
    )
    return {
        "command": "reconcile-candidate-head",
        "previous_head_sha": current_head,
        "candidate_sha": candidate_sha,
        "repair_node_id": repair_node_id,
        "repair_attempt_id": repair_attempt_id,
        "repair_task_id": repair_task_id,
        "revalidation_nodes": [
            node.get("id") for node in _candidate_revalidation_nodes(plan)
        ],
    }


def _reconcile_coordination_head(
    plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace
) -> None:
    """Bind one committed coordination-only checkpoint to the current RUN.

    This is not a product-candidate repair and changes no Git state. It lets the
    documented integration/wave-close bookkeeping commit advance the live parent
    head while retaining the prior integration head and all old evidence.
    """

    if plan.get("schema_version") != 6 or run.get("schema_version") != 11:
        raise ManifestError("reconcile-coordination-head requires PLAN v6 and RUN v11")
    if args.repo_root is None:
        raise ManifestError("reconcile-coordination-head requires --repo-root")
    if not _nonempty_string(getattr(args, "source", None)):
        raise ManifestError("reconcile-coordination-head requires a non-empty --source")
    candidate_sha = getattr(args, "candidate_sha", None)
    if not is_full_sha(candidate_sha):
        raise ManifestError("reconcile-coordination-head requires a full --candidate-sha")
    if run.get("status") not in RUN_DISPATCH_STATUSES:
        raise ManifestError("reconcile-coordination-head requires a ready or running RUN")
    if run.get("control", {}).get("desired_state") != "running":
        raise ManifestError("reconcile-coordination-head requires desired_state running")

    integration = run.get("integration")
    current_head = (
        integration.get("integration_head_sha")
        if isinstance(integration, dict)
        else None
    )
    if not is_full_sha(current_head):
        raise ManifestError("reconcile-coordination-head requires a current integration head")
    if candidate_sha == current_head:
        raise ManifestError(
            "candidate SHA already equals integration_head_sha; no reconciliation is needed"
        )
    prior_heads = integration.get("prior_head_shas", [])
    replay_event = any(
        isinstance(item, dict)
        and item.get("kind") == "coordination_head_reconciliation"
        and item.get("result") == "recorded"
        and f"new_head_sha={candidate_sha}" in item.get("evidence", [])
        for item in run.get("attempt_log", [])
    )
    if (isinstance(prior_heads, list) and candidate_sha in prior_heads) or replay_event:
        raise ManifestError("coordination head was already reconciled; replay is refused")

    root = Path(args.repo_root).resolve()
    repo_top_level = Path(_git_out(root, "rev-parse", "--show-toplevel").strip()).resolve()
    if not _same_path(root, repo_top_level):
        raise ManifestError("--repo-root must be the exact repository top-level checkout")
    _require_observed_plan_identity(plan, run, "reconcile-coordination-head")
    observed = run.get("observed")
    observed_git = observed.get("git") if isinstance(observed, dict) else None
    observed_path = (
        observed_git.get("parent_worktree_path")
        if isinstance(observed_git, dict)
        else None
    )
    if not isinstance(observed_path, str) or not _same_path(root, observed_path):
        raise ManifestError(
            f"--repo-root {root} is not the observed parent worktree {observed_path!r}"
        )
    expected_branch = _require_non_default_integration_branch(run)
    live_branch = _git_branch_name(root)
    observed_branch = (
        _normalized_branch(observed_git.get("parent_branch"))
        if isinstance(observed_git, dict)
        else None
    )
    if _normalized_branch(live_branch) != expected_branch or observed_branch != expected_branch:
        raise ManifestError(
            "reconcile-coordination-head requires the live and observed parent branch "
            "to equal the non-default integration branch"
        )
    live_head = _git_out(root, "rev-parse", "HEAD").strip()
    observed_head = (
        observed_git.get("parent_head_sha")
        if isinstance(observed_git, dict)
        else None
    )
    if live_head != candidate_sha or observed_head != candidate_sha:
        raise ManifestError(
            "reconcile-coordination-head requires --candidate-sha to equal both the "
            "live and freshly observed parent HEAD"
        )
    if (
        not isinstance(observed_git, dict)
        or observed_git.get("parent_dirty") is not False
        or _git_status_excluding_run(root, getattr(args, "run", None), run).strip()
    ):
        raise ManifestError(
            "reconcile-coordination-head requires a clean product tree apart from RUN "
            "and its declared generated tasks view"
        )

    parent_output = _git_out(root, "rev-list", "--parents", "-n", "1", candidate_sha).split()
    if len(parent_output) != 2 or parent_output[1] != current_head:
        raise ManifestError(
            "coordination head must be one ordinary direct child of the recorded integration head"
        )
    batch_base = integration.get("batch_base_sha")
    if not is_full_sha(batch_base) or not _git_is_ancestor(root, batch_base, candidate_sha):
        raise ManifestError(
            "coordination checkpoint must retain the run batch base as an ancestor"
        )

    review_nodes = {
        node.get("id"): node
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("review"), dict)
    }
    live_review_workers = []
    for worker in run.get("review_workers", []):
        if not (
            isinstance(worker, dict)
            and worker.get("phase") in {"leased", "worker_running"}
        ):
            continue
        review_node = review_nodes.get(worker.get("node_id"))
        if (
            not isinstance(review_node, dict)
            or review_node.get("review", {}).get("stage", "preintegration")
            == "integration"
        ):
            live_review_workers.append(str(worker.get("worker_id")))
    if live_review_workers:
        raise ManifestError(
            "reconcile-coordination-head refuses live reviewers: "
            + ", ".join(live_review_workers)
        )
    running_parent_nodes = sorted(
        str(node_id)
        for node_id, state in run.get("graph_state", {}).get("node_states", {}).items()
        if isinstance(state, dict)
        and state.get("phase") == "running"
        and not state.get("bound_worker_id")
    )
    if running_parent_nodes:
        raise ManifestError(
            "reconcile-coordination-head refuses running parent-owned nodes: "
            + ", ".join(running_parent_nodes)
        )
    nonisolated_writers = []
    for worker in run.get("workers", []):
        if not (
            isinstance(worker, dict)
            and worker.get("phase") in {"leased", "worker_running"}
        ):
            continue
        worktree = worker.get("worktree_path")
        if (
            worker.get("workspace_mode") not in {
                "parent_managed_worktree",
                "app_managed_worktree",
            }
            or not isinstance(worktree, str)
            or not worktree
            or _same_path(worktree, root)
        ):
            nonisolated_writers.append(str(worker.get("worker_id")))
    if nonisolated_writers:
        raise ManifestError(
            "in-flight writers must use isolated worktrees; parent checkout writers: "
            + ", ".join(sorted(nonisolated_writers))
        )

    coordination_paths_value = integration.get("coordination_paths", [])
    if not isinstance(coordination_paths_value, list):
        raise ManifestError("RUN coordination paths are invalid")
    exact_coordination_paths = {
        path for path in coordination_paths_value
        if isinstance(path, str) and validate_changed_path(path) is None
    }
    listed_frozen_paths = sorted(
        path for path in exact_coordination_paths
        if frozen_coordination_path(path, plan)
    )
    if listed_frozen_paths:
        raise ManifestError(
            "frozen product/design sources cannot be coordination paths: "
            + ", ".join(listed_frozen_paths)
        )
    unsupported_exact_paths = sorted(
        path for path in exact_coordination_paths
        if not supported_coordination_path(path)
    )
    if unsupported_exact_paths:
        raise ManifestError(
            "RUN declares unsupported product-path coordination entries: "
            + ", ".join(unsupported_exact_paths)
        )
    changes = _coordination_commit_changes(root, current_head, candidate_sha)
    if not changes:
        raise ManifestError("coordination checkpoint changes no declared files")
    deleted = sorted(path for status, path in changes if status.startswith("D"))
    if deleted:
        raise ManifestError(
            "coordination checkpoint must not delete files: " + ", ".join(deleted)
        )
    changed_paths = {path for _, path in changes}
    outside_coordination = sorted(changed_paths - exact_coordination_paths)
    if outside_coordination:
        raise ManifestError(
            "coordination checkpoint changed files outside exact declared paths: "
            + ", ".join(outside_coordination)
        )
    _require_regular_coordination_entries(
        root, current_head, candidate_sha, changed_paths
    )
    _require_generated_task_views(root, run, changed_paths)

    _require_candidate_revalidation_budget(plan, run)

    final_branch = _git_branch_name(root)
    final_head = _git_out(root, "rev-parse", "HEAD").strip()
    final_dirty = _git_status_excluding_run(root, getattr(args, "run", None), run).strip()
    if (
        _normalized_branch(final_branch) != expected_branch
        or final_head != candidate_sha
        or final_dirty
    ):
        raise ManifestError(
            "repository branch, HEAD, or product tree changed during coordination "
            "reconciliation; refresh observation and retry"
        )

    authorizations_before = copy.deepcopy(run.get("authorizations"))
    execution_authorization_before = (
        run.get("execution_authorized"),
        copy.deepcopy(run.get("execution_authorization_scope")),
        run.get("execution_authorization_source"),
    )
    prior_heads = integration.setdefault("prior_head_shas", [])
    if current_head not in prior_heads:
        prior_heads.append(current_head)
    _invalidate_stale_current_projections(plan, run, current_head, candidate_sha)
    integration["integration_head_sha"] = candidate_sha
    continuity = run.get("landing", {}).get("continuity")
    if isinstance(continuity, dict) and continuity.get("status") == "preserved":
        continuity["head_sha"] = candidate_sha
    if run.get("authorizations") != authorizations_before or (
        run.get("execution_authorized"),
        run.get("execution_authorization_scope"),
        run.get("execution_authorization_source"),
    ) != execution_authorization_before:
        raise ManifestError("coordination reconciliation must not change authorization")

    event_id = (
        f"COORDINATION-HEAD-{candidate_sha[:12]}-{len(run.get('attempt_log', [])) + 1}"
    )
    run.setdefault("attempt_log", []).append(
        {
            "attempt_id": event_id,
            "mission_id": None,
            "task_id": None,
            "lease_id": None,
            "kind": "coordination_head_reconciliation",
            "result": "recorded",
            "evidence": [
                f"source={args.source}",
                f"old_head_sha={current_head}",
                f"new_head_sha={candidate_sha}",
                "changed_paths=" + ",".join(sorted(changed_paths)),
                f"observed_at={observed.get('captured_at')}",
                "product_tree=unchanged outside declared coordination paths",
            ],
        }
    )


def _git_tree(repo_root: Path, sha: str) -> str:
    """Resolve a commit's tree SHA from live Git; the skip proof is real or absent."""

    try:
        reject_object_substitution(repo_root)
        result = run_git(repo_root, "rev-parse", f"{sha}^{{tree}}")
    except GitMetadataError as exc:
        raise ManifestError(str(exc)) from exc
    tree = result.stdout.strip()
    if result.returncode != 0 or not is_full_sha(tree):
        raise ManifestError(f"cannot resolve tree SHA for {sha!r} in {repo_root}")
    return tree


def _run_replace_commit_boundary(path: Path) -> None:
    """Deterministic race hook; production keeps this a no-op."""

    del path


def _replace_run_document(
    path: Path, run: dict[str, Any], expected_text: str | None = None, *, before_commit=None
) -> None:
    path = Path(path)
    _assert_non_reparse_path(path)
    text = path.read_text(encoding="utf-8")
    heading = "## Harness Run State"
    start = text.find(heading)
    fence_start = text.find("```json", start)
    body_start = text.find("\n", fence_start) + 1
    fence_end = text.find("\n```", body_start)
    if start < 0 or fence_start < 0 or body_start == 0 or fence_end < 0:
        raise ManifestError("RUN.md has no fenced Harness Run State JSON block")
    body = json.dumps({"harness_run": run}, indent=2, ensure_ascii=False)
    updated = text[:body_start] + body + text[fence_end:]
    _replace_document_text(
        path, updated, expected_text=text if expected_text is None else expected_text,
        before_commit=before_commit,
    )


def _replace_document_text(
    path: Path, updated: str, *, expected_text: str, before_commit=None
) -> None:
    """Preserve the actual displaced RUN/tasks bytes at the native boundary."""
    from document_write import replace_existing_bytes

    path = Path(path)
    _assert_non_reparse_path(path)
    original = path.read_bytes()
    # Text readers normalize newlines; protect the corresponding raw snapshot.
    observed = original.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    if observed != expected_text:
        raise ManifestError("RUN.md changed during this transition; re-load the manifest and retry")

    def commit_guard(temporary):
        _run_replace_commit_boundary(path)
        if before_commit is not None:
            before_commit(temporary)

    try:
        replace_existing_bytes(path, updated.encode("utf-8"), original, before_commit=commit_guard)
    except OSError as error:
        raise ManifestError(f"RUN.md changed or could not commit: {error}") from error


def _is_reparse(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        return bool(getattr(path.stat(), "st_file_attributes", 0) & 0x0400)
    except OSError as exc:
        raise ManifestError(f"cannot inspect transition path {path}: {exc}") from exc


def _assert_non_reparse_path(path: Path) -> None:
    current = Path(path)
    while True:
        if current.exists() and _is_reparse(current):
            raise ManifestError(f"transition path contains a symlink or reparse point: {current}")
        parent = current.parent
        if parent == current:
            return
        current = parent


def _write_text_exclusive(path: Path, text: str) -> None:
    """Create one derived output without overwriting a raced user file."""

    created = False
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            created = True
            handle.write(text)
    except FileExistsError as exc:
        raise ManifestError(f"refusing to overwrite {path}") from exc
    except OSError:
        if created:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise


def _ensure_plan_unchanged(path: Path, expected_text: str | None) -> None:
    if expected_text is not None and path.read_text(encoding="utf-8") != expected_text:
        raise ManifestError(
            "PLAN.md changed during this transition; re-load the manifest and retry"
        )


def _control(run: dict[str, Any], state: str, source: str) -> None:
    if state == "running" and any(
        isinstance(worker, dict) and worker.get("phase") in {"leased", "worker_running"}
        for worker in [*run.get("workers", []), *run.get("review_workers", [])]
    ):
        raise ManifestError(
            "cannot resume while a worker or review worker is still recorded active; reconcile it or refresh live worker evidence first"
        )
    timestamp = _now()
    run["control"] = {
        "desired_state": state,
        "requested_at": timestamp,
        "source": source,
        "acknowledged_at": timestamp,
    }


def _reconcile_interrupted(run: dict[str, Any], args: argparse.Namespace) -> None:
    worker = next(
        (
            item
            for item in run.get("workers", [])
            if isinstance(item, dict) and item.get("worker_id") == args.worker_id
        ),
        None,
    )
    if worker is None:
        raise ManifestError(f"unknown worker {args.worker_id!r}")
    if worker.get("phase") not in {"leased", "worker_running"}:
        raise ManifestError("worker is not active; no interrupted transition is needed")
    worker["phase"] = "blocked"
    mission_id = worker.get("mission_id")
    mission_state = run.get("mission_states", {}).get(mission_id)
    if isinstance(mission_state, dict):
        mission_state["phase"] = "blocked"
        mission_state["blockers"] = sorted(
            set([*mission_state.get("blockers", []), args.reason])
        )
    for state in run.get("graph_state", {}).get("node_states", {}).values():
        if isinstance(state, dict) and state.get("bound_worker_id") == args.worker_id:
            state["phase"] = "blocked"
            state["last_outcome"] = "blocked"
            state["blockers"] = sorted(set([*state.get("blockers", []), args.reason]))
            break
    run["attempt_log"].append(
        {
            "attempt_id": f"INTERRUPTED-{args.worker_id}-{len(run['attempt_log']) + 1}",
            "mission_id": mission_id,
            "task_id": None,
            "lease_id": worker.get("lease_id"),
            "kind": "interrupted_worker_reconciliation",
            "result": "blocked",
            "evidence": [args.reason, "working tree and local evidence were preserved"],
            "review_lineage_id": None,
            "failure_family_ids": [],
        }
    )




def _reset_edge_state(state: dict[str, Any]) -> None:
    state.update(
        {
            "status": "dormant",
            "traversals": 0,
            "source_attempt_id": None,
        }
    )


def _reconcile_interrupted_reviews(
    plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace
) -> None:
    worker_ids = args.worker_id
    if len(worker_ids) != len(set(worker_ids)):
        raise ManifestError("--worker-id values must be unique")

    plan_nodes = {
        node.get("id"): node
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict)
    }
    graph_state = run.get("graph_state", {})
    node_states = graph_state.get("node_states", {})
    edge_states = graph_state.get("edge_states", {})
    plan_edges = {
        edge.get("id"): edge
        for edge in plan.get("graph", {}).get("edges", [])
        if isinstance(edge, dict)
    }
    retained_attempt_ids = {
        attempt.get("attempt_id")
        for attempt in run.get("attempt_log", [])
        if isinstance(attempt, dict) and isinstance(attempt.get("attempt_id"), str)
    }

    for worker_id in worker_ids:
        worker = next(
            (
                item
                for item in run.get("review_workers", [])
                if isinstance(item, dict) and item.get("worker_id") == worker_id
            ),
            None,
        )
        if worker is None:
            raise ManifestError(f"unknown review worker {worker_id!r}")
        if worker.get("phase") not in {"leased", "worker_running"}:
            raise ManifestError(
                f"review worker {worker_id!r} is not active; no interrupted transition is needed"
            )

        node_id = worker.get("node_id")
        node = plan_nodes.get(node_id)
        review = node.get("review") if isinstance(node, dict) else None
        if not isinstance(review, dict):
            raise ManifestError(
                f"review worker {worker_id!r} does not reference a PLAN review node"
            )
        lineage_id = review.get("lineage_id")
        attempt_id = worker.get("attempt_id")
        if not isinstance(attempt_id, str) or not attempt_id:
            raise ManifestError(f"review worker {worker_id!r} has no attempt ID")
        if any(
            isinstance(item, dict) and item.get("attempt_id") == attempt_id
            for item in run.get("attempt_log", [])
        ):
            raise ManifestError(f"duplicate attempt ID {attempt_id!r}")

        worker["phase"] = "blocked"
        worker["outcome"] = "blocked"
        worker["findings"] = sorted(
            set([*worker.get("findings", []), args.reason])
        )
        run["attempt_log"].append(
            {
                "attempt_id": attempt_id,
                "mission_id": None,
                "task_id": None,
                "lease_id": None,
                "kind": "review",
                "result": "blocked",
                "evidence": [
                    args.reason,
                    INTERRUPTED_REVIEW_RECEIPT,
                    "partial review output was not accepted; local evidence was preserved",
                ],
                "review_lineage_id": lineage_id,
                "failure_family_ids": [],
            }
        )

        state = node_states.get(node_id)
        if not isinstance(state, dict):
            raise ManifestError(f"review node {node_id!r} has no graph state")
        if (
            state.get("bound_worker_id") != worker_id
            or state.get("last_attempt_id") != attempt_id
        ):
            raise ManifestError(
                f"review worker {worker_id!r} does not match the current graph binding"
            )
        state.update(
            {
                "phase": "dormant",
                "attempts": min(
                    node.get("max_attempts", 0), max(1, state.get("attempts", 0))
                ),
                "last_attempt_id": None,
                "last_outcome": None,
                "bound_worker_id": None,
                "blockers": [],
            }
        )

        for edge_id, edge in plan_edges.items():
            edge_state = edge_states.get(edge_id)
            if not isinstance(edge_state, dict):
                continue
            if edge.get("from") == node_id and edge_state.get(
                "source_attempt_id"
            ) == attempt_id:
                _reset_edge_state(edge_state)
                continue
            if edge.get("to") != node_id or edge_state.get("status") != "traversed":
                continue
            source_state = node_states.get(edge.get("from"))
            source_attempt_id = edge_state.get("source_attempt_id")
            if (
                not isinstance(source_state, dict)
                or (
                    source_state.get("last_attempt_id") != source_attempt_id
                    and source_attempt_id not in retained_attempt_ids
                )
            ):
                _reset_edge_state(edge_state)

    _control(run, "paused", args.source)

def _review_node(plan: dict[str, Any], node_id: str) -> dict[str, Any]:
    node = next(
        (
            item
            for item in plan.get("graph", {}).get("nodes", [])
            if isinstance(item, dict) and item.get("id") == node_id
        ),
        None,
    )
    if not isinstance(node, dict) or not isinstance(node.get("review"), dict):
        raise ManifestError(f"{node_id!r} is not a PLAN runtime review node")
    if node.get("kind") != "verifier" or node.get("executor") != "runtime_worker":
        raise ManifestError(f"{node_id!r} is not a PLAN runtime review node")
    return node

def _review_target(
    plan: dict[str, Any],
    run: dict[str, Any],
    node: dict[str, Any],
    repo_root: Path | None,
) -> tuple[str, str]:
    review = node["review"]
    mission_ids = review.get("mission_ids", [])
    stage = review.get("stage", "preintegration")
    if stage == "preintegration" and len(mission_ids) == 1:
        mission_id = mission_ids[0]
        mission_state = run.get("mission_states", {}).get(mission_id)
        if not isinstance(mission_state, dict):
            raise ManifestError(f"review mission {mission_id!r} has no RUN state")
        reviewed_sha = mission_state.get("head_sha")
        mission_worker = next(
            (
                worker
                for worker in run.get("workers", [])
                if isinstance(worker, dict)
                and worker.get("worker_id") == mission_state.get("worker_id")
                and worker.get("mission_id") == mission_id
            ),
            None,
        )
        review_path = (
            mission_worker.get("worktree_path")
            if isinstance(mission_worker, dict)
            else None
        )
    else:
        reviewed_sha = run.get("integration", {}).get("integration_head_sha")
        review_path = (
            str(repo_root.resolve())
            if repo_root is not None
            else run.get("observed", {}).get("git", {}).get("parent_worktree_path")
        )
    if not isinstance(reviewed_sha, str) or not reviewed_sha:
        raise ManifestError("review dispatch has no exact reviewed SHA")
    if not isinstance(review_path, str) or not review_path:
        raise ManifestError("review dispatch has no exact review path")
    return reviewed_sha, review_path

def _reserve_review_dispatch(
    plan: dict[str, Any],
    run: dict[str, Any],
    args: argparse.Namespace,
    *,
    repo_root: Path | None,
) -> dict[str, Any]:
    try:
        pre_errors = validate_current_plan_run(plan, run, repo_root=repo_root)
        if pre_errors:
            raise ManifestError(
                "reserve-review-dispatch requires a valid PLAN/RUN pair:"
                "\\n" + "\\n".join(f"- {item}" for item in pre_errors)
            )
        selection = select_ready_nodes(
            plan, run, repo_root=repo_root, manifest_already_validated=True,
        )
    except GraphSelectionError as exc:
        raise ManifestError(str(exc)) from exc
    directive = next(
        (
            item
            for item in selection["dispatchable_nodes"]
            if item.get("node_id") == args.node_id
        ),
        None,
    )
    if directive is None:
        reasons = next(
            (
                item.get("reason_codes", [])
                for item in selection["deferred_nodes"]
                if item.get("node_id") == args.node_id
            ),
            ["node_not_selected"],
        )
        raise ManifestError(
            f"review node {args.node_id!r} is not dispatchable: {', '.join(reasons)}"
        )
    node = _review_node(plan, args.node_id)
    _validate_security_integration_checkout(
        plan,
        run,
        node,
        repo_root,
        operation="reserve",
        run_path=getattr(args, "run", None),
    )
    if directive.get("launch_kind") == "run_parent":
        raise ManifestError("a managed review requires a fresh independent reviewer")
    if any(
        isinstance(worker, dict) and worker.get("worker_id") == args.worker_id
        for worker in [*run.get("workers", []), *run.get("review_workers", [])]
    ):
        raise ManifestError(f"duplicate worker ID {args.worker_id!r}")
    if any(
        isinstance(item, dict) and item.get("attempt_id") == args.attempt_id
        for item in [*run.get("attempt_log", []), *run.get("review_workers", [])]
    ):
        raise ManifestError(f"duplicate attempt ID {args.attempt_id!r}")
    reviewed_sha, review_path = _review_target(plan, run, node, repo_root)
    if node["review"].get("type") == "security":
        required_checks = (
            plan.get("security_review", {}).get("required_checks", [])
            if isinstance(plan.get("security_review"), dict)
            else []
        )
        executions = run.get("verifier_executions", [])
        for check_id in required_checks:
            matches = [
                execution
                for execution in executions
                if isinstance(execution, dict)
                and execution.get("verifier_id") == check_id
                and execution.get("layer") in {"batch", "final"}
                and execution.get("status") == "PASS"
                and execution.get("exit_code") == 0
                and isinstance(execution.get("context"), dict)
                and execution["context"].get("head_sha") == reviewed_sha
            ]
            if len(matches) != 1:
                raise ManifestError(
                    f"security review requires one current PASS execution for check {check_id!r} before reservation"
                )
    review_base_sha = run.get("integration", {}).get("batch_base_sha")
    if node["review"].get("type") == "security" and not is_full_sha(review_base_sha):
        raise ManifestError("security review dispatch requires a full batch_base_sha")
    report_path = args.report_path
    if directive["completion_channel"] == "report_file" and not report_path:
        raise ManifestError("--report-path is required for a report_file review")
    review_worker = {
        "worker_id": args.worker_id,
        "node_id": args.node_id,
        "attempt_id": args.attempt_id,
        "plan_revision": plan["revision"],
        "plan_digest_sha256": plan_digest(plan),
        "graph_revision": run["graph_state"]["graph_revision"],
        "reviewed_sha": reviewed_sha,
        "base_sha": review_base_sha,
        "review_path": review_path,
        "worker_runtime": directive["worker_runtime"],
        "completion_channel": directive["completion_channel"],
        "runtime_binding": copy.deepcopy(directive["runtime_binding"]),
        "workspace_mode": directive["workspace_mode"],
        "task_thread_id": None,
        "report_path": report_path,
        "phase": "leased",
        "outcome": None,
        "findings": [],
        "notes": [],
    }
    # Record the exact spawn receipt only after every guard has passed, as
    # _lease_worker does for mission workers.
    if directive["worker_runtime"] == "subagent":
        for mission_id in node["review"]["mission_ids"]:
            _materialize_authorized_target(
                run, "spawn_subagents", mission_id, f"worker:{args.worker_id}"
            )
        if directive.get("runtime_binding", {}).get("source") == "external_bridge":
            bridge_target = f"runtime:{directive['runtime_binding']['bridge_identity']}"
            for mission_id in node["review"]["mission_ids"]:
                _materialize_authorized_target(
                    run,
                    "invoke_external_runtime",
                    mission_id,
                    bridge_target,
                )
    run["review_workers"].append(review_worker)
    state = run["graph_state"]["node_states"][args.node_id]
    state.update(
        {
            "phase": "running",
            "attempts": min(
                node.get("max_attempts", 1), max(0, state.get("attempts", 0)) + 1
            ),
            "last_attempt_id": args.attempt_id,
            "last_outcome": None,
            "bound_worker_id": args.worker_id,
            "blockers": [],
        }
    )
    return {
        "dispatch_receipt": {
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
            "node_id": args.node_id,
            "worker_id": args.worker_id,
            "attempt_id": args.attempt_id,
            "reviewed_sha": reviewed_sha,
            "base_sha": review_base_sha,
            "review_path": review_path,
            "launch_kind": directive["launch_kind"],
            "required_actions": directive["required_actions"],
            "runtime_binding": directive["runtime_binding"],
            "tool_profile": directive["tool_profile"],
        }
    }

ENVIRONMENT_REFUND_CAP = 2

SCOPED_REPAIR_SECURITY_SCOPE = (
    "not_applicable (scoped repair outside trust boundaries)"
)


def _environment_refunds(run: dict[str, Any], lineage_id: Any) -> int:
    """Count retained environment refunds for one review lineage in this RUN."""
    return sum(
        1
        for attempt in run.get("attempt_log", [])
        if isinstance(attempt, dict)
        and attempt.get("kind") == "review"
        and attempt.get("blocker_class") == "environment"
        and attempt.get("review_lineage_id") == lineage_id
    )


def _record_review_attempt(
    plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    if any(
        isinstance(item, dict) and item.get("attempt_id") == args.attempt_id
        for item in run.get("attempt_log", [])
    ):
        raise ManifestError(f"duplicate attempt ID {args.attempt_id!r}")
    worker = next(
        (
            item
            for item in run.get("review_workers", [])
            if isinstance(item, dict)
            and item.get("worker_id") == args.worker_id
            and item.get("attempt_id") == args.attempt_id
        ),
        None,
    )
    if worker is None:
        raise ManifestError(
            "review result has no matching reserved dispatch receipt; reserve it before launch"
        )
    if worker.get("phase") not in {"leased", "worker_running"}:
        raise ManifestError("review dispatch is not active")
    scoped = bool(getattr(args, "scoped", False))
    repair_scope = (
        repair_scope_entry(run, worker.get("reviewed_sha")) if scoped else None
    )
    if scoped and repair_scope is None:
        raise ManifestError(
            "--scoped requires a recorded repair scope whose candidate_sha "
            "equals the reviewed head"
        )
    scoped_security_pass = (
        scoped
        and args.result == "pass"
        and repair_scope is not None
        and repair_scope.get("trust_boundary") is not True
    )
    node = _review_node(plan, worker.get("node_id"))
    if node["review"].get("lineage_id") != args.lineage:
        raise ManifestError("review result lineage does not match its reserved PLAN node")
    blocker_class = getattr(args, "blocker_class", "review")
    if blocker_class != "review" and args.result != "blocked":
        raise ManifestError("--blocker-class applies only to a blocked review result")
    environment_block = args.result == "blocked" and blocker_class == "environment"
    # An environment block records that this reviewer could not inspect the
    # candidate at all, so the live-checkout guard must not strand the attempt;
    # the refunded budget re-enters only through a full fresh reservation.
    if not environment_block:
        _validate_security_integration_checkout(
            plan,
            run,
            node,
            getattr(args, "repo_root", None),
            operation="record",
            run_path=getattr(args, "run", None),
        )
    if args.result not in node.get("allowed_outcomes", []):
        raise ManifestError("review result is not declared by its reserved PLAN node")
    state = run.get("graph_state", {}).get("node_states", {}).get(node["id"])
    if not isinstance(state, dict) or (
        state.get("phase") != "running"
        or state.get("last_attempt_id") != args.attempt_id
        or state.get("bound_worker_id") != args.worker_id
    ):
        raise ManifestError("review result does not match the current reserved graph attempt")
    is_security_review = node["review"].get("type") == "security"
    security_result_path = getattr(args, "security_result", None)
    security_result: dict[str, Any] | None = None
    if is_security_review:
        if security_result_path is None:
            if not environment_block and not scoped_security_pass:
                raise ManifestError(
                    "security review completion requires --security-result"
                )
        else:
            current_head = run.get("integration", {}).get("integration_head_sha")
            if worker.get("reviewed_sha") != current_head:
                raise ManifestError(
                    "security review result is stale; reserved SHA is not the current integration head"
                )
            if worker.get("base_sha") != run.get("integration", {}).get("batch_base_sha"):
                raise ManifestError(
                    "security review result is stale; reserved base is not the current batch base"
                )
            try:
                security_result = load_security_review_result(security_result_path)
            except SecurityReviewResultError as exc:
                raise ManifestError(str(exc)) from exc
            combined_review = len(review_lenses(node["review"])) > 1
            security_errors = validate_security_review_result(
                security_result,
                expected_decision=security_result_decision(
                    node["review"], args.result, security_result
                ),
                expected_reviewed_sha=worker.get("reviewed_sha"),
                expected_base_sha=worker.get("base_sha"),
                expected_scope=node["review"].get("scope", []),
                required_tools=node["review"].get("required_tools", []),
                required_checks=(
                    plan.get("security_review", {}).get("required_checks", [])
                    if isinstance(plan.get("security_review"), dict)
                    else []
                ),
                allowed_decisions=node.get("allowed_outcomes", []),
            )
            if security_errors:
                raise ManifestError(
                    "invalid security review result:\n"
                    + "\n".join(f"- {item}" for item in security_errors)
                )
            if args.finding and not combined_review:
                raise ManifestError(
                    "security review findings come from --security-result, not --finding"
                )
            # A combined node adds its other lenses' findings with --finding.
            findings = [
                *security_result_finding_summaries(security_result),
                *(args.finding or []),
            ]
        if security_result is None:
            # An environment block means the reviewer never inspected the
            # candidate, so the blocker itself is the only finding source.
            findings = args.finding or []
    else:
        if security_result_path is not None:
            raise ManifestError(
                "--security-result applies only to a security review node"
            )
        findings = args.finding or []
    if args.result == "pass" and findings:
        raise ManifestError("a PASS review cannot contain findings")
    if args.result == "pass" and ui_acceptance_review(node["review"]) and not ui_acceptance_evidence_present(args.evidence):
        raise ManifestError("UI acceptance PASS requires ui_parity: and ui_page_quality: evidence anchors")
    if args.result != "pass" and not findings:
        raise ManifestError("a non-pass review requires at least one --finding")
    notes = list(getattr(args, "note", None) or [])
    mission_ids = node["review"].get("mission_ids", [])
    mission_id = mission_ids[0] if len(mission_ids) == 1 else None
    if args.mission_id is not None and args.mission_id not in mission_ids:
        raise ManifestError("--mission-id is not covered by the reserved review node")
    attempt_evidence = list(args.evidence)
    if security_result is not None:
        attempt_evidence.append(
            "security_result_sha256:" + _json_sha256(security_result)
        )
    refund = environment_block and (
        _environment_refunds(run, node["review"].get("lineage_id"))
        < ENVIRONMENT_REFUND_CAP
    )
    attempt_entry = {
        "attempt_id": args.attempt_id,
        "mission_id": args.mission_id or mission_id,
        "task_id": None,
        "lease_id": None,
        "kind": "review",
        "result": args.result,
        "evidence": attempt_evidence,
        "review_lineage_id": args.lineage,
        "notes": notes,
    }
    if args.result == "blocked":
        attempt_entry["blocker_class"] = blocker_class
    if scoped:
        attempt_entry["scoped"] = True
        attempt_entry["repair_paths"] = list(repair_scope["repair_paths"])
    run["attempt_log"].append(attempt_entry)
    worker.update(
        {
            "phase": {
                "pass": "worker_passed",
                "blocked": "blocked",
            }.get(args.result, "worker_failed"),
            "outcome": args.result,
            "findings": findings,
            "notes": notes,
        }
    )
    if security_result is not None:
        worker["security_result"] = security_result
    if scoped:
        worker["scoped"] = True
        worker["repair_paths"] = list(repair_scope["repair_paths"])
    if scoped_security_pass:
        worker["security_scope"] = SCOPED_REPAIR_SECURITY_SCOPE
    if args.result == "pass":
        tree_sha = getattr(args, "tree_sha", None)
        if tree_sha is None and getattr(args, "repo_root", None) is not None:
            reviewed = worker.get("reviewed_sha")
            if is_full_sha(reviewed):
                tree_sha = _git_tree(args.repo_root, reviewed)
        if is_full_sha(tree_sha):
            worker["tree_sha"] = tree_sha
    # Every scoped PASS refunds the attempt: it accepts only the repair
    # diff, so a trust-boundary security result rides along without
    # consuming the full-scope review budget.
    scoped_budget_refund = scoped and args.result == "pass"
    if refund:
        # The reviewer could not inspect the candidate, so the node budget is
        # refunded and the selector mints a fresh attempt; the retained
        # attempt entry stays append-only evidence of the environment failure.
        state.update(
            {
                "phase": "dormant",
                "attempts": max(0, state.get("attempts", 0) - 1),
                "last_attempt_id": None,
                "last_outcome": None,
                "bound_worker_id": None,
                "blockers": [],
            }
        )
    else:
        if scoped_budget_refund:
            # A scoped PASS accepts the repair diff only, so the candidate keeps
            # its full-scope coverage from the prior non-scoped PASS. The node
            # succeeds on this attempt without consuming the review budget; the
            # retained attempt entry stays as the scoped acceptance evidence.
            state.update(
                {
                    "phase": "succeeded",
                    "attempts": max(0, state.get("attempts", 0) - 1),
                    "last_outcome": args.result,
                    "blockers": [],
                }
            )
        else:
            state.update(
                {
                    "phase": {
                        "pass": "succeeded",
                        "blocked": "blocked",
                    }.get(args.result, "failed"),
                    "last_outcome": args.result,
                    "blockers": findings if args.result == "blocked" else [],
                }
            )
        for edge in plan.get("graph", {}).get("edges", []):
            if (
                not isinstance(edge, dict)
                or edge.get("from") != node["id"]
                or edge.get("kind") != "route"
                or args.result not in edge.get("on_outcomes", [])
            ):
                continue
            edge_state = run["graph_state"]["edge_states"][edge["id"]]
            traversals = edge_state.get("traversals", 0)
            bound = edge.get("max_traversals")
            if isinstance(bound, int) and traversals >= bound:
                edge_state["status"] = "exhausted"
            else:
                edge_state["status"] = "traversed"
                edge_state["traversals"] = traversals + 1
            edge_state["source_attempt_id"] = args.attempt_id
    receipt = {
        "node_id": node["id"],
        "worker_id": args.worker_id,
        "attempt_id": args.attempt_id,
        "result": args.result,
        "blocker_class": blocker_class if args.result == "blocked" else None,
        "refunded": bool(refund or scoped_budget_refund),
    }
    if scoped:
        receipt["scoped"] = True
    if environment_block and not refund:
        receipt["message"] = "environment refund cap reached"
    return receipt

def _skip_integration_review(
    plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace
) -> None:
    node = _review_node(plan, args.node_id)
    if node["review"].get("stage", "preintegration") != "integration":
        raise ManifestError("skip-integration-review applies only to integration-stage review nodes")
    if node["review"].get("type") == "security":
        raise ManifestError(
            "security integration review must run fresh on the unified candidate"
        )
    state = run["graph_state"]["node_states"].get(args.node_id)
    if not isinstance(state, dict):
        raise ManifestError(f"no graph state for node {args.node_id!r}")
    if state.get("phase") not in {"dormant", "ready"}:
        raise ManifestError("integration review is not skippable in its current phase")
    integration = run.get("integration")
    head = integration.get("integration_head_sha") if isinstance(integration, dict) else None
    if not is_full_sha(head):
        raise ManifestError("skip-integration-review requires a recorded integration_head_sha")
    if args.repo_root is None:
        raise ManifestError("skip-integration-review requires --repo-root")
    graph_nodes = {
        item.get("id"): item
        for item in plan.get("graph", {}).get("nodes", [])
        if isinstance(item, dict)
    }
    if getattr(args, "worker_id", None) is None:
        _record_reviewed_merge_chain(plan, run, node, graph_nodes, args.repo_root, head)
        _mark_integration_review_skipped(state)
        return
    worker = next(
        (
            item
            for item in run.get("review_workers", [])
            if isinstance(item, dict)
            and item.get("worker_id") == args.worker_id
            and item.get("phase") == "worker_passed"
            and item.get("outcome") == "pass"
            and (graph_nodes.get(item.get("node_id")) or {}).get("review", {}).get(
                "stage", "preintegration"
            )
            == "preintegration"
            and review_lenses(node["review"])
            <= review_lenses((graph_nodes.get(item.get("node_id")) or {}).get("review"))
            and review_covers_ui_acceptance(
                graph_nodes[item["node_id"]]["review"], node["review"], item, run
            )
        ),
        None,
    )
    if worker is None:
        raise ManifestError(
            "no passed pre-integration review of the same type with required acceptance coverage matches that worker"
        )
    reviewed = worker.get("reviewed_sha")
    if not is_full_sha(reviewed):
        raise ManifestError("the matched review worker has no concrete reviewed_sha")
    head_tree = _git_tree(args.repo_root, head)
    reviewed_tree = _git_tree(args.repo_root, reviewed)
    if head_tree != reviewed_tree:
        raise ManifestError(
            "integration head tree differs from the reviewed tree; the review must run"
        )
    integration["integration_tree_sha"] = head_tree
    worker.setdefault("tree_sha", reviewed_tree)
    _mark_integration_review_skipped(state)


def _mark_integration_review_skipped(state: dict[str, Any]) -> None:
    state.update(
        {
            "phase": "skipped",
            "attempts": 0,
            "last_attempt_id": None,
            "last_outcome": None,
            "bound_worker_id": None,
            "blockers": [],
        }
    )


def _record_reviewed_merge_chain(
    plan: dict[str, Any],
    run: dict[str, Any],
    node: dict[str, Any],
    graph_nodes: dict[str, Any],
    repo_root: Path,
    head: str,
) -> None:
    """Prove from live Git that the head only merges reviewed mission heads.

    Walk first parents from the head. Each link must be a clean automatic merge
    whose second parent is an exact passed single-mission review head, and that
    side may change only the mission's write scope. The walk ends at the first
    other commit; it must be a reviewed head itself or a base every reviewed
    head contains. Anything else leaves no proof, so the review runs.
    """

    if not merge_chain_skip_allowed(plan, node["review"]):
        raise ManifestError(
            "a merge-chain skip applies only to frontend_code and backend_code"
            " reviews of a per_mission PLAN"
        )
    reviewed: dict[str, str] = {}
    for worker in run.get("review_workers", []):
        if not isinstance(worker, dict):
            continue
        review = (graph_nodes.get(worker.get("node_id")) or {}).get("review") or {}
        missions = review.get("mission_ids")
        if (
            worker.get("phase") == "worker_passed"
            and worker.get("outcome") == "pass"
            and review.get("stage", "preintegration") == "preintegration"
            and isinstance(missions, list)
            and len(missions) == 1
            and is_full_sha(worker.get("reviewed_sha"))
        ):
            reviewed[worker["reviewed_sha"]] = missions[0]
    scopes = {
        mission.get("id"): mission.get("write_scope", [])
        for mission in plan.get("missions", [])
        if isinstance(mission, dict)
    }
    links: list[dict[str, str]] = []
    commit = head
    while True:
        parents = _git_out(repo_root, "rev-list", "--parents", "-n", "1", commit).split()[1:]
        mission_id = reviewed.get(parents[1]) if len(parents) == 2 else None
        if mission_id is None or any(link["mission_id"] == mission_id for link in links):
            break
        try:
            merged = run_git(repo_root, "merge-tree", "--write-tree", parents[0], parents[1])
        except GitMetadataError as exc:
            raise ManifestError(str(exc)) from exc
        merged_tree = merged.stdout.split()[:1]
        if merged.returncode != 0 or merged_tree != [_git_tree(repo_root, commit)]:
            raise ManifestError(
                f"merge {commit} is not a clean automatic merge; the review must run"
            )
        base = _git_out(repo_root, "merge-base", parents[0], parents[1]).strip()
        if not all(
            path_in_scopes(path, scopes.get(mission_id, []))
            for path in _candidate_changed_paths(repo_root, base, parents[1])
        ):
            raise ManifestError(
                f"mission {mission_id} changed paths outside its write scope; the review must run"
            )
        links.append({"mission_id": mission_id, "reviewed_sha": parents[1], "commit_sha": commit})
        commit = parents[0]
    root_mission = reviewed.get(commit)
    if root_mission is not None and all(link["mission_id"] != root_mission for link in links):
        links.append({"mission_id": root_mission, "reviewed_sha": commit, "commit_sha": commit})
    elif not all(_git_is_ancestor(repo_root, commit, link["reviewed_sha"]) for link in links):
        raise ManifestError(
            f"merge chain base {commit} is not in every reviewed head; the review must run"
        )
    proof = {"head_sha": head, "links": links}
    if not reviewed_merge_chain_covers(
        plan, node, {**run, "integration": {**run["integration"], "reviewed_merge_chain": proof}}, graph_nodes
    ):
        raise ManifestError(
            "the merge chain does not cover every reviewed mission with disjoint write scopes;"
            " the review must run"
        )
    run["integration"]["reviewed_merge_chain"] = proof


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for state in ("pause", "resume", "cancel"):
        command = subparsers.add_parser(state)
        command.add_argument("--source", required=True)
    reconcile = subparsers.add_parser("reconcile-interrupted")
    reconcile.add_argument("--worker-id", required=True)
    reconcile.add_argument("--reason", required=True)
    review_reconcile = subparsers.add_parser("reconcile-interrupted-reviews")
    review_reconcile.add_argument("--worker-id", action="append", required=True)
    review_reconcile.add_argument("--reason", required=True)
    review_reconcile.add_argument("--source", required=True)
    reserve_review = subparsers.add_parser("reserve-review-dispatch")
    reserve_review.add_argument("--node-id", required=True)
    reserve_review.add_argument("--worker-id", required=True)
    reserve_review.add_argument("--attempt-id", required=True)
    reserve_review.add_argument("--report-path")
    reserve_review.add_argument("--diff-artifact-out", type=Path)
    reserve_review.add_argument(
        "--packet-out",
        type=Path,
        help="also render the reviewer packet from the in-memory reserved run",
    )
    reserve_review.add_argument("--max-diff-bytes", type=int)
    reserve_review.add_argument("--max-message-bytes", type=int)
    review = subparsers.add_parser("record-review-attempt")
    review.add_argument("--lineage", required=True)
    review.add_argument("--attempt-id", required=True)
    review.add_argument("--worker-id", required=True)
    review.add_argument("--mission-id")
    review.add_argument("--result", required=True)
    review.add_argument("--evidence", action="append", required=True)
    review.add_argument("--finding", action="append")
    review.add_argument(
        "--note",
        action="append",
        help="repeatable non-blocking observation; never blocks the review",
    )
    review.add_argument(
        "--blocker-class",
        choices=("environment", "review"),
        default="review",
        help="why a blocked review failed; environment refunds the attempt",
    )
    review.add_argument(
        "--scoped",
        action="store_true",
        help="record a scoped repair review pass against the head's recorded "
        "repair scope; a scoped PASS refunds the attempt",
    )
    review.add_argument("--security-result", type=Path)
    review.add_argument("--tree-sha")
    skip = subparsers.add_parser("skip-integration-review")
    skip.add_argument("--node-id", required=True)
    skip.add_argument(
        "--worker-id",
        help="prove a byte-identical tree; omit to prove a reviewed merge chain",
    )
    for name in ("acquire-run-lock", "release-run-lock", "heartbeat-run-lock"):
        lock_command = subparsers.add_parser(name)
        lock_command.add_argument("--owner")
    observation_parser = subparsers.add_parser("record-observation")
    observation_parser.add_argument("--available-worker-slots", type=int)
    observation_parser.add_argument("--isolation-capacity", type=int)
    observation_parser.add_argument("--capacity-evidence")
    wave_command = subparsers.add_parser("accept-wave")
    wave_command.add_argument("--wave-id", required=True)
    wave_command.add_argument("--mission-id", action="append", required=True)
    wave_command.add_argument("--batch-base-sha", required=True)
    close_wave = subparsers.add_parser("close-wave")
    close_wave.add_argument("--source", required=True)
    lease = subparsers.add_parser("lease-worker")
    lease.add_argument("--mission-id", required=True)
    lease.add_argument("--node-id", required=True)
    lease.add_argument("--worker-id", required=True)
    lease.add_argument("--lease-id", required=True)
    lease.add_argument("--attempt-id", required=True)
    lease.add_argument("--branch-ref", required=True)
    lease.add_argument("--worktree-path", required=True)
    lease.add_argument("--provider")
    lease.add_argument("--driver")
    lease.add_argument("--model")
    lease.add_argument("--reasoning-effort")
    lease.add_argument("--worker-runtime")
    lease.add_argument("--workspace-mode")
    lease.add_argument("--completion-channel")
    lease.add_argument("--report-path")
    reserve_node = subparsers.add_parser("reserve-node-attempt")
    reserve_node.add_argument("--node-id", required=True)
    reserve_node.add_argument("--attempt-id", required=True)
    reserve_node.add_argument("--evidence", action="append", default=[])
    reserve_node.add_argument(
        "--request-out",
        type=Path,
        help="write the exact local-verifier request after RUN is updated",
    )
    record_node = subparsers.add_parser("record-node-result")
    record_node.add_argument("--node-id", required=True)
    record_node.add_argument("--attempt-id", required=True)
    record_node.add_argument("--outcome", required=True, choices=(
        "pass", "fix_required", "retryable_failure", "blocked", "contract_gap"
    ))
    record_node.add_argument("--evidence", action="append", default=[])
    record_node.add_argument("--blocker", action="append", default=[])
    record_node.add_argument("--verifier-result", action="append", type=Path, default=[])
    worker_result = subparsers.add_parser("record-worker-result")
    worker_result.add_argument("--node-result", required=True, type=Path)
    worker_result.add_argument("--worker-result", type=Path)
    worker_result.add_argument("--verifier-result", action="append", type=Path, default=[])
    rejected = subparsers.add_parser("reject-worker-result")
    rejected.add_argument("--node-id", required=True)
    rejected.add_argument("--worker-id", required=True)
    rejected.add_argument(
        "--outcome", choices=("retryable_failure", "blocked"), required=True
    )
    rejected.add_argument("--reason", action="append", required=True)
    integration = subparsers.add_parser("record-integration")
    integration.add_argument("--mission-id", required=True)
    integration.add_argument("--integrated-sha", required=True)
    integration.add_argument("--verifier-result", type=Path, action="append", default=[])
    candidate = subparsers.add_parser("reconcile-candidate-head")
    candidate.add_argument("--candidate-sha", required=True)
    candidate.add_argument("--source", required=True)
    candidate.add_argument("--repair-node-id", required=True)
    candidate.add_argument("--repair-attempt-id", required=True)
    candidate.add_argument("--repair-task-id", required=True)
    candidate.add_argument(
        "--repair-path",
        action="append",
        help="repeatable repo-relative path repaired by this candidate; the "
        "candidate diff must stay inside the declared repair paths",
    )
    candidate.add_argument(
        "--trust-boundary",
        action="store_true",
        help="the repair touches a trust boundary; a scoped security re-check "
        "keeps its full structured security result",
    )
    coordination = subparsers.add_parser("reconcile-coordination-head")
    coordination.add_argument("--candidate-sha", required=True)
    coordination.add_argument("--source", required=True)
    watchdog = subparsers.add_parser("watchdog")
    watchdog.add_argument("--stale-after-minutes", type=float, default=DEFAULT_LOCK_STALE_MINUTES)
    watchdog.add_argument("--reclaim", action="store_true")
    parser.add_argument("--session-id")
    return parser






def _transition_under_lock(
    args: argparse.Namespace,
    plan: dict[str, Any],
    *,
    expected_plan_text: str | None = None,
) -> tuple[dict[str, Any] | None, list[str] | None, bool]:
    diff_budget = getattr(args, "max_diff_bytes", None)
    message_budget = getattr(args, "max_message_bytes", None)
    if diff_budget is not None or message_budget is not None:
        if getattr(args, "packet_out", None) is None:
            raise ManifestError(
                "--max-diff-bytes and --max-message-bytes require --packet-out; "
                "the budgets must validate the complete packet before durable writes"
            )
        if args.command != "reserve-review-dispatch":
            raise ManifestError(
                "packet byte budgets are valid only with reserve-review-dispatch"
            )
    if getattr(args, "max_message_bytes", None) is not None:
        try:
            check_message("", args.max_message_bytes)
        except InvalidMessageBudgetError as exc:
            raise ManifestError(f"invalid packet message budget: {exc}") from exc
    if diff_budget is not None and diff_budget < 1:
        raise ManifestError("invalid packet diff budget: --max-diff-bytes must be positive")
    original_text = args.run.read_text(encoding="utf-8")
    original = extract_json_manifest_text(
        original_text,
        RUN_HEADING,
        "harness_run",
        source=args.run,
    )
    run = copy.deepcopy(original)
    receipt = None
    report: list[str] | None = None
    if args.command == "watchdog":
        report = _watchdog_report(run, args.stale_after_minutes)
        if args.reclaim:
            if not isinstance(run.get("run_lock"), dict):
                return receipt, report, False
            _ensure_run_lock_free(run, args.session_id, args.stale_after_minutes)
            run.pop("run_lock", None)
        else:
            return receipt, report, False
    else:
        # The lock commands carry their own holder rules (acquire is the
        # documented stale-takeover path); every other mutation refuses
        # any foreign lock outright.
        if args.command not in {
            "acquire-run-lock",
            "release-run-lock",
            "heartbeat-run-lock",
        }:
            _ensure_no_foreign_lock(run, getattr(args, "session_id", None))
        if args.command in DISPATCH_COMMANDS:
            _require_held_run_lock(run, args)
    if args.command in {"pause", "resume", "cancel"}:
        _control(
            run,
            {"pause": "paused", "resume": "running", "cancel": "cancelled"}[
                args.command
            ],
            args.source,
        )
    elif args.command == "reconcile-interrupted":
        _reconcile_interrupted(run, args)
    elif args.command == "reconcile-interrupted-reviews":
        _reconcile_interrupted_reviews(plan, run, args)
    elif args.command == "reserve-review-dispatch":
        if args.repo_root is None:
            raise ManifestError("reserve-review-dispatch requires --repo-root")
        receipt = _reserve_review_dispatch(plan, run, args, repo_root=args.repo_root)
    elif args.command == "skip-integration-review":
        _skip_integration_review(plan, run, args)
    elif args.command == "record-observation":
        _record_observation(plan, run, args)
    elif args.command == "accept-wave":
        _accept_wave(plan, run, args)
    elif args.command == "close-wave":
        _close_wave(run, args)
    elif args.command == "reserve-node-attempt":
        receipt = _reserve_node_attempt(plan, run, args)
    elif args.command == "record-node-result":
        receipt = _record_node_result(plan, run, args)
    elif args.command == "lease-worker":
        _lease_worker(plan, run, args)
    elif args.command == "record-worker-result":
        receipt = record_worker_result(plan, run, args)
    elif args.command == "reject-worker-result":
        receipt = reject_worker_result(plan, run, args)
    elif args.command == "record-integration":
        _record_integration(plan, run, args)
    elif args.command == "reconcile-candidate-head":
        receipt = _reconcile_candidate_head(plan, run, args)
    elif args.command == "reconcile-coordination-head":
        _reconcile_coordination_head(plan, run, args)
    elif args.command == "acquire-run-lock":
        _acquire_run_lock(run, args)
    elif args.command == "release-run-lock":
        _release_run_lock(run, args)
    elif args.command == "heartbeat-run-lock":
        _heartbeat_run_lock(run, args)
    elif args.command != "watchdog":
        receipt = _record_review_attempt(plan, run, args)
    # A session holding the durable lock keeps it fresh through its own
    # transitions, so a long integration does not age it out mid-flight.
    lock = run.get("run_lock")
    if (
        isinstance(lock, dict)
        and getattr(args, "session_id", None)
        and lock.get("session_id") == args.session_id
    ):
        lock["heartbeat_at"] = _now()
    errors = validate_current_plan_run(plan, run, repo_root=args.repo_root)
    if errors:
        raise ManifestError(
            "transition would create an invalid RUN:\n"
            + "\n".join(f"- {item}" for item in errors)
        )

    packet = None
    diff_artifacts = []
    if getattr(args, "diff_artifact_out", None) and not getattr(args, "packet_out", None):
        raise ManifestError("--diff-artifact-out requires --packet-out")
    if receipt is not None and getattr(args, "packet_out", None):
        from render_review_packet import render_packet

        if args.packet_out.exists():
            raise ManifestError(f"refusing to overwrite {args.packet_out}")
        if getattr(args, "diff_artifact_out", None) and args.diff_artifact_out.resolve() == args.packet_out.resolve():
            raise ManifestError("packet and full diff artifact require distinct output paths")
        packet = render_packet(plan, run, args.node_id, args.repo_root,
                               max_diff_bytes=diff_budget if diff_budget is not None else 50000,
                               max_message_bytes=message_budget,
                               diff_artifact_out=getattr(args, "diff_artifact_out", None),
                               artifacts=diff_artifacts)

    verifier_request = None
    request_out = getattr(args, "request_out", None)
    if request_out is not None:
        if not isinstance(receipt, dict):
            raise ManifestError(
                "--request-out is only valid when reserving a local verifier node"
            )
        if isinstance(receipt.get("verifier_request"), dict):
            request_document = receipt["verifier_request"]
        else:
            raise ManifestError(
                "--request-out is only valid when reserving a local verifier node"
            )
        repo_root = getattr(args, "repo_root", None)
        if repo_root is not None:
            try:
                request_out.resolve().relative_to(Path(repo_root).resolve())
            except ValueError:
                pass
            else:
                raise ManifestError(
                    "local verifier request files must live outside the reviewed checkout"
                )
        request_text = json.dumps(
            request_document,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
        ) + "\n"
        verifier_request = request_text

    observation = getattr(args, "worker_observation", None)
    if isinstance(observation, dict):
        verify_worker_observation(observation)
    before_commit = None
    if args.command == "record-integration":
        from harness_integration_results import verify_integration_observation

        verify_integration_observation(args)

        def recheck_integration(pending: Path) -> None:
            # Recheck at the exchange boundary; only this writer's temporary RUN is new.
            verify_integration_observation(args, pending)
            _ensure_plan_unchanged(args.plan, expected_plan_text)

        before_commit = recheck_integration
    _ensure_plan_unchanged(args.plan, expected_plan_text)
    _replace_run_document(args.run, run, expected_text=original_text, before_commit=before_commit)
    if packet is not None:
        from render_review_packet import write_diff_artifact

        try:
            for path, data in diff_artifacts:
                write_diff_artifact(path, data)
            _write_text_exclusive(args.packet_out, packet)
        except (ManifestError, OSError) as exc:
            raise ManifestError(
                f"{exc}; the RUN review reservation is durable. Re-render the packet"
                " for its fixed node and candidate to new output paths before launch"
            ) from exc
    if verifier_request is not None:
        try:
            _write_text_exclusive(request_out, verifier_request)
        except (ManifestError, OSError) as exc:
            raise ManifestError(
                f"{exc}; the RUN reservation is durable and its exact request remains "
                "under attempt_log[].verifier_dispatch.request"
            ) from exc
    return receipt, report, True


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with _run_transition_lock(args.run):
            plan_text = args.plan.read_text(encoding="utf-8")
            plan = load_plan(args.plan)
            receipt, report, updated = _transition_under_lock(
                args, plan, expected_plan_text=plan_text
            )
    except (ManifestError, OSError, ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if receipt is not None:
        print(json.dumps(receipt, indent=2))
    elif report is not None:
        for line in report:
            print(line)
    elif updated:
        print(f"updated {args.run} with {args.command}")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())

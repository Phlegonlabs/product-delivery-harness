#!/usr/bin/env python3
"""Apply guarded PLAN-v6/RUN-v11 state transitions.

This replaces ad-hoc JSON editing for durable control, owner review grants,
and interrupted-worker reconciliation. It validates the complete manifest pair
before atomically replacing RUN.md.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_core import is_full_sha, plan_digest
from harness_manifest import (
    ManifestError,
    load_plan,
    load_run,
    validate_current_plan_run,
)
from select_ready_nodes import GraphSelectionError, select_ready_nodes


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


DEFAULT_LOCK_STALE_MINUTES = 15


def _parse_ts(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


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
            "reconcile them with reconcile-interrupted / reconcile-interrupted-reviews after reclaiming the lock"
        )
    elif running:
        lines.append("running nodes (parent live): " + ", ".join(sorted(running)))
    return lines


def _git_out(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo_root, capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise ManifestError(f"git {' '.join(args)} failed in {repo_root}")
    return result.stdout


def _record_observation(run: dict[str, Any], args: argparse.Namespace) -> None:
    """Write exactly what the parent observes: live Git facts plus a timestamp.

    This replaces hand-transcribing `harness_step.py`'s printed snapshot into
    RUN.observed — the observation `_write_launch_reasons` requires before any
    write dispatch clears.
    """

    if args.repo_root is None:
        raise ManifestError("record-observation requires --repo-root")
    root = args.repo_root
    head = _git_out(root, "rev-parse", "HEAD").strip()
    branch = _git_out(root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    porcelain = _git_out(root, "status", "--porcelain")
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
    for entry in worktrees:
        path = entry.get("path")
        dirty = False
        if isinstance(path, str):
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            dirty = bool(status.stdout.strip())
        entry.setdefault("head_sha", None)
        entry.setdefault("branch_ref", None)
        entry["managed_by"] = "parent"
        entry["dirty"] = dirty

    run["observed"]["captured_at"] = _now()
    run["observed"]["git"].update(
        {
            "parent_worktree_path": str(root.resolve()),
            "parent_branch": branch,
            "parent_head_sha": head,
            "parent_dirty": bool(porcelain.strip()),
            "worktrees": worktrees,
        }
    )


def _accept_wave(plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace) -> None:
    wave = run.get("active_wave")
    if not isinstance(wave, dict):
        raise ManifestError("run has no active_wave object")
    if wave.get("status") == "active" and wave.get("wave_id") != args.wave_id:
        raise ManifestError(
            f"wave {wave.get('wave_id')!r} is still active; close it before accepting another"
        )
    if not is_full_sha(args.batch_base_sha):
        raise ManifestError("accept-wave requires a full batch base SHA")
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
    run["integration"]["batch_base_sha"] = args.batch_base_sha
    wave.update(
        {
            "wave_id": args.wave_id,
            "status": "active",
            "plan_revision": plan.get("revision"),
            "plan_digest_sha256": (run.get("plan") or {}).get("digest_sha256"),
            "batch_base_sha": args.batch_base_sha,
            "selected_missions": list(args.mission_id),
            "deferred_missions": [],
            "conflict_edges": [],
        }
    )


def _lease_worker(plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace) -> None:
    wave = run.get("active_wave")
    if not isinstance(wave, dict) or wave.get("status") != "active":
        raise ManifestError("lease-worker requires an accepted active wave")
    if args.mission_id not in wave.get("selected_missions", []):
        raise ManifestError("lease-worker mission is not in the active wave")
    if any(
        isinstance(item, dict) and item.get("worker_id") == args.worker_id
        for item in run.get("workers", [])
    ):
        raise ManifestError(f"worker id {args.worker_id!r} already exists")
    if any(
        isinstance(item, dict) and item.get("attempt_id") == args.attempt_id
        for item in run.get("attempt_log", [])
    ):
        raise ManifestError(f"duplicate attempt ID {args.attempt_id!r}")
    node_states = run.get("graph_state", {}).get("node_states", {})
    node_state = node_states.get(args.node_id)
    if not isinstance(node_state, dict):
        raise ManifestError(f"no graph state for node {args.node_id!r}")
    mission_state = run.get("mission_states", {}).get(args.mission_id)
    if not isinstance(mission_state, dict):
        raise ManifestError(f"no mission state for {args.mission_id!r}")
    if mission_state.get("phase") not in {"queued", "ready", "failed"}:
        raise ManifestError(
            f"mission {args.mission_id!r} is {mission_state.get('phase')!r}; "
            "only queued, ready, or failed missions accept a new lease"
        )
    base_sha = wave.get("batch_base_sha")
    digest = (run.get("plan") or {}).get("digest_sha256")
    task_id = next(
        (
            tid
            for tid, state in run.get("task_states", {}).items()
            if tid.startswith(f"{args.mission_id}-")
            or tid in {
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
    node_state.update(
        {
            "phase": "running",
            "attempts": int(node_state.get("attempts") or 0) + 1,
            "last_attempt_id": args.attempt_id,
            "bound_worker_id": args.worker_id,
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
            "worker_runtime": args.worker_runtime,
            "workspace_mode": args.workspace_mode,
            "completion_channel": args.completion_channel,
            "runtime_binding": {
                "provider": args.provider,
                "driver": args.driver,
                "source": "host",
                "model": None,
                "reasoning_effort": None,
                "option_source": "provider_default",
            },
            "task_thread_id": None,
            "worktree_path": args.worktree_path,
            "branch_ref": args.branch_ref,
            "report_path": None,
            "phase": "worker_running",
            "worker_head_sha": None,
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
    if args.repo_root is not None:
        live_head = _git_out(args.repo_root, "rev-parse", "HEAD").strip()
        if live_head != args.integrated_sha:
            raise ManifestError(
                f"integration branch HEAD is {live_head}, not {args.integrated_sha}; "
                "integrate first, then record"
            )
    mission_state.update(
        {
            "phase": "integrated",
            "integration_gate": "PASS",
            "integrated_sha": args.integrated_sha,
        }
    )
    node_state = run.get("graph_state", {}).get("node_states", {}).get(f"N-{args.mission_id}")
    if isinstance(node_state, dict):
        node_state.update({"phase": "succeeded", "last_outcome": "pass"})
    run["integration"]["integration_head_sha"] = args.integrated_sha


def _git_tree(repo_root: Path, sha: str) -> str:
    """Resolve a commit's tree SHA from live Git; the skip proof is real or absent."""

    result = subprocess.run(
        ["git", "rev-parse", f"{sha}^{{tree}}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    tree = result.stdout.strip()
    if result.returncode != 0 or not is_full_sha(tree):
        raise ManifestError(f"cannot resolve tree SHA for {sha!r} in {repo_root}")
    return tree


def _replace_run_document(path: Path, run: dict[str, Any]) -> None:
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
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(updated)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


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


def _grant(run: dict[str, Any], args: argparse.Namespace) -> None:
    lineage = run.get("review_lineages", {}).get(args.lineage)
    if not isinstance(lineage, dict):
        raise ManifestError(f"unknown review lineage {args.lineage!r}")
    if args.additional_attempts != 1:
        raise ManifestError("one owner decision may grant exactly one additional review attempt")
    if lineage.get("owner_decisions"):
        raise ManifestError("this review lineage already used its one owner-granted successor")
    current_allowance = lineage.get("base_allowance", 0) + lineage.get(
        "additional_allowance", 0
    )
    if lineage.get("consumed_attempts", 0) < current_allowance:
        raise ManifestError("review allowance is not exhausted; an owner grant is premature")
    if not args.source_ref.startswith("user_turn:") or not args.source_ref.removeprefix(
        "user_turn:"
    ).strip():
        raise ManifestError("--source-ref must identify the approving user turn as user_turn:<id>")
    if args.decision_id.casefold() not in args.source.casefold():
        raise ManifestError(
            "--source must be the exact user quote and name the approved decision ID"
        )
    failure_family = next(
        (
            family
            for family in lineage.get("failure_families", [])
            if isinstance(family, dict) and family.get("id") == args.failure_family_id
        ),
        None,
    )
    if failure_family is None:
        raise ManifestError(
            "--failure-family-id must identify a retained failure family in this lineage"
        )
    if failure_family.get("status") not in {"open", "repairing"}:
        raise ManifestError("the owner-granted failure family must still be open")
    decision_ids = {
        item.get("id")
        for item in lineage.get("owner_decisions", [])
        if isinstance(item, dict)
    }
    if args.decision_id in decision_ids:
        raise ManifestError(f"duplicate owner decision {args.decision_id!r}")
    lineage["additional_allowance"] += args.additional_attempts
    lineage["owner_decisions"].append(
        {
            "id": args.decision_id,
            "source": args.source,
            "source_ref": args.source_ref,
            "failure_family_id": args.failure_family_id,
            "strategy": args.strategy,
            "acceptance_matrix": args.acceptance,
            "additional_review_attempts": args.additional_attempts,
        }
    )
    failure_family["strategy"] = args.strategy
    failure_family["status"] = "repairing"


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


def _sync_review_lineage_counts(run: dict[str, Any]) -> None:
    counts = {
        lineage_id: 0
        for lineage_id, lineage in run.get("review_lineages", {}).items()
        if isinstance(lineage, dict)
    }
    for attempt in run.get("attempt_log", []):
        if isinstance(attempt, dict) and attempt.get("review_lineage_id") in counts:
            counts[attempt["review_lineage_id"]] += 1
    for lineage_id, count in counts.items():
        run["review_lineages"][lineage_id]["consumed_attempts"] = count


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
    _sync_review_lineage_counts(run)
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
        lineage = run.get("review_lineages", {}).get(lineage_id)
        if not isinstance(lineage, dict):
            raise ManifestError(f"unknown review lineage {lineage_id!r}")

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
                    "partial review output was not accepted; local evidence was preserved",
                ],
                "review_lineage_id": lineage_id,
                "failure_family_ids": [],
            }
        )
        lineage["consumed_attempts"] += 1

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
            plan, run, repo_root=repo_root, manifest_already_validated=True
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
        "review_path": review_path,
        "worker_runtime": directive["worker_runtime"],
        "completion_channel": directive["completion_channel"],
        "runtime_binding": copy.deepcopy(directive["runtime_binding"]),
        "task_thread_id": None,
        "report_path": report_path,
        "phase": "leased",
        "outcome": None,
        "findings": [],
    }
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
            "node_id": args.node_id,
            "worker_id": args.worker_id,
            "attempt_id": args.attempt_id,
            "reviewed_sha": reviewed_sha,
            "review_path": review_path,
            "launch_kind": directive["launch_kind"],
            "required_actions": directive["required_actions"],
            "runtime_binding": directive["runtime_binding"],
            "tool_profile": directive["tool_profile"],
        }
    }


def _record_review_attempt(
    plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace
) -> None:
    lineage = run.get("review_lineages", {}).get(args.lineage)
    if not isinstance(lineage, dict):
        raise ManifestError(f"unknown review lineage {args.lineage!r}")
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
    node = _review_node(plan, worker.get("node_id"))
    if node["review"].get("lineage_id") != args.lineage:
        raise ManifestError("review result lineage does not match its reserved PLAN node")
    if args.result not in node.get("allowed_outcomes", []):
        raise ManifestError("review result is not declared by its reserved PLAN node")
    state = run.get("graph_state", {}).get("node_states", {}).get(node["id"])
    if not isinstance(state, dict) or (
        state.get("phase") != "running"
        or state.get("last_attempt_id") != args.attempt_id
        or state.get("bound_worker_id") != args.worker_id
    ):
        raise ManifestError("review result does not match the current reserved graph attempt")
    findings = args.finding or []
    if args.result == "pass" and findings:
        raise ManifestError("a PASS review cannot contain findings")
    if args.result != "pass" and not findings:
        raise ManifestError("a non-pass review requires at least one --finding")
    allowance = lineage.get("base_allowance", 0) + lineage.get(
        "additional_allowance", 0
    )
    if lineage.get("consumed_attempts", 0) >= allowance:
        raise ManifestError("review lineage allowance was exhausted before completion")
    family_ids: list[str] = []
    if args.failure_family_id:
        family_ids.append(args.failure_family_id)
        existing = next(
            (
                item
                for item in lineage["failure_families"]
                if isinstance(item, dict) and item.get("id") == args.failure_family_id
            ),
            None,
        )
        if existing is None:
            if not all((args.failure_primitive, args.equivalence_class, args.strategy)):
                raise ManifestError(
                    "a new --failure-family-id requires --failure-primitive, --equivalence-class, and --strategy"
                )
            lineage["failure_families"].append(
                {
                    "id": args.failure_family_id,
                    "primitive": args.failure_primitive,
                    "equivalence_classes": args.equivalence_class,
                    "strategy": args.strategy,
                    "status": "open",
                }
            )
    if args.result == "fix_required" and not family_ids:
        raise ManifestError("fix_required review requires one --failure-family-id")
    mission_ids = node["review"].get("mission_ids", [])
    mission_id = mission_ids[0] if len(mission_ids) == 1 else None
    if args.mission_id is not None and args.mission_id not in mission_ids:
        raise ManifestError("--mission-id is not covered by the reserved review node")
    run["attempt_log"].append(
        {
            "attempt_id": args.attempt_id,
            "mission_id": args.mission_id or mission_id,
            "task_id": None,
            "lease_id": None,
            "kind": "review",
            "result": args.result,
            "evidence": args.evidence,
            "review_lineage_id": args.lineage,
            "failure_family_ids": family_ids,
        }
    )
    lineage["consumed_attempts"] += 1
    worker.update(
        {
            "phase": {
                "pass": "worker_passed",
                "blocked": "blocked",
            }.get(args.result, "worker_failed"),
            "outcome": args.result,
            "findings": findings,
        }
    )
    if args.result == "pass":
        tree_sha = getattr(args, "tree_sha", None)
        if tree_sha is None and getattr(args, "repo_root", None) is not None:
            reviewed = worker.get("reviewed_sha")
            if is_full_sha(reviewed):
                tree_sha = _git_tree(args.repo_root, reviewed)
        if is_full_sha(tree_sha):
            worker["tree_sha"] = tree_sha
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


def _skip_integration_review(
    plan: dict[str, Any], run: dict[str, Any], args: argparse.Namespace
) -> None:
    node = _review_node(plan, args.node_id)
    if node["review"].get("stage", "preintegration") != "integration":
        raise ManifestError("skip-integration-review applies only to integration-stage review nodes")
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
            and (graph_nodes.get(item.get("node_id")) or {}).get("review", {}).get("type")
            == node["review"].get("type")
        ),
        None,
    )
    if worker is None:
        raise ManifestError(
            "no passed pre-integration review of the same type matches that worker"
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for state in ("pause", "resume", "cancel"):
        command = subparsers.add_parser(state)
        command.add_argument("--source", required=True)
    grant = subparsers.add_parser("grant-review-attempts")
    grant.add_argument("--lineage", required=True)
    grant.add_argument("--decision-id", required=True)
    grant.add_argument("--source", required=True)
    grant.add_argument("--source-ref", required=True)
    grant.add_argument("--failure-family-id", required=True)
    grant.add_argument("--strategy", required=True)
    grant.add_argument("--acceptance", action="append", required=True)
    grant.add_argument("--additional-attempts", type=int, default=1)
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
    reserve_review.add_argument(
        "--packet-out",
        type=Path,
        help="also render the reviewer packet from the in-memory reserved run",
    )
    review = subparsers.add_parser("record-review-attempt")
    review.add_argument("--lineage", required=True)
    review.add_argument("--attempt-id", required=True)
    review.add_argument("--worker-id", required=True)
    review.add_argument("--mission-id")
    review.add_argument("--result", required=True)
    review.add_argument("--evidence", action="append", required=True)
    review.add_argument("--finding", action="append")
    review.add_argument("--failure-family-id")
    review.add_argument("--failure-primitive")
    review.add_argument("--equivalence-class", action="append")
    review.add_argument("--strategy")
    review.add_argument("--tree-sha")
    skip = subparsers.add_parser("skip-integration-review")
    skip.add_argument("--node-id", required=True)
    skip.add_argument("--worker-id", required=True)
    for name in ("acquire-run-lock", "release-run-lock", "heartbeat-run-lock"):
        lock_command = subparsers.add_parser(name)
        lock_command.add_argument("--owner")
    subparsers.add_parser("record-observation")
    wave_command = subparsers.add_parser("accept-wave")
    wave_command.add_argument("--wave-id", required=True)
    wave_command.add_argument("--mission-id", action="append", required=True)
    wave_command.add_argument("--batch-base-sha", required=True)
    lease = subparsers.add_parser("lease-worker")
    lease.add_argument("--mission-id", required=True)
    lease.add_argument("--node-id", required=True)
    lease.add_argument("--worker-id", required=True)
    lease.add_argument("--lease-id", required=True)
    lease.add_argument("--attempt-id", required=True)
    lease.add_argument("--branch-ref", required=True)
    lease.add_argument("--worktree-path", required=True)
    lease.add_argument("--provider", required=True)
    lease.add_argument("--driver", required=True)
    lease.add_argument("--worker-runtime", default="subagent")
    lease.add_argument("--workspace-mode", default="parent_managed_worktree")
    lease.add_argument("--completion-channel", default="agent_result")
    integration = subparsers.add_parser("record-integration")
    integration.add_argument("--mission-id", required=True)
    integration.add_argument("--integrated-sha", required=True)
    watchdog = subparsers.add_parser("watchdog")
    watchdog.add_argument("--stale-after-minutes", type=float, default=DEFAULT_LOCK_STALE_MINUTES)
    watchdog.add_argument("--reclaim", action="store_true")
    parser.add_argument("--session-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = load_plan(args.plan)
        original = load_run(args.run)
        run = copy.deepcopy(original)
        receipt = None
        report: list[str] | None = None
        if args.command == "watchdog":
            report = _watchdog_report(run, args.stale_after_minutes)
            if args.reclaim:
                if not isinstance(run.get("run_lock"), dict):
                    for line in report:
                        print(line)
                    return 0
                _ensure_run_lock_free(run, args.session_id, args.stale_after_minutes)
                run.pop("run_lock", None)
            else:
                for line in report:
                    print(line)
                return 0
        else:
            _ensure_run_lock_free(run, getattr(args, "session_id", None))
        if args.command in {"pause", "resume", "cancel"}:
            _control(run, {"pause": "paused", "resume": "running", "cancel": "cancelled"}[args.command], args.source)
        elif args.command == "grant-review-attempts":
            _grant(run, args)
        elif args.command == "reconcile-interrupted":
            _reconcile_interrupted(run, args)
        elif args.command == "reconcile-interrupted-reviews":
            _reconcile_interrupted_reviews(plan, run, args)
        elif args.command == "reserve-review-dispatch":
            if args.repo_root is None:
                raise ManifestError("reserve-review-dispatch requires --repo-root")
            receipt = _reserve_review_dispatch(
                plan, run, args, repo_root=args.repo_root
            )
            if getattr(args, "packet_out", None):
                from render_review_packet import render_packet

                if args.packet_out.exists():
                    raise ManifestError(f"refusing to overwrite {args.packet_out}")
                packet = render_packet(
                    plan, run, args.node_id, args.repo_root
                )
                args.packet_out.write_text(packet, encoding="utf-8", newline="\n")
        elif args.command == "skip-integration-review":
            _skip_integration_review(plan, run, args)
        elif args.command == "record-observation":
            _record_observation(run, args)
        elif args.command == "accept-wave":
            _accept_wave(plan, run, args)
        elif args.command == "lease-worker":
            _lease_worker(plan, run, args)
        elif args.command == "record-integration":
            _record_integration(plan, run, args)
        elif args.command == "acquire-run-lock":
            _acquire_run_lock(run, args)
        elif args.command == "release-run-lock":
            _release_run_lock(run, args)
        elif args.command == "heartbeat-run-lock":
            _heartbeat_run_lock(run, args)
        else:
            _record_review_attempt(plan, run, args)
        errors = validate_current_plan_run(plan, run, repo_root=args.repo_root)
        if errors:
            raise ManifestError("transition would create an invalid RUN:\n" + "\n".join(f"- {item}" for item in errors))
        _replace_run_document(args.run, run)
    except (ManifestError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if receipt is not None:
        print(json.dumps(receipt, indent=2))
    elif report is not None:
        for line in report:
            print(line)
    else:
        print(f"updated {args.run} with {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

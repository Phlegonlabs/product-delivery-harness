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
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_manifest import (
    ManifestError,
    load_plan,
    load_run,
    validate_current_plan_run,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
    if args.additional_attempts < 1:
        raise ManifestError("--additional-attempts must be positive")
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
            "strategy": args.strategy,
            "acceptance_matrix": args.acceptance,
            "additional_review_attempts": args.additional_attempts,
        }
    )


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


def _record_review_attempt(run: dict[str, Any], args: argparse.Namespace) -> None:
    lineage = run.get("review_lineages", {}).get(args.lineage)
    if not isinstance(lineage, dict):
        raise ManifestError(f"unknown review lineage {args.lineage!r}")
    if any(
        isinstance(item, dict) and item.get("attempt_id") == args.attempt_id
        for item in run.get("attempt_log", [])
    ):
        raise ManifestError(f"duplicate attempt ID {args.attempt_id!r}")
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
    run["attempt_log"].append(
        {
            "attempt_id": args.attempt_id,
            "mission_id": args.mission_id,
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
    review = subparsers.add_parser("record-review-attempt")
    review.add_argument("--lineage", required=True)
    review.add_argument("--attempt-id", required=True)
    review.add_argument("--mission-id")
    review.add_argument("--result", required=True)
    review.add_argument("--evidence", action="append", required=True)
    review.add_argument("--failure-family-id")
    review.add_argument("--failure-primitive")
    review.add_argument("--equivalence-class", action="append")
    review.add_argument("--strategy")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = load_plan(args.plan)
        original = load_run(args.run)
        run = copy.deepcopy(original)
        if args.command in {"pause", "resume", "cancel"}:
            _control(run, {"pause": "paused", "resume": "running", "cancel": "cancelled"}[args.command], args.source)
        elif args.command == "grant-review-attempts":
            _grant(run, args)
        elif args.command == "reconcile-interrupted":
            _reconcile_interrupted(run, args)
        elif args.command == "reconcile-interrupted-reviews":
            _reconcile_interrupted_reviews(plan, run, args)
        else:
            _record_review_attempt(run, args)
        errors = validate_current_plan_run(plan, run, repo_root=args.repo_root)
        if errors:
            raise ManifestError("transition would create an invalid RUN:\n" + "\n".join(f"- {item}" for item in errors))
        _replace_run_document(args.run, run)
    except (ManifestError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"updated {args.run} with {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Re-observe live facts and select the ready frontier in one read-only call.

Before using a selector proposal the parent has to re-observe a list of live
facts, then re-check authorization, then select. Nothing in the contract says
those are separate parent turns, but done one command at a time they became
three or more, once per wave and again after every terminal result. Most of the
list is derivable from PLAN, RUN, and Git, so this command derives it in one
pass and names what is left for the parent to observe itself.

Read-only by construction. It never writes PLAN, RUN, Git, or host state, and
it never records an accepted wave. Recording the batch base, minting worker,
branch, and worktree identities, and re-checking each exact target immediately
before its mutation all remain the parent's own actions: the parent stays the
sole writer.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from harness_manifest import ManifestError, load_plan, load_run, plan_digest
from select_ready_nodes import GraphSelectionError, select_ready_nodes

# Facts no manifest or repository read can supply. The parent observes these
# from its own host and compares them with what RUN records.
PARENT_OBSERVED_FACTS = (
    "available worker slots and isolation capacity",
    "observed provider and available runtime drivers",
    "permission mode/profile, worker inheritance, and required filesystem/network surfaces",
    "host and Harness versions for the runtime version gate",
)


def _git(repo_root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def observe(repo_root: Path, plan: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    """Derive every pre-launch fact that PLAN, RUN, and Git already know."""

    integration = run.get("integration", {}) or {}
    recorded_base = integration.get("batch_base_sha")
    branch_ref = integration.get("branch")

    head = _git(repo_root, "rev-parse", "HEAD")
    branch = _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    porcelain = _git(repo_root, "status", "--porcelain")
    worktrees_raw = _git(repo_root, "worktree", "list", "--porcelain")
    branches_raw = _git(repo_root, "for-each-ref", "--format=%(refname)", "refs/heads")

    worktrees = [
        line.split(" ", 1)[1]
        for line in (worktrees_raw or "").splitlines()
        if line.startswith("worktree ")
    ]
    branches = [line for line in (branches_raw or "").splitlines() if line]

    base_reachable = None
    if recorded_base:
        base_reachable = (
            _git(repo_root, "merge-base", "--is-ancestor", recorded_base, "HEAD") is not None
        )

    recorded_digest = (run.get("plan") or {}).get("digest_sha256")
    live_digest = plan_digest(plan)

    adapter = (run.get("runtime_capabilities") or {}).get("runtime_adapter") or {}

    return {
        "capability": {
            "detection_source": adapter.get("detection_source"),
            "available_drivers": adapter.get("available_drivers"),
            "configured_max_parallel_workers": (
                run.get("runtime_capabilities") or {}
            ).get("max_parallel_workers"),
            "observed_worker_slots": (
                (run.get("observed") or {}).get("runtime") or {}
            ).get("available_worker_slots"),
            "observed_isolation_capacity": (
                (run.get("observed") or {}).get("runtime") or {}
            ).get("isolation_capacity"),
        },
        "plan": {
            "recorded_revision": (run.get("plan") or {}).get("revision"),
            "live_revision": plan.get("revision"),
            "recorded_digest_sha256": recorded_digest,
            "live_digest_sha256": live_digest,
            "digest_matches": recorded_digest == live_digest,
        },
        "git": {
            "head_sha": head,
            "branch": branch,
            "dirty": None if porcelain is None else bool(porcelain),
            "dirty_paths": [] if not porcelain else porcelain.splitlines(),
            "worktrees": worktrees,
            "branches": branches,
        },
        "integration": {
            "recorded_branch_ref": branch_ref,
            "recorded_batch_base_sha": recorded_base,
            "batch_base_reachable_from_head": base_reachable,
        },
        "authorizations": {
            key: bool(entry.get("authorized"))
            for key, entry in sorted((run.get("authorizations") or {}).items())
            if isinstance(entry, dict)
        },
        "still_observe_yourself": list(PARENT_OBSERVED_FACTS),
    }


def blocking_notes(observed: dict[str, Any]) -> list[str]:
    """Facts that make a proposal stale. Advisory: the parent still decides."""

    notes: list[str] = []
    if not observed["plan"]["digest_matches"]:
        notes.append(
            "RUN records a plan digest that does not match PLAN; recompute the proposal"
        )
    if observed["plan"]["recorded_revision"] != observed["plan"]["live_revision"]:
        notes.append("RUN plan revision does not match PLAN revision")
    if observed["git"]["dirty"]:
        notes.append(
            "parent checkout is dirty; attribute every path before dispatching a writer"
        )
    capability = observed["capability"]
    if capability["detection_source"] == "fallback":
        notes.append(
            "runtime capability was never observed (detection_source: fallback);"
            " this run will execute one mission at a time regardless of how many"
            " are ready. Probe the host and record slots, isolation capacity, and"
            " available drivers before dispatch"
        )
    if not observed["integration"]["recorded_batch_base_sha"]:
        notes.append("integration.batch_base_sha is unset; record it before dispatch")
    elif observed["integration"]["batch_base_reachable_from_head"] is False:
        notes.append(
            "recorded batch_base_sha is not an ancestor of the current head; the base is stale"
        )
    return notes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument(
        "--observe-only",
        action="store_true",
        help="skip node selection and report only the live-fact re-observation",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = load_plan(args.plan)
        run = load_run(args.run)
    except (ManifestError, OSError) as exc:
        print(json.dumps({"status": "ERROR", "errors": [str(exc)]}, sort_keys=True, indent=2))
        return 2

    payload: dict[str, Any] = {"observed": observe(args.repo_root, plan, run)}
    payload["notes"] = blocking_notes(payload["observed"])

    if not args.observe_only:
        try:
            payload["selection"] = select_ready_nodes(plan, run, repo_root=args.repo_root)
        except GraphSelectionError as exc:
            payload["status"] = "ERROR"
            payload["errors"] = [str(exc)]
            print(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False))
            return 2

    payload["status"] = "OK"
    print(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

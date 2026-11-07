#!/usr/bin/env python3
"""Build a worker or task verifier request for verifier_runtime.py.

Read-only. Binds the request to the mission's live lease in the parent RUN:
run_id, PLAN revision and digest, graph_revision, batch_base_sha and lease_id.
A task verifier (`--task-id` with one `--commit` per task commit) uses
attempt `<lease attempt>-<task suffix>`, the union of its commits' files and
the last commit as head. A worker verifier (no `--task-id`) uses attempt
`<lease attempt>-W` and the files from batch_base_sha to HEAD. The changed
files come from the same Git observation the worker-result validator uses.
Host preflight and the Git guard are filled in. Live HEAD must equal the
request head on a clean worker checkout, so build each task's request right
after its commit, before the next task starts.

Writes only `--out`, which must sit outside the checkout. Exits 0 on success,
1 when the lease, PLAN or checkout refuses the request, 2 on bad arguments.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from harness_core import is_full_sha, plan_digest
from harness_git import GitMetadataError
from harness_manifest import ManifestError, _verifier_owners, load_plan, load_run
from harness_transition import _coordination_ignored_paths
from validate_worker_result import _observe_git_worker
from verifier_request_context import verifier_context
from verifier_runtime import observe_plan_host_runtimes


def build_request(
    plan: dict[str, Any], run: dict[str, Any], run_path: Path, repo_root: Path,
    mission_id: str, verifier_id: str, task_id: str | None, commits: list[str],
) -> dict[str, Any]:
    """Return the verifier request or raise ManifestError naming the refusal."""

    owner = _verifier_owners(plan).get(verifier_id)
    if owner is None or owner[1] != mission_id or owner[0] not in {"task", "worker"}:
        raise ManifestError(f"{verifier_id!r} is not a task or worker verifier of mission {mission_id!r} in PLAN")
    layer, _, owner_task, declaration = owner
    if layer == "task" and (task_id != owner_task or not commits):
        raise ManifestError(f"{verifier_id!r} is a verifier of task {owner_task!r}; pass --task-id {owner_task} and its --commit SHAs")
    if layer == "worker" and task_id is not None:
        raise ManifestError(f"{verifier_id!r} is a worker verifier; omit --task-id and --commit")

    state = run.get("mission_states", {}).get(mission_id)
    if not isinstance(state, dict) or state.get("phase") != "worker_running" or not state.get("lease_id"):
        raise ManifestError(f"mission {mission_id!r} has no live worker lease in RUN")
    lease_id = state["lease_id"]
    workers = [worker for worker in run.get("workers", [])
               if isinstance(worker, dict) and worker.get("mission_id") == mission_id
               and worker.get("lease_id") == lease_id]
    if len(workers) != 1:
        raise ManifestError(f"RUN needs exactly one worker record for lease {lease_id!r}")
    worker = workers[0]
    digest = plan_digest(plan)
    if (worker.get("plan_revision"), worker.get("plan_digest_sha256")) != (plan.get("revision"), digest):
        raise ManifestError("PLAN is not the revision the lease was granted on")
    lease_attempt = worker.get("attempt_id")
    if not isinstance(lease_attempt, str) or not lease_attempt:
        raise ManifestError(f"lease {lease_id!r} has no dispatch attempt_id")

    synthetic = {"mission_id": mission_id, "lease_id": lease_id,
                 "task_results": [{"task_id": task_id, "commits": commits}] if task_id else []}
    observed = _observe_git_worker(run, synthetic, repo_root)
    if observed["dirty"] is not False or observed["ancestry_confirmed"] is not True:
        raise ManifestError("the worker checkout must be clean and descend from batch_base_sha")
    if task_id is not None:
        outside = [commit for commit in commits if commit not in observed["commit_order"]]
        if outside:
            raise ManifestError(f"commits are not between batch_base_sha and HEAD: {', '.join(outside)}")
        if commits[-1] != observed["head_sha"]:
            raise ManifestError("live HEAD is not the last --commit; build the request right after the task's commit")
        changed_files = observed["task_changed_files"][task_id]
        attempt_id = f"{lease_attempt}-{task_id.rsplit('/', 1)[-1]}"
    else:
        changed_files = observed["changed_files"]
        attempt_id = f"{lease_attempt}-W"

    host_entries, host_errors = observe_plan_host_runtimes({"final_gates": [declaration]}, repo_root)
    if host_errors or len(host_entries) != 1:
        raise ManifestError("host preflight failed: " + ("; ".join(host_errors) or "the verifier must declare execution.isolation host"))
    head_sha = observed["head_sha"]
    return {
        "protocol": "harness-verifier-request-v1",
        "verifier": declaration,
        "checkout_root": str(repo_root),
        "context": verifier_context(
            layer=layer,
            run=run,
            plan_revision=plan.get("revision"),
            plan_digest_sha256=digest,
            batch_base_sha=worker.get("batch_base_sha"),
            head_sha=head_sha,
            changed_files=changed_files,
            checkout_role="worker",
            checkout_dirty=False,
            cache_safe=False,
            mission_id=mission_id,
            task_id=task_id,
            attempt_id=attempt_id,
            lease_id=lease_id,
        ),
        "git_guard": {
            "expected_branch": str(worker.get("branch_ref") or "").removeprefix("refs/heads/"),
            "expected_head_sha": head_sha,
            "ignored_paths": _coordination_ignored_paths(repo_root, run_path, run),
        },
        "host_preflight": host_entries[0],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plan", required=True, type=Path, help="Frozen PLAN.md")
    parser.add_argument("--run", required=True, type=Path, help="Parent RUN.md holding the live lease")
    parser.add_argument("--repo-root", required=True, type=Path, help="Worker checkout root")
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--verifier-id", required=True)
    parser.add_argument("--task-id", help="Task whose verifier runs; omit for a worker verifier")
    parser.add_argument("--commit", action="append", default=[], help="Task commit SHA (repeatable, in order)")
    parser.add_argument("--out", required=True, type=Path, help="Request file outside the checkout")
    args = parser.parse_args(argv)
    for flag, path in (("--plan", args.plan), ("--run", args.run)):
        if not path.is_file():
            parser.error(f"{flag} {path} is not an existing file")
    if not args.repo_root.is_dir():
        parser.error(f"--repo-root {args.repo_root} is not a directory")
    if args.commit and args.task_id is None:
        parser.error("--commit needs --task-id")
    if any(not is_full_sha(commit) for commit in args.commit):
        parser.error("--commit must be a full lowercase Git SHA")
    root = args.repo_root.resolve()
    out = args.out.resolve()
    if out == root or root in out.parents:
        parser.error("--out must be outside the checkout, or the Git guard sees it as a change")

    try:
        request = build_request(
            load_plan(args.plan), load_run(args.run), args.run, root,
            args.mission_id, args.verifier_id, args.task_id, args.commit,
        )
    except (GitMetadataError, ManifestError, OSError) as exc:
        print(f"refused: {exc}")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((json.dumps(request, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    context = request["context"]
    print(f"wrote {context['layer']} request for {args.verifier_id} at {context['head_sha']} "
          f"({len(context['changed_files'])} changed files) to {out}")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())

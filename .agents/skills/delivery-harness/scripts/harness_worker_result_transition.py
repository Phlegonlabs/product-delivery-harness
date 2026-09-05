#!/usr/bin/env python3
"""Validate and stage one terminal mission-worker result in RUN state."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from harness_core import ManifestError, _normalized_branch, is_full_sha
from harness_manifest import validate_current_plan_run
from validate_node_result import validate_node_result
from validate_worker_result import load_worker_result, validate_worker_result_data


def _load_json(path: Path, wrapper: str | None = None) -> Any:
    value = json.loads(path.read_text(encoding="utf-8"))
    if wrapper is not None and isinstance(value, dict) and set(value) == {wrapper}:
        return value[wrapper]
    return value


def _validation_failure(label: str, errors: list[Any]) -> ManifestError:
    rendered = _render_issues(errors)
    return ManifestError(label + ":\n" + "\n".join(f"- {item}" for item in rendered))


def _render_issues(errors: list[Any]) -> list[str]:
    rendered = []
    for error in errors:
        if isinstance(error, dict):
            code = error.get("code")
            prefix = f"{code}: " if isinstance(code, str) and code else ""
            rendered.append(
                f"{prefix}{error.get('path')}: {error.get('message')}"
            )
        else:
            rendered.append(str(error))
    return rendered


def _mission_node(plan: dict[str, Any], node_id: str) -> dict[str, Any]:
    matches = [
        node
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict)
        and node.get("id") == node_id
        and node.get("kind") == "mission"
    ]
    if len(matches) != 1:
        raise ManifestError(f"node {node_id!r} must identify one PLAN mission node")
    return matches[0]


def _bound_worker(
    run: dict[str, Any], mission_id: str, worker_id: str
) -> dict[str, Any]:
    matches = [
        worker
        for worker in run.get("workers", [])
        if isinstance(worker, dict)
        and worker.get("mission_id") == mission_id
        and worker.get("worker_id") == worker_id
    ]
    if len(matches) != 1:
        raise ManifestError(
            f"mission {mission_id!r} must have one bound worker {worker_id!r}"
        )
    return matches[0]


def _git(root: Path, *arguments: str, text: bool = True) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=text,
        timeout=30,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() if text else completed.stderr.decode(errors="replace").strip()
        raise ManifestError(
            f"git {' '.join(arguments)} failed in {root}: {stderr or 'unknown error'}"
        )
    return completed.stdout


def _same_path(left: Path, right: str) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(
        str(Path(right).resolve())
    )


def _git_common_dir(root: Path) -> Path:
    value = Path(str(_git(root, "rev-parse", "--git-common-dir")).strip())
    return (value if value.is_absolute() else root / value).resolve()


def _observe_bound_worker(
    plan: dict[str, Any],
    run: dict[str, Any],
    node_result: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    node = _mission_node(plan, node_result["node_id"])
    mission_id = node.get("ref")
    node_state = run.get("graph_state", {}).get("node_states", {}).get(node["id"])
    if not isinstance(node_state, dict):
        raise ManifestError(f"node {node['id']!r} has no RUN state")
    worker = _bound_worker(run, mission_id, node_state.get("bound_worker_id"))
    worktree_path = worker.get("worktree_path")
    if not isinstance(worktree_path, str) or not worktree_path:
        raise ManifestError("bound worker has no worktree_path to observe")
    worktree = Path(worktree_path)
    if not worktree.is_dir():
        raise ManifestError(f"bound worker worktree does not exist: {worktree}")
    if os.path.normcase(str(_git_common_dir(worktree))) != os.path.normcase(
        str(_git_common_dir(repo_root))
    ):
        raise ManifestError("bound worker worktree belongs to a different Git repository")

    live_head = str(_git(worktree, "rev-parse", "HEAD")).strip()
    if not is_full_sha(live_head):
        raise ManifestError(f"worker worktree returned an invalid HEAD: {live_head!r}")
    live_branch = str(_git(worktree, "branch", "--show-current")).strip()
    expected_branch = _normalized_branch(worker.get("branch_ref"))
    if not live_branch or _normalized_branch(live_branch) != expected_branch:
        raise ManifestError(
            f"bound worker worktree is on branch {live_branch!r}, not {worker.get('branch_ref')!r}"
        )
    base_sha = worker.get("batch_base_sha")
    if not is_full_sha(base_sha):
        raise ManifestError("bound worker has no valid batch_base_sha")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", str(base_sha), live_head],
        cwd=worktree,
        capture_output=True,
        text=True,
        timeout=30,
    ).returncode == 0
    raw_paths = _git(
        worktree,
        "diff",
        "--name-status",
        "--diff-filter=ACDMRTUXB",
        "-z",
        f"{base_sha}..{live_head}",
        text=False,
    )
    tokens = [token for token in raw_paths.split(b"\0") if token]
    changed_paths: set[str] = set()
    index = 0
    while index < len(tokens):
        status = tokens[index].decode("ascii", errors="replace")
        index += 1
        path_count = 2 if status[:1] in {"R", "C"} else 1
        if index + path_count > len(tokens):
            raise ManifestError("git diff returned a malformed name-status record")
        for token in tokens[index : index + path_count]:
            changed_paths.add(token.decode("utf-8").replace("\\", "/"))
        index += path_count
    changed_files = sorted(changed_paths)
    dirty = bool(str(_git(worktree, "status", "--porcelain=v1", "--untracked-files=all")).strip())
    managed_by = "app" if worker.get("workspace_mode") == "app_managed_worktree" else "parent"
    observed_git = run.setdefault("observed", {}).setdefault("git", {})
    worktrees = observed_git.setdefault("worktrees", [])
    if not isinstance(worktrees, list):
        raise ManifestError("run.observed.git.worktrees must be a list")
    worktrees[:] = [
        entry
        for entry in worktrees
        if not (
            isinstance(entry, dict)
            and isinstance(entry.get("path"), str)
            and _same_path(worktree, entry["path"])
        )
    ]
    worktrees.append(
        {
            "path": worker["worktree_path"],
            "branch_ref": worker["branch_ref"],
            "head_sha": live_head,
            "managed_by": managed_by,
            "dirty": dirty,
        }
    )
    return {
        "root": worktree.resolve(),
        "head_sha": live_head,
        "changed_files": changed_files,
        "ancestry_confirmed": ancestry,
        "dirty": dirty,
    }


def verify_worker_observation(observation: dict[str, Any]) -> None:
    """Refuse a RUN write when the observed worker checkout changed in flight."""

    root = observation["root"]
    live_head = str(_git(root, "rev-parse", "HEAD")).strip()
    dirty = bool(str(_git(root, "status", "--porcelain=v1", "--untracked-files=all")).strip())
    if live_head != observation["head_sha"] or dirty != observation["dirty"]:
        raise ManifestError(
            "worker worktree changed during result recording; re-observe and retry"
        )


def _extend_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if isinstance(value, str) and value and value not in target:
            target.append(value)


def _record_attempt_evidence(
    run: dict[str, Any],
    *,
    attempt_id: str,
    mission_id: str,
    task_id: str | None,
    lease_id: str,
    layer: str,
    execution_key: str,
) -> None:
    if any(
        isinstance(worker, dict) and worker.get("attempt_id") == attempt_id
        for worker in run.get("review_workers", [])
    ):
        raise ManifestError(
            f"attempt id {attempt_id!r} is reserved by a review worker"
        )
    matches = [
        attempt
        for attempt in run.get("attempt_log", [])
        if isinstance(attempt, dict) and attempt.get("attempt_id") == attempt_id
    ]
    if len(matches) > 1:
        raise ManifestError(f"attempt id {attempt_id!r} is ambiguous")
    if matches:
        attempt = matches[0]
        association = (
            attempt.get("mission_id"),
            attempt.get("task_id"),
            attempt.get("lease_id"),
        )
        if association != (mission_id, task_id, lease_id):
            raise ManifestError(
                f"attempt id {attempt_id!r} is already bound to another mission/task/lease"
            )
        evidence = attempt.setdefault("evidence", [])
        if not isinstance(evidence, list):
            raise ManifestError(f"attempt id {attempt_id!r} has malformed evidence")
        _extend_unique(evidence, [execution_key])
        return
    run["attempt_log"].append(
        {
            "attempt_id": attempt_id,
            "mission_id": mission_id,
            "task_id": task_id,
            "lease_id": lease_id,
            "kind": "task_verifier" if layer == "task" else "worker_verifier",
            "result": "PASS",
            "evidence": [execution_key],
        }
    )


def _execution_id(run: dict[str, Any], verifier_id: str, execution_key: str) -> str:
    existing = {
        item.get("execution_id")
        for item in run.get("verifier_executions", [])
        if isinstance(item, dict)
    }
    stem = f"EXEC-{verifier_id}-{execution_key[:16]}"
    candidate = stem
    suffix = 2
    while candidate in existing:
        candidate = f"{stem}-{suffix}"
        suffix += 1
    return candidate


def _retained_execution(
    run: dict[str, Any],
    retained: dict[str, Any],
    evidence_paths: list[str],
) -> dict[str, Any]:
    stdout = retained.get("stdout")
    stderr = retained.get("stderr")
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        raise ManifestError("retained verifier stdout and stderr must be strings")
    context = retained.get("context")
    if not isinstance(context, dict):
        raise ManifestError("retained verifier context must be an object")
    execution_key = retained.get("execution_key")
    verifier_id = retained.get("verifier_id")
    if not isinstance(execution_key, str) or not isinstance(verifier_id, str):
        raise ManifestError("retained verifier identity is incomplete")
    return {
        "execution_id": _execution_id(run, verifier_id, execution_key),
        "verifier_id": verifier_id,
        "layer": context.get("layer"),
        "mission_id": context.get("mission_id"),
        "task_id": context.get("task_id"),
        "attempt_id": context.get("attempt_id"),
        "lease_id": context.get("lease_id"),
        "protocol": retained.get("protocol"),
        "execution_key": execution_key,
        "evidence_key": retained.get("evidence_key"),
        "key_document": copy.deepcopy(retained.get("key_document")),
        "verifier": copy.deepcopy(retained.get("verifier")),
        "context": copy.deepcopy(context),
        "status": retained.get("status"),
        "exit_code": retained.get("exit_code"),
        "cache_status": retained.get("cache_status"),
        "cache_reason": retained.get("cache_reason"),
        "duration_ms": retained.get("duration_ms"),
        "metrics": copy.deepcopy(retained.get("metrics")),
        "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
        "evidence_paths": list(evidence_paths),
    }


def _record_passing_result(
    plan: dict[str, Any],
    run: dict[str, Any],
    node_result: dict[str, Any],
    worker_result: dict[str, Any],
    retained_results: list[dict[str, Any]],
    observation: dict[str, Any],
) -> None:
    reported_identities = {
        (item.get("id"), item.get("evidence"))
        for item in worker_result.get("verifiers", [])
        if isinstance(item, dict)
    }
    for retained in retained_results:
        if not isinstance(retained, dict):
            raise ManifestError("each retained verifier result must be an object")
        identity = (retained.get("verifier_id"), retained.get("execution_key"))
        if identity not in reported_identities:
            continue
        context = retained.get("context")
        if not isinstance(context, dict):
            raise ManifestError("retained verifier context must be an object")
        required_context = {
            "attempt_id": context.get("attempt_id"),
            "mission_id": context.get("mission_id"),
            "lease_id": context.get("lease_id"),
            "layer": context.get("layer"),
        }
        if not all(isinstance(value, str) and value for value in required_context.values()):
            raise ManifestError("retained verifier attempt binding is incomplete")
        if context.get("task_id") is not None and not isinstance(context.get("task_id"), str):
            raise ManifestError("retained verifier task binding must be null or a string")
        _record_attempt_evidence(
            run,
            attempt_id=context["attempt_id"],
            mission_id=context["mission_id"],
            task_id=context.get("task_id"),
            lease_id=context["lease_id"],
            layer=context["layer"],
            execution_key=retained["execution_key"],
        )

    issues = validate_worker_result_data(
        plan,
        run,
        worker_result,
        observed_head_sha=observation["head_sha"],
        observed_changed_files=observation["changed_files"],
        ancestry_confirmed=observation["ancestry_confirmed"],
        retained_verifier_results=retained_results,
        manifest_already_validated=True,
    )
    if issues:
        node = _mission_node(plan, node_result["node_id"])
        outcomes = set(node.get("allowed_outcomes", []))
        outcome = "retryable_failure" if "retryable_failure" in outcomes else "blocked"
        if outcome not in outcomes:
            raise _validation_failure("worker result does not validate", issues)
        rejected = copy.deepcopy(node_result)
        rejected.update(
            {
                "status": "failed" if outcome == "retryable_failure" else "blocked",
                "outcome": outcome,
                "worker_result": None,
                "refinement_request": None,
            }
        )
        _record_nonpassing_result(
            plan,
            run,
            rejected,
            blockers_override=_render_issues(issues),
            observed_head=observation["head_sha"],
        )
        return

    node = _mission_node(plan, node_result["node_id"])
    mission_id = node.get("ref")
    node_state = run["graph_state"]["node_states"][node["id"]]
    worker = _bound_worker(run, mission_id, node_state.get("bound_worker_id"))
    if worker.get("lease_id") != worker_result.get("lease_id"):
        raise ManifestError("worker result lease does not match the bound worker")

    retained_by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    for retained in retained_results:
        if not isinstance(retained, dict):
            raise ManifestError("each retained verifier result must be an object")
        identity = (retained.get("verifier_id"), retained.get("execution_key"))
        if not all(isinstance(item, str) and item for item in identity):
            raise ManifestError("retained verifier identity is incomplete")
        if identity in retained_by_identity:
            raise ManifestError(f"duplicate retained verifier result for {identity[0]!r}")
        retained_by_identity[identity] = retained

    task_results = {
        item["task_id"]: item
        for item in worker_result.get("task_results", [])
        if isinstance(item, dict) and isinstance(item.get("task_id"), str)
    }
    for reported in worker_result.get("verifiers", []):
        identity = (reported.get("id"), reported.get("evidence"))
        retained = retained_by_identity.get(identity)
        if retained is None:
            raise ManifestError(f"no exact retained verifier result for {identity[0]!r}")
        context = retained["context"]
        task_result = task_results.get(context.get("task_id"))
        evidence_paths = (
            task_result.get("evidence_paths", [])
            if isinstance(task_result, dict)
            else worker_result.get("evidence_paths", [])
        )
        record = _retained_execution(run, retained, evidence_paths)
        if any(
            isinstance(existing, dict)
            and existing.get("execution_key") == record["execution_key"]
            and existing.get("verifier_id") == record["verifier_id"]
            for existing in run.get("verifier_executions", [])
        ):
            raise ManifestError(
                f"verifier execution {record['verifier_id']!r} is already retained"
            )
        _record_attempt_evidence(
            run,
            attempt_id=context["attempt_id"],
            mission_id=context["mission_id"],
            task_id=context["task_id"],
            lease_id=context["lease_id"],
            layer=context["layer"],
            execution_key=record["execution_key"],
        )
        run["verifier_executions"].append(record)

    for task_id, task_result in task_results.items():
        state = run["task_states"].get(task_id)
        if not isinstance(state, dict):
            raise ManifestError(f"worker result references unknown task {task_id!r}")
        state.update(
            {
                "phase": "mission_recorded",
                "attempts": max(1, int(state.get("attempts") or 0)),
                "commit_sha": task_result["head_sha"],
                "verifier_status": "PASS",
                "blockers": [],
                "refinement_request": None,
            }
        )

    report_path = worker.get("report_path")
    worker.update(
        {
            "phase": "worker_passed",
            "worker_head_sha": worker_result["head_sha"],
        }
    )
    run["mission_states"][mission_id].update(
        {
            "phase": "worker_passed",
            "head_sha": worker_result["head_sha"],
            "report_path": report_path,
            "blockers": [],
        }
    )
    dispatch = next(
        (
            attempt
            for attempt in run.get("attempt_log", [])
            if isinstance(attempt, dict)
            and attempt.get("attempt_id") == node_result["attempt_id"]
        ),
        None,
    )
    if isinstance(dispatch, dict):
        dispatch["result"] = "worker_passed"
        evidence = dispatch.setdefault("evidence", [])
        _extend_unique(evidence, node_result.get("evidence_paths", []))
        _extend_unique(evidence, worker_result.get("evidence_paths", []))


def _record_nonpassing_result(
    plan: dict[str, Any],
    run: dict[str, Any],
    node_result: dict[str, Any],
    *,
    blockers_override: list[str] | None = None,
    observed_head: str | None = None,
) -> None:
    outcome = node_result.get("outcome")
    if outcome not in {"retryable_failure", "blocked", "contract_gap"}:
        raise ManifestError(f"unsupported mission worker outcome {outcome!r}")
    if node_result.get("worker_result") is not None:
        raise ManifestError("non-passing mission node result must not embed a worker result")

    node = _mission_node(plan, node_result["node_id"])
    mission_id = node.get("ref")
    node_state = run["graph_state"]["node_states"][node["id"]]
    worker = _bound_worker(run, mission_id, node_state.get("bound_worker_id"))
    blocked = outcome in {"blocked", "contract_gap"}
    phase = "blocked" if blocked else "worker_failed"
    blocker = f"mission worker returned {outcome}"
    refinement = node_result.get("refinement_request")
    if isinstance(refinement, dict):
        blocker = json.dumps(refinement, sort_keys=True, ensure_ascii=False)
    blockers = list(blockers_override or ([blocker] if blocked else []))

    worker["phase"] = phase
    if observed_head is not None:
        worker["worker_head_sha"] = observed_head
    mission_state = run["mission_states"][mission_id]
    mission_state.update(
        {"phase": phase, "blockers": blockers, "head_sha": observed_head}
    )
    for task_id, task_state in run.get("task_states", {}).items():
        if not task_id.startswith(f"{mission_id}/") or not isinstance(task_state, dict):
            continue
        if task_state.get("phase") == "running":
            task_state.update(
                {
                    "phase": phase,
                    "blockers": blockers,
                    "refinement_request": refinement if outcome == "contract_gap" else None,
                }
            )
    node_state.update(
        {
            "phase": "blocked" if blocked else "failed",
            "last_outcome": outcome,
            "blockers": blockers,
        }
    )
    dispatch = next(
        (
            attempt
            for attempt in run.get("attempt_log", [])
            if isinstance(attempt, dict)
            and attempt.get("attempt_id") == node_result["attempt_id"]
        ),
        None,
    )
    if isinstance(dispatch, dict):
        dispatch["result"] = outcome
        _extend_unique(dispatch.setdefault("evidence", []), node_result.get("evidence_paths", []))
    for edge in plan.get("graph", {}).get("edges", []):
        if (
            not isinstance(edge, dict)
            or edge.get("from") != node["id"]
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
        edge_state["source_attempt_id"] = node_result["attempt_id"]


def _receipt(
    plan: dict[str, Any], run: dict[str, Any], node_id: str, command: str
) -> dict[str, Any]:
    node = _mission_node(plan, node_id)
    mission_id = node.get("ref")
    state = run.get("mission_states", {}).get(mission_id, {})
    return {
        "command": command,
        "node_id": node_id,
        "mission_id": mission_id,
        "phase": state.get("phase"),
        "head_sha": state.get("head_sha"),
        "blockers": list(state.get("blockers", [])),
    }


def record_worker_result(
    plan: dict[str, Any], run: dict[str, Any], args: Any
) -> dict[str, Any]:
    """Validate current evidence and atomically stage one mission result."""

    if args.repo_root is None:
        raise ManifestError("record-worker-result requires --repo-root")
    node_result = _load_json(args.node_result, "node_result")
    if not isinstance(node_result, dict) or not isinstance(node_result.get("node_id"), str):
        raise ManifestError("node result must identify a mission node")
    observation = _observe_bound_worker(plan, run, node_result, args.repo_root)
    args.worker_observation = observation
    manifest_errors = validate_current_plan_run(plan, run, repo_root=args.repo_root)
    if manifest_errors:
        raise _validation_failure("current PLAN/RUN does not validate", manifest_errors)
    node_errors = validate_node_result(
        plan, run, node_result, manifest_already_validated=True
    )
    if node_errors:
        raise _validation_failure("node result does not validate", node_errors)

    if node_result.get("status") == "succeeded" and node_result.get("outcome") == "pass":
        worker_result = node_result.get("worker_result")
        if not isinstance(worker_result, dict):
            raise ManifestError("passing mission node result must embed a worker result")
        if args.worker_result is not None:
            supplied = load_worker_result(args.worker_result)
            if supplied != worker_result:
                raise ManifestError(
                    "node result worker_result does not match --worker-result"
                )
        retained_results = [
            _load_json(path, "verifier_execution") for path in args.verifier_result
        ]
        _record_passing_result(
            plan, run, node_result, worker_result, retained_results, observation
        )
        return _receipt(plan, run, node_result["node_id"], "record-worker-result")

    if args.worker_result is not None or args.verifier_result:
        raise ManifestError("non-passing mission result cannot retain passing worker evidence")
    _record_nonpassing_result(
        plan,
        run,
        node_result,
        observed_head=observation["head_sha"],
    )
    return _receipt(plan, run, node_result["node_id"], "record-worker-result")


def reject_worker_result(
    plan: dict[str, Any], run: dict[str, Any], args: Any
) -> dict[str, Any]:
    """Record a parent-rejected current worker attempt without hand-editing RUN."""

    if args.repo_root is None:
        raise ManifestError("reject-worker-result requires --repo-root")
    node = _mission_node(plan, args.node_id)
    state = run.get("graph_state", {}).get("node_states", {}).get(args.node_id)
    if not isinstance(state, dict) or state.get("phase") != "running":
        raise ManifestError("reject-worker-result requires a running mission node")
    if state.get("bound_worker_id") != args.worker_id:
        raise ManifestError("reject-worker-result worker does not match the bound node")
    node_result = {
        "run_id": run.get("run_id"),
        "node_id": args.node_id,
        "attempt_id": state.get("last_attempt_id"),
        "plan_id": plan.get("plan_id"),
        "plan_revision": plan.get("revision"),
        "plan_digest_sha256": run.get("plan", {}).get("digest_sha256"),
        "graph_revision": run.get("graph_state", {}).get("graph_revision"),
        "batch_base_sha": run.get("integration", {}).get("batch_base_sha"),
        "status": "failed" if args.outcome == "retryable_failure" else "blocked",
        "outcome": args.outcome,
        "worker_result": None,
        "refinement_request": None,
        "evidence_paths": [],
    }
    observation = _observe_bound_worker(plan, run, node_result, args.repo_root)
    args.worker_observation = observation
    manifest_errors = validate_current_plan_run(plan, run, repo_root=args.repo_root)
    if manifest_errors:
        raise _validation_failure("current PLAN/RUN does not validate", manifest_errors)
    node_errors = validate_node_result(
        plan, run, node_result, manifest_already_validated=True
    )
    if node_errors:
        raise _validation_failure("rejected node result does not validate", node_errors)
    if args.outcome not in node.get("allowed_outcomes", []):
        raise ManifestError(
            f"outcome {args.outcome!r} is not declared by mission node {args.node_id!r}"
        )
    _record_nonpassing_result(
        plan,
        run,
        node_result,
        blockers_override=args.reason,
        observed_head=observation["head_sha"],
    )
    return _receipt(plan, run, args.node_id, "reject-worker-result")

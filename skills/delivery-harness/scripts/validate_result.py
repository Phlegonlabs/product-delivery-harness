#!/usr/bin/env python3
"""Validate a graph-backed mission payload in one pass.

A graph-backed run returns the node result and the worker result together, so
validating them through two CLIs walked the same PLAN and RUN manifests three
times and cost the parent two turns. This command loads the pair once,
validates it once, and returns one merged error list.

Read-only: it never writes PLAN, RUN, or Git state.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from harness_manifest import (
    ManifestError,
    load_plan,
    load_run,
    load_worker_result,
    validate_current_plan_run,
    is_current_pair,
    validate_plan,
    validate_run,
)
from validate_node_result import validate_node_result
from validate_worker_result import (
    _observe_git_worker,
    validate_worker_result_data,
)


def _unwrap(document: Any, key: str) -> Any:
    if isinstance(document, dict) and set(document) == {key}:
        return document[key]
    return document


def load_validation_inputs(
    plan_path: Path,
    run_path: Path,
    *,
    node_path: Path | None = None,
    worker_path: Path | None = None,
    verifier_paths: Sequence[Path | str] = (),
) -> tuple[Any, Any, Any, Any, list[Any]] | str:
    """Load PLAN, RUN, and result documents in one pass.

    Returns (plan, run, node_result, worker_result, retained verifier
    results), with None for result documents that were not requested, or the
    failure message when an input cannot be read or parsed.
    """
    try:
        plan = load_plan(plan_path)
        run = load_run(run_path)
        node_result = (
            _unwrap(json.loads(node_path.read_text(encoding="utf-8")), "node_result")
            if node_path
            else None
        )
        worker_result = load_worker_result(worker_path) if worker_path else None
        retained = [
            json.loads(Path(path).read_text(encoding="utf-8"))
            for path in verifier_paths
        ]
    except (ManifestError, OSError, ValueError, json.JSONDecodeError) as exc:
        return str(exc)
    return plan, run, node_result, worker_result, retained


def emit_result(errors: list[str]) -> int:
    """Print the shared PASS/ERROR payload and return the process exit code."""
    payload = {"status": "PASS" if not errors else "ERROR", "errors": errors}
    print(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False))
    return 0 if not errors else 2


def add_observation_arguments(
    parser: argparse.ArgumentParser,
    *,
    help_texts: bool = False,
    verifier_result_type: type[Path] | None = None,
) -> None:
    """Add the parent-observation claim flags shared by the worker CLIs."""
    parser.add_argument(
        "--observed-head-sha",
        help="Legacy parent-observed worker head SHA" if help_texts else None,
    )
    parser.add_argument(
        "--observed-changed-file",
        action="append",
        default=None,
        help="Parent-observed changed file; repeat for every path" if help_texts else None,
    )
    parser.add_argument(
        "--ancestry-confirmed",
        action="store_true",
        help=(
            "Assert the parent observed base as an ancestor of the worker head"
            if help_texts
            else None
        ),
    )
    parser.add_argument(
        "--verifier-result",
        action="append",
        default=[],
        type=verifier_result_type,
        help=(
            "Parent-retained verifier_runtime.py JSON result; repeat for each verifier"
            if help_texts
            else None
        ),
    )


def bound_worker_worktree_path(run: dict[str, Any], worker_result: Any) -> str | None:
    """Return the RUN worktree path bound to this mission/lease pair."""
    workers = run.get("workers", [])
    if not isinstance(worker_result, dict) or not isinstance(workers, list):
        return None
    return next(
        (
            worker.get("worktree_path")
            for worker in workers
            if isinstance(worker, dict)
            and worker.get("mission_id") == worker_result.get("mission_id")
            and worker.get("lease_id") == worker_result.get("lease_id")
        ),
        None,
    )


def worker_repo_root_required(run: dict[str, Any], worker_result: Any) -> bool:
    """Whether the bound worker worktree exists but --repo-root was omitted."""
    worker_path = bound_worker_worktree_path(run, worker_result)
    return isinstance(worker_path, str) and Path(worker_path).is_dir()


def worker_observation_kwargs(
    live_observation: dict[str, Any] | None,
    args: argparse.Namespace,
    retained: list[Any],
) -> dict[str, Any]:
    """Build validate_worker_result_data arguments from observations.

    Live Git observation of the bound checkout, when present, overrides the
    parent-observed claims.
    """
    return {
        "observed_head_sha": (
            live_observation["head_sha"]
            if live_observation is not None
            else args.observed_head_sha
        ),
        "observed_changed_files": (
            live_observation["changed_files"]
            if live_observation is not None
            else args.observed_changed_file
        ),
        "ancestry_confirmed": (
            live_observation["ancestry_confirmed"]
            if live_observation is not None
            else args.ancestry_confirmed
        ),
        "retained_verifier_results": retained,
        "observed_commit_order": (
            live_observation["commit_order"] if live_observation is not None else None
        ),
        "observed_task_changed_files": (
            live_observation["task_changed_files"]
            if live_observation is not None
            else None
        ),
        "manifest_already_validated": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument(
        "--node-result",
        type=Path,
        help="typed graph node result document",
    )
    parser.add_argument(
        "--worker-result",
        type=Path,
        help="worker result manifest document",
    )
    add_observation_arguments(parser, verifier_result_type=Path)
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Optional repository root; re-runs the frozen-source byte and "
        "semantic contract joins under that root during PLAN/RUN validation",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.node_result and not args.worker_result:
        return emit_result(["give at least one of --node-result or --worker-result"])

    loaded = load_validation_inputs(
        args.plan,
        args.run,
        node_path=args.node_result,
        worker_path=args.worker_result,
        verifier_paths=args.verifier_result,
    )
    if isinstance(loaded, str):
        return emit_result([loaded])
    plan, run, node_result, worker_result, retained = loaded

    errors: list[str] = []
    current_pair = is_current_pair(plan, run)
    if current_pair:
        live_observation = None
        if worker_result is not None and args.repo_root is not None:
            try:
                live_observation = _observe_git_worker(
                    run, worker_result, args.repo_root
                )
                if live_observation.get("dirty") is not False:
                    errors.append(
                        "--repo-root: live worker checkout is dirty or unavailable; RUN dirty=false is not sufficient"
                    )
            except ManifestError as exc:
                errors.append(f"--repo-root: {exc}")
        elif worker_repo_root_required(run, worker_result):
            errors.append(
                "--repo-root: current worker validation requires the live bound worktree"
            )
        errors.extend(
            validate_current_plan_run(plan, run, repo_root=args.repo_root)
        )
    else:
        if args.node_result:
            errors.append("node result validation requires PLAN v6 with RUN v11")
        errors.extend(validate_plan(plan, repo_root=args.repo_root))
        errors.extend(validate_run(plan, run))

    if not errors:
        if node_result is not None:
            errors.extend(
                validate_node_result(
                    plan, run, node_result, manifest_already_validated=True
                )
            )
        if worker_result is not None:
            errors.extend(
                f"{issue['path']}: {issue['message']}" if isinstance(issue, dict) else str(issue)
                for issue in validate_worker_result_data(
                    plan,
                    run,
                    worker_result,
                    **worker_observation_kwargs(live_observation, args, retained),
                )
            )

    return emit_result(sorted(set(errors)))


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())

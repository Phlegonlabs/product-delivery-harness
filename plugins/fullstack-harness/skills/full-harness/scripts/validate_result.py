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
from typing import Any

from harness_manifest import (
    ManifestError,
    load_plan,
    load_run,
    validate_current_plan_run,
    is_current_pair,
    validate_plan,
    validate_run,
)
from validate_node_result import validate_node_result
from validate_worker_result import load_worker_result, validate_worker_result_data


def _unwrap(document: Any, key: str) -> Any:
    if isinstance(document, dict) and set(document) == {key}:
        return document[key]
    return document


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
    parser.add_argument("--observed-head-sha")
    parser.add_argument("--observed-changed-file", action="append", default=None)
    parser.add_argument("--ancestry-confirmed", action="store_true")
    parser.add_argument("--verifier-result", action="append", default=[], type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.node_result and not args.worker_result:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "errors": ["give at least one of --node-result or --worker-result"],
                },
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2

    errors: list[str] = []
    try:
        plan = load_plan(args.plan)
        run = load_run(args.run)
        node_result = (
            _unwrap(json.loads(args.node_result.read_text(encoding="utf-8")), "node_result")
            if args.node_result
            else None
        )
        worker_result = load_worker_result(args.worker_result) if args.worker_result else None
        retained = [
            json.loads(path.read_text(encoding="utf-8")) for path in args.verifier_result
        ]
    except (ManifestError, OSError, ValueError, json.JSONDecodeError) as exc:
        payload = {"status": "ERROR", "errors": [str(exc)]}
        print(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False))
        return 2

    current_pair = is_current_pair(plan, run)
    if current_pair:
        errors.extend(validate_current_plan_run(plan, run))
    else:
        if args.node_result:
            errors.append("node result validation requires PLAN v6 with RUN v11")
        errors.extend(validate_plan(plan))
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
                    observed_head_sha=args.observed_head_sha,
                    observed_changed_files=args.observed_changed_file,
                    ancestry_confirmed=args.ancestry_confirmed,
                    retained_verifier_results=retained,
                    manifest_already_validated=True,
                )
            )

    errors = sorted(set(errors))
    payload = {"status": "PASS" if not errors else "ERROR", "errors": errors}
    print(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())

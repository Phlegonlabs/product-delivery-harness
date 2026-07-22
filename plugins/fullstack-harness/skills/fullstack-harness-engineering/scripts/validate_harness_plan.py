#!/usr/bin/env python3
"""Validate canonical harness PLAN and optional RUN manifests without mutation."""

from __future__ import annotations

import argparse
import sys

from harness_manifest import (
    ManifestError,
    canonical_json,
    load_plan,
    load_run,
    plan_digest,
    validate_integration_head_against_git,
    validate_plan,
    validate_run,
    validate_ui_evidence_files,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, help="Path to PLAN.md")
    parser.add_argument("--run", help="Optional path to plan-backed RUN.md")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used to verify schema-v9 screenshot artifacts",
    )
    args = parser.parse_args(argv)
    try:
        plan = load_plan(args.plan)
        errors = validate_plan(plan)
        run_errors: list[str] = []
        if args.run:
            run = load_run(args.run)
            run_errors = validate_run(plan, run)
            run_errors.extend(validate_ui_evidence_files(run, args.repo_root))
            run_errors.extend(validate_integration_head_against_git(run, args.repo_root))
    except (OSError, ManifestError) as exc:
        sys.stdout.write(
            canonical_json({"errors": [str(exc)], "status": "ERROR"})
        )
        return 2
    all_errors = sorted(set(errors + run_errors))
    result = {
        "errors": all_errors,
        "plan_digest_sha256": plan_digest(plan),
        "plan_id": plan.get("plan_id"),
        "plan_revision": plan.get("revision"),
        "status": "PASS" if not all_errors else "FAIL",
    }
    sys.stdout.write(canonical_json(result))
    return 0 if not all_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

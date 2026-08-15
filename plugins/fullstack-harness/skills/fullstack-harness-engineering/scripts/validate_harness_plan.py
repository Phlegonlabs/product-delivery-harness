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
    validate_current_plan_run,
    validate_integration_head_against_git,
    validate_plan,
    validate_run,
    validate_ui_evidence_files,
    validate_ui_surface_design_coverage,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, help="Path to PLAN.md")
    parser.add_argument("--run", help="Optional path to plan-backed RUN.md")
    parser.add_argument(
        "--repo-root",
        help="Optional repository root used to bind PLAN-v5 sources and verify UI artifacts",
    )
    parser.add_argument(
        "--design-system",
        help="Optional path to the product's design-system.json. When given, its "
        "stateMatrix and responsive verification set are cross-checked against the "
        "PLAN's UI surfaces so a PLAN cannot under-declare state or breakpoint "
        "coverage.",
    )
    args = parser.parse_args(argv)
    try:
        plan = load_plan(args.plan)
        errors: list[str] = []
        run_errors: list[str] = []
        run = None
        if args.run:
            run = load_run(args.run)
            if (plan.get("schema_version"), run.get("schema_version")) == (5, 10):
                errors = validate_current_plan_run(
                    plan, run, repo_root=args.repo_root
                )
            else:
                # Preserve the compatibility CLI for historical manifests;
                # current PLAN/RUN execution is strict before this dispatch.
                errors = validate_plan(plan, repo_root=args.repo_root)
                run_errors = validate_run(plan, run)
        else:
            errors = validate_plan(plan, repo_root=args.repo_root)
        if args.design_system:
            errors.extend(validate_ui_surface_design_coverage(plan, args.design_system))
        elif any(
            isinstance(source, dict)
            and str(source.get("location", "")).endswith("design-system.json")
            for source in (plan.get("sources") or [])
            if isinstance(plan.get("sources"), list)
        ):
            # A PLAN that freezes design-system.json as a contract source has
            # already committed to its stateMatrix and responsive set. Leaving
            # the cross-check opt-in let such a PLAN declare `ready` alone and
            # close out with one state of eleven.
            errors.append(
                "plan.sources: a frozen design-system.json contract source requires "
                "--design-system so state and responsive coverage are cross-checked"
            )
        if run is not None:
            repo_root = args.repo_root or "."
            run_errors.extend(validate_ui_evidence_files(run, repo_root))
            run_errors.extend(validate_integration_head_against_git(run, repo_root))
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

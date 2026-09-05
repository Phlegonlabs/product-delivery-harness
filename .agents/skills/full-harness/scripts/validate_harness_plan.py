#!/usr/bin/env python3
"""Validate canonical harness PLAN and optional RUN manifests without mutation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from harness_manifest import (
    ManifestError,
    canonical_json,
    load_plan,
    load_run,
    plan_digest,
    is_current_pair,
    validate_current_plan_run,
    validate_integration_head_against_git,
    validate_plan,
    validate_run,
    validate_ui_evidence_files,
    validate_ui_surface_design_coverage,
)


PRD_UI_RE = re.compile(r"\bUI-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
WIREFRAME_DATA_RE = re.compile(
    r'<script\s+id=["\']wireframe-data["\']\s+type=["\']application/json["\']\s*>'
    r"([\s\S]*?)</script>",
    re.IGNORECASE,
)


def _frozen_prd_source(plan: dict) -> dict | None:
    for source in plan.get("sources") or []:
        if (
            isinstance(source, dict)
            and str(source.get("location", "")).endswith("PRD.md")
        ):
            return source
    return None


def validate_ui_surface_prd_coverage(
    plan: dict, prd_path: str
) -> list[str]:
    """The PLAN's UI surfaces must name exactly the PRD's `UI-*` contract."""

    try:
        prd_text = Path(prd_path).read_text(encoding="utf-8")
    except OSError as exc:
        return [f"prd: cannot read {prd_path}: {exc}"]
    prd_ids = set(PRD_UI_RE.findall(prd_text))
    surfaces = plan.get("ui_surfaces")
    plan_ids = {
        surface.get("id")
        for surface in (surfaces if isinstance(surfaces, list) else [])
        if isinstance(surface, dict) and isinstance(surface.get("id"), str)
    }
    missing = sorted(prd_ids - plan_ids)
    extra = sorted(plan_ids - prd_ids)
    errors: list[str] = []
    if missing:
        errors.append(
            "plan.ui_surfaces: PRD surfaces absent from the PLAN: " + ", ".join(missing)
        )
    if extra:
        errors.append(
            "plan.ui_surfaces: PLAN surfaces absent from the PRD UI contract: "
            + ", ".join(extra)
        )
    return errors


def validate_ui_surface_wireframe_coverage(
    plan: dict, wireframes_path: str
) -> list[str]:
    """PLAN ui_surfaces and wireframes.html screens agree beyond the id set."""

    try:
        html = Path(wireframes_path).read_text(encoding="utf-8")
    except OSError as exc:
        return [f"wireframes: cannot read {wireframes_path}: {exc}"]
    match = WIREFRAME_DATA_RE.search(html)
    if match is None:
        return [f"wireframes: {wireframes_path} has no wireframe-data JSON block"]
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        return [f"wireframes: {wireframes_path} wireframe-data is invalid JSON: {exc}"]
    screens = data.get("screens") if isinstance(data, dict) else None
    screens_by_id: dict[str, dict] = {}
    if isinstance(screens, list):
        for screen in screens:
            if isinstance(screen, dict) and isinstance(screen.get("id"), str):
                screens_by_id[screen["id"]] = screen
    surfaces = {
        surface.get("id"): surface
        for surface in (plan.get("ui_surfaces") or [])
        if isinstance(surface, dict) and isinstance(surface.get("id"), str)
    }
    errors: list[str] = []
    for missing in sorted(set(surfaces) - set(screens_by_id)):
        errors.append(
            f"plan.ui_surfaces: surface {missing} has no wireframes.html screen"
        )
    for extra in sorted(set(screens_by_id) - set(surfaces)):
        errors.append(
            f"wireframes: screen {extra} is absent from the PLAN ui_surfaces"
        )
    for surface_id in sorted(set(surfaces) & set(screens_by_id)):
        surface = surfaces[surface_id]
        screen = screens_by_id[surface_id]
        if surface.get("route") != screen.get("route"):
            errors.append(
                f"plan.ui_surfaces: surface {surface_id} route "
                f"{surface.get('route')!r} differs from the wireframe route "
                f"{screen.get('route')!r}"
            )
        wireframe_states = {
            state.get("id")
            for state in (screen.get("states") or [])
            if isinstance(state, dict) and isinstance(state.get("id"), str)
        }
        plan_states = set(surface.get("states") or [])
        if plan_states != wireframe_states:
            errors.append(
                f"plan.ui_surfaces: surface {surface_id} states "
                f"{sorted(plan_states)} differ from the wireframe states "
                f"{sorted(wireframe_states)}"
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, help="Path to PLAN.md")
    parser.add_argument("--run", help="Optional path to plan-backed RUN.md")
    parser.add_argument(
        "--repo-root",
        help="Optional repository root used to bind PLAN-v6 sources and verify UI artifacts",
    )
    parser.add_argument(
        "--prd",
        help="Optional path to the product's PRD.md. Required when the PLAN "
        "freezes a PRD.md contract source: the PLAN's ui_surfaces must name "
        "exactly the PRD's `UI-*` surface contract, and the file's bytes must "
        "match the frozen source hash.",
    )
    parser.add_argument(
        "--wireframes",
        help="Optional path to wireframes.html. When given, the PLAN's "
        "ui_surfaces are joined against the wireframe screens beyond the id "
        "set: route and states must agree.",
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
            if is_current_pair(plan, run):
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
        prd_source = _frozen_prd_source(plan)
        if prd_source is not None and not args.prd:
            errors.append(
                "plan.sources: a frozen PRD.md contract source requires "
                "--prd so the UI surface contract is cross-checked"
            )
        if args.prd:
            errors.extend(validate_ui_surface_prd_coverage(plan, args.prd))
            expected_hash = (
                prd_source.get("content_sha256") if prd_source is not None else None
            )
            if isinstance(expected_hash, str) and expected_hash:
                try:
                    actual_hash = hashlib.sha256(
                        Path(args.prd).read_bytes()
                    ).hexdigest()
                except OSError as exc:
                    errors.append(f"prd: cannot read {args.prd}: {exc}")
                else:
                    if actual_hash != expected_hash:
                        errors.append(
                            f"prd: {args.prd} does not match the frozen PRD "
                            f"source content hash {expected_hash}"
                        )
        if args.wireframes:
            errors.extend(
                validate_ui_surface_wireframe_coverage(plan, args.wireframes)
            )
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

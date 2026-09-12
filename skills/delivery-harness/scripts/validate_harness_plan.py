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
from harness_contract_join import (
    DESIGN_SYSTEM_MARKDOWN_SOURCE_KINDS,
    frozen_sources as shared_frozen_sources,
    full_wireframe_checker_errors,
    parse_prd_ui_contract as shared_parse_prd_ui_contract,
    parse_wireframe_data,
    prd_web_viewport_floor_errors,
    registry_web_viewport_floor_errors,
    required_design_system_source_errors,
    validate_frozen_contract_joins,
    validate_plan_prd_text,
    validate_plan_wireframe_data,
    web_viewport_floor_required,
)
from harness_design_contract import compare_design_system_pair


PRD_SOURCE_KINDS = {"prd", "product requirement", "product requirements"}
WIREFRAME_SOURCE_KINDS = {"wireframe", "wireframes", "approved wireframe"}
DESIGN_SYSTEM_SOURCE_KINDS = {
    "design system json",
    "design system machine",
}


def validate_design_system_pair(
    markdown_path: str, registry_path: str
) -> list[str]:
    try:
        markdown_text = Path(markdown_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"design-system.md: cannot read {markdown_path}: {exc}"]
    try:
        registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"design-system.json: cannot read {registry_path}: {exc}"]
    if not isinstance(registry, dict):
        return [f"design-system.json: {registry_path} must contain a JSON object"]
    return compare_design_system_pair(markdown_text, registry)


def _frozen_sources(
    plan: dict, *, kinds: set[str], filenames: set[str]
) -> list[dict]:
    return shared_frozen_sources(plan, kinds=kinds, filenames=filenames)


def _validate_bound_artifact(
    sources: list[dict], artifact_path: str | None, *, flag: str, label: str
) -> list[str]:
    if not sources:
        return []
    if artifact_path is None:
        return [
            f"plan.sources: a frozen {label} contract source requires {flag} "
            "so its bytes and semantic projection are cross-checked"
        ]
    if len(sources) != 1:
        return [
            f"plan.sources: expected exactly one frozen {label} contract source, "
            f"found {len(sources)}"
        ]
    expected_hash = sources[0].get("content_sha256")
    if not isinstance(expected_hash, str) or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None:
        return [
            f"plan.sources: frozen {label} contract source requires content_sha256 "
            f"before {flag} can prove byte identity"
        ]
    try:
        actual_hash = hashlib.sha256(Path(artifact_path).read_bytes()).hexdigest()
    except OSError as exc:
        return [f"{label}: cannot read {artifact_path}: {exc}"]
    if actual_hash != expected_hash:
        return [
            f"{label}: {artifact_path} does not match the frozen {label} "
            f"source content hash {expected_hash}"
        ]
    return []


def _parse_prd_ui_contract(prd_text: str) -> tuple[dict[str, dict[str, object]], list[str]]:
    return shared_parse_prd_ui_contract(prd_text)


def validate_ui_surface_prd_coverage(
    plan: dict, prd_path: str
) -> list[str]:
    """PLAN surfaces must equal the PRD contract's ids, routes, and states."""

    try:
        prd_text = Path(prd_path).read_text(encoding="utf-8")
    except OSError as exc:
        return [f"prd: cannot read {prd_path}: {exc}"]
    return validate_plan_prd_text(plan, prd_text)


def validate_ui_surface_wireframe_coverage(
    plan: dict, wireframes_path: str, prd_path: str | None = None
) -> list[str]:
    """PLAN ui_surfaces and wireframes.html screens agree beyond the id set."""

    try:
        html = Path(wireframes_path).read_text(encoding="utf-8")
    except OSError as exc:
        return [f"wireframes: cannot read {wireframes_path}: {exc}"]
    data, errors = parse_wireframe_data(html, label=f"wireframes: {wireframes_path}")
    if data is not None:
        errors.extend(validate_plan_wireframe_data(plan, data))
    errors.extend(
        full_wireframe_checker_errors(
            Path(wireframes_path).read_bytes(),
            Path(prd_path).read_bytes() if prd_path else None,
        )
    )
    return errors


def _viewport_floor_errors(
    run: dict | None, *, prd_path: str | None, design_system_path: str | None
) -> list[str]:
    """Apply the three-viewport web floor at the CLI file joins.

    The frozen-source joins inside ``validate_current_plan_run`` already
    enforce this floor for gated runs; this covers the explicit ``--prd`` and
    ``--design-system`` joins, which also run without ``--repo-root``. Runs
    without a version gate pinning harness 0.34.0+ keep the two-target floor.
    """

    if not web_viewport_floor_required(run):
        return []
    errors: list[str] = []
    if prd_path is not None:
        try:
            prd_text = Path(prd_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            prd_text = None  # unreadable bytes are reported by the coverage join
        if prd_text is not None:
            errors.extend(prd_web_viewport_floor_errors(prd_text))
    if design_system_path is not None:
        try:
            registry = json.loads(Path(design_system_path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            registry = None  # malformed JSON is reported by the design joins
        if isinstance(registry, dict):
            errors.extend(registry_web_viewport_floor_errors(registry))
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
        help="Optional path to wireframes.html. Required when the PLAN freezes "
        "that source: its bytes must match the frozen hash, its screen ids, "
        "routes, and states must agree with the PLAN's ui_surfaces, and it must "
        "pass product-definition-builder's full wireframe checker (reviewer "
        "shell, self-containment, approved status, PRD join).",
    )
    parser.add_argument(
        "--design-system",
        help="Optional path to the product's design-system.json. Required when "
        "the PLAN freezes that source: its bytes must match the frozen hash, and "
        "its DS registry, stateMatrix, and responsive verification set are joined "
        "against the PLAN's UI surfaces.",
    )
    parser.add_argument(
        "--design-system-markdown",
        help="Optional path to design-system.md. Required with a frozen design-system "
        "pair so its bytes and generated contract can be checked against "
        "--design-system.",
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
        errors.extend(required_design_system_source_errors(plan))
        if args.repo_root and run is None:
            errors.extend(validate_frozen_contract_joins(plan, args.repo_root))
        prd_sources = _frozen_sources(
            plan, kinds=PRD_SOURCE_KINDS, filenames={"prd.md"}
        )
        errors.extend(
            _validate_bound_artifact(
                prd_sources,
                args.prd,
                flag="--prd",
                label="PRD",
            )
        )
        if args.prd:
            errors.extend(validate_ui_surface_prd_coverage(plan, args.prd))
        wireframe_sources = _frozen_sources(
            plan,
            kinds=WIREFRAME_SOURCE_KINDS,
            filenames={"wireframes.html"},
        )
        errors.extend(
            _validate_bound_artifact(
                wireframe_sources,
                args.wireframes,
                flag="--wireframes",
                label="wireframes",
            )
        )
        if args.wireframes:
            errors.extend(
                validate_ui_surface_wireframe_coverage(
                    plan, args.wireframes, args.prd
                )
            )
        design_system_sources = _frozen_sources(
            plan,
            kinds=DESIGN_SYSTEM_SOURCE_KINDS,
            filenames={"design-system.json"},
        )
        errors.extend(
            _validate_bound_artifact(
                design_system_sources,
                args.design_system,
                flag="--design-system",
                label="design-system.json",
            )
        )
        if args.design_system:
            errors.extend(validate_ui_surface_design_coverage(plan, args.design_system))
        design_markdown_sources = _frozen_sources(
            plan,
            kinds=DESIGN_SYSTEM_MARKDOWN_SOURCE_KINDS,
            filenames={"design-system.md"},
        )
        errors.extend(
            _validate_bound_artifact(
                design_markdown_sources,
                args.design_system_markdown,
                flag="--design-system-markdown",
                label="design-system.md",
            )
        )
        if args.design_system and args.design_system_markdown:
            errors.extend(
                validate_design_system_pair(
                    args.design_system_markdown, args.design_system
                )
            )
        if run is not None:
            errors.extend(
                _viewport_floor_errors(
                    run, prd_path=args.prd, design_system_path=args.design_system
                )
            )
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

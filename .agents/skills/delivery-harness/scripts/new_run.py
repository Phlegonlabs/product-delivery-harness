#!/usr/bin/env python3
"""Generate a fresh RUN.md skeleton from a validated PLAN.md.

Almost every field of a new RUN is derivable from the PLAN: the graph state
mirrors the PLAN graph node-for-node, mission and task states are seeded from
the PLAN's missions and tasks, final gate result ids are copied from
`plan.final_gates`, the plan digest is computed, and the twelve authorization
entries all start unauthorized. Hand-typing that was the largest single
authoring cost of starting a managed run, and a mistyped key set fails the
exact-key validator with no default fill to fall back on.

This command writes only the derivable skeleton. Every field it cannot derive
is left at its safe unset value for the parent to fill from observation:
authorizations stay false, `observed` stays null, `integration.branch` and
`batch_base_sha` stay unset, and `plan_readiness` stays `draft`. Generating a
RUN grants nothing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from harness_manifest import (
    AUTHORIZATION_KEYS,
    ManifestError,
    load_plan,
    plan_digest,
    validate_current_plan_run,
    validate_plan,
)
from harness_contract import contract_digest

def _harness_version() -> str:
    """Read the Harness version from skill-local or package metadata.

    A normal installation copies only the five skill directories, so the
    delivery-harness directory carries its own VERSION file. Package metadata
    remains a compatibility fallback for older packaged layouts.
    """

    version_pattern = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
    skill_version = Path(__file__).resolve().parent.parent / "VERSION"
    if skill_version.is_file():
        version = skill_version.read_text(encoding="utf-8").strip()
        if version_pattern.fullmatch(version):
            return version
        raise ManifestError(f"invalid Harness VERSION value in {skill_version}: {version!r}")

    for directory in Path(__file__).resolve().parents:
        package = directory / "package.json"
        # Only a package.json that owns a skill tree is this Harness's. A
        # standalone install (for example `~/.pi/agent/skills/...`) has none
        # above it, and walking on would happily record an unrelated app's
        # version from the user's home directory into the upgrade gate.
        if not package.is_file() or not (
            (directory / ".agents" / "skills").is_dir()
            or (directory / "plugins").is_dir()
        ):
            continue
        try:
            version = json.loads(package.read_text(encoding="utf-8"))["version"]
        except (OSError, ValueError, KeyError):
            continue
        if isinstance(version, str) and version_pattern.fullmatch(version):
            return version
    raise ManifestError(
        "cannot determine the Harness version; install delivery-harness with its VERSION file"
    )



def _node_state() -> dict[str, Any]:
    return {
        "phase": "dormant",
        "attempts": 0,
        "last_attempt_id": None,
        "last_outcome": None,
        "bound_worker_id": None,
        "blockers": [],
    }


def _edge_state() -> dict[str, Any]:
    return {
        "status": "dormant",
        "traversals": 0,
        "source_attempt_id": None,
    }


def _mission_state() -> dict[str, Any]:
    return {
        "phase": "queued",
        "lease_id": None,
        "lease_plan_revision": None,
        "lease_plan_digest_sha256": None,
        "worker_id": None,
        "base_sha": None,
        "head_sha": None,
        "prior_head_shas": [],
        "integration_gate": "planned",
        "integrated_sha": None,
        "blockers": [],
        "report_path": None,
    }


def _task_state() -> dict[str, Any]:
    return {
        "phase": "queued",
        "attempts": 0,
        "commit_sha": None,
        "verifier_status": "planned",
        "blockers": [],
        "refinement_request": None,
    }


def _gate_results(gates: Any) -> list[dict[str, Any]]:
    if not isinstance(gates, list):
        return []
    return [
        {"id": gate["id"], "status": "planned", "head_sha": None, "evidence": []}
        for gate in gates
        if isinstance(gate, dict) and isinstance(gate.get("id"), str)
    ]


def build_run(plan: dict[str, Any], *, run_id: str, branch: str) -> dict[str, Any]:
    security_review = plan.get("security_review")
    if not isinstance(security_review, dict) or security_review.get("status") not in {
        "required",
        "not_applicable",
    }:
        raise ManifestError(
            "new RUN requires explicit plan.security_review status required or not_applicable"
        )
    graph = plan.get("graph", {}) or {}
    nodes = graph.get("nodes", []) or []
    edges = graph.get("edges", []) or []
    missions = plan.get("missions", []) or []

    return {
        "schema_version": 11,
        "run_id": run_id,
        "plan": {
            "id": plan["plan_id"],
            "revision": plan["revision"],
            "digest_sha256": plan_digest(plan),
        },
        "status": "draft",
        "intent": "plan-only",
        "plan_readiness": "draft",
        "execution_authorized": False,
        "execution_authorization_source": None,
        "execution_authorization_scope": None,
        "control": {
            "desired_state": "running",
            "requested_at": None,
            "source": None,
            "acknowledged_at": None,
        },
        "authorizations": {
            key: {"authorized": False, "source": None} for key in AUTHORIZATION_KEYS
        },
        "runtime_capabilities": {
            "worker_runtime": "parent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": 1,
            "runtime_adapter": {
                "provider": "generic",
                "available_drivers": ["sequential_parent"],
                "detection_source": "fallback",
                "version_gate": {
                    "host_version": None,
                    "minimum_host_version": None,
                    "harness_version": None,
                    "required_harness_version": _harness_version(),
                    "session_id": None,
                    "loaded_contract_digest": None,
                    "installed_contract_digest": contract_digest(),
                    "status": "unobserved",
                    "evidence": "Runtime and Harness versions have not been observed yet",
                },
            },
            "reviewer_tools": {
                "chrome_devtools": {
                    "status": "unobserved",
                    "provider": "generic",
                    "driver": "sequential_parent",
                    "surface": "none",
                    "probe_scope": "unobserved",
                    "session_id": None,
                    "evidence": "No fresh reviewer session has probed Chrome DevTools yet",
                }
            },
            "permission_boundary": {
                "selected_mode": "unknown",
                "profile_name": None,
                "approval_policy": "unknown",
                "filesystem_scope": "unknown",
                "network_scope": "unknown",
                "local_binding": "unknown",
                "worker_inheritance": "unknown",
                "status": "unknown",
            },
        },
        "observed": {
            "captured_at": None,
            "git": {
                "parent_worktree_path": None,
                "parent_branch": None,
                "parent_head_sha": None,
                "parent_dirty": None,
                "default_branch": None,
                "worktrees": [],
            },
            "runtime": {
                "available_worker_slots": 1,
                "isolation_capacity": 1,
                "completion_channel_available": True,
            },
        },
        "integration": {
            "branch": branch,
            "retention": "ephemeral",
            "batch_base_sha": None,
            "integration_head_sha": None,
            "prior_head_shas": [],
            "coordination_paths": [
                "docs/goal/PLAN.md",
                "docs/goal/RUN.md",
                "docs/goal/DECISIONS.md",
            ],
        },
        "batch_gate_results": _gate_results(plan.get("batch_verifiers")),
        "final_gate_results": _gate_results(plan.get("final_gates")),
        "ui_evidence": [],
        "landing": {
            "mode": "local_only",
            "remote": "origin",
            "pushed_head_sha": None,
            "continuity": {
                "status": "planned",
                "branch_ref": branch,
                "head_sha": None,
                "reason": "Keep the reviewed run branch so the user can read it and land it",
            },
        },
        "graph_state": {
            "graph_revision": plan["revision"],
            "node_states": {
                node["id"]: _node_state()
                for node in nodes
                if isinstance(node, dict) and isinstance(node.get("id"), str)
            },
            "edge_states": {
                edge["id"]: _edge_state()
                for edge in edges
                if isinstance(edge, dict) and isinstance(edge.get("id"), str)
            },
        },
        "mission_states": {
            mission["id"]: _mission_state()
            for mission in missions
            if isinstance(mission, dict) and isinstance(mission.get("id"), str)
        },
        "task_states": {
            task["id"]: _task_state()
            for mission in missions
            if isinstance(mission, dict)
            for task in (mission.get("tasks") or [])
            if isinstance(task, dict) and isinstance(task.get("id"), str)
        },
        "active_wave": {
            "wave_id": None,
            "status": "idle",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": None,
            "batch_base_sha": None,
            "selected_missions": [],
            "deferred_missions": [],
            "conflict_edges": [],
        },
        "closed_waves": [],
        "workers": [],
        "review_workers": [],
        "review_lineages": {
            node["review"]["lineage_id"]: {
                "review_type": node["review"]["type"],
                "mission_ids": node["review"]["mission_ids"],
                "base_allowance": node["max_attempts"],
                "additional_allowance": 0,
                "consumed_attempts": 0,
                "failure_families": [],
                "owner_decisions": [],
            }
            for node in nodes
            if isinstance(node, dict)
            and node.get("kind") == "verifier"
            and node.get("executor") == "runtime_worker"
            and isinstance(node.get("review"), dict)
            and isinstance(node["review"].get("lineage_id"), str)
        },
        "workflow_runs": [],
        "verifier_executions": [],
        "runtime_metrics": None,
        "attempt_log": [],
    }


def render(run: dict[str, Any]) -> str:
    body = json.dumps({"harness_run": run}, indent=2, ensure_ascii=False)
    return (
        "# Run: <feature or product slice>\n"
        "\n"
        "Generated from PLAN.md by `scripts/new_run.py`. Every derivable field is\n"
        "filled; authorizations, observations, and the batch base are deliberately\n"
        "unset. Generating this file grants nothing.\n"
        "\n"
        "## Harness Run State\n"
        "\n"
        "```json\n" + body + "\n```\n"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--branch",
        required=True,
        help="exact non-protected integration branch ref for this run",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="write RUN.md here; refuses to overwrite an existing file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = load_plan(args.plan)
    except (ManifestError, OSError) as exc:
        print(f"cannot read plan: {exc}", file=sys.stderr)
        return 2

    errors = validate_plan(plan)
    if errors:
        print("plan does not validate; fix it before generating a run:", file=sys.stderr)
        for message in errors:
            print(f"  {message}", file=sys.stderr)
        return 2

    try:
        run = build_run(plan, run_id=args.run_id, branch=args.branch)
        run_errors = validate_current_plan_run(plan, run)
    except (ManifestError, OSError) as exc:
        print(f"cannot generate run: {exc}", file=sys.stderr)
        return 2
    if run_errors:
        print("generated run does not validate:", file=sys.stderr)
        for message in run_errors:
            print(f"  {message}", file=sys.stderr)
        return 2

    document = render(run)
    if args.out is None:
        print(document, end="")
        return 0
    if args.out.exists():
        # Never clobber live run state.
        print(f"refusing to overwrite {args.out}", file=sys.stderr)
        return 2
    args.out.write_text(document, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Upgrade canonical harness PLAN/RUN manifests forward one schema version at a time.

Every step adds only the keys a version introduces, always with neutral
"nothing has happened yet" values. The tool never fabricates an authorization,
a passed gate, a SHA, or any evidence. After the full chain the result must pass
the same validators as a from-scratch file; otherwise nothing is written.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from harness_manifest import (
    ManifestError,
    PLAN_HEADING,
    RUN_HEADING,
    load_plan,
    load_run,
    plan_digest,
    validate_plan,
    validate_run,
    validate_ui_evidence_files,
)


PLAN_MAX_SCHEMA = 5
RUN_MAX_SCHEMA = 10

LEGACY_ACCEPTANCE_RE = re.compile(r"^(?P<test_id>TEST-[A-Z0-9_-]+):\s+(?P<criterion>\S.*)$")


class UpgradeError(Exception):
    """Raised when an upgrade cannot complete without fabricating content."""


# --- PLAN upgrade steps -----------------------------------------------------


def _upgrade_plan_v2_to_v3(plan: dict[str, Any], repo_root: Path) -> list[str]:
    plan["schema_version"] = 3
    return []


def _freeze_source(source: dict[str, Any], repo_root: Path) -> str:
    """Return the real SHA-256 of the source content, or fail rather than invent one."""

    location = source.get("location")
    if isinstance(location, str) and location.strip():
        candidate = (repo_root / location).resolve()
        try:
            if candidate.is_file():
                return hashlib.sha256(candidate.read_bytes()).hexdigest()
        except OSError:
            pass
    raise UpgradeError(
        f"cannot freeze source {source.get('id')!r}: its location "
        f"{location!r} is not a readable file under --repo-root. Schema v4 "
        f"requires a real content_sha256 or source_revision per source, and "
        f"the upgrade must not fabricate one. Freeze this source's provenance "
        f"by hand, then re-run."
    )


def _synthesize_graph(plan: dict[str, Any]) -> dict[str, Any]:
    """Project schema-v2/v3 mission dependencies into the v4 typed graph.

    Every mission becomes one harness_parent mission node; every mission
    depends_on becomes one dependency edge. This is a faithful structural
    projection of the existing DAG, not new execution policy: no runtime
    provider is invented (executor is harness_parent, runtime is null).
    """

    missions = [
        mission
        for mission in plan.get("missions", [])
        if isinstance(mission, dict) and isinstance(mission.get("id"), str)
    ]
    node_id_for = {mission["id"]: f"N-{mission['id']}" for mission in missions}
    nodes = [
        {
            "id": node_id_for[mission["id"]],
            "kind": "mission",
            "ref": mission["id"],
            "executor": "harness_parent",
            "allowed_outcomes": ["pass", "blocked"],
            "max_attempts": 1,
            "runtime": None,
        }
        for mission in missions
    ]
    edges: list[dict[str, Any]] = []
    has_incoming = {mission["id"]: False for mission in missions}
    counter = 0
    for mission in missions:
        mission_id = mission["id"]
        for dependency in mission.get("depends_on", []):
            if (
                isinstance(dependency, str)
                and dependency in node_id_for
                and dependency != mission_id
            ):
                counter += 1
                edges.append(
                    {
                        "id": f"E-DEP-{counter}",
                        "kind": "dependency",
                        "from": node_id_for[dependency],
                        "to": node_id_for[mission_id],
                        "on_outcomes": ["pass"],
                        "max_traversals": None,
                    }
                )
                has_incoming[mission_id] = True
    entry_nodes = [
        node_id_for[mission["id"]]
        for mission in missions
        if not has_incoming[mission["id"]]
    ]
    return {"entry_nodes": entry_nodes, "nodes": nodes, "edges": edges}


def _upgrade_plan_v3_to_v4(plan: dict[str, Any], repo_root: Path) -> list[str]:
    added: list[str] = []
    for source in plan.get("sources", []):
        if isinstance(source, dict):
            source["content_sha256"] = _freeze_source(source, repo_root)
            source["source_revision"] = None
    added.extend(["sources[].content_sha256", "sources[].source_revision"])
    plan["required_reviews"] = []
    added.append("required_reviews")
    plan["graph"] = _synthesize_graph(plan)
    added.append("graph")
    for mission in plan.get("missions", []):
        if isinstance(mission, dict):
            mission.pop("depends_on", None)
    added.append("removed missions[].depends_on")
    plan["schema_version"] = 4
    return added


def _upgrade_release_target_v4_to_v5(target: dict[str, Any]) -> dict[str, Any]:
    target_id = target.get("id")
    data_mode = target.get("data_mode")
    stage = (
        "development"
        if data_mode == "isolated_non_production"
        else "production"
        if data_mode == "production"
        else None
    )
    if stage is None:
        raise UpgradeError(
            f"cannot convert release target {target_id!r}: its stage is ambiguous"
        )
    return {
        "id": target_id,
        "stage": stage,
        "source": target.get("source"),
        "artifact_kind": None,
        "requires_signing": None,
        "channel": None,
        "data_mode": data_mode,
        "trigger": None,
        "migration_classification": None,
        "commands": {
            "build": None,
            "migrate": target.get("migration_command"),
            "publish": target.get("deploy_command"),
        },
        "prerequisites": copy.deepcopy(target.get("prerequisites", [])),
        "smoke_verifiers": copy.deepcopy(target.get("smoke_verifiers", [])),
    }


def _upgrade_plan_v4_to_v5(plan: dict[str, Any], repo_root: Path) -> list[str]:
    del repo_root
    for source in plan.get("sources", []):
        if not isinstance(source, dict):
            continue
        status = source.get("status")
        if status == "delta accepted":
            source["status"] = "delta_accepted"
        elif status != "frozen":
            raise UpgradeError(
                f"cannot upgrade source {source.get('id')!r}: schema v5 requires "
                "frozen or delta_accepted published sources"
            )
        location = source.get("location")
        if isinstance(location, str) and "://" not in location:
            normalized = location.replace("\\", "/").removeprefix("./").strip("/").lower()
            parts = normalized.split("/")
            if any(
                parts[index : index + 3]
                in (["docs", "product", ".prd-staging"], ["docs", "product", ".design-staging"])
                for index in range(max(0, len(parts) - 2))
            ):
                raise UpgradeError(
                    f"cannot upgrade source {source.get('id')!r}: publish staged product input first"
                )
        source["staged_revision"] = None

    for mission in plan.get("missions", []):
        if not isinstance(mission, dict):
            continue
        for task in mission.get("tasks", []):
            if not isinstance(task, dict):
                continue
            rows: list[dict[str, Any]] = []
            seen_test_ids: set[str] = set()
            for entry in task.get("acceptance_matrix", []):
                match = LEGACY_ACCEPTANCE_RE.fullmatch(entry) if isinstance(entry, str) else None
                if match is None:
                    raise UpgradeError(
                        f"cannot convert acceptance row for task {task.get('id')!r}: "
                        "legacy rows must already name an exact TEST-* ID as "
                        "'TEST-ID: criterion'. Nothing was written."
                    )
                test_id = match.group("test_id")
                if test_id in seen_test_ids:
                    raise UpgradeError(
                        f"cannot convert acceptance rows for task {task.get('id')!r}: "
                        f"duplicate TEST ID {test_id!r}"
                    )
                seen_test_ids.add(test_id)
                rows.append(
                    {
                        "test_id": test_id,
                        "trace_ids": copy.deepcopy(task.get("trace_ids", [])),
                        "criterion": match.group("criterion"),
                    }
                )
            task["acceptance_matrix"] = rows

    if isinstance(plan.get("release"), dict):
        targets = plan["release"].get("targets")
        if not isinstance(targets, list):
            raise UpgradeError("cannot convert release targets: targets must be a list")
        plan["release"]["targets"] = [
            _upgrade_release_target_v4_to_v5(target)
            for target in targets
            if isinstance(target, dict)
        ]
    plan["schema_version"] = 5
    return [
        "sources[].staged_revision",
        "missions[].tasks[].acceptance_matrix structured rows",
        "release.targets provider-neutral fields when release is present",
    ]


_PLAN_STEPS = {
    2: _upgrade_plan_v2_to_v3,
    3: _upgrade_plan_v3_to_v4,
    4: _upgrade_plan_v4_to_v5,
}


# --- RUN upgrade steps ------------------------------------------------------


def _neutral_landing(*, auto_merge: bool) -> dict[str, Any]:
    landing = {
        "mode": "local_only",
        "remote": "origin",
        "head_branch": None,
        "base_branch": "main",
        "pushed_head_sha": None,
        "pr_number": None,
        "pr_url": None,
        "pr_state": "not_created",
        "pr_head_sha": None,
        "checks_status": "not_started",
        "checks_head_sha": None,
        "review_status": "not_requested",
        "review_head_sha": None,
        "blocking_findings": None,
        "unresolved_threads": None,
        "merge_status": "not_ready",
        "merged_sha": None,
    }
    if auto_merge:
        landing["auto_merge_requested"] = False
        landing["auto_merge_head_sha"] = None
    return landing


def _neutral_post_merge_cleanup() -> dict[str, Any]:
    return {
        "status": "not_started",
        "base": {"branch": "main", "head_sha": None, "merged_sha_reachable": None},
        "worktree": {
            "path": None,
            "branch_ref": None,
            "head_sha": None,
            "dirty": None,
            "managed_by": None,
            "status": "not_applicable",
        },
        "local_branch": {"ref": None, "head_sha": None, "status": "pending"},
        "evidence": [],
        "deferred_reason": None,
    }


def _derive_runtime_adapter(run: dict[str, Any]) -> dict[str, Any]:
    """Record the minimal adapter consistent with the already-recorded runtime mode.

    detection_source is "fallback": the upgrade did not freshly observe the host,
    it derived the smallest provider/driver set that keeps the recorded
    worker_runtime valid. sequential_parent is always included as the safe fallback.
    """

    worker_runtime = run.get("runtime_capabilities", {}).get("worker_runtime")
    if worker_runtime == "app_task":
        drivers = ["app_threads", "subagents", "sequential_parent"]
        provider = "codex"
    elif worker_runtime == "subagent":
        drivers = ["subagents", "sequential_parent"]
        provider = "generic"
    else:
        drivers = ["sequential_parent"]
        provider = "generic"
    return {
        "provider": provider,
        "available_drivers": drivers,
        "detection_source": "fallback",
    }


def _neutral_deployment_target() -> dict[str, Any]:
    return {
        "status": "not_started",
        "source_sha": None,
        "worker_name": None,
        "url": None,
        "version_id": None,
        "migration_status": "not_started",
        "verification_status": "not_started",
        "rollback_version": None,
        "evidence": [],
    }


def _neutral_deployments(provider: str) -> dict[str, Any]:
    return {
        "provider": provider,
        "development": _neutral_deployment_target(),
        "production": _neutral_deployment_target(),
    }


def _synthesize_graph_state(plan: dict[str, Any]) -> dict[str, Any]:
    graph = plan.get("graph", {})
    node_states = {
        node["id"]: {
            "phase": "dormant",
            "attempts": 0,
            "last_attempt_id": None,
            "last_outcome": None,
            "bound_worker_id": None,
            "blockers": [],
        }
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    edge_states = {
        edge["id"]: {"status": "dormant", "traversals": 0, "source_attempt_id": None}
        for edge in graph.get("edges", [])
        if isinstance(edge, dict) and isinstance(edge.get("id"), str)
    }
    return {
        "graph_revision": plan.get("revision"),
        "node_states": node_states,
        "edge_states": edge_states,
    }


def _plan_declares_release(plan: dict[str, Any]) -> bool:
    return plan.get("schema_version") in {3, 4, 5} and "release" in plan


def _is_graph_run(plan: dict[str, Any]) -> bool:
    return plan.get("schema_version") in {4, 5}


def _neutral_gate_results(gates: Any) -> list[dict[str, Any]]:
    return [
        {"id": gate["id"], "status": "planned", "head_sha": None, "evidence": []}
        for gate in (gates or [])
        if isinstance(gate, dict) and isinstance(gate.get("id"), str)
    ]


def _upgrade_run_v2_to_v3(run: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    authorizations = run.setdefault("authorizations", {})
    for key in ("configure_repository", "manage_pr_review", "merge_pr"):
        authorizations[key] = {"authorized": False, "source": None}
    run["landing"] = _neutral_landing(auto_merge=False)
    run["schema_version"] = 3
    return [
        "authorizations.configure_repository",
        "authorizations.manage_pr_review",
        "authorizations.merge_pr",
        "landing",
    ]


def _upgrade_run_v3_to_v4(run: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    landing = run.setdefault("landing", {})
    landing["auto_merge_requested"] = False
    landing["auto_merge_head_sha"] = None
    run["schema_version"] = 4
    return ["landing.auto_merge_requested", "landing.auto_merge_head_sha"]


def _upgrade_run_v4_to_v5(run: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    run.setdefault("observed", {}).setdefault("git", {})["parent_worktree_path"] = None
    run["post_merge_cleanup"] = _neutral_post_merge_cleanup()
    run["schema_version"] = 5
    return ["observed.git.parent_worktree_path", "post_merge_cleanup"]


def _upgrade_run_v5_to_v6(run: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    run.setdefault("runtime_capabilities", {})["runtime_adapter"] = (
        _derive_runtime_adapter(run)
    )
    run["schema_version"] = 6
    return ["runtime_capabilities.runtime_adapter"]


def _upgrade_run_v6_to_v7(run: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    added: list[str] = []
    if _plan_declares_release(plan):
        run["deployments"] = _neutral_deployments(plan["release"]["provider"])
        added.append("deployments")
    run["schema_version"] = 7
    return added


def _upgrade_run_v7_to_v8(run: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    run.setdefault("authorizations", {})["invoke_external_runtime"] = {
        "authorized": False,
        "source": None,
    }
    added = ["authorizations.invoke_external_runtime"]
    if _is_graph_run(plan):
        run["graph_state"] = _synthesize_graph_state(plan)
        run["review_workers"] = []
        added.extend(["graph_state", "review_workers"])
    run["schema_version"] = 8
    return added


def _upgrade_run_v8_to_v9(run: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    run["batch_gate_results"] = _neutral_gate_results(plan.get("batch_verifiers"))
    run["final_gate_results"] = _neutral_gate_results(plan.get("final_gates"))
    run["ui_evidence"] = []
    added = ["batch_gate_results", "final_gate_results", "ui_evidence"]
    if _is_graph_run(plan):
        run["workflow_runs"] = []
        added.append("workflow_runs")
    run["schema_version"] = 9
    return added


def _neutral_target_v10() -> dict[str, Any]:
    return {
        "status": "not_started",
        "source_sha": None,
        "authorized_head_sha": None,
        "artifact": None,
        "channel": None,
        "promotion": None,
        "availability": None,
        "migration_status": "not_started",
        "verification_status": "not_started",
        "destructive_migration_confirmed_sha": None,
    }


def _upgrade_run_v9_to_v10(run: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    authorizations = run.get("authorizations")
    if run.get("status") == "complete":
        raise UpgradeError("completed RUN v9 remains readable historical state and is not rewritten")
    if run.get("execution_authorized") is True or (
        isinstance(authorizations, dict)
        and any(
            isinstance(entry, dict) and entry.get("authorized") is True
            for entry in authorizations.values()
        )
    ):
        raise UpgradeError(
            "cannot upgrade active authorization to RUN v10 without explicit plan-bound reaffirmation"
        )

    landing = run.get("landing")
    integration = run.get("integration")
    if isinstance(landing, dict) and landing.get("mode") == "local_only":
        head_branch = landing.get("head_branch")
        base_branch = landing.get("base_branch")
        integration_branch = integration.get("branch") if isinstance(integration, dict) else None
        normalized_head = (
            head_branch.removeprefix("refs/heads/")
            if isinstance(head_branch, str) and head_branch
            else None
        )
        normalized_base = (
            base_branch.removeprefix("refs/heads/")
            if isinstance(base_branch, str) and base_branch
            else None
        )
        normalized_integration = (
            integration_branch.removeprefix("refs/heads/")
            if isinstance(integration_branch, str) and integration_branch
            else None
        )
        if (
            normalized_head is None
            or normalized_head == normalized_base
            or normalized_head != normalized_integration
        ):
            raise UpgradeError(
                "cannot upgrade local_only RUN v9 without an exact distinct retained branch"
            )

    if isinstance(authorizations, dict):
        authorizations["trigger_remote_ci"] = {"authorized": False, "source": None}
        authorizations["provision_cloud_resources"] = {
            "authorized": False,
            "source": None,
        }
    if isinstance(landing, dict):
        landing["continuity"] = (
            {
                "status": "planned",
                "branch_ref": (
                    landing["head_branch"]
                    if str(landing["head_branch"]).startswith("refs/heads/")
                    else f"refs/heads/{landing['head_branch']}"
                ),
                "head_sha": None,
                "reason": None,
            }
            if landing.get("mode") == "local_only"
            else {
                "status": "not_required",
                "branch_ref": None,
                "head_sha": None,
                "reason": None,
            }
        )

    run["verifier_executions"] = []
    added = [
        "authorizations.trigger_remote_ci",
        "authorizations.provision_cloud_resources",
        "landing.continuity",
        "verifier_executions",
    ]
    if _plan_declares_release(plan):
        deployments = run.get("deployments")
        if isinstance(deployments, dict):
            progressed = [
                target_id
                for target_id in ("development", "production")
                if isinstance(deployments.get(target_id), dict)
                and deployments[target_id].get("status") != "not_started"
            ]
            if progressed:
                raise UpgradeError(
                    "cannot convert progressed legacy deployment state to RUN v10 "
                    "structured evidence without fabricating records: "
                    + ", ".join(progressed)
                )
        release = plan.get("release", {})
        targets = release.get("targets", []) if isinstance(release, dict) else []
        run["targets"] = {
            target["id"]: _neutral_target_v10()
            for target in targets
            if isinstance(target, dict) and isinstance(target.get("id"), str)
        }
        run.pop("deployments", None)
        added.extend(["targets", "removed deployments"])
    else:
        run.pop("deployments", None)
    run["schema_version"] = 10
    return added


_RUN_STEPS = {
    2: _upgrade_run_v2_to_v3,
    3: _upgrade_run_v3_to_v4,
    4: _upgrade_run_v4_to_v5,
    5: _upgrade_run_v5_to_v6,
    6: _upgrade_run_v6_to_v7,
    7: _upgrade_run_v7_to_v8,
    8: _upgrade_run_v8_to_v9,
    9: _upgrade_run_v9_to_v10,
}


# --- chain drivers ----------------------------------------------------------


def upgrade_plan(plan: dict[str, Any], repo_root: Path) -> list[tuple[int, int, list[str]]]:
    report: list[tuple[int, int, list[str]]] = []
    while True:
        current = plan.get("schema_version")
        if not isinstance(current, int) or current >= PLAN_MAX_SCHEMA:
            break
        step = _PLAN_STEPS.get(current)
        if step is None:
            break
        added = step(plan, repo_root)
        report.append((current, plan["schema_version"], added))
    return report


def upgrade_run(run: dict[str, Any], plan: dict[str, Any]) -> list[tuple[int, int, list[str]]]:
    report: list[tuple[int, int, list[str]]] = []
    while True:
        current = run.get("schema_version")
        if not isinstance(current, int) or current >= RUN_MAX_SCHEMA:
            break
        step = _RUN_STEPS.get(current)
        if step is None:
            break
        added = step(run, plan)
        report.append((current, run["schema_version"], added))
    return report


# --- manifest rewrite (fence-preserving) ------------------------------------


def _render_manifest(
    path: Path, heading: str, wrapper: str, manifest: dict[str, Any]
) -> bytes:
    """Render only the fenced JSON body; keep every other byte identical."""

    raw = path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.split(newline)
    positions = [index for index, line in enumerate(lines) if line.strip() == heading]
    if len(positions) != 1:
        raise ManifestError(f"{path}: expected exactly one {heading!r}")
    index = positions[0] + 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or lines[index].strip() != "```json":
        raise ManifestError(f"{path}: first content after {heading!r} must be ```json")
    start = index + 1
    end = start
    while end < len(lines) and lines[end].strip() != "```":
        end += 1
    if end >= len(lines):
        raise ManifestError(f"{path}: unterminated JSON fence after {heading!r}")
    body = json.dumps({wrapper: manifest}, indent=2, ensure_ascii=False)
    new_lines = lines[:start] + body.split("\n") + lines[end:]
    return newline.join(new_lines).encode("utf-8")


def _stage_sibling(path: Path, content: bytes, label: str) -> Path:
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.{label}.", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(temp_name)
    descriptor_open = True
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor_open = False
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        if descriptor_open:
            os.close(descriptor)
        temp_path.unlink(missing_ok=True)
        raise
    return temp_path


def _rewrite_manifests_atomically(
    rewrites: list[tuple[Path, str, str, dict[str, Any]]]
) -> None:
    """Stage every sibling replacement before changing any canonical manifest."""

    staged: list[tuple[Path, Path, Path]] = []
    replaced: list[tuple[Path, Path]] = []
    try:
        for path, heading, wrapper, manifest in rewrites:
            original = path.read_bytes()
            rendered = _render_manifest(path, heading, wrapper, manifest)
            replacement = _stage_sibling(path, rendered, "new")
            try:
                backup = _stage_sibling(path, original, "backup")
            except Exception:
                replacement.unlink(missing_ok=True)
                raise
            staged.append((path, replacement, backup))
        for path, replacement, backup in staged:
            os.replace(replacement, path)
            replaced.append((path, backup))
    except Exception as exc:
        rollback_errors: list[str] = []
        for path, backup in reversed(replaced):
            try:
                os.replace(backup, path)
            except OSError as rollback_exc:
                rollback_errors.append(f"{path}: {rollback_exc}")
        detail = ""
        if rollback_errors:
            detail = "; rollback failed for " + "; ".join(rollback_errors)
        raise UpgradeError(f"failed to write upgraded manifests: {exc}{detail}") from exc
    finally:
        for _, replacement, backup in staged:
            replacement.unlink(missing_ok=True)
            backup.unlink(missing_ok=True)


# --- CLI --------------------------------------------------------------------


def _format_steps(label: str, path: str, report: list[tuple[int, int, list[str]]]) -> list[str]:
    if not report:
        return []
    first_from = report[0][0]
    last_to = report[-1][1]
    out = [f"{label} {path}: schema {first_from} -> {last_to}"]
    for old, new, added in report:
        detail = ", ".join(added) if added else "version bump only (no new keys)"
        out.append(f"  v{old} -> v{new}: {detail}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Upgrade harness PLAN/RUN manifests to the current schema."
    )
    parser.add_argument("--plan", required=True, help="Path to PLAN.md")
    parser.add_argument("--run", help="Optional path to plan-backed RUN.md")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used to freeze source content and verify artifacts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the planned per-step additions without writing anything",
    )
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root)

    try:
        plan = load_plan(args.plan)
        run = load_run(args.run) if args.run else None
    except (OSError, ManifestError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    original_errors = validate_plan(plan)
    if run is not None and not original_errors:
        original_errors = validate_run(plan, run) + validate_ui_evidence_files(
            run, args.repo_root
        )
    if original_errors:
        sys.stderr.write("refusing to upgrade an invalid manifest:\n")
        for error in original_errors:
            sys.stderr.write(f"  {error}\n")
        return 1

    plan_from = plan["schema_version"]
    run_from = run["schema_version"] if run is not None else None
    if plan_from >= PLAN_MAX_SCHEMA and (run is None or run_from >= RUN_MAX_SCHEMA):
        sys.stdout.write("already current: nothing to upgrade\n")
        return 0

    upgraded_plan = copy.deepcopy(plan)
    upgraded_run = copy.deepcopy(run) if run is not None else None
    try:
        plan_report = upgrade_plan(upgraded_plan, repo_root)
        run_report: list[tuple[int, int, list[str]]] = []
        if upgraded_run is not None:
            run_report = upgrade_run(upgraded_run, upgraded_plan)
    except UpgradeError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    plan_changed = bool(plan_report)
    digest_synced = False
    if upgraded_run is not None:
        upgraded_run["plan"]["id"] = upgraded_plan["plan_id"]
        upgraded_run["plan"]["revision"] = upgraded_plan["revision"]
        new_digest = plan_digest(upgraded_plan)
        if upgraded_run["plan"].get("digest_sha256") != new_digest:
            upgraded_run["plan"]["digest_sha256"] = new_digest
            digest_synced = True

    post_errors = validate_plan(upgraded_plan)
    if upgraded_run is not None and not post_errors:
        post_errors = validate_run(upgraded_plan, upgraded_run) + validate_ui_evidence_files(
            upgraded_run, args.repo_root
        )
    if post_errors:
        sys.stderr.write("upgrade produced an invalid manifest; nothing written:\n")
        for error in post_errors:
            sys.stderr.write(f"  {error}\n")
        return 1

    run_changed = bool(run_report) or digest_synced
    if not args.dry_run:
        rewrites: list[tuple[Path, str, str, dict[str, Any]]] = []
        if plan_changed:
            rewrites.append(
                (Path(args.plan), PLAN_HEADING, "harness_plan", upgraded_plan)
            )
        if upgraded_run is not None and run_changed:
            rewrites.append(
                (Path(args.run), RUN_HEADING, "harness_run", upgraded_run)
            )
        try:
            _rewrite_manifests_atomically(rewrites)
        except (OSError, ManifestError, UpgradeError) as exc:
            sys.stderr.write(f"{exc}\n")
            return 1

    summary: list[str] = []
    if plan_changed:
        summary.extend(_format_steps("PLAN", args.plan, plan_report))
    else:
        summary.append(f"PLAN {args.plan}: already at schema {plan_from}")
    if upgraded_run is not None:
        if run_report:
            summary.extend(_format_steps("RUN", args.run, run_report))
        else:
            summary.append(f"RUN {args.run}: already at schema {run_from}")
        if digest_synced:
            summary.append("  synced run.plan.digest_sha256 to the upgraded PLAN")
    if args.dry_run:
        summary.append("[dry-run] no files written")
    sys.stdout.write("\n".join(summary) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

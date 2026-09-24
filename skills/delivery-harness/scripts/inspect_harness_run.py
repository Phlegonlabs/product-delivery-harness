#!/usr/bin/env python3
"""Summarize canonical RUN state against live Git worktrees."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from harness_core import ManifestError, _nonempty_string, is_full_sha, load_run
from harness_git import GitMetadataError, reject_object_substitution, run_git
from harness_ui_evidence import _layout_check_required


FAILED_ATTEMPT_RESULTS = {"fix_required", "retryable_failure", "blocked", "contract_gap"}


def _git(
    worktree: Path,
    *args: str,
    guard_failures: list[str] | None = None,
) -> str | None:
    try:
        reject_object_substitution(worktree)
        result = run_git(worktree, *args, check=False, text=True)
    except GitMetadataError:
        if guard_failures is not None:
            guard_failures.append(
                "parent: Git observation blocked by metadata/configuration guard"
            )
        return None
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _normalized_branch(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().removeprefix("refs/heads/")


def _parent_git_summary(
    repo_root: Path, run: dict[str, Any], run_path: Path | None = None
) -> tuple[dict[str, Any], list[str]]:
    """Compare live parent Git facts with the canonical integration identity."""
    integration = run.get("integration")
    integration = integration if isinstance(integration, dict) else {}
    observed = run.get("observed")
    observed = observed if isinstance(observed, dict) else {}
    observed_git = observed.get("git")
    observed_git = observed_git if isinstance(observed_git, dict) else {}

    guard_failures: list[str] = []
    try:
        repository_probe = run_git(
            repo_root,
            "rev-parse",
            "--is-inside-work-tree",
            check=False,
            text=True,
        )
    except GitMetadataError:
        repository_available = False
        guard_failures.append(
            "parent: Git observation blocked by metadata/configuration guard"
        )
    except OSError:
        repository_available = False
    else:
        repository_available = (
            repository_probe.returncode == 0
            and repository_probe.stdout.strip().casefold() == "true"
        )

    live_head = (
        _git(repo_root, "rev-parse", "HEAD", guard_failures=guard_failures)
        if repository_available
        else None
    )
    live_branch = (
        _git(
            repo_root,
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
            guard_failures=guard_failures,
        )
        if repository_available
        else None
    )
    porcelain = (
        _git(
            repo_root,
            "status",
            "--porcelain",
            "--untracked-files=all",
            guard_failures=guard_failures,
        )
        if repository_available
        else None
    )
    if porcelain and run_path is not None:
        try:
            relative_run_path = run_path.resolve().relative_to(repo_root.resolve())
        except (OSError, ValueError):
            pass
        else:
            run_status = _git(
                repo_root,
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                f":(top,literal){relative_run_path.as_posix()}",
                guard_failures=guard_failures,
            )
            if (
                run_status == porcelain
                and run_status[:2] in {" M", "M ", "MM"}
            ):
                porcelain = ""
    live_dirty = bool(porcelain) if porcelain is not None else None
    required_observation_incomplete = bool(
        repository_available
        and (live_head is None or live_branch is None or porcelain is None)
    )

    integration_branch = _normalized_branch(integration.get("branch"))
    integration_head = integration.get("integration_head_sha")
    integration_head = integration_head if is_full_sha(integration_head) else None
    recorded_parent_branch = _normalized_branch(observed_git.get("parent_branch"))
    recorded_parent_head = observed_git.get("parent_head_sha")
    recorded_parent_head = (
        recorded_parent_head if is_full_sha(recorded_parent_head) else None
    )
    branch_matches = (
        live_branch == integration_branch
        if live_branch is not None and integration_branch is not None
        else None
    )
    head_matches = (
        live_head == integration_head
        if live_head is not None and integration_head is not None
        else None
    )
    branch_matches_recorded_parent = (
        live_branch == recorded_parent_branch
        if live_branch is not None and recorded_parent_branch is not None
        else None
    )
    head_matches_recorded_parent = (
        live_head == recorded_parent_head
        if live_head is not None and recorded_parent_head is not None
        else None
    )
    integration_object_exists = (
        _git(
            repo_root,
            "cat-file",
            "-e",
            f"{integration_head}^{{commit}}",
            guard_failures=guard_failures,
        )
        is not None
        if live_head is not None and integration_head is not None
        else None
    )

    warnings: list[str] = list(dict.fromkeys(guard_failures))
    if required_observation_incomplete and not guard_failures:
        warnings.append("parent: live Git observation is incomplete")
    if branch_matches is False:
        warnings.append(
            "parent: live branch "
            f"{live_branch} differs from integration branch {integration_branch}"
        )
    elif integration_branch is None and branch_matches_recorded_parent is False:
        warnings.append(
            "parent: live branch "
            f"{live_branch} differs from recorded parent branch {recorded_parent_branch}"
        )
    if head_matches is False:
        warnings.append(
            "parent: live HEAD "
            f"{live_head} differs from integration head {integration_head}"
        )
    elif integration_head is None and head_matches_recorded_parent is False:
        warnings.append(
            "parent: live HEAD "
            f"{live_head} differs from recorded parent head {recorded_parent_head}"
        )
    if integration_object_exists is False:
        warnings.append(
            f"parent: canonical integration object {integration_head} is missing locally"
        )
    if live_dirty is True:
        warnings.append("parent: live integration checkout is dirty")

    if guard_failures:
        comparison_state = "blocked"
    elif required_observation_incomplete:
        comparison_state = "partial"
    elif live_head is None:
        comparison_state = "unknown"
    elif warnings:
        comparison_state = "mismatch"
    elif (
        branch_matches is True
        and head_matches is True
        and integration_object_exists is True
    ):
        comparison_state = "aligned"
    else:
        comparison_state = "partial"

    return {
        "recorded_parent_worktree_path": observed_git.get("parent_worktree_path"),
        "recorded_parent_branch": recorded_parent_branch,
        "recorded_parent_head_sha": recorded_parent_head,
        "recorded_parent_dirty": observed_git.get("parent_dirty"),
        "live_worktree_path": str(repo_root) if repo_root.exists() else None,
        "live_branch": live_branch,
        "live_head_sha": live_head,
        "live_dirty": live_dirty,
        "git_observation_status": (
            "blocked"
            if guard_failures
            else "available"
            if repository_available and not required_observation_incomplete
            else "unavailable"
        ),
        "integration_branch": integration_branch,
        "integration_head_sha": integration_head,
        "integration_object_exists": integration_object_exists,
        "branch_matches_integration": branch_matches,
        "head_matches_integration": head_matches,
        "branch_matches_recorded_parent": branch_matches_recorded_parent,
        "head_matches_recorded_parent": head_matches_recorded_parent,
        "comparison_state": comparison_state,
        "needs_reconciliation": bool(warnings),
        "runtime_process_liveness": "unknown",
    }, warnings


def _attestation_summary(run: dict[str, Any]) -> dict[str, Any]:
    """Count parent-attested UI records and name failing or missing entries."""

    def row_key(row: dict[str, Any]) -> str:
        return "/".join(
            str(row.get(part)) for part in ("surface_id", "route", "breakpoint", "state")
        )

    def rows(key: str) -> list[dict[str, Any]]:
        return [row for row in run.get(key) or [] if isinstance(row, dict)]

    evidence = rows("ui_evidence")
    layout_required = _layout_check_required(run)
    ledger = rows("deviation_ledger")
    impacts = rows("ui_impact_summary")
    return {
        "ui_evidence_rows": len(evidence),
        "layout_check_failing_or_missing": [
            row_key(row)
            for row in evidence
            if str(row.get("layout_check") or "").startswith("fail")
            or (layout_required and not _nonempty_string(row.get("layout_check")))
        ],
        "deviation_ledger_rows": len(ledger),
        "ledger_rows_missing_citation": [
            row_key(row) for row in ledger if not _nonempty_string(row.get("citation"))
        ],
        "ui_impact_summary_rows": len(impacts),
        "impact_rows_missing_doc_delta": [
            row.get("mission_id")
            for row in impacts
            if row.get("impact") in {"structure", "both"}
            and not _nonempty_string(row.get("doc_delta"))
        ],
    }


def _failure_snapshot(attempt: dict[str, Any]) -> dict[str, Any]:
    evidence = attempt.get("evidence")
    return {
        "attempt_id": attempt.get("attempt_id"),
        "kind": attempt.get("kind"),
        "result": attempt.get("result"),
        "evidence": [
            item for item in evidence if isinstance(item, str)
        ] if isinstance(evidence, list) else [],
    }


def _attempt_recovery_summary(
    run: dict[str, Any], mission_ids: set[str]
) -> dict[str, Any]:
    """Read retained failure evidence without changing state or inferring liveness."""

    raw_attempts = run.get("attempt_log")
    attempts = raw_attempts if isinstance(raw_attempts, list) else []
    malformed_entries = (
        0 if raw_attempts is None
        else sum(not isinstance(attempt, dict) for attempt in attempts)
    )
    failures: dict[str, dict[str, Any] | None] = {
        mission_id: None for mission_id in mission_ids
    }
    failed_dispatch_counts: dict[str, int] = {
        mission_id: 0 for mission_id in mission_ids
    }
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        mission_id = attempt.get("mission_id")
        if not isinstance(mission_id, str):
            continue
        result = (
            attempt.get("result").casefold()
            if isinstance(attempt.get("result"), str)
            else None
        )
        if result not in FAILED_ATTEMPT_RESULTS:
            continue
        failure = _failure_snapshot(attempt)
        failures[mission_id] = failure
        if attempt.get("kind") == "dispatch":
            failed_dispatch_counts[mission_id] = failed_dispatch_counts.get(mission_id, 0) + 1
    return {
        "attempt_log_present": raw_attempts is not None,
        "attempt_log_valid": raw_attempts is None or isinstance(raw_attempts, list),
        "observed_entries": len(attempts),
        "malformed_entries": malformed_entries,
        "runtime_process_liveness": "unknown",
        "missions": [
            {
                "mission_id": mission_id,
                "failed_dispatch_count": failed_dispatch_counts.get(mission_id, 0),
                "most_recent_failure": failures.get(mission_id),
            }
            for mission_id in sorted(set(mission_ids) | set(failures))
        ],
    }


def _next_recovery_steps(summary: dict[str, Any]) -> list[str]:
    recovery = summary.get("attempt_recovery") or {}
    has_failure = any(
        item.get("most_recent_failure") is not None
        for item in recovery.get("missions", [])
    )
    if not summary["warnings"] and not has_failure:
        return []
    return [
        "Use inspect_harness_run.py --json and preserve retained attempt, grant, and verifier contexts.",
        "Confirm process/session liveness with the owning runtime first; dirty work alone does not prove interruption.",
        "Only after confirming interruption, use reconcile-interrupted or reconcile-interrupted-reviews with the required RUN lock.",
        "Use record-node-result or record-worker-result only for the matching current reserved attempt or lease; new work needs a new attempt, never rewritten history.",
    ]


def _runtime_metrics_summary(run: dict[str, Any]) -> dict[str, Any]:
    """Keep measured phase sums separate from unknown full-run intervals."""
    raw = run.get("runtime_metrics")
    metrics = raw if isinstance(raw, dict) else {}
    raw_events = metrics.get("events")
    events = raw_events if isinstance(raw_events, list) else []
    phases: dict[str, dict[str, Any]] = {}
    malformed = 0
    for event in events:
        phase = event.get("phase") if isinstance(event, dict) else None
        if not isinstance(phase, str) or not phase:
            malformed += 1
            continue
        row = phases.setdefault(phase, {
            "phase": phase, "event_count": 0,
            "measured_duration_ms": None, "unknown_duration_count": 0,
        })
        row["event_count"] += 1
        duration = event.get("duration_ms")
        if type(duration) is int and duration >= 0:
            row["measured_duration_ms"] = (row["measured_duration_ms"] or 0) + duration
        else:
            row["unknown_duration_count"] += 1
    return {
        "present": raw is not None,
        "event_count": len(events),
        "malformed_events": malformed,
        "phase_events": [phases[phase] for phase in sorted(phases)],
        **{key: metrics.get(key) if type(metrics.get(key)) is int and metrics[key] >= 0 else None
           for key in ("baseline_wall_time_ms", "run_wall_time_ms", "critical_path_ms")},
        "meaning": "Phase duration sums are partial observations, not run wall time or critical path.",
    }


def _verifier_timings_summary(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose each execution's observations without adding overlapping intervals."""
    executions = run.get("verifier_executions")
    return [
        {"verifier_id": execution.get("verifier_id"),
         "execution_key": execution.get("execution_key"),
         "timings": copy.deepcopy(execution["timings"])}
        for execution in executions if isinstance(execution, dict)
        and isinstance(execution.get("timings"), dict)
    ] if isinstance(executions, list) else []


def summarize_run(
    repo_root: Path, run: dict[str, Any], run_path: Path | None = None
) -> dict[str, Any]:
    runtime_capabilities = run.get("runtime_capabilities")
    runtime_adapter = (
        runtime_capabilities.get("runtime_adapter")
        if isinstance(runtime_capabilities, dict)
        else None
    )
    version_gate = (
        runtime_adapter.get("version_gate")
        if isinstance(runtime_adapter, dict)
        else None
    )
    workers = {
        item.get("mission_id"): item
        for item in run.get("workers", [])
        if isinstance(item, dict) and isinstance(item.get("mission_id"), str)
    }
    mission_ids: set[str] = {
        mission_id
        for mission_id in run.get("mission_states", {})
        if isinstance(mission_id, str)
    }
    recovery = _attempt_recovery_summary(run, mission_ids)
    missions: list[dict[str, Any]] = []
    warnings: list[str] = []
    parent_git, parent_warnings = _parent_git_summary(repo_root, run, run_path)

    for mission_id, state in sorted(run.get("mission_states", {}).items()):
        if not isinstance(state, dict):
            continue
        worker = workers.get(mission_id, {})
        raw_path = worker.get("worktree_path")
        worktree = (
            Path(raw_path)
            if isinstance(raw_path, str) and raw_path.strip()
            else None
        )
        if worktree is not None and not worktree.is_absolute():
            worktree = repo_root / worktree

        live_head = _git(worktree, "rev-parse", "HEAD") if worktree and worktree.exists() else None
        porcelain = (
            _git(worktree, "status", "--porcelain")
            if worktree and worktree.exists()
            else None
        )
        live_dirty = bool(porcelain) if porcelain is not None else None
        recorded_head = state.get("head_sha")
        head_drift = bool(
            live_head
            and isinstance(recorded_head, str)
            and live_head != recorded_head
        )
        dirty_drift = live_dirty is True
        phase = state.get("phase")
        worktree_required = phase in {
            "leased",
            "worker_running",
            "worker_passed",
            "integrating",
        }
        worktree_unavailable = worktree_required and (
            worktree is None or live_head is None or porcelain is None
        )
        needs_reconciliation = head_drift or dirty_drift or worktree_unavailable

        if needs_reconciliation:
            historical_drift = phase in {"integrated", "superseded"}
            reasons = []
            if head_drift:
                reasons.append(
                    "superseded or historical head drift"
                    if historical_drift
                    else "head advanced or diverged"
                )
            if dirty_drift:
                reasons.append(
                    "superseded or historical worktree drift"
                    if historical_drift
                    else "worktree dirty (process liveness unknown)"
                )
            if worktree_unavailable:
                reasons.append("worktree unavailable")
            warnings.append(f"{mission_id}: {', '.join(reasons)}")

        missions.append(
            {
                "mission_id": mission_id,
                "phase": phase,
                "recorded_head_sha": recorded_head,
                "live_head_sha": live_head,
                "live_dirty": live_dirty,
                "worktree_path": str(worktree) if worktree else None,
                "needs_reconciliation": needs_reconciliation,
                "drift_class": (
                    "superseded_or_historical"
                    if needs_reconciliation and historical_drift
                    else "active" if needs_reconciliation else None
                ),
                "runtime_process_liveness": "unknown",
            }
        )

    warnings.extend(parent_warnings)
    wave = run.get("active_wave")
    lock = run.get("run_lock")
    control = run.get("control")
    return {
        "run_id": run.get("run_id"),
        "schema_version": run.get("schema_version"),
        "status": run.get("status"),
        "control_desired_state": control.get("desired_state")
        if isinstance(control, dict)
        else None,
        "run_lock": lock if isinstance(lock, dict) else None,
        "active_wave": {
            "wave_id": wave.get("wave_id"),
            "status": wave.get("status"),
            "selected_missions": wave.get("selected_missions", []),
        }
        if isinstance(wave, dict)
        else None,
        "integration": run.get("integration"),
        "parent_git": parent_git,
        "runtime_process_state": "not inspected",
        "runtime_process_liveness": "unknown",
        "runtime_version_gate": version_gate if isinstance(version_gate, dict) else None,
        "runtime_metrics": _runtime_metrics_summary(run),
        "verifier_timings": _verifier_timings_summary(run),
        "missions": missions,
        "attempt_recovery": recovery,
        "attestations": _attestation_summary(run),
        "warnings": warnings,
        "next_recovery_steps": _next_recovery_steps(
            {"warnings": warnings, "attempt_recovery": recovery}
        ),
    }


def render_text(summary: dict[str, Any]) -> str:
    wave = summary.get("active_wave") or {}
    version_gate = summary.get("runtime_version_gate") or {}
    lock = summary.get("run_lock") or {}
    lines = [
        f"Run: {summary.get('run_id')} ({summary.get('status')})",
        f"Control: {summary.get('control_desired_state') or '-'}",
        "Run lock: "
        + (
            f"session={lock.get('session_id')} heartbeat={lock.get('heartbeat_at')}"
            if lock
            else "none"
        ),
        f"Wave: {wave.get('wave_id') or '-'} ({wave.get('status') or '-'})",
        "Runtime processes: not inspected; process liveness unknown",
        "Runtime version gate: "
        f"{version_gate.get('status') or 'unrecorded'} | "
        f"host={version_gate.get('host_version') or '-'} | "
        f"harness={version_gate.get('harness_version') or '-'} | "
        f"required={version_gate.get('required_harness_version') or '-'}",
    ]
    parent_git = summary.get("parent_git") or {}
    parent_dirty = (
        "dirty"
        if parent_git.get("live_dirty") is True
        else "clean"
        if parent_git.get("live_dirty") is False
        else "unknown"
    )
    integration_object = (
        "present"
        if parent_git.get("integration_object_exists") is True
        else "missing"
        if parent_git.get("integration_object_exists") is False
        else "unknown"
    )
    lines.append(
        "Parent Git: "
        f"{parent_git.get('comparison_state') or 'unknown'} | "
        f"branch={parent_git.get('live_branch') or '-'} | "
        f"head={parent_git.get('live_head_sha') or '-'} | "
        f"{parent_dirty} | "
        f"integration_branch={parent_git.get('integration_branch') or '-'} | "
        f"integration_head={parent_git.get('integration_head_sha') or '-'} | "
        f"integration_object={integration_object}"
    )
    metrics = summary.get("runtime_metrics") or {}
    def milliseconds(value: Any) -> str:
        return "unknown" if value is None else f"{value}ms"

    lines.append(
        "Runtime metrics: "
        f"run_wall={milliseconds(metrics.get('run_wall_time_ms'))} | "
        f"critical_path={milliseconds(metrics.get('critical_path_ms'))} | "
        f"baseline={milliseconds(metrics.get('baseline_wall_time_ms'))}"
    )
    for phase in metrics.get("phase_events", []):
        lines.append(
            f"Phase {phase['phase']}: events={phase['event_count']} | "
            f"measured_sum={milliseconds(phase['measured_duration_ms'])} | "
            f"unknown_durations={phase['unknown_duration_count']}"
        )
    for execution in summary.get("verifier_timings", []):
        lines.append(
            f"Verifier timings {execution['verifier_id']} ({execution['execution_key']}): "
            + json.dumps(execution["timings"], sort_keys=True)
        )
    for mission in summary["missions"]:
        marker = "RECONCILE" if mission["needs_reconciliation"] else "aligned"
        dirty = (
            "dirty"
            if mission["live_dirty"] is True
            else "clean"
            if mission["live_dirty"] is False
            else "unknown"
        )
        lines.append(
            f"{mission['mission_id']}: {mission['phase']} | {marker} | "
            f"{dirty} | recorded={mission['recorded_head_sha'] or '-'} | "
            f"live={mission['live_head_sha'] or '-'}"
        )
    recovery = summary.get("attempt_recovery") or {}
    lines.append(
        "Attempt recovery: "
        f"log={recovery.get('attempt_log_present', False)} | "
        f"valid={recovery.get('attempt_log_valid', True)} | "
        f"entries={recovery.get('observed_entries', 0)} | "
        f"malformed={recovery.get('malformed_entries', 0)} | "
        f"process liveness={recovery.get('runtime_process_liveness', 'unknown')}"
    )
    for mission_recovery in recovery.get("missions", []):
        failure = mission_recovery.get("most_recent_failure")
        evidence = failure.get("evidence", []) if failure else []
        lines.append(
            f"{mission_recovery['mission_id']}: failed_dispatches="
            f"{mission_recovery.get('failed_dispatch_count', 0)} | "
            f"latest={failure.get('attempt_id') if failure else '-'} | "
            f"evidence={', '.join(evidence) if evidence else '-'}"
        )
    if summary["warnings"]:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in summary["warnings"])
    if summary.get("next_recovery_steps"):
        lines.append("Recovery next steps:")
        lines.extend(f"- {step}" for step in summary["next_recovery_steps"])
    attestations = summary.get("attestations") or {}
    lines.append(
        "UI attestations: "
        f"evidence={attestations.get('ui_evidence_rows', 0)} | "
        f"ledger={attestations.get('deviation_ledger_rows', 0)} | "
        f"impact={attestations.get('ui_impact_summary_rows', 0)}"
    )
    for label, entries in (
        (
            "layout_check failing/missing",
            attestations.get("layout_check_failing_or_missing"),
        ),
        ("ledger rows missing citation", attestations.get("ledger_rows_missing_citation")),
        ("impact rows missing doc_delta", attestations.get("impact_rows_missing_doc_delta")),
    ):
        if entries:
            lines.append(f"- {label}: {', '.join(str(entry) for entry in entries)}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare a Harness RUN manifest with live Git worktrees."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument(
        "--run",
        type=Path,
        help="RUN.md path; defaults to <repo-root>/docs/goal/RUN.md",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    run_path = (args.run or repo_root / "docs" / "goal" / "RUN.md").resolve()
    try:
        summary = summarize_run(repo_root, load_run(run_path), run_path)
    except (GitMetadataError, OSError, ManifestError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(render_text(summary))
    return 1 if summary["warnings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

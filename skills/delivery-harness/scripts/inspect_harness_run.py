#!/usr/bin/env python3
"""Summarize canonical RUN state against live Git worktrees."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from harness_core import ManifestError, _nonempty_string, load_run
from harness_ui_evidence import _layout_check_required


def _git(worktree: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(worktree), *args],
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


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


def summarize_run(repo_root: Path, run: dict[str, Any]) -> dict[str, Any]:
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
    missions: list[dict[str, Any]] = []
    warnings: list[str] = []

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
            reasons = []
            if head_drift:
                reasons.append("head advanced or diverged")
            if dirty_drift:
                reasons.append("worktree dirty")
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
            }
        )

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
        "runtime_process_state": "not inspected",
        "runtime_version_gate": version_gate if isinstance(version_gate, dict) else None,
        "missions": missions,
        "attestations": _attestation_summary(run),
        "warnings": warnings,
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
        "Runtime processes: not inspected",
        "Runtime version gate: "
        f"{version_gate.get('status') or 'unrecorded'} | "
        f"host={version_gate.get('host_version') or '-'} | "
        f"harness={version_gate.get('harness_version') or '-'} | "
        f"required={version_gate.get('required_harness_version') or '-'}",
    ]
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
    if summary["warnings"]:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in summary["warnings"])
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
        summary = summarize_run(repo_root, load_run(run_path))
    except (OSError, ManifestError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(render_text(summary))
    return 1 if summary["warnings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Summarize canonical RUN state against live Git worktrees."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from harness_core import ManifestError, load_run


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


def summarize_run(repo_root: Path, run: dict[str, Any]) -> dict[str, Any]:
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
    return {
        "run_id": run.get("run_id"),
        "schema_version": run.get("schema_version"),
        "status": run.get("status"),
        "active_wave": {
            "wave_id": wave.get("wave_id"),
            "status": wave.get("status"),
            "selected_missions": wave.get("selected_missions", []),
        }
        if isinstance(wave, dict)
        else None,
        "integration": run.get("integration"),
        "runtime_process_state": "not inspected",
        "missions": missions,
        "warnings": warnings,
    }


def render_text(summary: dict[str, Any]) -> str:
    wave = summary.get("active_wave") or {}
    lines = [
        f"Run: {summary.get('run_id')} ({summary.get('status')})",
        f"Wave: {wave.get('wave_id') or '-'} ({wave.get('status') or '-'})",
        "Runtime processes: not inspected",
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

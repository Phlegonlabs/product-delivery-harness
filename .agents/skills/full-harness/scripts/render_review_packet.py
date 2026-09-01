#!/usr/bin/env python3
"""Render a deterministic, bounded review packet for one review node."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from harness_manifest import ManifestError, load_plan, load_run, validate_current_plan_run


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise ManifestError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def render_packet(
    plan: dict[str, Any],
    run: dict[str, Any],
    node_id: str,
    repo_root: Path,
    *,
    max_diff_bytes: int = 50000,
) -> str:
    node = next(
        (item for item in plan["graph"]["nodes"] if item.get("id") == node_id),
        None,
    )
    if not isinstance(node, dict) or not isinstance(node.get("review"), dict):
        raise ManifestError(f"{node_id!r} is not a runtime review node")
    review = node["review"]
    lineage = run["review_lineages"][review["lineage_id"]]
    mission_ids = set(review["mission_ids"])
    missions = [item for item in plan["missions"] if item["id"] in mission_ids]
    base = run["integration"].get("batch_base_sha")
    head = run["integration"].get("integration_head_sha")
    if review.get("stage", "preintegration") == "preintegration" and len(missions) == 1:
        head = run["mission_states"][missions[0]["id"]].get("head_sha") or head
    if not isinstance(base, str) or not isinstance(head, str):
        raise ManifestError("review packet requires concrete base and reviewed head SHAs")
    diff = _git(repo_root, "diff", "--no-ext-diff", f"{base}..{head}")
    encoded = diff.encode("utf-8")
    truncated = len(encoded) > max_diff_bytes
    if truncated:
        diff = encoded[:max_diff_bytes].decode("utf-8", errors="replace")
    acceptance = [
        {"task_id": task["id"], "acceptance_matrix": task["acceptance_matrix"]}
        for mission in missions
        for task in mission["tasks"]
    ]
    summary = _git(repo_root, "diff", "--stat", f"{base}..{head}").strip()
    changed = _git(repo_root, "diff", "--name-only", f"{base}..{head}").strip()
    return "\n".join(
        [
            f"# Review packet: {node_id}",
            "",
            f"- Reviewed head: `{head}`",
            f"- Base: `{base}`",
            f"- Lineage: `{review['lineage_id']}` ({lineage['consumed_attempts']}/{lineage['base_allowance'] + lineage['additional_allowance']} consumed)",
            f"- Scope: {', '.join(review['scope'])}",
            "",
            "## Contract",
            "",
            "```json",
            json.dumps(
                {
                    "required_evidence": review["required_evidence"],
                    "acceptance": acceptance,
                    "failure_families": lineage["failure_families"],
                    "owner_decisions": lineage["owner_decisions"],
                },
                indent=2,
                ensure_ascii=False,
            ),
            "```",
            "",
            "## Changed files",
            "",
            changed or "(none)",
            "",
            "## Diff stat",
            "",
            summary or "(none)",
            "",
            f"## Diff{' (truncated)' if truncated else ''}",
            "",
            "```diff",
            diff.rstrip(),
            "```",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--max-diff-bytes", type=int, default=50000)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        plan = load_plan(args.plan)
        run = load_run(args.run)
        errors = validate_current_plan_run(plan, run, repo_root=args.repo_root)
        if errors:
            raise ManifestError("invalid PLAN/RUN:\n" + "\n".join(errors))
        packet = render_packet(plan, run, args.node, args.repo_root, max_diff_bytes=args.max_diff_bytes)
        if args.out:
            if args.out.exists():
                raise ManifestError(f"refusing to overwrite {args.out}")
            args.out.write_text(packet, encoding="utf-8", newline="\n")
            print(f"wrote {args.out}")
        else:
            print(packet, end="")
    except (ManifestError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

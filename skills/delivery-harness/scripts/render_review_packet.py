#!/usr/bin/env python3
"""Render a deterministic, bounded review packet for one review node."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from harness_git import GitMetadataError, reject_object_substitution, run_git
from harness_graph import ui_acceptance_review
from harness_manifest import ManifestError, load_plan, load_run, validate_current_plan_run
from check_launch_packet import (
    InvalidMessageBudgetError,
    MessageBudgetOverflowError,
    check_message,
)


def validate_artifact_path(path: Path, repo_root: Path) -> None:
    """Review sidecars cannot dirty the reviewed checkout or replace data."""

    try:
        path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        pass
    else:
        raise ManifestError("full diff artifacts must live outside the reviewed checkout")
    if path.exists():
        raise ManifestError(f"refusing to overwrite {path}")
    if not path.parent.is_dir():
        raise ManifestError(f"diff artifact parent directory does not exist: {path.parent}")


def write_diff_artifact(path: Path, data: bytes) -> None:
    try:
        with path.open("xb") as stream:
            stream.write(data)
    except OSError as exc:
        raise ManifestError(f"full diff write failed at {path}; preserve any partial file and use a new output path: {exc}") from exc


def _git(repo: Path, *args: str) -> str:
    result = run_git(repo, *args, text=True, timeout=30)
    if result.returncode != 0:
        raise ManifestError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def _relevant_acceptance_mappings(
    plan: dict[str, Any], missions: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], bool]:
    """Return a bounded gate-to-TEST map for the reviewed mission slice."""

    reviewed_tests = {
        row.get("test_id")
        for mission in missions
        for task in mission.get("tasks", [])
        if isinstance(task, dict)
        for row in task.get("acceptance_matrix", [])
        if isinstance(row, dict) and isinstance(row.get("test_id"), str)
    }
    candidates: list[dict[str, Any]] = []
    for gate in plan.get("final_gates", []):
        if not isinstance(gate, dict):
            continue
        test_ids = gate.get("acceptance_test_ids", [])
        if isinstance(test_ids, list) and reviewed_tests.intersection(test_ids):
            candidates.append(
                {
                    "layer": "final",
                    "verifier_id": gate.get("id"),
                    "acceptance_test_ids": sorted(
                        item for item in test_ids if isinstance(item, str)
                    ),
                }
            )
    for mission in plan.get("missions", []):
        if not isinstance(mission, dict):
            continue
        for verifier in mission.get("integration_verifiers", []):
            if not isinstance(verifier, dict):
                continue
            test_ids = verifier.get("acceptance_test_ids", [])
            if isinstance(test_ids, list) and reviewed_tests.intersection(test_ids):
                candidates.append(
                    {
                        "layer": "mission_integration",
                        "mission_id": mission.get("id"),
                        "verifier_id": verifier.get("id"),
                        "acceptance_test_ids": sorted(
                            item for item in test_ids if isinstance(item, str)
                        ),
                    }
                )
    return candidates[:100], len(candidates) > 100


def render_packet(
    plan: dict[str, Any],
    run: dict[str, Any],
    node_id: str,
    repo_root: Path,
    *,
    max_diff_bytes: int = 50000,
    max_message_bytes: int | None = None,
    diff_artifact_out: Path | None = None,
    artifacts: list[tuple[Path, bytes]] | None = None,
) -> str:
    if max_message_bytes is not None:
        try:
            check_message("", max_message_bytes)
        except InvalidMessageBudgetError as exc:
            raise ManifestError(f"invalid review packet budget: {exc}") from exc
    if max_diff_bytes < 1:
        raise ManifestError("--max-diff-bytes must be positive")
    if diff_artifact_out is not None:
        validate_artifact_path(diff_artifact_out, repo_root)
    try:
        reject_object_substitution(repo_root)
    except (GitMetadataError, OSError) as exc:
        raise ManifestError(str(exc)) from exc
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
    if diff_artifact_out is not None and review.get("stage", "preintegration") == "preintegration":
        worker_ids = {run.get("mission_states", {}).get(mission["id"], {}).get("worker_id") for mission in missions}
        for worker in run.get("workers", []):
            if isinstance(worker, dict) and worker.get("worker_id") in worker_ids and isinstance(worker.get("worktree_path"), str):
                validate_artifact_path(diff_artifact_out, Path(worker["worktree_path"]))
    base = run["integration"].get("batch_base_sha")
    head = run["integration"].get("integration_head_sha")
    if review.get("stage", "preintegration") == "preintegration" and len(missions) == 1:
        head = run["mission_states"][missions[0]["id"]].get("head_sha") or head
    if not isinstance(base, str) or not isinstance(head, str):
        raise ManifestError("review packet requires concrete base and reviewed head SHAs")
    diff_args = ("diff", "--no-ext-diff", "--no-textconv", "--binary",
                 "--full-index", "--no-color", "--find-renames=50%",
                 "--src-prefix=a/", "--dst-prefix=b/", f"{base}..{head}")
    result = run_git(repo_root, *diff_args, text=False, timeout=30)
    if result.returncode != 0:
        raise ManifestError("cannot read full review diff")
    encoded = result.stdout
    diff = encoded.decode("utf-8", errors="replace")
    pending_artifacts: list[tuple[Path, bytes]] = []
    diff_artifact = None
    if diff_artifact_out is not None:
        diff_artifact = {
            "path": str(diff_artifact_out.resolve()), "base_sha": base,
            "head_sha": head, "sha256": hashlib.sha256(encoded).hexdigest(),
            "bytes": len(encoded),
            "name_status": _git(repo_root, "-c", "core.quotePath=true", "diff",
                                "--no-ext-diff", "--no-textconv", "--name-status",
                                "--find-renames=50%", f"{base}..{head}"),
        }
        pending_artifacts.append((diff_artifact_out, encoded))
    truncated = len(encoded) > max_diff_bytes
    if truncated:
        diff = encoded[:max_diff_bytes].decode("utf-8", errors="replace")
        changed = _git(
            repo_root,
            "diff",
            "--name-only",
            f"{base}..{head}",
        ).strip()
    acceptance = [
        {"task_id": task["id"], "acceptance_matrix": task["acceptance_matrix"]}
        for mission in missions
        for task in mission["tasks"]
    ]
    acceptance_mappings, mappings_truncated = _relevant_acceptance_mappings(
        plan, missions
    )
    version_gate = (
        run.get("runtime_capabilities", {}).get("runtime_adapter", {}).get("version_gate")
    )
    contract_adoption = (
        version_gate.get("contract_adoption")
        if isinstance(version_gate, dict)
        and version_gate.get("status") == "adopted"
        else None
    )
    # A security reviewer returns each PLAN required check with the key of
    # its one PASS execution at the reviewed head (null when there is none).
    required_checks = []
    security_policy = plan.get("security_review")
    if review["type"] == "security" and isinstance(security_policy, dict):
        for check_id in security_policy.get("required_checks", []):
            keys = [
                execution.get("execution_key")
                for execution in run.get("verifier_executions", [])
                if isinstance(execution, dict)
                and execution.get("verifier_id") == check_id
                and execution.get("layer") in {"batch", "final"}
                and execution.get("status") == "PASS"
                and execution.get("exit_code") == 0
                and isinstance(execution.get("context"), dict)
                and execution["context"].get("head_sha") == head
            ]
            required_checks.append(
                {"id": check_id, "execution_key": keys[0] if len(keys) == 1 else None}
            )
    packet_lines = [
        f"# Review packet: {node_id}",
        "",
        f"- Reviewed head: `{head}`",
        f"- Base: `{base}`",
        f"- Lineage: `{review['lineage_id']}` ({lineage['consumed_attempts']}/{lineage['base_allowance'] + lineage['additional_allowance']} consumed)",
        f"- Scope: {', '.join(review['scope'])}",
    ]
    if review.get("stage") == "integration" and review["type"] == "security":
        packet_lines += [
            "", "## Security coverage", "",
            "Perform a fresh full-scope review at the reviewed head. Prior mission"
            " reviews do not reduce security scope or replace required checks.",
        ]
    elif review.get("stage") == "integration":
        reviewed_heads = []
        for mission in missions:
            mission_head = (
                run.get("mission_states", {}).get(mission["id"], {}).get("head_sha")
            )
            if isinstance(mission_head, str) and mission_head:
                reviewed_heads.append(
                    f"- `{mission['id']}`: `{mission_head}`"
                    " (passed exact-head pre-integration review)"
                )
        if reviewed_heads:
            packet_lines += ["", "## Already-reviewed mission heads", "", *reviewed_heads]
        packet_lines += [
            "",
            "## Integration focus",
            "",
            "Each covered mission's content already passed its own exact-head"
            " pre-integration review. Focus this pass on what combination"
            " changed: merge seams, conflict resolutions, cross-mission"
            " interaction, and shared-contract boundaries.",
        ]
    if review["type"] in {"frontend_code", "backend_code"}:
        packet_lines += [
            "",
            "## Architecture review",
            "",
            "Apply references/delegation-contract.md#architecture-method to affected state, trust, integration or migration boundaries.",
            "Check the concrete caller example before the derived interfaces and types.",
            "Check mutable-state ownership, readers, invariants, invalid states and trust boundaries.",
            "Check repeat-call behavior and recovery after failure between steps against existing acceptance and TEST obligations.",
            "Compare structural alternatives only when coupling, durability, trust or migration remains unresolved.",
            "For unchanged boundaries, reuse the accepted design and verify the local repair.",
            "Classify tool and environment failures separately from design failures.",
            "Use existing review outcomes; do not reset repair budgets or approve new scope or stack decisions.",
        ]
    if (
        ui_acceptance_review(review)
        and plan.get("ui_surfaces")
    ):
        packet_lines += [
            "",
            "## Final UI Acceptance",
            "",
            "Follow the governing pinned contract; do not migrate a frozen RUN through this packet.",
            "For consolidated acceptance, inspect parity and page quality in this one review at the reviewed head.",
            "Use current ui_evidence, target_comparison, layout_check, platform captures and source evidence.",
            "Cover the full required UI matrix for the planned review scope, normal/reduced motion and required native proof.",
            "When parity passes within tolerance and the HiFi evidence is current, check only performance, the no-JavaScript path, console and network errors, and framework-rendered focus handling and accessible names.",
            "Otherwise also check heuristic UX, accessibility and responsive/device behavior alongside parity.",
            "Merge-seam source reading does not reduce required UI evidence coverage.",
            "Return one consolidated finding set and verdict covering both components; do not reopen design direction.",
            "For a repair re-review, check original defects and affected consumers with current evidence.",
            "Use the existing lineage budget; do not add a page-quality-only reviewer or another scoring wave.",
            "Missing required evidence blocks acceptance. Security and final regression obligations remain separate.",
            "Return ui_parity:<retained comparison anchor> and ui_page_quality:<retained quality-report anchor> in review evidence.",
        ]
    if truncated:
        # The untruncated diff already carries every path. Keep an explicit
        # path list only when byte truncation could hide the tail.
        packet_lines += [
            "",
            "## Changed files",
            "",
            changed,
        ]
    packet_lines += [
        "",
        (
            "This diff preview is incomplete. Read the complete base..head diff"
            " from the artifact when supplied (verify its hash), or inspect the same fixed Git"
            " range directly. Report uninspected paths and binary-content gaps;"
            " do not return PASS while required coverage remains unknown."
            if truncated else ""
        ),
        "",
        "## Contract",
        "",
        "```json",
        json.dumps(
            {
                "review_type": review["type"],
                "diff_artifact": diff_artifact,
                "skill_binding_slot": (
                    "code_security_verification"
                    if review["type"] == "security"
                    else None
                ),
                "required_evidence": review["required_evidence"],
                "required_tools": review.get("required_tools", []),
                "required_checks": required_checks,
                "reviewer_tool_capabilities": {
                    tool_name: run.get("runtime_capabilities", {})
                    .get("reviewer_tools", {})
                    .get(tool_name)
                    for tool_name in review.get("required_tools", [])
                },
                "contract_adoption": contract_adoption,
                "acceptance": acceptance,
                "acceptance_mappings": acceptance_mappings,
                "acceptance_mappings_truncated": mappings_truncated,
                "failure_families": lineage["failure_families"],
                "owner_decisions": lineage["owner_decisions"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        "```",
        (
            "Before any review action, independently recompute the seven-skill contract"
            " digest, compare it with `contract_adoption.contract_digest_sha256`, read"
            " the supplied fixed contract, and return your own reading evidence as"
            " `contract_adoption_check` (shape: `references/worker-result-contract.md`,"
            " Contract Adoption Check), beside your review result and never inside a"
            " security review result. Stop on a mismatch. An adoption receipt is not"
            " loaded-at-start evidence."
            if contract_adoption is not None
            else ""
        ),
        "",
        f"## Diff{' (truncated)' if truncated else ''}",
        "",
        "```diff",
        diff.rstrip(),
        "```",
        "",
    ]
    packet = "\n".join(packet_lines)
    if max_message_bytes is not None:
        try:
            check_message(packet, max_message_bytes)
        except MessageBudgetOverflowError as exc:
            raise ManifestError(
                f"review packet exceeds its full-message budget: {exc}. "
                "Use a smaller inline diff with a retained full artifact and "
                "scoped metadata. Defer the launch if required content cannot fit."
            ) from exc
        except InvalidMessageBudgetError as exc:
            raise ManifestError(f"invalid review packet budget: {exc}") from exc
    if artifacts is not None:
        artifacts.extend(pending_artifacts)
    else:
        for path, data in pending_artifacts:
            write_diff_artifact(path, data)
    return packet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--max-diff-bytes", type=int, default=50000)
    parser.add_argument("--max-message-bytes", type=int)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--diff-artifact-out", type=Path)
    args = parser.parse_args(argv)
    try:
        plan = load_plan(args.plan)
        run = load_run(args.run)
        errors = validate_current_plan_run(plan, run, repo_root=args.repo_root)
        if errors:
            raise ManifestError("invalid PLAN/RUN:\n" + "\n".join(errors))
        if args.out and args.out.exists():
            raise ManifestError(f"refusing to overwrite {args.out}")
        if args.out and args.diff_artifact_out and args.out.resolve() == args.diff_artifact_out.resolve():
            raise ManifestError("packet and full diff artifact require distinct output paths")
        artifacts = []
        packet = render_packet(plan, run, args.node, args.repo_root,
                               max_diff_bytes=args.max_diff_bytes,
                               max_message_bytes=args.max_message_bytes,
                               diff_artifact_out=args.diff_artifact_out, artifacts=artifacts)
        for path, data in artifacts:
            write_diff_artifact(path, data)
        if args.out:
            with args.out.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(packet)
            print(f"wrote {args.out}")
        else:
            print(packet, end="")
    except (ManifestError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())

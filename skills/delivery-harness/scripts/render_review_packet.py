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
from harness_graph import repair_scope_entry, ui_acceptance_review
from harness_manifest import ManifestError, load_plan, load_run, validate_current_plan_run
from harness_schema import review_lenses, review_policy
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


def _prior_fix_required_review(
    plan: dict[str, Any], run: dict[str, Any], node_id: str,
    review: dict[str, Any], head: str,
) -> dict[str, Any] | None:
    """Return the latest terminal fix_required review worker to re-check."""
    workers = [
        worker
        for worker in run.get("review_workers", [])
        if isinstance(worker, dict)
        and worker.get("outcome") == "fix_required"
        and isinstance(worker.get("reviewed_sha"), str)
        and worker["reviewed_sha"]
    ]
    matches = [worker for worker in workers if worker.get("node_id") == node_id]
    lineage_id = review.get("lineage_id")
    if not matches and isinstance(lineage_id, str) and lineage_id:
        nodes = {
            node.get("id"): node
            for node in plan.get("graph", {}).get("nodes", [])
            if isinstance(node, dict)
        }
        matches = [
            worker
            for worker in workers
            if isinstance(nodes.get(worker.get("node_id")), dict)
            and nodes[worker["node_id"]].get("review", {}).get("lineage_id")
            == lineage_id
        ]
        if not matches:
            attempts = {
                attempt.get("attempt_id"): attempt
                for attempt in run.get("attempt_log", [])
                if isinstance(attempt, dict)
            }
            matches = [
                worker
                for worker in workers
                if isinstance(attempts.get(worker.get("attempt_id")), dict)
                and attempts[worker["attempt_id"]].get("review_lineage_id")
                == lineage_id
            ]
    if not matches:
        return None
    prior = matches[-1]
    if prior["reviewed_sha"] == head:
        return None
    return prior


def _recheck_lines(
    recheck: dict[str, Any], repair_diff: str, repair_truncated: bool
) -> list[str]:
    lines = [
        "",
        "## Repair re-check",
        "",
        f"Prior reviewed head: `{recheck['prior_reviewed_sha']}`"
        f" (attempt `{recheck['prior_attempt_id']}`,"
        f" worker `{recheck['prior_worker_id']}`).",
        "",
        "Prior blocking findings:",
        *(
            f"- F{index}: {finding}"
            for index, finding in enumerate(recheck["prior_findings"], 1)
        ),
    ]
    if recheck["prior_notes"]:
        lines += [
            "",
            "Prior non-blocking notes (they do not need a verdict):",
            *(f"- {note}" for note in recheck["prior_notes"]),
        ]
    lines += [
        "",
        f"Repair range: `{recheck['repair_range']}`",
        "",
        "Changed files in the repair range:",
        "",
        recheck["repair_name_status"].rstrip(),
        "",
        "Repair diff:",
        "",
        "```diff",
        repair_diff.rstrip(),
        "```",
    ]
    if repair_truncated:
        lines += [
            "",
            "This repair diff preview is incomplete. Read the fixed Git range"
            f" directly (`{recheck['repair_range']}`). Report uninspected"
            " paths and binary-content gaps; do not return a verdict while"
            " required coverage remains unknown.",
        ]
    lines += [
        "",
        "Return a verdict for every prior blocking finding: resolved,"
        " unresolved, or superseded, with path and line evidence at the"
        " reviewed head.",
        "Inspect the repair range and the direct consumers of the changed"
        " code. The security lens re-binds to the reviewed head with full"
        " scope.",
        "An observation outside the prior findings and the repair range is a"
        " non-blocking note unless it is a validated security finding or a"
        " correctness defect in the repair range. Report notes separately;"
        " do not turn them into blocking findings.",
        "Do not reopen design direction, accepted scope, or stack decisions."
        " Do not reset the repair budget.",
        "If you cannot inspect the candidate (checkout or branch mismatch,"
        " permission denial, unavailable runtime), stop and report an"
        " environment blocker with evidence instead of a review verdict.",
    ]
    return lines


def _scoped_repair_lines(
    scoped: dict[str, Any],
    prior_findings: list[str],
    name_status: str,
    scoped_diff: str,
    truncated: bool,
) -> list[str]:
    """The scoped section that replaces the full-candidate diff."""

    trust = scoped.get("trust_boundary") is True
    scoped_range = f"{scoped['prior_head_sha']}..{scoped['candidate_sha']}"
    lines = [
        "",
        "## Scoped repair review",
        "",
        "This head is a recorded isolated repair. The candidate already"
        " carries a non-scoped PASS; this review covers the repair diff only.",
        "",
    ]
    if prior_findings:
        lines += [
            "Prior finding under repair:",
            *(
                f"- F{index}: {finding}"
                for index, finding in enumerate(prior_findings, 1)
            ),
            "",
        ]
        verdict = (
            "Return a verdict on every prior finding: resolved, unresolved,"
            " or superseded, with path and line evidence at the reviewed head."
        )
    else:
        verdict = (
            "Return a pass or fix_required verdict on the scoped repair at"
            " the reviewed head."
        )
    lines += [
        f"Repair range: `{scoped_range}` (scoped to the recorded repair paths)",
        "",
        "Changed files in the repair range:",
        "",
        name_status.rstrip(),
        "",
        "Repair diff:",
        "",
        "```diff",
        scoped_diff.rstrip(),
        "```",
    ]
    if truncated:
        lines += [
            "",
            "This repair diff preview is incomplete. Read the fixed Git range"
            f" directly (`{scoped_range}`). Report uninspected"
            " paths and binary-content gaps; do not return a verdict while"
            " required coverage remains unknown.",
        ]
    lines += [
        "",
        f"Trust boundary: {'yes' if trust else 'no'}. Apply the security"
        " lens to the scoped repair paths only when the trust boundary flag"
        " is set.",
        "",
        verdict,
        "Inspect only the repair paths and their direct consumers.",
        "An observation outside the repair paths and their direct consumers"
        " is a non-blocking note unless it is a validated security finding;"
        " report notes separately and do not turn them into blocking findings.",
    ]
    return lines


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
    lenses = review_lenses(review)
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
    scoped_entry = repair_scope_entry(run, head)
    recheck = (
        None
        if scoped_entry is not None
        else _prior_fix_required_review(plan, run, node_id, review, head)
    )
    recheck_contract = None
    repair_diff = ""
    repair_truncated = False
    if recheck is not None:
        repair_range = f"{recheck['reviewed_sha']}..{head}"
        repair_name_status = _git(
            repo_root, "-c", "core.quotePath=true", "diff",
            "--no-ext-diff", "--no-textconv", "--name-status",
            "--find-renames=50%", repair_range,
        )
        result = run_git(
            repo_root, "diff", "--no-ext-diff", "--no-textconv", "--binary",
            "--full-index", "--no-color", "--find-renames=50%",
            "--src-prefix=a/", "--dst-prefix=b/", repair_range,
            text=False, timeout=30,
        )
        if result.returncode != 0:
            raise ManifestError("cannot read repair range diff")
        repair_encoded = result.stdout
        repair_truncated = len(repair_encoded) > max_diff_bytes
        repair_diff = repair_encoded.decode("utf-8", errors="replace")
        if repair_truncated:
            repair_diff = repair_encoded[:max_diff_bytes].decode("utf-8", errors="replace")
        findings = recheck.get("findings")
        notes = recheck.get("notes")
        recheck_contract = {
            "prior_reviewed_sha": recheck["reviewed_sha"],
            "prior_worker_id": recheck["worker_id"],
            "prior_attempt_id": recheck["attempt_id"],
            "prior_findings": findings if isinstance(findings, list) else [],
            "prior_notes": notes if isinstance(notes, list) else [],
            "repair_range": repair_range,
            "repair_name_status": repair_name_status,
        }
    scoped_prior = (
        scoped_entry["prior_head_sha"] if scoped_entry is not None else None
    )
    scoped_paths = (
        list(scoped_entry["repair_paths"]) if scoped_entry is not None else []
    )
    diff_range = (
        f"{scoped_prior}..{head}"
        if scoped_entry is not None
        else f"{base}..{head}"
    )
    pathspec: tuple[str, ...] = (
        ("--", *scoped_paths) if scoped_entry is not None else ()
    )
    scoped_name_status = ""
    scoped_contract = None
    if scoped_entry is not None:
        scoped_name_status = _git(
            repo_root, "--literal-pathspecs", "-c", "core.quotePath=true", "diff",
            "--no-ext-diff", "--no-textconv", "--name-status",
            "--find-renames=50%", diff_range, *pathspec,
        )
        scoped_contract = {
            "prior_head_sha": scoped_entry["prior_head_sha"],
            "candidate_sha": scoped_entry["candidate_sha"],
            "repair_paths": list(scoped_entry["repair_paths"]),
            "trust_boundary": scoped_entry.get("trust_boundary") is True,
        }
    diff_args = ("--literal-pathspecs", "diff", "--no-ext-diff", "--no-textconv",
                 "--binary", "--full-index", "--no-color", "--find-renames=50%",
                 "--src-prefix=a/", "--dst-prefix=b/", diff_range, *pathspec)
    result = run_git(repo_root, *diff_args, text=False, timeout=30)
    if result.returncode != 0:
        raise ManifestError("cannot read review diff")
    encoded = result.stdout
    diff = encoded.decode("utf-8", errors="replace")
    pending_artifacts: list[tuple[Path, bytes]] = []
    diff_artifact = None
    if diff_artifact_out is not None:
        diff_artifact = {
            "path": str(diff_artifact_out.resolve()),
            "base_sha": scoped_prior or base,
            "head_sha": head, "sha256": hashlib.sha256(encoded).hexdigest(),
            "bytes": len(encoded),
            "name_status": _git(repo_root, "--literal-pathspecs",
                                "-c", "core.quotePath=true", "diff",
                                "--no-ext-diff", "--no-textconv", "--name-status",
                                "--find-renames=50%", diff_range,
                                *pathspec),
        }
        pending_artifacts.append((diff_artifact_out, encoded))
    truncated = len(encoded) > max_diff_bytes
    if truncated:
        diff = encoded[:max_diff_bytes].decode("utf-8", errors="replace")
        changed = _git(
            repo_root,
            "--literal-pathspecs",
            "diff",
            "--name-only",
            diff_range,
            *pathspec,
        ).strip()
    acceptance = [
        {"task_id": task["id"], "acceptance_matrix": task["acceptance_matrix"]}
        for mission in missions
        for task in mission["tasks"]
    ]
    acceptance_mappings, mappings_truncated = _relevant_acceptance_mappings(
        plan, missions
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
        f"- Attempts: {run['graph_state']['node_states'][node_id]['attempts']}/{node['max_attempts']}",
        "- Classify every observation as a blocking finding (defect against"
        " accepted scope, TEST obligations, security, or correctness) or a"
        " non-blocking note; notes never block.",
        f"- Scope: {', '.join(review['scope'])}",
    ]
    if recheck is not None:
        packet_lines += _recheck_lines(
            recheck_contract, repair_diff, repair_truncated
        )
    elif scoped_entry is not None:
        finding_workers = [
            worker
            for worker in run.get("review_workers", [])
            if isinstance(worker, dict)
            and worker.get("outcome") == "fix_required"
            and worker.get("reviewed_sha") == scoped_prior
        ]
        prior_findings = (
            finding_workers[-1].get("findings") if finding_workers else []
        )
        packet_lines += _scoped_repair_lines(
            scoped_entry,
            prior_findings if isinstance(prior_findings, list) else [],
            scoped_name_status,
            diff,
            truncated,
        )
    if review.get("stage") == "integration" and review["type"] == "security":
        packet_lines += [
            "", "## Security coverage", "",
            "Perform a fresh full-scope review at the reviewed head. Prior mission"
            " reviews do not reduce security scope or replace required checks.",
        ]
    elif review.get("stage") == "integration" and review_policy(plan) == "per_mission":
        # A final_candidate review has no earlier mission review to lean on.
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
    if lenses & {"frontend_code", "backend_code"}:
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
            "Use the existing node attempt limit; do not add a page-quality-only reviewer or another scoring wave.",
            "Missing required evidence blocks acceptance. Security and final regression obligations remain separate.",
            "Return ui_parity:<retained comparison anchor> and ui_page_quality:<retained quality-report anchor> in review evidence.",
        ]
    if truncated and scoped_entry is None:
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
            if truncated and scoped_entry is None else ""
        ),
        "",
        "## Contract",
        "",
        "```json",
        json.dumps(
            {
                "review_type": review["type"],
                "review_lenses": sorted(lenses),
                "diff_artifact": diff_artifact,
                "skill_binding_slot": (
                    "code_security_verification"
                    if review["type"] == "security"
                    else None
                ),
                "required_evidence": review["required_evidence"],
                "required_tools": review.get("required_tools", []),
                "required_checks": required_checks,
                "acceptance": acceptance,
                "acceptance_mappings": acceptance_mappings,
                "acceptance_mappings_truncated": mappings_truncated,
                "recheck": recheck_contract,
                "scoped_repair": scoped_contract,
            },
            indent=2,
            ensure_ascii=False,
        ),
        "```",
    ]
    if scoped_entry is None:
        packet_lines += [
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

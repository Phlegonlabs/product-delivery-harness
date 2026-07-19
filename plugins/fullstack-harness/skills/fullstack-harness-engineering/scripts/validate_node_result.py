#!/usr/bin/env python3
"""Validate a typed graph node result against canonical PLAN and RUN state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from harness_manifest import (
    ManifestError,
    load_plan,
    load_run,
    plan_digest,
    validate_plan,
    validate_run,
)


RESULT_KEYS = {
    "run_id",
    "node_id",
    "attempt_id",
    "plan_id",
    "plan_revision",
    "plan_digest_sha256",
    "graph_revision",
    "batch_base_sha",
    "status",
    "outcome",
    "worker_result",
    "refinement_request",
    "evidence_paths",
}
STATUS_OUTCOMES = {
    "succeeded": {"pass", "fix_required"},
    "failed": {"retryable_failure"},
    "blocked": {"blocked", "contract_gap"},
}


def validate_node_result(
    plan: dict[str, Any], run: dict[str, Any], result: Any
) -> list[str]:
    errors = [*validate_plan(plan), *validate_run(plan, run)]
    if errors:
        return sorted(set(errors))
    if plan.get("schema_version") != 4 or run.get("schema_version") not in {8, 9}:
        return ["node result validation requires PLAN v4 and RUN v8"]
    if not isinstance(result, dict) or set(result) != RESULT_KEYS:
        return ["node_result must contain the exact typed graph result fields"]
    node_map = {node["id"]: node for node in plan["graph"]["nodes"]}
    node_id = result["node_id"]
    if not isinstance(node_id, str) or not node_id:
        errors.append("node_result.node_id: must be a non-empty string")
        return sorted(set(errors))
    node = node_map.get(node_id)
    if node is None:
        errors.append("node_result.node_id: unknown PLAN node")
        return sorted(set(errors))
    state = run["graph_state"]["node_states"][node_id]
    if result["run_id"] != run["run_id"]:
        errors.append("node_result.run_id: does not match RUN")
    if result["plan_id"] != plan["plan_id"]:
        errors.append("node_result.plan_id: does not match PLAN")
    if result["plan_revision"] != plan["revision"]:
        errors.append("node_result.plan_revision: does not match PLAN")
    if result["plan_digest_sha256"] != plan_digest(plan):
        errors.append("node_result.plan_digest_sha256: does not match PLAN")
    if result["graph_revision"] != run["graph_state"]["graph_revision"]:
        errors.append("node_result.graph_revision: is stale")
    if result["batch_base_sha"] != run["integration"]["batch_base_sha"]:
        errors.append("node_result.batch_base_sha: does not match RUN")
    if state["phase"] != "running":
        errors.append("node_result.node_id: node is not running")
    if result["attempt_id"] != state["last_attempt_id"]:
        errors.append("node_result.attempt_id: does not match the active attempt")
    status = result["status"]
    outcome = result["outcome"]
    if not isinstance(status, str) or status not in STATUS_OUTCOMES:
        errors.append("node_result.status: has an unsupported value")
    elif not isinstance(outcome, str) or outcome not in STATUS_OUTCOMES[status]:
        errors.append("node_result.outcome: does not match status")
    if not isinstance(outcome, str) or outcome not in node["allowed_outcomes"]:
        errors.append("node_result.outcome: is not declared by the PLAN node")
    if not isinstance(result["evidence_paths"], list) or any(
        not isinstance(item, str) or not item for item in result["evidence_paths"]
    ):
        errors.append("node_result.evidence_paths: must be a list of non-empty strings")
    if node["kind"] == "mission" and status == "succeeded" and not isinstance(
        result["worker_result"], dict
    ):
        errors.append("node_result.worker_result: succeeded mission requires a worker result")
    if (
        node["kind"] == "verifier"
        and node["executor"] == "runtime_worker"
        and status == "succeeded"
    ):
        review_result = result["worker_result"]
        if not isinstance(review_result, dict):
            errors.append("node_result.worker_result: succeeded review requires a review result")
        else:
            required_review_keys = {"reviewed_sha", "findings", "evidence_summary"}
            if set(review_result) != required_review_keys:
                errors.append(
                    "node_result.worker_result: review result must contain reviewed_sha, findings, and evidence_summary"
                )
            else:
                review_workers = [
                    worker
                    for worker in run.get("review_workers", [])
                    if isinstance(worker, dict)
                    and worker.get("node_id") == result["node_id"]
                    and worker.get("attempt_id") == result["attempt_id"]
                ]
                if len(review_workers) != 1:
                    errors.append("node_result.worker_result: active review worker is missing or ambiguous")
                elif review_result["reviewed_sha"] != review_workers[0]["reviewed_sha"]:
                    errors.append("node_result.worker_result.reviewed_sha: does not match the review worker")
                if not isinstance(review_result["findings"], list):
                    errors.append("node_result.worker_result.findings: must be a list")
                if not isinstance(review_result["evidence_summary"], str) or not review_result[
                    "evidence_summary"
                ]:
                    errors.append("node_result.worker_result.evidence_summary: must be a non-empty string")
    if result["outcome"] == "contract_gap" and not isinstance(
        result["refinement_request"], dict
    ):
        errors.append("node_result.refinement_request: contract_gap requires a request")
    if result["outcome"] != "contract_gap" and result["refinement_request"] is not None:
        errors.append("node_result.refinement_request: must be null without contract_gap")
    return sorted(set(errors))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = json.loads(args.result.read_text(encoding="utf-8"))
        if isinstance(result, dict) and set(result) == {"node_result"}:
            result = result["node_result"]
        errors = validate_node_result(load_plan(args.plan), load_run(args.run), result)
    except (ManifestError, OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    payload = {"status": "PASS" if not errors else "ERROR", "errors": errors}
    print(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())

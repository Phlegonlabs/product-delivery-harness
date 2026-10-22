"""Recover only a receipt-proven stale mission-head ingestion rejection."""

from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harness_authorization import execution_covers
from harness_manifest import validate_current_plan_run
from harness_worker_ingestion_proof import (
    DIAGNOSTIC, KIND, bounded_bytes, join_original, one, original_run, receipt_for, require,
)
from harness_worker_result_transition import (
    _load_json, _observe_bound_worker, _project_passing_result, _record_worker_result,
    _validation_failure,
)
from validate_worker_result import load_worker_result


def verify_ingestion_sources(args: Any) -> None:
    """Recheck every supplied evidence file at the RUN commit boundary."""
    for path, expected in getattr(args, "ingestion_source_guards", {}).items():
        require(hashlib.sha256(bounded_bytes(Path(path))).hexdigest() == expected,
                "retained evidence changed before commit: " + str(path))


def verify_ingestion_before_commit(plan: dict[str, Any], run: dict[str, Any], args: Any) -> None:
    verify_ingestion_sources(args)
    node = _load_json(args.node_result, "node_result")
    observed = _observe_bound_worker(plan, run, node, args.repo_root)
    require(observed["head_sha"] == node["worker_result"]["head_sha"]
            and observed["dirty"] is False and observed["ancestry_confirmed"],
            "candidate changed before commit")


def _eligible(plan: dict[str, Any], run: dict[str, Any], proof: dict[str, Any],
              original: dict[str, Any], reconciliation_id: str) -> None:
    require(run.get("status") in {"ready", "running", "blocked"}
            and run.get("control", {}).get("desired_state") == "running",
            "RUN must be unfinished and enabled")
    require(isinstance(reconciliation_id, str) and bool(reconciliation_id.strip()),
            "reconciliation ID is required")
    require(not any(row.get("attempt_id") == reconciliation_id or
                    (row.get("kind") == KIND and row.get(KIND, {}).get("original_attempt_id")
                     == proof["worker"]["attempt_id"])
                    for row in run.get("attempt_log", []) if isinstance(row, dict)),
            "replay or reused reconciliation ID")
    node_id, mission_id = proof["node"]["id"], proof["mission_id"]
    state = run["graph_state"]["node_states"][node_id]
    require(state == proof["state"], "current failed attempt differs from the original rejection")
    mission = run["mission_states"][mission_id]
    require(mission == original["mission_states"][mission_id], "mission changed after the rejection")
    require(run.get("task_states") == original.get("task_states"), "task state changed after the rejection")
    require(run["graph_state"].get("graph_revision") == original["graph_state"].get("graph_revision"),
            "graph revision changed")
    for key, item in run["graph_state"]["node_states"].items():
        require(item == original["graph_state"]["node_states"].get(key),
                "another graph node changed after the rejection")
        require(item.get("phase") != "running", "another graph node is running")
    require(run["graph_state"].get("edge_states") == original["graph_state"].get("edge_states"),
            "downstream graph effects occurred")
    for item in run["graph_state"].get("edge_states", {}).values():
        require(item.get("source_attempt_id") != proof["worker"]["attempt_id"],
                "the failure already traversed a route")
    for worker in [*run.get("workers", []), *run.get("review_workers", [])]:
        require(worker.get("phase") not in {"leased", "worker_running"},
                "competing live or reserved work exists")
    require(run.get("workers") == original.get("workers")
            and run.get("review_workers") == original.get("review_workers"), "worker history changed")
    wave = run.get("active_wave", {})
    expected_wave = {**proof["wave"], "status": "closed"}
    require(wave == expected_wave, "original wave must be closed without replacement")
    one(run.get("closed_waves", []), "closed wave tombstone", wave_id=wave["wave_id"],
        batch_base_sha=wave["batch_base_sha"])
    require(execution_covers(run, mission_id)
            and run.get("execution_authorization_scope", {}).get("expires_when") == "run_complete",
            "surviving run_complete execution authorization is required")
    # Full schema validation checks each surviving action grant. Reconciliation
    # executes no external action and changes no grant or retry budget.
    require(mission.get("blockers") == [DIAGNOSTIC], "another mission blocker exists")


def _historical_admission(original: dict[str, Any], current: dict[str, Any],
                          proof: dict[str, Any]) -> dict[str, Any]:
    view = copy.deepcopy(original)
    # Coordination commits may advance the parent while the isolated candidate
    # and every frozen source stay unchanged. Use current parent Git evidence.
    for key in ("integration", "observed", "landing"):
        view[key] = copy.deepcopy(current[key])
    node_id, mission_id = proof["node"]["id"], proof["mission_id"]
    view["graph_state"]["node_states"][node_id].update(
        {"phase": "running", "last_outcome": None, "blockers": []})
    view["mission_states"][mission_id].update(
        {"phase": "worker_running", "head_sha": None, "blockers": []})
    worker = one(view["workers"], "historical worker", worker_id=proof["worker"]["worker_id"])
    worker["phase"] = "worker_running"
    for task_id, state in view["task_states"].items():
        if task_id.startswith(mission_id + "/") and state.get("phase") == "worker_failed":
            state.update({"phase": "running", "blockers": []})
    one(view["attempt_log"], "historical dispatch",
        attempt_id=proof["worker"]["attempt_id"])["result"] = "dispatched"
    return view


def reconcile_worker_ingestion(plan: dict[str, Any], run: dict[str, Any], args: Any) -> dict[str, Any]:
    require(args.repo_root is not None, "--repo-root is required")
    require(isinstance(args.source, str) and bool(args.source.strip()), "--source is required")
    paths = [args.original_run, args.node_result, args.worker_result, args.result_receipt,
             *args.verifier_result]
    args.ingestion_source_guards = {str(path): hashlib.sha256(bounded_bytes(path)).hexdigest()
                                    for path in paths}
    original = original_run(args.original_run, args.expected_original_run_sha256)
    node_result = _load_json(args.node_result, "node_result")
    require(isinstance(node_result, dict) and isinstance(node_result.get("node_id"), str),
            "node result must name a mission")
    proof = join_original(plan, run, original, node_result["node_id"])
    _eligible(plan, run, proof, original, args.reconciliation_id)
    require(node_result.get("status") == "succeeded" and node_result.get("outcome") == "pass"
            and node_result.get("worker_result") == proof["payload"], "original passing node result differs")
    require(load_worker_result(args.worker_result) == proof["payload"], "Markdown worker report differs")
    require(_load_json(args.result_receipt) == proof["worker"]["result_receipt"], "supplied original receipt differs")
    host_source = Path(proof["worker"]["result_receipt"]["source_ref"])
    args.ingestion_source_guards[str(host_source)] = hashlib.sha256(bounded_bytes(host_source)).hexdigest()
    errors = validate_current_plan_run(plan, run, repo_root=args.repo_root)
    if errors:
        raise _validation_failure("current PLAN/RUN does not validate", errors)
    view = _historical_admission(original, run, proof)
    accepted = _record_worker_result(plan, view, args)
    require(accepted.get("phase") == "worker_passed", "ordinary historical admission did not pass")
    retained = [_load_json(path, "verifier_execution") for path in args.verifier_result]
    staged = copy.deepcopy(run)
    staged["graph_state"]["node_states"][proof["node"]["id"]].update(
        {"phase": "running", "last_outcome": None, "blockers": []})
    _project_passing_result(plan, staged, node_result, proof["payload"], retained,
                            preserve_failed_dispatch=True)
    identities = [{"verifier_id": item["verifier_id"], "execution_key": item["execution_key"],
                   "attempt_id": item["context"]["attempt_id"]} for item in retained]
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    receipt = receipt_for(plan, proof, args.original_run, args.expected_original_run_sha256,
                           identities, source=args.source, timestamp=timestamp,
                           parent_session=args.session_id)
    staged["attempt_log"].append({"attempt_id": args.reconciliation_id,
        "mission_id": proof["mission_id"], "task_id": None, "lease_id": proof["worker"]["lease_id"],
        "kind": KIND, "result": "worker_passed", "evidence": [args.source], KIND: receipt})
    _observe_bound_worker(plan, staged, node_result, args.repo_root)
    verify_ingestion_sources(args)
    run.clear()
    run.update(staged)
    return {"command": "reconcile-worker-ingestion", "node_id": proof["node"]["id"],
            "mission_id": proof["mission_id"], "phase": "worker_passed",
            "head_sha": proof["payload"]["head_sha"], "reconciliation": receipt}

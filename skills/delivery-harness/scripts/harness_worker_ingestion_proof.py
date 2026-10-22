"""Evidence joins for one rejected, otherwise passing mission result."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from agent_launch_records import matching_launch_records
from agent_result_receipts import payload_digest, validate_result_receipt
from agent_role_contract import binding_is_role_bound, role_contract_enabled
from harness_core import ManifestError, extract_json_manifest_text, plan_digest
from harness_contract import contract_adoption_check_errors
from harness_schema import RUN_HEADING


KIND = "worker_ingestion_reconciliation"
DIAGNOSTIC = "observed_head_mismatch: worker_result.head_sha: does not match mission state"
MAX_PROOF_BYTES = 16 * 1024 * 1024
RECEIPT_KEYS = {
    "schema_version", "original_attempt_id", "node_id", "worker_id", "lease_id",
    "plan_revision", "plan_digest_sha256", "batch_base_sha", "head_sha", "wave_id",
    "diagnostic", "failed_dispatch_sha256", "result_receipt", "original_run",
    "original_adoption", "original_adoption_sha256", "launch_record_sha256",
    "verifier_identities", "source", "reconciled_at", "parent_session_id",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ManifestError("worker ingestion reconciliation: " + message)


def bounded_bytes(path: Path) -> bytes:
    require(path.is_absolute(), "proof paths must be absolute")
    with path.open("rb") as stream:
        raw = stream.read(MAX_PROOF_BYTES + 1)
    require(len(raw) <= MAX_PROOF_BYTES, "proof exceeds size limit")
    return raw


def original_run(path: Path, expected: str) -> dict[str, Any]:
    raw = bounded_bytes(path)
    require(hashlib.sha256(raw).hexdigest() == expected, "original RUN bytes changed")
    return extract_json_manifest_text(raw.decode("utf-8"), RUN_HEADING,
                                      "harness_run", source=path)


def one(rows: Any, label: str, **identity: Any) -> dict[str, Any]:
    matches = [row for row in rows if isinstance(row, dict)
               and all(row.get(key) == value for key, value in identity.items())]
    require(len(matches) == 1, label + " must have exactly one matching record")
    return matches[0]


def gate(run: dict[str, Any]) -> dict[str, Any]:
    value = run
    for key in ("runtime_capabilities", "runtime_adapter", "version_gate"):
        value = value.get(key) if isinstance(value, dict) else None
    return value if isinstance(value, dict) else {}


def join_original(plan: dict[str, Any], current: dict[str, Any], original: dict[str, Any],
                  node_id: str) -> dict[str, Any]:
    """Prove original reservation/adoption without accepting an old digest globally."""
    require(plan.get("schema_version") == 6 and current.get("schema_version") == 11
            and original.get("schema_version") == 11, "requires current PLAN-v6/RUN-v11")
    require(role_contract_enabled(current) and role_contract_enabled(original),
            "requires role-bound execution")
    require(current.get("run_id") == original.get("run_id"), "run identity changed")
    require(current.get("plan") == original.get("plan")
            and current["plan"].get("revision") == plan.get("revision")
            and current["plan"].get("digest_sha256") == plan_digest(plan), "PLAN identity changed")
    node = one(plan.get("graph", {}).get("nodes", []), "mission node", id=node_id, kind="mission")
    mission_id = node["ref"]
    old_state = original.get("graph_state", {}).get("node_states", {}).get(node_id, {})
    require(old_state.get("phase") == "failed"
            and old_state.get("last_outcome") == "retryable_failure"
            and old_state.get("blockers") == [DIAGNOSTIC], "original rejection is not the sole known diagnostic")
    old_mission = original.get("mission_states", {}).get(mission_id, {})
    require(old_mission.get("phase") == "worker_failed"
            and old_mission.get("blockers") == [DIAGNOSTIC], "original mission has another failure")
    worker = one(original.get("workers", []), "original worker",
                 worker_id=old_state.get("bound_worker_id"), mission_id=mission_id)
    require(binding_is_role_bound(worker.get("runtime_binding")), "unbound worker is ineligible")
    current_worker = one(current.get("workers", []), "retained worker", worker_id=worker["worker_id"],
                         mission_id=mission_id)
    for key in ("lease_id", "attempt_id", "batch_base_sha", "branch_ref", "worktree_path",
                "runtime_binding", "worker_head_sha", "result_receipt"):
        require(current_worker.get(key) == worker.get(key), "retained worker changed: " + key)
    attempt_id = old_state.get("last_attempt_id")
    require(worker.get("attempt_id") == attempt_id and worker.get("phase") == "worker_failed",
            "original attempt/worker mismatch")
    dispatch = one(original.get("attempt_log", []), "failed dispatch", attempt_id=attempt_id)
    require(dispatch.get("kind") == "dispatch" and dispatch.get("result") == "retryable_failure"
            and dispatch.get("lease_id") == worker.get("lease_id")
            and dispatch.get("mission_id") == mission_id, "original failed dispatch mismatch")
    require(one(current.get("attempt_log", []), "retained failed dispatch", attempt_id=attempt_id)
            == dispatch, "original failed dispatch changed")
    launch = one(matching_launch_records(original, assignment_kind="mission",
                 assignment_id=worker["lease_id"], attempt_id=attempt_id,
                 worker_id=worker["worker_id"]), "original launch")
    require(one(matching_launch_records(current, assignment_kind="mission",
                 assignment_id=worker["lease_id"], attempt_id=attempt_id,
                 worker_id=worker["worker_id"]), "retained launch") == launch,
            "original launch changed")
    adoption = gate(original).get("contract_adoption")
    require(gate(original).get("status") == "adopted" and isinstance(adoption, dict),
            "original dispatch lacks an adopted contract")
    require(adoption.get("session_id") == original.get("run_lock", {}).get("session_id"),
            "original adoption is not bound to its parent session")
    choices = [gate(current).get("contract_adoption"), *gate(current).get("contract_adoption_history", [])]
    require(sum(item == adoption for item in choices) == 1, "original adoption lacks a unique exact history join")
    receipt = worker.get("result_receipt")
    require(isinstance(receipt, dict), "original returned-result receipt is required")
    require(not validate_result_receipt(original, worker, "mission", receipt), "original receipt is invalid")
    source = json.loads(bounded_bytes(Path(receipt["source_ref"])))
    payload = source.get("payload")
    require(isinstance(payload, dict) and payload.get("status") == "worker_passed",
            "a genuine worker failure cannot be reconciled")
    require(not contract_adoption_check_errors(original, payload.get("contract_adoption_check")),
            "original child contract check does not match its dispatch adoption")
    require(payload.get("head_sha") == worker.get("worker_head_sha") == old_mission.get("head_sha")
            and payload.get("base_sha") == worker.get("batch_base_sha")
            and payload.get("lease_id") == worker.get("lease_id"), "original passing candidate mismatch")
    wave = original.get("active_wave", {})
    require(wave.get("status") == "active" and mission_id in wave.get("selected_missions", [])
            and wave.get("batch_base_sha") == worker.get("batch_base_sha"), "original wave mismatch")
    return {"node": node, "mission_id": mission_id, "state": old_state, "worker": worker,
            "dispatch": dispatch, "launch": launch, "adoption": adoption, "payload": payload,
            "wave": wave}


def receipt_for(plan: dict[str, Any], proof: dict[str, Any], original_path: Path,
                original_sha: str, verifier_identities: list[dict[str, Any]], *,
                source: str, timestamp: str, parent_session: str) -> dict[str, Any]:
    worker = proof["worker"]
    return {
        "schema_version": 1, "original_attempt_id": worker["attempt_id"],
        "node_id": proof["node"]["id"], "worker_id": worker["worker_id"],
        "lease_id": worker["lease_id"], "plan_revision": plan["revision"],
        "plan_digest_sha256": plan_digest(plan), "batch_base_sha": worker["batch_base_sha"],
        "head_sha": worker["worker_head_sha"], "wave_id": proof["wave"]["wave_id"],
        "diagnostic": DIAGNOSTIC, "failed_dispatch_sha256": payload_digest(proof["dispatch"]),
        "result_receipt": worker["result_receipt"],
        "original_run": {"source_ref": original_path.as_posix(), "source_sha256": original_sha},
        "original_adoption": proof["adoption"],
        "original_adoption_sha256": payload_digest(proof["adoption"]),
        "launch_record_sha256": payload_digest(proof["launch"]),
        "verifier_identities": verifier_identities, "source": source,
        "reconciled_at": timestamp, "parent_session_id": parent_session,
    }


def validate_reconciliation(plan: dict[str, Any], run: dict[str, Any], row: dict[str, Any]) -> list[str]:
    """Revalidate retained source bytes and immutable joins after later integration."""
    try:
        receipt = row.get(KIND)
        require(isinstance(receipt, dict) and set(receipt) == RECEIPT_KEYS,
                "receipt fields differ from the strict schema")
        require(type(receipt["schema_version"]) is int and receipt["schema_version"] == 1,
                "unsupported receipt schema")
        for key in ("source", "reconciled_at", "parent_session_id"):
            require(isinstance(receipt[key], str) and bool(receipt[key].strip()), "missing " + key)
        reference = receipt["original_run"]
        require(isinstance(reference, dict) and set(reference) == {"source_ref", "source_sha256"},
                "invalid original RUN reference")
        path = Path(reference["source_ref"])
        original = original_run(path, reference["source_sha256"])
        proof = join_original(plan, run, original, receipt["node_id"])
        identities = receipt["verifier_identities"]
        require(isinstance(identities, list) and bool(identities), "verifier identities are required")
        expected = receipt_for(plan, proof, path, reference["source_sha256"], identities,
                               source=receipt["source"], timestamp=receipt["reconciled_at"],
                               parent_session=receipt["parent_session_id"])
        require(receipt == expected, "persisted receipt no longer matches original evidence")
        require(row.get("mission_id") == proof["mission_id"] and row.get("task_id") is None
                and row.get("lease_id") == receipt["lease_id"] and row.get("result") == "worker_passed",
                "audit row identity mismatch")
        duplicates = [item for item in run.get("attempt_log", []) if isinstance(item, dict)
                      and item.get("kind") == KIND and isinstance(item.get(KIND), dict)
                      and item[KIND].get("original_attempt_id") == receipt["original_attempt_id"]]
        require(len(duplicates) == 1, "reconciliation must be unique for the original attempt")
        for identity in identities:
            require(isinstance(identity, dict) and set(identity) == {"verifier_id", "execution_key", "attempt_id"},
                    "invalid verifier identity fields")
            one(run.get("verifier_executions", []), "retained verifier", **identity,
                lease_id=receipt["lease_id"], mission_id=proof["mission_id"], status="PASS")
        expected_identities = {(item["id"], item["evidence"]) for item in proof["payload"]["verifiers"]}
        require(len(identities) == len(expected_identities)
                and {(item["verifier_id"], item["execution_key"]) for item in identities} == expected_identities,
                "retained verifier coverage changed")
        state = run.get("graph_state", {}).get("node_states", {}).get(receipt["node_id"], {})
        if state.get("last_attempt_id") == receipt["original_attempt_id"]:
            require(state.get("attempts") == proof["state"].get("attempts")
                    and state.get("bound_worker_id") == receipt["worker_id"], "original attempt count/binding changed")
            mission = run.get("mission_states", {}).get(proof["mission_id"], {})
            require(mission.get("head_sha") == receipt["head_sha"]
                    and mission.get("phase") in {"worker_passed", "integrating", "integration_failed", "integrated"},
                    "reconciled candidate projection is missing")
            require(state.get("phase") in {"running", "succeeded"}, "reconciled node projection is invalid")
            if mission.get("phase") == "worker_passed":
                require(state.get("phase") == "running" and state.get("last_outcome") is None
                        and state.get("blockers") == [], "candidate was marked complete before integration")
            for task in proof["payload"]["task_results"]:
                task_state = run.get("task_states", {}).get(task["task_id"], {})
                old_task = original.get("task_states", {}).get(task["task_id"], {})
                require(task_state.get("phase") == "mission_recorded"
                        and task_state.get("commit_sha") == task["head_sha"]
                        and task_state.get("verifier_status") == "PASS"
                        and task_state.get("attempts") == old_task.get("attempts"),
                        "reconciled task projection or count changed")
        return []
    except (ManifestError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        return [str(exc)]

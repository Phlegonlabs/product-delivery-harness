#!/usr/bin/env python3
"""Validate parent-observed launches against reserved attempts."""

from __future__ import annotations

from agent_role_bindings import (
    binding_for_runtime,
)
from agent_role_policy_updates import runtime_for_reservation
from agent_role_contract import (
    COMPLETION_KINDS,
    LAUNCH_FALLBACK_KEYS,
    LAUNCH_RECORD_KEYS,
    RUNTIME_AXES,
    WORKER_RUNTIME_KINDS,
    WORKSPACE_KINDS,
    _nonempty,
    binding_is_role_bound,
    is_worker_role_id,
)
from harness_core import (
    is_full_sha,
    is_safe_model_token,
)
from harness_schema import (
    RUNTIME_REASONING_EFFORTS,
    is_valid_provider_id,
)
from typing import (
    Any,
)


def validate_launch_record_shape(record: Any, path: str) -> list[str]:
    if not isinstance(record, dict):
        return [f"{path}: must be an object"]
    errors: list[str] = []
    allowed = set(LAUNCH_RECORD_KEYS) | set(LAUNCH_FALLBACK_KEYS)
    extra = sorted(set(record) - allowed)
    missing = sorted(LAUNCH_RECORD_KEYS - set(record))
    if extra:
        errors.append(f"{path}: unknown keys: {', '.join(extra)}")
    if missing:
        errors.append(f"{path}: missing keys: {', '.join(missing)}")
        return errors
    assignment_kind = record["assignment_kind"]
    if assignment_kind not in ("mission", "review"):
        errors.append(f"{path}.assignment_kind: must be mission or review")
    if not isinstance(record["plan_revision"], int) or isinstance(record["plan_revision"], bool) or record["plan_revision"] < 1:
        errors.append(f"{path}.plan_revision: must be a positive integer")
    if (
        not isinstance(record["plan_digest_sha256"], str)
        or len(record["plan_digest_sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in record["plan_digest_sha256"])
    ):
        errors.append(f"{path}.plan_digest_sha256: must be a lowercase SHA-256")
    if record["worker_runtime"] not in tuple(WORKER_RUNTIME_KINDS):
        errors.append(f"{path}.worker_runtime: has an unsupported value")
    if not is_worker_role_id(record["worker_role"]):
        errors.append(f"{path}.worker_role: has an unsupported value")
    if not is_worker_role_id(record["resolved_role"]):
        errors.append(f"{path}.resolved_role: has an unsupported value")
    if record["workspace_mode"] not in tuple(WORKSPACE_KINDS):
        errors.append(f"{path}.workspace_mode: has an unsupported value")
    if record["completion_channel"] not in tuple(COMPLETION_KINDS):
        errors.append(f"{path}.completion_channel: has an unsupported value")
    if not is_valid_provider_id(record["model_provider"]):
        errors.append(f"{path}.model_provider: has an unsupported value")
    if not is_safe_model_token(record["model"]):
        errors.append(f"{path}.model: must be a safe concrete model token")
    if record["reasoning_effort"] not in tuple(RUNTIME_REASONING_EFFORTS):
        errors.append(f"{path}.reasoning_effort: must be a supported concrete effort")
    if record["requested_model"] is not None and not is_safe_model_token(record["requested_model"]):
        errors.append(f"{path}.requested_model: must be null or a safe model token")
    if (
        record["requested_reasoning_effort"] is not None
        and record["requested_reasoning_effort"] not in tuple(RUNTIME_REASONING_EFFORTS)
    ):
        errors.append(f"{path}.requested_reasoning_effort: must be null or a supported effort")
    for key in (
        "assignment_id", "node_id", "attempt_id", "worker_id", "session_id",
        "launch_observation", "host_observation",
    ):
        if not _nonempty(record[key]):
            errors.append(f"{path}.{key}: must be a non-empty string")
    for key in ("source_sha", "base_sha", "reviewed_sha"):
        if not _sha_or_none(record[key]):
            errors.append(f"{path}.{key}: must be null or a full SHA")
    fallback = {key: record[key] for key in LAUNCH_FALLBACK_KEYS if key in record}
    if fallback:
        missing_fallback = sorted(LAUNCH_FALLBACK_KEYS - set(fallback))
        if missing_fallback:
            errors.append(f"{path}: fallback record requires all keys: {', '.join(missing_fallback)}")
        else:
            availability = fallback["availability"]
            if not isinstance(availability, dict) or set(availability) != {
                "classification", "observed_error", "policy_source"
            }:
                errors.append(f"{path}.availability: must contain classification, observed_error, and policy_source")
            elif (
                availability["classification"] != "model_provider_unavailable"
                or not _nonempty(availability["observed_error"])
                or not _nonempty(availability["policy_source"])
            ):
                errors.append(f"{path}.availability: requires observed model/provider unavailability and policy source")
            predecessor = fallback["predecessor"]
            if not isinstance(predecessor, dict) or set(predecessor) != {
                "worker_id", "stopped", "stop_evidence"
            }:
                errors.append(f"{path}.predecessor: must contain worker_id, stopped, and stop_evidence")
            elif (
                not _nonempty(predecessor["worker_id"])
                or predecessor["stopped"] is not True
                or not _nonempty(predecessor["stop_evidence"])
            ):
                errors.append(f"{path}.predecessor: requires confirmed termination evidence")
            partial = fallback["partial_work"]
            if not isinstance(partial, dict) or set(partial) != {
                "status", "evidence"
            }:
                errors.append(f"{path}.partial_work: must contain status and evidence")
            elif (
                partial["status"] not in ("none", "reconciled")
                or not _nonempty(partial["evidence"])
            ):
                errors.append(f"{path}.partial_work: requires explicit reconciliation evidence")
            configured = fallback["configured_fallback"]
            if not isinstance(configured, dict) or set(configured) != {
                "role", "model_provider", "model", "reasoning_effort", "policy_source"
            }:
                errors.append(f"{path}.configured_fallback: must contain role, model_provider, model, reasoning_effort, and policy_source")
            elif (
                not is_worker_role_id(configured["role"])
                or configured["role"] != record["resolved_role"]
                or configured["model_provider"] != record["model_provider"]
                or configured["model"] != record["requested_model"]
                or configured["reasoning_effort"] != record["requested_reasoning_effort"]
                or not _nonempty(configured["policy_source"])
            ):
                errors.append(f"{path}.configured_fallback: must equal this launch's allowed role binding")
            if not _nonempty(fallback["predecessor_attempt_id"]) or fallback["predecessor_attempt_id"] == record["attempt_id"]:
                errors.append(f"{path}.predecessor_attempt_id: must identify a different stopped attempt")
    return errors


def _sha_or_none(value: Any) -> bool:
    return value is None or is_full_sha(value)


def matching_launch_records(
    run: dict[str, Any],
    *,
    assignment_kind: str,
    assignment_id: Any,
    attempt_id: Any,
    worker_id: Any,
) -> list[dict[str, Any]]:
    records = run.get("launch_records") if isinstance(run.get("launch_records"), list) else []
    return [
        record for record in records
        if isinstance(record, dict)
        and record.get("assignment_kind") == assignment_kind
        and record.get("assignment_id") == assignment_id
        and record.get("attempt_id") == attempt_id
        and record.get("worker_id") == worker_id
    ]


def validate_launch_record(
    run: dict[str, Any],
    *,
    assignment_kind: str,
    assignment_id: str,
    node_id: str,
    attempt_id: str,
    worker_id: str,
    worker_role_expected: str,
    reserved: dict[str, Any],
) -> list[str]:
    """Join a parent-persisted observation to the exact reserved attempt."""

    matches = matching_launch_records(
        run,
        assignment_kind=assignment_kind,
        assignment_id=assignment_id,
        attempt_id=attempt_id,
        worker_id=worker_id,
    )
    if len(matches) != 1:
        return [
            f"run.launch_records: expected one parent launch record for {assignment_kind} "
            f"{assignment_id!r}, attempt {attempt_id!r}, worker {worker_id!r}"
        ]
    record = matches[0]
    prefix = "run.launch_records"
    errors = validate_launch_record_shape(record, prefix)
    binding = reserved.get("runtime_binding")
    if not isinstance(binding, dict):
        return errors + [f"{prefix}: reserved attempt has no runtime_binding"]
    expected = {
        "plan_revision": (run.get("plan") or {}).get("revision"),
        "plan_digest_sha256": (run.get("plan") or {}).get("digest_sha256"),
        "node_id": node_id,
        "worker_role": worker_role_expected,
        "resolved_role": binding.get("resolved_role"),
        "fallback_from_role": binding.get("fallback_from_role"),
        **{key: binding.get(key) for key in RUNTIME_AXES},
        "worker_runtime": binding.get("worker_runtime"),
        "workspace_mode": binding.get("workspace_mode"),
        "completion_channel": binding.get("completion_channel"),
        "model_provider": binding.get("model_provider"),
        "requested_model": binding.get("model"),
        "requested_reasoning_effort": binding.get("reasoning_effort"),
    }
    for key, value in expected.items():
        if record.get(key) != value:
            errors.append(f"{prefix}.{key}: does not match the reserved attempt")
    source_sha = record.get("source_sha")
    expected_source = (
        reserved.get("batch_base_sha")
        if assignment_kind == "mission"
        else reserved.get("reviewed_sha")
    )
    if source_sha != expected_source:
        errors.append(f"{prefix}.source_sha: does not match the reserved input SHA")
    expected_base = reserved.get("base_sha") if assignment_kind == "review" else None
    if record.get("base_sha") != expected_base:
        errors.append(f"{prefix}.base_sha: does not match the reserved base SHA")
    expected_review = reserved.get("reviewed_sha") if assignment_kind == "review" else None
    if record.get("reviewed_sha") != expected_review:
        errors.append(f"{prefix}.reviewed_sha: does not match the reserved review SHA")
    if not _nonempty(record.get("host_observation")):
        errors.append(f"{prefix}.host_observation: requires a separate parent attestation")
    if not is_safe_model_token(record.get("model")):
        errors.append(f"{prefix}.model: requires the concrete observed model identity")
    if record.get("reasoning_effort") not in tuple(RUNTIME_REASONING_EFFORTS):
        errors.append(f"{prefix}.reasoning_effort: requires the concrete observed effort")
    if binding.get("model") is not None and record.get("model") != binding["model"]:
        errors.append(f"{prefix}.model: does not match the explicit reserved request")
    if binding.get("reasoning_effort") is not None and record.get("reasoning_effort") != binding["reasoning_effort"]:
        errors.append(f"{prefix}.reasoning_effort: does not match the explicit reserved request")
    original_role = record.get("fallback_from_role")
    if original_role is not None:
        policy_runtime = runtime_for_reservation(run, assignment_kind, reserved, node_id)
        original_policy = binding_for_runtime(policy_runtime, original_role)
        resolved_role = record.get("resolved_role")
        target_policy = binding_for_runtime(policy_runtime, resolved_role)
        if original_policy is None or original_policy.get("fallback_role") != resolved_role:
            errors.append(f"{prefix}.resolved_role: is not the predecessor binding's configured fallback_role")
        if target_policy is None:
            errors.append(f"{prefix}.resolved_role: has no configured fallback binding")
        else:
            configured = record.get("configured_fallback")
            if not isinstance(configured, dict) or (
                configured.get("role") != resolved_role
                or configured.get("model_provider") != target_policy.get("model_provider")
                or configured.get("model") != target_policy.get("model")
                or configured.get("reasoning_effort") != target_policy.get("reasoning_effort")
            ):
                errors.append(f"{prefix}.configured_fallback: does not equal the predecessor's declared fallback binding")
        from agent_failure_receipts import AVAILABILITY_CODES, read_failure_receipt

        workers = run.get("workers" if assignment_kind == "mission" else "review_workers", [])
        predecessor_id = record.get("predecessor", {})
        predecessor_id = predecessor_id.get("worker_id") if isinstance(predecessor_id, dict) else None
        predecessors = [worker for worker in workers if isinstance(worker, dict)
                        and worker.get("attempt_id") == record.get("predecessor_attempt_id")
                        and worker.get("worker_id") == predecessor_id
                        and (worker.get("mission_id") == reserved.get("mission_id") if assignment_kind == "mission"
                             else worker.get("node_id") == reserved.get("node_id"))]
        if len(predecessors) != 1:
            errors.append(f"{prefix}: requires one exact predecessor reservation")
        else:
            predecessor = predecessors[0]
            primary = predecessor.get("runtime_binding")
            if (not binding_is_role_bound(primary) or primary.get("resolved_role") != original_role
                    or predecessor.get("phase") not in ("blocked", "worker_failed")):
                errors.append(f"{prefix}: predecessor is not a stopped primary role attempt")
            failure, issues = read_failure_receipt(run, predecessor, assignment_kind, predecessor.get("failure_receipt"))
            errors.extend(issues)
            if failure is not None:
                availability = record.get("availability", {})
                if (failure["failure_classification"] != "model_provider_unavailable"
                        or failure["error_code"] not in AVAILABILITY_CODES
                        or not isinstance(availability, dict)
                        or availability.get("observed_error") != failure["observed_error"]
                        or record.get("partial_work") != failure["partial_work"]):
                    errors.append(f"{prefix}: fallback differs from retained availability failure")
    return sorted(set(errors))

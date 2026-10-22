#!/usr/bin/env python3
"""Guard host role-policy updates and retain exact reservation policy views."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_KEY = "role_binding_updates"
JOIN_KEYS = ("assignment_kind", "assignment_id", "node_id", "worker_id", "attempt_id")
RECORD_KEYS = {"update_id", "owner_source", "parent_session_id", "updated_at",
               "before", "after", "before_sha256", "after_sha256", "reservations", "reservation_counts",
               "updated_roles", "policy_patch_sha256"}
MAX_POLICY_BYTES = 1024 * 1024


def policy_digest(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _map(run: dict[str, Any]) -> Any:
    runtime = run.get("runtime_capabilities")
    adapter = runtime.get("runtime_adapter") if isinstance(runtime, dict) else None
    return adapter.get("role_bindings") if isinstance(adapter, dict) else None


def reservation_join(kind: str, reservation: dict[str, Any], node_id: str) -> dict[str, Any]:
    return {"assignment_kind": kind,
            "assignment_id": reservation.get("lease_id") if kind == "mission" else node_id,
            "node_id": node_id, "worker_id": reservation.get("worker_id"),
            "attempt_id": reservation.get("attempt_id")}


def _key(join: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(join.get(key) for key in JOIN_KEYS)


def reservations(plan: dict[str, Any], run: dict[str, Any]) -> list[dict[str, Any]]:
    from agent_role_contract import binding_is_role_bound

    mission_nodes = {node.get("ref"): node.get("id") for node in plan.get("graph", {}).get("nodes", [])
                     if node.get("kind") == "mission"}
    result = []
    for kind, collection in (("mission", "workers"), ("review", "review_workers")):
        for worker in run.get(collection, []):
            if not isinstance(worker, dict) or not binding_is_role_bound(worker.get("runtime_binding")):
                continue
            node_id = mission_nodes.get(worker.get("mission_id")) if kind == "mission" else worker.get("node_id")
            join = reservation_join(kind, worker, node_id)
            launches = [row for row in run.get("launch_records", []) if isinstance(row, dict)
                        and _key(row) == _key(join)]
            identity_keys = ("batch_base_sha", "worker_head_sha", "branch_ref", "worktree_path") if kind == "mission" else ("reviewed_sha", "base_sha")
            result.append({**join, "runtime_binding": copy.deepcopy(worker["runtime_binding"]),
                           "reservation_input": {key: worker.get(key) for key in identity_keys},
                           "launch_record_sha256": policy_digest(launches[0]) if len(launches) == 1 else None})
    return result


def runtime_for_reservation(run: dict[str, Any], kind: str, reservation: dict[str, Any],
                            node_id: str) -> dict[str, Any]:
    """Only an exact retained join can select a historical map; never a role."""
    runtime = run.get("runtime_capabilities", {})
    history = run.get(HISTORY_KEY)
    if not isinstance(history, dict) or not isinstance(history.get("updates"), list):
        return runtime
    join = reservation_join(kind, reservation, node_id)
    matches = [record for record in history["updates"] if isinstance(record, dict)
               and isinstance(record.get("reservations"), list)
               for captured in record.get("reservations", []) if isinstance(captured, dict)
               and _key(captured) == _key(join)
               and captured.get("runtime_binding") == reservation.get("runtime_binding")]
    if len(matches) != 1 or not isinstance(matches[0].get("before"), dict):
        return runtime
    result = copy.deepcopy(runtime)
    result["runtime_adapter"]["role_bindings"] = copy.deepcopy(matches[0]["before"])
    return result


def validate_policy_history(plan: dict[str, Any], run: dict[str, Any]) -> list[str]:
    try:
        return _validate_policy_history(plan, run)
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        return ["run." + HISTORY_KEY + ": malformed policy history: " + str(exc)]


def _validate_policy_history(plan: dict[str, Any], run: dict[str, Any]) -> list[str]:
    from agent_role_bindings import validate_execution_binding, validate_role_bindings
    from agent_role_contract import role_contract_enabled

    if HISTORY_KEY not in run:
        return []
    prefix = "run." + HISTORY_KEY
    history = run[HISTORY_KEY]
    if (not role_contract_enabled(run) or not isinstance(history, dict)
            or set(history) != {"schema_version", "updates"} or history.get("schema_version") != 1
            or isinstance(history.get("schema_version"), bool)
            or not isinstance(history.get("updates"), list) or not history["updates"]):
        return [prefix + ": requires role-bound RUN-v11 and schema_version 1 with nonempty updates"]
    errors, ids, seen = [], set(), set()
    retained = reservations(plan, run)
    nodes = {node.get("id"): node for node in plan.get("graph", {}).get("nodes", [])}
    previous = None
    previous_counts = {"mission": 0, "review": 0}
    for index, record in enumerate(history["updates"]):
        path = f"{prefix}.updates[{index}]"
        if not isinstance(record, dict) or set(record) != RECORD_KEYS:
            errors.append(path + ": must contain exactly the role-policy update fields")
            continue
        for field in ("update_id", "owner_source", "parent_session_id", "updated_at"):
            if not _nonempty(record[field]):
                errors.append(path + f".{field}: must be a non-empty string")
        update_id = record["update_id"]
        if not isinstance(update_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", update_id) is None:
            errors.append(path + ".update_id: must be a bounded stable id")
        elif update_id in ids:
            errors.append(path + ".update_id: must be unique")
        else:
            ids.add(update_id)
        try:
            timestamp = datetime.fromisoformat(record["updated_at"].replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                raise ValueError("missing timezone")
        except (ValueError, TypeError, AttributeError):
            errors.append(path + ".updated_at: must be a timezone-aware timestamp")
        for field in ("before", "after"):
            view = copy.deepcopy(run)
            view["runtime_capabilities"]["runtime_adapter"]["role_bindings"] = record[field]
            errors.extend(path + ": " + issue for issue in validate_role_bindings(view))
            if policy_digest(record[field]) != record[field + "_sha256"]:
                errors.append(path + f".{field}_sha256: does not match the canonical map")
        if (not isinstance(record["before"], dict) or not isinstance(record["after"], dict)
                or set(record["before"]) != set(record["after"])):
            errors.append(path + ": updates may replace only existing logical roles")
        roles = record["updated_roles"]
        if (not isinstance(roles, list) or not roles or not all(isinstance(role, str) for role in roles)
                or roles != sorted(set(roles)) or not isinstance(record["before"], dict)
                or not isinstance(record["after"], dict) or set(roles) - set(record["before"])
                or set(roles) - set(record["after"])):
            errors.append(path + ".updated_roles: must name unique configured logical roles")
        else:
            patch = {role: record["after"][role] for role in roles}
            if (policy_digest(patch) != record["policy_patch_sha256"]
                    or {**record["before"], **patch} != record["after"]):
                errors.append(path + ": patch identity does not match the before/after maps")
        if record["before"] == record["after"]:
            errors.append(path + ": must change at least one role binding")
        if previous is not None and record["before"] != previous:
            errors.append(path + ": before map breaks the policy chain")
        previous = record["after"]
        captured_rows = record["reservations"]
        if not isinstance(captured_rows, list):
            errors.append(path + ".reservations: must be a list")
            continue
        counts = record["reservation_counts"]
        if (not isinstance(counts, dict) or set(counts) != {"mission", "review"}
                or any(type(counts[kind]) is not int or counts[kind] < previous_counts[kind]
                       or counts[kind] > len(run.get(collection, []))
                       for kind, collection in (("mission", "workers"), ("review", "review_workers")))):
            errors.append(path + ".reservation_counts: must bind monotonic retained reservation boundaries")
        else:
            boundary = {**run, "workers": run.get("workers", [])[:counts["mission"]],
                        "review_workers": run.get("review_workers", [])[:counts["review"]]}
            expected_rows = [row for row in reservations(plan, boundary) if _key(row) not in seen]
            if captured_rows != expected_rows:
                errors.append(path + ".reservations: must freeze every reservation at its first boundary")
            previous_counts = counts
        for captured in captured_rows:
            if (not isinstance(captured, dict) or set(captured) != {*JOIN_KEYS, "runtime_binding", "reservation_input", "launch_record_sha256"}
                    or captured.get("assignment_kind") not in ("mission", "review")
                    or not all(_nonempty(captured.get(key)) for key in JOIN_KEYS)):
                errors.append(path + ".reservations: malformed exact reservation join")
                continue
            identity = _key(captured)
            if identity in seen:
                errors.append(path + ".reservations: reservation already frozen at an earlier boundary")
            seen.add(identity)
            matches = [row for row in retained if _key(row) == identity]
            if len(matches) != 1 or matches[0] != captured:
                errors.append(path + ".reservations: captured reservation or binding identity changed")
                continue
            node = nodes.get(captured["node_id"])
            if node is None:
                errors.append(path + ".reservations: node no longer exists")
                continue
            runtime = copy.deepcopy(run["runtime_capabilities"])
            runtime["runtime_adapter"]["role_bindings"] = record["before"]
            errors.extend(validate_execution_binding(path, captured["runtime_binding"], node, runtime))
    if previous != _map(run):
        errors.append(prefix + ": final after map must equal the current role bindings")
    return sorted(set(errors))


def load_policy_patch(path: Path) -> dict[str, Any]:
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("non-finite JSON")
        return result

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("role policy JSON contains a duplicate key")
            result[key] = value
        return result

    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise ValueError("role policy must be a parent-owned regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_POLICY_BYTES + 1)
    if len(raw) > MAX_POLICY_BYTES:
        raise ValueError("role policy exceeds the 1 MiB limit")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs, parse_float=finite_float,
                           parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite JSON")))
    except (UnicodeError, RecursionError) as exc:
        raise ValueError("role policy must contain bounded UTF-8 JSON") from exc
    if not isinstance(value, dict) or not value:
        raise ValueError("role policy must be a nonempty object of logical role replacements")
    return value


def update_role_bindings(plan: dict[str, Any], run: dict[str, Any], args: Any) -> dict[str, Any]:
    from agent_role_bindings import resolve_runtime_binding, validate_role_bindings
    from agent_role_contract import role_contract_enabled, worker_role
    from harness_manifest import ManifestError, execution_covers

    if plan.get("schema_version") != 6 or run.get("schema_version") != 11 or not role_contract_enabled(run):
        raise ManifestError("role-policy update requires role-bound PLAN-v6/RUN-v11")
    if args.repo_root is None:
        raise ManifestError("role-policy update requires --repo-root")
    roots = [args.repo_root, *[worker["worktree_path"] for worker in run.get("workers", [])
                             if isinstance(worker, dict) and worker.get("worktree_path")]]
    for root in roots:
        if args.policy.resolve().is_relative_to(Path(root).resolve()):
            raise ManifestError("role policy must be parent-owned outside consumer and worker checkouts")
    patch = load_policy_patch(args.policy)
    expected = args.expected_role_bindings_sha256
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ManifestError("expected role bindings digest must be a lowercase SHA-256")
    if not _nonempty(args.owner_source) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", args.update_id) is None:
        raise ManifestError("role-policy update requires owner source and a bounded stable update id")
    scope = run.get("execution_authorization_scope")
    if (run.get("status") == "complete" or run.get("control", {}).get("desired_state") == "cancelled"
            or not isinstance(scope, dict) or scope.get("expires_when") != "run_complete"
            or not all(execution_covers(run, mission["id"]) for mission in plan.get("missions", []))):
        raise ManifestError("role-policy update requires surviving run_complete execution authority")
    wave = run.get("active_wave")
    live = any(isinstance(worker, dict) and worker.get("phase") in {"leased", "worker_running"}
               for key in ("workers", "review_workers") for worker in run.get(key, []))
    running = any(isinstance(state, dict) and state.get("phase") == "running"
                  for state in run.get("graph_state", {}).get("node_states", {}).values())
    reserved = any(isinstance(row, dict) and row.get("kind") == "node_attempt" and row.get("result") == "reserved"
                   for row in run.get("attempt_log", []))
    if (isinstance(wave, dict) and wave.get("status") in {"active", "proposed"}) or live or running or reserved:
        raise ManifestError("role-policy update requires a quiescent run")
    history = run.get(HISTORY_KEY, {"schema_version": 1, "updates": []})
    previous = [row for row in history["updates"] if row["update_id"] == args.update_id]
    if previous:
        row = previous[0]
        requested = copy.deepcopy(row["before"])
        if set(patch) - set(requested):
            raise ManifestError("role-policy update id was reused with different input")
        requested.update(patch)
        if (row["owner_source"] != args.owner_source or row["parent_session_id"] != args.session_id
                or row["before_sha256"] != expected or requested != row["after"]
                or policy_digest(patch) != row["policy_patch_sha256"]):
            raise ManifestError("role-policy update id was reused with different input")
        return {"update_id": args.update_id, "recorded": False, "after_sha256": row["after_sha256"]}
    current = _map(run)
    if not isinstance(current, dict) or policy_digest(current) != expected:
        raise ManifestError("current role bindings differ from the expected digest")
    if set(patch) - set(current):
        raise ManifestError("role policy contains unknown logical roles")
    proposed = copy.deepcopy(run)
    after = copy.deepcopy(current)
    after.update(copy.deepcopy(patch))
    proposed["runtime_capabilities"]["runtime_adapter"]["role_bindings"] = after
    issues = validate_role_bindings(proposed)
    if issues:
        raise ManifestError("invalid proposed role policy: " + "; ".join(issues))
    for node in plan.get("graph", {}).get("nodes", []):
        if (node.get("executor") == "runtime_worker" and worker_role(node) is not None
                and resolve_runtime_binding(node, proposed["runtime_capabilities"]) is None):
            issues.append(f"node {node.get('id')}: proposed policy conflicts with PLAN runtime choices")
    if after == current:
        issues.append("role-policy update must change at least one binding")
    if issues:
        raise ManifestError("invalid proposed role policy: " + "; ".join(issues))
    frozen = {_key(row) for record in history["updates"] for row in record["reservations"]}
    captured = [row for row in reservations(plan, run) if _key(row) not in frozen]
    record = {"update_id": args.update_id, "owner_source": args.owner_source,
              "parent_session_id": args.session_id,
              "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
              "before": copy.deepcopy(current), "after": after,
              "before_sha256": expected, "after_sha256": policy_digest(after), "reservations": captured,
              "updated_roles": sorted(patch), "policy_patch_sha256": policy_digest(patch),
              "reservation_counts": {"mission": len(run.get("workers", [])),
                                     "review": len(run.get("review_workers", []))}}
    run["runtime_capabilities"]["runtime_adapter"]["role_bindings"] = after
    run[HISTORY_KEY] = {"schema_version": 1, "updates": [*history["updates"], record]}
    return {"update_id": args.update_id, "recorded": True, "after_sha256": record["after_sha256"]}

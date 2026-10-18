"""Join parent-observed intervals to reserved attempts without advancing work."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from agent_launch_records import matching_launch_records, validate_launch_record
from agent_role_contract import role_contract_enabled
from deployment_source_observation import _load_json, _safe_regular_bytes
from harness_core import ManifestError
from harness_schema import is_valid_provider_id


MAX_REQUEST_BYTES = 64 * 1024
IDENTITY_FIELDS = ("run_id", "assignment_kind", "assignment_id", "node_id", "attempt_id", "worker_id", "sample_id")
COUNTS = ("duration_ms", "wait_ms", "input_tokens", "output_tokens", "cached_input_tokens", "context_bytes")
FIELDS = set(IDENTITY_FIELDS) | set(COUNTS) | {"schema", "phase", "status", "started_at", "completed_at"}
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z")


def load_observation(path: Path) -> dict[str, Any]:
    """Read one bounded local regular file using the existing guarded reader."""
    if str(path).startswith(("\\\\", "//")) or "://" in str(path):
        raise ManifestError("runtime observation must be a local file")
    target = Path(os.path.abspath(path))
    raw, _, errors = _safe_regular_bytes(target.parent, target.name, "runtime observation")
    if errors:
        raise ManifestError("; ".join(errors))
    if len(raw) > MAX_REQUEST_BYTES:
        raise ManifestError("runtime observation exceeds 64 KiB")
    try:
        value, errors = _load_json(raw, "runtime observation")
    except RecursionError as exc:
        raise ManifestError("runtime observation JSON nesting is too deep") from exc
    if errors:
        raise ManifestError("; ".join(errors))
    return value


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise ManifestError("runtime observation timestamps require an ISO-8601 timezone")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ManifestError("runtime observation timestamp is invalid") from exc


def _normalize(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict) or set(request) != FIELDS:
        raise ManifestError("runtime observation has an invalid closed field set")
    if request["schema"] != "runtime-observation/1":
        raise ManifestError("runtime observation requires runtime-observation/1")
    for name in IDENTITY_FIELDS:
        value = request[name]
        if (not isinstance(value, str) or not value or value != value.strip()
                or len(value) > 256 or any(ord(character) < 32 or ord(character) == 127 for character in value)):
            raise ManifestError("runtime observation identities must be bounded nonempty strings")
    if request["assignment_kind"] not in {"mission", "review"}:
        raise ManifestError("runtime observation assignment_kind must be mission or review")
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", request["sample_id"]):
        raise ManifestError("runtime observation sample_id must be a short stable identifier")
    if request["phase"] not in ("dispatch_to_terminal", "retry_backoff"):
        raise ManifestError("runtime observation phase must be dispatch_to_terminal or retry_backoff")
    if request["status"] not in ("complete", "failed", "blocked", "cancelled"):
        raise ManifestError("runtime observation must describe a terminal interval")
    started, completed = _timestamp(request["started_at"]), _timestamp(request["completed_at"])
    if completed < started:
        raise ManifestError("runtime observation completed_at precedes started_at")
    for name in COUNTS:
        value = request[name]
        if value is not None and (type(value) is not int or value < 0):
            raise ManifestError("runtime observation counts must be null or non-negative integers")
    cached, total = request["cached_input_tokens"], request["input_tokens"]
    if cached is not None and total is not None and cached > total:
        raise ManifestError("runtime observation cached tokens exceed input tokens")
    return {**request, "started_at": started.isoformat().replace("+00:00", "Z"),
            "completed_at": completed.isoformat().replace("+00:00", "Z")}


def _reserved(plan: dict[str, Any], run: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    mission = request["assignment_kind"] == "mission"
    key = "lease_id" if mission else "node_id"
    matches = [worker for worker in run.get("workers" if mission else "review_workers", [])
               if isinstance(worker, dict) and worker.get(key) == request["assignment_id"]
               and worker.get("worker_id") == request["worker_id"]
               and worker.get("attempt_id") == request["attempt_id"]]
    if len(matches) != 1:
        raise ManifestError("runtime observation requires one matching reserved attempt")
    worker = matches[0]
    if mission:
        nodes = [node.get("id") for node in plan.get("graph", {}).get("nodes", [])
                 if isinstance(node, dict) and node.get("kind") == "mission"
                 and node.get("ref") == worker.get("mission_id")]
    else:
        nodes = [node.get("id") for node in plan.get("graph", {}).get("nodes", [])
                 if isinstance(node, dict) and node.get("kind") == "verifier"
                 and node.get("executor") == "runtime_worker" and isinstance(node.get("review"), dict)
                 and node.get("id") == worker.get("node_id")]
    if nodes != [request["node_id"]]:
        raise ManifestError("runtime observation node does not match the reserved assignment")
    return worker


def append_observation(plan: dict[str, Any], run: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Append one observation or return an identical replay without mutation."""
    if not role_contract_enabled(run):
        raise ManifestError("runtime observations require a 0.58+ role-contract RUN")
    if run.get("status") in {"complete", "archived"}:
        raise ManifestError("runtime observations cannot change a closed RUN")
    request = _normalize(request)
    if request["run_id"] != run.get("run_id"):
        raise ManifestError("runtime observation belongs to another RUN")
    worker = _reserved(plan, run, request)
    binding = worker.get("runtime_binding")
    if not isinstance(binding, dict):
        raise ManifestError("runtime observation reservation has no runtime_binding")
    identity = {name: request[name] for name in ("assignment_kind", "assignment_id", "attempt_id", "worker_id")}
    launches = matching_launch_records(run, **identity)
    if launches:
        issues = validate_launch_record(run, **identity, node_id=request["node_id"],
                                        worker_role_expected=binding.get("worker_role"), reserved=worker)
        if issues:
            raise ManifestError("runtime observation has an invalid reserved launch: " + "; ".join(issues))
        provider = launches[0]["model_provider"]
    elif request["phase"] == "retry_backoff":
        provider = binding.get("model_provider")
    else:
        raise ManifestError("dispatch_to_terminal requires its parent-retained launch record")
    if not is_valid_provider_id(provider):
        raise ManifestError("runtime observation has no valid reserved model provider")
    digest_input = {name: request[name] for name in (*IDENTITY_FIELDS, "phase")}
    digest = hashlib.sha256(json.dumps(digest_input, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    event = {"event_id": "host-observation-" + digest, "provider": provider,
             **{name: request[name] for name in ("node_id", "attempt_id", "phase", "status", "started_at", "completed_at", *COUNTS)}}
    metrics = run.get("runtime_metrics")
    if metrics is not None and (not isinstance(metrics, dict) or not isinstance(metrics.get("events"), list)):
        raise ManifestError("runtime observation cannot repair malformed existing metrics")
    events = metrics["events"] if metrics is not None else []
    prior = [item for item in events if isinstance(item, dict) and item.get("event_id") == event["event_id"]]
    if prior:
        if len(prior) != 1 or prior[0] != event:
            raise ManifestError("runtime observation conflicts with its retained sample")
        return {"command": "record-runtime-observation", "recorded": False, "event": event}
    if metrics is None:
        metrics = {"baseline_wall_time_ms": None, "run_wall_time_ms": None, "critical_path_ms": None, "events": []}
        run["runtime_metrics"] = metrics
    metrics["events"].append(event)
    return {"command": "record-runtime-observation", "recorded": True, "event": event}

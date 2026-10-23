"""Admit fresh mission integration runner output without executing commands."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import stat
from pathlib import Path
from typing import Any

from harness_core import ManifestError, plan_digest
from harness_manifest import _has_retained_pass_execution, _verifier_owners, _validate_verifier_executions
from harness_worker_result_transition import _retained_execution
from verifier_runtime import VerifierRuntimeError, _git_guard_snapshot


MAX_RESULT_BYTES = 16 * 1024 * 1024


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ManifestError("integration verifier result: " + message)


def _file_token(value: os.stat_result) -> tuple[int, ...]:
    # Windows path stat and fstat disagree on legacy ctime after a rewrite.
    # Birth time is consistent there; POSIX ctime retains change detection.
    change_time = getattr(value, "st_birthtime_ns", 0) if os.name == "nt" else value.st_ctime_ns
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns,
            change_time, value.st_mode)


def _read_source(path: Path, root: Path) -> tuple[bytes, tuple[int, ...]]:
    from harness_transition import _assert_non_reparse_path

    _require(path.is_absolute(), "result paths must be absolute")
    _assert_non_reparse_path(path)
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        pass
    else:
        raise ManifestError("integration verifier result files must live outside the checkout")
    try:
        before = path.lstat()
        _require(stat.S_ISREG(before.st_mode), "result must be a regular file")
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            _require(_file_token(before) == _file_token(opened), "result identity changed while opening")
            raw = stream.read(MAX_RESULT_BYTES + 1)
            _require(_file_token(opened) == _file_token(os.fstat(stream.fileno())),
                     "result changed while reading")
        _assert_non_reparse_path(path)
        _require(_file_token(before) == _file_token(path.lstat()), "result identity changed while reading")
    except OSError as exc:
        raise ManifestError(f"cannot read integration verifier result {path}: {exc}") from exc
    _require(len(raw) <= MAX_RESULT_BYTES, "result exceeds the 16 MiB limit")
    return raw, _file_token(before)


def _json_result(raw: bytes) -> dict[str, Any]:
    def unique_pairs(pairs):
        value = {}
        for key, item in pairs:
            _require(key not in value, "duplicate JSON key")
            value[key] = item
        return value

    def finite_float(value):
        number = float(value)
        _require(math.isfinite(number), "non-finite JSON number")
        return number

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                           parse_float=finite_float,
                           parse_constant=lambda value: _require(False, "non-finite JSON number"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ManifestError("integration verifier result must contain bounded UTF-8 JSON") from exc
    if isinstance(value, dict) and set(value) == {"verifier_execution"}:
        value = value["verifier_execution"]
    _require(isinstance(value, dict), "runner output must be an object")
    return value


def _snapshot(root: Path, guard: dict[str, Any]) -> dict[str, Any]:
    from harness_transition import _git_out, _same_path

    _require(_same_path(root, _git_out(root, "rev-parse", "--show-toplevel").strip()),
             "checkout root must be the live Git root")
    try:
        return _git_guard_snapshot(root, guard)
    except (VerifierRuntimeError, OSError) as exc:
        raise ManifestError("integration verifier live Git guard failed: " + str(exc)) from exc


def retain_integration_results(plan: dict[str, Any], run: dict[str, Any], args: Any) -> None:
    """Stage admitted records; the caller owns locks, full validation and CAS."""
    from harness_transition import _coordination_ignored_paths, _candidate_changed_paths

    paths = list(getattr(args, "verifier_result", []) or [])
    if not paths:
        return
    root = Path(args.repo_root).resolve()
    branch = run["integration"]["branch"]
    guard = {"expected_branch": branch, "expected_head_sha": args.integrated_sha,
             "ignored_paths": sorted(_coordination_ignored_paths(root, getattr(args, "run", None), run))}
    snapshot = _snapshot(root, guard)
    expected_context = {
        "run_id": run["run_id"], "plan_revision": plan["revision"],
        "plan_digest_sha256": plan_digest(plan),
        "graph_revision": run["graph_state"]["graph_revision"],
        "batch_base_sha": run["integration"]["batch_base_sha"],
        "head_sha": args.integrated_sha,
        "changed_files": sorted(_candidate_changed_paths(root, run["integration"]["batch_base_sha"], args.integrated_sha)),
        "trust_domain": "parent_local", "checkout_role": "integration",
        "checkout_dirty": False, "cache_safe": False,
        "layer": "mission_integration", "mission_id": args.mission_id,
        "task_id": None, "attempt_id": None, "lease_id": None,
    }
    owners = _verifier_owners(plan)
    seen: set[str] = set()
    sources = []
    staged = copy.deepcopy(run)
    for path in paths:
        path = Path(path)
        raw, token = _read_source(path, root)
        retained = _json_result(raw)
        verifier_id = retained.get("verifier_id")
        _require(isinstance(verifier_id, str) and verifier_id in owners, "unknown verifier ID")
        layer, mission_id, task_id, declaration = owners[verifier_id]
        _require((layer, mission_id, task_id) == ("mission_integration", args.mission_id, None),
                 "verifier belongs to another route or mission")
        _require(verifier_id not in seen, "duplicate supplied verifier ID")
        seen.add(verifier_id)
        _require(retained.get("protocol") == "harness-verifier-execution-v2", "protocol-v2 output is required")
        _require(json.dumps(retained.get("context"), sort_keys=True) == json.dumps(expected_context, sort_keys=True),
                 "context differs from the current integration candidate")
        _require(isinstance(retained.get("stdout"), str) and isinstance(retained.get("stderr"), str),
                 "captured stdout and stderr are required")
        _require(retained.get("status") == "PASS" and type(retained.get("exit_code")) is int
                 and retained["exit_code"] == 0, "fresh PASS with exit 0 is required")
        _require(retained.get("cache_status") == "bypassed"
                 and retained.get("metrics") == {"executed": 1, "reused": 0}
                 and all(type(value) is int for value in retained["metrics"].values())
                 and "container_reuse_origin" not in retained, "cache reuse is forbidden")
        _require("reservation" not in retained and "dispatch_attestation" not in retained,
                 "node reservations belong to another ingestion route")
        isolation = declaration.get("execution", {}).get("isolation")
        _require(isolation == "host", "explicit host policy is required")
        nested_key = "host_execution_attestation"
        _require(set(retained) == {
            "protocol", "verifier_id", "status", "exit_code", "stdout", "stderr",
            "execution_key", "evidence_key", "verifier", "context", "key_document",
            "cache_status", "cache_reason", "duration_ms", "metrics",
            "git_guard_attestation", nested_key,
        }, "runner output fields must match actual protocol-v2 output")
        attestation = retained.get("git_guard_attestation")
        _require(isinstance(attestation, dict) and set(attestation) == {
            "checkout_root", "git_guard", "isolation_mode", "source_head_sha", nested_key,
            "tracked_files", "protected_path_sha256", "protected_path_stats",
        }, "complete Git guard attestation is required")
        _require(attestation["checkout_root"] == str(root) and attestation["git_guard"] == guard
                 and attestation["isolation_mode"] == isolation
                 and attestation["source_head_sha"] == args.integrated_sha
                 and isinstance(retained.get(nested_key), dict)
                 and attestation[nested_key] == retained[nested_key], "Git guard identity differs from the live candidate")
        _require(all(attestation[key] == value for key, value in snapshot.items()),
                 "tracked or protected verifier inputs changed")
        _require(not any(isinstance(row, dict) and row.get("status") == "PASS"
                         and row.get("verifier_id") == verifier_id
                         and row.get("mission_id") == args.mission_id
                         and row.get("context", {}).get("head_sha") == args.integrated_sha
                         and row.get("execution_key") == retained.get("execution_key")
                         for row in run.get("verifier_executions", [])), "PASS execution is already retained")
        staged.setdefault("verifier_executions", []).append(_retained_execution(staged, retained, [str(path)]))
        sources.append((str(path), hashlib.sha256(raw).hexdigest(), token))
    # This validator retains declaration, key, preflight and isolation checks.
    # The prospective integrated head is needed for merged-candidate evidence.
    staged["integration"]["integration_head_sha"] = args.integrated_sha
    staged["mission_states"][args.mission_id]["integrated_sha"] = args.integrated_sha
    errors: list[str] = []
    _validate_verifier_executions(errors, plan, staged)
    _require(not errors, "retained execution validation failed: " + "; ".join(errors))
    required_ids = {identifier for identifier, owner in owners.items()
                    if owner[:3] == ("mission_integration", args.mission_id, None)}
    _require(all(_has_retained_pass_execution(
        staged, verifier_id=identifier, layer="mission_integration", mission_id=args.mission_id,
        task_id=None, head_sha=args.integrated_sha,
    ) for identifier in required_ids), "complete declared integration PASS coverage is required")
    run["verifier_executions"] = staged["verifier_executions"]
    args.integration_observation = {"root": root, "guard": guard, "snapshot": snapshot, "sources": sources}


def verify_integration_observation(args: Any, pending: Path | None = None) -> None:
    observation = getattr(args, "integration_observation", None)
    if not isinstance(observation, dict):
        return
    for path, digest, token in observation["sources"]:
        raw, current_token = _read_source(Path(path), observation["root"])
        _require(current_token == token and hashlib.sha256(raw).hexdigest() == digest,
                 "result source changed before commit")
    guard, relative = observation["guard"], None
    if pending is not None:
        # At the RUN exchange boundary the writer's own temporary file exists;
        # exclude exactly that path, never a pattern.
        try:
            relative = pending.resolve().relative_to(Path(observation["root"]).resolve()).as_posix()
        except ValueError:
            relative = None
    if relative is not None:
        guard = {**guard, "ignored_paths": sorted({*guard["ignored_paths"], relative})}
    snapshot = _snapshot(observation["root"], guard)
    if relative is not None:
        snapshot["protected_path_sha256"].pop(relative, None)
        snapshot["protected_path_stats"].pop(relative, None)
    _require(snapshot == observation["snapshot"],
             "live Git or protected input identity changed before commit")

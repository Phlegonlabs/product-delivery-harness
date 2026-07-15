#!/usr/bin/env python3
"""Shared, stdlib-only manifest validation and conflict helpers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


PLAN_HEADING = "## Harness Plan Manifest"
RUN_HEADING = "## Harness Run State"
WORKER_HEADING = "## Worker Result Manifest"

AUTHORIZATION_KEYS_V2 = (
    "spawn_subagents",
    "create_user_owned_tasks",
    "create_local_worktrees",
    "create_app_managed_worktrees",
    "create_local_branches",
    "create_local_commits",
    "integrate_locally",
    "push",
    "create_pr",
    "deploy",
    "archive_worker_tasks",
    "remove_worktrees",
    "delete_branches",
)

AUTHORIZATION_KEYS = AUTHORIZATION_KEYS_V2 + (
    "configure_repository",
    "manage_pr_review",
    "merge_pr",
)

MISSION_PHASES = {
    "queued",
    "ready",
    "leased",
    "worker_running",
    "worker_passed",
    "integrating",
    "integrated",
    "blocked",
    "worker_failed",
    "integration_failed",
    "superseded",
}
TASK_PHASES = {
    "queued",
    "ready",
    "running",
    "worker_passed",
    "mission_recorded",
    "blocked",
    "worker_failed",
    "superseded",
}
WORKER_PHASES = {
    "leased",
    "worker_running",
    "worker_passed",
    "blocked",
    "worker_failed",
    "superseded",
}
GATE_VALUES = {"planned", "PASS", "FAIL", "BLOCKED", "UNVALIDATED"}
SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]{0,63}$")
TASK_ID_RE = re.compile(r"^([A-Z][A-Z0-9_-]{0,63})/([A-Z][A-Z0-9_-]{0,63})$")
TARGET_RE = re.compile(
    r"^(?:worker|task|worktree|branch|remote|pr|repository|environment):.+$"
)
EXPIRY_BOUNDARIES = {"wave_closed", "run_complete", "explicit_revocation"}
NESTED_SUBAGENT_ROLES = {"explorer", "researcher", "reviewer", "tester"}
PERMISSION_SELECTED_MODES = {
    "ask_for_approval",
    "approve_for_me",
    "full_access",
    "named_profile",
    "unknown",
}
PERMISSION_APPROVAL_POLICIES = {
    "untrusted",
    "on-request",
    "never",
    "granular",
    "unknown",
}
PERMISSION_FILESYSTEM_SCOPES = {
    "read_only",
    "workspace",
    "custom",
    "unrestricted",
    "unknown",
}
PERMISSION_NETWORK_SCOPES = {"disabled", "filtered", "open", "unknown"}
PERMISSION_LOCAL_BINDINGS = {"allowed", "blocked", "unknown"}
PERMISSION_INHERITANCE = {"inherited", "not_inherited", "unknown"}
PERMISSION_STATUSES = {"ready", "may_prompt", "blocked", "unknown"}


class ManifestError(ValueError):
    """Raised when a canonical manifest cannot be extracted or decoded."""


def extract_json_manifest(path: str | Path, heading: str, wrapper: str) -> dict[str, Any]:
    """Load the unique exact-heading JSON fence and return its wrapped object."""

    source = Path(path)
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    positions = [index for index, line in enumerate(lines) if line.strip() == heading]
    if len(positions) != 1:
        raise ManifestError(
            f"{source}: expected exactly one {heading!r}, found {len(positions)}"
        )
    index = positions[0] + 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or lines[index].strip() != "```json":
        raise ManifestError(f"{source}: first content after {heading!r} must be ```json")
    start = index + 1
    index = start
    while index < len(lines) and lines[index].strip() != "```":
        index += 1
    if index >= len(lines):
        raise ManifestError(f"{source}: unterminated JSON fence after {heading!r}")
    try:
        decoded = json.loads("\n".join(lines[start:index]))
    except json.JSONDecodeError as exc:
        raise ManifestError(f"{source}: invalid JSON: {exc}") from exc
    if not isinstance(decoded, dict) or set(decoded) != {wrapper}:
        raise ManifestError(f"{source}: JSON root must contain only {wrapper!r}")
    value = decoded[wrapper]
    if not isinstance(value, dict):
        raise ManifestError(f"{source}: {wrapper!r} must be an object")
    return value


def load_plan(path: str | Path) -> dict[str, Any]:
    return extract_json_manifest(path, PLAN_HEADING, "harness_plan")


def load_run(path: str | Path) -> dict[str, Any]:
    return extract_json_manifest(path, RUN_HEADING, "harness_run")


def load_worker_result(path: str | Path) -> dict[str, Any]:
    return extract_json_manifest(path, WORKER_HEADING, "worker_result")


def _canonicalize(value: Any, parent_key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {key: _canonicalize(value[key], key) for key in sorted(value)}
    if isinstance(value, list):
        normalized = [_canonicalize(item, parent_key) for item in value]
        if parent_key == "argv":
            return normalized
        if all(isinstance(item, dict) and isinstance(item.get("id"), str) for item in normalized):
            return sorted(normalized, key=lambda item: item["id"])
        if all(isinstance(item, dict) and isinstance(item.get("key"), str) for item in normalized):
            return sorted(normalized, key=lambda item: (item["key"], item.get("access", "")))
        if all(item is None or isinstance(item, (str, int, float, bool)) for item in normalized):
            return sorted(
                normalized,
                key=lambda item: json.dumps(item, ensure_ascii=False, separators=(",", ":")),
            )
        return normalized
    return value


def plan_digest(plan: dict[str, Any]) -> str:
    normalized = _canonicalize(plan)
    encoded = json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def is_full_sha(value: Any) -> bool:
    return isinstance(value, str) and SHA_RE.fullmatch(value) is not None


def validate_scope_claim(claim: Any) -> str | None:
    if not isinstance(claim, str) or not claim:
        return "must be a non-empty string"
    if claim.startswith("/") or "\\" in claim:
        return "must be a repository-relative POSIX path"
    if claim != claim.strip() or "//" in claim:
        return "must use canonical path spelling"
    if claim.startswith("!") or any(char in claim for char in "?[]{}"):
        return "contains unsupported glob syntax"
    wildcard_count = claim.count("*")
    if wildcard_count and not (claim.endswith("/**") and wildcard_count == 2):
        return "only one terminal /** wildcard is supported"
    base = claim[:-3] if claim.endswith("/**") else claim
    if not base or base.endswith("/"):
        return "has an empty or trailing path segment"
    segments = base.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        return "contains an empty, . or .. path segment"
    return None


def _claim_parts(claim: str, *, casefold: bool = False) -> tuple[tuple[str, ...], bool]:
    subtree = claim.endswith("/**")
    base = claim[:-3] if subtree else claim
    if casefold:
        base = base.casefold()
    return tuple(base.split("/")), subtree


def _parts_prefix(prefix: tuple[str, ...], value: tuple[str, ...]) -> bool:
    return len(prefix) <= len(value) and value[: len(prefix)] == prefix


def scope_overlap(left: str, right: str, *, casefold: bool = False) -> bool:
    left_parts, left_tree = _claim_parts(left, casefold=casefold)
    right_parts, right_tree = _claim_parts(right, casefold=casefold)
    if not left_tree and not right_tree:
        return left_parts == right_parts
    if left_tree and right_tree:
        return _parts_prefix(left_parts, right_parts) or _parts_prefix(right_parts, left_parts)
    if left_tree:
        return _parts_prefix(left_parts, right_parts)
    return _parts_prefix(right_parts, left_parts)


def scope_contains(parent: str, child: str) -> bool:
    parent_parts, parent_tree = _claim_parts(parent)
    child_parts, child_tree = _claim_parts(child)
    if not parent_tree:
        return not child_tree and parent_parts == child_parts
    if child_tree:
        return _parts_prefix(parent_parts, child_parts)
    return _parts_prefix(parent_parts, child_parts)


def path_in_scopes(path: str, scopes: Iterable[str]) -> bool:
    return any(scope_contains(scope, path) for scope in scopes)


def parent_owned_path(path: str) -> bool:
    base = path[:-3] if path.endswith("/**") else path
    name = base.rsplit("/", 1)[-1].casefold()
    return name in {"plan.md", "run.md"}


def mission_conflicts(left: dict[str, Any], right: dict[str, Any]) -> list[str]:
    reasons: set[str] = set()
    for left_scope in left.get("write_scope", []):
        for right_scope in right.get("write_scope", []):
            if scope_overlap(left_scope, right_scope):
                reasons.add("scope_overlap")
            elif scope_overlap(left_scope, right_scope, casefold=True):
                reasons.add("case_scope_collision")
    if set(left.get("serialized_resources", [])) & set(right.get("serialized_resources", [])):
        reasons.add("serialized_resource_conflict")
    left_resources = {item["key"]: item["access"] for item in left.get("runtime_resources", [])}
    right_resources = {item["key"]: item["access"] for item in right.get("runtime_resources", [])}
    for key in set(left_resources) & set(right_resources):
        if "exclusive" in {left_resources[key], right_resources[key]}:
            reasons.add("runtime_resource_conflict")
    return sorted(reasons)


def topological_levels(plan: dict[str, Any]) -> dict[str, int]:
    missions = {mission["id"]: mission for mission in plan.get("missions", [])}
    levels: dict[str, int] = {}

    def visit(mission_id: str, stack: set[str]) -> int:
        if mission_id in levels:
            return levels[mission_id]
        if mission_id in stack:
            raise ManifestError("mission dependency cycle")
        stack.add(mission_id)
        dependencies = missions[mission_id].get("depends_on", [])
        level = 0 if not dependencies else 1 + max(visit(dep, stack) for dep in dependencies)
        stack.remove(mission_id)
        levels[mission_id] = level
        return level

    for mission_id in sorted(missions):
        visit(mission_id, set())
    return levels


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _add(errors: list[str], path: str, message: str) -> None:
    errors.append(f"{path}: {message}")


def _keys(
    errors: list[str],
    path: str,
    value: Any,
    required: Iterable[str],
    optional: Iterable[str] = (),
) -> bool:
    if not isinstance(value, dict):
        _add(errors, path, "must be an object")
        return False
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        _add(errors, path, f"missing keys: {', '.join(missing)}")
    if unknown:
        _add(errors, path, f"unknown keys: {', '.join(unknown)}")
    return not missing and not unknown


def _strings(
    errors: list[str], path: str, value: Any, *, nonempty: bool = False
) -> list[str]:
    if not isinstance(value, list) or any(not _nonempty_string(item) for item in value):
        _add(errors, path, "must be a list of non-empty strings")
        return []
    if nonempty and not value:
        _add(errors, path, "must not be empty")
    if len(value) != len(set(value)):
        _add(errors, path, "must not contain duplicates")
    return value


def _validate_verifier(errors: list[str], path: str, value: Any) -> None:
    required = {"id", "cwd", "argv", "pass_signal"}
    if not _keys(errors, path, value, required):
        return
    for key in ("id", "cwd", "pass_signal"):
        if not _nonempty_string(value[key]):
            _add(errors, f"{path}.{key}", "must be a non-empty string")
    _strings(errors, f"{path}.argv", value["argv"], nonempty=True)


def _validate_scope_list(
    errors: list[str], path: str, value: Any, *, nonempty: bool = False
) -> list[str]:
    claims = _strings(errors, path, value, nonempty=nonempty)
    for index, claim in enumerate(claims):
        problem = validate_scope_claim(claim)
        if problem:
            _add(errors, f"{path}[{index}]", problem)
    return claims


def _cycle_nodes(edges: dict[str, list[str]]) -> set[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cyclic: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visiting:
            try:
                cyclic.update(trail[trail.index(node) :])
            except ValueError:
                cyclic.add(node)
            return
        if node in visited:
            return
        visiting.add(node)
        trail.append(node)
        for dependency in edges.get(node, []):
            if dependency in edges:
                visit(dependency, trail)
        trail.pop()
        visiting.remove(node)
        visited.add(node)

    for node in sorted(edges):
        visit(node, [])
    return cyclic


def validate_plan(plan: dict[str, Any]) -> list[str]:
    """Return deterministic validation errors for a harness_plan object."""

    errors: list[str] = []
    top_keys = {
        "schema_version",
        "plan_id",
        "revision",
        "objective",
        "max_parallel_workers",
        "sources",
        "traces",
        "ui_surfaces",
        "risks",
        "batch_verifiers",
        "final_gates",
        "missions",
    }
    if not _keys(errors, "plan", plan, top_keys):
        return sorted(errors)
    if plan["schema_version"] != 2:
        _add(errors, "plan.schema_version", "must equal 2")
    if not _nonempty_string(plan["plan_id"]):
        _add(errors, "plan.plan_id", "must be a non-empty string")
    if not _is_int(plan["revision"]) or plan["revision"] < 1:
        _add(errors, "plan.revision", "must be a positive integer")
    if not _nonempty_string(plan["objective"]):
        _add(errors, "plan.objective", "must be a non-empty string")
    if (
        not _is_int(plan["max_parallel_workers"])
        or not 1 <= plan["max_parallel_workers"] <= 3
    ):
        _add(errors, "plan.max_parallel_workers", "must be an integer from 1 to 3")

    sources: dict[str, dict[str, Any]] = {}
    if not isinstance(plan["sources"], list) or not plan["sources"]:
        _add(errors, "plan.sources", "must be a non-empty list")
    else:
        source_keys = {"id", "kind", "location", "owner", "status", "notes"}
        for index, source in enumerate(plan["sources"]):
            path = f"plan.sources[{index}]"
            if not _keys(errors, path, source, source_keys):
                continue
            for key in source_keys:
                if not _nonempty_string(source[key]):
                    _add(errors, f"{path}.{key}", "must be a non-empty string")
            source_id = source["id"]
            if source_id in sources:
                _add(errors, f"{path}.id", f"duplicate source ID {source_id!r}")
            sources[source_id] = source

    traces: dict[str, dict[str, Any]] = {}
    if not isinstance(plan["traces"], list) or not plan["traces"]:
        _add(errors, "plan.traces", "must be a non-empty list")
    else:
        trace_keys = {
            "id",
            "source_ids",
            "priority",
            "requirement",
            "disposition",
            "rationale",
        }
        for index, trace in enumerate(plan["traces"]):
            path = f"plan.traces[{index}]"
            if not _keys(errors, path, trace, trace_keys):
                continue
            trace_id = trace["id"]
            if not _nonempty_string(trace_id) or not ID_RE.fullmatch(trace_id):
                _add(errors, f"{path}.id", "must be a flat uppercase identifier")
            if trace_id in traces:
                _add(errors, f"{path}.id", f"duplicate trace ID {trace_id!r}")
            traces[trace_id] = trace
            source_ids = _strings(errors, f"{path}.source_ids", trace["source_ids"], nonempty=True)
            for source_id in source_ids:
                if source_id not in sources:
                    _add(errors, f"{path}.source_ids", f"unknown source {source_id!r}")
            if trace["priority"] not in {"must", "should", "could"}:
                _add(errors, f"{path}.priority", "must be must, should, or could")
            if trace["disposition"] not in {"planned", "deferred", "out_of_scope"}:
                _add(errors, f"{path}.disposition", "has an unsupported value")
            if not _nonempty_string(trace["requirement"]):
                _add(errors, f"{path}.requirement", "must be a non-empty string")
            if trace["disposition"] != "planned" and not _nonempty_string(trace["rationale"]):
                _add(errors, f"{path}.rationale", "is required when not planned")
            if trace["disposition"] == "planned" and trace["rationale"] is not None and not _nonempty_string(trace["rationale"]):
                _add(errors, f"{path}.rationale", "must be null or a non-empty string")

    if not isinstance(plan["ui_surfaces"], list):
        _add(errors, "plan.ui_surfaces", "must be a list")
    else:
        seen_ui: set[str] = set()
        ui_keys = {"id", "trace_ids", "route", "breakpoints", "states", "evidence_gate"}
        for index, surface in enumerate(plan["ui_surfaces"]):
            path = f"plan.ui_surfaces[{index}]"
            if not _keys(errors, path, surface, ui_keys):
                continue
            if not _nonempty_string(surface["id"]):
                _add(errors, f"{path}.id", "must be a non-empty string")
            elif surface["id"] in seen_ui:
                _add(errors, f"{path}.id", "must be unique")
            seen_ui.add(surface["id"])
            for trace_id in _strings(errors, f"{path}.trace_ids", surface["trace_ids"], nonempty=True):
                if trace_id not in traces:
                    _add(errors, f"{path}.trace_ids", f"unknown trace {trace_id!r}")
                elif traces[trace_id]["disposition"] != "planned":
                    _add(errors, f"{path}.trace_ids", f"trace {trace_id!r} is not planned")
            if not _nonempty_string(surface["route"]):
                _add(errors, f"{path}.route", "must be a non-empty string")
            _strings(errors, f"{path}.breakpoints", surface["breakpoints"], nonempty=True)
            _strings(errors, f"{path}.states", surface["states"], nonempty=True)
            if surface["evidence_gate"] not in {"required", "optional", "n/a"}:
                _add(errors, f"{path}.evidence_gate", "has an unsupported value")

    if not isinstance(plan["risks"], list):
        _add(errors, "plan.risks", "must be a list")
    else:
        seen_risks: set[str] = set()
        risk_keys = {"id", "description", "impact", "mitigation", "stop_condition"}
        for index, risk in enumerate(plan["risks"]):
            path = f"plan.risks[{index}]"
            if not _keys(errors, path, risk, risk_keys):
                continue
            for key in ("id", "description", "mitigation", "stop_condition"):
                if not _nonempty_string(risk[key]):
                    _add(errors, f"{path}.{key}", "must be a non-empty string")
            if risk["id"] in seen_risks:
                _add(errors, f"{path}.id", "must be unique")
            seen_risks.add(risk["id"])
            if risk["impact"] not in {"high", "medium", "low"}:
                _add(errors, f"{path}.impact", "must be high, medium, or low")

    for group in ("batch_verifiers", "final_gates"):
        if not isinstance(plan[group], list) or not plan[group]:
            _add(errors, f"plan.{group}", "must be a non-empty list")
        else:
            ids: set[str] = set()
            for index, verifier in enumerate(plan[group]):
                _validate_verifier(errors, f"plan.{group}[{index}]", verifier)
                if isinstance(verifier, dict) and isinstance(verifier.get("id"), str):
                    if verifier["id"] in ids:
                        _add(errors, f"plan.{group}[{index}].id", "must be unique")
                    ids.add(verifier["id"])

    missions: dict[str, dict[str, Any]] = {}
    if not isinstance(plan["missions"], list) or not plan["missions"]:
        _add(errors, "plan.missions", "must be a non-empty list")
        return sorted(set(errors))
    mission_keys = {
        "id",
        "alias",
        "objective",
        "priority",
        "merge_rank",
        "depends_on",
        "trace_ids",
        "write_scope",
        "deny_scope",
        "resource_inventory_complete",
        "serialized_resources",
        "runtime_resources",
        "worktree_eligible",
        "stop_conditions",
        "worker_verifiers",
        "integration_verifiers",
        "tasks",
    }
    for index, mission in enumerate(plan["missions"]):
        path = f"plan.missions[{index}]"
        if not _keys(errors, path, mission, mission_keys):
            continue
        mission_id = mission["id"]
        if not _nonempty_string(mission_id) or not ID_RE.fullmatch(mission_id):
            _add(errors, f"{path}.id", "must be a flat uppercase identifier")
        if mission_id in missions:
            _add(errors, f"{path}.id", f"duplicate mission ID {mission_id!r}")
        missions[mission_id] = mission

    task_records: dict[str, tuple[str, dict[str, Any], str]] = {}
    task_keys = {
        "id",
        "alias",
        "objective",
        "acceptance_matrix",
        "trace_ids",
        "depends_on",
        "parent_task",
        "legacy_task_ids",
        "replaced_by",
        "split_reason",
        "refinement_generation",
        "write_scope",
        "verifiers",
    }
    for index, mission in enumerate(plan["missions"]):
        if not isinstance(mission, dict) or not set(mission_keys).issubset(mission):
            continue
        mission_path = f"plan.missions[{index}]"
        mission_id = mission["id"]
        for key in ("alias", "objective"):
            if not _nonempty_string(mission[key]):
                _add(errors, f"{mission_path}.{key}", "must be a non-empty string")
        for key in ("priority", "merge_rank"):
            if not _is_int(mission[key]):
                _add(errors, f"{mission_path}.{key}", "must be an integer")
        _strings(errors, f"{mission_path}.depends_on", mission["depends_on"])
        mission_trace_ids = _strings(
            errors, f"{mission_path}.trace_ids", mission["trace_ids"], nonempty=True
        )
        for trace_id in mission_trace_ids:
            if trace_id not in traces:
                _add(errors, f"{mission_path}.trace_ids", f"unknown trace {trace_id!r}")
            elif traces[trace_id]["disposition"] != "planned":
                _add(errors, f"{mission_path}.trace_ids", f"trace {trace_id!r} is not planned")
        mission_write = _validate_scope_list(
            errors, f"{mission_path}.write_scope", mission["write_scope"], nonempty=True
        )
        mission_deny = _validate_scope_list(errors, f"{mission_path}.deny_scope", mission["deny_scope"])
        for claim in mission_write:
            if parent_owned_path(claim) and not any(scope_contains(deny, claim) for deny in mission_deny):
                _add(errors, f"{mission_path}.write_scope", f"parent-owned claim {claim!r}")
        if not isinstance(mission["resource_inventory_complete"], bool):
            _add(errors, f"{mission_path}.resource_inventory_complete", "must be boolean")
        serialized = _strings(
            errors, f"{mission_path}.serialized_resources", mission["serialized_resources"]
        )
        if any(not item.strip() for item in serialized):
            _add(errors, f"{mission_path}.serialized_resources", "contains an empty key")
        if not isinstance(mission["runtime_resources"], list):
            _add(errors, f"{mission_path}.runtime_resources", "must be a list")
        else:
            resource_map: dict[str, str] = {}
            for resource_index, resource in enumerate(mission["runtime_resources"]):
                resource_path = f"{mission_path}.runtime_resources[{resource_index}]"
                if not _keys(errors, resource_path, resource, {"key", "access"}):
                    continue
                if not _nonempty_string(resource["key"]):
                    _add(errors, f"{resource_path}.key", "must be a non-empty string")
                if resource["access"] not in {"exclusive", "shared_read"}:
                    _add(errors, f"{resource_path}.access", "has an unsupported value")
                if resource["key"] in resource_map:
                    _add(errors, f"{resource_path}.key", "must be unique")
                resource_map[resource["key"]] = resource["access"]
        if not isinstance(mission["worktree_eligible"], bool):
            _add(errors, f"{mission_path}.worktree_eligible", "must be boolean")
        _strings(errors, f"{mission_path}.stop_conditions", mission["stop_conditions"], nonempty=True)
        for verifier_group in ("worker_verifiers", "integration_verifiers"):
            values = mission[verifier_group]
            if not isinstance(values, list) or not values:
                _add(errors, f"{mission_path}.{verifier_group}", "must be a non-empty list")
            else:
                ids: set[str] = set()
                for verifier_index, verifier in enumerate(values):
                    _validate_verifier(
                        errors,
                        f"{mission_path}.{verifier_group}[{verifier_index}]",
                        verifier,
                    )
                    if isinstance(verifier, dict) and isinstance(verifier.get("id"), str):
                        if verifier["id"] in ids:
                            _add(errors, f"{mission_path}.{verifier_group}[{verifier_index}].id", "must be unique")
                        ids.add(verifier["id"])
        if not isinstance(mission["tasks"], list) or not mission["tasks"]:
            _add(errors, f"{mission_path}.tasks", "must be a non-empty list")
            continue
        for task_index, task in enumerate(mission["tasks"]):
            task_path = f"{mission_path}.tasks[{task_index}]"
            if not _keys(errors, task_path, task, task_keys):
                continue
            task_id = task["id"]
            match = TASK_ID_RE.fullmatch(task_id) if isinstance(task_id, str) else None
            if not match or match.group(1) != mission_id:
                _add(errors, f"{task_path}.id", "must be a flat ID prefixed by its mission")
            if task_id in task_records:
                _add(errors, f"{task_path}.id", f"duplicate task ID {task_id!r}")
            task_records[task_id] = (mission_id, task, task_path)

    mission_edges: dict[str, list[str]] = {}
    for mission_id, mission in missions.items():
        deps = mission.get("depends_on", []) if isinstance(mission, dict) else []
        mission_edges[mission_id] = deps if isinstance(deps, list) else []
        for dependency in mission_edges[mission_id]:
            if dependency not in missions:
                _add(errors, f"mission {mission_id}.depends_on", f"unknown mission {dependency!r}")
            if dependency == mission_id:
                _add(errors, f"mission {mission_id}.depends_on", "cannot depend on itself")
    cyclic_missions = _cycle_nodes(mission_edges)
    if cyclic_missions:
        _add(errors, "plan.missions", f"dependency cycle includes {', '.join(sorted(cyclic_missions))}")

    task_edges: dict[str, list[str]] = {}
    parent_edges: dict[str, list[str]] = {}
    legacy_owner: dict[str, str] = {}
    planned_trace_coverage: set[str] = set()
    for task_id, (mission_id, task, path) in task_records.items():
        for key in ("alias", "objective"):
            if not _nonempty_string(task[key]):
                _add(errors, f"{path}.{key}", "must be a non-empty string")
        _strings(errors, f"{path}.acceptance_matrix", task["acceptance_matrix"])
        trace_ids = _strings(errors, f"{path}.trace_ids", task["trace_ids"], nonempty=True)
        for trace_id in trace_ids:
            if trace_id not in traces:
                _add(errors, f"{path}.trace_ids", f"unknown trace {trace_id!r}")
            elif traces[trace_id]["disposition"] != "planned":
                _add(errors, f"{path}.trace_ids", f"trace {trace_id!r} is not planned")
            else:
                planned_trace_coverage.add(trace_id)
            mission_trace_set = set(missions.get(mission_id, {}).get("trace_ids", []))
            if trace_id not in mission_trace_set:
                _add(errors, f"{path}.trace_ids", f"trace {trace_id!r} is not declared by its mission")
        dependencies = _strings(errors, f"{path}.depends_on", task["depends_on"])
        task_edges[task_id] = dependencies
        for dependency in dependencies:
            if dependency not in task_records:
                _add(errors, f"{path}.depends_on", f"unknown task {dependency!r}")
            elif task_records[dependency][0] != mission_id:
                _add(errors, f"{path}.depends_on", "cross-mission task dependency is forbidden")
        legacy_ids = _strings(errors, f"{path}.legacy_task_ids", task["legacy_task_ids"])
        for legacy_id in legacy_ids:
            if legacy_id in legacy_owner:
                _add(errors, f"{path}.legacy_task_ids", f"legacy ID also owned by {legacy_owner[legacy_id]}")
            legacy_owner[legacy_id] = task_id
        replacements = _strings(errors, f"{path}.replaced_by", task["replaced_by"])
        generation = task["refinement_generation"]
        if not _is_int(generation) or generation not in {0, 1}:
            _add(errors, f"{path}.refinement_generation", "must be 0 or 1")
        parent = task["parent_task"]
        if generation == 0:
            if parent is not None or task["split_reason"] is not None:
                _add(errors, path, "generation-0 task must have null parent_task and split_reason")
        elif generation == 1:
            if not _nonempty_string(parent) or not _nonempty_string(task["split_reason"]):
                _add(errors, path, "generation-1 task requires parent_task and split_reason")
            if replacements:
                _add(errors, f"{path}.replaced_by", "generation-1 task cannot be split again")
        parent_edges[task_id] = [parent] if isinstance(parent, str) else []
        if isinstance(parent, str):
            if parent not in task_records:
                _add(errors, f"{path}.parent_task", f"unknown task {parent!r}")
            elif task_records[parent][0] != mission_id:
                _add(errors, f"{path}.parent_task", "must be in the same mission")
            elif task_id not in task_records[parent][1].get("replaced_by", []):
                _add(errors, f"{path}.parent_task", "parent does not list this replacement")
        for replacement in replacements:
            if replacement not in task_records:
                _add(errors, f"{path}.replaced_by", f"unknown task {replacement!r}")
            elif task_records[replacement][0] != mission_id:
                _add(errors, f"{path}.replaced_by", "replacement must be in the same mission")
            elif task_records[replacement][1].get("parent_task") != task_id:
                _add(errors, f"{path}.replaced_by", f"replacement {replacement!r} does not point back")
        task_scopes = _validate_scope_list(errors, f"{path}.write_scope", task["write_scope"], nonempty=True)
        mission = missions.get(mission_id, {})
        mission_scopes = mission.get("write_scope", []) if isinstance(mission, dict) else []
        mission_denies = mission.get("deny_scope", []) if isinstance(mission, dict) else []
        for claim in task_scopes:
            if not any(scope_contains(parent_scope, claim) for parent_scope in mission_scopes):
                _add(errors, f"{path}.write_scope", f"claim {claim!r} escapes mission scope")
            if any(scope_overlap(deny, claim) for deny in mission_denies):
                _add(errors, f"{path}.write_scope", f"claim {claim!r} overlaps mission deny scope")
        if not isinstance(task["verifiers"], list) or not task["verifiers"]:
            _add(errors, f"{path}.verifiers", "must be a non-empty list")
        else:
            verifier_ids: set[str] = set()
            for verifier_index, verifier in enumerate(task["verifiers"]):
                _validate_verifier(errors, f"{path}.verifiers[{verifier_index}]", verifier)
                if isinstance(verifier, dict) and isinstance(verifier.get("id"), str):
                    if verifier["id"] in verifier_ids:
                        _add(errors, f"{path}.verifiers[{verifier_index}].id", "must be unique")
                    verifier_ids.add(verifier["id"])

    for task_id, dependencies in task_edges.items():
        for dependency in dependencies:
            if dependency in task_records and task_records[dependency][1].get("replaced_by"):
                _add(errors, f"task {task_id}.depends_on", f"cannot target superseded task {dependency!r}")
    cyclic_tasks = _cycle_nodes(task_edges)
    if cyclic_tasks:
        _add(errors, "plan.tasks", f"dependency cycle includes {', '.join(sorted(cyclic_tasks))}")
    cyclic_parents = _cycle_nodes(parent_edges)
    if cyclic_parents:
        _add(errors, "plan.tasks", f"parent cycle includes {', '.join(sorted(cyclic_parents))}")

    for legacy_id, owner in legacy_owner.items():
        if legacy_id in task_records:
            _add(errors, f"task {owner}.legacy_task_ids", f"legacy ID collides with canonical task {legacy_id!r}")

    for trace_id, trace in traces.items():
        if trace.get("disposition") == "planned" and trace_id not in planned_trace_coverage:
            _add(errors, f"trace {trace_id}", "planned trace has no task coverage")

    return sorted(set(errors))


def _optional_string(errors: list[str], path: str, value: Any) -> None:
    if value is not None and not _nonempty_string(value):
        _add(errors, path, "must be null or a non-empty string")


def _optional_sha(errors: list[str], path: str, value: Any) -> None:
    if value is not None and not is_full_sha(value):
        _add(errors, path, "must be null or a full lowercase Git SHA")


def _optional_nonnegative_int(errors: list[str], path: str, value: Any) -> None:
    if value is not None and (not _is_int(value) or value < 0):
        _add(errors, path, "must be null or a non-negative integer")


def _validate_landing(errors: list[str], value: Any) -> None:
    path = "run.landing"
    keys = {
        "mode",
        "remote",
        "head_branch",
        "base_branch",
        "pushed_head_sha",
        "pr_number",
        "pr_url",
        "pr_state",
        "pr_head_sha",
        "checks_status",
        "checks_head_sha",
        "review_status",
        "review_head_sha",
        "blocking_findings",
        "unresolved_threads",
        "merge_status",
        "merged_sha",
    }
    if not _keys(errors, path, value, keys):
        return

    if value["mode"] not in {"local_only", "pull_request"}:
        _add(errors, f"{path}.mode", "must be local_only or pull_request")
    for key in ("remote", "head_branch", "base_branch", "pr_url"):
        _optional_string(errors, f"{path}.{key}", value[key])
    for key in (
        "pushed_head_sha",
        "pr_head_sha",
        "checks_head_sha",
        "review_head_sha",
        "merged_sha",
    ):
        _optional_sha(errors, f"{path}.{key}", value[key])
    _optional_nonnegative_int(errors, f"{path}.blocking_findings", value["blocking_findings"])
    _optional_nonnegative_int(errors, f"{path}.unresolved_threads", value["unresolved_threads"])

    if value["pr_number"] is not None and (
        not _is_int(value["pr_number"]) or value["pr_number"] < 1
    ):
        _add(errors, f"{path}.pr_number", "must be null or a positive integer")
    if value["pr_state"] not in {"not_created", "draft", "open", "closed", "merged"}:
        _add(errors, f"{path}.pr_state", "has an unsupported value")
    if value["checks_status"] not in {"not_started", "pending", "PASS", "FAIL", "BLOCKED"}:
        _add(errors, f"{path}.checks_status", "has an unsupported value")
    if value["review_status"] not in {
        "not_requested",
        "pending",
        "PASS",
        "CHANGES_REQUESTED",
        "BLOCKED",
    }:
        _add(errors, f"{path}.review_status", "has an unsupported value")
    if value["merge_status"] not in {"not_ready", "ready", "merged", "closed_unmerged"}:
        _add(errors, f"{path}.merge_status", "has an unsupported value")

    if (
        _nonempty_string(value["head_branch"])
        and _nonempty_string(value["base_branch"])
        and value["head_branch"] == value["base_branch"]
    ):
        _add(errors, path, "head_branch and base_branch must differ")

    created_states = {"draft", "open", "closed", "merged"}
    if value["pr_state"] in created_states:
        required_created = (
            "remote",
            "head_branch",
            "base_branch",
            "pushed_head_sha",
            "pr_number",
            "pr_url",
            "pr_head_sha",
        )
        if any(value[key] is None for key in required_created):
            _add(errors, path, "created PR state is missing remote, branch, URL, number, or head data")
        if value["pr_head_sha"] != value["pushed_head_sha"]:
            _add(errors, path, "pr_head_sha must match pushed_head_sha")
    elif value["pr_state"] == "not_created":
        if any(value[key] is not None for key in ("pr_number", "pr_url", "pr_head_sha")):
            _add(errors, path, "not_created PR must not record number, URL, or PR head")

    if value["mode"] == "local_only" and value["pr_state"] != "not_created":
        _add(errors, path, "local_only mode cannot record a created PR")
    if value["checks_status"] == "PASS" and (
        value["pr_state"] not in created_states
        or value["checks_head_sha"] is None
        or value["checks_head_sha"] != value["pr_head_sha"]
    ):
        _add(errors, path, "PASS checks must bind to a created PR's current head")
    if value["review_status"] == "PASS":
        if (
            value["pr_state"] not in created_states
            or value["review_head_sha"] is None
            or value["review_head_sha"] != value["pr_head_sha"]
        ):
            _add(errors, path, "PASS review must bind to a created PR's current head")
        if value["blocking_findings"] != 0 or value["unresolved_threads"] != 0:
            _add(errors, path, "PASS review requires zero blocking findings and unresolved threads")
    if value["merge_status"] in {"ready", "merged"} and (
        value["pr_state"] != ("open" if value["merge_status"] == "ready" else "merged")
        or value["checks_status"] != "PASS"
        or value["review_status"] != "PASS"
        or value["checks_head_sha"] != value["pr_head_sha"]
        or value["review_head_sha"] != value["pr_head_sha"]
    ):
        _add(
            errors,
            path,
            f"{value['merge_status']} status requires the matching PR state with current-head PASS checks and review",
        )
    if value["merge_status"] == "merged" and (
        value["pr_state"] != "merged" or value["merged_sha"] is None
    ):
        _add(errors, path, "merged status requires a merged PR and merged_sha")
    if value["pr_state"] == "merged" and value["merge_status"] != "merged":
        _add(errors, path, "merged PR requires merge_status merged")
    if value["merge_status"] == "closed_unmerged" and value["pr_state"] != "closed":
        _add(errors, path, "closed_unmerged requires a closed PR")
    if value["pr_state"] == "closed" and value["merge_status"] != "closed_unmerged":
        _add(errors, path, "closed PR requires merge_status closed_unmerged")
    if value["merge_status"] == "closed_unmerged" and value["merged_sha"] is not None:
        _add(errors, path, "closed_unmerged must not record merged_sha")


def _validate_authorization_scope(
    errors: list[str], path: str, value: Any, *, action: bool
) -> None:
    required = {"run_id", "mission_ids", "targets"} if action else {"run_id", "mission_ids", "expires_when"}
    if not _keys(errors, path, value, required):
        return
    if not _nonempty_string(value["run_id"]):
        _add(errors, f"{path}.run_id", "must be a non-empty string")
    _strings(errors, f"{path}.mission_ids", value["mission_ids"], nonempty=True)
    if action:
        targets = _strings(errors, f"{path}.targets", value["targets"], nonempty=True)
        for target in targets:
            if target != "*" and not TARGET_RE.fullmatch(target):
                _add(errors, f"{path}.targets", f"unsupported target {target!r}")
    else:
        if value["expires_when"] not in EXPIRY_BOUNDARIES:
            _add(
                errors,
                f"{path}.expires_when",
                "must be wave_closed, run_complete, or explicit_revocation",
            )


def authorization_covers(
    run: dict[str, Any], action: str, mission_id: str, target: str | None = None
) -> bool:
    entry = run.get("authorizations", {}).get(action, {})
    if not isinstance(entry, dict) or entry.get("authorized") is not True:
        return False
    scope = entry.get("scope")
    if not isinstance(scope, dict) or scope.get("run_id") != run.get("run_id"):
        return False
    missions = scope.get("mission_ids", [])
    if mission_id not in missions and "*" not in missions:
        return False
    targets = scope.get("targets", [])
    if target is not None and target not in targets and "*" not in targets:
        return False
    return _nonempty_string(entry.get("source")) and _authorization_not_expired(
        run, entry.get("expires_when")
    )


def execution_covers(run: dict[str, Any], mission_id: str) -> bool:
    if run.get("execution_authorized") is not True:
        return False
    if not _nonempty_string(run.get("execution_authorization_source")):
        return False
    scope = run.get("execution_authorization_scope")
    if not isinstance(scope, dict) or scope.get("run_id") != run.get("run_id"):
        return False
    missions = scope.get("mission_ids", [])
    return (mission_id in missions or "*" in missions) and _authorization_not_expired(
        run, scope.get("expires_when")
    )


def _authorization_not_expired(run: dict[str, Any], boundary: Any) -> bool:
    if boundary == "explicit_revocation":
        return True
    if boundary == "run_complete":
        return run.get("status") != "complete"
    if boundary == "wave_closed":
        return run.get("active_wave", {}).get("status") not in {"closed", "superseded"}
    return False


def validate_run(plan: dict[str, Any], run: dict[str, Any]) -> list[str]:
    """Validate a plan-backed harness_run object and cross-plan consistency."""

    errors: list[str] = []
    run_keys = {
        "schema_version",
        "run_id",
        "plan",
        "status",
        "intent",
        "plan_readiness",
        "execution_authorized",
        "execution_authorization_source",
        "execution_authorization_scope",
        "authorizations",
        "runtime_capabilities",
        "observed",
        "integration",
        "mission_states",
        "task_states",
        "active_wave",
        "workers",
        "attempt_log",
    }
    schema_version = run.get("schema_version") if isinstance(run, dict) else None
    if schema_version == 3:
        run_keys.add("landing")
    if not _keys(errors, "run", run, run_keys):
        return sorted(errors)
    if schema_version not in {2, 3}:
        _add(errors, "run.schema_version", "must equal 2 or 3")
    if not _nonempty_string(run["run_id"]):
        _add(errors, "run.run_id", "must be a non-empty string")
    if run["status"] not in {"draft", "ready", "running", "blocked", "complete"}:
        _add(errors, "run.status", "has an unsupported value")
    if run["intent"] not in {
        "plan-only",
        "plan-then-stop",
        "plan-then-execute",
        "execute-ready-plan",
    }:
        _add(errors, "run.intent", "has an unsupported value")
    if run["plan_readiness"] not in {"draft", "ready", "blocked"}:
        _add(errors, "run.plan_readiness", "has an unsupported value")
    if not isinstance(run["execution_authorized"], bool):
        _add(errors, "run.execution_authorized", "must be boolean")
    if run["execution_authorized"]:
        if not _nonempty_string(run["execution_authorization_source"]):
            _add(errors, "run.execution_authorization_source", "is required when authorized")
        _validate_authorization_scope(
            errors,
            "run.execution_authorization_scope",
            run["execution_authorization_scope"],
            action=False,
        )
        if isinstance(run["execution_authorization_scope"], dict) and run["execution_authorization_scope"].get("run_id") != run["run_id"]:
            _add(errors, "run.execution_authorization_scope.run_id", "must match run_id")
    else:
        _optional_string(
            errors, "run.execution_authorization_source", run["execution_authorization_source"]
        )
        if run["execution_authorization_scope"] is not None:
            _add(errors, "run.execution_authorization_scope", "must be null when unauthorized")

    if _keys(errors, "run.plan", run["plan"], {"id", "revision", "digest_sha256"}):
        if run["plan"]["id"] != plan.get("plan_id"):
            _add(errors, "run.plan.id", "does not match PLAN")
        if run["plan"]["revision"] != plan.get("revision"):
            _add(errors, "run.plan.revision", "does not match PLAN")
        digest = plan_digest(plan)
        if run["plan"]["digest_sha256"] != digest:
            _add(errors, "run.plan.digest_sha256", f"does not match semantic PLAN digest {digest}")

    authorization_keys = AUTHORIZATION_KEYS if schema_version == 3 else AUTHORIZATION_KEYS_V2
    authorizations = run["authorizations"]
    if not isinstance(authorizations, dict):
        _add(errors, "run.authorizations", "must be an object")
    else:
        missing = sorted(set(authorization_keys) - set(authorizations))
        unknown = sorted(set(authorizations) - set(authorization_keys))
        if missing:
            _add(errors, "run.authorizations", f"missing keys: {', '.join(missing)}")
        if unknown:
            _add(errors, "run.authorizations", f"unknown keys: {', '.join(unknown)}")
        for action in authorization_keys:
            if action not in authorizations:
                continue
            entry = authorizations[action]
            path = f"run.authorizations.{action}"
            if not _keys(errors, path, entry, {"authorized", "source"}, {"scope", "expires_when"}):
                continue
            if not isinstance(entry["authorized"], bool):
                _add(errors, f"{path}.authorized", "must be boolean")
            if entry["authorized"]:
                if not _nonempty_string(entry["source"]):
                    _add(errors, f"{path}.source", "is required when authorized")
                if "scope" not in entry or "expires_when" not in entry:
                    _add(errors, path, "authorized action requires scope and expires_when")
                else:
                    _validate_authorization_scope(errors, f"{path}.scope", entry["scope"], action=True)
                    if isinstance(entry["scope"], dict) and entry["scope"].get("run_id") != run["run_id"]:
                        _add(errors, f"{path}.scope.run_id", "must match run_id")
                    if entry["expires_when"] not in EXPIRY_BOUNDARIES:
                        _add(
                            errors,
                            f"{path}.expires_when",
                            "must be wave_closed, run_complete, or explicit_revocation",
                        )
            else:
                if entry["source"] is not None:
                    _add(errors, f"{path}.source", "must be null when unauthorized")
                if "scope" in entry or "expires_when" in entry:
                    _add(errors, path, "unauthorized action must omit scope and expires_when")

    if schema_version == 3:
        _validate_landing(errors, run["landing"])

    runtime_keys = {
        "worker_runtime",
        "workspace_mode",
        "completion_channel",
        "max_parallel_workers",
        "platform_lifecycle",
    }
    runtime = run["runtime_capabilities"]
    if _keys(
        errors,
        "run.runtime_capabilities",
        runtime,
        runtime_keys,
        {"nested_subagents", "permission_boundary"},
    ):
        if runtime["worker_runtime"] not in {"parent", "subagent", "app_task"}:
            _add(errors, "run.runtime_capabilities.worker_runtime", "has an unsupported value")
        if runtime["workspace_mode"] not in {
            "shared_checkout",
            "parent_managed_worktree",
            "app_managed_worktree",
        }:
            _add(errors, "run.runtime_capabilities.workspace_mode", "has an unsupported value")
        if runtime["completion_channel"] not in {
            "agent_result",
            "thread_poll",
            "report_file",
            "user_relay",
        }:
            _add(errors, "run.runtime_capabilities.completion_channel", "has an unsupported value")
        if not _is_int(runtime["max_parallel_workers"]) or not 1 <= runtime["max_parallel_workers"] <= 3:
            _add(errors, "run.runtime_capabilities.max_parallel_workers", "must be 1..3")
        permission = runtime.get("permission_boundary")
        if permission is not None and _keys(
            errors,
            "run.runtime_capabilities.permission_boundary",
            permission,
            {
                "selected_mode",
                "profile_name",
                "approval_policy",
                "filesystem_scope",
                "network_scope",
                "local_binding",
                "worker_inheritance",
                "status",
            },
        ):
            permission_path = "run.runtime_capabilities.permission_boundary"
            if permission["selected_mode"] not in PERMISSION_SELECTED_MODES:
                _add(errors, f"{permission_path}.selected_mode", "has an unsupported value")
            profile_name = permission["profile_name"]
            if permission["selected_mode"] == "named_profile":
                if not _nonempty_string(profile_name):
                    _add(errors, f"{permission_path}.profile_name", "is required for named_profile")
            elif profile_name is not None:
                _add(errors, f"{permission_path}.profile_name", "must be null unless selected_mode is named_profile")
            if permission["approval_policy"] not in PERMISSION_APPROVAL_POLICIES:
                _add(errors, f"{permission_path}.approval_policy", "has an unsupported value")
            if permission["filesystem_scope"] not in PERMISSION_FILESYSTEM_SCOPES:
                _add(errors, f"{permission_path}.filesystem_scope", "has an unsupported value")
            if permission["network_scope"] not in PERMISSION_NETWORK_SCOPES:
                _add(errors, f"{permission_path}.network_scope", "has an unsupported value")
            if permission["local_binding"] not in PERMISSION_LOCAL_BINDINGS:
                _add(errors, f"{permission_path}.local_binding", "has an unsupported value")
            if permission["worker_inheritance"] not in PERMISSION_INHERITANCE:
                _add(errors, f"{permission_path}.worker_inheritance", "has an unsupported value")
            if permission["status"] not in PERMISSION_STATUSES:
                _add(errors, f"{permission_path}.status", "has an unsupported value")
            if permission["status"] == "ready" and "unknown" in {
                permission["selected_mode"],
                permission["approval_policy"],
                permission["filesystem_scope"],
                permission["network_scope"],
                permission["local_binding"],
                permission["worker_inheritance"],
            }:
                _add(errors, permission_path, "cannot be ready while a boundary field is unknown")
            if permission["selected_mode"] == "full_access" and (
                permission["approval_policy"] != "never"
                or permission["filesystem_scope"] != "unrestricted"
                or permission["network_scope"] != "open"
                or permission["local_binding"] != "allowed"
            ):
                _add(
                    errors,
                    permission_path,
                    "full_access requires never, unrestricted filesystem, open network, and allowed local binding",
                )
        nested = runtime.get("nested_subagents")
        if nested is not None and _keys(
            errors,
            "run.runtime_capabilities.nested_subagents",
            nested,
            {
                "available",
                "max_depth",
                "max_children_per_worker",
                "allowed_roles",
                "write_policy",
                "completion_channel",
            },
        ):
            if not isinstance(nested["available"], bool):
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents.available",
                    "must be boolean",
                )
            if nested["max_depth"] != 1:
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents.max_depth",
                    "must equal 1",
                )
            if (
                not _is_int(nested["max_children_per_worker"])
                or not 1 <= nested["max_children_per_worker"] <= 3
            ):
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents.max_children_per_worker",
                    "must be 1..3",
                )
            roles = _strings(
                errors,
                "run.runtime_capabilities.nested_subagents.allowed_roles",
                nested["allowed_roles"],
                nonempty=True,
            )
            unknown_roles = sorted(set(roles) - NESTED_SUBAGENT_ROLES)
            if unknown_roles:
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents.allowed_roles",
                    f"unsupported roles: {', '.join(unknown_roles)}",
                )
            if nested["write_policy"] != "read_only":
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents.write_policy",
                    "must equal read_only",
                )
            if nested["completion_channel"] != "agent_result":
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents.completion_channel",
                    "must equal agent_result",
                )
        lifecycle = runtime["platform_lifecycle"]
        if _keys(
            errors,
            "run.runtime_capabilities.platform_lifecycle",
            lifecycle,
            {"owner", "automatic_retention_cleanup_possible", "durable_branch_required_before_unique_work"},
        ):
            if lifecycle["owner"] not in {"parent", "app"}:
                _add(errors, "run.runtime_capabilities.platform_lifecycle.owner", "must be parent or app")
            for key in ("automatic_retention_cleanup_possible", "durable_branch_required_before_unique_work"):
                if not isinstance(lifecycle[key], bool):
                    _add(errors, f"run.runtime_capabilities.platform_lifecycle.{key}", "must be boolean")

    observed = run["observed"]
    if _keys(errors, "run.observed", observed, {"captured_at", "git", "runtime"}):
        _optional_string(errors, "run.observed.captured_at", observed["captured_at"])
        git = observed["git"]
        if _keys(errors, "run.observed.git", git, {"parent_branch", "parent_head_sha", "parent_dirty", "worktrees"}):
            _optional_string(errors, "run.observed.git.parent_branch", git["parent_branch"])
            _optional_sha(errors, "run.observed.git.parent_head_sha", git["parent_head_sha"])
            if git["parent_dirty"] is not None and not isinstance(git["parent_dirty"], bool):
                _add(errors, "run.observed.git.parent_dirty", "must be null or boolean")
            if not isinstance(git["worktrees"], list):
                _add(errors, "run.observed.git.worktrees", "must be a list")
            else:
                for index, worktree in enumerate(git["worktrees"]):
                    path = f"run.observed.git.worktrees[{index}]"
                    if _keys(errors, path, worktree, {"path", "branch_ref", "head_sha", "managed_by", "dirty"}):
                        if not _nonempty_string(worktree["path"]):
                            _add(errors, f"{path}.path", "must be a non-empty string")
                        _optional_string(errors, f"{path}.branch_ref", worktree["branch_ref"])
                        _optional_sha(errors, f"{path}.head_sha", worktree["head_sha"])
                        if worktree["managed_by"] not in {"parent", "app"}:
                            _add(errors, f"{path}.managed_by", "must be parent or app")
                        if not isinstance(worktree["dirty"], bool):
                            _add(errors, f"{path}.dirty", "must be boolean")
        observed_runtime = observed["runtime"]
        if _keys(errors, "run.observed.runtime", observed_runtime, {"available_worker_slots", "isolation_capacity", "completion_channel_available"}):
            for key in ("available_worker_slots", "isolation_capacity"):
                if not _is_int(observed_runtime[key]) or observed_runtime[key] < 0:
                    _add(errors, f"run.observed.runtime.{key}", "must be a non-negative integer")
            if not isinstance(observed_runtime["completion_channel_available"], bool):
                _add(errors, "run.observed.runtime.completion_channel_available", "must be boolean")

    integration = run["integration"]
    if _keys(errors, "run.integration", integration, {"branch", "batch_base_sha", "integration_head_sha"}):
        _optional_string(errors, "run.integration.branch", integration["branch"])
        _optional_sha(errors, "run.integration.batch_base_sha", integration["batch_base_sha"])
        _optional_sha(errors, "run.integration.integration_head_sha", integration["integration_head_sha"])
        if (
            schema_version == 3
            and isinstance(run["landing"], dict)
            and run["landing"].get("merge_status") in {"ready", "merged"}
            and run["landing"].get("pr_head_sha") != integration["integration_head_sha"]
        ):
            _add(
                errors,
                "run.landing",
                "ready or merged status requires the current PR head to match integration_head_sha",
            )

    mission_ids = {mission["id"] for mission in plan.get("missions", []) if isinstance(mission, dict) and "id" in mission}
    task_ids = {
        task["id"]
        for mission in plan.get("missions", [])
        if isinstance(mission, dict)
        for task in mission.get("tasks", [])
        if isinstance(task, dict) and "id" in task
    }
    mission_states = run["mission_states"]
    mission_state_keys = {
        "phase",
        "lease_id",
        "lease_plan_revision",
        "lease_plan_digest_sha256",
        "worker_id",
        "base_sha",
        "head_sha",
        "integration_gate",
        "integrated_sha",
        "blockers",
        "report_path",
    }
    if not isinstance(mission_states, dict):
        _add(errors, "run.mission_states", "must be an object")
    else:
        if set(mission_states) != mission_ids:
            _add(errors, "run.mission_states", "keys must exactly match PLAN missions")
        for mission_id, state in mission_states.items():
            path = f"run.mission_states.{mission_id}"
            if not _keys(errors, path, state, mission_state_keys):
                continue
            if state["phase"] not in MISSION_PHASES:
                _add(errors, f"{path}.phase", "has an unsupported value")
            for key in ("lease_id", "worker_id", "report_path"):
                _optional_string(errors, f"{path}.{key}", state[key])
            if state["lease_plan_revision"] is not None and (
                not _is_int(state["lease_plan_revision"]) or state["lease_plan_revision"] < 1
            ):
                _add(errors, f"{path}.lease_plan_revision", "must be null or positive integer")
            for key in ("lease_plan_digest_sha256", "base_sha", "head_sha", "integrated_sha"):
                _optional_sha(errors, f"{path}.{key}", state[key])
            if state["integration_gate"] not in GATE_VALUES:
                _add(errors, f"{path}.integration_gate", "has an unsupported gate value")
            _strings(errors, f"{path}.blockers", state["blockers"])
            leased = state["phase"] in {"leased", "worker_running", "worker_passed", "integrating"}
            if leased and any(
                state[key] is None
                for key in ("lease_id", "lease_plan_revision", "lease_plan_digest_sha256", "worker_id", "base_sha")
            ):
                _add(errors, path, "leased/running mission is missing lease bindings")
            if state["phase"] == "integrated" and (
                state["integration_gate"] != "PASS" or state["integrated_sha"] is None
            ):
                _add(errors, path, "integrated mission requires PASS gate and integrated_sha")

    task_states = run["task_states"]
    task_state_keys = {
        "phase",
        "attempts",
        "commit_sha",
        "verifier_status",
        "blockers",
        "refinement_request",
    }
    if not isinstance(task_states, dict):
        _add(errors, "run.task_states", "must be an object")
    else:
        if set(task_states) != task_ids:
            _add(errors, "run.task_states", "keys must exactly match PLAN tasks")
        for task_id, state in task_states.items():
            path = f"run.task_states.{task_id}"
            if not _keys(errors, path, state, task_state_keys):
                continue
            if state["phase"] not in TASK_PHASES:
                _add(errors, f"{path}.phase", "has an unsupported value")
            if not _is_int(state["attempts"]) or state["attempts"] < 0:
                _add(errors, f"{path}.attempts", "must be a non-negative integer")
            _optional_sha(errors, f"{path}.commit_sha", state["commit_sha"])
            if state["verifier_status"] not in GATE_VALUES:
                _add(errors, f"{path}.verifier_status", "has an unsupported gate value")
            _strings(errors, f"{path}.blockers", state["blockers"])
            if state["refinement_request"] is not None and not isinstance(
                state["refinement_request"], dict
            ):
                _add(errors, f"{path}.refinement_request", "must be null or an object")

    wave = run["active_wave"]
    wave_keys = {
        "wave_id",
        "status",
        "plan_revision",
        "plan_digest_sha256",
        "batch_base_sha",
        "selected_missions",
        "deferred_missions",
        "conflict_edges",
    }
    if _keys(errors, "run.active_wave", wave, wave_keys):
        _optional_string(errors, "run.active_wave.wave_id", wave["wave_id"])
        if wave["status"] not in {"idle", "proposed", "active", "closed", "superseded"}:
            _add(errors, "run.active_wave.status", "has an unsupported value")
        if not _is_int(wave["plan_revision"]) or wave["plan_revision"] < 1:
            _add(errors, "run.active_wave.plan_revision", "must be positive integer")
        _optional_sha(errors, "run.active_wave.plan_digest_sha256", wave["plan_digest_sha256"])
        _optional_sha(errors, "run.active_wave.batch_base_sha", wave["batch_base_sha"])
        for mission_id in _strings(errors, "run.active_wave.selected_missions", wave["selected_missions"]):
            if mission_id not in mission_ids:
                _add(errors, "run.active_wave.selected_missions", f"unknown mission {mission_id!r}")
        if not isinstance(wave["deferred_missions"], list):
            _add(errors, "run.active_wave.deferred_missions", "must be a list")
        else:
            for index, item in enumerate(wave["deferred_missions"]):
                path = f"run.active_wave.deferred_missions[{index}]"
                if _keys(errors, path, item, {"mission_id", "reason_codes", "conflicts_with"}):
                    if item["mission_id"] not in mission_ids:
                        _add(errors, f"{path}.mission_id", "is unknown")
                    _strings(errors, f"{path}.reason_codes", item["reason_codes"], nonempty=True)
                    _strings(errors, f"{path}.conflicts_with", item["conflicts_with"])
        if not isinstance(wave["conflict_edges"], list):
            _add(errors, "run.active_wave.conflict_edges", "must be a list")
        else:
            for index, edge in enumerate(wave["conflict_edges"]):
                path = f"run.active_wave.conflict_edges[{index}]"
                if _keys(errors, path, edge, {"left", "right", "reason_codes"}):
                    if edge["left"] not in mission_ids or edge["right"] not in mission_ids:
                        _add(errors, path, "references an unknown mission")
                    if edge["left"] >= edge["right"]:
                        _add(errors, path, "endpoints must be lexical left < right")
                    _strings(errors, f"{path}.reason_codes", edge["reason_codes"], nonempty=True)

    worker_ids: set[str] = set()
    workers = run["workers"]
    worker_keys = {
        "worker_id",
        "mission_id",
        "lease_id",
        "plan_revision",
        "plan_digest_sha256",
        "batch_base_sha",
        "worker_runtime",
        "workspace_mode",
        "completion_channel",
        "task_thread_id",
        "worktree_path",
        "branch_ref",
        "report_path",
        "phase",
        "worker_head_sha",
    }
    if not isinstance(workers, list):
        _add(errors, "run.workers", "must be a list")
    else:
        for index, worker in enumerate(workers):
            path = f"run.workers[{index}]"
            if not _keys(errors, path, worker, worker_keys, {"nested_subagent_policy"}):
                continue
            for key in ("worker_id", "mission_id", "lease_id", "plan_digest_sha256", "batch_base_sha"):
                if not _nonempty_string(worker[key]):
                    _add(errors, f"{path}.{key}", "must be a non-empty string")
            if worker["worker_id"] in worker_ids:
                _add(errors, f"{path}.worker_id", "must be unique")
            worker_ids.add(worker["worker_id"])
            if worker["mission_id"] not in mission_ids:
                _add(errors, f"{path}.mission_id", "is unknown")
            if not _is_int(worker["plan_revision"]) or worker["plan_revision"] < 1:
                _add(errors, f"{path}.plan_revision", "must be positive integer")
            _optional_sha(errors, f"{path}.plan_digest_sha256", worker["plan_digest_sha256"])
            _optional_sha(errors, f"{path}.batch_base_sha", worker["batch_base_sha"])
            _optional_sha(errors, f"{path}.worker_head_sha", worker["worker_head_sha"])
            if worker["worker_runtime"] not in {"parent", "subagent", "app_task"}:
                _add(errors, f"{path}.worker_runtime", "has an unsupported value")
            if worker["workspace_mode"] not in {"shared_checkout", "parent_managed_worktree", "app_managed_worktree"}:
                _add(errors, f"{path}.workspace_mode", "has an unsupported value")
            if worker["completion_channel"] not in {"agent_result", "thread_poll", "report_file", "user_relay"}:
                _add(errors, f"{path}.completion_channel", "has an unsupported value")
            for key in ("task_thread_id", "worktree_path", "branch_ref", "report_path"):
                _optional_string(errors, f"{path}.{key}", worker[key])
            if worker["phase"] not in WORKER_PHASES:
                _add(errors, f"{path}.phase", "has an unsupported value")
            if worker["completion_channel"] == "report_file" and not _nonempty_string(worker["report_path"]):
                _add(errors, f"{path}.report_path", "is required for report_file")
            nested_policy = worker.get("nested_subagent_policy")
            if (
                worker["worker_runtime"] == "app_task"
                and isinstance(runtime, dict)
                and "nested_subagents" in runtime
                and nested_policy is None
            ):
                _add(
                    errors,
                    f"{path}.nested_subagent_policy",
                    "is required for app_task workers when runtime nested_subagents is recorded",
                )
            if nested_policy is not None and _keys(
                errors,
                f"{path}.nested_subagent_policy",
                nested_policy,
                {
                    "enabled",
                    "max_children",
                    "allowed_roles",
                    "write_policy",
                    "completion_channel",
                },
            ):
                if not isinstance(nested_policy["enabled"], bool):
                    _add(
                        errors,
                        f"{path}.nested_subagent_policy.enabled",
                        "must be boolean",
                    )
                if nested_policy["write_policy"] != "read_only":
                    _add(
                        errors,
                        f"{path}.nested_subagent_policy.write_policy",
                        "must equal read_only",
                    )
                if nested_policy["completion_channel"] != "agent_result":
                    _add(
                        errors,
                        f"{path}.nested_subagent_policy.completion_channel",
                        "must equal agent_result",
                    )
                policy_roles = _strings(
                    errors,
                    f"{path}.nested_subagent_policy.allowed_roles",
                    nested_policy["allowed_roles"],
                    nonempty=bool(nested_policy["enabled"]),
                )
                runtime_nested = (
                    runtime.get("nested_subagents")
                    if isinstance(runtime, dict)
                    else None
                )
                if nested_policy["enabled"]:
                    if worker["worker_runtime"] != "app_task":
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.enabled",
                            "may be true only for app_task workers",
                        )
                    if worker["workspace_mode"] != "app_managed_worktree":
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.enabled",
                            "requires an app_managed_worktree",
                        )
                    if not isinstance(runtime_nested, dict) or runtime_nested.get("available") is not True:
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.enabled",
                            "requires an available runtime nested-subagent capability",
                        )
                    runtime_limit = (
                        runtime_nested.get("max_children_per_worker")
                        if isinstance(runtime_nested, dict)
                        else None
                    )
                    if (
                        not _is_int(nested_policy["max_children"])
                        or not 1 <= nested_policy["max_children"] <= 3
                        or (_is_int(runtime_limit) and nested_policy["max_children"] > runtime_limit)
                    ):
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.max_children",
                            "must be 1..3 and not exceed the runtime limit",
                        )
                    runtime_roles = (
                        set(runtime_nested.get("allowed_roles", []))
                        if isinstance(runtime_nested, dict)
                        else set()
                    )
                    if set(policy_roles) - runtime_roles:
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.allowed_roles",
                            "must be a subset of runtime allowed_roles",
                        )
                    if not authorization_covers(
                        run,
                        "spawn_subagents",
                        worker["mission_id"],
                        f"worker:{worker['worker_id']}",
                    ):
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.enabled",
                            "requires matching spawn_subagents authorization",
                        )
                else:
                    if nested_policy["max_children"] != 0:
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.max_children",
                            "must equal 0 when disabled",
                        )
                    if policy_roles:
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.allowed_roles",
                            "must be empty when disabled",
                        )

    if not isinstance(run["attempt_log"], list):
        _add(errors, "run.attempt_log", "must be a list")
    else:
        attempt_keys = {"attempt_id", "mission_id", "task_id", "lease_id", "kind", "result", "evidence"}
        for index, attempt in enumerate(run["attempt_log"]):
            path = f"run.attempt_log[{index}]"
            if not _keys(errors, path, attempt, attempt_keys):
                continue
            for key in ("attempt_id", "mission_id", "kind", "result"):
                if not _nonempty_string(attempt[key]):
                    _add(errors, f"{path}.{key}", "must be a non-empty string")
            if attempt["mission_id"] not in mission_ids:
                _add(errors, f"{path}.mission_id", "is unknown")
            for key in ("task_id", "lease_id"):
                _optional_string(errors, f"{path}.{key}", attempt[key])
            if attempt["task_id"] is not None and attempt["task_id"] not in task_ids:
                _add(errors, f"{path}.task_id", "is unknown")
            _strings(errors, f"{path}.evidence", attempt["evidence"])

    return sorted(set(errors))

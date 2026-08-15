#!/usr/bin/env python3
"""Shared, stdlib-only manifest infrastructure: loading, digests, scopes, and value helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from harness_schema import (
    MODEL_TOKEN_RE,
    PLAN_HEADING,
    RUN_HEADING,
    RUNTIME_DRIVER_PRIORITY,
    SHA_RE,
    WORKER_HEADING,
)


class ManifestError(ValueError):
    """Raised when a canonical manifest cannot be extracted or decoded."""


def classify_execution_route(
    *,
    direct: bool = False,
    managed_artifacts: bool = False,
    selected_safe_write_missions: int = 0,
) -> str:
    """Classify the execution topology without selecting a transport driver.

    Direct work wins before managed artifacts are considered.  Once a managed
    PLAN/RUN route exists, the route is sequential until at least two safe write
    missions are actually selected.  ``runtime_driver`` remains an independent
    host-transport fact and is deliberately not consulted here.
    """

    if direct or not managed_artifacts:
        return "direct"
    if selected_safe_write_missions >= 2:
        return "parallel_graph"
    return "managed_sequential"


def route_runtime_driver(runtime: dict[str, Any]) -> str:
    """Select one deterministic execution driver from observed capabilities."""

    adapter = runtime.get("runtime_adapter")
    if not isinstance(adapter, dict):
        return {
            "parent": "sequential_parent",
            "subagent": "subagents",
            "app_task": "app_threads",
        }.get(runtime.get("worker_runtime"), "sequential_parent")

    available = adapter.get("available_drivers")
    if not isinstance(available, list):
        return "sequential_parent"
    provider = adapter.get("provider")
    priority = RUNTIME_DRIVER_PRIORITY.get(provider, ()) if isinstance(provider, str) else ()
    for driver in priority:
        if driver in available:
            return driver
    return "sequential_parent"


def resolve_runtime_options(policy: dict[str, Any], provider: str) -> dict[str, Any]:
    """Resolve one provider's PLAN options without inventing external Codex overrides."""

    raw_options = policy.get("provider_options")
    provider_options = raw_options if isinstance(raw_options, dict) else {}
    configured = provider_options.get(provider)
    default_model = "sonnet" if provider == "claude_code" else None
    if isinstance(configured, dict):
        return {
            "model": configured.get("model") or default_model,
            "reasoning_effort": configured.get("reasoning_effort"),
            "option_source": "plan_provider_options",
        }
    return {
        "model": default_model,
        "reasoning_effort": None,
        "option_source": "provider_default",
    }


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


def _normalized_branch(value: Any) -> str | None:
    """Return a branch name with any refs/heads/ prefix removed."""
    if not _nonempty_string(value):
        return None
    return value.removeprefix("refs/heads/")


def _branch_ref(value: Any) -> str | None:
    """Return the full refs/heads/ ref for a branch name, or None."""
    name = _normalized_branch(value)
    return None if name is None else f"refs/heads/{name}"


def is_full_sha(value: Any) -> bool:
    return isinstance(value, str) and SHA_RE.fullmatch(value) is not None


def is_safe_model_token(value: Any) -> bool:
    return isinstance(value, str) and MODEL_TOKEN_RE.fullmatch(value) is not None


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


def mission_dependencies(plan: dict[str, Any]) -> dict[str, list[str]]:
    """Return the canonical mission dependency projection for every PLAN schema."""

    missions = {
        mission["id"]: mission
        for mission in plan.get("missions", [])
        if isinstance(mission, dict) and isinstance(mission.get("id"), str)
    }
    if plan.get("schema_version") not in {4, 5}:
        return {
            mission_id: list(mission.get("depends_on", []))
            for mission_id, mission in missions.items()
        }

    graph = plan.get("graph", {})
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    node_to_mission = {
        node.get("id"): node.get("ref")
        for node in nodes
        if isinstance(node, dict)
        and isinstance(node.get("id"), str)
        and node.get("kind") == "mission"
        and isinstance(node.get("ref"), str)
        and node.get("ref") in missions
    }
    dependencies = {mission_id: [] for mission_id in missions}
    edges = graph.get("edges", []) if isinstance(graph, dict) else []
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("kind") != "dependency":
            continue
        source_id = edge.get("from")
        target_id = edge.get("to")
        source = node_to_mission.get(source_id) if isinstance(source_id, str) else None
        target = node_to_mission.get(target_id) if isinstance(target_id, str) else None
        if source is not None and target is not None:
            dependencies[target].append(source)
    return {
        mission_id: sorted(set(values))
        for mission_id, values in dependencies.items()
    }


def topological_levels(plan: dict[str, Any]) -> dict[str, int]:
    missions = {mission["id"]: mission for mission in plan.get("missions", [])}
    dependency_map = mission_dependencies(plan)
    levels: dict[str, int] = {}

    def visit(mission_id: str, stack: set[str]) -> int:
        if mission_id in levels:
            return levels[mission_id]
        if mission_id in stack:
            raise ManifestError("mission dependency cycle")
        stack.add(mission_id)
        dependencies = dependency_map.get(mission_id, [])
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


def _validate_scope_list(
    errors: list[str], path: str, value: Any, *, nonempty: bool = False
) -> list[str]:
    claims = _strings(errors, path, value, nonempty=nonempty)
    for index, claim in enumerate(claims):
        problem = validate_scope_claim(claim)
        if problem:
            _add(errors, f"{path}[{index}]", problem)
    return claims


def _validate_verifier(
    errors: list[str],
    path: str,
    value: Any,
    *,
    selection_scopes: Iterable[str] | None = None,
    cache_allowed: bool = True,
) -> None:
    required = {"id", "cwd", "argv", "pass_signal"}
    optional = {"selection", "cache"}
    if not _keys(errors, path, value, required, optional):
        return
    for key in ("id", "cwd", "pass_signal"):
        if not _nonempty_string(value[key]):
            _add(errors, f"{path}.{key}", "must be a non-empty string")
    _strings(errors, f"{path}.argv", value["argv"], nonempty=True)

    selection = value.get("selection")
    if selection is not None:
        selection_path = f"{path}.selection"
        if _keys(errors, selection_path, selection, {"mode", "scopes"}):
            mode = selection["mode"]
            if mode not in {"always", "changed_files"}:
                _add(errors, f"{selection_path}.mode", "must be always or changed_files")
            scopes = _validate_scope_list(
                errors,
                f"{selection_path}.scopes",
                selection["scopes"],
                nonempty=mode == "changed_files",
            )
            if mode == "always" and scopes:
                _add(errors, f"{selection_path}.scopes", "must be empty for always mode")
            if mode == "changed_files":
                if selection_scopes is None:
                    _add(errors, selection_path, "changed_files is allowed only for task and worker verifiers")
                else:
                    owner_scopes = list(selection_scopes)
                    for claim in scopes:
                        if not any(scope_contains(owner, claim) for owner in owner_scopes):
                            _add(
                                errors,
                                f"{selection_path}.scopes",
                                f"claim {claim!r} escapes the owning write scope",
                            )

    cache = value.get("cache")
    if cache is not None:
        cache_path = f"{path}.cache"
        if _keys(errors, cache_path, cache, {"mode", "environment_keys"}):
            mode = cache["mode"]
            if mode not in {"disabled", "session_exact"}:
                _add(errors, f"{cache_path}.mode", "must be disabled or session_exact")
            environment_keys = _strings(
                errors,
                f"{cache_path}.environment_keys",
                cache["environment_keys"],
            )
            if any(not key.strip() for key in environment_keys):
                _add(errors, f"{cache_path}.environment_keys", "contains an empty key")
            if mode == "disabled" and environment_keys:
                _add(errors, f"{cache_path}.environment_keys", "must be empty when cache is disabled")
            if mode == "session_exact" and not cache_allowed:
                _add(errors, cache_path, "session_exact is not allowed for this verifier")
            if mode == "session_exact" and value.get("pass_signal") != "exit 0":
                _add(errors, f"{path}.pass_signal", "session_exact requires the literal pass signal exit 0")


def _optional_string(errors: list[str], path: str, value: Any) -> None:
    if value is not None and not _nonempty_string(value):
        _add(errors, path, "must be null or a non-empty string")


def _optional_sha(errors: list[str], path: str, value: Any) -> None:
    if value is not None and not is_full_sha(value):
        _add(errors, path, "must be null or a full lowercase Git SHA")


def _optional_nonnegative_int(errors: list[str], path: str, value: Any) -> None:
    if value is not None and (not _is_int(value) or value < 0):
        _add(errors, path, "must be null or a non-negative integer")

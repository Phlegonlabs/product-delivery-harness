#!/usr/bin/env python3
"""Shared, stdlib-only manifest infrastructure: loading, digests, scopes, and value helpers."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable

from harness_git import GitMetadataError, reject_object_substitution, run_git
from harness_schema import (
    MODEL_TOKEN_RE,
    PLAN_HEADING,
    RUN_HEADING,
    RUNTIME_DRIVERS,
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
    # The parent orders observed, suitable native capabilities; host names do not route.
    for driver in available:
        if isinstance(driver, str) and driver in RUNTIME_DRIVERS:
            return driver
    return "sequential_parent"


def resolve_runtime_options(policy: dict[str, Any], provider: str) -> dict[str, Any]:
    """Resolve one provider's PLAN options without inventing host model defaults."""

    raw_options = policy.get("provider_options")
    provider_options = raw_options if isinstance(raw_options, dict) else {}
    configured = provider_options.get(provider)
    if isinstance(configured, dict):
        return {
            "model": configured.get("model"),
            "reasoning_effort": configured.get("reasoning_effort"),
            "option_source": "plan_provider_options",
        }
    return {
        "model": None,
        "reasoning_effort": None,
        "option_source": "provider_default",
    }


def extract_json_manifest_text(
    text: str,
    heading: str,
    wrapper: str,
    *,
    source: str | Path = "<memory>",
) -> dict[str, Any]:
    """Decode one exact-heading manifest from an already-read text snapshot."""

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


def extract_json_manifest(path: str | Path, heading: str, wrapper: str) -> dict[str, Any]:
    """Load the unique exact-heading JSON fence and return its wrapped object."""

    source = Path(path)
    return extract_json_manifest_text(
        source.read_text(encoding="utf-8"),
        heading,
        wrapper,
        source=source,
    )


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


def validate_changed_path(path: Any) -> str | None:
    """Validate one literal Git path without interpreting scope globs."""

    if not isinstance(path, str) or not path:
        return "must be a non-empty string"
    if path.startswith("/") or "\\" in path:
        return "must be a repository-relative POSIX path"
    if path != path.strip() or "//" in path:
        return "must use canonical path spelling"
    if path.endswith("/"):
        return "must name a file, not a directory"
    if len(path) >= 2 and path[1] == ":":
        return "must not contain a Windows drive"
    if path.startswith("!") or any(character in path for character in "*?{}"):
        return "contains unsupported glob syntax"
    if any(ord(character) < 32 for character in path):
        return "must not contain control characters"
    segments = path.split("/")
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
    if plan.get("schema_version") not in {4, 5, 6}:
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


SANDBOX_POLICY_KEYS = {
    "runtime",
    "image",
    "network",
    "read_only_rootfs",
    "no_new_privileges",
    "cap_drop",
    "tmpfs",
    "memory",
    "cpus",
    "pids_limit",
    "user",
    "pull",
}


def normalize_sandbox_policy(value: Any) -> dict[str, Any]:
    """Validate and normalize the machine-enforced container policy."""

    if not isinstance(value, dict) or set(value) != SANDBOX_POLICY_KEYS:
        raise ValueError("sandbox policy must contain the exact required keys")
    runtime = value["runtime"]
    image = value["image"]
    if runtime not in {"docker", "podman"}:
        raise ValueError("sandbox runtime must be docker or podman")
    if not isinstance(image, str) or re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}", image
    ) is None:
        raise ValueError("sandbox image must be a safe OCI reference pinned by @sha256 digest")
    if image.rsplit("@", 1)[-1] == "sha256:" + "0" * 64:
        raise ValueError(
            "sandbox image digest must be an observed non-zero RepoDigest, not a template placeholder"
        )
    if value["network"] != "none":
        raise ValueError("sandbox network must be none")
    if value["read_only_rootfs"] is not True or value["no_new_privileges"] is not True:
        raise ValueError("sandbox rootfs and no-new-privileges flags must be true")
    if not isinstance(value["cap_drop"], list) or value["cap_drop"] != ["ALL"]:
        raise ValueError("sandbox cap_drop must equal ['ALL']")
    if not isinstance(value["tmpfs"], list) or not value["tmpfs"]:
        raise ValueError("sandbox tmpfs must be a non-empty list")
    for item in value["tmpfs"]:
        if not isinstance(item, str) or re.fullmatch(
            r"/[A-Za-z0-9._/-]+(?::[A-Za-z0-9_=,.-]+)?", item
        ) is None or ".." in item.split(":", 1)[0].split("/"):
            raise ValueError("sandbox tmpfs entries must be safe absolute container paths")
    if not isinstance(value["memory"], str) or re.fullmatch(
        r"[1-9][0-9]*(?:[bkmg])?", value["memory"].lower()
    ) is None:
        raise ValueError("sandbox memory must use a positive numeric grammar")
    if not isinstance(value["cpus"], str) or re.fullmatch(
        r"[1-9][0-9]*(?:\.[0-9]+)?", value["cpus"]
    ) is None:
        raise ValueError("sandbox cpus must use a positive numeric grammar")
    if not isinstance(value["pids_limit"], str) or re.fullmatch(
        r"[1-9][0-9]{0,5}", value["pids_limit"]
    ) is None:
        raise ValueError("sandbox pids_limit must be a positive bounded integer")
    if not isinstance(value["user"], str) or re.fullmatch(
        r"[1-9][0-9]*:[1-9][0-9]*", value["user"]
    ) is None:
        raise ValueError("sandbox user must be a non-root uid:gid")
    if value["pull"] != "never":
        raise ValueError("sandbox pull must be never")
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False))


def _validate_verifier(
    errors: list[str],
    path: str,
    value: Any,
    *,
    selection_scopes: Iterable[str] | None = None,
    cache_allowed: bool = True,
    execution_required: bool = True,
) -> None:
    required = {"id", "cwd", "argv", "pass_signal"}
    optional = {"selection", "cache", "read_only"}
    if execution_required:
        required.add("execution")
    else:
        optional.add("execution")
    if not _keys(errors, path, value, required, optional):
        return
    for key in ("id", "cwd", "pass_signal"):
        if not _nonempty_string(value[key]):
            _add(errors, f"{path}.{key}", "must be a non-empty string")
    _strings(errors, f"{path}.argv", value["argv"], nonempty=True)
    if "read_only" in value and not isinstance(value["read_only"], bool):
        _add(errors, f"{path}.read_only", "must be boolean")

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
        if _keys(
            errors,
            cache_path,
            cache,
            {"mode", "environment_keys"},
            {"deterministic_local"},
        ):
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
            deterministic_local = cache.get("deterministic_local", False)
            if not isinstance(deterministic_local, bool):
                _add(errors, f"{cache_path}.deterministic_local", "must be boolean")
            # Integration, batch, and final gates ban reuse by default because a
            # gate at those layers usually touches a live environment. The
            # property that actually matters is the command's nature, not its
            # layer, so a verifier may attest that it is a pure local
            # deterministic command and become reusable. Never set this for a
            # browser capture, migration, mutable-environment smoke, network or
            # shared-database check, or a time/random-dependent command.
            if mode == "session_exact" and not cache_allowed and not deterministic_local:
                _add(
                    errors,
                    cache_path,
                    "session_exact at this layer requires cache.deterministic_local: true",
                )
            if mode == "session_exact" and value.get("pass_signal") != "exit 0":
                _add(errors, f"{path}.pass_signal", "session_exact requires the literal pass signal exit 0")

    execution = value.get("execution")
    if execution is None and not execution_required:
        return
    execution_path = f"{path}.execution"
    if _keys(
        errors,
        execution_path,
        execution,
        {"parallel_safe", "resources", "isolation"},
        {"sandbox"},
    ):
            if not isinstance(execution["parallel_safe"], bool):
                _add(errors, f"{execution_path}.parallel_safe", "must be boolean")
            isolation = execution["isolation"]
            if isolation not in {"container", "host"}:
                _add(
                    errors,
                    f"{execution_path}.isolation",
                    "must equal container or host",
                )
                return
            if isolation == "host":
                if execution["parallel_safe"] is not False:
                    _add(
                        errors,
                        f"{execution_path}.parallel_safe",
                        "must be false so host commands share one checkout serially",
                    )
                if "sandbox" in execution:
                    _add(errors, execution_path, "host execution must omit sandbox")
                if isinstance(cache, dict) and (cache.get("mode") != "disabled" or cache.get("deterministic_local", False)):
                    _add(errors, cache_path, "host execution requires disabled cache")
            else:
                sandbox_path = f"{execution_path}.sandbox"
                if "sandbox" not in execution:
                    _add(errors, sandbox_path, "is required for container isolation")
                    return
                sandbox = execution["sandbox"]
                try:
                    normalize_sandbox_policy(sandbox)
                except ValueError as exc:
                    _add(errors, sandbox_path, str(exc))
                if _keys(
                    errors,
                    sandbox_path,
                    sandbox,
                    {
                        "runtime",
                        "image",
                        "network",
                        "read_only_rootfs",
                        "no_new_privileges",
                        "cap_drop",
                        "tmpfs",
                        "memory",
                        "cpus",
                        "pids_limit",
                        "user",
                        "pull",
                    },
                ):
                        if sandbox["runtime"] not in {"docker", "podman"}:
                            _add(errors, f"{sandbox_path}.runtime", "must be docker or podman")
                        if not isinstance(sandbox["image"], str) or re.fullmatch(
                            r"[A-Za-z0-9][A-Za-z0-9._:/-]*@sha256:[0-9a-f]{64}", sandbox["image"]
                        ) is None:
                            _add(errors, f"{sandbox_path}.image", "must be pinned by @sha256 digest")
                        if sandbox["network"] != "none":
                            _add(errors, f"{sandbox_path}.network", "must equal none")
                        for flag in ("read_only_rootfs", "no_new_privileges"):
                            if sandbox[flag] is not True:
                                _add(errors, f"{sandbox_path}.{flag}", "must be true")
                        if not isinstance(sandbox["cap_drop"], list) or "ALL" not in sandbox["cap_drop"]:
                            _add(errors, f"{sandbox_path}.cap_drop", "must include ALL")
                        if not isinstance(sandbox["tmpfs"], list) or not sandbox["tmpfs"] or any(
                            not isinstance(item, str)
                            or re.fullmatch(r"/[A-Za-z0-9._/-]+(?::[A-Za-z0-9_=,.-]+)?", item) is None
                            or ".." in item.split(":", 1)[0].split("/")
                            for item in sandbox["tmpfs"]
                        ):
                            _add(errors, f"{sandbox_path}.tmpfs", "must be a non-empty list")
                        if not isinstance(sandbox["memory"], str) or re.fullmatch(r"[1-9][0-9]*(?:[bkmg])?", sandbox["memory"].lower()) is None:
                            _add(errors, f"{sandbox_path}.memory", "must use a bounded numeric memory grammar")
                        if not isinstance(sandbox["cpus"], str) or re.fullmatch(r"[1-9][0-9]*(?:\.[0-9]+)?", sandbox["cpus"]) is None:
                            _add(errors, f"{sandbox_path}.cpus", "must use a numeric CPU grammar")
                        if not isinstance(sandbox["pids_limit"], str) or re.fullmatch(r"[1-9][0-9]{0,5}", sandbox["pids_limit"]) is None:
                            _add(errors, f"{sandbox_path}.pids_limit", "must use a bounded PID grammar")
                        if not isinstance(sandbox["user"], str) or re.fullmatch(r"[1-9][0-9]*:[1-9][0-9]*", sandbox["user"]) is None:
                            _add(errors, f"{sandbox_path}.user", "must be a non-root uid:gid")
                        if sandbox["pull"] != "never":
                            _add(errors, f"{sandbox_path}.pull", "must equal never")
            resources = execution["resources"]
            if not isinstance(resources, list):
                _add(errors, f"{execution_path}.resources", "must be a list")
            else:
                resource_keys: set[str] = set()
                for index, resource in enumerate(resources):
                    resource_path = f"{execution_path}.resources[{index}]"
                    if not _keys(errors, resource_path, resource, {"key", "access"}):
                        continue
                    key = resource["key"]
                    if not _nonempty_string(key):
                        _add(errors, f"{resource_path}.key", "must be a non-empty string")
                    elif key in resource_keys:
                        _add(errors, f"{resource_path}.key", "must be unique")
                    else:
                        resource_keys.add(key)
                    if resource["access"] not in {"shared_read", "exclusive"}:
                        _add(
                            errors,
                            f"{resource_path}.access",
                            "must be shared_read or exclusive",
                        )


def _optional_string(errors: list[str], path: str, value: Any) -> None:
    if value is not None and not _nonempty_string(value):
        _add(errors, path, "must be null or a non-empty string")


def read_git_blob(
    root: Path, revision: str, relative_path: str, unavailable_message: str
) -> tuple[bytes | None, str | None]:
    """Read one blob from a commit/ref without consulting the working tree."""

    try:
        reject_object_substitution(root)
        result = run_git(
            root,
            "show",
            "--no-ext-diff",
            "--format=",
            f"{revision}:{relative_path}",
            text=False,
            timeout=10,
        )
    except (GitMetadataError, OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    if result.returncode != 0:
        reason = result.stderr.decode("utf-8", errors="replace").lower()
        if "not a git repository" in reason:
            return None, "--repo-root is not a Git checkout"
        return None, unavailable_message
    return result.stdout, None


def changed_files_digest(files: list[str]) -> str:
    """One canonical digest over the sorted changed-file list.

    Both the manifest validator and the worker-result validator key evidence
    on this value; a single definition keeps them from drifting apart.
    """

    return hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def sandbox_execution_binding_errors(
    policy: Any,
    preflight: Any,
    attestation: Any,
) -> list[str]:
    """Validate one container execution against its observed runtime identity."""

    errors: list[str] = []
    preflight_keys = {"runtime", "image", "repo_digest", "runtime_probe"}
    probe_keys = {"executable", "executable_sha256", "version_output_sha256"}
    attestation_keys = {
        "runtime",
        "runtime_probe",
        "image",
        "image_probe",
        "policy",
        "mount",
        "network",
    }
    if not isinstance(policy, dict):
        return ["declared container sandbox policy is missing"]
    if not isinstance(preflight, dict) or set(preflight) != preflight_keys:
        return ["sandbox preflight must retain the exact observed entry"]
    if preflight.get("runtime") != policy.get("runtime"):
        errors.append("sandbox preflight runtime differs from the declared policy")
    if preflight.get("image") != policy.get("image"):
        errors.append("sandbox preflight image differs from the declared policy")
    image = preflight.get("image")
    repo_digest = preflight.get("repo_digest")
    if (
        not isinstance(image, str)
        or not isinstance(repo_digest, str)
        or re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", repo_digest) is None
        or not repo_digest.endswith("@" + image.rsplit("@", 1)[-1])
    ):
        errors.append("sandbox preflight RepoDigest does not attest the pinned image")
    runtime_probe = preflight.get("runtime_probe")
    if not isinstance(runtime_probe, dict) or not probe_keys.issubset(runtime_probe) or set(runtime_probe) - probe_keys - {"trust"}:
        errors.append("sandbox preflight runtime identity is malformed")
    else:
        executable = runtime_probe.get("executable")
        if not isinstance(executable, str) or not executable or not Path(executable).is_absolute():
            errors.append("sandbox preflight executable is not an absolute path")
        for key in ("executable_sha256", "version_output_sha256"):
            if re.fullmatch(r"[0-9a-f]{64}", str(runtime_probe.get(key))) is None:
                errors.append(f"sandbox preflight {key} is not a SHA-256 digest")
        trust = runtime_probe.get("trust")
        if not isinstance(trust, dict) or set(trust) != {"path", "runtime", "ownership", "uid", "mode", "reparse"}:
            errors.append("sandbox preflight runtime trust proof is missing")
        elif trust.get("path") != runtime_probe.get("executable") or trust.get("reparse") is not False:
            errors.append("sandbox preflight runtime trust proof does not bind the executable")
    if not isinstance(attestation, dict) or set(attestation) != attestation_keys:
        errors.append("sandbox attestation must retain the complete execution identity")
        return errors
    if attestation.get("policy") != policy:
        errors.append("sandbox attestation policy differs from the declaration")
    if attestation.get("runtime") != preflight.get("runtime"):
        errors.append("sandbox attestation runtime differs from preflight")
    if attestation.get("image") != preflight.get("image"):
        errors.append("sandbox attestation image differs from preflight")
    if attestation.get("runtime_probe") != runtime_probe:
        errors.append("sandbox attestation runtime identity differs from preflight")
    if attestation.get("image_probe") != repo_digest:
        errors.append("sandbox attestation RepoDigest differs from preflight")
    if attestation.get("mount") != {
        "source": "git_archive",
        "destination": "/workspace",
        "read_only": True,
    }:
        errors.append("sandbox attestation does not prove the read-only Git archive mount")
    if attestation.get("network") != "none":
        errors.append("sandbox attestation does not prove network isolation")
    return errors


HOST_FINGERPRINT_KEYS = {"system", "machine", "release", "node_sha256"}
HOST_RUNTIME_VERSION_KEYS = {"system", "release", "machine"}


def host_execution_binding_errors(
    preflight: Any,
    attestation: Any,
    key_document: Any = None,
    checkout_root: Any = None,
) -> list[str]:
    """Validate the static host-identity join retained with one execution."""

    errors: list[str] = []
    preflight_keys = {
        "isolation",
        "argv0",
        "executable",
        "executable_sha256",
        "runtime_version",
        "host",
    }
    attestation_keys = {
        "isolation",
        "cwd",
        "host",
        "runtime_version",
        "executable",
    }
    if not isinstance(preflight, dict) or set(preflight) != preflight_keys:
        return ["host preflight must retain the exact observed identity"]
    if preflight.get("isolation") != "host":
        errors.append("host preflight isolation differs from the declaration")
    if not isinstance(preflight.get("argv0"), str) or not preflight["argv0"]:
        errors.append("host preflight argv0 must be a non-empty string")
    if not isinstance(preflight.get("executable"), str) or not Path(preflight["executable"]).is_absolute():
        errors.append("host preflight executable must be a non-empty absolute path")
    if re.fullmatch(r"[0-9a-f]{64}", str(preflight.get("executable_sha256", ""))) is None:
        errors.append("host preflight executable_sha256 must be a SHA-256 digest")
    version = preflight.get("runtime_version")
    if not isinstance(version, dict) or set(version) != HOST_RUNTIME_VERSION_KEYS:
        errors.append("host preflight runtime_version must retain the host OS identity")
    elif any(not isinstance(version.get(key), str) for key in HOST_RUNTIME_VERSION_KEYS):
        errors.append("host preflight runtime_version must contain string OS fields")
    host = preflight.get("host")
    if not isinstance(host, dict) or set(host) != HOST_FINGERPRINT_KEYS:
        errors.append("host preflight must retain the non-sensitive host fingerprint")
    elif (any(not isinstance(host[key], str) for key in HOST_FINGERPRINT_KEYS)
          or re.fullmatch(r"[0-9a-f]{64}", host["node_sha256"]) is None):
        errors.append("host preflight fingerprint contains invalid fields")
    if not isinstance(attestation, dict) or set(attestation) != attestation_keys:
        errors.append("host execution must retain the complete host attestation")
        return errors
    if attestation.get("isolation") != "host":
        errors.append("host attestation isolation differs from the declaration")
    if not isinstance(attestation.get("cwd"), str) or not Path(attestation["cwd"]).is_absolute():
        errors.append("host attestation must retain the execution cwd")
    if isinstance(key_document, dict):
        argv = key_document.get("argv")
        if not isinstance(argv, list) or not argv or preflight.get("argv0") != argv[0]:
            errors.append("host preflight argv0 differs from the declared command")
        if isinstance(checkout_root, str) and isinstance(key_document.get("cwd"), str):
            expected_cwd = str((Path(checkout_root) / key_document["cwd"]).resolve())
            if attestation.get("cwd") != expected_cwd:
                errors.append("host attestation cwd differs from the declared checkout cwd")
    if attestation.get("host") != preflight.get("host"):
        errors.append("host attestation fingerprint differs from preflight")
    if attestation.get("runtime_version") != preflight.get("runtime_version"):
        errors.append("host attestation runtime version differs from preflight")
    executable = attestation.get("executable")
    if not isinstance(executable, dict) or set(executable) != {
        "path",
        "sha256",
    }:
        errors.append("host attestation must retain the executed executable identity")
    elif (
        executable.get("path") != preflight.get("executable")
        or executable.get("sha256") != preflight.get("executable_sha256")
    ):
        errors.append("host attestation executable differs from preflight")
    return errors


def _optional_sha(errors: list[str], path: str, value: Any) -> None:
    if value is not None and not is_full_sha(value):
        _add(errors, path, "must be null or a full lowercase Git SHA")

#!/usr/bin/env python3
"""Orchestrates PLAN/RUN validation (validate_plan, validate_run) plus landing,
cleanup, and gate-result checks, and re-exports the public API that
scripts/tests import from this module by name."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from harness_schema import (
    AUTHORIZATION_KEYS,
    AUTHORIZATION_KEYS_V2,
    AUTHORIZATION_KEYS_V8,
    AUTHORIZATION_KEYS_V10,
    CLEANUP_BRANCH_STATUSES,
    CLEANUP_STATUSES,
    CLEANUP_WORKTREE_STATUSES,
    DEPLOYMENT_PROVIDERS,
    EXPIRY_BOUNDARIES,
    FUTURE_PR_TARGET_RE,
    GATE_VALUES,
    HEAD_BOUND_AUTHORIZATION_ACTIONS,
    ID_RE,
    MISSION_PHASES,
    NESTED_SUBAGENT_ROLES,
    PERMISSION_APPROVAL_POLICIES,
    PERMISSION_FILESYSTEM_SCOPES,
    PERMISSION_INHERITANCE,
    PERMISSION_LOCAL_BINDINGS,
    PERMISSION_NETWORK_SCOPES,
    PERMISSION_SELECTED_MODES,
    PERMISSION_STATUSES,
    PLAN_HEADING,
    RUN_HEADING,
    RUNTIME_DETECTION_SOURCES,
    RUNTIME_DRIVER_PRIORITY,
    RUNTIME_DRIVERS,
    RUNTIME_PROVIDERS,
    RUNTIME_REASONING_EFFORTS,
    RUNTIME_REVIEW_TYPES,
    SHA256_RE,
    SHA_RE,
    SUPPORTED_RUN_SCHEMA_VERSIONS,
    TASK_ID_RE,
    TASK_PHASES,
    WORKER_PHASES,
    WORKFLOW_RUN_DRIVERS_BY_PROVIDER,
    WORKFLOW_RUN_STATUSES,
    WORKFLOW_TOOL_PROFILES,
)


from harness_core import (
    ManifestError,
    _add,
    _is_int,
    _keys,
    _nonempty_string,
    _optional_nonnegative_int,
    _optional_sha,
    _optional_string,
    _strings,
    _validate_scope_list,
    _validate_verifier,
    canonical_json,
    is_full_sha,
    is_safe_model_token,
    load_plan,
    load_run,
    load_worker_result,
    mission_conflicts,
    mission_dependencies,
    parent_owned_path,
    path_in_scopes,
    plan_digest,
    resolve_runtime_options,
    route_runtime_driver,
    scope_contains,
    scope_overlap,
    topological_levels,
    validate_scope_claim,
)
from harness_authorization import (
    _landing_future_pr_target,
    _validate_authorization_scope,
    authorization_covers,
    execution_covers,
)
from harness_graph import (
    _cycle_nodes,
    _validate_graph,
    _validate_graph_state,
)
from harness_release import (
    _validate_deployments,
    _validate_release,
    _validate_targets,
)
from harness_ui_evidence import (
    _validate_ui_evidence,
    validate_integration_head_against_git,
    validate_ui_evidence_files,
    validate_ui_surface_recipe_coverage,
)


def _validated_sha_history(
    errors: list[str], path: str, value: Any
) -> set[str]:
    items = _strings(errors, path, value)
    valid: set[str] = set()
    for index, item in enumerate(items):
        _optional_sha(errors, f"{path}[{index}]", item)
        if is_full_sha(item):
            valid.add(item)
    return valid


def _validate_global_verifier_ids(errors: list[str], plan: dict[str, Any]) -> None:
    if plan.get("schema_version") != 5:
        return
    seen: dict[str, str] = {}

    def register(path: str, verifier: Any) -> None:
        if not isinstance(verifier, dict) or not _nonempty_string(verifier.get("id")):
            return
        verifier_id = verifier["id"]
        first_path = seen.get(verifier_id)
        if first_path is None:
            seen[verifier_id] = path
        else:
            _add(
                errors,
                f"{path}.id",
                f"must be globally unique; {verifier_id!r} is already declared at {first_path}",
            )

    for group in ("batch_verifiers", "final_gates"):
        for index, verifier in enumerate(plan.get(group, [])):
            register(f"plan.{group}[{index}]", verifier)
    for mission_index, mission in enumerate(plan.get("missions", [])):
        if not isinstance(mission, dict):
            continue
        mission_path = f"plan.missions[{mission_index}]"
        for group in ("worker_verifiers", "integration_verifiers"):
            for index, verifier in enumerate(mission.get(group, [])):
                register(f"{mission_path}.{group}[{index}]", verifier)
        for task_index, task in enumerate(mission.get("tasks", [])):
            if not isinstance(task, dict):
                continue
            for index, verifier in enumerate(task.get("verifiers", [])):
                register(
                    f"{mission_path}.tasks[{task_index}].verifiers[{index}]",
                    verifier,
                )
    release = plan.get("release")
    if isinstance(release, dict):
        for target_index, target in enumerate(release.get("targets", [])):
            if not isinstance(target, dict):
                continue
            target_path = f"plan.release.targets[{target_index}]"
            commands = target.get("commands")
            if isinstance(commands, dict):
                for command_name, verifier in commands.items():
                    register(f"{target_path}.commands.{command_name}", verifier)
            for index, verifier in enumerate(target.get("smoke_verifiers", [])):
                register(f"{target_path}.smoke_verifiers[{index}]", verifier)


def _is_product_staging_location(value: Any) -> bool:
    if not isinstance(value, str) or "://" in value:
        return False
    normalized = value.replace("\\", "/").removeprefix("./").strip("/").lower()
    parts = normalized.split("/")
    for staging_name in (".prd-staging", ".design-staging"):
        for index in range(len(parts) - 2):
            if parts[index : index + 3] == ["docs", "product", staging_name]:
                return True
    return False


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
    schema_version = plan.get("schema_version") if isinstance(plan, dict) else None
    if schema_version in {4, 5}:
        top_keys.update({"graph", "required_reviews"})
    optional_keys = {"release"} if schema_version in {3, 4, 5} else set()
    if not _keys(errors, "plan", plan, top_keys, optional_keys):
        return sorted(errors)
    if plan["schema_version"] not in {2, 3, 4, 5}:
        _add(errors, "plan.schema_version", "must equal 2, 3, 4, or 5")
    if not _nonempty_string(plan["plan_id"]):
        _add(errors, "plan.plan_id", "must be a non-empty string")
    if not _is_int(plan["revision"]) or plan["revision"] < 1:
        _add(errors, "plan.revision", "must be a positive integer")
    if not _nonempty_string(plan["objective"]):
        _add(errors, "plan.objective", "must be a non-empty string")
    if not _is_int(plan["max_parallel_workers"]) or plan["max_parallel_workers"] < 1:
        _add(errors, "plan.max_parallel_workers", "must be a positive integer")

    required_reviews: list[str] = []
    if schema_version in {4, 5}:
        required_reviews = _strings(
            errors,
            "plan.required_reviews",
            plan["required_reviews"],
        )
        if len(required_reviews) != len(set(required_reviews)):
            _add(errors, "plan.required_reviews", "must not contain duplicates")
        unknown_reviews = sorted(set(required_reviews) - RUNTIME_REVIEW_TYPES)
        if unknown_reviews:
            _add(
                errors,
                "plan.required_reviews",
                f"unsupported review types: {', '.join(unknown_reviews)}",
            )

    sources: dict[str, dict[str, Any]] = {}
    if not isinstance(plan["sources"], list) or not plan["sources"]:
        _add(errors, "plan.sources", "must be a non-empty list")
    else:
        source_keys = {"id", "kind", "location", "owner", "status", "notes"}
        if schema_version in {4, 5}:
            source_keys.update({"content_sha256", "source_revision"})
        if schema_version == 5:
            source_keys.add("staged_revision")
        for index, source in enumerate(plan["sources"]):
            path = f"plan.sources[{index}]"
            if not _keys(errors, path, source, source_keys):
                continue
            for key in {"id", "kind", "location", "owner", "status", "notes"}:
                if not _nonempty_string(source[key]):
                    _add(errors, f"{path}.{key}", "must be a non-empty string")
            if schema_version == 5 and source["status"] not in {
                "frozen",
                "delta_accepted",
                "revision staged",
            }:
                _add(
                    errors,
                    f"{path}.status",
                    "must be frozen, delta_accepted, or revision staged",
                )
            if schema_version == 5 and _is_product_staging_location(source["location"]):
                _add(
                    errors,
                    f"{path}.location",
                    "published PLAN sources cannot use product staging paths",
                )
            if schema_version in {4, 5}:
                content_sha = source["content_sha256"]
                source_revision = source["source_revision"]
                if content_sha is not None and (
                    not isinstance(content_sha, str) or SHA256_RE.fullmatch(content_sha) is None
                ):
                    _add(errors, f"{path}.content_sha256", "must be null or a lowercase SHA-256 digest")
                if source_revision is not None and not _nonempty_string(source_revision):
                    _add(errors, f"{path}.source_revision", "must be null or a non-empty immutable revision")
                if content_sha is None and source_revision is None:
                    _add(
                        errors,
                        path,
                        "schema v4+ sources require content_sha256 or source_revision",
                    )
            if schema_version == 5:
                staged = source["staged_revision"]
                if staged is not None and _keys(
                    errors,
                    f"{path}.staged_revision",
                    staged,
                    {"content_sha256", "source_revision", "notes"},
                ):
                    staged_sha = staged["content_sha256"]
                    staged_revision = staged["source_revision"]
                    if staged_sha is not None and (
                        not isinstance(staged_sha, str)
                        or SHA256_RE.fullmatch(staged_sha) is None
                    ):
                        _add(
                            errors,
                            f"{path}.staged_revision.content_sha256",
                            "must be null or a lowercase SHA-256 digest",
                        )
                    if staged_revision is not None and not _nonempty_string(staged_revision):
                        _add(
                            errors,
                            f"{path}.staged_revision.source_revision",
                            "must be null or a non-empty immutable revision",
                        )
                    if staged_sha is None and staged_revision is None:
                        _add(
                            errors,
                            f"{path}.staged_revision",
                            "requires content_sha256 or source_revision",
                        )
                    if not _nonempty_string(staged["notes"]):
                        _add(errors, f"{path}.staged_revision.notes", "must be a non-empty string")
                if source["status"] == "revision staged" and staged is None:
                    _add(errors, path, "revision staged source requires staged_revision")
                if source["status"] != "revision staged" and staged is not None:
                    _add(errors, path, "staged_revision requires source status 'revision staged'")
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

    declared_verifier_ids: set[str] = set()
    for group in ("batch_verifiers", "final_gates"):
        if not isinstance(plan[group], list) or not plan[group]:
            _add(errors, f"plan.{group}", "must be a non-empty list")
        else:
            ids: set[str] = set()
            for index, verifier in enumerate(plan[group]):
                _validate_verifier(
                    errors,
                    f"plan.{group}[{index}]",
                    verifier,
                    cache_allowed=False,
                )
                if isinstance(verifier, dict) and isinstance(verifier.get("id"), str):
                    if verifier["id"] in ids:
                        _add(errors, f"plan.{group}[{index}].id", "must be unique")
                    ids.add(verifier["id"])
                    declared_verifier_ids.add(verifier["id"])

    if plan["schema_version"] in {3, 4, 5} and "release" in plan:
        _validate_release(
            errors,
            plan["release"],
            schema_version=plan["schema_version"],
        )

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
        "trace_ids",
        "write_scope",
        "deny_scope",
        "resource_inventory_complete",
        "serialized_resources",
        "runtime_resources",
        "worktree_eligible",
        "required_skills",
        "stop_conditions",
        "worker_verifiers",
        "integration_verifiers",
        "tasks",
    }
    if plan["schema_version"] not in {4, 5}:
        mission_keys.add("depends_on")
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
        if plan["schema_version"] not in {4, 5}:
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
        _strings(errors, f"{mission_path}.required_skills", mission["required_skills"])
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
                        selection_scopes=(
                            mission_write if verifier_group == "worker_verifiers" else None
                        ),
                        cache_allowed=verifier_group != "integration_verifiers",
                    )
                    if isinstance(verifier, dict) and isinstance(verifier.get("id"), str):
                        if verifier["id"] in ids:
                            _add(errors, f"{mission_path}.{verifier_group}[{verifier_index}].id", "must be unique")
                        ids.add(verifier["id"])
                        declared_verifier_ids.add(verifier["id"])
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

    mission_edges = mission_dependencies(plan)
    for mission_id, mission in missions.items():
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
    verified_trace_coverage: set[str] = set()
    for task_id, (mission_id, task, path) in task_records.items():
        for key in ("alias", "objective"):
            if not _nonempty_string(task[key]):
                _add(errors, f"{path}.{key}", "must be a non-empty string")
        acceptance_trace_ids: set[str] = set()
        if plan["schema_version"] == 5:
            acceptance = task["acceptance_matrix"]
            if not isinstance(acceptance, list):
                _add(errors, f"{path}.acceptance_matrix", "must be a list")
            else:
                seen_test_ids: set[str] = set()
                for acceptance_index, row in enumerate(acceptance):
                    row_path = f"{path}.acceptance_matrix[{acceptance_index}]"
                    if not _keys(
                        errors,
                        row_path,
                        row,
                        {"test_id", "trace_ids", "criterion"},
                    ):
                        continue
                    test_id = row["test_id"]
                    if not _nonempty_string(test_id) or not test_id.startswith("TEST-"):
                        _add(errors, f"{row_path}.test_id", "must be a stable TEST-* ID")
                    elif test_id in seen_test_ids:
                        _add(errors, f"{row_path}.test_id", "must be unique within the task")
                    else:
                        seen_test_ids.add(test_id)
                    row_traces = _strings(
                        errors,
                        f"{row_path}.trace_ids",
                        row["trace_ids"],
                        nonempty=True,
                    )
                    acceptance_trace_ids.update(row_traces)
                    if not _nonempty_string(row["criterion"]):
                        _add(errors, f"{row_path}.criterion", "must be a non-empty string")
        else:
            _strings(errors, f"{path}.acceptance_matrix", task["acceptance_matrix"])
        trace_ids = _strings(errors, f"{path}.trace_ids", task["trace_ids"], nonempty=True)
        for trace_id in trace_ids:
            if trace_id not in traces:
                _add(errors, f"{path}.trace_ids", f"unknown trace {trace_id!r}")
            elif traces[trace_id]["disposition"] != "planned":
                _add(errors, f"{path}.trace_ids", f"trace {trace_id!r} is not planned")
            else:
                planned_trace_coverage.add(trace_id)
                if plan["schema_version"] == 5:
                    if trace_id in acceptance_trace_ids:
                        verified_trace_coverage.add(trace_id)
                elif (
                    isinstance(task["acceptance_matrix"], list)
                    and task["acceptance_matrix"]
                ):
                    verified_trace_coverage.add(trace_id)
            mission_trace_set = set(missions.get(mission_id, {}).get("trace_ids", []))
            if trace_id not in mission_trace_set:
                _add(errors, f"{path}.trace_ids", f"trace {trace_id!r} is not declared by its mission")
        if plan["schema_version"] == 5:
            unknown_acceptance_traces = sorted(acceptance_trace_ids - set(trace_ids))
            if unknown_acceptance_traces:
                _add(
                    errors,
                    f"{path}.acceptance_matrix",
                    "row trace_ids must be declared by the task: "
                    + ", ".join(unknown_acceptance_traces),
                )
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
                _validate_verifier(
                    errors,
                    f"{path}.verifiers[{verifier_index}]",
                    verifier,
                    selection_scopes=task_scopes,
                )
                if isinstance(verifier, dict) and isinstance(verifier.get("id"), str):
                    if verifier["id"] in verifier_ids:
                        _add(errors, f"{path}.verifiers[{verifier_index}].id", "must be unique")
                    verifier_ids.add(verifier["id"])
                    declared_verifier_ids.add(verifier["id"])

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
        if trace.get("disposition") != "planned":
            continue
        if trace_id not in planned_trace_coverage:
            _add(errors, f"trace {trace_id}", "planned trace has no task coverage")
        elif trace_id not in verified_trace_coverage:
            _add(
                errors,
                f"trace {trace_id}",
                "planned trace has no verification row: every task carrying it has "
                "an empty acceptance_matrix",
            )

    if plan["schema_version"] in {4, 5}:
        _validate_graph(
            errors,
            plan["graph"],
            missions,
            declared_verifier_ids,
            require_bounded_review_repair=plan["schema_version"] == 5,
        )
        declared_reviews = {
            node.get("review", {}).get("type")
            for node in plan["graph"].get("nodes", [])
            if isinstance(node, dict)
            and node.get("kind") == "verifier"
            and node.get("executor") == "runtime_worker"
            and isinstance(node.get("review"), dict)
        }
        missing_reviews = sorted(set(required_reviews) - declared_reviews)
        if missing_reviews:
            _add(
                errors,
                "plan.required_reviews",
                "missing runtime review nodes: " + ", ".join(missing_reviews),
            )

    _validate_global_verifier_ids(errors, plan)
    return sorted(set(errors))


def _validate_landing(errors: list[str], value: Any, schema_version: int) -> None:
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
    if schema_version >= 4:
        keys.update({"auto_merge_requested", "auto_merge_head_sha"})
    if schema_version == 10:
        keys.add("continuity")
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
    if schema_version >= 4:
        if not isinstance(value["auto_merge_requested"], bool):
            _add(errors, f"{path}.auto_merge_requested", "must be boolean")
        _optional_sha(errors, f"{path}.auto_merge_head_sha", value["auto_merge_head_sha"])
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
    if value["mode"] == "local_only" and value["pushed_head_sha"] is not None:
        _add(errors, path, "local_only mode cannot record a pushed head")
    if schema_version == 10:
        continuity = value["continuity"]
        if continuity is not None and _keys(
            errors,
            f"{path}.continuity",
            continuity,
            {"status", "branch_ref", "head_sha", "reason"},
        ):
            if continuity["status"] not in {"planned", "preserved", "blocked", "not_required"}:
                _add(errors, f"{path}.continuity.status", "has an unsupported value")
            _optional_string(errors, f"{path}.continuity.branch_ref", continuity["branch_ref"])
            _optional_sha(errors, f"{path}.continuity.head_sha", continuity["head_sha"])
            _optional_string(errors, f"{path}.continuity.reason", continuity["reason"])
            if continuity["status"] in {"planned", "preserved"}:
                if not _nonempty_string(continuity["branch_ref"]):
                    _add(errors, f"{path}.continuity.branch_ref", "is required for planned or preserved continuity")
                elif not continuity["branch_ref"].startswith("refs/heads/"):
                    _add(errors, f"{path}.continuity.branch_ref", "must be a full local branch ref")
            if continuity["status"] == "preserved" and not is_full_sha(continuity["head_sha"]):
                _add(errors, f"{path}.continuity.head_sha", "is required when continuity is preserved")
            if continuity["status"] == "blocked" and not _nonempty_string(continuity["reason"]):
                _add(errors, f"{path}.continuity.reason", "is required when continuity is blocked")
            if value["mode"] == "pull_request" and continuity["status"] != "not_required":
                _add(errors, f"{path}.continuity.status", "pull_request mode requires not_required")
            if value["mode"] == "local_only" and continuity["status"] == "not_required":
                _add(errors, f"{path}.continuity.status", "local_only mode requires a later-PR continuity path")
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
    if value["merge_status"] != "merged" and value["merged_sha"] is not None:
        _add(errors, path, "only merged status may record merged_sha")
    if schema_version >= 4:
        if value["auto_merge_requested"]:
            if (
                value["mode"] != "pull_request"
                or value["merge_status"] not in {"ready", "merged"}
                or value["auto_merge_head_sha"] is None
                or value["auto_merge_head_sha"] != value["pr_head_sha"]
            ):
                _add(
                    errors,
                    path,
                    "auto_merge_requested requires a ready or merged current-head PR",
                )
        elif value["auto_merge_head_sha"] is not None:
            _add(
                errors,
                f"{path}.auto_merge_head_sha",
                "must be null when auto_merge_requested is false",
            )


def _validate_post_merge_cleanup(
    errors: list[str], value: Any, run: dict[str, Any]
) -> None:
    path = "run.post_merge_cleanup"
    if not _keys(
        errors,
        path,
        value,
        {"status", "base", "worktree", "local_branch", "evidence", "deferred_reason"},
    ):
        return

    status = value["status"]
    if status not in CLEANUP_STATUSES:
        _add(errors, f"{path}.status", "has an unsupported value")

    base = value["base"]
    if _keys(
        errors,
        f"{path}.base",
        base,
        {"branch", "head_sha", "merged_sha_reachable"},
    ):
        _optional_string(errors, f"{path}.base.branch", base["branch"])
        _optional_sha(errors, f"{path}.base.head_sha", base["head_sha"])
        if base["merged_sha_reachable"] is not None and not isinstance(
            base["merged_sha_reachable"], bool
        ):
            _add(
                errors,
                f"{path}.base.merged_sha_reachable",
                "must be null or boolean",
            )

    worktree = value["worktree"]
    if _keys(
        errors,
        f"{path}.worktree",
        worktree,
        {"path", "branch_ref", "head_sha", "dirty", "managed_by", "status"},
    ):
        _optional_string(errors, f"{path}.worktree.path", worktree["path"])
        _optional_string(errors, f"{path}.worktree.branch_ref", worktree["branch_ref"])
        _optional_sha(errors, f"{path}.worktree.head_sha", worktree["head_sha"])
        if worktree["dirty"] is not None and not isinstance(worktree["dirty"], bool):
            _add(errors, f"{path}.worktree.dirty", "must be null or boolean")
        if worktree["managed_by"] not in {None, "parent", "app"}:
            _add(errors, f"{path}.worktree.managed_by", "must be null, parent, or app")
        if worktree["status"] not in CLEANUP_WORKTREE_STATUSES:
            _add(errors, f"{path}.worktree.status", "has an unsupported value")

    local_branch = value["local_branch"]
    if _keys(
        errors,
        f"{path}.local_branch",
        local_branch,
        {"ref", "head_sha", "status"},
    ):
        _optional_string(errors, f"{path}.local_branch.ref", local_branch["ref"])
        _optional_sha(errors, f"{path}.local_branch.head_sha", local_branch["head_sha"])
        if local_branch["status"] not in CLEANUP_BRANCH_STATUSES:
            _add(errors, f"{path}.local_branch.status", "has an unsupported value")
        integration = run.get("integration")
        if (
            isinstance(integration, dict)
            and integration.get("retention") == "persistent"
            and local_branch["status"] == "deleted"
        ):
            _add(
                errors,
                f"{path}.local_branch.status",
                "must not be deleted when run.integration.retention is persistent",
            )

    evidence = _strings(errors, f"{path}.evidence", value["evidence"])
    _optional_string(errors, f"{path}.deferred_reason", value["deferred_reason"])

    if not all(isinstance(item, dict) for item in (base, worktree, local_branch)):
        return

    landing = run.get("landing")
    if not isinstance(landing, dict):
        return

    expected_branch_ref = (
        f"refs/heads/{landing['head_branch']}"
        if _nonempty_string(landing.get("head_branch"))
        and not landing["head_branch"].startswith("refs/heads/")
        else landing.get("head_branch")
    )
    observed = run.get("observed")
    observed_git = observed.get("git") if isinstance(observed, dict) else None
    parent_worktree_path = (
        observed_git.get("parent_worktree_path")
        if isinstance(observed_git, dict)
        else None
    )
    observed_worktrees = (
        observed_git.get("worktrees", [])
        if isinstance(observed_git, dict)
        and isinstance(observed_git.get("worktrees", []), list)
        else []
    )

    worktree_status = worktree.get("status")
    worktree_manager = worktree.get("managed_by")
    if worktree_status in {"pending", "removed"} and worktree_manager != "parent":
        _add(
            errors,
            f"{path}.worktree.managed_by",
            "manual cleanup worktrees must be parent-managed",
        )
    if worktree_status == "platform_managed" and worktree_manager != "app":
        _add(
            errors,
            f"{path}.worktree.managed_by",
            "platform-managed worktrees must be app-managed",
        )
    if worktree_status == "not_applicable" and worktree_manager is not None:
        _add(
            errors,
            f"{path}.worktree.managed_by",
            "must be null when no linked worktree applies",
        )
    if (
        run.get("status") == "complete"
        and landing.get("mode") == "pull_request"
        and status in {"not_started", "ready"}
    ):
        _add(errors, path, "a completed pull-request run must complete or defer cleanup")

    if status == "not_applicable":
        if run.get("status") == "complete":
            if not isinstance(observed, dict) or not _nonempty_string(
                observed.get("captured_at")
            ):
                _add(
                    errors,
                    "run.observed.captured_at",
                    "is required for terminal not-applicable cleanup",
                )
            if not _nonempty_string(parent_worktree_path):
                _add(
                    errors,
                    "run.observed.git.parent_worktree_path",
                    "is required for terminal not-applicable cleanup",
                )
            if any(
                isinstance(item, dict)
                and item.get("path") != parent_worktree_path
                and item.get("branch_ref") == expected_branch_ref
                for item in observed_worktrees
            ):
                _add(
                    errors,
                    f"{path}.worktree.status",
                    "not_applicable requires no matching linked worktree in the current observation",
                )
        if landing.get("mode") == "pull_request" and landing.get("pr_state") not in {
            "closed",
            "not_created",
        }:
            _add(
                errors,
                path,
                "not_applicable is valid only before PR creation, after an unmerged close, or in local-only mode",
            )
        return

    if status == "not_started":
        if value["deferred_reason"] is not None:
            _add(errors, f"{path}.deferred_reason", "must be null unless cleanup is deferred")
        return

    if status == "deferred":
        if not _nonempty_string(value["deferred_reason"]):
            _add(errors, f"{path}.deferred_reason", "is required when cleanup is deferred")
        return

    if value["deferred_reason"] is not None:
        _add(errors, f"{path}.deferred_reason", "must be null unless cleanup is deferred")

    if landing.get("merge_status") != "merged" or landing.get("pr_state") != "merged":
        _add(errors, path, "ready or complete cleanup requires a merged pull request")

    base_branch = landing.get("base_branch")
    if base.get("branch") != base_branch:
        _add(errors, f"{path}.base.branch", "must match landing.base_branch")
    if base.get("head_sha") is None:
        _add(errors, f"{path}.base.head_sha", "is required for cleanup")
    if base.get("merged_sha_reachable") is not True:
        _add(
            errors,
            f"{path}.base.merged_sha_reachable",
            "must be true after observing the merged SHA on the base branch",
        )
    if local_branch.get("ref") != expected_branch_ref:
        _add(errors, f"{path}.local_branch.ref", "must match the merged PR head branch")
    if local_branch.get("head_sha") != landing.get("pr_head_sha"):
        _add(errors, f"{path}.local_branch.head_sha", "must match the merged PR head SHA")

    if not isinstance(observed, dict) or not _nonempty_string(observed.get("captured_at")):
        _add(errors, "run.observed.captured_at", "is required before cleanup")
    if not isinstance(observed_git, dict) or observed_git.get("parent_dirty") is not False:
        _add(errors, "run.observed.git.parent_dirty", "must be false before cleanup")
    if not _nonempty_string(parent_worktree_path):
        _add(errors, "run.observed.git.parent_worktree_path", "is required before cleanup")
    parent_branch = observed_git.get("parent_branch") if isinstance(observed_git, dict) else None
    parent_branch_ref = (
        f"refs/heads/{parent_branch}"
        if _nonempty_string(parent_branch) and not parent_branch.startswith("refs/heads/")
        else parent_branch
    )
    if (
        parent_branch_ref == local_branch.get("ref")
        and isinstance(observed_git, dict)
        and observed_git.get("parent_head_sha") != landing.get("pr_head_sha")
    ):
        _add(
            errors,
            "run.observed.git.parent_head_sha",
            "must match the merged PR head while the primary checkout is on the cleanup branch",
        )

    mission_states = run.get("mission_states")
    if not isinstance(mission_states, dict) or not mission_states or any(
        not isinstance(state, dict) or state.get("phase") != "integrated"
        for state in mission_states.values()
    ):
        _add(errors, path, "cleanup requires every run mission to be integrated")
        mission_ids: list[str] = []
    else:
        mission_ids = list(mission_states)

    branch_target = (
        f"branch:{local_branch['ref']}"
        if _nonempty_string(local_branch.get("ref"))
        else None
    )
    preserve_expiry = status == "complete"
    if branch_target is None or any(
        not authorization_covers(
            run,
            "delete_branches",
            mission_id,
            branch_target,
            preserve_completed_run_expiry=preserve_expiry,
        )
        for mission_id in mission_ids
    ):
        _add(
            errors,
            path,
            "cleanup requires matching delete_branches authorization for the exact local branch",
        )

    if worktree_status in {"pending", "removed"}:
        required_worktree = ("path", "branch_ref", "head_sha", "dirty")
        if any(worktree.get(key) is None for key in required_worktree):
            _add(errors, f"{path}.worktree", "manual cleanup requires path, branch, head, and dirty state")
        if worktree.get("branch_ref") != local_branch.get("ref"):
            _add(errors, f"{path}.worktree.branch_ref", "must match the local cleanup branch")
        if worktree.get("head_sha") != landing.get("pr_head_sha"):
            _add(errors, f"{path}.worktree.head_sha", "must match the merged PR head SHA")
        if worktree.get("dirty") is not False:
            _add(errors, f"{path}.worktree.dirty", "must be false before removal")
        if worktree.get("path") == parent_worktree_path:
            _add(errors, f"{path}.worktree.path", "must not target the primary checkout")
        worktree_target = (
            f"worktree:{worktree['path']}"
            if _nonempty_string(worktree.get("path"))
            else None
        )
        if worktree_target is None or any(
            not authorization_covers(
                run,
                "remove_worktrees",
                mission_id,
                worktree_target,
                preserve_completed_run_expiry=preserve_expiry,
            )
            for mission_id in mission_ids
        ):
            _add(
                errors,
                path,
                "cleanup requires matching remove_worktrees authorization for the exact path",
            )

        matching_worktrees = [
            item
            for item in observed_worktrees
            if isinstance(item, dict) and item.get("path") == worktree.get("path")
        ]
        if status == "ready" and not any(
            item.get("branch_ref") == worktree.get("branch_ref")
            and item.get("head_sha") == worktree.get("head_sha")
            and item.get("managed_by") == "parent"
            and item.get("dirty") is False
            for item in matching_worktrees
        ):
            _add(
                errors,
                f"{path}.worktree",
                "ready cleanup must match an observed clean parent-managed worktree",
            )
        if status == "complete" and matching_worktrees:
            _add(errors, f"{path}.worktree", "removed worktree must be absent from the refreshed observation")
    elif any(
        worktree.get(key) is not None for key in ("path", "branch_ref", "head_sha", "dirty")
    ):
        _add(
            errors,
            f"{path}.worktree",
            "non-manual worktree status must not record manual cleanup fields",
        )

    matching_linked_worktrees = [
        item
        for item in observed_worktrees
        if isinstance(item, dict)
        and item.get("path") != parent_worktree_path
        and item.get("branch_ref") == local_branch.get("ref")
    ]
    if (
        status in {"ready", "complete"}
        and worktree_status == "not_applicable"
        and matching_linked_worktrees
    ):
        _add(
            errors,
            f"{path}.worktree.status",
            "not_applicable requires no matching linked worktree in the current observation",
        )

    if status == "ready":
        if local_branch.get("status") != "pending":
            _add(errors, f"{path}.local_branch.status", "must be pending when cleanup is ready")
        if worktree_status not in {"pending", "not_applicable"}:
            _add(errors, f"{path}.worktree.status", "must be pending or not_applicable when cleanup is ready")
    elif status == "complete":
        integration = run.get("integration")
        retained = isinstance(integration, dict) and integration.get("retention") == "persistent"
        required_branch_status = "preserved" if retained else "deleted"
        if local_branch.get("status") != required_branch_status:
            _add(
                errors,
                f"{path}.local_branch.status",
                f"must be {required_branch_status} when cleanup is complete",
            )
        if worktree_status not in {"removed", "not_applicable"}:
            _add(errors, f"{path}.worktree.status", "must be removed or not_applicable when cleanup is complete")
        if not evidence:
            _add(errors, f"{path}.evidence", "must record cleanup verification evidence")
        if isinstance(observed_git, dict):
            parent_branch = observed_git.get("parent_branch")
            if _nonempty_string(parent_branch):
                parent_branch = parent_branch.removeprefix("refs/heads/")
            if parent_branch != base_branch:
                _add(errors, "run.observed.git.parent_branch", "must be the base branch after cleanup")
            if observed_git.get("parent_head_sha") != base.get("head_sha"):
                _add(errors, "run.observed.git.parent_head_sha", "must match the observed base head after cleanup")


def _validate_gate_results(
    errors: list[str],
    plan: dict[str, Any],
    run: dict[str, Any],
    *,
    plan_key: str,
    run_key: str,
    label: str,
) -> None:
    results = run[run_key]
    root_path = f"run.{run_key}"
    plan_gates = plan.get(plan_key)
    expected_ids = (
        {
            gate["id"]
            for gate in plan_gates
            if isinstance(gate, dict) and _nonempty_string(gate.get("id"))
        }
        if isinstance(plan_gates, list)
        else set()
    )
    if not isinstance(results, list):
        _add(errors, root_path, "must be a list")
        return

    seen: set[str] = set()
    valid_results: list[dict[str, Any]] = []
    result_keys = {"id", "status", "head_sha", "evidence"}
    integration = run.get("integration")
    integration_head = (
        integration.get("integration_head_sha")
        if isinstance(integration, dict)
        else None
    )
    for index, result in enumerate(results):
        path = f"{root_path}[{index}]"
        if not _keys(errors, path, result, result_keys):
            continue
        gate_id = result["id"]
        if not _nonempty_string(gate_id):
            _add(errors, f"{path}.id", "must be a non-empty string")
        else:
            if gate_id not in expected_ids:
                _add(errors, f"{path}.id", f"unknown {label} {gate_id!r}")
            elif gate_id in seen:
                _add(errors, f"{path}.id", "must be unique")
            seen.add(gate_id)
        if not isinstance(result["status"], str) or result["status"] not in GATE_VALUES:
            _add(errors, f"{path}.status", "has an unsupported gate value")
        _optional_sha(errors, f"{path}.head_sha", result["head_sha"])
        evidence = _strings(errors, f"{path}.evidence", result["evidence"])
        if result["status"] == "PASS" and (
            result["head_sha"] is None or not evidence
        ):
            _add(errors, path, "PASS requires head_sha and non-empty evidence")
        if result["status"] == "PASS" and result["head_sha"] != integration_head:
            _add(errors, path, f"PASS {label} must match integration_head_sha")
        if result["status"] == "PASS" and run.get("schema_version") == 10:
            expected_layer = "batch" if plan_key == "batch_verifiers" else "final"
            matching_executions = [
                execution
                for execution in run.get("verifier_executions", [])
                if isinstance(execution, dict)
                and execution.get("verifier_id") == gate_id
                and execution.get("layer") == expected_layer
                and execution.get("mission_id") is None
                and execution.get("task_id") is None
                and execution.get("attempt_id") is None
                and execution.get("lease_id") is None
                and execution.get("status") == "PASS"
                and execution.get("exit_code") == 0
                and execution.get("context", {}).get("head_sha") == result["head_sha"]
                and execution.get("evidence_key") in evidence
            ]
            if not matching_executions:
                _add(
                    errors,
                    path,
                    f"PASS {label} requires exact PASS/exit-0 verifier execution evidence",
                )
        valid_results.append(result)

    if seen != expected_ids:
        _add(errors, root_path, f"IDs must exactly match PLAN {plan_key}")

    if run.get("status") != "complete":
        return
    if any(result.get("status") != "PASS" for result in valid_results):
        _add(errors, root_path, f"complete run requires every {label} to PASS")
    if any(result.get("head_sha") != integration_head for result in valid_results):
        _add(
            errors,
            root_path,
            f"complete run {label} results must match integration_head_sha",
        )


def _validate_workflow_runs(
    errors: list[str], plan: dict[str, Any], run: dict[str, Any]
) -> None:
    value = run.get("workflow_runs")
    if value is None:
        return
    if not isinstance(value, list):
        _add(errors, "run.workflow_runs", "must be a list")
        return
    graph_nodes = {
        node["id"]: node
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict) and _nonempty_string(node.get("id"))
    }
    seen_ids: set[str] = set()
    active_attempts: set[tuple[str, str]] = set()
    entry_keys = {
        "workflow_run_id",
        "workflow_task_id",
        "resume_from_run_id",
        "script_path",
        "script_sha256",
        "run_id",
        "plan_revision",
        "plan_digest_sha256",
        "graph_revision",
        "batch_base_sha",
        "node_ids",
        "attempt_ids",
        "provider",
        "driver",
        "tool_profile",
        "status",
        "result_evidence",
        "metrics",
    }
    for index, item in enumerate(value):
        path = f"run.workflow_runs[{index}]"
        if not _keys(errors, path, item, entry_keys):
            continue
        workflow_run_id = item["workflow_run_id"]
        if not _nonempty_string(workflow_run_id):
            _add(errors, f"{path}.workflow_run_id", "must be a non-empty string")
        elif workflow_run_id in seen_ids:
            _add(errors, f"{path}.workflow_run_id", "must be unique")
        else:
            seen_ids.add(workflow_run_id)
        _optional_string(errors, f"{path}.workflow_task_id", item["workflow_task_id"])
        _optional_string(errors, f"{path}.resume_from_run_id", item["resume_from_run_id"])
        if not _nonempty_string(item["script_path"]):
            _add(errors, f"{path}.script_path", "must be a non-empty string")
        if not _nonempty_string(item["script_sha256"]) or not SHA256_RE.fullmatch(
            item["script_sha256"]
        ):
            _add(errors, f"{path}.script_sha256", "must be a lowercase SHA-256")
        if item["run_id"] != run.get("run_id"):
            _add(errors, f"{path}.run_id", "must match run.run_id")
        if not _is_int(item["plan_revision"]) or item["plan_revision"] < 1:
            _add(errors, f"{path}.plan_revision", "must be a positive integer")
        if not _nonempty_string(item["plan_digest_sha256"]) or not SHA256_RE.fullmatch(
            item["plan_digest_sha256"]
        ):
            _add(errors, f"{path}.plan_digest_sha256", "must be a lowercase SHA-256")
        if not _is_int(item["graph_revision"]) or item["graph_revision"] < 1:
            _add(errors, f"{path}.graph_revision", "must be a positive integer")
        if not isinstance(item["batch_base_sha"], str) or not SHA_RE.fullmatch(
            item["batch_base_sha"]
        ):
            _add(errors, f"{path}.batch_base_sha", "must be a full Git SHA")
        node_ids = _strings(errors, f"{path}.node_ids", item["node_ids"], nonempty=True)
        if len(node_ids) != len(set(node_ids)):
            _add(errors, f"{path}.node_ids", "must not contain duplicates")
        raw_attempt_ids = item["attempt_ids"]
        attempt_ids: dict[str, str] = {}
        if not isinstance(raw_attempt_ids, dict):
            _add(errors, f"{path}.attempt_ids", "must be an object keyed by node ID")
        else:
            for node_id, attempt_id in raw_attempt_ids.items():
                if not _nonempty_string(node_id) or not _nonempty_string(attempt_id):
                    _add(errors, f"{path}.attempt_ids", "keys and values must be non-empty strings")
                    continue
                attempt_ids[node_id] = attempt_id
            if set(attempt_ids) != set(node_ids):
                _add(errors, f"{path}.attempt_ids", "keys must exactly match node_ids")
        provider = item["provider"]
        allowed_drivers = WORKFLOW_RUN_DRIVERS_BY_PROVIDER.get(provider)
        if allowed_drivers is None:
            _add(errors, f"{path}.provider", "has an unsupported workflow provider")
        driver = item["driver"]
        if not isinstance(driver, str) or (
            allowed_drivers is not None and driver not in allowed_drivers
        ):
            _add(errors, f"{path}.driver", "does not match the workflow provider")
        profile = item["tool_profile"]
        if not isinstance(profile, str) or profile not in WORKFLOW_TOOL_PROFILES:
            _add(errors, f"{path}.tool_profile", "has an unsupported value")
        status = item["status"]
        if not isinstance(status, str) or status not in WORKFLOW_RUN_STATUSES:
            _add(errors, f"{path}.status", "has an unsupported value")
        _strings(errors, f"{path}.result_evidence", item["result_evidence"])
        metrics = item["metrics"]
        if _keys(errors, f"{path}.metrics", metrics, {"duration_ms", "token_count"}):
            for metric in ("duration_ms", "token_count"):
                current = metrics[metric]
                if current is not None and (not _is_int(current) or current < 0):
                    _add(errors, f"{path}.metrics.{metric}", "must be null or a non-negative integer")
        if status == "running":
            unknown_nodes = sorted(set(node_ids) - set(graph_nodes))
            if unknown_nodes:
                _add(
                    errors,
                    f"{path}.node_ids",
                    f"running workflow contains unknown graph nodes: {', '.join(unknown_nodes)}",
                )
            if profile == "mission_write" and any(
                graph_nodes.get(node_id, {}).get("kind") != "mission" for node_id in node_ids
            ):
                _add(errors, f"{path}.tool_profile", "mission_write requires only mission nodes")
            if profile in {"code_review_readonly", "visual_review_readonly"}:
                review_types: set[Any] = set()
                for node_id in node_ids:
                    review = graph_nodes.get(node_id, {}).get("review")
                    review_types.add(review.get("type") if isinstance(review, dict) else None)
                allowed_reviews = (
                    {"visual"}
                    if profile == "visual_review_readonly"
                    else {"frontend_code", "backend_code"}
                )
                if not review_types or not review_types.issubset(allowed_reviews):
                    _add(errors, f"{path}.tool_profile", "does not match its review node types")
            if item["plan_revision"] != plan.get("revision"):
                _add(errors, f"{path}.plan_revision", "running workflow must match PLAN")
            if item["plan_digest_sha256"] != plan_digest(plan):
                _add(errors, f"{path}.plan_digest_sha256", "running workflow must match PLAN")
            raw_graph_state = run.get("graph_state")
            graph_state = raw_graph_state if isinstance(raw_graph_state, dict) else {}
            if item["graph_revision"] != graph_state.get("graph_revision"):
                _add(errors, f"{path}.graph_revision", "running workflow is stale")
            raw_integration = run.get("integration")
            integration = raw_integration if isinstance(raw_integration, dict) else {}
            if item["batch_base_sha"] != integration.get("batch_base_sha"):
                _add(errors, f"{path}.batch_base_sha", "running workflow must match RUN")
            for node_id in node_ids:
                attempt_id = attempt_ids.get(node_id)
                state = graph_state.get("node_states", {}).get(node_id, {})
                if state.get("phase") != "running" or state.get("last_attempt_id") != attempt_id:
                    _add(errors, f"{path}.attempt_ids.{node_id}", "must match the active running node attempt")
                elif (node_id, attempt_id) in active_attempts:
                    _add(errors, f"{path}.attempt_ids.{node_id}", "is already bound to another running workflow")
                else:
                    active_attempts.add((node_id, attempt_id))
                node = graph_nodes.get(node_id, {})
                raw_policy = node.get("runtime")
                policy = raw_policy if isinstance(raw_policy, dict) else {}
                raw_allowed = policy.get("allowed_providers")
                allowed_providers = raw_allowed if isinstance(raw_allowed, list) else []
                if provider not in allowed_providers:
                    _add(errors, f"{path}.provider", f"node {node_id} does not allow {provider}")
            if run.get("status") == "complete":
                _add(errors, path, "complete RUN cannot retain a running workflow")


def _validate_verifier_executions(
    errors: list[str], plan: dict[str, Any], run: dict[str, Any]
) -> None:
    value = run.get("verifier_executions")
    if not isinstance(value, list):
        _add(errors, "run.verifier_executions", "must be an append-only list")
        return

    verifier_owners: dict[
        str, tuple[str, str | None, str | None, dict[str, Any]]
    ] = {}
    for mission in plan.get("missions", []):
        if not isinstance(mission, dict):
            continue
        mission_id = mission.get("id")
        for verifier in mission.get("worker_verifiers", []):
            if isinstance(verifier, dict) and _nonempty_string(verifier.get("id")):
                verifier_owners[verifier["id"]] = ("worker", mission_id, None, verifier)
        for verifier in mission.get("integration_verifiers", []):
            if isinstance(verifier, dict) and _nonempty_string(verifier.get("id")):
                verifier_owners[verifier["id"]] = ("mission_integration", mission_id, None, verifier)
        for task in mission.get("tasks", []):
            if not isinstance(task, dict):
                continue
            task_id = task.get("id")
            for verifier in task.get("verifiers", []):
                if isinstance(verifier, dict) and _nonempty_string(verifier.get("id")):
                    verifier_owners[verifier["id"]] = ("task", mission_id, task_id, verifier)
    for plan_key, layer in (("batch_verifiers", "batch"), ("final_gates", "final")):
        for verifier in plan.get(plan_key, []):
            if isinstance(verifier, dict) and _nonempty_string(verifier.get("id")):
                verifier_owners[verifier["id"]] = (layer, None, None, verifier)
    release = plan.get("release")
    if isinstance(release, dict):
        for target in release.get("targets", []):
            if not isinstance(target, dict):
                continue
            commands = target.get("commands")
            if isinstance(commands, dict):
                for verifier in commands.values():
                    if isinstance(verifier, dict) and _nonempty_string(verifier.get("id")):
                        verifier_owners[verifier["id"]] = ("release", None, None, verifier)
            for verifier in target.get("smoke_verifiers", []):
                if isinstance(verifier, dict) and _nonempty_string(verifier.get("id")):
                    verifier_owners[verifier["id"]] = (
                        "release",
                        None,
                        None,
                        verifier,
                    )

    attempt_log = run.get("attempt_log")
    attempt_items = attempt_log if isinstance(attempt_log, list) else []
    attempts_by_id = {
        item.get("attempt_id"): item
        for item in attempt_items
        if isinstance(item, dict) and _nonempty_string(item.get("attempt_id"))
    }
    attempt_ids = set(attempts_by_id)
    mission_states = run.get("mission_states")
    mission_state_items = mission_states.values() if isinstance(mission_states, dict) else []
    lease_ids = {
        state.get("lease_id")
        for state in mission_state_items
        if isinstance(state, dict) and _nonempty_string(state.get("lease_id"))
    }
    workers = run.get("workers")
    worker_items = workers if isinstance(workers, list) else []
    lease_ids.update(
        worker.get("lease_id")
        for worker in worker_items
        if isinstance(worker, dict) and _nonempty_string(worker.get("lease_id"))
    )

    entry_keys = {
        "execution_id",
        "verifier_id",
        "layer",
        "mission_id",
        "task_id",
        "attempt_id",
        "lease_id",
        "protocol",
        "execution_key",
        "evidence_key",
        "key_document",
        "verifier",
        "context",
        "status",
        "exit_code",
        "cache_status",
        "cache_reason",
        "duration_ms",
        "metrics",
        "stdout_sha256",
        "stderr_sha256",
        "evidence_paths",
    }
    seen_execution_ids: set[str] = set()
    for index, item in enumerate(value):
        path = f"run.verifier_executions[{index}]"
        if not _keys(errors, path, item, entry_keys):
            continue
        execution_id = item["execution_id"]
        if not _nonempty_string(execution_id):
            _add(errors, f"{path}.execution_id", "must be a non-empty string")
        elif execution_id in seen_execution_ids:
            _add(errors, f"{path}.execution_id", "must be unique")
        else:
            seen_execution_ids.add(execution_id)
        verifier_id = item["verifier_id"]
        owner = verifier_owners.get(verifier_id)
        declaration: dict[str, Any] | None = None
        if owner is None:
            _add(errors, f"{path}.verifier_id", "must reference a PLAN verifier")
        else:
            expected_layer, expected_mission, expected_task, declaration = owner
            if (item["layer"], item["mission_id"], item["task_id"]) != (
                expected_layer,
                expected_mission,
                expected_task,
            ):
                _add(errors, path, "layer and mission/task association must match the PLAN verifier")
        for key in ("mission_id", "task_id", "attempt_id", "lease_id"):
            _optional_string(errors, f"{path}.{key}", item[key])
        if item["layer"] == "mission_integration" and (
            not _nonempty_string(item["mission_id"])
            or any(item[key] is not None for key in ("task_id", "attempt_id", "lease_id"))
        ):
            _add(
                errors,
                path,
                "mission integration execution requires mission_id and null task/attempt/lease IDs",
            )
        if item["layer"] in {"batch", "final", "release"} and any(
            item[key] is not None
            for key in ("mission_id", "task_id", "attempt_id", "lease_id")
        ):
            _add(
                errors,
                path,
                f"{item['layer']} execution requires null mission/task/attempt/lease IDs",
            )
        if item["attempt_id"] is not None and item["attempt_id"] not in attempt_ids:
            _add(errors, f"{path}.attempt_id", "must reference retained parent attempt state")
        if item["lease_id"] is not None and item["lease_id"] not in lease_ids:
            _add(errors, f"{path}.lease_id", "must reference retained lease state")
        bound_worker: dict[str, Any] | None = None
        if item["layer"] in {"task", "worker"}:
            required_associations = ("mission_id", "attempt_id", "lease_id")
            if item["layer"] == "task":
                required_associations = (*required_associations, "task_id")
            if any(not _nonempty_string(item[key]) for key in required_associations):
                _add(
                    errors,
                    path,
                    f"{item['layer']} execution requires exact mission/task, attempt, and lease association",
                )
            if item["layer"] == "worker" and item["task_id"] is not None:
                _add(errors, f"{path}.task_id", "worker execution must use null task_id")
            attempt = attempts_by_id.get(item["attempt_id"])
            if isinstance(attempt, dict) and (
                attempt.get("mission_id") != item["mission_id"]
                or attempt.get("task_id") != item["task_id"]
                or attempt.get("lease_id") != item["lease_id"]
            ):
                _add(
                    errors,
                    f"{path}.attempt_id",
                    "must reference the exact retained mission/task/lease attempt",
                )
            matching_workers = [
                worker
                for worker in worker_items
                if isinstance(worker, dict)
                and worker.get("mission_id") == item["mission_id"]
                and worker.get("lease_id") == item["lease_id"]
            ]
            if len(matching_workers) != 1:
                _add(
                    errors,
                    f"{path}.lease_id",
                    "must bind exactly one retained mission worker",
                )
            else:
                bound_worker = matching_workers[0]
        protocol = item["protocol"]
        if protocol != "harness-verifier-execution-v1":
            _add(errors, f"{path}.protocol", "has an unsupported value")
        execution_key = item["execution_key"]
        if not isinstance(execution_key, str) or SHA256_RE.fullmatch(execution_key) is None:
            _add(errors, f"{path}.execution_key", "must be a lowercase SHA-256 digest")
        if item["evidence_key"] != execution_key:
            _add(errors, f"{path}.evidence_key", "must match execution_key")
        key_document = item["key_document"]
        key_document_keys = {
            "protocol",
            "verifier_id",
            "layer",
            "mission_id",
            "task_id",
            "attempt_id",
            "lease_id",
            "run_id",
            "plan_revision",
            "plan_digest_sha256",
            "graph_revision",
            "batch_base_sha",
            "head_sha",
            "changed_files_digest",
            "trust_domain",
            "checkout_role",
            "checkout_dirty",
            "cache_safe",
            "cwd",
            "argv",
            "pass_signal",
            "cache_mode",
            "environment_keys",
            "platform",
            "executable_identity",
            "environment_digests",
        }
        if _keys(errors, f"{path}.key_document", key_document, key_document_keys):
            encoded = json.dumps(
                key_document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
            if hashlib.sha256(encoded).hexdigest() != execution_key:
                _add(errors, f"{path}.execution_key", "must match key_document")
            if key_document["protocol"] != protocol:
                _add(errors, f"{path}.key_document.protocol", "must match protocol")
            for key in (
                "verifier_id",
                "layer",
                "mission_id",
                "task_id",
                "attempt_id",
                "lease_id",
            ):
                if key_document[key] != item[key]:
                    _add(errors, f"{path}.key_document.{key}", f"must match {key}")
            if not isinstance(key_document["checkout_dirty"], bool):
                _add(errors, f"{path}.key_document.checkout_dirty", "must be boolean")
            if not isinstance(key_document["cache_safe"], bool):
                _add(errors, f"{path}.key_document.cache_safe", "must be boolean")
            if key_document["cache_mode"] not in {"disabled", "session_exact"}:
                _add(errors, f"{path}.key_document.cache_mode", "has an unsupported value")
            environment_keys = _strings(
                errors,
                f"{path}.key_document.environment_keys",
                key_document["environment_keys"],
            )
            if environment_keys != sorted(set(environment_keys)):
                _add(errors, f"{path}.key_document.environment_keys", "must be sorted and unique")
            if _keys(
                errors,
                f"{path}.key_document.platform",
                key_document["platform"],
                {"system", "machine"},
            ):
                for key in ("system", "machine"):
                    if not isinstance(key_document["platform"][key], str):
                        _add(
                            errors,
                            f"{path}.key_document.platform.{key}",
                            "must be a string",
                        )
            if _keys(
                errors,
                f"{path}.key_document.executable_identity",
                key_document["executable_identity"],
                {"path", "size", "mtime_ns", "device", "inode"},
            ):
                if not _nonempty_string(key_document["executable_identity"]["path"]):
                    _add(
                        errors,
                        f"{path}.key_document.executable_identity.path",
                        "must be a non-empty string",
                    )
                for key in ("size", "mtime_ns", "device", "inode"):
                    if (
                        not _is_int(key_document["executable_identity"][key])
                        or key_document["executable_identity"][key] < 0
                    ):
                        _add(
                            errors,
                            f"{path}.key_document.executable_identity.{key}",
                            "must be a non-negative integer",
                        )
            environment_digests = key_document["environment_digests"]
            if not isinstance(environment_digests, dict):
                _add(
                    errors,
                    f"{path}.key_document.environment_digests",
                    "must be an object",
                )
            else:
                for key, digest in environment_digests.items():
                    if not _nonempty_string(key):
                        _add(
                            errors,
                            f"{path}.key_document.environment_digests",
                            "keys must be non-empty strings",
                        )
                    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
                        _add(
                            errors,
                            f"{path}.key_document.environment_digests.{key}",
                            "must be a lowercase SHA-256 digest",
                        )
        normalized_verifier = item["verifier"]
        if not _keys(
            errors,
            f"{path}.verifier",
            normalized_verifier,
            {"id", "cwd", "argv", "pass_signal", "cache"},
        ):
            pass
        else:
            if normalized_verifier["id"] != verifier_id:
                _add(errors, f"{path}.verifier.id", "must match verifier_id")
            declared_cache = (
                declaration.get("cache")
                if declaration is not None and isinstance(declaration.get("cache"), dict)
                else {"mode": "disabled", "environment_keys": []}
            )
            if declaration is not None and (
                normalized_verifier["cwd"] != declaration.get("cwd")
                or normalized_verifier["argv"] != declaration.get("argv")
                or normalized_verifier["pass_signal"] != declaration.get("pass_signal")
                or normalized_verifier["cache"] != declared_cache
            ):
                _add(errors, f"{path}.verifier", "must exactly match the PLAN verifier declaration")
            if _keys(
                errors,
                f"{path}.verifier.cache",
                normalized_verifier["cache"],
                {"mode", "environment_keys"},
            ):
                if normalized_verifier["cache"]["mode"] not in {
                    "disabled",
                    "session_exact",
                }:
                    _add(
                        errors,
                        f"{path}.verifier.cache.mode",
                        "has an unsupported value",
                    )
                environment_keys = _strings(
                    errors,
                    f"{path}.verifier.cache.environment_keys",
                    normalized_verifier["cache"]["environment_keys"],
                )
                if len(environment_keys) != len(set(environment_keys)):
                    _add(
                        errors,
                        f"{path}.verifier.cache.environment_keys",
                        "must be unique",
                    )
                if isinstance(key_document, dict) and (
                    key_document.get("cache_mode") != normalized_verifier["cache"]["mode"]
                    or key_document.get("environment_keys")
                    != sorted(normalized_verifier["cache"]["environment_keys"])
                ):
                    _add(errors, f"{path}.key_document", "must encode verifier cache policy")
            if not _nonempty_string(normalized_verifier["cwd"]):
                _add(errors, f"{path}.verifier.cwd", "must be a non-empty string")
            _strings(errors, f"{path}.verifier.argv", normalized_verifier["argv"])
            if not _nonempty_string(normalized_verifier["pass_signal"]):
                _add(
                    errors,
                    f"{path}.verifier.pass_signal",
                    "must be a non-empty string",
                )
            if isinstance(key_document, dict) and any(
                key_document.get(key) != normalized_verifier[key]
                for key in ("cwd", "argv", "pass_signal")
            ):
                _add(errors, f"{path}.key_document", "must encode the retained normalized verifier")
        context = item["context"]
        context_keys = {
            "run_id",
            "plan_revision",
            "plan_digest_sha256",
            "graph_revision",
            "batch_base_sha",
            "head_sha",
            "changed_files",
            "trust_domain",
            "checkout_role",
            "checkout_dirty",
            "cache_safe",
            "layer",
            "mission_id",
            "task_id",
            "attempt_id",
            "lease_id",
        }
        if _keys(errors, f"{path}.context", context, context_keys):
            for key in ("layer", "mission_id", "task_id", "attempt_id", "lease_id"):
                if context[key] != item[key]:
                    _add(errors, f"{path}.context.{key}", f"must match {key}")
            if context["run_id"] != run.get("run_id"):
                _add(errors, f"{path}.context.run_id", "must match run_id")
            if context["plan_revision"] != run.get("plan", {}).get("revision"):
                _add(errors, f"{path}.context.plan_revision", "must match run.plan.revision")
            if context["plan_digest_sha256"] != run.get("plan", {}).get("digest_sha256"):
                _add(errors, f"{path}.context.plan_digest_sha256", "must match run.plan.digest_sha256")
            if context["graph_revision"] is not None and not _is_int(
                context["graph_revision"]
            ):
                _add(
                    errors,
                    f"{path}.context.graph_revision",
                    "must be null or an integer",
                )
            for key in ("batch_base_sha", "head_sha"):
                if not is_full_sha(context[key]):
                    _add(
                        errors,
                        f"{path}.context.{key}",
                        "must be a 40- or 64-character lowercase SHA",
                    )
            integration = run.get("integration")
            if bound_worker is not None:
                if context["batch_base_sha"] != bound_worker.get("batch_base_sha"):
                    _add(
                        errors,
                        f"{path}.context.batch_base_sha",
                        "must match the retained worker batch base",
                    )
                if context["head_sha"] != bound_worker.get("worker_head_sha"):
                    _add(
                        errors,
                        f"{path}.context.head_sha",
                        "must match the retained worker head",
                    )
                if context["checkout_role"] != "worker":
                    _add(errors, f"{path}.context.checkout_role", "must equal worker")
                observed_git = run.get("observed", {}).get("git", {})
                if bound_worker.get("workspace_mode") in {
                    "parent_managed_worktree",
                    "app_managed_worktree",
                }:
                    observed_worktrees = (
                        observed_git.get("worktrees", [])
                        if isinstance(observed_git, dict)
                        else []
                    )
                    matching_worktrees = [
                        worktree
                        for worktree in observed_worktrees
                        if isinstance(worktree, dict)
                        and worktree.get("path") == bound_worker.get("worktree_path")
                        and worktree.get("branch_ref") == bound_worker.get("branch_ref")
                        and worktree.get("head_sha") == bound_worker.get("worker_head_sha")
                    ]
                    if len(matching_worktrees) != 1:
                        _add(
                            errors,
                            f"{path}.context",
                            "worker execution requires one matching parent-observed worktree",
                        )
                    elif context["checkout_dirty"] != matching_worktrees[0].get("dirty"):
                        _add(
                            errors,
                            f"{path}.context.checkout_dirty",
                            "must match the parent-observed worker worktree",
                        )
                    elif context["checkout_dirty"] is not False:
                        _add(
                            errors,
                            f"{path}.context.checkout_dirty",
                            "dirty isolated worker worktrees cannot produce accepted verifier evidence",
                        )
                elif isinstance(observed_git, dict) and (
                    context["checkout_dirty"] != observed_git.get("parent_dirty")
                ):
                    _add(
                        errors,
                        f"{path}.context.checkout_dirty",
                        "must match the parent-observed shared checkout",
                    )
            elif isinstance(integration, dict):
                if context["batch_base_sha"] != integration.get("batch_base_sha"):
                    _add(
                        errors,
                        f"{path}.context.batch_base_sha",
                        "must match run.integration.batch_base_sha",
                    )
                if context["head_sha"] != integration.get("integration_head_sha"):
                    _add(
                        errors,
                        f"{path}.context.head_sha",
                        "must match run.integration.integration_head_sha",
                    )
            for key in ("trust_domain", "checkout_role"):
                if not _nonempty_string(context[key]):
                    _add(
                        errors,
                        f"{path}.context.{key}",
                        "must be a non-empty string",
                    )
            changed_files = _strings(errors, f"{path}.context.changed_files", context["changed_files"])
            if changed_files != sorted(set(changed_files)):
                _add(errors, f"{path}.context.changed_files", "must be sorted and unique")
            if not isinstance(context["checkout_dirty"], bool):
                _add(errors, f"{path}.context.checkout_dirty", "must be boolean")
            if not isinstance(context["cache_safe"], bool):
                _add(errors, f"{path}.context.cache_safe", "must be boolean")
            if isinstance(key_document, dict):
                for key in (
                    "run_id",
                    "plan_revision",
                    "plan_digest_sha256",
                    "graph_revision",
                    "batch_base_sha",
                    "head_sha",
                    "trust_domain",
                    "checkout_role",
                    "checkout_dirty",
                    "cache_safe",
                    "layer",
                    "mission_id",
                    "task_id",
                    "attempt_id",
                    "lease_id",
                ):
                    if key_document.get(key) != context[key]:
                        _add(errors, f"{path}.key_document.{key}", "must match context")
                changed_digest = hashlib.sha256(
                    json.dumps(
                        changed_files,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).hexdigest()
                if key_document.get("changed_files_digest") != changed_digest:
                    _add(errors, f"{path}.key_document.changed_files_digest", "must match context")
        status = item["status"]
        exit_code = item["exit_code"]
        if status not in {"PASS", "FAIL", "TIMEOUT", "ERROR"}:
            _add(errors, f"{path}.status", "has an unsupported value")
        elif status == "PASS" and exit_code != 0:
            _add(errors, f"{path}.exit_code", "PASS requires exit_code 0")
        elif status == "FAIL" and (
            not _is_int(exit_code) or exit_code == 0
        ):
            _add(errors, f"{path}.exit_code", "FAIL requires a nonzero integer exit_code")
        elif status in {"TIMEOUT", "ERROR"} and exit_code is not None:
            _add(errors, f"{path}.exit_code", f"{status} requires null exit_code")
        if item["cache_status"] not in {"bypassed", "miss", "stored", "reused"}:
            _add(errors, f"{path}.cache_status", "has an unsupported value")
        elif item["cache_status"] in {"stored", "reused"} and (
            status != "PASS" or exit_code != 0
        ):
            _add(
                errors,
                f"{path}.cache_status",
                "stored or reused execution must be PASS with exit_code 0",
            )
        if not _nonempty_string(item["cache_reason"]):
            _add(errors, f"{path}.cache_reason", "must be a non-empty string")
        if not _is_int(item["duration_ms"]) or item["duration_ms"] < 0:
            _add(errors, f"{path}.duration_ms", "must be a non-negative integer")
        if _keys(errors, f"{path}.metrics", item["metrics"], {"executed", "reused"}):
            metrics_valid = True
            for metric in ("executed", "reused"):
                if not _is_int(item["metrics"][metric]) or item["metrics"][metric] < 0:
                    metrics_valid = False
                    _add(errors, f"{path}.metrics.{metric}", "must be a non-negative integer")
            if metrics_valid:
                expected_metrics = (
                    {"executed": 0, "reused": 1}
                    if item["cache_status"] == "reused"
                    else {"executed": 1, "reused": 0}
                )
                if item["metrics"] != expected_metrics:
                    _add(
                        errors,
                        f"{path}.metrics",
                        "must record exactly one execution or exact cache reuse",
                    )
        for key in ("stdout_sha256", "stderr_sha256"):
            digest = item[key]
            if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
                _add(errors, f"{path}.{key}", "must be a lowercase SHA-256 digest")
        _strings(errors, f"{path}.evidence_paths", item["evidence_paths"])


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
    plan_declares_release = (
        plan.get("schema_version") in {3, 4, 5} and "release" in plan
    )
    graph_run = (
        plan.get("schema_version") == 4 and schema_version in {8, 9}
    ) or (plan.get("schema_version") == 5 and schema_version == 10)
    if graph_run:
        run_keys.update({"graph_state", "review_workers"})
    if schema_version in {3, 4, 5, 6, 7, 8, 9, 10}:
        run_keys.add("landing")
    if schema_version in {5, 6, 7, 8, 9, 10}:
        run_keys.add("post_merge_cleanup")
    if schema_version in {7, 8, 9} and plan_declares_release:
        run_keys.add("deployments")
    if schema_version == 10:
        run_keys.add("verifier_executions")
        if plan_declares_release:
            run_keys.add("targets")
    if schema_version in {9, 10}:
        run_keys.update({"batch_gate_results", "final_gate_results", "ui_evidence"})
    if schema_version not in SUPPORTED_RUN_SCHEMA_VERSIONS:
        _add(errors, "run.schema_version", "must equal 2 through 10")
    if plan.get("schema_version") == 4 and schema_version not in {8, 9}:
        _add(errors, "run.schema_version", "must equal 8 or 9 for a schema v4 graph PLAN")
    elif plan.get("schema_version") == 5 and schema_version != 10:
        _add(errors, "run.schema_version", "must equal 10 for a schema v5 graph PLAN")
    elif schema_version == 8 and plan.get("schema_version") != 4:
        _add(errors, "run.schema_version", "schema v8 requires a schema v4 graph PLAN")
    elif schema_version == 10 and plan.get("schema_version") != 5:
        _add(errors, "run.schema_version", "schema v10 requires a schema v5 graph PLAN")
    elif (
        plan_declares_release
        and plan.get("schema_version") == 3
        and schema_version not in {7, 9}
    ):
        _add(
            errors,
            "run.schema_version",
            "must equal 7 or 9 when a schema v3 PLAN declares release",
        )
    optional_run_keys = {"deployments"} if schema_version in {7, 8, 9} else set()
    if schema_version == 10:
        optional_run_keys.add("targets")
    if graph_run:
        optional_run_keys.add("workflow_runs")
    if not _keys(errors, "run", run, run_keys, optional_run_keys):
        return sorted(errors)
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
    if schema_version == 10 and (
        run.get("plan_readiness") == "ready"
        or run.get("execution_authorized") is True
        or run.get("status") in {"running", "complete"}
    ):
        for index, source in enumerate(plan.get("sources", [])):
            if not isinstance(source, dict):
                continue
            if source.get("status") not in {"frozen", "delta_accepted"}:
                _add(
                    errors,
                    f"plan.sources[{index}].status",
                    "ready or executable RUN requires a frozen or delta_accepted source",
                )
            if _is_product_staging_location(source.get("location")):
                _add(
                    errors,
                    f"plan.sources[{index}].location",
                    "ready or executable RUN cannot use product staging paths",
                )
    if not isinstance(run["execution_authorized"], bool):
        _add(errors, "run.execution_authorized", "must be boolean")
    if (
        run.get("execution_authorized") is True
        and plan_declares_release
        and plan.get("schema_version") in {3, 4}
        and isinstance(run.get("landing"), dict)
        and run["landing"].get("mode") == "local_only"
    ):
        _add(
            errors,
            "run.execution_authorized",
            "cannot authorize execution for a release PLAN in local_only mode: the "
            "production target requires a merged PR, which local_only never records",
        )
    if (
        plan.get("schema_version") == 5
        and isinstance(plan.get("release"), dict)
        and (
            run.get("plan_readiness") == "ready"
            or run.get("execution_authorized") is True
            or run.get("status") in {"running", "complete"}
        )
    ):
        unresolved_targets = sorted(
            target.get("id", "<unknown>")
            for target in plan["release"].get("targets", [])
            if isinstance(target, dict)
            and (
                any(
                    target.get(key) is None
                    for key in (
                        "source",
                        "artifact_kind",
                        "requires_signing",
                        "channel",
                        "trigger",
                        "migration_classification",
                    )
                )
                or isinstance(target.get("commands"), dict)
                and target["commands"].get("build") is None
            )
        )
        if unresolved_targets:
            _add(
                errors,
                "run.plan_readiness",
                "ready or executable RUN has unresolved release semantics: "
                + ", ".join(unresolved_targets),
            )
    if (
        run.get("execution_authorized") is True
        and plan.get("schema_version") in {4, 5}
        and isinstance(plan.get("graph"), dict)
    ):
        reviewed_missions: set[str] = set()
        raw_graph_nodes = plan["graph"].get("nodes", [])
        raw_graph_edges = plan["graph"].get("edges", [])
        graph_nodes = raw_graph_nodes if isinstance(raw_graph_nodes, list) else []
        graph_edges = raw_graph_edges if isinstance(raw_graph_edges, list) else []
        mission_node_ids = {
            node["ref"]: node["id"]
            for node in graph_nodes
            if isinstance(node, dict)
            and node.get("kind") == "mission"
            and isinstance(node.get("id"), str)
            and isinstance(node.get("ref"), str)
        }
        for node in graph_nodes:
            if not isinstance(node, dict):
                continue
            if node.get("kind") != "verifier" or node.get("executor") != "runtime_worker":
                continue
            review = node.get("review")
            if not isinstance(review, dict):
                continue
            mission_ids = review.get("mission_ids") or []
            if schema_version == 10:
                if (
                    len(mission_ids) != 1
                    or not isinstance(mission_ids[0], str)
                    or not isinstance(node.get("allowed_outcomes"), list)
                    or "pass" not in node["allowed_outcomes"]
                    or not any(
                        isinstance(edge, dict)
                        and edge.get("kind") == "dependency"
                        and edge.get("from") == mission_node_ids.get(mission_ids[0])
                        and edge.get("to") == node.get("id")
                        for edge in graph_edges
                    )
                ):
                    continue
            for mission_id in mission_ids:
                if isinstance(mission_id, str):
                    reviewed_missions.add(mission_id)
        unreviewed = sorted(
            mission["id"]
            for mission in plan.get("missions", [])
            if isinstance(mission, dict)
            and isinstance(mission.get("id"), str)
            and mission.get("write_scope")
            and mission["id"] not in reviewed_missions
        )
        if unreviewed:
            review_requirement = (
                "no direct singleton pre-integration review node"
                if schema_version == 10
                else "no review node"
            )
            _add(
                errors,
                "run.execution_authorized",
                "cannot authorize execution while these missions have a write scope "
                f"and {review_requirement}: " + ", ".join(unreviewed),
            )
    if run["execution_authorized"]:
        if not _nonempty_string(run["execution_authorization_source"]):
            _add(errors, "run.execution_authorization_source", "is required when authorized")
        _validate_authorization_scope(
            errors,
            "run.execution_authorization_scope",
            run["execution_authorization_scope"],
            action=False,
            require_plan_binding=(schema_version == 10),
        )
        if isinstance(run["execution_authorization_scope"], dict):
            execution_scope = run["execution_authorization_scope"]
            if execution_scope.get("run_id") != run["run_id"]:
                _add(errors, "run.execution_authorization_scope.run_id", "must match run_id")
            if schema_version == 10:
                if execution_scope.get("plan_revision") != run.get("plan", {}).get("revision"):
                    _add(errors, "run.execution_authorization_scope.plan_revision", "must match run.plan.revision")
                if execution_scope.get("plan_digest_sha256") != run.get("plan", {}).get("digest_sha256"):
                    _add(errors, "run.execution_authorization_scope.plan_digest_sha256", "must match run.plan.digest_sha256")
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

    authorization_keys = (
        AUTHORIZATION_KEYS_V10
        if schema_version == 10
        else AUTHORIZATION_KEYS_V8
        if schema_version in {8, 9}
        else AUTHORIZATION_KEYS
        if schema_version in {3, 4, 5, 6, 7}
        else AUTHORIZATION_KEYS_V2
    )
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
            optional_entry_keys = {"scope", "expires_when"}
            if schema_version == 10:
                optional_entry_keys.add("authorized_head_sha")
            if not _keys(
                errors,
                path,
                entry,
                {"authorized", "source"},
                optional_entry_keys,
            ):
                continue
            if not isinstance(entry["authorized"], bool):
                _add(errors, f"{path}.authorized", "must be boolean")
            if entry["authorized"]:
                if not _nonempty_string(entry["source"]):
                    _add(errors, f"{path}.source", "is required when authorized")
                if "scope" not in entry or "expires_when" not in entry:
                    _add(errors, path, "authorized action requires scope and expires_when")
                else:
                    _validate_authorization_scope(
                        errors,
                        f"{path}.scope",
                        entry["scope"],
                        action=True,
                        action_name=action,
                        allow_future_pr=(schema_version in {6, 7, 8, 9, 10}),
                        require_plan_binding=(schema_version == 10),
                    )
                    if isinstance(entry["scope"], dict):
                        action_scope = entry["scope"]
                        if action_scope.get("run_id") != run["run_id"]:
                            _add(errors, f"{path}.scope.run_id", "must match run_id")
                        if schema_version == 10:
                            if action_scope.get("plan_revision") != run.get("plan", {}).get("revision"):
                                _add(errors, f"{path}.scope.plan_revision", "must match run.plan.revision")
                            if action_scope.get("plan_digest_sha256") != run.get("plan", {}).get("digest_sha256"):
                                _add(errors, f"{path}.scope.plan_digest_sha256", "must match run.plan.digest_sha256")
                    if entry["expires_when"] not in EXPIRY_BOUNDARIES:
                        _add(
                            errors,
                            f"{path}.expires_when",
                            "must be wave_closed, run_complete, or explicit_revocation",
                        )
                if schema_version == 10 and action in HEAD_BOUND_AUTHORIZATION_ACTIONS:
                    authorized_head = entry.get("authorized_head_sha")
                    if not is_full_sha(authorized_head):
                        _add(
                            errors,
                            f"{path}.authorized_head_sha",
                            "is required for this exact head-bound action",
                        )
                    targets = entry.get("scope", {}).get("targets", []) if isinstance(entry.get("scope"), dict) else []
                    if "*" in targets:
                        _add(
                            errors,
                            f"{path}.scope.targets",
                            "head-bound remote actions require exact targets, not *",
                        )
                elif schema_version == 10 and entry.get("authorized_head_sha") is not None:
                    _add(
                        errors,
                        f"{path}.authorized_head_sha",
                        "is only allowed for head-bound remote actions",
                    )
            else:
                if entry["source"] is not None:
                    _add(errors, f"{path}.source", "must be null when unauthorized")
                if "scope" in entry or "expires_when" in entry:
                    _add(errors, path, "unauthorized action must omit scope and expires_when")
                if schema_version == 10 and "authorized_head_sha" in entry:
                    _add(errors, f"{path}.authorized_head_sha", "must be omitted when unauthorized")

    if schema_version in {3, 4, 5, 6, 7, 8, 9, 10}:
        _validate_landing(errors, run["landing"], schema_version)
    if schema_version == 10 and isinstance(run.get("landing"), dict):
        landing = run["landing"]
        continuity = landing.get("continuity")
        integration = run.get("integration") if isinstance(run.get("integration"), dict) else {}
        head_branch = landing.get("head_branch")
        integration_branch = integration.get("branch")
        base_branch = landing.get("base_branch")
        normalized_head = (
            head_branch.removeprefix("refs/heads/")
            if _nonempty_string(head_branch)
            else None
        )
        normalized_integration = (
            integration_branch.removeprefix("refs/heads/")
            if _nonempty_string(integration_branch)
            else None
        )
        normalized_base = (
            base_branch.removeprefix("refs/heads/")
            if _nonempty_string(base_branch)
            else None
        )
        if normalized_head is None:
            _add(errors, "run.landing.head_branch", "is required for PLAN v5 branch continuity")
        if normalized_head != normalized_integration:
            _add(errors, "run.integration.branch", "must match landing.head_branch for PLAN v5")
        if normalized_head is not None and normalized_head == normalized_base:
            _add(errors, "run.landing.head_branch", "must differ from landing.base_branch")
        expected_branch_ref = (
            f"refs/heads/{normalized_integration}"
            if normalized_integration is not None
            else None
        )
        if isinstance(continuity, dict):
            continuity_status = continuity.get("status")
            continuity_branch = continuity.get("branch_ref")
            continuity_head = continuity.get("head_sha")
            if continuity_status in {"planned", "preserved", "blocked"} and (
                continuity_branch != expected_branch_ref
            ):
                _add(
                    errors,
                    "run.landing.continuity.branch_ref",
                    "must equal the exact retained integration branch ref",
                )
            if continuity_status == "planned" and continuity_head is not None:
                _add(errors, "run.landing.continuity.head_sha", "must be null while continuity is planned")
            if continuity_status in {"preserved", "blocked"} and continuity_head is not None and (
                continuity_head != integration.get("integration_head_sha")
            ):
                _add(
                    errors,
                    "run.landing.continuity.head_sha",
                    "must match the current integration head when recorded",
                )
            if continuity_status == "not_required" and any(
                continuity.get(key) is not None for key in ("branch_ref", "head_sha", "reason")
            ):
                _add(
                    errors,
                    "run.landing.continuity",
                    "not_required continuity must not record branch, head, or reason",
                )
        if landing.get("mode") == "local_only" and (
            landing.get("checks_status") != "not_started"
            or landing.get("review_status") != "not_requested"
            or landing.get("merge_status") != "not_ready"
            or landing.get("auto_merge_requested") is not False
            or any(
                landing.get(key) is not None
                for key in (
                    "checks_head_sha",
                    "review_head_sha",
                    "blocking_findings",
                    "unresolved_threads",
                    "merged_sha",
                    "auto_merge_head_sha",
                )
            )
        ):
            _add(errors, "run.landing", "local_only mode cannot record remote landing evidence")
        if landing.get("mode") == "local_only" and run.get("execution_authorized") is True:
            if not isinstance(continuity, dict) or continuity.get("status") not in {"planned", "preserved"}:
                _add(
                    errors,
                    "run.landing.continuity",
                    "authorized local_only execution requires a planned or preserved later-PR branch",
                )
        if landing.get("mode") == "local_only" and run.get("status") == "complete":
            integration = run.get("integration")
            integration_head = integration.get("integration_head_sha") if isinstance(integration, dict) else None
            if (
                not isinstance(continuity, dict)
                or continuity.get("status") != "preserved"
                or continuity.get("head_sha") != integration_head
            ):
                _add(
                    errors,
                    "run.landing.continuity",
                    "complete local_only run requires preserved continuity at the integration head",
                )
        if (
            landing.get("mode") == "pull_request"
            and landing.get("pr_state") in {"draft", "open", "merged"}
            and (
                landing.get("merge_status") in {"ready", "merged"}
                or run.get("status") == "complete"
            )
            and landing.get("pr_head_sha") != integration.get("integration_head_sha")
        ):
            _add(
                errors,
                "run.landing.pr_head_sha",
                "closing PR, review, CI, and final evidence must match the current integration head",
            )
    if (
        schema_version in {4, 5, 6, 7, 8, 9, 10}
        and isinstance(run["landing"], dict)
        and run["landing"].get("auto_merge_requested") is True
    ):
        pr_url = run["landing"].get("pr_url")
        mission_states = run.get("mission_states")
        if (
            not _nonempty_string(pr_url)
            or not isinstance(mission_states, dict)
            or not mission_states
            or any(
                not authorization_covers(
                    run,
                    "merge_pr",
                    mission_id,
                    f"pr:{pr_url}",
                    preserve_completed_run_expiry=(
                        run["landing"].get("merge_status") == "merged"
                    ),
                )
                for mission_id in mission_states
            )
        ):
            _add(
                errors,
                "run.landing",
                "auto_merge_requested requires matching merge_pr authorization for the exact PR",
            )
        authorizations = run.get("authorizations", {})
        merge_entry = authorizations.get("merge_pr", {}) if isinstance(authorizations, dict) else {}
        merge_scope = merge_entry.get("scope", {}) if isinstance(merge_entry, dict) else {}
        merge_targets = merge_scope.get("targets", []) if isinstance(merge_scope, dict) else []
        if schema_version == 10:
            if merge_entry.get("authorized_head_sha") != run["landing"].get("pr_head_sha"):
                _add(
                    errors,
                    "run.authorizations.merge_pr.authorized_head_sha",
                    "must match the exact current PR head for auto-merge",
                )
            release = plan.get("release")
            release_targets = release.get("targets", []) if isinstance(release, dict) else []
            merge_triggered_ids = [
                target.get("id")
                for target in release_targets
                if isinstance(target, dict) and target.get("trigger") == "merge"
            ]
            missing_consequences = [
                target_id
                for target_id in merge_triggered_ids
                if f"release:{target_id}" not in merge_targets
            ]
            if missing_consequences:
                _add(
                    errors,
                    "run.authorizations.merge_pr.scope.targets",
                    "merge authorization must include its auto-deploy release targets: "
                    + ", ".join(sorted(missing_consequences)),
                )
            deploy_entry = (
                authorizations.get("deploy", {})
                if isinstance(authorizations, dict)
                else {}
            )
            triggering_head = run["landing"].get("pr_head_sha")
            missing_deploy_authorizations = [
                target_id
                for target_id in merge_triggered_ids
                if deploy_entry.get("authorized_head_sha") != triggering_head
                or not isinstance(mission_states, dict)
                or not mission_states
                or any(
                    not authorization_covers(
                        run,
                        "deploy",
                        mission_id,
                        f"release:{target_id}",
                        preserve_completed_run_expiry=(
                            run["landing"].get("merge_status") == "merged"
                        ),
                    )
                    for mission_id in mission_states
                )
            ]
            if missing_deploy_authorizations:
                _add(
                    errors,
                    "run.authorizations.deploy",
                    "auto-merge requires separate exact deploy authorization at the triggering PR head for: "
                    + ", ".join(sorted(missing_deploy_authorizations)),
                )
        future_targets = {
            target
            for target in merge_targets
            if isinstance(target, str) and FUTURE_PR_TARGET_RE.fullmatch(target)
        }
        if future_targets and _landing_future_pr_target(run["landing"]) not in future_targets:
            _add(
                errors,
                "run.landing",
                "auto_merge_requested exact PR does not match its authorized future PR binding",
            )
    if schema_version in {5, 6, 7, 8, 9, 10}:
        _validate_post_merge_cleanup(errors, run["post_merge_cleanup"], run)
    if schema_version in {7, 8, 9} and "deployments" in run:
        _validate_deployments(errors, run["deployments"], run, plan)
    if schema_version == 10 and "targets" in run:
        _validate_targets(errors, run["targets"], run, plan)

    runtime_keys = {
        "worker_runtime",
        "workspace_mode",
        "completion_channel",
        "max_parallel_workers",
        "platform_lifecycle",
    }
    if schema_version in {6, 7, 8, 9, 10}:
        runtime_keys.add("runtime_adapter")
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
        if not _is_int(runtime["max_parallel_workers"]) or runtime["max_parallel_workers"] < 1:
            _add(errors, "run.runtime_capabilities.max_parallel_workers", "must be a positive integer")
        adapter = runtime.get("runtime_adapter")
        adapter_path = "run.runtime_capabilities.runtime_adapter"
        if schema_version in {6, 7, 8, 9, 10} and adapter is None:
            _add(errors, adapter_path, "must be an object")
        elif adapter is not None and _keys(
            errors,
            adapter_path,
            adapter,
            {
                "provider",
                "available_drivers",
                "detection_source",
            },
        ):
            provider = adapter["provider"]
            provider_valid = isinstance(provider, str) and provider in RUNTIME_PROVIDERS
            if not provider_valid:
                _add(errors, f"{adapter_path}.provider", "has an unsupported value")
            drivers = _strings(
                errors,
                f"{adapter_path}.available_drivers",
                adapter["available_drivers"],
                nonempty=True,
            )
            unknown_drivers = sorted(set(drivers) - RUNTIME_DRIVERS)
            if unknown_drivers:
                _add(
                    errors,
                    f"{adapter_path}.available_drivers",
                    f"unsupported drivers: {', '.join(unknown_drivers)}",
                )
            allowed_drivers = set(RUNTIME_DRIVER_PRIORITY.get(provider, ())) if provider_valid else set()
            incompatible_drivers = sorted(set(drivers) - allowed_drivers)
            if provider_valid and incompatible_drivers:
                _add(
                    errors,
                    f"{adapter_path}.available_drivers",
                    f"drivers do not match provider: {', '.join(incompatible_drivers)}",
                )
            if "sequential_parent" not in drivers:
                _add(
                    errors,
                    f"{adapter_path}.available_drivers",
                    "must include sequential_parent as the safe fallback",
                )
            detection_source = adapter["detection_source"]
            if not isinstance(detection_source, str) or detection_source not in RUNTIME_DETECTION_SOURCES:
                _add(errors, f"{adapter_path}.detection_source", "has an unsupported value")

            selected_driver = route_runtime_driver(runtime)
            if selected_driver == "app_threads" and (
                provider != "codex"
                or runtime["worker_runtime"] != "app_task"
                or runtime["workspace_mode"] != "app_managed_worktree"
                or runtime["completion_channel"] != "thread_poll"
            ):
                _add(errors, adapter_path, "app_threads requires codex app_task/app_managed_worktree/thread_poll")
            elif selected_driver == "dynamic_workflow" and (
                provider != "claude_code"
                or runtime["worker_runtime"] != "subagent"
                or runtime["workspace_mode"] != "parent_managed_worktree"
                or runtime["completion_channel"] != "agent_result"
            ):
                _add(
                    errors,
                    adapter_path,
                    "dynamic_workflow requires claude_code subagent/parent_managed_worktree/agent_result",
                )
            elif selected_driver == "subagents" and (
                runtime["worker_runtime"] != "subagent"
                or runtime["workspace_mode"] not in {"shared_checkout", "parent_managed_worktree"}
                or runtime["completion_channel"] not in {"agent_result", "report_file"}
            ):
                _add(errors, adapter_path, "subagents requires a supported subagent workspace and result channel")
            elif selected_driver == "sequential_parent" and (
                runtime["worker_runtime"] != "parent"
                or runtime["workspace_mode"] != "shared_checkout"
                or runtime["completion_channel"] != "agent_result"
            ):
                _add(errors, adapter_path, "sequential_parent requires parent/shared_checkout/agent_result")
            if selected_driver == "dynamic_workflow" and runtime.get("nested_subagents") is not None:
                _add(
                    errors,
                    "run.runtime_capabilities.nested_subagents",
                    "must be omitted for flat dynamic-workflow orchestration",
                )
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
        observed_git_keys = {
            "parent_branch",
            "parent_head_sha",
            "parent_dirty",
            "worktrees",
        }
        if schema_version in {5, 6, 7, 8, 9, 10}:
            observed_git_keys.add("parent_worktree_path")
        if _keys(errors, "run.observed.git", git, observed_git_keys):
            if schema_version in {5, 6, 7, 8, 9, 10}:
                _optional_string(
                    errors,
                    "run.observed.git.parent_worktree_path",
                    git["parent_worktree_path"],
                )
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
    integration_optional_keys = {"retention"}
    integration_prior_heads: set[str] = set()
    if schema_version == 10:
        integration_optional_keys.add("prior_head_shas")
    if _keys(
        errors,
        "run.integration",
        integration,
        {"branch", "batch_base_sha", "integration_head_sha"},
        integration_optional_keys,
    ):
        _optional_string(errors, "run.integration.branch", integration["branch"])
        _optional_sha(errors, "run.integration.batch_base_sha", integration["batch_base_sha"])
        _optional_sha(errors, "run.integration.integration_head_sha", integration["integration_head_sha"])
        if schema_version == 10 and "prior_head_shas" in integration:
            integration_prior_heads = _validated_sha_history(
                errors,
                "run.integration.prior_head_shas",
                integration.get("prior_head_shas"),
            )
        if integration.get("integration_head_sha") in integration_prior_heads:
            _add(
                errors,
                "run.integration.prior_head_shas",
                "must contain only superseded integration heads",
            )
        retention = integration.get("retention")
        if retention is not None and retention not in {"persistent", "ephemeral"}:
            _add(errors, "run.integration.retention", "must be null, persistent, or ephemeral")
        if (
            schema_version in {3, 4, 5, 6, 7, 8, 9}
            and isinstance(run["landing"], dict)
            and run["landing"].get("mode") == "pull_request"
            and _nonempty_string(run["landing"].get("head_branch"))
            and (
                not _nonempty_string(integration["branch"])
                or integration["branch"].removeprefix("refs/heads/")
                != run["landing"]["head_branch"].removeprefix("refs/heads/")
            )
        ):
            _add(
                errors,
                "run.landing",
                "pull_request mode requires integration.branch to match head_branch",
            )
        if (
            schema_version in {3, 4, 5, 6, 7, 8, 9}
            and isinstance(run["landing"], dict)
            and (
                run["landing"].get("checks_status") == "PASS"
                or run["landing"].get("review_status") == "PASS"
            )
            and run["landing"].get("pr_head_sha") != integration["integration_head_sha"]
        ):
            _add(
                errors,
                "run.landing",
                "PASS landing evidence requires the current PR head to match integration_head_sha",
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
    mission_state_optional_keys = (
        {"prior_head_shas"} if schema_version == 10 else set()
    )
    mission_prior_heads: dict[str, set[str]] = {}
    if not isinstance(mission_states, dict):
        _add(errors, "run.mission_states", "must be an object")
    else:
        if set(mission_states) != mission_ids:
            _add(errors, "run.mission_states", "keys must exactly match PLAN missions")
        for mission_id, state in mission_states.items():
            path = f"run.mission_states.{mission_id}"
            if not _keys(
                errors,
                path,
                state,
                mission_state_keys,
                mission_state_optional_keys,
            ):
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
            if schema_version == 10 and "prior_head_shas" in state:
                prior_heads = _validated_sha_history(
                    errors,
                    f"{path}.prior_head_shas",
                    state["prior_head_shas"],
                )
                mission_prior_heads[mission_id] = prior_heads
                if state.get("head_sha") in prior_heads:
                    _add(
                        errors,
                        f"{path}.prior_head_shas",
                        "must contain only superseded mission heads",
                    )
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

    if graph_run:
        _validate_graph_state(errors, plan, run)
        _validate_workflow_runs(errors, plan, run)

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
    graph_nodes_by_mission = {
        node.get("ref"): node
        for node in plan.get("graph", {}).get("nodes", [])
        if isinstance(node, dict) and node.get("kind") == "mission"
    } if plan.get("schema_version") in {4, 5} and isinstance(plan.get("graph"), dict) else {}
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
            if not _keys(
                errors,
                path,
                worker,
                worker_keys,
                {
                    "nested_subagent_policy",
                    "nested_review_evidence",
                    "runtime_binding",
                },
            ):
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
            runtime_binding = worker.get("runtime_binding")
            if graph_run and worker["mission_id"] in graph_nodes_by_mission and runtime_binding is None:
                _add(
                    errors,
                    f"{path}.runtime_binding",
                    "is required for a PLAN-v4 graph worker",
                )
            if runtime_binding is not None and _keys(
                errors,
                f"{path}.runtime_binding",
                runtime_binding,
                {
                    "provider",
                    "driver",
                    "source",
                    "model",
                    "reasoning_effort",
                    "option_source",
                },
            ):
                if runtime_binding["provider"] not in RUNTIME_PROVIDERS:
                    _add(errors, f"{path}.runtime_binding.provider", "has an unsupported value")
                if not _nonempty_string(runtime_binding["driver"]):
                    _add(errors, f"{path}.runtime_binding.driver", "must be a non-empty string")
                if runtime_binding["source"] != "host":
                    _add(errors, f"{path}.runtime_binding.source", "has an unsupported value")
                if runtime_binding["option_source"] not in {
                    "plan_provider_options",
                    "provider_default",
                }:
                    _add(errors, f"{path}.runtime_binding.option_source", "has an unsupported value")
                model = runtime_binding["model"]
                if model is not None and not is_safe_model_token(model):
                    _add(errors, f"{path}.runtime_binding.model", "must be null or a safe model token")
                effort = runtime_binding["reasoning_effort"]
                if effort is not None and effort not in RUNTIME_REASONING_EFFORTS:
                    _add(
                        errors,
                        f"{path}.runtime_binding.reasoning_effort",
                        "must be null or a supported reasoning effort",
                    )
                if runtime_binding["provider"] not in {"codex", "claude_code"} and effort is not None:
                    _add(
                        errors,
                        f"{path}.runtime_binding.reasoning_effort",
                        "must be null unless the provider supports selectable effort",
                    )
                graph_node = graph_nodes_by_mission.get(worker["mission_id"])
                policy = graph_node.get("runtime") if isinstance(graph_node, dict) else None
                if isinstance(policy, dict):
                    provider = runtime_binding["provider"]
                    if provider not in policy.get("allowed_providers", []):
                        _add(
                            errors,
                            f"{path}.runtime_binding.provider",
                            "must be allowed by the matching PLAN node",
                        )
                    expected_options = resolve_runtime_options(policy, provider)
                    if runtime_binding["model"] != expected_options["model"]:
                        _add(
                            errors,
                            f"{path}.runtime_binding.model",
                            "must match the matching PLAN provider option",
                        )
                    if (
                        runtime_binding["reasoning_effort"]
                        != expected_options["reasoning_effort"]
                    ):
                        _add(
                            errors,
                            f"{path}.runtime_binding.reasoning_effort",
                            "must match the matching PLAN provider option",
                        )
                    if runtime_binding["option_source"] != expected_options["option_source"]:
                        _add(
                            errors,
                            f"{path}.runtime_binding.option_source",
                            "must identify the matching PLAN option source",
                        )
            if worker["completion_channel"] == "report_file" and not _nonempty_string(worker["report_path"]):
                _add(errors, f"{path}.report_path", "is required for report_file")
            nested_policy = worker.get("nested_subagent_policy")
            nested_review_evidence = worker.get("nested_review_evidence")
            if (
                schema_version in {6, 7, 8, 9, 10}
                and isinstance(runtime, dict)
                and route_runtime_driver(runtime) == "dynamic_workflow"
                and nested_policy is not None
            ):
                _add(
                    errors,
                    f"{path}.nested_subagent_policy",
                    "must be omitted for flat dynamic-workflow orchestration",
                )
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
                    if (
                        schema_version == 10
                        and "reviewer" not in policy_roles
                    ):
                        _add(
                            errors,
                            f"{path}.nested_subagent_policy.allowed_roles",
                            "must include reviewer when enabled",
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
            if nested_review_evidence is not None and _keys(
                errors,
                f"{path}.nested_review_evidence",
                nested_review_evidence,
                {
                    "agent_id",
                    "role",
                    "task",
                    "status",
                    "summary",
                    "evidence_paths",
                    "reviewed_sha",
                    "decision",
                },
            ):
                for key in ("agent_id", "task", "summary"):
                    if not _nonempty_string(nested_review_evidence[key]):
                        _add(
                            errors,
                            f"{path}.nested_review_evidence.{key}",
                            "must be a non-empty string",
                        )
                if nested_review_evidence["role"] != "reviewer":
                    _add(
                        errors,
                        f"{path}.nested_review_evidence.role",
                        "must equal reviewer",
                    )
                if nested_review_evidence["status"] != "completed":
                    _add(
                        errors,
                        f"{path}.nested_review_evidence.status",
                        "must equal completed",
                    )
                _strings(
                    errors,
                    f"{path}.nested_review_evidence.evidence_paths",
                    nested_review_evidence["evidence_paths"],
                )
                if (
                    schema_version == 10
                    and not is_full_sha(nested_review_evidence["reviewed_sha"])
                ):
                    _add(
                        errors,
                        f"{path}.nested_review_evidence.reviewed_sha",
                        "must be a full lowercase Git SHA",
                    )
                else:
                    _optional_sha(
                        errors,
                        f"{path}.nested_review_evidence.reviewed_sha",
                        nested_review_evidence["reviewed_sha"],
                    )
                if nested_review_evidence["decision"] != "PASS":
                    _add(
                        errors,
                        f"{path}.nested_review_evidence.decision",
                        "must equal PASS",
                    )
                if (
                    is_full_sha(worker["worker_head_sha"])
                    and nested_review_evidence["reviewed_sha"]
                    != worker["worker_head_sha"]
                ):
                    _add(
                        errors,
                        f"{path}.nested_review_evidence.reviewed_sha",
                        "must match worker_head_sha",
                    )
                if not (
                    isinstance(nested_policy, dict)
                    and nested_policy.get("enabled") is True
                ):
                    _add(
                        errors,
                        f"{path}.nested_review_evidence",
                        "is allowed only for an enabled nested-subagent policy",
                    )

    if graph_run:
        review_workers = run["review_workers"]
        review_nodes = {
            node.get("id"): node
            for node in plan.get("graph", {}).get("nodes", [])
            if isinstance(node, dict)
            and node.get("kind") == "verifier"
            and node.get("executor") == "runtime_worker"
        }
        mission_node_refs = {
            node.get("id"): node.get("ref")
            for node in plan.get("graph", {}).get("nodes", [])
            if isinstance(node, dict) and node.get("kind") == "mission"
        }
        review_worker_keys = {
            "worker_id",
            "node_id",
            "attempt_id",
            "plan_revision",
            "plan_digest_sha256",
            "graph_revision",
            "reviewed_sha",
            "review_path",
            "worker_runtime",
            "completion_channel",
            "runtime_binding",
            "task_thread_id",
            "report_path",
            "phase",
            "outcome",
            "findings",
        }
        if not isinstance(review_workers, list):
            _add(errors, "run.review_workers", "must be a list")
        else:
            for index, worker in enumerate(review_workers):
                path = f"run.review_workers[{index}]"
                if not _keys(errors, path, worker, review_worker_keys):
                    continue
                for key in (
                    "worker_id",
                    "node_id",
                    "attempt_id",
                    "plan_digest_sha256",
                    "reviewed_sha",
                    "review_path",
                ):
                    if not _nonempty_string(worker[key]):
                        _add(errors, f"{path}.{key}", "must be a non-empty string")
                if worker["worker_id"] in worker_ids:
                    _add(errors, f"{path}.worker_id", "must be unique across all workers")
                worker_ids.add(worker["worker_id"])
                node = review_nodes.get(worker["node_id"])
                if node is None:
                    _add(errors, f"{path}.node_id", "must reference a runtime-worker verifier")
                outcome = worker["outcome"]
                if outcome is not None and (
                    not isinstance(outcome, str)
                    or (node is not None and outcome not in node.get("allowed_outcomes", []))
                ):
                    _add(errors, f"{path}.outcome", "is not declared by the reviewed node")
                findings = _strings(errors, f"{path}.findings", worker["findings"])
                if outcome not in (None, "pass") and not findings:
                    _add(errors, f"{path}.findings", "is required when outcome is not pass")
                if worker["phase"] in {"worker_passed", "blocked", "worker_failed"} and outcome is None:
                    _add(
                        errors,
                        f"{path}.outcome",
                        "is required once the review worker reaches a terminal phase",
                    )
                if not _is_int(worker["plan_revision"]) or worker["plan_revision"] < 1:
                    _add(errors, f"{path}.plan_revision", "must be a positive integer")
                if worker["plan_revision"] != plan.get("revision"):
                    _add(errors, f"{path}.plan_revision", "must match the current PLAN")
                _optional_sha(errors, f"{path}.plan_digest_sha256", worker["plan_digest_sha256"])
                if worker["plan_digest_sha256"] != plan_digest(plan):
                    _add(errors, f"{path}.plan_digest_sha256", "must match the current PLAN")
                if worker["graph_revision"] != run["graph_state"]["graph_revision"]:
                    _add(errors, f"{path}.graph_revision", "must match the current graph revision")
                _optional_sha(errors, f"{path}.reviewed_sha", worker["reviewed_sha"])
                reviewed_mission_ids = (
                    set(node.get("review", {}).get("mission_ids", []))
                    if isinstance(node, dict) and isinstance(node.get("review"), dict)
                    else set()
                )
                mission_state_items = (
                    mission_states.items()
                    if isinstance(mission_states, dict)
                    else []
                )
                reviewed_mission_states = {
                    mission_id: state
                    for mission_id, state in mission_state_items
                    if mission_id in reviewed_mission_ids and isinstance(state, dict)
                }
                direct_preintegration_mission_ids = {
                    mission_node_refs.get(edge.get("from"))
                    for edge in plan.get("graph", {}).get("edges", [])
                    if isinstance(edge, dict)
                    and edge.get("kind") == "dependency"
                    and edge.get("to") == worker["node_id"]
                    and len(
                        (review_nodes.get(worker["node_id"]) or {})
                        .get("review", {})
                        .get("mission_ids", [])
                    )
                    == 1
                    and mission_node_refs.get(edge.get("from"))
                    in reviewed_mission_ids
                }
                raw_state = run["graph_state"]["node_states"].get(
                    worker["node_id"], {}
                )
                state = raw_state if isinstance(raw_state, dict) else {}
                current_reviewable_shas = {
                    sha
                    for sha in (
                        run.get("integration", {}).get("integration_head_sha"),
                        run.get("landing", {}).get("pr_head_sha"),
                        *(
                            state.get("integrated_sha")
                            for state in reviewed_mission_states.values()
                        ),
                        *(
                            state.get("head_sha")
                            for mission_id, state in reviewed_mission_states.items()
                            if mission_id in direct_preintegration_mission_ids
                        ),
                        *(
                            sha
                            for mission_id in direct_preintegration_mission_ids
                            for sha in mission_prior_heads.get(mission_id, set())
                        ),
                    )
                    if is_full_sha(sha)
                }
                if (
                    state.get("last_outcome") == "fix_required"
                    and worker.get("outcome") == "fix_required"
                ):
                    current_reviewable_shas.update(integration_prior_heads)
                is_current_attempt = state.get("last_attempt_id") == worker["attempt_id"]
                if (
                    worker["reviewed_sha"] not in current_reviewable_shas
                    and is_current_attempt
                ):
                    _add(
                        errors,
                        f"{path}.reviewed_sha",
                        "must identify the direct singleton pre-integration worktree, integrated, or PR head",
                    )
                if worker["worker_runtime"] not in {"parent", "subagent", "app_task"}:
                    _add(errors, f"{path}.worker_runtime", "has an unsupported value")
                if worker["completion_channel"] not in {
                    "agent_result",
                    "thread_poll",
                    "report_file",
                    "user_relay",
                }:
                    _add(errors, f"{path}.completion_channel", "has an unsupported value")
                for key in ("task_thread_id", "report_path"):
                    _optional_string(errors, f"{path}.{key}", worker[key])
                if worker["completion_channel"] == "report_file" and not _nonempty_string(
                    worker["report_path"]
                ):
                    _add(errors, f"{path}.report_path", "is required for report_file")
                if worker["phase"] not in WORKER_PHASES:
                    _add(errors, f"{path}.phase", "has an unsupported value")
                if worker["phase"] in {"worker_running", "worker_passed"} and (
                    state.get("bound_worker_id") != worker["worker_id"]
                    or state.get("last_attempt_id") != worker["attempt_id"]
                ):
                    _add(errors, path, "active review worker must match the bound graph attempt")
                binding = worker["runtime_binding"]
                if _keys(
                    errors,
                    f"{path}.runtime_binding",
                    binding,
                    {
                        "provider",
                        "driver",
                        "source",
                        "model",
                        "reasoning_effort",
                        "option_source",
                    },
                ):
                    provider = binding["provider"]
                    policy = node.get("runtime") if isinstance(node, dict) else None
                    if provider not in RUNTIME_PROVIDERS:
                        _add(errors, f"{path}.runtime_binding.provider", "has an unsupported value")
                    if not isinstance(policy, dict) or provider not in policy.get(
                        "allowed_providers", []
                    ):
                        _add(
                            errors,
                            f"{path}.runtime_binding.provider",
                            "must be allowed by the matching review node",
                        )
                    if not _nonempty_string(binding["driver"]):
                        _add(errors, f"{path}.runtime_binding.driver", "must be a non-empty string")
                    if binding["source"] != "host":
                        _add(errors, f"{path}.runtime_binding.source", "has an unsupported value")
                    expected_options = (
                        resolve_runtime_options(policy, provider)
                        if isinstance(policy, dict)
                        else {
                            "model": None,
                            "reasoning_effort": None,
                            "option_source": "provider_default",
                        }
                    )
                    if binding["model"] is not None and not is_safe_model_token(binding["model"]):
                        _add(errors, f"{path}.runtime_binding.model", "must be null or a safe model token")
                    if binding["model"] != expected_options["model"]:
                        _add(errors, f"{path}.runtime_binding.model", "must match the review node")
                    if binding["reasoning_effort"] != expected_options["reasoning_effort"]:
                        _add(
                            errors,
                            f"{path}.runtime_binding.reasoning_effort",
                            "must match the review node",
                        )
                    if binding["option_source"] != expected_options["option_source"]:
                        _add(
                            errors,
                            f"{path}.runtime_binding.option_source",
                            "must identify the matching PLAN option source",
                        )
        workers_by_id = (
            {
                worker.get("worker_id"): worker
                for worker in workers
                if isinstance(worker, dict)
            }
            if isinstance(workers, list)
            else {}
        )
        mission_state_items = (
            mission_states.items()
            if schema_version == 10 and isinstance(mission_states, dict)
            else []
        )
        for mission_id, state in mission_state_items:
            if not isinstance(state, dict) or state.get("phase") not in {
                "integrating",
                "integrated",
            }:
                continue
            mission_worker = workers_by_id.get(state.get("worker_id"), {})
            if (
                not mission_worker
                or mission_worker.get("mission_id") != mission_id
            ):
                if schema_version == 10:
                    _add(
                        errors,
                        f"run.mission_states.{mission_id}.worker_id",
                        "transition to integrating requires a worker belonging to the same mission",
                    )
                continue
            nested_policy = (
                mission_worker.get("nested_subagent_policy")
                if isinstance(mission_worker, dict)
                else None
            )
            nested_policy_enabled = (
                isinstance(nested_policy, dict)
                and nested_policy.get("enabled") is True
            )
            nested_review_evidence = mission_worker.get(
                "nested_review_evidence"
            )
            head_sha = state.get("head_sha")
            if nested_policy_enabled:
                has_task_local_review = (
                    is_full_sha(head_sha)
                    and mission_worker.get("worker_head_sha") == head_sha
                    and isinstance(nested_review_evidence, dict)
                    and nested_review_evidence.get("role") == "reviewer"
                    and nested_review_evidence.get("status") == "completed"
                    and is_full_sha(nested_review_evidence.get("reviewed_sha"))
                    and nested_review_evidence.get("reviewed_sha") == head_sha
                    and nested_review_evidence.get("decision") == "PASS"
                )
                if not has_task_local_review:
                    _add(
                        errors,
                        f"run.mission_states.{mission_id}.integration_gate",
                        "transition to integrating requires retained task-local exact-head PASS review evidence",
                    )
            mission_node_ids = {
                node.get("id")
                for node in plan.get("graph", {}).get("nodes", [])
                if isinstance(node, dict)
                and node.get("kind") == "mission"
                and node.get("ref") == mission_id
            }
            preintegration_review_ids = {
                edge.get("to")
                for edge in plan.get("graph", {}).get("edges", [])
                if isinstance(edge, dict)
                and edge.get("kind") == "dependency"
                and edge.get("from") in mission_node_ids
                and edge.get("to") in review_nodes
                and len(
                    review_nodes[edge["to"]]
                    .get("review", {})
                    .get("mission_ids", [])
                )
                == 1
                and mission_id
                in review_nodes[edge["to"]]
                .get("review", {})
                .get("mission_ids", [])
            }
            raw_graph_state = run.get("graph_state")
            raw_node_states = (
                raw_graph_state.get("node_states")
                if isinstance(raw_graph_state, dict)
                else None
            )
            node_states = (
                raw_node_states if isinstance(raw_node_states, dict) else {}
            )
            review_node_states = {
                node_id: node_state
                for node_id, node_state in node_states.items()
                if isinstance(node_state, dict)
            }
            current_review_workers = {
                review_node_id: next(
                    (
                        review_worker
                        for review_worker in (
                            review_workers
                            if isinstance(review_workers, list)
                            else []
                        )
                        if isinstance(review_worker, dict)
                        and review_worker.get("node_id") == review_node_id
                        and review_worker.get("worker_id")
                        == review_node_states.get(review_node_id, {}).get(
                            "bound_worker_id"
                        )
                        and review_worker.get("attempt_id")
                        == review_node_states.get(review_node_id, {}).get(
                            "last_attempt_id"
                        )
                        and review_worker.get("reviewed_sha") == head_sha
                        and review_worker.get("worker_runtime")
                        in {"parent", "subagent", "app_task"}
                        and review_worker.get("phase") == "worker_passed"
                        and review_worker.get("outcome") is not None
                    ),
                    None,
                )
                for review_node_id in preintegration_review_ids
            }
            has_parent_review = (
                bool(preintegration_review_ids)
                and all(
                    review_node_states.get(review_node_id, {}).get("phase")
                    == "succeeded"
                    and review_node_states.get(review_node_id, {}).get(
                        "last_outcome"
                    )
                    == "pass"
                    and isinstance(
                        current_review_workers.get(review_node_id),
                        dict,
                    )
                    for review_node_id in preintegration_review_ids
                )
                and (
                    not nested_policy_enabled
                    or (
                        isinstance(nested_review_evidence, dict)
                        and any(
                            review_worker.get("worker_id")
                            == nested_review_evidence.get("agent_id")
                            and review_worker.get("outcome") == "pass"
                            for review_worker in current_review_workers.values()
                            if isinstance(review_worker, dict)
                        )
                    )
                )
                and sum(
                    current_review_workers[review_node_id].get("outcome")
                    == "pass"
                    for review_node_id in preintegration_review_ids
                )
                * 2
                > len(preintegration_review_ids)
            )
            if not has_parent_review:
                _add(
                    errors,
                    f"run.mission_states.{mission_id}.integration_gate",
                    "transition to integrating requires every planned pre-integration review node to retain a current-head reconciled PASS and a strict majority of exact-head reviewer PASS outcomes",
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

    if schema_version == 10:
        _validate_verifier_executions(errors, plan, run)

    if schema_version in {9, 10}:
        _validate_gate_results(
            errors,
            plan,
            run,
            plan_key="batch_verifiers",
            run_key="batch_gate_results",
            label="batch gate",
        )
        _validate_gate_results(
            errors,
            plan,
            run,
            plan_key="final_gates",
            run_key="final_gate_results",
            label="final gate",
        )
        _validate_ui_evidence(errors, plan, run)

    if schema_version in {8, 9, 10} and run.get("status") == "complete":
        if run.get("intent") not in {"plan-then-execute", "execute-ready-plan"}:
            _add(errors, "run.intent", "complete run requires execution intent")
        if run.get("plan_readiness") != "ready":
            _add(errors, "run.plan_readiness", "complete run requires ready plan")
        plan_sources = plan.get("sources")
        complete_source_statuses = (
            {"frozen", "delta_accepted"}
            if schema_version == 10
            else {"frozen", "delta accepted"}
        )
        if isinstance(plan_sources, list) and any(
            source.get("status") not in complete_source_statuses
            for source in plan_sources
            if isinstance(source, dict)
        ):
            _add(
                errors,
                "plan.sources",
                "complete run requires every source to be frozen or delta accepted",
            )
        if not isinstance(integration, dict) or integration.get("integration_head_sha") is None:
            _add(
                errors,
                "run.integration.integration_head_sha",
                "complete run requires an integration head",
            )
        landing = run.get("landing")
        if (
            isinstance(landing, dict)
            and landing.get("mode") == "pull_request"
            and (
                landing.get("pr_state") != "merged"
                or landing.get("merge_status") != "merged"
            )
        ):
            _add(
                errors,
                "run.landing",
                "complete pull-request run requires merged current-head landing",
            )
        if isinstance(landing, dict) and landing.get("mode") == "pull_request":
            pr_url = landing.get("pr_url")
            authorizations = run.get("authorizations")
            merge_authorization = (
                authorizations.get("merge_pr")
                if isinstance(authorizations, dict)
                else None
            )
            merge_scope = (
                merge_authorization.get("scope")
                if isinstance(merge_authorization, dict)
                else None
            )
            merge_targets = (
                merge_scope.get("targets") if isinstance(merge_scope, dict) else None
            )
            if (
                not _nonempty_string(pr_url)
                or not isinstance(merge_targets, list)
                or f"pr:{pr_url}" not in merge_targets
                or not isinstance(mission_states, dict)
                or not mission_states
                or any(
                    not authorization_covers(
                        run,
                        "merge_pr",
                        mission_id,
                        f"pr:{pr_url}",
                        preserve_completed_run_expiry=True,
                    )
                    for mission_id in mission_states
                )
            ):
                _add(
                    errors,
                    "run.authorizations.merge_pr",
                    "complete pull-request run requires merge authorization for the exact PR",
                )
            if schema_version == 10 and (
                not isinstance(merge_authorization, dict)
                or merge_authorization.get("authorized_head_sha")
                != landing.get("pr_head_sha")
            ):
                _add(
                    errors,
                    "run.authorizations.merge_pr.authorized_head_sha",
                    "complete pull-request run requires merge authorization at the current PR head",
                )
        if graph_run:
            graph_state = run.get("graph_state")
            node_states = (
                graph_state.get("node_states", {})
                if isinstance(graph_state, dict)
                else {}
            )
            edge_states = (
                graph_state.get("edge_states", {})
                if isinstance(graph_state, dict)
                else {}
            )
            if not isinstance(node_states, dict) or any(
                not isinstance(state, dict)
                or state.get("phase")
                not in {"succeeded", "skipped", "superseded"}
                for state in node_states.values()
            ):
                _add(
                    errors,
                    "run.graph_state.node_states",
                    "complete graph run requires every node to succeed, skip, or be superseded",
                )
            if isinstance(node_states, dict) and any(
                isinstance(state, dict) and bool(state.get("blockers"))
                for state in node_states.values()
            ):
                _add(
                    errors,
                    "run.graph_state.node_states",
                    "complete graph run cannot retain node blockers",
                )
            if isinstance(node_states, dict) and any(
                isinstance(state, dict)
                and state.get("phase") == "succeeded"
                and state.get("last_outcome") != "pass"
                for state in node_states.values()
            ):
                _add(
                    errors,
                    "run.graph_state.node_states",
                    "complete graph run requires every succeeded node to have pass outcome",
                )
            if not isinstance(edge_states, dict) or any(
                not isinstance(state, dict)
                or state.get("status") not in {"traversed", "exhausted", "skipped"}
                for state in edge_states.values()
            ):
                _add(
                    errors,
                    "run.graph_state.edge_states",
                    "complete graph run requires every edge to be terminal",
                )
        if not isinstance(mission_states, dict) or any(
            not isinstance(state, dict)
            or state.get("phase") not in {"integrated", "superseded"}
            for state in mission_states.values()
        ):
            _add(
                errors,
                "run.mission_states",
                "complete run requires every mission to be integrated or superseded",
            )
        if isinstance(mission_states, dict) and any(
            isinstance(state, dict) and bool(state.get("blockers"))
            for state in mission_states.values()
        ):
            _add(errors, "run.mission_states", "complete run cannot retain mission blockers")

        superseded_mission_ids = (
            {
                mission_id
                for mission_id, state in mission_states.items()
                if isinstance(state, dict) and state.get("phase") == "superseded"
            }
            if isinstance(mission_states, dict)
            else set()
        )
        superseded_task_ids = {
            item["id"]
            for current_mission in plan.get("missions", [])
            if isinstance(current_mission, dict)
            for item in current_mission.get("tasks", [])
            if (
                isinstance(item, dict)
                and _nonempty_string(item.get("id"))
                and (
                    item.get("replaced_by")
                    or current_mission.get("id") in superseded_mission_ids
                )
            )
        }
        task_closeout_invalid = not isinstance(task_states, dict)
        if isinstance(task_states, dict):
            for task_id, state in task_states.items():
                expected_phase = (
                    "superseded" if task_id in superseded_task_ids else "mission_recorded"
                )
                if not isinstance(state, dict) or state.get("phase") != expected_phase:
                    task_closeout_invalid = True
                    break
        if task_closeout_invalid:
            _add(
                errors,
                "run.task_states",
                "complete run requires every task to be mission_recorded or superseded",
            )
        if isinstance(task_states, dict) and any(
            isinstance(state, dict)
            and state.get("phase") == "mission_recorded"
            and state.get("verifier_status") != "PASS"
            for state in task_states.values()
        ):
            _add(
                errors,
                "run.task_states",
                "complete run requires every recorded task verifier to PASS",
            )
        if isinstance(task_states, dict) and any(
            isinstance(state, dict) and bool(state.get("blockers"))
            for state in task_states.values()
        ):
            _add(errors, "run.task_states", "complete run cannot retain task blockers")
        if isinstance(wave, dict) and wave.get("status") in {"proposed", "active"}:
            _add(errors, "run.active_wave", "complete run cannot retain an open wave")
        if isinstance(workers, list) and any(
            isinstance(worker, dict)
            and worker.get("phase") in {"leased", "worker_running", "blocked"}
            for worker in workers
        ):
            _add(errors, "run.workers", "complete run cannot retain active or blocked workers")
        review_workers = run.get("review_workers")
        if graph_run and isinstance(review_workers, list) and any(
            isinstance(worker, dict)
            and worker.get("phase") in {"leased", "worker_running", "blocked"}
            for worker in review_workers
        ):
            _add(
                errors,
                "run.review_workers",
                "complete run cannot retain active or blocked review workers",
            )

    return sorted(set(errors))

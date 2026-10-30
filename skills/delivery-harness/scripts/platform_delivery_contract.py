#!/usr/bin/env python3
"""Join the canonical platform-delivery contract to a PLAN v6 graph."""

from __future__ import annotations

from typing import Any


PROTOCOL = "platform-delivery/1"


def _add(errors: list[str], path: str, message: str) -> None:
    errors.append(f"{path}: {message}")


def _strings(
    errors: list[str], path: str, value: Any, *, nonempty: bool = False
) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        _add(errors, path, "must be a list of non-empty strings")
        return []
    if nonempty and not value:
        _add(errors, path, "must not be empty")
    if len(value) != len(set(value)):
        _add(errors, path, "must not contain duplicates")
    return value


def platform_delivery_shape_errors(plan: dict[str, Any]) -> list[str]:
    """Validate the optional PLAN shape before immutable source bytes are read."""

    errors: list[str] = []
    value = plan.get("platform_delivery")
    if value is None:
        return errors
    if not isinstance(value, dict):
        _add(errors, "plan.platform_delivery", "must be an object")
        return errors
    if set(value) != {"protocol", "stages"}:
        _add(
            errors,
            "plan.platform_delivery",
            "must contain exactly protocol and stages",
        )
        return errors
    if value["protocol"] != PROTOCOL:
        _add(
            errors,
            "plan.platform_delivery.protocol",
            f"must equal {PROTOCOL!r}",
        )
    stages = value["stages"]
    if not isinstance(stages, list) or not stages:
        _add(errors, "plan.platform_delivery.stages", "must be a non-empty list")
        return errors
    for index, stage in enumerate(stages):
        path = f"plan.platform_delivery.stages[{index}]"
        if not isinstance(stage, dict) or set(stage) != {
            "id",
            "mission_ids",
            "completion_mission_id",
            "integration_verifier_ids",
        }:
            _add(
                errors,
                path,
                "must contain exactly id, mission_ids, completion_mission_id, "
                "and integration_verifier_ids",
            )
            continue
        if not isinstance(stage["id"], str) or not stage["id"].strip():
            _add(errors, f"{path}.id", "must be a non-empty string")
        _strings(errors, f"{path}.mission_ids", stage["mission_ids"], nonempty=True)
        if not isinstance(stage["completion_mission_id"], str) or not stage[
            "completion_mission_id"
        ].strip():
            _add(
                errors,
                f"{path}.completion_mission_id",
                "must be a non-empty string",
            )
        _strings(
            errors,
            f"{path}.integration_verifier_ids",
            stage["integration_verifier_ids"],
            nonempty=True,
        )
    return errors


def _acceptance_test_ids(value: Any, path: str, errors: list[str]) -> list[str]:
    ids = _strings(errors, path, value)
    if any(not item.startswith("TEST-") for item in ids):
        _add(errors, path, "must contain only TEST-* IDs")
    return ids


def _unsafe_review_dependency(
    source_node: dict[str, Any] | None,
    target_node: dict[str, Any] | None,
) -> bool:
    """Return true when an edge cannot prove an integrated platform barrier."""

    if not isinstance(target_node, dict) or target_node.get(
        "kind"
    ) != "verifier" or target_node.get("executor") != "runtime_worker":
        return False
    review = target_node.get("review")
    if not isinstance(review, dict):
        return True
    stage = review.get("stage", "preintegration")
    mission_ids = review.get("mission_ids")
    if not isinstance(stage, str) or stage not in {"preintegration", "integration"}:
        return True
    if (
        not isinstance(mission_ids, list)
        or not mission_ids
        or any(not isinstance(item, str) or not item.strip() for item in mission_ids)
        or len(mission_ids) != len(set(mission_ids))
    ):
        return True
    return (
        stage == "preintegration"
        and len(mission_ids) == 1
        and isinstance(source_node, dict)
        and source_node.get("kind") == "mission"
        and source_node.get("ref") in mission_ids
    )


def _dependency_adjacency(plan: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, str]]:
    graph = plan.get("graph", {}) if isinstance(plan.get("graph"), dict) else {}
    nodes = {
        node.get("id"): node
        for node in graph.get("nodes", []) if isinstance(node, dict)
    }
    node_missions = {
        node_id: node["ref"]
        for node_id, node in nodes.items()
        if node.get("kind") == "mission" and isinstance(node.get("ref"), str)
    }
    dependencies: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    for edge in graph.get("edges", []):
        if not isinstance(edge, dict) or edge.get("kind") != "dependency":
            continue
        source, target = edge.get("from"), edge.get("to")
        source_node = nodes.get(source)
        target_node = nodes.get(target)
        if _unsafe_review_dependency(source_node, target_node):
            continue
        if source in nodes and target in nodes:
            dependencies[source].add(target)
    return dependencies, node_missions


def _reachable_nodes(
    dependencies: dict[str, set[str]], start_node: str
) -> set[str]:
    reached: set[str] = set()
    pending = list(dependencies.get(start_node, ()))
    while pending:
        node_id = pending.pop()
        if node_id in reached:
            continue
        reached.add(node_id)
        pending.extend(dependencies.get(node_id, ()))
    return reached


def _reaches_mission(
    dependencies: dict[str, set[str]],
    node_missions: dict[str, str],
    source_mission: str,
    target_missions: set[str],
) -> bool:
    source_nodes = [
        node_id
        for node_id, mission_id in node_missions.items()
        if mission_id == source_mission
    ]
    target_nodes = {
        node_id
        for node_id, mission_id in node_missions.items()
        if mission_id in target_missions
    }
    return any(
        _reachable_nodes(dependencies, source_node) & target_nodes
        for source_node in source_nodes
    )


def _annotated_verifier_tests(
    plan: dict[str, Any],
) -> tuple[set[str], set[str], list[str]]:
    errors: list[str] = []
    final_tests: set[str] = set()
    platform_tests: set[str] = set()
    verifier_groups = (("final_gates", None),)
    missions = {item.get("id"): item for item in plan.get("missions", []) if isinstance(item, dict)}
    for plan_key, _layer in verifier_groups:
        for gate in plan.get(plan_key, []):
            if not isinstance(gate, dict):
                continue
            ids = _acceptance_test_ids(
                gate.get("acceptance_test_ids", []),
                f"plan.{plan_key}.verifier.acceptance_test_ids",
                errors,
            )
            if ids:
                final_tests.update(ids)
                platform_tests.update(ids)
    for mission_id, mission in missions.items():
        for verifier in mission.get("integration_verifiers", []):
            if not isinstance(verifier, dict):
                continue
            ids = _acceptance_test_ids(
                verifier.get("acceptance_test_ids", []),
                f"plan.missions[{mission_id}].verifier.acceptance_test_ids",
                errors,
            )
            if ids:
                platform_tests.update(ids)
    return final_tests, platform_tests, errors


def _feature_gate_errors(
    plan: dict[str, Any],
    platform_tests: set[str],
    feature_test_authority: dict[str, set[str]] | None = None,
    *,
    require_feature_gates: bool = False,
) -> list[str]:
    errors: list[str] = []
    trace_tests: dict[str, set[str]] = {}
    carrying_missions: dict[str, set[str]] = {}
    missions = [item for item in plan.get("missions", []) if isinstance(item, dict)]
    for mission in missions:
        mission_id = mission.get("id")
        for task in mission.get("tasks", []):
            if not isinstance(task, dict):
                continue
            task_traces = {
                trace_id
                for trace_id in task.get("trace_ids", []) if isinstance(trace_id, str)
            }
            for trace_id in task_traces:
                carrying_missions.setdefault(trace_id, set()).add(mission_id)
            for row in task.get("acceptance_matrix", []):
                if not isinstance(row, dict):
                    continue
                test_id = row.get("test_id")
                if not isinstance(test_id, str):
                    continue
                for trace_id in row.get("trace_ids", []):
                    if isinstance(trace_id, str) and trace_id in task_traces:
                        trace_tests.setdefault(trace_id, set()).add(test_id)
    for trace in plan.get("traces", []):
        if not isinstance(trace, dict):
            continue
        trace_id = trace.get("id")
        is_feature = isinstance(trace_id, str) and trace_id.startswith("PRD-")
        if trace.get("priority") != "must" or trace.get("disposition") != "planned":
            if "acceptance_gate_ids" in trace:
                _add(
                    errors,
                    f"plan.traces[{trace_id}].acceptance_gate_ids",
                    "feature gates are supported only on planned must traces",
                )
            continue
        related_tests = trace_tests.get(trace_id, set())
        gates = trace.get("acceptance_gate_ids", [])
        expected_tests = (
            feature_test_authority.get(trace_id, set())
            if feature_test_authority is not None
            else related_tests
        )
        if require_feature_gates and is_feature and not gates:
            _add(
                errors,
                f"plan.traces[{trace_id}].acceptance_gate_ids",
                "a planned PRD must feature requires acceptance gates",
            )
        if feature_test_authority is not None and is_feature and not expected_tests:
            _add(
                errors,
                f"plan.traces[{trace_id}].acceptance_gate_ids",
                "canonical PRD authority has no Required-Yes TEST for the feature",
            )
        if require_feature_gates and trace_id in platform_tests and not gates:
            _add(
                errors,
                f"plan.traces[{trace_id}].acceptance_gate_ids",
                "a platform TEST obligation on a planned must trace requires a feature gate",
            )
        if not gates:
            if "acceptance_gate_ids" in trace:
                _strings(
                    errors,
                    f"plan.traces[{trace_id}].acceptance_gate_ids",
                    gates,
                    nonempty=True,
                )
            continue
        gate_ids = _strings(
            errors,
            f"plan.traces[{trace_id}].acceptance_gate_ids",
            gates,
            nonempty=True,
        )
        final_gates = {
            gate.get("id"): gate
            for gate in plan.get("final_gates", []) if isinstance(gate, dict)
        }
        graph_nodes = {
            node.get("id"): node
            for node in plan.get("graph", {}).get("nodes", [])
            if isinstance(node, dict)
        }
        covered: set[str] = set()
        authoritative_gate_tests = (
            set().union(*feature_test_authority.values())
            if feature_test_authority
            else set()
        )
        for gate_id in gate_ids:
            gate = final_gates.get(gate_id)
            if gate is None:
                _add(
                    errors,
                    f"plan.traces[{trace_id}].acceptance_gate_ids",
                    f"unknown final gate {gate_id!r}",
                )
                continue
            annotated = gate.get("acceptance_test_ids", [])
            if not isinstance(annotated, list):
                continue
            gate_test_ids = {item for item in annotated if isinstance(item, str)}
            covered.update(gate_test_ids)
            if feature_test_authority is not None and not gate_test_ids <= authoritative_gate_tests:
                _add(
                    errors,
                    f"plan.final_gates[{gate_id}].acceptance_test_ids",
                    "feature gate annotations name non-required TEST IDs: "
                    + ", ".join(sorted(gate_test_ids - authoritative_gate_tests)),
                )
            cache = gate.get("cache")
            cache_reusable = isinstance(cache, dict) and cache.get("mode") == "session_exact"
            if "selection" in gate or cache_reusable:
                _add(
                    errors,
                    f"plan.final_gates[{gate_id}].acceptance_test_ids",
                    "an accepting feature gate must run fresh on every candidate",
                )
            matching_nodes = [
                node_id
                for node_id, node in graph_nodes.items()
                if node.get("kind") == "verifier"
                and node.get("ref") == gate_id
                and node.get("executor") in {"local_command", "harness_parent"}
            ]
            if len(matching_nodes) != 1:
                _add(
                    errors,
                    f"plan.traces[{trace_id}].acceptance_gate_ids",
                    f"final gate {gate_id!r} requires one deterministic graph node",
                )
        obligations = expected_tests or related_tests
        missing_obligations = sorted(obligations - covered)
        if missing_obligations:
            _add(
                errors,
                f"plan.traces[{trace_id}].acceptance_gate_ids",
                "accepting gates do not cover every canonical feature TEST "
                "obligation; missing " + ", ".join(missing_obligations),
            )
        for mission_id in sorted(carrying_missions.get(trace_id, set())):
            for gate_id in gate_ids:
                matching_nodes = [
                    node_id
                    for node_id, node in graph_nodes.items()
                    if isinstance(node, dict)
                    and node.get("kind") == "mission"
                    and node.get("ref") == mission_id
                ]
                gate_nodes = [
                    node_id
                    for node_id, node in graph_nodes.items()
                    if isinstance(node, dict)
                    and node.get("kind") == "verifier"
                    and node.get("ref") == gate_id
                ]
                if len(matching_nodes) != 1 or len(gate_nodes) != 1:
                    continue
                if not _dependency_path_exists(plan, matching_nodes[0], gate_nodes[0]):
                    _add(
                        errors,
                        f"plan.traces[{trace_id}].acceptance_gate_ids",
                        f"mission {mission_id!r} does not precede accepting gate "
                        f"{gate_id!r} through dependency edges",
                    )
    return errors


def validate_feature_acceptance(
    plan: dict[str, Any],
    *,
    feature_test_authority: dict[str, set[str]] | None = None,
) -> list[str]:
    """Validate declared feature-gate metadata without a platform contract."""

    return _feature_gate_errors(
        plan,
        set(),
        feature_test_authority,
        require_feature_gates=False,
    )


def _dependency_path_exists(plan: dict[str, Any], source_node: str, target_node: str) -> bool:
    dependencies, _node_missions = _dependency_adjacency(plan)
    return target_node in _reachable_nodes(dependencies, source_node)


def validate_platform_delivery(
    plan: dict[str, Any],
    contract: Any | None,
    *,
    required_test_ids: set[str] | None = None,
    feature_test_authority: dict[str, set[str]] | None = None,
) -> list[str]:
    """Validate the PLAN join against a canonical parsed architecture contract."""

    errors = platform_delivery_shape_errors(plan)
    if errors:
        return errors
    declared = plan.get("platform_delivery") is not None
    platform_stage_tests = (
        {test_id for stage in contract.stages for test_id in stage.test_ids}
        if contract is not None
        else set()
    )
    errors.extend(_feature_gate_errors(
        plan,
        platform_stage_tests,
        feature_test_authority,
        require_feature_gates=contract is not None or declared,
    ))
    if contract is None:
        if declared:
            _add(
                errors,
                "plan.platform_delivery",
                "requires an approved platform-delivery/1 architecture contract",
            )
        return errors
    if contract.mode == "not_required":
        if declared:
            _add(
                errors,
                "plan.platform_delivery",
                "a not_required platform contract cannot declare stage mappings",
            )
        return errors
    if not declared:
        _add(
            errors,
            "plan.platform_delivery",
            "platform-delivery/1 requires PLAN platform_delivery stage mappings",
        )
        return errors

    stages_by_id = {stage.id: stage for stage in contract.stages}
    raw_stages = plan["platform_delivery"]["stages"]
    stage_indexes: dict[str, int] = {}
    raw_stage_ids: set[str] = set()
    for index, stage in enumerate(raw_stages):
        stage_id = stage.get("id")
        if isinstance(stage_id, str) and stage_id in stage_indexes:
            _add(
                errors,
                f"plan.platform_delivery.stages[{index}].id",
                f"duplicate PLAN stage ID {stage_id!r}",
            )
        elif isinstance(stage_id, str):
            stage_indexes[stage_id] = index
            raw_stage_ids.add(stage_id)
    for stage_id in sorted(raw_stage_ids - set(stages_by_id)):
        _add(
            errors,
            "plan.platform_delivery.stages",
            f"unknown PLAN stage ID {stage_id!r}",
        )
    for stage_id in sorted(set(stages_by_id) - raw_stage_ids):
        _add(
            errors,
            "plan.platform_delivery.stages",
            f"architecture stage ID absent from PLAN: {stage_id!r}",
        )
    if len(stage_indexes) != len(raw_stages):
        _add(
            errors,
            "plan.platform_delivery.stages",
            "stage IDs must be unique before canonical-order validation",
        )
    stages = []
    if raw_stage_ids == set(stages_by_id) and len(stage_indexes) == len(raw_stages):
        for canonical_stage in sorted(contract.stages, key=lambda stage: stage.order):
            stages.append(raw_stages[stage_indexes[canonical_stage.id]])
    else:
        stages = list(raw_stages)
    missions = {item.get("id"): item for item in plan.get("missions", []) if isinstance(item, dict)}
    assigned: dict[str, int] = {}
    first_stage_mission_ids: list[str] = []
    for index, stage in enumerate(stages):
        stage_id = stage.get("id")
        canonical_stage = stages_by_id.get(stage_id)
        if canonical_stage is None:
            _add(
                errors,
                f"plan.platform_delivery.stages[{index}].id",
                f"unknown architecture stage {stage_id!r}",
            )
            continue
        for mission_id in stage.get("mission_ids", []):
            if mission_id not in missions:
                _add(
                    errors,
                    f"plan.platform_delivery.stages[{index}].mission_ids",
                    f"unknown mission {mission_id!r}",
                )
            elif mission_id in assigned:
                _add(
                    errors,
                    f"plan.platform_delivery.stages[{index}].mission_ids",
                    f"mission {mission_id!r} is already assigned to architecture stage "
                    f"{stages[assigned[mission_id]].get('id')!r}",
                )
            else:
                assigned[mission_id] = index
        if canonical_stage.order == 1:
            first_stage_mission_ids = list(stage.get("mission_ids", []))
        completion = stage.get("completion_mission_id")
        if completion not in missions:
            _add(
                errors,
                f"plan.platform_delivery.stages[{index}].completion_mission_id",
                f"unknown mission {completion!r}",
            )
        elif completion not in stage.get("mission_ids", []):
            _add(
                errors,
                f"plan.platform_delivery.stages[{index}].completion_mission_id",
                "must belong to the same stage mission_ids",
            )

    release_surfaces = {
        surface.get("release_surface")
        for surface in plan.get("ui_surfaces", [])
        if isinstance(surface, dict) and isinstance(surface.get("release_surface"), str)
    }
    release_surfaces.discard(None)
    stage_surfaces = {
        surface
        for contract_stage in contract.stages
        for surface in contract_stage.surfaces
    }
    missing_surfaces = sorted(release_surfaces - stage_surfaces)
    if missing_surfaces:
        _add(
            errors,
            "plan.ui_surfaces",
            "release surfaces absent from platform stages: " + ", ".join(missing_surfaces),
        )

    surface_stages = {
        surface: position
        for position, stage in enumerate(contract.stages)
        for surface in stage.surfaces
    }
    effective_traces: dict[str, set[str]] = {}
    for mission_id, mission in missions.items():
        mission_traces = {
            trace_id
            for trace_id in mission.get("trace_ids", [])
            if isinstance(trace_id, str)
        }
        for task in mission.get("tasks", []):
            if not isinstance(task, dict) or task.get("replaced_by"):
                continue
            mission_traces.update(
                trace_id
                for trace_id in task.get("trace_ids", [])
                if isinstance(trace_id, str)
            )
        effective_traces[mission_id] = mission_traces
    for index, surface in enumerate(plan.get("ui_surfaces", [])):
        if not isinstance(surface, dict):
            continue
        release_surface = surface.get("release_surface")
        if release_surface not in surface_stages:
            continue
        ui_ids = {
            value
            for value in (surface.get("id"), *surface.get("trace_ids", []))
            if isinstance(value, str) and value.startswith("UI-")
        }
        owners = [
            mission_id
            for mission_id, trace_ids in effective_traces.items()
            if ui_ids and ui_ids & trace_ids
        ]
        if not owners:
            _add(
                errors,
                f"plan.ui_surfaces[{index}]",
                "explicit UI IDs have no mission or effective-task trace owner",
            )
            continue
        wrong_owners = [
            mission_id
            for mission_id in owners
            if mission_id not in assigned
            or assigned[mission_id] != surface_stages[release_surface]
        ]
        if wrong_owners:
            owner_stages = sorted(
                {
                    stages[assigned[mission_id]].get("id")
                    for mission_id in wrong_owners
                    if mission_id in assigned
                }
            )
            _add(
                errors,
                f"plan.ui_surfaces[{index}]",
                "UI owners are absent from or assigned to the wrong platform stage: "
                + ", ".join(sorted(map(str, wrong_owners)))
                + (f" ({', '.join(map(str, owner_stages))})" if owner_stages else ""),
            )
        if len({assigned.get(mission_id) for mission_id in owners}) > 1:
            _add(
                errors,
                f"plan.ui_surfaces[{index}]",
                "UI IDs cross platform stages: " + ", ".join(sorted(owners)),
            )

    dependencies, node_missions = _dependency_adjacency(plan)
    missing_foundation = [
        arch_id
        for arch_id in contract.shared_arch_ids
        if not any(
            arch_id in missions[mission_id].get("trace_ids", [])
            for mission_id in first_stage_mission_ids
            if mission_id in missions
        )
    ]
    if missing_foundation:
        _add(
            errors,
            "plan.platform_delivery.stages[0].mission_ids",
            "shared ARCH foundations missing from the first stage: "
            + ", ".join(sorted(missing_foundation)),
        )
    previous_completion: str | None = None
    for index, stage in enumerate(stages):
        canonical_stage = stages_by_id.get(stage.get("id"))
        if canonical_stage is None:
            continue
        stage_missions = list(stage.get("mission_ids", []))
        completion = stage.get("completion_mission_id")
        contributors = [
            mission_id
            for mission_id in stage_missions
            if mission_id != completion and mission_id in missions
        ]
        for mission_id in contributors:
            reached = _reaches_mission(dependencies, node_missions, mission_id, {completion})
            if not reached:
                _add(
                    errors,
                    f"plan.platform_delivery.stages[{index}].completion_mission_id",
                    f"mission {mission_id!r} does not precede completion "
                    f"{completion!r} through dependency edges",
                )
        upstream_tests = {
            test_id
            for earlier_stage in contract.stages
            if earlier_stage.order <= canonical_stage.order
            for test_id in earlier_stage.test_ids
        }
        selected_verifiers = [
            verifier
            for verifier_id in stage.get("integration_verifier_ids", [])
            for verifier in missions.get(completion, {}).get("integration_verifiers", [])
            if isinstance(verifier, dict) and verifier.get("id") == verifier_id
        ]
        known_selected_ids = {verifier.get("id") for verifier in selected_verifiers}
        unknown_selected = sorted(set(stage.get("integration_verifier_ids", [])) - known_selected_ids)
        if unknown_selected:
            _add(
                errors,
                f"plan.platform_delivery.stages[{index}].integration_verifier_ids",
                "completion integration verifier IDs not owned by completion mission "
                f"{completion!r}: " + ", ".join(unknown_selected),
            )
        selected_tests = {
            test_id
            for verifier in selected_verifiers
            for test_id in verifier.get("acceptance_test_ids", [])
            if isinstance(test_id, str)
        }
        missing_upstream = sorted(upstream_tests - selected_tests)
        if selected_verifiers and missing_upstream:
            _add(
                errors,
                f"plan.platform_delivery.stages[{index}].integration_verifier_ids",
                "completion integration verifier annotations must cover the full upstream "
                f"platform TEST set; missing {', '.join(missing_upstream)}",
            )
        if required_test_ids is not None:
            unauthoritative = sorted(selected_tests - required_test_ids)
        else:
            unauthoritative = []
        if unauthoritative:
            _add(
                errors,
                f"plan.platform_delivery.stages[{index}].integration_verifier_ids",
                "completion integration annotations name non-required TEST IDs: "
                + ", ".join(unauthoritative),
            )
        for verifier in selected_verifiers:
            verifier_path = (
                f"plan.missions[{completion}].integration_verifiers[{verifier.get('id')}]"
            )
            cache = verifier.get("cache")
            cache_reusable = isinstance(cache, dict) and cache.get("mode") == "session_exact"
            if "selection" in verifier or cache_reusable:
                _add(
                    errors,
                    verifier_path,
                    "a platform completion integration verifier must run fresh",
                )
            if not verifier.get("acceptance_test_ids"):
                _add(
                    errors,
                    verifier_path,
                    "requires nonempty acceptance_test_ids",
                )
        if previous_completion is not None:
            for mission_id in stage_missions:
                reached = _reaches_mission(
                    dependencies,
                    node_missions,
                    previous_completion,
                    {mission_id},
                )
                if not reached:
                    _add(
                        errors,
                        f"plan.platform_delivery.stages[{index}].mission_ids",
                        f"mission {mission_id!r} is not reachable from previous platform "
                        f"completion {previous_completion!r} through dependency edges",
                    )
        previous_completion = completion

    platform_tests = {test_id for stage in contract.stages for test_id in stage.test_ids}
    final_tests, annotated_tests, annotation_errors = _annotated_verifier_tests(plan)
    errors.extend(annotation_errors)
    missing_tests = sorted(platform_tests - final_tests)
    if missing_tests:
        _add(
            errors,
            "plan.final_gates",
            "platform TEST obligations not covered by final or completion gates: "
            + ", ".join(missing_tests),
        )
    if required_test_ids is not None:
        unauthoritative = sorted(annotated_tests - required_test_ids)
    else:
        unauthoritative = []
    if unauthoritative:
        _add(
            errors,
            "plan.final_gates.verifier.acceptance_test_ids",
            "acceptance annotations name non-required TEST IDs: "
            + ", ".join(unauthoritative),
        )
    return errors

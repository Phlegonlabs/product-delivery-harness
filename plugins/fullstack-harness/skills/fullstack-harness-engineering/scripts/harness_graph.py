#!/usr/bin/env python3
"""PLAN-v4 typed graph validation and RUN graph-state consistency checks."""

from __future__ import annotations

from typing import Any

from harness_core import (
    _add,
    _is_int,
    _keys,
    _nonempty_string,
    _optional_string,
    _strings,
    _validate_scope_list,
    is_safe_model_token,
)
from harness_schema import (
    AUTHORIZATION_KEYS,
    GRAPH_EDGE_PHASES,
    GRAPH_EXECUTORS,
    GRAPH_NODE_KINDS,
    GRAPH_NODE_PHASES,
    GRAPH_OUTCOMES,
    ID_RE,
    RUNTIME_PROVIDERS,
    RUNTIME_REASONING_EFFORTS,
    RUNTIME_REVIEW_TYPES,
    TARGET_RE,
    action_target_kind_allowed,
    action_target_kind_description,
)


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


def _validate_graph(
    errors: list[str],
    value: Any,
    missions: dict[str, dict[str, Any]],
    verifier_ids: set[str],
    *,
    require_bounded_review_repair: bool = False,
) -> None:
    path = "plan.graph"
    authorization_actions = AUTHORIZATION_KEYS
    if not _keys(errors, path, value, {"entry_nodes", "nodes", "edges"}):
        return

    entry_nodes = _strings(errors, f"{path}.entry_nodes", value["entry_nodes"], nonempty=True)
    nodes: dict[str, dict[str, Any]] = {}
    mission_nodes: dict[str, str] = {}
    node_keys = {
        "id",
        "kind",
        "ref",
        "executor",
        "allowed_outcomes",
        "max_attempts",
        "runtime",
    }
    if not isinstance(value["nodes"], list) or not value["nodes"]:
        _add(errors, f"{path}.nodes", "must be a non-empty list")
    else:
        for index, node in enumerate(value["nodes"]):
            node_path = f"{path}.nodes[{index}]"
            if not _keys(errors, node_path, node, node_keys, {"review", "target"}):
                continue
            node_id = node["id"]
            if not _nonempty_string(node_id) or not ID_RE.fullmatch(node_id):
                _add(errors, f"{node_path}.id", "must be a flat uppercase identifier")
                continue
            if node_id in nodes:
                _add(errors, f"{node_path}.id", "must be unique")
                continue
            nodes[node_id] = node
            kind = node["kind"]
            if not isinstance(kind, str) or kind not in GRAPH_NODE_KINDS:
                _add(errors, f"{node_path}.kind", "has an unsupported value")
                kind = None
            executor = node["executor"]
            if not isinstance(executor, str) or executor not in GRAPH_EXECUTORS:
                _add(errors, f"{node_path}.executor", "has an unsupported value")
                executor = None
            outcomes = _strings(
                errors,
                f"{node_path}.allowed_outcomes",
                node["allowed_outcomes"],
                nonempty=True,
            )
            unknown_outcomes = sorted(set(outcomes) - GRAPH_OUTCOMES)
            if unknown_outcomes:
                _add(
                    errors,
                    f"{node_path}.allowed_outcomes",
                    f"unsupported outcomes: {', '.join(unknown_outcomes)}",
                )
            if not _is_int(node["max_attempts"]) or not 1 <= node["max_attempts"] <= 3:
                _add(errors, f"{node_path}.max_attempts", "must be an integer from 1 to 3")
            if executor in {"runtime_worker", "harness_parent"} and not set(outcomes).intersection(
                {"retryable_failure", "blocked"}
            ):
                _add(
                    errors,
                    f"{node_path}.allowed_outcomes",
                    "runtime or parent execution requires retryable_failure or blocked for failure",
                )

            ref = node["ref"]
            valid_ref = _nonempty_string(ref)
            if not valid_ref:
                _add(errors, f"{node_path}.ref", "must be a non-empty string")
            if kind == "mission":
                if valid_ref and ref not in missions:
                    _add(errors, f"{node_path}.ref", "must reference a PLAN mission")
                elif valid_ref and ref in mission_nodes:
                    _add(errors, f"{node_path}.ref", "each mission must have exactly one graph node")
                elif valid_ref:
                    mission_nodes[ref] = node_id
                if executor not in {"runtime_worker", "harness_parent"}:
                    _add(errors, f"{node_path}.executor", "mission requires runtime_worker or harness_parent")
            elif kind == "verifier":
                if valid_ref and ref not in verifier_ids:
                    _add(errors, f"{node_path}.ref", "must reference a declared verifier")
                if executor not in {"runtime_worker", "harness_parent", "local_command"}:
                    _add(errors, f"{node_path}.executor", "verifier has an incompatible executor")
                review = node.get("review")
                if executor == "runtime_worker":
                    review_path = f"{node_path}.review"
                    if _keys(
                        errors,
                        review_path,
                        review,
                        {"type", "mission_ids", "scope", "required_evidence"},
                    ):
                        if not isinstance(review["type"], str) or review["type"] not in RUNTIME_REVIEW_TYPES:
                            _add(errors, f"{review_path}.type", "has an unsupported review type")
                        review_missions = _strings(
                            errors,
                            f"{review_path}.mission_ids",
                            review["mission_ids"],
                            nonempty=True,
                        )
                        for mission_id in review_missions:
                            if mission_id not in missions:
                                _add(
                                    errors,
                                    f"{review_path}.mission_ids",
                                    f"unknown mission {mission_id!r}",
                                )
                        _validate_scope_list(
                            errors,
                            f"{review_path}.scope",
                            review["scope"],
                            nonempty=True,
                        )
                        _strings(
                            errors,
                            f"{review_path}.required_evidence",
                            review["required_evidence"],
                            nonempty=True,
                        )
                elif review is not None:
                    _add(
                        errors,
                        f"{node_path}.review",
                        "must be omitted unless a verifier uses runtime_worker",
                    )
            elif kind == "approval" and executor != "human":
                _add(errors, f"{node_path}.executor", "approval requires human")
            elif kind == "external_wait" and executor != "external_system":
                _add(errors, f"{node_path}.executor", "external_wait requires external_system")
            elif kind == "lifecycle":
                if executor != "harness_parent":
                    _add(errors, f"{node_path}.executor", "lifecycle requires harness_parent")
                if valid_ref and ref not in authorization_actions:
                    _add(errors, f"{node_path}.ref", "must reference an authorization action")
                # `target` is optional so PLANs written before this field existed
                # stay valid (they keep resolving to the "*" default, exactly as
                # before). When present it must be the exact authorization
                # target select_ready_nodes.py checks the RUN ledger against —
                # schema v10 rejects "*" scope targets for every one of these
                # actions, so a lifecycle node with no target is permanently
                # unauthorized there; declaring one is how a PLAN makes the node
                # reachable.
                target = node.get("target")
                if target is not None and (
                    not _nonempty_string(target)
                    or target == "*"
                    or TARGET_RE.fullmatch(target) is None
                ):
                    _add(
                        errors,
                        f"{node_path}.target",
                        "must be null or an exact non-wildcard authorization target",
                    )
                elif (
                    target is not None
                    and valid_ref
                    and ref in authorization_actions
                    and not action_target_kind_allowed(ref, target)
                ):
                    _add(
                        errors,
                        f"{node_path}.target",
                        f"{ref} target kind must be "
                        f"{action_target_kind_description(ref)}",
                    )
            if kind != "verifier" and node.get("review") is not None:
                _add(
                    errors,
                    f"{node_path}.review",
                    "must be omitted unless a verifier uses runtime_worker",
                )
            if kind != "lifecycle" and node.get("target") is not None:
                _add(
                    errors,
                    f"{node_path}.target",
                    "must be omitted unless the node is lifecycle",
                )

            runtime = node["runtime"]
            if executor == "runtime_worker":
                runtime_path = f"{node_path}.runtime"
                if _keys(
                    errors,
                    runtime_path,
                    runtime,
                    {"preferred_provider", "allowed_providers"},
                    {"provider_options"},
                ):
                    # allowed_providers is intentionally schema-valid even when it excludes
                    # whatever provider happens to host the current RUN: a PLAN may target a
                    # host chosen later. No further "can this ever run anywhere" check is
                    # added beyond nonempty + RUNTIME_PROVIDERS membership (just below):
                    # every member of RUNTIME_PROVIDERS has a native driver in
                    # RUNTIME_DRIVER_PRIORITY, so there is no provider combination that is
                    # structurally unrunnable on every host. A host/provider mismatch is a
                    # RUN-time "runtime_unavailable" outcome (see select_ready_nodes.py),
                    # not a PLAN authoring error.
                    providers = _strings(
                        errors,
                        f"{runtime_path}.allowed_providers",
                        runtime["allowed_providers"],
                        nonempty=True,
                    )
                    unknown_providers = sorted(set(providers) - RUNTIME_PROVIDERS)
                    if unknown_providers:
                        _add(
                            errors,
                            f"{runtime_path}.allowed_providers",
                            f"unsupported providers: {', '.join(unknown_providers)}",
                        )
                    preferred = runtime["preferred_provider"]
                    if preferred is not None and preferred not in providers:
                        _add(
                            errors,
                            f"{runtime_path}.preferred_provider",
                            "must be null or one of allowed_providers",
                        )
                    provider_options = runtime.get("provider_options", {})
                    if not isinstance(provider_options, dict):
                        _add(errors, f"{runtime_path}.provider_options", "must be an object")
                    else:
                        unknown_option_providers = sorted(set(provider_options) - set(providers))
                        if unknown_option_providers:
                            _add(
                                errors,
                                f"{runtime_path}.provider_options",
                                "contains providers not present in allowed_providers: "
                                + ", ".join(unknown_option_providers),
                            )
                        for provider, options in provider_options.items():
                            option_path = f"{runtime_path}.provider_options.{provider}"
                            if not _keys(
                                errors,
                                option_path,
                                options,
                                {"model", "reasoning_effort"},
                            ):
                                continue
                            model = options["model"]
                            if model is not None and not is_safe_model_token(model):
                                _add(errors, f"{option_path}.model", "must be null or a safe model token")
                            effort = options["reasoning_effort"]
                            if effort is not None and effort not in RUNTIME_REASONING_EFFORTS:
                                _add(
                                    errors,
                                    f"{option_path}.reasoning_effort",
                                    "must be null or a supported reasoning effort",
                                )
                            if provider not in {"codex", "claude_code"} and effort is not None:
                                _add(
                                    errors,
                                    f"{option_path}.reasoning_effort",
                                    "must be null unless the provider supports selectable effort",
                                )
            elif runtime is not None:
                _add(errors, f"{node_path}.runtime", "must be null unless executor is runtime_worker")

    for entry in entry_nodes:
        if entry not in nodes:
            _add(errors, f"{path}.entry_nodes", f"unknown node {entry!r}")
    if set(mission_nodes) != set(missions):
        missing = sorted(set(missions) - set(mission_nodes))
        if missing:
            _add(errors, f"{path}.nodes", f"missing mission nodes: {', '.join(missing)}")

    edges: dict[str, dict[str, Any]] = {}
    dependency_map = {node_id: [] for node_id in nodes}
    combined_map = {node_id: [] for node_id in nodes}
    outgoing = {node_id: [] for node_id in nodes}
    incoming = {node_id: [] for node_id in nodes}
    edge_keys = {"id", "kind", "from", "to", "on_outcomes", "max_traversals"}
    if not isinstance(value["edges"], list):
        _add(errors, f"{path}.edges", "must be a list")
        return
    for index, edge in enumerate(value["edges"]):
        edge_path = f"{path}.edges[{index}]"
        if not _keys(errors, edge_path, edge, edge_keys):
            continue
        edge_id = edge["id"]
        valid_edge_id = _nonempty_string(edge_id) and ID_RE.fullmatch(edge_id) is not None
        if not valid_edge_id:
            _add(errors, f"{edge_path}.id", "must be a flat uppercase identifier")
        elif edge_id in edges:
            _add(errors, f"{edge_path}.id", "must be unique")
            valid_edge_id = False
        else:
            edges[edge_id] = edge
        source = edge["from"]
        target = edge["to"]
        valid_source = _nonempty_string(source)
        valid_target = _nonempty_string(target)
        if not valid_source:
            _add(errors, f"{edge_path}.from", "must be a non-empty string")
        elif source not in nodes:
            _add(errors, f"{edge_path}.from", "references an unknown node")
        if not valid_target:
            _add(errors, f"{edge_path}.to", "must be a non-empty string")
        elif target not in nodes:
            _add(errors, f"{edge_path}.to", "references an unknown node")
        if valid_source and valid_target and source == target:
            _add(errors, edge_path, "self edges are forbidden")
        outcomes = _strings(errors, f"{edge_path}.on_outcomes", edge["on_outcomes"], nonempty=True)
        if valid_source and source in nodes:
            invalid = sorted(set(outcomes) - set(nodes[source].get("allowed_outcomes", [])))
            if invalid:
                _add(
                    errors,
                    f"{edge_path}.on_outcomes",
                    f"source node does not declare: {', '.join(invalid)}",
                )
        if edge["kind"] == "dependency":
            if outcomes != ["pass"]:
                _add(errors, f"{edge_path}.on_outcomes", "dependency requires exactly ['pass']")
            if edge["max_traversals"] is not None:
                _add(errors, f"{edge_path}.max_traversals", "dependency must be null")
            if valid_source and valid_target and source in nodes and target in nodes:
                dependency_map[target].append(source)
        elif edge["kind"] == "route":
            bound = edge["max_traversals"]
            if bound is not None and (not _is_int(bound) or not 1 <= bound <= 3):
                _add(errors, f"{edge_path}.max_traversals", "must be null or an integer from 1 to 3")
        else:
            _add(errors, f"{edge_path}.kind", "must be dependency or route")
        if valid_source and valid_target and source in nodes and target in nodes:
            combined_map[target].append(source)
            outgoing[source].append(target)
            incoming[target].append(source)

    if require_bounded_review_repair:
        for node_id, node in nodes.items():
            if (
                node.get("kind") != "verifier"
                or node.get("executor") != "runtime_worker"
                or not isinstance(node.get("review"), dict)
                or "fix_required" not in node.get("allowed_outcomes", [])
            ):
                continue
            fix_routes = [
                edge
                for edge in edges.values()
                if edge.get("kind") == "route"
                and edge.get("from") == node_id
                and "fix_required" in edge.get("on_outcomes", [])
            ]
            reviewed_missions = set(node["review"].get("mission_ids", []))
            dependency_missions = {
                nodes[source].get("ref")
                for source in dependency_map[node_id]
                if nodes[source].get("kind") == "mission"
                and _nonempty_string(nodes[source].get("ref"))
            }
            same_mission_correction = (
                len(reviewed_missions) == 1
                and reviewed_missions == dependency_missions
                and _is_int(node.get("max_attempts"))
                and node["max_attempts"] >= 2
            )
            if not fix_routes:
                if not same_mission_correction:
                    _add(
                        errors,
                        f"{path}.nodes.{node_id}",
                        "runtime review with fix_required requires a bounded repair route or direct mission dependencies for same-worktree correction",
                    )
            else:
                bounded_fix_routes = [
                    edge for edge in fix_routes if _is_int(edge.get("max_traversals"))
                ]
                if len(bounded_fix_routes) != len(fix_routes):
                    _add(
                        errors,
                        f"{path}.nodes.{node_id}",
                        "fix_required repair routes require an explicit traversal bound",
                    )
                repair_targets = {edge.get("to") for edge in bounded_fix_routes}
                direct_rereview = any(
                    edge.get("kind") == "route"
                    and edge.get("from") in repair_targets
                    and edge.get("to") == node_id
                    and "pass" in edge.get("on_outcomes", [])
                    and _is_int(edge.get("max_traversals"))
                    for edge in edges.values()
                )
                reviewed_rereview = any(
                    dependency.get("kind") == "dependency"
                    and dependency.get("from") in repair_targets
                    and len(repair_targets) == 1
                    and isinstance(nodes.get(dependency.get("to")), dict)
                    and nodes[dependency["to"]].get("kind") == "verifier"
                    and isinstance(nodes[dependency["to"]].get("review"), dict)
                    and len(
                        nodes[dependency["to"]]["review"].get(
                            "mission_ids", []
                        )
                    )
                    == 1
                    and set(
                        nodes[dependency["to"]]["review"].get(
                            "mission_ids", []
                        )
                    )
                    == {
                        nodes[repair_target].get("ref")
                        for repair_target in repair_targets
                        if isinstance(nodes.get(repair_target), dict)
                        and nodes[repair_target].get("kind") == "mission"
                    }
                    and any(
                        edge.get("kind") == "route"
                        and edge.get("from") == dependency.get("to")
                        and edge.get("to") == node_id
                        and "pass" in edge.get("on_outcomes", [])
                        and _is_int(edge.get("max_traversals"))
                        for edge in edges.values()
                    )
                    for dependency in edges.values()
                )
                has_rereview = direct_rereview or reviewed_rereview
                if not has_rereview:
                    _add(
                        errors,
                        f"{path}.nodes.{node_id}",
                        "repair route must have a bounded pass route back to the review",
                    )
            direct_final_gate = any(
                edge.get("kind") == "route"
                and edge.get("from") == node_id
                and "pass" in edge.get("on_outcomes", [])
                and isinstance(nodes.get(edge.get("to")), dict)
                and nodes[edge["to"]].get("kind") == "verifier"
                and nodes[edge["to"]].get("executor") in {"harness_parent", "local_command"}
                for edge in edges.values()
            )
            review_then_final_gate = any(
                edge.get("kind") == "route"
                and edge.get("from") == node_id
                and "pass" in edge.get("on_outcomes", [])
                and _is_int(edge.get("max_traversals"))
                and isinstance(nodes.get(edge.get("to")), dict)
                and nodes[edge["to"]].get("kind") == "verifier"
                and nodes[edge["to"]].get("executor") == "runtime_worker"
                and any(
                    next_edge.get("kind") == "route"
                    and next_edge.get("from") == edge.get("to")
                    and "pass" in next_edge.get("on_outcomes", [])
                    and isinstance(nodes.get(next_edge.get("to")), dict)
                    and nodes[next_edge["to"]].get("kind") == "verifier"
                    and nodes[next_edge["to"]].get("executor")
                    in {"harness_parent", "local_command"}
                    for next_edge in edges.values()
                )
                for edge in edges.values()
            )
            has_final_gate = direct_final_gate or review_then_final_gate
            if not has_final_gate:
                _add(
                    errors,
                    f"{path}.nodes.{node_id}",
                    "review pass requires an outgoing route to a deterministic final gate",
                )

    cyclic_dependencies = _cycle_nodes(dependency_map)
    if cyclic_dependencies:
        _add(
            errors,
            f"{path}.edges",
            f"dependency cycle includes {', '.join(sorted(cyclic_dependencies))}",
        )

    cyclic_nodes = _cycle_nodes(combined_map)
    if cyclic_nodes:
        for edge_id, edge in edges.items():
            if (
                edge.get("kind") == "route"
                and edge.get("from") in cyclic_nodes
                and edge.get("to") in cyclic_nodes
                and edge.get("max_traversals") is None
            ):
                _add(
                    errors,
                    f"{path}.edges.{edge_id}.max_traversals",
                    "route cycles require an explicit traversal bound",
                )
        if not any(
            source in cyclic_nodes and target not in cyclic_nodes
            for source, targets in outgoing.items()
            for target in targets
        ):
            _add(errors, f"{path}.edges", "route cycles require an exit edge")

    roots = {node_id for node_id, sources in incoming.items() if not sources}
    if set(entry_nodes) != roots:
        _add(errors, f"{path}.entry_nodes", "must exactly match graph root nodes")
    reachable = set(entry_nodes)
    pending = list(entry_nodes)
    while pending:
        source = pending.pop()
        for target in outgoing.get(source, []):
            if target not in reachable:
                reachable.add(target)
                pending.append(target)
    unreachable = sorted(set(nodes) - reachable)
    if unreachable:
        _add(errors, f"{path}.nodes", f"unreachable nodes: {', '.join(unreachable)}")


def _validate_graph_state(
    errors: list[str], plan: dict[str, Any], run: dict[str, Any]
) -> None:
    path = "run.graph_state"
    value = run.get("graph_state")
    if not _keys(errors, path, value, {"graph_revision", "node_states", "edge_states"}):
        return
    if value["graph_revision"] != plan.get("revision"):
        _add(errors, f"{path}.graph_revision", "must match PLAN revision")

    graph = plan.get("graph", {})
    graph_nodes = {
        node["id"]: node
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    graph_edges = {
        edge["id"]: edge
        for edge in graph.get("edges", [])
        if isinstance(edge, dict) and isinstance(edge.get("id"), str)
    }
    raw_mission_states = run.get("mission_states")
    mission_states = (
        raw_mission_states if isinstance(raw_mission_states, dict) else {}
    )

    node_states = value["node_states"]
    node_state_keys = {
        "phase",
        "attempts",
        "last_attempt_id",
        "last_outcome",
        "bound_worker_id",
        "blockers",
    }
    if not isinstance(node_states, dict):
        _add(errors, f"{path}.node_states", "must be an object")
    else:
        if set(node_states) != set(graph_nodes):
            _add(errors, f"{path}.node_states", "keys must exactly match PLAN graph nodes")
        for node_id, state in node_states.items():
            state_path = f"{path}.node_states.{node_id}"
            if node_id not in graph_nodes or not _keys(errors, state_path, state, node_state_keys):
                continue
            node = graph_nodes[node_id]
            phase = state["phase"]
            valid_phase = isinstance(phase, str) and phase in GRAPH_NODE_PHASES
            if not valid_phase:
                _add(errors, f"{state_path}.phase", "has an unsupported value")
            attempts = state["attempts"]
            if not _is_int(attempts) or attempts < 0:
                _add(errors, f"{state_path}.attempts", "must be a non-negative integer")
            elif attempts > node.get("max_attempts", 0):
                _add(errors, f"{state_path}.attempts", "exceeds PLAN max_attempts")
            for key in ("last_attempt_id", "bound_worker_id"):
                _optional_string(errors, f"{state_path}.{key}", state[key])
            outcome = state["last_outcome"]
            if outcome is not None and (
                not isinstance(outcome, str)
                or outcome not in node.get("allowed_outcomes", [])
            ):
                _add(errors, f"{state_path}.last_outcome", "is not declared by the PLAN node")
            blockers = _strings(errors, f"{state_path}.blockers", state["blockers"])
            if valid_phase and phase in {"succeeded", "failed", "blocked"} and (
                not _nonempty_string(state["last_attempt_id"])
                or outcome is None
                or attempts < 1
            ):
                _add(errors, state_path, "terminal node requires attempt identity, outcome, and attempts")
            if phase == "blocked" and not blockers:
                _add(errors, f"{state_path}.blockers", "blocked node requires a blocker")
            if phase == "running" and node.get("executor") == "runtime_worker" and not _nonempty_string(
                state["bound_worker_id"]
            ):
                _add(errors, f"{state_path}.bound_worker_id", "is required for a running runtime worker")

            if node.get("kind") == "mission" and node.get("ref") in mission_states:
                mission_state = mission_states[node["ref"]]
                mission_phase = mission_state.get("phase") if isinstance(mission_state, dict) else None
                if phase == "succeeded" and (
                    outcome != "pass"
                    or mission_phase != "integrated"
                    or mission_state.get("integration_gate") != "PASS"
                ):
                    _add(errors, state_path, "succeeded mission node requires integrated mission PASS")
                if mission_phase == "integrated" and (
                    phase != "succeeded" or outcome != "pass"
                ):
                    _add(errors, state_path, "integrated mission must be a succeeded pass node")
                if phase == "running" and mission_phase not in {
                    "leased",
                    "worker_running",
                    "worker_passed",
                    "integrating",
                }:
                    _add(errors, state_path, "running mission node does not match mission phase")
                if phase == "ready" and mission_phase not in {"queued", "ready"}:
                    _add(errors, state_path, "ready mission node does not match mission phase")

    edge_states = value["edge_states"]
    edge_state_keys = {"status", "traversals", "source_attempt_id"}
    if not isinstance(edge_states, dict):
        _add(errors, f"{path}.edge_states", "must be an object")
    else:
        if set(edge_states) != set(graph_edges):
            _add(errors, f"{path}.edge_states", "keys must exactly match PLAN graph edges")
        for edge_id, state in edge_states.items():
            state_path = f"{path}.edge_states.{edge_id}"
            if edge_id not in graph_edges or not _keys(errors, state_path, state, edge_state_keys):
                continue
            status = state["status"]
            if not isinstance(status, str) or status not in GRAPH_EDGE_PHASES:
                _add(errors, f"{state_path}.status", "has an unsupported value")
            traversals = state["traversals"]
            if not _is_int(traversals) or traversals < 0:
                _add(errors, f"{state_path}.traversals", "must be a non-negative integer")
            bound = graph_edges[edge_id].get("max_traversals")
            if _is_int(traversals) and _is_int(bound) and traversals > bound:
                _add(errors, f"{state_path}.traversals", "exceeds PLAN max_traversals")
            _optional_string(errors, f"{state_path}.source_attempt_id", state["source_attempt_id"])
            if state["status"] == "traversed" and (
                not _is_int(traversals)
                or traversals < 1
                or not _nonempty_string(state["source_attempt_id"])
            ):
                _add(errors, state_path, "traversed edge requires traversal count and source attempt")
            # An edge declares which source outcomes may traverse it. Without
            # this check a `pass`-only edge can be recorded as traversed from a
            # fix_required attempt, which is how a run routes straight past the
            # review gate that just rejected it.
            source_state = (
                node_states.get(graph_edges[edge_id].get("from"))
                if isinstance(node_states, dict)
                else None
            )
            declared_outcomes = graph_edges[edge_id].get("on_outcomes")
            if (
                state["status"] == "traversed"
                and isinstance(source_state, dict)
                and isinstance(declared_outcomes, list)
                and _nonempty_string(state["source_attempt_id"])
                and source_state.get("last_attempt_id") == state["source_attempt_id"]
                and source_state.get("last_outcome") not in declared_outcomes
            ):
                _add(
                    errors,
                    f"{state_path}.source_attempt_id",
                    "traversed edge requires a source outcome the edge declares",
                )

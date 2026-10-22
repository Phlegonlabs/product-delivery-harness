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
    is_full_sha,
    is_safe_model_token,
    scope_contains,
    scope_overlap,
    validate_scope_claim,
)
from harness_schema import (
    AUTHORIZATION_KEYS,
    EXACT_TARGET_LIFECYCLE_ACTIONS,
    GRAPH_EDGE_PHASES,
    GRAPH_EXECUTORS,
    GRAPH_NODE_KINDS,
    GRAPH_NODE_PHASES,
    GRAPH_OUTCOMES,
    ID_RE,
    is_valid_provider_id,
    REVIEW_LENS_ORDER,
    REVIEWER_TOOL_KEYS,
    RUNTIME_REASONING_EFFORTS,
    RUNTIME_REVIEW_TYPES,
    TARGET_RE,
    action_target_kind_allowed,
    action_target_kind_description,
    review_lenses,
    review_policy,
)


def validate_cleanup_lifecycle_targets(errors: list[str], graph: Any) -> None:
    """A cleanup lifecycle node must name the exact task, worktree, or branch.

    Only validate_run calls this, for RUNs that require Harness 0.55.0 or
    later, so PLANs of older RUNs and their archives keep validating.
    """

    nodes = graph.get("nodes") if isinstance(graph, dict) else None
    if not isinstance(nodes, list):
        return
    for index, node in enumerate(nodes):
        if (
            isinstance(node, dict)
            and node.get("kind") == "lifecycle"
            and isinstance(node.get("ref"), str)
            and node["ref"] in EXACT_TARGET_LIFECYCLE_ACTIONS
            and node.get("target") is None
        ):
            _add(
                errors,
                f"plan.graph.nodes[{index}].target",
                f"{node['ref']} requires an exact non-wildcard authorization target",
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
    require_review_lineage: bool = False,
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
                    if (
                        require_bounded_review_repair
                        and _is_int(node["max_attempts"])
                        and node["max_attempts"] > 2
                    ):
                        _add(
                            errors,
                            f"{node_path}.max_attempts",
                            "runtime review allows at most 2 attempts",
                        )
                    review_path = f"{node_path}.review"
                    if _keys(
                        errors,
                        review_path,
                        review,
                        {
                            "type",
                            "mission_ids",
                            "scope",
                            "required_evidence",
                            *( {"lineage_id"} if require_review_lineage else set() ),
                        },
                        {
                            "stage",
                            "lenses",
                            "required_tools",
                            *(set() if require_review_lineage else {"lineage_id"}),
                        },
                    ):
                        lineage_id = review.get("lineage_id")
                        if lineage_id is not None and (
                            not _nonempty_string(lineage_id)
                            or not ID_RE.fullmatch(lineage_id)
                        ):
                            _add(
                                errors,
                                f"{review_path}.lineage_id",
                                "must be a flat uppercase identifier",
                            )
                        review_stage = review.get("stage", "preintegration")
                        if not isinstance(review_stage, str) or review_stage not in {
                            "preintegration",
                            "integration",
                        }:
                            _add(
                                errors,
                                f"{review_path}.stage",
                                "must be preintegration or integration",
                            )
                        if not isinstance(review["type"], str) or review["type"] not in RUNTIME_REVIEW_TYPES:
                            _add(errors, f"{review_path}.type", "has an unsupported review type")
                        if "lenses" in review:
                            lenses = _strings(
                                errors,
                                f"{review_path}.lenses",
                                review["lenses"],
                                nonempty=True,
                            )
                            unknown_lenses = sorted(set(lenses) - RUNTIME_REVIEW_TYPES)
                            if unknown_lenses:
                                _add(
                                    errors,
                                    f"{review_path}.lenses",
                                    f"unsupported review lenses: {', '.join(unknown_lenses)}",
                                )
                            elif len(lenses) != len(set(lenses)):
                                _add(errors, f"{review_path}.lenses", "must not contain duplicates")
                            elif lenses and review["type"] != next(
                                lens for lens in REVIEW_LENS_ORDER if lens in lenses
                            ):
                                _add(
                                    errors,
                                    f"{review_path}.type",
                                    "must equal the widest lens: security, visual, frontend_code, then backend_code",
                                )
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
                        review_scope = _validate_scope_list(
                            errors,
                            f"{review_path}.scope",
                            review["scope"],
                            nonempty=True,
                        )
                        if review.get("type") == "security":
                            if review.get("stage", "preintegration") != "integration":
                                _add(
                                    errors,
                                    f"{review_path}.stage",
                                    "security review must use the integration stage",
                                )
                            if set(review_missions) != set(missions):
                                _add(
                                    errors,
                                    f"{review_path}.mission_ids",
                                    "security review must cover every PLAN mission",
                                )
                            missing_scope = sorted(
                                f"{mission_id}:{claim}"
                                for mission_id in review_missions
                                for claim in (
                                    missions.get(mission_id, {}).get("write_scope", [])
                                    if isinstance(missions.get(mission_id), dict)
                                    else []
                                )
                                if isinstance(claim, str)
                                and validate_scope_claim(claim) is None
                                and not any(
                                    validate_scope_claim(parent) is None
                                    and scope_contains(parent, claim)
                                    for parent in review_scope
                                )
                            )
                            if missing_scope:
                                _add(
                                    errors,
                                    f"{review_path}.scope",
                                    "security review scope must contain every covered mission write scope: "
                                    + ", ".join(missing_scope),
                                )
                        _strings(
                            errors,
                            f"{review_path}.required_evidence",
                            review["required_evidence"],
                            nonempty=True,
                        )
                        if "required_tools" in review:
                            required_tools = _strings(
                                errors,
                                f"{review_path}.required_tools",
                                review["required_tools"],
                                nonempty=True,
                            )
                            unknown_tools = sorted(
                                set(required_tools) - REVIEWER_TOOL_KEYS
                            )
                            if unknown_tools:
                                _add(
                                    errors,
                                    f"{review_path}.required_tools",
                                    f"unsupported reviewer tools: {', '.join(unknown_tools)}",
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
                # `target` is optional for most refs so PLANs written before this
                # field existed stay valid; a missing target resolves to "*".
                # When present it must be the exact authorization target
                # select_ready_nodes.py checks the RUN ledger against. The ledger
                # rejects a "*" grant only for push, so a push node needs a
                # target. Cleanup refs (EXACT_TARGET_LIFECYCLE_ACTIONS) may use a
                # "*" grant; validate_cleanup_lifecycle_targets requires them
                # to name an exact target for 0.55.0+ RUNs.
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
                    {"provider_options", "worker_role"},
                ):
                    # Host eligibility is explicit; capability and option support are observed at launch.
                    providers = _strings(
                        errors,
                        f"{runtime_path}.allowed_providers",
                        runtime["allowed_providers"],
                        nonempty=True,
                    )
                    invalid_providers = sorted(
                        p for p in set(providers) if not is_valid_provider_id(p)
                    )
                    if invalid_providers:
                        _add(
                            errors,
                            f"{runtime_path}.allowed_providers",
                            "providers must be lowercase ids like codex or gemini_cli: "
                            + ", ".join(invalid_providers),
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


def ui_acceptance_review(review: dict[str, Any]) -> bool:
    evidence = review.get("required_evidence")
    return "visual" in review_lenses(review) and isinstance(evidence, list) and "ui_acceptance" in evidence




def ui_acceptance_evidence_present(evidence: list[str]) -> bool:
    return isinstance(evidence, list) and all(
        any(isinstance(item, str) and item.startswith(prefix) and item[len(prefix):].strip()
            for item in evidence)
        for prefix in ("ui_parity:", "ui_page_quality:")
    )


def review_covers_ui_acceptance(
    source: dict[str, Any], target: dict[str, Any], worker: dict[str, Any], run: dict[str, Any]
) -> bool:
    """Keep legacy skips; a marked acceptance needs matching coverage and evidence."""
    if not ui_acceptance_review(target):
        return True
    if not ui_acceptance_review(source):
        return False
    for key in ("mission_ids", "required_evidence", "required_tools"):
        required, provided = target.get(key, []), source.get(key, [])
        if not all(isinstance(items, list) and all(isinstance(item, str) for item in items)
                   for items in (required, provided)):
            return False
        if not set(required).issubset(provided):
            return False
    scopes = (source.get("scope"), target.get("scope"))
    if not all(isinstance(items, list) and all(isinstance(item, str) and validate_scope_claim(item) is None for item in items)
               for items in scopes):
        return False
    if not all(any(scope_contains(parent, claim) for parent in scopes[0])
               for claim in scopes[1]):
        return False
    attempts = [item for item in run.get("attempt_log", []) if isinstance(item, dict)
                and item.get("attempt_id") == worker.get("attempt_id")]
    return (
        len(attempts) == 1
        and attempts[0].get("kind") == "review"
        and attempts[0].get("result") == "pass"
        and attempts[0].get("review_lineage_id") == source.get("lineage_id")
        and ui_acceptance_evidence_present(attempts[0].get("evidence", []))
    )


MERGE_CHAIN_SKIP_TYPES = frozenset({"frontend_code", "backend_code"})


def merge_chain_skip_allowed(plan: dict[str, Any], review: dict[str, Any]) -> bool:
    """Only per_mission code reviews may skip; visual and security never do."""
    lenses = review_lenses(review)
    return (
        review_policy(plan) == "per_mission"
        and bool(lenses)
        and lenses <= MERGE_CHAIN_SKIP_TYPES
    )


def reviewed_merge_chain_covers(
    plan: dict[str, Any],
    node: dict[str, Any],
    run: dict[str, Any],
    graph_nodes: dict[str, Any],
) -> bool:
    """Check the recorded merge chain against RUN review state and PLAN scopes.

    ``skip-integration-review`` proves the Git facts from live Git and records
    them as ``integration.reviewed_merge_chain``: every link is a clean automatic
    merge of an exact reviewed mission head. This check binds that record to the
    current head, requires every planned single-mission review of each linked
    mission to PASS that exact head, requires every covered mission to be
    linked, and rejects overlapping write scopes. A visual review judges the
    rendered whole head, so it never uses this skip.
    """

    if not merge_chain_skip_allowed(plan, node["review"]):
        return False
    integration = run.get("integration")
    chain = integration.get("reviewed_merge_chain") if isinstance(integration, dict) else None
    if not isinstance(chain, dict) or not is_full_sha(chain.get("head_sha")):
        return False
    if chain["head_sha"] != integration.get("integration_head_sha"):
        return False
    node_states = (run.get("graph_state") or {}).get("node_states") or {}
    review_mission: dict[Any, Any] = {}
    for node_id, item in graph_nodes.items():
        review = item.get("review") if isinstance(item, dict) else None
        if (
            isinstance(review, dict)
            and review.get("stage", "preintegration") == "preintegration"
            and isinstance(review.get("mission_ids"), list)
            and len(review["mission_ids"]) == 1
            and (node_states.get(node_id) or {}).get("phase") != "superseded"
        ):
            review_mission[node_id] = review["mission_ids"][0]
    passed: dict[tuple[Any, Any], set[Any]] = {}
    workers = run.get("review_workers")
    for worker in workers if isinstance(workers, list) else []:
        if (
            isinstance(worker, dict)
            and worker.get("phase") == "worker_passed"
            and worker.get("outcome") == "pass"
            and worker.get("node_id") in review_mission
        ):
            key = (review_mission[worker["node_id"]], worker.get("reviewed_sha"))
            passed.setdefault(key, set()).add(worker["node_id"])
    links = chain.get("links")
    if not isinstance(links, list) or not links:
        return False
    linked: set[Any] = set()
    for link in links:
        if not isinstance(link, dict) or link.get("mission_id") in linked:
            return False
        mission_id = link["mission_id"]
        planned = {node_id for node_id, owner in review_mission.items() if owner == mission_id}
        if not planned or planned - passed.get((mission_id, link.get("reviewed_sha")), set()):
            return False
        linked.add(mission_id)
    covered = node["review"].get("mission_ids")
    if not isinstance(covered, list) or not covered or not set(covered) <= linked:
        return False
    scopes = {
        mission.get("id"): mission.get("write_scope", [])
        for mission in plan.get("missions", [])
        if isinstance(mission, dict)
    }
    if any(not isinstance(scopes.get(mission_id), list) for mission_id in linked):
        return False
    chained = sorted(linked)
    return not any(
        scope_overlap(left_scope, right_scope, casefold=True)
        for index, left in enumerate(chained)
        for right in chained[index + 1:]
        for left_scope in scopes[left]
        for right_scope in scopes[right]
    )


def _add_integration_review_skip_errors(
    errors: list[str],
    state_path: str,
    node: dict[str, Any],
    run: dict[str, Any],
    graph_nodes: dict[str, Any],
    plan: dict[str, Any],
) -> None:
    """An integration-stage review may skip only when no new combination exists.

    Re-dispatching a reviewer against a commit that a pre-integration review
    already passed reads a byte-identical tree and reaches the same verdict, and
    a reviewer dispatch is one of the most expensive steps in a run. Skipping it
    is safe when the integration head IS that reviewed commit, or it is a merge
    commit whose recorded ``integration_tree_sha`` equals the reviewed commit's
    recorded ``tree_sha`` — same bytes, same verdict. In both cases the PASS
    must cover every lens of the skipped review. A code review may also skip on a recorded
    merge chain of reviewed heads with disjoint write scopes; see
    ``reviewed_merge_chain_covers``. Any other integration head has a
    combination no earlier PASS covers, so the review must run.

    Without this check ``skipped`` carried no justification at all, so this both
    enables the short-circuit and closes that hole.
    """

    if node["review"].get("type") == "security":
        _add(
            errors,
            state_path,
            "skipped integration review is forbidden: security integration review must run fresh on the unified candidate",
        )
        return

    integration = run.get("integration")
    head = integration.get("integration_head_sha") if isinstance(integration, dict) else None
    if not is_full_sha(head):
        _add(
            errors,
            state_path,
            "skipped integration review requires a recorded integration_head_sha",
        )
        return

    integration_tree = (
        integration.get("integration_tree_sha") if isinstance(integration, dict) else None
    )
    tree_bound = is_full_sha(integration_tree)

    lenses = review_lenses(node["review"])
    review_workers = run.get("review_workers")
    for worker in review_workers if isinstance(review_workers, list) else []:
        if not isinstance(worker, dict):
            continue
        if worker.get("phase") != "worker_passed" or worker.get("outcome") != "pass":
            continue
        source = graph_nodes.get(worker.get("node_id"))
        if not isinstance(source, dict) or not isinstance(source.get("review"), dict):
            continue
        if source["review"].get("stage", "preintegration") != "preintegration":
            continue
        if not lenses or not lenses <= review_lenses(source["review"]):
            continue
        if not review_covers_ui_acceptance(source["review"], node["review"], worker, run):
            continue
        if worker.get("reviewed_sha") == head:
            return
        if (
            tree_bound
            and is_full_sha(worker.get("tree_sha"))
            and worker["tree_sha"] == integration_tree
        ):
            return
    if reviewed_merge_chain_covers(plan, node, run, graph_nodes):
        return

    _add(
        errors,
        state_path,
        "skipped integration review requires a pre-integration PASS of the same"
        " review type on the exact integration head or a byte-identical tree,"
        " or a recorded merge chain of reviewed heads",
    )


def _validate_graph_state(
    errors: list[str], plan: dict[str, Any], run: dict[str, Any]
) -> None:
    path = "run.graph_state"
    security_policy = plan.get("security_review")
    required_security = (
        isinstance(security_policy, dict)
        and security_policy.get("status") == "required"
    )
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
    retained_attempt_ids = {
        attempt.get("attempt_id")
        for attempt in run.get("attempt_log", [])
        if isinstance(attempt, dict) and _nonempty_string(attempt.get("attempt_id"))
    }
    graph_attempt_nodes = set(graph_nodes)
    for index, attempt in enumerate(
        run.get("attempt_log", []) if isinstance(run.get("attempt_log"), list) else []
    ):
        if not isinstance(attempt, dict) or attempt.get("node_id") is None:
            continue
        node_id = attempt.get("node_id")
        if node_id not in graph_attempt_nodes:
            _add(
                errors,
                f"run.attempt_log[{index}].node_id",
                "must reference a PLAN graph node",
            )
        if attempt.get("kind") == "node_attempt" and not _nonempty_string(
            attempt.get("attempt_id")
        ):
            _add(
                errors,
                f"run.attempt_log[{index}].attempt_id",
                "node attempt requires a non-empty attempt ID",
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
                or not _is_int(attempts)
                or attempts < 1
            ):
                _add(errors, state_path, "terminal node requires attempt identity, outcome, and attempts")
            if phase == "blocked" and not blockers:
                _add(errors, f"{state_path}.blockers", "blocked node requires a blocker")
            if phase == "running" and node.get("executor") == "runtime_worker" and not _nonempty_string(
                state["bound_worker_id"]
            ):
                _add(errors, f"{state_path}.bound_worker_id", "is required for a running runtime worker")

            if (
                node.get("kind") == "verifier"
                and isinstance(node.get("review"), dict)
                and node["review"].get("stage") == "integration"
                and phase == "skipped"
            ):
                _add_integration_review_skip_errors(
                    errors, state_path, node, run, graph_nodes, plan
                )

            if phase == "succeeded" and isinstance(node.get("review"), dict) and ui_acceptance_review(node["review"]):
                if not review_covers_ui_acceptance(node["review"], node["review"], {"attempt_id": state["last_attempt_id"]}, run):
                    _add(errors, state_path, "UI acceptance PASS requires ui_parity: and ui_page_quality: evidence anchors")

            # A required security review is a hard closeout gate.  It may not
            # be converted into a historical skip or superseded state to make
            # the final graph appear complete.  The closeout validator below
            # additionally binds the terminal state to the exact current
            # structured PASS result, but rejecting these terminal phases here
            # also protects non-complete RUNs from silently bypassing the gate.
            if (
                required_security
                and node.get("kind") == "verifier"
                and isinstance(node.get("review"), dict)
                and node["review"].get("type") == "security"
                and node["review"].get("stage") == "integration"
                and phase in {"skipped", "superseded"}
            ):
                _add(
                    errors,
                    state_path,
                    "required security integration review cannot be skipped or superseded",
                )

            if (
                node.get("kind") == "verifier"
                and isinstance(node.get("review"), dict)
                and node["review"].get("stage") == "integration"
                and phase in {"ready", "running"}
            ):
                incomplete_missions = sorted(
                    mission_id
                    for mission_id in node["review"].get("mission_ids", [])
                    if not isinstance(mission_states.get(mission_id), dict)
                    or mission_states[mission_id].get("phase") != "integrated"
                )
                if incomplete_missions:
                    _add(
                        errors,
                        state_path,
                        "integration review cannot become ready or run before every covered mission is integrated: "
                        + ", ".join(incomplete_missions),
                    )
                integration = run.get("integration")
                if not isinstance(integration, dict) or not is_full_sha(
                    integration.get("integration_head_sha")
                ):
                    _add(
                        errors,
                        state_path,
                        "integration review requires a full integration head SHA",
                    )

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
                and _nonempty_string(state["source_attempt_id"])
                and source_state.get("last_attempt_id") != state["source_attempt_id"]
                and state["source_attempt_id"] not in retained_attempt_ids
            ):
                _add(
                    errors,
                    f"{state_path}.source_attempt_id",
                    "must match the source node's current attempt or a retained attempt_log entry",
                )
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

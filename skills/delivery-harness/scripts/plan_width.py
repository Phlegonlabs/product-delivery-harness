#!/usr/bin/env python3
"""Report how parallel one PLAN can actually run.

A selector can only run missions together when the PLAN leaves them ready
together. This read-only planning aid groups missions into dependency levels,
measures the width of each level after mission conflicts, and reports the
findings that keep a PLAN narrower than its missions need. It reads only the
PLAN, never RUN, Git, or the network, and never writes a file, so a planner
can run it on a draft: it needs ``missions``, ``max_parallel_workers`` and
``graph.nodes`` / ``graph.edges`` to be readable, not a fully valid PLAN.

Dependency semantics follow the selector (``select_ready_nodes.py``): only
``kind: "dependency"`` edges count, so a conditional repair loop is neither a
dependency chain nor a crash.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

from harness_core import mission_conflicts
from harness_manifest import ManifestError, load_plan


class PlanWidthError(ValueError):
    """Raised when the PLAN cannot be read far enough to report width."""


def _index(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _readable_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise PlanWidthError("PLAN manifest must be an object")
    if not isinstance(plan.get("missions"), list):
        raise PlanWidthError("PLAN: missions must be a list")
    budget = plan.get("max_parallel_workers")
    if not isinstance(budget, int) or isinstance(budget, bool):
        raise PlanWidthError("PLAN: max_parallel_workers must be an integer")
    graph = plan.get("graph")
    if not isinstance(graph, dict):
        raise PlanWidthError("PLAN: graph must be an object")
    for key in ("nodes", "edges"):
        if not isinstance(graph.get(key), list):
            raise PlanWidthError(f"PLAN: graph.{key} must be a list")
    return plan


def _missions(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    missions: dict[str, dict[str, Any]] = {}
    for mission in plan["missions"]:
        if isinstance(mission, dict) and isinstance(mission.get("id"), str) and mission["id"]:
            missions.setdefault(mission["id"], mission)
    return missions


def _incoming_dependencies(plan: dict[str, Any]) -> dict[str, list[str]]:
    """Reversed dependency adjacency. Route edges never form dependencies."""
    graph = plan["graph"]
    node_ids = {
        node["id"]
        for node in graph["nodes"]
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    incoming: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in graph["edges"]:
        if not isinstance(edge, dict) or edge.get("kind") != "dependency":
            continue
        source, target = edge.get("from"), edge.get("to")
        if isinstance(source, str) and source in node_ids and target in node_ids:
            incoming[target].append(source)
    return incoming


def _node_refs(plan: dict[str, Any], missions: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {
        node["id"]: node["ref"]
        for node in plan["graph"]["nodes"]
        if isinstance(node, dict)
        and node.get("kind") == "mission"
        and isinstance(node.get("id"), str)
        and isinstance(node.get("ref"), str)
        and node["ref"] in missions
    }


def _immediate_dependencies(
    incoming: dict[str, list[str]], node_refs: dict[str, str]
) -> dict[str, set[str]]:
    """The missions each mission directly waits for.

    Walking backward from a mission node stops at the first mission node on
    each path, so an edge through any number of review or gate nodes still
    counts while a longer chain through another mission does not.
    """

    nodes_by_mission: dict[str, list[str]] = {}
    for node_id, ref in node_refs.items():
        nodes_by_mission.setdefault(ref, []).append(node_id)
    immediate: dict[str, set[str]] = {ref: set() for ref in nodes_by_mission}
    for mission_id, node_ids in nodes_by_mission.items():
        visited: set[str] = set(node_ids)
        frontier = list(node_ids)
        while frontier:
            node_id = frontier.pop()
            for source in incoming.get(node_id, []):
                if source in visited:
                    continue
                visited.add(source)
                ref = node_refs.get(source)
                if ref is None:
                    frontier.append(source)
                else:
                    immediate[mission_id].add(ref)
    return immediate


def _mission_levels(
    immediate: dict[str, set[str]], mission_ids: list[str]
) -> dict[str, int]:
    successors: dict[str, list[str]] = {mission_id: [] for mission_id in mission_ids}
    remaining = {mission_id: len(immediate.get(mission_id, ())) for mission_id in mission_ids}
    for mission_id in mission_ids:
        for source in immediate.get(mission_id, ()):
            successors[source].append(mission_id)
    levels = {mission_id: 0 for mission_id in mission_ids if remaining[mission_id] == 0}
    ready = [mission_id for mission_id in mission_ids if remaining[mission_id] == 0]
    while ready:
        source = ready.pop()
        for mission_id in successors[source]:
            remaining[mission_id] -= 1
            if remaining[mission_id] == 0:
                levels[mission_id] = 1 + max(levels[source] for source in immediate[mission_id])
                ready.append(mission_id)
    if len(levels) != len(mission_ids):
        raise PlanWidthError("PLAN: mission dependency cycle")
    return levels


def _level_groups(levels: dict[str, int], mission_ids: list[str]) -> list[list[str]]:
    groups: dict[int, list[str]] = {}
    for mission_id in mission_ids:
        groups.setdefault(levels[mission_id], []).append(mission_id)
    return [sorted(groups[level]) for level in sorted(groups)]


def _selector_key(missions: dict[str, dict[str, Any]], mission_id: str) -> tuple[int, int, str]:
    mission = missions[mission_id]
    return (-_index(mission.get("priority")), _index(mission.get("merge_rank")), mission_id)


def _runnable_set(
    group: list[str], missions: dict[str, dict[str, Any]]
) -> list[str]:
    chosen: list[str] = []
    for mission_id in sorted(group, key=lambda item: _selector_key(missions, item)):
        if all(
            not mission_conflicts(missions[mission_id], missions[other])
            for other in chosen
        ):
            chosen.append(mission_id)
    return chosen


def _critical_path(
    immediate: dict[str, set[str]], mission_ids: list[str]
) -> list[str]:
    if not mission_ids:
        return []
    best: dict[str, int] = {}
    predecessor: dict[str, str | None] = {}

    def resolve(mission_id: str) -> int:
        if mission_id in best:
            return best[mission_id]
        sources = sorted(immediate.get(mission_id, ()))
        if not sources:
            best[mission_id] = 1
            predecessor[mission_id] = None
            return 1
        lengths = {source: resolve(source) for source in sources}
        longest = max(lengths.values())
        predecessor[mission_id] = next(
            source for source in sources if lengths[source] == longest
        )
        best[mission_id] = 1 + longest
        return best[mission_id]

    for mission_id in sorted(mission_ids):
        resolve(mission_id)
    cursor = min(mission_ids, key=lambda item: (-best[item], item))
    path: list[str] = []
    while cursor is not None:
        path.append(cursor)
        cursor = predecessor[cursor]
    return list(reversed(path))


def _shared_resource_claims(
    missions: dict[str, dict[str, Any]]
) -> dict[tuple[str, str], set[str]]:
    claims: dict[tuple[str, str], set[str]] = {}
    for mission_id, mission in missions.items():
        for key in mission.get("serialized_resources", []) or []:
            if isinstance(key, str):
                claims.setdefault(("serialized", key), set()).add(mission_id)
        for resource in mission.get("runtime_resources", []) or []:
            if (
                isinstance(resource, dict)
                and isinstance(resource.get("key"), str)
                and resource.get("access") == "exclusive"
            ):
                claims.setdefault(("runtime", resource["key"]), set()).add(mission_id)
    return {claim: holders for claim, holders in sorted(claims.items())}


def _findings(
    plan: dict[str, Any],
    missions: dict[str, dict[str, Any]],
    immediate: dict[str, set[str]],
    level_groups: list[list[str]],
    width: int,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for target in sorted(immediate):
        for source in sorted(immediate[target]):
            if mission_conflicts(missions[source], missions[target]):
                continue
            findings.append(
                {
                    "code": "chain_without_conflict",
                    "missions": [source, target],
                    "detail": (
                        f"{target} waits for {source} although their scopes and "
                        f"resources do not conflict; keep the edge only if "
                        f"{target} consumes something {source} produces"
                    ),
                }
            )
    for level, group in enumerate(level_groups):
        for left, right in combinations(group, 2):
            reasons = mission_conflicts(missions[left], missions[right])
            if reasons:
                findings.append(
                    {
                        "code": "same_level_conflict",
                        "missions": [left, right],
                        "detail": (
                            f"{left} and {right} share level {level} but conflict: "
                            + ", ".join(reasons)
                        ),
                    }
                )
    for (kind, key), holders in _shared_resource_claims(missions).items():
        if len(holders) < 3:
            continue
        label = (
            "serialized resource"
            if kind == "serialized"
            else "runtime resource with exclusive access"
        )
        findings.append(
            {
                "code": "shared_exclusive_resource",
                "missions": sorted(holders),
                "detail": (
                    f"{len(holders)} missions claim {label} \"{key}\"; a per-worktree "
                    "port or database path removes the claim"
                ),
            }
        )
    budget = plan["max_parallel_workers"]
    if budget < width:
        findings.append(
            {
                "code": "budget_below_width",
                "missions": [],
                "detail": (
                    f"max_parallel_workers {budget} is below width {width}; the "
                    "widest level cannot run in one wave"
                ),
            }
        )
    return sorted(
        findings, key=lambda finding: (finding["code"], finding["missions"], finding["detail"])
    )


def measure(plan: dict[str, Any]) -> dict[str, Any]:
    _readable_plan(plan)
    missions = _missions(plan)
    mission_ids = sorted(missions)
    immediate = _immediate_dependencies(_incoming_dependencies(plan), _node_refs(plan, missions))
    levels = _mission_levels(immediate, mission_ids)
    level_groups = _level_groups(levels, mission_ids)
    dependency_width = max((len(group) for group in level_groups), default=0)
    width = max(
        (len(_runnable_set(group, missions)) for group in level_groups), default=0
    )
    return {
        "plan_id": plan.get("plan_id"),
        "revision": plan.get("revision"),
        "missions": len(missions),
        "configured_max_parallel_workers": plan["max_parallel_workers"],
        "levels": level_groups,
        "dependency_width": dependency_width,
        "width": width,
        "critical_path": _critical_path(immediate, mission_ids),
        "findings": _findings(plan, missions, immediate, level_groups, width),
    }


def report(result: dict[str, Any]) -> str:
    lines = [
        f"plan width: {result['width']} (dependency width {result['dependency_width']}, "
        f"{result['missions']} missions, budget {result['configured_max_parallel_workers']})"
    ]
    for level, group in enumerate(result["levels"]):
        lines.append(f"level {level}: {', '.join(group)}")
    lines.append(
        "critical path: " + (" -> ".join(result["critical_path"]) or "none")
    )
    if result["findings"]:
        for finding in result["findings"]:
            joined = ", ".join(finding["missions"])
            if joined:
                lines.append(f"{finding['code']}: {joined} — {finding['detail']}")
            else:
                lines.append(f"{finding['code']}: {finding['detail']}")
    else:
        lines.append("findings: none")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report a PLAN's parallel width, critical path, and findings."
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--json", action="store_true", help="print the JSON report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = _readable_plan(load_plan(args.plan))
    except (ManifestError, OSError, PlanWidthError) as exc:
        print(f"plan_width: {exc}", file=sys.stderr)
        return 2
    result = measure(plan)
    if args.json:
        print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    else:
        print(report(result))
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())

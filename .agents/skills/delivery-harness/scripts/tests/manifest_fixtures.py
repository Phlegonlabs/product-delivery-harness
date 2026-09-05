"""Shared manifest fixtures for Harness command-line tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import AUTHORIZATION_KEYS, plan_digest  # noqa: E402
from harness_schema import (  # noqa: E402
    CURRENT_PLAN_SCHEMA_VERSION,
    CURRENT_RUN_SCHEMA_VERSION,
)


SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40


def manifest_markdown(
    heading: str, wrapper: str, value: dict[str, object]
) -> str:
    encoded = json.dumps({wrapper: value}, sort_keys=True, indent=2)
    return f"# Harness fixture\n\n{heading}\n\n```json\n{encoded}\n```\n"


def wireframes_html(
    screens: list[dict[str, object]],
    *,
    product: str = "Fixture Product",
    approval_status: str = "approved",
) -> str:
    """A wireframes.html that passes product-definition-builder's full checker.

    Each screen dict carries the PLAN surface's ``id``, ``route``, and
    ``states``; the shell carries every reviewer marker and stays
    self-contained.
    """

    data_screens: list[dict[str, object]] = []
    for screen in screens:
        screen_id = str(screen["id"])
        region_id = f"{screen_id}-R1"
        states = [str(state) for state in (screen.get("states") or ["ready"])]
        data_screens.append(
            {
                "id": screen_id,
                "name": f"{screen_id} screen",
                "route": screen["route"],
                "goal": "fixture screen",
                "regions": [
                    {
                        "id": region_id,
                        "section": "Main",
                        "purpose": "Primary content",
                        "priority": "primary",
                        "span": 12,
                        "elements": ["Fixture element"],
                        "actions": [],
                    }
                ],
                "compactOrder": [region_id],
                "states": [
                    {
                        "id": state,
                        "label": state,
                        "treatments": {region_id: "unchanged"},
                    }
                    for state in states
                ],
            }
        )
    data = {
        "product": product,
        "approvalStatus": approval_status,
        "source": "PRD.md#UI-Surface-Contract",
        "screens": data_screens,
    }
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head><meta charset=\"utf-8\"><title>Wireframes</title></head>\n"
        "<body>\n"
        '<nav id="page-list" aria-label="All pages"></nav>\n'
        '<div id="state-controls"></div>\n'
        '<button type="button" data-viewport="expanded">Expanded</button>\n'
        '<button type="button" data-viewport="compact">Compact</button>\n'
        "<h2>All pages</h2>\n"
        "<main></main>\n"
        "<script>\n"
        "document.getElementById('page-list').textContent = 'All pages';\n"
        "</script>\n"
        '<script id="wireframe-data" type="application/json">\n'
        + json.dumps(data)
        + "\n</script>\n"
        "</body>\n</html>\n"
    )


def git(root: Path, *args: str) -> str:
    """Run git in `root`; raise with stderr on failure; return stripped stdout."""

    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed in {root}:\n{result.stderr}"
        )
    return result.stdout.strip()


def init_repo(root: Path, *files: str, default_branch: str = "main") -> str:
    """Create a committed repo with one commit per named file; return the head."""

    git(root, "init", "-q", "-b", default_branch)
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Harness Test")
    for name in files:
        (root / name).write_text(f"{name} base\n", encoding="utf-8")
        git(root, "add", name)
        git(root, "commit", "-qm", f"add {name}")
    return git(root, "rev-parse", "HEAD")


def verifier(identifier: str, *argv: str) -> dict[str, object]:
    return {
        "id": identifier,
        "cwd": ".",
        "argv": list(argv) or ["python3", "-m", "unittest"],
        "pass_signal": "exit 0",
    }


def task(
    mission_id: str,
    number: int,
    trace_id: str,
    path: str,
    *,
    depends_on: list[str] | None = None,
) -> dict[str, object]:
    task_id = f"{mission_id}/T{number:02d}"
    return {
        "id": task_id,
        "alias": f"task-{number}",
        "objective": f"Complete {task_id}",
        "acceptance_matrix": [
            {
                "test_id": f"TEST-{mission_id}-{number:02d}",
                "trace_ids": [trace_id],
                "criterion": f"{task_id} passes",
            }
        ],
        "trace_ids": [trace_id],
        "depends_on": list(depends_on or []),
        "parent_task": None,
        "legacy_task_ids": [],
        "replaced_by": [],
        "split_reason": None,
        "refinement_generation": 0,
        "write_scope": [path],
        "verifiers": [verifier(f"verify-{mission_id.lower()}-{number}", "tool", task_id)],
    }


def mission(
    mission_id: str,
    trace_id: str,
    write_scope: str,
    tasks: list[dict[str, object]],
    *,
    depends_on: list[str] | None = None,
    priority: int = 100,
    merge_rank: int = 10,
) -> dict[str, object]:
    return {
        "id": mission_id,
        "alias": mission_id.lower(),
        "objective": f"Deliver {mission_id}",
        "priority": priority,
        "merge_rank": merge_rank,
        "trace_ids": [trace_id],
        "write_scope": [write_scope],
        "deny_scope": ["docs/goal/PLAN.md", "docs/goal/RUN.md"],
        "resource_inventory_complete": True,
        "serialized_resources": [],
        "runtime_resources": [],
        "worktree_eligible": True,
        "required_skills": [],
        "stop_conditions": ["Stop on contract conflict"],
        "worker_verifiers": [verifier(f"worker-{mission_id.lower()}", "tool", "worker")],
        "integration_verifiers": [
            verifier(f"integrate-{mission_id.lower()}", "tool", "integration")
        ],
        "tasks": tasks,
    }


def graph_node(
    node_id: str,
    kind: str,
    ref: str,
    executor: str,
    outcomes: list[str],
) -> dict[str, object]:
    return {
        "id": node_id,
        "kind": kind,
        "ref": ref,
        "executor": executor,
        "allowed_outcomes": outcomes,
        "max_attempts": 2,
        "runtime": (
            {"preferred_provider": None, "allowed_providers": ["codex", "claude_code"]}
            if executor == "runtime_worker"
            else None
        ),
    }


def graph_for(*missions: dict[str, object]) -> dict[str, object]:
    """A mission chain, one singleton review per mission, one final gate.

    v10 needs every write-scope mission to have its own direct singleton
    pre-integration review, and v5 needs each review's `pass` to route into a
    deterministic gate. A review that covers exactly the one mission it depends
    on satisfies bounded repair through same-worktree correction, so no repair
    route is needed.
    """
    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    previous: str | None = None
    for item in missions:
        mission_id = item["id"]
        node_id = f"N-{mission_id}"
        review_id = f"N-REVIEW-{mission_id}"
        review_pass_id = f"N-REVIEW-PASS-{mission_id}"
        nodes.append(
            graph_node(
                node_id,
                "mission",
                mission_id,
                "runtime_worker",
                ["pass", "retryable_failure", "blocked", "contract_gap"],
            )
        )
        review = graph_node(
            review_id,
            "verifier",
            "batch",
            "runtime_worker",
            ["pass", "fix_required", "retryable_failure", "blocked", "contract_gap"],
        )
        review["review"] = {
            "type": "backend_code",
            "lineage_id": f"REVIEW-{mission_id}",
            "mission_ids": [mission_id],
            "scope": list(item["write_scope"]),
            "required_evidence": ["reviewed_sha", "findings"],
        }
        nodes.append(review)
        nodes.append(
            graph_node(
                review_pass_id,
                "verifier",
                "batch",
                "local_command",
                ["pass", "blocked"],
            )
        )
        edges.append(
            {
                "id": f"E-{mission_id}-REVIEW",
                "kind": "dependency",
                "from": node_id,
                "to": review_id,
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        edges.append(
            {
                "id": f"E-{mission_id}-REVIEW-PASS",
                "kind": "route",
                "from": review_id,
                "to": review_pass_id,
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        edges.append(
            {
                "id": f"E-{mission_id}-REVIEW-PASS-FINAL",
                "kind": "dependency",
                "from": review_pass_id,
                "to": "N-FINAL",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        if previous is not None:
            edges.append(
                {
                    "id": f"E-{previous}-{mission_id}",
                    "kind": "dependency",
                    "from": f"N-{previous}",
                    "to": node_id,
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                }
            )
        previous = mission_id
    nodes.append(
        graph_node("N-FINAL", "verifier", "final", "local_command", ["pass", "blocked"])
    )
    return {
        "entry_nodes": [f"N-{missions[0]['id']}"],
        "nodes": nodes,
        "edges": edges,
    }


def valid_plan() -> dict[str, object]:
    m1_tasks = [
        task("M1", 1, "REQ-001", "src/a/one.py"),
        task(
            "M1",
            2,
            "REQ-001",
            "src/a/two.py",
            depends_on=["M1/T01"],
        ),
    ]
    m1 = mission("M1", "REQ-001", "src/a/**", m1_tasks)
    m1["runtime_resources"] = [
        {"key": "port:3000", "access": "exclusive"},
        {"key": "db:test", "access": "shared_read"},
    ]
    m1["serialized_resources"] = ["migration:primary", "fixture:users"]

    m2 = mission(
        "M2",
        "REQ-002",
        "src/ab/**",
        [task("M2", 1, "REQ-002", "src/ab/one.py")],
        depends_on=["M1"],
        priority=80,
        merge_rank=20,
    )
    m2["runtime_resources"] = [{"key": "port:3001", "access": "exclusive"}]
    return {
        "schema_version": CURRENT_PLAN_SCHEMA_VERSION,
        "plan_id": "PLAN-TEST",
        "revision": 1,
        "objective": "Deliver a deterministic test plan",
        "max_parallel_workers": 3,
        "sources": [
            {
                "id": "SRC-001",
                "kind": "prd",
                "location": "docs/product/prd.md",
                "owner": "product",
                "status": "frozen",
                "content_sha256": "f" * 64,
                "source_revision": None,
                "staged_revision": None,
                "notes": "product contract",
            },
            {
                "id": "SRC-002",
                "kind": "architecture",
                "location": "docs/product/architecture.md",
                "owner": "engineering",
                "status": "frozen",
                "content_sha256": "e" * 64,
                "source_revision": None,
                "staged_revision": None,
                "notes": "technical contract",
            },
        ],
        "traces": [
            {
                "id": "REQ-001",
                "source_ids": ["SRC-002", "SRC-001"],
                "priority": "must",
                "requirement": "Deliver the first capability",
                "disposition": "planned",
                "rationale": None,
            },
            {
                "id": "REQ-002",
                "source_ids": ["SRC-001"],
                "priority": "should",
                "requirement": "Deliver the second capability",
                "disposition": "planned",
                "rationale": None,
            },
        ],
        "ui_surfaces": [],
        "risks": [],
        "batch_verifiers": [verifier("batch", "tool", "batch")],
        "final_gates": [verifier("final", "tool", "final")],
        "required_reviews": ["backend_code"],
        "graph": graph_for(m1, m2),
        "missions": [m1, m2],
    }


def legacy_plan(schema_version: int = 2) -> dict[str, object]:
    """Build a valid non-graph PLAN using an explicitly supported old schema."""
    if schema_version not in {2, 3}:
        raise ValueError("legacy non-graph PLAN schema must be 2 or 3")
    plan = valid_plan()
    plan["schema_version"] = schema_version
    plan.pop("graph")
    plan.pop("required_reviews")
    for source in plan["sources"]:
        source.pop("content_sha256")
        source.pop("source_revision")
        source.pop("staged_revision")
    dependencies = {"M1": [], "M2": ["M1"]}
    for current_mission in plan["missions"]:
        current_mission["depends_on"] = dependencies[current_mission["id"]]
        for current_task in current_mission["tasks"]:
            current_task["acceptance_matrix"] = [
                row["criterion"] for row in current_task["acceptance_matrix"]
            ]
    return plan


def legacy_graph_plan() -> dict[str, object]:
    """Build the readable PLAN-v4 form of the canonical typed graph."""
    plan = valid_plan()
    plan["schema_version"] = 4
    for source in plan["sources"]:
        source.pop("staged_revision")
    for current_mission in plan["missions"]:
        for current_task in current_mission["tasks"]:
            current_task["acceptance_matrix"] = [
                row["criterion"] for row in current_task["acceptance_matrix"]
            ]
    return plan








def current_version_gate() -> dict[str, object]:
    return {
        "host_version": "test-current",
        "minimum_host_version": None,
        "harness_version": "0.6.0",
        "required_harness_version": "0.6.0",
        "session_id": "test-session",
        "loaded_contract_digest": "a" * 64,
        "installed_contract_digest": "a" * 64,
        "status": "current",
        "evidence": "test fixture observed the current runtime and Harness release",
    }


def _valid_run(plan: dict[str, object]) -> dict[str, object]:
    digest = plan_digest(plan)
    mission_ids = [item["id"] for item in plan["missions"]]
    task_ids = [
        item["id"]
        for current_mission in plan["missions"]
        for item in current_mission["tasks"]
    ]
    return {
        "schema_version": CURRENT_RUN_SCHEMA_VERSION,
        "run_id": "RUN-TEST",
        "plan": {
            "id": plan["plan_id"],
            "revision": plan["revision"],
            "digest_sha256": digest,
        },
        "status": "draft",
        "intent": "plan-only",
        "plan_readiness": "draft",
        "execution_authorized": False,
        "execution_authorization_source": None,
        "execution_authorization_scope": None,
        "control": {
            "desired_state": "running",
            "requested_at": None,
            "source": None,
            "acknowledged_at": None,
        },
        "authorizations": {
            key: {"authorized": False, "source": None}
            for key in AUTHORIZATION_KEYS
        },
        "runtime_capabilities": {
            "worker_runtime": "parent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": 1,
            "runtime_adapter": {
                "provider": "codex",
                "available_drivers": ["sequential_parent"],
                "detection_source": "fallback",
                "version_gate": current_version_gate(),
            },
            "platform_lifecycle": {
                "owner": "parent",
                "automatic_retention_cleanup_possible": False,
                "durable_branch_required_before_unique_work": True,
            },
        },
        "observed": {
            "captured_at": None,
            "git": {
                "parent_worktree_path": "C:/repo/product-delivery-harness",
                "parent_branch": "main",
                "parent_head_sha": SHA_A,
                "parent_dirty": False,
                "worktrees": [],
            },
            "runtime": {
                "available_worker_slots": 1,
                "isolation_capacity": 1,
                "completion_channel_available": True,
            },
        },
        "integration": {
            "branch": "codex/test",
            "batch_base_sha": SHA_A,
            "integration_head_sha": SHA_A,
            "coordination_paths": [
                "docs/goal/PLAN.md",
                "docs/goal/RUN.md",
                "docs/goal/DECISIONS.md",
            ],
        },
        "landing": {
            "mode": "local_only",
            "remote": "origin",
            "pushed_head_sha": None,
            "continuity": None,
        },
        "mission_states": {
            mission_id: {
                "phase": "queued",
                "lease_id": None,
                "lease_plan_revision": None,
                "lease_plan_digest_sha256": None,
                "worker_id": None,
                "base_sha": None,
                "head_sha": None,
                "integration_gate": "planned",
                "integrated_sha": None,
                "blockers": [],
                "report_path": None,
            }
            for mission_id in mission_ids
        },
        "task_states": {
            task_id: {
                "phase": "queued",
                "attempts": 0,
                "commit_sha": None,
                "verifier_status": "planned",
                "blockers": [],
                "refinement_request": None,
            }
            for task_id in task_ids
        },
        "active_wave": {
            "wave_id": None,
            "status": "idle",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "batch_base_sha": None,
            "selected_missions": [],
            "deferred_missions": [],
            "conflict_edges": [],
        },
        "closed_waves": [],
        "workers": [],
        "review_workers": [],
        "review_lineages": {
            node["review"]["lineage_id"]: {
                "review_type": node["review"]["type"],
                "mission_ids": node["review"]["mission_ids"],
                "base_allowance": node["max_attempts"],
                "additional_allowance": 0,
                "consumed_attempts": 0,
                "failure_families": [],
                "owner_decisions": [],
            }
            for node in plan["graph"]["nodes"]
            if isinstance(node.get("review"), dict)
            and isinstance(node["review"].get("lineage_id"), str)
        },
        "attempt_log": [],
        "batch_gate_results": [
            {"id": gate["id"], "status": "planned", "head_sha": None, "evidence": []}
            for gate in plan["batch_verifiers"]
        ],
        "final_gate_results": [
            {"id": gate["id"], "status": "planned", "head_sha": None, "evidence": []}
            for gate in plan["final_gates"]
        ],
        "ui_evidence": [],
        "verifier_executions": [],
        "graph_state": {
            "graph_revision": plan["revision"],
            "node_states": {
                node["id"]: {
                    "phase": "dormant",
                    "attempts": 0,
                    "last_attempt_id": None,
                    "last_outcome": None,
                    "bound_worker_id": None,
                    "blockers": [],
                }
                for node in plan["graph"]["nodes"]
            },
            "edge_states": {
                edge["id"]: {
                    "status": "dormant",
                    "traversals": 0,
                    "source_attempt_id": None,
                }
                for edge in plan["graph"]["edges"]
            },
        },
    }


def valid_run(plan: dict[str, object]) -> dict[str, object]:
    """Build the current pair, or the matching v5/v10 compatibility fixture."""
    run = _valid_run(plan)
    if plan.get("schema_version") != 6:
        run["schema_version"] = 10
        run.pop("control")
        run.pop("review_lineages")
        run["integration"].pop("coordination_paths")
        gate = run["runtime_capabilities"]["runtime_adapter"]["version_gate"]
        gate.pop("session_id")
        gate.pop("loaded_contract_digest")
        gate.pop("installed_contract_digest")
    return run


def codex_capability_probe(
    *,
    app_threads: bool = False,
    subagents: bool = False,
    unobserved: set[str] | None = None,
) -> dict[str, object]:
    """Return a complete RUN-v10 Codex capability probe for focused tests."""
    unobserved = unobserved or set()
    app_capabilities = {
        "app_project_list",
        "app_thread_create",
        "app_thread_read",
        "app_thread_message",
        "app_thread_wait",
        "app_managed_worktree",
    }
    subagent_capabilities = {"direct_subagent_spawn", "direct_agent_result"}
    return {
        capability: {
            "status": (
                "unobserved"
                if capability in unobserved
                else "available"
                if (
                    app_threads and capability in app_capabilities
                ) or (
                    subagents and capability in subagent_capabilities
                )
                else "unavailable"
            ),
            "evidence": f"test observation: {capability}",
        }
        for capability in sorted(app_capabilities | subagent_capabilities)
    }


def legacy_run(plan: dict[str, object], schema_version: int) -> dict[str, object]:
    """Build a RUN whose body, not only version number, matches an old schema."""
    if schema_version not in {5, 6, 7, 8, 9}:
        raise ValueError("legacy RUN schema must be 5 through 9")
    run = valid_run(valid_plan())
    digest = plan_digest(plan)
    run["schema_version"] = schema_version
    run.pop("control", None)
    run.pop("review_lineages", None)
    run["integration"].pop("coordination_paths", None)
    run.pop("closed_waves")
    run["plan"] = {
        "id": plan["plan_id"],
        "revision": plan["revision"],
        "digest_sha256": digest,
    }
    run["active_wave"]["plan_revision"] = plan["revision"]
    run["active_wave"]["plan_digest_sha256"] = digest
    run.pop("verifier_executions")
    graph_run = plan["schema_version"] == 4 and schema_version in {8, 9}
    if not graph_run:
        run.pop("graph_state")
        run.pop("review_workers")
    if schema_version != 9:
        run.pop("batch_gate_results")
        run.pop("final_gate_results")
        run.pop("ui_evidence")
    if schema_version == 5:
        run["runtime_capabilities"].pop("runtime_adapter")
    else:
        run["runtime_capabilities"]["runtime_adapter"].pop("version_gate", None)
    return run


def legacy_graph_run(
    plan: dict[str, object], schema_version: int = 8
) -> dict[str, object]:
    if plan.get("schema_version") != 4 or schema_version not in {8, 9}:
        raise ValueError("legacy graph RUN requires PLAN v4 with RUN v8 or v9")
    run = valid_run(plan)
    run["schema_version"] = schema_version
    run.pop("control", None)
    run.pop("review_lineages", None)
    run["integration"].pop("coordination_paths", None)
    run["runtime_capabilities"]["runtime_adapter"].pop("version_gate", None)
    run.pop("closed_waves")
    run.pop("verifier_executions")
    if schema_version == 8:
        run.pop("batch_gate_results")
        run.pop("final_gate_results")
        run.pop("ui_evidence")
    return run


def mark_legacy_complete(plan: dict[str, object], run: dict[str, object]) -> None:
    """Complete a legacy RUN without adding RUN-v10 verifier executions."""
    run["status"] = "complete"
    run["intent"] = "plan-then-execute"
    run["plan_readiness"] = "ready"
    for state in run["mission_states"].values():
        state["phase"] = "integrated"
        state["integration_gate"] = "PASS"
        state["integrated_sha"] = run["integration"]["integration_head_sha"]
    for state in run["task_states"].values():
        state["phase"] = "mission_recorded"
        state["verifier_status"] = "PASS"
    for results in (
        run.get("batch_gate_results", []),
        run.get("final_gate_results", []),
    ):
        for result in results:
            result["status"] = "PASS"
            result["head_sha"] = run["integration"]["integration_head_sha"]
            result["evidence"] = ["gate passed"]
    run["landing"]["continuity"] = {
        "status": "preserved",
        "branch_ref": "refs/heads/"
        + run["integration"]["branch"].removeprefix("refs/heads/"),
        "head_sha": run["integration"]["integration_head_sha"],
        "reason": None,
    }


def valid_closeout_run(plan: dict[str, object]) -> dict[str, object]:
    """The canonical RUN staged for closeout: local-only, gates still planned."""
    run = valid_run(plan)
    run["landing"]["mode"] = "local_only"
    return run


def mark_complete(plan: dict[str, object], run: dict[str, object]) -> None:
    digest = plan_digest(plan)
    integration_head = run["integration"]["integration_head_sha"]
    batch_base = run["integration"]["batch_base_sha"]
    mission_ids = [mission["id"] for mission in plan["missions"]]
    worker_heads = {
        mission_id: head
        for mission_id, head in zip(mission_ids, (SHA_B, SHA_C), strict=True)
    }
    integrated_heads = {
        mission_id: head
        for mission_id, head in zip(
            mission_ids,
            (SHA_D, integration_head),
            strict=True,
        )
    }
    authorize_execution(run, mission_ids, status="complete")
    run["runtime_capabilities"].update(
        {
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": len(mission_ids),
            "runtime_adapter": {
                "provider": "codex",
                "available_drivers": ["subagents", "sequential_parent"],
                "detection_source": "fallback",
            },
        }
    )
    run["observed"]["runtime"].update(
        {
            "available_worker_slots": len(mission_ids),
            "isolation_capacity": len(mission_ids),
        }
    )
    graph_state = run.get("graph_state")
    if isinstance(graph_state, dict):
        node_attempts: dict[str, str] = {}
        mission_nodes: dict[str, dict[str, object]] = {}
        review_nodes: list[dict[str, object]] = []
        for index, node in enumerate(plan["graph"]["nodes"], start=1):
            node_id = node["id"]
            attempt_id = f"ATT-{index:02d}-{node_id}"
            node_attempts[node_id] = attempt_id
            state = graph_state["node_states"][node_id]
            state.update(
                {
                    "phase": "succeeded",
                    "attempts": 1,
                    "last_attempt_id": attempt_id,
                    "last_outcome": "pass",
                }
            )
            if node["kind"] == "mission":
                mission_nodes[node["ref"]] = node
                state["bound_worker_id"] = f"W-{node['ref']}"
            elif node["executor"] == "runtime_worker":
                review_nodes.append(node)
                state["bound_worker_id"] = f"RW-{node_id}"
        for edge in plan["graph"]["edges"]:
            graph_state["edge_states"][edge["id"]].update(
                {
                    "status": "traversed",
                    "traversals": 1,
                    "source_attempt_id": node_attempts[edge["from"]],
                }
            )

        run["workers"] = []
        for mission_id, node in mission_nodes.items():
            worker_id = f"W-{mission_id}"
            lease_id = f"LEASE-{mission_id}"
            worktree_path = f"C:/repo/worktrees/{mission_id.lower()}"
            branch_ref = f"refs/heads/codex/{mission_id.lower()}"
            worker_head = worker_heads[mission_id]
            run["workers"].append(
                {
                    "worker_id": worker_id,
                    "mission_id": mission_id,
                    "lease_id": lease_id,
                    "plan_revision": plan["revision"],
                    "plan_digest_sha256": digest,
                    "batch_base_sha": batch_base,
                    "worker_runtime": "subagent",
                    "workspace_mode": "parent_managed_worktree",
                    "completion_channel": "agent_result",
                    "runtime_binding": {
                        "provider": "codex",
                        "driver": "subagents",
                        "source": "host",
                        "model": None,
                        "reasoning_effort": None,
                        "option_source": "provider_default",
                    },
                    "task_thread_id": None,
                    "worktree_path": worktree_path,
                    "branch_ref": branch_ref,
                    "report_path": None,
                    "phase": "worker_passed",
                    "worker_head_sha": worker_head,
                }
            )
            run["observed"]["git"]["worktrees"].append(
                {
                    "path": worktree_path,
                    "branch_ref": branch_ref,
                    "head_sha": worker_head,
                    "managed_by": "parent",
                    "dirty": False,
                }
            )
            run["mission_states"][mission_id].update(
                {
                    "phase": "integrated",
                    "lease_id": lease_id,
                    "lease_plan_revision": plan["revision"],
                    "lease_plan_digest_sha256": digest,
                    "worker_id": worker_id,
                    "base_sha": batch_base,
                    "head_sha": worker_head,
                    "integration_gate": "PASS",
                    "integrated_sha": integrated_heads[mission_id],
                }
            )
            run["attempt_log"].append(
                {
                    "attempt_id": node_attempts[node["id"]],
                    "mission_id": mission_id,
                    "task_id": None,
                    "lease_id": lease_id,
                    "kind": "worker_verifier",
                    "result": "PASS",
                    "evidence": [],
                }
            )

        run["review_workers"] = []
        for node in review_nodes:
            review = node["review"]
            mission_id = review["mission_ids"][0]
            node_id = node["id"]
            mission_worker = next(
                worker
                for worker in run["workers"]
                if worker["mission_id"] == mission_id
            )
            run["review_workers"].append(
                {
                    "worker_id": f"RW-{node_id}",
                    "node_id": node_id,
                    "attempt_id": node_attempts[node_id],
                    "plan_revision": plan["revision"],
                    "plan_digest_sha256": digest,
                    "graph_revision": graph_state["graph_revision"],
                    "reviewed_sha": run["mission_states"][mission_id]["head_sha"],
                    "review_path": mission_worker["worktree_path"],
                    "worker_runtime": "parent",
                    "completion_channel": "agent_result",
                    "runtime_binding": {
                        "provider": "codex",
                        "driver": "sequential_parent",
                        "source": "host",
                        "model": None,
                        "reasoning_effort": None,
                        "option_source": "provider_default",
                    },
                    "task_thread_id": None,
                    "report_path": None,
                    "phase": "worker_passed",
                    "outcome": "pass",
                    "findings": [],
                }
            )

    worker_paths = [
        f"worktree:{worker['worktree_path']}" for worker in run["workers"]
    ]
    worker_branches = [
        f"branch:{worker['branch_ref']}" for worker in run["workers"]
    ]
    worker_targets = [f"worker:{worker['worker_id']}" for worker in run["workers"]]
    authorize_action(
        run,
        "spawn_subagents",
        mission_ids,
        worker_targets,
    )
    authorize_action(
        run,
        "create_local_worktrees",
        mission_ids,
        worker_paths,
    )
    authorize_action(
        run,
        "create_local_branches",
        mission_ids,
        worker_branches,
    )
    authorize_action(
        run,
        "create_local_commits",
        mission_ids,
        worker_branches,
    )
    authorize_action(
        run,
        "integrate_locally",
        mission_ids,
        [f"branch:{run['integration']['branch']}"],
    )

    superseded = {
        item["id"]
        for current_mission in plan["missions"]
        for item in current_mission["tasks"]
        if item["replaced_by"]
    }
    for task_id, state in run["task_states"].items():
        state["phase"] = "superseded" if task_id in superseded else "mission_recorded"
        state["verifier_status"] = "PASS"
        if state["phase"] == "mission_recorded":
            mission_id = task_id.split("/", 1)[0]
            worker = next(
                worker
                for worker in run["workers"]
                if worker["mission_id"] == mission_id
            )
            state["commit_sha"] = worker["worker_head_sha"]
            attempt_id = f"ATT-{task_id.replace('/', '-')}"
            run["attempt_log"].append(
                {
                    "attempt_id": attempt_id,
                    "mission_id": mission_id,
                    "task_id": task_id,
                    "lease_id": worker["lease_id"],
                    "kind": "task_verifier",
                    "result": "PASS",
                    "evidence": [],
                }
            )

    execution_index = 1
    for mission in plan["missions"]:
        mission_id = mission["id"]
        worker = next(
            worker
            for worker in run["workers"]
            if worker["mission_id"] == mission_id
        )
        worker_attempt = next(
            attempt
            for attempt in run["attempt_log"]
            if attempt["mission_id"] == mission_id and attempt["task_id"] is None
        )
        for task_declaration in mission["tasks"]:
            task_id = task_declaration["id"]
            if run["task_states"][task_id]["phase"] != "mission_recorded":
                continue
            task_attempt = next(
                attempt
                for attempt in run["attempt_log"]
                if attempt["task_id"] == task_id
            )
            for declaration in task_declaration["verifiers"]:
                run["verifier_executions"].append(
                    retained_gate_execution(
                        plan,
                        run,
                        declaration,
                        layer="task",
                        execution_id=f"EXEC-TASK-{execution_index:02d}",
                        mission_id=mission_id,
                        task_id=task_id,
                        attempt_id=task_attempt["attempt_id"],
                        lease_id=worker["lease_id"],
                        head_sha=worker["worker_head_sha"],
                        checkout_role="worker",
                    )
                )
                execution_index += 1
        for declaration in mission["worker_verifiers"]:
            run["verifier_executions"].append(
                retained_gate_execution(
                    plan,
                    run,
                    declaration,
                    layer="worker",
                    execution_id=f"EXEC-WORKER-{execution_index:02d}",
                    mission_id=mission_id,
                    attempt_id=worker_attempt["attempt_id"],
                    lease_id=worker["lease_id"],
                    head_sha=worker["worker_head_sha"],
                    checkout_role="worker",
                )
            )
            execution_index += 1
        for declaration in mission["integration_verifiers"]:
            run["verifier_executions"].append(
                retained_gate_execution(
                    plan,
                    run,
                    declaration,
                    layer="mission_integration",
                    execution_id=f"EXEC-INTEGRATION-{execution_index:02d}",
                    mission_id=mission_id,
                    head_sha=run["mission_states"][mission_id]["integrated_sha"],
                )
            )
            execution_index += 1

    for layer, plan_key, run_key in (
        ("batch", "batch_verifiers", "batch_gate_results"),
        ("final", "final_gates", "final_gate_results"),
    ):
        for index, (declaration, result) in enumerate(
            zip(plan[plan_key], run.get(run_key, [])),
            start=1,
        ):
            execution = retained_gate_execution(
                plan,
                run,
                declaration,
                layer=layer,
                execution_id=f"EXEC-{layer.upper()}-{index:02d}",
            )
            run["verifier_executions"].append(execution)
            result["status"] = "PASS"
            result["head_sha"] = integration_head
            result["evidence"] = [execution["evidence_key"]]
    # A complete run keeps its branch at the head it verified, so the user can
    # read it and land it.
    run["landing"]["continuity"] = {
        "status": "preserved",
        "branch_ref": "refs/heads/" + run["integration"]["branch"].removeprefix("refs/heads/"),
        "head_sha": run["integration"]["integration_head_sha"],
        "reason": None,
    }


def retained_gate_execution(
    plan: dict[str, object],
    run: dict[str, object],
    declaration: dict[str, object],
    *,
    layer: str,
    execution_id: str,
    mission_id: str | None = None,
    task_id: str | None = None,
    attempt_id: str | None = None,
    lease_id: str | None = None,
    head_sha: str | None = None,
    checkout_role: str = "integration",
) -> dict[str, object]:
    changed_files: list[str] = []
    execution_head = head_sha or run["integration"]["integration_head_sha"]
    context = {
        "run_id": run["run_id"],
        "plan_revision": run["plan"]["revision"],
        "plan_digest_sha256": run["plan"]["digest_sha256"],
        "graph_revision": run["graph_state"]["graph_revision"],
        "batch_base_sha": run["integration"]["batch_base_sha"],
        "head_sha": execution_head,
        "changed_files": changed_files,
        "trust_domain": "parent_local",
        "checkout_role": checkout_role,
        "checkout_dirty": False,
        "cache_safe": False,
        "layer": layer,
        "mission_id": mission_id,
        "task_id": task_id,
        "attempt_id": attempt_id,
        "lease_id": lease_id,
    }
    declared_cache = declaration.get(
        "cache",
        {"mode": "disabled", "environment_keys": []},
    )
    normalized_verifier = {
        "id": declaration["id"],
        "cwd": declaration["cwd"],
        "argv": declaration["argv"],
        "pass_signal": declaration["pass_signal"],
        "cache": declared_cache,
    }
    key_document = {
        "protocol": "harness-verifier-execution-v1",
        "verifier_id": declaration["id"],
        "layer": layer,
        "mission_id": mission_id,
        "task_id": task_id,
        "attempt_id": attempt_id,
        "lease_id": lease_id,
        "run_id": context["run_id"],
        "plan_revision": context["plan_revision"],
        "plan_digest_sha256": context["plan_digest_sha256"],
        "graph_revision": context["graph_revision"],
        "batch_base_sha": context["batch_base_sha"],
        "head_sha": context["head_sha"],
        "changed_files_digest": hashlib.sha256(b"[]").hexdigest(),
        "trust_domain": context["trust_domain"],
        "checkout_role": context["checkout_role"],
        "checkout_dirty": context["checkout_dirty"],
        "cache_safe": context["cache_safe"],
        "cwd": declaration["cwd"],
        "argv": declaration["argv"],
        "pass_signal": declaration["pass_signal"],
        "cache_mode": declared_cache["mode"],
        "environment_keys": sorted(declared_cache["environment_keys"]),
        "platform": {"system": "test", "machine": "test"},
        "executable_identity": {
            "path": "C:/python",
            "size": 1,
            "mtime_ns": 1,
            "device": 1,
            "inode": 1,
        },
        "environment_digests": {},
    }
    execution_key = hashlib.sha256(
        json.dumps(
            key_document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    empty_digest = hashlib.sha256(b"").hexdigest()
    return {
        "execution_id": execution_id,
        "verifier_id": declaration["id"],
        "layer": layer,
        "mission_id": mission_id,
        "task_id": task_id,
        "attempt_id": attempt_id,
        "lease_id": lease_id,
        "protocol": "harness-verifier-execution-v1",
        "execution_key": execution_key,
        "evidence_key": execution_key,
        "key_document": key_document,
        "verifier": normalized_verifier,
        "context": context,
        "status": "PASS",
        "exit_code": 0,
        "cache_status": "bypassed",
        "cache_reason": "cache_disabled",
        "duration_ms": 1,
        "metrics": {"executed": 1, "reused": 0},
        "stdout_sha256": empty_digest,
        "stderr_sha256": empty_digest,
        "evidence_paths": [],
    }








def authorize_execution(
    run: dict[str, object],
    mission_ids: list[str],
    *,
    status: str = "running",
    plan: dict[str, object] | None = None,
    digest: str | None = None,
) -> None:
    """Authorize execution for exactly `mission_ids`.

    The scope always binds the plan revision and digest the RUN records, since
    v10 requires it. `plan`/`digest` override that for the drift tests.
    """
    run_plan = run.get("plan", {})
    scope: dict[str, object] = {
        "run_id": run["run_id"],
        "plan_revision": plan["revision"] if plan is not None else run_plan.get("revision"),
        "plan_digest_sha256": digest if digest is not None else run_plan.get("digest_sha256"),
        "mission_ids": mission_ids,
        "expires_when": "run_complete",
    }
    # An authorized run must keep its branch, so continuity is planned by then.
    continuity = run.get("landing", {}).get("continuity")
    if continuity is None:
        run["landing"]["continuity"] = {
            "status": "planned",
            "branch_ref": "refs/heads/" + run["integration"]["branch"].removeprefix("refs/heads/"),
            "head_sha": None,
            "reason": None,
        }
    run.update(
        {
            "status": status,
            "intent": "plan-then-execute",
            "plan_readiness": "ready",
            "execution_authorized": True,
            "execution_authorization_source": "user requested execution",
            "execution_authorization_scope": scope,
        }
    )


def authorize_action(
    run: dict[str, object],
    action: str,
    mission_ids: list[str],
    targets: list[str],
) -> None:
    run["authorizations"][action] = {
        "authorized": True,
        "source": "user requested lifecycle action",
        "scope": {
            "run_id": run["run_id"],
            "plan_revision": run["plan"]["revision"],
            "plan_digest_sha256": run["plan"]["digest_sha256"],
            "mission_ids": mission_ids,
            "targets": targets,
        },
        "expires_when": "run_complete",
    }

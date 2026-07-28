#!/usr/bin/env python3
"""Typed graph orchestration tests (host-native provider binding only)."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import mission_dependencies  # noqa: E402
from harness_graph import _validate_graph  # noqa: E402
from harness_manifest import (  # noqa: E402
    AUTHORIZATION_KEYS,
    load_plan,
    load_run,
    plan_digest,
    topological_levels,
    validate_plan,
    validate_run,
)
from select_ready_nodes import (  # noqa: E402
    GraphSelectionError,
    _current_authorized_head,
    _runtime_binding,
    select_ready_nodes,
)
from test_harness_manifest import (  # noqa: E402
    authorize_execution,
    mark_complete,
    valid_plan,
    valid_run,
)
from validate_node_result import validate_node_result  # noqa: E402


def graph_node(
    node_id: str,
    kind: str,
    ref: str,
    executor: str,
    outcomes: list[str],
    *,
    providers: list[str] | None = None,
    preferred: str | None = None,
    provider_options: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": node_id,
        "kind": kind,
        "ref": ref,
        "executor": executor,
        "allowed_outcomes": outcomes,
        "max_attempts": 2,
        "runtime": (
            {
                "preferred_provider": preferred,
                "allowed_providers": providers or ["codex", "claude_code"],
                **({"provider_options": provider_options} if provider_options is not None else {}),
            }
            if executor == "runtime_worker"
            else None
        ),
    }


def lifecycle_node(ref: str, **extra: object) -> dict[str, object]:
    """A minimal harness-parent lifecycle node; `extra` sets `target` when given."""
    return {
        "id": "N-LIFECYCLE",
        "kind": "lifecycle",
        "ref": ref,
        "executor": "harness_parent",
        "allowed_outcomes": ["pass", "blocked"],
        "max_attempts": 1,
        "runtime": None,
        **extra,
    }


def start_mission(
    run: dict[str, object],
    plan: dict[str, object],
    digest: str,
    mission_id: str = "M1",
    *,
    base_sha: str | None = None,
) -> None:
    """Put one mission's graph node and mission state into the running shape."""
    run["graph_state"]["node_states"][f"N-{mission_id}"].update(
        {
            "phase": "running",
            "attempts": 1,
            "last_attempt_id": f"ATT-N-{mission_id}-1",
            "bound_worker_id": f"W-{mission_id}",
        }
    )
    run["mission_states"][mission_id].update(
        {
            "phase": "worker_running",
            "lease_id": f"LEASE-{mission_id}-1",
            "lease_plan_revision": plan["revision"],
            "lease_plan_digest_sha256": digest,
            "worker_id": f"W-{mission_id}",
            "base_sha": (
                base_sha if base_sha is not None else run["integration"]["batch_base_sha"]
            ),
        }
    )


def one_node_graph_errors(
    node: dict[str, object],
    missions: dict[str, object] | None = None,
    **kwargs: object,
) -> list[str]:
    """Validate a single-node, edgeless graph and return the errors it raised."""
    errors: list[str] = []
    _validate_graph(
        errors,
        {"entry_nodes": [node["id"]], "nodes": [node], "edges": []},
        missions or {},
        set(),
        require_bounded_review_repair=True,
        **kwargs,
    )
    return errors


def valid_graph_plan() -> dict[str, object]:
    plan = valid_plan()
    plan["schema_version"] = 4
    plan["required_reviews"] = []
    for source in plan["sources"]:
        source.update({"content_sha256": "f" * 64, "source_revision": None})
    for item in plan["missions"]:
        item.pop("depends_on")
    plan["graph"] = {
        "entry_nodes": ["N-M1"],
        "nodes": [
            graph_node(
                "N-M1",
                "mission",
                "M1",
                "runtime_worker",
                ["pass", "retryable_failure", "blocked", "contract_gap"],
            ),
            graph_node(
                "N-M2",
                "mission",
                "M2",
                "runtime_worker",
                ["pass", "retryable_failure", "blocked", "contract_gap"],
            ),
        ],
        "edges": [
            {
                "id": "E-M1-M2",
                "kind": "dependency",
                "from": "N-M1",
                "to": "N-M2",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        ],
    }
    coverage_review = graph_node(
        "N-COVERAGE-REVIEW",
        "verifier",
        "batch",
        "runtime_worker",
        ["pass", "fix_required", "retryable_failure", "blocked", "contract_gap"],
    )
    coverage_review["review"] = {
        "type": "backend_code",
        "mission_ids": ["M1", "M2"],
        "scope": ["src/a/**", "src/ab/**"],
        "required_evidence": ["reviewed_sha", "findings"],
    }
    plan["graph"]["nodes"].append(coverage_review)
    plan["graph"]["edges"].append(
        {
            "id": "E-M2-COVERAGE-REVIEW",
            "kind": "dependency",
            "from": "N-M2",
            "to": coverage_review["id"],
            "on_outcomes": ["pass"],
            "max_traversals": None,
        }
    )
    return plan


def detach_mission_edges(plan: dict[str, object]) -> None:
    """Make M1 and M2 independent roots while keeping the review node wired."""
    plan["graph"]["entry_nodes"] = ["N-M1", "N-M2"]
    plan["graph"]["edges"] = [
        edge for edge in plan["graph"]["edges"] if edge["to"] == "N-COVERAGE-REVIEW"
    ]


def mission_nodes(plan: dict[str, object]) -> list[dict[str, object]]:
    return [node for node in plan["graph"]["nodes"] if node["kind"] == "mission"]


def valid_graph_run(plan: dict[str, object]) -> dict[str, object]:
    run = valid_run(plan)
    run["observed"]["captured_at"] = "2026-07-25T00:00:00Z"
    run["schema_version"] = 8
    run["authorizations"] = {
        key: {"authorized": False, "source": None} for key in AUTHORIZATION_KEYS
    }
    run["review_workers"] = []
    run["graph_state"] = {
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
    }
    return run


def authorize(
    run: dict[str, object], action: str, mission_ids: list[str], target: str
) -> None:
    run["authorizations"][action] = {
        "authorized": True,
        "source": "user requested graph execution and Claude trial",
        "scope": {
            "run_id": run["run_id"],
            "mission_ids": mission_ids,
            "targets": [target],
        },
        "expires_when": "run_complete",
    }


def add_development_release_target(
    plan: dict[str, object], run: dict[str, object]
) -> dict[str, object]:
    """Give a template-built pair the optional preview environment.

    The canonical templates are main-only: one production target and no
    persistent integration branch. Tests that exercise the other supported
    shape — a repository with its own integration branch and a preview
    environment watching it — declare that target themselves.
    """
    development = copy.deepcopy(
        next(
            item
            for item in plan["release"]["targets"]
            if item["stage"] == "production"
        )
    )
    development.update(
        {
            "id": "web-development",
            "stage": "development",
            "source": "integration_head",
            "channel": "workers-development",
            "data_mode": "isolated_non_production",
            "trigger": "manual",
            "prerequisites": ["current_head_ci"],
        }
    )
    # Verifier and command IDs are globally unique across the PLAN.
    development["commands"]["build"]["id"] = "build-web-development"
    development["smoke_verifiers"][0]["id"] = "smoke-web-development"
    plan["release"]["targets"].insert(0, development)
    run["targets"]["web-development"] = copy.deepcopy(run["targets"]["web-production"])
    run["integration"]["branch"] = "refs/heads/development"
    return development


def lifecycle_v10_plan_and_run(
    action: str, target: str | None
) -> tuple[dict[str, object], dict[str, object]]:
    """A valid PLAN schema v5 / RUN schema v10 pair with one added lifecycle node.

    Built on the canonical templates (already exercised end-to-end by
    test_schema_v5_v10_contract.py) rather than a hand-built v10 fixture,
    because schema v10 pulls in release targets, plan/run digest binding, and
    other fields a minimal fixture would otherwise have to reconstruct from
    scratch. The new node has no edges and is its own entry node, so it does
    not disturb the template's existing graph reachability or mission wiring.
    """
    root = SCRIPTS_DIR.parent
    plan = load_plan(root / "assets/templates/HARNESS_PLAN.template.md")
    run = load_run(root / "assets/templates/MISSION_RUNBOOK.template.md")
    node: dict[str, object] = {
        "id": "N-LIFECYCLE",
        "kind": "lifecycle",
        "ref": action,
        "executor": "harness_parent",
        "allowed_outcomes": ["pass", "blocked"],
        "max_attempts": 1,
        "runtime": None,
    }
    if target is not None:
        node["target"] = target
    plan["graph"]["nodes"].append(node)
    plan["graph"]["entry_nodes"].append("N-LIFECYCLE")
    run["graph_state"]["node_states"]["N-LIFECYCLE"] = {
        "phase": "dormant",
        "attempts": 0,
        "last_attempt_id": None,
        "last_outcome": None,
        "bound_worker_id": None,
        "blockers": [],
    }
    digest = plan_digest(plan)
    run["plan"]["digest_sha256"] = digest
    authorize_execution(run, ["*"], status="ready", plan=plan, digest=digest)
    run["observed"]["captured_at"] = "2026-07-25T00:00:00Z"
    run["observed"]["git"].update(
        {
            "parent_worktree_path": "C:/repo",
            "parent_branch": "refs/heads/development",
            "parent_head_sha": "a" * 40,
            "parent_dirty": False,
        }
    )
    run["integration"].update(
        {
            "batch_base_sha": "a" * 40,
            "integration_head_sha": "a" * 40,
        }
    )
    run["runtime_capabilities"]["permission_boundary"] = {
        "selected_mode": "ask_for_approval",
        "profile_name": None,
        "approval_policy": "on-request",
        "filesystem_scope": "workspace",
        "network_scope": "filtered",
        "local_binding": "allowed",
        "worker_inheritance": "inherited",
        "status": "ready",
    }
    return plan, run


class GraphManifestTests(unittest.TestCase):






    def test_lifecycle_node_target_rejects_wildcard_and_bad_format(self) -> None:
        for target in ("*", "not-a-target", ""):
            with self.subTest(target=target):
                errors = one_node_graph_errors(lifecycle_node("push", target=target))
                self.assertTrue(
                    any(
                        "must be null or an exact non-wildcard authorization target" in error
                        for error in errors
                    ),
                    f"expected a target error for {target!r} in {errors!r}",
                )

    def test_lifecycle_node_target_is_optional_for_backward_compatibility(self) -> None:
        # A PLAN authored before the `target` field existed omits it entirely;
        # that must stay valid so this addition never breaks an already-valid
        # PLAN (select_ready_nodes.py falls back to the "*" default for it).
        self.assertEqual([], one_node_graph_errors(lifecycle_node("push")))

    def test_target_field_is_rejected_outside_lifecycle_nodes(self) -> None:
        errors = one_node_graph_errors(
            {
                "id": "N-M1",
                "kind": "mission",
                "ref": "M1",
                "executor": "runtime_worker",
                "allowed_outcomes": ["pass", "retryable_failure", "blocked"],
                "max_attempts": 1,
                "runtime": {
                    "preferred_provider": None,
                    "allowed_providers": ["codex"],
                },
                "target": "branch:codex/example",
            },
            {"M1": {"id": "M1"}},
        )
        self.assertTrue(
            any(
                "must be omitted unless the node is lifecycle" in error
                for error in errors
            ),
            errors,
        )

    def test_plan_v4_and_v5_project_the_same_graph_dependencies(self) -> None:
        plan = valid_graph_plan()
        expected = mission_dependencies(plan)
        self.assertTrue(any(expected.values()))

        plan["schema_version"] = 5

        self.assertEqual(expected, mission_dependencies(plan))

    def test_schema_v4_and_v8_are_valid_and_keep_mission_topology(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)

        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_run(plan, run))
        self.assertEqual({"M1": 0, "M2": 1}, topological_levels(plan))

    def test_workflow_run_binding_is_optional_and_validated(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        start_mission(run, plan, digest)
        run["workflow_runs"] = [
            {
                "workflow_run_id": "wf_test",
                "workflow_task_id": "task-test",
                "resume_from_run_id": None,
                "script_path": "assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js",
                "script_sha256": "c" * 64,
                "run_id": run["run_id"],
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "graph_revision": run["graph_state"]["graph_revision"],
                "batch_base_sha": run["integration"]["batch_base_sha"],
                "node_ids": ["N-M1"],
                "attempt_ids": {"N-M1": "ATT-N-M1-1"},
                "provider": "claude_code",
                "driver": "dynamic_workflow",
                "tool_profile": "mission_write",
                "status": "running",
                "result_evidence": [],
                "metrics": {"duration_ms": None, "token_count": None},
            }
        ]

        self.assertEqual([], validate_run(plan, run))
        run["workflow_runs"][0]["batch_base_sha"] = "b" * 40
        self.assertTrue(
            any("running workflow must match RUN" in error for error in validate_run(plan, run))
        )
        run["workflow_runs"][0]["batch_base_sha"] = run["integration"]["batch_base_sha"]
        run["workflow_runs"][0]["attempt_ids"]["N-M1"] = "ATT-STALE"
        self.assertTrue(
            any("active running node attempt" in error for error in validate_run(plan, run))
        )
        run["workflow_runs"][0]["attempt_ids"]["N-M1"] = "ATT-N-M1-1"
        run["status"] = "complete"
        self.assertTrue(
            any("complete RUN cannot retain a running workflow" in error for error in validate_run(plan, run))
        )
        run["status"] = "draft"
        run["workflow_runs"][0]["tool_profile"] = "visual_review_readonly"
        self.assertTrue(
            any("does not match its review node types" in error for error in validate_run(plan, run))
        )
        run["workflow_runs"][0].update(
            {
                "status": "completed",
                "tool_profile": "mission_write",
                "node_ids": ["N-HISTORICAL"],
                "attempt_ids": {"N-HISTORICAL": "ATT-HISTORICAL-1"},
            }
        )
        self.assertFalse(
            any("unknown graph nodes" in error for error in validate_run(plan, run))
        )

    def test_workflow_runs_are_claude_code_only(self) -> None:
        # A Codex-hosted graph RUN never produces workflow_runs entries: the
        # guarded external-Codex-agent workflow driver is fully removed, and
        # provider "codex" has no allowed workflow driver at all anymore.
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["runtime"] = {
            "preferred_provider": "claude_code",
            "allowed_providers": ["claude_code"],
        }
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        start_mission(run, plan, digest)
        workflow = {
            "workflow_run_id": "wf_test",
            "workflow_task_id": "task-test",
            "resume_from_run_id": None,
            "script_path": "assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js",
            "script_sha256": "d" * 64,
            "run_id": run["run_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "graph_revision": run["graph_state"]["graph_revision"],
            "batch_base_sha": run["integration"]["batch_base_sha"],
            "node_ids": ["N-M1"],
            "attempt_ids": {"N-M1": "ATT-N-M1-1"},
            "provider": "claude_code",
            "driver": "dynamic_workflow",
            "tool_profile": "mission_write",
            "status": "running",
            "result_evidence": [],
            "metrics": {"duration_ms": None, "token_count": None},
        }
        run["workflow_runs"] = [workflow]

        self.assertEqual([], validate_run(plan, run))

        codex_workflow = copy.deepcopy(run)
        codex_workflow["workflow_runs"][0]["provider"] = "codex"
        self.assertTrue(
            any(
                "unsupported workflow provider" in error
                for error in validate_run(plan, codex_workflow)
            )
        )

        codex_driver = copy.deepcopy(run)
        codex_driver["workflow_runs"][0]["provider"] = "codex"
        codex_driver["workflow_runs"][0]["driver"] = "app_threads"
        self.assertTrue(
            any(
                "unsupported workflow provider" in error
                for error in validate_run(plan, codex_driver)
            )
        )

    def test_one_workflow_run_may_cover_nodes_with_different_models(self) -> None:
        # workflow_runs no longer carries its own model/reasoning_effort: each
        # node's resolved model already lives on its own workers[]/
        # review_workers[] runtime_binding, so one live Workflow invocation
        # may freely mix models across the node_ids it covers.
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["runtime"]["allowed_providers"] = ["claude_code"]
        plan["graph"]["nodes"][0]["runtime"]["provider_options"] = {
            "claude_code": {"model": "sonnet", "reasoning_effort": None}
        }
        plan["graph"]["nodes"][1]["runtime"]["allowed_providers"] = ["claude_code"]
        plan["graph"]["nodes"][1]["runtime"]["provider_options"] = {
            "claude_code": {"model": "haiku", "reasoning_effort": None}
        }
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        start_mission(run, plan, digest, "M1")
        start_mission(run, plan, digest, "M2")
        run["workflow_runs"] = [
            {
                "workflow_run_id": "wf_test",
                "workflow_task_id": "task-test",
                "resume_from_run_id": None,
                "script_path": "assets/templates/CLAUDE_GRAPH_WORKFLOW.template.js",
                "script_sha256": "d" * 64,
                "run_id": run["run_id"],
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "graph_revision": run["graph_state"]["graph_revision"],
                "batch_base_sha": run["integration"]["batch_base_sha"],
                "node_ids": ["N-M1", "N-M2"],
                "attempt_ids": {"N-M1": "ATT-N-M1-1", "N-M2": "ATT-N-M2-1"},
                "provider": "claude_code",
                "driver": "dynamic_workflow",
                "tool_profile": "mission_write",
                "status": "running",
                "result_evidence": [],
                "metrics": {"duration_ms": None, "token_count": None},
            }
        ]

        self.assertEqual([], validate_run(plan, run))

        with_model_key = copy.deepcopy(run)
        with_model_key["workflow_runs"][0]["model"] = "sonnet"
        self.assertTrue(
            any(
                "unknown keys: model" in error
                for error in validate_run(plan, with_model_key)
            )
        )

    def test_schema_v4_and_v9_closeout_preserves_graph_state(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"].append(
            graph_node(
                "N-FINAL",
                "verifier",
                "final",
                "local_command",
                ["pass", "retryable_failure"],
            )
        )
        plan["graph"]["edges"].append(
            {
                "id": "E-M2-FINAL",
                "kind": "dependency",
                "from": "N-M2",
                "to": "N-FINAL",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        run = valid_graph_run(plan)
        run["schema_version"] = 9
        run["batch_gate_results"] = [
            {
                "id": gate["id"],
                "status": "planned",
                "head_sha": None,
                "evidence": [],
            }
            for gate in plan["batch_verifiers"]
        ]
        run["final_gate_results"] = [
            {
                "id": gate["id"],
                "status": "planned",
                "head_sha": None,
                "evidence": [],
            }
            for gate in plan["final_gates"]
        ]
        run["ui_evidence"] = []
        run["landing"]["mode"] = "local_only"
        mark_complete(plan, run)
        errors = validate_run(plan, run)
        self.assertTrue(
            any("every node to succeed, skip, or be superseded" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("every edge to be terminal" in error for error in errors),
            errors,
        )
        for index, node in enumerate(plan["graph"]["nodes"], start=1):
            run["graph_state"]["node_states"][node["id"]].update(
                {
                    "phase": "succeeded",
                    "attempts": 1,
                    "last_attempt_id": f"ATTEMPT-{index}",
                    "last_outcome": "pass",
                }
            )
        attempt_by_node = {
            node["id"]: f"ATTEMPT-{index}"
            for index, node in enumerate(plan["graph"]["nodes"], start=1)
        }
        for edge in plan["graph"]["edges"]:
            run["graph_state"]["edge_states"][edge["id"]].update(
                {
                    "status": "traversed",
                    "traversals": 1,
                    "source_attempt_id": attempt_by_node[edge["from"]],
                }
            )

        self.assertEqual([], validate_run(plan, run))
        run["graph_state"]["node_states"]["N-FINAL"].update(
            {
                "phase": "failed",
                "last_outcome": "retryable_failure",
            }
        )
        self.assertTrue(
            any(
                "every node to succeed, skip, or be superseded" in error
                for error in validate_run(plan, run)
            )
        )
        run["graph_state"]["node_states"]["N-FINAL"].update(
            {
                "phase": "succeeded",
                "last_outcome": "retryable_failure",
            }
        )
        self.assertTrue(
            any(
                "every succeeded node to have pass outcome" in error
                for error in validate_run(plan, run)
            )
        )

    def test_malformed_graph_scalars_return_errors_without_crashing(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["id"] = []
        self.assertTrue(any("flat uppercase identifier" in error for error in validate_plan(plan)))

        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["kind"] = []
        self.assertTrue(any("unsupported value" in error for error in validate_plan(plan)))

        for field, location in (
            ("ref", "nodes[0]"),
            ("id", "edges[0]"),
            ("from", "edges[0]"),
            ("to", "edges[0]"),
        ):
            for malformed in ([], {}):
                with self.subTest(field=field, malformed=type(malformed).__name__):
                    plan = valid_graph_plan()
                    collection = (
                        plan["graph"]["nodes"]
                        if location.startswith("nodes")
                        else plan["graph"]["edges"]
                    )
                    collection[0][field] = malformed
                    errors = validate_plan(plan)
                    self.assertTrue(any(f"plan.graph.{location}.{field}" in error for error in errors))

        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        run["graph_state"] = []
        self.assertTrue(any("run.graph_state" in error for error in validate_run(plan, run)))

        for field in ("phase", "last_outcome"):
            for malformed in ([], {}):
                with self.subTest(field=field, malformed=type(malformed).__name__):
                    run = valid_graph_run(plan)
                    run["graph_state"]["node_states"]["N-M1"][field] = malformed
                    errors = validate_run(plan, run)
                    self.assertTrue(
                        any(f"run.graph_state.node_states.N-M1.{field}" in error for error in errors)
                    )

        edge_id = plan["graph"]["edges"][0]["id"]
        for malformed in ([], {}):
            with self.subTest(field="status", malformed=type(malformed).__name__):
                run = valid_graph_run(plan)
                run["graph_state"]["edge_states"][edge_id]["status"] = malformed
                errors = validate_run(plan, run)
                self.assertTrue(
                    any(
                        f"run.graph_state.edge_states.{edge_id}.status" in error
                        for error in errors
                    )
                )

    def test_schema_v4_source_content_is_bound_into_the_plan_digest(self) -> None:
        plan = valid_graph_plan()
        original_digest = plan_digest(plan)
        plan["sources"][0]["content_sha256"] = "e" * 64

        self.assertNotEqual(original_digest, plan_digest(plan))
        plan["sources"][0]["content_sha256"] = None
        plan["sources"][0]["source_revision"] = None
        self.assertTrue(
            any("require content_sha256 or source_revision" in error for error in validate_plan(plan))
        )

    def test_runtime_nodes_require_a_declared_workflow_failure_outcome(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["allowed_outcomes"] = ["pass"]

        self.assertTrue(
            any(
                "runtime or parent execution requires retryable_failure or blocked" in error
                for error in validate_plan(plan)
            )
        )

    def test_required_review_type_needs_a_matching_runtime_review_node(self) -> None:
        plan = valid_graph_plan()
        plan["required_reviews"] = ["frontend_code"]

        self.assertTrue(
            any("missing runtime review nodes: frontend_code" in error for error in validate_plan(plan))
        )

    def test_provider_options_validate_and_bind_model_policy(self) -> None:
        plan = valid_graph_plan()
        node = plan["graph"]["nodes"][0]
        node["runtime"]["provider_options"] = {
            "codex": {
                "model": "gpt-5.6-terra",
                "reasoning_effort": "medium",
            },
            "claude_code": {
                "model": "sonnet",
                "reasoning_effort": None,
            },
        }
        self.assertEqual([], validate_plan(plan))

        runtime = valid_graph_run(plan)["runtime_capabilities"]
        runtime["runtime_adapter"].update(
            {
                "provider": "codex",
                "available_drivers": ["app_threads", "sequential_parent"],
                "detection_source": "observed",
            }
        )
        binding = _runtime_binding(node, runtime)
        self.assertEqual("gpt-5.6-terra", binding["model"])
        self.assertEqual("medium", binding["reasoning_effort"])
        self.assertEqual("plan_provider_options", binding["option_source"])

        node["runtime"]["provider_options"]["claude_code"]["reasoning_effort"] = "high"
        self.assertEqual([], validate_plan(plan))
        node["runtime"]["provider_options"]["generic"] = {
            "model": None,
            "reasoning_effort": "high",
        }
        node["runtime"]["allowed_providers"].append("generic")
        self.assertTrue(any("supports selectable effort" in error for error in validate_plan(plan)))

    def test_run_worker_binding_must_match_plan_provider_options(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["runtime"]["provider_options"] = {
            "codex": {
                "model": "gpt-5.6-terra",
                "reasoning_effort": "medium",
            }
        }
        run = valid_graph_run(plan)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
            }
        )
        run["runtime_capabilities"]["runtime_adapter"].update(
            {
                "provider": "codex",
                "available_drivers": ["app_threads", "sequential_parent"],
                "detection_source": "observed",
            }
        )
        run["workers"].append(
            {
                "worker_id": "W-M1",
                "mission_id": "M1",
                "lease_id": "LEASE-M1",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "batch_base_sha": "a" * 40,
                "worker_runtime": "app_task",
                "workspace_mode": "app_managed_worktree",
                "completion_channel": "thread_poll",
                "runtime_binding": {
                    "provider": "codex",
                    "driver": "app_threads",
                    "source": "host",
                    "model": "gpt-5.6-terra",
                    "reasoning_effort": "medium",
                    "option_source": "plan_provider_options",
                },
                "task_thread_id": None,
                "worktree_path": None,
                "branch_ref": None,
                "report_path": None,
                "phase": "leased",
                "worker_head_sha": None,
            }
        )

        self.assertEqual([], validate_run(plan, run))
        run["workers"][0]["runtime_binding"]["reasoning_effort"] = "high"
        self.assertTrue(
            any("must match the matching PLAN provider option" in error for error in validate_run(plan, run))
        )

    def test_codex_worker_runtime_binding_rejects_non_host_source(self) -> None:
        # The guarded external-Codex-agent driver/source pair is gone: a
        # worker's runtime_binding.source is always exactly "host", so the
        # old external_agent axis-consistency contract no longer applies.
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        worker = {
            "worker_id": "W-M1-CODEX",
            "mission_id": "M1",
            "lease_id": "LEASE-M1-CODEX",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "batch_base_sha": "a" * 40,
            "worker_runtime": "app_task",
            "workspace_mode": "app_managed_worktree",
            "completion_channel": "thread_poll",
            "runtime_binding": {
                "provider": "codex",
                "driver": "app_threads",
                "source": "host",
                "model": None,
                "reasoning_effort": None,
                "option_source": "provider_default",
            },
            "task_thread_id": "thread-codex-1",
            "worktree_path": None,
            "branch_ref": None,
            "report_path": None,
            "phase": "leased",
            "worker_head_sha": None,
        }
        run["workers"].append(worker)
        self.assertEqual([], validate_run(plan, run))

        run["workers"][0]["runtime_binding"]["source"] = "external_agent"
        self.assertTrue(
            any(
                "runtime_binding.source: has an unsupported value" in error
                for error in validate_run(plan, run)
            )
        )

    def test_dependency_cycles_and_unbounded_route_cycles_are_rejected(self) -> None:
        dependency_cycle = valid_graph_plan()
        dependency_cycle["graph"]["edges"].append(
            {
                "id": "E-M2-M1",
                "kind": "dependency",
                "from": "N-M2",
                "to": "N-M1",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        self.assertTrue(any("dependency cycle" in error for error in validate_plan(dependency_cycle)))

        route_cycle = valid_graph_plan()
        route_cycle["graph"] = {
            "entry_nodes": ["N-M1"],
            "nodes": [
                route_cycle["graph"]["nodes"][0],
                graph_node(
                    "N-REVIEW",
                    "verifier",
                    "batch",
                    "local_command",
                    ["pass", "fix_required", "blocked"],
                ),
                graph_node(
                    "N-FIX",
                    "verifier",
                    "final",
                    "local_command",
                    ["pass", "blocked"],
                ),
                graph_node(
                    "N-END",
                    "mission",
                    "M2",
                    "runtime_worker",
                    ["pass", "blocked"],
                ),
            ],
            "edges": [
                {
                    "id": "E-START",
                    "kind": "dependency",
                    "from": "N-M1",
                    "to": "N-REVIEW",
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
                {
                    "id": "E-FIX",
                    "kind": "route",
                    "from": "N-REVIEW",
                    "to": "N-FIX",
                    "on_outcomes": ["fix_required"],
                    "max_traversals": None,
                },
                {
                    "id": "E-REVIEW",
                    "kind": "route",
                    "from": "N-FIX",
                    "to": "N-REVIEW",
                    "on_outcomes": ["pass"],
                    "max_traversals": 2,
                },
                {
                    "id": "E-EXIT",
                    "kind": "route",
                    "from": "N-REVIEW",
                    "to": "N-END",
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
            ],
        }
        errors = validate_plan(route_cycle)
        self.assertTrue(any("route cycles require an explicit traversal bound" in error for error in errors))

    def test_harness_parent_mission_is_deferred_without_write_isolation(self) -> None:
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["executor"] = "harness_parent"
        plan["graph"]["nodes"][0]["runtime"] = None
        run = valid_graph_run(plan)
        authorize_execution(run, ["M1"])

        run["observed"]["runtime"].update(
            {"available_worker_slots": 0, "isolation_capacity": 0}
        )

        result = select_ready_nodes(plan, run)

        self.assertEqual([], result["dispatchable_nodes"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("workspace_not_isolated", deferred["N-M1"])

    def test_execution_authorization_requires_review_coverage_per_write_scope(self) -> None:
        # contract-and-traceability.md requires every mission write scope to be
        # covered by a review-type node regardless of landing.mode. local_only
        # gets no GitHub review, so an uncovered scope means no review at all.
        # The gate is execution authorization, not plan structure: an upgraded
        # v3 projection stays a valid PLAN, it just cannot be executed until
        # the review nodes are authored.
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        authorize_execution(run, ["M1", "M2"])
        self.assertEqual(validate_run(plan, run), [])

        uncovered = valid_graph_plan()
        review = next(
            node for node in uncovered["graph"]["nodes"] if node["id"] == "N-COVERAGE-REVIEW"
        )
        review["review"]["mission_ids"] = ["M1"]
        errors = validate_run(uncovered, run)
        self.assertTrue(
            any(
                "these missions have a write scope and no review node: M2" in error
                for error in errors
            ),
            f"expected an uncovered-M2 error in {errors!r}",
        )

        # An unauthorized run is still valid: the plan may legitimately be a
        # draft that has not authored its review nodes yet.
        draft = dict(run)
        draft["execution_authorized"] = False
        draft["execution_authorization_source"] = None
        draft["execution_authorization_scope"] = None
        draft["status"] = "planning"
        self.assertEqual(
            [
                error
                for error in validate_run(uncovered, draft)
                if "no review node" in error
            ],
            [],
        )

    def test_shared_checkout_defers_all_plan_backed_parent_writers(self) -> None:
        plan = valid_graph_plan()
        detach_mission_edges(plan)
        plan["max_parallel_workers"] = 2
        for node in mission_nodes(plan):
            node["executor"] = "harness_parent"
            node["runtime"] = None
        run = valid_graph_run(plan)
        authorize_execution(run, ["M1", "M2"])
        run["runtime_capabilities"]["max_parallel_workers"] = 2
        run["observed"]["runtime"].update(
            {"available_worker_slots": 0, "isolation_capacity": 0}
        )

        result = select_ready_nodes(plan, run)

        self.assertEqual([], result["dispatchable_nodes"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("workspace_not_isolated", deferred["N-M1"])
        self.assertIn("workspace_not_isolated", deferred["N-M2"])

    def test_unauthorized_mission_does_not_consume_write_budget(self) -> None:
        plan = valid_graph_plan()
        detach_mission_edges(plan)
        run = valid_graph_run(plan)
        run.update(
            {
                "status": "running",
                "intent": "plan-then-execute",
                "plan_readiness": "ready",
                "execution_authorized": True,
                "execution_authorization_source": "user requested M2 execution",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "mission_ids": ["M2"],
                    "expires_when": "run_complete",
                },
            }
        )
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "max_parallel_workers": 1,
            }
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "claude_code",
            "available_drivers": ["dynamic_workflow", "sequential_parent"],
            "detection_source": "observed",
        }
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, ["M2"], "*")

        result = select_ready_nodes(plan, run)

        self.assertEqual(["N-M2"], [item["node_id"] for item in result["dispatchable_nodes"]])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("execution_not_authorized", deferred["N-M1"])

    def test_codex_parent_cannot_bridge_a_claude_code_only_node(self) -> None:
        # A Codex parent has no mechanism to invoke Claude Code anymore: a
        # node whose allowed_providers is claude_code-only is simply
        # unavailable on a Codex host, with no fallback, regardless of how
        # much authorization is granted or how the adapter is observed.
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["runtime"] = {
            "preferred_provider": "claude_code",
            "allowed_providers": ["claude_code"],
            "provider_options": {
                "claude_code": {
                    "model": "opus",
                    "reasoning_effort": None,
                }
            },
        }
        run = valid_graph_run(plan)
        mission_ids = ["M1", "M2"]
        authorize_execution(run, mission_ids)
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "codex",
            "available_drivers": ["sequential_parent"],
            "detection_source": "observed",
        }
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, mission_ids, "*")

        result = select_ready_nodes(plan, run)

        self.assertEqual(["N-M1"], result["ready_frontier"])
        self.assertEqual([], result["dispatchable_nodes"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("runtime_unavailable", deferred["N-M1"])
        self.assertNotIn("wave_launches", result)

        # Widening the host's own native driver set (still never claude_code)
        # or otherwise proving capacity never resurrects the node: there is
        # no cross-host preflight or probe path left to take.
        run["runtime_capabilities"]["runtime_adapter"]["available_drivers"] = [
            "sequential_parent"
        ]
        run["observed"]["runtime"]["available_worker_slots"] = 3
        still_unavailable = select_ready_nodes(plan, run)
        deferred = {
            item["node_id"]: item["reason_codes"]
            for item in still_unavailable["deferred_nodes"]
        }
        self.assertIn("runtime_unavailable", deferred["N-M1"])

    def test_claude_parent_cannot_bridge_codex_only_nodes_in_isolated_worktrees(self) -> None:
        # Mirror image of the Codex-host case: a Claude Code parent has no
        # mechanism to invoke Codex anymore. A codex-only node stays
        # unavailable no matter the authorization or observed capability;
        # widening allowed_providers to include the host's own provider is
        # the only thing that makes it dispatchable, and it dispatches
        # natively (source "host"), never through a guarded external route.
        plan = valid_graph_plan()
        detach_mission_edges(plan)
        plan["max_parallel_workers"] = 2
        for node in mission_nodes(plan):
            node["runtime"] = {
                "preferred_provider": "codex",
                "allowed_providers": ["codex"],
            }
        run = valid_graph_run(plan)
        mission_ids = ["M1", "M2"]
        authorize_execution(run, mission_ids)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "max_parallel_workers": 2,
            }
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "claude_code",
            "available_drivers": ["dynamic_workflow", "sequential_parent"],
            "detection_source": "observed",
        }
        run["observed"]["runtime"].update(
            {"available_worker_slots": 2, "isolation_capacity": 2}
        )
        authorize(run, "spawn_subagents", mission_ids, "worker:preallocation")
        for action in (
            "create_app_managed_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, mission_ids, "*")

        schema_v8 = select_ready_nodes(plan, run)
        schema_v8_deferred = {
            item["node_id"]: item["reason_codes"]
            for item in schema_v8["deferred_nodes"]
        }
        self.assertEqual([], schema_v8["dispatchable_nodes"])
        self.assertIn("runtime_unavailable", schema_v8_deferred["N-M1"])
        self.assertIn("runtime_unavailable", schema_v8_deferred["N-M2"])
        self.assertNotIn("wave_launches", schema_v8)

        for node in plan["graph"]["nodes"]:
            node["runtime"]["allowed_providers"] = ["codex", "claude_code"]
        run["plan"]["digest_sha256"] = plan_digest(plan)
        authorize(run, "spawn_subagents", mission_ids, "*")
        authorize(run, "create_local_worktrees", mission_ids, "*")
        schema_v8_native = select_ready_nodes(plan, run)
        self.assertEqual(
            ["run_dynamic_workflow", "run_dynamic_workflow"],
            [item["launch_kind"] for item in schema_v8_native["dispatchable_nodes"]],
        )
        self.assertTrue(
            all(
                item["runtime_provider"] == "claude_code"
                and item["runtime_source"] == "host"
                for item in schema_v8_native["dispatchable_nodes"]
            )
        )

        # Narrowing back to codex-only removes any native route; schema v9
        # closeout scaffolding does not unlock a guarded external fallback.
        for node in plan["graph"]["nodes"]:
            node["runtime"]["allowed_providers"] = ["codex"]
        run["plan"]["digest_sha256"] = plan_digest(plan)
        run["schema_version"] = 9
        run["batch_gate_results"] = [
            {"id": item["id"], "status": "planned", "head_sha": None, "evidence": []}
            for item in plan["batch_verifiers"]
        ]
        run["final_gate_results"] = [
            {"id": item["id"], "status": "planned", "head_sha": None, "evidence": []}
            for item in plan["final_gates"]
        ]
        run["ui_evidence"] = []
        result = select_ready_nodes(plan, run)

        self.assertEqual(["N-M1", "N-M2"], result["ready_frontier"])
        self.assertEqual([], result["dispatchable_nodes"])
        deferred = {
            item["node_id"]: item["reason_codes"]
            for item in result["deferred_nodes"]
        }
        self.assertIn("runtime_unavailable", deferred["N-M1"])
        self.assertIn("runtime_unavailable", deferred["N-M2"])
        self.assertNotIn("wave_launches", result)

    def test_codex_only_review_defers_on_a_claude_code_host(self) -> None:
        plan = valid_graph_plan()
        review = graph_node(
            "N-BACKEND-REVIEW",
            "verifier",
            "batch",
            "runtime_worker",
            ["pass", "fix_required", "retryable_failure", "blocked", "contract_gap"],
            providers=["codex"],
            preferred="codex",
        )
        review["review"] = {
            "type": "backend_code",
            "mission_ids": ["M1"],
            "scope": ["src/a/**"],
            "required_evidence": ["reviewed_sha", "findings"],
        }
        plan["graph"]["nodes"].append(review)
        plan["graph"]["edges"].append(
            {
                "id": "E-M1-BACKEND-REVIEW",
                "kind": "dependency",
                "from": "N-M1",
                "to": review["id"],
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        plan["required_reviews"] = ["backend_code"]
        run = valid_graph_run(plan)
        run.update(
            {
                "status": "running",
                "intent": "plan-then-execute",
                "plan_readiness": "ready",
                "execution_authorized": True,
                "execution_authorization_source": "user requested review",
                "execution_authorization_scope": {
                    "run_id": run["run_id"],
                    "mission_ids": ["M1"],
                    "expires_when": "run_complete",
                },
            }
        )
        run["graph_state"]["node_states"]["N-M1"].update(
            {"phase": "succeeded", "attempts": 1, "last_attempt_id": "A-M1", "last_outcome": "pass"}
        )
        run["graph_state"]["node_states"]["N-M2"].update(
            {
                "phase": "blocked",
                "attempts": 1,
                "last_attempt_id": "A-M2",
                "last_outcome": "blocked",
                "blockers": ["not selected"],
            }
        )
        run["mission_states"]["M1"].update(
            {"phase": "integrated", "integration_gate": "PASS", "integrated_sha": "a" * 40}
        )
        run["mission_states"]["M2"]["phase"] = "blocked"
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
            }
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "claude_code",
            "available_drivers": ["dynamic_workflow", "sequential_parent"],
            "detection_source": "observed",
        }
        authorize(run, "spawn_subagents", ["M1"], "worker:preallocation")

        result = select_ready_nodes(plan, run)

        self.assertEqual([], result["dispatchable_nodes"])
        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("runtime_unavailable", deferred["N-BACKEND-REVIEW"])
        self.assertNotIn("wave_launches", result)

    def test_runtime_reviews_require_authorization_and_share_runtime_capacity(self) -> None:
        plan = valid_graph_plan()
        reviews = []
        for node_id, ref, review_type in (
            ("N-FRONTEND-REVIEW", "batch", "frontend_code"),
            ("N-VISUAL-REVIEW", "final", "visual"),
        ):
            node = graph_node(
                node_id,
                "verifier",
                ref,
                "runtime_worker",
                ["pass", "fix_required", "blocked", "contract_gap"],
                providers=["claude_code"],
                preferred="claude_code",
                provider_options={
                    "claude_code": {
                        "model": "claude-fable-5",
                        "reasoning_effort": "xhigh" if review_type == "frontend_code" else "high",
                    }
                },
            )
            node["review"] = {
                "type": review_type,
                "mission_ids": ["M1"],
                "scope": ["src/a/**"],
                "required_evidence": ["reviewed_sha", "findings"],
            }
            reviews.append(node)
        plan["graph"]["nodes"].extend(reviews)
        plan["required_reviews"] = ["frontend_code", "visual"]
        plan["graph"]["entry_nodes"].extend([node["id"] for node in reviews])
        run = valid_graph_run(plan)
        authorize_execution(run, ["M1", "M2"])
        run["graph_state"]["node_states"]["N-M1"].update(
            {"phase": "succeeded", "attempts": 1, "last_attempt_id": "A-M1", "last_outcome": "pass"}
        )
        run["graph_state"]["node_states"]["N-M2"].update(
            {
                "phase": "blocked",
                "attempts": 1,
                "last_attempt_id": "A-M2",
                "last_outcome": "blocked",
                "blockers": ["not in this review wave"],
            }
        )
        digest = plan_digest(plan)
        run["plan"]["digest_sha256"] = digest
        run["mission_states"]["M1"].update(
            {"phase": "integrated", "integration_gate": "PASS", "integrated_sha": "a" * 40}
        )
        run["mission_states"]["M2"]["phase"] = "blocked"
        run["integration"]["integration_head_sha"] = "a" * 40
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
            }
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "claude_code",
            "available_drivers": ["dynamic_workflow", "sequential_parent"],
            "detection_source": "observed",
        }

        unauthorized = select_ready_nodes(plan, run)
        review_deferred = {
            item["node_id"]: item["reason_codes"] for item in unauthorized["deferred_nodes"]
        }
        self.assertIn("action_not_authorized", review_deferred["N-FRONTEND-REVIEW"])
        self.assertIn("action_not_authorized", review_deferred["N-VISUAL-REVIEW"])

        authorize(run, "spawn_subagents", ["M1"], "*")
        selected = select_ready_nodes(plan, run)
        self.assertEqual(1, len(selected["dispatchable_nodes"]))
        self.assertEqual("N-FRONTEND-REVIEW", selected["dispatchable_nodes"][0]["node_id"])
        self.assertEqual(
            "claude-fable-5",
            selected["dispatchable_nodes"][0]["runtime_binding"]["model"],
        )
        self.assertEqual(
            "xhigh",
            selected["dispatchable_nodes"][0]["runtime_binding"]["reasoning_effort"],
        )
        self.assertEqual(
            "host",
            selected["dispatchable_nodes"][0]["runtime_binding"]["source"],
        )
        self.assertEqual(
            ["spawn_subagents"],
            selected["dispatchable_nodes"][0]["required_actions"],
        )
        self.assertEqual(
            "code_review_readonly",
            selected["dispatchable_nodes"][0]["tool_profile"],
        )
        review_deferred = {
            item["node_id"]: item["reason_codes"] for item in selected["deferred_nodes"]
        }
        self.assertEqual(["over_runtime_budget"], review_deferred["N-VISUAL-REVIEW"])

    def test_review_worker_and_result_are_bound_to_exact_reviewed_sha(self) -> None:
        plan = valid_graph_plan()
        review = graph_node(
            "N-FRONTEND-REVIEW",
            "verifier",
            "batch",
            "runtime_worker",
            ["pass", "fix_required", "blocked", "contract_gap"],
            providers=["claude_code"],
            preferred="claude_code",
            provider_options={
                "claude_code": {"model": "claude-fable-5", "reasoning_effort": "xhigh"}
            },
        )
        review["review"] = {
            "type": "frontend_code",
            "mission_ids": ["M1"],
            "scope": ["src/a/**"],
            "required_evidence": ["reviewed_sha", "findings"],
        }
        plan["graph"]["nodes"].append(review)
        plan["required_reviews"] = ["frontend_code"]
        plan["graph"]["entry_nodes"].append(review["id"])
        run = valid_graph_run(plan)
        run["integration"]["integration_head_sha"] = "a" * 40
        run["graph_state"]["node_states"][review["id"]].update(
            {
                "phase": "running",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-1",
                "bound_worker_id": "RW-1",
            }
        )
        run["review_workers"] = [
            {
                "worker_id": "RW-1",
                "node_id": review["id"],
                "attempt_id": "ATT-REVIEW-1",
                "plan_revision": plan["revision"],
                "plan_digest_sha256": plan_digest(plan),
                "graph_revision": run["graph_state"]["graph_revision"],
                "reviewed_sha": "a" * 40,
                "review_path": "C:/repo/review",
                "worker_runtime": "subagent",
                "completion_channel": "agent_result",
                "runtime_binding": {
                    "provider": "claude_code",
                    "driver": "dynamic_workflow",
                    "source": "host",
                    "model": "claude-fable-5",
                    "reasoning_effort": "xhigh",
                    "option_source": "plan_provider_options",
                },
                "task_thread_id": None,
                "report_path": None,
                "phase": "worker_running",
                "outcome": None,
                "findings": [],
            }
        ]
        self.assertEqual([], validate_run(plan, run))
        run["mission_states"]["M1"]["head_sha"] = "b" * 40
        run["review_workers"][0]["reviewed_sha"] = "b" * 40
        self.assertTrue(
            any(
                "must identify the direct singleton pre-integration worktree"
                in error
                for error in validate_run(plan, run)
            )
        )
        malformed_reviews = copy.deepcopy(run)
        malformed_reviews["review_workers"] = None
        self.assertTrue(
            any(
                "run.review_workers: must be a list" in error
                for error in validate_run(plan, malformed_reviews)
            )
        )
        run["mission_states"]["M2"]["head_sha"] = "c" * 40
        run["review_workers"][0]["reviewed_sha"] = "c" * 40
        self.assertTrue(
            any(
                "must identify the direct singleton pre-integration worktree"
                in error
                for error in validate_run(plan, run)
            )
        )
        run["mission_states"]["M2"]["head_sha"] = None
        run["mission_states"]["M1"]["head_sha"] = None
        run["review_workers"][0]["reviewed_sha"] = "a" * 40
        run["status"] = "complete"
        self.assertTrue(
            any(
                "cannot retain active or blocked review workers" in error
                for error in validate_run(plan, run)
            )
        )
        run["status"] = "draft"
        result = {
            "run_id": run["run_id"],
            "node_id": review["id"],
            "attempt_id": "ATT-REVIEW-1",
            "plan_id": plan["plan_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "graph_revision": run["graph_state"]["graph_revision"],
            "batch_base_sha": run["integration"]["batch_base_sha"],
            "status": "succeeded",
            "outcome": "pass",
            "worker_result": {
                "reviewed_sha": "a" * 40,
                "findings": [],
                "evidence_summary": "No blocking frontend findings.",
            },
            "refinement_request": None,
            "evidence_paths": ["review.json"],
        }
        self.assertEqual([], validate_node_result(plan, run, result))
        result["worker_result"]["reviewed_sha"] = "b" * 40
        self.assertTrue(
            any("does not match the review worker" in error for error in validate_node_result(plan, run, result))
        )

    def _frontend_review_node(self) -> dict[str, object]:
        review = graph_node(
            "N-FRONTEND-REVIEW",
            "verifier",
            "batch",
            "runtime_worker",
            ["pass", "fix_required", "blocked", "contract_gap"],
            providers=["claude_code"],
            preferred="claude_code",
            provider_options={
                "claude_code": {"model": "claude-fable-5", "reasoning_effort": "xhigh"}
            },
        )
        review["review"] = {
            "type": "frontend_code",
            "mission_ids": ["M1"],
            "scope": ["src/a/**"],
            "required_evidence": ["reviewed_sha", "findings"],
        }
        return review

    def _review_worker_runtime_binding(self) -> dict[str, object]:
        return {
            "provider": "claude_code",
            "driver": "dynamic_workflow",
            "source": "host",
            "model": "claude-fable-5",
            "reasoning_effort": "xhigh",
            "option_source": "plan_provider_options",
        }

    def test_review_worker_outcome_and_findings_are_validated_per_reviewer(self) -> None:
        plan = valid_graph_plan()
        review = self._frontend_review_node()
        plan["graph"]["nodes"].append(review)
        plan["required_reviews"] = ["frontend_code"]
        plan["graph"]["entry_nodes"].append(review["id"])
        run = valid_graph_run(plan)
        run["integration"]["integration_head_sha"] = "a" * 40
        run["graph_state"]["node_states"][review["id"]].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-1",
                "last_outcome": "pass",
                "bound_worker_id": "RW-1",
            }
        )
        base_worker = {
            "worker_id": "RW-1",
            "node_id": review["id"],
            "attempt_id": "ATT-REVIEW-1",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "graph_revision": run["graph_state"]["graph_revision"],
            "reviewed_sha": "a" * 40,
            "review_path": "C:/repo/review",
            "worker_runtime": "subagent",
            "completion_channel": "agent_result",
            "runtime_binding": self._review_worker_runtime_binding(),
            "task_thread_id": None,
            "report_path": None,
            "phase": "worker_passed",
            "outcome": "pass",
            "findings": [],
        }

        run["review_workers"] = [copy.deepcopy(base_worker)]
        self.assertEqual([], validate_run(plan, run))

        bad_outcome = copy.deepcopy(run)
        bad_outcome["review_workers"][0]["outcome"] = "not_a_declared_outcome"
        self.assertTrue(
            any(
                "is not declared by the reviewed node" in error
                for error in validate_run(plan, bad_outcome)
            )
        )

        missing_findings = copy.deepcopy(run)
        missing_findings["review_workers"][0]["outcome"] = "fix_required"
        self.assertTrue(
            any(
                "is required when outcome is not pass" in error
                for error in validate_run(plan, missing_findings)
            )
        )

        with_findings = copy.deepcopy(run)
        with_findings["review_workers"][0]["outcome"] = "fix_required"
        with_findings["review_workers"][0]["findings"] = ["missing null check on line 42"]
        self.assertEqual([], validate_run(plan, with_findings))

    def test_multiple_reviewers_on_same_node_keep_independent_outcomes(self) -> None:
        plan = valid_graph_plan()
        review = self._frontend_review_node()
        plan["graph"]["nodes"].append(review)
        plan["required_reviews"] = ["frontend_code"]
        plan["graph"]["entry_nodes"].append(review["id"])
        run = valid_graph_run(plan)
        run["integration"]["integration_head_sha"] = "a" * 40
        run["graph_state"]["node_states"][review["id"]].update(
            {
                "phase": "succeeded",
                "attempts": 1,
                "last_attempt_id": "ATT-REVIEW-1",
                "last_outcome": "pass",
                "bound_worker_id": "RW-1",
            }
        )
        passing_reviewer = {
            "worker_id": "RW-1",
            "node_id": review["id"],
            "attempt_id": "ATT-REVIEW-1",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "graph_revision": run["graph_state"]["graph_revision"],
            "reviewed_sha": "a" * 40,
            "review_path": "C:/repo/review-1",
            "worker_runtime": "subagent",
            "completion_channel": "agent_result",
            "runtime_binding": self._review_worker_runtime_binding(),
            "task_thread_id": None,
            "report_path": None,
            "phase": "worker_passed",
            "outcome": "pass",
            "findings": [],
        }
        dissenting_reviewer = {
            "worker_id": "RW-2",
            "node_id": review["id"],
            "attempt_id": "ATT-REVIEW-2",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": plan_digest(plan),
            "graph_revision": run["graph_state"]["graph_revision"],
            "reviewed_sha": "a" * 40,
            "review_path": "C:/repo/review-2",
            "worker_runtime": "subagent",
            "completion_channel": "agent_result",
            "runtime_binding": self._review_worker_runtime_binding(),
            "task_thread_id": None,
            "report_path": None,
            "phase": "superseded",
            "outcome": "fix_required",
            "findings": ["missing null check on line 42"],
        }
        run["review_workers"] = [passing_reviewer, dissenting_reviewer]

        # Majority-pass reconciliation lets the parent record an overall
        # "pass" even though one reviewer independently found fix_required;
        # both reviewers' own verdicts remain on the record unmodified.
        self.assertEqual([], validate_run(plan, run))
        self.assertEqual(
            "pass", run["graph_state"]["node_states"][review["id"]]["last_outcome"]
        )
        self.assertEqual("pass", run["review_workers"][0]["outcome"])
        self.assertEqual("fix_required", run["review_workers"][1]["outcome"])

    def test_node_result_is_bound_to_the_active_graph_attempt(self) -> None:
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        digest = plan_digest(plan)
        start_mission(run, plan, digest, base_sha="a" * 40)
        result = {
            "run_id": run["run_id"],
            "node_id": "N-M1",
            "attempt_id": "ATT-N-M1-1",
            "plan_id": plan["plan_id"],
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "graph_revision": run["graph_state"]["graph_revision"],
            "batch_base_sha": run["integration"]["batch_base_sha"],
            "status": "succeeded",
            "outcome": "pass",
            "worker_result": {"status": "PASS"},
            "refinement_request": None,
            "evidence_paths": ["worker-result.json"],
        }

        self.assertEqual([], validate_node_result(plan, run, result))
        malformed = copy.deepcopy(result)
        malformed["node_id"] = []
        self.assertTrue(
            any("must be a non-empty string" in error for error in validate_node_result(plan, run, malformed))
        )
        malformed = copy.deepcopy(result)
        malformed["status"] = []
        self.assertTrue(
            any("unsupported value" in error for error in validate_node_result(plan, run, malformed))
        )
        result["attempt_id"] = "ATT-STALE"
        self.assertTrue(
            any("active attempt" in error for error in validate_node_result(plan, run, result))
        )
        result["attempt_id"] = "ATT-N-M1-1"
        result["run_id"] = "RUN-STALE"
        self.assertTrue(
            any("does not match RUN" in error for error in validate_node_result(plan, run, result))
        )
        result["run_id"] = run["run_id"]
        result["batch_base_sha"] = "b" * 40
        self.assertTrue(
            any("batch_base_sha" in error for error in validate_node_result(plan, run, result))
        )

    def test_native_claude_code_nodes_carry_their_own_plan_selected_model(self) -> None:
        # Wave grouping (by model/effort/tool profile) is no longer a
        # graph-selector concern: select_ready_nodes never returns a
        # "wave_launches" key, and grouping same-host Dynamic Workflow
        # launches now belongs entirely to the Claude Code adapter. Each
        # dispatchable node still carries its own exact PLAN-selected
        # runtime_binding so the adapter can group them itself.
        plan = valid_graph_plan()
        detach_mission_edges(plan)
        for node, model in zip(mission_nodes(plan), ("sonnet", "opus"), strict=True):
            node["runtime"] = {
                "preferred_provider": "claude_code",
                "allowed_providers": ["claude_code"],
                "provider_options": {
                    "claude_code": {
                        "model": model,
                        "reasoning_effort": None,
                    }
                },
            }
        run = valid_graph_run(plan)
        mission_ids = ["M1", "M2"]
        authorize_execution(run, mission_ids)
        run["runtime_capabilities"].update(
            {
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "max_parallel_workers": 2,
            }
        )
        run["observed"]["runtime"].update(
            {"available_worker_slots": 2, "isolation_capacity": 2}
        )
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "claude_code",
            "available_drivers": ["dynamic_workflow", "sequential_parent"],
            "detection_source": "observed",
        }
        for action in (
            "spawn_subagents",
            "create_local_worktrees",
            "create_local_branches",
            "create_local_commits",
        ):
            authorize(run, action, mission_ids, "*")

        result = select_ready_nodes(plan, run)

        self.assertNotIn("wave_launches", result)
        self.assertEqual(
            ["N-M1", "N-M2"],
            [item["node_id"] for item in result["dispatchable_nodes"]],
        )
        self.assertEqual(
            ["sonnet", "opus"],
            [item["runtime_binding"]["model"] for item in result["dispatchable_nodes"]],
        )
        self.assertTrue(
            all(
                item["launch_kind"] == "run_dynamic_workflow"
                and item["runtime_provider"] == "claude_code"
                and item["runtime_source"] == "host"
                for item in result["dispatchable_nodes"]
            )
        )








    def test_approval_node_does_not_require_a_reconciled_parent(self) -> None:
        # Contrast with the lifecycle case above: an approval gate does not
        # mutate parent git state, so an unreconciled parent must not defer
        # it the way it defers a mission or lifecycle node.
        plan = valid_graph_plan()
        run = valid_graph_run(plan)
        plan["graph"]["nodes"].append(
            graph_node("N-APPROVAL", "approval", "final-signoff", "human", ["pass", "blocked"])
        )
        plan["graph"]["entry_nodes"].append("N-APPROVAL")
        run["plan"]["digest_sha256"] = plan_digest(plan)
        run["graph_state"]["node_states"]["N-APPROVAL"] = {
            "phase": "dormant",
            "attempts": 0,
            "last_attempt_id": None,
            "last_outcome": None,
            "bound_worker_id": None,
            "blockers": [],
        }
        authorize_execution(run, ["*"], status="ready")
        run["integration"]["batch_base_sha"] = None
        run["observed"]["git"]["parent_dirty"] = None

        result = select_ready_nodes(plan, run)

        dispatchable = {item["node_id"] for item in result["dispatchable_nodes"]}
        self.assertIn("N-APPROVAL", dispatchable)

    def test_runtime_unavailable_does_not_mask_other_deferral_reasons(self) -> None:
        # Previously a missing binding returned early, so an agent that fixed
        # runtime_unavailable would then discover batch_base_missing on the
        # next run instead of seeing both at once.
        plan = valid_graph_plan()
        plan["graph"]["nodes"][0]["runtime"]["allowed_providers"] = ["codex"]
        run = valid_graph_run(plan)
        authorize_execution(run, ["M1", "M2"])
        run["runtime_capabilities"]["runtime_adapter"] = {
            "provider": "claude_code",
            "available_drivers": ["sequential_parent"],
            "detection_source": "observed",
        }
        run["integration"]["batch_base_sha"] = None

        result = select_ready_nodes(plan, run)

        deferred = {item["node_id"]: item["reason_codes"] for item in result["deferred_nodes"]}
        self.assertIn("runtime_unavailable", deferred["N-M1"])
        self.assertIn("batch_base_missing", deferred["N-M1"])


if __name__ == "__main__":
    unittest.main()

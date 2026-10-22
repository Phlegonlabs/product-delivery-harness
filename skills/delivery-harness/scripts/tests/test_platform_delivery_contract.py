#!/usr/bin/env python3
"""Focused tests for the platform-delivery PLAN and verifier joins."""

from __future__ import annotations

import copy
import hashlib
import io
import re
import sys
import tempfile
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import _validate_verifier  # noqa: E402
from harness_manifest import validate_plan  # noqa: E402
from harness_manifest import validate_current_plan_run  # noqa: E402
from harness_manifest import _validate_verifier_executions  # noqa: E402
from manifest_fixtures import valid_plan  # noqa: E402
from manifest_fixtures import (  # noqa: E402
    eval_exempt_prd,
    carry_security_requirement,
    graph_node,
    manifest_markdown,
    materialize_plan_sources,
    retained_gate_execution,
    task as task_fixture,
    valid_run,
)
from platform_delivery_contract import (  # noqa: E402
    platform_delivery_shape_errors,
    validate_feature_acceptance,
    validate_platform_delivery,
)
from harness_contract_join import validate_frozen_contract_joins  # noqa: E402
import harness_contract_join as harness_contract_join_module  # noqa: E402
from select_ready_nodes import _incoming, _logical_reasons  # noqa: E402
from select_ready_nodes import _selection_context  # noqa: E402
from verifier_runtime import _validated_inputs  # noqa: E402
from render_review_packet import _relevant_acceptance_mappings  # noqa: E402
from validate_harness_plan import main as validate_plan_cli  # noqa: E402
from delivery_acceptance_io import (  # noqa: E402
    AcceptanceError,
    parse_required_prd_test_authority,
)


def contract(mode: str = "whole_platform_sequential") -> SimpleNamespace:
    return SimpleNamespace(
        mode=mode,
        shared_arch_ids=("ARCH-001",),
        stages=(
            SimpleNamespace(
                id="web",
                order=1,
                surfaces=("web-app", "public-api"),
                test_ids=("TEST-001",),
            ),
            SimpleNamespace(
                id="ios",
                order=2,
                surfaces=("ios-app",),
                test_ids=("TEST-002",),
            ),
        ),
    )


def platform_plan() -> dict[str, object]:
    """A valid graph fixture mapped from web completion to iOS completion."""

    plan = valid_plan()
    plan["missions"][0]["trace_ids"].append("ARCH-001")
    for task in plan["missions"][0]["tasks"]:
        task["trace_ids"].append("ARCH-001")
    plan["traces"].append(
        {
            "id": "ARCH-001",
            "source_ids": ["SRC-002"],
            "priority": "must",
            "requirement": "Establish the shared platform interface",
            "disposition": "planned",
            "rationale": None,
        }
    )
    plan["platform_delivery"] = {
        "protocol": "platform-delivery/1",
        "stages": [
            {
                "id": "web",
                "mission_ids": ["M1"],
                "completion_mission_id": "M1",
                "integration_verifier_ids": ["integrate-m1"],
            },
            {
                "id": "ios",
                "mission_ids": ["M2"],
                "completion_mission_id": "M2",
                "integration_verifier_ids": ["integrate-m2"],
            },
        ],
    }
    plan["missions"][0]["integration_verifiers"][0]["acceptance_test_ids"] = ["TEST-001"]
    plan["missions"][1]["integration_verifiers"][0]["acceptance_test_ids"] = [
        "TEST-001",
        "TEST-002",
    ]
    plan["final_gates"][0]["acceptance_test_ids"] = ["TEST-001", "TEST-002"]
    return plan


def add_feature_gate(plan: dict[str, object]) -> None:
    """Give REQ-001 a dependency-only path from both carrying missions."""

    for index, mission in enumerate(plan["missions"]):
        if "REQ-001" not in mission["trace_ids"]:
            mission["trace_ids"].append("REQ-001")
        if "ARCH-001" not in mission["trace_ids"]:
            mission["trace_ids"].append("ARCH-001")
        task = mission["tasks"][0]
        if "REQ-001" not in task["trace_ids"]:
            task["trace_ids"].append("REQ-001")
        if "ARCH-001" not in task["trace_ids"]:
            task["trace_ids"].append("ARCH-001")
            for row in task["acceptance_matrix"]:
                if "ARCH-001" not in row["trace_ids"]:
                    row["trace_ids"].append("ARCH-001")
        task["acceptance_matrix"].append(
            {
                "test_id": "TEST-001",
                "trace_ids": ["REQ-001"],
                "criterion": "The shared release regression passes",
            }
        )
        plan["graph"]["edges"].append(
            {
                "id": f"E-{mission['id']}-PLATFORM-FINAL",
                "kind": "dependency",
                "from": f"N-{mission['id']}",
                "to": "N-FINAL",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
    feature_tests = {
        row["test_id"]
        for mission in plan["missions"]
        for task in mission["tasks"]
        for row in task["acceptance_matrix"]
        if "REQ-001" in row["trace_ids"]
    }
    plan["final_gates"][0]["acceptance_test_ids"] = sorted(
        set(plan["final_gates"][0]["acceptance_test_ids"]) | feature_tests
    )
    plan["traces"][0]["acceptance_gate_ids"] = ["final"]


def three_platform_plan() -> dict[str, object]:
    """Build web -> iOS -> Android mappings with mission graph nodes."""

    plan = platform_plan()
    android_mission = {
        "id": "M3",
        "trace_ids": ["REQ-003"],
        "tasks": [task_fixture("M3", 1, "REQ-003", "src/c/one.py")],
        "integration_verifiers": [
            {
                "id": "integrate-m3",
                "cwd": ".",
                "argv": ["tool", "integration"],
                "pass_signal": "exit 0",
                "execution": {
                    "isolation": "host",
                    "parallel_safe": False,
                    "resources": [],
                },
                "acceptance_test_ids": ["TEST-001", "TEST-002", "TEST-003"],
            }
        ],
    }
    plan["missions"].append(android_mission)
    plan["graph"]["nodes"].append(
        {
            "id": "N-M3",
            "kind": "mission",
            "ref": "M3",
            "executor": "runtime_worker",
                "max_attempts": 2,
        }
    )
    plan["platform_delivery"]["stages"].append(
        {
            "id": "android",
            "mission_ids": ["M3"],
            "completion_mission_id": "M3",
            "integration_verifier_ids": ["integrate-m3"],
        }
    )
    plan["graph"]["edges"].append(
        {
            "id": "E-M2-M3",
            "kind": "dependency",
            "from": "N-M2",
            "to": "N-M3",
            "on_outcomes": ["pass"],
            "max_traversals": None,
        }
    )
    return plan


def three_stage_contract() -> SimpleNamespace:
    value = contract()
    return SimpleNamespace(
        mode=value.mode,
        shared_arch_ids=value.shared_arch_ids,
        stages=(
            *value.stages,
            SimpleNamespace(
                id="android",
                order=3,
                surfaces=("android-app",),
                test_ids=("TEST-003",),
            ),
        ),
    )


def add_ui_surface(
    plan: dict[str, object],
    *,
    surface_id: str,
    release_surface: str,
    owner_mission: str,
) -> dict[str, object]:
    """Add one PLAN surface and an explicit owner trace to mission and task."""

    surface = {
        "id": surface_id,
        "trace_ids": [f"REQ-{owner_mission[-1]}"],
        "route": f"/{surface_id.lower()}",
        "breakpoints": ["390", "768"],
        "states": ["ready"],
        "evidence_gate": "required",
        "release_surface": release_surface,
    }
    plan["ui_surfaces"].append(surface)
    mission = plan["missions"][int(owner_mission[-1]) - 1]
    mission["trace_ids"].append(surface_id)
    for task in mission["tasks"]:
        task["trace_ids"].append(surface_id)
    return surface


def add_runtime_review_handoff(
    plan: dict[str, object],
    *,
    source_mission: str,
    target_mission: str,
    stage: str,
    guarded: bool = False,
) -> None:
    """Replace the direct handoff with a runtime review dependency path."""

    reviewer_id = f"N-REVIEW-{source_mission}"
    reviewer = graph_node(
        reviewer_id,
        "verifier",
        f"review-{source_mission}",
        "runtime_worker",
        ["pass", "fix_required", "blocked"],
    )
    reviewer["review"] = {
        "type": "backend_code",
        "lineage_id": f"REVIEW-{source_mission}",
        "mission_ids": [source_mission],
        "scope": ["src/**"],
        "required_evidence": ["reviewed_sha", "findings"],
        "stage": stage,
    }
    plan["graph"]["nodes"].append(reviewer)
    plan["graph"]["edges"] = [
        edge
        for edge in plan["graph"]["edges"]
        if not (
            edge["kind"] == "dependency"
            and edge["from"] == f"N-{source_mission}"
            and edge["to"] == f"N-{target_mission}"
        )
    ]
    review_source = f"N-{source_mission}"
    if guarded:
        guard_id = f"N-GATE-{source_mission}"
        plan["graph"]["nodes"].append(
            graph_node(
                guard_id,
                "verifier",
                "final",
                "local_command",
                ["pass", "blocked"],
            )
        )
        plan["graph"]["edges"].append(
            {
                "id": f"E-{source_mission}-PLATFORM-GATE",
                "kind": "dependency",
                "from": f"N-{source_mission}",
                "to": guard_id,
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        review_source = guard_id
    plan["graph"]["edges"].extend(
        [
            {
                "id": f"E-{source_mission}-RUNTIME-REVIEW",
                "kind": "dependency",
                "from": review_source,
                "to": reviewer_id,
                "on_outcomes": ["pass"],
                "max_traversals": None,
            },
            {
                "id": f"E-RUNTIME-REVIEW-{target_mission}",
                "kind": "dependency",
                "from": reviewer_id,
                "to": f"N-{target_mission}",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            },
        ]
    )


def preintegration_review_run(plan: dict[str, object]) -> dict[str, object]:
    """Return worker-pass plus review-pass state while M1 remains unintegrated."""

    run = valid_run(plan)
    run["status"] = "running"
    run["plan_readiness"] = "ready"
    run["execution_authorized"] = True
    run["graph_state"]["node_states"]["N-M1"].update(
        {
            "phase": "running",
            "attempts": 1,
            "last_attempt_id": "ATT-M1",
            "last_outcome": None,
            "bound_worker_id": "W-M1",
        }
    )
    run["graph_state"]["node_states"]["N-REVIEW-M1"].update(
        {
            "phase": "succeeded",
            "attempts": 1,
            "last_attempt_id": "ATT-REVIEW-M1",
            "last_outcome": "pass",
            "bound_worker_id": "RW-M1",
        }
    )
    run["mission_states"]["M1"].update(
        {
            "phase": "worker_passed",
            "head_sha": "b" * 40,
        }
    )
    run["review_workers"].append(
        {
            "worker_id": "RW-M1",
            "node_id": "N-REVIEW-M1",
            "attempt_id": "ATT-REVIEW-M1",
            "plan_revision": plan["revision"],
            "plan_digest_sha256": run["plan"]["digest_sha256"],
            "graph_revision": run["graph_state"]["graph_revision"],
            "reviewed_sha": "b" * 40,
            "review_path": "C:/repo/worktrees/M1",
            "phase": "worker_passed",
            "outcome": "pass",
            "findings": [],
        }
    )
    return run


def feature_review_plan(stage: object, *, guarded: bool = False) -> dict[str, object]:
    """Bind a feature gate to M1 through a runtime-review dependency path."""

    plan = platform_plan()
    add_feature_gate(plan)
    feature_trace = next(
        trace for trace in plan["traces"] if trace["id"] == "REQ-001"
    )
    assert feature_trace["acceptance_gate_ids"] == ["final"]
    plan["graph"]["edges"] = [
        edge
        for edge in plan["graph"]["edges"]
        if edge["id"] not in {"E-M1-PLATFORM-FINAL", "E-M1-M2"}
    ]
    review = next(
        node for node in plan["graph"]["nodes"]
        if node["id"] == "N-REVIEW-M1"
    )
    review["allowed_outcomes"] = ["pass", "blocked"]
    review["review"]["stage"] = stage
    review["review"]["mission_ids"] = ["M1"]
    review_source = "N-M1"
    if guarded:
        review_source = "N-GATE-M1"
        plan["graph"]["nodes"].append(
            graph_node(
                review_source,
                "verifier",
                "batch",
                "local_command",
                ["pass", "blocked"],
            )
        )
        plan["graph"]["edges"] = [
            edge
            for edge in plan["graph"]["edges"]
            if not (
                edge["kind"] == "dependency"
                and edge["from"] == "N-M1"
                and edge["to"] == "N-REVIEW-M1"
            )
        ]
        plan["graph"]["edges"].extend(
            [
                {
                    "id": "E-M1-FEATURE-GATE",
                    "kind": "dependency",
                    "from": "N-M1",
                    "to": review_source,
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
                {
                    "id": "E-FEATURE-GATE-REVIEW",
                    "kind": "dependency",
                    "from": review_source,
                    "to": "N-REVIEW-M1",
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
            ]
        )
    plan["graph"]["edges"].append(
        {
            "id": "E-FEATURE-REVIEW-M2",
            "kind": "dependency",
            "from": "N-REVIEW-M1",
            "to": "N-M2",
            "on_outcomes": ["pass"],
            "max_traversals": None,
        }
    )
    return plan


class PlatformPlanShapeTests(unittest.TestCase):
    def test_optional_shape_is_empty_and_malformed_shapes_fail(self) -> None:
        self.assertEqual([], platform_delivery_shape_errors(valid_plan()))
        plan = platform_plan()
        self.assertEqual([], platform_delivery_shape_errors(plan))

        plan["platform_delivery"]["extra"] = True
        self.assertTrue(
            any("must contain exactly" in item for item in platform_delivery_shape_errors(plan))
        )

    def test_reordered_stage_mapping_list_keeps_architecture_authority(self) -> None:
        plan = platform_plan()
        reversed_plan = copy.deepcopy(plan)
        reversed_plan["platform_delivery"]["stages"].reverse()
        contract_value = contract()
        self.assertEqual(
            validate_platform_delivery(plan, contract_value),
            validate_platform_delivery(reversed_plan, contract_value),
        )
        # Stage two still depends on stage one through the fixture graph.
        self.assertFalse(
            any(
                "is not reachable from previous platform completion" in item
                for item in validate_platform_delivery(reversed_plan, contract_value)
            )
        )


class PlatformMappingTests(unittest.TestCase):
    def assert_error(self, plan: dict[str, object], fragment: str) -> None:
        errors = validate_platform_delivery(plan, contract())
        self.assertTrue(
            any(fragment in item for item in errors),
            f"expected {fragment!r} in {errors!r}",
        )

    def test_valid_web_then_ios_and_reversed_architecture_orders(self) -> None:
        self.assertEqual([], validate_platform_delivery(platform_plan(), contract()))
        reversed_plan = platform_plan()
        reversed_plan["platform_delivery"]["stages"].reverse()
        reversed_plan["missions"][0]["trace_ids"].remove("ARCH-001")
        reversed_plan["missions"][1]["trace_ids"].append("ARCH-001")
        reversed_plan["missions"][0]["integration_verifiers"][0][
            "acceptance_test_ids"
        ] = ["TEST-001", "TEST-002"]
        reversed_plan["missions"][1]["integration_verifiers"][0][
            "acceptance_test_ids"
        ] = ["TEST-002"]
        for edge in reversed_plan["graph"]["edges"]:
            if edge["from"] == "N-M1" and edge["to"] == "N-M2":
                edge["from"], edge["to"] = edge["to"], edge["from"]
        reversed_contract = SimpleNamespace(
            mode="whole_platform_sequential",
            shared_arch_ids=("ARCH-001",),
            stages=(
                SimpleNamespace(
                    id="ios", order=1, surfaces=("ios-app",), test_ids=("TEST-002",)
                ),
                SimpleNamespace(
                    id="web",
                    order=2,
                    surfaces=("web-app", "public-api"),
                    test_ids=("TEST-001",),
                ),
            ),
        )


        self.assertEqual(
            [],
            validate_platform_delivery(reversed_plan, reversed_contract),
        )

    def test_unknown_duplicate_and_unmapped_missions_fail(self) -> None:
        plan = platform_plan()
        plan["platform_delivery"]["stages"][0]["mission_ids"].append("M99")
        self.assert_error(plan, "unknown mission 'M99'")

        duplicate = platform_plan()
        duplicate["platform_delivery"]["stages"][1]["mission_ids"].append("M1")
        self.assert_error(duplicate, "already assigned")

        unmapped = platform_plan()
        unmapped["ui_surfaces"].append(
            {
                "id": "UI-OTHER",
                "trace_ids": ["REQ-001"],
                "route": "/other",
                "breakpoints": ["390", "768"],
                "states": ["ready"],
                "evidence_gate": "required",
                "release_surface": "desktop-app",
            }
        )
        self.assert_error(unmapped, "release surfaces absent")

    def test_shared_foundation_must_start_first_stage(self) -> None:
        plan = platform_plan()
        plan["platform_delivery"]["stages"][0]["mission_ids"] = ["M2"]
        plan["platform_delivery"]["stages"][1]["mission_ids"].append("M1")
        self.assert_error(plan, "shared ARCH foundations missing")

        later_shared = platform_plan()
        later_shared["missions"][1]["trace_ids"].append("ARCH-001")
        self.assertEqual([], validate_platform_delivery(later_shared, contract()))

    def test_dependency_paths_are_the_only_stage_handoff(self) -> None:
        plan = platform_plan()
        plan["graph"]["edges"] = [
            edge
            for edge in plan["graph"]["edges"]
            if not (
                edge["kind"] == "dependency"
                and edge["from"] == "N-M1"
                and edge["to"] == "N-M2"
            )
        ]
        self.assert_error(plan, "is not reachable from previous platform completion")

        route_only = platform_plan()
        for edge in route_only["graph"]["edges"]:
            if edge["from"] == "N-M1" and edge["to"] == "N-M2":
                edge["kind"] = "route"
                edge["max_traversals"] = 1
        self.assert_error(route_only, "is not reachable from previous platform completion")

    def test_pass_only_nonmission_intermediaries_reach_missions(self) -> None:
        intermediaries = (
            graph_node(
                "N-GATE",
                "verifier",
                "final",
                "local_command",
                ["pass", "blocked"],
            ),
            graph_node(
                "N-GATE",
                "approval",
                "stage-signoff",
                "human",
                ["pass", "blocked"],
            ),
        )
        for intermediary in intermediaries:
            with self.subTest(kind=intermediary["kind"]):
                handoff = platform_plan()
                handoff["graph"]["nodes"].append(intermediary)
                handoff["graph"]["edges"] = [
                    edge
                    for edge in handoff["graph"]["edges"]
                    if not (
                        edge["kind"] == "dependency"
                        and edge["from"] == "N-M1"
                        and edge["to"] == "N-M2"
                    )
                ]
                handoff["graph"]["edges"].extend(
                    [
                        {
                            "id": "E-M1-GATE",
                            "kind": "dependency",
                            "from": "N-M1",
                            "to": "N-GATE",
                            "on_outcomes": ["pass"],
                            "max_traversals": None,
                        },
                        {
                            "id": "E-GATE-M2",
                            "kind": "dependency",
                            "from": "N-GATE",
                            "to": "N-M2",
                            "on_outcomes": ["pass"],
                            "max_traversals": None,
                        },
                    ]
                )
                self.assertEqual([], validate_platform_delivery(handoff, contract()))

                contributor = platform_plan()
                contributor["graph"]["nodes"].append(intermediary)
                contributor["missions"].append(
                    {
                        "id": "M3",
                        "trace_ids": [],
                        "integration_verifiers": [],
                    }
                )
                contributor["graph"]["nodes"].append(
                    graph_node(
                        "N-M3",
                        "mission",
                        "M3",
                        "runtime_worker",
                        ["pass", "retryable_failure", "blocked", "contract_gap"],
                    )
                )
                contributor["platform_delivery"]["stages"][0]["mission_ids"] = [
                    "M1",
                    "M3",
                ]
                contributor["graph"]["edges"].extend(
                    [
                        {
                            "id": "E-M3-GATE",
                            "kind": "dependency",
                            "from": "N-M3",
                            "to": "N-GATE",
                            "on_outcomes": ["pass"],
                            "max_traversals": None,
                        },
                        {
                            "id": "E-GATE-M1",
                            "kind": "dependency",
                            "from": "N-GATE",
                            "to": "N-M1",
                            "on_outcomes": ["pass"],
                            "max_traversals": None,
                        },
                    ]
                )
                self.assertEqual(
                    [],
                    validate_platform_delivery(contributor, contract()),
                )

    def test_route_segments_cannot_satisfy_platform_dependency_paths(self) -> None:
        intermediary = graph_node(
            "N-GATE",
            "verifier",
            "final",
            "local_command",
            ["pass", "blocked"],
        )

        handoff = platform_plan()
        handoff["graph"]["nodes"].append(intermediary)
        handoff["graph"]["edges"] = [
            edge
            for edge in handoff["graph"]["edges"]
            if not (
                edge["kind"] == "dependency"
                and edge["from"] == "N-M1"
                and edge["to"] == "N-M2"
            )
        ]
        handoff["graph"]["edges"].extend(
            [
                {
                    "id": "E-M1-GATE",
                    "kind": "dependency",
                    "from": "N-M1",
                    "to": "N-GATE",
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
                {
                    "id": "E-GATE-M2",
                    "kind": "route",
                    "from": "N-GATE",
                    "to": "N-M2",
                    "on_outcomes": ["pass"],
                    "max_traversals": 1,
                },
            ]
        )
        self.assert_error(handoff, "is not reachable from previous platform completion")

        contributor = platform_plan()
        contributor["graph"]["nodes"].append(intermediary)
        contributor["missions"].append(
            {
                "id": "M3",
                "trace_ids": [],
                "integration_verifiers": [],
            }
        )
        contributor["graph"]["nodes"].append(
            graph_node(
                "N-M3",
                "mission",
                "M3",
                "runtime_worker",
                ["pass", "retryable_failure", "blocked", "contract_gap"],
            )
        )
        contributor["platform_delivery"]["stages"][0]["mission_ids"] = ["M1", "M3"]
        contributor["graph"]["edges"].extend(
            [
                {
                    "id": "E-M3-GATE",
                    "kind": "dependency",
                    "from": "N-M3",
                    "to": "N-GATE",
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                },
                {
                    "id": "E-GATE-M1",
                    "kind": "route",
                    "from": "N-GATE",
                    "to": "N-M1",
                    "on_outcomes": ["pass"],
                    "max_traversals": 1,
                },
            ]
        )
        self.assert_error(
            contributor,
            "mission 'M3' does not precede completion 'M1'",
        )

    def test_preintegration_review_only_handoff_fails_both_platform_checks(self) -> None:
        plan = platform_plan()
        plan["missions"][1]["depends_on"] = []
        add_runtime_review_handoff(
            plan,
            source_mission="M1",
            target_mission="M2",
            stage="preintegration",
        )
        self.assert_error(plan, "is not reachable from previous platform completion")

        contributor = platform_plan()
        contributor["missions"].append(
            {
                "id": "M3",
                "trace_ids": [],
                "integration_verifiers": [],
            }
        )
        contributor["graph"]["nodes"].append(
            graph_node(
                "N-M3",
                "mission",
                "M3",
                "runtime_worker",
                ["pass", "retryable_failure", "blocked", "contract_gap"],
            )
        )
        contributor["platform_delivery"]["stages"][0]["mission_ids"] = ["M1", "M3"]
        add_runtime_review_handoff(
            contributor,
            source_mission="M3",
            target_mission="M1",
            stage="preintegration",
        )
        self.assert_error(
            contributor,
            "mission 'M3' does not precede completion 'M1'",
        )

    def test_guarded_preintegration_reviews_keep_safe_platform_paths(self) -> None:
        handoff = platform_plan()
        add_runtime_review_handoff(
            handoff,
            source_mission="M1",
            target_mission="M2",
            stage="preintegration",
            guarded=True,
        )
        self.assertEqual([], validate_platform_delivery(handoff, contract()))

        contributor = platform_plan()
        contributor["missions"].append(
            {
                "id": "M3",
                "trace_ids": [],
                "integration_verifiers": [],
            }
        )
        contributor["graph"]["nodes"].append(
            graph_node(
                "N-M3",
                "mission",
                "M3",
                "runtime_worker",
                ["pass", "retryable_failure", "blocked", "contract_gap"],
            )
        )
        contributor["platform_delivery"]["stages"][0]["mission_ids"] = ["M1", "M3"]
        add_runtime_review_handoff(
            contributor,
            source_mission="M3",
            target_mission="M1",
            stage="preintegration",
            guarded=True,
        )
        self.assertEqual([], validate_platform_delivery(contributor, contract()))

    def test_integration_runtime_review_is_a_safe_platform_witness(self) -> None:
        plan = platform_plan()
        add_runtime_review_handoff(
            plan,
            source_mission="M1",
            target_mission="M2",
            stage="integration",
        )
        self.assertEqual([], validate_platform_delivery(plan, contract()))

        run = valid_run(plan)
        run["status"] = "running"
        run["plan_readiness"] = "ready"
        run["execution_authorized"] = True
        run["graph_state"]["node_states"]["N-M1"].update(
            {"phase": "succeeded", "last_outcome": "pass"}
        )
        run["graph_state"]["node_states"]["N-REVIEW-M1"].update(
            {"phase": "succeeded", "last_outcome": "pass"}
        )
        run["mission_states"]["M1"].update(
            {
                "phase": "integrated",
                "integrated_sha": "c" * 40,
                "integration_gate": "PASS",
            }
        )
        context = _selection_context(plan, run)
        node = next(item for item in plan["graph"]["nodes"] if item["id"] == "N-M2")
        self.assertEqual([], _logical_reasons(node, plan, run, *_incoming(plan), context))

    def test_worker_pass_and_preintegration_review_do_not_release_platform(self) -> None:
        plan = platform_plan()
        plan["missions"][1]["depends_on"] = []
        add_runtime_review_handoff(
            plan,
            source_mission="M1",
            target_mission="M2",
            stage="preintegration",
        )
        run = preintegration_review_run(plan)
        context = _selection_context(plan, run)
        node = next(item for item in plan["graph"]["nodes"] if item["id"] == "N-M2")

        self.assertEqual(
            [],
            _logical_reasons(node, plan, run, *_incoming(plan), context),
        )
        self.assert_error(plan, "is not reachable from previous platform completion")

    def test_middle_stage_completion_requires_dependency_path(self) -> None:
        plan = platform_plan()
        android_mission = {
            "id": "M3",
            "trace_ids": ["REQ-003"],
            "integration_verifiers": [
                {
                    "id": "integrate-m3",
                    "cwd": ".",
                    "argv": ["tool", "integration"],
                    "pass_signal": "exit 0",
                    "acceptance_test_ids": ["TEST-001", "TEST-002", "TEST-003"],
                }
            ],
        }
        plan["missions"].append(android_mission)
        plan["graph"]["nodes"].append(
            {
                "id": "N-M3",
                "kind": "mission",
                "ref": "M3",
                "executor": "runtime_worker",
                "max_attempts": 2,
            }
        )
        plan["platform_delivery"]["stages"].append(
            {
                "id": "android",
                "mission_ids": ["M3"],
                "completion_mission_id": "M3",
                "integration_verifier_ids": ["integrate-m3"],
            }
        )
        plan["graph"]["edges"].append(
            {
                "id": "E-M2-M3",
                "kind": "route",
                "from": "N-M2",
                "to": "N-M3",
                "on_outcomes": ["pass"],
                "max_traversals": 1,
            }
        )
        android = SimpleNamespace(
            id="android", order=3, surfaces=("android-app",), test_ids=("TEST-003",)
        )
        value = contract()
        value.stages += (android,)
        errors = validate_platform_delivery(plan, value)
        self.assertTrue(
            any(
                "mission 'M3' is not reachable from previous platform completion 'M2'"
                in item
                for item in errors
            ),
            errors,
        )

    def test_raw_stage_ids_must_exactly_match_architecture(self) -> None:
        plan = platform_plan()
        plan["platform_delivery"]["stages"].pop(1)
        plan["platform_delivery"]["stages"].append(
            {
                "id": "android",
                "mission_ids": ["M1"],
                "completion_mission_id": "M1",
                "integration_verifier_ids": ["integrate-m1"],
            }
        )
        errors = validate_platform_delivery(plan, contract())
        self.assertTrue(any("unknown PLAN stage ID 'android'" in item for item in errors))
        self.assertTrue(any("architecture stage ID absent from PLAN: 'ios'" in item for item in errors))


class PlatformVerifierTests(unittest.TestCase):
    def assert_error(self, plan: dict[str, object], fragment: str) -> None:
        errors = validate_platform_delivery(plan, contract())
        self.assertTrue(
            any(fragment in item for item in errors),
            f"expected {fragment!r} in {errors!r}",
        )

    def test_completion_verifier_must_own_and_cover_upstream_tests(self) -> None:
        plan = platform_plan()
        plan["platform_delivery"]["stages"][1]["integration_verifier_ids"] = [
            "integrate-m1"
        ]
        self.assert_error(plan, "not owned by completion mission")

        coverage = platform_plan()
        coverage["missions"][1]["integration_verifiers"][0][
            "acceptance_test_ids"
        ] = ["TEST-002"]
        self.assert_error(coverage, "must cover the full upstream platform TEST set")

        fresh = platform_plan()
        fresh["missions"][1]["integration_verifiers"][0]["cache"] = {
            "mode": "session_exact",
            "environment_keys": [],
            "deterministic_local": True,
        }
        self.assert_error(fresh, "must run fresh")

    def test_extra_completion_test_requires_canonical_prd_authority(self) -> None:
        plan = platform_plan()
        plan["missions"][1]["integration_verifiers"][0][
            "acceptance_test_ids"
        ] = ["TEST-001", "TEST-002", "TEST-REGRESSION"]
        errors = validate_platform_delivery(
            plan,
            contract(),
            required_test_ids={"TEST-001", "TEST-002", "TEST-REGRESSION"},
        )
        self.assertFalse(any("non-required TEST IDs" in item for item in errors), errors)
        errors = validate_platform_delivery(
            plan,
            contract(),
            required_test_ids={"TEST-001", "TEST-002"},
        )
        self.assertTrue(any("TEST-REGRESSION" in item for item in errors), errors)

    def test_unrelated_integration_verifier_annotation_stays_optional(self) -> None:
        plan = platform_plan()
        plan["missions"][1]["integration_verifiers"].append(
            copy.deepcopy(plan["missions"][1]["integration_verifiers"][0])
        )
        unrelated = plan["missions"][1]["integration_verifiers"][-1]
        unrelated["id"] = "unrelated-m2"
        unrelated.pop("acceptance_test_ids")
        errors = validate_platform_delivery(plan, contract())
        self.assertFalse(any("must not be empty" in item for item in errors), errors)

    def test_final_platform_coverage_may_include_extra_required_tests(self) -> None:
        plan = platform_plan()
        plan["final_gates"][0]["acceptance_test_ids"] = [
            "TEST-001",
            "TEST-002",
            "TEST-SHARED",
        ]
        self.assertEqual([], validate_platform_delivery(plan, contract()))

        incomplete = platform_plan()
        incomplete["final_gates"][0]["acceptance_test_ids"] = ["TEST-001"]
        self.assert_error(incomplete, "TEST-002")


class FeatureGateTests(unittest.TestCase):
    def assert_error(self, plan: dict[str, object], fragment: str) -> None:
        errors = validate_platform_delivery(plan, contract())
        self.assertTrue(
            any(fragment in item for item in errors),
            f"expected {fragment!r} in {errors!r}",
        )

    def test_applicable_platform_trace_requires_mapping(self) -> None:
        plan = platform_plan()
        plan["traces"].append(
            {
                "id": "PRD-PLATFORM",
                "source_ids": ["SRC-001"],
                "priority": "must",
                "requirement": "Complete the platform feature",
                "disposition": "planned",
                "rationale": None,
            }
        )
        plan["missions"][0]["trace_ids"].append("PRD-PLATFORM")
        plan["missions"][0]["tasks"][0]["trace_ids"].append("PRD-PLATFORM")
        plan["missions"][0]["tasks"][0]["acceptance_matrix"].append(
            {
                "test_id": "TEST-001",
                "trace_ids": ["PRD-PLATFORM"],
                "criterion": "The shared release regression passes",
            }
        )
        self.assert_error(plan, "requires acceptance gates")

        mapped = copy.deepcopy(plan)
        mapped["graph"]["edges"].append(
            {
                "id": "E-M1-PLATFORM-FINAL",
                "kind": "dependency",
                "from": "N-M1",
                "to": "N-FINAL",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        next(
            trace
            for trace in mapped["traces"]
            if trace["id"] == "PRD-PLATFORM"
        )["acceptance_gate_ids"] = ["final"]
        mapped["final_gates"][0]["acceptance_test_ids"] = [
            "TEST-M1-01",
            "TEST-M1-02",
            "TEST-001",
            "TEST-002",
        ]
        self.assertEqual([], validate_platform_delivery(mapped, contract()))

    def test_gate_test_coverage_and_dependency_are_enforced(self) -> None:
        plan = platform_plan()
        add_feature_gate(plan)
        plan["final_gates"][0]["acceptance_test_ids"] = ["TEST-002"]
        self.assert_error(plan, "canonical feature TEST obligation")

        route_only = platform_plan()
        add_feature_gate(route_only)
        route_only["graph"]["edges"] = [
            edge
            for edge in route_only["graph"]["edges"]
            if not (
                edge["from"] == "N-M2"
                and edge["to"] == "N-FINAL"
                and edge["kind"] == "dependency"
            )
        ]
        route_only["graph"]["edges"].append(
            {
                "id": "E-M2-PLATFORM-FINAL-ROUTE",
                "kind": "route",
                "from": "N-M2",
                "to": "N-FINAL",
                "on_outcomes": ["pass"],
                "max_traversals": 1,
            }
        )
        self.assert_error(route_only, "does not precede accepting gate")

    def test_conditional_or_nonmust_feature_gate_fails(self) -> None:
        plan = platform_plan()
        add_feature_gate(plan)
        plan["final_gates"][0]["selection"] = {
            "mode": "changed_files",
            "scopes": ["src/**"],
        }
        self.assert_error(plan, "must run fresh")

        nonmust = platform_plan()
        nonmust["traces"][0]["priority"] = "should"
        nonmust["traces"][0]["acceptance_gate_ids"] = ["final"]
        self.assert_error(nonmust, "only on planned must traces")

    def test_standalone_prd_feature_authority_is_enforced(self) -> None:
        plan = platform_plan()
        plan["traces"][0]["id"] = "PRD-001"
        plan["missions"][0]["trace_ids"][0] = "PRD-001"
        for task_entry in plan["missions"][0]["tasks"]:
            task_entry["trace_ids"][0] = "PRD-001"
            for row in task_entry["acceptance_matrix"]:
                row["trace_ids"][0] = "PRD-001"
        errors = validate_feature_acceptance(
            plan,
            feature_test_authority={"PRD-001": {"TEST-001", "TEST-REGRESSION"}},
        )
        self.assertEqual([], errors)
        plan["traces"][0]["acceptance_gate_ids"] = []
        errors = validate_feature_acceptance(
            plan,
            feature_test_authority={"PRD-001": {"TEST-001", "TEST-REGRESSION"}},
        )
        self.assertTrue(
            any("must not be empty" in item for item in errors),
            errors,
        )

        mapped = copy.deepcopy(plan)
        for task_entry in mapped["missions"][0]["tasks"]:
            task_entry["acceptance_matrix"].append(
                {
                    "test_id": "TEST-REGRESSION",
                    "trace_ids": ["PRD-001"],
                    "criterion": "The required regression passes",
                }
            )
        for mission in mapped["missions"]:
            mapped["graph"]["edges"].append(
                {
                    "id": f"E-{mission['id']}-PRD-FINAL",
                    "kind": "dependency",
                    "from": f"N-{mission['id']}",
                    "to": "N-FINAL",
                    "on_outcomes": ["pass"],
                    "max_traversals": None,
                }
            )
        mapped["traces"][0]["acceptance_gate_ids"] = ["final"]
        mapped.pop("platform_delivery")
        mapped["final_gates"][0]["acceptance_test_ids"] = [
            "TEST-001",
            "TEST-002",
            "TEST-REGRESSION",
        ]
        errors = validate_feature_acceptance(
            mapped,
            feature_test_authority={
                "PRD-001": {"TEST-001", "TEST-002", "TEST-REGRESSION"}
            },
        )
        self.assertEqual([], errors)

        omitted = copy.deepcopy(mapped)
        omitted["final_gates"][0]["acceptance_test_ids"] = ["TEST-001", "TEST-002"]
        errors = validate_feature_acceptance(
            omitted,
            feature_test_authority={
                "PRD-001": {"TEST-001", "TEST-002", "TEST-REGRESSION"}
            },
        )
        self.assertTrue(any("TEST-REGRESSION" in item for item in errors), errors)

        invalid = copy.deepcopy(mapped)
        invalid["final_gates"][0]["acceptance_test_ids"].append("TEST-UNLISTED")
        errors = validate_feature_acceptance(
            invalid,
            feature_test_authority={
                "PRD-001": {"TEST-001", "TEST-002", "TEST-REGRESSION"}
            },
        )
        self.assertTrue(any("TEST-UNLISTED" in item for item in errors), errors)

    def test_combined_feature_and_platform_metadata_is_not_rejected(self) -> None:
        plan = platform_plan()
        add_feature_gate(plan)
        self.assertEqual([], validate_plan(plan))
        self.assertEqual(
            [],
            validate_feature_acceptance(
                plan,
                feature_test_authority={
                    "REQ-001": {
                        "TEST-001",
                        "TEST-002",
                        "TEST-M1-01",
                        "TEST-M1-02",
                    }
                },
            ),
        )

    def test_feature_gate_rejects_unsafe_preintegration_review_path(self) -> None:
        plan = feature_review_plan("preintegration")
        self.assertEqual([], validate_plan(plan))
        self.assert_error(plan, "does not precede accepting gate 'final'")

    def test_feature_gate_accepts_guarded_preintegration_review_path(self) -> None:
        plan = feature_review_plan("preintegration", guarded=True)
        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_platform_delivery(plan, contract()))
        self.assertEqual(
            [],
            validate_feature_acceptance(
                plan,
                feature_test_authority={
                    "REQ-001": {
                        "TEST-001",
                        "TEST-002",
                        "TEST-M1-01",
                        "TEST-M1-02",
                    }
                },
            ),
        )

    def test_feature_gate_accepts_integration_review_path(self) -> None:
        plan = feature_review_plan("integration")
        self.assertEqual([], validate_plan(plan))
        self.assertEqual([], validate_platform_delivery(plan, contract()))
        self.assertEqual(
            [],
            validate_feature_acceptance(
                plan,
                feature_test_authority={
                    "REQ-001": {
                        "TEST-001",
                        "TEST-002",
                        "TEST-M1-01",
                        "TEST-M1-02",
                    }
                },
            ),
        )

    def test_unmarked_feature_gate_keeps_direct_legacy_path(self) -> None:
        plan = platform_plan()
        add_feature_gate(plan)
        plan.pop("platform_delivery")
        self.assertEqual([], validate_plan(plan))
        self.assertEqual(
            [],
            validate_feature_acceptance(
                plan,
                feature_test_authority={
                    "REQ-001": {
                        "TEST-001",
                        "TEST-002",
                        "TEST-M1-01",
                        "TEST-M1-02",
                    }
                },
            ),
        )

    def test_marked_not_required_contract_requires_feature_gates(self) -> None:
        plan = platform_plan()
        plan["traces"][0]["id"] = "PRD-001"
        plan["missions"][0]["trace_ids"][0] = "PRD-001"
        for task_entry in plan["missions"][0]["tasks"]:
            task_entry["trace_ids"][0] = "PRD-001"
            for row in task_entry["acceptance_matrix"]:
                row["trace_ids"][0] = "PRD-001"
        plan.pop("platform_delivery")
        errors = validate_platform_delivery(plan, contract(mode="not_required"))
        self.assertTrue(
            any("requires acceptance gates" in item for item in errors),
            errors,
        )

    def test_unmarked_historical_prd_feature_remains_compatible(self) -> None:
        plan = platform_plan()
        plan["traces"][0]["id"] = "PRD-001"
        plan["missions"][0]["trace_ids"][0] = "PRD-001"
        for task_entry in plan["missions"][0]["tasks"]:
            task_entry["trace_ids"][0] = "PRD-001"
            for row in task_entry["acceptance_matrix"]:
                row["trace_ids"][0] = "PRD-001"
        plan.pop("platform_delivery")
        self.assertEqual(
            [],
            validate_feature_acceptance(
                plan,
                feature_test_authority={"PRD-001": {"TEST-001"}},
            ),
        )

class UiStageOwnershipTests(unittest.TestCase):
    def assert_error(self, plan: dict[str, object], fragment: str) -> None:
        errors = validate_platform_delivery(plan, contract())
        self.assertTrue(
            any(fragment in item for item in errors),
            f"expected {fragment!r} in {errors!r}",
        )

    def test_explicit_ui_owner_must_match_its_stage(self) -> None:
        plan = platform_plan()
        add_ui_surface(
            plan,
            surface_id="UI-WEB",
            release_surface="web-app",
            owner_mission="M1",
        )
        add_ui_surface(
            plan,
            surface_id="UI-IOS",
            release_surface="ios-app",
            owner_mission="M2",
        )
        self.assertEqual([], validate_platform_delivery(plan, contract()))

        wrong = platform_plan()
        add_ui_surface(
            wrong,
            surface_id="UI-WEB",
            release_surface="web-app",
            owner_mission="M2",
        )
        self.assert_error(wrong, "wrong platform stage")

    def test_omitted_and_cross_stage_ui_owners_fail(self) -> None:
        omitted = platform_plan()
        surface = add_ui_surface(
            omitted,
            surface_id="UI-WEB",
            release_surface="web-app",
            owner_mission="M1",
        )
        for mission in omitted["missions"]:
            if "UI-WEB" in mission["trace_ids"]:
                mission["trace_ids"].remove("UI-WEB")
            for task in mission["tasks"]:
                if "UI-WEB" in task["trace_ids"]:
                    task["trace_ids"].remove("UI-WEB")
        surface["trace_ids"] = ["REQ-001"]
        self.assert_error(omitted, "no mission or effective-task trace owner")

        cross = platform_plan()
        add_ui_surface(
            cross,
            surface_id="UI-SHARED",
            release_surface="web-app",
            owner_mission="M1",
        )
        cross["missions"][1]["trace_ids"].append("UI-SHARED")
        cross["missions"][1]["tasks"][0]["trace_ids"].append("UI-SHARED")
        self.assert_error(cross, "cross platform stages")

    def test_superseded_task_trace_does_not_own_surface(self) -> None:
        plan = platform_plan()
        add_ui_surface(
            plan,
            surface_id="UI-WEB",
            release_surface="web-app",
            owner_mission="M1",
        )
        parent = plan["missions"][0]["tasks"][0]
        replacement = copy.deepcopy(parent)
        replacement["id"] = "M1/T03"
        replacement["parent_task"] = "M1/T01"
        parent["replaced_by"] = ["M1/T03"]
        plan["missions"][0]["tasks"].append(replacement)
        parent["trace_ids"].remove("UI-WEB")
        self.assertEqual([], validate_platform_delivery(plan, contract()))

    def test_shared_requirement_traces_do_not_infer_ui_ownership(self) -> None:
        plan = platform_plan()
        plan["ui_surfaces"].append(
            {
                "id": "UI-WEB",
                "trace_ids": ["REQ-001"],
                "route": "/web",
                "breakpoints": ["390", "768"],
                "states": ["ready"],
                "evidence_gate": "required",
                "release_surface": "web-app",
            }
        )
        self.assert_error(plan, "no mission or effective-task trace owner")


class PlatformCompatibilityTests(unittest.TestCase):
    def test_unmarked_plan_is_legacy(self) -> None:
        self.assertEqual([], validate_platform_delivery(valid_plan(), None))

    def test_declared_mapping_requires_contract(self) -> None:
        self.assertTrue(
            any(
                "requires an approved platform-delivery/1" in item
                for item in validate_platform_delivery(platform_plan(), None)
            )
        )

    def test_not_required_rejects_stage_mapping(self) -> None:
        errors = validate_platform_delivery(platform_plan(), contract(mode="not_required"))
        self.assertTrue(
            any("cannot declare stage mappings" in item for item in errors),
            errors,
        )


class VerifierAnnotationTests(unittest.TestCase):
    def test_runtime_normalizes_and_retains_without_key_shape_change(self) -> None:
        plan = platform_plan()
        declaration = plan["missions"][1]["integration_verifiers"][0]
        declaration["acceptance_test_ids"] = ["TEST-002", "TEST-001"]
        declaration["execution"]["isolation"] = "host"
        declaration["execution"]["parallel_safe"] = False
        declaration["execution"].pop("sandbox", None)
        declaration["argv"] = [sys.executable, "integration"]
        context = {
            "run_id": "RUN",
            "plan_revision": 1,
            "plan_digest_sha256": "a" * 64,
            "graph_revision": 1,
            "batch_base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "changed_files": [],
            "trust_domain": "parent_local",
            "checkout_role": "integration",
            "checkout_dirty": False,
            "cache_safe": False,
            "layer": "mission_integration",
            "mission_id": "M2",
            "task_id": None,
            "attempt_id": None,
            "lease_id": None,
        }
        cwd, argv, normalized, key_inputs = _validated_inputs(
            declaration,
            context,
            Path("."),
            {},
        )
        self.assertEqual(cwd, Path(".").resolve())
        self.assertEqual(argv, declaration["argv"])
        self.assertEqual(normalized["acceptance_test_ids"], ["TEST-001", "TEST-002"])
        self.assertNotIn("acceptance_test_ids", key_inputs)

        errors: list[str] = []
        _validate_verifier(errors, "verifier", declaration)
        self.assertEqual([], errors)

        malformed = copy.deepcopy(declaration)
        malformed["acceptance_test_ids"] = ["TEST-001", "TEST-001"]
        errors = []
        _validate_verifier(errors, "verifier", malformed)
        self.assertTrue(any("duplicates" in item for item in errors))

    def test_retained_execution_annotation_must_match_plan(self) -> None:
        plan = platform_plan()
        declaration = plan["missions"][0]["integration_verifiers"][0]
        declaration["acceptance_test_ids"] = ["TEST-001"]
        run = valid_run(plan)
        execution = retained_gate_execution(
            plan,
            run,
            declaration,
            layer="mission_integration",
            execution_id="EXEC-ANNOTATED",
            mission_id="M1",
            head_sha=run["mission_states"]["M1"]["integrated_sha"],
        )
        run["verifier_executions"] = [execution]
        errors: list[str] = []
        _validate_verifier_executions(errors, plan, run)
        self.assertFalse(
            any("acceptance_test_ids" in item for item in errors),
            errors,
        )

        execution["verifier"]["acceptance_test_ids"] = ["TEST-002"]
        errors = []
        _validate_verifier_executions(errors, plan, run)
        self.assertTrue(
            any(
                "must exactly match the PLAN verifier declaration" in item
                for item in errors
            ),
            errors,
        )

        execution["verifier"]["acceptance_test_ids"] = [None]
        errors = []
        _validate_verifier_executions(errors, plan, run)
        self.assertTrue(
            any("must be a list of non-empty strings" in item for item in errors),
            errors,
        )


class RuntimePlatformHandoffTests(unittest.TestCase):
    def test_worker_pass_does_not_unlock_third_integration(self) -> None:
        plan = three_platform_plan()
        run = valid_run(plan)
        run["mission_states"]["M1"].update(
            {
                "phase": "integrated",
                "integration_gate": "PASS",
                "integrated_sha": "a" * 40,
            }
        )
        run["mission_states"]["M2"].update(
            {
                "phase": "worker_passed",
                "integration_gate": "planned",
                "integrated_sha": None,
            }
        )
        run["graph_state"]["node_states"]["N-M1"].update(
            {"phase": "succeeded", "last_outcome": "pass"}
        )

        node = next(item for item in plan["graph"]["nodes"] if item["id"] == "N-M3")
        before = _logical_reasons(node, plan, run, *_incoming(plan))
        self.assertIn("dependency_not_satisfied", before)

        run["mission_states"]["M2"].update(
            {
                "phase": "integrated",
                "integration_gate": "PASS",
                "integrated_sha": "b" * 40,
            }
        )
        run["graph_state"]["node_states"]["N-M2"].update(
            {"phase": "succeeded", "last_outcome": "pass"}
        )
        after = _logical_reasons(node, plan, run, *_incoming(plan))
        self.assertNotIn("dependency_not_satisfied", after)

    def test_three_integration_passes_retain_exact_mission_heads(self) -> None:
        plan = three_platform_plan()
        run = valid_run(plan)
        mission_heads = {
            "M1": "a" * 40,
            "M2": "b" * 40,
            "M3": "c" * 40,
        }
        for mission_id, head_sha in mission_heads.items():
            run["mission_states"][mission_id].update(
                {
                    "phase": "integrated",
                    "integration_gate": "PASS",
                    "integrated_sha": head_sha,
                }
            )
            declaration = plan["missions"][
                int(mission_id[-1]) - 1
            ]["integration_verifiers"][0]
            run["verifier_executions"].append(
                retained_gate_execution(
                    plan,
                    run,
                    declaration,
                    layer="mission_integration",
                    execution_id=f"EXEC-{mission_id}",
                    mission_id=mission_id,
                    head_sha=head_sha,
                )
            )

        errors: list[str] = []
        _validate_verifier_executions(errors, plan, run)
        self.assertFalse(
            any("must match the mission integrated_sha" in item for item in errors),
            errors,
        )

        wrong = next(
            execution
            for execution in run["verifier_executions"]
            if execution["mission_id"] == "M2"
        )
        wrong["context"]["head_sha"] = "d" * 40
        errors = []
        _validate_verifier_executions(errors, plan, run)
        self.assertTrue(
            any("must match the mission integrated_sha" in item for item in errors),
            errors,
        )


class FrozenSourceJoinTests(unittest.TestCase):
    def join_plan(self) -> tuple[dict[str, object], dict[str, object]]:
        plan = valid_plan()
        run = valid_run(plan)
        run["runtime_capabilities"]["runtime_adapter"]["version_gate"][
            "required_harness_version"
        ] = "0.62.0"
        plan["sources"] = [
            {
                "id": "SRC-001",
                "kind": "prd",
                "location": "docs/product/PRD.md",
                "owner": "owner",
                "status": "frozen",
                "content_sha256": "a" * 64,
                "source_revision": None,
                "staged_revision": None,
                "notes": "fixture",
            },
            {
                "id": "SRC-002",
                "kind": "architecture",
                "location": "docs/product/architecture.md",
                "owner": "owner",
                "status": "frozen",
                "content_sha256": "b" * 64,
                "source_revision": None,
                "staged_revision": None,
                "notes": "fixture",
            },
            {
                "id": "SRC-003",
                "kind": "stack decisions",
                "location": "docs/product/stack-decisions.md",
                "owner": "owner",
                "status": "frozen",
                "content_sha256": "c" * 64,
                "source_revision": None,
                "staged_revision": None,
                "notes": "fixture",
            },
        ]
        return plan, run

    def test_visible_malformed_marker_fails_before_ui_return(self) -> None:
        plan, run = self.join_plan()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            texts = {
                "docs/product/PRD.md": "# PRD\n",
                "docs/product/architecture.md": (
                    "# Architecture\n\n"
                    "Platform delivery contract: platform-delivery/1\n"
                ),
                "docs/product/stack-decisions.md": "# Stack\n",
            }
            for location, text in texts.items():
                path = root / location
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                source = next(
                    item
                    for item in plan["sources"]
                    if item["location"] == location
                )
                source["content_sha256"] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
            errors = validate_frozen_contract_joins(plan, root, run=run)
        self.assertTrue(
            any(
                "requires an active Platform Delivery Sequence" in item
                for item in errors
            ),
            errors,
        )

    def test_missing_canonical_platform_parser_fails_closed(self) -> None:
        plan, run = self.join_plan()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            texts = {
                "docs/product/PRD.md": "# PRD\n",
                "docs/product/architecture.md": "# Architecture\n",
                "docs/product/stack-decisions.md": "# Stack\n",
            }
            for location, text in texts.items():
                path = root / location
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
                source = next(
                    item
                    for item in plan["sources"]
                    if item["location"] == location
                )
                source["content_sha256"] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
            with patch(
                "harness_contract_join._load_platform_delivery_parser",
                return_value=None,
            ):
                errors = validate_frozen_contract_joins(plan, root, run=run)
        self.assertTrue(
            any("canonical parser is unavailable" in item for item in errors),
            errors,
        )

    def test_canonical_prd_authority_groups_required_tests(self) -> None:
        prd = b"""# PRD

## Test Obligations
| TEST ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |
| --- | --- | --- | --- | --- | --- |
| TEST-001 | Works | integration | Yes | PRD-001, PRD-002 | Signal passes |
| TEST-REGRESSION | Regression | integration | Yes | PRD-001 | Signal passes |
| TEST-OPTIONAL | Optional | integration | No | PRD-001 | Signal observed |
"""
        self.assertEqual(
            {
                "PRD-001": {"TEST-001", "TEST-REGRESSION"},
                "PRD-002": {"TEST-001"},
            },
            parse_required_prd_test_authority(prd),
        )
        with self.assertRaises(AcceptanceError):
            parse_required_prd_test_authority(b"# PRD\n")

    def product_fixtures(self) -> tuple[str, str]:
        pdb_tests = (
            Path(__file__).resolve().parents[3]
            / "product-definition-builder" / "scripts" / "tests"
        )
        original_path = list(sys.path)
        if str(pdb_tests) not in sys.path:
            sys.path.insert(0, str(pdb_tests))
        try:
            from test_platform_delivery import (  # noqa: E402
                architecture as platform_architecture,
                sequence,
            )
            from test_product_package_checker import valid_architecture, valid_prd
        finally:
            sys.path[:] = original_path
        architecture = valid_architecture()
        platform = platform_architecture(platform=sequence())
        for heading in ("Component Architecture", "API and Interface Contracts", "Release Targets"):
            section = re.search(rf"^## {heading}\n.*?(?=^## |\Z)", platform, re.MULTILINE | re.DOTALL).group()
            architecture = re.sub(rf"^## {heading}\n.*?(?=^## |\Z)", lambda _: section, architecture,
                                  count=1, flags=re.MULTILINE | re.DOTALL)
        architecture += "\n" + sequence()
        return (
            architecture,
            eval_exempt_prd(valid_prd()),
        )

    def not_required_architecture(self, status: str = "approved") -> str:
        pdb_tests = (
            Path(__file__).resolve().parents[3]
            / "product-definition-builder" / "scripts" / "tests"
        )
        original_path = list(sys.path)
        if str(pdb_tests) not in sys.path:
            sys.path.insert(0, str(pdb_tests))
        try:
            from test_platform_delivery import (  # noqa: E402
                architecture as platform_architecture,
                sequence,
            )
        finally:
            sys.path[:] = original_path
        stage_header = (
            "| Order | Stage | Release surfaces | Required TEST IDs | "
            "Completion signal |\n"
            "| --- | --- | --- | --- | --- |\n"
        )
        return platform_architecture(
            specifications=(("web-app", "hosted_web", "web"),),
            platform=sequence(
                mode="not_required — Fixture ships exactly one hosted surface",
                rows=stage_header,
                status=status,
            ),
        )

    def unmarked_architecture(self) -> str:
        pdb_tests = (
            Path(__file__).resolve().parents[3]
            / "product-definition-builder" / "scripts" / "tests"
        )
        original_path = list(sys.path)
        if str(pdb_tests) not in sys.path:
            sys.path.insert(0, str(pdb_tests))
        try:
            from test_platform_delivery import architecture as platform_architecture
        finally:
            sys.path[:] = original_path
        return platform_architecture()

    def add_planned_feature(self, plan: dict[str, object], prd: str) -> str:
        feature = {
            "id": "PRD-FEATURE",
            "source_ids": ["SRC-001"],
            "priority": "must",
            "requirement": "Complete the platform feature",
            "disposition": "planned",
            "rationale": None,
            "acceptance_gate_ids": ["final"],
        }
        plan["traces"].append(feature)
        plan["missions"][0]["trace_ids"].append("PRD-FEATURE")
        feature_task = plan["missions"][0]["tasks"][0]
        feature_task["trace_ids"].append("PRD-FEATURE")
        feature_task["acceptance_matrix"].append(
            {
                "test_id": "TEST-FEATURE",
                "trace_ids": ["PRD-FEATURE"],
                "criterion": "The feature result is observable",
            }
        )
        plan["graph"]["edges"].append(
            {
                "id": "E-M1-REPAIR-FINAL",
                "kind": "dependency",
                "from": "N-M1",
                "to": "N-FINAL",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        gate = plan["final_gates"][0]
        gate["acceptance_test_ids"] = sorted(
            set(gate["acceptance_test_ids"]) | {"TEST-FEATURE"}
        )
        return prd.replace(
            "## Non-Functional Requirements",
            "| PRD-FEATURE | Complete the platform feature | Must | The feature result is observable |\n"
            "## Non-Functional Requirements", 1,
        ).replace(
            "## UI Design Handoff Status",
            "| TEST-FEATURE | Feature works | integration | Yes | PRD-FEATURE | "
            "Feature passes |\n## UI Design Handoff Status",
        )

    def materialized_platform_plan(
        self,
        root: Path,
        *,
        architecture: str,
        prd: str,
        plan: dict[str, object] | None = None,
    ) -> dict[str, object]:
        plan = plan or platform_plan()
        package_tests = Path(__file__).resolve().parents[3] / "product-definition-builder/scripts/tests"
        original_path = list(sys.path)
        try:
            sys.path.insert(0, str(package_tests))
            from test_product_package_checker import strictize_approved_package, valid_stack
            from check_product_package import STACK_SECTION_LAYERS
            stack = valid_stack().replace("| Required |", "| Approved |")
            stack = stack.replace(
                "## Frontend Technology Decision",
                "| OPT-BE-01 | Backend or data | Python service bundle | Local API | Team owns runtime | approved |\n"
                "| OPT-BE-02 | Backend or data | Go service bundle | Hosted API | Team owns compilation | rejected |\n"
                "| OPT-MOB-01 | Mobile or desktop | SwiftUI and Xcode bundle | iOS app | Team owns distribution | approved |\n"
                "| OPT-MOB-02 | Mobile or desktop | Cross-platform bundle | Multi-OS app | Team owns upgrades | rejected |\n\n"
                "## Frontend Technology Decision", 1,
            )
            stack += (
                "\n## Mobile/Desktop Technology Decision\n### Recorded or Approved Stack\n"
                "| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |\n"
                "| --- | --- | --- | --- | --- | --- |\n" +
                "\n".join(f"| {layer.title()} | fixture choice | Approved | Owner decision | Fits iOS | None |"
                          for layer in STACK_SECTION_LAYERS["Mobile/Desktop Technology Decision"]) + "\n"
            )
            prd, architecture, stack = strictize_approved_package(prd, architecture, stack)
        finally:
            sys.path[:] = original_path
        plan["sources"] = [
            {
                "id": "SRC-001",
                "kind": "prd",
                "location": "docs/product/PRD.md",
                "owner": "owner",
                "status": "frozen",
                "content_sha256": "a" * 64,
                "source_revision": None,
                "staged_revision": None,
                "notes": "platform fixture",
            },
            {
                "id": "SRC-002",
                "kind": "architecture",
                "location": "docs/product/architecture.md",
                "owner": "owner",
                "status": "frozen",
                "content_sha256": "b" * 64,
                "source_revision": None,
                "staged_revision": None,
                "notes": "platform fixture",
            },
            {
                "id": "SRC-003",
                "kind": "stack decisions",
                "location": "docs/product/stack-decisions.md",
                "owner": "owner",
                "status": "frozen",
                "content_sha256": "c" * 64,
                "source_revision": None,
                "staged_revision": None,
                "notes": "platform fixture",
            },
        ]
        texts = {
            "docs/product/PRD.md": prd,
            "docs/product/architecture.md": architecture,
            "docs/product/stack-decisions.md": stack,
        }
        for location, text in texts.items():
            path = root / location
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8", newline="\n")
            source = next(
                item for item in plan["sources"] if item["location"] == location
            )
            source["content_sha256"] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
        acceptance_tests = list(plan["final_gates"][0]["acceptance_test_ids"])
        carry_security_requirement(plan)
        plan["final_gates"][0]["acceptance_test_ids"] = sorted(set(acceptance_tests) | {"TEST-003"})
        for task in plan["missions"][0]["tasks"]:
            arch_ids = [trace for trace in task["trace_ids"] if trace.startswith("ARCH-")]
            if arch_ids:
                task["acceptance_matrix"].append({"test_id": "TEST-001", "trace_ids": arch_ids,
                                                   "criterion": "The shared platform interface passes"})
        return plan

    def combined_platform_feature_fixture(
        self,
        root: Path,
    ) -> tuple[dict[str, object], str]:
        """Return the proven valid public combined feature/platform fixture."""

        architecture, base_prd = self.product_fixtures()
        plan = platform_plan()
        mission_traces = plan["missions"][0]["trace_ids"]
        mission_traces[mission_traces.index("ARCH-001")] = "ARCH-002"
        for task in plan["missions"][0]["tasks"]:
            traces = task["trace_ids"]
            traces[traces.index("ARCH-001")] = "ARCH-002"
        next(
            trace for trace in plan["traces"] if trace["id"] == "ARCH-001"
        )["id"] = "ARCH-002"
        feature_prd = self.add_planned_feature(plan, base_prd)
        plan = self.materialized_platform_plan(
            root,
            architecture=architecture,
            prd=feature_prd,
            plan=plan,
        )
        prd_source = next(
            source for source in plan["sources"] if source["kind"] == "prd"
        )
        self.assertIsNone(prd_source["source_revision"])
        feature_prd = (root / prd_source["location"]).read_text(encoding="utf-8")
        self.assertEqual(hashlib.sha256(feature_prd.encode("utf-8")).hexdigest(), prd_source["content_sha256"])
        return plan, feature_prd

    def test_run_none_marked_platform_join_and_exact_byte_reuse(self) -> None:
        architecture, prd = self.product_fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
            )
            architecture = (root / "docs/product/architecture.md").read_text(encoding="utf-8")
            prd = (root / "docs/product/PRD.md").read_text(encoding="utf-8")
            real_loader = harness_contract_join_module._load_platform_delivery_parser
            real_module = real_loader(
                harness_contract_join_module.sibling_builder_scripts_dir()
            )
            parser_calls: list[tuple[str, str, bool]] = []

            def parse(architecture_text: str, prd_text: str, *, require: bool):
                parser_calls.append((architecture_text, prd_text, require))
                return real_module.parse_platform_delivery(
                    architecture_text,
                    prd_text,
                    require=require,
                )

            spy_module = SimpleNamespace(parse_platform_delivery=parse)
            with patch(
                "harness_contract_join._load_platform_delivery_parser",
                return_value=spy_module,
            ):
                errors = validate_frozen_contract_joins(plan, root, run=None)
        self.assertEqual(1, len(parser_calls), errors)
        self.assertEqual(architecture, parser_calls[0][0])
        self.assertEqual(prd, parser_calls[0][1])
        self.assertTrue(parser_calls[0][2])
        self.assertFalse(
            any("unknown PLAN stage ID" in item for item in errors),
            errors,
        )
        self.assertFalse(
            any("is not reachable from previous platform completion" in item for item in errors),
            errors,
        )
        self.assertLessEqual(len(errors), 8, errors)

    def test_run_none_marked_unknown_stage_and_missing_handoff_fail(self) -> None:
        architecture, prd = self.product_fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
            )
            plan["platform_delivery"]["stages"][0]["id"] = "desktop"
            errors = validate_frozen_contract_joins(plan, root, run=None)

            plan = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
            )
            plan["graph"]["edges"] = [
                edge
                for edge in plan["graph"]["edges"]
                if not (
                    edge["kind"] == "dependency"
                    and edge["from"] == "N-M1"
                    and edge["to"] == "N-M2"
                )
            ]
            errors.extend(validate_frozen_contract_joins(plan, root, run=None))
        self.assertTrue(
            any("unknown PLAN stage ID 'desktop'" in item for item in errors),
            errors,
        )
        self.assertTrue(
            any("is not reachable from previous platform completion" in item for item in errors),
            errors,
        )

    def test_legacy_pin_marked_platform_join_executes(self) -> None:
        architecture, prd = self.product_fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
            )
            _run = valid_run(plan)
            _run["runtime_capabilities"]["runtime_adapter"]["version_gate"][
                "required_harness_version"
            ] = "0.37.0"
            plan["graph"]["edges"] = [
                edge
                for edge in plan["graph"]["edges"]
                if not (
                    edge["kind"] == "dependency"
                    and edge["from"] == "N-M1"
                    and edge["to"] == "N-M2"
                )
            ]
            errors = validate_frozen_contract_joins(plan, root, run=_run)
        self.assertTrue(
            any("is not reachable from previous platform completion" in item for item in errors),
            errors,
        )

    def test_declared_mapping_missing_marker_and_drift_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.materialized_platform_plan(
                root,
                architecture="# Architecture\n",
                prd="# PRD\n",
            )
            errors = validate_frozen_contract_joins(plan, root, run=None)

            architecture_path = root / "docs/product/architecture.md"
            expected_hash = next(
                source["content_sha256"]
                for source in plan["sources"]
                if source["location"] == "docs/product/architecture.md"
            )
            architecture_path.write_text("# Drift\n", encoding="utf-8")
            errors.extend(validate_frozen_contract_joins(plan, root, run=None))
        self.assertTrue(
            any("requires platform-delivery/1" in item for item in errors),
            errors,
        )
        self.assertTrue(
            any(
                expected_hash in item
                and "frozen architecture bytes do not match content_sha256" in item
                for item in errors
            ),
            errors,
        )

    def test_public_combined_feature_and_platform_join_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, _feature_prd = self.combined_platform_feature_fixture(root)
            feature_trace = next(
                trace
                for trace in plan["traces"]
                if trace["id"] == "PRD-FEATURE"
            )
            feature_task = plan["missions"][0]["tasks"][0]
            feature_row = next(
                row
                for row in feature_task["acceptance_matrix"]
                if row["test_id"] == "TEST-FEATURE"
            )
            feature_dependency = next(
                edge
                for edge in plan["graph"]["edges"]
                if edge["id"] == "E-M1-REPAIR-FINAL"
            )
            errors = validate_frozen_contract_joins(plan, root, run=None)
        self.assertEqual(["final"], feature_trace["acceptance_gate_ids"])
        self.assertIn("PRD-FEATURE", plan["missions"][0]["trace_ids"])
        self.assertIn("PRD-FEATURE", feature_task["trace_ids"])
        self.assertIn("PRD-FEATURE", feature_row["trace_ids"])
        self.assertEqual("dependency", feature_dependency["kind"])
        self.assertEqual("N-M1", feature_dependency["from"])
        self.assertEqual("N-FINAL", feature_dependency["to"])
        self.assertIn("M1", plan["platform_delivery"]["stages"][0]["mission_ids"])
        self.assertIn("TEST-FEATURE", plan["final_gates"][0]["acceptance_test_ids"])
        self.assertEqual([], errors)

    def test_combined_fixture_negatives_fail_their_exact_join(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base_plan, _feature_prd = self.combined_platform_feature_fixture(root)
            self.assertEqual(
                [],
                validate_frozen_contract_joins(base_plan, root, run=None),
            )

            no_gate = copy.deepcopy(base_plan)
            next(
                trace
                for trace in no_gate["traces"]
                if trace["id"] == "PRD-FEATURE"
            ).pop("acceptance_gate_ids")
            no_gate_errors = validate_frozen_contract_joins(
                no_gate,
                root,
                run=None,
            )

            no_coverage = copy.deepcopy(base_plan)
            gate = no_coverage["final_gates"][0]
            gate["acceptance_test_ids"] = [
                test_id
                for test_id in gate["acceptance_test_ids"]
                if test_id != "TEST-FEATURE"
            ]
            no_coverage_errors = validate_frozen_contract_joins(
                no_coverage,
                root,
                run=None,
            )

            no_dependency = copy.deepcopy(base_plan)
            no_dependency["graph"]["edges"] = [
                edge
                for edge in no_dependency["graph"]["edges"]
                if not (edge["kind"] == "dependency" and edge["from"] == "N-M1" and edge["to"] == "N-FINAL")
            ]
            no_dependency_errors = validate_frozen_contract_joins(
                no_dependency,
                root,
                run=None,
            )
        self.assertTrue(
            any(
                "a planned PRD must feature requires acceptance gates" in item
                for item in no_gate_errors
            ),
            no_gate_errors,
        )
        self.assertTrue(
            any(
                "accepting gates do not cover every canonical feature TEST"
                in item and "TEST-FEATURE" in item
                for item in no_coverage_errors
            ),
            no_coverage_errors,
        )
        self.assertTrue(
            any(
                "does not precede accepting gate 'final'" in item
                for item in no_dependency_errors
            ),
            no_dependency_errors,
        )

    def test_marker_only_contract_is_adopted_without_mapping(self) -> None:
        architecture, prd = self.product_fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.materialized_platform_plan(root, architecture=architecture, prd=prd)
            plan.pop("platform_delivery")
            errors = validate_frozen_contract_joins(plan, root, run=None)
        self.assertTrue(
            any(
                "platform-delivery/1 requires PLAN platform_delivery stage mappings" in item
                for item in errors
            ),
            errors,
        )

    def test_adopted_contract_requires_approved_decision(self) -> None:
        architecture, prd = self.product_fixtures()
        draft_architecture = architecture.replace(
            "Decision status: approved", "Decision status: draft"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mapped = self.materialized_platform_plan(
                root,
                architecture=draft_architecture,
                prd=prd,
            )
            mapped_errors = validate_frozen_contract_joins(mapped, root, run=None)

            marker_only = self.materialized_platform_plan(
                root,
                architecture=draft_architecture,
                prd=prd,
            )
            marker_only.pop("platform_delivery")
            marker_errors = validate_frozen_contract_joins(marker_only, root, run=None)

            unresolved = self.materialized_platform_plan(
                root,
                architecture=self.not_required_architecture("blocked"),
                prd=prd,
            )
            unresolved.pop("platform_delivery")
            unresolved_errors = validate_frozen_contract_joins(
                unresolved,
                root,
                run=None,
            )
        self.assertTrue(
            any("requires an approved platform contract" in item for item in mapped_errors),
            mapped_errors,
        )
        self.assertTrue(
            any("requires an approved decision" in item for item in marker_errors),
            marker_errors,
        )
        self.assertTrue(
            any("requires an approved decision" in item for item in unresolved_errors),
            unresolved_errors,
        )

    def test_commented_and_fenced_markers_remain_unmarked_legacy(self) -> None:
        _, prd = self.product_fixtures()
        architecture = (
            "<!-- Platform delivery contract: platform-delivery/1 -->\n\n"
            "```markdown\n"
            "## Platform Delivery Sequence\n"
            "Platform delivery contract: platform-delivery/1\n"
            "```\n\n"
            + self.unmarked_architecture()
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.materialized_platform_plan(root, architecture=architecture, prd=prd)
            plan.pop("platform_delivery")
            errors = validate_frozen_contract_joins(plan, root, run=None)
        self.assertFalse(
            any("platform-delivery/1 requires PLAN platform_delivery" in item for item in errors),
            errors,
        )

    def test_declared_prd_failures_return_structured_diagnostics(self) -> None:
        architecture, valid_prd = self.product_fixtures()
        invalid_utf8 = b"# PRD\n\xff\n\n## Test Obligations\n"
        cases = (
            ("omitted", "requires exactly one frozen prd source"),
            ("duplicate", "requires exactly one frozen prd source"),
            ("missing", "cannot inspect frozen PRD path component"),
            ("hash mismatch", "bytes do not match content_sha256"),
            ("revision invalid", "source_revision must be a full Git SHA"),
            ("utf8 invalid", "core artifact is not valid UTF-8"),
        )
        for case, fragment in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    if case == "utf8 invalid":
                        prd_path = root / "docs/product/PRD.md"
                        prd_path.parent.mkdir(parents=True)
                        prd_path.write_bytes(invalid_utf8)
                        plan = self.materialized_platform_plan(
                            root,
                            architecture=architecture,
                            prd=valid_prd,
                        )
                        source = plan["sources"][0]
                        source["content_sha256"] = hashlib.sha256(invalid_utf8).hexdigest()
                        prd_path.write_bytes(invalid_utf8)
                    else:
                        plan = self.materialized_platform_plan(
                            root,
                            architecture=architecture,
                            prd=valid_prd,
                        )
                    if case == "omitted":
                        plan["sources"] = [
                            source for source in plan["sources"]
                            if source["kind"] != "prd"
                        ]
                    elif case == "duplicate":
                        duplicate = copy.deepcopy(plan["sources"][0])
                        duplicate["id"] = "SRC-DUPLICATE"
                        plan["sources"].append(duplicate)
                    elif case == "missing":
                        (root / "docs/product/PRD.md").unlink()
                    elif case == "hash mismatch":
                        (root / "docs/product/PRD.md").write_text("# Changed\n", encoding="utf-8")
                    elif case == "revision invalid":
                        plan["sources"][0]["source_revision"] = "short"
                    plan.pop("platform_delivery")
                    errors = validate_frozen_contract_joins(plan, root, run=None)
                self.assertTrue(any(fragment in item for item in errors), errors)

    def test_declared_architecture_failures_return_structured_diagnostics(self) -> None:
        architecture, prd = self.product_fixtures()
        invalid_utf8 = b"# Architecture\n\xff\n"
        cases = (
            ("duplicate", "requires exactly one frozen architecture source"),
            ("missing", "cannot inspect frozen architecture path component"),
            ("hash mismatch", "frozen architecture bytes do not match content_sha256"),
            ("revision invalid", "source_revision must be a full Git SHA"),
            ("utf8 invalid", "core artifact is not valid UTF-8"),
        )
        for case, fragment in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    plan = self.materialized_platform_plan(
                        root,
                        architecture=architecture,
                        prd=prd,
                    )
                    if case == "duplicate":
                        duplicate = copy.deepcopy(plan["sources"][1])
                        duplicate["id"] = "SRC-ARCH-DUPLICATE"
                        plan["sources"].append(duplicate)
                    elif case == "missing":
                        (root / "docs/product/architecture.md").unlink()
                    elif case == "hash mismatch":
                        (root / "docs/product/architecture.md").write_text(
                            "# Changed\n",
                            encoding="utf-8",
                        )
                    elif case == "revision invalid":
                        plan["sources"][1]["source_revision"] = "short"
                    elif case == "utf8 invalid":
                        architecture_path = root / "docs/product/architecture.md"
                        plan["sources"][1]["content_sha256"] = hashlib.sha256(
                            invalid_utf8
                        ).hexdigest()
                        architecture_path.write_bytes(invalid_utf8)
                    errors = validate_frozen_contract_joins(plan, root, run=None)
                self.assertTrue(any(fragment in item for item in errors), errors)

    def test_malformed_test_authority_fails_before_semantic_join(self) -> None:
        architecture, _prd = self.product_fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mapped = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd="# PRD\n",
            )
            mapped_errors = validate_frozen_contract_joins(mapped, root, run=None)

            marker_only = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd="# PRD\n",
            )
            marker_only.pop("platform_delivery")
            marker_errors = validate_frozen_contract_joins(marker_only, root, run=None)
        self.assertTrue(
            any(
                "canonical feature TEST authority failed safely" in item
                for item in mapped_errors
            ),
            mapped_errors,
        )
        self.assertTrue(
            any(
                "canonical feature TEST authority failed safely" in item
                for item in marker_errors
            ),
            marker_errors,
        )

    def test_platform_shape_failure_stops_before_semantic_traversal(self) -> None:
        for value in ("desktop", None, 7, []):
            with self.subTest(value=value):
                plan = platform_plan()
                plan["platform_delivery"]["stages"] = value
                shape_errors = platform_delivery_shape_errors(plan)
                self.assertTrue(shape_errors)
                semantic_errors = validate_platform_delivery(plan, contract())
                self.assertEqual(shape_errors, semantic_errors)

    def test_public_and_paired_routes_handle_invalid_platform_shape(self) -> None:
        architecture, prd = self.product_fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
            )
            plan["platform_delivery"]["stages"] = [None]
            public_errors = validate_frozen_contract_joins(plan, root, run=None)

            paired = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
            )
            paired["platform_delivery"]["stages"] = ["desktop"]
            paired_run = valid_run(paired)
            paired_run["runtime_capabilities"]["runtime_adapter"]["version_gate"][
                "required_harness_version"
            ] = "0.62.0"
            paired_errors = validate_frozen_contract_joins(
                paired,
                root,
                run=paired_run,
            )

            cli_plan_path = root / "PLAN.md"
            cli_plan = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
            )
            cli_plan["platform_delivery"]["stages"] = [None]
            cli_plan_path.write_text(
                manifest_markdown(
                    "## Harness Plan Manifest",
                    "harness_plan",
                    cli_plan,
                ),
                encoding="utf-8",
            )
            exit_code = validate_plan_cli([
                "--repo-root",
                str(root),
                "--plan",
                str(cli_plan_path),
            ])
        self.assertTrue(
            any("must contain exactly id" in item for item in public_errors),
            public_errors,
        )
        self.assertTrue(
            any("must contain exactly id" in item for item in paired_errors),
            paired_errors,
        )
        self.assertEqual(1, exit_code)

    def malformed_review_barrier_plan(
        self,
        mission_ids: object,
        stage: object = "preintegration",
    ) -> dict[str, object]:
        """Reach the selector predicate with one malformed runtime review."""

        plan = platform_plan()
        review = next(
            node for node in plan["graph"]["nodes"]
            if node["id"] == "N-REVIEW-M1"
        )
        review["allowed_outcomes"] = ["pass", "blocked"]
        review["review"]["mission_ids"] = mission_ids
        review["review"]["stage"] = stage
        plan["graph"]["edges"] = [
            edge
            for edge in plan["graph"]["edges"]
            if not (
                edge["kind"] == "dependency"
                and edge["from"] == "N-M1"
                and edge["to"] == "N-M2"
            )
        ]
        plan["graph"]["edges"].append(
            {
                "id": "E-REVIEW-M1-M2",
                "kind": "dependency",
                "from": "N-REVIEW-M1",
                "to": "N-M2",
                "on_outcomes": ["pass"],
                "max_traversals": None,
            }
        )
        return plan

    def test_malformed_runtime_review_metadata_cannot_witness_barrier(self) -> None:
        malformed_values = (None, 7, "M1", [None], ["M1", "M1"])
        for mission_ids in malformed_values:
            with self.subTest(mission_ids=mission_ids):
                plan = self.malformed_review_barrier_plan(mission_ids)
                graph_errors = validate_plan(plan)
                self.assertTrue(
                    any(
                        "review.mission_ids" in item
                        and (
                            "must be a list of non-empty strings" in item
                            or "must not contain duplicates" in item
                        )
                        for item in graph_errors
                    ),
                    graph_errors,
                )
                errors = validate_platform_delivery(plan, contract())
                self.assertTrue(
                    any(
                        "is not reachable from previous platform completion"
                        in item
                        for item in errors
                    ),
                    errors,
                )

    def test_malformed_review_stage_cannot_witness_barrier(self) -> None:
        malformed_stages = (None, 7, ["preintegration"], {"name": "preintegration"})
        for stage in malformed_stages:
            with self.subTest(stage=stage):
                plan = self.malformed_review_barrier_plan(["M1"], stage)
                errors = validate_platform_delivery(plan, contract())
                self.assertTrue(
                    any(
                        "is not reachable from previous platform completion"
                        in item
                        for item in errors
                    ),
                    errors,
                )
                graph_errors = validate_plan(plan)
                self.assertTrue(
                    any(
                        "review.stage" in item
                        and "must be preintegration or integration" in item
                        for item in graph_errors
                    ),
                    graph_errors,
                )

    def test_malformed_review_stage_reaches_feature_barrier(self) -> None:
        malformed_stages = (None, 7, ["preintegration"], {"name": "preintegration"})
        for stage in malformed_stages:
            with self.subTest(stage=stage):
                plan = feature_review_plan(stage)
                errors = validate_feature_acceptance(
                    plan,
                    feature_test_authority={
                        "REQ-001": {
                            "TEST-001",
                            "TEST-002",
                            "TEST-M1-01",
                            "TEST-M1-02",
                        }
                    },
                )
                self.assertTrue(
                    any(
                        "mission 'M1' does not precede accepting gate 'final'"
                        in item
                        for item in errors
                    ),
                    errors,
                )

    def test_omitted_review_stage_keeps_preintegration_barrier(self) -> None:
        platform_plan_value = self.malformed_review_barrier_plan(["M1"])
        next(
            node for node in platform_plan_value["graph"]["nodes"]
            if node["id"] == "N-REVIEW-M1"
        )["review"].pop("stage")
        self.assertFalse(
            any("review.stage" in item for item in validate_plan(platform_plan_value))
        )
        platform_errors = validate_platform_delivery(
            platform_plan_value,
            contract(),
        )
        self.assertTrue(
            any(
                "is not reachable from previous platform completion" in item
                for item in platform_errors
            ),
            platform_errors,
        )

        feature_plan_value = feature_review_plan("preintegration")
        next(
            node for node in feature_plan_value["graph"]["nodes"]
            if node["id"] == "N-REVIEW-M1"
        )["review"].pop("stage")
        self.assertFalse(
            any("review.stage" in item for item in validate_plan(feature_plan_value))
        )
        feature_errors = validate_feature_acceptance(
            feature_plan_value,
            feature_test_authority={
                "REQ-001": {
                    "TEST-001",
                    "TEST-002",
                    "TEST-M1-01",
                    "TEST-M1-02",
                }
            },
        )
        self.assertTrue(
            any(
                "does not precede accepting gate 'final'" in item
                for item in feature_errors
            ),
            feature_errors,
        )

    def test_malformed_review_fails_frozen_legacy_and_cli_routes(self) -> None:
        architecture, prd = self.product_fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            public = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
                plan=self.malformed_review_barrier_plan([None]),
            )
            public_run = valid_run(public)
            public_run["runtime_capabilities"]["runtime_adapter"][
                "version_gate"
            ]["required_harness_version"] = "0.62.0"
            public_errors = validate_frozen_contract_joins(
                public,
                root,
                run=public_run,
            )

            run_none = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
                plan=self.malformed_review_barrier_plan("M1"),
            )
            run_none_errors = validate_frozen_contract_joins(
                run_none,
                root,
                run=None,
            )

            legacy = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
                plan=self.malformed_review_barrier_plan(7),
            )
            legacy_run = valid_run(legacy)
            legacy_run["runtime_capabilities"]["runtime_adapter"][
                "version_gate"
            ]["required_harness_version"] = "0.37.0"
            legacy_errors = validate_frozen_contract_joins(
                legacy,
                root,
                run=legacy_run,
            )

            for stage_index, stage in enumerate(
                (None, 7, ["preintegration"], {"name": "preintegration"})
            ):
                strict = self.materialized_platform_plan(
                    root,
                    architecture=architecture,
                    prd=prd,
                    plan=self.malformed_review_barrier_plan(["M1"], stage),
                )
                strict_run = valid_run(strict)
                strict_run["runtime_capabilities"]["runtime_adapter"][
                    "version_gate"
                ]["required_harness_version"] = "0.62.0"
                strict_errors = validate_current_plan_run(
                    strict,
                    run=strict_run,
                    repo_root=root,
                )
                self.assertTrue(
                    any(
                        "is not reachable from previous platform completion"
                        in item
                        for item in strict_errors
                    ),
                    strict_errors,
                )
                self.assertTrue(
                    any(
                        "review.stage" in item
                        and "must be preintegration or integration" in item
                        for item in strict_errors
                    ),
                    strict_errors,
                )

                stage_plan_path = root / f"stage-plan-{stage_index}.md"
                stage_plan_path.write_text(
                    manifest_markdown(
                        "## Harness Plan Manifest",
                        "harness_plan",
                        strict,
                    ),
                    encoding="utf-8",
                )
                cli_output = io.StringIO()
                with redirect_stdout(cli_output):
                    stage_exit_code = validate_plan_cli([
                        "--repo-root",
                        str(root),
                        "--plan",
                        str(stage_plan_path),
                    ])
                cli_text = cli_output.getvalue()
                self.assertEqual(1, stage_exit_code)
                self.assertIn("must be preintegration or integration", cli_text)
                self.assertIn(
                    "is not reachable from previous platform completion",
                    cli_text,
                )

            run_none_stage = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
                plan=self.malformed_review_barrier_plan(
                    ["M1"],
                    {"name": "preintegration"},
                ),
            )
            run_none_errors.extend(
                validate_frozen_contract_joins(
                    run_none_stage,
                    root,
                    run=None,
                )
            )

            cli_plan = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
                plan=self.malformed_review_barrier_plan(["M1", "M1"]),
            )
            cli_plan_path = root / "PLAN.md"
            cli_plan_path.write_text(
                manifest_markdown(
                    "## Harness Plan Manifest",
                    "harness_plan",
                    cli_plan,
                ),
                encoding="utf-8",
            )
            exit_code = validate_plan_cli([
                "--repo-root",
                str(root),
                "--plan",
                str(cli_plan_path),
            ])

        for label, errors in (
            ("public", public_errors),
            ("run-none", run_none_errors),
            ("legacy", legacy_errors),
        ):
            with self.subTest(route=label):
                self.assertTrue(
                    any(
                        "is not reachable from previous platform completion"
                        in item
                        for item in errors
                    ),
                    errors,
                )
        self.assertEqual(1, exit_code)

    def test_declared_architecture_materializes_once_on_failure(self) -> None:
        architecture, prd = self.product_fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = self.materialized_platform_plan(
                root,
                architecture=architecture,
                prd=prd,
            )
            architecture_path = root / "docs/product/architecture.md"
            architecture_path.write_text("# Changed\n", encoding="utf-8")
            real_resolver = harness_contract_join_module._resolve_source_bytes
            calls: list[str] = []

            def resolve(source, repo_root, *, label, strict=False):
                if label == "architecture":
                    calls.append(label)
                return real_resolver(
                    source,
                    repo_root,
                    label=label,
                    strict=strict,
                )

            with patch(
                "harness_contract_join._resolve_source_bytes",
                side_effect=resolve,
            ):
                errors = validate_frozen_contract_joins(plan, root, run=None)
        self.assertEqual(1, len(calls), errors)
        self.assertTrue(
            any("frozen architecture bytes do not match content_sha256" in item for item in errors),
            errors,
        )

    def test_unmarked_feature_metadata_is_optional_but_explicit_fields_join(self) -> None:
        plan, _run = self.join_plan()
        plan["traces"].append(
            {
                "id": "PRD-FEATURE",
                "source_ids": ["SRC-001"],
                "priority": "must",
                "requirement": "Complete the headless feature",
                "disposition": "planned",
                "rationale": None,
            }
        )
        plan["missions"][0]["trace_ids"].append("PRD-FEATURE")
        feature_task = plan["missions"][0]["tasks"][0]
        feature_task["trace_ids"].append("PRD-FEATURE")
        feature_task["acceptance_matrix"].append(
            {
                "test_id": "TEST-FEATURE",
                "trace_ids": ["PRD-FEATURE"],
                "criterion": "The feature result is observable",
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            materialize_plan_sources(root, plan)
            from test_product_package_checker import strictize_approved_package
            source = plan["sources"][0]
            prd_path = root / source["location"]
            prd = prd_path.read_text(encoding="utf-8").replace(
                "## Non-Functional Requirements",
                "| PRD-FEATURE | Complete the headless feature | Must | The feature result is observable |\n"
                "## Non-Functional Requirements", 1,
            ).replace(
                "## UI Design Handoff Status",
                "| TEST-FEATURE | Feature works | integration | Yes | PRD-FEATURE | Result passes |\n"
                "## UI Design Handoff Status", 1,
            )
            product_sources = plan["sources"][:3]
            texts = strictize_approved_package(
                prd, *( (root / item["location"]).read_text(encoding="utf-8") for item in product_sources[1:] ),
            )
            for item, text in zip(product_sources, texts, strict=True):
                path = root / item["location"]
                path.write_text(text, encoding="utf-8", newline="\n")
                item["content_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            legacy_errors = validate_frozen_contract_joins(plan, root, run=None)

            next(trace for trace in plan["traces"] if trace["id"] == "PRD-FEATURE")["acceptance_gate_ids"] = []
            explicit_errors = validate_frozen_contract_joins(plan, root, run=None)
        self.assertEqual([], legacy_errors)
        self.assertTrue(
            any("must not be empty" in item for item in explicit_errors),
            explicit_errors,
        )


class ReviewPacketMappingTests(unittest.TestCase):
    def test_relevant_gate_to_test_mapping_is_bounded(self) -> None:
        plan = platform_plan()
        plan["missions"][0]["tasks"][0]["acceptance_matrix"].append(
            {
                "test_id": "TEST-001",
                "trace_ids": ["REQ-001"],
                "criterion": "The shared release regression passes",
            }
        )
        missions = list(plan["missions"])
        mappings, truncated = _relevant_acceptance_mappings(plan, missions)
        self.assertFalse(truncated)
        self.assertEqual(
            [
                {
                    "layer": "final",
                    "verifier_id": "final",
                    "acceptance_test_ids": ["TEST-001", "TEST-002"],
                },
                {
                    "layer": "mission_integration",
                    "mission_id": "M1",
                    "verifier_id": "integrate-m1",
                    "acceptance_test_ids": ["TEST-001"],
                },
                {
                    "layer": "mission_integration",
                    "mission_id": "M2",
                    "verifier_id": "integrate-m2",
                    "acceptance_test_ids": ["TEST-001", "TEST-002"],
                },
            ],
            mappings,
        )


if __name__ == "__main__":
    unittest.main()

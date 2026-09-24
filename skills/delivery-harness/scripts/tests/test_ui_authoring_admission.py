#!/usr/bin/env python3
"""Action-time admission tests for wireframe and HiFi authoring missions."""

from __future__ import annotations

import copy
import sys
import unittest
from argparse import Namespace
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_transition  # noqa: E402
import manifest_fixtures as mf  # noqa: E402
from harness_manifest import (  # noqa: E402
    ManifestError,
    mission_has_ui_authoring_action,
    validate_current_plan_run,
)
from select_ready_nodes import select_ready_nodes  # noqa: E402


REQUIRED_PAIR = ["ui-design-builder", "frontend-design"]


def _source(kind: str, location: str) -> dict[str, object]:
    return {
        "id": "SRC-UI-AUTHORING",
        "kind": kind,
        "location": location,
        "owner": "design",
        "status": "frozen",
        "content_sha256": "d" * 64,
        "source_revision": None,
        "staged_revision": None,
        "notes": "UI authoring admission fixture",
    }


def _configure_m1(
    plan: dict[str, object],
    *,
    scope: str,
    required_skills: list[str],
    source: dict[str, object] | None = None,
) -> dict[str, object]:
    mission = next(item for item in plan["missions"] if item["id"] == "M1")
    mission["write_scope"] = [scope]
    mission["required_skills"] = list(required_skills)
    for task in mission["tasks"]:
        task["write_scope"] = [scope]
    review = next(
        node
        for node in plan["graph"]["nodes"]
        if node.get("kind") == "verifier"
        and node.get("review", {}).get("mission_ids") == ["M1"]
    )
    review["review"]["scope"] = [scope]
    if source is not None:
        plan["sources"].append(source)
    return mission


def _authorized_pair(
    *,
    scope: str,
    required_skills: list[str],
    source: dict[str, object] | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    plan = mf.valid_plan()
    _configure_m1(
        plan,
        scope=scope,
        required_skills=required_skills,
        source=source,
    )
    run = mf.valid_run(plan)
    mf.authorize_execution(run, ["M1"], status="ready")
    run["runtime_capabilities"].update(
        {
            "worker_runtime": "subagent",
            "workspace_mode": "parent_managed_worktree",
            "completion_channel": "agent_result",
            "max_parallel_workers": 1,
            "runtime_adapter": {
                "provider": "codex",
                "available_drivers": ["subagents", "sequential_parent"],
                "detection_source": "observed",
                "capability_probe": mf.native_capability_probe(subagents=True),
                "version_gate": mf.current_version_gate(),
            },
        }
    )
    run["observed"]["runtime"].update(
        {
            "available_worker_slots": 1,
            "isolation_capacity": 1,
            "completion_channel_available": True,
        }
    )
    for action in (
        "spawn_subagents",
        "create_local_worktrees",
        "create_local_branches",
        "create_local_commits",
    ):
        mf.authorize_action(run, action, ["M1"], ["*"])
    return plan, run


def _activate_m1(run: dict[str, object]) -> None:
    run["active_wave"].update(
        {
            "wave_id": "W-UI",
            "status": "active",
            "batch_base_sha": run["integration"]["batch_base_sha"],
            "selected_missions": ["M1"],
            "deferred_missions": [],
            "conflict_edges": [],
        }
    )


def _lease_args() -> Namespace:
    return Namespace(
        mission_id="M1",
        node_id="N-M1",
        worker_id="W-UI",
        lease_id="LEASE-UI",
        attempt_id="ATT-UI",
        branch_ref="refs/heads/codex/ui-authoring",
        worktree_path="C:/repo/worktrees/ui-authoring",
        provider=None,
        driver=None,
        model=None,
        reasoning_effort=None,
        worker_runtime=None,
        workspace_mode=None,
        completion_channel=None,
        task_thread_id=None,
        report_path=None,
    )


class UiAuthoringScopeTests(unittest.TestCase):
    def test_wireframe_and_hifi_authoring_scope_matrix(self) -> None:
        cases = [
            ("default wireframe", "docs/design/wireframes.html", None),
            (
                "custom wireframe source",
                "custom/ux/**",
                _source("wireframe", "custom/ux/flow.html"),
            ),
            (
                "staged wireframe",
                "docs/design/.ui-staging/round-2/wireframes.html",
                None,
            ),
            (
                "broad staging round",
                "docs/design/.ui-staging/round-2/**",
                None,
            ),
            (
                "nested staging HiFi subtree",
                "docs/design/.ui-staging/round-2/hifi/**",
                None,
            ),
            (
                "canonical HiFi page",
                "docs/design/ui-references/round-2/index.html",
                None,
            ),
            (
                "canonical HiFi subtree",
                "docs/design/ui-references/round-2/**",
                None,
            ),
            (
                "custom approved target exact",
                "custom/hifi/index.html",
                _source(" Approved_UI-Target ", "custom/hifi/index.html"),
            ),
            (
                "custom approved target containing scope",
                "custom/hifi/**",
                _source("approved-ui_target", "custom/hifi/index.html"),
            ),
            (
                "custom approved target manifest sibling",
                "custom/hifi/details.html",
                _source("approved ui target", "custom/hifi/index.html"),
            ),
            (
                "mixed-case canonical HiFi subtree",
                "Docs/Design/UI-References/New/**",
                None,
            ),
            (
                "mixed-case canonical HiFi page",
                "Docs/Design/UI-References/New/Index.HTML",
                None,
            ),
            (
                "mixed-case staged subtree",
                "DOCS/DESIGN/.UI-STAGING/New/HiFi/**",
                None,
            ),
            (
                "mixed-case staged page",
                "DOCS/DESIGN/.UI-STAGING/New/Wireframes.HTML",
                None,
            ),
            (
                "mixed-case custom approved target exact",
                "CUSTOM/HIFI/INDEX.HTML",
                _source("approved ui target", "custom/hifi/index.html"),
            ),
            (
                "mixed-case custom approved target subtree",
                "CUSTOM/HIFI/**",
                _source("approved ui target", "custom/hifi/index.html"),
            ),
            (
                "mixed-case custom approved target sibling",
                "CUSTOM/HIFI/Details.HTML",
                _source("approved ui target", "custom/hifi/index.html"),
            ),
        ]
        for label, scope, source in cases:
            with self.subTest(label=label):
                plan = {"sources": [] if source is None else [source]}
                mission = {
                    "write_scope": [scope],
                    "deny_scope": [],
                    "required_skills": REQUIRED_PAIR,
                }
                self.assertTrue(mission_has_ui_authoring_action(plan, mission))

    def test_unrelated_html_and_evidence_json_are_not_ui_authoring(self) -> None:
        plan = {"sources": []}
        for scope in (
            "marketing/landing.html",
            "docs/design/ui-references/round-2/evidence.json",
            "docs/design/.ui-staging/round-2/browser-evidence.json",
        ):
            with self.subTest(scope=scope):
                mission = {
                    "write_scope": [scope],
                    "deny_scope": [],
                    "required_skills": [],
                }
                self.assertFalse(mission_has_ui_authoring_action(plan, mission))

    def test_deny_scope_can_remove_the_entire_authoring_scope(self) -> None:
        mission = {
            "write_scope": ["docs/design/ui-references/round-2/**"],
            "deny_scope": ["docs/design/ui-references/**"],
            "required_skills": [],
        }
        self.assertFalse(mission_has_ui_authoring_action({"sources": []}, mission))

        broad = {
            "write_scope": ["docs/design/**"],
            "deny_scope": [
                "docs/design/wireframes.html",
                "docs/design/ui-references/**",
                "docs/design/.ui-staging/**",
            ],
            "required_skills": [],
        }
        self.assertFalse(mission_has_ui_authoring_action({"sources": []}, broad))

        mixed_same_case_deny = {
            "write_scope": ["Docs/Design/UI-References/New/**"],
            "deny_scope": ["Docs/Design/UI-References/**"],
            "required_skills": [],
        }
        self.assertFalse(
            mission_has_ui_authoring_action(
                {"sources": []}, mixed_same_case_deny
            )
        )

        case_only_deny = {
            "write_scope": ["Docs/Design/UI-References/New/**"],
            "deny_scope": ["docs/design/ui-references/**"],
            "required_skills": [],
        }
        self.assertTrue(
            mission_has_ui_authoring_action({"sources": []}, case_only_deny)
        )

        custom_source = _source("approved ui target", "custom/hifi/index.html")
        custom_same_case_deny = {
            "write_scope": ["CUSTOM/HIFI/Details.HTML"],
            "deny_scope": ["CUSTOM/HIFI/**"],
            "required_skills": [],
        }
        self.assertFalse(
            mission_has_ui_authoring_action(
                {"sources": [custom_source]}, custom_same_case_deny
            )
        )

        custom_case_only_deny = {
            "write_scope": ["CUSTOM/HIFI/Details.HTML"],
            "deny_scope": ["custom/hifi/**"],
            "required_skills": [],
        }
        self.assertTrue(
            mission_has_ui_authoring_action(
                {"sources": [custom_source]}, custom_case_only_deny
            )
        )


class UiAuthoringAdmissionTests(unittest.TestCase):
    def test_wireframe_with_only_builder_is_deferred(self) -> None:
        plan, run = _authorized_pair(
            scope="docs/design/wireframes.html",
            required_skills=["ui-design-builder"],
        )
        self.assertEqual([], validate_current_plan_run(plan, run))

        selection = select_ready_nodes(plan, run)
        deferred = {
            item["node_id"]: item["reason_codes"]
            for item in selection["deferred_nodes"]
        }
        self.assertIn("ui_authoring_skills_missing", deferred["N-M1"])

    def test_custom_approved_target_requires_the_pair(self) -> None:
        plan, run = _authorized_pair(
            scope="custom/hifi/**",
            required_skills=["frontend-design"],
            source=_source("Approved_UI-Target", "custom/hifi/index.html"),
        )
        self.assertEqual([], validate_current_plan_run(plan, run))

        selection = select_ready_nodes(plan, run)
        deferred = {
            item["node_id"]: item["reason_codes"]
            for item in selection["deferred_nodes"]
        }
        self.assertIn("ui_authoring_skills_missing", deferred["N-M1"])

    def test_selector_and_lease_reject_mixed_case_scopes_before_mutation(self) -> None:
        cases = [
            ("Docs/Design/UI-References/Round-2/**", None),
            ("DOCS/DESIGN/.UI-STAGING/ROUND-2/HIFI/**", None),
            (
                "CUSTOM/HIFI/Details.HTML",
                _source("approved ui target", "custom/hifi/index.html"),
            ),
        ]
        for scope, source in cases:
            for declared in (["ui-design-builder"], ["frontend-design"]):
                with self.subTest(scope=scope, declared=declared):
                    plan, run = _authorized_pair(
                        scope=scope,
                        required_skills=declared,
                        source=source,
                    )
                    self.assertEqual([], validate_current_plan_run(plan, run))

                    selection = select_ready_nodes(plan, run)
                    deferred = {
                        item["node_id"]: item["reason_codes"]
                        for item in selection["deferred_nodes"]
                    }
                    self.assertIn("ui_authoring_skills_missing", deferred["N-M1"])
                    self.assertNotIn(
                        "N-M1",
                        [item["node_id"] for item in selection["dispatchable_nodes"]],
                    )

                    _activate_m1(run)
                    before = copy.deepcopy(run)
                    with self.assertRaisesRegex(ManifestError, "requires both"):
                        harness_transition._lease_worker(plan, run, _lease_args())
                    self.assertEqual(before, run)

    def test_pair_is_admitted_and_directive_preserves_declared_skills(self) -> None:
        declared = ["frontend-design", "custom-skill", "ui-design-builder"]
        plan, run = _authorized_pair(
            scope="docs/design/ui-references/round-2/**",
            required_skills=declared,
        )

        selection = select_ready_nodes(plan, run)
        directive = next(
            item
            for item in selection["dispatchable_nodes"]
            if item["node_id"] == "N-M1"
        )
        self.assertEqual(declared, directive["required_skills"])
        self.assertNotIn("design-system-compiler", directive["required_skills"])

        _activate_m1(run)
        harness_transition._lease_worker(plan, run, _lease_args())
        self.assertEqual("worker_running", run["mission_states"]["M1"]["phase"])

    def test_unrelated_html_dispatches_without_the_ui_pair(self) -> None:
        plan, run = _authorized_pair(
            scope="marketing/landing.html",
            required_skills=[],
        )

        selection = select_ready_nodes(plan, run)
        directive = next(
            item
            for item in selection["dispatchable_nodes"]
            if item["node_id"] == "N-M1"
        )
        self.assertEqual([], directive["required_skills"])

    def test_closed_historical_pair_stays_valid_and_is_not_dispatched(self) -> None:
        plan = mf.valid_plan()
        _configure_m1(
            plan,
            scope="docs/design/ui-references/round-2/index.html",
            required_skills=[],
        )
        run = mf.valid_run(plan)
        mf.mark_complete(plan, run)

        self.assertEqual([], validate_current_plan_run(plan, run))
        selection = select_ready_nodes(plan, run)
        self.assertEqual([], selection["dispatchable_nodes"])


if __name__ == "__main__":
    unittest.main()

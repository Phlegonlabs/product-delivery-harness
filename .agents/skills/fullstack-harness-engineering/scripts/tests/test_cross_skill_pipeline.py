#!/usr/bin/env python3
"""Cross-skill contract smoke test from product sources to runtime review."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
SKILLS_ROOT = Path(__file__).resolve().parents[3]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_manifest import validate_plan  # noqa: E402
from select_ready_nodes import _runtime_binding  # noqa: E402
from test_graph_orchestration import graph_node, valid_graph_plan, valid_graph_run  # noqa: E402


class CrossSkillPipelineTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILLS_ROOT / relative_path).read_text(encoding="utf-8")

    def test_prd_and_harness_share_trace_and_lifecycle_contracts(self) -> None:
        prd = self.read("prd-builder/references/output-contract.md")
        prd_lifecycle = self.read("prd-builder/references/artifact-lifecycle.md")
        harness = self.read(
            "fullstack-harness-engineering/references/contract-and-traceability.md"
        )

        for trace in ("PRD-001", "ARCH-001", "UI-001", "UX-001", "TEST-001"):
            self.assertIn(trace, prd)
        # The design system now lives in prd-builder, so its DS families are
        # contracted there and must resolve for the harness's DS-* trace rule.
        for ds_family in ("`DS-*`", "`DS-LAY-*`", "`DS-SUR-*`", "`DS-TYP-*`", "`DS-CTL-*`", "`DS-COMP-*`"):
            self.assertIn(ds_family, prd)
        self.assertIn("`DS-*` ID names an entry that exists in `design-system.json`", harness)
        self.assertIn("content_sha256", harness)
        self.assertIn("immutable `source_revision`", harness)
        self.assertIn("Passing validation does not authorize", prd_lifecycle)

    def test_design_system_pair_publishes_and_freezes_together(self) -> None:
        prd = self.read("prd-builder/references/output-contract.md")
        prd_lifecycle = self.read("prd-builder/references/artifact-lifecycle.md")
        harness = self.read(
            "fullstack-harness-engineering/references/contract-and-traceability.md"
        )

        # Both sides must name both files, or a run can freeze half a contract.
        for source in (prd, prd_lifecycle, harness):
            self.assertIn("design-system.md", source)
            self.assertIn("design-system.json", source)
        self.assertIn("publish together", prd_lifecycle)
        self.assertIn("Freeze both with a `content_sha256`", harness)
        self.assertIn("is `partial`, never `frozen`", harness)

    def test_harness_reads_the_responsive_set_from_the_design_system(self) -> None:
        prd = self.read("prd-builder/references/output-contract.md")
        harness_skill = self.read("fullstack-harness-engineering/SKILL.md")
        harness = self.read(
            "fullstack-harness-engineering/references/contract-and-traceability.md"
        )

        # Exactly-one-of is the rule on both sides; a default set in the harness
        # is what this pins against.
        self.assertIn("exactly one", prd)
        self.assertIn("do not carry a default set in this skill", harness_skill)
        self.assertIn("The harness does not carry its own default set", harness)

    def test_the_retired_middle_skill_is_gone_from_every_contract(self) -> None:
        for relative_path in (
            "prd-builder/SKILL.md",
            "prd-builder/references/output-contract.md",
            "prd-builder/references/artifact-lifecycle.md",
            "fullstack-harness-engineering/SKILL.md",
            "fullstack-harness-engineering/references/contract-and-traceability.md",
            "fullstack-harness-engineering/references/design-input-updates.md",
            "fullstack-harness-engineering/references/verification-gates.md",
            "fullstack-harness-engineering/references/execution-task-decomposition.md",
            "fullstack-harness-engineering/references/platform-archetypes.md",
            "fullstack-harness-engineering/assets/templates/HARNESS_PLAN.template.md",
            "fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md",
        ):
            source = self.read(relative_path)
            for retired in ("ui-architecture-builder", "ui-registry.json", "page-recipes.md"):
                self.assertNotIn(retired, source, f"{relative_path} still references {retired}")

    def test_wireframe_visual_direction_and_harness_conformance_boundary(self) -> None:
        wireframes = self.read("prd-builder/references/wireframe-guide.md")
        harness = self.read("fullstack-harness-engineering/SKILL.md")
        worker_goal = self.read(
            "fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md"
        )

        self.assertIn("Preference & HTML Exploration Handoff", wireframes)
        self.assertIn(
            "low-fidelity wireframes remain canonical for structure and flow",
            wireframes,
        )
        self.assertIn("The normal UI handoff is", harness)
        self.assertIn("frontend-design conformance mode", harness)
        self.assertIn("missing contract entry returns as a design-input delta", harness)
        self.assertIn("frontend-design conformance mode", worker_goal)

    def test_frontend_review_binds_to_the_host_provider_with_plan_selected_model(self) -> None:
        plan = valid_graph_plan()
        review = graph_node(
            "N-FRONTEND-REVIEW",
            "verifier",
            "batch",
            "runtime_worker",
            ["pass", "fix_required", "blocked", "contract_gap"],
            providers=["codex", "claude_code"],
            preferred="claude_code",
            provider_options={
                "claude_code": {"model": "claude-fable-5", "reasoning_effort": "xhigh"},
                "codex": {"model": "gpt-5.6-sol", "reasoning_effort": "xhigh"},
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
        self.assertEqual([], validate_plan(plan))

        runtime = valid_graph_run(plan)["runtime_capabilities"]
        runtime["runtime_adapter"] = {
            "provider": "codex",
            "available_drivers": ["app_threads", "sequential_parent"],
            "detection_source": "observed",
        }
        binding = _runtime_binding(review, runtime)

        # The node's preferred_provider is claude_code, but preferred_provider
        # is no longer consulted: the host actually running this session is
        # codex, so the node binds to codex (its own declared codex options),
        # never to a bridged/guarded claude_code process.
        self.assertEqual("codex", binding["provider"])
        self.assertEqual("host", binding["source"])
        self.assertEqual("app_threads", binding["driver"])
        self.assertEqual("gpt-5.6-sol", binding["model"])
        self.assertEqual("xhigh", binding["reasoning_effort"])


if __name__ == "__main__":
    unittest.main()

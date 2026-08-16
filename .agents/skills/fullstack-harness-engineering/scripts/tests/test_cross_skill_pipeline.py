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
from test_graph_orchestration import (  # noqa: E402
    attach_single_mission_review,
    graph_node,
    valid_graph_plan,
    valid_graph_run,
)


class CrossSkillPipelineTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        return (SKILLS_ROOT / relative_path).read_text(encoding="utf-8")

    def test_prd_and_harness_share_trace_and_lifecycle_contracts(self) -> None:
        prd = self.read("prd-builder/references/output-contract.md")
        prd_lifecycle = self.read("prd-builder/references/artifact-lifecycle.md")
        design = self.read("product-design-builder/references/output-contract.md")
        harness = self.read(
            "fullstack-harness-engineering/references/contract-and-traceability.md"
        )

        for trace in ("PRD-001", "ARCH-001", "UI-001", "UX-001", "TEST-001"):
            self.assertIn(trace, prd)
        # Product traces remain upstream while design traces live in the
        # dedicated design skill consumed by the Harness.
        for ds_family in ("`DS-*`", "`DS-COMP-*`"):
            self.assertIn(ds_family, design)
        self.assertIn("product-design-builder", prd)
        self.assertIn("`DS-*` ID names an entry that exists in `design-system.json`", harness)
        self.assertIn("content_sha256", harness)
        self.assertIn("immutable `source_revision`", harness)
        self.assertIn("Passing validation does not authorize", prd_lifecycle)

    def test_design_system_pair_publishes_and_freezes_together(self) -> None:
        design = self.read("product-design-builder/references/output-contract.md")
        design_lifecycle = self.read(
            "product-design-builder/references/artifact-lifecycle.md"
        )
        prd_lifecycle = self.read("prd-builder/references/artifact-lifecycle.md")
        harness = self.read(
            "fullstack-harness-engineering/references/contract-and-traceability.md"
        )

        # Both sides must name both files, or a run can freeze half a contract.
        for source in (design, design_lifecycle, prd_lifecycle, harness):
            self.assertIn("design-system.md", source)
            self.assertIn("design-system.json", source)
        self.assertIn("Publish the three files as one reconciled set", design_lifecycle)
        self.assertIn("Freeze both with a `content_sha256`", harness)
        self.assertIn("is `partial`, never `frozen`", harness)

    def test_harness_reads_the_responsive_set_from_the_design_system(self) -> None:
        design = self.read("product-design-builder/references/output-contract.md")
        harness_skill = self.read("fullstack-harness-engineering/SKILL.md")
        harness = self.read(
            "fullstack-harness-engineering/references/contract-and-traceability.md"
        )

        # Exactly-one-of is the rule on both sides; a default set in the harness
        # is what this pins against.
        self.assertIn("exactly one responsive verification set", design)
        self.assertIn("do not carry a default set in this skill", harness_skill)
        self.assertIn("The harness does not carry its own default set", harness)

    def test_the_retired_middle_skill_is_gone_from_every_contract(self) -> None:
        for relative_path in (
            "prd-builder/SKILL.md",
            "prd-builder/references/output-contract.md",
            "prd-builder/references/artifact-lifecycle.md",
            "product-design-builder/SKILL.md",
            "product-design-builder/references/output-contract.md",
            "product-design-builder/references/artifact-lifecycle.md",
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
        product_design = self.read("product-design-builder/SKILL.md")
        wireframes = self.read("product-design-builder/references/wireframe-guide.md")
        references = self.read("product-design-builder/references/design-reference-guide.md")
        harness = self.read("fullstack-harness-engineering/SKILL.md")
        design_updates = self.read(
            "fullstack-harness-engineering/references/design-input-updates.md"
        )
        worker_goal = self.read(
            "fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md"
        )

        self.assertIn("## Visual Direction Gate", wireframes)
        self.assertIn(
            "low-fidelity wireframes remain canonical for screen structure",
            wireframes,
        )
        self.assertIn("The gate is required; optional preview tooling is not", wireframes)
        self.assertIn("The published design system records the selected direction ID", wireframes)
        self.assertIn("The normal UI handoff is", harness)
        self.assertIn("mandatory `frontend-design` creation mode", harness)
        self.assertIn("## Mandatory Frontend Design Gate", product_design)
        self.assertIn("`product-design-builder` and `frontend-design`", product_design)
        self.assertIn("frontend-design conformance mode", harness)
        self.assertIn("missing contract entry returns as a design-input delta", harness)
        self.assertIn("frontend-design conformance mode", worker_goal)
        self.assertIn("Design inspiration", design_updates)
        self.assertIn("Page-faithful target", design_updates)
        self.assertIn("non-canonical evidence", design_updates)
        self.assertIn("user explicitly requests faithful conformance", harness)
        self.assertIn("never invoke them automatically", references)
        self.assertIn("design inspiration never enters this matrix", design_updates.lower())

    def test_repository_design_images_enter_the_reference_confirmation_flow(self) -> None:
        product_design = self.read("product-design-builder/SKILL.md")
        harness = self.read("fullstack-harness-engineering/SKILL.md")
        contract = self.read(
            "fullstack-harness-engineering/references/contract-and-traceability.md"
        )
        design_updates = self.read(
            "fullstack-harness-engineering/references/design-input-updates.md"
        )

        for content in (product_design, harness, contract, design_updates):
            self.assertIn("docs/design/", content)
            self.assertIn("repository-relative path", content)
        self.assertIn("candidate design inspiration", harness)
        self.assertIn("SHA-256 content hash", design_updates)
        self.assertIn("docs/goal/evidence/", design_updates)
        self.assertIn("owner-confirmed `RP-*`", design_updates)
        self.assertIn("repository-discovered reference", product_design)
        self.assertIn(
            "never treat repository presence as a page-faithful request",
            product_design,
        )

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
        attach_single_mission_review(plan, review)
        plan["required_reviews"] = ["frontend_code"]
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

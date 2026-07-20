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

    def test_prd_design_and_harness_share_trace_and_lifecycle_contracts(self) -> None:
        prd = self.read("prd-builder/references/output-contract.md")
        prd_lifecycle = self.read("prd-builder/references/artifact-lifecycle.md")
        design = self.read("design-package-builder/references/output-contract.md")
        design_lifecycle = self.read(
            "design-package-builder/references/artifact-lifecycle.md"
        )
        harness = self.read(
            "fullstack-harness-engineering/references/contract-and-traceability.md"
        )

        for trace in ("PRD-001", "ARCH-001", "UI-001", "UX-001", "TEST-001"):
            self.assertIn(trace, prd)
        for trace_prefix in ("`PRD-*`", "`ARCH-*`", "`UI-*`", "`UX-*`", "`TEST-*`", "`DS-*`"):
            self.assertIn(trace_prefix, design)
        self.assertIn("content_sha256", harness)
        self.assertIn("immutable `source_revision`", harness)
        self.assertIn("Passing validation does not authorize", prd_lifecycle)
        self.assertIn("Passing validation does not authorize", design_lifecycle)

    def test_builder_workflows_preserve_trace_contracts_for_the_harness(self) -> None:
        prd_workflow = self.read(
            "prd-builder/assets/templates/CLAUDE_PRD_WORKFLOW.template.js"
        )
        design_workflow = self.read(
            "design-package-builder/assets/templates/CLAUDE_DESIGN_WORKFLOW.template.js"
        )
        plan = self.read(
            "fullstack-harness-engineering/assets/templates/HARNESS_PLAN.template.md"
        )

        for trace in ("PRD", "ARCH", "UI", "UX", "TEST"):
            self.assertIn(trace, prd_workflow)
            self.assertIn(trace, design_workflow)
        self.assertIn("DS IDs", design_workflow)
        self.assertIn('"trace_ids"', plan)
        self.assertIn('"required_reviews"', plan)

    def test_frontend_review_falls_back_to_codex_with_plan_selected_model(self) -> None:
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
            "external_runtimes": [],
        }
        binding = _runtime_binding(review, runtime)

        self.assertEqual("codex", binding["provider"])
        self.assertEqual("app_threads", binding["driver"])
        self.assertEqual("gpt-5.6-sol", binding["model"])
        self.assertEqual("xhigh", binding["reasoning_effort"])


if __name__ == "__main__":
    unittest.main()

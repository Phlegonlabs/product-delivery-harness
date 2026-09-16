#!/usr/bin/env python3
"""Cross-skill contract smoke tests from product definition to delivery."""

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

    def test_product_definition_owns_product_and_stack_before_ui(self) -> None:
        product = self.read("product-definition-builder/SKILL.md")
        contract = self.read("product-definition-builder/references/output-contract.md")
        checker = self.read("product-definition-builder/scripts/check_product_package.py")
        ui = self.read("ui-design-builder/SKILL.md")

        for marker in (
            "Product Definition Approval",
            "Stack Decision Checkpoint",
            "complete frontend and backend architecture",
            "backend/data/auth",
        ):
            self.assertIn(marker, product + contract)
        self.assertIn("full_product_package_checker_errors", self.read("delivery-harness/scripts/harness_contract_join.py"))
        self.assertIn("UI Design Handoff Status", checker)
        self.assertIn("Use this skill only after `product-definition-builder`", ui)
        self.assertIn("does not create wireframes or visual design", product)

    def test_ui_design_builder_owns_wireframe_style_review_and_scores(self) -> None:
        ui = self.read("ui-design-builder/SKILL.md")
        wireframe = self.read("ui-design-builder/references/wireframe-guide.md")
        hifi = self.read("ui-design-builder/references/ui-design-pass.md")
        rubric = self.read("ui-design-builder/references/ui-grading-rubric.md")

        self.assertIn("docs/design/ui-design.md", ui)
        self.assertIn("docs/design/wireframes.html", ui)
        self.assertIn("wireframes/4", wireframe)
        self.assertIn("frontend-design", hifi)
        self.assertIn("impeccable critique", hifi)
        self.assertIn("impeccable audit", hifi)
        self.assertIn("wireframe overall score", rubric)
        self.assertIn("design-reference overall score", rubric)
        self.assertIn("`H2 Layout safety`, `H4 Responsive and edge states`, and `H8 Accessibility`", rubric)
        self.assertIn("## Copy Freeze Gate", wireframe)
        self.assertIn("--require-copy-approved", wireframe)

    def test_motion_and_media_routes_are_typed_and_authorized(self) -> None:
        route = self.read("ui-design-builder/references/motion-and-media-routing.md")
        checker = self.read("ui-design-builder/scripts/check_wireframe_html.py")

        for marker in (
            "`none`",
            "`image`",
            "`motion`",
            "`image + motion`",
            "`gsap-core`",
            "`gsap-timeline`",
            "`gsap-scrolltrigger`",
            "Higgsfield MCP",
            "exact provider/action authorization",
        ):
            self.assertIn(marker, route)
        self.assertIn("VALID_MEDIA_TREATMENTS", checker)
        self.assertIn("generationRoute", checker)
        self.assertIn("reducedMotionFallback", checker)

    def test_design_system_pair_publishes_and_freezes_together(self) -> None:
        design = self.read("design-system-compiler/SKILL.md")
        lifecycle = self.read("design-system-compiler/references/artifact-lifecycle.md")
        harness = self.read("delivery-harness/references/contract-and-traceability.md")

        for source in (design, lifecycle, harness):
            self.assertIn("design-system.md", source)
            self.assertIn("design-system.json", source)
        self.assertIn("Publish or archive the Markdown and JSON files together", lifecycle)
        self.assertIn("Freeze both with a `content_sha256`", harness)
        self.assertIn("half-present pair is `missing` or `partial`", harness)

    def test_harness_uses_ui_design_builder_checker_and_ui_sources(self) -> None:
        join = self.read("delivery-harness/scripts/harness_contract_join.py")
        harness = self.read("delivery-harness/SKILL.md")
        implementation = self.read("delivery-harness/references/ui-implementation-contract.md")

        self.assertIn("sibling_ui_design_scripts_dir", join)
        self.assertIn("ui-design-builder next to delivery-harness", join)
        self.assertIn("ui-design-builder` owns `docs/design/ui-design.md`", harness)
        self.assertIn("Read `PRD.md`, `architecture.md`, `stack-decisions.md`, approved `ui-design.md`", implementation)
        self.assertIn("## System-Conformance Mode", implementation)
        self.assertIn("## Target-Conformance Mode", implementation)
        self.assertIn("load the owner-bound frontend-authoring skill", implementation)
        self.assertIn("apply this document's conformance rules", implementation)
        self.assertNotIn("load `frontend-design` in conformance mode", implementation)
        self.assertIn("approved and copy-frozen page", implementation)
        self.assertIn("never frozen copy", self.read("delivery-harness/references/verification-gates.md"))

    def test_responsive_set_stays_equal_across_product_design_and_harness(self) -> None:
        prd = self.read("product-definition-builder/references/output-contract.md")
        design = self.read("design-system-compiler/references/output-contract.md")
        harness = self.read("delivery-harness/references/contract-and-traceability.md")

        self.assertIn(
            "`` `responsive` ``, and `` `copy` `` field names are invariant",
            prd,
        )
        self.assertTrue(
            "at least three ascending `viewports: 390, 768, 1200` for web" in prd
            or "at least three ascending `viewports: 390, 768, 1200` for hosted web/extensions" in prd
        )
        self.assertIn("one global responsive verification set for homogeneous products", design)
        self.assertIn("one set per `surfaceContracts` entry for hybrids", design)
        self.assertIn("copy the exact approved PRD/wireframe set", design)
        self.assertIn("PRD's `UI-*` surface contract agree exactly", harness)

    def test_ui_references_archive_without_deletion(self) -> None:
        ui_lifecycle = self.read("ui-design-builder/references/artifact-lifecycle.md")
        hifi = self.read("ui-design-builder/references/ui-design-pass.md")
        design_lifecycle = self.read("design-system-compiler/references/artifact-lifecycle.md")

        for source in (ui_lifecycle, hifi):
            self.assertIn("docs/design/ui-references/<run-id>/", source)
        self.assertIn("docs/design/archived/", ui_lifecycle)
        self.assertIn("never delete", ui_lifecycle.lower())
        self.assertIn("Never publish half a pair", design_lifecycle)

    def test_completed_goal_documents_archive_on_completion_declaration(self) -> None:
        harness = self.read("delivery-harness/references/contract-and-traceability.md")
        project_agents = self.read("delivery-harness/assets/templates/PROJECT_AGENTS.template.md")
        promotion = self.read("delivery-harness/references/branch-promotion-contract.md")

        self.assertIn("declares the project or initiative complete", harness)
        self.assertIn("archive on the same instruction", harness)
        self.assertIn("archive_run.py", harness)
        self.assertIn("docs/goal/archived/<YYYYMMDD-HHMMSS>-<run-id>/", harness)
        self.assertIn("writes closed `ARCHIVE_RECEIPT.json`", project_agents)
        self.assertIn("never moves anything under `docs/product/`", project_agents)
        self.assertIn("At RUN close, candidate C", promotion)
        self.assertIn("archive-only commit A", promotion)
        self.assertIn("If separately authorized, `push_archived_candidate.py`", promotion)
        self.assertIn("PENDING_TRUSTED_HOST_PUBLICATION", promotion)
        self.assertIn("never invokes `git push`", project_agents)
        self.assertIn("fresh PLAN/RUN on the same non-default branch from exact A", harness)
        self.assertIn("Only after production verification may activation readiness", promotion)
        self.assertIn("separate exact external-action authorization; it cannot claim readiness", promotion)
        self.assertLess(
            promotion.index("## Managed RUN Archive Before Promotion"),
            promotion.index("## Candidate Gate"),
        )
        self.assertLess(
            promotion.index("## Candidate Gate"),
            promotion.index("## Promote To Main"),
        )

    def test_activation_is_create_once_post_delivery_and_outcome_bound(self) -> None:
        product = self.read("product-definition-builder/SKILL.md")
        lifecycle = self.read("product-definition-builder/references/artifact-lifecycle.md")
        activation = self.read("product-activation/SKILL.md")
        delivery = self.read("delivery-harness/SKILL.md")

        self.assertIn("does not already exist", product)
        self.assertIn("docs/ACTIVATION.md", lifecycle)
        self.assertIn("Never create, edit, reopen, or extend `docs/goal/PLAN.md`", activation)
        self.assertIn(
            "Readiness, measurement handoff, outcome review, and SEO require promotion and production verification",
            delivery,
        )
        self.assertIn("preparation requires a fixed SHA and separate authorization", delivery)

    def test_downstream_skills_always_run_the_full_product_gate_with_repo_root(self) -> None:
        sources = {
            "ui design": self.read("ui-design-builder/SKILL.md"),
            "wireframes": self.read("ui-design-builder/references/wireframe-guide.md"),
            "design system": self.read("design-system-compiler/SKILL.md"),
            "activation": self.read("product-activation/SKILL.md"),
        }
        required = (
            "check_product_package.py",
            "--prd",
            "--architecture",
            "--stack-decisions",
            "--repo-root <repository-root>",
            "--require-filled",
            "--require-approved",
        )
        for label, source in sources.items():
            with self.subTest(label=label):
                for marker in required:
                    self.assertIn(marker, source)
        self.assertIn("always run", sources["activation"])
        self.assertNotIn(
            "When the PRD carries the Product Definition approval marker",
            sources["activation"],
        )

    def test_repository_design_images_require_recorded_confirmation(self) -> None:
        references = self.read("ui-design-builder/references/design-reference-guide.md")
        design_updates = self.read("delivery-harness/references/design-input-updates.md")

        self.assertIn("Record every inspected source", references)
        self.assertIn("Adopt / Adapt / Avoid", references)
        self.assertIn("owner confirmation", design_updates)
        self.assertIn("never by folder discovery", design_updates)

    def test_implementation_plan_sequencing_intent_survives(self) -> None:
        contract = self.read("delivery-harness/references/contract-and-traceability.md")
        self.assertIn("either adopt it in the drafted graph or record a one-line divergence reason", contract)
        self.assertIn("Coverage and trace-ID authority stay with `PRD.md`", contract)

    def test_frontend_review_binds_to_host_provider(self) -> None:
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
            "lineage_id": "REVIEW-FRONTEND",
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
        self.assertEqual("codex", binding["provider"])
        self.assertEqual("app_threads", binding["driver"])
        self.assertEqual("gpt-5.6-sol", binding["model"])


if __name__ == "__main__":
    unittest.main()

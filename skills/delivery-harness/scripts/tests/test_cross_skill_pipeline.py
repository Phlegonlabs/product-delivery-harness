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
        prd = self.read("product-definition-builder/references/output-contract.md")
        prd_lifecycle = self.read("product-definition-builder/references/artifact-lifecycle.md")
        design = self.read("design-system-compiler/references/output-contract.md")
        harness = self.read(
            "delivery-harness/references/contract-and-traceability.md"
        )

        for trace in ("PRD-001", "ARCH-001", "UI-001", "UX-001", "TEST-001"):
            self.assertIn(trace, prd)
        # Product traces remain upstream while design traces live in the
        # dedicated design skill consumed by the Harness.
        for ds_family in ("`DS-*`", "`DS-COMP-*`"):
            self.assertIn(ds_family, design)
        self.assertIn("design-system-compiler", prd)
        self.assertIn("wireframes.html", prd)
        self.assertNotIn("wireframes.md", prd)
        self.assertIn("Approved wireframe", harness)
        self.assertIn("`DS-*` ID names an entry that exists in `design-system.json` when", harness)
        self.assertIn("content_sha256", harness)
        self.assertIn("immutable `source_revision`", harness)
        self.assertIn("Passing validation does not authorize", prd_lifecycle)

    def test_completed_goal_documents_archive_on_completion_declaration(self) -> None:
        harness = self.read(
            "delivery-harness/references/contract-and-traceability.md"
        )
        project_agents = self.read(
            "delivery-harness/assets/templates/PROJECT_AGENTS.template.md"
        )

        self.assertIn("declares the project or initiative complete", harness)
        self.assertIn("run `scripts/archive_run.py` on the same instruction", harness)
        self.assertIn("docs/goal/archived/<YYYYMMDD-HHMMSS>-<run-id>/", harness)
        self.assertIn("Closeout Bar", harness)
        self.assertIn("Never move anything under `docs/product/`", harness)

        # The seeded project AGENTS.md states the same rule directly, so every
        # runtime sees goal-complete archival without loading the reference.
        self.assertIn("archive the finished plan runtime", project_agents)
        self.assertIn("archive the finished plan runtime with", project_agents)
        self.assertIn(
            "scripts/parity_capture.py --out docs/goal/evidence/production",
            project_agents,
        )
        self.assertIn(
            "docs/goal/archived/<YYYYMMDD-HHMMSS>-<run-id>/",
            project_agents,
        )
        self.assertIn("Closeout Bar", project_agents)
        self.assertIn("never moves anything under `docs/product/`", project_agents)
        state = self.read(
            "delivery-harness/references/execution-state-model.md"
        )
        # Activation runs after promotion and before archival so its updates
        # land in the still-live Update Log.
        for source in (project_agents, state):
            self.assertIn("runs after promotion and before archival", source)

    def test_activation_is_create_once_post_delivery_and_outcome_bound(self) -> None:
        product_skill = self.read("product-definition-builder/SKILL.md")
        product_contract = self.read(
            "product-definition-builder/references/output-contract.md"
        )
        product_lifecycle = self.read(
            "product-definition-builder/references/artifact-lifecycle.md"
        )
        activation_skill = self.read("product-activation/SKILL.md")
        activation_contract = self.read(
            "product-activation/references/activation-contract.md"
        )
        delivery_skill = self.read("delivery-harness/SKILL.md")
        deployment = self.read("delivery-harness/references/deployment-contract.md")
        documents = self.read(
            "delivery-harness/assets/templates/DOCUMENTS.template.md"
        )

        self.assertIn("does not already exist", product_skill)
        self.assertIn("preserve it byte-for-byte", product_skill)
        self.assertIn("creates it only when absent", product_contract)
        self.assertIn("Exclude it from the superseded-document inventory", product_lifecycle)
        self.assertIn("Never create, edit, reopen, or extend `docs/goal/PLAN.md`", activation_skill)
        self.assertIn(
            "reported to the delivery parent for recording", activation_skill
        )
        self.assertIn("Exact Action Digest", activation_contract)
        self.assertIn("verified `MS-*` sources", activation_skill)
        self.assertIn("`product-activation` follows required promotion and deployment verification; RUN grants no authority", delivery_skill)
        self.assertIn("## Product Activation Handoff", deployment)
        self.assertIn("| `docs/ACTIVATION.md` | `docs/` |", documents)
        self.assertIn("--require-verified-sources", product_contract)

    def test_design_system_pair_publishes_and_freezes_together(self) -> None:
        design = self.read("design-system-compiler/references/output-contract.md")
        design_lifecycle = self.read(
            "design-system-compiler/references/artifact-lifecycle.md"
        )
        prd_lifecycle = self.read("product-definition-builder/references/artifact-lifecycle.md")
        harness = self.read(
            "delivery-harness/references/contract-and-traceability.md"
        )

        # Both sides must name both files, or a run can freeze half a contract.
        for source in (design, design_lifecycle, prd_lifecycle, harness):
            self.assertIn("design-system.md", source)
            self.assertIn("design-system.json", source)
        self.assertIn("Publish the two design-system files as one reconciled set", design_lifecycle)
        self.assertIn("Freeze both with a `content_sha256`", harness)
        self.assertIn("half-present pair is `missing` or `partial`", harness)
        self.assertIn("No design-system pair is expected", harness)

    def test_responsive_set_stays_equal_across_product_design_and_harness(self) -> None:
        prd = self.read("product-definition-builder/references/output-contract.md")
        design = self.read("design-system-compiler/references/output-contract.md")
        harness_skill = self.read("delivery-harness/SKILL.md")
        harness = self.read(
            "delivery-harness/references/contract-and-traceability.md"
        )

        self.assertIn(
            "`` `responsive` ``, and `` `copy` `` field names are invariant", prd
        )
        self.assertIn("at least three ascending `viewports: 390, 768, 1200` for web", prd)
        self.assertIn("exactly one responsive verification set", design)
        self.assertIn("copied exactly from the approved PRD and wireframe", design)
        self.assertIn("references/contract-and-traceability.md", harness_skill)
        self.assertIn("PRD, approved `wireframes.html`, every PLAN UI surface", harness)
        self.assertIn("The harness carries no default set", harness)

    def test_the_retired_middle_skill_is_gone_from_every_contract(self) -> None:
        for relative_path in (
            "product-definition-builder/SKILL.md",
            "product-definition-builder/references/output-contract.md",
            "product-definition-builder/references/artifact-lifecycle.md",
            "design-system-compiler/SKILL.md",
            "design-system-compiler/references/output-contract.md",
            "design-system-compiler/references/artifact-lifecycle.md",
            "delivery-harness/SKILL.md",
            "delivery-harness/references/contract-and-traceability.md",
            "delivery-harness/references/design-input-updates.md",
            "delivery-harness/references/verification-gates.md",
            "delivery-harness/references/execution-task-decomposition.md",
            "delivery-harness/references/platform-archetypes.md",
            "delivery-harness/assets/templates/HARNESS_PLAN.template.md",
            "delivery-harness/assets/templates/WORKER_GOAL.template.md",
        ):
            source = self.read(relative_path)
            for retired in ("ui-architecture-builder", "ui-registry.json", "page-recipes.md"):
                self.assertNotIn(retired, source, f"{relative_path} still references {retired}")

    def test_prd_visual_direction_and_harness_conformance_boundary(self) -> None:
        prd = self.read("product-definition-builder/SKILL.md")
        ui_pass = self.read("product-definition-builder/references/ui-design-pass.md")
        product_design = self.read("design-system-compiler/SKILL.md")
        directions = self.read("design-system-compiler/references/visual-direction-guide.md")
        references = self.read("design-system-compiler/references/design-reference-guide.md")
        harness = self.read("delivery-harness/SKILL.md")
        ui_contract = self.read(
            "delivery-harness/references/ui-implementation-contract.md"
        )
        design_updates = self.read(
            "delivery-harness/references/design-input-updates.md"
        )
        worker_goal = self.read(
            "delivery-harness/assets/templates/WORKER_GOAL.template.md"
        )

        self.assertIn("run `references/ui-design-pass.md` directly", prd)
        self.assertIn("## Taste Applicability Gate", ui_pass)
        self.assertIn("## Design System Need Gate", ui_pass)
        self.assertIn("only when the human owner explicitly asks", directions)
        self.assertIn("references/ui-implementation-contract.md", harness)
        self.assertIn("## System-Conformance Mode", ui_contract)
        self.assertIn("## Target-Conformance Mode", ui_contract)
        self.assertIn("## Compilation Skills Gate", product_design)
        self.assertIn("`design-system-compiler` and `frontend-design`", product_design)
        self.assertIn("impeccable-concept-generation.md", product_design)
        self.assertIn("frontend-design conformance mode", ui_contract)
        self.assertIn("to `product-definition-builder`", ui_contract)
        self.assertIn("to `design-system-compiler`", ui_contract)
        self.assertIn("frontend-design conformance mode", worker_goal)
        self.assertIn("Design inspiration", design_updates)
        self.assertIn("Page-faithful target", design_updates)
        self.assertIn("non-canonical evidence", design_updates)
        self.assertIn("Only the approved target recorded in the PRD handoff", ui_contract)
        self.assertIn("never invoke them automatically", references)
        self.assertIn("design inspiration never enters this matrix", design_updates.lower())
        self.assertIn(
            "regenerate the affected screens' style layer from the current direction",
            ui_pass,
        )
        self.assertIn(
            "a reference that accumulates styles from previous versions is not approvable",
            ui_pass,
        )
        self.assertIn(
            "refresh the handoff's recorded SHA-256 for that file in the same run",
            ui_pass,
        )
        self.assertIn(
            "Never graft the new reference onto the previous implementation's CSS",
            ui_contract,
        )
        self.assertIn(
            "Implement a changed route from its current approved source only",
            ui_contract,
        )
        self.assertIn(
            "Carrying a superseded style into the accepted delta's implementation "
            "is a contract violation",
            design_updates,
        )
        self.assertIn(
            "The stale-carryover check is the after-side companion", design_updates
        )
        self.assertIn(
            "including removal of superseded styles, endpoints, rules, and flags",
            design_updates,
        )
        self.assertIn(
            "Silently carrying a superseded endpoint, rule, or flag forward "
            "alongside its replacement is a contract violation",
            design_updates,
        )
        self.assertIn(
            "The same check covers backend and app surfaces", design_updates
        )
        self.assertIn(
            "unless the delta records an explicit compatibility retention",
            design_updates,
        )

    def test_wireframes_and_ui_previews_have_separate_authority(self) -> None:
        prd = self.read("product-definition-builder/SKILL.md")
        design = self.read("design-system-compiler/SKILL.md")
        preview = self.read("product-definition-builder/references/ui-design-pass.md")
        ui_contract = self.read(
            "delivery-harness/references/ui-implementation-contract.md"
        )

        self.assertIn("single approved structural and Copy Freeze projection", prd)
        self.assertIn("`wireframes.html`", prd)
        self.assertIn("approved UI Design Handoff", design)
        self.assertIn("approved `wireframes.html`", design)
        self.assertIn("never invokes the provider", preview)
        self.assertIn("matching approved page in `wireframes.html`", ui_contract)
        self.assertIn("never overrides `PRD.md`", ui_contract)
        self.assertIn("implementation-bound", ui_contract)
        self.assertIn("UI Preview Gate outputs", ui_contract)

    def test_approved_html_references_carry_from_design_skills_to_harness_pages(self) -> None:
        prd = self.read("product-definition-builder/SKILL.md")
        preview = self.read("product-definition-builder/references/ui-design-pass.md")
        ui_contract = self.read(
            "delivery-harness/references/ui-implementation-contract.md"
        )
        contract = self.read(
            "delivery-harness/references/contract-and-traceability.md"
        )

        # The UI Design Pass renders one connected design-reference HTML
        # with its loaded design skills and retains the approved file.
        self.assertIn(
            "one self-contained design-reference HTML review file", prd
        )
        self.assertIn(
            "one connected review surface",
            preview,
        )
        self.assertIn("a left sidebar", preview)
        self.assertIn("Every visible product control responds", preview)
        self.assertIn("authentication-error preview scenes are omitted", preview)
        self.assertIn("generationStatus: deferred", preview)
        self.assertIn("request retention by default", preview)
        self.assertIn("cannot implement from an HTML reference", preview)
        # Harness then builds each bound page from the shared approved reference.
        self.assertIn("implemented from that shared reference", ui_contract)
        self.assertIn("markup, styles, assets, and rendered behavior", ui_contract)
        self.assertIn(
            "binding target evidence, not a preview to reinterpret", ui_contract
        )
        self.assertIn("approved all-screens HTML reference file's SHA-256", contract)

    def test_ui_references_folder_archives_superseded_sets_like_documents(self) -> None:
        preview = self.read("product-definition-builder/references/ui-design-pass.md")
        prd_lifecycle = self.read("product-definition-builder/references/artifact-lifecycle.md")
        design_lifecycle = self.read(
            "design-system-compiler/references/artifact-lifecycle.md"
        )
        design_updates = self.read(
            "delivery-harness/references/design-input-updates.md"
        )

        # Approved HTML references live in one dedicated folder on every side.
        for source in (preview, prd_lifecycle, design_lifecycle, design_updates):
            self.assertIn("docs/design/ui-references/<run-id>/", source)
        # A superseded set archives like superseded documents; nothing is deleted.
        self.assertIn("docs/design/archived/<YYYYMMDD-HHMMSS>-<run-id>/", preview)
        self.assertIn("docs/design/archived/<YYYYMMDD-HHMMSS>-<run-id>/", prd_lifecycle)
        self.assertIn("docs/design/archived/", design_lifecycle)
        self.assertIn("mirroring how superseded product documents move", prd_lifecycle)
        self.assertIn("Never delete a superseded reference file", preview)
        self.assertIn("no live contract points at an archived reference", prd_lifecycle)
        # Harness consumes the references only through the recorded handoff.
        self.assertIn("never by folder discovery", design_updates)

    def test_repository_design_images_enter_the_reference_confirmation_flow(self) -> None:
        prd = self.read("product-definition-builder/SKILL.md")
        product_design = self.read("design-system-compiler/SKILL.md")
        harness = self.read("delivery-harness/SKILL.md")
        contract = self.read(
            "delivery-harness/references/contract-and-traceability.md"
        )
        design_updates = self.read(
            "delivery-harness/references/design-input-updates.md"
        )

        for content in (prd, harness, contract, design_updates):
            self.assertIn("docs/design/", content)
        for content in (contract, design_updates):
            self.assertIn("repository-relative path", content)
        self.assertIn("references/design-input-updates.md", harness)
        self.assertIn("candidate design inspiration", design_updates)
        self.assertIn("SHA-256 content hash", design_updates)
        self.assertIn("docs/goal/evidence/", design_updates)
        self.assertIn("owner confirmation", design_updates)
        self.assertIn("Repository-discovered images remain non-canonical", product_design)

    def test_implementation_plan_sequencing_intent_survives_into_the_plan(self) -> None:
        contract = self.read(
            "delivery-harness/references/contract-and-traceability.md"
        )

        # A present implementation-plan.md's sequencing intent is mandatory
        # input: adopt it or record a divergence reason — never a silent drop.
        self.assertIn(
            "either adopt it in the drafted graph or record a one-line "
            "divergence reason in the PLAN",
            contract,
        )
        self.assertIn(
            "Coverage and trace-ID authority stay with `PRD.md`, "
            "`architecture.md`, and `stack-decisions.md`",
            contract,
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

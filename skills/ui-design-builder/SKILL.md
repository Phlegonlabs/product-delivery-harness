---
name: ui-design-builder
description: Turn an approved Product Definition into an owner-approved UI design package. Use after product-definition-builder for UI intake, direction studies, motion and media intent, frontend-design style integration, connected HiFi design-reference HTML, machine completeness review, Impeccable review, PRD-bound scoring, visual approval, and the Design System Need Gate. Do not use for product scope, backend architecture, technology-stack selection, or production implementation.
---

# UI Design Builder

## Installed Commands

Resolve `<ui-design-builder-skill-root>` to the absolute directory containing this installed SKILL.md. Resolve sibling skill roots from the same installation (normally `~/.agents/skills/`). Quote script paths, keep the working directory and `--repo-root` at the target project, and never assume that project contains `skills/`. In references, `skills/<name>/scripts/`, `<name>/scripts/`, and bare `scripts/` are logical installed-skill paths: expand them to the observed absolute skill root before execution. Repository maintenance and CI commands still run from this source repository.

## Purpose

At every invocation, apply `../delivery-harness/references/document-sync-contract.md`. During accepted delivery, use `../delivery-harness/references/bounded-enhancement.md` for same-scope corrections and next-round gaps; do not repeat initial design choices for a repair that restores the frozen design. Model the PRD's synthetic personas and loading, empty, permission, expired-session, failure, and recovery states. A mockup or HTML native projection is not real-login or native E2E evidence; that belongs to Harness.

Use this skill only after `product-definition-builder` has produced an owner-approved `PRD.md`, `architecture.md`, and `stack-decisions.md`. Product Definition decides what the product does and which frontend, backend, data, auth, deployment, mobile, and commercial technologies it uses. This skill decides how the approved UI is structured and expressed.

For every UI-bearing product, this skill owns:

- `docs/design/ui-design.md`;
- direction studies under `docs/design/directions/<round>/`;
- retained all-screens HiFi references under `docs/design/ui-references/<run-id>/`; and
- the Style Intake, Motion and Media Intent, Direction Selection, HiFi Completeness Preflight, HiFi Review, Visual Approval, and Design System Need gates.

Existing wireframes and old design-system pairs remain inspection and validation evidence. They are not inputs to a new `ui-design/3` package and never acquire new approval authority.

It does not change product scope, routes, actions, states, responsive targets, copy responsibilities, architecture, or stack by implication. Return those changes to `product-definition-builder` and resume only from a newly approved Product Definition revision.

At direction review and HiFi review, apply `../product-definition-builder/references/prd-refinement.md` to newly discovered journey, state, content and recovery gaps. Link evidence and affected PRD/UI/TEST IDs in the existing change record; distinguish a design defect from a missing product decision. Keep frozen product inputs intact until their owning flow resolves a contract gap. Continue unaffected design work.

Apply [Generate, Verify And Correct](../delivery-harness/references/gen-verify-correct.md) at direction and HiFi checkpoints. The bound frontend author repairs accepted-scope design defects and reruns the focused check; owners retain human selections and approvals.

## Stage Routing

Read the owning section before its matching action. Domain and direction guidance stays conditional.

- Before UI research or authorship, read [Required Skills And Inputs](references/stages/ui-design.md#required-skills-and-inputs).
- Before directions, HiFi or design repair, read the required inputs and [Workflow](references/stages/ui-design.md#workflow). Full initial authoring follows the complete required procedure in [Workflow](references/stages/ui-design.md#workflow).
- Before handoff self-review, read [Author Self-Review Before Handoff](references/stages/ui-design.md#author-self-review-before-handoff).
- Before unresolved visual, motion, reference or platform decisions, read [Reference Routing](references/stages/ui-design.md#reference-routing).

## Entry Boundary

- A new round requires the approved Product Definition and Stack Decision Checkpoint, with the package's exact UI contract.
- The host's actual `frontend_worker` is the single UI author. The actual writer loads the complete pinned `frontend-design` skill; a parent read does not author design.
- Enhancements author only added or changed pages and necessary connecting flows. Routine maintenance does not rebuild historical HiFi or reopen frozen approvals.
- Direction and HiFi authorship retain the required preflight, Impeccable critique/audit, browser evidence and H1-H9, then one human Visual Approval.

## Design Lifecycle

Use `references/review-workflow.md` to classify this round. New initial design and explicit full redesign use `ui-design/3`; retained `ui-design/2` packages keep their original sequence. Use the package selection rule in [Required Skills And Inputs](references/stages/ui-design.md#required-skills-and-inputs) for the product preflight. Enhancements start from the current accepted product and author added/changed pages plus necessary connecting flows. Retain the accepted direction for unchanged enhancement scope; do not restart direction selection for unchanged decisions. Routine maintenance edits the actual product, effective requirements and existing change record directly; it does not require rebuilding HiFi or synchronizing historical tokens. An accepted product change is not blocked solely because historical HiFi differs. No historical decision is rewritten into a new approval.

## Review And Repair Boundaries

- Author directions and HiFi from the PRD contract, not from an implied page skeleton. The design author may choose hierarchy, grouping, section rhythm, typography, density and visual treatment; it may not add a page, route, control, state, responsive target, operation, copy obligation or integration.
- Keep selected direction and approved HiFi identities traceable. A changed candidate needs applicable fresh evidence. The compiler writes a separate formal-pair preview; it never changes historical approvals.

- `frontend-design` is the single design author for directions and HiFi. It owns visual-direction and frontend-authoring judgment, not contract compilation or implementation conformance. Impeccable is a separately authorized, required quality review; its critique and audit PASS gate Visual Approval.
- Impeccable's full critique follows its own capability and subagent-authorization contract. Missing authorization is not capability failure and never grants delegation.
- New machine observations use `ui-evidence/3` without a human owner or attestation. `ui-evidence/2` retains its historical human-attested semantics and is never fabricated or relabeled. Only the actual owner supplies direction and Visual Approval.
- Keep copy source/completeness and PRD responsibilities valid. A changed product decision returns upstream; composition repairs inside accepted scope reuse authorization. Copy is reviewed with the full HiFi.
- HiFi checks use one complete diagnostic wave, one consolidated repair batch, and one re-review after the cheap completeness gate. Another failure stops at `blocked` unless the owner explicitly approves one changed strategy and acceptance matrix.
- Repair re-review follows `references/ui-grading-rubric.md#repair-re-review-scope`: original defects and affected consumers, with mandatory Impeccable checks and complete current evidence.
- Numeric scores summarize quality; they never override a PRD contradiction, broken browser matrix, inaccessible required flow, dead control, or missing human approval.
- The HiFi overall score is advisory. Keep every dimension threshold, actual-score consistency check and required Impeccable verdict.
- A generated image or motion asset is optional unless the approved Motion and Media Intent record makes it required. Provider failure never authorizes a substitute treatment.

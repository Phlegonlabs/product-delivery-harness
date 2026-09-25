---
name: ui-design-builder
description: Turn an approved Product Definition into an owner-approved UI design package. Use after product-definition-builder for UI intake, responsive structural wireframes, motion and media intent, frontend-design style integration, connected HiFi design-reference HTML, Impeccable review, PRD-bound scoring, visual approval, and the Design System Need Gate. Do not use for product scope, backend architecture, technology-stack selection, or production implementation.
---

# UI Design Builder

## Installed Commands

Resolve `<ui-design-builder-skill-root>` to the absolute directory containing this installed SKILL.md. Resolve sibling skill roots from the same installation (normally `~/.agents/skills/`). Quote script paths, keep the working directory and `--repo-root` at the target project, and never assume that project contains `skills/`. In references, `skills/<name>/scripts/`, `<name>/scripts/`, and bare `scripts/` are logical installed-skill paths: expand them to the observed absolute skill root before execution. Repository maintenance and CI commands still run from this source repository.

## Purpose

At every invocation, apply `../delivery-harness/references/document-sync-contract.md`. During accepted delivery, use `../delivery-harness/references/bounded-enhancement.md` for same-scope corrections and next-round gaps; do not repeat initial design choices for a repair that restores the frozen design. Model the PRD's synthetic personas and loading, empty, permission, expired-session, failure, and recovery states. A mockup or HTML native projection is not real-login or native E2E evidence; that belongs to Harness.

Use this skill only after `product-definition-builder` has produced an owner-approved `PRD.md`, `architecture.md`, and `stack-decisions.md`. Product Definition decides what the product does and which frontend, backend, data, auth, deployment, mobile, and commercial technologies it uses. This skill decides how the approved UI is structured and expressed.

For every UI-bearing product, this skill owns:

- `docs/design/ui-design.md`;
- `docs/design/wireframes.html`;
- retained all-screens HiFi references under `docs/design/ui-references/<run-id>/`; and
- the Style Intake, Motion and Media Intent, Wireframe Validation, Style Integration, HiFi Review, Visual Approval, and Design System Need gates.

It does not change product scope, routes, actions, states, responsive targets, copy responsibilities, architecture, or stack by implication. Return those changes to `product-definition-builder` and resume only from a newly approved Product Definition revision.

At wireframe validation and HiFi review, apply `../product-definition-builder/references/prd-refinement.md` to newly discovered journey, state, content and recovery gaps. Link evidence and affected PRD/UI/TEST IDs in the existing change record; distinguish a design defect from a missing product decision. Keep frozen product inputs intact until their owning flow resolves a contract gap. Continue unaffected design work.

## Required Skills And Inputs

1. **Load and use `frontend-design` before wireframes, directions, HiFi or design repairs.** Immediately before Wireframe authoring or repair, and again before direction/HiFi authoring or repair, run `python "<delivery-harness-skill-root>/scripts/check_skill_bindings.py" --agents-md <target-AGENTS.md> --stage ui-design` using Installed Commands resolution. The actual writer must load the full owner-pinned `frontend-design` skill in its own context; a parent read, source snapshot, role title or earlier-stage check is no substitute. Never backfill usage evidence or silently replace the binding. Missing or conflicting dependencies block only the dependent authoring stage; preserve earlier approvals and closed historical records. This rule grants no spawn action, and a direct parent may be the writer. Assemblers and reviewers build the shell or validate; they do not make product-design decisions. Record the observed digest, retained `SKILL.md` snapshot path/hash, candidate path/hash and applied choices in `### Frontend Design Usage`; every stage digest must match the snapshot. Wireframes use its hierarchy, layout and interaction methods in grayscale and have no Tokens or Design System Draft view; HiFi uses its full visual methods. Taste may supplement an approved direction, never replace the author.
2. Use `impeccable` only as a separately authorized quality workflow for the HiFi review: one `critique` and one `audit`. It does not author the selected direction or edit the candidate, and its side effects require their own explicit authorization; it is not the publication gate.
3. Require an approved Product Definition and Stack Decision Checkpoint. Before UI work, run `python "<product-definition-builder-skill-root>/scripts/check_product_package.py" --prd <approved PRD.md> --architecture <approved architecture.md> --stack-decisions <approved stack-decisions.md> --repo-root <repository-root> --require-filled --require-approved` from the repository root.
4. Read the complete PRD UI Surface Contract and the approved frontend stack, including component foundation and styling approach. A design that needs a stack change returns upstream before wireframing or Style Integration continues.
5. Read `references/artifact-lifecycle.md` and inspect any existing `ui-design.md`, `wireframes.html`, retained references, and design-system pair before drafting. Preserve stable `UI-*`, `UX-*`, `VD-*`, `REF-*`, and `RP-*` identities.

## Design Lifecycle

Use `references/review-workflow.md` to classify this round. Initial design and explicit full redesign use the full sequence. Enhancements start from the current accepted product and author added/changed pages plus necessary connecting flows. Routine maintenance edits the actual product, effective requirements and existing change record directly; it does not require rebuilding Wireframe/HiFi or synchronizing historical tokens. An accepted product change is not blocked solely because historical HiFi differs. No historical decision is rewritten into a new approval.

## Workflow

For initial UI work and affected frontend/mobile enhancements, apply `references/enhancement-recommendations.md`. Reuse supplied decisions, proactively recommend task-fit reference/CSS or native treatments, and carry explicit hero/motion requests into the existing UI/MM records. Recommendations never replace the existing approvals or actual platform evidence.

Before choosing incremental work, inspect the owner instruction for **full design rebuild with retained PRD**. Follow `references/design-translation.md` for that explicit exception, reading UX and iPhone scope. After skill updates and before implementation, apply `references/design-freshness.md`. Rebuild changes design authority, not product scope or filesystem permissions.

Enhancement mode takes precedence over the initial-design sequence below unless the owner explicitly selected a full design rebuild. Apply `references/enhancement-recommendations.md`'s Incremental UI Scope: add or patch only accepted pages/regions and connecting controls, retain every unaffected product screen and the approved direction, and record the before/after scope. Do not restart the all-screen authoring sequence, intake or direction selection for unchanged decisions. Complete package coverage means existing screens plus the delta, not redrawing existing screens. Re-run required validation and renew only affected decisions without rewriting old approval receipts.

1. Confirm the approved Product Definition and stack. Read `references/ui-design-intake.md` and `references/motion-and-media-routing.md`. Combine unanswered design, imagery and motion questions into one intake. Explicitly ask about unresolved reference images, screenshots, websites, Figma views or products, what to learn and what to avoid. Extend the Visual Preference Brief with the Design Brief in the existing UI intake. Reuse existing decisions; wait only for answers that block the next step.
2. Load `frontend-design`, translate the PRD with `references/design-translation.md`, and author the affected structure using `references/wireframe-guide.md`. New packages use `wireframes/5`, `structureStatus` and `copyInventory.locale`. Preserve typed copy sources, dynamic display contracts, actions, states and each platform's responsive rules. Keep product composition grayscale. Do not add a Tokens or Design System Draft route.
3. Run structure completeness, PRD joins, real-browser interactions and W1–W5. Require overall and W5 scores at least 80, every dimension at least 60, and no block. Record `## Wireframe Validation` and run `--require-structure-validated`. This is internal validation: there is no separate Copy Freeze or human Wireframe Approval in the new flow. Copy remains complete and sourced; the owner reviews it with HiFi.
4. With `frontend-design`, produce the requested direction studies over the same representative primary/stress cases and relevant platforms. Retain existing direction decisions for unchanged enhancement scope. Ask the owner to approve/select/mix/reject a new direction. Do not invent this decision. Simple functional motion may use CSS/WAAPI; scripted work follows the existing GSAP routes. Provider generation still needs its exact authorization.
5. Use `frontend-design` to author the complete connected `ui-hifi/2` package with the shared reviewer assembled by the official tools. Apply `references/output-contract.md`: App, Web front and administration groups, one product canvas, each platform's sizes/states with real switchable variants, working product menus and tabs, and a dedicated source-derived Design Tokens view with token purposes. Keep reviewer shell/panels isolated from product CSS. Preserve the restrictive CSP, page hashes and all product interaction destinations. HTML native projections remain design evidence, not native implementation evidence.
6. Run Impeccable critique/audit under the existing authorization, the browser matrix and H1–H9 before human review. New observations use `ui-output/3` and `ui-evidence/3`; separate machine results, qualitative assessments and human decisions. Consolidate defects, let the same `frontend-design` author repair them, and rerun checks on the actual changed candidate. Readiness still requires overall at least 90, H2/H4/H8 at least 90, H5/H7/H9 at least 80, every dimension at least 60, and no block or dispute.
7. Present the complete current HiFi entry, every manifest-listed sibling page, validated wireframe and affected `ui-design.md` handoff using verified absolute Markdown links. Request one **Visual Approval** covering copy, structure, menus, tabs, all other interactions, visuals and tokens. Use final logical paths in the authorized publication checkout, then canonical files in the source checkout after publication. Do not collect approval on `.ui-staging` paths. State scope and review focus. A preview panel is convenience only. Missing or stale pages/evidence block readiness. Wait for the explicit human decision; record owner, date, exact candidate and scope. Preserve valid authorization for same-scope repairs.
8. Apply the **Design System Need Gate** after Visual Approval. Only `required` invokes `design-system-compiler`. Its exact temporary marker is `Compiled design system pair: pending — design-system-compiler`; normal publication rejects it. `not_required` uses the approved HiFi/UI/PRD contract and records existing-pair disposition.
9. Run the normal publication checker at final logical paths in the authorized publication checkout. Retain every sibling, evidence file and required pair/preview. Publication, installation, commits and archival retain their separate authorization boundaries. The approved HiFi is the design baseline for this round's initial implementation.

## Review And Repair Boundaries

- Author interactive grayscale wireframes with complete sourced copy, task-fit composition and declared journeys. Editable flows need working local inputs and outcomes. W1–W5 remains an internal gate.
- Keep validated wireframe and approved HiFi identities traceable. A changed candidate needs applicable fresh evidence. The compiler writes a separate formal-pair preview; it never changes historical approvals.

- `frontend-design` is the single design author for wireframes and HiFi. It owns visual-direction and frontend-authoring judgment, not contract compilation or implementation conformance. Impeccable is a separately authorized quality workflow, not a publication gate.
- Impeccable's full critique follows its own capability and subagent-authorization contract. Missing authorization is not capability failure and never grants delegation.
- New machine observations use `ui-evidence/3` without a human owner or attestation. `ui-evidence/2` retains its historical human-attested semantics and is never fabricated or relabeled. Only the actual owner supplies direction and Visual Approval.
- Keep copy source/completeness and PRD responsibilities valid. A changed product decision returns upstream; composition repairs inside accepted scope reuse authorization. Copy is reviewed with the full HiFi.
- The wireframe and HiFi checks each use one complete diagnostic wave, one consolidated repair batch, and one re-review. Another failure stops at `blocked` unless the owner explicitly approves one changed strategy and acceptance matrix.
- Numeric scores summarize quality; they never override a PRD contradiction, broken browser matrix, inaccessible required flow, dead control, or missing human approval.
- A generated image or motion asset is optional unless the approved Motion and Media Intent record makes it required. Provider failure never authorizes a substitute treatment.

## Reference Routing

- Read `references/enhancement-recommendations.md` for baseline review, scoped recommendations, hero/motion completeness and Web/native before/after studies.

- Read `references/page-design-profiles.md` to map landing, portfolio, dashboard, data and form pages to scoped typography, motion, headline and density defaults in the existing Design Brief.

- Read `references/modern-design-sources.md` for sourced Web/native baselines and AI-assisted design practices; apply relevant guidance without importing another stack, skill dependency or design authority.

- Read `references/ui-design-intake.md` before asking UI direction questions.
- Read `references/motion-and-media-routing.md` for placeholder type, CSS/WAAPI, GSAP, and Higgsfield routing.
- Read `references/design-reference-guide.md` before inspecting or recording a visual reference or direction.
- Read `references/wireframe-guide.md` for `wireframes.html` structure and internal browser validation.
- Read `references/ui-design-pass.md` for Style Integration, the connected HiFi reference, Impeccable review, visual approval, and the Design System Need Gate.
- Read `references/ui-grading-rubric.md` before scoring either wireframes or HiFi. Apply its Layout Integrity And Anti-Slop Review during HiFi authoring and repair as well as review; scores cannot clear collapsed controls, clipped content or unreachable layers.
- Read `references/output-contract.md` for `ui-design.md` and evidence fields.
- Read `references/artifact-lifecycle.md` before staging, publishing, archiving, or replacing UI artifacts.

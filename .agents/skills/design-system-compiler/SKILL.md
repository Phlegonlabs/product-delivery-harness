---
name: design-system-compiler
description: Create or refine an implementation-ready frozen design-system contract (`design-system.md` and `design-system.json`) only when an approved PRD UI Design Handoff says a formal pair is required. Use for design systems, design tokens, UI primitives, product-component contracts, responsive/state matrices, or design-input deltas. The default path compiles an already approved UI direction and wireframes; it does not rerun Taste, concept generation, or preview selection.
---

# Design System Compiler

## Purpose

Turn an approved UI direction into two binding reusable UI sources:

- `design-system.md` for the selected visual direction and short human-facing rules; and
- `design-system.json` for machine-readable tokens, primitives, closed variants, product components, motion, responsive rules, source paths, and the state matrix.

This skill is optional. Invoke it only when an explicitly requested visual-design phase has produced an approved UI Design Handoff and `PRD.md` records `Design System Need Gate: required`. `PRD.md` owns product scope, structure, behavior, Builder UX Direction, and the approved UI Design Handoff. Approved `wireframes.html` is its low-fidelity interactive review projection. Do not duplicate or change those contracts, rerun visual exploration by default, implement production UI code, or create Harness PLAN/RUN state.

## Compilation Skills Gate

Before creating or revising a formal pair:

1. Confirm that the installed skill with exact frontmatter name `frontend-design` is available.
2. Load it with `design-system-compiler` in contract-compilation mode. It translates the approved direction into a coherent token, primitive, component, motion, responsive, and state system; it does not choose a new direction.
3. If `frontend-design` cannot be loaded, stop. Do not draft, revise, or validate the pair through a fallback path.

For a Harness design-source mission, `required_skills` must contain `design-system-compiler` and `frontend-design`. This is distinct from Harness UI implementation conformance mode, which obeys frozen sources and does not revise them.

Do not reload `design-taste-frontend` or `impeccable` merely to compile the pair. Their approved consequences, when used, are already frozen in `PRD.md`'s UI Design Handoff. Reopen visual direction only when the human owner explicitly asks; follow the bounded expansion in Reference Routing, return the selected result to `product-definition-builder` for approval and recording, and restart compilation from that updated source.

## Inputs And Ownership

Read the current sources in full before drafting:

- `PRD.md`, including its UI surface contract, Builder UX Direction Decision, approved `### UI Design Handoff`, and `Design System Need Gate: required` decision;
- approved `wireframes.html`, including its matching `UI-*` page, complete viewport or size-class set, state, region, per-target layout, and passing browser overlap/overflow review, plus `PRD.md`'s `### Wireframe Approval` record;
- `architecture.md` and `stack-decisions.md` when they constrain platform, rendering, accessibility, performance, or component sources;
- existing `design-system.md` and `design-system.json` for an enhancement or delta; and
- the immutable approved UI target and any confirmed `REF-*` / `RP-*` evidence named by the handoff.

Read `market-research.md` only when the handoff cites its `MR-*` evidence. Repository-discovered images remain non-canonical design inspiration unless the PRD handoff explicitly promotes one to a scoped page-faithful target with its hash, route, state, responsive scope, and tolerance.

If a required source is named but missing or unreadable, stop and request its path or contents. A statement that an approved source exists is not a substitute for reading it.

If an existing pair or staged revision describes the same product, enhance it. Preserve unaffected content and stable `UI-*`, `UX-*`, `DS-*`, and `DS-COMP-*` IDs. Never regenerate the pair from a blank slate.

Product scope, route, structure, content, action, flow, state, wireframe, or approved-target gaps return to `product-definition-builder` or the named product owner. A treatment that needs one of those changes is a finding, not permission to edit the source.

## Workflow

1. Confirm that `PRD.md` says `Design System Need Gate: required`. If it says `not_required` or `blocked`, stop; this skill should not have been invoked.
2. Pass the Compilation Skills Gate.
3. Verify that the PRD UI surface contract, approved Wireframe Approval, approved UI Design Handoff, immutable UI target, and approved `wireframes.html` are complete and consistent. If not, return a bounded update to `product-definition-builder` and wait.
4. Read `references/design-system-guide.md`. Use `frontend-design` to translate only the approved visual consequences, real controls, repeated compositions, states, and responsive needs into the smallest complete implementation contract.
5. Build `design-system.json`, write the short rationale in `design-system.md`, and reconcile names, required content order, the exact PRD/wireframe responsive set, per-target rules, states, browser-matrix evidence, and target provenance against the PRD and wireframes.
6. Run the validation commands and the final checklist in `references/output-contract.md`.
7. Stage and publish both files together using `references/artifact-lifecycle.md`. When called from `product-definition-builder`, return the validated pair to that parent workflow.

## Validation

Run these from the repository root:

```text
python .agents/skills/design-system-compiler/scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --write
python .agents/skills/design-system-compiler/scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --require-filled
python .agents/skills/design-system-compiler/scripts/check_color_contrast.py <the arguments required by the staged design system>
python .agents/skills/design-system-compiler/scripts/check_type_scale.py <the arguments required by the staged design system>
```

Also confirm:

- the Design System Need Gate is `required` and names its owner and reason;
- every PRD UI surface has an addressable route or an explicit `n/a` reason;
- every UI surface maps to an approved `wireframes.html` page with matching regions, states, responsive set, and per-target order, visibility, spans, reflow, and interaction rules;
- the approved UI target, Taste applicability record, visual approval, scope, hash, exact responsive coverage, passing browser-matrix evidence, and tolerance are present in the UI Design Handoff;
- every surface covers the final state matrix or records `<state>: n/a - <reason>` in `PRD.md`;
- every required UI element maps to a registered primitive or product component;
- exactly one responsive set with at least two targets exists: web `viewports` or native or desktop `sizeClasses`, and it matches the PRD and approved wireframe set;
- no unresolved placeholder, page-local value, or one-off control remains; and
- `design-system.md` and `design-system.json` publish together and agree through the pair checker.

## Reference Routing

- Read `references/design-system-guide.md` for normal contract compilation.
- Read `references/output-contract.md` for artifact boundaries and quality checks.
- Read `references/artifact-lifecycle.md` before creating staging files or publishing.
- Use `assets/templates/DESIGN_SYSTEM.template.md` and `assets/templates/DESIGN_SYSTEM.template.json` for the pair.
- Use the three scripts under `scripts/` for deterministic pair, contrast, and type-scale validation.
- Only when the owner explicitly asks to reopen direction, read `references/visual-direction-guide.md`, `references/design-reference-guide.md`, and `references/impeccable-concept-generation.md`; load `impeccable`, `frontend-design`, and the design method selected by the PRD UI Design Handoff. Use `../product-definition-builder/references/ui-design-pass.md` for Taste applicability and provider-neutral previews. Return the result upstream for human approval instead of writing the pair against an unrecorded direction.

## Output Rules

- Default artifacts to English unless the user requests another language.
- Keep the design system implementation-facing.
- Keep candidate directions, reference analysis, and preview artifacts outside the published pair.
- Keep stable trace IDs across revisions; do not reuse retired IDs for different meanings.
- Builder approval proves direction conformance, not usability. Record unresolved validation needs.
- Report exact staged and published paths, validation results, assumptions, and every intentionally unresolved gap.

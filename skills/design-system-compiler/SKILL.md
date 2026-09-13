---
name: design-system-compiler
description: Create or refine an implementation-ready frozen design-system contract (`design-system.md` and `design-system.json`) only from an approved Product Definition, Stack Decision Checkpoint, wireframe, and PRD UI Design Handoff whose gate requires a formal pair. Use for design tokens, primitives, product-component contracts, responsive/state matrices, or design-input deltas.
---

# Design System Compiler

## Purpose

Turn an approved UI direction into two binding reusable UI sources:

- `design-system.md` for the selected visual direction and short human-facing rules; and
- `design-system.json` for machine-readable tokens, primitives, closed variants, product components, motion, responsive rules, source paths, and the state matrix.

This skill is optional. Invoke it only when Product Definition Approval and the Stack Decision Checkpoint are approved, the visual phase has an approved UI Design Handoff, and `PRD.md` records `Design System Need Gate: required`. The compiler respects the approved component foundation and styling approach; it never changes stack by implication. `PRD.md` owns product scope, structure, behavior, Builder UX Direction, and the UI Design Handoff; approved `wireframes.html` is its structural projection. Do not duplicate or change those contracts, implement production UI, or create Harness PLAN/RUN state.

## Compilation Skills Gate

Before creating or revising a formal pair:

1. Confirm that the installed skill with exact frontmatter name `frontend-design` is available.
2. Load it with `design-system-compiler` in contract-compilation mode. It translates the approved direction into a coherent token, primitive, component, motion, responsive, and state system; it does not choose a new direction.
3. If `frontend-design` cannot be loaded, stop. Do not draft, revise, or validate the pair through a fallback path.

For a Harness design-source mission, `required_skills` must contain `design-system-compiler` and `frontend-design`. This is distinct from Harness UI implementation conformance mode, which obeys frozen sources and does not revise them.

Do not reload `design-taste-frontend` or `impeccable` merely to compile the pair. Their approved consequences, when used, are already frozen in `PRD.md`'s UI Design Handoff. Reopen visual direction only when the human owner explicitly asks; follow the bounded expansion in Reference Routing, return the selected result to `product-definition-builder` for approval and recording, and restart compilation from that updated source.

## Inputs And Ownership

Read the current sources in full before drafting:

- `PRD.md`, including Product Definition Approval, its UI surface contract, Builder UX Direction Decision, Motion Need Gate, approved `### UI Design Handoff`, and `Design System Need Gate: required` decision;
- approved `wireframes.html`, including its matching `UI-*` page, complete viewport or size-class set, state, region, per-target layout, and passing browser overlap/overflow review, plus `PRD.md`'s `### Wireframe Approval` record;
- `architecture.md` and `stack-decisions.md`, including the approved Stack Decision Checkpoint and its platform, rendering, component-foundation, styling, accessibility, and performance constraints;
- existing `design-system.md` and `design-system.json` for an enhancement or delta; and
- the immutable approved UI target and any confirmed `REF-*` / `RP-*` evidence named by the handoff.

Read `market-research.md` only when the handoff cites its `MR-*` evidence. Repository-discovered images remain non-canonical design inspiration unless the PRD handoff explicitly promotes one to a scoped page-faithful target with its hash, route, state, responsive scope, and tolerance.

If a required source is named but missing or unreadable, stop and request its path or contents. A statement that an approved source exists is not a substitute for reading it.

If an existing pair or staged revision describes the same product, enhance it. Preserve unaffected content and stable `UI-*`, `UX-*`, `DS-*`, and `DS-COMP-*` IDs. Never regenerate the pair from a blank slate.

Product scope, route, structure, content, action, flow, state, wireframe, or approved-target gaps return to `product-definition-builder` or the named product owner. A treatment that needs one of those changes is a finding, not permission to edit the source.

## Workflow

1. Run the sibling `product-definition-builder/scripts/check_product_package.py --require-filled --require-approved` over PRD, architecture, and stack decisions. Stop on a missing or stale Product Definition/Stack approval.
2. Confirm that `PRD.md` says `Design System Need Gate: required`; otherwise stop.
3. Pass the Compilation Skills Gate.
4. Verify the PRD UI surface contract, approved wireframe, handoff, target, component foundation, and styling approach are complete and consistent. A visual direction that needs another stack returns upstream.
5. Read `references/design-system-guide.md` and compile only approved visual consequences with `frontend-design`. Register motion variants only for `required` or approved `recommended` rows; a `not_required` row gets no decorative variant, and a `blocked` row returns upstream. Every variant records reduced-motion behavior.
6. Build and validate the pair against the PRD, wireframes, and approved technology constraints.
7. Run the validation commands and final checklist, then stage and publish both files together through the existing artifact lifecycle.

## Validation

Run these from the repository root:

```text
python skills/design-system-compiler/scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --write
python skills/design-system-compiler/scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --require-filled
python skills/design-system-compiler/scripts/check_color_contrast.py <the arguments required by the staged design system>
python skills/design-system-compiler/scripts/check_type_scale.py <the arguments required by the staged design system>
python skills/product-definition-builder/scripts/check_product_package.py --prd <PRD.md> --architecture <architecture.md> --stack-decisions <stack-decisions.md> --require-filled --require-approved
```

Also confirm:

- the Design System Need Gate is `required` and names its owner and reason;
- Product Definition Approval and the Stack Decision Checkpoint are approved, with no `Recommended` or `Provisional` executable layer;
- every PRD UI surface has an addressable route or an explicit `n/a` reason;
- every UI surface maps to an approved `wireframes.html` page with matching regions, states, responsive set, and per-target order, visibility, spans, reflow, and interaction rules;
- the approved UI target, Taste applicability record, visual approval, scope, hash, exact responsive coverage, passing browser-matrix evidence, and tolerance are present in the UI Design Handoff;
- every surface covers the final state matrix or records `<state>: n/a - <reason>` in `PRD.md`;
- every required UI element maps to a registered primitive or product component;
- every Motion Need Gate row is resolved; `required` and approved `recommended` motion maps to a registered variant plus reduced-motion behavior, while `not_required` introduces no decorative variant;
- exactly one responsive set exists — web `viewports` with at least three ascending targets, or native or desktop `sizeClasses` with at least two — and it matches the PRD and approved wireframe set;
- no unresolved placeholder, page-local value, or one-off control remains; and
- `design-system.md` and `design-system.json` publish together and agree through the pair checker.

## Reference Routing

- Read `references/design-system-guide.md` for normal contract compilation.
- Read `references/output-contract.md` for artifact boundaries and quality checks.
- Read `references/artifact-lifecycle.md` before creating staging files or publishing.
- Use `assets/templates/DESIGN_SYSTEM.template.md` and `assets/templates/DESIGN_SYSTEM.template.json` for the pair.
- Use the three scripts under `scripts/` for deterministic pair, contrast, and type-scale validation.
- Only when the owner explicitly asks to reopen direction, read `references/visual-direction-guide.md`, `references/design-reference-guide.md`, and `references/impeccable-concept-generation.md`; load `impeccable`, `frontend-design`, and the design method selected by the PRD UI Design Handoff. Use `../product-definition-builder/references/ui-design-pass.md` for Taste applicability, the connected interactive HTML, and deferred media or motion handoffs. Return the result upstream for human approval instead of writing the pair against an unrecorded direction.

## Output Rules

- Default artifacts to English unless the user requests another language.
- Keep the design system implementation-facing.
- Keep candidate directions, reference analysis, and preview artifacts outside the published pair.
- Keep stable trace IDs across revisions; do not reuse retired IDs for different meanings.
- Builder approval proves direction conformance, not usability. Record unresolved validation needs.
- Report exact staged and published paths, validation results, assumptions, and every intentionally unresolved gap.

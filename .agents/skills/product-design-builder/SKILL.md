---
name: product-design-builder
description: Create or refine an implementation-ready frozen design-system contract (`design-system.md` and `design-system.json`) from an existing PRD, product brief, or approved requirements. Use for visual directions, current public design-reference discovery, image/screenshot/URL/Figma/named-product design extraction, design systems, design tokens, UI primitives, product-component contracts, responsive/state matrices, or design-input deltas. This skill requires the separate `frontend-design` and `impeccable` skills for every design-system creation or revision; it must not fall back to an unaided design path.
---

# Product Design Builder

## Purpose

Turn approved product intent into two binding UI sources:

- `design-system.md` for the selected visual direction and short human-facing rules; and
- `design-system.json` for machine-readable tokens, primitives, closed variants, product components, motion, responsive rules, source paths, and the state matrix.

`PRD.md` owns product scope plus routes, screen structure, flows, visible-region responsibilities, actions, states, responsive behavior, and `UI-*` / `UX-*` traces. Do not duplicate those contracts here. Do not implement production UI code or create Harness PLAN/RUN state.

## Mandatory Design Skills Gate

Before creating or revising any visual direction, token, primitive, component, motion rule, or responsive rule:

1. Confirm that the installed skills with exact frontmatter names `frontend-design` and `impeccable` are available in the current session.
2. Load both skills with this skill. Use `impeccable` through `references/impeccable-concept-generation.md` for surface-mode and concept-world generation, and use `frontend-design` for hierarchy, differentiation, typography, color, composition, motion, and anti-generic-UI craft.
3. State that all three skills are active before producing design output.
4. If `frontend-design` or `impeccable` is unavailable or cannot be loaded, stop and report the missing dependency. Do not draft, revise, or validate the design artifacts through a fallback path.

For a Harness mission, `required_skills` must contain `product-design-builder`, `frontend-design`, and `impeccable`. A worker loads exactly that trio before the launch checklist. This is distinct from Harness UI implementation conformance mode, where `frontend-design` obeys an already frozen package and `impeccable` is not loaded.

Create HTML, Figma, image, or code previews only when the user explicitly asks for that extra artifact. Keep previews non-canonical and outside the staged or published package.

## Inputs And Ownership

Read the current sources in full before asking questions or drafting:

- `PRD.md` or the approved product brief, including its UI surface contract and Builder UX Direction Decision;
- `market-research.md` and the `MR-*` citations in `PRD.md` when research exists, or the recorded skipped or blocked status;
- `architecture.md` and `stack-decisions.md` when they constrain platform, rendering, accessibility, performance, or component sources;
- existing `design-system.md` and `design-system.json` for an enhancement or delta;
- approved reference images, screenshots, brand rules, or page-specific design inputs; and
- repository-discovered design-image candidates, especially readable files under `docs/design/`, passed by the Harness as non-canonical design inspiration with their repository-relative paths and SHA-256 content hashes. Inspect and confirm them through the normal reference flow; never treat repository presence as a page-faithful request.

If a required source is named but missing or unreadable, stop and request its path or contents. A statement that an approved source exists is not a substitute for reading it.

If an existing package or staged revision describes the same product, enhance it. Preserve unaffected content and stable `UI-*`, `UX-*`, `DS-*`, and `DS-COMP-*` IDs. Never regenerate the package from a blank slate.

Product scope, route, structure, content, action, flow, or state gaps return to `prd-builder` or the named product owner. A visual treatment that needs one of those changes is a finding, not permission to change the PRD.

## Workflow

1. Pass the Mandatory Design Skills Gate.
2. Read `references/visual-direction-guide.md`, then verify its Builder UX Direction Gate with the human product/design decision owner. Every `assumed` answer requires that owner's explicit authorization. If the recorded decision or UI surface contract is missing or incomplete, return a bounded update to `prd-builder` or the named product owner and wait; do not edit `PRD.md` here.
3. Read `references/design-reference-guide.md` and `references/impeccable-concept-generation.md`, build the bounded Market Design Evidence Brief, then run `references/visual-direction-guide.md`'s combined Style And Reference Intake. Ask the human owner for the desired character, disliked patterns, and any visual references in one turn. End the turn and wait.
4. Inspect every supplied or repository-discovered reference using `references/design-reference-guide.md`. Return `Adopt / Adapt / Avoid` principles and wait for confirmation before using their signals.
5. Use `impeccable` and `frontend-design` to form exactly three materially different product-specific directions, or one per set only for an owner-requested lightweight direction pass. Find and inspect one current public visual reference for every direction and a second only when it adds a distinct useful mechanic. Preserve the same representative PRD surfaces, structure, content responsibilities, states, and trace IDs.
6. Let the human owner select, reject, mix, or inspect another reference. Do not fix tokens or components until one direction and its contributing `RP-*` principles are explicitly confirmed, or the user explicitly authorizes a provisional assumption.
7. Read `references/design-system-guide.md`. Use `frontend-design` to translate the selected direction and real PRD UI surface contract into the smallest complete implementation contract.
8. Build `design-system.json`, write the short rationale in `design-system.md`, and reconcile names, required content order, responsive rules, and states against the PRD UI surface contract.
9. Run the validation commands and the final checklist in `references/output-contract.md`.
10. Stage and publish both files together using `references/artifact-lifecycle.md`. When called from `prd-builder`, return the validated pair to that parent workflow.

## Validation

Run these from the repository root:

```text
python .agents/skills/product-design-builder/scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --write
python .agents/skills/product-design-builder/scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --require-filled
python .agents/skills/product-design-builder/scripts/check_color_contrast.py <the arguments required by the staged design system>
python .agents/skills/product-design-builder/scripts/check_type_scale.py <the arguments required by the staged design system>
```

Also confirm:

- every PRD UI surface has an addressable route or an explicit `n/a` reason;
- every surface covers the final state matrix or records `<state>: n/a — <reason>` in `PRD.md`;
- every required UI element maps to a registered primitive or product component;
- exactly one responsive set exists: web `viewports` or native or desktop `sizeClasses`;
- no unresolved placeholder, page-local value, or one-off control remains; and
- `design-system.md` and `design-system.json` publish together and agree through the pair checker.

## Reference Routing

- Read `references/visual-direction-guide.md` before visual-direction work.
- Read `references/design-reference-guide.md` for visual-reference discovery, inspection, evidence records, and revision behavior.
- Read `references/design-system-guide.md` after one direction is selected.
- Read `references/output-contract.md` for artifact boundaries and quality checks.
- Read `references/artifact-lifecycle.md` before creating staging files or publishing.
- Use `assets/templates/DESIGN_SYSTEM.template.md` and `assets/templates/DESIGN_SYSTEM.template.json` for the design-system pair.
- Use the three scripts under `scripts/` for deterministic pair, contrast, and type-scale validation.

## Output Rules

- Default artifacts to English unless the user requests another language.
- Keep the design system implementation-facing.
- Put candidate directions, reference analysis, and optional previews outside the published package.
- Keep stable trace IDs across revisions; do not reuse retired IDs for different meanings.
- Builder approval proves direction conformance, not usability. Record unresolved validation needs.
- Report exact staged and published paths, validation results, assumptions, and every intentionally unresolved gap.

---
name: product-design-builder
description: Create or refine implementation-ready product wireframes and a frozen design-system contract (`wireframes.md`, `design-system.md`, and `design-system.json`) from an existing PRD, product brief, or approved requirements. Use for UI wireframes, screen flows, visual directions, current public design-reference discovery, image/screenshot/URL/Figma/named-product design extraction, design systems, design tokens, UI primitives, product-component contracts, responsive/state matrices, or design-input deltas. This skill requires the separate `frontend-design` skill for every wireframe and design-system creation or revision; it must not fall back to an unaided design path.
---

# Product Design Builder

## Purpose

Turn approved product intent into three binding UI sources:

- `wireframes.md` for screen structure, flow, visible-region responsibilities, actions, states, and `UI-*` / `UX-*` traces;
- `design-system.md` for the selected visual direction and short human-facing rules; and
- `design-system.json` for the machine-readable tokens, primitives, closed variants, product components, motion, responsive set, source paths, and state matrix.

Keep product scope in `PRD.md`. Do not implement production UI code or create Harness PLAN/RUN state.

## Mandatory Frontend Design Gate

Before creating or revising any wireframe, visual direction, token, primitive, component, motion rule, or responsive rule:

1. Confirm that the installed skill with exact frontmatter name `frontend-design` is available in the current session.
2. Load `frontend-design` together with this skill and apply its design-thinking, differentiation, typography, color, composition, motion, and anti-generic-UI discipline throughout the work.
3. State that both skills are active before producing design output. Do not claim `frontend-design` participation from a prior session, a package name, or remembered guidance.
4. If `frontend-design` is unavailable or cannot be loaded, stop and report the missing dependency. Do not draft, revise, or validate the design artifacts through a fallback path.

For a Harness mission, `required_skills` must contain both `product-design-builder` and `frontend-design`. A worker loads exactly that pair before the launch checklist. In this creation mode, `frontend-design` may choose and develop the product-specific direction inside the approved product, platform, accessibility, and Builder UX constraints. This is distinct from Harness UI implementation conformance mode, where `frontend-design` must obey an already frozen package.

Using `frontend-design` does not require preview code. Apply the skill to the documents directly. Create HTML, Figma, image, or code previews only when the user explicitly asks for that extra artifact, and keep them non-canonical and outside the staged or published package.

## Inputs And Ownership

Read the current sources in full before asking questions or drafting:

- `PRD.md` or the approved product brief;
- the Builder UX Direction Decision, including decision status and owner;
- `market-research.md` and the `MR-*` citations in `PRD.md` when research exists, or the recorded skipped/blocked status when it does not;
- `architecture.md` and `stack-decisions.md` when they constrain platform, rendering, accessibility, performance, or component sources;
- existing `wireframes.md`, `design-system.md`, and `design-system.json` for an enhancement or delta; and
- any approved reference images, screenshots, brand rules, or page-specific design inputs.

If a required source is named but missing or unreadable, stop and request its path or contents. A statement that an approved source exists is not a substitute for reading it.

If an existing package or staged revision describes the same product, enhance it. Preserve unaffected content and stable `UI-*`, `UX-*`, `DS-*`, and `DS-COMP-*` IDs. Never regenerate the package from a blank slate.

Product scope or architecture gaps return to `prd-builder` or the named product owner. A visual treatment that needs a product or structural change is a finding, not permission to change scope.

## Workflow

1. Pass the Mandatory Frontend Design Gate.
2. Read `references/wireframe-guide.md`, then verify its Builder UX Direction Gate with the human product/design decision owner before drafting. Every `assumed` answer requires that owner's explicit authorization. If the recorded decision is missing or incomplete, return a bounded update to `prd-builder` or the named product owner and wait; do not edit `PRD.md` here. Freeze the accepted direction with the product scope, routes, platform, content responsibilities, actions, states, traces, accessibility constraints, and performance limits.
3. Use `frontend-design` to reason about purposeful hierarchy, task-fit layout, differentiation, responsive behavior, and interaction intent. Draft low-fidelity ASCII wireframes and Mermaid flows. Keep palette, typeface, token values, surface styling, and detailed motion unfixed at this stage.
4. Run the wireframe quality pass in `references/output-contract.md`. Resolve generic regions, missing routes, incomplete states, unexplained boxes, and unbounded content before visual exploration.
5. Read `references/design-reference-guide.md`, build the bounded Market Design Evidence Brief, then run `references/wireframe-guide.md`'s combined Style And Reference Intake. Ask the human owner for the desired character, disliked patterns, and any images, URLs, Figma views, named products, or brand references in one turn. End the turn and wait; do not recommend a direction in the same turn.
6. After the owner replies, inspect every supplied reference using `references/design-reference-guide.md`. Return `Adopt / Adapt / Avoid` principles and wait for confirmation before using owner-supplied signals. Never infer details from an unreadable or inaccessible source.
7. Use `frontend-design` to form exactly three materially different product-specific directions. Find and inspect one current public visual reference for every direction and a second only when it adds a distinct useful mechanic. Include one contemporary/modern direction by default and a second only when preference, product constraints, and valid evidence support a materially different option. Preserve the same representative screens, structure, content responsibilities, states, and trace IDs. Keep `MR-*`/`S-*` market evidence separate from `REF-*` visual evidence, label inferences, and never describe a direction as market-supported without valid market evidence.
8. Let the human owner select, reject, mix, or inspect another reference. `Reject`-all and `Check This` produce a versioned revised set of exactly three directions after the required feedback or principle-confirmation pause. Do not fix tokens or components until one direction and its contributing `RP-*` principles are explicitly confirmed, or the user explicitly authorizes a provisional assumption.
9. Read `references/design-system-guide.md`. Use `frontend-design` to translate the selected direction into the smallest complete implementation contract required by the real wireframes.
10. Build `design-system.json`, write the short rationale in `design-system.md`, and reconcile final token, primitive, and product-component names back into every wireframe inventory and spacing declaration.
11. Run the validation commands below and the final checklist in `references/output-contract.md`.
12. Stage and publish all three files together using `references/artifact-lifecycle.md`. When this skill is called from `prd-builder`, return the validated artifacts to that parent workflow; `prd-builder` owns whole-package publication.

## Validation

Run these from the skill directory or use absolute script paths:

```text
python scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --write
python scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --require-filled
python scripts/check_color_contrast.py <the arguments required by the staged design system>
python scripts/check_type_scale.py <the arguments required by the staged design system>
```

Also confirm:

- each addressable route maps to exactly one wireframe screen;
- every screen covers the final state matrix or records `<state>: n/a — <reason>`;
- every wireframe element maps to a registered primitive or product component;
- exactly one responsive set exists: web `viewports` or native/desktop `sizeClasses`;
- no unresolved `custom — reason`, placeholder, page-local value, or one-off control remains; and
- `design-system.md` and `design-system.json` publish together and agree byte-for-structure through the pair checker.

## Reference Routing

- Read `references/wireframe-guide.md` before any structural or visual-direction work.
- Read `references/design-reference-guide.md` for visual-reference discovery, inspection, evidence records, source-specific fallback, and selection/revision behavior.
- Read `references/design-system-guide.md` only after structural wireframes pass and before fixing the selected direction into tokens and components.
- Read `references/output-contract.md` for exact artifact boundaries and quality checks.
- Read `references/artifact-lifecycle.md` before creating staging files or publishing.
- Use `assets/templates/DESIGN_SYSTEM.template.md` and `assets/templates/DESIGN_SYSTEM.template.json` for the design-system pair.
- Use the three scripts under `scripts/` for deterministic pair, contrast, and type-scale validation.

## Output Rules

- Default artifacts to English unless the user requests another language.
- Keep wireframes low fidelity and design systems implementation-facing.
- Put candidate directions, reference analysis, and optional previews outside the published package.
- Keep stable trace IDs across revisions; do not reuse retired IDs for different meanings.
- Builder approval proves direction conformance, not usability. Record unresolved validation needs.
- Report exact staged and published paths, validation results, assumptions, and every intentionally unresolved gap.

# Product Design Output Contract

Publish these files for a UI-bearing product:

- `design-system.md`
- `design-system.json`

The pair forms one visual implementation handoff. `PRD.md` owns routes, screen structure, flows, visible-region responsibilities, content, actions, states, responsive behavior, and trace IDs. The design-system pair owns visual implementation. Publish or revise both design-system files together.

## `design-system.md`

Include only:

- selected-direction status, owner, representative surface mode, concept thesis, named visual world, summary, and implementation consequences;
- selected `VD-*` direction provenance with applicable `MR-*`, inspected `REF-*`, confirmed `RP-*`, retrieval dates, and owner confirmation;
- short rationale for non-obvious token and component choices;
- computed contrast and type-scale evidence;
- concise responsive, interaction, accessibility, and reduced-motion rules; and
- product-specific do and don't guardrails plus the generated machine-contract block.

## `design-system.json`

Keep it the sole structured authority for:

- platform, styling mechanism, enforcement mode, token sources, and primitive sources;
- exactly one responsive verification set: `viewports` or `sizeClasses`;
- only the tokens the product uses;
- four primitive layers with closed variant sets;
- signature visual rules with stable `DS-*` IDs;
- recurring product components with `DS-COMP-*`, required content order, composition, and states;
- registered motion variants; and
- the UI state matrix.

## PRD Input Quality Check

- Each UI surface has one main purpose, one task-fit layout pattern, a real route or explicit `n/a`, and a density reason.
- Every visible region has exact copy or a bounded display contract, content priority, ordered responsibilities, actions, states, responsive behavior, and trace IDs.
- Public surfaces have bounded SEO fields, correct heading order, and image alt-text contracts.
- Ready, loading, empty, error, disabled, permission-denied, stale, expired, long-content, reduced-motion, and mobile-reflow states are covered or explicitly `n/a`.
- Scope, routes, actions, content responsibilities, and trace IDs stay fixed across visual directions.

If any item is missing, return a bounded PRD update. Do not invent it in the design system.

## Final Quality Check

- `impeccable` and `frontend-design` were loaded with `product-design-builder` for every creation or revision step.
- Every direction set records a surface mode and concept-generation route from `impeccable-concept-generation.md`.
- The human owner selected one consolidated direction, or explicitly authorized a provisional assumption.
- Every presented direction used one inspected current public `REF-*` source and at most one additional source that contributed a distinct useful mechanic.
- The selected direction records applicable `MR-*`, inspected `REF-*`, confirmed `RP-*`, retrieval dates, and owner confirmation; full extraction history remains outside the package.
- Visual references influenced only confirmed `Adopt / Adapt / Avoid` principles; protected artwork, branding, exact copy, HTML or CSS, source assets, and distinctive composition were not copied.
- Every token, primitive, component, motion variant, state, and responsive entry is required by a real PRD surface.
- Every required PRD element maps to the final registry, and no unresolved page-local exception remains.
- Pair generation, filled-pair validation, contrast checks, and type-scale checks pass.
- Candidate directions, full reference analysis, and optional preview artifacts remain outside the package.
- The final report names exact paths, decision status, validation results, assumptions, and open gaps.

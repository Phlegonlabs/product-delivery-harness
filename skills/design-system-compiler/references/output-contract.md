# Product Design Output Contract

Publish these files only when `PRD.md` records `Design System Need Gate: required`:

- `design-system.md`
- `design-system.json`

The pair forms one reusable visual implementation handoff. `PRD.md` owns product structure, behavior, and the approved UI Design Handoff; approved `wireframes.html` provides its structural interactive review view. The design-system pair owns tokens, closed variants, reusable components, motion, and the state matrix. Publish or revise both files together. The approved preview remains a scoped page-faithful target outside this pair.

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
- exactly one responsive verification set, copied exactly from the approved PRD and wireframe: at least three ascending web `viewports` or at least two native/desktop `sizeClasses`;
- only the tokens the product uses;
- four primitive layers with closed variant sets;
- optional primitive `dsId` values matching `DS-[A-Z]+-<number>` when a primitive needs a trace identity;
- signature visual rules with stable `DS-*` IDs, registered in `signatureRules` — every complete `DS-*` token the Markdown names (rule, primitive `dsId`, or `DS-COMP-*`) must resolve to this file, malformed lookalikes fail, and IDs are globally unique across all three registries;
- recurring product components with `DS-COMP-*`, required content order, composition, and states;
- registered motion variants; and
- the UI state matrix.

## PRD Input Quality Check

- The Design System Need Gate is `required` and records its human owner and reason.
- `### UI Design Handoff` records an approved immutable target, source hash, routes and states, the exact PRD/wireframe responsive set, passing browser-matrix evidence with no unintended overlap, clipping, occlusion, or horizontal overflow, tolerance, and allowed deviations.
- `wireframes.html` has human approval recorded in `PRD.md`, and each `UI-*` page matches the PRD.
- Each UI surface has one main purpose, one task-fit layout pattern, a real route or explicit `n/a`, and a density reason.
- Every visible region has exact copy or a bounded display contract, content priority, ordered responsibilities, actions, states, responsive behavior, and trace IDs.
- Public surfaces have bounded SEO fields, correct heading order, and image alt-text contracts.
- Ready, loading, empty, error, disabled, permission-denied, stale, expired, long-content, reduced-motion, and mobile-reflow states are covered or explicitly `n/a` at every responsive target.
- Scope, routes, actions, content responsibilities, wireframe structure, responsive rearrangement, and trace IDs stay fixed across visual directions.

If any item is missing, return a bounded PRD update. Do not invent it in the design system.

## Final Quality Check

- `frontend-design` was loaded with `design-system-compiler` in contract-compilation mode.
- `impeccable` and `design-taste-frontend` were not rerun during normal compilation; their approved consequences are read from the PRD UI Design Handoff.
- The Taste applicability record contains a Design Read and dial settings when applicable, or a specific `n/a` reason.
- The human owner approved one immutable UI target, or explicitly authorized a provisional assumption.
- The selected direction records applicable `MR-*`, inspected `REF-*`, confirmed `RP-*`, retrieval dates, and owner confirmation; full extraction history remains outside the package.
- Visual references influenced only confirmed `Adopt / Adapt / Avoid` principles; protected artwork, branding, exact copy, HTML or CSS, source assets, and distinctive composition were not copied.
- Every token, primitive, component, motion variant, state, and responsive entry is required by a real PRD surface; the responsive set contains at least three ascending web viewports or at least two native/desktop size classes and matches the approved PRD and wireframe exactly.
- Every required PRD element maps to the final registry, and no unresolved page-local exception remains.
- Pair generation, filled-pair validation, contrast checks, and type-scale checks pass.
- Candidate directions, full reference analysis, and UI preview artifacts remain outside the pair.
- The final report names exact paths, decision status, validation results, assumptions, and open gaps.

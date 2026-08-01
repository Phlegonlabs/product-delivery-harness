# Product Design Output Contract

Publish these files for a UI-bearing product:

- `wireframes.md`
- `design-system.md`
- `design-system.json`

The three files form one design handoff. `wireframes.md` owns structure and content responsibility. The design-system pair owns the visual implementation layer. Publish or revise them together when a visual change affects wireframe inventories, spacing tokens, components, states, or responsive behavior.

## `wireframes.md`

Include:

1. product and Builder UX Direction summary;
2. route-to-screen and public-route keyword map;
3. one focused Mermaid flow per primary journey, including failure paths;
4. one screen entry per shipped UI surface using `wireframe-guide.md`'s template;
5. exact copy or bounded display contracts for every visible region;
6. element inventories, structural spacing roles, media/motion purpose, states, and trace IDs; and
7. final reconciliation to the selected token, primitive, and product-component names.

Do not include high-fidelity styling, raw token values, candidate-direction history, or implementation code.

## `design-system.md`

Include only:

- selected-direction status, owner, summary, and implementation consequences;
- selected `VD-*` direction provenance with applicable `MR-*`, inspected `REF-*`, confirmed `RP-*`, retrieval dates, and owner confirmation;
- short rationale for non-obvious token and component choices;
- computed contrast and type-scale evidence;
- concise responsive, interaction, accessibility, and reduced-motion rules; and
- product-specific do/don't guardrails plus the generated machine-contract block.

## `design-system.json`

Keep it the sole structured authority for:

- platform, styling mechanism, enforcement mode, token sources, and primitive sources;
- exactly one responsive verification set: `viewports` or `sizeClasses`;
- only the tokens the product uses;
- four primitive layers with closed variant sets;
- signature visual rules with stable `DS-*` IDs;
- recurring product components with `DS-COMP-*`, required content order, composition, and states;
- registered motion variants; and
- the screen state matrix.

## Wireframe Quality Check

- Each screen has one main purpose, one task-fit layout pattern, a real route or an explicit `n/a`, and a density reason.
- Every visible region has exact copy or a bounded display contract, content priority, style job, element inventory, spacing, media, motion, and traces.
- Boxes represent real grouping, interaction, state, or hierarchy.
- Public screens have bounded SEO fields, correct heading order, and image alt-text contracts.
- Ready, loading, empty, error, disabled, permission-denied, stale, expired, long-content, reduced-motion, and mobile-reflow states are covered or explicitly `n/a`.
- Scope, routes, actions, content responsibilities, and trace IDs stay fixed across visual directions.

## Final Quality Check

- `frontend-design` was loaded with `product-design-builder` for every creation or revision step.
- The human owner selected one consolidated direction, or explicitly authorized a provisional assumption.
- Every presented direction used one inspected current public `REF-*` source and at most one additional source that contributed a distinct useful mechanic.
- The selected direction records applicable `MR-*`, inspected `REF-*`, confirmed `RP-*`, retrieval dates, and owner confirmation; full extraction history remains outside the package.
- Visual references influenced only confirmed `Adopt / Adapt / Avoid` principles; protected artwork, branding, exact copy, HTML/CSS, source assets, and distinctive composition were not copied.
- Every token, primitive, component, motion variant, state, and responsive entry is required by a real screen.
- Every wireframe element maps to the final registry, and no unresolved `custom — reason` remains.
- Pair generation, filled-pair validation, contrast checks, and type-scale checks pass.
- Candidate directions, full reference analysis, and optional preview artifacts remain outside the package.
- The final report names exact paths, decision status, validation results, assumptions, and open gaps.

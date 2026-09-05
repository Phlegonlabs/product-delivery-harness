# Design System Guide

Use this guide to publish the small frontend implementation contract in `docs/product/design-system.md` and `docs/product/design-system.json`.

The design system exists so frontend implementation can follow one set of tokens, primitives, component variants, states, responsive rules, and accessibility rules. It is not a design-research archive, component showcase, page recipe, or governance manual.

## Drafting Order

1. Confirm that `PRD.md` records `Design System Need Gate: required`, then load `product-design-builder` and `frontend-design` together. If `frontend-design` is unavailable, stop instead of creating or revising the pair through a fallback path.
2. Confirm that the PRD UI surface contract is complete and frozen, `wireframes.html` has explicit human-owner approval recorded in `### Wireframe Approval`, and `### UI Design Handoff` records an approved immutable target with scope, hash, responsive coverage, and tolerance.
3. Consume the selected direction, Taste applicability result, Design Read and dials when applicable, visual evidence, and human approval from the UI Design Handoff. Do not rerun visual-direction generation, `impeccable`, `design-taste-frontend`, or the UI Preview Gate during normal compilation.
4. Use `frontend-design` in contract-compilation mode to translate the approved direction, real controls, repeated compositions, states, and responsive needs into `design-system.json` without changing the target.
5. Write the short human rationale in `design-system.md`, then generate its machine-contract block from the JSON.
6. Reconcile the final token, primitive, and product-component names against every required PRD UI element and state. An unresolved page-local exception blocks publication.

Publish the Markdown and JSON together.

## Contract Boundary

`design-system.json` is the sole structured authority. It contains only what implementation and validation need:

- token and primitive source paths;
- the responsive verification set;
- tokens the product actually uses;
- primitives with closed variant sets;
- recurring product components and their required content;
- registered motion variants when motion is used; and
- the state matrix.

`design-system.md` adds only:

- a short selected-direction summary;
- compact selected-direction provenance: applicable `MR-*`, inspected `REF-*`, confirmed `RP-*`, retrieval dates, and owner confirmation;
- the reason behind token and component choices that are not self-evident;
- computed color-contrast and type-scale evidence;
- concise responsive, interaction, and accessibility rules; and
- product-specific do/don't guardrails.

Do not preserve reference-image files, the full image extraction or `Check This` analysis, rejected direction history, UI previews, per-route recipes, implementation examples, or general design theory in either file.

## Selected Visual Direction

Record:

- decision status: `selected`, `provisional`, or `assumed`;
- the human decision owner;
- the selected or consolidated `VD-*` direction ID;
- the Taste applicability decision and confirmed Design Read or dial settings when applicable;
- the representative surface mode, concept thesis, and named visual world when the approved handoff includes them;
- applicable `MR-*` market evidence, or an explicit statement that no valid market evidence supports the visual decision;
- inspected `REF-*` sources with direct URL or attachment label and retrieval date;
- confirmed `RP-*` `Adopt / Adapt / Avoid` principles and the owner's confirmation record;
- one paragraph describing the visual character; and
- three to five implementation consequences across hierarchy, density, typography, color, surfaces, icons or media, and motion.

Keep only the selected result. Candidate directions and reference-analysis notes remain non-canonical design-stage evidence outside the package.

Visual references influence the design system only through confirmed `RP-*` `Adopt / Adapt / Avoid` principles in the selected direction. Sampled colors, measured spacing, inferred type sizes, and other screenshot pixels do not become final token values. Synthesize accessible, platform-fit tokens from the confirmed principles and validate them with the normal contrast, type-scale, responsive, and state checks.

Builder approval proves direction conformance, not usability. Product requirements, representative-user evidence, platform convention, and accessibility outrank preference.

## Tokens

Define a token only when a PRD UI surface or declared component uses it. Raw colors, dimensions, and motion values may appear only in the JSON's declared `tokenSources`.

Keep the normal implementation groups:

- `color`
- `space`
- `radius`
- `fontSize`
- `lineHeight`
- `shadow`
- `duration`
- `easing`

Do not add speculative scales or unused theme layers.

For colors, state the palette basis and compute every text, UI-boundary, and semantic-color pairing with `scripts/check_color_contrast.py`. Record the actual ratio and keep meaning independent of color alone.

For typography, state the family or platform-font reason and the type-scale logic. Compute each role's line-height ratio with `scripts/check_type_scale.py`.

Dark mode, high contrast, chart colors, or platform-specific token overrides are added only when the product actually requires them.

## Primitives And Product Components

Primitives use four layers:

1. `layout` — spacing and flow;
2. `surface` — framing and elevation;
3. `typography` — text roles and truncation;
4. `control` — interactive controls and their states.

A primitive uses only lower layers. Every variant axis is a closed set. A page selects a registered value and may not invent another one.

Add a product component only when the same domain composition recurs across screens. Each product component has:

- `dsId`;
- `requiredContentOrder`;
- `composes`; and
- `states`.

Every `requiredContentOrder` entry is a never-drop field. It renders in that order wherever the component appears. The downstream Content contract conformance gate checks it.

Do not repeat the full primitive or component inventory manually in Markdown; the generated machine-contract block owns that view.

## Responsive, State, And Accessibility Rules

Ship exactly one responsive set:

- `viewports` for web; or
- `sizeClasses` for native or desktop.

Choose the smallest set that covers the real layouts. Native and desktop products use their platform's own size or window classes, not web pixel breakpoints.

`stateMatrix` is the checklist for every screen. Each screen implements every listed state or records `<state>: n/a — <reason>` in `PRD.md`. The PRD and JSON must agree.

Keep accessibility rules implementation-facing:

- visible focus;
- keyboard path where a keyboard exists;
- accessible names and labels;
- minimum target size;
- error association and status announcement;
- contrast; and
- reduced-motion behavior.

## Source And Enforcement Rules

- `tokenSources` are the only paths allowed to declare raw color, dimension, or motion values.
- `primitiveSources` are the paths allowed to define reusable control and surface selectors.
- Product pages compose registered tokens and controls. They do not define page-local values or one-off controls.
- When the existing contract cannot express a required UI, update the design system first, then use the new contract from the page.

## Conflict Rules

Resolve conflicts in this order:

1. product requirement or explicit user constraint;
2. representative-user evidence;
3. accessibility requirement;
4. target-platform convention;
5. selected Visual Direction;
6. provisional or assumed preference.

`PRD.md` owns product structure and behavior, and approved `wireframes.html` is its low-fidelity interactive review projection. The design system owns visual implementation. A visual treatment that needs a structural change returns to `prd-builder` instead of silently changing the screen.

## Publish Check

Before publication:

1. Confirm one selected or explicitly provisional Visual Direction plus UI preview evidence or an explicit owner waiver.
2. Confirm every token, primitive, component, state, and responsive entry is used or required.
3. Confirm every required PRD UI element maps to a registered primitive or product component.
4. Confirm no page-local value or control is required.
5. Generate the Markdown contract block with `scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --write`.
6. Validate it with `scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --require-filled`. The check also resolves every `DS-*` ID named anywhere in the Markdown — signature rules, primitive `dsId`, or `DS-COMP-*` — against the JSON's registered IDs, so an ID minted only in prose fails.
7. Run the contrast and type-scale checks.

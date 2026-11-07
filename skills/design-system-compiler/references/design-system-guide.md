# Design System Guide

Use this guide to publish the small frontend implementation contract in `docs/design/design-system.md` and `docs/design/design-system.json`.

The design system exists so frontend implementation can follow one set of tokens, primitives, component variants, states, responsive rules, and accessibility rules. It is not a design-research archive, component showcase, page recipe, or governance manual.

The stage [Workflow](stages/design-compilation.md#workflow) owns the drafting order and its [Validation](stages/design-compilation.md#validation) owns the publish check.

## Contract Boundary

`design-system.json` is the sole structured authority. Its `sourceBindings` resolve the current PRD, architecture, stack, `ui-design.md`, and approved HiFi target under `--repo-root` and match their current SHA-256 values. It contains only what implementation and validation need:

Use the closed enums `platform: web | ios | android | flutter | react-native | macos | windows | linux | desktop`, `stylingMechanism: utility CSS | Tailwind CSS | CSS-in-JS | CSS modules | plain CSS | platform theme`, and `enforcement: blocking | advisory`. `stackSemantics` binds the exact approved rendering model (or client strategy), component foundation (or framework), styling approach, and platform. `stackSemantics.stylingMechanism` stays the verbatim Stack styling approach; the global `stylingMechanism` is the closed value that names it, such as `plain CSS` for `modern vanilla CSS`, `Tailwind CSS` for `Tailwind CSS v4`, or `platform theme` for native or component-library-managed styles. A hybrid pair uses `surfaceContracts` instead of global `platform`, `stylingMechanism`, `viewports`, and `sizeClasses`, plus a `stackSemantics` map keyed by every UI-* surface. Platform and styling choices remain grounded in the approved `stack-decisions.md` source binding rather than being invented by the compiler. Shared tokens, primitives, product components, motion variants, and state matrix remain global.

Browser-extension UI uses `platform: web` with the UI approval `captureMode: browser-extension`; it is not silently treated as hosted web.

- current source bindings plus token and primitive source paths;
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
- the generated contrast and type-scale evidence;
- concise responsive, interaction, and accessibility rules; and
- product-specific do/don't guardrails.

Do not preserve reference-image files, the full image extraction or `Check This` analysis, rejected direction history, UI previews, per-route recipes, implementation examples, or general design theory in either file.

## Selected Visual Direction

Record:

- decision status: `selected` only;
- the human decision owner;
- the selected or consolidated `VD-*` direction ID;
- the approved Style Integration direction and candidate theme rules;
- the approved Platform rules, preserving shared brand roles and platform-specific typography, controls, density, and feedback;
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
- `fontFamily`
- `fontWeight`
- `shadow`
- `duration`
- `easing`

Do not add speculative scales or unused theme layers.

State the palette basis, the family or platform-font reason and the type-scale logic. Name every text, UI-boundary and semantic-color pairing in `contrastPairs` and every type role in `typeSteps`; `--write` renders their ratios into the generated evidence block. Keep meaning independent of color alone.

Dark mode, high contrast, chart colors, or platform-specific token overrides are added only when the product actually requires them.

## Primitives And Product Components

Primitives use four layers:

1. `layout` — spacing and flow;
2. `surface` — framing and elevation;
3. `typography` — text roles and truncation;
4. `control` — interactive controls and their states.

A primitive uses only lower layers. Every variant axis is a closed set. A page selects a registered value and may not invent another one. A primitive may declare an optional `dsId` matching `DS-[A-Z]+-<number>` when prose or PLAN traces need to name it.

Add a product component only when the same domain composition recurs across screens. Each product component has:

- `dsId`;
- `requiredContentOrder`;
- `composes`; and
- `states`.

Every `requiredContentOrder` entry is a never-drop field. It renders in that order wherever the component appears. The downstream Content contract conformance gate checks it.

Do not repeat the full primitive or component inventory manually in Markdown; the generated machine-contract block owns that view.

## Responsive, State, And Accessibility Rules

Ship exactly one responsive set for a homogeneous product:

- at least three ascending `viewports` for web; or
- at least two `sizeClasses` for native or desktop.

Copy the exact approved PRD and HiFi set; do not add, remove, or rename targets during compilation. Choose that smallest sufficient set upstream during product definition. Native and desktop products use their platform's own size or window classes, not web pixel breakpoints. Each target has an implementation-facing reflow, visibility, interaction, long-content, and intended-overlay rule. Unintended overlap, clipping, occlusion, and horizontal overflow are blocking defects at every target and state.

For a hybrid product, each `surfaceContracts` entry carries its own exact responsive set and release/capture contract; do not collapse web viewports and native/desktop size classes into one global set. Platform and styling mechanism stay in the approved stack decision.

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
5. the explicitly approved selected Visual Direction.

`PRD.md` owns product behavior, approved HiFi is its visual and interactive projection, and `ui-design.md` owns the selected visual direction. The design system owns reusable visual implementation rules. A product change returns to `product-definition-builder`; a wireframe or visual change returns to `ui-design-builder`.

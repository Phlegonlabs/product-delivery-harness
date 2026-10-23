# Design System Compiler Output Contract

Publish these files only when `docs/design/ui-design.md` records `Design System Need Gate: required`:

- `docs/design/design-system.md`
- `docs/design/design-system.json`

The pair forms one reusable visual implementation handoff. `PRD.md` owns product behavior; `docs/design/ui-design.md` owns UI decisions and the approved complete `ui-hifi/2` package. The design-system pair owns tokens, closed variants, reusable components, motion, and the state matrix. Publish or revise both files together. A `design-system/4` pair also requires its derived HTML. Legacy `design-system/1` remains inspection-only; `design-system/2` retains its original publication checks for legacy UI packages.

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

- platform, stack-bound rendering model/component foundation/styling semantics, styling mechanism, enforcement mode, token sources, and primitive sources;
- `sourceBindings` for exactly current PRD, architecture, stack, the approved UI contract and approved complete HiFi entry bytes, with no wireframe binding;
- one global responsive verification set for homogeneous products, or one set per `surfaceContracts` entry for hybrids; copy the exact approved PRD/HiFi set, with at least three ascending web `viewports` or two native/desktop `sizeClasses`, plus each surface’s release/capture identity and approved stack semantics; hybrids omit global platform, styling mechanism, viewports, and size classes;
- only the tokens the product uses;
- four primitive layers with closed variant sets;
- optional primitive `dsId` values matching `DS-[A-Z]+-<number>` when a primitive needs a trace identity;
- signature visual rules with stable `DS-*` IDs, registered in `signatureRules` — every complete `DS-*` token the Markdown names (rule, primitive `dsId`, or `DS-COMP-*`) must resolve to this file, malformed lookalikes fail, and IDs are globally unique across all three registries;
- recurring product components with `DS-COMP-*`, required content order, composition, and states;
- registered motion variants;
- the UI state matrix; and
- for `design-system/4` only, the `showcase` source map below.

### `design-system/4` showcase

`design-system/4` keeps every `design-system/3` field and rule and adds one closed `showcase` object, mirrored in the generated Markdown block:

```json
"showcase": {
  "schema": "ds-showcase/1",
  "specimens": [{"id": "button-primary", "subject": {"kind": "primitive", "name": "Button"},
                 "axes": {"variants": "primary", "sizes": "md"},
                 "source": {"page": "index.html", "selector": ".btn", "variant": "primary md", "state": "default"}}],
  "states": [{"subject": {"kind": "primitive", "name": "Button"}, "state": "hover", "mode": "pseudo", "specimen": "button-primary"},
             {"subject": {"kind": "primitive", "name": "Button"}, "state": "loading", "mode": "not_applicable", "reason": "Saving is instant."}],
  "motion": [{"variant": "sheet-rise", "specimen": "arrival-sheet",
              "trigger": {"kind": "attribute", "name": "data-open", "from": "false", "to": "true"}}]
}
```

- A specimen resolves to the first product element on that manifest page matching the simple element, class or ID selector with exactly that `data-specimen-variant` and `data-specimen-state`. Each claimed axis value appears as a word of the source variant. The registry never stores styles.
- Coverage is complete: every list-valued primitive axis value, every primitive and product component, every product-component `states` entry and, for `control` primitives, `default`, `hover`, `focus-visible`, `active` and `disabled`. Every required state has its own `showcase.states` row, even when a matching source specimen already exists. A state is `rendered` (its own source element), `pseudo` (the approved page CSS has `<selector>…:<state>`) or `not_applicable` with a concrete reason.
- Every `motionVariants` entry has a motion row. Its trigger is `attribute` (source element carries `from`; CSS selects the attribute and transitions or animates), `class`, or `animation`. An animation needs resolved literal names on the bound specimen's winning CSS declaration plus those named source keyframes. The checker follows importance, specificity and source order for simple/compound selectors and inline styles, including shorthand/name resets. Custom properties use the computed ancestor values, local cascade and valid fallbacks; missing or cyclic values cannot supply evidence. Dependency analysis follows direct, transitive and fallback values in the winning declaration and its named keyframes. Conditional custom properties are ignored only when analysis proves they cannot reach that dependency set; a relevant conditional definition, `@property` declaration, conditional/layered animation rule, complex selector, quoted name, escaped sequence or unsupported value is a finding. Unrelated page animations and reduced-motion-only rules cannot supply provenance. The page needs an approved `prefers-reduced-motion: reduce` rule.
- `ds-showcase/2` keeps every `/1` rule and adds a closed `source-runtime` trigger for approved script- or state-driven motion: `{"kind": "source-runtime", "mechanism": "waapi" | "css-animation", "intent": "MM-*", "surface": "UI-*", "state", "target", "scriptSha256", "activation": {"kind": "viewport" | "state-entry"}}`. The intent must be an approved motion row in the current `ui-design.md` with current normal and reduced-motion PASS evidence files. One intent binds one row. `scriptSha256` is the raw UTF-8 body hash of exactly one executable inline product script outside reviewer segments. The specimen must resolve to exactly one copy inside that manifest surface, state view and target. A missing or ambiguous copy, reviewer script, unknown key or non-literal value fails. These checks prove association, not playback.
- In `/2` only, a pseudo state may also use one unconditional rule `<simple ancestor selector> :<state>` whose ancestor is on the specimen's source path, such as `[data-ui-surface] :focus-visible`. Other selector forms stay unresolved. A `rendered` `open` state cannot come from a closed native `<details>`.
- The checker reads the HiFi entry from `sourceBindings.hifi` and each sibling by its manifest hash through safe non-link paths. A stale, missing or unresolved source fails the pair before any HTML is emitted.

## Approved Input Quality Check

The stage Validation list owns the checklist. Two input rules also apply:

- The UI contract records an approved immutable target, source hash, routes and states, the exact PRD/HiFi responsive set, passing browser-matrix evidence with no unintended overlap, clipping, occlusion, or horizontal overflow, tolerance, and allowed deviations.
- Copy stays fixed across visual directions. A proposed wording change returns to `product-definition-builder` as a PRD and HiFi copy delta and requires the full HiFi copy review.

## Final Quality Check

### Derived HTML View

For `design-system/4`, the same renderer emits a specimen book at the same `docs/design/design-system-preview.html` path:

- Foundations: every token with its value applied, scale ranges, the approved responsive set and the `@container` rules found in source CSS.
- Components: one sandboxed plate per specimen. A plate copies the approved element, its ancestor chain and the page's product CSS. Reviewer shell CSS and scripts are excluded. State tables show rendered, live pseudo-class and not-applicable treatments. In `ds-showcase/2`, a specimen inside a native `<details>` keeps the outermost disclosure as context. That context earns no coverage and registers no rendered open state. A disclosure that contains a script fails resolution.
- Surfaces: each manifest surface runs its approved product scripts in a plate with approved-size buttons, an intermediate-width slider, a state selector and the manifest operations. In `ds-showcase/2`, a Surface plate runs the page's own reviewer runtime through hidden copies of its target and state controls. Unsupported reviewer infrastructure fails rendering. The plate denies the clipboard before product code runs. That denial is not a copy success.
- Source scripts (`ds-showcase/2` Surface and source-runtime plates): each classic inline product script runs natively, once, at its source position and in source order, after the plate bootstrap. Unsupported script shapes fail rendering.
- Motion: Replay and Stop per motion row plus a Reduced motion control that applies the page's own reduced-motion rules; the system preference sets its initial state. A `source-runtime` row runs the full approved surface and its hash-bound scripts in a fresh frame. Its status reports only browser-observed effects on the bound subject. An `invalid` status means the plate did not prove the approved motion.
- Traceability: every plate's source page, selector, variant, state and page hash, the frozen input hashes and coverage counts.

Plates are `srcdoc` frames with `sandbox="allow-scripts"` only (no same origin, forms, popups or top navigation). The page CSP allows no network, frames or objects and pins every script by SHA-256; frames inherit it. Native platforms are labeled HTML demonstrations, not native evidence. Gallery chrome is fixed renderer styling; it never styles product specimens.

For `design-system/3` and older pairs the view below is unchanged byte-for-byte. The safe scalar preview includes typography, color, spacing, corners, shadows and user-triggered duration/easing samples. Motion respects reduced motion. Unsupported expressions stay explicitly labeled as text-only; they do not count as a visually inspected sample. The HiFi remains the source for full component styling and state behavior.

For new or revised required pairs, provide `docs/design/design-system-preview.html` alongside the pair. It displays token names and values, safe scalar specimens, declared primitive variants, component content order, states, responsive/platform rules and source identities. The registry does not encode complete component styling: use the approved HiFi for actual component appearance and interactions, and do not fabricate button variants from token names. Native values remain platform contracts, not proof of HTML/native parity.

From the target repository root, run:

```text
python "<design-system-compiler-skill-root>/scripts/render_design_system_preview.py" --repo-root <repository-root> --markdown <design-system.md> --registry <design-system.json>
python "<design-system-compiler-skill-root>/scripts/render_design_system_preview.py" --repo-root <repository-root> --markdown <design-system.md> --registry <design-system.json> --check <design-system-preview.html>
```

The first command emits UTF-8 HTML on stdout only after filled-pair and current-source validation. Capture those exact bytes at an authorized new destination; do not redirect over an existing artifact before validation succeeds. The second command is read-only and rejects changed pair bytes, stale sources, hand-edited or missing previews. It grants no approval and does not validate visual quality. When the pair registers a motion variant or a `pseudo` state row, or the preview has Surface plates that run product scripts, inspect those plates in a browser; static checks cannot show their live treatment. For each `source-runtime` row, press Replay, Stop and the Reduced motion control once at its default target, and record the observed phases in the handoff. Return an `invalid` plate to the author. Link the view with the pair in the handoff.

The Markdown/JSON pair remains the authority. The HTML is reproducible and is not a product route, a HiFi manifest page or a third hand-maintained contract. The legacy view contains no scripts, remote resources or imported product CSS; the `design-system/4` view contains only hash-pinned local scripts and copies of approved HiFi CSS inside sandboxed plates. It is retained as a review artifact, so do not hide it with a broad generated-HTML ignore rule. Existing pairs are not rewritten merely to add a preview. A historical wireframe has no Tokens view. Do not mutate historical artifacts when adding the separate formal preview.

### Pair Checks

The stage Validation list owns the checklist. Two rules also apply:

- Every token, primitive, component, motion variant, state, and responsive entry is required by a real PRD surface; the responsive set has at least three ascending web viewports or at least two native/desktop size classes and matches the approved PRD and HiFi exactly.
- Every required PRD element maps to the final registry, and no unresolved page-local exception remains.

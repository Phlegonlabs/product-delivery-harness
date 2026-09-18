# Product Design Output Contract

`sourceBindings.uiDesign.sha256` uses the canonical UI approval digest, not the raw file hash. Run `python "<ui-design-builder-skill-root>/scripts/ui_approval_digest.py" <ui-design.md>`; it excludes active derived pair/replacement linkage lines so linking the compiled pair does not invalidate its own input. All other source bindings use raw-file SHA-256.

Publish these files only when `docs/design/ui-design.md` records `Design System Need Gate: required`:

- `docs/design/design-system.md`
- `docs/design/design-system.json`

The pair forms one reusable visual implementation handoff. `PRD.md` owns product behavior; `docs/design/ui-design.md` owns UI decisions and the approved HiFi target; approved `wireframes/4` provides the structural interactive review view. The design-system pair owns tokens, closed variants, reusable components, motion, and the state matrix. Publish or revise both files together. New approval authority belongs to `design-system/2`; `design-system/1` remains inspection-only and is rejected by the publication checker.

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
- `sourceBindings` for current PRD, architecture, stack, `ui-design.md`, approved wireframes/4, and approved HiFi target bytes;
- one global responsive verification set for homogeneous products, or one set per `surfaceContracts` entry for hybrids; copy the exact approved PRD/wireframe set, with at least three ascending web `viewports` or two native/desktop `sizeClasses`, plus each surface’s release/capture identity and approved stack semantics; hybrids omit global platform, styling mechanism, viewports, and size classes;
- only the tokens the product uses;
- four primitive layers with closed variant sets;
- optional primitive `dsId` values matching `DS-[A-Z]+-<number>` when a primitive needs a trace identity;
- signature visual rules with stable `DS-*` IDs, registered in `signatureRules` — every complete `DS-*` token the Markdown names (rule, primitive `dsId`, or `DS-COMP-*`) must resolve to this file, malformed lookalikes fail, and IDs are globally unique across all three registries;
- recurring product components with `DS-COMP-*`, required content order, composition, and states;
- registered motion variants; and
- the UI state matrix.

## Approved Input Quality Check

- The Design System Need Gate is `required` and records its human owner and reason.
- `ui-design.md` records an approved immutable target, source hash, routes and states, the exact PRD/wireframe responsive set, passing browser-matrix evidence with no unintended overlap, clipping, occlusion, or horizontal overflow, tolerance, and allowed deviations.
- `wireframes.html` has human approval recorded in `ui-design.md`, and each `UI-*` page matches the PRD.
- Each UI surface has one main purpose, one task-fit layout pattern, a real route or explicit `n/a`, and a density reason.
- Every visible region carries the approved Copy Freeze: exact static strings and action labels, complete dynamic source/order/format/count/length/fallback contracts with representative examples, alternate-state copy, content priority, ordered responsibilities, actions, states, responsive behavior, and trace IDs.
- Public surfaces have bounded SEO fields, correct heading order, and image alt-text contracts.
- Ready, loading, empty, error, disabled, permission-denied, stale, expired, long-content, reduced-motion, and mobile-reflow states are covered or explicitly `n/a` at every responsive target.
- Scope, routes, actions, content responsibilities, wireframe structure, responsive rearrangement, and trace IDs stay fixed across visual directions.
- Copy stays fixed across visual directions. A proposed wording change returns to `product-definition-builder` as a PRD and wireframe copy delta and requires renewed Copy Freeze approval.

If product behavior or stack is missing, return a bounded Product Definition update. If UI direction or evidence is missing, return to `ui-design-builder`. Do not invent either in the design system.

## Final Quality Check

### Derived HTML View

For new or revised required pairs, provide `docs/design/design-system-preview.html` alongside the pair. It displays token names and values, safe scalar specimens, declared primitive variants, component content order, states, responsive/platform rules and source identities. The registry does not encode complete component styling: use the approved HiFi for actual component appearance and interactions, and do not fabricate button variants from token names. Native values remain platform contracts, not proof of HTML/native parity.

From the target repository root, run:

```text
python "<design-system-compiler-skill-root>/scripts/render_design_system_preview.py" --repo-root <repository-root> --markdown <design-system.md> --registry <design-system.json>
python "<design-system-compiler-skill-root>/scripts/render_design_system_preview.py" --repo-root <repository-root> --markdown <design-system.md> --registry <design-system.json> --check <design-system-preview.html>
```

The first command emits UTF-8 HTML on stdout only after filled-pair and current-source validation. Capture those exact bytes at an authorized new destination; do not redirect over an existing artifact before validation succeeds. The second command is read-only and rejects changed pair bytes, stale sources, hand-edited or missing previews. It grants no approval and does not validate visual quality. Inspect the generated view in a browser and link it with the pair in the handoff.

The Markdown/JSON pair remains the authority. The HTML is reproducible, contains no scripts, remote resources or imported product CSS, and is not a product route, a HiFi manifest page or a third hand-maintained contract. It is retained as a review artifact, so do not hide it with a broad generated-HTML ignore rule. Existing pairs are not rewritten merely to add a preview. Never replace or mutate the approved wireframe Draft view with formal values.

### Pair Checks

- The approved `frontend-design` direction is recorded in `ui-design.md`; the compiler owns pair generation and validation.
- `frontend-design` and Impeccable were not rerun during normal compilation; their approved consequences are read from `ui-design.md`.
- The Style Integration record names `frontend-design`, the selected direction, and its candidate theme rules.
- The human owner approved one immutable UI target.
- The selected direction records applicable `MR-*`, inspected `REF-*`, confirmed `RP-*`, retrieval dates, and owner confirmation; full extraction history remains outside the package.
- The existing direction decision names a direction from the hash-bound Direction comparison table, with primary and stress cases for each platform before full HiFi or token compilation. Platform rules preserve platform-specific type, icons, controls, density, and feedback; compilation never replaces them with Web defaults.
- Visual references influenced only confirmed `Adopt / Adapt / Avoid` principles; protected artwork, branding, exact copy, HTML or CSS, source assets, and distinctive composition were not copied.
- Every token, primitive, component, motion variant, state, and responsive entry is required by a real PRD surface; the responsive set contains at least three ascending web viewports or at least two native/desktop size classes and matches the approved PRD and wireframe exactly.
- Every required PRD element maps to the final registry, and no unresolved page-local exception remains.
- Pair generation, filled-pair validation, contrast checks, and type-scale checks pass.
- Candidate directions, full reference analysis, and UI preview artifacts remain outside the pair.
- The final report names exact paths, decision status, validation results, assumptions, and open gaps.

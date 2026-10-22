# UI Implementation Contract

Load this reference only when a mission writes UI code or a UI review needs the implementation contract.

Every route gets product behavior, copy responsibility, and its exact responsive set from `PRD.md`; implementation architecture and technology come from `architecture.md` and `stack-decisions.md`. In initial design or an active enhancement, the approved HiFi supplies reviewed composition and embedded `ui-hifi-copy/1` exact copy and dynamic display contracts; older pinned contracts retain their wireframe authority; `docs/design/ui-design.md` supplies the current design decisions and Visual Approval. Routine maintenance follows the current accepted product and effective requirements without regenerating historical design sources. No downstream source overrides Product Definition.

Visual authority uses exactly one mode:

- **System-conformance mode:** the UI design gate is `required`; `docs/design/design-system.md` and `docs/design/design-system.json` are present, frozen, and validated as a pair. Legacy `docs/product/design-system.*` remains readable.
- **Target-conformance mode:** the gate is `not_required`; `ui-design.md` records one human-approved immutable page-faithful target with source hash, routes, states, responsive scope, tolerance, and allowed deviations.

A `blocked` or missing UI design gate blocks implementation.

## Design And Maintenance Routing

First classify this round using `ui-design-builder/references/review-workflow.md`. Initial design, enhancements and an explicit full redesign use the applicable design gates below. Routine maintenance is valid only with UI impact `none` or `style`; a `structure` or `both` impact follows the affected design gates. Routine maintenance uses the current product, effective PRD and accepted changes: update affected requirements and the existing change record, modify and verify the product, and retain historical Wireframe/HiFi/tokens without mandatory regeneration. Historical visual differences alone are not a delivery block. A new product or stack decision still returns to its owning flow. An already frozen managed RUN keeps its pinned contract; reconcile at a task boundary rather than weakening its gates.

A validated frozen maintenance record may retain either `ui-design/3` or `ui-design/2`. Harness checks the current Product Definition, PLAN scope, retained target identity and declared frozen design files; it does not require a fresh render or new approval of historical pair/preview files for that route. Retention grants no current HiFi, pair or preview PASS. Without that record, new `/3` delivery still requires the complete `/4` package and its exact frozen derived HTML.

## Rules For Every UI Mission

Before author dispatch, apply [Frontend Visual Inputs](frontend-visual-inputs.md). Carry the selected captures, font/asset sources and visual features into the actual implementation task; require the author's own source and capture inspection evidence.

An enhancement implements only the accepted added/changed page or region scope. Retain existing Wireframe and HiFi pages, approved tokens/components and behavior outside that scope. New entry/return links are explicit affected regions. Follow `../../ui-design-builder/references/enhancement-recommendations.md`'s Incremental UI Scope and compare preserved screens before and after; a broad redraw is a scope failure even when every route still exists.

For initial UI and enhancements, reconcile explicit hero/motion requests with the approved UI/MM scope before writing. Use the approved composition, assets, CTA and compact reflow, then exercise the actual trigger, intermediate behavior, end state and reduced-motion fallback. A static screenshot or deferred asset cannot close a required motion item. Native typography, transitions, gestures and haptics need the approved platform tooling in the first implementation slice and final matrix; HTML projection evidence does not satisfy them. Route new design recommendations through `../../ui-design-builder/references/enhancement-recommendations.md` before changing a frozen decision.

1. Read `PRD.md`, `architecture.md` and `stack-decisions.md` before writing. For initial design or active enhancement, also read current approved `ui-design.md`, the matching copy-complete HiFi page and the active visual source (plus the wireframe only when required by a legacy frozen contract). Missing or mismatched route, state, responsive set, copy completeness, required decision, target scope, browser evidence, component foundation, or styling approach blocks that design route. Routine maintenance checks the current accepted product and effective requirements. A route whose PRD entry records SEO metadata implements exactly that `<title>`, meta description, canonical URL, and recorded extras; the rendered `<head>` is part of the deliverable. A missing SEO record is a PRD contract gap routed to `product-definition-builder`, never an implementation-time invention.
2. Follow the PRD's responsibilities and behavior. For initial design or active enhancement, also follow the affected approved HiFi's region order, grouping, element inventory, state placement, responsive rearrangement, exact static/action/feedback/alternate-state copy, and dynamic source/order/format/count/length/fallback contracts. Do not let a visual source change product structure or wording.
3. Implement every declared product state. Optional `design_coverage` maps visual checks onto an active state and records other global states that do not apply. Long-content, reduced-motion and mobile-reflow cannot be excluded when the design-system matrix requires them. Plans without this field retain their existing state declarations.
4. Treat unapproved screenshots, Figma frames, generated media, exploration HTML, unselected direction studies, and design inspiration as non-canonical. Only the approved target or design-system pair recorded in `ui-design.md` binds visual implementation. Reviewer navigation and deferred placeholders are not product scope. Implementation cannot reselect taste or derive new product requirements from generic defaults.
5. Run one Final UI Acceptance from `verification-gates.md` on the exact candidate. Combine the Final Visual Parity Loop and independent read-only page-quality pass in that review. Cover the recorded responsive/device set, product states, and design conditions in normal and reduced motion. Every matrix entry is free of unintended overlap, clipping, occlusion, and horizontal overflow. Hosted-browser target-conformance compares the approved HiFi reference and implementation side by side with `parity_capture.py`; browser-extension, native, and desktop surfaces use their platform-specific capture tooling or labeled manual captures and never substitute a hosted URL. System-conformance checks the pair against real product source plus the screenshot matrix. One reviewer checks parity, heuristic UX, accessibility, responsive/device behavior and performance using current shared evidence. Consolidate defects before repair, then recheck original defects and affected consumers within the existing budget. Impeccable may contribute only through a separately authorized side-effecting workflow.
6. Stop when implementation requires unsupported authority. Route product behavior, wording, display-contract, architecture, or stack changes to `product-definition-builder`; route copy completeness, wireframe, style, motion/media, or UI-target changes to `ui-design-builder`; route pair-only changes to `design-system-compiler`.
7. Implement a changed route from its current approved source only. Mixing superseded values into the new implementation is a contract violation.
8. Classify every completed UI task as `none`, `style`, `structure`, or `both`. `none` keeps all UI sources untouched. In active design work, `style` traces changed visual values to the approved direction, variant, or target, and `structure` or `both` integrates only when the frozen PRD, copy completeness, and current UI-design sources reflect the change. A wording or dynamic display-contract change is at least `structure`. In routine maintenance, which allows only `none` or `style`, update affected PRD requirements and verify the current product without asserting that historical design files match later accepted changes; a `structure` or `both` change leaves maintenance and follows the affected design gates. The parent records the strongest task impact in `ui_impact_summary`; `doc_delta` is required when that strongest impact is `structure` or `both`.
9. Motion is a design decision, not an implementation preference. Durations, easing, generated assets, and added or removed transitions trace to `ui-design.md`'s selected Motion and Media Intent plus a registered motion variant or the approved target's observable behavior. A pre-selection direction study is not this authority. A missing authority routes upstream rather than being guessed.

For a native/desktop platform whose approved Platform rules say `Native proof: required before expansion`, implement and verify the representative primary and stress cases first. Use the approved stack and native UI-test tooling or labeled manual native captures to check text scaling, control geometry, navigation, keyboard/safe-area behavior, and feedback; verify any approved haptics on a device that supports them. Record exact-head results in the existing UI evidence matrix before expanding to the remaining screens. HTML studies and HiFi projections cannot satisfy this checkpoint. Missing platform capability stays unvalidated; it never becomes an assumed PASS. This checkpoint also applies in target-conformance mode, and the final full matrix remains required.

## System-Conformance Mode

1. Read both design-system files with the product and UI design sources.
2. Invent no visual value. Colors, spacing, radii, type, durations, easing, and distances come from tokens; primitive props come from closed variants.
3. Compose registered primitives and product components and use only registered motion variants.
4. Use `design-system.json`'s `stateMatrix` and exactly one responsive verification set.
5. Run `python "<delivery-harness-skill-root>/scripts/check_ui_contract.py" --registry <design-system.json> --repo-root <root> --path <product-source-dir>` against changed files during the mission and real product source at the final gate. A filtered or zero-file run is not a clean signal, and neither is a `--token-source` or `--primitive-source` run: it prints NOT CONTRACT-CLEAN and exits 1 because source roles come from `design-system.json`.
6. A missing token, primitive, variant, component, or motion rule is a design-system delta; implementation never writes the frozen pair.

### Design Coverage

An opt-in surface keeps its exact product `states` and adds this separate projection. This partial example still needs reasons for every other inapplicable global matrix entry:

```json
"design_coverage": {
  "schema": "ui-design-coverage/1",
  "conditions": [
    {"id": "long-content", "base_state": "ready"},
    {"id": "reduced-motion", "base_state": "ready"},
    {"id": "mobile-reflow", "base_state": "ready"}
  ],
  "not_applicable": [
    {"state": "submitting", "reason": "This privacy route has no submission form."}
  ]
}
```

Conditions use an active product state. Exclusions cannot duplicate product states or exclude a required universal condition. Capture and evidence readers use the same projection. Route-map `conditions` entries supply setup separately from the base-state setup; long-content requires explicit setup on both reference and application. Browser motion preferences are observed, applied before navigation and restored even when a capture fails.

## Target-Conformance Mode

1. Confirm that `ui-design.md` says `Design System Need Gate: not_required` and names the approved target as the replacement visual contract.
2. Implement only the routes, states, and responsive scope that target covers. For an HTML target, port its observable layout, composition, visual values, and deterministic motion within tolerance; do not ship the review sidebar or mocked auth bypass.
3. Put repeated values in the smallest shared theme or style source needed. Do not invent a formal token registry or component catalog.
4. Derive choices only from the observable target, `ui-design.md`'s allowed deviations, approved brand source, and platform conventions. Mark non-observable behavior as a gap.
5. Verify page-to-target conformance with the recorded comparison method and tolerance. Do not claim design-system conformance when no registry exists.
6. When implementation reveals a genuine reusable-system need, return a Design System Need Gate delta to `ui-design-builder`.
7. When an approved target changes, port the current values and remove superseded styles/classes. Never graft a new target onto obsolete CSS.

For design-system work, load `design-system-compiler`; it owns compilation. For UI implementation, load the owner-bound frontend-authoring skill and apply this document's conformance rules around it. Do not claim an external skill exposes compilation, conformance, or read-only modes that its pinned tree does not define. Do not reopen UI intake, Style Integration, motion/media selection, or visual direction during implementation.

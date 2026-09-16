# UI Implementation Contract

Load this reference only when a mission writes UI code or a UI review needs the implementation contract.

Every route gets product behavior, copy responsibility, and its exact responsive set from `PRD.md`; implementation architecture and technology come from `architecture.md` and `stack-decisions.md`; approved `wireframes.html` supplies reviewed structure plus exact copy and dynamic display contracts; and `docs/design/ui-design.md` supplies Copy Freeze, Style Integration, Motion and Media Intent, HiFi evidence, Visual Approval, and the Design System Need Gate. No downstream source overrides Product Definition.

Visual authority uses exactly one mode:

- **System-conformance mode:** the UI design gate is `required`; `docs/design/design-system.md` and `docs/design/design-system.json` are present, frozen, and validated as a pair. Legacy `docs/product/design-system.*` remains readable.
- **Target-conformance mode:** the gate is `not_required`; `ui-design.md` records one human-approved immutable page-faithful target with source hash, routes, states, responsive scope, tolerance, and allowed deviations.

A `blocked` or missing UI design gate blocks implementation.

## Rules For Every UI Mission

1. Read `PRD.md`, `architecture.md`, `stack-decisions.md`, approved `ui-design.md`, the matching approved and copy-frozen page in `wireframes.html`, and the active visual source before writing. A missing or mismatched route, state, responsive set, copy status, Copy Freeze, approval, target scope, browser evidence, component foundation, or styling approach is a blocker. A route whose PRD entry records SEO metadata implements exactly that `<title>`, meta description, canonical URL, and recorded extras; the rendered `<head>` is part of the deliverable. A missing SEO record is a PRD contract gap routed to `product-definition-builder`, never an implementation-time invention.
2. Follow the PRD's responsibilities and behavior plus the wireframe's region order, grouping, element inventory, state placement, responsive rearrangement, exact static/action/feedback/alternate-state copy, and dynamic source/order/format/count/length/fallback contracts. Do not let the visual source change product structure or wording.
3. Implement every declared ready, loading, empty, error, disabled, permission-denied, stale, expired, long-content, reduced-motion, and mobile-reflow state, or retain its explicit `n/a` reason.
4. Treat unapproved screenshots, Figma frames, generated media, exploration HTML, and design inspiration as non-canonical. Only the approved target or design-system pair recorded in `ui-design.md` binds visual implementation. Reviewer navigation and deferred placeholders are not product scope.
5. Run the Final Visual Parity Loop across the recorded responsive/device set and states in normal and reduced motion. Every matrix entry is free of unintended overlap, clipping, occlusion, and horizontal overflow. Hosted-browser target-conformance compares the approved HiFi reference and implementation side by side with `parity_capture.py`; browser-extension, native, and desktop surfaces use their platform-specific capture tooling or labeled manual captures and never substitute a hosted URL. System-conformance checks the pair against real product source plus the screenshot matrix. Differences outside tolerance enter the bounded repair cycle. After parity closes, run the independent read-only page-quality pass from `verification-gates.md`; Impeccable may contribute only through a separately authorized side-effecting workflow.
6. Stop when implementation requires unsupported authority. Route product behavior, wording, display-contract, architecture, or stack changes to `product-definition-builder`; route Copy Freeze, wireframe, style, motion/media, or UI-target changes to `ui-design-builder`; route pair-only changes to `design-system-compiler`.
7. Implement a changed route from its current approved source only. Mixing superseded values into the new implementation is a contract violation.
8. Classify every completed UI task as `none`, `style`, `structure`, or `both`. `none` keeps all UI sources untouched. `style` traces every changed visual value to the approved direction, variant, or target. A wording or dynamic display-contract change is at least `structure`. `structure` or `both` integrates only when the frozen PRD, Copy Freeze, and approved UI-design sources already reflect the change. The parent records the strongest task impact in `ui_impact_summary`; `doc_delta` is required when that strongest impact is `structure` or `both`.
9. Motion is a design decision, not an implementation preference. Durations, easing, generated assets, and added or removed transitions trace to `ui-design.md`'s Motion and Media Intent plus a registered motion variant or the approved target's observable behavior. A missing authority routes upstream rather than being guessed.

For a native/desktop platform whose approved Platform rules say `Native proof: required before expansion`, implement and verify the representative primary and stress cases first. Use the approved stack and native UI-test tooling or labeled manual native captures to check text scaling, control geometry, navigation, keyboard/safe-area behavior, and feedback; verify any approved haptics on a device that supports them. Record exact-head results in the existing UI evidence matrix before expanding to the remaining screens. HTML studies and HiFi projections cannot satisfy this checkpoint. Missing platform capability stays unvalidated; it never becomes an assumed PASS. This checkpoint also applies in target-conformance mode, and the final full matrix remains required.

## System-Conformance Mode

1. Read both design-system files with the product and UI design sources.
2. Invent no visual value. Colors, spacing, radii, type, durations, easing, and distances come from tokens; primitive props come from closed variants.
3. Compose registered primitives and product components and use only registered motion variants.
4. Use `design-system.json`'s `stateMatrix` and exactly one responsive verification set.
5. Run `scripts/check_ui_contract.py --repo-root <root>` against changed files during the mission and real product source at the final gate. A filtered or zero-file run is not a clean signal.
6. A missing token, primitive, variant, component, or motion rule is a design-system delta; implementation never writes the frozen pair.

## Target-Conformance Mode

1. Confirm that `ui-design.md` says `Design System Need Gate: not_required` and names the approved target as the replacement visual contract.
2. Implement only the routes, states, and responsive scope that target covers. For an HTML target, port its observable layout, composition, visual values, and deterministic motion within tolerance; do not ship the review sidebar or mocked auth bypass.
3. Put repeated values in the smallest shared theme or style source needed. Do not invent a formal token registry or component catalog.
4. Derive choices only from the observable target, `ui-design.md`'s allowed deviations, approved brand source, and platform conventions. Mark non-observable behavior as a gap.
5. Verify page-to-target conformance with the recorded comparison method and tolerance. Do not claim design-system conformance when no registry exists.
6. When implementation reveals a genuine reusable-system need, return a Design System Need Gate delta to `ui-design-builder`.
7. When an approved target changes, port the current values and remove superseded styles/classes. Never graft a new target onto obsolete CSS.

For design-system work, load `design-system-compiler`; it owns compilation. For UI implementation, load the owner-bound frontend-authoring skill and apply this document's conformance rules around it. Do not claim an external skill exposes compilation, conformance, or read-only modes that its pinned tree does not define. Do not reopen UI intake, Style Integration, motion/media selection, or visual direction during implementation.

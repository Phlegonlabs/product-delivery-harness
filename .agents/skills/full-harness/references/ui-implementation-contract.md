# UI Implementation Contract

Load this reference only when a mission writes UI code or when a UI review needs the implementation contract. The core skill keeps the route and safety boundary concise; this file carries the detailed design-conformance rules.

Every UI route gets structure and behavior from its `PRD.md` `UI-*` entry. Approved `wireframes.html` provides the all-page, section-label, viewport, and state review projection; it helps implementation inspect the contract but never overrides `PRD.md`. Visual authority comes from exactly one mode selected by `PRD.md`'s Design System Need Gate:

- **System-conformance mode:** the gate is `required`; `design-system.md` and `design-system.json` are present, frozen, and validated as a pair.
- **Target-conformance mode:** the gate is `not_required`; `PRD.md` records a human-approved immutable page-faithful UI target with source hash, routes, states, responsive scope, tolerance, and allowed deviations. No placeholder design-system pair exists. When that target is retained high-fidelity HTML — the default web route from the UI Design Pass — each approved HTML reference file binds the routes it records, and every bound page is implemented from its HTML reference.

A `blocked` or missing gate blocks UI implementation. A historical pair does not silently override a new `not_required` decision; its retirement or continued authority must be explicit.

If a mission's planned `required_skills` includes `frontend-design`, the worker uses frontend-design conformance mode only. The skill changes execution craft, not the selected direction, contract precedence, or approval status.

## Rules For Every UI Mission

1. Read `PRD.md`, its approved UI Design Handoff, the matching approved page in `wireframes.html`, and the active visual source before writing. Resolve routes through each `UI-*` entry's `Route(s):` field. A missing route claim, duplicate claim, missing or mismatched approved wireframe artifact, missing target scope, or inconsistent Design System Need Gate is a blocker. A route whose entry records SEO metadata implements exactly that `<title>`, meta description, and recorded extras — the rendered `<head>` is part of the deliverable. A route with no SEO metadata record is a PRD contract gap routed to `prd-builder`, never an implementation-time invention.
2. Follow the PRD surface's responsibilities and behavior plus the wireframe's region order, grouping, element inventory, state placement, and responsive rearrangement. Do not let the visual source change product structure.
3. Implement every declared ready, loading, empty, error, disabled, permission-denied, stale, expired, long-content, reduced-motion, and mobile-reflow state, or retain its explicit `n/a` reason. The ready state alone does not close the task.
4. Treat unapproved screenshots, Figma frames, generated images, exploration or preview HTML, UI Preview Gate outputs, and design inspiration as non-canonical evidence. Approved low-fidelity `wireframes.html` is structural review evidence only. Only the approved target recorded in the PRD handoff binds target-conformance visual implementation; approved HTML reference files named by that handoff are binding target evidence, not previews to reinterpret.
5. Run visual verification across the recorded responsive set and states, in normal and reduced motion, and record evidence using `references/verification-gates.md`. The final gate for every UI run includes the Final Visual Parity Loop: in target-conformance mode, render the approved HTML reference side by side with the implemented route at the same route-breakpoint-state and record the comparison; in system-conformance mode, a clean contract check against the real product source plus the full screenshot matrix is the comparison. Differences outside the recorded tolerance enter the repair cycle there, up to two rounds. Once the loop closes, the final gate runs the page-quality pass (`verification-gates.md`) with the skill bound to the `ui_quality_verification` slot.
6. Stop when implementation requires a route, action, state, structure, visual value, component, or tolerance the active source does not support. Route PRD, wireframe, or UI-target changes to `prd-builder`; route formal design-system changes to `product-design-builder`.
7. Implement a changed route from its current approved source only. Mixing values from a superseded source version into the new implementation is a contract violation, not a merge.

## System-Conformance Mode

1. Read `design-system.json` and `design-system.md` with the route sources.
2. Invent no visual value. Colors, spacing, radii, font sizes, durations, easing, and distances come from tokens; primitive props come from closed variant sets.
3. Reimplement no control or surface. Compose registered primitives and product components and use only registered motion variants.
4. Use `design-system.json`'s `stateMatrix` and exactly one responsive verification set: `viewports` for web or `sizeClasses` for native/desktop.
5. Run `scripts/check_ui_contract.py` against changed files during the mission and the real product source at the final gate. A filtered or zero-file run is not a contract-clean signal.
6. A missing token, primitive, variant, component, or motion rule is a design-system delta. Never write the frozen pair from an implementation mission.

## Target-Conformance Mode

1. Confirm that the PRD explicitly says `Design System Need Gate: not_required` and names the approved page-faithful target as the replacement visual contract.
2. Implement only the routes, states, and responsive scope that target covers. Do not broaden a single target to unrelated pages. When the target is high-fidelity HTML, build each recorded route from its approved HTML reference file — port its observable layout, composition, and visual values into the production stack within the recorded tolerance; the reference is the comparison source, not scaffolding to copy.
3. Place repeated visual values in the smallest shared theme or style source the implementation needs. Avoid page-local drift, but do not invent a formal token registry, component catalog, or design-system pair.
4. Derive visual choices only from observable target evidence — for an HTML target, the reference file's markup, styles, assets, and rendered behavior — the PRD handoff's allowed deviations, the approved brand source, and platform conventions. Mark non-observable motion or interaction as a gap instead of guessing.
5. Verify page-to-target conformance with the recorded comparison method and tolerance. Do not run `check_ui_contract.py` or claim design-system conformance when no registry exists.
6. When implementation reveals genuine cross-surface token, closed-variant, multi-theme, multi-platform, or automated-conformance needs, stop and return a Design System Need Gate delta to `prd-builder`; do not grow an undeclared design system inside the code mission.
7. When a route's approved HTML reference changes, port the new file's observable style values and remove the styles and classes the new reference no longer contains — from that route, and from the shared style source when no other route's current reference still uses them. Never graft the new reference onto the previous implementation's CSS; the previous version's styles survive only where the new reference still shows them.

For design-system source work, load `product-design-builder` and `frontend-design` in compilation mode. For UI implementation, load `frontend-design` only when the user explicitly selected it for the new or high-impact visual surface and use conformance mode. Do not reopen concept generation or Taste direction selection during implementation.

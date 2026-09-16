# Style Integration And HiFi Pass

Run this pass only inside an active `ui-design-builder` flow after Product Definition Approval and human Wireframe Approval. It turns the approved structural wireframe into a human-approved visual target. `frontend-design` is the single design author. `impeccable` and rubric graders provide review evidence; they do not publish or approve the target.

## Frozen Inputs

Every direction and HiFi candidate uses the same:

- approved `PRD.md`, `architecture.md`, and `stack-decisions.md` identities;
- complete `UI-* × responsive target × non-n/a state` matrix;
- approved `wireframes.html` region order, grouping, actions, flows, states, and media placeholders;
- UI Design Intake and Visual Preference Brief;
- Motion and Media Intent rows;
- exact copy or bounded display contracts;
- brand, accessibility, platform, performance, component-foundation, and styling constraints; and
- applicable `MR-*` market evidence plus inspected `REF-*` visual evidence.

The pass cannot add, remove, reorder, or reinterpret product scope, content responsibility, routes, actions, flows, states, trace IDs, responsive targets, or approved stack constraints. A structural finding returns to `product-definition-builder` and Wireframe Approval. A visual direction that needs a different framework, component foundation, styling method, runtime, or provider returns to the Stack Decision Checkpoint and Product Definition Approval.

## Style Intake Gate

The intake must already be complete before `frontend-design` proposes a theme or Design Read. If it is missing, read `ui-design-intake.md`, ask the human owner the product-specific questions, end the turn, and wait. Never recommend a visual direction in the same turn as the intake.

If the owner supplies a reference, read `design-reference-guide.md` and inspect it through the matching source route. Record `REF-*` sources and proposed `Adopt / Adapt / Avoid` `RP-*` principles, then end the turn for confirmation before creating a direction.

When the owner has a clear direction, produce one product-specific direction. When the owner asks to compare or remains unsure after intake, produce exactly three materially different directions over the same frozen screens and states. Never substitute a fixed catalog of style names.

Present the complete direction set to the human owner. End the turn and wait for `approve`, `select`, `mix`, or `reject`; even a one-direction set needs explicit approval. A mix or rejection creates one complete revised direction set and another explicit decision. Do not create the connected HiFi reference or invoke a generation provider before a direction is selected.

## Frontend Design Style Integration

Load `frontend-design` and use its brief-first, subject-grounded design process. It owns the direction, page theme, and connected HiFi design-reference HTML across every surface. Do not load `design-taste-frontend`, `gpt-taste`, Impeccable build/refine commands, or another visual author in parallel.

For each direction, record:

- a versioned `VD-*` ID and concise design intent;
- product and audience fit;
- confirmed `REF-*` and `RP-*` evidence;
- layout, composition, typography, color, surface, shape, icon, imagery, and motion rules;
- tradeoffs and an avoid list; and
- how it respects the approved component foundation and styling approach.

Choose iconography through current official-source lookup. When icons are required, compare Lucide, Phosphor, Heroicons, and Tabler, select one primary and one named fallback, and record license, framework support, maintenance evidence, URLs, and retrieval dates. Record `UNVALIDATED` when evidence is unavailable; never silently choose from memory.

Choose typography with the same evidence discipline. Record display/body roles, required weights, Latin and CJK coverage, fallback order, loading strategy, source URLs, and retrieval dates. Record the palette derivation, contrast intent, and whether dark mode is in scope. These candidate theme values render the HiFi target but are not yet a frozen design-system contract.

## Motion And Generated Media

Consume the approved Motion and Media Intent rows without re-asking them. Use `motion-and-media-routing.md` to select CSS/WAAPI or the minimum applicable GSAP skills only after Wireframe Approval.

After direction selection, an installed Higgsfield MCP or another owner-approved generation provider may create an approved generated or curated motion asset only after exact provider/action authorization. Record provider capability, prompt, output identity, usage constraints, placement, fallback, and review result. If generation is not required for visual judgment, retain the typed static placeholder and defer the call. Generated output cannot add copy, controls, states, routes, or claims.

Required deterministic functional UI motion may run locally in the HiFi HTML with its normal and reduced-motion behavior. A generated video or cinematic asset has a static poster/fallback even when the generated output is present.

## Connected HiFi Reference

Produce a connected `ui-hifi/2` HTML package with `index.html` as its entry and sibling HTML files for separate pages. Cover every in-scope `UI-*` screen, responsive target, and non-`n/a` state. Each page embeds its CSS, scripts, fonts, and media. Keep a left review sidebar, screen/state switching, and the product actions needed to traverse every approved flow. A product tab or page link uses a real anchor to its declared HTML destination. Buttons change a declared local state, including overlays and feedback. Reviewer sidebar navigation never substitutes for product-control interaction coverage. Every current Visual Approval requires schema 2; schema-1 single-file references remain inspection-only.

The HTML contains exactly one canonical restrictive CSP meta:

`default-src 'none'; base-uri 'none'; connect-src 'none'; form-action 'none'; frame-src 'none'; object-src 'none'; navigate-to 'self'; img-src data:; media-src data:; font-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'`

The offline browser additionally allows only the declared package pages. CSP alone does not enforce the page allowlist and cannot prove arbitrary JavaScript safe. Follow the manifest and interaction-output schemas in `output-contract.md`.

The file calls no live backend, credential, identity provider, or unapproved generation provider. Login, registration, recovery, and authentication-error preview scenes may be marked `n/a` for this visual review without removing their production requirements. Native chrome may use a labeled HTML placeholder.

## Impeccable Quality Review And PRD-Bound Grading

Before human visual approval:

1. Freeze the PRD, `ui-design.md`, wireframe, and HiFi candidate paths and SHA-256 values.
2. Run `impeccable critique` and `impeccable audit` against the exact connected candidate only with explicit workflow authorization. Impeccable may have side effects and is not a read-only publication gate. Its Nielsen, detector, accessibility, responsive, performance, theming, and implementation-integrity scores are diagnostic evidence; the record uses exact `PASS` verdicts after the human gate standard is met.
3. Run `ui-grading-rubric.md`'s Technical Hard Gate and complete `H1`–`H9` scoring. These scores, not Impeccable's native totals, decide readiness.
4. Consolidate every Impeccable and rubric finding into one root-cause defect ledger before editing.
5. Let `frontend-design` make one repair batch. Then re-run the authorized Impeccable critique and audit checks plus the complete rubric once on the new SHA-256.

The candidate is ready for the human gate only when overall `H1`–`H9` is at least 90, `H2`, `H4`, and `H8` are each at least 90, every dimension is at least 60, and no block or disputed dimension remains. Do not repair merely to chase 100. A second failed review stops at `blocked` unless the owner explicitly approves one changed strategy and acceptance matrix.

## Browser And Human Visual Approval

Render every page-target-state and overlay in a real browser inside a closed offline sandbox and record the verdict as exact `PASS`. For schema 2, load the hash-checked pages into an isolated same-origin browser context using intercepted, locally fulfilled document requests; disable external network, service workers, popups, downloads, and forms. Allow only the exact declared HTML documents and block redirects or other destinations. Reset to the declared source page/state before each test. Click each product control and activate it by keyboard at every source responsive target; wait for the destination, then verify its visible surface/state and correct focus or selected-tab behavior. Begin the action transcript after trusted source-page/state setup completes. During each tested action, capture every attempted document navigation, including blocked ones, rather than filtering failures from the transcript. The review sidebar may set up a test but cannot be the tested control.

HiFi surface evidence keeps method `sandboxed-offline-browser`. Schema-2 packages require `ui-output/2` with the exact interaction results and local-navigation transcript described in `output-contract.md`. A missing result, wrong destination, invisible destination, bad focus, undeclared navigation, external request, popup, form attempt, or console error fails. Schema-1 references retain their existing `ui-output/1` no-navigation policy. Also reject unintended overlap, clipping, occlusion, broken wrapping, off-container content, or horizontal overflow. Verify long and localized content, normal/reduced motion, and intentional-overlay stacking and dismissal.

Present only a passing candidate. Record the human decision as `approved`, `revision_requested`, or `blocked` in `ui-design.md`, with the decision owner and date. Approval proves visual-direction conformance, not representative-user usability or production readiness.

## Retention And Design System Need Gate

Retain an approved all-screens target under `docs/design/ui-references/<run-id>/index.html` only with exact write approval. Record its SHA-256, routes, states, responsive scope, browser evidence, tolerance, and allowed deviations. Archive superseded references; never delete them or leave live pointers to archived paths.

After Visual Approval, record exactly one Design System Need result:

- `required`: a formal reusable token/component contract is needed or requested;
- `not_required`: the approved target, `ui-design.md`, wireframe, and PRD are sufficient; or
- `blocked`: a required decision or source is missing.

When `required`, write `Compiled design system pair: pending — design-system-compiler` as the exact handoff marker, run the compiler preflight against the approved PRD/architecture/stack/UI/wireframe/HiFi bytes, compile both files, and then replace the marker with both pair paths and hashes. The ordinary UI checker rejects a pending marker. When `not_required`, publish no placeholder pair and record the machine-bound existing-pair disposition.

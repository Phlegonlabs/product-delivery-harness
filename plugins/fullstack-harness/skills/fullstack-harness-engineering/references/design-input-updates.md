# Design Input Updates

Use this reference when the user provides a new or updated PRD, wireframe, design system, design inspiration, or explicit page-faithful target for either a new build or an existing app refinement.

## Core Rule

Classify every visual source before planning or implementation:

- **Design inspiration** is non-canonical evidence. It can influence implementation only after `product-design-builder` extracts owner-confirmed principles and freezes their consequences into `wireframes.md`, `design-system.md`, and `design-system.json`. A URL, screenshot, Figma frame, or market-research source is not implementation authority merely because it exists.
- **Page-faithful target** is an explicit user requirement for visual conformance. Treat it as binding only after the user requests faithful matching and the readable source version, route, states, responsive scope, and acceptance tolerance are frozen. Preserve it as version-bound acceptance evidence; do not silently broaden one target to other routes.

`design-system.md` and `design-system.json` are binding together, and implementation works from that pair plus the route's screen entry in `wireframes.md` — see `ui-implementation-contract.md`. `product-design-builder` must normalize either accepted source type into that frozen contract before code changes begin.

A `frontend-design` result produced or requested during implementation is a proposed design-input delta, not code-side authority. Do not apply its new visual direction, token, variant, component, motion pattern, or structure directly. Return it to `product-design-builder`, normalize and freeze the accepted change, then resume against the revised design system.

```text
1. Identify source type and version.
2. Compare updated input against the current contract, baseline app, or previous assumptions.
3. Record the delta and affected pages/components/API/data surfaces.
4. Resolve conflicts before implementation.
5. Freeze the accepted delta.
6. Implement only the accepted delta.
7. Verify conformance and regression.
```

**What "freeze" records.** Freezing is a manifest entry, not just a decision. Record the accepted delta on the affected source in the HARNESS_PLAN manifest: for a PLAN-v5 source, set `staged_revision` to the accepted revision. The source status moves to `frozen` or `delta_accepted`, and the binding fields (`location`, `content_sha256`, `source_revision`) update only once that revision is published to the canonical source location — then the PLAN revision and digest change too. A `staged_revision` alone is not an executable publication; a ready or executing RUN never points at a product staging path. See the HARNESS_PLAN template's source map for these fields.

## Input Types

```text
Updated PRD: changed workflows, scope, roles, data, success criteria, non-goals
Updated Builder UX Direction: changed experience priority, guidance/control, density, interaction/layout, confirmation/recovery, validation depth, decision owner, or decision status
Updated wireframe: screen structure, navigation, page regions, component hierarchy, state coverage
Updated design system: tokens, typography, spacing, radius, color, added/removed primitives, changed closed variant sets, interaction states, motion variants, product components, content contracts, state matrix, responsive set
Design inspiration: screenshot, image, Figma frame, website, named product, or visual reference used only for confirmed design principles
Page-faithful target: version-bound screenshot, Figma frame, mockup, handoff spec, or page target the user explicitly requires the implementation to match
Existing app baseline: current route behavior, screenshots, traces, metrics, source implementation
```

## Delta Record

Every accepted change should be captured as a delta row:

```text
| Delta ID | Source | Change | Affected surfaces | Supersedes | Acceptance / verifier | Status |
|---|---|---|---|---|---|---|
| DELTA-001 | updated wireframe | <change> | UI-003, DS-002 | <old assumption> | <gate> | accepted |
```

Rules:

- A delta can add, modify, or explicitly remove behavior.
- Superseded requirements must be recorded; do not silently drop existing behavior.
- Design inspiration must return to `product-design-builder`; only its accepted, frozen `REF-*` / `RP-*` consequences may enter implementation.
- Page-faithful targets must map to routes/screens, states, responsive breakpoints, source version, and acceptance tolerance.
- Design-system deltas must map to affected components and variants.
- A design-system delta must name every route that uses the changed entry. A delta that removes an entry must state what replaces it at each call site; an entry that disappears from `design-system.json` while a route still uses it is a break, not a cleanup.
- `design-system.md` and `design-system.json` are binding sources, so a design-system delta is a contract change and must be frozen before implementation like any other. A code-side "we already built it this way" is not an accepted delta.
- PRD deltas that change data/API/auth/permissions must trigger architecture and E2E updates.
- Builder UX Direction deltas must preserve their human owner and selected/provisional/assumed status, map to affected `UX-*`, `UI-*`, and `DS-*` traces, and name any required prototype or usability revalidation.

## Page-Faithful Target Matrix

Use this only when the user explicitly provides page-faithful targets for different pages. Design inspiration never enters this matrix. When the product has wireframes, their screen entries already carry the accepted mapping — read it there instead of rebuilding the table.

```text
| Page / route | UI source | Source version / hash | Breakpoints | States | Tolerance / allowed deviations | Components | Data source | Acceptance evidence |
|---|---|---|---|---|---|---|---|---|
| /dashboard | Figma frame <id> | <version or content hash> | mobile/tablet/desktop | loading/empty/error/ready | <named tolerance and allowed deviations> | cards/table/filter | API-002 | screenshot + journey |
```

For a required UI surface, `screenshot + journey` means a retained screenshot for every listed breakpoint-by-state combination, plus journey/console/network evidence where applicable. Record the screenshot path, hash, and integration head in current RUN-v10 state. Older RUN-v9 UI evidence remains readable.

States to consider:

- loading
- empty
- error
- disabled
- hover/focus/active
- selected/expanded
- long content
- permission denied
- plan/entitlement blocked
- responsive overflow

When the product has a design system, `design-system.json`'s `stateMatrix` is the authority for this list. Mark an inapplicable state `<state>:n/a` explicitly rather than omitting it.

## New Build Flow

For a new build with provided PRD, wireframe, design system, and any explicit page-faithful targets:

```text
M1 source intake and conflict resolution
M2 contract freeze and traceability
M3 foundation/data/API if needed
M4 tokens, primitives, and the UI contract check
M5 product components
M6 route implementation from design-system.json + each route's wireframe screen
M7 E2E and visual evidence
```

M4 through M6 follow `execution-task-decomposition.md`'s UI Build Order: tokens and primitives before components, components before routes, the registry and catalog landing with the primitives, and the contract check landing with the first routes rather than at the end.

M6 and M7 above are illustrative single lines, not a mandate to implement every route in one mission and defer visual evidence to the end. Per `contract-and-traceability.md`'s mission-granularity corollary, split M6 into one mission per page (or a small tightly-coupled group) and pair each with its own scoped `visual` review as soon as that mission integrates, rather than one M6 covering every route reviewed once by a later M7.

## Existing App Refinement Flow

For an existing app with an updated PRD, wireframe, design system, or page-faithful target:

```text
M1 baseline current app and source map
M2 delta audit: old behavior vs updated input
M3 accepted delta implementation
M4 before/after conformance evidence
M5 regression checks for preserved behavior
```

Use before/after captures for UI changes. The "before" side proves the current state; the "after" side proves the accepted delta was implemented without broad rewrite.

This flow is primary whenever an updated input exists. `existing-app-refinement.md` carries a second five-mission pattern for an existing app; use that one alone only when the user wants refinement with no updated PRD, wireframe, design system, or page UI reference — an open-ended "make it better", where an audit has to establish the work in the first place. When both conditions hold (an existing app being refined because a new design system or PRD arrived), run this flow and fold that reference into it. Do not run two mission sets:

- Its baseline-evidence lenses supply what M1 captures.
- Its backlog rows and ranking rules supply how M2 records what it finds.
- A finding the audit turns up that is not part of the accepted delta stays a backlog row. It needs the user's acceptance and its own mission; it does not ride along in M3.
- Its regression-protection checklist and stop-and-ask conditions apply to M5 unchanged.

## Conflict Handling

Stop and ask when:

- Updated PRD conflicts with updated wireframe.
- Builder UX Direction conflicts with observed user needs, accessibility, product requirements, or platform conventions and no validation decision resolves the conflict.
- Updated design system conflicts with an explicit page-faithful target.
- A page-faithful target omits required states, breakpoints, source version, or tolerance.
- A design inspiration source is being treated as code-side authority without an accepted, frozen `product-design-builder` delta.
- An in-scope route has no wireframe screen, or a route needs a token, primitive, variant, component, or motion variant that `design-system.json` does not list. Ask for the missing screen or design-system entry instead of improvising the route or passing a raw value at the call site.
- The updated input can only be implemented by leaving the design system — for example a spacing value no token carries, or a control the primitives do not cover. The fix is a delta on the token or primitive, decided once by the design source, not a page-local exception.
- A conformance-mode `frontend-design` pass proposes a value, variant, component, motion pattern, or page structure the frozen package does not contain. Record it as a delta and stop the implementation mission; do not treat the skill output as implicit design approval.
- Updated input would remove existing app behavior without explicit acceptance.
- The source version is unclear and multiple variants exist.
- A pixel/design-faithful claim is requested but the source is unavailable.

## Verification

Design-input verification should include:

- Trace coverage: every accepted delta has implementation and evidence.
- Visual conformance: when a page-faithful target exists, the page/component matches its frozen source, scope, and tolerance; inspiration alone creates no pixel-faithful claim.
- State coverage: required states and breakpoints are checked.
- Behavior conformance: PRD workflow and data/API behavior still pass.
- Design-system conformance: tokens/components/variants follow the updated system.
- Contract conformance: the implementation uses only entries `design-system.json` lists, follows each touched route's wireframe screen, and contains no raw visual value, page-local control, inline layout style, or unregistered motion. Run the project's UI contract check — this skill's `scripts/check_ui_contract.py` covers the source-scanning subset, against the product's real source — plus the visual check across the responsive verification set `design-system.json` carries, its `viewports` for a web target or its `sizeClasses` for a native or desktop target, in normal and reduced motion. A drift from the design system is a contract violation, not a stylistic difference; a passing functional test does not cover it. See `SKILL.md`'s UI Implementation Contract for what each implementation mission owes.
- Builder direction conformance: selected choices are reflected and provisional/assumed choices remain explicit; this proves direction conformance, not usability.
- Usability evidence: when required, representative users or an approved equivalent complete the named task against the specified prototype or implementation; agent preference, screenshots, and automated E2E do not substitute for that evidence.
- Regression: preserved routes, permissions, data behavior, content, analytics, and E2E journeys still pass.

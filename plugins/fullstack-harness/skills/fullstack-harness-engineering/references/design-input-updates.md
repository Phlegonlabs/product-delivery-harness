# Design Input Updates

Use this reference when the user provides a new or updated PRD, wireframe, design system, screenshot, Figma/page UI reference, or page-specific UI target for either a new build or an existing app refinement.

## Core Rule

Treat design and product inputs as versioned contract sources, not informal inspiration. When the design source is a `ui-architecture-builder` package, `ui-architecture.md`, `ui-registry.json`, and `page-recipes.md` are binding alongside `design-system.md`, and implementation works from the registry plus the route's recipe — see `SKILL.md`'s UI Implementation Contract.

```text
1. Identify source type and version.
2. Compare updated input against the current contract, baseline app, or previous assumptions.
3. Record the delta and affected pages/components/API/data surfaces.
4. Resolve conflicts before implementation.
5. Freeze the accepted delta.
6. Implement only the accepted delta.
7. Verify conformance and regression.
```

## Input Types

```text
Updated PRD: changed workflows, scope, roles, data, success criteria, non-goals
Updated Builder UX Direction: changed experience priority, guidance/control, density, interaction/layout, confirmation/recovery, validation depth, decision owner, or decision status
Updated wireframe: screen structure, navigation, page regions, component hierarchy, state coverage
Updated design system: tokens, typography, spacing, radius, color, component variants, interaction states
Updated UI architecture: layer model, source-of-truth precedence, content contracts, primitive contracts, product components, motion architecture, state matrix, guardrails, definition of done, adoption sequence
Updated UI registry: added/removed primitives, changed closed variant sets, motion variants, product components, page recipes
Updated page recipe: section order, container, density, allowed surfaces, forbidden patterns, required states, route → mockup → trace → test index
Page UI reference: screenshot, Figma frame, mockup, handoff spec, per-page layout target
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
- Page UI references must map to routes/screens and responsive breakpoints.
- Design-system deltas must map to affected components and variants.
- A registry delta must name every route whose recipe uses the changed entry, and a recipe delta must name the primitives, components, and motion variants the new recipe needs. A delta that removes a registry entry must state what replaces it at each call site; an entry that disappears from `ui-registry.json` while a route still uses it is a break, not a cleanup.
- `ui-registry.json` and `page-recipes.md` are binding sources, so a registry or recipe delta is a contract change and must be frozen before implementation like any other. A code-side "we already built it this way" is not an accepted delta.
- PRD deltas that change data/API/auth/permissions must trigger architecture and E2E updates.
- Builder UX Direction deltas must preserve their human owner and selected/provisional/assumed status, map to affected `UX-*`, `UI-*`, and `DS-*` traces, and name any required prototype or usability revalidation.

## Page UI Matrix

Use this when the user provides different UI references for different pages. When the design source is a `ui-architecture-builder` package, `page-recipes.md` already carries this mapping — read it there instead of rebuilding the table.

```text
| Page / route | UI source | Breakpoints | States | Components | Data source | Acceptance evidence |
|---|---|---|---|---|---|---|
| /dashboard | Figma frame <id> | mobile/tablet/desktop | loading/empty/error/ready | cards/table/filter | API-002 | screenshot + journey |
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

When the design source is a `ui-architecture-builder` package, the state matrix in `ui-architecture.md` is the authority for this list, and each route's recipe says which of those states that route must support. Mark an inapplicable state `n/a` explicitly rather than omitting it.

## New Build Flow

For a new build with provided PRD, wireframe, design system, and page UI references:

```text
M1 source intake and conflict resolution
M2 contract freeze and traceability
M3 foundation/data/API if needed
M4 tokens, primitives, ui-registry.json, mockups/catalog.html, and the UI contract check
M5 product components
M6 route implementation from ui-registry.json + each route's recipe
M7 E2E and visual evidence
```

M4 through M6 follow `execution-task-decomposition.md`'s UI Build Order: tokens and primitives before components, components before routes, the registry and catalog landing with the primitives, and the contract check landing with the first routes rather than at the end.

M6 and M7 above are illustrative single lines, not a mandate to implement every route in one mission and defer visual evidence to the end. Per `contract-and-traceability.md`'s mission-granularity corollary, split M6 into one mission per page (or a small tightly-coupled group) and pair each with its own scoped `visual` review as soon as that mission integrates, rather than one M6 covering every route reviewed once by a later M7.

## Existing App Refinement Flow

For an existing app with updated PRD/wireframe/design system/page UI:

```text
M1 baseline current app and source map
M2 delta audit: old behavior vs updated input
M3 accepted delta implementation
M4 before/after conformance evidence
M5 regression checks for preserved behavior
```

Use before/after captures for UI changes. The "before" side proves the current state; the "after" side proves the accepted delta was implemented without broad rewrite.

## Conflict Handling

Stop and ask when:

- Updated PRD conflicts with updated wireframe.
- Builder UX Direction conflicts with observed user needs, accessibility, product requirements, or platform conventions and no validation decision resolves the conflict.
- Updated design system conflicts with page UI mockups.
- Page UI reference omits required states or breakpoints.
- An in-scope route has no recipe, or a recipe needs a primitive, variant, component, or motion variant that `ui-registry.json` does not list. Ask for the missing recipe or registry entry instead of improvising the route or passing a raw value at the call site.
- The updated input can only be implemented by leaving the registry or a recipe — for example a spacing value no token carries, or a control the primitives do not cover. The fix is a delta on the primitive, token, or recipe, decided once by the design source, not a page-local exception.
- Updated input would remove existing app behavior without explicit acceptance.
- The source version is unclear and multiple variants exist.
- A pixel/design-faithful claim is requested but the source is unavailable.

## Verification

Design-input verification should include:

- Trace coverage: every accepted delta has implementation and evidence.
- Visual conformance: page/component matches accepted UI source within stated tolerance.
- State coverage: required states and breakpoints are checked.
- Behavior conformance: PRD workflow and data/API behavior still pass.
- Design-system conformance: tokens/components/variants follow the updated system.
- Contract conformance: the implementation uses only entries `ui-registry.json` lists, follows each touched route's recipe, and contains no raw visual value, page-local control, inline layout style, or unregistered motion. Run the project's UI contract check — this skill's `scripts/check_ui_contract.py` covers the source-scanning subset, against the product's real source rather than the package's mockups — plus the visual check across the responsive verification set the package's `ui-registry.json` carries — its `viewports` for a web target or its `sizeClasses` for a native or desktop target — in normal and reduced motion. A drift from the registry or a recipe is a contract violation, not a stylistic difference; a passing functional test does not cover it. See `SKILL.md`'s UI Implementation Contract for what each implementation mission owes.
- Builder direction conformance: selected choices are reflected and provisional/assumed choices remain explicit; this proves direction conformance, not usability.
- Usability evidence: when required, representative users or an approved equivalent complete the named task against the specified prototype or implementation; agent preference, screenshots, and automated E2E do not substitute for that evidence.
- Regression: preserved routes, permissions, data behavior, content, analytics, and E2E journeys still pass.

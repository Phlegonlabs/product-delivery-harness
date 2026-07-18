# Design Input Updates

Use this reference when the user provides a new or updated PRD, wireframe, design system, screenshot, Figma/page UI reference, or page-specific UI target for either a new build or an existing app refinement.

## Core Rule

Treat design and product inputs as versioned contract sources, not informal inspiration.

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
- PRD deltas that change data/API/auth/permissions must trigger architecture and E2E updates.
- Builder UX Direction deltas must preserve their human owner and selected/provisional/assumed status, map to affected `UX-*`, `UI-*`, and `DS-*` traces, and name any required prototype or usability revalidation.

## Page UI Matrix

Use this when the user provides different UI references for different pages:

```text
| Page / route | UI source | Breakpoints | States | Components | Data source | Acceptance evidence |
|---|---|---|---|---|---|---|
| /dashboard | Figma frame <id> | mobile/tablet/desktop | loading/empty/error/ready | cards/table/filter | API-002 | screenshot + journey |
```

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

## New Build Flow

For a new build with provided PRD, wireframe, design system, and page UI references:

```text
M1 source intake and conflict resolution
M2 contract freeze and traceability
M3 foundation/data/API if needed
M4 page/component implementation by UI matrix
M5 design-system conformance and responsive states
M6 E2E and visual evidence
```

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
- Builder direction conformance: selected choices are reflected and provisional/assumed choices remain explicit; this proves direction conformance, not usability.
- Usability evidence: when required, representative users or an approved equivalent complete the named task against the specified prototype or implementation; agent preference, screenshots, and automated E2E do not substitute for that evidence.
- Regression: preserved routes, permissions, data behavior, content, analytics, and E2E journeys still pass.

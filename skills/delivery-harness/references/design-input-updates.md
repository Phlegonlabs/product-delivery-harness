# Design Input Updates

Use this reference when the user provides a new or updated PRD, approved HTML wireframe, design system, design inspiration, or explicit page-faithful target for either a new build or an existing app refinement.

## Core Rule

Classify every visual source before planning or implementation:

- **Design inspiration** is non-canonical evidence. It can influence implementation only after the PRD UI Design Pass inspects it and the human owner approves the resulting scoped target or principles. When the Design System Need Gate is `required`, `design-system-compiler` also compiles those approved consequences into the pair. A URL, screenshot, Figma frame, or market-research source is not implementation authority merely because it exists.
- **Page-faithful target** is an explicit user requirement for visual conformance. Treat it as binding only after the user requests faithful matching and the readable source version, recorded routes, states, responsive scope, and acceptance tolerance are frozen. Preserve it as version-bound acceptance evidence; do not broaden it beyond the routes named in the handoff. The default UI Design Pass retains one connected all-screens HTML implementation reference under `docs/design/ui-references/<run-id>/`; superseded versions archive under `docs/design/archived/`. The harness reads either only through the PRD UI Design Handoff record, never by folder discovery.

Implementation always works from the route's `UI-*` entry in `PRD.md`, its approved interactive page in `wireframes.html`, and the active visual route in the UI Design Handoff. A `required` gate binds `design-system.md` and `design-system.json` together. A `not_required` gate binds the approved immutable page-faithful target instead. See `ui-implementation-contract.md`.

A `frontend-design` result produced or requested during implementation is a proposed design-input delta, not code-side authority. Do not apply a new visual direction, token, variant, component, motion pattern, or structure directly. Return target or direction changes to `product-definition-builder`; return formal pair changes to `design-system-compiler`. Resume only against the revised active source.

```text
1. Identify source type and version.
2. Compare updated input against the current contract, baseline app, or previous assumptions.
3. Record the delta and affected pages/components/API/data surfaces.
4. Resolve conflicts before implementation.
5. Freeze the accepted delta.
6. Implement only the accepted delta.
7. Verify conformance and regression.
```

**What "freeze" records.** Freezing is a manifest entry, not just a decision. Record the accepted delta on the affected source in the HARNESS_PLAN manifest: for a PLAN-v6 source, set `staged_revision` to the accepted revision. The source status moves to `frozen` or `delta_accepted`, and the binding fields (`location`, `content_sha256`, `source_revision`) update only once that revision is published to the canonical source location — then the PLAN revision and digest change too. A `staged_revision` alone is not an executable publication; a ready or executing RUN never points at a product staging path. See the HARNESS_PLAN template's source map for these fields.

## Input Types

```text
Updated PRD: changed workflows, scope, roles, data, success criteria, non-goals
Updated Builder UX Direction: changed experience priority, guidance/control, density, interaction/layout, confirmation/recovery, validation depth, decision owner, or decision status
Updated PRD UI surface contract: screen structure, navigation, page regions, content responsibilities, actions, and state coverage
Updated approved wireframe: `wireframes.html` covering region order, grouping, element inventory, state placement, section labels, page switching, and responsive rearrangement tied to `UI-*`, with approval recorded in `PRD.md`
Updated design system: tokens, typography, spacing, radius, color, added/removed primitives, changed closed variant sets, interaction states, motion variants, product components, content contracts, state matrix, responsive set
Design inspiration: screenshot, image, Figma frame, website, named product, or visual reference used only for confirmed design principles
Page-faithful target: version-bound screenshot, Figma frame, mockup, handoff spec, or page target the user explicitly requires the implementation to match
Existing app baseline: current route behavior, screenshots, traces, metrics, source implementation
```

## Repository Design Reference Discovery

During `System Review And Route` for UI-bearing work, recursively inspect the repository's conventional `docs/design/` folder when it exists and any other design folder the user explicitly names. Also include an obvious design image encountered during the normal bounded scope scan. Do not start a broad repository-wide image crawl when those locations are absent.

Treat readable `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.avif`, and `.svg` files in those locations as candidate design inspiration. For each candidate:

1. Record the exact repository-relative path and SHA-256 content hash in the parent checkpoint or plan intake notes.
2. Open and inspect the source before claiming any visible mechanic. Mark unreadable or ambiguous files as blocked instead of inferring their contents.
3. Classify it as design inspiration unless the user separately and explicitly requests page-faithful matching for a named route, state set, responsive scope, source version, and tolerance.
4. Route it to the PRD UI Design Pass for inspection and owner confirmation. Only the accepted, frozen consequences in the UI Design Handoff may shape implementation; a required formal pair is compiled afterward.

Do not treat general assets, logos, README covers, test snapshots, `docs/goal/evidence/`, dependency caches, generated output, or build artifacts as design references merely because they are images. Include one only when the user identifies it as a design source or its in-scope design purpose is explicit. Keep discovered files in place; do not copy, move, rename, or publish them into the product package. No discovered image is code-side authority, and the absence of `docs/design/` is not a blocker.

## Delta Record

Every accepted change should be captured as a delta row:

```text
| Delta ID | Source | Change | Affected surfaces | Supersedes | Acceptance / verifier | Status |
|---|---|---|---|---|---|---|
| DELTA-001 | updated PRD UI surface | <change> | UI-003, DS-002 | <old assumption> | <gate> | accepted |
```

Rules:

- A delta can add, modify, or explicitly remove behavior.
- Superseded requirements must be recorded; do not silently drop existing behavior.
- A UI delta that changes visual values must record the styles, classes, and values it supersedes and name every call site where the implementation removes them. Carrying a superseded style into the accepted delta's implementation is a contract violation, not a compatibility nicety.
- A backend or app delta must record the endpoints, business rules, queries, migrations, flags, jobs, and configuration it supersedes and name every call site where the implementation removes them — or record an explicit owner-accepted reason when a superseded surface is retained for compatibility. Silently carrying a superseded endpoint, rule, or flag forward alongside its replacement is a contract violation.
- Design inspiration must return to the PRD UI Design Pass; only accepted, frozen consequences in the UI Design Handoff may enter implementation.
- Page-faithful targets must map to routes/screens, states, responsive breakpoints, source version, and acceptance tolerance.
- Design-system deltas must map to affected components and variants.
- A design-system delta must name every route that uses the changed entry. A delta that removes an entry must state what replaces it at each call site; an entry that disappears from `design-system.json` while a route still uses it is a break, not a cleanup.
- When the gate is `required`, `design-system.md` and `design-system.json` are binding sources, so a design-system delta must be frozen before implementation. When it is `not_required`, a target change returns to the PRD UI Design Handoff and its human approval gate. A code-side "we already built it this way" is not an accepted delta.
- PRD deltas that change data/API/auth/permissions must trigger architecture and E2E updates.
- Wireframe deltas return to `product-definition-builder`, require renewed human-owner approval, and invalidate downstream visual-direction selection until reconciled.
- Builder UX Direction deltas must preserve their human owner and selected/provisional/assumed status, map to affected `UX-*`, `UI-*`, and `DS-*` traces, and name any required prototype or usability revalidation.

## Page-Faithful Target Matrix

Use this only when the user explicitly provides page-faithful targets for different pages. Design inspiration never enters this matrix. When `PRD.md` already carries the accepted page mapping, read it there instead of rebuilding the table.

```text
| Page / route | UI source | Source version / hash | Breakpoints | States | Tolerance / allowed deviations | Components | Data source | Acceptance evidence |
|---|---|---|---|---|---|---|---|---|
| /dashboard | Figma frame <id> | <version or content hash> | mobile/tablet/desktop | loading/empty/error/ready | <named tolerance and allowed deviations> | cards/table/filter | API-002 | screenshot + journey |
```

For a required UI surface, `screenshot + journey` means a retained screenshot for every listed breakpoint-by-state combination, plus journey/console/network evidence where applicable. In RUN-v11, read the artifact bytes from the recorded accepted Git commit/ref, safely decode those bytes, then compare `artifact_sha256`; record the screenshot path, hash, and integration head in current RUN state. Uncommitted or mutated working-tree screenshots cannot satisfy v10. Older RUN-v9 UI evidence remains readable and keeps its working-tree binding.

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

When the product has a required design system, `design-system.json`'s `stateMatrix` is the authority for this list. In target-conformance mode, the PRD UI surface and approved target scope are the authority. Mark an inapplicable state `<state>:n/a` explicitly rather than omitting it.

## New Build Flow

For a new build with a provided PRD, approved UI Design Handoff, and optional required design system:

```text
M1 source intake and conflict resolution
M2 contract freeze and traceability
M3 foundation/data/API if needed
M4 required pair: tokens, primitives, and the UI contract check; not_required: target-conformance foundation
M5 required pair: product components; not_required: shared style source only when the scoped UI needs it
M6 route implementation from the active visual source + each route's PRD UI surface entry + approved wireframe
M7 E2E and visual evidence
```

In system-conformance mode, M4 through M6 follow `execution-task-decomposition.md`'s UI Build Order: tokens and primitives before components, components before routes, the registry and catalog landing with the primitives, and the contract check landing with the first routes rather than at the end. Target-conformance mode does not create placeholder registry or catalog work.

M6 and M7 above are illustrative single lines, not a mandate to implement every route in one mission and defer visual evidence to the end. Per `contract-and-traceability.md`'s mission-granularity corollary, split M6 into one mission per page (or a small tightly-coupled group) and pair each with its own scoped `visual` review as soon as that mission integrates, rather than one M6 covering every route reviewed once by a later M7.

## Existing App Refinement Flow

For an existing app with an updated PRD, design system, or page-faithful target:

```text
M1 baseline current app and source map
M2 delta audit: old behavior vs updated input
M3 accepted delta implementation, including removal of superseded styles, endpoints, rules, and flags
M4 before/after conformance evidence plus the stale-carryover check
M5 regression checks for preserved behavior
```

Use before/after captures for UI changes. The "before" side proves the current state; the "after" side proves the accepted delta was implemented without broad rewrite.

The stale-carryover check is the after-side companion: an affected surface's after state must not show any visual element, style, or class the previous version had that the accepted delta supersedes. Old-version remnants surviving into the new version are a failed delta, whether they come from a production stylesheet that was never cleaned or from a reference file that accumulated superseded CSS.

The same check covers backend and app surfaces: the after state must not route to a removed endpoint, apply a superseded business rule, read a retired flag or config key, or keep a superseded query or job running. An enhancement that leaves the old path in place beside the new one has not finished; superseded behavior survives only where the accepted delta explicitly records a compatibility retention.

This flow is primary whenever an updated input exists. When no updated PRD, design system, or page UI reference exists — an open-ended "make it better", where an audit has to establish the work in the first place — use the Open-Ended Refinement section below instead. When both conditions hold, run this flow and fold that section into it. Do not run two mission sets:

- Its baseline-evidence lenses supply what M1 captures.
- Its backlog rows and ranking rules supply how M2 records what it finds.
- A finding the audit turns up that is not part of the accepted delta stays a backlog row. It needs the user's acceptance and its own mission; it does not ride along in M3.
- Its regression-protection checklist and stop-and-ask conditions apply to M5 unchanged.

## Conflict Handling

Stop and ask when:

- Updated PRD UI surface entries or wireframes conflict with other updated product requirements.
- Builder UX Direction conflicts with observed user needs, accessibility, product requirements, or platform conventions and no validation decision resolves the conflict.
- An updated required design system conflicts with the approved page-faithful target.
- A page-faithful target omits required states, breakpoints, source version, or tolerance.
- A design inspiration source is being treated as code-side authority without an accepted, frozen PRD UI Design Handoff update.
- An in-scope route has no PRD UI surface entry, approved wireframe, or active visual source. In system-conformance mode, ask for an absent registry entry. In target-conformance mode, ask for missing target scope, state, responsive coverage, or tolerance. Do not improvise.
- A required design-system route can only be implemented by leaving the pair. The fix is a formal delta, not a page-local exception. A target-conformance route that needs a broader system returns to the Design System Need Gate instead of growing one silently.
- A conformance-mode `frontend-design` pass proposes a value, variant, component, motion pattern, or page structure the frozen active source does not contain. Record it as a delta and stop; do not treat skill output as implicit approval.
- Updated input would remove existing app behavior without explicit acceptance.
- The source version is unclear and multiple variants exist.
- A pixel/design-faithful claim is requested but the source is unavailable.

## Verification

Design-input verification should include:

- Trace coverage: every accepted delta has implementation and evidence.
- Stale-carryover: affected surfaces show no superseded style, class, or previous-version element, and the implementation's style sources no longer contain styles the updated reference removed. Backend and app surfaces route no superseded endpoint, rule, flag, query, or job, unless the delta records an explicit compatibility retention.
- Visual conformance: when a page-faithful target exists, the page/component matches its frozen source, scope, and tolerance; inspiration alone creates no pixel-faithful claim.
- State coverage: required states and breakpoints are checked.
- Behavior conformance: PRD workflow and data/API behavior still pass.
- Design-system conformance: in system-conformance mode, tokens/components/variants follow the updated pair. In target-conformance mode, do not claim this gate.
- Contract conformance: system-conformance implementation uses only entries `design-system.json` lists and runs the UI contract check; target-conformance implementation uses the smallest shared style source needed and runs page-to-target comparison at the recorded tolerance. Both follow the PRD and approved wireframe across the active responsive set in normal and reduced motion. Drift from the active source is a contract violation, not a stylistic difference.
- Builder direction conformance: selected choices are reflected and provisional/assumed choices remain explicit; this proves direction conformance, not usability.
- Usability evidence: when required, representative users or an approved equivalent complete the named task against the specified prototype or implementation; agent preference, screenshots, and automated E2E do not substitute for that evidence.
- Regression: preserved routes, permissions, data behavior, content, analytics, and E2E journeys still pass.

## Open-Ended Refinement

Use this section when the user has an already-developed app, site, dashboard, SaaS product, or prototype and wants refinement, polish, optimization, cleanup, or evidence-backed improvement with no updated design or product input to conform to.

### Refinement Rule

Do not start by rewriting. Start by proving the current state.

```text
1. Identify the app archetype and target surfaces.
2. Capture a baseline from the running or buildable app.
3. Rank concrete issues by user impact, confidence, effort, and regression risk.
4. Convert accepted candidates into small missions.
5. Implement one improvement at a time.
6. Verify before/after evidence and run regression checks.
```

### Intake Fields

```text
Refinement target: UX | visual polish | performance | accessibility | SEO | conversion | reliability | test coverage | code quality
Current state: deployed URL | local app route | screenshots | failing checks | user complaints | analytics | known TODOs
Baseline command:
Primary journey:
Must preserve:
Out of scope:
Acceptance threshold:
```

If the user says "make it better" without a target, perform a refinement audit first and record a ranked backlog in `RUN.md`. Do not create a separate backlog file unless the list becomes materially difficult to scan; then expand it from `assets/templates/REFINEMENT_BACKLOG.template.md` and link it from `RUN.md`. Do not implement the backlog until the user accepts candidates or authorizes defaults.

### Baseline Evidence

Capture only evidence that matches the requested lens:

```text
UX: journey friction, navigation dead ends, form errors, empty/error/loading states, task completion
Visual polish: layout consistency, spacing, typography, overflow, responsive behavior, design-system drift
Performance: build size, Lighthouse/Core Web Vitals, slow routes, API latency, expensive queries
Accessibility: keyboard, focus, labels, landmarks, contrast, heading order, alt text, form errors
SEO/content: metadata, canonical, sitemap, structured data, internal links, content completeness
Conversion: CTA visibility, form completion, event tracking, thank-you/confirmation states
Reliability: console/network errors, failed requests, flaky tests, error boundaries, retries
Test coverage: missing tests around changed behavior, weak E2E journeys, unverified permissions
Code quality: duplication, unclear ownership, brittle state, dead code, overly broad components
```

Evidence can be command output, screenshots, traces, console logs, metrics, file references, or a rendered-page observation. When PLAN marks UI evidence required, retain a real screenshot for every planned breakpoint and state; the other evidence types are supplemental. Mark unverifiable surfaces as `UNVALIDATED`.

### Refinement Backlog Rows

Each candidate must be concrete:

```text
| ID | Lens | Finding | Evidence | Impact | Effort | Risk | Proposed verifier | Status |
|---|---|---|---|---|---|---|---|---|
| REF-001 | performance | <finding> | <metric/path> | high | M | medium | <cmd/threshold> | proposed |
```

Ranking rules:

- Prefer issues with direct user impact and deterministic verification.
- Prefer small improvements that preserve existing information architecture and contracts.
- Do not hide product rewrites inside "polish".
- Separate bug fixes from visual opinion changes.
- Treat design-system drift as a contract issue when a design system exists.

### Mission Patterns

Use this pattern when refinement starts from an audit — the user wants the app improved but supplied no updated PRD, design system, or page UI reference. When an updated input did arrive, `design-input-updates.md`'s "Existing App Refinement Flow" is primary instead.

Use one mission per accepted refinement theme:

```text
M1 baseline and backlog
M2 targeted UX/visual refinement
M3 performance or accessibility pass
M4 platform-specific refinement, such as SaaS auth/tenant or public-site SEO
M5 regression verification
```

For small accepted refinements, skip worktrees and run direct work with before/after evidence. Use worktrees when several accepted refinements can run independently or when the parent checkout must remain stable.

### Regression Protection

Before closeout, verify:

- The original primary journey still passes.
- The accepted metric or visual state improved or is explicitly accepted.
- Existing app contracts, routes, permissions, content, and data behavior did not regress.
- Screenshots/traces compare before and after for UI changes.
- Performance/accessibility/SEO changes include a threshold or artifact.
- Any skipped checks are recorded with risk.

### Stop And Ask Conditions

Stop before implementation when:

- The requested refinement implies a product redesign or information-architecture change.
- The app cannot build or run and no baseline can be captured.
- The only available evidence is subjective preference with no design source or user goal.
- A change would remove existing behavior, content, routes, analytics, permissions, or data.
- The requested change has no safe local verification path.

# Design Input Updates

Use this reference when the user provides a new or updated PRD, approved HiFi, design system, design inspiration, or explicit page-faithful target for a new build or an existing app refinement.

## Design And Maintenance Routing

First classify this round under [Product Contracts](governance/product-contracts.md#consumer-keep-product-contracts-current); initial design, enhancements and an explicit full redesign use the design gates below.

## Core Rule

Classify every visual source before planning or implementation:

- **Design inspiration** is non-canonical evidence. It can influence implementation only after `ui-design-builder` inspects it and the human owner approves the resulting scoped target or principles; when the Design System Need Gate is `required`, `design-system-compiler` then compiles those consequences into the pair. A URL, screenshot, Figma frame, or market-research source is not authority by itself.
- **Page-faithful target** is an explicit user requirement for visual conformance. It binds only after the user requests faithful matching and the readable source version, routes, states, responsive scope, and tolerance are frozen; keep it as version-bound evidence and do not broaden it beyond `ui-design.md`. UI Design Builder retains one connected all-screens HTML reference under `docs/design/ui-references/<run-id>/` and archives superseded versions under `docs/design/archived/`. Harness reads it only through the approved UI design contract, never by folder discovery.

For a new initial delivery or design enhancement, implementation uses the route's `UI-*` entry in `PRD.md`, current approved `ui-design.md`, the route's approved HiFi page with its embedded `ui-hifi-copy/1` copy (`ui-design/3`; a retained `ui-design/2` contract uses `ui-design/2`; a pinned wireframe contract follows [legacy pins](legacy/legacy-pins.md#legacy-ui-contracts-before-059)), and the active visual route. Static strings, action labels, feedback, and alternate-state messages are implementation-bound; dynamic examples are illustrative while their approved source/order/format/count/length/fallback contracts bind implementation. A `required` gate binds `design-system.md` and `design-system.json` together; `design-system/4` also binds its frozen derived HTML. A `not_required` gate binds the approved immutable page-faithful target instead. See `ui-implementation-contract.md`.

A `frontend-design` result produced or requested during implementation is a proposed design-input delta, not code-side authority. Do not apply a new visual direction, token, variant, component, motion pattern, or structure directly. Return target, direction or HiFi changes to `ui-design-builder`; return product behavior, copy/display contracts or stack changes to `product-definition-builder`; return formal pair changes to `design-system-compiler`. Resume only against the revised active source.

```text
1. Identify source type and version.
2. Compare updated input against the current contract, baseline app, or previous assumptions.
3. Record the delta and affected pages/components/API/data surfaces.
4. Resolve conflicts before implementation.
5. Freeze the accepted delta.
6. Implement only the accepted delta.
7. Verify conformance and regression.
```

**What "freeze" records.** Freezing is a manifest entry, not just a decision: record the accepted delta on the affected source in the HARNESS_PLAN manifest and, for a PLAN-v6 source, set `staged_revision` to the accepted revision. The source status moves to `frozen` or `delta_accepted`. The binding fields (`location`, `content_sha256`, `source_revision`) update only once that revision is published to the canonical source location, which also changes the PLAN revision and digest. A `staged_revision` alone is not an executable publication; a ready or executing RUN never points at a product staging path. See the HARNESS_PLAN template's source map.

## Input Types

```text
Updated PRD: changed workflows, scope, roles, data, success criteria, non-goals
Updated UI Design Intake: changed experience priority, guidance/control, density, interaction/layout, style, motion/media, references, validation depth, decision owner, or decision status
Updated PRD UI surface contract: screen structure, navigation, page regions, content responsibilities, actions, state coverage, and per-screen copy status
Updated approved HiFi: `ui-hifi/2` pages and the embedded `ui-hifi-copy/1` record, with HiFi Review and Visual Approval recorded in `ui-design.md`
Updated design system: tokens, typography, spacing, radius, color, added/removed primitives, changed closed variant sets, interaction states, motion variants, product components, content contracts, state matrix, responsive set
Design inspiration: screenshot, image, Figma frame, website, named product, or visual reference used only for confirmed design principles
Page-faithful target: version-bound screenshot, Figma frame, mockup, handoff spec, or page target the user explicitly requires the implementation to match
Existing app baseline: current route behavior, screenshots, traces, metrics, source implementation
```

## Repository Design Reference Discovery

During `System Review And Route` for UI-bearing work, recursively inspect the conventional `docs/design/` folder when it exists, any design folder the user explicitly names, and any obvious design image met in the normal bounded scope scan; do not start a broad repository-wide image crawl when those locations are absent.

Treat readable `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`, `.avif`, and `.svg` files in those locations as candidate design inspiration. For each candidate:

1. Record the exact repository-relative path and SHA-256 content hash in the parent checkpoint or plan intake notes.
2. Open and inspect the source before claiming any visible mechanic. Mark unreadable or ambiguous files as blocked; do not infer their contents.
3. Classify it as design inspiration unless the user separately and explicitly requests page-faithful matching for a named route, state set, responsive scope, source version, and tolerance.
4. Route it to `ui-design-builder` for inspection and owner confirmation; only accepted, frozen consequences in `ui-design.md` may shape implementation.

Do not treat general assets, logos, README covers, test snapshots, `docs/goal/evidence/`, dependency caches, generated output, or build artifacts as design references merely because they are images; include one only when the user identifies it as a design source or its in-scope design purpose is explicit. Keep discovered files in place; do not copy, move, rename, or publish them into the product package. The absence of `docs/design/` is not a blocker.

## Delta Record

For UI enhancements, apply `../../ui-design-builder/references/enhancement-recommendations.md`'s Incremental UI Scope: record added, changed and preserved pages before authoring or implementation, put necessary entry links and shared consumers in the named delta, and preserve unrelated product DOM, copy, layout, style and behavior.

Capture every accepted change as a delta row:

```text
| Delta ID | Source | Change | Affected surfaces | Supersedes | Acceptance / verifier | Status |
|---|---|---|---|---|---|---|
| DELTA-001 | updated PRD UI surface | <change> | UI-003, DS-002 | <old assumption> | <gate> | accepted |
```

Rules:

- A delta can add, modify, or explicitly remove behavior. Record superseded requirements; do not silently drop existing behavior.
- A UI delta that changes visual values must record the styles, classes, and values it supersedes and name every call site where the implementation removes them. Carrying a superseded style into the accepted delta's implementation is a contract violation.
- A user-visible wording or dynamic display-contract change is a `structure` copy delta. Update the affected PRD `` `copy` `` anchors. In an active initial design or enhancement, return the affected `ui-hifi-copy/1` items and surface `copyStatus` to draft, re-check reflow across every affected responsive target and state, and renew Product Definition Approval, the full HiFi copy review and affected Visual Approval before implementation. In routine maintenance, update effective requirements and the product with focused verification; do not regenerate historical design artifacts solely to match an accepted change.
- A backend or app delta must record the endpoints, business rules, queries, migrations, flags, jobs, and configuration it supersedes and name every call site where the implementation removes them, or record an explicit owner-accepted reason when a superseded surface is retained for compatibility.
- Design-system deltas must map to affected components and variants and name every route that uses the changed entry. A delta that removes an entry must state what replaces it at each call site; an entry that disappears from `design-system.json` while a route still uses it is a break, not a cleanup.
- When the gate is `required`, `design-system.md` and `design-system.json` are binding sources, so a design-system delta must be frozen before implementation. For `design-system/4`, regenerate and freeze the derived HTML from the accepted pair and bound sources. When it is `not_required`, a target change returns to `ui-design-builder` and Human Visual Approval. A code-side "we already built it this way" is not an accepted delta.
- PRD deltas that change data/API/auth/permissions must trigger architecture and E2E updates.
- In active initial design or enhancement, new product behavior, wording, and dynamic display-contract decisions return to `product-definition-builder`; copy completeness, style, motion/media, and HiFi-target deltas return to `ui-design-builder`. Renew the applicable decisions and checks on the affected scope. Routine maintenance follows the accepted current product and effective requirements without rewriting historical visual approvals.
- A legacy two-target web responsive set follows [legacy pins](legacy/legacy-pins.md#legacy-ui-contracts-before-059) before its package is next edited or re-validated.
- UI Design Intake deltas preserve their human owner, map to affected `UX-*`, `UI-*`, `MM-*`, and `DS-*` traces, and name any required prototype or usability revalidation.

## Page-Faithful Target Matrix

Use this only when the user explicitly provides page-faithful targets for different pages. Design inspiration never enters this matrix. When `PRD.md` already carries the accepted page mapping, read it there instead of rebuilding the table.

```text
| Page / route | UI source | Source version / hash | Breakpoints | States | Tolerance / allowed deviations | Components | Data source | Acceptance evidence |
|---|---|---|---|---|---|---|---|---|
| /dashboard | Figma frame <id> | <version or content hash> | mobile/tablet/desktop | loading/empty/error/ready | <named tolerance and allowed deviations> | cards/table/filter | API-002 | screenshot + journey |
```

For a required UI surface, `screenshot + journey` means a retained screenshot for every listed breakpoint-by-state combination, plus journey/console/network evidence where applicable. In RUN-v10 and RUN-v11, read the artifact bytes from the recorded accepted Git commit/ref, safely decode them, then compare `artifact_sha256`; record the screenshot path, hash, and integration head in current RUN state. Uncommitted or mutated working-tree screenshots cannot satisfy v10 or v11.

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

When the product has a required design system, `design-system.json`'s `stateMatrix` is the authority for this list; in target-conformance mode, the PRD UI surface and approved target scope are. Keep PLAN `states` as product states. Use optional `design_coverage` to account for remaining global states with one condition or a reasoned exclusion.

## New Build Flow

For a new initial or full-redesign build with an approved Product Definition, `ui-design.md` (`ui-design/3`), the complete approved HiFi package, and the required `design-system/4` package with frozen derived HTML. A retained `ui-design/2` build uses its original conditional `design-system/3` contract:

```text
M1 source intake and conflict resolution
M2 contract freeze and traceability
M3 foundation/data/API if needed
M4 required pair: tokens, primitives, and the UI contract check; retained UI2 not_required: target-conformance foundation
M5 required pair: product components; for `design-system/4`, source-bound showcase and frozen derived HTML; retained UI2 not_required: shared style source only when the scoped UI needs it
M6 route implementation from the active visual source + each route's PRD UI surface entry + its approved HiFi surface (retained UI2: original rules)
M7 E2E and visual evidence
```

In system-conformance mode, M4 through M6 follow `execution-task-decomposition.md`'s UI Build Order: tokens and primitives before components, components before routes, the registry and catalog landing with the primitives, and the contract check landing with the first routes. Target-conformance mode does not create placeholder registry or catalog work.

M6 and M7 are illustrative single lines, not a mandate to implement every route in one mission and defer visual evidence to the end. Per `contract-and-traceability.md`'s Review Placement Defaults, split M6 into one mission per feature batch. The one final review carries the visual lens; per-mission visual reviews exist only under `per_mission`.

## Existing App Refinement Flow

For an existing app with an updated PRD, design system, or page-faithful target:

```text
M1 baseline current app and source map
M2 delta audit: old behavior vs updated input
M3 accepted delta implementation, including removal of superseded styles, endpoints, rules, and flags
M4 before/after conformance evidence plus the stale-carryover check
M5 regression checks for preserved behavior
```

Use before/after captures for UI changes: "before" proves the current state, "after" proves the accepted delta was implemented without broad rewrite.

The stale-carryover check is the after-side companion: an affected surface's after state must not show any visual element, style, or class the previous version had that the accepted delta supersedes; such a remnant is a failed delta, whether from an uncleaned production stylesheet or a reference file that accumulated superseded CSS. It also covers backend and app surfaces: no route to a removed endpoint, no superseded business rule, no retired flag or config key, no superseded query or job still running. An enhancement that leaves the old path beside the new one has not finished; superseded behavior survives only where the accepted delta explicitly records a compatibility retention.

This flow is primary whenever an updated input exists. When no updated PRD, design system, or page UI reference exists — an open-ended "make it better" — use [Open-Ended Refinement](open-ended-refinement.md) instead. When both conditions hold, run this flow and fold that reference into it, not two mission sets:

- Its baseline-evidence lenses supply what M1 captures.
- Its backlog rows and ranking rules supply how M2 records what it finds.
- A finding outside the accepted delta stays a backlog row that needs the user's acceptance and its own mission; it does not ride along in M3.
- Its regression-protection checklist and stop-and-ask conditions apply to M5 unchanged.

## Conflict Handling

Stop and ask when:

- Updated PRD UI surface entries or HiFi pages conflict with other updated product requirements.
- UI Design Intake conflicts with observed user needs, accessibility, product requirements, or platform conventions and no validation decision resolves the conflict.
- An updated required design system conflicts with the approved page-faithful target.
- A page-faithful target omits required states, breakpoints, source version, or tolerance.
- A design inspiration source is being treated as code-side authority without an accepted, frozen `ui-design.md` update.
- In initial design or enhancement, an in-scope route has no PRD UI surface entry, approved HiFi surface, or active visual source: in system-conformance mode ask for an absent registry entry, in target-conformance mode for missing target scope, state, responsive coverage, or tolerance. Routine maintenance still requires current PRD/PLAN route, state and target coverage.
- A required design-system route can only be implemented by leaving the pair; the fix is a formal delta, not a page-local exception. A target-conformance route that needs a broader system returns to the Design System Need Gate instead of growing one silently.
- A conformance-mode `frontend-design` pass proposes a value, variant, component, motion pattern, or page structure the frozen active source lacks: record a delta and stop.
- Updated input would remove existing app behavior without explicit acceptance.
- The source version is unclear and multiple variants exist.
- A pixel/design-faithful claim is requested but the source is unavailable.

## Verification

Design-input verification should include:

- Trace coverage: every accepted delta has implementation and evidence.
- Stale-carryover: affected surfaces show no superseded style, class, or previous-version element, the implementation's style sources no longer contain styles the updated reference removed, and backend and app surfaces route no superseded endpoint, rule, flag, query, or job, unless the delta records a compatibility retention.
- Visual conformance: when a page-faithful target exists, the page/component matches its frozen source, scope, and tolerance; inspiration alone creates no pixel-faithful claim.
- State coverage: required states and breakpoints are checked.
- Behavior conformance: PRD workflow and data/API behavior still pass.
- Design-system conformance: in system-conformance mode, tokens/components/variants follow the updated pair; for `design-system/4`, the frozen derived HTML also matches the pair and bound sources. In target-conformance mode, do not claim this gate.
- Contract conformance: an active system-conformance design uses only entries `design-system.json` lists and runs the UI contract check; active target-conformance uses the smallest shared style source needed and runs page-to-target comparison at the recorded tolerance. Both follow the PRD and the approved HiFi surface with its `ui-hifi-copy/1` copy across the active responsive set in normal and reduced motion. Routine maintenance checks current product behavior and affected regression consumers, preserving historical design bytes. Drift from an active source is a contract violation.
- Builder direction conformance: selected choices are reflected and provisional/assumed choices remain explicit; this proves direction conformance, not usability.
- Usability evidence: when required, representative users or an approved equivalent complete the named task against the specified prototype or implementation; agent preference, screenshots, and automated E2E do not substitute for that evidence.
- Regression: preserved routes, permissions, data behavior, content, analytics, and E2E journeys still pass.

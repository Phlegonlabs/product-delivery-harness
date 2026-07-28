# Existing App Refinement

Use this reference when the user has an already-developed app, site, dashboard, SaaS product, or prototype and wants refinement, polish, optimization, cleanup, or evidence-backed improvement.

## Refinement Rule

Do not start by rewriting. Start by proving the current state.

```text
1. Identify the app archetype and target surfaces.
2. Capture a baseline from the running or buildable app.
3. Rank concrete issues by user impact, confidence, effort, and regression risk.
4. Convert accepted candidates into small missions.
5. Implement one improvement at a time.
6. Verify before/after evidence and run regression checks.
```

## Intake Fields

```text
Refinement target: UX | visual polish | performance | accessibility | SEO | conversion | reliability | test coverage | code quality | release readiness
Current state: deployed URL | local app route | screenshots | failing checks | user complaints | analytics | known TODOs
Baseline command:
Primary journey:
Must preserve:
Out of scope:
Acceptance threshold:
```

If the user says "make it better" without a target, perform a refinement audit first and record a ranked backlog in `RUN.md`. Do not create a separate backlog file unless the list becomes materially difficult to scan. Do not implement the backlog until the user accepts candidates or authorizes defaults.

## Baseline Evidence

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
Release readiness: env vars, deploy smoke, migrations, rollback, monitoring, release impact
```

Evidence can be command output, screenshots, traces, console logs, metrics, file references, or a rendered-page observation. When PLAN marks UI evidence required, retain a real screenshot for every planned breakpoint and state; the other evidence types are supplemental. Mark unverifiable surfaces as `UNVALIDATED`.

## Refinement Backlog Rows

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

## Mission Patterns

Use this pattern when refinement starts from an audit — the user wants the app improved but supplied no updated PRD, wireframe, design system, or page UI reference. When an updated input did arrive, `design-input-updates.md`'s "Existing App Refinement Flow" is primary instead: run that flow and feed it this file's lenses, backlog rows, and regression checks rather than standing up a second parallel mission set. The merge rule is stated there.

Use one mission per accepted refinement theme:

```text
M1 baseline and backlog
M2 targeted UX/visual refinement
M3 performance or accessibility pass
M4 platform-specific refinement, such as SaaS auth/tenant or public-site SEO
M5 regression and release verification
```

For small accepted refinements, skip worktrees and run direct work with before/after evidence. Use worktrees when several accepted refinements can run independently or when the parent checkout must remain stable.

## Regression Protection

Before closeout, verify:

- The original primary journey still passes.
- The accepted metric or visual state improved or is explicitly accepted.
- Existing app contracts, routes, permissions, content, and data behavior did not regress.
- Screenshots/traces compare before and after for UI changes.
- Performance/accessibility/SEO changes include a threshold or artifact.
- Any skipped checks are recorded with risk.

## Stop And Ask Conditions

Stop before implementation when:

- The requested refinement implies a product redesign or information-architecture change.
- The app cannot build or run and no baseline can be captured.
- The only available evidence is subjective preference with no design source or user goal.
- A change would remove existing behavior, content, routes, analytics, permissions, or data.
- The user asks for production-affecting changes without a safe verification path.

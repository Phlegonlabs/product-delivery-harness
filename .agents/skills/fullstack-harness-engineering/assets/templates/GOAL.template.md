# Goal Prompt: <feature or product slice>

```text
/goal Deliver <measurable full-stack outcome> using <contract paths> as frozen source of truth and <runbook path> as the mission state
verified by <E2E verification path> recording PASS for every required gate with evidence and no unaccepted UNVALIDATED surfaces
while preserving <frozen contracts, local data, unrelated/user changes, security/permission constraints>.
Use <mission coordination table>; run one mission at a time unless mission worktrees are declared independent; for parallel work, spawn one worker per independent mission in its own worktree and keep shared state updates parent-owned.
Between iterations, first check elapsed time and guardrails; then choose one ready task, run its verifier, record evidence, commit only verified work if commits are allowed, and update mission state.
Guardrails: one task per iteration; stop after 3 no-progress iterations; do not retry the same failed approach more than twice; ask before destructive actions, scope changes, skipped must-have requirements, or worktree cleanup.
If blocked, a verifier fails repeatedly, a required tool/source is unavailable, or no valid path remains, report the exact blocker, evidence, changed files, and required input.
```

## Pre-Launch Checklist

- [ ] Contract files exist and are frozen or assumptions are explicitly authorized.
- [ ] Mission runbook lists dependencies, write scopes, worktrees, verifiers, and evidence paths.
- [ ] E2E verification matrix has literal pass signals.
- [ ] UI Evidence Gate decision is recorded for every UI-bearing mission.
- [ ] Worktree/resource isolation is recorded for parallel missions.
- [ ] Destructive actions, migrations, data writes, and secret handling have approval rules.
- [ ] Product archetype gates are selected: SaaS/auth/tenant/billing/admin, public-site/content/SEO/analytics, catalog/commerce, or explicit n/a.
- [ ] Tenant isolation, role matrix, billing entitlement, content/SEO, analytics/conversion, catalog, and deployment smoke checks are either PASS-ready or marked `UNVALIDATED` with accepted risk.
- [ ] Existing-app refinement runs have baseline evidence, accepted refinement IDs, before/after evidence targets, and regression checks.
- [ ] Updated PRD, wireframe, design system, and page UI references are recorded as accepted deltas with affected routes/components and conformance evidence.

# Verification Gates

Use this reference to define task, mission, integration, UI, and release acceptance.

## Verification Ladder

Use the smallest reliable proof first:

```text
1. Reproduce or define the observable target.
2. Identify the smallest deterministic check.
3. Add focused regression coverage when behavior changes.
4. Run broader build/lint/type/unit checks.
5. Run API/data/integration checks.
6. Run browser E2E and visual/UI checks when UI changes.
7. Record evidence with commands, exit codes, artifacts, traces, screenshots, metrics, or approval.
8. If deterministic checks are impossible, use structured review and name residual risk.
```

## Gate Levels

Task gate:

- Proves one task changed the intended behavior.
- Must pass before commit.
- After it passes, create at most one coherent task commit using `commit-convention.md`; split the task first when independent outcomes remain.

Mission gate:

- Proves all task acceptance rows for one mission.
- Includes UI evidence if the mission changes UI, layout, navigation, or a user journey.

Integration gate:

- Runs after merged work lands on the parent/integration branch.
- Reruns each mission verifier where practical.
- Proves cross-mission behavior did not regress.

E2E gate:

- Proves the primary user journey works through UI, API, auth/permissions, data, and error handling.
- Blocks final PASS unless the user accepts named residual risk.

## Full-Stack E2E Matrix

Use or adapt this matrix:

```text
| Gate | Required when | Pass signal | Evidence |
|---|---|---|---|
| Build | always for buildable apps | command exits 0 | command + exit code |
| Lint / format | repo has commands | command exits 0 | command + exit code |
| Typecheck | typed codebase | command exits 0 | command + exit code |
| Unit tests | behavior changed | relevant suite exits 0 | command + exit code |
| API tests | API/service changed | expected status/body/validation | command + output |
| DB migration | schema changed | migrate/reset/seed succeeds | command + log |
| Permissions | auth/role behavior changed | allowed/denied cases pass | test or trace |
| Auth lifecycle | identity/session changed | signup/login/logout/session cases pass | test or trace |
| Tenant isolation | tenant-scoped data changed | cross-tenant access denied | test or trace |
| Billing / entitlement | plan-gated feature changed | allowed/blocked cases pass | test or trace |
| Audit / observability | sensitive action changed | event/log/metric created | log/test output |
| Browser journey | UI or workflow changed | primary journey completes | trace/screenshot/log |
| Responsive | UI changed | target breakpoints render without overlap | viewport captures |
| Console/network | browser surface changed | no relevant errors | console/network log |
| Accessibility | interactive UI changed | no serious blockers or named residuals | checker output |
| Visual design | design source exists | matches wireframe/design system within stated tolerance | screenshots or human approval |
| SEO metadata | public page changed | title/description/canonical/OG/schema as specified | rendered HTML or test |
| CMS/content readback | content source changed | draft/preview/publish/readback works | command/log/screenshot |
| Analytics / conversion | CTA/form/tracking changed | event/form/webhook observed or stub-verified | log/trace |
| Catalog / ecommerce | catalog surface changed | PLP/PDP/search/price/availability pass | test/trace |
| Performance | perf-sensitive path changed | metric threshold met | benchmark/report |
| Deployment smoke | deployment in scope | deployed URL and critical routes pass | command/trace |
| Release impact | user/operator-visible change | impact recorded | release note or mission row |
```

## UI Evidence Gate

Required when:

- The mission changes UI, UX, navigation, layout, visual styling, responsive behavior, or a real user journey.
- The user explicitly asks for visual proof.
- Acceptance requires screenshots, browser checks, or design comparison.

Optional when:

- The change is user-facing but not visual, and DOM/API/component tests prove it.

Not required when:

- Backend-only, cron, data pipeline, config, tests, refactor, docs-only, or API-only work has no browser-visible state.

Prefer targeted viewport, element, region, or trace evidence over whole-page screenshots. Whole-page captures need a reason.

## Evidence Schema

Each evidence row should include:

```text
Trace:
Command / action:
Expected pass signal:
Actual result:
Exit code:
Artifact path:
Commit hash:
Commit subject:
Status: PASS | FAIL | BLOCKED | UNVALIDATED
Notes:
```

## Failure Handling

If verification fails:

- Do not claim done.
- Do not commit failed work unless the commit is explicitly a harness/test artifact needed to expose the failure.
- Record the failing command, exit code, and minimal error.
- Decide whether the next action is code fix, test fix, environment fix, contract clarification, or user input.
- Treat repeated failure as a harness issue after two similar failed attempts.

## Closeout Bar

Final PASS requires:

- Every must-have trace ID is covered.
- Every required gate is PASS.
- Every skipped gate is justified.
- Every `UNVALIDATED` surface is named.
- Evidence paths exist or the user accepted non-file evidence.
- Baseline and skipped-check justifications are recorded when relevant.
- When worktree mode was used: the integration branch verifier has been rerun after merge. In single-checkout mode the final E2E gate on the working branch covers this.
- Landing state is recorded: pushed/PR opened with user approval, or explicitly left local.
- When worktree mode was used: worktree and branch cleanup is completed with user approval or explicitly deferred. In single-checkout mode record `N/A - single-checkout`.

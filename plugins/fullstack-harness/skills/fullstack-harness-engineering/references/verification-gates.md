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
- Must pass before a worker result can become `worker_passed` and before a task commit when commits are authorized.
- After it passes, create at most one coherent task commit using `commit-convention.md`; split the task first when independent outcomes remain.

Worker mission gate:

- Proves all task acceptance rows for one mission.
- Includes UI evidence if the mission changes UI, layout, navigation, or a user journey.
- Produces a worker result candidate; it does not satisfy downstream dependencies by itself.

Mission integration gate:

- Runs after merged work lands on the parent/integration branch.
- Runs that mission's declared `integration_verifiers` on the integrated head.
- Is the only gate that may transition a mission to `integrated` after the parent confirms the integrated SHA is reachable from the current integration head.

Batch integration gate:

- Runs the PLAN-level `batch_verifiers` after every selected wave has integrated serially.
- Proves cross-mission behavior did not regress and blocks the next wave on failure.

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

## Automated E2E And Smoke Reuse

Make deterministic automated E2E the normal proof for every primary journey. Record its command, CI check name, environment, covered journey, expected pass signal, artifact or retained log, and commit SHA before execution.

A current-head E2E PASS replaces a duplicate manual smoke only when all of these are true:

- The E2E ran against the exact integration or PR head being accepted.
- It covers the same primary journey, assertions, configuration, data, auth state, and external dependencies as the proposed smoke.
- It has a deterministic pass signal and retained evidence that can be tied to that head SHA.
- No later code, configuration, migration, dependency, or deployment change invalidated the result.

When these conditions hold, record the manual smoke disposition as `not required - covered by current-head E2E`, with the E2E check and SHA. This is not a skipped gate and needs no risk acceptance.

Manual smoke or another environment-specific check is still required when automated E2E is missing, skipped, failed, flaky, or materially narrower than the target; when a visual or external integration remains uncovered; or when the deployed environment differs from the tested environment. Deployment smoke remains a separate gate whenever deployment is in scope and current-head E2E did not run against that exact deployed release.

## Cloudflare Development And Production Gates

For a new PLAN schema-v4 Cloudflare release, use two deployed-environment gates rather than treating a successful upload as release completion; existing schema-v3 release plans retain the same gates:

| Gate | Source | Required proof |
|---|---|---|
| Development deployment | exact current PR head after current-head CI | development Worker/version/URL, migration PASS or not required, sandbox payment and development auth/data checks when applicable, deployed-environment E2E PASS, retained evidence |
| Production deployment | exact merged `main` SHA after development and merge PASS | production Worker/version/URL, migration PASS or not required, live configuration boundary, critical-route and primary-journey smoke PASS, retained evidence, rollback version when available |

Any new PR push invalidates the earlier development deployment PASS. Any new merged-base change invalidates production evidence that was not deployed from that exact SHA. Production cannot pass from the PR-head SHA after a squash merge; bind it to `landing.merged_sha` and retain the development PR-head evidence separately.

For authentication, payment, entitlement, or customer-data products, development verification must prove sandbox/non-production boundaries and production smoke must avoid destructive live transactions. Never substitute production data access for a missing development fixture.

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

## UX Direction And Usability Evidence

Keep these proofs separate:

| Proof | Question answered | Valid evidence |
|---|---|---|
| Builder UX Direction conformance | Did the result follow the named human builder's selected direction? | PRD/design source comparison, implementation review, screenshots |
| Behavioral completion | Can the system technically complete the critical task? | deterministic browser E2E, API/data assertions, trace |
| Accessibility | Can required users perceive and operate it under the declared standard? | automated checks plus required keyboard, assistive-technology, or human evaluation |
| Usability | Can representative users understand and complete the task with the intended effort and confidence? | prototype or implementation testing with representative users, or another explicitly approved research method |

Builder approval proves only direction conformance. Agent judgment, heuristic review, screenshots, and automated E2E may find problems, but none of them alone is representative-user usability evidence.

For every required usability gate, record the `UX-*` trace, critical task and scenario, prototype or implementation version, validation method, representative participant/source, target success/failure signal, actual result, findings and decision, evidence location, and bound commit or prototype version. Store only redacted summaries in the repository unless the user explicitly approves participant data or recordings.

Use `PASS` only when the declared method and target pass. Use `UNVALIDATED` when representative evidence is missing, the method is materially narrower than planned, or only builder/agent review exists. A required `UNVALIDATED` UX gate blocks final completion unless the named residual risk is explicitly accepted.

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

## Worker Result Gate

Before integration, the parent validates observed facts rather than trusting a report alone:

```text
Plan revision and digest match the active plan
Mission and lease match the selected wave
Reported base SHA matches the batch base
Reported head SHA matches the observed worker branch/ref
Base is an ancestor of head
Actual changed files stay inside mission write scope
No parent-owned PLAN.md or RUN.md was changed
No denied path or undeclared runtime resource was touched
Required worker verifiers are PASS with literal command/action evidence
```

If any check fails, set `worker_failed` or `blocked`; do not integrate. A clean worker result transitions through `integrating`, then either `integrated` after the integration gate passes or `integration_failed` if it does not.

Dependency readiness is strict: only a dependency in phase `integrated`, with `integration_gate: PASS` and a recorded integrated SHA reachable from the current integration head, is satisfied. `worker_passed`, a green branch, or a finished thread is insufficient.

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
- When `parent_managed_worktree` or `app_managed_worktree` was used: the integration-branch verifier has been rerun after integration. In `shared_checkout` mode the final E2E gate on the working integration head covers this.
- Every mission required for completion is `integrated`; no `leased`, `worker_running`, `worker_passed`, or `integrating` state remains.
- The final integration head still descends from every recorded required mission integration SHA.
- Landing state is recorded: explicitly left local, or final branch pushed and PR opened with user approval.
- In pull-request mode, local diff review passed before push; integration head, current PR head, check head, and review head match; checks and review are PASS; blocking findings and unresolved threads are zero. Any newer local integration or push resets this gate.
- When a primary journey exists, its required automated E2E check is PASS on the current head. Any replaced manual smoke records `not required - covered by current-head E2E`; uncovered or environment-specific smoke remains required.
- `merge_status: ready` is recorded only after the current-head landing gate passes, and `merged` preserves that evidence while adding the merged PR state and merge SHA. Actual merge and deploy remain separate authorized actions.
- A schema-v4-through-v6 auto-merge request is recorded only after the same current-head landing gate passes, `merge_pr` covers the exact PR, and the request is bound to that PR head SHA. Any changed head resets the request before fresh CI and review.
- A PR closed without merge records `closed` / `closed_unmerged` with no merge SHA; it is not left in the reusable `not_ready` state.
- In schemas v5 through v7, a completed pull-request run records `post_merge_cleanup` as complete or deferred. Complete cleanup proves the merged SHA is reachable from the refreshed base, the exact local branch still matched the merged PR head before deletion, the primary checkout is clean on the base, and any exact parent-managed linked worktree was clean and is now absent. `not_applicable` requires no matching linked worktree in the current observation; app-managed lifecycle is deferred instead of manually removed.
- When a worktree mode was used: manual worktree/branch cleanup is completed under its exact authorization or explicitly deferred, and app-managed platform lifecycle is recorded separately. In `shared_checkout` mode the worktree step is `not_applicable`; the primary checkout is never removed.

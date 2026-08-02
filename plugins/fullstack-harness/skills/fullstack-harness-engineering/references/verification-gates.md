# Verification Gates

Use this reference to define task, mission, integration, and UI acceptance.

## Verification Ladder

Use the smallest reliable proof first:

```text
1. Reproduce or define the observable target.
2. Identify the smallest deterministic check.
3. Run affected task and worker checks from parent-observed changed files.
4. Complete at least one read-only review on each exact worktree head before integration.
5. Run the mission integration surface after serial integration into the resolved integration branch.
6. Run only real cross-mission checks at the batch gate.
7. Converge runtime code review and repairs on an exact head.
8. Run broad regression, browser E2E, and visual/UI checks on the final current head.
9. Record evidence with commands, exit codes, artifacts, traces, screenshots, metrics, or approval.
10. If deterministic checks are impossible, use structured review and name residual risk.
```

## Gate Levels

Task gate:

- Proves one task changed the intended behavior.
- Runs focused checks selected from parent-observed changed files when the verifier declares `selection.mode: "changed_files"`; omitted selection metadata means `always`.
- Must pass before a worker result can become `worker_passed` and before a task commit when commits are authorized.
- After it passes, create at most one coherent task commit using `commit-convention.md`; split the task first when independent outcomes remain.
- Confirms every file the task touched still satisfies the project's File Size Limit (see the seeded root `CLAUDE.md`/`AGENTS.md`). A task that leaves a touched module over the limit without a stated exception fails this gate, rather than being caught, if at all, only by a later code review's subjective judgment.

Worker mission gate:

- Proves all task acceptance rows for one mission.
- Runs only applicable focused worker verifiers when changed-file selection is declared. Worker-reported paths never control applicability; the parent recomputes it from the observed diff.
- Produces a worker result candidate; it does not satisfy downstream dependencies by itself.

Worktree pre-integration review gate:

- Runs after worker checks and before the parent merges that mission head.
- Binds at least one independent read-only review to the exact current worktree head and records the reviewer, decision, findings, and evidence.
- In a Codex app task, the task's own Multi-agent reviewer performs this round when its enabled policy permits `reviewer`. If that policy is disabled, or a graph-backed direct worker has no nested policy, the parent runs an equivalent read-only review and records a terminal `review_workers[]` PASS whose review node covers the mission and whose `reviewed_sha` equals the current worktree head.
- Requires zero unresolved blocking findings. Any repair changes the head, invalidates the prior review, and requires a fresh round.
- Is the only gate that may transition a mission from `worker_passed` to `integrating`.

Mission integration gate:

- Runs after reviewed work lands on the resolved integration branch — the run's own `codex/<short-name>` branch under the default model.
- Runs that mission's declared `integration_verifiers` on the integrated head.
- Is the only gate that may transition a mission to `integrated` after the parent confirms the integrated SHA is reachable from the current integration head.

Batch integration gate:

- Runs the PLAN-level `batch_verifiers` after every selected wave has integrated serially.
- Contains only checks that need more than one integrated mission or shared contract. Do not repeat focused task suites here.
- Proves cross-mission behavior did not regress and blocks the next wave on failure.

Final/current-head gate:

- Runs broad regression, browser E2E, and visual/UI evidence only after local code-review and repair loops converge.
- Binds every PASS to the exact integration head. Any later code or configuration change invalidates the affected proof.
- Delivery ends on this local evidence. The harness never waits for remote CI or remote review.
- In `integration_push` mode, push only the final verified candidate — the exact head this gate passed on.

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
| Page-to-wireframe conformance | a route has a `wireframes.md` screen entry | the built route matches its screen entry in region responsibilities, section order, actions, and exact wording or display contract, judged at every required viewport or size class; state the tolerance and what is allowed to differ (real data, live copy, platform chrome) | screenshots + reviewer note |
| UI contract check | `design-system.json` exists | `scripts/check_ui_contract.py` reports no violation against the product's real source; a run that analyzed zero files is not a pass, and a `--rule`-filtered run is not a contract-clean signal | checker output |
| Design-system pair check | `design-system.md` and `design-system.json` both exist | `product-design-builder`'s `scripts/check_design_system_pair.py --markdown <design-system.md> --registry <design-system.json> --require-filled` exits 0 against the frozen pair, run from the repository root and never with `--write`; a failure is a stop condition per `contract-and-traceability.md`, not a fix-it-inline finding | checker output |
| Content contract conformance | a product component renders contract-governed content | every field in `design-system.json`'s `requiredContentOrder` renders, in that order — those fields never drop; limits, formats, empty and long-content rules respected | screenshot or content review |
| State matrix coverage | a UI route changed | every state in `design-system.json`'s `stateMatrix` is captured or listed as `<state>:n/a` with a reason, at every required viewport or size class | `ui_evidence` rows |
| No-JavaScript path | a route's wireframe screen declares server-rendered content | that content renders and is readable with JavaScript disabled | screenshot with JS disabled |
| SEO metadata | public page changed | title/description/canonical/OG/schema as specified | rendered HTML or test |
| CMS/content readback | content source changed | draft/preview/publish/readback works | command/log/screenshot |
| Analytics / conversion | CTA/form/tracking changed | event/form/webhook observed or stub-verified | log/trace |
| Catalog / ecommerce | catalog surface changed | PLP/PDP/search/price/availability pass | test/trace |
| Performance | perf-sensitive path changed | metric threshold met | benchmark/report |
| User-visible impact | user/operator-visible change | impact recorded | mission row |
```

## Changed-File Selection And Exact Execution Reuse

Changed-file selection is allowed only for task and worker verifiers. The declared selection scopes must stay inside the owning task or mission write scope. Integration, batch, final, migration, and smoke gates always run when their stage applies.

The parent supplies normalized, repository-relative observed paths to `select_verifiers.py`. A targeted verifier is `not_applicable` only when no observed path matches its exact path or `/**` subtree. Invalid or incomplete parent observations fail safe by requiring every declared verifier.

Every applicable declared verifier runs through `verifier_runtime.py`'s `run_verifier()`, cache configured or not; its returned `execution_key` is the worker result's reported `evidence`. This is unconditional — it is not limited to the `session_exact` cache-reuse path described below.

A local verifier may declare:

```json
{
  "selection": {
    "mode": "changed_files",
    "scopes": ["apps/api/**"]
  },
  "cache": {
    "mode": "session_exact",
    "environment_keys": ["CI"]
  }
}
```

`session_exact` is opt-in and accepts only literal `pass_signal: "exit 0"`. The parent must also mark the command deterministic and local, supply a clean checkout, and place the session cache in a repository-external path. The execution key binds run ID, PLAN revision/digest, graph revision, batch base, exact head, changed-file digest, trust domain, checkout role, cwd, ordered argv, executable identity, OS/architecture, pass signal, and selected environment-value digests.

Only PASS with exit code 0 is reusable. A changed input, dirty checkout, malformed entry, failure, timeout, missing cache root, or unsafe cache location runs the command fresh. Verifier IDs are not in the execution key, so two gates may cite one exact execution while each keeps its own PASS record and evidence key. Never use this cache for runtime review, browser capture, migration, mutable-environment smoke, network/shared-database checks, or time/random-dependent commands.

## Automated E2E And Smoke Reuse

Make deterministic automated E2E the normal proof for every primary journey. Record its command, CI check name, environment, covered journey, expected pass signal, artifact or retained log, and commit SHA before execution.

A current-head E2E PASS replaces a duplicate manual smoke only when all of these are true:

- The E2E ran against the exact integration head being accepted.
- It covers the same primary journey, assertions, configuration, data, auth state, and external dependencies as the proposed smoke.
- It has a deterministic pass signal and retained evidence that can be tied to that head SHA.
- No later code, configuration, migration, or dependency change invalidated the result.

When these conditions hold, record the manual smoke disposition as `not required - covered by current-head E2E`, with the E2E check and SHA. This is not a skipped gate and needs no risk acceptance.

Manual smoke or another environment-specific check is still required when automated E2E is missing, skipped, failed, flaky, or materially narrower than the target, or when a visual or external integration remains uncovered.

## UI Evidence Gate

Required when:

- The mission changes UI, UX, navigation, layout, visual styling, responsive behavior, or a real user journey.
- The user explicitly asks for visual proof.
- Acceptance requires screenshots, browser checks, or design comparison.

Optional when:

- The change is user-facing but not visual, and DOM/API/component tests prove it.

Not required when:

- Backend-only, cron, data pipeline, config, tests, refactor, docs-only, or API-only work has no browser-visible state.

Prefer targeted viewport, element, or region screenshots over whole-page captures. Whole-page captures need a reason. Traces, console logs, and browser reports are supplemental; they do not replace a required screenshot.

For every PLAN surface with `evidence_gate: required`, capture one screenshot for each planned route-by-breakpoint-by-state combination. Schema-v9 `ui_evidence` records the surface ID, route, breakpoint, state, repo-relative image path under `docs/goal/evidence/`, lowercase SHA-256, exact integration head SHA, and status. The closeout validator checks the matrix, current-head binding, file existence, non-empty image signature, and hash.

### Capture Mechanism By Platform

Only the capture mechanism changes with the resolved platform; the evidence discipline above is identical everywhere. Every platform must still produce a real binary screenshot under `docs/goal/evidence/`, record a lowercase SHA-256, bind it to the exact integration head, and cover the full breakpoint-by-state (native: device/OS-by-state) matrix. Placeholder, fabricated, or hand-drawn images never satisfy the gate.

For a web mission, capture through a browser: Playwright/headless-browser screenshots or browser DevTools, at the planned viewports. The route-by-breakpoint-by-state matrix and the runbook's web UI Evidence columns apply.

For a native iOS/Android/Flutter/macOS/Windows mission, capture through the platform's own UI-test tooling instead of a browser, using the device/OS-by-state matrix and the runbook's native UI Evidence columns:

- iOS: iOS Simulator screenshots produced by `xcodebuild test` running XCUITest cases.
- Android: Android Emulator screenshots produced by Espresso via `./gradlew connectedAndroidTest`.
- Flutter: integration-test screenshots via `flutter test integration_test/` (or `flutter drive`), captured for each native target in scope.
- macOS desktop: XCUITest screenshots from `xcodebuild test`.
- Windows desktop: WinAppDriver or a .NET UI-test framework driving the app.
- Fallback: when no UI-test tooling exists for the project yet, a manually captured Simulator/Emulator/device screenshot is acceptable, recorded with the same path, hash, and head binding and labeled as a manual capture.

When the design source's mockup HTML is styled to a different platform than the resolved target (for example web-styled mockups for a native mission), do not silently implement against it or guess the capture mechanism; stop and ask per `contract-and-traceability.md`'s mismatch condition.

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

Every current RUN-v10 PLAN batch and final gate has one canonical `batch_gate_results` or `final_gate_results` entry with the same gate ID, gate status, exact integration head SHA, and non-empty evidence. A PASS is stale as soon as the integration head changes, regardless of the RUN lifecycle state. Markdown evidence rows do not replace these canonical closeout records.

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
Required worker verifiers are PASS with `evidence` equal to the literal `execution_key` produced by `verifier_runtime.py`
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
- Every visual `TEST-*` obligation `PRD.md` marks required maps to a specific verification row above and that row is PASS. A generically named visual gate does not satisfy a specific obligation (see `contract-and-traceability.md`'s Trace IDs). A required `TEST-*` ID with no matching row is an uncovered must-have trace, not an optional extra.
- Schema-v9-and-later batch/final-gate IDs exactly match PLAN, and every result is PASS with evidence on the exact integration head.
- Closeout runs `scripts/validate_harness_plan.py --design-system <path to design-system.json>` whenever a design system is a contract source, so its `stateMatrix` and responsive set are cross-checked against the PLAN's UI surfaces. Without it, required screenshot coverage is derived from the PLAN's own state list, and a PLAN that declares `ready` alone reaches a PASS closeout with one state of eleven.
- Closeout runs `scripts/validate_harness_plan.py --repo-root` to cross-check `integration_head_sha` against the live Git branch head before trusting any recorded head-bound PASS: RUN.md's own internal consistency never proves the recorded head still matches reality.
- Every skipped gate is justified.
- Every `UNVALIDATED` surface is named, and naming it does not substitute for passing when that surface is still required: Final PASS is blocked while any required `ui_evidence` row (or other required gate) is `UNVALIDATED`, unless the user has explicitly accepted it as descoped with a recorded reason. A required row's screenshot or other evidence artifact changing after being marked PASS (a working-tree diff to an already-recorded evidence file) invalidates that recorded PASS until a fresh evidence-capture attempt reruns and re-binds it to the current head.
- Evidence paths exist. Required UI evidence is a real screenshot for every planned breakpoint-by-state combination, bound to the integration head and matching its recorded SHA-256; accepted non-file evidence applies only to gates that do not require screenshots.
- Baseline and skipped-check justifications are recorded when relevant.
- When `parent_managed_worktree` or `app_managed_worktree` was used: the integration-branch verifier has been rerun after integration. In `shared_checkout` mode the final E2E gate on the working integration head covers this.
- Every mission required for completion is `integrated` or explicitly superseded; every live task is `mission_recorded` with a PASS verifier, and no blocker, active or blocked mission/review worker, or open wave remains.
- The final integration head still descends from every recorded required mission integration SHA.
- Landing state is recorded: the verified integration head pushed to the run's own branch, or the run explicitly left local. `landing.continuity` is `preserved` at that integration head.
- In `integration_push` mode, local diff review passed before push and `pushed_head_sha` equals the integration head. Any newer local integration resets this gate. `pushed_head_sha` is a parent-attested record: the push itself is observed by the parent, not provable by the validators, which check it only for internal consistency and against the local branch.
- For current PLAN-v5 graph runs, every node is succeeded, skipped, or superseded with no retained blocker, and every edge is traversed, exhausted, or skipped; failed nodes must be routed or superseded, and no selector-ready work remains.
- When a primary journey exists, its required automated E2E check is PASS on the current head. Any replaced manual smoke records `not required - covered by current-head E2E`; uncovered or environment-specific smoke remains required.
- When a worktree mode was used: manual worktree/branch cleanup is completed under its exact authorization or explicitly deferred, and app-managed platform lifecycle is recorded separately. In `shared_checkout` mode the worktree step is `not_applicable`; the primary checkout is never removed.

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
7. After serial integration, run fresh parent-dispatched reviewers on the exact unified head and converge their repairs.
8. Fix the candidate SHA, then run one planned broad regression, browser E2E, and visual/UI validation suite on that head.
9. Record evidence with commands, exit codes, artifacts, traces, screenshots, metrics, or approval.
10. If deterministic checks are impossible, use structured review and name residual risk.
```

For RUN-v11 screenshot evidence, the order is immutable Git blob read, safe byte-based decode, then `artifact_sha256` comparison. RUN-v9 keeps its historical working-tree check.

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

Non-runtime node gate:

- Applies to `approval`, `external_wait`, `lifecycle`, and deterministic (`local_command` or `harness_parent`) verifier nodes.
- The parent first reserves the selected attempt with `reserve-node-attempt`, then performs the check, waits for the external state, or runs the lifecycle side effect outside the RUN lock.
- `record-node-result` closes only the matching reserved attempt, requires evidence, traverses declared route edges, and derives the graph phase from the outcome (`pass` → `succeeded`; `blocked`/`contract_gap` → `blocked`; `fix_required`/`retryable_failure` → `failed`). A lifecycle result is an evidence receipt; the transition never runs the action itself.
- If the non-runtime executor is interrupted, record `blocked` and the blocker through `record-node-result`; preserve the attempt evidence and use a fresh attempt for any retry.

Worktree pre-integration review gate:

- Runs after worker checks and before the parent merges that mission head.
- Binds at least one independent read-only review to the exact current worktree head and records the reviewer, decision, findings, and evidence.
- The parent dispatches the reviewer as a read-only sibling and records a terminal `review_workers[]` PASS whose preintegration-stage review node covers the mission and whose `reviewed_sha` equals the current worktree head. The mission worker never creates its own reviewer.
- Requires zero unresolved blocking findings. Any repair changes the head, invalidates the prior review, and requires a fresh round.
- Is the only gate that may transition a mission from `worker_passed` to `integrating`.

Mission integration gate:

- Runs after reviewed work lands on the exact non-default integration branch resolved from repository governance or the user's instruction.
- Runs that mission's declared `integration_verifiers` on the integrated head.
- Is the only gate that may transition a mission to `integrated` after the parent confirms the integrated SHA is reachable from the current integration head.

Batch integration gate:

- Runs the PLAN-level `batch_verifiers` after every selected wave has integrated serially.
- Groups independent local-command verifiers whose typed resource claims do not conflict. Use `scripts/verifier_runtime.py` batch mode. A verifier that declares no resource batches by default; `parallel_safe: false` or a conflicting exclusive claim keeps it serial. Task and worker gates use the same batch path.
- Contains only checks that need more than one integrated mission or shared contract. Do not repeat focused task suites here.
- Proves cross-mission behavior did not regress and blocks the next wave on failure.

Fresh integration review gate:

- Starts per surface once every mission covering that surface has integrated serially into one integration branch. It does not wait for unrelated surfaces still integrating.
- Uses new parent-dispatched read-only reviewer attempts on the exact `integration_head_sha`. A mission writer is never a reviewer.
- Skip the dispatch only when the integration head's tree is byte-identical to a tree a pre-integration review of the same review type already passed: the head is literally that reviewed commit, or it is a merge commit whose recorded `integration.integration_tree_sha` equals that review's recorded `review_workers[].tree_sha`. Then the reviewer would read a byte-identical tree and reach the same verdict, and a reviewer dispatch is one of the most expensive steps in a run. Record the node as `skipped`; the validator rejects that phase unless the matching PASS exists on that exact SHA or an identical tree. `harness_transition.py skip-integration-review --node-id <id> --worker-id <id> --repo-root <root>` performs the live-Git tree check and records the skip; `record-review-attempt --tree-sha` (or `--repo-root`) persists the reviewed commit's tree on PASS. This is the normal single-mission sequential wave: one mission integrated on top of reviewed state adds no new bytes to review.
- Any other integration head has a tree no earlier PASS covers. The "did the combination break" question is real there, and no earlier PASS answers it.
- Scope the reading to the seams. Each covered mission's content already passed its own exact-head review, so the packet lists the already-reviewed mission heads and this pass focuses on what combination changed — merge seams, conflict resolutions, cross-mission interaction, and shared-contract boundaries — instead of re-litigating mission internals.
- Uses one reviewer per applicable surface by default. Same-surface fan-out requires an explicit user request or a recorded high-impact risk. None may delegate.
- Returns all blocking findings in one bounded pass and routes one deduplicated finding set to a bounded repair mission. Runtime review permits only the initial review and one repair re-review. A repair changes the candidate SHA and invalidates every integration-stage PASS whose declared review scope intersects the repair diff. A review whose scope the repair did not touch keeps its PASS and records the new candidate SHA; the SHA string changing is not by itself a reason to re-review a surface the repair never reached.

Final/current-head gate:

- Runs the one planned broad regression, browser E2E, and visual/UI validation suite only after fresh integration review and repair loops converge.
- Binds every PASS to the exact integration head. Any later code or configuration change invalidates the affected proof.
- Focused task, worker, and integration checks are not this broad suite. Plan the suite as cross-cutting checks that only the whole candidate can answer — build, browser E2E, migration, UI evidence — rather than a rerun of every focused suite already green on the same code. A gate that only re-executes a mission's own unit tests on an unchanged tree is repeated work; either give it changed-file selection against the plan write union, or drop it and rely on the task and worker gates that already covered it.
- If the broad suite fails or a repair changes the candidate, establish and review a new candidate before rerunning it; do not claim an exactly-once history when the candidate changed.
- Delivery ends on this local evidence. The harness never waits for remote CI or remote review.
- In `integration_push` mode, push only the final verified candidate — the exact head this gate passed on.

E2E gate:

- Proves the primary user journey works through UI, API, auth/permissions, data, and error handling. When the matrix becomes materially difficult to scan or needs separate ownership, expand it into `assets/templates/E2E_VERIFICATION.template.md` and link it from `RUN.md`.
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
| Responsive layout safety | UI changed | every required breakpoint or size-class and state renders without unintended element overlap, clipping, occlusion, or horizontal overflow; intentional overlays match their named stacking, focus, safe-area, and dismissal behavior | viewport captures + browser geometry/reviewer evidence |
| Console/network | browser surface changed | no relevant errors | console/network log |
| Accessibility | interactive UI changed | no serious blockers or named residuals | checker output |
| Visual design | UI source exists | matches the PRD UI surface contract, approved wireframe, and active visual source (required design-system pair or approved page-faithful target) within stated tolerance | screenshots or human approval |
| Page-to-PRD conformance | a route has a `PRD.md` `UI-*` entry and matching approved wireframe | the built route matches PRD behavior and wireframe region order, grouping, element inventory, states, responsive rearrangement, actions, and exact wording or display contract, judged at every required viewport or size class; no unintended overlap, clipping, occlusion, or horizontal overflow; state the tolerance and what is allowed to differ (real data, live copy, platform chrome) | screenshots + browser geometry/reviewer note |
| UI contract check | `design-system.json` exists and the Design System Need Gate is `required` | `scripts/check_ui_contract.py --repo-root <root>` (default: current working directory) reports no violation against the product's real source; token and primitive source declarations resolve by exact normalized repo-relative identity, not filename suffix; a run that analyzed zero files is not a pass, and a `--rule`-filtered run is not a contract-clean signal | checker output |
| Design-system pair check | `design-system.md` and `design-system.json` both exist | `python .agents/skills/design-system-compiler/scripts/check_design_system_pair.py --markdown <design-system.md> --registry <design-system.json> --require-filled` exits 0 against the frozen pair, run from the repository root and never with `--write`; a failure is a stop condition per `contract-and-traceability.md`, not a fix-it-inline finding | checker output |
| Content contract conformance | a product component renders contract-governed content | every field in `design-system.json`'s `requiredContentOrder` renders, in that order — those fields never drop; limits, formats, empty and long-content rules respected | screenshot or content review |
| State matrix coverage | a UI route changed | every state in the required pair's `stateMatrix`, or in the PRD UI surface and approved target scope when the pair is `not_required`, is captured or listed as `<state>:n/a` with a reason at every required viewport or size class | `ui_evidence` rows |
| No-JavaScript path | a route's PRD UI surface declares server-rendered content | that content renders and is readable with JavaScript disabled | screenshot with JS disabled |
| SEO metadata | public page changed | title/description/canonical/OG/schema as specified | rendered HTML or test |
| CMS/content readback | content source changed | draft/preview/publish/readback works | command/log/screenshot |
| Analytics / conversion | CTA/form/tracking changed | event/form/webhook observed or stub-verified | log/trace |
| Catalog / ecommerce | catalog surface changed | PLP/PDP/search/price/availability pass | test/trace |
| Performance | perf-sensitive path changed | metric threshold met | benchmark/report |
| User-visible impact | user/operator-visible change | impact recorded | mission row |
```

## Changed-File Selection And Exact Execution Reuse

Task and worker verifiers select against their own task or mission write scope. Batch and final gates may also select, but against the union of every mission write scope in the PLAN, never one mission's slice — the question they answer is whether the whole candidate regressed. Each of `batch_verifiers` and `final_gates` must keep at least one always-run verifier, so cross-mission interaction is proved rather than selected away; put build, browser E2E, migration, and UI checks there. Integration, migration, and smoke gates always run when their stage applies.

The parent supplies normalized, repository-relative observed paths to `select_verifiers.py`. A targeted verifier is `not_applicable` only when no observed path matches its exact path or `/**` subtree. Invalid or incomplete parent observations fail safe by requiring every declared verifier.

Pillow is imported lazily by the UI-evidence path. When it is unavailable, return a targeted UI-evidence decoding error without preventing non-UI CLIs from starting. RUN-v11 screenshot checks decode the artifact from the accepted Git `head_sha`, not from a mutable working-tree copy.

Every applicable declared verifier runs through `verifier_runtime.py`'s `run_verifier()`, cache configured or not; its returned `execution_key` is the worker result's reported `evidence`. This is unconditional — it is not limited to the `session_exact` cache-reuse path described below.

A parent-owned batch/final graph verifier also carries the reserved node/attempt nonce and Git guard emitted by `reserve-node-attempt`. The runtime verifies the exact branch, HEAD, clean tree, and tracked-file fingerprint before and after execution. The exact tracked RUN excluded from dirty status is not excluded from integrity checks: its bytes and file identity are snapshotted across execution, its starting SHA-256 is attested, and `record-node-result` rehashes it before accepting evidence. A different checkout, replayed nonce, retargeted request, checkout drift, protected coordination-file change, or request/result artifact inside the reviewed checkout is rejected.

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

`session_exact` is opt-in and accepts only literal `pass_signal: "exit 0"`.

Integration, batch, and final gates refuse reuse by default. That default keys on the gate's layer, but the property that decides safety is the command's nature. A verifier at those layers may add `cache.deterministic_local: true` to attest it is a pure local deterministic command and become reusable. Never set it for runtime review, browser capture, migration, mutable-environment smoke, a network or shared-database check, or a time/random-dependent command; those are not pure functions of the tree and stay uncacheable regardless of layer. A static source scan such as `check_ui_contract.py` is a legitimate candidate. The parent must also mark the command deterministic and local, supply a clean checkout, and place the session cache in a repository-external path. The execution key binds run ID, PLAN revision/digest, graph revision, batch base, exact head, changed-file digest, trust domain, checkout role, cwd, ordered argv, executable identity, OS/architecture, pass signal, and selected environment-value digests.

Only PASS with exit code 0 is reusable. A changed input, dirty checkout, malformed entry, failure, timeout, missing cache root, or unsafe cache location runs the command fresh. Logical attribution — verifier ID, layer, mission, task, attempt, and lease — is not in the execution key, so equivalent opted-in task and worker gates may cite one exact execution while each keeps its own PASS record, context, and evidence key. Never use this cache for runtime review, browser capture, migration, mutable-environment smoke, network/shared-database checks, or time/random-dependent commands.

## Automated E2E And Smoke Reuse

Make deterministic automated E2E the normal proof for every primary journey. Record its command, CI check name, environment, covered journey, expected pass signal, artifact or retained log, and commit SHA before execution. A target repository that wants the same checks in CI seeds its workflow from `assets/templates/PROJECT_CI.template.yml`; CI results are retained evidence the harness may cite but never waits on, and CI and the harness share the single E2E command definition from the contract.

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

For every PLAN surface with `evidence_gate: required`, capture one screenshot for each planned route-by-breakpoint-by-state combination.

Capture the full matrix once on the mission's worktree head. After serial integration, recapture the full matrix bound to the integration head only when the integration diff intersects that surface's write scope; when it does not, rebind the existing evidence to the integration head and record why. A merge that touched only backend files cannot change a rendered UI surface, and recapturing the whole route-by-breakpoint-by-state matrix to prove that is the slowest verifier class in the ladder. A merge that did touch the surface recaptures in full. Schema-v9 `ui_evidence` records the surface ID, route, breakpoint, state, repo-relative image path under `docs/goal/evidence/`, lowercase SHA-256, exact integration head SHA, and status. The closeout validator checks the matrix, current-head binding, file existence, non-empty image signature, and hash.

For a route whose `UI-*` entry records SEO metadata, the same evidence set includes the rendered `<head>` on the integration head: its `<title>` and meta description match the PRD record. A mismatch is a failing check, not a style preference; a route with no PRD SEO record is a contract gap routed to `product-definition-builder`, not a verifier skip.

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

### Final Visual Parity Loop

Every run with at least one PLAN `ui_surfaces` entry closes its UI evidence with a final visual parity loop, bound to the exact integration head. The loop compares the implemented surface against the run's visual authority — this applies to both conformance modes, not only target-conformance runs.

For each planned route-by-breakpoint-by-state combination:

- **Target-conformance mode (HTML target):** open the route's approved HTML reference file in the browser at the same breakpoint and state, capture it, and capture the implemented route at that same combination. Store both under `docs/goal/evidence/` (for example `parity/<route>-<state>-<breakpoint>-target.png` and `-actual.png`). Compare layout, element inventory, and observable visual values item by item within the PRD handoff's recorded tolerance. The reference render is the comparison source, not an aspiration.
- **System-conformance mode:** the baseline is the frozen design-system pair. The comparison evidence is a clean `scripts/check_ui_contract.py` run against the product's real source at the integration head (a zero-file or `--rule`-filtered run is not a baseline) plus the full screenshot matrix checked against the pair's tokens and variants.

Record the comparison on each `ui_evidence` row as a `target_comparison` object: `baseline` (`html_target` or `design_system`), `baseline_artifact` (the reference-render image path under `docs/goal/evidence/` for `html_target`, or the contract-check evidence key for `design_system`), and `verdict` (`pass` or `deviation`). A `deviation` verdict must list every observed difference in `differences`, and each difference must either fall inside the PRD handoff's allowed deviations or trigger a repair.

Repair cycle: a missing element, a structural difference, or any difference outside the recorded tolerance is not a `pass`. Repair the surface, recapture the affected matrix entries, and rebind the evidence to the new integration head SHA. A parity repair is an ordinary candidate-changing repair: it invalidates the final-gate PASS and every integration-stage PASS whose scope intersects the repair diff, and it consumes review-lineage attempts under `graph-orchestration.md`'s Root-Cause Repair Escalation — the loop's two-round cap does not add attempts on top of that budget. Stop after two failed repair rounds and report the remaining differences as-is; never widen the tolerance or relabel an unresolved difference to close the run. Screenshots from an older head or placeholder images never satisfy the loop.

### Final Page-Quality Pass

Every run with at least one PLAN `ui_surfaces` entry follows the Final Visual Parity Loop with one final page-quality pass over the delivered high-fidelity pages, bound to the exact integration head. The pass runs the skill bound to the project's `ui_quality_verification` slot — `impeccable` by default — in evaluate mode: one `critique` (heuristic UX review) and one `audit` (accessibility, responsive, and performance checks) per delivered route, batched in a single round.

- Findings are ordinary review findings. A blocking defect enters the repair cycle under the same Root-Cause Repair Escalation budget as a parity repair; the pass adds no review attempts of its own. Record the pass, every finding, and its verdict as evidence rows bound to the integration head, and never relabel an unresolved finding to close the run.
- The pass verifies quality, not direction. A finding that conflicts with the frozen `PRD.md` UI contract, approved `wireframes.html`, or the active visual source never authorizes a local change; route it to `product-definition-builder` as a design-input delta.
- Evaluate commands only. The pass never runs the bound skill's build, init, document, or live flows, and never creates `PRODUCT.md`, `DESIGN.md`, or another competing product authority in the repository.
- If the bound skill is unavailable in the delivery environment, record the gate `UNVALIDATED` with the named residual risk; it blocks final completion unless the user explicitly accepts the descoped gate.

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

Every current RUN-v11 PLAN batch and final gate has one canonical `batch_gate_results` or `final_gate_results` entry with the same gate ID, gate status, exact integration head SHA, and non-empty evidence. A PASS is stale as soon as the integration head changes, regardless of the RUN lifecycle state. Markdown evidence rows do not replace these canonical closeout records.

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

If candidate validation fails after its current node binding is accepted, `record-worker-result` retains the issues as `worker_failed` or `blocked`; use `reject-worker-result` when the candidate itself is stale or untrusted. Do not integrate either outcome. A clean result reaches `worker_passed`, then transitions through `integrating` to either `integrated` after the integration gate passes or `integration_failed` if it does not.

Dependency readiness is strict: only a dependency in phase `integrated`, with `integration_gate: PASS` and a recorded integrated SHA reachable from the current integration head, is satisfied. `worker_passed`, a green branch, or a finished thread is insufficient.

## Unified Code-Security Review

Every new managed PLAN records `security_review.status` as `required` or `not_applicable`; the latter needs a concrete non-code reason. Harness 0.28.0 and later refuse to generate or validate a new-version RUN when that policy is omitted. A required policy declares `security` in `required_reviews` and includes at least one integration-stage security reviewer covering every mission. The Harness parent resolves the project's `code_security_verification` Skill Binding, reserves the review attempt, and dispatches a fresh sibling reviewer with `code-security-review` against the exact `integration_head_sha`.

The security reviewer is read-only, never delegates, and reports all validated findings in one pass. It receives no write scope, commit authority, scanner-install permission, network permission, or live-target penetration authority. Optional local scanners may add evidence; a required but unavailable scanner, advisory source, or independent reviewer blocks the gate rather than producing a partial PASS. Completion passes the result as `--security-result`; the transition validates and retains its exact review type, decision, SHA, base, scope, exclusions, trust boundaries, tools, coverage, findings, and evidence. A security PASS must have an empty `exclusions` list; the current contract does not allow a PASS with narrowed or omitted coverage.

A security review is not eligible for `skip-integration-review`, even when a pre-integration code review covered a byte-identical tree. The unified security pass evaluates cross-mission trust boundaries and security-specific source-to-sink paths from a fresh context. PASS binds to the exact current integration SHA and declared scope. Any repair creates a new candidate, invalidates the security result and all downstream final-gate evidence, and requires a fresh security review before final validation.

Security reservation and completion recheck the live integration checkout before accepting the attempt: the exact integration branch and HEAD, clean status (allowing only the exact tracked RUN exception), and ancestry from the current batch base. A mismatch blocks the attempt. Required security nodes cannot be skipped, superseded, or replaced at closeout; a missing, skipped, stale, partial, blocked, or superseded security result prevents final PASS.

An interrupted security reviewer does not fabricate a structured decision. `reconcile-interrupted-reviews` retains a blocked worker without `security_result` only when the unique matching review attempt carries the `interrupted_review_reconciliation` receipt. The node returns to dormant and the run stays paused; the receipt cannot satisfy closeout. A later exact structured PASS from the current reviewer may close the gate while the receipt-bound historical worker remains. A PASS also needs at least one tool or manual source review recorded as `passed` or `findings`; skipped or unavailable tools alone are not review evidence.

The neutral PLAN template does not guess an unknown repair mission. Its security node returns `blocked` when a validated finding needs code changes; the parent then refines PLAN with a bounded repair and re-review route before any mutation. A project that declares `fix_required` on the security node must declare that bounded route up front.

## Failure Handling

If verification fails:

- Do not claim done.
- Do not commit failed work unless the commit is explicitly a harness/test artifact needed to expose the failure.
- Record the failing command, exit code, and minimal error.
- Decide whether the next action is code fix, test fix, environment fix, contract clarification, or user input.
- Treat repeated failure as a harness issue after two similar failed attempts.
- Treat adjacent edge cases from one parsing, validation, serialization, protocol, state-machine, or boundary primitive as one failure family. Do not authorize another example-specific patch after that family survives a repair.
- Before another write, require a structural repair objective and an acceptance matrix covering the family's known equivalence classes; otherwise return `REFINEMENT_REQUEST` or `contract_gap`.
- Preserve the mission + review surface + root-cause attempt count across PLAN revisions. Replanning never resets it, and a generic instruction to continue never authorizes an extra review.

## Closeout Bar

Final PASS requires:

- Every must-have trace ID is covered.
- Every required gate is PASS.
- Every new managed code-delivery PLAN has a completed `security` review from the `code_security_verification` binding, recorded as PASS on the exact current integration head with no exclusions. The required security node cannot be skipped or superseded; a missing, skipped, stale, partial, blocked, or superseded security review prevents closeout.
- Every visual `TEST-*` obligation `PRD.md` marks required maps to a specific verification row above and that row is PASS. A generically named visual gate does not satisfy a specific obligation (see `contract-and-traceability.md`'s Trace IDs). A required `TEST-*` ID with no matching row is an uncovered must-have trace, not an optional extra.
- Schema-v9-and-later batch/final-gate IDs exactly match PLAN, and every result is PASS with evidence on the exact integration head.
- Closeout runs `scripts/validate_harness_plan.py --design-system <path to design-system.json> --design-system-markdown <path to design-system.md>` whenever the Design System Need Gate is `required`, so both frozen hashes, the generated Markdown contract, compiler ID namespaces, all PLAN `DS-*` traces, `stateMatrix`, and the responsive set are cross-checked. In target-conformance mode, required screenshot coverage comes from the frozen PRD target scope and PLAN UI evidence rows; absence of both design-system arguments is expected only when PLAN does not freeze that pair.
- Closeout runs `scripts/validate_harness_plan.py --repo-root` to cross-check `integration_head_sha` against the live Git branch head before trusting any recorded head-bound PASS: RUN.md's own internal consistency never proves the recorded head still matches reality.
- Closeout passes `--prd <path to PRD.md>` whenever PLAN freezes a PRD source. The given bytes must equal that row's `content_sha256`; a source-revision-only row is not enough for this file join. A UI-bearing PRD has exactly one matched `ui-surface-contract` boundary pair and exactly one `route` and `states` anchor per `UI-*` entry. The PLAN's surface IDs, one literal route per entry, and states must equal those anchors, and the PRD is still parsed when PLAN claims no UI surfaces. A frozen approved wireframe source likewise requires byte-matching `--wireframes <path to wireframes.html>`, whose screen IDs, routes, and states must agree with PLAN and whose frozen bytes must pass `product-definition-builder`'s full wireframe checker (reviewer shell, self-containment, filled data, approved status, and the PRD-to-wireframe join). The transition write path runs the same source-presence, byte, and semantic joins under `--repo-root`, so closeout cannot be the first time executable drift is detected.
- Every skipped gate is justified.
- Every `UNVALIDATED` surface is named, and naming it does not substitute for passing when that surface is still required: Final PASS is blocked while any required `ui_evidence` row (or other required gate) is `UNVALIDATED`, unless the user has explicitly accepted it as descoped with a recorded reason. RUN-v11 re-reads the accepted Git blob at the recorded head, so a working-tree mutation cannot replace or satisfy that evidence; RUN-v9 keeps its historical working-tree invalidation behavior.
- Evidence paths exist. Required UI evidence is a real screenshot for every planned breakpoint-by-state combination, bound to the integration head and matching its recorded SHA-256; for RUN-v11, existence and decoding are checked in the accepted Git commit/ref rather than the working tree. Accepted non-file evidence applies only to gates that do not require screenshots.
- Baseline and skipped-check justifications are recorded when relevant.
- When `parent_managed_worktree` or `app_managed_worktree` was used: the integration-branch verifier has been rerun after integration. In `shared_checkout` mode the final E2E gate on the working integration head covers this.
- Every mission required for completion is `integrated` or explicitly superseded; every live task is `mission_recorded` with a PASS verifier, and no blocker, active or blocked mission/review worker, or open wave remains.
- The final integration head still descends from every recorded required mission integration SHA.
- Landing state is recorded: the verified integration head pushed to the run's own branch, or the run explicitly left local. `landing.continuity` is `preserved` at that integration head.
- In `integration_push` mode, local diff review passed before push and `pushed_head_sha` equals the integration head. Any newer local integration resets this gate. `pushed_head_sha` is a parent-attested record: the push itself is observed by the parent, not provable by the validators, which check it only for internal consistency and against the local branch.
- For current PLAN-v6 graph runs, every node is succeeded, skipped, or superseded with no retained blocker, and every edge is traversed, exhausted, or skipped; failed nodes must be routed or superseded, and no selector-ready work remains.
- When a primary journey exists, its required automated E2E check is PASS on the current head. Any replaced manual smoke records `not required - covered by current-head E2E`; uncovered or environment-specific smoke remains required.
- When a worktree mode was used: manual worktree/branch cleanup is completed under its exact authorization or explicitly deferred, and app-managed platform lifecycle is recorded separately. In `shared_checkout` mode the worktree step is `not_applicable`; the primary checkout is never removed.

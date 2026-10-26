# Verification Gates

Use this reference to define task, mission, integration, and UI acceptance.

The managed ladder below follows the declared graph and selector. Direct source maintenance may overlap resource-safe read-only review and final regression on one unchanged candidate, but must collect both results before closeout. That scheduling choice never bypasses a managed dependency or reuses evidence after a repair.

For new delivery work, also apply `delivery-acceptance-contract.md` and `bounded-enhancement.md`. Freeze required TEST/scenario/platform/auth expectations before running tests, prepare only authorized isolated synthetic fixtures, and validate the evidence register before final acceptance. Managed plans declare this check as an always-run final verifier with its graph node; direct work runs it without manufacturing PLAN/RUN. Legacy frozen runs retain their original schema and evidence, never retroactive PASS.

## Verification Ladder

Applicable eval gates run `check_eval_acceptance.py` under `eval-acceptance-contract.md` before delivery acceptance. Recompute both full reports from the frozen PRD policy at exact clean H2; inspect judge/tool and clean-checkout provenance independently. A quality rate never weakens all-required functional TEST acceptance.

Use the smallest reliable proof first:

```text
1. Reproduce or define the observable target.
2. Identify the smallest deterministic check.
3. Run affected task and worker checks from parent-observed changed files.
4. Integrate serially into the resolved integration branch; run the mission integration surface and only real cross-mission checks, with seam verifiers selected from the merge diff.
5. Run one combined review on the unified head.
6. Make one consolidated repair and one targeted re-check.
7. Fix the candidate SHA, then run one planned broad regression, browser E2E, and visual/UI validation suite on that head.
8. Record evidence with commands, exit codes, artifacts, traces, screenshots, metrics, or approval.
9. If deterministic checks are impossible, use structured review and name residual risk.
```

For RUN-v11 screenshot evidence, the order is immutable Git blob read, safe byte-based decode, then `artifact_sha256` comparison. Earlier RUN schemas: `legacy-pins.md#run-schemas-before-v11`.

## Review Topology

Default `review_policy: final_candidate`. One review node on the unified candidate carries every lens its diff needs, listed in `review.lenses`: `frontend_code` or `backend_code` for changed code, `visual` with `required_tools: ["chrome_devtools"]` when the PLAN has `ui_surfaces`, and `security` when the plan's security policy requires it. Its `review.type` is the widest lens (security, visual, frontend_code, backend_code). It binds the exact `integration_head_sha`, loads `code-security-review` for the security lens, and returns one consolidated finding set. A mission integrates after `worker_passed` and the Worker Result Gate; no mission review precedes it.

One reviewer per candidate. Parallel reviewers on one candidate or surface group need an explicit owner request and return one consolidated finding set through the parent; they never each start a repair loop.

Finding triage. A reviewer separates blocking findings from non-blocking notes. A blocking finding is a defect against accepted scope, a TEST obligation, security, or correctness. A non-blocking note is style, decorative wording, a suggestion, or backlog. Only blocking findings produce `fix_required`; a PASS records notes through `record-review-attempt --note`, and the notes go to the backlog or the Epic. Security findings of severity critical/high are always blocking.

Make one consolidated repair, then one targeted re-check on the new SHA. The security lens re-binds to the new SHA with full scope. A failed re-check stops at `blocked`.

Re-check scope. The re-check packet carries the prior reviewed head, the prior blocking findings, the prior notes, and the repair range `<prior>..<head>` with its name-status list and diff. The reviewer returns a verdict per prior finding (resolved / unresolved / superseded) and inspects the repair range and its direct consumers. The security lens stays at full scope. Anything else is a note, unless it is a validated security finding or a correctness defect inside the repair range.

Pre-review repair gate. Before a re-check is reserved, or on the direct route dispatched, the author presents the focused verifier PASS at the new head and, for a failure family, the family's acceptance matrix with each equivalence class exercised. A repair without that evidence is not dispatched for review; it returns to the author. This is author evidence, not a review attempt.

Environment-blocked attempts. An attempt the reviewer could not perform — checkout or branch mismatch, sandbox permission denial, unavailable runtime, interrupted before inspection — is recorded `blocked` with `blocker_class: environment` and evidence. It does not consume the node's attempt or the repair budget; the transition refunds the node attempt, at most two per review lineage per RUN (a successor node in the same lineage shares the count), and keeps the attempt log and worker entry. It is not a review verdict and never a PASS.

Scope-disjoint carry-forward. On the direct route only, a review PASS bound to SHA X, including its security lens, stays valid for a descendant commit Y when every path changed between X and Y is outside the review scope and non-executable: docs, Epic, evidence, README. Record the origin PASS SHA, the X..Y path list, and the reason; never relabel it as a fresh review. Any code, config, dependency, migration, or toolchain change is a new candidate. Managed runs do not use this rule: a bookkeeping child binds through `reconcile-coordination-head`, and any other head change invalidates every gate PASS (`execution-state-model.md`).

Security lens applicability. On the direct route, the security lens is required when the diff touches executable code, configuration, dependencies, CI, infrastructure, secrets handling, or data access. A diff that touches only documentation, copy, Epics, evidence records, PLAN/RUN bookkeeping, or design-source text records `security: not_applicable (<reason>)` with the changed path list as evidence instead of `UNVALIDATED`. Managed PLANs keep `security_review.status` as today.

Review count budget. Record the planned review points for the round: reviewer dispatches, not self-checks. Give the reason for each point beyond one combined review plus one re-check.

`review_policy: per_mission`, which an absent field means on older plans, or an owner request or recorded high-impact risk, adds exact-head pre-integration reviews. Only then do the tree-identical and merge-chain skips below apply. Security never skips and never reuses.

## Gate Levels

Task gate:

- Proves one task changed the intended behavior.
- Runs focused checks selected from parent-observed changed files when the verifier declares `selection.mode: "changed_files"`; omitted selection metadata means `always`.
- Must pass before a worker result can become `worker_passed` and before a task commit when commits are authorized.
- For a touched security boundary, includes the declared negative test proving denial and no unauthorized side effects. A missing upstream PRD/TEST decision is `contract_gap`; unavailable required tooling or evidence blocks the task.
- After it passes, create at most one coherent task commit using `commit-convention.md`; split the task first when independent outcomes remain.
- Apply the project's File Size Checkpoint to touched modules. At 500 lines, review whether a module has more than one responsibility; split when that improves ownership and verification, otherwise record why it stays together. This is not a hard limit. A missing responsibility review blocks the task, not the line count itself.

Worker mission gate:

- Proves all task acceptance rows for one mission.
- Runs only applicable focused worker verifiers when changed-file selection is declared. Worker-reported paths never control applicability; the parent recomputes it from the observed diff.
- Produces a worker result candidate; it does not satisfy downstream dependencies by itself.

Current task and worker verifiers declare explicit host execution.
Commands run fresh in the bound checkout with exact candidate, command identity, logs, exit status and source/Git guards.
No container runtime or image policy is part of current readiness or result evidence.

Non-runtime node gate:

- Applies to `approval`, `external_wait`, `lifecycle`, and deterministic (`local_command` or `harness_parent`) verifier nodes.
- The parent first reserves the selected attempt with `reserve-node-attempt`, then performs the check, waits for the external state, or runs the lifecycle side effect outside the RUN lock.
- `record-node-result` closes only the matching reserved attempt, requires evidence, traverses declared route edges, and derives the graph phase from the outcome (`pass` → `succeeded`; `blocked`/`contract_gap` → `blocked`; `fix_required`/`retryable_failure` → `failed`). A lifecycle result is an evidence receipt; the transition never runs the action itself.
- If the non-runtime executor is interrupted, record `blocked` and the blocker through `record-node-result`; preserve the attempt evidence and use a fresh attempt for any retry.

Worktree pre-integration review gate (`per_mission` only):

- Runs after worker checks and before the parent merges that mission head.
- The parent dispatches an independent read-only reviewer bound to the exact current worktree head and records a terminal `review_workers[]` PASS (reviewer, decision, findings, evidence) whose preintegration-stage review node covers the mission and whose `reviewed_sha` equals that head. The mission worker never creates its own reviewer.
- Requires zero unresolved blocking findings. Any repair changes the head and invalidates the prior review.
- Under `per_mission` it is the gate that moves `worker_passed` to `integrating`; under `final_candidate` the Worker Result Gate alone does.

Mission integration gate:

- Runs after reviewed work lands on the exact non-protected run integration branch resolved from repository governance or the user's instruction.
- Runs that mission's declared `integration_verifiers` on the integrated head.
- Admit actual protocol-v2 output through repeatable `record-integration --verifier-result <absolute-external-json>` flags. Require fresh execution, captured streams, exact PLAN/RUN context, and complete declared PASS coverage. Existing valid retained evidence remains usable without flags.
- Bind host output to the live integration root, branch, candidate, tracked snapshots, and exact RUN/generated-tasks protected paths. Recheck source bytes and protected identities before the atomic RUN write. Reuse, duplicate input, retained-PASS replay, and another route's reservation are refused.
- When missions meet at a security boundary, integration checks cover the seam — enforcement, cross-mission trust/data flow, and failure/no-side-effect behavior — rather than repeating only per-task unit checks.
- Is the only gate that may transition a mission to `integrated` after the parent confirms the integrated SHA is reachable from the current integration head.

Platform handoff gate:

- Applies to a `platform-delivery/1` completion mission. Its selected integration verifiers run fresh, disable reuse, and annotate every upstream platform TEST ID.
- Retains the exact `mission_integration` PASS at that mission's `integrated_sha`. This retained PASS starts the next platform; `worker_passed`, a route, or a batch gate does not.
- Treats a later candidate as new proof. It reruns only the seam and final gates per Review Topology.

Batch integration gate:

- Runs the PLAN-level `batch_verifiers` after every selected wave has integrated serially.
- Uses `scripts/verifier_runtime.py` batch mode. Host verifiers require `parallel_safe: false` and run serially within that runner; independent workers may run host checks concurrently in separate worktrees. Task and worker gates use the same batch path.
- Contains only checks that need more than one integrated mission or shared contract. Do not repeat focused task suites here.
- Proves cross-mission behavior did not regress and blocks the next wave on failure.

Fresh integration review gate:

- Starts once every mission it covers has integrated serially into one integration branch. It uses new parent-dispatched read-only reviewer attempts on the exact `integration_head_sha`; a mission writer is never a reviewer. Lenses, repair and re-check follow Review Topology.
- Under `per_mission`, skip the dispatch when the integration head's tree is byte-identical to a tree a pre-integration review of the same review type already passed: the head is literally that reviewed commit, or it is a merge commit whose recorded `integration.integration_tree_sha` equals that review's recorded `review_workers[].tree_sha`. Record the node as `skipped`; the validator rejects that phase unless the matching PASS exists on that exact SHA or an identical tree. Run `python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> skip-integration-review --node-id <id> --worker-id <id>` for the live-Git tree check and skip record. `record-review-attempt --tree-sha <sha>` persists the reviewed tree on PASS; the global `--repo-root <root>` before that subcommand can derive it from Git.
- Under `per_mission`, a `frontend_code` or `backend_code` review also skips when the head is a merge chain of reviewed heads. Omit `--worker-id` from the same command; it walks first parents from the head and records `integration.reviewed_merge_chain`. Each link is a clean automatic merge of an exact mission head that passed every planned pre-integration review of its mission. That side changes only its mission's write scope, and the linked write scopes do not overlap. The walk ends at a reviewed head or at a base that every reviewed head contains. A conflict, a manual merge edit, an overlapping scope, an unreviewed head or commit, or a missing proof means the review runs. A `visual` review judges the rendered head, so only the tree-identical skip applies to it. Security review never skips.
- Otherwise the review runs. Under `per_mission` the packet lists the already-reviewed mission heads and the pass focuses on what the combination changed; under `final_candidate` it reads the whole candidate diff.
- A repair changes the candidate SHA and invalidates current integration-stage PASS coverage. Historical reviews keep their original SHA; never relabel an old PASS as new evidence.

Final/current-head gate:

- Runs the one planned broad regression, browser E2E, and visual/UI validation suite only after the combined review and its one repair loop converge.
- Covers every `platform-delivery/1` TEST ID. Extra required shared-regression tests are allowed. Every annotated feature gate runs fresh on the exact integration head.
- Binds every PASS to the exact integration head. Any later code or configuration change invalidates the affected proof.
- Focused task, worker, and integration checks are not this broad suite. Plan the suite as cross-cutting checks that only the whole candidate can answer — build, browser E2E, migration, UI evidence — rather than a rerun of every focused suite already green on the same code. A gate that only re-executes a mission's own unit tests on an unchanged tree is repeated work; either give it changed-file selection against the plan write union, or drop it and rely on the task and worker gates that already covered it.
- If the broad suite fails or a repair changes the candidate, run the one targeted re-check on the new candidate before rerunning it; do not claim an exactly-once history when the candidate changed.
- Delivery ends on this local evidence. The harness never waits for remote CI or remote review.
- Harness 0.38+ closes this gate locally at candidate C and performs no RUN push. Archive and publication follow `branch-promotion-contract.md#managed-run-archive-before-promotion`.

E2E gate:

- Proves the primary user journey works through UI, API, auth/permissions, data, and error handling. When the matrix becomes materially difficult to scan or needs separate ownership, expand it into `assets/templates/E2E_VERIFICATION.template.md` and link it from `RUN.md`.
- Blocks final PASS while a required obligation is failed, blocked, or unvalidated. A named residual risk or next-round handoff does not turn it into PASS; an explicitly changed future scope is recorded separately.

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
| Security controls | a required trust boundary changed | unauthorized action denied with no unauthorized side effects | negative test or trace |
| Billing / entitlement | plan-gated feature changed | allowed/blocked cases pass | test or trace |
| Audit / observability | sensitive action changed | event/log/metric created | log/test output |
| Browser journey | UI or workflow changed | primary journey completes | trace/screenshot/log |
| Responsive layout safety | UI changed | every required breakpoint or size-class and state renders without unintended element overlap, clipping, occlusion, or horizontal overflow; intentional overlays match their named stacking, focus, safe-area, and dismissal behavior | viewport captures + browser geometry/reviewer evidence |
| Console/network | browser surface changed | no relevant errors | console/network log |
| Accessibility | interactive UI changed | no serious blockers or named residuals | checker output |
| Visual design | initial design or active enhancement has an approved UI source | matches the PRD UI surface contract, the approved HiFi surface (pinned legacy contracts: `legacy-pins.md#legacy-ui-contracts-before-059`), and active visual source (required design-system package, including frozen derived HTML for `design-system/4`, or approved page-faithful target) within stated tolerance; routine maintenance checks the current accepted product and effective requirements | screenshots or human approval |
| Page-to-PRD conformance | an initial or enhanced route has a `PRD.md` `UI-*` entry and a matching copy-complete HiFi page (current `ui-design/3` or retained `ui-design/2`); a pinned legacy contract follows `legacy-pins.md#legacy-ui-contracts-before-059` | the built route matches PRD behavior and the affected HiFi region order, grouping, element inventory, states, responsive rearrangement, actions, exact static/action/feedback/alternate-state wording from its `ui-hifi-copy/1` copy, and dynamic source/order/format/count/length/fallback contracts at every required target; no unintended overlap, clipping, occlusion, or horizontal overflow; routine maintenance checks current affected behavior and regression consumers without regenerating historical HiFi | screenshots + browser geometry/reviewer note |
| UI contract check | `design-system.json` exists and the Design System Need Gate is `required` | `python "<delivery-harness-skill-root>/scripts/check_ui_contract.py" --registry <design-system.json> --repo-root <root> --path <product-source-dir>` (default: current working directory) reports no violation against the product's real source; token and primitive source declarations resolve by exact normalized repo-relative identity, not filename suffix; a run that analyzed zero files is not a pass, and a `--rule`-filtered run is not a contract-clean signal; source roles come only from the frozen `design-system.json`, so a `--token-source` or `--primitive-source` run prints `NOT CONTRACT-CLEAN` and exits non-zero | checker output |
| Design-system pair check | the active initial/enhancement visual route requires a current pair | `python "<design-system-compiler-skill-root>/scripts/check_design_system_pair.py" --markdown <design-system.md> --registry <design-system.json> --repo-root <repository-root> --require-filled` exits 0 against the frozen pair, run from the repository root and never with `--write`; a failure is a stop condition per `contract-and-traceability.md`. A retained historical pair in routine maintenance is not revalidated against a later accepted PRD solely because it exists; preserve its bytes and check the current product instead | checker output |
| Content contract conformance | a product component renders contract-governed content | every field in `design-system.json`'s `requiredContentOrder` renders, in that order — those fields never drop; limits, formats, empty and long-content rules respected | screenshot or content review |
| State matrix coverage | a UI route changed | every state in the required pair's `stateMatrix`, or in the PRD UI surface and approved target scope when the pair is `not_required`, is captured, listed as legacy `<state>:n/a`, or accounted for by validated `design_coverage` at every required viewport or size class | `ui_evidence` rows |
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

Parent-observed changed paths are literal repository-relative filenames, including dynamic routes such as `[slug]`, `[...slug]` and `[[...slug]]`. They are not scope patterns. Absolute paths, traversal and non-canonical separators remain invalid; write-scope declarations retain their separate restricted grammar.

The parent supplies normalized, repository-relative observed paths to `select_verifiers.py`. A targeted verifier is `not_applicable` only when no observed path matches its exact path or `/**` subtree. Invalid or incomplete parent observations fail safe by requiring every declared verifier.

Pillow is imported lazily by the UI-evidence path. When it is unavailable, return a targeted UI-evidence decoding error without preventing non-UI CLIs from starting. RUN-v11 screenshot checks decode the artifact from the accepted Git `head_sha`, not from a mutable working-tree copy.

Every applicable declared verifier requires an explicit execution mode. Host mode runs the declared argv in the bound checkout with the project toolchain and current user permissions. It retains command identity, cwd, exact SHA, logs, exit status, timeout and source/Git checks. It allows ignored build output but rejects changed tracked source or protected Git/coordination state; it does not automatically reset or clean up. Host verifiers execute serially within one runner and never reuse cached results. This is not a claim of network or filesystem confinement. Missing, container, `live`, and `git_snapshot` modes remain invalid in current tools. Browser, external service, migration, and mutable-environment operations retain their separate routes and action authorization.

Before the final source/Git checks, host execution ends its owned process group or job after success, failure, or timeout. Process ownership setup or cleanup failure cannot produce PASS. Windows starts the command suspended, assigns it to a Job, then resumes it. POSIX uses a new process group; host commands must stay in that group and must not daemonize with `setsid` or `setpgid`. Commands that need to escape that lifetime need a separately authorized managed service with its own finite lifetime. This manages verifier lifetime; it does not grant filesystem or network confinement.

A parent-owned batch/final graph verifier also carries the reserved node/attempt nonce and Git guard emitted by `reserve-node-attempt`. The runtime verifies the exact branch, HEAD, clean tree, and tracked-file fingerprint before and after execution. RUN and its declared generated `docs/tasks.md` view are coordination exceptions to dirty status, not integrity checks: their bytes and file identities are snapshotted across execution, starting SHA-256 values are attested, and `record-node-result` rehashes both before accepting evidence. Hand-authored or undeclared views and product dirt still block dispatch. A different checkout, replayed nonce, retargeted request, checkout drift, protected coordination-file change, or request/result artifact inside the reviewed checkout is rejected.

New local verifier declarations use:

```json
{"execution":{"parallel_safe":false,"resources":[],"isolation":"host"}}
```

Host declarations grant no dependency installation, network side effect or publication authority.
Provision the project environment under its existing authorization before verification.
On Windows, use native executables with argument arrays; do not wrap arbitrary commands in a shell.

The runtime decides PASS from exit code 0 alone.
Write `pass_signal` as `exit 0`; give any additional condition its own verifier argv.
Keep request and result artifacts outside the reviewed checkout.
Every execution key binds its immutable context, exact head, command, cwd, host executable identity and source/Git inputs.
Current verifier commands always execute fresh. Historical container/cache protocols use their [exact pinned bundle](legacy-pins.md#container-verifiers-before-066).
Retained evidence keeps its original SHA and origin; never relabel it as a fresh execution.

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

For every PLAN surface with `evidence_gate: required`, capture each planned product state and applicable `design_coverage` condition at every declared responsive target. Exclusions make no screenshot.

Capture the full matrix once on the final candidate; mission-head captures are author evidence, not `ui_evidence` rows. Current RUN-v11 `ui_evidence` records the surface ID, route, breakpoint, state, repo-relative image path under `docs/goal/evidence/`, lowercase SHA-256, exact integration head SHA, and status. Rows additionally record the PLAN `capture_mode`-compatible `capture_method` and a complete immutable `target_comparison`: `baseline`, exact `authority_sources` path/hash identities, a real hashed `baseline_artifact` image under `docs/goal/evidence/`, its `baseline_artifact_sha256`, verdict, and differences. The closeout validator checks the matrix, current-head binding, file existence, non-empty image signature, and hash. Every row also records `layout_check`: `pass` from a real-browser DOM geometry scan at that breakpoint and state — no unintended element overlap, clipping, occlusion, or horizontal overflow over visible peers, containers, and viewport bounds; `fail — <selectors>` records the offending elements and blocks the gate until the surface is repaired and the entry recaptured; `manual — <basis>` records a labeled manual review or native UI-test layout assertion; `n/a — <reason>` records why no geometry check applies. A `layout_check` value — like a `deviation_ledger` citation or a `ui_impact_summary` row — is a recorded attestation, not a validator-proven fact: the validators prove completeness and shape, never that the scan ran or that a citation is true, so each attestation names a verifiable anchor (`ui-design.md` clause, delta ID, or manual basis) a reviewer can check. A screenshot alone never satisfies the layout check.

For a route whose `UI-*` entry records SEO metadata, the same evidence set includes the rendered `<head>` on the integration head: its `<title>` and meta description match the PRD record. A mismatch is a failing check, not a style preference; a route with no PRD SEO record is a contract gap routed to `product-definition-builder`, not a verifier skip.

### Capture Mechanism By Platform

Parity screenshot filenames include a SHA-256 of the exact surface, route,
breakpoint, and state tuple. Display tokens alone are not unique: `/foo/bar`
and `/foo-bar`, or names differing only in case, must retain separate files.
Consumers use the paths recorded in the capture manifest.

Only the capture mechanism changes with the resolved platform; the evidence discipline above is identical everywhere. Every platform must still produce a real binary screenshot under `docs/goal/evidence/`, record a lowercase SHA-256, bind it to the exact integration head, and cover the full breakpoint-by-state (native: device/OS-by-state) matrix. Placeholder, fabricated, or hand-drawn images never satisfy the gate.

For a hosted-browser surface (`capture_mode: hosted-browser`), capture through a browser: Playwright/headless-browser screenshots, browser DevTools, or the `agent-browser` CLI, at that surface's planned viewports. The route-by-breakpoint-by-state matrix and the runbook's hosted-browser UI Evidence columns apply. `scripts/parity_capture.py` captures only this hosted subset in a hybrid plan; extension, native, and desktop groups are reported as platform/manual groups rather than rejected or approximated with a URL.

For a browser-extension mission (`capture_mode: browser-extension`), use extension-aware browser automation against the installed extension and its declared contexts. Record `capture_method: browser-extension`; do not substitute a hosted URL or `--base-url` parity capture.

For a native iOS/Android/Flutter/macOS/Windows mission (`capture_mode: native`), capture through the platform's own UI-test tooling instead of a browser, using the device/OS-by-state matrix and the runbook's native UI Evidence columns. Record `capture_method: native-ui-test` or `manual-native`:

- iOS: iOS Simulator screenshots produced by `xcodebuild test` running XCUITest cases.
- Android: Android Emulator screenshots produced by Espresso via `./gradlew connectedAndroidTest`.
- Flutter: integration-test screenshots via `flutter test integration_test/` (or `flutter drive`), captured for each native target in scope.
- macOS desktop: XCUITest screenshots from `xcodebuild test`.
- Windows desktop: WinAppDriver or a .NET UI-test framework driving the app.
- Fallback: when no UI-test tooling exists for the project yet, a manually captured Simulator/Emulator/device screenshot is acceptable, recorded with the same path, hash, and head binding and labeled as a manual capture.

For a desktop mission (`capture_mode: desktop`), use the platform desktop UI-test tooling or a labeled manual desktop capture. Record `capture_method: desktop-ui-test` or `manual-desktop`; desktop evidence never uses a hosted URL or browser parity helper.

When the design source's mockup HTML is styled to a different platform than the resolved target (for example web-styled mockups for a native mission), do not silently implement against it or guess the capture mechanism; stop and ask per `contract-and-traceability.md`'s mismatch condition.

### Final UI Acceptance

New direct and managed UI work uses one independent read-only acceptance for parity and page quality on the exact candidate SHA.
The parent or author prepares the required captures and automated results before review.
One reviewer inspects both components below using the same current evidence and returns one consolidated finding set.
Record parity comparisons and page-quality findings separately within that acceptance result; both must pass.
Do not schedule a second page-quality review after parity or another parity review after page quality.

For managed work, include this acceptance in the applicable planned `visual` review on the same candidate.
New consolidated visual nodes include `ui_acceptance` in their existing `required_evidence` list.
Under `per_mission`, an earlier visual review may declare the same contract.
Record `ui_parity:<comparison anchor>` and `ui_page_quality:<quality-report anchor>` in that attempt's evidence.
The parent inspects both retained anchors; their presence alone does not prove the checks occurred.
Tree-identical reuse also requires coverage of the target's missions, semantic scope, required evidence and tools.
An unmarked or incomplete earlier PASS cannot replace a marked acceptance.
Do not add another reviewer node or reset its lineage budget.
Frozen RUNs retain their pinned contracts until an authorized task boundary; never add the marker to a completed review (`legacy-pins.md#legacy-ui-contracts-before-059`).

#### Final Visual Parity Loop

The parity component covers every applicable UI surface and binds its evidence to the exact candidate head.
Managed coverage includes every PLAN `ui_surfaces` entry.
Compare the implementation against its approved visual authority in both conformance modes.

For each planned route-by-breakpoint-by-state combination:

- **Target-conformance mode (hosted-browser HTML target):** run `scripts/parity_capture.py --plan <PLAN.md> --reference <approved design-reference HTML> --base-url <app origin> --route-map <route-map.json>` only when every PLAN UI surface has `capture_mode: hosted-browser`. It enumerates product states and validated design conditions from PLAN `ui_surfaces`, captures the reference render and the implemented page at the same viewport as `-target.png`/`-actual.png` pairs under `docs/goal/evidence/parity/`, runs a DOM geometry probe per app page for the `layout_check` attestation, and writes `manifest.json` plus a self-contained `parity-board.html`. The route map is a small JSON the parent writes once per run: each route's reference selector plus optional `app_eval`/`reference_eval` state and condition setup; `long-content` needs both sides, and motion media is applied before navigation and restored after success or failure. A ready state captures without a trigger, other states are captured only when triggered and otherwise listed as manifest gaps for the reviewer. Judge every pair on the board item by item and record the verdicts as the `target_comparison` rows below. Manual capture remains valid when the CLI is unavailable. Compare layout, element inventory, and observable visual values item by item within `ui-design.md`'s recorded tolerance. The reference render is the comparison source, not an aspiration.

For `capture_mode: browser-extension`, `native`, or `desktop`, do not run URL parity for that surface and do not claim hosted parity. Capture the approved target and implemented surface with the platform-specific extension/native/desktop tooling (or an explicitly labeled manual capture), using that surface's responsive targets, bind both to the accepted Git head, and record the platform capture method and exact authority source in each `target_comparison` row. A hybrid plan must keep each UI-* surface's release surface, class, responsive set, and capture method explicit.

Store comparison pairs under `docs/goal/evidence/`. Automated captures use `parity/<label>-<tuple-sha256>-target.png` and `parity/<label>-<tuple-sha256>-actual.png`; use the exact paths recorded in `manifest.json`.
- **System-conformance mode:** the baseline is the frozen design-system package. For `design-system/4`, the baseline includes the frozen derived HTML. The comparison evidence is a clean `scripts/check_ui_contract.py` run against the product's real source at the integration head (a zero-file, `--rule`-filtered, `--token-source` or `--primitive-source` run is not a baseline) plus the full screenshot matrix checked against the pair's tokens and variants.

Record the comparison on each `ui_evidence` row as a `target_comparison` object: `baseline` (`html_target` or `design_system`), `baseline_artifact` (the reference-render image path under `docs/goal/evidence/` for `html_target`, or the contract-check evidence key for `design_system`), and `verdict` (`pass` or `deviation`). A `deviation` verdict lists every observed difference, and each difference either falls inside `ui-design.md`'s allowed deviations or triggers repair.

Record accepted deviations in the RUN `deviation_ledger`. Every `deviation` difference has one ledger row (`surface_id`, `route`, `breakpoint`, `state`, `difference`, `citation`) citing the `ui-design.md` clause that admits it. A difference that changes regions, states, actions, routes, or responsive behavior is structural drift and routes upstream. Repeated differences cite the frozen design-input delta; accumulated in-tolerance drift never substitutes for a doc update.

Static screenshots never close a motion change. When a mission's diff touches transition, animation, duration, easing, or generated motion assets, its parity evidence adds a motion check row: the authority from `ui-design.md`'s Motion and Media Intent (plus its registered variant or approved target behavior), what the reviewer confirmed in normal and reduced motion, and the verdict. A motion change with no authority citation routes to `ui-design-builder` instead of passing on still images.

Repair cycle: a missing element, a structural difference, or any difference outside the recorded tolerance is not a `pass`. Repair the surface, recapture the affected matrix entries, and rebind the evidence to the new integration head SHA. A parity repair is an ordinary candidate-changing repair: it invalidates the final-gate PASS and every integration-stage PASS whose scope intersects the repair diff. The loop uses the one repair and re-check from `gen-verify-correct.md`; it does not add attempts on top of that budget. After a failed re-check, report the remaining differences as-is; never widen the tolerance or relabel an unresolved difference to close the run. Screenshots from an older head or placeholder images never satisfy the loop.

#### Final Page-Quality Pass

The same acceptance reviewer checks each delivered route.
When parity passes within tolerance and the HiFi evidence is current, the HiFi review already proved heuristic UX, accessibility and responsive layout.
The pass then covers only implementation-only properties: performance, the no-JavaScript path, console and network errors, and the focus handling and accessible names the framework renders.
HiFi evidence is current when PLAN freezes the approved HiFi entry that Visual Approval and its passing review bind.
Otherwise, including routine maintenance and legacy wireframe sources, the pass also checks heuristic UX, accessibility and responsive/device behavior.
This page-quality pass is part of Final UI Acceptance, not a later review or another aesthetic grading wave.
Impeccable is not the default for this node.
Its pinned workflow has disclosed subagent, browser/server, snapshot-write and optional-download side effects.
It may run only as a separately authorized UI-quality workflow.
Its report may provide evidence without replacing the independent Harness reviewer.

- Findings are ordinary review findings. A blocking defect enters the same one repair and re-check as a parity repair; the pass adds no review attempts of its own. Record the pass, every finding, and its verdict as evidence rows bound to the integration head, and never relabel an unresolved finding to close the run.
- Consolidate parity and quality defects into the one repair.
- Retain required matrix coverage and check both components for regressions. Do not reopen direction selection or start a broad search for taste preferences.
- The pass verifies quality, not direction. A finding that conflicts with frozen product behavior returns to `product-definition-builder`; a finding that conflicts with `ui-design.md`, the approved HiFi (or a pinned legacy wireframe), or the active visual source returns to `ui-design-builder`. Neither authorizes a local change.
- Read-only reviewer actions only. The pass never runs a bound skill's build, init, document, snapshot, download, or live-server flows, and never creates `PRODUCT.md`, `DESIGN.md`, `.impeccable/`, or another competing authority in the repository.
- If the bound skill is unavailable in the delivery environment, record the gate `UNVALIDATED` with the named residual risk; it blocks final completion unless the user explicitly accepts the descoped gate.

## UX Direction And Usability Evidence

Keep these proofs separate:

| Proof | Question answered | Valid evidence |
|---|---|---|
| UI Design Intake conformance | Did the result follow the named human owner's approved UI direction? | `ui-design.md`, approved target comparison, implementation review, screenshots |
| Behavioral completion | Can the system technically complete the critical task? | deterministic browser E2E, API/data assertions, trace |
| Accessibility | Can required users perceive and operate it under the declared standard? | automated checks plus required keyboard, assistive-technology, or human evaluation |
| Usability | Can representative users understand and complete the task with the intended effort and confidence? | prototype or implementation testing with representative users, or another explicitly approved research method |

UI owner approval proves only direction conformance. Agent judgment, heuristic review, screenshots, and automated E2E may find problems, but none of them alone is representative-user usability evidence.

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

Every new managed PLAN records `security_review.status` as `required` or `not_applicable`; the latter needs a concrete non-code reason. New RUN generation and validation reject an omitted security-review policy. A required policy declares `security` in `required_reviews`. The `security` lens sits on an integration-stage review covering every mission, usually the one combined final review, with review scope containing each covered mission's complete write scope. The Harness parent resolves the project's `code_security_verification` Skill Binding, reserves the review attempt, and dispatches a fresh sibling reviewer with `code-security-review` against the exact `integration_head_sha`.

A required policy may also list `security_review.required_checks`: unique batch or final verifier IDs that must pass before the review. Each ID must resolve to exactly one `local_command` or `harness_parent` graph verifier with a dependency path into every security node. Reservation refuses the review unless each ID has exactly one PASS execution with exit 0 at the reviewed head. The review packet lists each ID with that execution's `execution_key`, and the security result's `checks` must equal the PLAN list.

Early controls and negative tests are development evidence, not a substitute for this final independent review. Do not automatically install scanners, probe production, enable network access, or add delegated reviewers. An optional scanner that is absent is recorded as an explicit coverage gap; a required unavailable scanner, advisory source, or reviewer blocks.

The security reviewer is read-only, never delegates, and reports all validated findings in one pass. It receives no write scope, commit authority, scanner-install permission, network permission, or live-target penetration authority. Optional local scanners may add evidence; a required but unavailable scanner, advisory source, or independent reviewer blocks the gate rather than producing a partial PASS. Completion passes the result as `--security-result`; the transition validates and retains its exact review type, decision, SHA, base, scope, exclusions, trust boundaries, tools, coverage, findings, and evidence. A security PASS must have an empty `exclusions` list; the current contract does not allow a PASS with narrowed or omitted coverage.

A security review is not eligible for `skip-integration-review`, even when a pre-integration code review covered a byte-identical tree. The unified security pass evaluates cross-mission trust boundaries and security-specific source-to-sink paths from a fresh context. PASS binds to the exact current integration SHA and declared scope. Any repair creates a new candidate and invalidates the security result and all downstream final-gate evidence. The one targeted re-check re-binds the security lens to the new SHA with full scope; no second security reviewer is dispatched before final validation.

Security reservation and completion recheck the live integration checkout before accepting the attempt: the exact integration branch and HEAD, clean status (allowing only the exact tracked RUN exception), and ancestry from the current batch base. A mismatch blocks the attempt. Required security nodes cannot be skipped, superseded, or replaced at closeout; a missing, skipped, stale, partial, blocked, or superseded security result prevents final PASS.

An interrupted security reviewer does not fabricate a structured decision. `reconcile-interrupted-reviews` retains a blocked worker without `security_result` only when the unique matching review attempt carries the `interrupted_review_reconciliation` receipt. The node returns to dormant and the run stays paused; the receipt cannot satisfy closeout. A later exact structured PASS from the current reviewer may close the gate while the receipt-bound historical worker remains. A PASS also needs at least one tool or manual source review recorded as `passed` or `findings`; skipped or unavailable tools alone are not review evidence.

The neutral PLAN template's combined final node allows one initial review and one targeted recheck (`max_attempts: 2`).
A covered parent-side repair uses the existing declared task and `reconcile-candidate-head` under its exact authorization.
Alternatively, predeclare the [optional repair-only mission](graph-orchestration.md#optional-repair-only-mission) before execution.
A first-review PASS leaves that untouched mission dormant; it does not block closeout.
A `fix_required` activates its single bounded repair, followed by normal result recording, integration and one targeted recheck.
A failed recheck stops; never reset attempts, hide the finding or dispatch another repair automatically.
Both routes review the actual repaired unified SHA with complete security scope.

## Failure Handling

Review packets are bounded previews. Both `render_review_packet.py` and `reserve-review-dispatch --packet-out` accept `--diff-artifact-out <new-checkout-external-path>` to retain the complete binary-capable diff. The packet binds its absolute path, SHA-256, byte count, fixed base/head and complete name-status inventory. Neither output replaces an existing file. A truncated packet requires reading the full artifact or the same fixed Git range and reporting uninspected paths or binary gaps before PASS. These instructions improve review input; retained result evidence does not mechanically prove path coverage or reviewer understanding. Security integration packets require fresh full-scope review and retain all original checks and exclusions rules. A sidecar failure after RUN persistence reports the durable reservation and requires a new output path before launch.

Apply `bounded-enhancement.md`: reuse existing exact authority for covered repairs instead of requesting repeated approval. At the stricter repair/graph limit, report verified and incomplete scope and hand remaining failures to the next round. Finishing the session is not successful delivery closeout; keep unfinished managed state paused/reconciled and do not archive it as passed.

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
- RUN-v11 batch/final-gate IDs exactly match PLAN, and every result is PASS with evidence on the exact integration head.
- Closeout runs `scripts/validate_harness_plan.py --design-system <path to design-system.json> --design-system-markdown <path to design-system.md>` whenever the Design System Need Gate is `required`, so both frozen hashes, the generated Markdown contract, compiler ID namespaces, all PLAN `DS-*` traces, `stateMatrix`, `design_coverage`, and the responsive set are cross-checked. `ui-design/3` joins also prove the frozen `design-system/4` derived HTML. In target-conformance mode, required screenshot coverage comes from the frozen PRD target scope and PLAN UI evidence rows; absence of both design-system arguments is expected only when PLAN does not freeze that pair.
- Closeout runs `scripts/validate_harness_plan.py --repo-root` to cross-check `integration_head_sha` against the live Git branch head before trusting any recorded head-bound PASS: RUN.md's own internal consistency never proves the recorded head still matches reality.
- Closeout passes `--prd <path to PRD.md>` whenever PLAN freezes a PRD source. The given bytes must equal that row's `content_sha256`; a source-revision-only row is not enough for this file join. The PRD-to-PLAN `UI-*` surface join and the `ui-design/3` joins under `--repo-root` follow `contract-and-traceability.md`; retained `ui-design/2` and legacy wireframe sources follow `legacy-pins.md#legacy-ui-contracts-before-059`. Managed maintenance instead freezes its task-record Epic, preserves historical design bytes, and still joins current PRD/PLAN route/state/targets. The transition write path runs the same applicable joins under `--repo-root`.
- Every skipped gate is justified.
- The RUN `deviation_ledger` is complete (`legacy-pins.md#pins-before-055` for older pins): every accepted parity deviation is recorded with its allowed-deviation citation, no accepted deviation changes structure, regions, states, actions, routes, or responsive behavior, and any repeated deviation on the same surface cites its frozen design-input delta. Each citation is a recorded attestation (see the attestation caveat in the UI Evidence Gate).
- The RUN `ui_impact_summary` is complete: every mission on a UI run carries its `none`/`style`/`structure`/`both` classification, and every `structure` or `both` row names the accepted upstream design-input delta. The row records the strongest task impact the mission's workers reported (ui-implementation-contract.md rule 8) and, like the ledger, is a recorded attestation.
- Every `UNVALIDATED` surface is named, and naming it does not substitute for passing when that surface is still required: Final PASS is blocked while any required `ui_evidence` row (or other required gate) is `UNVALIDATED`, unless the user has explicitly accepted it as descoped with a recorded reason. RUN-v11 re-reads the accepted Git blob at the recorded head, so a working-tree mutation cannot replace or satisfy that evidence.
- Evidence paths exist. Required UI evidence is a real screenshot for every planned breakpoint-by-state combination, bound to the integration head and matching its recorded SHA-256; for RUN-v11, existence and decoding are checked in the accepted Git commit/ref rather than the working tree. Accepted non-file evidence applies only to gates that do not require screenshots. Every required row also carries a non-failing `layout_check` result, and a PASS row with a failed layout check never closes the run.
- Baseline and skipped-check justifications are recorded when relevant.
- When `parent_managed_worktree` was used (historical app-managed execution follows its exact pinned bundle): the mission integration verifiers passed on the integrated head. The one full run on the candidate is the only full run; in `shared_checkout` mode the final E2E gate on the working integration head covers this.
- Every required reached mission is `integrated` or explicitly superseded, with recorded passing tasks and no blockers, active/blocked workers or open wave. An untouched repair-only mission behind the final review's untaken route may remain queued with dormant tasks; never mark it as executed.
- The final integration head still descends from every recorded required mission integration SHA.
- Landing is `local_only`: `landing.continuity` is `preserved` at C, `pushed_head_sha` is null, push authorization is false, and no push lifecycle node exists (`legacy-pins.md#pins-before-055`).
- Archival is post-closeout. A must pass archived PLAN/RUN validation, receipt verification and exact C-to-A relocation/allowlist checks. It inherits C's review, security and gate evidence when the C-to-A diff touches only the archive allowlist (`branch-promotion-contract.md#managed-run-archive-before-promotion`); it never changes the archived RUN.
- For current graphs, every reached node is terminal with no retained blocker and every reached edge is terminal. Untaken routes may leave their exclusive repair subtree dormant. No selector-ready work remains; an activated failed repair cannot use this exception.
- When a primary journey exists, its required automated E2E check is PASS on the current head. Any replaced manual smoke records `not required - covered by current-head E2E`; uncovered or environment-specific smoke remains required.
- When a worktree mode was used: manual worktree/branch cleanup is completed under its exact authorization or explicitly deferred, and app-managed platform lifecycle is recorded separately. In `shared_checkout` mode the worktree step is `not_applicable`; the primary checkout is never removed.

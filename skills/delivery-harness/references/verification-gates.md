# Verification Gates

Use this reference to define task, mission, integration, and UI acceptance.

The managed ladder below follows the declared graph and selector. Direct source maintenance may overlap resource-safe read-only review and final regression on one unchanged candidate, but must collect both results before closeout; this never bypasses a managed dependency or reuses evidence after a repair.

For new delivery work, also apply `delivery-acceptance-contract.md` and `bounded-enhancement.md`: freeze required TEST/scenario/platform/auth expectations before running tests, prepare only authorized isolated synthetic fixtures, and validate the evidence register before final acceptance. Managed plans declare this check as an always-run final verifier with its graph node; direct work runs it without manufacturing PLAN/RUN. Legacy frozen runs keep their original schema and evidence, never retroactive PASS.

## Verification Ladder

Applicable eval gates run `check_eval_acceptance.py` under `eval-acceptance-contract.md` before delivery acceptance. Recompute both full reports from the frozen PRD policy at exact clean H2; inspect judge/tool and clean-checkout provenance independently. A quality rate never weakens all-required functional TEST acceptance.

Use the smallest reliable proof first:

```text
1. Reproduce or define the observable target.
2. Identify the smallest deterministic check.
3. Run affected task and worker checks from parent-observed changed files.
4. Integrate serially into the resolved integration branch; run the mission integration surface and only real cross-mission checks, with seam verifiers selected from the merge diff.
5. Run one combined review on the unified head.
6. Make one consolidated repair and one targeted re-check; after the re-check, remaining defects enter the Isolated Repair Protocol.
7. Fix the candidate SHA, then run one planned broad regression, browser E2E, and visual/UI validation suite on that head.
8. Record evidence with commands, exit codes, artifacts, traces, screenshots, metrics, or approval.
9. If deterministic checks are impossible, use structured review and name residual risk.
```

For RUN-v11 screenshot evidence, the order is immutable Git blob read, safe byte-based decode, then `artifact_sha256` comparison. Earlier RUN schemas: `legacy/legacy-pins.md#run-schemas-before-v11`.

## Review Topology

Default `review_policy: final_candidate`. One review node on the unified candidate carries every lens its diff needs, listed in `review.lenses`: `frontend_code` or `backend_code` for changed code, `visual` with `required_tools: ["chrome_devtools"]` when the PLAN has `ui_surfaces`, and `security` when the security policy requires it. Its `review.type` is the widest lens (security, visual, frontend_code, backend_code). It binds the exact `integration_head_sha`, loads `security-review.md` for the security lens, and returns one consolidated finding set. A mission integrates after `worker_passed` and the Worker Result Gate; no mission review precedes it.

Domain lenses. A PLAN may add `domain:<field>` entries to `review.lenses` from the PRD Ambition Range rows marked `review lens`; the Growth Contract's Range crew may supply `domain:seo`, `domain:aso`, and `domain:growth` lenses when the PRD's Growth Contract requires those discovery surfaces. The combined reviewer applies that field's method or tool, not role-play. Domain findings share the triage and review budget and add no reviewer node. A domain lens never sets `review.type`.

One reviewer per candidate. Parallel reviewers on one candidate or surface group need an explicit owner request and return one consolidated finding set through the parent; they never each start a repair loop.

When a review packet exceeds the reviewer route's caps, the parent splits it into scoped calls over disjoint path groups of the same exact SHA ([General Runtime Adapter](runtime-adapters.md#reviewer-tools)) and merges the returned sets into one consolidated finding set under this section's finding triage and two-pass budget. This is one review point, not the multi-reviewer fan-out that needs an owner request.

Finding triage. A reviewer separates blocking findings from non-blocking notes. A blocking finding is a defect against accepted scope, a TEST obligation, security, or correctness; a non-blocking note is style, decorative wording, a suggestion, or backlog. Only blocking findings produce `fix_required`; a PASS records notes through `record-review-attempt --note`, and the notes go to the backlog or the Epic. Security findings of severity critical/high are always blocking.

Each candidate stage gets at most two independent review passes: the initial review and one targeted re-check, run on the new SHA after one consolidated repair. The security lens re-binds to the new SHA with full scope. After the re-check, every remaining or newly found defect enters the Isolated Repair Protocol; no owner decision opens another full review round.

Re-check scope. The packet carries the prior reviewed head, blocking findings and notes, and the repair range `<prior>..<head>` (name-status list and diff). The reviewer returns a verdict per prior finding (resolved / unresolved / superseded) and inspects the repair range and its direct consumers; anything else is a note unless it is a validated security finding or a correctness defect inside the range.

Pre-review repair gate. Before a re-check is reserved (on the direct route, dispatched), the author presents the focused verifier PASS at the new head and, for a failure family, the family's acceptance matrix with each equivalence class exercised. A repair without that evidence returns to the author undispatched. This is author evidence, not a review attempt.

Environment-blocked attempts. An attempt the reviewer could not perform — checkout or branch mismatch, sandbox permission denial, unavailable runtime, interrupted before a verdict — is recorded `blocked` with `blocker_class: environment` and evidence. It consumes neither the node's attempt nor the repair budget: the transition refunds the node attempt, at most two per review lineage per RUN, and keeps the attempt log and worker entry. It is not a review verdict and never a PASS.

Scope-disjoint carry-forward. On the direct route only, a review PASS bound to SHA X, including its security lens, stays valid for a descendant commit Y when every path changed between X and Y is outside the review scope and non-executable: docs, Epic, evidence, README. Record the origin PASS SHA, the X..Y path list, and the reason; never relabel it as a fresh review. Any code, config, dependency, migration, or toolchain change is a new candidate. Managed runs do not use this rule: a bookkeeping child binds through `reconcile-coordination-head`, and any other head change invalidates every gate PASS (`execution-state-model.md`).

Security lens applicability. On the direct route, the security lens is required when the diff touches executable code, configuration, dependencies, CI, infrastructure, secrets handling, or data access. A diff that touches only documentation, copy, Epics, evidence records, PLAN/RUN bookkeeping, or design-source text records `security: not_applicable (<reason>)` with the changed path list as evidence instead of `UNVALIDATED`. Managed PLANs keep `security_review.status` as today.

Review count budget. Record the planned review points for the round: reviewer dispatches, not self-checks. Give the reason for each point beyond one combined review plus one re-check.

`review_policy: per_mission`, which an absent field means on older plans, or an owner request or recorded high-impact risk, adds exact-head pre-integration reviews. Only then do the tree-identical and merge-chain skips below apply. Security never skips and never reuses.

## Isolated Repair Protocol

After the targeted re-check, every remaining or newly found defect enters this protocol instead of another global review.

Scope-bound carry-forward. The anchor is the latest full review of the candidate, PASS or `fix_required`; it inspected every path, so paths it did not flag carry forward. A `fix_required` anchor needs at least one scoped repair step before closeout, and a required security node needs a passing security result at the anchor or trust-boundary scoped security passes covering the chain. A scoped PASS from an isolated repair re-binds the candidate PASS for the repaired paths and their direct consumers; the anchor carries forward for the rest. This extends the scope-disjoint rule above to code paths on both routes. Record the origin PASS SHA, the repair path list, and the scoped PASS; never relabel the carried-forward PASS as a fresh full review.

One finding family becomes one bounded repair task:

1. The author fixes the family and runs the focused verifier selected from the changed files; the pre-review repair gate above applies before any review.
2. One scoped review covers the repair diff. The reviewer receives only the finding, the repair diff, and its direct consumers; the parent renders that packet with `render_review_packet.py`, which switches to the `## Scoped repair review` form when the reviewed head carries a recorded repair scope.
3. The security lens joins the scoped review only when the diff touches a trust boundary named in the PRD Security Requirements, or an auth, session, secrets, data access, dependency, CI, or infrastructure path. Otherwise the scoped review records `security: not_applicable (scoped repair outside trust boundaries)` with the changed path list.
4. A scoped PASS re-binds the candidate PASS under the scope-bound carry-forward above.
5. No full-scope re-review follows a scoped PASS. No Final UI Acceptance rerun happens unless the repair touches a UI surface, and then only that surface's matrix entries are recaptured and rechecked. Every other entry carries forward only while its render fingerprint is unchanged.
6. A scoped review does not consume the review node's attempts. Managed runs record it with `record-review-attempt --scoped`.
7. The broad regression and E2E suite runs once per candidate at the end. A failure there is an isolated repair; rerun only the failing suites plus the changed-file selection, never the whole suite.

## Gate Levels

Task gate:

- Proves one task changed the intended behavior.
- Runs focused checks selected from parent-observed changed files when the verifier declares `selection.mode: "changed_files"`; omitted selection metadata means `always`.
- Must pass before a worker result can become `worker_passed` and before a task commit when commits are authorized.
- For a touched security boundary, includes the declared negative test proving denial and no unauthorized side effects. A missing upstream PRD/TEST decision is `contract_gap`; unavailable required tooling or evidence blocks the task.
- After it passes, create at most one coherent task commit per `commit-convention.md`; split the task first when independent outcomes remain.
- Apply the project's File Size Checkpoint to touched modules: at 500 lines, review whether a module has more than one responsibility; split when that improves ownership and verification, otherwise record why it stays together. The count is not a hard limit; a missing responsibility review blocks the task.

Worker mission gate:

- Proves all task acceptance rows for one mission.
- Runs only applicable focused worker verifiers when changed-file selection is declared. Worker-reported paths never control applicability; the parent recomputes it from the observed diff.
- Produces a worker result candidate; it does not satisfy downstream dependencies by itself.

Non-runtime node gate:

- Applies to `approval`, `external_wait`, `lifecycle`, and deterministic (`local_command` or `harness_parent`) verifier nodes.
- The parent first reserves the selected attempt with `reserve-node-attempt`, then performs the check, waits for the external state, or runs the lifecycle side effect outside the RUN lock.
- `record-node-result` closes the matching reserved attempt with evidence and derives the graph phase from the outcome (`pass` → `succeeded`; `blocked`/`contract_gap` → `blocked`; `fix_required`/`retryable_failure` → `failed`). A lifecycle result is an evidence receipt; the transition never runs the action itself.
- If the executor is interrupted, record `blocked` and the blocker through `record-node-result`; preserve the attempt evidence and use a fresh attempt for any retry.

Worktree pre-integration review gate (`per_mission` only):

- Runs after worker checks and before the parent merges that mission head.
- The parent dispatches an independent read-only reviewer bound to the exact current worktree head and records a terminal `review_workers[]` PASS whose preintegration-stage review node covers the mission and whose `reviewed_sha` equals that head. The mission worker never creates its own reviewer.
- Requires zero unresolved blocking findings. Any repair changes the head and invalidates the prior review.
- Moves `worker_passed` to `integrating`; under `final_candidate` the Worker Result Gate alone does.

Mission integration gate:

- Runs after reviewed work lands on the exact non-protected run integration branch resolved from repository governance or the user's instruction.
- Runs that mission's declared `integration_verifiers` on the integrated head.
- Admit actual protocol-v2 output through repeatable `record-integration --verifier-result <absolute-external-json>` flags; each needs fresh execution, captured streams, exact PLAN/RUN context, and complete declared PASS coverage. Existing valid retained evidence remains usable without flags.
- When missions meet at a security boundary, integration checks cover the seam — enforcement, cross-mission trust/data flow, and failure/no-side-effect behavior — not only per-task unit checks.
- Is the only gate that may transition a mission to `integrated`, after the parent confirms the integrated SHA is reachable from the current integration head.

Platform handoff gate:

- Applies to a `platform-delivery/1` completion mission. Its selected integration verifiers run fresh, disable reuse, and annotate every upstream platform TEST ID.
- Retains the exact `mission_integration` PASS at that mission's `integrated_sha`. This retained PASS starts the next platform; `worker_passed`, a route, or a batch gate does not.
- Treats a later candidate as new proof. It reruns only the seam and final gates per Review Topology.

Batch integration gate:

- Runs the PLAN-level `batch_verifiers` after every selected wave has integrated serially.
- Uses `scripts/verifier_runtime.py` batch mode, as do task and worker gates; host verifiers require `parallel_safe: false`, and independent workers may run host checks concurrently in separate worktrees.
- Contains only checks that need more than one integrated mission or shared contract. Do not repeat focused task suites here.
- Proves cross-mission behavior did not regress and blocks the next wave on failure.

Fresh integration review gate:

- Starts once every mission it covers has integrated serially into one integration branch. It uses new parent-dispatched read-only reviewer attempts on the exact `integration_head_sha`; a mission writer is never a reviewer. Lenses, repair and re-check follow Review Topology.
- Under `per_mission`, skip the dispatch when the integration head's tree is byte-identical to a tree a pre-integration review of the same review type already passed: the head is that reviewed commit, or a merge commit whose `integration.integration_tree_sha` equals that review's `review_workers[].tree_sha`. Record the node as `skipped`. Run `python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> skip-integration-review --node-id <id> --worker-id <id>` for the live-Git tree check and skip record. `record-review-attempt --tree-sha <sha>` persists the reviewed tree on PASS; the global `--repo-root <root>` before that subcommand can derive it from Git.
- Under `per_mission`, a `frontend_code` or `backend_code` review also skips when the head is a merge chain of reviewed heads: omit `--worker-id` from the same command, which walks first parents and records `integration.reviewed_merge_chain`. Each link must be a clean automatic merge of an exact mission head that passed every planned pre-integration review of its mission, changing only that mission's write scope, with linked scopes not overlapping. A conflict, manual merge edit, overlapping scope, unreviewed head or commit, or missing proof means the review runs. A `visual` review judges the rendered head, so only the tree-identical skip applies to it. Security review never skips.
- Otherwise the review runs. Under `per_mission` the packet lists the already-reviewed mission heads and the pass focuses on what the combination changed; under `final_candidate` it reads the whole candidate diff.
- A repair invalidates current integration-stage PASS coverage for the repaired paths until a scoped PASS re-binds them. Historical reviews keep their original SHA.

Final/current-head gate:

- Runs the one planned broad regression, browser E2E, and visual/UI validation suite only after the combined review and its one repair loop converge.
- Covers every `platform-delivery/1` TEST ID. Extra required shared-regression tests are allowed. Every annotated feature gate runs fresh on the exact integration head.
- Binds every PASS to the exact integration head. Any later code or configuration change invalidates the affected proof.
- Focused task, worker, and integration checks are not this suite. Plan cross-cutting checks only the whole candidate can answer — build, browser E2E, migration, UI evidence — not a rerun of every focused suite already green on the same code. A gate that only re-executes a mission's own unit tests on an unchanged tree gets changed-file selection against the plan write union, or is dropped.
- A failure in the once-per-candidate broad suite enters the Isolated Repair Protocol.
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
| Visual design | initial design or active enhancement has an approved UI source | matches the PRD UI surface contract, the approved HiFi surface (pinned legacy contracts: `legacy/legacy-pins.md#legacy-ui-contracts-before-059`), and active visual source (required design-system package, including frozen derived HTML for `design-system/4`, or approved page-faithful target) within stated tolerance; routine maintenance checks the current accepted product and effective requirements | screenshots or human approval |
| Page-to-PRD conformance | an initial or enhanced route has a `PRD.md` `UI-*` entry and a matching copy-complete HiFi page (current `ui-design/3` or retained `ui-design/2`) | the built route matches PRD behavior and the affected HiFi region order, grouping, element inventory, states, responsive rearrangement, actions, exact static/action/feedback/alternate-state wording from its `ui-hifi-copy/1` copy, and dynamic source/order/format/count/length/fallback contracts at every required target; routine maintenance checks current affected behavior and regression consumers without regenerating historical HiFi | screenshots + browser geometry/reviewer note |
| UI contract check | `design-system.json` exists and the Design System Need Gate is `required` | `python "<delivery-harness-skill-root>/scripts/check_ui_contract.py" --registry <design-system.json> --repo-root <root> --path <product-source-dir>` (default: current working directory) reports no violation against the product's real source; token and primitive sources resolve by exact normalized repo-relative identity, not filename suffix; a zero-file run is not a pass, and a `--rule`-filtered, `--token-source`, or `--primitive-source` run is not contract-clean; source roles come only from the frozen `design-system.json` | checker output |
| Design-system pair check | the active initial/enhancement visual route requires a current pair | `python "<design-system-compiler-skill-root>/scripts/check_design_system_pair.py" --markdown <design-system.md> --registry <design-system.json> --repo-root <repository-root> --require-filled` exits 0 against the frozen pair, run from the repository root and never with `--write`; a failure is a stop condition per `contract-and-traceability.md`. A retained historical pair in routine maintenance is not revalidated against a later accepted PRD solely because it exists; preserve its bytes and check the current product | checker output |
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

Task and worker verifiers select against their own task or mission write scope. Batch and final gates may also select, but against the union of every mission write scope in the PLAN, never one mission's slice. Each of `batch_verifiers` and `final_gates` must keep at least one always-run verifier; put build, browser E2E, migration, and UI checks there. Integration, migration, and smoke gates always run when their stage applies.

Parent-observed changed paths are literal repository-relative filenames, including dynamic routes such as `[slug]`, `[...slug]` and `[[...slug]]`, not scope patterns. Absolute paths, traversal and non-canonical separators remain invalid; write-scope declarations keep their separate restricted grammar.

The parent supplies normalized, repository-relative observed paths to `select_verifiers.py`. A targeted verifier is `not_applicable` only when no observed path matches its exact path or `/**` subtree. Invalid or incomplete parent observations fail safe by requiring every declared verifier.

Every applicable declared verifier requires an explicit execution mode. Host mode runs the declared argv in the bound checkout with the project toolchain and current user permissions. Host verifiers execute serially within one runner and never reuse cached results; this is no network or filesystem confinement. Missing, container, `live`, and `git_snapshot` modes are invalid in current tools, and no container runtime or image policy is part of readiness or result evidence. Browser, external service, migration, and mutable-environment operations keep their separate routes and action authorization.

Host commands run in an owned process group or job that ends after success, failure, or timeout, before the final source/Git checks; they must stay in that group and must not daemonize with `setsid` or `setpgid`. Commands that need to escape that lifetime need a separately authorized managed service with its own finite lifetime.

A native or desktop verifier (xcodebuild, Simulator, Android Emulator or AVD, Gradle, Flutter, .NET, Linux toolkits) builds on demand and cleans after. Before starting it records free disk space and a threshold and does not start below it: it reports BLOCKED, or first removes its own earlier leftovers. It keeps a ledger of what it creates (the DerivedData path, build, `.build`, Gradle and Flutter output directories, Simulator devices by UDID, Android AVD names, caches it populated). After the evidence (screenshots, logs, hashes) is copied into the repository evidence path, it deletes every ledger entry, then runs the final source/Git checks. It deletes only what it created, never pre-existing Simulators, runtimes or caches. A Simulator runtime the run installed stays by default and is deleted only when free space is below the threshold; devices and DerivedData are always removed. A cleanup failure cannot produce PASS. Record the ledger, the free-space readings and the cleanup result in the evidence row's Notes.

A parent-owned batch/final graph verifier carries the reserved node/attempt nonce and Git guard from `reserve-node-attempt`. Only RUN and its declared generated `docs/tasks.md` view are exempt from dirty status; a replayed nonce, checkout drift, protected coordination-file change, or request/result artifact inside the reviewed checkout is rejected.

New local verifier declarations use:

```json
{"execution":{"parallel_safe":false,"resources":[],"isolation":"host"}}
```

Host declarations grant no dependency installation, network side effect or publication authority. Provision the project environment under its existing authorization before verification. On Windows, use native executables with argument arrays; do not wrap arbitrary commands in a shell.

The runtime decides PASS from exit code 0 alone. Write `pass_signal` as `exit 0`; give any additional condition its own verifier argv. Keep request and result artifacts outside the reviewed checkout. Current verifier commands always execute fresh. Historical container/cache protocols use their [exact pinned bundle](legacy/legacy-pins.md#container-verifiers-before-066). Retained evidence keeps its original SHA and origin; never relabel it as a fresh execution.

## Automated E2E And Smoke Reuse

Make deterministic automated E2E the normal proof for every primary journey. Record its command, CI check name, environment, covered journey, expected pass signal, artifact or retained log, and commit SHA before execution. A target repository that wants the same checks in CI seeds its workflow from `assets/templates/PROJECT_CI.template.yml`; CI results are retained evidence the harness may cite but never waits on, and both share the contract's single E2E command definition.

A current-head E2E PASS replaces a duplicate manual smoke only when all of these are true:

- The E2E ran against the exact integration head being accepted.
- It covers the same primary journey, assertions, configuration, data, auth state, and external dependencies as the proposed smoke.
- It has a deterministic pass signal and retained evidence tied to that head SHA.
- No later code, configuration, migration, or dependency change invalidated the result.

Then record the manual smoke disposition as `not required - covered by current-head E2E`, with the E2E check and SHA; this is not a skipped gate and needs no risk acceptance. Manual smoke or another environment-specific check is still required when automated E2E is missing, skipped, failed, flaky, or materially narrower than the target, or when a visual or external integration remains uncovered.

## UI Evidence Gate

Required when:

- The mission changes UI, UX, navigation, layout, visual styling, responsive behavior, or a real user journey.
- The user explicitly asks for visual proof.
- Acceptance requires screenshots, browser checks, or design comparison.

Optional when:

- The change is user-facing but not visual, and DOM/API/component tests prove it.

Not required when:

- Backend-only, cron, data pipeline, config, tests, refactor, docs-only, or API-only work has no browser-visible state.

Prefer targeted viewport, element, or region screenshots over whole-page captures, which need a reason. Traces, console logs, and browser reports are supplemental; they do not replace a required screenshot.

For every PLAN surface with `evidence_gate: required`, capture each planned product state and applicable `design_coverage` condition at every declared responsive target. Exclusions make no screenshot.

Capture the full matrix once on the final candidate; mission-head captures are author evidence, not `ui_evidence` rows. Current RUN-v11 `ui_evidence` records the surface ID, route, breakpoint, state, repo-relative image path under `docs/goal/evidence/`, lowercase SHA-256, exact integration head SHA, and status. Rows additionally record the PLAN `capture_mode`-compatible `capture_method` and a complete immutable `target_comparison`: `baseline`, exact `authority_sources` path/hash identities, a real hashed `baseline_artifact` image under `docs/goal/evidence/`, its `baseline_artifact_sha256`, verdict, and differences. Every row also records `layout_check`: `pass` from a real-browser DOM geometry scan at that breakpoint and state — no unintended element overlap, clipping, occlusion, or horizontal overflow over visible peers, containers, and viewport bounds; `fail — <selectors>` records the offending elements and blocks the gate until the surface is repaired and the entry recaptured; `manual — <basis>` records a labeled manual review or native UI-test layout assertion; `n/a — <reason>` records why no geometry check applies. A `layout_check` value — like a `deviation_ledger` citation or a `ui_impact_summary` row — is a recorded attestation, not a validator-proven fact: the validators prove completeness and shape, never that the scan ran or a citation is true, so each attestation names a verifiable anchor (`ui-design.md` clause, delta ID, or manual basis). A screenshot alone never satisfies the layout check.

After a repair, probe every matrix entry on the new integration head and apply [render fingerprint carry-forward](../../ui-design-builder/references/output-contract.md#render-fingerprint-carry-forward). Recapture the entries the repair touches and any entry whose fingerprint changed. An entry with an equal fingerprint keeps its original image and SHA-256, records the new integration head in `head_sha` (the probe ran on it), and names its source head SHA and fingerprint in the retained comparison anchor.

For a route whose `UI-*` entry records SEO metadata, the same evidence set includes the rendered `<head>` on the integration head: its `<title>` and meta description match the PRD record. A mismatch is a failing check, not a style preference; a route with no PRD SEO record is a contract gap routed to `product-definition-builder`, not a verifier skip.

### Capture Mechanism By Platform

Parity screenshot filenames include a SHA-256 of the exact surface, route, breakpoint, and state tuple, so distinct tuples never share a file. Consumers use the paths recorded in the capture manifest.

Only the capture mechanism changes with the resolved platform. Every platform must still produce a real binary screenshot under `docs/goal/evidence/`, record a lowercase SHA-256, bind it to the exact integration head, and cover the full breakpoint-by-state (native: device/OS-by-state) matrix. Placeholder, fabricated, or hand-drawn images never satisfy the gate.

For a hosted-browser surface (`capture_mode: hosted-browser`), capture through a browser — Playwright/headless-browser screenshots, browser DevTools, or the `agent-browser` CLI — at that surface's planned viewports, using the route-by-breakpoint-by-state matrix and the runbook's hosted-browser UI Evidence columns. `scripts/parity_capture.py` captures only this hosted subset in a hybrid plan; extension, native, and desktop groups are reported as platform/manual groups rather than rejected or approximated with a URL.

For a browser-extension mission (`capture_mode: browser-extension`), use extension-aware browser automation against the installed extension and its declared contexts. Record `capture_method: browser-extension`; do not substitute a hosted URL or `--base-url` parity capture.

For a native iOS/Android/Flutter/macOS/Windows/Linux mission (`capture_mode: native`), capture through the platform's own UI-test tooling instead of a browser, using the device/OS-by-state matrix and the runbook's native UI Evidence columns. Record `capture_method: native-ui-test` or `manual-native`:

- iOS: Simulator screenshots from XCUITest cases run by `xcodebuild test`.
- Android: Emulator screenshots from Espresso via `./gradlew connectedAndroidTest`.
- Flutter: integration-test screenshots via `flutter test integration_test/` (or `flutter drive`), for each native target in scope.
- macOS desktop: XCUITest screenshots from `xcodebuild test`.
- Windows desktop: WinAppDriver or a .NET UI-test framework driving the app.
- Linux desktop: the toolkit's own UI tests (Flutter `integration_test`, `tauri-driver`, or an AT-SPI tool such as dogtail) in a pinned distribution image.
- Fallback: when no UI-test tooling exists yet, a manually captured Simulator/Emulator/device screenshot is acceptable with the same path, hash, and head binding, labeled as a manual capture.

For a desktop mission (`capture_mode: desktop`), use the platform desktop UI-test tooling or a labeled manual desktop capture. Record `capture_method: desktop-ui-test` or `manual-desktop`; desktop evidence never uses a hosted URL or browser parity helper.

When the design source's mockup HTML is styled to a different platform than the resolved target, do not silently implement against it or guess the capture mechanism; stop and ask per `contract-and-traceability.md`'s mismatch condition.

### Final UI Acceptance

New direct and managed UI work uses one independent read-only acceptance for parity and page quality on the exact candidate SHA. The parent or author prepares the required captures and automated results before review. One reviewer inspects both components below on the same current evidence and returns one consolidated finding set, recording parity comparisons and page-quality findings separately; both must pass.

For managed work, include this acceptance in the applicable planned `visual` review on the same candidate. New consolidated visual nodes include `ui_acceptance` in their existing `required_evidence` list; under `per_mission`, an earlier visual review may declare the same contract. Record `ui_parity:<comparison anchor>` and `ui_page_quality:<quality-report anchor>` in that attempt's evidence. The parent inspects both retained anchors; their presence alone does not prove the checks occurred. Tree-identical reuse also requires coverage of the target's missions, semantic scope, required evidence and tools; an unmarked or incomplete earlier PASS cannot replace a marked acceptance. Do not add another reviewer node or reset its lineage budget. Frozen RUNs retain their pinned contracts until an authorized task boundary; never add the marker to a completed review (`legacy/legacy-pins.md#legacy-ui-contracts-before-059`).

#### Final Visual Parity Loop

The parity component covers every applicable UI surface (managed: every PLAN `ui_surfaces` entry) and binds its evidence to the exact candidate head, comparing the implementation against its approved visual authority in both conformance modes.

For each planned route-by-breakpoint-by-state combination:

- **Target-conformance mode (hosted-browser HTML target):** run `scripts/parity_capture.py --plan <PLAN.md> --reference <approved design-reference HTML> --base-url <app origin> --route-map <route-map.json>` only when every PLAN UI surface has `capture_mode: hosted-browser`. It captures the reference render and the implemented page at the same viewport as `-target.png`/`-actual.png` pairs, runs a DOM geometry probe per app page for the `layout_check` attestation, and writes `manifest.json` plus a self-contained `parity-board.html`. The parent writes the route map once per run: each route's reference selector plus optional `app_eval`/`reference_eval` state and condition setup (`long-content` needs both sides); states not triggered are listed as manifest gaps for the reviewer. Diff first: pass `ui-design.md`'s recorded tolerance as `--tolerance` (a 0 to 1 fraction of differing pixels; `exact` is 0). The script records each pair's geometry fingerprint, pixel diff and a `classification` of `identical`, `changed` or `carried`, and lists changed pairs first on the board. An `identical` pair records `pass` with the capture pair and diff value. A size mismatch, a missing pixel diff, or differing pixels that form a region wider and taller than 4 px is `changed` whatever the tolerance, so a missing or moved element never passes on an aggregate pixel share. Judge only the `changed` pairs item by item (layout, element inventory, observable visual values). Record every verdict as a `target_comparison` row below. Manual capture remains valid when the CLI is unavailable.

For `capture_mode: browser-extension`, `native`, or `desktop`, do not run URL parity for that surface and do not claim hosted parity. Capture the approved target and implemented surface with the platform-specific extension/native/desktop tooling (or an explicitly labeled manual capture) at that surface's responsive targets, bind both to the accepted Git head, and record the platform capture method and exact authority source in each `target_comparison` row. Pairs with no DOM geometry source are judged item by item; a pixel diff alone records no `pass`. A hybrid plan keeps each UI-* surface's release surface, class, responsive set, and capture method explicit.

Store comparison pairs under `docs/goal/evidence/`. Automated captures use `parity/<label>-<tuple-sha256>-target.png` and `parity/<label>-<tuple-sha256>-actual.png`; use the exact paths recorded in `manifest.json`.
- **System-conformance mode:** the baseline is the frozen design-system package (for `design-system/4`, including the frozen derived HTML). The comparison evidence is a clean `scripts/check_ui_contract.py` run against the product's real source at the integration head (per the UI contract check row) plus the full screenshot matrix checked against the pair's tokens and variants.

Record the comparison on each `ui_evidence` row as a `target_comparison` object: `baseline` is `html_target` or `design_system`; `baseline_artifact` is the reference-render image path under `docs/goal/evidence/` for `html_target`, or the contract-check evidence key for `design_system`; `verdict` is `pass` or `deviation`. A `deviation` verdict lists every observed difference, each either inside `ui-design.md`'s allowed deviations or repaired.

Record accepted deviations in the RUN `deviation_ledger`. Every `deviation` difference has one ledger row (`surface_id`, `route`, `breakpoint`, `state`, `difference`, `citation`) citing the `ui-design.md` clause that admits it. A difference that changes regions, states, actions, routes, or responsive behavior is structural drift and routes upstream. Repeated differences cite the frozen design-input delta; accumulated in-tolerance drift never substitutes for a doc update.

Static screenshots never close a motion change. When a mission's diff touches transition, animation, duration, easing, or generated motion assets, its parity evidence adds a motion check row: the authority from `ui-design.md`'s Motion and Media Intent (plus its registered variant or approved target behavior), what the reviewer confirmed in normal and reduced motion, and the verdict. A motion change with no authority citation routes to `ui-design-builder` instead of passing on still images.

Repair cycle: a missing element, a structural difference, or any difference outside the recorded tolerance is not a `pass`. Repair the surface, recapture the affected matrix entries, carry the rest forward by render fingerprint (`--carry-from <previous manifest.json>`: a pair carries when it was `identical`, its geometry fingerprint, fresh app screenshot hash and target inputs are unchanged, and both earlier images still match their hashes; `--recapture-carried` captures everything again), and rebind the evidence to the new integration head SHA. A parity repair is an ordinary candidate-changing repair. The loop uses the one repair and re-check from `gen-verify-correct.md`; it does not add attempts on top of that budget. After a failed re-check, remaining differences enter the Isolated Repair Protocol: a scoped repair recaptures and rechecks only the affected surface's matrix entries and judges its pairs diff-first; never widen the tolerance or relabel an unresolved difference to close the run.

#### Final Page-Quality Pass

The same acceptance reviewer checks each delivered route. When parity passes within tolerance and the HiFi evidence is current, the pass covers only implementation-only properties: performance, the no-JavaScript path, console and network errors, and the focus handling and accessible names the framework renders. HiFi evidence is current when PLAN freezes the approved HiFi entry that Visual Approval and its passing review bind. Otherwise, including routine maintenance and legacy wireframe sources, the pass also checks heuristic UX, accessibility and responsive/device behavior. Impeccable is not the default for this node; it may run only as a separately authorized UI-quality workflow, and its report may provide evidence without replacing the independent Harness reviewer.

- Findings are ordinary review findings. A blocking defect joins the parity defects in the same one repair and re-check; the pass adds no review attempts of its own. Record the pass, every finding, and its verdict as evidence rows bound to the integration head.
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

UI owner approval proves only direction conformance. Agent judgment, heuristic review, screenshots, and automated E2E alone are not representative-user usability evidence.

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

Every new managed PLAN records `security_review.status` as `required` or `not_applicable`; the latter needs a concrete non-code reason. A required policy declares `security` in `required_reviews`. The `security` lens sits on an integration-stage review covering every mission, usually the one combined final review, with review scope containing each covered mission's complete write scope. The Harness parent resolves the project's `code_security_verification` Skill Binding, reserves the review attempt, and dispatches a fresh sibling reviewer with `delivery-harness/references/security-review.md` against the exact `integration_head_sha`.

A required policy may also list `security_review.required_checks`: unique batch or final verifier IDs, each a `local_command` or `harness_parent` graph verifier with a dependency path into every security node. Reservation refuses the review unless each has exactly one PASS execution with exit 0 at the reviewed head; the packet lists each `execution_key`, and the security result's `checks` must equal the PLAN list.

Early controls and negative tests are development evidence, not a substitute for this final independent review. Do not automatically install scanners, probe production, enable network access, or add delegated reviewers. An optional scanner that is absent is recorded as an explicit coverage gap; a required unavailable scanner, advisory source, or reviewer blocks.

The security reviewer is read-only, never delegates, and reports all validated findings in one pass. It receives no write scope, commit authority, scanner-install permission, network permission, or live-target penetration authority. Completion passes the result as `--security-result`. A security PASS must have an empty `exclusions` list; narrowed or omitted coverage is not a PASS.

The unified security pass evaluates cross-mission trust boundaries and security-specific source-to-sink paths from a fresh context. PASS binds to the exact current integration SHA and declared scope. No second security reviewer is dispatched before final validation.

An interrupted security reviewer does not fabricate a structured decision. `reconcile-interrupted-reviews` retains a blocked worker without `security_result` only when the unique matching review attempt carries the `interrupted_review_reconciliation` receipt; the run stays paused and the receipt cannot satisfy closeout. A later exact structured PASS from the current reviewer may close the gate. A PASS also needs at least one tool or manual source review recorded as `passed` or `findings`; skipped or unavailable tools alone are not review evidence.

The neutral PLAN template's combined final node allows one initial review and one targeted recheck (`max_attempts: 2`). A covered parent-side repair uses the existing declared task and `reconcile-candidate-head` under its exact authorization; alternatively, predeclare the [optional repair-only mission](graph-orchestration.md#optional-repair-only-mission) before execution. A `fix_required` activates its single bounded repair, followed by normal result recording, integration and one targeted recheck; never reset attempts or hide a finding. Both routes review the actual repaired unified SHA with complete security scope.

## Failure Handling

Review packets are bounded previews. Both `render_review_packet.py` and `reserve-review-dispatch --packet-out` accept `--diff-artifact-out <new-checkout-external-path>` to retain the complete binary-capable diff. A truncated packet requires reading the full artifact or the same fixed Git range and reporting uninspected paths or binary gaps before PASS. A sidecar failure after RUN persistence reports the durable reservation and requires a new output path before launch.

Apply `bounded-enhancement.md`: reuse existing exact authority for covered repairs instead of requesting repeated approval. At the stricter repair/graph limit, report verified and incomplete scope and hand remaining failures to the next round. Finishing the session is not successful delivery closeout; keep unfinished managed state paused/reconciled and do not archive it as passed.

If verification fails:

- Do not claim done, and do not commit failed work unless the commit is explicitly a harness/test artifact needed to expose the failure.
- Record the failing command, exit code, and minimal error.
- Decide whether the next action is code fix, test fix, environment fix, contract clarification, or user input.
- A timeout or turn cap reached before a verdict is an environment-blocked attempt. The next attempt uses smaller path groups or a smaller brief, never the same packet again.
- Treat repeated failure as a harness issue after two similar failed attempts.
- Treat adjacent edge cases from one parsing, validation, serialization, protocol, state-machine, or boundary primitive as one failure family. Do not authorize another example-specific patch after that family survives a repair. Before another write, require a structural repair objective and an acceptance matrix covering the family's known equivalence classes; otherwise return `REFINEMENT_REQUEST` or `contract_gap`.
- Preserve the mission + review surface + root-cause attempt count across PLAN revisions; a generic instruction to continue never authorizes an extra review.

## Closeout Bar

Final PASS requires:

- Every must-have trace ID is covered.
- Every required gate is PASS.
- Every new managed code-delivery PLAN has a completed `security` review from the `code_security_verification` binding, recorded as PASS on the exact current integration head with no exclusions, or on the anchor head with a scoped-review coverage chain whose entries outside trust boundaries record `security: not_applicable` and whose trust-boundary entries carry their own security result. The required security node cannot be skipped or superseded; a missing, skipped, stale, partial, blocked, or superseded security review prevents closeout.
- Every visual `TEST-*` obligation `PRD.md` marks required maps to a specific verification row above and that row is PASS. A generically named visual gate does not satisfy a specific obligation (see `contract-and-traceability.md`'s Trace IDs).
- RUN-v11 batch/final-gate IDs exactly match PLAN, and every result is PASS with evidence on the exact integration head.
- Closeout runs `scripts/validate_harness_plan.py --design-system <path to design-system.json> --design-system-markdown <path to design-system.md>` whenever the Design System Need Gate is `required`. `ui-design/3` joins also prove the frozen `design-system/4` derived HTML. In target-conformance mode, required screenshot coverage comes from the frozen PRD target scope and PLAN UI evidence rows; absence of both design-system arguments is expected only when PLAN does not freeze that pair.
- Closeout runs `scripts/validate_harness_plan.py --repo-root` to cross-check `integration_head_sha` against the live Git branch head before trusting any recorded head-bound PASS.
- Closeout passes `--prd <path to PRD.md>` whenever PLAN freezes a PRD source. The given bytes must equal that row's `content_sha256`; a source-revision-only row is not enough. The PRD-to-PLAN `UI-*` surface join and the `ui-design/3` joins under `--repo-root` follow `contract-and-traceability.md`; retained `ui-design/2` and legacy wireframe sources follow `legacy/legacy-pins.md#legacy-ui-contracts-before-059`. Managed maintenance instead freezes its task-record Epic, preserves historical design bytes, and still joins current PRD/PLAN route/state/targets.
- Every skipped gate is justified, and baseline justifications are recorded when relevant.
- The RUN `deviation_ledger` is complete (`legacy/legacy-pins.md#pins-before-055` for older pins): every accepted parity deviation carries its allowed-deviation citation, none changes structure, regions, states, actions, routes, or responsive behavior, and a repeated deviation on the same surface cites its frozen design-input delta. Each citation is a recorded attestation (see the UI Evidence Gate).
- The RUN `ui_impact_summary` is complete: every mission on a UI run carries its `none`/`style`/`structure`/`both` classification, and every `structure` or `both` row names the accepted upstream design-input delta. The row records the strongest task impact the mission's workers reported (ui-implementation-contract.md rule 8) and, like the ledger, is a recorded attestation.
- Every `UNVALIDATED` surface is named, and naming it does not substitute for passing when that surface is still required: Final PASS is blocked while any required `ui_evidence` row (or other required gate) is `UNVALIDATED`, unless the user has explicitly accepted it as descoped with a recorded reason.
- Evidence paths exist. Required UI evidence is a real screenshot for every planned breakpoint-by-state combination, bound to the integration head and matching its recorded SHA-256 (RUN-v11: checked in the accepted Git commit/ref, not the working tree). Accepted non-file evidence applies only to gates that do not require screenshots.
- When `parent_managed_worktree` was used (historical app-managed execution follows its exact pinned bundle): the mission integration verifiers passed on the integrated head. In `shared_checkout` mode the final E2E gate on the working integration head covers this.
- Every required reached mission is `integrated` or explicitly superseded, with recorded passing tasks and no blockers, active/blocked workers or open wave. An untouched repair-only mission behind the final review's untaken route may remain queued with dormant tasks; never mark it as executed.
- The final integration head still descends from every recorded required mission integration SHA.
- Landing is `local_only`: `landing.continuity` is `preserved` at C, `pushed_head_sha` is null, push authorization is false, and no push lifecycle node exists (`legacy/legacy-pins.md#pins-before-055`).
- Archival is post-closeout. A must pass archived PLAN/RUN validation, receipt verification and exact C-to-A relocation/allowlist checks. It inherits C's review, security and gate evidence when the C-to-A diff touches only the archive allowlist (`branch-promotion-contract.md#managed-run-archive-before-promotion`); it never changes the archived RUN.
- For current graphs, every reached node is terminal with no retained blocker and every reached edge is terminal. No selector-ready work remains; an activated failed repair cannot use the dormant-subtree exception.
- When a primary journey exists, its required automated E2E check is PASS on the current head.
- When a worktree mode was used: manual worktree/branch cleanup is completed under its exact authorization or explicitly deferred, and app-managed platform lifecycle is recorded separately. In `shared_checkout` mode the worktree step is `not_applicable`; the primary checkout is never removed.

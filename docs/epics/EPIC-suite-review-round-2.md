# EPIC-suite-review-round-2: the heavy items from the suite review

Status: in_progress on `feat/suite-review-r2` (base `main` `e4d05197`); all ten items merged at `ecd5dbf2`, 0.79.0 surfaces and the candidate matrix next

## Problem And Baseline

The suite review of 2026-11-07 (`docs/epics/EPIC-suite-review-2026-11.md`, workflow `wf_19618f07-bb2`) verified 91 findings. Seventy-eight landed in that Epic's two waves and W12's closing pass. These ten need a RUN schema change, a browser-driver extension, a new read-only promotion script or a contract change behind a version pin, so they wait for their own round. Each item keeps its review id; the refuter's refined proposal is the specification and its existing-coverage list is what must not be duplicated.

Baseline: local `main` at `e4d05197`, which merged `fix/compact-tracked-files-retention`, `feat/bdd-scenarios` (0.77.0) and `feat/suite-review-r1` (0.78.0) on 2026-11-07 at the owner's instruction; the matrix at that head passed every step except one real-browser module that only needed an absolute `PLAYWRIGHT_MODULE` path (`task/release-0780/matrix-main-e4d05197/`).

## Accepted Scope

All ten items, owner instruction 2026-11-07 ("整套東西你幫我合併進去，然後再跟進整套東西，然後用 Multi-agent 這邊去做"; then "全部用 GLM 5.3 Flash 去搞定它"). M2 and M4 are one set of four `harness_transition.py` subcommands. M1 is split into the interaction pass (M1a), the reviewer rows (M1b) and `--intermediate`, which M7 also names and owns. M3's task and worker halves were already covered by round 1's `build_verifier_request.py` (W8), so M3 narrows to the shared context function and the mission integration layer. The version pin for M16 and M23 is `(0, 79, 0)`.

Writers: GLM-5.3 Flash (`glm` / `glm-5.3-flash`, thought_level max) via `delegate_task`, one item per brief in a T3 worktree, briefs under the parent's scratchpad `briefs-r2/`; the parent (Claude Fable 5.1, by the owner's standing direction) integrates, applies cross-file requests, repairs and reviews each diff. GLM sessions stop at 100 turns, so most items took two or three writers: the parent committed each stopped worker's clean partial work on its branch and the next writer cherry-picked it.

## Items

### S1 [high/M] Worker packets are filled in by hand, though the reviewer packet is already rendered by a script

Area: Worker launch packet

Problem: For every mission attempt the parent copies about 30 fields from PLAN/RUN into the template. lease-worker has just validated and written those same values. Then the parent runs a separate size check. This is repeated, error-prone transcription with no added judgment.

Evidence:
- skills/delivery-harness/references/runtime-adapters.md:68 'Render ../assets/templates/WORKER_GOAL.template.md with scope, skills, permissions, verifier, result contract and exact input identity'
- skills/delivery-harness/references/stages/stage-cards.md:93 'Render the bounded WORKER_GOAL.template.md packet per mission. Check the complete packet before dispatch.' plus a separate check_launch_packet.py call at :103
- skills/delivery-harness/assets/templates/WORKER_GOAL.template.md:8-48: 41 placeholders. Most come straight from what lease-worker just recorded: PLAN id/revision/digest, mission/tasks, lease, batch base, required_skills, provider/driver/model/effort, the three axes, worktree/branch, write/deny scope, verifiers, resource claims, PRD/TEST security pairs
- skills/delivery-harness/references/runtime-performance.md:9 and harness_transition.py:4369-4380: reserve-review-dispatch --packet-out already renders the reviewer packet and checks its size in one command
- C:/Users/mps19/Documents/GitHub/agentkiosk/docs/epics/EPIC-003-checker-v1-delivery.md:166 packet M1-worker-goal.md (9,404 bytes, cap 14,000) hand-assembled, then a separate check_launch_packet PASS

Proposal: Add an optional `--packet-out <new-path> --max-message-bytes <n>` to `lease-worker`, plus repeatable `--context-path` (the script hashes them) and an optional `--host-file` holding the facts only the host can supply (permissions, route caps, parent launch identity, Visual inputs block). When `--packet-out` is given, the call renders WORKER_GOAL.template.md from the in-memory leased RUN and applies check_message before the durable RUN write. It writes the packet exclusively after the write, as reserve-review-dispatch does. Then reorder runtime-adapters.md steps 4-6 to lease, render, launch, matching Card 4 and the template header. Card 4 drops its separate render sentence and the check_launch_packet command. app_task routes whose host assigns the task id at creation keep the manual render.

Existing coverage, not to duplicate:
- skills/delivery-harness/scripts/check_launch_packet.py (byte check only, run as a separate step)
- skills/ui-design-builder/scripts/visual_inputs.py via skills/delivery-harness/references/frontend-visual-inputs.md:11 (Visual inputs block only)
- skills/delivery-harness/scripts/harness_transition.py:1957-2285 _lease_worker (computes and records the binding, renders nothing)
- skills/delivery-harness/scripts/harness_transition.py:4376-4380,4631-4705 reserve-review-dispatch --packet-out (reviewer packet only)
- skills/delivery-harness/scripts/render_review_packet.py (reviewer packet only)
- skills/delivery-harness/references/execution-state-model.md:82,86 (documents lease-worker without a packet flag)

### M1 [high/L] Capture tooling stops at the case matrix; interactions, reviewer object, intermediate widths and motion receipts are still hand-built per project

Area: ui-design-builder/scripts/hifi_matrix_capture.py + references/matrix-capture.md

Problem: Every HiFi surface check needs a ui-output/3 that holds the matrix, the click+keyboard interaction rows, the reviewer viewport/specimen rows, a separate intermediate-width output and per-intent motion-preview outputs. The suite ships only the matrix part. Each consumer writes its own interaction collector, specimen collector, motion capture and a merge script, which is where most review time and repeated attempts now go.

Evidence:
- skills/ui-design-builder/references/matrix-capture.md:42 ("What the output still lacks is the `interactions` and `reviewer` objects")
- skills/ui-design-builder/references/matrix-capture.md:56 (no product control is clicked; checker requires both objects)
- skills/ui-design-builder/references/output-contract.md:48 (reviewer object: viewport + specimens, measured in browser)
- skills/ui-design-builder/references/output-contract.md:254 (every interaction at every source target, click and keyboard)
- skills/ui-design-builder/references/output-contract.md:286 (Intermediate width check needs an observed ui-output/3 at widths between adjacent viewports)
- skills/ui-design-builder/references/motion-and-media-routing.md:59-67 (motion-preview receipts; no script produces them)
- skills/ui-design-builder/scripts/hifi_reviewer.py:51 (reviewer_contract derives expected rows; it has no CLI and observes nothing)
- docs/epics/EPIC-ui-review-speed.md:24 ("shipped no matrix driver, so each project wrote its own")
- agentkiosk/docs/design/ui-design.md:126 ("frozen D2 operations collector", "packet-local token collector" beside the installed matrix engine, dated 2026-11-06, after the driver shipped)
- agentkiosk/docs/design/evidence/20261106-h076-final-001/assembly/README.md (assemble_final_003..005.py merge matrix + 608 reviewer specimens + intermediate output by hand)
- agentkiosk/docs/design/evidence/20261106-h076-final-001/reviewer/reviewer_collect.py and specimens/{adapter.py,dom.js,freeze.py,prepare.py}
- agentkiosk/docs/design/evidence/20261105-h076-motion-001/ (15 hand-run motion attempt folders)

Proposal: Extend skills/ui-design-builder/scripts/hifi_matrix_capture.py with three additions:
1. The default run also clicks and Enter/Space-activates every manifest interaction at every source target, writing the output-contract.md:254 `interactions` rows and `navigation` events.
2. The default run measures the `reviewer` viewport and specimen rows in the order `hifi_reviewer.reviewer_contract` returns them.
3. A new `--intermediate` flag writes a second ui-output/3 with the same interactions and reviewer, at the midpoint of every adjacent web viewport pair, self-checked with `ui_design_v3.intermediate_width_findings`.

Then:
- drop the first bullet of matrix-capture.md:56 ("What it does not prove"), and
- cut ui-design-pass.md:156-164 to the command plus a read-on-failure pointer, removing the stale Overview/Tokens/recovery traversal that output-contract.md:48 already hands to the shell tests.

Leave motion-preview capture as a separate follow-up. It first needs a product-DOM `data-motion-intent` marker, because matrix-capture.md:50 says the HiFi DOM marks no motion region.

Existing coverage, not to duplicate:
- skills/ui-design-builder/scripts/hifi_matrix_capture.py (case matrix, axes, carry-forward only; clicks no product control)
- skills/ui-design-builder/scripts/hifi_reviewer.py:51 reviewer_contract (works out expected reviewer rows; observes nothing, no CLI)
- skills/ui-design-builder/scripts/ui_design_v3.py:165,200 intermediate_width_required / intermediate_width_findings (checks intermediate cases; does not produce them)
- skills/ui-design-builder/scripts/check_ui_design_contract.py:809 _intermediate_width_evidence (checker only)
- skills/ui-design-builder/scripts/review_evidence.py (builds the receipt from an existing ui-output/3)
- skills/ui-design-builder/assets/templates/HIFI_REVIEWER.template.html:78-89,260-264,309 (in-page specimen display values that a driver could read)
- skills/ui-design-builder/references/ui-design-pass.md:156-164 (manual browser procedure only)

### M2 [high/M] No guarded transition records authorization grants, readiness or closeout, so parents hand-edit RUN JSON

Area: execution-state-model.md Authorization Action Ledger / readiness / closeout; harness_transition.py

Problem: The rules forbid 'validate and write back' edits to RUN, but three required state changes have no transition. Each grant must copy the current plan revision and digest exactly, or it silently covers nothing. Consumers write throwaway scripts that edit RUN directly, break its JSON, and bypass the lock and guards the other transitions enforce.

Evidence:
- skills/delivery-harness/references/execution-state-model.md:118 ('initial readiness, capability/authorization recording, formal revisions, and final closeout need their documented parent-owned procedure'; no procedure or command is given)
- skills/delivery-harness/references/execution-state-model.md:44 ('complete' is not a label the parent may set independently, yet no command sets it)
- skills/delivery-harness/references/execution-state-model.md:313-338 (the grant must carry run_id, plan_revision, plan_digest_sha256, exact targets and the wave pair, all typed by hand)
- skills/delivery-harness/references/stages/stage-cards.md:66 ('set plan_readiness: ready through the parent-owned readiness procedure')
- skills/delivery-harness/scripts/harness_transition.py:4359-4420 (subcommands cover pause/resume/cancel, lock, observation, wave, lease, attempts, review, integration and reconcile; none writes authorizations, plan_readiness or status: complete)
- jolvex-platform/docs/goal/record_m2.py:24-34 (a consumer script rewrites authorization targets and mission_states through regex plus json.loads)
- jolvex-platform/docs/goal/fix_run_json.py:9-12 (repairs RUN JSON broken by Windows paths written by hand)
- jolvex-platform/docs/goal/shape_run_evidence.py:15-22

Proposal: Add three lock-holding harness_transition.py subcommands. Each one writes RUN only after the in-memory pair passes the existing manifest validation:
- `record-authorization --action <ledger key|execution> --source <exact owner statement> --mission-id <id>... --target <t>... --expires-when <v>`. It fills run_id and the plan revision and digest from RUN; for wave_closed it also fills the active wave pair. It refuses `push`.
- `record-readiness --source <readiness record path>`. It sets plan_readiness: ready only when the validator passes.
- `record-closeout --source <text>`, with --repo-root. It sets status: complete only when every status: complete condition passes against live Git.

Then:
- Replace "their documented parent-owned procedure" at execution-state-model.md:118 and stage-cards.md:66 with these command names.
- Add record-closeout to Card 7's commands, which currently never set complete.
- List all three under Scripted Transition Flag Surfaces and in MISSION_RUNBOOK.template.md:184.
- Shrink the hand-authored grant JSON at execution-state-model.md:313-326 to one line that points at the command.

Existing coverage, not to duplicate:
- skills/delivery-harness/scripts/harness_manifest.py:4547-4563 (validator rejects authorized ready/running RUN without plan_readiness: ready)
- skills/delivery-harness/scripts/harness_manifest.py:4746-4778 (validator rejects a grant whose run_id/plan_revision/plan_digest/wave pair mismatch RUN, after the hand edit)
- skills/delivery-harness/scripts/harness_manifest.py:5956-5975 (validator checks status: complete conditions only once status is already complete)
- skills/delivery-harness/scripts/harness_transition.py:1084-1190 (close-wave resets wave_closed grants and execution authorization; never sets them)
- skills/delivery-harness/references/execution-state-model.md:337 (lease-worker materializes exact targets from an active wildcard grant, covering only receipts)
- skills/delivery-harness/scripts/new_run.py:183 (initial plan_readiness: draft, authorizations false)
- skills/delivery-harness/references/stages/managed-delivery.md:96-130 (readiness conditions and environment probe, but no write step)
- skills/delivery-harness/references/verification-gates.md Closeout Bar (conditions only, no write step)

### M3 [high/M] No script builds the verifier_runtime request for task, worker or integration checks

Area: Task/worker/integration verifier requests

Problem: Task, worker and integration verifiers need an exact request: the per-task context (that task's own commit files and attempt id), the Git guard and the host preflight with the executable hash. The library functions exist (host_executable_identity, _git_guard_snapshot), but there is no CLI. Workers and parents hand-assemble the JSON, get the context wrong, and re-run checks. One consumer copied an earlier execution record instead of building a new one.

Evidence:
- skills/delivery-harness/scripts/verifier_runtime.py:1210-1236: the only CLI input is --request <json> carrying verifier, context, checkout_root, git_guard and host_preflight
- skills/delivery-harness/references/execution-state-model.md:66-70: only reserve-node-attempt --request-out produces a request, and only for batch/final graph nodes
- skills/delivery-harness/assets/templates/WORKER_GOAL.template.md:80 tells the worker to run each verifier through verifier_runtime.py but gives no way to build the request
- skills/delivery-harness/references/worktree-thread-orchestration.md:196 says to run mission integration verifiers and keep their protocol-v2 output, with no request builder
- skills/delivery-harness/scripts/select_verifiers.py:149-152 picks verifiers from changed files but emits no request
- C:/Users/mps19/Documents/GitHub/agentkiosk/docs/epics/EPIC-003-checker-v1-delivery.md:166 'a parent-supplied verifier helper that builds the exact Harness request (host preflight, git guard)'
- C:/Users/mps19/Documents/GitHub/agentkiosk/docs/epics/EPIC-003-checker-v1-delivery.md:170: the worker's T02/T03 contexts carried the cumulative file list and the dispatch attempt id, so the parent re-ran three verifiers
- C:/Users/mps19/Documents/GitHub/jolvex-platform/docs/goal/record_m2.py: cloned M1's verifier execution, rewrote its context and key_document, and recomputed execution_key by hand

Proposal: Add `--request-out-dir <dir outside checkout> --run <RUN.md> --checkout <path> --layer task|worker|mission_integration [--task-id <id>] [--attempt-id <id>] [--integrated-sha <sha>]` to skills/delivery-harness/scripts/select_verifiers.py, writing one ready verifier_runtime request per selected verifier. The context must be computed by the same shared function that validate_worker_result.py:495-620 and harness_integration_results.py:108-122 already check against:
- task: that task's head and its own commit files.
- worker: the base..head files.
- mission integration: the batch_base..integrated files, checkout_role "integration" and cache_safe false.
- Refuse an attempt_id that RUN's attempt_log already binds to another task.

The git_guard comes from the live branch and head plus _coordination_ignored_paths, and host_preflight comes from host_executable_identity. Then replace the prose at WORKER_GOAL.template.md:80, worktree-thread-orchestration.md:196 and stage-cards.md Card 5 with that one command.

Existing coverage, not to duplicate:
- skills/delivery-harness/scripts/harness_transition.py:1271-1322 (_local_verifier_request builds requests for batch/final only)
- skills/delivery-harness/references/execution-state-model.md:66-70 (reserve-node-attempt --request-out, non-mission nodes only)
- skills/delivery-harness/references/stages/stage-cards.md:133-134 (same batch/final route)
- skills/delivery-harness/references/worker-result-contract.md:28-52 (documents the context shape only; no per-task head/files rule, no git_guard/host_preflight, no integration context)
- skills/delivery-harness/scripts/validate_worker_result.py:495-620 and skills/delivery-harness/scripts/harness_integration_results.py:108-122 (the expected contexts exist in code but only as validators)

### M4 [high/M] Opening, revising and closing a RUN are still hand edits to the JSON

Area: RUN lifecycle transitions (readiness, grants, runtime, revision, closeout)

Problem: The routine mid-run mutations are scripted, but the RUN edits with the most authority are not: the 12 grant entries and their scopes, execution_authorized and its scope, runtime_adapter and version_gate, plan_readiness and status, rebinding grants after a PLAN revision, and landing continuity with status: complete. Parents edit the JSON or write their own scripts. That breaks JSON, repeats the same scope on 12 entries, and risks the very mistakes the guarded path exists to prevent.

Evidence:
- skills/delivery-harness/references/execution-state-model.md:120 'initial readiness, capability/authorization recording, formal revisions, and final closeout need their documented parent-owned procedure. Do not invent a subcommand'; :122 'The tools have no guarded formal PLAN-revision mutation'
- skills/delivery-harness/references/stages/stage-cards.md:62 (Card 3) asks for exact authorization recording and setting plan_readiness: ready; its commands at :66-69 are only record-observation and validate
- skills/delivery-harness/references/runtime-upgrades.md:8 and runtime-adapters.md:12-31 ask the parent to record provider, drivers, route caps and version_gate digests by hand
- skills/delivery-harness/assets/templates/HARNESS_GOAL.template.md:6 'The parent transcribes each yes row into the RUN authorizations ledger'
- skills/delivery-harness/scripts/harness_transition.py:4 docstring claims it replaces ad-hoc JSON editing for owner grants, but its subcommands (:4359-4498) have no grant, readiness, runtime, revision or close command
- skills/delivery-harness/references/execution-state-model.md:44-58 lists the status: complete conditions; harness_transition.py:3041-3043 only updates landing.continuity.head_sha once it is already preserved, and no command sets preserved or complete
- C:/Users/mps19/Documents/GitHub/agentkiosk/docs/epics/EPIC-003-checker-v1-delivery.md:166 'authorizations transcribed from the signed brief ... runtime adapter ... recorded ... plan_readiness ready, status ready'
- C:/Users/mps19/Documents/GitHub/agentkiosk/docs/goal/DECISIONS.md:7 'same ledger rows re-authorized for digest cdc39c25…'; dilution-radar/docs/goal/RUN.md:12-80 is at PLAN revision 22, with run_id/revision/digest repeated in each of 12 grant scopes
- C:/Users/mps19/Documents/GitHub/jolvex-platform/docs/goal/fix_run_json.py:9-11 repaired invalid JSON escapes from hand-typed Windows paths; record_m2.py and shape_run_evidence.py rewrote grants, observed and integration fields with regex

Proposal: Add record-only subcommands to harness_transition.py. Each takes the run lock, requires --source carrying the owner's words, and validates the full pair before writing. The first is `record-grant --action --target... --mission-id... --expires-when --source`. It fills run_id and the current plan revision and digest, refuses `push`, and is the only rebind path after a validated PLAN revision, run again with fresh owner words. The second is `open-run --intent --mission-id... --expires-when --source`. It sets intent, execution_authorized with its source and scope, and plan_readiness and status to ready, but only when the existing validator passes. The third is `close-run --source`. It sets landing.continuity to preserved at integration_head_sha and status to complete, but only when the existing complete checks pass. An optional fourth, `record-runtime --provider --driver... --route-caps --session-id [--loaded-digest]`, writes runtime_adapter and version_gate and never fills the loaded digest from installed bytes. List the commands in Cards 3 and 7 and in Scripted Transition Flag Surfaces. Replace the 'documented parent-owned procedure' wording at execution-state-model.md:118-120 with the command names.

Existing coverage, not to duplicate:
- skills/delivery-harness/scripts/new_run.py:1-17,173-216 (seeds RUN with all 12 authorizations false, plan_readiness draft, status draft, intent plan-only, installed_contract_digest computed)
- skills/delivery-harness/scripts/harness_transition.py:4428-4443 lease-worker and reserve-review-dispatch record exact-target receipts under existing wildcard grants (execution-state-model.md:334)
- skills/delivery-harness/scripts/harness_transition.py:1178-1187 close-wave resets wave_closed grants and execution_authorized
- skills/delivery-harness/scripts/harness_transition.py:3041-3043 refreshes landing.continuity.head_sha only when already preserved
- skills/delivery-harness/scripts/harness_manifest.py:4549-4564,5956-5960 validator enforces ready/complete preconditions after a hand edit
- skills/delivery-harness/scripts/archive_run.py:495 and inspect_harness_run.py:426 read status complete but never set it
- skills/delivery-harness/references/execution-state-model.md:118-120 states these are parent-owned procedures with no subcommand

### M7 [high/M] First-Wave Audit Axes and the matrix driver's --axes disagree

Area: references/ui-grading-rubric.md#first-wave-audit-axes vs references/matrix-capture.md#axes

Problem: A lead grader who runs the shipped driver as documented leaves the dark-theme base matrix and the 320 px reflow sweep unobserved, so the rubric's own list is not met and projects run extra passes by hand.

Evidence:
- skills/ui-design-builder/references/ui-grading-rubric.md:23 (each theme in scope is part of the base matrix, every case)
- skills/ui-design-builder/references/matrix-capture.md:36 and :50 (dark is a sampled axis: two states x two targets per page)
- skills/ui-design-builder/references/ui-grading-rubric.md:38 (reduced motion only on pages with a motion region) vs skills/ui-design-builder/references/matrix-capture.md:50 (runs on every page)
- skills/ui-design-builder/references/ui-grading-rubric.md:35-36 (long/localized copy, intermediate widths and 320 px reflow) — no matching --axes value
- agentkiosk/docs/design/evidence/20261104-h076-dark-matrix-001 and 20261104-h076-zoom-diag-001 (separate hand-run dark and zoom passes)

Proposal: Add three options to hifi_matrix_capture.py and give each a row in matrix-capture.md#flags. (1) `--color-scheme dark` runs the full base matrix with the browser context's colorScheme set to dark and writes it to its own `--out` as a separate ui-output/3; this replaces agentkiosk's dark_matrix.py adapter. (2) `--intermediate` widens `[data-hifi-canvas]` with an inline width to the midpoint of each adjacent pair of approved web widths and writes the ui-output/3 that review_evidence.py turns into the `Intermediate width check` receipt (output-contract.md:286). (3) An axis `reflow-320` puts the two sampled states at a 320 CSS px canvas width and writes them as sidecar axis rows like the other axes. Then add one line to matrix-capture.md#axes saying long and localized copy is judged from the authored copy (rubric:67), not from a flag. Leave rubric:38 unchanged.

Existing coverage, not to duplicate:
- skills/ui-design-builder/references/matrix-capture.md:36 (--axes dark,reduced-motion,forced-colors,zoom-200 only)
- skills/ui-design-builder/references/matrix-capture.md:50 (dark sampled on two states x two targets; reduced motion on every page, documented)
- skills/ui-design-builder/scripts/hifi_matrix_capture.py:43 (AXES tuple) and :209 (base context colorScheme 'light')
- skills/ui-design-builder/references/output-contract.md:286 (Intermediate width check needs an observed ui-output/3 at in-between widths)
- skills/ui-design-builder/scripts/ui_design_v3.py:200-234 and check_ui_design_contract.py:809-827 (checker enforces the intermediate-width receipt; no shipped tool writes it)
- skills/delivery-harness/references/pre-delivery-self-review.md:52 (tells the author to cover intermediate widths and long copy with the driver)
- skills/ui-design-builder/references/modern-design-sources.md:8 (defines 320 CSS px reflow as an accessibility stress case)
- skills/ui-design-builder/references/ui-grading-rubric.md:67 (long real copy and bilingual wrapping judged from authored content)

### M14 [high/M] No read-only command proves main pre-state, frozen-base ancestry and tree equality of server-created main S

Area: delivery-harness / Promote To Main readback

Problem: Archive and publication are scripted, but Promote To Main conditions 4 and 7 have no script. Each landing re-derives the same Git checks by hand: remote main equals the recorded pre-state, frozen base is an ancestor of the candidate, main_before is an ancestor of the new main, and the candidate and main trees match. Two consumers and the source repo each wrote this proof in a different shape: JSON, prose, or an Epic line. A mistake in a hand comparison can let a different tree inherit the candidate's review, security and CI evidence. The contract forbids that at lines 89-94.

Evidence:
- skills/delivery-harness/references/branch-promotion-contract.md:68 (later main movement requires fresh promotion reconciliation, but nothing performs it)
- skills/delivery-harness/references/branch-promotion-contract.md:81 (condition 4: fresh remote main matches recorded pre-state and proves ancestry from the frozen base)
- skills/delivery-harness/references/branch-promotion-contract.md:84 and :91 (condition 7: S tree must equal candidate tree; record S, the tree proof and the original identities)
- skills/delivery-harness/references/trusted-host-publication.md:5-7 (publication has prepare and verify-receipt; promotion has no equivalent)
- skills/delivery-harness/scripts/push_archived_candidate.py:501-504 (under main-preview/1 the receipt's expected_main is no longer checked against main)
- skills/delivery-harness/scripts/push_archived_candidate.py:518-552 (_remote_state: isolated ls-remote that can be reused)
- skills/delivery-harness/scripts/branch_policy.py:81-123 (archive_ancestry_base and the merge-base ancestry check that can be reused)
- C:/Users/mps19/Documents/GitHub/ticketradar/docs/release/parking-planning/live/main-landing.json:2-13 (hand-built main_before, main_after, candidate_tree, main_tree, tree_equal, evidence_origin)
- C:/Users/mps19/Documents/GitHub/ticketradar/docs/release/parking-planning/release-report.md:18 ('The server merge and candidate trees both equal bf2b4e56...')
- C:/Users/mps19/Documents/GitHub/jolvex-platform/docs/DEPLOYMENT.md:211 and :629 (tree equality stated in prose with no command output)
- docs/epics/EPIC-flow-robustness.md:55 and docs/epics/EPIC-release-0.65.3.md:18 (the source repo also proves PR merge tree equality by hand every release)
- skills/delivery-harness/references/governance/source-maintenance.md:71 (tree equality is required before tagging)

Proposal: Add a read-only script, skills/delivery-harness/scripts/promotion_readback.py, with two subcommands.

`pre` covers condition 4. It takes --repo-root, --remote, --candidate, --base and --main-before as full SHAs. It reads refs/heads/main once through push_archived_candidate._remote_state and _configured_push_url. It returns BLOCKED unless that main equals --main-before, --base is an ancestor of --candidate, and --main-before is an ancestor of --candidate.

`post` covers conditions 7 and 8. It takes the same inputs plus an optional --out path outside the checkout. It reads main again and requires that commit to already exist locally, from the separately authorized fetch. It checks that --main-before is an ancestor of the new main. It compares the trees with rev-parse ^{tree} and classifies the landing as exact, tree_equal_S or new_candidate.

Both subcommands print JSON with observed_main, the ancestry booleans, candidate_tree, main_tree, landing and status PASS or BLOCKED. The JSON also states that the result grants no landing, tag or deployment. The script never fetches, pushes, merges or tags.

Name the script in branch-promotion-contract.md conditions 4 and 7. Replace "exact tree-equality proof" at line 91 with "the `post` JSON", and add the same pointer to governance/source-maintenance.md:71 and the README Releasing section in all four languages.

Existing coverage, not to duplicate:
- skills/delivery-harness/scripts/push_archived_candidate.py:613-636 (verify-receipt reads back only run-branch A, not main)
- skills/delivery-harness/scripts/push_archived_candidate.py:499-507 (receipt expected_main is checked only for pre-main-preview pins; frozen-base-to-C ancestry at archive time)
- skills/delivery-harness/scripts/archive_run.py (binds the observed main into ARCHIVE_RECEIPT.json at archive time only)
- skills/delivery-harness/scripts/branch_policy.py:94-123 (validate_branch_policy_ancestry: frozen base to initial/candidate head at PLAN/RUN validation, not at landing)
- skills/delivery-harness/scripts/check_deployment.py:495-711 (Release Source Provenance: deployment source SHA readback, no main tree equality)
- skills/delivery-harness/scripts/harness_transition.py:3356,4101-4250 (integration/reviewer tree tracking inside a RUN, not main landing)
- skills/delivery-harness/references/branch-promotion-contract.md:81,84,91 and governance/source-maintenance.md:71 (rules stated in prose only)

### M15 [high/M] parity_capture.py cannot drive the ui-hifi/2 HiFi package it is supposed to compare against

Area: delivery-harness production UI parity: scripts/parity_capture.py reference side

Problem: The approved HiFi is a multi-page ui-hifi/2 package. Its responsive target and state are chosen with reviewer-shell buttons, and its layout responds to canvas width through container queries. parity_capture.py treats the reference as one page reached through route-like links and sized by viewport width, and it screenshots the reviewer sidebar along with the page. Its -target.png therefore never shows the approved surface at the requested target and state. The one real consumer run captured zero pairs, and the owner dropped the gate. The route map that must supply app_eval for every state has no template. Its keys are documented only in code, and parameterised routes need app_path, which no document mentions.

Evidence:
- skills/delivery-harness/scripts/parity_capture.py:470-499 (opens the single --reference file, then clicks a route-map selector or probes a[href=route])
- skills/delivery-harness/scripts/parity_capture.py:502-525 (picks the breakpoint by resizing the browser viewport)
- skills/delivery-harness/scripts/parity_capture.py:528-538 (screenshots the whole viewport, so the reviewer sidebar is in the target PNG)
- skills/ui-design-builder/references/output-contract.md:35-36 (each HiFi page has a fixed reviewer shell; targets are [data-hifi-canvas] widths set by container queries; host viewport media queries are banned)
- skills/ui-design-builder/references/output-contract.md:43 (states switch through button[data-hifi-state-control])
- skills/ui-design-builder/scripts/hifi_matrix_capture.py:260-316 (already drives the target and state controls and screenshots [data-hifi-canvas])
- C:/Users/mps19/Documents/GitHub/jolvex-platform/docs/goal/archived/20260916-215455-m11b2-implementation-closeout/evidence/manifest.json (status FAIL: 0 pairs captured, 1890 skipped; 210 'no reference navigation found', the rest 'no app_eval trigger ... in the route map')
- C:/Users/mps19/Documents/GitHub/jolvex-platform/docs/goal/archived/20260916-215455-m11b2-implementation-closeout/PLAN.md:6399 (reference was a ui-hifi/2 bundle with 34 surfaces)
- C:/Users/mps19/Documents/GitHub/jolvex-platform/docs/goal/archived/20260916-215455-m11b2-implementation-closeout/RUN.md:46 (owner descoped the parity gate and used a Computer Use pass instead)
- skills/delivery-harness/references/verification-gates.md:290 (the route map gets one sentence; its app_path, states.<s>.app_eval/reference_eval and conditions keys are defined only in parity_capture.py:818-880)

Proposal: Add a `--hifi-package <dir>` reference mode to skills/delivery-harness/scripts/parity_capture.py that, for each PLAN surface_id, opens the page named by the entry `ui-hifi-manifest` surfaces[].page, uses agent-browser eval to click `[data-hifi-target-control="<breakpoint>"]` and `[data-hifi-state-control="<state>"][data-hifi-state-surface="<id>"]`, and screenshots only `[data-hifi-canvas]` (app side captured full-page at the same width, package bytes hashed into target_inputs); in that mode, ignore reference selectors and reference_eval, and ship skills/delivery-harness/assets/templates/PARITY_ROUTE_MAP.template.json carrying per route `app_path` (concrete URL for parameterised routes), `states.<state>.app_eval` and `conditions.long-content.app_eval`, linked from verification-gates.md:290.

Existing coverage, not to duplicate:
- skills/delivery-harness/references/verification-gates.md:290 (one route-map sentence plus 'Manual capture remains valid when the CLI is unavailable', a fallback, not coverage)
- skills/ui-design-builder/scripts/hifi_matrix_capture.py:268-316 (drives target/state controls and screenshots [data-hifi-canvas], but only for the design-stage HiFi check, writing outside docs/goal/evidence/)
- skills/ui-design-builder/references/matrix-capture.md (documents the design-side driver only)
- skills/delivery-harness/scripts/parity_capture.py:839-873 (route-map keys defined only in code)

### M16 [high/M] The default ui-design/3 path never compares the implementation with the approved HiFi

Area: Final Visual Parity Loop in system-conformance mode (verification-gates.md, harness_ui_evidence.py)

Problem: Nothing verifies rule 2 (HiFi composition and copy) on the normal path. check_ui_contract.py checks tokens and variants only. The screenshot matrix is judged against the pair. The evidence validator rejects an html_target baseline once a pair exists and never binds the frozen HiFi or the preview row, even though verification-gates.md:295 calls the derived HTML part of the baseline. The page-quality pass then drops its heuristic UX, accessibility and responsive checks because parity passed and the HiFi evidence is current, but that parity never looked at the HiFi. Drift from the approved HiFi in region order, element inventory or copy passes both parts of Final UI Acceptance.

Evidence:
- skills/ui-design-builder/references/stages/ui-design.md:42 (in ui-design/3 the Need Gate is always required, except under mvp, so system-conformance is the normal mode)
- skills/delivery-harness/references/ui-implementation-contract.md:27 (rule 2: the HiFi's region order, element inventory and exact copy bind implementation)
- skills/delivery-harness/references/frontend-visual-inputs.md:28 (the HiFi pages are a UI mission's primary input)
- skills/delivery-harness/references/ui-implementation-contract.md:30 (rule 5: only target-conformance runs parity_capture against the HiFi; system-conformance checks the pair plus the screenshot matrix)
- skills/delivery-harness/references/verification-gates.md:295 (system-conformance evidence is check_ui_contract plus screenshots judged against tokens and variants)
- skills/delivery-harness/references/verification-gates.md:307 (the page-quality pass shrinks to implementation-only properties when parity passes and HiFi evidence is current)
- skills/delivery-harness/scripts/harness_ui_evidence.py:532-541 (baseline must be design_system whenever a pair is frozen, so html_target is rejected)
- skills/delivery-harness/scripts/harness_ui_evidence.py:222-238 (design_system authority is only the md and json rows; the approved ui target and design system preview rows are left out)
- skills/delivery-harness/assets/templates/HARNESS_PLAN.template.md:356 (ui-design/3 PLANs freeze the approved ui target and design system preview rows)

Proposal: Behind a new harness version pin, change the system-conformance bullet at verification-gates.md:295 and the matching sentence at ui-implementation-contract.md:30 so the parity component also judges every hosted-browser matrix entry against the frozen approved HiFi with parity_capture.py, in the Page-to-PRD scope of verification-gates.md:175 (region order, element inventory, exact copy). Let the :307 page-quality shortcut apply only when that HiFi comparison passed. In harness_ui_evidence.py `_expected_authority_sources(plan, "design_system")` (lines 222-238), append the frozen `approved ui target` row whenever the PLAN has one, so a design_system target_comparison cannot validate without citing the HiFi. Keep the existing contract-check baseline_artifact.

Existing coverage, not to duplicate:
- skills/delivery-harness/references/verification-gates.md:175 (Page-to-PRD conformance row requires the HiFi's region order, element inventory and exact ui-hifi-copy/1 copy; evidence is only 'screenshots + browser geometry/reviewer note', not wired into Final UI Acceptance or any validator)
- skills/delivery-harness/references/verification-gates.md:174 (Visual design row: matches the approved HiFi surface and the active visual source within tolerance)
- skills/delivery-harness/references/design-input-updates.md:177 (both modes follow the approved HiFi surface with its ui-hifi-copy/1 copy)
- skills/delivery-harness/references/verification-gates.md:286 (parity loop claims to compare against the approved visual authority in both modes; for system-conformance that authority is defined as the pair only)
- skills/delivery-harness/scripts/harness_contract_join.py:379-384 and verification-gates.md:412 (frozen design-system preview bytes are already joined and proved at PLAN/closeout, so leaving the preview row out of target_comparison is bookkeeping, not a missing proof)
- skills/delivery-harness/scripts/parity_capture.py (no mode gate; it can already run against the HiFi in system-conformance, but nothing requires it)

### M23 [medium/M] New managed PLANs must declare the acceptance gate, but the validator checks this only under eval adoption

Area: delivery-acceptance-contract.md:17; harness_contract_join.py

Problem: For the common case, a PRD with Required TEST rows and no eval policy, a new PLAN can omit the delivery-acceptance source, the final gate and its verifier node and still validate and close. The only safeguard is a human 'gate-authoring review'.

Evidence:
- skills/delivery-harness/references/delivery-acceptance-contract.md:17 ('declare check_delivery_acceptance.py as an always-run final gate ... Gate-authoring review must reject a missing acceptance verifier')
- skills/delivery-harness/references/verification-gates.md:7
- skills/delivery-harness/scripts/eval_plan_contract.py:147 (returns [] when eval-policy applicability is not_required, which skips every acceptance-gate check)
- skills/delivery-harness/scripts/harness_contract_join.py:190-191 ('Eval adoption owns these joins')
- skills/delivery-harness/assets/templates/HARNESS_PLAN.template.md:432-436

Proposal: In eval_plan_contract.validate_eval_plan, when the RUN pin is at or after the next release and applicability is not_required, still require: one frozen delivery-acceptance source whose prd_sha256 equals the frozen PRD hash; the delivery-acceptance and final-closeout final gates, with the first checked by _command(..., "check_delivery_acceptance.py", {--repo-root, --prd, --contract, --contract-sha256 = source content_sha256, --results, --candidate-from-head}); and a pass-only path from every broad final gate through delivery-acceptance to final-closeout (give _topology a chain parameter so it no longer hard-codes eval-acceptance). Then replace the last sentence of delivery-acceptance-contract.md:17, the "Legacy PLANs without eval-policy adoption..." sentence at :78 and HARNESS_PLAN.template.md:448-453 with one line: runs pinned before that release keep readiness review as their check.

Existing coverage, not to duplicate:
- skills/delivery-harness/scripts/eval_plan_contract.py:147-195 (source, argv and topology join, but only when eval-policy applicability is required)
- skills/delivery-harness/scripts/harness_contract_join.py:186-195 (deliberately skips the delivery-acceptance source and leaves it to eval adoption)
- skills/delivery-harness/scripts/validate_worker_result.py:351-365,998-1042 (register write fence, active only when the gate is declared)
- skills/delivery-harness/assets/templates/HARNESS_PLAN.template.md:432-453 (template entries; readiness review covers only older plans with no marker)
- skills/delivery-harness/scripts/tests/test_new_run.py:149-181 (template gate entries generate)
- skills/delivery-harness/scripts/tests/test_eval_plan_contract.py:241-248 (a not_required PLAN with no final gates passes)
- skills/delivery-harness/references/delivery-acceptance-contract.md:17,78 (human gate-authoring review only)

## Acceptance And Dependencies

| ID | Expected outcome | Verification | Dependency |
| --- | --- | --- | --- |
| pending | per item above once accepted | focused tests plus the candidate matrix | round 1 landed on `main` |

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Epic proposed | the ten items the suite review deferred | `d0216c2c` | owner decision on scope |
| M14 `promotion_readback.py` | read-only `pre`/`post` for Promote To Main conditions 4, 7 and 8; contract and source-maintenance name it; READMEs name the `post` JSON (parent cross-file edit) | `843342bb`..`406f769b`, merged `f14b4740`; `e17afbee` | 12 tests, UTF-8 inventory, doc-pinning modules exit 0 |
| M23 acceptance gate required at 0.79.0+ | `eval_plan_contract` requires the frozen delivery-acceptance source, both final gates and the pass-only chain when applicability is not_required and the RUN pin is at or after 0.79.0; contract and PLAN template say older pins keep readiness review | `988ca35e`..`bf68f653`, merged `e9f3fd6b` | 27 tests, PLAN-rendering modules exit 0 |
| M15 `parity_capture.py --hifi-package` | ui-hifi/2 package reference mode driving the reviewer controls and screenshotting `[data-hifi-canvas]`; `PARITY_ROUTE_MAP.template.json`; verification-gates line 290 | `e96a37d2`..`db109381`, merged `ea534350` | parity tests, template inventory, skill contract exit 0; parent checked the `dataset.hifiState` contract against `HIFI_REVIEWER.template.html` |
| M3 shared context | `verifier_request_context.verifier_context` used by `validate_worker_result.py` and `harness_integration_results.py` | `3ae9e3c0`, merged `e7ef3725` | 34 worker-result and 9 ingestion tests exit 0 |
| M2+M4 `record-grant`, `open-run` | the first two record-only subcommands with lock, `--source`, in-memory pair validation and `push` refusal | `ea413bd3`, `f77fd035`, merged `486f6481` | 12 tests exit 0; one test that needed an invalid pair on disk was dropped, `acquire-run-lock` refuses such a pair first |
| S1 `lease-worker --packet-out` | renders WORKER_GOAL from the leased RUN, size-checks before the durable write, exclusive-create after it; runtime-adapters steps reordered; Card 4 drops the separate render and `check_launch_packet.py` step; WORKER_GOAL launch step 3 reworded at the word cap (parent) | `24d2d2af`, `e90cef35`, merged `17ce1579`; `5c0303f8`, `78b73abb` | 7 packet tests, 17 launch-packet tests, 70 skill contract tests exit 0 |
| M2+M4 `close-run`, `record-runtime`, docs | the last two subcommands, Cards 3 and 7, execution-state-model flag surfaces and grant pointer, HARNESS_GOAL line 6; parent kept `new_run.py`'s installed digest and derived `restart_required` on a digest mismatch | `6d2a3c5d`..`212f3d65`, merged `715b1832`; `51eee7ac`, `353602b2` | 22 record-command tests, 95 manifest tests exit 0 |
| M3 integration layer | `build_verifier_request.py --layer mission_integration --integrated-sha`; task and worker contexts through `verifier_context`; integration loop step 6 and Card 5 name the command (parent completed the flags) | `958b8530`..`0708cdc2`, merged `f82ca5db` | 6 request tests, documented-commands, skill contract exit 0 |
| M1a interaction pass | `hifi_matrix_capture.py` clicks and Enter/Space-activates every manifest interaction at every source target, writes `interactions` rows and `navigation` events; the first writer's hang was a payload field named `id` clobbering the driver reply id; matrix-capture reference updated (parent) | `53d3900a`, `08ec2b47`, merged `2c0c359a`; `8a4110fa` | 78 real-Chromium tests exit 0 |
| M16 HiFi comparison in system-conformance | `harness_ui_evidence._expected_authority_sources` appends the frozen `approved ui target` row for RUNs pinned at or after 0.79.0; verification-gates 297/309 and ui-implementation-contract rule 5 require the hosted-browser HiFi comparison and keep the page-quality shortcut only when it passed | `e70d9d18`, `0596c99d`, merged `ca4fae47` | 55 ui-evidence tests, 95 across the v11 and design-coverage modules exit 0; both sides of the pin tested |
| M7 `--color-scheme dark` | the whole base matrix under `colorScheme: dark` into its own `--out`; axis resets return to the run's theme | `2122d2b1`, merged `90d9cbe8` | 83 tests with real Chromium exit 0 |
| M1b reviewer rows | driver op `reviewer` measures the viewport and specimen rows in `hifi_reviewer.reviewer_contract` order after the interaction pass; `validate_output` applies the checker's `reviewer_evidence_findings`; matrix-capture gains a Reviewer object section and ui-design-pass 157 is cut to the command | `b801069f`, `4f0469e3`, merged `0baa9ab1` | 90 tests with real Chromium, review-matrix docs, ui-hifi reviewer modules exit 0 |
| M7 `--intermediate` | every non-n/a state at the midpoint of each adjacent pair of numeric viewport widths into `OUT/intermediate`, self-checked with `ui_design_v3.intermediate_width_findings`; parent fixed the fake driver's case key and kept the reviewer pass out of the sweep after the merge | `6f635532`, `843bfd93`, merged `82d17b16`; `7c552bf4` | 99 tests with real Chromium exit 0 |
| M7 `reflow-320` axis and docs | sampled states once at a 320 px canvas from the smallest target, sidecar rows like the other axes, inline width cleared after the axis; matrix-capture flags and axes text, long and localized copy judged from authored copy | `71dcdb8f`, `2182ec22`, merged `ecd5dbf2` | 103 tests with real Chromium exit 0 |

## Results And Remaining Work

All ten items landed on `feat/suite-review-r2` at `ecd5dbf2`: S1, M1 (interactions, reviewer rows, intermediate widths), M2+M4, M3 (narrowed to the shared context and the integration layer; its task and worker halves were round 1's `build_verifier_request.py`), M7, M14, M15, M16, M23. Next: 0.79.0 surfaces with `prepare_release.py`, the full matrix at the candidate with browsers required, this Epic's close, then the consumer rollout the owner asked for (pause running RUNs, install, one GLM writer per consumer, resume).

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / feat/suite-review-r2 / 8a4110fa plus this record / task/ untracked
Stage and skill: source maintenance, round 2 integration
Inputs consumed (path + hash or revision): docs/epics/EPIC-suite-review-2026-11.md backlog; workflow result wf_19618f07-bb2
Approvals in force (gate, owner, date, candidate): owner 2026-11-07: merge round 1 into local main, run round 2 with GLM 5.3 Flash writers, then update every consumer; no push, tag or install granted
Done and verified (command, exit code): per Change Log row; focused modules exit 0 at each merge
Remaining: M1b, M7, M16 integration and review; 0.79.0 surfaces; candidate matrix; Epic close; consumer rollout
Blocked / waiting (gate name or owner decision): three live writers
Next action (one command or one owner decision): merge M1b, M7 and M16 when they report, then prepare_release.py --version 0.79.0
Next owner (skill or human): harness parent
```

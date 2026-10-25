# Execution State Model

Use this reference for long, multi-mission, refined-task, or parallel execution. It defines which artifact owns each kind of state and prevents a worker result from being mistaken for an integrated result.

## System Review And Route

After an explicit `delivery-harness` request and before any PLAN/RUN artifact, task-specific skill, runtime adapter/model selection, worker preflight, or worker launch, the parent performs one bounded, read-only `System Review And Route`. It reads the user request, repository instructions, current Git state, requested scope, and available upstream product/design inputs, then records a route decision outside managed artifacts:

```text
Project size: small | large
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Route: direct | plan-backed graph
```

The stage is parent-only and cannot create or edit `PLAN.md`, `RUN.md`, `tasks.md`, evidence, branches, worktrees, or other managed state; it does not load a task skill, select a worker/model, invoke an external runtime, or spawn a worker. A small route remains direct and creates no PLAN/RUN. A large route creates the current PLAN schema v6 plus RUN schema v11 and only then enters graph readiness. The stage is not a graph node and must not be represented in `graph_state`.

## Sequential Parent Route

When no agent capability is available after routing, write missions in the large route may select `sequential_parent`: the PLAN mission remains `executor: runtime_worker`, while RUN records a parent-owned executor/worker binding solely for lease/state validation (`worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, `completion_channel: agent_result`). This binding is not a delegated or spawned worker and requires no `spawn_subagents`; the parent is the sole mission writer and executes one mission at a time. It cannot satisfy a fresh independent runtime-review node, which remains blocked until an eligible reviewer driver or allowed host exists. A parent-managed worktree is required; if it is unavailable or unauthorized, the route blocks rather than writing in `shared_checkout`.

## Three Authorities

The harness has three distinct authorities. Do not merge them into one table or infer one from another.

| Authority | Owns | Does not own |
|---|---|---|
| `PLAN.md` | Static declarations for one plan revision: requirements, traces, mission/task definitions, dependency DAGs, scopes, resource claims, verifier commands, provider/model policy, priorities, and merge ranks | Worker leases, live phase, current Git head, verifier results, authorization decisions, or selected waves |
| `RUN.md` | Mutable coordination state: readiness, explicit authorization ledger, chosen runtime capabilities, mission/task phases, leases, workers, wave proposals accepted by the parent, integration outcomes, batch/final-gate results, UI artifact metadata, landing state, blockers, and evidence pointers | Repository truth, process truth, or a new plan definition |
| Observed Git/runtime facts | The current checkout, refs, commit ancestry, diffs, worktrees, dirty state, active worker slots, process availability, and completion signals | User authorization or declarative scope |

`PLAN.md` and `RUN.md` each contain one canonical fenced JSON manifest. The exact level-two headings are `## Harness Plan Manifest` and `## Harness Run State`; the first non-empty content after each heading is its single fenced `json` block. Markdown tables — including the optional standalone `tasks.md` (`assets/templates/TASKS.template.md`), an on-demand regenerated mission/task listing view — are non-canonical human views. Tools parse the JSON manifests only; they must not recover state from prose or tables.

The parent is the only writer of `PLAN.md` and `RUN.md`. Workers return reports and evidence. The parent verifies those reports against observed facts before changing canonical state.

New managed work uses PLAN v6 with RUN v11. Legacy compact RUN-only records and older schemas remain readable history; they cannot authorize new managed execution.
To finish an older protocol, use its [exact pinned bundle](legacy-pins.md#finishing-a-run-on-its-pinned-bundle).
Do not null the current PLAN identity or migrate a live RUN to bypass a gate.
The sequential parent cannot supply independent review; use a fresh eligible reviewer or an authorized serialized host handoff.

Use exact RUN lifecycle values:

```text
status: draft | ready | running | blocked | complete
plan_readiness: draft | ready | blocked
```

`complete` is an execution closeout state, not a label the parent may set independently. Setting `status: complete` requires every applicable condition below to hold:

| Condition | Requirement |
|---|---|
| Execution intent | The run carries execution intent, not plan-only |
| Inputs frozen | Every source input is ready/frozen or accepted |
| Integration head | A `integration_head_sha` is recorded |
| Missions | Every reached mission is integrated or superseded; an untouched repair-only mission behind an untaken final-review route may stay queued |
| Tasks | Every reached live task is `mission_recorded` with a PASS verifier; an untriggered repair's tasks remain dormant/queued |
| Blockers | No blockers remain |
| Workers | No active or blocked mission or review worker |
| Waves | No proposed or active wave |
| Landing | `landing.continuity` is `preserved` with its `head_sha` equal to the integration head |
| PLAN-v6 graph run | Every node is succeeded, skipped, or superseded; every edge is terminal; no retained node blocker (a failed node must be routed or superseded before closeout). Transitions mark only taken routes, so a dependency whose source passed, and a route whose source passed with an outcome it does not match, also count as terminal. A node, and its queued mission and tasks, that only such untaken routes lead to stays dormant and does not block |
| RUN-v11 gates | Every PLAN batch and final gate has a PASS result bound to the integration head, and every required UI screenshot matrix entry is PASS; when a UI registry is supplied, the PLAN surface matrix also covers its exact responsive set, required states, and route trace/test bindings |
| Gate freshness | A changed integration head invalidates an earlier gate PASS immediately, in every RUN lifecycle state |

Current tools validate PLAN v6 with RUN v11 only.
Historical schema procedures belong to their pinned bundle, never the current execution path.

`plan_readiness: ready` is the machine gate. Human verification tables may display `PASS`, but selectors never substitute a table cell for canonical readiness.

## Generating And Validating State

Author PLAN by hand: its objective, sources and digests, traces, scopes, verifiers, graph, and acceptance rows are the real decisions.

Generate RUN with `scripts/new_run.py --plan <PLAN.md> --run-id <id> --branch <exact ref> --out <RUN.md>`. Everything a new RUN can derive from PLAN it derives: the mirrored graph state, seeded mission and task states, gate result ids, and the plan digest. Everything it cannot derive stays at its safe unset value — authorizations false, `observed` null, `batch_base_sha` unset, `plan_readiness: draft`. Generating a RUN grants nothing, and the command refuses to overwrite an existing file.

Reserve each non-mission graph attempt before its side effect with `scripts/harness_transition.py --plan <PLAN.md> --run <RUN.md> --session-id <id> reserve-node-attempt --node-id <id> --attempt-id <id> [--evidence <text>]`.
This covers approval, external-wait, lifecycle and deterministic batch/final verifier nodes.
A local verifier also needs global `--repo-root <root>` and may write `--request-out <file>` outside the checkout.
RUN retains the exact branch, head, checkout, request, digest and attempt nonce before writing that file.
If file creation fails, the request remains recoverable in `attempt_log[].verifier_dispatch.request`.

Run `verifier_runtime.py --request <file>` outside the RUN lock.
It checks branch, HEAD, clean status, tracked inputs and host execution identity before and after the command.
RUN and its declared generated tasks view remain content-protected coordination exceptions, with starting hashes and file identities attested.
Finish the reserved attempt with `record-node-result` and exactly one `--verifier-result` for a completed local check.
Result recording requires `--repo-root` and rejects replay, root/head drift, request mismatch or changed protected files.
An interrupted check records `blocked`, evidence and a blocker without inventing a result file.
Lifecycle transitions record evidence only; they never perform the lifecycle action.

Record a returned graph-backed mission payload with one locked call: `scripts/harness_transition.py --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> record-worker-result --node-result <file> --worker-result <file> --verifier-result <file>`. Repeat the verifier-result flag as needed. The transition observes the bound worker worktree's live branch, head, dirty state, `base..head` diff, and ancestry; reloads and validates the current pair, node result, worker result, and retained verifier executions inside the RUN transaction; then rechecks the worker head and PLAN before replacing RUN. A non-passing mission uses the same command with its node result and no passing worker/verifier payload. When the parent cannot trust or accept the candidate itself, use guarded `reject-worker-result --node-id <id> --worker-id <id> --outcome <retryable_failure|blocked> --reason <text>`. `scripts/validate_result.py` remains the read-only preflight when no state update is requested.

### Scripted Transition Flag Surfaces

Required flags per `harness_transition.py` subcommand, as the parser defines them:

- `pause`, `resume`, `cancel`: `--source`.
- `accept-wave`: `--wave-id`, repeatable `--mission-id`, `--batch-base-sha`.
- `lease-worker`: `--mission-id`, `--node-id`, `--worker-id`, `--lease-id`, `--attempt-id`, `--branch-ref`, and `--worktree-path`. Optional `--provider`, `--driver`, `--model`, `--reasoning-effort`, `--worker-runtime`, `--workspace-mode`, and `--completion-channel` are compatibility assertions and must match the selector-derived binding. The transition materializes exact lease targets only from an active wildcard grant without changing authorization.
- `reserve-node-attempt`: `--node-id`, `--attempt-id`; optional repeatable `--evidence` records the pre-side-effect receipt. A local batch/final verifier also requires top-level `--repo-root` and may use `--request-out` to write its directly executable verifier request.
- `record-node-result`: `--node-id`, `--attempt-id`, `--outcome`, repeatable `--evidence`; optional repeatable `--blocker` and `--verifier-result`. It requires the matching reserved attempt and derives the graph phase from the declared outcome.
- `record-observation`: requires global `--repo-root`; optional `--available-worker-slots <n>`, `--isolation-capacity <n>`, and `--capacity-evidence <text>` must be supplied together from current host observations. Non-negative counts are recorded with an attempt-log entry; omitted flags preserve existing capacity and do not discover agent slots.
- `reserve-review-dispatch`: `--node-id`, `--worker-id`, `--attempt-id`; optional `--report-path` and `--packet-out` render the reviewer packet in the same call. With `--packet-out`, optional `--diff-artifact-out` retains a complete diff at a new checkout-external path.
- `reconcile-interrupted`: `--worker-id`, `--reason`. Confirm the predecessor stopped and inspect partial work before retry.
- `record-review-attempt`: `--lineage`, `--attempt-id`, `--worker-id`, `--result`, repeatable `--evidence`; optional `--mission-id`, `--finding`, `--security-result`, and `--tree-sha`. Every non-pass result needs findings. A node with the `security` lens requires `--security-result` and derives findings from that validated object. Supply global `--repo-root` to derive the reviewed tree when `--tree-sha` is absent. Repeatable `--note` records one non-blocking observation; notes never block. `--blocker-class environment|review` applies to `blocked` results; the default is `review`. `environment` marks an inspection failure and refunds the attempt, at most twice per node.
- `reject-worker-result`: `--node-id`, `--worker-id`, `--outcome retryable_failure|blocked`, repeatable `--reason`.
- `record-integration`: `--mission-id`, `--integrated-sha`; optional repeatable `--verifier-result <absolute-external-json>`. It admits fresh protocol-v2 mission integration output and records integration in one locked, validated CAS transaction. Existing valid retained evidence remains usable without the flag.
- `reconcile-candidate-head`: `--candidate-sha`, `--source`, `--repair-node-id`, `--repair-attempt-id`, `--repair-task-id`; requires global `--repo-root` and a held `--session-id` lock. Records an already committed, authorized repair after mission integration; it never edits Git or grants repair authority.

`scripts/validate_result.py` requires `--plan` and `--run`; its optional flags include `--ancestry-confirmed` and `--repo-root`. `scripts/inspect_harness_run.py` requires `--repo-root`; `scripts/harness_step.py` accepts `--observe-only`. `--help` lists the rest.

## Plan Revisions And Snapshots

Every plan manifest has a stable `plan_id`, a positive integer `revision`, and a semantic SHA-256 digest of the `harness_plan` object. Before encoding, the shipped tools recursively canonicalize dictionaries; sort object lists with `id` by ID, resource lists by `(key, access)`, and scalar set-like lists lexically; and preserve `argv` order because command argument order is semantic. Canonical bytes are the UTF-8 encoding of `json.dumps(normalized_plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`. Reordering sources, missions, tasks, claims, or other set-like fields therefore does not change the digest. Any semantic change to mission/task definitions, dependencies, scopes, resources, or verifiers creates a new digest and requires an incremented revision.

Verifier declarations are data, not shell prose. Each verifier records at least `id`, repository-relative `cwd`, argument-vector `argv`, and a `pass_signal` label. The runtime decides PASS from exit code 0 alone, so write `pass_signal` as `exit 0`. This keeps validation independent of shell quoting and makes worker and integration gates auditable.

A worker-supplied hash is only a claim, even when it is 64 lowercase hexadecimal characters. The parent retains each `verifier_runtime.py` result, including verifier ID, immutable context, key document, exact head, status, exit result, and execution key. Worker-result validation recomputes the key from the retained key document and requires the reported verifier ID, status, and evidence key to match that parent-retained result exactly. Missing, forged, stale-context, wrong-head, or mismatched results fail closed.

Retained execution history and current PASS coverage are separate checks. Earlier executions keep their original checkpoint, attempt, lease and checkout facts; a later task commit, integration head or worktree observation does not rewrite them. Historical integration executions must belong to recorded integration history. Current task and gate PASS coverage still requires the applicable current lease and exact checkpoint or integration SHA. An old PASS is history, not permission to skip a fresh check on changed code.

When the CLI is given `--repo-root`, local sources resolve inside that root. Harness 0.38+ joined Product/UI/Design sources require exact canonical kind/path plus `content_sha256`; current bytes must match, and a supplied full-SHA `source_revision` blob must equal those same bytes. URLs are never fetched as joined authority. RUN-v11 UI evidence reads artifact, baseline, and visual-authority blobs from the accepted Git commit before decoding and comparing hashes.

Derived artifacts must bind all three values:

```text
plan_id
plan_revision
plan_digest_sha256
```

A selected wave also binds a committed `batch_base_sha`. A proposal becomes stale when its plan revision, plan digest, or base SHA no longer matches current observed facts. Recompute it; do not edit the old result into apparent validity.

PLAN authoring is a separate owner-gated discipline from a running RUN. A parent may draft and revise PLAN content, then validate that candidate with `scripts/validate_harness_plan.py` before treating a new revision as authoritative. Validators are read-only diagnostics: passing one proves the proposed bytes are well formed; it does not authorize a rewrite, recompute retained history, rebind a grant, erase receipts or attempts, or replace lock/receipt/exact-SHA evidence. Routine RUN operations use the guarded `harness_transition.py` subcommands. Initial readiness, capability/authorization recording, formal revisions, and final closeout still need their documented parent-owned procedure; do not invent a subcommand or use those authoring steps to bypass an available transition. There is no general “validate and write back” permission for RUN.

The tools have no guarded formal PLAN-revision mutation. If a substantive revision is required while a RUN is live, stop new dispatch at a safe boundary, reconcile active workers and reviews, preserve every worktree, dirty state, failed attempt, receipt, and historical RUN record unchanged, release the run lock when the session ends, and obtain a fresh owner instruction for the new revision and its exact actions. Prepare the revised PLAN as a new candidate, validate it, and continue only through the documented revision/recovery procedure with exact new authorization, or a newly authorized run pair. Never edit the live RUN to make old grants or evidence look current, reset attempt counts, discard verifier records, or relabel an old result as new-revision evidence. Keep an unchanged copy of the previous pair and review the complete state diff before writing; a validator PASS alone is insufficient.

Render the non-canonical tasks view explicitly when needed.
Use `scripts/render_tasks_view.py --plan <PLAN.md> --run <RUN.md> --out docs/tasks.md --repo-root <target-root>`.
Add `--check` to diagnose staleness. RUN transitions no longer refresh the view automatically.
The renderer preserves the Update Log and refuses a non-generated destination.

Only RUN and the declared `docs/tasks.md` carrying this run's generation marker/identity are coordination exceptions to the clean-checkout check. A hand-authored, undeclared, retargeted, or other-run view remains ordinary dirt, as do product files. No coordination commit is needed between checkpoints. After an authorized formal PLAN revision or closeout outside these transitions, explicitly render and check the view.

At every required integration or wave-close checkpoint, commit the exact declared coordination files as one ordinary direct child of the recorded integration head, then freshly observe that commit and bind it with `reconcile-coordination-head`. Supported exact paths are `PLAN.md`, `RUN.md`, `DECISIONS.md`, and `REFINEMENT_BACKLOG.md` directly under `docs/goal/` or in one bounded run namespace such as `docs/goal/pdr12/`, the historical or matching generated `tasks.md`, `docs/DOCUMENTS.md`, and one exact `docs/epics/*.md` checkpoint record. A glob, arbitrary application/package source, frozen product/design source, non-regular Git entry, or mode/type change never qualifies. From 0.55.0 RUN validation also rejects an `integration.coordination_paths` entry outside the supported paths. The guard proves live/observed head, branch, repository, PLAN identity, forward ancestry, clean product tree, and exact changed paths; it also rejects deletion, drift, replay, and active integration reviewers/parent-side checks while allowing isolated in-flight mission workers and isolated preintegration reviewers. The old head and all retained evidence remain immutable, and current exact-head review/gate projections are re-armed without changing authorization or Git.

Observed facts are read live before every mutating action. `RUN.md` may record a timestamped snapshot under `observed` for auditability, but the snapshot never replaces a fresh check.

The minimum RUN snapshot shape is:

```json
{
  "observed": {
    "captured_at": null,
    "git": {
      "parent_worktree_path": null,
      "parent_branch": null,
      "parent_head_sha": null,
      "parent_dirty": null,
      "worktrees": []
    },
    "runtime": {
      "available_worker_slots": 1,
      "isolation_capacity": 1,
      "completion_channel_available": true
    }
  }
}
```

`null` means “not observed yet,” not “safe” or “not applicable.” A selector that needs a null fact must defer or request a fresh observation.

## Canonical Mission Phases

Mission phases are finite-state values, not free-form progress notes:

```text
queued -> ready -> leased -> worker_running -> worker_passed -> integrating -> integrated
```

Terminal or interrupting phases are:

```text
blocked | worker_failed | integration_failed | superseded
```

| Transition | Required evidence |
|---|---|
| `queued -> ready` | Dependencies are integrated, gates pass, authorization permits the next action, and the mission has no blocker |
| `ready -> leased` | Parent records one worker lease bound to mission, plan revision/digest, and base SHA |
| `leased -> worker_running` | Worker identity and workspace are observable |
| `worker_running -> worker_passed` | `record-worker-result` observed the bound worktree and revalidated its head/diff/ancestry, worker/node payload, and retained verifier evidence under the RUN lock |
| `worker_failed -> worker_passed` | For a sole stale parent-head rejection, run `record-observation`, then record the unchanged result through a fresh permitted attempt. Preserve the original failed dispatch; ordinary review and integration still apply |
| `worker_passed -> integrating` | Parent rechecks ancestry, actual diff scope, forbidden files, head stability and integration authorization; under `review_policy: per_mission` also a terminal `review_workers[]` PASS bound to the exact worktree head. RUN-v11 workers never use task-local nested review evidence |
| `integrating -> integrated` | Changes are on the resolved integration branch, the integration verifier passed, and `integrated_sha` is recorded |

These phase transitions describe one run's lifecycle. Historical `run.integration.retention: "persistent"` remains readable and preserves that branch during cleanup; it does not authorize reuse as an integration target. A new managed run uses PLAN `branch_policy` under `main-preview/1` to freeze remote main for ordinary work and hotfixes. Historical RUNs retain their original pinned base. Later waves re-anchor to the current integration head, never to a moved protected branch.

`worker_passed` is not completion for dependency purposes. It means only that the worker-level gate passed in its workspace. A dependent mission becomes ready only when every dependency is `integrated`, its integration gate is `PASS`, and observed Git ancestry confirms its `integrated_sha` is an ancestor of the current integration head.

`worker_failed` preserves the terminal node evidence recorded by `record-worker-result`; a passing worker payload is required only for `worker_passed`. `integration_failed` preserves the worker-passed state plus the failed integration attempt. Neither unlocks downstream dependencies. Retrying creates a new attempt or lease; it does not overwrite the failed evidence.

## Canonical Task Phases

Tasks are executed sequentially inside one mission worker. Use the same success distinction at task scale:

```text
queued -> ready -> running -> worker_passed -> mission_recorded
blocked | worker_failed | superseded
```

`worker_passed -> mission_recorded` occurs when the parent confirms the passing task's commit/change is reachable from the reported mission head and represented by its `task_results` entry in the accepted worker result/report. The parent may record both observations in one serialized RUN update, but it must preserve the evidence distinction. A blocked/failed mission result names `current_task_id` and preserves earlier task results. `mission_recorded` does not make the mission `integrated`. Refined parent tasks use `superseded`; their replacement tasks carry the executable work.

## Recover Before Creating Another RUN

For an existing delivery, inspect the canonical PLAN/RUN, live parent Git state and owning runtime before starting work. Match run ID, PLAN revision/digest, mission, task, attempt, lease and exact SHA; a native task title or a prose completion note is not that binding. Unknown process state requires observation, not another launch.

Keep an unchanged PLAN in the same RUN through retries and authorized repairs. Preserve completed missions, original receipts and cumulative budgets. Use guarded recovery transitions; never hand-reset succeeded gates, copy old PASS evidence to a new SHA, or open a replacement RUN to escape a checker or exhausted budget. A new initiative, substantive PLAN revision or incompatible legacy binding follows the explicit revision/replanning boundary and preserves the old pair unchanged.

Separate historical evidence from current coverage. Reconcile only the parent and currently relevant workspaces, then reserve a fresh attempt for each required check on the current candidate. A failed or blocked observation is not permission to skip reconciliation. Refresh the declared tasks view from RUN and verify it with `--check` at handoff. Native completion, manifest validity and exact-candidate verification are separate results.

## Resume Reconciliation Gate

The inspector reports live parent Git identity separately from recorded observations and the canonical integration identity. A branch/head mismatch or missing integration object needs reconciliation; a blocked Git authority check is an observation failure. Unknown Git or process state is never proof of alignment or liveness. This diagnostic summary does not replace formal PLAN/RUN validation.

A `running` RUN can be picked up by a different session than the one that last touched it — the same host resuming after an interruption, or a different agent entirely. Before that parent selects or launches any ready node, it must reconcile the observed working tree against canonical `task_states`/`mission_states`, not just trust the last recorded checkpoint. Start with `inspect_harness_run.py` as `SKILL.md` directs; it exits 1 when any mission needs reconciliation, and its summary shows the recorded run lock and control state. Before dispatching work that consumes a project-bound skill slot, also verify that binding's pin with `python "<delivery-harness-skill-root>/scripts/check_skill_bindings.py" --stage <stage>` using `references/installed-commands.md`; choose the actual upcoming stage from the approved scope, never reuse a product-definition result for delivery. A mismatch is a review moment, not a silent swap.

The inspector's attempt-recovery summary is read-only. It counts only retained `kind: dispatch` entries whose recorded result is a declared failure and shows the most recent retained failure evidence in list order; it never infers counts from attempt-ID suffixes. `worker_running` and dirty output are not proof that a process is alive or dead; the owning runtime must observe liveness. Treat `integrated` or `superseded` drift as historical evidence, keep active-worker drift separate, preserve all retained attempts, grants, and verifier contexts, and keep the existing reconciliation flags and exit codes. Confirm interruption with the owning runtime before using `reconcile-interrupted` or `reconcile-interrupted-reviews` under the required RUN lock. Use `record-node-result` or `record-worker-result` only for a matching current reserved attempt or lease; new work gets a new attempt. Never rewrite or rebind old evidence.

Read `observed.git.parent_dirty` and the actual diff live. If the checkout is dirty, map every changed path to the task(s) whose `write_scope` covers it. Any dirty content that falls inside a task still at `queued`, `ready`, or `running` — i.e. not yet `worker_passed` — is drift: real work exists that canonical state does not account for.
Drift blocks new work. Resolve it before advancing, by one of:

- Running the covering task's own verifier against the current dirty state. If it passes, commit per `commit-convention.md` and record the task as `worker_passed` (then `mission_recorded` once integration-reachability is confirmed) so canonical state now matches reality.
- If the drift does not pass verification, is partial, or its origin is unclear, stop and ask the user how to proceed (finish and verify it, stash it, or discard it) rather than silently building further work on top of unverified, unrecorded state.

Never treat a dirty checkout as "safe to ignore" or "safe to build on" without this reconciliation.

A resume snapshot is usable only when the parent checkout path, branch, head, and clean/dirty state are all known. Enumerate linked worktrees, then reconcile the current parent and currently bound mission/review workspaces to their exact paths, branches, heads and clean state. A missing, dirty or mismatched relevant workspace blocks the frontier. Unrelated linked worktrees and retained historical workers do not become current dependencies merely because they appear in the inventory. Apply the same checks to a `ready` RUN that already contains active work. A stale RUN snapshot is not a safe default.

Reconcile the current host and loaded Harness release through `runtime_capabilities.runtime_adapter.version_gate` as a separate observation. Follow `runtime-upgrades.md`. `unobserved`, `upgrade_required`, `restart_required`, and historical `adopted` defer current runtime-worker dispatch. `compatible_old` may finish only the already-active wave and its streaming reviews; it defers the next wave. A runtime update never revives a lease.

At resume, a worker recorded as `leased` or `worker_running` requires observation of its owning runtime before the parent treats it as live or interrupted. A phase alone does not block unrelated ready work during a live wave: passing siblings can enter streaming review while other verified bindings remain active. After a confirmed stopped review fan-out, use `harness_transition.py reconcile-interrupted-reviews` once with every affected review worker ID. The transition records each interrupted attempt as blocked, preserves attempt counts in the append-only attempt log, resets the current review nodes, removes incoming edge traversals that have no current or retained source attempt, and persists `control.desired_state: paused`. It does not grant another review attempt or resume dispatch. When the interrupted worker was a security reviewer, the matching attempt receipt records `interrupted_review_reconciliation`; only that exact receipt permits the blocked worker to omit `security_result`. It is interruption evidence, never a security decision or PASS. After a later current reviewer supplies the exact structured PASS, the receipt-bound historical worker may remain without blocking closeout.

## Repairing The Integrated Candidate

For the optional isolated repair mission, follow `graph-orchestration.md#optional-repair-only-mission`. First-pass approval leaves it dormant; a finding activates one repair and one targeted recheck.

The additional historical-review admission preserves a passed or failed integration reviewer at a recorded prior head after its current graph binding is cleared. It requires a unique retained review attempt, matching outcome and lineage. A blocked reviewer qualifies only through the existing interrupted-review reconciliation receipt, using the same predicate as closeout. Other blocked or active old reviewers remain invalid and refuse candidate movement before RUN persistence. The older fix_required prior-head rule keeps its pinned semantics. Its retained bytes and receipts stay unchanged. This admissibility does not revive its PASS or security coverage for the new candidate.

For a repair within the unchanged PLAN after all missions have integrated, keep the existing RUN. After separately authorized edits, verification and commits, observe the clean parent checkout and run `harness_transition.py --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> reconcile-candidate-head --candidate-sha <full-live-HEAD> --repair-node-id <failed-node> --repair-attempt-id <failed-attempt> --repair-task-id <mission/task> --source <repair-evidence>`. The transition requires the exact observed non-default integration checkout, forward ancestry, the exact current failed gate/review attempt, one declared repair task and its write scope, existing exact commit/integration grants, no active workers or attempts, and remaining revalidation budgets. A completed RUN cannot be reopened by this command.

The old candidate enters `integration.prior_head_shas`; mission/task completion and historical receipts remain intact. Current gates and integration reviews must establish fresh coverage for the new head. Attempt counts and authorization grants are preserved, including exhausted limits. Reconcile and rerun the affected current gates instead of replaying completed missions, replacing the RUN, or relabeling old evidence. A change to product scope or PLAN still follows the formal revision procedure.

This recovery accepts a concrete `fix_required` or `retryable_failure` verifier result, or an integration review's `fix_required` result. A `contract_gap` or an unexplained `blocked` result is not a repair grant. An inactive routed integration review already marked `skipped` cannot carry an old candidate's tree proof forward; candidate reconciliation refuses that unsupported graph shape without changing RUN. Resolve it through the formal refinement boundary.

## Mid-Run Modification Recording

The drift rules above fire at resume; the same duty applies while the run is live. Un-checkpointed work of an existing task is drift and stays with that task under the rules above; review-driven repair likewise stays inside the mission it repairs, as a new attempt on the same work. Everything else that appears during the run — an extra fix, a follow-up edit, or a change the user reports mid-run — is new content, never folded into a mission that happens to be nearby.

Record each such modification as its own mission: open it through a plan revision before the edits continue (`contract-and-traceability.md`), give it its own tasks and verifier, and run it through the normal lease, worker, and integration phases. Then regenerate `docs/tasks.md` with `scripts/render_tasks_view.py`; it groups one section per mission, newest first.

A mid-run modification is done when it is recorded in RUN and visible in the tasks view, not when the edit lands. Nothing stays only in the working tree or only in the conversation.

Before the completed coordination set is archived, append every owner or agent update not already reflected in `docs/product/PRD.md` to the preserved `docs/tasks.md` Update Log. Product-affecting changes also update the PRD in the same change. Archive candidate A then freezes that log with the RUN; the PRD remains the persistent product record. Activation, outcome review, and SEO happen only after A reaches `main` and production is verified, so their findings belong to their own operational records or a later enhancement, never a reopened archived RUN.

## Typed Graph State

PLAN v6 and RUN v11 carry the typed-graph contract: typed nodes, explicit dependency/route edges, and one `graph_state` object with the matching plan revision, one state per node, and one state per edge. The graph state is the routing authority; mission state remains the operational lease, Git, worker, and integration detail for mission nodes.

Use node phases:

```text
dormant | ready | running | succeeded | failed | blocked | skipped | superseded
```

Use declared outcomes only:

```text
pass | fix_required | retryable_failure | blocked | contract_gap
```

Every node state records `attempts`, `last_attempt_id`, `last_outcome`, optional bound worker, and blockers. Every edge state records `status`, traversal count, and source attempt. A terminal node requires an attempt identity and outcome. A mission node may become `succeeded/pass` only when its mission is `integrated` with an integration `PASS`; the validator rejects either side claiming completion without the other.

Non-mission nodes use a two-step attempt invariant: `reserve-node-attempt` changes a dispatchable `approval`, `external_wait`, `lifecycle`, or deterministic batch/final verifier node to `running` and appends a `node_attempt` receipt; `record-node-result` may terminate only that matching running receipt. Its phase projection is deterministic — `pass` becomes `succeeded`, `blocked` or `contract_gap` becomes `blocked`, and `fix_required` or `retryable_failure` becomes `failed` — while the declared outcome remains the route signal. Evidence is required at result time. A stopped or otherwise interrupted non-runtime attempt is completed as `blocked` through `record-node-result`; approval, external-wait, and deterministic-verifier `retryable_failure` may retry directly while budget remains, but lifecycle retry requires an explicit bounded route because its side effect may be unknown.

Dependency edges always consume `pass` and remain acyclic. Route edges activate from declared outcomes. A cyclic route requires a PLAN traversal bound and an exit. A retry or subgraph replay creates new attempts and preserves old evidence; it never revives a lease, action grant, base/head binding, or verifier result.

Run `python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan docs/goal/PLAN.md --run docs/goal/RUN.md --repo-root <absolute-root> record-observation` before selection.
Global flags precede the subcommand. Record actual Git facts and capacity from the host; never infer process liveness from RUN phases.
Every authority-bearing Git read disables replacement objects and rejects replace refs plus legacy graft metadata before trusting a SHA.
Current selection requires PLAN v6 with RUN v11.

Task, worker, mission-integration, batch and final verifier declarations use explicit `execution.isolation: "host"`.
Missing, container and snapshot modes are invalid in current tools.
Host commands run fresh and serially per runner with exact source/Git guards; worktrees do not confine operating-system permissions.
Browser, network, external-service and mutable-environment operations retain their own routes and action authorization.
The derived `execution_route` is `managed_sequential` for fewer than two selected writers, or `parallel_graph` for two or more.
`runtime_driver` remains a separate transport fact. Follow `graph-orchestration.md` for routing.

## Authorization Action Ledger

Authorization is action-specific. Overall `execution_authorized` also has siblings `execution_authorization_source` and `execution_authorization_scope`; when true, both must match the run, mission, and expiry boundary. Every action entry defaults to `authorized: false` and records an explicit user source before it can become true. A goal, plan, template, skill selection, worker report, or assistant assumption cannot authorize itself.

The ledger has exactly 12 actions:

```text
invoke_external_runtime
spawn_subagents
create_user_owned_tasks
create_local_worktrees
create_app_managed_worktrees
create_local_branches
create_local_commits
integrate_locally
push
archive_worker_tasks
remove_worktrees
delete_branches
```

`invoke_external_runtime` is required when the Harness parent starts a different provider process or service. Its target is `runtime:<provider>`. It does not replace `spawn_subagents`, worktree, branch, commit, integration, or lifecycle authorization. Pre-0.58 pins follow [legacy pins](legacy-pins.md#pre-058-runtime-dispatch). A configured external bridge requires this key and `spawn_subagents`; PLAN host eligibility still applies. It remains a parent rule for external processes the parent starts itself.

The ordinary execution loop uses only the applicable local entries. Parent-dispatched sibling workers and reviewers require their exact launch authorization. App-task dispatch is historical and unsupported by the current driver set. "Implement", "build", "fix", or "refactor" never implies a remote action. Harness 0.38+ keeps RUN `push` false; after A exists, a new exact instruction is captured in the checkout-external request instead of the archived RUN. All 12 keys remain for schema compatibility.

For a large `sequential_parent` route, leave `spawn_subagents`, `create_user_owned_tasks`, and `create_app_managed_worktrees` unauthorized and unused. The route's parent-owned worktree/branch/commit/integration actions still require their own matching grants.

Pre-0.38 RUN-v11 push recovery follows [legacy pins](legacy-pins.md#pre-038-run-branch-push). Harness 0.38+ rejects that path before any side effect. Post-archive publication follows `branch-promotion-contract.md#managed-run-archive-before-promotion`. Neither path can target `main` or `development`.

Each `authorizations` entry has this minimum shape:

```json
{
  "authorized": false,
  "source": null
}
```

When `authorized` is true, add a required `scope` object with `run_id`, `mission_ids`, and exact `targets`, plus `expires_when`. Schema v10 additionally requires `plan_revision` and `plan_digest_sha256` in that scope, and both must equal `run.plan.revision` and `run.plan.digest_sha256`:

```json
{
  "authorized": true,
  "source": "<exact user statement>",
  "scope": {
    "run_id": "<run id>",
    "plan_revision": 3,
    "plan_digest_sha256": "<64-hex>",
    "mission_ids": ["M1"],
    "targets": ["branch:refs/heads/<exact-run-branch>"]
  },
  "expires_when": "run_complete"
}
```

That pair is what makes `SKILL.md`'s rule real: when the plan revision or digest changes, the scope stops matching and the grant stops covering anything, instead of silently carrying forward. Below v10 the scope has no plan binding, so nothing compares one — the invalidation rule is inert there and a v7-v9 grant survives a plan change untouched.

Targets use action-specific prefixes, and there are only five: `worker:`, `task:`, `worktree:`, `branch:`, and `runtime:`. The kind is part of the action's type, so every action accepts only its own kinds and this is always enforced — there is no per-artifact opt-in. `expires_when` is `wave_closed`, `run_complete`, or `explicit_revocation` and is evaluated against current RUN state. Use `"*"` only for a dimension the user explicitly authorized run-wide. A selector/coordinator treats missing, expired, or nonmatching scope as unauthorized; authorization is never a global boolean inferred for every mission or target.

When a `"*"` grant covers a launch, the transition records the exact target as a receipt in the same grant: `lease-worker` for mission workers and `reserve-review-dispatch` for a subagent reviewer (`worker:<id>`). RUN-v11 validation requires each mission worker launch receipt (`worker:`, `task:`, `worktree:`, `branch:`) under exact `mission_ids` at every version, and each current subagent reviewer needs its exact `worker:` authorization receipt. So the selector defers those launches and `lease-worker` refuses a mission launch whose grant lists `"*"` in `mission_ids`.

A `"*"` grant may cover `archive_worker_tasks`, `remove_worktrees`, and `delete_branches`, but their PLAN lifecycle node must name an exact `target`: `reserve-node-attempt` refuses one without it, and a cleanup PASS recorded against `"*"` fails validation. `delete_branches` never covers `main`, `development`, the observed default branch, or their full `refs/remotes/<remote>/<name>` equivalents; from 0.55.0 a grant listing one is also invalid. The guard is exact rather than origin-specific: an unqualified `<remote>/<name>` target is an ordinary branch name unless it equals the observed default.

`wave_closed` is one-use authorization for the currently recorded wave. Its scope must add the immutable `wave_id` and `batch_base_sha`, and both values must equal the current `active_wave` while that wave is `proposed` or `active`. When that wave becomes `closed` or `superseded`, append its `{ "wave_id", "batch_base_sha" }` pair to the v10 RUN's durable `closed_waves` list before replacing or re-proposing `active_wave`. Every matching action entry then returns to `{ "authorized": false, "source": null }`, and overall execution authorization is cleared when it used the same boundary. Never copy or revive a wave-scoped grant for a pair already in `closed_waves`; a new wave needs a newly recorded explicit source and a new identity/base pair. Legacy RUN schemas remain readable without this v10 history field.

A `run_complete`-bounded authorization stays valid evidence at closeout even after its boundary expires — do not erase the record of what was authorized and done just because the run finished.

`source` identifies the user statement or durable approval record. Narrow authorization remains narrow:

- Static conflict and parallel-eligibility analysis performed by the parent does not require implementation, worktree, branch, commit, or integration authorization. A launch-bound ready frontier and selected wave do require execution plus all launch-path authorizations. Delegating even read-only analysis still requires `spawn_subagents` or `create_user_owned_tasks`, according to the chosen worker primitive.
- `spawn_subagents` does not authorize user-owned app tasks.
- Worktree creation does not authorize branch creation, commits, integration, or cleanup.
- Local integration does not authorize branch deletion, worktree removal, or any `push`. Current RUNs remain local-only; legacy recovery and post-archive publication require their own exact grants.
- Platform-managed retention is not a harness cleanup action and may still apply to app-managed worktrees.

Before each action, check its entry again and compare it with observed state. A previously authorized action can still be unsafe because the target changed or the plan became stale.

## Landing State

RUN v11 keeps the four-key `landing` shape for compatibility:

```text
mode: local_only
remote
pushed_head_sha
continuity: { status, branch_ref, head_sha, reason }
```

A Harness 0.38+ RUN starts and ends `local_only` at candidate C. `pushed_head_sha` stays null, the RUN push authorization stays false, and the graph has no push lifecycle node. The complete archived RUN remains bound to C; writing later candidate A into it would change A and create a self-reference.

Archive, publication and promotion follow `branch-promotion-contract.md#managed-run-archive-before-promotion`; a post-A failure follows `branch-promotion-contract.md#post-a-candidate-or-preview-failure`.

`integration.branch` is the only mutable branch field in RUN. It names the non-protected run branch; `PLAN.branch_policy.base_ref/base_sha` is the frozen immutable source declaration. The optional `observed.git.default_branch` fact is only a push safety observation. Cleanup can never spend a wildcard or old-RUN grant on protected `main` or existing `development`.

`continuity` records that the run branch survives the run — it is what the user reads and lands:

```text
status: planned | preserved | blocked
```

`planned` and `preserved` require a full local `refs/heads/` ref in `branch_ref`. `preserved` also requires `head_sha`. `blocked` requires a `reason`. Authorized execution requires `planned` or `preserved`; a `complete` run requires `preserved` with `head_sha` equal to the integration head.

## Runtime Capability Axes

Record provider, supported driver, worker runtime, workspace and completion channel without inferring capabilities from product labels.
Host policy owns concrete tools, models, effort and fallbacks; `runtime-adapters.md` owns the dispatch procedure.

### Runtime adapter and routing

`runtime_adapter` records the observed lowercase `provider`, ordered `available_drivers`, `detection_source` and version gate.
The current drivers are `subagents` and `sequential_parent`.
A user-owned app-task request is unsupported; block it rather than silently replacing it.
Historical app/task fields remain retained history, interpreted only by their [pinned bundle](legacy-pins.md#finishing-a-run-on-its-pinned-bundle).

Missing grants do not erase capability. Unknown loaded identity stays unknown.
A historical `adopted` status defers current dispatch with `pinned_bundle_or_restart_required`.
See `runtime-upgrades.md` for digest, restart and legacy-pin handling.

### Reviewer tool capabilities

A visual reviewer must attach a real browser and report actual inspection evidence.
A parent's browser connection or a role name does not prove reviewer capability.
A missing required tool blocks the review; source-only review cannot supply a visual PASS.

### Worker runtime

Use `subagent` for a delegated child or `parent` for actual sequential-parent execution.
The selector derives the matching portable binding from observed host capabilities and PLAN options.
Unsupported explicit model or effort choices block without substitution.

### Workspace mode

`parent_managed_worktree` is required for mission writes, including sequential-parent work.
`shared_checkout` is limited to direct sole-writer work or read-only analysis.
A worktree isolates repository files, not ports, databases, secrets or operating-system permissions.

### Completion channel

Use the selected driver's actual result channel: `agent_result` or supported `report_file`.
Prefer terminal events or waits. Use bounded polling only when neither is available, and record that limitation.

### Flat parent-owned delegation

Workers and reviewers never delegate.
The parent dispatches every explorer, writer and reviewer as a sibling under its own authorization and attempt budget.
One writer owns each exact-base checkout.

### Permission boundary

Observe the actual parent/child permissions before launch.
They must cover linked-worktree Git metadata, temp/cache paths, network destinations, local bindings and required sockets.
A prompt or profile label does not prove permission-level isolation, and permissions never grant an action.

## Capability Gate

Before leasing or fanning out a mission, the parent must prove all applicable rows:

| Check | PASS condition |
|---|---|
| Runtime available | Chosen `worker_runtime` exists in this session and its authorization entry passes |
| Workspace available | Chosen `workspace_mode` can be created or observed without overwriting existing work |
| Write isolation | Every plan-backed write mission uses an eligible isolated worktree; `shared_checkout` is direct/read-only only and cannot satisfy `sequential_parent` |
| Completion observable | Chosen `completion_channel` can return a terminal result, blocker, or failure to the parent |
| Integration observable | Parent can obtain base SHA, worker head SHA, actual changed paths, and verifier evidence |
| Resource isolation | File scopes and every runtime resource have complete, supported claims |
| Lifecycle understood | Branch/ref durability and retention behavior are recorded |
| Permission boundary | Parent mode/profile and inheritance are observed; every required filesystem, Git metadata, temp/cache, network, local-binding, and socket surface is covered without an unresolved prompt |
| Runtime route | Provider and available drivers are observed; the deterministic selected driver matches the declared runtime/workspace/completion axes |
| Flat worker topology | Every worker and reviewer remains a parent-dispatched sibling and never delegates |

If any capability, isolation, permission, or completion row is unknown, do not fan out. Observe it first; if it remains unavailable, select the real `sequential_parent` route defined above and apply the same verification gates. Missing launch authorization is not an unknown capability: request the exact run-wide launch bundle once and pause rather than rewriting the runtime adapter or silently downgrading.

The configured write-worker maximum follows `stages/managed-delivery.md#default-runtime-and-wave-policy`. Deterministic mission selection is the default immediately after Plan Readiness and execution authorization; run validation and selection before any production task. The effective wave remains the minimum of that configured maximum, live worker slots, isolated workspaces, dependency-ready nonconflicting missions, and every capability and permission gate above.

## Run Lock And Watchdog

Durable execution for one RUN has two machine guards; both are `harness_transition.py` subcommands.

- **Run lock**: before dispatching, the parent records `run.run_lock` (`session_id`, `acquired_at`, `heartbeat_at`) with `--session-id <id> acquire-run-lock` (the flag goes before the subcommand) and refreshes it with `--session-id <id> heartbeat-run-lock`; any successful transition by the holding session also refreshes the heartbeat. Every mutating transition refuses a lock held by another session — fresh, stale, or with an unparseable heartbeat — so two parents cannot dispatch against the same state; a stale or unparseable foreign lock is taken over only through the explicit `watchdog --reclaim` or `acquire-run-lock` path. The dispatch commands (`accept-wave`, `lease-worker`, `reserve-node-attempt`, `record-node-result`, `record-worker-result`, `reject-worker-result`, `reserve-review-dispatch`, `record-integration`, `reconcile-candidate-head`, `close-wave`) additionally require the calling session to already hold the durable lock. Separately, every `harness_transition.py` process takes a short operating-system lock keyed to the RUN path across its PLAN/RUN load, validation, mutation, and atomic replace, which also serializes two commands from the same session. The writer compares the expected destination text, writes a same-directory temporary file, and uses `os.replace` under the OS lock. A detected conflicting edit is refused. Release the durable lock with `release-run-lock` when the session ends.
- **Watchdog**: `watchdog [--stale-after-minutes N]` reports read-only whether the lock is live or stale and lists `running` nodes that lost their parent heartbeat as interrupted-work candidates; `--reclaim` clears a stale lock so the reconcile transitions can run.

RUN coordination paths protect `docs/goal/DECISIONS.md`, the parent-owned mid-run decision log.
Record each owner decision with its ID, question, decision, source and date. Workers never write that log.
`new_run.py` declares the coordination paths; render and check `docs/tasks.md` explicitly at handoff.

## Serialized Same-Repository Host Handoff

Hosts may hand off a large plan-backed run only as a serialized, same-repository operation. Host A must close the active wave: `RUN.active_wave.status` is neither `active` nor `proposed`. The `active_wave` object remains part of RUN; an absent object is not proof that handoff is safe. The handoff never transfers a live lease, hides a worker, or starts a second writer. Preserve the canonical PLAN/RUN and graph state, mission/task evidence, and current exact head SHA. Do not invent a new schema field or identity from the handoff.

Host B must validate the preserved PLAN/RUN and exact SHA, then re-probe its own runtime version, loaded Harness version, permission, isolation, and completion capabilities. Replace the old `runtime_adapter`/observed capability snapshot with Host B's fresh snapshot before selecting work or running the next read-only review; do not merge Host A's capability claims into Host B's. Terminal worker and review records remain historical evidence with Host A's original bindings. Any live or newly allocated attempt must instead match Host B's provider and selected driver. Host B uses the same graph and exact-head review gates and may proceed only from a clean, reconciled state.

If Host B's review returns `fix_required`, route the findings back to Host A's original mission/worktree for repair. The old review is invalid; any new head invalidates the prior review and requires a fresh verifier and the reviews `verification-gates.md#review-topology` requires before integration or another handoff. This is a serialized file/repository handoff, not an in-session bridge or automatic cross-host invocation. Cross-machine handoff is unsupported until a future schema defines a portable workspace identity and evidence transport; do not claim that a shared repository path alone provides that bridge.

## Parent-Owned Wave State

The selector produces a pure proposal. Only the parent may accept it into `RUN.md` as `active_wave`. The accepted wave records at least:

```text
wave_id
status: idle | proposed | active | closed | superseded
plan_revision
plan_digest_sha256
batch_base_sha
selected_missions
deferred_missions and reason codes
```

RUN schema v11 also carries an append-only `closed_waves` list of
`{ wave_id, batch_base_sha }` pairs. Append a pair before closing or
superseding that wave; a proposed or active wave may not reuse a pair already
listed there. A `wave_closed` grant is valid only when its scope matches the
current pair and that pair is absent from `closed_waves`. Older RUN schemas do
not require this field and remain readable.

Each mission lease and worker record binds the mission, attempt, PLAN revision/digest and batch base.
`lease-worker` copies the selector's portable runtime binding and validates compatibility flags.
The parent records the actual launched session, model and result origin in attempt evidence.
Accept only that session's result; record failed starts as `blocked` with the host error.

Worker status, head SHA, integration result, and evidence are live RUN state. A wave stays `active` while its selected workers run, and `record-worker-result` accepts a result only against that active wave and the current bound attempt. During the active wave the selector blocks new writers and lifecycle mutations, but dispatches any dependency-ready read-only node: under `review_policy: per_mission`, a pre-integration review for a selected mission already at `worker_passed`; an approval; or an external wait. Read-only nodes hold no lease, produce no commit, and move no head, so they cannot perturb a live writer. The parent records terminal worker results as they arrive and re-runs selection. A mission may integrate before the wave closes once its gate passed (under `per_mission`, its exact-head review PASS); integration stays strictly serial, so at most one mission is `integrating` at a time. The wave closes as soon as every selected mission's worker result is recorded. Batch gates always follow wave close. Any worker failure, integration failure, dependency change, or plan revision also closes the wave and forces a recompute from current state. A plan revision supersedes every active old-revision lease: quiesce those workers at safe boundaries and issue new leases only after validating their preserved heads against the new plan. Never carry forward an old result, conflict, or readiness assumption.

Closing a wave is a guarded transition, never a hand edit: `harness_transition.py ... close-wave --source <text>` refuses while any worker or review worker is still live (reconcile them first) and while any selected mission is still queued or running. A `worker_passed` mission may close with the wave — its worker result was recorded by `record-worker-result` and its integration may complete after the close — but only while overall execution authorization survives the boundary: a `run_complete`-bounded grant does, while a `wave_closed`-bounded grant dies at close and therefore requires those missions to integrate, fail, or reconcile first. The command appends the `{ wave_id, batch_base_sha }` tombstone, flips the wave to `closed`, resets every `wave_closed`-bounded action grant to `{ "authorized": false, "source": null }`, and clears overall execution authorization when it used the same boundary; `run_complete`-bounded grants survive as closeout evidence. The next `accept-wave` must name a fresh wave identity and base pair. The write-path guards are likewise enforced by the tooling: `accept-wave` requires a live clean product tree on the observed non-protected run integration branch and head; `lease-worker` binds the mission's own graph node, derives its full runtime binding, validates the portable axes, and refuses conflicting concurrent missions; `record-integration` proves the integrated head against live Git. Each command fails closed on stale state.

Observe actual required capabilities before dispatch; host names do not prove them.

# Execution State Model

Use this reference for long, multi-mission, refined-task, or parallel execution. It defines which artifact owns each kind of state, so a worker result is never mistaken for an integrated one.

## System Review And Route

After an explicit `delivery-harness` request and before any PLAN/RUN artifact, task-specific skill, runtime adapter/model selection, worker preflight, or worker launch, the parent performs one bounded, read-only `System Review And Route`: it reads the request, repository instructions, Git state, scope, and upstream product/design inputs, then records a route decision outside managed artifacts:

```text
Project size: small | large
Intent: plan-only | plan-then-stop | plan-then-execute | execute-ready-plan
Route: direct | plan-backed graph
```

The stage is parent-only. It cannot create or edit `PLAN.md`, `RUN.md`, `tasks.md`, evidence, branches, worktrees, or other managed state, and does not load a task skill, select a worker/model, invoke an external runtime, or spawn a worker. A small route stays direct with no PLAN/RUN; a large route creates the current PLAN schema v6 plus RUN schema v11 and only then enters graph readiness. The stage is not a graph node and never appears in `graph_state`.

## Sequential Parent Route

With no agent capability after routing, large-route write missions may select `sequential_parent`. The PLAN mission stays `executor: runtime_worker`; RUN records a parent-owned executor/worker binding solely for lease/state validation (`worker_runtime: parent`, `workspace_mode: parent_managed_worktree`, `completion_channel: agent_result`). It is not a delegated or spawned worker and requires no `spawn_subagents`; the parent is the sole mission writer and executes one mission at a time. It cannot satisfy a fresh independent runtime-review node, which stays blocked until an eligible reviewer driver, an allowed host, or an authorized serialized host handoff exists. A parent-managed worktree is required; if it is unavailable or unauthorized, the route blocks rather than writing in `shared_checkout`.

## Three Authorities

The harness has three distinct authorities. Do not merge them into one table or infer one from another.

| Authority | Owns | Does not own |
|---|---|---|
| `PLAN.md` | Static declarations for one plan revision: requirements, traces, mission/task definitions, dependency DAGs, scopes, resource claims, verifier commands, provider/model policy, priorities, merge ranks | Worker leases, live phase, current Git head, verifier results, authorization decisions, selected waves |
| `RUN.md` | Mutable coordination state: readiness, explicit authorization ledger, chosen runtime capabilities, mission/task phases, leases, workers, parent-accepted wave proposals, integration outcomes, batch/final-gate results, UI artifact metadata, landing state, blockers, evidence pointers | Repository truth, process truth, a new plan definition |
| Observed Git/runtime facts | The current checkout, refs, commit ancestry, diffs, worktrees, dirty state, active worker slots, process availability, completion signals | User authorization or declarative scope |

`PLAN.md` and `RUN.md` each hold one canonical fenced JSON manifest under the exact level-two headings `## Harness Plan Manifest` and `## Harness Run State`; the first non-empty content after each heading is its single fenced `json` block. Markdown tables, including the optional standalone `tasks.md` (`assets/templates/TASKS.template.md`, a regenerated mission/task view), are non-canonical human views; tools never recover state from prose or tables. The parent is the only writer of both files and checks worker reports against observed facts before changing canonical state.

New managed work uses PLAN v6 with RUN v11, the only pair current tools validate. Legacy compact RUN-only records and older schemas remain readable history and cannot authorize new managed execution.
To finish an older protocol, use its [exact pinned bundle](legacy/legacy-pins.md#finishing-a-run-on-its-pinned-bundle).
Do not null the current PLAN identity or migrate a live RUN to bypass a gate.

Use exact RUN lifecycle values:

```text
status: draft | ready | running | blocked | complete
plan_readiness: draft | ready | blocked
```

`complete` is an execution closeout state, not a label the parent may set independently. Setting `status: complete` requires every applicable condition below:

| Condition | Requirement |
|---|---|
| Execution intent | The run carries execution intent, not plan-only |
| Inputs frozen | Every source input is ready/frozen or accepted |
| Integration head | `integration_head_sha` is recorded |
| Missions | Every reached mission is integrated or superseded; an untouched repair-only mission behind an untaken final-review route may stay queued |
| Tasks | Every reached live task is `mission_recorded` with a PASS verifier; an untriggered repair's tasks stay dormant/queued |
| Quiescence | No blockers, no active or blocked mission or review worker, no proposed or active wave |
| Landing | `landing.continuity` is `preserved` with `head_sha` equal to the integration head |
| PLAN-v6 graph run | Every node is succeeded, skipped, or superseded; every edge is terminal; no retained node blocker (route or supersede a failed node first). A dependency whose source passed, or a route whose source passed with a non-matching outcome, counts as terminal; a node (with its queued mission and tasks) reachable only through untaken routes stays dormant and does not block |
| RUN-v11 gates | Every PLAN batch and final gate has a PASS bound to the integration head, and every required UI screenshot matrix entry is PASS; with a supplied UI registry, the PLAN surface matrix also covers its exact responsive set, required states, and route trace/test bindings |
| Gate freshness | A changed integration head invalidates an earlier gate PASS immediately, in every lifecycle state |

`plan_readiness: ready` is the machine gate; selectors never substitute a table cell for it.

## Generating And Validating State

Author PLAN by hand.

Generate RUN with `scripts/new_run.py --plan <PLAN.md> --run-id <id> --branch <exact ref> --out <RUN.md>`. It derives everything PLAN determines; the rest stays at its safe unset value (authorizations false, `observed` null, `batch_base_sha` unset, `plan_readiness: draft`). Generating a RUN grants nothing and refuses to overwrite an existing file.

Reserve each non-mission graph attempt before its side effect with `scripts/harness_transition.py --plan <PLAN.md> --run <RUN.md> --session-id <id> reserve-node-attempt --node-id <id> --attempt-id <id> [--evidence <text>]`.
A local verifier also needs global `--repo-root <root>` and may write `--request-out <file>` outside the checkout; if file creation fails, the request stays recoverable in `attempt_log[].verifier_dispatch.request`.

Run `verifier_runtime.py --request <file>` outside the RUN lock.
Finish the reserved attempt with `record-node-result` and exactly one `--verifier-result` for a completed local check; recording requires `--repo-root`.
Lifecycle transitions record evidence only; they never perform the lifecycle action.

Record a returned graph-backed mission payload with one locked call: `scripts/harness_transition.py --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> record-worker-result --node-result <file> --worker-result <file> --verifier-result <file>`. Repeat the verifier-result flag as needed. A non-passing mission uses the same command with its node result and no passing worker/verifier payload. If the parent cannot trust or accept the candidate, use guarded `reject-worker-result --node-id <id> --worker-id <id> --outcome <retryable_failure|blocked> --reason <text>`. `scripts/validate_result.py` is the read-only preflight when no state update is requested.

### Scripted Transition Flag Surfaces

Required flags per `harness_transition.py` subcommand, as the parser defines them:

- `pause`, `resume`, `cancel`: `--source`.
- `accept-wave`: `--wave-id`, repeatable `--mission-id`, `--batch-base-sha`.
- `lease-worker`: `--mission-id`, `--node-id`, `--worker-id`, `--lease-id`, `--attempt-id`, `--branch-ref`, and `--worktree-path`. Optional `--provider`, `--driver`, `--model`, `--reasoning-effort`, `--worker-runtime`, `--workspace-mode`, and `--completion-channel` are compatibility assertions and must match the selector-derived binding. With `--packet-out <new-path>` and `--max-message-bytes <n>`, the call also renders `WORKER_GOAL.template.md` from the in-memory leased run and refuses any unfilled `<...>` placeholder; the packet is size-checked before the durable RUN write and created exclusively after it. Repeatable `--context-path <path>` names the ordered context sources; the packet records each with its SHA-256 hash. `--host-file <file>` holds a JSON object of the host-only placeholder values: worker contract, parent launch identity, route caps, permissions, visual inputs, and repair context.
- `reserve-node-attempt`: `--node-id`, `--attempt-id`; optional repeatable `--evidence`.
- `record-node-result`: `--node-id`, `--attempt-id`, `--outcome`, repeatable `--evidence`; optional repeatable `--blocker` and `--verifier-result`.
- `record-observation`: requires global `--repo-root`; optional `--available-worker-slots <n>`, `--isolation-capacity <n>`, and `--capacity-evidence <text>` must be supplied together from current host observations. Omitted flags preserve existing capacity and do not discover agent slots.
- `reserve-review-dispatch`: `--node-id`, `--worker-id`, `--attempt-id`; optional `--report-path` and `--packet-out` render the reviewer packet in the same call; with `--packet-out`, optional `--diff-artifact-out` retains a complete diff at a new checkout-external path.
- `reconcile-interrupted`: `--worker-id`, `--reason`.
- `record-review-attempt`: `--lineage`, `--attempt-id`, `--worker-id`, `--result`, repeatable `--evidence`; optional `--mission-id`, `--finding`, `--security-result`, and `--tree-sha`. Every non-pass result needs findings. A node with the `security` lens requires `--security-result` and derives findings from that validated object. Global `--repo-root` derives the reviewed tree when `--tree-sha` is absent.
  - `--note <text>` records a non-blocking note with a PASS; a note never produces `fix_required`.
  - `--blocker-class environment|review` with `--result blocked` (default `review`): `environment` marks an inspection failure, needs no `--security-result`, refunds the node attempt (at most two per review lineage per RUN) and keeps the attempt log and worker entry; a blocked result is never a PASS.
  - `--scoped` records a scoped repair review against the head's recorded repair scope; a scoped PASS refunds the attempt, records `scoped` and the scope's `repair_paths` on the attempt and worker, and traverses its pass route edges like an ordinary PASS.
- `reject-worker-result`: `--node-id`, `--worker-id`, `--outcome retryable_failure|blocked`, repeatable `--reason`.
- `record-integration`: `--mission-id`, `--integrated-sha`; optional repeatable `--verifier-result <absolute-external-json>` admits fresh protocol-v2 mission integration output; existing valid retained evidence remains usable without it.
- `reconcile-candidate-head`: `--candidate-sha`, `--source`, `--repair-node-id`, `--repair-attempt-id`, `--repair-task-id`; requires global `--repo-root` and a held `--session-id` lock. Records an already committed, authorized repair after mission integration; it never edits Git or grants repair authority. Repeatable `--repair-path <repo-relative path>` records the repair scope on the new candidate in `integration.repair_scopes` (entries: `candidate_sha`, `prior_head_sha`, `repair_paths`, `source`, optional `trust_boundary`) and requires `git diff <old-head>..<new-head>` to stay inside the declared paths; `--trust-boundary` marks the repair as touching a trust boundary. With `--repair-path` (a scoped repair) the review node's exhausted attempt budget does not block reconciliation; the scoped review that follows refunds its attempt.
- `record-grant`: `--action`, `--expires-when`, `--source`; repeatable `--target` and `--mission-id`. `--action execution` takes no `--target` and authorizes execution with the mission scope.
- `open-run`: `--intent`, `--source`; optional repeatable `--mission-id` and `--expires-when`. Execution flags must travel together and need an execution intent.
- `close-run`: `--source`; requires a held `--session-id` lock. Global `--repo-root` defaults to the RUN file's repository and binds the closeout conditions to live Git.
- `record-runtime`: `--provider`; repeatable `--driver` and `--route-caps` (`<route>=<cap>=<integer>` or a JSON object); optional `--loaded-digest`. It keeps the installed digest `new_run.py` recorded and never reads installed bytes to fill the loaded one.

`scripts/validate_result.py` requires `--plan` and `--run`; its optional flags include `--ancestry-confirmed` and `--repo-root`. `scripts/inspect_harness_run.py` requires `--repo-root` and takes `--session-id`; `scripts/harness_step.py` accepts `--observe-only`. `--help` lists the rest.

## Plan Revisions And Snapshots

Every plan manifest has a stable `plan_id`, a positive integer `revision`, and a semantic SHA-256 digest of the `harness_plan` object, computed over `json.dumps(normalized_plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` (UTF-8) with object lists sorted by `id`, resource lists by `(key, access)`, scalar set-like lists lexically, and `argv` order preserved. Reordering set-like fields leaves the digest unchanged; any semantic change to mission/task definitions, dependencies, scopes, resources, or verifiers creates a new digest and requires an incremented revision.

Verifier declarations are data, not shell prose: at least `id`, repository-relative `cwd`, argument-vector `argv`, and a `pass_signal` label. The runtime decides PASS from exit code 0 alone, so write `pass_signal` as `exit 0`.

A worker-supplied hash is only a claim: the parent retains each `verifier_runtime.py` result, and worker-result validation recomputes the key from it, failing closed on anything missing, forged, stale-context, wrong-head, or mismatched. An earlier PASS is history; current coverage needs the applicable current lease and exact checkpoint or integration SHA, so an old PASS never skips a fresh check on changed code.

Joined Product/UI/Design sources resolve inside `--repo-root` and must match their `content_sha256` (and a supplied full-SHA `source_revision` blob); URLs are never fetched as joined authority.

Derived artifacts must bind all three values:

```text
plan_id
plan_revision
plan_digest_sha256
```

A selected wave also binds a committed `batch_base_sha`. A proposal is stale when its plan revision, plan digest, or base SHA no longer matches observed facts; recompute it rather than editing the old result.

PLAN authoring is owner-gated and separate from a running RUN. Validate a candidate with `scripts/validate_harness_plan.py` before treating a new revision as authoritative; validators are read-only diagnostics, and a pass proves only that the bytes are well formed. It authorizes no rewrite, recomputing retained history, rebinding a grant, or erasing receipts or attempts, and replaces no lock/receipt/exact-SHA evidence. Routine RUN operations use the guarded `harness_transition.py` subcommands. `open-run` records initial readiness, `record-grant` and `record-runtime` record capability and authorization, and `close-run` records the final closeout. Formal revisions keep their documented parent-owned procedure. Do not invent a subcommand, bypass an available transition, or “validate and write back” RUN.

The tools have no guarded formal PLAN-revision mutation. For a substantive revision while a RUN is live: stop new dispatch at a safe boundary, reconcile active workers and reviews, preserve every worktree, dirty state, failed attempt, receipt, and historical RUN record, release the run lock when the session ends, and get a fresh owner instruction for the new revision and its exact actions. Validate the revision as a new candidate and continue only through the documented revision/recovery procedure with exact new authorization, or a newly authorized run pair. Never edit the live RUN to make old grants or evidence look current, reset attempt counts, discard verifier records, or relabel an old result as new-revision evidence. Keep an unchanged copy of the previous pair and review the full state diff before writing.

Render the non-canonical tasks view explicitly with `scripts/render_tasks_view.py --plan <PLAN.md> --run <RUN.md> --out docs/tasks.md --repo-root <target-root>`; add `--check` to diagnose staleness. RUN transitions no longer refresh it, so render and check at handoff and after a formal PLAN revision or closeout outside the transitions. Only RUN and the declared `docs/tasks.md` carrying this run's generation marker/identity are exceptions to the clean-checkout check; a hand-authored, undeclared, retargeted, or other-run view is ordinary dirt, as are product files. Between checkpoints, commit nothing to the run branch except mission merges.

At every required integration or wave-close checkpoint, commit the exact declared coordination files as one ordinary direct child of the recorded integration head, then freshly observe that commit and bind it with `reconcile-coordination-head`. Supported exact paths are `PLAN.md`, `RUN.md`, `DECISIONS.md`, and `REFINEMENT_BACKLOG.md` directly under `docs/goal/` or in one bounded run namespace such as `docs/goal/pdr12/`, the historical or matching generated `tasks.md`, `docs/DOCUMENTS.md`, and one exact `docs/epics/*.md` checkpoint record. A glob, arbitrary application/package source, frozen product/design source, non-regular Git entry, or mode/type change never qualifies; from 0.55.0 RUN validation also rejects an `integration.coordination_paths` entry outside the supported paths. Bind it only with no active integration reviewers or parent-side checks; isolated in-flight mission workers and isolated preintegration reviewers are allowed.

Observed facts are read live before every mutating action. `RUN.md` may record a timestamped snapshot under `observed` for auditability, but the snapshot never replaces a fresh check. The minimum RUN snapshot shape is:

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

Mission phases are finite-state values:

```text
queued -> ready -> leased -> worker_running -> worker_passed -> integrating -> integrated
```

Terminal or interrupting phases are:

```text
blocked | worker_failed | integration_failed | superseded
```

| Transition | Required evidence |
|---|---|
| `queued -> ready` | Dependencies integrated, gates pass, authorization permits the next action, no blocker |
| `ready -> leased` | Parent records one worker lease bound to mission, plan revision/digest, and base SHA |
| `leased -> worker_running` | Worker identity and workspace are observable |
| `worker_running -> worker_passed` | `record-worker-result` observed the bound worktree and revalidated its head, dirty state, `base..head` diff and ancestry, worker/node payload, and retained verifier evidence under the RUN lock |
| `worker_failed -> worker_passed` | Sole stale parent-head rejection only: run `record-observation`, then record the unchanged result through a fresh permitted attempt, preserving the original failed dispatch; ordinary review and integration still apply |
| `worker_passed -> integrating` | Parent rechecks ancestry, diff scope, forbidden files, head stability and integration authorization; under `review_policy: per_mission` also a terminal `review_workers[]` PASS bound to the exact worktree head. RUN-v11 workers never use task-local nested review evidence |
| `integrating -> integrated` | Changes are on the resolved integration branch, the integration verifier passed, and `integrated_sha` is recorded |

Historical `run.integration.retention: "persistent"` preserves its branch during cleanup but is no integration target. A new managed run uses PLAN `branch_policy` under `main-preview/1` to freeze remote main for ordinary work and hotfixes; historical RUNs keep their original pinned base. Later waves re-anchor to the current integration head, never to a moved protected branch.

`worker_passed` means only that the worker-level gate passed in its workspace; it is not completion for dependency purposes. A dependent mission becomes ready only when every dependency is `integrated`, its integration gate is `PASS`, and observed Git ancestry confirms its `integrated_sha` is an ancestor of the current integration head.

`worker_failed` preserves the terminal node evidence recorded by `record-worker-result`; a passing worker payload is required only for `worker_passed`. `integration_failed` preserves the worker-passed state plus the failed integration attempt. Neither unlocks downstream dependencies.

## Canonical Task Phases

Tasks run sequentially inside one mission worker:

```text
queued -> ready -> running -> worker_passed -> mission_recorded
blocked | worker_failed | superseded
```

`worker_passed -> mission_recorded` occurs when the parent confirms the passing task's commit/change is reachable from the reported mission head and represented by its `task_results` entry in the accepted worker result/report. The parent may record both observations in one serialized RUN update but must preserve the evidence distinction. A blocked/failed mission result names `current_task_id` and preserves earlier task results. `mission_recorded` does not make the mission `integrated`. Refined parent tasks use `superseded`; their replacement tasks carry the executable work.

## Recover Before Creating Another RUN

For an existing delivery, inspect the canonical PLAN/RUN, live parent Git state and owning runtime before starting work, and match run ID, PLAN revision/digest, mission, task, attempt, lease and exact SHA; a native task title or prose completion note is not that binding.

Keep an unchanged PLAN in the same RUN through retries and authorized repairs, preserving completed missions, original receipts and cumulative budgets. Unknown process state requires observation, not another launch. Use guarded recovery transitions; never hand-reset succeeded gates, copy old PASS evidence to a new SHA, or open a replacement RUN to escape a checker or exhausted budget. A new initiative, substantive PLAN revision or incompatible legacy binding follows the explicit revision/replanning boundary and preserves the old pair unchanged.

Reserve a fresh attempt for each required check on the current candidate; a failed or blocked observation is not permission to skip reconciliation. Native completion, manifest validity and exact-candidate verification are separate results.

## Resume Reconciliation Gate

A branch/head mismatch or missing integration object needs reconciliation; a blocked Git authority check is an observation failure. Unknown Git or process state is never proof of alignment or liveness.

A `running` RUN can be picked up by a different session. Before that parent selects or launches any ready node, it must reconcile the observed working tree against canonical `task_states`/`mission_states` rather than trust the last recorded checkpoint. Start with `inspect_harness_run.py` as `SKILL.md` directs; it exits 1 when any mission needs reconciliation. Before dispatching work that consumes a project-bound skill slot, also verify that binding's pin with `python "<delivery-harness-skill-root>/scripts/check_skill_bindings.py" --stage <stage>` using `references/installed-commands.md`; choose the actual upcoming stage from the approved scope, never reuse a product-definition result for delivery. A mismatch is a review moment, not a silent swap.

A `running` RUN with no run lock and no observable owning process is stale: stop at the inspector's `Next` block and get one explicit owner decision (pause, cancel or resume) before any selection or launch.

A worker recorded as `leased` or `worker_running`, and dirty output, do not prove a process is alive or dead; the owning runtime must observe liveness. Treat `integrated` or `superseded` drift as historical evidence and keep active-worker drift separate. Confirm interruption there and inspect partial work before `reconcile-interrupted` or `reconcile-interrupted-reviews` under the required RUN lock. Use `record-node-result` or `record-worker-result` only for a matching current reserved attempt or lease; new work gets a new attempt. Never rewrite or rebind old evidence, and preserve retained attempts, grants, and verifier contexts.

Read `observed.git.parent_dirty` and the actual diff live. Map every dirty path to the task(s) whose `write_scope` covers it; dirty content inside a task still at `queued`, `ready`, or `running` is drift, real work that canonical state does not account for.
Drift blocks new work. Resolve it before advancing, by one of:

- Running the covering task's own verifier against the current dirty state. If it passes, commit per `commit-convention.md` and record the task as `worker_passed` (then `mission_recorded` once integration-reachability is confirmed).
- If the drift does not pass verification, is partial, or its origin is unclear, stop and ask the user how to proceed (finish and verify it, stash it, or discard it).

Never treat a dirty checkout as "safe to ignore" or "safe to build on" without this reconciliation.

A resume snapshot is usable only when the parent checkout path, branch, head, and clean/dirty state are all known. Enumerate linked worktrees and reconcile the current parent and currently bound mission/review workspaces to their exact paths, branches, heads and clean state; a missing, dirty or mismatched relevant workspace blocks the frontier, while unrelated linked worktrees and retained historical workers are not current dependencies. Apply the same checks to a `ready` RUN that already contains active work.

Reconcile the current host and loaded Harness release through `runtime_capabilities.runtime_adapter.version_gate` as a separate observation, following `runtime-upgrades.md`. `unobserved`, `upgrade_required`, `restart_required`, and historical `adopted` (`pinned_bundle_or_restart_required`) defer current runtime-worker dispatch; `compatible_old` may finish only the already-active wave and its streaming reviews and defers the next wave. A runtime update never revives a lease.

After a confirmed stopped review fan-out, run `harness_transition.py reconcile-interrupted-reviews` once with every affected review worker ID; it blocks each interrupted attempt, keeps attempt counts, and persists `control.desired_state: paused`, granting no further review attempt and not resuming dispatch. For an interrupted security reviewer, the attempt receipt records `interrupted_review_reconciliation`; only that exact receipt lets the blocked worker omit `security_result`. It is interruption evidence, never a security decision or PASS; once a later current reviewer supplies the exact structured PASS, the receipt-bound historical worker no longer blocks closeout.

## Repairing The Integrated Candidate

For the optional isolated repair mission, follow `graph-orchestration.md#optional-repair-only-mission`. First-pass approval leaves it dormant; a finding activates one repair and one targeted recheck. `verification-gates.md#review-topology` owns the re-check packet and scope.

A passed or failed integration reviewer at a recorded prior head stays admissible after its graph binding is cleared (unique retained attempt, matching outcome and lineage); a blocked one qualifies only through the interrupted-review reconciliation receipt or an environment-blocked attempt entry (`--blocker-class environment`), using the same predicates as closeout; other blocked or active old reviewers refuse candidate movement. The older fix_required prior-head rule keeps its pinned semantics. Admission never revives the old PASS or security coverage for the new candidate.

For a repair within the unchanged PLAN after all missions have integrated, keep the existing RUN. After separately authorized edits, verification and commits, observe the clean parent checkout and run `harness_transition.py --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> reconcile-candidate-head --candidate-sha <full-live-HEAD> --repair-node-id <failed-node> --repair-attempt-id <failed-attempt> --repair-task-id <mission/task> --source <repair-evidence>`. It requires the exact observed non-default integration checkout, forward ancestry, the exact current failed gate/review attempt, one declared repair task and its write scope, existing exact commit/integration grants, no active workers or attempts, and remaining revalidation budgets. A completed RUN cannot be reopened by this command.

The old candidate enters `integration.prior_head_shas`; mission/task completion, historical receipts, attempt counts and authorization grants (including exhausted limits) are preserved. Current gates and integration reviews must establish fresh coverage for the new head: rerun the affected gates instead of replaying completed missions, replacing the RUN, or relabeling old evidence.

This recovery accepts a concrete `fix_required` or `retryable_failure` verifier result, or an integration review's `fix_required` result. A `contract_gap` or an unexplained `blocked` result is not a repair grant. An inactive routed integration review already marked `skipped` cannot carry an old candidate's tree proof forward; resolve it through the formal refinement boundary.

After the targeted re-check, remaining findings enter the Isolated Repair Protocol in `verification-gates.md`: record each scoped review with `record-review-attempt --scoped` and bind each repair's path list with `reconcile-candidate-head --repair-path`; a scoped review does not consume the review node's attempts.

## Mid-Run Modification Recording

Un-checkpointed work of an existing task is drift and stays with that task; review-driven repair likewise stays inside the mission it repairs, as a new attempt on the same work. Everything else that appears during the run (an extra fix, a follow-up edit, or a change the user reports mid-run) is new content, never folded into a mission that happens to be nearby.

Record each such modification as its own mission: open it through a plan revision before the edits continue (`contract-and-traceability.md`), give it its own tasks and verifier, and run it through the normal lease, worker, and integration phases. Then regenerate `docs/tasks.md` with `scripts/render_tasks_view.py`; it groups one section per mission, newest first. A modification is done when it is recorded in RUN and visible in the tasks view, not when the edit lands.

Before the completed coordination set is archived, append every owner or agent update not already in `docs/product/PRD.md` to the preserved `docs/tasks.md` Update Log; product-affecting changes also update the PRD in the same change. Archive candidate A then freezes that log with the RUN. External setup read-back, the outcome review and the growth review happen only after A reaches `main` and production is verified, and their findings never reopen the archived RUN.

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

Non-mission nodes use a two-step attempt invariant: `reserve-node-attempt` changes a dispatchable `approval`, `external_wait`, `lifecycle`, or deterministic batch/final verifier node to `running` and appends a `node_attempt` receipt; `record-node-result` may terminate only that matching running receipt, with evidence. The phase is derived from the declared outcome (`pass` becomes `succeeded`, `blocked` or `contract_gap` becomes `blocked`, `fix_required` or `retryable_failure` becomes `failed`), which remains the route signal. A stopped or interrupted non-runtime attempt is completed as `blocked` through `record-node-result` with evidence and a blocker, never an invented result file. Approval, external-wait, and deterministic-verifier `retryable_failure` may retry directly while budget remains; lifecycle retry requires an explicit bounded route because its side effect may be unknown.

Dependency edges always consume `pass` and remain acyclic. Route edges activate from declared outcomes. A cyclic route requires a PLAN traversal bound and an exit. A retry or subgraph replay creates new attempts and preserves old evidence; it never revives a lease, action grant, base/head binding, or verifier result.

Run `python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan docs/goal/PLAN.md --run docs/goal/RUN.md --repo-root <absolute-root> record-observation` before selection.
Record actual Git facts and capacity from the host; never infer process liveness from RUN phases.

Task, worker, mission-integration, batch and final verifier declarations use explicit `execution.isolation: "host"`; missing, container and snapshot modes are invalid in current tools.
Browser, network, external-service and mutable-environment operations retain their own routes and action authorization.
The derived `execution_route` is `managed_sequential` for fewer than two selected writers, or `parallel_graph` for two or more.
`runtime_driver` is a separate transport fact; follow `graph-orchestration.md` for routing.

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

`invoke_external_runtime` is required when the Harness parent starts a different provider process or service. Its target is `runtime:<provider>`. It does not replace `spawn_subagents`, worktree, branch, commit, integration, or lifecycle authorization. Pre-0.58 pins follow [legacy pins](legacy/legacy-pins.md#pre-058-runtime-dispatch). A configured external bridge requires this key and `spawn_subagents`; PLAN host eligibility still applies.

The ordinary execution loop uses only the applicable local entries. Parent-dispatched sibling workers and reviewers require their exact launch authorization. App-task dispatch is historical and unsupported by the current driver set. "Implement", "build", "fix", or "refactor" never implies a remote action. Harness 0.38+ keeps RUN `push` false; after A exists, a new exact instruction is captured in the checkout-external request instead of the archived RUN. All 12 keys remain for schema compatibility.

For a large `sequential_parent` route, leave `spawn_subagents`, `create_user_owned_tasks`, and `create_app_managed_worktrees` unauthorized and unused. The route's parent-owned worktree/branch/commit/integration actions still require their own matching grants.

Pre-0.38 RUN-v11 push recovery follows [legacy pins](legacy/legacy-pins.md#pre-038-run-branch-push); Harness 0.38+ rejects that path before any side effect. Neither it nor post-archive publication can target `main` or `development`.

Each `authorizations` entry has this minimum shape:

```json
{
  "authorized": false,
  "source": null
}
```

When `authorized` is true, add a required `scope` object with `run_id`, `mission_ids`, and exact `targets`, plus `expires_when`. Schema v10 additionally requires `plan_revision` and `plan_digest_sha256` in that scope, and both must equal `run.plan.revision` and `run.plan.digest_sha256`.

Record the authorized entry with `harness_transition.py record-grant`; it fills the scope from the live run pair and refuses a grant it cannot bind.

That pair is what makes `SKILL.md`'s rule real: when the plan revision or digest changes, the scope stops matching and the grant covers nothing. Below v10 the scope has no plan binding, so nothing compares one — the invalidation rule is inert there and a v7-v9 grant survives a plan change untouched.

Targets use only the prefixes `worker:`, `task:`, `worktree:`, `branch:`, and `runtime:`, and each action accepts only its own kinds. `expires_when` is `wave_closed`, `run_complete`, or `explicit_revocation`, evaluated against current RUN state. Use `"*"` only for a dimension the user explicitly authorized run-wide. A selector/coordinator treats missing, expired, or nonmatching scope as unauthorized; authorization is never a global boolean inferred for every mission or target.

A `"*"` grant covering a launch gets the exact target recorded as a receipt in the same grant: `lease-worker` for mission workers, `reserve-review-dispatch` for a subagent reviewer (`worker:<id>`). Mission launch receipts (`worker:`, `task:`, `worktree:`, `branch:`) need exact `mission_ids` at every version, so the selector defers a launch whose grant lists `"*"` there.

A `"*"` grant may cover `archive_worker_tasks`, `remove_worktrees`, and `delete_branches`, but their PLAN lifecycle node must name an exact `target`. `delete_branches` never covers `main`, `development`, the observed default branch, or their full `refs/remotes/<remote>/<name>` equivalents (from 0.55.0 a grant listing one is invalid); an unqualified `<remote>/<name>` target is an ordinary branch name unless it equals the observed default.

`wave_closed` is one-use authorization for the currently recorded wave. Its scope must add the immutable `wave_id` and `batch_base_sha`, both equal to the current `active_wave` while it is `proposed` or `active`. When that wave becomes `closed` or `superseded`, its `{ "wave_id", "batch_base_sha" }` pair is appended to the v10 RUN's durable `closed_waves` list (older schemas remain readable without it) before `active_wave` is replaced or re-proposed, every matching action entry returns to `{ "authorized": false, "source": null }`, and overall execution authorization is cleared when it used the same boundary. Never copy or revive a wave-scoped grant for a pair already in `closed_waves`: a new wave needs a newly recorded explicit source and a new identity/base pair, and a proposed or active wave may not reuse a listed pair.

`source` identifies the user statement or durable approval record. Narrow authorization remains narrow:

- Static conflict and parallel-eligibility analysis performed by the parent does not require implementation, worktree, branch, commit, or integration authorization. A launch-bound ready frontier and selected wave do require execution plus all launch-path authorizations. Delegating even read-only analysis still requires `spawn_subagents` or `create_user_owned_tasks`, according to the chosen worker primitive.
- Worktree creation does not authorize branch creation, commits, integration, or cleanup; local integration does not authorize branch deletion, worktree removal, or any `push`. Legacy recovery and post-archive publication require their own exact grants.

Before each action, recheck its entry against observed state; a previously authorized action can still be unsafe because the target changed or the plan became stale.

## Landing State

RUN v11 keeps the four-key `landing` shape for compatibility:

```text
mode: local_only
remote
pushed_head_sha
continuity: { status, branch_ref, head_sha, reason }
```

A Harness 0.38+ RUN starts and ends `local_only` at candidate C. `pushed_head_sha` stays null and the graph has no push lifecycle node. The complete archived RUN remains bound to C; later candidate A is never written into it.

Archive, publication and promotion follow `branch-promotion-contract.md#managed-run-archive-before-promotion`; a post-A failure follows `branch-promotion-contract.md#post-a-candidate-or-preview-failure`.

`integration.branch` is the only mutable branch field in RUN. It names the non-protected run branch; `PLAN.branch_policy.base_ref/base_sha` is the frozen immutable source declaration. The optional `observed.git.default_branch` fact is only a push safety observation.

`continuity` records that the run branch survives the run — it is what the user reads and lands:

```text
status: planned | preserved | blocked
```

`planned` and `preserved` require a full local `refs/heads/` ref in `branch_ref`. `preserved` also requires `head_sha`. `blocked` requires a `reason`. Authorized execution requires `planned` or `preserved`.

## Runtime Capability Axes

Record provider, supported driver, worker runtime, workspace and completion channel without inferring capabilities from product labels.
Host policy owns concrete tools, models, effort and fallbacks; `runtime-adapters.md` owns the dispatch procedure.

### Runtime adapter and routing

`runtime_adapter` records the observed lowercase `provider`, ordered `available_drivers`, `detection_source` and version gate.
The current drivers are `subagents` and `sequential_parent`.
A user-owned app-task request is unsupported; block it rather than silently replacing it.
Historical app/task fields remain retained history, interpreted only by their [pinned bundle](legacy/legacy-pins.md#finishing-a-run-on-its-pinned-bundle).
Unknown loaded identity stays unknown.
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
They must cover linked-worktree Git metadata, temp/cache paths, network destinations, local bindings and required sockets, with no unresolved prompt.
A prompt or profile label does not prove permission-level isolation, and permissions never grant an action.

## Capability Gate

Before leasing or fanning out a mission, the parent must prove all applicable rows, and every axis rule above must hold (isolated write workspace, completion channel, permission boundary, flat topology):

| Check | PASS condition |
|---|---|
| Runtime available | Chosen `worker_runtime` exists in this session and its authorization entry passes |
| Workspace available | Chosen `workspace_mode` can be created or observed without overwriting existing work |
| Completion observable | Chosen `completion_channel` can return a terminal result, blocker, or failure to the parent |
| Integration observable | Parent can obtain base SHA, worker head SHA, actual changed paths, and verifier evidence |
| Resource isolation | File scopes and every runtime resource have complete, supported claims |
| Lifecycle understood | Branch/ref durability and retention behavior are recorded |
| Runtime route | Provider and available drivers are observed; the deterministic selected driver matches the declared runtime/workspace/completion axes |

If any capability, isolation, permission, or completion check is unknown, do not fan out. Observe it first; if it remains unavailable, select the real `sequential_parent` route defined above and apply the same verification gates. Missing launch authorization is not an unknown capability: request the exact run-wide launch bundle once and pause rather than rewriting the runtime adapter or silently downgrading.

The configured write-worker maximum follows `stages/managed-delivery.md#default-runtime-and-wave-policy`. Deterministic mission selection is the default immediately after Plan Readiness and execution authorization; run validation and selection before any production task. The effective wave remains the minimum of that configured maximum, live worker slots, isolated workspaces, dependency-ready nonconflicting missions, and every capability and permission gate above.

## Run Lock And Watchdog

Durable execution for one RUN has two machine guards; both are `harness_transition.py` subcommands.

- **Run lock**: before dispatching, the parent records `run.run_lock` (`session_id`, `acquired_at`, `heartbeat_at`) with `--session-id <id> acquire-run-lock` and refreshes it with `--session-id <id> heartbeat-run-lock`; any successful transition by the holding session also refreshes the heartbeat. Every mutating transition refuses a lock held by another session (fresh, stale, or with an unparseable heartbeat); a stale or unparseable foreign lock is taken over only through the explicit `watchdog --reclaim` or `acquire-run-lock` path. The dispatch commands (`accept-wave`, `lease-worker`, `reserve-node-attempt`, `record-node-result`, `record-worker-result`, `reject-worker-result`, `reserve-review-dispatch`, `record-integration`, `reconcile-candidate-head`, `close-wave`) additionally require the calling session to already hold the durable lock. Release it with `release-run-lock` when the session ends.
- **Watchdog**: `watchdog [--stale-after-minutes N]` reports read-only whether the lock is live or stale and lists `running` nodes that lost their parent heartbeat as interrupted-work candidates; `--reclaim` clears a stale lock.

RUN coordination paths protect `docs/goal/DECISIONS.md`, the parent-owned mid-run decision log.
Record each owner decision with its ID, question, decision, source and date. Workers never write that log.
`new_run.py` declares the coordination paths.

## Serialized Same-Repository Host Handoff

Hosts may hand off a large plan-backed run only as a serialized, same-repository operation. It never transfers a live lease, hides a worker, or starts a second writer, and it invents no new schema field or identity. Host A first closes the active wave (`RUN.active_wave.status` is neither `active` nor `proposed`; an absent `active_wave` object is not proof) and preserves the canonical PLAN/RUN, graph state, mission/task evidence, and current exact head SHA.

Host B validates the preserved PLAN/RUN and exact SHA, then re-probes its own runtime version, loaded Harness version, permission, isolation, and completion capabilities, and replaces the old `runtime_adapter`/observed capability snapshot with its fresh one before selecting work or running the next read-only review; it never merges Host A's capability claims. Terminal worker and review records stay historical evidence with Host A's bindings, while any live or new attempt must match Host B's provider and selected driver. Host B uses the same graph and exact-head review gates and proceeds only from a clean, reconciled state.

If Host B's review returns `fix_required`, route the findings back to Host A's original mission/worktree. Any new head invalidates the prior review and requires a fresh verifier and the reviews `verification-gates.md#review-topology` requires before integration or another handoff. This is a serialized file/repository handoff, not an in-session bridge or automatic cross-host invocation. Cross-machine handoff is unsupported until a future schema defines a portable workspace identity and evidence transport; a shared repository path alone is not that bridge.

## Parent-Owned Wave State

Only the parent may accept the selector's pure proposal into `RUN.md` as `active_wave`. The accepted wave records at least:

```text
wave_id
status: idle | proposed | active | closed | superseded
plan_revision
plan_digest_sha256
batch_base_sha
selected_missions
deferred_missions and reason codes
```

The parent records the actual launched session, model and result origin in attempt evidence.
Accept only that session's result; record failed starts as `blocked` with the host error.

While a wave is `active`, `record-worker-result` accepts a result only against that wave and the current bound attempt. The selector blocks new writers and lifecycle mutations but dispatches any dependency-ready read-only node: under `review_policy: per_mission`, a pre-integration review for a selected mission already at `worker_passed`; an approval; or an external wait. Record terminal worker results as they arrive and re-run selection. A mission may integrate before the wave closes once its gate passed (under `per_mission`, its exact-head review PASS); integration stays strictly serial, one `integrating` mission at a time. The wave closes once every selected mission's worker result is recorded, and batch gates follow. A worker or integration failure, dependency change, or plan revision also closes the wave and forces a recompute. A plan revision supersedes every active old-revision lease: quiesce those workers at safe boundaries and issue new leases only after validating their preserved heads against the new plan. Never carry forward an old result, conflict, or readiness assumption.

Close a wave only with `harness_transition.py ... close-wave --source <text>`, never a hand edit. It refuses while any worker or review worker is still live (reconcile them first) and while any selected mission is still queued or running. A `worker_passed` mission may close with the wave and integrate after the close, but only while overall execution authorization survives the boundary: a `run_complete`-bounded grant does, while a `wave_closed`-bounded grant dies at close and therefore requires those missions to integrate, fail, or reconcile first. The command appends the `{ wave_id, batch_base_sha }` tombstone, flips the wave to `closed`, and resets `wave_closed`-bounded grants and overall execution authorization as above; `run_complete`-bounded grants survive as closeout evidence. `accept-wave` requires a live clean product tree on the observed non-protected run integration branch and head; every dispatch command fails closed on stale state.

Observe actual required capabilities before dispatch; host names do not prove them.

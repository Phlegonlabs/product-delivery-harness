# Managed Stage Cards

Use the card for the stage you are in. Cards add no rule; they order what the contracts already require. When a card and a contract disagree, the contract wins. Read the full contract only when a command fails, state is unfamiliar, or the card names it. `<delivery-harness-skill-root>`, `<PLAN.md>`, `<RUN.md>`, `<root>`, and `<id>` are placeholders; resolve every angle-bracket token as `references/installed-commands.md` states.

## Card 1: Entry And Resume

**When**

A session starts on a target that may hold a managed RUN, or a `running` RUN resumes in a new session. Record the System Review And Route before any managed artifact.

Run `inspect_harness_run.py` first and follow its Next block. The inspector exits 1 when a mission needs reconciliation. Map every dirty path to its covering task; drift inside a task that is not `worker_passed` blocks new work. Confirm the runtime version gate as a separate observation. Verify the skill binding for the actual upcoming stage. Reclaim a stale lock only through `watchdog --reclaim`. Treat a stale snapshot or unexplained drift as an owner decision.

**Commands in order**

```text
python "<delivery-harness-skill-root>/scripts/inspect_harness_run.py" --repo-root <root>
python "<delivery-harness-skill-root>/scripts/check_skill_bindings.py" --agents-md <AGENTS.md> --stage <stage>
```

**Stop when**

- The Next block names reconciliation.
- The run lock is held by another live session.
- Drift exists inside a task that is not `worker_passed`.
- The version gate is `unobserved`, `upgrade_required`, or `restart_required`.

**Read on failure**

- `references/execution-state-model.md` — "Resume Reconciliation Gate", "Run Lock And Watchdog"
- `references/runtime-upgrades.md`

## Card 2: Plan Authoring

**When**

The route is `large`, the intent is plan-backed, and no current PLAN/RUN pair exists.

Author PLAN by hand from `assets/templates/HARNESS_PLAN.template.md`. Freeze every needed source with its exact path and `content_sha256` digest. Map one feature batch to one mission; never bundle unrelated features. Plan one combined review node on the unified candidate and list every lens its diff needs. Record `security_review.status` as `required`, or `not_applicable` with a concrete non-code reason. Give each executable task one atomic commit boundary and one verifier. Add `--prd` only when the PLAN freezes a PRD source. Validate the candidate, then generate RUN; generation grants nothing.

**Commands in order**

```text
python "<delivery-harness-skill-root>/scripts/validate_harness_plan.py" --plan <PLAN.md> --repo-root <root> --prd <PRD.md>
python "<delivery-harness-skill-root>/scripts/new_run.py" --plan <PLAN.md> --run-id <id> --branch <branch-ref> --out <RUN.md> --repo-root <root>
```

**Stop when**

- The validator exits non-zero.
- A frozen digest does not match current bytes.
- One mission bundles unrelated features.
- `new_run.py` refuses because `<RUN.md>` exists.

**Read on failure**

- `references/stages/managed-delivery.md` — "Plan Large Work", "Default Mission Topology"
- `references/contract-and-traceability.md`

## Card 3: Readiness

**When**

PLAN is validated, RUN exists, and the first dispatch approaches. Recheck before each new wave.

Pass the Mission Cohesion Gate for every mission. Require one verifier per mission, one atomic commit boundary per executable task, and one bounded worker slice per task. Require an executable provider for every runtime-worker node. Record exact authorization in the RUN ledger; every action entry needs `authorized: true` with an explicit user source, exact scope, and `expires_when`. Record live Git facts and capacity with `record-observation`; supply capacity flags only from observed host evidence. Validate the pair with the RUN bound. After every readiness row passes, set `plan_readiness: ready` through the parent-owned readiness procedure.

**Commands in order**

```text
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> record-observation
python "<delivery-harness-skill-root>/scripts/validate_harness_plan.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root>
```

**Stop when**

- A mission lacks a verifier or an executable provider.
- An authorization entry lacks its exact source and scope.
- The Mission Cohesion Gate fails for a mission.
- `plan_readiness` stays `blocked`.

**Read on failure**

- `references/stages/managed-delivery.md` — "Pass Plan Readiness"
- `references/execution-state-model.md` — "Authorization Action Ledger"
- `references/execution-task-decomposition.md` — Mission Cohesion Gate

## Card 4: Dispatch

**When**

`plan_readiness` is `ready`, the version gate passes, and execution plus launch authorization covers the wave.

Acquire the durable run lock first. Refresh it with `heartbeat-run-lock`; every successful transition also refreshes it. Record the observation, then select the frontier with the read-only step command. Accept the proposal into RUN; recompute it when the revision, digest, or base went stale. Create each worktree and branch only under its own grants. `lease-worker` materializes exact targets only from active wildcard grants. Render the bounded `WORKER_GOAL.template.md` packet per mission. Check the complete packet before dispatch. Lease each worker, then launch every ready sibling before waiting on any result.

**Commands in order**

```text
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> acquire-run-lock
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> record-observation
python "<delivery-harness-skill-root>/scripts/harness_step.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> accept-wave --wave-id <id> --mission-id <id> --batch-base-sha <sha>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> lease-worker --mission-id <id> --node-id <id> --worker-id <id> --lease-id <id> --attempt-id <id> --branch-ref <branch-ref> --worktree-path <worktree-path>
python "<delivery-harness-skill-root>/scripts/check_launch_packet.py" --message-file <file> --max-message-bytes <n>
```

**Stop when**

- The lock is held by another session.
- `accept-wave` refuses a stale proposal.
- A capability or permission gate row is unknown.
- A worktree, branch, or launch grant is missing.

**Read on failure**

- `references/execution-state-model.md` — "Run Lock And Watchdog", "Parent-Owned Wave State", "Capability Gate"
- `references/runtime-performance.md` — "Bounded Context Capsule"

## Card 5: Record Results

**When**

A worker returned a result, a non-mission attempt finished, or every selected worker result is recorded.

Preflight the payload read-only before any state change. Record the mission result with one locked call; repeat `--verifier-result` per retained execution. A non-passing mission records its node result and no passing payload. Reject a stale or untrusted candidate. Reserve each non-mission attempt before its side effect, then close it with exactly one outcome. Run `verifier_runtime.py` outside the RUN lock and keep request and result files outside the checkout. Record each integration after its gate passes; integration stays serial. Close the wave when no worker or review worker is live.

**Commands in order**

```text
python "<delivery-harness-skill-root>/scripts/validate_result.py" --plan <PLAN.md> --run <RUN.md> --node-result <file> --worker-result <file> --verifier-result <file>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> record-worker-result --node-result <file> --worker-result <file> --verifier-result <file>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> reject-worker-result --node-id <id> --worker-id <id> --outcome retryable_failure --reason <text>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> reserve-node-attempt --node-id <id> --attempt-id <id> --request-out <file>
python "<delivery-harness-skill-root>/scripts/verifier_runtime.py" --request <file>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> record-node-result --node-id <id> --attempt-id <id> --outcome pass --evidence <text> --verifier-result <file>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> record-integration --mission-id <id> --integrated-sha <sha>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> close-wave --source <text>
```

**Stop when**

- Validation reports a mismatch against live Git.
- Changed files leave the mission write scope.
- A result has no matching reserved attempt or lease.
- A selected mission is still queued or running at close.

**Read on failure**

- `references/execution-state-model.md` — "Generating And Validating State", "Parent-Owned Wave State"
- `references/verification-gates.md` — "Worker Result Gate", "Gate Levels"

## Card 6: Review And Repair

**When**

Missions are integrated and the review node is dependency-ready, or a review returned findings.

Reserve the review and render its packet in one call. Launch the reviewer only from that persisted receipt. One combined review covers the unified head. Record PASS notes with `--note`, blocking findings with `--finding`, and an unperformed attempt as `blocked --blocker-class environment`. Group findings into one family and send one consolidated repair. Reconcile the repaired head, then reserve one targeted re-check on the new SHA. After the re-check, remaining defects enter the Isolated Repair Protocol; record scoped reviews with `--scoped`.

**Commands in order**

```text
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> reserve-review-dispatch --node-id <id> --worker-id <id> --attempt-id <id> --packet-out <file>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> record-review-attempt --lineage <id> --attempt-id <id> --worker-id <id> --result pass --evidence <text> --note <text>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> record-review-attempt --lineage <id> --attempt-id <id> --worker-id <id> --result fix_required --evidence <text> --finding <text>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> record-review-attempt --lineage <id> --attempt-id <id> --worker-id <id> --result blocked --blocker-class environment --evidence <text>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> reconcile-candidate-head --candidate-sha <sha> --source <text> --repair-node-id <id> --repair-attempt-id <id> --repair-task-id <id> --repair-path <path>
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> record-review-attempt --lineage <id> --attempt-id <id> --worker-id <id> --result pass --scoped --evidence <text>
```

**Stop when**

- The packet is truncated and the diff artifact stays unread.
- The same-scope review would rerun on an unchanged SHA.
- The repair diff would leave the declared repair paths.
- A third full review round is proposed.

**Read on failure**

- `references/verification-gates.md` — "Review Topology", "Isolated Repair Protocol"
- `references/execution-state-model.md` — "Scripted Transition Flag Surfaces"

## Card 7: Closeout

**When**

Every mission is integrated, the review converged, and final gates have run on the exact head.

Bind every gate PASS to the current integration head; a changed head invalidates every earlier PASS. Run the plan validator against the live root, so recorded heads match live Git. Add `--design-system <design-system.json>` and `--design-system-markdown <design-system.md>` when the Design System Need Gate is `required`. Check every closeout bar item and every `status: complete` condition. Render and check the tasks view. Release the lock when the session ends. The run lands `local_only`; archive and publication are separate grants.

**Commands in order**

```text
python "<delivery-harness-skill-root>/scripts/validate_harness_plan.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root>
python "<delivery-harness-skill-root>/scripts/render_tasks_view.py" --plan <PLAN.md> --run <RUN.md> --out docs/tasks.md --repo-root <root> --check
python "<delivery-harness-skill-root>/scripts/harness_transition.py" --plan <PLAN.md> --run <RUN.md> --repo-root <root> --session-id <id> release-run-lock
```

**Stop when**

- A gate PASS is missing or stale on the current head.
- The security review is missing, skipped, or stale.
- The validator reports head drift.
- An archive or publication action is proposed without its own grant.

**Read on failure**

- `references/verification-gates.md` — "Closeout Bar"
- `references/execution-state-model.md` — exact RUN lifecycle values and `status: complete` conditions
- `references/branch-promotion-contract.md` — "Managed RUN Archive Before Promotion"

# Optional Goal Prompt

Normally keep the Goal objective and checkpoint in the PLAN-v6/RUN-v11 managed artifacts after routing. Use this standalone snippet only for a direct small-work prompt or when a workflow explicitly needs a copy-ready prompt before managed artifacts exist; it is never a compact RUN-only replacement. This prompt records expected execution shape and requests authorization; it never grants authorization to itself.

Before using any task-specific skill or managed workflow, the parent must complete the parent-only, read-only `System Review And Route` stage. That first stage reads the request, repository instructions, Git state, scope, and upstream inputs, then records `small`/`large` and `direct`/`plan-backed graph`. It does not load a task skill, select an adapter/model, create PLAN/RUN, preflight workers, invoke an external runtime, or spawn a worker. Only a large route may create PLAN schema v6 plus RUN schema v11.

```text
/goal Prepare the complete delivery path for <measurable outcome> using <canonical source paths> as the source of truth.

Expected coordination:
- runtime provider: observed lowercase host identity | generic
- available drivers: <observed list including sequential_parent>
- selected driver: app_threads | subagents | sequential_parent
- worker_runtime: parent | subagent | app_task
- workspace_mode: shared_checkout | parent_managed_worktree | app_managed_worktree
- completion_channel: agent_result | thread_poll | report_file | user_relay
- planning depth: direct | PLAN + RUN
- execution route (derived after selection): direct | managed_sequential | parallel_graph
- maximum parallel workers: <observed runtime cap and configured PLAN cap; effective cap is the lower value>
- automatic mission fan-out: user-owned app tasks | native sibling agents | disabled
- nested mission helpers: disabled; parent dispatches any explorer or reviewer as a sibling

Requested actions, pending explicit user authorization:
- <one or more exact ledger keys, or none>

For automatic app-task fan-out, request the local execution bundle `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, and `integrate_locally` with exact scope. Workers never delegate. Harness 0.38 RUN push stays false; any later archive-candidate publication needs a new action-time request after A exists.

For native sibling-agent fan-out with isolated mission writes, request the local bundle `spawn_subagents`, `create_local_worktrees`, `create_local_branches`, `create_local_commits`, and `integrate_locally` with exact scope. The parent allocates one worktree per mission and runs one flat workflow. This requests local approval only; it grants no post-archive publication.

For a large route with no usable agent capability, select `sequential_parent` and follow the Sequential Parent Route in `skills/delivery-harness/references/execution-state-model.md`: the PLAN mission keeps `executor: runtime_worker`, RUN records the parent-owned binding solely for lease/state validation, and the parent executes one mission at a time under the same PLAN/RUN graph and exact-head review gates.

For ordinary mission work, resolve the non-protected run branch from observed `main`. Harness 0.38 RUNs close `local_only` at C. Archive with exact main evidence and an immutable external anchor, commit the moved set plus `ARCHIVE_RECEIPT.json` as A, and reverify it against that anchor. A new exact instruction plus external request/attempt/receipt may publish A. Candidate gates and separate exact-A `main` promotion follow. Never recreate `development` or force-push.

Before any implementation, map every must-have requirement to a trace, dependency-ordered mission, immutable flat task ID, supported write/deny scope, complete typed resource inventory, worker verifier, integration verifier, and final gate. Write static definitions to PLAN.md and live state to the canonical JSON in RUN.md. Validate plan structure and pass the Plan Readiness Gate.

In the target repository, start every mission worktree from the current resolved integration SHA. Each worktree completes one exact-head read-only review before parent integration; repairs require a fresh review. Merge passing worktrees only into that integration branch. Cut the explicitly resolved non-default run branch from the current default branch and use it for integration; never edit or commit on the default branch, and never push to it.

Do not treat this Goal text, plan readiness, expected mode, or requested action list as authorization. Keep all 12 schema-v11 RUN authorization entries false unless the user explicitly approves the exact action and its source, run/mission/target scope, plan revision, plan digest, and expiry boundary are recorded; older RUN schemas retain their original ledger. `invoke_external_runtime` is separate from worker creation and requires `runtime:<provider>`. Overall execution authorization also records its explicit source. The parent may perform read-only validation and static graph/conflict analysis without implementation authorization, but a launch-bound selected wave requires execution and launch-action authorization; delegating even the analysis still requires the matching worker-creation authorization. If implementation and its required actions are authorized, select only ready non-conflicting nodes against a fixed base SHA; otherwise stop at ready and report what authorization is missing. New managed work always uses the PLAN-v6/RUN-v11 pair. Existing legacy compact RUN-only artifacts may be read and validated for compatibility, but they are not authored or extended by this prompt; migrate to a fresh pair before managed execution.

When an authorized selector result contains launch directives, consume it under the general runtime adapter contract. Map observed native tools to the selected driver, preserve explicit topology, resolve deferred tools before declaring them unavailable, and record real identities. Launch all selected fresh siblings before waiting for terminal results. Every explorer, writer and reviewer remains parent-dispatched; workers do not delegate. Do not replace explicitly requested user-owned tasks with direct agents or parent execution. Missing required capability blocks the affected work; native completion never bypasses result validation.

Workers never edit PLAN.md or RUN.md. A worker that needs task decomposition returns REFINEMENT_REQUEST and stops. A worker pass is only an integration candidate; the parent must validate its actual changes, integrate it, run integration gates, and verify ancestry before downstream work becomes ready. Recompute the next wave after each integration batch.

Stop on requirements conflict, unsupported scope/resource claims, stale plan digest or base, unavailable required verifier, any authorization boundary, or three consecutive no-progress iterations. Complete only when every must-have trace is covered, every required gate is PASS, every integrated SHA is verified, and every UNVALIDATED surface is explicitly accepted.
```

## Minimal Pre-Launch Check

- [ ] One objective and stopping condition are explicit.
- [ ] Canonical sources are linked, not duplicated.
- [ ] UI-bearing work freezes the human-owned `ui-design.md`, approved wireframe, Style Integration, Impeccable HiFi review, H1-H9 result, Visual Approval, and required validation depth; owner approval is not representative-user usability proof.
- [ ] PLAN contains the complete static trace, mission/task DAG, scopes, resources, and verifiers.
- [ ] RUN contains the matching plan revision/digest and current observed facts.
- [ ] Provider, observed drivers, selected route, runtime, workspace, and completion channel are recorded consistently.
- [ ] Plan Readiness passes before implementation begins.
- [ ] Every needed action is explicitly authorized in RUN; all other ledger entries remain false.
- [ ] The Harness 0.38 RUN is verified `local_only` with push false. Archive-only A has exact relocation proof; any run-branch publication has an external request/attempt/receipt and exact read-back. `main` promotion has separate authorization and full A evidence.
- [ ] UI evidence and final E2E gates are defined when applicable, including the automated E2E command, current-head check/evidence, target environment, and manual-smoke disposition.
- [ ] The fixed integration base and post-batch recomputation rule are recorded.
- [ ] Destructive actions and external writes remain separate approval boundaries.

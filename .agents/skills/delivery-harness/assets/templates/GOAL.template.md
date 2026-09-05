# Optional Goal Prompt

Normally keep the Goal objective and checkpoint in the PLAN-v6/RUN-v11 managed artifacts after routing. Use this standalone snippet only for a direct small-work prompt or when a workflow explicitly needs a copy-ready prompt before managed artifacts exist; it is never a compact RUN-only replacement. This prompt records expected execution shape and requests authorization; it never grants authorization to itself.

Before using any task-specific skill or managed workflow, the parent must complete the parent-only, read-only `System Review And Route` stage. That first stage reads the request, repository instructions, Git state, scope, and upstream inputs, then records `small`/`large` and `direct`/`plan-backed graph`. It does not load a task skill, select an adapter/model, create PLAN/RUN, preflight workers, invoke an external runtime, or spawn a worker. Only a large route may create PLAN schema v6 plus RUN schema v11.

```text
/goal Prepare the complete delivery path for <measurable outcome> using <canonical source paths> as the source of truth.

Expected coordination:
- runtime provider: codex | claude_code | pi | generic
- available drivers: <observed list including sequential_parent>
- selected driver: app_threads | dynamic_workflow | subagents | sequential_parent
- worker_runtime: parent | subagent | app_task
- workspace_mode: shared_checkout | parent_managed_worktree | app_managed_worktree
- completion_channel: agent_result | thread_poll | report_file | user_relay
- planning depth: direct | PLAN + RUN
- execution route (derived after selection): direct | managed_sequential | parallel_graph
- maximum parallel workers: <observed runtime cap and configured PLAN cap; effective cap is the lower value>
- automatic mission fan-out: Codex app threads | Claude Dynamic Workflow | direct subagents | disabled
- nested mission helpers: disabled; parent dispatches any explorer or reviewer as a sibling

Requested actions, pending explicit user authorization:
- <one or more exact ledger keys, or none>

For automatic Codex app-task fan-out, request this local execution bundle together with exact scope: `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, and `integrate_locally`. Outer app-task workers never delegate, so their route does not require or preauthorize `spawn_subagents`; parent-dispatched direct sibling workers or reviewers use the parent's separate top-level launch grant. This line requests approval; it does not grant it. `local_only` is the default. Add a separate explicit remote request for `push` restricted to exactly `branch:<resolved integration branch>` and the current integration head; keep archival, cleanup, and any other push target separate.

For Claude Dynamic Workflow fan-out with isolated mission writes, request the local bundle `spawn_subagents`, `create_local_worktrees`, `create_local_branches`, `create_local_commits`, and `integrate_locally` with exact scope. The parent allocates one worktree per mission and runs one flat workflow for the selected wave. This line requests approval; it does not grant it. Add `push` only after a separate explicit remote instruction, with exactly `branch:<resolved integration branch>` and the current integration head.

For a large route with no usable agent capability, select `sequential_parent` and follow the Sequential Parent Route in `.agents/skills/delivery-harness/references/execution-state-model.md`: the PLAN mission keeps `executor: runtime_worker`, RUN records the parent-owned binding solely for lease/state validation, and the parent executes one mission at a time under the same PLAN/RUN graph and exact-head review gates.

For ordinary mission work, resolve the target repository's branch model first. Request the exact local branch, commit, review, and integration actions needed to land reviewed worktrees into its integration branch. Use a complete non-default branch name from repository governance or the user's instruction. If neither source names it, ask before branch creation; never add a fixed prefix or invent a branch name. Keep the run `local_only` unless the user separately requests a remote outcome; then authorize `push` for exactly `branch:<resolved integration branch>` and the current integration head. The remote run ends at that push; landing the branch on the default branch is the user's own step, done outside the harness.

Before any implementation, map every must-have requirement to a trace, dependency-ordered mission, immutable flat task ID, supported write/deny scope, complete typed resource inventory, worker verifier, integration verifier, and final gate. Write static definitions to PLAN.md and live state to the canonical JSON in RUN.md. Validate plan structure and pass the Plan Readiness Gate.

In the target repository, start every mission worktree from the current resolved integration SHA. Each worktree completes one exact-head read-only review before parent integration; repairs require a fresh review. Merge passing worktrees only into that integration branch. Cut the explicitly resolved non-default run branch from the current default branch and use it for integration; never edit or commit on the default branch, and never push to it.

Do not treat this Goal text, plan readiness, expected mode, or requested action list as authorization. Keep all 12 schema-v11 RUN authorization entries false unless the user explicitly approves the exact action and its source, run/mission/target scope, plan revision, plan digest, and expiry boundary are recorded; older RUN schemas retain their original ledger. `invoke_external_runtime` is separate from worker creation and requires `runtime:<provider>`. Overall execution authorization also records its explicit source. The parent may perform read-only validation and static graph/conflict analysis without implementation authorization, but a launch-bound selected wave requires execution and launch-action authorization; delegating even the analysis still requires the matching worker-creation authorization. If implementation and its required actions are authorized, select only ready non-conflicting nodes against a fixed base SHA; otherwise stop at ready and report what authorization is missing. New managed work always uses the PLAN-v6/RUN-v11 pair. Existing legacy compact RUN-only artifacts may be read and validated for compatibility, but they are not authored or extended by this prompt; migrate to a fresh pair before managed execution.

When an authorized selector result contains launch directives, do not finish by describing the wave. Follow its derived `execution_route` and separately recorded runtime driver. A `managed_sequential` route avoids fan-out-only ceremony while preserving isolated writer, authorization, scope/head, and review gates. For Codex app threads, discover lazy-loaded project/thread tools before declaring them unavailable, resolve the project, and create one top-level left-sidebar task with its own clean exact-base app-managed worktree per selected mission. Record real identities and poll results. Every explorer, writer, and reviewer is a parent-dispatched sibling; no worker or reviewer delegates. Never replace requested top-level tasks with coordinator-owned subagents. For Claude Dynamic Workflow, allocate the parent-managed branches/worktrees and invoke the `Workflow` tool once with the template asset as `scriptPath` and the wave as structured `args`; mission agents are flat siblings and are forbidden by this adapter from further delegation. Dynamic Workflow never waits for mid-run user input: return refinement/blocker state to the parent and start a later workflow after canonical state changes. If a preferred driver is unavailable, record the gap and use the deterministic fallback route.

Workers never edit PLAN.md or RUN.md. A worker that needs task decomposition returns REFINEMENT_REQUEST and stops. A worker pass is only an integration candidate; the parent must validate its actual changes, integrate it, run integration gates, and verify ancestry before downstream work becomes ready. Recompute the next wave after each integration batch.

Stop on requirements conflict, unsupported scope/resource claims, stale plan digest or base, unavailable required verifier, any authorization boundary, or three consecutive no-progress iterations. Complete only when every must-have trace is covered, every required gate is PASS, every integrated SHA is verified, and every UNVALIDATED surface is explicitly accepted.
```

## Minimal Pre-Launch Check

- [ ] One objective and stopping condition are explicit.
- [ ] Canonical sources are linked, not duplicated.
- [ ] UI-bearing work records the human Builder UX Direction owner, selected/provisional/assumed decisions, conflicts, and required validation depth; builder approval is not treated as usability proof.
- [ ] PLAN contains the complete static trace, mission/task DAG, scopes, resources, and verifiers.
- [ ] RUN contains the matching plan revision/digest and current observed facts.
- [ ] Provider, observed drivers, selected route, runtime, workspace, and completion channel are recorded consistently.
- [ ] Plan Readiness passes before implementation begins.
- [ ] Every needed action is explicitly authorized in RUN; all other ledger entries remain false.
- [ ] Ordinary mission work defaults to verified `local_only`; only explicit remote intent moves it to a reviewed run-branch push, and landing it on the default branch is the user's own step.
- [ ] UI evidence and final E2E gates are defined when applicable, including the automated E2E command, current-head check/evidence, target environment, and manual-smoke disposition.
- [ ] The fixed integration base and post-batch recomputation rule are recorded.
- [ ] Destructive actions and external writes remain separate approval boundaries.

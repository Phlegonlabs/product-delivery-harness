# Optional Goal Prompt

Normally keep the Goal objective and checkpoint in `docs/goal/RUN.md`. Use this standalone snippet only when a workflow explicitly needs a copy-ready prompt without creating RUN.md. This prompt records expected execution shape and requests authorization; it never grants authorization to itself.

```text
/goal Prepare the complete delivery path for <measurable outcome> using <canonical source paths> as the source of truth.

Expected coordination:
- runtime provider: codex | claude_code | generic
- available drivers: <observed list including sequential_parent>
- selected driver: app_threads | dynamic_workflow | subagents | sequential_parent
- worker_runtime: parent | subagent | app_task
- workspace_mode: shared_checkout | parent_managed_worktree | app_managed_worktree
- completion_channel: agent_result | thread_poll | report_file | user_relay
- maximum parallel workers: <1-3>
- automatic mission fan-out: Codex app threads | Claude Dynamic Workflow | direct subagents | disabled
- nested mission helpers: enabled read-only, 1-3 per non-trivial app task | disabled
- automatic PR landing: enabled after explicit landing-bundle authorization | disabled

Requested actions, pending explicit user authorization:
- <one or more exact ledger keys, or none>

For automatic Codex app-task fan-out, request this local execution bundle together with exact scope: `spawn_subagents`, `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, and `integrate_locally`. This line requests approval; it does not grant it. Keep every push, PR, review, merge, deploy, archival, and cleanup action as a separate ledger entry; when pull-request landing is intended, include the missing launch and landing entries in the same one-time Plan Readiness authorization checkpoint.

For Claude Dynamic Workflow fan-out with isolated mission writes, request `spawn_subagents`, `create_local_worktrees`, `create_local_branches`, `create_local_commits`, and `integrate_locally` with exact scope. The parent allocates one worktree per mission and runs one flat workflow for the selected wave. This line requests approval; it does not grant it.

For a new end-to-end automatic pull-request landing, proactively request `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `create_pr`, `manage_pr_review`, and `merge_pr` together with exact scope at Plan Readiness; omit an action only when its mutation has already happened or is not needed. Record one explicit user statement under each covered entry, then continue through Draft PR, current-head CI, Codex review, zero unresolved threads, exact-head squash auto-merge, and merged-state confirmation without asking again between those stages. This line requests approval; it does not grant it. Keep `configure_repository` as a separate ledger entry, but include it in the same checkpoint when inspection proves an exact review or auto-merge configuration change is required. Keep deploy, archival, and cleanup separate.

Before any implementation, map every must-have requirement to a trace, dependency-ordered mission, immutable flat task ID, supported write/deny scope, complete typed resource inventory, worker verifier, integration verifier, and final gate. Write static definitions to PLAN.md and live state to the canonical JSON in RUN.md. Validate plan structure and pass the Plan Readiness Gate.

Do not treat this Goal text, plan readiness, expected mode, or requested action list as authorization. Keep all 16 RUN authorization entries false unless the user explicitly approves the exact action and its source, run/mission/target scope, and expiry boundary are recorded. Overall execution authorization also records its explicit source. The parent may perform read-only validation and static conflict/parallel-eligibility analysis without implementation authorization, but a launch-bound selected wave requires execution and launch-action authorization; delegating even the analysis still requires the matching worker-creation authorization. If implementation and its required actions are authorized, select only ready non-conflicting missions against a fixed base SHA; otherwise stop at ready and report what authorization is missing.

When an authorized selector result contains launch directives, do not finish by describing the wave. Follow its recorded runtime route. For Codex app threads, resolve the project, create one worktree thread per selected mission, record real identities, and poll results; each non-trivial mission thread uses its authorized read-only direct-subagent policy. For Claude Dynamic Workflow, allocate the parent-managed branches/worktrees and invoke the `Workflow` tool once with the template asset as `scriptPath` and the wave as structured `args`; mission agents are flat siblings and are forbidden by this adapter from further delegation. Dynamic Workflow never waits for mid-run user input: return refinement/blocker state to the parent and start a later workflow after canonical state changes. If a preferred driver is unavailable, record the gap and use the deterministic fallback route.

When the automatic landing bundle is authorized, do not stop after verification or PR creation. Poll CI and review, fix authorized in-scope findings, invalidate stale evidence after every push, request review again for the new head, and enable exact-head squash auto-merge only after every current-head gate passes. Finish only after GitHub reports the PR merged and its merge SHA is recorded.

Workers never edit PLAN.md or RUN.md. A worker that needs task decomposition returns REFINEMENT_REQUEST and stops. A worker pass is only an integration candidate; the parent must validate its actual changes, integrate it, run integration gates, and verify ancestry before downstream work becomes ready. Recompute the next wave after each integration batch.

Stop on requirements conflict, unsupported scope/resource claims, stale plan digest or base, unavailable required verifier, any authorization boundary, or three consecutive no-progress iterations. Complete only when every must-have trace is covered, every required gate is PASS, every integrated SHA is verified, and every UNVALIDATED surface is explicitly accepted.
```

## Minimal Pre-Launch Check

- [ ] One objective and stopping condition are explicit.
- [ ] Canonical sources are linked, not duplicated.
- [ ] PLAN contains the complete static trace, mission/task DAG, scopes, resources, and verifiers.
- [ ] RUN contains the matching plan revision/digest and current observed facts.
- [ ] Provider, observed drivers, selected route, runtime, workspace, and completion channel are recorded consistently.
- [ ] Plan Readiness passes before implementation begins.
- [ ] Every needed action is explicitly authorized in RUN; all other ledger entries remain false.
- [ ] Automatic landing was inspected and requested once at Plan Readiness; it is either fully authorized for exact targets or stops once with the complete missing-action list.
- [ ] UI evidence and final E2E/release gates are defined when applicable, including the automated E2E command, current-head check/evidence, target environment, and manual-smoke disposition.
- [ ] The fixed integration base and post-batch recomputation rule are recorded.
- [ ] Destructive actions and external writes remain separate approval boundaries.

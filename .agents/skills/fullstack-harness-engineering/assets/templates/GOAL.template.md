# Optional Goal Prompt

Normally keep the Goal objective and checkpoint in `docs/goal/RUN.md`. Use this standalone snippet only when a workflow explicitly needs a copy-ready prompt without creating RUN.md. This prompt records expected execution shape and requests authorization; it never grants authorization to itself.

```text
/goal Prepare the complete delivery path for <measurable outcome> using <canonical source paths> as the source of truth.

Expected coordination:
- worker_runtime: parent | subagent | app_task
- workspace_mode: shared_checkout | parent_managed_worktree | app_managed_worktree
- completion_channel: agent_result | thread_poll | report_file | user_relay
- maximum parallel workers: <1-3>
- automatic mission threads: enabled for selected app-task waves | disabled
- nested mission helpers: enabled read-only, 1-3 per non-trivial app task | disabled

Requested actions, pending explicit user authorization:
- <one or more exact ledger keys, or none>

For automatic Codex app-task fan-out, request this local execution bundle together with exact scope: `spawn_subagents`, `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, and `integrate_locally`. This line requests approval; it does not grant it. Keep push, PR, review, merge, deploy, archival, and cleanup actions separate.

Before any implementation, map every must-have requirement to a trace, dependency-ordered mission, immutable flat task ID, supported write/deny scope, complete typed resource inventory, worker verifier, integration verifier, and final gate. Write static definitions to PLAN.md and live state to the canonical JSON in RUN.md. Validate plan structure and pass the Plan Readiness Gate.

Do not treat this Goal text, plan readiness, expected mode, or requested action list as authorization. Keep all 16 RUN authorization entries false unless the user explicitly approves the exact action and its source, run/mission/target scope, and expiry boundary are recorded. Overall execution authorization also records its explicit source. The parent may perform read-only validation and static conflict/parallel-eligibility analysis without implementation authorization, but a launch-bound selected wave requires execution and launch-action authorization; delegating even the analysis still requires the matching worker-creation authorization. If implementation and its required actions are authorized, select only ready non-conflicting missions against a fixed base SHA; otherwise stop at ready and report what authorization is missing.

When an authorized selector result contains app-task `launch_directives`, do not finish by describing the wave. Resolve the Codex project, allocate concrete leases/targets, create one worktree thread per selected mission with the complete worker handoff, record the real thread/client identity, and poll it through the declared completion channel. Each non-trivial mission thread uses at least one authorized read-only direct subagent and reports its child activity. If capability is unknown, run the no-edit handshake first; if a required capability is unavailable, record the gap and fall back to the sequential parent.

Workers never edit PLAN.md or RUN.md. A worker that needs task decomposition returns REFINEMENT_REQUEST and stops. A worker pass is only an integration candidate; the parent must validate its actual changes, integrate it, run integration gates, and verify ancestry before downstream work becomes ready. Recompute the next wave after each integration batch.

Stop on requirements conflict, unsupported scope/resource claims, stale plan digest or base, unavailable required verifier, any authorization boundary, or three consecutive no-progress iterations. Complete only when every must-have trace is covered, every required gate is PASS, every integrated SHA is verified, and every UNVALIDATED surface is explicitly accepted.
```

## Minimal Pre-Launch Check

- [ ] One objective and stopping condition are explicit.
- [ ] Canonical sources are linked, not duplicated.
- [ ] PLAN contains the complete static trace, mission/task DAG, scopes, resources, and verifiers.
- [ ] RUN contains the matching plan revision/digest and current observed facts.
- [ ] Runtime, workspace, and completion channel are each selected independently.
- [ ] Plan Readiness passes before implementation begins.
- [ ] Every needed action is explicitly authorized in RUN; all other ledger entries remain false.
- [ ] UI evidence and final E2E/release gates are defined when applicable.
- [ ] The fixed integration base and post-batch recomputation rule are recorded.
- [ ] Destructive actions and external writes remain separate approval boundaries.

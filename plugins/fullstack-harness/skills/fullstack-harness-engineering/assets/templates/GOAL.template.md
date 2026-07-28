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
- maximum parallel workers: <observed runtime cap and configured PLAN cap; effective cap is the lower value>
- automatic mission fan-out: Codex app threads | Claude Dynamic Workflow | direct subagents | disabled
- nested mission helpers: enabled read-only, 1-3 per non-trivial app task | disabled
- automatic PR landing: enabled after explicit landing-bundle authorization | disabled
- automatic Cloudflare promotion: reviewed development head -> production branch only after final user approval and exact deploy authorization | disabled

Requested actions, pending explicit user authorization:
- <one or more exact ledger keys, or none>

For automatic Codex app-task fan-out, request this local execution bundle together with exact scope: `spawn_subagents`, `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, and `integrate_locally`. This line requests approval; it does not grant it. Keep every push, PR, review, merge, deploy, archival, and cleanup action as a separate ledger entry. Never include the later production promotion in this ordinary mission-launch checkpoint.

For Claude Dynamic Workflow fan-out with isolated mission writes, request `spawn_subagents`, `create_local_worktrees`, `create_local_branches`, `create_local_commits`, and `integrate_locally` with exact scope. The parent allocates one worktree per mission and runs one flat workflow for the selected wave. This line requests approval; it does not grant it.

For ordinary mission work, resolve the target repository's branch and landing model first. Request only the exact local branch, commit, review, and integration actions needed to land reviewed worktrees into its integration branch; do not request or infer a future protected-branch promotion. After the user separately reviews the accumulated integration result and explicitly approves promotion, request the remaining `push`, `create_pr`, `manage_pr_review`, and `merge_pr` actions with exact scope. Use `future-pr:<owner>/<repo>:base=<base>:head=<head>` until the PR exists, then verify that binding and append `pr:<full-PR-URL>` before review or merge. Once that late checkpoint authorizes every remaining action, finish current-head CI and Codex review and use exact-head squash auto-merge without asking again between those already approved stages. Keep `configure_repository` separate.

For full deployed Cloudflare delivery, request `deploy` separately for each exact `release:<target-id>`. A manual remote workflow also needs `trigger_remote_ci` for `workflow:<identity>`; provisioning needs `provision_cloud_resources` for each `cloud-resource:<provider>:<environment>:<kind>:<logical-name>`. Development binds to the verified `development` head and must pass deployed-environment E2E. Production binds publication evidence to the resulting `production` head after the authorized promotion. Native merge-triggered publication requires independent exact `merge_pr` and `deploy` grants. One answer may authorize all exact targets at the final promotion checkpoint, but no action implies another.

Before any implementation, map every must-have requirement to a trace, dependency-ordered mission, immutable flat task ID, supported write/deny scope, complete typed resource inventory, worker verifier, integration verifier, and final gate. Write static definitions to PLAN.md and live state to the canonical JSON in RUN.md. Validate plan structure and pass the Plan Readiness Gate.

In the target repository, start every mission worktree from the current resolved integration SHA. Each worktree completes one exact-head read-only review before parent integration; repairs require a fresh review. Merge passing worktrees only into that integration branch. Preserve the repository's protected landing flow. If it defines no other model, use `development` for integration and `production` for the separately approved promotion target.

Do not treat this Goal text, plan readiness, expected mode, or requested action list as authorization. Keep all 19 schema-v10 RUN authorization entries false unless the user explicitly approves the exact action and its source, run/mission/target scope, plan revision, plan digest, and expiry boundary are recorded; older RUN schemas retain their original ledger. `invoke_external_runtime` is separate from worker creation and requires `runtime:<provider>`. Overall execution authorization also records its explicit source. The parent may perform read-only validation and static graph/conflict analysis without implementation authorization, but a launch-bound selected wave requires execution and launch-action authorization; delegating even the analysis still requires the matching worker-creation authorization. If implementation and its required actions are authorized, select only ready non-conflicting nodes against a fixed base SHA; otherwise stop at ready and report what authorization is missing.

When an authorized selector result contains launch directives, do not finish by describing the wave. Follow its recorded runtime route. For Codex app threads, discover lazy-loaded project/thread tools before declaring them unavailable, resolve the project, and create one top-level left-sidebar task with its own app-managed worktree per selected mission. Record real identities and poll results; each non-trivial mission thread then runs its own authorized read-only direct-subagent policy. Never replace requested top-level tasks with coordinator-owned subagents. For Claude Dynamic Workflow, allocate the parent-managed branches/worktrees and invoke the `Workflow` tool once with the template asset as `scriptPath` and the wave as structured `args`; mission agents are flat siblings and are forbidden by this adapter from further delegation. Dynamic Workflow never waits for mid-run user input: return refinement/blocker state to the parent and start a later workflow after canonical state changes. If a preferred driver is unavailable, record the gap and use the deterministic fallback route.

After final user approval starts an authorized protected-branch promotion, do not stop after PR creation. Start or observe CI and Codex review concurrently for the exact candidate head, fix authorized in-scope findings, invalidate stale evidence after every push, and restart both remote gates. Stop at a merge-ready PR and hand it to the human, naming the exact merge-ready head. Merge toward a protected base remains human-owned unless a later explicit instruction names that exact existing PR. Production deployment is a separate lifecycle action: the harness performs it only when exact `deploy` authorization and provider topology permit, and never infers it from merge. Ordinary integration work may instead use an authorized `integration_pull_request` into the retained integration branch.

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
- [ ] Ordinary mission work ends on reviewed `development`; any production promotion waits for the separate final user-approval checkpoint.
- [ ] Cloudflare release targets, isolated bindings/secrets/auth/payment modes, migrations, exact-SHA deploy commands, deployed-environment checks, and separate deploy authorization are defined when deployment is in scope.
- [ ] UI evidence and final E2E/release gates are defined when applicable, including the automated E2E command, current-head check/evidence, target environment, and manual-smoke disposition.
- [ ] The fixed integration base and post-batch recomputation rule are recorded.
- [ ] Destructive actions and external writes remain separate approval boundaries.

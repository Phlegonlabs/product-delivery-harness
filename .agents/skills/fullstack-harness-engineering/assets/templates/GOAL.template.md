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
- automatic Cloudflare promotion: reviewed run branch -> protected base only after the user asks for the pull request, merges it, and gives exact deploy authorization | disabled

Requested actions, pending explicit user authorization:
- <one or more exact ledger keys, or none>

For automatic Codex app-task fan-out, request this ordinary execution-intent bundle together with exact scope: `spawn_subagents`, `create_user_owned_tasks`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, and `push` restricted to `branch:<resolved integration branch>` (`branch:refs/heads/codex/<short-name>` under the main-only default). This line requests approval; it does not grant it. Keep every PR, review, merge, deploy, archival, cleanup, and push outside the resolved integration branch as a separate ledger entry. Never include the later production promotion in this ordinary mission-launch checkpoint.

For Claude Dynamic Workflow fan-out with isolated mission writes, request `spawn_subagents`, `create_local_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, and `push` restricted to `branch:<resolved integration branch>` (`branch:refs/heads/codex/<short-name>` under the main-only default) with exact scope. The parent allocates one worktree per mission and runs one flat workflow for the selected wave. This line requests approval; it does not grant it.

For ordinary mission work, resolve the target repository's branch and landing model first. Request the exact local branch, commit, review, and integration actions needed to land reviewed worktrees into its integration branch, plus `push` restricted to `branch:<resolved integration branch>` so the run can reach `integration_push`, and do not request or infer a future protected-branch promotion. Under the main-only default, that exact push target is the run's own `branch:refs/heads/codex/<short-name>`. The grouped instruction covers that push only after `landing.integration_branch_protection` binds the exact branch to `unprotected` status and a `repository:` policy source; otherwise record a separate exact target source. After the user separately reviews the accumulated integration result and explicitly approves promotion, request `create_pr` and `manage_pr_review`, plus any other independently required actions, with exact scope. Bind `create_pr` and `manage_pr_review` to `future-pr:<owner>/<repo>:base=<base>:head=<head>` until the PR exists, then verify that binding and append `pr:<full-PR-URL>`. Once that late checkpoint authorizes those actions, finish current-head CI and Codex review, then stop at a merge-ready handoff. Do not bind `merge_pr` until a later explicit instruction names the exact existing PR. Keep `configure_repository` separate.

For full deployed Cloudflare delivery, request `deploy` separately for each exact `release:<target-id>`. A manual remote workflow also needs `trigger_remote_ci` for `workflow:<identity>`; provisioning needs `provision_cloud_resources` for each `cloud-resource:<provider>:<environment>:<kind>:<logical-name>`. Only when an actual preview or staging release target is declared, bind its deployment evidence to the exact reviewed integration head and require deployed-environment E2E. Production publication evidence and deploy execution bind to the resulting `main` head after the user-started landing PR merges, or to the resulting head of the resolved protected base when repository instructions define another protected base. Native merge-triggered publication always requires independent exact production `deploy` authorization. If the harness performs or auto-merges, exact `merge_pr` authorization is additionally required; when a human merges externally, leave `merge_pr` false and retain actor/event evidence bound to the exact PR URL, reviewed head, and merged SHA. One answer may authorize all exact targets at the final promotion checkpoint, but no action implies another.

Before any implementation, map every must-have requirement to a trace, dependency-ordered mission, immutable flat task ID, supported write/deny scope, complete typed resource inventory, worker verifier, integration verifier, and final gate. Write static definitions to PLAN.md and live state to the canonical JSON in RUN.md. Validate plan structure and pass the Plan Readiness Gate.

In the target repository, start every mission worktree from the current resolved integration SHA. Each worktree completes one exact-head read-only review before parent integration; repairs require a fresh review. Merge passing worktrees only into that integration branch. Preserve the repository's protected landing flow. If it defines no other model, cut the run's own `codex/<short-name>` branch from the current `main` and use it for integration; `main` is the protected base and is never written to directly.

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
- [ ] Ordinary mission work ends on the reviewed run branch once it is pushed; the pull request into the protected base waits for its own user instruction.
- [ ] Cloudflare release targets, isolated bindings/secrets/auth/payment modes, migrations, exact-SHA deploy commands, deployed-environment checks, and separate deploy authorization are defined when deployment is in scope.
- [ ] UI evidence and final E2E/release gates are defined when applicable, including the automated E2E command, current-head check/evidence, target environment, and manual-smoke disposition.
- [ ] The fixed integration base and post-batch recomputation rule are recorded.
- [ ] Destructive actions and external writes remain separate approval boundaries.

# Worktree And Thread Orchestration

Use this reference when the harness runs more than one mission, uses subagents, or needs worktree isolation.

## Default: Single-Checkout Subagent Orchestration

Prefer this mode unless a worktree exception below applies. One checkout, one branch, parent-owned state:

- Write missions run one at a time, each delegated to a subagent with the mission's `RUN.md` section as its prompt and the mission write scope as a stated constraint.
- Read-only work (baseline audits, reviews, verification lenses) may fan out to parallel subagents freely.
- Never run parallel write subagents in one checkout: even disjoint write scopes collide on lockfiles, build caches, generated files, dev servers, and local databases.
- A sequential single-checkout subagent reports to the parent directly; create `docs/goal/evidence/M<n>/REPORT.md` only when a durable report is needed for handoff or integration.
- Worktree preflight, merge order, integration merges, and worktree cleanup do not apply. Landing is one branch and one PR under the same push/PR gate.
- If the runtime has no subagent primitive, the parent runs the same missions sequentially itself with identical gates.

## Parent And Worker Roles

Parent thread owns:

- Source intake and contract freeze.
- `PLAN.md` and the single parent-owned `RUN.md`.
- Worktree creation plan.
- Worker prompts.
- Merge order and conflict handling.
- Integration and E2E verification.
- Final closeout.

Worker thread owns:

- One mission only.
- Its own worktree or isolated workspace.
- The mission write scope.
- Task-level verification and commits.
- Evidence report back to parent.

Workers must not edit parent-owned `PLAN.md` or `RUN.md` during parallel execution. They report evidence; the parent serializes updates into `RUN.md`.

## When To Use Worktrees

Worktrees are opt-in, not the default. Opting in means accepting real coordination cost: preflight, merge order, integration reruns, and cleanup. Completion signaling depends on the runtime: Codex manual mission threads do not notify the parent -- the user relays completion; Claude Code worktree-isolated background subagents report back to the parent automatically (see `orchestration-research-notes.md`). Use worktrees only for:

- High-risk refactors where the parent needs a stable foreground checkout.
- Heavy missions that genuinely need parallel writes to win wall-clock time.
- Long-running background work that must not block the parent checkout.
- Missions requiring conflicting dev ports, local databases, or fixtures at the same time.

Skip worktrees for:

- Anything the default single-checkout subagent mode can handle.
- Small direct work and single-file fixes.
- Read-only planning, audits, and reviews.
- Sequential work where one checkout is simpler and safer.

## Preflight

Run from the parent checkout:

```powershell
git status --short --branch
git worktree list --porcelain
git branch --format='%(refname:short) %(worktreepath)'
```

Do not proceed silently if:

- The parent has unrelated dirty changes that affect the mission.
- The target worktree path already exists and may contain data.
- The branch name already exists and is checked out elsewhere.
- The base branch is not the intended integration base.

Ask before deleting, moving, cleaning, resetting, or overwriting any worktree or local file.

Record preflight in the harness artifacts before launch:

```text
Base branch:
Parent git status:
Existing worktrees:
Branch/worktree conflicts:
Dirty-file attribution:
Dependency DAG/toposort:
.worktreeinclude needed:
Resource isolation plan:
```

## Worktree Naming

Use stable mission names:

```text
Worktree path: ../<repo>-e<epic>-m<mission>
Branch: codex/e<epic>-m<mission>
```

Manual Git worktree command:

```powershell
git worktree add -b codex/e1-m1 ../project-e1-m1 main
```

For Codex app managed worktrees, record the Codex-created worktree/thread instead of manually creating a path. Managed worktrees may start detached; create a branch only when the work needs commits or sharing.

## Environment Isolation

Record these per mission:

```text
Dev port:
Database/schema:
Seed/reset command:
Migration allocation:
Env file policy:
External service sandbox:
Auth provider app/tenant:
Payment sandbox account:
Webhook endpoint:
Queue/topic:
Object storage bucket:
Email/SMS sandbox:
Feature flag namespace:
Test users/orgs:
```

Worktrees isolate files, not ports, databases, secrets, queues, caches, or running services. Full-stack missions need explicit resource isolation.

If ignored local files are required in Codex-managed app worktrees, use `.worktreeinclude` in the repository root for files such as `.env.local`. Do not list tracked files.

## Mission Coordination Table

```text
| Mission | Depends on | Write scope | Worktree | Branch | Port / DB | Verifier | Evidence | Merge order | Status |
|---|---|---|---|---|---|---|---|---|---|
| M1 foundation | none | db/**, auth/** | ../project-e1-m1 | codex/e1-m1 | 3001 / app_m1 | <cmd> | <path> | 1 | planned |
```

## Worker Goal And Report Files

For parallel Codex threads, keep each worker prompt in the parent task when possible. Create a copy-ready worker goal file from `assets/templates/WORKER_GOAL.template.md` only when another task or worktree needs a durable handoff:

```text
docs/goal/evidence/M<n>/GOAL.md
```

Workers write their final report to their temporary mission evidence directory, never to parent-owned `PLAN.md` or `RUN.md`:

```text
docs/goal/evidence/M<n>/REPORT.md
```

The parent reads each `REPORT.md`, verifies the claims against the actual worktree state, and folds the durable result into `RUN.md`. After integration, retain the report only when it is needed for acceptance or future debugging.

## Worker Prompt Shape

```text
You are the worker for Mission <n> only.
Worktree: <path>
Branch: <branch>
Read first: <contract files>, <mission section>
Write only: <paths>, <evidence dir>
Do not edit: parent-owned PLAN.md or RUN.md, frozen contracts, unrelated files.
Do not sync: never pull, rebase, merge, or push against the base branch; the parent owns sync and landing.
Task loop: choose one task, implement it, run the verifier, record evidence, and commit only if verification passes using the harness atomic commit convention.
Report back: write <evidence dir>/REPORT.md with changed files, commands, exit codes, evidence paths, commit hash, blockers, residual risk.
Stop and ask if the write scope is insufficient, requirements conflict, verification cannot run, or destructive action is needed.
```

## Upstream Sync During Parallel Runs

The parent owns all synchronization against the base branch. Workers never pull, rebase, or merge upstream into their mission branch.

If the base branch advances mid-run:

- Default: let workers finish their missions, then integrate onto the updated base and rerun each mission verifier there.
- If a mid-run sync is unavoidable (for example, a fix the mission depends on landed upstream), the parent pauses the worker at a task boundary, performs the rebase or merge in that worktree, reruns the mission verifier, then resumes the worker.
- Record every sync event and its verifier result in the `RUN.md` attempt log.
- If a sync produces conflicts that touch frozen contract surfaces, stop and ask before resolving.

## Integration

Parent integration loop:

```text
1. Wait for worker report.
2. Inspect changed files and commit hash.
3. Merge in declared order.
4. Rerun that mission's verifier on the integration branch.
5. Record integration evidence.
6. Continue only when integration passes or the blocker is logged.
7. Run final E2E verification after all required missions merge.
```

Do not merge a mission whose own verifier failed unless the user explicitly accepts the risk.

## Landing And Push-Back

Landing covers everything after local integration passes: push, PR, merge to main, and cleanup.

### Integration Branch Strategy

Decide before launch and record it in `PLAN.md`:

```text
Single mission: feature branch cut from main, land via one PR.
Multi-mission: merge mission branches into codex/e<epic>-integration, land via one PR to main.
Direct-to-main integration: only when the user explicitly chooses it.
```

### Push / PR Gate

Do not push or open a PR until all of these hold:

- Integration verifiers and the final E2E gate are PASS.
- The evidence register is complete and every `UNVALIDATED` surface is accepted by the user.
- Final `git status` / diff review shows expected changes only.
- The user has approved the landing action. Push and PR creation are outward-facing; do not perform them silently.

PR description should include: summary mapped to trace IDs, verification evidence summary, `UNVALIDATED` surfaces, and migration/deploy notes when relevant.

### Merge Conflicts

1. The parent resolves conflicts in the integration branch or a dedicated integration worktree, never inside a worker's worktree mid-mission.
2. Resolve using the frozen contract as the arbiter. If the conflict reveals a contract gap or two missions legitimately claim the same surface, stop and ask.
3. After resolving, rerun the affected missions' verifiers before continuing the merge order.

### Post-Landing Cleanup

Only after the PR is merged and the user confirms cleanup:

```powershell
git worktree list --porcelain
git worktree remove <path>
git branch -d codex/e<n>-m<n>
```

Ask before every removal. Never force-delete branches that are not fully merged. Record the cleanup (or the decision to defer it) in `RUN.md`.

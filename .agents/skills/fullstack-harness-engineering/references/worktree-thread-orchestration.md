# Worktree And Thread Orchestration

Use this reference when the harness runs more than one mission, uses subagents, or needs worktree isolation.

## Parent And Worker Roles

Parent thread owns:

- Source intake and contract freeze.
- Harness docs and mission state.
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

Workers must not edit shared harness docs during parallel execution. They report evidence; the parent serializes updates.

## When To Use Worktrees

Use worktrees for:

- Parallel mission execution.
- Full-stack work with UI/API/data changes.
- Long-running background work.
- High-risk refactors where the parent needs a stable foreground checkout.
- Different missions requiring different dev ports, local databases, or fixtures.

Skip worktrees for:

- Small direct work.
- Single-file fixes.
- Read-only planning.
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

## Worker Prompt Shape

```text
You are the worker for Mission <n> only.
Worktree: <path>
Branch: <branch>
Read first: <contract files>, <mission section>
Write only: <paths>
Do not edit: shared harness docs, frozen contracts, unrelated files.
Task loop: choose one task, implement it, run the verifier, record evidence, commit only if verification passes.
Report back: changed files, commands, exit codes, evidence paths, commit hash, blockers, residual risk.
Stop and ask if the write scope is insufficient, requirements conflict, verification cannot run, or destructive action is needed.
```

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

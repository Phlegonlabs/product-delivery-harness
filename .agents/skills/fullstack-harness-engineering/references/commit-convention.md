# Atomic Commit Convention

Use this convention for every harness-managed task commit. Commit permission is an independent authorization action; implementation permission alone does not grant it.

## Atomic Boundary

- Commit one coherent, independently verified task outcome at a time.
- Include the implementation, focused tests, and any migration or documentation required for that same outcome.
- Exclude any unrelated formatting, cleanup, refactors, generated files, and user-owned work.
- Split an oversized task through the parent-owned refinement protocol before committing when it contains independently useful outcomes. Never rewrite only `RUN.md` to invent accepted scope.
- Stage explicit files, inspect the staged diff, and commit only after the task verifier passes and commits are authorized.
- Do not commit failed work except an explicitly planned harness or test artifact whose purpose is to expose the failure.
- Do not start a second task's implementation before the current task's verifier has run and, on pass, its commit is made. Checkpoint each task as you finish it, not in a batch at the end of a mission or session — an interruption before that checkpoint leaves unverified, unrecorded drift that a later resume has to reconstruct from the diff alone (see `execution-state-model.md`'s Resume Reconciliation Gate).
- When a task reads a new required environment variable, add its placeholder entry to `.env.example` in that same commit (see `platform-archetypes.md`'s Greenfield / Empty Repository section) — never land the code that reads it without the matching documented placeholder, and never commit the real `.env`/local secret file itself.

## Commit Message

Use:

```text
<type>(<scope>): <imperative summary>

Task: <mission-id>/<task-token>
Trace: <TRACE-ID>[, <TRACE-ID>]
Verified: <command or action> (<pass signal>)
```

Example:

```text
feat(auth): implement password login

Task: M2/T03
Trace: PRD-012, ARCH-004
Verified: pnpm test --filter auth (exit 0)
```

Rules:

- Write the complete message in English.
- Keep the subject at 72 characters or fewer, use lowercase `type` and `scope`, use an imperative summary, and omit the final period.
- Use one of: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `build`, or `ci`.
- Use a stable product or engineering area for `scope`, such as `auth`, `billing`, `api`, `db`, `dashboard`, `ui`, `harness`, or `prd`; do not use a filename.
- Include exactly one planned task ID in `Task`. Split the task first if a commit would need multiple task IDs.
- Treat the task ID as an opaque immutable reference. A readable alias may change without changing the ID.
- Include every upstream trace covered by the commit in `Trace`. Use `HARNESS` only for an approved internal harness, maintenance, or cleanup task with no upstream trace.
- Record the actual verifier and literal result in `Verified`. Separate multiple verifiers with semicolons.
- Use `type(scope)!:` plus a `BREAKING CHANGE:` paragraph when a deliberately approved breaking change is unavoidable.

## RUN.md Recording

After the commit succeeds and its task verifier passes, the worker reports the task as `worker_passed`. The parent then confirms the commit is reachable from the reported mission head and represented in the worker result/report before recording the task as `mission_recorded` in RUN. The task itself is never marked `integrated`; only its mission may become `integrated` after worker-result validation, integration onto the current head, and the mission integration gate.

```text
`a1b2c3d` — `feat(auth): implement password login` — PASS
```

One mission branch may contain multiple ordered task commits. List closeout commits as:

```text
Commits:
- a1b2c3d feat(auth): implement password login — M2/T03
```

Record the final hash after commit creation. Do not amend a task commit merely to place its own hash in `RUN.md`; land parent-owned `RUN.md` bookkeeping at the next authorized checkpoint or closeout, and do not require a checkpoint commit to self-reference.

Commit `PLAN.md`/`RUN.md` themselves to git at every mission integration or wave close — do not let "the next authorized checkpoint" drift into several missions' or a full day's worth of code landing in git while the plan/run bookkeeping that explains those changes remains only a local uncommitted file. A crash, fresh clone, or reset before that commit permanently severs the integrated code from the record of why it was integrated, what it was reviewed against, and what revision authorized it.

## Integration Commits

When the parent creates a merge or integration-only commit, do not pretend it is a task commit. Use a mission-level body:

```text
chore(integration): integrate mission M2

Mission: M2
Plan-Revision: 3
Integrated-Head: <sha>
Verified: <integration verifier> (<pass signal>)
```

An integration commit may reference several task commits from the same mission. Record the exact integrated SHA in `RUN.md`; downstream missions are not unblocked by a worker commit that has not passed this integration boundary.

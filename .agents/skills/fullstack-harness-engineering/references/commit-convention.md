# Atomic Commit Convention

Use this convention for every harness-managed task commit.

## Atomic Boundary

- Commit one coherent, independently verified task outcome at a time.
- Include the implementation, focused tests, and any migration or documentation required for that same outcome.
- Exclude any unrelated formatting, cleanup, refactors, generated files, and user-owned work.
- Split an oversized task in `RUN.md` before committing when it contains independently useful outcomes.
- Stage explicit files, inspect the staged diff, and commit only after the task verifier passes and commits are authorized.
- Do not commit failed work except an explicitly planned harness or test artifact whose purpose is to expose the failure.

## Commit Message

Use:

```text
<type>(<scope>): <imperative summary>

Task: M<n>/T<n>
Trace: <TRACE-ID>[, <TRACE-ID>]
Verified: <command or action> (<pass signal>)
```

Example:

```text
feat(auth): implement password login

Task: M2/T3
Trace: PRD-012, ARCH-004
Verified: pnpm test --filter auth (exit 0)
```

Rules:

- Write the complete message in English.
- Keep the subject at 72 characters or fewer, use lowercase `type` and `scope`, use an imperative summary, and omit the final period.
- Use one of: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `build`, or `ci`.
- Use a stable product or engineering area for `scope`, such as `auth`, `billing`, `api`, `db`, `dashboard`, `ui`, `harness`, or `prd`; do not use a filename.
- Include exactly one planned task ID in `Task`. Split the task first if a commit would need multiple task IDs.
- Include every upstream trace covered by the commit in `Trace`. Use `HARNESS` only for an approved internal harness, maintenance, or cleanup task with no upstream trace.
- Record the actual verifier and literal result in `Verified`. Separate multiple verifiers with semicolons.
- Use `type(scope)!:` plus a `BREAKING CHANGE:` paragraph when a deliberately approved breaking change is unavoidable.

## RUN.md Recording

After the commit succeeds, set the task row to `passed` and write `Evidence / commit` as:

```text
`a1b2c3d` — `feat(auth): implement password login` — PASS
```

List closeout commits as:

```text
Commits:
- a1b2c3d feat(auth): implement password login — M2/T3
```

Record the final hash after commit creation. Do not amend a task commit merely to place its own hash in `RUN.md`; land parent-owned `RUN.md` bookkeeping at the next authorized checkpoint or closeout, and do not require a checkpoint commit to self-reference.

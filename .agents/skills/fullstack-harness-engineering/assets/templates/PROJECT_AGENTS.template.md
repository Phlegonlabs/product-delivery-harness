# Project Rules

This template uses `main` as the default branch but does not prescribe a run-branch prefix. If the repository already defines another branch model, keep that existing governance and replace the default name below; never overwrite conflicting repository instructions.

## Runtime Boundary

- This file contains shared repository governance. Codex and Pi load it as their native project context; the generated `CLAUDE.md` imports it for Claude Code.
- Keep runtime-specific worker roles, model selection, subagent behavior, and launch flags in the matching Full-Stack Harness adapter. Never copy Codex, Claude Code, or Pi mechanics into another runtime's worker.

## Core Development Principles

### Keep It Simple (KISS / YAGNI)

- Only do what's asked. No unrequested features, fallbacks, or "future-proof" abstractions.
- Prefer the simplest thing that works. Don't over-engineer.
- Don't "improve" code you weren't asked to touch.

### File Size Limit

- A module must not exceed 500 lines. When an implementation would cross that limit, split it before committing — check and split at the moment the task's own file would cross the limit (via the task-refinement protocol in the Full-Stack Harness's `execution-task-decomposition.md`), not as a later end-of-project audit.
- Exceptions require stating the reason in the same commit: generated code/migrations, configuration files, schema/type-definition files, and a package's own re-export/entrypoint module.

### No Backwards-Compatibility Code

- Don't add hacks, shims, or dual-path logic for compatibility unless explicitly asked.
- If something needs changing, change it directly. Don't preserve old interfaces.
- Delete dead code. Don't comment it out to "keep it around."

### Surgical Changes

- Make the smallest change possible. One goal per change.
- Only remove imports and variables your own edit orphaned.
- Avoid wide refactors unless you can prove they're safe.
- Keep diffs reviewable and easy to roll back.

### Think Before Coding

- Propose a plan and approach for review before writing code.
- Define clear acceptance criteria and a test plan.

### Verify First

- Every change must be verifiable (tests, scripts, output). If you can't verify it, don't ship it.
- For bug fixes, write or update a regression test before changing implementation.

### Do-Not-Touch Areas

- (List protected files here, e.g. database migrations, public API response shapes)

## Protect Local Data

- Preserve unrelated dirty files, branches, and worktrees.
- Confirm before deleting, overwriting, or moving important local data.

## Branch Model

- Map one independently testable goal to one mission. Tasks inside that mission stay sequential under one writer.
- Give every writer an explicit file-ownership scope and a separate worktree. Workers and reviewers never delegate; the Harness parent dispatches every explorer, writer, and reviewer as a sibling.
- Freeze and integrate shared APIs, schemas, and types before starting dependent write missions in parallel.
- Resolve the complete non-default run-branch name from repository governance or the user's instruction. If neither source names it, ask before branch creation; never add a fixed prefix or invent a branch name.
- Cut that resolved run branch from the current default branch, then create every implementation worktree from the current resolved integration-branch SHA.
- Before dispatch, verify each worktree has the expected repository, branch/ref, exact base HEAD, and a clean status.
- Never edit, commit, or merge on the default branch, and never push to it. Cutting a branch from it is fine; writing to it is not.
- Run focused checks and at least one exact-head read-only review in or against each completed worktree. A repair requires a fresh review.
- With matching `integrate_locally` authorization, merge only reviewed worktree heads into the resolved integration branch.
- After serial integration, use fresh read-only reviewers on the exact unified integration SHA, then run one broad final validation on the fixed candidate SHA.
- The run defaults to verified local completion; only an explicit remote outcome pushes the verified integration head to the run branch. Landing the run branch on the default branch is the user's own step, done outside this harness.
- Later work cuts a fresh run branch from the then-current default branch.

## Action Authorization

- Before any action represented in the RUN authorization ledger, verify its exact authorization. The ledger covers external runtime invocation, subagents, user-owned tasks, worktrees, local branches, local commits, local integration, push, task archival, worktree removal, and branch deletion. When a RUN ledger exists, the matching action must be true for the exact target; direct work without RUN still requires an explicit user instruction for the covered mutation.
- Ordinary plan-backed work starts and normally ends `local_only` on the resolved integration branch; a separate explicit remote outcome may move it to `integration_push` when that verified head is pushed. The run is complete there; it does not wait for GitHub.
- With matching `create_local_branches` authorization, work on the exact resolved non-default run branch.
- With matching `create_local_commits` authorization, commit only the verified task scope.
- Worker branches stay local. With matching `integrate_locally` authorization, integrate exact-head review-passing work into the resolved integration branch.
- Run `<verification-command>` and `<e2e-command>`, then review the complete diff before push.
- Treat a PASS from the required automated E2E on the current head as the proof for its covered primary journeys. Record duplicate manual smoke as `not required - covered by current-head E2E`; require manual smoke only for a materially different environment or an uncovered visual/external-integration risk.
- With matching explicit remote intent and `push` authorization, push only the verified resolved integration branch and current head. A current v10 push also requires one exact branch target and known `observed.git.default_branch`; a target, integration branch, or observed default branch resolving to `main` is refused.
- Remove only an authorized clean linked worktree, then delete only the authorized local worker branch. Never remove the primary checkout, and never delete the run branch the user still has to read.
- Task archival, worktree removal, and branch deletion remain separate ledger actions even when several are approved in one explicit readiness statement.

## Review Guidelines

Treat authorization bypasses, writes to the default branch, stale review SHAs, data loss, scope escapes, and missing behavior verification as blocking findings. Do not report style preferences as blockers.

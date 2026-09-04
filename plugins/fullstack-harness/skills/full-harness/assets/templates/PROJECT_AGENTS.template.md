# Project Rules

This file is ready-to-use shared repository guidance. Resolve the repository's real default branch, commands, and protected paths from live project state; do not leave template placeholders or assume they are always the same across repositories.

## Runtime Boundary

- This file contains shared repository governance. Codex and Pi load it as their native project context; the generated `CLAUDE.md` imports it for Claude Code.
- Keep runtime-specific worker roles, model selection, subagent behavior, and launch flags in the Full-Stack Harness runtime adapter reference (`full-harness/references/runtime-adapters.md`, the section for the detected host). Never copy Codex, Claude Code, or Pi mechanics into another runtime's worker.
- Rules under **Managed Full-Stack Harness Runs** apply only after the Harness routes work into PLAN/RUN. Small direct work follows the shared principles, Git safety, and verification rules without creating Harness state, missions, workers, or worktrees unless the repository or user requires them.

## Skill Bindings

The delivery flow binds stage slots, not fixed skill names. This table binds the project's installed skills to those slots; updating it to adopt a new skill is a project edit, not a harness change, and a bound skill inherits the same modes, frozen sources, and review gates as the default.

| Slot | Stage | Bound skill | Pinned SHA-256 |
| --- | --- | --- | --- |
| design_direction | wireframes → UI direction and mockup (UI Design Pass) | <bundled Taste-aware pass (`design-taste-frontend`), or an installed taste skill> | <hash of the bound skill's SKILL.md> |
| design_compilation | frozen design-system pair | <bundled `product-design-builder` + `frontend-design`, or your own> | n/a for defaults |
| frontend_implementation | implementation missions | <bundled `frontend-design`, or your own frontend skill> | <hash of the bound skill's SKILL.md> |

An unbound slot uses the bundled default. A non-default bound skill pins the SHA-256 of its SKILL.md; `full-harness/scripts/check_skill_bindings.py` recomputes it and fails on a mismatch, so changing a bound skill's content is a deliberate, reviewed pin update — never a silent swap. PLAN missions resolve their workers' skill lists from this table where a slot applies.

## Core Development Principles

### Keep It Simple (KISS / YAGNI)

- Only do what's asked. No unrequested features, fallbacks, or "future-proof" abstractions.
- Prefer the simplest thing that works. Don't over-engineer.
- Don't "improve" code you weren't asked to touch.

### File Size Limit

- A module must not exceed 500 lines. When an implementation would cross that limit, split it before committing — check and split at the moment the task's own file would cross the limit (via the task-refinement protocol in the Full-Stack Harness's `execution-task-decomposition.md`), not as a later end-of-project audit.
- Exceptions require stating the reason in the same commit: generated code/migrations, configuration files, schema/type-definition files, and a package's own re-export/entrypoint module.

### Compatibility Changes

- Don't add hacks, shims, or dual-path logic unless a frozen product or repository contract requires compatibility.
- Don't remove or break an existing interface as unrelated cleanup. When an authorized contract change intentionally removes one, update its consumers and tests in the same scoped change.
- Remove code only when the requested change makes it dead and verification proves it is no longer used.

### Surgical Changes

- Make the smallest change possible. One goal per change.
- Only remove imports and variables your own edit orphaned.
- Avoid wide refactors unless you can prove they're safe.
- Keep diffs reviewable and easy to roll back.

### Think Before Coding

- For multi-step, high-risk, or ambiguous work, state a brief approach, acceptance criteria, and test plan before editing.
- Small bounded work may proceed directly after inspecting the relevant code and instructions.

### Verify First

- Every change must be verifiable (tests, scripts, output). If you can't verify it, don't ship it.
- For bug fixes, add or update a regression test when practical. If no reliable automated test fits, explain the verification used instead.

## Protect Local Data

- Preserve unrelated dirty files, branches, and worktrees.
- Confirm before deleting, overwriting, or moving important local data.

## Git Safety

- Resolve the default branch from repository state or governance; never assume its name.
- Never edit, commit, merge, or push on the default branch. Cutting a non-default branch from it is fine.
- Resolve the complete non-default branch name from repository governance or the user's instruction. If neither names it, ask before branch creation; never add a fixed prefix or invent a branch name.
- Push requires separate explicit remote intent for the exact non-default branch and current verified head.
- Preserve unrelated dirty files, branches, and worktrees. Cleanup, worktree removal, task archival, and branch deletion require their own exact authorization.

## Deployment

- Resolve this section from the live project before finishing bootstrap; keep it only when the repository deploys, per the Full-Stack Harness `deployment-contract.md`.
- Platform and mode: the deploy platform id (for example `cloudflare`, `vercel`, `aws`) and `git_connected`, `ci_connected`, or `manual`.
- Production deploys only from the resolved default branch; preview builds track non-default branch pushes. They are separate environments with separate URLs and stateful resources, and a preview PASS never proves production.
- Preview mechanism or URL pattern: <fill>
- Production URL: <fill>
- Deployed-commit check (platform API/CLI command or response header): <fill>
- Protected resources preview must never bind: <databases, buckets, secrets, domains>

## Managed Full-Stack Harness Runs

The rules below apply only to a PLAN-v6/RUN-v11 managed route. They do not convert small direct work into a managed run.

- Map one independently testable goal to one mission. Tasks inside that mission stay sequential under one writer.
- Give every writer an explicit file-ownership scope and a separate worktree. Workers and reviewers never delegate; the Harness parent dispatches every explorer, writer, and reviewer as a sibling.
- Freeze and integrate shared APIs, schemas, and types before starting dependent write missions in parallel.
- Cut that resolved run branch from the current default branch, then create every implementation worktree from the current resolved integration-branch SHA.
- Before dispatch, verify each worktree has the expected repository, branch/ref, exact base HEAD, and a clean status.
- Run focused checks and at least one exact-head read-only review in or against each completed worktree. A repair requires a fresh review.
- With matching `integrate_locally` authorization, merge only reviewed worktree heads into the resolved integration branch.
- After serial integration, use fresh read-only reviewers on the exact unified integration SHA, then run one broad final validation on the fixed candidate SHA.
- The run defaults to verified local completion; only an explicit remote outcome pushes the verified integration head to the run branch. Landing the run branch on the default branch is the user's own step, done outside this harness.
- Later work cuts a fresh run branch from the then-current default branch.

### Action Authorization

- Before any action represented in the RUN authorization ledger, verify its exact authorization. Preserve all 12 keys: `invoke_external_runtime`, `spawn_subagents`, `create_user_owned_tasks`, `create_local_worktrees`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `archive_worker_tasks`, `remove_worktrees`, and `delete_branches`.
- Ordinary plan-backed work starts and normally ends `local_only` on the resolved integration branch; a separate explicit remote outcome may move it to `integration_push` when that verified head is pushed. The run is complete there; it does not wait for GitHub.
- With matching `create_local_branches` authorization, work on the exact resolved non-default run branch.
- With matching `create_local_commits` authorization, commit only the verified task scope.
- Worker branches stay local. With matching `integrate_locally` authorization, integrate exact-head review-passing work into the resolved integration branch.
- Run the exact repository-defined focused verification and applicable E2E commands, then review the complete diff before push. If commands are undocumented, inspect the repository's package scripts and CI configuration and state the commands selected.
- Treat a PASS from the required automated E2E on the current head as the proof for its covered primary journeys. Record duplicate manual smoke as `not required - covered by current-head E2E`; require manual smoke only for a materially different environment or an uncovered visual/external-integration risk.
- With matching explicit remote intent and `push` authorization, push only the verified resolved integration branch and current head. The current RUN push guard requires one exact branch target, the authorized integration head, and known `observed.git.default_branch`; refuse any target or integration branch that resolves to the observed default branch, with literal `main` retained as a fail-safe refusal.
- Remove only an authorized clean linked worktree, then delete only the authorized local worker branch. Never remove the primary checkout, and never delete the run branch the user still has to read.
- Task archival, worktree removal, and branch deletion remain separate ledger actions even when several are approved in one explicit readiness statement.

## Review Guidelines

Treat authorization bypasses, writes to the default branch, stale review SHAs, data loss, scope escapes, and missing behavior verification as blocking findings. Do not report style preferences as blockers.

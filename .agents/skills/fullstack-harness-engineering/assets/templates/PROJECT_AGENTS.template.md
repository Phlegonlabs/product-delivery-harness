# Project Rules

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

## Pull Request Flow

- Do not push directly to `<base-branch>`.
- Before any action represented in the RUN authorization ledger, verify its exact authorization. Common GitHub-flow examples are branch creation, local commits, local integration, repository configuration, push, PR creation, review-state mutation, merge, and cleanup. When a RUN ledger exists, the matching action must be true for the exact target; direct work without RUN still requires an explicit user instruction for the covered mutation.
- For plan-backed work, choose landing from the requested outcome. Local branch, commit, or integration work stays `local_only` and does not wait for GitHub. For an explicitly requested pull-request outcome, inspect the full launch, review, and merge path at Plan Readiness. Request every missing branch, commit, integration, push, PR, review-management, and merge action once with exact scope, then record each approved action under its own ledger key. Before a PR exists, bind review and merge to `future-pr:<owner>/<repo>:base=<base-branch>:head=<head-branch>`; after creation, verify the binding and append the exact `pr:<full-PR-URL>` target. Include an exact repository-configuration action in that checkpoint only when the observed setup requires it.
- With matching `create_local_branches` authorization, work on `<branch-prefix>/<short-name>`.
- With matching `create_local_commits` authorization, commit only the verified task scope.
- Worker branches stay local. With matching `integrate_locally` authorization, integrate verified work into one final parent branch.
- Run `<verification-command>` and `<e2e-command>`, then review the complete diff before push.
- Treat a PASS from the required automated E2E on the current head as the proof for its covered primary journeys. Record duplicate manual smoke as `not required - covered by current-head E2E`; require manual or deployment smoke only for a materially different environment or an uncovered visual/external-integration risk.
- Change branch rules, required checks, repository auto-merge, or Codex review settings only with matching `configure_repository` authorization.
- With matching `push` authorization, push only the final parent branch.
- With separate `create_pr` authorization, open a Draft PR. Do not create a non-draft PR, mark it ready, or otherwise expose it to automatic review without matching `manage_pr_review` authorization.
- With separate `manage_pr_review` authorization, mark the PR ready when required and request Codex review immediately; do not wait for CI first.
- After every new push, start or observe current-head CI, including required E2E, and request current-head review again. Poll both gates concurrently.
- After current-head CI and Codex review pass and unresolved threads reach zero, use matching `merge_pr` authorization to enable squash auto-merge with an exact head-SHA match. Never enable auto-merge before those gates pass.
- When every remaining branch, commit, push, PR creation, review-management, and merge mutation is explicitly authorized for its exact target, continue through that landing flow without pausing between stages. Poll CI and review, reset stale evidence after every push, fix only authorized in-scope findings, and finish only after GitHub reports the PR merged.
- After a merged PR, re-fetch the base and verify the exact PR head before cleanup. Remove only an authorized clean linked worktree, switch the primary checkout to the base branch, then delete only the authorized local feature branch. Never remove the primary checkout.
- Merge, auto-merge, deploy, branch deletion, and worktree removal remain separate ledger actions even when several are approved in one explicit readiness statement.

## Cloudflare Release Flow

- For deployable Cloudflare applications, use one codebase with isolated `development` and `production` Workers and environment-specific storage, secrets, auth configuration, payment mode, routes, and webhooks.
- Deploy the exact current PR head to the PLAN-v5 development target only after current-head CI passes and `deploy` authorization covers its exact `release:<target-id>` and authorized head. A new push makes that grant and its evidence stale.
- Require development migration and deployed-environment E2E PASS before merge. Development uses non-production data and payment sandbox mode when payment applies.
- Publish the exact merged `<base-branch>` SHA to the production target only after GitHub reports the PR merged and exact production-target deploy authorization is present. Keep the authorized candidate head separate from the resulting merged source SHA. Production smoke must pass before release completion.
- Use the exact-SHA dispatched Cloudflare deployment workflow. Do not make an arbitrary branch push or base-branch push an unconditional deployment path, and do not infer deploy authorization from push or merge.
- Keep Wrangler configuration as the repository source of truth. Never store Cloudflare tokens or environment secret values in PLAN, RUN, workflow files, or committed dotenv files.
- Before the first deploy for this product, confirm `wrangler.jsonc` exists (scaffold it per the Full-Stack Harness's `cloudflare-deployment-lifecycle.md` if missing) and confirm Cloudflare account access is verified (GitHub Environment secrets for the CD workflow, or an authenticated Wrangler session locally). Never attempt a deploy while either is unverified.

## Review Guidelines

Treat authorization bypasses, direct base-branch landing, stale check/review/deployment SHAs, cross-environment data or secret reuse, data loss, scope escapes, and missing behavior verification as blocking findings. Do not report style preferences as blockers.

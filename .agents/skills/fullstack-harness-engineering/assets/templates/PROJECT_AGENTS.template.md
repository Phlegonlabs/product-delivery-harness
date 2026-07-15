# Project Rules

## Protect Local Data

- Preserve unrelated dirty files, branches, and worktrees.
- Confirm before deleting, overwriting, or moving important local data.

## Pull Request Flow

- Do not push directly to `<base-branch>`.
- Before any action represented in the RUN authorization ledger, verify its exact authorization. Common GitHub-flow examples are branch creation, local commits, local integration, repository configuration, push, PR creation, review-state mutation, merge, and cleanup. When a RUN ledger exists, the matching action must be true for the exact target; direct work without RUN still requires an explicit user instruction for the covered mutation.
- With matching `create_local_branches` authorization, work on `<branch-prefix>/<short-name>`.
- With matching `create_local_commits` authorization, commit only the verified task scope.
- Worker branches stay local. With matching `integrate_locally` authorization, integrate verified work into one final parent branch.
- Run `<verification-command>` and review the complete diff before push.
- Change branch rules, required checks, repository auto-merge, or Codex review settings only with matching `configure_repository` authorization.
- With matching `push` authorization, push only the final parent branch.
- With separate `create_pr` authorization, open a Draft PR.
- After CI passes, use separate `manage_pr_review` authorization to mark it ready and request Codex review.
- After every new push, wait for current-head CI and request review again.
- After current-head CI and Codex review pass and unresolved threads reach zero, use matching `merge_pr` authorization to enable squash auto-merge with an exact head-SHA match. Never enable auto-merge before those gates pass.
- When every remaining branch, commit, push, PR creation, review-management, and merge mutation is explicitly authorized for its exact target, continue through that landing flow without pausing between stages. Poll CI and review, reset stale evidence after every push, fix only authorized in-scope findings, and finish only after GitHub reports the PR merged.
- After a merged PR, re-fetch the base and verify the exact PR head before cleanup. Remove only an authorized clean linked worktree, switch the primary checkout to the base branch, then delete only the authorized local feature branch. Never remove the primary checkout.
- Merge, auto-merge, deploy, branch deletion, and worktree removal require separate approval.

## Review Guidelines

Treat authorization bypasses, direct base-branch landing, stale check/review SHAs, data loss, scope escapes, and missing behavior verification as blocking findings. Do not report style preferences as blockers.

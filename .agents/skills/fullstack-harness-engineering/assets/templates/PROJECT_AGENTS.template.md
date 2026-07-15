# Project Rules

## Protect Local Data

- Preserve unrelated dirty files, branches, and worktrees.
- Confirm before deleting, overwriting, or moving important local data.

## Pull Request Flow

- Do not push directly to `<base-branch>`.
- Before each branch, local integration, push, PR creation, or PR review-state mutation, verify its exact authorization. When a RUN ledger exists, the matching action must be true for the exact target; direct work without RUN still requires an explicit user instruction for the covered mutation.
- With matching `create_local_branches` authorization, work on `<branch-prefix>/<short-name>`.
- Worker branches stay local. With matching `integrate_locally` authorization, integrate verified work into one final parent branch.
- Run `<verification-command>` and review the complete diff before push.
- With matching `push` authorization, push only the final parent branch.
- With separate `create_pr` authorization, open a Draft PR.
- After CI passes, use separate `manage_pr_review` authorization to mark it ready and request Codex review.
- After every new push, wait for current-head CI and request review again.
- Merge, deploy, branch deletion, and worktree removal require separate approval.

## Review Guidelines

Treat authorization bypasses, direct base-branch landing, stale check/review SHAs, data loss, scope escapes, and missing behavior verification as blocking findings. Do not report style preferences as blockers.

# Project Rules

## Protect Local Data

- Preserve unrelated dirty files, branches, and worktrees.
- Confirm before deleting, overwriting, or moving important local data.

## Pull Request Flow

- Do not push directly to `<base-branch>`.
- Work on `<branch-prefix>/<short-name>`.
- Worker branches stay local. Integrate verified work into one final parent branch.
- Run `<verification-command>` and review the complete diff before push.
- Open a Draft PR, wait for CI, mark it ready, and request Codex review.
- After every new push, wait for current-head CI and request review again.
- Merge, deploy, branch deletion, and worktree removal require separate approval.

## Review Guidelines

Treat authorization bypasses, direct base-branch landing, stale check/review SHAs, data loss, scope escapes, and missing behavior verification as blocking findings. Do not report style preferences as blockers.

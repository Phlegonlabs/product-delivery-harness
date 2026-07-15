# Project Rules

## Protect Local Data

- Never delete, overwrite, or move important local data without explicit user approval.
- Preserve unrelated dirty files, branches, and worktrees.
- Avoid destructive Git and filesystem commands unless the user asked for that exact action.

## Keep Changes Simple

- Make the smallest change that satisfies the request.
- Do not add speculative abstractions or unrelated cleanup.
- Write short, direct documentation, comments, commit messages, and reports.

## Git And Pull Request Flow

- Do not push directly to `main`.
- Before each branch, push, PR creation, or PR review-state mutation, verify its exact authorization. When a RUN ledger exists, the matching action must be true for the exact target; direct work without RUN still requires an explicit user instruction for the covered mutation.
- With matching `create_local_branches` authorization, create a `codex/<short-name>` branch for implementation work.
- Worker branches and worktrees stay local. The parent integrates verified worker commits into one final branch.
- Before push, run the required tests and review the complete diff against `main`.
- With matching `push` authorization, push only the final branch.
- With separate `create_pr` authorization, open a Draft PR.
- After CI passes, use separate `manage_pr_review` authorization to mark the PR ready and request Codex review.
- A new push makes earlier CI and review results stale. Wait for checks and request review again for the new head SHA.
- Merge, auto-merge, deploy, branch deletion, and worktree removal are separate actions. Do not infer approval for them from implementation or PR creation.

## Required Verification

Run:

```text
python -m unittest discover -s .agents/skills/fullstack-harness-engineering/scripts/tests -v
```

Also run `git diff --check` before commit.

## Review Guidelines

Treat these as blocking findings:

- Any path that bypasses explicit action authorization for branch, commit, integration, repository configuration, push, PR review management, merge, deploy, or cleanup.
- Any direct push or merge path to `main` that bypasses the PR landing flow.
- Any PASS check or review state that is not bound to the current PR head SHA.
- Any schema change that breaks valid RUN schema v2 files without an explicit migration path.
- Any worker that edits parent-owned PLAN/RUN state, escapes its write scope, or independently pushes or opens a PR.
- Any behavior change without focused tests, or any test/workflow command that does not run from the repository root.

Do not report formatting preferences as blockers. Focus on correctness, authorization boundaries, stale-state safety, data preservation, and missing verification.

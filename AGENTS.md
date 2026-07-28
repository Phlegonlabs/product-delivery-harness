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
- Before any action represented in the RUN authorization ledger, verify its exact authorization. Common GitHub-flow examples are branch creation, local commits, local integration, repository configuration, push, PR creation, review-state mutation, merge, and cleanup. When a RUN ledger exists, the matching action must be true for the exact target; direct work without RUN still requires an explicit user instruction for the covered mutation.
- With matching `create_local_branches` authorization, create a `codex/<short-name>` branch for implementation work.
- With matching `create_local_commits` authorization, commit only the verified task scope.
- Worker branches and worktrees stay local. With matching `integrate_locally` authorization, the parent integrates verified worker commits into one final branch.
- Before push, run the required tests and review the complete diff against `main`.
- Change branch rules, required checks, repository auto-merge, or Codex review settings only with matching `configure_repository` authorization.
- With matching `push` authorization, push only the final branch.
- With separate `create_pr` authorization, open a Draft PR.
- With separate `manage_pr_review` authorization, mark the PR ready and request Codex review immediately after creation; do not wait for CI first. Observe current-head CI and review concurrently.
- A new push makes earlier CI and review results stale. Start or observe current-head CI and request review again for the new head SHA immediately, then poll both gates concurrently.
- After current-head CI and Codex review pass and unresolved threads reach zero, the next step depends on the PR's base. For a PR into the resolved integration branch, matching `merge_pr` authorization allows enabling squash auto-merge with an exact head-SHA match; never enable it before those gates pass. For a PR into `main`, stop: report the PR as merge-ready with its exact head SHA and let the human merge. Do not merge into `main` and do not enable auto-merge there, no matter which gates passed — only a separate explicit instruction naming that exact PR authorizes it.
- After GitHub reports the PR merged, fetch the base and confirm the local feature branch still equals the merged PR head. With exact cleanup authorization, remove only a clean linked worktree, switch the primary checkout to `main`, then delete only that local feature branch. Never remove the primary checkout.
- Merge, auto-merge, deploy, branch deletion, and worktree removal are separate actions. Do not infer approval for them from implementation or PR creation.

## Required Verification

Edit only the canonical sources in `.agents/skills/`, then run all of this from the repository root:

```text
python scripts/sync_plugin_skills.py
python scripts/sync_plugin_skills.py --check
python -m unittest discover -s .agents/skills/fullstack-harness-engineering/scripts/tests -v
python -m unittest discover -s .agents/skills/prd-builder/scripts/tests -v
python -m unittest discover -s plugins/fullstack-harness/skills/fullstack-harness-engineering/scripts/tests -p "test_packaged_*.py" -v
git diff --check
```

CI runs the same set. Running only the engineering suite passes locally and then fails CI at the sync check, because the generated plugin bundle was never regenerated.

## Review Guidelines

Treat these as blocking findings:

- Any path that bypasses explicit action authorization for any of the 19 ledger actions — external runtime invocation, subagent spawn, user-owned task creation, worktree creation, branch, commit, integration, repository configuration, push, PR creation, remote CI dispatch, PR review management, merge, cloud-resource provisioning, deploy, worker-task archival, worktree removal, or branch deletion.
- Any `push`, `merge_pr`, or `deploy` grant that reaches a target outside the execution-intent scope without recording that target's own separate source in `target_sources`.
- Any direct push or merge path to `main` that bypasses the PR landing flow.
- Any PASS check or review state that is not bound to the current PR head SHA.
- Any schema change that breaks valid RUN schema v2 through v10 files without an explicit migration path.
- Any worker that edits parent-owned PLAN/RUN state, escapes its write scope, or independently pushes or opens a PR.
- Any behavior change without focused tests, or any test/workflow command that does not run from the repository root.

Do not report formatting preferences as blockers. Focus on correctness, authorization boundaries, stale-state safety, data preservation, and missing verification.

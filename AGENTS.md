# Project Rules

## Protect Local Data

- Never delete, overwrite, or move important local data without explicit user approval.
- Preserve unrelated dirty files, branches, and worktrees.
- Avoid destructive Git and filesystem commands unless the user asked for that exact action.

## Keep Changes Simple

- Make the smallest change that satisfies the request.
- Do not add speculative abstractions or unrelated cleanup.
- Write short, direct documentation, comments, commit messages, and reports.

## Git Flow

- Do not edit, commit, merge, or push directly to the default branch (`main` in this repository).
- Before any action represented in the RUN authorization ledger, verify its exact authorization. When a RUN ledger exists, the matching action must be true for the exact target; direct work without RUN still requires an explicit user instruction for the covered mutation.
- With matching `create_local_branches` authorization, create the exact non-default branch named by repository governance or the user, cut from the current default branch. If neither source names it, ask before branch creation; never add a fixed prefix.
- With matching `create_local_commits` authorization, commit only the verified task scope.
- Worker branches and worktrees stay local. With matching `integrate_locally` authorization, the parent integrates verified worker commits into that one run branch.
- Before push, run the required tests and review the complete diff against `main`.
- With matching `push` authorization, push that run branch. The run ends there: report the branch and its exact head SHA.
- Landing the pushed branch on `main` is the user's own step. Do not open a pull request, request review, merge, or deploy unless the user asks for that exact thing in its own instruction.
- Branch deletion and worktree removal are separate actions. Do not infer approval for them from implementation or from a successful push.

## Required Verification

Edit only the canonical sources in `.agents/skills/`, then run all of this from the repository root:

```text
python scripts/sync_plugin_skills.py
python scripts/sync_plugin_skills.py --check
python -m unittest discover -s .agents/skills/full-harness/scripts/tests -v
python -m unittest discover -s .agents/skills/prd-builder/scripts/tests -v
python -m unittest discover -s .agents/skills/product-design-builder/scripts/tests -v
python -m unittest discover -s plugins/fullstack-harness/skills/full-harness/scripts/tests -p "test_packaged_*.py" -v
git diff --check
```

CI runs the same set. Running only the engineering suite passes locally and then fails CI at the sync check, because the generated plugin bundle was never regenerated.

Every flow that lands on `main` bumps the release version in the same change: `package.json`, both plugin manifests (`plugins/fullstack-harness/.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`), `.claude-plugin/marketplace.json`, the README badges and version-history entries in all three languages, the RUNBOOK `required_harness_version` default, and the pinned version asserts in `test_private_marketplace.py` and `test_skill_contract.py`. A breaking skill-bundle change bumps the minor version.

## Review Guidelines

Treat these as blocking findings:

- Any path that bypasses explicit action authorization for one of the 12 ledger keys: `invoke_external_runtime`, `spawn_subagents`, `create_user_owned_tasks`, `create_local_worktrees`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `archive_worker_tasks`, `remove_worktrees`, or `delete_branches`.
- Any `push` that reaches `main`, or any run whose own integration branch resolves to `main`.
- Any `push` grant whose target is a branch other than the run's resolved integration branch.
- Any gate PASS that is not bound to the exact integration head SHA.
- Any worker that edits parent-owned PLAN/RUN state, escapes its write scope, or independently pushes.
- Any behavior change without focused tests, or any test/workflow command that does not run from the repository root.

Do not report formatting preferences as blockers. Focus on correctness, authorization boundaries, stale-state safety, data preservation, and missing verification.

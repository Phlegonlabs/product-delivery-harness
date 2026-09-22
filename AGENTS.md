# Project Rules

## Project Entry And Current Work

Start with the effective repository instructions, `docs/DOCUMENTS.md` when present, current product/design sources and relevant unfinished work. At the first work in a new session and every skill invocation, apply `delivery-harness/references/document-sync-contract.md` (under `skills/` in this source repository). Observe loaded versus installed skill identity; unknown means unknown, not the current disk version.

Keep one current PRD. Complete enhancements use `docs/epics/EPIC-<id>.md`, indexed in `docs/DOCUMENTS.md`, to record the problem, baseline, accepted outcome, requirement references, dependencies, document impact and result. Small fixes append to the relevant Epic; detailed direct-task evidence may be linked from it. Follow `delivery-harness/references/bounded-enhancement.md`; an Epic never duplicates PRD or RUN and never grants actions.

Derive the goal, write scope, design source, dependencies and acceptance checks in the existing task record or PLAN/RUN. Use direct work when one writer and one coherent verification sequence suffice; use managed coordination only when durable handoff, isolated integration or a bounded graph requires it. Preserve valid decisions and authorizations; ask only about a concrete missing dependency.

## Repository Change Checkpoints

These checks apply to every agent task, including work outside Product Delivery Harness and repositories without PLAN/RUN. Run them at task start, after a significant edit/commit/merge/branch switch or newly observed external change, and before completion or handoff. They are task checkpoints, not a background timer, and require only local Git plus the repository documents.

- Observe repository root, branch, HEAD, staged/unstaged changes and non-ignored untracked paths. Compare with the last recorded repository/branch/HEAD and scoped change evidence in the relevant Epic. Use bounded local history and scoped diffs; do not fetch, scan all history or open credential files. Include commits made outside Harness as well as current working-tree changes.
- If the baseline is missing, unreachable or belongs to another branch/repository, record a first observation or baseline gap and the current facts. Do not claim an exact delta or that nothing changed. Preserve unrelated dirty work; discovering a change is not permission to edit it.
- Record each meaningful code, product, configuration or documentation change in `docs/epics/EPIC-<id>.md`, even for small direct work. Append to the matching Epic's Change Log; create a narrowly scoped Epic only when no suitable one exists. An unknown-purpose external change is `observed / unverified` with an explicit scope/intent gap, not an accepted feature or completed task. Keep `docs/DOCUMENTS.md` indexed.
- Keep the record factual: observation time, repository/branch, baseline and observed HEAD, affected paths and requirement IDs when known, observed behavior/change, decision source if known, actual verification and unresolved work. Label uncommitted evidence `working-tree` and record its actual verification separately; HEAD alone does not identify those bytes. Retain scoped diff evidence or its fingerprint so an unchanged HEAD cannot hide new edits. Exclude secrets, generated caches and the Epic/index update itself from recursive change logging.
- Group related changes into one logical entry; append again only when the observed change, verification or unresolved state differs. Reuse an existing entry from another agent instead of duplicating it. A no-change check needs no new Epic or log row. Preserve old results and archived records; a follow-up links them rather than rewriting history.
- During a read-only or no-write task, report the proposed Epic update without writing it. Otherwise update the Epic/index under the task's local documentation authority. The record never grants product approval, marks tests passed without evidence, creates PLAN/RUN, or authorizes commits, branches, installs, pushes, deployment or cleanup.

## Required Reading

- Before editing `skills/` or any documented flow, read the canonical SKILL.md and the references the change touches; the four READMEs are the documentation of record.
- Before running a Product Delivery Harness flow in a target repository, that repository's seeded `AGENTS.md` Required Reading rules govern the session — they are mandatory, not advisory.
- Work that skipped this reading is a blocking review finding.

## Protect Local Data

- Never delete, overwrite, or move important local data without explicit user approval.
- Preserve unrelated dirty files, branches, and worktrees.
- Avoid destructive Git and filesystem commands unless the user asked for that exact action.

## Gitignore Hygiene

- Treat `.gitignore` as part of every direct and managed change. During the scope scan, decide whether the task introduces or retires a local secret file, generated output, dependency directory, cache, log, temporary file, editor state, or platform artifact.
- Add only patterns justified by the repository's observed toolchain. Ignore value-bearing local environment and credential files plus reproducible local artifacts; keep source, lockfiles, migrations, tests, fixtures, configuration examples and schemas, product documents, and required canonical artifacts tracked.
- Keep `.env.example` or the platform-native example tracked with placeholders only, and ignore the corresponding value-bearing local file. Never open a secret file to decide its ignore rule.
- Preserve existing entries and use the narrowest practical patterns. Never add an ignore rule just to hide a dirty worktree, and never untrack a tracked file, delete it, or rewrite Git history without explicit approval. If a likely secret file is already tracked, stop and report its path without reading its value.
- Update `.gitignore` in the same scoped change that introduces the artifact class. Verify representative ignored and tracked paths with `git check-ignore -v`, `git status --short --ignored`, and `git ls-files` before completion.

## Keep Changes Simple

- Make the smallest change that satisfies the request.
- Do not add speculative abstractions or unrelated cleanup.
- Write short, direct documentation, comments, commit messages, and reports.

## Keep Product Contracts Current

- English `PRD.md` and `architecture.md` remain implementation authority. When drafting or updating them, maintain complete Chinese `PRD.zh-TW.md` and `architecture.zh-TW.md` review copies under the Product Definition bilingual-review contract; reconcile owner feedback into English first. Chinese copies never replace canonical inputs or grant separate approval. At task entry and change checkpoints, when an existing English PRD or architecture has no Chinese copy, create a complete same-directory `<source-stem>.zh-TW.md` translation under existing write authority, even without a full Harness flow. Preserve English bytes and approvals; validate each available pair and record the backfill in the matching Epic. Read-only tasks report the missing copy; do not overwrite existing translations or automatically rewrite archives.

- When `docs/product/PRD.md` exists, every product change updates the affected PRD requirements, acceptance criteria, and trace IDs in the same change, including small post-delivery fixes that do not use Product Delivery Harness PLAN/RUN.
- Before implementation, classify the change's UI impact as `none`, `structure`, `style`, or `both`. Adding a page, route, visible region, state, or responsive behavior is at least `structure`.
- For `structure` or `both`, update product-owned behavior through `product-definition-builder` first, obtain Product Definition Approval, then update only the affected `ui-design.md` and `wireframes.html` scope through `ui-design-builder` and rerun its gates. For `style` or `both`, rerun Style Integration, Impeccable review, H1-H9 grading, and Visual Approval or record the owner's decision to retain the existing direction; update the design-system pair only when required.
- Preserve unaffected requirements, IDs, pages, wireframes, and design decisions. A direct task may stay small, but it is not complete while implementation and the canonical product documents disagree.

## Monetization And Partner Channels

When a product has pricing, paid access, purchase-gated features or outside sellers, read `skills/delivery-harness/references/project-operating-rules.md#monetization-and-partner-channels` before product, stack or UI changes. Keep those gates in the PRD and separate billing, entitlements and partner responsibilities.

## Mission Task Split

- When decomposing a PRD into full-delivery missions, split each mission into more, finer tasks: one task per small, independently verifiable step, so each step is done and checked carefully.
- Each task keeps its own atomic commit. Finer tasks never create extra parallel workers; they stay sequential checkpoints inside the mission.

## Git Flow

- This repository is permanently main-only. Do not edit or commit directly on the default branch (`main`); update it only by exact-SHA promotion under `skills/delivery-harness/references/branch-promotion-contract.md`. The retired branch name `development` is not a release source or integration target.
- Before any action represented in the RUN authorization ledger, verify its exact authorization. When a RUN ledger exists, the matching action must be true for the exact target; direct work without RUN still requires an explicit user instruction for the covered mutation.
- With matching `create_local_branches` authorization, create the exact non-default run branch named by repository governance or the user. Cut both `initial_delivery` and `enhancement` runs from the observed remote `main` head. If the delivery kind or branch name is unresolved, ask; never add a fixed prefix.
- With matching `create_local_commits` authorization, commit only the verified task scope. Commit atomically: one commit per minimal logical change (matching the minimal task split), never bundling unrelated changes.
- Worker branches and worktrees stay local. With matching `integrate_locally` authorization, the parent integrates verified worker commits into that one run branch.
- Harness 0.38 RUNs close `local_only` at candidate C. Their `push` authorization remains false, `pushed_head_sha` remains null, and PLAN contains no push lifecycle node. Explicitly pinned pre-0.38 RUNs retain their historical run-branch push path only for recovery.
- After RUN close, archive on the same branch with exact main evidence and a required immutable checkout-external anchor, create archive-only direct child A, and verify the archived PLAN/RUN, receipt, anchor, relocation, and full suite. Publishing A requires a new instruction plus that same anchor and external request/attempt/receipt; it pushes without force and reads back A. Candidate gates and separately authorized exact-A `main` promotion follow; never force-push.
- An `initial_delivery` or `enhancement` completes with the exact verified candidate at remote `main`. Non-production environments build from the candidate branch/SHA, never a persistent integration branch.
- Branch deletion and worktree removal are separate actions. Do not infer approval for them from implementation or from a successful push.

## Update Local Skills

- Every push that changes `skills/` is followed by the local skills update in the same turn. Quiesce active skill-using sessions, then run `install.sh` or `install.ps1` against `~/.agents/skills/`. It installs `delivery-harness`, `product-definition-builder`, `ui-design-builder`, `design-system-compiler`, `code-security-review`, `product-activation`, and `seo-growth-review`; retires `full-harness`, `prd-builder`, and `product-design-builder`; and writes the prior copies under `~/.agents/skill-backups/product-delivery-harness/`. Never replace the installer with manual move/copy commands, and never overwrite or delete prior copies. Restore the backup if verification fails. Restart the host only after success. This step is mandatory after a push, never deferred.
- Per-runtime copies (Codex plugin, Claude plugin, Pi extension) stay retired. Do not install, update, or reinstall them.

## Required Verification

Edit only the canonical sources in `skills/`, then run all of this from the repository root:

```text
python -m pip install -r skills/delivery-harness/requirements-test.txt
python skills/delivery-harness/scripts/check_skill_spec.py
python -m pyflakes skills/delivery-harness/scripts skills/product-definition-builder/scripts skills/ui-design-builder/scripts skills/design-system-compiler/scripts skills/product-activation/scripts skills/seo-growth-review/scripts
python skills/delivery-harness/scripts/docs_weight.py
python -m unittest discover -s skills/delivery-harness/scripts/tests -v
# POSIX shells
HARNESS_GOLDEN_PATH=1 python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_golden_path.py" -v
# PowerShell
$env:HARNESS_GOLDEN_PATH='1'; python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_golden_path.py" -v; Remove-Item Env:HARNESS_GOLDEN_PATH
python -m unittest discover -s skills/product-definition-builder/scripts/tests -v
python -m unittest discover -s skills/ui-design-builder/scripts/tests -v
python -m unittest discover -s skills/design-system-compiler/scripts/tests -v
python -m unittest discover -s skills/product-activation/scripts/tests -v
python -m unittest discover -s skills/seo-growth-review/scripts/tests -v
git diff --check
```

CI runs the same set.

Every flow that promotes to `main` bumps the release version in the same change: `package.json`, `skills/delivery-harness/VERSION`, the README badges and version-history entries in all four languages, the RUNBOOK `required_harness_version` default, and the pinned version asserts in `test_skill_contract.py`. A breaking skill-bundle change bumps the minor version. After the release promotion reaches `main`, tag that commit with the matching `v<version>` tag — the READMEs' Releasing section is the full checklist.

Any change that adds or alters a skill, rule, or documented flow also updates the READMEs' descriptive sections in the same change, in all four languages — the README is documentation-of-record, not a release-time artifact.

## Review Guidelines

Treat these as blocking findings:

- Any path that bypasses explicit action authorization for one of the 12 ledger keys: `invoke_external_runtime`, `spawn_subagents`, `create_user_owned_tasks`, `create_local_worktrees`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `archive_worker_tasks`, `remove_worktrees`, or `delete_branches`.
- Any Harness 0.38 RUN with `integration_push`, non-null `pushed_head_sha`, enabled push grant, or a push lifecycle node; any legacy RUN push that reaches `main` or `development`; or any run whose integration branch resolves to either name.
- Any archive-candidate publication that lacks the receipt-bound immutable external anchor and separately authorized external request/attempt/receipt, does not prove exact C-to-A relocation, uses force, accepts remote drift, or fails to read back exact A. Neither it nor a legacy RUN grant authorizes `main`.
- Any `main` promotion that bypasses `skills/delivery-harness/references/branch-promotion-contract.md`, lacks separate exact branch/SHA authorization, uses force, moves a stale/diverged ref, or lacks complete exact-candidate verification. A required PR may create a new main SHA only with verified tree equality and immediate full exact-main-SHA verification before tag or release completion. Creating or using a persistent `development` branch is also blocking.
- Any gate PASS that is not bound to the exact integration head SHA.
- Any worker that edits parent-owned PLAN/RUN state, escapes its write scope, or independently pushes.
- Any behavior change without focused tests, or any test/workflow command that does not run from the repository root.

Do not report formatting preferences as blockers. Focus on correctness, authorization boundaries, stale-state safety, data preservation, and missing verification.

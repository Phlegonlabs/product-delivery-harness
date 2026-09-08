# Project Rules

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

- When `docs/product/PRD.md` exists, every product change updates the affected PRD requirements, acceptance criteria, and trace IDs in the same change, including small post-delivery fixes that do not use Product Delivery Harness PLAN/RUN.
- Before implementation, classify the change's UI impact as `none`, `structure`, `style`, or `both`. Adding a page, route, visible region, state, or responsive behavior is at least `structure`.
- For `structure` or `both`, update only the affected PRD UI Surface Contract entries and `wireframes.html` pages, then re-run their applicable validation and approval gate. For `style` or `both`, also update the approved UI direction or record the owner's decision to keep it; update the design-system contract only when the approved change requires it.
- Preserve unaffected requirements, IDs, pages, wireframes, and design decisions. A direct task may stay small, but it is not complete while implementation and the canonical product documents disagree.

## Monetization And Partner Channels

- When a product has pricing, paid access, purchase-gated features, or outside sellers, keep explicit Monetization Infrastructure and Partner Channel gates in `docs/product/PRD.md`; record `not_required` with a reason when either does not apply.
- Resolve the commercial model and purchase surfaces before selecting technology. RevenueCat is one candidate, never the default: compare current official evidence for native store billing, RevenueCat, Qonversion, Adapty, Superwall, Stripe Billing, Paddle, Lemon Squeezy, or another product-fit option.
- Treat affiliate, referral, and reseller as different motions. A reseller decision must cover deal registration, price authority or wholesale terms, customer ownership, provisioning, delegated administration, support, renewals, termination, and channel conflict; an affiliate link alone does not satisfy it.
- Keep billing/store, entitlement, paywall/checkout, merchant-of-record/tax, attribution, commission/payout, and reseller-operation responsibilities separate in PRD, architecture, stack decisions, implementation, and tests. Update affected UI Surface Contract entries and `wireframes.html` before implementing customer, partner, pricing, purchase, or administration surfaces.

## Mission Task Split

- When decomposing a PRD into full-delivery missions, split each mission into more, finer tasks: one task per small, independently verifiable step, so each step is done and checked carefully.
- Each task keeps its own atomic commit. Finer tasks never create extra parallel workers; they stay sequential checkpoints inside the mission.

## Git Flow

- Do not edit or commit directly on `development` or the default branch (`main` in this repository). Update them only by exact-SHA promotion under `.agents/skills/delivery-harness/references/branch-promotion-contract.md`.
- Before any action represented in the RUN authorization ledger, verify its exact authorization. When a RUN ledger exists, the matching action must be true for the exact target; direct work without RUN still requires an explicit user instruction for the covered mutation.
- With matching `create_local_branches` authorization, create the exact non-default run branch named by repository governance or the user. Cut an `initial_delivery` run from the observed `main` head and an `enhancement` run from the observed `development` head. If the delivery kind or branch name is unresolved, ask; never add a fixed prefix.
- With matching `create_local_commits` authorization, commit only the verified task scope. Commit atomically: one commit per minimal logical change (matching the minimal task split), never bundling unrelated changes.
- Worker branches and worktrees stay local. With matching `integrate_locally` authorization, the parent integrates verified worker commits into that one run branch.
- Before any RUN push, run the required tests and review the complete diff against its recorded base. With matching `push` authorization, push only that run branch and exact verified head; the RUN ends there.
- After RUN close, promote the candidate to `development` only with separate action-time authorization for that remote branch and SHA, then fetch/read back the ref and run the complete internal suite against the exact remote `development` head.
- Promote to `main` only after the development head passes, the remote refs have not drifted, `main` is an ancestor of the verified development SHA, and the update is fast-forward to that same SHA. Require a second separate action-time authorization naming `main` and the SHA; never force-push. Read back both refs and verify production separately.
- An `initial_delivery` completes with `development` and `main` at the same verified SHA. An `enhancement` enters `development` first and leaves `main` unchanged until internal verification passes.
- Branch deletion and worktree removal are separate actions. Do not infer approval for them from implementation or from a successful push.

## Update Local Skills

- Every push that changes `.agents/skills/` is followed by the local skills update, in the same turn. Quiesce active skill-using sessions first. Move any existing `delivery-harness`, `product-definition-builder`, `design-system-compiler`, `product-activation`, `code-security-review`, `full-harness`, `prd-builder`, and `product-design-builder` directories to one timestamped backup under `~/.agents/skill-backups/product-delivery-harness/`, outside the discovery root; never overwrite or delete them. Copy the five current repository skills into `~/.agents/skills/`, verify their files match canonical, verify the three legacy IDs are absent from that discovery directory, then restart the host. Restore the backup if verification fails. This step is mandatory after a push, never deferred to a later request.
- Per-runtime copies (Codex plugin, Claude plugin, Pi extension) stay retired. Do not install, update, or reinstall them.

## Required Verification

Edit only the canonical sources in `.agents/skills/`, then run all of this from the repository root:

```text
python -m pip install -r .agents/skills/delivery-harness/requirements-test.txt
python .agents/skills/delivery-harness/scripts/check_skill_spec.py
python -m pyflakes .agents/skills/delivery-harness/scripts .agents/skills/product-definition-builder/scripts .agents/skills/design-system-compiler/scripts .agents/skills/product-activation/scripts
python -m unittest discover -s .agents/skills/delivery-harness/scripts/tests -v
HARNESS_GOLDEN_PATH=1 python -m unittest discover -s .agents/skills/delivery-harness/scripts/tests -p "test_golden_path.py" -v
python -m unittest discover -s .agents/skills/product-definition-builder/scripts/tests -v
python -m unittest discover -s .agents/skills/design-system-compiler/scripts/tests -v
python -m unittest discover -s .agents/skills/product-activation/scripts/tests -v
git diff --check
```

CI runs the same set.

Every flow that promotes to `main` bumps the release version in the same change: `package.json`, `.agents/skills/delivery-harness/VERSION`, the README badges and version-history entries in all four languages, the RUNBOOK `required_harness_version` default, and the pinned version asserts in `test_skill_contract.py`. A breaking skill-bundle change bumps the minor version. After the release promotion reaches `main`, tag that commit with the matching `v<version>` tag — the READMEs' Releasing section is the full checklist.

Any change that adds or alters a skill, rule, or documented flow also updates the READMEs' descriptive sections in the same change, in all four languages — the README is documentation-of-record, not a release-time artifact.

## Review Guidelines

Treat these as blocking findings:

- Any path that bypasses explicit action authorization for one of the 12 ledger keys: `invoke_external_runtime`, `spawn_subagents`, `create_user_owned_tasks`, `create_local_worktrees`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `archive_worker_tasks`, `remove_worktrees`, or `delete_branches`.
- Any RUN push that reaches `development` or `main`, or any run whose own integration branch resolves to either protected branch.
- Any RUN `push` grant whose target is a branch other than the run's resolved integration branch; post-RUN promotion never reuses that grant.
- Any `development` or `main` promotion that bypasses `.agents/skills/delivery-harness/references/branch-promotion-contract.md`, lacks separate exact branch/SHA authorization, uses force, moves a stale/diverged ref, or promotes to `main` without internal verification on the exact remote development SHA.
- Any gate PASS that is not bound to the exact integration head SHA.
- Any worker that edits parent-owned PLAN/RUN state, escapes its write scope, or independently pushes.
- Any behavior change without focused tests, or any test/workflow command that does not run from the repository root.

Do not report formatting preferences as blockers. Focus on correctness, authorization boundaries, stale-state safety, data preservation, and missing verification.

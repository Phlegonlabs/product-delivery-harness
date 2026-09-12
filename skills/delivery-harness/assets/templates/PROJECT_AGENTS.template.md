# Project Rules

This file is ready-to-use shared repository guidance. Resolve the repository's real default branch, commands, and protected paths from live project state; do not leave template placeholders or assume they are always the same across repositories.

## Runtime Boundary

- This file contains shared repository governance. Codex and Pi load it as their native project context; the generated `CLAUDE.md` imports it for Claude Code.
- Keep runtime-specific worker roles, model selection, subagent behavior, and launch flags in the Product Delivery Harness runtime adapter reference (`delivery-harness/references/runtime-adapters.md`, the section for the detected host). Never copy Codex, Claude Code, or Pi mechanics into another runtime's worker.
- Rules under **Managed Product Delivery Harness Runs** apply only after the Harness routes work into PLAN/RUN. Small direct work follows the shared principles, Git safety, and verification rules without creating Harness state, missions, workers, or worktrees unless the repository or user requires them.

## Required Reading

- Before any managed Product Delivery Harness work, the session reads this file's **Managed Product Delivery Harness Runs** rules and the installed `delivery-harness` SKILL.md (the orchestration skill itself, loaded as a skill rather than a table slot); the Skill Bindings table below pins the stage-slot skills the harness dispatches, and their pinned SHA-256 hashes are verified by `delivery-harness/scripts/check_skill_bindings.py`.
- Before any product-affecting direct work, the session reads the affected sections of `docs/product/PRD.md` plus every document `docs/DOCUMENTS.md` names for that scope (wireframes, design pair, architecture). A named source that does not exist yet is reported, not skipped.
- Skipping this reading is a blocking review finding: a change built on unread contracts is not a completed change.

## Skill Bindings

The delivery flow binds stage slots, not fixed skill names. This table binds the project's installed skills to those slots; updating it to adopt a new skill is a project edit, not a harness change, and a bound skill inherits the same modes, frozen sources, and review gates as the default.

| Slot | Stage | Bound skill | Pinned SHA-256 |
| --- | --- | --- | --- |
| design_direction | wireframes → UI direction and mockup (UI Design Pass) | <bundled Taste-aware pass (`design-taste-frontend`), or an installed taste skill> | <hash of the bound skill's SKILL.md> |
| design_compilation | frozen design-system pair | <bundled `design-system-compiler` + `frontend-design`, or your own> | n/a for defaults |
| frontend_implementation | implementation missions | <bundled `frontend-design`, or your own frontend skill> | <hash of the bound skill's SKILL.md> |
| ui_quality_verification | final page-quality pass after all design-reference pages are implemented | <bundled `impeccable` evaluate pass (`critique` + `audit`), or an installed UI-quality skill> | <hash of the bound skill's SKILL.md> |
| code_security_verification | fresh unified code-security review before final regression and closeout | <bundled `code-security-review`, or an installed read-only security-review skill> | n/a for default |

An unbound slot uses the bundled default. A non-default bound skill pins the SHA-256 of its SKILL.md; `delivery-harness/scripts/check_skill_bindings.py` recomputes it and fails on a mismatch, so changing a bound skill's content is a deliberate, reviewed pin update — never a silent swap. PLAN missions resolve their workers' skill lists from this table where a slot applies. The `code_security_verification` slot is loaded by a parent-dispatched, read-only integration-stage reviewer after all missions share one fixed candidate SHA; the reviewer receives no implementation or lifecycle authority.

## Core Development Principles

### Keep It Simple (KISS / YAGNI)

- Only do what's asked. No unrequested features, fallbacks, or "future-proof" abstractions.
- Prefer the simplest thing that works. Don't over-engineer.
- Don't "improve" code you weren't asked to touch.

### First Principles

- Reason from the problem's actual constraints, not from habit, inherited patterns, or how another project solved it.
- When a decision is non-obvious, derive it from what the product must do, then choose the simplest structure that satisfies it.

### File Size Limit

- A module must not exceed 500 lines. When an implementation would cross that limit, split it before committing — check and split at the moment the task's own file would cross the limit (via the task-refinement protocol in the Product Delivery Harness's `execution-task-decomposition.md`), not as a later end-of-project audit.
- Keep every module small, self-contained, and single-purpose. A module that proves problematic is deleted and rewritten from scratch rather than patched around; no compatibility shim keeps the replaced module alive.
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

## Keep Product Contracts Current

- When `docs/product/PRD.md` exists, every product change updates the affected PRD requirements, acceptance criteria, and trace IDs in the same change, including small post-delivery fixes that do not use Product Delivery Harness PLAN/RUN.
- Before implementation, classify the change's UI impact as `none`, `structure`, `style`, or `both`. Adding a page, route, visible region, state, or responsive behavior is at least `structure`.
- For `none`, preserve `wireframes.html` and the approved UI direction. For `structure` or `both`, update only the affected PRD UI Surface Contract entries and `wireframes.html` pages, then re-run their applicable validation and approval gate. For `style` or `both`, also update the approved UI direction or record the owner's decision to keep it; update `design-system.md` and `design-system.json` only when the approved change requires the formal pair to change.
- Preserve unaffected requirements, IDs, pages, wireframes, and design decisions. A direct task may stay small, but it is not complete while implementation and the canonical product documents disagree.

## Monetization And Partner Channels

- When a product has pricing, paid access, purchase-gated features, or outside sellers, keep explicit Monetization Infrastructure and Partner Channel gates in `docs/product/PRD.md`; record `not_required` with a reason when either does not apply.
- Resolve the commercial model and purchase surfaces before selecting technology. RevenueCat is one candidate, never the default: compare current official evidence for native store billing, RevenueCat, Qonversion, Adapty, Superwall, Stripe Billing, Paddle, Lemon Squeezy, or another product-fit option.
- Treat affiliate, referral, and reseller as different motions. A reseller decision must cover deal registration, price authority or wholesale terms, customer ownership, provisioning, delegated administration, support, renewals, termination, and channel conflict; an affiliate link alone does not satisfy it.
- Keep billing/store, entitlement, paywall/checkout, merchant-of-record/tax, attribution, commission/payout, and reseller-operation responsibilities separate in PRD, architecture, stack decisions, implementation, and tests. Update affected UI Surface Contract entries and `wireframes.html` before implementing customer, partner, pricing, purchase, or administration surfaces.

## Protect Local Data

- Preserve unrelated dirty files, branches, and worktrees.
- Confirm before deleting, overwriting, or moving important local data.

## Gitignore Hygiene

- Treat `.gitignore` as part of every direct and managed change. During the scope scan, decide whether the task introduces or retires a local secret file, generated output, dependency directory, cache, log, temporary file, editor state, or platform artifact.
- Add only patterns justified by the repository's observed toolchain. Ignore value-bearing local environment and credential files plus reproducible local artifacts; keep source, lockfiles, migrations, tests, fixtures, configuration examples and schemas, product documents, and required canonical artifacts tracked.
- Keep `.env.example` or the platform-native example tracked with placeholders only, and ignore the corresponding value-bearing local file. Never open a secret file to decide its ignore rule.
- Preserve existing entries and use the narrowest practical patterns. Never add an ignore rule just to hide a dirty worktree, and never untrack a tracked file, delete it, or rewrite Git history without explicit approval. If a likely secret file is already tracked, stop and report its path without reading its value.
- Update `.gitignore` in the same scoped change that introduces the artifact class. Verify representative ignored and tracked paths with `git check-ignore -v`, `git status --short --ignored`, and `git ls-files` before completion.

## Git Safety

- Resolve the default branch from repository state or governance; never assume its name.
- Use the resolved default branch (`main` for this workflow) as the only persistent protected branch and production source. Never edit or commit directly on it; the retired branch name `development` is not a release source or integration target.
- Resolve the complete non-default run-branch name from repository governance or the user's instruction. Cut both `initial_delivery` and `enhancement` runs from observed remote `main`. If the kind or name is unresolved, ask; never add a fixed prefix or invent a name.
- A RUN push requires separate explicit remote intent for its exact run branch and verified head. It never authorizes `main` or the retired `development` name.
- After RUN close, follow `delivery-harness/references/branch-promotion-contract.md`: verify the exact candidate and any isolated non-production deployment from its run branch/SHA, then separately authorize and fast-forward that SHA to `main`. Never force-push; stop on drift or divergence.
- Preserve unrelated dirty files, branches, and worktrees. Cleanup, worktree removal, task archival, and branch deletion require their own exact authorization.

## Deployment

- Resolve this section from the live project before finishing bootstrap; keep it only when the repository deploys, per the Product Delivery Harness `deployment-contract.md`.
- Platform and mode: the deploy platform id (for example `cloudflare`, `vercel`, `aws`) and `git_connected`, `ci_connected`, or `manual`.
- Non-production deploys from the exact candidate run branch or immutable candidate SHA; production deploys from `main`. Candidate and production environments remain separate, and a candidate PASS never proves production.
- Production and preview bind fully separate D1/KV/R2/Durable-Object resources: the preview environment declares its complete binding set, never references a production resource ID, and the deployment record's Resource Isolation table carries both ID sets.
- Before a deployable push, reconcile `docs/DEPLOYMENT.md` against tracked environment declarations, platform config, CI workflows, and auth/integration code. List exact secret and variable names, preview/production placement, source owner, and external-console tasks; never read or record secret values. After deployment, update only from read-only evidence and report every pending human action.
- Preview mechanism or URL pattern: <fill>
- Production URL: <fill>
- Deployed-commit check (platform API/CLI command or response header): <fill>
- Protected resources preview must never bind: <databases, buckets, secrets, domains>

## Post-Delivery Activation

- Use `product-activation` only after implementation has a fixed release SHA or exact artifact identity. It owns `docs/ACTIVATION.md` and never edits or extends a delivery PLAN/RUN.
- Product Definition may create the first Activation seed when the path is absent. Preserve an existing record; only `product-activation` reconciles its live action, source, evidence, and readiness state.
- Probe purpose-built connector/API/CLI first, then Browser, Computer Use, and manual handoff. Capability never grants permission.
- Bind every external write to the exact account or organization, project or property, environment, action, and current action digest. DNS, permissions, credentials, billing, production traffic, public submission, data sharing, and destructive changes require action-time confirmation.
- Never record secret values. Password, MFA, OTP, CAPTCHA, banking, tax, legal attestation, and secret-value entry remain user handoffs.
- Refresh and read back every change. A success toast, mutation response, upload, submission, or owner statement does not prove behavior.
- Route a missing product hook to a new `delivery-harness` change and a missing requirement, metric, TEST ID, or release target to `product-definition-builder`. Activation never patches product code in place.
- Activation readiness is per release target and does not keep the delivery RUN open or replace the later outcome-review measurement window.

## Managed Product Delivery Harness Runs

The rules below apply only to a PLAN-v6/RUN-v11 managed route. They do not convert small direct work into a managed run.

- Map one independently testable goal to one mission. Tasks inside that mission stay sequential under one writer.
- Give every writer an explicit file-ownership scope and a separate worktree. Workers and reviewers never delegate; the Harness parent dispatches every explorer, writer, and reviewer as a sibling.
- Freeze and integrate shared APIs, schemas, and types before starting dependent write missions in parallel.
- Cut every initial-delivery or enhancement run branch from current observed remote `main`, then create every implementation worktree from the resolved integration-branch SHA.
- Before dispatch, verify each worktree has the expected repository, branch/ref, exact base HEAD, and a clean status.
- Run focused checks and at least one exact-head read-only review in or against each completed worktree. A repair requires a fresh review.
- With matching `integrate_locally` authorization, merge only reviewed worktree heads into the resolved integration branch.
- After serial integration, use fresh read-only reviewers on the exact unified integration SHA, then run one broad final validation on the fixed candidate SHA.
- The RUN defaults to verified local completion; only explicit remote intent pushes the verified integration head to its run branch. Post-RUN `main` promotion follows the separate branch-promotion contract and never inherits the RUN grant.
- After a completed plan and before its archival, record every owner or agent update not already reflected in `docs/product/PRD.md` as one dated row in the `docs/tasks.md` Update Log — the fenced section the renderer preserves verbatim; product-affecting updates also follow Keep Product Contracts Current into the PRD in the same change.
- When the owner declares the goal complete and its run has passed the Closeout Bar, archive the finished plan runtime with `scripts/archive_run.py`: it moves `docs/goal/PLAN.md`, `RUN.md`, `DECISIONS.md`, `REFINEMENT_BACKLOG.md`, the `evidence/` directory, and the rendered `docs/tasks.md` into `docs/goal/archived/<YYYYMMDD-HHMMSS>-<run-id>/` and records the row in `docs/DOCUMENTS.md` (`contract-and-traceability.md`). Archival runs on the owner's completion instruction after its dry-run move list is approved; it never deletes and never moves anything under `docs/product/`. The archival commit rides the run branch and reaches `main` through the same promotion path. A later plan starts only after the completed set is archived, never by overwriting it. Post-delivery activation (`product-activation`) runs after promotion and before archival, so its findings are logged as Update Log rows while the rendered `docs/tasks.md` is still live.
- Later enhancement work cuts a fresh run branch from the current observed remote `main` head after the prior promotion state is resolved.

### Action Authorization

- Before any action represented in the RUN authorization ledger, verify its exact authorization. Preserve all 12 keys: `invoke_external_runtime`, `spawn_subagents`, `create_user_owned_tasks`, `create_local_worktrees`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `archive_worker_tasks`, `remove_worktrees`, and `delete_branches`.
- Ordinary plan-backed work starts and normally ends `local_only` on the resolved integration branch; a separate explicit remote outcome may move it to `integration_push` when that verified head is pushed. The run is complete there; it does not wait for GitHub.
- With matching `create_local_branches` authorization, work on the exact resolved non-default run branch.
- With matching `create_local_commits` authorization, commit only the verified task scope.
- Worker branches stay local. With matching `integrate_locally` authorization, integrate exact-head review-passing work into the resolved integration branch.
- Run the exact repository-defined focused verification and applicable E2E commands, then review the complete diff before push. If commands are undocumented, inspect the repository's package scripts and CI configuration and state the commands selected.
- Treat a PASS from the required automated E2E on the current head as the proof for its covered primary journeys. Record duplicate manual smoke as `not required - covered by current-head E2E`; require manual smoke only for a materially different environment or an uncovered visual/external-integration risk.
- With matching explicit remote intent and `push` authorization, push only the verified run integration branch and current head. The RUN push guard requires one exact target and refuses the retired `development` name, the observed default branch, and literal `main`; the default branch uses only the post-RUN promotion contract.
- After RUN completion, treat `main` promotion as a new exact action outside the RUN ledger. Require separate action-time authorization, fresh remote-ref read-back, fast-forward ancestry, and complete tests on the exact candidate SHA before promotion.
- Remove only an authorized clean linked worktree, then delete only the authorized local worker branch. Never remove the primary checkout, and never delete the run branch the user still has to read.
- Task archival, worktree removal, and branch deletion remain separate ledger actions even when several are approved in one explicit readiness statement.

### Commit Messages

Every commit in a managed run follows `delivery-harness/references/commit-convention.md`. The message shape:

```text
<type>(<scope>): <imperative summary>

Task: <mission-id>/<task-token>
Trace: <TRACE-ID>[, <TRACE-ID>]
Verified: <command or action> (<pass signal>)
```

- Write in English. Keep the subject at 72 characters or fewer, lowercase `type` and `scope`, imperative summary, no final period. `type` is one of `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `build`, `ci`; `scope` is a stable area such as `auth` or `ui`, never a filename.
- One commit holds one kind of change: a task commit carries one verified outcome, a repair commit one root-cause fix, an integration commit reviewed heads and coordination state only, a bookkeeping commit `PLAN.md`/`RUN.md` only. Two kinds of change land as two commits in dependency order.
- Every commit names exactly one task ID, its upstream traces, and the actual verifier with its literal pass signal. A merge or integration-only commit uses the mission-level form (`chore(integration): integrate mission M2` with `Mission`, `Plan-Revision`, `Integrated-Head`), never a fake task body.
- Direct small work — including plan-mode edits outside a managed run — commits with the same subject shape `<type>(<scope>): <imperative summary>` and no trailers required. The subject is the record:

```text
fix(dashboard): correct save-button copy
chore(deps): bump playwright to 1.49
```

## Review Guidelines

Treat authorization bypasses, direct edits or commits on protected branches, unverified or non-fast-forward promotion, stale review SHAs, data loss, scope escapes, missing behavior verification, and work that skipped the Required Reading rules as blocking findings. Do not report style preferences as blockers.

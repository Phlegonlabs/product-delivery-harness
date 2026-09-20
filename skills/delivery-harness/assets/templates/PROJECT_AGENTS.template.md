# Project Rules

This file is ready-to-use shared repository guidance. Resolve the repository's real default branch, commands, and protected paths from live project state; do not leave template placeholders or assume they are always the same across repositories.

## Runtime Boundary

- This file contains shared repository governance. Codex and Pi load it as their native project context; the generated `CLAUDE.md` imports it for Claude Code.
- Keep runtime-specific worker roles, model selection, subagent behavior, and launch flags in the Product Delivery Harness runtime adapter reference (`delivery-harness/references/runtime-adapters.md`, the section for the detected host). Never copy Codex, Claude Code, or Pi mechanics into another runtime's worker.
- Rules under **Managed Product Delivery Harness Runs** apply only after the Harness routes work into PLAN/RUN. Small direct work follows the shared principles, Git safety, and verification rules without creating Harness state, missions, workers, or worktrees unless the repository or user requires them.

## Project Entry And Current Work

Start with the effective repository instructions, `docs/DOCUMENTS.md` when present, current product/design sources and relevant unfinished work. At the first work in a new session and every skill invocation, apply `delivery-harness/references/document-sync-contract.md` (under `skills/` in this source repository). Observe loaded versus installed skill identity; unknown means unknown, not the current disk version.

Keep one current PRD. Complete enhancements use `docs/epics/EPIC-<id>.md`, indexed in `docs/DOCUMENTS.md`, to record the problem, baseline, accepted outcome, requirement references, dependencies, document impact and result. Small fixes may use an existing Epic or direct-task record. Follow `delivery-harness/references/bounded-enhancement.md`; an Epic never duplicates PRD or RUN and never grants actions.

Derive the goal, write scope, design source, dependencies and acceptance checks in the existing task record or PLAN/RUN. Use direct work when one writer and one coherent verification sequence suffice; use managed coordination only when durable handoff, isolated integration or a bounded graph requires it. Preserve valid decisions and authorizations; ask only about a concrete missing dependency.

## Required Reading

- Before any managed Product Delivery Harness work, the session reads this file's **Managed Product Delivery Harness Runs** rules and the installed `delivery-harness` SKILL.md (the orchestration skill itself, loaded as a skill rather than a table slot); the Skill Bindings table below pins the stage-slot skills the harness dispatches, and their pinned SHA-256 hashes are verified by `delivery-harness/scripts/check_skill_bindings.py`.
- Before any product-affecting direct work, the session reads the affected sections of `docs/product/PRD.md` plus every document `docs/DOCUMENTS.md` names for that scope (wireframes, design pair, architecture). A named source that does not exist yet is reported, not skipped.
- Skipping this reading is a blocking review finding: a change built on unread contracts is not a completed change.

## Skill Bindings

The delivery flow binds stage slots, not fixed skill names. This table binds the project's installed skills to those slots; updating it to adopt a new skill is a project edit, not a harness change, and a bound skill inherits the same modes, frozen sources, and review gates as the default.

| Slot | Stage | Bound skill | Pinned SHA-256 |
| --- | --- | --- | --- |
| ui_design | approved Product Definition → UI intake, wireframes, HiFi, approvals | `pending` | `pending` |
| style_integration | approved wireframe → page theme and connected HiFi target | `pending` | `pending` |
| design_compilation | frozen design-system pair | `pending` | `pending` |
| frontend_implementation | implementation missions | `pending` | `pending` |
| ui_quality_verification | authorized HiFi/page-quality review | `pending` | `pending` |
| code_security_verification | fresh unified code-security review before final regression and closeout | `pending` | `pending` |

These rows are intentionally unresolved in the seed. Before managed work, observe the installed skill trees, show the exact choices and side effects to the owner, then replace each required stage slot with one skill name and its full-tree SHA-256. `pending` in both cells is allowed only outside the checked stage. Product Definition uses `--stage product-definition`; UI authoring uses `--stage ui-design`; compilation uses `--stage design-compilation`; a proven headless/backend-only scope uses `--stage backend`. Omit `--stage` for full UI delivery or unknown applicability. Recheck at every stage change; a stage result never authorizes a later stage. `frontend-design` is external and supports visual direction/frontend authoring only; do not claim compilation, conformance, or read-only modes it does not define. The pinned `impeccable` profile requires separate authorization for subagents, browser/server activity, snapshot writes, and any optional binary download; it is not a Harness read-only reviewer. `delivery-harness/scripts/check_skill_bindings.py` rejects unresolved, fenced, duplicate, malformed, missing, or drifted bindings. The code-security reviewer receives no implementation or lifecycle authority.

## Core Development Principles

### Bounded Enhancement And Test Evidence

- At every skill invocation, apply the shared `delivery-harness/references/document-sync-contract.md`; inspect current PRD, runtime/skill identity and relevant instruction pointers before work. Preserve owner rules and immutable history.
- Follow `delivery-harness/references/bounded-enhancement.md`: reuse the accepted scope and valid action grants for repairs, technical document synchronization, module replacement and retesting. Do not repeat approvals for unchanged decisions. Never infer external, destructive, publication or installation authority.
- A module that fails accepted requirements may be replaced inside its write scope; preserve required interfaces, unaffected requirements, data and recoverable history. Reverify dependent behavior rather than preserving bad code through patches.
- Use `delivery-harness/references/delivery-acceptance-contract.md` for isolated synthetic accounts, separate mock/real-auth tests and per-platform evidence. Never use production data or a test login bypass in production.
- Bound repair attempts; retain unresolved PRD/TEST gaps for the next round. Ending a round is not a delivery PASS, a descoped requirement, or authorization to launch another task.

### Keep It Simple (KISS / YAGNI)

- Only do what's asked. No unrequested features, fallbacks, or "future-proof" abstractions.
- Prefer the simplest thing that works. Don't over-engineer.
- Don't "improve" code you weren't asked to touch.

### First Principles

- Reason from the problem's actual constraints, not from habit, inherited patterns, or how another project solved it.
- When a decision is non-obvious, derive it from what the product must do, then choose the simplest structure that satisfies it.

### File Size Checkpoint

- At 500 lines, review whether the module has more than one responsibility. Split when it improves ownership and verification; otherwise record why it stays together. This is a checkpoint, not a hard limit or permission to add tasks.
- Choose a bounded repair or replacement from the failing requirement and regression evidence. Preserve required compatibility, data and unrelated work; never delete and rewrite a module merely because it is problematic.

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
- For `none`, preserve all UI sources. For `structure` or `both`, update affected PRD behavior through `product-definition-builder`, then update `ui-design.md` and `wireframes.html` through `ui-design-builder` and rerun their gates. For `style` or `both`, rerun Style Integration, Impeccable review, H1-H9 grading, and Visual Approval or record the owner's decision to retain the existing direction. Update the design-system pair only when the approved change requires it.
- Preserve unaffected requirements, IDs, pages, wireframes, and design decisions. A direct task may stay small, but it is not complete while implementation and the canonical product documents disagree.

## Monetization And Partner Channels

When pricing, paid access, purchase-gated features or outside sellers apply, read `delivery-harness/references/project-operating-rules.md#monetization-and-partner-channels` in full. These rules are mandatory only for that route; they grant no actions.

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
- Harness 0.38 RUNs close `local_only` and keep their push grant false. After archival, a separately authorized checkout-external request/attempt/receipt may publish exact archive candidate A to the run branch. It never authorizes `main` or `development`.
- Follow `delivery-harness/references/branch-promotion-contract.md`: verify A and any isolated non-production deployment, then separately authorize and fast-forward exact A to `main`. Never force-push; stop on drift or divergence.
- Preserve unrelated dirty files, branches, and worktrees. Cleanup, worktree removal, task archival, and branch deletion require their own exact authorization.

## Deployment

- Resolve this section from the live project before finishing bootstrap; keep it only when the repository deploys, per the Product Delivery Harness `deployment-contract.md`.
- Platform and mode: the deploy platform id (for example `cloudflare`, `vercel`, `aws`) and `git_connected`, `ci_connected`, or `manual`.
- Non-production deploys from the exact candidate run branch or immutable candidate SHA; production deploys from `main`. Candidate and production environments remain separate, and a candidate PASS never proves production.
- Hosted-browser production uses `parity_capture.py` at the production URL. Browser-extension, native, and desktop targets use their platform automation or labeled manual captures and never substitute URL parity. Bind every result to the exact production SHA and artifact.
- Production and preview bind fully separate D1/KV/R2/Durable-Object resources: the preview environment declares its complete binding set, never references a production resource ID, and the deployment record's Resource Isolation table carries both ID sets.
- Before a deployable push, reconcile `docs/DEPLOYMENT.md` against tracked environment declarations, platform config, CI workflows, and auth/integration code. List exact secret and variable names, preview/production placement, source owner, and external-console tasks; never read or record secret values. After deployment, update only from read-only evidence and report every pending human action.
- Preview mechanism or URL pattern: <fill>
- Production URL: <fill>
- Deployed-commit check (platform API/CLI command or response header): <fill>
- Protected resources preview must never bind: <databases, buckets, secrets, domains>

## Post-Delivery Activation

Before post-delivery setup, external activation actions or readiness claims, read `delivery-harness/references/project-operating-rules.md#post-delivery-activation` in full. These rules are mandatory only for that route; they grant no actions.

## Managed Product Delivery Harness Runs

Before creating or resuming a managed PLAN/RUN, read `delivery-harness/references/project-operating-rules.md#managed-product-delivery-harness-runs` in full. These rules are mandatory only for that route; they grant no actions.

## Review Guidelines

Treat authorization bypasses, direct edits or commits on protected branches, unverified or non-fast-forward promotion, stale review SHAs, data loss, scope escapes, missing behavior verification, and work that skipped the Required Reading rules as blocking findings. Do not report style preferences as blockers.

## Completion

Update affected live PRD, architecture, design and operational sources under existing authority. Preserve untouched pages, IDs, decisions and historical evidence. Report actual SHA/build, checks, independent review, release/installation state and unresolved obligations. Required failures, stale evidence or skipped checks prevent a complete delivery claim.

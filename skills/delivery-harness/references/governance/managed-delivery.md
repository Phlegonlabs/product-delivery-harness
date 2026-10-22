# Managed And Consumer Delivery

These rules own consumer protected-branch routing, managed-run entry, review boundaries, and conditional operating routes. They do not create a RUN or grant any action.

## Git Safety

- Before every authorized commit, read `delivery-harness/references/commit-convention.md`. Direct tasks use `<type>(<scope>): <imperative summary>`; managed task and mission trailers apply only inside managed runs.
- Managed Harness requires the default branch to be named `main`; archive and promotion tooling binds only `main` refs. Confirm the name from repository state at bootstrap. If it differs, stop before managed work and ask the owner.
- `main` is the persistent protected production branch. New `main-preview/1` work needs no permanent development branch. Preserve historical pins and existing protected branches.
- Resolve the complete non-default run-branch name from repository governance or the user's instruction. Freeze the matching observed remote head in PLAN `branch_policy`: `main` for both ordinary work and hotfixes. Cut both `initial_delivery` and `enhancement` run branches from that frozen head. If the kind or name is unresolved, ask; never add a fixed prefix or invent a name.
- Harness 0.38+ RUNs close `local_only` and keep their push grant false. After archival, a separately authorized checkout-external request/attempt/receipt may publish exact archive candidate A to the run branch. It never authorizes `main` or `development`.
- Follow `delivery-harness/references/branch-promotion-contract.md`: verify A and its applicable isolated PR/branch Preview. Then separately authorize exact-SHA promotion to protected `main` and verify production. Never force-push; stop on drift or divergence.
- Preserve unrelated dirty files, branches, and worktrees. Cleanup, worktree removal, task archival, and branch deletion require their own exact authorization.

## Managed Product Delivery Harness Runs

Before creating or resuming a managed PLAN/RUN, read `delivery-harness/references/project-operating-rules.md#managed-product-delivery-harness-runs` in full. These rules are mandatory only for that route; they grant no actions.

## Review Guidelines

Treat authorization bypasses, direct edits or commits on protected branches, unverified or non-fast-forward promotion, stale review SHAs, data loss, scope escapes, missing behavior verification, and work that skipped the Required Reading rules as blocking findings. Do not report style preferences as blockers.

# Cloudflare Deployment Lifecycle

Use this reference when a deployable application targets Cloudflare. The default release shape is one repository and one codebase deployed to two isolated Workers:

```text
current PR head -> development Worker -> deployed-environment E2E
merged main SHA -> production Worker -> production smoke
```

`development` and `production` are Cloudflare environments. `main` is the Git base branch, not an environment name. Do not add a long-lived `development` branch unless the repository already uses one or the user explicitly chooses that branching model.

## Static Release Contract

New Cloudflare release PLAN files use schema v4 and define `release.provider: cloudflare` with exactly two targets. Existing schema-v3 release plans remain readable. Non-Cloudflare or non-deployable plans omit `release` instead of inheriting Cloudflare behavior:

- `development` uses `source: pr_head`, a `development` Wrangler environment, an isolated non-production Worker, sandbox payment credentials when payment applies, development auth configuration, and non-production storage.
- `production` uses `source: merged_main`, a `production` Wrangler environment, the production Worker, live payment credentials when payment applies, production auth configuration, and production storage.

Each target declares its Worker name, repository-relative Wrangler config path, migration command or explicit `null`, deployment command, prerequisites, and deployed-environment smoke verifiers. Never store secret values, Cloudflare API tokens, private keys, customer data, or copied production credentials in PLAN or RUN.

Use the repository's Wrangler config as the application deployment source of truth. Define environment-specific bindings explicitly; do not assume D1, KV, R2, Durable Objects, queues, service bindings, vars, or secrets inherit safely between environments. Keep payment mode, auth clients and redirect URLs, cookie scope, databases, buckets, queues, and third-party webhook endpoints isolated.

## Wrangler Config and Account Bootstrap

Both of these are one-time prerequisites, not part of every deploy attempt. Complete them before the first Cloudflare deploy for a product, and re-check the account gate before every later deploy attempt.

**Config scaffolding.** When a PLAN declares `release.provider: cloudflare` and a target's `wrangler_config_path` does not yet exist in the repository, generate `wrangler.jsonc` before attempting any deploy. Verify the current Wrangler config schema against official documentation first; do not rely on a memorized or stale schema, since Cloudflare's config format changes. Generate a config containing `name`, `compatibility_date` (from current docs, not memory), the application's entry point, and per-environment sections for `development` and `production` that use the exact `worker_name` and `wrangler_environment` values already recorded in the PLAN's `release.targets` — never invent different names than what the PLAN declares. Declare bindings (D1, KV, R2, Durable Objects, queues, vars, secrets) explicitly per environment; never let a binding default to being shared between development and production.

**Account verification gate.** Before attempting any Cloudflare deploy command — development or production, whether a local `wrangler deploy` or the dispatched GitHub Actions workflow — confirm Cloudflare account access is actually available:

- GitHub Actions path (`assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml`): confirm `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` are configured as secrets on the `cloudflare-development`/`cloudflare-production` GitHub Environments the workflow dispatches against (`environment: cloudflare-${{ inputs.target_environment }}`).
- Local/manual deploy path: confirm an authenticated Wrangler session exists (for example, `wrangler whoami` succeeds).

If neither can be confirmed, stop — do not attempt the deploy — and tell the user exactly what is missing and how to fix it (run `wrangler login` locally, or add the two secrets to the named GitHub Environments). Never ask the user to paste a token or secret value into chat, and never write one into PLAN, RUN, workflow files, or any committed file; direct them to set it via the Cloudflare dashboard, `wrangler login`, or the GitHub repository/environment secrets UI themselves.

## Live Deployment State

Every new schema-v4 PLAN that declares a release uses a schema-v9 RUN with `deployments`; existing schema-v4/schema-v8 and schema-v3/schema-v7 pairs remain readable. A RUN without a release PLAN omits `deployments`. `deployments.development` and `deployments.production` record:

```text
status
source_sha
worker_name
url
version_id
migration_status
verification_status
rollback_version when available
retained evidence
```

Development reaches `PASS` only when current-head CI passed for the exact PR head, the same SHA was deployed to the development Worker, migration is `PASS` or `not_required`, and the declared development E2E/smoke checks pass against the deployed URL.

Production reaches `PASS` only after development passes, GitHub reports the PR merged, the production source equals `landing.merged_sha`, migration is `PASS` or `not_required`, and production smoke passes. Squash merge creates a different commit SHA from the PR head, so preserve both the development PR-head SHA and the merged production SHA instead of claiming they are identical.

## Authorization And Triggering

Deployment remains separate from push, PR merge, and repository configuration. At Plan Readiness, when the user requested full deployed delivery, ask once for the exact deployment targets together with the other missing actions, then record deployment under the existing `deploy` ledger entry:

```text
environment:development
environment:production
```

One explicit user statement may authorize both targets, but neither is inferred from push or merge. `configure_repository` separately covers installing or changing GitHub workflows, environments, branch rules, and repository settings.

Use `assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml` as the default deployment workflow. It is explicitly dispatched with the target environment and exact source SHA after the parent verifies RUN authorization and gates. Do not make arbitrary feature-branch pushes or every `main` push an unconditional deployment path, because that would turn push authorization into implicit deploy authorization.

## Pre-Deploy Confirmation Checkpoint

The `deploy:production` ledger authorization granted at Plan Readiness lets the landing-and-deploy loop run without pausing for a second authorization. It does not license firing the production deploy blindly. Before the parent actually runs the production deploy command, verify two things and surface them to the user. This is a confirmation/notification checkpoint at the moment of execution, not a new ledger action — do not add a field to RUN or change any schema for it.

**Deploying SHA drift.** Record the SHA that was the current head when `deploy:production` was authorized. Before the production deploy fires, compare it to the SHA about to be deployed. If they differ — because review-repair, a new push, or re-integration changed the head since authorization — stop and ask for a fresh, explicit confirmation naming the new SHA. The old authorization covered the code the user saw when they granted it; do not silently ship a different SHA under it.

**Migration destructiveness.** Before running any migration as part of the production deploy, classify it:

- Additive — new column, table, or index with safe defaults and no possible data loss. This rides the general `deploy:production` authorization.
- Potentially destructive — column or table drop, type narrowing, a `NOT NULL` added to existing data, or any data transformation that cannot be trivially reversed. This needs its own explicit confirmation, separate from `deploy:production`. Do not let it ride through on the same blanket authorization as a routine additive migration. Name the exact destructive operation when asking, and confirm the rollback/backup plan is ready first.

If either check trips, stop and ask before proceeding. If both are clean — same SHA, additive-or-no migration — proceed under the existing authorization without a redundant prompt.

## Migration And Data Rules

Apply migrations in dependency order and use backward-compatible schema changes when old and new Worker versions can overlap. Development migration and reset/seed checks run only against development resources. Production migration runs only after the production deployment gate is authorized and its rollback/compatibility plan is ready.

For applications with payment, authentication, entitlements, or customer data:

- Development uses payment sandbox/test mode and production uses live mode.
- Development and production use distinct auth applications or clients, redirect URLs, webhook endpoints, and host-only cookie scopes.
- Development never reads or writes the production database. Use synthetic or explicitly approved sanitized data when realistic fixtures are needed.
- Durable Object namespaces and other stateful bindings remain environment-specific. Do not rely on Worker version preview URLs as a substitute for an isolated development Worker.

## Verification And Failure Rules

Retain the deployment URL, Cloudflare version/deployment identifier, source SHA, migration output, and smoke/E2E evidence. A successful Wrangler command alone is not the development or production PASS signal.

On failure:

- Stop promotion to production when development deploy, migration, or deployed-environment verification fails.
- Do not mark production PASS when its smoke test fails, even if the upload succeeded.
- Record the last known rollback version when Cloudflare exposes one; do not invent it for a first deployment.
- Treat any new PR push as stale development evidence and redeploy/reverify the new current head.
- Treat any change to merged `main` as stale production evidence until that exact SHA is deployed and smoked.

Recheck current official Cloudflare documentation and the installed Wrangler config schema before using fast-moving configuration fields or command options:

- https://developers.cloudflare.com/workers/wrangler/environments/
- https://developers.cloudflare.com/workers/wrangler/configuration/
- https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/
- https://developers.cloudflare.com/workers/versions-and-deployments/
- https://developers.cloudflare.com/d1/reference/migrations/

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
- https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/
- https://developers.cloudflare.com/workers/versions-and-deployments/
- https://developers.cloudflare.com/d1/reference/migrations/

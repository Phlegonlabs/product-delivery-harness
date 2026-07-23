# Cloudflare Deployment Lifecycle

Use this reference when a deployable application targets Cloudflare. The default release shape is one repository and one codebase deployed to two isolated Workers:

```text
current PR head -> development Worker -> deployed-environment E2E
merged main SHA -> production Worker -> production smoke
```

`development` and `production` are Cloudflare environments. `main` is the Git base branch, not an environment name. Do not add a long-lived `development` branch unless the repository already uses one or the user explicitly chooses that branching model.

## Static Release Contract

New Cloudflare release PLAN files use schema v4 and define `release.provider: cloudflare` with exactly two targets. Existing schema-v3 release plans remain readable. Non-Cloudflare or non-deployable plans omit `release` instead of inheriting Cloudflare behavior:

- `development` uses `source: pr_head`, a `development` Wrangler environment, an isolated non-production Worker, sandbox payment credentials when payment applies, development auth configuration, and non-production storage. Its `source` may instead be `integration_head` when the repository uses Cloudflare's native Git auto-deploy — see "Auto-Deploy Release Model (Alternative Trigger)" below.
- `production` uses `source: merged_main`, a `production` Wrangler environment, the production Worker, live payment credentials when payment applies, production auth configuration, and production storage.

Each target declares its Worker name, repository-relative Wrangler config path, migration command or explicit `null`, deployment command, prerequisites, and deployed-environment smoke verifiers. Never store secret values, Cloudflare API tokens, private keys, customer data, or copied production credentials in PLAN or RUN.

Use the repository's Wrangler config as the application deployment source of truth. Define environment-specific bindings explicitly; do not assume D1, KV, R2, Durable Objects, queues, service bindings, vars, or secrets inherit safely between environments. Keep payment mode, auth clients and redirect URLs, cookie scope, databases, buckets, queues, and third-party webhook endpoints isolated.

## Wrangler Config and Account Bootstrap

Both of these are one-time prerequisites, not part of every deploy attempt. Complete them before the first Cloudflare deploy for a product, and re-check the account gate before every later deploy attempt.

**Config scaffolding.** When a PLAN declares `release.provider: cloudflare` and a target's `wrangler_config_path` does not yet exist in the repository, generate `wrangler.jsonc` before attempting any deploy. Verify the current Wrangler config schema against official documentation first; do not rely on a memorized or stale schema, since Cloudflare's config format changes. Generate a config containing `name`, `compatibility_date` (from current docs, not memory), the application's entry point, and per-environment sections for `development` and `production` that use the exact `worker_name` and `wrangler_environment` values already recorded in the PLAN's `release.targets` — never invent different names than what the PLAN declares. Declare bindings (D1, KV, R2, Durable Objects, queues, vars, secrets) explicitly per environment; never let a binding default to being shared between development and production.

After scaffolding or changing `wrangler.jsonc`, and before the first deploy attempt, run `scripts/check_wrangler_binding_isolation.py --wrangler-config <path>` to catch a scaffolded config that reuses the same D1/KV/R2/queue/Durable Object resource identity between `development` and `production`. Treat any reported collision as a blocking Stop-And-Ask condition: report the exact binding and shared identity value to the user and ask which environment should keep the real resource, instead of silently guessing and picking one.

**Account verification gate.** Before attempting any Cloudflare deploy command — development or production, whether a local `wrangler deploy` or the dispatched GitHub Actions workflow — confirm Cloudflare account access is actually available:

- GitHub Actions path (`assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml`): confirm `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` are configured as secrets on the `cloudflare-development`/`cloudflare-production` GitHub Environments the workflow dispatches against (`environment: cloudflare-${{ inputs.target_environment }}`).
- Local/manual deploy path: confirm an authenticated Wrangler session exists (for example, `wrangler whoami` succeeds).

If neither can be confirmed, stop — do not attempt the deploy — and tell the user exactly what is missing and how to fix it (run `wrangler login` locally, or add the two secrets to the named GitHub Environments). Never ask the user to paste a token or secret value into chat, and never write one into PLAN, RUN, workflow files, or any committed file; direct them to set it via the Cloudflare dashboard, `wrangler login`, or the GitHub repository/environment secrets UI themselves.

**Day one resource creation.** Once the config and account gates above pass, create the concrete Cloudflare resources a settled architecture already confirms it needs — do not provision a binding speculatively for a hypothetical future need. For each confirmed D1 database, KV namespace, R2 bucket, Durable Object namespace, or queue, create one isolated instance per environment (for example `wrangler d1 create <name>-development` and `wrangler d1 create <name>-production`) before wiring their IDs into `wrangler.jsonc`'s per-environment sections — isolated bindings cannot be declared correctly until both resources actually exist and have their own IDs. Then create both Worker shells with an initial no-op `wrangler deploy --env development` and `wrangler deploy --env production` so they exist in the Cloudflare dashboard. Doing this at bootstrap, rather than deferring it to the first authorized feature deploy, is what lets `check_wrangler_binding_isolation.py` validate real isolated IDs immediately and lets the user wire up dashboard-level configuration (custom domains, environment variables) without waiting. This creates empty resources and Worker shells only; it authorizes nothing about deploying real feature code — that still requires the `deploy:development`/`deploy:production` ledger entries and, for production, the Pre-Deploy Confirmation Checkpoint below, exactly as before. Record the real Worker names, resource IDs, and dashboard configuration this step produces in `doc/deployment.md` (scaffolded from `assets/templates/PROJECT_CLOUDFLARE_DEPLOYMENT_GUIDE.template.md`) so a future maintainer has an operational reference, not just the machine-readable `RUN.md` state.

## Live Deployment State

Every new schema-v4 PLAN that declares a release uses a schema-v9 RUN with `deployments`; existing schema-v4/schema-v8 and schema-v3/schema-v7 pairs remain readable. A RUN without a release PLAN omits `deployments`. `deployments.development` and `deployments.production` record:

```text
status
source_sha
authorized_head_sha when recorded
worker_name
url
version_id
migration_status
migration_classification when recorded
destructive_migration_confirmed_sha when recorded
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

## Auto-Deploy Release Model (Alternative Trigger)

This is an explicit alternative to the default dispatched-GitHub-Actions model in "Authorization And Triggering" above. Choose it only when the user explicitly wants Cloudflare's own native Git integration (Workers Builds) to auto-deploy on push instead of harness-dispatched deploys. Do not default to this model; the dispatched-Actions model above remains the default.

**Branch and Worker topology.** Connect the repository directly to Cloudflare Workers Builds using two separate Cloudflare Worker resources, each independently connected via Cloudflare's Git integration to the *same* repository:

- The **development** Worker watches the harness's own integration branch (`run.integration.branch` — the long-lived branch where mission work lands before promotion; the user may name this branch literally `development`). Its Cloudflare "Deploy command" is `wrangler deploy --env development`.
- The **production** Worker watches `main` (the harness's `landing.base_branch`). Its Cloudflare "Deploy command" is `wrangler deploy --env production`.
- Both Workers, and any confirmed D1/KV/R2/Durable Object/queue bindings they need, should already exist per this doc's "Day one resource creation" step above (in "Wrangler Config and Account Bootstrap") before wiring up their Git connections — creating them at that point, rather than only now, avoids a second isolation check later and means the per-environment binding IDs are already correct in `wrangler.jsonc` before Cloudflare starts auto-deploying on every push. Then connect the same repository separately to each Worker — each with its own branch-to-listen-to setting and its own deploy command, per Cloudflare's own advanced-setup guidance.
- Declare `run.integration.retention: "persistent"` for this model, since the development Worker's Cloudflare Git connection depends on this branch surviving across runs rather than being recreated and deleted each time. See `MISSION_RUNBOOK.template.md`'s integration-branch-creation paragraph for the exact mechanics of how a persistent branch is reused as a run's starting base instead of created fresh.
- `assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml` is NOT used in this model at all. That template belongs only to the default dispatched-Actions model. Do not wire up both at once.

Cloudflare's own mechanism has no approval or review gate: pushing to a Worker's configured branch runs that Worker's Deploy command immediately and automatically. (Pushing to any *other* branch instead runs Cloudflare's "Non-production branch deploy command", default `wrangler versions upload`, which uploads a version without promoting it live.) See:

- https://developers.cloudflare.com/workers/ci-cd/builds/configuration/
- https://developers.cloudflare.com/workers/ci-cd/builds/advanced-setups/

**Release-target `source` value.** Under this model, the development release target's `source` may be `integration_head` (in addition to the existing `pr_head`), chosen at PLAN-authoring time to declare that this alternative model is in use. When `source: integration_head`, `deployments.development`'s PASS binds to `run.integration.integration_head_sha` (the harness's already-tracked, live-Git-cross-checked integration branch head) instead of to any PR field. There is no per-PR development deploy in this model, since Cloudflare deploys continuously on every push to the integration branch regardless of whether a PR against `main` is even open yet. Production's `source` stays `merged_main` unchanged — that part of the contract does not change between the two models.

**No pause point — the checkpoint moves to the merge, not the deploy.** Because Cloudflare's infrastructure fires the deploy automatically and immediately on push, the harness cannot intercept "the moment before the deploy command runs" the way it does in the dispatched model — there is no separate deploy command for the harness to gate. The control point the harness DOES still fully own is **merging/pushing the integration branch into `main`** (an `integrate_locally`/`merge_pr`/`push`-authorized action already gated by the existing authorization ledger), since that merge is what triggers the production Worker's auto-deploy almost immediately afterward. Therefore, in this model, run the "Pre-Deploy Confirmation Checkpoint" below (SHA-drift comparison and migration-destructiveness classification) **immediately before the harness merges/pushes the integration branch into `main`**, not before a separate deploy command — in this model that merge IS effectively the production deploy trigger.

**Substitute boundary for out-of-band merges.** The harness's own pre-merge checkpoint only fires when the harness itself performs the merge. To guard against someone bypassing the harness and merging the integration branch into `main` directly, recommend the user enable GitHub branch protection on `main` (require a pull request, require review, disallow direct pushes). This is good practice regardless of which release trigger model is chosen, but it is the ONLY remaining safety boundary against an out-of-band production deploy in this alternative model, since Cloudflare's own auto-deploy has no approval gate of its own.

## Pre-Deploy Confirmation Checkpoint

The `deploy:production` ledger authorization granted at Plan Readiness lets the landing-and-deploy loop run without pausing for a second authorization. It does not license firing the production deploy blindly. Before the parent actually runs the production deploy command, verify two things and surface them to the user. This is a confirmation/notification checkpoint at the moment of execution, not a new ledger action. Under the default dispatched model this checkpoint runs right before the production deploy command fires; under the "Auto-Deploy Release Model (Alternative Trigger)" above it runs right before the harness merges the integration branch into `main` instead — same checks, different trigger moment, per that section.

**Deploying SHA drift.** At the moment `deploy:production` is authorized (Plan Readiness), record the current integration head SHA into `deployments.production.authorized_head_sha`. Before the production deploy fires, compare that recorded value against the live SHA about to be deployed. If they differ — because review-repair, a new push, or re-integration changed the head since authorization — stop and ask for a fresh, explicit confirmation naming the new SHA, and update `authorized_head_sha` to match. The old authorization covered the code the user saw when they granted it; do not silently ship a different SHA under it.

**Migration destructiveness.** Before running any migration as part of the production deploy, classify it:

- Additive — new column, table, or index with safe defaults and no possible data loss. This rides the general `deploy:production` authorization. Record the classification as `deployments.production.migration_classification: "additive"`.
- Potentially destructive — column or table drop, type narrowing, a `NOT NULL` added to existing data, or any data transformation that cannot be trivially reversed. This needs its own explicit confirmation, separate from `deploy:production`. Do not let it ride through on the same blanket authorization as a routine additive migration. Name the exact destructive operation when asking, and confirm the rollback/backup plan is ready first. Record the classification as `deployments.production.migration_classification: "destructive"` and, once the separate confirmation is obtained, the exact SHA it was obtained at in `deployments.production.destructive_migration_confirmed_sha` — so the decision is auditable after the fact rather than only decided informally in conversation.

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

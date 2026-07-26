# Cloudflare Deployment Lifecycle

Use this reference when a deployable application targets Cloudflare. The default release shape is one repository and one codebase deployed to two isolated Workers:

```text
reviewed development head -> development Worker -> deployed-environment E2E
user-approved development -> production promotion
production head -> production Worker -> production smoke
```

`development` and `production` are both Git branches and isolated Cloudflare environments in the target repository's standard model. Mission worktrees start from and merge back into the persistent `development` branch after exact-head review. The `production` branch changes only through a later user-approved promotion from `development`.

## Static Release Contract

New Cloudflare release PLAN files use PLAN schema v5 and the same provider-neutral target shape as every other release. Use stable target IDs such as `web-development` and `web-production`; do not add provider-specific PLAN keys. Existing older release schemas remain readable. Non-deployable plans omit `release`.

- The development target uses `stage: development`, `source: integration_head`, `data_mode: isolated_non_production`, and a manual or merge trigger chosen at plan time.
- The production target uses `stage: production`, `source: production_head`, `data_mode: production`, and a manual or merge trigger chosen at plan time. `merged_main` remains readable only in older plans.

Every target contains exactly `id`, `stage`, `source`, `artifact_kind`, `requires_signing`, `channel`, `data_mode`, `trigger`, `migration_classification`, `commands`, `prerequisites`, and `smoke_verifiers`. `commands` contains `build`, `migrate`, and `publish`; a manual target requires a publish command, while a merge-triggered target records `publish: null`. A null `migration_classification` is unresolved and blocks execution. Never store secrets, tokens, private keys, customer data, or copied production credentials in PLAN or RUN.

Keep Cloudflare identity and isolation in the repository's Wrangler config, `docs/deployment.md`, target prerequisites, and retained RUN evidence. Record the exact Worker name, Wrangler environment/config path, account/project identity, and isolated D1, KV, R2, Durable Object, queue, secret, auth, payment, and webhook configuration there. Do not put those provider-specific fields in the PLAN-v5 target object.

## Wrangler Config and Account Bootstrap

These are one-time prerequisites, not part of every deploy attempt. Complete them before the first Cloudflare deploy for a product, and re-check the account gate before every later deploy attempt.

**Config scaffolding.** When a PLAN target's Cloudflare prerequisites identify a Wrangler config that does not yet exist, generate `wrangler.jsonc` before attempting any deploy. Verify the current Wrangler config schema against official documentation first; do not rely on memory. Generate a config containing `name`, a current `compatibility_date`, the application entry point, and explicit `development` and `production` environments. The exact Worker names, Wrangler environment names, and config path come from the approved project deployment guide and target prerequisites, not extra PLAN-v5 keys. Declare bindings explicitly per environment; never let a binding default to being shared between development and production.

After scaffolding or changing `wrangler.jsonc`, and before the first deploy attempt, run `scripts/check_wrangler_binding_isolation.py --wrangler-config <path>` to catch a scaffolded config that reuses the same D1/KV/R2/queue/Durable Object resource identity between `development` and `production`. Treat any reported collision as a blocking Stop-And-Ask condition: report the exact binding and shared identity value to the user and ask which environment should keep the real resource, instead of silently guessing and picking one.

**Account verification gate.** Before attempting any Cloudflare deploy command — development or production, whether a local `wrangler deploy` or the dispatched GitHub Actions workflow — confirm Cloudflare account access is actually available:

- GitHub Actions path (`assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml`): confirm `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` are configured as secrets on the `cloudflare-development`/`cloudflare-production` GitHub Environments the workflow dispatches against (`environment: cloudflare-${{ inputs.target_environment }}`).
- Local/manual deploy path: confirm an authenticated Wrangler session exists (for example, `wrangler whoami` succeeds).

If neither can be confirmed, stop — do not attempt the deploy — and tell the user exactly what is missing and how to fix it (run `wrangler login` locally, or add the two secrets to the named GitHub Environments). Never ask the user to paste a token or secret value into chat, and never write one into PLAN, RUN, workflow files, or any committed file; direct them to set it via the Cloudflare dashboard, `wrangler login`, or the GitHub repository/environment secrets UI themselves.

**Day one resource creation.** Once the config and account gates pass, create only the concrete resources a settled architecture requires. Each creation requires `provision_cloud_resources` authorization with an exact `cloud-resource:<provider>:<environment>:<kind>:<logical-name>` target. Create distinct D1, KV, R2, Durable Object, or queue instances per environment before wiring IDs into Wrangler. Creating Worker shells or publishing code also requires `deploy` authorization for the exact `release:<target-id>` and authorized head; provisioning permission never implies deploy permission. Run the isolation check after real IDs are present. Record Worker names, resource IDs, config paths, and dashboard settings in `docs/deployment.md` so the provider details remain operationally visible without changing the provider-neutral PLAN target.

## Live Deployment State

Every new PLAN-v5 release uses RUN schema v10 `targets`, keyed exactly by the PLAN target IDs. A RUN without PLAN release targets has no target entries. Each target retains status, exact `source_sha`, exact `authorized_head_sha`, artifact/build/version/signing proof, channel and promotion proof, availability proof, migration and verification status, destructive-migration confirmation when needed, and hashed evidence references. Cloudflare Worker names, URLs, deployment IDs, rollback versions, and resource IDs belong inside those retained references or the project deployment guide, not as replacement target keys.

Development reaches `PASS` only when the declared source SHA was deployed to the isolated development Worker, migration is `PASS` or `not_required`, and the declared deployed-environment checks pass against that exact deployment.

Production reaches `PASS` only after applicable prerequisite targets pass, GitHub reports the PR merged, `targets[production-id].source_sha` equals `landing.merged_sha`, migration is `PASS` or `not_required`, and production smoke passes. The authorized candidate head and the resulting merged source SHA are distinct facts: a squash merge normally creates a new merged SHA. Preserve the authorized PR/integration head in authorization and landing evidence, then bind production publication to the resulting merged source SHA.

## Authorization And Triggering

Deployment remains separate from push, PR merge, remote workflow triggering, cloud-resource provisioning, and repository configuration. Development deploy authorization may be requested with ordinary work. Production deploy and promotion actions wait for the user's separate final approval to start `development -> production`. `deploy` uses `release:<target-id>`. Dispatching remote CI additionally uses `trigger_remote_ci` with `workflow:<identity>`. Installing or changing the workflow uses `configure_repository`; creating provider resources uses `provision_cloud_resources` with exact cloud-resource targets.

One explicit user statement may authorize several exact targets, but no action is inferred from another. For a native merge-triggered publication, require independent exact `merge_pr` and `deploy` grants, bound to the same PLAN revision/digest, candidate head, and `release:<target-id>`. The merge grant authorizes landing the candidate head. The deploy grant authorizes the publication consequence. After merge, observe and retain the resulting merged source SHA separately.

Use `assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml` for a manual target. Dispatch it with the exact source SHA only after the parent verifies the exact workflow and release grants. Do not make arbitrary pushes an unconditional publication path.

## Auto-Deploy Release Model (Alternative Trigger)

This is an explicit alternative to the default dispatched-GitHub-Actions model in "Authorization And Triggering" above. Choose it only when the user explicitly wants Cloudflare's own native Git integration (Workers Builds) to auto-deploy on push instead of harness-dispatched deploys. Do not default to this model; the dispatched-Actions model above remains the default.

**Branch and Worker topology.** This model uses persistent `development` for `run.integration.branch` and protected `production` for `landing.base_branch`. Mission work lands on `development` only after worktree review. Promoting `development` into `production`, which triggers the production Worker, is a separate later action that starts only after final user approval. Connect the repository directly to Cloudflare Workers Builds using two separate Cloudflare Worker resources, each independently connected via Cloudflare's Git integration to the same repository:

- The **development** Worker watches `development`. Its Cloudflare "Deploy command" is `wrangler deploy --env development`.
- The **production** Worker watches `production`. Its Cloudflare "Deploy command" is `wrangler deploy --env production`.
- Both Workers, and any confirmed D1/KV/R2/Durable Object/queue bindings they need, should already exist per this doc's "Day one resource creation" step above (in "Wrangler Config and Account Bootstrap") before wiring up their Git connections — creating them at that point, rather than only now, avoids a second isolation check later and means the per-environment binding IDs are already correct in `wrangler.jsonc` before Cloudflare starts auto-deploying on every push. Then connect the same repository separately to each Worker — each with its own branch-to-listen-to setting and its own deploy command, per Cloudflare's own advanced-setup guidance.
- Both persistent branches must exist before wiring the Workers' Git connections. If either is missing, report it and obtain exact branch-creation authorization; do not create it implicitly.
- Declare `run.integration.retention: "persistent"` for this model, since the development Worker's Cloudflare Git connection depends on this branch surviving across runs rather than being recreated and deleted each time. This is enforced, not just a reminder: `validate_harness_plan.py` rejects a `development` release target whose `source` is `integration_head` unless `run.integration.retention` is exactly `"persistent"`. See `MISSION_RUNBOOK.template.md`'s integration-branch-creation paragraph for the exact mechanics of how a persistent branch is reused as a run's starting base instead of created fresh.
- `assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml` is NOT used in this model at all. That template belongs only to the default dispatched-Actions model. Do not wire up both at once.

Cloudflare's own mechanism has no approval or review gate: pushing to a Worker's configured branch runs that Worker's Deploy command immediately and automatically. (Pushing to any *other* branch instead runs Cloudflare's "Non-production branch deploy command", default `wrangler versions upload`, which uploads a version without promoting it live.) See:

- https://developers.cloudflare.com/workers/ci-cd/builds/configuration/
- https://developers.cloudflare.com/workers/ci-cd/builds/advanced-setups/

**Release-target `source` value.** The development release target uses `integration_head`, binding PASS to the live-Git-cross-checked `development` head in `run.integration.integration_head_sha`. Production uses `production_head`, which binds to `landing.merged_sha` after the approved `development -> production` promotion.

**No pause point — the checkpoint moves to the promotion merge.** Because Cloudflare deploys automatically on branch changes, the harness gates the exact `development -> production` merge. Run the Pre-Deploy Confirmation Checkpoint immediately before that approved merge because it is effectively the production deploy trigger.

**Substitute boundary for out-of-band merges.** Protect `production`: require a pull request and review, and disallow direct pushes. This is the remaining safety boundary against an out-of-band production deploy because Cloudflare's own auto-deploy has no human approval gate.

## Pre-Deploy Confirmation Checkpoint

The final user approval starts production promotion; exact `merge_pr` and `deploy` authorizations still remain independent. Before the parent runs the production deploy command or performs the auto-deploy-triggering `development -> production` merge, verify the exact SHA and migration classification below.

**Deploying SHA drift.** At the final production-promotion approval checkpoint, record the current `development` head SHA into `targets[production-id].authorized_head_sha`. Before production promotion or deploy fires, compare that value against the live SHA about to be promoted. If they differ because review-repair, a new push, or re-integration changed the head, stop and ask for a fresh explicit confirmation naming the new SHA.

**Migration destructiveness.** Before running any migration as part of the production deploy, classify it:

- Additive — new column, table, or index with safe defaults and no possible data loss. This rides the exact production-target `deploy` authorization. Record the classification as the PLAN target's `migration_classification: "additive"`.
- Potentially destructive — column or table drop, type narrowing, a `NOT NULL` added to existing data, or any data transformation that cannot be trivially reversed. This needs its own explicit confirmation, separate from the target's ordinary `deploy` grant. Do not let it ride through on the same blanket authorization as a routine additive migration. Name the exact destructive operation when asking, and confirm the rollback/backup plan is ready first. Record the classification as the PLAN target's `migration_classification: "destructive"` and, once the separate confirmation is obtained, the exact SHA it was obtained at in `targets[production-id].destructive_migration_confirmed_sha` — so the decision is auditable after the fact rather than only decided informally in conversation.

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
- Treat any change to `production` as stale production evidence until that exact SHA is deployed and smoked.

Recheck current official Cloudflare documentation and the installed Wrangler config schema before using fast-moving configuration fields or command options:

- https://developers.cloudflare.com/workers/wrangler/environments/
- https://developers.cloudflare.com/workers/wrangler/configuration/
- https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/
- https://developers.cloudflare.com/workers/versions-and-deployments/
- https://developers.cloudflare.com/d1/reference/migrations/

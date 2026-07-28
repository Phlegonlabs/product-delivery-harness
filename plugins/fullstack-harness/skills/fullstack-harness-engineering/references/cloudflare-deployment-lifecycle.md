# Cloudflare Deployment Lifecycle

Use this reference when a deployable application targets Cloudflare. The default release shape is one repository and one codebase deployed to one production Worker:

```text
reviewed mission heads -> the run's own branch -> push (the run is complete)
user-started PR: run branch -> main -> current-head CI and review -> the human merges
main head -> production Worker -> production smoke
```

`production` is a Cloudflare environment, not a Git branch. `main` is the only persistent branch: mission worktrees start from the recorded current `main` SHA, integrate after exact-head review into the run's own `codex/<short-name>` branch, and reach `main` only through the user-started pull request a human merges. The production Worker builds from `main`.

A repository that genuinely keeps a preview or staging environment may additionally declare a `development` Cloudflare environment and a matching non-production release target. That is optional: the default model does not require one and PLAN validation does not demand one. Target-repository governance wins — when the repository's own instructions define a separate integration or protected landing branch, preserve those exact names and topology.

## Static Release Contract

New Cloudflare release PLAN files use PLAN schema v5 and the same provider-neutral target shape as every other release. Use the stable target IDs `architecture.md`'s `## Release Targets` section already declares; mint an ID such as `web-production` only when no such section exists. Do not add provider-specific PLAN keys. Existing older release schemas remain readable. Non-deployable plans omit `release`.

- The production target uses `stage: production`, `source: production_head`, `data_mode: production`, and a manual or merge trigger chosen at plan time. `merged_main` remains readable only in older plans. This is the only target the default model requires.
- An optional non-production target uses `stage: development`, `source: integration_head`, `data_mode: isolated_non_production`, and a manual or merge trigger chosen at plan time. Declare it only when the repository keeps a preview or staging environment, and mint the ID `web-development` when `architecture.md` names none.

Every target contains exactly `id`, `stage`, `source`, `artifact_kind`, `requires_signing`, `channel`, `data_mode`, `trigger`, `migration_classification`, `commands`, `prerequisites`, and `smoke_verifiers`. `commands` contains `build`, `migrate`, and `publish`; a manual target requires a publish command, while a merge-triggered target records `publish: null`. A null `migration_classification` is unresolved and blocks execution. Never store secrets, tokens, private keys, customer data, or copied production credentials in PLAN or RUN.

Keep Cloudflare identity and isolation in the repository's Wrangler config, `docs/deployment.md`, target prerequisites, and retained RUN evidence. Record the exact Worker name, Wrangler environment/config path, account/project identity, and isolated D1, KV, R2, Durable Object, queue, secret, auth, payment, and webhook configuration there. Do not put those provider-specific fields in the PLAN-v5 target object.

## Wrangler Config and Account Bootstrap

These are one-time prerequisites, not part of every deploy attempt. Complete them before the first Cloudflare deploy for a product, and re-check the account gate before every later deploy attempt.

**Config scaffolding.** When a PLAN target's Cloudflare prerequisites identify a Wrangler config that does not yet exist, generate `wrangler.jsonc` before attempting any deploy. Verify the current Wrangler config schema against official documentation first; do not rely on memory. Generate a config containing `name`, a current `compatibility_date`, the application entry point, and one explicit environment per declared release target — `production` always, plus `development` when the repository declares the optional preview target. The exact Worker names, Wrangler environment names, and config path come from the approved project deployment guide and target prerequisites, not extra PLAN-v5 keys. Declare bindings explicitly per environment; never let a binding default to being shared between development and production.

When the config declares both environments, run `scripts/check_wrangler_binding_isolation.py --wrangler-config <path>` after scaffolding or changing `wrangler.jsonc` and before the first deploy attempt, to catch a scaffolded config that reuses the same D1/KV/R2/queue/Durable Object resource identity between `development` and `production`. Treat any reported collision as a blocking Stop-And-Ask condition: report the exact binding and shared identity value to the user and ask which environment should keep the real resource, instead of silently guessing and picking one.

**Account verification gate.** Before attempting any Cloudflare deploy command — development or production, whether a local `wrangler deploy` or the dispatched GitHub Actions workflow — confirm Cloudflare account access is actually available:

- GitHub Actions path (`assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml`): confirm `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` are configured as secrets on the `cloudflare-development`/`cloudflare-production` GitHub Environments the workflow dispatches against (`environment: cloudflare-${{ inputs.target_environment }}`).
- Local/manual deploy path: confirm an authenticated Wrangler session exists (for example, `wrangler whoami` succeeds).

If neither can be confirmed, stop — do not attempt the deploy — and tell the user exactly what is missing and how to fix it (run `wrangler login` locally, or add the two secrets to the named GitHub Environments). Never ask the user to paste a token or secret value into chat, and never write one into PLAN, RUN, workflow files, or any committed file; direct them to set it via the Cloudflare dashboard, `wrangler login`, or the GitHub repository/environment secrets UI themselves.

**Day one resource creation.** Once the config and account gates pass, create only the concrete resources a settled architecture requires. Each creation requires `provision_cloud_resources` authorization with an exact `cloud-resource:<provider>:<environment>:<kind>:<logical-name>` target. Create distinct D1, KV, R2, Durable Object, or queue instances per environment before wiring IDs into Wrangler. Creating Worker shells or publishing code also requires `deploy` authorization for the exact `release:<target-id>` and authorized head; provisioning permission never implies deploy permission. Run the isolation check after real IDs are present. Record Worker names, resource IDs, config paths, and dashboard settings in `docs/deployment.md` so the provider details remain operationally visible without changing the provider-neutral PLAN target.

## Live Deployment State

Every new PLAN-v5 release uses RUN schema v10 `targets`, keyed exactly by the PLAN target IDs. A RUN without PLAN release targets has no target entries. Each target retains status, exact `source_sha`, exact `authorized_head_sha`, artifact/build/version/signing proof, channel and promotion proof, availability proof, migration and verification status, destructive-migration confirmation when needed, and hashed evidence references. Cloudflare Worker names, URLs, deployment IDs, rollback versions, and resource IDs belong inside those retained references or the project deployment guide, not as replacement target keys.

A declared non-production target reaches `PASS` only when its declared source SHA was deployed to the isolated development Worker, migration is `PASS` or `not_required`, and the declared deployed-environment checks pass against that exact deployment.

Production reaches `PASS` only after applicable prerequisite targets pass, GitHub reports the PR merged, `targets[production-id].source_sha` equals `landing.merged_sha`, migration is `PASS` or `not_required`, and production smoke passes. The authorized candidate head and the resulting merged source SHA are distinct facts: a squash merge normally creates a new merged SHA. Preserve the authorized PR/integration head in authorization and landing evidence, then bind production publication to the resulting merged source SHA.

## Authorization And Triggering

Deployment remains separate from push, PR merge, remote workflow triggering, cloud-resource provisioning, and repository configuration. No `deploy` — including an optional preview or staging target — ever rides the execution-intent instruction: each is its own authorization moment with an exact `release:<target-id>`. Landing on `main` and deploying from it wait for the user's separate instructions.

One rule covers who runs the production deploy, in both trigger models below:

- The harness runs the production deploy command when `deploy` is authorized for that exact production `release:<target-id>` at that exact head. That grant is never inferred from `merge_pr`, from the instruction that started landing, or from the development loop. In every new marked `action-targets/1` RUN-v10 artifact, it carries its own recorded `target_sources` entry (`execution-state-model.md`); the current RUN template is marked. An existing unmarked legacy RUN-v10 entry keeps historical validation only while it omits `target_sources`, and adding `target_sources` opts that entry into the same strict provenance rules.
- The merge into `main` is always the human's. The harness may open the landing PR, observe current-head CI, and request review; it does not merge and does not enable auto-merge there.
- Where the production Worker deploys from its own Cloudflare Git connection, the human's merge is the deploy trigger and the harness runs no deploy command. The exact production `deploy` grant still records the publication consequence. Leave `merge_pr` false because the harness only observes the external human merge, and retain `external_merge_observation` from GitHub's `merged_by` actor plus a durable API/event reference bound to the exact PR URL, reviewed head, and merged SHA.

`deploy` uses `release:<target-id>` in RUN schema v10; older RUN v7-v9 `deployments` files used `environment:<target-id>` for the same grant (see `execution-state-model.md`). Dispatching remote CI additionally uses `trigger_remote_ci` with `workflow:<identity>`. Installing or changing the workflow uses `configure_repository`; creating provider resources uses `provision_cloud_resources` with exact cloud-resource targets.

One explicit user statement may authorize several exact targets, but no action is inferred from another. A native merge-triggered publication always requires independent exact production `deploy` authorization bound to the PLAN revision/digest, candidate head, missions, and `release:<target-id>`. If the harness performs or auto-merges, exact `merge_pr` authorization for the PR and current head is also required. If a human merges externally, leave `merge_pr` false and retain the actor/event-bound `external_merge_observation`; a merged status alone is not proof. After merge, observe and retain the resulting merged source SHA separately.

Use `assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml` for a manual target. Dispatch it with the exact source SHA only after the parent verifies the exact workflow and release grants. Do not make arbitrary pushes an unconditional publication path.

## Auto-Deploy Release Model (Alternative Trigger)

This is an explicit alternative to the default dispatched-GitHub-Actions model in "Authorization And Triggering" above. Choose it only when the user explicitly wants Cloudflare's own native Git integration (Workers Builds) to auto-deploy on push instead of harness-dispatched deploys. Do not default to this model; the dispatched-Actions model above remains the default.

**Branch and Worker topology.** Under the default branch model this needs one Cloudflare Worker resource, connected via Cloudflare's Git integration to the repository. Mission work integrates into the run's own `codex/<short-name>` branch; that branch reaches `main` only through the user-started PR a human merges, and that merge is what triggers the production Worker.

- The **production** Worker watches `main`. Its Cloudflare "Deploy command" is `wrangler deploy --env production`.
- That Worker, and any confirmed D1/KV/R2/Durable Object/queue bindings it needs, should already exist per this doc's "Day one resource creation" step above (in "Wrangler Config and Account Bootstrap") before wiring up its Git connection — creating them at that point, rather than only now, avoids a second isolation check later and means the per-environment binding IDs are already correct in `wrangler.jsonc` before Cloudflare starts auto-deploying on every push to `main`. Then connect the repository to the Worker with its branch-to-listen-to setting and its deploy command, per Cloudflare's own advanced-setup guidance.
- `main` already exists in every repository, so this model needs no branch creation and no setup gap to report.
- A repository that keeps a preview or staging environment may connect a second **development** Worker to a branch of its choosing, with deploy command `wrangler deploy --env development`. That is optional and outside the default model. When it does, and that non-production release target's `source` is `integration_head`, the watched branch must survive across runs: declare `run.integration.retention: "persistent"`, which the validator enforces rather than merely recommends. See `MISSION_RUNBOOK.template.md`'s integration-branch-creation paragraph for how a persistent branch is reused as a run's starting base instead of created fresh. The default model's run branch is disposable and needs none of this.
- `assets/templates/PROJECT_CLOUDFLARE_DEPLOY.template.yml` is NOT used in this model at all. That template belongs only to the default dispatched-Actions model. Do not wire up both at once.

Cloudflare's own mechanism has no approval or review gate: pushing to a Worker's configured branch runs that Worker's Deploy command immediately and automatically. (Pushing to any *other* branch instead runs Cloudflare's "Non-production branch deploy command", default `wrangler versions upload`, which uploads a version without promoting it live.) See:

- https://developers.cloudflare.com/workers/ci-cd/builds/configuration/
- https://developers.cloudflare.com/workers/ci-cd/builds/advanced-setups/

**Release-target `source` value.** Production uses `production_head`, which binds to `landing.merged_sha` after the human merges the landing PR into `main`. An optional non-production target uses `integration_head`, binding PASS to the live-Git-cross-checked head in `run.integration.integration_head_sha`.

**The run-branch push does not deploy.** No Worker watches the run's own branch, so pushing it runs Cloudflare's non-production branch deploy command (`wrangler versions upload` by default) and promotes nothing live. That push is part of the ordinary execution instruction rather than a separate confirmation (see `SKILL.md`'s Execution Authorization Gate): the run uses `landing.mode: integration_push`, `landing.pushed_head_sha` carries the pushed integration head, and the run is complete there. Where a repository does connect a Worker to a branch the run pushes, that push *is* a deploy — record that target's `deploy` entry with its exact `release:<target-id>` and its own recorded source. Do not pretend an auto-deploying push was not a deploy.

**The checkpoint is the landing merge, and that merge is the human's.** Run the Pre-Deploy Confirmation Checkpoint immediately before handing over the run branch -> `main` merge, because that merge is effectively the production deploy trigger — then hand the merge-ready PR over. The harness does not perform that merge and does not enable auto-merge for it. In this model the harness runs no production deploy command at all; the exact production `deploy` grant records the publication the human's merge causes.

**Substitute boundary for out-of-band merges.** Protect `main`: require a pull request and review, and disallow direct pushes. This is the remaining safety boundary against an out-of-band production deploy because Cloudflare's own auto-deploy has no human approval gate. Combined with the human-owned merge above, the only path to a production build is a person pressing merge on a PR that already converged on its exact head.

## Pre-Deploy Confirmation Checkpoint

The user's instruction starts landing on `main`; exact production `deploy` authorization remains independent and is never covered by the execution-intent instruction that covers the development loop. If the harness performs or auto-merges, exact `merge_pr` authorization is separately required. If a human merges externally, leave `merge_pr` false and record observed merged state. Run this checkpoint before either production event: before the parent runs the production deploy command under its exact `deploy` grant, and before it hands over the auto-deploy-triggering merge into `main`. Verify the exact SHA and migration classification below.

**Deploying SHA drift.** At that checkpoint, record the current run-branch head SHA into `targets[production-id].authorized_head_sha`. Before the merge or deploy fires, compare that value against the live SHA about to land. If they differ because review-repair, a new push, or re-integration changed the head, stop and ask for a fresh explicit confirmation naming the new SHA.

**Migration destructiveness.** Before running any migration as part of the production deploy, classify it:

- Additive — new column, table, or index with safe defaults and no possible data loss. This rides the exact production-target `deploy` authorization. Record the classification as the PLAN target's `migration_classification: "additive"`.
- Potentially destructive — column or table drop, type narrowing, a `NOT NULL` added to existing data, or any data transformation that cannot be trivially reversed. This needs its own explicit confirmation, separate from the target's ordinary `deploy` grant. Do not let it ride through on the same blanket authorization as a routine additive migration. Name the exact destructive operation when asking, and confirm the rollback/backup plan is ready first. Record the classification as the PLAN target's `migration_classification: "destructive"` and, once the separate confirmation is obtained, the exact SHA it was obtained at in `targets[production-id].destructive_migration_confirmed_sha` — so the decision is auditable after the fact rather than only decided informally in conversation.

If either check trips, stop and ask before proceeding. If both are clean — same SHA, additive-or-no migration — proceed under the existing exact `deploy` authorization without a redundant prompt: run the deploy command in the dispatched-Actions model, or hand the merge over in the auto-deploy model. "Proceed" never means merging the landing PR.

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

- Stop the landing on `main` when a declared non-production deploy, migration, or deployed-environment verification fails.
- Do not mark production PASS when its smoke test fails, even if the upload succeeded.
- Record the last known rollback version when Cloudflare exposes one; do not invent it for a first deployment.
- Treat any new PR push as stale non-production evidence and redeploy/reverify the new current head.
- Treat any change to `main` as stale production evidence until that exact SHA is deployed and smoked.

Recheck current official Cloudflare documentation and the installed Wrangler config schema before using fast-moving configuration fields or command options:

- https://developers.cloudflare.com/workers/wrangler/environments/
- https://developers.cloudflare.com/workers/wrangler/configuration/
- https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/
- https://developers.cloudflare.com/workers/versions-and-deployments/
- https://developers.cloudflare.com/d1/reference/migrations/

# Deployment

The deployment record for this repository: the platform model, the exact configuration a human must supply, the runbook for adding a binding, and the live environment status. The governing semantics live in the Product Delivery Harness `deployment-contract.md`; this file is the project's filled-in instance. Keep it at `docs/DEPLOYMENT.md`, reconcile it against the implementation before every deployable push, and update its status after deployment.

## Record

- Platform: <cloudflare | vercel | aws | any lowercase id>
- Mode: git_connected (the platform builds on push) | ci_connected (a repository CI workflow deploys on push) | manual (a recorded deploy command the user runs)
- Production branch: the repository's resolved default branch (what lands there is the production candidate)
- Preview: tracks non-default branch pushes; a preview PASS never proves production
- Production URL: <url>
- Preview URL pattern: <pattern>
- Deployed-commit check: <platform API/CLI command or response header>
- Protected resources preview must never bind: <databases, buckets, secrets, domains>

## Resource Isolation

Production and preview use fully separate stateful resources. Record every binding class this project uses; an identical ID in both columns is a blocker. Mark a class the project does not use `n/a`.

| Binding class | Production resource | Preview resource |
| --- | --- | --- |
| D1 database | <fill> | <fill> |
| KV namespace | <fill> | <fill> |
| R2 bucket | <fill> | <fill> |
| Durable Objects | <fill> | <fill> |

## Required Secrets and Variables

This is the human configuration handoff. Inventory names and destinations only — never record a secret value in this file, a commit, a command transcript, or deployment evidence. Reconcile the rows from tracked declarations and code references such as `.env.example`, the environment schema, platform config, CI workflows, and auth or integration code. Do not open local value-bearing files such as `.env`, `.env.local`, or `.dev.vars` to prepare this table. If the project needs no secrets or variables, keep one `none` / `n/a` row instead of deleting the section.

| Name | Kind | Consumer | Preview placement | Production placement | Source / owner | Status |
| --- | --- | --- | --- | --- | --- | --- |
| <secret or variable name> | <secret or variable> | <runtime, build, CI, or external service> | <fill> | <fill> | <fill> | pending |

Placement means the exact control surface a human opens. Examples: a Cloudflare Worker's named development or production environment; Vercel Project Settings scoped to Preview or Production; or repository Actions secrets for a CI deploy token. Classify browser-exposed configuration as `variable`, not `secret`. Include deploy credentials used by CI as well as application runtime keys.

## External Console Setup

Record every non-code task required in another system, especially auth setup: create the application or tenant, register preview and production callback/redirect URLs, set allowed origins and logout URLs, configure webhook endpoints, attach domains or DNS, and grant required roles. Put any credential name created by these steps in the inventory above, but never its value. If no external setup is required, keep one `none` / `n/a` row.

| Service | Setting | Preview / non-production | Production | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| <service> | <setting or account task> | <fill> | <fill> | <fill> | pending |

## Adding A Binding

Per-platform runbook. The order behind every platform's steps is the same: the resource exists before any config references it, the preview side is verified before anything lands on the default branch, and each production landing is verified again on the production URL. The commands are not the same — use this project's platform section, and never apply another platform's steps.

### cloudflare

For a new stateful binding (KV namespace, D1 database, R2 bucket, Durable Objects). The order is a hard constraint on both sides: create the resource first, then write the declaration — a declaration naming a missing resource fails deploy validation and turns the pipeline red.

1. Create the preview-side resource with the project's `-preview` naming and record its ID. Any ID the wrangler config needs must exist before the declaration is written.
2. Declare the binding in the development environment (for example `env.development`) and push the run branch; the preview pipeline deploys it automatically. Acceptance on the branch preview URL: the app's own binding listing (for example `/health`) shows the new binding name and the feature works. Add the new binding class row to the Resource Isolation table above.
3. Create the production-side resource. This is an owner action — do not skip it or swap the order.
4. Add the production environment's declaration (for example `env.production`) together with the other preview-verified changes and land it on the default branch. After the production deploy, verify the new binding on every production URL — a preview PASS never proves production.
5. Secrets for the new binding: fake or dedicated values on the preview worker, real values only in production, never in the wrangler config.
6. With a D1 schema change: apply the migration to the preview database and verify it there first; coordinate the production database migration with the default-branch deploy so new code never ships before the production schema exists.

### vercel, aws, generic

Do not reuse the cloudflare steps. Record this project's own steps in the same order: create the resource, attach it to the preview environment and verify on the preview URL, attach the production environment only with the default-branch landing, then verify on the production URL. Vercel attaches stores and integrations as per-environment settings in the project; AWS Amplify wires resources into the branch mapping's backend environments. Values and secrets stay scoped per environment and never enter the repository.

## Human Setup Checklist

These steps are performed by a person with platform access; the Harness never performs, triggers, or reconfigures them. Check them off as completed.

### Git connection (git_connected mode)

- [ ] Connect the repository to the platform (Cloudflare Pages/Workers, Vercel project, or AWS Amplify app).
- [ ] Set the production branch to the repository's default branch.
- [ ] Enable automatic preview builds for non-default branches.

### CI connection (ci_connected mode)

- [ ] Create the project from the CLI (for example `wrangler pages project create <name> --production-branch <default-branch>`) and run the first deploy yourself.
- [ ] Add the repository workflow that deploys on push: the production branch to production, every other branch to a preview URL.
- [ ] On Workers, the workflow runs `wrangler deploy` for the production branch and targets the named development environment (`wrangler deploy --env development`, or `wrangler versions upload --env development` for a per-push preview URL) for every other branch.
- [ ] Create the non-production resources at setup — `wrangler d1 create`, `wrangler kv namespace create`, `wrangler r2 bucket create` with a `-preview` name — and bind them through the named preview environment with its full binding set declared explicitly; named environments do not inherit bindings.
- [ ] Confirm a version preview of the production Worker is never used for stateful preview traffic: it shares that Worker's live bindings, so its writes reach production resources.
- [ ] Store the platform API token as a repository secret; never place it in the repository itself.
- [ ] Keep preview and production variables and secrets separate in the workflow, exactly as in a git-connected project.

### Environments

- [ ] Reconcile every required secret and variable name against the implemented code and tracked configuration; do not copy values into this document.
- [ ] Complete or explicitly leave `pending` every Required Secrets and Variables row, with the exact preview and production placement named.
- [ ] Complete the External Console Setup rows, including auth callback URLs, allowed origins, webhook endpoints, domains, and required roles when applicable.
- [ ] Create separate preview and production environments with separate variables and secrets.
- [ ] Point preview at non-production databases, buckets, and auth providers; never bind a production resource to preview.
- [ ] Fill the Resource Isolation table with both resource-ID sets and confirm no ID appears in both columns.
- [ ] Attach the production domain to the production environment only.

### Verification access

- [ ] Confirm the deployed-commit check command runs read-only with the available credentials.
- [ ] Record the check result for one known deployment below.

## Platform Notes

- cloudflare: prefer native Preview URLs; per-branch disposable Workers only when a feature such as Durable Objects requires them, with a reserved name prefix and a protected list of permanent Workers. Production is a separately gated environment, never a side effect of preview. `ci_connected` bootstraps the same model with `wrangler pages project create` plus a push-triggered CI workflow; a Wrangler-created Direct Upload project can never be converted to git-connected.
- vercel: preview per push, production on the default branch; environment scoping in project settings is the protected-production boundary.
- aws: Amplify branch mapping — default branch to production, non-default branches to automatic previews; separate backend environments and secrets per branch mapping.
- generic: record branch-build semantics when the platform supports them; otherwise record `manual` with the deploy command and the read-only check that follows.

## Environment Status

| Environment | URL | Expected head | Deployed SHA | Checked | Status |
| --- | --- | --- | --- | --- | --- |
| preview | | | | | |
| production | | | | | |

Verification is read-only: record what deployed, compare it to the expected head, and route any mismatch to the owner or a new mission — never redeploy from here.

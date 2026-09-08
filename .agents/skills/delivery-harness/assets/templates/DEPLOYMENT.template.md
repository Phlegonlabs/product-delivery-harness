# Deployment

The deployment record for this repository: the platform model, the exact configuration a human must supply, the runbook for adding a binding, and the live environment status. The governing semantics live in the Product Delivery Harness `deployment-contract.md`; this file is the project's filled-in instance. Keep it at `docs/DEPLOYMENT.md`, reconcile it against the implementation before every deployable push, and update its status after deployment.

## Record

- Platform: <cloudflare | vercel | aws | any lowercase id>
- Mode: git_connected (the platform builds on push) | ci_connected (a repository CI workflow deploys on push) | manual (a recorded deploy command the user runs)
- Development branch: `development` (persistent internal candidate and non-production environment)
- Production branch: `main` (receives only the exact internally verified development SHA)
- Run-branch previews: optional and disposable; they never replace verification on the remote `development` head
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

After the delivery RUN closes, the sibling `product-activation` skill may convert applicable rows into exact `ACT-*` actions in `docs/ACTIVATION.md`. The row itself grants no external-write permission. Keep deployment placement here and detailed action, capability, authorization, and evidence state in the Activation record.

| Service | Setting | Preview / non-production | Production | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| <service> | <setting or account task> | <fill> | <fill> | <fill> | pending |

## Adding A Binding

Per-platform runbook. The order is fixed: each resource exists before config references it, the exact remote `development` head passes internal verification, then the unchanged SHA reaches `main` and production is verified separately. Commands vary by platform; never copy another platform's steps.

### cloudflare

For a new stateful binding (KV namespace, D1 database, R2 bucket, Durable Objects). The order is a hard constraint on both sides: create the resource first, then write the declaration — a declaration naming a missing resource fails deploy validation and turns the pipeline red.

1. Create the preview-side resource with the project's `-preview` naming and record its ID. Any ID the wrangler config needs must exist before the declaration is written.
2. Declare the binding in the development environment (for example `env.development`), promote the exact candidate to `development`, and verify it on the development URL. A run-branch preview does not satisfy this gate. Add the binding class row to Resource Isolation.
3. Create the production-side resource. This is an owner action — do not skip it or swap the order.
4. Add the production declaration (for example `env.production`) to the same candidate lineage. If that changes the SHA, promote it to `development` and repeat internal verification. Then fast-forward the exact verified SHA to `main` and verify every production URL.
5. Secrets for the new binding: fake or dedicated values on the preview worker, real values only in production, never in the wrangler config.
6. With a D1 schema change: apply the migration to the preview database and verify it there first; coordinate the production database migration with the default-branch deploy so new code never ships before the production schema exists.

### vercel, aws, generic

Do not reuse the cloudflare commands. Keep the same order: create and attach non-production resources, promote and verify `development`, prepare production resources, then promote the unchanged verified SHA to `main` and verify production. Values and secrets stay scoped per environment and never enter the repository.

## Branch Promotion

Follow `delivery-harness/references/branch-promotion-contract.md`. Fill this record from read-back evidence; a future intention is not a completed row.

- Delivery kind: <initial_delivery | enhancement>
- Run branch: <full branch ref>
- Candidate SHA: <full SHA>
- Development before: <full SHA | absent for authorized initial creation>
- Development pushed and read back: <full SHA | pending>
- Internal development verification: <PASS/FAIL/pending; exact SHA, commands/checks, environment/URL, timestamp, evidence>
- Main before: <full SHA>
- Main ancestry/fast-forward proof: <PASS/FAIL/pending>
- Main pushed and read back: <full SHA | pending>
- Final ref convergence: <PASS when remote development and main equal the verified SHA | pending>
- Production deployed SHA and smoke: <full SHA plus PASS/FAIL/pending>

## Human Setup Checklist

These steps are performed by a person with platform access; the Harness never performs, triggers, or reconfigures them. Check them off as completed.

### Git connection (git_connected mode)

- [ ] Connect the repository to the platform (Cloudflare Pages/Workers, Vercel project, or AWS Amplify app).
- [ ] Map `development` to the isolated internal/non-production environment.
- [ ] Map `main` to production.
- [ ] Treat other run-branch previews as optional and non-authoritative.

### CI connection (ci_connected mode)

- [ ] Create the project from the CLI (for example `wrangler pages project create <name> --production-branch main`) and run the separately authorized bootstrap deploy.
- [ ] Add the repository workflow that deploys `development` to the internal environment and `main` to production; optional run branches may receive disposable previews.
- [ ] On Workers, run `wrangler deploy` for `main` and target the named development environment only from `development` (`wrangler deploy --env development`, or `wrangler versions upload --env development`).
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

- cloudflare: `development` targets the isolated preview Worker/environment and `main` targets production; optional run-branch previews never substitute for development verification.
- vercel: `development` is the internally verified preview and `main` is production; environment scoping protects production.
- aws: map `development` to isolated non-production and `main` to production; keep separate backend environments and secrets.
- generic: record the same two protected branch roles when supported; otherwise use `manual` with separate authorization and read-back.

## Environment Status

| Environment | URL | Expected head | Deployed SHA | Checked | Status |
| --- | --- | --- | --- | --- | --- |
| development | | | | | |
| production | | | | | |

Verification is read-only: record what deployed, compare it to the expected head, and route any mismatch to the owner or a new mission — never redeploy from here.

## Product Activation Handoff

- Activation record: `docs/ACTIVATION.md` when the product has post-delivery setup or measurable outcome sources; absent is valid for legacy or non-applicable products.
- Handoff timing: after required `development`/`main` promotion and deployment verification complete, never as another RUN node or authorization.
- Handoff content: exact delivered/deployed SHA, release target IDs and URLs, deployment evidence, implemented hooks, and pending name-only configuration or console rows.
- Execution: `product-activation` probes connector/API/CLI/Browser/Computer Use routes and performs only exact authorized actions.
- Completion: an Activation target is ready only after read-back and behavior evidence; pending activation never keeps the delivery RUN open.

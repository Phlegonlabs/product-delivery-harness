# Deployment Contract

Use this reference when a delivery will be deployed, when verifying a deployed environment, or when moving a project between deploy platforms. The Harness RUN still ends locally or at its own run-branch push. `branch-promotion-contract.md` then controls the separately authorized exact-SHA promotion to `main`; this contract maps the candidate branch/SHA and production branch to environments and verifies what the platform serves.

## Model

- Production tracks `main`; the production pipeline deploys only the exact candidate SHA promoted there after all candidate verification passes.
- The isolated internal environment tracks the exact candidate run branch or immutable candidate SHA. There is no persistent integration branch.
- A git-connected or CI-connected platform maps the candidate run branch/SHA to the isolated non-production environment and `main` to production. The bootstrap deploy remains a separately authorized owner action when required; branch promotion adds no RUN authorization keys and never reuses the run-branch grant.
- Development and production are separate environments with separate URLs, builds, stateful resources, auth, and payment modes. A development PASS never proves production; development never binds production databases, buckets, secrets, or domains.
- Every independently released unit has one lowercase kebab-case surface name. Production uses the canonical `<product-slug>-<surface-suffix>` name without `-prod`; development uses that exact name plus `-dev`. Use `web`, `api`, and `extension` as the normal suffixes. Use another descriptive suffix only for a separately released unit; native artifacts use their platform suffix while a separately hosted backend remains `api`. Provider and store names stay in provider/channel fields unless artifacts actually differ by provider. Long-lived staging or QA may use its real stage suffix; ephemeral candidate previews keep platform-generated identities.
- CLI or console deploys remain explicit user machine mutations outside the RUN ledger, like any other installed-software operation. The Harness never triggers, rolls back, or reconfigures a deployment.

## Platform Abstraction

Any lowercase platform id is valid. Each section below names that platform's native preview and production mechanics; `generic` covers everything else. Adding a platform adds one section, not a new flow — the model above does not change.

## Human Configuration Handoff

`docs/DEPLOYMENT.md` is both the deployment record and the operator handoff. `product-definition-builder` seeds it from the product and architecture decisions. Before every deployable push, `delivery-harness` reconciles it against the implementation whenever the change adds, removes, renames, or changes the use of configuration, auth, a binding, an integration, or a deploy workflow. After deployment, the parent records the observed environment result and leaves every external-console task truthfully `pending`, `configured`, `verified`, or `n/a`. A later `product-activation` run may consume those rows, but it receives no authorization from their presence or status.

The reconciliation is name-only and read-only:

1. Inspect tracked declaration surfaces: `.env.example` or another committed example, typed environment schemas, platform config, CI workflows, and the code paths that read configuration or call auth and external services.
2. Never open value-bearing local files such as `.env`, `.env.local`, `.dev.vars`, exported platform secrets, or credential stores to populate the document. Never copy a value into Markdown, Git, logs, command transcripts, or evidence.
3. In **Required Secrets and Variables**, record each exact key name, classify it as a secret or non-secret variable, name its consumer, identify the exact preview and production placement, name where the human obtains it, and record status. Include CI deploy credentials as well as application runtime configuration. Browser-exposed keys are variables even when their provider calls them keys.
4. In **External Console Setup**, record every non-code action with its exact system and environment: auth application or tenant creation, callback and logout URLs, allowed origins, webhook registration, domain/DNS attachment, role grants, payment mode, or another provider-side setting.
5. When no rows apply, keep an explicit `none` / `n/a` row. Never omit either section, and never invent a key or callback URL that the product or implementation has not defined.

A `pending` row is allowed in the record because it is an honest human handoff. It is also an availability gate: if the row is required for the target environment, that environment cannot be reported ready until the human finishes it and a behavior-level smoke check passes. The Harness reports the exact pending names and console tasks; it never fills, rotates, reveals, or guesses their values and never reconfigures the platform.

## Platform: cloudflare

- The default Cloudflare route is Workers with Static Assets. Pages enters a project only when the owner explicitly decides it, recorded in that project's deployment record and `stack-decisions.md`.
- Workers resource isolation is configured, not assumed. Version previews inherit the Worker's existing bindings, so isolation comes from a named Wrangler environment (for example `env.development`) that deploys the separately named development Worker (for example `<product-slug>-web-dev`) and binds only non-production resources. Create those resources at project setup with names derived from their canonical production resource plus `-dev` — for example `wrangler d1 create <resource-name>-dev`, `wrangler kv namespace create <resource-name>-dev`, and `wrangler r2 bucket create <resource-name>-dev` — before the first development push, and declare the development environment's full binding set explicitly: named environments do not inherit bindings, so a missing declaration surfaces as a broken or wrong binding rather than a safe default. A development target bound to a production D1/R2/KV/Durable-Object/auth/webhook resource is a blocker, not a configuration preference, and this boundary must not depend on an experimental flag. Record both sets in the deployment record's Resource Isolation table — every stateful binding class (D1 database, KV namespace, R2 bucket, Durable Objects) with its production and development resource IDs — and cross-check the development environment's declared bindings read-only against the recorded production IDs before the first development push serves traffic, so any production ID appearing in a development binding is caught before data moves, not after. `scripts/check_deployment.py` fails a record whose isolation table shares one ID between the two columns.
- Adding a binding follows one order: create the non-production resource, declare it, deploy the exact candidate branch/SHA to the isolated development environment, and verify the binding on its URL. Only then create the production resource, include its declaration in the same candidate lineage, repeat candidate verification if the SHA changes, and promote that exact verified SHA to `main`. Production is verified separately. Missing resources, shared production IDs, or schema-order failures block promotion. Development secrets stay fake or dedicated; production values never enter tracked config. D1 migrations run against the non-production database first and are coordinated with the `main` promotion so code never precedes its production schema. The project instance lives in `docs/DEPLOYMENT.md`; platform commands vary, but candidate-first verification does not.
- Cloudflare Pages, git-connected: the candidate run branch supplies the internal preview deployment, while `main` is the configured production branch at `<project>.pages.dev`. The evidence must bind the preview to the exact candidate SHA.
- Cloudflare Workers, CI-connected: deploy `main` with `wrangler deploy` and deploy the exact candidate SHA to the named non-production environment with `wrangler deploy --env development` (or `wrangler versions upload --env development`). A version Preview URL of the production Worker shares live bindings and is not an isolated development environment. Production promotion is a separate exact-SHA `main` update, never a side effect of another branch push.
- Cloudflare Pages, CI-connected (Wrangler bootstrap): create the project with `wrangler pages project create <name> --production-branch main`, run the first deploy yourself, then let candidate run branches build isolated previews while `main` supplies production. Choose this mode at creation time — a Wrangler-created Direct Upload project cannot later become git-connected.
- Workers: version Preview URLs review new code on the Worker's existing bindings — stateless review only. When the application needs isolated state, such as Durable Objects or any stateful preview traffic, use the named preview environment's separately named Worker instead, with a reserved name prefix and a protected list of every permanent Worker. Production is a separately gated Wrangler environment, never a side effect of a preview push.
- Deployed-commit check: `wrangler pages deployment list` / `wrangler deployments list`, the Cloudflare API, or the deployment's response headers.

## Platform: vercel

- Git-connected: the exact candidate run branch supplies the internally verified preview and `main` supplies production.
- Keep preview and production environment variables and domains separate in the project settings; the protected-production boundary is the platform's environment scoping, not a Harness action.
- Deployed-commit check: `vercel inspect <url>` or the Vercel API.

## Platform: aws

- Amplify, git-connected: map the exact candidate run branch to an isolated non-production environment and `main` to production.
- Preview and production use separate backend environments and secrets; never point a preview branch mapping at production resources.
- Deployed-commit check: `aws amplify list-jobs` / the Amplify API.

## Platform: generic

- Assume branch-build semantics when the platform supports them: the exact candidate run branch for internal verification and `main` for production. Otherwise record `mode: manual` with the separately authorized deploy command and read-only check.
- Record what is known; never invent a platform capability the project has not configured.

## Post-Deploy Verification (read-only)

Verify the candidate environment before promotion when it applies, then verify production after the separately authorized `main` promotion:

1. The expected environment URL resolves — the isolated non-production URL for the exact candidate SHA, then the production URL for the promoted `main` head.
2. The deployed commit equals the expected head, read from the platform API/CLI or response headers, and recorded bound to that SHA. A mismatch or a stale build is a finding for the user or a new mission, never a redeploy order.
3. Verify required human configuration through non-secret evidence: platform metadata that exposes names but not values, plus behavior-level checks such as a completed auth redirect or integration smoke. Never print or retrieve a secret value. Keep an unverified requirement `pending` even when the build itself succeeded.
4. Record evidence with the environment, URL, deployed SHA, expected SHA, and the check command — the same evidence discipline as any other gate. Reconcile the Required Secrets and Variables and External Console Setup statuses with what was actually verified. `scripts/check_deployment.py --deployment <path>` structurally validates the record read-only (unresolved placeholders, missing handoff sections, invalid handoff rows, missing environment rows, partially verified rows) without ever running the recorded command.
5. Report the observed non-production or production URL with its exact SHA and every remaining human action. When the build has not finished or the URL cannot be observed, leave the record pending; never construct or guess a URL.

Writing the observed result into the tracked deployment record does not authorize or require another push. A later commit of that operational update is a new change under the ordinary branch, verification, commit, and push boundaries; its status row describes the deployment it observed and never pretends to be a self-reference to the document commit.

## Product Activation Handoff

Deployment and activation are separate. The RUN closes at its local or run-branch-push boundary; branch promotion and deployment verification follow under their own authorizations. The sibling `product-activation` skill then owns any explicitly requested external setup and `docs/ACTIVATION.md`; it never reopens or edits PLAN/RUN.

After RUN close, provide one bounded handoff when the product has deployable surfaces:

- the exact delivered and, when available, deployed full Git SHA;
- stable release target IDs, environments or channels, and observed URLs;
- deployment-check evidence and every unresolved environment mismatch;
- implemented analytics, consent, crash, store, email, payment, webhook, monitoring, or other activation hooks; and
- every pending Required Secrets and Variables or External Console Setup row, naming configuration only and never a value.

If the user already asked to continue into activation, invoke `product-activation` only after required branch promotion and deployment verification complete. Otherwise report the exact handoff and suggest the explicit next invocation. Tool availability, a signed-in browser, a deployment PASS, and RUN authorization do not authorize an external console mutation. Product Activation probes connector/API/CLI/Browser/Computer Use routes separately, binds approval to each exact target and action, and writes `verified` only after independent read-back and behavior evidence.

An absent `docs/ACTIVATION.md` remains valid for legacy or non-applicable products. Product Definition may create the first seed when the path is absent; Product Activation bootstraps it when needed. Neither absence nor a pending activation task keeps the delivery RUN open.

## Recording The Model In A Repository

Two records carry the deployment model. `docs/DEPLOYMENT.md`, seeded during PRD creation and reconciled before promotion, is the detailed instance: candidate/main branch roles, platform record, name-only configuration inventory, external-console tasks, internal-test evidence, and environment status. The seeded `AGENTS.md` summarizes the same main-only governance. Keep both filled from live evidence; an unfilled record means the model is unknown. `docs/ACTIVATION.md` remains separate.

## Moving Between Platforms

Migrating — Cloudflare to AWS or Vercel, or anywhere else — changes the record and platform section, not the flow: map the exact candidate run branch/SHA to isolated non-production and `main` to production, update the deployment record, and re-verify both exact SHAs. No promotion or authorization rule changes with the platform.

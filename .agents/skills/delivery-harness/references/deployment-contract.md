# Deployment Contract

Use this reference when a delivery will be deployed, when verifying a deployed environment, or when moving a project between deploy platforms. The Harness run itself still ends at the push of the verified run branch; deployment is what the platform does with Git after that. This contract makes that step explicit, verifiable, and portable.

## Model

- Production tracks the repository's resolved default branch: what the user lands on `main` is the production candidate, and the platform's production pipeline deploys exactly that. Merging to the default branch remains the user's own step, outside the Harness.
- Preview tracks the run branch: a git-connected platform builds a preview for each non-default-branch push. The run's already-authorized `push` is then the only Harness action in the deployment loop — a git-connected deployment adds no authorization keys, and the 12-key ledger stays frozen.
- A repository CI workflow can own the same loop: `ci_connected` mode records a workflow (for example GitHub Actions running Wrangler) that deploys on push — the production branch to production, every non-default branch to a preview URL. The bootstrap deploy may be a one-time owner-run CLI command; the automated loop itself lives in the repository. A CI deployment adds no authorization keys, exactly like a git-connected one: the run's authorized `push` stays the only Harness action, and the Harness never triggers, rolls back, or reconfigures the workflow.
- Preview and production are separate environments: separate URLs, separate builds, and separate stateful resources. A preview PASS never proves production; production never deploys from a non-default branch; preview never binds production databases, buckets, secrets, or domains.
- CLI or console deploys remain explicit user machine mutations outside the RUN ledger, like any other installed-software operation. The Harness never triggers, rolls back, or reconfigures a deployment.

## Platform Abstraction

Any lowercase platform id is valid. Each section below names that platform's native preview and production mechanics; `generic` covers everything else. Adding a platform adds one section, not a new flow — the model above does not change.

## Platform: cloudflare

- The default Cloudflare route is Workers with Static Assets. Pages enters a project only when the owner explicitly decides it, recorded in that project's deployment record and `stack-decisions.md`.
- Workers resource isolation is configured, not assumed. Version previews inherit the Worker's existing bindings, so isolation comes from a named Wrangler environment (for example `env.development`) that deploys a separately named Worker (for example `<name>-preview`) and binds only non-production resources. Create those resources at project setup — `wrangler d1 create <name>-preview`, `wrangler kv namespace create <name>-preview`, `wrangler r2 bucket create <name>-preview` — before the first preview push, and declare the development environment's full binding set explicitly: named environments do not inherit bindings, so a missing declaration surfaces as a broken or wrong binding rather than a safe default. A preview bound to a production D1/R2/KV/Durable-Object/auth/webhook resource is a blocker, not a configuration preference, and this boundary must not depend on an experimental flag. Record both sets in the deployment record's Resource Isolation table — every stateful binding class (D1 database, KV namespace, R2 bucket, Durable Objects) with its production and preview resource IDs — and cross-check the development environment's declared bindings read-only against the recorded production IDs before the first preview push serves traffic, so any production ID appearing in a preview binding is caught before data moves, not after. `scripts/check_deployment.py` fails a record whose isolation table shares one ID between the two columns.
- Adding a binding follows one order on both sides: create the resource, then write the declaration. Preview first — create the preview-side resource, declare it in the named development environment's explicit binding set, push the run branch, and accept it on the branch preview URL: the app's own binding listing (for example a `/health` endpoint) shows the new binding name and the feature works. Then production — the owner creates the production resource, and only then does the production-environment declaration land on the default branch together with the other preview-verified changes; after the deploy, verify the new binding on every production URL, because a preview PASS never proves production. The order is a hard constraint on both sides: a declaration that reaches the platform before its resource exists fails deploy validation (invalid KV ID, missing resource) and turns the pipeline red. A new binding's secrets take fake or dedicated values on preview and real values only in production, never in the wrangler config. A binding that changes D1 schema migrates the preview database first and coordinates the production migration with the default-branch deploy, so code never ships before the production schema exists. The project instance of this runbook lives in the seeded `docs/DEPLOYMENT.md`'s "Adding A Binding" section. The order is portable; the commands are not — that runbook scopes these wrangler steps to cloudflare, and vercel, aws, and generic projects record their own equivalent (resource created before its environment reference, preview verified before production) in the same section.
- Cloudflare Pages, git-connected: a preview builds per non-default-branch push at `<hash>.<project>.pages.dev`; production builds on the configured production branch at `<project>.pages.dev`. Set the production branch to the repository's resolved default branch.
- Cloudflare Workers, CI-connected: the same workflow deploys the default environment with `wrangler deploy` on the production branch and targets the named development environment with `wrangler deploy --env development` on every other branch — or `wrangler versions upload --env development` when a per-push version preview URL of the preview Worker fits the review better. A version preview URL of the production Worker itself is review-only for stateless surfaces: it serves a new version of the same Worker and shares that Worker's live bindings, so its writes reach production D1/KV/R2. The deployed-commit check still reads `wrangler deployments list`, and the preview link reported in the conversation is the preview Worker's URL or its version preview URL, observed from the workflow's `wrangler versions upload` output or `wrangler versions list`, each push producing a fresh URL rather than a stable branch alias. Preview deploys never touch production traffic or production resources. Promoting to production is `wrangler deploy` (or `wrangler versions deploy` for a gradual rollout), never a side effect of a preview push.
- Cloudflare Pages, CI-connected (Wrangler bootstrap): create the project with `wrangler pages project create <name> --production-branch <default-branch>`, run the first deploy yourself with `wrangler pages deploy`, then let a repository CI workflow build and run `wrangler pages deploy ./dist --branch <branch>` on every push, with the API token stored as a repository secret. The branch split is identical to git-connected: the production branch deploys to `<project>.pages.dev`, every other branch serves a preview at `<hash>.<project>.pages.dev`. Choose this mode at creation time — a Wrangler-created Direct Upload project can never be converted to git-connected afterwards.
- Workers: version Preview URLs review new code on the Worker's existing bindings — stateless review only. When the application needs isolated state, such as Durable Objects or any stateful preview traffic, use the named preview environment's separately named Worker instead, with a reserved name prefix and a protected list of every permanent Worker. Production is a separately gated Wrangler environment, never a side effect of a preview push.
- Deployed-commit check: `wrangler pages deployment list` / `wrangler deployments list`, the Cloudflare API, or the deployment's response headers.

## Platform: vercel

- Git-connected: a preview builds per push at `<project>-<hash>-<scope>.vercel.app`; production builds on the default branch at the project domain.
- Keep preview and production environment variables and domains separate in the project settings; the protected-production boundary is the platform's environment scoping, not a Harness action.
- Deployed-commit check: `vercel inspect <url>` or the Vercel API.

## Platform: aws

- Amplify, git-connected: create one branch mapping — the default branch to the production environment, non-default branches to automatic preview environments — and record the preview URL pattern.
- Preview and production use separate backend environments and secrets; never point a preview branch mapping at production resources.
- Deployed-commit check: `aws amplify list-jobs` / the Amplify API.

## Platform: generic

- Assume branch-build semantics when the platform supports them: production on the default branch, preview per non-default-branch push. Otherwise record `mode: manual` with the deploy command the user runs and the read-only check that follows it.
- Record what is known; never invent a platform capability the project has not configured.

## Post-Deploy Verification (read-only)

After the run's authorized push, or after the user lands a change on the default branch, verify the environment as a read-only gate:

1. The expected environment URL resolves — the preview URL for the pushed head, the production URL after the landing.
2. The deployed commit equals the expected head, read from the platform API/CLI or response headers, and recorded bound to that SHA. A mismatch or a stale build is a finding for the user or a new mission, never a redeploy order.
3. Record evidence with the environment, URL, deployed SHA, expected SHA, and the check command — the same evidence discipline as any other gate. `scripts/check_deployment.py --deployment <path>` structurally validates the record read-only (unresolved placeholders, missing environment rows, partially verified rows) without ever running the recorded command.
4. Report the pushed head's preview URL to the user in the conversation as part of this gate — the URL the platform or CI workflow actually produced, observed read-only from the workflow run output or the platform's version/deployment listing. When the build has not finished or the URL cannot be observed, say exactly that and leave the record pending; never construct or guess a URL.

## Recording The Model In A Repository

Two records carry the model. `docs/DEPLOYMENT.md`, seeded during PRD creation from `assets/templates/DEPLOYMENT.template.md`, is the detailed instance: the platform record, the human setup checklist (git connection, environments, verification access), and the environment status table. The seeded `AGENTS.md` deployment section (imported by `CLAUDE.md`) is the governance summary agents follow: platform, mode, production branch, preview mechanism, production URL, deployed-commit check, and protected resources. Keep both filled from the live project; an unfilled record means the deployment model is unknown, not "deploy whatever".

## Moving Between Platforms

Migrating — Cloudflare to AWS or Vercel, or anywhere else — changes the record and the platform section, not the flow: reconnect Git on the new platform, map the default branch to production and non-default branches to preview, re-point the seeded deployment record, and re-verify both environments with the new platform's committed-check command. No Harness rule, gate, or authorization changes with the platform.

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

- Cloudflare Pages, git-connected: a preview builds per non-default-branch push at `<hash>.<project>.pages.dev`; production builds on the configured production branch at `<project>.pages.dev`. Set the production branch to the repository's resolved default branch.
- Cloudflare Pages, CI-connected (Wrangler bootstrap): create the project with `wrangler pages project create <name> --production-branch <default-branch>`, run the first deploy yourself with `wrangler pages deploy`, then let a repository CI workflow build and run `wrangler pages deploy ./dist --branch <branch>` on every push, with the API token stored as a repository secret. The branch split is identical to git-connected: the production branch deploys to `<project>.pages.dev`, every other branch serves a preview at `<hash>.<project>.pages.dev`. Choose this mode at creation time — a Wrangler-created Direct Upload project can never be converted to git-connected afterwards.
- Cloudflare Workers, CI-connected: the same workflow deploys with `wrangler deploy` on the production branch and uploads a preview version with `wrangler versions upload` on every other branch — each uploaded version serves its own preview URL once `preview_urls` is enabled in the Wrangler config, and the deployed-commit check still reads `wrangler deployments list`. Preview versions are still Workers: they bind only non-production D1/R2/KV/Durable-Object/auth/webhook resources and never touch production traffic. Promoting to production is `wrangler deploy` (or `wrangler versions deploy` for a gradual rollout), never a side effect of the upload.
- Workers: prefer native version Preview URLs. Use one disposable Worker per branch only when the application needs something Preview URLs do not support, such as Durable Objects — then preview Workers use a reserved name prefix, bind only non-production D1/R2/KV/Durable-Object/auth/webhook resources, and keep a protected list of every permanent Worker. Production is a separately gated Wrangler environment, never a side effect of a preview push.
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

## Recording The Model In A Repository

Two records carry the model. `docs/DEPLOYMENT.md`, seeded during PRD creation from `assets/templates/DEPLOYMENT.template.md`, is the detailed instance: the platform record, the human setup checklist (git connection, environments, verification access), and the environment status table. The seeded `AGENTS.md` deployment section (imported by `CLAUDE.md`) is the governance summary agents follow: platform, mode, production branch, preview mechanism, production URL, deployed-commit check, and protected resources. Keep both filled from the live project; an unfilled record means the deployment model is unknown, not "deploy whatever".

## Moving Between Platforms

Migrating — Cloudflare to AWS or Vercel, or anywhere else — changes the record and the platform section, not the flow: reconnect Git on the new platform, map the default branch to production and non-default branches to preview, re-point the seeded deployment record, and re-verify both environments with the new platform's committed-check command. No Harness rule, gate, or authorization changes with the platform.

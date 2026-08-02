---
name: manage-cloudflare-worker-deployments
description: Configure, audit, test, and repair automatic per-branch Cloudflare Worker previews with deterministic Worker names, safe cleanup, and an optional separately gated production bootstrap deployment. Use when a repository needs non-main branch deployments, cannot use Cloudflare version Preview URLs (including Workers with Durable Objects), needs branch Worker lifecycle automation copied to another repository, needs an explicitly authorized first production deployment, or has orphaned preview Workers that should be cleaned safely without touching production.
---

# Manage Cloudflare Worker Deployments

Create one disposable Cloudflare Worker per non-protected Git branch. Keep production deployment separately configured and manually gated. Delete only Workers whose names match the reserved preview prefix.

## Start with discovery

Inspect the target repository before writing:

1. Resolve the repository root, default branch, current Git status, package manager, install command, verification command, build command, Wrangler config, Worker application directory, and non-production Wrangler environment.
2. Identify every permanent Worker name, protected branch, production binding, and shared stateful resource.
3. Determine the account `workers.dev` subdomain and choose an account-wide unique preview prefix.
4. Inspect existing workflows and preserve unrelated or uncommitted changes.
5. Read [references/settings.md](references/settings.md) before choosing token permissions, forced deletion, Durable Object handling, or the verification sequence.

Do not infer production authorization from a request for branch previews.

## Choose the deployment model

Prefer native Cloudflare version Preview URLs when they satisfy the application. Use real branch Workers when the user requests isolated Worker names or the application implements a feature that version Preview URLs do not support, such as Durable Objects.

Keep these boundaries:

- Deploy only non-protected branches.
- Bind only non-production D1, R2, KV, Durable Objects, auth, payments, webhooks, and secrets.
- List every permanent Worker in `protectedWorkers`.
- Reserve `workerPrefix` exclusively for disposable branch Workers.
- Keep production deployment in a separate workflow.

When the user explicitly requests the initial production deployment, configure a named Wrangler `production` environment and the manual production workflow. Never make production deployment a side effect of preview installation or a non-protected branch push.

## Install the template

Use the bundled installer from the target repository root. It previews changes unless `--apply` is present:

```sh
python3 /path/to/skill/scripts/install.py \
  --repo . \
  --worker-prefix example-preview \
  --workers-dev-subdomain example-account \
  --protected-worker example-production \
  --production-worker example-production \
  --wrangler-cwd apps/platform \
  --wrangler-environment development \
  --production-environment production
```

Choose commands explicitly when repository inference is unsuitable:

```sh
python3 /path/to/skill/scripts/install.py \
  --repo . \
  --worker-prefix example-preview \
  --workers-dev-subdomain example-account \
  --protected-worker example-production \
  --production-worker example-production \
  --install-command "bun install --frozen-lockfile" \
  --verify-command "bun run verify" \
  --build-command "bun run build" \
  --wrangler-command "bunx wrangler" \
  --wrangler-cwd apps/platform \
  --wrangler-environment development \
  --production-environment production \
  --apply
```

Never use `--overwrite` without first reviewing the exact existing files and preserving user changes.
`--apply` uses POSIX no-follow directory-descriptor writes; on hosts without an equivalent
primitive it fails closed without writing. Dry-run remains available on every host.

The installer creates:

```text
.cloudflare/branch-workers.json
.github/workflows/cloudflare-branch-workers.yml
.github/workflows/cloudflare-production.yml
scripts/cloudflare-branch-worker.mjs
scripts/cloudflare-branch-worker.test.mjs
```

The production workflow is created only when `--production-worker` is supplied. The production Worker must also be passed through `--protected-worker`.

Add the dependency-free test to the repository's normal verification command when practical.

## Configure safely

Review `.cloudflare/branch-workers.json` after installation:

- Align `protectedBranches` with the workflow's `push.branches-ignore`.
- Include production, staging, shared development, and other permanent Worker names in `protectedWorkers`.
- Keep `delete.force` false by default.
- Enable forced deletion only when the generated branch Worker owns isolated disposable Durable Object state and no permanent Worker depends on it.
- Point `wrangler.environment` only at a non-production environment with `workers_dev=true`.
- Keep `production.workerName` in `protectedWorkers`, outside `workerPrefix`, and point `production.environment` at the named production Wrangler environment.
- Add a post-deployment smoke command through `afterDeploy` when the repository has one.

Do not place Cloudflare tokens or other secret values in files, logs, plans, or responses.

## Configure production explicitly

When production is authorized:

1. Add `env.production` to `wrangler.jsonc` or the repository's existing Wrangler config.
2. Set production routes, custom domains, vars, and every non-inheritable binding explicitly. Never copy preview resource identifiers into production without verification.
3. Keep the configured production Worker name in `protectedWorkers`.
4. Create or review the GitHub Environment named by `--github-production-environment` (default `production`). Add required reviewers when supported.
5. Run `node scripts/cloudflare-branch-worker.mjs production-plan`.
6. Validate with Wrangler's dry-run or check command supported by the repository.
7. Trigger `Cloudflare production Worker` manually and enter `deploy-production`.

The production workflow must run only when manually dispatched from the repository's
default branch. Keep a job-level guard that compares `github.ref` with
`refs/heads/${{ github.event.repository.default_branch }}` and check out the event's
trusted `github.sha`, rather than an arbitrary dispatch ref. Do not automatically
trigger this workflow on a default-branch push. The first production deployment
remains an explicit action. Treat the Wrangler configuration as the source of truth
and regenerate Worker binding types after changing environments when the project uses
generated types.

## Configure GitHub

Create:

- Actions secret `CLOUDFLARE_API_TOKEN`.
- Actions variable `CLOUDFLARE_ACCOUNT_ID`.
- GitHub Environment `production` or the configured equivalent when installing the production workflow.
- Restrict that GitHub Environment's deployment branch/tag policy to the repository's default branch.

Scope the token to the intended account and minimum required resources. Add read permissions for bound D1, R2, KV, or other resources only when Wrangler must validate them during deployment.

Merge the workflow, configuration, and trusted cleanup script into the repository's default branch before relying on branch deletion. GitHub loads the `delete` workflow from the default branch; a workflow that exists only on the branch being deleted will not run.

Do not expose deployment secrets to fork pull requests. Keep same-repository branch code review and default-branch protection enabled because collaborators can change deployment scripts.

## Verify the lifecycle

Use this order:

1. Run the installer without `--apply` and review every destination.
2. Run:

   ```sh
   node --test scripts/cloudflare-branch-worker.test.mjs
   node scripts/cloudflare-branch-worker.mjs plan feature/preview-test
   ```

3. Run the repository's verification and development build.
4. If production is configured, run `production-plan`, validate the production Wrangler environment, and review the manual workflow without triggering it.
5. Confirm the workflows and cleanup script exist on the default branch.
6. When explicitly authorized, manually deploy production once and verify its routes, bindings, and Worker name.
7. Push a disposable non-protected branch and wait for its deployment run.
8. Verify the emitted Worker name, `workers.dev` URL, meaningful application routes, browser console, and non-production bindings.
9. Delete the disposable branch.
10. Verify the GitHub `delete` run succeeds, Cloudflare reports the Worker absent, and cache-busted application routes return 404.

If deletion occurs during a deployment, allow the shared concurrency group to serialize deployment and cleanup. Do not call the delay a cleanup failure while the earlier run still owns the group.

## Handle failures

- No cleanup run after branch deletion: confirm the workflow exists on the default branch and the event is `delete` with `ref_type=branch`.
- Cleanup run waits: inspect the same concurrency group for an active deployment.
- Worker lookup succeeds after cleanup: inspect the cleanup log, token scope, generated name, prefix guard, and protected name guard.
- Wrangler rejects D1 or R2 lookup: add only the necessary resource read permission to the GitHub Actions token.
- Worker deletion is blocked by Durable Objects: verify state isolation before considering `delete.force=true`.
- Homepage loads but other routes return 404 after cleanup: treat the homepage as stale edge cache and confirm Worker existence through the Cloudflare API.

Never broaden deletion to account-wide Workers, production names, shared storage, the repository, or the user home directory.

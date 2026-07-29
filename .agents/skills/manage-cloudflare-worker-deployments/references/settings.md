# Settings and safety reference

## Contents

- Lifecycle contract
- Configuration fields
- GitHub workflow events
- Production bootstrap
- Cloudflare token permissions
- Durable Objects and forced deletion
- Verification checklist
- Official references

## Lifecycle contract

| Repository event | Expected result |
|---|---|
| Push to a non-protected branch | Verify, build, create or update its deterministic branch Worker |
| Reopen a same-repository pull request | Recreate its Worker if cleanup already removed it |
| Delete a branch | Delete only its deterministic branch Worker |
| Close or merge a same-repository pull request | Delete only its deterministic branch Worker |
| Push to the default branch | Do not deploy a branch Worker |
| Manually confirm the production workflow | Verify, build, and deploy only the configured protected production Worker |

Use this deterministic Worker name:

```text
<workerPrefix>-<sanitized-branch>-<first-8-characters-of-sha256(branch)>
```

The hash prevents collisions between branch names that sanitize to the same value.

## Configuration fields

| Field | Requirement |
|---|---|
| `workerPrefix` | Account-wide unique prefix reserved for disposable Workers |
| `protectedBranches` | Include the default branch and any long-lived branch that must not create a preview |
| `protectedWorkers` | Include production, staging, shared development, and other permanent Worker names |
| `maxWorkerNameLength` | Keep between 24 and 63; 48 is a conservative default |
| `workersDevSubdomain` | Cloudflare account `workers.dev` subdomain |
| `install` | Dependency installation command and working directory |
| `verify` | Repository verification command and working directory |
| `build` | Development Worker build command and working directory |
| `wrangler.command` | Pinned `npx wrangler`, `bunx wrangler`, or equivalent command |
| `wrangler.cwd` | Directory containing the Worker application |
| `wrangler.environment` | Non-production Wrangler environment |
| `wrangler.config` | Optional Wrangler config path |
| `production.workerName` | Optional permanent production Worker; must appear in `protectedWorkers` and remain outside `workerPrefix` |
| `production.environment` | Named Wrangler production environment; must differ from the preview environment |
| `production.config` | Optional production Wrangler config path; defaults to `wrangler.config` |
| `afterDeploy` | Optional smoke or preview-secret setup command |
| `delete.force` | Keep false unless branch Durable Object state is isolated and disposable |

Keep `workers_dev=true` in the selected Wrangler environment. The generated Worker receives a normal:

```text
https://<generated-worker>.<workersDevSubdomain>.workers.dev
```

Do not use another Worker's version Preview URL as the branch URL.

## GitHub workflow events

Use:

```yaml
on:
  push:
    branches-ignore:
      - main
  delete:
  pull_request:
    types:
      - reopened
  pull_request_target:
    types:
      - closed
```

The `delete` event only starts a workflow whose file exists on the default branch. Merge the trusted cleanup script, its configuration, and the workflow into the default branch before testing automatic cleanup.

Use the same concurrency key for deploy and cleanup. Keep deployment `cancel-in-progress: true` and cleanup `cancel-in-progress: false`. A cleanup run may wait while an already-running deployment owns that key, then delete the Worker.

Skip fork pull-request deployment. GitHub does not provide repository deployment secrets to untrusted fork code.

## Production bootstrap

Create `.github/workflows/cloudflare-production.yml` only when the user explicitly requests a production deployment. Keep it separate from branch lifecycle events and use:

```yaml
on:
  workflow_dispatch:
```

Require the operator to enter `deploy-production`, use a GitHub Environment such as `production`, serialize production runs, and keep `cancel-in-progress: false`.

Define `env.production` in the Wrangler configuration. Bindings such as `vars`, D1, R2, KV, Durable Objects, services, and other environment-specific resources may not inherit; review and declare them explicitly. Configure production routes or custom domains in that environment when applicable.

For a new JSONC configuration, use this shape and replace every binding and route with reviewed project values:

```jsonc
{
  "$schema": "./node_modules/wrangler/config-schema.json",
  "name": "example",
  "main": "src/index.ts",
  "compatibility_date": "YYYY-MM-DD",
  "env": {
    "development": {
      "workers_dev": true,
      "vars": { "ENVIRONMENT": "development" }
    },
    "production": {
      "name": "example-production",
      "workers_dev": false,
      "routes": ["example.com/*"],
      "vars": { "ENVIRONMENT": "production" }
    }
  }
}
```

Before the first deployment:

- Verify `production.workerName` is a permanent name in `protectedWorkers`.
- Verify it does not start with the disposable preview prefix.
- Run `node scripts/cloudflare-branch-worker.mjs production-plan`.
- Validate the selected Wrangler configuration and generate binding types when used by the project.
- Review routes, secrets, migrations, and stateful bindings.
- Trigger the production workflow manually from the trusted default branch.
- Verify meaningful routes, logs, bindings, and the deployed Worker identity.

The branch cleanup command derives a Worker name from the branch and rejects names outside `workerPrefix`; it never accepts the configured production Worker as a deletion target.

## Cloudflare token permissions

Create a dedicated account API token for GitHub Actions. Start with:

- Workers Scripts: Write.
- Account Settings: Read when Wrangler needs account metadata.

Add only the resource read permissions Wrangler requires to validate configured bindings, for example:

- Workers R2 Storage: Read.
- D1: Read.
- KV Storage: Read.

Do not grant production resource access merely because the account contains production resources. Store:

- Token in GitHub Actions secret `CLOUDFLARE_API_TOKEN`.
- Account ID in GitHub Actions variable `CLOUDFLARE_ACCOUNT_ID`.

Never commit either value.

## Durable Objects and forced deletion

Cloudflare version Preview URLs are not suitable for Workers that implement Durable Objects. A real per-branch Worker gives the branch a normal Worker URL and its own Worker identity.

`delete.force=true` is destructive. It can remove associated Durable Object state and affect dependent Workers. Enable it only after all of these are true:

- The Worker name matches the reserved preview prefix.
- The Worker is not in `protectedWorkers`.
- The Durable Object namespace belongs only to that branch Worker.
- No permanent Worker has a service or Durable Object binding to it.
- Losing its state is an accepted part of branch cleanup.

Shared D1 and R2 bindings are references. Deleting a Worker must not delete those databases or buckets.

## Verification checklist

- Working tree inspected and unrelated changes preserved.
- Installer dry-run reviewed.
- Generated Worker name starts with the reserved prefix.
- Default and protected branches rejected by the lifecycle script.
- Permanent Worker names rejected by the delete guard.
- Dependency-free tests pass.
- Repository verification and build pass.
- Workflow exists on the default branch.
- Production plan names only a protected permanent Worker.
- Production Wrangler environment has explicit production bindings and routes.
- First production deployment is manually confirmed and verified when authorized.
- Branch deployment run succeeds.
- Meaningful Preview routes return 200.
- Preview browser console has no relevant errors.
- Bindings point only to non-production resources.
- Branch deletion creates a GitHub `delete` run.
- Cleanup step succeeds.
- Cloudflare Worker lookup returns not found.
- Cache-busted Preview routes return 404.
- Production Worker and shared storage remain present.

## Official references

- Cloudflare Preview URL limitations: https://developers.cloudflare.com/workers/configuration/previews/
- Cloudflare Wrangler commands: https://developers.cloudflare.com/workers/wrangler/commands/
- Cloudflare Wrangler environments: https://developers.cloudflare.com/workers/wrangler/environments/
- Cloudflare CI environment variables: https://developers.cloudflare.com/workers/wrangler/system-environment-variables/
- GitHub Actions events: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows

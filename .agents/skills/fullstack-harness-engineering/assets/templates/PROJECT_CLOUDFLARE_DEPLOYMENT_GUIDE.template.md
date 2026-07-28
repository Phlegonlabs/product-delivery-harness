# Cloudflare Deployment Setup Guide

One-time operational record of how this project's Cloudflare Workers are configured. Fill in every `<placeholder>` with the real value as Day One Resource Creation happens (see the Full-Stack Harness's `references/cloudflare-deployment-lifecycle.md`). Update this file whenever the deployment topology changes. It is the human source for Cloudflare-specific Worker, environment, config, and resource identity. PLAN-v5 keeps provider-neutral release targets, while RUN-v10 `targets` keyed by those stable PLAN target IDs remain the canonical machine-readable execution record.

## Environments

The default model runs one environment, published from the protected base. Add the preview row only when this project actually keeps a separate non-production environment.

| Environment | Worker name | Wrangler environment | Deployed URL |
|---|---|---|---|
| Production | `<worker-name>-production` | `production` | `<url>` |
| Preview (optional) | `<worker-name>-development` | `development` | `<url>` |

## Resource Bindings (isolated per environment)

Only needed when this project keeps a preview environment alongside production.

| Binding | Type | Preview resource ID/name | Production resource ID/name |
|---|---|---|---|
| `<binding name>` | D1 / KV / R2 / Durable Object / Queue | `<id>` | `<id>` |

Confirm with `scripts/check_wrangler_binding_isolation.py --wrangler-config <path>` that no row shares the same ID between environments.

## Deployment Trigger Model

<Name which model this project uses: "Dispatched-Actions (default)" or "Auto-Deploy Release Model (alternative)", and why.>

### If Dispatched-Actions Model

- GitHub Environments to configure: `cloudflare-production`, plus `cloudflare-development` only when a preview environment exists.
- Secrets required on each: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.
- Workflow file: `.github/workflows/<deploy-workflow-name>.yml` (scaffolded from `PROJECT_CLOUDFLARE_DEPLOY.template.yml`).
- How to trigger: <describe the exact dispatch mechanism, e.g. a workflow_dispatch input naming the target environment and source SHA>.

### If Auto-Deploy Release Model

- Production Worker's Cloudflare dashboard Git connection watches branch: `<resolved-protected-base-branch>`.
- A preview Worker, when one exists, watches its own `<resolved-integration-branch>`.
- Deploy command per environment: `wrangler deploy --env production` (and `--env development` for a preview environment).
- Non-production branch deploy command (any other branch): `wrangler versions upload` (default; uploads a version without promoting it live).
- Confirm `<resolved-protected-base-branch>` is protected from direct pushes. A preview Worker additionally needs `run.integration.retention` set to `"persistent"` so its watched branch is not deleted between runs.

## Custom Domains

| Environment | Domain |
|---|---|
| `<environment>` | `<domain, or "none">` |

## Account Access

- Cloudflare account ID: `<value, or "see GitHub Environment secret">`.
- Who has dashboard access: `<names/roles>`.

## Last Verified

`<date>` — `<what was checked, e.g. "wrangler whoami succeeded locally; both Workers visible in the Cloudflare dashboard; check_wrangler_binding_isolation.py passed">`

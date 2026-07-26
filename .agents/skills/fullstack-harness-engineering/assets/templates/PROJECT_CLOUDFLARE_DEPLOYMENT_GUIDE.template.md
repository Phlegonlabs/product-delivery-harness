# Cloudflare Deployment Setup Guide

One-time operational record of how this project's Cloudflare Workers are configured. Fill in every `<placeholder>` with the real value as Day One Resource Creation happens (see the Full-Stack Harness's `references/cloudflare-deployment-lifecycle.md`). Update this file whenever the deployment topology changes. It is the human source for Cloudflare-specific Worker, environment, config, and resource identity. PLAN-v5 keeps provider-neutral release targets, while RUN-v10 `targets` keyed by those stable PLAN target IDs remain the canonical machine-readable execution record.

## Environments

| Environment | Worker name | Wrangler environment | Deployed URL |
|---|---|---|---|
| Development | `<worker-name>-development` | `development` | `<url>` |
| Production | `<worker-name>-production` | `production` | `<url>` |

## Resource Bindings (isolated per environment)

| Binding | Type | Development resource ID/name | Production resource ID/name |
|---|---|---|---|
| `<binding name>` | D1 / KV / R2 / Durable Object / Queue | `<id>` | `<id>` |

Confirm with `scripts/check_wrangler_binding_isolation.py --wrangler-config <path>` that no row shares the same ID between environments.

## Deployment Trigger Model

<Name which model this project uses: "Dispatched-Actions (default)" or "Auto-Deploy Release Model (alternative)", and why.>

### If Dispatched-Actions Model

- GitHub Environments to configure: `cloudflare-development`, `cloudflare-production`.
- Secrets required on each: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`.
- Workflow file: `.github/workflows/<deploy-workflow-name>.yml` (scaffolded from `PROJECT_CLOUDFLARE_DEPLOY.template.yml`).
- How to trigger: <describe the exact dispatch mechanism, e.g. a workflow_dispatch input naming the target environment and source SHA>.

### If Auto-Deploy Release Model

- Development Worker's Cloudflare dashboard Git connection watches branch: `development`.
- Production Worker's Cloudflare dashboard Git connection watches branch: `production`.
- Deploy command per environment: `wrangler deploy --env development` / `wrangler deploy --env production`.
- Non-production branch deploy command (any other branch): `wrangler versions upload` (default; uploads a version without promoting it live).
- `run.integration.retention` must be `"persistent"` for this model — confirm `development` is not deleted between runs and `production` is protected from direct pushes.

## Custom Domains

| Environment | Domain |
|---|---|
| `<environment>` | `<domain, or "none">` |

## Account Access

- Cloudflare account ID: `<value, or "see GitHub Environment secret">`.
- Who has dashboard access: `<names/roles>`.

## Last Verified

`<date>` — `<what was checked, e.g. "wrangler whoami succeeded locally; both Workers visible in the Cloudflare dashboard; check_wrangler_binding_isolation.py passed">`

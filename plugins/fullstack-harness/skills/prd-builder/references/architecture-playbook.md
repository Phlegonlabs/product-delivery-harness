# Architecture Playbook

Use this playbook to make architecture sections implementation-ready. The overall architecture may remain stack-neutral where requirements do not justify a named choice. For products with a browser surface, record the required/selected frontend or make an evidence-backed recommendation as described in `frontend-stack-selection.md`. For products with a backend, persistent data, or auth requirement, apply the same decision-status discipline to the backend runtime, database, and auth layers as described in `references/backend-stack-selection.md`.

## Baseline Architecture Coverage

Every architecture should cover:

- Product archetype and target surfaces.
- Actors and external systems.
- Frontend or client responsibilities.
- For products with a browser frontend, frontend technology layers: deployment/runtime, rendering model, framework, UI library, build tool, routing/data approach, styling/component approach, and testing.
- For products with a backend, persistent data, or auth requirement, backend technology layers: runtime/framework, database category, database engine, auth strategy, auth provider, API style, background jobs/queue, and file/object storage.
- Backend, service, or workflow orchestration responsibilities.
- Data model and persistence.
- API, event, file, or trigger contracts.
- Authentication, authorization, and role boundaries.
- Security, privacy, secrets, and audit concerns.
- Integrations and failure handling.
- Deployment, environment configuration, migrations, and rollback.
- Observability, metrics, alerting, and audit logs.
- Scaling, reliability, idempotency, retries, and rate limits.

## Development-to-Production Release Pattern

For a deployable product, resolve the deployment platform explicitly (via the interview's platform `AskUserQuestion` step, the user, or the current repository) before writing this section — never default to one silently. Keep one repository and one codebase, then promote exact commits through two separately named environments. The table below uses Cloudflare's two-Worker model as the worked example; for another resolved platform, substitute its equivalent named per-environment unit (for example, separate Vercel project environments, separate AWS stacks or services, or separate self-hosted environment configs) while keeping the same isolation and evidence guarantees:

| Target | Release source | Runtime and data boundary | Required proof |
| --- | --- | --- | --- |
| Development | Current pull-request head after current-head CI | Development environment (Worker, for Cloudflare); isolated non-production bindings, secrets, data, auth, and sandbox payment credentials | Migration result when applicable, deployed URL/version, automated checks, and development smoke |
| Production | Exact merged base-branch SHA after development passes | Production environment (Worker, for Cloudflare); production bindings, secrets, data, auth, and live payment credentials | Migration result when applicable, deployed URL/version, production smoke, monitoring signal, and rollback version |

Do not model development as a second codebase or a long-lived development branch by default. Do not let a development environment access production customer data, production sessions, or live payment mutations. Specify promotion prerequisites, migration order, backward-compatibility needs, secret ownership, rollback, and which evidence becomes stale after a new commit or deployment.

Isolation does not mean development stays empty. When the product has content-shaped data (for example articles, images, or other catalog-style entities), seed the development environment with representative mock/sample data as part of the development migration or setup step, so development testing sees realistic content without ever reading real production records. Record the mock-data seed in the development row's Migration Order cell of the environment-contract table (see `references/output-contract.md`'s architecture.md template) or an equivalent setup step, and never source it from a live production copy unless the user explicitly authorizes and scopes that as a separate, deliberate sync/anonymization process. (If this PRD is later handed off to the fullstack-harness-engineering skill, that Migration Order entry is what becomes its PLAN release-target `migration_command` field.)

## Web App Pattern

Use for browser-based SaaS, marketplaces, dashboards, portals, and public web products.

- Frontend: routes, layout model, server/client rendering assumptions, form validation, state management, responsive behavior.
- Frontend decision: status (`Required`, `Selected`, `Recommended`, or `Provisional`), product-fit rationale, alternatives rejected, official-source verification date, runtime compatibility, and any spike needed to close uncertainty.
- Backend: API layer, business services, validation, background jobs, file handling, notifications.
- Data: relational entities by default for transactional products; include indexes, tenancy, soft delete, audit history, and retention when relevant.
- APIs: list core REST, GraphQL, RPC, or server action contracts; include pagination, filtering, validation errors, auth errors, and rate limits.
- Security: session management, CSRF when applicable, RBAC, tenant isolation, input validation, secure file upload, secrets handling.
- Operations: environments, database migrations, feature flags, scheduled jobs, queues, monitoring, rollback.

## Mobile App Pattern

Use for native or cross-platform iOS and Android products.

- Client: navigation structure, local state, offline behavior, push notifications, permissions, deep links, device capabilities.
- Backend: sync API, auth sessions, notification service, media upload, entitlement or subscription checks when relevant.
- Data: local cache, remote canonical records, conflict resolution, sync timestamps, deletion behavior.
- APIs: mobile-friendly payloads, versioning, pagination, retry-safe mutations, upload progress, token refresh.
- Security: secure storage, biometric or device auth if needed, PII minimization, jailbreak or rooted device assumptions only when required.
- Operations: app release channels, server compatibility windows, analytics, crash reporting, rollback limitations after app store release.

## Internal Tool Pattern

Use for admin panels, operations consoles, review queues, workflow tools, and back-office systems.

- Frontend: dense table views, filters, search, bulk actions, detail panels, audit trails, keyboard efficiency where useful.
- Backend: permissioned admin endpoints, approval workflows, import/export, background processing, audit logging.
- Data: operational records, user actions, review status, assignment, SLA timestamps, immutable audit entries.
- APIs: guarded mutations, bulk operation contracts, validation summaries, idempotency keys for destructive or repeat actions.
- Security: least-privilege roles, approval gates, PII masking, access review, comprehensive audit logs.
- Operations: queue visibility, retry tools, manual override policies, incident playbooks.

## Automation and Agent Workflow Pattern

Use for scheduled automations, event-triggered workflows, AI agents, data pipelines, and integration tools.

- Triggers: schedule, webhook, email, file drop, database change, manual run, or user command.
- Orchestration: workflow steps, state machine, queue, retry policy, timeout, cancellation, and human approval points.
- Tools and integrations: source system, destination system, auth method, scopes, rate limits, quotas, and sandbox behavior.
- Data: run records, step logs, input snapshots, generated outputs, idempotency keys, deduplication, and replay support.
- Safety: permission boundaries, dry-run mode, confirmation gates, prompt injection defenses for AI workflows, output validation.
- Failure handling: partial success, retryable and non-retryable errors, dead-letter queue, alerting, resume, rollback or compensating actions.
- Observability: run history, step-level logs, latency, success rate, cost, token or API usage, integration error rates.

## API or Backend Service Pattern

Use when the product is mainly a service consumed by other systems.

- Interfaces: endpoints, events, SDK boundaries, authentication, versioning, rate limits, and error taxonomy.
- Domain services: validation, authorization, business rules, consistency boundaries, transaction design.
- Data: canonical entities, migrations, indexing, archival, retention, encryption, and backup.
- Operations: SLOs, capacity, autoscaling, deploy strategy, backward compatibility, observability, and incident response.

## Decision Guidance

- Prefer the simplest architecture that satisfies the stated workflows and constraints.
- Call out tradeoffs when choosing between synchronous requests, background jobs, event-driven design, or scheduled processing.
- Specify idempotency for payment, notification, import, workflow, and external mutation flows.
- Specify authorization at both UI and backend layers.
- For a browser frontend, backend, persistent data, or auth requirement, name the required/selected stack or a recommended stack when requirements support a decision; do not leave the implementer to reinterpret a flat list of tools or present a recommendation as user-approved.
- Treat platform, rendering, framework, UI library, and build tooling as separate decisions. For example, `Cloudflare Workers + React + Vite` is a coherent stack; `Cloudflare vs Astro vs Vite vs React` is not a coherent comparison.
- For Cloudflare delivery, name separate development and production Workers even though both use the same codebase. Define isolated bindings, secrets, data, auth, and payment modes plus the exact PR-head-to-merged-main promotion path.
- Avoid naming other vendors unless the user specified one, the current environment requires it, or a documented tradeoff makes the recommendation materially more useful.

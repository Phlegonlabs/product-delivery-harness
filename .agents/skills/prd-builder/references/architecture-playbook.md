# Architecture Playbook

Use this playbook to make architecture sections implementation-ready. The overall architecture may remain stack-neutral where requirements do not justify a named choice. For products with a browser surface, record the required/selected frontend or make an evidence-backed recommendation as described in `frontend-stack-selection.md`.

## Baseline Architecture Coverage

Every architecture should cover:

- Product archetype and target surfaces.
- Actors and external systems.
- Frontend or client responsibilities.
- For products with a browser frontend, frontend technology layers: deployment/runtime, rendering model, framework, UI library, build tool, routing/data approach, styling/component approach, and testing.
- Backend, service, or workflow orchestration responsibilities.
- Data model and persistence.
- API, event, file, or trigger contracts.
- Authentication, authorization, and role boundaries.
- Security, privacy, secrets, and audit concerns.
- Integrations and failure handling.
- Deployment, environment configuration, migrations, and rollback.
- Observability, metrics, alerting, and audit logs.
- Scaling, reliability, idempotency, retries, and rate limits.

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
- For a browser frontend, name the required/selected stack or a recommended stack when requirements support a decision; do not leave the implementer to reinterpret a flat list of tools or present a recommendation as user-approved.
- Treat platform, rendering, framework, UI library, and build tooling as separate decisions. For example, `Cloudflare Workers + React + Vite` is a coherent stack; `Cloudflare vs Astro vs Vite vs React` is not a coherent comparison.
- Avoid naming other vendors unless the user specified one, the current environment requires it, or a documented tradeoff makes the recommendation materially more useful.

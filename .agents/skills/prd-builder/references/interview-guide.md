# Interview Guide

Ask a full product interview before drafting artifacts unless the user explicitly permits assumptions or asks to skip discovery. Keep the interview concise, grouped, and practical.

## Interview Structure

Ask only questions that are not already answered.

1. Product goal
   - What problem should this solve?
   - Who is the primary user or buyer?
   - What outcome would make this successful?
2. Users and roles
   - Which user roles need access?
   - What permissions or approval levels are required?
   - Are there admin, operator, customer, or viewer roles?
3. Core workflows
   - What are the top 3 user workflows?
   - What starts each workflow?
   - What is the successful end state?
4. Product surface
   - Should this be web, mobile app, internal tool, automation or agent workflow, API, or a hybrid?
   - Which platforms, devices, or channels matter?
   - Are there accessibility, localization, or offline requirements?
5. Data and integrations
   - What data does the product create, read, update, or delete?
   - What third-party systems, APIs, files, emails, calendars, CRMs, payment providers, or databases are involved?
   - What data freshness and retention expectations apply?
6. Business rules
   - What rules, thresholds, calculations, approvals, or eligibility logic matter?
   - What must never happen?
   - What compliance, audit, or policy constraints apply?
7. UX expectations
   - What screens, dashboards, forms, or notifications are expected?
   - What should users see when there is no data, a long-running job, a validation error, or a permission issue?
   - Are there known design references or brand constraints?
8. Architecture constraints
   - Is there a required stack, hosting environment, database, auth provider, or existing system?
   - Are there latency, scale, reliability, security, or cost constraints?
   - Does the product need observability, audit logs, background jobs, or queueing?
9. Delivery constraints
   - What is in scope for v1?
   - What is explicitly out of scope?
   - What timeline, milestone, or team constraint should shape the implementation plan?
10. Success and validation
   - Which metrics define launch success?
   - Which acceptance tests must pass before release?
   - What risks or unknowns should the team investigate first?

## Completeness Criteria

Discovery is complete enough to draft when the agent can state:

- The user, buyer, and primary problem.
- The product archetype and target surfaces.
- The top workflows and expected end states.
- The core data objects and integrations.
- The v1 scope, non-goals, and constraints.
- The architecture assumptions and high-risk unknowns.
- The UI screens or interaction points that need wireframes.
- The success metrics and acceptance criteria.

If any item is missing and the user did not authorize assumptions, ask follow-up questions before drafting.

## Assumption Mode

If the user asks for a first draft without more questions:

- State that assumptions are being used.
- Add an `Assumptions` section to every artifact where relevant.
- Add unresolved items to `Open Questions`.
- Avoid inventing named vendors, frameworks, compliance requirements, or pricing unless the prompt strongly implies them.

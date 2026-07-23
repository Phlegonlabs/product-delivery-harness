# Interview Guide

Ask a full product interview before drafting artifacts unless the user explicitly permits assumptions or asks to skip discovery. Keep the interview concise, grouped, and practical.

Bullets marked `(AskUserQuestion)` are a closed, enumerable set — resolve them with Claude Code's `AskUserQuestion` tool immediately after the free-text interview message, not as open questions inside it. Everything else stays free text, since it is too product-specific or too action-specific to enumerate.

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
   - Should this be web, mobile app, desktop app, internal tool, automation or agent workflow, API, or a hybrid? (AskUserQuestion)
   - If the answer is mobile app, which mobile platform: native iOS, native Android, Flutter (cross-platform), React Native (cross-platform), or undecided and need a recommendation? (AskUserQuestion) When the answer is undecided, resolve the recommendation with `mobile-stack-selection.md`, the same way the browser frontend choice follows `frontend-stack-selection.md`.
   - If the answer is desktop app, which desktop platform: macOS, Windows, cross-platform (e.g. Electron or Tauri), or undecided and need a recommendation? (AskUserQuestion)
   - Which platforms, devices, or channels matter?
   - Are there accessibility, localization, or offline requirements?
5. Data and integrations
   - What data does the product create, read, update, or delete?
   - What third-party systems, APIs, files, emails, calendars, CRMs, payment providers, or databases are involved?
   - What data freshness and retention expectations apply?
   - What category of persistence does this data need: relational (structured records, joins, transactions), document (flexible/nested records), key-value or cache only, or no persistent database? (AskUserQuestion)
6. Business rules
   - What rules, thresholds, calculations, approvals, or eligibility logic matter?
   - What must never happen?
   - What compliance, audit, or policy constraints apply?
7. UX expectations
   - Who is the builder or human product/design decision owner for the UX direction?
   - What should the experience optimize first: speed, clarity, guided completion, expert control, exploration, conversion, or content comprehension? (AskUserQuestion)
   - Should the product be guided or flexible, sparse or information-dense, and familiar or deliberately expressive? Which primary layout pattern does the builder prefer, and why does it fit the user's task? (AskUserQuestion)
   - Which actions require confirmation, undo, recovery, progress feedback, or human intervention? Ask this as free text — it varies too much by action to enumerate.
   - What validation depth does the builder expect: documented assumptions, internal prototype review, testing with likely users, or recurring usability benchmarking? (AskUserQuestion)
   - What screens, dashboards, forms, or notifications are expected?
   - What should users see when there is no data, a long-running job, a validation error, or a permission issue?
   - What overall visual character should the finished interface convey? Ask the user to choose or describe a direction instead of assuming one. Offer compact examples only when useful: modern minimal, editorial, utilitarian and dense, warm and human, bold and expressive, or an existing brand reference. (AskUserQuestion, using modern minimal / editorial / utilitarian and dense / warm and human as the four options and the tool's built-in Other for bold and expressive or a brand reference)
   - If the answer is only `modern`, which concrete cues should define it: sparse or dense information, generous or compact spacing, quiet or expressive typography, restrained or vivid color, product imagery, and formal or friendly interaction tone?
   - Are there known design references or brand constraints?
   - Which headings, body copy, labels, CTAs, legal text, and state messages already have approved wording? For the rest, what must each region display or communicate?
   - Which regions need a specific style direction or animation, and what should that treatment communicate about hierarchy, meaning, or action?
   - For a landing page, what single message and primary action belong in the first viewport, and which details can be deferred?
   - Which regions require an image, product media, video, or animation, and what should each help the user understand or do?
8. Architecture constraints
   - Is there a required stack, hosting environment, database, auth provider, or existing system?
   - What auth strategy should this product use: build custom authentication, a managed third-party provider (e.g., Auth0, Clerk, WorkOS), a platform-native provider (e.g., Cloudflare Access, AWS Cognito), or no auth needed? (AskUserQuestion)
   - For a deployable web product, which deployment platform should this use: Cloudflare, Vercel, AWS, or self-hosted? (AskUserQuestion, unless the user's prompt or the current repository already names one) — ask this only when the resolved product surface is web, or a hybrid that includes a web surface. It does not apply to a native iOS, native Android, Flutter, macOS, or Windows target, whose release path is an app store or a signed installer rather than a web host; for those, resolve distribution with the matching platform pattern in `architecture-playbook.md` instead of asking this question.
   - For a browser frontend, is the product primarily content-led, interaction-led, or a mixture? Which routes require SEO, static generation, server rendering, authenticated personalization, or SPA behavior?
   - If the platform is Cloudflare, does the frontend need Cloudflare Workers bindings or APIs such as D1, KV, R2, Durable Objects, Queues, Workflows, or Workers AI? For another platform, note the equivalent platform-managed services it needs.
   - Which team skills, existing components, package constraints, browser targets, and build/deployment workflows should shape the frontend choice?
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
- For products with a browser frontend, the content/interactivity profile, rendering needs, deployment constraints, and evidence needed to recommend a stack.
- For products with a backend, persistent data, or auth requirement, the resolved database category and auth strategy, and the evidence needed to recommend a backend framework, database engine, and auth provider.
- The UI screens or interaction points that need wireframes.
- A Builder UX Direction Decision naming the human decision owner, experience priority, guidance/control balance, information density, preferred layout/interaction pattern, recovery expectations, and validation depth. Each decision is `selected`, `provisional`, or `assumed`.
- Approved or draft exact wording and bounded display responsibilities for wireframed regions, or permission to derive them.
- The requested overall interface style, or permission to record `modern-minimal` as a provisional assumption.
- Required style and motion intent for visually important regions, or permission to derive it.
- The success metrics and acceptance criteria.

If any item is missing and the user did not authorize assumptions, ask follow-up questions before drafting.

## Enhancement Mode

When `docs/PRD.md` (or another document clearly describing the same product) already exists, this run enhances it instead of starting fresh. Read the existing package in full first, then run a delta interview:

- Ask only about the categories above that the new idea actually adds to, changes, or leaves unresolved.
- Do not re-ask a question the existing package already answers; carry that answer forward unchanged.
- When the new idea adds a mobile or desktop target to a product that previously had only a web target (or, conversely, adds a web target to a previously mobile/desktop-only product), always re-trigger the platform-selection question (the mobile/desktop platform `AskUserQuestion` steps in this guide, "Product surface" lines 25-26) for the NEW target specifically. This holds even though the existing target's already-answered platform question is carried forward unchanged, per the "do not re-ask what's already answered" rule above — the new target has no answer yet, so it must be asked.
- If the new idea conflicts with an existing decision, surface the conflict explicitly and ask which should win instead of silently overwriting it.

## Assumption Mode

If the user asks for a first draft without more questions:

- State that assumptions are being used.
- Add an `Assumptions` section to every artifact where relevant.
- Add unresolved items to `Open Questions`.
- Record missing builder UX choices as `assumed`, never as selected or user-validated. Builder preference alone is not usability evidence.
- Do not invent compliance requirements or pricing. A named frontend recommendation is allowed when it follows `frontend-stack-selection.md`, is supported by the known requirements, and clearly identifies assumptions and alternatives.

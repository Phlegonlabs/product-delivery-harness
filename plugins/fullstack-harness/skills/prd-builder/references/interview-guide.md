# Interview Guide

Ask a full product interview before drafting artifacts unless the user explicitly permits assumptions or asks to skip discovery. Keep the interview concise, grouped, and practical.

Bullets marked `(AskUserQuestion)` are a closed, enumerable set — resolve them with Claude Code's `AskUserQuestion` tool immediately after the free-text interview message, not as open questions inside it. Everything else stays free text, since it is too product-specific or too action-specific to enumerate.

The closed-set questions fit three `AskUserQuestion` calls of at most four questions each, in this order:

1. The decisions that depend on no other answer: product archetype and validation depth.
2. For a UI-bearing product, the four closed Builder UX Direction dimensions: experience priority, guidance versus expert control, information density, and preferred layout/interaction pattern.
3. The decisions that depend on call 1's archetype answer: deployment platform, the mobile or desktop platform follow-up, database category, and auth strategy.

Never ask a call-3 question in call 1. The product surface is still unknown there, so the answer can be about a platform the product does not have — and a wrong deployment platform then freezes a wrong environment contract into `architecture.md`.

Every call-3 question carries a skip rule, so a real run asks fewer than four. Only a hybrid spanning web, mobile, and desktop surfaces with a backend leaves all five unresolved. Drop in this order rather than opening a fourth call, and resolve the dropped question as an explicit `Recommended` decision per `mobile-stack-selection.md`, never as `Selected`:

1. Desktop platform — recommend one desktop target and record it as `Recommended`.
2. Mobile platform — recommend one mobile stack and record it as `Recommended`.

Deployment platform, database category, and auth strategy never drop. Each has no documented default to fall back on, and guessing one silently freezes the wrong environment contract into `architecture.md`, or the wrong store or identity boundary into `stack-decisions.md`.

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
   - If the answer is mobile app, which mobile platform: native iOS, native Android, Flutter (cross-platform), React Native (cross-platform), or undecided and need a recommendation? (AskUserQuestion, in call 3, since it depends on the archetype answer; first to drop after the desktop follow-up when the closed-set budget is full) Skip it when the user's prompt, the existing package, or the current repository already names the mobile platform. When the answer is undecided or the question was dropped, resolve the recommendation with `mobile-stack-selection.md`, the same way the browser frontend choice follows `frontend-stack-selection.md`.
   - If the answer is desktop app, which desktop platform: macOS, Windows, cross-platform (e.g. Electron or Tauri), or undecided and need a recommendation? (AskUserQuestion, in call 3, since it depends on the archetype answer; first to drop when the closed-set budget is full) Skip it when the user's prompt, the existing package, or the current repository already names the desktop platform. When the answer is undecided or the question was dropped, resolve the recommendation with `mobile-stack-selection.md`.
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
   - Do not ask the user to choose from a fixed catalog of high-fidelity visual styles in this interview. Record known brand references, constraints, and product-specific visual goals. The design-system step derives the visual direction from those inputs per `references/design-system-guide.md`; when an exploration is explicitly authorized, `frontend-design`'s Purpose, Tone, Constraints, and Differentiation criteria derive the preference choices dynamically instead of a fixed menu.
   - Are there known design references or brand constraints?
   - Which headings, body copy, labels, CTAs, legal text, and state messages already have approved wording? For the rest, what must each region display or communicate?
   - Which regions need a specific style direction or animation, and what should that treatment communicate about hierarchy, meaning, or action?
   - For a landing page, what single message and primary action belong in the first viewport, and which details can be deferred?
   - Which regions require an image, product media, video, or animation, and what should each help the user understand or do?
8. Architecture constraints
   - Is there a required stack, hosting environment, database, auth provider, or existing system?
   - What auth strategy should this product use: build custom authentication, a managed third-party provider (e.g., Auth0, Clerk, WorkOS), a platform-native provider (e.g., Cloudflare Access, AWS Cognito), or no auth needed? (AskUserQuestion)
   - For a deployable web, API, or hosted backend target, which deployment platform should this use: Cloudflare, Vercel, AWS, or self-hosted? (AskUserQuestion, in call 3, unless the user's prompt or the current repository already names one) Use the built-in Other option to record an explicit stage-to-provider mapping when development and production differ. Ask this only when the resolved product surface includes a hosted web/API/backend surface, which is why it belongs in call 3 and never in the same batch as the product-surface question. It does not apply to a native iOS, native Android, Flutter, macOS, or Windows target, whose release path is an app store or a signed installer rather than a web host; for those, resolve distribution with the matching platform pattern in `architecture-playbook.md` instead of asking this question.
   - For a browser frontend, is the product primarily content-led, interaction-led, or a mixture? Which routes require SEO, static generation, server rendering, authenticated personalization, or SPA behavior?
   - If the platform is Cloudflare, does the frontend need Cloudflare Workers bindings or APIs such as D1, KV, R2, Durable Objects, Queues, Workflows, or Workers AI? For another platform, note the equivalent platform-managed services it needs.
   - Which team skills, existing components, package constraints, browser targets, and build/deployment workflows should shape the frontend choice?
   - Which non-functional quality attributes apply: performance, reliability, availability, security, privacy, accessibility, scalability, maintainability, operability, compliance, or another named attribute? For each applicable attribute, what surface and population does it cover, how is it measured, and what numeric or bounded target applies? Record units, traffic or tested population, measurement window, and percentile where applicable; record non-applicable categories explicitly as `N/A` with a reason.
   - Does the product need observability, audit logs, background jobs, or queueing?
9. Delivery and release targets
   - What is in scope for v1?
   - What is explicitly out of scope?
   - What timeline, milestone, or team constraint should shape the implementation plan?
   - What is the complete inventory of expected deployable web, API, mobile, or desktop surfaces? Give each surface a stable ID, then name the exact development and production targets for every expected surface. Give each target its own stable ID, record `surface` separately from the stage-specific `provider`, and allow providers to differ between stages.
   - For each target, which current PLAN-v5 source policy produces it: `pr_head` or `integration_head` for development, and `merged_main` for production? If the product requires a signed tag or another source rule, record that as an unresolved engineering-handoff gap instead of freezing an unsupported source choice.
   - What artifact kind is released, what signing or notarization is required, and what exact environment, store channel, testing track, update feed, or distribution channel receives it?
   - What submission, promotion, review, or manual-approval path must complete? What signal proves the release is actually available to its intended audience? Upload, submission, review approval, or a successful deployment command alone is not availability.
   - What rollout controls apply, and what is the real recovery path? For native stores and signed installers, identify when recovery means halting a staged rollout and shipping a signed forward-fix rather than claiming an instant rollback.
10. Success and validation
   - Which metrics define launch success?
   - Which observable test obligations must pass before release? Identify the functional or non-functional requirement each obligation proves, its test type, and its literal or measurable expected signal. The PRD assigns stable `TEST-*` IDs during synthesis.
   - What risks or unknowns should the team investigate first?

## Completeness Criteria

Discovery is complete enough to draft when the agent can state:

- The user, buyer, and primary problem.
- The product archetype and target surfaces.
- The top workflows and expected end states.
- The core data objects and integrations.
- The v1 scope, non-goals, and constraints.
- The architecture assumptions and high-risk unknowns.
- A complete expected deployable-surface inventory with stable surface IDs, plus stable development and production target IDs for every expected surface. Each target separates stable `surface` identity from stage-specific `provider`, uses a current PLAN-v5 source policy, and records artifact kind, signing requirement, exact channel/track, submission/promotion/review or manual-approval path, actual availability signal, rollout, and rollback or forward-fix path. Native targets are not forced into a web environment model.
- For products with a browser frontend, the content/interactivity profile, rendering needs, deployment constraints, and evidence needed to recommend a stack.
- For products with a backend, persistent data, or auth requirement, the resolved database category and auth strategy, and the evidence needed to recommend a backend framework, database engine, and auth provider.
- The UI screens or interaction points that need wireframes.
- A Builder UX Direction Decision naming the human decision owner, experience priority, guidance/control balance, information density, preferred layout/interaction pattern, recovery expectations, and validation depth. Each decision is `selected`, `provisional`, or `assumed`.
- Approved or draft exact wording and bounded display responsibilities for wireframed regions, or permission to derive them.
- Known brand references, visual hard limits, and product-specific visual goals, with high-fidelity preference discovery explicitly deferred to the optional downstream `frontend-design` exploration.
- Required style and motion intent for visually important regions, or permission to derive it.
- The success metrics and acceptance criteria.
- The applicable non-functional quality categories, each measurable target, and explicit reasons for categories that are `N/A`.
- The release-blocking test obligations and the functional or non-functional requirements each one proves, ready for stable `TEST-*` IDs.

If any item is missing and the user did not authorize assumptions, ask follow-up questions before drafting.

## Enhancement Mode

When `docs/product/PRD.md` (or another document clearly describing the same product) already exists, this run enhances it instead of starting fresh. Read the existing package in full first, then run a delta interview:

- Ask only about the categories above that the new idea actually adds to, changes, or leaves unresolved.
- Do not re-ask a question the existing package already answers; carry that answer forward unchanged.
- Preserve existing `TEST-*` IDs for unchanged obligations. Add a new TEST ID only when the delta creates an uncovered obligation; do not renumber or replace existing tests during cleanup.
- Preserve stable release target IDs for unchanged targets. Add a target ID only for a new release destination, and retire rather than reuse an ID when a target is removed.
- When the new idea adds a mobile or desktop target to a product that previously had only a web target (or, conversely, adds a web target to a previously mobile/desktop-only product), always re-trigger the platform-selection question (the mobile/desktop platform `AskUserQuestion` follow-ups under "Product surface" above) for the NEW target specifically. This holds even though the existing target's already-answered platform question is carried forward unchanged, per the "do not re-ask what's already answered" rule above — the new target has no answer yet, so it must be asked.
- If the new idea conflicts with an existing decision, surface the conflict explicitly and ask which should win instead of silently overwriting it.

## Assumption Mode

If the user asks for a first draft without more questions:

- State that assumptions are being used.
- Add an `Assumptions` section to every artifact where relevant.
- Add unresolved items to `Open Questions`.
- Record missing builder UX choices as `assumed`, never as selected or user-validated. Builder preference alone is not usability evidence.
- Do not invent compliance requirements or pricing. A named frontend recommendation is allowed when it follows `frontend-stack-selection.md`, is supported by the known requirements, and clearly identifies assumptions and alternatives.

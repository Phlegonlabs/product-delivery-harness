# Interview Guide

Ask a full product interview before drafting artifacts unless the user explicitly permits assumptions or asks to skip discovery. Keep the interview concise, grouped, and practical.

Bullets marked `(AskUserQuestion)` are a closed, enumerable set. Do not include them in the free-text segments. Ask one free-text segment per turn, wait for its reply, and start the closed questions only after every applicable segment has a reply and the final coverage check passes. Everything else stays free text because it is too product-specific or action-specific to enumerate.

Size each `AskUserQuestion` call to the question tool's actual per-call question and option limits. Batch each phase into the minimum number of calls the tool permits, never repeat an answered decision to reshape a call, and use the tool's built-in Other when its option limit cannot show the full candidate list; record that full list in `PRD.md`. There is no host-specific or cross-phase total-call cap. Start the closed-set phase only after the segmented free-text sequence is complete, in this order:

1. The decisions that depend on no other answer: product archetype and validation depth.
2. For a UI-bearing product, the five closed Builder UX Direction dimensions: experience priority, guidance versus expert control, information density, preferred layout/interaction pattern, and motion direction.
3. The decisions that depend on the archetype call's answer: deployment platform, mobile or desktop target platforms, client implementation strategy, browser-extension targets, monetization model, partner channel, database category, auth strategy, and stack decision mode.

This table is the canonical closed-decision inventory and phase order. Each applicable ID is asked exactly once by the matching `(AskUserQuestion)` bullet below. Batch only within one phase; a host with a smaller per-call capacity splits that phase without dropping or moving decisions.

| ID | Phase | Decision |
| --- | --- | --- |
| AQ-ARCHETYPE | independent | Product archetype |
| AQ-VALIDATION-DEPTH | independent | Validation depth |
| AQ-EXPERIENCE-PRIORITY | builder | Experience priority |
| AQ-GUIDANCE-CONTROL | builder | Guidance versus expert control |
| AQ-INFORMATION-DENSITY | builder | Information density |
| AQ-LAYOUT-PATTERN | builder | Layout and interaction pattern |
| AQ-MOTION-DIRECTION | builder | Motion direction and decision authority |
| AQ-DEPLOYMENT-PLATFORM | final | Deployment platform |
| AQ-MOBILE-TARGETS | final | Mobile target operating systems |
| AQ-DESKTOP-TARGETS | final | Desktop target operating systems |
| AQ-CLIENT-STRATEGY | final | Native versus cross-platform client strategy |
| AQ-BROWSER-TARGETS | final | Browser-extension targets |
| AQ-MONETIZATION-MODEL | final | Monetization model |
| AQ-PARTNER-CHANNEL | final | Partner channel |
| AQ-DATABASE-CATEGORY | final | Database category |
| AQ-AUTH-STRATEGY | final | Auth strategy |
| AQ-STACK-DECISION-MODE | final | How the owner wants unresolved technology choices decided |

Never ask a final-phase question in the archetype call. The product surface is still unknown there, so the answer can be about a platform the product does not have — and a wrong deployment platform then freezes a wrong environment contract into `architecture.md`.

Every final-phase question carries a skip rule, so ask only what remains applicable. A hybrid may leave many final decisions unresolved; split them across as many calls as the tool's real per-call capacity requires. Never drop an applicable decision or silently convert it from a user selection into an agent recommendation merely to reduce the number of calls.

## Segmented Free-Text Sequence

For a fresh package, use exactly three planned free-text turns. Ask only one segment per turn, end the turn, and wait for the reply. Before sending the next segment, remove prompts that the user's request, repository, existing package, or earlier replies already answer or make inapplicable. If a reply answers a later segment early, carry it forward instead of repeating it.

The short prompts below are the user-facing interview. Do not paste the longer **Question Routing Reference** as a questionnaire; use it only to interpret answers, detect gaps, and prepare concise follow-ups. Segment 1 must tell the user that applicable multiple-choice decisions follow after the open-ended sequence. No `AskUserQuestion` call may interrupt these segments.

In enhancement mode, run only the segments touched or reopened by the requested delta. Preserve every unaffected answer and decision without reconfirming it. A segment with no unresolved prompt is skipped; it does not require an empty turn.

### Segment 1 — Product and users

Ask the unresolved parts of these short prompts:

- What problem should this product solve, for whom, and what outcome would make it successful?
- Which people or organizations use, buy, administer, approve, or observe it, and what access differences matter?
- Where, when, and on which devices or channels will they use it? Mention accessibility, localization, or offline needs that matter.
- How should it make money, who pays, and should affiliates, referral partners, or resellers help sell it?

Capture internally: goal, buyer, users, roles, permissions, use context, channels, commercial intent, pricing direction, partner-sales intent, accessibility, localization, offline expectations, and known brand or policy constraints. Do not ask the closed product-archetype question here.

### Segment 2 — Workflows, data, and rules

Ask the unresolved parts of these short prompts:

- Walk through the most important workflows: what starts each one, the key steps, and the successful end state.
- What data and systems does each workflow use? Which data is sensitive, where may it go, and what retention, deletion, residency, or consent rules apply?
- Which rules, approvals, limits, audit needs, or forbidden outcomes apply? For AI/automation, what may it do, what needs human approval, and what limits apply?
- Which actions need confirmation, progress feedback, undo, recovery, or human intervention, and which screens or notifications support them?

Capture internally: top workflows, triggers, end states, data lifecycle, integrations, freshness, retention, classification, residency, deletion/export, consent, vendor and human access, business rules, compliance boundaries, AI/automation permissions and evaluation, UI states, content responsibilities, and confirmation/recovery expectations. Leave database category, auth strategy, validation depth, Builder UX dimensions, and stack decision mode for `AskUserQuestion`.

### Segment 3 — Delivery, success, and risk

Ask the unresolved parts of these short prompts:

- What is in or out of v1, and which timeline, team, stack, hosting, cost, license, lock-in, or existing-system constraints matter?
- What must be released for development and production, through which channels, and what proves each release is actually available and recoverable?
- Which launch metrics, measurable quality targets, and release-blocking tests define success?
- Which risks, unknowns, observability needs, background work, or operational concerns should be investigated first?

Capture internally: scope and non-goals; architecture and build-versus-buy constraints; cost, licensing, and lock-in tolerances; expected deployable surfaces; stable development and production targets; source refs; artifacts and signing; channels; release gates; availability signals; rollout and recovery; success metrics with baseline, window, source, and owner; measurable NFRs; test obligations; risks; observability; audit; jobs; and queues. Ask concise targeted follow-ups rather than exposing this entire capture list to the user.

After segment 3, compare the aggregate answers with **Completeness Criteria**. If a material item is still missing and the user did not authorize assumptions, ask one compact targeted free-text follow-up containing only the missing items. This follow-up is an exception, not a fourth planned segment. Begin the closed `AskUserQuestion` phase only after the coverage check passes.

## Question Routing Reference

Ask only questions that are not already answered. Route unresolved details into the three short segments above or into the closed-question phase; do not emit this section as one long interview message.

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
   - [AQ-ARCHETYPE] Should this be web, mobile app, desktop app, browser extension, internal tool, automation or agent workflow, API, or a hybrid? (AskUserQuestion)
   - [AQ-MOBILE-TARGETS] If the answer includes a mobile app, which operating systems ship in v1: iOS, Android, both, or another explicit set? (AskUserQuestion, final phase) This decides destinations, not framework. Skip it when the prompt, package, or repository already names the complete v1 target set.
   - [AQ-DESKTOP-TARGETS] If the answer includes a desktop app, which operating systems ship in v1: macOS, Windows, both, or another explicit set? (AskUserQuestion, final phase) This decides destinations, not toolkit. Skip it when the complete target set is already named.
   - [AQ-CLIENT-STRATEGY] For a mobile or desktop client, should v1 use platform-native implementations, one cross-platform codebase, or an evidence-backed recommendation? (AskUserQuestion, final phase) Ask only after the target operating systems are known. Framework and toolchain choices such as Flutter versus React Native, or Tauri versus Electron, are later coherent-stack options under the Stack Decision Checkpoint rather than peer platform choices in this question.
   - [AQ-BROWSER-TARGETS] If the answer is browser extension, which browsers ship in v1: Chrome/Chromium only, Chrome plus Firefox, or an evidence-backed recommendation? (AskUserQuestion, final phase; use Other for Safari or another explicit set) Skip it when the full target set is already named. A browser extension skips the hosted deployment-platform question.
   - Which platforms, devices, or channels matter?
   - Are there accessibility, localization, or offline requirements?
5. Data and integrations
   - What data does the product create, read, update, or delete?
   - What third-party systems, APIs, files, emails, calendars, CRMs, payment providers, or databases are involved?
   - What data freshness and retention expectations apply?
   - Which data classes are public, internal, personal, sensitive, regulated, confidential, or customer-owned? Who may access each class, which vendors may process it, where may it reside, and how is it exported or deleted?
   - [AQ-DATABASE-CATEGORY] What category of persistence does this data need: relational, document, key-value/cache only, no persistent database, or an evidence-backed recommendation? (AskUserQuestion)
6. Business rules
   - What rules, thresholds, calculations, approvals, or eligibility logic matter?
   - What must never happen?
   - What compliance, audit, or policy constraints apply?
   - [AQ-MONETIZATION-MODEL] If the product has commercial intent or an unresolved pricing strategy, which model applies: no commercial surface, one-time purchase, recurring subscription, usage-based, hybrid, or undecided and need a recommendation? (AskUserQuestion, final phase, since the viable purchase route depends on the archetype answer) Skip it only when the user's prompt, existing package, or repository already resolves the model. This decision makes the Monetization Infrastructure Gate applicable but does not select RevenueCat or any other provider automatically.
   - [AQ-PARTNER-CHANNEL] If the product may use outside sellers or promoters, which channel applies: none, affiliate, referral, reseller, hybrid, or undecided and need a recommendation? (AskUserQuestion, final phase, since the operating model depends on the product and purchase surfaces) Skip it when the user's prompt or existing package already resolves the channel, or when the product has no commercial or partner-distribution intent. Affiliate link attribution, known-lead referral, and reseller-owned sales are different operating models; resolve them with `monetization-and-partner-channel-guide.md`.
7. UX expectations
   - Who is the builder or human product/design decision owner for the UX direction?
   - [AQ-EXPERIENCE-PRIORITY] What should the experience optimize first: speed, clarity, guided completion, expert control, exploration, conversion, or content comprehension? (AskUserQuestion)
   - [AQ-GUIDANCE-CONTROL] Should the experience be guided, balanced, or expert-flexible? (AskUserQuestion)
   - [AQ-INFORMATION-DENSITY] Should the interface be sparse, balanced, or information-dense? (AskUserQuestion)
   - [AQ-LAYOUT-PATTERN] Which primary layout and interaction pattern does the builder prefer, and why does it fit the user's task? (AskUserQuestion)
   - [AQ-MOTION-DIRECTION] Should the shipped interface stay quiet with only necessary functional feedback, use expressive motion where it improves hierarchy or brand, or let the AI recommend one of those directions from the product evidence? (AskUserQuestion) When the owner delegates the recommendation, the AI records its rationale and per-surface Motion Need Gate; it does not silently authorize generated motion, autoplay or sound, a material performance budget, an accessibility exception, or a new product surface.
   - Which actions require confirmation, undo, recovery, progress feedback, or human intervention? Ask this as free text — it varies too much by action to enumerate.
   - [AQ-VALIDATION-DEPTH] What validation depth does the builder expect: documented assumptions, internal prototype review, testing with likely users, or recurring usability benchmarking? (AskUserQuestion)
   - What screens, dashboards, forms, or notifications are expected?
   - What should users see when there is no data, a long-running job, a validation error, or a permission issue?
   - Do not ask the user to choose from a fixed catalog of design-reference visual styles in this discovery interview. Record known brand references, visual constraints, product-specific goals, and disliked patterns. After the PRD UI surface contract and wireframes are approved and the market-research gap pass is available, the direct UI Design Pass asks what style the owner wants, waits for the answer, checks `design-taste-frontend` applicability, and produces one recommended product-specific direction by default. It produces three comparable directions only when the owner asks for alternatives or a recorded conflict needs comparison. That later gate is a separate decision phase.
   - Are there known design references or brand constraints?
   - Which headings, body copy, labels, CTAs, legal text, and state messages already have approved wording? For the rest, what must each region display or communicate?
   - Which regions need a specific style direction or animation, and what should that treatment communicate about hierarchy, meaning, or action? Use the answer to classify each key surface as `required`, `recommended`, `not_required`, or `blocked` in the Motion Need Gate.
   - For a landing page, what single message and primary action belong in the first viewport, and which details can be deferred?
   - Which regions require an image, product media, video, or animation, and what should each help the user understand or do?
8. Architecture constraints
   - Is there a required stack, hosting environment, database, auth provider, or existing system?
   - [AQ-AUTH-STRATEGY] What auth strategy should this product use: build custom authentication, a managed third-party provider, a platform-native provider, no auth, or an evidence-backed recommendation? (AskUserQuestion)
   - [AQ-DEPLOYMENT-PLATFORM] For a deployable web, API, or hosted backend target, which deployment platform should this use? (AskUserQuestion, final phase, unless the user's prompt or current repository already names one) Use product evidence to show two or three serious applicable choices with concise tradeoffs, including an evidence-backed recommendation choice; use the built-in Other for another provider or an explicit stage-to-provider mapping. It does not apply to native or browser-extension distribution targets, whose release path is resolved with `architecture-playbook.md`.
   - For a browser frontend, is the product primarily content-led, interaction-led, or a mixture? Which routes require SEO, static generation, server rendering, authenticated personalization, or SPA behavior?
   - If the platform is Cloudflare, does the frontend need Cloudflare Workers bindings or APIs such as D1, KV, R2, Durable Objects, Queues, Workflows, or Workers AI? For another platform, note the equivalent platform-managed services it needs.
   - Which team skills, existing components, package constraints, browser targets, and build/deployment workflows should shape the frontend choice?
   - What build-versus-buy, operating-cost, license, vendor-lock-in, maintenance-owner, or migration constraints apply to technology and service choices?
   - [AQ-STACK-DECISION-MODE] How should unresolved implementation technology be decided: the owner reviews one recommended coherent stack plus alternatives, the owner selects layer by layer, or the owner explicitly delegates the final choice to the product-definition-builder? (AskUserQuestion, final phase) A delegation is recorded authority, not permission to skip the later Product Definition Approval.
   - Which non-functional quality attributes apply: performance, reliability, availability, security, privacy, accessibility, scalability, maintainability, operability, compliance, or another named attribute? For each applicable attribute, what surface and population does it cover, how is it measured, and what numeric or bounded target applies? Record units, traffic or tested population, measurement window, and percentile where applicable; record non-applicable categories explicitly as `N/A` with a reason.
   - Does the product need observability, audit logs, background jobs, or queueing?
9. AI and automation, when applicable
   - What model or automation capability is needed, and what may it read, retain, generate, or change?
   - Which tool calls or side effects require confirmation or human approval, and how can the feature be disabled safely?
   - What evaluation set, quality threshold, prohibited outcome, cost/latency budget, observability, fallback, and incident path define acceptable behavior?
   - How are prompt injection, untrusted tool output, data leakage, and invalid generated output contained?
10. Delivery and release targets
   - What is in scope for v1?
   - What is explicitly out of scope?
   - What timeline, milestone, or team constraint should shape the implementation plan?
   - What is the complete inventory of expected deployable web, API, mobile, desktop, or browser-extension surfaces? Give each surface a stable ID, then name the exact development and production targets for every expected surface. Give each target its own stable ID, explicit lowercase kebab-case surface suffix, and lowercase kebab-case release name. Production uses the unqualified canonical `<product-slug>-<surface-suffix>` name with no `-prod`; development uses that exact name plus `-dev`; distinct surfaces never share a release name. Record `surface` separately from the stage-specific `provider`, and allow providers to differ between stages.
   - For each target, which exact branch or ref produces the release? Under the standard main-only branch-promotion contract, the exact candidate run branch/ref supplies the internally tested development release and `main` supplies production. Initial delivery and later enhancements both start from observed remote `main`. Record any signed tag or different source rule explicitly.
   - What artifact kind is released, what signing or notarization is required, and what exact environment, store channel, testing track, update feed, or distribution channel receives it?
   - What submission, promotion, review, or manual-approval path must complete? What signal proves the release is actually available to its intended audience? Upload, submission, review approval, or a successful deployment command alone is not availability.
   - What rollout controls apply, and what is the real recovery path? For native stores and signed installers, identify when recovery means halting a staged rollout and shipping a signed forward-fix rather than claiming an instant rollback.
11. Success and validation
    - Which metrics define launch success? For each, name the baseline, target or guardrail, measurement window, source/method, and owner.
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
- A complete expected deployable-surface inventory with stable surface IDs, plus stable development and production target IDs for every expected surface. Each target separates stable `surface` identity from stage-specific `provider`, names the exact candidate run branch/ref for internal release and `main` for production under the standard main-only promotion contract (or records an explicit alternative), and records artifact kind, signing, channel, release gates, availability, rollout, and recovery. Native targets are not forced into a web environment model.
- For products with a browser frontend, the content/interactivity profile, rendering needs, deployment constraints, and evidence needed to recommend a stack.
- For products with a backend, persistent data, or auth requirement, the resolved database category and auth strategy (or explicit recommendation request), and the evidence needed to recommend a backend framework, database engine, and auth provider.
- For mobile, desktop, or browser-extension products, the exact v1 operating-system/browser targets are separate from native-versus-cross-platform and framework/toolchain choices.
- The Stack Decision Mode and named human decision owner; no recommendation is treated as accepted merely because the agent wrote it.
- A Data and Trust Gate with classification, residency, retention, deletion/export, consent/policy, vendor/human access, and risk ownership when applicable, or `not_required` with a reason.
- An AI and Automation Gate with data, model/provider boundary, tool permissions, human approval, evaluation, cost/latency, fallback/shutoff, injection defense, and output validation when applicable, or `not_required` with a reason.
- The monetization model and both the Monetization Infrastructure Gate and Partner Channel Gate, including explicit `not_required` reasons; when applicable, the pricing/offer rules, purchase surfaces, entitlement owner, merchant-of-record/tax owner, partner motion, attribution, commission, payout, and reseller responsibilities needed to recommend current providers.
- The UI screens or interaction points that need a canonical PRD surface entry.
- A Builder UX Direction Decision naming the human decision owner, experience priority, guidance/control balance, information density, preferred layout/interaction pattern, motion direction and decision authority, recovery expectations, and validation depth. Each decision is `selected`, `provisional`, or `assumed`.
- Approved or draft exact wording and bounded display responsibilities for visible regions, or permission to derive them.
- Known brand references, visual hard limits, disliked patterns, and product-specific visual goals, with design-reference preference discovery explicitly deferred to the direct UI Design Pass after the PRD UI surface contract and wireframes are approved.
- A Motion Need Gate for every key UI surface: `required`, `recommended`, `not_required`, or `blocked`, with purpose, trigger, decision source, and reduced-motion fallback; when the owner delegates the recommendation, the AI records why without expanding scope or authorizing a generation provider.
- The success metrics and acceptance criteria, including baseline, target/guardrail, measurement window, source/method, and owner.
- The applicable non-functional quality categories, each measurable target, and explicit reasons for categories that are `N/A`.
- The release-blocking test obligations and the functional or non-functional requirements each one proves, ready for stable `TEST-*` IDs.

If any item is missing and the user did not authorize assumptions, ask follow-up questions before drafting.

## Enhancement Mode

When `docs/product/PRD.md` (or another document clearly describing the same product) already exists, this run enhances it instead of starting fresh. Read the existing package in full first, then run a delta interview:

- Record an `Enhancement Impact Record` before drafting. Classify product scope/behavior, UI structure/style, data/integrations, architecture/stack, data/trust/AI, monetization/partner channels, and release/operations as unchanged or changed; keep the existing `none` / `structure` / `style` / `both` vocabulary for the UI row. Each changed row names the affected IDs or decisions, artifacts to refresh, and approval gates to rerun.
- First, classify the delta's UI impact explicitly with the owner: `none` (no UI change), `structure` (screens, regions, flows, or states change), `style` (the visual direction or design system is affected), or `both`. Never assume `none` because the request reads backend- or data-side — most enhancements are design-side. Record the classification; it drives the wireframe revision and style-review rules in `wireframe-guide.md`'s Enhancement Revisions.
- Ask only about the categories above that the new idea actually adds to, changes, or leaves unresolved.
- Do not re-ask a question the existing package already answers; carry that answer forward unchanged.
- Preserve existing `TEST-*` IDs for unchanged obligations. Add a new TEST ID only when the delta creates an uncovered obligation; do not renumber or replace existing tests during cleanup.
- Preserve stable release target IDs for unchanged targets. Add a target ID only for a new release destination, and retire rather than reuse an ID when a target is removed.
- When the new idea adds a mobile, desktop, or browser-extension target, re-trigger the applicable target-set and implementation-strategy questions for that new target. Existing target answers remain unchanged.
- If the new idea conflicts with an existing decision, surface the conflict explicitly and ask which should win instead of silently overwriting it.

## Assumption Mode

If the user asks for a first draft without more questions:

- State that assumptions are being used.
- Add an `Assumptions` section to every artifact where relevant.
- Add unresolved items to the structured `Open Questions` table with owner, deadline, approval impact, and status.
- Record missing builder UX choices as `assumed`, never as selected or user-validated. Builder preference alone is not usability evidence.
- Do not invent compliance requirements or pricing. A named technology recommendation is allowed when it follows the applicable stack-selection guide, is supported by known requirements, and clearly identifies assumptions and alternatives; it remains `Recommended` and cannot pass Product Definition Approval unless the owner accepts it or previously delegated that exact decision class.

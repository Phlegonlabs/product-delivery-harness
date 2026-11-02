# Interview Guide

Ask a full product interview before drafting artifacts unless the user explicitly permits assumptions or asks to skip discovery.

Bullets marked `(AskUserQuestion)` are a closed, enumerable set. Do not include them in the free-text segments; start the closed questions only after every applicable segment has a reply and the final coverage check passes. Everything else stays free text.

Size each `AskUserQuestion` call to the question tool's actual per-call question and option limits. Batch each phase into the minimum number of calls the tool permits, never repeat an answered decision to reshape a call, and use the tool's built-in Other when its option limit cannot show the full candidate list; record that full list in `PRD.md`. There is no host-specific or cross-phase total-call cap.

This table is the canonical closed-decision inventory and phase order. `independent` decisions depend on no other answer and form the archetype call; when the research assessment recommends `go`, its Research Gate decision leads it. `final` decisions depend on the archetype call's answer. Each applicable ID is asked exactly once by its `(AskUserQuestion)` bullet below; batch only within one phase.

| ID | Phase | Decision |
| --- | --- | --- |
| AQ-ARCHETYPE | independent | Product archetype |
| AQ-VALIDATION-DEPTH | independent | Validation depth |
| AQ-DELIVERY-PROFILE | independent | Delivery profile |
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
| AQ-MODULE-ORDER | final | Which module ships first and which depend on it |
| AQ-MIGRATION-MODE | final | Legacy cutover mode |
| AQ-JURISDICTIONS | final | Tax and accounting jurisdictions |

Never ask a final-phase question in the archetype call. Every final-phase question carries a skip rule: skip it only when the user's prompt, existing package, repository, or an earlier reply already fully resolves it, or when its bullet gives another condition. Never drop an applicable decision or silently turn a user selection into an agent recommendation to reduce calls.

## Segmented Free-Text Sequence

For a fresh package, use four planned free-text turns; under `Delivery profile: mvp`, an owner speed request compresses them into two turns: Segments 1+2, then 3+4. Ask only one segment per turn and wait for the reply. Before sending each segment, remove prompts that the user's request, repository, existing package, or earlier replies already answer or make inapplicable, carrying early answers forward.

The short prompts below are the user-facing interview; use the longer **Question Routing Reference** only to interpret answers, detect gaps, and prepare concise follow-ups, never as a questionnaire. Segment 1 must tell the user that applicable multiple-choice decisions follow the open-ended sequence. In enhancement mode, run only the segments touched or reopened by the requested delta; skip a segment with no unresolved prompt without an empty turn.

### Segment 1 — Product and users

- What problem should this product solve, for whom, and what outcome would make it successful?
- Which people or organizations use, buy, administer, approve, or observe it, and what access differences matter?
- Where, when and on which devices will people use it? Include companion websites, accessibility, language and offline needs.
- How should it make money, who pays, and should affiliates, referral partners, or resellers help sell it?

### Segment 2 — Workflows, data, and rules

- Walk through the most important workflows: what starts each one, the key steps, and the successful end state.
- What data and systems are used? Which data is sensitive, and what retention or consent rules apply? Also name security assets and trust boundaries.
- Which rules, approvals, limits, audit needs, or forbidden outcomes apply? For AI/automation, what may it do, what needs human approval, and what limits apply?
- Which actions need confirmation, progress feedback, undo, recovery, or human intervention, and which screens or notifications support them?

Capture internally: security entry points, abuse cases, prior incidents, required evidence, owner, and residual risk.

When the request, repository, or earlier replies point to a multi-module business system or the owner names a program, also ask the unresolved parts of these prompts in the same turn:

- Which modules make up the product, who owns each one, and what does each own?
- Which master data do modules share, and which module owns each entity?
- Which document types does each module handle, and how does each move from creation to a final state?
- Which approval rules apply, and who may create, approve, post, or reverse what?
- Which reports do people run today, and which legacy systems and data must migrate?
- Which external systems must it integrate with, and which business processes cross modules, such as order-to-cash, procure-to-pay, or period close?

Capture internally, per module: name, owner, owned entities, and dependencies; per shared entity: owner module, readers, and identity key; per document type: states, terminal states, who may trigger each transition, and the guarding rule; role pairs that must stay separate, report audience and freshness, legacy source owner and volume, external-system direction, cadence, and error owner, and each cross-module process with its modules in order.

### Segment 3 — Delivery, success, and risk

- What is in or out of v1, and which timeline, team, stack, hosting, cost, license, lock-in, or existing-system constraints matter?
- What releases through each development/production channel, in which owner-selected platform order with stage tests, and what proves availability and recovery?
- Which launch metrics, measurable quality targets, and release-blocking tests define success?
- Which risks, unknowns, observability needs, background work, or operational concerns should be investigated first?

Capture internally: source refs, audit, jobs, and queues.

For a program, also ask the unresolved parts of these prompts in the same turn:

- What load must it carry: named users, peak concurrent users, transactions per day, data growth per year, and years of retention?
- Which jurisdictions does it operate in, for tax, e-invoicing, record retention, and data residency?
- What cutover constraints apply: a parallel run, blackout dates such as period close or audits, and an agreed rollback window?

### Segment 4 — Ambition

- After this works, what should happen next, which decision or ritual does it feed, and what would make it unnecessary?
- Who does this best today, what instruments and raw material do they use, and why would someone come back or open the app again?
- Beyond the acceptable target, what is the unreasonable one, and what other than you and us would prove it worked?
- Said as verbs, what is this work and which fields join the crew, and where will people first see it — which of those places can we set up before launch?

Record the rungs in the PRD's `## Ambition` section and the growth answers in its `## Growth Contract` section per `output-contract.md`.

After segment 4, compare the aggregate answers with **Completeness Criteria**. If a material item is still missing and the user did not authorize assumptions, ask one compact targeted free-text follow-up containing only the missing items. This follow-up is an exception, not a fifth planned segment. Begin the closed `AskUserQuestion` phase only after the coverage check passes.

## Question Routing Reference

1. Product surface
   - [AQ-ARCHETYPE] Should this be web, mobile app, desktop app, browser extension, API, agent or bot, MCP server, library or plugin, internal tool, a content channel, or a combination? Name every surface, then the primary one. (AskUserQuestion)
   - [AQ-MOBILE-TARGETS] If the answer includes a mobile app, which operating systems ship in v1: iOS, Android, both, or another explicit set? (AskUserQuestion, final phase) This decides destinations, not framework.
   - For a mobile product, carry its public showcase/authenticated Web scope into the archetype decision and release inventory, resolving only missing scope, per `mobile-stack-selection.md#app-and-companion-web-contract`. Reuse settled client-strategy decisions.
   - [AQ-DESKTOP-TARGETS] If the answer includes a desktop app, which operating systems ship in v1: macOS, Windows, Linux, or another explicit set? (AskUserQuestion, final phase)
   - [AQ-CLIENT-STRATEGY] For a mobile or desktop client, should v1 use platform-native implementations, one cross-platform codebase, or an evidence-backed recommendation? (AskUserQuestion, final phase) Ask only after the target operating systems are known. Framework and toolchain choices belong to the Stack Decision Checkpoint.
   - [AQ-BROWSER-TARGETS] If the answer is browser extension, which browsers ship in v1: Chrome/Chromium only, Chrome plus Firefox, or an evidence-backed recommendation? (AskUserQuestion, final phase; use Other for Safari or another explicit set) A browser extension skips the hosted deployment-platform question.
2. Data and integrations
   - What data freshness and retention expectations apply?
   - [AQ-DATABASE-CATEGORY] What category of persistence does this data need: relational, document, key-value/cache only, no persistent database, or an evidence-backed recommendation? (AskUserQuestion)
3. Business rules
   - What thresholds, calculations, eligibility logic, and compliance or policy constraints apply?
   - [AQ-MONETIZATION-MODEL] If the product has commercial intent or an unresolved pricing strategy, which model applies: no commercial surface, one-time purchase, recurring subscription, usage-based, hybrid, or undecided and need a recommendation? (AskUserQuestion, final phase, since the viable purchase route depends on the archetype answer) This makes the Monetization Infrastructure Gate applicable but selects no provider automatically.
   - [AQ-PARTNER-CHANNEL] If the product may use outside sellers or promoters, which channel applies: none, affiliate, referral, reseller, hybrid, or undecided and need a recommendation? (AskUserQuestion, final phase, since the operating model depends on the product and purchase surfaces) Skip it when the product has no commercial or partner-distribution intent. Resolve it with `monetization-and-partner-channel-guide.md`.
4. UX and UI product obligations
   - Who owns later UI design decisions?
   - [AQ-VALIDATION-DEPTH] What validation depth does the builder expect: documented assumptions, internal prototype review, testing with likely users, or recurring usability benchmarking? (AskUserQuestion)
   - What screens, dashboards, forms, or notifications are expected, and what should users see when there is no data, a long-running job, a validation error, or a permission issue?
   - Record only hard brand, platform, legal, or accessibility constraints needed to define the product. Do not ask about preferred density, layout, visual character, typography, color, imagery, icons, motion, media placeholders, wireframes, or design tokens; those belong to `ui-design-builder` after Product Definition Approval.
   - Which headings, body copy, labels, CTAs, legal text, and state messages already have approved wording? For the rest, what must each region display or communicate?
   - For a landing page, what single message and primary action belong in the first viewport, and which details can be deferred?
5. Architecture constraints
   - [AQ-AUTH-STRATEGY] What auth strategy should this product use: build custom authentication, a managed third-party provider, a platform-native provider, no auth, or an evidence-backed recommendation? (AskUserQuestion)
   - [AQ-DEPLOYMENT-PLATFORM] For a deployable web, API, or hosted backend target, which deployment platform should this use? (AskUserQuestion, final phase, unless the user's prompt or current repository already names one) Use product evidence to show two or three serious applicable choices with concise tradeoffs, including an evidence-backed recommendation; use the built-in Other for another provider or a stage-to-provider mapping. If the owner requests a recommendation or has no preference, carry that forward, investigate coherent platform-plus-stack bundles, and present them for acceptance before approval; never repeatedly demand provider names or silently mark one resolved. It does not apply to native or browser-extension distribution targets (see `architecture-playbook.md`).
   - For a browser frontend, is the product primarily content-led, interaction-led, or a mixture? Which routes require SEO, static generation, server rendering, authenticated personalization, or SPA behavior?
   - If the platform is Cloudflare, does the frontend need Workers bindings or APIs such as D1, KV, R2, Durable Objects, Queues, Workflows, or Workers AI? For another platform, note its equivalent platform-managed services.
   - Which team skills, existing components, package constraints, browser targets, and build/deployment workflows should shape the frontend choice?
   - What build-versus-buy, operating-cost, license, vendor-lock-in, maintenance-owner, or migration constraints apply to technology and service choices?
   - [AQ-STACK-DECISION-MODE] How should unresolved implementation technology be decided: the owner reviews one recommended coherent stack plus alternatives, the owner selects layer by layer, or the owner explicitly delegates the final choice to the product-definition-builder? (AskUserQuestion, final phase) "No preference" selects the first review path, not a delegated final answer or automatic approval. Explain consequences in plain language; a delegation is recorded authority, not permission to skip the later Product Definition Approval.
   - Which non-functional quality attributes apply: performance, reliability, availability, security, privacy, accessibility, scalability, maintainability, operability, compliance, or another named attribute? For each, what surface and population does it cover, how is it measured, and what numeric or bounded target applies? Record units, measurement window, and percentile where applicable; mark non-applicable categories `N/A` with a reason.
6. AI and automation, when applicable
   - What model or automation capability is needed, what may it read, retain, generate, or change, and which tool calls or side effects require confirmation or human approval?
   - How can the feature be disabled safely, and how are prompt injection, untrusted tool output, data leakage, and invalid generated output contained?
   - Resolve `eval-policy-contract.md`, reusing answered decisions; there is no universal pass rate.
7. Delivery and release targets
   - [AQ-DELIVERY-PROFILE] Which delivery profile fits: `standard`, `mvp`, or `program` (several modules delivered one at a time in dependency order)? (AskUserQuestion) For a new product with one owner or a small team, recommend `mvp` first and state what `standard` adds; recommend `program` when the replies name several modules with shared data. The owner still picks.
   - What is the complete inventory of expected deployable web, API, mobile, desktop, or browser-extension surfaces? Give each surface a stable ID, then name its exact development and production targets, each with its own stable ID, lowercase kebab-case surface suffix, and lowercase kebab-case release name. Production uses the unqualified canonical `<product-slug>-<surface-suffix>` name with no `-prod`; development uses that exact name plus `-dev`; distinct surfaces never share a release name. Record `surface` separately from the stage-specific `provider`; providers may differ between stages.
   - For a multi-platform product, ask the human owner whether to sequence whole-platform delivery, and record the order, stage completion tests, shared API/interface ARCH IDs, and owner decision. Do not infer the order or use a shared label to evade separate platform evidence. A single platform may record a concrete not-required reason.
   - New packages use `main-preview/1`: development is the exact candidate branch/ref and SHA, and production is `refs/heads/main` after separate authorization. Ordinary work and hotfixes both freeze remote main. Preserve historical package/RUN pins without migration. Record native Preview capability or an isolated alternative. Tags and alternative production refs are rejected.
   - What artifact kind is released, what signing or notarization is required, and what environment, store channel, testing track, update feed, or distribution channel receives it?
   - What submission, promotion, review, or manual-approval path must complete? What signal proves the release is available to its intended audience? Upload, submission, review approval, or a successful deployment command alone is not availability.
   - What rollout controls apply, and what is the real recovery path? For native stores and signed installers, identify when recovery means halting a staged rollout and shipping a signed forward-fix rather than claiming an instant rollback.
8. Success and validation
   - Which observable test obligations must pass before release? Identify the functional or non-functional requirement each obligation proves, its test type, and its literal or measurable expected signal. The PRD assigns stable `TEST-*` IDs during synthesis.
9. Ambition
   - Which rung of the ladder does this release serve?
10. Program scale, only when the delivery profile is `program`
    - Modules and shared data: a dependency cycle means the split is wrong, so ask which module should own the shared piece. Every shared entity has exactly one owner module.
    - Legacy sources: ask for the control totals that prove each load.
    - Cross-module processes: ask for the result that proves each one end to end.
    - Capacity and jurisdictions: numbers need a basis, and each jurisdiction implies its own tax, e-invoice, retention, and residency rules.
    - [AQ-MODULE-ORDER] Which module ships first, and which modules depend on it? (AskUserQuestion, final phase) Offer the modules named in the Segment 2 reply and record the full order in the PRD's Module Map. The shared kernel is the usual first candidate.
    - [AQ-MIGRATION-MODE] How does the program cut over from the legacy systems: big-bang cutover, parallel run, phased by module, or an evidence-backed recommendation? (AskUserQuestion, final phase) When the program is greenfield with no data to migrate, skip it and record the migration section as `not_required` with that reason.
    - [AQ-JURISDICTIONS] Which tax and accounting jurisdictions apply? (AskUserQuestion, final phase) Offer the countries or regions named in the Segment 3 reply and allow several. Each answer seeds the Data and Trust rows: tax and e-invoice regime, record retention, data residency, and statutory filings.

## Completeness Criteria

Discovery is complete enough to draft when the agent can state:

- The user, buyer, primary problem, product archetype, and target surfaces.
- The top workflows with end states, core data objects, integrations, v1 scope, non-goals, constraints, architecture assumptions, and high-risk unknowns.
- A complete expected deployable-surface inventory with stable surface IDs and stable development and production target IDs for every surface, each recording the release answers above under main-preview/1. Native targets are not forced into a web environment model.
- For products with a browser frontend, the content/interactivity profile, rendering needs, deployment constraints, and evidence needed to recommend a stack.
- For products with a backend, persistent data, or auth requirement, the resolved database category and auth strategy (or explicit recommendation request), and the evidence needed to recommend a backend framework, database engine, and auth provider.
- For mobile, desktop, or browser-extension products, the exact v1 operating-system/browser targets.
- The Stack Decision Mode and named human decision owner.
- A Data and Trust Gate with classification, residency, retention, deletion/export, consent/policy, vendor/human access, and risk ownership when applicable, or `not_required` with a reason.
- Security discovery inputs for `output-contract.md`'s risk list: assets, entry points, trust boundaries, adversary actions, forbidden outcomes, prior incidents, required tools/evidence, owner, and residual risk — or a concrete owner-approved documentation-only reason.
- An AI and Automation Gate with data, model/provider boundary, tool permissions, human approval, evaluation, cost/latency, fallback/shutoff, injection defense, and output validation when applicable, or `not_required` with a reason.
- The monetization model, plus the Monetization Infrastructure Gate and Partner Channel Gate with explicit `not_required` reasons; when applicable, the pricing/offer rules, purchase surfaces, entitlement owner, merchant-of-record/tax owner, partner motion, attribution, commission, payout, and reseller responsibilities.
- The UI screens or interaction points that need a canonical PRD surface entry, with approved or draft exact wording and bounded display responsibilities for visible regions (or permission to derive them).
- The named human owner for the later `ui-design-builder` phase, or an explicit `not_required` result for a headless product.
- The success metrics and acceptance criteria, including baseline, target/guardrail, stretch, measurement window, source/method, and owner.
- The Ambition ladder with an outside judge on every rung, at least one stretch target, the crew or an explicit `none`, and the access gaps.
- The delivery Shape: track, companion surface, and console type.
- The Growth Contract: a north star with Day 7 and Day 30 targets, at least one re-engagement mechanism for web or app tracks, discovery surfaces including the social, video, newsletter or community accounts the team actually runs, and a launch window with a destination per row.
- The applicable non-functional quality categories, each measurable target, and explicit reasons for categories that are `N/A`.
- The release-blocking test obligations and the functional or non-functional requirements each one proves, ready for stable `TEST-*` IDs.
- For `Delivery profile: program`, the Module Map has an order, every module has an owner, shared data has an owner module, and each cross-module business process names its modules; the capacity numbers, jurisdictions, and migration mode (or a greenfield reason) are recorded too.

## Enhancement Mode

When `docs/product/PRD.md` (or another document clearly describing the same product) already exists, this run enhances it instead of starting fresh. Read the existing package in full first, then run a delta interview:

- Record an `Enhancement Impact Record` in this round's PRD delta (`docs/product/deltas/PRD-DELTA-<EPIC-ID>.md`, `artifact-lifecycle.md`) before drafting. Classify product scope/behavior, UI structure/style, data/integrations, architecture/stack, data trust / AI, Security, monetization/partner channels, and release/operations as unchanged or changed, naming affected IDs, refreshes, and gates per `output-contract.md`.
- Classify the delta's UI impact explicitly with the owner: `none` (no UI change), `structure` (product-defined screens, routes, flows, or states change), `style` (only the downstream UI direction or design system is affected), or `both`. A `style`-only request routes to `ui-design-builder`; `structure` or `both` updates Product Definition first, then refreshes downstream UI approval.
- Ask only about the categories above that the new idea adds to, changes, or leaves unresolved. Do not re-ask a question the existing package already answers; carry that answer forward unchanged.
- Preserve existing `TEST-*` IDs for unchanged obligations. Add a new TEST ID only when the delta creates an uncovered obligation; do not renumber or replace existing tests during cleanup.
- Preserve stable release target IDs for unchanged targets. Add a target ID only for a new release destination, and retire rather than reuse an ID when a target is removed.
- When the new idea adds a mobile, desktop, or browser-extension target, re-trigger the applicable target-set and implementation-strategy questions for that new target.
- If the new idea conflicts with an existing decision, surface the conflict and ask which should win; never overwrite it silently.
- Ask Segment 4 only when the delta changes goals, metrics, users, or the delta's ambition rung.

## Assumption Mode

If the user asks for a first draft without more questions:

- State that assumptions are being used.
- Add an `Assumptions` section to every artifact where relevant.
- Add unresolved items to the structured `Open Questions` table with owner, deadline, approval impact, and status.
- Do not invent downstream UI choices; record the `ui-design-builder` handoff as pending.
- Do not invent compliance requirements or pricing. A named technology recommendation is allowed when it follows the applicable stack-selection guide, is supported by known requirements, and names its assumptions and alternatives; it stays `Recommended` and cannot pass Product Definition Approval unless the owner accepts it or previously delegated that exact decision class.
- Draft the PRD's `## Ambition` section with `Assumed` markers on unverified entries.

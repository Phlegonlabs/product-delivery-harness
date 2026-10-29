# Output Contract

Produce a core multi-file Markdown PRD package. Stage and publish it according to `artifact-lifecycle.md`. The final package belongs under `docs/product/`. Use exactly these core artifact names unless the user requests different names:

- `docs/product/PRD.md`
- `docs/product/architecture.md`
- `docs/product/stack-decisions.md`

Every package passes a human Product Definition Approval before UI design or implementation. The owner approves product scope, measurable requirements, complete frontend and backend architecture, applicable trust/security/AI/commercial gates, resolved stack choices, release targets, accepted assumptions, and non-blocking open questions as one named package revision. A UI-bearing product then stops for a later explicit `ui-design-builder` request. A headless product records UI design as `not_required` but still passes Product Definition Approval.

This contract covers the owner-approved product, architecture, technology stack, and required UI behavior. It does not require a wireframe, visual direction, motion/media treatment, preview, token set, or design-system rules. Those belong to `ui-design-builder` and, when needed, `design-system-compiler`.

It also publishes `docs/product/market-research.md` when the post-draft market-research gap pass ran and returned findings. That pass runs before Stack Decision and Product Definition approval so its findings and Platform Optimization Recommendations cannot silently stale an accepted package. Every recommendation gets an explicit owner decision before any accepted change is applied. When the user declined it, no web tool was available, confidential context prevented a safe query, or the role returned blocked, the package records that state explicitly. See `market-research-guide.md`.

For a product with any deployable web, API/backend, mobile, desktop, or browser-extension release target, it also creates a one-time operational seed at `docs/ACTIVATION.md` from the sibling `product-activation` template when that path is absent. The seed maps release targets, every PRD metric, and every required `TEST-*` signal, but it contains no external authorization, account guess, secret value, or claim that a source is verified. An existing Activation record is owned by `product-activation` and is preserved byte-for-byte during product enhancement.

It specifies what each UI surface must show and do. It does not decide how the surface is composed or styled and creates no HTML reviewer.

`PRD.md` is the canonical source for product scope, routes, screen purpose, content responsibility, actions, states, responsive obligations, flows, trace IDs, trust/security/AI gates, and Product Definition Approval. `architecture.md` fixes frontend and backend structure, and `stack-decisions.md` records the separate Stack Decision Checkpoint. Later UI artifacts never override the approved Product Definition revision.

Produce `docs/product/implementation-plan.md` only when the user explicitly asks for delivery sequencing or implementation planning.

Keep canonical artifact prose in English. Produce complete Traditional Chinese owner review copies of PRD and architecture during drafting as `PRD.zh-TW.md` and `architecture.zh-TW.md`; they never become implementation authority. Follow `bilingual-review.md` for source hashes, matching trace IDs, semantic review, approval and paired publication. Preserve literal product copy and identifiers in their required language. Other artifacts remain English unless the owner requests translations.

## Design And Maintenance Routing

First classify this round using `ui-design-builder/references/review-workflow.md`. Initial design, enhancements and an explicit full redesign use the applicable design gates below. Routine maintenance is valid only with UI impact `none` or `style`; a `structure` or `both` change follows the affected design gates. Routine maintenance uses the current product, effective PRD and accepted changes: update affected requirements and the existing change record, modify and verify the product, and retain historical Wireframe/HiFi/tokens without mandatory regeneration. Historical visual differences alone are not a delivery block. A new product or stack decision still returns to its owning flow. An already frozen managed RUN keeps its pinned contract; reconcile at a task boundary rather than weakening its gates.

## Device And Reading Scope

For newly scoped iOS products, propose iPhone first. iPad is included only when explicitly required; never remove it from an approved PRD without an owner decision. Two named iPhone review targets can satisfy the native responsive set without assuming an iPad regular layout. Record supported orientations, OS range and Dynamic Type obligations separately. Declare supported locales and whether content uses locale switching or simultaneous bilingual reading. Stacked language pairs allow natural wrapping and assistive language identification. Do not force multi-language work onto single-language products or invent language controls. The UI owner translates these obligations into composition and visual design.

## How To Read This Package

Every artifact has one primary reader and one job. Write for that reader.

| Artifact | Primary reader | Answers |
| --- | --- | --- |
| `PRD.md` | The owner and anyone deciding whether to build this | What it is, for whom, what counts as done, and whether the product definition is approved |
| `architecture.md` | An engineer about to implement | How the system is shaped and where the risk is |
| `PRD.zh-TW.md`, `architecture.zh-TW.md` | The owner reviewing in Chinese | The complete meaning of the matching English sources; non-canonical review only |
| `stack-decisions.md` | The owner and engineer choosing or reviewing technology | Which coherent options were considered, what the owner approved, and why |
| `market-research.md` | Anyone questioning a product claim in `PRD.md` | What already exists out there, and what the evidence is |
| `research-assessment.md` | Anyone deciding whether this product should have been drafted | What the pre-draft evidence supported, and what the gate decided |
| `outcomes/YYYY-MM-DD-<release-set>.md` | The owner deciding what happens after a release | Immutable post-deployment measurements and the verdict |
| `docs/DEPLOYMENT.md` | The human operator preparing and checking a release | Which secret and variable names go where, which external consoles need work, and what actually deployed |
| `docs/ACTIVATION.md` | The owner or operator activating a delivered release | Which external actions and measurement sources are pending, configured, verified, blocked, or stale |
| `docs/DOCUMENTS.md` | Anyone locating flow artifacts | Which documents exist, who owns them, and their current status |

Core decision order is `PRD.md` → `architecture.md` → `stack-decisions.md`. For UI products, `docs/design/ui-design.md` and its HiFi target are later downstream inputs; pinned legacy packages also retain `docs/design/wireframes.html`. Optional UI/design-system and operational records never override Product Definition. Research artifacts hold evidence behind cited `RA-*` and `MR-*` findings.

The research-to-approval order is research-first evidence → complete candidate → Platform Optimization Recommendations → explicit owner choices → accepted revisions → Stack Decision Checkpoint → Product Definition Approval.

Two rules keep the package readable:

- **Meaning before bookkeeping.** Each file opens with what a human needs to understand the product and ends with the ID matrices and decision records that machines, auditors, and downstream skills need. Never open a file with a trace table.
- **One notation per block.** Prose, ASCII, and ID tables do not interleave inside a section. A table wider than seven columns is a sign the content wants to be a list instead; the Metrics table's `Stretch` column and the environment contract in `architecture.md` are the exceptions.

Length budget. These are targets, not caps — say less when the product is simple, and go over only when the product is genuinely more complex, not when a section drifted:

- `PRD.md`: about 200 lines. `## At a Glance` fits on one screen.
- `architecture.md`: about 250 lines.
- `stack-decisions.md`: about 150 lines.
- `market-research.md`: about 150 lines. Findings and sources, not an industry report.
- `research-assessment.md`: about 80 lines. Evidence and the gate decision, not a duplicate of the post-draft research.
- `outcomes/YYYY-MM-DD-<release-set>.md`: about 60 lines. Deployed facts and the verdict, not a status report.

When a section runs past its share, the usual cause is detail that belongs in a different artifact. Move it before expanding the file.

## `PRD.md`

Apply [Initial Product Foundations](../../delivery-harness/references/initial-product-foundations.md) to public discovery and early implementation order.
Required app AEO names its approved public content surface; private native screens cannot supply crawlable web evidence.

Use this structure:

```markdown
# PRD: [Product Name]

## At a Glance
| | |
| --- | --- |
| What it is | [One line] |
| Primary user | [One line] |
| Why now | [One line] |
| Success looks like | [One metric with its target] |
| Biggest risk | [One line] |
| Delivery profile | standard / mvp |
| Shape | track: web / app / agent / tool / content; companion: <public surface or none>; console: none / config-only / operations |

[One paragraph describing the product, user, and outcome.]

The Shape row names the primary surface family; every surface still routes on its own through the [Surface Catalog](../../delivery-harness/references/surface-catalog.md). `track` is `web`, `app`, `agent`, `tool`, or `content`; `companion` names the public companion surface or `none`; `console` is `none`, `config-only`, or `operations`. Keep the row consistent with the User Journeys, UI surfaces and release targets. An app track needs a companion public surface when AEO/SEO is required. An agent or tool track needs a public docs surface or an explicit `none` with its reason. A content track may have no release target when the architecture records that `none` with its reason. `console: operations` needs the console journeys in the Agentic Operations Console Pattern. A legacy package without the Shape row stays valid.

## Enhancement Impact Record
Include this section only in enhancement mode for a package without `docs/product/deltas/`; with deltas, this record lives in the PRD delta, not in `PRD.md`.

| Area | Impact | Affected IDs / decisions | Required refresh |
| --- | --- | --- | --- |
| Product scope / behavior | [unchanged / changed] | [IDs or none] | [Artifacts and gates or none] |
| UI structure / style | [none / structure / style / both] | [UI/UX IDs or none] | [HiFi/UI Design gates or retained legacy gates or none] |
| Data / integrations | [unchanged / changed] | [IDs or none] | [Artifacts and gates or none] |
| Architecture / stack | [unchanged / changed] | [ARCH IDs/layers or none] | [Stack checkpoint and artifacts or none] |
| Data trust / AI | [unchanged / changed] | [Gate/IDs or none] | [Artifacts and gates or none] |
| Security | [unchanged / changed] | [Gate/IDs or none] | [Artifacts and gates or none] |
| Monetization / partner | [unchanged / changed] | [Gate/IDs or none] | [Artifacts and gates or none] |
| Release / operations | [unchanged / changed] | [Targets or none] | [Artifacts and gates or none] |

Changed rows use area-specific refreshes. Product behavior reopens `PRD.md` and Product Definition Approval. For `ui-design/2`, a UI `structure`, `both` or active-design `style` row names `ui-design.md`, HiFi, HiFi review and Visual Approval, with copy completeness included in HiFi. A retained legacy `structure`/`both` row names `wireframes.html`, `ui-design.md`, Wireframe Validation and Visual Approval; legacy `style` names `ui-design.md` and Visual Approval. Generic Product approval accepts either complete explicit vocabulary; `--ui-contract ui-design/3` (new packages) or `ui-design/2` (retained packages) requires the HiFi vocabulary and additionally checks operations. Use that flag before approving a new UI design package and again before direction work. Routine maintenance retains its separate applicability rules. Data/integration changes reopen `PRD.md`, `architecture.md`, and Product Definition Approval. Architecture/stack changes reopen `architecture.md`, `stack-decisions.md`, Stack Decision Checkpoint, and Product Definition Approval. Trust/AI and monetization/partner changes reopen all three core package files plus both approval gates. Security changes reopen `PRD.md`, `architecture.md`, and Product Definition Approval; a security change that changes a stack decision also marks Architecture/stack changed. Release/operations changes reopen `architecture.md`, `DEPLOYMENT.md`, Product Definition Approval, and the deployment checker. Naming unrelated artifacts or generic approval words does not satisfy the row.

## Problem Statement
[Current pain, trigger, and why now.]

## Goals
- [Goal]

## Ambition
### Goal Beyond The Goal
| Rung | Outcome | Outside judge |
| --- | --- | --- |
| 1 | [the task done well] | [what proves it, other than us] |
| 2 | [the outcome the task serves] | [...] |
| 3 | [the durable workflow or replaced ritual that takes the human out of the loop] | [...] |

### Depth
| Best practitioners | Their instruments | Rawest material | Stretch target | Outside judge |
| --- | --- | --- | --- | --- |

### Range
Verbs: [the work restated as verbs, e.g. "getting busy people to believe a story about cause and effect and decide under uncertainty in 30 minutes"]

| Field | What they actually do here | Method or tool | Used as |
| --- | --- | --- | --- |
| [journalist] | [...] | [...] | design input / review lens / go-to-market |

When no other field helps, keep one row `| none | <reason> | n/a | n/a |`.

### Access
| Need | Present or missing | Unlocks |
| --- | --- | --- |

Rungs are better, not bigger. The outside judge is never the model or the owner's impression. The stretch target is the unreasonable target the team treats as reasonable; acceptance still uses the TEST and metric target. Crew rows marked `review lens` become optional domain lenses for the delivery review; Harness owns that rule in [Review Topology](../../delivery-harness/references/verification-gates.md#review-topology). Do what the field does: each crew row names what that field actually does here, not a role-play. `## Ambition` is required for packages created or enhanced under this contract version; a package without `docs/product/deltas/` and without `## Ambition` is legacy and stays valid.

## Growth Contract
### North Star
| Track | North star | Day 7 target | Day 30 target | Stretch | Source (MS-*) |
| --- | --- | --- | --- | --- | --- |

### Re-engagement
| Mechanism (email / push / subscription / deep link / return trigger) | Surface or event | TEST ID |
| --- | --- | --- |

### Discovery Surfaces
| Surface | Kind (seo-cluster / geo-page / store-listing / directory / landing / social / video_channel / newsletter / community / docs_site) | Owner stage | TEST or MS ID |
| --- | --- | --- | --- |

### Launch Window
| Day | Channel class (owned / earned / search / store) | Action | Owner | Readback metric | Destination |
| --- | --- | --- | --- | --- | --- |

Targets are hypotheses with a stated basis. `Owner stage` is `delivery`, `activation`, `gtm` or `growth` (`seo` remains a legacy alias of `growth`); the Launch Window needs at least one row whose day is within Day 0 to Day 7 inclusive, and each row names one real destination: a path, listing, account or `none (reason)`. The Day 7 and Day 30 reviews bind to the north-star targets. A missing re-engagement mechanism on a web or app track is a blocking gap; an agent, tool or content track records a mechanism or a `none` row with its reason. A discovery surface of kind seo-cluster, geo-page, store-listing, directory or landing maps to a UI surface, release target or landing path that exists in this PRD. A presence surface (social, video_channel, newsletter, community, docs_site) is written as `<platform>:<handle-or-url>`, such as `instagram:@handle` or `docs:https://docs.example.com`; it names the account the team runs, not a build. Kinds and their default sources are listed in the [Surface Catalog](../../delivery-harness/references/surface-catalog.md). Channel classes: `owned` is an account, list or product surface the team controls; `earned` is a community, directory or press that decides independently; `search` is public pages and listing text that reach search and answer engines; `store` is store, registry or marketplace assets.

## Non-Goals
- [Explicitly out of scope]

## Users and Personas
| Persona | Need | Key Workflow | Success Signal |
| --- | --- | --- | --- |

## User Journeys
### Journey 1: [Name]
Role and initial data: [actor, tenant/account state, prerequisites]
1. [User action, affected data and expected visible result]
2. [Persisted result, permission boundary and observable success]
Failure and recovery: [validation, denial, dependency failure, retry or cancellation]
Trace: [PRD/UI/TEST IDs for this complete journey]

## Functional Requirements
| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| PRD-001 | [Requirement] | [Must / should / could] | [Observable acceptance] |

## Non-Functional Requirements
| ID | Quality attribute | Scope / requirement | Measure | Target / threshold | TEST IDs |
| --- | --- | --- | --- | --- | --- |
| PRD-002 | [Performance / reliability / availability / security / privacy / accessibility / scalability / maintainability / operability / compliance, or another applicable attribute] | [Surface, workflow, population, and condition covered] | [Measured signal with unit, population, window, and percentile where applicable] | [Numeric threshold or bounded outcome] | TEST-002 |
| N/A | [Non-applicable quality category] | [Why it does not apply to this product or scope] | N/A | N/A | N/A |

Record every applicable quality category as a measurable `PRD-*` requirement, or record the category as explicitly `N/A` with a reason. The `N/A` row is an applicability record, not an NFR obligation, and does not receive a requirement or TEST ID. Words such as `fast`, `secure`, `reliable`, `scalable`, or `accessible` do not pass without an observable measure and target. Include units, tested population or traffic shape, measurement window, and percentile where they affect the result.

## UX Requirements
| ID | User / task | Requirement | Success and failure signal | Evidence status |
| --- | --- | --- | --- | --- |
| UX-001 | [User completing a critical task] | [Screens, states, accessibility, notifications, responsive behavior, or recovery] | [Observable success plus failure or abandonment signal] | [research-backed / prototype-reviewed / assumption] |

<!-- ui-surface-contract:start -->
## UI Surface Contract

Omit this section only when the product has no shipped UI surface. Define one entry per addressable screen or bounded UI surface. This is the canonical product source for what each surface must support; `ui-design-builder` later decides its layout and visual structure.

For App + companion Web products, apply `mobile-stack-selection.md#app-and-companion-web-contract`: one PRD covers the included iOS app, Android app, public showcase and any separately scoped authenticated Web app. Bind every platform to its own release surface and `UI-*` entries; shared client source code does not merge platform requirements, native/browser evidence or release targets. Record included/deferred/excluded destinations in Product Archetype and scope, without adding a competing surface registry.

The two HTML comments, each `UI-*` heading, and the backticked `` `route` ``, `` `releaseSurface` ``, `` `surfaceClass` ``, `` `captureMode` ``, `` `states` ``, `` `responsive` ``, and `` `copy` `` field names are invariant machine anchors for new or revised packages. A UI-bearing PRD contains exactly one non-empty matched boundary pair around the complete surface contract; every `UI-*` heading in the document is inside it. Keep the anchors unchanged when the surrounding PRD is written in another language. Each entry has exactly one literal route; use a separate `UI-*` entry when another addressable route needs the same presentation. Legacy single-platform packages without the three platform-binding anchors remain readable, but an approved new or revised package records them on every surface.

### UI-001 — [Surface name]

- `route`: [One literal route value, or `n/a — <reason>`]
- `releaseSurface`: [Exact stable `Surface` value from `architecture.md` Release Targets, such as `web-app` or `ios-app`]
- `surfaceClass`: [Exact Release Target surface class, such as `hosted_web`, `browser_extension`, `ios`, `android`, `macos`, or `windows`]
- `captureMode`: [hosted-browser / browser-extension / native / desktop, derived from `surfaceClass`]
- Main purpose: [One primary user goal]
- Content responsibilities: [Required information and controls; exact copy or bounded display contract for each, without choosing layout or region order]
- Actions and transitions: [Primary, secondary, destructive, navigation, success, and failure paths]
- `operations`: [JSON list of operation objects using the review-workflow fields below, or `none — <concrete reason of at least 12 characters>`; review task completeness, then verify HiFi joins at the UI approval gates (legacy packages also join Wireframe flows)]
- `states`: [Comma-separated state IDs. Record an inapplicable state as `<state>:n/a — <reason>` so the PLAN join can preserve the decision]
- `responsive`: [This surface's exact responsive set: at least three ascending numeric viewports for hosted web/extensions, default `viewports: 390, 768, 1024, 1440`; or at least two ordered named size classes for native/desktop, such as `sizeClasses: phone-small, phone-large` for phone-only apps. Hybrid surfaces keep separate sets; preserve existing approved targets]
- `copy`: [draft / approved / revision_requested / blocked] — [Static strings are implementation-bound after copy completeness; dynamic values follow their approved source/order/format/count/length/fallback contracts]
- Responsive obligations: [Content/actions that never drop, required interaction modes, long-content behavior, and overlay focus/dismissal requirements; layout order, grid, spans, and reflow remain UI-design decisions]
- Accessibility: [Focus, labels, announcements, heading order, and alt text as applicable]
- SEO metadata: [Per-route `<title>` and meta description; canonical URL or `n/a — <reason>`; Open Graph/social, robots, and structured-data decisions as applicable or `n/a — <reason>`]
- Trace IDs: [PRD-*, UX-*, ARCH-*, TEST-*]

<!-- ui-surface-contract:end -->

Every route maps to exactly one `UI-*` entry. Every required content responsibility states what it displays, where the content comes from, what the user should understand or do, and any source, order, format, count, length, or fallback constraint. The `` `copy` `` status records the PRD's copy responsibility: `draft` means ui-design-builder may propose and approve exact wording during copy completeness; `approved` means that responsibility and its display contract are already product-approved. `revision_requested` and `blocked` stop UI work. A full HiFi approval may advance a PRD `draft` responsibility to approved exact copy without rewriting the PRD status; `ui-design-builder` owns that final full HiFi approval and returns any changed responsibility or display contract for renewed Product Definition Approval. Do not invent layout regions in Product Definition.

SEO metadata is part of the surface contract, not an implementation-time invention. Each route's entry records its own unique `<title>` and meta description, written for that page's actual content, plus the applicable extras or an explicit `n/a — <reason>`. Site-level SEO obligations — indexing strategy, sitemap and robots policy, canonical policy, default structured data — are recorded in Frontend Delivery Requirements, and a required SEO obligation traces to its own `TEST-*` row like any other requirement.

## Frontend Delivery Requirements
- [Target devices and browsers, content/interactivity profile, rendering, performance, accessibility, localization, offline, and deployment constraints; site-level SEO — indexing strategy, sitemap and robots policy, canonical policy, default structured data — while each route's own `<title>` and meta description live in its `UI-*` entry]

Omit this section only when the product has no browser frontend.

## Data and Integration Requirements
- [Data objects, external systems, freshness, retention]

## Data and Trust
Data and Trust Gate: [required / not_required / blocked] — [reason], decided by [human owner]

When `required`, record the product decisions before selecting vendors:

| Area | Decision | Owner / evidence | TEST IDs |
| --- | --- | --- | --- |
| Classification and ownership | [Public/internal/personal/sensitive/regulated/confidential/customer-owned classes and source of truth] | [Owner/evidence] | [TEST-*] |
| Residency and vendor processing | [Allowed regions, subprocessors, transfer limits] | [Owner/evidence] | [TEST-*] |
| Retention, deletion, and export | [Periods, triggers, legal holds, user/admin export and deletion behavior] | [Owner/evidence] | [TEST-*] |
| Consent and policy basis | [Consent, notice, contract, or policy requirement] | [Owner/evidence] | [TEST-*] |
| Human and administrative access | [Roles, approval, masking, audit] | [Owner/evidence] | [TEST-*] |
| Incident and residual risk | [Detection, response owner, accepted residual risk] | [Owner/evidence] | [TEST-*] |

Each Data and Trust row has a stable test trace in order: `TRUST-CLASSIFICATION`, `TRUST-RESIDENCY`, `TRUST-RETENTION`, `TRUST-CONSENT`, `TRUST-ACCESS`, and `TRUST-INCIDENT`. At least one Required-Yes `TEST-*` named by the row includes that exact token in its Test Obligations upstream trace cell.

## Security Requirements
Security Requirements Gate: [required / not_required / blocked] — [reason], decided by [human owner]
Security scope: [executable / documentation_only]

Executable software — including static sites, clients, CLI tools, and agents — is `required` even without personal data or authentication. `not_required` is valid only when Security scope is `documentation_only`, the package has no executable or deployable surface, and the owner records that rationale. `blocked` prevents Product Definition Approval.

For `not_required`, the At a Glance `What it is` starts with `documentation-only` (or `A documentation-only`), and Product Archetype contains only `documentation_only — <concrete reason>`. Frontend, Backend, Data Model, API and Interface, and AI and Automation architecture each record `not_required — <reason>`. Every Component Architecture component is a concrete `.md`, `.rst`, or `.txt` file under `docs/`, or a root README file; directory wildcards, traversal, executable files, and MDX are forbidden. Workflow and Data Flow contains only `human_review — <reason>`; Deployment and Operations contains only `document_distribution — <reason>`; both reasons need at least 20 characters. Shipped UI, required automation, or release targets prohibit the exemption. No release target alone is not documentation-only proof.

Every Required-Yes security TEST must be referenced by a Security Requirements row. Its Expected signal uses `denial: rejected (<observable rejection signal>); no unauthorized side effects: unchanged (<observable state evidence>)`. Each parenthesized observation needs at least 12 characters and no placeholders, including the literal generic labels above. Preserve these English labels and statuses when translating observations. For example: `denial: rejected (validation error returned); no unauthorized side effects: unchanged (run record has zero writes)`. Harness security acceptance criteria use the same format. These are test assertions to verify, not a claim that prose itself proves the control works; review and executed tests must verify that the observations support both assertions.

When `required`, use exactly these seven columns. Every row references an existing `Must` or NFR `PRD-*` and at least one `Required: Yes` security `TEST-*` whose Test Obligations upstream trace names that same `PRD-*`:

| PRD ID | Asset / trust boundary | Abuse case | Control / safe failure | TEST IDs | Owner | Residual risk |
| --- | --- | --- | --- | --- | --- | --- |
| PRD-001 | [Asset and boundary crossed] | [Adversary action and forbidden outcome] | [Control, denial/safe failure, and no unauthorized side effects] | TEST-001 | [Human owner] | [none / none — concrete reason / accepted — concrete rationale] |

Each Residual risk cell uses the English machine prefixes `none` or `accepted`. Valid values are exactly `none`, `none — concrete reason`, or `accepted — concrete rationale`; a hyphen may replace the em dash. Keep these prefixes in English when surrounding prose is translated. Pending wording, unknown wording, a placeholder, or a bare `accepted` value is not an owner decision.

Cover the risk classes applicable to the product: identity/session/authorization/tenant isolation; untrusted input/injection/XSS/path/command execution; secrets/logs and dependency/build supply chain; upload/outbound URL/SSRF; webhook signatures/replay/idempotency; abuse/resource limits; secure storage/deep links/IPC/permissions for clients; and AI prompt/tool boundaries. Record each inapplicable class as `n/a — reason`; do not force irrelevant backend, auth, vendor, or scanner requirements.

Security tests must prove denial and absence of unauthorized side effects for the touched boundary. A generic final scan or broad review does not replace those negative tests. Discovery records prior incidents and owner-required tools or evidence. This follows the same SDLC principle reflected in [NIST SSDF](https://csrc.nist.gov/Projects/ssdf): track requirements, risks, and design decisions, then select risk-based controls and testing; it makes no compliance or certification claim.

Older documents may be inspected for history, but a current approval requires this section and explicit owner reapproval. Never auto-rewrite a frozen source to synthesize it.

## AI and Automation
AI and Automation Gate: [required / not_required / blocked] — [reason], decided by [human owner]

New packages include the active `eval-policy/1` JSON block from `eval-policy-contract.md` here and run the core checker with `--repo-root <repository-root> --eval-policy eval-policy/1`. Freeze policy/input bytes before approval; runner implementation and handoff evidence come later. Required AI cannot waive eval.

When `required`, record:

| Area | Decision | Owner / evidence | TEST IDs |
| --- | --- | --- | --- |
| Capability and provider boundary | [What the model/automation does; provider or self-host boundary] | [Owner/evidence] | [TEST-*] |
| Input, context, and retention | [Data allowed, retrieval sources, provider retention/training limits] | [Owner/evidence] | [TEST-*] |
| Tool and side-effect permissions | [Allowed tools/actions, confirmation and human approval points] | [Owner/evidence] | [TEST-*] |
| Evaluation and prohibited outcomes | [Representative eval set, thresholds, failure classes] | [Owner/evidence] | [TEST-*] |
| Cost, latency, and observability | [Budgets, usage metrics, alerts] | [Owner/evidence] | [TEST-*] |
| Fallback, shutoff, and incident path | [Degraded path, cancellation, disable switch, response owner] | [Owner/evidence] | [TEST-*] |
| Injection and output validation | [Untrusted-input isolation, schema/policy checks, invalid-output handling] | [Owner/evidence] | [TEST-*] |

Each AI row has a stable test trace in order: `AI-CAPABILITY`, `AI-CONTEXT`, `AI-SIDE-EFFECTS`, `AI-EVALUATION`, `AI-OPERATIONS`, `AI-FALLBACK`, and `AI-VALIDATION`. At least one Required-Yes `TEST-*` named by the row includes that exact token in its Test Obligations upstream trace cell.

## Business Rules
- [Rules, thresholds, approvals, calculations]

## Monetization and Partner Channels

Record both gates even when they are not required. Do not select RevenueCat merely because the product has pricing, and do not treat affiliate, referral, and reseller as synonyms.

| Decision | Selection | Product rationale / evidence | Status | Trace IDs |
| --- | --- | --- | --- | --- |
| Monetization model | [none / one_time / subscription / usage_based / hybrid / undecided] | [Who pays and for what] | [selected / approved / recommended / provisional / assumed] | [PRD-* / MR-* / RA-*] |
| Monetization Infrastructure Gate | [required / not_required / blocked] | [Purchase surfaces and infrastructure need, or explicit reason none] | [selected / approved / recommended / provisional / assumed] | [PRD-* / ARCH-* / TEST-*] |
| Pricing and offer | [Tiers, price metric, interval/unit, trial/discount, currency/region, upgrade/downgrade/cancel/refund] | [Value and buyer fit] | [selected / approved / recommended / provisional / assumed] | [PRD-* / TEST-*] |
| Purchase and entitlement | [Store/web/invoice surfaces; product, purchase/subscription, and entitlement source of truth] | [Cross-platform and lifecycle needs] | [selected / approved / recommended / provisional / assumed] | [ARCH-* / TEST-*] |
| Merchant of record / tax owner | [Product company / Stripe arrangement / Paddle / Lemon Squeezy / other / n/a] | [Payment, invoice, tax, fraud, refund, chargeback, and billing-support ownership] | [selected / approved / recommended / provisional / assumed] | [ARCH-* / TEST-*] |
| Partner Channel Gate | [required / not_required / blocked] | [Outside distribution need, or explicit reason none] | [selected / approved / recommended / provisional / assumed] | [PRD-* / ARCH-* / TEST-*] |
| Partner motion | [none / affiliate / referral / reseller / hybrid / undecided] | [Link attribution, known-lead referral, partner-owned sale, or named combination] | [selected / approved / recommended / provisional / assumed] | [PRD-* / TEST-*] |
| Partner economics and operations | [Commission/discount, attribution, reversal, payout, customer ownership, provisioning, support, termination] | [Channel rules] | [selected / approved / recommended / provisional / assumed] | [PRD-* / ARCH-* / TEST-*] |

Use `monetization-and-partner-channel-guide.md` to select providers only after these decisions. If either gate is `required`, add every customer, partner, and admin surface to the UI Surface Contract and add observable success, failure, cancellation, refund, attribution, commission, payout, provisioning, and termination obligations. The later `ui-design-builder` run projects those approved surfaces into HiFi.

## Metrics
| Metric | Definition | Baseline | Target / guardrail | Stretch | Measurement window | Source / method | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |

`Stretch` repeats the stretch target from `## Ambition` Depth.
Define the GA4/Firebase or approved alternative destination, canonical events and collection controls before dependent feature work.
Trace initial event delivery, duplicate prevention and test-traffic isolation through TEST obligations; actual production measurement remains release-bound. The Day 7 and Day 30 growth reviews read these definitions against the Growth Contract's north-star targets and feed the next delta round.

## Risks
| Risk | Impact | Mitigation |
| --- | --- | --- |

## Assumptions
| Assumption | Impact if wrong | Validation | Owner | Decision date | Status |
| --- | --- | --- | --- | --- | --- |
| [Assumption] | [Impact] | [Evidence or experiment] | [Owner] | [YYYY-MM-DD] | [open / accepted / validated / rejected] |

## Open Questions
| Question | Why it matters | Owner | Decision deadline | Blocks approval | Status / resolution |
| --- | --- | --- | --- | --- | --- |
| [Question] | [Decision or requirement affected] | [Owner] | [YYYY-MM-DD] | [Yes / No] | [Open / resolved — answer] |

Every open question names whether it blocks Product Definition Approval. An approved package has no unresolved `Yes` row. Non-blocking rows and open assumptions appear explicitly in the approval record; silence is not acceptance.

During candidate refinement, use these existing fields for unresolved lifecycle findings: affected IDs, evidence and proposed acceptance wording can appear in the question/resolution. Follow `prd-refinement.md`; do not edit frozen inputs to insert new questions or create a separate refinement ledger.

## Test Obligations
| TEST ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |
| --- | --- | --- | --- | --- | --- |
| TEST-001 | [Observable behavior or quality obligation] | [Unit / integration / contract / E2E / performance / security / accessibility / operational] | [Yes / No] | PRD-001 | [Literal pass signal, measured result, or threshold] |

Every `Must` functional requirement and every applicable non-functional requirement maps to at least one row whose `Required` value is `Yes`. A row may cover more than one upstream requirement only when one test genuinely verifies all of them. Preserve each `TEST-*` ID when its obligation keeps the same meaning; retire rather than reuse an ID whose meaning changes.

---

## UI Design Handoff Status

Every Product Definition records exactly one result:

UI design: [pending explicit ui-design-builder request / not_required — headless reason]

UI decision owner: [Human owner / n/a for headless]

Product Definition does not decide density, layout preference, visual style, motion treatment, media placeholders, wireframes, page theme, or design tokens. `ui-design-builder` records those decisions later in `docs/design/ui-design.md` without changing the approved Product Definition unless it finds a product or stack gap.

## Product Definition Decisions

This section is present for every product, including headless APIs and automations. It separates content decisions from the later filesystem publication authorization. Once the package has `docs/product/deltas/`, this section carries one line `Latest delta: docs/product/deltas/PRD-DELTA-<EPIC-ID>.md` naming the current round's delta.

### Research Gate

Research Gate: [go / clarify / stop / skipped] — [assessment date and findings path, or skip reason], decided by [human owner]
[For `clarify`, the questions asked and their resolutions, and the final gate value after re-assessment. For a skipped assessment, record whether the user declined it, no web tool was available, confidential context prevented a safe query, or the package is a trivial stub. Enhancement packages cite the prior package's gate unchanged.]

<!-- product-definition-approval:start -->
### Product Definition Approval
- Package mode: [new / enhancement]
- Package revision: [Stable revision label for this candidate]
- Package digest: [sha256:<64 lowercase hex> over the raw PRD/architecture/stack text, including fenced, indented and commented content; only this approval block is excluded]
- Decision: [approved / revision_requested / blocked]
- Decision owner: [Human product owner]
- Decided on: [YYYY-MM-DD]
- Approved artifacts: [PRD.md, architecture.md, stack-decisions.md]
- Market research reconciliation: [completed / skipped — reason / blocked — reason]
- Stack Decision Checkpoint: [approved / revision_requested / blocked]
- Accepted assumptions and non-blocking questions: [None / exact rows accepted for this revision]
- Blocking items: [None / exact unresolved decisions]
<!-- product-definition-approval:end -->

Keep the required level-two PRD headings, Product Definition marker pair and fields, Data and Trust/Security/AI gate lines, Metrics/Assumptions/Open Questions headers, and Monetization/Partner decision header plus its two gate row labels in English when surrounding prose is translated; the core-package checker treats them as machine anchors.

The owner receives one concise package review: product scope and non-goals; Must requirements and acceptance criteria; data/trust, security, AI, monetization, and partner gates; metrics and required tests; complete frontend and backend architecture; release targets; the approved stack bundle; risks; and every assumption/open question. `approved` requires an approved Stack Decision Checkpoint, no unresolved question marked `Blocks approval: Yes`, no blocked trust/AI/security/commercial gate, and no unresolved scope-changing research finding. A substantive change to those approved contents creates a new package revision and reopens this gate. Later UI evidence lives in `docs/design/ui-design.md`; it does not reopen Product Definition unless it exposes or requests a change to the approved product or stack.

#### Human Review Presentation

Before asking for Product Definition Approval, send a user-visible response with verified absolute Markdown links to the complete current PRD, architecture, and stack source; include every produced market/research artifact, its Platform Optimization Recommendations and decision statuses, and the applicable staged Deployment, Documents, and Activation seeds. Link the staging location while the candidate remains staged and canonical locations after publication. The response names what is ready and the review focus and requests an explicit approval decision. A summary, screenshot, tool-only output, panel-only open, or plain path cannot replace those links. Opening a viewer is convenience evidence only. If a linked file is missing, stale, or cannot be opened, report the blockage and do not claim approval readiness.

### Downstream UI Design

For a UI-bearing product, Product Definition ends after the approved core package is published. A later explicit `ui-design-builder` run consumes that exact revision and owns `docs/design/ui-design.md`, retained HiFi references, legacy wireframes when pinned, copy completeness, UI grading, visual approval, and the Design System Need Gate. Those artifacts never become approved merely because this PRD exists. PRD `draft` or `approved` copy responsibility tells whether UI work may proceed; it does not by itself approve final on-screen copy.

If UI design exposes a missing route, action, state, responsive obligation, or content responsibility, return it to `product-definition-builder` as a contract delta; the owner approves it as a new package revision before UI work resumes. An architecture decision or stack constraint gap needs a full package revision and Product Definition Approval.

```

## `market-research.md`

Produced by the post-draft gap pass in `market-research-guide.md`. Omit the whole file when that pass was skipped or returned blocked.

Every row that states a fact carries a source. A row with no source is marked `UNVALIDATED` and reads as a hypothesis, never as a finding.

Use this structure, keeping only the sections that apply to this product:

```markdown
# Market Research: [Product Name]

## Scope of This Research
[What was researched and what was deliberately left out. For an internal tool, name the real alternatives — the current spreadsheet, the existing internal system, doing nothing — rather than commercial products nobody would buy here.]

Researched on: [YYYY-MM-DD]

## What Exists Today
| Alternative | What it is | Who uses it | Where it falls short | Confidence | Sources |
| --- | --- | --- | --- | --- | --- |
| [Named product, in-house build, manual process, or nothing] | [One line] | [Segment] | [Observed limitation, not marketing spin] | [sourced / reported / UNVALIDATED] | [S-01] |

## Feature Baseline
| Capability | Table stakes or differentiator | Present in this PRD | Confidence | Sources |
| --- | --- | --- | --- | --- |
| [Capability] | [Table stakes / differentiator] | [Yes / No / Partial — cite PRD-*] | [sourced / reported / UNVALIDATED] | [S-02] |

## Differentiation
[The wedge against the named alternatives, and whether the drafted PRD actually delivers it. Say so plainly when it does not.]

## Pricing Reference Points
| Alternative | Model | Published price | Retrieved | Sources |
| --- | --- | --- | --- | --- |

Omit this section when the product has no commercial surface.

## Category Benchmarks
| Metric | This PRD's target | Category reference point | Confidence | Sources |
| --- | --- | --- | --- | --- |

## Market Risks
| Risk | Why it applies here | Confidence | Sources |
| --- | --- | --- | --- |
| [Incumbent response, switching cost, platform dependency, regulatory or licensing limit] | [One line] | [sourced / reported / UNVALIDATED] | [S-03] |

## Findings
| MR ID | Finding | Lands in | Recommended change | Confidence | Sources |
| --- | --- | --- | --- | --- | --- |
| MR-001 | [What the research established] | [Artifact and section] | [What should change, or "no change — confirms current draft"] | [sourced / reported / UNVALIDATED] | [S-01] |

## Platform Optimization Recommendations
Compare the pre-draft and post-draft evidence with the candidate. Keep at most five useful, ranked proposals. Use `None — [evidence-backed reason]` when evidence supports no proposal.

### Proposal 1 — [Short outcome]
- Affected PRD: [section names and existing `PRD-*`, `UX-*`, `ARCH-*`, or `TEST-*` IDs; proposed section for a new gap]
- Supporting evidence: [RA-*/MR-*]
- User problem: [one line]
- Proposed action: [add / simplify / remove / defer / other concrete action]
- Expected benefit hypothesis: [hypothesis only; no measured-benefit claim]
- Cost / dependency / tradeoff: [one line]
- Priority and rationale: [1–5 with reason]
- Validation metric or experiment: [observable signal and method]
- Decision status: `pending | accepted | revise | deferred | rejected`
- Decision rationale: [owner, decision date, and reason; leave pending until the owner decides]

## Unresolved
| Question | What was searched | What would settle it |
| --- | --- | --- |

## Sources
| Source ID | Publisher | Title | URL | Retrieved | Type |
| --- | --- | --- | --- | --- | --- |
| S-01 | [Publisher] | [Title] | [URL] | [YYYY-MM-DD] | [primary / secondary] |
```

`Lands in` names the artifact and section a finding affects, so the parent can apply it without re-reading the whole package. A finding that would widen product scope is recorded as a recommendation and raised with the user; the research role never decides scope. For Platform Optimization Recommendations, the parent applies only an owner-recorded accepted proposal. `revise` returns the proposal for explicit acceptance before a PRD change. Present verified absolute Markdown links to the complete staged PRD and recommendations before asking for choices. Deferral or rejection never clears an approval-blocking gap.

## `research-assessment.md`

Produced by the pre-draft research-first assessment. `research-first-guide.md` owns its template and gate. Omit the whole file when that pass was skipped; `PRD.md`'s `### Research Gate` then records which skip reason applied instead of citing the artifact.

Every factual row follows `market-research-guide.md`'s source rules: a source ID, or `UNVALIDATED` with what was searched. The post-draft `market-research.md` reconciles against this file rather than researching the same ground twice. The gate itself is recorded in `PRD.md`'s `### Research Gate`; this file holds the evidence behind it. A `stop` gate leaves this file in the staging directory with no drafted package.

## `docs/ACTIVATION.md`

Create this operational seed only for a package with a deployable release target and only when the final path does not already exist. In short, `product-definition-builder` creates it only when absent. Resolve the template and checker from the sibling `product-activation` skill. If that sibling is unavailable, publish the core product package without an Activation file and report the missing optional handoff; do not invent a local substitute template.

The seed must:

- retain the template's exact headings, table headers, task boundary comments, and English machine anchors;
- fill the product name and every known owner;
- select `core` plus every known surface profile, recording rejected expected profiles as `n/a` with a reason;
- list every stable release-target ID from `architecture.md`, including API/backend, Android, macOS, Windows, and other hybrid targets, without inventing a SHA or deployed identity; record a concrete Activation `n/a` disposition for a target that provably has no operational activation scope;
- add exactly one Outcome Coverage row for every `## Metrics` metric and every `TEST-*` row marked `Required: Yes`, repeating the exact structured definition/obligation, baseline, target/guardrail, measurement window, and expected-signal values, scoped to that supported Activation target subset;
- leave implementation-owned actions, routes, accounts, queries, release bindings, sources, evidence, authorization, and readiness visibly pending;
- contain secret names only and no secret values; and
- pass `python "<product-activation-skill-root>/scripts/check_activation.py" --activation <staged ACTIVATION.md> --prd <staged PRD.md> --architecture <staged architecture.md> --deployment <staged DEPLOYMENT.md> --stack-decisions <staged stack-decisions.md> --repo-root <repository-root>` before publication; the approved package and full Deployment record are one joined authority and must be staged together.

Publish a new seed flat at `docs/ACTIVATION.md` in the same approved move as the product package. Once the path exists, `product-activation` owns it. Product Definition reads it for context but never stages, overwrites, archives, resets, or treats its operational status as product approval.

## `outcomes/YYYY-MM-DD-<release-set>.md`

Produced only when the owner asks for an outcome review after a deployment, following the workflow's post-publish step. It is a post-deployment record, not part of the drafting package, and its absence from a package is normal. A saved review is immutable: write a new dated record for each review. One record covers one production release target.

Use `assets/templates/OUTCOME_REVIEW.template.md`. Run the package, Deployment and Activation checkers on their own inputs first, then validate the record with `python "<product-definition-builder-skill-root>/scripts/check_outcome_review.py" --outcome docs/product/outcomes/YYYY-MM-DD-<release-set>.md --prd docs/product/PRD.md --architecture docs/product/architecture.md --deployment docs/DEPLOYMENT.md --activation docs/ACTIVATION.md --repo-root <repository-root> --require-lifecycle`. The check joins the record to those inputs; it does not rerun them.

Rules:

- Bind the record to the exact release: the Release SHA, artifact and checked time equal the Deployment PASS row, the Activation sha256 equals the current `docs/ACTIVATION.md` bytes, and the Activation Sources table lists every matching verified `MS-*` source and only those.
- Record actual against target for every `PRD.md` `## Metrics` metric and every required `TEST-*` expected signal. Baseline, target and any numeric window duration must equal the PRD row. An empty or duplicate Measurements table means the review is not done.
- The measurement window is real elapsed time after deployment, uses real calendar dates, closes on or before the review date, and cannot extend into the future. A review written at deploy time with "pending" actuals is a stub, not a verdict.
- An incident requires typed containment, a human owner, and explicit routing into the next Product Definition `PRD Risks` and `PRD Open Questions`.
- The verdict vocabulary is closed: `no_change`, `enhancement`, or `incident`. Every later run reads this file in full during enhancement detection.

## `docs/product/deltas/PRD-DELTA-<EPIC-ID>.md`

An enhancement round that changes the approved package records itself in a PRD delta with schema `prd-delta/1`. `<EPIC-ID>` is the Epic file's id token: `EPIC-041` for `docs/epics/EPIC-041-<slug>.md`. One delta per round, aligned one-to-one with that round's Epic. `PRD.md` keeps only the approved state; the delta holds the round's why, impact, before/after, and approval. Create it from `assets/templates/PRD_DELTA.template.md` at the start of the round with the baseline hash, and publish the delta, the PRD, and their review copies together.

Use this structure:

```markdown
# PRD Delta <EPIC-ID>: <outcome in one line>

| | |
| --- | --- |
| Epic | docs/epics/EPIC-<id>-<slug>.md |
| Baseline PRD | sha256:<64 lowercase hex of PRD.md before this delta> |
| Result PRD | sha256:<64 lowercase hex after publication> or pending |
| Status | draft / approved |
| Ambition rung | 1 / 2 / 3 — <one line naming the rung from the PRD Ambition ladder> |

## Why
[Owner request, date and source; the goal beyond the goal this round serves.]

## Enhancement Impact Record
[The table from `## PRD.md`, unchanged columns.]

## Changed Requirements
| ID | Change | Before | After | TEST IDs |
| --- | --- | --- | --- | --- |
| PRD-0xx | new / revised / retired | [summary or n/a] | [summary] | TEST-0xx |

## Decisions
- decision:<slug> — [one line]

## Approval
[Product Definition Approval for this delta: owner, date, result PRD hash, using the same `product-definition-approval` marker block convention as PRD.md.]
```

A `Baseline PRD` or `Result PRD` hash is the SHA-256 of `PRD.md`'s file text without the `product-definition-approval` marker block, exactly as `bilingual-review.md` defines the review-source hash. The delta's own hash excludes its marker block. Each published delta receives a complete `PRD-DELTA-<EPIC-ID>.zh-TW.md` review copy; `bilingual-review.md` owns the pairing.

Once a package has `docs/product/deltas/`:

- A `PRD.md` heading containing a `YYYY-MM-DD` date is forbidden. Dated round history lives in the deltas.
- `## Enhancement Impact Record` lives in the delta, not in `PRD.md`.
- `## Product Definition Decisions` carries one line `Latest delta: docs/product/deltas/PRD-DELTA-<EPIC-ID>.md` naming the current round's delta.

A new round adds a new delta and updates that line. Whole-package replacement keeps the archive steps in `artifact-lifecycle.md`. A bounded enhancement needs no whole-package archive: the delta's before/after rows plus Git are the history.

## `architecture.md`

Use this structure:

Keep the required level-two headings below in English when surrounding prose is translated; they are core-package checker anchors.

Architecture Summary, Product Archetype, System Context, Component Architecture, Workflow and Data Flow, Auth/Permissions/Security, Deployment and Operations, Observability, Scaling/Reliability, Technical Risks/Tradeoffs, and Architecture Trace Index are mandatory and cannot be replaced with `not_required`. Frontend, Backend, Data Model, API/Interface, Data and Trust, AI/Automation, Integrations, and Monetization/Partner architecture may use exactly `not_required — <concrete reason>` only when the corresponding product surface or approved gate is genuinely not applicable. A `required` PRD gate always forbids `not_required` in its architecture section.

```markdown
# Architecture: [Product Name]

## Architecture Summary
[Implementation-ready overview in a few sentences: the main pieces, what talks to what, and the one or two decisions that constrain everything else.]

Technology selections and their rationale live in `stack-decisions.md`.

## Product Archetype
[Web app, mobile app, desktop app, browser extension, internal tool, automation or agent workflow, API or hybrid. Record mobile/desktop operating-system destinations and browser-extension targets separately from native/cross-platform strategy, framework, and toolchain; reference the approved stack rows rather than flattening those layers here.]

## System Context
[Actors, systems, dependencies.]

## Component Architecture
| ARCH ID | Component | Responsibility | Upstream trace IDs | Notes |
| --- | --- | --- | --- | --- |

## Frontend Architecture
For every product that ships a frontend, describe in a few lines: surface composition (which surfaces exist and how they group), the state and data-fetch approach, routing, and build/bundling. Reference the recorded layers in `stack-decisions.md` instead of restating them. Omit this section only when the product ships no frontend at all.

## Backend Architecture
Describe in a few lines: service boundaries, API style, data access, and background jobs when they exist, referencing `stack-decisions.md` rather than duplicating its decisions. For a product with no backend, this section is one line stating that there is no backend and why.

## Data Model
| Entity | Key Fields | Relationships | Notes |
| --- | --- | --- | --- |

## API and Interface Contracts
| ARCH ID | Interface | Method or Trigger | Input | Output | Errors | TEST IDs |
| --- | --- | --- | --- | --- | --- | --- |

## Workflow and Data Flow
[Describe request, background job, event, and integration flows.]

## Auth, Permissions, and Security
[Authentication, authorization, secrets, audit, privacy, and abuse-case enforcement. For each required PRD Security Requirements row, explain how the named control is enforced at this boundary using the same PRD and TEST IDs; negative tests prove denial and no unauthorized side effects.]

## Data and Trust Architecture
[Implement the PRD Data and Trust Gate: data classification and ownership, source of truth, storage/processing regions, vendor boundaries, encryption, access/audit, retention, deletion/export, consent/policy, backup/recovery, and incident ownership. When the gate is `not_required`, state the PRD reason. A `blocked` gate cannot reach Product Definition Approval.]

## AI and Automation Architecture
[Implement the PRD AI and Automation Gate: model/provider and version boundary, allowed context and retrieval sources, prompt/tool trust boundaries, side-effect approvals, evaluation and output validation, cost/latency budgets, observability, fallback/shutoff, and incident handling. When the gate is `not_required`, state the PRD reason. A `blocked` gate cannot reach Product Definition Approval.]

## Integrations
| System | Purpose | Data exchanged | Auth / scopes | Contract / limits | Failure / recovery | Owner |
| --- | --- | --- | --- | --- | --- | --- |

## Monetization and Partner Channel Architecture
[If both PRD gates are `not_required`, state that with the PRD reasons. Otherwise define product/price, order/invoice, purchase/subscription, entitlement, partner, referral/lead/deal, commission/discount, payout, refund, and chargeback ownership as applicable; identity joins; purchase and partner event flows; verified idempotent webhooks; replay/out-of-order handling; reconciliation; entitlement grant/revoke/restore; commission reversal; reseller provisioning/deprovisioning and delegated administration; environment separation; and external-console responsibilities. Reference the separate layers selected in `stack-decisions.md`.]

## Deployment and Operations
[Hosting, environments, config, migrations, queues, cron, rollback.]

Record initial deployment and measurement prerequisites, their owners, dependent work and evidence in the existing sections and `docs/DEPLOYMENT.md`.
Use the fixed initial build for authorized setup; keep later release availability and unknown platform artifacts pending.

For every deployable hosted web, API, or backend target, include this environment contract (Cloudflare Worker naming shown as the worked example; substitute the resolved platform's equivalent deployment unit). Do not use this two-row hosted-environment table for native mobile or desktop store/signed-installer distribution:

| Target | Exact Release Source | Deployment Unit | Data / Bindings / Secrets | Auth Mode | Payment Mode | Migration Order | Deployed Verification | Rollback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Development | [Exact PR/branch candidate and verified deployment SHA] | [`<product-slug>-<surface-suffix>-dev`] | [Isolated non-production resources] | [Development] | [Sandbox or not applicable] | [Classification, command, and ordering or not applicable] | [Internal suite, URL, deployed SHA, smoke, evidence] | [Prior development version] |
| Production | [Verified main landing SHA after candidate Preview acceptance and separate promotion read-back] | [`<product-slug>-<surface-suffix>`; never add `-prod`] | [Production resources] | [Production] | [Live or not applicable] | [Classification, command, and ordering or not applicable] | [URL, deployed SHA, production smoke, evidence] | [Prior production version] |

State that both hosted targets use one repository and one codebase. Do not reuse production data, sessions, secrets, or live payment mutations in development. Write each Migration Order cell so the human or CI release process can run it in order.

## Release Targets

New packages record `Release source policy: main-preview/1` immediately below this heading. The development target uses `stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha`; production uses `stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha`. Development is an isolated Preview or test channel, not a permanent Git branch. Historical `dual-branch/1` keeps `refs/heads/development` and `promotion.verified_development_sha`; markerless historical packages keep `candidate/1`. Allow at most one matching active marker. A logical `-dev` release name need not equal a provider-generated Preview name or URL.

Use this provider-neutral section for every deployable web, API, mobile, desktop, or browser-extension surface, including hosted targets already summarized in the environment table above. First record the complete expected deployable-surface inventory using stable surface IDs. Then record one block per exact destination and give it a stable target ID, explicit lowercase kebab-case surface suffix, and lowercase kebab-case release name. The production release name is the canonical `<product-slug>-<surface-suffix>` name and never ends in `-prod`; development uses that exact name plus `-dev`; one release name cannot belong to multiple surface IDs. Use the surface suffix guidance in `architecture-playbook.md` for web, API, extension, native, and independently released supporting units. Every expected surface needs at least one `development` target and one `production` target; a package that omits an expected surface is incomplete. Keep the stable `surface` identity separate from `provider`, because one surface may use different providers by stage. Keep surface and target IDs stable across revisions; retire rather than reuse an ID when its meaning changes.

This section is authoritative product documentation for the human or CI release process. The Product Definition checker and downstream Deployment, Activation, Outcome, and SEO joins consume its stable target identities.

Expected deployable surfaces: [stable surface IDs, for example `web-app`, `public-api`, `ios-app`]

### Release Target: [stable-target-id]
- Surface: [Stable expected surface ID]
- Surface class: [one class from the Surface Catalog: hosted_web / hosted_api / browser_extension / ios / android / macos / windows / worker / job / webhook / realtime / cli / agent / mcp_server / skill_or_plugin / library_or_sdk / messaging_bot / marketplace_app / assistant_listing / container_or_self_hosted / internal_service / other_nonpublic]
- Public discoverability: [yes / no]
- Surface suffix: [Lowercase kebab-case suffix for this independently released unit]
- Release name: [Production `<product-slug>-<surface-suffix>` or that exact name plus `-dev` for development]
- Provider: [Stage-specific hosting, store, or distribution provider]
- Stage: [development / production]
- Source policy: [`stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha` for main-preview/1 or legacy development, `stage=development; ref=refs/heads/development; sha=promotion.verified_development_sha` for dual-branch development, or `stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha` for production]
- Artifact kind: [Static bundle, container, serverless bundle, API service, IPA, AAB, signed DMG/PKG, MSIX, signed installer, or another exact artifact]
- Signing requirement: [Not required, or exact certificate/signing/notarization requirement and owner]
- Exact channel / track: [Named environment, URL, TestFlight group, Play track, App Store, update feed, direct-download channel, or another exact destination]
- Submission / promotion / review / manual approval path: [Ordered gates and decision owner]
- Availability signal: [Observable proof that the intended audience can reach, install, or download this exact release, plus the smoke/acceptance signal]
- Rollout: [Immediate, percentage/phased/staged rollout, audience ring, or another controlled sequence]
- Rollback / forward-fix: [Prior deployed version for instant rollback, or rollout halt/removal plus corrected signed artifact through the same review/distribution path]

A successful build, upload, submission, deployment command, notarization, or store approval is not availability by itself. Hosted availability requires the deployed route or API to answer the named smoke checks. Store and signed-installer availability requires the approved artifact to be actually installable or downloadable through the named channel and to pass its release smoke check. Native recovery may require halting a phased or staged rollout and shipping a signed forward-fix; do not promise web-style rollback when the channel cannot perform it.

For an owner-selected whole-platform sequence, add this opt-in section after Release Targets. It orders implementation only after the PRD records every platform's requirements, UI surfaces, and tests. A shared API or interface appears in the stage that first makes it available; shared ARCH IDs must be authority rows. The stage surfaces cover the expected inventory exactly once. `not_required` is valid only for one user-facing surface class, with a concrete reason. Draft and blocked statuses stay non-executable.

## Platform Delivery Sequence
Platform delivery contract: platform-delivery/1
Delivery mode: whole_platform_sequential
Decision owner: [Human owner]
Decision status: approved
Shared surfaces: [Expected surface IDs or leave empty]
Shared interface ARCH IDs: [ARCH-* authority IDs or leave empty]

| Order | Stage | Release surfaces | Required TEST IDs | Completion signal |
| --- | --- | --- | --- | --- |
| 1 | [Stage ID] | [Expected surface IDs] | [Required TEST IDs] | [Observable completion signal] |

Keep this section absent for legacy packages. A visible contract marker always validates. Malformed fields, unsupported protocols, duplicate stages or surfaces, omitted inventory, unknown references, hidden example markers, and non-required TEST IDs fail closed.

## Observability
[Logs, metrics, traces, alerts, dashboards, audit events.]

## Scaling and Reliability
[Expected load, bottlenecks, caching, retries, idempotency, disaster recovery.]

## Technical Risks and Tradeoffs
| Decision | Options Considered | Recommendation | Reason |
| --- | --- | --- | --- |

---

## Architecture Trace Index
Coverage matrix. Fill it last and read it only when checking that a requirement reached implementation.

| ARCH ID | Contract or decision | Upstream PRD / UX IDs | Downstream UI / TEST IDs |
| --- | --- | --- | --- |
| ARCH-001 | [Stable architecture contract] | PRD-001 | UI-001, TEST-001 |
```

## `stack-decisions.md`

Every decision in this file uses the same shape: drivers, coherent bundles presented to the owner, then resolved layers with status and authority/evidence on every row. The shared `Alternatives Considered` and `Unresolved Decision Protocol` tables cover all decisions.

Use these statuses per layer: `Required` means a user, organization, or hard external constraint mandates the selection; `Selected` means the current product or repository already adopted it; `Approved` means the human owner accepted a new choice directly or through an explicit recorded delegation; `Recommended` is evidence-backed advice not yet accepted and is non-executable; `Provisional` is a leading choice pending named evidence. Only `Required`, `Selected`, and `Approved` are executable. A section may mix statuses. `Authority / evidence` cites the source that justifies the row. A `Selected` row uses `repository:<repo-relative-path>@<40-character-commit-SHA>` when the path is bound to a real Git revision, or `repository:<repo-relative-path>@sha256:<64-character-current-content-hash>` for current non-Git evidence; the checker resolves the path and revision/hash under `--repo-root` through a standalone exact-SHA Git boundary that disables config injection, rejects repository identity overrides, and fails closed on replace refs or grafts. Authority is not another status label, and recommendation text alone is not approval.

Use this structure:

```markdown
# Stack Decisions: [Product Name]

<!-- stack-decision-checkpoint:start -->
## Stack Decision Checkpoint
- Decision: [approved / revision_requested / blocked]
- Decision owner: [Human owner]
- Decided on: [YYYY-MM-DD]
- Approved areas: [Frontend / Mobile or desktop / Backend or data / AI or automation / Monetization or partner channel / Toolchain / none]
- Delegated choices: [None / exact decision classes explicitly delegated and source]
- Open areas: [None / exact unresolved areas]
- Checkpoint digest: [sha256:<64 lowercase hex> over the raw stack text, including fenced, indented and commented content; only this checkpoint block is excluded]
- Applicable areas: [Exact release-surface and gate applicability]
- Resolved areas: [Exact areas closed by this checkpoint]
- Approved option map: [OPT-ID=layer=>selection;layer=>selection entries, exactly matching approved executable layer selections. Use the explicit `||` map form `||OPT-ID=...||OPT-ID=...||` when a layer name or selection contains a comma; comma-only legacy maps remain readable. The Product Definition author derives this candidate from the recorded rows; only the owner's accepted checkpoint and canonical digest binding make it approved]
<!-- stack-decision-checkpoint:end -->

Keep the `Stack Decisions` title, this marker pair and fields, the Coherent Options header, every `Recorded or Approved Stack` heading, and layer-table header in English in a translated package; they are machine anchors.

For example, one commercial option can use `||OPT-MP-01=attribution, commission, payout, and reseller operations=>First-party ledger, monthly payout;billing=>None||`. Explicit maps require both outer `||` markers. Inside them, `||` separates options and `;` separates layers; these delimiters and `=>` are reserved syntax. Layer names and selections must be nonempty, and option IDs and layer names must be unique within their respective map and option.

Write the map only after recording an accepted new bundle. A package with only `Selected`/`Required` layers and no approved option keeps `Approved option map: None`. The checker accepts this sentinel case-insensitively and does not require an options table. A newly approved layer or option still requires its complete option evidence and exact map. Run the product-package checker to verify the map and repository authority; authoring the map does not establish either.

Before this checkpoint, present two or three coherent bundles for every applicable unresolved area. Each bundle names all coupled layers, fit, tradeoffs, operating and maintenance ownership, cost/license/data constraints, serious alternatives, and revisit triggers. The owner may approve the recommendation, modify layers, or rely on an explicit prior delegation. `Recommended` and `Provisional` rows keep this checkpoint blocked.

### Coherent Options Presented
Use this shared table for every unresolved area before the checkpoint. Preserve the complete option the owner accepted as well as rejected serious alternatives; do not record only the winning framework name.

| Option ID | Area | Complete bundle | Best fit | Tradeoffs / ownership | Disposition |
| --- | --- | --- | --- | --- | --- |
| OPT-FE-01 | [Frontend / Backend or data / Mobile or desktop / AI or automation / Commercial / Toolchain] | [Every coupled layer in this option] | [Why and when it fits] | [Cost, lock-in, data, maintenance, operations] | [recommended / approved / rejected] |

## Frontend Technology Decision
Use this section for every product with a browser frontend. Omit it only when no browser surface exists.

### Decision Drivers
- [Product evidence that determines the choice: content density, interactivity, SEO, rendering, auth, edge data, team capability, reuse, performance, and deployment constraints.]

### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Deployment / runtime | [e.g. Cloudflare Workers with Static Assets] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Rendering model | [Static, SSG, SSR, on-demand, SPA, islands, or hybrid by route] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Language | [TypeScript / JavaScript / another exact choice] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Package manager | [npm / pnpm / Yarn / Bun / another exact choice] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Framework | [e.g. Astro, React Router, or none] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| UI library | [e.g. React or none] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Component foundation | [e.g. shadcn/ui owned source, headless primitives, packaged suite, or custom] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Styling approach | [Tailwind CSS / CSS Modules / modern vanilla CSS / another exact choice] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Build tool | [e.g. Vite, or framework-managed] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Routing and data | [Approach] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Testing | [Unit, component, end-to-end, accessibility] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |

### Rendering and Route Strategy
| Route Group | Rendering | Data Source | Cache / Freshness | Auth Boundary | Rationale |
| --- | --- | --- | --- | --- | --- |

### Platform Compatibility Verification
- Checked on: [YYYY-MM-DD]
- Official sources: [Direct links]
- Runtime/build requirements: [Compatibility date, Node version, adapter/plugin, bindings, asset routing, or other constraints]

## Mobile/Desktop Technology Decision
A product may add this section in a later revision after Frontend Technology Decision is already frozen, when a mobile or desktop target is added to an existing web product; freezing this section does not reopen or require revisiting the already-frozen Frontend Technology Decision. Use this section for every product with a mobile app or desktop app target (native iOS, native Android, Flutter, React Native, macOS, Windows, or cross-platform desktop) — omit it when no such target exists.

### Decision Drivers
- [Product evidence that determines the choice, weighed per `references/mobile-stack-selection.md`: target platforms and reach, native capability needs, offline/sync requirements, team capability, code reuse with an existing web frontend, distribution and store constraints, and performance expectations.]

### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Target operating systems | [iOS / Android / both / macOS / Windows / exact set] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Client strategy | [Platform-native / cross-platform] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Framework | [SwiftUI / Jetpack Compose / Flutter / React Native / Tauri / Electron / exact choice] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Styling approach | [platform theme / another exact choice] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Toolchain | [Xcode / Android Studio / Flutter-Dart / Expo or bare React Native / desktop equivalent] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Navigation and state | [Approach] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Local persistence | [Approach] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Secure storage | [Approach] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Offline sync | [Approach or n/a] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Push and native modules | [Approach or n/a] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Backend/API integration | [Approach] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Distribution mechanism | [Store/test track, signing/build service, installer/update feed] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Testing | [Unit and UI automation per platform] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |

Compatibility checked on: [YYYY-MM-DD] — official sources: [Direct links]

## CLI and Toolchain Decision
Use this section for `cli`, `mcp_server`, `skill_or_plugin`, `library_or_sdk`, `container_or_self_hosted`, `internal_service` and `other_nonpublic` release surfaces. All map to the single canonical `Toolchain` area in Approved, Applicable, Resolved, and Coherent Options records; `CLI/toolchain` is accepted as an alias. A hybrid containing several of these classes still declares the area once. Keep activation profile names separate from stack areas.

### Decision Drivers
- [Target platforms, command/interface contract, packaging, distribution, upgrade policy, and team constraints.]

### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Language | [Selection] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Toolchain | [Runtime/compiler and build/package tooling] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Distribution mechanism | [Package registry, signed binary, or internal artifact channel] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Testing | [Command/interface and platform checks] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |

## Backend and Data Technology Decision
Use this section for every product with a backend, persistent data, or auth requirement. Omit it only when the product provably has none of these.

### Decision Drivers
- [Data shape/relationships, consistency/transaction needs, query complexity, scale, identity/compliance requirements, team capability, platform-managed services, integration surface.]

### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Service topology | [Monolith or named services; monorepo or polyrepo organization] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Backend runtime / framework | [Selection] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Database category | [Relational / Document / Key-value or cache only / None] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Database engine | [Selection] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Auth strategy | [Build custom / Managed third-party / Platform-native / None] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Auth provider | [Selection] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| API style | [REST / GraphQL / RPC / server actions] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Background jobs / queue | [Selection or not applicable] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| File / object storage | [Selection or not applicable] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |

### Data Entity to Store Mapping
| Entity | Store | Rationale |
| --- | --- | --- |

### Platform and Vendor Compatibility Verification
- Checked on: [YYYY-MM-DD]
- Official sources: [Direct links]
- Runtime/service requirements: [Bindings, connection limits, region/residency, quota, or other constraints]

## AI and Automation Technology Decision
Include this section only when the PRD's AI and Automation Gate is `required`.

### Decision Drivers
- [Capability, data classification, context/retrieval, tool permissions, evaluation thresholds, prohibited outcomes, cost/latency, observability, fallback/shutoff, provider terms, and team ownership.]

### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Model / automation provider | [Selection] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Model and version policy | [Pinned/rolling model, change and evaluation policy] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Context / retrieval | [Selection or n/a] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Tool execution and approvals | [Execution shape; SDK; durable state/resume; tool/sandbox boundary; allowlist; human gates] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Evaluation and output validation | [Harness, dataset, schemas/policies] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Observability and cost controls | [Tracing, budgets, alerts] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Fallback and shutoff | [Selection] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |

Compatibility checked on: [YYYY-MM-DD] — official sources: [Direct links]

## Monetization and Partner Channel Technology Decision
Always record the two PRD gate results here. When both are `not_required`, state their reasons and omit the layer table. Otherwise use `monetization-and-partner-channel-guide.md`, compare only current options that fit the resolved model and surfaces, and keep responsibilities separate.

### Decision Drivers
- [Commercial model, buyer, pricing/offer rules, purchase surfaces, entitlement needs, merchant-of-record/tax responsibility, partner motion, attribution/commission/payout, reseller operations, existing systems, team capacity, and current official provider evidence.]

### Recorded or Approved Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Store commerce / billing | [Native store, RevenueCat Billing, Stripe Billing, Paddle Billing, Lemon Squeezy, existing, custom, or n/a] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Subscription and entitlement source | [RevenueCat, Qonversion, Superwall, native/custom, existing, or n/a] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Paywall / checkout | [Adapty, Superwall, RevenueCat, provider checkout, custom, or n/a] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Merchant of record / tax | [Product company, Paddle, Lemon Squeezy, Stripe arrangement, other, or n/a] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Affiliate / referral / reseller platform | [PartnerStack, Rewardful, FirstPromoter, Lemon Squeezy Affiliates, custom, existing, or n/a] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Attribution, commission, payout, and reseller operations | [Provider/custom boundary] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |

Compatibility checked on: [YYYY-MM-DD] — official sources: [Direct links]

---

## Options And Open Decisions

### Alternatives Considered
One row per rejected option, across every decision above.

| Area | Alternative | Where It Fits Better | Why Not Selected Here | Revisit Trigger |
| --- | --- | --- | --- | --- |
| [Frontend / Mobile or desktop / Backend or data / Toolchain / AI or automation / Monetization or partner channel] | [Alternative or coherent bundle] | [Context] | [Reason] | [Trigger] |

### Unresolved Decision Protocol
Use only when a layer cannot yet be decided. A bare `TBD` does not pass validation.

| Area | Open Decision | Missing Evidence | Owner | Decision Date | Time-boxed Spike | Pass / Fail Criteria |
| --- | --- | --- | --- | --- | --- | --- |
```

## Optional UI Design Handoff

Stop after Product Definition Approval. When the owner later asks to design the UI, invoke `../ui-design-builder/SKILL.md` with the approved PRD, architecture, and stack paths. It asks UI, style, motion, and media questions; creates comparable direction studies with `frontend-design`; after owner selection, authors complete HiFi and checks PRD coverage and sourced copy; runs Impeccable HiFi review plus H1–H9 grading; obtains visual approval; and invokes `design-system-compiler` only when its later gate is `required`.

## Optional `implementation-plan.md`

Create this file only when explicitly requested.

Use this structure:

```markdown
# Implementation Plan: [Product Name]

## Delivery Strategy
[How to sequence the build.]

## Milestones
| Milestone | Scope | Exit Criteria |
| --- | --- | --- |

## Dependency Order
1. [Foundational dependency]
2. [Next dependency]

Order applicable AEO, deployment and measurement foundations before features that need them. Independent work may continue during external setup blockers.

## Engineering Tasks
| Area | Task | Owner Type | Notes |
| --- | --- | --- | --- |

## Release Plan
[Launch, feature flags, migration, rollout, support. Reuse the stable release target IDs from `architecture.md`; do not rename destinations in the plan.]

## Rollback Plan
[How to revert safely.]

## Unresolved Decisions
- [Decision needed]

---

## Harness Handoff Signals
These are planning hints, not a canonical Harness PLAN or RUN graph.

| Work area | Upstream trace IDs | Prerequisites | Parallel candidate | Shared or exclusive resources | Required review / evidence | Human gate |
| --- | --- | --- | --- | --- | --- | --- |
| [Area] | PRD-001, ARCH-001, UI-001 | [Contract or prior outcome] | [yes / no / conditional] | [Schema, generated client, port, database, external service, or none known] | [Frontend/backend/visual/E2E/security] | [Decision or none] |

## Test Strategy
Reuse the canonical `TEST-*` IDs from `PRD.md`'s `## Test Obligations` table. Sequence or add implementation detail to those obligations; do not create anonymous checks or replacement TEST IDs.

| TEST ID | Test Type | Coverage | Upstream trace IDs | Acceptance Signal |
| --- | --- | --- | --- | --- |
| TEST-001 | [Unit / integration / E2E / performance / security / visual / accessibility] | [Implementation coverage for the existing obligation] | PRD-001, ARCH-001, UI-001 | [Same pass signal, with implementation detail if needed] |
```

## Quality Checklist

Before archiving earlier documents or publishing the staged package, verify:

### Readability

- Each artifact opens with human-readable content and keeps decision records near the end: `PRD.md` opens with `## At a Glance`, records `## UI Design Handoff Status`, and closes with `## Product Definition Decisions`; `architecture.md` opens with `## Architecture Summary` and closes with `## Architecture Trace Index`; `stack-decisions.md` opens with its machine-anchored Stack Decision Checkpoint and closes with `## Options And Open Decisions`.
- `## At a Glance` answers what the product is, who it is for, why now, what success looks like, and the biggest risk — one line each, on one screen.
- Each artifact is within reach of its length budget in "How To Read This Package". A file well over budget names which content should have moved to another artifact instead of expanding.
- No table in the package exceeds seven columns except the environment contract in `architecture.md`, whose columns are all release-critical, and the Metrics table's `Stretch` column.

### Completeness

- Before first-delivery approval, the one author self-review applies the UI and technical perspectives of `prd-refinement.md` to complete journeys and cross-feature dependencies. Findings retain evidence, stable IDs and dispositions; required gaps cannot be silently deferred. Later findings follow the same rule without rewriting frozen approvals.
- `PRD.md`, `architecture.md`, and `stack-decisions.md` are present in the run-specific staging directory with Product Definition Approval and Stack Decision Checkpoint both `approved`. Run `python "<product-definition-builder-skill-root>/scripts/check_product_package.py" --prd <staged PRD.md> --architecture <staged architecture.md> --stack-decisions <staged stack-decisions.md> --repo-root <repository-root> --require-filled --require-approved` before publication; new packages add `--eval-policy eval-policy/1`, and new whole-platform authoring adds `--platform-delivery platform-delivery/1`. It validates the structure, Must/NFR-to-TEST coverage, Security Requirements traces, release-target identity, metrics, decision tables, approval markers, executable stack statuses, live `Selected` evidence, and blocked gates. The staged operational documents follow their existing applicability rules. UI-bearing packages record a pending `ui-design-builder` handoff; headless packages record `not_required` without skipping Product Definition Approval.
- Non-functional requirements name a measure and target; vague adjectives alone do not pass.
- Required trust, security, AI, monetization, and partner gates carry into architecture, stack decisions, UI surfaces, and `TEST-*` obligations, including failure and termination states.
- A UI-bearing `PRD.md` records the human owner for later UI design and complete surfaces, actions, states, responsive obligations, copy responsibilities, accessibility, and recovery behavior. It contains no guessed layout, style, motion/media treatment, wireframe approval, or design token. UI preference is not presented as user validation.
- A hosted target records the platform resolved during interview (via `AskUserQuestion` unless the user or repository already named one; never a silent default) and one codebase with separate development and production environments.
- The database category and auth strategy trace back to the interview's `AskUserQuestion` answers rather than a silent default.
- A pricing strategy never silently selects RevenueCat; `stack-decisions.md` compares current providers through `monetization-and-partner-channel-guide.md` and keeps affiliate, referral, and reseller distinct.
- If produced, `implementation-plan.md` reuses the canonical `TEST-*` IDs and stable release target IDs. It does not replace them with anonymous checks or renamed destinations.
- The market-research gap pass completes or records its skip/block reason before Stack Decision and Product Definition approval, and its queries pass the Research Disclosure Check. A new package records a `### Research Gate`; an enhancement cites the prior gate unchanged and researches only the delta.
- When the pass was skipped or blocked, `PRD.md`'s `## Assumptions` records that the market context is unvalidated. Findings that changed the package cite their `MR-*` IDs, and `PRD.md` states conclusions rather than restating the competitor table. Findings that would widen scope are open questions or recommendations, not silent changes.

### Publication

- No current-package artifact will be published outside `docs/product/` unless the user explicitly requested another location.
- The superseded-document inventory excludes `docs/product/archived/`, unrelated documents, and ambiguous candidates.
- In enhancement mode, unaffected sections, `PRD-*`, `ARCH-*`, `UI-*`, `UX-*`, `TEST-*`, `MR-*`, `RA-*` IDs, and stable release target IDs from the prior package were carried forward unchanged rather than regenerated, and the diff is scoped to what the new discovery actually added, changed, or removed; new TEST IDs cover only obligations that were previously uncovered, and new release target IDs cover only destinations that were previously uncovered.
- Validation does not trigger publication by itself. Exact overwrite and archive moves are already authorized, or the staged package remains unchanged while approval is requested.
- After publication, the completion response uses verified absolute Markdown links to the final canonical package and applicable operational/context files; the approval response itself retains the staging links that the owner actually reviewed.


## Operations For New Design Rounds

For `ui-design/3` or `ui-design/2` preflight (and legacy wireframes/5), each UI surface includes the invariant `operations` anchor described in `../../ui-design-builder/references/review-workflow.md#required-product-operations`. Derive required navigation, menus, tabs and recovery from product tasks before design. Product Definition review must reconcile this list with the user tasks. The first `UI-*` entry is the entry surface; HiFi renders it on `index.html`. For `ui-design/3`, the checker fails a surface that operations cannot reach from the entry surface. It also fails a state that an operation opens as a page, overlay, state or tab when no operation leaves that state. Feedback is transient. A surface with `none — <reason>` is terminal. Run `check_product_package.py --require-filled --require-approved --repo-root <root> --ui-contract ui-design/3` (or `ui-design/2` for a retained package) with the three product paths before current direction work. UI validation joins these requirements directly to the HiFi manifest and controls; a missing operation fails before visual review. Legacy packages keep the wireframe join.

# Output Contract

Produce a core multi-file Markdown PRD package. Stage and publish it according to `artifact-lifecycle.md`. The final package belongs under `docs/product/`. Use exactly these core artifact names unless the user requests different names:

- `docs/product/PRD.md`
- `docs/product/architecture.md`
- `docs/product/stack-decisions.md`

Every package passes a human Product Definition Approval before UI design or implementation. The owner approves product scope, measurable requirements, complete frontend and backend architecture, applicable trust/AI/commercial gates, resolved stack choices, release targets, accepted assumptions, and non-blocking open questions as one named package revision. A UI-bearing product then stops for a later explicit `ui-design-builder` request. A headless product records UI design as `not_required` but still passes Product Definition Approval.

This contract covers the owner-approved product, architecture, technology stack, and required UI behavior. It does not require a wireframe, visual direction, motion/media treatment, preview, token set, or design-system rules. Those belong to `ui-design-builder` and, when needed, `design-system-compiler`.

It also publishes `docs/product/market-research.md` when the post-draft market-research gap pass ran and returned findings. That pass runs before Stack Decision and Product Definition approval so its findings cannot silently stale an accepted package. When the user declined it, no web tool was available, confidential context prevented a safe query, or the role returned blocked, the package records that state explicitly. See `market-research-guide.md`.

For a product with any deployable web, API/backend, mobile, desktop, or browser-extension release target, it also creates a one-time operational seed at `docs/ACTIVATION.md` from the sibling `product-activation` template when that path is absent. The seed maps release targets, every PRD metric, and every required `TEST-*` signal, but it contains no external authorization, account guess, secret value, or claim that a source is verified. An existing Activation record is owned by `product-activation` and is preserved byte-for-byte during product enhancement.

It specifies what each UI surface must show and do. It does not decide how the surface is composed or styled and creates no HTML reviewer.

`PRD.md` is the canonical source for product scope, routes, screen purpose, content responsibility, actions, states, responsive obligations, flows, trace IDs, trust/AI gates, and Product Definition Approval. `architecture.md` fixes frontend and backend structure, and `stack-decisions.md` records the separate Stack Decision Checkpoint. Later UI artifacts never override the approved Product Definition revision.

Produce `docs/product/implementation-plan.md` only when the user explicitly asks for delivery sequencing or implementation planning.

Default all artifact content to English unless the user explicitly asks for another language.

## How To Read This Package

Every artifact has one primary reader and one job. Write for that reader.

| Artifact | Primary reader | Answers |
| --- | --- | --- |
| `PRD.md` | The owner and anyone deciding whether to build this | What it is, for whom, what counts as done, and whether the product definition is approved |
| `architecture.md` | An engineer about to implement | How the system is shaped and where the risk is |
| `stack-decisions.md` | The owner and engineer choosing or reviewing technology | Which coherent options were considered, what the owner approved, and why |
| `market-research.md` | Anyone questioning a product claim in `PRD.md` | What already exists out there, and what the evidence is |
| `research-assessment.md` | Anyone deciding whether this product should have been drafted | What the pre-draft evidence supported, and what the gate decided |
| `outcome-review.md` | The owner deciding what happens after a release | What actually happened post-deployment, measured against the targets, and the verdict |
| `docs/DEPLOYMENT.md` | The human operator preparing and checking a release | Which secret and variable names go where, which external consoles need work, and what actually deployed |
| `docs/ACTIVATION.md` | The owner or operator activating a delivered release | Which external actions and measurement sources are pending, configured, verified, blocked, or stale |
| `docs/DOCUMENTS.md` | Anyone locating flow artifacts | Which documents exist, who owns them, and their current status |

Core decision order is `PRD.md` → `architecture.md` → `stack-decisions.md`. For UI products, `docs/design/ui-design.md` and `docs/design/wireframes.html` are later downstream inputs. Optional UI/design-system and operational records never override Product Definition. Research artifacts hold evidence behind cited `RA-*` and `MR-*` findings.

Two rules keep the package readable:

- **Meaning before bookkeeping.** Each file opens with what a human needs to understand the product and ends with the ID matrices and decision records that machines, auditors, and downstream skills need. Never open a file with a trace table.
- **One notation per block.** Prose, ASCII, and ID tables do not interleave inside a section. A table wider than seven columns is a sign the content wants to be a list instead.

Length budget. These are targets, not caps — say less when the product is simple, and go over only when the product is genuinely more complex, not when a section drifted:

- `PRD.md`: about 200 lines. `## At a Glance` fits on one screen.
- `architecture.md`: about 250 lines.
- `stack-decisions.md`: about 150 lines.
- `market-research.md`: about 150 lines. Findings and sources, not an industry report.
- `research-assessment.md`: about 80 lines. Evidence and the gate decision, not a duplicate of the post-draft research.
- `outcome-review.md`: about 60 lines. Deployed facts and the verdict, not a status report.

When a section runs past its share, the usual cause is detail that belongs in a different artifact. Move it before expanding the file.

## `PRD.md`

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

[One paragraph describing the product, user, and outcome.]

## Enhancement Impact Record
Include this section only in enhancement mode.

| Area | Impact | Affected IDs / decisions | Required refresh |
| --- | --- | --- | --- |
| Product scope / behavior | [unchanged / changed] | [IDs or none] | [Artifacts and gates or none] |
| UI structure / style | [none / structure / style / both] | [UI/UX IDs or none] | [Wireframe/UI Design gates or none] |
| Data / integrations | [unchanged / changed] | [IDs or none] | [Artifacts and gates or none] |
| Architecture / stack | [unchanged / changed] | [ARCH IDs/layers or none] | [Stack checkpoint and artifacts or none] |
| Data trust / AI | [unchanged / changed] | [Gate/IDs or none] | [Artifacts and gates or none] |
| Monetization / partner | [unchanged / changed] | [Gate/IDs or none] | [Artifacts and gates or none] |
| Release / operations | [unchanged / changed] | [Targets or none] | [Artifacts and gates or none] |

Changed rows use area-specific refreshes. Product behavior reopens `PRD.md` and Product Definition Approval. UI `structure`/`both` reopens `wireframes.html`, `ui-design.md`, Copy Freeze, Wireframe Approval, and Visual Approval; `style` reopens `ui-design.md` and Visual Approval. Data/integration changes reopen `PRD.md`, `architecture.md`, and Product Definition Approval. Architecture/stack changes reopen `architecture.md`, `stack-decisions.md`, Stack Decision Checkpoint, and Product Definition Approval. Trust/AI and monetization/partner changes reopen all three core package files plus both approval gates. Release/operations changes reopen `architecture.md`, `DEPLOYMENT.md`, Product Definition Approval, and the deployment checker. Naming unrelated artifacts or generic approval words does not satisfy the row.

## Problem Statement
[Current pain, trigger, and why now.]

## Goals
- [Goal]

## Non-Goals
- [Explicitly out of scope]

## Users and Personas
| Persona | Need | Key Workflow | Success Signal |
| --- | --- | --- | --- |

## User Journeys
### Journey 1: [Name]
1. [Step]
2. [Step]

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

The two HTML comments, each `UI-*` heading, and the backticked `` `route` ``, `` `releaseSurface` ``, `` `surfaceClass` ``, `` `captureMode` ``, `` `states` ``, `` `responsive` ``, and `` `copy` `` field names are invariant machine anchors for new or revised packages. A UI-bearing PRD contains exactly one non-empty matched boundary pair around the complete surface contract; every `UI-*` heading in the document is inside it. Keep the anchors unchanged when the surrounding PRD is written in another language. Each entry has exactly one literal route; use a separate `UI-*` entry when another addressable route needs the same presentation. Legacy single-platform packages without the three platform-binding anchors remain readable, but an approved new or revised package records them on every surface.

### UI-001 — [Surface name]

- `route`: [One literal route value, or `n/a — <reason>`]
- `releaseSurface`: [Exact stable `Surface` value from `architecture.md` Release Targets, such as `web-app` or `ios-app`]
- `surfaceClass`: [Exact Release Target surface class, such as `hosted_web`, `browser_extension`, `ios`, `android`, `macos`, or `windows`]
- `captureMode`: [hosted-browser / browser-extension / native / desktop, derived from `surfaceClass`]
- Main purpose: [One primary user goal]
- Content responsibilities: [Required information and controls; exact copy or bounded display contract for each, without choosing layout or region order]
- Actions and transitions: [Primary, secondary, destructive, navigation, success, and failure paths]
- `states`: [Comma-separated state IDs. Record an inapplicable state as `<state>:n/a — <reason>` so the PLAN join can preserve the decision]
- `responsive`: [This surface's exact responsive set: at least three ascending `viewports: 390, 768, 1200` for hosted web/extensions, or at least two `sizeClasses: compact, regular` for native/desktop. Hybrid surfaces may use different sets]
- `copy`: [draft / approved / revision_requested / blocked] — [Static strings are implementation-bound after Copy Freeze; dynamic values follow their approved source/order/format/count/length/fallback contracts]
- Responsive obligations: [Content/actions that never drop, required interaction modes, long-content behavior, and overlay focus/dismissal requirements; layout order, grid, spans, and reflow remain UI-design decisions]
- Accessibility: [Focus, labels, announcements, heading order, and alt text as applicable]
- SEO metadata: [Per-route `<title>` and meta description; canonical URL or `n/a — <reason>`; Open Graph/social, robots, and structured-data decisions as applicable or `n/a — <reason>`]
- Trace IDs: [PRD-*, UX-*, ARCH-*, TEST-*]

<!-- ui-surface-contract:end -->

Every route maps to exactly one `UI-*` entry. Every required content responsibility states what it displays, where the content comes from, what the user should understand or do, and any source, order, format, count, length, or fallback constraint. The `` `copy` `` status records the PRD's copy responsibility: `draft` means ui-design-builder may propose and approve exact wording during Copy Freeze; `approved` means that responsibility and its display contract are already product-approved. `revision_requested` and `blocked` stop UI work. A schema-4 wireframe approval may advance a PRD `draft` responsibility to approved exact wireframe copy without rewriting the PRD status to the wireframe status; `ui-design-builder` owns that final Copy Freeze approval and returns any changed responsibility or display contract for renewed Product Definition Approval. Do not invent layout regions in Product Definition.

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

## AI and Automation
AI and Automation Gate: [required / not_required / blocked] — [reason], decided by [human owner]

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

Use `monetization-and-partner-channel-guide.md` to select providers only after these decisions. If either gate is `required`, add every customer, partner, and admin surface to the UI Surface Contract and add observable success, failure, cancellation, refund, attribution, commission, payout, provisioning, and termination obligations. The later `ui-design-builder` run projects those approved surfaces into wireframes.

## Metrics
| Metric | Definition | Baseline | Target / guardrail | Measurement window | Source / method | Owner |
| --- | --- | --- | --- | --- | --- | --- |

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

This section is present for every product, including headless APIs and automations. It separates content decisions from the later filesystem publication authorization.

### Research Gate

Research Gate: [go / clarify / stop / skipped] — [assessment date and findings path, or skip reason], decided by [human owner]
[For `clarify`, the questions asked and their resolutions, and the final gate value after re-assessment. For a skipped assessment, record whether the user declined it, no web tool was available, confidential context prevented a safe query, or the package is a trivial stub. Enhancement packages cite the prior package's gate unchanged.]

<!-- product-definition-approval:start -->
### Product Definition Approval
- Package mode: [new / enhancement]
- Package revision: [Stable revision label for this candidate]
- Decision: [approved / revision_requested / blocked]
- Decision owner: [Human product owner]
- Decided on: [YYYY-MM-DD]
- Approved artifacts: [PRD.md, architecture.md, stack-decisions.md]
- Market research reconciliation: [completed / skipped — reason / blocked — reason]
- Stack Decision Checkpoint: [approved / revision_requested / blocked]
- Accepted assumptions and non-blocking questions: [None / exact rows accepted for this revision]
- Blocking items: [None / exact unresolved decisions]
<!-- product-definition-approval:end -->

Keep the required level-two PRD headings, Product Definition marker pair and fields, Data and Trust/AI gate lines, Metrics/Assumptions/Open Questions headers, and Monetization/Partner decision header plus its two gate row labels in English when surrounding prose is translated; the core-package checker treats them as machine anchors.

The owner receives one concise package review: product scope and non-goals; Must requirements and acceptance criteria; data/trust, AI, monetization, and partner gates; metrics and required tests; complete frontend and backend architecture; release targets; the approved stack bundle; risks; and every assumption/open question. `approved` requires an approved Stack Decision Checkpoint, no unresolved question marked `Blocks approval: Yes`, no blocked trust/AI/commercial gate, and no unresolved scope-changing research finding. A substantive change to those approved contents creates a new package revision and reopens this gate. Later UI evidence lives in `docs/design/ui-design.md`; it does not reopen Product Definition unless it exposes or requests a change to the approved product or stack.

### Downstream UI Design

For a UI-bearing product, Product Definition ends after the approved core package is published. A later explicit `ui-design-builder` run consumes that exact revision and owns `docs/design/ui-design.md`, `docs/design/wireframes.html`, retained HiFi references, Copy Freeze, UI grading, visual approval, and the Design System Need Gate. Those artifacts never become approved merely because this PRD exists. PRD `draft` or `approved` copy responsibility tells whether UI work may proceed; it does not by itself approve final on-screen copy.

If UI design exposes a missing route, action, state, responsive obligation, content responsibility, architecture decision, or stack constraint, return the gap to this skill, revise the affected core artifact, and obtain Product Definition Approval on a new revision before UI work resumes.

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

## Unresolved
| Question | What was searched | What would settle it |
| --- | --- | --- |

## Sources
| Source ID | Publisher | Title | URL | Retrieved | Type |
| --- | --- | --- | --- | --- | --- |
| S-01 | [Publisher] | [Title] | [URL] | [YYYY-MM-DD] | [primary / secondary] |
```

`Lands in` names the artifact and section a finding affects, so the parent can apply it without re-reading the whole package. A finding that would widen product scope is recorded as a recommendation and raised with the user; the research role never decides scope.

## `research-assessment.md`

Produced by the pre-draft research-first assessment in `research-first-guide.md`. Omit the whole file when that pass was skipped; `PRD.md`'s `### Research Gate` then records which skip reason applied instead of citing the artifact.

Every factual row follows `market-research-guide.md`'s source rules: a source ID, or `UNVALIDATED` with what was searched. The post-draft `market-research.md` reconciles against this file rather than researching the same ground twice.

Use this structure, keeping only the sections that apply to this product:

```markdown
# Research Assessment: [Product Name]

## Scope of This Assessment
[What was assessed and what was deliberately left out.]

Researched on: [YYYY-MM-DD]

## Segment And Jobs Evidence
| Finding | Evidence | Confidence | Sources |
| --- | --- | --- | --- |

## Existing Alternatives
| Alternative | What it is | Who uses it | Where it falls short | Confidence | Sources |
| --- | --- | --- | --- | --- | --- |

## Integration And Adoption Baseline
[Prose or table: table-stakes integrations, adoption signals, switching costs.]

## Market Risks
| Risk | Why it applies here | Confidence | Sources |
| --- | --- | --- | --- |

## Findings
| RA ID | Finding | Confidence | Sources |
| --- | --- | --- | --- |

## Unresolved
| Question | What was searched | What would settle it |
| --- | --- | --- |

## Sources
| Source ID | Publisher | Title | URL | Retrieved | Type |
| --- | --- | --- | --- | --- | --- |
```

The gate itself is recorded in `PRD.md`'s `### Research Gate`; this file holds the evidence behind it. A `stop` gate leaves this file in the staging directory with no drafted package.

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
- pass `python skills/product-activation/scripts/check_activation.py --activation <staged ACTIVATION.md> --prd <staged PRD.md> --architecture <staged architecture.md> --deployment <staged DEPLOYMENT.md>` before publication; the architecture and deployment inputs are the only release-target authority and must be staged together.

Publish a new seed flat at `docs/ACTIVATION.md` in the same approved move as the product package. Once the path exists, `product-activation` owns it. Product Definition reads it for context but never stages, overwrites, archives, resets, or treats its operational status as product approval.

## `outcome-review.md`

Produced only when the owner asks for an outcome review after a deployment, following the workflow's post-publish step. It is a post-deployment record, not part of the drafting package, and its absence from a package is normal.

Use `assets/templates/OUTCOME_REVIEW.template.md` and validate it with `scripts/check_outcome_review.py`. A single-target review keeps its original fields. A product with multiple production targets records an ordered `Production release targets: target-set: <id>, <id>, ...` field, one immutable row per target in `## Target Reviews`, and target-bound signal rows in `## Target Measurements`; the top-level `Verdict` is the deterministic aggregate (`incident` if any target is incident, otherwise `enhancement` if any target is enhancement, otherwise `no_change`). Separate target rows prevent one target's SHA, artifact, deployment, or measurement source from overwriting another target.

```markdown
# Outcome Review: [Product Name]

## Record
Schema: outcome-review/1
Product, human outcome owner, production release target, full Release SHA, exact artifact/build identity, exact Deployment identity and checked time, Deployment PASS, `docs/ACTIVATION.md`, lowercase SHA-256 of the current Activation bytes, real Reviewed date, and closed verdict. A multi-target Record also adds `Production release targets: target-set: ...` and keeps the legacy primary fields bound to the first ordered target.

For a multi-target review, add these ordered target and per-signal tables:

```markdown
## Target Reviews
| Release target | Release SHA | Artifact / build identity | Deployment identity | Deployment checked | Deployment status | Activation sources | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [production target] | [full SHA] | [artifact] | [release;channel;artifact] | [RFC3339] | PASS | [MS IDs] | [enum] |

## Target Measurements
| Signal | Release target | Baseline | Target | Window start | Window end | Actual | Source ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [PRD metric or required TEST] | [target] | [baseline] | [target] | [date] | [date] | [actual] | [MS-*] |
```

The target set for each signal is the exact `Release targets` value in Activation Outcome Coverage for that signal. Do not synthesize a full signal-by-target cross-product when Activation scopes a signal to only some production targets.

## Activation Sources
Every matching verified `MS-*` source and only those sources. Each row repeats the exact target@SHA#artifact binding, human owner, verification time, and non-secret evidence.

## Measurements
| Signal | Baseline | Target | Window start | Window end | Actual | Source ID |
| --- | --- | --- | --- | --- | --- | --- |
| [PRD `## Metrics` metric or `TEST-*` expected signal] | [pre-deploy value or "none recorded"] | [the recorded target] | [YYYY-MM-DD] | [YYYY-MM-DD] | [measured value] | [MS-*] |

## Feedback
| Fact | Source ID | Observed |
| --- | --- | --- |
| [Post-deployment fact] | [MS-*] | [bounded non-secret observation] |

For a multi-target review, use `Fact | Release target | Source ID | Observed` instead. Every feedback fact must name the target and a verified source bound to that target; it may not implicitly reuse the primary target's source set.

## Incident Response
| Incident | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence |
| --- | --- | --- | --- | --- | --- |
| [none, or the incident] | [containment or n/a] | [human or n/a] | [PRD Risks routing or n/a] | [PRD Open Questions routing or n/a] | [MS-* or n/a] |

## Verdict
Verdict: [no_change / enhancement / incident] — [one-line reason]

## Open Follow-ups
| Follow-up | Route |
| --- | --- |
| [Item or none] | [enhancement request / open question / risk / none] |
```

Rules:

- Run `python skills/product-definition-builder/scripts/check_outcome_review.py --outcome docs/product/outcome-review.md --prd docs/product/PRD.md --architecture docs/product/architecture.md --deployment docs/DEPLOYMENT.md --activation docs/ACTIVATION.md`.
- Record actual against target for every `PRD.md` `## Metrics` metric and every required `TEST-*` expected signal; baseline, target/expected signal, and (when present) numeric measurement-window duration must exactly join the PRD row. An empty or duplicate Measurements table means the review is not done.
- The measurement window is real elapsed time after deployment, uses real calendar dates, closes on or before the review date, and cannot extend into the future. A review written at deploy time with "pending" actuals is a stub, not a verdict.
- A single-target review cannot mix targets or releases and is production-only. A multi-target review keeps the ordered target set explicit, joins every target row to its own current Deployment PASS identity and verified `MS-*` sources, and repeats every PRD metric and required `TEST-*` signal per target in `Target Measurements`. No target's SHA, artifact, source, or actual may be reused implicitly for another target. All reviewed targets must be production architecture targets, and the aggregate verdict follows the closed deterministic severity order.
- An incident requires typed containment, a human owner, and explicit concrete routing into the next Product Definition `PRD Risks` and `PRD Open Questions`.
- The verdict vocabulary is closed: `no_change`, `enhancement`, or `incident`. Every later run reads this file in full during enhancement detection.

Legacy outcome prose may be read as context, but it cannot authorize a verdict under this contract. A legacy `Activation source status:` line or old `| Metric | Baseline | Target | Window | Actual | Source |` table does not satisfy the current release binding; recreate the record in the schema above and let the checker apply Activation's `--require-verified-sources` gate before any verdict is routed.

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
[Authentication, authorization, secrets, audit, privacy, abuse cases.]

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

For every deployable hosted web, API, or backend target, include this environment contract (Cloudflare Worker naming shown as the worked example; substitute the resolved platform's equivalent deployment unit). Do not use this two-row hosted-environment table for native mobile or desktop store/signed-installer distribution:

| Target | Exact Release Source | Deployment Unit | Data / Bindings / Secrets | Auth Mode | Payment Mode | Migration Order | Deployed Verification | Rollback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Development | [Exact candidate run branch/ref and verified SHA] | [`<product-slug>-<surface-suffix>-dev`] | [Isolated non-production resources] | [Development] | [Sandbox or not applicable] | [Classification, command, and ordering or not applicable] | [Internal suite, URL, deployed SHA, smoke, evidence] | [Prior development version] |
| Production | [Exact remote `main` head after the same verified candidate SHA is fast-forwarded and read back] | [`<product-slug>-<surface-suffix>`; never add `-prod`] | [Production resources] | [Production] | [Live or not applicable] | [Classification, command, and ordering or not applicable] | [URL, deployed SHA, production smoke, evidence] | [Prior production version] |

State that both hosted targets use one repository and one codebase. Do not reuse production data, sessions, secrets, or live payment mutations in development. Write each Migration Order cell so the human or CI release process can run it in order.

## Release Targets
Use this provider-neutral section for every deployable web, API, mobile, desktop, or browser-extension surface, including hosted targets already summarized in the environment table above. First record the complete expected deployable-surface inventory using stable surface IDs. Then record one block per exact destination and give it a stable target ID, explicit lowercase kebab-case surface suffix, and lowercase kebab-case release name. The production release name is the canonical `<product-slug>-<surface-suffix>` name and never ends in `-prod`; development uses that exact name plus `-dev`; one release name cannot belong to multiple surface IDs. Use the surface suffix guidance in `architecture-playbook.md` for web, API, extension, native, and independently released supporting units. Every expected surface needs at least one `development` target and one `production` target; a package that omits an expected surface is incomplete. Keep the stable `surface` identity separate from `provider`, because one surface may use different providers by stage. Keep surface and target IDs stable across revisions; retire rather than reuse an ID when its meaning changes.

This section is authoritative product documentation for the human or CI release process. The Product Definition checker and downstream Deployment, Activation, Outcome, and SEO joins consume its stable target identities.

Expected deployable surfaces: [stable surface IDs, for example `web-app`, `public-api`, `ios-app`]

### Release Target: [stable-target-id]
- Surface: [Stable expected surface ID]
- Surface class: [hosted_web / hosted_api / browser_extension / ios / android / macos / windows / worker / job / webhook / realtime / cli / agent / other_nonpublic]
- Public discoverability: [yes / no]
- Surface suffix: [Lowercase kebab-case suffix for this independently released unit]
- Release name: [Production `<product-slug>-<surface-suffix>` or that exact name plus `-dev` for development]
- Provider: [Stage-specific hosting, store, or distribution provider]
- Stage: [development / production]
- Source policy: [`stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha` for development, or `stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha` for production]
- Artifact kind: [Static bundle, container, serverless bundle, API service, IPA, AAB, signed DMG/PKG, MSIX, signed installer, or another exact artifact]
- Signing requirement: [Not required, or exact certificate/signing/notarization requirement and owner]
- Exact channel / track: [Named environment, URL, TestFlight group, Play track, App Store, update feed, direct-download channel, or another exact destination]
- Submission / promotion / review / manual approval path: [Ordered gates and decision owner]
- Availability signal: [Observable proof that the intended audience can reach, install, or download this exact release, plus the smoke/acceptance signal]
- Rollout: [Immediate, percentage/phased/staged rollout, audience ring, or another controlled sequence]
- Rollback / forward-fix: [Prior deployed version for instant rollback, or rollout halt/removal plus corrected signed artifact through the same review/distribution path]

A successful build, upload, submission, deployment command, notarization, or store approval is not availability by itself. Hosted availability requires the deployed route or API to answer the named smoke checks. Store and signed-installer availability requires the approved artifact to be actually installable or downloadable through the named channel and to pass its release smoke check. Native recovery may require halting a phased or staged rollout and shipping a signed forward-fix; do not promise web-style rollback when the channel cannot perform it.

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
- Approved areas: [Frontend / Mobile or desktop / Backend or data / AI or automation / Monetization or partner channel / none]
- Delegated choices: [None / exact decision classes explicitly delegated and source]
- Open areas: [None / exact unresolved areas]
<!-- stack-decision-checkpoint:end -->

Keep the `Stack Decisions` title, this marker pair and fields, the Coherent Options header, every `Recorded or Approved Stack` heading, and layer-table header in English in a translated package; they are machine anchors.

Before this checkpoint, present two or three coherent bundles for every applicable unresolved area. Each bundle names all coupled layers, fit, tradeoffs, operating and maintenance ownership, cost/license/data constraints, serious alternatives, and revisit triggers. The owner may approve the recommendation, modify layers, or rely on an explicit prior delegation. `Recommended` and `Provisional` rows keep this checkpoint blocked.

### Coherent Options Presented
Use this shared table for every unresolved area before the checkpoint. Preserve the complete option the owner accepted as well as rejected serious alternatives; do not record only the winning framework name.

| Option ID | Area | Complete bundle | Best fit | Tradeoffs / ownership | Disposition |
| --- | --- | --- | --- | --- | --- |
| OPT-FE-01 | [Frontend / Backend or data / Mobile or desktop / AI or automation / Commercial] | [Every coupled layer in this option] | [Why and when it fits] | [Cost, lock-in, data, maintenance, operations] | [recommended / approved / rejected] |

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
| Tool execution and approvals | [Runtime, allowlist, human gates] | [Required / Selected / Approved / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
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
| [Frontend / Mobile or desktop / Backend or data / AI or automation / Monetization or partner channel] | [Alternative or coherent bundle] | [Context] | [Reason] | [Trigger] |

### Unresolved Decision Protocol
Use only when a layer cannot yet be decided. A bare `TBD` does not pass validation.

| Area | Open Decision | Missing Evidence | Owner | Decision Date | Time-boxed Spike | Pass / Fail Criteria |
| --- | --- | --- | --- | --- | --- | --- |
```

## Optional UI Design Handoff

Stop after Product Definition Approval. When the owner later asks to design the UI, invoke `../ui-design-builder/SKILL.md` with the approved PRD, architecture, and stack paths. It asks UI, style, motion, and media questions; creates and scores the wireframe; integrates the approved style with `frontend-design`; runs Impeccable HiFi review plus H1–H9 grading; obtains visual approval; and invokes `design-system-compiler` only when its later gate is `required`.

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
- No table in the package exceeds seven columns except the environment contract in `architecture.md`, whose columns are all release-critical.

### Completeness

- `PRD.md`, `architecture.md`, and `stack-decisions.md` are present in the run-specific staging directory. Their Product Definition Approval and Stack Decision Checkpoint are both `approved`, and `check_product_package.py --repo-root <repository-root> --require-filled --require-approved` passes before publication. The staged operational documents follow their existing applicability rules. UI-bearing packages record a pending `ui-design-builder` handoff; headless packages record `not_required` without skipping Product Definition Approval.
- `## Non-Functional Requirements` is always present immediately after `## Functional Requirements`. Every applicable quality attribute has a measurable `PRD-*` requirement with a measure and target; non-applicable categories are explicitly `N/A` with a reason. Vague adjectives alone do not pass. Units, tested population or traffic shape, measurement window, and percentile are present where applicable.
- `## Test Obligations` is always present after `## Open Questions` and before the trailing product decision records. Its rows use stable `TEST-*` IDs and include obligation, test type, required status, upstream trace IDs, and an expected signal.
- Every `Must` functional requirement and every applicable non-functional requirement maps to at least one `TEST-*` row marked `Required: Yes`. No required obligation is left as anonymous prose.
- `## Metrics` records baseline, target or guardrail, measurement window, source/method, and owner for every success measure; metric names are unique. Guardrails are separate metric rows when they need separate ownership or evidence.
- `## Assumptions` and `## Open Questions` use their structured owner/decision tables. No unresolved Open Questions row marked `Blocks approval: Yes` remains when Product Definition Approval is approved; the approval record explicitly accepts any open non-blocking row or assumption.
- Every PRD records a Data and Trust Gate and an AI and Automation Gate as `required`, `not_required`, or `blocked` with a reason and human owner. An approved package has neither gate blocked. Required gates are carried into architecture, stack decisions where technology is involved, UI surfaces, and `TEST-*` obligations.
- Every `PRD.md` records both the Monetization Infrastructure Gate and Partner Channel Gate with `required`, `not_required`, or `blocked` plus a reason. Commercial products record the monetization model, pricing/offer rules, purchase surfaces, entitlement source, and merchant-of-record/tax owner. Products with outside distribution record affiliate, referral, reseller, or hybrid motion plus attribution, commission/discount, reversal, payout, customer ownership, provisioning, support, termination, and fraud rules as applicable.
- Product Definition Approval requires both commercial gate rows to be `selected` or `approved`; `recommended`, `provisional`, `assumed`, or `blocked` remains a draft decision.
- A pricing strategy never silently selects RevenueCat. `stack-decisions.md` compares current relevant providers through `monetization-and-partner-channel-guide.md`, cites official evidence and retrieval date, separates store/billing, entitlement, paywall/checkout, merchant-of-record/tax, and partner-channel layers, and records rejected alternatives and revisit triggers. Affiliate, referral, and reseller remain distinct motions.
- When either gate is required, `architecture.md` defines the applicable revenue and partner entities, stable identity joins, verified idempotent event/webhook flows, retry/replay/reconciliation, refund/chargeback effects, entitlement grant/revoke/restore, commission reversal, and reseller provisioning/deprovisioning. Required UI surfaces and `TEST-*` obligations cover the chosen lifecycle, including failure and termination states.
- For a UI-bearing product, `PRD.md` records the human owner for later UI design plus complete surfaces, routes, actions, states, responsive obligations, copy responsibilities, accessibility, confirmation, and recovery behavior. Every new or revised surface binds its exact architecture `releaseSurface`, matching `surfaceClass`, derived `captureMode`, and its own responsive set; hybrid platforms are never flattened into one global set. It does not contain a guessed layout, style, motion/media treatment, wireframe approval, or design token.
- An enhancement package records the complete Enhancement Impact Record across product behavior, UI structure/style, data/integrations, architecture/stack, data trust/AI, monetization/partner, and release/operations. Each changed row names affected IDs/decisions, refreshed artifacts, and rerun gates. UI keeps the `none` / `structure` / `style` / `both` classification and its existing wireframe/design consequences.
- UI preference is not presented as user validation. `ui-design-builder` later records those choices and keeps conflicts with user evidence or accessibility requirements explicit.
- For every deployable web, API, mobile, desktop, or browser-extension surface, `architecture.md` has a provider-neutral `## Release Targets` section with an explicit expected deployable-surface inventory and at least one development-stage and one production-stage target for every expected surface. A missing expected surface fails validation. Every target has a stable ID, an explicit lowercase kebab-case surface suffix and release name, separate stable surface and stage-specific provider fields, a source policy naming the exact branch or ref, artifact kind, signing requirement, exact channel/track, submission/promotion/review or manual-approval path, actual availability signal, rollout, and rollback or forward-fix path. Production uses the canonical `<product-slug>-<surface-suffix>` name without `-prod`; development uses that exact name plus `-dev`; release names are globally unique across surface IDs. Different providers by stage are valid for the same surface.
- Upload, submission, deployment-command success, notarization, or store approval alone is not accepted as availability. Hosted targets prove the route/API is serving and passes smoke checks; store or signed-installer targets prove the intended audience can actually install/download the artifact and that its release smoke check passes.
- For a deployable hosted web, API, or backend target, `architecture.md` records the platform resolved during interview (via `AskUserQuestion` unless the user or repository already named one — never a silent default) and defines one codebase with separate development and production environments (named Workers when the platform is Cloudflare).
- The hosted environment contract names the exact candidate run branch/ref as the internally tested development source and remote `main` as production. Initial delivery and enhancements both start from observed remote `main`; the exact candidate passes internal and applicable isolated development-environment verification before separately authorized fast-forward promotion to `main`. It also names distinct deployment units, isolated resources/secrets/data/auth/payment modes, migration order, evidence, and recovery. Development never uses production customer data, sessions, or live payment mutations. Native targets remain provider-neutral.
- Native release recovery does not claim instant rollback when the channel cannot perform it. It records how to halt or reduce a staged/phased rollout and ship a corrected signed forward-fix through the same submission, review, or distribution path.
- For a browser product, `stack-decisions.md` records the owner-approved coherent frontend stack, with language, package manager, component foundation, and styling as separate layers alongside runtime, rendering, framework, UI library, build, routing/data, and tests.
- Every frontend layer row records Selection, Status, Authority / evidence, Why It Fits, and Constraint / follow-up. Status is accurate per layer, authority cites its source rather than repeating a status label, and one section may mix statuses.
- For a product with a backend, persistent data, or auth requirement, `stack-decisions.md` records the owner-approved coherent backend stack, separating topology, runtime, database category/engine, auth strategy/provider, API, jobs, and storage. No runtime, engine, or vendor is a silent default.
- Every backend/data layer row records Selection, Status, Authority / evidence, Why It Fits, and Constraint / follow-up. Status is accurate per layer, authority cites its source rather than repeating a status label, and the database category and auth strategy trace back to the interview's `AskUserQuestion` answers rather than a silent default.
- For a mobile or desktop target, operating-system destinations are resolved before native/cross-platform strategy and framework/toolchain. The approved stack separately records navigation/state, persistence, secure storage, sync, push/native modules, backend integration, distribution, and tests.
- Every mobile/desktop layer row records Selection, Status, Authority / evidence, Why It Fits, and Constraint / follow-up. Status is accurate per layer, authority cites its source rather than repeating a status label, and one section may mix statuses.
- Every rejected option for any stack decision appears once in `stack-decisions.md`'s shared `Alternatives Considered` table with its area named, rather than repeated per decision section.
- Any unresolved frontend, backend, database, auth, mobile/desktop, AI/automation, or commercial decision appears in the shared `Unresolved Decision Protocol` table with an owner, deadline, time-boxed spike, and pass/fail criteria; a bare `TBD` does not pass.
- An approved Stack Decision Checkpoint contains only `Required`, `Selected`, or `Approved` executable rows. `Recommended` and `Provisional` may remain in a staged candidate but block Product Definition Approval and Harness. Explicit delegation is recorded in the checkpoint and turns the resulting accepted choice into `Approved`; it never makes `Recommended` executable.
- If produced, `implementation-plan.md` includes milestones, dependency order, non-canonical Harness handoff signals, test strategy, release plan, rollback plan, and unresolved decisions. Its test strategy reuses the canonical `TEST-*` IDs from `PRD.md`; it does not replace them with anonymous checks or newly numbered duplicates. Its release plan reuses the stable release target IDs from `architecture.md`.
- The market-research gap pass completes or records its skip/block reason before Stack Decision and Product Definition approval. Its queries pass the Research Disclosure Check; confidential inputs never leave the product context by implication.
- For a new package, `PRD.md` records a `### Research Gate` with `go`, `clarify`, `stop`, or the permitted skip reason, including confidential-context constraints. An enhancement cites the prior gate unchanged and researches only the delta.
- A silently missing Research Gate, Stack Decision Checkpoint, or Product Definition Approval does not validate.
- When `research-assessment.md` is present, every factual row cites a source ID resolving to a `## Sources` row with publisher, URL, and retrieval date, or is marked `UNVALIDATED` with what was searched. No competitor, price, funding figure, user count, or market size appears without a source.
- When `market-research.md` is present, every factual row cites a source ID resolving to a `## Sources` row with publisher, URL, and retrieval date. Any claim without one is marked `UNVALIDATED` with what was searched. No competitor, price, funding figure, user count, or market size appears without a source.
- When the pass was skipped or blocked, `PRD.md`'s `## Assumptions` records that the market context is unvalidated.
- Findings that changed the package cite their `MR-*` IDs in the sections they changed, and `PRD.md` states conclusions rather than restating the competitor table, sources, or retrieval dates. Findings that would widen product scope are recorded as open questions or recommendations, not applied silently.
- When the read-only agent work graph was used, every required role has an explicit result, failed agents are retained as blocked lanes, and trace/consistency verifier findings are resolved or recorded before finalization. Agent output is treated as a candidate; the parent still owns staging and publication.
- Run `python skills/product-definition-builder/scripts/check_product_package.py --prd <staged PRD.md> --architecture <staged architecture.md> --stack-decisions <staged stack-decisions.md> --repo-root <repository-root> --require-filled --require-approved` before publication. It validates substantive core sections, complete UI surfaces, Must/NFR-to-TEST coverage, gate-area traces, release-target identity, metrics, decision tables, both approval markers, executable stack statuses, live `Selected` evidence, and blocked trust/AI/commercial gates.

### Publication

- No current-package artifact will be published outside `docs/product/` unless the user explicitly requested another location.
- The superseded-document inventory excludes `docs/product/archived/`, unrelated documents, and ambiguous candidates.
- In enhancement mode, unaffected sections, `PRD-*`, `ARCH-*`, `UI-*`, `UX-*`, `TEST-*`, `MR-*`, `RA-*` IDs, and stable release target IDs from the prior package were carried forward unchanged rather than regenerated, and the diff is scoped to what the new discovery actually added, changed, or removed; new TEST IDs cover only obligations that were previously uncovered, and new release target IDs cover only destinations that were previously uncovered.
- Validation does not trigger publication by itself. Exact overwrite and archive moves are already authorized, or the staged package remains unchanged while approval is requested.

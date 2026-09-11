# Output Contract

Produce a core multi-file Markdown PRD package. Stage and publish it according to `artifact-lifecycle.md`. The final package belongs under `docs/product/`. Use exactly these core artifact names unless the user requests different names:

- `docs/product/PRD.md`
- `docs/product/architecture.md`
- `docs/product/stack-decisions.md`
- `docs/product/wireframes.html` for a UI-bearing product

For a UI-bearing product, include the complete UI surface contract in `PRD.md`, project it into one interactive `wireframes.html` containing every page, obtain human approval, and stop. Run `ui-design-pass.md`, Taste, UI preview generation, `design-system-compiler`, or Harness only after a separate explicit request to continue into visual design or implementation. A product with no UI surface records the skip in `PRD.md` and publishes no placeholder wireframe or design artifacts.

This contract covers the product spec and approved structural screen structure and behavior. It does not require a visual direction, preview, token set, closed component variants, or design-system rules. Those belong to a later optional visual-design phase.

It also publishes `docs/product/market-research.md` when the post-draft market-research gap pass ran and returned findings. That pass is on by default for a non-trivial package; when the user declined it, no web tool was available, or the role returned blocked, the package publishes without the file and records the unvalidated market context in `PRD.md`'s `## Assumptions`. See `market-research-guide.md`.

For a product with a web, iOS, or browser-extension release target, it also creates a one-time operational seed at `docs/ACTIVATION.md` from the sibling `product-activation` template when that path is absent. The seed maps release targets, every PRD metric, and every required `TEST-*` signal, but it contains no external authorization, account guess, secret value, or claim that a source is verified. An existing Activation record is owned by `product-activation` and is preserved byte-for-byte during product enhancement.

It specifies what each UI surface must show and do and shows its structure in a self-contained HTML reviewer. Do not turn `wireframes.html` into a design-reference mockup or add token schemas, component catalogs, or styling rules here.

`PRD.md` is the canonical source for product scope, routes, screen purpose, visible-region responsibility, content, actions, states, responsive behavior, flows, trace IDs, and the Builder UX Direction Decision. `wireframes.html` is the only structural review projection and never overrides `PRD.md`. If a later visual-design phase is explicitly requested, its approved handoff and optional design-system pair add visual implementation authority without taking ownership of product structure or behavior.

Produce `docs/product/implementation-plan.md` only when the user explicitly asks for delivery sequencing or implementation planning.

Default all artifact content to English unless the user explicitly asks for another language.

## How To Read This Package

Every artifact has one primary reader and one job. Write for that reader.

| Artifact | Primary reader | Answers |
| --- | --- | --- |
| `PRD.md` | Anyone deciding whether to build this | What is it, for whom, and what counts as done |
| `wireframes.html` | The human owner reviewing the full UI map | How all pages, labeled sections, viewport arrangements, and states fit together in one interactive file |
| `architecture.md` | An engineer about to implement | How the system is shaped and where the risk is |
| `stack-decisions.md` | An engineer choosing or reviewing technology | Which stack, and why that one |
| `market-research.md` | Anyone questioning a product claim in `PRD.md` | What already exists out there, and what the evidence is |
| `research-assessment.md` | Anyone deciding whether this product should have been drafted | What the pre-draft evidence supported, and what the gate decided |
| `outcome-review.md` | The owner deciding what happens after a release | What actually happened post-deployment, measured against the targets, and the verdict |
| `docs/DEPLOYMENT.md` | The human operator preparing and checking a release | Which secret and variable names go where, which external consoles need work, and what actually deployed |
| `docs/ACTIVATION.md` | The owner or operator activating a delivered release | Which external actions and measurement sources are pending, configured, verified, blocked, or stale |
| `docs/DOCUMENTS.md` | Anyone locating flow artifacts | Which documents exist, who owns them, and their current status |
| `design-system.md` + `design-system.json` (only after an explicitly requested visual-design phase whose Design System Need Gate is `required`) | A designer or frontend engineer styling reusable surfaces | The binding token, primitive, component, and state contract; read alongside `PRD.md` and `wireframes.html` |

Core reading order is `PRD.md` → `wireframes.html` → `architecture.md` → `stack-decisions.md`. Read the optional visual-design handoff and design-system pair only when that later phase was requested and completed. Read `docs/DEPLOYMENT.md` for release configuration and `docs/ACTIVATION.md` for post-delivery operational state; neither overrides the product contract. `market-research.md` is evidence, not narrative: read it when a `PRD.md` statement cites an `MR-*` ID and you want the source behind it. `research-assessment.md` is the same kind of evidence for the pre-draft decision: read it when a statement cites an `RA-*` ID.

Two rules keep the package readable:

- **Meaning before bookkeeping.** Each file opens with what a human needs to understand the product and ends with the ID matrices and decision records that machines, auditors, and downstream skills need. Never open a file with a trace table.
- **One notation per block.** Prose, ASCII, and ID tables do not interleave inside a section. A table wider than seven columns is a sign the content wants to be a list instead.

Length budget. These are targets, not caps — say less when the product is simple, and go over only when the product is genuinely more complex, not when a section drifted:

- `PRD.md`: about 200 lines. `## At a Glance` fits on one screen.
- `wireframes.html`: one self-contained file; keep product data in the embedded data block and reuse the supplied reviewer shell rather than duplicating page-specific CSS or JavaScript.
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

Omit this section only when the product has no shipped UI surface. Define one entry per addressable screen or bounded UI surface. This is the canonical implementation source for structure and behavior.

The two HTML comments, each `UI-*` heading, and the backticked `` `route` ``, `` `states` ``, and `` `responsive` `` field names are invariant machine anchors. A UI-bearing PRD contains exactly one non-empty matched boundary pair around the complete surface contract; every `UI-*` heading in the document is inside it, and each entry contains exactly one of each anchor. Keep them unchanged when the surrounding PRD is written in another language. Each entry has exactly one literal route; use a separate `UI-*` entry when another addressable route needs the same presentation.

### UI-001 — [Surface name]

- `route`: [One literal route value, or `n/a — <reason>`]
- Main purpose: [One primary user goal]
- Layout pattern and density: [Task-fit pattern and reason]
- Region order and responsibilities: [Ordered visible regions; exact copy or bounded display contract for each]
- Actions and transitions: [Primary, secondary, destructive, navigation, success, and failure paths]
- `states`: [Comma-separated state IDs. Record an inapplicable state as `<state>:n/a — <reason>` so the PLAN join can preserve the decision]
- `responsive`: [Exactly one responsive set: at least three ascending `viewports: 390, 768, 1200` for web, or at least two `sizeClasses: compact, regular` for native/desktop. Every UI-* entry in one package uses the same set]
- Responsive behavior: [For every declared target: order, grid/stacking, visibility, never-drop content/actions, interaction-mode changes, long-content handling, and intended-overlay stacking/focus/dismissal behavior]
- Accessibility: [Focus, labels, announcements, heading order, and alt text as applicable]
- SEO metadata: [Per-route `<title>` and meta description; canonical URL or `n/a — <reason>`; Open Graph/social, robots, and structured-data decisions as applicable or `n/a — <reason>`]
- Trace IDs: [PRD-*, UX-*, ARCH-*, TEST-*]

<!-- ui-surface-contract:end -->

Every route maps to exactly one `UI-*` entry. Every region states what it displays, where the content comes from, what the user should understand or do, and any ordering, format, count, or length constraint. Do not use generic placeholders such as `Main content`, `Feature section`, or `Card 1`.

SEO metadata is part of the surface contract, not an implementation-time invention. Each route's entry records its own unique `<title>` and meta description, written for that page's actual content, plus the applicable extras or an explicit `n/a — <reason>`. Site-level SEO obligations — indexing strategy, sitemap and robots policy, canonical policy, default structured data — are recorded in Frontend Delivery Requirements, and a required SEO obligation traces to its own `TEST-*` row like any other requirement.

## Frontend Delivery Requirements
- [Target devices and browsers, content/interactivity profile, rendering, performance, accessibility, localization, offline, and deployment constraints; site-level SEO — indexing strategy, sitemap and robots policy, canonical policy, default structured data — while each route's own `<title>` and meta description live in its `UI-*` entry]

Omit this section only when the product has no browser frontend.

## Data and Integration Requirements
- [Data objects, external systems, freshness, retention]

## Business Rules
- [Rules, thresholds, approvals, calculations]

## Monetization and Partner Channels

Record both gates even when they are not required. Do not select RevenueCat merely because the product has pricing, and do not treat affiliate, referral, and reseller as synonyms.

| Decision | Selection | Product rationale / evidence | Status | Trace IDs |
| --- | --- | --- | --- | --- |
| Monetization model | [none / one_time / subscription / usage_based / hybrid / undecided] | [Who pays and for what] | [selected / recommended / provisional / assumed] | [PRD-* / MR-* / RA-*] |
| Monetization Infrastructure Gate | [required / not_required / blocked] | [Purchase surfaces and infrastructure need, or explicit reason none] | [selected / recommended / provisional / assumed] | [PRD-* / ARCH-* / TEST-*] |
| Pricing and offer | [Tiers, price metric, interval/unit, trial/discount, currency/region, upgrade/downgrade/cancel/refund] | [Value and buyer fit] | [selected / recommended / provisional / assumed] | [PRD-* / TEST-*] |
| Purchase and entitlement | [Store/web/invoice surfaces; product, purchase/subscription, and entitlement source of truth] | [Cross-platform and lifecycle needs] | [selected / recommended / provisional / assumed] | [ARCH-* / TEST-*] |
| Merchant of record / tax owner | [Product company / Stripe arrangement / Paddle / Lemon Squeezy / other / n/a] | [Payment, invoice, tax, fraud, refund, chargeback, and billing-support ownership] | [selected / recommended / provisional / assumed] | [ARCH-* / TEST-*] |
| Partner Channel Gate | [required / not_required / blocked] | [Outside distribution need, or explicit reason none] | [selected / recommended / provisional / assumed] | [PRD-* / ARCH-* / TEST-*] |
| Partner motion | [none / affiliate / referral / reseller / hybrid / undecided] | [Link attribution, known-lead referral, partner-owned sale, or named combination] | [selected / recommended / provisional / assumed] | [PRD-* / TEST-*] |
| Partner economics and operations | [Commission/discount, attribution, reversal, payout, customer ownership, provisioning, support, termination] | [Channel rules] | [selected / recommended / provisional / assumed] | [PRD-* / ARCH-* / TEST-*] |

Use `monetization-and-partner-channel-guide.md` to select providers only after these decisions. If either gate is `required`, add every customer, partner, and admin surface to the UI Surface Contract and `wireframes.html`, and add observable success, failure, cancellation, refund, attribution, commission, payout, provisioning, and termination obligations as applicable.

## Metrics
| Metric | Definition | Target |
| --- | --- | --- |

## Risks
| Risk | Impact | Mitigation |
| --- | --- | --- |

## Assumptions
- [Assumption]

## Open Questions
- [Question]

## Test Obligations
| TEST ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |
| --- | --- | --- | --- | --- | --- |
| TEST-001 | [Observable behavior or quality obligation] | [Unit / integration / contract / E2E / performance / security / accessibility / operational] | [Yes / No] | PRD-001 | [Literal pass signal, measured result, or threshold] |

Every `Must` functional requirement and every applicable non-functional requirement maps to at least one row whose `Required` value is `Yes`. A row may cover more than one upstream requirement only when one test genuinely verifies all of them. Preserve each `TEST-*` ID when its obligation keeps the same meaning; retire rather than reuse an ID whose meaning changes.

---

## Builder UX Direction Decision

Decision record. Read it when you need to know why the interface is shaped the way it is; skip it on a first pass.

Decision owner: [Human product/design owner or commissioning team]

| Dimension | Direction | Product / user rationale | Status | Validation needed |
| --- | --- | --- | --- | --- |
| Experience priority | [Speed / clarity / guided completion / expert control / exploration / conversion / comprehension] | [Why this fits the product and user task] | [selected / provisional / assumed] | [None / prototype review / likely-user test / benchmark] |
| Guidance and control | [Guided / balanced / expert-flexible] | [Reason] | [selected / provisional / assumed] | [Method or none] |
| Information density | [Sparse / balanced / dense] | [Reason] | [selected / provisional / assumed] | [Method or none] |
| Interaction and layout | [Familiar / expressive; preferred primary pattern] | [Reason] | [selected / provisional / assumed] | [Method or none] |
| Motion direction | [Quiet with functional feedback / expressive where justified / AI recommendation] | [Reason and who may decide per-surface motion] | [selected / provisional / assumed] | [Normal plus reduced-motion review / owner decision] |
| Confirmation and recovery | [Confirm / undo / retry / escalation expectations] | [Reason] | [selected / provisional / assumed] | [Method or none] |

Validation depth: [lightweight direction-conformance review only / moderate (conformance plus targeted checks) / deep (formal usability or user-evidence validation)] — [selected / provisional / assumed], decided by [decision owner]
This is the single recorded home for the interview's validation-depth answer, so the design-system step and downstream skills can read it here instead of re-asking.

Builder direction is a product input, not usability proof. Record any conflict with user evidence or accessibility requirements as a hypothesis or open question.

Motion Need Gate:

| UI scope | Gate | Purpose and trigger | Decision source | Reduced-motion fallback |
| --- | --- | --- | --- | --- |
| [UI-* screen or named region] | [required / recommended / not_required / blocked] | [State feedback, progress, spatial relationship, hierarchy, brand expression, or reason none is needed] | [Owner selection / AI recommendation accepted by owner / assumed] | [Equivalent static state, immediate transition, or other non-motion signal] |

The AI may recommend a gate when the owner delegated motion direction. Generated motion, autoplay or sound, a material performance budget, an accessibility exception, or a scope-changing treatment still needs a human decision. A `blocked` row prevents visual approval.

### Research Gate

Research Gate: [go / clarify / stop] — assessed [YYYY-MM-DD], findings in [research-assessment.md path]
[For `clarify`, the questions asked and their resolutions, and the final gate value after re-assessment. For a skipped assessment, which recorded reason applied: the user declined it, no web search or fetch tool was available, or the package is a trivial stub. Enhancement packages cite the prior package's gate unchanged instead of re-running it.]

### Wireframe Approval

Artifact: [wireframes.html path]

Decision: [approved / revision_requested / blocked], decided by [human owner] on [YYYY-MM-DD]

Approved scope: [UI-* entries, routes, the exact `responsive` viewports or size classes, and states]

Responsive browser check: [Browser and date; PASS for every UI-* × responsive target × non-n/a state with no unintended overlap, clipping, occlusion, or horizontal overflow; intended overlays and their stacking/focus/dismissal rule]

UI grading: [One complete diagnostic wave; lead and any justified specialist lenses; frozen PRD path plus revision or SHA-256; current candidate HTML SHA-256; Technical Hard Gate and DOM geometry results; 0–100 visual-quality scores plus statuses and medians when applicable; wireframe overall threshold 80 or design-reference overall threshold 90; advisories; disputed dimensions; design-reference H2/H4/H8 threshold 90 results; one consolidated root-cause defect ledger; the one repair batch and one re-review outcome or blocked owner decision; inline detail rows / skipped — multi-agent capability unavailable, with the same frozen identities and hard-gate result]

Bounded revisions or unresolved items: [None / named items]

Wireframe references consulted: [None — reason the Reference Pass was skipped / one line per source: URL, publisher, retrieval date, structural pattern adopted or rejected]

Visual design phase: [not requested / requested / completed]

### UI Design Handoff

Include this subsection only after the human owner explicitly requests the visual-design phase.

Taste applicability: [applicable / partially_applicable / n/a: reason]

Design method: [design-taste-frontend / frontend-design for named excluded surfaces / explicit gpt-taste alternative for named scope]

Design Read and dials: [one-line Design Read plus DESIGN_VARIANCE / MOTION_INTENSITY / VISUAL_DENSITY when Taste applies; otherwise the platform/design-system basis]

Selected direction: [VD-* ID and one-line visual intent, with confirmed REF-* / RP-* IDs or none] — [approved / provisional / blocked], decided by [human owner]

Frozen PRD basis: [PRD.md path plus revision or SHA-256 used by the HTML and grading stage]

Preview scope: [Included UI-* screens and states; login, registration, recovery, and authentication-error previews recorded n/a without removing production auth requirements]

Key-surface treatments: [Per screen/region: Motion Need Gate plus motion-led / imagery-led / motion + imagery / quiet treatment, with owner or accepted AI-recommendation source]

Functional UI motion evidence: [Per required position: trigger, purpose, deterministic local CSS/JavaScript behavior, normal-mode result, and equivalent reduced-motion result]

Deferred generation handoff: [Per generated media/motion position: placement or trigger, dedicated prompt, source, reduced-motion expectation when applicable, generationStatus: deferred; no provider invoked]

Iconography: [Recommended primary icon set plus named fallback, with cited official-source URLs and retrieval dates / None — the product uses no icons / UNVALIDATED pick and why]

Typography: [Recommended display + body pairing and CJK stack with cited official-source URLs and retrieval dates; loading strategy (self-host/CDN, subsetting, font-display) / Platform-fixed faces — reason / UNVALIDATED pick and why]

Color & dark mode: [Palette derivation and named scale approach with cited source; dark mode in scope or named later scope]

Connected HTML review: [One self-contained design-reference HTML path; complete embedded CSS; left sidebar listing every in-scope UI-* page or screen; working page, state, modal/drawer, feedback, approved-flow interactions, and required local UI motion with a reduced-motion fallback; no live backend, authentication, or generation call]

| UI target | Source path or immutable version | SHA-256 | Routes / states | Responsive scope | Tolerance and allowed deviations |
| --- | --- | --- | --- | --- | --- |
| [Preview ID] | [Path or version] | [Digest] | [UI-* and states] | [Exact PRD viewports or size classes plus browser matrix evidence] | [Comparison method, tolerance, real-data/platform-chrome allowances; named stacking/focus/dismissal behavior for intentional overlays] |

Preview evidence: [Interactive HTML browser matrix; Technical Hard Gate, console, and element-level DOM geometry results; working-control, keyboard/focus, accessibility, responsive, motion in normal and reduced modes, and design-consistency evidence; limitations; diagnostic scores, consolidated defect ledger, bounded repair/re-review outcome, or capability-unavailable skip]

Visual approval is direction conformance, not usability proof or production readiness.

Design System Need Gate: [required / not_required / blocked] — [reason], decided by [owner]

Replacement visual contract when `not_required`: [approved page-faithful target above plus PRD.md and wireframes.html]

Approved wireframe review projection: [wireframes.html path]
```

Keep the `### UI Design Handoff` heading text exactly as written when that optional subsection is present because the design-system workflow consumes it by anchor.

## `wireframes.html`

Produce this file for every UI-bearing product, using `wireframe-guide.md` and `assets/templates/WIREFRAMES.template.html`.

It must be one self-contained local file containing:

1. every `UI-*` page or shipped surface;
2. an all-pages overview and page/route switcher;
3. data-driven controls for the exact PRD responsive set, with at least three ascending web viewports or at least two native/desktop size classes;
4. required state switching for each page;
5. complete per-target order, visibility, grid spans, reflow, and interaction rules for every page;
6. visible product-fit section names plus purpose, priority, elements, working PRD actions, and state treatment;
7. runtime region-overlap and horizontal-overflow QA for the selected matrix entry; and
8. approval status that agrees with `PRD.md`'s `### Wireframe Approval`.

The embedded page data must agree exactly with `PRD.md`; `PRD.md` wins on conflict. Every visible region action maps to exactly one `page`, `overlay`, or `feedback` flow and works locally without a network request. The data block may also project optional deferred `mediaIntent`, `UX-*` traces, and element display contracts described in `wireframe-guide.md`; they inherit the same agreement rule. Use inline CSS and JavaScript only for the structural review shell. Make no external request and include no production component, brand styling, design-reference visual direction, generated imagery, final animation, or design-system token decision. Human approval completes the wireframe phase; do not start visual design or implementation unless separately requested.

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

Create this operational seed only for a package with a web, iOS, or browser-extension release target and only when the final path does not already exist. In short, `product-definition-builder` creates it only when absent. Resolve the template and checker from the sibling `product-activation` skill. If that sibling is unavailable, publish the core product package without an Activation file and report the missing optional handoff; do not invent a local substitute template.

The seed must:

- retain the template's exact headings, table headers, task boundary comments, and English machine anchors;
- fill the product name and every known owner;
- select `core` plus every known surface profile, recording rejected expected profiles as `n/a` with a reason;
- list only the stable web, iOS, and browser-extension release target IDs from `architecture.md` without inventing a SHA or deployed identity; exclude Android, desktop, API-only, and other targets even when the package is hybrid;
- add exactly one Outcome Coverage row for every `## Metrics` metric and every `TEST-*` row marked `Required: Yes`, scoped to that supported Activation target subset;
- leave implementation-owned actions, routes, accounts, queries, release bindings, sources, evidence, authorization, and readiness visibly pending;
- contain secret names only and no secret values; and
- pass `product-activation/scripts/check_activation.py --activation <staged path> --prd <staged PRD.md>` before publication.

Publish a new seed flat at `docs/ACTIVATION.md` in the same approved move as the product package. Once the path exists, `product-activation` owns it. Product Definition reads it for context but never stages, overwrites, archives, resets, or treats its operational status as product approval.

## `outcome-review.md`

Produced only when the owner asks for an outcome review after a deployment, following the workflow's post-publish step. It is a post-deployment record, not part of the drafting package, and its absence from a package is normal.

Use this structure:

```markdown
# Outcome Review: [Product Name]

## Deployed
Deployed SHA: [full Git SHA]
Release reference: [run branch head / release tag — where this SHA came from]
Deployed on: [YYYY-MM-DD]
Targets: [each architecture.md release target this deployment reached, or the subset it covered]
Activation record: [docs/ACTIVATION.md / not present / n/a]
Activation source status: [verified / incomplete / legacy-unavailable / n/a]
Activation sources: [matching verified MS-* IDs, or explicit reason none apply]

## Measurements
| Metric | Baseline | Target | Window | Actual | Source |
| --- | --- | --- | --- | --- | --- |
| [PRD `## Metrics` metric or `TEST-*` expected signal] | [pre-deploy value or "none recorded"] | [the recorded target] | [measurement window] | [measured value or "pending"] | [how the number was produced: analytics, log query, manual count] |

## Feedback
[Observed post-deployment facts: usage, friction, failures, owner remarks. Facts with sources, not wishes.]

## Verdict
Verdict: [no_change / enhancement / incident] — [one-line reason]
[Routing: `enhancement` findings become the next enhancement request's input; `incident` findings enter the next run's `PRD.md` `## Risks` and `## Open Questions`; `no_change` schedules nothing.]

## Open Follow-ups
| Follow-up | Route |
| --- | --- |
| [Item] | [enhancement request / open question / risk] |
```

Rules:

- Record actual against target for every `PRD.md` `## Metrics` metric and every `TEST-*` expected signal the deployment was supposed to move; an empty Measurements table means the review is not done.
- The measurement window is real elapsed time after deployment. A review written at deploy time with "pending" actuals is a stub, not a verdict.
- When `docs/ACTIVATION.md` exists, run its checker with `--prd docs/product/PRD.md --require-verified-sources` and `--require-ready <target-id>` for each reviewed target in its supported active target set. Use only verified `MS-*` sources bound to the same target, deployed SHA, and artifact/build identity. Record Activation as `n/a` for a reviewed Android, desktop, API-only, or other target outside that set; do not pull an unsupported hybrid target into the gate. A configured, blocked, stale, or mismatched source cannot support an actual or verdict.
- A missing Activation record remains allowed for a legacy or non-applicable product, but the review records that state explicitly and does not imply that an unverified analytics or operational source is trustworthy.
- The verdict vocabulary is closed: `no_change`, `enhancement`, or `incident`. Every later run reads this file in full during enhancement detection.

## `architecture.md`

Use this structure:

```markdown
# Architecture: [Product Name]

## Architecture Summary
[Implementation-ready overview in a few sentences: the main pieces, what talks to what, and the one or two decisions that constrain everything else.]

Technology selections and their rationale live in `stack-decisions.md`.

## Product Archetype
[Web app, mobile app, desktop app, browser extension, internal tool, automation or agent workflow, API or hybrid. For a mobile app, name the resolved platform: native iOS, native Android, Flutter, or React Native. For a desktop app, name the resolved platform: macOS, Windows, or cross-platform. For a browser extension, name the resolved browser target: Chrome with Manifest V3 by default; Firefox or Safari as explicit alternatives.]

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

## Integrations
| System | Purpose | Direction | Failure Handling |
| --- | --- | --- | --- |

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

This section is product documentation for the human or CI release process that runs after the engineering harness pushes its branch. The harness does not consume or enforce any field in it.

Expected deployable surfaces: [stable surface IDs, for example `web-app`, `public-api`, `ios-app`]

### Release Target: [stable-target-id]
- Surface: [Stable expected surface ID]
- Surface suffix: [Lowercase kebab-case suffix for this independently released unit]
- Release name: [Production `<product-slug>-<surface-suffix>` or that exact name plus `-dev` for development]
- Provider: [Stage-specific hosting, store, or distribution provider]
- Stage: [development / production]
- Source policy: [exact candidate run branch/ref for the internally tested development release and `main` for production after same-SHA fast-forward, or another exact branch/ref rule including a required signed tag, stated explicitly]
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

Every decision in this file uses the same shape: drivers, then resolved layers with status and authority/evidence on every row. The shared `Alternatives Considered` and `Unresolved Decision Protocol` tables at the end cover all decisions, so options and open decisions are compared in one place instead of repeated once per decision.

Use these statuses per layer: `Required` means a user, organization, or hard external constraint mandates the selection; `Selected` means the current product or repository already adopted it; `Recommended` is evidence-backed advice not yet accepted; `Provisional` is a leading choice pending named evidence. A section may mix statuses. `Authority / evidence` cites the source that justifies the row — for example a dated user statement, organization policy, repository/config path, product requirement IDs, official documentation with check date, or named spike. Authority is not another status label, and `PRD recommendation` alone is not evidence.

Use this structure:

```markdown
# Stack Decisions: [Product Name]

## Frontend Technology Decision
Use this section for every product with a browser frontend. Omit it only when no browser surface exists.

### Decision Drivers
- [Product evidence that determines the choice: content density, interactivity, SEO, rendering, auth, edge data, team capability, reuse, performance, and deployment constraints.]

### Recorded or Recommended Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Deployment / runtime | [e.g. Cloudflare Workers with Static Assets] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Rendering model | [Static, SSG, SSR, on-demand, SPA, islands, or hybrid by route] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Framework | [e.g. Astro, React Router, or none] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| UI library | [e.g. React or none] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Build tool | [e.g. Vite, or framework-managed] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Routing and data | [Approach] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Styling and components | [Approach] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Testing | [Unit, component, end-to-end, accessibility] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |

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

### Recorded or Recommended Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Platform | [native iOS, native Android, Flutter, React Native, macOS, Windows, or cross-platform desktop] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Toolchain | [e.g. Xcode/SwiftUI, Android Studio/Jetpack Compose, Flutter/Dart, Expo/React Native, or the desktop equivalent] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Distribution mechanism | [e.g. App Store/TestFlight, Play Console tracks, EAS Submit, MSIX, notarization — as applicable] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Backend/API integration | [Approach for reaching the backend or APIs] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Push / offline sync | [Push notification and offline/sync approach, when applicable] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Testing | [Unit and UI-automation framework per platform] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |

Compatibility checked on: [YYYY-MM-DD] — official sources: [Direct links]

## Backend and Data Technology Decision
Use this section for every product with a backend, persistent data, or auth requirement. Omit it only when the product provably has none of these.

### Decision Drivers
- [Data shape/relationships, consistency/transaction needs, query complexity, scale, identity/compliance requirements, team capability, platform-managed services, integration surface.]

### Recorded or Recommended Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Service topology | [Monolith or named services; monorepo or polyrepo organization] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Backend runtime / framework | [Selection] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Database category | [Relational / Document / Key-value or cache only / None] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Database engine | [Selection] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Auth strategy | [Build custom / Managed third-party / Platform-native / None] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Auth provider | [Selection] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| API style | [REST / GraphQL / RPC / server actions] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Background jobs / queue | [Selection or not applicable] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| File / object storage | [Selection or not applicable] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |

### Data Entity to Store Mapping
| Entity | Store | Rationale |
| --- | --- | --- |

### Platform and Vendor Compatibility Verification
- Checked on: [YYYY-MM-DD]
- Official sources: [Direct links]
- Runtime/service requirements: [Bindings, connection limits, region/residency, quota, or other constraints]

## Monetization and Partner Channel Technology Decision
Always record the two PRD gate results here. When both are `not_required`, state their reasons and omit the layer table. Otherwise use `monetization-and-partner-channel-guide.md`, compare only current options that fit the resolved model and surfaces, and keep responsibilities separate.

### Decision Drivers
- [Commercial model, buyer, pricing/offer rules, purchase surfaces, entitlement needs, merchant-of-record/tax responsibility, partner motion, attribution/commission/payout, reseller operations, existing systems, team capacity, and current official provider evidence.]

### Recorded or Recommended Stack
| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |
| --- | --- | --- | --- | --- | --- |
| Store commerce / billing | [Native store, RevenueCat Billing, Stripe Billing, Paddle Billing, Lemon Squeezy, existing, custom, or n/a] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Subscription and entitlement source | [RevenueCat, Qonversion, Superwall, native/custom, existing, or n/a] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Paywall / checkout | [Adapty, Superwall, RevenueCat, provider checkout, custom, or n/a] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Merchant of record / tax | [Product company, Paddle, Lemon Squeezy, Stripe arrangement, other, or n/a] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Affiliate / referral / reseller platform | [PartnerStack, Rewardful, FirstPromoter, Lemon Squeezy Affiliates, custom, existing, or n/a] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |
| Attribution, commission, payout, and reseller operations | [Provider/custom boundary] | [Required / Selected / Recommended / Provisional] | [Cited source] | [Reason] | [Constraint] |

Compatibility checked on: [YYYY-MM-DD] — official sources: [Direct links]

---

## Options And Open Decisions

### Alternatives Considered
One row per rejected option, across every decision above.

| Area | Alternative | Where It Fits Better | Why Not Selected Here | Revisit Trigger |
| --- | --- | --- | --- | --- |
| [Frontend / Mobile or desktop / Backend or data / Monetization or partner channel] | [Alternative] | [Context] | [Reason] | [Trigger] |

### Unresolved Decision Protocol
Use only when a layer cannot yet be decided.

| Area | Open Decision | Missing Evidence | Owner | Decision Date | Time-boxed Spike | Pass / Fail Criteria |
| --- | --- | --- | --- | --- | --- | --- |
```

## Optional UI Design And Product Design Handoff

Stop after the human owner approves `wireframes.html` unless they explicitly ask to continue into visual design. On that later request, run `ui-design-pass.md`: record Taste applicability, use `design-taste-frontend` where applicable or `frontend-design` for excluded surfaces, produce the connected interactive design-reference HTML with deferred image and motion handoffs, obtain human visual approval, and freeze the selected result in `PRD.md`'s `### UI Design Handoff`. Pass a known reference use as `design inspiration` or `page-faithful target`; do not infer faithful-copy intent from a URL, screenshot, or Figma frame.

Run the Design System Need Gate after approval. `not_required` is a normal result for a small or single-surface UI; its approved page-faithful target plus `PRD.md` and `wireframes.html` form the replacement visual contract. When the gate is `required`, pass the approved UI Design Handoff and staged product sources to `../design-system-compiler/SKILL.md`; it owns `design-system.md` and `design-system.json`, preserves stable `DS-*` and `DS-COMP-*` IDs, and does not reopen visual direction by default. If the product has no shipped UI surface, record the reason in `PRD.md` and publish no placeholder wireframe, preview, or design artifacts.

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

- Each artifact opens with human-readable content and keeps ID matrices and decision records at the end: `PRD.md` opens with `## At a Glance`, and for a UI-bearing product closes with `## Builder UX Direction Decision`, including `### Wireframe Approval` and the optional `### UI Design Handoff` only when visual design was requested; `architecture.md` opens with `## Architecture Summary` and closes with `## Architecture Trace Index`; `stack-decisions.md` closes with `## Options And Open Decisions`.
- `## At a Glance` answers what the product is, who it is for, why now, what success looks like, and the biggest risk — one line each, on one screen.
- Each artifact is within reach of its length budget in "How To Read This Package". A file well over budget names which content should have moved to another artifact instead of expanding.
- No table in the package exceeds seven columns except the environment contract in `architecture.md`, whose columns are all release-critical.

### Completeness

- `PRD.md`, `architecture.md`, and `stack-decisions.md` are present in the run-specific staging directory and are ready to publish under `docs/product/`. The staged `DEPLOYMENT.md` is present for every package with a deployable surface (a purely local product records `manual` mode or the skip in `stack-decisions.md` instead), contains the Required Secrets and Variables and External Console Setup handoff sections, records names and destinations but no values, and leaves implementation-owned details visibly unresolved for pre-deploy reconciliation. When the package has a web, iOS, or browser-extension release target, the sibling `product-activation` skill is available, and the live path is absent, a staged create-once `ACTIVATION.md` seed passes its checker against the staged PRD; an existing live Activation record is preserved and no replacement is staged. The staged `DOCUMENTS.md` manifest is present with its status column filled for every document this package creates or preserves. For a UI-bearing complete wireframe package, approved `wireframes.html` and `PRD.md`'s approved `### Wireframe Approval` are also present. An approved UI Design Handoff and validated design-system pair are required only when the owner explicitly requested and completed that later visual-design phase. For a product with no UI surface, wireframe and design artifacts are absent and `PRD.md` records that skip with its reason.
- `## Non-Functional Requirements` is always present immediately after `## Functional Requirements`. Every applicable quality attribute has a measurable `PRD-*` requirement with a measure and target; non-applicable categories are explicitly `N/A` with a reason. Vague adjectives alone do not pass. Units, tested population or traffic shape, measurement window, and percentile are present where applicable.
- `## Test Obligations` is always present after `## Open Questions` and before the trailing Builder UX decision. Its rows use stable `TEST-*` IDs and include obligation, test type, required status, upstream trace IDs, and an expected signal.
- Every `Must` functional requirement and every applicable non-functional requirement maps to at least one `TEST-*` row marked `Required: Yes`. No required obligation is left as anonymous prose.
- Every `PRD.md` records both the Monetization Infrastructure Gate and Partner Channel Gate with `required`, `not_required`, or `blocked` plus a reason. Commercial products record the monetization model, pricing/offer rules, purchase surfaces, entitlement source, and merchant-of-record/tax owner. Products with outside distribution record affiliate, referral, reseller, or hybrid motion plus attribution, commission/discount, reversal, payout, customer ownership, provisioning, support, termination, and fraud rules as applicable.
- A pricing strategy never silently selects RevenueCat. `stack-decisions.md` compares current relevant providers through `monetization-and-partner-channel-guide.md`, cites official evidence and retrieval date, separates store/billing, entitlement, paywall/checkout, merchant-of-record/tax, and partner-channel layers, and records rejected alternatives and revisit triggers. Affiliate, referral, and reseller remain distinct motions.
- When either gate is required, `architecture.md` defines the applicable revenue and partner entities, stable identity joins, verified idempotent event/webhook flows, retry/replay/reconciliation, refund/chargeback effects, entitlement grant/revoke/restore, commission reversal, and reseller provisioning/deprovisioning. Required UI surfaces and `TEST-*` obligations cover the chosen lifecycle, including failure and termination states.
- For a UI-bearing product, `PRD.md` records the human Builder UX Direction owner and concrete choices for experience priority, guidance/control, information density, interaction/layout, motion direction and decision authority, confirmation/recovery, validation depth, and decision status. Its Motion Need Gate classifies every key surface as `required`, `recommended`, `not_required`, or `blocked` with purpose, trigger, source, and reduced-motion fallback.
- For a UI-bearing product, `wireframes.html` maps every `UI-*` entry exactly once in one self-contained `wireframes/3` file with working overview, page, responsive-target, state, section-label, runtime layout-QA, and PRD action controls; the checker keeps `wireframes/2` read compatibility for unchanged historical files. Every visible region action in schema 3 maps to exactly one local `page`, `overlay`, or `feedback` flow. Every PRD entry has exactly one `` `responsive` `` anchor; its set matches the HTML, contains at least three ascending web viewports or at least two native/desktop size classes, and every screen supplies complete per-target order, visibility, columns, spans, reflow, and interaction rules. Optional `mediaIntent` entries are validated deferred MCP-generation handoffs, not generated output. The file contains no design-reference styling or product implementation code, agrees with `PRD.md`, passes `wireframe-guide.md`'s quality check and `check_wireframe_html.py --require-filled --require-approved`, and has one human `approved` decision recorded in `PRD.md` before the wireframe phase completes. The approval record includes the real-browser matrix result and the PRD-bound diagnostic wave, consolidated ledger, and bounded repair/re-review outcome, or the exact capability-unavailable skip when the host cannot run that stage. No unintended overlap, clipping, occlusion, or horizontal overflow exists at any UI surface, responsive target, or non-`n/a` state, and every intentional overlay names its stacking, focus, and dismissal rule. `PRD.md` also records either the consulted wireframe references or the reason the Reference Pass was skipped.
- An enhancement package records its UI-impact classification — `none`, `structure`, `style`, or `both`. When the impact is `structure` or `both`, the refreshed `### Wireframe Approval` covers the changed `UI-*` scope. When it is `style` or `both`, the package carries the owner's recorded decision to re-run the UI Design Pass or keep the existing direction; a style-impacting enhancement with an unchanged handoff or design-system pair and no recorded owner decision does not validate.
- A wireframe-only package records `Visual design phase: not requested` and validates without Taste, preview evidence, a UI Design Handoff, a Design System Need Gate, or design-system artifacts. When visual design was explicitly requested, `PRD.md` records those later decisions and evidence, and the `### UI Design Handoff` carries an `Iconography:` line recording the recommended set with cited sources or an explicit skip, `UNVALIDATED`, or no-icons reason, a `Typography:` line recording the pairing, CJK stack, and loading strategy or an explicit skip or `UNVALIDATED` reason, and a `Color & dark mode:` line recording the palette derivation and dark-mode scope — a visual package missing any of these three lines does not validate.
- Builder preference is not presented as user validation. Conflicts with user evidence or accessibility requirements remain explicit hypotheses, validation needs, or open questions.
- For every deployable web, API, mobile, desktop, or browser-extension surface, `architecture.md` has a provider-neutral `## Release Targets` section with an explicit expected deployable-surface inventory and at least one development-stage and one production-stage target for every expected surface. A missing expected surface fails validation. Every target has a stable ID, an explicit lowercase kebab-case surface suffix and release name, separate stable surface and stage-specific provider fields, a source policy naming the exact branch or ref, artifact kind, signing requirement, exact channel/track, submission/promotion/review or manual-approval path, actual availability signal, rollout, and rollback or forward-fix path. Production uses the canonical `<product-slug>-<surface-suffix>` name without `-prod`; development uses that exact name plus `-dev`; release names are globally unique across surface IDs. Different providers by stage are valid for the same surface.
- Upload, submission, deployment-command success, notarization, or store approval alone is not accepted as availability. Hosted targets prove the route/API is serving and passes smoke checks; store or signed-installer targets prove the intended audience can actually install/download the artifact and that its release smoke check passes.
- For a deployable hosted web, API, or backend target, `architecture.md` records the platform resolved during interview (via `AskUserQuestion` unless the user or repository already named one — never a silent default) and defines one codebase with separate development and production environments (named Workers when the platform is Cloudflare).
- The hosted environment contract names the exact candidate run branch/ref as the internally tested development source and remote `main` as production. Initial delivery and enhancements both start from observed remote `main`; the exact candidate passes internal and applicable isolated development-environment verification before separately authorized fast-forward promotion to `main`. It also names distinct deployment units, isolated resources/secrets/data/auth/payment modes, migration order, evidence, and recovery. Development never uses production customer data, sessions, or live payment mutations. Native targets remain provider-neutral.
- Native release recovery does not claim instant rollback when the channel cannot perform it. It records how to halt or reduce a staged/phased rollout and ship a corrected signed forward-fix through the same submission, review, or distribution path.
- For a browser product, `stack-decisions.md` records the required/selected stack or recommends one frontend stack, separates its technology layers, maps rendering by route, and records official-source verification date and runtime constraints.
- Every frontend layer row records Selection, Status, Authority / evidence, Why It Fits, and Constraint / follow-up. Status is accurate per layer, authority cites its source rather than repeating a status label, and one section may mix statuses.
- For a product with a backend, persistent data, or auth requirement, `stack-decisions.md` records the required/selected backend stack or recommends one, separates service topology first, then backend runtime, database category, database engine, auth strategy, and auth provider as distinct layers, maps data entities to stores, and records official-source verification date and runtime/service constraints. Service topology states monolith versus named services and monorepo versus polyrepo organization.
- Every backend/data layer row records Selection, Status, Authority / evidence, Why It Fits, and Constraint / follow-up. Status is accurate per layer, authority cites its source rather than repeating a status label, and the database category and auth strategy trace back to the interview's `AskUserQuestion` answers rather than a silent default.
- For a product with a mobile app or desktop app target, `stack-decisions.md` records the required/selected stack or recommends one per `mobile-stack-selection.md`, separates platform, toolchain, distribution mechanism, backend/API integration, push/offline-sync approach, and testing as distinct layers, and records official-source verification date.
- Every mobile/desktop layer row records Selection, Status, Authority / evidence, Why It Fits, and Constraint / follow-up. Status is accurate per layer, authority cites its source rather than repeating a status label, and one section may mix statuses.
- Every rejected option for any stack decision appears once in `stack-decisions.md`'s shared `Alternatives Considered` table with its area named, rather than repeated per decision section.
- Any unresolved frontend, backend, database, auth, or mobile/desktop decision appears in `stack-decisions.md`'s shared `Unresolved Decision Protocol` table with an owner, deadline, time-boxed spike, and pass/fail criteria; a bare `TBD` does not pass validation.
- Before publishing, every `stack-decisions.md` layer row is `Required`, `Selected`, or `Recommended`. A `Provisional` row passes only when the user resolved it or explicitly accepted it as `Provisional`, and that acceptance is recorded in `stack-decisions.md`. A silent Provisional layer does not validate, because `delivery-harness` treats it as a stop condition at scaffold time.
- When the visual-design phase was explicitly requested, the Design System Need Gate is not `blocked`. Its UI Design Handoff records one connected self-contained design-reference HTML review file: the left sidebar lists every in-scope `UI-*` page or screen, every visible product control performs its recorded page, state, modal/drawer, or feedback behavior, required functional UI motion runs locally with an equivalent reduced-motion path, and full CSS is present. Login, registration, recovery, and authentication-error previews are recorded `n/a` for this visual pass; the HTML starts from the main or authenticated entry without live auth. Generated image and motion positions remain static deferred-generation placeholders with dedicated prompts and no provider call. The handoff records its frozen PRD identity plus the PRD-bound diagnostic and bounded repair/re-review outcome, or the exact capability-unavailable skip. When the gate is `required`, the package includes the validated pair returned by `design-system-compiler` and the parent records its exact staged paths and passing checks. When it is `not_required`, no placeholder pair is present and the approved page-faithful UI target, `PRD.md`, and `wireframes.html` are explicitly named as the replacement visual contract.
- If produced, `implementation-plan.md` includes milestones, dependency order, non-canonical Harness handoff signals, test strategy, release plan, rollback plan, and unresolved decisions. Its test strategy reuses the canonical `TEST-*` IDs from `PRD.md`; it does not replace them with anonymous checks or newly numbered duplicates. Its release plan reuses the stable release target IDs from `architecture.md`.
- The market-research gap pass either produced `market-research.md`, or the package records which reason skipped it — the user declined, no web search or fetch tool was available, the package is a trivial stub, or the role returned blocked. A silently missing pass does not validate.
- For a new package, `PRD.md` records a `### Research Gate` with a `go`, `clarify`, or `stop` value, and either `research-assessment.md` is staged with the package or the gate records which skip reason applied — the user declined the assessment, no web search or fetch tool was available, or the package is a trivial stub. An enhancement package cites the prior package's gate unchanged instead of re-running the assessment. A silently missing gate does not validate.
- When `research-assessment.md` is present, every factual row cites a source ID resolving to a `## Sources` row with publisher, URL, and retrieval date, or is marked `UNVALIDATED` with what was searched. No competitor, price, funding figure, user count, or market size appears without a source.
- When `market-research.md` is present, every factual row cites a source ID resolving to a `## Sources` row with publisher, URL, and retrieval date. Any claim without one is marked `UNVALIDATED` with what was searched. No competitor, price, funding figure, user count, or market size appears without a source.
- When the pass was skipped or blocked, `PRD.md`'s `## Assumptions` records that the market context is unvalidated.
- Findings that changed the package cite their `MR-*` IDs in the sections they changed, and `PRD.md` states conclusions rather than restating the competitor table, sources, or retrieval dates. Findings that would widen product scope are recorded as open questions or recommendations, not applied silently.
- When Dynamic Workflow was used, every required role has an explicit result, failed agents are retained as blocked lanes, and trace/consistency verifier findings are resolved or recorded before finalization. Workflow output is treated as a candidate; the parent still owns staging and publication.

### Publication

- No current-package artifact will be published outside `docs/product/` unless the user explicitly requested another location.
- The superseded-document inventory excludes `docs/product/archived/`, unrelated documents, and ambiguous candidates.
- In enhancement mode, unaffected sections, `PRD-*`, `ARCH-*`, `UI-*`, `UX-*`, `TEST-*`, `MR-*`, `RA-*` IDs, and stable release target IDs from the prior package were carried forward unchanged rather than regenerated, and the diff is scoped to what the new discovery actually added, changed, or removed; new TEST IDs cover only obligations that were previously uncovered, and new release target IDs cover only destinations that were previously uncovered.
- Validation does not trigger publication by itself. Exact overwrite and archive moves are already authorized, or the staged package remains unchanged while approval is requested.

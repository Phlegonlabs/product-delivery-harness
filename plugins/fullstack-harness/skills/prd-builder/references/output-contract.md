# Output Contract

Produce a core multi-file Markdown PRD package. Stage and publish it according to `artifact-lifecycle.md`. The final package belongs under `docs/product/`. Use exactly these artifact names unless the user requests different names:

- `docs/product/PRD.md`
- `docs/product/architecture.md`
- `docs/product/stack-decisions.md`
- `docs/product/wireframes.md` for a UI-bearing product

A product with no UI surface — a headless API or backend service, or an automation whose only surfaces belong to someone else's client — publishes no `wireframes.md`, `design-system.md`, or `design-system.json`, and records that skip in `PRD.md`. Never publish a placeholder wireframes file for a product with no screens.

This package covers the product spec and the design system. For a UI-bearing product it also publishes `design-system.md` and `design-system.json`, contracted below.

It also publishes `docs/product/market-research.md` when the post-draft market-research gap pass ran and returned findings. That pass is on by default for a non-trivial package; when the user declined it, no web tool was available, or the role returned blocked, the package publishes without the file and records the unvalidated market context in `PRD.md`'s `## Assumptions`. See `market-research-guide.md`.

It stays out of the page layer. Do not add per-route recipes, per-route high-fidelity HTML mockups, a component catalog page, or page-level visual acceptance specs. The design system is defined once at the system level; implementation composes each route from `wireframes.md` plus the design system, and a route that needs something the system lacks comes back as a design-system change rather than a page-local exception.

`wireframes.md` is the canonical source for product scope and screen structure. When the user explicitly authorizes the optional `frontend-design` Preference & HTML Exploration handoff in `wireframe-guide.md`, its two or three candidate directions and approved selected HTML remain non-canonical design-stage evidence outside this package. They cannot change scope or silently replace a wireframe; structural findings return to the PRD owner for a bounded wireframe revision and another quality-check pass.

Produce `docs/product/implementation-plan.md` only when the user explicitly asks for delivery sequencing or implementation planning.

Default all artifact content to English unless the user explicitly asks for another language.

## How To Read This Package

Every artifact has one primary reader and one job. Write for that reader.

| Artifact | Primary reader | Answers |
| --- | --- | --- |
| `PRD.md` | Anyone deciding whether to build this | What is it, for whom, and what counts as done |
| `wireframes.md` | A designer or frontend engineer | What each screen must show and do |
| `architecture.md` | An engineer about to implement | How the system is shaped and where the risk is |
| `stack-decisions.md` | An engineer choosing or reviewing technology | Which stack, and why that one |
| `market-research.md` | Anyone questioning a product claim in `PRD.md` | What already exists out there, and what the evidence is |
| `design-system.md` + `design-system.json` | A designer or frontend engineer styling a screen | The binding visual contract — tokens, primitives, components, and states; read alongside `wireframes.md` |

Reading order is `PRD.md` → `wireframes.md` → `architecture.md` → `stack-decisions.md`. `market-research.md` is evidence, not narrative: read it when a `PRD.md` statement cites an `MR-*` ID and you want the source behind it.

Two rules keep the package readable:

- **Meaning before bookkeeping.** Each file opens with what a human needs to understand the product and ends with the ID matrices and decision records that machines, auditors, and downstream skills need. Never open a file with a trace table.
- **One notation per block.** Prose, ASCII, and ID tables do not interleave inside a section. A table wider than seven columns is a sign the content wants to be a list instead.

Length budget. These are targets, not caps — say less when the product is simple, and go over only when the product is genuinely more complex, not when a section drifted:

- `PRD.md`: about 200 lines. `## At a Glance` fits on one screen.
- `architecture.md`: about 250 lines.
- `stack-decisions.md`: about 150 lines.
- `wireframes.md`: about 40 lines per screen, plus roughly 10 lines per visible region block.
- `market-research.md`: about 150 lines. Findings and sources, not an industry report.

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

## Frontend Delivery Requirements
- [Target devices and browsers, content/interactivity profile, SEO, rendering, performance, accessibility, localization, offline, and deployment constraints]

Omit this section only when the product has no browser frontend.

## Data and Integration Requirements
- [Data objects, external systems, freshness, retention]

## Business Rules
- [Rules, thresholds, approvals, calculations]

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
| Confirmation and recovery | [Confirm / undo / retry / escalation expectations] | [Reason] | [selected / provisional / assumed] | [Method or none] |

Validation depth: [lightweight direction-conformance review only / moderate (conformance plus targeted checks) / deep (formal usability or user-evidence validation)] — [selected / provisional / assumed], decided by [decision owner]
This is the single recorded home for the interview's validation-depth answer, so the design-system step and downstream skills can read it here instead of re-asking.

Builder direction is a product input, not usability proof. Record any conflict with user evidence or accessibility requirements as a hypothesis or open question.
```

Keep this section's heading text exactly as written. `wireframes.md` links to it by anchor (`PRD.md#builder-ux-direction-decision`); the anchor survives the section moving to the end of the file, but not the heading being renamed.

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

## `architecture.md`

Use this structure:

```markdown
# Architecture: [Product Name]

## Architecture Summary
[Implementation-ready overview in a few sentences: the main pieces, what talks to what, and the one or two decisions that constrain everything else.]

Technology selections and their rationale live in `stack-decisions.md`.

## Product Archetype
[Web app, mobile app, desktop app, internal tool, automation or agent workflow, API or hybrid. For a mobile app, name the resolved platform: native iOS, native Android, Flutter, or React Native. For a desktop app, name the resolved platform: macOS, Windows, or cross-platform.]

## System Context
[Actors, systems, dependencies.]

## Component Architecture
| ARCH ID | Component | Responsibility | Upstream trace IDs | Notes |
| --- | --- | --- | --- | --- |

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

## Deployment and Operations
[Hosting, environments, config, migrations, queues, cron, rollback.]

For every deployable hosted web, API, or backend target, include this environment contract (Cloudflare Worker naming shown as the worked example; substitute the resolved platform's equivalent deployment unit). Do not use this two-row hosted-environment table for native mobile or desktop store/signed-installer distribution:

| Target | Exact Release Source | Deployment Unit | Data / Bindings / Secrets | Auth Mode | Payment Mode | Migration Order | Deployed Verification | Rollback |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Development | [The pushed integration-branch head after current-head CI, or the head of an explicitly retained integration branch] | [Distinct development deployment unit, e.g. Cloudflare Worker, Vercel project environment, AWS stack] | [Isolated non-production resources] | [Development] | [Sandbox or not applicable] | [Classification, command, and ordering or not applicable] | [URL, version, checks, smoke, evidence] | [Prior development version] |
| Production | [The default-branch head after development PASS] | [Distinct production deployment unit] | [Production resources] | [Production] | [Live or not applicable] | [Classification, command, and ordering or not applicable] | [URL, version, production smoke, evidence] | [Prior production version] |

State that both hosted targets use one repository and one codebase. Do not reuse production data, sessions, secrets, or live payment mutations in development. Write each Migration Order cell so the human or CI release process can run it in order.

## Release Targets
Use this provider-neutral section for every deployable web, API, mobile, or desktop surface, including hosted targets already summarized in the environment table above. First record the complete expected deployable-surface inventory using stable surface IDs. Then record one block per exact destination and give it a stable target ID. Every expected surface needs at least one `development` target and one `production` target; a package that omits an expected surface is incomplete. Keep the stable `surface` identity separate from `provider`, because one surface may use different providers by stage. Keep surface and target IDs stable across revisions; retire rather than reuse an ID when its meaning changes.

This section is product documentation for the human or CI release process that runs after the engineering harness pushes its branch. The harness does not consume or enforce any field in it.

Expected deployable surfaces: [stable surface IDs, for example `web-app`, `public-api`, `ios-app`]

### Release Target: [stable-target-id]
- Surface: [Stable expected surface ID]
- Provider: [Stage-specific hosting, store, or distribution provider]
- Stage: [development / production]
- Source policy: [The exact branch or ref this release is built from — for example the pushed integration-branch head for development, or the default-branch head after merge for production. State any other source rule, such as a signed tag, explicitly rather than leaving it implied]
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

---

## Options And Open Decisions

### Alternatives Considered
One row per rejected option, across every decision above.

| Area | Alternative | Where It Fits Better | Why Not Selected Here | Revisit Trigger |
| --- | --- | --- | --- | --- |
| [Frontend / Mobile or desktop / Backend or data] | [Alternative] | [Context] | [Reason] | [Trigger] |

### Unresolved Decision Protocol
Use only when a layer cannot yet be decided.

| Area | Open Decision | Missing Evidence | Owner | Decision Date | Time-boxed Spike | Pass / Fail Criteria |
| --- | --- | --- | --- | --- | --- | --- |
```

## `wireframes.md`

Use this structure:

````markdown
# Wireframes: [Product Name]

## Wireframe Direction
- Fidelity: Low
- Builder UX direction source: [PRD.md#builder-ux-direction-decision]
- Decision status: [selected / provisional / assumed, with unresolved items]
- Product visual inputs: [Known brand references, hard limits, and product-specific visual goals; high-fidelity preference discovery deferred]
- Structural interpretation: [Hierarchy, spacing, density, grouping, imagery, and interaction-tone consequences]
- Canonical structure: [This `wireframes.md`; downstream visual candidates cannot change scope, screen structure, actions, states, region responsibilities, or trace IDs]
- Optional preference & HTML exploration handoff: [not requested / explicitly authorized for the same one or two representative UI IDs; owner and selected IDs]
- Visual layer: [Tokens, typefaces, palette, primitive contracts and their closed variant sets, and detailed art direction live in `design-system.md` and `design-system.json`, drafted after this file from the screens below]

## Navigation Model
[Primary navigation, tabs, routes, or channels.]

## User Flow
```mermaid
flowchart TD
  A["Entry"] --> B["Core Action"]
  B --> C["Success State"]
```

## Screen: [Name]

Route(s): [Every route this screen serves, exactly as the product addresses it — `/settings/billing`, `/orders/:id`, a native route or deep-link name, or `n/a` with a reason for a screen with no addressable route]

Main purpose: [Single primary goal, one sentence]

Primary emphasis: [What gets the strongest weight, and why]

Secondary / quiet: [What stays present but subordinate]

Layout pattern: [Landing / workspace / dashboard / form or wizard / search or catalog / justified custom pattern] — chosen because: [one sentence tying the pattern to the main purpose]

Density: [Sparse / balanced / dense, with a task or content reason]

```text
+------------------------------------------------+
| Header                                         |
+------------------------------------------------+
| [Exact copy/data or DISPLAY: responsibility]  |
|                                                |
| [Exact primary action label]                   |
+------------------------------------------------+
```

### States
- Loading:
- Empty:
- Error:
- Permission:
- Success:

### Content, Style, Media & Motion Notes
One block per visible region, in the order the region appears on screen.

**UI-001-R01 — [Region]**
- Content mode: [exact copy / display contract]
- Exact wording or display contract: [Verbatim wording, or what to show + intended takeaway/action + source + constraints]
- Content priority: [must-have / secondary / defer]
- Style direction: [Visual job and hierarchy/comprehension purpose]
- Image / media: [required / optional / none; purpose]
- Motion: [required / optional / none; purpose]
- Notes: [Status, fallback, or design handoff question]
- Trace IDs: PRD-001, UX-001

### Trace
UI ID: UI-001

Trace IDs: PRD-001, UX-001, ARCH-001
````

## `design-system.md` and `design-system.json`

Publish both for a UI-bearing product; skip both for a product with no UI surface and record that decision. Follow `assets/templates/DESIGN_SYSTEM.template.md` and `assets/templates/DESIGN_SYSTEM.template.json`, and read `references/design-system-guide.md` before drafting either.

A UI-bearing product ships without the pair only when the user explicitly overrides the requirement — for example because implementation builds against a design system this package does not own. That is the only valid skip for a UI-bearing product; the drafter never decides it. `PRD.md`'s `## Assumptions` records who asked for the override, the reason, and what visual contract implementation uses instead.

Draft them after `wireframes.md`: the primitive inventory is derived from the screens the wireframes actually contain, not invented ahead of them.

`design-system.md` owns the reasoning, ratios, guardrails, and decisions. Its machine-contract block is generated and is not hand-edited.

`design-system.json` is the sole structured authority and the only file downstream tooling parses. Required keys:

| Key | Required | Contract |
|---|---|---|
| `schema` | yes | Literal `design-system/1`. |
| `product`, `platform` | yes | Non-empty strings. `platform` is one of `web`, `ios`, `android`, `flutter`, `react-native`, `macos`, `windows`, or `desktop`. Any browser-surfaced product, including an internal tool with a browser frontend, uses the literal value `web`; `viewports` requires exactly `web`. |
| `tokenSources` | yes | Non-empty list of paths. The only files where a raw color, dimension, or motion value may appear. Matched as path suffixes, so give enough of the path to be unambiguous — `theme/vars.css`, not `vars.css`. |
| `primitiveSources` | yes | List of paths whose job is defining control and surface selectors. May be empty when the product has no such file yet. Same suffix-matching rule. |
| `viewports` **or** `sizeClasses` | exactly one | `viewports` is a non-empty list of unique positive numbers, for a web target only. `sizeClasses` is a non-empty list of unique non-empty strings, for a native or desktop target. Shipping both, neither, or an empty set is an error. |
| `tokens` | yes | Object of token groups (`color`, `space`, `radius`, `fontSize`, `lineHeight`, `shadow`, `duration`, `easing`). Every value referenced anywhere in the product appears here. |
| `primitives` | yes | Object keyed by primitive name. Each value has a `layer` of `layout`, `surface`, `typography`, or `control`, an optional `class` when the base class differs from the kebab-cased name, and one list per variant axis. Every variant list is a closed set. |
| `productComponents` | no | Object keyed by component name, each with `dsId`, `requiredContentOrder`, `composes`, and `states`. |
| `motionVariants` | no | List of named motion variants a call site may reference. |
| `stateMatrix` | yes | The states every screen must cover or explicitly mark `n/a`. |

`requiredContentOrder` is the ordered list of content fields a product component must render, in the order it renders them. Every field on it is a **never-drop field**: implementation may not reorder the list, drop a field at a narrow viewport or size class, hide one behind a truncation rule, or omit one in a denser variant. A field that may legitimately disappear does not belong on the list. `fullstack-harness-engineering`'s Content contract conformance gate checks the built component against this list, so a component published without the key fails pair validation. The generated Markdown contract reproduces the ordered list exactly.

The two files must agree: neither may carry a token, primitive, variant, or state the other does not.

### Design System Trace IDs

| Family | Covers |
|---|---|
| `DS-*` | A signature visual decision in the Product-Specific Visual Thesis |
| `DS-COMP-*` | A product component |

Preserve these across revisions and never reuse a retired ID for a different meaning, exactly like `PRD-*` and `UI-*`.

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

- Each artifact opens with human-readable content and keeps ID matrices and decision records at the end: `PRD.md` opens with `## At a Glance`, and for a UI-bearing product closes with `## Builder UX Direction Decision`; `architecture.md` opens with `## Architecture Summary` and closes with `## Architecture Trace Index`; `stack-decisions.md` closes with `## Options And Open Decisions`.
- `## At a Glance` answers what the product is, who it is for, why now, what success looks like, and the biggest risk — one line each, on one screen.
- Each artifact is within reach of its length budget in "How To Read This Package". A file well over budget names which content should have moved to another artifact instead of expanding.
- No table in the package exceeds seven columns except the environment contract in `architecture.md`, whose columns are all release-critical.
- Every screen block in `wireframes.md` leads with `Route(s):` and `Main purpose:` and carries its `UI ID` and trace IDs in the closing `### Trace` block, not ahead of the human-readable lines.
- Every screen records `Route(s):` using the product's real addressing, or `n/a` with a reason. Every route named in `## Navigation Model` resolves to exactly one screen block, and no two screens claim the same route. Implementation resolves a route to its screen entry through this field, so an unlisted or ambiguous route blocks the build.

### Completeness

- `PRD.md`, `architecture.md`, and `stack-decisions.md` are present in the run-specific staging directory and are ready to publish under `docs/product/`. `wireframes.md` is present for a UI-bearing product; for a product with no UI surface it is absent and `PRD.md` records that skip with its reason.
- `## Non-Functional Requirements` is always present immediately after `## Functional Requirements`. Every applicable quality attribute has a measurable `PRD-*` requirement with a measure and target; non-applicable categories are explicitly `N/A` with a reason. Vague adjectives alone do not pass. Units, tested population or traffic shape, measurement window, and percentile are present where applicable.
- `## Test Obligations` is always present after `## Open Questions` and before the trailing Builder UX decision. Its rows use stable `TEST-*` IDs and include obligation, test type, required status, upstream trace IDs, and an expected signal.
- Every `Must` functional requirement and every applicable non-functional requirement maps to at least one `TEST-*` row marked `Required: Yes`. No required obligation is left as anonymous prose.
- For a UI-bearing product, `PRD.md` records the human Builder UX Direction owner and concrete choices for experience priority, guidance/control, information density, interaction/layout, confirmation/recovery, validation depth, and decision status.
- Builder preference is not presented as user validation. Conflicts with user evidence or accessibility requirements remain explicit hypotheses, validation needs, or open questions.
- For every deployable web, API, mobile, or desktop surface, `architecture.md` has a provider-neutral `## Release Targets` section with an explicit expected deployable-surface inventory and at least one development-stage and one production-stage target for every expected surface. A missing expected surface fails validation. Every target has a stable ID, separate stable surface and stage-specific provider fields, a source policy naming the exact branch or ref, artifact kind, signing requirement, exact channel/track, submission/promotion/review or manual-approval path, actual availability signal, rollout, and rollback or forward-fix path. Different providers by stage are valid for the same surface.
- Upload, submission, deployment-command success, notarization, or store approval alone is not accepted as availability. Hosted targets prove the route/API is serving and passes smoke checks; store or signed-installer targets prove the intended audience can actually install/download the artifact and that its release smoke check passes.
- For a deployable hosted web, API, or backend target, `architecture.md` records the platform resolved during interview (via `AskUserQuestion` unless the user or repository already named one — never a silent default) and defines one codebase with separate development and production environments (named Workers when the platform is Cloudflare).
- The hosted environment contract names the exact release source for each stage (the pushed integration-branch head or an explicitly retained integration branch for development; the default-branch head for production), distinct per-environment deployment-unit names, isolated resources/secrets/data/auth/payment modes, migration order, deployed-environment verification, evidence, and rollback. For Cloudflare delivery specifically, that means distinct Worker names. Development never uses production customer data, sessions, or live payment mutations. Native mobile and desktop targets remain in provider-neutral release blocks rather than this hosted table.
- Native release recovery does not claim instant rollback when the channel cannot perform it. It records how to halt or reduce a staged/phased rollout and ship a corrected signed forward-fix through the same submission, review, or distribution path.
- For a browser product, `stack-decisions.md` records the required/selected stack or recommends one frontend stack, separates its technology layers, maps rendering by route, and records official-source verification date and runtime constraints.
- Every frontend layer row records Selection, Status, Authority / evidence, Why It Fits, and Constraint / follow-up. Status is accurate per layer, authority cites its source rather than repeating a status label, and one section may mix statuses.
- For a product with a backend, persistent data, or auth requirement, `stack-decisions.md` records the required/selected backend stack or recommends one, separates service topology first, then backend runtime, database category, database engine, auth strategy, and auth provider as distinct layers, maps data entities to stores, and records official-source verification date and runtime/service constraints. Service topology states monolith versus named services and monorepo versus polyrepo organization.
- Every backend/data layer row records Selection, Status, Authority / evidence, Why It Fits, and Constraint / follow-up. Status is accurate per layer, authority cites its source rather than repeating a status label, and the database category and auth strategy trace back to the interview's `AskUserQuestion` answers rather than a silent default.
- For a product with a mobile app or desktop app target, `stack-decisions.md` records the required/selected stack or recommends one per `mobile-stack-selection.md`, separates platform, toolchain, distribution mechanism, backend/API integration, push/offline-sync approach, and testing as distinct layers, and records official-source verification date.
- Every mobile/desktop layer row records Selection, Status, Authority / evidence, Why It Fits, and Constraint / follow-up. Status is accurate per layer, authority cites its source rather than repeating a status label, and one section may mix statuses.
- Every rejected option for any stack decision appears once in `stack-decisions.md`'s shared `Alternatives Considered` table with its area named, rather than repeated per decision section.
- Any unresolved frontend, backend, database, auth, or mobile/desktop decision appears in `stack-decisions.md`'s shared `Unresolved Decision Protocol` table with an owner, deadline, time-boxed spike, and pass/fail criteria; a bare `TBD` does not pass validation.
Every `wireframes.md` and design-system check below applies only to a UI-bearing product. For a product with no UI surface, skip them and confirm instead that `PRD.md` records the skip and its reason.

- `wireframes.md` includes ASCII wireframes and at least one Mermaid user flow.
- `wireframes.md` identifies itself as the canonical structural source and records whether the optional downstream `frontend-design` Preference & HTML Exploration handoff is not requested or explicitly authorized for the same one or two representative `UI-*` IDs.
- No `frontend-design` candidate or selected HTML is stored in the staged or published PRD package. Candidate directions never add scope or silently change the canonical wireframes; any structural finding returns to the PRD owner for a bounded wireframe revision and another checklist pass.
- `wireframes.md` records brand references, visual hard limits, and product-specific visual goals while explicitly deferring high-fidelity preference discovery. It does not freeze a style catalog, tokens, or a `modern-minimal` default.
- `wireframes.md` cites the Builder UX Direction Decision and preserves whether each controlling choice is selected, provisional, or assumed.
- Every important screen names a layout pattern and density justified by its primary task and content shape.
- Every important screen states a one-sentence main purpose, names its primary emphasis and secondary/quiet content, and ties its layout pattern to that purpose with a stated reason. A main purpose that could describe any screen in the product (for example "helps the user get things done") does not pass; it must be specific to this screen's job.
- The screen's ASCII layout is drawn from the skeleton matching its stated layout pattern in `references/wireframe-guide.md`'s Layout Skeletons by Pattern, not the workspace skeleton reused by default for a landing, wizard, or search screen.
- For a product with any public-facing marketing, landing, or SEO-relevant page, the exact copy on those screens has a clear headline/H1 and keyword-relevant (not stuffed) wording, a usable heading hierarchy, a meta-description-worthy summary, and descriptive non-generic alt text or `DISPLAY` contracts for images. This check does not apply to internal-tool, dashboard, or authenticated-only screens. Run it whether or not Dynamic Workflow's `seo-copy-verifier` role executed.
- Every visible wireframe region contains either exact UI wording or a display contract covering what to show, the intended takeaway or action, the source, and relevant constraints. Generic placeholders do not pass validation.
- Every visually important wireframe region names its style direction and purpose. Every animated region labels motion as required, optional, or none and states what it communicates.
- ASCII boxes represent real grouping, interaction, state, or hierarchy. Repeated bordered panels with colored side rails or accent stripes are not implied without a named semantic or approved brand role.
- Landing-page wireframes keep one clear value proposition and primary action in the first viewport, give each section one job, and defer secondary detail instead of copying the whole PRD into the page.
- Relevant wireframes label image/media and motion as required, optional, or none with a stated purpose, while leaving visual treatment and detailed choreography to `design-system.md`.
- For a UI-bearing product, `design-system.md` and `design-system.json` are both present. JSON is the sole structured authority; Markdown contains exactly one generated machine-contract block plus human rationale. They are absent only when the user explicitly overrode the requirement and `PRD.md`'s `## Assumptions` records the requester, the reason, and the visual contract implementation uses instead. Refresh the block with `scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --write`, then run `scripts/check_design_system_pair.py --markdown <staged design-system.md> --registry <staged design-system.json> --require-filled` and resolve every reported mismatch or placeholder before publishing.
- Every product component in `design-system.json` carries non-empty `requiredContentOrder`, `composes`, and `states` arrays. The generated Markdown contract preserves their exact values and order.
- `design-system.json` ships exactly one of `viewports` or `sizeClasses`, non-empty and unique, matching the resolved platform. A native or desktop target does not ship web pixel breakpoints.
- `design-system.json` parses as JSON, declares `schema: "design-system/1"`, and its `tokenSources` are specific enough that no unrelated file shares the same path tail.
- Every color pairing in `design-system.md` records a computed contrast ratio from `scripts/check_color_contrast.py`, and every type role records a computed line-height ratio from `scripts/check_type_scale.py`. Estimated or omitted ratios do not pass.
- The design system names a taste statement, at least two signature decisions, and the generic defaults this product avoids. A system with no stated avoided defaults has not run the Anti-Generic Review.
- Every primitive's variant lists are closed sets, and each primitive sits in exactly one of the four layers with no upward dependency.
- `design-system.md`'s primitive inventory covers every control and surface the wireframes' screens actually use. A screen region with no primitive that can express it is an open question, not a silent gap.
- If produced, `implementation-plan.md` includes milestones, dependency order, non-canonical Harness handoff signals, test strategy, release plan, rollback plan, and unresolved decisions. Its test strategy reuses the canonical `TEST-*` IDs from `PRD.md`; it does not replace them with anonymous checks or newly numbered duplicates. Its release plan reuses the stable release target IDs from `architecture.md`.
- The market-research gap pass either produced `market-research.md`, or the package records which reason skipped it — the user declined, no web search or fetch tool was available, the package is a trivial stub, or the role returned blocked. A silently missing pass does not validate.
- When `market-research.md` is present, every factual row cites a source ID resolving to a `## Sources` row with publisher, URL, and retrieval date. Any claim without one is marked `UNVALIDATED` with what was searched. No competitor, price, funding figure, user count, or market size appears without a source.
- When the pass was skipped or blocked, `PRD.md`'s `## Assumptions` records that the market context is unvalidated.
- Findings that changed the package cite their `MR-*` IDs in the sections they changed, and `PRD.md` states conclusions rather than restating the competitor table, sources, or retrieval dates. Findings that would widen product scope are recorded as open questions or recommendations, not applied silently.
- When Dynamic Workflow was used, every required role has an explicit result, failed agents are retained as blocked lanes, and trace/consistency verifier findings are resolved or recorded before finalization. Workflow output is treated as a candidate; the parent still owns staging and publication.

### Publication

- No current-package artifact will be published outside `docs/product/` unless the user explicitly requested another location.
- The superseded-document inventory excludes `docs/product/archived/`, unrelated documents, and ambiguous candidates.
- In enhancement mode, unaffected sections, `PRD-*`, `ARCH-*`, `UI-*`, `UX-*`, `TEST-*`, `MR-*` IDs, and stable release target IDs from the prior package were carried forward unchanged rather than regenerated, and the diff is scoped to what the new discovery actually added, changed, or removed; new TEST IDs cover only obligations that were previously uncovered, and new release target IDs cover only destinations that were previously uncovered.
- Validation does not trigger publication by itself. Exact overwrite and archive moves are already authorized, or the staged package remains unchanged while approval is requested.

<!-- Copy to docs/product/PRD.md when the Delivery profile is program. Replace every [bracket] and <angle> placeholder, delete rows and tables that do not apply, then delete this comment. Module PRDs start from MODULE_PRD.template.md. Add the TEST-MIG rows from PROGRAM_MIGRATION.template.md when legacy data moves. -->
# PRD: [Program Name]

## At a Glance
| | |
| --- | --- |
| What it is | [One line: the program and the business it runs] |
| Primary user | [One line] |
| Why now | [One line] |
| Success looks like | [One metric with its target] |
| Biggest risk | [One line] |
| Delivery profile | program |
| Shape | track: web / app / agent / tool / content; companion: <public surface or none>; console: none / config-only / operations |

[One paragraph describing the program, the modules it joins, and the outcome.]

## Problem Statement
[Current pain, trigger, and why now.]

## Goals
- [Program goal]

## Ambition
### Goal Beyond The Goal
| Rung | Outcome | Outside judge |
| --- | --- | --- |
| 1 | [the program delivered well] | [what proves it, other than us] |
| 2 | [the outcome the program serves] | [...] |
| 3 | [the durable workflow or replaced ritual] | [...] |

### Depth
| Best practitioners | Their instruments | Rawest material | Stretch target | Outside judge |
| --- | --- | --- | --- | --- |
| [...] | [...] | [...] | [...] | [...] |

### Range
Verbs: [the work restated as verbs]

| Field | What they actually do here | Method or tool | Used as |
| --- | --- | --- | --- |
| [field] | [...] | [...] | design input / review lens / go-to-market |

### Access
| Need | Present or missing | Unlocks |
| --- | --- | --- |
| [...] | [...] | [...] |

## Growth Contract
### North Star
| Track | North star | Day 7 target | Day 30 target | Stretch | Source (MS-*) |
| --- | --- | --- | --- | --- | --- |
| [track] | [...] | [...] | [...] | [...] | MS-<NNN> |

### Re-engagement
| Mechanism (email / push / subscription / deep link / return trigger) | Surface or event | TEST ID |
| --- | --- | --- |
| [mechanism or none — reason] | [...] | TEST-PRG-<NNN> |

### Discovery Surfaces
| Surface | Kind (seo-cluster / geo-page / store-listing / directory / landing / social / video_channel / newsletter / community / docs_site) | Owner stage | TEST or MS ID |
| --- | --- | --- | --- |
| [...] | [...] | [delivery / activation / gtm / growth] | TEST-PRG-<NNN> |

### Launch Window
| Day | Channel class (owned / earned / search / store) | Action | Owner | Readback metric | Destination |
| --- | --- | --- | --- | --- | --- |
| [Day 0 to Day 7] | [...] | [...] | [Human owner] | [...] | [path, listing, account or none (reason)] |

## Non-Goals
- [Explicitly out of scope for the program]

## Users and Personas
| Persona | Need | Key Workflow | Success Signal |
| --- | --- | --- | --- |
| [Org-wide persona] | [...] | [...] | [...] |

## Module Map
| Module | Scope | Name | Owns | Depends on | Order | Status |
| --- | --- | --- | --- | --- | --- | --- |
| kernel | KRN | Shared kernel | [Master data the kernel owns, e.g. party, item, currency, calendar] | none | 1 | planned |
| [module-id] | <SCOPE> | [Name] | [Entities and rules it owns] | [kernel and other module-ids] | 2 | planned |

Scope is 2-5 uppercase letters and never a family name (PRD ARCH UI UX TEST DS RA MR MS TRUST AI BR). Order lists dependencies first. Status is planned / approved / released.

## Shared Data
| Entity | Owner module | Readers | Identity key | Change rule |
| --- | --- | --- | --- | --- |
| [Entity] | kernel | [module-ids that depend on the owner] | [key] | [Owner writes; readers keep the key and a read copy] |

## Glossary
| Term | Definition | Owning module | Avoid |
| --- | --- | --- | --- |
| [Term] | [One sentence] | [module-id] | [Words not to use] |

## User Journeys
### Journey 1: [Cross-module journey name]
Role and initial data: [actor, company state, prerequisites]
1. [User action, module, affected data and expected visible result]
2. [Persisted result, permission boundary and observable success]
Failure and recovery: [validation, denial, dependency failure, retry or cancellation]
Trace: [PRD/TEST IDs for this complete journey]

## Functional Requirements
| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| PRD-PRG-001 | [Single sign-on and one user directory across modules] | Must | [Observable acceptance] |
| PRD-PRG-002 | [Role permissions across modules with segregation of duties] | Must | [Observable acceptance] |
| PRD-PRG-003 | [Audit trail for every posting and permission change] | Must | [Observable acceptance] |
| PRD-PRG-004 | [Order-to-cash across the modules in Business Processes] | Must | [Observable acceptance] |
| PRD-PRG-005 | [Procure-to-pay across the modules in Business Processes] | Must | [Observable acceptance] |
| PRD-PRG-006 | [Period close across the ledger and sub-ledger modules] | Must | [Observable acceptance] |

## Non-Functional Requirements
| ID | Quality attribute | Scope / requirement | Measure | Target / threshold | TEST IDs |
| --- | --- | --- | --- | --- | --- |
| PRD-PRG-007 | Performance | [Page and API response at peak concurrent users] | [p95 latency in ms at the Capacity peak] | [Numeric threshold] | TEST-PRG-<NNN> |
| PRD-PRG-008 | Reliability | [Posting throughput at the Capacity transaction volume] | [Postings per second, error rate] | [Numeric threshold] | TEST-PRG-<NNN> |
| PRD-PRG-009 | Scalability | [Storage and query time at the Capacity yearly growth] | [GB and p95 query time after the growth] | [Numeric threshold] | TEST-PRG-<NNN> |
| PRD-PRG-010 | Compliance | [Record retention] | [Years live and years archived] | [Numeric threshold] | TEST-PRG-<NNN> |

## Capacity Assumptions
| Driver | Value | Basis | NFR IDs |
| --- | --- | --- | --- |
| Peak concurrent users | [number] | [Source of the number] | PRD-PRG-007 |
| Transactions per day, all modules | [number] | [Source of the number] | PRD-PRG-008 |
| Data growth per year | [GB] | [Source of the number] | PRD-PRG-009 |
| Retention | [years] | [Owner decision or rule] | PRD-PRG-010 |

## UX Requirements
not_required — the program defines no screens; each module PRD owns its UX Requirements and UI Surface Contract.

## Data and Integration Requirements
- [Shared data objects, external systems, freshness and retention at program level]

## Integrations Register
| External system | Direction and cadence | Idempotency key | Reconciliation report | Error queue owner | Modules | TEST IDs |
| --- | --- | --- | --- | --- | --- | --- |
| [System] | [in / out, schedule] | [key] | [report] | [Human owner] | [module-ids] | TEST-PRG-<NNN> |

## Data and Trust
Data and Trust Gate: [required / not_required / blocked] — [reason], decided by [human owner]

| Area | Decision | Owner / evidence | TEST IDs |
| --- | --- | --- | --- |
| Classification and ownership | [Classes and source of truth] | [Owner/evidence] | TEST-PRG-<NNN> |
| Residency and vendor processing | [Allowed regions, subprocessors, transfer limits] | [Owner/evidence] | TEST-PRG-<NNN> |
| Retention, deletion, and export | [Periods, triggers, legal holds, export and deletion] | [Owner/evidence] | TEST-PRG-<NNN> |
| Consent and policy basis | [Consent, notice, contract, or policy requirement] | [Owner/evidence] | TEST-PRG-<NNN> |
| Human and administrative access | [Roles, approval, masking, audit] | [Owner/evidence] | TEST-PRG-<NNN> |
| Incident and residual risk | [Detection, response owner, accepted residual risk] | [Owner/evidence] | TEST-PRG-<NNN> |

Upstream traces, in row order: `TRUST-CLASSIFICATION`, `TRUST-RESIDENCY`, `TRUST-RETENTION`, `TRUST-CONSENT`, `TRUST-ACCESS`, `TRUST-INCIDENT`.

## Security Requirements
Security Requirements Gate: [required / not_required / blocked] — [reason], decided by [human owner]
Security scope: [executable / documentation_only]

| PRD ID | Asset / trust boundary | Abuse case | Control / safe failure | TEST IDs | Owner | Residual risk |
| --- | --- | --- | --- | --- | --- | --- |
| PRD-PRG-001 | [Asset and boundary crossed] | [Adversary action and forbidden outcome] | [Control, denial/safe failure, and no unauthorized side effects] | TEST-PRG-<NNN> | [Human owner] | [none — reason / accepted — rationale] |
| PRD-PRG-002 | Role assignment boundary | A user holds both duties of a Segregation of Duties pair | Reject the assignment and write nothing | TEST-PRG-002 | [Human owner] | [none — reason / accepted — rationale] |

## Permission Matrix
### Roles
| Role | Description | Scope |
| --- | --- | --- |
| [role-id] | [What the role does] | [Company, entity or whole program] |

### Segregation of Duties
| Duty A | Duty B | Rule | TEST ID |
| --- | --- | --- | --- |
| <module-id>:<verb> | <module-id>:<verb> | No role holds both | TEST-PRG-002 |

## AI and Automation
AI and Automation Gate: [required / not_required / blocked] — [reason], decided by [human owner]

| Area | Decision | Owner / evidence | TEST IDs |
| --- | --- | --- | --- |
| Capability and provider boundary | [...] | [Owner/evidence] | TEST-PRG-<NNN> |
| Input, context, and retention | [...] | [Owner/evidence] | TEST-PRG-<NNN> |
| Tool and side-effect permissions | [...] | [Owner/evidence] | TEST-PRG-<NNN> |
| Evaluation and prohibited outcomes | [...] | [Owner/evidence] | TEST-PRG-<NNN> |
| Cost, latency, and observability | [...] | [Owner/evidence] | TEST-PRG-<NNN> |
| Fallback, shutoff, and incident path | [...] | [Owner/evidence] | TEST-PRG-<NNN> |
| Injection and output validation | [...] | [Owner/evidence] | TEST-PRG-<NNN> |

Upstream traces, in row order: `AI-CAPABILITY`, `AI-CONTEXT`, `AI-SIDE-EFFECTS`, `AI-EVALUATION`, `AI-OPERATIONS`, `AI-FALLBACK`, `AI-VALIDATION`. A required gate also needs the `eval-policy/1` block from `eval-policy-contract.md`.

## Business Rules
| ID | Trigger | Condition | Outcome | Exceptions | Owner | TEST IDs |
| --- | --- | --- | --- | --- | --- | --- |
| BR-PRG-001 | [Event that fires the rule] | [Condition] | [Outcome] | [Exceptions or none] | [Human owner] | TEST-PRG-<NNN> |

## Business Processes
| Process | Modules in order | TEST IDs |
| --- | --- | --- |
| order-to-cash | [module-ids in process order] | TEST-E2E-001 |
| procure-to-pay | [module-ids in process order] | TEST-E2E-002 |
| period-close | [module-ids in process order] | TEST-E2E-003 |

Fixture PF-BASE: [one company, a 12-month calendar, parties, items, warehouses, opening balances]. Its ID, sha256, fixed clock and golden outputs are recorded in architecture.md. Each run restores it into an empty database and tears it down.

## Monetization and Partner Channels
| Decision | Selection | Product rationale / evidence | Status | Trace IDs |
| --- | --- | --- | --- | --- |
| Monetization model | [none / one_time / subscription / usage_based / hybrid / undecided] | [Who pays and for what] | [selected / approved / recommended / provisional / assumed] | [PRD-* / MR-* / RA-*] |
| Monetization Infrastructure Gate | [required / not_required / blocked] | [Reason] | [status] | [PRD-* / ARCH-* / TEST-*] |
| Pricing and offer | [...] | [...] | [status] | [...] |
| Purchase and entitlement | [...] | [...] | [status] | [...] |
| Merchant of record / tax owner | [...] | [...] | [status] | [...] |
| Partner Channel Gate | [required / not_required / blocked] | [Reason] | [status] | [PRD-* / ARCH-* / TEST-*] |
| Partner motion | [none / affiliate / referral / reseller / hybrid / undecided] | [...] | [status] | [...] |
| Partner economics and operations | [...] | [...] | [status] | [...] |

## Metrics
| Metric | Definition | Baseline | Target / guardrail | Stretch | Measurement window | Source / method | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [North-star metric] | [Definition] | [Baseline] | [Target] | [Stretch] | [N days] | [Source] | [Human owner] |

## Risks
| Risk | Impact | Mitigation |
| --- | --- | --- |
| [Risk] | [Impact] | [Mitigation] |

## Assumptions
| Assumption | Impact if wrong | Validation | Owner | Decision date | Status |
| --- | --- | --- | --- | --- | --- |
| [Assumption] | [Impact] | [Evidence or experiment] | [Owner] | [YYYY-MM-DD] | [open / accepted / validated / rejected] |

## Open Questions
| Question | Why it matters | Owner | Decision deadline | Blocks approval | Status / resolution |
| --- | --- | --- | --- | --- | --- |
| [Question] | [Decision or requirement affected] | [Owner] | [YYYY-MM-DD] | [Yes / No] | [Open / resolved — answer] |

## Test Obligations
| TEST ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |
| --- | --- | --- | --- | --- | --- |
| TEST-PRG-001 | [Observable behavior or quality obligation] | [Unit / integration / contract / E2E / performance / security / accessibility / operational] | Yes | PRD-PRG-001 | [Literal pass signal, measured result, or threshold] |
| TEST-PRG-002 | Reject a role assignment that gives one role both duties of a Segregation of Duties pair | security | Yes | PRD-PRG-002 | denial: rejected ([observable rejection signal]); no unauthorized side effects: unchanged ([observable state evidence]) |
| TEST-E2E-001 | Order-to-cash on fixture PF-BASE: [quote, order, ship, invoice, receipt, GL post] | E2E | Yes | PRD-PRG-004, PRD-<SCOPE>-<NNN> | [AR sub-ledger, stock value and trial balance equal expected/o2c.json to the cent; every document reaches its terminal state] |
| TEST-E2E-002 | Procure-to-pay on fixture PF-BASE: [requisition, PO, receipt, three-way match, payment] | E2E | Yes | PRD-PRG-005, PRD-<SCOPE>-<NNN> | [AP sub-ledger equals the GL control account; the mismatched invoice is held and not paid] |
| TEST-E2E-003 | Period close on fixture PF-BASE after TEST-E2E-001 and TEST-E2E-002 | E2E | Yes | PRD-PRG-006, PRD-<SCOPE>-<NNN> | Close succeeds only when sub-ledgers reconcile; a posting into the closed period is rejected with zero rows written; reopening needs role `controller` and is audited |

---

## UI Design Handoff Status

UI design: not_required — the program defines no screens; module PRDs hand off their own UI design.

UI decision owner: n/a for headless

## Product Definition Decisions

### Research Gate

Research Gate: [go / clarify / stop / skipped] — [assessment date and findings path, or skip reason], decided by [human owner]

<!-- product-definition-approval:start -->
### Product Definition Approval
- Package mode: [new / enhancement]
- Package revision: [PD-R<integer>@sha256:<package digest>]
- Package digest: [sha256:<64 lowercase hex> over the raw PRD/architecture/stack text; only this approval block is excluded]
- Decision: [approved / revision_requested / blocked]
- Decision owner: [Human product owner]
- Decided on: [YYYY-MM-DD]
- Approved artifacts: PRD.md, architecture.md, stack-decisions.md
- Market research reconciliation: [completed / skipped — reason / blocked — reason]
- Stack Decision Checkpoint: [approved / revision_requested / blocked]
- Accepted assumptions and non-blocking questions: [None / exact rows accepted for this revision]
- Blocking items: [None / exact unresolved decisions]
<!-- product-definition-approval:end -->

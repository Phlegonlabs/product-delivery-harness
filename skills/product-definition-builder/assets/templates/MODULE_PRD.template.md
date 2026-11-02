<!-- Copy to docs/product/modules/<module-id>/PRD.md for each module in the program Module Map. The module id is the directory name and the scope is its Module Map row; the PRD repeats neither. Replace <SCOPE> with that scope in every ID, replace every other [bracket] and <angle> placeholder, delete rows that do not apply, then delete this comment. The Program revision line is the program PRD's `program_prd_digest` (canonical bytes, approval block excluded); the checker prints it as a warning when it goes stale. The gate lines restate the program PRD values and may not relax them. Cite another module's IDs only when that module is in this module's Depends on. -->
# PRD: [Module Name]

## At a Glance
| | |
| --- | --- |
| What it is | [One line: what this module does inside the program] |
| Primary user | [One line] |
| Why now | [One line] |
| Success looks like | [One metric with its target] |
| Biggest risk | [One line] |

Program revision: sha256:<64 lowercase hex>

[One paragraph describing the module, the entities it owns, and the outcome.]

## Problem Statement
[Current pain this module removes and why now.]

## Goals
- [Module goal]

## Non-Goals
- [Explicitly out of scope for this module]

## Users and Personas
| Persona | Need | Key Workflow | Success Signal |
| --- | --- | --- | --- |
| [Program persona this module serves] | [Need in this module] | [...] | [...] |

## User Journeys
### Journey 1: [Name]
Role and initial data: [actor, company state, prerequisites]
1. [User action, affected data and expected visible result]
2. [Persisted result, permission boundary and observable success]
Failure and recovery: [validation, denial, dependency failure, retry or cancellation]
Trace: [PRD/UI/TEST IDs for this complete journey]

## Functional Requirements
| ID | Requirement | Priority | Acceptance Criteria |
| --- | --- | --- | --- |
| PRD-<SCOPE>-001 | [Requirement] | [Must / should / could] | [Observable acceptance] |

## Non-Functional Requirements
| ID | Quality attribute | Scope / requirement | Measure | Target / threshold | TEST IDs |
| --- | --- | --- | --- | --- | --- |
| PRD-<SCOPE>-002 | [Quality attribute] | [Surface, workflow, population and condition covered] | [Measured signal with unit, window and percentile] | [Numeric threshold] | TEST-<SCOPE>-002 |

## UX Requirements
| ID | User / task | Requirement | Success and failure signal | Evidence status |
| --- | --- | --- | --- | --- |
| UX-<SCOPE>-001 | [User completing a critical task] | [Screens, states, accessibility, notifications, or recovery] | [Observable success plus failure signal] | [research-backed / prototype-reviewed / assumption] |

<!-- ui-surface-contract:start -->
## UI Surface Contract

### UI-<SCOPE>-001 — [Surface name]

- `route`: [One literal route value, or `n/a — <reason>`]
- `releaseSurface`: [A surface ID in the module architecture's `Program release surfaces`]
- `surfaceClass`: [Exact Release Target surface class, such as `hosted_web`]
- `captureMode`: [hosted-browser / browser-extension / native / desktop, derived from `surfaceClass`]
- Main purpose: [One primary user goal]
- Content responsibilities: [Required information and controls; exact copy or bounded display contract for each]
- Actions and transitions: [Primary, secondary, destructive, navigation, success, and failure paths]
- `operations`: [JSON list of operation objects, or `none — <concrete reason of at least 12 characters>`]
- `states`: [Comma-separated state IDs; `<state>:n/a — <reason>` for an inapplicable state]
- `responsive`: [`viewports: 390, 768, 1024, 1440` or ordered `sizeClasses`]
- `copy`: [draft / approved / revision_requested / blocked] — [copy responsibility]
- Responsive obligations: [Content and actions that never drop; long-content and overlay behavior]
- Accessibility: [Focus, labels, announcements, heading order, and alt text]
- SEO metadata: [`<title>`, meta description, canonical URL, or `n/a — <reason>`]
- Trace IDs: [PRD-<SCOPE>-*, UX-<SCOPE>-*, ARCH-<SCOPE>-*, TEST-<SCOPE>-*]

<!-- ui-surface-contract:end -->

## Data and Integration Requirements
- [Entities this module owns, which program Shared Data it reads, and the external systems it uses from the Integrations Register]

## Data and Trust
Data and Trust Gate: [value equal to the program PRD] — [reason], decided by [human owner]

| Area | Decision | Owner / evidence | TEST IDs |
| --- | --- | --- | --- |
| Classification and ownership | [Module decision, or the program decision applies unchanged] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |
| Residency and vendor processing | [...] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |
| Retention, deletion, and export | [...] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |
| Consent and policy basis | [...] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |
| Human and administrative access | [...] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |
| Incident and residual risk | [...] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |

Upstream traces, in row order: `TRUST-CLASSIFICATION`, `TRUST-RESIDENCY`, `TRUST-RETENTION`, `TRUST-CONSENT`, `TRUST-ACCESS`, `TRUST-INCIDENT`.

## Security Requirements
Security Requirements Gate: [value equal to the program PRD] — [reason], decided by [human owner]
Security scope: [executable / documentation_only]

| PRD ID | Asset / trust boundary | Abuse case | Control / safe failure | TEST IDs | Owner | Residual risk |
| --- | --- | --- | --- | --- | --- | --- |
| PRD-<SCOPE>-001 | [Asset and boundary crossed] | [Adversary action and forbidden outcome] | [Control, denial/safe failure, and no unauthorized side effects] | TEST-<SCOPE>-<NNN> | [Human owner] | [none — reason / accepted — rationale] |

## AI and Automation
AI and Automation Gate: [value equal to the program PRD] — [reason], decided by [human owner]

| Area | Decision | Owner / evidence | TEST IDs |
| --- | --- | --- | --- |
| Capability and provider boundary | [Module decision, or the program decision applies unchanged] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |
| Input, context, and retention | [...] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |
| Tool and side-effect permissions | [...] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |
| Evaluation and prohibited outcomes | [...] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |
| Cost, latency, and observability | [...] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |
| Fallback, shutoff, and incident path | [...] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |
| Injection and output validation | [...] | [Owner/evidence] | TEST-<SCOPE>-<NNN> |

Upstream traces, in row order: `AI-CAPABILITY`, `AI-CONTEXT`, `AI-SIDE-EFFECTS`, `AI-EVALUATION`, `AI-OPERATIONS`, `AI-FALLBACK`, `AI-VALIDATION`.

## Business Rules
| ID | Trigger | Condition | Outcome | Exceptions | Owner | TEST IDs |
| --- | --- | --- | --- | --- | --- | --- |
| BR-<SCOPE>-001 | [Event that fires the rule] | [Condition] | [Outcome] | [Exceptions or none] | [Human owner] | TEST-<SCOPE>-<NNN> |

### Document States
Document: [Document name]. Terminal states: [states].
| From | To | Action | Who may trigger | Side effects | Guard |
| --- | --- | --- | --- | --- | --- |
| [state] | [state] | [action] | [role-id] | [Side effects] | BR-<SCOPE>-<NNN> |

## Permission Matrix
| Role | Action | Data scope | Condition |
| --- | --- | --- | --- |
| [role-id from the program Roles] | <module-id>:<verb> | [Data scope] | [Condition, e.g. an amount limit from BR-<SCOPE>-<NNN>] |

## Reports
| PRD ID | Report | Audience | Filters | Source entities | Freshness | Export |
| --- | --- | --- | --- | --- | --- | --- |
| PRD-<SCOPE>-<NNN> | [Report name] | [Role] | [Filters] | [Entities] | [Live / daily / on close] | [CSV / PDF / none] |

## Monetization and Partner Channels
| Decision | Selection | Product rationale / evidence | Status | Trace IDs |
| --- | --- | --- | --- | --- |
| Monetization model | [program value] | [Reason] | [status] | [PRD-* / MR-* / RA-*] |
| Monetization Infrastructure Gate | [program value] | [Reason] | [status] | [PRD-* / ARCH-* / TEST-*] |
| Pricing and offer | [program value] | [...] | [status] | [...] |
| Purchase and entitlement | [program value] | [...] | [status] | [...] |
| Merchant of record / tax owner | [program value] | [...] | [status] | [...] |
| Partner Channel Gate | [program value] | [Reason] | [status] | [PRD-* / ARCH-* / TEST-*] |
| Partner motion | [program value] | [...] | [status] | [...] |
| Partner economics and operations | [program value] | [...] | [status] | [...] |

## Metrics
| Metric | Definition | Baseline | Target / guardrail | Measurement window | Source / method | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| [Module metric] | [Definition] | [Baseline] | [Target] | [N days] | [Source] | [Human owner] |

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
| TEST-<SCOPE>-001 | [Observable behavior or quality obligation] | [Unit / integration / contract / E2E / performance / security / accessibility / operational] | Yes | PRD-<SCOPE>-001 | [Literal pass signal, measured result, or threshold] |
| TEST-<SCOPE>-002 | [Observable obligation that proves PRD-<SCOPE>-002] | [Performance / reliability / operational] | Yes | PRD-<SCOPE>-002 | [Measured result against the NFR threshold] |

---

## UI Design Handoff Status

UI design: [pending explicit ui-design-builder request / not_required — headless reason]

UI decision owner: [Human owner / n/a for headless]

## Product Definition Decisions

<!-- product-definition-approval:start -->
### Product Definition Approval
- Package mode: [new / enhancement]
- Package revision: [PD-R<integer>@sha256:<package digest>]
- Package digest: [sha256:<64 lowercase hex> over the raw module PRD and module architecture text; only this approval block is excluded]
- Decision: [approved / revision_requested / blocked]
- Decision owner: [Human product owner]
- Decided on: [YYYY-MM-DD]
- Approved artifacts: PRD.md, architecture.md, stack-decisions.md
- Market research reconciliation: [completed / skipped — reason / blocked — reason]
- Stack Decision Checkpoint: [approved / revision_requested / blocked]
- Accepted assumptions and non-blocking questions: [None / exact rows accepted for this revision]
- Blocking items: [None / exact unresolved decisions]
<!-- product-definition-approval:end -->

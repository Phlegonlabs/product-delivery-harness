# Harness Plan: <feature or product slice>

## Source Map

| Source | Path / URL | Owner | Status | Notes |
|---|---|---|---|---|
| PRD | <path> | <owner> | draft / frozen | <summary> |
| Updated PRD | <path> | <owner> | draft / accepted / n/a | <delta summary> |
| Wireframe | <path or URL> | <owner> | draft / frozen | <screens> |
| Updated wireframe | <path or URL> | <owner> | draft / accepted / n/a | <affected screens> |
| Design system | <path or URL> | <owner> | draft / frozen | <tokens/components> |
| Updated design system | <path or URL> | <owner> | draft / accepted / n/a | <affected tokens/components> |
| Page UI references | <path or URL> | <owner> | draft / accepted / n/a | <pages/components> |
| Architecture | <path> | <owner> | draft / frozen | <contracts> |
| Content / CMS | <path or URL> | <owner> | draft / frozen / n/a | <collections/pages> |
| Analytics / release | <path or URL> | <owner> | draft / frozen / n/a | <events/deploy target> |

## Objective

<One measurable outcome.>

## Product Archetype

```text
Archetype:
Audience:
Traffic or workflow objective:
Critical surfaces:
Existing app state:
Refinement lenses:
Input change type:
Release target:
```

## Scope

### Must Have

- `<TRACE-ID>` <requirement>

### Non-Goals

- <explicitly out of scope>

## Contract Freeze

| Surface | Contract path / section | Status | Freeze decision |
|---|---|---|---|
| Product | <path> | draft / frozen | <decision> |
| Architecture / data / API | <path> | draft / frozen | <decision> |
| UI flow / wireframe | <path> | draft / frozen | <decision> |
| Design system | <path> | draft / frozen | <decision> |
| Verification | <path> | draft / frozen | <decision> |
| Input delta | <path or section> | draft / accepted / n/a | <decision> |
| Page UI matrix | <path or section> | draft / accepted / n/a | <decision> |
| Identity / access | <path or section> | draft / frozen / n/a | <decision> |
| Tenant / data isolation | <path or section> | draft / frozen / n/a | <decision> |
| Billing / entitlements | <path or section> | draft / frozen / n/a | <decision> |
| Content / CMS / SEO | <path or section> | draft / frozen / n/a | <decision> |
| Analytics / conversion | <path or section> | draft / frozen / n/a | <decision> |
| Catalog / commerce | <path or section> | draft / frozen / n/a | <decision> |

## Platform Contract

### Identity And Access

<auth/session/roles/admin or n/a>

### Tenant / Organization Model

<tenant boundaries, data ownership, isolation evidence or n/a>

### Billing / Entitlements

<plans, limits, subscription states, feature gates or n/a>

### Public Site / Content / SEO

<page inventory, URL/slugs, CMS/source, metadata, sitemap, robots, redirects or n/a>

### Analytics / Conversion

<events, forms, pixels, consent, UTM, CRM/webhook evidence or n/a>

### Catalog / Commerce

<products, variants, pricing, inventory, search/filter, checkout boundary or n/a>

## Traceability Matrix

| Trace ID | Source | Requirement | Implementation owner | Verification |
|---|---|---|---|---|
| PRD-001 | PRD | <requirement> | Mission <n> | TEST-001 |

## Input Delta Matrix

| Delta ID | Source | Change | Affected surfaces | Supersedes | Acceptance / verifier | Status |
|---|---|---|---|---|---|---|
| DELTA-001 | updated PRD / wireframe / design system / page UI | <change> | <trace IDs> | <old requirement or n/a> | <gate> | proposed / accepted / blocked |

## Page UI Matrix

| Page / route | UI source | Breakpoints | States | Components | Data source | Acceptance evidence |
|---|---|---|---|---|---|---|
| <route> | <source> | <breakpoints> | <states> | <components> | <API/data> | <screenshot/trace/test> |

## Existing App Baseline

| Lens | Baseline evidence | Current result | Target / threshold | Status |
|---|---|---|---|---|
| <UX/perf/a11y/etc> | <cmd/screenshot/trace/path> | <result> | <target> | captured / missing / n/a |

## Refinement Backlog

| ID | Lens | Finding | Evidence | Impact | Effort | Risk | Proposed verifier | Status |
|---|---|---|---|---|---|---|---|---|
| REF-001 | <lens> | <finding> | <metric/path> | high / med / low | S / M / L | low / med / high | <cmd/threshold> | proposed |

## Mission Map

| Mission | Objective | Depends on | Write scope | Verifier | Status |
|---|---|---|---|---|---|
| M1 | <foundation> | none | <paths> | <command> | planned |

## Worktree And Thread Plan

Applies to worktree modes only. In the default single-checkout mode, write `N/A - single-checkout` here and skip the table.

| Mission | Worktree | Branch | Port / DB | Runner | Merge order |
|---|---|---|---|---|---|
| M1 | <path> | <branch> | <port/schema> | parent / worker | 1 |

## Launch Preflight

Required before launching any worktree mode. In the default single-checkout mode, write `N/A - single-checkout` here and skip the table.

| Check | Result | Evidence / note |
|---|---|---|
| Base branch | <branch> | |
| Parent git status | clean / dirty | |
| Existing worktrees | <list> | |
| Branch/worktree conflicts | none / <details> | |
| Dependency DAG/toposort | pass / fail | |
| Resource isolation | pass / fail | |
| .worktreeinclude needed | yes / no | |

## Stop / Ask Conditions

- <condition>

## Open Risks

| Risk | Impact | Mitigation | Owner |
|---|---|---|---|
| <risk> | <impact> | <mitigation> | <owner> |

# Optional Expanded E2E Verification: <feature or product slice>

Keep verification in `RUN.md` by default. Use this standalone expansion only when the verification matrix becomes materially difficult to scan or needs separate ownership. Link it from `RUN.md` instead of duplicating rows.

## Verification Summary

| Gate | Required | Status | Evidence | Notes |
|---|---|---|---|---|
| Build | yes / no | planned | | |
| Lint / format | yes / no | planned | | |
| Typecheck | yes / no | planned | | |
| Unit tests | yes / no | planned | | |
| API / integration | yes / no | planned | | |
| DB migration / seed / reset | yes / no | planned | | |
| Permissions | yes / no | planned | | |
| Auth lifecycle | yes / no | planned | | |
| Tenant isolation | yes / no | planned | | |
| Billing / entitlements | yes / no | planned | | |
| Audit / observability | yes / no | planned | | |
| Browser journey | yes / no | planned | | |
| Builder UX Direction conformance | yes / no | planned | | |
| Usability / task success | yes / no | planned | | |
| Responsive | yes / no | planned | | |
| Console / network | yes / no | planned | | |
| Accessibility | yes / no | planned | | |
| Visual design comparison | yes / no | planned | | |
| Design input delta conformance | yes / no | planned | | |
| Before/after refinement evidence | yes / no | planned | | |
| SEO metadata / crawlability | yes / no | planned | | |
| CMS/content readback | yes / no | planned | | |
| Analytics / conversion | yes / no | planned | | |
| Catalog / ecommerce | yes / no | planned | | |
| Performance | yes / no | planned | | |
| Automated E2E | yes / no | planned | | |

## Automated E2E Contract

| Field | Value |
|---|---|
| Command | `<e2e-command>` |
| CI check name | `<e2e-check-name>` |
| Environment | `<local / preview / staging / deployed>` |
| Covered journeys | `<journey IDs>` |
| Expected pass signal | `<exit code / assertion>` |
| Bound commit SHA | `<hash>` |
| Retained evidence | `<artifact / trace / CI log>` |
| Manual smoke disposition | `required / not required - covered by current-head E2E` |
| Disposition reason | `<coverage match or uncovered risk>` |

A current-head E2E PASS may replace only a duplicate manual smoke for the same journey and equivalent environment. Keep external-integration, visual, or other materially different smoke checks required until they have their own proof.

## Primary Journey

```text
User:
Preconditions:
Steps:
Expected result:
Data created / modified:
Cleanup:
```

## UX Direction And Usability Evidence

Builder approval proves direction conformance only. Use `UNVALIDATED` when only builder/agent review, screenshots, heuristic review, or automated E2E exists and the plan requires representative-user usability evidence.

| UX trace | Critical task / scenario | Direction owner and status | Method | Representative participant / source | Target | Actual result | Redacted evidence | Bound version / SHA | Status |
|---|---|---|---|---|---|---|---|---|---|
| UX-001 | <task and context> | <owner; selected/provisional/assumed> | <prototype review / likely-user test / benchmark / other> | <segment or approved source> | <success/failure signal> | <result> | <path/report/decision> | <version or SHA> | planned |

## Archetype Scenarios

| Scenario | Required when | Steps / assertion | Status | Evidence |
|---|---|---|---|---|
| Wrong-role denied | roles/permissions exist | <steps> | planned | |
| Cross-tenant denied | tenant model exists | <steps> | planned | |
| Billing entitlement blocked | billing/feature gates exist | <steps> | planned | |
| SEO metadata check | public pages exist | <steps> | planned | |
| Conversion event/form | CTA/forms/tracking exist | <steps> | planned | |
| Catalog listing/detail | catalog exists | <steps> | planned | |

## Evidence Register

| Trace | Command / action | Expected pass signal | Actual result | Exit code | Artifact path | Commit hash | Status |
|---|---|---|---|---|---|---|---|
| TEST-001 | <cmd/action> | <pass signal> | <result> | <code> | <path> | <hash> | planned |

## Before / After Evidence

| Refinement ID | Before evidence | After evidence | Expected improvement | Actual result | Status |
|---|---|---|---|---|---|
| REF-001 | <path/metric> | <path/metric> | <target> | <result> | planned |

## Design Input Conformance

| Delta / page | Source | Expected conformance | Evidence | Status |
|---|---|---|---|---|
| DELTA-001 | <PRD/wireframe/design/page UI source> | <expected result> | <test/screenshot/trace> | planned |

## Skipped Checks

| Gate | Reason skipped | Risk | Accepted by |
|---|---|---|---|
| <gate> | <reason> | <risk> | <name/date or pending> |

## Unvalidated Surfaces

| Surface | Why unvalidated | Risk | Accepted by |
|---|---|---|---|
| <surface> | <reason> | <risk> | <name/date or pending> |

# E2E Verification: <feature or product slice>

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
| Deployment smoke | yes / no | planned | | |
| Release impact | yes / no | planned | | |

## Primary Journey

```text
User:
Preconditions:
Steps:
Expected result:
Data created / modified:
Cleanup:
```

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

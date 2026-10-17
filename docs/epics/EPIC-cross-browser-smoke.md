# Cross-Browser Smoke Verification

Status: in_progress

## Problem And Baseline

At `bf56ab27` (0.64.0), every harness browser check uses Playwright Chromium. Consumer PRDs list Firefox and Safari as supported browsers. Examples: hardwareprices, agentkiosk and jolvex-platform. Nothing verifies those browsers. Recorded evidence says so: "Firefox/WebKit are not installed" in ticketradar, and "Safari, Firefox not checked" in agentic-commons-site.

## Accepted Outcome

Consumer projects verify the browsers their PRD names. The owner chose the complete design over a lighter rule-based one. The design source is the GPT-6 Astra plan of 2026-10-17 (run `20261017-114314-9b00fd00`), adjusted so the consumer `verify` check uses the same draft and ready split as source CI.

## Requirements

| ID | Outcome |
| --- | --- |
| CB-01 | The PRD records browser targets in a `browser-targets/1` table under Frontend Delivery Requirements. A package without the table keeps Chromium-only behavior and gains no new obligation. A malformed declaration fails; it never falls back. |
| CB-02 | Chrome and Edge map to `chromium`, Firefox to `firefox`, and Safari on macOS or iOS to `webkit`. Evidence labels `webkit` as an approximation of Safari, not Safari itself. |
| CB-03 | The seeded consumer CI runs the product smoke tests once per mapped engine, only on ready pull requests, default-branch pushes, merge queue and manual runs. Draft runs skip them and report `verify-draft`; complete runs report the required `verify`. |
| CB-04 | Delivery acceptance `delivery-acceptance/2` and `delivery-results/2` carry a browser identity on web scenarios. When the PRD maps a target to Firefox or WebKit, every release target, smoke test and engine combination needs a frozen scenario and a passing result. The `/1` records stay valid only without such targets. |
| CB-05 | The package checker joins browser rows to hosted web release targets and required PRD TEST IDs. |
| CB-06 | The four READMEs and the owning references describe the behavior. Everyday harness evidence stays Chromium. |

## Document Impact

| Source | Affected artifact |
| --- | --- |
| `skills/product-definition-builder/scripts/browser_targets.py` | New shared parser and engine CLI, also seeded into consumer `.github/scripts/` |
| `skills/product-definition-builder/references/output-contract.md`, `interview-guide.md` | PRD Browser Targets section and owner question |
| `skills/product-definition-builder/scripts/check_product_package.py` | Package join |
| `skills/delivery-harness/scripts/check_delivery_acceptance.py` and its helpers | `/2` schemas and browser coverage |
| `skills/delivery-harness/assets/templates/PROJECT_CI.template.yml` | Engine matrix and draft and ready split |
| `skills/delivery-harness/references/` acceptance, verification, deployment and testing pages | Owning rules |
| Four READMEs | Verification section |

## Change Log

| Change | Commit | Verification |
| --- | --- | --- |

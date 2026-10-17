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
| PRD browser target parser and CLI (CB-01, CB-02) | `a6c2b5cf` | Parser tests pass, including a run from a copy of only the two scripts. |
| PRD template section and owner question (CB-01, CB-06) | `b7b3c442` | Product Definition skill contract passes. |
| Delivery acceptance version 2 with browser identity (CB-04) | `f3e38110` | Nine new version 2 cases pass. |
| Package check joins targets and tests (CB-05) | `1d3f6bb9` | Seven new package checker cases pass. |
| Consumer CI engine matrix with the draft and ready split (CB-03) | `13a37953` | Template tests pass. The six verify gate cases and the resolver passed through local Git Bash. |
| PRD-derived browser coverage in delivery acceptance (CB-04) | `dee439ee` | Six coverage cases pass. |
| References and four READMEs (CB-06) | `cec9ac25` | Reference library, skill contract and README structure tests pass. |
| Integration exercise | — | A fixture PRD with Chrome, Edge, Firefox and iOS Safari resolved to chromium, firefox and webkit. Playwright 1.62.1 then launched Chromium 151, Firefox 153 and WebKit 26.5 on Windows, each rendering the smoke page. |
| Review fixes: strict table parsing, type-safe schemas, `verify-detached`, subsection wording | `15f8ebe5`, `75df1464`, `ee5dc3d3`, `3353ebbe` | GPT-6.1 Sol reviews of both halves returned FIX_REQUIRED. One finding was high in each half, plus medium findings. All are fixed, with new tests. The detached-check gap also exists in source CI and is tracked for a separate change. |
| Version 0.64.3 | `448f8738` | Skill contract and README structure tests pass. |

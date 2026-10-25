# PRD Delta <EPIC-ID>: <outcome in one line>

Schema: prd-delta/1. Publish at `docs/product/deltas/PRD-DELTA-<EPIC-ID>.md`, where `<EPIC-ID>` is the Epic file's id token, for example `EPIC-041` for `docs/epics/EPIC-041-<slug>.md`. One delta per enhancement round, aligned one-to-one with that round's Epic. A hash is the SHA-256 of the file text without the `product-definition-approval` marker block, exactly as `bilingual-review.md` defines the review-source hash. Keep the headings, table headers, field labels, and the marker pair in English; they are machine anchors. The Traditional Chinese review copy `PRD-DELTA-<EPIC-ID>.zh-TW.md` uses the same marker rule and is translated in full.

| | |
| --- | --- |
| Epic | docs/epics/EPIC-<id>-<slug>.md |
| Baseline PRD | sha256:<64 lowercase hex of PRD.md before this delta> |
| Result PRD | sha256:<64 lowercase hex after publication> or pending |
| Status | draft / approved |
| Ambition rung | 1 / 2 / 3 — <one line naming the rung from the PRD Ambition ladder> |

## Why

[Owner request, date and source; the goal beyond the goal this round serves.]

## Enhancement Impact Record

Reuse the table from `output-contract.md` `## PRD.md` with unchanged columns. Record it here, never in `PRD.md`.

| Area | Impact | Affected IDs / decisions | Required refresh |
| --- | --- | --- | --- |
| Product scope / behavior | [unchanged / changed] | [IDs or none] | [Artifacts and gates or none] |
| UI structure / style | [none / structure / style / both] | [UI/UX IDs or none] | [HiFi/UI Design gates or retained legacy gates or none] |
| Data / integrations | [unchanged / changed] | [IDs or none] | [Artifacts and gates or none] |
| Architecture / stack | [unchanged / changed] | [ARCH IDs/layers or none] | [Stack checkpoint and artifacts or none] |
| Data trust / AI | [unchanged / changed] | [Gate/IDs or none] | [Artifacts and gates or none] |
| Security | [unchanged / changed] | [Gate/IDs or none] | [Artifacts and gates or none] |
| Monetization / partner | [unchanged / changed] | [Gate/IDs or none] | [Artifacts and gates or none] |
| Release / operations | [unchanged / changed] | [Targets or none] | [Artifacts and gates or none] |

## Changed Requirements

| ID | Change | Before | After | TEST IDs |
| --- | --- | --- | --- | --- |
| PRD-0xx | new / revised / retired | [summary or n/a] | [summary] | TEST-0xx |

## Decisions

- decision:<slug> — [one line]

## Approval

<!-- product-definition-approval:start -->
### Product Definition Approval — Delta
- Decision owner: [Human product owner]
- Decided on: [YYYY-MM-DD]
- Result PRD: sha256:<64 lowercase hex after publication> or pending
- Decision: [approved / revision_requested / blocked]
- Blocking items: [None / exact unresolved decisions]
<!-- product-definition-approval:end -->

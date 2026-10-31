# Launch Runbook

Bind each PRD Launch Window row to checks before and after its day.
The runbook is a proposal. It publishes nothing and schedules nothing.

## Inputs

Read each input as it exists at the checkpoint time; a stale input is a gap to record.

- The `### Launch Window` rows from the PRD Growth Contract: Day, Channel class, Action, Owner, Readback metric, Destination.
- The messaging record at `docs/gtm/MESSAGING.md`, when present.
- `docs/DEPLOYMENT.md` Release Target Status and Measurement Sources, with each `MS-*` row's status.
- The campaign review package from go-to-market, with approved items and their destinations.

## Checkpoints

Run each checkpoint against every Launch Window row in its range. Record each check in the Record table.

### T-14

- List every row with no owner, no real destination or no readback metric; route each gap to its owner.
- Confirm each destination route exists in the PRD; route a missing route to product-definition-builder.
- Confirm the messaging record covers each row's channel class; name the missing copy.
- List the `MS-*` rows the readbacks need; record missing sources as gaps for delivery-harness.

### T-7

- Confirm each destination resolves and shows the intended pre-launch state.
- Confirm tracking identifiers exist in the measurement plan; use only existing identifiers.
- List assets and alt text per row; mark missing media as missing.
- Confirm store listing contracts and screenshot sets where a row needs them.
- Confirm the reply or moderation owner per row; record unowned rows as gaps.

### T-1

- Confirm each destination resolves and shows approved copy and assets.
- Confirm each needed `MS-*` row is `verified`, or record the gap.
- Confirm the rollback action and owner for a broken destination.
- Confirm the reply owner's duty window with dates and timezone.
- Record each row's readback metric with its exact source path.

### T0

- Confirm the destination resolves and shows the released build or listing before any copy goes out.
- Confirm tracking identifiers reach the destination exactly as planned.
- Publish only through the authorized publisher; record post IDs and URLs in the campaign package.
- Confirm the reply owner covers the posting window.
- Read the row's metric source once and record the baseline, or record it as unavailable.

### T+1

- Resolve each destination again. A broken destination triggers its rollback; do not retry without a diagnosis.
- Read back each row's metric; record value, source, range and timezone, or the gap.
- Confirm the reply owner answered or routed the replies received so far.

### T+7

- Read back each Day 7 metric; record value, source and window, or the gap.
- Hand the results to growth-review's `growth_review` mode.

### T+30

- Read back each Day 30 metric the same way.
- Hand the results to growth-review's `growth_review` mode again.

## Readback Handoff

Day 7 and Day 30 readbacks go to growth-review's `growth_review` mode, per its Growth Review Cadence section in `growth-review/references/review-method.md` (resolve the installed skill root as the Harness `installed-commands.md` states).
The runbook records raw readbacks with sources and observation times; growth-review interprets them.
Its findings return as PRD delta candidates. The PRD owner accepts or rejects each candidate.

## Record

| Launch Window row | Checkpoint | Check | Result | Evidence | Owner |
| --- | --- | --- | --- | --- | --- |

One row per check. `Result` is pass, gap or rollback.
`Evidence` names the observed destination, metric source and observation time.
An empty Record table means the runbook is still a proposal.

# Legacy Pins

Read this file only when you resume, recover, validate, edit or close a PLAN, RUN or design package pinned to an earlier Harness version, schema or branch protocol. New work never uses these rules. The validators keep enforcing them, and a pin never widens authorization.

## Pre-0.38 Run-Branch Push

Explicitly pinned pre-0.38 RUN-v11 files keep the historical `integration_push` shape and run-branch push path for recovery only. The legacy push guard requires explicit remote intent, one exact integration-branch target, and the current integration head. Harness 0.38+ rejects that path before any side effect. A legacy push never targets `main` or `development`.

## Pre-0.58 Runtime Dispatch

Under pre-0.58 pinned semantics, the scripts do not support cross-provider runtime dispatch. A node whose providers exclude the current host stays `runtime_unavailable`, and no dispatch path requires `invoke_external_runtime`. These pins keep native dispatch only.

## Branch Protocols Before 0.63

RUNs pinned from 0.59 through 0.62 retain `dual-branch/1` without migration.
Ordinary work freezes remote `development`, lands verified A there, verifies landing SHA S, then separately promotes S to main.
A hotfix freezes main, releases A there, then separately forward-integrates A into current development without losing unrelated work.
Verify the resulting development SHA T and retain its read-back. The outcome report adds development landing S or forward-integration SHA T and read-back.
Pre-0.59 pins retain their recorded candidate/main contract. Malformed pins never establish historical compatibility.
Historical corrections retain their original runtime pin and frozen policy; a new correction source cannot authorize a protocol downgrade.
Never delete existing main or development branches through a RUN cleanup grant.

## RUN-v9 And Earlier Evidence

RUN-v9 and earlier UI evidence remains readable and keeps its working-tree binding. Legacy plans may mark an inapplicable state `<state>:n/a` explicitly rather than omitting it.

## Legacy Wireframe Contracts

Where the current rules name the approved HiFi surface, a pinned legacy contract uses its validated schema-5 or approved legacy `wireframes.html` instead. This covers implementation inputs, route sources, missing-source stops and contract conformance.

A legacy two-target web responsive set is a mandatory delta before its package is next edited or re-validated. Raise the set to at least three ascending viewports and carry the new target through `PRD.md`, the retained design source, the design-system package when present, and every PLAN `ui_surfaces` breakpoint list together. Historical `wireframes/2` stays readable at two targets and `wireframes/3` remains readable with its earlier media-intent shape; current wireframe-free packages create no wireframe.

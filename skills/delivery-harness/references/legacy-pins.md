# Legacy Pins

Read this file only when you resume, recover, validate, edit or close a PLAN, RUN or design package pinned to an earlier Harness version, schema or branch protocol. New work never uses these rules. Use the exact pinned bundle for these procedures; current tools are not their execution path. A pin never widens authorization.

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

## Legacy UI Contracts Before 0.59

Where the current rules name the approved HiFi surface, a pinned legacy contract uses its validated schema-5 or approved legacy `wireframes.html` instead. This covers implementation inputs, route sources, missing-source stops, contract conformance, and the wireframe region order, element inventory and copy that the Visual design and Page-to-PRD rows check.

A schema-5 wireframe PRD has one `copy` anchor per `UI-*` entry. A pinned legacy initial or enhancement wireframe source needs byte-matching `--wireframes <path to wireframes.html>` and must pass the full checker, including sourced copy and the exact PRD join. An unmarked Final UI Acceptance node keeps its pinned behavior; never add the `ui_acceptance` marker to a completed review.

A retained `ui-design/2` package (pins 0.56–0.58) freezes its original conditional `design-system/3` contract; older pins retain their historical joins.

A legacy two-target web responsive set is a mandatory delta before its package is next edited or re-validated. Raise the set to at least three ascending viewports and carry the new target through `PRD.md`, the retained design source, the design-system package when present, and every PLAN `ui_surfaces` breakpoint list together. Historical `wireframes/2` stays readable at two targets and `wireframes/3` remains readable with its earlier media-intent shape; current wireframe-free packages create no wireframe.

## RUN Schemas Before V11

RUN-v9 and earlier UI evidence remains readable and keeps its working-tree binding: the historical working-tree check and invalidation, not the accepted Git blob read. Legacy plans may mark an inapplicable state `<state>:n/a` explicitly rather than omitting it. PLAN v4 orders missions by graph dependency edges like v6; PLAN v2 and v3 keep the legacy `missions[].depends_on` DAG.

## Pins Before 0.55

Runs pinned before 0.34.0 record no `layout_check`. Before 0.35.0 the `deviation_ledger` and `ui_impact_summary` are recorded but not machine-checked. Before 0.38.0 a `ui_evidence` row has no `capture_method` or `target_comparison`. Pre-0.38 RUN-v11 files keep their legacy landing and closeout rule for recovery.

## Container Verifiers Before 0.66

A PLAN pinned before 0.66 may declare `execution.isolation: "container"` with a pinned image RepoDigest, observed runtime, disabled network and read-only rootfs. Such a verifier never falls back to host mode. Container verifiers with `execution.parallel_safe: true` and no exclusive resource conflict may run together and share immutable Git archive bytes within one batch, and `session_exact` reuse stays within one batch.

## Finishing A Run On Its Pinned Bundle

A RUN pinned below 0.66 that needs its original protocol runs the scripts from `~/.agents/skill-backups/product-delivery-harness/<stamp>/delivery-harness/` or from a checkout of tag `v<pin>`, with `<delivery-harness-skill-root>` pointing there. `installed-commands.md` resolution already allows a non-default root.

## Historical Runtime And Publication Evidence

The pinned bundle owns historical app-task drivers, role/launch/result receipts, adoption commands, container caches and signed publication procedures.
Do not run those procedures from the current skill root or add their fields to a new RUN.
Retain old records and original results unchanged.
Historical `adopted` is readable only with an explicit pin below 0.66.
Current dispatch defers it with `pinned_bundle_or_restart_required`; it never proves a current loaded bundle.
A 0.66+ RUN cannot use `adopted`.

# Architecture Improvements: First Batch

Status: complete_local_source
Design workflow: enhancement
UI impact: none (skill contracts and validators, not product UI).

## Problem And Baseline

The architecture review identified incomplete runtime timing, late compiler checks, and optional GTM work outside the current source.
The owner accepted the first three improvements in chat on 2026-10-18.
Baseline: `cac3403e68e9503c812439b15fb92cd786af4004`, clean `ui-review-thresholds` in the `9e8f` checkout.
The prior UI review changes remain part of this baseline.

## Accepted Scope

- Record parent-observed runtime intervals through existing guarded transitions and the current metrics format. Start with the observed Codex host.
- Check source-computable HiFi/compiler compatibility before Visual Approval. Keep registry-dependent coverage in the compiler.
- Reconcile the existing optional GTM source from `dad7a22aa67f0afde18459b6b6d51ba13c1a903f` and link existing product metrics when available.

Use three sequential bounded direct tasks with one parent writer and atomic commits.
There is no parallel write ownership, mission-head integration or consumer PLAN/RUN.
The owner permitted parent research after the exploratory workers hit 429, with independent architecture checking retained.
The architecture role reviews the implementation interfaces; the required independent reviewer checks the final source candidate.
Local source edits and commits are authorized. Publication, installation and host configuration changes remain outside this task.

## Acceptance And Dependencies

| ID | Expected outcome | Focused verification |
| --- | --- | --- |
| ARCH-01 | Guarded observation ingestion preserves event identity, actual durations, failed attempts and unknown values. Replays are idempotent; conflicts fail. | Runtime transition and telemetry positive/negative tests |
| ARCH-02 | Source-only limitations are visible before approval without a provisional registry or circular imports. Diagnostics do not imply compile readiness; existing hard checks and legacy behavior remain. | UI preflight, compiler showcase and dependency-import tests |
| ARCH-03 | Both existing GTM skills are discoverable in source with optional product/metric references and unchanged publishing boundaries. | Standalone skill validation, contract checks and independent scenario review |

All changes preserve Impeccable requirements, dimension thresholds, current evidence and action authorization.
Binding-only refresh, rolling writers, general code generation and additional growth automation remain later proposals.

## Document Impact

Update each changed skill's owners and all four README descriptions in its atomic task.
Preserve core versions, active pinned runs, installation destinations and historical source records.
Use existing metrics and campaign records; add no local-only file class or Gitignore rule.
Detailed check logs and review packets stay in the task's external evidence directory.

## Change Log

| Observation | Result | Remaining work |
| --- | --- | --- |
| 2026-10-18 entry | Baseline and source scopes verified; implementation interface review dispatched. | All three tasks and final review pending. |
| 2026-10-18 GTM source | Added the eight skill files from `dad7a22a`, then linked optional product/operation/metric/MS references. Preserved standalone drafting and separate publication authority. | Skill specification, relative links, invocation metadata, 65 core contracts and diff checks passed. Core skill trees, installers and version remained unchanged at this checkpoint. Final independent review pending. |
| 2026-10-18 runtime intervals | GTM committed as `8f017c28`. Added guarded `record-runtime-observation`, bound to RUN/reservation/attempt/worker and derived provider identity. | Ingestion 13 tests (one symlink capability skip), prior runtime observations nine, transitions 15 (one platform skip), launch CLI five, and Pyflakes passed. Initial review-node lookup failed; it was corrected to the existing verifier-node shape and rerun. Identical replay preserves RUN bytes; conflicting or stale input fails. |
| 2026-10-18 source preflight | Runtime intervals committed as `642760bc`. Reused compiler animation classification for advisory `ui-design/3` source diagnostics before approval. | Source unit tests five, fresh CLI/integration tests six, showcase regressions 19 and Pyflakes passed. Static controls stay quiet; stale HiFi still fails; `/2` is unchanged. Missing helpers and registry-dependent checks remain explicit, without a new gate or provisional registry. |
| 2026-10-18 independent review repair | Preflight committed as `42b38643`. Review found a P2 warning for static specimens beside unrelated conditional custom properties. | The new regression failed before repair. Static-only classification now ignores those variables without granting animation provenance. Seven source tests, six integration tests, 149 compiler tests (four Windows skips), and Pyflakes passed. Fresh candidate review remains required. |
| 2026-10-18 final candidate | Repair committed as `f342b3b7`. Fresh independent correctness and security review passed all 28 changed paths with no exclusions. | Exact-candidate UI 380, compiler 149, runtime 22, and core contract 65 tests passed their suites. Windows platform skips passed on Linux; Linux-only skips passed on Windows. Source/standalone specifications, Pyflakes and documentation weight passed. Detailed logs remain in the linked result. |

Runtime ingestion lives in a focused module. The existing transition entrypoint only dispatches it and preserves transaction guards.
The new observation request does not add RUN fields, change the scheduler, or make timing evidence an acceptance gate.
Source preflight remains with the compiler's existing tree/CSS reader to avoid duplicate parsing or a circular import.
The large UI checker only exposes a diagnostics collector and CLI output; existing strict results keep their original meaning.

## Results And Remaining Work

All three accepted source outcomes are complete at `f342b3b7e588daf139743fa6aa04f905e1bbf9f1`.
The final bookkeeping commit changes only this Epic and the document index; the source review remains bound to that candidate.
See the [local result and verification receipts](C:/Users/mps19/.codex/visualizations/2026/10/18/01a14ddc-a48e-7f33-bbdc-912f5d10aa9b/architecture-review/architecture-result.md).

The handoff audit found shared instructions current by meaning against the installed `0.64.0` template.
Its SHA-256 is `257C6DB1B429FCE7138F29BB6E8AC9ACB12EBAD3C1524B0A7A20180CF84D939C`; source-repository exceptions remain intentional.
Document sync remains `review_required` for unknown loaded identity, first observation and unchanged README migration/history names.
Those findings were inspected; no installed or loaded skill update is claimed.

Runtime tests use synthetic fixtures. Real host adoption and measured time savings remain unverified.
GTM integration supplies source skills and draft handoffs, not published campaigns or growth results.
No push, formal release, installation, deployment or monitoring activation occurred. No temporary service remains from this task.

## Release And Installation Follow-up

Published in [v0.65.0](https://github.com/Phlegonlabs/product-delivery-harness/releases/tag/v0.65.0) through PR #151 at main `8847b027d73deb711ff33fb7b8a71c9a7363803c`.
The seven-skill bundle was installed and all 439 files matched the release. Standalone GTM sources remain optional and uninstalled.
See the [publication and installation result](EPIC-ui-review-efficiency.md#publication-and-installation-result) for exact CI, independent review, backup and source evidence.

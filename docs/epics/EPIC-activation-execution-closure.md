# EPIC-activation-execution-closure: Require external execution closeout

Status: complete

## Problem And Baseline

The owner's reviewed flow assessment found that Activation runs often stopped at
a filled document. A filled or structurally valid record does not prove that an
authorized, executable external action was attempted, verified, or explicitly
blocked. Baseline: detached source checkout at
`bdae1d82acfd24cdeb2866f5480ff4d4d73b0b61`.

Decision source: owner-approved
`流程與提速評估.md`,
section 6.

## Accepted Scope

Add a read-only terminal closeout check. Every required ACT action must be
verified, or blocked with a concrete reason or the exact owner-deferral form.
Ready, configured, pending, uncertain, and stale required actions fail. An
accepted blocked action or owner deferral keeps the Record blocked; only a
record without one can be handoff-ready. The closeout command joins the
existing source, capability, digest, evidence, and readiness contracts. It does
not call providers, infer authorization, or add an SDK engine.

## Change Log

| Observation / change | Scope | Verification |
| --- | --- | --- |
| 2026-09-29 implementation working-tree | `skills/product-activation/SKILL.md`, activation contract, checker, tests, four README descriptions, this Epic and index. Added `--require-closeout`, owner-deferral syntax, release-identity evidence wording, and manual return read-back wording. No schema change; `/1` records remain readable. | Activation suite: 61 tests passed in 0.781s. Logs: `%TEMP%\\pdh-activation-closeout-focused9-err-20260929.log`; pyflakes, skill spec, docs weight, and diff check passed in `%TEMP%\\pdh-activation-closeout-static2-out-20260929.log`. Entry document sync ran with loaded identity unobserved and reported byte-drift review; `%TEMP%\\pdh-activation-closeout-document-sync-20260929.log`. Cross-skill and exact-candidate checks remain before release. |
| 2026-09-29 parent-review repair working-tree | Checker, tests, skill and contract wording, four README descriptions, and this row. An explicit closeout no-op may have an empty task boundary only when every architecture target has a concrete `n/a` readiness disposition. Normal structural parsing still rejects an empty boundary. Owner-deferral remaining work and generic blocked reasons must be concrete; placeholder or generic-only reasons fail. | Activation suite: 65 tests passed in 0.865s. Logs: `%TEMP%\\pdh-activation-noop-repair5-err-20260929.log`; pyflakes, skill spec, docs weight, and diff check passed in `%TEMP%\\pdh-activation-noop-static2-out-20260929.log`. Fresh exact-SHA suite and release checks remain. |
| 2026-09-29 policy reconciliation working-tree | Activation skill and contract plus four README descriptions. Made inventory, delta reconciliation, continuation through mutation/read-back/behavior, and terminal closeout the default execution obligation; explicit owner request is required for documentation-only planning. Preserved valid evidence reuse, no-op disposition, authorization, digest, route, secret, and read-only checker boundaries. No checker or schema change. | Activation suite: 65 tests passed in 0.881s. Logs: `%TEMP%\\pdh-activation-policy-final-err-20260929.log`. Skill spec, docs weight, and diff check passed; log `%TEMP%\\pdh-activation-policy-final-static-out-20260929.log`. Atomic documentation commit and parent exact-SHA integration remain. |

- 2026-10-03 consolidation repair, baseline `4b62c2ab15f958633ac9e61e79ab03551d7b3200` on `codex/harness-flow-modernization`: independent correctness review reproduced rejection of concrete translated blocker and owner-deferral prose. Recognize Unicode words and unsegmented prose, retaining placeholder/vague-reason rejection and the blocked record requirement. English machine anchors and action authority are unchanged. UI impact none; this restores the contract's existing translated-content allowance. New CJK cases failed before the fix; working-tree Activation checker 60/60 then passed, including Chinese ordinary blockers, Chinese owner deferral, French prose, vague translated reasons and no false completion. Whitespace passed. Scoped diff, commit receipt and red/green logs remain under `pdh-worktree-merge-20261003-eb6k85jg`; fresh final-SHA CI and follow-up review remain pending.

- 2026-10-03 no-op disposition repair, baseline `c382375b7b305d30f9b196814125d8a0199b8f4f` on `codex/harness-flow-modernization`: an unresolved PR #135 comment independently reproduced a taskless closeout with `n/a - x`. Target Readiness, no-op detection and closeout now validate the reason suffix with the existing substantive Unicode predicate. Source contracts and README descriptions already require concrete target reasons; no new rule or action authority is added. UI impact none. The regression failed for four trivial/placeholder reasons before repair; the working-tree checker then passed all 61 tests, including concrete English and Chinese no-ops. Scoped Pyflakes and whitespace passed. The existing checker remains one document-validation responsibility; this repair adds one shared predicate rather than splitting its module. External logs are `activation-noop-suffix-red.log`, `activation-noop-suffix-green.log` and `activation-noop-suffix-pyflakes.log` in the consolidation evidence directory. Fresh final-candidate CI and independent re-review remain required.

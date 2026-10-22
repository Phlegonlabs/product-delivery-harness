# EPIC-activation-execution-closure: Require external execution closeout

Status: local_candidate

## Problem And Baseline

The owner's reviewed flow assessment found that Activation runs often stopped at
a filled document. A filled or structurally valid record does not prove that an
authorized, executable external action was attempted, verified, or explicitly
blocked. Baseline: detached source checkout at
`bdae1d82acfd24cdeb2866f5480ff4d4d73b0b61`.

Decision source: owner-approved
`C:/Users/mps19/Documents/Codex/2026-09-29/harness-flow-review-01a0ed97/流程與提速評估.md`,
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

- 2026-10-03 consolidation repair, baseline `4b62c2ab15f958633ac9e61e79ab03551d7b3200` on `codex/harness-flow-modernization`: independent correctness review reproduced rejection of concrete translated blocker and owner-deferral prose. Recognize Unicode words and unsegmented prose, retaining placeholder/vague-reason rejection and the blocked record requirement. English machine anchors and action authority are unchanged. UI impact none; this restores the contract's existing translated-content allowance. New CJK cases failed before the fix; working-tree Activation checker 60/60 then passed, including Chinese ordinary blockers, Chinese owner deferral, French prose, vague translated reasons and no false completion. Whitespace passed. Scoped diff, commit receipt and red/green logs remain under `C:/Users/mps19/AppData/Local/Temp/pdh-worktree-merge-20261003-eb6k85jg`; fresh final-SHA CI and follow-up review remain pending.

- 2026-10-03 no-op disposition repair, baseline `c382375b7b305d30f9b196814125d8a0199b8f4f` on `codex/harness-flow-modernization`: an unresolved PR #135 comment independently reproduced a taskless closeout with `n/a - x`. Target Readiness, no-op detection and closeout now validate the reason suffix with the existing substantive Unicode predicate. Source contracts and README descriptions already require concrete target reasons; no new rule or action authority is added. UI impact none. The regression failed for four trivial/placeholder reasons before repair; the working-tree checker then passed all 61 tests, including concrete English and Chinese no-ops. Scoped Pyflakes and whitespace passed. The existing checker remains one document-validation responsibility; this repair adds one shared predicate rather than splitting its module. External logs are `activation-noop-suffix-red.log`, `activation-noop-suffix-green.log` and `activation-noop-suffix-pyflakes.log` in the consolidation evidence directory. Fresh final-candidate CI and independent re-review remain required.

## Staged Digest Follow-Up

The owner requested this fix after the 2026-10-20 whole-skill review confirmed a P2 command-path defect.
Baseline: clean `5a1cce1f` on `codex/ui-acceptance`; the preceding atomic commit fixes UI diagnostic coverage.
Preparation uses a staged record, but the documented digest command defaults to the live record.
Every preparation digest example must explicitly select `docs/.activation-staging/<run-id>/ACTIVATION.md`.
Keep the CLI's live default, action authorization, read-only behavior and publication rules unchanged.
Acceptance requires executing documented commands with a staged-only record and with different live/staged action digests.
Check that neither record changes. Run the Activation suite and include this fix in the final independent candidate review.
The direct route has one parent writer. UI impact and Gitignore impact are `none`.
The existing test module retains its checker-contract responsibility; this regression does not require a module split.
All three preparation digest commands now select the staged record explicitly, with a quoted path.
The regression executes those documented commands, including a run ID containing spaces.
It confirms the staged digest with no live file and with a different live digest; both records remain unchanged.
The regression failed on the old documentation and passed after the command fixes.
All 75 Activation tests passed. Six Python script trees passed Pyflakes; source specification, documentation weight and whitespace checks passed.
Logs: `fix-activation-red-1792565311497198300.log`, `fix-activation-green-1792565353546688400.log` and `fix-activation-suite-1792565396900115000.log`.
These logs are in `C:/Users/mps19/.codex/visualizations/2026/10/20/01a15a38-8db7-7e32-9e42-6380059bccdf`.
Scoped document sync retains unknown loaded identity and first-observation review findings; no loaded-runtime adoption is claimed.
The fix is committed as `73bdfd34` after the separate UI diagnostic repair `5a1cce1f`.
On 2026-10-21, fresh independent correctness and security review passed for clean `73bdfd347518237b11cba3ec101175614544c8db`.
The review covered the complete 13-file follow-up diff, with no findings, exclusions or gaps.
The unchanged [security result](C:/Users/mps19/.codex/visualizations/2026/10/20/01a15a38-8db7-7e32-9e42-6380059bccdf/fix-security-result.json) passed the source result validator.
The reviewer independently passed all 66 Activation checker tests; the parent passed all 75 Activation tests at that candidate.
The final bookkeeping changes only the two fix records and index; reviewed source bytes remain unchanged.
Shared instructions are current by meaning against the observed installed 0.65.2 template, preserving intentional source exceptions.
Unknown loaded identity, first-baseline and historical README-pointer findings remain explicit; document sync is not a PASS.
This local source fix is complete. No install, push or release occurred; the prior installed development bundle remains unchanged.

## Audit-Fix Installation

On 2026-10-21, the owner requested the shared development installation from clean `92027b82`.
The official installer and full-tree verification passed for all seven skills and 439 tracked files.
The installed Activation suite passed all 75 tests, including the staged-command regression.
The [installation record](EPIC-ui-review-efficiency.md#audit-fix-development-installation) names coordination, source, backup, digest and read-back evidence.
The previous installation is recoverable. Consumer pins remain unchanged; loaded identity remains unknown until a fresh host session.
No push or formal release occurred.

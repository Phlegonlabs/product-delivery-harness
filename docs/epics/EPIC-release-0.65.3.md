# Release 0.65.3

Status: fixed-candidate publication; the linked receipt records the final result
Design workflow: maintenance
UI impact: none (skill workflow and source release)

The owner requested a PR and main merge after required checks and independent review.
Baseline: clean `8382c437d33e5aed38c698e933cb4466b902abed` on `codex/ui-acceptance`, observed 2026-10-21.
Remote main: `8db251b7f0999dd62a100ec70ea78b64455b2b6d`.

Scope: publish the accepted UI-review, visual-handoff, agent-policy and validation fixes already committed on this branch.
The source outcomes remain in their existing Epics; this record does not rewrite their historical evidence.
The release bumps package, lockfile, copied-skill version, RUNBOOK default and all four README surfaces to `0.65.3`.
No managed schema changes or active RUN migration occur.

The parent is the sole writer. A fresh configured reviewer inspects the complete base-to-candidate diff without changing source.
The required `validate` aggregate must pass every Linux, macOS, Windows, browser and golden-path job on that exact candidate.
Use a merge commit to preserve atomic history, then prove candidate/main tree equality and verify the new main SHA independently.
Tag only verified main as `v0.65.3`. Compare the released bundle with shared installation before any required coordinated installer update.
Branch deletion and worktree cleanup remain outside this request.

The [publication receipt](C:/Users/mps19/.codex/visualizations/2026/10/20/01a15a38-8db7-7e32-9e42-6380059bccdf/release-0.65.3-result.json) records exact candidate/main identities, review, CI, tag and installation results.
The PR description and its linked checks provide remote publication evidence.
Loaded skill identity remains unknown until observed; installed bytes do not prove existing sessions adopted them.

## Change Log

| Observation | Result | Remaining work |
| --- | --- | --- |
| 2026-10-21 entry | Owner authorized the PR and conditional main merge. Main requires the `validate` check and resolved review threads. Release metadata is prepared. | Fixed-candidate CI/review, SHA-bound merge, exact-main verification, tag and installation comparison. |
| 2026-10-22 maintenance-handoff repair | Review of `044e9311` found one medium regression after complete 59-path coverage and 601 reviewer tests. Added current-product maintenance handoff through the existing task-record classifier. | Fresh review and CI on the repaired candidate before merge. |
| 2026-10-22 preview repair | Review and GitHub Codex identified unchecked derived preview bytes at `541abdb4`. Ordinary preview equality and explicit historical omission now pass 27 focused cases. | Fresh exact-candidate review/CI and resolution of the verified GitHub thread. |

## Maintenance Handoff Repair

The [original review](C:/Users/mps19/.codex/visualizations/2026/10/20/01a15a38-8db7-7e32-9e42-6380059bccdf/release-0.65.3-candidate-review.json) remains unchanged with decision `fix_required`.
Its SHA-256 is `f2e88e2b4c1b828ce4c2bdb135ccb4a15156d70f02e5fc5af93093a980e81f64`.
The helper wrongly required historical Product/Stack hashes even when the current frozen maintenance join accepted updated product sources.

Implementation maintenance now accepts the existing validated task record with UI impact `none` or `style`.
It names current Product/Stack files, marks historical bindings as provenance, and retains strict study, capture, HiFi and pair checks.
Initial design and enhancement source joins remain strict. Managed PLAN/source joins and all approval requirements remain unchanged.
The helper writes no input file and grants no authority.

Regression tests first failed on the previous helper. The initial current-version fixture needed its existing eval exemption before reproducing the intended failure.
After that fixture correction, the accepted complete maintenance join reached the missing handoff route and failed as expected.
All 16 visual-input and ten frozen-package join cases pass after repair, including CLI equivalence and negative classification/source cases.
Those 26 checks are parent executions; the earlier 601 tests remain reviewer evidence for `044e9311`.
This is the first repair round for this maintenance-handoff defect family. No previous actor-state repair budget is reset.

## Derived Preview Repair

The complete 60-path re-review of `541abdb4` closed the maintenance defect and found one separate medium preview-freshness defect.
The [corrected review result](C:/Users/mps19/.codex/visualizations/2026/10/20/01a15a38-8db7-7e32-9e42-6380059bccdf/release-0.65.3-repaired-review-corrected.json) preserves the original result and fixes one supplemental line citation.
Its SHA-256 is `0d7ca2d7dc0d0e38006d4f9b558f76e20b961b346829a1da451037abfb59fa40`.
The same issue appeared in GitHub Codex thread `PRRT_kwDOTLHN1c6vFFwr`. That thread remains a merge blocker until verified resolution.
CI passed all 20 jobs at `541abdb4`; that result does not validate this later repair.

Ordinary implementation now compares a derived preview with the existing deterministic renderer for the bound pair and HiFi.
An edited, unrelated or missing preview blocks packet assembly without rewriting input files.
Maintenance retains its historical pair and HiFi, and omits the unchecked historical derived preview from current inputs.
It does not require fresh historical rendering or reopen Visual Approval.

A real current-version package reproduced the preview-only failure before repair.
The synthetic legacy-pair unit remains separate from real `/4` preview coverage in the frozen-package integration suite.
All 16 visual-input and 11 frozen-package cases pass after the preview repair.
This is the first repair round for the preview-freshness family. Fresh exact-candidate review and CI remain required.

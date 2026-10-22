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

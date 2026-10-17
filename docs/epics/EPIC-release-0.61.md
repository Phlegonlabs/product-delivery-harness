# Release 0.61.0

Status: complete
Source verification recorded; publication tracked by [PR #136](https://github.com/Phlegonlabs/product-delivery-harness/pull/136).
UI impact: none

## Scope And Authority

On 2026-10-04, the owner requested commits, pushes and a PR merge directly to
main, without development. This is a one-release exception to the ordinary
development-first path. The standing branch policy and managed RUN contracts
remain unchanged. No branch deletion or worktree removal is authorized.

The chat began in clean detached checkout `20fb` at
`1782fa000b107396fd36787c7df7fad8a2141c82`, the observed remote main and v0.60.0.
Remote development was `ec9c599c70dce3a46b948865fc300503a4c71998`.
Three completed source groups were found in clean, idle work checkouts:

| Source branch | Fixed source head | Accepted work |
| --- | --- | --- |
| `codex/harness-flow-modernization` | `1200d98ef05cd30bd614043d8100bf7c46396e48` | STE writing, caller/state architecture methods and bounded experiments |
| `codex/document-review-handoff` | `9eea776f` | Complete Product Definition and UI document inventory in chat |
| `codex/readme-release-skills` | `27c8af66` | Standalone README writing and runtime packaging skills |

The parent owns `codex/release-0.61.0` in this checkout. It preserves the original
atomic commits and records integration separately. Source work and its existing
reviews stay in the linked Epics. Remote execution remains pending.

The minor version reflects new required review-presentation and writing rules.
No runtime schema or historical approval is migrated. Standalone skills remain
outside the seven-skill installer and digest.

## Acceptance

Run focused integration checks, the complete applicable local matrix, fresh
independent source/security review, and exact-candidate Linux/macOS/Windows CI.
Require a clean checkout and no blocking findings before merge. Merge through
the required PR mechanism with the candidate SHA bound at action time. Verify
the resulting main tree, repeat exact-main CI and fresh security review, then
tag main and compare/install the released seven-skill bundle at a quiet boundary.

Logs and temporary artifacts stay outside Git under
`pdh-release-20261004-cmvxqzgi/`.
The existing dependency/cache/environment ignore rules cover this task.
No consumer PRD, architecture, design package or PLAN/RUN applies.
Loaded skill identity is unobserved. Installed baseline is 0.60.0, digest
`252229aff6fafa7ab1283ff5e052f800b31ee713b6b64ac0b66b6c852ef915af`.

## Change Log

| Checkpoint | Change and evidence | Verification and remaining work |
| --- | --- | --- |
| 2026-10-04 entry | Clean baseline and three source heads above; live main/development read-back agreed with local remote refs | No uncommitted source work. Owner explicitly bypassed development for this release. |
| 2026-10-04 document-review integration | `571339628858a39d840e20c79df6ab22c27f98d4`; original `9eea776f` retained | 60 Harness contracts and staged whitespace passed. Only index conflict resolved, preserving both inventories. |
| 2026-10-04 standalone integration | `0e1de4ccd6a4e17a2218173f6af98b198500c8d8`; original four source commits retained | Standalone skill specification and 60 Harness contracts passed. Only index conflict resolved, preserving all entries. |
| 2026-10-04 release preparation | Working-tree version, lock metadata, four-language badges/history and RUNBOOK default move together to 0.61.0 | Candidate checks, fresh review, push, PR merge, tag and installed update pending. |
| 2026-10-04 focused release checks | Source and standalone specification, full pyflakes, docs weight, 60 Harness contracts, nine review-packet tests and seven graph-identity tests | All passed. Playwright 1.62.1 and Chromium revision 1234 observed; dependency versions match the lockfile. Complete matrix and independent exact-SHA review follow the release commit. |
| 2026-10-04 source candidate | `088165eaad209868d7923ced2ea3b0cb963dbafe`; [complete platform run](https://github.com/Phlegonlabs/product-delivery-harness/actions/runs/37203732054); independent REL-061-R1 review | All 20 CI jobs, including required browser, golden path, Linux/macOS/Windows suites and validate passed. Fresh full-diff source/security review passed with no exclusions. Native reviewer binding is Sol/xhigh; independent provider attestation unavailable. |
| 2026-10-04 local verifier cleanup | Exact-candidate hosted matrix completed while the duplicate local matrix was still running | Local broad attempt deliberately cancelled, not PASS. Captured runner PID/start/command and descendants in `local-matrix-stop.json`; every captured task process exited. Focused local results remain separate. |
| 2026-10-04 owner confirmation and handoff audit | Owner confirmed all three groups and `codex/release-0.61.0`; inherited index incorrectly described main as 0.58.0 | Correct only the live index status and this record. No skill/source bytes changed. Final bookkeeping SHA requires fresh complete CI and independent review before merge. Installed template 0.60.0 remains current by meaning; its missing STE section is the accepted source addition pending installation. |
| 2026-10-04 publication-state correction | REL-061-R2 reviewed `956540c1ee1473fa327500e7a7318367a104eb08`; complete source-security PASS, one release-record finding | Present tense overstated future publication artifacts. Separate observed source verification from pending final-head, main, tag and installation gates below. No code, skill or configuration changes. Fresh final-candidate review and CI required. |

## Publication Evidence

The exact source-verification results above remain bound to their original SHA.
Release bookkeeping changes only this record and the Documents index.
At this source-record freeze, final-head verification, main promotion, tagging
and installation remain pending. The table separates observations from expected
destinations. An expected path, tag name or link does not prove completion.

| Gate at this source-record freeze | Observed state | Destination for later results |
| --- | --- | --- |
| Source candidate `088165ea` | Complete platform CI and independent source/security review passed | Original exact-SHA run and review above |
| Final corrected PR head | Fresh complete CI and source/security review pending | [PR #136](https://github.com/Phlegonlabs/product-delivery-harness/pull/136) checks and external reviewer result |
| Main promotion and release tag | No merge or tag performed | PR merge SHA, exact-main CI/security result, then verified remote `v0.61.0` tag |
| Local installation and branch read-back | Installed 0.60.0 observed; no release installation performed | Official installer backup/receipt and external `release-outcome.json` |

After verified publication, the parent will write the installation and branch
read-back receipt to
`release-outcome.json`.
The PR, verified tag and receipt will retain later outcomes without rewriting
this frozen candidate's historical observations.
Remote execution remains pending in its source Epic.

Related source records: [architecture and loops](EPIC-architecture-loop-remote-execution.md),
[writing](EPIC-document-writing-policy.md), [package review](EPIC-document-review-handoff.md),
and [standalone skills](EPIC-readme-release-skills.md).

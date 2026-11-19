# EPIC-workflow-validation: test every skill end to end, then close the handoff gaps

Status: candidate prepared as 0.94.0 on branch `fix/paperpair-workflow-validation`; merge, tag and install on the owner's word of 2026-11-19
Design workflow: enhancement
UI impact: none (UI test fixtures only)

## Problem And Baseline

On 2026-11-18 the owner asked for every step of every skill to be tested in throwaway repositories, with anything that does not work repaired. On 2026-11-19 the owner asked for multi-agent scenario runs across skill handoffs, and then for a multi-agent review of the whole suite. Baseline: `main` `31c6d89a` (v0.93.0).

The runs showed that a downstream skill often did not notice a changed or broken upstream file. A checker that could not read a row skipped it, so a claim with no support passed.

## Accepted Scope

- Handoffs fail on what they cannot read: research claims, campaign approvals, keyword-map citations and campaign registrations.
- Product Definition: a headless tool may record a reasoned absence of public discovery and then launches through owned channels only; PRD `KW-*` citations resolve against the keyword map.
- Owner decision, 2026-11-19: the Launch Window accepts only the six-column table with Destination.
- `growth-review`: localized store-listing fields; demand research also when an enhancement adds public pages.
- Release packager: check images and the CLI example inside the npm tarball; stop the whole process tree at the deadline.
- The default spec check covers the five standalone skills.

Not in scope: Linux test runs (owner decision of 2026-11-19: this machine has no Linux; the CI Linux jobs cover POSIX cases); consumer adoption.

## Change Log

| Change | Commits |
| --- | --- |
| Security reference recognized by both context tools; standalone skills in the default spec run | `4b36ca40`, `3fc442fb`, `98d4633d` |
| Document sync tracks keyword maps, public messaging, research and campaign inputs | `0eb1db22`, `5da21e9d`, `653edce0`, `c1fdf2cb` |
| Approved claims checked against current research; campaign bindings | `b34f70c7`, `9c60ce17`, `7277cc74`, `3d2d0f01`, `2cc0bebf`, `415b0d65` |
| Keyword citations, headless discovery, launch scope | `0e3decb9`, `f2e59f57`, `2cb4db7d`, `e19ceb2a`, `29cb048d` |
| Six-column Launch Window only | `abc576f6` |
| Growth: store-listing fields, demand research for enhancements | `ffb7628f`, `0163f639` |
| Release packager: npm README images and CLI example, process tree | `f94eb1e0`, `55fb1787`, `56a695ad`, `5abf5611` |
| UI fixtures: Chromium run, touch targets, contrast canvas | `7bdd562d`, `9f51c5b4`, `6984c968` |
| Cross-skill wording: interview evidence, contact list, logo sketch counts | `a416a588`, `31e0ee6d` |

## Review And Repairs

Scenario runs (Codex, 2026-11-18/19) used four throwaway projects covering the ten skills, an Apple Silicon Mac for the Darwin-only cases, and reran each repair against the recorded counterexamples.

Suite review (2026-11-19) on `55fb1787`: four read-only GPT-6.1 Sol scopes and six GLM-5.3 Flash explorers (two timed out and were rerun as four narrower scopes). 17 confirmed defects, each reproduced by the parent before repair. 16 were repaired in one consolidated repair. The seventeenth, the five-column Launch Window, became the owner decision above. The UI-to-design-system-to-delivery chain, the standalone skill paths and all 511 documented script flags showed no defect.

One targeted re-check on `31e0ee6d` confirmed 16 repairs and found five defects in the repair itself: an italic Claim header read as malformed, a fenced copy's line reported, and a Markdown-rendering filter in the release packager that hid real images or rewrote HTML paths. The filter was removed rather than patched; image syntax outside a fenced block counts again. The process-tree stop now kills and waits for the root on every path. These were verified with the reviewer's own reproductions; no second re-check was run.

Final review point on `4d6f42d6`, the range after the re-check: one GPT-6.1 Sol code review and one GLM-5.3 Flash documentation check, run in parallel. Three findings, all fixed: a failing root kill skipped the wait in the tree stop; the four version entries overstated the tree stop; the Spanish entry dropped "interview". The fixes were verified with the reviewers' own inputs.

While rerunning the deadline test the parent found that `node` on Windows can be a version-manager shim: the old timeout killed only the shim and left the real Node running. Five orphaned test processes were stopped by recorded PID.

## Verification

- Full Required Verification matrix on `31e0ee6d`: 9 of 9 steps passed (Windows).
- On `5abf5611`: spec check, pyflakes, docs weight, diff check and eight affected harness test modules passed.
- On `abc576f6`: the product suite, 474 tests, passed.
- The pull-request CI matrix runs on the final head.

## Consumer Impact

Three consumer PRDs still use the five-column Launch Window: agentic-commons-site, agentic-commons-site-deploy and agentkiosk. They need a Destination column when they adopt 0.94.0. No consumer is pinned above 0.87.0 today.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / fix/paperpair-workflow-validation / release candidate / none
Stage and skill: source maintenance of the skill suite; direct work, no PLAN/RUN
Inputs consumed (path + hash or revision): main 31c6d89a (v0.93.0); owner requests of 2026-11-18 and 2026-11-19
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): unknown; not run in this round
Approvals in force (gate, owner, date, candidate): owner, 2026-11-19: six-column Launch Window; commit, push, merge commit and branch removal
Done and verified (command, exit code): ci_test_shards.py matrix on 31e0ee6d, exit 0; affected modules on 5abf5611 and the product suite on abc576f6, exit 0
Remaining: pull-request CI and bot review; merge; tag v0.94.0; install; branch cleanup
Blocked / waiting (gate name or owner decision): none
Next action (one command or one owner decision): open the pull request
Next owner (skill or human): parent agent
```

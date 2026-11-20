# EPIC-ui-review-convergence: fewer UI review passes and less browser time

Status: published as 0.95.0 on 2026-11-19 (PR #207, `main` `61278db1`, tag `v0.95.0`); installed the same day (five-skill contract `dac0ed2d…`); patch 0.95.1 prepared on `fix/measure-hidden-text-at-zoom`, not yet published; consumers not yet adopted
Design workflow: enhancement
UI impact: none (review rules, evidence rules and UI scripts; no product UI)

## Problem And Baseline

On 2026-11-19 the owner asked why UI testing takes so long in every project and why each review pass finds new problems. Read-only analysis of jolvex-platform, agentkiosk, hk-car-care and mark-six-3d found UI rounds of 50 to 146 hours. The time went to evidence rework, repair and re-check cycles, and review waves that grew far past the rule's two reviewers: jolvex's first wave inspected all 5,285 captures under a 540-second reviewer cap and ran as 16 agents. A mid-round Harness install changed identities and forced rework. Baseline: `main` `0613b863` (v0.94.0).

Owner decisions, 2026-11-19: stop the running UI threads; remove the 9-minute reviewer cap (the profile guard now allows up to 7,200 seconds; that file is outside this repository); keep three direction studies (the one-study-first change was cancelled); delete review packets once their review passes; the real problem is too many reviews, each finding new problems.

## Accepted Scope

- A review wave is two reviewers, never split by page group. They look by eye at each page at its smallest target, every machine-flagged case and the axis sample.
- A re-review closes the earlier findings and judges the repair. A defect already present in unchanged content is a next-round note, except a regression the repair caused or a high or critical security finding.
- `review_evidence.py ready` before a wave or re-review. A hang or driver failure gets one rerun, then goes to the owner.
- Matrix driver: per-page and per-operation restart budgets that give the same rows at any worker count; a failed restart blocks only its page; `text-split`; the intermediate sweep on the axis sample's states without repeated interactions; seconds per kind of work in the summary line.
- Delivery parity recaptures only the routes a repair names, with per-page HiFi carry.
- A round keeps its Harness version until it closes. `review_input.py --remove` deletes a passed packet.
- Raw capture output stays out of Git; the approval check lists cited captures missing from the index.
- Stopping a process tree never follows a reused Windows parent id (matrix driver and release packager).

Not in scope: fewer interaction attempts (every operation at every target with click and keyboard is 86% of the remaining measured work; that is a coverage decision for the owner); `--only` narrowing the reviewer pass (0.6% of the measured jolvex run, and the reviewer contract is package-wide); a targeted after-repair recapture option.

## Change Log

| Change | Commits |
| --- | --- |
| Round version freeze; passed packets removed | `13bc5916`, `c8e835f7`, `4529bd1a` |
| Per-page and per-operation restart budgets | `78cb8a69`, `6f0cb27c`, `8de2338b` |
| `text-split` measurement | `80ed463f`, `f0627065`, `fc0ab193` |
| Readiness check; repeated hangs go to the owner; sidecar records checked | `f310b74f`, `139ecd3c`, `e5c597df`, `e65ac817`, `4d403d65`, `c873f15f` |
| Parity recapture by repair scope; per-page HiFi carry | `168b5304`, `ab8e6daf`, `efe6b985`, `a2330f10` |
| Raw captures out of Git; cited captures in the index | `b78f9903`, `dc915f57`, `e0a1bdc5`, `262e44aa`, `49bcd930`, `8c3e3877` |
| Intermediate sweep on the axis sample, no repeated interactions; earlier receipts stay valid | `0b32d38b`, `ff5423ce` |
| Where a run's time went | `ea0775c8` |
| Process-tree stop ignores reused parent ids and ends each process through a checked handle | `b13aacdf`, `7e6a69e0`, `e3b4fffa`, `9d99e9d6` |
| Packet removal refuses links, foreign directories, work trees and changed packets | `cc08bba3`, `78aa2693`, `a2fc79eb`, `740fb9e3`, `238f7d85` |
| Two-reviewer waves, the visual inspection set, re-check scope | `9cfd4cae`, `a0678b96`, `4b6e2941`, `3e61b378`, `d359cf46`, `6192a7e7`, `1765027d` |
| Release 0.95.0 | `e877f285`, `4a07bca3` |
| 0.95.0 publication record | `6d059e9c` |
| Measurements skip screen-reader-only text at any canvas zoom | `b152a453` |
| A destination on the source page fails after 10 s; page loads keep 30 s | `6dcb0d48` |
| A repair reruns only what it can affect; a verified tree is not run twice | `9ac20fa9` |
| Release 0.95.1 | `3b7a13af` |
| Every evidence owner allows the tree reuse, for deterministic suites only | `0590f801` |
| `clip` counts as hiding only on absolute and fixed boxes | `586322c9` |

## Review And Repairs

Workers W1 to W4, W6, W6b, W7 and repair workers A, B and C (Claude Opus 5.5) each wrote one change in its own worktree; the parent cherry-picked them onto `ui-review-speed` and resolved two conflicts by keeping both sides. W5 (one direction study first) was cancelled by the owner's decision.

Matrix-flow review on `efe6b985`: three read-only GPT-6.1 Sol scopes (matrix size, driver code, capture speed) and one GLM-5.3 Flash documentation check. The parent reproduced each blocking finding before repair:

- An operation split across workers spent one budget per worker: four workers gave three FAIL rows where one gave two. Fixed by making an operation's attempts one work item.
- A failed restart at a phase start aborted the run with exit 2. It now blocks only the next page's work.
- The readiness check could never pass a permanent tool limit. A repeated hang now goes to the owner after one rerun.
- The intermediate sweep covered every state, derived ones included, where the rubric names the axis sample. On the last jolvex public run (756 base cases, four workers, 44.6 minutes) it took 630 cases; the axis sample takes 150.
- The axis sample is per surface in the driver and was per page in the rules; the rules now say surface.
- The GLM finding (text split missing from the self-review list) was already fixed in `fc0ab193`.
- Not changed: a hyphen or soft hyphen inside a figure (Chromium never breaks an ASCII hyphen before a digit, UAX #14 LB21 and LB25); a raised digit read as a second line (synthetic only); per-character range calls (about 25 ms per dense case, estimated).

A separate GPT-6.2 Sol analysis named repeated interactions in the intermediate sweep. The jolvex sidecars showed its size: the sweep reran all 4,344 interaction attempts with the same id, target, trigger and result as the base run, 3,477 of 7,356 measured worker-seconds. The sweep now runs none.

While testing, the parent found that a process-tree test counted ten processes of a chat app as driver survivors: the driver had been given the reused id of that app's dead parent. `taskkill /T` follows that stale link, so a hung-driver stop could kill an unrelated program; both tree stops now check creation times.

Final review point on `3cec026c` (`86ca5823` after four commit subjects were reworded; same tree): one GPT-6.1 Sol call per lens (code, flow rules with the version entries, security), run in parallel. Findings and what happened to them:

- The critique, audit and grading receipts carry the whole matrix, and the assessment check wanted one observation per case. This, not the rubric, made every reviewer inspect every capture: the 16-agent jolvex wave. Observations now cover the inspection set and must include each surface at its smallest target (`d359cf46`).
- A recorded high risk could add a third grader without the owner; only an owner request can now (`6192a7e7`).
- A Git error skipped the cited-capture index check; inside a Git checkout it is now a problem. Paths with an apostrophe go to the pathspec-file route (`8c3e3877`).
- The version entries claimed identical rows at any worker count; corrected (`4a07bca3`).
- Process-tree stops still used bare ids after the snapshot, and the packager could confirm a stop whose root had left the list. Each child now ends through a handle whose creation time matches the list, an id a later process took counts as ended and is never touched, and an unlisted root leaves the stop unconfirmed (`7e6a69e0`, `e3b4fffa`).
- `review_input.py --remove` trusted three marker names and followed links. It now refuses a link or junction on the path or inside the packet, a packet holding the working directory or Git treats as a work tree root, and anything but a clone detached at the SHA in HEAD.txt with well-formed markers (`cc08bba3`, `78aa2693`, `a2fc79eb`).
- `ready` trusted the sidecar's capture fields, and a page-open timeout missed the tool-limit route. It now checks every case record against the output's bound captures and this run's file names, and page-open hangs and screenshot errors take the tool-limit route (`e65ac817`, `4d403d65`). With `--recapture-carried` a record keeps both its fresh capture and its `carriedFrom`, as the driver writes it.
Targeted re-check on `d65d6caf` (code and security, in parallel): 11 of the 13 findings resolved or superseded; a process root keeps its id while its Popen handle is open. Still open: observations at only the smallest target built a PASS receipt, though the inspection set includes the axis sample's largest target; a sidecar without its subject or run times reached READY; packet removal deleted a matching checkout holding an unlisted file. One consolidated repair closed them, with two notes: a PASS case needs a fresh or a carried screenshot, and a terminated process counts as ended only once it finishes (`1765027d`, `c873f15f`, `740fb9e3`, `9d99e9d6`).

One scoped review on `9d99e9d6` confirmed those and kept one block: data kept inside `.git`, or in a folder named like a review-input file, was still deleted. The build now lists every file of the packet with its SHA-256, and removal refuses a packet in which anything changed since (`238f7d85`).

The Codex review on PR #207 (`fc1b2de2`) found two more. The two-reviewer bullet had dropped "unless agent policy sets another topology", though AGENTS.md gives worker topology to agent policy; restored (`0a8dc9e5`). The inspection-set check ignored the state, so observing only an error screen at both end targets passed; each surface now needs its default state there (`c2f7a7cb`). Both threads were answered and resolved.

- Not changed: a 0.94.0 parity manifest cannot carry into 0.95.0 because the HiFi carry key changed, so the first parity run after adoption recaptures every entry once; the cited-capture check compares file names with the index, not staged bytes, and a stale staged image fails the hash check in the next checkout.

## Ten-Repository Check And 0.95.1

After the merge the owner asked for a real run on the consumer repositories. 0.95.0 ran on scratch copies of ten repositories (nine UI packages), and seven backends ran in clean clones:

- jolvex's full package took 52.6 minutes with four workers, against 1 h 41 min on 0.94.0. Interaction attempts were 77 to 99 % of measured browser time in every repository.
- A destination that never applied waited the whole 30 s action limit: 276 attempts, about 2.3 worker-hours. 236 were state changes on the source page; 40 were agentkiosk navigations.
- 580 of jolvex's 652 `text-clip` rows were screen-reader-only text: `zoom-200` doubled its 1 px box. Spot checks of the 1,658 `text-split` rows found real wrapping defects; 62 % of the rows sit in twelve shared components.
- Six of seven backends cannot pass their own verification on this machine for environment reasons (pinned Node and Bun, workerd, a Clerk key, CRLF byte checks, wrangler local D1, a hanging `wrangler types`). Most suites take seconds to a minute (jolvex's full `check` takes 15.5 minutes); the time goes to repeated full suites (about 40 in one hk-car-care Epic) and identical trees verified again (agentkiosk RUN-005 to RUN-007). `verification-gates.md` said a repair reuses nothing, while Isolated Repair Protocol step 7 reruns only the failing suites.

Owner decision, 2026-11-19: ship 0.95.1 with the hidden-text fix, a 10 s destination wait and the rule fix. The 10 s figure assumed jolvex's slowest passing attempt (10.98 s) spent under 10 s on its destination. It did not: its source page opens in about 0.56 s, and the navigation into jolvex's `index.html` waited about 10.4 s. So only a destination on the source page gets 10 s, and an attempt that loads a page keeps 30 s. On the measured runs that saves about 1.3 worker-hours instead of 1.5. New browser tests fail against the 0.95.0 wait and against a flat short wait.

The rule fix covers the direct route. Managed RUNs still verify each new head fresh, because the runtime binds every gate PASS to the exact head; reusing a tree across RUNs needs runtime work. Fewer interaction attempts stays the owner's coverage decision.

Review point on `a0d3bddd`: one GPT-6.1 Sol call with the code, rules and security lenses returned `fix_required`. The Codex review of the same head found nothing, and its CI passed.

- R1: the tree reuse contradicted `source-maintenance.md` (same exact SHA only) and `branch-promotion-contract.md` (archive A and main S only). Both now allow it for deterministic suites only, and the gate rule says it covers no review, security, browser, live-state or migration result (`0590f801`).
- R2, reproduced in Chromium with the reviewer's command: the hidden-text rule counted `clip: rect(0 0 0 0)` on any box, so a visible 20 px static button lost its target-size failure. `clip` applies only to absolute and fixed boxes, and now counts only there (`586322c9`).
- R3 (note): both screen-reader fixtures also had a clip, so neither the zoom division nor a clip rule was tested alone. Each new fixture needs one rule, and the text-clip test fails when that rule is removed.

## Verification

- Full Required Verification matrix on `3cec026c` (`86ca5823` after the subject rewording, same tree): 9 of 9 passed on Windows, about 20 minutes.
- After each repair: the affected modules, pyflakes over every script tree and the diff check passed; each new test failed before its repair.
- Pull-request CI on `588008ac`: all 14 checks passed (Linux, macOS, Windows, browser and golden path). The Codex review threads were answered and resolved.
- `promotion_readback.py pre` passed against `main` `0613b863`; PR #207 merged as `61278db1`; `post` returned `tree_equal_S`. Tag `v0.95.0` points at `61278db1`. `./install.sh` exited 0 and the installed contract equals the source: `dac0ed2dd3d2bd0a467b0cad4d74f301a297a7601651ca00b6558e16f2f6960a`.
- 0.95.1: the UI suite passed (36 modules, three browser workers) after the wait change; the doc-asserting Harness modules passed (127 tests); `check_skill_spec.py`, pyflakes, `docs_weight.py` and `prepare_release.py --check` passed. Pull-request CI on `a0d3bddd`: all 14 checks passed. After the repair: the UI suite (36 modules), the measured-accessibility browser tests and 249 contract and document tests passed; the reviewer's R2 command gives the 0.95.0 row again. The full matrix runs as pull-request CI on the repaired head.

## Consumer Impact

Earlier approvals stay valid: an intermediate receipt with every interaction row still passes. Consumers adopt between rounds, never during one. No consumer is pinned above 0.94.0.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / fix/measure-hidden-text-at-zoom / the commit that adds this block / task/ (untracked)
Stage and skill: source maintenance of the skill suite; direct work, no PLAN/RUN
Inputs consumed (path + hash or revision): main 61278db1 (v0.95.0); ten-repository and backend runs of 2026-11-19; owner decision of 2026-11-19
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): current; installed template 82c457c0…, VERSION 0.95.0, bundle dac0ed2d…; the five reported differences (Runtime Boundary, Engineering Principles, Mandatory Governance Routes, Delivery Autonomy, and the omitted Harness Version, Required Reading, Behavior Specs, Skill Bindings and Deployment sections) are this source repository's documented local choices
Approvals in force (gate, owner, date, candidate): owner, 2026-11-19: publish 0.95.1 with the hidden-text fix, the destination wait and the rule fix
Done and verified (command, exit code): UI suite, doc-asserting Harness modules, spec, pyflakes and release checks, exit 0; review point on a0d3bddd and one consolidated repair
Remaining: targeted re-check, CI on the repaired head, merge, tag, install
Blocked / waiting (gate name or owner decision): fewer interaction attempts (owner); removal of this round's worker worktrees and branches and the remote ui-review-speed branch (owner)
Next action (one command or one owner decision): run the targeted re-check of a0d3bddd..HEAD
Next owner (skill or human): parent
```

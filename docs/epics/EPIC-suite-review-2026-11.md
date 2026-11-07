# EPIC-suite-review-2026-11: simplify, template and fill the suite

Status: in_progress

## Problem And Baseline

On 2026-11-07 the owner asked for a review of the whole suite: what can be simplified, what should become a template, and what the architecture and the skills still lack, with the gaps to be filled. A Workflow run (`wf_19618f07-bb2`, 138 agents, Claude Opus 5.5 at effort xhigh, read-only) put eight readers on eight subsystems plus a completeness critic, and one independent refuter on every finding. 93 raw findings and 30 critic-gap findings went in; 91 survived and 32 were refuted. The refuter's refined proposal is the specification for each surviving item; its "existing coverage" list is what must not be duplicated.

Baseline: `feat/bdd-scenarios` at `0974cbe4` (the 0.77.0 candidate `d36c7216` plus its record), stacked on `origin/main` `12eecf90`. This round lands as 0.78.0 after 0.77.0.

Owner direction: writers are Claude Opus 5.5 at effort xhigh via `claude-t3-direct`, one per bounded file set in a T3 worktree; the parent (Claude Fable 5.1) integrates, repairs and reviews.

## Accepted Scope

- Every item in the backlog below with assignment `wave A`, `wave B` or `round 2`. Waves A and B are this Epic; round 2 is a later Epic with the same backlog ids. Items marked `superseded` fold into the item that supersedes them. `M20` is an owner action: land `fix/compact-tracked-files-retention` on `main` before `v0.77.0` is tagged.
- A writer implements the refuter's refined proposal, not the reader's original one, and reads the refuter's existing-coverage list first. When a proposal spans another writer's file, the writer names the exact cross-file edit in its report and the parent applies it.
- Wording rule for every touched section: shorter sentences, no repeated rule, no new word beyond what the rule needs. A test that pins a sentence is updated with the sentence, never deleted. Docs weight per skill must not rise net across the Epic except where a new reference is the item itself.
- Every behavior change ships with a focused test. Scripts keep the UTF-8 `main` block pattern and pyflakes cleanliness.
- Out of scope: owner authority, approval gates, data-safety rules, model or provider policy.

Ambition rung: 2 — a maintainer or consumer no longer re-invents the artifacts the suite already knows the shape of, and a managed run reads about a fifth less before acting.
Outside judge: `docs_reading_budget.py` and the consumer repositories' next adoption, which should need no hand-written packet, release log or attributes file.

## Acceptance And Dependencies

| ID | Expected outcome | Verification | Dependency |
| --- | --- | --- | --- |
| SR-1 | Wave A integrated: every W5, W7, W9, W10 item implemented or explicitly deferred with a reason | affected suites per writer, then the four skill suites on the integrated head | none |
| SR-2 | Wave B integrated: every W6, W8, W11, W12 item implemented or explicitly deferred with a reason | same | SR-1 |
| SR-3 | Managed must-read at the delivery-harness entry drops by at least 8,000 words against `0974cbe4` | `docs_reading_budget.py --skip-section direct-route` before and after | SR-1 |
| SR-4 | Four READMEs describe the new templates and scripts; version 0.78.0 on every surface | `test_skill_contract.py` | SR-2 |
| SR-5 | Full Required Verification matrix green at the candidate | `task/release-0780/matrix-<sha>/summary.txt` | SR-4 |

## Document Impact

| Changed source / requirement | Affected live artifact | Required recheck |
| --- | --- | --- |
| Reference and stage wording | the files each item names | docs weight, reading budget, pinned-sentence tests |
| New templates and scripts | `assets/templates/`, `scripts/`, SKILL inventories, READMEs | skill spec, UTF-8 inventory, focused tests |
| Release surfaces | four READMEs, CHANGELOG, VERSION, package files | `test_skill_contract.py` |

## Backlog

Full text of each item (problem, evidence, refined proposal, existing coverage) is in the parent's brief files; the ids here are the stable reference.

| ID | Category | Title | Value / effort | Assignment |
| --- | --- | --- | --- | --- |
| S1 | simplify | Worker packets are filled in by hand, though the reviewer packet is already rendered by a script | high / M | round 2 |
| S2 | simplify | Anchor the two whole-file reads that managed-delivery.md makes mandatory | high / S | wave A / W5 |
| S3 | simplify | Retire the dead mission runbook template; HARNESS_GOAL still sends the parent to a section new RUNs lack | medium / M | wave B / W6 |
| S4 | simplify | Host, launch and selection rules are restated across five runtime references | medium / M | wave A / W5 |
| S5 | simplify | One-wave/one-re-review/two-scoped-re-review budget and the 85/80 thresholds are restated in six files | medium / M | wave A / W10 |
| S6 | simplify | Compute contrast and type-scale evidence inside the pair checker instead of hand-run commands and hand-copied ratios | medium / M | wave B / W11 |
| S7 | simplify | The README restates detailed review rules in four languages, so nearly every Epic needs a README writer | medium / M | wave B / W12 |
| S8 | simplify | The entry loads two whole gate contracts on every invocation, including docs-only direct work | medium / S | wave A / W5 |
| S9 | simplify | The review budget, re-check packet and reviewer-result rules are restated in seven files | medium / S | wave A / W5 |
| S10 | simplify | The Closeout Bar restates the closeout table and the validator's complete-status checks | medium / S | wave A / W5 |
| S11 | simplify | The checker flag set is restated seven times in four variants; let the package declare its feature files | medium / S | wave A / W9 |
| S12 | simplify | Read only the playbook patterns for the package's own surface classes | medium / S | wave A / W9 |
| S13 | simplify | Three stack guides repeat the status vocabulary, the selection steps and the record checklist | medium / S | wave A / W9 |
| S14 | simplify | review-workflow.md restates the stage's binding, research, Shape and self-review rules | medium / S | wave A / W10 |
| S15 | simplify | Replace hand-assembled sourceBindings and showcase coverage rows with one scaffold command | medium / S | wave B / W11 |
| S16 | simplify | Cut growth-review must-read from about 7,270 to about 5,400 words | medium / S | wave B / W11 |
| S17 | simplify | Remove restated drafting and validation rules that the stage file or the checkers already own | medium / S | wave B / W11 |
| S18 | simplify | The nine-file version bump and CHANGELOG rotation are rewritten as a script each release | medium / S | wave B / W12 |
| S19 | simplify | The source index keeps 15 per-Epic status rows that went stale; released Epics are never closed | medium / S | wave B / W12 |
| S20 | simplify | SKILL.md:93 forces a whole-file read of the 1,701-word promotion contract; only two short sections apply at entry | medium / S | wave A / W5 |
| S21 | simplify | design-input-updates.md is out of date: it treats wireframes as live inputs and renews a gate ui-design/3 does not have | medium / S | wave B / W6 |
| S22 | simplify | The mvp direction/approval/Need Gate rule is written nine times | low / M | wave A / W10 |
| S23 | simplify | Every skill's mandatory delegation read carries the Architecture Method and launch-packet restatements | low / S | wave A / W5 |
| S24 | simplify | The required runtime-upgrade gate carries UI design-round pin and migration rules that belong elsewhere | low / S | wave A / W5 |
| S25 | simplify | The source AGENTS.md omission list names template sections removed a month ago | low / S | wave B / W12 |
| S26 | simplify | Retire the pre-0.66 anchor receipt keys; pinned scripts already own pre-0.66 archives | low / S | wave B / W8 |
| S27 | simplify | Move the Open-Ended Refinement half behind a pointer and give the two row shapes one home | low / S | wave B / W6 |
| T1 | template | No UI_DESIGN.template.md; the ui-design.md skeleton is embedded in a 6,100-word reference with a broken fence | high / M | wave A / W10 |
| T2 | template | 'Current Epic' is never defined; consumers invent prose pointers and keep several live Handoff blocks | high / S | wave B / W6 |
| T3 | template | Branch Promotion record lacks protection, base, mechanism, S and tree fields, and its exact-SHA row contradicts condition 7 | high / S | wave B / W6 |
| T4 | template | Consolidated defect ledger has fields in five places, no location and no template; consumers invent their own schemas | medium / M | wave A / W10 |
| T5 | template | The Epic Handoff block and Change Log lack fields the handoff audit and direct review require | medium / S | wave B / W6 |
| T6 | template | Direct-route review briefs have no template; the packet renderer works only for managed runs | medium / S | wave B / W6 |
| T7 | template | Per-release deployment evidence piles up inside DEPLOYMENT.md because no release record template exists | medium / S | superseded by T12 |
| T8 | template | Move the standard package skeletons out of output-contract.md into templates; a per-artifact split alone saves little | medium / S | wave A / W9 |
| T9 | template | Grader, Impeccable-operator and scoped re-review packets are hand-written every round | medium / S | wave A / W10 |
| T10 | template | Evidence files have no template; ticketradar writes the same machine-readable shape again every round | medium / S | wave B / W6 |
| T11 | template | No seed .gitattributes; consumers hand-write divergent per-run rule lists | medium / S | wave B / W6 |
| T12 | template | No per-release record template; consumers hand-write release logs into DEPLOYMENT.md and ad-hoc docs/release folders | medium / S | wave B / W6 |
| T13 | template | Direct-route assignment packets have no template; hk-car-care hand-wrote 52 TASK.md with drifting sections | medium / S | wave B / W6 |
| T14 | template | The JSON template still targets design-system/3 with ds-showcase/1, and lacks the font and theme groups consumers always add | low / S | wave B / W11 |
| M1 | missing | Capture tooling stops at the case matrix; interactions, reviewer object, intermediate widths and motion receipts are still hand-built per project | high / L | round 2 |
| M2 | missing | No guarded transition records authorization grants, readiness or closeout, so parents hand-edit RUN JSON | high / M | round 2 |
| M3 | missing | No script builds the verifier_runtime request for task, worker or integration checks | high / M | round 2 |
| M4 | missing | Opening, revising and closing a RUN are still hand edits to the JSON | high / M | round 2 |
| M5 | missing | An AI package cannot satisfy eval-policy/1 and --features together | high / M | wave B / W8 |
| M6 | missing | The BDD runner layer and the 'architecture testing section' have no home outside CLI products | high / M | wave A / W9 |
| M7 | missing | First-Wave Audit Axes and the matrix driver's --axes disagree | high / M | round 2 |
| M8 | missing | One acceptance profile cannot express a register that mixes local and deployed scenarios | high / M | superseded by M11 |
| M9 | missing | Template audit is a by-meaning read of AGENTS.md only; the script reports noisy hashes and DOCUMENTS.md drifts unchecked | high / M | wave A / W7 |
| M10 | missing | Nothing builds delivery-results.json; every row's identity is hand-copied from the register | high / M | wave B / W8 |
| M11 | missing | One run profile cannot describe a mixed-platform matrix, so result rows must repeat a false device and build | high / M | wave B / W8 |
| M12 | missing | No suite-wide owner for storing hash-bound records byte for byte | high / M | wave B / W6 |
| M13 | missing | Attributes are checked only at H2; run a read-only git check-attr at entry | high / M | wave A / W7 |
| M14 | missing | No read-only command proves main pre-state, frozen-base ancestry and tree equality of server-created main S | high / M | round 2 |
| M15 | missing | parity_capture.py cannot drive the ui-hifi/2 HiFi package it is supposed to compare against | high / M | round 2 |
| M16 | missing | The default ui-design/3 path never compares the implementation with the approved HiFi | high / M | round 2 |
| M17 | missing | Each Handoff rewrite makes document-sync report drift, so consumers commit a baseline refresh every time | high / S | wave A / W7 |
| M18 | missing | Successor-review-generation rules contradict the rule that a failed re-check ends the budget | high / S | wave A / W5 |
| M19 | missing | The security result validator has no CLI, so direct-route results are checked by hand | high / S | wave A / W7 |
| M20 | missing | The fix that shrinks verifier records in RUN.md is not on the 0.77.0 line, so RUN.md grows to tens of MB again | high / S | owner action |
| M21 | missing | Rubric tells the parent to write a 20-item `UI grading:` line; the checker accepts only a receipt pointer | high / S | wave A / W10 |
| M22 | missing | Output contract and agent prompt contradict the mvp profile and the checker | high / S | wave A / W10 |
| M23 | missing | New managed PLANs must declare the acceptance gate, but the validator checks this only under eval adoption | medium / M | round 2 |
| M24 | missing | Owner-approved feature files are left out of the approval presentation, the independent review and the approval binding | medium / M | wave A / W9 |
| M25 | missing | No script runs the required matrix locally; the documented block skips browser tests and checks no diff | medium / M | wave B / W8 |
| M26 | missing | Task-level verifier requests are hand-built; consumers ship their own helper and workers get it wrong | medium / M | wave B / W8 |
| M27 | missing | Hash mismatch messages hide line-ending conversion and point to the wrong repair | medium / M | wave B / W6 |
| M28 | missing | Entry context command runs in write mode, the entry checklist omits it, and the handoff audit compares by hand | medium / S | wave A / W5 |
| M29 | missing | No rule owns the consumer bundle-adoption procedure, so every release brief restates it | medium / S | wave B / W6 |
| M30 | missing | The Readiness card leaves out the Environment Preflight, a readiness blocker | medium / S | wave A / W5 |
| M31 | missing | Nothing proves the frozen register still matches the feature files it was rendered from | medium / S | wave A / W7 |
| M32 | missing | Profile tags are neither validated nor required at approval, and surface classes have no platform mapping | medium / S | wave A / W9 |
| M33 | missing | Surface Lenses has no row for macos, windows and linux, and no test keeps it in sync with the Surface Catalog | medium / S | wave B / W11 |
| M34 | missing | Discovery RA-* candidates don't fit the research-assessment schema they are handed to | medium / S | wave B / W11 |
| M35 | missing | MESSAGING.md names growth-review and readme-studio as readers, but neither reads it | medium / S | wave B / W11 |
| M36 | missing | Every release re-pins 19 consumers with a new one-off script; no bundle script does the mechanical adoption | medium / S | wave B / W8 |
| M37 | missing | No install output gives the five-skill contract digest, and harness_contract.py silently ignores its arguments | medium / S | wave A / W7 |
| M38 | missing | Feature files must be frozen in PLAN sources, but the PLAN template and validator ignore them | medium / S | wave A / W7 |
| M39 | missing | No rule keeps parent bookkeeping commits off the run branch before the first integration | medium / S | wave A / W5 |
| M40 | missing | Existing registers have no path to feature files, and the merged Behavior Specs rule contradicts them | medium / S | wave B / W6 |
| M41 | missing | No write-scope checklist, so PLANs are revised repeatedly to cover tests, config, generator output and scaffold leftovers | medium / S | wave B / W6 |
| M42 | missing | The Wrangler section misses the Vite-plugin redirected-config trap that deploys the dev Worker as production | medium / S | wave B / W6 |
| M43 | missing | visual_inputs.py cannot read the compiler's derived preview above 32 MiB, so its freshness check is skipped | medium / S | wave A / W10 |
| M44 | missing | The BDD runner layer exists only in the CLI and Toolchain table, yet web and native scaffolds install it | medium / S | wave A / W9 |
| M45 | missing | Release Target Status has no state between store upload and availability, and upload-only evidence can pass as PASS | medium / S | wave B / W6 |
| M46 | missing | Promotion step 9 and release outcome assume production can be verified in the same session | medium / S | wave B / W6 |
| M47 | missing | Rules kept in .git/info/attributes do not reach the clean clones the suite relies on | medium / S | wave B / W6 |
| M48 | missing | Condition 2 has no stated outcome when the host refuses the protection readback | medium / S | wave B / W6 |
| M49 | missing | JSON token values are never checked against the approved HiFi CSS | low / S | wave B / W11 |
| M50 | missing | growth-review's two output contracts disagree: the stage requires a Handoff block and PRD delta candidates the Default Output skeleton lacks | low / S | wave B / W11 |

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Epic opened with the verified backlog | 91 surviving findings from `wf_19618f07-bb2`, assigned to two waves, round 2, superseded or owner | `2389a383` | none |
| W10: ui-design-builder | S5, S14, S22, T1, T4, T9, M21, M22, M43: budget and thresholds stated once, three new templates, mvp alignment, uncapped preview read | `d94fc68e`..`131c8594`, fast-forwarded | udb suite 451 tests exit 0; harness doc modules exit 0; udb must-read 32,758 to 30,990 |
| W5: delivery-harness references | S2, S4, S8, S9, S10, S20, S23, S24, M18, M28, M30, M39: anchored managed reads, one owner per restated rule, Card 8, `architecture-method.md`, read-only entry check, readiness preflight | `d5bada44`..`84ae9bc5`, merged at `1a1602f9`; parent cross-file edits `cb2521f2` | nine doc modules exit 0; managed must-read 41,245 to 28,543 |
| W7: delivery-harness scripts | M19, M31, M17, M37, M38, M13, M9: security result CLI, render `--check`, Handoff left out of document-sync hashes, contract digest CLI and installer line, frozen feature-file PLAN rows, byte-attribute and diff output in the context check | `755a5103`..`2845c719`, merged at `9df9e298`; parent cross-file edits `54906acb` | harness suite 112 modules exit 0 on the worker branch; golden path and installer tests exit 0 |
| W9: product-definition-builder | S11, S12, S13, T8, M6, M44, M24, M32: coverage from the PRD's own pointer line, anchored playbook reads, one status rule for the stack guides, skeletons out of the output contract, BDD runner rows, `Feature files` approval digest, validated profile tag values | `8d49e8f0`..`d1fa2cc0`, merged at `4c3127a0`; parent deferred edits `146947ee` | pdb suite 440 tests exit 0; dsc suite exit 0 after the one-line test fix; pdb must-read 41,475 to 37,919 |

## Results And Remaining Work

- Wave A integrated at `146947ee`: 36 backlog items done, none skipped. Parent review of the four diffs found no blocking finding; the review notes are in the Change Log rows.
- Decisions taken in wave A: the entry runs `configure_project_context.py --check --merge-agents` and the readiness card runs `--check --require-resolved`; `--check` on the renderer is named in Card 2 and the acceptance contract, not in SKILL.md, which sits one word under its cap; the PLAN template carries a feature-file source row but no acceptance-profile row (the frozen register embeds the profile); the package checker requires one BDD runner row anywhere, not one per table; the renderer and the reader share one profile vocabulary, pinned by `test_profile_tag_vocabulary.py`.
- Entry must-read after wave A: delivery-harness 31,076 (from 43,863), product-definition-builder 37,641 (from 41,185), ui-design-builder 30,794 (from 32,758). Docs weight 189,855 against 193,298 at v0.76.0.
- Left for wave B or later: step 9 of the product-definition stage still reads `output-contract.md` whole (13,188 words); the READMEs do not yet name the new templates, flags and Card 8.
- Wave B (W6 references and templates, W8 scripts, W11 design-system-compiler, growth-review and standalone skills, W12 cross-cutting and READMEs) follows; then the 0.78.0 bump and the full matrix.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / feat/suite-review-r1 / 146947ee plus this record / task/ untracked
Stage and skill: source maintenance, managed topology by hand (delivery-harness governance)
Inputs consumed (path + hash or revision): workflow result wf_19618f07-bb2; feat/bdd-scenarios 0974cbe4; source-maintenance.md, delegation-contract.md, commit-convention.md at that revision
Approvals in force (gate, owner, date, candidate): owner direction 2026-11-07 to review the suite and fill the verified gaps with Opus 5.5 xhigh writers and Fable 5.1 review; local branches, worktrees and commits; no push, tag, install or release
Done and verified (command, exit code): wave A at 146947ee: pdb suite 440 tests, udb suite 451 tests, dsc suite, and the harness doc, template, anchor, render, document-sync, context and security-result modules (exit 0); check_skill_spec.py, docs_weight.py, docs_reading_budget.py, git diff --check (exit 0); harness suite 112 modules exit 0 on W7's branch
Remaining: wave B, integration, review, 0.78.0 bump, full matrix at the candidate; round 2 Epic for the heavy items
Blocked / waiting (gate name or owner decision): owner action M20 (land fix/compact-tracked-files-retention before v0.77.0)
Next action (one command or one owner decision): launch W6, W8, W11, W12 from this commit
Next owner (skill or human): harness parent
```

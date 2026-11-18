# EPIC-entry-route-split: a direct task reads only what its route needs

Status: in_progress
Design workflow: enhancement
UI impact: none

## Problem And Baseline

Two independent reviews (Claude Fable 5.2 and GPT-6.2 Astra, 2026-11-18) compared the Harness with the PStack plugin and agreed on one cost: the `delivery-harness` entry named 26,445 words as required reading for every task. Between 4,700 and 9,600 of those words serve only managed PLAN/RUN work, and between 5,300 and 6,000 serve only UI changes. The entry file already told direct work to skip the managed stage file, but its clauses were worded as obligations, so neither the reading-budget tool nor a careful agent could tell which reads were conditional.

Baseline: `main` `a0d3bbe8` (v0.90.1). `docs_reading_budget.py`, `delivery-harness` row: own 1,999, mandatory 24,446, must-read 26,445.

This is round one of three the owner approved on 2026-11-18. Round two adds an Epic-level landing grant. Round three adds evidence-carrying review findings, an on-demand second reader and the engineering principles.

## Accepted Scope

Owner decision, 2026-11-18: three rounds, one theme and one PR each. Round one cuts reading load and changes no rule, authorization or gate.

- ER-1: the direct steps move out of `SKILL.md` into `references/stages/direct-cards.md`. Card D1 serves every direct task. Card D2 is added only for an `initial_delivery`. Card D3 is added only when the task changes UI.
- ER-2: clauses in the entry file that apply only to managed runs or only to UI work state that trigger.
- ER-3: `docs_reading_budget.py` reports each direct card as an entry, and a test caps the direct route.
- ER-4: the Gitignore contract is read only when a task introduces or retires a local-only file class.
- ER-5: a script checks a commit message, so the commit convention is read when the check fails, not before every commit.

Not done in this round, with the reason:

- The hand-written flag list under `execution-state-model.md` "Scripted Transition Flag Surfaces" (648 words) stays. It is managed-only, a stage card already names it as a read-on-failure, and it carries constraints beyond the parser's flag names. Removing it would not shorten the direct route.
- The review order repeated between `gen-verify-correct.md` and the direct steps stays. The steps now sit in Card D1, and the saving was estimated at 150 to 250 words.

Ambition rung: 1 — the direct route's required reading drops below 5,000 words.
Outside judge: `docs_reading_budget.py` on the candidate, and the ceiling test in `test_docs_reading_budget.py`.

## Acceptance And Dependencies

| ID | Expected outcome | Verification | Dependency |
| --- | --- | --- | --- |
| ER-1 | `SKILL.md` names the three cards with their triggers and holds none of the direct steps; D1 names no UI or initial-product contract | `test_skill_contract.py::test_direct_route_reads_only_the_cards_its_task_needs` | none |
| ER-2 | No rule text is lost: every phrase the contract tests pinned is still asserted, in the entry file or in the card it moved to | `test_skill_contract.py` (three assertions now read the card) | ER-1 |
| ER-3 | `direct-cards#...` rows appear in the report; entry file plus D1 stays under 5,000 words, D2 and D3 under 3,500 each | `test_docs_reading_budget.py` | ER-1 |
| ER-4 | The System Review still records `Gitignore impact`; the contract is named with its trigger | `test_skill_contract.py` | none |
| ER-5 | The script rejects each malformed subject with a message that states the fix; the Git rules name the script | `test_check_commit_message.py`, `test_governance_entry_routes.py` | worker commit |

## Measured Result

`docs_reading_budget.py`, words. "Must-read" is the entry's own words plus every link its wording makes mandatory, two levels deep. It is a static count from the wording, not a record of what an agent opened.

| Route | Before (`a0d3bbe8`) | After (`5e5bcbf3`) |
| --- | --- | --- |
| Direct task, no UI (entry file + Card D1) | 26,445 | 3,828 |
| Add-on for an initial delivery (Card D2) | included above | 2,861 |
| Add-on for a UI change (Card D3) | included above | 2,670 |

Reads that fire on a trigger are not in these numbers. The common ones for a direct task: `delegation-contract.md` when the parent assigns the work to another executor (1,558 words), `gen-verify-correct.md` when a review returns findings (813), and the promotion sections of `branch-promotion-contract.md` when the task lands on `main`.

Total normative words rose by 210 (`docs_weight.py`: 205,514 to 205,724): the new card file's lead paragraph and the trigger wording.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Direct steps moved to three cards; managed and UI reads state their trigger | ER-1, ER-2, ER-4. `SKILL.md`, `references/stages/direct-cards.md`, `direct-fan-out.md`, `governance/task-and-handoff.md`, `pre-delivery-self-review.md`, `test_skill_contract.py` | `7ada5b6f` | Doc-asserting modules pass (181 tests). Review pending. |
| Reading budget measures direct cards and caps the route | ER-3. `docs_reading_budget.py`, `test_docs_reading_budget.py` | `5e5bcbf3` | 37 tests pass; `test_install_script.py` passes once the card file is tracked. |

## Results And Remaining Work

Remaining: ER-5 (worker in a separate worktree), the Git-rule wording that names the script, release preparation for 0.91.0, one review point on the candidate, CI matrix on the PR.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / entry-route-split / 5e5bcbf3 / task/ (untracked, not part of this round)
Stage and skill: source maintenance of delivery-harness; direct work, no PLAN/RUN
Inputs consumed (path + hash or revision): main a0d3bbe8 (v0.90.1); owner-approved plan of 2026-11-18
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): unknown; not run in this round
Approvals in force (gate, owner, date, candidate): plan approval, owner, 2026-11-18: three work branches, local commits, push and PR. Merge to main, tag, install and consumer adoption are not approved.
Done and verified (command, exit code): pytest on the doc-asserting modules, exit 0; docs_reading_budget.py, exit 0
Remaining: ER-5, release preparation, review, PR
Blocked / waiting (gate name or owner decision): none
Next action (one command or one owner decision): integrate the worker's check_commit_message.py commit
Next owner (skill or human): parent agent
```

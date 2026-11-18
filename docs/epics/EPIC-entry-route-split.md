# EPIC-entry-route-split: a direct task reads only what its route needs

Status: published as 0.91.0 on 2026-11-18 (PR #201, `main` `a3b547dd`, tag `v0.91.0`); installed the same day (five-skill contract `97e2afba…`); consumers not yet adopted
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
- ER-5: a script checks a commit message, so the message rules of the commit convention are read when the check fails. Atomic Boundary, which no script can check, is still read before every commit.

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
| ER-5 | The script rejects each malformed subject with a message that states the fix; the Git rules name the script and keep the Atomic Boundary read | `test_check_commit_message.py`, `test_governance_entry_routes.py` | worker commit |

## Measured Result

`docs_reading_budget.py`, words. "Must-read" is the entry's own words plus every link its wording makes mandatory, two levels deep. It is a static count from the wording, not a record of what an agent opened.

| Route | Before (`a0d3bbe8`) | After (`1aa2be47`) |
| --- | --- | --- |
| Direct task, no UI (entry file + Card D1) | 26,445 | 3,828 |
| Add-on for an initial delivery (Card D2) | included above | 2,861 |
| Add-on for a UI change (Card D3) | included above | 2,670 |

Reads that fire on a trigger are not in these numbers. The common ones for a direct task: `delegation-contract.md` when the parent assigns the work to another executor (1,558 words), `gen-verify-correct.md` when a review returns findings (813), and the promotion sections of `branch-promotion-contract.md` when the task lands on `main`.

Total normative words rose by 317 (`docs_weight.py`: 205,514 to 205,831): the new card file's lead paragraph, the trigger wording and the sentences that name the commit check.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Direct steps moved to three cards; managed and UI reads state their trigger | ER-1, ER-2, ER-4. `SKILL.md`, `references/stages/direct-cards.md`, `direct-fan-out.md`, `governance/task-and-handoff.md`, `pre-delivery-self-review.md`, `test_skill_contract.py` | `7ada5b6f` | Doc-asserting modules pass (181 tests). Review pending. |
| Reading budget measures direct cards and caps the route | ER-3. `docs_reading_budget.py`, `test_docs_reading_budget.py` | `5e5bcbf3` | 37 tests pass; `test_install_script.py` passes (50 tests). |
| Commit message check | ER-5. `check_commit_message.py` and its tests, written by a GLM-5.3 worker in its own worktree; the parent added the script to the CLI inventory in `test_cli_utf8_output.py`, which the worker's brief did not let it edit | `6696fbba` | 45 tests pass; the script accepts every commit on this branch. |
| Git rules name the check | ER-5. `governance/source-maintenance.md`, `governance/managed-delivery.md`, `commit-convention.md`; the route rows in `AGENTS.md` and `PROJECT_AGENTS.template.md` drop the unconditional convention link | `1aa2be47` | Doc-asserting modules pass (282 tests). Consumers see the template row as a difference at their next adoption. |

## Review And Repairs

One review point on `dac27345`, code and security in one read-only call (GPT-6.1 Sol, effort high, 348 s). Verdict FIX_REQUIRED, five blocking findings, each with a reproduction. The route split itself had no finding: the reviewer found no lost rule in the moved steps, no weaker assertion, and no broken target among 108 references.

| Finding | Repair |
| --- | --- |
| Reading the convention only on a failed check dropped the rules no script checks, such as inspecting the staged diff and adding a new variable to `.env.example` in the same commit | The Git rules again require reading Atomic Boundary before every commit; only the message rules wait for a failed check (`4654386e`) |
| Any subject starting with `Merge ` passed every check, also with `--managed` | A message file is never exempt. With `--rev` and without `--managed`, only a commit with two or more parents passes as a merge (`0b67aaf3`) |
| A scope with an underscore was rejected, a restriction the convention did not have | Underscores are allowed, and the convention now states the allowed characters (`0b67aaf3`, `4654386e`) |
| `feat(auth):add login` passed without the space after the colon | The missing space is an error (`0b67aaf3`) |
| An empty `BREAKING CHANGE:` line counted as the required paragraph | The marker needs text after it (`0b67aaf3`) |

Each script repair has a test that failed before it.

Targeted re-check on `9fe53b3c` (same reviewer, 149 s): all five findings resolved; one more defect inside the repair range. With `--rev --managed`, a two-parent commit whose message carried task trailers still passed, because the trailer set was chosen from the subject alone. Isolated repair `fc47a98f`: a managed merge needs the mission-level trailers and no Task trailer, whatever its subject says. Scoped review of that repair on `7615ece7` (101 s): PASS, security lens not applicable (git invocation and file reads unchanged). Note, not blocking: the real-merge tests do not cover a mission body that also carries a Task trailer; the reviewer confirmed that case is rejected.

CI on `9fe53b3c` (PR #201): the `quality` job failed on pyflakes, two `skill` locals left unused in `test_skill_contract.py` after their assertions moved to the card file. Removed in `c8b5a673`. The parent had run pyflakes on the changed scripts but not on that test file.

Pull-request review (Codex, on `9fe53b3c`), one P2: the Git rules required `--managed` for every commit inside a managed run, but a bookkeeping commit of coordination files has no task trailers (`test_close_wave.py` creates `chore(run): checkpoint wave bookkeeping`), so a required checkpoint could not pass the check. Repair: the rules name `--managed` for task, repair and integration commits only; a bookkeeping commit uses the plain check. The script is unchanged apart from its help text.

## Results And Remaining Work

CI on `c138746c`: all 14 jobs pass. The owner approved the merge, tag and installation on 2026-11-18. PR #201 merged as `a3b547dd`; `promotion_readback.py post` reports `tree_equal_S` against candidate `c138746c`. Installed contract `97e2afbae5faadd46a8fd93b3602bdb916f803a88eb154aadbfae9b44736b2ca`, replacing `a355924c…`; prior copies are under `~/.agents/skill-backups/product-delivery-harness/20261118-045731/`.

Remaining: consumer adoption of 0.91.0, which no one has asked for yet. The route-table row in `PROJECT_AGENTS.template.md` shows as a difference in each consumer at its next adoption.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / main / a3b547dd / task/ (untracked, not part of this round)
Stage and skill: source maintenance of delivery-harness; direct work, no PLAN/RUN
Inputs consumed (path + hash or revision): main a0d3bbe8 (v0.90.1); owner-approved plan of 2026-11-18
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): unknown; not run in this round
Approvals in force (gate, owner, date, candidate): none open; merge, tag and install were approved and done on 2026-11-18
Done and verified (command, exit code): CI matrix on c138746c, 14 of 14 pass; promotion_readback.py post, PASS; install.sh, exit 0; installed harness_contract.py digest equals the source digest
Remaining: consumer adoption
Blocked / waiting (gate name or owner decision): consumer adoption waits for the owner
Next action (one command or one owner decision): none for this Epic; round two continues in EPIC-epic-landing-grant
Next owner (skill or human): owner
```

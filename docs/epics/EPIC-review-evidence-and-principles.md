# EPIC-review-evidence-and-principles: findings carry proof, a second reader on demand, and the principles in AGENTS.md

Status: candidate prepared as 0.93.0; re-check and PR pending
Design workflow: enhancement
UI impact: none

## Problem And Baseline

Round three of the three approved on 2026-11-18. Four things were left from the comparison with the PStack plugin:

- A reviewer could return a blocking code finding that nobody had run. The repair loop then chased it. The security lens already required source-to-sink validation; the code lens required nothing of the kind.
- The owner asked for multi-model review. Both independent reviews of the idea agreed it should be on demand, and that model choice belongs to agent policy, not to a shared skill.
- The owner asked for the PStack principles in every repository's `AGENTS.md`, in full. Both reviews advised a shorter form; the owner chose the full text.
- A correction the owner gives twice was answered by adding a rule. Nothing fails when an agent skips a rule.

Baseline: `main` `82d91fad` (v0.92.0). Earlier rounds: [EPIC-entry-route-split](EPIC-entry-route-split.md), [EPIC-epic-landing-grant](EPIC-epic-landing-grant.md).

## Accepted Scope

Owner decisions, 2026-11-18: a second model reads on demand, not at every review point; all 24 principles go into `AGENTS.md` in full.

- RE-1: a blocking code finding carries its proof: the command or input, the observed result and the required result. A reviewer that cannot run code still reports it as blocking, marked `unrun`, with the exact command; the parent runs it before it accepts any verdict. Only a finding with no command or input at all is a note. The review packet says so.
- RE-2: a second reader from another vendor joins the same review point when the diff touches a trust boundary or the owner names a contested design. It adds no review pass. Agent policy names the executor; a missing one is recorded, not substituted.
- RE-3: `PROJECT_AGENTS.template.md` and this repository's `AGENTS.md` gain `## Engineering Principles` with the 24 PStack principles: title, when it applies, text. The section grants no action and yields to every rule. The MIT license and the source commit are recorded in `assets/third-party/PSTACK-LICENSE`.
- RE-4: the handoff audit asks that a repeated correction be fixed at the highest level that works: structure, a check, a test, and a rule last.

Not in this round: a read-only review route for a second vendor in the owner's T3 profile guard, which lives outside this repository; a blind eval of skill changes; a hillclimb loop for open-ended refinement.

Ambition rung: 1 — the four rules are stated once, each with a test.
Outside judge: one independent review of the candidate; the principles section compared with the pinned PStack copy by `test_project_template_rules.py`.

## Acceptance And Dependencies

| ID | Expected outcome | Verification | Dependency |
| --- | --- | --- | --- |
| RE-1 | The rule is in Review Topology and in the packet; security and visual findings keep their own evidence rules | `test_skill_contract.py::test_blocking_findings_carry_proof_and_a_second_reader_adds_no_pass`, `test_review_recheck_packet.py` | none |
| RE-2 | The second reader is on demand, another vendor, inside the one review point, and never a model named by the skill | the same test | none |
| RE-3 | The section in the template equals the one in `AGENTS.md`; 24 distinct entries in five groups; no pointer to a PStack-only skill; Never Block on the Human states its limit; the license file names the author and the commit | `test_project_template_rules.py::test_repo_instructions_cover_every_shared_template_section` | none |
| RE-4 | The order is stated once, in the handoff audit | `test_skill_contract.py::test_a_repeated_correction_is_fixed_at_the_highest_level_that_works` | none |

## Measured

- The principles section is 3,215 words. `AGENTS.md` in this repository goes from about 890 to 4,103 words, the project template from about 1,610 to 4,827. Every agent session in a repository that adopts the template reads those words. This is the cost the owner accepted; round one cut the direct route by about 22,600 words.
- Direct-route required reading, `docs_reading_budget.py`: 3,890 to 4,173 words. The two new paragraphs sit in Review Topology, which every direct task reads. The ceiling test allows 5,000.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Repeated corrections | RE-4. `governance/task-and-handoff.md` | `aa02f37c` | Contract test passes. |
| Proof for blocking findings; second reader | RE-1, RE-2. `verification-gates.md`, `delegation-contract.md`, `render_review_packet.py`, the four READMEs | `4eec4f08` | Doc-asserting modules and the packet tests pass. |
| Engineering Principles | RE-3. `PROJECT_AGENTS.template.md`, `AGENTS.md`, `assets/third-party/PSTACK-LICENSE` | `23fe2bd5` | Template tests pass. Built by a script from the pinned copy at `cursor/plugins` `93b916d4`; two sentences replaced, one limit added. |

## Review And Repairs

One review point on `cd65dfb5`, code and security in one read-only call (GPT-6.1 Sol, effort high, 319 s). Verdict FIX_REQUIRED with one blocking finding. The reviewer compared all 24 principle entries with their PStack originals and found only the three stated changes; it found the full MIT license present, no principle that overrides a Harness rule under the section's precedence sentence, no extra review pass and no named model in the second-reader rule, and the packet line in the right place for every packet form.

The finding: RE-1 said a code finding without an observed result is a note. A reviewer that cannot run code can only give the command, so a real defect became a note, and a PASS with notes could be accepted with the command never run. Repair `22f7810b`: such a finding stays blocking and is marked `unrun`; the parent runs every `unrun` command before it accepts the verdict, PASS included; a command nobody can run stays open as an unavailable check. Only a finding with no command or input at all is a note.

Two notes from the same review, taken in the same commit: the consolidated-repair sentence now names the second reader as the exception to "parallel reviewers only on an owner request"; the principles text is pinned by its SHA-256 and the two opening paragraphs are compared, since the earlier test compared only the two local copies from `### Core` on.

Targeted re-check: pending.

## Results And Remaining Work

Remaining: the targeted re-check, PR, CI matrix. Merge, tag and install wait for the owner.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / review-evidence-and-principles / 23fe2bd5 / task/ (untracked, not part of this round)
Stage and skill: source maintenance of delivery-harness; direct work, no PLAN/RUN
Inputs consumed (path + hash or revision): main 82d91fad (v0.92.0); owner-approved plan of 2026-11-18; PStack at cursor/plugins 93b916d4
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): unknown; not run in this round
Approvals in force (gate, owner, date, candidate): plan approval, owner, 2026-11-18: work branch, local commits, push and PR. Merge, tag and install for this round are not yet approved.
Done and verified (command, exit code): pytest on the doc-asserting modules, exit 0; pyflakes on the four script trees, exit 0
Remaining: release preparation, review, PR
Blocked / waiting (gate name or owner decision): none
Next action (one command or one owner decision): prepare the 0.93.0 release entries
Next owner (skill or human): parent agent
```

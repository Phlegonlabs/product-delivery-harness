# EPIC-epic-landing-grant: one owner approval covers an Epic's push, merge, deployment and cleanup

Status: candidate prepared as 0.92.0; review and PR pending
Design workflow: enhancement
UI impact: none

## Problem And Baseline

The owner wants an agent to finish an Epic without stopping to ask at each Git step, so that code can land overnight. The promotion contract made that impossible by wording, not by any gate: condition 5 of Promote To Main and the archive publication rule both require an instruction that names the exact SHA, and a SHA exists only after the work is done. Push, merge, branch deletion and worktree removal each waited for a new instruction.

Two independent reviews (Claude Fable 5.2 and GPT-6.2 Astra, 2026-11-18) agreed on the cut. Autonomy belongs to an Epic and an action, not to a project's age. The owner approves how the candidate will be identified; the parent binds that approval to the real SHA when it acts. A candidate must not be able to edit its own grant or its own required checks.

Baseline: `main` `a3b547dd` (v0.91.0). This is round two of three approved on 2026-11-18; round one is [EPIC-entry-route-split](EPIC-entry-route-split.md).

## Accepted Scope

Owner decisions, 2026-11-18:

- A grant covers commit, push, pull request, merge to `main`, production deployment with its smoke, and deletion of the merged work branch and its worktrees.
- A grant also covers bot review threads. The owner first left this out and added it later the same day: fix a confirmed finding or post a concrete disproof, reply, resolve, read the state back.
- Rounds are published one at a time.

Included:

- LG-1: the rule. `branch-promotion-contract.md` gains `## Epic Landing Grant`; condition 5 and the publication rule accept a passing grant check in place of the SHA-naming instruction. No gate changes.
- LG-2: repository eligibility. `PROJECT_AGENTS.template.md` and this repository's `AGENTS.md` gain `## Delivery Autonomy`, default `Landing: owner_each_time`. The parent reads it from the frozen `main` base.
- LG-3: `scripts/landing_gate.py` with `record`, `revoke`, `check` and `cleanup-plan`. It is offline, performs no action and never writes inside the checkout.
- LG-4: the standing cleanup exception, limited to the commands `cleanup-plan` prints.

Kept unchanged: every review, security, acceptance, Preview and read-back gate; the 12 ledger keys; a managed RUN closing `local_only` at C with `push` false; the C-to-A archive receipt; legacy pins; no force-push.

Always the owner's: product scope and PRD changes, a changed visual direction, spending and paid resources, external console setup, destructive data operations and migrations, protection or ruleset exceptions, and owner-only paths (`AGENTS.md`, `CLAUDE.md`, CI workflow files, plus what the repository lists).

Not in this round: choosing a pilot repository and setting it to `epic_grant`. That needs the repository's CI coverage and protection rules read first, and it is the owner's decision. This source repository is seeded at `owner_each_time`.

Ambition rung: 2 — an eligible repository lands an Epic end to end on one owner approval.
Outside judge: `test_landing_gate.py` refusing each attack the reviews named (wrong repository, stale head, expiry, revocation, a policy edited on the candidate), and one independent review of the candidate.

## Acceptance And Dependencies

| ID | Expected outcome | Verification | Dependency |
| --- | --- | --- | --- |
| LG-1 | The section states the two conditions, the six actions, the order, what stays the owner's and the managed-RUN limits; every pointer resolves | `test_skill_contract.py::test_epic_landing_grant_replaces_the_sha_instruction_and_no_gate`, `test_governance_entry_routes.py` | none |
| LG-2 | A seeded repository starts at `owner_each_time`; this repository states its own policy | `test_skill_contract.py`, `test_project_template_rules.py` | none |
| LG-3 | `check` passes a valid grant and refuses: hash mismatch, revoked, expired, action not granted, wrong repository, stale head, base not an ancestor, policy not `epic_grant`, policy changed only on the candidate, an owner-only path, a missing or failed required check, checks for another SHA, a review that is not PASS or binds an older code state, failed acceptance, a deployment without a passing read-back | `test_landing_gate.py` | worker commit |
| LG-4 | `cleanup-plan` plans a merged branch and its clean linked worktree; refuses a dirty worktree, a branch that moved, the primary checkout and a protected branch; no planned command holds a force flag | `test_landing_gate.py` | worker commit |

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Rule text, templates and pointers | LG-1, LG-2, LG-4. `branch-promotion-contract.md`, `SKILL.md`, `stages/direct-cards.md`, `stages/stage-cards.md`, `trusted-host-publication.md`, `direct-fan-out.md`, the three governance files, `EPIC.template.md`, `PROJECT_AGENTS.template.md`, `AGENTS.md`, the four READMEs | `4c403761` | Doc-asserting modules pass (241 tests). Direct route must-read 3,828 to 3,878 words; the grant section is read only when an Epic records a grant. |

| Landing gate script | LG-3, LG-4. `landing_gate.py` (record, revoke, check, cleanup-plan) and 51 tests, written by a GLM-5.3 worker in its own worktree | `8e7b9ff7` | 51 tests pass; pyflakes clean on the four script trees. |
| Parent inspection before review | Four gaps the parent found by reading the script. It refused every ssh remote of the form `git@host:owner/repo.git` as a credential, although the shared push-URL helper already accepts a passwordless ssh identity and rejects a password. A renamed owner-only file showed only its new name and passed the owner-only check. A failed diff read as "nothing changed". A merge check with no `--evidence` raised instead of refusing. The review carry-forward also accepted any `.md` path, which in this repository includes rule text; it now accepts only `docs/` and top-level `README*.md` and `CHANGELOG.md` | `8c93cd64` | 55 tests pass, four of them new. |

## Results And Remaining Work

Remaining: one review point, PR, CI matrix. Merge, tag and install wait for the owner, because this repository's own policy is `Landing: owner_each_time`.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / epic-landing-grant / release commit for 0.92.0 / task/ (untracked, not part of this round)
Stage and skill: source maintenance of delivery-harness; direct work, no PLAN/RUN
Inputs consumed (path + hash or revision): main a3b547dd (v0.91.0); owner-approved plan of 2026-11-18
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): unknown; not run in this round
Approvals in force (gate, owner, date, candidate): plan approval, owner, 2026-11-18: work branch, local commits, push and PR. Merge, tag and install for this round are not yet approved.
Done and verified (command, exit code): pytest on the doc-asserting modules and test_landing_gate.py, exit 0; pyflakes on the four script trees, exit 0; prepare_release.py --check, exit 0
Remaining: review, PR, CI matrix
Blocked / waiting (gate name or owner decision): none
Next action (one command or one owner decision): run the read-only review on the candidate diff
Next owner (skill or human): parent agent
```

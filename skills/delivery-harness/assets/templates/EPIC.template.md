# EPIC-<id>: <outcome>

Status: proposed | accepted | in_progress | blocked | complete

## Problem And Baseline

Describe the observed problem, current behavior and desired measurable outcome.
Reference the current PRD path, requirement IDs and baseline revision/SHA.
Keep one current PRD; do not copy it here or create a PRD per Epic. This Epic's
PRD change lives in its round delta `docs/product/deltas/PRD-DELTA-<EPIC-ID>.md`;
reference that delta path and its Baseline/Result hashes here.

## Accepted Scope

Record the owner's accepted outcome, included work, exclusions and decision source.
Reference valid action grants in the existing task or RUN; this file grants none.

Ambition rung: <1|2|3> — <outcome>
Outside judge: <what proves it, other than us>

## Acceptance And Dependencies

Derive this table's rows from the bound delta's Changed Requirements table and
its TEST IDs; an Epic without a delta keeps its requirement/TEST references from
the current PRD and stays valid.

| Requirement / TEST ID | Expected outcome | Verification / environment | Dependency |
| --- | --- | --- | --- |
| <existing ID> | <observable result including failure/recovery> | <check and evidence location> | <dependency or none> |

## Document Impact

| Changed source / requirement | Affected live artifact | Required recheck |
| --- | --- | --- |
| <source and ID> | <path and affected section/page> | <gate or test> |

## Change Log

Record each entry as `delivery-harness/references/governance/task-and-handoff.md#repository-change-checkpoints` describes. Add an entry only for a new meaningful change, verification result or unresolved state. A Harness bundle adoption is one row with the adopted digest. This record grants no authority and requires no PLAN/RUN.

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| <one logical feature or small fix> | <requirements, files and UI pages/regions> | <exact SHA or artifact> | <actual result, including failures> |

Append same-outcome fixes here. A new accepted outcome gets a linked new Epic.
Do not rewrite earlier results or copy the PRD, scheduler or authorization ledger.

## Results And Remaining Work

Link exact implementation SHA, test evidence and direct-task or PLAN/RUN records.
Record actual outcomes, unresolved criteria, spent repair attempts and next action.
Preserve historical failures and approval evidence. Complete means every required
criterion passed on the actual candidate; a handoff alone does not complete it.

## Handoff

Rewrite this block in place at task start, after each authorized commit, before
the session stops, and at each stage exit; never append a second block. For a
managed RUN, point the `Next action` line at the `inspect_harness_run.py` Next
block and restate no RUN state. The block grants nothing and is not a second
state source.

```text
Repository / branch / HEAD / dirty paths:
Stage and skill:
Inputs consumed (path + hash or revision):
Approvals in force (gate, owner, date, candidate):
Done and verified (command, exit code):
Remaining:
Blocked / waiting (gate name or owner decision):
Next action (one command or one owner decision):
Next owner (skill or human):
```

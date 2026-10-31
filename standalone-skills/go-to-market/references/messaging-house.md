# Messaging House

Keep one persisted messaging record per project at `docs/gtm/MESSAGING.md`.
Show the exact path before creating the file. Reuse an existing record when one is present.
The record holds the approved wording for the project. Campaign drafts, store listing copy, registry descriptions, README first lines, social bios and docs taglines derive from it.
Fill the record with [the messaging template](../assets/templates/MESSAGING.template.md).

## Facts Come From The Product Records

Take facts from the product records only:

- PRD `## At a Glance` and `## Ambition` for the product, user and outcome.
- PRD `## Growth Contract` for the north star, re-engagement mechanisms, discovery surfaces and launch window.
- PRD `## Metrics` for metric definitions and targets.
- `docs/product/stack-decisions.md` for availability decisions.
- The deployment release state for what users can actually try.

This record derives wording. It never changes a product fact.
When a product fact changes, update this record first, then update every variant that repeats the fact.
Mark affected drafts out of date until their revisions cite the updated record.

## Record Contents

The record contains these sections:

- ICP: who the user is, their task, the adoption trigger, the current alternative, the market and the language.
- Positioning statement: who needs this, which task improves, why this product, and what proves it.
- Three proof points, each with its source and observation date.
- Approved public claims, each with its evidence and check date.
- Claims not allowed, with the missing or conflicting evidence.
- Voice rules, with one example sentence and one avoid example.
- Words and tactics to avoid.
- Destination map: each intended action with its real URL, listing or account.
- Per-surface one-liners for the store subtitle, registry description, README first line, social bio and docs tagline.

Leave each one-liner's length limit as a placeholder. The channel playbook fills the limit from a checked platform source at execution readiness. Never invent a platform limit.

## Owner Approval

The owner approves the claims list. The approval binds the record revision.
A claim without owner approval stays out of public drafts.
Record the approval source, the date and the approved revision in the record.

## Reader Boundary

`growth-review` listing checks, `readme-studio` and store listing copy work read this record.
Reading the record grants no authority over the PRD. Product facts change only in the product records.

## Revision Discipline

Put a revision marker and the date on every change.
State the changed sections and the source of each change.
Keep prior revisions and their decisions as history in the record's change log.

# EPIC-design-flow: carry the owner's references across projects and compare directions side by side

Status: integrated on `design-flow` (stacked on `parallel-checks`); full browser suite and review pending; not published
Design workflow: enhancement
UI impact: none in a product. One reviewer page changes: the assembled direction review gains `compare.html`.

## Problem And Baseline

The owner pointed at a public four-step design workflow (references, tools, direction, a tweak bar) and asked to tune the matching parts of `ui-design-builder`. The flow already had a captured reference board, an Impeccable review and three parallel direction studies. Four gaps were picked by the owner on 2026-11-17:

- Every project gathered its 9 to 12 references from scratch; the owner's taste did not carry over.
- The standard profile took two owner turns before HiFi: one to confirm the board's principles, one to select a direction.
- The assembled direction review showed one study at a time behind a sidebar.
- The stage card's steps were single paragraphs of 200 to 400 words.

The tweak bar from that workflow is not in this round.

Baseline: `4b96438b` (`parallel-checks`, on `main` `3a553df7`, v0.85.0).

## Accepted Scope

- DF-1: an owner reference library outside any project (default `~/.agents/design-references/`, `index.md` table). The board starts from it; research fills only the roles it does not cover; a chosen entry is copied into the round with its hash. After Visual Approval the agent offers once to add the round's Adopt and Adapt references, and writes only on the owner's yes, never overwriting an entry.
- DF-2: the board, its proposed principles and the direction studies reach the owner in one turn. A rejected principle is handled in the mix-or-modify revision.
- DF-3: a round of three studies also gets `compare.html`: every study live in one row at the same case and width, one opened at full size with previous, next and back. Study files are unchanged.
- DF-4: the owner may ask for one variant round of three takes on a chosen direction, recorded in a `### Variant round` table (`Direction | Based on | Axis`).
- DF-5: the stage card is split into short steps with every rule kept.

Kept unchanged: owner approvals and who decides, `REF-*`/`RP-*`/`VD-*` identities and hashes, the board count and role coverage, the closed offline package rules, legacy package meanings, every command.

## Acceptance

| ID | Expected outcome | Verification |
| --- | --- | --- |
| DF-1, DF-2 | The library section, intake question, Design Brief field and one-turn rule are stated once and the restating documents agree; packages written under the two-turn rule stay valid (the checker has no order rule) | `ui-design-builder` `test_skill_contract.py` (two new tests), `design-system-compiler` `test_skill_contract.py` |
| DF-3 | `compare.html` lists every study once in round order, stays closed (exact CSP, no external reference), frames each study sandboxed; one-study modes get none | `test_direction_review.py`, `test_reviewer_browser.py` (one real Chromium case) |
| DF-4 | A valid variant round passes; a parent outside the previous round, a shared axis or a wrong row count fails | `test_ui_design_contract.py` |
| DF-5 | Steps, headings, anchors, commands and pinned phrases unchanged; 193 inventory lines: 188 kept, 5 replaced by a pointer to a section that states the rule in full | the doc-asserting modules of the four suites |

## Execution Record

Direct Fan-Out: three Claude Sonnet 5.5 writers (claude-t3-direct, effort high).

| Part | Result |
| --- | --- |
| DA, DF-1 and DF-2 | merged (`ed86bf74`, `f17a09de`). No checker change was needed. |
| DB, DF-3 and DF-4 | merged (`0f9c66ef`, `d330e24b`). One conflict in `ui-design-pass.md`, where DA and DB each extended the direction-set paragraph; both sentences kept. The comparison is a new generated file because a study's CSP forbids framing. |
| Parent | `58eeee65`: two sentences DA flagged outside its files (`Direction Records` opening, the `review-workflow.md` lifecycle line). |
| DC, DF-5 | `3d70780b`, on the integrated head. The card is 3,272 words against 3,275 before; the 2,600-word target was not reached, because nearly every clause is a rule and the brief forbade moving rules out of the card. |

Evidence for DF-3 (before and after, 1440 and 390 px): `C:/Users/mps19/.t3/scratch/design-flow-round/direction-compare/`.

Known limits of `compare.html`, from its writer: Escape returns to the comparison only when focus is outside the study frame; a long study scrolls in its column without a visible scrollbar; a later single-study revision leaves the old `compare.html` in the folder.

## Change Log

- 2026-11-17: round opened and integrated; fourteen non-browser modules pass on the merged head; full browser suite and independent review pending.

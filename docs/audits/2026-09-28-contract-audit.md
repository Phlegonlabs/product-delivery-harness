# Contract audit follow-up

Baseline: `1591a4482155f9601b568b2c357857629dd6c0b1` on `codex/macos-support`.
The owner requested multiple agents, fixes, commits, push and merge. Three read-only
agents checked the findings; the parent owns all edits and Git actions. The source
report was truncated. The owner asked the parent to use judgment for missing text.
The rows below distinguish repairs from findings that did not justify a change.

## High findings

| ID | Disposition and source |
| --- | --- |
| H1 | Fixed: task gates, decomposition, traceability and TASKS use the 500-line File Size Checkpoint. Review responsibilities; line count alone does not fail a gate. |
| H2 | Fixed: the review-skip example supplies PLAN/RUN and places global flags before its subcommand. A regression parses the actual documented argv. |
| H3 | Fixed: review-attempt guidance distinguishes global `--repo-root` from subcommand `--tree-sha`. |
| H4 | Fixed: both UI-check examples supply the registry and source directory. Regression checks run each actual example against clean and violating source. |
| H5 | Fixed: HiFi instructions use reviewer shell v3 while retaining the current `ui-hifi/2` package identifier. |
| H6 | Fixed: the compiler input check requires schema-5 Wireframe Validation and preserves legacy Wireframe Approval. |
| H7 | Fixed: the compiler agent prompt uses the same wireframe and Visual Approval boundary. |
| H8 | Fixed: target/direction changes return to UI Design Builder; product and stack decisions retain their upstream owner. |
| H9 | Fixed: browser extensions use the `browser extension` activation profile, separate from hosted web. |
| H10 | Fixed: security PASS requires complete coverage, no gaps/exclusions, reviewed surfaces, a trust boundary and exact-SHA evidence. |
| H11 | Fixed: the interview no longer suggests an alternative production source outside the main-only contract. |
| H12 | Fixed: architecture guidance starts from the produced candidate; it does not say the RUN pushes its branch. |
| H13 | Fixed: the Product Definition prompt seeds activation for every release target with activation scope. |
| H14 | Fixed: remove undefined STORE/SIGN examples; keep defined APPSHELL/CAP tags and existing core trace ownership. |
| H15 | Fixed: GOAL resolves the installed Harness root instead of assuming a consumer `skills/` directory. |

## Medium findings

| ID | Disposition and source |
| --- | --- |
| M1 | Fixed: consumer command examples use quoted installed skill roots; repository maintenance/CI paths remain source-relative. |
| M2 | Fixed: the required security-policy rule states current behavior instead of an obsolete release announcement. |
| M3 | Fixed: remove the repeated PLAN-null clause in the execution-state model. |
| M4 | Fixed: unsupported explicit user-owned-task/isolation requests block; only optional routes may use the authorized sequential-parent fallback. |
| M5 | Fixed: remove the unexplained 12px-rule denial from the frontend option reference. |
| M6 | Fixed: immutable screenshot reading explicitly covers RUN-v10 and RUN-v11, preserving v9 semantics. |
| M7 | Fixed: structural design within accepted product scope returns to UI Design Builder. New behavior/copy/stack decisions still return to Product Definition. |
| M8 | Fixed: remove the stale 0.47 label; `ui-hifi/2` remains current and reviewer shell v2 is historical. |
| M9 | Fixed: runtime-performance guidance states measured rules and has a complete numbered list. |
| M10 | Fixed: runtime-adapter guidance states the supported native capability boundary directly. |
| M11 | Fixed: current wireframe references say validated; historical approved wireframes keep their meaning. |
| M12 | Fixed: design profiles/rubric name concrete default treatments to inspect without banning valid system fonts, cards or native controls. |
| M13 | Fixed: the Product Definition prompt includes Security Requirements, Monetization Infrastructure and Partner Channel gates, including approval blockers. |
| M14 | Fixed: compiler output-contract heading uses the current skill name. |

## Low findings

| ID | Disposition and source |
| --- | --- |
| L1 | Fixed: local integration grants no push authority, including within the integration-branch scope. |
| L2 | Fixed: Taste may supplement the approved direction; Frontend Design remains the sole author. |
| L3 | Clarified: `persistent` is historical retention compatibility, not permission to reuse a persistent integration branch. |
| L4 | Fixed documentation gap: add the required operations entry to the PRD example. Product Definition review checks task completeness; current schema-5 UI approval gates already enforce declared operations against Wireframe flows and HiFi interactions. Browser evidence remains required. The draft manual-only claim was corrected after inspection of the approval-stage caller; no parser or schema change is needed. |
| L5 | Fixed: RUNBOOK describes container-only, deterministic current-batch `session_exact` reuse and mandatory fresh checks. There is no disk result cache. |
| L6 | Fixed unsupported claims: Grafana and unindexed Python Workers/changelog statements are marked pending source verification. Retain other indexed evidence and its original dates. |
| L7 | Clarified: current-facing references say `Harness 0.38+`; this names the policy threshold, not the installed version. Legacy pre-0.38 recovery is unchanged. |
| L8 | Retained: `visual-direction-guide.md` routes legitimate reopening work, and `impeccable-concept-generation.md` is a tested compatibility pointer. Deleting them is not a supported fix. |
| L9 | Fixed: Design System Guide conflict priorities 5 and 6 duplicated the selected direction. Keep one explicitly approved direction priority. |
| L10 | Clarified: GSAP skills are optional external skills, not bundled installer dependencies. Availability grants no installation or stack decision. |
| L11 | Fixed: worktree guidance directly forbids manual canonical RUN edits without narrating the retired process. |
| L12 | Reviewed: no missing referenced rule was found; the Sequential Parent Route and serialized host-handoff section exist. Clarify that the review needs a fresh context on an allowed driver. The original truncated allegation cannot be recovered. |
| L13 | Fixed: the local-only operating section requires review before closeout and separates later publication. |
| L14 | Fixed executable examples: use consistent `*-skill-root` placeholders. Ordinary narrative skill references remain relative. |
| L15 | Fixed: remove the unsupported CocoaPods status claim and require current official support/compatibility verification before selection. |
| L16 | Fixed: move conditional API overlays under API / Backend. |
| L17 | Not reproduced: the pasted number/text is missing. The adjacent motion-source clue was checked: all ten linked motion sources are already listed under `sources.md`'s motion section. No source was fabricated or needlessly duplicated. |
| L18 | Fixed: remove duplicate performance safety prose and clarify that integration commits contain reviewed heads; PLAN/RUN updates use a separate bookkeeping commit. |

## Verification and release record

The first focused run exposed six assertions tied to old wording/examples. Correct
the assertions where the audited instruction changed, preserving the same behavior
checks; retain useful safety wording where it remained accurate. The new command
regression initially lacked the fixture's responsive set; the corrected fixture
passes both the clean-source and rejected-raw-style checks.

The parent runs the full required suite, golden path and browser checks from the
repository root. Exact candidate verification and independent-review output are
retained outside this checkout under
`work/`.
See the matching Epic for the repository checkpoints and final handoff for the exact
candidate SHA, test results, publication, installation and remaining promotion gate.
This record grants no actions or PASS.

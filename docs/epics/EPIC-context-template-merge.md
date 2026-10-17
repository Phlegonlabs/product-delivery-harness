# EPIC-context-template-merge: Safe AGENTS bootstrap merge

Status: complete

## Problem And Baseline

At detached baseline `bdae1d82acfd24cdeb2866f5480ff4d4d73b0b61` (Harness 0.58.0), `configure_project_context.py` created missing context files but left every existing `AGENTS.md` untouched. A target could therefore remain without current shared guidance after an authorized bootstrap. The approved review in `流程與提速評估.md` identified the merge gap and host-specific installer wording. The checkout started clean at that baseline.

## Accepted Scope

Implement an explicit, idempotent AGENTS merge for authorized bootstrap only. An absent AGENTS file receives the current template. An existing file keeps its owner policy, paths, bindings and overrides; the tool may append only absent top-level template sections in a reviewable block. Same-heading differences are unresolved semantic divergences, not automatic wins. Keep the no-reparse checks and exclusive creation path; use a bounded atomic replacement for merge. Update the bootstrap/Product Definition instructions, worker UI-author sentence, host-neutral frontend-design acquisition wording, four README descriptions, focused tests, this Epic and its index row. The parent-owned root AGENTS Git Flow and branch policy are out of scope.

## Acceptance And Dependencies

| ID | Expected outcome | Verification |
| --- | --- | --- |
| CTM-01 | A missing AGENTS file uses the current template while CLAUDE uses its distinct template | Existing bootstrap tests |
| CTM-02 | Existing local rules and overrides stay authoritative; only missing shared sections are added | New focused merge tests |
| CTM-03 | Same-heading differences remain explicit and merge is idempotent; check mode does not write | New focused merge tests |
| CTM-04 | UI authoring remains capability-bound to the host frontend author and dependency wording is host-neutral | Harness/Product contract and external dependency tests |
| CTM-05 | English source instructions and four README descriptions agree | Contract tests and descriptive-document review |

## Document Impact

Delivery Harness context/bootstrap guidance, document-sync handoff guidance, Product Definition publish step, worker goal template, dependency manifest/checker, installer messages and all four READMEs carry the same behavior. This Epic and `docs/DOCUMENTS.md` record the source-maintenance outcome. No product PRD exists for this repository work.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| 2026-09-29 MOD-A implementation | Owner-approved batch A: add safe context merge and explicit conflict reporting; keep host roles capability-bound and remove Codex-specific frontend-design acquisition wording | Working-tree candidate on baseline `bdae1d82acfd24cdeb2866f5480ff4d4d73b0b61`; atomic task commit is the change containing this Epic | Focused bootstrap, Harness contract, Product contract and external dependency tests passed before the task commit. Full required suite, independent review, promotion, installation and release remain with the parent. No push, install, branch creation or deletion is authorized here. |
| 2026-09-29 parent entry clarification | Keep entry bootstrap as the first source task; narrow Product Definition publication to context-bootstrap moves and defer Skill Bindings resolution to Delivery Harness entry | Follow-up to `689610c00316725db97da4fb9289f90b116c261a`; working-tree changes until the follow-up commit | Product contract verification passed (96 tests). Skill specification, changed-file pyflakes, docs weight and diff checks passed. Parent integration and full suite remain outstanding. |
| 2026-09-29 parent review repairs | Make existing-AGENTS application proposal-only until a reviewed exact-hash heading plan; acknowledge every same-heading divergence; append instead of replace to preserve concurrent owner bytes; reject duplicate headings and ignore headings in fenced code; retain stage-specific binding resolution and extend entry wording to existing targets | Prior local commits `689610c00316725db97da4fb9289f90b116c261a` and `791552ff3120e57b008f075d50eedea0e9be25d5`; working-tree repair until its atomic commit | Configure tests (11), delivery contract tests (60) and Product contract tests (96) passed. Skill specification, changed-file pyflakes, docs weight and diff checks passed. Exact-head rerun, full suite, independent review and promotion remain outstanding. |
| 2026-09-29 parent CLI/upgrade repairs | Fix `--merge-plan` without `--merge-agents` to emit argparse usage instead of a traceback; let a later reviewed template upgrade append under the existing shared-guidance heading without duplicating it; require explicit acknowledgment of the existing heading divergence and consolidate plan validation | Follow-up to `ce2f3a0c89322d45a37339deb1203fb99ae30301`; working-tree repair until its atomic commit | Configure tests passed 13, including CLI usage/no-traceback and second-template-upgrade regressions; changed-file pyflakes and diff checks passed. The 529-line configurator remains one context-bootstrap responsibility after the 500-line checkpoint; no unrelated split is planned. Exact-head rerun and parent integration remain outstanding. |
| 2026-09-29 idempotent-entry repair | Make no-plan `--merge-agents` succeed for missing-file creation or an unchanged pair while retaining nonzero exits for pending proposals or parser conflicts; replace the impossible template-byte-equality publish gate with post-reconciliation `--check --require-resolved --stage product-definition`, and document that intentional stricter local rules are not overwritten | Follow-up to `94d0e8c28edadc56d7a9cc07f060cf49e8b48d1f`; working-tree repair until its atomic commit | New subprocess regression proves first-run creation and second-run unchanged both exit 0; focused configure/Product contract checks and source documentation checks pending before commit. Parent has integrated the prior four commits; this new local commit awaits parent integration. |

## Verification Before Commit

Focused tests passed: `test_configure_project_context.py` (9), delivery `test_skill_contract.py` (60), Product Definition `test_skill_contract.py` (96), and `test_external_skill_dependencies.py` (9). `check_skill_spec.py`, changed-file pyflakes, `docs_weight.py`, `git diff --check`, CRLF-normalized `bash -n install.sh`, and PowerShell parser validation passed. Scoped document sync is `review_required`, as expected for first baseline review and unobserved session-loaded skill identity; its legacy-name findings are in the four READMEs' release history and remain for parent semantic disposition. The complete required suite, independent review, exact-head release verification and installation are not claimed.

## Review Repair Verification

Before the repair commit, `test_configure_project_context.py` passed 11 tests, including a race injection that appends owner bytes after the pre-write observation and proves the tool does not replace them; duplicate/fenced-heading tests passed; delivery `test_skill_contract.py` passed 60 tests; and Product `test_skill_contract.py` passed 96 tests. Skill specification, changed-file pyflakes, docs weight and diff checks passed. Scoped document sync remained `review_required` for unobserved loaded identity, first baseline review and historical README legacy names; its fresh log is outside the checkout. The repair intentionally renames heading matches to proposals: the plan can authorize an append, but it cannot prove that a preamble or differently named local rule lacks a contradiction.

- 2026-10-03 append-result repair at baseline `6027662666f6a807f0d505f1decf06938b22b935`, `codex/harness-flow-modernization` (CTM-02/03/05): an unresolved PR #135 comment reproduced a false `applied` result after concurrent same-inode writes. Read the reviewed bytes through the opened descriptor before appending and require final bytes to equal original plus approved block. Reject earlier drift before adding the block; report later drift while preserving every external and appended byte. Never truncate or roll back owner data. Synchronize document-sync guidance and the four existing README descriptions. UI impact none; the configurator remains one context-bootstrap responsibility after the 500-line checkpoint. The two race regressions failed before repair. Working-tree verification passed 16 configure tests, including pre-open append, same-size content edit, late-write preservation, unchanged application and idempotent upgrade. Scoped Pyflakes and whitespace passed; logs `context-append-race-*.log` remain in the external consolidation directory. Fresh exact-candidate CI and independent review remain required.

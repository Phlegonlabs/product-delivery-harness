# EPIC-document-writing-policy: Use STE core writing rules

Status: complete

## Problem And Baseline

The owner wants project documents to use the core writing rules of ASD-STE100.
Existing guidance asks for short, direct prose but gives no shared technical writing rules.

- Observation: 2026-10-04 03:00 UTC-7.
- Repository: `product-delivery-harness`.
- Branch: `codex/harness-flow-modernization`.
- Baseline: `4cef4f4c28fa69181188589e1055dc6c3d01163f`, clean at entry.
- Source and observed installed Harness: `0.60.0`; loaded identity unobserved.
- This is source maintenance. No product PRD, UI design or PLAN/RUN applies.

## Accepted Scope

Decision source: the owner's request and selection on 2026-10-04:
"採用核心寫作規則，作為專案文件準則（建議）".

Apply a STE-informed guideline to new or changed documentation.
Apply English sentence limits to English prose.
Use clear, consistent terminology in all languages.
Preserve technical meaning, literal source text, requirement strength, approvals and history.
This scope does not include full dictionary conformity or rewriting old documents.

One parent writer owns the checkout. Effective machine instructions require an atomic local commit.
No push, branch creation, installation or remote action is included.

## Acceptance And Dependencies

| Expected outcome | Verification |
| --- | --- |
| Clear sentences, steps, conditions and terms | Official sources and independent document review |
| Language limits and conformity claims are accurate | English rules separated from multilingual principles |
| Meaning and existing authority remain intact | Scoped diff and source review |
| Project and seeded guidance agree | Existing template and context-merge checks |
| All four READMEs describe the same policy | Translation review and existing README checks |

## Document Impact

| Path | Change |
| --- | --- |
| `AGENTS.md` | Document Writing section |
| `skills/delivery-harness/assets/templates/PROJECT_AGENTS.template.md` | Matching consumer guidance |
| Four READMEs | Writing policy beside project governance |
| `docs/DOCUMENTS.md` | Index this Epic |

No new artifact class needs an ignore rule. All changed files are source documents.
No dictionary, checker, new skill or schema is added.

## Change Log

| Request | Reason and scope | Evidence | Verification and remaining work |
| --- | --- | --- | --- |
| 2026-10-04 core-rule selection | Shared writing guideline; UI impact `none` | `working-tree` at baseline `4cef4f4c28fa69181188589e1055dc6c3d01163f`; source diff fingerprint below | Agent Skills check, eight focused tests and whitespace check passed. STE-R3 found no blockers. Epic language clarification applied; release and installation remain pending. |

## Results And Remaining Work

STE-R1 checks official ASD/STEMG sources. STE-R2 maps the existing source and verification scope.
Both are independent read-only assignments. The parent alone edits this checkout.
STE-R2 reused the completed `loop_engineering_boundary` sibling because the session thread limit prevented another launch.
Its actual model identity is unobserved; no model fallback was requested or used.

STE-R1 verified Issue 9 and rules 1.1, 1.11, 3.6, 5.1-5.4 and 6.3 from the official PDF.
It used direct HTTP access and in-memory parsing without writing files.
STE-R2 confirmed the eight-file source scope and existing focused verification.
Their results support a project guideline, not a full-conformity claim.

The Agent Skills specification check passed. Eight existing tests passed:
four project-template checks, one governance bootstrap check, two context-merge checks and one four-README contract check.
`git diff --check` passed. No new tests or runtime code were needed for this prose-only change.
Verification logs remain outside the repository under the task-owned `pdh-ste-check-` prefix in the system temporary directory.

STE-R3 attempt 1 found no blocking findings and inspected the retained verification logs.
Its nonblocking Epic clarification now limits English sentence counts explicitly to English prose.
The six rule-bearing files remain byte-identical to the reviewed inputs; later Epic/index edits record results and source status.
Review covers documentation only, not runtime behavior, installation or release.
The assigned reviewer uses the host's native reviewer binding; its model is not independently observable inside the child task.

Rule-bearing diff SHA-256, excluding this Epic and its index:
`00e04ffa34d2654b9b1fbaf848eee0537de65cd337dc549c9d7743ce5ac22a12`.
Git preserves this task's eight-file diff and final commit identity.

Entry document sync returned `review_required`: loaded identity is unknown, and no prior inventory baseline applies.
It also flagged retired names in README migration guidance and release history. These records remain unchanged.
Observed installed template `0.60.0` has SHA-256 `0d5064d94c0072ad2d1f06f3b516dab328d425be79454df10b50ce6f44b2470e`.
The shared writing rule will be a source addition pending formal release and installation.
Existing installed shared rules remain current by meaning. Document Writing is an authorized source addition, not an installed-template update.
No loaded digest or inventory snapshot was invented. The document-sync report remains `review_required`, not a delivery verdict.

Reference: [official ASD-STE100 overview](https://www.asd-ste100.org/about_STE.html).
This project guideline is not a claim of full ASD-STE100 conformity.

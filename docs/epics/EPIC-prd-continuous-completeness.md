# EPIC: PRD completeness through delivery

Status: implemented and verified locally; uncommitted and not installed by this task

## Problem And Baseline

The owner wants the same PRD improved throughout delivery, with UI and technical perspectives checking the whole first delivery before implementation. Existing roles cover individual topics but do not explicitly reconcile first-delivery journey gaps and later discoveries through one refinement rule.

Observed 2026-09-24 UTC in `C:/Users/mps19/Documents/GitHub/product-delivery-harness`, branch `codex/design-brief-references`, baseline and observed HEAD `b4ffe691b97265d5a76817c2e0ccf457e084fa54`. This is a source-repository workflow enhancement; there is no product PRD to create here. UI impact: none. Route: small, direct, one parent writer.

The existing uncommitted Design Brief change is retained; its earlier verification remains in [its Epic](EPIC-design-brief-reference-intake.md). The unrelated untracked `scripts/design/hifi_model.py` is preserved. No new branch, commit, push or installation is authorized by this record.

## Accepted Scope

- One shared PRD refinement reference with stage-specific evidence and dispositions.
- First candidate review from UI and technical perspectives, including cross-feature dependencies and the complete first-use-to-value journey. Use existing roles and approval checkpoints.
- Keep one current PRD, stable IDs, English authority and full Chinese review copies. Preserve frozen inputs and historical approvals; new product decisions follow existing gates.
- Wire the rule into Product Definition, UI, implementation, verification and activation/outcome handoffs; update all four README descriptions.
- Use the user-authorized GLM worker for a read-only patch proposal. The parent applies and verifies the changes in this dirty checkout.

Decision source: the owner's selection of continuous PRD completion and subsequent request to consider overall first-delivery completeness through UI and technical perspectives. Earlier explicit GLM-worker authorization remains applicable.

## Acceptance And Dependencies

| Existing contract | Expected outcome | Verification |
| --- | --- | --- |
| Product Definition candidate and agent work graph | Applicable UI and technical lenses review the same first candidate; headless products do not acquire UI scope | Focused packet tests and scenario review |
| Product approval and artifact lifecycle | Findings cannot silently expand scope, reapprove a frozen package or replace owner decisions | Existing approval/translation suites and semantic review |
| UI, delivery and activation ownership | Each stage routes new evidence into the existing product/change records | Routing review and required full suite |
| README documentation of record | Same behavior described in all four languages | Diff review, spec and docs-weight checks |

## Document Impact

Canonical skill sources and Product Definition graph packets/tests change. READMEs, this Epic and `docs/DOCUMENTS.md` describe the result. Existing Design Brief edits remain intact. No schema, approval gate, product artifact, new graph role or installed skill changes are intended. Logs and temporary proposals stay outside the checkout; no new Gitignore pattern is needed.

## Change Log

| Observation | Change and evidence | Verification / remaining work |
| --- | --- | --- |
| 2026-09-24 UTC, working-tree | Entry HEAD and branch match the prior Design Brief baseline; ten tracked modifications, its untracked Epic and the unrelated Python file predate this work | Prior Design Brief result retained; this enhancement has not yet passed verification |
| 2026-09-24 UTC, working-tree | Added stage hooks in UI, delivery, activation and shared document-sync instructions; GLM read-only drafting launched | Entry document-sync reports first observation and unknown loaded identity; semantic source review performed. Full evidence under `C:/Users/mps19/AppData/Local/Temp/pdh-prd-completeness-f113a9165ea94b1d941623fb19b1ff6d/` |
| 2026-09-24 UTC, working-tree | GLM Flash run `20260924-003034-96554812606d4428b1b7ff2b00cde509` completed read-only, exit 0, 483.804 seconds. Parent integrated its reference/routing proposal, clarified frozen-input handling and added concrete requirement-writing guidance, graph packet instructions and three focused tests | Worker did not mutate files or claim tests. Parent focused tests and all three prerequisite commands passed |
| 2026-09-24 UTC, working-tree | Final combined skill/README/test source fingerprint before full checks: `1639df5001d6306f334433dc1193bee8a7097012666e287e26ae0cb2ea06245c`; per-file hashes in `source-before.json`. Earlier Design Brief edits are included; Epic/index excluded | Spec and pyflakes passed. Docs weight: +1,752 words versus v0.53.1, including the prior +555-word Design Brief change. Full suites running on these bytes |
| 2026-09-24 UTC, first full verification | UI: 279 passed with required Chromium. Harness: 1,165 tests in 997.306 seconds, 10 failures, 2 errors, 16 skips. Installer scenarios rejected the new untracked reference; the Harness entry grew to 3,630 words against a strict under-3,600 limit | First-run failure retained in `harness-full.log`; remaining suites had not run. No PASS claimed |
| 2026-09-24 UTC, repair round 1 | Added only the new reference with Git intent-to-add so installer manifests can include its working-tree bytes; no file content is staged for commit. Shortened the Harness routing paragraph to bring the entry to 3,594 words without dropping the shared rule | Focused installer and context-budget tests running; fresh final fingerprint and full verification required |
| 2026-09-24 UTC, repair verification | Focused installer tests passed the first five cases, including complete installation, before the task's 300-second deadline interrupted rollback testing. Exit 124; not a suite PASS. The task process tree was inspected, stopped and checked absent, including the child mentioned in taskkill output | No source failure was reported before the deadline. Full repaired verification runs serially with a 2,400-second Harness limit; logs use fresh `final-*` names |
| 2026-09-24 UTC, repaired working-tree | Final source fingerprint `8e92787cf69f1da0042ca2cb13b9d7afa6a74322cd6847805c59a81a782bde55`, per-file hashes in `source-repaired.json`; same branch/HEAD, original unrelated file and installed skill digest | This supersedes the earlier test-input fingerprint, not its historical failure record |
| 2026-09-24 UTC, repaired full verification | Spec, pyflakes, docs-weight (+1,716 words vs v0.53.1), required Chromium UI (279), Product Definition (235), Design System (99, 3 platform skips), Activation (56), SEO (17), enabled golden path (1) and diff check all exited 0 | Final Harness suite remains running. Other suites use the repaired source fingerprint; no source changes followed |
| 2026-09-24 UTC, final verification | All 11 required repaired-source jobs exited 0. Harness ran 1,165 tests in 1,655.002 seconds, OK with 16 Windows/opt-in skips. Required Chromium UI ran 279, all passed. Golden path passed separately. Product Definition 235, Design System 99 (3 platform skips), Activation 56, SEO 17 all passed | `final-repaired-jobs.json.results.json` and fresh per-job logs retain the evidence. `source-after.json` matches the repaired source fingerprint, branch, HEAD and unrelated file hash. No source edit followed |
| 2026-09-24 UTC, external installed-skill observation | The separately installed seven-skill digest changed from `dd610610baff6e3d607f61a9d5e7c40114a610d7ae17090958b8d813cc0f699f` to `2d4bae42609dda5ad25996ec8b6501989b052b090ace089899b7e62583cdf754` during validation. Installed `delivery-harness/scripts/select_verifiers.py` has a modified time of 2026-09-24 08:07:45 UTC and hash `8ec22743b1146b9792ba0d7b0732129b508fa3be1445db3ededcdf30ab970995` | Observed/unverified external change. The repository source file remains unmodified. This task did not install skills, claim a loaded digest, or adopt the changed installed bytes |

## Results And Remaining Work

Release continuation: this PRD change was committed on `codex/design-brief-references` as `dee2d77` (`feat(prd): refine first delivery requirements across stages`), after Design Brief commit `b257304`. Version 0.54.0 preparation is in progress. The repaired-source verification below remains historical evidence; final candidate verification and release actions are tracked separately.

The continuous PRD refinement rule, first-delivery UI/technical review lenses, graph packets, cross-stage routing, four README descriptions, Epic and index are implemented in the local working tree. Three focused graph tests passed; all 11 required jobs passed on the repaired source. The final source fingerprint is `8e92787cf69f1da0042ca2cb13b9d7afa6a74322cd6847805c59a81a782bde55` and matches `source-after.json`. HEAD remains `b4ffe691b97265d5a76817c2e0ccf457e084fa54` on `codex/design-brief-references`; no commit, push, promotion or official skills installation was done. The unrelated untracked file's hash remains `66b61a803153d4da49e10ce3e25b72a51229728a84bc48371620012e21e38b9c`. The loaded skill identity is unknown. The separately installed bundle changed externally during testing; its cause and applicability were not verified. No product release or production UI quality is claimed.

## Scenario Review

These are parent semantic checks of the workflow, not executions of a real product or proof of model output quality:

| Scenario | Required disposition |
| --- | --- |
| First draft lists separate screens but omits the path from creating a record to finding its saved result | UI perspective names the missing journey edge; reconcile accepted behavior into existing UI/PRD/TEST rows before approval |
| A native local-data app has no browser frontend | It still receives the UI completeness lens; no hosted platform or login is invented |
| A headless automation has no shipped UI | Review caller/operator journeys and technical recovery, with no placeholder screens |
| Retry creates duplicate data despite a clear approved no-duplicate obligation | Repair implementation and verify the existing TEST; do not weaken the PRD |
| Design reveals an unapproved new administrative action in a frozen package | Retain evidence/proposed wording in the existing change record; dependent work awaits the existing product decision and valid refreshed bindings |
| Post-release measurements miss an approved target | Retain actual evidence and the target; route through the existing outcome verdict, never lower the target to claim success |

Three focused graph packet tests passed: native UI applicability, headless exclusion, and synthesis/review routing that retains approval boundaries. They check emitted instructions and lane selection, not whether a model will discover every missing requirement. Required prerequisites also passed: pip requirements, npm ci and Chromium installation.

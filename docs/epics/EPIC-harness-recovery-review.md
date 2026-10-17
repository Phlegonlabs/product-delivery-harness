# Harness Recovery And Review Inputs

Status: complete
All six outcomes integrated in atomic local commits; focused checks passed; complete release matrix and candidate review remain separate; not released or installed.

## Accepted Outcome

On 2026-09-30 the owner requested multi-agent architecture review, asked whether this is harness engineering, and then instructed direct flow optimization. This round fixes the confirmed execution/recovery defects and improves complete review input. The existing selector, PLAN/RUN, receipts, locks, authorization ledger and exact-candidate gates remain the architecture.

Baseline: `codex/harness-flow-modernization`, `e6e6d1e9f743f48889b3e11dce4f0c3f5d5d27ed`, clean. Source and observed installed Harness are 0.59.0; the installed copy is a development installation. Loaded identity is unknown. The parent owns all writes in this checkout. This direct source task has UI impact `none` and creates no consumer Product Definition or PLAN/RUN. User authorization covers source, tests and documentation; it does not include commits, publication, release or installation.

## Requirements And Acceptance

| ID | Outcome | Required checks |
| --- | --- | --- |
| FLOW-01 | Parent lock and worker launch session have distinct CLI arguments | Public parser/transaction test with full RUN validation; sibling sessions, wrong parent/model/attempt and missing/reused child denied without RUN writes |
| FLOW-02 | Terminal integration reviews survive a candidate move as history without concealing blockers | Complete synthetic RUN validation; unique attempt/outcome/lineage join; stale current PASS and active/unreconciled blocked history rejected; receipt-bound interrupted review survives movement and complete closeout |
| FLOW-03 | Archive ancestry follows the frozen dual-branch base | Real Git development candidate with an unforwarded main hotfix; stale main observation, invalid base and legacy main ancestry still rejected; archive/publication regression suites |
| FLOW-04 | UI entry chooses the same package contract throughout | New initial/full redesign `/3`, retained `/2`, enhancement and maintenance instructions consistent; cross-skill contract checks |
| FLOW-05 | Current delegated mission retry requires confirmed termination | Missing/wrong/tampered receipt, live predecessor and unresolved partial work denied without mutation; selector and lease independently recheck; old pins unchanged |
| FLOW-06 | Bounded review previews have a complete fixed diff source | External exclusive artifact with exact bytes/hash/base/head/name-status; large and binary changes, existing/in-checkout path rejection; security receives fresh full-scope guidance |

## Scope And Dependencies

Changes cover launch CLI/locks, terminal review validation, archive/publication ancestry, interrupted mission receipt admission, review packet outputs and UI entry text. Existing stored formats remain unchanged. The new launch flag is an explicit correction of an ambiguous CLI interface; frozen launch records keep `session_id`. FLOW-05 applies only to 0.59+ role-bound delegated missions; the separate review fan-out interruption path retains its existing protocol. FLOW-06 improves inputs and instructions; it does not add returned path-coverage enforcement or prove reviewer understanding.

Read-only explorers supplied separate execution and upstream designs. Their initial GLM starts failed with API 429. The owner explicitly approved Astra/high for these two explorations; actual endpoint identity was not observable. Claude Opus 5.5/xhigh independently reviewed the baseline through the read-only bridge. Architecture and execution findings were checked against source before editing. Relevant reading includes canonical Harness/UI skills, delegation, document sync, bounded enhancement, execution state, agent receipts, branch promotion, runtime performance, verification and all four README descriptions.

The unchanged context proposal remains [context-decomposition.md](../research/context-decomposition.md). Its CTX tasks, returned coverage enforcement and real host behavior/cost evaluation are later measured work; this round claims no runtime token or throughput savings. Existing modernization frontend work remains separate and untouched.

## Change Log

### 2026-10-03 — Source integration complete

- FLOW-01 d727dbe5, FLOW-02 73fbe145, FLOW-03 1194bea7, FLOW-04 d813a06a, FLOW-05 1a9a6d21 and FLOW-06 a4b53102 retain separate task history. The staged-source checks below passed; the timed-out broad archival selection remains recorded, not reused as PASS.
- At parent 41bf3304d643b43b7ca315f75a76283be00609a7 the checkout is clean. Source recovery bytes are committed, and original working-tree baseline copies remain outside the checkout. Follow-up UI documentation/tests are recorded in EPIC-design-showcase.md.
- Fixed release verification, independent/security review, hosted platform results and exact protected-target decisions are still required. Formal release and local installation have not occurred.

### 2026-10-02 — Authorized release integration

- The owner requested commit, push, formal release and a local skills update after multi-agent UI pipeline inspection. This extends the earlier local implementation authority; exact protected-branch promotion and the missing development bootstrap remain separate decisions.
- Entry: `codex/harness-flow-modernization`, HEAD `5c6b9de431b2174a40285a10a13bef59fd38261c`, empty index and 31 retained recovery changes. The parent owns all writes. FLOW-01 through FLOW-06 will be staged and tested as separate source trees before atomic commits.
- Prior results below certify their recorded working-tree inputs only. Fresh full release checks and independent UI pipeline/candidate review remain required. No product deployment target exists in this skill-source repository.
- Test exports, process records and logs remain outside the checkout under `pdh-release-20261002-trrq9aed`. Existing ignore patterns cover the observed caches and dependencies; source and tests remain tracked.

### 2026-09-30 — Working-tree implementation

- Repository/branch and baseline are stated above; observed HEAD remains the baseline. The task has no commit.
- FLOW-01 replaces launch-local `--session-id` with required `--worker-session-id`, records that child identity and requires a held parent lock.
- FLOW-02 admits only detached terminal prior-head reviews with an exact retained review attempt. Active/current bindings and all existing receipt/security checks remain enforced.
- FLOW-03 adds one frozen-base selector shared by archive creation and publication. Archive creation retains exact observed-main binding; current publication no longer demands a moving main ref equal a historical receipt. Legacy pins keep that demand.
- FLOW-04 removes unconditional `/2` lifecycle/preflight wording from UI entry.
- FLOW-05 stores a validated stopped failure receipt before interrupted phase changes and revalidates it on selector/lease admission.
- FLOW-06 adds external full binary diff artifacts and exclusive output writes to both packet entrypoints; failures after RUN persistence explicitly report the durable reservation.
- Four-language README descriptions and touched contracts are synchronized. No new local artifact class is introduced in the checkout; existing ignore rules cover Python caches, and task logs/receipts/diffs live outside it. New regression sources and this Epic remain tracked-source candidates.
- Verification and fresh independent working-tree review are pending below. Historical test results do not certify these bytes. Completion does not imply the separate 0.59 release is ready.

### 2026-09-30 — Independent review corrections

Claude bridge review completed as `claude-opus-5-5` (requested xhigh), session `93ff2109-e616-48f6-a99d-1f867fee3201`, with Read/Glob/Grep only and no permission denials. It reviewed snapshot `da345e770ac56149bc1f9a6d50973b546fa0822cd05e43115ad8793269e0b6d3` and returned changes required. This is working-tree review, not exact-SHA security certification.

- F1: Updated both remaining launch fixtures to `worker_session_id`.
- F2: The complete historical-review fixture now retains only parent/local graph attempts, leaving original review identities distinct. Its positive test validates the entire PLAN/RUN before and after the move; removing historical admission makes that positive test fail.
- F3: Truncation guidance sits outside the invariant execution contract. It explicitly allows fixed Git inspection when no artifact was requested.
- F4: Publication lineage scanning now stops at the frozen delivery base. Correction chains compare the complete frozen branch policy and receipt-bound original PLAN/RUN bytes, rather than requiring their separate main observations to match. Real 0.59 archives test main movement, landed-development history, correction continuity and altered-base denial; legacy cases retain their main-based interpretation.
- F5: Equal packet/artifact output paths are rejected before RUN persistence; preintegration artifacts also stay outside the bound mission checkout.
- F6: A failed exclusive artifact write preserves its partial file and reports the path. It creates no successful packet or valid coverage evidence. No automatic deletion was added under local data-preservation rules.
- Historical `blocked` reviewers retain the existing complete-RUN blocker rule; this round does not claim generic blocked-review closeout or alter that gate.
- The first affected-suite run had 296 tests, two fixture/packet failures and four platform skips. Corrected manifest/review/receipt suites then passed 232 tests. These are intermediate results; final full-suite evidence remains pending.
- The early full-suite job was cancelled before correction completion. Its verified process tree exited; its nonzero result is cancellation evidence, not test evidence. All logs and review artifacts remain outside the checkout.
- Transition/manifest modules already exceed 500 lines. These fixes stay beside their existing guarded state joins; shared receipt/base/output helpers own the reusable logic. Splitting the entire kernel would expand this bounded recovery change without improving these checks.

## Verification And Handoff

Final working-tree behavior/documentation scope after M2: `519364ab3eb8ffdf01b90c5f49cdaf4842d2dce7cd0dedc2d378e6845f360506`. This digest includes the four READMEs and excludes factual `docs/` handoff updates; exact per-path hashes and complete diff are retained externally in `closure-scope.json` and `closure-implementation.diff`. The preceding reviewed scope `3cf224ec1f2082984fd5ad13fffe631cca9c2b3ed793c317f36b28d89ce82aba` remains immutable in `post-review-scope.json`. HEAD remains `e6e6d1e9f743f48889b3e11dce4f0c3f5d5d27ed`; this identifies the baseline, not the changed working-tree bytes.

| Check | Actual result and evidence |
| --- | --- |
| Complete final Harness suite and golden path | 1,482 tests, no failures/errors, 18 platform skips, `full-closure-27.log`; golden path and required browser verification enabled. All 21 installer-module cases use the separately recorded copied-source fixture because this source checkout intentionally retains untracked new test files |
| Pre-M2 focused Harness suite | 266 tests passed, `post-review-20.log`; retained as intermediate evidence, superseded for current Harness behavior by the full final run |
| Product Definition | 256 passed, `sibling-suites-17.log` |
| UI Design | 318 passed with required browser checks enabled, `sibling-suites-17.log`; observed Playwright 1.62.1 matches lockfile and Chromium revision 1234 is present |
| Design System Compiler | 134 tests, 4 platform skips, no failures after the stale wording correction, `compiler-21.log`; the earlier one-failure run remains recorded |
| Activation / SEO | 65 / 21 passed, `sibling-suites-17.log` |
| Installer scenarios | Unchanged suite on copied candidate: 21 tests, all 19 installer cases passed; 2 CI assertions errored because the auxiliary fixture omitted the unchanged workflow. `installer-ci-22.log` reruns both with that workflow and passes. These are temporary sources/destinations, never the observed installed skills |
| Final static checks | Skill specification, pyflakes across all six scripted skill trees, docs-weight report and diff whitespace passed after M2, `static-28.log`. Earlier `static-23` also passed. Docs-weight estimates are not model token measurements |
| Exact final bundle installers | Both Bash complete-manifest/migration and PowerShell migration/rollback/complete-parity checks passed, `installer-closure-29.log`, 2 tests. `installer-closure-manifest.json` hashes all copied bytes. Only the task-local fixture has an index/commit; destinations stay temporary |
| Final independent M2 confirmation | Claude bridge `9d313a9c-6910-4bcc-b81c-cee810673cd3`, reported `claude-opus-5-5`, requested xhigh, Read/Glob/Grep, no denials; no confidence-80 correctness/authorization/regression findings introduced by M2. Previous six changes were checked in the prior reviews |

All evidence lives under `pdh-architecture-review-20260930-yxosnz1x`. Broad full-suite result and its installer denial remain recorded below rather than being relabeled PASS. `installer-final-24.log` subsequently passed both installer payload checks on scope `3cf224...`; the third review completed and led to the final M2 correction below.

Shared-template audit: observed installed Harness 0.59.0, template SHA-256 `0d5064d94c0072ad2d1f06f3b516dab328d425be79454df10b50ce6f44b2470e`. Shared rules remain current by meaning; source-specific stage/deployment/activation omissions, Git Flow, required reading and soft 500-line checkpoint are intentional. `AGENTS.md` was not changed. There is no live product PRD/architecture pair in this source repo requiring translation. Epic/index, affected references and the four README descriptions agree with this direct source task. No managed tasks view applies. `.gitignore` continues to cover observed caches/dependencies; generated evidence stays outside the checkout.

Source and installed VERSION both say 0.59.0, but their implementation bytes differ. Loaded identity remains unknown. No release, tag, commit, push, protected-branch landing or local skill update was performed. The separate modernization frontend correction, full exact-SHA release matrix, host behavior/cost evaluation and initial-base observation provenance remain their own outstanding work.

### 2026-09-30 — Second review disposition

Claude bridge session `d4f5e9e6-c4ee-4eca-b457-58b57d692bb2` completed as `claude-opus-5-5`, requested xhigh, Read/Glob/Grep only. It found F1–F6 correctly implemented and one new blocked-review interaction (M1). The bridge reports model identity; endpoint reasoning effort is not independently observable. The complete canonical Harness and UI skills were included in its required reading.

- M1 is fixed by admitting only historical `worker_passed` and `worker_failed` phases. A blocked sibling makes candidate reconciliation fail validation before RUN persistence, so fresh gates cannot conceal an unclosable retained blocker. The regression uses the public transaction and actual invalidation with a synthetic RUN; live Git/product repair joins are isolated and tested separately in `test_candidate_resume.py`.
- Added detached structured-security PASS and tampered historical SHA coverage, plus retained failed-review coverage. Old child flag rejection is now a separate test with the required new child flag still present.
- UI entry's remaining new-package `/2` sentence is corrected; graph guidance explicitly distinguishes full-scope integration security review. A pre-existing compiler test required a removed phrase. It now checks the canonical retained `/2` single-recommendation rule and keeps the `/3` three-direction assertion. No pending frontend source or direction policy was changed.
- Correction publication across a pre-0.59 to 0.59 policy boundary is deliberately refused: the prior frozen policy must match the current one, and the older contract has none. Migration needs a fresh governed delivery; old archives are not relabeled.
- The base is frozen in PLAN and validated as a candidate ancestor. These repairs do not add a machine receipt proving that `base_ref` pointed to `base_sha` at initial branch creation. Comparing against a moving ref later cannot prove that observation; this remains a separate provenance gap.
- `corrections-12.log` ran 12 tests, correcting the second review request's mistaken count of 13. Full Harness/golden-path run 13 ran 1,496 tests with 9 failures, 2 errors and 18 platform skips. All failures/errors were in installer tests: new untracked canonical test sources caused installers to stop before each intended scenario. Installers are unchanged and retain that refusal. A task-local Git fixture copies and hash-checks the candidate sources for the unchanged installer suite; only that synthetic repo is indexed/committed, and destinations stay temporary. The real checkout index, refs and installed skills are untouched.
- Final post-review recovery/launch/UI/candidate checks passed 38 tests. Initial new fixture errors and an incorrect test-module name were corrected before this result; their failed logs remain outside the checkout. The remaining skill suites and focused final manifest/static checks are recorded below when finished.

### 2026-09-30 — Reconciled review interruption exception

Third read-only Claude review completed as `claude-opus-5-5`, requested xhigh, session `31de6e87-471b-4c72-ad5e-9fad26853c01`, no tool denials. It identified M2: M1's blanket blocked-history refusal also refused already reconciled review interruptions, although existing closeout permits them. That was already a limitation at HEAD; retaining it would leave an avoidable recovery gap in this round.

- M2 uses the exact existing `_is_reconciled_interrupted_review` predicate for historical admission as well as closeout. It still requires the common unique retained attempt/outcome/lineage join and recorded prior head. Generic blocked reviewers remain refused. An interruption receipt provides no candidate PASS or security coverage.
- The positive regression calls the real interruption transition, validates before and after it, moves the candidate, retains original worker bytes, and validates a complete synthetic closeout with fresh current gates. Missing receipt, wrong lineage/outcome and duplicate attempt reject the movement. Public transaction denial now asserts the reviewed-SHA error and has a passing control. Failed-history checks include `retryable_failure` and `contract_gap`, not only the existing `fix_required` path.
- Additional admission wording is now precise: the older `fix_required` rule retains its previous pinned semantics. The new attempt-join requirement is not retroactively imposed on that path.
- The new active/closeout fixtures initially exposed synthetic driver/lineage and duplicate-attempt setup errors. Those were corrected; all 9 historical-review tests then passed in `interruption-26.log`. Synthetic closeout reconstructs current gate evidence; it does not claim a live host delivery.
- Review evidence correction: `installer-16` exited 1 because of the omitted auxiliary workflow; both unchanged CI tests had already passed against the real checkout and then passed again in `installer-ci-22`. Two test files changed after its source copy: historical-review tests and the compiler contract test. Both are included in the later exact-payload installer fixture.
- `static-23` did run on scope `3cf224...` after the preceding delta, contrary to the third review's stale-log inference. M2 changes require new static evidence and a new frozen scope. The final full Harness run separates installer cases into their isolated source fixture because canonical untracked-source refusal must remain enforced.
- Remaining narrower validation gap: detached structured security PASS coverage has no declared `required_checks` in that synthetic fixture. Existing structured-security suites verify required-check joins; this round does not claim a new combined retained-check fixture or live host conformance evaluation.
- Fourth bounded review confirmed M2's recommended code option, matching existing closeout and all common admission gates. It verified the true interruption transition, unchanged retained bytes, full synthetic closeout, receipt mutations, transaction denial and passing control. The candidate transaction test isolates live Git/product repair joins; separate candidate tests cover those joins. It reviewed scope `519364...`; no source writes followed. Model identity is bridge-reported, effort remains unobservable. Its missing full-suite result was timing, not a code finding.

### 2026-09-30 — Local handoff

- Final full Harness run exited 0 after 935.911 seconds: 1,482 tests, 18 platform skips, no failures/errors. The required golden path ran. The 21 installer cases are accounted for by the unchanged comprehensive installer fixture run, two CI supplements, and fresh exact-bundle Bash/PowerShell tests; the original nonzero logs remain intact. This is a composite local verification record, not a relabeled single successful full-discovery invocation in the untracked source checkout.
- Other five suites total 794 tests, no unresolved failures and 4 compiler platform skips. Windows observations do not certify POSIX/macOS-only checks. Final static checks and independent source review passed as recorded above. Formal exact-commit multi-platform release/security evidence remains a separate obligation.
- Handoff checkpoint at `2026-09-30T11:32:39Z`: repository remains `product-delivery-harness`, branch `codex/harness-flow-modernization`, HEAD `e6e6d1e9f743f48889b3e11dce4f0c3f5d5d27ed`. The index is unchanged and empty of staged edits. All observed non-ignored dirty paths belong to this Epic's source/test/README/document changes. Code/documentation behavior hashes still match frozen scope `519364ab3eb8ffdf01b90c5f49cdaf4842d2dce7cd0dedc2d378e6845f360506`; only factual Epic/index handoff text changes afterward.
- No task preview or log-watcher service was started. Verification wrappers recorded finite deadlines and exited; all native agents and Claude bridge reviews are stopped. Test logs, snapshots and synthetic installer source repositories are preserved outside the checkout.
- This round completes FLOW-01–06 under local source authority. The next integration owner may separately authorize atomic commits and integration into the existing modernization candidate. Release, protected-branch promotion and installation retain their own exact grants. Existing stopped frontend work and future context/host evaluation remain separate; no token, cost or throughput improvement is claimed.

### 2026-10-02 — FLOW-01 atomic integration

- Parent baseline `19f833f9b70e76ae2c00a507131f58f6c2e8546c`; staged source tree `cf53b84c4e90dbd2d95688fe3a48e767bc9ef6fe` exported and tested from its repository root before the commit. Documentation added after testing changes no tested skill bytes.
- Focused positive and negative checks: 27 tests passed in `recovery-01-staged.log`; finite job exited with no remaining owned processes. The commit contains only this FLOW outcome, its tests and four-language descriptions.
- Full exact-candidate release matrix and independent UI pipeline/candidate review remain pending. No remote publication or installed-skill mutation.

### 2026-10-02 — FLOW-02 atomic integration

- Parent baseline `d727dbe5d8e177f6f8a1d4a214aeaef5284bee79`; staged source tree `0b9634e09cc49d42059d0fe9c4780b0040b7588b` exported and tested from its repository root before the commit. Documentation added after testing changes no tested skill bytes.
- Focused positive and negative checks: 19 tests passed in `recovery-02-staged.log`; finite job exited with no remaining owned processes. The commit contains only this FLOW outcome, its tests and four-language descriptions.
- Full exact-candidate release matrix and independent UI pipeline/candidate review remain pending. No remote publication or installed-skill mutation.

### 2026-10-03 — FLOW-03 atomic integration

- Parent baseline `73fbe1457a9c8c46c31626a0c7cd2853b1fb0d58`; staged source tree `545e023de8811b6b6d68b2cf895cb3fe9e4437df` exported and tested from its repository root before the commit. Documentation added after testing changes no tested skill bytes.
- Focused positive and negative checks: 13 tests, no failures/errors, no skips in `recovery-03-changed.log`; finite job exited with no remaining owned processes. The commit contains only this FLOW outcome, its tests and four-language descriptions.
- The larger 96-case archive/publication selection reached its 600-second deadline before completion. Its result is timeout (124), not PASS; its owned process tree exited. The focused 13-case run covers frozen-base selection, actual Git archive ancestry/main freshness, legacy and malformed pins, four dual-branch publication/correction cases and whole-set archival. Complete archive/publication regressions remain required in the final release matrix.
- Full exact-candidate release matrix and independent UI pipeline/candidate review remain pending. No remote publication or installed-skill mutation.

### 2026-10-03 — FLOW-04 atomic integration

- Parent baseline `1194bea700fc010122535b4fe37240cd11f5dc01`; staged source tree `ca3a7a765ef844bd959e62d226ce0af28a48ee28` exported and tested from its repository root before the commit. Documentation added after testing changes no tested skill bytes.
- Focused positive and negative checks: 17 tests, no failures/errors, no skips in `recovery-04-staged.log`; finite job exited with no remaining owned processes. The commit contains only this FLOW outcome, its tests and four-language descriptions.
- Full exact-candidate release matrix and independent UI pipeline/candidate review remain pending. No remote publication or installed-skill mutation.

### 2026-10-03 — FLOW-05 atomic integration

- Parent baseline `d813a06a0c752acd86ad7e5665b32cb93a236be1`; staged source tree `915977d83ed182e2d70928790a92e04235430ce7` exported and tested from its repository root before the commit. Documentation added after testing changes no tested skill bytes.
- Focused positive and negative checks: 7 tests, no failures/errors, no skips in `recovery-05-staged.log`; finite job exited with no remaining owned processes. The commit contains only this FLOW outcome, its tests and four-language descriptions.
- Full exact-candidate release matrix and independent UI pipeline/candidate review remain pending. No remote publication or installed-skill mutation.

### 2026-10-03 — FLOW-06 atomic integration

- Parent baseline `1a9a6d217329299617cbb2d45caae1498123aa06`; staged source tree `9668cc2a0d932eef47961849a65e5e4d726ee2d2` exported and tested from its repository root before the commit. Documentation added after testing changes no tested skill bytes.
- Focused positive and negative checks: 8 tests, no failures/errors, no skips in `recovery-06-staged.log`; finite job exited with no remaining owned processes. The commit contains only this FLOW outcome, its tests and four-language descriptions.
- Full exact-candidate release matrix and independent UI pipeline/candidate review remain pending. No remote publication or installed-skill mutation.

# EPIC-pre-delivery-self-review: Review each authoring stage before delivery

Status: complete

## Problem And Baseline

Baseline: main `d7083fb3f43481127fd25252f200e5aa1d37e977`, release 0.56.1.
Post-draft market research and HiFi independent review already exist. Author
self-review is not explicit at each stage exit, and the README diagrams allow
a UI-deferred shortcut into Harness.

## Accepted Scope

The owner requested PRD market research and self-review, UI self-review and
HiFi self-review before Product Delivery Harness execution. Treat UI as
structure/direction review in the current flow, not a restored Wireframe stage.
Update the three owning skills, their relevant flow references, seeded/shared
governance and all four READMEs. Use existing task/evidence records, approvals and
validators; add no schema, product artifact or approval round. Add focused
document-contract regression checks without claiming machine proof of self-review.

Project size: small. Route: direct, one parent writer. UI impact: none.
Gitignore impact: none; verification logs stay outside the checkout and existing
rules cover dependencies and Python caches. This task changes workflow guidance,
not executable validator behavior. The owner's follow-up authorizes commit, push,
PR creation and merge. Release 0.57.0 carries the new stage-exit requirement;
earlier pinned RUNs keep their historical contracts. Resolve the exact branch and
candidate promotion authority under repository governance before those actions.
After a successful skills push, the repository requires the backup-preserving
local installer in the same turn. No new reboot or branch deletion is requested.

## Acceptance And Dependencies

| Contract | Expected outcome | Verification |
| --- | --- | --- |
| Product Definition | Post-draft research and accepted revisions precede author self-review and existing approval | Inspect skill, market guide and refinement reference |
| UI design | Structure/direction and connected HiFi have separate author checks, evidence and bounded repairs | Inspect skill, review lifecycle and UI pass |
| Responsive review | Preserve the four default Web targets (390/768/1024/1440 CSS px), intermediate-width checks, approved target sets and native size classes | Compare canonical Product responsive contract and modern-design-sources; distinguish 320 px accessibility stress from authored targets |
| Harness entry | Applicable current reviews and existing approvals precede execution; no UI-deferred shortcut | Inspect direct/managed entry and both README diagrams |
| Evidence integrity | No fabricated research, visual PASS, human decision or historical self-review | Cross-reference review limits and source identity rules |
| Documentation | Four language descriptions and diagrams agree | Diff review and repository verification suite |

## Document Impact

The new shared self-review reference is consumed by Product Definition, UI Design
Builder and Delivery Harness. Their existing stage references and README flow
diagrams must agree. The source repository has no consumer PRD or managed RUN.

## Change Log

| Change / request | Reason and scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| 2026-09-28: owner requested pre-delivery self-review | PRD/market, UI direction, HiFi and Harness handoff | First observation at main `d7083fb3`; clean detached worktree at the same SHA | Source contracts inspected; implementation and required checks pending |
| 2026-09-28: responsive and release follow-up | Retain the four Web review targets; publish through commit, push and PR merge | Working-tree contract and 0.57.0 release surfaces | Static checks and five sibling suites passed; Harness/golden-path suite and independent advisory review running |
| 2026-09-28: advisory review and bounded repairs | Clarify backend binding vs initial-delivery prerequisites; restore scoped diagram routes; use present-day catch-up reviews for earlier approvals; reconcile the live index | Working-tree source diff SHA-256 `c09bdfa1880b774405a493902c91a3bff7c9b5a547013d2a883336b346be1bf6`, excluding this Epic and index | Opus 5.5 advisory identified three medium and one low finding; parent checked and repaired them. Fresh exact-SHA independent review remains pending |
| 2026-09-28: verification checkpoint | Preserve installer refusal of untracked skill sources; stage the two new canonical source/test files under commit authority | Installer diagnostic failed before staging and passed after staging; no installer code changed | First Harness run had already failed and was cancelled after 704 seconds; its owned process tree exited. It is not a full-suite PASS. Fixed-candidate full suite and golden path remain required |
| 2026-09-28: owner confirmed release branch | Use `codex/pre-delivery-self-review` for the authorized commit/push/PR workflow | Fresh origin/main fetch remained `d7083fb3f43481127fd25252f200e5aa1d37e977`; branch created from that exact head with scoped changes preserved | Focused contract and static checks passed; prepare a fixed candidate for full verification and fresh security review |
| 2026-09-28: strengthen deferred-route regression | Check each localized scoped route and reject deferred-UI entry edges | `ef5e7942aa246a553531ebb2c8375a51aec72794`, following `3ab0eb3ad91f2129737bf2c96a53d21355017ed1` | Four focused tests and Pyflakes passed; fresh Opus security review `20260928-200528-8f0eb8b3` passed for ef5e794, with only a non-blocking request to clarify this record |
| 2026-09-28: repair bounded core context | Full Harness suite found 3,764 words against the existing less-than-3,600 limit; shorten repeated guidance and retain details in the shared reference | Follow-up working-tree change to Harness SKILL.md only, plus this result record; ef5e794 remains preserved | The 60 skill-contract tests pass after repair (`core-repair-contract-20260928-203518`). Complete exact-candidate regression, fresh security review and new exact-SHA promotion authorization remain required |

## Results And Remaining Work

Exact candidate `3ab0eb3ad91f2129737bf2c96a53d21355017ed1` received a security
PASS from fresh Opus 5.5 review `20260928-195504-d19be99d`. Its non-blocking
correctness finding showed the README regression accepted any route label.
The bounded follow-up checks each language's maintenance/enhancement label and
rejects deferred-UI edges into Harness or its route node, with negative examples
for every language and destination. This new commit invalidates the earlier
exact-SHA promotion authorization and requires fresh review/verification.

Candidate prepared in the attached `self-review-gates` worktree on the
owner-confirmed `codex/pre-delivery-self-review`, based on the freshly observed
origin/main `d7083fb3f43481127fd25252f200e5aa1d37e977`. The primary checkout remains
clean on `main`. Release, final exact-SHA verification and installation are not
claimed by this candidate record; retain their actual results in the release
handoff and PR evidence before claiming completion.

Verification evidence is retained outside the checkout under
`work/`:

- `setup-20260928-114325`: npm ci, Chromium installation and Python test requirements passed.
- `static-20260928-115552`: repaired source passes skill spec, Pyflakes, docs weight and diff whitespace checks; staged whitespace also passed.
- `other-20260928-114339`: Product Definition 240, UI 311 (browser checks required), Design System 120 (4 platform skips), Activation 56 and SEO 21 tests passed before advisory repairs.
- Before the ef5e794 test-strengthening repair, the 3 new `test_pre_delivery_self_review.py` checks and 96 Product Definition `test_skill_contract.py` checks passed (parent command transcript).
- `installer-diagnostic-20260928-115007`: the previously failing installer corruption test passed after new source files became tracked.
- `harness-20260928-114339`: failed/cancelled historical run, not release evidence. Golden path did not run.
- Independent advisory: Claude Code Bridge run `20260928-114441-bc47d037`, reported model `claude-opus-5-5`, completed read-only with findings. It is not an exact-SHA security PASS; repairs were checked by the parent only.
- Exact ef5e794: `static-20260928-200559` passed all static checks. `other-20260928-201358` passed Product 240, UI 311 with browser required, Design System 120 (4 platform skips), Activation 56 and SEO 21 tests. These remain historical results after the core-context repair.
- `harness-20260928-201358`: exact ef5e794 ran 1,385 tests with one core-word-count failure and 19 platform skips; golden path did not run. The supervisor and test process exited. This is not a full-suite PASS.

Handoff governance audit: shared rules are current against the observed installed
0.56.1 template (Git blob `07e8a2281ddd590caa67f3e902f78c6e31d15e5c`), with the
new additive self-review rule mirrored in source AGENTS and its template for
0.57.0. Keep the documented source-repository omissions and stricter Git Flow.
No consumer PRD, architecture or managed PLAN/RUN exists for this source task.
Existing ignore rules cover node_modules and Python caches; source, lockfile and
regression tests remain tracked. No logs or secrets enter the change.

At this repair checkpoint, release and installation remain pending. Commit the
bounded repair, then verify the new exact candidate and obtain its promotion
authorization. Retain subsequent verification, PR, main read-back, tag and
backup-preserving installation results in the release handoff and PR evidence;
this source record does not claim those later actions. Source is a 0.57.0
candidate; observed installed skills are 0.56.1 and loaded identity is unknown.
No branch deletion or reboot belongs to this release task.

## Later Repository Observation — 2026-09-29

The workflow-modernization task observed this work at `b591a618ba8454da8b9ec22b6ea633def2203c24` in its main baseline history (PR #133 in the commit subject). The local annotated `v0.57.0` tag peels to that commit. This corrects the current document index; the earlier candidate and verification history above remains intact. This local observation does not reverify remote CI, publication or the earlier installation.

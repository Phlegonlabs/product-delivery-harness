# EPIC-agent-delegation-contract: Enforce parent-owned agent assignments

Status: complete

## Problem And Baseline

At `b591a618ba8454da8b9ec22b6ea633def2203c24` (Harness 0.57.0), role guidance does not bind the actual executor. Product analysis joins results by role and position, and research has one instance. Direct UI work can bypass delegation. Managed selection assumes a run-wide driver and cannot express a host-owned external bridge.

## Accepted Scope

The owner requested multi-agent implementation of the discussed task decomposition, repeated researcher/explorer instances, role routing, parent-owned launches, dependency joins and result verification. On 2026-09-29 the owner named `codex/agent-delegation-contract` as the local branch. This is source maintenance with no consumer Product Definition or managed PLAN/RUN. UI impact: none; no product UI is authored. Agents share this checkout with one writer at a time. Other agents inspect read-only.

Source, tests, affected references, templates, four README descriptions and version surfaces are in scope. Existing approvals and historical runs retain their pinned semantics. No push, promotion, installation, deletion or publication is authorized by this record. No local-only artifact class is planned; verification logs and bridge requests stay outside the checkout.

## Acceptance And Dependencies

| ID | Expected outcome | Verification | Dependency |
| --- | --- | --- | --- |
| AD-01 | Two independent substantive research/exploration questions produce distinct same-role assignments when authorized and available; one question does not force fan-out | Focused packet and policy tests | Frozen question identities |
| AD-02 | Required results join by assignment/input identity, accepting reorder and rejecting duplicate, missing and stale results | Product graph tests | Explicit attempt/input binding |
| AD-03 | Direct and managed UI authoring resolve the host frontend role; missing mandatory delegate never silently becomes parent work | Routing/admission tests and contract review | Host role binding |
| AD-04 | Native and external dispatch derive applicable authorization; host eligibility is separate from model provider | Selector and transition tests | Observed capabilities and exact grants |
| AD-05 | Worker/reviewer leases and results retain requested and actual execution identity; mismatches cannot PASS | Result/transition tests | Fresh launch evidence |
| AD-06 | Flat parent-owned launches, dependency barriers and one writer per checkout remain enforced | Regression tests and review | Existing ownership guards |
| AD-07 | Fallback requires explicit model/provider unavailability, termination and partial-work reconciliation; missing tools/timeouts do not qualify | Focused negative tests | Host fallback policy |
| AD-08 | Old pinned runs keep their prior contract; descriptive docs and all version surfaces agree | Legacy tests, skill checks, full required suite | Versioned admission |
| AD-09 | PRD and HiFi/UI HTML author self-reviews execute at their stage exits; missing or stale evidence cannot count as a current pass | Entry/exit path audit and focused regression checks | Existing author-review and independent-review boundaries |
| AD-10 | Consumer AGENTS template requires a 500-physical-line hard cap for new code/test modules, KISS, first principles, responsibility-based splits and no speculative compatibility code; no Harness-source hard cap | Consumer bootstrap and existing-instruction preservation tests | `PROJECT_AGENTS.template.md`; owner scope clarification on 2026-09-29 |

## Document Impact

Update the shared delegation/runtime contracts, Product Definition research graph, UI author routing, worker packets, affected tests and four READMEs. Track existing oversized modules in `docs/epics/agent-delegation-module-debt.md`. Index this Epic. Preserve owner-specific model bindings outside generic skill defaults.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| 2026-09-29 entry and accepted scope | Owner authorized Multi Agent changes and exact branch; two explorers and one architect completed read-only analysis | Repository `product-delivery-harness`; baseline and observed HEAD `b591a618ba8454da8b9ec22b6ea633def2203c24`; clean main before branch creation | No implementation tests yet. Document sync reports loaded identity unobserved and first baseline required. Source and installed version observed 0.57.0. |
| 2026-09-29 upstream assignment batch | AD-01/02 and upstream AD-03/06: pure frozen packets, identity joins, distinct workers, current graph mode and UI role guidance | Working-tree changes on the same HEAD; implementer relinquished writer ownership after its batch | Worker reports 7 delegation tests, 247 Product tests, 311 UI tests and Product pyflakes passing; parent found and requested capability, identity, input-mutation and launch-effort regression coverage. Full candidate suite and independent review pending. First implementer invocation failed with terminal 429 before edits; same-model retry succeeded, no fallback used. |
| 2026-09-29 shared rules and candidate version | Shared parent delegation contract, direct route, template/local guidance, four README descriptions; breaking behavior targets 0.58.0 | Working-tree documentation and version surfaces; no commit or release | Managed role binding/receipt implementation and full verification remain pending. Existing large graph module keeps orchestration in one entry point; new packet construction and joins are isolated in a separate module. |
| 2026-09-29 managed role batch and follow-up scope | AD-03 through AD-08: per-node binding, guarded bridge routing, parent launch records and explicit recovery; owner additionally requested PRD and HiFi/UI HTML self-review audit (AD-09) | Same branch/HEAD; uncommitted source and tests. Host frontend effort changed by owner to high; reviewer stays xhigh. Generic source retains host-owned model policy | Worker reports 11 role tests, 45 graph tests, changed-file pyflakes and diff check passing. Reviewer recovery/result provenance still needs coverage. Parent shortened SKILL routing text after two skill-contract failures; rerun pending. Fresh read-only scenario evaluation found intended multi-instance waves and blocking behavior, plus upstream fallback wording and UI research storage gaps scheduled for repair. |
| 2026-09-29 500-line module cap (AD-10) | Owner confirmed the shared-principle change only for new modules and tests; existing baseline oversized modules are migration debt and were not split. Updated root/template guidance, four current README descriptions, pre-delivery producer/self-check identity wording and focused tests. Inspected updated Product/UI references; no direct contradiction required an edit | Working-tree changes on baseline `b591a618ba8454da8b9ec22b6ea633def2203c24`; `docs/epics/agent-delegation-module-debt.md` records 76 baseline modules and found the same 76-path class in the current tracked scan | External finite runner: 3 new cap tests, bootstrap template contract test and changed-file pyflakes passed at 180 seconds; docs weight is a non-gating report and ran; `git diff --check` passed. Full suite, independent review and any promotion remain pending. |

## Results And Remaining Work

### Publication Instruction — 2026-09-29

The owner explicitly requested commit, push, merge and local skills update, then waived independent review for this change. No new reviewer was launched and no independent PASS is claimed. Commits `08e6bc4` (delegation and result identity) and `78317b8` (consumer template principles) preserve the two implementation outcomes. Remote `main` was fetched at `b591a618ba8454da8b9ec22b6ea633def2203c24`; repository rules require a PR, the `validate` check and squash merging, with zero required approving reviews. No rule bypass is authorized or planned.

Fresh Product, required-browser UI, compiler, activation, SEO, golden-path, focused role/integration, skill-specification and pyflakes checks passed. The full Harness check is in progress under a finite 2,400-second deadline; its earlier 1,200-second timeout was not a passing result. Final exact-candidate CI, merge read-back/tree equality, exact-main CI, release tag and official local installation remain required. Release notes now describe 0.58.0 without retaining the earlier local-candidate wording; this is release preparation, not evidence of publication.

### Owner Scope Correction — 2026-09-29

The owner clarified that AD-10 applies only to projects adopting the AGENTS template, not to this Harness source repository. This supersedes the earlier source-cap and migration-debt interpretation below. The template retains KISS and first principles, explicitly requires responsibility-based splits before new code/test modules exceed 500 physical lines, and rejects speculative compatibility code. Required frozen interfaces remain protected. Root AGENTS returns to its original 500-line responsibility checkpoint with the source-repository exception stated explicitly.

Removed the Harness-wide source-size scan and its inventory dependency from the focused tests. The prior 76-module inventory is retained as superseded historical evidence, not an active backlog. Bootstrap tests now prove the consumer receives the template while existing instruction files and oversized consumer source remain untouched. All four current README descriptions and candidate notes reflect this scope. Three focused tests passed in `consumer-template-scope-1790677487990503800.log` in the external task directory. No other delegation implementation changed; independent review remains paused by owner instruction and full-suite completion remains outstanding.

The 60-test skill-contract suite initially found one stale migration-debt wording assertion. Updated it to the clarified consumer scope; all 60 tests then passed (`consumer-template-contract-green-1790677539847214700.log`). Skill specification, changed-test pyflakes and diff checks passed. Installed template identity remains 0.57.0; loaded identity is unobserved, so document sync requires review rather than claiming synchronized runtime adoption. The root source-specific size policy is an explicit owner choice, not template drift to repair. No install, commit or push occurred.

### Parent Integration Checkpoint — 2026-09-29

AD-03/04/05/07/08 integration repairs are working-tree changes at the same baseline HEAD. Added per-role native/bridge probe identity, result and failed-start provenance, reviewer recovery, atomic failed admission, legacy field gating and generated RUN role-table seeding. Split new role helpers by responsibility, kept every new module below 500 physical lines, and preserved pre-existing large modules as recorded debt. The new source inventory uses Git intent-to-add, with no staged content commit. Focused verification and the first broad audit are recorded below; final frozen checks and independent review are the next required gates.

Parent integration added retained result/failure receipts, availability-only recovery for mission/reviewer nodes, atomic result admission, mandatory UI-role validation, malformed-value guards, per-role reviewer probes and an empty unobserved role table in generated RUNs. New helper/test modules stay within 500 lines. The cap test uses the explicit debt inventory rather than requiring an old Git object in shallow CI.

The first broad Harness check ran 1,402 tests: 41 failures, 3 errors, 19 skips. This was an intermediate mutable-source audit, not final evidence. Root causes included missing role tables in new RUNs, legacy fixture version ambiguity, stale wording/probe handling, and installer refusal of untracked new source files. New skill sources were marked intent-to-add for the installer's tracked-source inventory; no content was committed or published. Focused reruns now pass: 10 new-RUN tests, 60 skill-contract tests, selector tests, structured security tests, 11 role tests, 7 role integration/shape tests, 3 failure-receipt tests, 2 returned-result tests and the current review admission test. Complete candidate verification and independent review remain pending.

Branch remains `codex/agent-delegation-contract`, HEAD `b591a618ba8454da8b9ec22b6ea633def2203c24`, with uncommitted working-tree changes. Installed template 0.57.0 still has the prior checkpoint policy; source 0.58.0 is a candidate, not a release. No real PRD or product UI was authored or visually accepted in this source-maintenance task. No release, installation, commit or push is claimed.

### Preserved Working-Tree Handoff — 2026-09-29

The frozen 60-file snapshot is retained outside the checkout at `candidate-20260929T095600786062Z`; its manifest SHA-256 is `d622b8c4843afde5b0d70eddc6356702cdde411424c7ce88becab4a0fcf3193a`. On those bytes, Product tests passed (253), required-browser UI tests passed (311), design-system tests passed (120, four platform skips), activation tests passed (56), SEO tests passed (21), and the enabled golden-path test passed. Skill specification, skill validation, pyflakes, module-cap tests and diff checks passed; docs weight ran successfully.

The full Harness check reached its actual 1,200-second deadline before completion. It exposed a legacy review-state object-identity regression; this is not a full-suite PASS. The runner terminated the owned process tree, and the recorded Python PID and the two child PIDs named in cleanup output were subsequently absent. The final follow-up changed only the review/result staging wrappers: pinned pre-role-contract RUNs retain in-place updates, while current role-contract RUNs retain atomic staging. The failing test was reproduced before repair. The complete `test_harness_v11.py` file and `test_agent_*.py` tests passed after repair. These final wrapper bytes are not represented by the frozen snapshot; the complete Harness suite still needs a fresh successful run.

Claude Opus 5.5 / xhigh independent review reached its 900-second deadline with no conclusion. Its process stopped; no availability fallback was used. The owner explicitly chose to preserve changes and not rerun review yet. Independent review remains incomplete, not approved. External check logs and process records remain in the task directory above. No checks or background services are intentionally left running at handoff.

The repository, branch and HEAD remain unchanged from the preceding checkpoint. Source rules intentionally differ from the observed installed 0.57.0 template in delegated role routing and the new-module 500-line hard cap; installed skills were not updated. Existing oversized modules remain the 76-path debt inventory, not a refactor performed by this change. The next owner must finish exact-candidate full verification and obtain a new instruction before rerunning independent review. Commit, publication, promotion and installation remain unperformed.

### Merge-Gate Review Repairs — 2026-09-29

Exact candidate `d2a4beb68eed881280562e5563821c6274f8cfa5` passed the full required suite locally, but the first no-force fast-forward promotion to `main` was rejected by repository rules because PR #134 had four unresolved review conversations. All four findings were confirmed against source: per-binding workspaces were ignored by dispatch, conflict and budget checks; `app_task` role bindings required no observed app capabilities; completed market-research results could be empty; and omitted effort rejected a host-default launch identity.

Fixed all four in the selector, the role-binding validator and the read-only assignment identity join. A completed research result now requires non-empty `findings` and `sources`. Added regression tests for each repair and updated the market-research guide plus all four README release notes. Focused role-dispatch, role-contract, selector, readonly-assignment and graph-identity suites passed. The repair creates a new candidate, so the verified `d2a4beb` authorization cannot be reused; exact-SHA promotion authorization must be renewed after the full suite passes on the repaired candidate.

### Creative Frontend Dispatch Brief — 2026-09-29

The owner added one more dispatch requirement: frontend work must be briefed for maximum creativity, not a mechanical page build. Added a canonical `maximum-creativity brief` to the delegation contract, the UI authoring orchestration packet rule, the seeded worker goal template and the ui-design-builder direction/HiFi prompt rule. The brief directs the writer toward the most distinctive, high-craft visual concept the frozen PRD allows while keeping pages, operations, states and copy bounded by the PRD. A cross-skill contract test now pins the brief across all four documents, and the four README release notes describe it.

### Later Repository Observation — 2026-09-29

The workflow-modernization task observed this work in its clean main baseline `bdae1d82acfd24cdeb2866f5480ff4d4d73b0b61` (PR #134 in the commit subject). The local annotated `v0.58.0` tag peels to that commit. This corrects the current document index; the earlier candidate and verification history above remains intact. This local observation does not reverify remote CI, publication or the earlier installation.

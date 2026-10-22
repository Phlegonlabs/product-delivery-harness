# Release 0.66.0: Fewer Review Rounds

Status: in_progress
Design workflow: enhancement
UI impact: none (skill contracts, validators and documentation; no product UI).

## Problem And Baseline

Every product and every Harness version paid many review rounds. AgentKiosk showed the cost: 8 HiFi review waves with 5 reviewers each, 3 Product Definition re-approvals, 29 tasks planned as 26 missions with 37 review nodes, and the Harness bundle re-adopted about five times mid-run. Its private bundles came from an unreleased Codex branch, so main never received that work.

Baseline: `origin/main` `32893537` (v0.65.3).

## Accepted Scope

Owner requests in chat on 2026-10-22: review the whole skill set (Product, UI, delivery, go-to-market, social content) on Fable once; change it with multiple Opus agents; review once on Opus 5.5; push, release, and sync every repository that uses the skills. No GPT review. Include the Codex AgentKiosk branch with the commit-boundary fix.

The owner later changed all remaining work to Sol 6.1 with high reasoning. This replaces the earlier Opus-only authoring and review choices. Fresh workers and the independent final reviewer use `gpt-6.1-sol` / `high`; historical execution evidence stays unchanged.

Kept: owner decisions, exact-SHA security review, HiFi 85/80, mandatory Impeccable critique and audit, real-browser evidence, Visual Approval, authorization and data-safety rules.

## Work

| Part | Source | Result |
| --- | --- | --- |
| Review boundaries | `review-batch-boundaries` (EPIC-review-batch-boundaries) | Feature-batch missions; one repair after all reviews; one contract per RUN |
| Codex AgentKiosk line | `integration-commit-recheck` (36 commits) | Compiler motion replay and CSP repairs, state coverage, retry head, role policy, integration ingestion, commit-boundary recheck (EPIC-integration-result-adoption) |
| Whole-skill review | Fable `claude-fable-5-1`, high, read-only | 83 gates (73 mandatory) inventoried; 7 change packages with disjoint files |
| P1 UI review scope | Opus writer, `ui-review-scope` | Scoped HiFi re-review, audit axes once, lead plus one Impeccable operator, repair classes, one revised direction study, carried rows, session reuse |
| P2 Diagnostic validator | Opus writer, `diagnostic-retention` | Retention values use the strict rule; no false defects |
| P3 Product contract gate | Opus writer, `product-contract-gate` | PRD check fails unreachable surfaces and opened states without exit; contract delta; one self-review; changed-section translation compare; two link inventories |
| P4 Identity churn | Opus writer, `identity-churn` | Design-round pin; identity finding once per session; audit reuse across compaction; one entry and one exit check |
| P5 Managed review topology | Opus writer, `managed-review-topology` | One combined-lens reviewer per mission; recorded clean merge chain skips the non-security code integration review; scoped final page quality |
| P6 Downstream read scope | Opus writer, `downstream-read-scope` | Compiler and Activation read the sections they use; preview browser inspection for motion, pseudo states and script-running Surface plates |
| P7 Token diet | Opus writer, `token-diet` | Entry checklist, legacy-pins file, deduplicated rules |
| Integration fixes | Parent | CSP diagnostic and loader fixtures cover the full manifest; ingestion fixture no longer leaks a test path; motion verifier writes UTF-8 |

## Verification

Recorded with the release candidate below. Earlier evidence: `review-batch-boundaries` full delivery-harness suite 1752 OK (21 skipped); release base `fc69958d` suites ui-design-builder 417, design-system-compiler 258 (5 skipped), product-definition-builder 306, product-activation 75, seo-growth-review 22, all OK.

## Remaining Work

Sol 6.1 / high review of the final candidate, PR and CI, main landing, tag, installation, and consumer syncs. AgentKiosk remains report-only; its own parent handles any later adoption at a quiescent boundary.

## Recovery On 2026-10-22

The owner asked this chat to finish the remaining packages and release steps. The original SA, SB and SD CLI processes have exited. No writer was restarted over a live predecessor.

`int` is detached at `f56b249f`. The `release-0.66` branch was still at `fc69958d` in `rel`. The parent fast-forwarded that branch to `f56b249f`; further integration belongs in `rel`. Both checkouts were clean at that checkpoint.

| Package | Observed head | Remaining work |
| --- | --- | --- |
| SA | `f56b249f` | Six dirty scripts; finish the validator changes and focused tests before committing |
| SB | `40b75478` | Two dirty files after its first commit; finish the transition changes and focused tests |
| SC | `b4733597` | Two committed changes, but its report says partly complete; resolve the remaining joins and imports, then verify without shims |
| SD | `f56b249f` | Eleven changed paths, including staged deletions; finish archive/publication changes and tests |
| SEC | `d0bc5450` | Committed; integrate after its dependencies and align the remaining prose |
| DH-A | `b4e9be90` | Four commits and eight dirty references; inspect and finish before integration |

Fresh recovery checks: SA and SB changed-script pyflakes passed. SD pyflakes failed on three unused test imports. DH-A, SC and SEC each passed 64 delivery skill-contract tests. These checks do not validate the combined candidate. SC's original shim-only results remain limited evidence. The full release matrix and final independent review are still pending.

One fresh `claude-opus-5-5` / `xhigh` bridge attempt returned HTTP 429 before using tools. It reported a session-limit reset at 14:50 UTC-7. The process exited; no model fallback was used. A one-time continuation is scheduled in this chat for 14:55 UTC-7 on 2026-10-22.

The installed bundle remains `0.65.3`, digest `e17abe58a295bc7b53cf2c3cc654a4164136b61aaf0be0b194067cfcb2496e5a`. Loaded identity is unknown. The installed template is current by meaning for the source repository's retained local exceptions; no instruction file was replaced. Document sync reports first-observation review and unknown loaded identity, not PASS.

The [recovery record](C:/Users/mps19/.codex/visualizations/2026/10/22/01a164d4-5532-74c0-9a52-6683f6198131/work/release-recovery.md) links exact dirty-diff fingerprints, retained patches, command logs, launch evidence and original briefs. No push, PR, tag, installation or consumer edit occurred in this recovery step. The original seven consumer targets still need confirmation from the earlier launch plan; a broad Harness-reference scan is not that target list.

### Sol Continuation

The owner replaced all remaining executors with Sol 6.1 / high. The parent deleted the quota-reset heartbeat `harness-0-66` and resumed immediately. Four fresh native workers own the existing SA, SB, SD and DH-A checkouts. The parent retains serial integration and SC prerequisite work. This changes no global agent configuration or consumer RUN pin.

SC is clean at `b1b95ff1`. New commits localize the host identity keys (`13bcc51b`), use one strict Product/UI join (`199f052e`), and remove container reuse and duplicate timing machinery (`b1b95ff1`). The join passes 23 focused tests, including missing-pin authority enforcement. The final runtime passes 18 focused tests, including retained command, cwd and executable tampering. Changed-file pyflakes and whitespace checks pass. Full host integration tests still need the actual merged SA/SB modules.

DH-A is clean at `74ee543f`, with its earlier partials committed and 89 focused tests passing. A multi-mission final-review repair path remains an integration issue for SA/SB; the singleton template test does not prove it.

The original consumer inventory was recovered from the prior session: ticketradar, hardwareprices, jolvex-platform, dilution-radar, agentcommercehq, agentic-commons-site and agentkiosk. AgentKiosk remains report-only. The [scope inventory](C:/Users/mps19/.codex/visualizations/2026/10/22/01a164d4-5532-74c0-9a52-6683f6198131/work/seven-consumer-scope.json) records the source and initial Git state. Preserve dirty work in ticketradar, agentcommercehq and agentkiosk. Instruction syncs wait for the verified release and installation.

### Integrated Script And Review Batch

All six remaining heads are integrated at `d6388113`, in the requested order: SA `03b6a492`, SB `a9cad550`, SC `b1b95ff1`, SD `59def2c5`, SEC `d0bc5450`, and DH-A `74ee543f`.

The SB predecessor overlapped two SA-owned test files; the merge preserves the final verified SA versions. The retired container-cache contract test stays removed. DH-A's modern template-budget regression is preserved in `test_validator_diet.py`; its fallback mutation became an assertion against the actual merged template. That targeted real-validator test passed before the merge commit.

SA records 505 cutover checks, 63 skill contracts, 112 image/contract checks, 44 repair checks, and two actual repair journeys passing on frozen real combined inputs. SB records 212 passes and three Windows symlink skips across 215 focused checks. SD's scoped checks and targeted repairs remain at their original inputs; subsequent real-source overlays found strict fixture prerequisites, not an obsolete API call. These are worker-input results, not a PASS for the merged release candidate.

Four consumer structural comparisons added no errors and preserved every PLAN/RUN byte. The full consumer source joins remain unverified after a bounded AgentKiosk baseline timeout. No consumer was adopted or edited. Current `adopted` history is readable only for pins below 0.66 and always defers new dispatch to the pinned-bundle/restart route.

Native CI now selects `test_push_archived_candidate.py` instead of the retired trusted-host test (`9742a5ac`). Five shard tests and both native planner invocations passed. Next: actual merged-code checks, ALIGN, README/CHANGELOG cleanup, fresh Sol 6.1 / high review with security, and required fixed-candidate CI before publication.

### Final Candidate Preparation

The merged-code checks finished at `c4a419cf`. Four atomic commits add the actual conditional repair journey to native CI and update approved-source fixtures. Host execution retains executable-identity tamper rejection. Archive tests accept committed screenshots and reject working-tree-only evidence. Production guards were not weakened.

The actual merged checks passed: core 336; results 177 with two platform skips; ingestion nine; candidate/closeout 55; archive 33 with three skips; host 18 with two skips; platform joins 65; source bindings 13; skill contracts 63; CI planner six. Six isolated test discoveries imported successfully. Pyflakes and whitespace checks passed. The local `.claude/merged-code-sol1/handoff-final.json` retains exact commands, inputs and logs; all 48 captured processes exited. These focused results do not replace final candidate CI.

ALIGN `eefe606f` merged as `0965e151`; RSA `fd57ce91` merged as `871254a7`. Runtime references describe the current drivers, host checks, archive proofs and bounded repair mission. All four READMEs retain their covers, UI prompts and five newest history entries. Older English history moved unchanged into `CHANGELOG.md`; the redundant Chinese workflow copy was retired. The remaining UI freshness pointer was corrected in `63b97bea`.

After integration, 63 skill contracts, three README checks and three documented-command checks passed. The parent document inventory returned `review_required`: first observations, retained historical names and unknown loaded identity remain explicit. The installed bundle is still 0.65.3. Intentional source-repository template exceptions remain; no consumer PLAN/RUN was rewritten.

The [release receipt](C:/Users/mps19/.codex/visualizations/2026/10/22/01a164d4-5532-74c0-9a52-6683f6198131/work/release-receipt-0.66.0.json) records the exact candidate, independent review, CI, main/tag readback, installation and consumer outcomes as they occur. They are pending at this preparation checkpoint. No source push, PR, tag, installation or consumer edit has occurred yet.

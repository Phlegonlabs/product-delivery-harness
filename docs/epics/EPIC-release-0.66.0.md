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

Sol 6.1 / high review of the final candidate, PR and CI, main landing, tag, installation, and consumer syncs. AgentKiosk's active RUN adopts the release once at a quiescent boundary through its own parent.

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

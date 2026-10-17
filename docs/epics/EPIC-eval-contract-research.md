# EPIC-eval-contract-research: Define eval acceptance and handoff

Status: complete

## Problem And Baseline

The owner wants future projects to freeze an eval rubric and pass rate in the
product contract, then deliver an eval harness and an operating runbook.
This round studies how that fits the existing Product Delivery Harness.

- Repository: `product-delivery-harness`.
- First observation: 2026-10-03 00:11 UTC-7.
- Entry: clean detached HEAD `bdae1d82acfd24cdeb2866f5480ff4d4d73b0b61`.
- Research branch: `codex/eval-contract-research`, created at that exact HEAD.
- Local `main` and cached `origin/main` also name that SHA. No fetch or live
  remote-head claim is made.
- Source Harness: `0.58.0`. Observed installed Harness: `0.59.0`.
- Installed bundle digest:
  `cdd97b1151213988ca89c1fafd19af28405c2c046ddea96cd28405bb4635ab7a`.
- Loaded-at-session-start digest: unobserved. The document check returned
  `review_required`: `loaded_identity_unobserved`, `baseline_review_required`.
- This source repository has no consumer PRD, product architecture or active
  PLAN/RUN to extend. No placeholder product package is needed.

## Accepted Scope

Decision source: the owner's 2026-10-03 instruction to research eval rubric,
pass rate, eval harness and runbook integration on another branch.

The parent owns a Traditional Chinese research proposal, this Epic and its
index entry. UI impact: `none`. Route: small, direct research; no PLAN/RUN.
The owner instruction authorizes the local research branch. The effective
machine instructions require an atomic local commit of this work.

Implementation, new global thresholds, publication, promotion, installation,
new worktrees and cleanup are outside this round. A proposed contract is not
an approved rule for future projects.

## Acceptance And Dependencies

| Research question | Expected result | Verification | Dependency |
| --- | --- | --- | --- |
| EVAL-Q1 | Locate product-contract ownership and propose rubric/threshold inputs | Source paths and line evidence from a read-only explorer | Current source at the baseline SHA |
| EVAL-Q2 | Locate delivery gates and propose reproducible eval/handoff artifacts | Source paths and line evidence from a separate read-only explorer | Current source at the baseline SHA |
| EVAL-Q3 | Explain pass-rate arithmetic, failure rules, adoption steps and open decisions | Parent synthesis, primary-source references and document checks | Q1 and Q2 results |

Direct delegation follows the repository's sibling-exploration requirement.
The parent is the only writer. Helpers have no write, commit, test/cache,
service, external-action or further-delegation scope.

| Assignment / attempt | Executor | Frozen input | Result |
| --- | --- | --- | --- |
| EVAL-Q1 / EVAL-Q1-A1 | Native `code_explorer`, task `/root/eval_product_contract` | Baseline SHA; clean skill sources | Returned matching repository/branch/SHA; Product Definition AI-EVALUATION/TEST coverage and approval-digest gaps located |
| EVAL-Q2 / EVAL-Q2-A1 | Native `code_explorer`, task `/root/eval_delivery_gate` | Baseline SHA; clean skill sources | Returned matching repository/branch/SHA; verifier/acceptance/H1-H2 lifecycle and operating-runbook gap located |

The native role definition binds `zai-coding/glm-5.3-flashx` / `max`.
Observed execution identity and any unknown provider/session facts are
recorded with the returned results; requested identity alone proves nothing.
Both helpers reported the runtime-declared FlashX identity; neither exposed
independent provider/session telemetry. Those facts remain unknown. Results
were joined by the explicit assignment/attempt IDs, not their return order.
No availability fallback has been used. Both tasks completed without writes.
These were source explorations, not a formal independent review PASS.

## Document Impact

| Source | Artifact | Recheck |
| --- | --- | --- |
| Owner's research request and current source contracts | `docs/research/eval-contract-integration.md` | Current/proposed behavior, internal links and examples |
| Research status | This Epic and `docs/DOCUMENTS.md` | Scope, baseline, checks and remaining work |

No canonical skill, template, schema, runtime or published README behavior
changes in this round. Gitignore impact: none; only tracked Markdown is added.
Transient inspection logs are stored outside the checkout.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| 2026-10-03 entry and research branch | Freeze the observed baseline; scope research before implementation | Baseline SHA above; clean working tree before branch creation; scoped documents will be `working-tree` until committed | Git root/HEAD/branch/status observed; document inventory requires semantic review; research synthesis pending |
| 2026-10-03 research synthesis | New research report, this Epic and two DOCUMENTS rows; UI impact none; source skills unchanged | `working-tree` report SHA-256 `6bc41fc5445777bdc6995312084c837721940256d6642d07f57e7a927e18427c`; HEAD remains the baseline until the scoped commit | Both source assignments complete; parent reconciled competing proposals; diff whitespace check passed; document/link/arithmetic checks and commit checkpoint recorded below |

## Results And Remaining Work

The [research proposal](../research/eval-contract-integration.md) is complete.
It recommends a frozen project-specific eval contract/report and arithmetic
checker feeding the existing all-required-pass delivery acceptance semantics.
It defines future-product applicability, PRD inputs, case/trial rules, critical
and slice gates, reproducible handoff, H1/H2 evidence handling and implementation
outcomes. Thresholds and implementation remain proposals.

The parent reconciled Q1's separate eval artifact with Q2's suggested generic
acceptance-v2 pass policy. It selected a narrow eval artifact/checker plus the
existing acceptance assertions, preserving required functional tests. No RUN
schema, scheduler or global percentage is added.

### Handoff Document Audit

- The installed `PROJECT_AGENTS.template.md` is from observed `0.59.0`, SHA-256
  `0d5064d94c0072ad2d1f06f3b516dab328d425be79454df10b50ce6f44b2470e`.
- Shared entry/checkpoint, evidence, authorization and data-preservation rules
  are current by meaning. Installed template design rules differ: new
  `ui-design/3` / `design-system/4` versus this source's `ui-design/2` policy.
  That affected UI subsection is stale relative to the installed template;
  a safe source-version merge is unresolved, so AGENTS stays intact.
- The installed ordinary dual-branch policy differs from source main-only.
  Source AGENTS explicitly declares Git Flow a local choice; preserve it.
- Loaded-at-start identity remains unknown; document inventory is not a skill
  adoption, approval, capability or delivery PASS.
- This research report, Epic and index agree. Existing unrelated DOCUMENTS
  rows still describe 0.57/0.58 candidates despite this checkout's 0.58 HEAD;
  propose reconciling them in their own outcomes, without rewriting history.
- No consumer product/design documents, generated tasks view or PLAN/RUN are
  applicable. No source, release, installation or product-verification claim
  is made by this research outcome.

### Verification And Next Action

Source reading and both returned assignments support the research conclusions.
Primary OpenAI and Anthropic eval guidance was checked on 2026-10-03; URLs are
in the proposal. Document verification checks only this research scope; the
full source skill suites and formal independent review are not claimed.

- Ten local Markdown link targets exist within this checkout.
- Eight policy examples and the 94.95% versus 95% rounding boundary checked.
  This validates the proposal's arithmetic, not an implemented eval checker.
- `git diff --check` passed. Scoped comparison against the baseline confirms
  no changes to skills, AGENTS, READMEs, package version or `.gitignore`.
- The handoff document check covers the original inventory plus all three
  research documents. It returned exit 1 / `review_required`, with only
  `loaded_identity_unobserved` and `baseline_review_required`; no missing
  required research document was reported.
- Inspection report retained outside the checkout at
  `document-sync-handoff.json`.
- The local research commit contains only the report, this Epic and the
  DOCUMENTS entries. Resolve its SHA from `git log -1 -- docs/research/eval-contract-integration.md`;
  the commit does not need to name its own hash in its content.

The next implementation owner must select the actual target source/release,
accept the proposed scope and freeze each adopter's rubric, sample manifest,
threshold and trial semantics. Research authority grants no implementation,
push, promotion, tag, install, worktree removal or branch deletion.

# Review Batch Boundaries

Status: complete (local source; release and installation are outside this task)
Design workflow: enhancement
UI impact: none (planning and review contracts; no product UI changes).

## Problem And Baseline

A consumer run (AgentKiosk Checker v1, PLAN revision 2) planned 29 tasks as 26 missions and 37 review nodes: 26 per-mission reviews, 6 per-page visual reviews, 4 integration-stage reviews and 1 early-journey reviewer. 23 missions held a single task. Every review costs a packet, a dispatch, reconciliation and an integration, so review overhead dominated the run.

The cause was in the Harness guidance, not the consumer: the Mission Cohesion Gate split a mission whenever one clause could pass review alone, preferred the smaller mission, and gave every page its own mission and visual review. Review count follows mission count.

The same run also re-adopted new Harness bundles and role policies several times mid-run, and repaired findings as they arrived instead of after all reviews of a candidate returned.

Baseline: `origin/main` `32893537` (v0.65.3). Branch `review-batch-boundaries`, clean at start.

## Accepted Scope

Owner requests in chat on 2026-10-22: converge review boundaries so a repair batch has a clear end; plan missions as about eight feature batches with fine tasks and atomic commits inside; fix the tool version and model policy for a run; and "不要再出現類似的問題：那麼多個 review 節點".

- A mission is a feature batch: one user-visible feature or one shared foundation, owned by one writer role. Split only for a different writer role, a shared contract freeze, parallel work worth one more review, or a batch too large for one worker session. A one-task mission records its reason. Planners count review nodes before readiness.
- One visual review per frontend feature batch, not per page.
- The 10-20 minute slice applies to each task, not the whole mission.
- Repair starts after every required review of the candidate returns. The re-review checks the original findings, the changed code and its direct consumers. Non-blocking suggestions go to the backlog. A failed re-review stops at `blocked`.
- One RUN keeps one adopted Harness contract and role/model policy. Only a run-blocking defect is adopted mid-run, once, with all known blocking fixes together.

Kept unchanged: the RUN-v11 single-mission preintegration coverage rule, integration-stage surface reviews, the all-mission security review, the initial-plus-one-re-review budget and owner gates. No PLAN/RUN schema or validator change.

## Acceptance And Dependencies

| ID | Expected outcome | Verification |
| --- | --- | --- |
| RBB-1 | Mission sizing guidance plans feature batches and counts review nodes | `test_skill_contract.py` mission topology assertions |
| RBB-2 | Repair waits for all required reviews; re-review is targeted; suggestions never make `fix_required` | `test_skill_contract.py` root-cause assertions |
| RBB-3 | One RUN keeps one adopted contract and policy | `test_skill_contract.py` runtime-upgrade assertions |

## Document Impact

`execution-task-decomposition.md`, `stages/managed-delivery.md`, `contract-and-traceability.md`, `graph-orchestration.md`, `gen-verify-correct.md`, `runtime-upgrades.md`, `platform-archetypes.md`, `design-input-updates.md`, `governance/source-maintenance.md`, the PLAN and worker templates, the four READMEs and `docs/WORKFLOW.zh-TW.md`.

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| Feature-batch missions, targeted repair, run-scoped pin | Owner requests above; files in Document Impact | Branch `review-batch-boundaries` commits after `32893537` | See Results |

## Results And Remaining Work

Commits `0bf5443a`, `bef575fb` and `c226b714`. Each commit's staged tree passed `test_skill_contract.py` (65). The final tree passed `check_skill_spec.py`, `docs_weight.py` (+204 words against v0.65.3), `git diff --check`, and 11 doc-reading test files: cross_skill_pipeline 18, docs_weight 13, enhancement_entry_contract 8, governance_entry_routes 7, graph_orchestration 45, platform_archetype_example 1, pre_delivery_self_review 4, project_template_rules 4, readme_structure 5, reference_library 13, plan_verifier_bindings 9. The full delivery-harness suite result is recorded with the release. A Fable (`claude-fable-5-1`, high) whole-skill review followed, covering PRD, UI design, design system, delivery, activation, SEO, GTM and social content. Its change plan is carried out as the next release. Release, installation and push are not done in this Epic.

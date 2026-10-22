# Retain reservation identity when the owner changes role policy

Status: local implementation and focused verification complete; independent source review and isolated adoption pending.

The owner instructed AgentKiosk to use GPT-6.1 Sol for all new work on 2026-10-22. Its unchanged PLAN leaves model and effort selections to host policy. The retained M01 author was Opus/high. Current validation re-resolves every retained reservation against today's defaults, so changing the frontend policy invalidates both historical M01 workers.

Baseline runtime candidate: `1dea7fd44680b1cce30accaa7dcf9616a01335c2`, with documentation through `0dba3bcd3086a70e7ca047349123e90c56506d3b`. AgentKiosk uses fixed private bundle-004, digest `598e80d7449ec071c4d2a0cdc27b92ac70a7984361f46e05bc4798a6840ff331`. M01 recovery has passed. Complete its ordinary Sol review and integration before another runtime adoption. This source work changes no product, design, shared installation or consumer state.

## Required outcome

Add one guarded `update-role-bindings` command. At an authorized quiet boundary, it validates an explicit role-policy patch, expected current digest and observed capabilities. It records versioned before/after maps and exact reservation joins. New selections use only the current map. Historical reservations retain their original policy through exact mission/review, assignment, node, worker and attempt identity. Preserve their runtime bindings, launches, receipts, results, counts and review obligations.

Use existing locks, full prospective validation and PLAN/RUN CAS. Identical replay is a no-op; conflicting reuse fails. The command changes no provider, PLAN, grant, skill pin, contract adoption, attempt or outcome. Runs without the optional extension keep existing behavior. Keep fallback evidence strict and bind retained fallback history to its original policy. Do not add a second scheduler or per-node policy override.

## Verification

Prove old Opus reservations remain valid and new frontend/backend/general reservations resolve to explicit native Sol. Reject archived-policy selection by a new reservation, tampered old identity, stale digest, active work, foreign lock, malformed or unavailable capability, conflicting replay and requested/observed model mismatch. Preserve original result, failure, launch and ingestion-reconciliation checks. Run focused role, receipt, transition and reconciliation regressions, plus source static checks. A fresh Sol code/security review must bind the fixed candidate before a new isolated bundle is proposed.

## Change log

- Native code architect `/root/model_policy_architecture_007`, configured as GPT-6.1 Sol/xhigh, verified the actual M01 mismatch in memory. All 63 runtime nodes retain null model/effort choices, so no PLAN revision is needed. Existing observation/adoption commands cannot update role policy. Source commit `ada2b750` changes a separate Dynamic Workflow helper and supplies no managed migration route. Its whole tree must not replace this private runtime. The parent accepted the minimal additive command and exact-reservation history design for local implementation under the owner's model instruction. Source reading was read-only; no review PASS or consumer mutation follows from it.
- 2026-10-22: `/root/role_policy_implement_007` implemented the accepted feature on `codex/agentkiosk-motion-compiler`, based at `817b73c4f24b9f9f4fd9ec56ac7f763691940911`. The host interrupted that Sol writer before commit. After confirming it had stopped, the parent assigned `/root/role_policy_continue_008` the same checkout and scope. This was a Sol continuation, not availability fallback. The continuation preserved its 13 dirty feature files and all prior check receipts.
- The feature adds guarded `update-role-bindings` and optional `role_binding_updates` schema 1. Exact reservation joins retain original binding, input/candidate and launch snapshots. First-boundary capture prevents a later policy from relabelling old attempts. New reservations use the current map. The update validates the current pair, held parent lock, quiet boundary, surviving authority, complete proposed map and explicit PLAN options. Existing OS locking and final PLAN/RUN comparisons still guard persistence. Identical replay preserves bytes; conflicting reuse fails.
- The source scope is the new policy module and its tests, three narrow role/manifest/transition integrations, four runtime references and all four README translations. This Epic and its index record the result. UI impact is `none`. The six other stage-bound skill trees, release/version files, consumer state and shared installation remain outside this change.
- The continuation reproduced numeric JSON overflow with `1e999` and `-1e999`. Python's constant hook did not reject those values. A finite-number parser now rejects both. The failing receipt remains in `checks/role-policy-008-overflow-before-1792660994150013000.json`; the final 10-test suite passed in 69.750 seconds. Its receipt is `checks/role-policy-008-final-10-1792661001981516300.json`.
- Retained `role-policy-007` checks passed 61 transition tests, 19 agent/receipt tests, 10 dispatch tests, two ingestion tests, one review-result test and four stopped-predecessor tests. Static analysis, skill specification and documentation weight checks passed. Those executions preceded the finite-number repair; they are retained evidence, not fresh executions. Earlier provider-options/fallback fixture errors, a model-tamper assertion and a RUN-race assertion remain in their original failed logs. Later suites passed. All receipts live under `C:/Users/mps19/AppData/Local/Temp/agentkiosk-implementation-20261021-01/checks`.

## Continuation handoff

The direct route uses one writer and creates no source PLAN/RUN. The source has no applicable product PRD or UI package. The four READMEs and runtime references define this internal behavior.

The continuation read the source instructions, required governance, changed references, README sections, Epic and index. Document sync still reports first-observation review, unobserved loaded identity and retained README migration/history names. Those findings do not prove a loaded runtime or an installation. The observed shared installation reports version `0.65.2` and bundle digest `ea3f1959e69ad681a3e3972ffed11e87ddf2172cf5f07b0652541081f8e7aacd`.

The installed template SHA-256 is `d9d5b85e37283031068223317d85a2431fc3438b91dc502d61dadff4d50936a9`. The source's stricter delegation rules and documented source-only omissions remain intentional. Shared rule meanings are current for this scope; no instruction file was replaced. Loaded-at-start identity remains unknown.

The checkout-external `role-policy-008/candidate-fingerprint.json` records the final feature bytes. Its credential-pattern scan covers changed content only and does not replace independent security review. The parent must review the exact local commit before proposing a new isolated bundle. The full release matrix, publication, installation and consumer adoption remain pending. A four-role native Sol/xhigh JSON and command example remain proposal-only in `role-policy-008` scratch.

## Remaining authority

The model choice is settled. Installation and adoption of a new fixed isolated digest remain separate from local implementation and require their existing owner boundary. Preserve bundle-004 and all original evidence until that step succeeds. No shared update, publication, deployment or cleanup is part of this repair.

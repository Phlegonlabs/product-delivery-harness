# Retain reservation identity when the owner changes role policy

Status: bounded source repair accepted for local implementation; no new bundle or consumer update adopted.

The owner instructed AgentKiosk to use GPT-6.1 Sol for all new work on 2026-10-22. Its unchanged PLAN leaves model and effort selections to host policy. The retained M01 author was Opus/high. Current validation re-resolves every retained reservation against today's defaults, so changing the frontend policy invalidates both historical M01 workers.

Baseline runtime candidate: `1dea7fd44680b1cce30accaa7dcf9616a01335c2`, with documentation through `0dba3bcd3086a70e7ca047349123e90c56506d3b`. AgentKiosk uses fixed private bundle-004, digest `598e80d7449ec071c4d2a0cdc27b92ac70a7984361f46e05bc4798a6840ff331`. M01 recovery has passed. Complete its ordinary Sol review and integration before another runtime adoption. This source work changes no product, design, shared installation or consumer state.

## Required outcome

Add one guarded `update-role-bindings` command. At an authorized quiet boundary, it validates an explicit role-policy patch, expected current digest and observed capabilities. It records versioned before/after maps and exact reservation joins. New selections use only the current map. Historical reservations retain their original policy through exact mission/review, assignment, node, worker and attempt identity. Preserve their runtime bindings, launches, receipts, results, counts and review obligations.

Use existing locks, full prospective validation and PLAN/RUN CAS. Identical replay is a no-op; conflicting reuse fails. The command changes no provider, PLAN, grant, skill pin, contract adoption, attempt or outcome. Runs without the optional extension keep existing behavior. Keep fallback evidence strict and bind retained fallback history to its original policy. Do not add a second scheduler or per-node policy override.

## Verification

Prove old Opus reservations remain valid and new frontend/backend/general reservations resolve to explicit native Sol. Reject archived-policy selection by a new reservation, tampered old identity, stale digest, active work, foreign lock, malformed or unavailable capability, conflicting replay and requested/observed model mismatch. Preserve original result, failure, launch and ingestion-reconciliation checks. Run focused role, receipt, transition and reconciliation regressions, plus source static checks. A fresh Sol code/security review must bind the fixed candidate before a new isolated bundle is proposed.

## Change log

- Native code architect `/root/model_policy_architecture_007`, configured as GPT-6.1 Sol/xhigh, verified the actual M01 mismatch in memory. All 63 runtime nodes retain null model/effort choices, so no PLAN revision is needed. Existing observation/adoption commands cannot update role policy. Source commit `ada2b750` changes a separate Dynamic Workflow helper and supplies no managed migration route. Its whole tree must not replace this private runtime. The parent accepted the minimal additive command and exact-reservation history design for local implementation under the owner's model instruction. Source reading was read-only; no review PASS or consumer mutation follows from it.

## Remaining authority

The model choice is settled. Installation and adoption of a new fixed isolated digest remain separate from local implementation and require their existing owner boundary. Preserve bundle-004 and all original evidence until that step succeeds. No shared update, publication, deployment or cleanup is part of this repair.

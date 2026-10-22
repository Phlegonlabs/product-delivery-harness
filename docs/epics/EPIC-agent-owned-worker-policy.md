# Agent-Owned Worker Policy

Status: in_progress
Design workflow: maintenance
UI impact: none (execution policy and skill instructions)

## Problem And Baseline

The owner wants agent configuration to choose workers; skills should not duplicate worker restrictions.
Baseline: clean `da6d3e7e2d3881b8c7de2f5d4ae071a8d4eaa094` on `codex/ui-acceptance`, observed 2026-10-21.
The [previous outcome](EPIC-frontend-author-handoff.md) retains its verified stage routing and visual-input history.
This is a new policy-ownership outcome; it does not rewrite that closed result.

## Accepted Scope

The owner confirmed moving worker identity, model, effort, fallback and delegation choices to agent/AGENTS configuration.
Skills retain work methods, complete visual handoff, 85/80 quality thresholds and necessary verification.
Preserve action authorization, data protection, actual execution evidence and pinned historical run semantics.
Keep existing design Opus/xhigh and implementation Sonnet/xhigh decisions in the agent authority.
Canonical shared skills and local wrapper instructions/defaults are in scope where they duplicate these decisions.
No product UI, deployment, publication, core-bundle installation or host reload is requested.

The parent is the sole writer; two read-only sibling explorers inspect shared contracts and host wrappers separately.
This is direct source maintenance with one coherent verification sequence; no PLAN/RUN is needed.
Local atomic commits are authorized by repository instructions. No push is authorized.
Gitignore impact: none; evidence and recoverable host backups stay outside the checkout.

## Acceptance

| ID | Expected result | Verification |
| --- | --- | --- |
| AWP-1 | Shared skills defer executor, model, effort, fallback and delegation selection to agent policy | Live-source and caller review; applicable source contracts |
| AWP-2 | Host wrappers consume explicit agent choices without competing hardcoded policy | Focused positive/negative checks and separately hash-bound host evidence |
| AWP-3 | Visual inputs, 85/80, necessary review, authorization and execution provenance remain intact | Applicable UI/source checks and fresh fixed-candidate independent review |
| AWP-4 | Existing pinned managed records retain their original meaning | Scope/diff audit and relevant runtime regressions if executable behavior changes |

## Change Log

| Observation | Result | Remaining work |
| --- | --- | --- |
| 2026-10-21 entry | Baseline clean. Owner confirmed the broad worker-policy separation. Two read-only assignments inspect shared rules and host duplicates. | Reconcile their evidence, update the smallest coherent live scope, verify and review. |

The entry inventory records unknown loaded identity, first-baseline review and inspected README migration pointers.
The installed core digest is `f635763875e40ad30f112933c3f78efbf9cebb5501eb13ea57d4b5dabb8ce28b`; it is not the loaded identity.

## AWP-1 Source Policy

Effective host policy is `C:/Users/mps19/.codex/AGENTS.md` plus installed agent definitions under `C:/Users/mps19/.codex/agents/`.
Repository AGENTS now identifies those effective sources instead of copying their concrete models.
Shared live instructions defer author identity, staffing, review fan-out and fallback choice to that agent policy.
UI research no longer requires a separate native instance for each question; question packets and result joins remain distinct.
HiFi staffing has no skill-defined lead/specialist count; one wave and one consolidated assessment remain required.
The actual UI writer still reads the complete pinned design skill and the source-bound visual inputs.
The four README descriptions and existing document-contract assertions now match that ownership.

No managed schema or executable selector changed. Existing `frontend_worker`/`reviewer` strings remain serialized responsibility labels, not required native agent names.
RUN-v11 lease, flat-topology and typed availability-failure receipt formats retain their original compatibility meaning.
This change does not claim those formats support unimplemented nested graphs or arbitrary recovery records.
Actual executor bindings remain configurable; required independent review, exact-SHA evidence and grants remain enforced.

Focused checks passed: 65 Harness contracts, 14 UI document contracts, 18 cross-skill contracts, nine UI-admission cases, ten role-dispatch cases and three failure-receipt cases.
The first complete 399-case UI run had two old-wording assertion failures and two platform skips; both assertions were updated and the 14-case document suite passed.
The first Harness run had four old-wording failures and a cp1252 log-tail encoding error; the corrected UTF-8 run passed all 65.
Skill specification, document weight and whitespace checks passed. A fresh unified candidate check and independent review remain pending.
Host sources are still unchanged at this checkpoint; 13 recoverable input copies are retained in `agent-policy-host-before/manifest.json` under the task evidence directory.

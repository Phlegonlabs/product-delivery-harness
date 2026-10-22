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

## AWP-2 Host Helpers

Removed the fixed role set and frontend special case from Dynamic Workflow's catalog.
Every valid installed agent TOML supplies its own model, effort and sandbox metadata.
New assignment inputs may carry explicit `preferred_route`, `requested_model` and `requested_effort` from agent policy.
Omitted settings inherit profile metadata; explicit null remains runtime inheritance. Route labels do not prove transport capability.
Binding checks the chosen route and preserves native actor identity. External actor reuse remains unsupported by the tool.
Legacy native-to-native-fallback receipt behavior remains readable; the ledger neither chooses nor invokes a fallback.

Claude, Dynamic Workflow and GLM wrapper instructions now defer worker policy to agent configuration.
Their instructions retain complete visual inputs, permissions, process deadlines, partial-work reconciliation and execution evidence.
The command reference no longer repeats the stale frontend Opus/high default.
Claude request examples omit optional model/effort keys; actual launcher preparation rejects explicit null values.
GLM launcher parameter support is a transport capability, not an agent selection policy; callers pass resolved choices explicitly.
Actual host AGENTS, native agent definitions and both launcher implementations remain unchanged.

Six host files changed. All 13 before/after inputs have separately hash-bound snapshots outside Git.
Before: `agent-policy-host-before/manifest.json`; after: `agent-policy-host-final/manifest.json` in the task evidence directory.
Final host manifest SHA-256: `948bc2b60e8a0aa28f8270e7ed6fcb9bd91ab3e47792a553bdcf2b7454d350fe`.

All 29 host workflow tests passed, including profile inheritance, new installed roles, explicit design/implementation choices, route mismatch and actual-model evidence.
The new tests failed against the old overrides, then passed after the implementation change.
Three host skills passed quick validation. No-launch preparation passed for omitted settings and explicit Opus/xhigh and Sonnet/xhigh requests.
Optional host Pyflakes reports two pre-existing unused imports; the retained baseline produces the same diagnostics. No unrelated import cleanup was made.
The existing workflow module remains one ledger/controller responsibility; this task does not split its established module.
Fresh unified candidate checks, independent review and final handoff remain pending.

## Bounded Review Repair

Independent review of `6b26864e2bafb329486804596975b29352ead4a7` returned three medium findings requiring repair.
The immutable result is retained at `agent-policy-security-result.json` in the task evidence directory.
Result SHA-256: `fc1a1e52f547013a672f30ed1cb45da722372c22867edda044d4849725c4f7ee`.
The structured result passed validation unchanged against its exact 35-path scope.

One bounded batch fixes all three configuration-retention defects:

- Revalidation preserves selected route, model and effort on a fresh node.
- New explicit actor settings are checked before dispatch and cannot be overwritten at bind.
- Explicit actor replacement may choose new settings while retaining the predecessor's binding and snapshot history.
- Agent-selected research staffing may reuse a stable worker/session pair with separate assignment, attempt, input and reservation identities.
- Required independent corroboration still requires distinct identities; research reuse cannot cross into analysis, synthesis or verifier assignments.

Research packets add optional frozen `distinct_workers`; current guides require an explicit agent choice.
False permits sequential reuse, true preserves independent corroboration, and omission retains historical distinct-worker semantics and input hashes.
Product graphs forward `research_distinct_workers` and actual configured research executor identity.
No fixed native research-role list remains in the standalone packet helper.
Shared identity validation retains authority, role/model/effort, reservation, result, source and phase checks.
The full Product suite caught one additional old grading-staffing wording assertion; it now matches the accepted agent-owned staffing policy.

Regression evidence: new host and research cases failed on the reviewed candidate, then passed after repair.
All 34 host workflow cases and all 306 Product Definition cases pass. Harness65, cross18, source static and document weight also pass.
The pre-existing large packet-test and contract-test modules retain their single regression responsibility; this scoped repair does not split them.
No model, service, product UI, publication, installation or agent-definition change occurred.
The three changed host repair inputs have a new 13-file snapshot at `agent-policy-host-repaired/manifest.json`.
Manifest SHA-256: `7c684f2834e81da9907f697f12e153ce8b1c0f282cf139157caa279780624927`.

Prior snapshots and the failed review remain immutable. Fresh fixed-candidate re-review remains pending.

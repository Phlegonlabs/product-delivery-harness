# Worker Goal: <mission ID> — <objective>

Use only after routing, validation, exact authorization, lease and worktree verification. A `sequential_parent` route does not render this packet.

```text
Complete <mission ID> (<objective>) only.

Identity:
- PLAN: <path>; ID <id>; revision <revision>; digest <sha256>
- RUN snapshot: <path or payload>
- Mission/tasks: <IDs>
- Runtime slice: one bounded mission slice; target 10-20 minutes including focused verification
- Lease: <lease-id>
- Batch base: <full SHA>

Runtime:
- required_skills: <mission skill list verbatim or none>
- Provider/driver: <provider> / <driver>
- Logical/resolved role: <worker_role> / <resolved_role>
- Worker/workspace/completion: <worker_runtime> / <workspace_mode> / <completion_channel>
- Worktree and branch/ref: <exact values>
- Host-specific context: <ordered paths>
- Worker contract: <matching adapter contract>
- Launch record: <assignment/attempt/worker/session receipt or none>
- Runtime-contract adoption: <contract_adoption receipt or none>
- Handoff: <fresh bounded packet or host-native task context; max_message_bytes <positive integer>>
- Context source hashes: <ordered paths with matching hashes>
- Visual inputs: <frontend-visual-inputs.md block; omit for non-UI>
- Result contract: <absolute or readable path to references/worker-result-contract.md>
- Permissions: <mode/profile, filesystem/network/bindings, approval policy>
- Resource claims: <typed keys and access>
- Nested delegation: disabled

Scope:
- Write: <mission write_scope>
- Deny: <mission deny_scope>, PLAN.md, RUN.md, frozen contracts, and unrelated files

Acceptance:
- Objective and stop conditions: <exact values>
- Verifiers: <selected task/worker verifiers>; platform <stage/completion/TESTs or none>
- Security requirements: <in-scope PRD-*/TEST-* pairs or none>
- Commit authorization: <true/false and source>

Repair context (omit for an initial implementation):
- Root-cause families: <stable labels, affected primitives, and consolidated findings>
- Known variants and acceptance matrix: <all cases the repair must close>
- Rejected narrow approach: <case-specific strategy that must not be repeated>
- Review lineage: <mission, surface, used attempts across PLAN revisions, remaining authorized allowance>
```

## Launch

1. Enter the assigned worktree. Read the ordered repository context and only the named skills. Keep automatic context discovery enabled.
2. With a contract-adoption receipt, independently recompute the seven-skill contract digest and stop on a mismatch. Read the fixed contract and report it as `contract_adoption_check`.
3. Use this complete handoff. Do not reconstruct parent context. Open PLAN/RUN only for named missing fields.
4. The parent ran `scripts/check_launch_packet.py` before dispatch. Verify source hashes, repository, branch/ref, base SHA, clean state, digest, lease, scope, resources, permissions, authorizations. Stop on invalid, stale, or drift.
5. Apply only the matching host contract; never borrow another host's model, role, context, or launch mechanics. Confirm temp/cache paths, network, local bindings, and sockets fit its boundary.

## Work

- Make the smallest coherent change inside the write scope.
- For architecture-bearing work, apply `references/delegation-contract.md#architecture-method`; start with a caller example before deriving interfaces and types.
- Never edit PLAN/RUN, create another worker/task/branch/worktree/lease, or delegate.
- Do not pull, rebase, merge, integrate, push, archive, remove a worktree, or delete a branch.
- With `create_local_commits` authorized, run the focused verifier and create the atomic task commit. Confirm its checkpoint; only then begin the next task. Each commit names one task; commit repairs separately for that task. Report each SHA once in Git order; the last commit equals the reported head.
- Before a task commit or `worker_passed`, implement each touched boundary's control and negative test proving denial and no unauthorized side effects. Keep a scaffolded protected route fail-closed until this is true.
- For a repair handoff, fix the named root-cause family rather than applying the findings as independent patches. If another adjacent variant shows that the proposed mechanism is not closed, stop before adding another special case and return `REFINEMENT_REQUEST` or `contract_gap` with the structural strategy and missing acceptance classes.
- If the remaining work no longer fits this bounded slice, stop before the next independent mutation and return `REFINEMENT_REQUEST`.
- Stop on a requirement conflict, scope escape, destructive action, unexpected parent-head movement, unavailable verifier, or three consecutive no-progress iterations. Do not retry one failed approach more than twice.

For direction/HiFi authoring/repair or explicitly pinned legacy Wireframe work, `required_skills` must name both `ui-design-builder` and the exact owner-bound `frontend-design`. Before authoring, run `python "<delivery-harness-skill-root>/scripts/check_skill_bindings.py" --agents-md <target-AGENTS.md> --stage ui-design` through installed-command resolution. The actual writer loads full pinned skills there; a parent read, snapshot or role title is no substitute. Do not backfill evidence or replace a binding. Missing/conflicting dependencies block only authoring; preserve prior approvals and closed history. This grants no delegation; agent policy selects the UI author. Assemblers/reviewers provide shell construction and validation, not product-design decisions. Carry the delegation contract's maximum-creativity brief.

For design-system compilation, load `design-system-compiler`. Read approved `PRD.md`, `ui-design.md`, and the HiFi target; for `ui-design/3`, read the complete `design-system/4` package and frozen derived HTML on update/reuse. Read `wireframes.html` only for a legacy bound pair. Proceed only when the applicable gate requires compilation; do not reopen direction or claim another skill defines a mode.

For frontend implementation, load the owner-bound frontend-authoring skill and read the named PRD UI surface, approved `ui-design.md`, active visual source, and any wireframe required by a legacy frozen contract. The Harness—not the external skill—owns system/target conformance. In system-conformance mode, read `design-system.md`, `design-system.json`, and `design-system/4` derived HTML; invent no token, primitive, variant, component, or motion rule. In target-conformance mode, read the approved immutable UI target and stay within its scope/tolerance. Return a design-input delta and stop when the active source is incomplete.

For any UI-touching mission, classify the completed change against frozen product and UI-design sources as `none`, `style`, `structure`, or `both`, and state it in the terminal payload's `integration_notes`. A `structure` or `both` change absent from the approved PRD and UI-design contracts returns upstream and stops; it is never reported as `worker_passed`.

## Verify

Select focused checks from parent-observed changed files using `selection.mode: "changed_files"`. Run each declared verifier through `scripts/verifier_runtime.py` so the result includes an `execution_key`; a free-form shell transcript is not verifier evidence. A required security check without its tool or retained evidence is blocked, not skipped.

There is no disk verifier cache; do not pass `cache_root`.

## Return

Read the supplied `references/worker-result-contract.md` only when preparing the terminal payload. Emit:

- `WORKER_RESULT` when the assigned mission reaches `worker_passed`, `blocked`, or `worker_failed`;
- `REFINEMENT_REQUEST` when the current task cannot remain one independently verifiable unit; or
- the graph node wrapper when the parent requests it.

Report `worker_passed`, never integrated. The parent validates live Git, runs exact-head review, integrates, and updates RUN.

## No Nested Delegation

Do not spawn, create, or delegate to another agent. All explorers, writers, and reviewers are parent-dispatched siblings. Report `subagent_activity.status: "not_applicable"`, a concrete flat-topology reason, and an empty `children` list.

## Workspace Notes

- `shared_checkout`: only the parent may be the sole writer.
- `parent_managed_worktree`: use the exact parent-created worktree and base.
- `app_managed_worktree`: remain on the assigned ref; create or attach a durable branch only when explicitly authorized.

## Launch Checklist

- [ ] System Review And Route completed before this delegated handoff exists.
- [ ] PLAN schema v6 and RUN schema v11 validate and match the supplied digest.
- [ ] Lease, base, worktree, branch/ref, permission boundary, and required actions are current.
- [ ] Host-specific repository context and matching adapter contract were read.
- [ ] Any adoption digest was recomputed, matched, read, and reported.
- [ ] Exact skills, write/deny scope, resources, stop conditions, and verifiers are known.
- [ ] The result-contract path is readable.

# Worker Goal: <mission ID> — <objective>

Use this template only after System Review And Route, PLAN/RUN validation, exact authorization, lease allocation, and worktree verification. A `sequential_parent` route does not render it.

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
- Skills to load: <exact list or none>
- Provider/driver: <provider> / <driver>
- Worker/workspace/completion: <worker_runtime> / <workspace_mode> / <completion_channel>
- Worktree and branch/ref: <exact values>
- Host-specific repository context: <ordered paths>
- Runtime-specific worker contract: <matching adapter contract>
- Context handoff: <fresh bounded packet or host-native task context>
- Context sources: <ordered paths>
- Result contract: <absolute or readable path to references/worker-result-contract.md>
- Permission boundary: <mode/profile, filesystem/network/bindings, approval policy>
- Resource claims: <typed keys and access>
- Nested delegation: disabled

Scope:
- Write: <mission write_scope>
- Deny: <mission deny_scope>, PLAN.md, RUN.md, frozen contracts, and unrelated files

Acceptance:
- Objective and stop conditions: <exact values>
- Verifiers: <selected task and worker verifiers>
- Commit authorization: <true/false and source>

Repair context (omit for an initial implementation):
- Root-cause families: <stable labels, affected primitives, and consolidated findings>
- Known variants and acceptance matrix: <all cases the repair must close>
- Rejected narrow approach: <case-specific strategy that must not be repeated>
- Review lineage: <mission, surface, used attempts across PLAN revisions, remaining authorized allowance>
```

## Launch

1. Enter the assigned worktree. Read the ordered repository context and only the named skills. Keep automatic context discovery enabled.
2. Treat this handoff as the complete live task. Do not reconstruct or continue the parent conversation; open PLAN/RUN only when the packet names a specific field that cannot be supplied directly.
3. Verify repository, branch/ref, base SHA, clean starting state, plan digest, lease, scope, resources, permission boundary, and authorizations. Stop on a missing, stale, or contradictory value.
4. Apply only the matching host contract. Do not borrow another host's model, role, context, or launch mechanics.
5. Confirm required temp/cache paths, network, local bindings, and sockets fit the inherited boundary.

## Work

- Make the smallest coherent change inside the write scope.
- Never edit PLAN/RUN, create another worker/task/branch/worktree/lease, or delegate.
- Do not pull, rebase, merge, integrate, push, archive, remove a worktree, or delete a branch.
- Create commits only when `create_local_commits` is authorized. Each task commit names one task; the last commit equals the reported head.
- For a repair handoff, fix the named root-cause family rather than applying the findings as independent patches. If another adjacent variant shows that the proposed mechanism is not closed, stop before adding another special case and return `REFINEMENT_REQUEST` or `contract_gap` with the structural strategy and missing acceptance classes.
- If the remaining work no longer fits this bounded slice, stop before the next independent mutation and return `REFINEMENT_REQUEST`; do not wait for a host timeout to create the checkpoint.
- Stop on a requirement conflict, scope escape, destructive action, unexpected parent-head movement, unavailable verifier, or three consecutive no-progress iterations. Do not retry one failed approach more than twice.

For design creation mode, load `product-design-builder`, `impeccable`, and `frontend-design` together and stop at required human gates.

For frontend-design conformance mode, read the named wireframe, `design-system.md`, and `design-system.json`. Do not invent a token, primitive, variant, component, motion rule, state, or structure. Return a design-input delta and stop.

## Verify

Select focused checks from parent-observed changed files using `selection.mode: "changed_files"`. Run each declared verifier through `scripts/verifier_runtime.py` so the result includes an `execution_key`; a free-form shell transcript is not verifier evidence.

Use a repository-external cache only when the parent supplies it and the command is an opted-in deterministic `exit 0` check with exact immutable inputs. Otherwise use `cache_root=None`.

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
- `app_managed_worktree`: remain on the assigned ref; create or attach a durable branch only when explicitly authorized. Platform retention is independent from Harness cleanup authorization.

## Launch Checklist

- [ ] System Review And Route completed before this delegated handoff exists.
- [ ] PLAN schema v5 and RUN schema v10 validate and match the supplied digest.
- [ ] Lease, base, worktree, branch/ref, permission boundary, and required actions are current.
- [ ] Host-specific repository context and matching adapter contract were read.
- [ ] Exact skills, write/deny scope, resources, stop conditions, and verifiers are known.
- [ ] No nested delegation is permitted.
- [ ] The result-contract path is readable.

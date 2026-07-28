---
name: fullstack-harness-github-landing
description: "GitHub landing adapter for Full Stack Harness engineering. Use only when the requested and authorized outcome includes push, pull-request creation, GitHub Actions checks, Codex review, merge, or repository configuration. Runs local verification first, then evaluates CI and review concurrently on the final PR head. Do not load for local-only branch or commit work."
---

# Full-Stack Harness: GitHub Landing Adapter

## Load Boundary

Read `../fullstack-harness-engineering/SKILL.md` first. This adapter owns only remote landing. It does not choose Codex or Claude worker mechanics and does not replace shared PLAN/RUN, verification, integration, deployment, or cleanup rules.

Load it only when the user explicitly requests a remote outcome such as push, PR, CI, review, merge, or repository configuration. A shared repository alone is not enough. Local branch, commit, or integration work stays `local_only` and never waits for GitHub.

## Tooling

Use the `gh` CLI as the default concrete tool for every GitHub action in this adapter, falling back to plain `git` for local push mechanics: `git push`; `gh pr create --body-file <rendered PULL_REQUEST.template.md>` (or `gh pr edit` to update one already open); `gh pr view --json` / `gh api` to inspect branch protection, required status checks, PR template, and repository auto-merge configuration; `gh pr checks` to observe CI; `gh pr merge --match-head-commit <SHA>` for the exact-head merge guard, combined with `--squash`, and `--auto` only for the non-protected integration base described in the Pull-Request Handover section. Read `../fullstack-harness-engineering/references/orchestration-research-notes.md`'s "Local And GitHub Code Review" section for the exact Codex Cloud connection requirement and the `@codex review` manual trigger this adapter's review gate depends on.

## Authorization And Readiness

Inspect the exact remote, base branch, head branch, branch rules, required checks, review availability, PR template, and repository auto-merge setting. Observation does not authorize mutation.

Record every required action separately:

```text
configure_repository
push
create_pr
trigger_remote_ci
manage_pr_review
merge_pr
```

Local branch, commit, review, and integration authorization remains in the core ledger. At Plan Readiness, request every missing action for the outcome that is currently in scope. Ordinary mission work ends when the verified integration head is pushed to the integration branch resolved from target-repository instructions; do not include a future protected-branch promotion merely because implementation is authorized. After the user asks to land that pushed branch, bind `create_pr` and `manage_pr_review` to `future-pr:<owner>/<repo>:base=<resolved-base>:head=<resolved-head>`. After PR creation, verify repository/base/head and append the exact `pr:<full-PR-URL>` target without discarding the future binding or user source. Do not bind `merge_pr` here: asking for the PR is not asking for the merge.

`create_pr` does not authorize marking ready, requesting or resolving review, changing repository settings, or merging. `manage_pr_review`, `configure_repository`, and `merge_pr` remain independent.

## Resolved Integration To Landing Promotion

Read the target repository's instructions and existing branch/PR topology before filling any branch-bound authorization. Preserve its implementation, integration, head, and protected base branches. Only when it defines no other model, `main` is the protected landing branch and the only persistent one, and the run's own `codex/<short-name>` branch — cut from the current `main` and disposable — is the integration branch. Mission worktrees are reviewed before they merge into the resolved integration branch; this adapter does not open one PR per worktree.

An ordinary run ends at the push to that integration branch. Nothing has reached the protected base and no PR exists yet. Do not create the landing PR, request remote review, or merge toward the resolved protected base until the user reads the pushed branch and asks to land it. That instruction is not inferred from earlier implementation, local integration, deployment, or generic landing authorization. After it is recorded, require the exact resolved head and base for every branch-bound action and run the normal current-head convergence loop. Later PRD, UI, and feature changes cut a new run branch from the then-current protected base rather than continuing on a branch that already landed.

## Local-First, Remote-Final Policy

Remote CI is a final-head release gate, not a per-mission development loop:

1. Complete selected task checks, per-worktree exact-head review before integration, real resolved-branch integration checks, exact-SHA runtime review/repair, broad regression, E2E/UI evidence, `git diff --check`, and final diff review locally.
2. Commit the verified integration head under exact local authorization.
3. Push only that final candidate head, and only to the resolved integration branch. Do not push intermediate worker heads merely to obtain CI. An ordinary run is complete at that push.
4. Create the PR only when the user asks to land the pushed branch and `create_pr` is authorized, using `gh pr create --body-file` rendered from `../fullstack-harness-engineering/assets/templates/PULL_REQUEST.template.md` (fill in the verification command and landing checklist) as the body base. If review management is authorized and the repository requires a ready PR for review, mark it ready and request Codex review immediately after creation — when the repository does not have Automatic reviews enabled, this means commenting `@codex review` on the PR (`gh pr comment --body "@codex review"`); do not wait for CI first.
5. Observe automatically started GitHub Actions and Codex review for the same PR head, then poll both concurrently. Observation is read-only. Dispatching, rerunning, or otherwise causing a remote workflow execution requires separate `trigger_remote_ci` authorization with an exact `workflow:<identity>` target. CI and review are sibling remote gates, not a serial `CI -> review` chain.

The normal remote critical path is:

```text
final local PASS -> push final head to the run's own branch -> the run is complete

the user asks to land that branch
-> create/ready the run branch -> protected base PR
   |-> current-head CI
   `-> current-head Codex review
both PASS on the same SHA -> hand the verified PR to the human
```

This reduces waiting without weakening the gate: the handover still requires both results. Repository-required checks may run automatically after push; the parent should begin the review lane as soon as its independent authorization and PR state allow.

## Current-Head Convergence Loop

Bind every remote result to the exact current head:

- checks PASS only when `checks_head_sha == pr_head_sha == integration.integration_head_sha`;
- review PASS only when `review_head_sha` matches the same SHA, blocking findings are zero, and unresolved threads are zero;
- any local integration or new push invalidates prior current-head CI, review, E2E, deployment, and auto-merge evidence tied to an older SHA.

When CI or review finds an authorized in-scope defect, repair it locally, rerun invalidated local gates, commit and push the new final candidate, then restart CI and review concurrently for the new head. Stop for missing authorization, a scope/contract decision, or the worker/run-level guardrail of three consecutive no-progress iterations (see `../fullstack-harness-engineering/assets/templates/GOAL.template.md` and `../fullstack-harness-engineering/assets/templates/WORKER_GOAL.template.md`).

Do not repeatedly run the complete GitHub pipeline for unchanged local work. Do not create empty commits to retrigger it. Use GitHub-native rerun only when a current-head job is transient and rerun is permitted by the repository.

## Pull-Request Handover

Which side of this section applies is decided by the PR's base branch, not by how the run was approved.

A PR whose base is the protected landing branch is the human's. Under the default branch model every PR this adapter opens is one of these: head is the run's own branch, base is `main`. After the user asks to land that branch, the parent runs one continuous loop up to — and stopping at — a merge-ready PR: push the final candidate, create the PR, mark it ready, request review, and converge CI and review on the current head. It does not merge and does not enable auto-merge there.

A PR whose base is a resolved non-protected integration branch is ordinary development work, and only a target repository that defines such a branch ever produces one. Once current-head CI and review pass and unresolved threads reach zero, the parent may merge it or enable repository auto-merge on it. This is the single case where the core's Execution Authorization Gate lets `merge_pr` ride the execution-intent instruction, and only for a PR based on that exact branch. Use `gh pr merge --match-head-commit <SHA>` so the merge stays bound to the exact reviewed head. Never enable auto-merge before those gates pass.

Report the PR as ready to merge only when:

- the PR head still equals the verified integration head;
- the PR head and base branches exactly match the resolved, authorized target-repository branches;
- required current-head CI, including required E2E, is PASS;
- current-head Codex review is PASS;
- blocking findings and unresolved threads are zero.

Then stop and hand it over, naming the exact head SHA that is merge-ready. A new push resets both remote gates and the handover has to be re-established on the new head.

Merge toward the protected base yourself only when the user separately and explicitly asks for it on a named PR — approval to open the landing PR never carries it, and neither does the execution-intent grant in the integration-branch case above. In that case `merge_pr` must cover every required mission and the exact PR target, use `gh pr merge --match-head-commit <SHA>` as an exact-head guard, wait until GitHub reports the PR merged, and record the resulting merged source SHA separately; a squash merge normally makes it differ from the authorized candidate head.

If repository auto-merge, required checks, or review configuration needs a change, do not mutate settings without exact `configure_repository` authorization. Direct push or merge to the base branch is never a substitute for the PR flow.

## Deployment And Cleanup Boundaries

Deployment is not part of GitHub landing authorization. Release target IDs are provider-neutral and exact-SHA-bound; read the core provider lifecycle only when deployment is requested. Cleanup, task archival, worktree removal, and branch deletion remain separate post-merge actions and are never inferred from a successful merge.

A native merge-triggered Cloudflare release crosses two independent boundaries at the same operation. It requires exact merge/landing authorization bound to the current PLAN revision/digest, exact PR/head, and every `release:<target-id>` consequence. It also requires exact deployment authorization bound to the same PLAN revision/digest, head, missions, and `release:<target-id>` target. Never infer deployment authorization from merge authorization, and never infer merge authorization from deployment authorization. If either grant is absent, stale, or targets a different head, do not merge. Run the core Pre-Deploy Confirmation Checkpoint immediately before the merge because that merge is the provider's publication trigger.

## Completion

An `integration_push` run is complete when the verified integration head reaches the resolved integration branch and RUN records that branch, the pushed head SHA, and the local evidence behind it. It does not wait for a PR, for CI, or for a deploy.

A pull-request run remains non-complete when the exact current-head CI and review gates pass and the verified PR is handed to the human. At that merge-ready handoff, RUN records the PR URL, PR head, check head, review head, findings/threads, and evidence, but keeps the run non-complete while the PR is open. After the human merges, observe that GitHub reports the PR merged and inspect the current merged base state; record `pr_state: "merged"`, `merge_status: "merged"`, the resulting `merged_sha`, and the required merged-base evidence, then and only then set the RUN to `complete`. The same observation requirement applies when the harness performed a separately authorized exact-PR merge. Report any unexecuted deployment or cleanup action separately.

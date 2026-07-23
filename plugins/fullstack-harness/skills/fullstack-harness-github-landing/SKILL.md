---
name: fullstack-harness-github-landing
description: "GitHub landing adapter for Full Stack Harness engineering. Use only when the requested and authorized outcome includes push, pull-request creation, GitHub Actions checks, Codex review, merge, or repository configuration. Runs local verification first, then evaluates CI and review concurrently on the final PR head. Do not load for local-only branch or commit work."
---

# Full-Stack Harness: GitHub Landing Adapter

## Load Boundary

Read `../fullstack-harness-engineering/SKILL.md` first. This adapter owns only remote landing. It does not choose Codex or Claude worker mechanics and does not replace shared PLAN/RUN, verification, integration, deployment, or cleanup rules.

Load it only when the user explicitly requests a remote outcome such as push, PR, CI, review, merge, or repository configuration. A shared repository alone is not enough. Local branch, commit, or integration work stays `local_only` and never waits for GitHub.

## Tooling

Use the `gh` CLI as the default concrete tool for every GitHub action in this adapter, falling back to plain `git` for local push mechanics: `git push`; `gh pr create --body-file <rendered PULL_REQUEST.template.md>` (or `gh pr edit` to update one already open); `gh pr view --json` / `gh api` to inspect branch protection, required status checks, PR template, and repository auto-merge configuration; `gh pr checks` to observe CI; `gh pr merge --match-head-commit <SHA>` for the exact-head merge guard, combined with `--squash` and `--auto` per the Authorized Automatic Pull-Request Landing section. Read `../fullstack-harness-engineering/references/orchestration-research-notes.md`'s "Local And GitHub Code Review" section for the exact Codex Cloud connection requirement and the `@codex review` manual trigger this adapter's review gate depends on.

## Authorization And Readiness

Inspect the exact remote, base branch, head branch, branch rules, required checks, review availability, PR template, and repository auto-merge setting. Observation does not authorize mutation.

Record every required action separately:

```text
configure_repository
push
create_pr
manage_pr_review
merge_pr
```

Local branch, commit, and integration authorization remains in the core ledger. At Plan Readiness, request every missing launch and landing action once. Before a PR exists, bind `manage_pr_review` and `merge_pr` to `future-pr:<owner>/<repo>:base=<base-branch>:head=<head-branch>`. After PR creation, verify repository/base/head and append the exact `pr:<full-PR-URL>` target without discarding the future binding or user source.

`create_pr` does not authorize marking ready, requesting or resolving review, changing repository settings, or merging. `manage_pr_review`, `configure_repository`, and `merge_pr` remain independent.

## Local-First, Remote-Final Policy

Remote CI is a final-head release gate, not a per-mission development loop:

1. Complete selected task checks, real integration checks, exact-SHA runtime review/repair, broad regression, E2E/UI evidence, `git diff --check`, and final diff review locally.
2. Commit the verified integration head under exact local authorization.
3. Push only that final candidate head. Do not push intermediate worker heads merely to obtain CI.
4. Create the PR only when authorized, using `gh pr create --body-file` rendered from `../fullstack-harness-engineering/assets/templates/PULL_REQUEST.template.md` (fill in the verification command and landing checklist) as the body base. If review management is authorized and the repository requires a ready PR for review, mark it ready and request Codex review immediately after creation — when the repository does not have Automatic reviews enabled, this means commenting `@codex review` on the PR (`gh pr comment --body "@codex review"`); do not wait for CI first.
5. Start or observe GitHub Actions and Codex review for the same PR head, then poll both concurrently. They are sibling remote gates, not a serial `CI -> review` chain.

The normal remote critical path is:

```text
final local PASS -> push final head -> create/ready PR
                                      |-> current-head CI
                                      `-> current-head Codex review
both PASS on the same SHA -> exact-head merge
```

This reduces waiting without weakening the gate: merge still requires both results. Repository-required checks may run automatically after push; the parent should begin the review lane as soon as its independent authorization and PR state allow.

## Current-Head Convergence Loop

Bind every remote result to the exact current head:

- checks PASS only when `checks_head_sha == pr_head_sha == integration.integration_head_sha`;
- review PASS only when `review_head_sha` matches the same SHA, blocking findings are zero, and unresolved threads are zero;
- any local integration or new push invalidates prior current-head CI, review, E2E, deployment, and auto-merge evidence tied to an older SHA.

When CI or review finds an authorized in-scope defect, repair it locally, rerun invalidated local gates, commit and push the new final candidate, then restart CI and review concurrently for the new head. Stop for missing authorization, a scope/contract decision, or the worker/run-level guardrail of three consecutive no-progress iterations (see `../fullstack-harness-engineering/assets/templates/GOAL.template.md` and `WORKER_GOAL.template.md`).

Do not repeatedly run the complete GitHub pipeline for unchanged local work. Do not create empty commits to retrigger it. Use GitHub-native rerun only when a current-head job is transient and rerun is permitted by the repository.

## Authorized Automatic Pull-Request Landing

When every remaining action is authorized, do not stop after local verification, push, PR creation, CI start, or review request. The parent owns one continuous landing loop through current-head convergence.

Enable squash auto-merge only after:

- the PR head still equals the verified integration head;
- required current-head CI, including required E2E, is PASS;
- current-head Codex review is PASS;
- blocking findings and unresolved threads are zero;
- `merge_pr` covers every required mission and the exact PR target.

Use an exact-head guard. A new push resets the merge request and both remote gates. Wait until GitHub reports the PR merged before declaring landing complete, and record the merged SHA separately from a squash-merged PR head.

If repository auto-merge, required checks, or review configuration needs a change, do not mutate settings without exact `configure_repository` authorization. Direct push or merge to the base branch is never a substitute for the PR flow.

## Deployment And Cleanup Boundaries

Deployment is not part of GitHub landing authorization. For Cloudflare, development and production are separate exact-SHA targets with separate `deploy` authorization; read the core lifecycle reference only when deployment is requested. Cleanup, task archival, worktree removal, and branch deletion remain separate post-merge actions and are never inferred from a successful merge. When the target release uses the Cloudflare Auto-Deploy Release Model (`run.integration.retention: "persistent"`, development `source: "integration_head"` — see the core lifecycle reference), merging the integration branch into `main` through this adapter's landing loop is the de facto production-deploy trigger, since Cloudflare's own Git integration auto-deploys on that push; run the core's Pre-Deploy Confirmation Checkpoint (SHA-drift and migration-destructiveness checks) immediately before that merge in this case, not as a separate later step.

## Completion

A pull-request run is complete only when the exact current-head CI and review gates pass, the authorized merge finishes, GitHub reports the PR merged, and RUN records PR URL, PR head, check head, review head, merged SHA, findings/threads, and evidence. Report any unexecuted deployment or cleanup action separately.

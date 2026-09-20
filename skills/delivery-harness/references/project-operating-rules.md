# Conditional Project Operating Rules

Read only the section triggered by project AGENTS.md. These shared rules retain their authorization and evidence boundaries. Local project facts stay in the project, not this installed reference.

## Monetization And Partner Channels

- When a product has pricing, paid access, purchase-gated features, or outside sellers, keep explicit Monetization Infrastructure and Partner Channel gates in `docs/product/PRD.md`; record `not_required` with a reason when either does not apply.
- Resolve the commercial model and purchase surfaces before selecting technology. RevenueCat is one candidate, never the default: compare current official evidence for native store billing, RevenueCat, Qonversion, Adapty, Superwall, Stripe Billing, Paddle, Lemon Squeezy, or another product-fit option.
- Treat affiliate, referral, and reseller as different motions. A reseller decision must cover deal registration, price authority or wholesale terms, customer ownership, provisioning, delegated administration, support, renewals, termination, and channel conflict; an affiliate link alone does not satisfy it.
- Keep billing/store, entitlement, paywall/checkout, merchant-of-record/tax, attribution, commission/payout, and reseller-operation responsibilities separate in PRD, architecture, stack decisions, implementation, and tests. Update affected UI Surface Contract entries through `product-definition-builder`, then update `ui-design.md` and `wireframes.html` through `ui-design-builder` before implementing customer, partner, pricing, purchase, or administration surfaces.

## Post-Delivery Activation

- Use `product-activation` only after implementation has a fixed release SHA or exact artifact identity. It owns `docs/ACTIVATION.md` and never edits or extends a delivery PLAN/RUN.
- Product Definition may create the first Activation seed when the path is absent. Preserve an existing record; only `product-activation` reconciles its live action, source, evidence, and readiness state.
- Probe purpose-built connector/API/CLI first, then Browser, Computer Use, and manual handoff. Capability never grants permission.
- Bind every external write to the exact account or organization, project or property, environment, action, and current action digest. DNS, permissions, credentials, billing, production traffic, public submission, data sharing, and destructive changes require action-time confirmation.
- Never record secret values. Password, MFA, OTP, CAPTCHA, banking, tax, legal attestation, and secret-value entry remain user handoffs.
- Refresh and read back every change. A success toast, mutation response, upload, submission, or owner statement does not prove behavior.
- Route a missing product hook to a new `delivery-harness` change and a missing requirement, metric, TEST ID, or release target to `product-definition-builder`. Activation never patches product code in place.
- Activation readiness is per release target and does not keep the delivery RUN open or replace the later outcome-review measurement window.

## Managed Product Delivery Harness Runs

The rules below apply only to a PLAN-v6/RUN-v11 managed route. They do not convert small direct work into a managed run.

- Map one independently testable goal to one mission. Tasks inside that mission stay sequential under one writer.
- Give every writer an explicit file-ownership scope and a separate worktree. Workers and reviewers never delegate; the Harness parent dispatches every explorer, writer, and reviewer as a sibling.
- Freeze and integrate shared APIs, schemas, and types before starting dependent write missions in parallel.
- Cut every initial-delivery or enhancement run branch from current observed remote `main`, then create every implementation worktree from the resolved integration-branch SHA.
- Before dispatch, verify each worktree has the expected repository, branch/ref, exact base HEAD, and a clean status.
- Run focused checks and at least one exact-head read-only review in or against each completed worktree. A repair requires a fresh review.
- With matching `integrate_locally` authorization, merge only reviewed worktree heads into the resolved integration branch.
- After serial integration, use fresh read-only reviewers on the exact unified integration SHA, then run one broad final validation on the fixed candidate SHA.
- The RUN closes at local candidate C. Archive-only child A is verified and may reach the run branch only through a new action-time authorization and immutable external request/attempt/receipt. `main` promotion is another action.
- After a completed plan and before its archival, record every owner or agent update not already reflected in `docs/product/PRD.md` as one dated row in the `docs/tasks.md` Update Log — the fenced section the renderer preserves verbatim; product-affecting updates also follow Keep Product Contracts Current into the PRD in the same change.
- After the Closeout Bar, run `archive_run.py` on the same branch with the approved dry-run list, `--expected-main`, `--main-ref`, and an absolute checkout-external `--anchor-out`. It moves the full coordination set, updates `docs/DOCUMENTS.md`, writes closed `ARCHIVE_RECEIPT.json` plus the external anchor, never moves anything under `docs/product/`, and rolls back failures. Commit only repository bookkeeping as A. `push_archived_candidate.py --archive-anchor <same path>` may prepare publication only after another exact instruction; it rejects caller prose/ref as authority, binds the exact canonical URL plus observed trust-policy/verifier hashes, never invokes `git push`, and keeps request/attempt/receipt/evidence outside the checkout. A trusted host independently reloads and revalidates the request with sanitized config, performs the exact URL no-force push, signs execution evidence, and recovery verifies it before reading back A and closing the receipt; agents and the local executor must not run the emitted argv without that trusted boundary. Candidate gates and later lifecycle steps follow in order. If candidate or preview evidence fails after A, create a fresh PLAN/RUN on the same non-default branch from exact A, import prior verified scope plus repair and bind A's receipt/anchor and immutable prior publication state as historical inputs, require new grants, close C2, archive a new-anchor A2, and never rewrite A or reuse its records. If A was published, A2's remote pre-state must be exactly A; if not, it must remain absent.
- Later enhancement work cuts a fresh run branch from the current observed remote `main` head after the prior promotion state is resolved.

### Action Authorization

- Before any action represented in the RUN authorization ledger, verify its exact authorization. Preserve all 12 keys: `invoke_external_runtime`, `spawn_subagents`, `create_user_owned_tasks`, `create_local_worktrees`, `create_app_managed_worktrees`, `create_local_branches`, `create_local_commits`, `integrate_locally`, `push`, `archive_worker_tasks`, `remove_worktrees`, and `delete_branches`.
- Harness 0.38 plan-backed work closes `local_only` at C. `integration_push` remains pre-0.38 recovery state only; A is post-RUN and cannot be written into the archived RUN without changing itself.
- With matching `create_local_branches` authorization, work on the exact resolved non-default run branch.
- With matching `create_local_commits` authorization, commit only the verified task scope.
- Worker branches stay local. With matching `integrate_locally` authorization, integrate exact-head review-passing work into the resolved integration branch.
- Run the exact repository-defined focused verification and applicable E2E commands, then review the complete diff before push. If commands are undocumented, inspect the repository's package scripts and CI configuration and state the commands selected.
- Treat a PASS from the required automated E2E on the current head as the proof for its covered primary journeys. Record duplicate manual smoke as `not required - covered by current-head E2E`; require manual smoke only for a materially different environment or an uncovered visual/external-integration risk.
- After RUN completion, prepare verified A only through the separately authorized archive-candidate protocol. It derives the run branch and C from the archive, verifies clean exact A, and checks remote pre-state. The immutable request binds the canonical URL, observed trust policy, and absolute verifier; a trusted host performs the exact URL `git --no-replace-objects push` without force and signs execution evidence, while recovery verifies that evidence and reads back A. The archived RUN grants nothing and local tooling never runs the push.
- Treat A publication and `main` promotion as separate exact actions outside generic execution permission. Require fresh remote read-back, ancestry, and complete A tests. Archive, publication, promotion, production verification, activation, outcome review, and SEO remain separate gates.
- Remove only an authorized clean linked worktree, then delete only the authorized local worker branch. Never remove the primary checkout, and never delete the run branch the user still has to read.
- Task archival, worktree removal, and branch deletion remain separate ledger actions even when several are approved in one explicit readiness statement.

### Commit Messages

Every commit in a managed run follows `delivery-harness/references/commit-convention.md`. The message shape:

```text
<type>(<scope>): <imperative summary>

Task: <mission-id>/<task-token>
Trace: <TRACE-ID>[, <TRACE-ID>]
Verified: <command or action> (<pass signal>)
```

- Write in English. Keep the subject at 72 characters or fewer, lowercase `type` and `scope`, imperative summary, no final period. `type` is one of `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `build`, `ci`; `scope` is a stable area such as `auth` or `ui`, never a filename.
- One commit holds one kind of change: a task commit carries one verified outcome, a repair commit one root-cause fix, an integration commit reviewed heads and coordination state only, a bookkeeping commit `PLAN.md`/`RUN.md` only. Two kinds of change land as two commits in dependency order.
- Every commit names exactly one task ID, its upstream traces, and the actual verifier with its literal pass signal. A merge or integration-only commit uses the mission-level form (`chore(integration): integrate mission M2` with `Mission`, `Plan-Revision`, `Integrated-Head`), never a fake task body.
- Direct small work — including plan-mode edits outside a managed run — commits with the same subject shape `<type>(<scope>): <imperative summary>` and no trailers required. The subject is the record:

```text
fix(dashboard): correct save-button copy
chore(deps): bump playwright to 1.49
```

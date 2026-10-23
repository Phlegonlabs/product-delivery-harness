# Conditional Project Operating Rules

Read only the section triggered by project AGENTS.md. These shared rules retain their authorization and evidence boundaries. Local project facts stay in the project, not this installed reference.

## Monetization And Partner Channels

- When a product has pricing, paid access, purchase-gated features, or outside sellers, keep explicit Monetization Infrastructure and Partner Channel gates in `docs/product/PRD.md`; record `not_required` with a reason when either does not apply.
- Resolve the commercial model and purchase surfaces before selecting technology. RevenueCat is one candidate, never the default: compare current official evidence for native store billing, RevenueCat, Qonversion, Adapty, Superwall, Stripe Billing, Paddle, Lemon Squeezy, or another product-fit option.
- Treat affiliate, referral, and reseller as different motions. A reseller decision must cover deal registration, price authority or wholesale terms, customer ownership, provisioning, delegated administration, support, renewals, termination, and channel conflict; an affiliate link alone does not satisfy it.
- Keep billing/store, entitlement, paywall/checkout, merchant-of-record/tax, attribution, commission/payout, and reseller-operation responsibilities separate in PRD, architecture, stack decisions, implementation, and tests. Update affected UI Surface Contract entries through `product-definition-builder`, then update `ui-design.md` and `wireframes.html` through `ui-design-builder` before implementing customer, partner, pricing, purchase, or administration surfaces.

## Post-Delivery Activation

- Use `product-activation` preparation from a fixed usable initial build; verify final readiness against the actual release SHA and artifact. It owns `docs/ACTIVATION.md` and never edits or extends a delivery PLAN/RUN.
- Product Definition may create the first Activation seed when the path is absent. Preserve an existing record; only `product-activation` reconciles its live action, source, evidence, and readiness state.
- Probe purpose-built connector/API/CLI first, then Browser, Computer Use, and manual handoff. Capability never grants permission.
- Bind every external write to the exact account or organization, project or property, environment, action, and current action digest. DNS, permissions, credentials, billing, production traffic, public submission, data sharing, and destructive changes require action-time confirmation.
- Never record secret values. Password, MFA, OTP, CAPTCHA, banking, tax, legal attestation, and secret-value entry remain user handoffs.
- Refresh and read back every change. A success toast, mutation response, upload, submission, or owner statement does not prove behavior.
- Route a missing product hook to a new `delivery-harness` change and a missing requirement, metric, TEST ID, or release target to `product-definition-builder`. Activation never patches product code in place.
- Activation readiness is per release target and does not keep the delivery RUN open or replace the later outcome-review measurement window.

## Managed Product Delivery Harness Runs

The rules below apply only to a PLAN-v6/RUN-v11 managed route. They do not convert small direct work into a managed run.

- Size missions by `execution-task-decomposition.md#mission-cohesion-gate`; tasks inside a mission stay sequential under one writer.
- Give every writer an explicit file-ownership scope and a separate worktree. Workers and reviewers never delegate; the Harness parent dispatches every explorer, writer, and reviewer as a sibling.
- Freeze and integrate shared APIs, schemas, and types before starting dependent write missions in parallel.
- Read PLAN `branch_policy`. New `main-preview/1` work freezes the observed remote main head for ordinary work and hotfixes. Cut every initial-delivery or enhancement run branch from that frozen head, then create every implementation worktree from the resolved integration-branch SHA.
- Before dispatch, verify each worktree has the expected repository, branch/ref, exact base HEAD, and a clean status.
- Run focused checks in each completed worktree. Review counts, repair and the final validation follow `verification-gates.md`.
- With matching `integrate_locally` authorization, merge only worktree heads that pass the Worker Result Gate and the reviews their plan requires into the resolved integration branch.
- The RUN closes at local candidate C. Archive, publication, preview and promotion follow `branch-promotion-contract.md#managed-run-archive-before-promotion`. Pinned historical RUNs follow `delivery-harness/references/legacy-pins.md`.
- After a completed plan and before its archival, record every owner or agent update not already reflected in `docs/product/PRD.md` as one dated row in the `docs/tasks.md` Update Log — the fenced section the renderer preserves verbatim; product-affecting updates also follow Keep Product Contracts Current into the PRD in the same change.
- After the Closeout Bar, archive, publish and promote as `branch-promotion-contract.md#managed-run-archive-before-promotion` states. A failed post-A candidate or preview gate follows its "Post-A Candidate Or Preview Failure" section.
- Later enhancement work freezes a fresh remote base after the prior protected-branch state is resolved: remote `main` for ordinary work and hotfixes.

### Action Authorization

- Before any action represented in the RUN authorization ledger, verify its exact authorization. Preserve all 12 keys in the [Authorization Action Ledger](execution-state-model.md#authorization-action-ledger).
- Harness 0.38+ plan-backed work closes `local_only` at C. A is post-RUN and cannot be written into the archived RUN without changing itself.
- With matching `create_local_branches` authorization, work on the exact resolved non-default run branch.
- With matching `create_local_commits` authorization, commit only the verified task scope.
- Worker branches stay local. With matching `integrate_locally` authorization, integrate exact-head review-passing work into the resolved integration branch.
- Run the exact repository-defined focused verification and applicable E2E commands, then review the complete diff before local closeout. Any later publication needs its own authorization and candidate checks. If commands are undocumented, inspect the repository's package scripts and CI configuration and state the commands selected.
- Treat a PASS from the required automated E2E on the current head as the proof for its covered primary journeys. Record duplicate manual smoke as `not required - covered by current-head E2E`; require manual smoke only for a materially different environment or an uncovered visual/external-integration risk.
- Treat A publication, Preview acceptance, and `main` promotion as separate exact actions outside generic execution permission, unless one owner release instruction names them together (`branch-promotion-contract.md`). Require fresh remote read-back, ancestry, and the inherited exact-SHA evidence; a tree-equal server SHA inherits it. Archive, publication, protected landing, promotion, production verification, activation, outcome review, and SEO remain separate gates.
- Remove only an authorized clean linked worktree, then delete only the authorized local worker branch. Never remove the primary checkout or run branch the user still has to read. Never delete protected `main` or existing protected `development`, even under an old or wildcard cleanup grant.
- Task archival, worktree removal, and branch deletion remain separate ledger actions even when several are approved in one explicit readiness statement.

### Commit Messages

Every commit in a managed run follows `delivery-harness/references/commit-convention.md`. The message shape:

```text
<type>(<scope>): <imperative summary>

Task: <mission-id>/<task-token>
Trace: <TRACE-ID>[, <TRACE-ID>]
Verified: <command or action> (<pass signal>)
```

- Subject limits, types and scopes are in `commit-convention.md`.
- One commit holds one kind of change. Two kinds of change land as two commits in dependency order.
- Every commit names exactly one task ID, its upstream traces, and the actual verifier with its literal pass signal. A merge or integration-only commit uses the mission-level form (`chore(integration): integrate mission M2` with `Mission`, `Plan-Revision`, `Integrated-Head`), never a fake task body.
- Direct small work — including plan-mode edits outside a managed run — commits with the same subject shape `<type>(<scope>): <imperative summary>` and no trailers required. The subject is the record:

```text
fix(dashboard): correct save-button copy
chore(deps): bump playwright to 1.49
```

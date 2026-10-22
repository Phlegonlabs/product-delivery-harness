# Product Activation Stage

## Path Interpretation

Outside a real Markdown link, `references/...`, `assets/...`, `scripts/...`, and sibling skill paths such as `../delivery-harness/...` are logical installed-skill paths from `<product-activation-skill-root>`. `docs/...` remains repository-relative.

## Required Inputs

Read the applicable files before drafting or executing:

- `docs/product/PRD.md` for metrics, privacy decisions, and required `TEST-*` signals;
- `docs/product/architecture.md` for stable release targets and distribution channels;
- `docs/product/stack-decisions.md` for the approved Stack Decision Checkpoint, providers, and constraints;
- `docs/DEPLOYMENT.md` for environment URLs, deployed SHA evidence, configuration names, and external-console handoff;
- the tracked declarations and code paths that establish non-secret configuration names and implemented hooks.

Also read an existing `docs/ACTIVATION.md` in full. If a staged activation exists under `docs/.activation-staging/`, do not create another one until the user chooses whether to resume, publish, or preserve it.

An absent product package is a `contract_gap`. An absent release identity or ambiguous account, organization, project, property, app, environment, or store target blocks external writes.

## Workflow

Early website/app preparation follows [Initial Product Foundations](../../../delivery-harness/references/initial-product-foundations.md) at a fixed usable build.
Complete ready authorized setup before its dependent features. Preserve the same staged record for later release reconciliation.
Run closeout honestly: final-release obligations and unknown native artifacts may leave preparation blocked or structurally incomplete.
Report verified setup actions separately; do not call that result activation-complete or replace missing future bindings with the initial build.

Activation is execution by default. First inventory the exact external state and calculate the real delta from the product, implementation, Deployment, and existing Activation evidence. Reuse valid evidence only when its release identity and observed external state remain valid. Continue every ready, authorized required action through mutation, independent read-back, and applicable behavior check unless it is blocked by a concrete gap or the owner explicitly defers it. Do not stop after a seed, structural check, or checker pass, and do not replace an executable action with instructions to the owner. Only an explicit owner request for a documentation-only or planning pass may stop at preparation.

1. Validate product, release, and deployment inputs. From the repository root, always run `python "<product-definition-builder-skill-root>/scripts/check_product_package.py" --prd <approved PRD.md> --architecture <approved architecture.md> --stack-decisions <approved stack-decisions.md> --repo-root <repository-root> --require-filled --require-approved`. An absent package is a `contract_gap`. Run `delivery-harness/scripts/check_deployment.py` when applicable. The verified-source handoff command must include `--stack-decisions`, `--expected-repository`, and `--candidate-ref` when a candidate ref exists; it re-runs the full approved Product Definition and Deployment checks before accepting Activation evidence. Treat deployment checks as evidence, not activation proof.
2. Read `references/activation-contract.md` completely.

    For an adopted deployment, operations, or integration choice that is relevant to the exact target, consult `../delivery-harness/references/reference-selection.md` and only the relevant domain under `../delivery-harness/references/option-library/`. The catalog does not create actions, routes, accounts, or authority.
3. Read `references/profile-catalog.md` completely, then select `core` plus only the surface and feature overlays supported by the PRD, architecture, implementation, and owner decisions. The release-surface applicability matrix is exhaustive: hosted web requires `web`/frontend, browser extensions require `browser extension`, native targets require their OS profile, backend targets require `api / backend`, agents additionally require `agent/automation`, and CLI/other non-public targets require `cli/toolchain` or `other_nonpublic`. Record every rejected or unsupported overlay as `no` with an explicit `n/a — reason` instead of silently omitting an expected surface.
4. If no live activation record exists, start from `assets/templates/ACTIVATION.template.md`. Preserve the stable metric names, `TEST-*` IDs, release target IDs, and existing configuration names. Do not invent an account, query, callback, event, channel, or key name.
5. Create or resume `docs/.activation-staging/<run-id>/ACTIVATION.md`. Record the live baseline SHA-256 when a live record exists. Never edit the live record while the activation pass is incomplete.
6. Map every PRD metric and required `TEST-*` expected signal into **Outcome Coverage**, repeating the structured definition/obligation, baseline, target/guardrail, measurement window, source/method, owner, and expected-signal values exactly. Schema `product-activation/2` uses the typed source/method and owner columns; legacy `/1` records remain readable but are not the forward seed format. Define an `MS-*` source for each measurable signal or mark the signal blocked. A source is not verified merely because an SDK, tag, property, or dashboard exists.
7. Split external work into the smallest independently verifiable `ACT-*` actions. One action has one exact target, desired state, authorization digest, write attempt, read-back, and behavior check. Preview and production are separate actions.
8. Probe execution routes for the current session and exact target. Tool installation or a parent-session package listing alone is `unobserved`, not `available`.
9. Select one write route per action in this order unless the user explicitly names a surface: purpose-built connector, official API, official CLI, Browser, Computer Use, then manual handoff. Browser is the normal UI route for web consoles. Use Computer Use for native graphical interfaces or when Browser cannot serve the exact task.
10. Run `python "<product-activation-skill-root>/scripts/check_activation.py" --activation "docs/.activation-staging/<run-id>/ACTIVATION.md" --show-action-digests`. Place each computed digest in its staged ready action. Show the user one exact preview containing the `ACT-*` IDs, digests, service, account or organization, project or property, environment, current state, desired state, data destination, risk, and routes.
11. Bind ordinary reversible actions to an exact displayed batch approval. Ask at action time for DNS, persistent credentials, permissions, billing, production traffic, public submission, data sharing, destructive actions, or another high-impact change. Hand password, MFA, OTP, CAPTCHA, banking, tax, legal attestation, and secret-value entry to the user.
12. Before each mutation, re-read the exact target and precondition. Drift invalidates the digest and authorization. If the desired state already exists, perform read-only verification rather than spending the write grant.
13. Execute external writes serially per target. Mark the grant consumed on the first mutation attempt, including an ambiguous timeout. After an unknown result, read back before any retry; never create a duplicate resource or submission by switching routes blindly.
14. Refresh the provider state after each action. Record a distinct read-back and the behavior-level signal in non-secret evidence. A success toast, HTTP 2xx mutation response, upload completion, submission, or owner statement proves configuration at most; it does not prove behavior. After an owner completes a manual step, read back that exact target immediately before resuming other work.
15. Run `python "<product-activation-skill-root>/scripts/check_activation.py" --activation <staged ACTIVATION.md> --prd docs/product/PRD.md --architecture docs/product/architecture.md --deployment docs/DEPLOYMENT.md --stack-decisions docs/product/stack-decisions.md --repo-root <repository-root> --require-filled` throughout reconciliation. Before ending an execution pass, run that complete command with `--require-closeout`. The authority flags `--require-closeout`, `--require-verified-sources` and `--require-ready` also need `--expected-repository <owner/repository>`, plus `--candidate-ref <full-or-authority-ref>` when a target's source authority is `run.integration.branch`. Before outcome handoff add `--require-verified-sources`. To claim a target ready, add `--require-ready <release-target-id>` for each active target. A closeout failure means the affected action remains pending or blocked; it does not become activation-complete. Preparation may end only with a concrete blocker or explicit owner deferral, never as activation complete. A true no-op needs no synthetic action, but every architecture target must have a concrete `n/a` readiness disposition. The architecture parser is the only release-target authority; each target needs readiness or that concrete `n/a` disposition. Preparation may perform separately authorized deployment prerequisites at a fixed implementation SHA, but cannot pass readiness or verified measurement handoff until the exact release is available.
16. Before publishing, recompute the live baseline SHA-256. If the live file changed, stop and reconcile. Show the exact create or overwrite path and obtain approval unless the user's current instruction already authorizes it. Publish only the validated staged file; leave failed or paused staging intact.
17. Report readiness separately for each release target, every remaining blocker or manual step, and the verified `MS-*` sources. End the activation run. The later, owner-requested outcome review starts only after its real measurement window closes.

## Status And Outcome Handoff

Use the status rules in `references/activation-contract.md`. Keep `configured` distinct from `verified`, preserve `uncertain` results, and mark old evidence `stale` when its action digest, release binding, dependency, or external state changes.

`docs/ACTIVATION.md` is an operational record refreshed in place. Product Definition may create the first seed, but only this skill reconciles and verifies live actions. Git history retains prior versions; never archive this file with the PRD package or delete it during enhancement.

When an outcome review is requested and `docs/ACTIVATION.md` exists, validate it with the current PRD and verified sources first. The outcome review may use only `MS-*` rows whose release target, SHA, and artifact/build identity match the deployed release. Missing activation remains explicit and compatible for legacy or non-applicable products; never invent a source to complete a verdict.

## Reference Routing

- Always read `references/activation-contract.md` for the document schema, action digest, status, staging, authorization, and evidence rules.
- Read `references/profile-catalog.md` after the contract, then apply only the profiles justified by the current product surfaces and features.
- Use `assets/templates/ACTIVATION.template.md` for a new seed or legacy bootstrap.
- Run `scripts/check_activation.py` for structural, PRD-coverage, digest, evidence, readiness, and terminal-closeout checks. The checker is read-only.

## Output

Report:

- the live and staged activation paths;
- release target and SHA bindings;
- selected profiles and execution routes;
- completed, verified, blocked, stale, and manual `ACT-*` actions;
- accepted owner deferrals and the exact work left in them;
- verified `MS-*` measurement sources;
- target-by-target activation readiness;
- exact code or contract gaps routed back upstream;
- the measurement-window start or why it remains pending.

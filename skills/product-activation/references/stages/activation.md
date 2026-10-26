# Product Activation Stage

## Path Interpretation

Outside a real Markdown link, `references/...`, `assets/...`, `scripts/...`, and sibling skill paths such as `../delivery-harness/...` are logical installed-skill paths from `<product-activation-skill-root>`. `docs/...` remains repository-relative.

## Required Inputs

Before drafting or executing, read only these sections. The Workflow checkers still join each complete file.

- `docs/product/PRD.md`: `Data and Integration Requirements`, `Data and Trust`, `AI and Automation`, `Monetization and Partner Channels`, `Metrics`, and `Test Obligations`;
- `docs/product/architecture.md`: `Release Targets`, `Integrations`, `Deployment and Operations`, and `Observability`;
- `docs/product/stack-decisions.md`: the approved Stack Decision Checkpoint and each applicable `Recorded or Approved Stack`;
- `docs/DEPLOYMENT.md`: `Record`, `Required Secrets and Variables`, `External Console Setup`, `Release Target Status`, `Environment Status`, and `Product Activation Handoff`;
- the tracked declarations and code paths that establish non-secret configuration names and implemented hooks.

Read another section when a selected profile or action needs it, such as `Frontend Delivery Requirements` for web discoverability. Read an existing `docs/ACTIVATION.md` in full; this stage reconciles all of it. If a staged activation exists under `docs/.activation-staging/`, do not create another one until the user chooses whether to resume, publish, or preserve it.

An absent product package is a `contract_gap`. An absent release identity or ambiguous account, organization, project, property, app, environment, or store target blocks external writes.

## Workflow

Early website/app preparation follows [Initial Product Foundations](../../../delivery-harness/references/initial-product-foundations.md) at a fixed usable build. Preserve the same staged record for later release reconciliation.

Activation is execution by default: inventory the exact external state, calculate the real delta from the product, implementation, Deployment, and existing Activation evidence, and continue every ready, authorized required action through mutation, independent read-back, and behavior check. Only an explicit owner request for a documentation-only or planning pass may stop at preparation. [Target Readiness](../activation-contract.md#target-readiness) owns evidence reuse and closeout.

1. Validate product, release, and deployment inputs with the full `check_activation.py` command in step 15. It always runs `check_product_package.py` (`--require-filled --require-approved`, from `--repo-root <repository-root>`) and `check_deployment.py` when applicable, so do not run them separately. An absent package is a `contract_gap`. Deployment checks are evidence, not activation proof.
2. Read `references/activation-contract.md`.

    For an adopted deployment, operations, or integration choice that is relevant to the exact target, consult `../delivery-harness/references/reference-selection.md` and only the relevant domain under `../delivery-harness/references/option-library/`. The catalog does not create actions, routes, accounts, or authority.
3. Read `references/profile-catalog.md` Core, the surface sections that the architecture surface classes map to, and the selected overlays. Select `core` plus only the surface and feature overlays supported by the PRD, architecture, implementation, and owner decisions. The release-surface applicability matrix is exhaustive: hosted web requires `web`/frontend, browser extensions require `browser extension`, native targets require their OS profile, backend targets require `api / backend`, agents additionally require `agent/automation`, and CLI/other non-public targets require `cli/toolchain` or `other_nonpublic`. Record every rejected or unsupported overlay as `no` with an explicit `n/a — reason` instead of silently omitting an expected surface. Growth profiles follow the PRD `Shape` track: `web` may select `geo-readback`, `app` may select `aso-and-store-launch`, and `agent` may select `agent-directory`. Select one only when the PRD Growth Contract requires that discovery surface. Map each PRD Growth Contract Discovery Surfaces row by kind: `store-listing` → `aso-and-store-launch`, `directory` → `agent-directory`, `geo-page` → `geo-readback`.
4. If no live activation record exists, start from `assets/templates/ACTIVATION.template.md`. Preserve the stable metric names, `TEST-*` IDs, release target IDs, and existing configuration names. Do not invent an account, query, callback, event, channel, or key name.
5. Create or resume `docs/.activation-staging/<run-id>/ACTIVATION.md`. Record the live baseline SHA-256 when a live record exists. Never edit the live record while the activation pass is incomplete.
6. Map every PRD metric and required `TEST-*` expected signal into **Outcome Coverage** as one pointer row each; the PRD owns the definition, baseline, target, window, source/method and owner. Define an `MS-*` source for each measurable signal or mark the signal blocked. A source is not verified merely because an SDK, tag, property, or dashboard exists.
7. Split external work into the smallest independently verifiable `ACT-*` actions. One action has one exact target, desired state, authorization digest, write attempt, read-back, and behavior check. Preview and production are separate actions.
8. Probe execution routes for the current session and exact target. Tool installation or a parent-session package listing alone is `unobserved`, not `available`.
9. Select one write route per action in this order unless the user explicitly names a surface: purpose-built connector, official API, official CLI, Browser, Computer Use, then manual handoff. Browser is the normal UI route for web consoles. Use Computer Use for native graphical interfaces or when Browser cannot serve the exact task.
10. Run `python "<product-activation-skill-root>/scripts/check_activation.py" --activation "docs/.activation-staging/<run-id>/ACTIVATION.md" --show-action-digests`. Place each computed digest in its staged ready action. Show the user one exact preview containing the `ACT-*` IDs, digests, service, account or organization, project or property, environment, current state, desired state, data destination, risk, and routes.
11. Bind ordinary reversible actions to an exact displayed batch approval. Ask at action time for DNS, persistent credentials, permissions, billing, production traffic, public submission, data sharing, destructive actions, or another high-impact change. Hand password, MFA, OTP, CAPTCHA, banking, tax, legal attestation, and secret-value entry to the user.
12. Before each mutation, re-read the exact target and precondition. Drift invalidates the digest and authorization. If the desired state already exists, perform read-only verification rather than spending the write grant.
13. Execute external writes serially per target. Mark the grant consumed on the first mutation attempt, including an ambiguous timeout. After an unknown result, read back before any retry; never create a duplicate resource or submission by switching routes blindly.
14. Refresh the provider state after each action. Record a distinct read-back and the behavior-level signal in non-secret evidence. A success toast, HTTP 2xx mutation response, upload completion, submission, or owner statement proves configuration at most; it does not prove behavior. After an owner completes a manual step, read back that exact target immediately before resuming other work.
15. Run `python "<product-activation-skill-root>/scripts/check_activation.py" --activation <staged ACTIVATION.md> --prd docs/product/PRD.md --architecture docs/product/architecture.md --deployment docs/DEPLOYMENT.md --stack-decisions docs/product/stack-decisions.md --repo-root <repository-root> --require-filled` once before closeout. Before ending an execution pass, run that complete command with `--require-closeout`; the closeout rule is in [Target Readiness](../activation-contract.md#target-readiness). The authority flags `--require-closeout`, `--require-verified-sources` and `--require-ready` also need `--expected-repository <owner/repository>`, plus `--candidate-ref <full-or-authority-ref>` when a target's source authority is `run.integration.branch`. Before outcome handoff add `--require-verified-sources`. To claim a target ready, add `--require-ready <release-target-id>` for each active target. The architecture parser is the only release-target authority; each target needs readiness or a concrete `n/a` disposition. Preparation may perform separately authorized deployment prerequisites at a fixed implementation SHA, but cannot pass readiness or verified measurement handoff until the exact release is available.
16. Before publishing, recompute the live baseline SHA-256. If the live file changed, stop and reconcile. Show the exact create or overwrite path and obtain approval unless the user's current instruction already authorizes it. Publish only the validated staged file; leave failed or paused staging intact.
17. Report readiness separately for each release target, every remaining blocker or manual step, and the verified `MS-*` sources. End the activation run. The later, owner-requested outcome review starts only after its real measurement window closes.

## Status And Outcome Handoff

Use the status rules in `references/activation-contract.md`. Keep `configured` distinct from `verified`, preserve `uncertain` results, and mark old evidence `stale` when its action digest, release binding, dependency, or external state changes.

`docs/ACTIVATION.md` is an operational record refreshed in place. Product Definition may create the first seed, but only this skill reconciles and verifies live actions. Git history retains prior versions; never archive this file with the PRD package or delete it during enhancement.

When an outcome review is requested and `docs/ACTIVATION.md` exists, validate it with the current PRD and verified sources first. The outcome review may use only `MS-*` rows whose release target, SHA, and artifact/build identity match the deployed release. Missing activation remains explicit and compatible for legacy or non-applicable products; never invent a source to complete a verdict.

## Reference Routing

- `references/activation-contract.md`: schema, digest, status, staging, authorization, evidence and checker rules.
- `references/profile-catalog.md`: profiles, read by the scope in Workflow step 3.
- `assets/templates/ACTIVATION.template.md`: a new seed or legacy bootstrap.

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

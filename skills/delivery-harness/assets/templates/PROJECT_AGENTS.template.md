# Project Rules

This file is ready-to-use shared repository guidance. Resolve the repository's commands and protected paths from live project state; do not leave template placeholders or assume they are always the same across repositories.

## Runtime Boundary

- This file is the entry. It contains authority boundaries and routes, not complete procedures. Preserve the current host's effective instruction discovery and precedence.
- Apply `delivery-harness/references/delegation-contract.md` before direct or managed routing. Resolve worker identity, model, effort, fallback and delegation from effective agent configuration and AGENTS instructions. Verify actual launch/result identity. The actual frontend author reads the complete pinned `frontend-design` SKILL.md and applicable project design skills in its own context; verify the full-tree pin independently. Fresh independent review binds the exact candidate. One writer owns each checkout, including the parent. Preserve required independent review and configured execution choices.
- Use the general runtime adapter reference (`delivery-harness/references/runtime-adapters.md`) for observed capabilities, authorization, isolation and result contracts. Host policy supplies role/model and explicit bridge bindings; shared skills supply no provider-specific model default. External execution retains its own authorization and capability checks.
- Rules under **Managed Product Delivery Harness Runs** apply only after the Harness routes work into PLAN/RUN. Small direct work follows the shared principles, Git safety, and verification rules without creating Harness state, missions, workers, or worktrees unless the repository or user requires them.
- Preserve unrelated local work. Important local data needs explicit owner approval before deletion, overwrite, or move.

## Required Reading

- Before any managed Product Delivery Harness work, the session reads this file's **Managed Product Delivery Harness Runs** rules and the installed `delivery-harness` SKILL.md (the orchestration skill itself, loaded as a skill rather than a table slot); the Skill Bindings table below pins the stage-slot skills the harness dispatches, and their pinned SHA-256 hashes are verified by `delivery-harness/scripts/check_skill_bindings.py`.
- Before any product-affecting direct work, the session reads the affected sections of `docs/product/PRD.md` plus every document `docs/DOCUMENTS.md` names for that scope (retained wireframes, design package, architecture). A named source that does not exist yet is reported, not skipped.
- Skipping this reading is a blocking review finding: a change built on unread contracts is not a completed change.

## Skill Bindings

The delivery flow binds stage slots, not fixed skill names. This table binds the project's installed skills to those slots; updating it to adopt a new skill is a project edit, not a harness change, and a bound skill inherits the same modes, frozen sources, and review gates as the default.

| Slot | Stage | Bound skill | Pinned SHA-256 |
| --- | --- | --- | --- |
| ui_design | approved Product Definition → UI intake, directions, HiFi, approval | `pending` | `pending` |
| style_integration | approved PRD and selected direction → page theme and connected HiFi target | `pending` | `pending` |
| design_compilation | frozen design-system pair | `pending` | `pending` |
| frontend_implementation | implementation missions | `pending` | `pending` |
| ui_quality_verification | authorized HiFi review / consolidated UI acceptance | `pending` | `pending` |
| code_security_verification | fresh unified code-security review before final regression and closeout | `pending` | `pending` |

These rows are intentionally unresolved in the seed. Before managed work, observe the installed skill trees, show the exact choices and side effects to the owner, then replace each required stage slot with one skill name and its full-tree SHA-256. `pending` in both cells is allowed only outside the checked stage. Product Definition uses `--stage product-definition`; UI authoring uses `--stage ui-design`; compilation uses `--stage design-compilation`; a proven headless/backend-only scope uses `--stage backend`. Omit `--stage` for full UI delivery or unknown applicability. Recheck at every stage change; a stage result never authorizes a later stage. `frontend-design` is external and supports visual direction/frontend authoring only; do not claim compilation, conformance, or read-only modes it does not define. The pinned `impeccable` profile requires separate authorization for subagents, browser/server activity, snapshot writes, and any optional binary download; it is not a Harness read-only reviewer. `delivery-harness/scripts/check_skill_bindings.py` rejects unresolved, fenced, duplicate, malformed, missing, or drifted bindings. The code-security reviewer receives no implementation or lifecycle authority.

## Mandatory Governance Routes

Resolve `delivery-harness/` references against the observed installed delivery-harness skill root, not a presumed target-local `skills/` directory. Read the complete named section before the action named by its trigger. The route is mandatory; an owner file's rules cannot be widened by this entry.

| Trigger | Complete rule owner |
| --- | --- |
| First work in a session or every skill invocation | `delivery-harness/references/governance/task-and-handoff.md#project-entry-and-current-work` |
| Task start; significant edit, commit, merge, branch switch, or observed external change | `delivery-harness/references/governance/task-and-handoff.md#repository-change-checkpoints` |
| Completion or handoff | `delivery-harness/references/governance/task-and-handoff.md#handoff-documentation-audit` and `delivery-harness/references/governance/task-and-handoff.md#consumer-completion` |
| Local deletion, overwrite, or move | `delivery-harness/references/governance/development-rules.md#protect-local-data` |
| Implementation or repair | `delivery-harness/references/governance/development-rules.md#keep-changes-simple` and `delivery-harness/references/governance/development-rules.md#consumer-core-development-principles` |
| New or changed documentation | `delivery-harness/references/governance/development-rules.md#document-writing` |
| A task introduces or retires a local-only file class | `delivery-harness/references/gitignore-contract.md` |
| Product requirements, architecture, UI impact, redesign, pricing, or partner channel | `delivery-harness/references/governance/product-contracts.md#consumer-keep-product-contracts-current` |
| Pricing, paid access, purchase-gated features, or outside sellers | `delivery-harness/references/project-operating-rules.md#monetization-and-partner-channels` |
| Branch, commit, integration, archive, publication, cleanup, or protected-branch landing | `delivery-harness/references/governance/managed-delivery.md#git-safety` and `delivery-harness/references/commit-convention.md` |
| Managed PLAN/RUN | `delivery-harness/SKILL.md`, `delivery-harness/references/governance/managed-delivery.md#managed-product-delivery-harness-runs`, and `delivery-harness/references/project-operating-rules.md#managed-product-delivery-harness-runs` |
| Deployment model, verification, or platform move | `delivery-harness/references/deployment-contract.md#deployment-contract` |
| Post-delivery activation | `delivery-harness/references/project-operating-rules.md#post-delivery-activation` |
| Review or acceptance claim | `delivery-harness/references/governance/managed-delivery.md#review-guidelines` |

The Epic and index record observed work; neither record grants product approval, marks a test PASS without evidence, or authorizes a commit, branch, install, push, deployment, cleanup, publication, or external action.

## Deployment

- Resolve this section from the live project before finishing bootstrap; keep it only when the repository deploys, per the Product Delivery Harness `deployment-contract.md`.
- Platform and mode: the deploy platform id (for example `cloudflare`, `vercel`, `aws`) and `git_connected`, `ci_connected`, or `manual`.
- Non-production deploys from the exact candidate run branch or immutable candidate SHA; production deploys from `main`. Candidate and production environments remain separate, and a candidate PASS never proves production.
- Hosted-browser production uses `parity_capture.py` at the production URL. Browser-extension, native, and desktop targets use their platform automation or labeled manual captures and never substitute URL parity. Bind every result to the exact production SHA and artifact.
- Production and preview bind fully separate D1/KV/R2/Durable-Object resources: the preview environment declares its complete binding set, never references a production resource ID, and the deployment record's Resource Isolation table carries both ID sets.
- Before a deployable push, reconcile `docs/DEPLOYMENT.md` against tracked environment declarations, platform config, CI workflows, and auth/integration code. List exact secret and variable names, preview/production placement, source owner, and external-console tasks; never read or record secret values. After deployment, update only from read-only evidence and report every pending human action.
- Preview mechanism or URL pattern: <fill>
- Production URL: <fill>
- Deployed-commit check (platform API/CLI command or response header): <fill>
- Protected resources preview must never bind: <databases, buckets, secrets, domains>

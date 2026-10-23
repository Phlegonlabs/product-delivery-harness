# Project Rules

## Skill Activation

Use this suite only when the user explicitly requests a named skill or continues its already requested workflow.
A `$skill-name` invocation or a natural-language request naming the skill qualifies; discussing a skill does not.
Required checks and dependencies stay within that requested outcome. A new top-level stage needs an explicit request.
Installed skills, seeded instructions, product documents and existing PLAN/RUN files do not activate a workflow.
For ordinary tasks, follow effective host and repository instructions plus the user's request.
Do not run Harness routing, document sync, Epic/index updates, template audits or PLAN/RUN solely because these instructions exist.
Existing data protection and action authorization still apply.

## Runtime Boundary

- This file is the entry. It contains authority boundaries and routes, not complete procedures. Preserve the current host's effective instruction discovery and precedence.
- Within an explicitly requested skill workflow, apply [Parent-Owned Delegation](skills/delivery-harness/references/delegation-contract.md) before direct or managed routing. Resolve executors and delegation from effective agent configuration, AGENTS instructions and observed tools. The actual frontend author reads the complete pinned `frontend-design` SKILL.md and applicable project design skills in its own context; verify the full-tree pin independently. Fresh independent review binds the exact candidate. One writer owns each checkout, including the parent; preserve required independent review and actual execution evidence.
- For explicitly requested managed execution, use [General Runtime Adapter](skills/delivery-harness/references/runtime-adapters.md) for observed native capabilities, authorization, isolation and result contracts. Capability does not grant an action.
- Within an explicitly requested `delivery-harness` workflow, direct work uses one writer and one coherent verification sequence. Managed rules apply only after work routes into PLAN/RUN.
- Preserve unrelated local work. Important local data needs explicit owner approval before deletion, overwrite, or move.
- This source repository intentionally omits the template's Skill Bindings (it has no consumer stage slots), Deployment and Post-Delivery Activation (it deploys and activates no product), and the delivery-acceptance bullet (it has no product accounts or data). Its Git Flow replaces the template's Git Safety, and its Required Reading replaces the template's. Treat these as local choices, not drift, in the handoff audit.

## Worker Policy

Effective agent definitions and AGENTS instructions own worker selection, models, effort, fallback and delegation topology. Shared skills own methods, inputs, authorization, evidence and acceptance; they do not supply competing worker policy. Persisted RUN labels describe responsibilities, not native agent identities; preserve the pinned execution protocol.

## Mandatory Governance Routes

Harness-specific routes below apply only within an explicitly requested skill workflow.
Source reading, verification and Git rules still govern maintenance of this repository without starting a consumer delivery workflow.
Read the complete linked section before its applicable action. The links are mandatory, and an owner file's rules cannot be widened by this entry.

| Trigger | Complete rule owner |
| --- | --- |
| Explicit invocation of a skill in this suite | [Project Entry](skills/delivery-harness/references/governance/task-and-handoff.md#project-entry-and-current-work) |
| Task start; significant edit, commit, merge, branch switch, or observed external change | [Repository Change Checkpoints](skills/delivery-harness/references/governance/task-and-handoff.md#repository-change-checkpoints) |
| Completion or handoff | [Handoff Documentation Audit](skills/delivery-harness/references/governance/task-and-handoff.md#handoff-documentation-audit) and [Source Completion](skills/delivery-harness/references/governance/task-and-handoff.md#source-completion) |
| Local deletion, overwrite, or move | [Protect Local Data](skills/delivery-harness/references/governance/development-rules.md#protect-local-data) |
| Implementation or repair | [Keep Changes Simple](skills/delivery-harness/references/governance/development-rules.md#keep-changes-simple) and [Source Core Development Principles](skills/delivery-harness/references/governance/development-rules.md#source-core-development-principles) |
| New or changed documentation | [Document Writing](skills/delivery-harness/references/governance/development-rules.md#document-writing) |
| A task introduces or retires a local-only file class | [Gitignore Contract](skills/delivery-harness/references/gitignore-contract.md) |
| Product requirements, architecture, UI impact, redesign, pricing, or partner channel | [Product Contracts](skills/delivery-harness/references/governance/product-contracts.md#source-keep-product-contracts-current) |
| Pricing, paid access, purchase-gated features, or outside sellers | [Monetization And Partner Channels](skills/delivery-harness/references/governance/product-contracts.md#monetization-and-partner-channels) |
| Editing `skills/`, a documented flow, or running a seeded consumer flow | [Source Required Reading](skills/delivery-harness/references/governance/source-maintenance.md#required-reading) |
| Decomposing PRD work into missions | [Mission Task Split](skills/delivery-harness/references/governance/source-maintenance.md#mission-task-split) |
| Branch, commit, integration, archive, publication, cleanup, or source main landing | [Source Git Flow](skills/delivery-harness/references/governance/source-maintenance.md#git-flow) and [Atomic Commit Convention](skills/delivery-harness/references/commit-convention.md) |
| Every atomic source task before verification | [Required Verification](skills/delivery-harness/references/governance/source-maintenance.md#required-verification) |
| Formal release, version promotion, tag, bundle installation, or host reload | [Update Local Skills](skills/delivery-harness/references/governance/source-maintenance.md#update-local-skills) and [Required Verification](skills/delivery-harness/references/governance/source-maintenance.md#required-verification) |
| Review or acceptance claim | [Source Review Guidelines](skills/delivery-harness/references/governance/source-maintenance.md#review-guidelines) |
| Creating or resuming managed PLAN/RUN | [Managed And Consumer Delivery](skills/delivery-harness/references/governance/managed-delivery.md#managed-product-delivery-harness-runs), [Conditional Project Operating Rules](skills/delivery-harness/references/project-operating-rules.md#managed-product-delivery-harness-runs), and the canonical Harness [SKILL.md](skills/delivery-harness/SKILL.md) |

The Epic and index record observed work; neither record grants product approval, marks a test PASS without evidence, or authorizes a commit, branch, install, push, deployment, cleanup, publication, or external action.

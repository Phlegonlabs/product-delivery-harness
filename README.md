<p align="center">
  <img src="./assets/readme-cover-en.png" alt="Product Delivery Harness — define, design, deliver, and verify" width="100%">
</p>

<p align="center">
  <strong>English</strong> | <a href="README.zh-TW.md">繁體中文</a> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.es.md">Español</a>
</p>

<p align="center">
  <a href="https://github.com/Phlegonlabs/product-delivery-harness/actions/workflows/harness-ci.yml"><img alt="CI" src="https://github.com/Phlegonlabs/product-delivery-harness/actions/workflows/harness-ci.yml/badge.svg"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-0.66.0-059669?style=flat-square">
</p>

# Product Delivery Harness

Skills for turning product ideas and change requests into verified software with Codex, Claude Code, Pi or another skills-capable host. Product definition, design, implementation, security and activation retain their own sources, evidence and owner decisions.

## Install

You need Python 3.10+, Git and a host that discovers `~/.agents/skills/`. On Windows, run `./install.sh` in Git Bash.

```bash
git clone https://github.com/Phlegonlabs/product-delivery-harness.git
cd product-delivery-harness
./install.sh
```

The installer locks the destination and stages only Git-index-tracked bundle files. It backs up current and legacy managed IDs under `~/.agents/skill-backups/product-delivery-harness/`, then verifies every installed path and byte.

It rejects unsafe links and unexpected source artifacts. Attempt ownership markers limit rollback to that attempt; foreign paths and prior backups remain intact. Its source receipt records the source SHA and dirty state.

The installer copies scripts, references, assets and templates. Tests stay in the source checkout; run them there. Install the pinned Python dependencies before validation:

```bash
python -m pip install -r skills/delivery-harness/requirements-test.txt
```

Updates use the same installer, never raw-copy replacement. Obtain authorization, quiesce relevant skill sessions and retain backups; start a fresh host session after verified success. A failed install rolls back. If later verification fails, rerun the installer from the previous release tag.

For upgrades from 0.23 or earlier, archive the legacy directories under their original IDs in the same backup: `full-harness` → `delivery-harness`, `prd-builder` → `product-definition-builder`, `product-design-builder` → `design-system-compiler`.

UI work also needs the exact external `frontend-design` and `impeccable` trees in the [dependency manifest](skills/delivery-harness/assets/external-skill-dependencies.json). Follow their recorded installation routes, then run `check_external_skill_dependencies.py`. Review changed trees before updating full-tree pins. Project Skill Bindings keep owner-confirmed choices; never substitute a skill silently.

## Start here

| Your starting point | Skill | Result |
| --- | --- | --- |
| Product idea | `product-definition-builder` | Approved PRD, architecture, stack and TEST obligations |
| Approved Product Definition with UI | `ui-design-builder` | Directions, complete HiFi, browser evidence and Visual Approval |
| Approved HiFi requiring a design system | `design-system-compiler` | Frozen pair and source-bound derived HTML |
| Scoped implementation or maintenance | `delivery-harness` | Direct work or managed PLAN/RUN |
| Fixed integrated code candidate | `code-security-review` | Read-only exact-SHA security result and coverage gaps |
| External setup or release readiness | `product-activation` | Authorized actions, readback and readiness per target |
| Public production site | `seo-growth-review` | Read-only search and measurement review with routed follow-ups |

Each bundled skill can run independently when its required inputs are present. The full pipeline is optional.

For relevant choices or adopted decisions needing context, use [reference selection](skills/delivery-harness/references/reference-selection.md) and the [optional catalog](skills/delivery-harness/references/option-library/README.md). Neither is a prerequisite or grants execution authority; existing decisions and approvals remain binding.

## Typical prompts

Use `$skill-name` in Codex, or ask your host for the named skill. State the exact write scope and local or remote outcome.

```text
Use $product-definition-builder to define this product, including complete frontend/backend architecture, data/auth/deployment choices, coherent stack options, UI behavior, release targets, tests, and Product Definition Approval. Stop before UI design.
```

```text
The Product Definition is approved. Use $ui-design-builder with the `ui-design/3` contract and mandatory $frontend-design. Run the product preflight, read the PRD UI Surface Contract directly, and show three materially different directions over the same representative cases for my selection.
```

```text
I selected a direction. Continue $ui-design-builder with $frontend-design: build the complete connected HiFi, run the HiFi completeness preflight, then run separately authorized $impeccable critique and audit plus H1-H9 grading. Ask for one full Visual Approval covering copy, structure, product menus, tabs, visuals and tokens, then use $design-system-compiler for the required `design-system/4` pair and frozen derived HTML.
```

```text
Use $delivery-harness to implement the approved plan. Create a branch and commit the verified change, but do not push or open a PR.
```

```text
The delivery is complete. Use $product-activation for the production release targets, configure only the exact external actions I approve, verify each result by read-back, and stop after recording activation readiness and the measurement-window handoff.
```

```text
Use $seo-growth-review to audit this production website, reconcile Search Console visibility with GA4 on-site outcomes, prioritize evidence-backed keyword and page opportunities, and route every proposed change without modifying the site or external accounts.
```

## What is included

| Skill | Owns |
| --- | --- |
| `product-definition-builder` | `PRD.md`, `architecture.md`, `stack-decisions.md`, research and Product Definition Approval |
| `ui-design-builder` | `docs/design/ui-design.md`, direction studies and the approved complete HiFi package |
| `design-system-compiler` | Frozen `design-system.md` / `design-system.json` and `design-system-preview.html` |
| `delivery-harness` | Scope routing, authorization, tasks, integration, verification and PLAN/RUN when needed |
| `code-security-review` | Security lens on the exact candidate; findings, tools, coverage and exclusions |
| `product-activation` | `docs/ACTIVATION.md`, external setup, behavior proof and measurement handoff |
| `seo-growth-review` | Production SEO and organic-growth evidence; inline review or an explicitly requested report |

## Standalone skills

[Go To Market](standalone-skills/go-to-market/SKILL.md) selects channels and experiments. [GTM Content](standalone-skills/gtm-content/SKILL.md) prepares channel-specific drafts, assets and calendars.

[README Studio](standalone-skills/readme-studio/SKILL.md) prepares project READMEs with real demonstrations. [Release Packager](standalone-skills/release-packager/SKILL.md) verifies release artifacts and consumer installation paths.

These four complete skill directories require separate host registration; `install.sh` installs only the seven core skills. Registration, builds, downloads, signing, publication, scheduling and account changes retain their own authorization. Reuse existing product and measurement records; add no review wave.

## How the system fits together

```mermaid
flowchart LR
  Product["Product Definition + owner approval"] --> UI["UI directions + complete HiFi"] --> Design["Visual Approval + required design-system pair"]
  Product -->|"headless or scoped enhancement or maintenance"| Harness["Direct or managed delivery"]
  Design --> Harness
  Harness --> Review["One combined review on final SHA"] --> Tests["One broad final validation"] --> C["Fixed candidate C"]
  C -->|managed| A["Managed only: archive-only A"] --> Publish["Authorized candidate publication + Preview when needed"]
  C -->|direct| Publish
  Publish --> Main["Separately authorized exact-SHA main landing"] --> Activate["Activation per target"] --> Outcome["Measured outcome + optional SEO review"]
```

Initial UI requires design and all applicable self-reviews before Harness execution. Follow [author self-review](skills/delivery-harness/references/pre-delivery-self-review.md) at the Product, direction and HiFi exits below.

## Operating rules

The delivery core makes one size decision: one writer and one coherent verification sequence stay direct. Independent writable missions, durable handoff or a bounded correction graph use PLAN/RUN. Missions are feature batches; fine tasks keep their own atomic commits.

- [Entry and handoff](skills/delivery-harness/references/governance/task-and-handoff.md): inspect current instructions and sources; unknown loaded identity stays unknown.
- [Delegation](skills/delivery-harness/references/delegation-contract.md): agent configuration and AGENTS choose executors, models, effort and fallback. One writer owns each checkout; assigned workers never delegate.
- [Verification](skills/delivery-harness/references/verification-gates.md): bind required evidence to the exact candidate; missing capability or evidence stays blocked.
- [Candidate publication and promotion](skills/delivery-harness/references/branch-promotion-contract.md): preserve exact targets, action grants and remote readback; never force-push.
- [Source maintenance](skills/delivery-harness/references/governance/source-maintenance.md): use focused atomic checks and one complete candidate matrix.

Before every handoff, check source hashes, the Epic record and document consistency. `docs/tasks.md` is a RUN-derived view; generated content is not hand-edited. [Document sync](skills/delivery-harness/references/document-sync-contract.md), [bounded repairs](skills/delivery-harness/references/bounded-enhancement.md) and [delivery acceptance](skills/delivery-harness/references/delivery-acceptance-contract.md) own these checks.

| Stage | Default review and stop condition |
| --- | --- |
| Product Definition | One author self-review of the whole package after drafting and research reconciliation; recheck affected changes before owner approval. |
| Directions | The same author checks and repairs rendered studies before owner selection. Three studies; the owner chooses. A modification adds one revised selected study and decision; rejection starts a new set. |
| HiFi | After completeness preflight, the same author self-reviews and repairs before independent review. One diagnostic wave, one consolidated repair and one affected-scope re-review. Required browser coverage, Impeccable `critique` **and** `audit`, rounded H1–H9 overall **at least 85** and every dimension **at least 80**, then Visual Approval. Carry unchanged evidence forward with its identity. |
| Delivery | `review_policy: final_candidate`: one combined code, visual-if-UI and security review on the fixed final SHA. Use a real browser for UI. Allow one consolidated repair and one targeted recheck of original findings, changed code and direct consumers; rebind security with full scope. A failed recheck stops at `blocked`. |
| Release | One owner instruction may name several exact release actions. Archive-only A and tree-equal server main S inherit verified evidence under the rules below. A changed tree is a new candidate. |
| Activation | Verify authorization, independent readback and applicable behavior for each release target; preparation and production readiness remain separate. |

A missing `review_policy` retains legacy `per_mission` behavior. Preserve frozen PLAN/RUN pins and historical approvals; never reset consumed attempts by renaming a node. A further review attempt needs the recorded explicit owner decision. Security is mandatory for code delivery; without it report `UNVALIDATED`, never PASS. The first HiFi pass covers every audit axis. Its re-review repeats critique and audit on affected pages and states while retaining the full evidence matrix.

Impeccable remains mandatory for HiFi, but is not the default read-only implementation reviewer. Its workflow needs separate authorization for subagents, browser/server activity, snapshot writes and optional downloads. Product, stack, direction and Visual Approval decisions stay with their owners.

## General runtime adapter

Current drivers are `subagents` and `sequential_parent`; map observed native tools through the [runtime adapter](skills/delivery-harness/references/runtime-adapters.md). Parent execution cannot satisfy an independent review. Host verifiers use current user permissions and provide no filesystem or network confinement. Capability never grants an action.

Preserve all twelve [action permissions](skills/delivery-harness/references/execution-state-model.md#authorization-action-ledger):

```text
invoke_external_runtime, spawn_subagents, create_user_owned_tasks,
create_local_worktrees, create_app_managed_worktrees, create_local_branches,
create_local_commits, integrate_locally, push, archive_worker_tasks,
remove_worktrees, delete_branches
```

Current RUNs close `local_only`, with `push` false and `pushed_head_sha` null. Publication, protected-branch landing, deployment, installation, archival and cleanup retain their separate grants.

## Repository layout

| Path | Purpose |
| --- | --- |
| `skills/` | Seven canonical skills, references, assets, templates and source tests |
| `standalone-skills/` | Separately registered optional skills |
| `assets/` | README cover assets |
| `docs/` | Live index and task records |
| `.github/workflows/harness-ci.yml` | Exact-candidate CI |
| `install.sh` | Verified bundle installation and updates |

## Maintain the skills

Edit canonical sources and update all four README descriptions in the same change. Select focused tests and negative cases from the changed files. Run tests from the source checkout:

```bash
python skills/delivery-harness/scripts/check_skill_spec.py
python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_skill_contract.py"
python skills/delivery-harness/scripts/docs_weight.py
git diff --check
```

The [required matrix](skills/delivery-harness/references/governance/source-maintenance.md#required-verification) runs once on the fixed candidate through CI. Run it locally only when CI is unavailable. Preserve browser and native coverage; failures and changed inputs require affected rechecks. Retain the origin of reused evidence.

## Releasing

Follow the [source Git flow](skills/delivery-harness/references/governance/source-maintenance.md#git-flow) and [required verification](skills/delivery-harness/references/governance/source-maintenance.md#required-verification). Land the reviewed source candidate through its required PR to protected `main`; tag that commit `v<version>`. Update these release surfaces together:

1. `package.json` version and `skills/delivery-harness/VERSION`.
2. Version badges and current version-history entries in all four READMEs.
3. `required_harness_version` in `assets/templates/MISSION_RUNBOOK.template.md` under the delivery skill.
4. Keep tests deriving versions from `VERSION`, not new hard-coded literals.

Archive-only A must be C's direct child and pass exact receipt-bound archive verification before inheriting C's evidence. Only receipt-listed coordination/evidence moves, optional generated `docs/tasks.md`, the `docs/DOCUMENTS.md` update and `ARCHIVE_RECEIPT.json` may differ. All other paths stay unchanged. Retain C's reviewed SHA and original result origins; inherited evidence is never a fresh execution at A. A tree-equal server-created main SHA S inherits the candidate evidence with its original origin; equality alone requires no repeated suite or security review. A different tree needs new candidate verification.

Publication requires the exact owner-authorized SHA and branch, a no-force push and remote readback. A single release instruction may bind these grants together; stop on drift or failed gates. After a verified formal release, update a changed installed bundle through the official installer at a quiescent boundary, with backup and verification. A badge proves neither installation nor deployment.

## Security and data safety

Keep credentials and user data out of the repository. Preserve unrelated files, worktrees and backups; deletion or replacement needs its exact owner authorization. Read-only security review never installs scanners, edits code or probes live targets without separate scope. See [security review](skills/code-security-review/SKILL.md) and [data protection](skills/delivery-harness/references/governance/development-rules.md#protect-local-data).

## License

[MIT](LICENSE). Retain third-party licenses and attribution for reused source and assets.

## Version history

- **0.66.0** — Cut repeated review rounds across PRD, UI and delivery while keeping 85/80, Impeccable, Visual Approval and exact-SHA security review. Plan missions as feature batches with one combined-lens reviewer each and skip a code integration review only on a proven clean merge chain. Repair once after all reviews of a candidate return and re-review only the repair. Scope HiFi re-review to the ledger with carried rows, revise a modified direction as one study, and catch unreachable surfaces and dead-end states in the PRD check. Keep one Harness contract per RUN and per design round, record unobserved identity once per session, and load a short entry checklist instead of the long contracts. Fix retention false defects, a commit-boundary race in integration recording, and release the AgentKiosk compiler, state-coverage, role-policy and ingestion work.

- **0.65.3** — Use one design review wave and one implementation UI acceptance while retaining 85/80 and required evidence. Deliver complete visual inputs to authors and let agent configuration choose workers. Preserve frozen runs and repair diagnostic coverage, acceptance reuse, and staged Activation digests.

- **0.65.2** — Publish the complete four-language delivery flowchart. Mark PRD self-review, foundation timing, MultiAgent handoffs, existing review counts and parallel GTM inputs. Record Instagram and Threads as the current owner context, evaluate Facebook Pages and keep X optional. Preserve 85/80 and existing review budgets.

- **0.65.1** — Clarify one complete PRD package author review and affected-scope rechecks before approval. Order core-journey proof and applicable load, cost, migration and recovery evidence within existing engineering tasks. Add X channel selection, content guidance and draft-to-measurement handoffs to the optional GTM skills. Explain roles, foundation timing and review limits in all four READMEs. Reuse existing records and review budgets; no new schema or review wave.

- **0.65.0** — Require HiFi overall 85 and every H1-H9 dimension 80, with mandatory Impeccable and bounded repair review. Move build access, repository-protection readback, AEO/search, deployment, analytics, feedback, errors and alerts into existing startup stages. Explain parent-owned MultiAgent collaboration. Add guarded runtime observations, advisory compiler-source diagnostics and optional GTM strategy/content handoffs. Current HiFi acceptance changes; historical approvals and evidence retain their meaning.

Earlier releases: [CHANGELOG.md](CHANGELOG.md).

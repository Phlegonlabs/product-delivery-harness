<p align="center">
  <img src="./assets/readme-cover-en.png" alt="Full Stack Harness — plan, build, verify, and land" width="100%">
</p>

<p align="center">
  <strong>English</strong> | <a href="README.zh-TW.md">繁體中文</a> | <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/Phlegonlabs/fullstack-goal-dev/actions/workflows/harness-ci.yml"><img alt="CI" src="https://github.com/Phlegonlabs/fullstack-goal-dev/actions/workflows/harness-ci.yml/badge.svg?branch=main"></a>
  <img alt="Private marketplace" src="https://img.shields.io/badge/marketplace-private-111827?style=flat-square">
  <img alt="Codex" src="https://img.shields.io/badge/Codex-supported-2563EB?style=flat-square">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude_Code-supported-D97706?style=flat-square">
  <img alt="Version" src="https://img.shields.io/badge/version-0.2.0-059669?style=flat-square">
</p>

# Full Stack Harness

Private skill marketplace for turning a product idea or change request into a verified delivery flow with Codex or Claude Code.

It is not a prompt collection. The plugin separates product definition, visual design, and engineering execution so each stage has one source of truth, a bounded handoff, and its own verification.

> Define the product. Make the design concrete. Execute only the work that is ready. Verify the exact result before it moves.

## Start here

| If you have... | Start with | What you get |
| --- | --- | --- |
| A product idea | `prd-builder` | Requirements, architecture, stack decisions, wireframes, sourced market research, and the design system |
| A scoped change in an existing repository | `fullstack-harness-engineering` | Direct implementation for small work, or a managed PLAN/RUN flow for large work |

The skills can be used independently. You do not need to run the entire pipeline for every task.

## Core guarantees

- **Small work stays small.** One bounded change uses a direct inspect, implement, verify, and review loop.
- **Large work is explicit.** PLAN v5 defines the typed graph; RUN v10 records authorization, attempts, and evidence.
- **Workers are isolated.** Write missions use dedicated worktrees and bounded scopes. The parent validates every returned commit and diff.
- **Capability is not permission.** A runtime may be able to push or clean up, but each action still needs exact authorization.
- **Evidence follows the SHA.** A new commit invalidates earlier gate and UI evidence for the old head.
- **The run ends at the push.** The harness commits and pushes the run's own branch. Landing it on the default branch is yours to do.

## What is included

| Skill | Use it for | Main output |
| --- | --- | --- |
| `prd-builder` | Product discovery, requirements, architecture, frontend-stack decisions, low-fidelity wireframes, a post-draft market-research gap pass, and the design system: tokens, primitive contracts with closed variant sets, product components, motion rules, and the state matrix | `PRD.md`, `architecture.md`, `stack-decisions.md`, `wireframes.md`, `market-research.md`, `design-system.md`, `design-system.json` |
| `fullstack-harness-engineering` | Shared size gate, PLAN/RUN, authorization, local verification, and integration | Direct work, `RUN.md`, or `PLAN.md` + `RUN.md` |
| `fullstack-harness-codex` | Top-level Codex tasks, one app-managed worktree per mission, and task-local read-only Multi-agent helpers | Runtime launch directives and worker results |
| `fullstack-harness-claude-code` | Claude Dynamic Workflow and parent-managed worktrees | Runtime launch directives and worker results |

The delivery core makes one size decision before it invokes managed orchestration:

- Small work stays direct with no planner, scheduler, PLAN/RUN, subagent, or external-runtime preflight by default.
- Large work enters managed planning. It may use `RUN.md` for a sequential delivery or `PLAN.md` and `RUN.md` for multiple missions and durable handoff.
- Scheduler fan-out starts only when a large plan has at least two independent ready missions. The core then loads exactly one host adapter; external runtimes are preflighted only when a selected route needs them.
- Work never waits for remote CI. A run finishes when its verified integration head is pushed to the run's own branch.

Size means coordination scope and blast radius, not a raw file or line count. If small work grows, the Harness preserves completed work and plans only the remainder.

## How the system fits together

```mermaid
flowchart LR
  Idea["Product idea or change request"] --> PRD["prd-builder\nProduct and technical definition"]
  PRD --> Harness["fullstack-harness-engineering\nShared delivery core"]
  Harness --> Runtime["One host adapter\nCodex or Claude Code"]
  Runtime --> Evidence["Local tests and UI evidence"]
  Evidence --> Push["Push to the run's own branch\nLanding on the default branch is yours"]
```

You can start at any stage. For example, use the Harness alone to fix an existing app. The skills keep their responsibilities separate: `prd-builder` defines what to build and what it looks like, and the Harness builds it without redesigning it.

## Delivery model

The Harness is built around explicit boundaries:

1. Inspect the current project and identify the required work.
2. Freeze the relevant contracts, sources, scope, and verification steps.
3. Plan dependencies before starting implementation when the task is large enough to need it.
4. Use parallel workers only when the work is independent, isolated, and explicitly authorized.
5. Verify task results, integrations, UI journeys where relevant, and the final diff.
6. Stop with verified local evidence unless a remote outcome is requested; then push the run's own branch with exact push authorization. Opening a PR, merging, and deploying are your own steps outside the Harness.

For plan-backed work, it records task scope, dependencies, worker ownership, verification commands, and action-specific authorization. A passing test does not authorize a push, worktree removal, or branch deletion.

```mermaid
flowchart TB
  Intake["Intake: request, repo, instructions"] --> Size{"small or large?"}
  Size -->|small| Direct["Direct parent work<br/>no PLAN/RUN, no scheduler"]
  Size -->|large| Plan["PLAN v5 + RUN v10<br/>frozen contracts, authorization ledger"]
  Plan --> Observe["Record observed git + batch_base_sha<br/>(the selector returns an empty frontier without it)"]
  Observe --> Frontier["Ready frontier<br/>dependencies, scope/resource conflicts, permission gates<br/>bounded by observed slots x isolation x conflicts"]
  Frontier --> Host["One host adapter: codex or claude_code<br/>no cross-host fallback"]
  Host --> Work["Isolated mission worktree<br/>attempt + lease, worker tests + commits"]
  Work --> Review["Exact-head read-only review<br/>required before integration"]
  Review -->|pass| Integrate["Serial integration into the resolved branch"]
  Review -->|fix_required| Work
  Integrate --> Gates["Integration, batch, E2E and UI evidence gates"]
  Gates -->|fix_required| Repair["Bounded repair route"]
  Repair --> Rereview["Re-review on the new head"]
  Rereview --> Gates
  Gates -->|pass| Local["Local verification complete"]
  Direct --> Local
  Local --> Remote{"push requested and authorized?"}
  Remote -->|no| Done["Stop with verified local evidence"]
  Remote -->|yes| Push["Push the run's own branch<br/>run ends here"]
  Push -.-> Yours["PR, merge, and deploy:<br/>your own steps, outside the Harness"]
```


## Lightweight runtime adapters

The shared core owns the one PLAN/RUN control plane. Runtime-specific launch details are loaded lazily:

- A Codex host loads only `fullstack-harness-codex` and executes only `codex`-provider PLAN nodes.
- A Claude Code host loads only `fullstack-harness-claude-code` and executes only `claude_code`-provider PLAN nodes.
- Neither adapter can invoke the other runtime. A ready node whose provider does not match the current host is reported blocked on provider mismatch and left for a run hosted by the matching adapter.

Shared scripts, schemas, references, and templates remain under `fullstack-harness-engineering`; adapters link to them rather than shipping duplicate runtimes. This keeps the default prompt small.

## Graph engineering and Dynamic Workflows

The skills use two graph layers:

- The **org graph** is the stable role contract: product, architecture, UX, design-system, mission-worker, reviewer, approval, integration, and lifecycle responsibilities.
- The **work graph** is the temporary task graph for one run. PRD and design workflows use bounded analysis graphs only when the host can enforce a `builder_readonly` tool profile; otherwise they fall back to the sequential parent. Engineering uses the canonical PLAN v5 graph and RUN v10 state.

Interviews and approvals stay outside running workflows because Claude Code Dynamic Workflows cannot ask for mid-run user input. The parent freezes inputs first, runs a bounded workflow, then owns staged writes, conflict resolution, approval, and publication.

For engineering, the Harness validates and selects the dependency-ready frontier before creating or requesting worktrees. Native Claude missions use parent-managed worktrees under `.claude/worktrees/`, bind every worker to the exact batch base, and require `EnterWorktree` before repository access. In every route, the parent validates the returned commit and actual Git diff, integrates accepted commits serially, and recomputes the graph frontier.

Claude waves are separated by model, reasoning effort, and tool profile:

- `mission_write` includes `EnterWorktree` and bounded write tools.
- `code_review_readonly` omits write-capable tools.
- `visual_review_readonly` uses the exact read/search allowlist and reviews retained screenshots or other existing evidence. New browser tools must be vetted and added to the profile before use.

When Claude Code returns real Workflow run IDs, RUN state may retain the workflow/task ID, script digest, node group, graph/base binding, tool profile, status, and available metrics. Same-session resume can use that binding; cross-session recovery starts a new workflow attempt from canonical PLAN/RUN state.

A graph node's `allowed_providers` must include the host that is actually running the Harness before that node can be selected. Claude Code cannot delegate a node to Codex, and Codex cannot delegate a node to Claude Code; there is no cross-host bridge. A ready node whose provider does not match the current host is recorded blocked on provider mismatch and left for a run hosted by the matching adapter.

## Install

This is a private GitHub marketplace. You need access to `Phlegonlabs/fullstack-goal-dev`, GitHub CLI authentication, and either Codex, Claude Code, or both.

```bash
gh auth login
gh auth setup-git
git ls-remote https://github.com/Phlegonlabs/fullstack-goal-dev.git HEAD
```

### Fastest setup

```powershell
git clone https://github.com/Phlegonlabs/fullstack-goal-dev.git
Set-Location .\fullstack-goal-dev
powershell -File .\scripts\update-private-skills.ps1
```

The clone only gives you the script. The updater always installs from GitHub — `Phlegonlabs/fullstack-goal-dev` at `main` by default — and never reads your working directory. Local edits are not installed this way; use [Use a local checkout during development](#use-a-local-checkout-during-development) for that.

Then open a new Codex task or reload Claude Code. Confirm the plugin is visible:

```powershell
codex plugin list
claude plugin list
```

### One-command updater

The shared updater detects installed runtimes, adds or updates the marketplace, and installs the plugin where supported. Re-run the same command when this repository changes.

Windows with PowerShell 7 (`pwsh`):

```powershell
Set-Location .\fullstack-goal-dev
pwsh -File .\scripts\update-private-skills.ps1
```

`pwsh` is a separate install. Windows PowerShell 5.1, which ships with Windows, also runs the script:

```powershell
Set-Location .\fullstack-goal-dev
powershell -File .\scripts\update-private-skills.ps1
```

macOS or Linux shell with PowerShell 7:

```bash
cd fullstack-goal-dev
pwsh -File ./scripts/update-private-skills.ps1
```

Open a new Codex task after updating. Reload or restart Claude Code after updating its plugin.

### Install directly in Codex

```bash
codex plugin marketplace add Phlegonlabs/fullstack-goal-dev --ref main
codex plugin add fullstack-harness@fullstack-goal-dev
codex plugin list
```

### Install directly in Claude Code

```bash
claude plugin marketplace add Phlegonlabs/fullstack-goal-dev --scope user
claude plugin install fullstack-harness@fullstack-goal-dev --scope user
claude plugin list
```

Run `/reload-plugins` or restart Claude Code once the plugin is installed.

### Use a local checkout during development

Use a local marketplace when testing changes in this repository. Do not register the local and GitHub marketplace under the same name at the same time.

```powershell
$repo = (Resolve-Path .).Path
codex plugin marketplace add $repo
codex plugin add fullstack-harness@fullstack-goal-dev
claude plugin marketplace add $repo --scope user
claude plugin install fullstack-harness@fullstack-goal-dev --scope user
```

## Typical prompts

Codex accepts the `$skill-name` form below. In Claude Code, invoke the installed namespaced skill, such as `/fullstack-harness:prd-builder`, or ask for it by name.

```text
Use $prd-builder to turn this idea into a PRD, architecture, stack decisions, and wireframes.
```

```text
Use $prd-builder to add the design system to docs/product/ from the existing PRD.md and wireframes.md.
```

```text
Use $fullstack-harness-engineering to review the existing app, plan the required work, and stop before implementation.
```

```text
Use $fullstack-harness-engineering to implement the approved plan. Create a branch and commit the verified change, but do not push or open a PR.
```

```text
Use $fullstack-harness-engineering to implement this plan and push the verified branch. I will open the PR and handle the merge myself.
```

For a multi-mission delivery, state the intended local and remote outcome. Branch creation, commits, integration, repository configuration, push, worktree removal, and branch deletion are independent actions. The Harness opens no pull request, merges nothing, and deploys nothing — those stay with you.

## Codex and Claude Code execution

The Harness records the actual runtime capability instead of assuming one from an installed CLI.

| Runtime | Preferred parallel route | Fallback |
| --- | --- | --- |
| Codex app (`fullstack-harness-codex`) | App tasks in isolated app-managed worktrees | Direct subagents, then one sequential parent |
| Claude Code (`fullstack-harness-claude-code`) | Dynamic workflow with exact-base parent-managed `.claude/worktrees/` worktrees | Direct subagents, then one sequential parent |

On Codex, the preferred route is two-level: each selected mission opens a separate top-level conversation in the left sidebar with its own app-managed worktree, then that task runs its own bounded Multi-agent helpers. Coordinator-owned subagents do not replace those top-level tasks. The adapter searches the current Codex tool surface for lazy-loaded project and thread tools before it uses a fallback. When the user explicitly requests this topology, missing thread capability is a blocker rather than permission to collapse the work back into one conversation.

Target-repository branch instructions take precedence. When a repository does not define another model, mission worktrees start from the current default-branch SHA, pass an exact-head read-only review before integration into the run's own branch, and the run ends when that verified branch is pushed. Landing it on the default branch is your own step. Fixes require a fresh review on the new head.

Each adapter runs only PLAN nodes whose allowed providers include its own host; there is no cross-host route. A node that requires the other host's provider is reported blocked on provider mismatch instead of being executed here.

Parallel implementation has no small fixed cap by default; the configured write-worker maximum is set generously high, and the effective wave is bounded by observed worker slots, isolation capacity, and the dependency-ready conflict-free frontier size instead. Every worker needs an isolated workspace, a bounded write scope, a verifier, and explicit authorization. Worktrees are allocated only after ready-frontier selection. Native Claude missions enter their assigned parent-managed worktree. Workers never edit the parent `PLAN.md` or `RUN.md`, push, open PRs, merge, deploy, or remove worktrees. The parent owns integration and every landing or lifecycle action.

## Repository layout

```text
.agents/skills/                                      Canonical skill sources
plugins/fullstack-harness/skills/                    Generated plugin copies; do not edit directly
plugins/fullstack-harness/.claude-plugin/plugin.json Claude Code plugin manifest
plugins/fullstack-harness/.codex-plugin/plugin.json  Codex plugin manifest
.agents/plugins/marketplace.json                     Codex marketplace definition
.claude-plugin/marketplace.json                      Claude Code marketplace definition
assets/                                              README covers
scripts/sync_plugin_skills.py                        Copies canonical skills into the plugin bundle
scripts/update-private-skills.ps1                    Updates installed marketplaces and plugin
.github/workflows/harness-ci.yml                     Contract, unit, and E2E checks
```

## Maintain the marketplace

Edit only the canonical sources in `.agents/skills/`, then sync and verify the generated plugin bundle.

```bash
python scripts/sync_plugin_skills.py
python scripts/sync_plugin_skills.py --check
python -m unittest discover -s .agents/skills/fullstack-harness-engineering/scripts/tests -v
python -m unittest discover -s .agents/skills/prd-builder/scripts/tests -v
python -m unittest discover -s plugins/fullstack-harness/skills/fullstack-harness-engineering/scripts/tests -p "test_packaged_*.py" -v
git diff --check
```

Before a release, update the matching version in both plugin manifests and `.claude-plugin/marketplace.json`, and inspect the entire diff. Do not push directly to `main`.

## Security and data safety

- Keep GitHub tokens and other credentials out of this repository.
- The updater uses your existing GitHub CLI session; it does not store a token in the project.
- Do not delete old standalone skill copies until the plugin is confirmed to load correctly.
- The orchestration skill requires explicit authorization for every state-changing Git or lifecycle action.

## Version history

Update this section with each release, alongside the version bump described above.

- **0.3.0** — Removed the GitHub landing adapter and the whole deployment/release model. The harness now ends at a push to the run's own branch; landing on the default branch is the user's own step. Authorization ledger cut from 19 actions to 12; `landing` reduced to `mode`, `remote`, `pushed_head_sha`, `continuity`; `integration.branch` is the only branch field. Dropped branch-protection evidence, `target_sources`, the three contract markers, `post_merge_cleanup`, `plan.release`, and `run.targets`.
- **0.2.0** — Worktree-per-mission default; PLAN v5 / RUN v10 typed graph with multi-reviewer fan-out; Cloudflare dispatched-deploy and Auto-Deploy (native Git auto-deploy) release models; persistent integration branches; per-page generic HTML prototypes replacing the retired page UI matrix; mobile/desktop platform support including a dedicated mobile stack-selection guide (native iOS/Android, Flutter, React Native/Expo); environment-secret scaffolding via `.env.example`; a Haiku cost tier for bounded/mechanical delegated work.

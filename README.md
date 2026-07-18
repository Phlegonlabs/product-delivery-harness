<p align="center">
  <img src="./assets/readme-banner.svg" alt="Full Stack Harness" width="100%">
</p>

<p align="center">
  <img alt="Private marketplace" src="https://img.shields.io/badge/marketplace-private-111827?style=flat-square">
  <img alt="Codex" src="https://img.shields.io/badge/Codex-supported-2563EB?style=flat-square">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude_Code-supported-D97706?style=flat-square">
  <img alt="Version" src="https://img.shields.io/badge/version-0.1.1-059669?style=flat-square">
</p>

# Full Stack Harness

Private skill marketplace for turning a product idea into a verified delivery flow with Codex or Claude Code.

It is not just a collection of prompts. The plugin separates product definition, visual design, and delivery orchestration so each stage has a clear source of truth and a safe handoff to the next.

## What is included

| Skill | Use it for | Main output |
| --- | --- | --- |
| `prd-builder` | Product discovery, requirements, architecture, frontend-stack decisions, and low-fidelity wireframes | `PRD.md`, `architecture.md`, `wireframes.md` |
| `design-package-builder` | Design direction, tokens, icon and motion rules, page specs, and visual acceptance | `design-system.md`, `page-ui-matrix.md`, `ui-mockups.md`, `visual-acceptance.md` |
| `fullstack-harness-engineering` | Traceable implementation planning, safe multi-agent execution, verification, and PR landing | Direct work, `RUN.md`, or `PLAN.md` + `RUN.md` |

The delivery skill makes one size decision before it invokes managed orchestration:

- Small work stays direct with no planner, scheduler, PLAN/RUN, subagent, or external-runtime preflight by default.
- Large work enters managed planning. It may use `RUN.md` for a sequential delivery or `PLAN.md` and `RUN.md` for multiple missions and durable handoff.
- Scheduler fan-out starts only when a large plan has at least two independent ready missions. External Claude is preflighted only when a selected route needs it.

Size means coordination scope and blast radius, not a raw file or line count. If small work grows, the Harness preserves completed work and plans only the remainder.

## How the system fits together

```mermaid
flowchart LR
  Idea["Product idea or change request"] --> PRD["prd-builder\nProduct and technical definition"]
  PRD --> Design["design-package-builder\nVisual system and page rules"]
  PRD --> Harness["fullstack-harness-engineering\nPlan, implement, verify, land"]
  Design --> Harness
  Harness --> Evidence["Tests, UI evidence, PR gates"]
```

You can start at any stage. For example, use the Harness alone to fix an existing app, or use the design skill when a PRD already exists. The skills keep their responsibilities separate: the PRD skill does not invent a design system, and the design skill does not write a delivery plan.

## Delivery model

The Harness is built around explicit boundaries:

1. Inspect the current project and identify the required work.
2. Freeze the relevant contracts, sources, scope, and verification steps.
3. Plan dependencies before starting implementation when the task is large enough to need it.
4. Use parallel workers only when the work is independent, isolated, and explicitly authorized.
5. Verify task results, integrations, UI journeys where relevant, and the final diff.
6. Land through the repository's PR flow only with separate authorization for each GitHub action.

For plan-backed work, it records task scope, dependencies, worker ownership, verification commands, and action-specific authorization. A passing test does not authorize a push, PR, review action, merge, deploy, or cleanup.

## Install

This is a private GitHub marketplace. You need access to `Phlegonlabs/fullstack-goal-dev`, GitHub CLI authentication, and either Codex, Claude Code, or both.

```bash
gh auth login
gh auth setup-git
git ls-remote https://github.com/Phlegonlabs/fullstack-goal-dev.git HEAD
```

### One-command updater

Clone the repository, then run the shared updater. It detects the installed runtimes, adds or updates the marketplace, and installs the plugin where supported.

Windows PowerShell:

```powershell
git clone https://github.com/Phlegonlabs/fullstack-goal-dev.git
Set-Location .\fullstack-goal-dev
pwsh -File .\scripts\update-private-skills.ps1
```

macOS or Linux shell with PowerShell 7:

```bash
git clone https://github.com/Phlegonlabs/fullstack-goal-dev.git
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

```text
Use $prd-builder to turn this idea into a PRD, architecture, and wireframes.
```

```text
Use $design-package-builder to create a design package from doc/PRD.md and doc/wireframes.md.
```

```text
Use $fullstack-harness-engineering to review the existing app, plan the required work, and stop before implementation.
```

```text
Use $fullstack-harness-engineering to implement the approved plan. Create a branch and commit the verified change, but do not push or open a PR.
```

For a multi-mission delivery, state the complete launch and landing permissions in the request. Branch creation, commits, integration, push, PR creation, review management, merge, deployment, and cleanup are independent actions.

## Codex and Claude Code execution

The Harness records the actual runtime capability instead of assuming one from an installed CLI.

| Runtime | Preferred parallel route | Fallback |
| --- | --- | --- |
| Codex app | App tasks in isolated app-managed worktrees | Direct subagents, then one sequential parent |
| Claude Code | Dynamic workflow with parent-managed worktrees | Direct subagents, then one sequential parent |

Parallel implementation is capped at three write missions by default. Every worker needs an isolated workspace, a bounded write scope, a verifier, and explicit authorization. Workers never edit the parent `PLAN.md` or `RUN.md`, push, open PRs, merge, deploy, or remove worktrees. The parent owns integration and every landing or lifecycle action.

## Repository layout

```text
.agents/skills/                   Canonical skill sources
plugins/fullstack-harness/skills/ Generated plugin copies; do not edit directly
.agents/plugins/marketplace.json  Codex marketplace definition
.claude-plugin/marketplace.json   Claude Code marketplace definition
scripts/sync_plugin_skills.py     Copies canonical skills into the plugin bundle
scripts/update-private-skills.ps1 Updates installed marketplaces and plugin
.github/workflows/harness-ci.yml  Contract, unit, and E2E checks
```

## Maintain the marketplace

Edit only the canonical sources in `.agents/skills/`, then sync and verify the generated plugin bundle.

```bash
python scripts/sync_plugin_skills.py
python scripts/sync_plugin_skills.py --check
python -m unittest discover -s .agents/skills/fullstack-harness-engineering/scripts/tests -v
python -m unittest discover -s .agents/skills/design-package-builder/scripts/tests -v
python -m unittest discover -s .agents/skills/prd-builder/scripts/tests -v
git diff --check
```

Before a release, update the matching version in both plugin manifests and `.claude-plugin/marketplace.json`, inspect the entire diff, and use the repository PR flow. Do not push directly to `main`.

## Security and data safety

- Keep GitHub tokens and other credentials out of this repository.
- The updater uses your existing GitHub CLI session; it does not store a token in the project.
- Do not delete old standalone skill copies until the plugin is confirmed to load correctly.
- The orchestration skill requires explicit authorization for every state-changing GitHub or lifecycle action.

---

## 繁體中文

### 這是什麼

Full Stack Harness 是給 Codex 與 Claude Code 使用的私有 skill marketplace。它把一個產品想法或既有系統改動，拆成三個可交接的階段：產品定義、視覺設計、以及可驗證的交付流程。

| Skill | 用途 | 主要產出 |
| --- | --- | --- |
| `prd-builder` | 產品需求、架構、前端技術選擇、低保真 wireframe | PRD、架構與 wireframe 文件 |
| `design-package-builder` | 視覺方向、設計系統、icon 與 motion 規範、頁面規格 | Design system、頁面規格、視覺驗收條件 |
| `fullstack-harness-engineering` | 既有系統盤點、實作規劃、多 agent 協作、驗證與 PR landing | 直接處理、`RUN.md`，或 `PLAN.md` + `RUN.md` |

你可以從任何一段開始：已有 PRD 就直接做設計；已有產品就用 Harness 做盤點、規劃或實作。

### 安裝與更新

需具備 `Phlegonlabs/fullstack-goal-dev` 的存取權限，並先登入 GitHub CLI：

```bash
gh auth login
gh auth setup-git
```

從 repository clone 後，在 Windows 或已安裝 PowerShell 7 的 macOS/Linux 執行：

```powershell
pwsh -File .\scripts\update-private-skills.ps1
```

Updater 會偵測 Codex 與 Claude Code，更新 marketplace 並安裝 plugin。Codex 更新後請開新的 task；Claude Code 則執行 `/reload-plugins` 或重新啟動。

### 使用方式

```text
Use $prd-builder to turn this idea into a PRD, architecture, and wireframes.
```

```text
Use $design-package-builder to create a design package from the current PRD and wireframes.
```

```text
Use $fullstack-harness-engineering to review the existing app, plan the work, and stop before implementation.
```

### 交付原則

Harness 會先把工作分成小項目或大項目。小項目直接處理，預設不啟動 planner、scheduler、PLAN/RUN、subagent 或外部 runtime preflight。大項目才進入 managed planning；只有存在兩個以上可獨立執行的 ready missions 時才啟動 scheduler。Claude bridge 也只會在選定的 route 確實需要 Claude 時 preflight。

大小看的是協調範圍與影響面，不是單純計算檔案數或程式碼行數。小項目途中變大時，Harness 會保留已完成的工作，只規劃剩餘範圍。

多 agent 寫入預設最多三個 mission，且每個 mission 都必須有獨立 worktree、限定寫入範圍、驗證指令與明確授權。Worker 絕不修改 parent 的 `PLAN.md` 或 `RUN.md`，也不執行 push、開 PR、merge、deploy 或清理；整合與所有 landing、lifecycle 動作只由 parent 負責。建立 branch、commit、整合、push、開 PR、管理 review、merge、deploy 與清理，都是分開的授權動作；測試通過不等於可以自動執行這些動作。

### 維護 repository

只修改 `.agents/skills/` 下的 canonical skills。`plugins/fullstack-harness/skills/` 是產生檔，使用以下命令同步與驗證：

```bash
python scripts/sync_plugin_skills.py
python scripts/sync_plugin_skills.py --check
python -m unittest discover -s .agents/skills/fullstack-harness-engineering/scripts/tests -v
git diff --check
```

版本發布前需同步更新兩份 plugin manifest 與 `.claude-plugin/marketplace.json` 的版本，跑完 CI 對應測試，並依 PR 流程合併。不要直接 push 到 `main`。

<p align="center">
  <img src="./assets/readme-banner.svg" alt="Full Stack Harness — private multi-runtime skill marketplace" width="100%">
</p>

<p align="center">
  <img alt="Private marketplace" src="https://img.shields.io/badge/marketplace-private-111827?style=flat-square">
  <img alt="Codex multi-thread" src="https://img.shields.io/badge/Codex-multi--thread-2563EB?style=flat-square">
  <img alt="Claude dynamic workflow" src="https://img.shields.io/badge/Claude-dynamic_workflow-D97706?style=flat-square">
  <img alt="Windows" src="https://img.shields.io/badge/Windows-PowerShell-7C3AED?style=flat-square">
  <img alt="macOS" src="https://img.shields.io/badge/macOS-zsh-334155?style=flat-square">
  <img alt="Plugin version" src="https://img.shields.io/badge/plugin-v0.1.0-059669?style=flat-square">
</p>

<p align="center">
  <strong>語言 / 语言：</strong>
  <a href="#繁體中文">繁體中文</a> ·
  <a href="#简体中文">简体中文</a>
</p>

---

<a id="繁體中文"></a>

# Full Stack Goal Dev（繁體中文）

> [繁體中文](#繁體中文) · [简体中文](#简体中文)

這是一個供 Codex 和 Claude Code 使用的私人 skill marketplace。一個 plugin 會安裝以下三個 skills：

- `fullstack-harness-engineering`
- `prd-builder`
- `design-package-builder`

Harness 會偵測目前使用的 runtime。Codex 會將平行工作路由到 multi-thread waves；Claude Code 則會路由到 dynamic workflow。

## 安裝需求

- 具備私人 GitHub repository `Phlegonlabs/fullstack-goal-dev` 的存取權限
- 已安裝 [GitHub CLI](https://cli.github.com/)，並使用 `gh auth login` 登入
- 已安裝 Codex CLI、Claude Code，或兩者皆已安裝
- 已使用 `gh auth setup-git` 設定 Git credential
- macOS 如要使用共用更新 script，需安裝 PowerShell 7（`pwsh`）

安裝前先確認 GitHub 存取權限：

```bash
gh auth status
git ls-remote https://github.com/Phlegonlabs/fullstack-goal-dev.git HEAD
```

## 在另一部裝置快速安裝

### Windows

在 PowerShell 執行：

```powershell
gh auth login
gh auth setup-git
git clone https://github.com/Phlegonlabs/fullstack-goal-dev.git
Set-Location .\fullstack-goal-dev
pwsh -File .\scripts\update-private-skills.ps1
```

如果沒有 `pwsh`，請安裝 PowerShell 7，或使用下方的 plugin 直接安裝指令。

### macOS

在 Terminal 執行：

```bash
gh auth login
gh auth setup-git
git clone https://github.com/Phlegonlabs/fullstack-goal-dev.git
cd fullstack-goal-dev
pwsh -File ./scripts/update-private-skills.ps1
```

可以使用 `brew install --cask powershell` 安裝 PowerShell，或不用 PowerShell，直接執行下方的 plugin 指令。

更新 script 會偵測已安裝的 runtimes、新增或重新整理 marketplace，並安裝或更新 plugin。第一次安裝後，請開啟新的 Codex task，並重新啟動 Claude Code。

## 直接安裝 plugin

以下指令在 Windows 和 macOS 相同。

### Codex

```bash
codex plugin marketplace add Phlegonlabs/fullstack-goal-dev --ref main
codex plugin add fullstack-harness@fullstack-goal-dev
codex plugin list
```

安裝後請開啟新的 Codex task，讓新 skills 載入。

### Claude Code

```bash
claude plugin marketplace add Phlegonlabs/fullstack-goal-dev --scope user
claude plugin install fullstack-harness@fullstack-goal-dev --scope user
claude plugin list
```

在 Claude Code 內執行 `/reload-plugins`，或重新啟動 Claude Code。

## 從本機 checkout 安裝

開發 plugin 時使用這種方式。Marketplace 會追蹤目前 checkout 的檔案，而不是私人 Git remote。

### Windows PowerShell

```powershell
$repo = (Resolve-Path .).Path
codex plugin marketplace add $repo
codex plugin add fullstack-harness@fullstack-goal-dev
claude plugin marketplace add $repo --scope user
claude plugin install fullstack-harness@fullstack-goal-dev --scope user
```

### macOS Terminal

```bash
codex plugin marketplace add "$PWD"
codex plugin add fullstack-harness@fullstack-goal-dev
claude plugin marketplace add "$PWD" --scope user
claude plugin install fullstack-harness@fullstack-goal-dev --scope user
```

不要同時使用名稱相同的本機 marketplace 和 Git marketplace。切換來源前，先透過相應 CLI 移除舊來源。

## 更新已安裝的 plugin

從最新的 repository clone 執行共用 updater：

```powershell
pwsh -File ./scripts/update-private-skills.ps1
```

也可以分別更新每個 runtime：

```bash
# Codex
codex plugin marketplace upgrade fullstack-goal-dev
codex plugin add fullstack-harness@fullstack-goal-dev

# Claude Code
claude plugin marketplace update fullstack-goal-dev
claude plugin update fullstack-harness@fullstack-goal-dev --scope user
```

## 自動更新

### Claude Code 啟動時更新

Claude Code 支援啟動時自動更新 marketplace。第三方 marketplace 不會預設開啟，請前往 `/plugin` → **Marketplaces** → **fullstack-goal-dev** → **Enable auto-update**。

也可以把以下設定合併到使用者設定檔：

- Windows：`%USERPROFILE%\.claude\settings.json`
- macOS：`~/.claude/settings.json`

```json
{
  "extraKnownMarketplaces": {
    "fullstack-goal-dev": {
      "source": {
        "source": "github",
        "repo": "Phlegonlabs/fullstack-goal-dev"
      },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "fullstack-harness@fullstack-goal-dev": true
  }
}
```

不要用這段內容覆蓋現有設定檔。只合併這些 keys，並保留其他設定。

背景存取私人 repository 時，啟動 Claude Code 的環境必須有 `GH_TOKEN` 或 `GITHUB_TOKEN`。不要把 token 儲存在這個 repository。若從 terminal 啟動 Claude Code，可以從已登入的 GitHub CLI session 取得 token：

```powershell
# Windows PowerShell profile
$env:GH_TOKEN = gh auth token
```

```bash
# macOS ~/.zshrc
export GH_TOKEN="$(gh auth token)"
```

目前行為可參考 [Claude Code marketplace 指南](https://code.claude.com/docs/en/plugin-marketplaces)和[自動更新指南](https://code.claude.com/docs/en/discover-plugins)。

### Codex 排程更新

Codex CLI 目前提供明確的 marketplace upgrade 和 plugin install 指令。若要無人值守更新，可以讓作業系統定時執行共用更新 script。

#### Windows Task Scheduler

將 `<repo>` 換成 repository 的絕對路徑：

```powershell
$action = New-ScheduledTaskAction `
  -Execute "pwsh.exe" `
  -Argument '-NoProfile -File "<repo>\scripts\update-private-skills.ps1"'
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask `
  -TaskName "Update Full Stack Harness Skills" `
  -Action $action `
  -Trigger $trigger `
  -Description "Refresh the private Codex and Claude Code skill marketplace"
```

#### macOS launchd

建立 `~/Library/LaunchAgents/com.phlegonlabs.fullstack-harness-update.plist`。使用 `pwd` 和 `command -v pwsh` 的結果替換 `<repo>` 與 `pwsh` 路徑：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.phlegonlabs.fullstack-harness-update</string>
  <key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/pwsh</string>
    <string>-NoProfile</string>
    <string>-File</string>
    <string>&lt;repo&gt;/scripts/update-private-skills.ps1</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/fullstack-harness-update.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/fullstack-harness-update-error.log</string>
</dict>
</plist>
```

載入一次：

```bash
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.phlegonlabs.fullstack-harness-update.plist
```

## Windows 與 macOS 的差異

| 項目 | Windows | macOS |
| --- | --- | --- |
| 預設 shell | PowerShell | zsh |
| Repository 路徑 | `C:\path\fullstack-goal-dev` | `/Users/name/path/fullstack-goal-dev` |
| 共用 updater | `pwsh -File .\scripts\update-private-skills.ps1` | `pwsh -File ./scripts/update-private-skills.ps1` |
| 發布時的 Python 指令 | 通常是 `python` | 通常是 `python3` |
| Git credentials | Git Credential Manager / `gh auth setup-git` | Keychain / `gh auth setup-git` |
| 排程更新 | Task Scheduler | launchd |
| Claude 設定檔 | `%USERPROFILE%\.claude\settings.json` | `~/.claude/settings.json` |

Plugin 名稱、marketplace 名稱、版本，以及 Codex/Claude CLI 指令在兩個平台上相同。

## 發布 skill 更新

Canonical skills 位於 `.agents/skills`。不要直接修改自動產生的 plugin copies。

```bash
# Windows 通常使用 python；macOS 沒有 python 時使用 python3。
python scripts/sync_plugin_skills.py
python scripts/sync_plugin_skills.py --check
python -m unittest discover -s .agents/skills/fullstack-harness-engineering/scripts/tests -v
```

開 pull request 前：

1. 同時更新兩份 plugin manifests 和 `.claude-plugin/marketplace.json` 的版本。
2. 執行所有 contract tests 和 E2E tests。
3. 執行 `git diff --check`。
4. 透過 repository 的 pull request 流程 merge。

其他裝置會在下一次手動或排程更新時收到新版本。

## 疑難排解

### 無法驗證私人 repository

```bash
gh auth status
gh auth setup-git
git ls-remote https://github.com/Phlegonlabs/fullstack-goal-dev.git HEAD
```

### Marketplace 已存在，但指向錯誤來源

```bash
codex plugin marketplace list --json
claude plugin marketplace list --json
```

透過相應 CLI 移除舊 marketplace，再加入正確的本機或 Git 來源。移除 Claude marketplace 也會移除從該來源安裝的 plugins。

### 找不到 skills

- Codex：開啟新的 task。
- Claude Code：執行 `/reload-plugins` 或重新啟動 Claude Code。
- 使用 `codex plugin list --json` 或 `claude plugin list --json`，確認 `fullstack-harness@fullstack-goal-dev` 已啟用。
- `~/.codex/skills`、`~/.agents/skills` 或 `~/.claude/skills` 下的舊 standalone copies 可能造成 skill 名稱重複。在確認 plugin 版本正常前，不要刪除它們。

<p align="right"><a href="#繁體中文">返回繁體中文版頂部</a> · <a href="#简体中文">切換到简体中文</a></p>

---

<a id="简体中文"></a>

# Full Stack Goal Dev（简体中文）

> [繁體中文](#繁體中文) · [简体中文](#简体中文)

这是一个供 Codex 和 Claude Code 使用的私有 skill marketplace。一个 plugin 会安装以下三个 skills：

- `fullstack-harness-engineering`
- `prd-builder`
- `design-package-builder`

Harness 会检测当前使用的 runtime。Codex 会将并行工作路由到 multi-thread waves；Claude Code 则会路由到 dynamic workflow。

## 安装要求

- 具备私有 GitHub repository `Phlegonlabs/fullstack-goal-dev` 的访问权限
- 已安装 [GitHub CLI](https://cli.github.com/)，并使用 `gh auth login` 登录
- 已安装 Codex CLI、Claude Code，或两者都已安装
- 已使用 `gh auth setup-git` 设置 Git credential
- macOS 如需使用共用更新 script，需安装 PowerShell 7（`pwsh`）

安装前先确认 GitHub 访问权限：

```bash
gh auth status
git ls-remote https://github.com/Phlegonlabs/fullstack-goal-dev.git HEAD
```

## 在另一台设备快速安装

### Windows

在 PowerShell 中运行：

```powershell
gh auth login
gh auth setup-git
git clone https://github.com/Phlegonlabs/fullstack-goal-dev.git
Set-Location .\fullstack-goal-dev
pwsh -File .\scripts\update-private-skills.ps1
```

如果没有 `pwsh`，请安装 PowerShell 7，或使用下方的 plugin 直接安装命令。

### macOS

在 Terminal 中运行：

```bash
gh auth login
gh auth setup-git
git clone https://github.com/Phlegonlabs/fullstack-goal-dev.git
cd fullstack-goal-dev
pwsh -File ./scripts/update-private-skills.ps1
```

可以使用 `brew install --cask powershell` 安装 PowerShell，或不用 PowerShell，直接执行下方的 plugin 命令。

更新 script 会检测已安装的 runtimes、添加或刷新 marketplace，并安装或更新 plugin。首次安装后，请打开新的 Codex task，并重启 Claude Code。

## 直接安装 plugin

以下命令在 Windows 和 macOS 上相同。

### Codex

```bash
codex plugin marketplace add Phlegonlabs/fullstack-goal-dev --ref main
codex plugin add fullstack-harness@fullstack-goal-dev
codex plugin list
```

安装后请打开新的 Codex task，让新 skills 加载。

### Claude Code

```bash
claude plugin marketplace add Phlegonlabs/fullstack-goal-dev --scope user
claude plugin install fullstack-harness@fullstack-goal-dev --scope user
claude plugin list
```

在 Claude Code 中运行 `/reload-plugins`，或重启 Claude Code。

## 从本地 checkout 安装

开发 plugin 时使用这种方式。Marketplace 会跟踪当前 checkout 的文件，而不是私有 Git remote。

### Windows PowerShell

```powershell
$repo = (Resolve-Path .).Path
codex plugin marketplace add $repo
codex plugin add fullstack-harness@fullstack-goal-dev
claude plugin marketplace add $repo --scope user
claude plugin install fullstack-harness@fullstack-goal-dev --scope user
```

### macOS Terminal

```bash
codex plugin marketplace add "$PWD"
codex plugin add fullstack-harness@fullstack-goal-dev
claude plugin marketplace add "$PWD" --scope user
claude plugin install fullstack-harness@fullstack-goal-dev --scope user
```

不要同时使用名称相同的本地 marketplace 和 Git marketplace。切换来源前，先通过相应 CLI 移除旧来源。

## 更新已安装的 plugin

从最新的 repository clone 运行共用 updater：

```powershell
pwsh -File ./scripts/update-private-skills.ps1
```

也可以分别更新每个 runtime：

```bash
# Codex
codex plugin marketplace upgrade fullstack-goal-dev
codex plugin add fullstack-harness@fullstack-goal-dev

# Claude Code
claude plugin marketplace update fullstack-goal-dev
claude plugin update fullstack-harness@fullstack-goal-dev --scope user
```

## 自动更新

### Claude Code 启动时更新

Claude Code 支持启动时自动更新 marketplace。第三方 marketplace 不会默认开启，请前往 `/plugin` → **Marketplaces** → **fullstack-goal-dev** → **Enable auto-update**。

也可以把以下设置合并到用户设置文件：

- Windows：`%USERPROFILE%\.claude\settings.json`
- macOS：`~/.claude/settings.json`

```json
{
  "extraKnownMarketplaces": {
    "fullstack-goal-dev": {
      "source": {
        "source": "github",
        "repo": "Phlegonlabs/fullstack-goal-dev"
      },
      "autoUpdate": true
    }
  },
  "enabledPlugins": {
    "fullstack-harness@fullstack-goal-dev": true
  }
}
```

不要用这段内容覆盖现有设置文件。只合并这些 keys，并保留其他设置。

后台访问私有 repository 时，启动 Claude Code 的环境必须有 `GH_TOKEN` 或 `GITHUB_TOKEN`。不要把 token 存储在这个 repository 中。如果从 terminal 启动 Claude Code，可以从已登录的 GitHub CLI session 获取 token：

```powershell
# Windows PowerShell profile
$env:GH_TOKEN = gh auth token
```

```bash
# macOS ~/.zshrc
export GH_TOKEN="$(gh auth token)"
```

当前行为可参考 [Claude Code marketplace 指南](https://code.claude.com/docs/en/plugin-marketplaces)和[自动更新指南](https://code.claude.com/docs/en/discover-plugins)。

### Codex 定时更新

Codex CLI 目前提供明确的 marketplace upgrade 和 plugin install 命令。如需无人值守更新，可以让操作系统定时执行共用更新 script。

#### Windows Task Scheduler

将 `<repo>` 替换为 repository 的绝对路径：

```powershell
$action = New-ScheduledTaskAction `
  -Execute "pwsh.exe" `
  -Argument '-NoProfile -File "<repo>\scripts\update-private-skills.ps1"'
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask `
  -TaskName "Update Full Stack Harness Skills" `
  -Action $action `
  -Trigger $trigger `
  -Description "Refresh the private Codex and Claude Code skill marketplace"
```

#### macOS launchd

创建 `~/Library/LaunchAgents/com.phlegonlabs.fullstack-harness-update.plist`。使用 `pwd` 和 `command -v pwsh` 的结果替换 `<repo>` 和 `pwsh` 路径：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.phlegonlabs.fullstack-harness-update</string>
  <key>ProgramArguments</key>
  <array>
    <string>/opt/homebrew/bin/pwsh</string>
    <string>-NoProfile</string>
    <string>-File</string>
    <string>&lt;repo&gt;/scripts/update-private-skills.ps1</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/fullstack-harness-update.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/fullstack-harness-update-error.log</string>
</dict>
</plist>
```

加载一次：

```bash
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.phlegonlabs.fullstack-harness-update.plist
```

## Windows 与 macOS 的区别

| 项目 | Windows | macOS |
| --- | --- | --- |
| 默认 shell | PowerShell | zsh |
| Repository 路径 | `C:\path\fullstack-goal-dev` | `/Users/name/path/fullstack-goal-dev` |
| 共用 updater | `pwsh -File .\scripts\update-private-skills.ps1` | `pwsh -File ./scripts/update-private-skills.ps1` |
| 发布时的 Python 命令 | 通常是 `python` | 通常是 `python3` |
| Git credentials | Git Credential Manager / `gh auth setup-git` | Keychain / `gh auth setup-git` |
| 定时更新 | Task Scheduler | launchd |
| Claude 设置文件 | `%USERPROFILE%\.claude\settings.json` | `~/.claude/settings.json` |

Plugin 名称、marketplace 名称、版本，以及 Codex/Claude CLI 命令在两个平台上相同。

## 发布 skill 更新

Canonical skills 位于 `.agents/skills`。不要直接修改自动生成的 plugin copies。

```bash
# Windows 通常使用 python；macOS 没有 python 时使用 python3。
python scripts/sync_plugin_skills.py
python scripts/sync_plugin_skills.py --check
python -m unittest discover -s .agents/skills/fullstack-harness-engineering/scripts/tests -v
```

打开 pull request 前：

1. 同时更新两份 plugin manifests 和 `.claude-plugin/marketplace.json` 的版本。
2. 运行所有 contract tests 和 E2E tests。
3. 运行 `git diff --check`。
4. 通过 repository 的 pull request 流程 merge。

其他设备会在下一次手动或定时更新时收到新版本。

## 故障排查

### 无法验证私有 repository

```bash
gh auth status
gh auth setup-git
git ls-remote https://github.com/Phlegonlabs/fullstack-goal-dev.git HEAD
```

### Marketplace 已存在，但指向错误来源

```bash
codex plugin marketplace list --json
claude plugin marketplace list --json
```

通过相应 CLI 移除旧 marketplace，再添加正确的本地或 Git 来源。移除 Claude marketplace 也会移除从该来源安装的 plugins。

### 找不到 skills

- Codex：打开新的 task。
- Claude Code：运行 `/reload-plugins` 或重启 Claude Code。
- 使用 `codex plugin list --json` 或 `claude plugin list --json`，确认 `fullstack-harness@fullstack-goal-dev` 已启用。
- `~/.codex/skills`、`~/.agents/skills` 或 `~/.claude/skills` 下的旧 standalone copies 可能造成 skill 名称重复。在确认 plugin 版本正常前，不要删除它们。

<p align="right"><a href="#简体中文">返回简体中文版顶部</a> · <a href="#繁體中文">切換到繁體中文</a></p>

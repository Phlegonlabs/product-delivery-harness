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

# Full Stack Goal Dev

Private skill marketplace for Codex and Claude Code. One plugin installs these three skills:

- `fullstack-harness-engineering`
- `prd-builder`
- `design-package-builder`

The harness detects the active runtime. Codex routes parallel work through multi-thread waves; Claude Code routes it through a dynamic workflow.

## Requirements

- Access to the private `Phlegonlabs/fullstack-goal-dev` GitHub repository
- [GitHub CLI](https://cli.github.com/) authenticated with `gh auth login`
- Codex CLI, Claude Code, or both
- Git credential access configured with `gh auth setup-git`
- PowerShell 7 (`pwsh`) only if you want to use the shared update script on macOS

Verify GitHub access before installing:

```bash
gh auth status
git ls-remote https://github.com/Phlegonlabs/fullstack-goal-dev.git HEAD
```

## Quick install on another device

### Windows

Run in PowerShell:

```powershell
gh auth login
gh auth setup-git
git clone https://github.com/Phlegonlabs/fullstack-goal-dev.git
Set-Location .\fullstack-goal-dev
pwsh -File .\scripts\update-private-skills.ps1
```

If `pwsh` is unavailable, install PowerShell 7 or use the direct plugin commands below.

### macOS

Run in Terminal:

```bash
gh auth login
gh auth setup-git
git clone https://github.com/Phlegonlabs/fullstack-goal-dev.git
cd fullstack-goal-dev
pwsh -File ./scripts/update-private-skills.ps1
```

Install PowerShell with `brew install --cask powershell`, or use the direct plugin commands without PowerShell.

The update script detects which runtimes are installed, adds or refreshes the marketplace, and installs or updates the plugin. Start a new Codex task and restart Claude Code after the first install.

## Direct plugin installation

These commands are the same on Windows and macOS.

### Codex

```bash
codex plugin marketplace add Phlegonlabs/fullstack-goal-dev --ref main
codex plugin add fullstack-harness@fullstack-goal-dev
codex plugin list
```

Open a new Codex task after installation so the new skills are loaded.

### Claude Code

```bash
claude plugin marketplace add Phlegonlabs/fullstack-goal-dev --scope user
claude plugin install fullstack-harness@fullstack-goal-dev --scope user
claude plugin list
```

Inside Claude Code, run `/reload-plugins` or restart Claude Code.

## Install from a local checkout

Use this during plugin development. The marketplace tracks the checked-out files instead of the private Git remote.

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

Do not mix a local marketplace and a Git marketplace with the same marketplace name. Remove the old source before switching.

## Update the installed plugin

Run the shared updater from a current clone:

```powershell
pwsh -File ./scripts/update-private-skills.ps1
```

Or update each runtime directly:

```bash
# Codex
codex plugin marketplace upgrade fullstack-goal-dev
codex plugin add fullstack-harness@fullstack-goal-dev

# Claude Code
claude plugin marketplace update fullstack-goal-dev
claude plugin update fullstack-harness@fullstack-goal-dev --scope user
```

## Automatic updates

### Claude Code startup updates

Claude Code supports marketplace auto-update at startup. Third-party marketplaces are not enabled automatically, so enable it in `/plugin` → **Marketplaces** → **fullstack-goal-dev** → **Enable auto-update**.

For a settings-based setup, merge this into the user settings file:

- Windows: `%USERPROFILE%\.claude\settings.json`
- macOS: `~/.claude/settings.json`

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

Do not replace an existing settings file with this snippet. Merge these keys and preserve the other settings.

Background access to a private repository requires `GH_TOKEN` or `GITHUB_TOKEN` in the environment that launches Claude Code. Avoid storing the token in this repository. If Claude Code is launched from a terminal, you can obtain the token from the authenticated GitHub CLI session:

```powershell
# Windows PowerShell profile
$env:GH_TOKEN = gh auth token
```

```bash
# macOS ~/.zshrc
export GH_TOKEN="$(gh auth token)"
```

See the [Claude Code marketplace guide](https://code.claude.com/docs/en/plugin-marketplaces) and [auto-update guide](https://code.claude.com/docs/en/discover-plugins) for the current behavior.

### Codex scheduled updates

The current Codex CLI exposes explicit marketplace upgrade and plugin install commands. Use the shared update script in an operating-system schedule for unattended updates.

#### Windows Task Scheduler

Replace `<repo>` with the absolute repository path:

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

Create `~/Library/LaunchAgents/com.phlegonlabs.fullstack-harness-update.plist`. Replace `<repo>` and the `pwsh` path with values from `pwd` and `command -v pwsh`:

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

Load it once:

```bash
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.phlegonlabs.fullstack-harness-update.plist
```

## Windows and macOS differences

| Area | Windows | macOS |
| --- | --- | --- |
| Default shell | PowerShell | zsh |
| Repository path | `C:\path\fullstack-goal-dev` | `/Users/name/path/fullstack-goal-dev` |
| Shared updater | `pwsh -File .\scripts\update-private-skills.ps1` | `pwsh -File ./scripts/update-private-skills.ps1` |
| Python command for publishing | Usually `python` | Usually `python3` |
| Git credentials | Git Credential Manager / `gh auth setup-git` | Keychain / `gh auth setup-git` |
| Scheduled updates | Task Scheduler | launchd |
| Claude settings | `%USERPROFILE%\.claude\settings.json` | `~/.claude/settings.json` |

The plugin names, marketplace names, version, and Codex/Claude CLI commands do not change between platforms.

## Publish a skill update

The canonical skills live under `.agents/skills`. Do not edit the generated plugin copies directly.

```bash
# Windows: use python. macOS: use python3 if python is unavailable.
python scripts/sync_plugin_skills.py
python scripts/sync_plugin_skills.py --check
python -m unittest discover -s .agents/skills/fullstack-harness-engineering/scripts/tests -v
```

Before opening a pull request:

1. Bump the version in both plugin manifests and `.claude-plugin/marketplace.json`.
2. Run all contract and E2E tests.
3. Run `git diff --check`.
4. Merge through the repository pull request flow.

Other devices receive the new version through their next manual or scheduled update.

## Troubleshooting

### Private repository authentication fails

```bash
gh auth status
gh auth setup-git
git ls-remote https://github.com/Phlegonlabs/fullstack-goal-dev.git HEAD
```

### Marketplace exists but points to the wrong source

```bash
codex plugin marketplace list --json
claude plugin marketplace list --json
```

Remove the old marketplace through its CLI, then add the intended local or Git source again. Removing a Claude marketplace also removes plugins installed from it.

### Skills do not appear

- Codex: start a new task.
- Claude Code: run `/reload-plugins` or restart Claude Code.
- Confirm `fullstack-harness@fullstack-goal-dev` is enabled with `codex plugin list --json` or `claude plugin list --json`.
- Older standalone copies under `~/.codex/skills`, `~/.agents/skills`, or `~/.claude/skills` can create duplicate skill names. Do not delete them until you have confirmed the plugin version works.

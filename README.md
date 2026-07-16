# Full Stack Goal Dev

Private skill marketplace for Codex and Claude Code. The same plugin contains:

- `fullstack-harness-engineering`
- `prd-builder`
- `design-package-builder`

## Set up another device

Sign in to GitHub first so Git can read this private repository. Then clone the repository and run:

```powershell
pwsh -File .\scripts\update-private-skills.ps1
```

The script adds or refreshes the private marketplace and installs the plugin for every supported runtime found on the device. Restart Codex or Claude Code after an update.

## Publish a skill update

Edit the canonical copies under `.agents/skills`, then run:

```powershell
python .\scripts\sync_plugin_skills.py
python .\scripts\sync_plugin_skills.py --check
python -m unittest discover -s .agents/skills/fullstack-harness-engineering/scripts/tests -v
```

Bump the plugin version in both plugin manifests and in `.claude-plugin/marketplace.json`. Commit through the normal pull request flow. Other devices receive the update the next time they run `update-private-skills.ps1`.

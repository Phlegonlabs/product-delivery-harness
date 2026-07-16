param(
    [string]$Repository = "Phlegonlabs/fullstack-goal-dev",
    [string]$Ref = "main"
)

$ErrorActionPreference = "Stop"
$Marketplace = "fullstack-goal-dev"
$Plugin = "fullstack-harness"
$PluginSelector = "$Plugin@$Marketplace"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Command failed with exit code $LASTEXITCODE."
    }
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is required to access the private repository."
}
Invoke-Checked gh auth status

if (Get-Command codex -ErrorAction SilentlyContinue) {
    $codexMarketplaces = (Invoke-Checked codex plugin marketplace list --json | ConvertFrom-Json).marketplaces
    if ($codexMarketplaces.name -contains $Marketplace) {
        Invoke-Checked codex plugin marketplace upgrade $Marketplace
    }
    else {
        Invoke-Checked codex plugin marketplace add $Repository --ref $Ref
    }
    Invoke-Checked codex plugin add $PluginSelector
}
else {
    Write-Warning "Codex CLI was not found. Skipping Codex."
}

if (Get-Command claude -ErrorAction SilentlyContinue) {
    $claudeMarketplaces = Invoke-Checked claude plugin marketplace list --json | ConvertFrom-Json
    if ($claudeMarketplaces.name -contains $Marketplace) {
        Invoke-Checked claude plugin marketplace update $Marketplace
    }
    else {
        Invoke-Checked claude plugin marketplace add $Repository --scope user
    }

    $installedPlugins = Invoke-Checked claude plugin list --json | ConvertFrom-Json
    if ($installedPlugins.id -contains $PluginSelector) {
        Invoke-Checked claude plugin update $PluginSelector --scope user
    }
    else {
        Invoke-Checked claude plugin install $PluginSelector --scope user
    }
}
else {
    Write-Warning "Claude CLI was not found. Skipping Claude Code."
}

Write-Host "Private skills are current. Restart each runtime that was updated."

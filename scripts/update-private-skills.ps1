param(
    [string]$Repository = "Phlegonlabs/fullstack-goal-dev",
    [string]$Ref = "main",
    [switch]$UpdateHostRuntimes,
    [switch]$ReplacePiStandaloneSkills
)

$ErrorActionPreference = "Stop"
$Marketplace = "fullstack-goal-dev"
$Plugin = "fullstack-harness"
$PluginSelector = "$Plugin@$Marketplace"
$PiSource = if ([string]::IsNullOrWhiteSpace($Ref)) {
    "git:github.com/$Repository"
}
else {
    "git:github.com/$Repository@$Ref"
}
$ClaudeMarketplaceSource = if ([string]::IsNullOrWhiteSpace($Ref)) {
    $Repository
}
else {
    "https://github.com/$Repository.git#$Ref"
}

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

function Get-JsonItems {
    param(
        $Payload,
        [Parameter(Mandatory = $true)][string]$WrapperProperty
    )

    if ($null -eq $Payload) {
        return @()
    }
    if ($Payload.PSObject.Properties.Name -contains $WrapperProperty) {
        return @($Payload.$WrapperProperty)
    }
    return @($Payload)
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is required to access the private repository."
}
Invoke-Checked gh auth status

if ($UpdateHostRuntimes) {
    if (Get-Command codex -ErrorAction SilentlyContinue) {
        Invoke-Checked codex update
    }
    if (Get-Command claude -ErrorAction SilentlyContinue) {
        Invoke-Checked claude update
    }
    if (Get-Command pi -ErrorAction SilentlyContinue) {
        Invoke-Checked pi update --self --no-approve
    }
}

if (Get-Command codex -ErrorAction SilentlyContinue) {
    $codexMarketplaces = Get-JsonItems (Invoke-Checked codex plugin marketplace list --json | ConvertFrom-Json) "marketplaces"
    if ($codexMarketplaces.name -contains $Marketplace) {
        $codexMarketplace = @($codexMarketplaces | Where-Object { $_.name -eq $Marketplace })[0]
        if ($null -ne $codexMarketplace.marketplaceSource) {
            Invoke-Checked codex plugin marketplace upgrade $Marketplace
        }
        else {
            Write-Host "Codex marketplace is local; using its current checkout."
        }
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
    $claudeMarketplaces = Get-JsonItems (Invoke-Checked claude plugin marketplace list --json | ConvertFrom-Json) "marketplaces"
    if ($claudeMarketplaces.name -contains $Marketplace) {
        $claudeMarketplace = @($claudeMarketplaces | Where-Object { $_.name -eq $Marketplace })[0]
        if ($claudeMarketplace.source -eq "directory") {
            Write-Host "Claude marketplace is local; using its current checkout."
        }
        else {
            Invoke-Checked claude plugin marketplace update $Marketplace
        }
    }
    else {
        Invoke-Checked claude plugin marketplace add $ClaudeMarketplaceSource --scope user
    }

    $installedPlugins = Get-JsonItems (Invoke-Checked claude plugin list --json | ConvertFrom-Json) "plugins"
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

if (Get-Command pi -ErrorAction SilentlyContinue) {
    $piPackageLines = @(Invoke-Checked pi list --no-approve)
    $piPackageText = $piPackageLines -join "`n"
    $piIdentity = "git:github.com/$Repository"
    if ($piPackageText.Contains($piIdentity)) {
        Invoke-Checked pi update --extension $PiSource --no-approve
    }
    else {
        Invoke-Checked pi install $PiSource --no-approve
        $piPackageLines = @(Invoke-Checked pi list --no-approve)
        $piPackageText = $piPackageLines -join "`n"
    }

    $piAgentDir = if ([string]::IsNullOrWhiteSpace($env:PI_CODING_AGENT_DIR)) {
        Join-Path ([Environment]::GetFolderPath("UserProfile")) ".pi/agent"
    }
    else {
        $env:PI_CODING_AGENT_DIR
    }
    $piSkillsDir = Join-Path $piAgentDir "skills"
    $harnessSkills = @(
        "fullstack-harness-claude-code",
        "fullstack-harness-codex",
        "fullstack-harness-engineering",
        "fullstack-harness-pi",
        "manage-cloudflare-worker-deployments",
        "prd-builder",
        "product-design-builder"
    )
    $standaloneSkills = @(
        $harnessSkills | Where-Object {
            Test-Path -LiteralPath (Join-Path $piSkillsDir $_)
        }
    )

    if ($standaloneSkills.Count -gt 0 -and -not $ReplacePiStandaloneSkills) {
        Write-Warning (
            "Standalone Pi Harness skills can shadow the updated package and were left unchanged: " +
            ($standaloneSkills -join ", ") +
            ". Re-run with -ReplacePiStandaloneSkills to back them up and replace only those skill directories."
        )
    }
    elseif ($standaloneSkills.Count -gt 0) {
        $sourceIndex = -1
        for ($index = 0; $index -lt $piPackageLines.Count; $index++) {
            if ($piPackageLines[$index].Trim().StartsWith($piIdentity, [System.StringComparison]::OrdinalIgnoreCase)) {
                $sourceIndex = $index
                break
            }
        }
        if ($sourceIndex -lt 0 -or $sourceIndex + 1 -ge $piPackageLines.Count) {
            throw "Could not resolve the installed Pi package path for $PiSource."
        }
        $piPackagePath = $piPackageLines[$sourceIndex + 1].Trim()
        $piPackageSkills = Join-Path $piPackagePath ".agents/skills"
        if (-not (Test-Path -LiteralPath $piPackageSkills -PathType Container)) {
            throw "Installed Pi package has no canonical skill directory: $piPackageSkills"
        }

        $resolvedAgentDir = [System.IO.Path]::GetFullPath($piAgentDir)
        $resolvedSkillsDir = [System.IO.Path]::GetFullPath($piSkillsDir)
        if (-not $resolvedSkillsDir.StartsWith($resolvedAgentDir, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing Pi migration outside the configured agent directory: $resolvedSkillsDir"
        }
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $backupRoot = Join-Path $piAgentDir "skill-backups/fullstack-harness-$timestamp"
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

        foreach ($skillName in $standaloneSkills) {
            $sourceSkill = Join-Path $piPackageSkills $skillName
            if (-not (Test-Path -LiteralPath (Join-Path $sourceSkill "SKILL.md") -PathType Leaf)) {
                throw "Installed Pi package is missing $skillName/SKILL.md."
            }
        }

        # Copy first, then swap. Moving the live skill out and only then copying
        # the replacement in leaves the skill missing if the copy fails, and a
        # recursive copy is a realistic failure point on Windows: a long path
        # under scripts/tests/fixtures, or a file locked by a running Pi
        # session. Staging every replacement before touching anything live
        # reduces the dangerous window to a rename, and a failed rename rolls
        # the already-swapped skills back.
        $staged = @()
        try {
            foreach ($skillName in $standaloneSkills) {
                $sourceSkill = Join-Path $piPackageSkills $skillName
                $stagedSkill = Join-Path $piSkillsDir "$skillName.incoming-$timestamp"
                if (Test-Path -LiteralPath $stagedSkill) {
                    Remove-Item -LiteralPath $stagedSkill -Recurse -Force
                }
                Copy-Item -LiteralPath $sourceSkill -Destination $stagedSkill -Recurse
                $staged += [pscustomobject]@{ Name = $skillName; Path = $stagedSkill }
            }
        }
        catch {
            foreach ($item in $staged) {
                try { Remove-Item -LiteralPath $item.Path -Recurse -Force } catch {}
            }
            throw "Staging the replacement skills failed; nothing was changed. $_"
        }

        $swapped = @()
        try {
            foreach ($item in $staged) {
                $destinationSkill = Join-Path $piSkillsDir $item.Name
                $backupSkill = Join-Path $backupRoot $item.Name
                Move-Item -LiteralPath $destinationSkill -Destination $backupSkill
                Move-Item -LiteralPath $item.Path -Destination $destinationSkill
                $swapped += [pscustomobject]@{ Name = $item.Name; Backup = $backupSkill; Live = $destinationSkill }
            }
        }
        catch {
            foreach ($item in $swapped) {
                try {
                    if (Test-Path -LiteralPath $item.Live) {
                        Remove-Item -LiteralPath $item.Live -Recurse -Force
                    }
                    Move-Item -LiteralPath $item.Backup -Destination $item.Live
                }
                catch {
                    Write-Warning "Could not restore $($item.Name); it remains at $($item.Backup)."
                }
            }
            foreach ($item in $staged) {
                try {
                    if (Test-Path -LiteralPath $item.Path) {
                        Remove-Item -LiteralPath $item.Path -Recurse -Force
                    }
                }
                catch {}
            }
            throw "Replacing the standalone skills failed and the previous ones were restored. $_"
        }
        Write-Host "Replaced standalone Pi Harness skills. Backup: $backupRoot"
    }
}
else {
    Write-Warning "Pi CLI was not found. Skipping Pi."
}

Write-Host "Private skills are current. Restart each runtime that was updated."

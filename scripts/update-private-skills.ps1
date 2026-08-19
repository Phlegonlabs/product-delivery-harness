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

    # Reinstall rather than update. `claude plugin update` compares the
    # plugin.json version and reports "already at the latest version" when it
    # matches, so any change that ships new skill content without bumping that
    # version leaves the cached copy stale while the command reports success.
    # That is the worst kind of stale: silent, and indistinguishable from
    # up to date. Codex avoids it only because `plugin add` reinstalls; do the
    # same here instead of relying on the version string being maintained.
    # `claude plugin install` is a no-op when the plugin is already installed,
    # so forcing a refetch means uninstalling first. That opens a window where a
    # failed install leaves no plugin at all, which the plain `update` path
    # never did -- so retry once and, if it still fails, say plainly that the
    # plugin is now absent and how to put it back.
    $installedPlugins = Get-JsonItems (Invoke-Checked claude plugin list --json | ConvertFrom-Json) "plugins"
    if ($installedPlugins.id -contains $PluginSelector) {
        Invoke-Checked claude plugin uninstall $PluginSelector --scope user
    }
    try {
        Invoke-Checked claude plugin install $PluginSelector --scope user
    }
    catch {
        Write-Warning "Installing $PluginSelector failed; retrying once."
        try {
            Invoke-Checked claude plugin install $PluginSelector --scope user
        }
        catch {
            throw ("Claude plugin $PluginSelector is currently NOT installed: it was uninstalled to force a refetch and both install attempts failed. Restore it with: claude plugin install $PluginSelector --scope user. $_")
        }
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
        # reduces the dangerous window to a rename.
        #
        # Stage outside the skills directory. A half-copied directory left in
        # $piSkillsDir carries a valid SKILL.md, and Pi scans that directory, so
        # a partial copy or a killed process would leave Pi loading a duplicate.
        $stagingRoot = Join-Path $backupRoot ".staging"
        New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null

        # Clean up any staging directory an earlier interrupted run left behind
        # inside the skills directory, from before staging moved out of it.
        $strays = @(Get-ChildItem -LiteralPath $piSkillsDir -Directory -Filter "*.incoming-*" -ErrorAction SilentlyContinue)
        foreach ($stray in $strays) {
            Write-Warning "Removing a staging directory left by an interrupted run: $($stray.Name)"
            Remove-Item -LiteralPath $stray.FullName -Recurse -Force
        }

        $staged = @()
        try {
            foreach ($skillName in $standaloneSkills) {
                $sourceSkill = Join-Path $piPackageSkills $skillName
                $stagedSkill = Join-Path $stagingRoot $skillName
                Copy-Item -LiteralPath $sourceSkill -Destination $stagedSkill -Recurse
                $staged += [pscustomobject]@{ Name = $skillName; Path = $stagedSkill }
            }
        }
        catch {
            try { Remove-Item -LiteralPath $stagingRoot -Recurse -Force } catch {}
            throw "Staging the replacement skills failed; nothing was changed. $_"
        }

        # Record the backup move as soon as it succeeds, not after the whole
        # swap. If the second move fails -- the locked-file case this staging
        # exists to survive -- the live directory is already gone, and a record
        # written only after both moves would leave that one skill missing while
        # the error claimed everything was restored.
        $moves = @()
        try {
            foreach ($item in $staged) {
                $destinationSkill = Join-Path $piSkillsDir $item.Name
                $backupSkill = Join-Path $backupRoot $item.Name
                Move-Item -LiteralPath $destinationSkill -Destination $backupSkill
                $moves += [pscustomobject]@{ Name = $item.Name; Backup = $backupSkill; Live = $destinationSkill }
                Move-Item -LiteralPath $item.Path -Destination $destinationSkill
            }
        }
        catch {
            $unrestored = @()
            for ($i = $moves.Count - 1; $i -ge 0; $i--) {
                $move = $moves[$i]
                try {
                    if (Test-Path -LiteralPath $move.Live) {
                        Remove-Item -LiteralPath $move.Live -Recurse -Force
                    }
                    Move-Item -LiteralPath $move.Backup -Destination $move.Live
                }
                catch {
                    $unrestored += $move.Name
                    Write-Warning "Could not restore $($move.Name); the previous copy is at $($move.Backup)."
                }
            }
            try { Remove-Item -LiteralPath $stagingRoot -Recurse -Force } catch {}
            if ($unrestored.Count -gt 0) {
                throw ("Replacing the standalone skills failed. These were NOT restored and must be copied back from $backupRoot manually: " + ($unrestored -join ", ") + ". $_")
            }
            throw "Replacing the standalone skills failed and the previous ones were restored. $_"
        }
        try { Remove-Item -LiteralPath $stagingRoot -Recurse -Force } catch {}
        Write-Host "Replaced standalone Pi Harness skills. Backup: $backupRoot"
    }
}
else {
    Write-Warning "Pi CLI was not found. Skipping Pi."
}

Write-Host "Private skills are current. Restart each runtime that was updated."

# Install the seven Product Delivery Harness skills into a user skills directory.
# The source is staged and verified before mutation. Existing managed copies are
# moved to one timestamped backup, and any failure restores that backup.
param(
    [string]$Destination = "$HOME\.agents\skills",
    [string]$BackupRoot = "$HOME\.agents\skill-backups\product-delivery-harness",
    [switch]$CheckDependencies
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 3.0

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsSrc = Join-Path $RepoRoot "skills"
$Skills = @(
    "delivery-harness",
    "product-definition-builder",
    "ui-design-builder",
    "design-system-compiler",
    "code-security-review",
    "product-activation",
    "seo-growth-review"
)
$LegacySkills = @(
    "full-harness",
    "prd-builder",
    "product-design-builder"
)
$ManagedSkills = $Skills + $LegacySkills
$ExternalDependencies = @{
    "frontend-design" = "https://github.com/anthropics/skills/tree/main/skills/frontend-design"
    "impeccable" = "https://github.com/pbakaus/impeccable"
}
$RequiredCommands = @(
    "Compare-Object",
    "Copy-Item",
    "Get-ChildItem",
    "Get-Command",
    "Get-Date",
    "Get-FileHash",
    "Move-Item",
    "New-Item",
    "Remove-Item",
    "Start-Sleep",
    "Test-Path"
)

$StageRoot = $null
$BackupDir = $null
$Installed = @()
$Moved = @()
$AttemptId = "pdh-$((Get-Date).ToString('yyyyMMdd-HHmmss'))-$([Guid]::NewGuid().ToString('N'))"
$LockPath = $null
$LockStream = $null
$LockOwned = $false

if ($CheckDependencies) {
    $missing = @()
    foreach ($name in $ExternalDependencies.Keys) {
        $skillPath = Join-Path $Destination (Join-Path $name "SKILL.md")
        if (Test-Path -LiteralPath $skillPath -PathType Leaf) {
            Write-Host "dependency available: $name"
        } else {
            $missing += "$name (source: $($ExternalDependencies[$name]))"
        }
    }
    if ($missing.Count -gt 0) {
        $missing | ForEach-Object { Write-Error "dependency missing: $_" }
        throw "install frontend-design through the Codex skill installer and Impeccable through 'npx impeccable install', then rerun with -CheckDependencies"
    }
    exit 0
}

foreach ($CommandName in $RequiredCommands) {
    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "required command is unavailable: $CommandName"
    }
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "required command is unavailable: git"
}

foreach ($Skill in $Skills) {
    $SourceDir = Join-Path $SkillsSrc $Skill
    if (-not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
        throw "missing skill directory $SourceDir"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $SourceDir "SKILL.md") -PathType Leaf)) {
        throw "missing $(Join-Path $SourceDir 'SKILL.md')"
    }
}

function Test-CacheFile {
    param([string]$RelativePath)

    $parts = $RelativePath -split "[\\/]"
    if ($parts -contains "__pycache__" -or $parts -contains ".pytest_cache") {
        return $true
    }
    $extension = [IO.Path]::GetExtension($RelativePath).ToLowerInvariant()
    return $extension -eq ".pyc" -or $extension -eq ".pyo"
}

function Test-ForbiddenSourceFile {
    param([string]$RelativePath)

    $parts = @($RelativePath.ToLowerInvariant() -split "[\\/]")
    foreach ($part in $parts) {
        if ($part -eq ".env.example" -or
            ($part.StartsWith(".env.") -and $part.EndsWith(".example")) -or
            $part -eq ".dev.vars.example") { continue }
        if ($part -eq ".env" -or $part.StartsWith(".env.") -or
            $part -eq ".dev.vars" -or $part.StartsWith(".dev.vars.") -or
            $part -eq ".ds_store" -or $part -eq "thumbs.db" -or
            $part -eq ".idea" -or $part -eq ".vscode" -or
            $part -eq "node_modules" -or $part.EndsWith(".log")) {
            return $true
        }
    }
    return $false
}

function Assert-NoReparseComponents {
    param([string]$Path)

    $full = [IO.Path]::GetFullPath($Path)
    $cursor = $full
    while ($null -ne $cursor -and $cursor.Length -gt 0) {
        $item = Get-Item -LiteralPath $cursor -Force -ErrorAction SilentlyContinue
        if ($null -ne $item) {
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "reparse-point path component is forbidden: $cursor"
            }
        }
        $parent = Split-Path -Parent $cursor
        if ($parent -eq $cursor) { break }
        $cursor = $parent
    }
}

function Get-TrackedRelativeFiles {
    param([string]$Skill)

    $prefix = "skills/$Skill/"
    $tracked = @(& git -C $RepoRoot ls-files -- "skills/$Skill")
    if ($LASTEXITCODE -ne 0) {
        throw "could not read tracked manifest for $Skill"
    }
    $relativeFiles = @()
    foreach ($path in $tracked) {
        $normalized = $path.Replace("\", "/")
        if (-not $normalized.StartsWith($prefix, [StringComparison]::Ordinal)) {
            throw "unexpected tracked path for $Skill`: $path"
        }
        $relative = $normalized.Substring($prefix.Length)
        if (Test-CacheFile $relative) { continue }
        if (Test-ForbiddenSourceFile $relative) {
            throw "forbidden tracked source artifact: $path"
        }
        $relativeFiles += $relative
    }
    if ($relativeFiles.Count -eq 0) {
        throw "$Skill tracked manifest is empty"
    }
    return @($relativeFiles | Sort-Object -Unique)
}

function Assert-NoUnexpectedSourceFiles {
    param([string]$Skill)

    $commands = @(
        @("ls-files", "--others", "--exclude-standard", "--", "skills/$Skill"),
        @("ls-files", "--others", "--ignored", "--exclude-standard", "--", "skills/$Skill")
    )
    foreach ($arguments in $commands) {
        $paths = @(& git -C $RepoRoot @arguments)
        if ($LASTEXITCODE -ne 0) {
            throw "could not inspect untracked source files for $Skill"
        }
        foreach ($path in $paths) {
            $relative = $path.Replace("\", "/").Substring("skills/$Skill/".Length)
            if (Test-CacheFile $relative) { continue }
            throw "untracked or ignored source artifact is not installable: $path"
        }
    }
}

function Get-TreeManifest {
    param([string]$Root)

    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        throw "manifest root does not exist: $Root"
    }
    $SourceRoot = (Resolve-Path -LiteralPath $Root).ProviderPath
    $manifest = @(Get-ChildItem -LiteralPath $SourceRoot -Recurse -Force -File |
        Where-Object {
            $relative = $_.FullName.Substring($SourceRoot.Length + 1)
            -not (Test-CacheFile $relative) -and $relative -ne ".pdh-install-owner"
        } |
        ForEach-Object {
            $relative = $_.FullName.Substring($SourceRoot.Length + 1)
            [pscustomobject]@{
                Relative = $relative.Replace("\", "/")
                Sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        } |
        Sort-Object -Property Relative)
    if ($manifest.Count -eq 0) {
        throw "manifest is empty: $Root"
    }
    return $manifest
}

function Get-SourceManifest {
    param([string]$Skill)

    $SourceRoot = Join-Path $SkillsSrc $Skill
    return @(Get-TrackedRelativeFiles $Skill | ForEach-Object {
        $sourceFile = Join-Path $SourceRoot $_
        if (-not (Test-Path -LiteralPath $sourceFile -PathType Leaf)) {
            throw "tracked source file is missing: $sourceFile"
        }
        [pscustomobject]@{
            Relative = $_
            Sha256 = (Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    })
}

function Compare-Tree {
    param(
        [string]$Skill,
        [string]$Target,
        [string]$Label
    )

    $sourceManifest = Get-SourceManifest $Skill
    $targetManifest = Get-TreeManifest $Target
    $difference = Compare-Object -ReferenceObject $sourceManifest -DifferenceObject $targetManifest -Property Relative, Sha256
    if ($null -ne $difference) {
        throw "$Label file manifest or bytes do not match the tracked source"
    }
}

function Copy-TrackedFiles {
    param(
        [string]$Skill,
        [string]$Target
    )

    $SourceRoot = Join-Path $SkillsSrc $Skill
    foreach ($relative in Get-TrackedRelativeFiles $Skill) {
        $sourceFile = Join-Path $SourceRoot $relative
        $targetFile = Join-Path $Target $relative
        $targetDirectory = Split-Path -Parent $targetFile
        Assert-NoReparseComponents $sourceFile
        Assert-NoReparseComponents $targetFile
        Assert-NoReparseComponents $targetDirectory
        if (-not (Test-Path -LiteralPath $targetDirectory)) {
            New-Item -ItemType Directory -Path $targetDirectory | Out-Null
        }
        Assert-NoReparseComponents $sourceFile
        Assert-NoReparseComponents $targetDirectory
        Assert-NoReparseComponents $targetFile
        Copy-Item -LiteralPath $sourceFile -Destination $targetFile
    }
}

function Release-InstallLock {
    if ($null -ne $LockStream) {
        $LockStream.Dispose()
        $script:LockStream = $null
    }
    if ($LockOwned -and $null -ne $LockPath -and (Test-Path -LiteralPath $LockPath -PathType Leaf)) {
        $owner = [IO.File]::ReadAllText($LockPath).Trim()
        if ($owner -eq $AttemptId -or -not $owner) {
            Assert-NoReparseComponents $LockPath
            Remove-Item -LiteralPath $LockPath -Force
        }
        else {
            Write-Warning "refusing to remove an install lock not owned by this attempt: $LockPath"
        }
    }
    $script:LockOwned = $false
}

function Restore-Installation {
    $restoreFailed = $false

    foreach ($Skill in $Installed) {
        $target = Join-Path $Destination $Skill
        $ownerPath = Join-Path $target ".pdh-install-owner"
        $ownerExists = Test-Path -LiteralPath $ownerPath -PathType Leaf
        $ownerMatches = $ownerExists -and
            [IO.File]::ReadAllText($ownerPath).Trim() -eq $AttemptId
        if ($ownerMatches -or (-not $ownerExists -and $LockOwned)) {
            try {
                Assert-NoReparseComponents $target
                Remove-Item -LiteralPath $target -Recurse -Force
            }
            catch {
                Write-Warning "could not remove partial install: $target"
                $restoreFailed = $true
            }
        }
        elseif (Test-Path -LiteralPath $target) {
            Write-Warning "preserving partial target not owned by this attempt: $target"
            $restoreFailed = $true
        }
    }

    if ($null -ne $BackupDir) {
        foreach ($Skill in $Moved) {
            $target = Join-Path $Destination $Skill
            $saved = Join-Path $BackupDir $Skill
            if (-not (Test-Path -LiteralPath $saved)) {
                continue
            }
            if (Test-Path -LiteralPath $target) {
                Write-Warning "cannot restore $Skill because $target still exists"
                $restoreFailed = $true
                continue
            }
            try {
                Assert-NoReparseComponents $saved
                Assert-NoReparseComponents $target
                Move-Item -LiteralPath $saved -Destination $target
            }
            catch {
                Write-Warning "could not restore $saved"
                $restoreFailed = $true
            }
        }
        if ((Test-Path -LiteralPath $BackupDir) -and -not (Get-ChildItem -LiteralPath $BackupDir -Force)) {
            try {
                Assert-NoReparseComponents $BackupDir
                Remove-Item -LiteralPath $BackupDir -Force
            }
            catch {
                $restoreFailed = $true
            }
        }
    }

    if ($null -ne $StageRoot -and (Test-Path -LiteralPath $StageRoot)) {
        try {
            Assert-NoReparseComponents $StageRoot
            Remove-Item -LiteralPath $StageRoot -Recurse -Force
        }
        catch {
            $restoreFailed = $true
        }
    }
    return -not $restoreFailed
}

try {
    Assert-NoReparseComponents $SkillsSrc
    Assert-NoReparseComponents $Destination
    Assert-NoReparseComponents $BackupRoot
    foreach ($Skill in $Skills) {
        Assert-NoUnexpectedSourceFiles $Skill
    }
    $destinationFull = [IO.Path]::GetFullPath($Destination).TrimEnd('\', '/')
    $skillsSourceFull = [IO.Path]::GetFullPath($SkillsSrc).TrimEnd('\', '/')
    $separator = [IO.Path]::DirectorySeparatorChar
    if ($destinationFull.Equals($skillsSourceFull, [StringComparison]::OrdinalIgnoreCase) -or
        $destinationFull.StartsWith($skillsSourceFull + $separator, [StringComparison]::OrdinalIgnoreCase) -or
        $skillsSourceFull.StartsWith($destinationFull + $separator, [StringComparison]::OrdinalIgnoreCase)) {
        throw "destination overlaps repository skills: $destinationFull"
    }
    $backupFull = [IO.Path]::GetFullPath($BackupRoot).TrimEnd('\', '/')
    if ($backupFull.Equals($destinationFull, [StringComparison]::OrdinalIgnoreCase) -or
        $backupFull.StartsWith($destinationFull + $separator, [StringComparison]::OrdinalIgnoreCase)) {
        throw "BackupRoot must stay outside Destination: $backupFull"
    }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Assert-NoReparseComponents $Destination
    $LockPath = Join-Path $Destination ".pdh-install.lock"
    try {
        $LockStream = [IO.File]::Open(
            $LockPath,
            [IO.FileMode]::CreateNew,
            [IO.FileAccess]::ReadWrite,
            [IO.FileShare]::None
        )
        $LockOwned = $true
    }
    catch {
        throw "another install owns destination lock: $LockPath"
    }
    if ($env:PDH_INSTALL_TEST_FAIL_LOCK_OWNER) {
        throw "induced lock owner marker failure"
    }
    $lockBytes = [Text.Encoding]::UTF8.GetBytes("$AttemptId`n")
    $LockStream.Write($lockBytes, 0, $lockBytes.Length)
    $LockStream.Flush()
    if ($env:PDH_INSTALL_TEST_HOLD_LOCK_SECONDS) {
        Start-Sleep -Seconds ([double]$env:PDH_INSTALL_TEST_HOLD_LOCK_SECONDS)
    }
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $stageName = ".pdh-install-stage-$stamp-$([Guid]::NewGuid().ToString('N'))"
    $StageRoot = Join-Path $Destination $stageName
    New-Item -ItemType Directory -Path $StageRoot | Out-Null
    Assert-NoReparseComponents $StageRoot

    foreach ($Skill in $Skills) {
        $stageTarget = Join-Path $StageRoot $Skill
        New-Item -ItemType Directory -Path $stageTarget | Out-Null
        Assert-NoReparseComponents $stageTarget
        Copy-TrackedFiles -Skill $Skill -Target $stageTarget
    }

    # Test-only corruption hook. It changes a staged non-SKILL file before the
    # pre-install equality gate, so tests can prove every file is checked.
    $corruptRelative = $env:PDH_INSTALL_TEST_CORRUPT_STAGE
    if ($corruptRelative) {
        if ($corruptRelative -match '(^|[\\/])\.\.([\\/]|$)' -or $corruptRelative -match '^[\\/]') {
            throw "invalid staged corruption path"
        }
        $corruptFile = Join-Path $StageRoot $corruptRelative
        if (-not (Test-Path -LiteralPath $corruptFile -PathType Leaf)) {
            throw "corruption test path is not a staged file"
        }
        [IO.File]::AppendAllText($corruptFile, "`nexpected test corruption`n")
    }

    foreach ($Skill in $Skills) {
        Compare-Tree -Skill $Skill -Target (Join-Path $StageRoot $Skill) -Label $Skill
    }

    New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
    Assert-NoReparseComponents $BackupRoot
    $existing = @($ManagedSkills | Where-Object { Test-Path -LiteralPath (Join-Path $Destination $_) })
    if ($existing.Count -gt 0) {
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $BackupDir = Join-Path $BackupRoot $stamp
        $collision = 1
        while (Test-Path -LiteralPath $BackupDir) {
            $BackupDir = Join-Path $BackupRoot "$stamp-$collision"
            $collision++
        }
        New-Item -ItemType Directory -Path $BackupDir | Out-Null
        Assert-NoReparseComponents $BackupDir
        foreach ($Skill in $existing) {
            $Moved += $Skill
            Assert-NoReparseComponents (Join-Path $Destination $Skill)
            Assert-NoReparseComponents (Join-Path $BackupDir $Skill)
            Move-Item -LiteralPath (Join-Path $Destination $Skill) -Destination (Join-Path $BackupDir $Skill)
            Write-Host "backed up existing $Skill -> $(Join-Path $BackupDir $Skill)"
        }
    }

    foreach ($Skill in $Skills) {
        $target = Join-Path $Destination $Skill
        Assert-NoReparseComponents $target
        if ($env:PDH_INSTALL_TEST_CREATE_FOREIGN_TARGET -eq $Skill) {
            New-Item -ItemType Directory -Path $target | Out-Null
            [IO.File]::WriteAllText((Join-Path $target "keep.txt"), "foreign sentinel`n")
        }
        if (Test-Path -LiteralPath $target) {
            throw "install target appeared during transaction: $target"
        }
        New-Item -ItemType Directory -Path $target | Out-Null
        Assert-NoReparseComponents $target
        $Installed += $Skill
        if ($env:PDH_INSTALL_TEST_FAIL_OWNER_MARKER -eq $Skill) {
            throw "induced target owner marker failure for $Skill"
        }
        [IO.File]::WriteAllText((Join-Path $target ".pdh-install-owner"), "$AttemptId`n")
        $stageSource = Join-Path $StageRoot $Skill
        Get-ChildItem -LiteralPath $stageSource -Recurse -Force -File | ForEach-Object {
            $relative = $_.FullName.Substring($stageSource.Length + 1)
            $targetFile = Join-Path $target $relative
            $targetDirectory = Split-Path -Parent $targetFile
            Assert-NoReparseComponents $_.FullName
            Assert-NoReparseComponents $targetFile
            Assert-NoReparseComponents $targetDirectory
            if (-not (Test-Path -LiteralPath $targetDirectory)) {
                New-Item -ItemType Directory -Path $targetDirectory | Out-Null
            }
            Assert-NoReparseComponents $_.FullName
            Assert-NoReparseComponents $targetDirectory
            Assert-NoReparseComponents $targetFile
            Copy-Item -LiteralPath $_.FullName -Destination $targetFile
        }
        Write-Host "installed $Skill -> $target"
        if ($env:PDH_INSTALL_FAIL_AFTER -eq $Skill) {
            throw "induced failure after installing $Skill"
        }
    }

    foreach ($Skill in $Skills) {
        Compare-Tree -Skill $Skill -Target (Join-Path $Destination $Skill) -Label $Skill
    }
    foreach ($Skill in $LegacySkills) {
        if (Test-Path -LiteralPath (Join-Path $Destination $Skill)) {
            throw "legacy skill remains installed: $Skill"
        }
    }

    foreach ($Skill in $Skills) {
        $ownerPath = Join-Path (Join-Path $Destination $Skill) ".pdh-install-owner"
        if (-not (Test-Path -LiteralPath $ownerPath -PathType Leaf) -or
            [IO.File]::ReadAllText($ownerPath).Trim() -ne $AttemptId) {
            throw "installed target ownership marker changed: $(Join-Path $Destination $Skill)"
        }
    }
    foreach ($Skill in $Skills) {
        Assert-NoReparseComponents (Join-Path (Join-Path $Destination $Skill) ".pdh-install-owner")
        Remove-Item -LiteralPath (Join-Path (Join-Path $Destination $Skill) ".pdh-install-owner") -Force
    }

    Assert-NoReparseComponents $StageRoot
    Remove-Item -LiteralPath $StageRoot -Recurse -Force
    $StageRoot = $null
    Write-Host "done. start a fresh host session so it discovers the skills."
}
catch {
    $originalFailure = $_.Exception
    if (-not (Restore-Installation)) {
        Write-Warning "rollback finished with errors; the timestamped backup is preserved"
    }
    throw $originalFailure
}
finally {
    Release-InstallLock
}

# Install the five Product Delivery Harness skills into a user skills directory.
# Any pre-existing copies are moved to one timestamped backup first - nothing is
# overwritten or deleted. Re-running this script is the update path.
param(
    [string]$Destination = "$HOME\.agents\skills"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillsSrc = Join-Path $repoRoot "skills"
$backupRoot = "$HOME\.agents\skill-backups\product-delivery-harness"
$skills = @(
    "delivery-harness",
    "product-definition-builder",
    "design-system-compiler",
    "code-security-review",
    "product-activation"
)

foreach ($skill in $skills) {
    if (-not (Test-Path (Join-Path $skillsSrc $skill))) {
        Write-Error "missing skill directory $(Join-Path $skillsSrc $skill)"
    }
}

New-Item -ItemType Directory -Force -Path $Destination | Out-Null

$existing = $skills | Where-Object { Test-Path (Join-Path $Destination $_) }
if ($existing) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupDir = Join-Path $backupRoot $stamp
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    foreach ($skill in $existing) {
        Move-Item (Join-Path $Destination $skill) (Join-Path $backupDir $skill)
        Write-Host "backed up existing $skill -> $(Join-Path $backupDir $skill)"
    }
}

foreach ($skill in $skills) {
    $target = Join-Path $Destination $skill
    Copy-Item -Path (Join-Path $skillsSrc $skill) -Destination $Destination -Recurse -Force
    Get-ChildItem -Path $target -Recurse -Directory -Filter "__pycache__" |
        Remove-Item -Recurse -Force
    if ((Get-FileHash (Join-Path (Join-Path $skillsSrc $skill) "SKILL.md")).Hash -ne
        (Get-FileHash (Join-Path $target "SKILL.md")).Hash) {
        Write-Error "$target/SKILL.md does not match the checkout"
    }
    Write-Host "installed $skill -> $target"
}

Write-Host "done. start a fresh host session so it discovers the skills."

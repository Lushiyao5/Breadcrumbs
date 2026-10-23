[CmdletBinding()]
param(
    [string]$Repository = $(if ($env:TLOCK_REPOSITORY) { $env:TLOCK_REPOSITORY } else { "SaroashDS/Tlock" })
)

$ErrorActionPreference = "Stop"
$headers = @{
    Accept = "application/vnd.github+json"
    "User-Agent" = "tlock-bootstrap"
    "X-GitHub-Api-Version" = "2022-11-28"
}
$tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
$workRoot = Join-Path $tempBase ("tlock-bootstrap-" + [guid]::NewGuid().ToString("N"))
$archivePath = Join-Path $workRoot "tlock.zip"
$extractPath = Join-Path $workRoot "source"

try {
    Write-Host "Finding the latest Tlock release..." -ForegroundColor Yellow
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/$Repository/releases/latest" -Headers $headers
    New-Item -ItemType Directory -Force -Path $extractPath | Out-Null
    Invoke-WebRequest -Uri $release.zipball_url -Headers $headers -OutFile $archivePath
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractPath -Force
    $sourceRoot = Get-ChildItem -LiteralPath $extractPath -Directory | Select-Object -First 1
    if (-not $sourceRoot) {
        throw "The GitHub release archive did not contain a source directory."
    }
    $installer = Join-Path $sourceRoot.FullName "install.ps1"
    if (-not (Test-Path -LiteralPath $installer)) {
        throw "install.ps1 was not found in the latest release."
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $installer
    if ($LASTEXITCODE -ne 0) {
        throw "The Tlock installer failed with exit code $LASTEXITCODE."
    }
}
finally {
    if (Test-Path -LiteralPath $workRoot) {
        $resolved = (Resolve-Path -LiteralPath $workRoot).Path
        if ($resolved.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase) -and
            (Split-Path -Leaf $resolved).StartsWith("tlock-bootstrap-")) {
            Remove-Item -LiteralPath $resolved -Recurse -Force
        }
    }
}

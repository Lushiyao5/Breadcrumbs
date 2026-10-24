[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  BREADCRUMBS // installing your focus companion" -ForegroundColor Yellow
Write-Host ""

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExecutable = Get-Command python -All -ErrorAction SilentlyContinue |
    Where-Object { $_.Source -notlike "*Microsoft\WindowsApps\python.exe" } |
    Select-Object -ExpandProperty Source -First 1

if (-not $pythonExecutable) {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $resolved = & $pyLauncher.Source -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $resolved) {
            $pythonExecutable = $resolved.Trim()
        }
    }
}

if (-not $pythonExecutable) {
    throw "Python 3.11+ was not found. Install Python from python.org, then run this installer again."
}

$pythonVersion = & $pythonExecutable -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pythonVersion -lt [version]"3.11") {
    throw "Breadcrumbs requires Python 3.11 or newer; found Python $pythonVersion."
}

$runtimeRoot = Join-Path $env:LOCALAPPDATA "Breadcrumbs"
$virtualEnvironment = Join-Path $runtimeRoot "venv"
$virtualPython = Join-Path $virtualEnvironment "Scripts\python.exe"
$breadcrumbsExecutable = Join-Path $virtualEnvironment "Scripts\breadcrumbs.exe"

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
if (-not (Test-Path $virtualPython)) {
    Write-Host "  Creating private runtime..." -ForegroundColor DarkGray
    & $pythonExecutable -m venv $virtualEnvironment
    if ($LASTEXITCODE -ne 0) { throw "Could not create the Breadcrumbs runtime." }
}

Write-Host "  Installing Breadcrumbs and its terminal UI..." -ForegroundColor DarkGray
& $virtualPython -m pip install --disable-pip-version-check --quiet --upgrade $projectRoot
if ($LASTEXITCODE -ne 0) {
    throw "Package installation failed. Check your internet connection and try again."
}

$windowsApps = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
$launcherPath = Join-Path $windowsApps "breadcrumbs.cmd"
$launcher = "@echo off`r`n`"$breadcrumbsExecutable`" %*`r`n"
New-Item -ItemType Directory -Force -Path $windowsApps | Out-Null
Set-Content -LiteralPath $launcherPath -Value $launcher -Encoding Ascii
$legacyLauncher = Join-Path $windowsApps "tlock.cmd"
if (Test-Path -LiteralPath $legacyLauncher) {
    Set-Content -LiteralPath $legacyLauncher -Value $launcher -Encoding Ascii
}

Write-Host ""
Write-Host "  Ready! Type " -NoNewline -ForegroundColor Green
Write-Host "breadcrumbs" -NoNewline -ForegroundColor Yellow
Write-Host " from any PowerShell window." -ForegroundColor Green
Write-Host "  Existing session data is preserved." -ForegroundColor DarkGray
Write-Host ""

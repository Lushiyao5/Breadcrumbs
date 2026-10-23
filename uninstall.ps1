[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$runtimeRoot = Join-Path $env:LOCALAPPDATA "Tlock"
$launcherPath = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\tlock.cmd"

if (Test-Path $launcherPath) {
    Remove-Item -LiteralPath $launcherPath -Force
}
if (Test-Path $runtimeRoot) {
    $resolvedRuntime = (Resolve-Path -LiteralPath $runtimeRoot).Path
    $expectedRuntime = [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "Tlock"))
    if ($resolvedRuntime -eq $expectedRuntime) {
        Remove-Item -LiteralPath $resolvedRuntime -Recurse -Force
    }
}

Write-Host "Tlock was uninstalled. Your history in ~/.tlock was kept." -ForegroundColor Yellow

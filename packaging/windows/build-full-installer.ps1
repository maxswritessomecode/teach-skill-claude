# Teach Skill Claude - Full Windows Installer Build
# Usage: .\packaging\windows\build-full-installer.ps1

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$distDir = Join-Path $projectDir "dist"
$specFile = Join-Path $PSScriptRoot "TeachSkillClaude.spec"
$installerScript = Join-Path $PSScriptRoot "TeachSkillClaude.iss"

Set-Location $projectDir

Write-Host "=== Teach Skill Claude Full Installer Build ===" -ForegroundColor Cyan
Write-Host "Project: $projectDir"

$pyVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python 3.10+ is required on the build machine." -ForegroundColor Red
    exit 1
}
if ($pyVersion -match "Python (\d+)\.(\d+)") {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if (-not ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10))) {
        Write-Host "Python 3.10 or higher is required. Found $pyVersion" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Could not parse Python version: $pyVersion" -ForegroundColor Red
    exit 1
}
Write-Host "Python: $pyVersion"

$pyinstaller = python -m PyInstaller --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller is required in the build environment." -ForegroundColor Red
    Write-Host "Install it in your build venv, then rerun this script." -ForegroundColor Yellow
    exit 1
}
Write-Host "PyInstaller: $pyinstaller"

$iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
if (-not $iscc) {
    Write-Host "Inno Setup ISCC.exe is required to create TeachSkillClaudeSetup.exe." -ForegroundColor Red
    Write-Host "Install Inno Setup and ensure ISCC.exe is on PATH." -ForegroundColor Yellow
    exit 1
}
Write-Host "Inno Setup: $($iscc.Source)"

if (Test-Path $distDir) {
    Remove-Item $distDir -Recurse -Force
}

python -m PyInstaller $specFile --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller build failed." -ForegroundColor Red
    exit 1
}

& $iscc.Source $installerScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "Inno Setup build failed." -ForegroundColor Red
    exit 1
}

Write-Host "Created installer output in: $distDir" -ForegroundColor Green

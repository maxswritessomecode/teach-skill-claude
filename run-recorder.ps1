# Teach Skill — Easy Recorder Launcher for Windows
# Usage: .\run-recorder.ps1

$ErrorActionPreference = "Stop"

# Navigate to script's own folder to support relative executions
Set-Location $PSScriptRoot

Write-Host "`n=== Teach Skill Launcher ===" -ForegroundColor Cyan

# 1. Detect and ensure virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "  Virtual environment not found. Initiating full Windows setup..." -ForegroundColor Yellow
    powershell -File .\scripts\setup-windows.ps1
}

# 2. Activate virtual environment and launch
Write-Host "  Activating virtual environment..." -ForegroundColor White
& .\.venv\Scripts\Activate.ps1

Write-Host "  Launching Telemetry Recorder tray app..." -ForegroundColor Green
teach-skill record

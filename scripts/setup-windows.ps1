# Teach Skill — Windows Development Environment Setup
# Run in PowerShell as Administrator (right-click > Run as Administrator)
# Usage: .\scripts\setup-windows.ps1

$ErrorActionPreference = "Stop"

Write-Host "`n=== Teach Skill — Windows Setup ===" -ForegroundColor Cyan
Write-Host ""

# --- 1. Check Python ---
Write-Host "[1/7] Checking Python..." -ForegroundColor Yellow
try {
    $pyVersion = python --version 2>&1
    if ($pyVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -ge 3 -and $minor -ge 10) {
            Write-Host "  OK: $pyVersion" -ForegroundColor Green
        } else {
            Write-Host "  FAIL: Python 3.10+ required, found $pyVersion" -ForegroundColor Red
            Write-Host "  Install from: https://www.python.org/downloads/" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "  FAIL: Python not found" -ForegroundColor Red
    Write-Host "  Install from: https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  IMPORTANT: Check 'Add Python to PATH' during install" -ForegroundColor Red
    exit 1
}

# --- 2. Check uv ---
Write-Host "[2/7] Checking uv..." -ForegroundColor Yellow
try {
    $uvVersion = uv --version 2>&1
    Write-Host "  OK: $uvVersion" -ForegroundColor Green
} catch {
    Write-Host "  WARN: uv not found. Attempting to install..." -ForegroundColor Yellow
    try {
        # Download and install uv via powershell
        powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
        $env:Path += ";$env:USERPROFILE\.local\bin"
        $uvVersion = uv --version 2>&1
        Write-Host "  OK: Installed $uvVersion" -ForegroundColor Green
    } catch {
        Write-Host "  WARN: Failed to install uv automatically. Falling back to standard Python pip." -ForegroundColor Yellow
    }
}

# --- 3. Check Git ---
Write-Host "[3/7] Checking Git..." -ForegroundColor Yellow
try {
    $gitVersion = git --version 2>&1
    Write-Host "  OK: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "  FAIL: Git not found" -ForegroundColor Red
    Write-Host "  Install from: https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

# --- 4. Check Claude Code CLI ---
Write-Host "[4/7] Checking Claude Code CLI..." -ForegroundColor Yellow
try {
    $claudeVersion = claude --version 2>&1
    Write-Host "  OK: $claudeVersion" -ForegroundColor Green
} catch {
    Write-Host "  WARN: Claude Code CLI not found" -ForegroundColor Yellow
    Write-Host "  Install from: https://claude.ai/code" -ForegroundColor Yellow
    Write-Host "  (Not blocking — needed for compile step, not for development)" -ForegroundColor Yellow
}

# --- 5. Clone repo (if not already in it) ---
Write-Host "[5/7] Setting up repository..." -ForegroundColor Yellow
$projectDir = "$env:USERPROFILE\projects\teach-skill-antigravity"

if (Test-Path "$projectDir\.git") {
    Write-Host "  OK: Repo already cloned at $projectDir" -ForegroundColor Green
    Set-Location $projectDir
} else {
    Write-Host "  Cloning repo to $projectDir..." -ForegroundColor White
    New-Item -ItemType Directory -Path "$env:USERPROFILE\projects" -Force | Out-Null
    git clone https://github.com/maxswritessomecode/teach-skill.git $projectDir
    Set-Location $projectDir
    Write-Host "  OK: Cloned to $projectDir" -ForegroundColor Green
}

# --- 6. Create venv and install dependencies ---
Write-Host "[6/7] Setting up virtual environment..." -ForegroundColor Yellow
$useUv = $false
try {
    $null = Get-Command uv -ErrorAction Stop
    $useUv = $true
} catch {}

if ($useUv) {
    if (-not (Test-Path ".venv")) {
        uv venv
        Write-Host "  Created .venv using uv" -ForegroundColor Green
    } else {
        Write-Host "  OK: .venv already exists" -ForegroundColor Green
    }
    
    # Activate venv
    & .\.venv\Scripts\Activate.ps1
    
    Write-Host "  Installing dependencies using uv..." -ForegroundColor White
    uv pip install -e ".[recorder,dev]"
    Write-Host "  OK: Project and dependencies installed via uv" -ForegroundColor Green
} else {
    if (-not (Test-Path ".venv")) {
        python -m venv .venv
        Write-Host "  Created .venv using standard Python" -ForegroundColor Green
    } else {
        Write-Host "  OK: .venv already exists" -ForegroundColor Green
    }
    
    # Activate venv
    & .\.venv\Scripts\Activate.ps1
    
    Write-Host "  Installing dependencies using pip..." -ForegroundColor White
    pip install --upgrade pip | Out-Null
    pip install -e ".[recorder,dev]"
    Write-Host "  OK: Project and dependencies installed via pip" -ForegroundColor Green
}

# --- 7. Verify installations ---
Write-Host "[7/7] Verifying installations..." -ForegroundColor Yellow

$checks = @(
    @{ Name = "pywin32";         Test = "import win32gui; print('ok')" },
    @{ Name = "pynput";          Test = "import pynput; print('ok')" },
    @{ Name = "Pillow";          Test = "from PIL import Image; print('ok')" },
    @{ Name = "pystray";         Test = "import pystray; print('ok')" },
    @{ Name = "click";           Test = "import click; print('ok')" },
    @{ Name = "claude-agent-sdk"; Test = "import claude_agent_sdk; print('ok')" },
    @{ Name = "pytest";          Test = "import pytest; print('ok')" }
)

$allPassed = $true
foreach ($check in $checks) {
    try {
        $result = python -c $check.Test 2>&1
        if ($result -eq "ok") {
            Write-Host "  OK: $($check.Name)" -ForegroundColor Green
        } else {
            Write-Host "  FAIL: $($check.Name) — $result" -ForegroundColor Red
            $allPassed = $false
        }
    } catch {
        Write-Host "  FAIL: $($check.Name) — import error" -ForegroundColor Red
        $allPassed = $false
    }
}

# --- Summary ---
Write-Host "`n=== Setup Summary ===" -ForegroundColor Cyan
Write-Host "  Project: $projectDir" -ForegroundColor White
Write-Host "  Python:  $(python --version 2>&1)" -ForegroundColor White
Write-Host "  Venv:    $projectDir\.venv" -ForegroundColor White

if ($allPassed) {
    Write-Host "`n  All checks passed!" -ForegroundColor Green
} else {
    Write-Host "`n  Some checks failed — review errors above" -ForegroundColor Red
}

Write-Host "`n  To activate the venv in future sessions:" -ForegroundColor Yellow
Write-Host "    cd $projectDir" -ForegroundColor White
Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""

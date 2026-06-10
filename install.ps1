# Teach Skill Claude - Windows Installation Script
# Run in PowerShell (no admin elevation required if Python is already installed!)
# Usage: Double-click or run .\install.ps1 in PowerShell from the extracted folder.

$ErrorActionPreference = "Stop"
Clear-Host

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "      Teach Skill Claude - Windows Installer " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will set up the Teach Skill Claude recorder on your system." -ForegroundColor White
Write-Host "Requirements: Python 3.10+ must be installed." -ForegroundColor Yellow
Write-Host ""

# --- 1. Verify Python ---
Write-Host "[1/4] Checking Python installation..." -ForegroundColor Yellow
try {
    $pyVersion = python --version 2>&1
    if ($pyVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10)) {
            Write-Host "  Found: $pyVersion" -ForegroundColor Green
        } else {
            Write-Host "  Error: Python 3.10 or higher is required. Found $pyVersion" -ForegroundColor Red
            Write-Host "  Please install the latest Python from: https://www.python.org/downloads/" -ForegroundColor Cyan
            Read-Host "Press Enter to exit..."
            exit 1
        }
    }
} catch {
    Write-Host "  Error: Python was not found on your system." -ForegroundColor Red
    Write-Host "  Please download and install Python from: https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host "  IMPORTANT: Make sure to check the box 'Add Python.exe to PATH' during installation!" -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

# --- 2. Create Virtual Environment ---
Write-Host "[2/4] Creating virtual environment (.venv)..." -ForegroundColor Yellow
$currentDir = Get-Location
if (Test-Path ".venv") {
    Write-Host "  Virtual environment already exists." -ForegroundColor Green
} else {
    try {
        python -m venv .venv
        Write-Host "  Created virtual environment successfully." -ForegroundColor Green
    } catch {
        Write-Host "  Error: Failed to create virtual environment." -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
}

# --- 3. Install Package & Dependencies ---
Write-Host "[3/4] Installing dependencies..." -ForegroundColor Yellow
try {
    # Upgrade pip first
    Write-Host "  Upgrading pip..." -ForegroundColor White
    $pipUpgradeOutput = & .\.venv\Scripts\python.exe -m pip install --upgrade pip 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "pip upgrade failed: $pipUpgradeOutput"
    }
    
    # Remove old editable package metadata from earlier project names, if present.
    Write-Host "  Removing old package metadata if present..." -ForegroundColor White
    $null = & .\.venv\Scripts\python.exe -m pip uninstall -y teach-skill 2>&1

    # Install package in editable/local mode with recorder options
    Write-Host "  Installing Teach Skill Claude recorder packages..." -ForegroundColor White
    $installOutput = & .\.venv\Scripts\python.exe -m pip install -e ".[recorder]" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed: $installOutput"
    }
    
    # Verify recorder-only imports are available after installing extras
    Write-Host "  Verifying recorder imports..." -ForegroundColor White
    $verifyOutput = & .\.venv\Scripts\python.exe -c "import win32gui, win32process, win32clipboard, win32con, psutil, uiautomation; from PIL import Image; import pynput, pystray" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Recorder import verification failed: $verifyOutput"
    }
    
    Write-Host "  Dependencies installed successfully." -ForegroundColor Green
} catch {
    Write-Host "  Error: Failed to install dependencies." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

# --- 4. Initialize Configuration ---
Write-Host "[4/4] Setting up configuration..." -ForegroundColor Yellow
$configDir = Join-Path $env:USERPROFILE ".teach-skill"
$configFile = Join-Path $configDir "config.json"
$defaultRecordingsDir = Join-Path $configDir "recordings"

if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

if (Test-Path $configFile) {
    Write-Host "  Existing config.json found. Keeping current settings." -ForegroundColor Green
} else {
    # Create default config matching the tester's profile
    $configObj = @{
        "hotkey_toggle" = "ctrl+shift+t"
        "hotkey_pause" = "ctrl+shift+p"
        "storage_path" = $defaultRecordingsDir.Replace("\", "\\")
        "screenshot_resolution" = "native"
        "screenshot_capture_mode" = "adaptive"
        "compile_max_image_edge" = 1568
        "privacy_filter" = $true
        "capture_raw_keystrokes" = $false
        "capture_ui_context" = $true
    }
    
    $configJson = $configObj | ConvertTo-Json -Depth 5
    Set-Content -Path $configFile -Value $configJson -Force
    Write-Host "  Created default configuration at: $configFile" -ForegroundColor Green
}

# --- 5. Create Desktop Launcher ---
Write-Host ""
Write-Host "Creating a double-clickable launcher on your Desktop..." -ForegroundColor Yellow

$desktopPath = [Environment]::GetFolderPath("Desktop")
$launcherFile = Join-Path $currentDir "Start-Recorder.bat"
$desktopLauncher = Join-Path $desktopPath "Start Teach Skill Claude.bat"

$launcherContent = @"
@echo off
cd /d "%~dp0"
echo =========================================
echo       Starting Teach Skill Claude
echo =========================================
echo.
.venv\Scripts\python.exe -m teach_skill.cli launch
"@

# Write launcher to project folder
Set-Content -Path $launcherFile -Value $launcherContent -Force

# Write copy launcher to Desktop
$desktopLauncherContent = @"
@echo off
cd /d "$currentDir"
.venv\Scripts\python.exe -m teach_skill.cli launch
"@
Set-Content -Path $desktopLauncher -Value $desktopLauncherContent -Force

Write-Host "  [✓] Created launcher in folder: Start-Recorder.bat" -ForegroundColor Green
Write-Host "  [✓] Created launcher on Desktop: Start Teach Skill Claude.bat" -ForegroundColor Green

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "         INSTALLATION SUCCESSFUL!            " -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "How to start recording:" -ForegroundColor White
Write-Host "  Simply double-click the 'Start Teach Skill Claude' shortcut on your Desktop!" -ForegroundColor Cyan
Write-Host "  When done, right-click the red circle tray icon and choose 'Stop Recording'." -ForegroundColor Cyan
Write-Host ""
Write-Host "Your recordings are saved inside: " -ForegroundColor White
Write-Host "  $configDir" -ForegroundColor Yellow
Write-Host "Logs are saved inside: " -ForegroundColor White
Write-Host "  $configDir\logs" -ForegroundColor Yellow
Write-Host "Use the README compile command to turn a recording into a skill." -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to finish..."

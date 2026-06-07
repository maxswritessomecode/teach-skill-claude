@echo off
setlocal
cd /d "%~dp0"

echo =============================================
echo       Teach Skill Claude - Windows Installer
echo =============================================
echo.
echo This installer uses cmd.exe and Python directly.
echo It does not run script files or change execution policy.
echo.

echo [1/5] Checking Python installation...
set "PYTHON_CMD=python"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    py -3 --version >nul 2>&1
    if errorlevel 1 (
        echo   Error: Python was not found.
        echo   Install Python 3.10 or newer from https://www.python.org/downloads/
        echo   During installation, check "Add Python.exe to PATH".
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py -3"
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    %PYTHON_CMD% --version
    echo   Error: Python 3.10 or newer is required.
    pause
    exit /b 1
)
%PYTHON_CMD% --version

echo.
echo [2/5] Creating virtual environment...
if exist ".venv\Scripts\python.exe" (
    echo   Virtual environment already exists.
) else (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo   Error: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

echo.
echo [3/5] Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo   Error: Failed to upgrade pip.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip uninstall -y teach-skill >nul 2>&1
".venv\Scripts\python.exe" -m pip install -e ".[recorder]"
if errorlevel 1 (
    echo   Error: Failed to install Teach Skill Claude dependencies.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -c "import win32gui, win32process, win32clipboard, win32con, psutil, uiautomation; from PIL import Image; import pynput, pystray"
if errorlevel 1 (
    echo   Error: Recorder dependency verification failed.
    pause
    exit /b 1
)

echo.
echo [4/5] Creating default config...
".venv\Scripts\python.exe" -c "from pathlib import Path; import json; root=Path.home()/'.teach-skill'; rec=root/'recordings'; root.mkdir(parents=True, exist_ok=True); rec.mkdir(parents=True, exist_ok=True); cfg=root/'config.json'; data={'hotkey_toggle':'ctrl+shift+t','hotkey_pause':'ctrl+shift+p','storage_path':str(rec),'screenshot_resolution':'native','privacy_filter':True,'capture_raw_keystrokes':False,'capture_ui_context':True}; cfg.exists() or cfg.write_text(json.dumps(data, indent=2), encoding='utf-8')"
if errorlevel 1 (
    echo   Error: Failed to create default config.
    pause
    exit /b 1
)

echo.
echo [5/5] Creating launchers...
(
    echo @echo off
    echo cd /d "%~dp0"
    echo .venv\Scripts\python.exe -m teach_skill.cli launch
) > "Start-Recorder.bat"

if exist "%USERPROFILE%\Desktop" (
    (
        echo @echo off
        echo cd /d "%CD%"
        echo .venv\Scripts\python.exe -m teach_skill.cli launch
    ) > "%USERPROFILE%\Desktop\Start Teach Skill Claude.bat"
    echo   Created Desktop launcher: Start Teach Skill Claude.bat
) else (
    echo   Desktop folder not found. Use Start-Recorder.bat in this folder.
)

echo.
echo =============================================
echo         INSTALLATION SUCCESSFUL
echo =============================================
echo.
echo Start with: Start-Recorder.bat
echo Logs: %USERPROFILE%\.teach-skill\logs\teach-skill.log
echo.
pause

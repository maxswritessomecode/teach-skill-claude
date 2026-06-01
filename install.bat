@echo off
cd /d "%~dp0"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -Command "Unblock-File -LiteralPath '%~dp0install.ps1' -ErrorAction SilentlyContinue; & '%~dp0install.ps1'"

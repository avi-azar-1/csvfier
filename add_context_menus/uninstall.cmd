@echo off
REM Helper script to bypass execution policy and run the uninstall script
cd /d "%~dp0"
echo Running uninstall_context_menu.ps1...
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall_context_menu.ps1"

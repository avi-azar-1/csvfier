@echo off
REM Helper script to bypass execution policy and run the install script
cd /d "%~dp0"
echo Running install_context_menu.ps1...
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_context_menu.ps1"

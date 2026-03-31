# Requires -Version 3.0
$ErrorActionPreference = "Stop"

$scriptDir = $PSScriptRoot
if ($scriptDir -eq "" -or $null -eq $scriptDir) {
    $scriptDir = (Get-Location).Path
}

$csvfierPath = Join-Path -Path $scriptDir -ChildPath "csvfier.py"

if (-Not (Test-Path -Path $csvfierPath)) {
    Write-Host "Error: csvfier.py not found at $csvfierPath" -ForegroundColor Red
    Write-Host "Please run this script from the directory containing csvfier.py." -ForegroundColor Red
    Read-Host "Press enter to exit..."
    exit 1
}

$pythonCommand = Get-Command "python.exe" -ErrorAction SilentlyContinue
if ($null -eq $pythonCommand) {
    # Try just 'python' if 'python.exe' fails
    $pythonCommand = Get-Command "python" -ErrorAction SilentlyContinue
}

if ($null -eq $pythonCommand) {
    Write-Host "Error: python executable not found in PATH." -ForegroundColor Red
    Read-Host "Press enter to exit..."
    exit 1
}

$pythonPath = $pythonCommand.Source

# Find pythonw.exe to run without a console window
$pythonwPath = $pythonPath -replace 'python\.exe$', 'pythonw.exe' -replace 'python$', 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonwPath)) {
    # If pythonw.exe does not exist in the same folder, fallback to python.exe
    $pythonwPath = $pythonPath 
}

Write-Host "Found Python at: $pythonPath" -ForegroundColor Green
if ($pythonwPath -ne $pythonPath) {
    Write-Host "Found Pythonw (no window) at: $pythonwPath" -ForegroundColor Green
}
Write-Host "Found Csvfier at: $csvfierPath" -ForegroundColor Green
function Install-ContextMenu {
    param (
        [string]$Path,
        [string]$Name,
        [string]$CommandArgs
    )
    
    $winPath = $Path.Replace("HKCU:\", "HKCU\")
    
    # Create key and set (default) value
    reg add $winPath /ve /d $Name /f | Out-Null
    
    # Add specific Windows system icon instead of generic Python exe icon
    reg add $winPath /v "Icon" /t REG_EXPAND_SZ /d "%systemroot%\system32\imageres.dll,186" /f | Out-Null
    
    # Command string for the action using pythonw so no console window spawns
    $commandString = "`"$pythonwPath`" `"$csvfierPath`" $CommandArgs `"`%1`""
    
    $winCmdPath = "$winPath\command"
    reg add $winCmdPath /ve /d $commandString /f | Out-Null
}

try {
    Write-Host "`nInstalling context menu items for files..."
    Install-ContextMenu -Path "HKCU:\Software\Classes\*\shell\csvify_encode" -Name "csvify encode" -CommandArgs "encode"
    Install-ContextMenu -Path "HKCU:\Software\Classes\*\shell\csvify_decode" -Name "csvify decode" -CommandArgs "decode"

    Write-Host "Installing context menu items for directories..."
    Install-ContextMenu -Path "HKCU:\Software\Classes\Directory\shell\csvify_encode" -Name "csvify encode" -CommandArgs "encode"
    Install-ContextMenu -Path "HKCU:\Software\Classes\Directory\shell\csvify_decode" -Name "csvify decode" -CommandArgs "decode"

    Write-Host "`nContext menu items installed successfully!" -ForegroundColor Green
    Write-Host "You can now right-click a file or folder and select 'csvify encode' or 'csvify decode'." -ForegroundColor Green
} catch {
    Write-Host "`nAn error occurred while installing context menu entries: $_" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press enter to exit..."

# Requires -Version 3.0
$ErrorActionPreference = "Stop"

$paths = @(
    "HKCU:\Software\Classes\*\shell\csvify_encode",
    "HKCU:\Software\Classes\*\shell\csvify_decode",
    "HKCU:\Software\Classes\Directory\shell\csvify_encode",
    "HKCU:\Software\Classes\Directory\shell\csvify_decode"
)

Write-Host "Removing csvfier context menu items..."

try {
    foreach ($path in $paths) {
        $winPath = $path.Replace("HKCU:\", "HKCU\")
        $null = reg query $winPath 2>&1
        if ($LASTEXITCODE -eq 0) {
            reg delete $winPath /f | Out-Null
            Write-Host "Removed $path" -ForegroundColor Green
        } else {
            Write-Host "Already removed $path" -ForegroundColor Yellow
        }
    }
    Write-Host "`nContext menu items uninstalled successfully!" -ForegroundColor Green
} catch {
    Write-Host "`nAn error occurred while removing context menu entries: $_" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press enter to exit..."

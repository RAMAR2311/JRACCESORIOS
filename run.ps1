# Script de arranque en PowerShell para JRACCESORIOS
Set-Location $PSScriptRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       INICIANDO SERVIDOR JRACCESORIOS" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$pythonExe = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "[INFO] Creando entorno virtual .venv..." -ForegroundColor Yellow
    & "C:\Users\MI PC\AppData\Local\Programs\Python\Python314\python.exe" -m venv --system-site-packages .venv
}

Write-Host "Servidor web disponible en: " -NoNewline
Write-Host "http://localhost:5000" -ForegroundColor Green
Write-Host "Presiona Ctrl+C para detener el servidor." -ForegroundColor Gray
Write-Host ""

Start-Process "http://localhost:5000"
& $pythonExe app.py

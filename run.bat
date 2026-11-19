@echo off
cd /d "%~dp0"
title JRACCESORIOS - Sistema de Gestion
echo ========================================================
echo        INICIANDO SERVIDOR JRACCESORIOS
echo ========================================================
echo.

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [INFO] Creando entorno virtual .venv...
    "C:\Users\MI PC\AppData\Local\Programs\Python\Python314\python.exe" -m venv --system-site-packages .venv
)

echo Usando entorno virtual: .venv
echo Servidor web disponible en: http://localhost:5000
echo.
echo Abriendo navegador en http://localhost:5000 ...
start http://localhost:5000
echo.
echo Presiona Ctrl+C para detener el servidor.
echo ========================================================

.\.venv\Scripts\python.exe app.py
pause

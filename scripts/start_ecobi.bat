@echo off
setlocal
title EcoBI Intelligence — Plataforma Corporativa Local

echo =======================================================
echo  Iniciando EcoBI Intelligence (Release Piloto Windows)
echo =======================================================

cd /d "%~dp0\.."

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXEC=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXEC=python"
)

echo Usando runtime Python: %PYTHON_EXEC%

"%PYTHON_EXEC%" scripts\ecobi_launcher.py %*

if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao iniciar o EcoBI Intelligence. Verifique os logs em data\logs\ecobi.log.
    pause
)

endlocal

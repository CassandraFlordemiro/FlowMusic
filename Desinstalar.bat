@echo off
chcp 65001 >nul
title Desinstalador do FlowMusic 360
color 0E

echo ========================================================
echo        Desinstalador do FlowMusic 360
echo ========================================================
echo.

echo [1/2] Encerrando o serviço em segundo plano...
python "%~dp0client.py" stop_daemon >nul 2>&1

echo [2/2] Removendo o plugin do Flow Launcher...
set "FLOW_PLUGINS=%APPDATA%\FlowLauncher\Plugins\FlowMusic-1.0.0"
if exist "%FLOW_PLUGINS%" (
    rmdir /s /q "%FLOW_PLUGINS%" >nul 2>&1
)

color 0A
echo.
echo FlowMusic 360 foi desinstalado do Flow Launcher com sucesso!
echo.
pause


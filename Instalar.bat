@echo off
chcp 65001 >nul
title Instalador do FlowMusic 360
color 0B

echo ========================================================
echo         Instalador do FlowMusic 360 para Flow Launcher
echo ========================================================
echo.

:: 1. Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERRO] Python não foi encontrado no sistema!
    echo Por favor, instale o Python 3.10+ em https://python.org
    echo e certifique-se de marcar "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

echo [1/4] Instalando dependências do Python (pygame, pillow, yt-dlp)...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if %errorlevel% neq 0 (
    echo [AVISO] Falha ao instalar algumas dependências. Tentando continuar...
)

:: 2. Localizar Flow Launcher
set "FLOW_PLUGINS=%APPDATA%\FlowLauncher\Plugins\FlowMusic-1.0.0"
echo [2/4] Sincronizando arquivos com o Flow Launcher em:
echo       %FLOW_PLUGINS%

if not exist "%FLOW_PLUGINS%" (
    mkdir "%FLOW_PLUGINS%" >nul 2>&1
)

copy /y "%~dp0flow_plugin_main.py" "%FLOW_PLUGINS%\main.py" >nul
copy /y "%~dp0plugin.json" "%FLOW_PLUGINS%\plugin.json" >nul

if exist "%~dp0assets" (
    xcopy /e /i /y "%~dp0assets" "%FLOW_PLUGINS%\assets" >nul
)

:: 3. Iniciar Daemon em segundo plano
echo [3/4] Iniciando o serviço do FlowMusic em segundo plano...
wscript.exe "%~dp0Iniciar_FlowMusic.vbs"

:: 4. Concluído!
color 0A
echo [4/4] Instalação concluída com sucesso!
echo.
echo ========================================================
echo  Como usar:
echo   1. Abra o Flow Launcher (Alt + Espaço)
echo   2. Digite: m
echo   3. Atalho da Ilha Flutuante: Ctrl + Alt + M
echo   4. Alternar Tema Claro/Escuro: clique na Lua/Sol ou digite: m tema
echo   5. Volume: role a rodinha do mouse sobre a Ilha!
echo ========================================================
echo.
pause


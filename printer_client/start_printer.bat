@echo off
title Xprinter Client - Sale and Stock Bot
echo ========================================
echo  Sale and Stock Bot - Printer Client
echo ========================================
echo.

cd /d "%~dp0"

REM Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.12+
    pause
    exit /b 1
)

REM Check dependencies
python -c "import websockets; import win32print" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing or updating dependencies...
    pip install -r requirements.txt
    echo.
)

:loop
echo [%date% %time%] Starting Printer Client...
python client.py
echo.
echo [%date% %time%] Client stopped. Restarting in 3 seconds...
timeout /t 3 /nobreak >nul
goto loop

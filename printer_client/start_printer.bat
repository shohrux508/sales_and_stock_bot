@echo off
title Xprinter Client - Sale & Stock Bot
echo ========================================
echo  Sale ^& Stock Bot - Printer Client
echo ========================================
echo.

cd /d "%~dp0"

REM Проверяем наличие Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python не найден! Установите Python 3.12+
    pause
    exit /b 1
)

REM Проверяем наличие зависимостей
python -c "import websockets" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Установка зависимостей...
    pip install -r requirements.txt
    echo.
)

:loop
echo [%date% %time%] Запуск клиента печати...
python client.py
echo.
echo [%date% %time%] Клиент завершил работу. Перезапуск через 3 секунды...
timeout /t 3 /noplay >nul
goto loop

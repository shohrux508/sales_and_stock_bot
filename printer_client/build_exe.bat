@echo off
title Building Printer Client EXE
echo ========================================
echo  Building Printer Client EXE
echo ========================================
echo.

cd /d "%~dp0"

REM Install dependencies including PyInstaller
echo [1/3] Installing dependencies...
pip install -r requirements.txt

REM Build the EXE
echo [2/3] Building executable...
pyinstaller --onefile --noconsole --name "PrinterClient" --clean client.py

echo.
echo [3/3] Done! 
echo Check the "dist" folder for PrinterClient.exe
echo.
echo IMPORTANT: Remember to put your .env file in the same folder as the EXE.
pause

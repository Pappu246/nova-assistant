@echo off
cd /d "%~dp0"
echo Stopping NOVA...

REM Kill server window
taskkill /FI "WINDOWTITLE eq NOVA-Server*" /F >nul 2>&1

REM Kill voice window
taskkill /FI "WINDOWTITLE eq NOVA-Voice*" /F >nul 2>&1

REM Kill python processes running nova
python shutdown.py

REM Kill chromium (browser-use wala)
taskkill /F /IM chromium.exe >nul 2>&1

echo.
echo NOVA band ho gaya Boss.
timeout /t 2 /nobreak >nul

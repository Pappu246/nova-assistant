@echo off
cd /d "%~dp0"
title NOVA

echo ============================================
echo   NOVA Starting - Continuous Mode
echo   Hey Jarvis ki zaroorat NAHI
echo   Bas bolo - time kya hai
echo ============================================
echo.

REM Check if NOVA already running
tasklist /FI "WINDOWTITLE eq NOVA*" 2>nul | find /I "cmd.exe" >nul
if errorlevel 1 goto start_nova
echo NOVA already running.
goto done

:start_nova
echo Starting NOVA in continuous mode...
start "NOVA" /min cmd /c "python main.py --continuous"

:done
echo.
echo NOVA ready hai Boss - HUD bottom-right mein.
echo Band karne ke liye: nova_stop.bat
timeout /t 2 /nobreak >nul

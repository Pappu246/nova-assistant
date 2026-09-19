@echo off
cd /d "%~dp0"
title NOVA

echo ============================================
echo   NOVA Starting
echo   Bas bolo - "time kya hai"
echo ============================================
echo.

start "NOVA" /min cmd /c "python main.py --continuous"

echo NOVA ready hai Boss - HUD bottom-right mein.
timeout /t 2 /nobreak >nul

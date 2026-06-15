@echo off
title AI Job Hunter
cd /d "%~dp0"
echo ============================================
echo   AI Job Hunter - Starting...
echo ============================================
echo.
echo Installing dependencies...
python -m pip install -r requirements.txt --quiet 2>nul
echo.
echo Running job hunter...
cd src
python main.py
echo.
echo ============================================
echo   Done! Press any key to exit.
echo ============================================
pause

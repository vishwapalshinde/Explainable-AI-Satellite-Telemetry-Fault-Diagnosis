@echo off
REM ============================================================================
REM STARTUP SCRIPT FOR EXPLAINABLE AI SATELLITE TELEMETRY SYSTEM
REM ============================================================================
REM This script starts the complete application with one click
REM Location: Project Root
REM Usage: Double-click this file OR run: startup.bat
REM ============================================================================

cls
echo ============================================================================
echo  🚀 EXPLAINABLE AI SATELLITE TELEMETRY SYSTEM - STARTUP
echo ============================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Python is not installed or not in PATH
    echo.
    echo Solution:
    echo   1. Install Python 3.10+ from https://www.python.org
    echo   2. Make sure to check "Add Python to PATH" during installation
    echo   3. Restart your computer
    echo   4. Try again: double-click this file
    echo.
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ ERROR: Node.js is not installed or not in PATH
    echo.
    echo Solution:
    echo   1. Install Node.js 18+ from https://nodejs.org
    echo   2. Restart your computer
    echo   3. Try again: double-click this file
    echo.
    pause
    exit /b 1
)

echo ✅ Python is installed
python --version

echo ✅ Node.js is installed
node --version

echo.
echo ============================================================================
echo 📊 STARTING APPLICATION...
echo ============================================================================
echo.
echo This will start:
echo   🔹 Backend  (FastAPI) on http://127.0.0.1:8000
echo   🔹 Frontend (Next.js) on http://localhost:3000
echo.
echo Once started, your browser will open automatically.
echo.
echo ⏻ To stop: Press CTRL+C in this window and confirm
echo.
pause

REM Start the application
cd /d "%~dp0"
python app.py

if %errorlevel% neq 0 (
    echo.
    echo ❌ Application failed to start
    echo Check the error messages above
    pause
    exit /b 1
)

pause

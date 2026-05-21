@echo off
title MHXY Assistant
cd /d "%~dp0"

echo ============================================
echo   MHXY AI Assistant v2 - Starting...
echo ============================================
echo.

set "PYTHON_CMD=py -3.12"
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    set "PYTHON_CMD=python"
    python --version >nul 2>&1
)
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.12 not found
    echo Please install from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH"
    pause
    exit /b 1
)

echo [OK] Python 3.12 ready

if not exist "vendor" (
    echo.
    echo [INFO] First run - installing dependencies...
    echo.
    call setup_deps.bat
    if %errorlevel% neq 0 (
        pause
        exit /b 1
    )
) else (
    echo [OK] Dependencies found
)

echo.
echo [INFO] Loading AI assistant...
echo        First launch may take 5-15 seconds
echo.

%PYTHON_CMD% bootstrap.py

if %errorlevel% neq 0 (
    echo.
    echo ============================================
    echo [ERROR] Launch failed (code: %errorlevel%)
    echo ============================================
    echo.
    echo Common fixes:
    echo   1. Missing deps - run setup_deps.bat
    echo   2. DLL conflict - delete vendor folder and retry
    echo   3. Wrong Python version - need 3.12
    echo.
    pause
    exit /b 1
)

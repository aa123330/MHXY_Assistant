@echo off
chcp 65001 >nul 2>&1
title Setup Dependencies
cd /d "%~dp0"

set "INSTALL_ML=0"
if /I "%~1"=="full" set "INSTALL_ML=1"
if /I "%~1"=="ml" set "INSTALL_ML=1"

echo Installing runtime dependencies for Python 3.12...
echo.

set "PYTHON_CMD=py -3.12"
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    set "PYTHON_CMD=python"
)

%PYTHON_CMD% -m pip install --target vendor -r requirements.txt

if "%INSTALL_ML%"=="1" (
    echo.
    echo Installing OCR/YOLO dependencies...
    %PYTHON_CMD% -m pip install -r requirements-ml.txt
) else (
    echo.
    echo Skipping OCR/YOLO dependencies for the lite runtime.
    echo Run setup_deps.bat full to install PaddleOCR, Torch and Ultralytics.
)

echo.
echo Done.
pause

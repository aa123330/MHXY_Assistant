@echo off
chcp 65001 >nul 2>&1
title Setup Dependencies
cd /d "%~dp0"

echo Installing dependencies for Python 3.12...
echo.

set "PYTHON_CMD=py -3.12"
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    set "PYTHON_CMD=python"
)

%PYTHON_CMD% -m pip install --target vendor opencv-python "numpy>=1.26,<2.0" Pillow mss pynput pywin32 PyYAML pyautogui

echo.
echo Installing OCR dependencies...
%PYTHON_CMD% -m pip install "paddlepaddle==2.6.2" "paddleocr==2.9.1"
echo.
echo Installing YOLO dependencies...
%PYTHON_CMD% -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
%PYTHON_CMD% -m pip install ultralytics

echo.
echo Done.
pause

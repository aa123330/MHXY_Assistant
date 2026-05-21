@echo off
title MHXY Debug
cd /d "%~dp0"
echo ============================================
echo   MHXY Assistant - Debug Mode
echo ============================================
echo.

set "PYTHON_CMD=py -3.12"
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    set "PYTHON_CMD=python"
)

echo [Step 1] Python version:
%PYTHON_CMD% --version
echo.

echo [Step 2] Check vendor:
if exist "vendor" (
    echo     vendor/ found
) else (
    echo     vendor/ NOT found! Run setup_deps.bat first.
    pause
    exit /b 1
)

echo [Step 3] Test import cv2:
%PYTHON_CMD% -c "import sys; sys.path.insert(0,'vendor'); import cv2; print('cv2 OK:', cv2.__version__)"
echo.

echo [Step 4] Test import numpy:
%PYTHON_CMD% -c "import sys; sys.path.insert(0,'vendor'); import numpy; print('numpy OK:', numpy.__version__)"
echo.

echo [Step 5] Test import PIL:
%PYTHON_CMD% -c "import sys; sys.path.insert(0,'vendor'); from PIL import Image; print('PIL OK')"
echo.

echo [Step 6] Test import mss:
%PYTHON_CMD% -c "import sys; sys.path.insert(0,'vendor'); import mss; print('mss OK')"
echo.

echo [Step 7] Test import pynput:
%PYTHON_CMD% -c "import sys; sys.path.insert(0,'vendor'); import pynput; print('pynput OK')"
echo.

echo [Step 8] Test core module:
%PYTHON_CMD% -c "import sys; sys.path.insert(0,'vendor'); sys.path.insert(0,'.'); from core import find_window; print('core OK')"
echo.

echo [Step 9] Launch app:
%PYTHON_CMD% bootstrap.py
echo.
pause

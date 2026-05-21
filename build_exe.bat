@echo off
cd /d "%~dp0"

set "PYTHON_CMD=py -3.12"
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    set "PYTHON_CMD=python"
)

set "PACKAGE_ML=0"
set "PACKAGE_NAME=lite"
if /I "%~1"=="full" set "PACKAGE_ML=1"
if /I "%~1"=="full" set "PACKAGE_NAME=full"
if /I "%~1"=="ml" set "PACKAGE_ML=1"
if /I "%~1"=="ml" set "PACKAGE_NAME=full"

echo Install PyInstaller and pywin32 for Python 3.12...
%PYTHON_CMD% -m pip install pyinstaller pywin32

echo.
echo Check packaged dependencies for %PACKAGE_NAME% EXE...
%PYTHON_CMD% -c "import os, sys, pathlib, importlib.util; sys.path.insert(0,'vendor'); [sys.path.insert(0, str(pathlib.Path('vendor')/line.strip())) for p in pathlib.Path('vendor').glob('*.pth') for line in p.read_text().splitlines() if line.strip() and not line.startswith('#') and (pathlib.Path('vendor')/line.strip()).exists()]; required=['cv2','numpy','PIL','mss','pynput','win32gui','yaml','tkinter']; required += ['torch','ultralytics','paddle','paddleocr'] if os.environ.get('PACKAGE_ML','0') not in ('0','') else []; missing=[m for m in required if not importlib.util.find_spec(m)]; print('required missing:', missing); import tkinter; tkinter.Tcl(); raise SystemExit(1 if missing else 0)"
if %errorlevel% neq 0 (
    echo Required dependencies are missing or Tkinter/Tcl is not usable.
    echo Run setup_deps.bat first.
    echo If Tkinter/Tcl fails, repair Python 3.12 and enable "tcl/tk and IDLE".
    pause
    exit /b 1
)

echo.
echo Build %PACKAGE_NAME% EXE...
set "PYTHONPATH=%CD%\vendor;%CD%"
%PYTHON_CMD% -m PyInstaller build_exe.spec --noconfirm

if %errorlevel% neq 0 (
    echo Build failed! Please check the error above.
    pause
    exit /b 1
)

echo Done! EXE: dist\MHXY_Assistant.exe
pause

@echo off
cd /d "%~dp0"

set "PYTHON_CMD=py -3.12"
%PYTHON_CMD% --version >nul 2>&1
if %errorlevel% neq 0 (
    set "PYTHON_CMD=python"
)

echo Install PyInstaller and pywin32 for Python 3.12...
%PYTHON_CMD% -m pip install pyinstaller pywin32

echo.
echo Check packaged dependencies...
%PYTHON_CMD% -c "import sys, pathlib, importlib.util; sys.path.insert(0,'vendor'); [sys.path.insert(0, str(pathlib.Path('vendor')/line.strip())) for p in pathlib.Path('vendor').glob('*.pth') for line in p.read_text().splitlines() if line.strip() and not line.startswith('#') and (pathlib.Path('vendor')/line.strip()).exists()]; required=['cv2','numpy','PIL','mss','pynput','win32gui','yaml','pyautogui','tkinter','torch','ultralytics','paddle','paddleocr']; missing=[m for m in required if not importlib.util.find_spec(m)]; print('required missing:', missing); import tkinter; tkinter.Tcl(); raise SystemExit(1 if missing else 0)"
if %errorlevel% neq 0 (
    echo Required dependencies are missing or Tkinter/Tcl is not usable.
    echo Run setup_deps.bat first.
    echo If Tkinter/Tcl fails, repair Python 3.12 and enable "tcl/tk and IDLE".
    pause
    exit /b 1
)

echo.
echo Build EXE...
set "PYTHONPATH=%CD%\vendor;%CD%"
%PYTHON_CMD% -m PyInstaller build_exe.spec --noconfirm

if %errorlevel% neq 0 (
    echo Build failed! Please check the error above.
    pause
    exit /b 1
)

echo Done! EXE: dist\MHXY_Assistant.exe
pause

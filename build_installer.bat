@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "PYTHON_CMD=py -3.12"
%PYTHON_CMD% -c "import sys; print(sys.version)" >nul 2>nul
if errorlevel 1 set "PYTHON_CMD=python"

echo [1/5] Using Python:
%PYTHON_CMD% -c "import sys; print(sys.executable); print(sys.version)"
if errorlevel 1 goto :python_error

set "PACKAGE_ML=0"
set "PACKAGE_NAME=lite"
if /I "%~1"=="full" set "PACKAGE_ML=1"
if /I "%~1"=="full" set "PACKAGE_NAME=full"
if /I "%~1"=="ml" set "PACKAGE_ML=1"
if /I "%~1"=="ml" set "PACKAGE_NAME=full"

echo.
echo [2/5] Checking build dependencies...
%PYTHON_CMD% -c "import PyInstaller, PIL; print('PyInstaller', PyInstaller.__version__); print('Pillow', PIL.__version__)"
if errorlevel 1 goto :deps_error

echo.
echo [3/5] Checking runtime dependencies for %PACKAGE_NAME% package...
%PYTHON_CMD% -c "import os, sys, importlib.util; from pathlib import Path; vendor=Path('vendor').resolve(); sys.path.insert(0, str(vendor)); [sys.path.insert(0, str((vendor / line.strip()).resolve())) for p in vendor.glob('*.pth') for line in p.read_text(encoding='utf-8').splitlines() if line.strip() and not line.strip().startswith('#')]; mods=['cv2','mss','pynput','win32gui','yaml','numpy','PIL']; mods += ['torch','ultralytics','paddle','paddleocr'] if os.environ.get('PACKAGE_ML','0') not in ('0','') else []; missing=[m for m in mods if importlib.util.find_spec(m) is None]; print('missing:', ', '.join(missing) or 'none'); raise SystemExit(1 if missing else 0)"
if errorlevel 1 goto :runtime_deps_error

echo.
echo [4/5] Building %PACKAGE_NAME% onedir app with PyInstaller...
%PYTHON_CMD% -m PyInstaller build_installer.spec --noconfirm --clean
if errorlevel 1 goto :pyinstaller_error

echo.
echo [5/5] Building installer with Inno Setup...
where ISCC >nul 2>nul
if errorlevel 1 goto :iscc_missing
ISCC installer\mhxy_assistant.iss
if errorlevel 1 goto :inno_error

echo.
echo Done.
echo Package mode: %PACKAGE_NAME%
echo App folder: dist\MHXY_Assistant
echo Installer folder: dist\installer
exit /b 0

:python_error
echo ERROR: Python 3.12 or python command is not available.
exit /b 1

:deps_error
echo ERROR: Build dependencies are missing. Run setup_deps.bat first.
exit /b 1

:runtime_deps_error
echo ERROR: Runtime dependencies are missing. Run setup_deps.bat first.
exit /b 1

:pyinstaller_error
echo ERROR: PyInstaller build failed.
exit /b 1

:iscc_missing
echo ERROR: Inno Setup compiler ISCC was not found in PATH.
echo Install Inno Setup 6, then run this script again.
echo The app folder was built at dist\MHXY_Assistant.
exit /b 1

:inno_error
echo ERROR: Inno Setup failed to build the installer.
exit /b 1

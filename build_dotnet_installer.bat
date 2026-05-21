@echo off
setlocal
cd /d "%~dp0"

set "DOTNET=C:\Program Files\dotnet\dotnet.exe"
if not exist "%DOTNET%" set "DOTNET=dotnet"

set "DOTNET_CLI_HOME=%CD%\.dotnet_home"
set "DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1"
set "DOTNET_CLI_TELEMETRY_OPTOUT=1"
set "APPDATA=%CD%\.appdata"
set "NUGET_PACKAGES=%CD%\.nuget\packages"

echo [1/3] Publishing .NET WPF app...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$root=(Resolve-Path .).Path; $out=Join-Path $root 'dist\MHXY_Assistant_Net'; if ((Test-Path $out) -and ((Resolve-Path $out).Path.StartsWith($root))) { Remove-Item -LiteralPath $out -Recurse -Force }; New-Item -ItemType Directory -Force -Path $out | Out-Null"
if errorlevel 1 exit /b 1
"%DOTNET%" publish src\MhxyAssistant.App\MhxyAssistant.App.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=false -p:PublishTrimmed=false -o dist\MHXY_Assistant_Net
if errorlevel 1 exit /b 1

where ISCC >nul 2>nul
if errorlevel 1 (
  echo [2/3] Inno Setup ISCC was not found in PATH.
  echo Install Inno Setup or add ISCC.exe to PATH, then run this script again.
  exit /b 1
)

echo [2/3] Building installer...
ISCC installer\mhxy_assistant.iss
if errorlevel 1 exit /b 1

echo [3/3] Done.
endlocal

@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "ENV_DIR=%SCRIPT_DIR%python_env"

where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  set "PY=py"
) else (
  set "PY=python"
)

%PY% -m venv "%ENV_DIR%"
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

"%ENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

"%ENV_DIR%\Scripts\python.exe" -m pip install -r "%SCRIPT_DIR%requirements.txt"
if %ERRORLEVEL% NEQ 0 exit /b %ERRORLEVEL%

echo UnrealMCP environment ready:
echo   %ENV_DIR%\Scripts\python.exe
echo Configure your MCP client to run:
echo   "%ENV_DIR%\Scripts\python.exe" "%SCRIPT_DIR%unreal_mcp_bridge.py"

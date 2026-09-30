@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "PYTHON=%SCRIPT_DIR%python_env\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo ERROR: Python environment not found. Run setup_unreal_mcp.bat first. >&2
  exit /b 1
)

"%PYTHON%" "%SCRIPT_DIR%unreal_mcp_bridge.py" %*

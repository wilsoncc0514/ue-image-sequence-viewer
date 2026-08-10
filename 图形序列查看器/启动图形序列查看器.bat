@echo off
setlocal
set "APP_DIR=%~dp0"
set "PY_CHECK="
set "PY_GUI="
set "PY_ARGS="

if exist "%APP_DIR%.venv\Scripts\python.exe" if exist "%APP_DIR%.venv\Scripts\pythonw.exe" (
    set "PY_CHECK=%APP_DIR%.venv\Scripts\python.exe"
    set "PY_GUI=%APP_DIR%.venv\Scripts\pythonw.exe"
    goto :check_runtime
)

where py >nul 2>&1
if not errorlevel 1 (
    where pyw >nul 2>&1
    if not errorlevel 1 (
        set "PY_CHECK=py"
        set "PY_GUI=pyw"
        set "PY_ARGS=-3"
        goto :check_runtime
    )
)

where python >nul 2>&1
if not errorlevel 1 (
    where pythonw >nul 2>&1
    if not errorlevel 1 (
        set "PY_CHECK=python"
        set "PY_GUI=pythonw"
        goto :check_runtime
    )
)

echo [ERROR] Python 3.10 or newer with pythonw was not found.
echo Install Python from https://www.python.org/ and enable Add Python to PATH.
pause
exit /b 1

:check_runtime
"%PY_CHECK%" %PY_ARGS% -c "import sys, tkinter; from PIL import Image; assert sys.version_info.__ge__((3, 10))" >nul 2>&1
if errorlevel 1 goto :missing_dependency

if /I "%~1"=="--smoke-test" (
    "%PY_CHECK%" %PY_ARGS% "%APP_DIR%main.py" %*
    exit /b %errorlevel%
)

start "" "%PY_GUI%" %PY_ARGS% "%APP_DIR%main.py" %*
exit /b 0

:missing_dependency
set "REQUIREMENTS=%APP_DIR%requirements.txt"
if not exist "%REQUIREMENTS%" set "REQUIREMENTS=%APP_DIR%..\requirements.txt"
echo [ERROR] Python 3.10+, Tkinter, or Pillow is unavailable.
echo Run: "%PY_CHECK%" %PY_ARGS% -m pip install -r "%REQUIREMENTS%"
pause
exit /b 1

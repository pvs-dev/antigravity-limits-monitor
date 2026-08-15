@echo off
cd /d "%~dp0"
echo ========================================================
echo   Starting Antigravity Limits Monitor in Console Mode
echo ========================================================
echo.

set PYTHON_EXE=python

if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe" (
    set PYTHON_EXE="%LOCALAPPDATA%\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe"
)

echo Using Python: %PYTHON_EXE%
%PYTHON_EXE% main.py --settings
if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo   Process stopped with code %errorlevel%
    echo ========================================================
    pause
)

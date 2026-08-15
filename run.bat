@echo off
cd /d "%~dp0"

:: 1. Check if Python 3.13 (with PySide6) exists in WindowsApps
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\pythonw.exe" main.py %*
    goto :eof
)

:: 2. Check if py launcher has python 3.13
py -3.13 -c "import PySide6" >nul 2>&1
if %errorlevel% equ 0 (
    start "" py -3.13 -w main.py %*
    goto :eof
)

:: 3. Check C:\Python312
if exist "C:\Python312\pythonw.exe" (
    start "" "C:\Python312\pythonw.exe" main.py %*
    goto :eof
)

:: 4. Fallback to default pythonw
start "" pythonw main.py %*

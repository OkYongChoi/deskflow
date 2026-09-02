@echo off
setlocal
cd /d "%~dp0"
where pythonw >nul 2>&1
if errorlevel 1 (
    echo Python GUI launcher ^(pythonw.exe^) was not found.
    pause
    exit /b 1
)
start "" pythonw -m deskflow
endlocal

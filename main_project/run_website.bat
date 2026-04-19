@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
)

echo Running database migrations...
"%PYTHON_EXE%" manage.py migrate
if errorlevel 1 (
    echo.
    echo Migration failed. Check database credentials and dependencies.
    pause
    exit /b 1
)

echo Starting website at http://127.0.0.1:8000/
"%PYTHON_EXE%" manage.py runserver 127.0.0.1:8000

endlocal

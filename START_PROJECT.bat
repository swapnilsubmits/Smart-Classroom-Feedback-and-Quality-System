@echo off
REM Smart Classroom Feedback System - Auto Startup

echo.
echo ====================================
echo Starting Classroom Feedback System
echo ======================`==============
echo.

REM Get the full path of the script directory
set PROJECT_DIR=%~dp0
cd /d "%PROJECT_DIR%"

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install dependencies if needed
pip install -r backend\requirements.txt >nul 2>&1

REM Start the Flask server
cd backend
echo.
echo ====================================
echo ✅ Starting Flask server...
echo ====================================
echo.
echo API Server: http://localhost:5000
echo.
echo ⚠️  IMPORTANT: Keep this window open while using the system!
echo Close this window or press Ctrl+C to stop the server.
echo.

python app.py

pause

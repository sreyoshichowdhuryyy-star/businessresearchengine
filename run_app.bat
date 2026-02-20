@echo off
echo Starting Business Research Engine...

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in your PATH.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b
)

echo Installing dependencies...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo Failed to install dependencies. Please check your internet connection or Python installation.
    pause
    exit /b
)

echo Running Application...
streamlit run app.py

pause

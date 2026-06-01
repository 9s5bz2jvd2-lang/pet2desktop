@echo off
setlocal
echo ============================================
echo   Pet2Desktop - 宠物陪你

echo   One-Click Setup / 一键安装
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.10+ is required.
    echo Install from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/2] Installing dependencies...
pip install -r "%~dp0scripts\requirements.txt"
if %errorlevel% neq 0 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)

echo.
echo [2/2] Done! Run with:
echo   python scripts\main.py path\to\your-pet.jpg
echo.
echo Or double-click a pet photo and drag it onto main.py.
echo.
pause

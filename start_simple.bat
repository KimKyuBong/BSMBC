@echo off
chcp 65001 >nul
title 방송 시스템 서버

echo ========================================
echo    방송 시스템 서버 시작
echo ========================================
echo.

cd /d "%~dp0"

:: 가상환경 Python 경로
if exist "venv\Scripts\python.exe" (
    set PYTHON_EXE=venv\Scripts\python.exe
) else (
    echo ❌ 가상환경을 찾을 수 없습니다!
    echo    venv 폴더를 확인해주세요.
    pause
    exit /b 1
)

echo ✅ 가상환경 발견
echo 🚀 서버 시작 중...
echo.
echo 서버 종료하려면 Ctrl+C를 누르세요
echo.

%PYTHON_EXE% main.py

pause



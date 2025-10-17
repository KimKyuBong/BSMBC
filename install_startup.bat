@echo off
chcp 65001 >nul
title 시스템 시작시 자동 실행 설정

echo ========================================
echo    시스템 시작시 자동 실행 설정
echo ========================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ 관리자 권한이 필요합니다!
    echo.
    echo 이 파일을 마우스 오른쪽 클릭 후
    echo "관리자 권한으로 실행"을 선택해주세요.
    echo.
    pause
    exit /b 1
)

echo ✅ 관리자 권한 확인 완료
echo.

cd /d "%~dp0"

:: 현재 디렉토리 경로
set SCRIPT_PATH=%CD%\start_simple.bat

:: 가상환경 Python 경로
if exist "venv\Scripts\python.exe" (
    set PYTHON_PATH=%CD%\venv\Scripts\python.exe
    set MAIN_PATH=%CD%\main.py
) else (
    echo ❌ 가상환경을 찾을 수 없습니다!
    pause
    exit /b 1
)

echo 📂 설치 경로: %CD%
echo 🐍 Python: %PYTHON_PATH%
echo 📄 Main: %MAIN_PATH%
echo.

:: 기존 작업이 있으면 삭제
echo 🗑️  기존 작업 제거 중...
schtasks /delete /tn "방송시스템자동실행" /f >nul 2>&1

:: 새로운 작업 생성
echo 📝 새 작업 생성 중...
schtasks /create /tn "방송시스템자동실행" /tr "\"%PYTHON_PATH%\" \"%MAIN_PATH%\"" /sc onstart /ru SYSTEM /rl HIGHEST /f

if %errorLevel% equ 0 (
    echo.
    echo ========================================
    echo ✅ 설치 완료!
    echo ========================================
    echo.
    echo 시스템이 시작될 때 자동으로 서버가 실행됩니다.
    echo.
    echo 📌 작업 이름: 방송시스템자동실행
    echo 📌 실행 계정: SYSTEM
    echo 📌 트리거: 시스템 시작 시
    echo.
    echo 작업 관리자에서 확인:
    echo   1. Win+R 누르기
    echo   2. taskschd.msc 입력
    echo   3. "방송시스템자동실행" 찾기
    echo.
    echo 제거하려면: uninstall_startup.bat 실행
    echo ========================================
) else (
    echo.
    echo ❌ 설치 실패!
    echo 오류 코드: %errorLevel%
)

echo.
pause



@echo off
chcp 65001 >nul
title 학교 방송 제어 시스템 서버

echo 🚀 학교 방송 제어 시스템 서버 시작
echo ========================================

:: 프로젝트 디렉토리로 이동
cd /d "%~dp0"

:: 가상환경 활성화 (있는 경우)
if exist "venv\Scripts\activate.bat" (
    echo 📦 가상환경 활성화 중...
    call venv\Scripts\activate.bat
)

:: 로그 디렉토리 생성
if not exist "logs" mkdir logs

:: 서버 시작
echo 🔧 FastAPI 서버 시작 중...
echo 📍 서버 주소: http://localhost:8000
echo 📚 API 문서: http://localhost:8000/docs
echo 📊 상태 확인: http://localhost:8000/health
echo ========================================

:: 서버 실행 (백그라운드에서 실행)
start /B python main.py

:: 서버가 시작될 때까지 대기
timeout /t 3 /nobreak >nul

:: 브라우저에서 API 문서 열기
echo 🌐 브라우저에서 API 문서를 엽니다...
start http://localhost:8000/docs

echo ✅ 서버가 백그라운드에서 실행 중입니다.
echo 💡 서버를 중지하려면 작업 관리자에서 Python 프로세스를 종료하세요.
echo ========================================
pause 
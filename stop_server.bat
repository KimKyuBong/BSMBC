@echo off
chcp 65001 >nul
title 서버 중지

echo 🛑 학교 방송 제어 시스템 서버 중지
echo ========================================

:: Python 프로세스 찾기 및 종료
echo 🔍 Python 프로세스 검색 중...

:: main.py 프로세스 종료
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *main.py*" 2>NUL | find /I "python.exe" >NUL
if %ERRORLEVEL% EQU 0 (
    echo 🎯 main.py 프로세스 발견, 종료 중...
    taskkill /F /IM python.exe /FI "WINDOWTITLE eq *main.py*" >NUL 2>&1
)

:: uvicorn 프로세스 종료
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *uvicorn*" 2>NUL | find /I "python.exe" >NUL
if %ERRORLEVEL% EQU 0 (
    echo 🎯 uvicorn 프로세스 발견, 종료 중...
    taskkill /F /IM python.exe /FI "WINDOWTITLE eq *uvicorn*" >NUL 2>&1
)

:: 포트 8000 사용 프로세스 종료
echo 🔍 포트 8000 사용 프로세스 검색 중...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    echo 🎯 PID %%a 프로세스 종료 중...
    taskkill /F /PID %%a >NUL 2>&1
)

echo ✅ 서버 중지 완료
echo ========================================
pause 
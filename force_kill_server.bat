@echo off
chcp 65001 >nul
title 서버 강제 종료

echo 🛑 서버 강제 종료 중...
echo ========================================

:: 1. 포트 8000 사용 프로세스 강제 종료
echo 🔍 포트 8000 사용 프로세스 검색 및 종료...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    echo 🎯 PID %%a 프로세스 강제 종료 중...
    taskkill /F /PID %%a >nul 2>&1
)

:: 2. Python 프로세스 강제 종료
echo 🔍 Python 프로세스 강제 종료...
taskkill /F /IM python.exe >nul 2>&1

:: 3. uvicorn 프로세스 강제 종료
echo 🔍 uvicorn 프로세스 강제 종료...
taskkill /F /IM uvicorn.exe >nul 2>&1

:: 4. main.py 관련 프로세스 종료
echo 🔍 main.py 관련 프로세스 종료...
wmic process where "commandline like '%main.py%'" delete >nul 2>&1

:: 5. production_server.py 관련 프로세스 종료
echo 🔍 production_server.py 관련 프로세스 종료...
wmic process where "commandline like '%production_server.py%'" delete >nul 2>&1

:: 6. FastAPI 관련 프로세스 종료
echo 🔍 FastAPI 관련 프로세스 종료...
wmic process where "commandline like '%fastapi%'" delete >nul 2>&1

:: 잠시 대기
timeout /t 2 /nobreak >nul

:: 포트 상태 확인
echo 🔍 포트 8000 상태 확인...
netstat -ano | findstr :8000
if %ERRORLEVEL% EQU 0 (
    echo ⚠️ 포트 8000이 여전히 사용 중입니다.
    echo 🔄 추가 강제 종료 시도...
    
    :: 추가 강제 종료
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
        echo 🎯 PID %%a 추가 강제 종료...
        taskkill /F /PID %%a >nul 2>&1
    )
) else (
    echo ✅ 포트 8000이 해제되었습니다.
)

echo ========================================
echo ✅ 서버 강제 종료 완료!
echo 💡 이제 서버를 다시 시작할 수 있습니다.
echo ========================================
pause 
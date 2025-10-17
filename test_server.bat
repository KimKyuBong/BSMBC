@echo off
chcp 65001 >nul
title 서버 테스트

echo ========================================
echo    서버 연결 테스트
echo ========================================
echo.

echo 서버 상태 확인 중...
echo.

curl -s http://localhost:8000/health

if %errorLevel% equ 0 (
    echo.
    echo ========================================
    echo ✅ 서버가 정상 작동 중입니다!
    echo ========================================
    echo.
    echo 접속 가능한 URL:
    echo   - API 문서: http://localhost:8000/docs
    echo   - 헬스체크: http://localhost:8000/health
    echo   - 메인페이지: http://localhost:8000/
    echo.
) else (
    echo.
    echo ========================================
    echo ❌ 서버가 실행되지 않았습니다
    echo ========================================
    echo.
    echo start_simple.bat 을 먼저 실행해주세요.
    echo.
)

pause



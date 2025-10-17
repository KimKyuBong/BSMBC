@echo off
chcp 65001 >nul
title 자동 실행 제거

echo ========================================
echo    자동 실행 제거
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

echo 🗑️  작업 제거 중...
schtasks /delete /tn "방송시스템자동실행" /f

if %errorLevel% equ 0 (
    echo.
    echo ========================================
    echo ✅ 제거 완료!
    echo ========================================
    echo.
    echo 시스템 시작 시 자동 실행이 해제되었습니다.
    echo.
) else (
    echo.
    echo ⚠️  작업을 찾을 수 없거나 이미 제거되었습니다.
)

echo.
pause



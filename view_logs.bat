@echo off
chcp 65001 >nul
title 실시간 서버 로그

cd /d "%~dp0"

echo ========================================
echo    실시간 서버 로그 모니터링
echo ========================================
echo.
echo 종료하려면 Ctrl+C를 누르세요
echo.

powershell -Command "$latestLog = Get-ChildItem -Path .\logs -Filter *.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1; Write-Host \"로그 파일: $($latestLog.Name)\" -ForegroundColor Green; Write-Host \"`n\" ; Get-Content $latestLog.FullName -Tail 30 -Wait -Encoding UTF8"




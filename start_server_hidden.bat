@echo off
cd /d "C:\Users\bssmBroadcast\BSMBC"

REM VBS 스크립트를 생성하여 백그라운드 실행
echo Set WshShell = CreateObject("WScript.Shell") > "%TEMP%\start_server.vbs"
echo WshShell.Run "cmd /c cd /d C:\Users\bssmBroadcast\BSMBC && venv\Scripts\python.exe run_production.py", 0, False >> "%TEMP%\start_server.vbs"

REM VBS 스크립트 실행
cscript //nologo "%TEMP%\start_server.vbs"

REM 임시 파일 삭제
del "%TEMP%\start_server.vbs"

echo 서버가 백그라운드에서 시작되었습니다.
echo 서버 상태 확인: tasklist | findstr python.exe
timeout /t 3 /nobreak >nul



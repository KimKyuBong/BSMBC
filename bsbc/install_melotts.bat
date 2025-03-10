@echo off
echo MeloTTS 설치 도우미 스크립트 실행
echo ======================================
echo.

cd /d %~dp0
.\venv\Scripts\python.exe install_melotts.py

echo.
echo 설치 프로세스 완료
echo 아무 키나 누르면 종료합니다...
pause > nul 
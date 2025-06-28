@echo off
echo ========================================
echo FFmpeg 자동 설치 스크립트
echo ========================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [*] 관리자 권한으로 실행 중...
) else (
    echo [!] 이 스크립트는 관리자 권한이 필요합니다.
    echo [!] 관리자 권한으로 다시 실행해주세요.
    pause
    exit /b 1
)

:: 작업 디렉토리 설정
set "WORK_DIR=%~dp0"
set "FFMPEG_DIR=%WORK_DIR%ffmpeg"
set "DOWNLOAD_URL=https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
set "ZIP_FILE=%WORK_DIR%ffmpeg.zip"

echo [*] 작업 디렉토리: %WORK_DIR%
echo [*] FFmpeg 설치 디렉토리: %FFMPEG_DIR%
echo.

:: 기존 설치 확인
if exist "%FFMPEG_DIR%\bin\ffmpeg.exe" (
    echo [*] FFmpeg가 이미 설치되어 있습니다.
    echo [*] 경로: %FFMPEG_DIR%\bin
    goto :add_to_path
)

:: 디렉토리 생성
if not exist "%FFMPEG_DIR%" (
    echo [*] FFmpeg 디렉토리 생성 중...
    mkdir "%FFMPEG_DIR%"
)

:: FFmpeg 다운로드
echo [*] FFmpeg 다운로드 중... (시간이 걸릴 수 있습니다)
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%ZIP_FILE%'}"

if not exist "%ZIP_FILE%" (
    echo [!] FFmpeg 다운로드 실패
    pause
    exit /b 1
)

echo [*] 다운로드 완료: %ZIP_FILE%

:: 압축 해제
echo [*] 압축 해제 중...
powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath '%WORK_DIR%' -Force"

:: 압축 파일 삭제
del "%ZIP_FILE%"

:: 압축 해제된 폴더 찾기
for /d %%i in ("%WORK_DIR%ffmpeg-master-*") do (
    echo [*] 압축 해제된 폴더 발견: %%i
    xcopy "%%i\*" "%FFMPEG_DIR%\" /E /I /Y
    rmdir /s /q "%%i"
    goto :found_extracted
)

:found_extracted
echo [*] FFmpeg 설치 완료

:add_to_path
:: PATH 환경변수에 추가
echo [*] PATH 환경변수에 FFmpeg 경로 추가 중...

:: 현재 PATH 확인
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "CURRENT_PATH=%%b"

:: FFmpeg 경로가 이미 있는지 확인
echo %CURRENT_PATH% | findstr /i "%FFMPEG_DIR%\bin" >nul
if %errorLevel% == 0 (
    echo [*] FFmpeg 경로가 이미 PATH에 있습니다.
) else (
    echo [*] PATH에 FFmpeg 경로 추가 중...
    setx /M PATH "%CURRENT_PATH%;%FFMPEG_DIR%\bin"
    echo [*] PATH 환경변수 업데이트 완료
)

:: 설치 확인
echo.
echo [*] FFmpeg 설치 확인 중...
"%FFMPEG_DIR%\bin\ffmpeg.exe" -version >nul 2>&1
if %errorLevel% == 0 (
    echo [*] FFmpeg 설치 성공!
    echo [*] 경로: %FFMPEG_DIR%\bin\ffmpeg.exe
    echo.
    echo [*] 프리뷰 기능을 사용할 수 있습니다.
) else (
    echo [!] FFmpeg 설치 확인 실패
    pause
    exit /b 1
)

echo.
echo ========================================
echo 설치 완료!
echo ========================================
echo [*] 새 명령 프롬프트를 열어서 다음 명령어로 확인하세요:
echo     ffmpeg -version
echo     ffprobe -version
echo.
echo [*] 프리뷰 기능이 정상적으로 작동할 것입니다.
echo.
pause 
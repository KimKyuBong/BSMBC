# 윈도우 FastAPI 서버 안정적 운영 가이드

## 📋 목차
1. [필수 의존성 설치](#1-필수-의존성-설치)
2. [Windows Service로 등록](#2-windows-service로-등록)
3. [배치 파일로 자동 시작](#3-배치-파일로-자동-시작)
4. [프로덕션 서버 사용](#4-프로덕션-서버-사용)
5. [서버 모니터링](#5-서버-모니터링)
6. [문제 해결](#6-문제-해결)

## 1. 필수 의존성 설치

### 1.1 Python 패키지 설치
```bash
# 가상환경 생성 (권장)
python -m venv venv
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 1.2 Windows Service 지원 패키지
```bash
# pywin32 설치 (Windows Service용)
pip install pywin32
```

## 2. Windows Service로 등록

### 2.1 서비스 설치
```bash
# 관리자 권한으로 PowerShell 실행 후
python windows_service.py install
```

### 2.2 서비스 관리
```bash
# 서비스 시작
python windows_service.py start

# 서비스 중지
python windows_service.py stop

# 서비스 재시작
python windows_service.py restart

# 서비스 상태 확인
python windows_service.py status

# 서비스 제거
python windows_service.py uninstall
```

### 2.3 Windows 서비스 관리자에서 확인
1. `Win + R` → `services.msc` 입력
2. "학교 방송 제어 시스템" 서비스 찾기
3. 속성에서 자동 시작 설정

## 3. 배치 파일로 자동 시작

### 3.1 기본 서버 시작
```bash
# 개발용 서버 시작
start_server.bat

# 서버 중지
stop_server.bat
```

### 3.2 프로덕션 서버 시작
```bash
# 프로덕션용 서버 시작
start_production.bat
```

## 4. 프로덕션 서버 사용

### 4.1 환경 변수 설정
```bash
# 시스템 환경 변수 설정
set HOST=0.0.0.0
set PORT=8000
set WORKERS=1
```

### 4.2 직접 실행
```bash
python production_server.py
```

### 4.3 프로덕션 서버 특징
- ✅ 향상된 로깅 시스템
- ✅ 자동 재시작 기능
- ✅ 보안 미들웨어
- ✅ 성능 최적화
- ✅ 시그널 핸들링

## 5. 서버 모니터링

### 5.1 자동 모니터링 시작
```bash
python monitor_server.py
```

### 5.2 모니터링 설정
```bash
# 환경 변수로 설정
set SERVER_URL=http://localhost:8000
set CHECK_INTERVAL=30
```

### 5.3 모니터링 기능
- 🔍 30초마다 서버 상태 확인
- 🔄 자동 재시작 (최대 5회)
- 📝 상세한 로그 기록
- ⚠️ 오류 알림

## 6. 문제 해결

### 6.1 포트 충돌 해결
```bash
# 포트 8000 사용 프로세스 확인
netstat -ano | findstr :8000

# 프로세스 종료
taskkill /F /PID <프로세스ID>
```

### 6.2 권한 문제 해결
```bash
# 관리자 권한으로 실행
# 또는 방화벽에서 포트 8000 허용
```

### 6.3 로그 확인
```bash
# 서버 로그
logs/server_YYYYMMDD.log

# 모니터링 로그
logs/monitor_YYYYMMDD.log

# 서비스 로그
logs/service.log
```

### 6.4 일반적인 오류

#### 오류: "포트가 이미 사용 중입니다"
```bash
# 해결 방법
stop_server.bat
# 또는
taskkill /F /IM python.exe
```

#### 오류: "모듈을 찾을 수 없습니다"
```bash
# 해결 방법
pip install -r requirements.txt
```

#### 오류: "권한이 부족합니다"
```bash
# 해결 방법: 관리자 권한으로 실행
```

## 7. 권장 운영 방법

### 7.1 개발 환경
```bash
# 개발용 서버 (자동 재시작)
python main.py
```

### 7.2 테스트 환경
```bash
# 프로덕션 서버
python production_server.py
```

### 7.3 운영 환경
```bash
# Windows Service 등록 (권장)
python windows_service.py install
python windows_service.py start

# 또는 모니터링과 함께
python monitor_server.py
```

## 8. 성능 최적화

### 8.1 워커 수 조정
```bash
# CPU 코어 수에 따라 조정
set WORKERS=4
```

### 8.2 메모리 최적화
```bash
# 환경 변수 설정
set PYTHONOPTIMIZE=1
```

### 8.3 로그 로테이션
- 로그 파일이 100MB를 넘으면 자동으로 새 파일 생성
- 30일 이상 된 로그 파일 자동 삭제

## 9. 보안 설정

### 9.1 방화벽 설정
```bash
# Windows 방화벽에서 포트 8000 허용
netsh advfirewall firewall add rule name="BroadcastAPI" dir=in action=allow protocol=TCP localport=8000
```

### 9.2 IP 제한 설정
```python
# app/core/security.py에서 허용 IP 설정
"allowed_ip_networks": [
    "10.129.49.0/24",
    "10.129.50.0/24",
    "127.0.0.1/32"
]
```

## 10. 백업 및 복구

### 10.1 설정 파일 백업
```bash
# 중요 설정 파일 백업
copy bsbc\data\config\*.* backup\config\
```

### 10.2 데이터 백업
```bash
# 오디오 파일 및 로그 백업
xcopy data\audio backup\audio\ /E /Y
xcopy logs backup\logs\ /E /Y
```

---

## 📞 지원

문제가 발생하면 다음을 확인하세요:
1. 로그 파일 확인
2. 서버 상태 확인: `http://localhost:8000/health`
3. API 문서 확인: `http://localhost:8000/docs`

## 🔄 업데이트

새 버전 배포 시:
1. 서비스 중지: `python windows_service.py stop`
2. 코드 업데이트
3. 의존성 업데이트: `pip install -r requirements.txt`
4. 서비스 재시작: `python windows_service.py start` 
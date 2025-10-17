# 🎙️ 학교 방송 제어 시스템 (BSMBC)

> 라즈베리파이 기반 학교 방송 장비 원격 제어 시스템

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.119.0-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi-red.svg)](https://www.raspberrypi.org/)

학교 내 교실 및 특수실의 방송 장비를 네트워크를 통해 원격 제어하고, 예약 방송 및 음성 합성(TTS) 기능을 제공하는 통합 방송 관리 시스템입니다.

---

## ✨ 주요 기능

### 🎯 방송 제어
- **장치 제어**: 64개 방송 장치 개별/그룹 제어
- **음성 방송**: TTS(Text-to-Speech)를 통한 텍스트 방송
- **파일 방송**: 오디오 파일 업로드 및 방송
- **프리뷰 시스템**: 방송 전 미리듣기 및 승인
- **큐 관리**: 여러 방송 대기열 관리

### 🔊 오디오 처리
- **TTS 엔진**: gTTS (Google TTS), MeloTTS, pyttsx3 지원
- **오디오 정규화**: ffmpeg loudnorm (-12.0 dBFS 목표)
- **신호음 합성**: 시작음 + 메인 오디오 + 끝음 자동 조합
- **고품질 출력**: 192k-256k MP3 비트레이트

### 📅 스케줄링
- **예약 방송**: 시간/요일 기반 자동 방송
- **반복 실행**: 매일/매주 반복 스케줄
- **백그라운드 실행**: APScheduler 기반

### 🔒 보안
- **IP 기반 접근 제어**: 허용된 네트워크만 접속
- **TOTP 인증**: 2단계 인증 지원 (옵션)
- **장치 상태 복원**: 방송 후 원래 상태로 자동 복원

---

## 🚀 빠른 시작

### 방법 1: Docker (권장)

```bash
# 1. 저장소 클론
git clone https://github.com/KimKyuBong/BSMBC.git
cd BSMBC

# 2. Docker Compose로 실행
sudo docker compose up -d

# 3. 로그 확인
sudo docker compose logs -f

# 4. 브라우저 접속
# http://라즈베리파이IP:8000
```

### 방법 2: 직접 설치

```bash
# 1. 시스템 패키지 설치
sudo apt-get update
sudo apt-get install -y vlc python3-vlc ffmpeg espeak espeak-ng alsa-utils

# 2. Python 패키지 설치
pip3 install -r requirements.txt --break-system-packages
pip3 install audioop-lts gTTS pyttsx3 --break-system-packages

# 3. 서버 실행
python3 main.py

# 4. 브라우저 접속
# http://localhost:8000
```

---

## 📋 시스템 요구사항

### 하드웨어
- **플랫폼**: 라즈베리파이 (ARM64)
- **메모리**: 최소 512MB, 권장 2GB
- **저장공간**: 2GB 이상

### 소프트웨어
- **OS**: Debian Bookworm/Trixie 또는 Raspberry Pi OS
- **Python**: 3.13+
- **Docker**: 28.5.1+ (선택사항)

### 네트워크
- **방송 서버**: UDP 22000 포트 접근 가능
- **웹 서버**: TCP 8000 포트

---

## 📂 프로젝트 구조

```
BSMBC/
├── app/
│   ├── api/              # FastAPI 라우트
│   │   └── routes/
│   │       ├── broadcast.py       # 방송 API
│   │       ├── device_matrix.py   # 장치 매트릭스 API
│   │       └── schedule.py        # 스케줄 API
│   ├── core/             # 핵심 모듈
│   │   ├── config.py              # 설정 관리
│   │   ├── device_mapping.py      # 장치 매핑 (JSON 기반)
│   │   └── security.py            # 보안 관리
│   ├── models/           # 데이터 모델
│   │   ├── device.py
│   │   └── schedule.py
│   ├── services/         # 비즈니스 로직
│   │   ├── broadcast_controller.py  # 방송 컨트롤러
│   │   ├── broadcast_manager.py     # 방송 관리자
│   │   ├── tts_service.py           # TTS 통합
│   │   ├── network.py               # 네트워크 통신
│   │   └── packet_builder.py        # 패킷 생성
│   ├── utils/            # 유틸리티
│   │   ├── audio_normalizer.py    # 오디오 정규화
│   │   └── cli.py                 # CLI 유틸리티
│   ├── static/           # 정적 파일
│   └── templates/        # HTML 템플릿
├── config/               # 설정 파일
│   ├── device_matrix.json         # 장치 매트릭스 (동적 로드)
│   └── security_config.json       # 보안 설정
├── data/                 # 데이터 디렉토리
│   ├── audio/            # 업로드된 오디오
│   ├── previews/         # 프리뷰 파일
│   ├── temp/             # 임시 파일
│   ├── start.mp3         # 시작 신호음
│   └── end.mp3           # 끝 신호음
├── docs/                 # 기술 문서
├── tools/                # 관리 도구
├── Dockerfile            # Docker 이미지 정의
├── docker-compose.yml    # Docker Compose 설정
├── main.py               # 웹 서버 진입점
└── requirements.txt      # Python 의존성
```

---

## 🎯 사용 방법

### Web UI

브라우저에서 `http://라즈베리파이IP:8000` 접속

- **방송 제어**: 텍스트/오디오 방송, 프리뷰, 승인
- **장치 매트릭스**: 64개 장치 상태 시각화
- **스케줄 관리**: 예약 방송 설정

### API (Swagger UI)

`http://라즈베리파이IP:8000/docs`

- 모든 API 엔드포인트 문서화
- 직접 테스트 가능한 인터랙티브 UI

### CLI (Command Line)

```bash
# 장치 제어
python3 app/utils/cli.py control "1-1" --on
python3 app/utils/cli.py control "모둠12" --off

# 그룹 제어
python3 app/utils/cli.py group grade1 --on
python3 app/utils/cli.py group all --off

# 시스템 상태
python3 app/utils/cli.py status

# 스케줄 관리
python3 app/utils/cli.py schedule --list
```

---

## 🐳 Docker 배포

### 빌드 및 실행

```bash
# 이미지 빌드
docker compose build

# 백그라운드 실행
docker compose up -d

# 로그 확인
docker compose logs -f

# 중지
docker compose down
```

### 볼륨 관리

```bash
# 데이터 백업
docker run --rm \
  -v $(pwd)/data:/backup \
  alpine tar czf /backup/backup.tar.gz -C /backup .

# 로그 확인
docker compose exec broadcast tail -f /app/logs/app_*.log
```

자세한 내용은 [DOCKER_GUIDE.md](DOCKER_GUIDE.md) 참조

---

## ⚙️ 설정

### 장치 매트릭스 (`config/device_matrix.json`)

4행 16열 장치 배치를 JSON으로 정의:

```json
[
  ["1-1", "1-2", "1-3", "1-4", ..., "2-1", "2-2", "2-3", "2-4", ...],
  ["3-1", "3-2", "3-3", "3-4", ...],
  ["교행연회", "교사연구", ..., "모둠12", ...],
  ["본관1층", "융합1층", ..., "강당", "방송실", "운동장", "옥외"]
]
```

**동적 기능**:
- 그룹 자동 생성 (학년별, 전체교실)
- 장치 매핑 자동 생성
- 웹 UI에서 실시간 수정 가능

### 보안 설정 (`config/security_config.json`)

```json
{
  "totp_enabled": false,
  "totp_secret": "...",
  "ip_check_enabled": true,
  "allowed_ips": [
    "127.0.0.1/32",
    "192.168.0.0/16"
  ]
}
```

### 환경 변수

```bash
TARGET_IP=192.168.0.200      # 방송 서버 IP
TARGET_PORT=22000            # 방송 서버 포트
```

---

## 🏗️ 아키텍처

### 기술 스택

| 구분 | 기술 |
|------|------|
| **Backend** | FastAPI, Uvicorn |
| **TTS** | gTTS (Google), MeloTTS, pyttsx3 |
| **Audio** | VLC, FFmpeg, pydub |
| **Network** | Scapy (UDP 패킷) |
| **Scheduler** | APScheduler |
| **Frontend** | Jinja2 Templates, Vanilla JS |

### 시스템 흐름

```
1. 웹/API 요청
   ↓
2. BroadcastController (방송 큐 관리)
   ↓
3. TTS 생성 + 오디오 정규화 + 신호음 합성
   ↓
4. 프리뷰 생성 및 승인
   ↓
5. BroadcastManager (장치 제어)
   ↓
6. NetworkManager (UDP 패킷 전송)
   ↓
7. VLC 오디오 재생 (ALSA)
   ↓
8. 장치 상태 자동 복원
```

---

## 📊 주요 개선사항

### v1.0.0 (2025-10-17)

#### 🔄 윈도우 → 라즈베리파이 마이그레이션
- [x] FFmpeg 시스템 경로 사용 (`/usr/bin/ffmpeg`)
- [x] VLC CLI 환경 최적화 (ALSA 출력)
- [x] 네트워크 인터페이스: `eth0`
- [x] 경로 정규화 (리눅스 표준)

#### 🐳 Docker 지원
- [x] ARM64 최적화 Dockerfile
- [x] Docker Compose 설정
- [x] Bridge/Host 네트워크 지원
- [x] 볼륨 영속성 (data, logs)
- [x] 헬스체크 및 자동 재시작

#### 🎨 하드코딩 제거
- [x] 장치 매핑 → JSON 동적 로드
- [x] 그룹 정의 → 매트릭스에서 자동 생성
- [x] 설정 파일 단일화

#### 🔊 오디오 시스템
- [x] Python 3.13 호환 (audioop-lts)
- [x] gTTS 우선 사용 (Google TTS)
- [x] 다중 TTS 엔진 지원
- [x] 고품질 오디오 정규화

---

## 📚 문서

- **[INSTALLATION_COMPLETE.md](INSTALLATION_COMPLETE.md)** - 완전한 설치 가이드
- **[RASPBERRY_PI_SETUP.md](RASPBERRY_PI_SETUP.md)** - 라즈베리파이 설정
- **[DOCKER_GUIDE.md](DOCKER_GUIDE.md)** - Docker 배포 가이드
- **[docs/security_guide.md](docs/security_guide.md)** - 보안 설정
- **[docs/API_COMPLETE_SPECIFICATION.md](docs/API_COMPLETE_SPECIFICATION.md)** - 완전한 API 문서

---

## 🛠️ 개발

### 로컬 개발 환경

```bash
# 개발 모드 실행 (auto-reload)
python3 main.py

# 로그 확인
tail -f logs/app_$(date +%Y%m%d).log

# 테스트
python3 -m pytest
```

### 코드 구조

- **동적 로딩**: 모든 장치/그룹 정보는 JSON에서 로드
- **싱글톤 패턴**: BroadcastController, DeviceMapper
- **비동기 처리**: FastAPI async endpoints
- **스레드 풀**: 프리뷰 생성 병렬 처리

---

## 🔧 트러블슈팅

### 오디오가 안 나올 때

```bash
# ALSA 장치 확인
aplay -l

# VLC 테스트
cvlc --version

# 볼륨 조정
alsamixer
```

### Docker 오디오 문제

```bash
# 오디오 장치 마운트 확인
docker inspect broadcast-system | grep -A 5 Devices

# 컨테이너 내부 확인
docker exec -it broadcast-system aplay -l
```

### 네트워크 연결 문제

```bash
# 패킷 전송 테스트
python3 -c "from app.services.network import NetworkManager; nm = NetworkManager(); nm.test_connection()"

# 로그 확인
grep "패킷 전송" logs/app_*.log
```

---

## 🤝 기여

이슈 및 PR 환영합니다!

---

## 📝 라이선스

MIT License

---

## 📞 문의

- **GitHub**: [KimKyuBong/BSMBC](https://github.com/KimKyuBong/BSMBC)
- **Email**: bmbc@raspberry.local

---

## 🎯 로드맵

- [ ] 웹 UI 개선 (React/Vue.js)
- [ ] 실시간 모니터링 (WebSocket)
- [ ] 모바일 앱 지원
- [ ] 다중 서버 지원
- [ ] 통계 및 분석 기능
- [ ] MeloTTS 고품질 TTS 지원 확대

---

**Made with ❤️ for BMBC**

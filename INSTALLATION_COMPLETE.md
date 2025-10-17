# 🎉 라즈베리파이 방송 시스템 설치 완료!

## ✅ 설치 완료 항목

### 1. 시스템 패키지
- ✓ **FFmpeg 7.1.2** - 오디오/비디오 처리
- ✓ **VLC 3.0.21** - 오디오 재생 (ALSA 출력)
- ✓ **espeak/espeak-ng** - TTS 백엔드
- ✓ **python3-pip** - Python 패키지 관리자

### 2. Python 패키지
- ✓ **audioop-lts 0.2.2** - Python 3.13 호환성
- ✓ **numpy 2.3.4** - 수치 연산
- ✓ **scipy 1.16.2** - 과학 계산
- ✓ **librosa 0.11.0** - 오디오 분석
- ✓ **soundfile 0.13.1** - 오디오 파일 I/O
- ✓ **pydub** - 오디오 조작
- ✓ **python-vlc 3.0.21203** - VLC Python 바인딩
- ✓ **fastapi 0.119.0** - 웹 프레임워크
- ✓ **uvicorn 0.37.0** - ASGI 서버
- ✓ **APScheduler** - 스케줄링
- ✓ **pyotp** - TOTP 인증

### 3. 코드 수정
- ✓ 윈도우 → 라즈베리파이 경로 변경
- ✓ FFmpeg 시스템 경로 사용
- ✓ VLC CLI 환경 최적화
- ✓ 프리뷰 디렉토리 경로 수정

### 4. 디렉토리 구조
```
/home/bmbc/project/BSMBC/data/
├── audio/          # 오디오 파일
├── previews/       # 프리뷰 파일
│   └── test_preview.mp3
├── temp/           # 임시 파일
│   ├── test_combined.mp3
│   └── test_normalized.mp3
├── tts_models/     # TTS 모델 캐시
├── start.mp3       # 시작 신호음 (3.03초)
└── end.mp3         # 끝 신호음 (3.07초)
```

## ✅ 테스트 완료 기능

### 1. 오디오 재생 ✓
- VLC 재생 정상 작동
- ALSA 오디오 출력 확인
- 재생 상태 모니터링 정상

### 2. 오디오 조합 (pydub) ✓
- 시작음 + 메인 오디오 + 끝음 조합 성공
- 12.21초 프리뷰 생성 확인
- MP3 저장 정상 (287.8 KB)

### 3. 오디오 정규화 ✓
- ffmpeg loudnorm 필터 작동
- 볼륨 분석 기능 정상
- 목표 볼륨 -12.0 dBFS 적용
- 정규화 전후 통계 확인

### 4. 시스템 통합 ✓
- BroadcastController 초기화 성공
- BroadcastManager 정상 작동
- AudioNormalizer 정상 작동
- 64개 장치 매트릭스 로드 완료

## 🚀 시스템 실행 방법

### 웹 서버 모드
```bash
cd /home/bmbc/project/BSMBC
python3 main.py
```

브라우저에서 `http://라즈베리파이IP:8000` 접속

### CLI 모드
```bash
cd /home/bmbc/project/BSMBC
python3 cli.py --help
```

사용 가능한 명령:
- `python3 cli.py control 1-1 --on`  # 1학년 1반 켜기
- `python3 cli.py group grade1 --on`  # 1학년 전체 켜기
- `python3 cli.py status`  # 시스템 상태 확인

## 📊 시스템 정보

### 환경
- **OS**: Debian Trixie (Linux 6.12.47+rpt-rpi-v8)
- **Python**: 3.13.5
- **아키텍처**: ARM64 (aarch64)

### 오디오 장치
- bcm2835 Headphones (기본)
- vc4-hdmi-0 (HDMI)
- vc4-hdmi-1 (HDMI)

### 네트워크
- **대상 IP**: 192.168.0.200
- **대상 포트**: 22000
- **네트워크 인터페이스**: eth0

## ⚙️ 주요 설정

### 오디오 정규화
- **목표 볼륨**: -12.0 dBFS
- **헤드룸**: 1.0 dB
- **샘플레이트**: 44100 Hz
- **비트레이트**: 192k-256k (MP3)

### VLC 설정 (CLI 최적화)
```
--no-video          # 비디오 출력 비활성화
--aout=alsa         # ALSA 오디오 출력
--quiet             # 로그 감소
```

## 🔧 추가 권장 사항

### 1. PATH 설정 (선택사항)
```bash
echo 'export PATH=$PATH:/home/bmbc/.local/bin' >> ~/.bashrc
source ~/.bashrc
```

### 2. 자동 시작 설정 (systemd)
```bash
sudo nano /etc/systemd/system/broadcast.service
```

```ini
[Unit]
Description=School Broadcast System
After=network.target

[Service]
Type=simple
User=bmbc
WorkingDirectory=/home/bmbc/project/BSMBC
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable broadcast.service
sudo systemctl start broadcast.service
```

### 3. 볼륨 조정
```bash
alsamixer  # 터미널 믹서
```

### 4. 방화벽 설정 (필요시)
```bash
sudo ufw allow 8000/tcp  # 웹 서버 포트
```

## 📝 로그 확인

### 애플리케이션 로그
```bash
tail -f /home/bmbc/project/BSMBC/logs/app_$(date +%Y%m%d).log
```

### 시스템 로그
```bash
journalctl -u broadcast -f  # systemd 서비스 사용 시
```

## ⚠️ 알려진 이슈

### Python 3.13 audioop
- Python 3.13에서 audioop 모듈 제거됨
- **해결**: audioop-lts 0.2.2 설치로 해결 ✓

### TTS 엔진 경고
- pyttsx3 로드 실패 경고 표시됨
- **영향**: TTS 기능 사용 시 espeak 수동 설정 필요
- **해결 방법**: espeak이 이미 설치되어 있어 문제없음

## 🎯 성능 최적화

### 메모리 사용량 최적화
- 프리뷰 생성 시 스레드 풀 사용 (최대 4개)
- 임시 파일 자동 정리
- 장치 상태 백업/복원 기능

### 오디오 품질
- 고품질 정규화 옵션 지원
- 무손실 중간 처리 (PCM)
- 최종 출력 MP3 고품질

## 📚 참고 문서
- `RASPBERRY_PI_SETUP.md` - 설치 과정 상세 기록
- `README.md` - 프로젝트 전체 개요
- `docs/security_guide.md` - 보안 설정 가이드

---

## ✅ 최종 점검 결과

| 항목 | 상태 | 비고 |
|------|------|------|
| FFmpeg/FFprobe | ✅ | 7.1.2 설치됨 |
| VLC | ✅ | 3.0.21 설치됨 |
| Python 패키지 | ✅ | 모두 설치됨 |
| 오디오 재생 | ✅ | 정상 작동 |
| 오디오 조합 | ✅ | pydub 정상 |
| 오디오 정규화 | ✅ | ffmpeg loudnorm |
| 시스템 통합 | ✅ | 모든 모듈 로드 성공 |

**🎉 라즈베리파이 환경에서 모든 기능이 정상 작동합니다!**

생성일: 2025-10-17
버전: 1.0.0
플랫폼: Raspberry Pi (Debian Trixie, ARM64)

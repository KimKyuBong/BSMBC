# 라즈베리파이 설치 완료 상태

## ✅ 완료된 작업

### 1. FFmpeg 설치
- ffmpeg 7.1.2 설치 완료
- ffprobe 설치 완료
- 경로: /usr/bin/ffmpeg, /usr/bin/ffprobe

### 2. VLC 설치
- VLC 3.0.21 설치 완료
- python-vlc 3.0.21203 설치 완료
- ALSA 오디오 출력 설정 완료

### 3. TTS 엔진
- espeak 설치 완료
- espeak-ng 설치 완료
- pyttsx3가 espeak을 백엔드로 사용

### 4. Python 패키지
- pydub 0.25.1 설치 완료
- python-vlc 설치 완료
- 기타 의존성 설치 완료

### 5. 경로 수정
- 윈도우 경로 → 리눅스 경로 변경
- D:/previews → /home/bmbc/project/BSMBC/data/previews
- FFmpeg 시스템 경로 사용

### 6. 디렉토리 구조
```
/home/bmbc/project/BSMBC/data/
├── audio/          # 오디오 파일
├── previews/       # 프리뷰 파일
├── temp/           # 임시 파일
├── tts_models/     # TTS 모델 캐시
├── start.mp3       # 시작 신호음
└── end.mp3         # 끝 신호음
```

### 7. 오디오 출력 테스트
- VLC로 정상 재생 확인
- ALSA 오디오 장치 감지됨
- 재생 상태 모니터링 정상 작동

## ⚠️ 알려진 문제

### pydub audioop 이슈
- Python 3.13에서 audioop 모듈이 제거됨
- pydub가 audioop에 의존하지만, 실제 사용 시 문제 없음
- VLC로 직접 재생하므로 영향 없음
- 프리뷰 생성 시에만 pydub 사용 (ffmpeg로 대체 가능)

## 🚀 시스템 실행 방법

### 웹 서버 실행
```bash
cd /home/bmbc/project/BSMBC
python3 main.py
```

### CLI 모드
```bash
cd /home/bmbc/project/BSMBC
python3 cli.py --help
```

## 📝 추가 권장 사항

1. **pydub 대안**: Python 3.12로 다운그레이드하거나 ffmpeg 직접 사용
2. **자동 시작**: systemd 서비스 등록 권장
3. **오디오 볼륨**: alsamixer로 볼륨 조정 가능
4. **방화벽**: 필요한 포트(기본 8000) 열기

## 🔧 시스템 정보

- OS: Debian Trixie (Linux 6.12.47+rpt-rpi-v8)
- Python: 3.13.5
- VLC: 3.0.21
- FFmpeg: 7.1.2
- 오디오: ALSA (bcm2835 Headphones, HDMI)


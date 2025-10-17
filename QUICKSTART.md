# 🚀 빠른 시작 가이드

> 5분 안에 방송 시스템 실행하기

---

## 🐳 Docker로 실행 (가장 빠름!)

### 1단계: Docker 설치

```bash
# Docker 설치 스크립트
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 사용자 권한 추가
sudo usermod -aG docker $USER
newgrp docker
```

### 2단계: 프로젝트 클론 및 실행

```bash
# 저장소 클론
git clone https://github.com/KimKyuBong/BSMBC.git
cd BSMBC

# Docker Compose로 한 번에 실행!
sudo docker compose up -d

# 로그 확인 (선택사항)
sudo docker compose logs -f
```

### 3단계: 접속

브라우저에서 `http://라즈베리파이IP:8000` 접속

**끝! 🎉**

---

## 💻 직접 설치 (Docker 없이)

### 1단계: 시스템 패키지 설치

```bash
sudo apt-get update
sudo apt-get install -y \
  vlc python3-vlc \
  ffmpeg \
  espeak espeak-ng \
  alsa-utils \
  python3-pip
```

### 2단계: Python 패키지 설치

```bash
cd /path/to/BSMBC

# 필수 패키지
pip3 install -r requirements.txt --break-system-packages

# 추가 패키지
pip3 install audioop-lts gTTS pyttsx3 --break-system-packages
```

### 3단계: 서버 실행

```bash
python3 main.py
```

브라우저에서 `http://localhost:8000` 접속

---

## 🎯 첫 방송 해보기

### 웹 UI 사용

1. 브라우저에서 `http://라즈베리파이IP:8000` 접속
2. "방송" 메뉴 클릭
3. 텍스트 입력: "테스트 방송입니다"
4. 대상 선택: 원하는 교실/장치
5. "프리뷰 생성" 버튼 클릭
6. 미리듣기 후 "승인" 버튼 클릭

### Python으로 직접

```python
import requests

# 프리뷰 생성
response = requests.post(
    'http://localhost:8000/api/broadcast/text',
    data={
        'text': '테스트 방송입니다',
        'target_rooms': '101,102,201',  # 1-1, 1-2, 2-1
        'language': 'ko',
        'auto_off': 'true'
    }
)

preview_id = response.json()['preview_id']
print(f'프리뷰 ID: {preview_id}')

# 프리뷰 승인 및 방송
requests.post(f'http://localhost:8000/api/broadcast/preview/approve/{preview_id}')
print('방송 시작!')
```

### CLI 사용

```bash
# 1학년 전체 켜기
python3 app/utils/cli.py group grade1 --on

# 상태 확인
python3 app/utils/cli.py status

# 모두 끄기
python3 app/utils/cli.py group all --off
```

---

## ⚙️ 기본 설정 확인

### 장치 매트릭스

`config/device_matrix.json` 파일 확인:

```json
[
  ["1-1", "1-2", "1-3", "1-4", ..., "2-1", "2-2", "2-3", "2-4", ...],
  ["3-1", "3-2", "3-3", "3-4", ...],
  [...],
  [...]
]
```

- 총 4행 16열 = 64개 장치
- 실제 사용하는 장치만 이름 지정
- 나머지는 "장치5", "장치6" 등으로 표시

### 네트워크 설정

`app/core/config.py`:

```python
DEFAULT_TARGET_IP = "192.168.0.200"   # 방송 서버 IP
DEFAULT_TARGET_PORT = 22000           # 방송 서버 포트
```

필요시 수정하거나 환경 변수로 오버라이드:

```bash
TARGET_IP=192.168.0.100 python3 main.py
```

---

## 📊 상태 확인

### Docker 환경

```bash
# 컨테이너 상태
sudo docker compose ps

# 로그
sudo docker compose logs --tail=100

# 리소스 사용량
sudo docker stats broadcast-system
```

### 직접 실행

```bash
# 프로세스 확인
ps aux | grep "python3 main.py"

# 포트 확인
netstat -tlnp | grep 8000

# 로그
tail -f logs/app_*.log
```

---

## 🆘 문제 해결

### 서버가 시작 안 될 때

```bash
# 포트 사용 확인
sudo lsof -i :8000

# 기존 프로세스 종료
pkill -f "python3 main.py"

# 재시작
python3 main.py
```

### TTS가 안 될 때

```bash
# TTS 엔진 확인
python3 -c "from app.services.tts_service import init_tts_service; tts = init_tts_service(); print(tts.get_tts_info())"

# espeak 테스트
espeak "테스트" -v ko

# gTTS 테스트 (인터넷 필요)
python3 -c "from gtts import gTTS; tts = gTTS('테스트', lang='ko'); tts.save('test.mp3')"
```

---

## 📖 더 알아보기

- **완전한 설치**: [INSTALLATION_COMPLETE.md](INSTALLATION_COMPLETE.md)
- **Docker 가이드**: [DOCKER_GUIDE.md](DOCKER_GUIDE.md)
- **API 문서**: http://라즈베리파이IP:8000/docs
- **보안 설정**: [docs/security_guide.md](docs/security_guide.md)

---

**Happy Broadcasting! 🎙️**


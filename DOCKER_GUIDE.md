# 🐳 Docker 배포 가이드

## 📋 목차
1. [Docker 설치](#docker-설치)
2. [이미지 빌드](#이미지-빌드)
3. [컨테이너 실행](#컨테이너-실행)
4. [관리 명령](#관리-명령)

---

## 🔧 Docker 설치

### 라즈베리파이에 Docker 설치
```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 현재 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER

# 재로그인 또는
newgrp docker

# Docker 설치 확인
docker --version
docker compose version
```

---

## 🏗️ 이미지 빌드

### 1. Docker 이미지 빌드
```bash
cd /home/bmbc/project/BSMBC

# 이미지 빌드
docker build -t broadcast-system:latest .

# 빌드 확인
docker images | grep broadcast-system
```

### 2. Docker Compose로 빌드
```bash
# 이미지 빌드
docker compose build

# 빌드 로그 확인
docker compose build --progress=plain
```

---

## 🚀 컨테이너 실행

### 방법 1: Docker Compose (권장)
```bash
# 백그라운드 실행
docker compose up -d

# 로그 확인
docker compose logs -f

# 상태 확인
docker compose ps
```

### 방법 2: Docker 명령어
```bash
# 컨테이너 실행
docker run -d \
  --name broadcast-system \
  --network host \
  --device /dev/snd:/dev/snd \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config \
  -e TARGET_IP=192.168.0.200 \
  -e TARGET_PORT=22000 \
  --restart unless-stopped \
  broadcast-system:latest

# 로그 확인
docker logs -f broadcast-system
```

---

## 🛠️ 관리 명령

### 컨테이너 제어
```bash
# 시작
docker compose start
# 또는
docker start broadcast-system

# 중지
docker compose stop
# 또는
docker stop broadcast-system

# 재시작
docker compose restart
# 또는
docker restart broadcast-system

# 제거
docker compose down
# 또는
docker rm -f broadcast-system
```

### 로그 확인
```bash
# 실시간 로그
docker compose logs -f

# 최근 로그 100줄
docker compose logs --tail=100

# 특정 시간 이후 로그
docker compose logs --since 10m
```

### 컨테이너 접속
```bash
# 쉘 접속
docker compose exec broadcast bash
# 또는
docker exec -it broadcast-system bash

# Python 직접 실행
docker compose exec broadcast python3
```

### 상태 확인
```bash
# 컨테이너 상태
docker compose ps

# 리소스 사용량
docker stats broadcast-system

# 헬스체크 상태
docker inspect broadcast-system | grep -A 10 Health
```

---

## 🌐 접속 방법

### 웹 UI
```
http://라즈베리파이IP:8000
```

### API 문서 (Swagger)
```
http://라즈베리파이IP:8000/docs
```

### 헬스체크
```bash
curl http://localhost:8000/
```

---

## 📦 볼륨 관리

### 데이터 볼륨
```bash
# 볼륨 위치 확인
docker volume inspect broadcast-system_data

# 백업
docker run --rm \
  -v broadcast-system_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/data-backup.tar.gz -C /data .

# 복원
docker run --rm \
  -v broadcast-system_data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/data-backup.tar.gz"
```

---

## 🔍 문제 해결

### 오디오가 안 나올 때
```bash
# 오디오 장치 확인
docker compose exec broadcast aplay -l

# ALSA 설정 확인
docker compose exec broadcast cat /proc/asound/cards

# VLC 테스트
docker compose exec broadcast cvlc --version
```

### 권한 문제
```bash
# 오디오 장치 권한 확인
ls -l /dev/snd/

# 사용자를 audio 그룹에 추가
sudo usermod -aG audio $USER
```

### 네트워크 문제
```bash
# 네트워크 모드 확인
docker inspect broadcast-system | grep NetworkMode

# 포트 확인
docker port broadcast-system
```

---

## 🔄 업데이트

### 코드 업데이트 후 재배포
```bash
# Git pull
git pull origin main

# 이미지 재빌드
docker compose build --no-cache

# 컨테이너 재시작
docker compose down
docker compose up -d
```

---

## 📊 시스템 요구사항

### 최소 사양
- **CPU**: 1 core
- **메모리**: 512 MB
- **디스크**: 2 GB

### 권장 사양
- **CPU**: 2 cores
- **메모리**: 2 GB
- **디스크**: 5 GB

---

## ⚙️ 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `TARGET_IP` | 방송 서버 IP | 192.168.0.200 |
| `TARGET_PORT` | 방송 서버 포트 | 22000 |
| `PYTHONUNBUFFERED` | Python 버퍼링 비활성화 | 1 |

`.env` 파일로 관리:
```bash
# .env 파일 생성
cat > .env << EOF
TARGET_IP=192.168.0.200
TARGET_PORT=22000
EOF

# docker-compose.yml에서 env_file 사용
docker compose --env-file .env up -d
```

---

## 🎯 자동 시작 설정

### Docker 서비스로 등록
```bash
# 부팅 시 Docker 자동 시작
sudo systemctl enable docker

# 컨테이너 자동 재시작 설정 (이미 적용됨)
# restart: unless-stopped
```

---

## 📝 주의사항

### 1. 오디오 장치
- 컨테이너에서 호스트의 오디오 장치 접근 필요
- `/dev/snd` 마운트 필수

### 2. 네트워크 모드
- `host` 모드 사용 권장 (UDP 패킷 전송)
- 브릿지 모드는 네트워크 제한 가능

### 3. 데이터 영속성
- `data/`, `logs/` 볼륨 마운트로 데이터 보존
- 컨테이너 삭제 시에도 데이터 유지

### 4. 메모리 관리
- TTS 모델 로드 시 메모리 사용량 증가
- 최소 512MB 권장

---

## 🚀 빠른 시작

```bash
# 1. Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# 2. 이미지 빌드 및 실행
cd /home/bmbc/project/BSMBC
docker compose up -d

# 3. 로그 확인
docker compose logs -f

# 4. 브라우저 접속
# http://라즈베리파이IP:8000
```

---

## 📚 참고 자료

- `RASPBERRY_PI_SETUP.md` - 라즈베리파이 설치 가이드
- `INSTALLATION_COMPLETE.md` - 설치 완료 가이드
- `README.md` - 프로젝트 개요


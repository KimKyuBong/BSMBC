# 라즈베리파이 방송 제어 시스템 - Docker 이미지
# Base: Debian Bookworm (ARM64)
FROM python:3.13-slim

# 메타데이터
LABEL maintainer="BMBC <bmbc@raspberry.local>"
LABEL description="학교 방송 제어 시스템 - 라즈베리파이 환경"
LABEL version="1.0.0"

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    LANG=ko_KR.UTF-8 \
    LC_ALL=ko_KR.UTF-8

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 오디오 관련
    vlc \
    python3-vlc \
    ffmpeg \
    alsa-utils \
    espeak \
    espeak-ng \
    # 네트워크 도구
    curl \
    net-tools \
    iputils-ping \
    # 빌드 도구
    gcc \
    g++ \
    make \
    # 기타 유틸리티
    locales \
    && rm -rf /var/lib/apt/lists/*

# 한국어 로케일 설정
RUN sed -i '/ko_KR.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen ko_KR.UTF-8

# 작업 디렉토리 설정
WORKDIR /app

# requirements.txt 복사 및 Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 추가 패키지 설치 (requirements.txt에 없는 것들)
RUN pip install --no-cache-dir \
    audioop-lts==0.2.2 \
    pydub \
    gTTS \
    pyttsx3 \
    pyotp \
    httptools \
    websockets \
    psutil

# 애플리케이션 코드 복사
COPY app/ ./app/
COPY config/ ./config/
COPY data/ ./data/
COPY docs/ ./docs/
COPY tools/ ./tools/
COPY main.py .
COPY packet_sniffer.py .
COPY README.md .

# 디렉토리 생성
RUN mkdir -p \
    /app/data/audio \
    /app/data/previews \
    /app/data/temp \
    /app/data/tts_models \
    /app/logs

# 포트 노출
EXPOSE 8000

# 볼륨 마운트 포인트
VOLUME ["/app/data", "/app/logs"]

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# 서버 실행
CMD ["python3", "main.py"]


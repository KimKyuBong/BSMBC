# 📚 기술 문서

이 디렉토리에는 시스템의 상세 기술 문서가 포함되어 있습니다.

## 📋 문서 목록

### API 문서
- **[API_COMPLETE_SPECIFICATION.md](API_COMPLETE_SPECIFICATION.md)** - 완전한 API 명세
- **[preview_api_spec.md](preview_api_spec.md)** - 프리뷰 API 상세
- **[queue_api_spec.md](queue_api_spec.md)** - 큐 관리 API

### 시스템 문서
- **[COMPLETE_SYSTEM_SPECIFICATION.md](COMPLETE_SYSTEM_SPECIFICATION.md)** - 전체 시스템 명세
- **[PREVIEW_SYSTEM_SPECIFICATION.md](PREVIEW_SYSTEM_SPECIFICATION.md)** - 프리뷰 시스템 상세

### 보안 문서
- **[security_guide.md](security_guide.md)** - 보안 설정 가이드

---

## 🔄 최신 업데이트 반영사항

### 라즈베리파이 환경 (2025-10-17)
- FFmpeg: 시스템 경로 (`/usr/bin/ffmpeg`)
- VLC: ALSA 오디오 출력
- 네트워크: eth0 인터페이스
- TTS: gTTS (Google TTS) 우선 사용

### 하드코딩 제거
- 장치 매핑: `config/device_matrix.json`에서 동적 로드
- 그룹 정의: 매트릭스에서 자동 생성
- 설정 파일 기반 운영

### Docker 지원
- ARM64 최적화 이미지
- Bridge/Host 네트워크 옵션
- 볼륨 영속성

---

## 💡 사용 예시

모든 API는 **Swagger UI**에서도 확인 가능:
```
http://라즈베리파이IP:8000/docs
```

---

**문서 관리**: 프로젝트 변경 시 관련 문서도 함께 업데이트 필요

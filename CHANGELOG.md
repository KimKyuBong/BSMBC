# 📝 변경 이력

## v1.0.0 (2025-10-17)

### 🎉 라즈베리파이 마이그레이션 완료

#### 🔄 플랫폼 이동
- **윈도우 → 라즈베리파이** 완전 이전
- ARM64 아키텍처 최적화
- Debian Trixie 지원

#### 🗑️ 제거된 항목
- ❌ 윈도우 배치 파일 (*.bat, *.ps1)
- ❌ 윈도우 FFmpeg 바이너리 (253,421줄 삭제)
- ❌ Windows Service 스크립트
- ❌ 윈도우 전용 문서

#### ✅ 추가된 기능

**시스템 패키지**:
- VLC 3.0.21 + python-vlc (ALSA 출력)
- FFmpeg 7.1.2 (시스템 경로)
- gTTS 2.5.4 (Google TTS)
- espeak/espeak-ng (TTS 백엔드)
- audioop-lts 0.2.2 (Python 3.13 호환)

**코드 개선**:
- FFmpeg 경로: 시스템 경로 사용 (`/usr/bin/ffmpeg`)
- 네트워크: `eth0` 인터페이스
- 프리뷰 디렉토리: `data/previews`
- VLC: CLI 환경 최적화 (`--aout=alsa`)

**문서**:
- + INSTALLATION_COMPLETE.md
- + RASPBERRY_PI_SETUP.md
- + DOCKER_GUIDE.md
- + QUICKSTART.md
- + 사용방법_최신.md

#### 🐳 Docker 지원

**추가 파일**:
- + Dockerfile (ARM64 최적화)
- + docker-compose.yml (Bridge 네트워크)
- + .dockerignore

**기능**:
- 완전한 컨테이너화
- 볼륨 영속성 (data, logs)
- 헬스체크 및 자동 재시작
- Bridge/Host 네트워크 지원

#### 🎨 하드코딩 제거

**device_mapping.py**:
- ✓ device_map: JSON에서 동적 로드
- ✓ device_groups: 매트릭스에서 자동 생성
- ✓ _build_device_map_from_matrix() 추가
- ✓ _build_device_groups() 추가

**cli.py**:
- ✓ group_devices: DeviceMapper에서 동적 로드
- ✓ 그룹 별칭 지원 (grade1 → 1학년전체)

**이점**:
- JSON만 수정하면 장치/그룹 자동 반영
- 유지보수성 대폭 향상
- 확장성 증가

#### 🔊 오디오 시스템 개선

**TTS 엔진**:
- gTTS 우선 사용 (Google TTS)
- 자연스러운 한국어 발음
- pyttsx3 파일 저장 안정성 개선

**오디오 처리**:
- ✓ 정규화: ffmpeg loudnorm (-12.0 dBFS)
- ✓ 조합: 시작음 + 메인 + 끝음
- ✓ 재생: VLC + ALSA
- ✓ Python 3.13 완전 호환

#### 📊 테스트 완료

**기능 테스트**:
- ✅ 오디오 재생 (VLC + ALSA)
- ✅ 오디오 조합 (pydub)
- ✅ 오디오 정규화 (ffmpeg)
- ✅ TTS 음성 합성 (gTTS)
- ✅ 방송 시스템 통합
- ✅ 모둠12 장비 방송 성공

**Docker 테스트**:
- ✅ 이미지 빌드 성공
- ✅ 컨테이너 실행 성공
- ✅ 네트워크 통신 정상
- ✅ 오디오 출력 정상
- ✅ 방송 기능 전체 작동

---

## 📈 통계

### 코드 변경
- **커밋 2개**: 라즈베리파이 마이그레이션 + Docker 지원
- **파일 변경**: 75개
- **추가**: 964줄
- **삭제**: 253,501줄

### 패키지 설치
- **시스템**: 6개 (VLC, FFmpeg, espeak 등)
- **Python**: 50+ 개 (모두 자동 설치)

### 기능
- **장치 수**: 64개 (4행 16열)
- **실제 장치**: 42개
- **자동 그룹**: 5개
- **TTS 엔진**: 3개 (gTTS 우선)

---

## 🎯 다음 버전 계획

### v1.1.0 (예정)
- [ ] 웹 UI 개선 (Vue.js/React)
- [ ] 실시간 모니터링 (WebSocket)
- [ ] MeloTTS 고품질 TTS
- [ ] 모바일 앱 지원
- [ ] 통계 및 분석 기능

### v1.2.0 (예정)
- [ ] 다중 서버 지원
- [ ] 클라우드 백업
- [ ] AI 음성 합성
- [ ] 음성 인식 기능

---

## 🤝 기여자

- **BMBC** - 초기 개발 및 라즈베리파이 마이그레이션

---

**최종 업데이트**: 2025-10-17
**플랫폼**: Raspberry Pi (Debian Trixie, ARM64)
**버전**: 1.0.0

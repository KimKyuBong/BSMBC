# 방송 프리뷰 시스템 명세서

## 📋 개요

방송 요청 전에 프리뷰를 통해 내용을 확인하고 승인/거부할 수 있는 시스템입니다. 실제 방송과 동일한 형태(시작 신호음 + 메인 오디오 + 끝 신호음)로 미리 들어볼 수 있습니다.

---

## 🎵 프리뷰 시스템 동작 원리

### 1. 프리뷰 생성 과정
```
방송 요청 → 프리뷰 생성 → 사용자 확인 → 승인/거부 → 실제 방송
```

### 2. 프리뷰 오디오 구성
- **시작 신호음** (도미솔도) + **메인 오디오** + **끝 신호음** (도솔미도)
- 실제 방송과 동일한 형태로 미리 들어볼 수 있습니다

### 3. 프리뷰 ID 생성 규칙
- 형식: `preview_YYYYMMDD_HHMMSS_HASH`
- 예시: `preview_20250628_175529_6b39beaf`

---

## 🔧 기술 요구사항

### 필수 소프트웨어
- **FFmpeg**: 오디오 파일 처리 및 신호음 결합
- **pydub**: Python 오디오 처리 라이브러리
- **FastAPI**: 웹 API 서버

### FFmpeg 설치 경로
```
C:\Users\bssmBroadcast\BSMBC\bsbc\ffmpeg\ffmpeg-2025-06-26-git-09cd38e9d5-full_build\bin\
├── ffmpeg.exe
├── ffprobe.exe
└── ffplay.exe
```

---

## 📡 API 엔드포인트

### 1. 텍스트 방송 프리뷰 생성

#### 엔드포인트
```
POST /api/broadcast/text
```

#### 요청
- **Content-Type**: `multipart/form-data`
- **파라미터**:
  - `text` (필수): 방송할 텍스트
  - `target_rooms` (선택): 방송할 방 번호 (쉼표로 구분, 예: "101,102,315")
  - `language` (선택): 텍스트 언어 (기본값: "ko")
  - `auto_off` (선택): 방송 후 자동으로 장치 끄기 (기본값: true)

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "status": "preview_ready",
  "preview_info": {
    "preview_id": "preview_20250628_175529_6b39beaf",
    "job_type": "text",
    "params": {
      "text": "315방 학생 여러분 안녕하세요...",
      "target_devices": ["3-15"],
      "end_devices": ["3-15"],
      "language": "ko"
    },
    "preview_path": "c:\\Users\\bssmBroadcast\\BSMBC\\bsbc\\data\\audio\\previews\\preview_20250628_175529_6b39beaf.mp3",
    "preview_url": "/api/broadcast/preview/preview_20250628_175529_6b39beaf.mp3",
    "approval_endpoint": "/api/broadcast/approve/preview_20250628_175529_6b39beaf",
    "estimated_duration": 20.1,
    "created_at": "2025-06-28T17:55:29.815524",
    "status": "pending"
  },
  "message": "텍스트 방송 프리뷰가 생성되었습니다. 확인 후 승인해주세요.",
  "instructions": {
    "preview_id": "preview_20250628_175529_6b39beaf",
    "listen_preview": "GET /api/broadcast/preview/audio/preview_20250628_175529_6b39beaf.mp3",
    "approve_preview": "POST /api/broadcast/preview/approve/preview_20250628_175529_6b39beaf",
    "reject_preview": "POST /api/broadcast/preview/reject/preview_20250628_175529_6b39beaf",
    "check_all_previews": "GET /api/broadcast/previews"
  },
  "timestamp": "2025-06-28T17:55:29.949920"
}
```

---

### 2. 오디오 방송 프리뷰 생성

#### 엔드포인트
```
POST /api/broadcast/audio
```

#### 요청
- **Content-Type**: `multipart/form-data`
- **파라미터**:
  - `audio_file` (필수): 방송할 오디오 파일 (MP3, WAV 등)
  - `target_rooms` (선택): 방송할 방 번호 (쉼표로 구분)
  - `auto_off` (선택): 방송 후 자동으로 장치 끄기 (기본값: true)

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "status": "preview_ready",
  "preview_info": {
    "preview_id": "preview_20250628_175352_5a61ffff",
    "job_type": "audio",
    "params": {
      "audio_path": "data/audio/preview_audio_20250628_175352.mp3",
      "target_devices": ["1-1", "1-2"],
      "end_devices": ["1-1", "1-2"]
    },
    "preview_path": "c:\\Users\\bssmBroadcast\\BSMBC\\bsbc\\data\\audio\\previews\\preview_20250628_175352_5a61ffff.mp3",
    "preview_url": "/api/broadcast/preview/preview_20250628_175352_5a61ffff.mp3",
    "approval_endpoint": "/api/broadcast/approve/preview_20250628_175352_5a61ffff",
    "estimated_duration": 45.2,
    "created_at": "2025-06-28T17:53:52.123456",
    "status": "pending"
  },
  "message": "오디오 방송 프리뷰가 생성되었습니다. 확인 후 승인해주세요.",
  "instructions": {
    "preview_id": "preview_20250628_175352_5a61ffff",
    "listen_preview": "GET /api/broadcast/preview/audio/preview_20250628_175352_5a61ffff.mp3",
    "approve_preview": "POST /api/broadcast/preview/approve/preview_20250628_175352_5a61ffff",
    "reject_preview": "POST /api/broadcast/preview/reject/preview_20250628_175352_5a61ffff",
    "check_all_previews": "GET /api/broadcast/previews"
  },
  "timestamp": "2025-06-28T17:53:52.949920"
}
```

---

### 3. 프리뷰 승인

#### 엔드포인트
```
POST /api/broadcast/preview/approve/{preview_id}
```

#### 요청
- **Method**: POST
- **Path Parameter**: `preview_id` - 승인할 프리뷰 ID

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "preview_id": "preview_20250628_175529_6b39beaf",
  "broadcast_result": {
    "status": "queued",
    "queue_size": 1,
    "queue_position": 1,
    "estimated_start_time": "17:55:39",
    "estimated_duration": 20.1,
    "message": "방송이 대기열 1번째에 추가되었습니다."
  },
  "message": "프리뷰가 승인되어 방송 큐에 추가되었습니다.",
  "timestamp": "2025-06-28T17:55:39.180716"
}
```

---

### 4. 프리뷰 거부

#### 엔드포인트
```
POST /api/broadcast/preview/reject/{preview_id}
```

#### 요청
- **Method**: POST
- **Path Parameter**: `preview_id` - 거부할 프리뷰 ID

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "preview_id": "preview_20250628_175529_6b39beaf",
  "message": "프리뷰가 거부되었습니다.",
  "timestamp": "2025-06-28T17:55:39.180716"
}
```

---

### 5. 프리뷰 정보 조회

#### 엔드포인트
```
GET /api/broadcast/preview/{preview_id}
```

#### 요청
- **Method**: GET
- **Path Parameter**: `preview_id` - 조회할 프리뷰 ID

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "preview_info": {
    "preview_id": "preview_20250628_175529_6b39beaf",
    "job_type": "text",
    "params": {
      "text": "315방 학생 여러분 안녕하세요...",
      "target_devices": ["3-15"],
      "end_devices": ["3-15"],
      "language": "ko"
    },
    "preview_path": "c:\\Users\\bssmBroadcast\\BSMBC\\bsbc\\data\\audio\\previews\\preview_20250628_175529_6b39beaf.mp3",
    "preview_url": "/api/broadcast/preview/preview_20250628_175529_6b39beaf.mp3",
    "approval_endpoint": "/api/broadcast/approve/preview_20250628_175529_6b39beaf",
    "estimated_duration": 20.1,
    "created_at": "2025-06-28T17:55:29.815524",
    "status": "pending"
  },
  "timestamp": "2025-06-28T17:55:39.180716"
}
```

---

### 6. 모든 프리뷰 조회

#### 엔드포인트
```
GET /api/broadcast/previews
```

#### 요청
- **Method**: GET
- **파라미터**: 없음

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "previews": [
    {
      "preview_id": "preview_20250628_175352_5a61ffff",
      "job_type": "text",
      "estimated_duration": 20.1,
      "created_at": "2025-06-28T17:55:29.815524",
      "status": "pending"
    }
  ],
  "count": 1,
  "timestamp": "2025-06-28T17:55:39.180716"
}
```

---

### 7. 프리뷰 오디오 파일 제공

#### 엔드포인트
```
GET /api/broadcast/preview/audio/{preview_id}.mp3
```

#### 요청
- **Method**: GET
- **Path Parameter**: `preview_id` - 다운로드할 프리뷰 ID

#### 성공 응답 (200 OK)
- **Content-Type**: `audio/mpeg`
- **Body**: MP3 오디오 파일 바이너리 데이터

---

## 📁 파일 구조

### 프리뷰 파일 저장 위치
```
C:\Users\bssmBroadcast\BSMBC\bsbc\data\audio\previews\
├── preview_20250628_175529_6b39beaf.mp3  (137.2KB - 신호음 포함)
├── preview_20250628_175352_5a61ffff.mp3  (128.0KB - 신호음 포함)
└── ...
```

### 신호음 파일 위치
```
C:\Users\bssmBroadcast\BSMBC\bsbc\data\
├── start.mp3  (시작 신호음 - 도미솔도)
└── end.mp3    (끝 신호음 - 도솔미도)
```

---

## 🧪 테스트 결과

### 성공적인 프리뷰 생성 사례
- **315방 테스트**: 137.2KB 프리뷰 생성 (신호음 포함)
- **101,102방 테스트**: 128.0KB 프리뷰 생성 (신호음 포함)
- **프리뷰 승인**: 방송 큐에 성공적으로 추가
- **오디오 다운로드**: MP3 파일 정상 다운로드

### 파일 크기 비교
- **신호음 없음**: 14KB ~ 52KB
- **신호음 포함**: 128KB ~ 140KB

---

## ⚠️ 오류 코드

| HTTP 상태 코드 | 설명 |
|---------------|------|
| 200 | 성공 |
| 400 | 잘못된 요청 (활성화된 방 없음, 파라미터 오류 등) |
| 404 | 프리뷰를 찾을 수 없음 |
| 500 | 서버 내부 오류 (프리뷰 생성 실패, 승인/거부 실패 등) |

---

## 🔄 사용 워크플로우

### 1. 프리뷰 생성
```bash
curl -X POST "http://localhost:8000/api/broadcast/text" \
  -F "text=315방 학생 여러분 안녕하세요." \
  -F "target_rooms=315"
```

### 2. 프리뷰 확인
```bash
# 프리뷰 목록 조회
curl -X GET "http://localhost:8000/api/broadcast/previews"

# 프리뷰 오디오 다운로드
curl -X GET "http://localhost:8000/api/broadcast/preview/audio/preview_20250628_175529_6b39beaf.mp3" \
  -o preview.mp3
```

### 3. 프리뷰 승인
```bash
curl -X POST "http://localhost:8000/api/broadcast/preview/approve/preview_20250628_175529_6b39beaf"
```

### 4. 방송 큐 확인
```bash
curl -X GET "http://localhost:8000/api/broadcast/queue"
```

---

## 📝 주의사항

1. **FFmpeg 필수**: 프리뷰 생성에 FFmpeg가 반드시 필요합니다
2. **파일 관리**: 프리뷰 파일은 승인/거부 후 자동으로 정리됩니다
3. **동시성**: 여러 프리뷰를 동시에 생성할 수 있습니다
4. **메모리**: 프리뷰는 메모리에 저장되므로 서버 재시작 시 초기화됩니다
5. **파일 크기**: 신호음이 포함된 프리뷰는 더 큰 파일 크기를 가집니다

---

## 🎯 성능 지표

- **프리뷰 생성 시간**: 평균 0.5~1초
- **파일 크기**: 신호음 포함 시 128KB~140KB
- **지원 형식**: MP3, WAV
- **동시 처리**: 다중 프리뷰 생성 가능

---

*문서 버전: 1.0*  
*최종 업데이트: 2025-06-28*  
*작성자: AI Assistant* 
# 방송 프리뷰 시스템 API 명세서

## 개요
방송 요청 전에 프리뷰를 통해 내용을 확인하고 승인/거부할 수 있는 시스템입니다.

---

## 프리뷰 시스템 동작 원리

### 1. 프리뷰 생성 과정
```
방송 요청 → 프리뷰 생성 → 사용자 확인 → 승인/거부 → 실제 방송
```

### 2. 프리뷰 오디오 구성
- **시작 신호음** (도미솔도) + **메인 오디오** + **끝 신호음** (도솔미도)
- 실제 방송과 동일한 형태로 미리 들어볼 수 있습니다

### 3. 프리뷰 ID 생성 규칙
- 형식: `preview_YYYYMMDD_HHMMSS_HASH`
- 예시: `preview_20250628_143000_a1b2c3d4`

---

## API 엔드포인트

### 1. 오디오 방송 프리뷰 생성

#### 엔드포인트
```
POST /api/broadcast/preview/audio
```

#### 설명
오디오 파일을 업로드하여 방송 프리뷰를 생성합니다.

#### 요청
- **Content-Type**: `multipart/form-data`
- **파라미터**:
  - `audio_file` (필수): 방송할 오디오 파일 (MP3, WAV 등)
  - `target_rooms` (선택): 방송할 방 번호 (쉼표로 구분, 예: "101,102,201")
  - `auto_off` (선택): 방송 후 자동으로 장치 끄기 (기본값: true)

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "status": "preview_ready",
  "preview_info": {
    "preview_id": "preview_20250628_143000_a1b2c3d4",
    "job_type": "audio",
    "preview_url": "/api/broadcast/preview/preview_20250628_143000_a1b2c3d4.mp3",
    "approval_endpoint": "/api/broadcast/approve/preview_20250628_143000_a1b2c3d4",
    "estimated_duration": 45.2,
    "created_at": "2025-06-28T14:30:00",
    "status": "pending"
  },
  "message": "오디오 방송 프리뷰가 생성되었습니다. 확인 후 승인해주세요.",
  "timestamp": "2025-06-28T14:30:00.123456"
}
```

#### 오류 응답 (400 Bad Request)
```json
{
  "detail": "활성화된 방이 없습니다. 먼저 방을 활성화하세요."
}
```

#### 오류 응답 (500 Internal Server Error)
```json
{
  "detail": "오디오 프리뷰 생성 실패: 오류 메시지"
}
```

---

### 2. 텍스트 방송 프리뷰 생성

#### 엔드포인트
```
POST /api/broadcast/preview/text
```

#### 설명
텍스트를 입력하여 TTS 방송 프리뷰를 생성합니다.

#### 요청
- **Content-Type**: `multipart/form-data`
- **파라미터**:
  - `text` (필수): 방송할 텍스트
  - `target_rooms` (선택): 방송할 방 번호 (쉼표로 구분)
  - `language` (선택): 텍스트 언어 (기본값: "ko")
  - `auto_off` (선택): 방송 후 자동으로 장치 끄기 (기본값: true)

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "status": "preview_ready",
  "preview_info": {
    "preview_id": "preview_20250628_143000_b2c3d4e5",
    "job_type": "text",
    "preview_url": "/api/broadcast/preview/preview_20250628_143000_b2c3d4e5.mp3",
    "approval_endpoint": "/api/broadcast/approve/preview_20250628_143000_b2c3d4e5",
    "estimated_duration": 8.5,
    "created_at": "2025-06-28T14:30:00",
    "status": "pending"
  },
  "message": "텍스트 방송 프리뷰가 생성되었습니다. 확인 후 승인해주세요.",
  "timestamp": "2025-06-28T14:30:00.123456"
}
```

---

### 3. 프리뷰 승인

#### 엔드포인트
```
POST /api/broadcast/preview/approve/{preview_id}
```

#### 설명
프리뷰를 승인하여 실제 방송 큐에 추가합니다.

#### 요청
- **Method**: POST
- **Path Parameter**: `preview_id` - 승인할 프리뷰 ID

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "preview_id": "preview_20250628_143000_a1b2c3d4",
  "broadcast_result": {
    "status": "queued",
    "queue_size": 2,
    "queue_position": 2,
    "estimated_start_time": "14:31:30",
    "estimated_duration": 45.2,
    "message": "방송이 대기열 2번째에 추가되었습니다."
  },
  "message": "프리뷰가 승인되어 방송 큐에 추가되었습니다.",
  "timestamp": "2025-06-28T14:30:05.123456"
}
```

#### 오류 응답 (400 Bad Request)
```json
{
  "detail": "프리뷰 승인 실패"
}
```

---

### 4. 프리뷰 거부

#### 엔드포인트
```
POST /api/broadcast/preview/reject/{preview_id}
```

#### 설명
프리뷰를 거부하여 삭제합니다.

#### 요청
- **Method**: POST
- **Path Parameter**: `preview_id` - 거부할 프리뷰 ID

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "preview_id": "preview_20250628_143000_a1b2c3d4",
  "message": "프리뷰가 거부되었습니다.",
  "timestamp": "2025-06-28T14:30:05.123456"
}
```

---

### 5. 프리뷰 정보 조회

#### 엔드포인트
```
GET /api/broadcast/preview/{preview_id}
```

#### 설명
특정 프리뷰의 상세 정보를 조회합니다.

#### 요청
- **Method**: GET
- **Path Parameter**: `preview_id` - 조회할 프리뷰 ID

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "preview_info": {
    "preview_id": "preview_20250628_143000_a1b2c3d4",
    "job_type": "audio",
    "params": {
      "audio_path": "data/audio/preview_audio_20250628_143000.mp3",
      "target_devices": ["1-1", "1-2"],
      "end_devices": ["1-1", "1-2"]
    },
    "preview_path": "data/audio/previews/preview_20250628_143000_a1b2c3d4.mp3",
    "preview_url": "/api/broadcast/preview/preview_20250628_143000_a1b2c3d4.mp3",
    "approval_endpoint": "/api/broadcast/approve/preview_20250628_143000_a1b2c3d4",
    "estimated_duration": 45.2,
    "created_at": "2025-06-28T14:30:00",
    "status": "pending"
  },
  "timestamp": "2025-06-28T14:30:05.123456"
}
```

#### 오류 응답 (404 Not Found)
```json
{
  "detail": "프리뷰를 찾을 수 없습니다."
}
```

---

### 6. 모든 프리뷰 조회

#### 엔드포인트
```
GET /api/broadcast/previews
```

#### 설명
현재 대기 중인 모든 프리뷰 목록을 조회합니다.

#### 요청
- **Method**: GET
- **파라미터**: 없음

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "previews": [
    {
      "preview_id": "preview_20250628_143000_a1b2c3d4",
      "job_type": "audio",
      "estimated_duration": 45.2,
      "created_at": "2025-06-28T14:30:00",
      "status": "pending"
    },
    {
      "preview_id": "preview_20250628_143100_b2c3d4e5",
      "job_type": "text",
      "estimated_duration": 8.5,
      "created_at": "2025-06-28T14:31:00",
      "status": "pending"
    }
  ],
  "count": 2,
  "timestamp": "2025-06-28T14:30:05.123456"
}
```

---

### 7. 프리뷰 오디오 파일 제공

#### 엔드포인트
```
GET /api/broadcast/preview/audio/{preview_id}.mp3
```

#### 설명
프리뷰 오디오 파일을 다운로드할 수 있도록 제공합니다.

#### 요청
- **Method**: GET
- **Path Parameter**: `preview_id` - 다운로드할 프리뷰 ID

#### 성공 응답 (200 OK)
- **Content-Type**: `audio/mpeg`
- **Body**: MP3 오디오 파일 바이너리 데이터

#### 오류 응답 (404 Not Found)
```json
{
  "detail": "프리뷰를 찾을 수 없습니다."
}
```

---

## 사용 예시

### 1. cURL을 사용한 프리뷰 생성
```bash
# 오디오 프리뷰 생성
curl -X POST "http://localhost:8000/api/broadcast/preview/audio" \
  -F "audio_file=@announcement.mp3" \
  -F "target_rooms=101,102,201" \
  -F "auto_off=true"

# 텍스트 프리뷰 생성
curl -X POST "http://localhost:8000/api/broadcast/preview/text" \
  -F "text=안녕하세요. 방송 테스트입니다." \
  -F "target_rooms=101,102" \
  -F "language=ko"
```

### 2. Python을 사용한 프리뷰 관리
```python
import requests

# 1. 프리뷰 생성
with open('announcement.mp3', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/broadcast/preview/audio',
        files={'audio_file': f},
        data={'target_rooms': '101,102,201'}
    )
    
if response.status_code == 200:
    preview_info = response.json()['preview_info']
    preview_id = preview_info['preview_id']
    
    # 2. 프리뷰 오디오 다운로드
    audio_response = requests.get(
        f'http://localhost:8000/api/broadcast/preview/audio/{preview_id}.mp3'
    )
    
    with open('preview.mp3', 'wb') as f:
        f.write(audio_response.content)
    
    # 3. 프리뷰 승인
    approve_response = requests.post(
        f'http://localhost:8000/api/broadcast/preview/approve/{preview_id}'
    )
    
    if approve_response.status_code == 200:
        print("프리뷰가 승인되어 방송 큐에 추가되었습니다.")
```

### 3. 모든 프리뷰 조회
```python
import requests

response = requests.get('http://localhost:8000/api/broadcast/previews')
if response.status_code == 200:
    data = response.json()
    print(f"대기 중인 프리뷰: {data['count']}개")
    
    for preview in data['previews']:
        print(f"- {preview['preview_id']}: {preview['job_type']} 방송")
```

---

## 주의사항

1. **프리뷰 파일 관리**: 프리뷰 파일은 승인/거부 후 자동으로 정리됩니다
2. **동시성**: 여러 프리뷰를 동시에 생성할 수 있습니다
3. **메모리**: 프리뷰는 메모리에 저장되므로 서버 재시작 시 초기화됩니다
4. **파일 크기**: 큰 오디오 파일의 경우 프리뷰 생성에 시간이 걸릴 수 있습니다
5. **신호음**: 모든 프리뷰에는 시작/끝 신호음이 포함됩니다

---

## 오류 코드

| HTTP 상태 코드 | 설명 |
|---------------|------|
| 200 | 성공 |
| 400 | 잘못된 요청 (활성화된 방 없음, 파라미터 오류 등) |
| 404 | 프리뷰를 찾을 수 없음 |
| 500 | 서버 내부 오류 (프리뷰 생성 실패, 승인/거부 실패 등) | 
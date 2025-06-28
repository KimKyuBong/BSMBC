# BSMBC API 완전 명세서

## 📋 개요

BSMBC 방송 시스템의 모든 API 엔드포인트에 대한 완전한 명세서입니다.

---

## 🔗 기본 정보

### 서버 URL
```
http://localhost:8000
```

### 인증
- **TOTP 토큰**: 2단계 인증 (필수)
- **API 키**: 클라이언트 식별 (필수)

### Content-Type
- **요청**: `multipart/form-data` (파일 업로드), `application/json` (일반)
- **응답**: `application/json`

---

## 📡 API 엔드포인트 목록

### 1. 텍스트 방송 프리뷰 생성
### 2. 오디오 방송 프리뷰 생성
### 3. 프리뷰 승인
### 4. 프리뷰 거부
### 5. 프리뷰 정보 조회
### 6. 모든 프리뷰 조회
### 7. 프리뷰 오디오 다운로드
### 8. 방송 큐 조회
### 9. 방송 큐 상태
### 10. 장치 매트릭스 조회
### 11. 장치 상태 조회
### 12. 시스템 상태 조회

---

## 🎵 방송 API

### 1. 텍스트 방송 프리뷰 생성

#### 엔드포인트
```
POST /api/broadcast/text
```

#### 설명
텍스트를 TTS로 변환하여 프리뷰를 생성합니다.

#### 요청 파라미터
| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| text | string | ✅ | 방송할 텍스트 | "315방 학생 여러분 안녕하세요." |
| target_rooms | string | ❌ | 방송할 방 번호 (쉼표로 구분) | "101,102,315" |
| language | string | ❌ | 텍스트 언어 | "ko" (기본값) |
| auto_off | boolean | ❌ | 방송 후 자동으로 장치 끄기 | true (기본값) |

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

#### 오류 응답 (400 Bad Request)
```json
{
  "success": false,
  "error": "no_active_devices",
  "message": "활성화된 방송 장치가 없습니다.",
  "details": {
    "available_rooms": [],
    "suggested_action": "장치 매트릭스를 확인하거나 장치를 활성화하세요."
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

#### 설명
오디오 파일을 업로드하여 프리뷰를 생성합니다.

#### 요청 파라미터
| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| audio_file | file | ✅ | 방송할 오디오 파일 | MP3, WAV 파일 |
| target_rooms | string | ❌ | 방송할 방 번호 (쉼표로 구분) | "101,102,315" |
| auto_off | boolean | ❌ | 방송 후 자동으로 장치 끄기 | true (기본값) |

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
    "reject_preview": "POST /api/broadcast/preview/reject/preview_20250628_175352_5a61ffff",
    "check_all_previews": "GET /api/broadcast/previews"
  },
  "timestamp": "2025-06-28T17:53:52.949920"
}
```

---

## 👁️ 프리뷰 관리 API

### 3. 프리뷰 승인

#### 엔드포인트
```
POST /api/broadcast/preview/approve/{preview_id}
```

#### 설명
생성된 프리뷰를 승인하여 실제 방송 큐에 추가합니다.

#### Path Parameters
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| preview_id | string | 승인할 프리뷰 ID |

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

#### 설명
생성된 프리뷰를 거부하여 삭제합니다.

#### Path Parameters
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| preview_id | string | 거부할 프리뷰 ID |

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

#### 설명
특정 프리뷰의 상세 정보를 조회합니다.

#### Path Parameters
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| preview_id | string | 조회할 프리뷰 ID |

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

#### 설명
현재 생성된 모든 프리뷰 목록을 조회합니다.

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

### 7. 프리뷰 오디오 다운로드

#### 엔드포인트
```
GET /api/broadcast/preview/audio/{preview_id}.mp3
```

#### 설명
프리뷰 오디오 파일을 다운로드합니다.

#### Path Parameters
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| preview_id | string | 다운로드할 프리뷰 ID |

#### 성공 응답 (200 OK)
- **Content-Type**: `audio/mpeg`
- **Body**: MP3 오디오 파일 바이너리 데이터

---

## 📋 큐 관리 API

### 8. 방송 큐 조회

#### 엔드포인트
```
GET /api/broadcast/queue
```

#### 설명
현재 방송 큐의 상태를 조회합니다.

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "queue_info": {
    "queue_size": 1,
    "current_broadcast": null,
    "pending_broadcasts": [
      {
        "id": "broadcast_20250628_175539_123456",
        "type": "text",
        "target_devices": ["3-15"],
        "estimated_duration": 20.1,
        "created_at": "2025-06-28T17:55:39.180716",
        "status": "queued",
        "queue_position": 1
      }
    ],
    "completed_broadcasts": []
  },
  "timestamp": "2025-06-28T17:55:39.180716"
}
```

---

### 9. 방송 큐 상태

#### 엔드포인트
```
GET /api/broadcast/queue/status
```

#### 설명
방송 큐의 간단한 상태 정보를 조회합니다.

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "status": {
    "queue_size": 1,
    "is_broadcasting": false,
    "estimated_wait_time": 0,
    "message": "대기열에 1개의 방송이 있습니다."
  },
  "timestamp": "2025-06-28T17:55:39.180716"
}
```

---

## 🏢 장치 관리 API

### 10. 장치 매트릭스 조회

#### 엔드포인트
```
GET /api/devices/matrix
```

#### 설명
모든 장치의 매트릭스 정보를 조회합니다.

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "device_matrix": {
    "buildings": {
      "1": {
        "floors": {
          "1": {
            "rooms": {
              "1": {
                "device_id": "1-1",
                "name": "1층 1호실",
                "type": "speaker",
                "status": "online"
              }
            }
          }
        }
      }
    },
    "total_devices": 150,
    "online_devices": 145,
    "offline_devices": 5
  },
  "timestamp": "2025-06-28T17:55:39.180716"
}
```

---

### 11. 장치 상태 조회

#### 엔드포인트
```
GET /api/devices/status
```

#### 설명
모든 장치의 현재 상태를 조회합니다.

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "device_status": {
    "online": 145,
    "offline": 5,
    "busy": 0,
    "error": 0,
    "total": 150,
    "details": {
      "online_devices": ["1-1", "1-2", "3-15"],
      "offline_devices": ["2-10", "2-11"],
      "busy_devices": [],
      "error_devices": []
    }
  },
  "timestamp": "2025-06-28T17:55:39.180716"
}
```

---

## 🔧 시스템 관리 API

### 12. 시스템 상태 조회

#### 엔드포인트
```
GET /api/system/status
```

#### 설명
시스템의 전반적인 상태를 조회합니다.

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "system_status": {
    "server": {
      "status": "running",
      "uptime": "2 days, 5 hours, 30 minutes",
      "version": "2.0.0"
    },
    "services": {
      "broadcast_manager": "running",
      "scheduler": "running",
      "device_monitor": "running"
    },
    "resources": {
      "cpu_usage": 15.2,
      "memory_usage": 45.8,
      "disk_usage": 23.1
    },
    "network": {
      "active_connections": 5,
      "total_requests": 1250,
      "error_rate": 0.1
    }
  },
  "timestamp": "2025-06-28T17:55:39.180716"
}
```

---

## 장치 상태 복원 기능

### 장치 상태 복원 기능 활성화/비활성화

#### 엔드포인트
```
POST /api/broadcast/device-restore/set
```

#### 설명
방송 후 장치 상태를 원래대로 복원하는 기능을 활성화하거나 비활성화합니다.

#### 요청
- **Content-Type**: `application/x-www-form-urlencoded`
- **파라미터**:
  - `enabled` (필수): `true` (활성화) 또는 `false` (비활성화)

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "restore_enabled": true,
  "message": "장치 상태 복원 기능이 활성화되었습니다.",
  "timestamp": "2025-06-28T14:30:00.123456"
}
```

---

### 장치 상태 복원 기능 정보 조회

#### 엔드포인트
```
GET /api/broadcast/device-restore/info
```

#### 설명
현재 장치 상태 복원 기능의 설정과 저장된 상태 정보를 조회합니다.

#### 요청
- **Method**: GET
- **파라미터**: 없음

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "info": {
    "restore_enabled": true,
    "backup_count": 2,
    "backup_devices": ["1-1", "1-2"],
    "backup_states": {
      "1-1": true,
      "1-2": false
    }
  },
  "timestamp": "2025-06-28T14:30:00.123456"
}
```

---

### 저장된 장치 상태 백업 데이터 정리

#### 엔드포인트
```
POST /api/broadcast/device-restore/clear
```

#### 설명
저장된 장치 상태 백업 데이터를 모두 정리합니다.

#### 요청
- **Method**: POST
- **파라미터**: 없음

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "message": "저장된 장치 상태 백업 데이터가 정리되었습니다.",
  "timestamp": "2025-06-28T14:30:00.123456"
}
```

---

## ⚠️ 오류 코드

### HTTP 상태 코드

| 코드 | 설명 |
|------|------|
| 200 | 성공 |
| 400 | 잘못된 요청 |
| 401 | 인증 실패 |
| 403 | 권한 없음 |
| 404 | 리소스를 찾을 수 없음 |
| 500 | 서버 내부 오류 |

### 오류 응답 형식
```json
{
  "success": false,
  "error": "error_code",
  "message": "오류 메시지",
  "details": {
    "additional_info": "추가 정보"
  },
  "timestamp": "2025-06-28T17:55:39.180716"
}
```

### 주요 오류 코드

| 오류 코드 | 설명 | 해결 방법 |
|----------|------|----------|
| `no_active_devices` | 활성화된 장치가 없음 | 장치 매트릭스 확인 |
| `preview_not_found` | 프리뷰를 찾을 수 없음 | 프리뷰 ID 확인 |
| `invalid_file_format` | 지원하지 않는 파일 형식 | MP3, WAV 파일 사용 |
| `file_too_large` | 파일이 너무 큼 | 50MB 이하 파일 사용 |
| `authentication_failed` | 인증 실패 | TOTP 토큰 확인 |

---

## 🔄 사용 예시

### cURL 예시

#### 1. 텍스트 방송 프리뷰 생성
```bash
curl -X POST "http://localhost:8000/api/broadcast/text" \
  -F "text=315방 학생 여러분 안녕하세요." \
  -F "target_rooms=315"
```

#### 2. 프리뷰 승인
```bash
curl -X POST "http://localhost:8000/api/broadcast/preview/approve/preview_20250628_175529_6b39beaf"
```

#### 3. 프리뷰 오디오 다운로드
```bash
curl -X GET "http://localhost:8000/api/broadcast/preview/audio/preview_20250628_175529_6b39beaf.mp3" \
  -o preview.mp3
```

#### 4. 큐 상태 확인
```bash
curl -X GET "http://localhost:8000/api/broadcast/queue"
```

### Python 예시

```python
import requests

# 텍스트 방송 프리뷰 생성
response = requests.post(
    "http://localhost:8000/api/broadcast/text",
    files={"text": (None, "315방 학생 여러분 안녕하세요.")},
    data={"target_rooms": "315"}
)

if response.status_code == 200:
    data = response.json()
    preview_id = data["preview_info"]["preview_id"]
    
    # 프리뷰 승인
    approve_response = requests.post(
        f"http://localhost:8000/api/broadcast/preview/approve/{preview_id}"
    )
    
    if approve_response.status_code == 200:
        print("방송이 큐에 추가되었습니다!")
```

---

## 📝 주의사항

1. **인증 필수**: 모든 API 호출에 TOTP 토큰과 API 키가 필요합니다
2. **파일 크기**: 오디오 파일은 50MB 이하여야 합니다
3. **동시 요청**: 너무 많은 동시 요청을 피하세요
4. **오류 처리**: 항상 응답 상태 코드를 확인하세요
5. **타임아웃**: 긴 작업은 적절한 타임아웃을 설정하세요

---

*문서 버전: 2.0*  
*최종 업데이트: 2025-06-28*  
*작성자: AI Assistant* 
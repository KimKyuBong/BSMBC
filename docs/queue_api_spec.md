# 방송 큐 현황 API 명세서

## 개요
방송 시스템의 큐 현황을 확인할 수 있는 API 엔드포인트들입니다.

---

## 1. 큐 현황 조회

### 엔드포인트
```
GET /api/broadcast/queue
```

### 설명
현재 방송 큐의 상태와 대기 중인 작업들을 JSON 형태로 반환합니다.

### 요청
- **Method**: GET
- **인증**: 불필요
- **파라미터**: 없음

### 응답

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "queue_status": {
    "is_playing": boolean,
    "current_broadcast": {
      "start_time": "HH:MM:SS",
      "estimated_duration": number,
      "elapsed_time": number,
      "remaining_time": number,
      "progress_percent": number
    },
    "queue_size": number,
    "queue_items": [
      {
        "position": number,
        "job_type": "audio" | "text",
        "estimated_duration": number,
        "estimated_start_time": "HH:MM:SS",
        "created_at": "HH:MM:SS",
        "audio_path": "string",
        "target_devices": ["string"],
        "text": "string",
        "language": "string"
      }
    ]
  },
  "timestamp": "ISO 8601 datetime"
}
```

#### 응답 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `success` | boolean | 요청 성공 여부 |
| `queue_status.is_playing` | boolean | 현재 재생 중인지 여부 |
| `queue_status.current_broadcast` | object | 현재 재생 중인 방송 정보 (재생 중이 아닐 때는 null) |
| `queue_status.current_broadcast.start_time` | string | 방송 시작 시간 (HH:MM:SS) |
| `queue_status.current_broadcast.estimated_duration` | number | 예상 총 재생 시간 (초) |
| `queue_status.current_broadcast.elapsed_time` | number | 경과 시간 (초) |
| `queue_status.current_broadcast.remaining_time` | number | 남은 시간 (초) |
| `queue_status.current_broadcast.progress_percent` | number | 진행률 (%) |
| `queue_status.queue_size` | number | 대기열에 있는 작업 수 |
| `queue_status.queue_items` | array | 대기열 작업 목록 |
| `queue_status.queue_items[].position` | number | 큐에서의 순서 (1부터 시작) |
| `queue_status.queue_items[].job_type` | string | 작업 유형 ("audio" 또는 "text") |
| `queue_status.queue_items[].estimated_duration` | number | 예상 재생 시간 (초) |
| `queue_status.queue_items[].estimated_start_time` | string | 예상 시작 시간 (HH:MM:SS) |
| `queue_status.queue_items[].created_at` | string | 작업 생성 시간 (HH:MM:SS) |
| `queue_status.queue_items[].audio_path` | string | 오디오 파일 경로 (audio 타입만) |
| `queue_status.queue_items[].target_devices` | array | 대상 장치 목록 |
| `queue_status.queue_items[].text` | string | 방송할 텍스트 (text 타입만) |
| `queue_status.queue_items[].language` | string | 언어 코드 (text 타입만) |
| `timestamp` | string | 응답 생성 시간 (ISO 8601) |

#### 오류 응답 (500 Internal Server Error)
```json
{
  "detail": "큐 현황 확인 실패: 오류 메시지"
}
```

### 사용 예시

#### cURL
```bash
curl -X GET "http://localhost:8000/api/broadcast/queue"
```

#### Python
```python
import requests

response = requests.get("http://localhost:8000/api/broadcast/queue")
if response.status_code == 200:
    data = response.json()
    print(f"현재 재생 중: {data['queue_status']['is_playing']}")
    print(f"대기열 크기: {data['queue_status']['queue_size']}")
    
    if data['queue_status']['current_broadcast']:
        current = data['queue_status']['current_broadcast']
        print(f"진행률: {current['progress_percent']}%")
        print(f"남은 시간: {current['remaining_time']}초")
```

---

## 2. 큐 현황 콘솔 출력

### 엔드포인트
```
POST /api/broadcast/queue/print
```

### 설명
큐 현황을 서버 콘솔에 보기 좋게 출력합니다. 로그 모니터링용으로 사용합니다.

### 요청
- **Method**: POST
- **인증**: 불필요
- **파라미터**: 없음

### 응답

#### 성공 응답 (200 OK)
```json
{
  "success": true,
  "message": "큐 현황이 콘솔에 출력되었습니다.",
  "timestamp": "ISO 8601 datetime"
}
```

#### 콘솔 출력 예시
```
============================================================
🎵 방송 큐 현황
============================================================
▶️  현재 재생 중:
   시작 시간: 14:30:15
   경과 시간: 12.3초 / 45.2초
   남은 시간: 32.9초
   진행률: 27.2%

📋 대기열: 3개 작업

   1. AUDIO 방송
      예상 시작: 14:31:00
      예상 길이: 30.0초
      생성 시간: 14:29:45
      파일: data/audio/broadcast_20250628_160717.mp3
      대상 장치: ['1-1', '1-2']

   2. TEXT 방송
      예상 시작: 14:31:30
      예상 길이: 8.5초
      생성 시간: 14:30:00
      텍스트: 안녕하세요. 방송 테스트입니다...
      언어: ko
      대상 장치: ['2-1', '2-2']

   3. AUDIO 방송
      예상 시작: 14:31:38
      예상 길이: 120.0초
      생성 시간: 14:30:10
      파일: data/audio/announcement.wav
      대상 장치: ['1-1', '1-2', '1-3', '1-4']
============================================================
```

#### 오류 응답 (500 Internal Server Error)
```json
{
  "detail": "큐 현황 출력 실패: 오류 메시지"
}
```

### 사용 예시

#### cURL
```bash
curl -X POST "http://localhost:8000/api/broadcast/queue/print"
```

#### Python
```python
import requests

response = requests.post("http://localhost:8000/api/broadcast/queue/print")
if response.status_code == 200:
    print("큐 현황이 콘솔에 출력되었습니다.")
```

---

## 큐 시스템 동작 원리

### 1. 큐 구조
- **FIFO (First In, First Out)**: 먼저 들어온 작업이 먼저 실행
- **단일 실행**: 한 번에 하나의 방송만 실행
- **자동 연속**: 현재 방송 완료 후 다음 큐 작업 자동 실행

### 2. 작업 타입
- **audio**: 오디오 파일 방송
- **text**: TTS 텍스트 방송 (내부적으로 오디오로 변환)

### 3. 예상 시작 시간 계산
```
현재 시간 + (현재 방송 남은 시간) + (큐 앞 작업들의 예상 시간 합)
```

### 4. 큐 상태 변화
1. **방송 요청** → 큐에 작업 추가
2. **현재 재생 중** → 큐에서 대기
3. **재생 완료** → 다음 작업 자동 실행
4. **큐 비움** → 대기 중인 작업 없음

---

## 모니터링 활용 예시

### 1. 실시간 큐 모니터링
```python
import requests
import time

def monitor_queue():
    while True:
        try:
            response = requests.get("http://localhost:8000/api/broadcast/queue")
            if response.status_code == 200:
                data = response.json()
                status = data['queue_status']
                
                print(f"재생 중: {status['is_playing']}")
                print(f"대기열: {status['queue_size']}개")
                
                if status['current_broadcast']:
                    current = status['current_broadcast']
                    print(f"진행률: {current['progress_percent']}%")
                
                for item in status['queue_items']:
                    print(f"대기: {item['job_type']} - {item['estimated_start_time']}")
            
        except Exception as e:
            print(f"모니터링 오류: {e}")
        
        time.sleep(5)  # 5초마다 확인

# 모니터링 시작
monitor_queue()
```

### 2. 큐 상태 알림
```python
import requests
import json

def check_queue_status():
    response = requests.get("http://localhost:8000/api/broadcast/queue")
    if response.status_code == 200:
        data = response.json()
        status = data['queue_status']
        
        # 큐가 비어있을 때 알림
        if status['queue_size'] == 0 and not status['is_playing']:
            print("🎵 모든 방송이 완료되었습니다!")
        
        # 큐가 길 때 알림
        elif status['queue_size'] > 5:
            print(f"⚠️ 대기열이 길어졌습니다: {status['queue_size']}개 작업")
        
        return status
    
    return None
```

---

## 주의사항

1. **큐 순서**: 작업은 요청 순서대로 처리됩니다
2. **예상 시간**: 실제 재생 시간과 다를 수 있습니다
3. **동시성**: 한 번에 하나의 방송만 실행됩니다
4. **오류 처리**: 작업 실행 중 오류 발생 시 다음 작업으로 넘어갑니다
5. **메모리**: 큐는 메모리에 저장되므로 서버 재시작 시 초기화됩니다 
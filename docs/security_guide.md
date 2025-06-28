# 방송 제어 시스템 보안 가이드

이 문서는 학교 방송 제어 시스템의 보안 기능 설정 및 사용 방법을 안내합니다.

## 보안 기능 개요

방송 제어 시스템은 다음 두 가지 보안 레이어를 통해 무단 접근을 방지합니다:

1. **IP 주소 제한**: 특정 IP 주소 대역에서만 API에 접근할 수 있습니다.
2. **시간 기반 인증(TOTP)**: 30초마다 변경되는, 일회용 API 키를 사용합니다.

## 설정 파일

보안 설정은 다음 파일에 저장됩니다:
```
bsbc/data/config/security_config.json
```

이 파일은 서버가 처음 시작될 때 자동으로 생성되며, 다음 내용을 포함합니다:

```json
{
    "allowed_ip_networks": [
        "10.129.49.0/24",
        "10.129.50.0/24",
        "127.0.0.1/32"
    ],
    "totp_secret": "자동 생성된 비밀키",
    "totp_window": 2,
    "api_key_header": "X-API-Key",
    "totp_enabled": false,
    "ip_check_enabled": true
}
```

## 보안 설정 활성화/비활성화

보안 설정은 두 가지 방법으로 변경할 수 있습니다:

### 1. 관리자 도구 사용(권장)

제공된 관리자 도구를 사용하여 보안 설정을 변경할 수 있습니다:

```bash
python bsbc/tools/toggle_security.py
```

이 도구는 다음 기능을 제공합니다:
- TOTP 인증 활성화/비활성화
- IP 검사 활성화/비활성화
- 현재 설정 확인

### 2. 직접 설정 파일 수정

설정 파일을 직접 수정하여 보안 설정을 변경할 수 있습니다:
- `"totp_enabled": true` 또는 `false` - TOTP 인증 활성화/비활성화
- `"ip_check_enabled": true` 또는 `false` - IP 검사 활성화/비활성화

**중요**: 설정 파일을 수정한 후에는 서버를 재시작해야 변경사항이 적용됩니다.

## IP 주소 제한 설정

허용할 IP 주소 대역을 변경하려면 `security_config.json` 파일의 `allowed_ip_networks` 배열을 수정하세요:

```json
"allowed_ip_networks": [
    "10.129.49.0/24",  // 10.129.49.0 ~ 10.129.49.255
    "10.129.50.0/24",  // 10.129.50.0 ~ 10.129.50.255
    "192.168.1.10/32"  // 단일 IP 주소
]
```

CIDR 표기법을 사용하여 IP 대역을 지정할 수 있습니다:
- `/24`는 255.255.255.0 서브넷 마스크를 의미합니다.
- `/32`는 단일 IP 주소를 의미합니다.

## TOTP 인증 설정

### 비밀키 관리

TOTP 비밀키는 서버 초기화 시 자동으로 생성됩니다. 이 키는 서버와 클라이언트 간에 공유되어야 합니다.

* **비밀키 확인**: `/admin/generate-totp` 엔드포인트에 접속하여 확인할 수 있습니다.
* **키 재생성**: 보안 강화를 위해 주기적으로 키를 변경하려면 `security_config.json` 파일에서 `totp_secret` 값을 빈 문자열(`""`)로 설정한 후 서버를 재시작하세요.

### 클라이언트 설정

TOTP 코드 생성을 위한 두 가지 방법:

1. **Google Authenticator 앱 사용**:
   - `/admin/generate-totp` 엔드포인트에서 QR 코드를 스캔하세요.
   - 또는 `tools/generate_totp.py` 스크립트의 QR 코드를 이용하세요.

2. **제공된 클라이언트 유틸리티 사용**:
   - `tools/generate_totp.py` - 현재 TOTP 코드를 실시간으로 표시
   - `tools/api_client_example.py` - API 요청 예제 코드

## API 요청 예시

Python 요청 예시:

```python
import requests
import pyotp

# TOTP 비밀키 (보안 설정 파일에서 가져옴)
secret_key = "YOUR_SECRET_KEY"

# TOTP 코드 생성
totp = pyotp.TOTP(secret_key)
current_code = totp.now()

# API 요청
url = "http://server-address:8000/api/broadcast/text"
headers = {"X-API-Key": current_code}
data = {
    "text": "안녕하세요, 방송 테스트입니다.",
    "target_devices": "301,302,303,304"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

curl 요청 예시:

```bash
# 먼저 TOTP 코드를 생성한 후 사용
curl -X POST "http://server-address:8000/api/broadcast/text" \
  -H "X-API-Key: 123456" \  # TOTP 생성 도구에서 얻은 코드
  -H "Content-Type: application/json" \
  -d '{"text": "안녕하세요, 방송 테스트입니다.", "target_devices": "301,302,303,304"}'
```

## 보안 미들웨어 동작

시스템은 다음 경로를 **공개 경로**로 설정하여 인증 없이 접근 가능합니다:
- `/docs` - API 문서 (Swagger UI)
- `/redoc` - API 문서 (ReDoc)
- `/openapi.json` - OpenAPI 스키마
- `/` - 루트 경로
- `/health` - 서버 상태 확인
- `/broadcast` - 방송 관리 웹 UI
- `/admin` - 관리자 도구 (상태 확인 및 TOTP 코드 생성)

그 외 모든 API 경로(`/api/*`)는 IP 제한 및 TOTP 인증이 필요합니다.

## 문제 해결

1. **"허용되지 않은 IP" 오류**:
   - 클라이언트 IP가 허용된 대역에 포함되어 있는지 확인하세요.
   - 필요하다면 `security_config.json` 파일의 `allowed_ip_networks` 배열에 IP 대역을 추가하세요.

2. **"유효하지 않은 API 키" 오류**:
   - 서버와 클라이언트의 시간이 동기화되어 있는지 확인하세요.
   - 올바른 비밀키를 사용하고 있는지 확인하세요.
   - 동일한 TOTP 코드를 짧은 시간 내에 여러 번 사용하지 마세요.

3. **TOTP 코드가 빠르게 만료됨**:
   - TOTP 코드는 30초마다 변경됩니다. API 요청 직전에 코드를 생성해야 합니다.
   - 시간 윈도우 설정(`totp_window`)을 조정하여 유효 기간을 늘릴 수 있습니다.

## 보안 관련 개선 사항

* **HTTPS 지원 추가**: 프로덕션 환경에서는 HTTPS를 통해 API 통신을 암호화할 것을 강력히 권장합니다.
* **로그인 기반 인증**: 더 높은 보안이 필요한 경우, JWT 기반 사용자 인증 시스템을 추가할 수 있습니다.
* **접근 로깅**: 모든 API 요청에 대한 상세 로그를 기록하여 보안 감사에 활용할 수 있습니다. 
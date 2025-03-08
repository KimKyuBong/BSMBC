# 학교 방송 제어 시스템 (BSBC)

학교 방송 장비를 제어하기 위한 시스템입니다. 이 시스템은 학교 내 교실 및 특수실의 방송 장비를 원격으로 제어할 수 있는 기능을 제공합니다.

## 기능

- 교실 및 특수실 방송 장비 제어 (켜기/끄기)
- 그룹별 장비 일괄 제어 (학년별, 특수실 등)
- 예약 방송 스케줄링
- 시스템 상태 모니터링
- RESTful API 제공
- 명령행 인터페이스 (CLI) 제공

## 설치 방법

1. 저장소 클론:
   ```
   git clone https://github.com/yourusername/bsbc.git
   cd bsbc
   ```

2. 의존성 설치:
   ```
   pip install -r requirements.txt
   ```

## 사용 방법

### API 서버 실행

```
python main.py
```

기본적으로 서버는 `http://localhost:8000`에서 실행됩니다.
API 문서는 `http://localhost:8000/docs`에서 확인할 수 있습니다.

### CLI 사용

```
python cli.py <command> [options]
```

사용 가능한 명령:
- `control`: 장치 제어
- `group`: 장치 그룹 제어
- `channel`: 채널 제어
- `status`: 시스템 상태 조회
- `schedule`: 스케줄 관리
- `test`: 테스트 기능
- `network`: 네트워크 설정

예시:
```
# 장치 켜기
python cli.py control "1-1" --on

# 그룹 제어
python cli.py group grade1 --on

# 스케줄 목록 조회
python cli.py schedule --list
```

## 프로젝트 구조

```
bsbc/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── broadcast.py
│   │       └── schedule.py
│   ├── core/
│   │   ├── config.py
│   │   └── device_mapping.py
│   ├── models/
│   │   ├── device.py
│   │   └── schedule.py
│   ├── services/
│   │   ├── broadcast_controller.py
│   │   ├── network.py
│   │   ├── packet_builder.py
│   │   └── scheduler.py
│   └── utils/
│       └── cli.py
├── cli.py
├── main.py
├── requirements.txt
└── README.md
```

## 라이선스

MIT 
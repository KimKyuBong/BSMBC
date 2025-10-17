#!/usr/bin/env python3
"""
프로덕션 환경용 서버 실행 스크립트
작업 스케줄러/서비스에서 사용
"""
import uvicorn
import sys
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    print("=" * 60)
    print("방송 제어 시스템 서버 시작 (프로덕션 모드)")
    print("=" * 60)
    
    # 프로덕션 모드로 실행 (reload=False, workers=1)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 프로덕션에서는 reload 비활성화
        log_level="info",
        access_log=True
    )




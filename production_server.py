#!/usr/bin/env python3
"""
프로덕션용 FastAPI 서버
윈도우에서 안정적으로 운영하기 위한 향상된 서버 설정
"""
import os
import sys
import signal
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# 메인 앱 임포트
from main import app
from app.core.config import setup_logging

class ProductionServer:
    """프로덕션 서버 클래스"""
    
    def __init__(self):
        # 중앙 로깅 설정 사용
        self.logger = setup_logging(__name__)
        self.server = None
        self.running = False
        
        # 시그널 핸들러 설정
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 프로덕션 미들웨어 추가
        self.setup_production_middleware()
    
    def setup_production_middleware(self):
        """프로덕션용 미들웨어 설정"""
        # CORS 설정 (필요시 수정)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 신뢰할 수 있는 호스트 설정
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"]  # 프로덕션에서는 특정 호스트만 허용
        )
    
    def signal_handler(self, signum, frame):
        """시그널 핸들러"""
        self.logger.info(f"시그널 {signum} 수신, 서버 종료 중...")
        self.stop_server()
    
    def start_server(self, host="0.0.0.0", port=8000, workers=1):
        """서버 시작"""
        try:
            self.logger.info("Production server starting...")
            self.logger.info(f"Server address: http://{host}:{port}")
            self.logger.info(f"Workers: {workers}")
            
            # uvicorn 설정
            config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
                workers=workers,
                log_level="info",
                access_log=True,
                reload=False,  # 프로덕션에서는 reload 비활성화
                loop="asyncio",
                http="httptools",  # 더 빠른 HTTP 파서
                ws="websockets",
                lifespan="on",
                server_header=False,  # 보안을 위해 서버 헤더 숨김
                date_header=True,
                forwarded_allow_ips="*",
                proxy_headers=True,
                forwarded_headers=True
            )
            
            self.server = uvicorn.Server(config)
            self.running = True
            
            # 서버 실행
            self.server.run()
            
        except Exception as e:
            self.logger.error(f"Server start failed: {e}")
            self.running = False
            raise
    
    def stop_server(self):
        """서버 중지"""
        if self.server and self.running:
            self.logger.info("Server stopping...")
            self.running = False
            if hasattr(self.server, 'should_exit'):
                self.server.should_exit = True
    
    def health_check(self):
        """서버 상태 확인"""
        return {
            "status": "running" if self.running else "stopped",
            "timestamp": datetime.now().isoformat(),
            "uptime": getattr(self, 'uptime', 0)
        }

def create_startup_script():
    """시작 스크립트 생성 (사용 안 함 - 서비스 전용)"""
    pass

def main():
    """메인 함수 (서비스 전용)"""
    # 환경 변수에서 설정 읽기
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WORKERS", "1"))
    
    # 서버 인스턴스 생성 및 시작
    server = ProductionServer()
    
    try:
        server.start_server(host=host, port=port, workers=workers)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import sys
        print(f"Server error: {e}", file=sys.stderr)
    finally:
        server.stop_server()

if __name__ == "__main__":
    # 서비스 전용 - 불필요한 스크립트 생성 제거
    main() 
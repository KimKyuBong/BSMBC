#!/usr/bin/env python3
"""
서버 모니터링 및 자동 재시작 스크립트
"""
import os
import sys
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.config import setup_logging

class ServerMonitor:
    """서버 모니터링 클래스"""
    
    def __init__(self, server_url="http://localhost:8000", check_interval=30):
        self.server_url = server_url
        self.check_interval = check_interval
        self.restart_count = 0
        self.max_restarts = 5
        
        # 중앙 로깅 설정 사용
        self.logger = setup_logging(__name__)
    
    def check_server_health(self):
        """서버 상태 확인"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=10)
            if response.status_code == 200:
                return True
            else:
                self.logger.warning(f"서버 응답 코드: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"서버 연결 실패: {e}")
            return False
    
    def start_server(self):
        """서버 시작"""
        try:
            self.logger.info("🚀 서버 시작 중...")
            
            # 프로덕션 서버 시작
            process = subprocess.Popen(
                [sys.executable, "production_server.py"],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # 서버가 시작될 때까지 대기
            time.sleep(5)
            
            if process.poll() is None:
                self.logger.info("✅ 서버가 성공적으로 시작되었습니다.")
                return process
            else:
                self.logger.error("❌ 서버 시작 실패")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 서버 시작 중 오류: {e}")
            return None
    
    def stop_server(self):
        """서버 중지"""
        try:
            # 포트 8000 사용 프로세스 찾기 및 종료
            if os.name == 'nt':  # Windows
                subprocess.run(["taskkill", "/F", "/IM", "python.exe"], 
                             capture_output=True, text=True)
            else:  # Linux/Mac
                subprocess.run(["pkill", "-f", "production_server.py"], 
                             capture_output=True, text=True)
            
            self.logger.info("🛑 서버가 중지되었습니다.")
            time.sleep(2)
            
        except Exception as e:
            self.logger.error(f"❌ 서버 중지 중 오류: {e}")
    
    def restart_server(self):
        """서버 재시작"""
        self.restart_count += 1
        
        if self.restart_count > self.max_restarts:
            self.logger.error(f"❌ 최대 재시작 횟수({self.max_restarts}) 초과")
            return False
        
        self.logger.warning(f"🔄 서버 재시작 시도 {self.restart_count}/{self.max_restarts}")
        
        # 서버 중지
        self.stop_server()
        
        # 잠시 대기
        time.sleep(3)
        
        # 서버 시작
        process = self.start_server()
        
        if process:
            self.logger.info("✅ 서버 재시작 성공")
            return True
        else:
            self.logger.error("❌ 서버 재시작 실패")
            return False
    
    def monitor(self):
        """모니터링 시작"""
        self.logger.info("🔍 서버 모니터링 시작")
        self.logger.info(f"📍 모니터링 대상: {self.server_url}")
        self.logger.info(f"⏱️ 체크 간격: {self.check_interval}초")
        
        # 초기 서버 시작
        if not self.check_server_health():
            self.logger.info("서버가 실행되지 않고 있습니다. 서버를 시작합니다.")
            self.start_server()
        
        try:
            while True:
                # 서버 상태 확인
                if not self.check_server_health():
                    self.logger.warning("⚠️ 서버가 응답하지 않습니다.")
                    
                    # 서버 재시작
                    if not self.restart_server():
                        self.logger.error("❌ 서버 재시작 실패, 모니터링 중단")
                        break
                else:
                    self.logger.info("✅ 서버 정상 동작 중")
                    # 성공적인 체크 후 재시작 카운터 리셋
                    self.restart_count = 0
                
                # 대기
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            self.logger.info("👋 모니터링이 사용자에 의해 중단되었습니다.")
        except Exception as e:
            self.logger.error(f"❌ 모니터링 중 오류: {e}")
    
    def health_check(self):
        """모니터링 상태 확인"""
        return {
            "status": "monitoring",
            "server_url": self.server_url,
            "check_interval": self.check_interval,
            "restart_count": self.restart_count,
            "max_restarts": self.max_restarts,
            "timestamp": datetime.now().isoformat()
        }

def main():
    """메인 함수"""
    print("🔍 서버 모니터링 시스템")
    print("=" * 50)
    
    # 설정
    server_url = os.getenv("SERVER_URL", "http://localhost:8000")
    check_interval = int(os.getenv("CHECK_INTERVAL", "30"))
    
    print(f"📍 서버 URL: {server_url}")
    print(f"⏱️ 체크 간격: {check_interval}초")
    print("=" * 50)
    
    # 모니터링 시작
    monitor = ServerMonitor(server_url, check_interval)
    monitor.monitor()

if __name__ == "__main__":
    main() 
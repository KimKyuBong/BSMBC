#!/usr/bin/env python3
"""
Windows Service로 FastAPI 서버를 등록하는 스크립트
"""
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import time
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from main import app
from app.core.config import setup_logging

class BroadcastService(win32serviceutil.ServiceFramework):
    """
    방송 제어 시스템 Windows Service
    """
    _svc_name_ = "BroadcastControlService"
    _svc_display_name_ = "학교 방송 제어 시스템"
    _svc_description_ = "학교 방송 장비를 제어하는 FastAPI 서버"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = False
        
        # 중앙 로깅 설정 사용
        self.logger = setup_logging(__name__)

    def SvcStop(self):
        """서비스 중지"""
        self.logger.info("서비스 중지 요청")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False

    def SvcDoRun(self):
        """서비스 실행"""
        self.logger.info("서비스 시작")
        self.running = True
        
        try:
            # FastAPI 서버 실행
            config = uvicorn.Config(
                app=app,
                host="0.0.0.0",
                port=8000,
                log_level="info",
                access_log=True
            )
            server = uvicorn.Server(config)
            
            # 서버 시작
            self.logger.info("FastAPI 서버 시작 중...")
            server.run()
            
        except Exception as e:
            self.logger.error(f"서비스 실행 중 오류: {e}")
            self.running = False

def install_service():
    """서비스 설치"""
    try:
        win32serviceutil.InstallService(
            BroadcastService._svc_name_,
            BroadcastService._svc_display_name_,
            BroadcastService._svc_description_,
            startType=win32service.SERVICE_AUTO_START
        )
        print("✅ 서비스가 성공적으로 설치되었습니다.")
        print("   서비스 이름: BroadcastControlService")
        print("   표시 이름: 학교 방송 제어 시스템")
    except Exception as e:
        print(f"❌ 서비스 설치 실패: {e}")

def uninstall_service():
    """서비스 제거"""
    try:
        win32serviceutil.RemoveService(BroadcastService._svc_name_)
        print("✅ 서비스가 성공적으로 제거되었습니다.")
    except Exception as e:
        print(f"❌ 서비스 제거 실패: {e}")

def start_service():
    """서비스 시작"""
    try:
        win32serviceutil.StartService(BroadcastService._svc_name_)
        print("✅ 서비스가 시작되었습니다.")
    except Exception as e:
        print(f"❌ 서비스 시작 실패: {e}")

def stop_service():
    """서비스 중지"""
    try:
        win32serviceutil.StopService(BroadcastService._svc_name_)
        print("✅ 서비스가 중지되었습니다.")
    except Exception as e:
        print(f"❌ 서비스 중지 실패: {e}")

def restart_service():
    """서비스 재시작"""
    try:
        win32serviceutil.RestartService(BroadcastService._svc_name_)
        print("✅ 서비스가 재시작되었습니다.")
    except Exception as e:
        print(f"❌ 서비스 재시작 실패: {e}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("🚀 방송 제어 시스템 Windows Service 관리")
        print("=" * 50)
        print("사용법:")
        print("  python windows_service.py install    - 서비스 설치")
        print("  python windows_service.py uninstall  - 서비스 제거")
        print("  python windows_service.py start      - 서비스 시작")
        print("  python windows_service.py stop       - 서비스 중지")
        print("  python windows_service.py restart    - 서비스 재시작")
        print("  python windows_service.py status     - 서비스 상태 확인")
        print("=" * 50)
    else:
        win32serviceutil.HandleCommandLine(BroadcastService) 
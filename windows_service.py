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
import threading
import asyncio
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
# main.py와 app을 여기서 import하지 않고 나중에 import
# from main import app
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
        self.server = None
        self.server_thread = None
        
        # 중앙 로깅 설정 사용
        self.logger = setup_logging(__name__)
        
        # 서비스 시작 로그
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTING,
            (self._svc_name_, '')
        )

    def SvcStop(self):
        """서비스 중지"""
        try:
            self.logger.info("서비스 중지 요청 수신")
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            
            # 서버 종료
            self.running = False
            if self.server:
                self.logger.info("FastAPI 서버 종료 중...")
                self.server.should_exit = True
            
            # 이벤트 설정
            win32event.SetEvent(self.stop_event)
            
            # 서버 쓰레드 종료 대기
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=10)
            
            self.logger.info("서비스가 정상적으로 중지되었습니다")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, '')
            )
        except Exception as e:
            self.logger.error(f"서비스 중지 중 오류: {e}")

    def SvcDoRun(self):
        """서비스 실행"""
        try:
            self.logger.info("=" * 60)
            self.logger.info("학교 방송 제어 시스템 서비스 시작")
            self.logger.info("=" * 60)
            self.running = True
            
            # 서비스 시작을 Windows에 즉시 알림 (중요!)
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            
            # 서버를 별도 쓰레드에서 실행
            self.server_thread = threading.Thread(target=self._run_server, daemon=False)
            self.server_thread.start()
            
            # 종료 이벤트 대기
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
            
        except Exception as e:
            self.logger.error(f"서비스 실행 중 치명적 오류: {e}")
            servicemanager.LogErrorMsg(f"서비스 실행 중 오류: {e}")
            self.running = False
    
    def _run_server(self):
        """별도 쓰레드에서 FastAPI 서버 실행"""
        try:
            # 시작 지연 (네트워크 초기화 대기)
            self.logger.info("네트워크 초기화 대기 중 (3초)...")
            time.sleep(3)
            
            self.logger.info("FastAPI 애플리케이션 로딩 중...")
            
            # 작업 디렉토리 확인
            work_dir = str(project_root)
            self.logger.info(f"작업 디렉토리: {work_dir}")
            os.chdir(work_dir)
            
            # 필요한 디렉토리 생성
            for directory in ['logs', 'data/temp', 'data/audio/previews']:
                dir_path = project_root / directory
                dir_path.mkdir(parents=True, exist_ok=True)
            
            # 이제 main.py를 import (무거운 작업)
            self.logger.info("main.py 모듈 로딩 중...")
            from main import app
            self.logger.info("FastAPI 앱 로딩 완료!")
            
            # FastAPI 서버 설정
            config = uvicorn.Config(
                app=app,
                host="0.0.0.0",
                port=8000,
                log_level="info",
                access_log=True,
                loop="asyncio"
            )
            
            self.server = uvicorn.Server(config)
            
            # 서버 시작
            self.logger.info("FastAPI 서버 시작 - http://0.0.0.0:8000")
            servicemanager.LogInfoMsg("FastAPI 서버가 시작되었습니다: http://0.0.0.0:8000")
            
            # asyncio로 서버 실행
            asyncio.run(self.server.serve())
            
        except Exception as e:
            self.logger.error(f"서버 실행 중 오류: {e}", exc_info=True)
            servicemanager.LogErrorMsg(f"FastAPI 서버 오류: {str(e)}")
            self.running = False

def install_service():
    """서비스 설치"""
    try:
        # 기존 서비스가 있으면 제거
        try:
            win32serviceutil.RemoveService(BroadcastService._svc_name_)
            print("기존 서비스를 제거했습니다.")
            import time
            time.sleep(2)
        except:
            pass
        
        win32serviceutil.InstallService(
            BroadcastService._svc_name_,
            BroadcastService._svc_display_name_,
            BroadcastService._svc_description_,
            startType=win32service.SERVICE_AUTO_START,
            errorControl=win32service.SERVICE_ERROR_NORMAL
        )
        print("✅ 서비스가 성공적으로 설치되었습니다.")
        print("   서비스 이름: BroadcastControlService")
        print("   표시 이름: 학교 방송 제어 시스템")
        print("   시작 유형: 자동")
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
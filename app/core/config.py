#!/usr/bin/env python3
"""
설정 관리 모듈
시스템 설정, 상수, 환경 변수를 관리합니다.
"""
import os
import sys
from pathlib import Path

# 앱 버전
APP_VERSION = "1.0.0"

# 네트워크 설정
DEFAULT_INTERFACE = r"\Device\NPF_{A3EA7E25-E0C4-4F61-8FA9-69FA733D2708}"
DEFAULT_TARGET_IP = "192.168.0.200"
DEFAULT_TARGET_PORT = 22000

# 데이터 디렉토리 설정
# 애플리케이션 데이터를 저장할 디렉토리 경로 설정
if getattr(sys, 'frozen', False):
    # 실행 파일로 패키징된 경우
    BASE_DIR = Path(sys.executable).parent
else:
    # 스크립트로 실행 중인 경우
    BASE_DIR = Path(os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

APP_DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(APP_DATA_DIR, exist_ok=True)

# 파일 경로
SCHEDULE_FILE = os.path.join(APP_DATA_DIR, "broadcast_schedule.csv")

# 특수 채널 및 명령 정의
SPECIAL_CHANNELS = {
    0x00: "기본 채널",
    0x40: "그룹 제어 채널 (64)",
    0xD0: "특수 기능 채널 (208)"
}

class Config:
    """
    설정 관리 클래스
    설정 값을 로드하고 관리합니다.
    """
    def __init__(self):
        self.app_version = APP_VERSION
        self.default_interface = DEFAULT_INTERFACE
        self.default_target_ip = DEFAULT_TARGET_IP
        self.default_target_port = DEFAULT_TARGET_PORT
        self.schedule_file = SCHEDULE_FILE
        self.special_channels = SPECIAL_CHANNELS
        
        # 데이터 디렉토리 설정
        self.app_data_dir = APP_DATA_DIR
        
        # 오디오 파일 저장 디렉토리
        self.audio_dir = os.path.join(self.app_data_dir, "audio")
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # TTS 모델 캐시 디렉토리
        self.tts_models_dir = os.path.join(self.app_data_dir, "tts_models")
        os.makedirs(self.tts_models_dir, exist_ok=True)
        
    def get_app_info(self):
        """
        앱 정보 반환
        """
        return {
            "version": self.app_version,
            "name": "학교 방송 제어 시스템"
        }
    
    def update_target_ip(self, ip):
        """
        대상 IP 업데이트
        """
        self.default_target_ip = ip
        return True
    
    def update_target_port(self, port):
        """
        대상 포트 업데이트
        """
        self.default_target_port = int(port)
        return True

# 싱글톤 인스턴스
config = Config() 
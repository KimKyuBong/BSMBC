#!/usr/bin/env python3
"""
설정 관리 모듈
시스템 설정, 상수, 환경 변수를 관리합니다.
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# 앱 버전
APP_VERSION = "1.0.0"

# 네트워크 설정
DEFAULT_INTERFACE = "eth0"  # 라즈베리파이 기본 이더넷 인터페이스
DEFAULT_TARGET_IP = "192.168.0.200"
DEFAULT_TARGET_PORT = 22000

# FFmpeg 경로 설정 (시스템 경로 사용 - 라즈베리파이)
FFMPEG_PATH = Path("/usr/bin/ffmpeg")
FFPROBE_PATH = Path("/usr/bin/ffprobe")

# 오디오 정규화 기본 설정
DEFAULT_TARGET_DBFS = -12.0

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

# 로그 디렉토리 설정
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 파일 경로
SCHEDULE_FILE = os.path.join(APP_DATA_DIR, "broadcast_schedule.csv")

# 특수 채널 및 명령 정의
SPECIAL_CHANNELS = {
    0x00: "기본 채널",
    0x40: "그룹 제어 채널 (64)",
    0xD0: "특수 기능 채널 (208)"
}

def setup_logging(name: str = None, level: str = "INFO") -> logging.Logger:
    """
    통일된 로깅 설정
    
    Parameters:
    -----------
    name : str, optional
        로거 이름 (기본값: None, __name__ 사용)
    level : str, optional
        로그 레벨 (기본값: "INFO")
    
    Returns:
    --------
    logging.Logger
        설정된 로거 인스턴스
    """
    if name is None:
        name = __name__
    
    # 로거 가져오기
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있으면 그대로 반환
    if logger.handlers:
        return logger
    
    # 로그 레벨 설정
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # 로그 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 파일 핸들러 설정
    log_file = LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

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
        
        # FFmpeg 경로 설정
        self.ffmpeg_path = FFMPEG_PATH
        self.ffprobe_path = FFPROBE_PATH
        
        # 데이터 디렉토리 설정
        self.app_data_dir = APP_DATA_DIR
        
        # 메인 데이터 디렉토리 (시작/끝 신호음 등)
        self.data_dir = self.app_data_dir
        
        # 오디오 파일 저장 디렉토리
        self.audio_dir = os.path.join(self.app_data_dir, "audio")
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # TTS 모델 캐시 디렉토리
        self.tts_models_dir = os.path.join(self.app_data_dir, "tts_models")
        os.makedirs(self.tts_models_dir, exist_ok=True)
        
        # 임시 디렉토리
        self.temp_dir = os.path.join(self.app_data_dir, "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 로그 디렉토리
        self.log_dir = LOG_DIR
        
        # 오디오 정규화 설정
        self.default_target_dbfs = DEFAULT_TARGET_DBFS
        
    def get_app_info(self):
        """
        앱 정보 반환
        """
        return {
            "version": self.app_version,
            "name": "학교 방송 제어 시스템"
        }
    
    def get_ffmpeg_paths(self):
        """
        FFmpeg 경로 정보 반환
        
        Returns:
        --------
        dict
            ffmpeg 관련 경로 정보
        """
        return {
            "ffmpeg_path": str(self.ffmpeg_path),
            "ffprobe_path": str(self.ffprobe_path),
            "ffmpeg_exists": self.ffmpeg_path.exists(),
            "ffprobe_exists": self.ffprobe_path.exists()
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
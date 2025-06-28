"""
방송 제어 시스템 보안 모듈
IP 제한 및 시간 기반 API 키 인증을 제공합니다.
"""

import os
import ipaddress
import time
import json
import secrets
import pyotp
from typing import Optional, List, Set, Dict, Union
from pathlib import Path
from fastapi import Request, HTTPException
from starlette.status import HTTP_403_FORBIDDEN

# 설정 파일 경로
SECURITY_CONFIG_PATH = Path("data/config/security_config.json")

# 기본 설정
DEFAULT_CONFIG = {
    "allowed_ip_networks": [
        "10.129.55.254/32",
        "10.129.50.0/24",
        "127.0.0.1/32"  # 로컬 개발용 (필요시 제거)
    ],
    "totp_secret": "",  # 초기 실행 시 자동 생성됨
    "totp_window": 2,   # ±1분 허용
    "api_key_header": "X-API-Key",
    "totp_enabled": False,  # TOTP 인증 활성화/비활성화 플래그
    "ip_check_enabled": True  # IP 검사 활성화/비활성화 플래그
}

class SecurityManager:
    """보안 관리 클래스"""
    
    def __init__(self):
        self.config = self._load_or_create_config()
        self.allowed_networks = [
            ipaddress.ip_network(network)
            for network in self.config["allowed_ip_networks"]
        ]
        
        # TOTP 비밀키가 없으면 새로 생성
        if not self.config["totp_secret"]:
            self.config["totp_secret"] = pyotp.random_base32()
            self._save_config()
            print(f"[*] 새로운 TOTP 비밀키가 생성되었습니다.")
        
        # TOTP 생성기 초기화
        self.totp = pyotp.TOTP(self.config["totp_secret"])
        
        print(f"[*] 보안 관리자가 초기화되었습니다.")
        print(f"[*] 허용된 IP 네트워크: {', '.join(self.config['allowed_ip_networks'])}")
        print(f"[*] TOTP 인증: {'활성화됨' if self.config['totp_enabled'] else '비활성화됨'}")
        print(f"[*] IP 검사: {'활성화됨' if self.config['ip_check_enabled'] else '비활성화됨'}")
        
    def _load_or_create_config(self) -> Dict:
        """설정 파일 로드 또는 생성"""
        if SECURITY_CONFIG_PATH.exists():
            try:
                with open(SECURITY_CONFIG_PATH, "r") as f:
                    config = json.load(f)
                    
                    # 새로운 옵션 추가 (이전 버전 호환성)
                    if "totp_enabled" not in config:
                        config["totp_enabled"] = DEFAULT_CONFIG["totp_enabled"]
                    if "ip_check_enabled" not in config:
                        config["ip_check_enabled"] = DEFAULT_CONFIG["ip_check_enabled"]
                    
                    return config
                    
            except Exception as e:
                print(f"[!] 보안 설정 파일 로드 중 오류: {e}")
                print(f"[*] 기본 설정을 사용합니다.")
                return DEFAULT_CONFIG
        else:
            # 설정 파일 디렉토리 생성
            SECURITY_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            # 설정 파일 생성
            with open(SECURITY_CONFIG_PATH, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            
            print(f"[*] 보안 설정 파일이 생성되었습니다: {SECURITY_CONFIG_PATH}")
            return DEFAULT_CONFIG
    
    def _save_config(self):
        """설정 파일 저장"""
        with open(SECURITY_CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=4)
    
    def is_ip_allowed(self, ip: str) -> bool:
        """IP 주소가 허용된 네트워크에 속하는지 확인"""
        try:
            request_ip = ipaddress.ip_address(ip)
            return any(request_ip in network for network in self.allowed_networks)
        except ValueError:
            return False
    
    def generate_totp(self) -> str:
        """현재 시간에 대한 TOTP 코드 생성"""
        return self.totp.now()
    
    def verify_totp(self, token: str) -> bool:
        """TOTP 코드 검증"""
        return self.totp.verify(token, valid_window=self.config["totp_window"])
    
    def get_totp_secret(self) -> str:
        """TOTP 비밀키 반환"""
        return self.config["totp_secret"]
    
    def get_totp_uri(self, issuer_name: str = "방송제어시스템") -> str:
        """QR 코드 생성을 위한 TOTP URI 반환"""
        return self.totp.provisioning_uri(name="broadcast-admin", issuer_name=issuer_name)
    
    def generate_totp_for_time(self, timestamp: int) -> str:
        """특정 시간에 대한 TOTP 코드 생성"""
        return self.totp.at(timestamp)
        
    def set_totp_enabled(self, enabled: bool):
        """TOTP 인증 활성화/비활성화 설정"""
        self.config["totp_enabled"] = enabled
        self._save_config()
        print(f"[*] TOTP 인증이 {'활성화' if enabled else '비활성화'}되었습니다.")
        
    def set_ip_check_enabled(self, enabled: bool):
        """IP 검사 활성화/비활성화 설정"""
        self.config["ip_check_enabled"] = enabled
        self._save_config()
        print(f"[*] IP 검사가 {'활성화' if enabled else '비활성화'}되었습니다.")
        
    def is_totp_enabled(self) -> bool:
        """TOTP 인증 활성화 여부 확인"""
        return self.config["totp_enabled"]
        
    def is_ip_check_enabled(self) -> bool:
        """IP 검사 활성화 여부 확인"""
        return self.config["ip_check_enabled"]

# 전역 보안 관리자 객체
security_manager = None

def get_security_manager() -> SecurityManager:
    """보안 관리자 객체 반환 (싱글톤)"""
    global security_manager
    if security_manager is None:
        security_manager = SecurityManager()
    return security_manager

# FastAPI 미들웨어용 검증 함수
async def verify_ip_and_api_key(request: Request):
    """IP 주소 및 API 키 검증"""
    # 보안 관리자 인스턴스 가져오기
    sm = get_security_manager()
    
    # 1. IP 주소 검증 (활성화된 경우)
    if sm.is_ip_check_enabled():
        client_ip = request.client.host
        if not sm.is_ip_allowed(client_ip):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=f"접근이 거부되었습니다: 허용되지 않은 IP ({client_ip})"
            )
    
    # 2. API 키(TOTP) 검증 (활성화된 경우)
    if sm.is_totp_enabled():
        api_key_header = sm.config["api_key_header"]
        api_key = request.headers.get(api_key_header)
        
        # 키가 없는 경우
        if not api_key:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail=f"인증 실패: {api_key_header} 헤더가 필요합니다"
            )
        
        # 키 검증
        if not sm.verify_totp(api_key):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="인증 실패: 유효하지 않은 API 키"
            ) 
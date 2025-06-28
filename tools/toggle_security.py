#!/usr/bin/env python3
"""
방송 제어 시스템 보안 설정 관리 도구

이 스크립트는 보안 설정 파일을 직접 수정하여 TOTP 인증과 IP 검사를 활성화/비활성화합니다.
서버 관리자만 실행할 수 있어야 합니다.

사용법:
    python toggle_security.py
"""

import os
import sys
import json
from pathlib import Path

# 경로 설정
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent.parent
CONFIG_PATH = ROOT_DIR / "data" / "config" / "security_config.json"

def load_config():
    """보안 설정 파일 로드"""
    if not CONFIG_PATH.exists():
        print(f"[!] 오류: 설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")
        print("[!] 서버를 먼저 실행하여 설정 파일을 생성하세요.")
        return None
        
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] 설정 파일 로드 중 오류: {e}")
        return None

def save_config(config):
    """보안 설정 파일 저장"""
    try:
        # 디렉토리가 없으면 생성
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"[!] 설정 파일 저장 중 오류: {e}")
        return False

def toggle_totp(config, enabled):
    """TOTP 인증 활성화/비활성화"""
    config["totp_enabled"] = enabled
    if save_config(config):
        print(f"[*] TOTP 인증이 {'활성화' if enabled else '비활성화'}되었습니다.")
        return True
    return False

def toggle_ip_check(config, enabled):
    """IP 검사 활성화/비활성화"""
    config["ip_check_enabled"] = enabled
    if save_config(config):
        print(f"[*] IP 검사가 {'활성화' if enabled else '비활성화'}되었습니다.")
        return True
    return False

def display_current_settings(config):
    """현재 설정 표시"""
    print("\n===== 현재 보안 설정 =====")
    print(f"TOTP 인증: {'활성화됨' if config.get('totp_enabled', False) else '비활성화됨'}")
    print(f"IP 검사: {'활성화됨' if config.get('ip_check_enabled', True) else '비활성화됨'}")
    print(f"허용된 IP 네트워크: {', '.join(config.get('allowed_ip_networks', []))}")
    print(f"TOTP 비밀키: {config.get('totp_secret', '없음')}")
    print("==========================\n")

def main():
    """메인 함수"""
    print("\n===== 방송 제어 시스템 보안 설정 관리 도구 =====\n")
    
    # 설정 로드
    config = load_config()
    if not config:
        sys.exit(1)
    
    # 현재 설정 표시
    display_current_settings(config)
    
    while True:
        print("\n===== 메뉴 =====")
        print("1. TOTP 인증 활성화")
        print("2. TOTP 인증 비활성화")
        print("3. IP 검사 활성화")
        print("4. IP 검사 비활성화")
        print("5. 현재 설정 확인")
        print("0. 종료")
        
        choice = input("\n선택: ")
        
        if choice == "1":
            toggle_totp(config, True)
        elif choice == "2":
            toggle_totp(config, False)
        elif choice == "3":
            toggle_ip_check(config, True)
        elif choice == "4":
            toggle_ip_check(config, False)
        elif choice == "5":
            # 변경사항이 있을 수 있으므로 다시 로드
            config = load_config()
            if config:
                display_current_settings(config)
        elif choice == "0":
            print("[*] 프로그램을 종료합니다.")
            break
        else:
            print("[!] 잘못된 선택입니다. 다시 시도하세요.")
        
        # 작업 후 다시 로드
        config = load_config()
        
    print("\n[*] 서버를 재시작하여 변경사항을 적용하세요.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] 프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"\n[!] 오류 발생: {e}") 
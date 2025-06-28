#!/usr/bin/env python3
"""
TOTP 코드 생성 유틸리티

이 스크립트는 방송 제어 시스템 API 접근을 위한 시간 기반 일회용 암호(TOTP)를 생성합니다.
클라이언트 측에서 실행하여 API 요청 시 필요한 헤더를 생성할 수 있습니다.

사용법:
    python generate_totp.py
"""

import os
import sys
import time
import json
import pyotp
import qrcode
from pathlib import Path

# 설정 파일 경로
SECURITY_CONFIG_PATH = Path("../data/config/security_config.json")

def get_secret_key():
    """
    보안 설정 파일에서 비밀키 가져오기
    """
    if SECURITY_CONFIG_PATH.exists():
        try:
            with open(SECURITY_CONFIG_PATH, "r") as f:
                config = json.load(f)
                return config.get("totp_secret", "")
        except Exception as e:
            print(f"[!] 설정 파일 로드 실패: {e}")
            return ""
    else:
        print(f"[!] 설정 파일을 찾을 수 없음: {SECURITY_CONFIG_PATH}")
        return ""

def generate_totp(secret_key=""):
    """
    TOTP 코드 생성
    """
    if not secret_key:
        secret_key = get_secret_key()
        
    if not secret_key:
        print("[!] 비밀키를 찾을 수 없습니다.")
        return None
        
    totp = pyotp.TOTP(secret_key)
    code = totp.now()
    
    return {
        "code": code,
        "valid_for_seconds": 30 - (int(time.time()) % 30),
        "secret": secret_key
    }

def display_qr_code(secret_key, issuer_name="방송제어시스템"):
    """
    QR 코드 생성 및 표시
    """
    try:
        totp = pyotp.TOTP(secret_key)
        uri = totp.provisioning_uri(name="broadcast-admin", issuer_name=issuer_name)
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        qr.add_data(uri)
        qr.make(fit=True)
        
        # 터미널에 ASCII 아트로 QR 코드 표시
        qr.print_ascii()
        
        print(f"\n[*] 이 QR 코드를 Google Authenticator 앱에서 스캔하세요.")
        print(f"[*] 또는 다음 비밀키를 직접 입력하세요: {secret_key}")
        
    except Exception as e:
        print(f"[!] QR 코드 생성 실패: {e}")

def main():
    """
    메인 함수
    """
    print("\n===== 방송 제어 시스템 TOTP 생성기 =====\n")
    
    # 비밀키 로드
    secret_key = get_secret_key()
    
    if not secret_key:
        print("[!] 비밀키를 찾을 수 없습니다. 서버 측에서 먼저 보안 설정을 초기화해주세요.")
        sys.exit(1)
    
    # 사용자 입력
    show_qr = input("Google Authenticator용 QR 코드를 표시할까요? (y/n): ").lower() == 'y'
    
    if show_qr:
        display_qr_code(secret_key)
    
    # TOTP 생성
    while True:
        result = generate_totp(secret_key)
        
        if not result:
            print("[!] TOTP 생성 실패")
            break
            
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n===== 방송 제어 시스템 TOTP 생성기 =====\n")
        print(f"[*] TOTP 코드: {result['code']}")
        print(f"[*] 유효 시간: {result['valid_for_seconds']}초")
        print(f"[*] 헤더 이름: X-API-Key")
        print(f"[*] 헤더 값: {result['code']}")
        print("\n[*] API 요청 시 위 헤더를 추가하세요.")
        print("[*] 새 코드가 자동으로 생성됩니다. 종료하려면 Ctrl+C를 누르세요.\n")
        
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n[*] 프로그램을 종료합니다.")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] 프로그램을 종료합니다.")
    except Exception as e:
        print(f"\n[!] 오류 발생: {e}") 
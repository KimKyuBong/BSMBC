#!/usr/bin/env python3
"""
방송 제어 시스템 API 클라이언트 예제

이 스크립트는 시간 기반 API 키와 IP 제한이 적용된 방송 제어 시스템 API에
안전하게 접근하는 방법을 보여줍니다.

사용법:
    python api_client_example.py
"""

import os
import sys
import time
import json
import requests
import pyotp
from pathlib import Path

# 설정
API_BASE_URL = "http://localhost:8000/api"  # 실제 서버 주소로 변경하세요
CONFIG_PATH = Path("../data/config/security_config.json")

def get_totp_secret():
    """보안 설정 파일에서 TOTP 비밀키 가져오기"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
                return config.get("totp_secret", "")
        except Exception as e:
            print(f"[!] 설정 파일 로드 실패: {e}")
            return ""
    else:
        print(f"[!] 설정 파일을 찾을 수 없음: {CONFIG_PATH}")
        print(f"[*] 서버 초기화 후 생성된 설정 파일이 필요합니다.")
        return ""

def generate_totp(secret=None):
    """TOTP 코드 생성"""
    if not secret:
        secret = get_totp_secret()
        
    if not secret:
        print("[!] TOTP 비밀키를 찾을 수 없습니다.")
        return None
        
    totp = pyotp.TOTP(secret)
    return totp.now()

def api_request(method, endpoint, data=None, params=None, headers=None):
    """API 요청 함수"""
    if headers is None:
        headers = {}
    
    # TOTP 코드 생성 및 헤더에 추가
    totp_code = generate_totp()
    if not totp_code:
        print("[!] API 키 생성 실패")
        return None
        
    headers["X-API-Key"] = totp_code
    
    url = f"{API_BASE_URL}/{endpoint.lstrip('/')}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method.upper() == "DELETE":
            response = requests.delete(url, json=data, headers=headers)
        else:
            print(f"[!] 지원되지 않는 HTTP 메서드: {method}")
            return None
            
        # 응답 처리
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        print(f"[!] HTTP 오류: {e}")
        try:
            print(f"[!] 응답 내용: {response.json()}")
        except:
            print(f"[!] 응답 내용: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[!] 요청 오류: {e}")
    
    return None

def test_api_connection():
    """API 연결 테스트"""
    print("\n[*] API 연결 테스트 중...")
    
    # 기본 엔드포인트 테스트 (인증 필요 없음)
    try:
        response = requests.get(f"{API_BASE_URL.rstrip('/api')}/health")
        response.raise_for_status()
        print(f"[+] 서버 상태: {response.json()}")
    except Exception as e:
        print(f"[!] 서버 연결 실패: {e}")
        return False
    
    # 인증이 필요한 엔드포인트 테스트
    result = api_request("GET", "broadcast/status")
    if result:
        print(f"[+] API 인증 성공: {result}")
        return True
    else:
        print(f"[!] API 인증 실패")
        return False

def example_text_broadcast():
    """텍스트 방송 예제"""
    print("\n[*] 텍스트 방송 전송 예제...")
    
    # 방송할 장치 목록
    devices = "301,302,303,304"  # 3학년 1~4반
    
    # 방송할 텍스트
    text = "안녕하세요, 방송 테스트입니다."
    
    # API 요청 데이터
    data = {
        "text": text,
        "target_devices": devices,
        "language": "ko"
    }
    
    # POST 요청 보내기
    result = api_request("POST", "broadcast/text", data=data)
    
    if result:
        print(f"[+] 방송 전송 성공: {result}")
        return True
    else:
        print(f"[!] 방송 전송 실패")
        return False

def main():
    """메인 함수"""
    print("\n===== 방송 제어 시스템 API 클라이언트 예제 =====\n")
    
    # TOTP 비밀키 확인
    secret = get_totp_secret()
    if not secret:
        print("[!] 서버에서 먼저 보안 설정을 초기화해야 합니다.")
        sys.exit(1)
    
    print(f"[*] TOTP 비밀키: {secret}")
    print(f"[*] 현재 TOTP 코드: {generate_totp(secret)}")
    
    # API 연결 테스트
    if not test_api_connection():
        print("[!] API 연결 테스트 실패. 프로그램을 종료합니다.")
        return
    
    # 사용자 입력
    while True:
        print("\n===== 메뉴 =====")
        print("1. 텍스트 방송 보내기")
        print("2. API 연결 테스트")
        print("0. 종료")
        
        choice = input("\n선택: ")
        
        if choice == "1":
            example_text_broadcast()
        elif choice == "2":
            test_api_connection()
        elif choice == "0":
            print("[*] 프로그램을 종료합니다.")
            break
        else:
            print("[!] 잘못된 선택입니다. 다시 시도하세요.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] 프로그램이 중단되었습니다.")
    except Exception as e:
        print(f"\n[!] 오류 발생: {e}") 
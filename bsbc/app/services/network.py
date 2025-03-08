#!/usr/bin/env python3
"""
네트워크 통신 모듈
방송 시스템과의 통신을 관리합니다.
"""
import socket
from scapy.all import IFACES

class NetworkManager:
    """
    네트워크 관리 클래스
    방송 시스템과의 소켓 통신을 처리합니다.
    """
    def __init__(self, target_ip="192.168.0.200", target_port=22000, interface=None):
        """
        초기화 함수 - 네트워크 설정을 초기화합니다.
        
        Parameters:
        -----------
        target_ip : str
            대상 방송 장비 IP
        target_port : int
            대상 방송 장비 포트
        interface : str
            사용할 네트워크 인터페이스
        """
        self.target_ip = target_ip
        self.target_port = target_port
        self.interface = interface
        
        # 패킷 카운터 초기화
        self.packet_counter = 0
        
    def print_interface_info(self):
        """인터페이스 정보 출력"""
        try:
            iface_data = None
            for name, data in IFACES.items():
                if name == self.interface:
                    iface_data = data
                    break
                    
            if iface_data:
                print(f"[*] 사용 중인 인터페이스: {self.interface}")
                print(f"    - 설명: {iface_data.description}")
                print(f"    - IP 주소: {iface_data.ip or 'IP 없음'}")
                print(f"    - MAC 주소: {iface_data.mac or 'MAC 없음'}")
        except Exception as e:
            print(f"[!] 인터페이스 정보 조회 실패: {e}")
    
    def send_payload(self, payload):
        """
        방송 장비에 페이로드 전송
        
        Parameters:
        -----------
        payload : bytes
            전송할 페이로드 데이터
            
        Returns:
        --------
        tuple(bool, bytes)
            성공 여부와 응답 데이터
        """
        if payload is None:
            print("[!] 유효하지 않은 페이로드")
            return False, None
        
        try:
            # 소켓 생성
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # 연결 타임아웃 설정 (3초)
            s.settimeout(3)
            
            print(f"[*] {self.target_ip}:{self.target_port}에 연결 중...")
            # TCP 연결 시도
            s.connect((self.target_ip, self.target_port))
            
            # 소스 포트 확인
            source_port = s.getsockname()[1]
            
            print(f"[*] 패킷 정보:")
            print(f"    - 소스 IP: 192.168.0.100, 포트: {source_port}")
            print(f"    - 대상 IP: {self.target_ip}, 포트: {self.target_port}")
            
            # 페이로드 디버깅 정보 추가
            print(f"    - 페이로드 길이: {len(payload)} 바이트 (헥스: {len(payload):02x}h)")
            
            # 페이로드가 예상 길이(46바이트)와 다를 경우 경고
            if len(payload) != 46:
                print(f"    - [!] 주의: 예상 길이(46바이트)와 다릅니다!")
            
            # 페이로드 헥스값 출력 (보기 좋게 정렬)
            hex_str = payload.hex()
            for i in range(0, len(hex_str), 32):
                if i == 0:
                    print(f"    - 페이로드 헥스: {hex_str[i:i+32]}")
                else:
                    print(f"                    {hex_str[i:i+32]}")
            
            print(f"    - 페이로드 마지막 4바이트: {payload[-4:].hex()}")
            
            # 페이로드 전송
            print(f"\n[*] 데이터 전송 중...")
            s.sendall(payload)
            
            # 응답 데이터
            response_data = None
            
            # 응답 대기 (최대 3초)
            try:
                print("[*] 응답 대기 중...")
                response = s.recv(1024)
                if response:
                    print(f"[+] 응답 수신: {len(response)} 바이트")
                    print(f"    - 헥스: {response.hex()}")
                    response_data = response
                else:
                    print("[!] 응답 없음")
            except socket.timeout:
                print("[!] 응답 타임아웃")
            
            # 연결 종료
            s.close()
            
            print("[+] 패킷 전송 완료")
            self.packet_counter += 1
            return True, response_data
            
        except ConnectionRefusedError:
            print(f"[!] 연결 거부됨: {self.target_ip}:{self.target_port}")
        except socket.timeout:
            print(f"[!] 연결 타임아웃: {self.target_ip}:{self.target_port}")
        except Exception as e:
            print(f"[!] 패킷 전송 실패: {e}")
        
        return False, None
    
    def initialize_connection(self):
        """
        서버 연결 초기화 및 상태 확인
        
        Returns:
        --------
        tuple(bool, bytes)
            성공 여부와 응답 데이터
        """
        print("[*] 서버 연결 초기화 중...")
        
        try:
            # 소켓 생성 및 서버 연결
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((self.target_ip, self.target_port))
            
            # 상태 요청 패킷 생성 (빈 패킷으로 서버에 연결만 해도 상태를 응답함)
            empty_payload = bytes.fromhex("022d0043420100000000000000000000000000000000000000000000000000000000000000000000002f0300")
            
            # 패킷 전송
            print("[*] 상태 요청 패킷 전송 중...")
            s.sendall(empty_payload)
            
            # 응답 데이터
            response_data = None
            
            # 응답 대기
            try:
                print("[*] 서버 응답 대기 중...")
                response = s.recv(1024)
                if response:
                    print(f"[+] 응답 수신: {len(response)} 바이트")
                    print(f"    - 헥스: {response.hex()}")
                    response_data = response
                else:
                    print("[!] 응답 없음")
            except socket.timeout:
                print("[!] 응답 타임아웃")
            
            # 연결 종료
            s.close()
            
            return (response_data is not None), response_data
            
        except Exception as e:
            print(f"[!] 서버 연결 초기화 실패: {e}")
            return False, None

# 싱글톤 인스턴스 생성
network_manager = NetworkManager() 
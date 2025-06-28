#!/usr/bin/env python3
"""
네트워크 통신 모듈
방송 시스템의 패킷 생성 및 통신을 처리합니다.
"""
import socket
from scapy.all import IFACES
from .packet_builder import PacketBuilder

class NetworkManager:
    """
    네트워크 통신 관리 클래스
    패킷 생성 및 방송 장비와의 통신을 처리합니다.
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
        
        # 패킷 빌더 초기화
        self.packet_builder = PacketBuilder()
        
        # 네트워크 인터페이스 설정
        if interface is None:
            self.interface = self._get_default_interface()
    
    def _get_default_interface(self):
        """기본 네트워크 인터페이스 선택"""
        try:
            interfaces = IFACES.show(resolve_mac=False, print_result=False)
            if interfaces and isinstance(interfaces, dict):
                # 첫 번째 인터페이스 선택
                return list(interfaces.keys())[0]
        except Exception as e:
            print(f"[!] 인터페이스 선택 중 오류: {e}")
        return None
    
    def send_payload(self, payload, timeout=5):
        """
        페이로드를 방송 장비로 전송 (2번 연속 전송)
        Returns:
            (bool, bytes|None): (성공여부, 마지막 응답값)
        """
        last_response = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((self.target_ip, self.target_port))
            for i in range(2):
                sock.send(payload)
                print(f"[*] 패킷 전송 {i+1}/2: {len(payload)}바이트")
                try:
                    response = sock.recv(1024)
                    if response:
                        print(f"[*] 응답 수신: {response.hex()}")
                        last_response = response
                except socket.timeout:
                    print(f"[!] 응답 타임아웃 {i+1}/2")
            sock.close()
            self.packet_counter += 1
            return True, last_response
        except Exception as e:
            print(f"[!] 패킷 전송 실패: {e}")
            return False, None
    
    def send_payload_single(self, payload, timeout=5):
        """
        페이로드를 방송 장비로 전송 (1번만 전송)
        Returns:
            (bool, bytes|None): (성공여부, 응답값)
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((self.target_ip, self.target_port))
            sock.send(payload)
            print(f"[*] 패킷 전송: {len(payload)}바이트")
            response = None
            try:
                response = sock.recv(1024)
                if response:
                    print(f"[*] 응답 수신: {response.hex()}")
            except socket.timeout:
                print(f"[!] 응답 타임아웃")
            sock.close()
            self.packet_counter += 1
            return True, response
        except Exception as e:
            print(f"[!] 패킷 전송 실패: {e}")
            return False, None
    
    def send_coordinate_packet(self, row, col, state):
        """
        특정 좌표 장비 상태 패킷 전송
        
        Parameters:
        -----------
        row : int
            행 번호 (1-4)
        col : int
            열 번호 (1-16)
        state : int
            0: 끄기, 1: 켜기
            
        Returns:
        --------
        tuple(bool, bytes|None)
            (전송 성공 여부, 응답 데이터)
        """
        payload = self.packet_builder.create_coordinate_payload(row, col, state)
        if payload:
            return self.send_payload_single(payload)
        return False, None
    
    def send_current_state_packet(self, active_rooms):
        """
        현재 상태 패킷 전송
        
        Parameters:
        -----------
        active_rooms : set
            활성화된 방 번호 집합
            
        Returns:
        --------
        (bool, bytes|None)
            (전송 성공 여부, 응답 데이터)
        """
        print(f"[*] NetworkManager: 현재 상태 패킷 전송 시작 (활성 방: {sorted(active_rooms)})")
        
        try:
            payload = self.packet_builder.create_current_state_payload(active_rooms)
            if payload:
                print(f"[*] NetworkManager: 패킷 생성 완료 ({len(payload)}바이트)")
                print(f"[*] NetworkManager: 패킷 헥스: {payload.hex()}")
                
                success, response = self.send_payload_single(payload)
                
                if success:
                    print(f"[*] NetworkManager: 패킷 전송 성공")
                    if response:
                        print(f"[*] NetworkManager: 응답 수신: {response.hex()}")
                    return True, response
                else:
                    print(f"[!] NetworkManager: 패킷 전송 실패")
                    return False, response
            else:
                print(f"[!] NetworkManager: 패킷 생성 실패")
                return False, None
                
        except Exception as e:
            print(f"[!] NetworkManager: 패킷 전송 중 오류: {e}")
            return False, None
    
    def get_packet_counter(self):
        """전송된 패킷 수 조회"""
        return self.packet_counter
    
    def reset_packet_counter(self):
        """패킷 카운터 초기화"""
        self.packet_counter = 0
        print("[*] 패킷 카운터 초기화")
    
    def test_connection(self):
        """
        방송 장비 연결 테스트
        
        Returns:
        --------
        bool
            연결 성공 여부
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((self.target_ip, self.target_port))
            sock.close()
            print(f"[*] 연결 테스트 성공: {self.target_ip}:{self.target_port}")
            return True
        except Exception as e:
            print(f"[!] 연결 테스트 실패: {e}")
            return False

    def initialize_connection(self):
        """
        네트워크 연결 초기화 및 상태 확인
        
        Returns:
        --------
        tuple
            (성공여부, 응답데이터)
        """
        try:
            # 연결 테스트
            if not self.test_connection():
                return False, None
            
            # 모든 장비 OFF 패킷 전송으로 초기화
            payload = self.packet_builder.create_all_off_payload()
            if payload:
                success, response = self.send_payload(payload)
                if success:
                    print("[*] 네트워크 연결 초기화 완료")
                    return True, response
                else:
                    print("[!] 네트워크 초기화 패킷 전송 실패")
                    return False, None
            else:
                print("[!] 초기화 패킷 생성 실패")
                return False, None
                
        except Exception as e:
            print(f"[!] 네트워크 연결 초기화 중 오류: {e}")
            return False, None

    def print_interface_info(self):
        """네트워크 인터페이스 정보 출력"""
        try:
            print(f"[*] 네트워크 설정:")
            print(f"    - 대상 IP: {self.target_ip}")
            print(f"    - 대상 포트: {self.target_port}")
            print(f"    - 인터페이스: {self.interface}")
            print(f"    - 전송된 패킷 수: {self.packet_counter}")
        except Exception as e:
            print(f"[!] 네트워크 인터페이스 정보 출력 중 오류: {e}")

# 싱글톤 인스턴스 생성
network_manager = NetworkManager() 
#!/usr/bin/env python3
"""
패킷 파서 모듈
네트워크에서 받은 응답 패킷을 해석하여 장비 상태를 추출합니다.
"""

from .packet_base import PacketBase

class PacketParser(PacketBase):
    """
    패킷 파서 클래스
    네트워크 응답 패킷을 해석하여 4행 16열 행렬의 장비 상태를 추출합니다.
    """
    def __init__(self):
        super().__init__()
        # 응답 패킷 구조 상수 추가
        self.RESPONSE_HEADER = bytes.fromhex("022c00")
        self.RESPONSE_COMMAND = bytes.fromhex("53420000000000")
    
    def parse_device_status_packet(self, packet):
        """
        장비 상태 응답 패킷을 파싱하여 활성화된 장비 목록을 추출
        
        Parameters:
        -----------
        packet : bytes
            파싱할 패킷 데이터
            
        Returns:
        --------
        list
            활성화된 장비 좌표 리스트 [(row, col), ...]
        """
        if len(packet) < 44:  # 44바이트 이상이면 정상
            print(f"[!] 패킷 길이 오류: {len(packet)}바이트 (최소 44바이트 필요)")
            return []
        
        # 패킷 유효성 검사 (송신 패킷과 응답 패킷 모두 지원)
        if not self._validate_response_packet(packet):
            print("[!] 패킷 유효성 검사 실패")
            return []
        
        active_devices = []
        
        # 각 행의 바이트 위치에서 비트를 확인하여 활성화된 장비 추출
        for row in range(1, 5):  # 1~4행
            for group in range(2):  # 0: 1~8열, 1: 9~16열
                byte_pos = self.BYTE_MAP[(row, group)]
                byte_value = packet[byte_pos]
                
                # 각 비트를 확인하여 활성화된 장비 찾기
                for bit_pos in range(8):
                    if byte_value & (1 << bit_pos):
                        # 비트 위치를 열 번호로 변환
                        if group == 0:  # 1~8열
                            col = bit_pos + 1
                        else:  # 9~16열
                            col = bit_pos + 9
                        
                        active_devices.append((row, col))
                        print(f"[*] 활성화된 장비 발견: ({row}, {col}) -> 바이트 {byte_pos}, 비트 {bit_pos}")
        
        print(f"[*] 총 {len(active_devices)}개의 활성화된 장비 발견")
        return active_devices
    
    def parse_device_status_packet_to_dict(self, packet):
        """
        장비 상태 응답 패킷을 파싱하여 전체 장비 상태 딕셔너리로 반환
        """
        if len(packet) < 44:  # 44바이트 이상이면 정상
            print(f"[!] 패킷 길이 오류: {len(packet)}바이트 (최소 44바이트 필요)")
            return {}
        
        # 패킷 유효성 검사 (송신 패킷과 응답 패킷 모두 지원)
        if not self._validate_response_packet(packet):
            print("[!] 패킷 유효성 검사 실패")
            return {}
        
        device_status = {}
        
        # 모든 장비를 먼저 OFF 상태로 초기화
        for row in range(1, 5):
            for col in range(1, 17):
                device_status[(row, col)] = False
        
        # 활성화된 장비만 ON 상태로 설정
        active_devices = self.parse_device_status_packet(packet)
        for row, col in active_devices:
            device_status[(row, col)] = True
        
        return device_status
    
    def parse_device_status_packet_to_rooms(self, packet):
        """
        장비 상태 응답 패킷을 파싱하여 활성화된 방 번호 목록으로 반환
        
        Parameters:
        -----------
        packet : bytes
            파싱할 패킷 데이터
            
        Returns:
        --------
        set
            활성화된 방 번호 집합 (예: {101, 205, 312})
        """
        active_devices = self.parse_device_status_packet(packet)
        active_rooms = set()
        
        for row, col in active_devices:
            room_number = row * 100 + col
            active_rooms.add(room_number)
        
        return active_rooms
    
    def _validate_response_packet(self, packet):
        """
        응답 패킷 유효성 검사 (송신 패킷과 응답 패킷 모두 지원)
        """
        # 기본 길이 검사 (44바이트 이상이면 정상)
        if len(packet) < 44:
            print(f"[!] 패킷 길이 오류: {len(packet)}바이트 (최소 44바이트 필요)")
            return False
        
        # 헤더 검사 (송신 패킷 또는 응답 패킷)
        if packet[0:3] == self.HEADER:
            # 송신 패킷 구조
            expected_command = self.COMMAND
            packet_type = "송신"
        elif packet[0:3] == self.RESPONSE_HEADER:
            # 응답 패킷 구조
            expected_command = self.RESPONSE_COMMAND
            packet_type = "응답"
        else:
            print(f"[!] 헤더 오류: {packet[0:3].hex()} (예상: {self.HEADER.hex()} 또는 {self.RESPONSE_HEADER.hex()})")
            return False
        
        # 명령어 검사
        if packet[3:10] != expected_command:
            print(f"[!] 명령어 오류: {packet[3:10].hex()} (예상: {expected_command.hex()})")
            return False
        
        # 체크섬 검사
        if packet_type == "송신":
            calculated_checksum = self.calculate_checksum(packet)
            received_checksum = packet[43]
            if calculated_checksum != received_checksum:
                print(f"[!] 체크섬 오류: 계산값 {calculated_checksum:02x}, 수신값 {received_checksum:02x}")
                return False
        else:
            # 응답 패킷 체크섬: 0~42번 XOR + 0x03 == 43번 바이트
            xor_chk = 0
            for b in packet[:43]:
                xor_chk ^= b
            calc_chk = (xor_chk + 0x03) & 0xFF
            received_checksum = packet[43]
            if calc_chk != received_checksum:
                print(f"[!] 응답 체크섬 오류: 계산값 {calc_chk:02x}, 수신값 {received_checksum:02x}")
                return False
            else:
                print(f"[*] 응답 패킷 체크섬 정상: {calc_chk:02x}")
        
        # 푸터 검사
        if len(packet) == 44:
            # 44바이트 응답 패킷: 마지막 바이트가 03
            if packet[43] != 0x03:
                print(f"[!] 푸터 오류: {packet[43]:02x} (예상: 03)")
                return False
        else:
            # 46바이트 패킷: 마지막 2바이트가 0300
            if packet[44:46] != self.FOOTER:
                print(f"[!] 푸터 오류: {packet[44:46].hex()} (예상: {self.FOOTER.hex()})")
                return False
        
        print(f"[*] {packet_type} 패킷 유효성 검사 통과")
        return True
    
    def print_packet_analysis_with_devices(self, packet):
        """
        패킷 분석 결과와 활성화된 장비 목록을 함께 출력
        
        Parameters:
        -----------
        packet : bytes
            분석할 패킷 데이터
        """
        # 기본 패킷 분석 출력
        self.print_packet_analysis(packet)
        
        # 활성화된 장비 목록
        active_devices = self.parse_device_status_packet(packet)
        if active_devices:
            print(f"\n활성화된 장비: {active_devices}")
        else:
            print("\n활성화된 장비: 없음")

    def print_device_matrix_from_packet(self, packet):
        """
        응답 패킷을 4x16 도식(행렬)으로 시각화하여 출력합니다.
        ON은 ●, OFF는 ○로 표시합니다.
        """
        device_status = self.parse_device_status_packet_to_dict(packet)
        print("\n장비 상태 행렬:")
        for row in range(1, 5):
            line = ''
            for col in range(1, 17):
                line += '●' if device_status.get((row, col), False) else '○'
            print(f"{row}행: {line}")
        print("=========================")

# 싱글톤 인스턴스 생성
packet_parser = PacketParser() 
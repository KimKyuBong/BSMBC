#!/usr/bin/env python3
"""
패킷 베이스 모듈
패킷 빌더와 파서의 공통 기능을 제공합니다.
"""

class PacketBase:
    """
    패킷 베이스 클래스
    패킷 빌더와 파서의 공통 기능을 정의합니다.
    """
    
    # 패킷 구조 상수
    PACKET_SIZE = 46
    HEADER = bytes.fromhex("022d00")
    COMMAND = bytes.fromhex("43420100000000")
    FOOTER = bytes.fromhex("0300")
    
    # 바이트 매핑: 캡처 데이터 분석 결과에 따라 수정
    BYTE_MAP = {
        (1, 0): 10, (1, 1): 11,  # 1행 1~8열, 9~16열
        (2, 0): 14, (2, 1): 15,  # 2행 1~8열, 9~16열
        (3, 0): 18, (3, 1): 19,  # 3행 1~8열, 9~16열
        (4, 0): 22, (4, 1): 23,  # 4행 1~8열, 9~16열
    }
    
    def __init__(self):
        pass
    
    def calculate_checksum(self, packet):
        """
        패킷의 체크섬을 계산하는 함수
        
        Parameters:
        -----------
        packet : bytearray or bytes
            체크섬을 계산할 패킷
            
        Returns:
        --------
        int
            계산된 체크섬 값
        """
        checksum = 0
        # 패킷의 처음부터 42바이트까지 XOR 연산 (실제 패킷 분석 결과)
        for i in range(0, 43):
            checksum ^= packet[i]
        return checksum
    
    def validate_packet(self, packet):
        """
        패킷 유효성 검사
        
        Parameters:
        -----------
        packet : bytes
            검사할 패킷 데이터
            
        Returns:
        --------
        bool
            유효성 검사 결과
        """
        # 기본 길이 검사
        if len(packet) != self.PACKET_SIZE:
            print(f"[!] 패킷 길이 오류: {len(packet)}바이트 (예상: {self.PACKET_SIZE}바이트)")
            return False
        
        # 헤더 검사
        if packet[0:3] != self.HEADER:
            print(f"[!] 헤더 오류: {packet[0:3].hex()} (예상: {self.HEADER.hex()})")
            return False
        
        # 체크섬 검사
        calculated_checksum = self.calculate_checksum(packet)
        received_checksum = packet[43]
        
        if calculated_checksum != received_checksum:
            print(f"[!] 체크섬 오류: 계산값 {calculated_checksum:02x}, 수신값 {received_checksum:02x}")
            return False
        
        # 푸터 검사
        if packet[44:46] != self.FOOTER:
            print(f"[!] 푸터 오류: {packet[44:46].hex()} (예상: {self.FOOTER.hex()})")
            return False
        
        return True
    
    def get_byte_bit_position(self, row, col):
        """
        캡처 패킷과 100% 일치하는 바이트/비트 매핑 (8열씩 바이트가 바뀌는 구조)
        row: 1~4, col: 1~16
        
        Parameters:
        -----------
        row : int
            행 번호 (1-4)
        col : int
            열 번호 (1-16)
            
        Returns:
        --------
        tuple
            (byte_pos, bit_pos) 튜플
        """
        # 1~8열, 9~16열을 각각 별도의 바이트로 취급
        if 1 <= col <= 8:
            group = 0
            bit_pos = (col - 1) % 8
        else:
            group = 1
            bit_pos = (col - 9) % 8
        
        byte_pos = self.BYTE_MAP[(row, group)]
        return byte_pos, bit_pos
    
    def get_coordinate_from_byte_bit(self, byte_pos, bit_pos):
        """
        바이트/비트 위치에서 좌표를 역산
        
        Parameters:
        -----------
        byte_pos : int
            바이트 위치
        bit_pos : int
            비트 위치 (0-7)
            
        Returns:
        --------
        tuple or None
            (row, col) 좌표 또는 None
        """
        # 바이트 위치에서 행과 그룹 찾기
        for (row, group), pos in self.BYTE_MAP.items():
            if pos == byte_pos:
                # 비트 위치에서 열 번호 계산
                if group == 0:  # 1~8열
                    col = bit_pos + 1
                else:  # 9~16열
                    col = bit_pos + 9
                return (row, col)
        return None
    
    def create_base_packet(self):
        """
        기본 패킷 구조 생성
        
        Returns:
        --------
        bytearray
            기본 패킷 구조
        """
        packet = bytearray(self.PACKET_SIZE)
        
        # 기본 헤더 설정
        packet[0:3] = self.HEADER
        packet[3:10] = self.COMMAND
        
        # 나머지는 0으로 초기화 (이미 0)
        
        return packet
    
    def finalize_packet(self, packet):
        """
        패킷 완성 (체크섬 및 푸터 설정)
        
        Parameters:
        -----------
        packet : bytearray
            완성할 패킷
            
        Returns:
        --------
        bytes
            완성된 패킷
        """
        # 체크섬 계산 및 설정
        checksum = self.calculate_checksum(packet)
        packet[42] = 0x00
        packet[43] = checksum
        packet[44:46] = self.FOOTER
        
        return bytes(packet)
    
    def print_packet_analysis(self, packet):
        """
        패킷 분석 결과를 출력
        
        Parameters:
        -----------
        packet : bytes
            분석할 패킷 데이터
        """
        print("\n=== 패킷 분석 결과 ===")
        print(f"패킷 길이: {len(packet)}바이트")
        print(f"패킷 헥스: {packet.hex()}")
        
        # 헤더 분석
        print(f"헤더: {packet[0:3].hex()}")
        print(f"명령어: {packet[3:10].hex()}")
        
        # 장비 상태 바이트 분석
        print("\n장비 상태 바이트:")
        for row in range(1, 5):
            for group in range(2):
                byte_pos = self.BYTE_MAP[(row, group)]
                byte_value = packet[byte_pos]
                col_range = "1-8" if group == 0 else "9-16"
                print(f"  {row}행 {col_range}열 (바이트 {byte_pos}): {byte_value:02x} ({bin(byte_value)[2:].zfill(8)})")
        
        # 체크섬 분석
        calculated_checksum = self.calculate_checksum(packet)
        received_checksum = packet[43]
        print(f"\n체크섬: 계산값 {calculated_checksum:02x}, 수신값 {received_checksum:02x}")
        print(f"푸터: {packet[44:46].hex()}")
        print("=" * 30) 
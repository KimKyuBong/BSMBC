#!/usr/bin/env python3
"""
패킷 빌더 모듈
방송 시스템 제어용 패킷을 생성합니다.
"""

from .packet_base import PacketBase

class PacketBuilder(PacketBase):
    """
    패킷 빌더 클래스
    4행 16열 행렬에 대한 장비 온오프 패킷을 생성합니다.
    """
    def __init__(self):
        super().__init__()
    
    def create_coordinate_payload(self, row, col, state=1):
        """
        특정 좌표(row, col)의 장비를 제어하는 패킷 생성
        
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
        bytes
            생성된 패킷 페이로드
        """
        # 좌표 유효성 검사
        if not (1 <= row <= 4 and 1 <= col <= 16):
            print(f"[!] 잘못된 좌표: ({row}, {col}). 1-4행, 1-16열 범위여야 합니다.")
            return None
        
        # 기본 페이로드 생성
        payload = self.create_base_packet()
        
        # 좌표를 바이트/비트 위치로 변환
        byte_pos, bit_pos = self.get_byte_bit_position(row, col)
        
        # 비트 설정
        if state:
            payload[byte_pos] |= (1 << bit_pos)
            print(f"[*] 장치 활성화: ({row}, {col}) -> 바이트 {byte_pos}, 비트 {bit_pos}")
        else:
            payload[byte_pos] &= ~(1 << bit_pos)
            print(f"[*] 장치 비활성화: ({row}, {col}) -> 바이트 {byte_pos}, 비트 {bit_pos}")
        
        # 패킷 완성
        return self.finalize_packet(payload)
    
    def create_multiple_coordinates_payload(self, coordinates, state=1):
        """
        여러 좌표의 장비를 동시에 제어하는 패킷 생성
        
        Parameters:
        -----------
        coordinates : list
            좌표 리스트 [(row, col), ...]
        state : int
            0: 끄기, 1: 켜기
            
        Returns:
        --------
        bytes
            생성된 패킷 페이로드
        """
        # 기본 페이로드 생성
        payload = self.create_base_packet()
        
        # 각 좌표에 대해 비트 설정
        for row, col in coordinates:
            if not (1 <= row <= 4 and 1 <= col <= 16):
                print(f"[!] 잘못된 좌표 무시: ({row}, {col})")
                continue
            
            byte_pos, bit_pos = self.get_byte_bit_position(row, col)
            
            if state:
                payload[byte_pos] |= (1 << bit_pos)
                print(f"[*] 장치 활성화: ({row}, {col}) -> 바이트 {byte_pos}, 비트 {bit_pos}")
            else:
                payload[byte_pos] &= ~(1 << bit_pos)
                print(f"[*] 장치 비활성화: ({row}, {col}) -> 바이트 {byte_pos}, 비트 {bit_pos}")
        
        # 패킷 완성
        return self.finalize_packet(payload)
    
    def create_byte_bit_payload(self, byte_pos, bit_pos, state=1):
        """
        특정 바이트/비트 위치의 장비를 제어하는 패킷 생성
        
        Parameters:
        -----------
        byte_pos : int
            바이트 위치 (0-7)
        bit_pos : int
            비트 위치 (0-7)
        state : int
            0: 끄기, 1: 켜기
            
        Returns:
        --------
        bytes
            생성된 패킷 페이로드
        """
        # 위치 유효성 검사
        if not (0 <= byte_pos <= 7 and 0 <= bit_pos <= 7):
            print(f"[!] 잘못된 바이트/비트 위치: 바이트 {byte_pos}, 비트 {bit_pos}")
            return None
        
        # 기본 페이로드 생성
        payload = self.create_base_packet()
        
        # 비트 설정
        if state:
            payload[byte_pos] |= (1 << bit_pos)
            print(f"[*] 장치 활성화: 바이트 {byte_pos}, 비트 {bit_pos}")
        else:
            payload[byte_pos] &= ~(1 << bit_pos)
            print(f"[*] 장치 비활성화: 바이트 {byte_pos}, 비트 {bit_pos}")
        
        # 패킷 완성
        return self.finalize_packet(payload)
    
    def create_all_off_payload(self):
        """
        모든 장비를 끄는 패킷 생성
        
        Returns:
        --------
        bytes
            전체 OFF 패킷
        """
        # 기본 페이로드 생성 (이미 모든 비트가 0)
        payload = self.create_base_packet()
        
        # 패킷 완성
        result = self.finalize_packet(payload)
        print("[*] 전체 장비 OFF 패킷 생성")
        return result
    
    def create_current_state_payload(self, active_rooms):
        """
        현재 활성화된 방들의 상태를 기반으로 패킷 생성
        
        Parameters:
        -----------
        active_rooms : set
            활성화된 방들의 집합 (예: {101, 205, 312})
            
        Returns:
        --------
        bytes
            생성된 패킷 페이로드
        """
        print(f"[*] PacketBuilder: 현재 상태 패킷 생성 시작 (활성 방: {sorted(active_rooms)})")
        
        # 기본 페이로드 생성
        payload = self.create_base_packet()
        print(f"[*] PacketBuilder: 기본 패킷 생성 완료")
        
        # 활성화된 방들에 대해 비트 설정
        activated_count = 0
        for room in active_rooms:
            # 방 번호를 행/열로 변환 (예: 101 -> 1행 1열)
            row = room // 100
            col = room % 100
            
            if 1 <= row <= 4 and 1 <= col <= 16:
                byte_pos, bit_pos = self.get_byte_bit_position(row, col)
                payload[byte_pos] |= (1 << bit_pos)
                activated_count += 1
                print(f"[*] PacketBuilder: 활성화된 방 {room} ({row}행 {col}열) -> 바이트 {byte_pos}, 비트 {bit_pos}")
            else:
                print(f"[!] PacketBuilder: 잘못된 방 번호 무시: {room}")
        
        print(f"[*] PacketBuilder: 총 {activated_count}개 방 활성화 설정 완료")
        
        # 패킷 완성
        result = self.finalize_packet(payload)
        print(f"[*] PacketBuilder: 패킷 완성 완료 ({len(result)}바이트)")
        
        return result

# 싱글톤 인스턴스 생성
packet_builder = PacketBuilder() 
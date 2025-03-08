#!/usr/bin/env python3
"""
장치 매핑 모듈
장치 좌표와 이름 간의 매핑을 관리합니다.
"""

class DeviceMapper:
    """
    장치 매퍼 클래스
    장치 좌표, 이름, 비트 위치 간의 매핑을 처리합니다.
    """
    def __init__(self):
        # 장치 매핑 테이블 초기화 (좌표 -> 장치명)
        self.device_map = {
            # 1학년 (1행 1-4열)
            (0, 0): "1-1", (0, 1): "1-2", (0, 2): "1-3", (0, 3): "1-4",
            # 2학년 (1행 8-11열)
            (0, 8): "2-1", (0, 9): "2-2", (0, 10): "2-3", (0, 11): "2-4",
            # 3학년 (2행 1-4열)
            (1, 0): "3-1", (1, 1): "3-2", (1, 2): "3-3", (1, 3): "3-4",
            # 특수실 (3행)
            (2, 0): "선생영역", (2, 1): "시청각실", (2, 2): "체육관", (2, 3): "보건실부",
            (2, 4): "교무실", (2, 5): "과학실비", (2, 6): "강당", (2, 7): "방송실",
            # 특수실 (4행)
            (3, 0): "별관1-1", (3, 1): "별관1-2", (3, 2): "별관1-3", (3, 3): "별관2-1",
            (3, 4): "별관2-2", (3, 5): "지문등고", (3, 6): "무등12", (3, 7): "경이포구",
            # 특수실 (5행)
            (4, 0): "운동장", (4, 1): "옥의"
        }
        
        # 역방향 매핑 생성 (장치명 -> 좌표)
        self.device_to_coord = {v: k for k, v in self.device_map.items()}
        
        # 상태 코드 매핑 테이블
        self.STATE_CODES = {
            frozenset([]): 0x00,                # 모두 꺼짐
            frozenset([301]): 0x03,             # 3학년 1반만 켜짐
            frozenset([301, 302]): 0x01,        # 3학년 1,2반 모두 켜짐
            # 추가 상태 코드는 더 많은 테스트를 통해 확장 가능
        }
        
        # 상태 코드 역매핑 (서버 응답 해석용)
        self.REVERSE_STATE_CODES = {
            0x00: frozenset([]),                # 모두 꺼짐
            0x03: frozenset([301]),             # 3학년 1반만 켜짐
            0x01: frozenset([301, 302]),        # 3학년 1,2반 모두 켜짐
            # 추가 상태 코드는 더 많은 테스트를 통해 확장 가능
        }
    
    def get_device_name(self, row, col):
        """좌표로 장치명 찾기"""
        return self.device_map.get((row, col), "알 수 없음")
    
    def get_device_coords(self, device_name):
        """장치명으로 좌표 찾기"""
        return self.device_to_coord.get(device_name, None)
    
    def get_byte_bit_position(self, row, col):
        """좌표에 따른 바이트 위치와 비트 위치 계산"""
        # 행에 따른 베이스 바이트 위치
        if row == 0:     # 첫 번째 행 (1학년/2학년)
            if col < 8:  # 왼쪽 8개 (1학년 영역)
                byte_pos = 10  # 패킷의 11번째 바이트
                bit_pos = col
            else:        # 오른쪽 8개 (2학년 영역)
                byte_pos = 11  # 패킷의 12번째 바이트
                bit_pos = col - 8
        elif row == 1:   # 두 번째 행 (3학년)
            byte_pos = 12  # 패킷의 13번째 바이트 (2바이트 건너뜀)
            bit_pos = col
        elif row == 2:   # 세 번째 행 (특수실 첫 번째 그룹)
            byte_pos = 15  # 패킷의 16번째 바이트 (2바이트 건너뜀)
            bit_pos = col
        elif row == 3:   # 네 번째 행 (특수실 두 번째 그룹)
            byte_pos = 16  # 패킷의 17번째 바이트
            bit_pos = col
        elif row == 4:   # 다섯 번째 행 (운동장, 옥의)
            byte_pos = 17  # 패킷의 18번째 바이트
            bit_pos = col
        else:
            return None, None
        
        return byte_pos, bit_pos
    
    def get_state_code(self, active_rooms):
        """
        현재 활성화된 반 목록에 따른 상태 코드를 반환합니다.
        
        Parameters:
        -----------
        active_rooms : set
            활성화된 방 ID 집합
            
        Returns:
        --------
        int
            상태 코드 값
        """
        frozen_set = frozenset(active_rooms)
        if frozen_set in self.STATE_CODES:
            return self.STATE_CODES[frozen_set]
        else:
            print(f"[!] 매핑되지 않은 상태 조합: {active_rooms}")
            return 0x00  # 기본값
    
    def get_rooms_from_state_code(self, state_code):
        """
        상태 코드로부터 활성화된 방 목록을 반환합니다.
        
        Parameters:
        -----------
        state_code : int
            서버에서 받은 상태 코드
            
        Returns:
        --------
        set
            활성화된 방 ID 집합
        """
        if state_code in self.REVERSE_STATE_CODES:
            return set(self.REVERSE_STATE_CODES[state_code])
        else:
            print(f"[!] 알 수 없는 상태 코드: 0x{state_code:02X}")
            return set()

# 싱글톤 인스턴스 생성
device_mapper = DeviceMapper() 
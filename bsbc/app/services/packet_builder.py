#!/usr/bin/env python3
"""
패킷 빌더 모듈
방송 시스템 제어용 패킷을 생성합니다.
"""
from ..core.device_mapping import device_mapper

class PacketBuilder:
    """
    패킷 빌더 클래스
    다양한 형태의 제어 패킷을 생성합니다.
    """
    def __init__(self):
        # 장치 매퍼 인스턴스 저장
        self.device_mapper = device_mapper
    
    def calculate_checksum(self, packet):
        """
        패킷의 체크섬을 계산하는 함수
        
        Parameters:
        -----------
        packet : bytearray
            체크섬을 계산할 패킷
            
        Returns:
        --------
        int
            계산된 체크섬 값
        """
        checksum = 0
        # 패킷의 처음부터 23바이트까지 XOR 연산
        for i in range(0, 23):
            checksum ^= packet[i]
        return checksum
    
    def create_command_payload(self, command_type=0x01, channel=0x00, state=0x00):
        """
        방송 장비 제어 패킷 페이로드 생성 함수 (실제 패킷 분석 결과 기반)
        
        Parameters:
        ----------
        command_type : int
            명령 타입 (0x01: 조명/기기 제어)
        channel : int
            제어할 장비 채널 번호 (0~255)
        state : int
            장비 상태 (0: OFF, 1: ON)
            
        Returns:
        -------
        bytes
            생성된 패킷 페이로드
        """
        # 기본 채널(0x00)은 상태에 따라 다른 패턴 사용
        if channel == 0x00:
            if state == 0x00:  # 끄기 상태
                # 패킷 구조 (끄기 - 모든 패딩값 0x00)
                # 레거시 헤더 형식으로 복원
                payload = bytearray(46)  # 46바이트 배열 생성
                
                # 헤더 설정 (02 2d 00)
                payload[0:3] = bytes.fromhex("022d00") 
                payload[3:10] = bytes.fromhex("43420100000000")
                
                # 패딩 영역 (0-값으로 채움, 이미 0으로 초기화되어 있음)
                
                # 체크섬 계산 및 설정
                checksum = self.calculate_checksum(payload)
                
                # 패킷 길이 및 종료 바이트 설정
                payload[42] = 0x00  # 첫 번째 바이트
                payload[43] = checksum  # 두 번째 바이트에 체크섬 설정
                payload[44] = 0x03  # 세 번째 바이트 (종료 바이트)
                payload[45] = 0x00  # 네 번째 바이트
                
                return bytes(payload)
            else:  # 켜기 상태
                # 정확히 46바이트가 되도록 직접 바이트 배열 생성
                packet = bytearray(46)  # 46바이트 배열 생성
                
                # 헤더 설정 (02 2d 00)
                packet[0:3] = bytes.fromhex("022d00")
                packet[3:10] = bytes.fromhex("43420100010000")
                
                # 패딩 영역 (0-값으로 채움, 이미 0으로 초기화되어 있음)
                
                # 0x40 값 위치 설정 (인덱스 22에 0x40 배치)
                packet[22] = 0x40
                
                # FF 패턴 설정 (인덱스 26, 30, 34에 0xFFFF 패턴 배치)
                ff_pattern = bytes.fromhex("ffff0000")
                packet[26:30] = ff_pattern
                packet[30:34] = ff_pattern
                packet[34:38] = ff_pattern
                
                # 체크섬 계산 및 설정
                checksum = self.calculate_checksum(packet)
                
                # 패킷 길이 및 종료 바이트 설정
                packet[42] = 0x00  # 첫 번째 바이트
                packet[43] = checksum  # 두 번째 바이트에 체크섬 설정
                packet[44] = 0x03  # 세 번째 바이트 (종료 바이트)
                packet[45] = 0x00  # 네 번째 바이트
                
                return bytes(packet)
        
        # 다른 일반 채널은 새로운 방식 적용
        packet = bytearray(46)  # 총 46바이트 패킷
        
        # 1. 패킷 헤더 (3바이트)
        packet[0:3] = bytes.fromhex("022d00")  # 헤더 설정 (02 2d 00)
        
        # 2. 나머지 헤더 및 명령 정보
        packet[3:5] = bytes.fromhex("4342")  # 고정값 'CB'
        packet[5] = command_type  # 명령 타입 (0x01: 조명/기기 제어)
        packet[6] = channel       # 채널 (0~255)
        packet[7] = state         # 상태 (0: OFF, 1: ON)
        packet[8:10] = bytes.fromhex("0000")  # 패딩 바이트
        
        # 3. 패딩 영역 (33바이트, 인덱스 10~42)
        for i in range(10, 42):
            packet[i] = 0x00
        
        # 체크섬 계산 및 설정
        checksum = self.calculate_checksum(packet)
        
        # 패킷 길이 및 종료 바이트 설정
        packet[42] = 0x00  # 첫 번째 바이트
        packet[43] = checksum  # 두 번째 바이트에 체크섬 설정
        packet[44] = 0x03  # 세 번째 바이트 (종료 바이트)
        packet[45] = 0x00  # 네 번째 바이트
        
        return bytes(packet)
    
    def create_device_payload(self, device_name, state=1):
        """장치명을 기준으로 제어 패킷 생성
        
        Parameters:
        -----------
        device_name : str
            제어할 장치명 (예: "1-1", "선생영역")
        state : int
            0: 끄기, 1: 켜기
        """
        # 기본 페이로드 생성 (46바이트)
        payload = bytearray(46)
        
        # 기본 헤더 - 레거시 형식으로 복원 (02 2d 00)
        payload[0:3] = bytes.fromhex("022d00")  # 원래 헤더 형식 (02 2d 00)
        payload[3:10] = bytes.fromhex("43420100000000")  # 나머지 헤더 부분
        
        # 장치명에 따라 직접 바이트 위치 설정
        # 이미지의 레이아웃에 맞게 매핑
        try:
            # 학년-반 형식 (예: "1-1", "3-2")
            if '-' in device_name and device_name[0].isdigit():
                grade, class_num = device_name.split('-')
                grade = int(grade)
                class_num = int(class_num)
                
                # 이미지 레이아웃에 따른 바이트 위치 매핑
                if grade == 1:  # 1학년 (1-1, 1-2, 1-3, 1-4)
                    if 1 <= class_num <= 4:
                        byte_pos = 10  # 11번째 바이트 
                        bit_pos = class_num - 1
                    else:
                        print(f"[!] 1학년에는 1반부터 4반까지만 있습니다: {class_num}")
                        return None
                elif grade == 2:  # 2학년 (2-1, 2-2, 2-3, 2-4)
                    if 1 <= class_num <= 4:
                        byte_pos = 10  # 11번째 바이트
                        bit_pos = class_num + 7  # 시작 위치 8부터
                    else:
                        print(f"[!] 2학년에는 1반부터 4반까지만 있습니다: {class_num}")
                        return None
                elif grade == 3:  # 3학년 (3-1, 3-2, 3-3, 3-4)
                    if 1 <= class_num <= 4:
                        byte_pos = 11  # 12번째 바이트
                        bit_pos = class_num - 1
                    else:
                        print(f"[!] 3학년에는 1반부터 4반까지만 있습니다: {class_num}")
                        return None
                else:
                    print(f"[!] 지원하지 않는 학년: {grade}")
                    return None
            # 특수 공간 처리 (이미지의 레이아웃 기반)
            else:
                # 특수 공간 매핑 (이미지에 표시된 순서대로)
                special_rooms = {
                    "교무실": (11, 4),  # 12번째 바이트, 4번 비트
                    "과학실": (11, 5),
                    "정의교실": (11, 6),
                    "남여휴게실": (11, 7),
                    "교무실2": (12, 0),  # 13번째 바이트, 0번 비트 
                    "학생식당": (12, 1),
                    "위클래식": (12, 2),
                    "프로그램실": (12, 3),
                    "교무2처": (12, 4),
                    "진로상담": (12, 5),
                    "모듈1실": (12, 6),
                    "정의교실2": (12, 7),
                    # 다음 행 (A1호실, B2호실 등)
                    "A1호실": (13, 0),  # 14번째 바이트, 0번 비트
                    "B2호실": (13, 1),
                    "A2호실": (13, 2),
                    "B3호실": (13, 3),
                    "방송실-1": (13, 4),
                    "방송실-2": (13, 5),
                    "방송실-3": (13, 6),
                    "별관1-1": (13, 7),
                    "별관2-1": (14, 0),  # 15번째 바이트, 0번 비트
                    "별관2-2": (14, 1),
                    "운동장": (14, 2),
                    "옥외": (14, 3)
                }
                
                if device_name in special_rooms:
                    byte_pos, bit_pos = special_rooms[device_name]
                else:
                    print(f"[!] 알 수 없는 특수 공간: {device_name}")
                    return None
            
            # 상태에 따라 비트 설정 또는 해제
            if state:
                payload[byte_pos] |= (1 << bit_pos)  # 비트 설정 (켜기)
            else:
                payload[byte_pos] &= ~(1 << bit_pos)  # 비트 해제 (끄기)
                
        except Exception as e:
            print(f"[!] 장치 패킷 생성 중 오류: {e}")
            return None
        
        # 체크섬 계산 및 설정
        checksum = self.calculate_checksum(payload)
        
        # 패킷 길이 및 종료 바이트 설정
        payload[42] = 0x00  # 첫 번째 바이트
        payload[43] = checksum  # 두 번째 바이트에 체크섬 설정
        payload[44] = 0x03  # 세 번째 바이트 (종료 바이트)
        payload[45] = 0x00  # 네 번째 바이트
        
        return payload
    
    def create_multi_device_payload(self, device_list, state=1):
        """여러 장치를 동시에 제어하는 패킷 생성
        
        Parameters:
        -----------
        device_list : list
            제어할 장치명 리스트 (예: ["1-1", "1-2", "선생영역"])
        state : int
            0: 끄기, 1: 켜기
        """
        # 기본 페이로드 생성 (46바이트)
        payload = bytearray(46)
        
        # 기본 헤더 - 레거시 형식으로 복원 (02 2d 00)
        payload[0:3] = bytes.fromhex("022d00")  # 원래 헤더 형식 (02 2d 00)
        payload[3:10] = bytes.fromhex("43420100000000")  # 나머지 헤더 부분
        
        # 각 장치별로 개별 페이로드 생성 후 비트 통합
        for device_name in device_list:
            device_payload = self.create_device_payload(device_name, state)
            if device_payload is None:
                continue
                
            # 장치별 페이로드의 데이터 부분(10~42 바이트)을 결합
            for i in range(10, 42):
                payload[i] |= device_payload[i]
        
        # 체크섬 계산 및 설정
        checksum = self.calculate_checksum(payload)
        
        # 패킷 길이 및 종료 바이트 설정
        payload[42] = 0x00  # 첫 번째 바이트
        payload[43] = checksum  # 두 번째 바이트에 체크섬 설정
        payload[44] = 0x03  # 세 번째 바이트 (종료 바이트)
        payload[45] = 0x00  # 네 번째 바이트
        
        return payload
    
    def create_current_state_payload(self, active_rooms=None):
        """
        현재 활성화된 방 목록을 기반으로 전체 시스템 상태 패킷 생성
        
        Parameters:
        -----------
        active_rooms : set
            활성화된 방 ID 집합 (예: {301, 302} - 3학년 1반과 2반이 활성화)
            
        Returns:
        --------
        bytes
            시스템 상태가 담긴 패킷 페이로드
        """
        # 기본 페이로드 생성 (46바이트)
        payload = bytearray(46)
        
        # 기본 헤더 - 레거시 형식으로 복원 (02 2d 00)
        payload[0:3] = bytes.fromhex("022d00")  # 원래 헤더 형식 (02 2d 00)
        payload[3:10] = bytes.fromhex("43420100000000")  # 나머지 헤더 부분
        
        # active_rooms가 지정되지 않으면 빈 상태 반환
        if not active_rooms:
            # 모든 장치가 비활성화된 상태
            # 체크섬 계산 및 설정
            checksum = self.calculate_checksum(payload)
            
            # 패킷 길이 및 종료 바이트 설정
            payload[42] = 0x00  # 첫 번째 바이트
            payload[43] = checksum  # 두 번째 바이트에 체크섬 설정
            payload[44] = 0x03  # 세 번째 바이트 (종료 바이트)
            payload[45] = 0x00  # 네 번째 바이트
            return payload
        
        # 각 활성화된 방의 비트 설정
        for room_id in active_rooms:
            try:
                # 방 ID를 분석하여 학년과 반 추출
                # 예: 301 -> 3학년 1반
                if 100 <= room_id < 1000:  # 정상적인 방 ID 형식 (3자리)
                    grade = room_id // 100  # 앞자리 (학년)
                    class_num = room_id % 100  # 뒤 두자리 (반)
                    
                    # 이미지 레이아웃에 따른 매핑 확인
                    if grade == 1:  # 1학년
                        if 1 <= class_num <= 4:
                            byte_pos = 10  # 11번째 바이트
                            bit_pos = class_num - 1
                        else:
                            print(f"[!] 1학년에는 1반부터 4반까지만 있습니다: {class_num}")
                            continue
                    elif grade == 2:  # 2학년
                        if 1 <= class_num <= 4:
                            byte_pos = 10  # 11번째 바이트
                            bit_pos = class_num + 7  # 시작 위치 8부터
                        else:
                            print(f"[!] 2학년에는 1반부터 4반까지만 있습니다: {class_num}")
                            continue
                    elif grade == 3:  # 3학년
                        if 1 <= class_num <= 4:
                            byte_pos = 11  # 12번째 바이트
                            bit_pos = class_num - 1
                        else:
                            print(f"[!] 3학년에는 1반부터 4반까지만 있습니다: {class_num}")
                            continue
                    else:
                        print(f"[!] 지원하지 않는 학년: {grade}")
                        continue
                    
                    # 비트 설정 (활성화)
                    payload[byte_pos] |= (1 << bit_pos)
                    
                # 특수 공간 ID 처리 (1000 이상)
                else:
                    # 특수 공간 매핑 (ID -> 바이트/비트 위치)
                    special_rooms_map = {
                        1001: (11, 4),  # "교무실"
                        1002: (11, 5),  # "과학실"
                        1003: (11, 6),  # "정의교실"
                        1004: (11, 7),  # "남여휴게실"
                        1005: (12, 0),  # "교무실2"
                        1006: (12, 1),  # "학생식당"
                        1007: (12, 2),  # "위클래식"
                        1008: (12, 3),  # "프로그램실"
                        1009: (12, 4),  # "교무2처"
                        1010: (12, 5),  # "진로상담"
                        1011: (12, 6),  # "모듈1실"
                        1012: (12, 7),  # "정의교실2"
                        1013: (13, 0),  # "A1호실"
                        1014: (13, 1),  # "B2호실"
                        1015: (13, 2),  # "A2호실"
                        1016: (13, 3),  # "B3호실"
                        1017: (13, 4),  # "방송실-1"
                        1018: (13, 5),  # "방송실-2"
                        1019: (13, 6),  # "방송실-3"
                        1020: (13, 7),  # "별관1-1"
                        1021: (14, 0),  # "별관2-1"
                        1022: (14, 1),  # "별관2-2"
                        1023: (14, 2),  # "운동장"
                        1024: (14, 3)   # "옥외"
                    }
                    
                    if room_id in special_rooms_map:
                        byte_pos, bit_pos = special_rooms_map[room_id]
                        # 비트 설정 (활성화)
                        payload[byte_pos] |= (1 << bit_pos)
                    else:
                        print(f"[!] 알 수 없는 특수 공간 ID: {room_id}")
                        continue
            except Exception as e:
                print(f"[!] 방 ID 처리 중 오류 ({room_id}): {e}")
                continue
        
        # 체크섬 계산 및 설정
        checksum = self.calculate_checksum(payload)
        
        # 패킷 길이 및 종료 바이트 설정
        payload[42] = 0x00  # 첫 번째 바이트
        payload[43] = checksum  # 두 번째 바이트에 체크섬 설정 
        payload[44] = 0x03  # 세 번째 바이트 (종료 바이트)
        payload[45] = 0x00  # 네 번째 바이트
        
        return payload
    
    def create_input_channel_payload(self, channel_id, state=1):
        """
        입력 채널 제어 패킷 생성
        
        Parameters:
        -----------
        channel_id : int
            제어할 입력 채널 ID (1~16)
        state : int
            0: 끄기, 1: 켜기
            
        Returns:
        --------
        bytes
            입력 채널 제어 패킷
        """
        if not 1 <= channel_id <= 16:
            print(f"[!] 잘못된 입력 채널 ID: {channel_id}. 1부터 16 사이의 값이어야 합니다.")
            return None
            
        # 패킷 생성 (18바이트)
        payload = bytearray(18)
        
        # 헤더 설정 (7바이트까지는 고정)
        payload[0:7] = bytes.fromhex("021100435640")
        payload[7] = 0x01  # 고정 값
        
        # 입력 채널 ID 설정
        payload[8] = channel_id
        
        # 채널 타입에 따라 제어 코드 결정
        # 1, 2, 11번 채널은 마이크 타입, 나머지는 라인 타입
        if channel_id in [1, 2, 11]:
            # 마이크 타입
            if state == 1:  # 켜기
                type_code = 0x01
            else:  # 끄기
                type_code = 0x21
        else:
            # 라인 타입
            if state == 1:  # 켜기
                type_code = 0x03
            else:  # 끄기
                type_code = 0x23
        
        # 패턴 설정
        payload[9] = 0xFF  # 고정값
        payload[10] = type_code  # 채널 타입과 상태 기반 제어 코드
        
        # 채널별 패턴 설정 (관찰된 실제 패킷 기반)
        if channel_id == 1:
            payload[11:15] = bytes.fromhex("00100501" if state == 1 else "00100500")
        elif channel_id == 3:
            payload[11:15] = bytes.fromhex("000F050A" if state == 1 else "000F0500")
        elif channel_id == 5:
            payload[11:15] = bytes.fromhex("000F050A" if state == 1 else "000F0500")
        elif channel_id == 7:
            payload[11:15] = bytes.fromhex("00110501" if state == 1 else "00110500")
        else:
            # 일반적인 패턴
            payload[11:15] = bytes.fromhex("00100501" if state == 1 else "00100500")
        
        # 체크섬 계산
        checksum = 0
        for i in range(0, 16):
            checksum ^= payload[i]
        
        # 체크섬 및 종료 바이트 설정
        payload[16] = checksum  # 체크섬
        payload[17] = 0x03      # 종료 바이트
        
        return bytes(payload)
    
    def create_all_input_channels_payload(self, state=1, channel_type="all"):
        """
        모든 입력 채널 또는 특정 타입의 모든 채널을 동시에 제어하는 패킷 생성
        
        Parameters:
        -----------
        state : int
            0: 모두 끄기, 1: 모두 켜기
        channel_type : str
            "mic": 마이크 타입 채널만, "line": 라인 타입 채널만, "all": 모든 채널
            
        Returns:
        --------
        bytes
            입력 채널 제어 패킷
        """
        # 패킷 생성 (18바이트)
        payload = bytearray(18)
        
        # 헤더 설정
        payload[0:7] = bytes.fromhex("021100435640")
        payload[7] = 0x01  # 고정 값
        
        # 전체 채널 설정 (0xFF = 전체 채널)
        payload[8] = 0xFF
        
        # 채널 타입에 따라 제어 코드 결정
        if channel_type == "mic":
            # 마이크 타입
            type_code = 0x01 if state == 1 else 0x21
        elif channel_type == "line":
            # 라인 타입
            type_code = 0x03 if state == 1 else 0x23
        else:
            # 기본값 - 마이크 타입 코드 사용
            type_code = 0x01 if state == 1 else 0x21
        
        # 패턴 설정
        payload[9] = 0xFF  # 고정값
        payload[10] = type_code  # 채널 타입과 상태 기반 제어 코드
        payload[11:15] = bytes.fromhex("00100501" if state == 1 else "00100500")
        
        # 체크섬 계산
        checksum = 0
        for i in range(0, 16):
            checksum ^= payload[i]
        
        # 체크섬 및 종료 바이트 설정
        payload[16] = checksum  # 체크섬
        payload[17] = 0x03      # 종료 바이트
        
        return bytes(payload)
            
# 싱글톤 인스턴스 생성
packet_builder = PacketBuilder() 
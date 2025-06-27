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
    
    def _get_special_space_byte_bit(self, room_id):
        """
        특수 공간 ID를 바이트/비트 위치로 매핑
        
        Parameters:
        -----------
        room_id : int
            특수 공간 ID (예: 1031, 1032, 1023 등)
            
        Returns:
        --------
        tuple
            (byte_pos, bit_pos) 또는 None
        """
        # 특수 공간 ID 매핑 (패킷 분석 결과 기반)
        special_space_mapping = {
            # 바이트 10 (비트 0-7): 1-8번째 특수 공간
            1031: (10, 0),  # 교행연회
            1032: (10, 1),  # 교사연구
            1033: (10, 2),  # 매점
            1034: (10, 3),  # 보건학부
            1035: (10, 4),  # 컴퓨터12
            1036: (10, 5),  # 과학준비
            1037: (10, 6),  # 창의준비
            1038: (10, 7),  # 남여휴게
            
            # 바이트 11 (비트 0-7): 9-16번째 특수 공간
            1039: (11, 0),  # 교무실
            1040: (11, 1),  # 학생식당
            1041: (11, 2),  # 위클회의
            1042: (11, 3),  # 프로그12
            1043: (11, 4),  # 전문교무
            1044: (11, 5),  # 진로상담
            1045: (11, 6),  # 모둠12
            1046: (11, 7),  # 창의공작
            
            # 바이트 12 (비트 0-7): 17-24번째 특수 공간
            1047: (12, 0),  # 본관1층
            1048: (12, 1),  # 융합관1층
            1049: (12, 2),  # 본관2층
            1050: (12, 3),  # 융합관2층
            1051: (12, 4),  # 융합관3층
            1052: (12, 5),  # 강당
            1053: (12, 6),  # 방송실
            1054: (12, 7),  # 별관1-1
            
            # 바이트 13 (비트 0-7): 25-32번째 특수 공간
            1055: (13, 0),  # 별관1-2
            1056: (13, 1),  # 별관1-3
            1057: (13, 2),  # 별관2-1
            1058: (13, 3),  # 별관2-2
            # 29, 30번째는 공백 (1059, 1060은 사용하지 않음)
            1061: (13, 6),  # 운동장 (31번째)
            1062: (13, 7),  # 옥외 (32번째)
            # 나머지 2개는 미사용 또는 향후 확장용
        }
        
        return special_space_mapping.get(room_id)
    
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
        try:
            # 장치 매퍼를 통해 장치명에 해당하는 좌표 얻기
            coords = self.device_mapper.get_device_coords(device_name)
            if coords is None:
                print(f"[!] 알 수 없는 장치명: {device_name}")
                return None
                
            # 좌표로부터 바이트 위치와 비트 위치 계산
            row, col = coords
            byte_pos, bit_pos = self.device_mapper.get_byte_bit_position(row, col)
            
            # 특수 공간인지 확인 (room_id가 1000 이상인 경우)
            room_id = self.device_mapper._get_device_id(device_name)
            if room_id and room_id >= 1000:
                # 특수 공간 ID를 바이트/비트로 매핑
                special_pos = self._get_special_space_byte_bit(room_id)
                if special_pos:
                    byte_pos, bit_pos = special_pos
                    print(f"[*] 특수 공간 처리: {device_name} (ID: {room_id}) -> 바이트 {byte_pos}, 비트 {bit_pos}")
                else:
                    print(f"[!] 알 수 없는 특수 공간 ID: {room_id}")
                    return None
            else:
                # 일반 교실 처리
                print(f"[*] 일반 교실 처리: {device_name} -> 좌표 ({row}, {col}) -> 바이트 {byte_pos}, 비트 {bit_pos}")
            
            # 상태에 따라 비트 설정 또는 해제
            if state:
                payload[byte_pos] |= (1 << bit_pos)  # 비트 설정 (켜기)
                print(f"[*] 장치 활성화: {device_name} -> 바이트 {byte_pos}, 비트 {bit_pos} 켜기")
            else:
                payload[byte_pos] &= ~(1 << bit_pos)  # 비트 해제 (끄기)
                print(f"[*] 장치 비활성화: {device_name} -> 바이트 {byte_pos}, 비트 {bit_pos} 끄기")
                
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
        # 로그 추가: 받은 active_rooms 출력 
        print(f"[*] create_current_state_payload 호출됨: {active_rooms}")
        
        # 기본 페이로드 생성 (46바이트)
        payload = bytearray(46)
        
        # 기본 헤더 - 레거시 형식으로 복원 (02 2d 00)
        payload[0:3] = bytes.fromhex("022d00")  # 원래 헤더 형식 (02 2d 00)
        payload[3:10] = bytes.fromhex("43420100000000")  # 나머지 헤더 부분
        
        # active_rooms가 지정되지 않거나 비어있으면 빈 상태 반환
        if not active_rooms:
            # 모든 장치가 비활성화된 상태
            print("[*] 활성화된 방이 없음")
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
                # 방 ID 타입 로깅
                print(f"[*] 방 ID 처리 중: {room_id} (타입: {type(room_id).__name__})")
                
                # 문자열 타입 처리 (방 ID가 문자열로 들어올 경우)
                if isinstance(room_id, str):
                    try:
                        room_id = int(room_id)
                        print(f"[*] 문자열 ID를 숫자로 변환: {room_id}")
                    except:
                        print(f"[!] 문자열을 숫자로 변환할 수 없음: {room_id}")
                        continue
                
                # 방 ID를 분석하여 학년과 반 추출
                # 예: 301 -> 3학년 1반
                if 100 <= room_id < 1000:  # 일반 교실 ID (3자리)
                    print(f"[*] 일반 교실 처리: {room_id}")
                    grade = room_id // 100  # 앞자리 (학년)
                    class_num = room_id % 100  # 뒤 두자리 (반)
                    
                    # 유효한 학년 및 반 번호 확인
                    if grade < 1 or grade > 3:
                        print(f"[!] 지원하지 않는 학년: {grade}")
                        continue
                        
                    if class_num < 1 or class_num > 4:
                        print(f"[!] 잘못된 반 번호: {class_num}. 1~4 사이 값이어야 합니다.")
                        continue
                    
                    # 장치 좌표로 변환 (grade -> row, class_num -> col)
                    if grade == 1:  # 1학년
                        row, col = 0, class_num - 1  # 0행, (반-1)열
                    elif grade == 2:  # 2학년
                        row, col = 0, class_num + 7  # 0행, (반+7)열
                    elif grade == 3:  # 3학년
                        row, col = 1, class_num - 1  # 1행, (반-1)열
                    
                    # 장치 매퍼를 통해 바이트/비트 위치 계산
                    byte_pos, bit_pos = self.device_mapper.get_byte_bit_position(row, col)
                    
                    # 비트 설정 (활성화)
                    payload[byte_pos] |= (1 << bit_pos)
                    print(f"[*] 장치 활성화: {grade}학년 {class_num}반 -> 좌표 ({row}, {col}) -> 바이트 {byte_pos}, 비트 {bit_pos}")
                    
                # 특수 공간 ID 처리 (1000 이상)
                elif room_id >= 1000:
                    print(f"[*] 특수 공간 처리: {room_id}")
                    # 특수 공간 ID를 좌표로 변환
                    special_room_coords = {
                        # 교무실, 과학실, 정의교실, 남여휴게실 등 (3행)
                        1001: (2, 0), 1002: (2, 1), 1003: (2, 2), 1004: (2, 3),
                        1005: (2, 4), 1006: (2, 5), 1007: (2, 6), 1008: (2, 7),
                        # A1호실, B2호실 등 (4행)
                        1013: (3, 0), 1014: (3, 1), 1015: (3, 2), 1016: (3, 3),
                        1017: (3, 4), 1018: (3, 5), 1019: (3, 6), 1020: (3, 7),
                        # 별관, 운동장 등 (5행)
                        1021: (4, 0), 1022: (4, 1), 1023: (4, 2), 1024: (4, 3)
                    }
                    
                    if room_id in special_room_coords:
                        row, col = special_room_coords[room_id]
                        # 장치 매퍼를 통해 바이트/비트 위치 계산
                        byte_pos, bit_pos = self.device_mapper.get_byte_bit_position(row, col)
                        
                        # 비트 설정 (활성화)
                        payload[byte_pos] |= (1 << bit_pos)
                        print(f"[*] 특수 공간 활성화: ID {room_id} -> 좌표 ({row}, {col}) -> 바이트 {byte_pos}, 비트 {bit_pos}")
                    else:
                        print(f"[!] 알 수 없는 특수 공간 ID: {room_id}")
                        continue
                else:
                    print(f"[!] 지원하지 않는 방 ID 형식: {room_id}")
                    continue
            except Exception as e:
                print(f"[!] 방 ID 처리 중 오류 ({room_id}): {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 패킷 완성 후 로깅
        print(f"[*] 생성된 패킷 바이트: {', '.join([f'{i}:{payload[i]:02x}' for i in range(len(payload)) if payload[i] != 0])}")
        
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
    
    def create_byte_bit_payload(self, byte_pos, bit_pos, state=1):
        """
        바이트 위치와 비트 위치를 직접 사용하여 제어 패킷 생성
        이 함수는 좌표로부터 직접 패킷을 생성할 때 사용합니다.
        
        Parameters:
        -----------
        byte_pos : int
            제어할 장치가 위치한 바이트 위치
        bit_pos : int
            제어할 장치가 위치한 비트 위치 (0-7)
        state : int
            0: 끄기, 1: 켜기
            
        Returns:
        --------
        bytes
            생성된 패킷 페이로드
        """
        # 기본 페이로드 생성 (46바이트)
        payload = bytearray(46)
        
        # 기본 헤더 - 레거시 형식으로 복원 (02 2d 00)
        payload[0:3] = bytes.fromhex("022d00")  # 원래 헤더 형식 (02 2d 00)
        payload[3:10] = bytes.fromhex("43420100000000")  # 나머지 헤더 부분
        
        # 지정된 바이트 및 비트 위치에 상태 설정
        if state:
            payload[byte_pos] |= (1 << bit_pos)  # 비트 설정 (켜기)
            print(f"[*] 장치 활성화: 바이트 {byte_pos}, 비트 {bit_pos} 켜기")
        else:
            payload[byte_pos] &= ~(1 << bit_pos)  # 비트 해제 (끄기)
            print(f"[*] 장치 비활성화: 바이트 {byte_pos}, 비트 {bit_pos} 끄기")
        
        # 체크섬 계산 및 설정
        checksum = self.calculate_checksum(payload)
        
        # 패킷 길이 및 종료 바이트 설정
        payload[42] = 0x00  # 첫 번째 바이트
        payload[43] = checksum  # 두 번째 바이트에 체크섬 설정
        payload[44] = 0x03  # 세 번째 바이트 (종료 바이트)
        payload[45] = 0x00  # 네 번째 바이트
        
        return payload
            
# 싱글톤 인스턴스 생성
packet_builder = PacketBuilder() 
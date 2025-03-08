#!/usr/bin/env python3
"""
방송 제어 시스템 컨트롤러 모듈
시스템의 핵심 기능을 통합적으로 관리합니다.
"""
from ..core.config import config
from ..core.device_mapping import device_mapper
from .packet_builder import packet_builder
from .network import network_manager
from .scheduler import broadcast_scheduler

class BroadcastController:
    """
    방송 제어 시스템 컨트롤러 클래스
    시스템의 모든 기능을 통합하고 관리합니다.
    """
    def __init__(self, target_ip=None, target_port=None, interface=None):
        """
        초기화 함수
        
        Parameters:
        -----------
        target_ip : str
            대상 방송 장비 IP
        target_port : int
            대상 방송 장비 포트
        interface : str
            사용할 네트워크 인터페이스
        """
        # 네트워크 관리자 설정 업데이트
        if target_ip:
            network_manager.target_ip = target_ip
        if target_port:
            network_manager.target_port = target_port
        if interface:
            network_manager.interface = interface
        
        # 시스템 상태 관리
        self.active_rooms = set()
        self.system_initialized = False
        
        # 장치 매퍼 속성 추가
        self.device_mapper = device_mapper
    
    def get_version(self):
        """
        앱 버전 정보 반환
        """
        return config.app_version
    
    def print_system_info(self):
        """
        시스템 정보 출력
        """
        print(f"[*] 방송 제어 시스템 정보:")
        print(f"    - 버전: {config.app_version}")
        print(f"    - 대상 IP: {network_manager.target_ip}")
        print(f"    - 대상 포트: {network_manager.target_port}")
        
        # 인터페이스 정보 출력
        network_manager.print_interface_info()
    
    def control_device(self, device_name, state=1):
        """
        장치 제어
        
        Parameters:
        -----------
        device_name : str
            제어할 장치명 (예: "1-1", "선생영역")
        state : int
            0: 끄기, 1: 켜기
            
        Returns:
        --------
        bool
            성공 여부
        """
        print(f"[*] 장치 제어: {device_name}, 상태: {'켜기' if state else '끄기'}")
        
        # 장치 상태 메모리에 업데이트
        try:
            # 장치 이름 형식에 따라 room_id 계산
            if '-' in device_name and device_name[0].isdigit():
                # 학년-반 형식 (예: "1-1", "3-2")
                grade, class_num = device_name.split('-')
                grade = int(grade)
                class_num = int(class_num)
                
                # 룸 ID 계산 (예: 1학년 1반 -> 101)
                room_id = grade * 100 + class_num
            else:
                # 특수 공간 매핑 (이미지에 표시된 순서대로)
                special_rooms = {
                    "교무실": 1001,
                    "과학실": 1002,
                    "정의교실": 1003,
                    "남여휴게실": 1004,
                    "교무실2": 1005,
                    "학생식당": 1006,
                    "위클래식": 1007,
                    "프로그램실": 1008,
                    "교무2처": 1009,
                    "진로상담": 1010,
                    "모듈1실": 1011,
                    "정의교실2": 1012,
                    "A1호실": 1013,
                    "B2호실": 1014,
                    "A2호실": 1015,
                    "B3호실": 1016,
                    "방송실-1": 1017,
                    "방송실-2": 1018,
                    "방송실-3": 1019,
                    "별관1-1": 1020,
                    "별관2-1": 1021,
                    "별관2-2": 1022,
                    "운동장": 1023,
                    "옥외": 1024
                }
                
                if device_name in special_rooms:
                    room_id = special_rooms[device_name]
                else:
                    print(f"[!] 알 수 없는 특수 공간: {device_name}")
                    return False
            
            # 상태에 따라 활성 방 목록 업데이트
            if state:
                self.active_rooms.add(room_id)
                print(f"[*] 활성화된 방 추가: {room_id} (현재 목록: {self.active_rooms})")
            else:
                self.active_rooms.discard(room_id)
                print(f"[*] 활성화된 방 제거: {room_id} (현재 목록: {self.active_rooms})")
                
        except Exception as e:
            print(f"[!] 장치 상태 업데이트 중 오류: {e}")
            return False
            
        # 현재 활성화된 방 목록 기반으로 패킷 생성
        payload = packet_builder.create_current_state_payload(self.active_rooms)
        if payload is None:
            return False
        
        # 페이로드 전송
        success, _ = network_manager.send_payload(payload)
        return success
    
    def control_multiple_devices(self, device_list, state=1):
        """
        여러 장치 동시 제어
        
        Parameters:
        -----------
        device_list : list
            제어할 장치명 리스트 (예: ["1-1", "1-2", "선생영역"])
        state : int
            0: 끄기, 1: 켜기
            
        Returns:
        --------
        bool
            성공 여부
        """
        print(f"[*] 여러 장치 제어: {', '.join(device_list)}, 상태: {'켜기' if state else '끄기'}")
        
        # 각 장치의 상태를 메모리에 업데이트
        for device_name in device_list:
            try:
                # 장치 이름 형식에 따라 room_id 계산
                if '-' in device_name and device_name[0].isdigit():
                    # 학년-반 형식 (예: "1-1", "3-2")
                    grade, class_num = device_name.split('-')
                    grade = int(grade)
                    class_num = int(class_num)
                    
                    # 룸 ID 계산 (예: 1학년 1반 -> 101)
                    room_id = grade * 100 + class_num
                else:
                    # 특수 공간 매핑 (이미지에 표시된 순서대로)
                    special_rooms = {
                        "교무실": 1001,
                        "과학실": 1002,
                        "정의교실": 1003,
                        "남여휴게실": 1004,
                        "교무실2": 1005,
                        "학생식당": 1006,
                        "위클래식": 1007,
                        "프로그램실": 1008,
                        "교무2처": 1009,
                        "진로상담": 1010,
                        "모듈1실": 1011,
                        "정의교실2": 1012,
                        "A1호실": 1013,
                        "B2호실": 1014,
                        "A2호실": 1015,
                        "B3호실": 1016,
                        "방송실-1": 1017,
                        "방송실-2": 1018,
                        "방송실-3": 1019,
                        "별관1-1": 1020,
                        "별관2-1": 1021,
                        "별관2-2": 1022,
                        "운동장": 1023,
                        "옥외": 1024
                    }
                    
                    if device_name in special_rooms:
                        room_id = special_rooms[device_name]
                    else:
                        print(f"[!] 알 수 없는 특수 공간: {device_name}")
                        continue
                
                # 상태에 따라 활성 방 목록 업데이트
                if state:
                    self.active_rooms.add(room_id)
                else:
                    self.active_rooms.discard(room_id)
                    
            except Exception as e:
                print(f"[!] 장치 상태 업데이트 중 오류 ({device_name}): {e}")
                continue
        
        print(f"[*] 현재 활성화된 방 목록: {self.active_rooms}")
        
        # 현재 활성화된 방 목록 기반으로 패킷 생성
        payload = packet_builder.create_current_state_payload(self.active_rooms)
        if payload is None:
            return False
        
        # 페이로드 전송
        success, _ = network_manager.send_payload(payload)
        return success
    
    def control_channel(self, command_type=0x01, channel=0x00, state=0x00):
        """
        방송 채널 제어
        
        Parameters:
        -----------
        command_type : int
            명령 타입 (0x01: 조명/기기 제어)
        channel : int
            제어할 채널 번호
        state : int
            상태 (0: OFF, 1: ON)
            
        Returns:
        --------
        bool
            성공 여부
        """
        # 명령 타입에 따라 적절한 페이로드 생성
        if channel == 0x40:  # 특수 채널 64
            payload = packet_builder.create_special_payload_64(state)
        elif channel == 0xD0:  # 특수 채널 208
            payload = packet_builder.create_special_payload_208(state)
        else:  # 일반 채널
            payload = packet_builder.create_command_payload(command_type, channel, state)
        
        # 페이로드 전송
        success, _ = network_manager.send_payload(payload)
        return success
    
    def initialize_system_state(self):
        """
        시스템의 초기 상태를 확인하기 위해 서버에 연결
        
        Returns:
        --------
        bool
            성공 여부
        """
        # 서버 연결 초기화 및 상태 확인
        success, response = network_manager.initialize_connection()
        
        if success and response:
            # 응답 분석
            self.parse_server_response(response)
            return True
        else:
            print("[!] 시스템 상태 초기화 실패")
            return False
    
    def parse_server_response(self, response):
        """
        서버 응답 분석
        
        Parameters:
        -----------
        response : bytes
            서버 응답 데이터
            
        Returns:
        --------
        bool
            성공 여부
        """
        try:
            # 응답 패킷이 너무 작은 경우에도 처리 시도
            if len(response) < 0x60:
                print(f"[!] 응답 패킷이 작습니다: {len(response)} 바이트")
                print(f"    - 헥스: {response.hex()}")
                
                # 작은 패킷 형식에 대한 처리 (일반적인 장치 상태 응답은 8~33바이트 범위)
                if len(response) >= 8 and response[0] == 0x02:
                    # 상태 코드 위치 추정 (작은 패킷에서는 일반적으로 7번째 바이트)
                    if len(response) >= 14 and response[1] == 0x0e:
                        state_code = response[9]  # 14바이트 형식
                    elif len(response) >= 8 and response[1] == 0x08:
                        state_code = response[6]  # 8바이트 형식
                    elif len(response) >= 33 and response[1] == 0x21:
                        state_code = response[7]  # 33바이트 형식
                    else:
                        # 알 수 없는 형식이지만 일반적인 위치에서 시도
                        state_code = response[min(7, len(response)-1)]
                    
                    print(f"[*] 추정된 상태 코드: 0x{state_code:02X}")
                    
                    # 상태 코드에 따라 활성 방 목록 업데이트
                    self.active_rooms = self.device_mapper.get_rooms_from_state_code(state_code)
                    print(f"[+] 시스템 상태 업데이트: 활성화된 반 = {self.active_rooms}")
                    
                    self.system_initialized = True
                    return True
            
            # 기존 대형 패킷 처리 로직
            # 헤더 확인 (대략적인 위치)
            header_pos = -1
            for i in range(len(response) - 5):
                if response[i:i+5] == b'\x02\x3c\x00\x53\x53':
                    header_pos = i
                    break
            
            if header_pos == -1:
                print("[!] 응답에서 상태 헤더를 찾을 수 없습니다")
                print(f"    응답 헥스: {response.hex()}")
                return False
            
            # 상태 코드 위치 계산 (헤더 + 4)
            state_code_pos = header_pos + 9
            if state_code_pos >= len(response):
                print("[!] 상태 코드 위치가 응답 범위를 벗어납니다")
                return False
            
            # 상태 코드 추출
            state_code = response[state_code_pos]
            print(f"[*] 확인된 상태 코드: 0x{state_code:02X}")
            
            # 활성화 비트 확인 (헤더 + 0x29)
            active_bit_pos = header_pos + 0x29
            if active_bit_pos < len(response):
                active_bit = response[active_bit_pos]
                print(f"[*] 활성화 비트: 0x{active_bit:02X}")
            
            # 상태 코드에 따라 활성 방 목록 업데이트
            self.active_rooms = self.device_mapper.get_rooms_from_state_code(state_code)
            print(f"[+] 시스템 상태 업데이트: 활성화된 반 = {self.active_rooms}")
            
            self.system_initialized = True
            return True
            
        except Exception as e:
            print(f"[!] 응답 분석 오류: {e}")
            return False
    
    def set_room_state(self, room_id, state):
        """
        특정 교실의 상태를 설정하고 서버에 업데이트합니다.
        
        Parameters:
        -----------
        room_id : int
            교실 ID (예: 301 = 3학년 1반)
        state : int
            상태 (0: 끄기, 1: 켜기)
        
        Returns:
        --------
        bool
            성공 여부
        """
        # 현재 상태 업데이트
        if state == 1:
            self.active_rooms.add(room_id)
        else:
            self.active_rooms.discard(room_id)
        
        # 상태 코드 계산
        state_code = self.device_mapper.get_state_code(self.active_rooms)
        
        # 상태 기반 페이로드 생성
        payload = packet_builder.create_state_payload(state_code)
        
        # 명령 전송
        success, _ = network_manager.send_payload(payload)
        return success
    
    def send_test_packets(self):
        """
        테스트용 패킷 시퀀스 전송
        """
        print("\n[*] 테스트 패킷 시퀀스 시작")
        
        # 제공된 패킷 분석 결과에 따른 테스트 패킷들
        test_cases = [
            # [명령 타입, 채널, 상태, 설명]
            [0x01, 0x00, 0x00, "기본 채널 끄기 (캡처된 패킷과 일치)"],
            [0x01, 0x00, 0x01, "기본 채널 켜기"],
            [0x01, 0x40, 0x00, "특수 채널 64 끄기 (특수 페이로드)"],
            [0x01, 0x40, 0x01, "특수 채널 64 켜기 (특수 페이로드)"],
            [0x01, 0xD0, 0x00, "특수 채널 208 끄기 (특수 페이로드)"],
            [0x01, 0xD0, 0x01, "특수 채널 208 켜기 (특수 페이로드)"]
        ]
        
        for i, test in enumerate(test_cases):
            cmd_type, channel, state, desc = test
            print(f"\n[*] 테스트 케이스 {i+1}: {desc}")
            
            self.control_channel(cmd_type, channel, state)
            
            # 다음 테스트 전에 잠시 대기
            import time
            time.sleep(1)
            
            # 장치 응답을 기다림
            print("\n[*] 장치 응답 기다리는 중... (3초)")
            time.sleep(3)
        
        print("\n[*] 테스트 패킷 시퀀스 완료")
    
    # 스케줄러 관련 메서드 - 내부적으로 스케줄러 모듈 사용
    def schedule_broadcast(self, time_str, days, command_type, channel, state):
        """
        방송 스케줄 저장
        """
        return broadcast_scheduler.schedule_broadcast(time_str, days, command_type, channel, state)
    
    def view_schedules(self):
        """
        저장된 방송 스케줄 목록 출력
        """
        return broadcast_scheduler.view_schedules()
    
    def delete_schedule(self, index):
        """
        지정된 인덱스의 스케줄 삭제
        """
        return broadcast_scheduler.delete_schedule(index)
    
    def start_scheduler(self):
        """
        스케줄러 시작
        """
        return broadcast_scheduler.start_scheduler()
    
    def stop_scheduler(self):
        """
        스케줄러 중지
        """
        return broadcast_scheduler.stop_scheduler()

    def control_mixer(self, mixer_id, state=1):
        """
        믹서 제어 기능
        
        Parameters:
        -----------
        mixer_id : int
            제어할 믹서 번호 (1~16)
        state : int
            0: 끄기, 1: 켜기
            
        Returns:
        --------
        bool
            성공 여부
        """
        print(f"[*] 믹서 제어: {mixer_id}번, 상태: {'켜기' if state else '끄기'}")
        
        # 믹서 제어 패킷 생성
        payload = packet_builder.create_mixer_control_payload(mixer_id, state)
        if payload is None:
            return False
        
        # 페이로드 전송
        success, _ = network_manager.send_payload(payload)
        return success
    
    def control_all_mixers(self, state=1):
        """
        모든 믹서 동시 제어
        
        Parameters:
        -----------
        state : int
            0: 모두 끄기, 1: 모두 켜기
            
        Returns:
        --------
        bool
            성공 여부
        """
        print(f"[*] 모든 믹서 제어, 상태: {'켜기' if state else '끄기'}")
        
        # 모든 믹서 제어 패킷 생성
        payload = packet_builder.create_all_mixers_control_payload(state)
        if payload is None:
            return False
        
        # 페이로드 전송
        success, _ = network_manager.send_payload(payload)
        return success
    
    def test_mixer_sequence(self):
        """
        믹서 테스트 시퀀스 실행
        """
        print("\n[*] 믹서 테스트 시퀀스 시작")
        
        # 모든 믹서 끄기로 초기화
        print("\n[*] 0. 모든 믹서 끄기로 초기화")
        self.control_all_mixers(0)
        import time
        time.sleep(1)
        
        # 테스트 1: 홀수 믹서(1, 3, 5, 7) 차례로 켜기
        print("\n[*] 1. 홀수 믹서(1, 3, 5, 7) 차례로 켜기")
        for mixer_id in [1, 3, 5, 7]:
            print(f"[*] {mixer_id}번 믹서 켜기")
            self.control_mixer(mixer_id, 1)
            time.sleep(1)  # 각 명령 사이에 1초 대기
        
        # 테스트 2: 모든 믹서 끄기
        print("\n[*] 2. 모든 믹서 끄기")
        self.control_all_mixers(0)
        time.sleep(1)
        
        # 테스트 3: 모든 믹서 켜기
        print("\n[*] 3. 모든 믹서 켜기")
        self.control_all_mixers(1)
        time.sleep(1)
        
        # 테스트 4: 16번부터 차례로 끄기
        print("\n[*] 4. 모든 믹서 차례로 끄기 (16번부터)")
        for mixer_id in range(16, 0, -1):
            print(f"[*] {mixer_id}번 믹서 끄기")
            self.control_mixer(mixer_id, 0)
            time.sleep(0.5)  # 각 명령 사이에 0.5초 대기
        
        print("\n[*] 믹서 테스트 시퀀스 완료")

    def control_input_channel(self, channel_id, state=1):
        """
        입력 채널 제어 기능
        
        Parameters:
        -----------
        channel_id : int
            제어할 입력 채널 ID (1~16)
        state : int
            0: 끄기, 1: 켜기
            
        Returns:
        --------
        bool
            성공 여부
        """
        print(f"[*] 입력 채널 제어: {channel_id}번, 상태: {'켜기' if state else '끄기'}")
        
        # 채널 타입 출력 (마이크/라인)
        channel_type = "마이크" if channel_id in [1, 2, 11] else "라인"
        print(f"[*] 채널 타입: {channel_type}")
        
        # 입력 채널 제어 패킷 생성
        payload = packet_builder.create_input_channel_payload(channel_id, state)
        if payload is None:
            return False
        
        # 페이로드 전송
        success, _ = network_manager.send_payload(payload)
        return success
    
    def control_all_input_channels(self, state=1, channel_type="all"):
        """
        모든 입력 채널 또는 특정 타입의 모든 채널 동시 제어
        
        Parameters:
        -----------
        state : int
            0: 모두 끄기, 1: 모두 켜기
        channel_type : str
            "mic": 마이크 타입 채널만, "line": 라인 타입 채널만, "all": 모든 채널
            
        Returns:
        --------
        bool
            성공 여부
        """
        type_str = {
            "mic": "마이크 타입",
            "line": "라인 타입",
            "all": "모든"
        }.get(channel_type, "모든")
        
        print(f"[*] {type_str} 입력 채널 제어, 상태: {'켜기' if state else '끄기'}")
        
        # 입력 채널 제어 패킷 생성
        payload = packet_builder.create_all_input_channels_payload(state, channel_type)
        if payload is None:
            return False
        
        # 페이로드 전송
        success, _ = network_manager.send_payload(payload)
        return success
    
    def test_input_channels(self):
        """
        입력 채널 테스트 시퀀스 실행
        """
        print("\n[*] 입력 채널 테스트 시퀀스 시작")
        
        # 모든 입력 채널 끄기로 초기화
        print("\n[*] 0. 모든 입력 채널 끄기로 초기화")
        self.control_all_input_channels(0)
        
        import time
        time.sleep(1)
        
        # 테스트 1: 홀수 채널(1, 3, 5, 7) 차례로 켜기
        print("\n[*] 1. 홀수 채널(1, 3, 5, 7) 차례로 켜기")
        for channel_id in [1, 3, 5, 7]:
            channel_type = "마이크" if channel_id in [1, 2, 11] else "라인"
            print(f"[*] {channel_id}번 입력 채널({channel_type}) 켜기")
            self.control_input_channel(channel_id, 1)
            time.sleep(1)  # 각 명령 사이에 1초 대기
        
        # 테스트 2: 모든 채널 끄기
        print("\n[*] 2. 모든 입력 채널 끄기")
        self.control_all_input_channels(0)
        time.sleep(1)
        
        # 테스트 3: 마이크 타입 채널만 켜기
        print("\n[*] 3. 마이크 타입 채널만 켜기")
        self.control_all_input_channels(1, "mic")
        time.sleep(1)
        
        # 테스트 4: 라인 타입 채널만 켜기
        print("\n[*] 4. 라인 타입 채널만 켜기")
        self.control_all_input_channels(1, "line")
        time.sleep(1)
        
        # 테스트 5: 모든 채널 켜기
        print("\n[*] 5. 모든 입력 채널 켜기")
        self.control_all_input_channels(1)
        time.sleep(1)
        
        # 테스트 6: 16번부터 차례로 끄기
        print("\n[*] 6. 모든 입력 채널 차례로 끄기 (16번부터)")
        for channel_id in range(16, 0, -1):
            channel_type = "마이크" if channel_id in [1, 2, 11] else "라인"
            print(f"[*] {channel_id}번 입력 채널({channel_type}) 끄기")
            self.control_input_channel(channel_id, 0)
            time.sleep(0.5)  # 각 명령 사이에 0.5초 대기
        
        print("\n[*] 입력 채널 테스트 시퀀스 완료")

# 싱글톤 인스턴스 생성
broadcast_controller = BroadcastController() 
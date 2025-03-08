#!/usr/bin/env python3
from scapy.all import Ether, IP, TCP, Raw, hexdump, sendp, conf, IFACES
import os
import sys
import time
import datetime
import csv
import threading
import socket
import re

# 고정 인터페이스 설정 (찾은 이더넷 인터페이스)
DEFAULT_INTERFACE = r"\Device\NPF_{A3EA7E25-E0C4-4F61-8FA9-69FA733D2708}"

# 전역 설정
APP_VERSION = "1.0.0"
SCHEDULE_FILE = "broadcast_schedule.csv"
TARGET_IP = "192.168.0.200"
TARGET_PORT = 22000

# 특수 채널 및 명령 정의
SPECIAL_CHANNELS = {
    0x00: "기본 채널",
    0x40: "그룹 제어 채널 (64)",
    0xD0: "특수 기능 채널 (208)"
}

class BroadcastController:
    """
    학교 방송 제어 시스템 클래스
    학교 방송 장비 조작과 스케줄링을 담당합니다.
    """
    def __init__(self, interface=None, target_ip="192.168.0.200", target_port=22000):
        """
        초기화 함수 - 네트워크 설정을 초기화합니다.
        
        Parameters:
        -----------
        interface : str
            사용할 네트워크 인터페이스
        target_ip : str
            대상 방송 장비 IP
        target_port : int
            대상 방송 장비 포트
        """
        self.interface = interface  # 나중에 필요한 경우를 위해 유지
        self.target_ip = target_ip  # 방송 장비 IP
        self.target_port = target_port  # 방송 장비 포트 (기본값: 22000)
        
        # 패킷 카운터 초기화
        self.packet_counter = 0
        
        # 스케줄링 정보 저장을 위한 CSV 파일 경로
        self.schedule_file = "broadcast_schedule.csv"
        
        # 스케줄러 스레드
        self.scheduler_thread = None
        self.running = False
        
        # 시스템 상태 관리
        self.active_rooms = set()
        self.system_initialized = False
        
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
        
        print(f"[*] 방송 제어 시스템 초기화 완료")
        print(f"    - 대상 IP: {self.target_ip}")
        print(f"    - 대상 포트: {self.target_port}")
        
        # 인터페이스 정보 출력
        self.print_interface_info()
        
        # 스케줄러 초기화
        self.scheduler_running = False
    
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
                payload_hex = (
                    "022d0043420100000000"  # 헤더 + 명령(0x01) + 채널(0x00) + 상태(0x00)
                    "00000000000000000000000000000000"  # 첫 번째 패딩 블록
                    "00000000000000000000000000000000"  # 두 번째 패딩 블록
                    "002f0300"              # 체크섬(0x2F) + 종료 바이트(0x03) + 추가 바이트(0x00)
                )
                bytes_data = bytes.fromhex(payload_hex)
                assert len(bytes_data) == 46, f"패킷 길이 오류: {len(bytes_data)} 바이트"
                return bytes_data
            else:  # 켜기 상태
                # 정확히 46바이트가 되도록 직접 바이트 배열 생성
                packet = bytearray(46)  # 46바이트 배열 생성
                
                # 헤더 + 명령 + 채널 + 상태 설정 (10바이트)
                header = bytes.fromhex("022d0043420100010000")
                packet[0:10] = header
                
                # 패딩 영역 (0-값으로 채움, 이미 0으로 초기화되어 있음)
                
                # 0x40 값 위치 설정 (인덱스 22에 0x40 배치)
                packet[22] = 0x40
                
                # FF 패턴 설정 (인덱스 26, 30, 34에 0xFFFF 패턴 배치)
                ff_pattern = bytes.fromhex("ffff0000")
                packet[26:30] = ff_pattern
                packet[30:34] = ff_pattern
                packet[34:38] = ff_pattern
                
                # 체크섬 및 종료 바이트 설정
                footer = bytes.fromhex("006e0300")
                packet[42:46] = footer
                
                assert len(packet) == 46, f"패킷 길이 오류: {len(packet)} 바이트"
                return bytes(packet)
        
        # 다른 일반 채널은 기존 방식 유지
        packet = bytearray(43)  # 총 43바이트 패킷
        
        # 1. 패킷 헤더 (5바이트)
        packet[0] = 0x02  # 시작 바이트
        packet[1] = 0x2D  # 헤더 바이트
        packet[2] = 0x00
        packet[3] = 0x43
        packet[4] = 0x42
        
        # 2. 명령 정보 (5바이트)
        packet[5] = command_type  # 명령 타입 (0x01: 조명/기기 제어)
        packet[6] = channel       # 채널 (0~255)
        packet[7] = state         # 상태 (0: OFF, 1: ON)
        packet[8] = 0x00
        packet[9] = 0x00
        
        # 3. 패딩 영역 (31바이트, 인덱스 10~40)
        for i in range(10, 41):
            packet[i] = 0x00
        
        # 4. 체크섬 계산 (실제 패킷에서 추출)
        packet[41] = 0x2F  # 기본 체크섬 값
        
        # 5. 종료 바이트와 추가 바이트
        packet[42] = 0x03  # 종료 바이트
        
        return bytes(packet)
    
    def create_special_payload_64(self, state=0x00):
        """
        채널 64(0x40)용 특수 페이로드 생성
        실제 패킷 캡처본 분석 결과 기반
        """
        # 정확히 46바이트가 되도록 직접 바이트 배열 생성
        packet = bytearray(46)  # 46바이트 배열 초기화
        
        # 헤더 + 명령 + 채널 + 상태 (10바이트)
        header = bytes.fromhex(f"022d0043420140{state:02x}0000")
        packet[0:10] = header
        
        # 특수 패턴 설정 (0F 0F 00 00 0F 00 00 00)
        pattern1 = bytes.fromhex("0f0f00000f000000")
        packet[10:18] = pattern1
        
        # FF 패턴 설정 (여러 위치에 0xFFFF 패턴 배치)
        ff_pattern = bytes.fromhex("ffff0000")
        packet[18:22] = ff_pattern
        packet[22:26] = ff_pattern
        packet[30:34] = ff_pattern
        packet[34:38] = ff_pattern
        packet[38:42] = ff_pattern
        
        # 체크섬 및 종료 바이트 설정
        if state == 0x00:
            footer = bytes.fromhex("00600300")  # 끄기 상태 체크섬
        else:
            footer = bytes.fromhex("00610300")  # 켜기 상태 체크섬
        packet[42:46] = footer
        
        assert len(packet) == 46, f"패킷 길이 오류: {len(packet)} 바이트"
        return bytes(packet)
    
    def create_special_payload_208(self, state=0x00):
        """
        채널 208(0xD0)용 특수 페이로드 생성
        실제 패킷 분석 결과 기반
        """
        # 정확히 46바이트가 되도록 직접 바이트 배열 생성
        packet = bytearray(46)  # 46바이트 배열 초기화
        
        # 헤더 + 명령 + 채널 (10바이트)
        # 특수 채널 208은 위치가 다름 (인덱스 7에 0xD0)
        header_hex = "022d00434201"
        packet[0:6] = bytes.fromhex(header_hex)
        packet[6] = 0x00    # 첫 번째 바이트
        packet[7] = 0xD0    # 두 번째 바이트 (0xD0 = 208)
        packet[8] = state   # 상태값 설정
        packet[9] = 0x00    # 마지막 바이트
        
        # 특수 패턴 설정 (0F 0F 00 00 0F 00 00 00)
        pattern1 = bytes.fromhex("0f0f00000f000000")
        packet[10:18] = pattern1
        
        # FF 패턴 설정 (여러 위치에 0xFFFF 패턴 배치)
        ff_pattern = bytes.fromhex("ffff0000")
        packet[18:22] = ff_pattern
        packet[22:26] = ff_pattern
        packet[30:34] = ff_pattern
        packet[34:38] = ff_pattern
        packet[38:42] = ff_pattern
        
        # 체크섬 및 종료 바이트 설정
        if state == 0x00:
            footer = bytes.fromhex("00ef0300")  # 끄기 상태 체크섬
        else:
            footer = bytes.fromhex("00ee0300")  # 켜기 상태 체크섬
        packet[42:46] = footer
        
        assert len(packet) == 46, f"패킷 길이 오류: {len(packet)} 바이트"
        return bytes(packet)
    
    def send_command(self, command_type=0x01, channel=0x01, state=0x01, use_default_payload=True):
        """
        방송 장비 명령 전송 - TCP 소켓 방식으로 변경
        
        Parameters:
        ----------
        command_type : int
            명령 타입 (0x01: 조명/기기 제어, 0x03: 채널 변경 등)
        channel : int
            제어할 채널 번호
        state : int
            상태 (0: OFF, 1: ON)
        use_default_payload : bool
            기본 페이로드 생성 함수 사용 여부
        """
        # 1. 페이로드 생성
        if use_default_payload:
            # 일반 페이로드 생성
            payload = self.create_command_payload(command_type, channel, state)
        elif channel == 0x40:
            # 채널 64용 특수 페이로드
            payload = self.create_special_payload_64(state)
        elif channel == 0xD0:
            # 채널 208용 특수 페이로드
            payload = self.create_special_payload_208(state)
        else:
            # 기본 페이로드
            payload = self.create_command_payload(command_type, channel, state)
        
        # 명령 정보 출력
        cmd_types = {0x01: "장비 제어", 0x02: "볼륨 제어", 0x03: "채널 변경"}
        cmd_states = {0x00: "끄기", 0x01: "켜기"}
        
        cmd_name = cmd_types.get(command_type, "알 수 없음")
        state_name = cmd_states.get(state, "알 수 없음") if command_type == 0x01 else str(state)
        
        # 채널이 특수 채널인 경우 설명 추가
        channel_desc = SPECIAL_CHANNELS.get(channel, f"채널 {channel}")
        
        print(f"[*] 명령 전송: {cmd_name}, {channel_desc}, 상태: {state_name}")
        
        # 2. 소켓 통신 방식으로 전송
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
            
            # 응답 대기 (최대 3초)
            try:
                print("[*] 응답 대기 중...")
                response = s.recv(1024)
                if response:
                    print(f"[+] 응답 수신: {len(response)} 바이트")
                    print(f"    - 헥스: {response.hex()}")
                else:
                    print("[!] 응답 없음")
            except socket.timeout:
                print("[!] 응답 타임아웃")
            
            # 연결 종료
            s.close()
            
            print("[+] 패킷 전송 완료")
            self.packet_counter += 1
            return True
            
        except ConnectionRefusedError:
            print(f"[!] 연결 거부됨: {self.target_ip}:{self.target_port}")
        except socket.timeout:
            print(f"[!] 연결 타임아웃: {self.target_ip}:{self.target_port}")
        except Exception as e:
            print(f"[!] 패킷 전송 실패: {e}")
        
        return False
    
    def send_test_packets(self):
        """테스트용 패킷 시퀀스 전송"""
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
        
        # 패킷 카운터 초기화 (캡처된 패킷과 일치하게)
        self.packet_counter = 0
        
        for i, test in enumerate(test_cases):
            cmd_type, channel, state, desc = test
            print(f"\n[*] 테스트 케이스 {i+1}: {desc}")
            
            # 특수 채널인 경우 특수 페이로드 사용
            use_default = not (channel in [0x40, 0xD0])
            self.send_command(cmd_type, channel, state, use_default)
            
            # 다음 테스트 전에 잠시 대기
            time.sleep(1)
            
            # 장치 응답을 기다림
            print("\n[*] 장치 응답 기다리는 중... (3초)")
            time.sleep(3)
        
        print("\n[*] 테스트 패킷 시퀀스 완료")
    
    def control_light(self, channel, state):
        """조명/기기 제어 함수"""
        return self.send_command(command_type=0x01, channel=channel, state=state)
    
    def control_volume(self, channel, level):
        """볼륨 제어 함수"""
        return self.send_command(command_type=0x02, channel=channel, state=level)
    
    def select_channel(self, channel):
        """채널 선택 함수"""
        return self.send_command(command_type=0x03, channel=channel, state=0x01)
    
    def schedule_broadcast(self, time_str, days, command_type, channel, state):
        """
        방송 스케줄 저장
        
        Parameters:
        -----------
        time_str : str
            실행 시간 (HH:MM 형식)
        days : str
            실행 요일 (쉼표로 구분된 요일 문자열)
        command_type : int
            명령 타입
        channel : int
            채널 번호
        state : int
            상태
        """
        # CSV 파일이 없으면 생성
        file_exists = os.path.isfile(self.schedule_file)
        
        try:
            with open(self.schedule_file, 'a', newline='') as file:
                writer = csv.writer(file)
                
                # 파일이 새로 생성된 경우 헤더 작성
                if not file_exists:
                    writer.writerow(['time', 'days', 'command_type', 'channel', 'state'])
                
                # 스케줄 데이터 추가
                writer.writerow([time_str, days, command_type, channel, state])
                
            print(f"[+] 예약 방송이 추가되었습니다: {time_str} ({days})")
            return True
            
        except Exception as e:
            print(f"[!] 예약 방송 추가 실패: {e}")
            return False
    
    def load_schedules(self):
        """
        저장된 방송 스케줄 목록 불러오기
        
        Returns:
        --------
        list
            스케줄 데이터 목록
        """
        schedules = []
        
        if not os.path.isfile(self.schedule_file):
            return schedules
            
        try:
            with open(self.schedule_file, 'r', newline='') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    schedules.append(row)
                    
            return schedules
            
        except Exception as e:
            print(f"[!] 예약 방송 불러오기 실패: {e}")
            return []
    
    def view_schedules(self):
        """
        저장된 방송 스케줄 목록 출력
        
        Returns:
        --------
        list
            스케줄 데이터 목록
        """
        schedules = self.load_schedules()
        
        if not schedules:
            print("[!] 저장된 예약 방송이 없습니다.")
            return []
            
        return schedules
    
    def delete_schedule(self, index):
        """
        지정된 인덱스의 스케줄 삭제
        
        Parameters:
        -----------
        index : int
            삭제할 스케줄 인덱스
        """
        schedules = self.load_schedules()
        
        if not schedules or index < 0 or index >= len(schedules):
            print("[!] 유효하지 않은 스케줄 인덱스입니다.")
            return False
            
        # 지정된 인덱스 제외하고 나머지 스케줄 저장
        try:
            with open(self.schedule_file, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['time', 'days', 'command_type', 'channel', 'state'])
                
                for i, schedule in enumerate(schedules):
                    if i != index:
                        writer.writerow([
                            schedule['time'],
                            schedule['days'],
                            schedule['command_type'],
                            schedule['channel'],
                            schedule['state']
                        ])
                        
            print(f"[+] 예약 방송이 삭제되었습니다.")
            return True
            
        except Exception as e:
            print(f"[!] 예약 방송 삭제 실패: {e}")
            return False
    
    def run_scheduler(self):
        """
        스케줄러 실행 함수 - 백그라운드에서 스케줄을 확인하고 명령 실행
        """
        self.scheduler_running = True
        print("[*] 스케줄러가 시작되었습니다")
        
        while self.scheduler_running:
            # 현재 시간 가져오기
            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M")
            current_day = now.strftime("%A")  # 요일
            
            schedules = self.load_schedules()
            
            # 현재 시간에 실행할 스케줄이 있는지 확인
            for schedule in schedules:
                time_str = schedule.get('time', '')
                days = schedule.get('days', '').split(',')
                
                # 시간과 요일이 일치하면 명령 실행
                if time_str == current_time and (current_day in days or 'Everyday' in days):
                    cmd_type = int(schedule.get('command_type', 1))
                    channel = int(schedule.get('channel', 1))
                    state = int(schedule.get('state', 1))
                    
                    # 시간에 실행되는 커맨드라는 것을 표시
                    print(f"\n[*] 예약된 방송 실행 중: {time_str} ({current_day})")
                    self.send_command(cmd_type, channel, state)
            
            # 1분마다 체크
            time.sleep(60)
    
    def start_scheduler(self):
        """스케줄러 시작"""
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.scheduler_running = True
            self.scheduler_thread = threading.Thread(target=self.run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            print("[+] 스케줄러가 백그라운드에서 실행 중입니다")
        else:
            print("[!] 스케줄러가 이미 실행 중입니다")
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_running = False
            self.scheduler_thread.join(2)  # 2초간 스레드 종료 대기
            if self.scheduler_thread.is_alive():
                print("[!] 스케줄러 종료에 실패했습니다")
            else:
                self.scheduler_thread = None
                print("[+] 스케줄러가 중지되었습니다")
        else:
            print("[!] 실행 중인 스케줄러가 없습니다")

    def initialize_system_state(self):
        """
        시스템의 초기 상태를 확인하기 위해 서버에 연결하고 상태 정보를 요청합니다.
        """
        print("[*] 시스템 상태 초기화 중...")
        
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
            
            # 응답 대기
            try:
                print("[*] 서버 응답 대기 중...")
                response = s.recv(1024)
                if response:
                    print(f"[+] 응답 수신: {len(response)} 바이트")
                    self.parse_server_response(response)
                else:
                    print("[!] 응답 없음")
            except socket.timeout:
                print("[!] 응답 타임아웃")
            
            # 연결 종료
            s.close()
            
            return True
            
        except Exception as e:
            print(f"[!] 시스템 상태 초기화 실패: {e}")
            return False
    
    def parse_server_response(self, response):
        """
        서버 응답을 분석하여 현재 시스템 상태를 업데이트합니다.
        
        Parameters:
        -----------
        response : bytes
            서버로부터 받은 응답 데이터
        """
        try:
            # 응답 패킷이 충분히 큰지 확인
            if len(response) < 0x60:
                print(f"[!] 응답 패킷이 너무 작습니다: {len(response)} 바이트")
                return False
            
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
            
            # 상태 코드에 따라 활성 반 목록 업데이트
            if state_code in self.REVERSE_STATE_CODES:
                self.active_rooms = set(self.REVERSE_STATE_CODES[state_code])
                print(f"[+] 시스템 상태 업데이트: 활성화된 반 = {self.active_rooms}")
            else:
                print(f"[!] 알 수 없는 상태 코드: 0x{state_code:02X}")
            
            self.system_initialized = True
            return True
            
        except Exception as e:
            print(f"[!] 응답 분석 오류: {e}")
            return False
    
    def get_state_code(self):
        """
        현재 활성화된 반 목록에 따른 상태 코드를 반환합니다.
        
        Returns:
        --------
        int
            상태 코드 값
        """
        frozen_set = frozenset(self.active_rooms)
        if frozen_set in self.STATE_CODES:
            return self.STATE_CODES[frozen_set]
        else:
            print(f"[!] 매핑되지 않은 상태 조합: {self.active_rooms}")
            return 0x00  # 기본값
    
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
        state_code = self.get_state_code()
        
        # 상태 기반 페이로드 생성
        payload = self.create_state_payload(state_code)
        
        # 명령 전송
        return self.send_command_with_payload(payload)
    
    def create_state_payload(self, state_code):
        """
        상태 코드에 따른 페이로드를 생성합니다.
        
        Parameters:
        -----------
        state_code : int
            상태 코드 값
            
        Returns:
        --------
        bytes
            생성된 페이로드
        """
        # 46바이트 페이로드 생성
        payload = bytearray(46)
        
        # 기본 헤더 설정
        header = bytes.fromhex("022d0043420100000000")
        payload[0:10] = header
        
        # 상태 코드 설정 (11번째 바이트)
        payload[11] = state_code
        
        # 활성화 상태 확인 (켜진 반이 있는지)
        has_active_rooms = len(self.active_rooms) > 0
        
        # 체크섬 값 결정 (상태에 따라 다름)
        if has_active_rooms:
            # 다양한 상태에 따른 체크섬 설정 필요
            if state_code == 0x03:
                footer = bytes.fromhex("003C0300")  # 3학년 1반 켜짐
            elif state_code == 0x01:
                footer = bytes.fromhex("003E0300")  # 3학년 1,2반 켜짐
            else:
                footer = bytes.fromhex("002F0300")  # 기본값
        else:
            # 모두 꺼진 상태
            footer = bytes.fromhex("003E0300")
        
        # 체크섬 설정
        payload[42:46] = footer
        
        return bytes(payload)
    
    def send_command_with_payload(self, payload):
        """
        미리 생성된 페이로드로 명령을 전송합니다.
        
        Parameters:
        -----------
        payload : bytes
            전송할 페이로드
        
        Returns:
        --------
        bool
            성공 여부
        """
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
            
            # 응답 대기 (최대 3초)
            try:
                print("[*] 응답 대기 중...")
                response = s.recv(1024)
                if response:
                    print(f"[+] 응답 수신: {len(response)} 바이트")
                    print(f"    - 헥스: {response.hex()}")
                    # 응답 분석하여 시스템 상태 업데이트
                    self.parse_server_response(response)
                else:
                    print("[!] 응답 없음")
            except socket.timeout:
                print("[!] 응답 타임아웃")
            
            # 연결 종료
            s.close()
            
            print("[+] 패킷 전송 완료")
            self.packet_counter += 1
            return True
            
        except ConnectionRefusedError:
            print(f"[!] 연결 거부됨: {self.target_ip}:{self.target_port}")
        except socket.timeout:
            print(f"[!] 연결 타임아웃: {self.target_ip}:{self.target_port}")
        except Exception as e:
            print(f"[!] 패킷 전송 실패: {e}")
        
        return False

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
        
        # 기본 헤더
        payload[0:10] = bytes.fromhex("022d0043420100000000")
        
        # 장치 좌표 찾기
        coords = self.get_device_coords(device_name)
        if not coords:
            print(f"[!] 장치를 찾을 수 없음: {device_name}")
            return None
        
        row, col = coords
        
        # 바이트와 비트 위치 계산
        byte_pos, bit_pos = self.get_byte_bit_position(row, col)
        if byte_pos is None:
            print(f"[!] 잘못된 좌표: ({row}, {col})")
            return None
        
        # 상태에 따라 비트 설정 또는 해제
        if state:
            payload[byte_pos] |= (1 << bit_pos)
        else:
            payload[byte_pos] &= ~(1 << bit_pos)
        
        # 체크섬 계산 및 설정 (마지막 4바이트)
        # 상태에 따라 체크섬값 결정 (실제 값은 분석 필요)
        if state:
            payload[42:46] = bytes.fromhex("03030303")
        else:
            payload[42:46] = bytes.fromhex("04040404")
        
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
        
        # 기본 헤더
        payload[0:10] = bytes.fromhex("022d0043420100000000")
        
        # 각 장치의 비트 설정
        for device_name in device_list:
            coords = self.get_device_coords(device_name)
            if not coords:
                print(f"[!] 장치를 찾을 수 없음: {device_name}")
                continue
                
            row, col = coords
            byte_pos, bit_pos = self.get_byte_bit_position(row, col)
            
            if byte_pos is None:
                print(f"[!] 잘못된 좌표: ({row}, {col})")
                continue
                
            # 상태에 따라 비트 설정 또는 해제
            if state:
                payload[byte_pos] |= (1 << bit_pos)
            else:
                payload[byte_pos] &= ~(1 << bit_pos)
        
        # 체크섬 계산 및 설정 (마지막 4바이트)
        if state:
            payload[42:46] = bytes.fromhex("03030303")
        else:
            payload[42:46] = bytes.fromhex("04040404")
        
        return payload
        
    def control_device_by_name(self, device_name, state=1):
        """장치명을 기준으로 제어 명령 전송
        
        Parameters:
        -----------
        device_name : str
            제어할 장치명 (예: "1-1", "선생영역")
        state : int
            0: 끄기, 1: 켜기
        """
        print(f"[*] 장치 제어: {device_name}, 상태: {'켜기' if state else '끄기'}")
        
        payload = self.create_device_payload(device_name, state)
        if payload is None:
            return False
            
        # 소켓 통신으로 전송
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
            
            # 응답 대기 (최대 3초)
            try:
                print("[*] 응답 대기 중...")
                response = s.recv(1024)
                if response:
                    print(f"[+] 응답 수신: {len(response)} 바이트")
                    print(f"    - 헥스: {response.hex()}")
                else:
                    print("[!] 응답 없음")
            except socket.timeout:
                print("[!] 응답 타임아웃")
            
            # 연결 종료
            s.close()
            
            print("[+] 패킷 전송 완료")
            self.packet_counter += 1
            return True
            
        except ConnectionRefusedError:
            print(f"[!] 연결 거부됨: {self.target_ip}:{self.target_port}")
        except socket.timeout:
            print(f"[!] 연결 타임아웃: {self.target_ip}:{self.target_port}")
        except Exception as e:
            print(f"[!] 패킷 전송 실패: {e}")
        
        return False
        
    def control_multiple_devices(self, device_list, state=1):
        """여러 장치를 동시에 제어
        
        Parameters:
        -----------
        device_list : list
            제어할 장치명 리스트 (예: ["1-1", "1-2", "선생영역"])
        state : int
            0: 끄기, 1: 켜기
        """
        print(f"[*] 여러 장치 제어: {', '.join(device_list)}, 상태: {'켜기' if state else '끄기'}")
        
        payload = self.create_multi_device_payload(device_list, state)
        if payload is None:
            return False
            
        # 소켓 통신으로 전송 (기존 send_command 로직과 유사)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((self.target_ip, self.target_port))
            
            source_port = s.getsockname()[1]
            
            print(f"[*] 패킷 정보:")
            print(f"    - 소스 IP: 192.168.0.100, 포트: {source_port}")
            print(f"    - 대상 IP: {self.target_ip}, 포트: {self.target_port}")
            print(f"    - 페이로드 길이: {len(payload)} 바이트")
            
            # 페이로드 전송
            s.sendall(payload)
            
            # 응답 대기
            try:
                response = s.recv(1024)
                if response:
                    print(f"[+] 응답 수신: {len(response)} 바이트")
                    print(f"    - 헥스: {response.hex()}")
                else:
                    print("[!] 응답 없음")
            except socket.timeout:
                print("[!] 응답 타임아웃")
            
            s.close()
            
            print("[+] 패킷 전송 완료")
            self.packet_counter += 1
            return True
            
        except Exception as e:
            print(f"[!] 패킷 전송 실패: {e}")
        
        return False

def get_interface_list():
    """사용 가능한 네트워크 인터페이스 목록 반환"""
    interfaces = []
    
    if os.name == 'nt':  # Windows
        try:
            # 스캐피 인터페이스 목록 사용
            for name, iface in IFACES.items():
                if iface.ip:  # IP가 있는 인터페이스만 선택
                    interfaces.append({
                        'name': name,
                        'description': iface.description or "설명 없음",
                        'ip': iface.ip or "IP 없음",
                        'mac': iface.mac or "MAC 없음"
                    })
        except Exception as e:
            print(f"[!] 인터페이스 목록 조회 실패: {e}")
    else:  # Linux/macOS
        try:
            import netifaces
            interfaces_list = netifaces.interfaces()
            
            for iface in interfaces_list:
                try:
                    addrs = netifaces.ifaddresses(iface)
                    if netifaces.AF_INET in addrs:  # IP가 있는 인터페이스만
                        ip = addrs[netifaces.AF_INET][0]['addr']
                        interfaces.append({
                            'name': iface,
                            'description': iface,
                            'ip': ip,
                            'mac': "MAC 없음"
                        })
                except Exception:
                    pass
        except ImportError:
            print("[!] netifaces 모듈이 설치되지 않았습니다.")
    
    return interfaces

def main():
    """
    학교 방송 제어 프로그램 메인 함수
    """
    print("="*50)
    print("학교 방송 제어 시스템 v1.0")
    print("="*50)
    
    # 네트워크 인터페이스 목록 가져오기
    interfaces = get_interface_list()
    
    if not interfaces:
        print("[!] 사용 가능한 네트워크 인터페이스를 찾을 수 없습니다.")
        print("    네트워크 연결을 확인하고 다시 시도하세요.")
        return
    
    # 인터페이스 목록 표시
    print("[*] 사용 가능한 네트워크 인터페이스:")
    for i, iface in enumerate(interfaces):
        print(f"    {i+1}. {iface['name']} - {iface['description']}")
        print(f"       IP: {iface['ip']}, MAC: {iface['mac']}")
    
    # 인터페이스 선택
    selected = input("\n[?] 사용할 인터페이스 번호를 입력하세요 (기본값: 1): ")
    if not selected:
        selected = 1
    else:
        try:
            selected = int(selected)
            if selected < 1 or selected > len(interfaces):
                print("[!] 잘못된 번호입니다. 기본값 1을 사용합니다.")
                selected = 1
        except ValueError:
            print("[!] 잘못된 번호입니다. 기본값 1을 사용합니다.")
            selected = 1
    
    # 선택된 인터페이스 정보
    selected_iface = interfaces[selected-1]
    print(f"[*] 선택된 인터페이스: {selected_iface['name']}")
    
    # 대상 IP 입력
    target_ip = input(f"[?] 대상 장비 IP (기본값: 192.168.0.200): ") or "192.168.0.200"
    
    # 대상 포트 입력
    target_port_str = input(f"[?] 대상 장비 포트 (기본값: 22000): ") or "22000"
    try:
        target_port = int(target_port_str)
    except ValueError:
        print("[!] 잘못된 포트 번호입니다. 기본값 22000을 사용합니다.")
        target_port = 22000
    
    # 방송 제어 객체 생성
    controller = BroadcastController(
        interface=selected_iface['name'],
        target_ip=target_ip,
        target_port=target_port
    )
    
    # 시스템 상태 초기화
    print("\n[*] 시스템 상태 확인 중...")
    controller.initialize_system_state()
    
    # 메인 메뉴 루프
    while True:
        print("\n" + "="*50)
        print("학교 방송 제어 시스템 - 메인 메뉴")
        print("="*50)
        print("1. 장비 켜기/끄기")
        print("2. 볼륨 제어")
        print("3. 채널 선택")
        print("4. 예약 방송 설정")
        print("5. 예약 방송 조회/삭제")
        print("6. 테스트 메뉴")
        print("7. 설정")
        print("8. 상태 관리 (3학년)")
        print("0. 종료")
        print("="*50)
        
        choice = input("\n메뉴 선택: ")
        
        if choice == "1":
            # 장비 켜기/끄기 메뉴
            print("\n" + "-"*40)
            print("장비 켜기/끄기")
            print("-"*40)
            print("1. 모든 장비 켜기")
            print("2. 모든 장비 끄기")
            print("3. 특정 채널 켜기")
            print("4. 특정 채널 끄기")
            print("0. 이전 메뉴로")
            
            sub_choice = input("\n선택: ")
            
            if sub_choice == "1":
                # 모든 장비 켜기 - 기본 채널 (1번)
                controller.send_command(command_type=0x01, channel=0x01, state=0x01)
            elif sub_choice == "2":
                # 모든 장비 끄기 - 기본 채널 (1번)
                controller.send_command(command_type=0x01, channel=0x01, state=0x00)
            elif sub_choice == "3":
                # 특정 채널 켜기
                try:
                    channel = int(input("채널 번호 (기본: 1): ") or "1")
                    controller.send_command(command_type=0x01, channel=channel, state=0x01)
                except ValueError:
                    print("[!] 잘못된 채널 번호입니다.")
            elif sub_choice == "4":
                # 특정 채널 끄기
                try:
                    channel = int(input("채널 번호 (기본: 1): ") or "1")
                    controller.send_command(command_type=0x01, channel=channel, state=0x00)
                except ValueError:
                    print("[!] 잘못된 채널 번호입니다.")
            elif sub_choice == "0":
                continue
            else:
                print("[!] 잘못된 선택입니다.")
                
        elif choice == "2":
            # 볼륨 제어 메뉴
            print("\n" + "-"*40)
            print("볼륨 제어")
            print("-"*40)
            print("1. 볼륨 설정")
            print("0. 이전 메뉴로")
            
            sub_choice = input("\n선택: ")
            
            if sub_choice == "1":
                try:
                    volume = int(input("볼륨 레벨 (0-10): "))
                    if 0 <= volume <= 10:
                        # 볼륨 제어 명령
                        controller.send_command(command_type=0x02, channel=0x01, state=volume)
                    else:
                        print("[!] 볼륨은 0에서 10 사이여야 합니다.")
                except ValueError:
                    print("[!] 잘못된 볼륨 레벨입니다.")
            elif sub_choice == "0":
                continue
            else:
                print("[!] 잘못된 선택입니다.")
                
        elif choice == "3":
            # 채널 선택 메뉴
            print("\n" + "-"*40)
            print("채널 선택")
            print("-"*40)
            print("1. 기본 채널 (0x01)")
            print("2. 그룹 채널 (0x40)")
            print("3. 특수 채널 (0xD0)")
            print("4. 사용자 지정 채널")
            print("0. 이전 메뉴로")
            
            sub_choice = input("\n선택: ")
            
            if sub_choice == "1":
                # 기본 채널 제어
                state = int(input("상태 (0: 끄기, 1: 켜기): ") or "1")
                controller.send_command(command_type=0x01, channel=0x01, state=state)
            elif sub_choice == "2":
                # 그룹 채널 제어 (0x40 = 64)
                state = int(input("상태 (0: 끄기, 1: 켜기): ") or "1")
                controller.send_command(command_type=0x01, channel=0x40, state=state, use_default_payload=False)
            elif sub_choice == "3":
                # 특수 채널 제어 (0xD0 = 208)
                state = int(input("상태 (0: 끄기, 1: 켜기): ") or "1")
                controller.send_command(command_type=0x01, channel=0xD0, state=state, use_default_payload=False)
            elif sub_choice == "4":
                # 사용자 지정 채널 제어
                try:
                    channel = int(input("채널 번호: "))
                    state = int(input("상태 (0: 끄기, 1: 켜기): ") or "1")
                    controller.send_command(command_type=0x01, channel=channel, state=state)
                except ValueError:
                    print("[!] 잘못된 입력입니다.")
            elif sub_choice == "0":
                continue
            else:
                print("[!] 잘못된 선택입니다.")
                
        elif choice == "4":
            # 예약 방송 설정
            print("\n" + "-"*40)
            print("예약 방송 설정")
            print("-"*40)
            
            # 시간 입력 (HH:MM 형식)
            time_str = input("시간 (HH:MM): ")
            
            # 시간 형식 확인
            if not re.match(r"^([0-1][0-9]|2[0-3]):([0-5][0-9])$", time_str):
                print("[!] 잘못된 시간 형식입니다. (예: 08:30, 14:15)")
                continue
            
            # 요일 선택
            print("\n요일 선택:")
            print("1. 월요일")
            print("2. 화요일")
            print("3. 수요일")
            print("4. 목요일")
            print("5. 금요일")
            print("6. 토요일")
            print("7. 일요일")
            print("8. 매일")
            
            days_input = input("요일 번호 (쉼표로 구분, 예: 1,3,5): ")
            
            # 요일 매핑
            day_map = {
                "1": "Monday",
                "2": "Tuesday",
                "3": "Wednesday",
                "4": "Thursday",
                "5": "Friday",
                "6": "Saturday",
                "7": "Sunday",
                "8": "Everyday"
            }
            
            days = []
            for day_num in days_input.split(","):
                day = day_map.get(day_num.strip())
                if day:
                    days.append(day)
            
            if not days:
                print("[!] 유효한 요일을 선택해야 합니다.")
                continue
            
            # 명령 타입 선택
            print("\n명령 타입:")
            print("1. 장비 켜기/끄기 (기본)")
            print("2. 볼륨 제어")
            print("3. 채널 변경")
            
            cmd_type = int(input("명령 타입 (기본: 1): ") or "1")
            
            # 채널 선택
            print("\n채널 선택:")
            print("1. 기본 채널 (0x01)")
            print("2. 그룹 채널 (0x40)")
            print("3. 특수 채널 (0xD0)")
            print("4. 사용자 지정 채널")
            
            channel_choice = input("채널 선택 (기본: 1): ") or "1"
            
            if channel_choice == "1":
                channel = 0x01
            elif channel_choice == "2":
                channel = 0x40
            elif channel_choice == "3":
                channel = 0xD0
            elif channel_choice == "4":
                channel = int(input("채널 번호: "))
            else:
                print("[!] 잘못된 채널 선택입니다. 기본 채널을 사용합니다.")
                channel = 0x01
            
            # 상태 입력
            if cmd_type == 1:  # 장비 켜기/끄기
                state = int(input("상태 (0: 끄기, 1: 켜기): ") or "1")
            elif cmd_type == 2:  # 볼륨 제어
                state = int(input("볼륨 레벨 (0-10): ") or "5")
                if state < 0 or state > 10:
                    print("[!] 잘못된 볼륨 레벨입니다. 기본값 5를 사용합니다.")
                    state = 5
            else:
                state = int(input("상태 값: ") or "1")
            
            # 예약 추가
            controller.schedule_broadcast(time_str, ','.join(days), cmd_type, channel, state)
            
            # 스케줄러 시작 (이미 실행 중이 아니라면)
            controller.start_scheduler()
            
        elif choice == "5":
            # 예약 방송 조회/삭제
            print("\n" + "-"*40)
            print("예약 방송 조회/삭제")
            print("-"*40)
            
            schedules = controller.view_schedules()
            
            if not schedules:
                print("[!] 저장된 예약 방송이 없습니다.")
                continue
            
            print("\n" + "-"*70)
            print("번호 | 시간  | 요일                     | 명령 타입   | 채널     | 상태")
            print("-"*70)
            
            for i, schedule in enumerate(schedules):
                time_str = schedule.get('time', '')
                days = schedule.get('days', '')
                cmd_type = int(schedule.get('command_type', 1))
                channel = int(schedule.get('channel', 1))
                state = int(schedule.get('state', 1))
                
                # 명령 타입 변환
                cmd_type_str = {
                    1: "장비 켜기/끄기",
                    2: "볼륨 제어",
                    3: "채널 변경"
                }.get(cmd_type, f"알 수 없음({cmd_type})")
                
                # 채널 변환
                channel_str = {
                    0x01: "기본(0x01)",
                    0x40: "그룹(0x40)",
                    0xD0: "특수(0xD0)"
                }.get(channel, f"채널({channel})")
                
                # 상태 변환
                if cmd_type == 1:  # 장비 켜기/끄기
                    state_str = "켜기" if state == 1 else "끄기"
                elif cmd_type == 2:  # 볼륨 제어
                    state_str = f"볼륨({state})"
                else:
                    state_str = str(state)
                
                print(f"{i+1:4} | {time_str:5} | {days:24} | {cmd_type_str:10} | {channel_str:8} | {state_str}")
            
            print("-"*70)
            
            # 삭제 옵션
            delete = input("\n삭제할 예약 번호 (취소: 0): ")
            
            if delete == "0":
                continue
            
            try:
                delete_idx = int(delete) - 1
                if 0 <= delete_idx < len(schedules):
                    controller.delete_schedule(delete_idx)
                    print("[+] 예약이 삭제되었습니다.")
                else:
                    print("[!] 잘못된 예약 번호입니다.")
            except ValueError:
                print("[!] 잘못된 입력입니다.")
                
        elif choice == "6":
            # 테스트 메뉴
            print("\n" + "-"*40)
            print("테스트 메뉴")
            print("-"*40)
            print("1. 기본 채널 테스트")
            print("2. 그룹 채널 테스트")
            print("3. 특수 채널 테스트")
            print("4. 모든 테스트 (순차 실행)")
            print("0. 이전 메뉴로")
            
            sub_choice = input("\n선택: ")
            
            if sub_choice == "1":
                # 기본 채널 테스트 서브메뉴
                print("\n" + "-"*40)
                print("기본 채널 테스트")
                print("-"*40)
                print("1. 기본 채널 켜기 (ON)")
                print("2. 기본 채널 끄기 (OFF)")
                print("3. 켜기+끄기 순차 테스트")
                print("0. 이전 메뉴로")
                
                basic_choice = input("\n선택: ")
                
                if basic_choice == "1":
                    # 기본 채널 켜기만
                    print("\n[*] 기본 채널 ON 테스트...")
                    controller.send_command(command_type=0x01, channel=0x00, state=0x01)
                elif basic_choice == "2":
                    # 기본 채널 끄기만
                    print("\n[*] 기본 채널 OFF 테스트...")
                    controller.send_command(command_type=0x01, channel=0x00, state=0x00)
                elif basic_choice == "3":
                    # 켜기+끄기 순차 테스트
                    print("\n[*] 기본 채널 ON 테스트...")
                    controller.send_command(command_type=0x01, channel=0x00, state=0x01)
                    time.sleep(2)
                    
                    print("\n[*] 기본 채널 OFF 테스트...")
                    controller.send_command(command_type=0x01, channel=0x00, state=0x00)
                elif basic_choice == "0":
                    continue
                else:
                    print("[!] 잘못된 선택입니다.")
                
            elif sub_choice == "2":
                # 그룹 채널 테스트 서브메뉴
                print("\n" + "-"*40)
                print("그룹 채널 테스트")
                print("-"*40)
                print("1. 그룹 채널 켜기 (ON)")
                print("2. 그룹 채널 끄기 (OFF)")
                print("3. 켜기+끄기 순차 테스트")
                print("0. 이전 메뉴로")
                
                group_choice = input("\n선택: ")
                
                if group_choice == "1":
                    # 그룹 채널 켜기만
                    print("\n[*] 그룹 채널 ON 테스트...")
                    controller.send_command(command_type=0x01, channel=0x40, state=0x01, use_default_payload=False)
                elif group_choice == "2":
                    # 그룹 채널 끄기만
                    print("\n[*] 그룹 채널 OFF 테스트...")
                    controller.send_command(command_type=0x01, channel=0x40, state=0x00, use_default_payload=False)
                elif group_choice == "3":
                    # 켜기+끄기 순차 테스트
                    print("\n[*] 그룹 채널 ON 테스트...")
                    controller.send_command(command_type=0x01, channel=0x40, state=0x01, use_default_payload=False)
                    time.sleep(2)
                    
                    print("\n[*] 그룹 채널 OFF 테스트...")
                    controller.send_command(command_type=0x01, channel=0x40, state=0x00, use_default_payload=False)
                elif group_choice == "0":
                    continue
                else:
                    print("[!] 잘못된 선택입니다.")
                
            elif sub_choice == "3":
                # 특수 채널 테스트 서브메뉴
                print("\n" + "-"*40)
                print("특수 채널 테스트")
                print("-"*40)
                print("1. 특수 채널 켜기 (ON)")
                print("2. 특수 채널 끄기 (OFF)")
                print("3. 켜기+끄기 순차 테스트")
                print("0. 이전 메뉴로")
                
                special_choice = input("\n선택: ")
                
                if special_choice == "1":
                    # 특수 채널 켜기만
                    print("\n[*] 특수 채널 ON 테스트...")
                    controller.send_command(command_type=0x01, channel=0xD0, state=0x01, use_default_payload=False)
                elif special_choice == "2":
                    # 특수 채널 끄기만
                    print("\n[*] 특수 채널 OFF 테스트...")
                    controller.send_command(command_type=0x01, channel=0xD0, state=0x00, use_default_payload=False)
                elif special_choice == "3":
                    # 켜기+끄기 순차 테스트
                    print("\n[*] 특수 채널 ON 테스트...")
                    controller.send_command(command_type=0x01, channel=0xD0, state=0x01, use_default_payload=False)
                    time.sleep(2)
                    
                    print("\n[*] 특수 채널 OFF 테스트...")
                    controller.send_command(command_type=0x01, channel=0xD0, state=0x00, use_default_payload=False)
                elif special_choice == "0":
                    continue
                else:
                    print("[!] 잘못된 선택입니다.")
                
            elif sub_choice == "4":
                # 모든 테스트 순차 실행
                print("\n[*] 종합 테스트 시작...")
                
                # 기본 채널 테스트
                print("\n[*] 1. 기본 채널 ON 테스트...")
                controller.send_command(command_type=0x01, channel=0x00, state=0x01)
                time.sleep(2)
                
                print("\n[*] 2. 기본 채널 OFF 테스트...")
                controller.send_command(command_type=0x01, channel=0x00, state=0x00)
                time.sleep(2)
                
                # 그룹 채널 테스트
                print("\n[*] 3. 그룹 채널 ON 테스트...")
                controller.send_command(command_type=0x01, channel=0x40, state=0x01, use_default_payload=False)
                time.sleep(2)
                
                print("\n[*] 4. 그룹 채널 OFF 테스트...")
                controller.send_command(command_type=0x01, channel=0x40, state=0x00, use_default_payload=False)
                time.sleep(2)
                
                # 특수 채널 테스트
                print("\n[*] 5. 특수 채널 ON 테스트...")
                controller.send_command(command_type=0x01, channel=0xD0, state=0x01, use_default_payload=False)
                time.sleep(2)
                
                print("\n[*] 6. 특수 채널 OFF 테스트...")
                controller.send_command(command_type=0x01, channel=0xD0, state=0x00, use_default_payload=False)
                
                print("\n[*] 테스트 완료!")
                
            elif sub_choice == "0":
                continue
                
            else:
                print("[!] 잘못된 선택입니다.")
                
        elif choice == "7":
            # 설정 메뉴
            print("\n" + "-"*40)
            print("설정")
            print("-"*40)
            print("1. 대상 IP 변경")
            print("2. 대상 포트 변경")
            print("3. 스케줄러 시작")
            print("4. 스케줄러 중지")
            print("0. 이전 메뉴로")
            
            sub_choice = input("\n선택: ")
            
            if sub_choice == "1":
                # 대상 IP 변경
                new_ip = input(f"새 대상 IP (현재: {controller.target_ip}): ")
                if new_ip:
                    controller.target_ip = new_ip
                    print(f"[+] 대상 IP가 {new_ip}로 변경되었습니다.")
                    
            elif sub_choice == "2":
                # 대상 포트 변경
                try:
                    new_port = int(input(f"새 대상 포트 (현재: {controller.target_port}): "))
                    controller.target_port = new_port
                    print(f"[+] 대상 포트가 {new_port}로 변경되었습니다.")
                except ValueError:
                    print("[!] 잘못된 포트 번호입니다.")
                    
            elif sub_choice == "3":
                # 스케줄러 시작
                controller.start_scheduler()
                
            elif sub_choice == "4":
                # 스케줄러 중지
                controller.stop_scheduler()
                
            elif sub_choice == "0":
                continue
                
            else:
                print("[!] 잘못된 선택입니다.")
                
        elif choice == "8":
            # 상태 관리 메뉴 (3학년)
            print("\n" + "-"*40)
            print("상태 관리 (3학년)")
            print("-"*40)
            
            # 현재 상태 표시
            active_rooms = controller.active_rooms
            print("\n현재 상태:")
            if 301 in active_rooms:
                print("- 3학년 1반: 켜짐")
            else:
                print("- 3학년 1반: 꺼짐")
                
            if 302 in active_rooms:
                print("- 3학년 2반: 켜짐")
            else:
                print("- 3학년 2반: 꺼짐")
            
            print("\n1. 3학년 1반 켜기")
            print("2. 3학년 1반 끄기")
            print("3. 3학년 2반 켜기")
            print("4. 3학년 2반 끄기")
            print("5. 3학년 모든 반 켜기")
            print("6. 3학년 모든 반 끄기")
            print("7. 시스템 상태 초기화")
            print("0. 이전 메뉴로")
            
            sub_choice = input("\n선택: ")
            
            if sub_choice == "1":
                # 3학년 1반 켜기
                controller.set_room_state(301, 1)
            elif sub_choice == "2":
                # 3학년 1반 끄기
                controller.set_room_state(301, 0)
            elif sub_choice == "3":
                # 3학년 2반 켜기
                controller.set_room_state(302, 1)
            elif sub_choice == "4":
                # 3학년 2반 끄기
                controller.set_room_state(302, 0)
            elif sub_choice == "5":
                # 3학년 모든 반 켜기
                controller.set_room_state(301, 1)
                time.sleep(0.5)
                controller.set_room_state(302, 1)
            elif sub_choice == "6":
                # 3학년 모든 반 끄기
                controller.set_room_state(302, 0)
                time.sleep(0.5)
                controller.set_room_state(301, 0)
            elif sub_choice == "7":
                # 시스템 상태 초기화
                controller.initialize_system_state()
            elif sub_choice == "0":
                continue
            else:
                print("[!] 잘못된 선택입니다.")
                
        elif choice == "0":
            # 종료
            if controller.scheduler_thread and controller.scheduler_thread.is_alive():
                controller.stop_scheduler()
                
            print("\n[*] 프로그램을 종료합니다...")
            break
            
        else:
            print("[!] 잘못된 선택입니다. 다시 시도하세요.")

# 모듈로 임포트된 경우가 아니라 직접 실행된 경우에만 main() 호출
if __name__ == "__main__":
    main() 
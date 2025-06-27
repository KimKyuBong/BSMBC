#!/usr/bin/env python3
"""
방송 제어 컨트롤러 모듈
방송 시스템 전체 제어를 담당합니다.
"""
import os
import time
import threading
import logging
import json
import shutil
import datetime
import wave
import contextlib
import numpy as np
import pyaudio
import traceback
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple, Optional, Union
from fastapi import UploadFile, HTTPException
import sys

# 멜로 TTS 및 오디오 처리 라이브러리
TTS_ENGINE = None

try:
    import pyttsx3
    TTS_ENGINE = "pyttsx3"
    print("[*] pyttsx3 TTS 엔진이 로드되었습니다.")
except ImportError:
    try:
        from gtts import gTTS
        TTS_ENGINE = "gtts"
        print("[*] gTTS 엔진이 로드되었습니다.")
    except ImportError:
        # MeloTTS 시도는 일단 건너뜁니다
        try:
            import vlc
            print("[*] VLC 모듈이 로드되었습니다. 오디오 재생이 가능합니다.")
        except ImportError:
            print("[!] 경고: VLC 모듈을 로드할 수 없습니다. 오디오 재생이 제한될 수 있습니다.")
        
        print("[!] 경고: TTS 엔진을 로드할 수 없습니다. 텍스트-음성 변환 기능이 비활성화됩니다.")

from ..core.config import config
from ..core.device_mapping import device_mapper
from .packet_builder import packet_builder
from .network import network_manager
from .scheduler import broadcast_scheduler

# 로깅 설정
logger = logging.getLogger(__name__)

# 음성 파일 저장 경로와 TTS 모델 경로는 config에서 이미 설정되어 있음
AUDIO_DIR = Path(config.audio_dir)
TTS_MODELS_DIR = Path(config.tts_models_dir)

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
        
        # 오디오 재생 관련 속성
        self.player = None
        self.is_playing = False
        self.broadcast_thread = None
        
        # TTS 모델 속성
        self.tts_model = None
        self.tts_initialized = False
    
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
                # device_mapper를 사용하여 장치 ID 가져오기
                room_id = self.device_mapper._get_device_id(device_name)
                if room_id is None:
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
            또는 방 ID 리스트 (예: [301, 302, 303]) 
        state : int
            0: 끄기, 1: 켜기
            
        Returns:
        --------
        bool
            성공 여부
        """
        print(f"[*] 여러 장치 제어: {', '.join(map(str, device_list))}, 상태: {'켜기' if state else '끄기'}")
        
        # 각 장치의 상태를 메모리에 업데이트
        for device_name in device_list:
            try:
                # device_name 타입 확인 로깅
                print(f"[*] 처리 중인 device_name: {device_name} (타입: {type(device_name).__name__})")
                
                # 이미 숫자 ID 형식으로 들어온 경우 (예: 301, 302)
                if isinstance(device_name, int):
                    room_id = device_name
                    print(f"[*] 숫자 ID로 직접 처리: {room_id}")
                # 문자열 타입 처리
                elif isinstance(device_name, str):
                    # 숫자 문자열인 경우 (예: "301")
                    if device_name.isdigit():
                        room_id = int(device_name)
                        print(f"[*] 숫자 문자열을 숫자 ID로 변환: {device_name} -> {room_id}")
                    # 학년-반 형식 (예: "1-1", "3-2")
                    elif '-' in device_name and device_name[0].isdigit():
                        grade, class_num = device_name.split('-')
                        grade = int(grade)
                        class_num = int(class_num)
                        
                        # 룸 ID 계산 (예: 1학년 1반 -> 101, 3학년 1반 -> 301)
                        room_id = grade * 100 + class_num
                        print(f"[*] 학년-반 처리: {device_name} -> ID {room_id}")
                    else:
                        # device_mapper를 사용하여 장치 ID 가져오기
                        room_id = self.device_mapper._get_device_id(device_name)
                        if room_id is None:
                            print(f"[!] 알 수 없는 장치명: {device_name}")
                            continue
                        print(f"[*] 특수공간 처리: {device_name} -> ID {room_id}")
                else:
                    print(f"[!] 지원되지 않는 데이터 타입: {type(device_name).__name__}")
                    continue
                
                # 상태에 따라 활성 방 목록 업데이트
                if state:
                    self.active_rooms.add(room_id)
                    print(f"[*] 활성화된 방 추가: {room_id} (현재 목록: {self.active_rooms})")
                else:
                    self.active_rooms.discard(room_id)
                    print(f"[*] 활성화된 방 제거: {room_id} (현재 목록: {self.active_rooms})")
                    
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

    def initialize_tts(self, language="ko"):
        """
        TTS 모델 초기화
        
        Parameters:
        -----------
        language : str
            TTS에 사용할 언어 (기본값: 한국어)
            
        Returns:
        --------
        bool
            성공 여부
        """
        try:
            print(f"[*] TTS 서비스 초기화 중 (언어: {language})...")
            
            # 통합 TTS 서비스 사용
            from .tts_service import init_tts_service
            
            # 캐시 디렉토리 설정
            cache_dir = os.path.join(config.app_data_dir, "tts_models")
            os.makedirs(cache_dir, exist_ok=True)
            
            # TTS 서비스 초기화
            self.tts_service = init_tts_service(cache_dir=cache_dir)
            
            # 언어 설정
            self.tts_service.change_language(language)
            
            # TTS 정보 출력
            tts_info = self.tts_service.get_tts_info()
            print(f"[*] 활성화된 TTS 엔진: {tts_info['description']} (품질: {tts_info['quality']})")
            
            self.tts_initialized = True
            print(f"[*] TTS 서비스 초기화 완료 (언어: {language})")
            return True
            
        except Exception as e:
            print(f"[!] TTS 서비스 초기화 실패: {e}")
            traceback.print_exc()
            self.tts_initialized = False
            return False
    
    def generate_speech(self, text, output_path=None, language="ko"):
        """
        텍스트를 음성으로 변환
        
        Parameters:
        -----------
        text : str
            변환할 텍스트
        output_path : str or Path
            출력 파일 경로 (지정하지 않으면 자동 생성)
        language : str
            텍스트 언어 (기본값: 한국어)
            
        Returns:
        --------
        Path or None
            생성된 음성 파일 경로 또는 실패시 None
        """
        try:
            # 텍스트가 비어있으면 오류
            if not text or not text.strip():
                print("[!] 오류: 변환할 텍스트가 비어있습니다.")
                return None
            
            # TTS 서비스가 초기화되지 않았으면 초기화
            if not hasattr(self, 'tts_service') or not self.tts_initialized:
                print("[*] TTS 서비스가 초기화되지 않았습니다. 초기화를 시도합니다...")
                success = self.initialize_tts(language)
                if not success:
                    print("[!] TTS 서비스 초기화 실패, 음성 변환을 진행할 수 없습니다.")
                    return None
            
            # 출력 경로가 지정되지 않았으면 자동 생성
            if output_path is None:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = Path(os.path.join(config.audio_dir, f"tts_{timestamp}.wav"))
            else:
                output_path = Path(output_path)
            
            # 디렉토리가 존재하지 않으면 생성
            os.makedirs(output_path.parent, exist_ok=True)
            
            # 텍스트 내용 로깅 (긴 텍스트는 일부만 표시)
            display_text = text[:50] + ('...' if len(text) > 50 else '')
            print(f"[*] 텍스트를 음성으로 변환 중: '{display_text}'")
            
            # TTS 서비스를 사용하여 음성 생성
            start_time = time.time()
            result_path = self.tts_service.synthesize(text, output_path=output_path, language=language)
            
            if not result_path:
                print("[!] 음성 생성 실패")
                return None
                
            elapsed_time = time.time() - start_time
            print(f"[*] 음성 파일 생성 완료: {output_path} (소요 시간: {elapsed_time:.2f}초)")
            
            return output_path
            
        except Exception as e:
            print(f"[!] 음성 생성 실패: {e}")
            traceback.print_exc()
            return None
    
    def play_audio(self, audio_path):
        """
        오디오 파일 재생
        
        Parameters:
        -----------
        audio_path : str or Path
            재생할 오디오 파일 경로
            
        Returns:
        --------
        bool
            성공 여부
        """
        try:
            # 파일이 존재하는지 확인
            audio_path = Path(audio_path)
            if not audio_path.exists():
                print(f"[!] 오류: 오디오 파일이 존재하지 않습니다: {audio_path}")
                return False
            
            # 파일 확장자 확인
            file_ext = audio_path.suffix.lower()
            
            # 이미 재생 중이면 중지
            if self.is_playing and hasattr(self, 'player'):
                print("[*] 이미 재생 중인 오디오가 있습니다. 중지 후 새로운 오디오를 재생합니다.")
                self.stop_audio()
            
            print(f"[*] 오디오 파일 재생 준비: {audio_path}")
            
            # 먼저 VLC를 사용해 시도
            try:
                if 'vlc' not in sys.modules:
                    # VLC 모듈 동적 임포트
                    import vlc
                    print("[*] VLC 모듈 로드됨")
                else:
                    import vlc
                
                # 오류 방지용 딜레이
                time.sleep(0.1)
                    
                # VLC 인스턴스 초기화 (더 많은 옵션 추가)
                vlc_instance = vlc.Instance('--no-audio-time-stretch', '--audio-resampler=soxr', '--no-video')
                
                # 미디어 플레이어 생성
                self.player = vlc_instance.media_player_new()
                
                # 미디어 객체 생성
                media = vlc_instance.media_new(str(audio_path))
                
                # 이벤트 관리 변수 설정
                self.playback_finished = False
                
                # 종료 이벤트 관리를 위한 이벤트 매니저 설정
                event_manager = media.event_manager()
                
                # 이벤트 콜백 함수
                def handle_end_event(event):
                    # VLC 상태가 실제로 종료되었는지 확인
                    if event.u.new_state in [vlc.State.Ended, vlc.State.Error, vlc.State.Stopped]:
                        self.playback_finished = True
                        print(f"[*] VLC 이벤트: 미디어 재생 완료 (상태: {event.u.new_state})")
                
                # 종료 이벤트 리스너 등록
                event_manager.event_attach(vlc.EventType.MediaStateChanged, handle_end_event)
                
                # 미디어를 플레이어에 설정
                self.player.set_media(media)
                
                # 재생 볼륨 설정 - 최대 볼륨으로 설정 (100%에서 150%로 증가)
                self.player.audio_set_volume(100)
                print(f"[*] 오디오 볼륨 설정: 100%")
                
                # 상태 설정
                self.is_playing = True
                
                # 재생 시작
                play_result = self.player.play()
                
                if play_result == 0:
                    print(f"[*] 오디오 재생 시작 (VLC 사용): {audio_path}")
                    
                    # 상태 확인을 위한 대기
                    time.sleep(0.5)
                    
                    # 재생 상태 확인
                    if self.player.get_state() in [vlc.State.Playing, vlc.State.Opening]:
                        # 오디오 정보 표시
                        try:
                            # 오디오 길이 가져오기 시도
                            max_tries = 10
                            for i in range(max_tries):
                                duration_ms = self.player.get_length()
                                if duration_ms > 0:
                                    print(f"[*] 오디오 길이: {duration_ms/1000:.1f}초")
                                    break
                                time.sleep(0.2)  # 길이 정보를 가져올 수 있을 때까지 짧게 대기
                            
                            # 여전히 길이를 가져오지 못한 경우
                            if duration_ms <= 0:
                                # 대체 방법으로 wave 모듈 사용 시도
                                try:
                                    with contextlib.closing(wave.open(str(audio_path), 'r')) as f:
                                        frames = f.getnframes()
                                        rate = f.getframerate()
                                        duration = frames / float(rate)
                                        print(f"[*] 오디오 길이(wave 사용): {duration:.1f}초")
                                except:
                                    print("[!] 오디오 길이를 결정할 수 없습니다.")
                        except Exception as e:
                            print(f"[!] 오디오 정보 가져오기 실패: {e}")
                        
                        # 재생 모니터링 스레드 시작
                        self.player_thread = threading.Thread(
                            target=self._monitor_vlc_playback,
                            daemon=True
                        )
                        self.player_thread.start()
                        
                        return True
                    else:
                        print(f"[!] VLC 재생 상태가 Playing이 아님: {self.player.get_state()}")
                else:
                    print(f"[!] VLC 재생 시작 실패: {play_result}")
            except Exception as e:
                print(f"[!] VLC로 오디오 재생 실패: {e}")
                traceback.print_exc()
                
            # 여기서부터는 VLC 실패 시의 대체 방법들
            # VLC 재생에 실패한 경우 PyAudio 또는 다른 방법으로 시도
            print("[*] 대체 방법으로 오디오 재생을 시도합니다...")
            
            # pydub 시도
            try:
                if 'pydub' in sys.modules:
                    from pydub import AudioSegment
                    from pydub.playback import play
                    
                    print("[*] pydub으로 오디오 재생을 시도합니다...")
                    sound = AudioSegment.from_file(audio_path)
                    
                    # 백그라운드 재생을 위한 스레드 생성
                    def _play_pydub():
                        self.is_playing = True
                        play(sound)
                        self.is_playing = False
                        print("[*] pydub 오디오 재생 완료")
                    
                    self.player_thread = threading.Thread(target=_play_pydub, daemon=True)
                    self.player_thread.start()
                    return True
            except Exception as e:
                print(f"[!] pydub으로 오디오 재생 실패: {e}")
            
            # PyAudio 시도
            try:
                import wave
                
                # WAV 파일인지 확인
                if file_ext != '.wav':
                    # 다른 형식을 WAV로 변환 시도
                    try:
                        if 'pydub' in sys.modules:
                            from pydub import AudioSegment
                            temp_wav_path = audio_path.with_suffix('.temp.wav')
                            sound = AudioSegment.from_file(audio_path)
                            sound.export(temp_wav_path, format="wav")
                            print(f"[*] 파일 변환 완료: {temp_wav_path}")
                            audio_path = temp_wav_path
                    except Exception as e:
                        print(f"[!] 파일 변환 실패: {e}")
                
                print("[*] PyAudio를 사용하여 오디오 재생을 시도합니다...")
                try:
                    # WAV 파일 정보 읽기
                    with wave.open(str(audio_path), 'rb') as wf:
                        # PyAudio 초기화
                        import pyaudio
                        self.player = pyaudio.PyAudio()
                        
                        # 스트림 열기
                        stream = self.player.open(
                            format=self.player.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True
                        )
                        
                        # 파일 정보 출력
                        print(f"[*] 오디오 형식: {wf.getframerate()}Hz, {wf.getnchannels()} 채널")
                        
                        # 파일 길이 계산 (초)
                        frames = wf.getnframes()
                        rate = wf.getframerate()
                        duration = frames / float(rate)
                        print(f"[*] 오디오 길이: {duration:.1f}초")
                        
                        # 스트림과 파일 정보 저장
                        self.player_info = {
                            'stream': stream,
                            'wf': wf,
                            'data': wf.readframes(frames)  # 모든 오디오 데이터 읽기
                        }
                        
                        # 재생 스레드 시작
                        self.player_thread = threading.Thread(
                            target=self._play_audio_thread,
                            daemon=True
                        )
                        self.player_thread.start()
                        
                        # 재생 상태 설정
                        self.is_playing = True
                        print(f"[*] 오디오 재생 시작 (PyAudio 사용): {audio_path}")
                        
                        return True
                except wave.Error as we:
                    print(f"[!] WAV 파일 처리 중 오류: {we}")
            except Exception as e:
                print(f"[!] PyAudio로 오디오 재생 실패: {e}")
                
            print("[!] 모든 오디오 재생 방법이 실패했습니다.")
            return False
                
        except Exception as e:
            print(f"[!] 오디오 재생 중 오류 발생: {e}")
            traceback.print_exc()
            return False
            
    def _play_audio_thread(self):
        """
        PyAudio로 오디오 재생을 처리하는 스레드 함수
        """
        try:
            stream = self.player_info['stream']
            data = self.player_info['data']
            
            # 오디오 데이터 스트림에 쓰기
            stream.write(data)
            
            # 스트림 종료
            stream.stop_stream()
            stream.close()
            
            # 재생 상태 업데이트
            self.is_playing = False
            
        except Exception as e:
            print(f"[!] 오디오 재생 스레드 오류: {e}")
            traceback.print_exc()
            
        finally:
            # 클린업
            if hasattr(self, 'player') and self.player:
                self.player.terminate()
            self.is_playing = False
    
    def stop_audio(self):
        """
        현재 재생 중인 오디오를 중지합니다.
        """
        if not self.is_playing:
            print("[*] 중지할 오디오가 없습니다.")
            return True
            
        print("[*] 오디오 재생을 중지합니다...")
        
        try:
            # VLC 플레이어인 경우
            import vlc
            if hasattr(self, 'player') and isinstance(self.player, vlc.MediaPlayer):
                try:
                    # 재생 중이면 먼저 중지
                    self.player.stop()
                    
                    # 현재 상태 확인
                    state = self.player.get_state()
                    if state != vlc.State.Stopped and state != vlc.State.NothingSpecial:
                        # 완전히 중지될 때까지 짧게 대기
                        time.sleep(0.1)
                    
                    # 미디어 객체 정리
                    media = self.player.get_media()
                    if media:
                        try:
                            media.release()
                        except Exception as e:
                            print(f"[!] 미디어 객체 해제 중 오류: {e}")
                            pass
                    
                    # 안전하게 플레이어 해제
                    try:
                        self.player.release()
                    except Exception as e:
                        print(f"[!] 플레이어 해제 중 오류: {e}")
                        # 오류 발생 시 대체 방법
                        if hasattr(self, 'player'):
                            self.player = None
                            
                    print("[*] VLC 오디오 재생이 중지되었습니다.")
                    
                except Exception as e:
                    print(f"[!] VLC 플레이어 중지 중 오류: {e}")
                    traceback.print_exc()
                    # 오류가 발생해도 플레이어 인스턴스는 해제
                    if hasattr(self, 'player'):
                        self.player = None
                
                # 재생 상태 업데이트
                self.is_playing = False
                return True
                
            # PyAudio 플레이어인 경우
            elif hasattr(self, 'player_info') and self.player_info:
                if 'stream' in self.player_info:
                    try:
                        # 스트림 닫기
                        self.player_info['stream'].stop_stream()
                        self.player_info['stream'].close()
                    except:
                        pass
                        
                # PyAudio 정리
                if hasattr(self, 'player'):
                    try:
                        self.player.terminate()
                    except:
                        pass
                        
                # 정보 정리
                self.player_info = None
                
                print("[*] PyAudio 오디오 재생이 중지되었습니다.")
                self.is_playing = False
                return True
                
            # 다른 타입의 플레이어
            elif hasattr(self, 'player'):
                print("[*] 알 수 없는 유형의 플레이어를 중지합니다.")
                del self.player
                self.is_playing = False
                return True
                
            else:
                print("[!] 플레이어 인스턴스를 찾을 수 없습니다.")
                self.is_playing = False
                return False
                
        except Exception as e:
            print(f"[!] 오디오 중지 중 오류 발생: {e}")
            traceback.print_exc()
            # 오류가 발생한 경우에도 재생 상태 초기화
            self.is_playing = False
            # 안전하게 플레이어 참조 제거
            if hasattr(self, 'player'):
                self.player = None
            if hasattr(self, 'player_info'):
                self.player_info = None
            return False
    
    def _monitor_vlc_playback(self):
        """
        VLC 재생 상태를 모니터링하는 스레드 함수
        """
        try:
            import vlc
            if not hasattr(self, 'player') or not isinstance(self.player, vlc.MediaPlayer):
                return
            
            # 오디오 재생이 끝날 때까지 모니터링
            while self.is_playing:
                # 현재 상태 확인
                try:
                    state = self.player.get_state()
                    
                    # 재생 완료 또는 중지 상태 확인
                    if state in [vlc.State.Ended, vlc.State.Stopped, vlc.State.Error]:
                        print(f"[*] VLC 재생 완료 감지 (상태: {state})")
                        self.playback_finished = True
                        # 재생 상태 업데이트만 하고 실제 stop_audio는 호출하지 않음
                        self.is_playing = False
                        break
                except Exception as e:
                    print(f"[!] VLC 상태 확인 중 오류: {e}")
                    # 오류 발생 시 대기 후 재시도
                    time.sleep(1)
                    continue
                
                # 일정 시간 대기
                time.sleep(0.5)
                
        except Exception as e:
            print(f"[!] VLC 모니터링 스레드 오류: {e}")
            traceback.print_exc()
            # 오류 발생 시 재생 중지로 간주
            self.playback_finished = True
            self.is_playing = False
    
    def _check_playback_finished(self):
        """
        재생 완료 여부를 확인합니다
        
        Returns:
        --------
        bool
            재생이 완료되었으면 True, 아니면 False
        """
        # VLC 재생 끝났는지 확인
        if hasattr(self, 'playback_finished') and self.playback_finished:
            return True
            
        # 재생 중 플래그 확인
        if not self.is_playing:
            return True
            
        # VLC 플레이어 상태 확인
        try:
            import vlc
            if hasattr(self, 'player') and isinstance(self.player, vlc.MediaPlayer):
                state = self.player.get_state()
                if state in [vlc.State.Ended, vlc.State.Stopped, vlc.State.Error]:
                    print(f"[*] 재생 완료 체크: VLC 상태 {state}")
                    return True
        except Exception as e:
            print(f"[!] VLC 상태 확인 중 오류: {e}")
            pass
            
        # PyAudio 플레이어 완료 체크
        if hasattr(self, 'player_info') and 'stream' in self.player_info:
            # 스트림 비활성화 여부 확인 (가능한 경우)
            pass
            
        # 아직 재생 중
        return False
    
    def broadcast_audio(self, audio_path, target_devices, end_devices=None, duration=None):
        """
        방송 실행 (오디오 파일)
        
        Parameters:
        -----------
        audio_path : str or Path
            재생할 오디오 파일 경로
        target_devices : list
            방송할 장치 목록
        end_devices : list
            방송 종료 후 끌 장치 목록 (None이면 target_devices와 동일)
        duration : int
            강제 종료 시간(초) (None이면 자동 감지)
            
        Returns:
        --------
        bool
            성공 여부
        """
        # 이미 방송 중인 경우 처리
        if self.broadcast_thread and self.broadcast_thread.is_alive():
            print("[!] 이미 방송이 실행 중입니다.")
            return False
        
        # 종료 시 끌 장치 목록이 지정되지 않았으면 시작 장치와 동일하게 설정
        if end_devices is None:
            end_devices = target_devices
        
        # 방송 실행을 위한 스레드 생성
        self.broadcast_thread = threading.Thread(
            target=self._broadcast_thread_func,
            args=(audio_path, target_devices, end_devices, duration),
            daemon=True
        )
        
        # 스레드 시작
        self.broadcast_thread.start()
        print(f"[*] 방송 시작: {len(target_devices)}개 장치, 오디오: {audio_path}")
        return True
    
    def _broadcast_thread_func(self, audio_path, target_devices, end_devices, duration):
        """
        방송 실행 스레드 함수
        """
        try:
            # end_devices가 None이면 target_devices로 설정
            if end_devices is None:
                end_devices = target_devices
                
            # end_devices가 단일 문자열인 경우 리스트로 변환
            if isinstance(end_devices, str):
                # "string" 값이 그대로 들어오는 경우 target_devices 사용
                if end_devices == "string":
                    end_devices = target_devices
                    print("[*] end_devices 'string' 값을 target_devices로 대체")
                else:
                    # 쉼표로 구분된 문자열인 경우 리스트로 분할
                    end_devices = [d.strip() for d in end_devices.split(",") if d.strip()]
                    print(f"[*] end_devices 문자열을 목록으로 변환: {end_devices}")
                    
            # 1. 대상 장치 활성화
            print(f"[*] 방송 장치 활성화 중: {', '.join(map(str, target_devices))}")
            success = self.control_multiple_devices(target_devices, state=1)
            if not success:
                print("[!] 장치 활성화 실패")
                return
            
            # 2. 장치 활성화 후 0.5초 대기 (1초에서 0.5초로 감소)
            print("[*] 장치 활성화 후 0.5초 대기...")
            time.sleep(0.5)  # 1초에서 0.5초로 변경
            
            # 3. 오디오 재생
            print(f"[*] 오디오 재생 시작: {audio_path}")
            success = self.play_audio(audio_path)
            if not success:
                print("[!] 오디오 재생 실패")
                # 장치 비활성화
                self.control_multiple_devices(end_devices, state=0)
                return
                
            print("[*] 오디오 재생 성공, 완료 대기 중...")
            
            # 4. 재생 완료 대기
            if duration:
                # 지정된 시간 동안 대기
                print(f"[*] 지정된 시간({duration}초) 동안 방송 진행 중...")
                time.sleep(duration)
                # 지정된 시간이 지나면 강제 중지
                self.stop_audio()
            else:
                # 재생 종료 감지 (최대 2분 타임아웃)
                print("[*] 오디오 재생 완료 대기 중...")
                max_wait = 120  # 최대 2분
                start_time = time.time()
                
                # 재생 완료 감지 또는 타임아웃 체크
                while not self._check_playback_finished():
                    time.sleep(0.5)
                    
                    # 주기적으로 상태 로그 출력
                    if int(time.time() - start_time) % 5 == 0:  # 5초마다 로그
                        print(f"[*] 재생 대기 중... 경과 시간: {int(time.time() - start_time)}초")
                    
                    # 타임아웃 체크
                    if time.time() - start_time > max_wait:
                        print("[!] 재생 완료 대기 타임아웃, 강제 종료합니다.")
                        break
                        
                # 재생 중지 (이미 완료되었더라도 안전하게 호출)
                self.stop_audio()
            
            # 5-1. 재생 종료 후 0.5초 대기 (1초에서 0.5초로 감소)
            print("[*] 재생 종료 후 0.5초 대기...")
            time.sleep(0.5)  # 1초에서 0.5초로 변경
            
            # 6. 방송 종료 후 장치 비활성화 - 예외 처리 추가
            try:
                # end_devices가 여전히 string이면 target_devices 사용
                if isinstance(end_devices, str):
                    end_devices = target_devices
                    print(f"[*] 종료 시 string 값이 감지되어 target_devices({', '.join(map(str, target_devices))})로 대체")
                
                print(f"[*] 방송 종료, 장치 비활성화 중: {', '.join(map(str, end_devices))}")
                self.control_multiple_devices(end_devices, state=0)
                print("[*] 장치 비활성화 완료")
            except Exception as e:
                print(f"[!] 장치 비활성화 중 오류: {e}")
                traceback.print_exc()
                # 오류 발생시 target_devices로 한번 더 시도
                try:
                    print(f"[*] 장치 비활성화 재시도 (target_devices 사용): {', '.join(map(str, target_devices))}")
                    self.control_multiple_devices(target_devices, state=0)
                except Exception as retry_error:
                    print(f"[!] 장치 비활성화 재시도 중 오류: {retry_error}")
            
            print("[*] 방송 프로세스 완료")
            
        except Exception as e:
            print(f"[!] 방송 스레드 실행 중 오류: {e}")
            traceback.print_exc()
            
            # 오류 발생 시 장치 비활성화 시도
            try:
                self.stop_audio()
                print(f"[*] 오류 복구: 장치 비활성화 시도...")
                # end_devices가 string이면 target_devices 사용
                if isinstance(end_devices, str):
                    end_devices = target_devices
                self.control_multiple_devices(end_devices, state=0)
            except Exception as cleanup_error:
                print(f"[!] 오류 복구 중 추가 오류 발생: {cleanup_error}")
    
    def broadcast_text(self, text, target_devices, end_devices=None, language="ko"):
        """
        텍스트 방송 실행 (TTS)
        
        Parameters:
        -----------
        text : str
            방송할 텍스트
        target_devices : list
            방송할 장치 목록
        end_devices : list
            방송 종료 후 끌 장치 목록 (None이면 target_devices와 동일)
        language : str
            텍스트 언어 (기본값: 한국어)
            
        Returns:
        --------
        bool
            성공 여부
        """
        # 1. TTS로 음성 생성
        print(f"[*] 텍스트를 음성으로 변환 중: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # TTS 서비스 초기화 (필요한 경우)
        if not hasattr(self, 'tts_service') or not self.tts_service:
            self.initialize_tts(language)
        
        # 언어 변경이 필요한 경우
        if language and hasattr(self, 'tts_language') and language != self.tts_language:
            self.initialize_tts(language)
        
        # 음성 생성
        audio_path = self.generate_speech(text, language=language)
        if not audio_path:
            print("[!] 음성 생성에 실패했습니다.")
            return False
        
        # 2. 생성된 오디오로 방송 실행
        return self.broadcast_audio(audio_path, target_devices, end_devices)
    
    def stop_broadcast(self):
        """
        현재 실행 중인 방송 중지
        
        Returns:
        --------
        bool
            성공 여부
        """
        try:
            # 오디오 재생 중지
            self.stop_audio()
            
            # 모든 장치 상태 초기화
            self.initialize_system_state()
            
            print("[*] 방송 강제 종료")
            return True
            
        except Exception as e:
            print(f"[!] 방송 중지 중 오류: {e}")
            return False

    def schedule_broadcast_text(self, schedule_time, text, target_devices, end_devices=None, language="ko"):
        """
        텍스트 방송 예약
        
        Parameters:
        -----------
        schedule_time : str
            방송 예약 시간 (예: "2023-10-25 13:30:00")
        text : str
            방송할 텍스트
        target_devices : list
            방송할 장치 목록
        end_devices : list
            방송 종료 후 끌 장치 목록 (None이면 target_devices와 동일)
        language : str
            텍스트 언어 (기본값: 한국어)
            
        Returns:
        --------
        str
            예약된 작업 ID (실패 시 None)
        """
        try:
            # 스케줄 시간 처리
            if isinstance(schedule_time, str):
                # 문자열 형식 확인 및 변환
                try:
                    schedule_time = datetime.datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    print(f"[!] 오류: 시간 형식이 잘못되었습니다. 'YYYY-MM-DD HH:MM:SS' 형식이어야 합니다.")
                    return None
            
            # 현재 시간보다 이전이면 오류
            if schedule_time < datetime.datetime.now():
                print(f"[!] 오류: 예약 시간이 현재 시간보다 이전입니다.")
                return None
                
            # 스케줄러가 없으면 초기화
            if not hasattr(self, '_broadcast_scheduler'):
                from apscheduler.schedulers.background import BackgroundScheduler
                self._broadcast_scheduler = BackgroundScheduler()
                self._broadcast_scheduler.start()
                print(f"[*] 방송 스케줄러가 시작되었습니다.")
            
            # 작업 ID 생성
            job_id = f"broadcast_text_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{id(text)}"
            
            # 스케줄 등록
            self._broadcast_scheduler.add_job(
                self.broadcast_text,
                'date',
                run_date=schedule_time,
                args=[text, target_devices, end_devices, language],
                id=job_id,
                name=f"TTS 방송: {text[:20]}{'...' if len(text) > 20 else ''}"
            )
            
            time_diff = schedule_time - datetime.datetime.now()
            hours, remainder = divmod(time_diff.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            print(f"[*] 방송이 예약되었습니다. ID: {job_id}")
            print(f"[*] 예약 시간: {schedule_time.strftime('%Y-%m-%d %H:%M:%S')} ({int(hours)}시간 {int(minutes)}분 {int(seconds)}초 후)")
            
            return job_id
            
        except Exception as e:
            print(f"[!] 방송 예약 중 오류: {e}")
            traceback.print_exc()
            return None
            
    def schedule_broadcast_audio(self, schedule_time, audio_path, target_devices, end_devices=None, duration=None):
        """
        오디오 방송 예약
        
        Parameters:
        -----------
        schedule_time : str
            방송 예약 시간 (예: "2023-10-25 13:30:00")
        audio_path : str or Path
            재생할 오디오 파일 경로
        target_devices : list
            방송할 장치 목록
        end_devices : list
            방송 종료 후 끌 장치 목록 (None이면 target_devices와 동일)
        duration : int
            강제 종료 시간(초) (None이면 자동 감지)
            
        Returns:
        --------
        str
            예약된 작업 ID (실패 시 None)
        """
        try:
            # 스케줄 시간 처리
            if isinstance(schedule_time, str):
                # 문자열 형식 확인 및 변환
                try:
                    schedule_time = datetime.datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    print(f"[!] 오류: 시간 형식이 잘못되었습니다. 'YYYY-MM-DD HH:MM:SS' 형식이어야 합니다.")
                    return None
            
            # 현재 시간보다 이전이면 오류
            if schedule_time < datetime.datetime.now():
                print(f"[!] 오류: 예약 시간이 현재 시간보다 이전입니다.")
                return None
                
            # 오디오 파일 존재 확인
            audio_path = Path(audio_path)
            if not audio_path.exists():
                print(f"[!] 오류: 오디오 파일이 존재하지 않습니다: {audio_path}")
                return None
                
            # 스케줄러가 없으면 초기화
            if not hasattr(self, '_broadcast_scheduler'):
                from apscheduler.schedulers.background import BackgroundScheduler
                self._broadcast_scheduler = BackgroundScheduler()
                self._broadcast_scheduler.start()
                print(f"[*] 방송 스케줄러가 시작되었습니다.")
            
            # 작업 ID 생성
            job_id = f"broadcast_audio_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{audio_path.name}"
            
            # 스케줄 등록
            self._broadcast_scheduler.add_job(
                self.broadcast_audio,
                'date',
                run_date=schedule_time,
                args=[audio_path, target_devices, end_devices, duration],
                id=job_id,
                name=f"오디오 방송: {audio_path.name}"
            )
            
            time_diff = schedule_time - datetime.datetime.now()
            hours, remainder = divmod(time_diff.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            print(f"[*] 방송이 예약되었습니다. ID: {job_id}")
            print(f"[*] 예약 시간: {schedule_time.strftime('%Y-%m-%d %H:%M:%S')} ({int(hours)}시간 {int(minutes)}분 {int(seconds)}초 후)")
            
            return job_id
            
        except Exception as e:
            print(f"[!] 방송 예약 중 오류: {e}")
            traceback.print_exc()
            return None
            
    def get_scheduled_broadcasts(self):
        """
        예약된 방송 목록 조회
        
        Returns:
        --------
        list
            예약된 방송 정보 목록
        """
        try:
            if not hasattr(self, '_broadcast_scheduler'):
                return []
                
            scheduled_jobs = []
            for job in self._broadcast_scheduler.get_jobs():
                scheduled_jobs.append({
                    "job_id": job.id,
                    "name": job.name,
                    "run_time": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "remaining": str(job.next_run_time - datetime.datetime.now()).split('.')[0]
                })
                
            return scheduled_jobs
            
        except Exception as e:
            print(f"[!] 예약 방송 목록 조회 중 오류: {e}")
            traceback.print_exc()
            return []
            
    def cancel_scheduled_broadcast(self, job_id):
        """
        예약된 방송 취소
        
        Parameters:
        -----------
        job_id : str
            취소할 작업 ID
            
        Returns:
        --------
        bool
            성공 여부
        """
        try:
            if not hasattr(self, '_broadcast_scheduler'):
                print(f"[!] 오류: 방송 스케줄러가 초기화되지 않았습니다.")
                return False
                
            job = self._broadcast_scheduler.get_job(job_id)
            if not job:
                print(f"[!] 오류: 해당 ID({job_id})의 예약 방송이 존재하지 않습니다.")
                return False
                
            self._broadcast_scheduler.remove_job(job_id)
            print(f"[*] 예약 방송이 취소되었습니다. ID: {job_id}")
            return True
            
        except Exception as e:
            print(f"[!] 예약 방송 취소 중 오류: {e}")
            traceback.print_exc()
            return False

    def play_audio_with_end_devices(self, audio_path, end_devices=None):
        """
        이미 활성화된 장치에 오디오를 재생하고 종료 시 지정된 장치를 끕니다.
        
        Parameters:
        -----------
        audio_path : str or Path
            재생할 오디오 파일 경로
        end_devices : list
            방송 종료 후 끌 장치 목록
            
        Returns:
        --------
        bool
            성공 여부
        """
        # 이미 방송 중인 경우 처리
        if self.broadcast_thread and self.broadcast_thread.is_alive():
            print("[!] 이미 방송이 실행 중입니다.")
            return False
        
        # 방송 실행을 위한 스레드 생성 (장치 활성화 단계 생략)
        self.broadcast_thread = threading.Thread(
            target=self._broadcast_thread_with_end_devices,
            args=(audio_path, end_devices),
            daemon=True
        )
        
        # 스레드 시작
        self.broadcast_thread.start()
        print(f"[*] 방송 시작 (장치는 이미 활성화됨), 오디오: {audio_path}")
        return True
    
    def _broadcast_thread_with_end_devices(self, audio_path, end_devices):
        """
        방송 실행 스레드 함수 (장치 활성화 단계 생략 버전)
        """
        try:
            # end_devices 체크
            if not end_devices:
                print("[!] 종료 시 끌 장치가 지정되지 않았습니다.")
                end_devices = []
                
            # end_devices가 단일 문자열인 경우 리스트로 변환
            if isinstance(end_devices, str):
                # 쉼표로 구분된 문자열인 경우 리스트로 분할
                end_devices = [d.strip() for d in end_devices.split(",") if d.strip()]
                print(f"[*] end_devices 문자열을 목록으로 변환: {end_devices}")
            
            # 1. 오디오 재생 (장치는 이미 활성화되어 있다고 가정)
            print(f"[*] 오디오 재생 시작: {audio_path}")
            success = self.play_audio(audio_path)
            if not success:
                print("[!] 오디오 재생 실패")
                return
            
            # 2. 재생 완료 대기
            print("[*] 오디오 재생 완료 대기 중...")
            max_wait = 120  # 최대 2분
            start_time = time.time()
            
            # 재생 완료 감지 또는 타임아웃 체크
            while not self._check_playback_finished():
                time.sleep(0.5)
                
                # 주기적으로 상태 로그 출력
                if int(time.time() - start_time) % 5 == 0:  # 5초마다 로그
                    print(f"[*] 재생 대기 중... 경과 시간: {int(time.time() - start_time)}초")
                
                # 타임아웃 체크
                if time.time() - start_time > max_wait:
                    print("[!] 재생 완료 대기 타임아웃, 강제 종료합니다.")
                    break
                    
            # 3. 재생 중지 (이미 완료되었더라도 안전하게 호출)
            self.stop_audio()
            
            # 4. 재생 종료 후 0.5초 대기
            print("[*] 재생 종료 후 0.5초 대기...")
            time.sleep(0.5)
            
            # 5. 방송 종료 후 장치 비활성화
            if end_devices:
                try:
                    print(f"[*] 방송 종료, 장치 비활성화 중: {', '.join(map(str, end_devices))}")
                    self.control_multiple_devices(end_devices, state=0)
                    print("[*] 장치 비활성화 완료")
                except Exception as e:
                    print(f"[!] 장치 비활성화 중 오류: {e}")
                    traceback.print_exc()
            else:
                print("[*] end_devices가 지정되지 않아 장치 비활성화를 건너뜁니다.")
            
            print("[*] 방송 프로세스 완료")
            
        except Exception as e:
            print(f"[!] 방송 스레드 실행 중 오류: {e}")
            traceback.print_exc()
            
            # 오류 발생 시 장치 비활성화 시도
            if end_devices:
                try:
                    self.control_multiple_devices(end_devices, state=0)
                except Exception as cleanup_error:
                    print(f"[!] 오류 복구 중 추가 오류 발생: {cleanup_error}")
    
    def schedule_broadcast_text_with_positions(self, schedule_time, text, matrix_positions, target_devices, end_devices=None, language="ko"):
        """
        행/열 좌표 정보를 포함한 텍스트 방송 예약
        
        Parameters:
        -----------
        schedule_time : str
            방송 예약 시간 (예: "2023-10-25 13:30:00")
        text : str
            방송할 텍스트
        matrix_positions : list
            방송할 장치의 행/열 좌표 목록 [(row1, col1), (row2, col2), ...]
        target_devices : list
            방송할 장치명 목록 (좌표에 해당하는 장치명들)
        end_devices : list
            방송 종료 후 끌 장치 목록 (None이면 target_devices와 동일)
        language : str
            텍스트 언어 (기본값: 한국어)
            
        Returns:
        --------
        str
            예약된 작업 ID (실패 시 None)
        """
        try:
            # 스케줄 시간 처리
            if isinstance(schedule_time, str):
                # 문자열 형식 확인 및 변환
                try:
                    schedule_time = datetime.datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    print(f"[!] 오류: 시간 형식이 잘못되었습니다. 'YYYY-MM-DD HH:MM:SS' 형식이어야 합니다.")
                    return None
            
            # 현재 시간보다 이전이면 오류
            if schedule_time < datetime.datetime.now():
                print(f"[!] 오류: 예약 시간이 현재 시간보다 이전입니다.")
                return None
                
            # 스케줄러가 없으면 초기화
            if not hasattr(self, '_broadcast_scheduler'):
                from apscheduler.schedulers.background import BackgroundScheduler
                self._broadcast_scheduler = BackgroundScheduler()
                self._broadcast_scheduler.start()
                print(f"[*] 방송 스케줄러가 시작되었습니다.")
            
            # 작업 ID 생성
            job_id = f"broadcast_text_matrix_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{id(text)}"
            
            # 오디오 생성 실행 (미리 생성하여 저장)
            audio_path = self.generate_speech(text, language=language)
            if not audio_path:
                print(f"[!] 오류: 텍스트를 음성으로 변환하지 못했습니다.")
                return None
            
            # 실행할 함수 정의 (익명 함수 대신 표준 함수 사용)
            def execute_matrix_broadcast(audio_path, matrix_positions, target_devices, end_devices, language):
                try:
                    print(f"[*] 예약된 방송 시작: {audio_path}")
                    
                    # 필요한 모듈 임포트
                    from ..core.device_mapping import DeviceMapper
                    from .packet_builder import packet_builder
                    from .network import network_manager
                    
                    device_mapper = DeviceMapper()
                    
                    # 1. 좌표 기반으로 장치 활성화
                    activation_success = True
                    for row, col in matrix_positions:
                        try:
                            # 행/열로부터 바이트와 비트 위치 계산
                            byte_pos, bit_pos = device_mapper.get_byte_bit_position(row, col)
                            print(f"[*] 행/열 ({row},{col}) -> 바이트: {byte_pos}, 비트: {bit_pos}")
                            
                            # 패킷 생성 및 전송 (상태 1 = 켜기)
                            payload = packet_builder.create_byte_bit_payload(byte_pos, bit_pos, state=1)
                            
                            if payload is None:
                                print(f"[!] 행/열 ({row},{col})에 대한 패킷 생성 실패")
                                activation_success = False
                                continue
                            
                            # 패킷 전송
                            send_success, _ = network_manager.send_payload(payload)
                            if not send_success:
                                print(f"[!] 행/열 ({row},{col})에 대한 신호 전송 실패")
                                activation_success = False
                        except Exception as e:
                            print(f"[!] 행/열 ({row},{col}) 처리 중 오류: {e}")
                            activation_success = False
                    
                    if not activation_success:
                        print("[!] 일부 좌표에 대한 신호 전송이 실패했습니다.")
                    
                    # 2. 장치 활성화 후 0.5초 대기
                    time.sleep(0.5)
                    
                    # 3. 오디오 재생
                    print(f"[*] 오디오 재생 시작: {audio_path}")
                    success = self.play_audio(audio_path)
                    if not success:
                        print("[!] 오디오 재생 실패")
                        # 장치 비활성화
                        for row, col in matrix_positions:
                            try:
                                byte_pos, bit_pos = device_mapper.get_byte_bit_position(row, col)
                                payload = packet_builder.create_byte_bit_payload(byte_pos, bit_pos, state=0)
                                if payload:
                                    network_manager.send_payload(payload)
                            except Exception as e:
                                print(f"[!] 장치 비활성화 중 오류: {e}")
                        return
                    
                    # 4. 재생 완료 대기
                    max_wait = 120  # 최대 2분
                    start_time = time.time()
                    
                    # 재생 완료 감지 또는 타임아웃 체크
                    while not self._check_playback_finished():
                        time.sleep(0.5)
                        
                        # 타임아웃 체크
                        if time.time() - start_time > max_wait:
                            print("[!] 재생 완료 대기 타임아웃, 강제 종료합니다.")
                            break
                    
                    # 5. 재생 중지 (이미 완료되었더라도 안전하게 호출)
                    self.stop_audio()
                    
                    # 6. 재생 종료 후 0.5초 대기
                    time.sleep(0.5)
                    
                    # 7. 종료 후 장치 비활성화
                    print(f"[*] 방송 종료, 장치 비활성화 중...")
                    # 먼저 좌표 기반으로 비활성화
                    for row, col in matrix_positions:
                        try:
                            byte_pos, bit_pos = device_mapper.get_byte_bit_position(row, col)
                            payload = packet_builder.create_byte_bit_payload(byte_pos, bit_pos, state=0)
                            if payload:
                                network_manager.send_payload(payload)
                                print(f"[*] 행/열 ({row},{col}) 비활성화 완료")
                        except Exception as e:
                            print(f"[!] 행/열 ({row},{col}) 비활성화 중 오류: {e}")
                    
                    # 추가로 end_devices가 지정된 경우 이를 통해서도 비활성화 
                    if end_devices:
                        try:
                            print(f"[*] 종료 장치 목록 비활성화 중: {', '.join(map(str, end_devices))}")
                            self.control_multiple_devices(end_devices, state=0)
                        except Exception as e:
                            print(f"[!] 종료 장치 비활성화 중 오류: {e}")
                    
                    print("[*] 예약 방송 실행 완료")
                except Exception as e:
                    print(f"[!] 예약 방송 실행 중 오류: {e}")
                    traceback.print_exc()
                    
                    # 오류 발생 시 장치 비활성화 시도
                    try:
                        # 좌표 기반 비활성화
                        for row, col in matrix_positions:
                            try:
                                byte_pos, bit_pos = device_mapper.get_byte_bit_position(row, col)
                                payload = packet_builder.create_byte_bit_payload(byte_pos, bit_pos, state=0)
                                if payload:
                                    network_manager.send_payload(payload)
                            except:
                                pass
                        
                        # 장치명 기반 비활성화도 추가로 시도
                        if target_devices:
                            self.control_multiple_devices(target_devices, state=0)
                    except:
                        pass
            
            # 스케줄 등록
            self._broadcast_scheduler.add_job(
                execute_matrix_broadcast,
                'date',
                run_date=schedule_time,
                args=[audio_path, matrix_positions, target_devices, end_devices, language],
                id=job_id,
                name=f"TTS 행렬 방송: {text[:20]}{'...' if len(text) > 20 else ''}"
            )
            
            time_diff = schedule_time - datetime.datetime.now()
            hours, remainder = divmod(time_diff.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            print(f"[*] 행렬 방송이 예약되었습니다. ID: {job_id}")
            print(f"[*] 예약 시간: {schedule_time.strftime('%Y-%m-%d %H:%M:%S')} ({int(hours)}시간 {int(minutes)}분 {int(seconds)}초 후)")
            print(f"[*] 대상 좌표: {', '.join([f'({row},{col})' for row, col in matrix_positions])}")
            
            return job_id
            
        except Exception as e:
            print(f"[!] 행렬 방송 예약 중 오류: {e}")
            traceback.print_exc()
            return None
    
    def _broadcast_thread_with_end_devices(self, audio_path, end_devices):
        """
        방송 실행 스레드 함수 (장치 활성화 단계 생략 버전)
        """
        try:
            # end_devices 체크
            if not end_devices:
                print("[!] 종료 시 끌 장치가 지정되지 않았습니다.")
                end_devices = []
                
            # end_devices가 단일 문자열인 경우 리스트로 변환
            if isinstance(end_devices, str):
                # 쉼표로 구분된 문자열인 경우 리스트로 분할
                end_devices = [d.strip() for d in end_devices.split(",") if d.strip()]
                print(f"[*] end_devices 문자열을 목록으로 변환: {end_devices}")
            
            # 1. 오디오 재생 (장치는 이미 활성화되어 있다고 가정)
            print(f"[*] 오디오 재생 시작: {audio_path}")
            success = self.play_audio(audio_path)
            if not success:
                print("[!] 오디오 재생 실패")
                return
            
            # 2. 재생 완료 대기
            print("[*] 오디오 재생 완료 대기 중...")
            max_wait = 120  # 최대 2분
            start_time = time.time()
            
            # 재생 완료 감지 또는 타임아웃 체크
            while not self._check_playback_finished():
                time.sleep(0.5)
                
                # 주기적으로 상태 로그 출력
                if int(time.time() - start_time) % 5 == 0:  # 5초마다 로그
                    print(f"[*] 재생 대기 중... 경과 시간: {int(time.time() - start_time)}초")
                
                # 타임아웃 체크
                if time.time() - start_time > max_wait:
                    print("[!] 재생 완료 대기 타임아웃, 강제 종료합니다.")
                    break
                    
            # 3. 재생 중지 (이미 완료되었더라도 안전하게 호출)
            self.stop_audio()
            
            # 4. 재생 종료 후 0.5초 대기
            print("[*] 재생 종료 후 0.5초 대기...")
            time.sleep(0.5)
            
            # 5. 방송 종료 후 장치 비활성화
            if end_devices:
                try:
                    print(f"[*] 방송 종료, 장치 비활성화 중: {', '.join(map(str, end_devices))}")
                    self.control_multiple_devices(end_devices, state=0)
                    print("[*] 장치 비활성화 완료")
                except Exception as e:
                    print(f"[!] 장치 비활성화 중 오류: {e}")
                    traceback.print_exc()
            else:
                print("[*] end_devices가 지정되지 않아 장치 비활성화를 건너뜁니다.")
            
            print("[*] 방송 프로세스 완료")
            
        except Exception as e:
            print(f"[!] 방송 스레드 실행 중 오류: {e}")
            traceback.print_exc()
            
            # 오류 발생 시 장치 비활성화 시도
            if end_devices:
                try:
                    self.control_multiple_devices(end_devices, state=0)
                except Exception as cleanup_error:
                    print(f"[!] 오류 복구 중 추가 오류 발생: {cleanup_error}")
    
    def schedule_broadcast_audio_with_positions(self, schedule_time, audio_path, matrix_positions, target_devices, end_devices=None, duration=None):
        """
        행/열 좌표 정보를 포함한 오디오 방송 예약
        
        Parameters:
        -----------
        schedule_time : str
            방송 예약 시간 (예: "2023-10-25 13:30:00")
        audio_path : str or Path
            재생할 오디오 파일 경로
        matrix_positions : list
            방송할 장치의 행/열 좌표 목록 [(row1, col1), (row2, col2), ...]
        target_devices : list
            방송할 장치명 목록 (좌표에 해당하는 장치명들)
        end_devices : list
            방송 종료 후 끌 장치 목록 (None이면 target_devices와 동일)
        duration : int
            강제 종료 시간(초) (None이면 자동 감지)
            
        Returns:
        --------
        str
            예약된 작업 ID (실패 시 None)
        """
        try:
            # 스케줄 시간 처리
            if isinstance(schedule_time, str):
                # 문자열 형식 확인 및 변환
                try:
                    schedule_time = datetime.datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    print(f"[!] 오류: 시간 형식이 잘못되었습니다. 'YYYY-MM-DD HH:MM:SS' 형식이어야 합니다.")
                    return None
            
            # 현재 시간보다 이전이면 오류
            if schedule_time < datetime.datetime.now():
                print(f"[!] 오류: 예약 시간이 현재 시간보다 이전입니다.")
                return None
                
            # 오디오 파일 존재 확인
            audio_path = Path(audio_path)
            if not audio_path.exists():
                print(f"[!] 오류: 오디오 파일이 존재하지 않습니다: {audio_path}")
                return None
                
            # 스케줄러가 없으면 초기화
            if not hasattr(self, '_broadcast_scheduler'):
                from apscheduler.schedulers.background import BackgroundScheduler
                self._broadcast_scheduler = BackgroundScheduler()
                self._broadcast_scheduler.start()
                print(f"[*] 방송 스케줄러가 시작되었습니다.")
            
            # 작업 ID 생성
            job_id = f"broadcast_audio_matrix_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{audio_path.name}"
            
            # 실행할 함수 정의
            def execute_matrix_audio_broadcast(audio_path, matrix_positions, target_devices, end_devices, duration):
                try:
                    print(f"[*] 예약된 오디오 방송 시작: {audio_path}")
                    
                    # 필요한 모듈 임포트
                    from ..core.device_mapping import DeviceMapper
                    from .packet_builder import packet_builder
                    from .network import network_manager
                    
                    device_mapper = DeviceMapper()
                    
                    # 1. 좌표 기반으로 장치 활성화
                    activation_success = True
                    for row, col in matrix_positions:
                        try:
                            # 행/열로부터 바이트와 비트 위치 계산
                            byte_pos, bit_pos = device_mapper.get_byte_bit_position(row, col)
                            print(f"[*] 행/열 ({row},{col}) -> 바이트: {byte_pos}, 비트: {bit_pos}")
                            
                            # 패킷 생성 및 전송 (상태 1 = 켜기)
                            payload = packet_builder.create_byte_bit_payload(byte_pos, bit_pos, state=1)
                            
                            if payload is None:
                                print(f"[!] 행/열 ({row},{col})에 대한 패킷 생성 실패")
                                activation_success = False
                                continue
                            
                            # 패킷 전송
                            send_success, _ = network_manager.send_payload(payload)
                            if not send_success:
                                print(f"[!] 행/열 ({row},{col})에 대한 신호 전송 실패")
                                activation_success = False
                        except Exception as e:
                            print(f"[!] 행/열 ({row},{col}) 처리 중 오류: {e}")
                            activation_success = False
                    
                    if not activation_success:
                        print("[!] 일부 좌표에 대한 신호 전송이 실패했습니다.")
                    
                    # 2. 장치 활성화 후 0.5초 대기
                    time.sleep(0.5)
                    
                    # 3. 오디오 재생
                    print(f"[*] 오디오 재생 시작: {audio_path}")
                    success = self.play_audio(audio_path)
                    if not success:
                        print("[!] 오디오 재생 실패")
                        # 장치 비활성화
                        for row, col in matrix_positions:
                            try:
                                byte_pos, bit_pos = device_mapper.get_byte_bit_position(row, col)
                                payload = packet_builder.create_byte_bit_payload(byte_pos, bit_pos, state=0)
                                if payload:
                                    network_manager.send_payload(payload)
                            except Exception as e:
                                print(f"[!] 장치 비활성화 중 오류: {e}")
                        return
                    
                    # 4. 재생 완료 대기
                    if duration:
                        # 지정된 시간 동안 대기
                        print(f"[*] 지정된 시간({duration}초) 동안 방송 진행 중...")
                        time.sleep(duration)
                        # 지정된 시간이 지나면 강제 중지
                        self.stop_audio()
                    else:
                        # 재생 종료 감지 (최대 2분 타임아웃)
                        print("[*] 오디오 재생 완료 대기 중...")
                        max_wait = 120  # 최대 2분
                        start_time = time.time()
                        
                        # 재생 완료 감지 또는 타임아웃 체크
                        while not self._check_playback_finished():
                            time.sleep(0.5)
                            
                            # 타임아웃 체크
                            if time.time() - start_time > max_wait:
                                print("[!] 재생 완료 대기 타임아웃, 강제 종료합니다.")
                                break
                        
                        # 재생 중지 (이미 완료되었더라도 안전하게 호출)
                        self.stop_audio()
                    
                    # 5. 재생 종료 후 0.5초 대기
                    print("[*] 재생 종료 후 0.5초 대기...")
                    time.sleep(0.5)
                    
                    # 6. 종료 후 장치 비활성화
                    print(f"[*] 방송 종료, 장치 비활성화 중...")
                    # 먼저 좌표 기반으로 비활성화
                    for row, col in matrix_positions:
                        try:
                            byte_pos, bit_pos = device_mapper.get_byte_bit_position(row, col)
                            payload = packet_builder.create_byte_bit_payload(byte_pos, bit_pos, state=0)
                            if payload:
                                network_manager.send_payload(payload)
                                print(f"[*] 행/열 ({row},{col}) 비활성화 완료")
                        except Exception as e:
                            print(f"[!] 행/열 ({row},{col}) 비활성화 중 오류: {e}")
                    
                    # 추가로 end_devices가 지정된 경우 이를 통해서도 비활성화 
                    if end_devices:
                        try:
                            print(f"[*] 종료 장치 목록 비활성화 중: {', '.join(map(str, end_devices))}")
                            self.control_multiple_devices(end_devices, state=0)
                        except Exception as e:
                            print(f"[!] 종료 장치 비활성화 중 오류: {e}")
                    
                    print("[*] 예약 방송 실행 완료")
                except Exception as e:
                    print(f"[!] 예약 방송 실행 중 오류: {e}")
                    traceback.print_exc()
                    
                    # 오류 발생 시 장치 비활성화 시도
                    try:
                        # 좌표 기반 비활성화
                        for row, col in matrix_positions:
                            try:
                                byte_pos, bit_pos = device_mapper.get_byte_bit_position(row, col)
                                payload = packet_builder.create_byte_bit_payload(byte_pos, bit_pos, state=0)
                                if payload:
                                    network_manager.send_payload(payload)
                            except:
                                pass
                        
                        # 장치명 기반 비활성화도 추가로 시도
                        if target_devices:
                            self.control_multiple_devices(target_devices, state=0)
                    except:
                        pass
            
            # 스케줄 등록
            self._broadcast_scheduler.add_job(
                execute_matrix_audio_broadcast,
                'date',
                run_date=schedule_time,
                args=[audio_path, matrix_positions, target_devices, end_devices, duration],
                id=job_id,
                name=f"오디오 행렬 방송: {audio_path.name}"
            )
            
            time_diff = schedule_time - datetime.datetime.now()
            hours, remainder = divmod(time_diff.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            print(f"[*] 행렬 오디오 방송이 예약되었습니다. ID: {job_id}")
            print(f"[*] 예약 시간: {schedule_time.strftime('%Y-%m-%d %H:%M:%S')} ({int(hours)}시간 {int(minutes)}분 {int(seconds)}초 후)")
            print(f"[*] 대상 좌표: {', '.join([f'({row},{col})' for row, col in matrix_positions])}")
            
            return job_id
            
        except Exception as e:
            print(f"[!] 행렬 오디오 방송 예약 중 오류: {e}")
            traceback.print_exc()
            return None

# 싱글톤 인스턴스 생성
broadcast_controller = BroadcastController() 
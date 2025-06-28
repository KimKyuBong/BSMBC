#!/usr/bin/env python3
"""
통합 방송 관리자 서비스
네트워크를 통한 장치 상태 관리와 실제 패킷 전송을 통합하여 관리합니다.
"""

import logging
from typing import Set, Dict, Any, Tuple, Optional, List
from .network import NetworkManager
from ..models.device import DeviceStatus
import time

# 로거 설정
logger = logging.getLogger(__name__)

class BroadcastManager:
    """
    통합 방송 관리자
    네트워크를 통한 장치 상태 관리와 패킷 전송을 통합하여 관리합니다.
    """
    
    def __init__(self, target_ip="192.168.0.200", target_port=22000):
        """
        통합 방송 관리자 초기화
        
        Args:
            target_ip (str): 대상 서버 IP
            target_port (int): 대상 서버 포트
        """
        # 네트워크 관리자 초기화
        self.network_manager = NetworkManager(target_ip, target_port)
        
        # 장치 상태 관리 (메모리 상에서 관리)
        self.device_matrix = {}  # {(row, col): DeviceStatus}
        self.active_rooms = set()  # 활성화된 방 번호 집합
        
        # 통계
        self.packet_sent_count = 0
        
        # 매트릭스 초기화 (4행 16열)
        self._initialize_device_matrix()
        
        logger.info(f"통합 방송 관리자 초기화 완료 - 대상: {target_ip}:{target_port}")
    
    def _initialize_device_matrix(self):
        """장치 매트릭스 초기화"""
        for row in range(1, 5):  # 1~4행
            for col in range(1, 17):  # 1~16열
                self.device_matrix[(row, col)] = DeviceStatus.OFF
        logger.info("장치 매트릭스 초기화 완료 (4행 16열)")
    
    def _room_to_coordinates(self, room_id: int) -> Tuple[int, int]:
        """방 번호를 좌표로 변환 (예: 312 -> (3, 12))"""
        row = room_id // 100
        col = room_id % 100
        return row, col
    
    def _coordinates_to_room(self, row: int, col: int) -> int:
        """좌표를 방 번호로 변환 (예: (3, 12) -> 312)"""
        return row * 100 + col
    
    def _validate_coordinates(self, row: int, col: int) -> bool:
        """좌표 유효성 검사"""
        return 1 <= row <= 4 and 1 <= col <= 16
    
    def turn_on_device(self, row: int, col: int) -> bool:
        """
        개별 장치를 켜고 실제 패킷을 전송합니다.
        """
        if not self._validate_coordinates(row, col):
            logger.error(f"잘못된 좌표: ({row}, {col})")
            return False
        
        logger.info(f"장치 켜기 + 패킷 전송: ({row}, {col})")
        
        # 이전 상태 백업
        previous_active = self.active_rooms.copy()
        
        try:
            # 1. 내부 상태 업데이트
            room_id = self._coordinates_to_room(row, col)
            self.device_matrix[(row, col)] = DeviceStatus.ON
            self.active_rooms.add(room_id)
            
            # 2. 현재 활성화된 모든 방들의 상태로 패킷 전송
            success, response = self.network_manager.send_current_state_packet(self.active_rooms)
            
            if success:
                self.packet_sent_count += 1
                logger.info(f"패킷 전송 성공: {sorted(self.active_rooms)} (총 {len(self.active_rooms)}개 방)")
                if response:
                    logger.info(f"서버 응답: {response.hex()}")
                return True
            else:
                # 패킷 전송 실패 시 이전 상태로 롤백
                self.device_matrix[(row, col)] = DeviceStatus.OFF
                self.active_rooms = previous_active
                logger.error(f"패킷 전송 실패 - 상태 롤백")
                return False
            
        except Exception as e:
            logger.error(f"장치 켜기 오류: {e}")
            # 오류 발생 시 이전 상태로 롤백
            self.device_matrix[(row, col)] = DeviceStatus.OFF
            self.active_rooms = previous_active
            return False
    
    def turn_off_device(self, row: int, col: int) -> bool:
        """
        개별 장치를 끄고 실제 패킷을 전송합니다.
        """
        if not self._validate_coordinates(row, col):
            logger.error(f"잘못된 좌표: ({row}, {col})")
            return False
        
        logger.info(f"장치 끄기 + 패킷 전송: ({row}, {col})")
        
        # 이전 상태 백업
        previous_active = self.active_rooms.copy()
        previous_status = self.device_matrix[(row, col)]
        
        try:
            # 1. 내부 상태 업데이트
            room_id = self._coordinates_to_room(row, col)
            self.device_matrix[(row, col)] = DeviceStatus.OFF
            self.active_rooms.discard(room_id)
            
            # 2. 현재 활성화된 모든 방들의 상태로 패킷 전송
            success, response = self.network_manager.send_current_state_packet(self.active_rooms)
            
            if success:
                self.packet_sent_count += 1
                logger.info(f"패킷 전송 성공: {sorted(self.active_rooms)} (총 {len(self.active_rooms)}개 방)")
                if response:
                    logger.info(f"서버 응답: {response.hex()}")
                return True
            else:
                # 패킷 전송 실패 시 이전 상태로 롤백
                self.device_matrix[(row, col)] = previous_status
                self.active_rooms = previous_active
                logger.error(f"패킷 전송 실패 - 상태 롤백")
                return False
            
        except Exception as e:
            logger.error(f"장치 끄기 오류: {e}")
            # 오류 발생 시 이전 상태로 롤백
            self.device_matrix[(row, col)] = previous_status
            self.active_rooms = previous_active
            return False
    
    def set_active_rooms(self, active_rooms: Set[int]) -> bool:
        """
        방 번호 기반 다중 장치 제어 + 실제 패킷 전송
        """
        logger.info(f"방 번호 기반 제어 + 패킷 전송: {active_rooms}")
        
        # 이전 상태 백업
        previous_active = self.active_rooms.copy()
        previous_matrix = self.device_matrix.copy()
        
        try:
            # 1. 모든 장치를 일단 OFF로 설정
            for row in range(1, 5):
                for col in range(1, 17):
                    self.device_matrix[(row, col)] = DeviceStatus.OFF
            
            # 2. 활성화할 방들만 ON으로 설정
            self.active_rooms = set()
            for room_id in active_rooms:
                row, col = self._room_to_coordinates(room_id)
                if self._validate_coordinates(row, col):
                    self.device_matrix[(row, col)] = DeviceStatus.ON
                    self.active_rooms.add(room_id)
                else:
                    logger.warning(f"잘못된 방 번호 무시: {room_id}")
            
            # 3. 실제 패킷 전송
            success, response = self.network_manager.send_current_state_packet(self.active_rooms)
            
            if success:
                self.packet_sent_count += 1
                logger.info(f"패킷 전송 성공: {sorted(self.active_rooms)} (총 {len(self.active_rooms)}개 방)")
                if response:
                    logger.info(f"서버 응답: {response.hex()}")
                return True
            else:
                # 패킷 전송 실패 시 이전 상태로 롤백
                self.device_matrix = previous_matrix
                self.active_rooms = previous_active
                logger.error(f"패킷 전송 실패 - 상태 롤백")
                return False
            
        except Exception as e:
            logger.error(f"다중 장치 제어 오류: {e}")
            # 오류 발생 시 이전 상태로 롤백
            self.device_matrix = previous_matrix
            self.active_rooms = previous_active
            return False
    
    def turn_off_all_devices(self) -> bool:
        """
        모든 장치 끄기 + 실제 패킷 전송
        """
        logger.info("모든 장치 끄기 + 패킷 전송")
        print("[*] BroadcastManager: 모든 장치 끄기 시작")
        
        # 이전 상태 백업
        previous_active = self.active_rooms.copy()
        previous_matrix = self.device_matrix.copy()
        
        print(f"[*] BroadcastManager: 이전 상태 - 활성 방: {sorted(previous_active)}")
        print(f"[*] BroadcastManager: 이전 상태 - 활성 장치 수: {sum(1 for status in previous_matrix.values() if status == DeviceStatus.ON)}")
        
        try:
            # 1. 내부 상태 업데이트 (모든 장치 OFF)
            print("[*] BroadcastManager: 내부 상태 업데이트 (모든 장치 OFF)")
            for row in range(1, 5):
                for col in range(1, 17):
                    self.device_matrix[(row, col)] = DeviceStatus.OFF
            self.active_rooms.clear()
            print("[*] BroadcastManager: 내부 상태 업데이트 완료")
            
            # 상태 확인
            print("[*] BroadcastManager: 업데이트 후 상태 확인")
            active_count_after_update = sum(1 for status in self.device_matrix.values() if status == DeviceStatus.ON)
            active_rooms_after_update = len(self.active_rooms)
            print(f"[*] BroadcastManager: 업데이트 후 활성 장치 수: {active_count_after_update}")
            print(f"[*] BroadcastManager: 업데이트 후 활성 방 수: {active_rooms_after_update}")
            
            # 2. 실제 패킷 전송 (빈 집합 = 모든 장치 OFF) - 최대 3번 시도
            print("[*] BroadcastManager: 패킷 전송 시작 (최대 3번 시도)")
            for attempt in range(3):
                try:
                    print(f"[*] BroadcastManager: 패킷 전송 시도 {attempt + 1}/3")
                    success, response = self.network_manager.send_current_state_packet(set())
                    
                    if success:
                        self.packet_sent_count += 1
                        logger.info(f"모든 장치 끄기 패킷 전송 성공 (시도 {attempt + 1}/3)")
                        print(f"[*] BroadcastManager: 패킷 전송 성공 (시도 {attempt + 1}/3)")
                        if response:
                            logger.info(f"서버 응답: {response.hex()}")
                            print(f"[*] BroadcastManager: 서버 응답 수신: {response.hex()}")
                        
                        # 최종 상태 확인
                        print("[*] BroadcastManager: 최종 상태 확인")
                        final_active_count = sum(1 for status in self.device_matrix.values() if status == DeviceStatus.ON)
                        final_active_rooms = len(self.active_rooms)
                        print(f"[*] BroadcastManager: 최종 활성 장치 수: {final_active_count}")
                        print(f"[*] BroadcastManager: 최종 활성 방 수: {final_active_rooms}")
                        print(f"[*] BroadcastManager: 최종 활성 방 목록: {sorted(self.active_rooms)}")
                        
                        if final_active_count == 0:
                            print("[*] BroadcastManager: 모든 장치가 성공적으로 OFF 상태로 설정됨")
                        else:
                            print(f"[!] BroadcastManager: 경고 - 여전히 {final_active_count}개 장치가 ON 상태")
                        
                        return True
                    else:
                        print(f"[!] BroadcastManager: 패킷 전송 실패 (시도 {attempt + 1}/3)")
                        if attempt < 2:
                            print(f"[*] BroadcastManager: 재시도 전 대기 (0.5초)")
                            time.sleep(0.5)
                        
                except Exception as e:
                    print(f"[!] BroadcastManager: 패킷 전송 시도 {attempt + 1}/3 중 오류: {e}")
                    if attempt < 2:
                        print(f"[*] BroadcastManager: 재시도 전 대기 (0.5초)")
                        time.sleep(0.5)
            
            # 모든 시도 실패 시 이전 상태로 롤백
            print("[!] BroadcastManager: 모든 패킷 전송 시도 실패 - 상태 롤백")
            self.device_matrix = previous_matrix
            self.active_rooms = previous_active
            logger.error("패킷 전송 실패 - 상태 롤백")
            return False
            
        except Exception as e:
            logger.error(f"모든 장치 끄기 오류: {e}")
            print(f"[!] BroadcastManager: 모든 장치 끄기 중 오류: {e}")
            # 오류 발생 시 이전 상태로 롤백
            self.device_matrix = previous_matrix
            self.active_rooms = previous_active
            return False
    
    def get_device_status(self, row: int, col: int) -> Optional[DeviceStatus]:
        """개별 장치 상태 조회"""
        if not self._validate_coordinates(row, col):
            return None
        return self.device_matrix.get((row, col), DeviceStatus.OFF)
    
    def get_active_rooms(self) -> Set[int]:
        """활성화된 방 번호 집합 조회"""
        return self.active_rooms.copy()
    
    def get_active_devices(self) -> List[Tuple[int, int]]:
        """활성화된 장치 좌표 목록 조회"""
        active_devices = []
        for (row, col), status in self.device_matrix.items():
            if status == DeviceStatus.ON:
                active_devices.append((row, col))
        return active_devices
    
    def test_connection(self) -> bool:
        """네트워크 연결 테스트"""
        logger.info("네트워크 연결 테스트")
        success = self.network_manager.test_connection()
        logger.info(f"연결 테스트 결과: {success}")
        return success
    
    def get_status_summary(self) -> Dict[str, Any]:
        """통합 상태 요약"""
        active_count = sum(1 for status in self.device_matrix.values() if status == DeviceStatus.ON)
        total_devices = len(self.device_matrix)
        
        return {
            "total_devices": total_devices,
            "active_count": active_count,
            "inactive_count": total_devices - active_count,
            "active_devices": self.get_active_devices(),
            "active_rooms": sorted(self.active_rooms),
            "network_packets_sent": self.packet_sent_count,
            "target_ip": self.network_manager.target_ip,
            "target_port": self.network_manager.target_port
        }
    
    def print_status_matrix(self):
        """장치 매트릭스 상태 출력"""
        print("\n" + "=" * 80)
        print("🎯 통합 방송 장치 매트릭스 상태")
        print("=" * 80)
        print("   ●: 활성화 (ON)  ○: 비활성화 (OFF)")
        print("-" * 80)
        
        # 열 번호 헤더
        print("행\\열", end="")
        for col in range(1, 17):
            print(f"{col:3}", end="")
        print()
        
        # 각 행의 상태 출력
        for row in range(1, 5):
            print(f" {row}  ", end="")
            for col in range(1, 17):
                status = self.get_device_status(row, col)
                symbol = "●" if status == DeviceStatus.ON else "○"
                print(f" {symbol} ", end="")
            print()
        
        print("-" * 80)
        
        # 통합 상태 요약
        summary = self.get_status_summary()
        
        print(f"📊 활성화: {summary['active_count']}개 | 비활성화: {summary['inactive_count']}개")
        print(f"📡 전송된 패킷 수: {summary['network_packets_sent']}개")
        print(f"🎯 대상 서버: {summary['target_ip']}:{summary['target_port']}")
        
        # 활성화된 장치 목록
        active_devices = summary['active_devices']
        if active_devices:
            print(f"🔥 활성화된 장치: ", end="")
            for i, (row, col) in enumerate(active_devices):
                room_id = row * 100 + col
                print(f"방{room_id}({row},{col})", end="")
                if i < len(active_devices) - 1:
                    print(", ", end="")
            print()
        else:
            print("🔥 활성화된 장치: 없음")
        
        print("=" * 80)

# 싱글톤 인스턴스 생성
broadcast_manager = BroadcastManager() 
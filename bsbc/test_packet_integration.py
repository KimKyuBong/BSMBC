#!/usr/bin/env python3
"""
장치 관리자와 네트워크 패킷 전송 통합 테스트
실제 패킷 전송과 장치 상태 관리를 연동합니다.
"""

import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), 'bsbc'))

from bsbc.app.services.broadcast_device_manager_improved import broadcast_device_manager_improved
from bsbc.app.services.network import network_manager
from bsbc.app.services.packet_builder import packet_builder

class IntegratedBroadcastManager:
    """
    장치 관리자와 네트워크 전송을 통합한 관리자
    """
    
    def __init__(self):
        """초기화"""
        self.device_manager = broadcast_device_manager_improved
        self.network_manager = network_manager
        self.packet_builder = packet_builder
        
        print("🔗 통합 방송 관리자 초기화 완료")
        print(f"   - 네트워크 대상: {self.network_manager.target_ip}:{self.network_manager.target_port}")
    
    def turn_on_device_with_packet(self, row, col):
        """
        개별 장치를 켜고 실제 패킷을 전송합니다.
        상태 관리자가 현재 상태를 파악하여 해당 상태로 패킷을 전송합니다.
        """
        print(f"🔥 장치 켜기 + 패킷 전송: ({row}, {col})")
        
        # 이전 상태 백업
        previous_active = self.device_manager.get_active_rooms()
        
        # 1. 내부 상태 업데이트
        device_success = self.device_manager.turn_on_device(row, col)
        print(f"   ✅ 장치 상태 업데이트: {device_success}")
        
        if not device_success:
            return False
        
        # 2. 현재 활성화된 모든 방들의 상태로 패킷 전송
        try:
            current_active_rooms = self.device_manager.get_active_rooms()
            packet_success, response = self.network_manager.send_current_state_packet(current_active_rooms)
            print(f"   📡 패킷 전송 결과: {packet_success}")
            print(f"   🎯 전송된 상태: {sorted(current_active_rooms)} (총 {len(current_active_rooms)}개 방)")
            
            if response:
                print(f"   📥 서버 응답: {response.hex()}")
            
            return packet_success
            
        except Exception as e:
            print(f"   ❌ 패킷 전송 오류: {e}")
            # 패킷 전송 실패 시 이전 상태로 롤백
            self.device_manager.set_active_rooms(previous_active)
            return False
    
    def turn_off_device_with_packet(self, row, col):
        """
        개별 장치를 끄고 실제 패킷을 전송합니다.
        상태 관리자가 현재 상태를 파악하여 해당 상태로 패킷을 전송합니다.
        """
        print(f"💤 장치 끄기 + 패킷 전송: ({row}, {col})")
        
        # 이전 상태 백업
        previous_active = self.device_manager.get_active_rooms()
        
        # 1. 내부 상태 업데이트
        device_success = self.device_manager.turn_off_device(row, col)
        print(f"   ✅ 장치 상태 업데이트: {device_success}")
        
        if not device_success:
            return False
        
        # 2. 현재 활성화된 모든 방들의 상태로 패킷 전송
        try:
            current_active_rooms = self.device_manager.get_active_rooms()
            packet_success, response = self.network_manager.send_current_state_packet(current_active_rooms)
            print(f"   📡 패킷 전송 결과: {packet_success}")
            print(f"   🎯 전송된 상태: {sorted(current_active_rooms)} (총 {len(current_active_rooms)}개 방)")
            
            if response:
                print(f"   📥 서버 응답: {response.hex()}")
            
            return packet_success
            
        except Exception as e:
            print(f"   ❌ 패킷 전송 오류: {e}")
            # 패킷 전송 실패 시 이전 상태로 롤백
            self.device_manager.set_active_rooms(previous_active)
            return False
    
    def set_active_rooms_with_packet(self, active_rooms):
        """
        방 번호 기반 제어 + 실제 패킷 전송
        
        Args:
            active_rooms: 활성화할 방 번호 집합/리스트
            
        Returns:
            bool: 성공 여부
        """
        print(f"🏠 방 번호 기반 제어 + 패킷 전송: {active_rooms}")
        
        # 이전 상태 백업
        previous_active = self.device_manager.get_active_rooms()
        
        # 1. 내부 상태 업데이트
        device_success = self.device_manager.set_active_rooms(active_rooms)
        print(f"   ✅ 장치 상태 업데이트: {device_success}")
        
        if not device_success:
            return False
        
        # 2. 실제 패킷 전송
        try:
            # 현재 활성화된 방 목록으로 패킷 생성
            current_active = self.device_manager.get_active_rooms()
            packet_success, response = self.network_manager.send_current_state_packet(current_active)
            print(f"   📡 패킷 전송 결과: {packet_success}")
            
            if response:
                print(f"   📥 서버 응답: {response.hex()}")
            
            return packet_success
            
        except Exception as e:
            print(f"   ❌ 패킷 전송 오류: {e}")
            # 패킷 전송 실패 시 이전 상태로 롤백
            self.device_manager.set_active_rooms(previous_active)
            return False
    
    def turn_off_all_with_packet(self):
        """
        모든 장치 끄기 + 실제 패킷 전송
        
        Returns:
            bool: 성공 여부
        """
        print("💤 모든 장치 끄기 + 패킷 전송")
        
        # 이전 상태 백업
        previous_active = self.device_manager.get_active_rooms()
        
        # 1. 내부 상태 업데이트
        device_success = self.device_manager.turn_off_all_devices()
        print(f"   ✅ 장치 상태 업데이트: {device_success}")
        
        if not device_success:
            return False
        
        # 2. 실제 패킷 전송 (모든 장치 OFF)
        try:
            # 빈 집합으로 패킷 전송 (모든 장치 OFF)
            packet_success, response = self.network_manager.send_current_state_packet(set())
            print(f"   📡 패킷 전송 결과: {packet_success}")
            
            if response:
                print(f"   📥 서버 응답: {response.hex()}")
            
            return packet_success
            
        except Exception as e:
            print(f"   ❌ 패킷 전송 오류: {e}")
            # 패킷 전송 실패 시 이전 상태로 롤백
            self.device_manager.set_active_rooms(previous_active)
            return False
    
    def test_connection(self):
        """네트워크 연결 테스트"""
        print("🔌 네트워크 연결 테스트")
        success = self.network_manager.test_connection()
        print(f"   📡 연결 테스트 결과: {success}")
        return success
    
    def get_status_summary(self):
        """통합 상태 요약"""
        device_summary = self.device_manager.get_device_status_summary()
        network_counter = self.network_manager.get_packet_counter()
        
        return {
            "device_status": device_summary,
            "network_packets_sent": network_counter,
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
                status = self.device_manager.get_device_status(row, col)
                symbol = "●" if status and status.name == "ON" else "○"
                print(f" {symbol} ", end="")
            print()
        
        print("-" * 80)
        
        # 통합 상태 요약
        summary = self.get_status_summary()
        device_info = summary["device_status"]
        
        print(f"📊 활성화: {device_info['active_count']}개 | 비활성화: {device_info['inactive_count']}개")
        print(f"📡 전송된 패킷 수: {summary['network_packets_sent']}개")
        print(f"🎯 대상 서버: {summary['target_ip']}:{summary['target_port']}")
        
        # 활성화된 장치 목록
        active_devices = device_info['active_devices']
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


def test_integrated_broadcast():
    """통합 방송 시스템 테스트"""
    
    print("🚀 통합 방송 시스템 테스트 시작")
    print("=" * 80)
    print("이 테스트는 장치 상태 관리와 실제 패킷 전송을 모두 수행합니다.")
    print("=" * 80)
    
    # 통합 관리자 생성
    integrated_manager = IntegratedBroadcastManager()
    
    # 1단계: 네트워크 연결 테스트
    print("\n🔄 1단계: 네트워크 연결 테스트")
    connection_ok = integrated_manager.test_connection()
    
    if not connection_ok:
        print("❌ 네트워크 연결 실패! 시뮬레이션 모드로 계속 진행합니다.")
        print("   (실제 패킷은 전송되지 않지만 상태 관리는 정상 작동)")
    
    integrated_manager.print_status_matrix()
    time.sleep(2)
    
    # 2단계: 모든 장치 끄기 (초기화)
    print("\n🔄 2단계: 시스템 초기화 (모든 장치 끄기)")
    success = integrated_manager.turn_off_all_with_packet()
    print(f"✅ 초기화 결과: {success}")
    integrated_manager.print_status_matrix()
    time.sleep(3)
    
    # 3단계: 모둠12 켜기 (개별 장치 제어)
    print("\n🔄 3단계: 모둠12 켜기 (개별 장치 제어)")
    success = integrated_manager.turn_on_device_with_packet(3, 12)
    print(f"✅ 모둠12 켜기 결과: {success}")
    integrated_manager.print_status_matrix()
    time.sleep(3)
    
    # 4단계: 1학년 교실들 켜기 (여러 장치)
    print("\n🔄 4단계: 1학년 교실들 켜기")
    rooms_1st = {101, 102, 103, 104}
    success = integrated_manager.set_active_rooms_with_packet(rooms_1st)
    print(f"✅ 1학년 교실들 켜기 결과: {success}")
    integrated_manager.print_status_matrix()
    time.sleep(3)
    
    # 5단계: 2학년으로 전환
    print("\n🔄 5단계: 2학년 교실들로 전환")
    rooms_2nd = {201, 202, 203, 204, 205}
    success = integrated_manager.set_active_rooms_with_packet(rooms_2nd)
    print(f"✅ 2학년 교실들 전환 결과: {success}")
    integrated_manager.print_status_matrix()
    time.sleep(3)
    
    # 6단계: 개별 장치 끄기
    print("\n🔄 6단계: 개별 장치 끄기 (방201)")
    success = integrated_manager.turn_off_device_with_packet(2, 1)
    print(f"✅ 방201 끄기 결과: {success}")
    integrated_manager.print_status_matrix()
    time.sleep(3)
    
    # 7단계: 최종 정리
    print("\n🔄 7단계: 최종 정리 (모든 장치 끄기)")
    success = integrated_manager.turn_off_all_with_packet()
    print(f"✅ 최종 정리 결과: {success}")
    integrated_manager.print_status_matrix()
    
    # 8단계: 최종 통계
    print("\n📊 8단계: 최종 통계")
    summary = integrated_manager.get_status_summary()
    device_info = summary["device_status"]
    
    print(f"🔢 총 상태 변경 횟수: {device_info['total_changes']}회")
    print(f"📡 총 전송된 패킷 수: {summary['network_packets_sent']}개")
    print(f"⏱️ 테스트 진행 시간: {device_info['uptime_seconds']:.1f}초")
    print(f"🎯 대상 서버: {summary['target_ip']}:{summary['target_port']}")
    
    # 히스토리
    print("\n📚 최근 상태 변경 히스토리:")
    history = integrated_manager.device_manager.get_status_history(5)
    for i, change in enumerate(history, 1):
        print(f"   {i}. 방{change['room_id']} ({change['position'][0]},{change['position'][1]}): "
              f"{change['old_state']} → {change['new_state']}")
    
    print("\n🎉 통합 테스트 완료!")
    print("=" * 80)


def test_interactive_integrated():
    """대화형 통합 테스트"""
    integrated_manager = IntegratedBroadcastManager()
    
    print("\n🎮 대화형 통합 테스트 모드")
    print("=" * 60)
    print("명령어:")
    print("  on <행> <열>        - 특정 장치 켜기 + 패킷 전송")
    print("  off <행> <열>       - 특정 장치 끄기 + 패킷 전송")
    print("  rooms <방번호들>    - 방 번호로 제어 + 패킷 전송")
    print("  all_off            - 모든 장치 끄기 + 패킷 전송")
    print("  show               - 현재 상태 보기")
    print("  test_conn          - 네트워크 연결 테스트")
    print("  stats              - 통계 보기")
    print("  quit               - 종료")
    print("=" * 60)
    
    while True:
        try:
            command = input("\n통합 명령어 입력> ").strip().lower()
            
            if command == "quit":
                break
            elif command == "show":
                integrated_manager.print_status_matrix()
            elif command == "all_off":
                success = integrated_manager.turn_off_all_with_packet()
                print(f"✅ 모든 장치 끄기 결과: {success}")
                integrated_manager.print_status_matrix()
            elif command == "test_conn":
                integrated_manager.test_connection()
            elif command == "stats":
                summary = integrated_manager.get_status_summary()
                print(f"\n📊 통계:")
                print(f"   - 활성화된 장치: {summary['device_status']['active_count']}개")
                print(f"   - 총 상태 변경: {summary['device_status']['total_changes']}회")
                print(f"   - 전송된 패킷: {summary['network_packets_sent']}개")
            elif command.startswith("on "):
                parts = command.split()
                if len(parts) == 3:
                    row, col = int(parts[1]), int(parts[2])
                    success = integrated_manager.turn_on_device_with_packet(row, col)
                    print(f"✅ 방{row*100+col} 켜기 결과: {success}")
                    integrated_manager.print_status_matrix()
            elif command.startswith("off "):
                parts = command.split()
                if len(parts) == 3:
                    row, col = int(parts[1]), int(parts[2])
                    success = integrated_manager.turn_off_device_with_packet(row, col)
                    print(f"✅ 방{row*100+col} 끄기 결과: {success}")
                    integrated_manager.print_status_matrix()
            elif command.startswith("rooms "):
                room_str = command[6:]
                rooms = [int(r.strip()) for r in room_str.split(",")]
                success = integrated_manager.set_active_rooms_with_packet(rooms)
                print(f"✅ 방 {rooms} 설정 결과: {success}")
                integrated_manager.print_status_matrix()
            else:
                print("❌ 알 수 없는 명령어입니다.")
                
        except (ValueError, IndexError):
            print("❌ 잘못된 명령어 형식입니다.")
        except KeyboardInterrupt:
            print("\n\n👋 프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    try:
        print("🎯 통합 방송 시스템 테스트")
        print("1. 자동 통합 테스트")
        print("2. 대화형 통합 테스트")
        
        choice = input("\n선택하세요 (1 또는 2): ").strip()
        
        if choice == "1":
            test_integrated_broadcast()
        elif choice == "2":
            test_interactive_integrated()
        else:
            print("기본으로 자동 통합 테스트를 실행합니다.")
            test_integrated_broadcast()
            
    except KeyboardInterrupt:
        print("\n\n👋 프로그램을 종료합니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
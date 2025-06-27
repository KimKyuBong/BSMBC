#!/usr/bin/env python3
"""
control_multiple_devices 함수 테스트 스크립트
"""
import sys
import os
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.broadcast_controller import broadcast_controller

def test_control_multiple_devices():
    """control_multiple_devices 함수 테스트"""
    print("=" * 60)
    print("control_multiple_devices 함수 테스트 시작")
    print("=" * 60)
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "1학년 교실들 켜기",
            "devices": ["1-1", "1-2", "1-3", "1-4"],
            "state": 1
        },
        {
            "name": "1학년 교실들 끄기", 
            "devices": ["1-1", "1-2", "1-3", "1-4"],
            "state": 0
        },
        {
            "name": "2학년 교실들 켜기",
            "devices": ["2-1", "2-2", "2-3", "2-4"], 
            "state": 1
        },
        {
            "name": "2학년 교실들 끄기",
            "devices": ["2-1", "2-2", "2-3", "2-4"],
            "state": 0
        },
        {
            "name": "3학년 교실들 켜기",
            "devices": ["3-1", "3-2", "3-3", "3-4"],
            "state": 1
        },
        {
            "name": "3학년 교실들 끄기",
            "devices": ["3-1", "3-2", "3-3", "3-4"],
            "state": 0
        },
        {
            "name": "혼합 장치들 켜기 (교실 + 특수실)",
            "devices": ["1-1", "2-1", "3-1", "교무실", "강당"],
            "state": 1
        },
        {
            "name": "혼합 장치들 끄기",
            "devices": ["1-1", "2-1", "3-1", "교무실", "강당"],
            "state": 0
        },
        {
            "name": "숫자 ID로 테스트",
            "devices": [101, 201, 301],  # 1-1, 2-1, 3-1
            "state": 1
        },
        {
            "name": "숫자 ID로 끄기",
            "devices": [101, 201, 301],
            "state": 0
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n[*] 테스트 {i}: {test_case['name']}")
        print(f"    장치: {test_case['devices']}")
        print(f"    상태: {'켜기' if test_case['state'] else '끄기'}")
        
        try:
            # 함수 실행
            success = broadcast_controller.control_multiple_devices(
                test_case['devices'], 
                test_case['state']
            )
            
            if success:
                print(f"    [+] 성공")
            else:
                print(f"    [!] 실패")
                
        except Exception as e:
            print(f"    [!] 오류 발생: {e}")
        
        # 다음 테스트 전에 대기
        print("    [*] 3초 대기...")
        time.sleep(3)
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)

def test_single_device():
    """단일 장치 제어 테스트"""
    print("\n" + "=" * 60)
    print("단일 장치 제어 테스트")
    print("=" * 60)
    
    test_devices = ["1-1", "2-1", "3-1", "교무실", "강당", "방송실", "운동장"]
    
    for device in test_devices:
        print(f"\n[*] 장치 '{device}' 켜기 테스트")
        try:
            success = broadcast_controller.control_device(device, 1)
            if success:
                print(f"    [+] 성공")
            else:
                print(f"    [!] 실패")
        except Exception as e:
            print(f"    [!] 오류: {e}")
        
        time.sleep(2)
        
        print(f"[*] 장치 '{device}' 끄기 테스트")
        try:
            success = broadcast_controller.control_device(device, 0)
            if success:
                print(f"    [+] 성공")
            else:
                print(f"    [!] 실패")
        except Exception as e:
            print(f"    [!] 오류: {e}")
        
        time.sleep(2)

def test_device_mapping():
    """장치 매핑 정보 확인"""
    print("\n" + "=" * 60)
    print("장치 매핑 정보 확인")
    print("=" * 60)
    
    # 장치 매퍼에서 정보 가져오기
    device_mapper = broadcast_controller.device_mapper
    
    print(f"[*] 전체 장치 수: {len(device_mapper.device_map)}")
    print(f"[*] 활성화된 방 목록: {broadcast_controller.active_rooms}")
    
    # 일부 장치 좌표 확인
    test_devices = ["1-1", "2-1", "3-1", "교무실", "강당"]
    for device in test_devices:
        coords = device_mapper.get_device_coords(device)
        if coords:
            row, col = coords
            device_id = device_mapper._get_device_id(device)
            print(f"[*] {device}: 좌표({row},{col}), ID({device_id})")
        else:
            print(f"[!] {device}: 좌표를 찾을 수 없음")

if __name__ == "__main__":
    try:
        # 시스템 정보 출력
        print("[*] 방송 제어 시스템 초기화...")
        broadcast_controller.print_system_info()
        
        # 장치 매핑 정보 확인
        test_device_mapping()
        
        # 단일 장치 테스트
        test_single_device()
        
        # 다중 장치 테스트
        test_control_multiple_devices()
        
    except KeyboardInterrupt:
        print("\n[!] 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n[!] 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc() 
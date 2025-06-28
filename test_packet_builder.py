#!/usr/bin/env python3
"""
패킷 빌더 테스트 모듈
4행 16열 행렬의 모든 좌표를 테스트합니다.
"""
import time
import socket
import json
from app.services.packet_builder import packet_builder
from app.services.network import network_manager

# 네트워크 설정
TARGET_IP = "192.168.0.200"
TARGET_PORT = 22000

# 캡처된 패킷 로드 함수
def load_captured_packets():
    with open("../captured_packets.json", "r", encoding="utf-8") as f:
        return json.load(f)

def compare_packets(generated: bytes, captured_hex: str, title: str):
    captured = bytes.fromhex(captured_hex)
    print(f"\n=== {title} 패킷 비교 ===")
    print(f"생성된 패킷: {generated.hex()}")
    print(f"캡처된 패킷: {captured.hex()}")
    if generated == captured:
        print("✓ 패킷 일치!")
    else:
        print("✗ 패킷 불일치!")
        for i in range(min(len(generated), len(captured))):
            if generated[i] != captured[i]:
                print(f"  바이트 {i}: 생성={generated[i]:02x}, 캡처={captured[i]:02x}")

def test_single_coordinate(row, col, state):
    """단일 좌표 테스트"""
    print(f"[{row:2d},{col:2d}] {'켜기' if state else '끄기'} 테스트 중...")
    
    # 패킷 생성
    payload = packet_builder.create_coordinate_payload(row, col, state)
    if payload is None:
        print(f"[!] 패킷 생성 실패: ({row}, {col})")
        return False
    
    # 패킷 로그 출력
    print(f"[*] 패킷 전송: {len(payload)}바이트")
    print(f"[*] 패킷 데이터: {payload.hex()}")
    
    # 네트워크 매니저를 통해 전송
    success, response = network_manager.send_payload_single(payload)
    
    if success:
        print(f"[✓] ({row}, {col}) {'켜기' if state else '끄기'} 성공")
    else:
        print(f"[✗] ({row}, {col}) {'켜기' if state else '끄기'} 실패")
    
    return success

def test_all_coordinates():
    """모든 좌표 테스트 (4행 16열 = 64개)"""
    print("패킷 빌더 테스트 시작")
    print(f"대상: {TARGET_IP}:{TARGET_PORT}")
    print(f"테스트 좌표: 4행 × 16열 = 64개")
    print(f"간격: 5초")
    print("=" * 60)
    
    # 네트워크 매니저 설정
    network_manager.target_ip = TARGET_IP
    network_manager.target_port = TARGET_PORT
    total_tests = 0
    success_count = 0
    fail_count = 0
    
    # 모든 좌표에 대해 켜기/끄기 테스트
    for row in range(4, 5):  # 1-4행
        for col in range(9, 17):  # 1-16열
            print(f"\n--- {row}행 {col}열 테스트 ---")
            
            # 켜기 테스트
            total_tests += 1
            if test_single_coordinate(row, col, 1):
                success_count += 1
            else:
                fail_count += 1
            
            time.sleep(1)  # 5초 대기
            
            # 끄기 테스트
            total_tests += 1
            if test_single_coordinate(row, col, 0):
                success_count += 1
            else:
                fail_count += 1
            
            time.sleep(1)  # 5초 대기
    
    # 최종 결과 출력
    print("\n" + "=" * 60)
    print("패킷 빌더 테스트 완료!")
    print(f"총 테스트: {total_tests}개")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"성공률: {success_count/total_tests*100:.1f}%")

def test_multiple_coordinates():
    """여러 좌표 동시 테스트"""
    print("\n여러 좌표 동시 테스트")
    print("=" * 40)
    
    # 핵심 좌표들 (각 행의 1, 5, 9, 13열)
    key_coordinates = [
        (1, 1), (1, 5), (1, 9), (1, 13),
        (2, 1), (2, 5), (2, 9), (2, 13),
        (3, 1), (3, 5), (3, 9), (3, 13),
        (4, 1), (4, 5), (4, 9), (4, 13)
    ]
    
    # 켜기 테스트
    print("핵심 좌표들 동시 켜기...")
    payload = packet_builder.create_multiple_coordinates_payload(key_coordinates, 1)
    if payload:
        print(f"[*] 동시 켜기 패킷: {payload.hex()}")
        network_manager.send_payload_single(payload)
        print(f"동시 켜기 결과: 전송 완료")
    
    time.sleep(1)
    
    # 끄기 테스트
    print("핵심 좌표들 동시 끄기...")
    payload = packet_builder.create_multiple_coordinates_payload(key_coordinates, 0)
    if payload:
        print(f"[*] 동시 끄기 패킷: {payload.hex()}")
        network_manager.send_payload_single(payload)
        print(f"동시 끄기 결과: 전송 완료")

def test_all_off():
    """전체 OFF 테스트"""
    print("\n전체 OFF 테스트")
    print("=" * 40)
    
    payload = packet_builder.create_all_off_payload()
    if payload:
        print(f"[*] 전체 OFF 패킷: {payload.hex()}")
        network_manager.send_payload_single(payload)
        print(f"전체 OFF 결과: 전송 완료")

def test_compare_with_captured():
    captured_packets = load_captured_packets()
    # 1. 전체 OFF (첫 번째 패킷)
    gen_off = packet_builder.create_all_off_payload()
    compare_packets(gen_off, captured_packets[0]["hex_data"], "전체 OFF")
    # 2. 1행 5열 켜기 (두 번째 패킷)
    gen_1_5_on = packet_builder.create_coordinate_payload(1, 5, 1)
    compare_packets(gen_1_5_on, captured_packets[1]["hex_data"], "1행 5열 켜기")
    # 3. 1행 9열 켜기 (여섯 번째 패킷)
    gen_1_9_on = packet_builder.create_coordinate_payload(1, 9, 1)
    compare_packets(gen_1_9_on, captured_packets[5]["hex_data"], "1행 9열 켜기")
    # 4. 2행 1열 켜기 (네 번째 패킷)
    gen_2_1_on = packet_builder.create_coordinate_payload(2, 1, 1)
    compare_packets(gen_2_1_on, captured_packets[3]["hex_data"], "2행 1열 켜기")
    # 5. 2행 9열 켜기 (여덟 번째 패킷)
    gen_2_9_on = packet_builder.create_coordinate_payload(2, 9, 1)
    compare_packets(gen_2_9_on, captured_packets[7]["hex_data"], "2행 9열 켜기")

if __name__ == "__main__":
    try:
        # 1. 전체 OFF로 시작
        test_all_off()
        time.sleep(3)
        
        # # 2. 여러 좌표 동시 테스트
        test_multiple_coordinates()
        # time.sleep(3)
        
        # 3. 개별 좌표 테스트 (선택사항 - 시간이 오래 걸림)
        # test_all_coordinates()
        
        # 4. 생성된 패킷과 캡처된 패킷 비교
        # test_compare_with_captured()
        
    except KeyboardInterrupt:
        print("\n\n테스트가 중단되었습니다.")
        # 중단 시 전체 OFF
        test_all_off()
    except Exception as e:
        print(f"\n테스트 중 오류 발생: {e}")
        # 오류 시 전체 OFF
        test_all_off() 
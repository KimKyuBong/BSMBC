#!/usr/bin/env python3
"""
명령행 인터페이스 유틸리티
명령행에서 방송 제어 시스템을 조작하기 위한 기능을 제공합니다.
"""
import os
import sys
import time
import re
import argparse
from ..services.broadcast_controller import broadcast_controller

def parse_args():
    """
    명령행 인수 분석
    
    Returns:
    --------
    argparse.Namespace
        파싱된 명령행 인수
    """
    parser = argparse.ArgumentParser(description="학교 방송 제어 시스템 명령행 도구")
    
    # 서브커맨드 구성
    subparsers = parser.add_subparsers(dest="command", help="명령")
    
    # 장치 제어 명령
    control_parser = subparsers.add_parser("control", help="장치 제어")
    control_parser.add_argument("device", help="제어할 장치명 (예: '1-1', '선생영역')")
    control_parser.add_argument("--on", action="store_true", help="장치 켜기")
    control_parser.add_argument("--off", action="store_true", help="장치 끄기")
    
    # 장치 그룹 제어 명령
    group_parser = subparsers.add_parser("group", help="장치 그룹 제어")
    group_parser.add_argument("group", help="제어할 그룹 (예: 'grade1', 'special')")
    group_parser.add_argument("--on", action="store_true", help="장치 켜기")
    group_parser.add_argument("--off", action="store_true", help="장치 끄기")
    
    # 채널 제어 명령
    channel_parser = subparsers.add_parser("channel", help="채널 제어")
    channel_parser.add_argument("channel", type=int, help="제어할 채널 번호")
    channel_parser.add_argument("--on", action="store_true", help="채널 켜기")
    channel_parser.add_argument("--off", action="store_true", help="채널 끄기")
    
    # 시스템 상태 명령
    status_parser = subparsers.add_parser("status", help="시스템 상태 조회")
    status_parser.add_argument("--init", action="store_true", help="시스템 상태 초기화")
    
    # 스케줄 관련 명령
    schedule_parser = subparsers.add_parser("schedule", help="스케줄 관리")
    schedule_parser.add_argument("--list", action="store_true", help="스케줄 목록 조회")
    schedule_parser.add_argument("--add", action="store_true", help="스케줄 추가")
    schedule_parser.add_argument("--delete", type=int, help="스케줄 삭제 (ID 지정)")
    schedule_parser.add_argument("--start", action="store_true", help="스케줄러 시작")
    schedule_parser.add_argument("--stop", action="store_true", help="스케줄러 중지")
    
    # 스케줄 추가 시 필요한 인수
    schedule_parser.add_argument("--time", help="실행 시간 (HH:MM 형식)")
    schedule_parser.add_argument("--days", help="실행 요일 (쉼표로 구분)")
    schedule_parser.add_argument("--command", type=int, help="명령 타입 (1: 장비 제어)")
    schedule_parser.add_argument("--target", type=int, help="대상 채널/장치")
    schedule_parser.add_argument("--state", type=int, help="상태 (0: 끄기, 1: 켜기)")
    
    # 테스트 명령
    test_parser = subparsers.add_parser("test", help="테스트 기능")
    test_parser.add_argument("--sequence", action="store_true", help="테스트 시퀀스 실행")
    
    # 네트워크 설정 명령
    network_parser = subparsers.add_parser("network", help="네트워크 설정")
    network_parser.add_argument("--ip", help="대상 IP 설정")
    network_parser.add_argument("--port", type=int, help="대상 포트 설정")
    
    return parser.parse_args()

def print_header():
    """
    프로그램 헤더 출력
    """
    print("\n" + "="*60)
    print("  학교 방송 제어 시스템 - 명령행 도구")
    print("  버전:", broadcast_controller.get_version())
    print("="*60)

def handle_control_command(args):
    """
    장치 제어 명령 처리
    """
    if args.on and args.off:
        print("[!] 에러: --on과 --off를 동시에 사용할 수 없습니다.")
        return False
    
    if not (args.on or args.off):
        print("[!] 에러: --on 또는 --off 옵션을 지정해야 합니다.")
        return False
    
    state = 1 if args.on else 0
    action = "켜기" if args.on else "끄기"
    
    print(f"[*] 장치 '{args.device}' {action} 명령 실행...")
    success = broadcast_controller.control_device(args.device, state)
    
    if success:
        print(f"[+] 장치 '{args.device}' {action} 명령이 성공적으로 실행되었습니다.")
    else:
        print(f"[!] 장치 '{args.device}' {action} 명령 실행 실패")
    
    return success

def handle_group_command(args):
    """
    장치 그룹 제어 명령 처리
    """
    if args.on and args.off:
        print("[!] 에러: --on과 --off를 동시에 사용할 수 없습니다.")
        return False
    
    if not (args.on or args.off):
        print("[!] 에러: --on 또는 --off 옵션을 지정해야 합니다.")
        return False
    
    state = 1 if args.on else 0
    action = "켜기" if args.on else "끄기"
    
    # 그룹별 장치 매핑
    group_devices = {
        "grade1": ["1-1", "1-2", "1-3", "1-4"],
        "grade2": ["2-1", "2-2", "2-3", "2-4"],
        "grade3": ["3-1", "3-2", "3-3", "3-4"],
        "special": ["선생영역", "시청각실", "체육관", "보건실부"],
        "all": ["1-1", "1-2", "1-3", "1-4", "2-1", "2-2", "2-3", "2-4", "3-1", "3-2", "3-3", "3-4"]
    }
    
    if args.group not in group_devices:
        print(f"[!] 에러: 알 수 없는 그룹 '{args.group}'")
        print("[*] 사용 가능한 그룹: grade1, grade2, grade3, special, all")
        return False
    
    devices = group_devices[args.group]
    print(f"[*] 그룹 '{args.group}' ({', '.join(devices)}) {action} 명령 실행...")
    
    success = broadcast_controller.control_multiple_devices(devices, state)
    
    if success:
        print(f"[+] 그룹 '{args.group}' {action} 명령이 성공적으로 실행되었습니다.")
    else:
        print(f"[!] 그룹 '{args.group}' {action} 명령 실행 실패")
    
    return success

def handle_channel_command(args):
    """
    채널 제어 명령 처리
    """
    if args.on and args.off:
        print("[!] 에러: --on과 --off를 동시에 사용할 수 없습니다.")
        return False
    
    if not (args.on or args.off):
        print("[!] 에러: --on 또는 --off 옵션을 지정해야 합니다.")
        return False
    
    state = 1 if args.on else 0
    action = "켜기" if args.on else "끄기"
    
    print(f"[*] 채널 {args.channel} {action} 명령 실행...")
    success = broadcast_controller.control_channel(0x01, args.channel, state)
    
    if success:
        print(f"[+] 채널 {args.channel} {action} 명령이 성공적으로 실행되었습니다.")
    else:
        print(f"[!] 채널 {args.channel} {action} 명령 실행 실패")
    
    return success

def handle_status_command(args):
    """
    시스템 상태 명령 처리
    """
    if args.init:
        print("[*] 시스템 상태 초기화 중...")
        success = broadcast_controller.initialize_system_state()
        
        if success:
            print("[+] 시스템 상태가 초기화되었습니다.")
            print(f"[*] 활성화된 반: {broadcast_controller.active_rooms}")
        else:
            print("[!] 시스템 상태 초기화 실패")
        
        return success
    
    # 상태 정보 출력
    print("[*] 시스템 상태 정보:")
    print(f"    - 버전: {broadcast_controller.get_version()}")
    print(f"    - 대상 IP: {broadcast_controller.network_manager.target_ip}")
    print(f"    - 대상 포트: {broadcast_controller.network_manager.target_port}")
    print(f"    - 상태 초기화: {'완료' if broadcast_controller.system_initialized else '미완료'}")
    
    if broadcast_controller.system_initialized:
        print(f"    - 활성화된 반: {broadcast_controller.active_rooms}")
    
    return True

def handle_schedule_command(args):
    """
    스케줄 관련 명령 처리
    """
    if args.list:
        # 스케줄 목록 조회
        schedules = broadcast_controller.view_schedules()
        
        if not schedules:
            print("[!] 저장된 예약 방송이 없습니다.")
            return True
        
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
                0x00: "기본(0x00)",
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
        return True
    
    elif args.add:
        # 스케줄 추가
        if not args.time:
            print("[!] 에러: --time 옵션이 필요합니다. (예: --time 08:30)")
            return False
        
        if not args.days:
            print("[!] 에러: --days 옵션이 필요합니다. (예: --days Monday,Wednesday,Friday)")
            return False
        
        if not args.target:
            print("[!] 에러: --target 옵션이 필요합니다. (예: --target 0)")
            return False
        
        if args.state is None:
            print("[!] 에러: --state 옵션이 필요합니다. (예: --state 1)")
            return False
        
        # 시간 형식 확인
        if not re.match(r"^([0-1][0-9]|2[0-3]):([0-5][0-9])$", args.time):
            print("[!] 에러: 잘못된 시간 형식입니다. (예: 08:30)")
            return False
        
        # 커맨드 타입 기본값
        command_type = args.command if args.command is not None else 1
        
        print(f"[*] 스케줄 추가 중: {args.time}, {args.days}, 명령 타입: {command_type}, 대상: {args.target}, 상태: {args.state}")
        success = broadcast_controller.schedule_broadcast(args.time, args.days, command_type, args.target, args.state)
        
        if success:
            print("[+] 스케줄이 성공적으로 추가되었습니다.")
            print("[*] 스케줄러 시작 중...")
            broadcast_controller.start_scheduler()
        else:
            print("[!] 스케줄 추가 실패")
        
        return success
    
    elif args.delete is not None:
        # 스케줄 삭제
        print(f"[*] 스케줄 {args.delete} 삭제 중...")
        success = broadcast_controller.delete_schedule(args.delete - 1)  # 인덱스는 0부터 시작하지만 사용자에게는 1부터 표시
        
        if success:
            print(f"[+] 스케줄 {args.delete}가 삭제되었습니다.")
        else:
            print(f"[!] 스케줄 {args.delete} 삭제 실패")
        
        return success
    
    elif args.start:
        # 스케줄러 시작
        print("[*] 스케줄러 시작 중...")
        broadcast_controller.start_scheduler()
        print("[+] 스케줄러가 시작되었습니다.")
        return True
    
    elif args.stop:
        # 스케줄러 중지
        print("[*] 스케줄러 중지 중...")
        broadcast_controller.stop_scheduler()
        print("[+] 스케줄러가 중지되었습니다.")
        return True
    
    else:
        print("[!] 에러: schedule 명령에는 --list, --add, --delete, --start, --stop 중 하나가 필요합니다.")
        return False

def handle_test_command(args):
    """
    테스트 관련 명령 처리
    """
    if args.sequence:
        print("[*] 테스트 시퀀스 실행 중...")
        broadcast_controller.send_test_packets()
        return True
    
    print("[!] 에러: test 명령에는 --sequence 옵션이 필요합니다.")
    return False

def handle_network_command(args):
    """
    네트워크 설정 명령 처리
    """
    changed = False
    
    if args.ip:
        print(f"[*] 대상 IP를 {args.ip}로 변경 중...")
        broadcast_controller.network_manager.target_ip = args.ip
        print(f"[+] 대상 IP가 {args.ip}로 변경되었습니다.")
        changed = True
    
    if args.port:
        print(f"[*] 대상 포트를 {args.port}로 변경 중...")
        broadcast_controller.network_manager.target_port = args.port
        print(f"[+] 대상 포트가 {args.port}로 변경되었습니다.")
        changed = True
    
    if not changed:
        print("[!] 에러: network 명령에는 --ip 또는 --port 옵션이 필요합니다.")
        return False
    
    return True

def main():
    """
    메인 함수
    """
    args = parse_args()
    print_header()
    
    if not args.command:
        print("[!] 에러: 명령이 지정되지 않았습니다.")
        print("[*] 사용 가능한 명령: control, group, channel, status, schedule, test, network")
        return 1
    
    # 명령별 처리 함수 매핑
    command_handlers = {
        "control": handle_control_command,
        "group": handle_group_command,
        "channel": handle_channel_command,
        "status": handle_status_command,
        "schedule": handle_schedule_command,
        "test": handle_test_command,
        "network": handle_network_command
    }
    
    # 명령 처리
    if args.command in command_handlers:
        success = command_handlers[args.command](args)
        return 0 if success else 1
    else:
        print(f"[!] 에러: 알 수 없는 명령 '{args.command}'")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
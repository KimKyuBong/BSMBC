#!/usr/bin/env python3
"""
스케줄러 모듈
방송 스케줄링을 관리합니다.
"""
import os
import csv
import time
import threading
import datetime
from ..core.config import config
from .packet_builder import packet_builder
from .network import network_manager

class BroadcastScheduler:
    """
    방송 스케줄러 클래스
    예약된 방송을 스케줄링하고 실행합니다.
    """
    def __init__(self):
        """
        초기화 함수
        """
        # 스케줄러 스레드
        self.scheduler_thread = None
        self.running = False
        
        # 스케줄링 정보 저장을 위한 CSV 파일 경로
        self.schedule_file = config.schedule_file
    
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
        self.running = True
        print("[*] 스케줄러가 시작되었습니다")
        
        while self.running:
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
                    
                    # 명령 타입에 따라 페이로드 생성
                    if channel == 0x40:  # 특수 채널 64
                        payload = packet_builder.create_special_payload_64(state)
                    elif channel == 0xD0:  # 특수 채널 208
                        payload = packet_builder.create_special_payload_208(state)
                    else:  # 일반 채널
                        payload = packet_builder.create_command_payload(cmd_type, channel, state)
                    
                    # 네트워크 전송
                    network_manager.send_payload(payload)
            
            # 1분마다 체크
            time.sleep(60)
    
    def start_scheduler(self):
        """스케줄러 시작"""
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.running = True
            self.scheduler_thread = threading.Thread(target=self.run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            print("[+] 스케줄러가 백그라운드에서 실행 중입니다")
        else:
            print("[!] 스케줄러가 이미 실행 중입니다")
    
    def stop_scheduler(self):
        """스케줄러 중지"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.running = False
            self.scheduler_thread.join(2)  # 2초간 스레드 종료 대기
            if self.scheduler_thread.is_alive():
                print("[!] 스케줄러 종료에 실패했습니다")
            else:
                self.scheduler_thread = None
                print("[+] 스케줄러가 중지되었습니다")
        else:
            print("[!] 실행 중인 스케줄러가 없습니다")

# 싱글톤 인스턴스 생성
broadcast_scheduler = BroadcastScheduler() 
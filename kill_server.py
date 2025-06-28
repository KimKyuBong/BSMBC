#!/usr/bin/env python3
"""
서버 강제 종료 스크립트
"""
import os
import sys
import subprocess
import psutil
import time

def kill_processes_by_port(port=8000):
    """특정 포트를 사용하는 프로세스 종료"""
    print(f"🔍 포트 {port} 사용 프로세스 검색 중...")
    
    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            connections = proc.info['connections']
            if connections:
                for conn in connections:
                    if conn.laddr.port == port:
                        print(f"🎯 PID {proc.info['pid']} ({proc.info['name']}) 종료 중...")
                        proc.kill()
                        killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return killed_count

def kill_python_processes():
    """Python 관련 프로세스 종료"""
    print("🔍 Python 프로세스 검색 중...")
    
    killed_count = 0
    target_processes = ['python.exe', 'uvicorn.exe']
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] in target_processes:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if any(keyword in cmdline.lower() for keyword in ['main.py', 'production_server.py', 'fastapi', 'uvicorn']):
                    print(f"🎯 PID {proc.info['pid']} ({proc.info['name']}) 종료 중...")
                    print(f"   명령어: {cmdline}")
                    proc.kill()
                    killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    return killed_count

def check_port_status(port=8000):
    """포트 상태 확인"""
    try:
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        return f":{port}" in result.stdout
    except:
        return False

def main():
    """메인 함수"""
    print("🛑 서버 강제 종료 도구")
    print("=" * 50)
    
    port = 8000
    
    # 1단계: 포트 사용 프로세스 종료
    print("\n🔄 1단계: 포트 사용 프로세스 종료")
    killed = kill_processes_by_port(port)
    print(f"✅ {killed}개 프로세스 종료됨")
    
    # 2단계: Python 프로세스 종료
    print("\n🔄 2단계: Python 관련 프로세스 종료")
    killed = kill_python_processes()
    print(f"✅ {killed}개 Python 프로세스 종료됨")
    
    # 3단계: 대기
    print("\n⏱️ 3초 대기 중...")
    time.sleep(3)
    
    # 4단계: 포트 상태 확인
    print("\n🔍 4단계: 포트 상태 확인")
    if check_port_status(port):
        print(f"⚠️ 포트 {port}가 여전히 사용 중입니다.")
        print("🔄 추가 강제 종료 시도...")
        
        # 추가 강제 종료
        killed = kill_processes_by_port(port)
        print(f"✅ 추가 {killed}개 프로세스 종료됨")
        
        time.sleep(2)
        
        if check_port_status(port):
            print(f"❌ 포트 {port} 해제 실패")
            return False
        else:
            print(f"✅ 포트 {port} 해제 성공")
    else:
        print(f"✅ 포트 {port}가 해제되었습니다.")
    
    print("\n" + "=" * 50)
    print("🎉 서버 강제 종료 완료!")
    print("💡 이제 서버를 다시 시작할 수 있습니다.")
    print("=" * 50)
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    
    input("\n엔터를 눌러 종료하세요...") 
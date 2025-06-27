#!/usr/bin/env python3
"""
특수 공간 제어 테스트 스크립트
"""
import sys
import os
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.broadcast_controller import broadcast_controller

def test_special_spaces():
    """특수 공간 제어 테스트"""
    print("=" * 60)
    print("특수 공간 제어 테스트 시작")
    print("=" * 60)
    
    # 테스트할 특수 공간들
    special_spaces = ["교행연회", "교사연구", "매점", "보건학부", "컴퓨터12", "과학준비", "창의준비", "남여휴게", 
                     "교무실", "학생식당", "위클회의", "프로그12", "전문교무", "진로상담", "모둠12", "창의공작",
                     "본관1층", "융합관1층", "본관2층", "융합관2층", "융합관3층", "강당", "방송실", "별관1-1",
                     "별관1-2", "별관1-3", "별관2-1", "별관2-2", "운동장", "옥외"]
    
    for space in special_spaces:
        print(f"\n[*] 특수 공간 '{space}' 켜기 테스트")
        try:
            success = broadcast_controller.control_device(space, 1)
            if success:
                print(f"    [+] 성공")
            else:
                print(f"    [!] 실패")
        except Exception as e:
            print(f"    [!] 오류: {e}")
        
        time.sleep(2)
        
        print(f"[*] 특수 공간 '{space}' 끄기 테스트")
        try:
            success = broadcast_controller.control_device(space, 0)
            if success:
                print(f"    [+] 성공")
            else:
                print(f"    [!] 실패")
        except Exception as e:
            print(f"    [!] 오류: {e}")
        
        time.sleep(2)

if __name__ == "__main__":
    test_special_spaces() 
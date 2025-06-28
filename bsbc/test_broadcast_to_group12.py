#!/usr/bin/env python3
"""
모둠12에 테스트 TTS 방송 전송
"""

import sys
import os
sys.path.append('.')

from app.services.broadcast_controller import broadcast_controller

def main():
    print('🎙️ 모둠12에 테스트 TTS 방송 시작')
    print('=' * 50)
    
    # 모둠12는 1학년 12반을 의미하므로 1-12로 설정
    target_device = '3-15'
    test_message = '안녕하세요. 모둠12 테스트 방송입니다. 잘 들리시나요?'
    
    print(f'📍 대상: {target_device} (모둠12)')
    print(f'📝 메시지: {test_message}')
    print()
    
    # TTS 방송 전송
    result = broadcast_controller.broadcast_text(
        text=test_message,
        target_devices=[target_device],
        end_devices=[target_device],
        language='ko'
    )
    
    print('✅ 방송 큐 추가 결과:')
    print(f'   상태: {result["status"]}')
    print(f'   큐 크기: {result["queue_size"]}')
    print(f'   메시지: {result["message"]}')
    print()
    print('🔊 방송이 시작됩니다...')
    
    # 방송 처리 대기
    import time
    print('⏳ 방송 처리를 기다리는 중...')
    time.sleep(5)
    
    # 최종 상태 확인
    print('\n📊 최종 상태:')
    from app.services.broadcast_manager import broadcast_manager
    broadcast_manager.print_status_matrix()

if __name__ == '__main__':
    main() 
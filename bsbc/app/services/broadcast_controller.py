#!/usr/bin/env python3
"""
방송 제어 컨트롤러 모듈 - BroadcastManager 중심으로 단순화
방송 시스템 전체 제어를 담당합니다.
"""
import os
import time
import threading
import logging
import json
import datetime
import wave
import contextlib
import traceback
import queue
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
        try:
            import vlc
            print("[*] VLC 모듈이 로드되었습니다. 오디오 재생이 가능합니다.")
        except ImportError:
            print("[!] 경고: VLC 모듈을 로드할 수 없습니다. 오디오 재생이 제한될 수 있습니다.")
        
        print("[!] 경고: TTS 엔진을 로드할 수 없습니다. 텍스트-음성 변환 기능이 비활성화됩니다.")

from ..core.config import config
from .broadcast_manager import broadcast_manager

# 로깅 설정
logger = logging.getLogger(__name__)

# 음성 파일 저장 경로
AUDIO_DIR = Path(config.audio_dir)

class BroadcastJob:
    """방송 작업 클래스"""
    def __init__(self, job_type, params, job_id=None):
        self.job_type = job_type  # 'audio' or 'text'
        self.params = params
        self.job_id = job_id or f"job_{int(time.time() * 1000)}"
        self.estimated_duration = self._calculate_duration()
        self.created_at = datetime.datetime.now()
        
    def _calculate_duration(self):
        """작업의 예상 소요 시간 계산 (초 단위)"""
        if self.job_type == 'audio':
            audio_path = self.params.get('audio_path')
            duration = self.params.get('duration')
            
            if duration:
                return duration
            
            if audio_path:
                try:
                    audio_path = Path(audio_path)
                    if audio_path.exists() and audio_path.suffix.lower() in ['.wav']:
                        with wave.open(str(audio_path), 'rb') as wav_file:
                            frames = wav_file.getnframes()
                            rate = wav_file.getframerate()
                            return frames / rate
                    else:
                        return 30  # 기본값
                except Exception as e:
                    logger.warning(f"오디오 파일 길이 확인 실패: {e}")
                    return 30
            else:
                return 30
                
        elif self.job_type == 'text':
            text = self.params.get('text', '')
            estimated_chars = len(text)
            return max(3, estimated_chars * 0.3)  # 최소 3초
            
        return 30  # 기본값

class BroadcastController:
    """
    방송 제어 시스템 컨트롤러 클래스 - BroadcastManager 중심으로 단순화
    """
    def __init__(self, target_ip=None, target_port=None, interface=None):
        """
        초기화 함수 - BroadcastManager 중심으로 단순화
        
        Parameters:
        -----------
        target_ip : str
            대상 방송 장비 IP
        target_port : int
            대상 방송 장비 포트
        interface : str
            사용할 네트워크 인터페이스 (현재 미사용)
        """
        # BroadcastManager 초기화 (네트워크 설정 포함)
        if target_ip or target_port:
            # 사용자 지정 IP/포트로 새 BroadcastManager 생성
            from .broadcast_manager import BroadcastManager
            self.broadcast_manager = BroadcastManager(
                target_ip=target_ip or "192.168.0.200",
                target_port=target_port or 22000
            )
        else:
            # 기본 설정 사용
            self.broadcast_manager = broadcast_manager
        
        # DeviceMapper 초기화
        from ..core.device_mapping import DeviceMapper
        self.device_mapper = DeviceMapper()
        
        # 오디오 재생 관련 속성
        self.player = None
        self.is_playing = False
        self.broadcast_thread = None
        
        # TTS 모델 속성
        self.tts_model = None
        self.tts_initialized = False
        
        # 방송 작업 관리
        self.broadcast_jobs = []
        self.current_broadcast_start_time = None
        self.current_broadcast_duration = None
        
        self.broadcast_queue = queue.Queue()
        self.broadcast_worker_thread = threading.Thread(target=self._broadcast_worker, daemon=True)
        self.broadcast_worker_thread.start()
        
        # 스케줄러 초기화 (필요시)
        self._broadcast_scheduler = None
        
        print(f"[*] BroadcastController 초기화 완료 - BroadcastManager 사용")
    
    def _device_name_to_coordinates(self, device_name):
        """
        장치명을 행/열 좌표로 변환
        
        Parameters:
        -----------
        device_name : str
            장치명 (예: "1-1", "3-2")
            
        Returns:
        --------
        tuple
            (row, col) 또는 (None, None)
        """
        try:
            # 학년-반 형식 (예: "1-1", "3-2")
            if '-' in device_name and device_name[0].isdigit():
                grade, class_num = device_name.split('-')
                row = int(grade)
                col = int(class_num)
                
                # 좌표 유효성 검사
                if 1 <= row <= 4 and 1 <= col <= 16:
                    return row, col
                else:
                    print(f"[!] 좌표 범위 초과: ({row}, {col})")
                    return None, None
            else:
                print(f"[!] 지원되지 않는 장치명 형식: {device_name}")
                return None, None
                    
        except Exception as e:
            print(f"[!] 장치명 변환 중 오류: {e}")
            return None, None
    
    def get_version(self):
        """앱 버전 정보 반환"""
        return config.app_version
    
    def print_system_info(self):
        """시스템 정보 출력"""
        print(f"[*] 방송 제어 시스템 정보:")
        print(f"    - 버전: {config.app_version}")
        summary = self.broadcast_manager.get_status_summary()
        print(f"    - 대상 IP: {summary['target_ip']}")
        print(f"    - 대상 포트: {summary['target_port']}")
        print(f"    - 전체 장치: {summary['total_devices']}개")
        print(f"    - 활성화된 장치: {summary['active_count']}개")
    
    def control_device_single(self, device_name, state=1):
        """
        장치 제어 (BroadcastManager 사용)
        
        Parameters:
        -----------
        device_name : str
            제어할 장치명 (예: "1-1")
        state : int
            0: 끄기, 1: 켜기
            
        Returns:
        --------
        bool
            성공 여부
        """
        print(f"[*] 장치 제어 (BroadcastManager): {device_name}, 상태: {'켜기' if state else '끄기'}")
        
        try:
            # 장치 이름을 행/열 좌표로 변환
            row, col = self._device_name_to_coordinates(device_name)
            if row is None or col is None:
                print(f"[!] 장치명을 좌표로 변환 실패: {device_name}")
                return False
            
            # BroadcastManager를 통해 장치 제어
            if state:
                success = self.broadcast_manager.turn_on_device(row, col)
            else:
                success = self.broadcast_manager.turn_off_device(row, col)
            
            return success
            
        except Exception as e:
            print(f"[!] 장치 제어 중 오류: {e}")
            return False
    
    def control_device(self, device_name, state=1):
        """기본 장치 제어 (control_device_single과 동일)"""
        return self.control_device_single(device_name, state)
    
    def control_multiple_devices(self, device_list, state=1):
        """
        여러 장치 동시 제어 - BroadcastManager 사용
        
        Parameters:
        -----------
        device_list : list
            제어할 장치명 리스트 (예: ["1-1", "1-2", "2-1"])
        state : int
            0: 끄기, 1: 켜기
            
        Returns:
        --------
        bool
            성공 여부
        """
        print(f"[*] 여러 장치 제어 (BroadcastManager): {', '.join(map(str, device_list))}, 상태: {'켜기' if state else '끄기'}")
        
        try:
            # 장치 목록을 방 ID 집합으로 변환
            target_rooms = set()
            
            for device_name in device_list:
                try:
                    # 숫자 ID인 경우
                    if isinstance(device_name, int):
                        room_id = device_name
                    # 문자열 처리
                    elif isinstance(device_name, str):
                        if device_name.isdigit():
                            room_id = int(device_name)
                        elif '-' in device_name and device_name[0].isdigit():
                            grade, class_num = device_name.split('-')
                            room_id = int(grade) * 100 + int(class_num)
                        else:
                            print(f"[!] 지원되지 않는 장치명: {device_name}")
                            continue
                    else:
                        print(f"[!] 지원되지 않는 데이터 타입: {type(device_name)}")
                        continue
                    
                    # 좌표 유효성 검사
                    row = room_id // 100
                    col = room_id % 100
                    if 1 <= row <= 4 and 1 <= col <= 16:
                        target_rooms.add(room_id)
                    else:
                        print(f"[!] 잘못된 방 ID: {room_id}")
                        
                except Exception as e:
                    print(f"[!] 장치 처리 중 오류 ({device_name}): {e}")
                    continue
            
            # BroadcastManager를 통해 상태 설정
            if state:
                # 켜기: 현재 활성 방들과 새로운 방들을 합침
                current_active = self.broadcast_manager.get_active_rooms()
                all_active_rooms = current_active.union(target_rooms)
                success = self.broadcast_manager.set_active_rooms(all_active_rooms)
            else:
                # 끄기: 현재 활성 방에서 target_rooms를 제거
                current_active = self.broadcast_manager.get_active_rooms()
                remaining_rooms = current_active - target_rooms
                success = self.broadcast_manager.set_active_rooms(remaining_rooms)
            
            if success:
                print(f"[*] 다중 장치 제어 완료: {sorted(target_rooms) if state else sorted(current_active - remaining_rooms)}")
            
            return success
            
        except Exception as e:
            print(f"[!] 다중 장치 제어 중 오류: {e}")
            return False
    
    def test_connection(self):
        """네트워크 연결 테스트"""
        return self.broadcast_manager.test_connection()
    
    def get_status_summary(self):
        """시스템 상태 요약"""
        return self.broadcast_manager.get_status_summary()
    
    def print_status_matrix(self):
        """장치 매트릭스 상태 출력"""
        self.broadcast_manager.print_status_matrix()
    
    # TTS 관련 메서드들
    def initialize_tts(self, language="ko"):
        """TTS 시스템 초기화"""
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
        """텍스트를 음성으로 변환"""
        try:
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
            
            # 텍스트 내용 로깅
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
    
    # 오디오 재생 관련 메서드들 (기존 코드 유지)
    def play_audio(self, audio_path):
        """오디오 파일 재생"""
        try:
            audio_path = Path(audio_path)
            if not audio_path.exists():
                print(f"[!] 오류: 오디오 파일이 존재하지 않습니다: {audio_path}")
                return False
            
            if self.is_playing and hasattr(self, 'player'):
                print("[*] 이미 재생 중인 오디오가 있습니다. 중지 후 새로운 오디오를 재생합니다.")
                self.stop_audio()
            
            print(f"[*] 오디오 파일 재생 준비: {audio_path}")
            
            # VLC를 사용해 재생 시도
            try:
                import vlc
                
                # VLC 인스턴스 초기화
                vlc_instance = vlc.Instance('--no-audio-time-stretch', '--audio-resampler=soxr', '--no-video')
                self.player = vlc_instance.media_player_new()
                media = vlc_instance.media_new(str(audio_path))
                
                # 종료 이벤트 관리
                self.playback_finished = False
                
                def handle_end_event(event):
                    if event.u.new_state in [vlc.State.Ended, vlc.State.Error, vlc.State.Stopped]:
                        self.playback_finished = True
                        print(f"[*] VLC 이벤트: 미디어 재생 완료")
                
                event_manager = media.event_manager()
                event_manager.event_attach(vlc.EventType.MediaStateChanged, handle_end_event)
                
                self.player.set_media(media)
                self.player.audio_set_volume(100)
                self.is_playing = True
                
                play_result = self.player.play()
                
                if play_result == 0:
                    print(f"[*] 오디오 재생 시작 (VLC 사용): {audio_path}")
                    time.sleep(0.5)
                    
                    if self.player.get_state() in [vlc.State.Playing, vlc.State.Opening]:
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
                
            print("[!] 모든 오디오 재생 방법이 실패했습니다.")
            return False
                
        except Exception as e:
            print(f"[!] 오디오 재생 중 오류 발생: {e}")
            traceback.print_exc()
            return False
    
    def stop_audio(self):
        """현재 재생 중인 오디오를 중지합니다."""
        if not self.is_playing:
            print("[*] 중지할 오디오가 없습니다.")
            return True
            
        print("[*] 오디오 재생을 중지합니다...")
        
        try:
            import vlc
            if hasattr(self, 'player') and isinstance(self.player, vlc.MediaPlayer):
                try:
                    self.player.stop()
                    time.sleep(0.1)
                    
                    media = self.player.get_media()
                    if media:
                        try:
                            media.release()
                        except:
                            pass
                    
                    try:
                        self.player.release()
                    except:
                        if hasattr(self, 'player'):
                            self.player = None
                            
                    print("[*] VLC 오디오 재생이 중지되었습니다.")
                    
                except Exception as e:
                    print(f"[!] VLC 플레이어 중지 중 오류: {e}")
                    if hasattr(self, 'player'):
                        self.player = None
                
                self.is_playing = False
                return True
                
        except Exception as e:
            print(f"[!] 오디오 중지 중 오류 발생: {e}")
            self.is_playing = False
            if hasattr(self, 'player'):
                self.player = None
            return False
    
    def _monitor_vlc_playback(self):
        """VLC 재생 상태를 모니터링하는 스레드 함수"""
        try:
            import vlc
            if not hasattr(self, 'player') or not isinstance(self.player, vlc.MediaPlayer):
                return
            
            while self.is_playing:
                try:
                    state = self.player.get_state()
                    
                    if state in [vlc.State.Ended, vlc.State.Stopped, vlc.State.Error]:
                        print(f"[*] VLC 재생 완료 감지 (상태: {state})")
                        self.playback_finished = True
                        self.is_playing = False
                        break
                except Exception as e:
                    print(f"[!] VLC 상태 확인 중 오류: {e}")
                    time.sleep(1)
                    continue
                
                time.sleep(0.5)
                
        except Exception as e:
            print(f"[!] VLC 모니터링 스레드 오류: {e}")
            self.playback_finished = True
            self.is_playing = False
    
    def _check_playback_finished(self):
        """재생 완료 여부를 확인합니다"""
        if hasattr(self, 'playback_finished') and self.playback_finished:
            return True
            
        if not self.is_playing:
            return True
            
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
            
        return False
    
    # 방송 큐 관련 메서드들
    def broadcast_audio(self, audio_path, target_devices, end_devices=None, duration=None):
        """오디오 방송을 큐에 추가"""
        job = BroadcastJob('audio', {
            'audio_path': audio_path,
            'target_devices': target_devices,
            'end_devices': end_devices,
            'duration': duration
        })
        
        self.broadcast_queue.put(job)
        self.broadcast_jobs.append(job)
        
        queue_position = len(self.broadcast_jobs)
        estimated_start_time = self._calculate_estimated_start_time(queue_position)
        
        return {
            "status": "queued", 
            "queue_size": queue_position,
            "queue_position": queue_position,
            "estimated_start_time": estimated_start_time,
            "estimated_duration": job.estimated_duration,
            "message": f"방송이 대기열 {queue_position}번째에 추가되었습니다."
        }
    
    def broadcast_text(self, text, target_devices, end_devices=None, language="ko"):
        """텍스트 방송을 큐에 추가"""
        job = BroadcastJob('text', {
            'text': text,
            'target_devices': target_devices,
            'end_devices': end_devices,
            'language': language
        })
        
        self.broadcast_queue.put(job)
        self.broadcast_jobs.append(job)
        
        queue_position = len(self.broadcast_jobs)
        estimated_start_time = self._calculate_estimated_start_time(queue_position)
        
        return {
            "status": "queued", 
            "queue_size": queue_position,
            "queue_position": queue_position,
            "estimated_start_time": estimated_start_time,
            "estimated_duration": job.estimated_duration,
            "message": f"방송이 대기열 {queue_position}번째에 추가되었습니다."
        }
    
    def _calculate_estimated_start_time(self, queue_position):
        """큐 순서에 따른 예상 시작시간 계산"""
        import datetime
        
        now = datetime.datetime.now()
        total_estimated_duration = 0
        
        # 현재 재생 중인 방송의 남은 시간
        if self.is_playing and self.current_broadcast_start_time and self.current_broadcast_duration:
            elapsed_time = (datetime.datetime.now() - self.current_broadcast_start_time).total_seconds()
            remaining_current_broadcast = max(0, self.current_broadcast_duration - elapsed_time)
            total_estimated_duration += remaining_current_broadcast
        
        # 큐에 있는 작업들의 예상 소요시간
        for i in range(queue_position - 1):
            if i < len(self.broadcast_jobs):
                total_estimated_duration += self.broadcast_jobs[i].estimated_duration
        
        estimated_start = now + datetime.timedelta(seconds=total_estimated_duration)
        return estimated_start.strftime("%H:%M:%S")
    
    def _do_broadcast_audio(self, audio_path, target_devices, end_devices=None, duration=None):
        """오디오 방송 실행"""
        try:
            if not os.path.exists(audio_path):
                logger.error(f"오디오 파일을 찾을 수 없음: {audio_path}")
                return False

            print(f"[*] 오디오 방송 시작: {audio_path}")
            print(f"[*] 대상 장치: {target_devices}")

            # end_devices가 지정되지 않으면 target_devices와 동일하게 설정 (방송 후 자동 끄기)
            if end_devices is None:
                end_devices = target_devices
                print(f"[*] 방송 완료 후 자동으로 끌 장치: {end_devices}")

            # 1. 대상 장치 활성화
            print(f"[*] 1단계: 대상 장치 활성화 시작...")
            success = self.control_multiple_devices(target_devices, 1)
            if not success:
                logger.error("장치 활성화 실패")
                return False
            print(f"[*] 1단계: 대상 장치 활성화 완료")

            # 2. 오디오 재생
            print(f"[*] 2단계: 오디오 재생 시작...")
            success = self.play_audio(str(audio_path))
            if not success:
                logger.error("오디오 재생 실패")
                print(f"[*] 재생 실패로 인한 장치 끄기 시작: {end_devices}")
                self._force_turn_off_devices(end_devices)
                return False
            print(f"[*] 2단계: 오디오 재생 시작 완료")

            # 3. 재생 완료 대기
            max_wait = duration if duration else 120
            start_time = time.time()
            
            print(f"[*] 3단계: 재생 완료 대기 중... (최대 {max_wait}초)")
            while not self._check_playback_finished():
                time.sleep(0.5)
                if time.time() - start_time > max_wait:
                    print("[!] 재생 완료 대기 타임아웃, 강제 종료합니다.")
                    break

            # 4. 재생 중지
            print(f"[*] 4단계: 오디오 재생 중지...")
            self.stop_audio()
            print("[*] 4단계: 오디오 재생 중지 완료")

            # 5. 종료 후 대기
            print(f"[*] 5단계: 종료 후 대기 (0.5초)...")
            time.sleep(0.5)

            # 6. 종료 장치 비활성화 (방송 완료 후 자동으로 장치 끄기)
            if end_devices:
                print(f"[*] 6단계: 방송 완료 - 장치 끄기 시작: {end_devices}")
                success = self._force_turn_off_devices(end_devices)
                if success:
                    print(f"[*] 6단계: 장치 끄기 완료: {end_devices}")
                else:
                    print(f"[!] 6단계: 장치 끄기 실패: {end_devices}")

            print("[*] 오디오 방송 완료")
            return True

        except Exception as e:
            logger.exception("오디오 방송 실행 중 오류")
            print(f"[!] 방송 실행 중 예외 발생: {e}")
            try:
                self.stop_audio()
                if end_devices:
                    print(f"[*] 예외 발생으로 인한 장치 끄기: {end_devices}")
                    self._force_turn_off_devices(end_devices)
            except Exception as cleanup_error:
                print(f"[!] 정리 작업 중 오류: {cleanup_error}")
            return False
    
    def _force_turn_off_devices(self, device_list):
        """
        장치를 강제로 끄는 메서드 (여러 번 시도)
        
        Parameters:
        -----------
        device_list : list
            끌 장치 목록
            
        Returns:
        --------
        bool
            성공 여부
        """
        if not device_list:
            print("[*] 끌 장치가 없습니다.")
            return True
            
        print(f"[*] 장치 강제 끄기 시작: {device_list}")
        
        # 최대 3번 시도
        for attempt in range(3):
            try:
                print(f"[*] 장치 끄기 시도 {attempt + 1}/3...")
                
                # BroadcastManager를 통한 장치 끄기
                success = self.control_multiple_devices(device_list, 0)
                
                if success:
                    print(f"[*] 장치 끄기 성공 (시도 {attempt + 1}/3)")
                    
                    # 상태 확인
                    time.sleep(0.2)
                    active_rooms = self.broadcast_manager.get_active_rooms()
                    print(f"[*] 현재 활성화된 방: {sorted(active_rooms)}")
                    
                    return True
                else:
                    print(f"[!] 장치 끄기 실패 (시도 {attempt + 1}/3)")
                    
            except Exception as e:
                print(f"[!] 장치 끄기 시도 {attempt + 1}/3 중 오류: {e}")
            
            # 재시도 전 대기
            if attempt < 2:
                time.sleep(0.5)
        
        # 모든 시도 실패 시 최후 수단으로 모든 장치 끄기
        print("[!] 모든 시도 실패, 최후 수단으로 모든 장치 끄기 시도...")
        try:
            success = self.broadcast_manager.turn_off_all_devices()
            if success:
                print("[*] 모든 장치 끄기 성공")
                return True
            else:
                print("[!] 모든 장치 끄기 실패")
                return False
        except Exception as e:
            print(f"[!] 모든 장치 끄기 중 오류: {e}")
            return False
    
    def _do_broadcast_text(self, text, target_devices, end_devices=None, language="ko"):
        """TTS 방송 실행"""
        try:
            print(f"[*] TTS 방송 시작: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            print(f"[*] 대상 장치: {target_devices}")
            print(f"[*] 언어: {language}")

            # 1. TTS 오디오 생성
            print("[*] TTS 오디오 생성 중...")
            audio_path = self.generate_speech(text, language=language)
            if not audio_path:
                logger.error("TTS 오디오 생성 실패")
                return False

            print(f"[*] TTS 오디오 생성 완료: {audio_path}")

            # 2. 오디오 방송 실행
            return self._do_broadcast_audio(
                audio_path=audio_path,
                target_devices=target_devices,
                end_devices=end_devices
            )

        except Exception as e:
            logger.exception("TTS 방송 실행 중 오류")
            return False
    
    def stop_broadcast(self):
        """현재 실행 중인 방송 중지"""
        try:
            print("[*] 방송 강제 종료 시작...")
            
            # 1. 오디오 재생 중지
            print("[*] 1단계: 오디오 재생 중지...")
            self.stop_audio()
            print("[*] 1단계: 오디오 재생 중지 완료")
            
            # 2. 방송 큐 비우기
            print("[*] 2단계: 방송 큐 정리...")
            queue_size = self.broadcast_queue.qsize()
            while not self.broadcast_queue.empty():
                try:
                    self.broadcast_queue.get_nowait()
                    self.broadcast_queue.task_done()
                except queue.Empty:
                    break
            print(f"[*] 2단계: 방송 큐 정리 완료 ({queue_size}개 작업 제거)")
            
            # 3. 방송 작업 목록 비우기
            print("[*] 3단계: 방송 작업 목록 정리...")
            jobs_count = len(self.broadcast_jobs)
            self.broadcast_jobs.clear()
            print(f"[*] 3단계: 방송 작업 목록 정리 완료 ({jobs_count}개 작업 제거)")
            
            # 4. BroadcastManager를 통해 모든 장치 끄기
            print("[*] 4단계: 모든 장치 끄기...")
            success = self.broadcast_manager.turn_off_all_devices()
            if success:
                print("[*] 4단계: BroadcastManager를 통한 모든 장치 끄기 완료")
                
                # 상태 확인
                time.sleep(0.2)
                active_rooms = self.broadcast_manager.get_active_rooms()
                if active_rooms:
                    print(f"[!] 경고: 여전히 활성화된 방이 있습니다: {sorted(active_rooms)}")
                    # 추가 시도
                    print("[*] 추가 시도로 모든 장치 끄기...")
                    retry_success = self.broadcast_manager.turn_off_all_devices()
                    if retry_success:
                        print("[*] 추가 시도 성공")
                    else:
                        print("[!] 추가 시도 실패")
                else:
                    print("[*] 모든 장치가 성공적으로 꺼졌습니다.")
            else:
                print("[!] 4단계: BroadcastManager를 통한 장치 끄기 실패")
                # 최후 수단으로 다시 시도
                print("[*] 최후 수단으로 다시 시도...")
                final_success = self.broadcast_manager.turn_off_all_devices()
                if final_success:
                    print("[*] 최후 수단 성공")
                else:
                    print("[!] 최후 수단 실패")
            
            # 5. 현재 방송 상태 초기화
            print("[*] 5단계: 방송 상태 초기화...")
            self.current_broadcast_start_time = None
            self.current_broadcast_duration = None
            print("[*] 5단계: 방송 상태 초기화 완료")
            
            print("[*] 방송 강제 종료 완료")
            logger.info("방송 강제 종료 완료")
            return True
            
        except Exception as e:
            print(f"[!] 방송 중지 중 오류: {e}")
            logger.exception(f"방송 중지 중 오류: {e}")
            
            # 오류 발생 시에도 장치 끄기 시도
            try:
                print("[*] 오류 발생으로 인한 장치 끄기 시도...")
                self.broadcast_manager.turn_off_all_devices()
            except Exception as cleanup_error:
                print(f"[!] 정리 작업 중 오류: {cleanup_error}")
            
            return False

    def _broadcast_worker(self):
        """방송 작업 처리 워커 스레드"""
        while True:
            job = self.broadcast_queue.get()
            try:
                # 현재 방송 시작 시간과 예상 길이 기록
                self.current_broadcast_start_time = datetime.datetime.now()
                self.current_broadcast_duration = job.estimated_duration
                
                if job.job_type == 'audio':
                    self._do_broadcast_audio(**job.params)
                elif job.job_type == 'text':
                    self._do_broadcast_text(**job.params)
                
                # 작업 완료 후 목록에서 제거
                if job in self.broadcast_jobs:
                    self.broadcast_jobs.remove(job)
                
                # 현재 방송 상태 초기화
                self.current_broadcast_start_time = None
                self.current_broadcast_duration = None
                
            except Exception as e:
                logger.error(f"방송 작업 처리 중 오류: {e}")
                if job in self.broadcast_jobs:
                    self.broadcast_jobs.remove(job)
            finally:
                self.broadcast_queue.task_done()

# 싱글톤 인스턴스 생성
broadcast_controller = BroadcastController()
#!/usr/bin/env python3
"""
방송 제어 컨트롤러 모듈 - BroadcastManager 중심으로 단순화
방송 시스템 전체 제어를 담당합니다.
"""
import os
import time
import threading
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
import hashlib
import shutil
import asyncio
from concurrent.futures import ThreadPoolExecutor

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

from ..core.config import config, setup_logging
from .broadcast_manager import broadcast_manager

# 중앙 로깅 설정 사용
logger = setup_logging(__name__)

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
        
        # 시작/끝 신호음 파일 경로
        self.start_signal_path = Path(config.data_dir) / "start.mp3"
        self.end_signal_path = Path(config.data_dir) / "end.mp3"
        
        # 프리뷰 관리
        self.preview_dir = Path("D:/previews")
        print(f"[*] 프리뷰 디렉토리 설정: {self.preview_dir}")
        print(f"[*] 프리뷰 디렉토리 절대 경로: {self.preview_dir.absolute()}")
        
        try:
            self.preview_dir.mkdir(exist_ok=True)
            print(f"[*] 프리뷰 디렉토리 생성/확인 완료: {self.preview_dir}")
        except Exception as e:
            print(f"[!] 프리뷰 디렉토리 생성 실패: {e}")
        
        self.pending_previews = {}  # preview_id -> preview_info
        
        # 프리뷰 생성용 스레드 풀 (병렬 처리용)
        self.preview_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="preview_worker")
        print(f"[*] 프리뷰 생성 스레드 풀 초기화 완료 (최대 4개 동시 처리)")
        
        # 장치 상태 저장 및 복원 기능
        self.device_state_backup = {}  # 방송 전 장치 상태 저장
        self.restore_device_states_enabled = True  # 방송 후 상태 복원 여부 (기본값: True)
        
        print(f"[*] BroadcastController 초기화 완료 - BroadcastManager 사용")
        print(f"[*] 시작 신호음: {self.start_signal_path}")
        print(f"[*] 끝 신호음: {self.end_signal_path}")
        print(f"[*] 프리뷰 디렉토리: {self.preview_dir}")
        print(f"[*] 장치 상태 복원 기능: {'활성화' if self.restore_device_states_enabled else '비활성화'}")
    
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
            
            # 출력 경로가 지정되지 않았으면 자동 생성 (temp 디렉토리 사용)
            if output_path is None:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                # temp 디렉토리에 임시 TTS 파일 생성
                output_path = Path(config.temp_dir) / f"audio_{timestamp}_tts.wav"
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
            
            return str(result_path)
            
        except Exception as e:
            logger.error(f"음성 생성 중 오류: {e}")
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
                print("[*] 이미 재생 중인 오디오가 있습니다. 큐에서 대기 중입니다.")
                return False
            
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
    def broadcast_audio(self, audio_path, target_devices, end_devices=None, duration=None, skip_signals=False):
        """오디오 방송을 큐에 추가"""
        job = BroadcastJob('audio', {
            'audio_path': audio_path,
            'target_devices': target_devices,
            'end_devices': end_devices,
            'duration': duration,
            'skip_signals': skip_signals
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
    
    def _do_broadcast_audio(self, audio_path, target_devices, end_devices=None, duration=None, skip_signals=False):
        """오디오 방송 실행"""
        try:
            if not os.path.exists(audio_path):
                logger.error(f"오디오 파일을 찾을 수 없음: {audio_path}")
                return False

            print(f"[*] 오디오 방송 시작: {audio_path}")
            print(f"[*] 대상 장치: {target_devices}")
            if skip_signals:
                print(f"[*] 프리뷰 파일 재생 모드 (시작음/끝음 건너뜀)")

            # end_devices가 지정되지 않으면 target_devices와 동일하게 설정 (방송 후 자동 끄기)
            if end_devices is None:
                end_devices = target_devices
                print(f"[*] 방송 완료 후 자동으로 끌 장치: {end_devices}")

            # 0. 방송 전 장치 상태 저장 (복원 기능이 활성화된 경우)
            if self.restore_device_states_enabled:
                print(f"[*] 0단계: 방송 전 장치 상태 저장...")
                self.save_device_states(target_devices)
                print(f"[*] 0단계: 장치 상태 저장 완료")

            # 1. 대상 장치 활성화
            print(f"[*] 1단계: 대상 장치 활성화 시작...")
            success = self.control_multiple_devices(target_devices, 1)
            if not success:
                logger.error("장치 활성화 실패")
                return False
            print(f"[*] 1단계: 대상 장치 활성화 완료")

            # 2. 시작 신호음 재생 (프리뷰 파일이 아닌 경우에만)
            if not skip_signals:
                print(f"[*] 2단계: 시작 신호음 재생...")
                if self.play_start_signal():
                    # 시작 신호음 재생 완료 대기
                    while not self._check_playback_finished():
                        time.sleep(0.1)
                    self.stop_audio()
                    print(f"[*] 2단계: 시작 신호음 재생 완료")
                else:
                    print(f"[*] 2단계: 시작 신호음 재생 건너뜀")
            else:
                print(f"[*] 2단계: 시작 신호음 재생 건너뜀 (프리뷰 파일)")

            # 3. 메인 오디오 재생
            print(f"[*] 3단계: 메인 오디오 재생 시작...")
            success = self.play_audio(str(audio_path))
            if not success:
                logger.error("오디오 재생 실패")
                print(f"[*] 재생 실패로 인한 장치 끄기 시작: {end_devices}")
                self._force_turn_off_devices(end_devices)
                return False
            print(f"[*] 3단계: 메인 오디오 재생 시작 완료")

            # 4. 재생 완료 대기
            print(f"[*] 4단계: 재생 완료 대기 중...")
            while not self._check_playback_finished():
                time.sleep(0.5)

            # 5. 재생 중지
            print(f"[*] 5단계: 메인 오디오 재생 중지...")
            self.stop_audio()
            print("[*] 5단계: 메인 오디오 재생 중지 완료")

            # 6. 끝 신호음 재생 (프리뷰 파일이 아닌 경우에만)
            if not skip_signals:
                print(f"[*] 6단계: 끝 신호음 재생...")
                if self.play_end_signal():
                    # 끝 신호음 재생 완료 대기
                    while not self._check_playback_finished():
                        time.sleep(0.1)
                    self.stop_audio()
                    print(f"[*] 6단계: 끝 신호음 재생 완료")
                else:
                    print(f"[*] 6단계: 끝 신호음 재생 건너뜀")
            else:
                print(f"[*] 6단계: 끝 신호음 재생 건너뜀 (프리뷰 파일)")

            # 7. 종료 후 대기
            print(f"[*] 7단계: 종료 후 대기 (0.5초)...")
            time.sleep(0.5)

            # 8. 장치 상태 처리
            if self.restore_device_states_enabled:
                # 8a. 저장된 상태로 복원
                print(f"[*] 8단계: 장치 상태 복원 시작...")
                self.restore_device_states(target_devices)
                print(f"[*] 8단계: 장치 상태 복원 완료")
            else:
                # 8b. 기존 방식: 종료 장치 비활성화 (방송 완료 후 자동으로 장치 끄기)
                if end_devices:
                    print(f"[*] 8단계: 방송 완료 - 장치 끄기 시작: {end_devices}")
                    success = self._force_turn_off_devices(end_devices)
                    if success:
                        print(f"[*] 8단계: 장치 끄기 완료: {end_devices}")
                    else:
                        print(f"[!] 8단계: 장치 끄기 실패: {end_devices}")

            print("[*] 오디오 방송 완료")
            return True

        except Exception as e:
            logger.exception("오디오 방송 실행 중 오류")
            print(f"[!] 방송 실행 중 예외 발생: {e}")
            try:
                self.stop_audio()
                if self.restore_device_states_enabled:
                    # 예외 발생 시에도 상태 복원 시도
                    print(f"[*] 예외 발생으로 인한 장치 상태 복원 시도...")
                    self.restore_device_states(target_devices)
                elif end_devices:
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
        """텍스트 방송 실행"""
        try:
            print(f"[*] 텍스트 방송 시작: {text[:50]}{'...' if len(text) > 50 else ''}")
            print(f"[*] 대상 장치: {target_devices}")

            # end_devices가 지정되지 않으면 target_devices와 동일하게 설정
            if end_devices is None:
                end_devices = target_devices
                print(f"[*] 방송 완료 후 자동으로 끌 장치: {end_devices}")

            # 0. 방송 전 장치 상태 저장 (복원 기능이 활성화된 경우)
            if self.restore_device_states_enabled:
                print(f"[*] 0단계: 방송 전 장치 상태 저장...")
                self.save_device_states(target_devices)
                print(f"[*] 0단계: 장치 상태 저장 완료")

            # 1. TTS 오디오 생성
            print(f"[*] 1단계: TTS 오디오 생성...")
            tts_audio_path = self.generate_speech(text, language=language)
            if not tts_audio_path:
                logger.error("TTS 오디오 생성 실패")
                return False
            print(f"[*] 1단계: TTS 오디오 생성 완료: {tts_audio_path}")

            # 2. 대상 장치 활성화
            print(f"[*] 2단계: 대상 장치 활성화 시작...")
            success = self.control_multiple_devices(target_devices, 1)
            if not success:
                logger.error("장치 활성화 실패")
                return False
            print(f"[*] 2단계: 대상 장치 활성화 완료")

            # 3. 시작 신호음 재생
            print(f"[*] 3단계: 시작 신호음 재생...")
            if self.play_start_signal():
                # 시작 신호음 재생 완료 대기
                while not self._check_playback_finished():
                    time.sleep(0.1)
                self.stop_audio()
                print(f"[*] 3단계: 시작 신호음 재생 완료")
            else:
                print(f"[*] 3단계: 시작 신호음 재생 건너뜀")

            # 4. TTS 오디오 재생
            print(f"[*] 4단계: TTS 오디오 재생 시작...")
            success = self.play_audio(str(tts_audio_path))
            if not success:
                logger.error("TTS 오디오 재생 실패")
                print(f"[*] 재생 실패로 인한 장치 끄기 시작: {end_devices}")
                self._force_turn_off_devices(end_devices)
                return False
            print(f"[*] 4단계: TTS 오디오 재생 시작 완료")

            # 5. 재생 완료 대기
            print(f"[*] 5단계: 재생 완료 대기 중...")
            while not self._check_playback_finished():
                time.sleep(0.5)

            # 6. 재생 중지
            print(f"[*] 6단계: TTS 오디오 재생 중지...")
            self.stop_audio()
            print("[*] 6단계: TTS 오디오 재생 중지 완료")

            # 7. 끝 신호음 재생
            print(f"[*] 7단계: 끝 신호음 재생...")
            if self.play_end_signal():
                # 끝 신호음 재생 완료 대기
                while not self._check_playback_finished():
                    time.sleep(0.1)
                self.stop_audio()
                print(f"[*] 7단계: 끝 신호음 재생 완료")
            else:
                print(f"[*] 7단계: 끝 신호음 재생 건너뜀")

            # 8. 종료 후 대기
            print(f"[*] 8단계: 종료 후 대기 (0.5초)...")
            time.sleep(0.5)

            # 9. 장치 상태 처리
            if self.restore_device_states_enabled:
                # 9a. 저장된 상태로 복원
                print(f"[*] 9단계: 장치 상태 복원 시작...")
                self.restore_device_states(target_devices)
                print(f"[*] 9단계: 장치 상태 복원 완료")
            else:
                # 9b. 기존 방식: 종료 장치 비활성화
                if end_devices:
                    print(f"[*] 9단계: 방송 완료 - 장치 끄기 시작: {end_devices}")
                    success = self._force_turn_off_devices(end_devices)
                    if success:
                        print(f"[*] 9단계: 장치 끄기 완료: {end_devices}")
                    else:
                        print(f"[!] 9단계: 장치 끄기 실패: {end_devices}")

            print("[*] 텍스트 방송 완료")
            return True

        except Exception as e:
            logger.exception("텍스트 방송 실행 중 오류")
            print(f"[!] 방송 실행 중 예외 발생: {e}")
            try:
                self.stop_audio()
                if self.restore_device_states_enabled:
                    # 예외 발생 시에도 상태 복원 시도
                    print(f"[*] 예외 발생으로 인한 장치 상태 복원 시도...")
                    self.restore_device_states(target_devices)
                elif end_devices:
                    print(f"[*] 예외 발생으로 인한 장치 끄기: {end_devices}")
                    self._force_turn_off_devices(end_devices)
            except Exception as cleanup_error:
                print(f"[!] 정리 작업 중 오류: {cleanup_error}")
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
                    # skip_signals 파라미터 추출
                    skip_signals = job.params.get('skip_signals', False)
                    # skip_signals를 별도로 전달하고 나머지는 **job.params로 전달
                    self._do_broadcast_audio(
                        audio_path=job.params['audio_path'],
                        target_devices=job.params['target_devices'],
                        end_devices=job.params.get('end_devices'),
                        duration=job.params.get('duration'),
                        skip_signals=skip_signals
                    )
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

    def get_queue_status(self):
        """큐 현황 정보 반환"""
        try:
            current_status = {
                "is_playing": self.is_playing,
                "current_broadcast": None,
                "queue_size": len(self.broadcast_jobs),
                "queue_items": []
            }
            
            # 현재 재생 중인 방송 정보
            if self.is_playing and self.current_broadcast_start_time and self.current_broadcast_duration:
                elapsed_time = (datetime.datetime.now() - self.current_broadcast_start_time).total_seconds()
                remaining_time = max(0, self.current_broadcast_duration - elapsed_time)
                
                current_status["current_broadcast"] = {
                    "start_time": self.current_broadcast_start_time.strftime("%H:%M:%S"),
                    "estimated_duration": self.current_broadcast_duration,
                    "elapsed_time": round(elapsed_time, 1),
                    "remaining_time": round(remaining_time, 1),
                    "progress_percent": round((elapsed_time / self.current_broadcast_duration) * 100, 1) if self.current_broadcast_duration > 0 else 0
                }
            
            # 큐에 있는 작업들 정보
            for i, job in enumerate(self.broadcast_jobs):
                estimated_start_time = self._calculate_estimated_start_time(i + 1)
                
                job_info = {
                    "position": i + 1,
                    "job_type": job.job_type,
                    "estimated_duration": job.estimated_duration,
                    "estimated_start_time": estimated_start_time,
                    "created_at": job.created_at.strftime("%H:%M:%S")
                }
                
                # 작업 타입별 추가 정보
                if job.job_type == 'audio':
                    job_info["audio_path"] = job.params.get('audio_path', '')
                    job_info["target_devices"] = job.params.get('target_devices', [])
                elif job.job_type == 'text':
                    text = job.params.get('text', '')
                    job_info["text"] = text[:50] + "..." if len(text) > 50 else text
                    job_info["target_devices"] = job.params.get('target_devices', [])
                    job_info["language"] = job.params.get('language', 'ko')
                
                current_status["queue_items"].append(job_info)
            
            return current_status
            
        except Exception as e:
            logger.error(f"큐 상태 확인 중 오류: {e}")
            return {"error": str(e)}
    
    def print_queue_status(self):
        """큐 현황을 콘솔에 출력"""
        status = self.get_queue_status()
        
        print("\n" + "="*60)
        print("🎵 방송 큐 현황")
        print("="*60)
        
        # 현재 재생 중인 방송
        if status["is_playing"] and status["current_broadcast"]:
            current = status["current_broadcast"]
            print(f"▶️  현재 재생 중:")
            print(f"   시작 시간: {current['start_time']}")
            print(f"   경과 시간: {current['elapsed_time']}초 / {current['estimated_duration']}초")
            print(f"   남은 시간: {current['remaining_time']}초")
            print(f"   진행률: {current['progress_percent']}%")
        else:
            print("⏸️  현재 재생 중인 방송 없음")
        
        # 큐 상태
        queue_size = status["queue_size"]
        print(f"\n📋 대기열: {queue_size}개 작업")
        
        if queue_size == 0:
            print("   대기 중인 작업 없음")
        else:
            for item in status["queue_items"]:
                print(f"\n   {item['position']}. {item['job_type'].upper()} 방송")
                print(f"      예상 시작: {item['estimated_start_time']}")
                print(f"      예상 길이: {item['estimated_duration']}초")
                print(f"      생성 시간: {item['created_at']}")
                
                if item['job_type'] == 'audio':
                    print(f"      파일: {item['audio_path']}")
                elif item['job_type'] == 'text':
                    print(f"      텍스트: {item['text']}")
                    print(f"      언어: {item['language']}")
                
                print(f"      대상 장치: {item['target_devices']}")
        
        print("="*60 + "\n")

    def play_start_signal(self):
        """방송 시작 신호음 재생"""
        if self.start_signal_path.exists():
            print(f"[*] 방송 시작 신호음 재생: {self.start_signal_path}")
            return self.play_audio(str(self.start_signal_path))
        else:
            print(f"[!] 시작 신호음 파일이 없습니다: {self.start_signal_path}")
            return False
    
    def play_end_signal(self):
        """방송 끝 신호음 재생"""
        if self.end_signal_path.exists():
            print(f"[*] 방송 끝 신호음 재생: {self.end_signal_path}")
            return self.play_audio(str(self.end_signal_path))
        else:
            print(f"[!] 끝 신호음 파일이 없습니다: {self.end_signal_path}")
            return False

    def create_preview(self, job_type, params):
        """프리뷰 생성 (병렬 처리)"""
        # 스레드 풀에서 프리뷰 생성 실행
        future = self.preview_executor.submit(self._create_preview_sync, job_type, params)
        return future.result()  # 완료될 때까지 기다림
    
    async def create_preview_async(self, job_type, params):
        """프리뷰 생성 (비동기)"""
        # 별도 스레드에서 프리뷰 생성 실행
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._create_preview_sync, job_type, params)
        return result
    
    def _create_preview_sync(self, job_type, params):
        """프리뷰 생성 (동기)"""
        try:
            import datetime
            import hashlib
            
            print(f"[프리뷰] 프리뷰 생성 시작 - job_type: {job_type}, params: {params}")
            
            # 프리뷰 ID 생성
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            params_hash = hashlib.md5(str(params).encode()).hexdigest()[:8]
            preview_id = f"{timestamp}_{params_hash}"
            
            print(f"[프리뷰] 프리뷰 ID 생성: {preview_id}")
            
            preview_info = {
                "preview_id": preview_id,
                "job_type": job_type,
                "params": params,
                "created_at": datetime.datetime.now(),
                "status": "pending"
            }
            
            # 프리뷰 오디오 생성
            print(f"[프리뷰] 프리뷰 오디오 생성 시작...")
            if job_type == 'audio':
                # 오디오 파일의 경우 시작 신호음 + 원본 오디오 + 끝 신호음으로 프리뷰 생성
                print(f"[프리뷰] 오디오 프리뷰 생성...")
                preview_path = self._create_audio_preview(preview_id, params)
            elif job_type == 'text':
                # TTS의 경우 TTS 생성 후 시작 신호음 + TTS 오디오 + 끝 신호음으로 프리뷰 생성
                print(f"[프리뷰] 텍스트 프리뷰 생성...")
                preview_path = self._create_text_preview(preview_id, params)
            else:
                raise ValueError(f"지원하지 않는 작업 타입: {job_type}")
            
            print(f"[프리뷰] 프리뷰 오디오 생성 결과: {preview_path}")
            
            if preview_path:
                preview_info["preview_path"] = preview_path
                preview_info["preview_url"] = f"/api/broadcast/preview/{preview_id}.mp3"
                preview_info["approval_endpoint"] = f"/api/broadcast/approve/{preview_id}"
                
                # 예상 길이 계산
                print(f"[프리뷰] 예상 길이 계산...")
                job = BroadcastJob(job_type, params)
                preview_info["estimated_duration"] = job.estimated_duration
                print(f"[프리뷰] 예상 길이: {job.estimated_duration}초")
                
                # 실제 프리뷰 파일 길이 측정 (ffprobe 사용)
                try:
                    actual_duration = self._get_audio_duration_with_ffprobe(preview_path)
                    if actual_duration > 0:
                        preview_info["actual_duration"] = actual_duration
                        print(f"[프리뷰] 실제 프리뷰 길이: {actual_duration:.2f}초")
                    else:
                        preview_info["actual_duration"] = None
                        print(f"[프리뷰] 실제 길이 측정 실패")
                except Exception as e:
                    preview_info["actual_duration"] = None
                    print(f"[프리뷰] 길이 측정 중 오류: {e}")
                
                # 방송 큐 상태 확인 및 예상 시간 계산
                print(f"[프리뷰] 큐 상태 확인 및 예상 시간 계산...")
                queue_status = self.get_queue_status()
                current_time = datetime.datetime.now()
                
                # 현재 진행 중인 방송이 있는지 확인
                if queue_status["current_broadcast"]:
                    current_broadcast = queue_status["current_broadcast"]
                    preview_info["queue_status"] = "waiting"
                    preview_info["current_broadcast"] = {
                        "job_type": current_broadcast.get("job_type", "unknown"),
                        "estimated_duration": current_broadcast.get("estimated_duration", 0),
                        "started_at": current_broadcast.get("started_at"),
                        "estimated_end_time": current_broadcast.get("estimated_end_time")
                    }
                    
                    # 현재 방송 종료 후 시작하므로 예상 시작 시간 = 현재 방송 종료 시간
                    estimated_start_time = current_broadcast.get("estimated_end_time")
                    if estimated_start_time:
                        preview_info["estimated_start_time"] = estimated_start_time.isoformat()
                        # 예상 종료 시간 = 시작 시간 + 방송 길이
                        if preview_info.get("actual_duration"):
                            estimated_end_time = estimated_start_time + datetime.timedelta(seconds=preview_info["actual_duration"])
                        else:
                            estimated_end_time = estimated_start_time + datetime.timedelta(seconds=preview_info["estimated_duration"])
                        preview_info["estimated_end_time"] = estimated_end_time.isoformat()
                        
                        print(f"[프리뷰] 예상 시작 시간: {estimated_start_time.strftime('%H:%M:%S')}")
                        print(f"[프리뷰] 예상 종료 시간: {estimated_end_time.strftime('%H:%M:%S')}")
                    else:
                        preview_info["estimated_start_time"] = None
                        preview_info["estimated_end_time"] = None
                        
                else:
                    # 대기 중인 방송이 있는지 확인
                    if queue_status["queue_items"]:
                        preview_info["queue_status"] = "queued"
                        # 대기 중인 방송들의 총 길이 계산
                        total_waiting_duration = sum(
                            broadcast.get("estimated_duration", 0) 
                            for broadcast in queue_status["queue_items"]
                        )
                        
                        # 예상 시작 시간 = 현재 시간 + 대기 중인 방송들의 총 길이
                        estimated_start_time = current_time + datetime.timedelta(seconds=total_waiting_duration)
                        preview_info["estimated_start_time"] = estimated_start_time.isoformat()
                        
                        # 예상 종료 시간 = 시작 시간 + 방송 길이
                        if preview_info.get("actual_duration"):
                            estimated_end_time = estimated_start_time + datetime.timedelta(seconds=preview_info["actual_duration"])
                        else:
                            estimated_end_time = estimated_start_time + datetime.timedelta(seconds=preview_info["estimated_duration"])
                        preview_info["estimated_end_time"] = estimated_end_time.isoformat()
                        
                        print(f"[프리뷰] 대기 중인 방송 수: {len(queue_status['queue_items'])}")
                        print(f"[프리뷰] 예상 시작 시간: {estimated_start_time.strftime('%H:%M:%S')}")
                        print(f"[프리뷰] 예상 종료 시간: {estimated_end_time.strftime('%H:%M:%S')}")
                    else:
                        # 즉시 시작 가능
                        preview_info["queue_status"] = "ready"
                        preview_info["estimated_start_time"] = current_time.isoformat()
                        
                        # 예상 종료 시간 = 현재 시간 + 방송 길이
                        if preview_info.get("actual_duration"):
                            estimated_end_time = current_time + datetime.timedelta(seconds=preview_info["actual_duration"])
                        else:
                            estimated_end_time = current_time + datetime.timedelta(seconds=preview_info["estimated_duration"])
                        preview_info["estimated_end_time"] = estimated_end_time.isoformat()
                        
                        print(f"[프리뷰] 즉시 시작 가능")
                        print(f"[프리뷰] 예상 종료 시간: {estimated_end_time.strftime('%H:%M:%S')}")
                
                # 대기 중인 프리뷰에 추가
                self.pending_previews[preview_id] = preview_info
                
                print(f"[*] 프리뷰 생성 완료: {preview_id}")
                return preview_info
            else:
                print(f"[프리뷰] 프리뷰 오디오 생성 실패")
                raise Exception("프리뷰 오디오 생성 실패")
                
        except Exception as e:
            print(f"[프리뷰] 프리뷰 생성 중 오류: {e}")
            import traceback
            traceback.print_exc()
            logger.error(f"프리뷰 생성 중 오류: {e}")
            return None
    
    def _create_audio_preview(self, preview_id, params):
        """오디오 방송 프리뷰 생성"""
        try:
            from pydub import AudioSegment
            import shutil
            from ..core.config import config
            
            audio_path = params.get('audio_path')
            use_original = params.get('use_original', False)  # 원본 사용 플래그
            original_preview_id = params.get('original_preview_id', '')  # 원본 프리뷰 ID
            
            if not audio_path or not Path(audio_path).exists():
                raise Exception(f"오디오 파일을 찾을 수 없음: {audio_path}")
            
            print(f"[프리뷰] 오디오 프리뷰 생성 시작 (use_original={use_original})")
            logger.info(f"[프리뷰] use_original 플래그 타입: {type(use_original)}, 값: {use_original}")
            
            # 원본 사용 플래그가 있는 경우 원본 파일을 그대로 프리뷰로 사용
            if use_original:
                print(f"[프리뷰] 원본 사용 플래그 감지: 원본 파일을 그대로 프리뷰로 사용")
                logger.info(f"[프리뷰] 원본 사용 플래그가 True입니다. 정규화 및 시작음/끝음 추가를 건너뜁니다.")
                # 원본 파일을 프리뷰 디렉토리로 복사
                preview_path = self.preview_dir / f"{preview_id}.mp3"
                print(f"[프리뷰] 프리뷰 파일 저장 경로: {preview_path}")
                print(f"[프리뷰] 프리뷰 파일 절대 경로: {preview_path.absolute()}")
                shutil.copy2(audio_path, preview_path)
                
                print(f"[*] 원본 파일을 프리뷰로 복사 완료: {preview_path}")
                logger.info(f"[프리뷰] 원본 파일 복사 완료: {audio_path} -> {preview_path}")
                return str(preview_path)
            else:
                logger.info(f"[프리뷰] use_original 플래그가 False입니다. 일반 처리로 진행합니다.")
            
            # 일반 파일 처리 (기존 로직)
            # config에서 ffmpeg 경로 가져오기
            ffmpeg_paths = config.get_ffmpeg_paths()
            ffmpeg_path = Path(ffmpeg_paths["ffmpeg_path"])
            ffprobe_path = Path(ffmpeg_paths["ffprobe_path"])
            
            if not ffmpeg_paths["ffmpeg_exists"] or not ffmpeg_paths["ffprobe_exists"]:
                print(f"[!] ffmpeg/ffprobe 파일을 찾을 수 없습니다.")
                print(f"[!] ffmpeg 경로: {ffmpeg_path}")
                print(f"[!] ffprobe 경로: {ffprobe_path}")
                # 프리뷰 없이 원본 파일 경로만 반환
                return str(audio_path)
            
            # pydub에 ffmpeg 경로 설정
            import os
            os.environ['PATH'] = str(ffmpeg_path.parent) + os.pathsep + os.environ.get('PATH', '')
            
            try:
                # 오디오 정규화 적용
                normalized_audio_path = self._normalize_audio_for_preview(audio_path, preview_id)
                
                # 정규화된 오디오 파일 로드
                main_audio = AudioSegment.from_file(normalized_audio_path)
                
                # 시작 신호음 로드
                start_audio = AudioSegment.from_file(str(self.start_signal_path)) if self.start_signal_path.exists() else AudioSegment.empty()
                
                # 끝 신호음 로드
                end_audio = AudioSegment.from_file(str(self.end_signal_path)) if self.end_signal_path.exists() else AudioSegment.empty()
                
                # 프리뷰 오디오 조합: 시작 신호음 + 정규화된 메인 오디오 + 끝 신호음
                preview_audio = start_audio + main_audio + end_audio
                
                # 프리뷰 파일 저장
                preview_path = self.preview_dir / f"{preview_id}.mp3"
                print(f"[프리뷰] 일반 처리 프리뷰 파일 저장 경로: {preview_path}")
                preview_audio.export(str(preview_path), format="mp3")
                
                # ffprobe로 파일 길이 확인
                try:
                    file_size = preview_path.stat().st_size
                    print(f"[프리뷰] 오디오 프리뷰 파일 생성 완료: {preview_path} (크기: {file_size:,} bytes)")
                    
                    # ffprobe로 정확한 길이 확인
                    duration = self._get_audio_duration_with_ffprobe(str(preview_path))
                    if duration > 0:
                        print(f"[프리뷰] 오디오 프리뷰 길이 (ffprobe): {duration:.2f}초")
                    else:
                        # pydub으로 길이 확인 시도 (백업)
                        try:
                            audio_length = len(preview_audio) / 1000.0  # 밀리초를 초로 변환
                            print(f"[프리뷰] 오디오 프리뷰 길이 (pydub): {audio_length:.2f}초")
                        except Exception as e:
                            print(f"[프리뷰] pydub 길이 확인 실패: {e}")
                        
                except Exception as e:
                    print(f"[프리뷰] 파일 정보 확인 실패: {e}")
                
                # 임시 정규화 파일 정리
                if normalized_audio_path != audio_path and Path(normalized_audio_path).exists():
                    Path(normalized_audio_path).unlink()
                
                print(f"[*] 오디오 프리뷰 생성 (정규화 적용): {preview_path}")
                return str(preview_path)
                
            except Exception as e:
                print(f"[!] 오디오 처리 중 오류: {e}")
                # 오류 발생 시 원본 파일을 복사하여 프리뷰로 사용
                preview_path = self.preview_dir / f"{preview_id}.mp3"
                shutil.copy2(audio_path, preview_path)
                print(f"[*] 원본 파일을 프리뷰로 복사: {preview_path}")
                return str(preview_path)
            
        except Exception as e:
            logger.error(f"오디오 프리뷰 생성 중 오류: {e}")
            return None
    
    def _normalize_audio_for_preview(self, audio_path: str, preview_id: str) -> str:
        """
        프리뷰용 오디오 정규화 (고품질)
        """
        print(f"[정규화] 프리뷰용 오디오 정규화 시도: {audio_path} (preview_id={preview_id})")
        try:
            from ..utils.audio_normalizer import audio_normalizer
            
            # 정규화 전 볼륨 정보 확인
            print(f"[정규화] 정규화 전 볼륨 분석 시작...")
            before_stats = audio_normalizer.get_audio_stats(audio_path)
            if "error" not in before_stats:
                print(f"[정규화] 정규화 전 - 평균: {before_stats.get('mean_volume', 'N/A')} dBFS, 최대: {before_stats.get('max_volume', 'N/A')} dBFS")
            else:
                print(f"[정규화] 정규화 전 볼륨 분석 실패: {before_stats['error']}")
            
            # 정규화 필요성 확인
            norm_info = audio_normalizer.get_normalization_info(audio_path)
            print(f"[정규화] 정규화 필요성 분석 결과: {norm_info}")
            
            if "error" in norm_info:
                print(f"[정규화] 정규화 정보 분석 실패: {norm_info['error']}")
                return audio_path
            
            if not norm_info.get("needs_normalization", False):
                print(f"[정규화] 정규화 불필요: {norm_info.get('reason', '볼륨이 적절함')}")
                return audio_path
            
            print(f"[정규화] 정규화 필요: {norm_info.get('reason', '')}")
            print(f"[정규화] 현재 평균 볼륨: {norm_info.get('current_mean_volume', 'N/A')} dBFS")
            print(f"[정규화] 목표 볼륨: {norm_info.get('target_volume', 'N/A')} dBFS")
            
            # 정규화된 파일 경로 (temp 디렉토리에 표준화된 형식으로 저장)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            normalized_path = Path(config.temp_dir) / f"normalized_{timestamp}_norm.mp3"
            
            # 고품질 정규화 수행
            success = audio_normalizer.normalize_audio_high_quality(
                input_path=audio_path,
                output_path=str(normalized_path),
                target_dbfs=norm_info.get("target_volume", config.default_target_dbfs),  # config에서 기본값 사용
                headroom=1.0
            )
            
            if success and normalized_path.exists():
                print(f"[정규화] 정규화 완료: {normalized_path}")
                return str(normalized_path)
            else:
                print(f"[정규화] 정규화 실패, 원본 파일 사용")
                return audio_path
                
        except Exception as e:
            print(f"[정규화] 정규화 중 오류: {e}")
            return audio_path
    
    def _get_audio_duration_with_ffprobe(self, audio_path: str) -> float:
        """
        ffprobe를 사용해서 오디오 파일 길이를 정확하게 확인
        
        Parameters:
        -----------
        audio_path : str
            확인할 오디오 파일 경로
            
        Returns:
        --------
        float
            오디오 길이 (초), 실패 시 0.0
        """
        try:
            from ..core.config import config
            import subprocess
            import json
            
            ffmpeg_paths = config.get_ffmpeg_paths()
            ffprobe_path = Path(ffmpeg_paths["ffprobe_path"])
            
            if not ffmpeg_paths["ffprobe_exists"]:
                print(f"[!] ffprobe를 찾을 수 없습니다.")
                return 0.0
            
            # ffprobe로 오디오 정보 분석
            cmd = [
                str(ffprobe_path),
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                print(f"[!] ffprobe 실행 실패: {result.stderr}")
                return 0.0
            
            if not result.stdout.strip():
                print(f"[!] ffprobe에서 출력이 없습니다.")
                return 0.0
            
            data = json.loads(result.stdout)
            format_info = data.get("format", {})
            duration = float(format_info.get("duration", 0))
            
            return duration
            
        except Exception as e:
            print(f"[!] ffprobe로 길이 확인 중 오류: {e}")
            return 0.0

    def _create_text_preview(self, preview_id, params):
        print(f"[프리뷰] TTS 방송 프리뷰 생성 시작 (preview_id={preview_id})")
        try:
            from pydub import AudioSegment
            import shutil
            from ..core.config import config
            
            text = params.get('text', '')
            language = params.get('language', 'ko')
            
            # TTS 오디오 생성
            tts_audio_path = self.generate_speech(text, language=language)
            if not tts_audio_path:
                raise Exception("TTS 오디오 생성 실패")
            print(f"[프리뷰] TTS 오디오 생성 완료: {tts_audio_path}")
            
            # config에서 ffmpeg 경로 가져오기
            ffmpeg_paths = config.get_ffmpeg_paths()
            ffmpeg_path = Path(ffmpeg_paths["ffmpeg_path"])
            ffprobe_path = Path(ffmpeg_paths["ffprobe_path"])
            print(f"[프리뷰] ffmpeg 경로: {ffmpeg_path}")
            print(f"[프리뷰] ffprobe 경로: {ffprobe_path}")
            
            if not ffmpeg_paths["ffmpeg_exists"] or not ffmpeg_paths["ffprobe_exists"]:
                print(f"[프리뷰] ffmpeg/ffprobe 파일을 찾을 수 없습니다.")
                # TTS 파일을 프리뷰 디렉토리로 복사
                preview_path = self.preview_dir / f"{preview_id}.wav"
                shutil.copy2(tts_audio_path, preview_path)
                print(f"[프리뷰] TTS 파일을 프리뷰로 복사: {preview_path}")
                return str(preview_path)
            
            # pydub에 ffmpeg 경로 설정
            import os
            os.environ['PATH'] = str(ffmpeg_path.parent) + os.pathsep + os.environ.get('PATH', '')
            print(f"[프리뷰] pydub PATH 설정 완료")
            
            try:
                # TTS 오디오 정규화 적용
                print(f"[TTS정규화] TTS 정규화 시작: {tts_audio_path}")
                normalized_tts_path = self._normalize_audio_for_preview(tts_audio_path, preview_id)
                print(f"[TTS정규화] TTS 정규화 완료: {normalized_tts_path}")
                
                # 정규화된 TTS 오디오 로드
                tts_audio = AudioSegment.from_file(normalized_tts_path)
                
                # 시작 신호음 로드
                start_audio = AudioSegment.from_file(str(self.start_signal_path)) if self.start_signal_path.exists() else AudioSegment.empty()
                
                # 끝 신호음 로드
                end_audio = AudioSegment.from_file(str(self.end_signal_path)) if self.end_signal_path.exists() else AudioSegment.empty()
                
                # 프리뷰 오디오 조합: 시작 신호음 + 정규화된 TTS 오디오 + 끝 신호음
                preview_audio = start_audio + tts_audio + end_audio
                
                # 프리뷰 파일 저장 (mp3 옵션 명시)
                preview_path = self.preview_dir / f"{preview_id}.mp3"
                preview_audio.export(
                    str(preview_path), 
                    format="mp3",
                    bitrate="192k",
                    parameters=["-ac", "2", "-ar", "44100"]
                )
                
                # ffprobe로 파일 길이 확인
                try:
                    file_size = preview_path.stat().st_size
                    print(f"[프리뷰] 프리뷰 파일 생성 완료: {preview_path} (크기: {file_size:,} bytes)")
                    
                    # ffprobe로 정확한 길이 확인
                    duration = self._get_audio_duration_with_ffprobe(str(preview_path))
                    if duration > 0:
                        print(f"[프리뷰] 프리뷰 길이 (ffprobe): {duration:.2f}초")
                    else:
                        # pydub으로 길이 확인 시도 (백업)
                        try:
                            audio_length = len(preview_audio) / 1000.0  # 밀리초를 초로 변환
                            print(f"[프리뷰] 프리뷰 길이 (pydub): {audio_length:.2f}초")
                        except Exception as e:
                            print(f"[프리뷰] pydub 길이 확인 실패: {e}")
                        
                except Exception as e:
                    print(f"[프리뷰] 파일 정보 확인 실패: {e}")
                
                # 정규화된 TTS 파일을 보존 (임시로)
                preserved_normalized_path = self.preview_dir / f"preserved_normalized_tts_{preview_id}.mp3"
                shutil.copy2(normalized_tts_path, preserved_normalized_path)
                print(f"[TTS정규화] 정규화된 TTS 파일 보존: {preserved_normalized_path}")
                
                # 임시 정규화 파일은 정리하지 않음 (보존용으로 사용)
                # if normalized_tts_path != tts_audio_path and Path(normalized_tts_path).exists():
                #     Path(normalized_tts_path).unlink()
                
                print(f"[*] TTS 프리뷰 생성 (정규화 적용): {preview_path}")
                return str(preview_path)
                
            except Exception as e:
                print(f"[!] TTS 오디오 처리 중 오류: {e}")
                # 오류 발생 시 TTS 파일을 복사하여 프리뷰로 사용
                preview_path = self.preview_dir / f"{preview_id}.wav"
                shutil.copy2(tts_audio_path, preview_path)
                print(f"[*] TTS 파일을 프리뷰로 복사: {preview_path}")
                return str(preview_path)
            
        except Exception as e:
            logger.error(f"TTS 프리뷰 생성 중 오류: {e}")
            return None
    
    def approve_preview(self, preview_id):
        """프리뷰 승인 및 실제 방송 큐에 추가"""
        try:
            if preview_id not in self.pending_previews:
                raise Exception(f"프리뷰를 찾을 수 없음: {preview_id}")
            
            preview_info = self.pending_previews[preview_id]
            job_type = preview_info["job_type"]
            params = preview_info["params"]
            preview_path = preview_info.get("preview_path")
            
            if not preview_path or not Path(preview_path).exists():
                raise Exception(f"프리뷰 파일을 찾을 수 없음: {preview_path}")
            
            # 프리뷰 파일을 직접 방송 큐에 추가
            if job_type == 'audio':
                # 오디오 프리뷰: 프리뷰 파일을 직접 사용
                result = self.broadcast_audio(
                    audio_path=preview_path,
                    target_devices=params.get('target_devices', []),
                    end_devices=params.get('end_devices', []),
                    duration=preview_info.get('actual_duration'),
                    skip_signals=True  # 프리뷰 파일에는 이미 시작음/끝음이 포함됨
                )
            elif job_type == 'text':
                # 텍스트 프리뷰: 프리뷰 파일을 직접 사용
                result = self.broadcast_audio(
                    audio_path=preview_path,
                    target_devices=params.get('target_devices', []),
                    end_devices=params.get('end_devices', []),
                    duration=preview_info.get('actual_duration'),
                    skip_signals=True  # 프리뷰 파일에는 이미 시작음/끝음이 포함됨
                )
            else:
                raise Exception(f"지원하지 않는 작업 타입: {job_type}")
            
            # 승인된 프리뷰 제거
            del self.pending_previews[preview_id]
            
            print(f"[*] 프리뷰 승인 완료: {preview_id}")
            print(f"[*] 프리뷰 파일 방송: {preview_path}")
            return result
            
        except Exception as e:
            logger.error(f"프리뷰 승인 중 오류: {e}")
            return None
    
    def reject_preview(self, preview_id):
        """프리뷰 거부"""
        try:
            if preview_id not in self.pending_previews:
                raise Exception(f"프리뷰를 찾을 수 없음: {preview_id}")
            
            # 프리뷰 파일 삭제
            preview_info = self.pending_previews[preview_id]
            preview_path = preview_info.get("preview_path")
            if preview_path and Path(preview_path).exists():
                Path(preview_path).unlink()
            
            # 대기 중인 프리뷰에서 제거
            del self.pending_previews[preview_id]
            
            print(f"[*] 프리뷰 거부 완료: {preview_id}")
            return True
            
        except Exception as e:
            logger.error(f"프리뷰 거부 중 오류: {e}")
            return False
    
    def get_preview_info(self, preview_id):
        """프리뷰 정보 조회"""
        return self.pending_previews.get(preview_id)
    
    def get_all_previews(self):
        """모든 대기 중인 프리뷰 조회"""
        return list(self.pending_previews.values())

    def save_device_states(self, target_devices):
        """
        방송 대상 장치들의 현재 상태를 저장
        
        Parameters:
        -----------
        target_devices : list
            상태를 저장할 장치 목록
            
        Returns:
        --------
        bool
            저장 성공 여부
        """
        try:
            if not target_devices:
                print("[*] 저장할 장치가 없습니다.")
                return True
                
            print(f"[*] 장치 상태 저장 시작: {target_devices}")
            
            # 현재 활성화된 방 목록 가져오기
            active_rooms = self.broadcast_manager.get_active_rooms()
            print(f"[*] 현재 활성화된 방: {sorted(active_rooms)}")
            
            # 대상 장치들의 상태 저장
            for device in target_devices:
                # 장치명을 방 번호로 변환 (예: "1-1" -> "101")
                room_number = self._device_name_to_room_number(device)
                if room_number:
                    # 현재 상태 저장 (활성화되어 있으면 True, 아니면 False)
                    self.device_state_backup[device] = room_number in active_rooms
                    print(f"[*] 장치 {device} (방 {room_number}) 상태 저장: {'켜짐' if room_number in active_rooms else '꺼짐'}")
                else:
                    # 일반 장치의 경우 (방 번호가 없는 장치)
                    # 장치 매트릭스에서 해당 장치의 위치를 찾아서 상태 저장
                    device_coords = self._find_device_in_matrix(device)
                    if device_coords:
                        row, col = device_coords
                        # 장치 매트릭스 위치를 기반으로 상태 저장
                        # 실제로는 해당 위치의 장치가 활성화되어 있는지 확인
                        self.device_state_backup[device] = self._is_device_active_at_position(row, col, active_rooms)
                        print(f"[*] 일반 장치 {device} (위치: {row},{col}) 상태 저장: {'켜짐' if self.device_state_backup[device] else '꺼짐'}")
                    else:
                        print(f"[!] 장치 {device}의 위치를 찾을 수 없습니다.")
            
            print(f"[*] 장치 상태 저장 완료: {len(self.device_state_backup)}개 장치")
            return True
            
        except Exception as e:
            print(f"[!] 장치 상태 저장 중 오류: {e}")
            return False
    
    def restore_device_states(self, target_devices):
        """
        저장된 상태로 장치들을 복원
        Parameters:
        -----------
        target_devices : list
            상태를 복원할 장치 목록
        Returns:
        --------
        bool
            복원 성공 여부
        """
        try:
            if not self.restore_device_states_enabled:
                print("[*] 장치 상태 복원이 비활성화되어 있습니다.")
                return True
            if not target_devices:
                print("[*] 복원할 장치가 없습니다.")
                return True
            if not self.device_state_backup:
                print("[*] 저장된 장치 상태가 없습니다.")
                return True
            print(f"[*] 장치 상태 복원 시작: {target_devices}")
            # 현재 활성화된 방 목록 가져오기
            active_rooms = self.broadcast_manager.get_active_rooms()
            print(f"[*] 방송 후 현재 활성화된 방: {sorted(active_rooms)}")
            # 켜야 할 장치와 꺼야 할 장치 분리
            devices_to_turn_on = []
            devices_to_turn_off = []
            for device in target_devices:
                if device in self.device_state_backup:
                    original_state = self.device_state_backup[device]
                    room_number = self._device_name_to_room_number(device)
                    if room_number:
                        current_state = room_number in active_rooms
                        if current_state != original_state:
                            if original_state:
                                devices_to_turn_on.append(device)
                            else:
                                devices_to_turn_off.append(device)
                    else:
                        device_coords = self._find_device_in_matrix(device)
                        if device_coords:
                            row, col = device_coords
                            current_state = self._is_device_active_at_position(row, col, active_rooms)
                            if current_state != original_state:
                                if original_state:
                                    devices_to_turn_on.append(device)
                                else:
                                    devices_to_turn_off.append(device)
            # 한 번에 상태 반영
            if devices_to_turn_on:
                print(f"[*] 켜야 할 장치: {devices_to_turn_on}")
                self.control_multiple_devices(devices_to_turn_on, 1)
            if devices_to_turn_off:
                print(f"[*] 꺼야 할 장치: {devices_to_turn_off}")
                self.control_multiple_devices(devices_to_turn_off, 0)
            # 복원 완료 후 상태 확인
            time.sleep(0.5)
            final_active_rooms = self.broadcast_manager.get_active_rooms()
            print(f"[*] 상태 복원 후 활성화된 방: {sorted(final_active_rooms)}")
            # 백업 데이터 정리
            for device in target_devices:
                if device in self.device_state_backup:
                    del self.device_state_backup[device]
            print(f"[*] 장치 상태 복원 완료")
            return True
        except Exception as e:
            print(f"[!] 장치 상태 복원 중 오류: {e}")
            return False
    
    def _find_device_in_matrix(self, device_name):
        """
        장치명을 장치 매트릭스에서 찾아서 좌표 반환
        
        Parameters:
        -----------
        device_name : str
            찾을 장치명
            
        Returns:
        --------
        tuple
            (row, col) 또는 None
        """
        try:
            device_matrix = self.device_mapper.get_device_matrix()
            for row in range(len(device_matrix)):
                for col in range(len(device_matrix[row])):
                    if device_matrix[row][col] == device_name:
                        return (row, col)
            return None
        except Exception as e:
            print(f"[!] 장치 매트릭스 검색 중 오류: {e}")
            return None
    
    def _is_device_active_at_position(self, row, col, active_rooms):
        """
        특정 위치의 장치가 활성화되어 있는지 확인
        
        Parameters:
        -----------
        row : int
            행 번호
        col : int
            열 번호
        active_rooms : list
            활성화된 방 목록
            
        Returns:
        --------
        bool
            활성화 여부
        """
        try:
            # 장치 매트릭스 위치를 기반으로 활성화 여부 판단
            # 실제 구현에서는 해당 위치의 장치 상태를 확인하는 로직 필요
            # 현재는 단순히 해당 위치가 활성화되어 있다고 가정
            device_id = row * 16 + col + 1
            return device_id in active_rooms
        except Exception as e:
            print(f"[!] 장치 활성화 상태 확인 중 오류: {e}")
            return False
    
    def _device_name_to_room_number(self, device_name):
        """
        장치명을 방 번호로 변환
        
        Parameters:
        -----------
        device_name : str
            장치명 (예: "1-1", "3-2")
            
        Returns:
        --------
        int
            방 번호 (예: 101, 302) 또는 None
        """
        try:
            # 학년-반 형식 (예: "1-1", "3-2")
            if '-' in device_name and device_name[0].isdigit():
                grade, class_num = device_name.split('-')
                grade = int(grade)
                class_num = int(class_num)
                
                # 방 번호 생성 (학년 + 반)
                room_number = grade * 100 + class_num
                
                # 좌표 유효성 검사
                if 1 <= grade <= 4 and 1 <= class_num <= 16:
                    return room_number
                else:
                    print(f"[!] 좌표 범위 초과: ({grade}, {class_num})")
                    return None
            else:
                print(f"[!] 지원되지 않는 장치명 형식: {device_name}")
                return None
                    
        except Exception as e:
            print(f"[!] 장치명 변환 중 오류: {e}")
            return None
    
    def set_restore_device_states(self, enabled):
        """
        장치 상태 복원 기능 활성화/비활성화 설정
        
        Parameters:
        -----------
        enabled : bool
            복원 기능 활성화 여부
        """
        self.restore_device_states_enabled = enabled
        print(f"[*] 장치 상태 복원 기능: {'활성화' if enabled else '비활성화'}")
    
    def get_device_state_backup_info(self):
        """
        저장된 장치 상태 정보 조회
        
        Returns:
        --------
        dict
            저장된 장치 상태 정보
        """
        return {
            "restore_enabled": self.restore_device_states_enabled,
            "backup_count": len(self.device_state_backup),
            "backup_devices": list(self.device_state_backup.keys()),
            "backup_states": self.device_state_backup.copy()
        }

# 싱글톤 인스턴스 생성
broadcast_controller = BroadcastController()
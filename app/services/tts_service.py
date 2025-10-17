#!/usr/bin/env python3
"""
통합 TTS(Text-to-Speech) 서비스 모듈
다양한 TTS 엔진을 통합하여 고품질 음성 합성을 제공합니다.
"""
import os
import time
import traceback
import importlib.util
from pathlib import Path

# 기본 설정
DEFAULT_LANGUAGE = "ko"  # 기본 언어: 한국어
AUDIO_EXT = {
    "melotts": ".wav",
    "gtts": ".mp3",
    "pyttsx3": ".wav",
}

class TTSService:
    """
    통합 TTS 서비스 클래스
    다양한 TTS 엔진을 관리하고 최상의 가용 엔진을 사용합니다.
    """
    def __init__(self, cache_dir=None):
        """
        TTSService 초기화
        
        Parameters:
        -----------
        cache_dir : str 또는 Path
            TTS 모델 캐시 디렉토리 (기본값: None)
        """
        self.tts_engine = None  # 현재 사용 중인 TTS 엔진
        self.tts_type = None    # TTS 엔진 유형
        self.cache_dir = cache_dir
        
        # 사용 가능한 TTS 엔진 초기화
        self._initialize_tts_engines()
    
    def _initialize_tts_engines(self):
        """
        사용 가능한 TTS 엔진 초기화
        우선순위: MeloTTS > gTTS > pyttsx3
        """
        # 1. MeloTTS 시도 (최고 품질)
        if self._try_load_melotts():
            print("[*] MeloTTS 엔진이 활성화되었습니다.")
            return
        
        # 2. gTTS 시도 (중간 품질, 인터넷 필요)
        if self._try_load_gtts():
            print("[*] gTTS 엔진이 활성화되었습니다.")
            return
            
        # 3. pyttsx3 시도 (낮은 품질, 오프라인)
        if self._try_load_pyttsx3():
            print("[*] pyttsx3 엔진이 활성화되었습니다.")
            return
            
        # 모든 엔진 로드 실패
        print("[!] 경고: 사용 가능한 TTS 엔진이 없습니다.")
    
    def _try_load_melotts(self):
        """MeloTTS 엔진 로드 시도"""
        try:
            if importlib.util.find_spec("melo") is not None:
                from melo import Text2Speech
                
                # 캐시 디렉토리 설정
                cache_args = {}
                if self.cache_dir:
                    cache_args["cache_dir"] = str(self.cache_dir)
                
                # 진행률 콜백 함수
                def progress_callback(progress):
                    if int(progress * 100) % 10 == 0:
                        print(f"[*] 모델 다운로드 진행률: {int(progress * 100)}%")
                
                # 한국어 모델 초기화
                self.tts_engine = Text2Speech(
                    model_name="base", 
                    speaker="KR",
                    progress_callback=progress_callback,
                    **cache_args
                )
                self.tts_type = "melotts"
                return True
        except ImportError:
            print("[!] MeloTTS 모듈을 찾을 수 없습니다.")
        except Exception as e:
            print(f"[!] MeloTTS 초기화 오류: {e}")
            traceback.print_exc()
        return False
    
    def _try_load_gtts(self):
        """gTTS 엔진 로드 시도"""
        try:
            if importlib.util.find_spec("gtts") is not None:
                from gtts import gTTS
                # gTTS는 객체가 아닌 함수로 사용되므로 self.tts_engine에 클래스 자체를 저장
                self.tts_engine = gTTS
                self.tts_type = "gtts"
                return True
        except ImportError:
            print("[!] gTTS 모듈을 찾을 수 없습니다.")
        except Exception as e:
            print(f"[!] gTTS 초기화 오류: {e}")
            traceback.print_exc()
        return False
    
    def _try_load_pyttsx3(self):
        """pyttsx3 엔진 로드 시도"""
        try:
            if importlib.util.find_spec("pyttsx3") is not None:
                import pyttsx3
                self.tts_engine = pyttsx3.init()
                self.tts_type = "pyttsx3"
                
                # 최적의 품질 설정
                self.tts_engine.setProperty('rate', 150)  # 속도
                self.tts_engine.setProperty('volume', 1.0)  # 볼륨
                return True
        except ImportError:
            print("[!] pyttsx3 모듈을 찾을 수 없습니다.")
        except Exception as e:
            print(f"[!] pyttsx3 초기화 오류: {e}")
            traceback.print_exc()
        return False
    
    def synthesize(self, text, output_path=None, language=DEFAULT_LANGUAGE):
        """
        텍스트를 음성으로 변환
        
        Parameters:
        -----------
        text : str
            변환할 텍스트
        output_path : str 또는 Path
            출력 파일 경로 (None이면 자동 생성)
        language : str
            텍스트 언어 (기본값: 한국어)
            
        Returns:
        --------
        Path
            생성된 음성 파일 경로
        """
        if not self.tts_engine:
            print("[!] 오류: 활성화된 TTS 엔진이 없습니다.")
            return None
            
        # 텍스트 검증
        if not text or not text.strip():
            print("[!] 오류: 변환할 텍스트가 비어있습니다.")
            return None
            
        try:
            # 출력 경로 자동 생성
            if output_path is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                ext = AUDIO_EXT.get(self.tts_type, ".wav")
                output_path = f"audio_{timestamp}{ext}"
            
            output_path = Path(output_path)
            
            # 디렉토리 생성
            os.makedirs(output_path.parent, exist_ok=True)
            
            print(f"[*] 텍스트를 음성으로 변환 중: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            start_time = time.time()
            
            # TTS 엔진별 처리
            if self.tts_type == "melotts":
                # MeloTTS 사용
                wav_data = self.tts_engine.synthesize(text=text)
                
                # 출력 형식이 mp3인 경우 변환
                if output_path.suffix.lower() == '.mp3':
                    try:
                        from pydub import AudioSegment
                        import io
                        
                        # 임시 WAV 파일로 먼저 저장
                        temp_wav_path = output_path.with_suffix('.temp.wav')
                        
                        # MeloTTS가 올바른 WAV 헤더를 생성했는지 확인
                        if not wav_data.startswith(b'RIFF') or b'WAVE' not in wav_data[:12]:
                            # PCM 데이터로 가정하고 WAV 파일 생성
                            try:
                                import numpy as np
                                import wave
                                
                                # 바이트 데이터를 NumPy 배열로 변환 (16비트 PCM 가정)
                                audio_array = np.frombuffer(wav_data, dtype=np.int16)
                                
                                # 표준 WAV 파일 생성 (16비트, 단일 채널, 24kHz 가정)
                                with wave.open(str(temp_wav_path), 'wb') as wf:
                                    wf.setnchannels(1)  # 모노
                                    wf.setsampwidth(2)  # 16비트
                                    wf.setframerate(24000)  # 24kHz
                                    wf.writeframes(audio_array.tobytes())
                                
                                print(f"[*] PCM 데이터에서 WAV 파일 생성: {temp_wav_path}")
                            except Exception as e:
                                print(f"[!] PCM 변환 중 오류: {e}")
                                
                                # 오류 발생 시 원시 데이터를 그대로 WAV 파일로 저장
                                with open(temp_wav_path, "wb") as f:
                                    f.write(wav_data)
                        else:
                            # 올바른 WAV 헤더가 있으면 그대로 저장
                            with open(temp_wav_path, "wb") as f:
                                f.write(wav_data)
                        
                        # WAV 파일을 MP3로 변환
                        if temp_wav_path.exists():
                            sound = AudioSegment.from_file(temp_wav_path, format="wav")
                            sound.export(output_path, format="mp3", bitrate="192k")
                            
                            # 임시 파일 삭제
                            os.remove(temp_wav_path)
                            print(f"[*] WAV를 MP3로 변환 완료: {output_path}")
                        else:
                            print(f"[!] 임시 WAV 파일을 찾을 수 없습니다: {temp_wav_path}")
                    except Exception as e:
                        print(f"[!] MP3 변환 중 오류: {e}")
                        
                        # 변환 실패 시 WAV 파일로 출력
                        output_path = output_path.with_suffix('.wav')
                        with open(output_path, "wb") as f:
                            f.write(wav_data)
                else:
                    # WAV 파일 직접 저장
                    # MeloTTS가 올바른 WAV 헤더를 생성했는지 확인
                    if not wav_data.startswith(b'RIFF') or b'WAVE' not in wav_data[:12]:
                        print("[!] 경고: MeloTTS가 생성한 데이터에 올바른 WAV 헤더가 없습니다.")
                        # PCM 데이터로 가정하고 WAV 파일 생성
                        try:
                            import wave
                            import numpy as np
                            
                            # 바이트 데이터를 NumPy 배열로 변환 (16비트 PCM 가정)
                            audio_array = np.frombuffer(wav_data, dtype=np.int16)
                            
                            # 표준 WAV 파일 생성 (16비트, 단일 채널, 24kHz 가정)
                            with wave.open(str(output_path), 'wb') as wf:
                                wf.setnchannels(1)  # 모노
                                wf.setsampwidth(2)  # 16비트
                                wf.setframerate(24000)  # 24kHz
                                wf.writeframes(audio_array.tobytes())
                            
                            print(f"[*] PCM 데이터에서 올바른 WAV 파일 생성: {output_path}")
                        except Exception as e:
                            print(f"[!] WAV 생성 중 오류: {e}")
                            
                            # 오류 발생 시 원시 데이터를 그대로 WAV 파일로 저장
                            with open(output_path, "wb") as f:
                                f.write(wav_data)
                    else:
                        # 올바른 WAV 헤더가 있으면 그대로 저장
                        with open(output_path, "wb") as f:
                            f.write(wav_data)
            
            elif self.tts_type == "gtts":
                # gTTS 사용
                lang_map = {
                    "ko": "ko",
                    "en": "en",
                    "ja": "ja",
                    "zh": "zh-CN",
                    "es": "es",
                    "fr": "fr"
                }
                gtts_lang = lang_map.get(language.lower(), "ko")
                
                # 고품질 설정
                tts = self.tts_engine(
                    text=text, 
                    lang=gtts_lang,
                    slow=False, 
                    tld="com"  # Google.com 서버 사용
                )
                tts.save(str(output_path))
            
            elif self.tts_type == "pyttsx3":
                # pyttsx3 사용
                # 언어 설정 시도
                voices = self.tts_engine.getProperty('voices')
                for voice in voices:
                    if language == "ko" and ("korean" in voice.name.lower() or "ko" in voice.id.lower()):
                        self.tts_engine.setProperty('voice', voice.id)
                        break
                    elif language == "en" and "en" in voice.id.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
                
                # 파일로 저장
                self.tts_engine.save_to_file(text, str(output_path))
                self.tts_engine.runAndWait()
                
                # 파일 쓰기 완료 대기 (최대 5초)
                import time as time_module
                for i in range(50):
                    if output_path.exists() and os.path.getsize(output_path) > 0:
                        break
                    time_module.sleep(0.1)
            
            # 결과 정보 출력
            elapsed_time = time.time() - start_time
            print(f"[*] 음성 파일 생성 완료: {output_path} (소요 시간: {elapsed_time:.2f}초)")
            
            if output_path.exists():
                file_size = os.path.getsize(output_path) / 1024  # KB
                print(f"[*] 생성된 음성 파일 크기: {file_size:.1f} KB")
                return output_path
            else:
                print(f"[!] 생성된 파일을 찾을 수 없습니다: {output_path}")
                return None
                
        except Exception as e:
            print(f"[!] 음성 생성 중 오류 발생: {e}")
            traceback.print_exc()
            return None
    
    def change_language(self, language):
        """
        TTS 언어 변경
        
        Parameters:
        -----------
        language : str
            변경할 언어 코드 (ko, en, ja, zh, es, fr)
            
        Returns:
        --------
        bool
            성공 여부
        """
        try:
            if self.tts_type == "melotts":
                # MeloTTS 언어 변경
                speaker_map = {
                    "ko": "KR",
                    "en": "EN-Default",
                    "ja": "JP",
                    "zh": "ZH",
                    "es": "ES",
                    "fr": "FR"
                }
                speaker = speaker_map.get(language.lower(), "KR")
                
                # 캐시 디렉토리 설정
                cache_args = {}
                if self.cache_dir:
                    cache_args["cache_dir"] = str(self.cache_dir)
                
                # 새 모델 초기화
                from melo import Text2Speech
                self.tts_engine = Text2Speech(
                    model_name="base", 
                    speaker=speaker,
                    **cache_args
                )
                
                print(f"[*] MeloTTS 언어 변경 완료: {speaker}")
                return True
                
            elif self.tts_type == "pyttsx3":
                # pyttsx3 언어 변경 (사용 가능한 음성 목록에서 검색)
                voices = self.tts_engine.getProperty('voices')
                for voice in voices:
                    if language == "ko" and ("korean" in voice.name.lower() or "ko" in voice.id.lower()):
                        self.tts_engine.setProperty('voice', voice.id)
                        print(f"[*] pyttsx3 음성 변경 완료: {voice.name}")
                        return True
                    elif language == "en" and "en" in voice.id.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        print(f"[*] pyttsx3 음성 변경 완료: {voice.name}")
                        return True
                
                print(f"[!] 지정한 언어({language})에 맞는 음성을 찾을 수 없습니다.")
                return False
                
            elif self.tts_type == "gtts":
                # gTTS는 매 호출마다 언어 설정이 가능하므로 별도 설정 불필요
                return True
                
            else:
                print("[!] 알 수 없는 TTS 엔진 유형입니다.")
                return False
                
        except Exception as e:
            print(f"[!] 언어 변경 중 오류 발생: {e}")
            traceback.print_exc()
            return False
    
    def get_tts_info(self):
        """
        현재 TTS 엔진 정보 반환
        """
        info = {
            "engine_type": self.tts_type,
            "engine_available": self.tts_engine is not None,
        }
        
        if self.tts_type == "melotts":
            info["description"] = "MeloTTS (고품질 TTS)"
            info["quality"] = "최상"
            info["internet_required"] = False
        elif self.tts_type == "gtts":
            info["description"] = "Google TTS"
            info["quality"] = "중간"
            info["internet_required"] = True
        elif self.tts_type == "pyttsx3":
            info["description"] = "Microsoft TTS"
            info["quality"] = "기본"
            info["internet_required"] = False
        else:
            info["description"] = "알 수 없음"
            info["quality"] = "알 수 없음"
            info["internet_required"] = False
        
        return info

# 싱글톤 인스턴스
tts_service = None

def init_tts_service(cache_dir=None):
    """
    TTS 서비스 초기화 함수
    """
    global tts_service
    if tts_service is None:
        tts_service = TTSService(cache_dir=cache_dir)
    return tts_service

def get_tts_service():
    """
    TTS 서비스 인스턴스 가져오기
    """
    global tts_service
    if tts_service is None:
        tts_service = TTSService()
    return tts_service 
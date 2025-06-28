#!/usr/bin/env python3
"""
오디오 정규화 유틸리티 모듈
오디오 파일의 볼륨을 일정하게 맞추는 기능을 제공합니다.
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple

from ..core.config import setup_logging, config

# 중앙 로깅 설정 사용
logger = setup_logging(__name__)

class AudioNormalizer:
    """
    오디오 정규화 클래스
    오디오 파일의 볼륨을 분석하고 정규화합니다.
    """
    
    def __init__(self, target_dbfs: float = -10.0, headroom: float = 1.0):
        """
        AudioNormalizer 초기화
        
        Parameters:
        -----------
        target_dbfs : float
            목표 볼륨 레벨 (dBFS, 기본값: -10.0)
        headroom : float
            헤드룸 (dB, 기본값: 1.0)
        """
        self.target_dbfs = target_dbfs
        self.headroom = headroom
        
        # ffmpeg 경로 설정
        self.ffmpeg_path = self._get_ffmpeg_path()
        self.ffprobe_path = self._get_ffprobe_path()
        
        # 임시 디렉토리 설정
        self.temp_dir = Path(config.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[*] AudioNormalizer 초기화 완료")
        print(f"[*] 목표 볼륨: {target_dbfs} dBFS")
        print(f"[*] 헤드룸: {headroom} dB")
        print(f"[*] 임시 디렉토리: {self.temp_dir}")
    
    def _create_temp_file(self, suffix: str = ".wav") -> Path:
        """
        임시 파일 생성
        
        Parameters:
        -----------
        suffix : str
            파일 확장자
            
        Returns:
        --------
        Path
            임시 파일 경로
        """
        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix,
            dir=self.temp_dir,
            delete=False
        )
        temp_file.close()
        return Path(temp_file.name)
    
    def _cleanup_temp_files(self, *file_paths):
        """
        임시 파일들 정리
        
        Parameters:
        -----------
        *file_paths : Path
            삭제할 파일 경로들
        """
        for file_path in file_paths:
            if file_path and file_path.exists():
                try:
                    file_path.unlink()
                    logger.debug(f"임시 파일 삭제: {file_path}")
                except Exception as e:
                    logger.warning(f"임시 파일 삭제 실패: {file_path} - {e}")
    
    def _get_ffmpeg_path(self) -> Optional[Path]:
        """ffmpeg 경로 반환"""
        try:
            from ..core.config import config
            ffmpeg_paths = config.get_ffmpeg_paths()
            
            if ffmpeg_paths["ffmpeg_exists"]:
                return Path(ffmpeg_paths["ffmpeg_path"])
            else:
                print(f"[!] ffmpeg를 찾을 수 없습니다: {ffmpeg_paths['ffmpeg_path']}")
                return None
        except Exception as e:
            print(f"[!] ffmpeg 경로 설정 중 오류: {e}")
            return None
    
    def _get_ffprobe_path(self) -> Optional[Path]:
        """ffprobe 경로 반환"""
        try:
            from ..core.config import config
            ffmpeg_paths = config.get_ffmpeg_paths()
            
            if ffmpeg_paths["ffprobe_exists"]:
                return Path(ffmpeg_paths["ffprobe_path"])
            else:
                print(f"[!] ffprobe를 찾을 수 없습니다: {ffmpeg_paths['ffprobe_path']}")
                return None
        except Exception as e:
            print(f"[!] ffprobe 경로 설정 중 오류: {e}")
            return None
    
    def analyze_audio(self, audio_path: str) -> dict:
        """
        오디오 파일 분석
        
        Parameters:
        -----------
        audio_path : str
            분석할 오디오 파일 경로
            
        Returns:
        --------
        dict
            오디오 분석 결과
        """
        try:
            if not self.ffprobe_path:
                return {"error": "ffprobe를 찾을 수 없습니다."}
            
            import subprocess
            import json
            
            # Windows에서 인코딩 문제 해결
            if sys.platform == "win32":
                # UTF-8 인코딩으로 환경 변수 설정
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                
                # ffprobe로 오디오 정보 분석
                cmd = [
                    str(self.ffprobe_path),
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    audio_path
                ]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8',
                    env=env,
                    errors='replace'
                )
            else:
                # Linux/Mac에서는 기본 방식 사용
                cmd = [
                    str(self.ffprobe_path),
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    audio_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"error": f"ffprobe 실행 실패: {result.stderr}"}
            
            if not result.stdout.strip():
                return {"error": "ffprobe에서 출력이 없습니다."}
            
            data = json.loads(result.stdout)
            
            # 오디오 스트림 찾기
            audio_stream = None
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "audio":
                    audio_stream = stream
                    break
            
            if not audio_stream:
                return {"error": "오디오 스트림을 찾을 수 없습니다."}
            
            # 기본 정보 추출
            format_info = data.get("format", {})
            duration = float(format_info.get("duration", 0))
            bit_rate = int(format_info.get("bit_rate", 0))
            
            # 오디오 스트림 정보
            sample_rate = int(audio_stream.get("sample_rate", 0))
            channels = int(audio_stream.get("channels", 0))
            codec = audio_stream.get("codec_name", "unknown")
            
            return {
                "duration": duration,
                "bit_rate": bit_rate,
                "sample_rate": sample_rate,
                "channels": channels,
                "codec": codec,
                "file_size": os.path.getsize(audio_path)
            }
            
        except Exception as e:
            logger.error(f"오디오 분석 중 오류: {e}")
            return {"error": str(e)}
    
    def get_audio_stats(self, audio_path: str) -> dict:
        """
        오디오 파일의 볼륨 통계 분석
        
        Parameters:
        -----------
        audio_path : str
            분석할 오디오 파일 경로
            
        Returns:
        --------
        dict
            볼륨 통계 정보
        """
        try:
            if not self.ffmpeg_path:
                return {"error": "ffmpeg를 찾을 수 없습니다."}
            
            import subprocess
            
            # Windows에서 인코딩 문제 해결
            if sys.platform == "win32":
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                
                # ffmpeg로 볼륨 통계 분석
                cmd = [
                    str(self.ffmpeg_path),
                    "-i", audio_path,
                    "-af", "volumedetect",
                    "-f", "null",
                    "-"
                ]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8',
                    env=env,
                    errors='replace'
                )
            else:
                # Linux/Mac에서는 기본 방식 사용
                cmd = [
                    str(self.ffmpeg_path),
                    "-i", audio_path,
                    "-af", "volumedetect",
                    "-f", "null",
                    "-"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"error": f"ffmpeg 실행 실패: {result.stderr}"}
            
            # 출력에서 볼륨 정보 추출
            output = result.stderr
            
            # 평균 볼륨 (RMS)
            mean_volume = None
            if "mean_volume:" in output:
                mean_line = [line for line in output.split('\n') if "mean_volume:" in line][0]
                mean_volume = float(mean_line.split(":")[1].strip().replace(" dB", ""))
            
            # 최대 볼륨
            max_volume = None
            if "max_volume:" in output:
                max_line = [line for line in output.split('\n') if "max_volume:" in line][0]
                max_volume = float(max_line.split(":")[1].strip().replace(" dB", ""))
            
            return {
                "mean_volume": mean_volume,
                "max_volume": max_volume,
                "volume_range": max_volume - mean_volume if max_volume and mean_volume else None
            }
            
        except Exception as e:
            logger.error(f"볼륨 통계 분석 중 오류: {e}")
            return {"error": str(e)}
    
    def normalize_audio_high_quality(self, input_path: str, output_path: str, 
                                   target_dbfs: Optional[float] = None,
                                   headroom: Optional[float] = None) -> bool:
        """
        고품질 오디오 정규화 (임시 파일 사용)
        
        Parameters:
        -----------
        input_path : str
            입력 오디오 파일 경로
        output_path : str
            출력 오디오 파일 경로
        target_dbfs : float, optional
            목표 볼륨 레벨 (기본값: -10.0)
        headroom : float, optional
            헤드룸 (기본값: 1.0)
            
        Returns:
        --------
        bool
            정규화 성공 여부
        """
        temp_files = []
        
        try:
            if not self.ffmpeg_path:
                logger.error("ffmpeg를 찾을 수 없습니다.")
                return False
            
            # 기본값 사용
            target = target_dbfs if target_dbfs is not None else self.target_dbfs
            head = headroom if headroom is not None else self.headroom
            
            logger.info(f"고품질 오디오 정규화 시작: {input_path}")
            logger.info(f"목표 볼륨: {target} dBFS, 헤드룸: {head} dB")
            
            import subprocess
            
            # 1단계: 임시 파일로 고품질 정규화
            temp_normalized = self._create_temp_file(".wav")
            temp_files.append(temp_normalized)
            
            # Windows에서 인코딩 문제 해결
            if sys.platform == "win32":
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                
                # 고품질 정규화 (loudnorm 필터 + 고품질 설정)
                cmd = [
                    str(self.ffmpeg_path),
                    "-i", input_path,
                    "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I=-23.0:measured_LRA=7.0:measured_TP=-2.0:measured_thresh=-33.0:offset=0.0:linear=true:print_format=summary",
                    "-ar", "48000",  # 고품질 샘플레이트
                    "-ac", "2",      # 스테레오
                    "-b:a", "320k",  # 고품질 비트레이트
                    "-c:a", "pcm_s16le",  # 무손실 코덱
                    "-y",            # 덮어쓰기
                    str(temp_normalized)
                ]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8',
                    env=env,
                    errors='replace'
                )
            else:
                # Linux/Mac에서는 기본 방식 사용
                cmd = [
                    str(self.ffmpeg_path),
                    "-i", input_path,
                    "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I=-23.0:measured_LRA=7.0:measured_TP=-2.0:measured_thresh=-33.0:offset=0.0:linear=true:print_format=summary",
                    "-ar", "48000",  # 고품질 샘플레이트
                    "-ac", "2",      # 스테레오
                    "-b:a", "320k",  # 고품질 비트레이트
                    "-c:a", "pcm_s16le",  # 무손실 코덱
                    "-y",            # 덮어쓰기
                    str(temp_normalized)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"고품질 정규화 실패: {result.stderr}")
                return False
            
            # 2단계: 최종 출력 형식으로 변환
            if sys.platform == "win32":
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                
                # 최종 출력 (MP3로 변환)
                cmd = [
                    str(self.ffmpeg_path),
                    "-i", str(temp_normalized),
                    "-c:a", "libmp3lame",
                    "-b:a", "256k",  # 고품질 MP3
                    "-ar", "44100",  # 표준 샘플레이트
                    "-ac", "2",      # 스테레오
                    "-q:a", "2",     # 고품질 설정
                    "-y",            # 덮어쓰기
                    output_path
                ]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8',
                    env=env,
                    errors='replace'
                )
            else:
                # Linux/Mac에서는 기본 방식 사용
                cmd = [
                    str(self.ffmpeg_path),
                    "-i", str(temp_normalized),
                    "-c:a", "libmp3lame",
                    "-b:a", "256k",  # 고품질 MP3
                    "-ar", "44100",  # 표준 샘플레이트
                    "-ac", "2",      # 스테레오
                    "-q:a", "2",     # 고품질 설정
                    "-y",            # 덮어쓰기
                    output_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"최종 변환 실패: {result.stderr}")
                return False
            
            # 정규화 전후 통계 비교
            before_stats = self.get_audio_stats(input_path)
            after_stats = self.get_audio_stats(output_path)
            
            logger.info(f"고품질 정규화 완료: {output_path}")
            logger.info(f"정규화 전 - 평균: {before_stats.get('mean_volume', 'N/A')} dB, 최대: {before_stats.get('max_volume', 'N/A')} dB")
            logger.info(f"정규화 후 - 평균: {after_stats.get('mean_volume', 'N/A')} dB, 최대: {after_stats.get('max_volume', 'N/A')} dB")
            
            return True
            
        except Exception as e:
            logger.error(f"고품질 오디오 정규화 중 오류: {e}")
            return False
        finally:
            # 임시 파일 정리
            self._cleanup_temp_files(*temp_files)
    
    def normalize_audio_simple(self, input_path: str, output_path: str, 
                             target_dbfs: Optional[float] = None) -> bool:
        """
        간단한 오디오 정규화 (임시 파일 사용)
        
        Parameters:
        -----------
        input_path : str
            입력 오디오 파일 경로
        output_path : str
            출력 오디오 파일 경로
        target_dbfs : float, optional
            목표 볼륨 레벨 (기본값: -10.0)
            
        Returns:
        --------
        bool
            정규화 성공 여부
        """
        temp_files = []
        
        try:
            if not self.ffmpeg_path:
                logger.error("ffmpeg를 찾을 수 없습니다.")
                return False
            
            target = target_dbfs if target_dbfs is not None else self.target_dbfs
            
            logger.info(f"간단한 오디오 정규화 시작: {input_path}")
            logger.info(f"목표 볼륨: {target} dBFS")
            
            import subprocess
            
            # 임시 파일 생성
            temp_normalized = self._create_temp_file(".wav")
            temp_files.append(temp_normalized)
            
            # Windows에서 인코딩 문제 해결
            if sys.platform == "win32":
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                
                # 간단한 정규화 (loudnorm 필터)
                cmd = [
                    str(self.ffmpeg_path),
                    "-i", input_path,
                    "-af", f"loudnorm=I={target}",
                    "-ar", "44100",  # 표준 샘플레이트
                    "-ac", "2",      # 스테레오
                    "-c:a", "pcm_s16le",  # 무손실 코덱
                    "-y",            # 덮어쓰기
                    str(temp_normalized)
                ]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8',
                    env=env,
                    errors='replace'
                )
            else:
                # Linux/Mac에서는 기본 방식 사용
                cmd = [
                    str(self.ffmpeg_path),
                    "-i", input_path,
                    "-af", f"loudnorm=I={target}",
                    "-ar", "44100",  # 표준 샘플레이트
                    "-ac", "2",      # 스테레오
                    "-c:a", "pcm_s16le",  # 무손실 코덱
                    "-y",            # 덮어쓰기
                    str(temp_normalized)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"오디오 정규화 실패: {result.stderr}")
                return False
            
            # 최종 출력 형식으로 변환
            if sys.platform == "win32":
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                
                # 최종 출력 (MP3로 변환)
                cmd = [
                    str(self.ffmpeg_path),
                    "-i", str(temp_normalized),
                    "-c:a", "libmp3lame",
                    "-b:a", "192k",  # 표준 비트레이트
                    "-ar", "44100",  # 표준 샘플레이트
                    "-ac", "2",      # 스테레오
                    "-y",            # 덮어쓰기
                    output_path
                ]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8',
                    env=env,
                    errors='replace'
                )
            else:
                # Linux/Mac에서는 기본 방식 사용
                cmd = [
                    str(self.ffmpeg_path),
                    "-i", str(temp_normalized),
                    "-c:a", "libmp3lame",
                    "-b:a", "192k",  # 표준 비트레이트
                    "-ar", "44100",  # 표준 샘플레이트
                    "-ac", "2",      # 스테레오
                    "-y",            # 덮어쓰기
                    output_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"최종 변환 실패: {result.stderr}")
                return False
            
            logger.info(f"간단한 정규화 완료: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"간단한 오디오 정규화 중 오류: {e}")
            return False
        finally:
            # 임시 파일 정리
            self._cleanup_temp_files(*temp_files)
    
    def get_normalization_info(self, audio_path: str) -> dict:
        """
        오디오 파일의 정규화 필요성 분석
        
        Parameters:
        -----------
        audio_path : str
            분석할 오디오 파일 경로
            
        Returns:
        --------
        dict
            정규화 정보
        """
        try:
            stats = self.get_audio_stats(audio_path)
            
            if "error" in stats:
                return stats
            
            mean_volume = stats.get("mean_volume")
            max_volume = stats.get("max_volume")
            
            if mean_volume is None or max_volume is None:
                return {"error": "볼륨 정보를 가져올 수 없습니다."}
            
            # 정규화 필요성 판단
            needs_normalization = False
            reason = ""
            
            if mean_volume < self.target_dbfs - 5:
                needs_normalization = True
                reason = f"평균 볼륨이 너무 낮음 ({mean_volume} dBFS)"
            elif mean_volume > self.target_dbfs + 5:
                needs_normalization = True
                reason = f"평균 볼륨이 너무 높음 ({mean_volume} dBFS)"
            elif max_volume > -1.0:
                needs_normalization = True
                reason = f"최대 볼륨이 클리핑 임계값을 초과 ({max_volume} dBFS)"
            
            return {
                "needs_normalization": needs_normalization,
                "reason": reason,
                "current_mean_volume": mean_volume,
                "current_max_volume": max_volume,
                "target_volume": self.target_dbfs,
                "volume_difference": mean_volume - self.target_dbfs
            }
            
        except Exception as e:
            logger.error(f"정규화 정보 분석 중 오류: {e}")
            return {"error": str(e)}
    
    def cleanup_all_temp_files(self):
        """
        모든 임시 파일 정리
        """
        try:
            if not self.temp_dir.exists():
                return
            
            count = 0
            for temp_file in self.temp_dir.glob("*"):
                if temp_file.is_file():
                    try:
                        temp_file.unlink()
                        count += 1
                        logger.debug(f"임시 파일 삭제: {temp_file}")
                    except Exception as e:
                        logger.warning(f"임시 파일 삭제 실패: {temp_file} - {e}")
            
            logger.info(f"임시 파일 정리 완료: {count}개 파일 삭제")
            return count
            
        except Exception as e:
            logger.error(f"임시 파일 정리 중 오류: {e}")
            return 0
    
    def get_temp_dir_info(self):
        """
        임시 디렉토리 정보 반환
        """
        try:
            if not self.temp_dir.exists():
                return {"error": "임시 디렉토리가 존재하지 않습니다."}
            
            files = list(self.temp_dir.glob("*"))
            total_size = sum(f.stat().st_size for f in files if f.is_file())
            
            return {
                "temp_dir": str(self.temp_dir),
                "file_count": len(files),
                "total_size_bytes": total_size,
                "total_size_mb": total_size / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"임시 디렉토리 정보 조회 중 오류: {e}")
            return {"error": str(e)}

# 싱글톤 인스턴스
audio_normalizer = AudioNormalizer() 
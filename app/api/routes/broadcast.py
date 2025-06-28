#!/usr/bin/env python3
"""
방송 제어 API 라우터 (broadcast_controller 단일 기반)
"""
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
from pathlib import Path

from ...services.broadcast_controller import broadcast_controller
from ...core.config import config, setup_logging

# 중앙 로깅 설정 사용
logger = setup_logging(__name__)

router = APIRouter(
    tags=["broadcast"],
    responses={404: {"description": "Not found"}},
)

AUDIO_DIR = Path(config.audio_dir)
os.makedirs(AUDIO_DIR, exist_ok=True)

# 시스템 정보
@router.get("/", response_model=Dict[str, Any])
async def get_system_info():
    info = broadcast_controller.get_status_summary()
    return {
        "system": {
            "version": config.app_version,
            "target_ip": info["target_ip"],
            "target_port": info["target_port"]
        },
        "devices": {
            "total": info["total_devices"],
            "active_rooms": info["active_rooms"]
        },
        "message": "방송 시스템 API (broadcast_controller 기반)"
    }

# 장치 상태 매트릭스
@router.get("/status", response_model=Dict[str, Any])
async def get_device_status():
    summary = broadcast_controller.get_status_summary()
    matrix = []
    for row in range(1, 5):
        row_data = []
        for col in range(1, 17):
            room_id = row * 100 + col
            status = room_id in summary["active_rooms"]
            row_data.append({
                "room_id": room_id,
                "position": {"row": row, "col": col},
                "active": status
            })
        matrix.append(row_data)
    return {
        "success": True,
        "matrix": matrix,
        "summary": {
            "active_rooms": summary["active_rooms"],
            "active_count": summary["active_count"],
            "total_devices": summary["total_devices"]
        }
    }

# 네트워크 연결 테스트
@router.post("/test-connection", response_model=Dict[str, Any])
async def test_network_connection():
    success = broadcast_controller.test_connection()
    info = broadcast_controller.get_status_summary()
    return {
        "success": success,
        "target_ip": info["target_ip"],
        "target_port": info["target_port"],
        "message": "연결 성공" if success else "연결 실패"
    }

# 개별 장치 제어
@router.post("/devices/control", response_model=Dict[str, Any])
async def control_device(
    row: int = Body(..., description="행 번호 (1-4)", ge=1, le=4),
    col: int = Body(..., description="열 번호 (1-16)", ge=1, le=16),
    state: bool = Body(..., description="장치 상태 (true: 켜기, false: 끄기)")
):
    room_id = row * 100 + col
    try:
        if state:
            success = broadcast_controller.control_device_single(f"{row}-{col}", 1)
            action = "켜기"
        else:
            success = broadcast_controller.control_device_single(f"{row}-{col}", 0)
            action = "끄기"
        return {
            "success": success,
            "room_id": room_id,
            "position": {"row": row, "col": col},
            "action": action,
            "state": state,
            "message": f"방{room_id} {action} {'성공' if success else '실패'}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"장치 제어 오류: {e}")
        raise HTTPException(status_code=500, detail=f"장치 제어 실패: {str(e)}")

# 여러 방 제어
@router.post("/rooms/control", response_model=Dict[str, Any])
async def control_rooms(
    room_ids: List[int] = Body(..., description="제어할 방 번호 리스트 (예: [101, 102, 201])"),
    state: bool = Body(True, description="상태 (true: 켜기, false: 끄기)")
):
    try:
        device_names = [f"{room_id//100}-{room_id%100}" for room_id in room_ids]
        success = broadcast_controller.control_multiple_devices(device_names, 1 if state else 0)
        return {
            "success": success,
            "requested_rooms": sorted(room_ids),
            "action": "켜기" if state else "끄기",
            "message": f"방 {'켜기' if state else '끄기'} {'성공' if success else '실패'}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"방 제어 오류: {e}")
        raise HTTPException(status_code=500, detail=f"방 제어 실패: {str(e)}")

# 모든 장치 끄기
@router.post("/all-off", response_model=Dict[str, Any])
async def turn_off_all_devices():
    try:
        success = broadcast_controller.broadcast_manager.turn_off_all_devices()
        return {
            "success": success,
            "action": "전체 끄기",
            "message": "모든 장치 끄기 " + ("성공" if success else "실패"),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"전체 끄기 오류: {e}")
        raise HTTPException(status_code=500, detail=f"전체 끄기 실패: {str(e)}")

# 큐 현황 확인
@router.get("/queue", response_model=Dict[str, Any])
async def get_queue_status():
    """방송 큐 현황 확인"""
    try:
        status = broadcast_controller.get_queue_status()
        return {
            "success": True,
            "queue_status": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"큐 현황 확인 오류: {e}")
        raise HTTPException(status_code=500, detail=f"큐 현황 확인 실패: {str(e)}")

# 큐 현황 콘솔 출력
@router.post("/queue/print", response_model=Dict[str, Any])
async def print_queue_status():
    """큐 현황을 콘솔에 출력"""
    try:
        broadcast_controller.print_queue_status()
        return {
            "success": True,
            "message": "큐 현황이 콘솔에 출력되었습니다.",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"큐 현황 출력 오류: {e}")
        raise HTTPException(status_code=500, detail=f"큐 현황 출력 실패: {str(e)}")

# 텍스트 방송
@router.post("/text", response_model=Dict[str, Any])
async def broadcast_text(
    background_tasks: BackgroundTasks,
    text: str = Form(..., description="방송할 텍스트"),
    target_rooms: Optional[str] = Form(None, description="방송할 방 번호 (쉼표로 구분, 예: '101,102,201')"),
    language: str = Form("ko", description="텍스트 언어 (ko, en, zh, ja, es, fr)"),
    auto_off: bool = Form(True, description="방송 후 자동으로 장치 끄기")
):
    """텍스트 방송 프리뷰 생성"""
    try:
        if target_rooms:
            room_list = [int(r.strip()) for r in target_rooms.split(",") if r.strip()]
            device_names = [f"{room_id//100}-{room_id%100}" for room_id in room_list]
        else:
            # 전체 방송: 현재 활성화된 방들
            summary = broadcast_controller.get_status_summary()
            device_names = [f"{room_id//100}-{room_id%100}" for room_id in summary["active_rooms"]]
            if not device_names:
                raise HTTPException(status_code=400, detail="활성화된 방이 없습니다. 먼저 방을 활성화하세요.")
        
        # 프리뷰 생성
        params = {
            'text': text,
            'target_devices': device_names,
            'end_devices': device_names if auto_off else None,
            'language': language
        }
        
        preview_info = broadcast_controller.create_preview('text', params)
        if not preview_info:
            raise HTTPException(status_code=500, detail="프리뷰 생성 실패")
        
        # 상태에 따른 메시지 생성
        queue_status = preview_info.get("queue_status", "unknown")
        if queue_status == "ready":
            message = "텍스트 방송 프리뷰가 생성되었습니다. 즉시 시작 가능합니다."
        elif queue_status == "waiting":
            current_broadcast = preview_info.get("current_broadcast", {})
            message = f"텍스트 방송 프리뷰가 생성되었습니다. 현재 {current_broadcast.get('job_type', '방송')}이 진행 중입니다."
        elif queue_status == "queued":
            message = "텍스트 방송 프리뷰가 생성되었습니다. 대기 중인 방송이 있습니다."
        else:
            message = "텍스트 방송 프리뷰가 생성되었습니다. 확인 후 승인해주세요."
        
        return {
            "success": True,
            "status": "preview_ready",
            "preview_id": preview_info["preview_id"],
            "preview_filename": preview_info["preview_id"],
            "preview_info": preview_info,
            "message": message,
            "instructions": {
                "preview_id": preview_info["preview_id"],
                "preview_filename": preview_info["preview_id"],
                "listen_preview": f"GET /api/broadcast/preview/audio/{preview_info['preview_id']}",
                "approve_preview": f"POST /api/broadcast/preview/approve/{preview_info['preview_id']}",
                "reject_preview": f"POST /api/broadcast/preview/reject/{preview_info['preview_id']}",
                "check_all_previews": "GET /api/broadcast/previews"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"텍스트 프리뷰 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=f"텍스트 프리뷰 생성 실패: {str(e)}")

# 오디오 방송
@router.post("/audio", response_model=Dict[str, Any])
async def broadcast_audio(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(..., description="방송할 오디오 파일"),
    target_rooms: Optional[str] = Form(None, description="방송할 방 번호 (쉼표로 구분)"),
    auto_off: bool = Form(True, description="방송 후 자동으로 장치 끄기")
):
    """오디오 방송 프리뷰 생성"""
    try:
        # 파일 저장
        file_extension = os.path.splitext(audio_file.filename)[1]
        temp_path = AUDIO_DIR / f"preview_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
        with open(temp_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        # 파일 길이 체크 (5분 = 300초 제한)
        try:
            logger.info(f"오디오 파일 길이 확인 시작: {temp_path}")
            duration = broadcast_controller._get_audio_duration_with_ffprobe(str(temp_path))
            logger.info(f"오디오 파일 길이 확인 완료: {duration:.1f}초")
            
            if duration > 300:  # 5분 초과
                logger.warning(f"오디오 파일이 너무 김: {duration:.1f}초 > 300초")
                # 임시 파일 삭제
                if temp_path.exists():
                    temp_path.unlink()
                    logger.info(f"임시 파일 삭제: {temp_path}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"오디오 파일이 너무 깁니다. 현재 길이: {duration:.1f}초, 최대 허용 길이: 300초 (5분)"
                )
            print(f"[*] 오디오 파일 길이 확인: {duration:.1f}초")
        except HTTPException:
            # HTTPException은 그대로 재발생
            raise
        except Exception as e:
            logger.error(f"오디오 파일 길이 확인 실패: {e}")
            # 길이 확인 실패 시에도 임시 파일 삭제
            if temp_path.exists():
                temp_path.unlink()
                logger.info(f"길이 확인 실패로 임시 파일 삭제: {temp_path}")
            raise HTTPException(
                status_code=400, 
                detail=f"오디오 파일 길이 확인 실패: {str(e)}"
            )
        
        # 대상 장치 설정
        if target_rooms:
            room_list = [int(r.strip()) for r in target_rooms.split(",") if r.strip()]
            device_names = [f"{room_id//100}-{room_id%100}" for room_id in room_list]
        else:
            summary = broadcast_controller.get_status_summary()
            device_names = [f"{room_id//100}-{room_id%100}" for room_id in summary["active_rooms"]]
            if not device_names:
                raise HTTPException(status_code=400, detail="활성화된 방이 없습니다. 먼저 방을 활성화하세요.")
        
        # 프리뷰 생성
        params = {
            'audio_path': str(temp_path),
            'target_devices': device_names,
            'end_devices': device_names if auto_off else None
        }
        
        preview_info = broadcast_controller.create_preview('audio', params)
        if not preview_info:
            raise HTTPException(status_code=500, detail="프리뷰 생성 실패")
        
        # 상태에 따른 메시지 생성
        queue_status = preview_info.get("queue_status", "unknown")
        if queue_status == "ready":
            message = "오디오 방송 프리뷰가 생성되었습니다. 즉시 시작 가능합니다."
        elif queue_status == "waiting":
            current_broadcast = preview_info.get("current_broadcast", {})
            message = f"오디오 방송 프리뷰가 생성되었습니다. 현재 {current_broadcast.get('job_type', '방송')}이 진행 중입니다."
        elif queue_status == "queued":
            message = "오디오 방송 프리뷰가 생성되었습니다. 대기 중인 방송이 있습니다."
        else:
            message = "오디오 방송 프리뷰가 생성되었습니다. 확인 후 승인해주세요."
        
        return {
            "success": True,
            "status": "preview_ready",
            "preview_id": preview_info["preview_id"],
            "preview_filename": preview_info["preview_id"],
            "preview_info": preview_info,
            "message": message,
            "instructions": {
                "preview_id": preview_info["preview_id"],
                "preview_filename": preview_info["preview_id"],
                "listen_preview": f"GET /api/broadcast/preview/audio/{preview_info['preview_id']}",
                "approve_preview": f"POST /api/broadcast/preview/approve/{preview_info['preview_id']}",
                "reject_preview": f"POST /api/broadcast/preview/reject/{preview_info['preview_id']}",
                "check_all_previews": "GET /api/broadcast/previews"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        # HTTPException은 그대로 재발생
        raise
    except Exception as e:
        logger.error(f"오디오 프리뷰 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=f"오디오 프리뷰 생성 실패: {str(e)}")

# 방송 중지
@router.post("/stop", response_model=Dict[str, Any])
async def stop_broadcast():
    try:
        stop_success = broadcast_controller.stop_broadcast()
        return {
            "success": stop_success,
            "action": "방송 중지 및 장치 끄기",
            "message": "방송 중지 " + ("성공" if stop_success else "실패"),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"방송 중지 오류: {e}")
        raise HTTPException(status_code=500, detail=f"방송 중지 실패: {str(e)}")

# 프리뷰 승인
@router.post("/preview/approve/{preview_id}", response_model=Dict[str, Any])
async def approve_preview(preview_id: str):
    """프리뷰 승인 및 방송 큐에 추가"""
    try:
        # 방송 요청
        result = broadcast_controller.approve_preview(preview_id)
        
        if result:
            preview_info = broadcast_controller.get_preview_info(preview_id)
            if preview_info:
                estimated_start = preview_info.get("estimated_start_time")
                estimated_end = preview_info.get("estimated_end_time")
                
                # 시간 정보 포맷팅
                start_time_str = ""
                end_time_str = ""
                if estimated_start:
                    start_dt = datetime.fromisoformat(estimated_start)
                    start_time_str = start_dt.strftime("%H:%M:%S")
                if estimated_end:
                    end_dt = datetime.fromisoformat(estimated_end)
                    end_time_str = end_dt.strftime("%H:%M:%S")
                
                message = "방송이 승인되었습니다."
                if start_time_str and end_time_str:
                    message += f" 예상 시작: {start_time_str}, 예상 종료: {end_time_str}"
                elif start_time_str:
                    message += f" 예상 시작: {start_time_str}"
                
                return {
                    "success": True,
                    "status": "broadcast_approved",
                    "message": message,
                    "preview_id": preview_id,
                    "estimated_start_time": estimated_start,
                    "estimated_end_time": estimated_end,
                    "formatted_start_time": start_time_str,
                    "formatted_end_time": end_time_str,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": True,
                    "status": "broadcast_approved",
                    "message": "방송이 승인되었습니다.",
                    "preview_id": preview_id,
                    "timestamp": datetime.now().isoformat()
                }
        else:
            raise HTTPException(status_code=400, detail="프리뷰 승인 실패")
        
    except Exception as e:
        logger.error(f"프리뷰 승인 오류: {e}")
        raise HTTPException(status_code=500, detail=f"프리뷰 승인 실패: {str(e)}")

# 프리뷰 거부
@router.post("/preview/reject/{preview_id}", response_model=Dict[str, Any])
async def reject_preview(preview_id: str):
    """프리뷰 거부"""
    try:
        success = broadcast_controller.reject_preview(preview_id)
        if not success:
            raise HTTPException(status_code=400, detail="프리뷰 거부 실패")
        
        return {
            "success": True,
            "preview_id": preview_id,
            "message": "프리뷰가 거부되었습니다.",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"프리뷰 거부 오류: {e}")
        raise HTTPException(status_code=500, detail=f"프리뷰 거부 실패: {str(e)}")

# 프리뷰 정보 조회
@router.get("/preview/{preview_id}", response_model=Dict[str, Any])
async def get_preview_info(preview_id: str):
    """프리뷰 정보 조회"""
    try:
        preview_info = broadcast_controller.get_preview_info(preview_id)
        if not preview_info:
            raise HTTPException(status_code=404, detail="프리뷰를 찾을 수 없습니다.")
        
        return {
            "success": True,
            "preview_info": preview_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"프리뷰 정보 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"프리뷰 정보 조회 실패: {str(e)}")

# 모든 프리뷰 조회
@router.get("/previews", response_model=Dict[str, Any])
async def get_all_previews():
    """모든 대기 중인 프리뷰 조회"""
    try:
        previews = broadcast_controller.get_all_previews()
        return {
            "success": True,
            "previews": previews,
            "count": len(previews),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"프리뷰 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"프리뷰 목록 조회 실패: {str(e)}")

# 프리뷰 오디오 파일 제공
@router.get("/preview/audio/{preview_id}")
async def get_preview_audio(preview_id: str):
    """프리뷰 오디오 파일 제공"""
    try:
        # .mp3 확장자가 포함된 경우 제거
        if preview_id.endswith('.mp3'):
            preview_id = preview_id[:-4]
        
        # 먼저 메모리에서 프리뷰 정보 확인
        preview_info = broadcast_controller.get_preview_info(preview_id)
        
        if preview_info:
            # 메모리에 프리뷰 정보가 있는 경우
            preview_path = preview_info.get("preview_path")
            if not preview_path or not Path(preview_path).exists():
                raise HTTPException(status_code=404, detail="프리뷰 오디오 파일을 찾을 수 없습니다.")
        else:
            # 메모리에 프리뷰 정보가 없는 경우, 파일 시스템에서 직접 확인
            preview_path = Path("D:/previews") / f"{preview_id}.mp3"
            if not preview_path.exists():
                raise HTTPException(status_code=404, detail="프리뷰를 찾을 수 없습니다.")
        
        from fastapi.responses import FileResponse
        return FileResponse(preview_path, media_type="audio/mpeg")
        
    except Exception as e:
        logger.error(f"프리뷰 오디오 제공 오류: {e}")
        raise HTTPException(status_code=500, detail=f"프리뷰 오디오 제공 실패: {str(e)}")

# 장치 상태 복원 기능 제어
@router.post("/device-restore/set")
async def set_device_restore_enabled(enabled: bool = Form(..., description="장치 상태 복원 기능 활성화 여부")):
    """장치 상태 복원 기능 활성화/비활성화 설정"""
    try:
        broadcast_controller.set_restore_device_states(enabled)
        return {
            "success": True,
            "restore_enabled": enabled,
            "message": f"장치 상태 복원 기능이 {'활성화' if enabled else '비활성화'}되었습니다.",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"장치 상태 복원 설정 오류: {e}")
        raise HTTPException(status_code=500, detail=f"장치 상태 복원 설정 실패: {str(e)}")

@router.get("/device-restore/info")
async def get_device_restore_info():
    """장치 상태 복원 기능 정보 조회"""
    try:
        info = broadcast_controller.get_device_state_backup_info()
        return {
            "success": True,
            "info": info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"장치 상태 복원 정보 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"장치 상태 복원 정보 조회 실패: {str(e)}")

@router.post("/device-restore/clear")
async def clear_device_state_backup():
    """저장된 장치 상태 백업 데이터 정리"""
    try:
        # 백업 데이터 정리
        broadcast_controller.device_state_backup.clear()
        return {
            "success": True,
            "message": "저장된 장치 상태 백업 데이터가 정리되었습니다.",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"장치 상태 백업 정리 오류: {e}")
        raise HTTPException(status_code=500, detail=f"장치 상태 백업 정리 실패: {str(e)}")

# 임시 파일 관리
@router.get("/temp-files/info")
async def get_temp_files_info():
    """임시 파일 디렉토리 정보 조회"""
    try:
        from ...utils.audio_normalizer import audio_normalizer
        info = audio_normalizer.get_temp_dir_info()
        return {
            "success": True,
            "temp_files_info": info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"임시 파일 정보 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"임시 파일 정보 조회 실패: {str(e)}")

@router.post("/temp-files/cleanup")
async def cleanup_temp_files():
    """임시 파일 정리"""
    try:
        from ...utils.audio_normalizer import audio_normalizer
        count = audio_normalizer.cleanup_all_temp_files()
        return {
            "success": True,
            "cleaned_files_count": count,
            "message": f"{count}개의 임시 파일이 정리되었습니다.",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"임시 파일 정리 오류: {e}")
        raise HTTPException(status_code=500, detail=f"임시 파일 정리 실패: {str(e)}")

# 오디오 정규화 정보
@router.get("/audio-normalizer/info")
async def get_audio_normalizer_info():
    """오디오 정규화 설정 정보 조회"""
    try:
        from ...utils.audio_normalizer import audio_normalizer
        return {
            "success": True,
            "normalizer_info": {
                "target_dbfs": audio_normalizer.target_dbfs,
                "headroom": audio_normalizer.headroom,
                "temp_dir": str(audio_normalizer.temp_dir),
                "ffmpeg_path": str(audio_normalizer.ffmpeg_path) if audio_normalizer.ffmpeg_path else None,
                "ffprobe_path": str(audio_normalizer.ffprobe_path) if audio_normalizer.ffprobe_path else None
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"오디오 정규화 정보 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"오디오 정규화 정보 조회 실패: {str(e)}") 
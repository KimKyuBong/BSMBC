#!/usr/bin/env python3
"""
방송 제어 API 라우터 (broadcast_controller 단일 기반)
"""
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import os
from pathlib import Path

from ...services.broadcast_controller import broadcast_controller
from ...core.config import config

router = APIRouter(
    tags=["broadcast"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)
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

# 텍스트 방송
@router.post("/text", response_model=Dict[str, Any])
async def broadcast_text(
    background_tasks: BackgroundTasks,
    text: str = Form(..., description="방송할 텍스트"),
    target_rooms: Optional[str] = Form(None, description="방송할 방 번호 (쉼표로 구분, 예: '101,102,201')"),
    language: str = Form("ko", description="텍스트 언어 (ko, en, zh, ja, es, fr)"),
    auto_off: bool = Form(True, description="방송 후 자동으로 장치 끄기")
):
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
        # 방송 실행
        broadcast_success = broadcast_controller.broadcast_text(text, device_names, language=language)
        # 방송 후 자동 끄기
        if auto_off and broadcast_success:
            background_tasks.add_task(broadcast_controller.broadcast_manager.turn_off_all_devices)
        return {
            "success": broadcast_success,
            "text": text,
            "language": language,
            "target_rooms": device_names,
            "auto_off": auto_off,
            "message": "텍스트 방송 " + ("성공" if broadcast_success else "실패"),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"텍스트 방송 오류: {e}")
        raise HTTPException(status_code=500, detail=f"텍스트 방송 실패: {str(e)}")

# 오디오 방송
@router.post("/audio", response_model=Dict[str, Any])
async def broadcast_audio(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(..., description="방송할 오디오 파일"),
    target_rooms: Optional[str] = Form(None, description="방송할 방 번호 (쉼표로 구분)"),
    auto_off: bool = Form(True, description="방송 후 자동으로 장치 끄기")
):
    try:
        file_extension = os.path.splitext(audio_file.filename)[1]
        temp_path = AUDIO_DIR / f"broadcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
        with open(temp_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        if target_rooms:
            room_list = [int(r.strip()) for r in target_rooms.split(",") if r.strip()]
            device_names = [f"{room_id//100}-{room_id%100}" for room_id in room_list]
        else:
            summary = broadcast_controller.get_status_summary()
            device_names = [f"{room_id//100}-{room_id%100}" for room_id in summary["active_rooms"]]
            if not device_names:
                raise HTTPException(status_code=400, detail="활성화된 방이 없습니다.")
        broadcast_success = broadcast_controller.broadcast_audio(str(temp_path), device_names)
        if auto_off and broadcast_success:
            background_tasks.add_task(broadcast_controller.broadcast_manager.turn_off_all_devices)
        background_tasks.add_task(lambda: os.remove(temp_path) if temp_path.exists() else None)
        return {
            "success": broadcast_success,
            "filename": audio_file.filename,
            "target_rooms": device_names,
            "auto_off": auto_off,
            "message": "오디오 방송 " + ("성공" if broadcast_success else "실패"),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"오디오 방송 오류: {e}")
        raise HTTPException(status_code=500, detail=f"오디오 방송 실패: {str(e)}")

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
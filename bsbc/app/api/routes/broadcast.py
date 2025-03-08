#!/usr/bin/env python3
"""
방송 제어 API 라우터
방송 제어 관련 API 엔드포인트를 정의합니다.
"""
from fastapi import APIRouter, HTTPException, Query, Path, Body
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from ...models.device import DeviceInfo, DeviceState, DeviceGroup, DeviceStateResponse, SystemState
from ...services.broadcast_controller import broadcast_controller

# 라우터 생성
router = APIRouter(
    prefix="/api/broadcast",
    tags=["broadcast"],
    responses={404: {"description": "Not found"}},
)

# 로거 설정
logger = logging.getLogger(__name__)

@router.get("/", response_model=Dict[str, Any])
async def get_broadcast_info():
    """
    방송 시스템 정보 조회
    """
    return {
        "version": broadcast_controller.get_version(),
        "target_ip": broadcast_controller.network_manager.target_ip,
        "target_port": broadcast_controller.network_manager.target_port,
        "status": "connected" if broadcast_controller.system_initialized else "disconnected"
    }

@router.get("/devices", response_model=List[DeviceInfo])
async def get_all_devices():
    """
    모든 장치 목록 조회
    """
    devices = []
    
    # 장치 매퍼에서 모든 장치 정보 조회
    for coords, name in broadcast_controller.device_mapper.device_map.items():
        row, col = coords
        device_info = DeviceInfo(
            name=name,
            coords={"row": row, "col": col},
            description=f"{name} 장치"
        )
        devices.append(device_info)
    
    return devices

@router.get("/devices/{device_name}", response_model=DeviceInfo)
async def get_device_info(device_name: str = Path(..., description="장치 이름")):
    """
    특정 장치 정보 조회
    """
    coords = broadcast_controller.device_mapper.get_device_coords(device_name)
    if not coords:
        raise HTTPException(status_code=404, detail=f"장치를 찾을 수 없음: {device_name}")
    
    row, col = coords
    return DeviceInfo(
        name=device_name,
        coords={"row": row, "col": col},
        description=f"{device_name} 장치"
    )

@router.post("/control", response_model=DeviceStateResponse)
async def control_device(device: DeviceState = Body(..., description="제어할 장치 및 상태")):
    """
    장치 제어
    """
    logger.info(f"장치 제어 요청: {device.device_name}, 상태: {device.state}")
    
    # 장치 제어 실행
    success = broadcast_controller.control_device(device.device_name, 1 if device.state else 0)
    
    # 현재 시간 정보
    now = datetime.now().isoformat()
    
    # 응답 생성
    response = DeviceStateResponse(
        device_name=device.device_name,
        state=device.state,
        response_time=now,
        success=success
    )
    
    return response

@router.post("/control/group", response_model=List[DeviceStateResponse])
async def control_device_group(
    group: DeviceGroup = Body(..., description="제어할 장치 그룹"),
    state: bool = Query(True, description="설정할 상태 (true: 켜기, false: 끄기)")
):
    """
    장치 그룹 일괄 제어
    """
    logger.info(f"장치 그룹 제어 요청: {group.group_name}, 장치: {group.devices}, 상태: {state}")
    
    # 장치 그룹 제어 실행
    success = broadcast_controller.control_multiple_devices(group.devices, 1 if state else 0)
    
    # 현재 시간 정보
    now = datetime.now().isoformat()
    
    # 응답 생성
    responses = []
    for device_name in group.devices:
        response = DeviceStateResponse(
            device_name=device_name,
            state=state,
            response_time=now,
            success=success
        )
        responses.append(response)
    
    return responses

@router.get("/state", response_model=SystemState)
async def get_system_state():
    """
    시스템 전체 상태 조회
    """
    # 시스템 초기화 여부 확인
    if not broadcast_controller.system_initialized:
        # 시스템 상태 초기화 시도
        success = broadcast_controller.initialize_system_state()
        if not success:
            raise HTTPException(status_code=500, detail="시스템 상태 초기화 실패")
    
    # 장치별 상태 정보 생성
    device_states = {}
    for coords, name in broadcast_controller.device_mapper.device_map.items():
        # 현재는 3학년 1반 상태만 알 수 있음
        if name == "3-1":
            device_states[name] = 301 in broadcast_controller.active_rooms
        elif name == "3-2":
            device_states[name] = 302 in broadcast_controller.active_rooms
        else:
            # 다른 장치는 상태 정보 없음
            device_states[name] = False
    
    # 시스템 상태 반환
    return SystemState(
        active_rooms=broadcast_controller.active_rooms,
        device_states=device_states,
        last_updated=datetime.now().isoformat()
    )

@router.post("/state/initialize", response_model=Dict[str, Any])
async def initialize_system():
    """
    시스템 상태 초기화
    서버에 연결하여 현재 상태 정보를 가져옵니다.
    """
    success = broadcast_controller.initialize_system_state()
    
    if not success:
        raise HTTPException(status_code=500, detail="시스템 상태 초기화 실패")
    
    return {
        "success": True,
        "active_rooms": list(broadcast_controller.active_rooms),
        "message": "시스템 상태가 초기화되었습니다."
    }

@router.post("/test", response_model=Dict[str, Any])
async def run_test_sequence():
    """
    테스트 패킷 시퀀스 실행
    """
    import threading
    
    def run_test():
        broadcast_controller.send_test_packets()
    
    thread = threading.Thread(target=run_test)
    thread.daemon = True
    thread.start()
    
    return {"status": "success", "message": "테스트 시퀀스가 시작되었습니다."}

@router.post("/mixers/control", response_model=Dict[str, Any])
async def control_mixer(
    mixer_id: int = Query(..., description="제어할 믹서 ID (1~16)", ge=1, le=16),
    state: bool = Query(True, description="설정할 상태 (true: 켜기, false: 끄기)")
):
    """
    개별 믹서 제어
    """
    try:
        success = broadcast_controller.control_mixer(mixer_id, 1 if state else 0)
        
        if success:
            return {
                "status": "success", 
                "message": f"믹서 {mixer_id}번이 {'켜졌습니다' if state else '꺼졌습니다'}"
            }
        else:
            raise HTTPException(status_code=500, detail=f"믹서 {mixer_id}번 제어 실패")
    except Exception as e:
        logger.error(f"믹서 제어 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"믹서 제어 중 오류: {str(e)}")

@router.post("/mixers/control/all", response_model=Dict[str, Any])
async def control_all_mixers(
    state: bool = Query(True, description="설정할 상태 (true: 모두 켜기, false: 모두 끄기)")
):
    """
    모든 믹서 동시 제어
    """
    try:
        success = broadcast_controller.control_all_mixers(1 if state else 0)
        
        if success:
            return {
                "status": "success", 
                "message": f"모든 믹서가 {'켜졌습니다' if state else '꺼졌습니다'}"
            }
        else:
            raise HTTPException(status_code=500, detail="모든 믹서 제어 실패")
    except Exception as e:
        logger.error(f"모든 믹서 제어 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"모든 믹서 제어 중 오류: {str(e)}")

@router.post("/mixers/test", response_model=Dict[str, Any])
async def run_mixer_test():
    """
    믹서 테스트 시퀀스 실행
    """
    import threading
    
    def run_test():
        broadcast_controller.test_mixer_sequence()
    
    thread = threading.Thread(target=run_test)
    thread.daemon = True
    thread.start()
    
    return {"status": "success", "message": "믹서 테스트 시퀀스가 시작되었습니다."}

@router.post("/input_channels/control", response_model=Dict[str, Any])
async def control_input_channel(
    channel_id: int = Query(..., description="제어할 입력 채널 ID (1~16)", ge=1, le=16),
    state: bool = Query(True, description="설정할 상태 (true: 켜기, false: 끄기)")
):
    """
    개별 입력 채널 제어
    """
    try:
        success = broadcast_controller.control_input_channel(channel_id, 1 if state else 0)
        
        channel_type = "마이크" if channel_id in [1, 2, 11] else "라인"
        
        if success:
            return {
                "status": "success", 
                "message": f"입력 채널 {channel_id}번({channel_type})이 {'켜졌습니다' if state else '꺼졌습니다'}"
            }
        else:
            raise HTTPException(status_code=500, detail=f"입력 채널 {channel_id}번 제어 실패")
    except Exception as e:
        logger.error(f"입력 채널 제어 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"입력 채널 제어 중 오류: {str(e)}")

@router.post("/input_channels/control/all", response_model=Dict[str, Any])
async def control_all_input_channels(
    state: bool = Query(True, description="설정할 상태 (true: 모두 켜기, false: 모두 끄기)"),
    channel_type: str = Query("all", description="채널 타입 ('mic': 마이크 타입만, 'line': 라인 타입만, 'all': 모든 채널)")
):
    """
    모든 입력 채널 동시 제어
    """
    try:
        if channel_type not in ["mic", "line", "all"]:
            raise HTTPException(status_code=400, detail="채널 타입은 'mic', 'line', 'all' 중 하나여야 합니다.")
        
        success = broadcast_controller.control_all_input_channels(1 if state else 0, channel_type)
        
        type_str = {
            "mic": "마이크 타입",
            "line": "라인 타입",
            "all": "모든"
        }.get(channel_type, "모든")
        
        if success:
            return {
                "status": "success", 
                "message": f"{type_str} 입력 채널이 {'켜졌습니다' if state else '꺼졌습니다'}"
            }
        else:
            raise HTTPException(status_code=500, detail=f"{type_str} 입력 채널 제어 실패")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"입력 채널 제어 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"입력 채널 제어 중 오류: {str(e)}")

@router.post("/input_channels/test", response_model=Dict[str, Any])
async def run_input_channel_test():
    """
    입력 채널 테스트 시퀀스 실행
    """
    import threading
    
    def run_test():
        broadcast_controller.test_input_channels()
    
    thread = threading.Thread(target=run_test)
    thread.daemon = True
    thread.start()
    
    return {"status": "success", "message": "입력 채널 테스트 시퀀스가 시작되었습니다."} 
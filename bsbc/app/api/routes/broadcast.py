#!/usr/bin/env python3
"""
방송 제어 API 라우터
방송 제어 관련 API 엔드포인트를 정의합니다.
"""
#
# TODO: API 엔드포인트 정리 계획
# --------------------------------------------------------------------------------------
# 1. 중복된 엔드포인트 정리:
#    - schedule 관련 엔드포인트를 /api/schedule/ 아래로 통합
#    - broadcast.py에서 스케줄 관련 엔드포인트 제거
#
# 2. 명확한 URL 구조 정립:
#    - /api/broadcast/ - 실시간 방송 제어
#    - /api/schedule/  - 예약 방송 관리
#    - /api/device/    - 장치 관리 및 상태
#    - /api/system/    - 시스템 설정 및 상태
#
# 3. 버전 관리 도입:
#    - 향후 API 버전 관리 위해 /api/v1/broadcast/ 형태로 변경 고려
# --------------------------------------------------------------------------------------

from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form, BackgroundTasks, Request
from fastapi import Path as FastAPIPath  # Path를 FastAPIPath로 이름 변경
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import os
import uuid
import tempfile
from pathlib import Path
from fastapi import status
from werkzeug.utils import secure_filename
import time

from ...models.device import DeviceInfo, DeviceState, DeviceGroup, DeviceStateResponse, SystemState
from ...services.broadcast_controller import broadcast_controller
from ...core.config import config  # 수정: config 인스턴스 임포트

# 라우터 생성
router = APIRouter(
    tags=["broadcast"],
    responses={404: {"description": "Not found"}},
)

# 로거 설정
logger = logging.getLogger(__name__)

# 오디오 파일 저장 경로
AUDIO_DIR = Path(config.audio_dir)  # 수정: audio_dir 속성 직접 사용
os.makedirs(AUDIO_DIR, exist_ok=True)

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
async def get_device_info(device_name: str = FastAPIPath(..., description="장치 이름")):
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

@router.post("/audio", response_model=Dict[str, Any])
async def broadcast_audio(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(..., description="방송할 오디오 파일"),
    target_devices: str = Form(..., description="방송할 장치 목록 (쉼표로 구분)"),
    end_devices: Optional[str] = Form(None, description="방송 종료 후 끌 장치 목록 (쉼표로 구분)"),
    duration: Optional[int] = Form(None, description="방송 지속 시간(초) (미지정시 파일 길이만큼 재생)")
):
    """
    오디오 파일 업로드 방송 API
    """
    try:
        # 장치 목록 파싱
        target_device_list = [d.strip() for d in target_devices.split(",") if d.strip()]
        
        if not target_device_list:
            raise HTTPException(status_code=400, detail="방송 대상 장치가 지정되지 않았습니다")
            
        # 종료 시 끌 장치 목록 파싱 (지정된 경우)
        end_device_list = None
        if end_devices:
            end_device_list = [d.strip() for d in end_devices.split(",") if d.strip()]
        
        # 임시 파일 생성
        temp_file_path = AUDIO_DIR / f"{uuid.uuid4()}.wav"
        
        # 파일 저장
        with open(temp_file_path, "wb") as f:
            f.write(await audio_file.read())
        
        # 방송 시작
        success = broadcast_controller.broadcast_audio(
            audio_path=temp_file_path,
            target_devices=target_device_list,
            end_devices=end_device_list,
            duration=duration
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="방송 시작 실패")
            
        return {
            "status": "success",
            "message": "방송이 시작되었습니다",
            "filename": audio_file.filename,
            "target_devices": target_device_list,
            "end_devices": end_device_list or target_device_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("오디오 방송 처리 중 오류")
        raise HTTPException(status_code=500, detail=f"오디오 방송 처리 중 오류: {str(e)}")

@router.post("/text", response_model=Dict[str, Any])
async def broadcast_text(
    background_tasks: BackgroundTasks,
    text: str = Form(..., description="방송할 텍스트"),
    target_devices: str = Form(..., description="방송할 장치 목록 (쉼표로 구분)"),
    end_devices: Optional[str] = Form(None, description="방송 종료 후 끌 장치 목록 (쉼표로 구분)"),
    language: str = Form("ko", description="텍스트 언어 (ko, en, zh, ja, es, fr)")
):
    """
    텍스트 TTS 방송 API
    """
    try:
        # 장치 목록 파싱
        target_device_list = [d.strip() for d in target_devices.split(",") if d.strip()]
        
        if not target_device_list:
            raise HTTPException(status_code=400, detail="방송 대상 장치가 지정되지 않았습니다")
            
        # 종료 시 끌 장치 목록 파싱 (지정된 경우)
        end_device_list = None
        if end_devices:
            end_device_list = [d.strip() for d in end_devices.split(",") if d.strip()]
        
        # 로그에 전체 장치 목록 출력
        print(f"[*] 방송 대상 장치 목록: {target_device_list}")
        
        # 지원되는 언어인지 확인
        supported_languages = ["ko", "en", "zh", "ja", "es", "fr"]
        if language.lower() not in supported_languages:
            raise HTTPException(status_code=400, detail=f"지원되지 않는 언어입니다. 지원 언어: {', '.join(supported_languages)}")
        
        # 방송 시작
        success = broadcast_controller.broadcast_text(
            text=text,
            target_devices=target_device_list,
            end_devices=end_device_list,
            language=language
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="TTS 방송 시작 실패")
            
        return {
            "status": "success",
            "message": "TTS 방송이 시작되었습니다",
            "text_length": len(text),
            "target_devices": target_device_list,
            "end_devices": end_device_list or target_device_list,
            "language": language
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("TTS 방송 처리 중 오류")
        raise HTTPException(status_code=500, detail=f"TTS 방송 처리 중 오류: {str(e)}")

@router.post("/text/group", response_model=Dict[str, Any])
async def broadcast_text_to_group(
    background_tasks: BackgroundTasks,
    text: str = Form(..., description="방송할 텍스트"),
    group_name: str = Form(..., description="방송할 그룹명 (예: '1학년전체', '전체교실')"),
    end_devices: Optional[str] = Form(None, description="방송 종료 후 끌 장치 목록 (쉼표로 구분)"),
    language: str = Form("ko", description="텍스트 언어 (ko, en, zh, ja, es, fr)"),
    schedule_time: Optional[str] = Form(None, description="방송 예약 시간 (YYYY-MM-DD HH:MM:SS 형식)")
):
    """
    그룹 장치들에 텍스트 TTS 방송 API
    
    그룹명으로 방송 대상 장치를 지정합니다.
    그룹 예시: "1학년전체", "2학년전체", "3학년전체", "전체교실", "전체장치"
    """
    try:
        from ...core.device_mapping import device_mapper
        
        # 그룹 장치 목록 가져오기
        devices = device_mapper.get_group_devices(group_name)
        
        if devices is None:
            raise HTTPException(status_code=404, detail=f"장치 그룹을 찾을 수 없습니다: {group_name}")
        
        if not devices:
            raise HTTPException(status_code=400, detail=f"그룹에 등록된 장치가 없습니다: {group_name}")
            
        print(f"[*] 방송 대상 그룹: {group_name}, 장치 수: {len(devices)}")
        
        # 그룹 내 모든 장치 활성화
        results = device_mapper.broadcast_to_group(group_name, True)  # 상태 True = 켜기
        
        if results["fail_count"] > 0:
            logger.warning(f"일부 장치 활성화 실패: {results['fail_count']}개")
            
        # 종료 시 끌 장치 목록 파싱 (지정된 경우)
        end_device_list = None
        if end_devices:
            end_device_list = [d.strip() for d in end_devices.split(",") if d.strip()]
        else:
            end_device_list = devices  # 기본값은 방송 대상과 동일
            
        # 예약 방송인 경우
        if schedule_time:
            # 시간 형식 확인
            try:
                datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail="잘못된 시간 형식입니다. 'YYYY-MM-DD HH:MM:SS' 형식이어야 합니다."
                )
                
            # 예약 전에 활성화된 장치 비활성화 (예약 시점에 다시 활성화할 것이므로)
            device_mapper.broadcast_to_group(group_name, False)  # 상태 False = 끄기
                
            # 방송 예약
            job_id = broadcast_controller.schedule_broadcast_text(
                schedule_time=schedule_time,
                text=text,
                target_devices=devices,
                end_devices=end_device_list,
                language=language
            )
            
            if not job_id:
                raise HTTPException(status_code=500, detail="TTS 방송 예약 실패")
                
            return {
                "status": "success",
                "message": f"TTS 방송이 예약되었습니다 ({schedule_time})",
                "job_id": job_id,
                "text_length": len(text),
                "group_name": group_name,
                "device_count": len(devices),
                "end_devices": end_device_list,
                "language": language
            }
        else:
            # 일반 방송 시작 - TTS 음성 생성
            audio_path = broadcast_controller.generate_speech(text, language=language)
            if not audio_path:
                # 장치 비활성화 처리
                device_mapper.broadcast_to_group(group_name, False)  # 상태 False = 끄기
                raise HTTPException(status_code=500, detail="음성 생성에 실패했습니다")
            
            # 재생 완료 후 장치를 비활성화하기 위한 백그라운드 태스크
            def play_and_deactivate():
                try:
                    # 오디오 재생
                    broadcast_controller.play_audio(audio_path)
                    
                    # 방송 완료 후 장치 비활성화
                    logger.info(f"방송 완료, 장치 비활성화 처리: {end_device_list}")
                    
                    # 개별 장치로 비활성화 요청 (그룹 비활성화는 모든 연결 장치에 영향을 줄 수 있음)
                    broadcast_controller.control_multiple_devices(end_device_list, 0)  # 0 = 끄기
                    
                except Exception as e:
                    logger.exception(f"오디오 재생 및 장치 비활성화 중 오류: {str(e)}")
                
            # 백그라운드 태스크 등록
            background_tasks.add_task(play_and_deactivate)
            
            return {
                "status": "success", 
                "message": "TTS 방송이 시작되었습니다",
                "text_length": len(text),
                "group_name": group_name,
                "device_count": len(devices)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"그룹 TTS 방송 처리 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"그룹 TTS 방송 처리 중 오류: {str(e)}")

@router.post("/stop", response_model=Dict[str, Any])
async def stop_broadcast():
    """
    현재 실행 중인 방송 중지
    """
    try:
        success = broadcast_controller.stop_broadcast()
        
        if not success:
            raise HTTPException(status_code=500, detail="방송 중지 실패")
            
        return {
            "status": "success",
            "message": "방송이 중지되었습니다"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("방송 중지 중 오류")
        raise HTTPException(status_code=500, detail=f"방송 중지 중 오류: {str(e)}")

@router.post("/schedule/audio", response_model=Dict[str, Any])
async def schedule_broadcast_audio(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(..., description="방송할 오디오 파일"),
    target_devices: str = Form(..., description="방송할 장치 목록 (쉼표로 구분)"),
    end_devices: Optional[str] = Form(None, description="방송 종료 후 끌 장치 목록 (쉼표로 구분)"),
    duration: Optional[int] = Form(None, description="방송 지속 시간(초) (미지정시 파일 길이만큼 재생)"),
    schedule_time: str = Form(..., description="예약 시간 (YYYY-MM-DD HH:MM:SS)")
):
    """
    오디오 방송 예약 API (DEPRECATED: /api/schedule/ POST 사용 권장)
    """
    try:
        # 장치 목록 파싱
        target_device_list = [d.strip() for d in target_devices.split(",") if d.strip()]
        
        if not target_device_list:
            raise HTTPException(status_code=400, detail="방송 대상 장치가 지정되지 않았습니다")
            
        # 종료 시 끌 장치 목록 파싱 (지정된 경우)
        end_device_list = None
        if end_devices:
            end_device_list = [d.strip() for d in end_devices.split(",") if d.strip()]
        
        # 임시 파일 생성
        temp_file_path = Path(os.path.join(config.app_data_dir, "audio", f"{uuid.uuid4()}.wav"))
        os.makedirs(temp_file_path.parent, exist_ok=True)
        
        # 파일 저장
        with open(temp_file_path, "wb") as f:
            f.write(await audio_file.read())
        
        # 방송 예약
        result = broadcast_controller.schedule_broadcast_audio(
            schedule_time=schedule_time,
            audio_path=temp_file_path,
            target_devices=target_device_list,
            end_devices=end_device_list,
            duration=duration
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="오디오 방송 예약 실패")
            
        return {
            "status": "success",
            "message": "오디오 방송이 예약되었습니다",
            "job_id": result["job_id"],
            "schedule_time": result["schedule_time"],
            "filename": audio_file.filename,
            "target_devices": target_device_list,
            "end_devices": end_device_list or target_device_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("오디오 방송 예약 처리 중 오류")
        raise HTTPException(status_code=500, detail=f"오디오 방송 예약 처리 중 오류: {str(e)}")

@router.get("/schedule", response_model=List[Dict[str, Any]])
async def get_scheduled_broadcasts():
    """
    예약된 방송 목록 조회 (DEPRECATED: /api/schedule/ 사용 권장)
    """
    try:
        scheduled_broadcasts = broadcast_controller.get_scheduled_broadcasts()
        
        return scheduled_broadcasts
        
    except Exception as e:
        logger.exception("예약 방송 목록 조회 중 오류")
        raise HTTPException(status_code=500, detail=f"예약 방송 목록 조회 중 오류: {str(e)}")

@router.delete("/schedule/{job_id}", response_model=Dict[str, Any])
async def cancel_scheduled_broadcast(job_id: str = FastAPIPath(..., description="취소할 방송 작업 ID")):
    """
    예약된 방송 취소 (DEPRECATED: /api/schedule/{id} DELETE 사용 권장)
    """
    try:
        success = broadcast_controller.cancel_scheduled_broadcast(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"해당 ID({job_id})의 예약 방송을 찾을 수 없습니다")
            
        return {
            "status": "success",
            "message": "예약된 방송이 취소되었습니다",
            "job_id": job_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("예약 방송 취소 중 오류")
        raise HTTPException(status_code=500, detail=f"예약 방송 취소 중 오류: {str(e)}")

@router.post("/all-off", status_code=status.HTTP_200_OK)
async def turn_off_all_devices():
    """
    모든 장치 종료
    """
    try:
        # 모든 장치 목록 가져오기
        all_devices = list(broadcast_controller.device_mapper.device_map.values())
        print(f"[*] 모든 장치({len(all_devices)}개)를 종료합니다.")
        
        # 모든 장치 종료
        success = broadcast_controller.control_multiple_devices(all_devices, state=0)
        
        if success:
            return {"message": f"모든 장치({len(all_devices)}개)가 종료되었습니다."}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="장치 종료 중 오류가 발생했습니다."
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"오류 발생: {str(e)}"
        )

@router.post("/control/matrix", response_model=Dict[str, Any])
async def control_device_matrix(
    matrix_positions: str = Form(..., description="제어할 장치 행/열 위치 (예: '0,0;0,1;1,0' 형식)"),
    state: bool = Query(True, description="설정할 상태 (true: 켜기, false: 끄기)")
):
    """
    행/열 좌표로 지정된 장치들을 직접 제어하는 API
    
    matrix_positions 형식: '행,열;행,열' (예: '0,0;0,1;1,0')
    """
    try:
        # 행/열 위치 파싱
        positions = []
        for pos in matrix_positions.split(';'):
            if not pos.strip():
                continue
            try:
                row, col = map(int, pos.strip().split(','))
                positions.append((row, col))
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"잘못된 행/열 형식: {pos}. '행,열' 형식이어야 합니다."
                )
                
        if not positions:
            raise HTTPException(status_code=400, detail="제어 대상 장치가 지정되지 않았습니다")
            
        print(f"[*] 제어 대상 행/열 위치: {positions}")
        
        # 필요한 모듈들을 임포트
        from ...core.device_mapping import DeviceMapper
        from ...services.packet_builder import packet_builder
        from ...services.network import network_manager
        device_mapper = DeviceMapper()
        
        # 결과 저장용 변수
        results = {"positions": {}, "success_count": 0, "fail_count": 0}
        
        # 각 행/열 좌표별로 신호 전송
        for row, col in positions:
            try:
                # 행/열 좌표로 장치명 확인
                device_name = device_mapper.get_device_name(row, col)
                
                # 행/열로부터 바이트와 비트 위치 계산
                byte_pos, bit_pos = device_mapper.get_byte_bit_position(row, col)
                print(f"[*] 행/열 ({row},{col}) -> 바이트: {byte_pos}, 비트: {bit_pos}")
                
                # 패킷 생성 및 전송
                payload = packet_builder.create_byte_bit_payload(byte_pos, bit_pos, 1 if state else 0)
                
                if payload is None:
                    print(f"[!] 행/열 ({row},{col})에 대한 패킷 생성 실패")
                    results["positions"][f"{row},{col}"] = {
                        "success": False,
                        "reason": "패킷 생성 실패",
                        "device_name": device_name
                    }
                    results["fail_count"] += 1
                    continue
                
                # 패킷 전송
                send_success, _ = network_manager.send_payload(payload)
                
                # 결과 저장
                results["positions"][f"{row},{col}"] = {
                    "success": send_success,
                    "device_name": device_name
                }
                
                if send_success:
                    results["success_count"] += 1
                else:
                    results["fail_count"] += 1
                    
            except Exception as e:
                print(f"[!] 행/열 ({row},{col}) 처리 중 오류: {e}")
                results["positions"][f"{row},{col}"] = {
                    "success": False,
                    "reason": str(e)
                }
                results["fail_count"] += 1
        
        # 전체 결과 반환
        results["total"] = len(positions)
        results["status"] = "success" if results["fail_count"] == 0 else "partial"
        results["action"] = "켜기" if state else "끄기"
        
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("행/열 기반 장치 제어 중 오류")
        raise HTTPException(status_code=500, detail=f"행/열 기반 장치 제어 중 오류: {str(e)}")

@router.get("/device-mapping", response_model=Dict[str, Any])
async def get_device_mapping():
    """
    장치 매핑 정보를 반환합니다.
    
    프론트엔드에서 행/열 기반 UI 구성에 사용됩니다.
    """
    try:
        from ...core.device_mapping import device_mapper
        
        # 장치 매핑 정보를 JSON 형식으로 가져옴
        mapping_data = device_mapper.get_device_mapping_json()
        
        return {
            "status": "success",
            "data": mapping_data
        }
    except Exception as e:
        logger.exception("장치 매핑 정보 조회 중 오류")
        raise HTTPException(status_code=500, detail=f"장치 매핑 정보 조회 중 오류: {str(e)}")

@router.get("/groups", response_model=Dict[str, Any])
async def get_device_groups():
    """
    등록된 장치 그룹 정보 조회 API
    """
    try:
        from ...core.device_mapping import device_mapper
        
        # 모든 그룹 정보 가져오기
        groups = device_mapper.get_all_groups()
        
        # 응답 데이터 구성
        response_data = {}
        for group_name, devices in groups.items():
            response_data[group_name] = {
                "devices": devices,
                "count": len(devices)
            }
        
        return {
            "status": "success",
            "data": response_data
        }
    except Exception as e:
        logger.exception("장치 그룹 정보 조회 중 오류")
        raise HTTPException(status_code=500, detail=f"장치 그룹 정보 조회 중 오류: {str(e)}")

@router.post("/groups/{group_name}/control", response_model=Dict[str, Any])
async def control_device_group(
    group_name: str = FastAPIPath(..., description="제어할 그룹명"),
    state: bool = Query(True, description="설정할 상태 (true: 켜기, false: 끄기)")
):
    """
    장치 그룹 일괄 제어
    
    그룹명에 해당하는 모든 장치를 켜거나 끕니다.
    """
    try:
        from ...core.device_mapping import device_mapper
        
        # 그룹 장치 목록 가져오기
        devices = device_mapper.get_group_devices(group_name)
        
        if devices is None:
            raise HTTPException(status_code=404, detail=f"장치 그룹을 찾을 수 없습니다: {group_name}")
            
        if not devices:
            return {
                "status": "warning",
                "message": f"그룹에 등록된 장치가 없습니다: {group_name}",
                "device_count": 0
            }
            
        # 그룹 제어 실행
        results = device_mapper.broadcast_to_group(group_name, state)
        
        return {
            "status": "success",
            "message": f"그룹 '{group_name}' 장치 {len(devices)}개가 {'켜졌습니다' if state else '꺼졌습니다'}",
            "device_count": len(devices),
            "success_count": results["success_count"],
            "fail_count": results["fail_count"]
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"그룹 제어 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"그룹 제어 중 오류: {str(e)}")

@router.get("/groups/{group_name}", response_model=Dict[str, Any])
async def get_group_devices(
    group_name: str = FastAPIPath(..., description="조회할 그룹명")
):
    """
    특정 그룹에 포함된 장치 목록 조회 API
    """
    try:
        from ...core.device_mapping import device_mapper
        
        # 그룹 장치 목록 가져오기
        devices = device_mapper.get_group_devices(group_name)
        
        if devices is None:
            raise HTTPException(status_code=404, detail=f"장치 그룹을 찾을 수 없습니다: {group_name}")
        
        # 각 장치의 상세 정보 수집
        device_details = []
        for device_name in devices:
            coords = device_mapper.get_device_coords(device_name)
            if coords:
                row, col = coords
                device_id = device_mapper._get_device_id(device_name)
                device_type = device_mapper._get_device_type(device_name)
                
                device_details.append({
                    "device_name": device_name,
                    "device_id": device_id,
                    "position": [row, col],
                    "type": device_type
                })
        
        return {
            "status": "success",
            "group_name": group_name,
            "count": len(devices),
            "devices": device_details
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"그룹 장치 목록 조회 중 오류: {group_name}")
        raise HTTPException(status_code=500, detail=f"그룹 장치 목록 조회 중 오류: {str(e)}") 
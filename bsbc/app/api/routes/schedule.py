#!/usr/bin/env python3
"""
스케줄 관련 API 라우터
방송 스케줄 관련 API 엔드포인트를 정의합니다.
"""
from fastapi import APIRouter, HTTPException, Path, Query, Body
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from ...models.schedule import ScheduleItem, ScheduleCreate, ScheduleResponse, ScheduleUpdate
from ...services.broadcast_controller import broadcast_controller

# 라우터 생성
router = APIRouter(
    prefix="/api/schedule",
    tags=["schedule"],
    responses={404: {"description": "Not found"}},
)

# 로거 설정
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[ScheduleResponse])
async def get_all_schedules(
    active_only: bool = Query(False, description="활성화된 스케줄만 조회")
):
    """
    모든 스케줄 조회
    """
    # 스케줄 목록 조회
    schedules = broadcast_controller.view_schedules()
    
    # 응답 데이터 변환
    response_data = []
    for i, schedule in enumerate(schedules):
        item = ScheduleResponse(
            id=i,
            time=schedule.get('time', ''),
            days=schedule.get('days', ''),
            command_type=int(schedule.get('command_type', 1)),
            channel=int(schedule.get('channel', 0)),
            state=int(schedule.get('state', 0)),
            description="",  # 기존 스케줄에는 설명 필드가 없음
            active=True  # 기존 스케줄은 모두 활성화 상태
        )
        response_data.append(item)
    
    # 활성화된 스케줄만 필터링
    if active_only:
        response_data = [s for s in response_data if s.active]
    
    return response_data

@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int = Path(..., description="스케줄 ID", ge=0)
):
    """
    특정 스케줄 조회
    """
    # 스케줄 목록 조회
    schedules = broadcast_controller.view_schedules()
    
    # 해당 ID의 스케줄이 있는지 확인
    if schedule_id >= len(schedules):
        raise HTTPException(status_code=404, detail=f"스케줄 ID {schedule_id}를 찾을 수 없습니다")
    
    # 스케줄 데이터 반환
    schedule = schedules[schedule_id]
    return ScheduleResponse(
        id=schedule_id,
        time=schedule.get('time', ''),
        days=schedule.get('days', ''),
        command_type=int(schedule.get('command_type', 1)),
        channel=int(schedule.get('channel', 0)),
        state=int(schedule.get('state', 0)),
        description="",  # 기존 스케줄에는 설명 필드가 없음
        active=True  # 기존 스케줄은 모두 활성화 상태
    )

@router.post("/", response_model=ScheduleResponse)
async def create_schedule(
    schedule: ScheduleCreate = Body(..., description="생성할 스케줄 정보")
):
    """
    새 스케줄 생성
    """
    logger.info(f"새 스케줄 생성 요청: {schedule.time}, {schedule.days}, {schedule.command_type}, {schedule.channel}, {schedule.state}")
    
    # 스케줄 생성
    success = broadcast_controller.schedule_broadcast(
        schedule.time,
        schedule.days,
        schedule.command_type,
        schedule.channel,
        schedule.state
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="스케줄 생성 실패")
    
    # 생성된 스케줄 ID 조회
    schedules = broadcast_controller.view_schedules()
    new_id = len(schedules) - 1
    
    # 스케줄러 시작
    broadcast_controller.start_scheduler()
    
    # 생성된 스케줄 정보 반환
    return ScheduleResponse(
        id=new_id,
        time=schedule.time,
        days=schedule.days,
        command_type=schedule.command_type,
        channel=schedule.channel,
        state=schedule.state,
        description=schedule.description,
        active=True
    )

@router.delete("/{schedule_id}", response_model=Dict[str, Any])
async def delete_schedule(
    schedule_id: int = Path(..., description="삭제할 스케줄 ID", ge=0)
):
    """
    스케줄 삭제
    """
    logger.info(f"스케줄 삭제 요청: ID {schedule_id}")
    
    # 스케줄 목록 조회
    schedules = broadcast_controller.view_schedules()
    
    # 해당 ID의 스케줄이 있는지 확인
    if schedule_id >= len(schedules):
        raise HTTPException(status_code=404, detail=f"스케줄 ID {schedule_id}를 찾을 수 없습니다")
    
    # 스케줄 삭제
    success = broadcast_controller.delete_schedule(schedule_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="스케줄 삭제 실패")
    
    return {
        "success": True,
        "id": schedule_id,
        "message": f"스케줄 ID {schedule_id}가 삭제되었습니다"
    }

@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int = Path(..., description="수정할 스케줄 ID", ge=0),
    schedule_update: ScheduleUpdate = Body(..., description="수정할 스케줄 정보")
):
    """
    스케줄 수정
    """
    # 현재는 스케줄 수정이 직접 지원되지 않아 삭제 후 다시 생성하는 방식으로 구현
    logger.info(f"스케줄 수정 요청: ID {schedule_id}")
    
    # 스케줄 목록 조회
    schedules = broadcast_controller.view_schedules()
    
    # 해당 ID의 스케줄이 있는지 확인
    if schedule_id >= len(schedules):
        raise HTTPException(status_code=404, detail=f"스케줄 ID {schedule_id}를 찾을 수 없습니다")
    
    # 기존 스케줄 정보 가져오기
    existing_schedule = schedules[schedule_id]
    
    # 기존 값과 업데이트 값 병합
    time = schedule_update.time or existing_schedule.get('time', '')
    days = schedule_update.days or existing_schedule.get('days', '')
    command_type = schedule_update.command_type or int(existing_schedule.get('command_type', 1))
    channel = schedule_update.channel or int(existing_schedule.get('channel', 0))
    state = schedule_update.state if schedule_update.state is not None else int(existing_schedule.get('state', 0))
    description = schedule_update.description or ""
    
    # 스케줄 삭제
    delete_success = broadcast_controller.delete_schedule(schedule_id)
    if not delete_success:
        raise HTTPException(status_code=500, detail="스케줄 수정 실패 (삭제 단계)")
    
    # 새 스케줄 생성
    create_success = broadcast_controller.schedule_broadcast(
        time,
        days,
        command_type,
        channel,
        state
    )
    
    if not create_success:
        raise HTTPException(status_code=500, detail="스케줄 수정 실패 (생성 단계)")
    
    # 수정된 스케줄 정보 반환
    return ScheduleResponse(
        id=schedule_id,
        time=time,
        days=days,
        command_type=command_type,
        channel=channel,
        state=state,
        description=description,
        active=True
    )

@router.post("/start", response_model=Dict[str, Any])
async def start_scheduler():
    """
    스케줄러 시작
    """
    logger.info("스케줄러 시작 요청")
    
    broadcast_controller.start_scheduler()
    
    return {
        "success": True,
        "message": "스케줄러가 시작되었습니다"
    }

@router.post("/stop", response_model=Dict[str, Any])
async def stop_scheduler():
    """
    스케줄러 중지
    """
    logger.info("스케줄러 중지 요청")
    
    broadcast_controller.stop_scheduler()
    
    return {
        "success": True,
        "message": "스케줄러가 중지되었습니다"
    } 
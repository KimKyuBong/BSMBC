#!/usr/bin/env python3
"""
장치 관련 데이터 모델
Pydantic을 사용한 장치 관련 데이터 모델 정의
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Set, Tuple

class DeviceCoords(BaseModel):
    """장치 좌표 모델"""
    row: int = Field(..., description="장치의 행 좌표")
    col: int = Field(..., description="장치의 열 좌표")

class DeviceInfo(BaseModel):
    """장치 정보 모델"""
    name: str = Field(..., description="장치 이름 (예: '1-1', '선생영역')")
    coords: DeviceCoords = Field(..., description="장치 좌표")
    description: Optional[str] = Field(None, description="장치 설명")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "1-1",
                "coords": {
                    "row": 0,
                    "col": 0
                },
                "description": "1학년 1반 교실"
            }
        }

class DeviceState(BaseModel):
    """장치 상태 모델"""
    device_name: str = Field(..., description="장치 이름")
    state: bool = Field(..., description="장치 상태 (True: 켜짐, False: 꺼짐)")
    
    class Config:
        schema_extra = {
            "example": {
                "device_name": "1-1",
                "state": True
            }
        }

class DeviceGroup(BaseModel):
    """장치 그룹 모델"""
    group_name: str = Field(..., description="그룹 이름")
    devices: List[str] = Field(..., description="그룹에 속한 장치 이름 목록")
    
    class Config:
        schema_extra = {
            "example": {
                "group_name": "1학년",
                "devices": ["1-1", "1-2", "1-3", "1-4"]
            }
        }

class DeviceStateResponse(BaseModel):
    """장치 상태 응답 모델"""
    device_name: str = Field(..., description="장치 이름")
    state: bool = Field(..., description="장치 상태")
    response_time: str = Field(..., description="응답 시간")
    success: bool = Field(..., description="성공 여부")
    
    class Config:
        schema_extra = {
            "example": {
                "device_name": "1-1",
                "state": True,
                "response_time": "2023-03-08T12:34:56",
                "success": True
            }
        }

class SystemState(BaseModel):
    """시스템 전체 상태 모델"""
    active_rooms: Set[int] = Field(default_factory=set, description="활성화된 방 ID 목록")
    device_states: Dict[str, bool] = Field(default_factory=dict, description="장치별 상태")
    last_updated: str = Field(..., description="마지막 업데이트 시간")
    
    class Config:
        schema_extra = {
            "example": {
                "active_rooms": [301, 302],
                "device_states": {
                    "1-1": True,
                    "1-2": False,
                    "3-1": True
                },
                "last_updated": "2023-03-08T12:34:56"
            }
        } 
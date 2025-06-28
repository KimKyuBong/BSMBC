#!/usr/bin/env python3
"""
장치 관련 데이터 모델
Pydantic을 사용한 장치 관련 데이터 모델 정의
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Set, Tuple
from enum import Enum

class DeviceStatus(Enum):
    """장치 상태 열거형"""
    OFF = 0
    ON = 1

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
        json_schema_extra = {
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
        json_schema_extra = {
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
        json_schema_extra = {
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
        json_schema_extra = {
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
        json_schema_extra = {
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

class DeviceMatrixMapping(BaseModel):
    """4행 16열 장치 매트릭스 매핑 모델"""
    matrix: List[List[str]] = Field(..., description="4행 16열 장치 이름 매트릭스")
    
    class Config:
        json_schema_extra = {
            "example": {
                "matrix": [
                    ["1-1", "1-2", "1-3", "1-4", "장치5", "장치6", "장치7", "장치8", "2-1", "2-2", "2-3", "2-4", "장치13", "장치14", "장치15", "장치16"],
                    ["3-1", "3-2", "3-3", "3-4", "장치21", "장치22", "장치23", "장치24", "장치25", "장치26", "장치27", "장치28", "장치29", "장치30", "장치31", "장치32"],
                    ["교행연회", "교사연구", "협동조합", "보건학부", "컴터12", "과학준비", "창의준비", "남여휴게", "일반교무", "급식실", "위클회의", "플그12", "전문교무", "진로연구", "모둠12", "창의공작"],
                    ["본관1층층", "융합1층", "본관2층", "융합2층", "융합3층", "강당", "방송실", "별관11", "별관12", "별관13", "별관21", "별관22", "장치61", "장치62", "운동장", "옥외"]
                ]
            }
        }

class DeviceMatrixUpdate(BaseModel):
    """장치 매트릭스 업데이트 모델"""
    row: int = Field(..., ge=0, le=3, description="행 번호 (0-3)")
    col: int = Field(..., ge=0, le=15, description="열 번호 (0-15)")
    device_name: str = Field(..., description="장치 이름")
    
    class Config:
        json_schema_extra = {
            "example": {
                "row": 0,
                "col": 0,
                "device_name": "1-1"
            }
        }

class DeviceMatrixResponse(BaseModel):
    """장치 매트릭스 응답 모델"""
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    matrix: Optional[List[List[str]]] = Field(None, description="현재 장치 매트릭스")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "장치 매트릭스가 성공적으로 업데이트되었습니다.",
                "matrix": [
                    ["1-1", "1-2", "1-3", "1-4", "1-5", "1-6", "1-7", "1-8", "1-9", "1-10", "1-11", "1-12", "1-13", "1-14", "1-15", "1-16"],
                    ["2-1", "2-2", "2-3", "2-4", "2-5", "2-6", "2-7", "2-8", "2-9", "2-10", "2-11", "2-12", "2-13", "2-14", "2-15", "2-16"],
                    ["3-1", "3-2", "3-3", "3-4", "3-5", "3-6", "3-7", "3-8", "3-9", "3-10", "3-11", "3-12", "3-13", "3-14", "3-15", "3-16"],
                    ["4-1", "4-2", "4-3", "4-4", "4-5", "4-6", "4-7", "4-8", "4-9", "4-10", "4-11", "4-12", "4-13", "4-14", "4-15", "4-16"]
                ]
            }
        } 
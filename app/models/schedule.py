#!/usr/bin/env python3
"""
스케줄 관련 데이터 모델
Pydantic을 사용한 스케줄 관련 데이터 모델 정의
"""
#
# TODO: 스케줄 모델 개선 계획
# ----------------------------------------------------------------------
# 1. 방송 스케줄 모델 확장:
#   - 기존 모델은 단순 타이머 스케줄용으로 설계됨
#   - 방송 스케줄을 위한 새로운 필드 필요:
#     - schedule_type: "timer" | "broadcast" (어떤 종류의 스케줄인지)
#     - content_type: "text" | "audio" (방송 스케줄일 때 컨텐츠 유형)
#     - content: 방송 텍스트 또는 오디오 파일 경로
#     - target_devices: 방송할 장치 목록 
#     - end_devices: 방송 종료 후 끌 장치 목록
#     - duration: 방송 지속 시간 (오디오 파일인 경우)
#     - language: 텍스트 언어 (TTS 방송인 경우)
#
# 2. 새로운 모델 추가:
#   - BroadcastScheduleCreate: 방송 스케줄 생성용 모델
#   - BroadcastScheduleResponse: 방송 스케줄 응답용 모델
# ----------------------------------------------------------------------

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union
import re

class ScheduleItem(BaseModel):
    """스케줄 항목 모델"""
    time: str = Field(..., description="실행 시간 (HH:MM 형식)")
    days: str = Field(..., description="실행 요일 (쉼표로 구분된 요일 문자열)")
    command_type: int = Field(1, description="명령 타입 (1: 장비 제어, 2: 볼륨 제어, 3: 채널 변경)")
    channel: int = Field(..., description="채널 번호")
    state: int = Field(..., description="상태값")
    
    @validator('time')
    def validate_time(cls, v):
        """시간 형식 검증"""
        if not re.match(r"^([0-1][0-9]|2[0-3]):([0-5][0-9])$", v):
            raise ValueError("시간 형식이 올바르지 않습니다 (HH:MM)")
        return v
    
    @validator('days')
    def validate_days(cls, v):
        """요일 형식 검증"""
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Everyday"]
        days = v.split(',')
        for day in days:
            day = day.strip()
            if day not in valid_days:
                raise ValueError(f"유효하지 않은 요일: {day}")
        return v
    
    @validator('command_type')
    def validate_command_type(cls, v):
        """명령 타입 검증"""
        if v not in [1, 2, 3]:
            raise ValueError("유효하지 않은 명령 타입 (1, 2, 3만 허용)")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "time": "08:30",
                "days": "Monday,Wednesday,Friday",
                "command_type": 1,
                "channel": 0,
                "state": 1
            }
        }

class ScheduleCreate(BaseModel):
    """스케줄 생성 모델"""
    time: str = Field(..., description="실행 시간 (HH:MM 형식)")
    days: Union[str, List[str]] = Field(..., description="실행 요일 (문자열 또는 목록)")
    command_type: int = Field(1, description="명령 타입 (1: 장비 제어, 2: 볼륨 제어, 3: 채널 변경)")
    channel: int = Field(..., description="채널 번호")
    state: int = Field(..., description="상태값")
    description: Optional[str] = Field(None, description="스케줄 설명")
    
    @validator('days', pre=True)
    def validate_days(cls, v):
        """요일 형식 검증 및 변환"""
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Everyday"]
        
        if isinstance(v, list):
            for day in v:
                if day not in valid_days:
                    raise ValueError(f"유효하지 않은 요일: {day}")
            return ','.join(v)
        
        elif isinstance(v, str):
            days = v.split(',')
            for day in days:
                day = day.strip()
                if day not in valid_days:
                    raise ValueError(f"유효하지 않은 요일: {day}")
            return v
        
        else:
            raise ValueError("요일은 문자열 또는 문자열 목록이어야 합니다")
    
    class Config:
        json_schema_extra = {
            "example": {
                "time": "08:30",
                "days": ["Monday", "Wednesday", "Friday"],
                "command_type": 1,
                "channel": 0,
                "state": 1,
                "description": "아침 조회 방송"
            }
        }

class ScheduleResponse(BaseModel):
    """스케줄 응답 모델"""
    id: int = Field(..., description="스케줄 ID")
    time: str = Field(..., description="실행 시간")
    days: str = Field(..., description="실행 요일")
    command_type: int = Field(..., description="명령 타입")
    channel: int = Field(..., description="채널 번호")
    state: int = Field(..., description="상태값")
    description: Optional[str] = Field(None, description="스케줄 설명")
    active: bool = Field(True, description="활성화 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "time": "08:30",
                "days": "Monday,Wednesday,Friday",
                "command_type": 1,
                "channel": 0,
                "state": 1,
                "description": "아침 조회 방송",
                "active": True
            }
        }

class ScheduleUpdate(BaseModel):
    """스케줄 업데이트 모델"""
    time: Optional[str] = Field(None, description="실행 시간 (HH:MM 형식)")
    days: Optional[Union[str, List[str]]] = Field(None, description="실행 요일 (문자열 또는 목록)")
    command_type: Optional[int] = Field(None, description="명령 타입")
    channel: Optional[int] = Field(None, description="채널 번호")
    state: Optional[int] = Field(None, description="상태값")
    description: Optional[str] = Field(None, description="스케줄 설명")
    active: Optional[bool] = Field(None, description="활성화 여부")
    
    @validator('days', pre=True)
    def validate_days(cls, v):
        """요일 형식 검증 및 변환"""
        if v is None:
            return v
            
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Everyday"]
        
        if isinstance(v, list):
            for day in v:
                if day not in valid_days:
                    raise ValueError(f"유효하지 않은 요일: {day}")
            return ','.join(v)
        
        elif isinstance(v, str):
            days = v.split(',')
            for day in days:
                day = day.strip()
                if day not in valid_days:
                    raise ValueError(f"유효하지 않은 요일: {day}")
            return v
        
        else:
            raise ValueError("요일은 문자열 또는 문자열 목록이어야 합니다")
    
    class Config:
        json_schema_extra = {
            "example": {
                "time": "09:00",
                "days": ["Monday", "Tuesday"],
                "state": 0,
                "active": False
            }
        } 
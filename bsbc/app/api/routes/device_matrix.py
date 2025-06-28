#!/usr/bin/env python3
"""
장치 매트릭스 관리 API 라우터
4행 16열 장치 매트릭스 관리를 위한 API 엔드포인트를 정의합니다.
"""

from fastapi import APIRouter, HTTPException, Body, Query, Path
from fastapi.responses import JSONResponse
from typing import List, Dict, Any
import logging

from ...models.device import (
    DeviceMatrixMapping, 
    DeviceMatrixUpdate, 
    DeviceMatrixResponse
)
from ...services.broadcast_controller import broadcast_controller

# 라우터 생성
router = APIRouter(
    prefix="/device-matrix",
    tags=["device-matrix"],
    responses={404: {"description": "Not found"}},
)

# 로거 설정
logger = logging.getLogger(__name__)

@router.get("/", response_model=Dict[str, Any])
async def get_device_matrix():
    """
    현재 장치 매트릭스 조회
    4행 16열 장치 매트릭스를 반환합니다.
    각 위치에 장치명과 장치번호(room_id)를 포함합니다.
    """
    try:
        matrix = broadcast_controller.device_mapper.get_device_matrix()
        
        # 장치번호와 함께 매트릭스 구성
        enhanced_matrix = []
        for row_idx, row in enumerate(matrix):
            row_data = []
            for col_idx, device_name in enumerate(row):
                # 장치번호 계산 (1부터 시작하는 행/열 기준)
                room_id = (row_idx + 1) * 100 + (col_idx + 1)
                row_data.append({
                    "device_name": device_name,
                    "room_id": room_id,
                    "position": {
                        "row": row_idx + 1,  # 1부터 시작
                        "col": col_idx + 1   # 1부터 시작
                    },
                    "matrix_position": {
                        "row": row_idx,      # 0부터 시작 (매트릭스 인덱스)
                        "col": col_idx       # 0부터 시작 (매트릭스 인덱스)
                    }
                })
            enhanced_matrix.append(row_data)
        
        return {
            "success": True,
            "message": "장치 매트릭스를 성공적으로 조회했습니다.",
            "matrix": enhanced_matrix,
            "total_rows": 4,
            "total_cols": 16,
            "total_devices": 64
        }
    except Exception as e:
        logger.error(f"장치 매트릭스 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"장치 매트릭스 조회 실패: {str(e)}")

@router.post("/", response_model=DeviceMatrixResponse)
async def update_device_matrix(
    matrix_data: DeviceMatrixMapping = Body(..., description="업데이트할 장치 매트릭스")
):
    """
    장치 매트릭스 전체 업데이트
    4행 16열 장치 매트릭스를 전체 업데이트합니다.
    """
    try:
        success, message = broadcast_controller.device_mapper.update_device_matrix(matrix_data.matrix)
        
        if success:
            return DeviceMatrixResponse(
                success=True,
                message=message,
                matrix=broadcast_controller.device_mapper.get_device_matrix()
            )
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"장치 매트릭스 업데이트 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"장치 매트릭스 업데이트 실패: {str(e)}")

@router.put("/position", response_model=DeviceMatrixResponse)
async def update_device_at_position(
    update_data: DeviceMatrixUpdate = Body(..., description="업데이트할 장치 정보")
):
    """
    특정 위치의 장치 이름 업데이트
    지정된 행/열 위치의 장치 이름을 업데이트합니다.
    """
    try:
        success, message = broadcast_controller.device_mapper.update_device_at_position(
            update_data.row, 
            update_data.col, 
            update_data.device_name
        )
        
        if success:
            return DeviceMatrixResponse(
                success=True,
                message=message,
                matrix=broadcast_controller.device_mapper.get_device_matrix()
            )
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"장치 위치 업데이트 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"장치 위치 업데이트 실패: {str(e)}")

@router.get("/position/{row}/{col}", response_model=Dict[str, Any])
async def get_device_at_position(
    row: int = Path(..., ge=0, le=3, description="행 번호 (0-3)"),
    col: int = Path(..., ge=0, le=15, description="열 번호 (0-15)")
):
    """
    특정 위치의 장치 이름 조회
    지정된 행/열 위치의 장치 이름을 반환합니다.
    """
    try:
        device_name = broadcast_controller.device_mapper.get_device_at_position(row, col)
        
        if device_name is not None:
            return {
                "success": True,
                "row": row,
                "col": col,
                "device_name": device_name,
                "message": f"위치 ({row}, {col})의 장치: {device_name}"
            }
        else:
            raise HTTPException(status_code=404, detail=f"위치 ({row}, {col})의 장치를 찾을 수 없습니다.")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"장치 위치 조회 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"장치 위치 조회 실패: {str(e)}")

@router.post("/reset", response_model=DeviceMatrixResponse)
async def reset_device_matrix():
    """
    장치 매트릭스 초기화
    장치 매트릭스를 기본값(장치1~장치64)으로 초기화합니다.
    """
    try:
        success, message = broadcast_controller.device_mapper.reset_matrix_to_default()
        
        if success:
            return DeviceMatrixResponse(
                success=True,
                message=message,
                matrix=broadcast_controller.device_mapper.get_device_matrix()
            )
        else:
            raise HTTPException(status_code=500, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"장치 매트릭스 초기화 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"장치 매트릭스 초기화 실패: {str(e)}")

@router.get("/preview", response_model=Dict[str, Any])
async def preview_device_matrix():
    """
    장치 매트릭스 미리보기
    현재 장치 매트릭스를 시각적으로 보기 좋게 반환합니다.
    """
    try:
        matrix = broadcast_controller.device_mapper.get_device_matrix()
        
        # 시각적 표현을 위한 포맷팅
        preview = []
        for row_idx, row in enumerate(matrix):
            row_data = {
                "row": row_idx,
                "devices": []
            }
            for col_idx, device_name in enumerate(row):
                row_data["devices"].append({
                    "col": col_idx,
                    "device_name": device_name,
                    "position": f"({row_idx}, {col_idx})"
                })
            preview.append(row_data)
        
        return {
            "success": True,
            "message": "장치 매트릭스 미리보기",
            "total_rows": 4,
            "total_cols": 16,
            "total_devices": 64,
            "matrix_preview": preview
        }
        
    except Exception as e:
        logger.error(f"장치 매트릭스 미리보기 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"장치 매트릭스 미리보기 실패: {str(e)}")

@router.post("/bulk-update", response_model=DeviceMatrixResponse)
async def bulk_update_devices(
    updates: List[DeviceMatrixUpdate] = Body(..., description="일괄 업데이트할 장치 목록")
):
    """
    장치 일괄 업데이트
    여러 장치를 한 번에 업데이트합니다.
    """
    try:
        success_count = 0
        error_messages = []
        
        for update in updates:
            success, message = broadcast_controller.device_mapper.update_device_at_position(
                update.row, 
                update.col, 
                update.device_name
            )
            
            if success:
                success_count += 1
            else:
                error_messages.append(f"위치 ({update.row}, {update.col}): {message}")
        
        # 매트릭스 저장
        save_success = broadcast_controller.device_mapper._save_matrix_config()
        
        if save_success:
            return DeviceMatrixResponse(
                success=True,
                message=f"일괄 업데이트 완료: {success_count}개 성공, {len(error_messages)}개 실패",
                matrix=broadcast_controller.device_mapper.get_device_matrix()
            )
        else:
            raise HTTPException(status_code=500, detail="매트릭스 설정 저장에 실패했습니다.")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"장치 일괄 업데이트 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"장치 일괄 업데이트 실패: {str(e)}")

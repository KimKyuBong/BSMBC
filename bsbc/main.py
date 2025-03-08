#!/usr/bin/env python3
"""
학교 방송 제어 시스템 FastAPI 애플리케이션
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import config
from app.api.routes import broadcast, schedule

# FastAPI 앱 생성
app = FastAPI(
    title="학교 방송 제어 시스템",
    description="학교 방송 장비를 원격으로 제어하는 API 시스템",
    version=config.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 및 템플릿 설정
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    templates = Jinja2Templates(directory="app/templates")
except:
    print("경고: 정적 파일 또는 템플릿 디렉토리가 없습니다.")

# 라우트 포함
app.include_router(broadcast.router, prefix="/api/broadcast", tags=["방송 제어"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["방송 일정"])

@app.get("/", tags=["기본"])
async def root():
    """
    루트 경로 접속 시 앱 정보 반환
    """
    return {
        "app": config.get_app_info(),
        "message": "학교 방송 제어 시스템 API에 오신 것을 환영합니다!",
        "docs": "/docs"
    }

@app.get("/health", tags=["기본"])
async def health_check():
    """
    서버 상태 확인
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    # 개발 서버 실행
    print("방송 제어 시스템 서버를 시작합니다...")
    try:
        import os
        # 정적 파일 및 템플릿 디렉토리 생성 (경고 메시지 방지)
        os.makedirs('app/static', exist_ok=True)
        os.makedirs('app/templates', exist_ok=True)
        
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except Exception as e:
        print(f"서버 시작 중 오류 발생: {e}") 
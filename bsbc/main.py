#!/usr/bin/env python3
"""
학교 방송 제어 시스템 FastAPI 애플리케이션
"""
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time

from app.core.config import config
from app.api.routes import broadcast, schedule
from app.core.security import verify_ip_and_api_key, get_security_manager

# 보안 관리자 초기화 (싱글톤)
security_manager = get_security_manager()

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

# 보안 미들웨어 클래스 정의
class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 공개 경로 목록 (인증 없이 접근 가능)
        public_paths = ["/docs", "/redoc", "/openapi.json", "/", "/health", "/broadcast", "/admin"]
        
        # 현재 경로가 공개 경로인지 확인
        path = request.url.path
        if path in public_paths or any(path.startswith(p + "/") for p in public_paths):
            # 공개 경로는 인증 없이 통과
            return await call_next(request)
        
        # IP 주소 및 API 키 검증
        await verify_ip_and_api_key(request)
        
        # 검증 통과 시 다음 미들웨어로 진행
        return await call_next(request)

# 보안 미들웨어 등록
app.add_middleware(SecurityMiddleware)

# 정적 파일 및 템플릿 설정
try:
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    templates = Jinja2Templates(directory="app/templates")
except:
    print("경고: 정적 파일 또는 템플릿 디렉토리가 없습니다.")

"""
TODO: API 구조 정리 계획
----------------------------------------------------------------------
1. 기존 구조:
   - /api/broadcast/* - 방송 제어 + 일부 스케줄 기능 (중복)
   - /api/schedule/* - 스케줄 관리

2. 개선된 구조로 변경 예정:
   - /api/broadcast/* - 실시간 방송 제어만 담당
   - /api/schedule/* - 모든 스케줄 관련 기능 담당
   - /api/device/* - 장치 관리 및 상태 (향후)
   - /api/system/* - 시스템 설정 및 상태 (향후)

3. API 버전 관리 도입 검토:
   - /api/v1/broadcast/*, /api/v1/schedule/* 등
----------------------------------------------------------------------
"""

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

@app.get("/broadcast", response_class=HTMLResponse, tags=["웹 UI"])
async def broadcast_page(request: Request):
    """
    방송 관리 페이지
    """
    return templates.TemplateResponse("broadcast.html", {"request": request})

# TOTP 코드 발급 엔드포인트 추가 (개발 및 관리용)
@app.get("/admin/generate-totp", tags=["관리"])
async def generate_totp():
    """
    현재 시간에 대한 TOTP 코드 생성 (개발 및 관리용)
    """
    totp = security_manager.generate_totp()
    return {
        "totp": totp,
        "valid_for_seconds": 30 - (time.time() % 30),
        "secret": security_manager.get_totp_secret(),
        "totp_uri": security_manager.get_totp_uri(),
        "totp_enabled": security_manager.is_totp_enabled(),
        "ip_check_enabled": security_manager.is_ip_check_enabled()
    }

@app.get("/admin/security/status", tags=["관리"])
async def security_status():
    """
    보안 설정 상태 확인
    """
    return {
        "totp_enabled": security_manager.is_totp_enabled(),
        "ip_check_enabled": security_manager.is_ip_check_enabled(),
        "allowed_networks": security_manager.config["allowed_ip_networks"]
    }

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
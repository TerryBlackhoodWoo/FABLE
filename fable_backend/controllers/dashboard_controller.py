"""
대시보드 라우트 — 사람이 직접 로그인해서 자기 계정의 대화 로그·사용량을 조회하는 용도.
/ask 등 콘텐츠 API의 API 키 인증과는 완전히 별개 트랙 (services/auth_service.py 상단 설명 참고).
"""

from fastapi import APIRouter, Depends

from schemas import LoginRequest, LoginResponse, LogEntry, UsageResponse
from services import auth_service
from dao import log_dao, usage_dao

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    token = await auth_service.login(request.username, request.password)
    return LoginResponse(access_token=token)


@router.get("/logs", response_model=list[LogEntry])
async def get_logs(account: dict = Depends(auth_service.get_current_account)):
    rows = await log_dao.list_by_account(account["id"])
    return [
        LogEntry(
            id=r["id"],
            question=r["question"],
            answer=r["answer"],
            speaker=r["speaker"],
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.get("/usage", response_model=UsageResponse)
async def get_usage(account: dict = Depends(auth_service.get_current_account)):
    today_count = await usage_dao.get_today_count(account["id"])
    return UsageResponse(today_count=today_count, daily_limit=account["daily_limit"])

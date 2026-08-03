"""
API 키 검증 + 사용량 추적을 담당하는 서비스.
FastAPI Depends()로 라우트 핸들러 진입 전에 실행되어, 비용이 드는 Gemini/Mongo 호출 전에
인증 실패/한도 초과를 걸러낸다.
"""

import hashlib

from fastapi import Header, HTTPException

from dao import account_dao, usage_dao


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def verify_and_track(x_api_key: str = Header(..., alias="X-API-Key")) -> dict:
    """
    요청 헤더의 API 키를 검증하고, 사용량을 원자적으로 1 증가시킨 뒤,
    deployment 계정이 일일 한도를 넘었으면 429로 차단한다.
    developer 계정은 사용량은 기록하되(분석용) 한도 체크는 건너뛴다.
    """
    key_hash = hash_api_key(x_api_key)
    account = await account_dao.find_by_key_hash(key_hash)

    if not account or not account["is_active"]:
        raise HTTPException(status_code=401, detail="유효하지 않은 API 키입니다.")

    # 원자적 증가 (ON CONFLICT DO UPDATE) — 동시 요청이 몰려도 카운트가 안전하게 늘어남
    new_count = await usage_dao.increment_today_count(account["id"])

    if account["account_type"] == "deployment" and account["daily_limit"] is not None:
        if new_count > account["daily_limit"]:
            raise HTTPException(
                status_code=429, detail="오늘의 사용량 한도를 초과했습니다."
            )

    return account

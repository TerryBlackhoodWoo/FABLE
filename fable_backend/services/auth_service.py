"""
인증 서비스 — 두 가지 완전히 다른 인증 트랙을 담당한다.

1) API 키 인증 (서버-서버, /ask 등 콘텐츠 API용) — verify_and_track()
2) 대시보드 로그인 (사람이 직접 로그인, /logs 등 조회용 API) — login() + get_current_account()

두 트랙은 서로 독립적: API 키는 콘텐츠를 소비하는 배포처/개발자용,
로그인은 그 계정의 사용량/로그를 사람이 눈으로 확인하는 용도.
"""

import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Header, HTTPException

from config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    LOGIN_MAX_ATTEMPTS,
    LOGIN_LOCKOUT_MINUTES,
)
from dao import account_dao, usage_dao


# ---------- API 키 인증 (기존, v0.3.0) ----------

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

    new_count = await usage_dao.increment_today_count(account["id"])

    if account["account_type"] == "deployment" and account["daily_limit"] is not None:
        if new_count > account["daily_limit"]:
            raise HTTPException(status_code=429, detail="오늘의 사용량 한도를 초과했습니다.")

    return account


# ---------- 대시보드 로그인 (신규, v0.4.0) ----------

def hash_password(raw_password: str) -> str:
    return bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt()).decode()


def verify_password(raw_password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(raw_password.encode(), password_hash.encode())


def create_access_token(account_id: str) -> str:
    payload = {
        "sub": str(account_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def login(username: str, password: str) -> str:
    account = await account_dao.find_by_username(username)

    if not account or not account["is_active"] or not account["password_hash"]:
        # 계정이 없는 경우와 비밀번호가 틀린 경우를 같은 메시지로 응답 —
        # "이 아이디는 존재하지 않는다"는 정보 자체를 노출하지 않기 위함
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    if account["locked_until"] and account["locked_until"] > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=423,
            detail=f"로그인 시도가 너무 많습니다. {LOGIN_LOCKOUT_MINUTES}분 후 다시 시도하세요.",
        )

    if not verify_password(password, account["password_hash"]):
        attempts = account["failed_login_attempts"] + 1
        lock_until = None
        if attempts >= LOGIN_MAX_ATTEMPTS:
            lock_until = datetime.now(timezone.utc) + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        await account_dao.register_failed_login(account["id"], lock_until)
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    await account_dao.reset_login_attempts(account["id"])
    return create_access_token(account["id"])


async def get_current_account(authorization: str = Header(...)) -> dict:
    """Authorization: Bearer <JWT> 헤더를 검증해서 로그인된 계정 정보를 반환."""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="인증 토큰이 필요합니다.")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="유효하지 않거나 만료된 토큰입니다.")

    account = await account_dao.find_by_id(payload.get("sub"))
    if not account or not account["is_active"]:
        raise HTTPException(status_code=401, detail="유효하지 않은 계정입니다.")

    return account
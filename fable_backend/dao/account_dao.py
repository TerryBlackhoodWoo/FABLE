"""
accounts 테이블 접근 전담 (Postgres/Supabase).
API 키는 해시로만 비교 — 원문을 DB에 저장하지 않는다.
"""

from database_pg import get_pool


async def find_by_key_hash(key_hash: str) -> dict | None:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, account_type, label, daily_limit, is_active
        FROM accounts
        WHERE api_key_hash = $1
        """,
        key_hash,
    )
    return dict(row) if row else None


async def create_account(
    key_hash: str,
    key_prefix: str,
    account_type: str,
    label: str | None = None,
    daily_limit: int | None = None,
) -> dict:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO accounts (api_key_hash, api_key_prefix, account_type, label, daily_limit)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, account_type, label, daily_limit, is_active
        """,
        key_hash,
        key_prefix,
        account_type,
        label,
        daily_limit,
    )
    return dict(row)

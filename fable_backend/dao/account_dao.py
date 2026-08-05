"""
accounts 테이블 접근 전담 (Postgres/Supabase).
API 키는 해시로만 비교 — 원문을 DB에 저장하지 않는다.
로그인(username/password)도 같은 원칙: 비밀번호는 해시로만 저장.
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


# ---------- 로그인 (v0.4.0) ----------

async def find_by_id(account_id: str) -> dict | None:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, account_type, label, daily_limit, is_active, username
        FROM accounts
        WHERE id = $1
        """,
        account_id,
    )
    return dict(row) if row else None


async def find_by_username(username: str) -> dict | None:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, account_type, label, is_active, password_hash,
               failed_login_attempts, locked_until
        FROM accounts
        WHERE username = $1
        """,
        username,
    )
    return dict(row) if row else None


async def set_login_credentials(account_id: str, username: str, password_hash: str) -> None:
    pool = get_pool()
    await pool.execute(
        """
        UPDATE accounts
        SET username = $2, password_hash = $3
        WHERE id = $1
        """,
        account_id,
        username,
        password_hash,
    )


async def register_failed_login(account_id: str, lock_until) -> None:
    """실패 시도 +1. lock_until이 주어지면 잠금도 같이 설정."""
    pool = get_pool()
    await pool.execute(
        """
        UPDATE accounts
        SET failed_login_attempts = failed_login_attempts + 1,
            locked_until = COALESCE($2, locked_until)
        WHERE id = $1
        """,
        account_id,
        lock_until,
    )


async def reset_login_attempts(account_id: str) -> None:
    pool = get_pool()
    await pool.execute(
        """
        UPDATE accounts
        SET failed_login_attempts = 0, locked_until = NULL
        WHERE id = $1
        """,
        account_id,
    )
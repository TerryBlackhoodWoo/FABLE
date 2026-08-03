"""
usage_counters 테이블 접근 전담 (Postgres/Supabase).
(계정, 날짜) 복합키라 날짜가 바뀌면 새 행이 자동으로 생기는 구조 — 별도 리셋 배치 불필요.
"""

from database_pg import get_pool


async def get_today_count(account_id: str) -> int:
    pool = get_pool()
    row = await pool.fetchrow(
        """
        SELECT request_count FROM usage_counters
        WHERE account_id = $1 AND usage_date = CURRENT_DATE
        """,
        account_id,
    )
    return row["request_count"] if row else 0


async def increment_today_count(account_id: str) -> int:
    """
    오늘자 카운터를 원자적으로 +1 하고, 증가된 이후 값을 반환.
    INSERT ... ON CONFLICT로 "오늘 첫 요청이면 새로 만들고, 아니면 증가"를 한 번에 처리.
    """
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO usage_counters (account_id, usage_date, request_count)
        VALUES ($1, CURRENT_DATE, 1)
        ON CONFLICT (account_id, usage_date)
        DO UPDATE SET request_count = usage_counters.request_count + 1
        RETURNING request_count
        """,
        account_id,
    )
    return row["request_count"]
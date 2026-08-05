"""
conversation_logs 테이블 접근 전담 (Postgres/Supabase).
"""

import json

from database_pg import get_pool


async def insert_log(
    account_id: str | None,
    question: str,
    answer: str,
    speaker: str,
    source_summary: dict,
) -> None:
    pool = get_pool()
    await pool.execute(
        """
        INSERT INTO conversation_logs (account_id, question, answer, speaker, source_summary)
        VALUES ($1, $2, $3, $4, $5)
        """,
        account_id,
        question,
        answer,
        speaker,
        json.dumps(source_summary, ensure_ascii=False),
    )


async def list_by_account(account_id: str, limit: int = 50) -> list[dict]:
    """대시보드 조회용 — 최신순으로 최근 N개."""
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT id, question, answer, speaker, created_at
        FROM conversation_logs
        WHERE account_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        account_id,
        limit,
    )
    return [dict(r) for r in rows]

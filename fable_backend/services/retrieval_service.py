"""
질문 임베딩 생성(gemini_service)과 유사 청크 조회(source_chunk_dao)를 조합하는 계층.
컨트롤러가 이 두 계층을 직접 알 필요 없이, 이 서비스 하나만 호출하면 되도록 감싼다.
"""

from dao import source_chunk_dao
from services import gemini_service


async def search_similar_chunks(question: str) -> list[dict]:
    query_vector = await gemini_service.embed_query(question)
    return await source_chunk_dao.find_similar_chunks(query_vector)

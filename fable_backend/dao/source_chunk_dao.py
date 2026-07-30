"""
source_chunks 컬렉션 데이터 접근 계층.

역할 경계: 이 파일은 "이미 만들어진 쿼리 벡터를 받아서 몽고에서 유사 청크를 가져오는 것"까지만
책임진다. 임베딩 생성(Gemini 호출)은 services 쪽 책임이라 여기 들어오지 않는다.
"""

from config import COLLECTION_NAME, VECTOR_INDEX_NAME, TOP_K
from database import get_db


async def find_similar_chunks(
    query_vector: list[float], top_k: int = TOP_K
) -> list[dict]:
    collection = get_db()[COLLECTION_NAME]

    pipeline = [
        {
            "$vectorSearch": {
                "index": VECTOR_INDEX_NAME,
                "path": "embedding",
                "queryVector": query_vector,
                "numCandidates": 100,
                "limit": top_k,
            }
        },
        {
            "$project": {
                "_id": 0,
                "work_title": 1,
                "chapter": 1,
                "chunk_text": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    cursor = collection.aggregate(pipeline)
    return [doc async for doc in cursor]


async def insert_chunks(docs: list[dict]) -> int:
    """build_source_chunks.py 같은 적재 스크립트에서도 재사용 가능하도록 분리해둠."""
    collection = get_db()[COLLECTION_NAME]
    result = await collection.insert_many(docs)
    return len(result.inserted_ids)

"""
FABLE 01단계 — 원전 텍스트 청크 분할 + 임베딩 + MongoDB 저장

사용법:
1. 이 파일과 같은 폴더(또는 하위 sources/ 폴더)에 아래 두 파일 위치:
   - iliad_book1.md   (일리아드 BOOK I, Samuel Butler역)
   - odyssey_book8.md (오디세이아 BOOK VIII, Samuel Butler역)
2. .env에 MONGODB_URI, GEMINI_API_KEY 있는지 확인
3. pip install "motor[srv]" python-dotenv google-genai
4. python build_source_chunks.py

무엇을 하는가:
- 각 파일을 문단 단위로 읽어서, 너무 짧은 문단은 합치고 너무 긴 문단은 문장 단위로 쪼갬
- 청크마다 앞 청크의 마지막 1문장을 살짝 겹쳐 붙여서(overlap) 문맥 단절 방지
- Gemini Embedding API(gemini-embedding-001)로 벡터화
- MongoDB의 fable_mvp.source_chunks 컬렉션에 저장
"""

import asyncio
import os
import re
import sys

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from google import genai

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DB_NAME = "fable_mvp"
COLLECTION_NAME = "source_chunks"

# 청크 분할 기준 (대략적인 글자 수 기준 — 한국어 토크나이저 없이도 간단히 조절 가능)
TARGET_CHUNK_CHARS = 1200  # 청크 하나 목표 크기 (영문 기준 대략 250~300 토큰)
OVERLAP_SENTENCES = 1  # 앞 청크에서 겹쳐 가져올 문장 수

SOURCES = [
    {
        "path": "sources/iliad_book1.md",
        "work_title": "일리아드",
        "chapter": "BOOK I",
        "translator": "Samuel Butler",
    },
    {
        "path": "sources/odyssey_book8.md",
        "work_title": "오디세이아",
        "chapter": "BOOK VIII",
        "translator": "Samuel Butler",
    },
]


def split_sentences(text: str) -> list[str]:
    """아주 단순한 문장 분리기. 영문 원전 산문 기준으로 충분히 동작."""
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z“\"])", text)
    return [s.strip() for s in sentences if s.strip()]


def build_chunks(raw_text: str) -> list[str]:
    """문단 구분을 무시하고 전체를 문장 리스트로 만든 뒤,
    목표 글자 수에 맞춰 문장을 이어붙여 청크를 만들고 약간씩 겹치게 한다."""
    # 마크다운 헤더, 각주 링크 등 잡음 제거
    cleaned = re.sub(r"\[\[\d+\]\]\([^)]*\)", "", raw_text)  # 각주 링크 제거
    cleaned = re.sub(r"^#.*$", "", cleaned, flags=re.MULTILINE)  # 헤더 라인 제거

    sentences = split_sentences(cleaned)

    chunks = []
    current: list[str] = []
    current_len = 0

    for sent in sentences:
        current.append(sent)
        current_len += len(sent)
        if current_len >= TARGET_CHUNK_CHARS:
            chunks.append(" ".join(current))
            # 다음 청크는 마지막 OVERLAP_SENTENCES 문장부터 다시 시작 (문맥 연결용)
            current = current[-OVERLAP_SENTENCES:] if OVERLAP_SENTENCES else []
            current_len = sum(len(s) for s in current)

    if current:
        chunks.append(" ".join(current))

    return chunks


async def embed_texts(client: genai.Client, texts: list[str]) -> list[list[float]]:
    """Gemini Embedding API 호출. 문서 검색용 임베딩이므로 task_type=RETRIEVAL_DOCUMENT 사용."""
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=texts,
        config={"task_type": "RETRIEVAL_DOCUMENT"},
    )
    return [e.values for e in result.embeddings]


async def main():
    if not MONGODB_URI or not GEMINI_API_KEY:
        print("❌ .env에서 MONGODB_URI 또는 GEMINI_API_KEY를 찾지 못했습니다.")
        sys.exit(1)

    mongo_client = AsyncIOMotorClient(MONGODB_URI)
    db = mongo_client[DB_NAME]
    collection = db[COLLECTION_NAME]

    genai_client = genai.Client(api_key=GEMINI_API_KEY)

    total_inserted = 0

    for source in SOURCES:
        path = source["path"]
        if not os.path.exists(path):
            print(
                f"⚠️  {path} 를 찾을 수 없어 건너뜁니다. 스크립트와 같은 위치에 sources/ 폴더를 두세요."
            )
            continue

        with open(path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        chunks = build_chunks(raw_text)
        print(
            f"[{source['work_title']} {source['chapter']}] 청크 {len(chunks)}개 생성됨"
        )

        # Gemini Embedding API는 한 번에 여러 텍스트를 받을 수 있지만,
        # 안전하게 소량 배치로 나눠서 호출 (요청 크기 제한 회피)
        BATCH_SIZE = 10
        docs_to_insert = []

        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            embeddings = await embed_texts(genai_client, batch)

            for chunk_text, embedding in zip(batch, embeddings):
                docs_to_insert.append(
                    {
                        "work_title": source["work_title"],
                        "chapter": source["chapter"],
                        "translator": source["translator"],
                        "chunk_text": chunk_text,
                        "embedding": embedding,
                    }
                )

        if docs_to_insert:
            result = await collection.insert_many(docs_to_insert)
            inserted = len(result.inserted_ids)
            total_inserted += inserted
            print(f"  → MongoDB에 {inserted}개 저장 완료")

    print(
        f"\n✅ 전체 완료: 총 {total_inserted}개 청크가 {DB_NAME}.{COLLECTION_NAME}에 저장됨"
    )
    mongo_client.close()


if __name__ == "__main__":
    asyncio.run(main())

"""
FABLE 02단계 — 원전 텍스트(일리아드/오디세이아 전체 24권 + 역사 9권) 청크 분할 + 임베딩 + MongoDB 저장

이전 버전(01단계)은 일리아드 BOOK I / 오디세이아 BOOK VIII 두 챕터만 손으로 잘라 처리했지만,
이 버전은 "## BOOK N" 헤더를 기준으로 각 작품 전체를 자동으로 Book 단위로 나눠 처리한다.
헤로도토스의 "## NOTES TO BOOK N"(각주) 섹션은 본문이 아니므로 자동으로 건너뛴다.

사용법:
1. sources/ 폴더에 아래 4개 파일 위치 (이미 준비되어 있음):
   - iliad_full.md      (일리아드 전체, Samuel Butler역)
   - odyssey_full.md    (오디세이아 전체, Samuel Butler역)
   - herodotus_vol1.md  (역사 1~4권, G. C. Macaulay역)
   - herodotus_vol2.md  (역사 5~9권, G. C. Macaulay역)
2. .env에 MONGODB_URI, GEMINI_API_KEY 있는지 확인
3. pip install "motor[srv]" python-dotenv google-genai
4. python build_source_chunks.py

무엇을 하는가:
- 각 파일을 "## BOOK N" 헤더 기준으로 Book 단위 세그먼트로 분리 (NOTES/PREFACE 등은 제외)
- 각 Book 안에서 문장 단위로 재조립 → 약 1,200자(≈250~300토큰)마다 청크로 자름
- 청크 경계에서 문맥 끊기지 않게 앞 청크 마지막 문장을 다음 청크 앞에 겹쳐 붙임
- Gemini Embedding API(gemini-embedding-001)로 벡터화
- **재실행 시 중복 방지**: 같은 work_title의 기존 청크를 먼저 삭제하고 새로 삽입 (idempotent)
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

TARGET_CHUNK_CHARS = 1200
OVERLAP_SENTENCES = 1
EMBED_BATCH_SIZE = 20

# 하나의 work_title에 여러 파일이 걸쳐있을 수 있음 (헤로도토스 = 2권)
SOURCES = [
    {
        "paths": ["sources/iliad_full.md"],
        "work_title": "일리아드",
        "translator": "Samuel Butler",
    },
    {
        "paths": ["sources/odyssey_full.md"],
        "work_title": "오디세이아",
        "translator": "Samuel Butler",
    },
    {
        "paths": ["sources/herodotus_vol1.md", "sources/herodotus_vol2.md"],
        "work_title": "역사",
        "translator": "G. C. Macaulay",
    },
]

BOOK_HEADER_RE = re.compile(r"^##\s+(BOOK\s+[IVXLCDM]+)\b", re.IGNORECASE)
ANY_HEADER_RE = re.compile(r"^##\s+")


def split_into_books(raw_text: str) -> list[tuple[str, str]]:
    """'## BOOK N' 헤더 기준으로 (챕터 라벨, 본문) 리스트를 만든다.
    NOTES/PREFACE/FOOTNOTES 등 BOOK이 아닌 섹션(각주, 서문 등)은 제외한다."""
    books: list[tuple[str, str]] = []
    current_label: str | None = None
    current_lines: list[str] = []

    for line in raw_text.splitlines():
        if ANY_HEADER_RE.match(line):
            if current_label:
                books.append((current_label, "\n".join(current_lines)))
            m = BOOK_HEADER_RE.match(line)
            current_label = m.group(1).upper() if m else None
            current_lines = []
        elif current_label:
            current_lines.append(line)

    if current_label:
        books.append((current_label, "\n".join(current_lines)))

    return books


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    return [
        s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z“\"])", text) if s.strip()
    ]


def build_chunks(raw_text: str) -> list[str]:
    cleaned = re.sub(r"\[\[\d+\]\]\([^)]*\)", "", raw_text)
    sentences = split_sentences(cleaned)

    chunks, current, current_len = [], [], 0
    for sent in sentences:
        current.append(sent)
        current_len += len(sent)
        if current_len >= TARGET_CHUNK_CHARS:
            chunks.append(" ".join(current))
            current = current[-OVERLAP_SENTENCES:] if OVERLAP_SENTENCES else []
            current_len = sum(len(s) for s in current)
    if current:
        chunks.append(" ".join(current))
    return chunks


async def embed_texts(client: genai.Client, texts: list[str]) -> list[list[float]]:
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
    collection = mongo_client[DB_NAME][COLLECTION_NAME]
    genai_client = genai.Client(api_key=GEMINI_API_KEY)

    total_inserted = 0

    for source in SOURCES:
        work_title = source["work_title"]

        # 재실행 시 중복 방지 — 같은 작품의 기존 청크를 먼저 삭제
        deleted = await collection.delete_many({"work_title": work_title})
        if deleted.deleted_count:
            print(
                f"[{work_title}] 기존 청크 {deleted.deleted_count}개 삭제 (재처리 전 정리)"
            )

        all_books: list[tuple[str, str]] = []
        for path in source["paths"]:
            if not os.path.exists(path):
                print(f"⚠️  {path} 를 찾을 수 없어 건너뜁니다.")
                continue
            with open(path, "r", encoding="utf-8") as f:
                raw_text = f.read()
            all_books.extend(split_into_books(raw_text))

        print(f"[{work_title}] {len(all_books)}개 Book 발견")

        for chapter_label, book_text in all_books:
            chunks = build_chunks(book_text)
            if not chunks:
                continue

            docs_to_insert = []
            for i in range(0, len(chunks), EMBED_BATCH_SIZE):
                batch = chunks[i : i + EMBED_BATCH_SIZE]
                embeddings = await embed_texts(genai_client, batch)
                for chunk_text, embedding in zip(batch, embeddings):
                    docs_to_insert.append(
                        {
                            "work_title": work_title,
                            "chapter": chapter_label,
                            "translator": source["translator"],
                            "chunk_text": chunk_text,
                            "embedding": embedding,
                        }
                    )

            if docs_to_insert:
                result = await collection.insert_many(docs_to_insert)
                inserted = len(result.inserted_ids)
                total_inserted += inserted
                print(f"  {chapter_label}: 청크 {len(chunks)}개 → 저장 완료")

    print(
        f"\n✅ 전체 완료: 총 {total_inserted}개 청크가 {DB_NAME}.{COLLECTION_NAME}에 저장됨"
    )
    mongo_client.close()


if __name__ == "__main__":
    asyncio.run(main())

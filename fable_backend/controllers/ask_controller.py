"""
/ask 라우트를 담당하는 컨트롤러.
비즈니스 로직(검색, 라우팅, 답변 생성, 이미지 검색)은 services에 위임하고,
여기서는 요청을 받아 서비스들을 asyncio.gather로 동시 호출한 뒤 응답 형태로 조립하는 것만 한다.
"""

import asyncio

from fastapi import APIRouter

from config import SPEAKER_SEARCH_TERMS
from schemas import AskRequest, AskResponse, SourceChunk, CharacterImage
from services import retrieval_service, gemini_service, wiki_image_service

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    # 1단계: 벡터 검색(임베딩+DB조회)과 라우팅 판단(+이미지 검색어 생성)을 asyncio.gather로 동시 처리
    search_task = asyncio.create_task(
        retrieval_service.search_similar_chunks(request.question)
    )
    routing_task = asyncio.create_task(gemini_service.decide_routing(request.question))

    chunks, routing = await asyncio.gather(search_task, routing_task)
    speaker = routing.get("speaker", "호메로스")
    image_query = routing.get("image_query", "")
    fallback_title = SPEAKER_SEARCH_TERMS.get(speaker, speaker)

    # 2단계: 답변 생성(Gemini)과 장면 기반 이미지 검색(Wikimedia)도 서로 무관한 작업이라 동시 처리
    answer_task = asyncio.create_task(
        gemini_service.generate_answer(request.question, chunks, routing)
    )
    image_task = asyncio.create_task(
        wiki_image_service.search_character_image(image_query, fallback_title)
    )

    answer, image_data = await asyncio.gather(answer_task, image_task)

    return AskResponse(
        answer=answer,
        speaker=speaker,
        sources=[
            SourceChunk(
                work_title=c["work_title"],
                chapter=c["chapter"],
                chunk_text=c["chunk_text"],
                score=c["score"],
            )
            for c in chunks
        ],
        image=CharacterImage(**image_data) if image_data else None,
    )


@router.get("/health")
async def health():
    return {"status": "ok"}

"""
Gemini API 호출을 모아둔 서비스 계층.
DB 접근은 하지 않고, 오직 "텍스트를 Gemini에 보내고 결과를 받는" 책임만 가진다.
"""

import asyncio
import json

from google import genai

from config import GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL, GEMINI_CHAT_MODEL, SPEAKERS

_client: genai.Client | None = None


def connect():
    global _client
    _client = genai.Client(api_key=GEMINI_API_KEY)


def get_client() -> genai.Client:
    if _client is None:
        raise RuntimeError("Gemini 클라이언트가 아직 초기화되지 않았습니다. connect()를 먼저 호출하세요.")
    return _client


async def embed_query(text: str) -> list[float]:
    """검색 쿼리용 임베딩 (task_type=RETRIEVAL_QUERY)."""
    result = get_client().models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=[text],
        config={"task_type": "RETRIEVAL_QUERY"},
    )
    return result.embeddings[0].values


async def decide_routing(question: str) -> dict:
    """질문을 어느 화자가 답할지 판단."""
    speaker_list = "\n".join(f"- {name}: {desc}" for name, desc in SPEAKERS.items())

    prompt = f"""다음은 FABLE 서비스의 화자 목록입니다:
{speaker_list}

사용자 질문: "{question}"

이 질문에 가장 적합하게 답변할 화자를 목록 중에서 한 명 선택하세요.
질문이 특정 인물의 감정/행동/디테일을 구체적으로 묻는다면 그 인물로,
전반적인 배경 설명이나 두 작품을 아우르는 질문이면 "호메로스"로 판단하세요.

반드시 아래 JSON 형식으로만 답하세요 (다른 설명 없이):
{{"speaker": "선택한 화자 이름", "reason": "간단한 판단 이유(한 문장)"}}"""

    response = await asyncio.to_thread(
        get_client().models.generate_content,
        model=GEMINI_CHAT_MODEL,
        contents=prompt,
    )

    text = response.text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"speaker": "호메로스", "reason": "라우팅 판단 실패로 기본 내레이터 배정"}


async def generate_answer(question: str, chunks: list[dict], routing: dict) -> str:
    """검색된 청크 + 라우팅 결과를 근거로 캐릭터 1인칭 답변 생성."""
    speaker = routing.get("speaker", "호메로스")
    speaker_desc = SPEAKERS.get(speaker, SPEAKERS["호메로스"])

    if chunks:
        context_block = "\n\n".join(
            f"[출처: {c['work_title']} {c['chapter']}]\n{c['chunk_text']}" for c in chunks
        )
    else:
        context_block = "(관련 원문 근거를 찾지 못했습니다.)"

    prompt = f"""당신은 {speaker}입니다. {speaker_desc}

다음은 참고할 원문 발췌(영문 원전, Samuel Butler역)입니다:
{context_block}

규칙:
1. 반드시 한국어로, {speaker} 한 사람의 1인칭 말투로만 답할 것.
   다른 인물의 대사를 인용하거나 화자를 중간에 바꾸지 말 것 — 채팅 메신저처럼 그 인물 한 명이 직접 대화하는 형식을 유지할 것.
2. 분량은 3~5문장, 400자 이내로 짧게. 배경 설명을 전부 욱여넣지 말고 질문에 곧바로 답할 것.
3. 원문을 그대로 옮기지 말고 요약·의역할 것. 부득이하게 인용해도 15단어(영문 기준)를 넘기지 말 것.
4. 문장 끝이 아니라 답변 전체에 걸쳐 자연스럽게, 필요하면 근거 챕터를 한 번만 짧게 언급할 것 (예: "—일리아드 1권 기준" 정도).
5. 근거 원문이 부족하면 솔직하게 "이 부분은 아직 다루지 못했다"는 취지로 짧게 답할 것 — 지어내지 말 것.
6. 신화적 서술과 역사적 실증을 혼동하지 말 것.
7. 질문이 다른 인물(예: 아킬레우스)의 사정을 더 알아야 답이 될 것 같으면, 그 인물의 대사를 지어내지 말고
   "그건 아킬레우스한테 직접 물어보시오" 식으로 짧게 안내만 할 것 (실제로 그 인물이 되어 말하지 말 것).

사용자 질문: {question}"""

    response = await asyncio.to_thread(
        get_client().models.generate_content,
        model=GEMINI_CHAT_MODEL,
        contents=prompt,
    )
    return response.text.strip()
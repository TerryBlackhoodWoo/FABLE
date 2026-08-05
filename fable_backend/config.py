import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")  # Supabase(Postgres) 연결 문자열

# 대시보드 로그인 (v0.4.0)
JWT_SECRET = os.getenv("JWT_SECRET")  # 반드시 .env에 긴 랜덤 문자열로 설정
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 12  # 12시간
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

DB_NAME = "fable_mvp"
COLLECTION_NAME = "source_chunks"
VECTOR_INDEX_NAME = "vector_index"

TOP_K = 4  # 검색해서 가져올 청크 개수

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
# 별칭(alias) 사용 — Google이 Flash 모델을 교체해도 코드를 안 건드려도 되도록.
# (2026-07-30 기준 gemini-3.6-flash를 가리킴)
GEMINI_CHAT_MODEL = "gemini-flash-latest"

# 01단계 스코프에 등장하는 화자 목록 (일리아드 BOOK I + 오디세이아 BOOK VIII 기준)
SPEAKERS = {
    "호메로스": "내레이터. 두 서사시 전체를 소개하고, 세부 인물이 필요할 때 다른 화자로 넘긴다.",
    "아킬레우스": "일리아드 BOOK I의 주인공. 아가멤논과의 갈등으로 전쟁에서 물러난다.",
    "아가멤논": "그리스 연합군 총사령관. 아킬레우스와 갈등을 빚는 인물.",
    "오디세우스": "오디세이아 BOOK VIII에서 데모도코스에게 목마 노래를 청하는 인물.",
    "데모도코스": "눈먼 음유시인. 목마 이야기를 노래로 들려준다.",
}

# 화자별 영문 위키백과 문서 제목 (동명이인 없이 정확히 그 인물을 가리키는 제목으로)
SPEAKER_SEARCH_TERMS = {
    "호메로스": "Homer",
    "아킬레우스": "Achilles",
    "아가멤논": "Agamemnon",
    "오디세우스": "Odysseus",
    "데모도코스": "Demodocus",
}

WIKIMEDIA_USER_AGENT = "FABLE/0.1 (https://github.com/TerryBlackhoodWoo/FABLE)"
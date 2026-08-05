from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class SourceChunk(BaseModel):
    work_title: str
    chapter: str
    chunk_text: str
    score: float


class CharacterImage(BaseModel):
    title: str
    thumb_url: str
    source_url: str
    artist: str
    license: str


class AskResponse(BaseModel):
    answer: str
    speaker: str
    sources: list[SourceChunk]
    image: CharacterImage | None = None


# ---------- 대시보드 로그인 (v0.4.0) ----------

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogEntry(BaseModel):
    id: int
    question: str
    answer: str | None
    speaker: str | None
    created_at: str


class UsageResponse(BaseModel):
    today_count: int
    daily_limit: int | None
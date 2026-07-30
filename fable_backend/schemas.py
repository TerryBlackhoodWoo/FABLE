from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str


class SourceChunk(BaseModel):
    work_title: str
    chapter: str
    chunk_text: str
    score: float


class AskResponse(BaseModel):
    answer: str
    speaker: str
    sources: list[SourceChunk]

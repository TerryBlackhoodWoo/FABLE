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

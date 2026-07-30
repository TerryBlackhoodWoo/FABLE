"""
FABLE 01단계 MVP — 앱 진입점

실행:
  pip install fastapi uvicorn "motor[srv]" python-dotenv google-genai
  uvicorn main:app --reload
  → http://127.0.0.1:8000/docs 에서 /ask 테스트
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

import database
from services import gemini_service
from controllers.ask_controller import router as ask_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.connect()
    gemini_service.connect()
    yield
    database.close()


app = FastAPI(title="FABLE 01단계 MVP", lifespan=lifespan)
app.include_router(ask_router)

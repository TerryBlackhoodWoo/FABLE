"""
FABLE 01단계 MVP — 앱 진입점

실행:
  pip install fastapi uvicorn "motor[srv]" python-dotenv google-genai
  uvicorn main:app --reload
  → http://127.0.0.1:8000/docs 에서 /ask 테스트
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database
import database_pg
from config import CORS_ALLOWED_ORIGINS
from services import gemini_service
from controllers.ask_controller import router as ask_router
from controllers.dashboard_controller import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.connect()
    await database_pg.connect()
    gemini_service.connect()
    yield
    database.close()
    await database_pg.close()


app = FastAPI(title="FABLE 01단계 MVP", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ask_router)
app.include_router(dashboard_router)

# FABLE 01단계 MVP — FastAPI 백엔드 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성만 먼저 복사해서 캐시 활용 (코드만 바뀌면 pip install 다시 안 돌게)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# .env는 이미지에 절대 포함하지 않는다 (실행 시 --env-file 또는 플랫폼 환경변수로 주입)

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

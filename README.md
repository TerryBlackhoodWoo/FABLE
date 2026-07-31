# FABLE

영화·게임을 보기 전, 관련 신화·역사 속 인물이 직접 배경지식을 브리핑해주는 RAG 기반 캐릭터 챗 백엔드.

> "각색은 다르지만 검증된 사실은 일치한다" — 여러 각색 매체가 같은 사건을 다르게 그려도, 검증 가능한 원전 사실은 하나로 수렴한다는 게 이 프로젝트의 콘텐츠 문법입니다.

프론트엔드 저장소: [FABLE_frontend](https://github.com/TerryBlackhoodWoo/FABLE_frontend)

## 프로젝트 소개

〈남산의 부장들〉을 배경지식 없이 봤을 때와, 관련 역사(10·26 등)를 알고 봤을 때 같은 영화가 완전히 다르게 읽혔던 경험에서 출발한 프로젝트입니다. FABLE은 이 경험을 서비스로 만들었습니다 — 영화를 보기 전, 신화·역사 속 인물(내레이터)이 직접 "이거 알고 보면 더 재밌어"라고 브리핑해주는 캐릭터 챗입니다.

01단계 MVP는 호메로스가 진행하는 신화 도메인(일리아스·오디세이아)을 다룹니다.

## 핵심 설계

- **내레이터 → 캐릭터 핸드오프**: 호메로스가 전체 흐름을 안내하다가, 질문이 특정 인물(아킬레우스 등)의 디테일을 물으면 그 캐릭터로 답변 화자가 전환됩니다.
- **원전 근거 우선**: 모든 답변은 퍼블릭도메인 원전(Samuel Butler역 일리아드/오디세이아) 청크를 RAG로 검색해 근거로 삼습니다. 원문 인용은 15단어 이내로 제한하고, 근거가 부족하면 "아직 다루지 못했다"고 솔직히 답합니다.
- **1답변 1화자**: 답변 안에서 화자가 임의로 바뀌지 않도록 프롬프트 레벨에서 강제합니다.

## 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | FastAPI (Python 3.11, async) |
| 벡터 검색 | MongoDB Atlas Vector Search |
| LLM | Gemini API (`gemini-flash-latest`, `gemini-embedding-001`) |
| 컨테이너 | Docker |
| 배포 | Railway (예정) |

## 아키텍처

```
[Next.js(TS) 프론트엔드]
        │ HTTPS/JSON
        ▼
[FastAPI 백엔드 (async)]
    │
    ├─→ [MongoDB Atlas Vector Search] — 원전 텍스트 임베딩 저장/검색
    │
    └─→ [Gemini API] — 질문 라우팅 판단 + 답변 생성
         (asyncio.gather로 검색+라우팅 동시 처리)
```

### 백엔드 레이어 구조

```
fable_backend/
├── main.py                      # 앱 진입점, CORS/lifespan 설정
├── config.py                    # 환경변수, 상수, 화자 목록
├── database.py                  # MongoDB 연결 관리
├── schemas.py                   # 요청/응답 Pydantic 모델
├── dao/
│   └── source_chunk_dao.py      # DB 접근 전담 (벡터 검색 쿼리)
├── services/
│   ├── gemini_service.py        # Gemini 호출 (임베딩/라우팅/답변생성)
│   └── retrieval_service.py     # 임베딩+검색 조합
└── controllers/
    └── ask_controller.py        # /ask, /health 라우트
```

DAO(DB 접근) / Services(외부 API 호출) / Controllers(라우트)로 계층을 분리해, 각 레이어가 서로의 책임을 침범하지 않도록 설계했습니다.

## 로컬 실행

### 요구 사항
- Python 3.11+
- MongoDB Atlas 클러스터 (M0 무료 티어로 충분)
- Gemini API 키

### 설치

```bash
git clone https://github.com/TerryBlackhoodWoo/FABLE.git
cd FABLE/fable_backend
pip install -r requirements.txt
```

### 환경변수

`fable_backend/.env` 파일 생성:

```
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
GEMINI_API_KEY=<your-gemini-api-key>
```

> 값에 따옴표를 넣지 마세요. `python-dotenv`는 따옴표를 자동으로 처리하지만, Docker의 `--env-file` 옵션은 따옴표를 값의 일부로 그대로 읽어 연결 오류가 발생합니다.

### 실행

```bash
uvicorn main:app --reload
```

`http://127.0.0.1:8000/docs`에서 Swagger UI로 API를 테스트할 수 있습니다.

### Docker로 실행

```bash
docker build -t fable-backend .
docker run -d -p 8000:8000 --env-file .env --name fable-backend fable-backend
```

## API

### `POST /ask`

**요청**
```json
{
  "question": "아킬레우스는 왜 화가 났어?"
}
```

**응답**
```json
{
  "answer": "내가 왜 분노했냐고 묻는가? 오만함과 탐욕에 빠진 아가멤논이...",
  "speaker": "아킬레우스",
  "sources": [
    {
      "work_title": "일리아드",
      "chapter": "BOOK I",
      "chunk_text": "...",
      "score": 0.877
    }
  ]
}
```

### `GET /health`

서버 상태 확인용.

## 데이터 준비

원전 텍스트 청크 분할 + 임베딩 + MongoDB 저장은 `build_source_chunks.py`로 수행합니다.

```bash
python build_source_chunks.py
```

`sources/` 폴더에 있는 퍼블릭도메인 원전(Project Gutenberg, Samuel Butler역 일리아드·오디세이아)을 문장 단위로 재청크하고, Gemini Embedding API로 벡터화한 뒤 MongoDB의 `source_chunks` 컬렉션에 저장합니다.

## 현재 범위 (01단계)

- 신화 도메인: 일리아드 BOOK I(전쟁 발발 정황), 오디세이아 BOOK VIII(목마 에피소드)
- 화자: 호메로스(내레이터), 아킬레우스, 아가멤논, 오디세우스, 데모도코스

## 다음 단계

- [ ] Railway 배포
- [ ] 역사 도메인(헤로도토스) 추가
- [ ] 캐릭터 DB를 코드 하드코딩에서 MongoDB 컬렉션으로 이전

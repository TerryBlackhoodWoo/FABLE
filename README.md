# FABLE

영화·게임을 보기 전, 관련 신화·역사 속 인물이 직접 배경지식을 브리핑해주는 RAG 기반 캐릭터 챗 백엔드.

> "각색은 다르지만 검증된 사실은 일치한다" — 여러 각색 매체가 같은 사건을 다르게 그려도, 검증 가능한 원전 사실은 하나로 수렴한다는 게 이 프로젝트의 콘텐츠 문법입니다.

프론트엔드 저장소: [FABLE_frontend](https://github.com/TerryBlackhoodWoo/FABLE_frontend)

## 프로젝트 소개

〈남산의 부장들〉을 배경지식 없이 봤을 때와, 관련 역사(10·26 등)를 알고 봤을 때 같은 영화가 완전히 다르게 읽혔던 경험에서 출발한 프로젝트입니다. FABLE은 이 경험을 서비스로 만들었습니다 — 영화를 보기 전, 신화·역사 속 인물(내레이터)이 직접 "이거 알고 보면 더 재밌어"라고 브리핑해주는 캐릭터 챗입니다.

01단계 MVP는 호메로스가 진행하는 신화 도메인(일리아스·오디세이아)을 다뤘고, 이후 헤로도토스가 진행하는 역사 도메인(《역사》)이 추가되었습니다.

## 핵심 설계

- **신화/역사 도메인 분리 + 내레이터 → 캐릭터 핸드오프**: 호메로스(신화 도메인)와 헤로도토스(역사 도메인)가 각자 영역을 안내하다가, 질문이 특정 인물(아킬레우스 등)의 디테일을 물으면 그 캐릭터로 답변 화자가 전환됩니다.
- **원전 근거 우선**: 모든 답변은 퍼블릭도메인 원전(Samuel Butler역 일리아드/오디세이아, G.C. Macaulay역 헤로도토스 《역사》) 청크를 RAG로 검색해 근거로 삼습니다. 원문 인용은 15단어 이내로 제한하고, 근거가 부족하면 "아직 다루지 못했다"고 솔직히 답합니다.
- **1답변 1화자**: 답변 안에서 화자가 임의로 바뀌지 않도록 프롬프트 레벨에서 강제합니다.
- **멀티턴 대화**: 최근 5턴까지의 대화 히스토리를 요청에 함께 전달해, 이전 맥락을 반영한 답변이 가능합니다.
- **장면 기반 이미지 검색**: 답변마다 그 장면을 그린 고전 회화·유물 이미지를 Wikimedia에서 함께 찾아 보여줍니다. 인물 이름만으로 검색하면 동명이인이 걸리는 문제가 있어, 라우팅 판단 시 Gemini가 장면을 특정하는 영문 검색어까지 함께 생성하고, 실패 시 위키백과 인물 대표 이미지로 폴백합니다.
- **계정별 접근 제어**: 개발자 계정(무제한)과 배포용 계정(일일 한도)을 구분해 API 키로 인증합니다. 모든 요청은 Postgres에 로그로 남습니다.
- **대시보드 로그인**: 관리자가 발급한 아이디/비밀번호로 로그인해, 해당 계정의 대화 로그와 사용량을 조회할 수 있습니다. API 키 인증(콘텐츠용)과 완전히 분리된 별도 인증 트랙(JWT)입니다.

## 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | FastAPI (Python 3.11, async) |
| 벡터 검색 | MongoDB Atlas Vector Search |
| 계정 · 로그 | PostgreSQL (Supabase) |
| LLM | Gemini API (`gemini-flash-latest`, `gemini-embedding-001`) |
| 이미지 | Wikimedia Commons / Wikipedia API (키 불필요) |
| 인증 | API 키(SHA-256 해시) + JWT(대시보드 로그인, bcrypt) |
| 컨테이너 | Docker |
| 배포 | Railway |

## 아키텍처

```
[Next.js(TS) 프론트엔드]
        │ HTTPS/JSON (X-API-Key 또는 Bearer JWT)
        ▼
[FastAPI 백엔드 (async)]
    │
    ├─→ [PostgreSQL/Supabase] — API 키 인증, 사용량 제한, 대화 로그, 대시보드 로그인
    │
    ├─→ [MongoDB Atlas Vector Search] — 원전 텍스트 임베딩 저장/검색
    │
    ├─→ [Gemini API] — 질문 라우팅 판단(+이미지 검색어 생성) / 답변 생성
    │
    └─→ [Wikimedia Commons·Wikipedia API] — 장면 기반 캐릭터 이미지 검색

  0단계: API 키 검증 + 사용량 체크 (Gemini/Mongo 호출 전, 비용 발생 이전에 차단)
  1단계: 벡터검색 + 라우팅판단 → asyncio.gather로 동시 처리
  2단계: 답변생성(히스토리 반영) + 이미지검색 → asyncio.gather로 동시 처리
```

### 백엔드 레이어 구조

```
fable_backend/
├── main.py                      # 앱 진입점, CORS/lifespan(Mongo+Postgres) 설정
├── config.py                    # 환경변수, 상수, 화자 목록(SPEAKERS), CORS/JWT 설정
├── database.py                  # MongoDB 연결 관리
├── database_pg.py               # PostgreSQL(Supabase) 연결 관리 (asyncpg 풀)
├── schemas.py                   # 요청/응답 Pydantic 모델 (AskRequest에 history 필드 포함)
├── create_account.py            # API 키 계정 발급 CLI
├── set_login.py                 # 계정에 대시보드 로그인(ID/PW) 부여 CLI
├── build_source_chunks.py       # 원전 텍스트 → 청크 → 임베딩 → Mongo 저장 (전체 자동화)
├── migrations/
│   ├── 001_accounts_and_logs.sql
│   └── 002_login_columns.sql
├── sources/                     # 원전 텍스트 (Project Gutenberg, git 추적 제외)
│   ├── iliad_full.md            # 일리아드 24권 전체 (Samuel Butler역)
│   ├── odyssey_full.md          # 오디세이아 24권 전체 (Samuel Butler역)
│   ├── herodotus_vol1.md        # 역사 1~4권 (G.C. Macaulay역)
│   └── herodotus_vol2.md        # 역사 5~9권 (G.C. Macaulay역)
├── dao/
│   ├── source_chunk_dao.py      # Mongo — 벡터 검색 쿼리
│   ├── account_dao.py           # Postgres — 계정 조회/생성/로그인 정보
│   ├── usage_dao.py             # Postgres — 사용량 조회/원자적 증가
│   └── log_dao.py               # Postgres — 대화 로그 기록/조회
├── services/
│   ├── gemini_service.py        # Gemini 호출 (임베딩/라우팅+이미지쿼리/답변생성, 히스토리 반영)
│   ├── retrieval_service.py     # 임베딩+검색 조합
│   ├── wiki_image_service.py    # Wikimedia 장면 검색 + 인물 이미지 폴백
│   └── auth_service.py          # API 키 인증 + JWT 로그인 (완전히 분리된 두 트랙)
└── controllers/
    ├── ask_controller.py        # /ask, /health
    └── dashboard_controller.py  # /login, /logs, /usage
```

DAO(DB 접근) / Services(외부 API 호출) / Controllers(라우트)로 계층을 분리해, 각 레이어가 서로의 책임을 침범하지 않도록 설계했습니다.

## 로컬 실행

### 요구 사항
- Python 3.11+
- MongoDB Atlas 클러스터 (M0 무료 티어로 충분)
- PostgreSQL (Supabase 무료 티어로 충분) — **Session Pooler** 연결 문자열 권장
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
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@<region>.pooler.supabase.com:5432/postgres
JWT_SECRET=<32자 이상의 랜덤 문자열>
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

> 값에 따옴표를 넣지 마세요. `python-dotenv`는 따옴표를 자동으로 처리하지만, Docker의 `--env-file` 옵션은 따옴표를 값의 일부로 그대로 읽어 연결 오류가 발생합니다.

> `CORS_ALLOWED_ORIGINS`는 콤마로 구분해 여러 출처를 등록할 수 있습니다. 배포 시 프론트엔드 도메인을 추가해야 브라우저가 요청을 막지 않습니다.

> Supabase 연결 시 **Direct Connection이 아닌 Session Pooler**를 사용하세요. Direct Connection은 IPv6 전용이라 IPv6 미지원 네트워크에서 DNS 조회가 실패합니다.

> Wikimedia API는 별도 키가 필요 없습니다. `config.py`의 `WIKIMEDIA_USER_AGENT`만 정책에 맞게 식별 가능한 문자열로 유지하면 됩니다.

### 데이터베이스 마이그레이션

Supabase SQL Editor에서 순서대로 실행:
1. `migrations/001_accounts_and_logs.sql` — 계정/사용량/로그 테이블
2. `migrations/002_login_columns.sql` — 대시보드 로그인 컬럼 추가

### 계정 발급

```bash
# API 키 발급 (콘텐츠 API용)
python create_account.py --type developer --label "본인 테스트용"

# 위에서 받은 id로 대시보드 로그인 정보 부여 (선택)
python set_login.py --account-id <위에서 받은 id> --username terry --password "강력한 비밀번호"
```

API 키는 발급 시점에만 표시됩니다(DB엔 해시만 저장). 안전한 곳에 저장 후 클라이언트의 `X-API-Key` 헤더에 사용하세요.

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

## 배포 (Railway)

1. Railway에서 GitHub 저장소(`FABLE`) 연결
2. **Settings → Root Directory**를 `fable_backend`로 지정 (저장소 루트가 아니라 서브폴더에 `Dockerfile`이 있으므로 필수)
3. **Variables**에 위 환경변수 전부 등록 (`CORS_ALLOWED_ORIGINS`에 프론트 배포 도메인 포함)
4. **Settings → Networking → Generate Domain**으로 공개 URL 생성
5. GitHub에 push하면 자동 재배포됨

## API

### `POST /ask`

**요청 헤더**: `X-API-Key: fbl_dev_...`

**요청 본문**
```json
{
  "question": "아킬레우스는 왜 화가 났어?",
  "history": [
    { "role": "user", "content": "일리아드 1권 내용 알려줘" },
    { "role": "assistant", "content": "..." }
  ]
}
```
`history`는 선택 필드이며, 최근 5턴까지 전달해 멀티턴 대화 맥락을 반영합니다.

**응답**
```json
{
  "answer": "내가 왜 분노했냐고 묻는가? 오만함과 탐욕에 빠진 아가멤논이...",
  "speaker": "아킬레우스",
  "sources": [
    { "work_title": "일리아드", "chapter": "BOOK I", "chunk_text": "...", "score": 0.877 }
  ],
  "image": {
    "title": "Achilles Briseis MAN Napoli Inv9105 n01.jpg",
    "thumb_url": "https://upload.wikimedia.org/...",
    "source_url": "https://commons.wikimedia.org/wiki/File:...",
    "artist": "anonymous",
    "license": "Public domain"
  }
}
```
`image`는 관련 이미지를 찾지 못하면 `null`입니다. API 키가 없거나 유효하지 않으면 `401`, 배포용 계정이 일일 한도를 초과하면 `429`를 반환합니다.

### `POST /login`

**요청 본문**: `{ "username": "terry", "password": "..." }`
**응답**: `{ "access_token": "eyJ...", "token_type": "bearer" }`
5회 연속 실패 시 15분간 잠금(`423`).

### `GET /logs`, `GET /usage`

**요청 헤더**: `Authorization: Bearer <access_token>`
로그인한 계정의 최근 대화 로그(`/logs`)와 오늘 사용량(`/usage`)을 반환합니다.

### `GET /health`

서버 상태 확인용 (인증 불필요).

## 데이터 준비

원전 텍스트 청크 분할 + 임베딩 + MongoDB 저장은 `build_source_chunks.py`로 수행합니다.

```bash
python build_source_chunks.py
```

`sources/` 폴더에 있는 퍼블릭도메인 원전(Project Gutenberg — 일리아드·오디세이아 Samuel Butler역, 헤로도토스 《역사》 G.C. Macaulay역)을 Book 단위로 자동 청크 분할하고, Gemini Embedding API로 벡터화한 뒤 MongoDB의 `source_chunks` 컬렉션에 저장합니다. 재실행 시 기존 데이터를 지우고 전체로 교체합니다(`delete_many` 후 재삽입).

## 현재 범위

- 신화 도메인: 일리아드·오디세이아 (호메로스 내레이터)
- 역사 도메인: 헤로도토스 《역사》 (헤로도토스 내레이터) — 화자 라우팅 반영 완료
- 화자: 호메로스(내레이터, 신화 도메인), 아킬레우스, 아가멤논, 오디세우스, 데모도코스, 헤로도토스(역사 도메인)
- 답변마다 장면 기반 고전 미술/유물 이미지 첨부 (Wikimedia)
- 최근 5턴까지 대화 히스토리 반영 (멀티턴)
- API 키 기반 계정 인증, 배포용 계정 일일 사용량 제한, 전체 대화 로그 적재 (Postgres)
- 대시보드 로그인(JWT) + 로그/사용량 조회 API
- Railway 배포

## 다음 단계

- [x] 역사 도메인(헤로도토스) 화자 추가 — 라우팅 반영 완료
- [x] 원전 텍스트 전체 학습 (`build_source_chunks.py` 실행, 헤로도토스 원문 전체 적재)
- [x] 캐릭터 DB를 코드 하드코딩에서 MongoDB 컬렉션으로 이전
- [ ] 자소서/포트폴리오용 최종 문서화
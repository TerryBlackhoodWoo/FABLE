# FABLE Frontend

FABLE의 Next.js(TypeScript) 프론트엔드 — 원전 근거 캐릭터 챗 UI.

백엔드 저장소: [FABLE](https://github.com/TerryBlackhoodWoo/FABLE)

## 개요

질문을 입력하면 백엔드(`FastAPI`)의 `/ask`를 호출해, 신화 속 인물(호메로스 또는 핸드오프된 캐릭터)의 답변과 원전 출처(작품·챕터·유사도 점수), 그리고 그 장면을 그린 고전 미술/유물 이미지를 함께 보여주는 미니멀 채팅 UI입니다.

## 기술 스택

- Next.js 16 (App Router)
- TypeScript
- Tailwind CSS

## 디자인 방향

FABLE 기획 초기부터 이어져 온 그리스 도자기(테라코타·브론즈·다크어스) 팔레트를 웹에도 그대로 적용했습니다.

| 토큰 | 값 | 용도 |
|---|---|---|
| Background | `#16110D` | 페이지 배경 |
| Panel | `#1F1712` | 카드/입력창 배경 |
| Terracotta | `#C1592F` | 버튼, 화자명 강조 |
| Bronze | `#B0894F` | 보더, 라벨 |
| Cream | `#EFE4D0` | 본문 텍스트 |

- **Display**: Noto Serif KR (타이틀, 화자명)
- **Body**: Noto Sans KR (본문)
- **Mono**: IBM Plex Mono (출처·유사도 점수 라벨)
- **시그니처 요소**: 그리스 문양(meander) SVG 패턴 — 카드 상단 hairline으로만 절제해서 사용

## 로컬 실행

### 요구 사항
- Node.js 18+
- 실행 중인 FABLE 백엔드 ([설정 가이드](https://github.com/TerryBlackhoodWoo/FABLE))

### 설치

```bash
git clone https://github.com/TerryBlackhoodWoo/FABLE_frontend.git
cd FABLE_frontend
npm install
```

### 환경변수

`.env.local` 파일 생성:

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

### 실행

```bash
npm run dev
```

`http://localhost:3000`에서 확인합니다.

## 프로젝트 구조

```
src/app/
├── layout.tsx     # 폰트(Noto Serif/Sans KR, IBM Plex Mono) 설정
├── globals.css     # 전역 스타일, 색상 토큰
└── page.tsx        # 메인 채팅 UI (질문 입력, 답변/출처/이미지 표시)
```

## 기능

- 질문 입력 → `/ask` 호출 → 화자·답변·원전 출처·장면 이미지 표시
- 로딩 상태("묻는 중…"), 에러 메시지 — HTTP 오류 응답과 네트워크 연결 실패를 구분해서 실제 원인을 보여줌
- 이미지가 없는 응답(관련 명화를 못 찾은 경우)에도 자연스럽게 대응 (이미지 영역 자체를 렌더링하지 않음)

## 백엔드 연동 시 주의사항 (CORS)

백엔드가 다른 출처(포트 8000)에서 도는 만큼, FastAPI 쪽에 `CORSMiddleware`로 `localhost:3000`을 허용 출처로 등록해야 합니다. 이게 없으면 `OPTIONS /ask` 요청이 브라우저 단에서 `405`로 막힙니다 (백엔드 저장소의 `main.py` 참고).

## 다음 단계

- [ ] Railway 배포
- [ ] 대화 히스토리(멀티턴) UI
- [ ] 캐릭터 핸드오프 시각적 전환 효과
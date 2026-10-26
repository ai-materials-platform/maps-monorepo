# 재료 챗봇 게이트웨이

셸·PyQt 챗봇과 Qwen(DeepInfra) 사이에 서는 서버. 재료공학·MAPS 사용법 질문에만 답하고, 프롬프트 인젝션을 막고, API 키를 설치본에서 뺀다.
설계: `docs/specs/2026-10-26-materials-chat-gateway-design.md` · 계획: `docs/plans/2026-10-26-materials-chat-gateway.md`

요청 처리: 접속 코드 인증·횟수 제한 → 월 상한 → 주제·인젝션 판정 → RAG 검색 → 서버 시스템 프롬프트로 조립 → Qwen → 시스템 프롬프트 유출 검사.

## 로컬 실행

```bash
cd apps/gateway
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m pytest -q                              # 실제 모델 호출 없음
```

서버 실행에 필요한 환경변수:

| 이름 | 내용 |
|---|---|
| `UPSTREAM_BASE_URL` | DeepInfra OpenAI 호환 주소 |
| `UPSTREAM_API_KEY` | DeepInfra 키 (서버에만 둔다) |
| `LLM_MODEL` / `GUARD_MODEL` / `EMBED_MODEL` | 답변·판정·임베딩 모델 ID |
| `ACCESS_CODE_HASHES` | 접속 코드 해시, 쉼표로 구분 |
| `PRICE_IN_PER_M` / `PRICE_OUT_PER_M` | 100만 토큰당 단가(USD), 월 상한 계산용 |
| `MONTHLY_CAP_USD` / `RATE_PER_HOUR` / `RATE_PER_DAY` | 선택. 기본 10 / 30 / 200 |

```bash
uvicorn app.main:app_from_env --factory --reload
```

## 접속 코드 발급

```bash
python tools/new_code.py --name 홍길동
```

코드는 사용자에게(앱 `.env`의 `LLM_API_KEY`), 해시는 Render `ACCESS_CODE_HASHES`에 쉼표로 추가. 코드를 잃어버리거나 유출되면 새로 발급하고 예전 해시를 지운다.

## RAG 문서·색인

- 문서: `rag/docs/maps/`(MAPS 팀 작성), `rag/docs/open/`(공개 라이선스 요약, 출처는 `rag/docs/SOURCES.md`). 저작권 있는 교재·논문은 넣지 않는다.
- 문서마다 머리에 `title`, `source`, `license`.
- 문서를 바꾸면 색인을 다시 만들고 커밋한다(Render 빌드에서 임베딩을 부르지 않으려고):

```bash
python rag/build_index.py   # UPSTREAM_BASE_URL, UPSTREAM_API_KEY, EMBED_MODEL 필요 → rag/index.npz, rag/chunks.json
```

## 평가 (배포 기준)

```bash
python eval/run_eval.py --url http://127.0.0.1:8000 --code <접속 코드> --model-label qwen
```

공격 질문 95% 이상 거절, 정상 질문 잘못 거절 5% 이하여야 통과(종료 코드 0). 결과는 `eval/results/`(커밋 안 함). 모델이나 프롬프트를 바꿀 때마다 다시 돌린다. 한국어 품질 비교는 `--compare-upstream <주소> --compare-model <모델 ID>`.

## 배포 (Render)

1. Render에서 GitHub 레포를 연결하고 레포 루트의 `render.yaml` 블루프린트로 서비스를 만든다.
2. `sync: false` 환경변수 값을 Render 화면에서 입력한다.
3. `<서비스 주소>/health` → `{"ok": true}` 확인, 배포 주소로 평가 스크립트 실행.
4. 앱 `.env`: `LLM_BASE_URL=<서비스 주소>/v1`, `LLM_API_KEY=<접속 코드>`.

무료 단계는 한동안 안 쓰면 잠들어 첫 응답이 느리고, 재시작하면 사용량 기록(월 상한·횟수)이 초기화된다. DeepInfra 계정의 사용액 한도를 최종 안전장치로 함께 건다.

## 모델 교체

`LLM_MODEL`(필요하면 `GUARD_MODEL`, 단가 두 개)만 바꾸고 재배포한 뒤 평가를 다시 돌린다. 앱은 고칠 필요 없다. 임베딩 모델을 바꾸면 색인도 다시 만든다.

## 확인한 모델·가격

Task 9(실제 배포)에서 공식 페이지를 확인하고 날짜와 함께 적는다.

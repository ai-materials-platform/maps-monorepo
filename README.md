# MAPS — Microstructure & Alloy Prediction System

오스테나이트계 스테인리스강의 조성과 공정 조건을 입력하면 **물성을 예측**하고, 그 결과로 **3D 시편 시험과 충돌 시뮬레이션**까지 한 흐름으로 실행하는 데스크톱 분석 환경이다.

```
조성 입력 (Fe/Cr/Ni/Mo/...) + 공정 조건 (용체화 온도·시간, 시험 온도 등)
  → 상·결정구조 판정: Ni/Cr 당량 → Schaeffler 판정 → γ-FCC/α-BCC/α'-BCT 분율 (경험식 + CALPHAD)
  → 물성 예측: 항복강도 / 인장강도(UTS) / 연신율 / 단면수축률 (+ 불확실도, 학습 범위 밖 경고)
  → 응력-변형률 곡선
  → 3D 시편 시험 (강도·굽힘·늘어짐·온도) + Von Mises 시각화
  → 충돌 시뮬레이션 (판 · 로켓 동체 · 차량 정면 · 차량 부분 정면)
  → 보고서 (PDF) + 워크스페이스 저장
```

## 구성 요소

| 앱 | 역할 | 기술 |
|---|---|---|
| `apps/prediction` | 물성 예측 앱. Excel 전처리 → RF/GBM/MLP/TFP 학습 → 추론, 응력-변형률 탐색기, AI 재료 챗봇 | Python, PyQt6, scikit-learn, TensorFlow Probability, Flask |
| `apps/simulation` | 시뮬레이션 앱. 3D 시편 시험, 충돌 시뮬레이션(노드-빔 물리), 보고서 | React 19, Three.js, Electron 34, Python 표준 라이브러리 백엔드 |
| `apps/shell` | 통합 런처. 예측·시뮬레이션을 자식 프로세스로 띄우고 결과 저장소(`projects/`)를 관리 | Electron |
| `apps/gateway` | 재료 챗봇 게이트웨이. API 키 보관, 접속 코드·횟수·비용 제한, 주제/인젝션 판정, RAG | FastAPI, Render |
| `apps/shared` | 세 앱이 같이 쓰는 타이틀바·메뉴·테마(다크모드 동기화) | JS, CSS |

예측 앱과 시뮬레이션 앱은 버튼 하나로 서로 오간다(단일 인스턴스: 이미 떠 있으면 새 창 대신 앞으로 가져옴). 창을 닫으면 딸린 프로세스까지 함께 정리된다.

## 실행

```bash
# 의존성 (최초 1회)
npm run install:all
pip install -r requirements.txt   # prediction용 (TensorFlow 포함)

# 실행
npm run dev:simulation    # 시뮬레이션 단독
npm run dev:prediction    # 예측 앱 단독 (python apps/prediction/main.py)
npm run dev:shell         # 통합 런처 (둘 다 자동 기동)
```

## 검증

| 명령 | 대상 |
|---|---|
| `npm run check` | 모노레포 구조·필수 파일·JS/Python 문법 |
| `node --test apps/simulation/src/physics/` | 충돌 물리 (MAPS 곡선 재현, 파단, 시나리오) |
| `node --test apps/shared/` | 공통 메뉴·테마 동기화 |
| `python apps/simulation/backend/test_platform_input.py` | 예측 입력 기본값·학습 범위 검사 |
| `cd apps/gateway && .venv/Scripts/python -m pytest -q` | 챗봇 게이트웨이 (`requirements-dev.txt` 설치 후) |
| `npm run check:simulation` | 시뮬레이션 앱 빌드 |

## 서비스 포트

| 서비스 | 포트 | 소스 |
|---|---|---|
| Prediction Flask API | 5000 | `apps/prediction/src/api/server.py` |
| Simulation backend | 8765 | `apps/simulation/backend/simulation_server.py` |
| Simulation frontend (Vite) | 5173 | `apps/simulation/vite.config.js` |
| 챗봇 게이트웨이 | Render 배포 | `apps/gateway`, `render.yaml` |

## 예측 모델의 적용 범위

사전학습 모델은 오스테나이트계 스테인리스강 인장 데이터(2,180건, Cr 16~21 · Ni 8.4~34 wt%, 시험 온도 293~1273 K)로 학습했다.
범위 밖 조성은 숫자가 나와도 믿을 수 없으며, 시뮬레이션 앱은 이런 입력에 경고를 띄운다.
범위 안에서는 조성·공정보다 **시험 온도**의 영향이 훨씬 크다(자세한 수치는 `apps/simulation/src/physics/README.md`).

## 저장소 구조

```
apps/prediction/   # 예측 앱 (Python 코어 + Flask API)
apps/simulation/   # 시뮬레이션 앱 (React + Electron + backend), 충돌 물리는 src/physics/
apps/shell/        # 통합 런처 (Electron)
apps/gateway/      # 재료 챗봇 게이트웨이 (FastAPI)
apps/shared/       # 공통 타이틀바·메뉴·테마
docs/              # 설계 문서·구현 계획
projects/          # 실행 결과 저장소
tools/             # check / 테마 검사 등 보조 스크립트
```

## 이력

`ai-materials-discovery-platform`, `ai-materials-discovery-platform-simulation`,
`integrated-material-analysis-environment` 3개 리포지토리를 모노레포로 통합한 것이다.

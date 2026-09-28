# MAPS — Microstructure & Alloy Prediction System

합금 조성과 공정 조건을 입력하면 **물성을 예측**하고, 그 결과로 **인장 시험 3D 시뮬레이션**까지 한 흐름으로 실행하는 데스크톱 분석 환경이다.

```
조성 입력 (Fe/Cr/Ni/Mo/...) + 공정 조건 (용체화 온도·시간, 시험 온도 등)
  → 물성 예측: 항복강도 / 인장강도(UTS) / 연신율 / 단면수축률 (+ 불확실성)
  → Stress-Strain 곡선 생성
  → 3D 시편 시뮬레이션 (강도·굽힘·늘어짐·온도 시험) + Von Mises 시각화
  → 보고서 생성 (PDF) + 워크스페이스 저장
```

## 구성 요소

| 앱 | 역할 | 기술 |
|---|---|---|
| `apps/prediction` | 물성 예측 데스크톱 앱. Excel 전처리 → RF/GBM/MLP/TFP 학습 → 추론, Stress-Strain 탐색기, AI 챗봇 내장 | Python, PyQt6, scikit-learn, TensorFlow |
| `apps/simulation` | 시뮬레이션 데스크톱 앱. 조성 기반 3D 시편 렌더링, 시험모드 변형 시각화, 보고서/PDF 출력 | React 19, Three.js, Electron, Python(표준lib 백엔드) |
| `apps/shell` | 통합 런처. 예측·시뮬레이션을 자식 프로세스로 띄우고 워크플로우와 결과 저장소를 총괄 | Electron |

두 앱은 버튼 하나로 서로 오간다 (단일 인스턴스: 이미 떠 있으면 새 창 대신 앞으로 가져옴). 창을 닫으면 딸린 프로세스까지 함께 정리된다.

## 실행

```bash
# 의존성 (최초 1회)
npm run install:all
pip install -r requirements.txt   # prediction용 (TensorFlow 포함)

# 실행
npm run dev:simulation    # 시뮬레이션 단독
npm run dev:prediction    # 예측 앱 단독 (python apps/prediction/main.py)
npm run dev:shell         # 통합 런처 (둘 다 자동 기동)

# 검증
npm run check
```

## 서비스 포트

| 서비스 | 포트 | 소스 |c
|---|---|---|
| Prediction Flask API | 5000 | `apps/prediction/src/api/server.py` |
| Simulation backend | 8765 | `apps/simulation/backend/simulation_server.py` |
| Simulation frontend (Vite) | 5173 | `apps/simulation/vite.config.js` |

## 저장소 구조

```
apps/prediction/   # 예측 앱 (Python 코어)
apps/simulation/   # 시뮬레이션 앱 (React + Electron + backend)
apps/shell/        # 통합 런처 (Electron)
projects/          # 실행 결과 저장소
tools/             # check / healthcheck 보조 스크립트
```

## 이력

`ai-materials-discovery-platform`, `ai-materials-discovery-platform-simulation`,
`integrated-material-analysis-environment` 3개 리포지토리를 모노레포로 통합한 것이다.

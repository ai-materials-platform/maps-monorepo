# AI Materials Discovery Platform v2.0

> 스테인리스강(오스테나이트계)의 화학 조성과 공정 변수를 기반으로 기계적 물성을 예측하는 AI 플랫폼

---

## 개요

본 플랫폼은 재료공학 도메인 지식과 머신러닝을 결합하여, 연구자가 Excel 데이터 하나로 **전처리 → 학습 → 성능 분석 → 물성 추론**을 하나의 데스크톱 앱에서 수행할 수 있도록 설계된 시스템입니다.

### 예측 대상 물성

| 구분 | 물성 | 단위 |
|------|------|------|
| 강도 | 0.2% 항복강도 (Proof Stress) | MPa |
| 강도 | 인장강도 (UTS) | MPa |
| 연성 | 연신율 (Elongation) | % |
| 연성 | 단면 수축률 (Area Reduction) | % |

---

## 시스템 아키텍처

```
사용자
  └→ PyQt6 데스크톱 앱
       ├→ DataEngine  (전처리 / Feature Engineering)
       └→ ModelEngine (RF / GBM / MLP / TFP 앙상블)
```

- **PyQt6** 기반 네이티브 데스크톱 GUI
- Python 엔진과 직접 통신 (별도 서버 불필요)
- 학습 진행 상태를 QThread로 실시간 전달

---

## 기술 스택

### Python 백엔드

| 라이브러리 | 용도 |
|-----------|------|
| scikit-learn | RF, GBM, MLP 모델 / StandardScaler / KNNImputer |
| TensorFlow | TFP 앙상블 기반 구조 |
| TensorFlow Probability | 확률론적 예측, 불확실성 정량화 |
| pandas / NumPy | 데이터 처리, 배열 연산 |
| xlrd / openpyxl | `.xls` 및 `.xlsx` / `.xlsm` Excel 파일 파싱 |
| joblib | 모델 직렬화 (.pkl) |

### PyQt6 프론트엔드

| 기술 | 용도 |
|------|------|
| PyQt6 | 크로스플랫폼 데스크톱 GUI 프레임워크 |
| matplotlib (QTAgg) | Parity Plot, Stress-Strain Curve, 예측 그래프 |
| QThread / pyqtSignal | 학습 진행 상태 실시간 전달 |

### 패키징

| 도구 | 결과물 |
|------|--------|
| PyInstaller | 단일 실행파일 (.exe / 바이너리) |

---

## 주요 기능

### 1. 데이터 전처리

**1차 전처리 (데이터 정제)**
- 수치형 변환 및 형식 오류 처리
- 결측치 처리: 평균 / 중앙값 / KNN / 행 제거
- 도메인 기준 검증 (SSINA 오스테나이트 조성표 기반)
- 이상치 처리: IQR 기반 / 도메인 기준 / clip / 제거

**2차 전처리 (Feature Engineering)**

| 파생 변수 | 계산식 |
|----------|--------|
| `Cr_Ni_ratio` | `Cr / Ni` |
| `C_plus_N` | `C + N` |
| `Ni_eq` | `Ni + 30×C + 0.5×Mn` |
| `Cr_eq` | `Cr + Mo + 1.5×Si + 0.5×Nb` |

### 2. 피처 컬럼 선택
### 3. 피처 컬럼 선택

전처리 완료 후 학습 전에 사용할 입력 피처를 개별 선택/해제할 수 있습니다.
- 원본 변수(29개) / 파생 변수(4개) 구분하여 체크박스 목록 표시
- 선택 상태는 모델과 함께 저장되어 추론 시 자동 적용
- 최소 1개 이상 선택해야 학습 가능

### 3. 모델 학습

| 모델 | 구현 | 불확실성 산출 |
|------|------|--------------|
| Random Forest (RF) | `RandomForestRegressor` | 트리별 표준편차 |
| Gradient Boosting (GBM) | `MultiOutputRegressor(GBM)` | 휴리스틱 |
| MLP Neural Network | `MLPRegressor` + Early Stopping | 휴리스틱 |
| TFP 앙상블 | Bootstrap 5-MLP Ensemble | 앙상블 표준편차 |

- 학습 진행 상태를 QThread로 실시간 전달
- 사용자 정의 반복 횟수 및 조기 종료(Early Stopping) 지원

### 4. 성능 분석
- **Parity Plot**: 실제값 vs 예측값 분포 (대각선 기준선 포함)
- **상관관계 히트맵**: 반응형 (창 크기에 따라 수치 표시 자동 조절)
- **이중 Y축 그래프**: 단위가 다른 강도(MPa)와 연성(%) 동시 비교

### 5. 물성 추론
화학 조성 및 공정 조건 입력 → 4개 물성 + 불확실성(표준편차) 즉시 예측

### 6. Stress-Strain Curve
예측된 물성 기반으로 응력-변형률 곡선 자동 생성 및 시각화

### 7. 분석 기록
예측 결과를 워크스페이스 단위로 저장, 불러오기, 비교 가능

---

## 디렉토리 구조

```
ai-materials-discovery-platform/
├── src/
│   ├── engine/
│   │   ├── data_engine.py              # 전처리 엔진
│   │   ├── model_engine.py             # 모델 엔진
│   │   └── process_condition_engine.py # 공정 조건 예측 엔진
│   └── gui/
│       ├── main_window.py              # 메인 윈도우 진입점
│       ├── constants.py                # 상수 정의
│       ├── mixins/                     # 기능별 Mixin
│       │   ├── ui_setup_mixin.py       # UI 구성
│       │   ├── theme_mixin.py          # 테마/다크모드
│       │   ├── inference_mixin.py      # 물성 추론
│       │   ├── training_mixin.py       # 모델 학습
│       │   ├── preprocessing_mixin.py  # 전처리
│       │   ├── charts_mixin.py         # 그래프
│       │   ├── workspace_mixin.py      # 분석 기록
│       │   ├── settings_panel_mixin.py # 설정 패널
│       │   └── process_condition_mixin.py # 공정 조건
│       ├── widgets/                    # 커스텀 위젯
│       │   ├── mpl_canvas.py           # Matplotlib 캔버스
│       │   ├── prediction_guide.py     # 사용 가이드 오버레이
│       │   └── stress_strain_widget.py # Stress-Strain Curve
│       └── threads/
│           └── training_thread.py      # 학습 QThread
│
├── data/
│   ├── raw/                            # 원본 Excel 데이터
│   └── processed/                      # 전처리 결과
├── models/                             # 학습된 모델 .pkl
├── workspaces/                         # 분석 기록 저장
├── docs/
│   ├── 기술서.md
│   └── 계획서.md
├── main.py                             # 앱 실행 진입점
└── requirements.txt
```

---

## 실행 방법

```bash
# 1. Python 의존성 설치
pip install -r requirements.txt

# 2. 앱 실행
python main.py
```

---

## 데이터 형식

- **입력**: `.xls` (Excel 97-2003) 및 `.xlsx` / `.xlsm` (Excel 2007+) — 원본 조성/공정 변수 29개 포함
- **모델 저장**: `joblib` 직렬화 `.pkl` (`models/` 폴더)

---

## 참고

- 도메인 기준은 [SSINA 오스테나이트 조성표](https://www.ssina.com/education/technical-resources/composition-properties/) 기반
- 세부 기술 명세: [`docs/기술서.md`](docs/기술서.md)
- 리팩토링 및 배포 계획: [`docs/계획서.md`](docs/계획서.md)

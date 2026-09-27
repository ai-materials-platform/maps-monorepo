# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Materials Discovery Platform — predicts mechanical properties (yield stress, UTS, elongation, area reduction) of austenitic stainless steel from chemical composition and process parameters. Uses an ensemble of RF, GBM, MLP, and TFP (TensorFlow Probability) models with uncertainty quantification.

## Current State

The project is mid-refactor on branch `refactor/modular-gui-and-packaging`. The current working app is PyQt6-based; the target architecture is Electron (frontend) + Flask API (backend). See `PLAN.md` for the detailed refactoring roadmap.

## Running the App

**Current (PyQt6, working):**
```bash
pip install -r requirements.txt
python main.py
```

**Target (Electron + Flask, in progress):**
```bash
# Terminal 1 — Python backend
python python/main_api.py          # Flask on port 5001

# Terminal 2 — Electron frontend
cd electron && npm install && npm start
```

## Architecture

### Current structure
```
src/
  api/server.py          # Flask API stub (port 5000)
  engine/data_engine.py  # Preprocessing, feature engineering, scaling (526 lines)
  engine/model_engine.py # Model training and inference (RF/GBM/MLP/TFP)
  gui/main_window.py     # Monolithic PyQt6 window (being replaced)
main.py                  # PyQt6 entry point
```

### Target structure (from PLAN.md)
```
python/
  config/settings.py     # Centralized config (model paths, ports, etc.)
  main_api.py            # Flask entry point
  engine/                # Migrated from src/engine/
electron/
  main.js                # Electron main process (spawns Flask subprocess)
  renderer/              # HTML/CSS/JS tabs
```

### Data flow
Excel input → `DataEngine.load_data()` → `DataEngine.preprocess_data()` (clean, impute, engineer 4 features, scale) → **[feature selection]** → `ModelEngine.train()` → `ModelEngine.predict()` (mean + std) → Flask JSON → Electron UI

### 4 engineered features
`Cr_Ni_ratio`, `C_plus_N`, `Ni_eq` (Ni + 30C + 0.5Mn), `Cr_eq` (Cr + Mo + 1.5Si + 0.5Nb)

### Uncertainty quantification per model
- **RF**: Variance across trees
- **GBM**: Heuristic (prediction × 0.05)
- **MLP**: Heuristic + early stopping
- **TFP**: Bootstrap ensemble of 5 MLPs (real uncertainty)

### Model storage paths (target)
- macOS: `~/Library/Application Support/AIMaterialsDiscovery/`
- Windows: `%APPDATA%\AIMaterialsDiscovery\`

## Packaging (target, from PLAN.md)
```bash
# Python backend → standalone binary
pyinstaller python/main_api.py --onefile --name main_api --distpath python/dist

# macOS DMG
cd electron && npm run build:mac

# Windows EXE
cd electron && npm run build:win
```

## Planned Feature: Pre-training Feature Column Selection

### Goal
전처리 완료 후, 학습 전에 사용자가 입력 피처 컬럼을 개별적으로 선택/해제할 수 있어야 한다.

### 현재 상태 (as-is)
`DataEngine._get_selected_feature_columns()` (line 397)은 `input_feature_mode` 옵션으로만 피처 그룹을 전환한다.
- `"combined"` → raw 29개 + engineered 4개 전부
- `"clean_only"` → raw 29개만
- `"engineered_only"` → engineered 4개만

개별 컬럼 단위 선택은 없다.

### 구현 설계 (to-be)

**`DataEngine` 변경점:**
```python
# __init__에 추가
self.selected_feature_cols: list[str] | None = None  # None = 전체 사용

# 새 메서드 추가
def set_selected_features(self, cols: list[str]) -> None:
    """학습/추론에 사용할 피처 컬럼을 명시적으로 지정한다."""
    valid = [c for c in cols if c in self.feature_cols]
    self.selected_feature_cols = valid if valid else None

def get_available_feature_cols(self) -> list[str]:
    """전처리 후 실제로 df에 존재하는 피처 컬럼 목록을 반환한다."""
    if self.df is None:
        return []
    return [c for c in self.feature_cols if c in self.df.columns]

# _get_selected_feature_columns 수정
def _get_selected_feature_columns(self, df):
    if self.selected_feature_cols is not None:
        return [c for c in self.selected_feature_cols if c in df.columns]
    # 기존 mode 로직 유지 (하위 호환)
    mode = self.quality_options.get("input_feature_mode", "combined")
    ...
```

**주의:** `selected_feature_cols`가 설정된 상태에서 `get_inference_data()`도 동일한 컬럼 집합을 사용하므로, 학습 시와 추론 시 피처 순서/개수가 반드시 일치해야 한다. `DataEngine` 인스턴스(scaler 포함)를 `models/data_engine.pkl`로 저장·복원하기 때문에 `selected_feature_cols`도 자동으로 유지된다.

**Flask API 추가 엔드포인트:**
```
GET  /features/available   → 전처리 후 선택 가능한 컬럼 목록 반환
POST /features/select      → { "cols": ["Cr", "Ni", ...] } 로 선택 저장
GET  /features/selected    → 현재 선택된 컬럼 목록 반환
```

**UI 플로우 (Electron):**
1. 전처리 탭 → 전처리 실행 → 완료 후 "피처 선택" 패널 활성화
2. 체크박스 목록으로 raw/engineered 구분하여 표시, 전체선택/해제 제공
3. "학습 시작" 버튼 클릭 전까지 선택 변경 가능
4. 학습 탭으로 이동 시 선택된 컬럼 수를 요약 표시

**검증 규칙:**
- 최소 1개 이상 선택해야 학습 버튼 활성화
- engineered feature를 선택했으나 `feature_engineering=False`인 경우 경고 표시

## Excel File Support

`DataEngine.load_data()`는 `pd.read_excel()`을 사용한다. pandas는 확장자에 따라 내부 엔진을 자동 선택한다.

| 확장자 | 필요 라이브러리 | 지원 여부 |
|--------|----------------|----------|
| `.xls` | `xlrd` | ✅ (requirements.txt에 있음) |
| `.xlsx` / `.xlsm` | `openpyxl` | ✅ (추가 예정) |
| `.xlsb` | `pyxlsb` | 미지원 (재료 데이터에서 사용 안 함) |

`openpyxl`을 `requirements.txt`에 추가하면 `.xls`/`.xlsx` 모두 커버된다.
GUI 파일 다이얼로그(`main_window.py:696`)는 이미 `*.xls *.xlsx` 필터를 허용하고 있어 별도 수정 불필요.

**쓰기 기능은 현재 미구현** — 전처리 결과를 파일로 내보내는 코드(`to_excel()`)가 없음.

## Key Constraints
- Flask API uses SSE (Server-Sent Events) for real-time training progress streaming to the Electron renderer.
- `flask-cors` is required for the Electron↔Flask communication (not yet in `requirements.txt`).
- `.claude/settings.local.json` restricts Bash tool to git, pip show, and read-only operations.

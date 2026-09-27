# MAPS Monorepo

3개 리포를 하나로 합친 모노레포.

```
apps/
  prediction/   # AI Materials Discovery Platform (Python: PyQt6 + ML, Flask :5000)
  simulation/   # Discovery Platform Simulation (React19 + Three.js + Electron, backend :8765, Vite :5173)
  shell/        # MAPS 통합 런처 (Electron, prediction+simulation을 자식 프로세스로 기동)
projects/       # 실행 결과 저장소 (shell이 루트 projects/에 저장)
tools/          # check / dev 보조 스크립트
```

## 실행

```bash
# 1. 의존성
npm run install:all
pip install -r requirements.txt   # prediction용 (TF 포함, 무거움)

# 2. 개별 실행
npm run dev:prediction    # PyQt 예측 앱
npm run dev:simulation    # 시뮬레이션 (Vite+Electron)
npm run dev:shell         # 통합 런처 (예측+시뮬 자동 기동)

# 3. 검증
npm run check
```

## 포트

| 서비스 | 포트 | 소스 |
|---|---|---|
| Prediction Flask | 5000 | apps/prediction/src/api/server.py |
| Simulation backend | 8765 | apps/simulation/backend/simulation_server.py |
| Simulation Vite | 5173 | apps/simulation/vite.config.js |

## 통합 변경점 (3→1)

- `apps/shell/electron+renderer` = 구 prediction의 superset으로 단일화 (구 analysis/shell 515줄 → 808줄 버전 채택, 중복 제거)
- `apps/prediction`에서 electron/renderer/package.json 제거 → Python 코어만 남김
- shell 기본 경로를 `../prediction`, `../simulation`으로 변경 (예전엔 `../ai-materials-*` 외부 경로)
- simulation 백엔드가 `apps/prediction/models/pretrained_*.pkl`을 모노레포 안에서 찾도록 수정
- `projects/`를 루트로 단일화 (shell이 `apps/shell/projects` 대신 루트 `projects/` 사용)
- `realREADME.md` 필수 체크 버그 수정 (파일이 리포에 없음)

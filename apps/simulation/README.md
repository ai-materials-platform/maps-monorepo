# MAPS 시뮬레이션 앱

예측 물성으로 3D 시편 시험과 충돌 시뮬레이션을 보여 주고 보고서를 만드는 Electron 앱.
가운데 화면 위의 `시편 시험 | 충돌 시뮬` 버튼으로 두 보기를 오간다.

## 주요 기능

**물성 예측**
- 합금 조성 직접 입력·프리셋(STS 304 · 316 · 321), Excel/JSON 파일·외부 예측 결과 URL 불러오기
- 백엔드(`/predict`)가 사전학습 모델로 예측. 학습 범위 밖 입력·모델에 없는 원소는 예측 결과 아래에 경고
- 상 분율(Schaeffler), 결정구조(FCC/BCC/BCT), 결정 격자 뷰어

**시편 시험** (`App.jsx`)
- ASTM E8 도그본 시편 3D 렌더링, 강도·굽힘·늘어짐·온도 시험, Von Mises 색상 표시
- FEM이 아니라 버텍스 변형 기반 시각화

**충돌 시뮬** (`src/physics/`)
- 시나리오 4종: 판 찌그러짐, 로켓 동체, 차량 정면, 차량 부분 정면
- 자체 구현한 노드-빔 물리: 예측 응력-변형률 곡선을 그대로 재료 법칙으로 사용, 인장·눌림 파단, 접촉
- 두 재료 나란히 비교, 같은 합금을 다른 시험 온도로 비교, 다시 보기, 파편, 탑승 공간 감속도 그래프
- 계산은 Web Worker에서 돌아 화면이 멈추지 않는다
- 물리 모델의 가정·검증(이론식 비교)·한계는 [`src/physics/README.md`](src/physics/README.md)

**보고서**
- 보고서 생성·편집 후 PDF/CSV/JSON 내보내기 (Electron `printToPDF`)

## 실행

```bash
npm install
npm run dev      # Vite 개발 서버 + Electron
npm start        # vite build 후 dist/index.html 로드
npm run build    # 화면만 빌드 (dist/)
```

충돌 시뮬만 브라우저에서 따로 열어 볼 수 있다(개발용, 설치본에는 없음):
개발 서버를 띄우고 `http://127.0.0.1:5173/sandbox.html`.

## 테스트

```bash
node --test src/physics/                    # 충돌 물리 (모노레포 루트에서는 apps/simulation/src/physics/)
python backend/test_platform_input.py       # 예측 입력 기본값·학습 범위 검사
```

## 프로젝트 구조

```text
apps/simulation/
├─ electron/          main.cjs(창·백엔드 실행·IPC), preload.cjs(desktopApi 브리지), shared.cjs
├─ backend/           simulation_server.py(예측·시뮬 API), test_platform_input.py
├─ scripts/           dev.mjs, start.mjs
├─ sandbox.html       충돌 시뮬 단독 화면 (개발용)
└─ src/
   ├─ App.jsx         메인 화면 (예측·시편 시험·충돌 보기 전환)
   ├─ lib/physics.js  응력-변형률 곡선, Von Mises, 상 분율
   ├─ components/     ReportModal.jsx, LatticeViewer.jsx
   └─ physics/        충돌 시뮬: nodebeam.js(물리 코어), scenarios.js, crash-worker.js, CrashLab.jsx
```

## 백엔드 API (`http://127.0.0.1:8765`)

| 엔드포인트 | 내용 |
|---|---|
| `GET /health` | 상태 |
| `GET /platform/status` | 사전학습 모델 연결 상태 |
| `POST /predict` | 조성·공정 → 물성 예측. 응답에 `outOfRange`, `unknownElements` 포함 |
| `POST /platform/predict` | 사전학습 모델 원본 응답 |
| `POST /simulate` | 시편 시험 결과 |
| `POST /import-prediction` | 외부 예측 결과 URL 불러오기 |

사전학습 모델은 `apps/prediction/models/`에서 찾는다(`AI_MATERIALS_PLATFORM_DIR`로 재지정 가능).

## 주의 사항

- 사전학습 모델은 오스테나이트계 스테인리스강 데이터로 학습했다. 범위 밖 조성의 예측은 믿을 수 없다.
- 탄성계수와 밀도는 모델 예측이 아니라 백엔드 계산식으로 낸다(탄성계수는 경험식이라 스테인리스에서 실제보다 낮다).
- 시편 시험은 버텍스 변형 시각화, 충돌 시뮬은 실시간 근사 물리다. 공학 해석(FEM)을 대신하지 않는다.
- 미세조직 상 분율은 조성 기반 근사치다.

# AI Materials Discovery Platform — 리팩토링 계획서

> 브랜치: `refactor/modular-gui-and-packaging` | 작성일: 2026-03-31

---

## 1. 목표

| 목표 | 설명 |
|------|------|
| **Python 백엔드 모듈 분리** | 1,079줄 모놀리식 `main_window.py` 제거, Flask API 중심으로 재편 |
| **Electron 프론트엔드 도입** | 기존 PyQt6 GUI → Electron(HTML/CSS/JS) 기반 UI로 전환 |
| **스플래시 스크린** | 앱 실행 시 Word/Excel 수준의 로딩 창으로 완성도 향상 |
| **설정값 중앙화** | 하드코딩 상수를 `config/settings.py`로 통합 |
| **크로스플랫폼 배포** | electron-builder로 `.exe` (Windows) / `.dmg` (macOS) 생성 |

---

## 2. 전체 아키텍처 전환

### 기존 구조 (PyQt6 단일 프로세스)

```
사용자
  └→ PyQt6 GUI (main_window.py, 1,079줄)
       └→ DataEngine / ModelEngine (직접 호출)
```

### 변경 후 구조 (Electron + Flask 두 프로세스)

```
사용자
  └→ Electron (렌더러 프로세스, HTML/CSS/JS)
       └→ HTTP 요청 (localhost:5001)
            └→ Flask API Server (Python 백엔드)
                 ├→ DataEngine
                 └→ ModelEngine
```

**Electron 메인 프로세스**가 앱 실행 시 Python Flask 서버를 자식 프로세스로 기동하고,
Flask가 준비되면 스플래시를 닫고 메인 창을 표시한다.

---

## 3. 목표 디렉토리 구조

```
ai-materials-discovery-platform/
│
├── python/                           ← 기존 src/ 재편 (Python 백엔드 전용)
│   ├── main_api.py                   ← Flask 앱 진입점 (포트 5001)
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py               ← 모든 상수/경로/도메인 기준
│   ├── engine/
│   │   ├── data_engine.py            ← 변경 없음 (상수만 settings.py 참조)
│   │   └── model_engine.py           ← 변경 없음
│   └── api/
│       ├── __init__.py
│       ├── routes_preprocess.py      ← 전처리 관련 엔드포인트
│       ├── routes_train.py           ← 학습 관련 엔드포인트
│       ├── routes_performance.py     ← 성능 분석 엔드포인트
│       └── routes_inference.py       ← 추론 엔드포인트
│
├── electron/                         ← NEW: Electron 프론트엔드
│   ├── package.json
│   ├── package-lock.json
│   ├── main.js                       ← Electron 메인 프로세스
│   ├── preload.js                    ← 렌더러 ↔ 메인 브리지
│   ├── splash.html                   ← 스플래시 스크린
│   ├── splash.css                    ← 스플래시 스타일
│   ├── assets/
│   │   ├── icon.png                  ← 앱 아이콘 (공용)
│   │   ├── icon.icns                 ← macOS 전용
│   │   └── icon.ico                  ← Windows 전용
│   └── renderer/                     ← 메인 UI (웹 페이지)
│       ├── index.html                ← 메인 창 진입점
│       ├── style.css
│       └── pages/
│           ├── preprocess.js         ← 전처리 탭
│           ├── training.js           ← 학습 탭
│           ├── performance.js        ← 성능 분석 탭
│           └── inference.js          ← 물성 추론 탭
│
├── requirements.txt                  ← Python 의존성
├── requirements-dev.txt              ← 개발 전용 (pyinstaller 제거)
│
└── docs/
    ├── 기술서.md
    └── 계획서.md
```

---

## 4. 스플래시 스크린 상세 설계

### 4.1 동작 흐름

```
앱 실행 (더블클릭)
  → [1] Electron 메인 프로세스 시작
  → [2] 스플래시 창 즉시 표시  ──────────────────┐
  → [3] Python Flask 서버 subprocess로 기동       │  사용자가 보는 화면
  → [4] Flask 준비 완료 감지 (Health Check 폴링)  │  (로딩 중 표시)
  → [5] 스플래시 페이드 아웃                      │
  → [6] 메인 창 페이드 인 ──────────────────────┘
```

### 4.2 스플래시 창 스펙

```javascript
// electron/main.js
const splash = new BrowserWindow({
  width: 480,
  height: 280,
  frame: false,           // 창 테두리/버튼 없음
  transparent: true,      // OS 배경 투명
  alwaysOnTop: true,      // 항상 최상단
  resizable: false,
  center: true,
  webPreferences: { nodeIntegration: false }
})
splash.loadFile('splash.html')
```

### 4.3 스플래시 화면 레이아웃

```
┌──────────────────────────────────────────────┐
│                                              │
│         🔬  AI Materials Discovery          │
│              Platform  v2.0                  │
│                                              │
│   ┌──────────────────────────────────┐       │
│   │████████████████████░░░░░░░░░░░│  │       │
│   └──────────────────────────────────┘       │
│         Python 엔진 초기화 중...              │
│                                              │
│                             © 2026  v2.0.0  │
└──────────────────────────────────────────────┘

- 배경: 반투명 다크 (#1a1a2e, opacity 0.96) + 둥근 모서리
- 로고: 중앙 정렬, 브랜드 컬러
- 프로그레스 바: CSS 애니메이션 (실제 진행률 반영)
- 상태 텍스트: 단계별 변경 ("Flask 서버 시작 중...", "모델 준비 중..." 등)
- 페이드 인/아웃: CSS transition (opacity 0.3s)
```

### 4.4 단계별 상태 텍스트

| 단계 | 표시 텍스트 | 진행률 |
|------|------------|--------|
| Python 프로세스 시작 | `Python 엔진 초기화 중...` | 20% |
| Flask 서버 기동 대기 | `API 서버 시작 중...` | 50% |
| Health Check 통과 | `데이터 엔진 준비 중...` | 80% |
| 메인 창 로드 완료 | `완료` | 100% |

### 4.5 Python 프로세스 관리 (`main.js`)

```javascript
const { spawn } = require('child_process')
const path = require('path')

let pythonProcess = null

function startPythonBackend() {
  const pythonExe = app.isPackaged
    ? path.join(process.resourcesPath, 'python', 'main_api')  // 패키징 시
    : 'python'                                                  // 개발 시

  const scriptPath = app.isPackaged
    ? null                                                      // 패키징 시 exe 직접 실행
    : path.join(__dirname, '..', 'python', 'main_api.py')

  pythonProcess = app.isPackaged
    ? spawn(pythonExe)
    : spawn(pythonExe, [scriptPath])

  pythonProcess.stdout.on('data', (data) => console.log(`Python: ${data}`))
  pythonProcess.stderr.on('data', (data) => console.error(`Python Error: ${data}`))
}

// 앱 종료 시 Python 프로세스도 함께 종료
app.on('before-quit', () => {
  if (pythonProcess) pythonProcess.kill()
})
```

### 4.6 Flask 준비 감지 (Health Check)

```javascript
async function waitForFlask(maxRetries = 30) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const res = await fetch('http://localhost:5001/health')
      if (res.ok) return true
    } catch (e) { /* 아직 준비 안 됨 */ }
    await new Promise(r => setTimeout(r, 500))  // 0.5초 간격
  }
  throw new Error('Python 백엔드 시작 실패')
}
```

---

## 5. Python 백엔드 재편

### 5.1 Flask API 엔드포인트 확장

기존 `/predict` 하나에서 기능별 라우트로 분리:

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | 서버 상태 확인 (스플래시용) |
| `/preprocess/load` | POST | Excel 파일 로드 |
| `/preprocess/run` | POST | 전처리 실행 (품질 옵션 포함) |
| `/preprocess/preview` | GET | 전처리 결과 미리보기 (JSON) |
| `/preprocess/domain-ranges` | GET/PUT | 도메인 기준 조회/수정 |
| `/train/start` | POST | 모델 학습 시작 |
| `/train/status` | GET | 학습 진행 상태 (SSE 또는 폴링) |
| `/performance/metrics` | GET | R², MAE 등 성능 지표 |
| `/performance/parity` | GET | Parity Plot 데이터 |
| `/performance/heatmap` | GET | 상관관계 히트맵 데이터 |
| `/inference/predict` | POST | 조성 입력 → 4개 물성 예측 |

### 5.2 학습 진행 상태 실시간 전달

학습은 시간이 걸리므로 **SSE(Server-Sent Events)** 사용:

```
GET /train/status  →  text/event-stream
data: {"progress": 45, "r2": 0.87, "mae": 12.3, "log": "Epoch 900/2000"}
```

Electron 렌더러에서 `EventSource`로 수신 → 실시간 프로그레스 바 + 로그 업데이트.

### 5.3 `python/config/settings.py` — 설정값 중앙화

| 상수 | 현재 위치 | 내용 |
|------|----------|------|
| `RAW_FEATURE_COLS` | data_engine.py | 원본 입력 변수 29개 |
| `ENGINEERED_FEATURE_COLS` | data_engine.py | 파생 변수 4개 |
| `TARGET_COLS` | data_engine.py | 예측 대상 물성 4개 |
| `DEFAULT_DOMAIN_RANGES` | data_engine.py | 오스테나이트/고온 도메인 기준 |
| `MODEL_PATH` | main_window.py | OS별 user data 경로로 변경 |
| `API_PORT` | (신규) | `5001` |
| `CORS_ORIGINS` | (신규) | `["http://localhost:*"]` |

**플랫폼별 모델 저장 경로:**

```
macOS:   ~/Library/Application Support/AIMaterialsDiscovery/
Windows: %APPDATA%\AIMaterialsDiscovery\
개발:    ./models/
```

---

## 6. Electron UI 구성

### 6.1 렌더러 탭 구조

기존 PyQt6 탭 4개를 그대로 웹 페이지로 재현:

| 탭 | 파일 | 주요 연동 API |
|----|------|--------------|
| 데이터 전처리 | `renderer/pages/preprocess.js` | `/preprocess/*` |
| 모델 학습 | `renderer/pages/training.js` | `/train/*` (SSE) |
| 성능 분석 | `renderer/pages/performance.js` | `/performance/*` |
| 물성 추론 | `renderer/pages/inference.js` | `/inference/predict` |

### 6.2 Electron 기술 스택

| 항목 | 기술 | 이유 |
|------|------|------|
| 프레임워크 | Electron 30+ | 크로스플랫폼 데스크톱 |
| UI 라이브러리 | Vanilla JS + CSS (또는 Vue 3) | 의존성 최소화 |
| 차트/그래프 | Chart.js 또는 Plotly.js | Parity Plot, 히트맵 |
| API 통신 | `fetch` API | Flask REST 호출 |
| 실시간 스트림 | `EventSource` | 학습 진행 상태 SSE |
| 패키징 | electron-builder | .exe / .dmg 생성 |

### 6.3 IPC (메인 ↔ 렌더러) 통신

`preload.js`를 통해 보안 브리지만 노출:

```javascript
// preload.js
contextBridge.exposeInMainWorld('electronAPI', {
  getApiBaseUrl: () => 'http://localhost:5001',
  openFileDialog: () => ipcRenderer.invoke('open-file-dialog'),
})
```

렌더러에서는 `window.electronAPI.openFileDialog()`로 파일 선택 다이얼로그 호출.

---

## 7. 패키징 전략 (electron-builder)

### 7.1 `electron/package.json` 빌드 설정

```json
{
  "build": {
    "appId": "com.yourorg.ai-materials-discovery",
    "productName": "AI Materials Discovery",
    "directories": { "output": "../dist" },
    "files": ["**/*", "!node_modules"],
    "extraResources": [
      { "from": "../python/dist/main_api", "to": "python/main_api" }
    ],
    "mac": {
      "icon": "assets/icon.icns",
      "target": [{ "target": "dmg", "arch": ["arm64", "x64"] }]
    },
    "win": {
      "icon": "assets/icon.ico",
      "target": [{ "target": "nsis", "arch": ["x64"] }]
    }
  }
}
```

### 7.2 Python 백엔드 패키징

Electron은 JS만 번들링하므로 Python 백엔드는 **별도로 PyInstaller로 단일 실행파일**로 만들어 `extraResources`에 포함:

```bash
# Python → 단일 실행파일
pyinstaller python/main_api.py --onefile --name main_api \
  --distpath python/dist \
  --hidden-import sklearn --hidden-import tensorflow ...

# Electron → 앱 번들 (Python 실행파일 포함)
cd electron && npm run build
```

### 7.3 빌드 순서

```bash
# 1. Python 백엔드 단일 실행파일 생성
pyinstaller python/main_api.py --onefile --name main_api --distpath python/dist

# 2. macOS DMG 생성
cd electron && npm run build:mac
# → dist/AI Materials Discovery-2.0.0-arm64.dmg

# 3. Windows EXE 생성 (Windows 환경에서)
cd electron && npm run build:win
# → dist/AI Materials Discovery Setup 2.0.0.exe
```

### 7.4 예상 이슈 및 대응

| 이슈 | 원인 | 대응 |
|------|------|------|
| Python 기동 시간 (3~10초) | TF 로딩 | 스플래시 스크린으로 자연스럽게 커버 |
| CORS 오류 | Electron이 `file://`로 렌더러 로드 | Flask에 `flask-cors` 적용, `CORS_ORIGINS` 설정 |
| 포트 충돌 (5001) | 다른 프로세스 사용 중 | 포트 자동 탐색 로직 추가 |
| macOS Gatekeeper | 미서명 앱 차단 | 배포 시 Apple Developer ID 서명 필요, 테스트는 ad-hoc |
| TF `.dylib` 누락 | PyInstaller 미수집 | ImportError 추적 → `--hidden-import` 보완 |
| 앱 강제 종료 시 Python 좀비 | 프로세스 미종료 | `before-quit` 훅에서 `pythonProcess.kill()` |

---

## 8. 구현 단계 (순서 준수)

### Phase 1 — Python 백엔드 재편

| 단계 | 작업 | 파일 |
|------|------|------|
| 1 | 브랜치 확인 | `refactor/modular-gui-and-packaging` |
| 2 | config 분리 | `python/config/settings.py` 생성 |
| 3 | API 라우트 분리 | `python/api/routes_*.py` 4개 생성 |
| 4 | Flask 진입점 정비 | `python/main_api.py` (포트 5001, CORS 적용) |
| 5 | `/health` 엔드포인트 추가 | 스플래시 Health Check용 |
| 6 | SSE 학습 상태 스트림 구현 | `/train/status` |
| 7 | 모델 저장 경로 OS별 분기 | `settings.py` |

### Phase 2 — Electron 기본 구조

| 단계 | 작업 | 파일 |
|------|------|------|
| 8 | Electron 프로젝트 초기화 | `electron/package.json`, `npm init` |
| 9 | 메인 프로세스 작성 | `electron/main.js` |
| 10 | preload 브리지 작성 | `electron/preload.js` |
| 11 | 메인 창 HTML 뼈대 | `electron/renderer/index.html` |
| 12 | Flask 연동 테스트 | `fetch('http://localhost:5001/health')` 확인 |

### Phase 3 — 스플래시 스크린

| 단계 | 작업 | 파일 |
|------|------|------|
| 13 | 스플래시 HTML/CSS 작성 | `electron/splash.html`, `splash.css` |
| 14 | Python 프로세스 기동 로직 | `main.js` - `startPythonBackend()` |
| 15 | Health Check 폴링 로직 | `main.js` - `waitForFlask()` |
| 16 | 스플래시 → 메인 창 전환 | 페이드 아웃/인 트랜지션 |
| 17 | 단계별 상태 텍스트 연동 | IPC로 렌더러 → 스플래시 메시지 업데이트 |

### Phase 4 — UI 탭 구현

| 단계 | 작업 | 파일 |
|------|------|------|
| 18 | 전처리 탭 | `renderer/pages/preprocess.js` |
| 19 | 학습 탭 (SSE 연동) | `renderer/pages/training.js` |
| 20 | 성능 분석 탭 (Chart.js) | `renderer/pages/performance.js` |
| 21 | 추론 탭 | `renderer/pages/inference.js` |

### Phase 5 — 패키징

| 단계 | 작업 |
|------|------|
| 22 | PyInstaller로 `main_api` 단일 실행파일 생성 |
| 23 | electron-builder 설정 (`package.json` build 섹션) |
| 24 | macOS DMG 빌드 + ad-hoc 코드사이닝 테스트 |
| 25 | Windows EXE 빌드 테스트 |

---

## 9. 검증 체크리스트

### 개발 환경 검증

- [ ] `python python/main_api.py` 실행 → Flask 포트 5001 응답 확인
- [ ] `GET /health` → `{"status": "ok"}` 반환
- [ ] `cd electron && npm start` → 스플래시 표시 후 메인 창 전환
- [ ] 전처리 탭: 파일 업로드 → 전처리 → 미리보기 정상 표시
- [ ] 학습 탭: SSE 스트림으로 실시간 진행률 업데이트
- [ ] 성능 탭: Parity Plot, 히트맵 차트 정상 렌더링
- [ ] 추론 탭: 조성 입력 → 4개 물성 + 불확실성 정상 출력
- [ ] 앱 종료 시 Python 프로세스 함께 종료 확인

### 스플래시 검증

- [ ] 앱 실행 즉시 스플래시 표시 (0.5초 이내)
- [ ] 단계별 상태 텍스트 변경 확인
- [ ] 프로그레스 바 진행 확인
- [ ] Flask 준비 완료 후 스플래시 → 메인 창 전환 (페이드 효과)
- [ ] Python 기동 실패 시 에러 메시지 표시

### 패키징 검증

- [ ] `python/dist/main_api` 실행파일 단독 실행 확인
- [ ] macOS: `dist/*.dmg` 마운트 → 앱 실행 → 스플래시 → 메인 창
- [ ] Windows: `dist/*.exe` 설치 → 앱 실행 → 스플래시 → 메인 창
- [ ] 모델 저장 경로 OS별 user data 디렉토리 확인

---

## 10. 의존성

### Python (`requirements.txt`)

```
tensorflow
tensorflow-probability
pandas
xlrd
flask
flask-cors               ← NEW: CORS 처리
scikit-learn
numpy
joblib
```

### Python 개발용 (`requirements-dev.txt`)

```
pyinstaller>=6.3
```

### Electron (`electron/package.json`)

```json
{
  "dependencies": {
    "electron": "^30.0.0"
  },
  "devDependencies": {
    "electron-builder": "^24.0.0"
  }
}
```

### 시스템 도구

```
# macOS
brew install create-dmg   ← DMG 생성 (선택, electron-builder가 대체 가능)

# Windows
# Inno Setup 별도 설치 (NSIS 대신 사용 시)
```

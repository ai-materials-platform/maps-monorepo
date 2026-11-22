# MAPS Shell (통합 런처)

모노레포 안의 Electron 통합 런처. `apps/prediction`(PyQt/Flask)과
`apps/simulation`(Electron + 백엔드)을 자식 프로세스로 띄우고, `projects/` 결과 저장을 담당한다.
예측 화면은 PyQt 앱이 맡으므로 런처에는 예측·학습 화면이 없다(10월에 웹 예측 화면 제거).

전체 설명은 루트 `README.md` 참고.

## 실행

```bash
# 루트에서
npm run dev:shell

# 또는 여기서 직접
npm install
npm run dev        # = electron .
npm run check      # 런처 필수 파일·문법 검사
npm run build:win  # Windows 설치본 (electron-builder, dist_electron/)
```

설치본은 `dist_python/main_app`(PyInstaller로 만든 `main_app.exe`·`prediction_api.exe`·`simulation_api.exe`)과
`../simulation/dist`, `../shared`를 함께 담는다. 시뮬레이션 화면이나 백엔드를 바꿨으면 각각 다시 빌드한 뒤 설치본을 만든다.

## 경로 해결 (모노레포 기본값)

- prediction: `apps/prediction` (`AI_MATERIALS_PLATFORM_DIR`로 재지정 가능)
- simulation: `apps/simulation` (`AI_MATERIALS_SIMULATION_DIR`로 재지정 가능)
- 결과 저장: 루트 `projects/` (`.env`의 별도 지정이 없는 한)
- 포트: prediction Flask `5000` / simulation backend `8765` / Vite `5173`

## 출처

구 `ai-materials-discovery-platform`의 Electron 런처(808줄, superset)를
단일 셸로 채택하고 모노레포 경로에 맞게 수정한 것이다.
구 `integrated-material-analysis-environment`의 515줄 버전은 중복이라 제거됨.

# MAPS UI 통일 설계

- 작성일: 2026-10-25
- 상태: 사용자 검토 대기
- 범위: 셸(`apps/shell`, Electron) · PyQt 예측 앱(`apps/prediction`) · 시뮬레이션(`apps/simulation`, Electron + React)

## 1. 목표

세 앱은 이미 설치 파일 하나(MAPS.exe)로 함께 실행된다. 하지만 창마다 테두리·메뉴·색·폰트가 달라 서로 다른 프로그램처럼 보인다. 이 작업의 목표는 **세 창이 한 프로그램처럼 보이게** 하는 것이다.

성공 기준:

- 세 앱의 타이틀바 높이·색·메뉴 줄이 같다.
- 다크모드를 한 앱에서 바꾸면 나머지 두 앱도 1초 안에 따라 바뀐다.
- 자동 검사 2개(테마, 메뉴)가 통과한다.
- 설치본 빌드가 성공하고, 오프라인에서도 폰트가 같게 보인다.

결정 사항(사용자 확인 완료):

| 항목 | 결정 |
|---|---|
| 기준 스타일 | PyQt 예측 앱 |
| 타이틀바 | Electron도 자체 타이틀바, 창 버튼(─ □ ✕)은 Windows 기본(`titleBarOverlay`). PyQt 창 버튼은 Windows 아이콘 폰트로 교체 |
| 메뉴 | 세 앱 공통 4개(파일·편집·보기·도움말) + 보기 메뉴에 화면 간 이동 |
| 공유 방식 | 공통 파일을 세 앱이 같이 읽는다(`apps/shared/`) |
| 다크모드 | 1차에 세 앱의 화면 틀까지, 2차에 시뮬 3D·그래프 안쪽 |

범위 밖: 각 앱 내부 화면 구성(패널 배치, 탭 구조) 변경, 시뮬 3D 장면·컬러맵·그래프 안쪽의 다크모드(2차), Mac 대응.

## 2. 현재 차이 (조사 결과)

| 항목 | 셸 | PyQt | 시뮬 |
|---|---|---|---|
| 창 테두리 | Windows 기본 + Electron 메뉴 막대 | 테두리 없는 자체 타이틀바(30px) | Windows 기본 + Electron 메뉴 막대 |
| 상단 메뉴 | 파일·편집·보기·도움말 | 파일·편집·보기·데이터·분석·도구·도움말 (편집~도구 5개는 비어 있음) | 파일·편집·보기·도움말 |
| 폰트 | Pretendard → Segoe UI → 맑은 고딕 | 맑은 고딕 11px | IBM Plex Sans/Mono (구글 폰트, 인터넷 필요) |
| 배경 | `#f4f6f9` | `#F4F6F8` | `#f4f2ef` (베이지) |
| 포인트 색 | `#1f6feb` | `#1E293B` + 버튼 `#1D4ED8` | `#1a5fa8` |
| 다크모드 | 있음 | 있음 | 없음 |
| 로고 | MAPS 로고 | MAPS 로고 | 일반 아이콘 |
| 모서리·그림자 | 둥근 모서리, 그림자 | 6~10px, 그림자 없음 | 2px, 그림자 없음 |

## 3. 공통 파일 (`apps/shared/`)

| 파일 | 역할 | 쓰는 앱 |
|---|---|---|
| `maps-theme.css` | 디자인 값(색·폰트·크기·모서리), 라이트 `:root` + 다크 `:root[data-theme="dark"]` | 셋 다 |
| `menus.json` | 메뉴·항목·단축키·기능 ID·노출 앱 | 셋 다 |
| `titlebar.js`, `titlebar.css` | 타이틀바와 펼침 메뉴(바닐라 JS, 프레임워크 없음) | 셸, 시뮬 |

규칙: `maps-theme.css`에는 **단순한 값만** 둔다(색코드, px 숫자, 폰트 이름). Qt가 계산식·그라데이션 같은 CSS 기능을 이해하지 못하기 때문이다. 이 규칙을 파일 맨 위 주석으로 적는다.

PyQt는 `maps-theme.css`를 정규식으로 읽어 `{이름: 값}` 사전을 만든다(`--name: value;` 줄만). 없는 이름을 요청하면 기본값을 쓰고 경고를 로그에 남긴다(앱은 죽지 않는다).

## 4. 디자인 값 (PyQt 현재 값 기준)

| 이름 | 라이트 | 다크 |
|---|---|---|
| `--maps-bg` | `#F4F6F8` | `#1E1E1E` |
| `--maps-panel` | `#FFFFFF` | `#252526` |
| `--maps-panel-muted` | `#F8FAFC` | `#2D2D2D` |
| `--maps-border` | `#C9D2DC` | `#3E3E42` |
| `--maps-text` | `#111827` | `#D4D4D4` |
| `--maps-text-secondary` | `#475569` | `#CCCCCC` |
| `--maps-text-muted` | `#64748B` | `#9D9D9D` |
| `--maps-accent` | `#1E293B` | `#1E293B` |
| `--maps-primary` | `#1D4ED8` | `#1D4ED8` |
| `--maps-primary-hover` | `#2563EB` | `#2563EB` |
| `--maps-success` | `#58C472` | `#58C472` |
| `--maps-danger` | `#C42B1C` | `#C42B1C` |
| `--maps-titlebar-bg` | `#FFFFFF` | `#1E1E1E` |
| `--maps-titlebar-border` | `#C9D2DC` | `#3B4350` |
| `--maps-menu-text` | `#374151` | `#D4D4D4` |
| `--maps-menu-hover` | `#F1F5F9` | `#2D2D2D` |
| `--maps-font-sans` | `"Malgun Gothic"` | 같음 |
| `--maps-font-mono` | `Consolas` | 같음 |
| `--maps-font-size` | `11px` | 같음 |
| `--maps-font-size-title` | `15px` | 같음 |
| `--maps-radius-sm` | `6px` | 같음 |
| `--maps-radius-lg` | `10px` | 같음 |
| `--maps-titlebar-height` | `30px` | 같음 |

- 그림자는 없앤다(PyQt 기준). 셸 카드 그림자를 제거한다.
- 폰트는 Windows 기본 폰트만 쓴다. 시뮬의 구글 폰트 로드(`index.html`)를 제거한다.
- 다크 `--maps-menu-text`·`--maps-menu-hover`는 PyQt에 없던 값이라 새로 정했다. 구현 중 화면 확인 후 조정할 수 있다.

## 5. 타이틀바

모양(세 앱 공통):

```
[로고 24px] 파일  편집  보기  도움말 ········ (창 이름, 흐린 글자) ········ [─][□][✕]
└──────────────────────── 높이 30px, 아래 1px 구분선 ────────────────────────┘
```

- 메뉴 버튼: 11px 굵게, 좌우 여백 10px, 모서리 4px, 마우스를 올리면 `--maps-menu-hover`.
- 창 버튼: 각 46px. 닫기 버튼 hover는 `--maps-danger`.

Electron(셸·시뮬):

- `BrowserWindow`에 `titleBarStyle: 'hidden'`, `titleBarOverlay: { color: <titlebar-bg>, symbolColor: <menu-text>, height: 30 }`.
- 다크모드가 바뀌면 `win.setTitleBarOverlay(...)`로 창 버튼 색을 바꾼다.
- 타이틀바 빈 곳은 `-webkit-app-region: drag`, 메뉴 버튼은 `no-drag`. 오른쪽 138px(46×3)은 창 버튼 자리로 비운다.
- 기본 메뉴는 `menus.json`으로 만들되 숨긴다(`setMenuBarVisibility(false)`). 숨겨도 단축키(`Ctrl+Z` 등)가 동작한다.

PyQt:

- `CustomTitleBar`를 유지한다. 색을 공통 값에서 읽는다.
- 창 버튼 글자를 `Segoe Fluent Icons`(없으면 `Segoe MDL2 Assets`) 아이콘으로 바꾼다. 최소화 `U+E921`, 최대화 `U+E922`, 이전 크기 `U+E923`, 닫기 `U+E8BB`.

## 6. 펼침 메뉴

- 모양: `--maps-panel` 배경, 1px `--maps-border`, 모서리 6px, 안쪽 여백 4px, 항목 12px(좌 12px·우 24px), hover `--maps-menu-hover`, 구분선 1px, 비활성은 `--maps-text-muted`, 단축키는 오른쪽 정렬 흐린 글자.
- 동작: 클릭하면 열기. 열린 상태에서 다른 메뉴 버튼에 마우스를 올리면 전환. Esc와 바깥 클릭으로 닫기. 키보드 ↑↓로 이동, Enter로 실행.
- PyQt: `QMenu`에 같은 값으로 스타일시트를 적용한다.

## 7. 메뉴 구성 (`menus.json`)

항목 형식: `{ "id": "file.save", "label": "분석 기록 저장", "shortcut": "Ctrl+S", "apps": ["pyqt"] }`. 구분선은 `{ "separator": true }`.

| 메뉴 | 항목 (노출 앱) |
|---|---|
| 파일 | 분석 기록 저장 `Ctrl+S` · 불러오기 (pyqt) / 보고서 생성 · CSV 내보내기 · JSON 내보내기 · 상태 저장 · 대시보드에 저장 (sim) / 닫기 (pyqt, sim) / 종료 (shell) |
| 편집 | 실행 취소 `Ctrl+Z` · 다시 실행 `Ctrl+Y` · 잘라내기 `Ctrl+X` · 복사 `Ctrl+C` · 붙여넣기 `Ctrl+V` · 전체 선택 `Ctrl+A` (공통) |
| 보기 | 대시보드 · 물성 예측 · 시뮬레이션 (공통 이동, 현재 창은 체크 표시) / 다크모드 전환 · 전체 화면 `F11` (공통) / 개발자 도구 (Electron 개발 모드만) |
| 도움말 | 사용자 가이드 · MAPS 정보 (공통) |

- PyQt의 빈 메뉴(데이터·분석·도구)는 제거한다.
- 각 앱은 기능 ID → 처리 함수 표를 가진다. 표에 없는 ID의 항목은 비활성으로 보이고 로그를 남긴다.

이동 메뉴 처리:

| 앱 | 대시보드 | 물성 예측 | 시뮬레이션 |
|---|---|---|---|
| 셸 | 대시보드 창 표시 | 기존 `startPredictionApp` | 기존 `openSimulationWindow` |
| PyQt | `MAPS.exe --show-dashboard` (신규) | 현재 창(체크, 비활성) | `MAPS.exe --open-simulation` (기존) |
| 시뮬 | 셸 IPC로 대시보드 표시 | 셸 IPC로 PyQt 실행 | 현재 창(체크, 비활성) |

셸은 `second-instance`와 시작 인자에서 `--show-dashboard`를 처리한다(`--open-simulation`과 같은 방식). PyQt 개발 모드(셸 없이 `python main.py`)에서는 `AI_MAPS_SHELL_EXE`가 없으므로 대시보드 항목을 비활성으로 둔다. 시뮬 단독 실행(`npm run dev`, 셸 없음)에서는 기존 단독 실행 기능을 쓴다. 대시보드는 `app:close`의 셸 기동, 물성 예측은 `prediction:open`이다.

## 8. 다크모드

범위:

| 단계 | 셸 | PyQt | 시뮬 |
|---|---|---|---|
| 1차 | 공통 값 연결 | 공통 값 연결 | 화면 틀(타이틀바·메뉴·패널·버튼·글자) 새로 대응 |
| 2차 | – | – | 3D 장면 배경·응력 컬러맵·그래프 안쪽 |

세 앱 동기화:

- 설정 파일 `%APPDATA%\MAPS\theme.json` (`{"theme": "light" | "dark"}`). 위치를 고정해 개발 모드·설치본, 세 앱 모두 같은 파일을 본다.
- 다크모드 전환 = 이 파일에 쓰기. 세 앱은 파일을 지켜보다가 바뀌면 즉시 반영한다(Electron `fs.watch`, PyQt `QFileSystemWatcher`).
- 파일이 없거나 깨졌으면 라이트로 시작하고 파일을 새로 쓴다.
- 기존 각 앱의 다크모드 버튼(셸 상단 버튼, PyQt "다크 모드" 버튼)도 같은 파일에 쓰도록 바꾼다.

## 9. 앱별 변경

| | 셸 | PyQt | 시뮬 |
|---|---|---|---|
| 창 | 대시보드 창·시뮬 창 모두 자체 타이틀바 (`apps/shell/electron/main.cjs`) | 변경 없음 | 단독 실행 `apps/simulation/electron/main.cjs`도 같은 방식 |
| 색·폰트 | `renderer/styles.css`의 기존 변수를 공통 값에 연결, 그림자 제거 | `constants.py`·`theme_mixin.py`·`custom_titlebar.py`의 직접 적힌 색을 공통 값으로 | `src/styles.css` `:root`를 공통 값으로, 구글 폰트 제거, 모서리 변경, 화면 틀 인라인 색을 변수로 |
| 메뉴 | `menus.json` 기반 | `menus.json` 기반, 빈 메뉴 제거, QMenu 스타일 | `menus.json` 기반 (`shared.cjs`의 메뉴 정의 대체) |
| 유지 | 각 앱 안의 이동·다크모드 버튼(스타일만 공통 값으로) | 같음 | 같음 |

## 10. 패키징

| 앱 | 개발 모드 | 설치본 |
|---|---|---|
| 시뮬 | vite가 `apps/shared`를 번들에 포함 (`server.fs.allow`에 `../shared` 추가) | `dist`에 포함되어 추가 작업 없음 |
| 셸 | 커스텀 프로토콜 `maps-shared://` → `apps/shared` | 같은 프로토콜 → `resources/shared` (electron-builder `extraResources`에 `../shared` 추가) |
| PyQt | `apps/shared` | `maps.spec` `datas`에 `shared` 추가, `sys._MEIPASS/shared`에서 읽음 |

## 11. 검증

자동 검사:

1. `tools/check_ui_theme.py`: 세 앱 코드에서 쓰는 `--maps-*` 이름이 `maps-theme.css`에 모두 있는지, 라이트·다크가 같은 이름 집합을 정의하는지.
2. `tools/check_ui_menus.py`: `menus.json`의 기능 ID마다, `apps`에 적힌 각 앱의 처리 함수 표에 그 ID가 있는지.

화면 비교:

- 세 창을 라이트·다크로 캡처해 나란히 보여준다. Electron은 앱 내부 캡처(CDP), PyQt는 Qt `grab()`. 데스크톱 화면 캡처는 쓰지 않는다.
- 타이틀바 30px만 잘라 세 앱을 위아래로 붙여 비교한다.

동작 확인: 메뉴(클릭·전환·Esc·키보드), 단축키, 세 앱 각각에서 이동 메뉴, 다크모드 동기화(1초 이내)와 재시작 후 유지, 창 끌기·더블클릭 최대화·스냅, 설치본 오프라인 폰트.

## 12. 작업 순서

1. 공통 파일(`maps-theme.css`, `menus.json`)과 검사 스크립트 2개
2. 셸: 타이틀바·메뉴·색
3. 시뮬: 타이틀바·메뉴·색·폰트·화면 틀 다크
4. PyQt: 공통 값 읽기, 창 버튼 아이콘, 메뉴 정리·스타일
5. 다크모드 동기화(`theme.json`), `--show-dashboard`
6. 패키징 설정과 설치본 검증

각 단계 끝에 화면을 캡처해 사용자 확인을 받는다.

## 13. 위험과 대응

| 위험 | 대응 |
|---|---|
| Electron 기본 메뉴를 숨기면 단축키가 사라짐 | 숨긴 기본 메뉴를 `menus.json`으로 유지(5절) |
| HTML 메뉴의 키보드·접근성 누락 | ↑↓·Enter·Esc 지원을 완료 기준에 포함 |
| 공통 값 이름 변경 시 조용히 기본색으로 바뀜 | 테마 검사 스크립트 |
| Win10에 Segoe Fluent Icons 없음 | `Segoe MDL2 Assets`로 대체(같은 코드포인트) |
| 시뮬 화면 틀의 인라인 색 누락 | 3단계에서 `App.jsx` 인라인 색을 검색해 틀 영역은 변수로 교체, 나머지는 2차 다크모드 목록에 기록 |
| `fs.watch` 중복 이벤트 | 값이 실제로 바뀐 경우에만 반영 |

# MAPS UI 통일 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 셸·PyQt·시뮬 세 창이 같은 타이틀바·메뉴·색·폰트·다크모드를 갖게 해서 한 프로그램처럼 보이게 한다.

**Architecture:** `apps/shared/`에 디자인 값(`maps-theme.css`)과 메뉴 정의(`menus.json`)를 두고 세 앱이 같이 읽는다. Electron 두 앱은 공통 HTML 타이틀바(`titlebar.js`)와 Windows 기본 창 버튼(`titleBarOverlay`)을 쓰고, PyQt는 기존 `CustomTitleBar`에 같은 값을 적용한다. 다크모드는 `%APPDATA%\MAPS\theme.json` 한 파일을 세 앱이 지켜보며 동기화한다.

**Tech Stack:** Electron 34(CJS main, ESM renderer 모듈), 바닐라 JS, React 18 + Vite 6(시뮬), PyQt6, Python 3.12 표준 라이브러리, `node:test`(추가 의존성 없음).

**Spec:** `docs/superpowers/specs/2026-10-25-ui-unification-design.md`

## Global Constraints

- 기준 스타일은 PyQt 예측 앱. 디자인 값은 스펙 4절 표의 값을 그대로 쓴다(이름 `--maps-*`).
- `maps-theme.css`에는 단순한 값만(색코드, px 숫자, 폰트 이름). 계산식·그라데이션 금지. 파일 맨 위 주석으로 이 규칙을 적는다.
- 폰트는 Windows 기본만: `"Malgun Gothic"`, 숫자 `Consolas`. 구글 폰트 로드 금지.
- 타이틀바 높이 30px, 로고 24px, 메뉴 버튼 11px 굵게, 창 버튼 46px. 그림자 없음.
- 메뉴는 세 앱 공통 4개: 파일·편집·보기·도움말. 빈 메뉴를 만들지 않는다.
- 다크모드 설정 파일: `%APPDATA%\MAPS\theme.json`, 내용 `{"theme": "light"}` 또는 `{"theme": "dark"}`.
- 다크모드 1차 범위: 화면 틀(타이틀바·메뉴·패널·버튼·글자)만. 시뮬 3D 장면·응력 컬러맵·그래프 안쪽은 건드리지 않는다.
- 새 npm/pip 의존성 추가 금지.
- 각 앱 안의 기존 이동·다크모드 버튼과 내부 화면 구성은 유지한다(스타일만 공통 값으로).
- 커밋 메시지·PR에 도구 표기를 넣지 않는다.

## Review Focus

1. `theme.json`이 없거나 깨진 JSON이거나 `"theme"` 값이 이상할 때 → 라이트로 시작하고 올바른 파일을 다시 쓴다(앱이 죽지 않음). Task 2 테스트.
2. `fs.watch`가 한 번 쓰기에 이벤트를 여러 번 보내거나 같은 값을 다시 쓸 때 → 콜백은 값이 실제로 바뀐 경우에만 1번 호출(깜빡임·무한 루프 없음). Task 2 테스트.
3. Win10처럼 `Segoe Fluent Icons`가 없는 PC → `Segoe MDL2 Assets`로 대체되어 창 버튼이 네모(□ 깨짐)로 보이지 않음. Task 6 테스트.
4. 메뉴가 열린 상태에서 창이 포커스를 잃거나(다른 창 클릭) 메뉴 항목을 실행할 때 → 메뉴가 닫힘. Task 3 테스트.
5. `menus.json`에 처리 함수가 없는 ID가 들어오면 → 그 항목만 비활성으로 보이고 나머지 메뉴는 정상. Task 3 테스트 + Task 1 메뉴 검사.

---

## File Structure

| 파일 | 상태 | 책임 |
|---|---|---|
| `apps/shared/maps-theme.css` | 신규 | 디자인 값(라이트 `:root`, 다크 `:root[data-theme="dark"]`) |
| `apps/shared/menus.json` | 신규 | 메뉴·항목·단축키·기능 ID·노출 앱 |
| `apps/shared/menu-model.js` | 신규 | 메뉴 정의를 앱별로 거르고 키보드 이동 계산(순수 함수, ESM) |
| `apps/shared/titlebar.js`, `titlebar.css` | 신규 | Electron용 타이틀바·펼침 메뉴 DOM(ESM) |
| `apps/shared/theme-sync.cjs` | 신규 | `theme.json` 읽기·쓰기·감시(Electron main) |
| `apps/shared/window-chrome.cjs` | 신규 | `BrowserWindow` 타이틀바 옵션, 숨긴 기본 메뉴, 역할 ID 처리(Electron main) |
| `apps/shared/*.test.mjs` | 신규 | `node --test` 테스트 |
| `tools/check_ui_theme.py`, `tools/check_ui_menus.py` | 신규 | 자동 검사 2개 |
| `apps/prediction/src/gui/theme_tokens.py` | 신규 | PyQt에서 `maps-theme.css` 읽기, 공통 폴더 경로 |
| `apps/prediction/src/gui/theme_sync.py` | 신규 | PyQt에서 `theme.json` 읽기·쓰기·감시 |
| `apps/prediction/src/gui/test_theme_tokens.py`, `test_theme_sync.py`, `test_titlebar_glyphs.py` | 신규 | PyQt 쪽 테스트(실행형 스크립트, 기존 테스트 방식) |
| `apps/shell/electron/main.cjs`, `preload.cjs`, `renderer/index.html`, `renderer/app.js`, `renderer/styles.css`, `package.json` | 수정 | 셸 적용 |
| `apps/simulation/electron/shared.cjs`, `main.cjs`, `preload.cjs`, `src/App.jsx`, `src/styles.css`, `index.html`, `vite.config.js` | 수정 | 시뮬 적용 |
| `apps/prediction/src/gui/constants.py`, `mixins/theme_mixin.py`, `mixins/ui_setup_mixin.py`, `widgets/custom_titlebar.py`, `main_window.py` | 수정 | PyQt 적용 |
| `apps/prediction/scripts/maps.spec` | 수정 | 번들에 `shared/` 포함 |

## Menu IDs (menus.json이 정의하고 모든 Task가 공유)

| ID | 라벨 | 단축키 | apps | 처리 위치 |
|---|---|---|---|---|
| `file.workspace.save` | 분석 기록 저장 | Ctrl+S | pyqt | PyQt |
| `file.workspace.open` | 분석 기록 불러오기 | – | pyqt | PyQt |
| `file.report` | 보고서 생성 | – | sim | 시뮬 렌더러 |
| `file.export.csv` | CSV 내보내기 | – | sim | 시뮬 렌더러 |
| `file.export.json` | JSON 내보내기 | – | sim | 시뮬 렌더러 |
| `file.state.save` | 상태 저장 | – | sim | 시뮬 렌더러 |
| `file.dashboard.save` | 대시보드에 저장 | – | sim | 시뮬 렌더러 |
| `file.close` | 닫기 | – | pyqt, sim | 역할(main) / PyQt |
| `file.quit` | 종료 | – | shell | 역할(main) |
| `edit.undo` `edit.redo` `edit.cut` `edit.copy` `edit.paste` `edit.selectAll` | 실행 취소·다시 실행·잘라내기·복사·붙여넣기·전체 선택 | Ctrl+Z·Ctrl+Y·Ctrl+X·Ctrl+C·Ctrl+V·Ctrl+A | shell, pyqt, sim | 역할(main) / PyQt(포커스 위젯) |
| `view.nav.dashboard` | 대시보드 | – | shell, pyqt, sim | 각 앱 |
| `view.nav.prediction` | 물성 예측 | – | shell, pyqt, sim | 각 앱 |
| `view.nav.simulation` | 시뮬레이션 | – | shell, pyqt, sim | 각 앱 |
| `view.theme.toggle` | 다크모드 전환 | – | shell, pyqt, sim | 각 앱(→ theme.json) |
| `view.fullscreen` | 전체 화면 | F11 | shell, pyqt, sim | 역할(main) / PyQt |
| `view.devtools` | 개발자 도구 | – | shell, sim (`devOnly`) | 역할(main) |
| `help.guide` | 사용자 가이드 | – | pyqt | PyQt |
| `help.about` | MAPS 정보 | – | shell, pyqt, sim | 역할(main) / PyQt |

메뉴 순서는 파일·편집·보기·도움말. 보기 메뉴는 이동 3개 → 구분선 → 다크모드·전체 화면 → (개발 모드) 개발자 도구. 파일 메뉴의 `file.close`/`file.quit` 앞에 구분선.

---

### Task 1: 공통 디자인 값·메뉴 정의와 자동 검사

**Files:**
- Create: `apps/shared/maps-theme.css`, `apps/shared/menus.json`
- Create: `apps/prediction/src/gui/theme_tokens.py`, `apps/prediction/src/gui/test_theme_tokens.py`
- Create: `tools/check_ui_theme.py`, `tools/check_ui_menus.py`

**Interfaces:**
- Produces: `maps-theme.css`의 `--maps-*` 23개(스펙 4절). `menus.json` 형식 `{"menus":[{"id":"file","label":"파일","items":[{"id","label","shortcut"?,"apps":[...],"devOnly"?}|{"separator":true}]}]}`.
- Produces (Python): `shared_dir() -> pathlib.Path` (개발: `apps/shared`, 번들: `sys._MEIPASS/shared`), `load_tokens(path: pathlib.Path | None = None) -> dict[str, dict[str, str]]` (키 `"light"`/`"dark"`, 값 사전의 키는 `--` 없이 `maps-bg` 형태, 다크에 없는 키는 라이트 값으로 채움), `token(name: str, dark: bool) -> str` (없는 이름이면 `"#FF00FF"`를 돌려주고 `logging.warning`).
- Produces (검사): `check_ui_menus.py`는 앱별 처리 ID를 정규식 `MENU_HANDLERS\s*=\s*\{(.*?)\}` 블록 안의 `'id'`/`"id"` 키에서 읽고, 역할 ID는 `apps/shared/window-chrome.cjs`의 `ROLE_IDS` 배열에서 읽는다(Task 4·5·6이 이 이름으로 만든다).

- [ ] **Step 1: 실패하는 테스트 작성** — `test_theme_tokens.py`

```python
def test_light_and_dark_values_from_spec():
    t = load_tokens()
    assert t["light"]["maps-bg"] == "#F4F6F8"
    assert t["dark"]["maps-bg"] == "#1E1E1E"
    assert t["light"]["maps-titlebar-height"] == "30px"
    assert t["dark"]["maps-font-sans"] == '"Malgun Gothic"'  # 다크에 없는 키는 라이트에서 채움

def test_unknown_token_does_not_crash():
    assert token("maps-does-not-exist", dark=False) == "#FF00FF"

def test_simple_values_only():
    for theme in load_tokens().values():
        for v in theme.values():
            assert not any(bad in v for bad in ("calc(", "var(", "gradient")), v
```

- [ ] **Step 2: 실행해서 실패 확인** — `python apps/prediction/src/gui/test_theme_tokens.py` → `ModuleNotFoundError: theme_tokens`

- [ ] **Step 3: `maps-theme.css`(스펙 4절 값, 맨 위 규칙 주석), `menus.json`(위 Menu IDs 표 그대로), `theme_tokens.py` 구현** — 파싱은 `re.findall(r"--([\w-]+)\s*:\s*([^;]+);")`를 `:root {…}`와 `:root[data-theme="dark"] {…}` 블록별로 적용.

- [ ] **Step 4: 테스트 통과 확인** — 같은 명령 → `ok`

- [ ] **Step 5: 검사 스크립트 2개 작성** — `check_ui_theme.py`: (a) 라이트·다크 이름 집합이 같거나 다크가 라이트의 부분집합인지, (b) `apps/shell`, `apps/simulation/src`, `apps/prediction/src`에서 쓰인 `--maps-[\w-]+`(또는 `token("maps-…")`)가 전부 정의돼 있는지. `check_ui_menus.py`: 각 항목의 `apps`마다 그 앱 처리 표 또는 `ROLE_IDS`에 ID가 있는지. 없으면 목록을 출력하고 종료 코드 1.

- [ ] **Step 6: 검사 실행** — `python tools/check_ui_theme.py` → `ok`. `python tools/check_ui_menus.py` → 아직 처리 표가 없으므로 실패 목록 출력(정상, Task 4~6에서 통과로 바뀜)

- [ ] **Step 7: 커밋** — `git commit -m "feat(shared): 공통 디자인 값·메뉴 정의와 UI 검사 스크립트"`

---

### Task 2: 다크모드 동기화 모듈 (Electron·PyQt 공용 규약)

**Files:**
- Create: `apps/shared/theme-sync.cjs`, `apps/shared/theme-sync.test.mjs`
- Create: `apps/prediction/src/gui/theme_sync.py`, `apps/prediction/src/gui/test_theme_sync.py`

**Interfaces:**
- Produces (JS): `themeFile(): string` (`path.join(process.env.APPDATA, 'MAPS', 'theme.json')`, 테스트용으로 `MAPS_THEME_FILE` 환경변수가 있으면 그 경로), `readTheme(file = themeFile()): 'light'|'dark'`, `writeTheme(theme: 'light'|'dark', file = themeFile()): void` (폴더 생성 포함), `watchTheme(cb: (theme) => void, file = themeFile()): () => void` (부모 폴더를 `fs.watch`, 100ms 디바운스, 마지막 값과 다를 때만 `cb`).
- Produces (Python): `theme_file() -> pathlib.Path`, `read_theme(path=None) -> str`, `write_theme(theme: str, path=None) -> None`, `ThemeWatcher(QObject)` with signal `changed(str)` (`QFileSystemWatcher`로 파일과 부모 폴더를 감시, 값이 바뀔 때만 emit).

- [ ] **Step 1: 실패하는 테스트 작성** — `theme-sync.test.mjs` (임시 폴더 사용)

```js
test('missing or broken file reads as light and is rewritten', () => {
  assert.equal(readTheme(tmp('none.json')), 'light');
  fs.writeFileSync(f, '{not json'); assert.equal(readTheme(f), 'light');
  assert.deepEqual(JSON.parse(fs.readFileSync(f, 'utf8')), { theme: 'light' });
  fs.writeFileSync(f, '{"theme":"purple"}'); assert.equal(readTheme(f), 'light');
});
test('watch fires once per real change only', async () => {
  const seen = []; const stop = watchTheme(t => seen.push(t), f);
  writeTheme('dark', f); writeTheme('dark', f); await sleep(400);
  writeTheme('light', f); await sleep(400); stop();
  assert.deepEqual(seen, ['dark', 'light']);
});
```

`test_theme_sync.py`도 같은 두 시나리오(깨진 파일 → light + 재작성, `ThemeWatcher.changed`가 dark·light 각 1번)를 `QCoreApplication` 이벤트 루프로 검사.

- [ ] **Step 2: 실패 확인** — `node --test apps/shared/theme-sync.test.mjs`, `python apps/prediction/src/gui/test_theme_sync.py` → 모듈 없음

- [ ] **Step 3: 두 모듈 구현** — 읽기 실패·잘못된 값이면 `writeTheme('light')` 후 `'light'` 반환.

- [ ] **Step 4: 통과 확인** — 같은 명령 둘 다 통과

- [ ] **Step 5: 커밋** — `git commit -m "feat(shared): theme.json 다크모드 동기화 모듈"`

---

### Task 3: 공통 타이틀바와 펼침 메뉴 (Electron용)

**Files:**
- Create: `apps/shared/menu-model.js`, `apps/shared/menu-model.test.mjs`
- Create: `apps/shared/titlebar.js`, `apps/shared/titlebar.css`

**Interfaces:**
- Consumes: `menus.json`(Task 1), `--maps-*` 변수(Task 1).
- Produces (`menu-model.js`, ESM 순수 함수): `menusFor(spec, app: 'shell'|'pyqt'|'sim', { dev = false, handled = () => true } = {}) -> Array<{id,label,items:Array<{id,label,shortcut?,enabled}|{separator:true}>}>` — 다른 앱 항목·`devOnly`(dev=false일 때) 제거, 맨 앞·맨 뒤·연속 구분선 정리, 항목이 0개인 메뉴 제거, `enabled = handled(id)`. `nextIndex(items, current: number, delta: 1|-1) -> number` — 구분선·비활성 건너뛰고 순환.
- Produces (`titlebar.js`): `mountTitlebar(host: HTMLElement, { app, spec, title, dev, handled, onAction: (id) => void, checkedId?: string }) -> { setTitle(text), destroy() }`. DOM: `.maps-titlebar > img.maps-logo + .maps-menubar > button.maps-menu-btn*` + `.maps-title` + `.maps-overlay-gap`(138px). 펼침 목록 `.maps-menu-pop`.
- 동작(스펙 6절): 클릭 열기, 열린 동안 다른 버튼 `mouseenter`로 전환, Esc·바깥 `mousedown`·`window` `blur`·항목 실행 시 닫기, ↑↓ `nextIndex`, Enter 실행. 비활성 항목은 클릭 무시.

- [ ] **Step 1: 실패하는 테스트 작성** — `menu-model.test.mjs`

```js
test('filters by app and drops empty menus', () => {
  const m = menusFor(spec, 'shell');
  assert.deepEqual(m.map(x => x.id), ['file','edit','view','help']);
  assert.ok(!flat(m).some(i => i.id === 'file.report'));      // sim 전용
  assert.ok(!flat(m).some(i => i.id === 'view.devtools'));    // devOnly, dev=false
});
test('no leading, trailing or double separators', () => { /* 각 메뉴 items 검사 */ });
test('unhandled id is shown disabled, others enabled', () => {
  const m = menusFor(spec, 'sim', { handled: id => id !== 'file.report' });
  assert.equal(find(m, 'file.report').enabled, false);
  assert.equal(find(m, 'file.export.csv').enabled, true);
});
test('nextIndex skips separators and disabled, wraps', () => { /* [a, sep, b(disabled), c] 0→3, 3→0 */ });
```

- [ ] **Step 2: 실패 확인** — `node --test apps/shared/menu-model.test.mjs` → 모듈 없음

- [ ] **Step 3: `menu-model.js` 구현 → 테스트 통과 확인**

- [ ] **Step 4: `titlebar.js`·`titlebar.css` 구현** — 색·크기는 전부 `var(--maps-*)`. 드래그는 `.maps-titlebar { -webkit-app-region: drag }`, 버튼·팝업은 `no-drag`. 로고는 셸 `index.html`의 MAPS SVG를 `data:` URI로 내장.

- [ ] **Step 5: 브라우저 확인(포커스 잃음 포함)** — `apps/shared/titlebar-demo.html`(커밋하지 않는 임시 파일)에서 `mountTitlebar` 후 브라우저 패널로: 메뉴 열기 → 다른 버튼 hover 전환 → Esc 닫힘 → 다시 열고 `window.dispatchEvent(new Event('blur'))` → 닫힘 → ↓↓Enter로 `onAction` 호출 ID 확인. 라이트/다크(`data-theme`) 캡처.

- [ ] **Step 6: 커밋** — `git commit -m "feat(shared): 공통 타이틀바·펼침 메뉴 컴포넌트"`

---

### Task 4: 셸 적용

**Files:**
- Create: `apps/shared/window-chrome.cjs`
- Modify: `apps/shell/electron/main.cjs` (`createWindow` 972행 부근, `openSimulationWindow`의 `new BrowserWindow`, `second-instance` 1011행 부근, 시작 인자 997행 부근, 앱 메뉴 `setupAppMenu`)
- Modify: `apps/shell/electron/preload.cjs`, `apps/shell/renderer/index.html`, `apps/shell/renderer/app.js`(테마 600행 부근, 메뉴 액션 614행 부근), `apps/shell/renderer/styles.css`(변수 1~23행)

**Interfaces:**
- Consumes: Task 1 파일, Task 2 `theme-sync.cjs`, Task 3 `titlebar.js`.
- Produces (`window-chrome.cjs`): `ROLE_IDS = ['file.close','file.quit','edit.undo','edit.redo','edit.cut','edit.copy','edit.paste','edit.selectAll','view.fullscreen','view.devtools','help.about']`, `chromeOptions(theme: 'light'|'dark') -> { titleBarStyle: 'hidden', titleBarOverlay: { color, symbolColor, height: 30 } }`(색은 `maps-theme.css`에서 읽음), `applyOverlay(win, theme)`, `async installHiddenMenu(win, app: 'shell'|'sim', onAppAction: (id) => void)`(`menu-model.js`를 동적 `import()`로 불러 기본 메뉴를 만들고 `win.setMenu(menu)`, `win.setMenuBarVisibility(false)`; 역할 ID는 `role`로, 나머지는 `onAppAction`), `runRole(win, id)`, `registerMenuIpc()`(채널 `menu:invoke` → 역할이면 `runRole`, 아니면 렌더러로 `menu-action` 전송), `registerSharedProtocol(sharedDir)`(`maps-shared://` → 파일).
- Produces (preload, 셸·시뮬 공통 이름): `mapsUi.invoke(id)`, `mapsUi.onAction(cb) -> unsubscribe`, `mapsUi.getTheme() -> Promise<string>`, `mapsUi.setTheme(theme)`, `mapsUi.onTheme(cb) -> unsubscribe`, `mapsUi.isDev`.
- Produces (셸 렌더러): `MENU_HANDLERS = { 'view.nav.dashboard', 'view.nav.prediction', 'view.nav.simulation', 'view.theme.toggle' }` 객체 리터럴(값은 기존 `switchPage('home')`, `openPredictionPlatform()`, `openSimulationPlatform()`, 테마 토글).
- Produces (셸 main): 시작 인자·`second-instance`에서 `--show-dashboard` → 대시보드 창 `show()`·`focus()`(+ 시뮬 창이 있으면 그대로 둠).

- [ ] **Step 1: `window-chrome.cjs`의 메뉴 생성 테스트 작성** — `window-chrome.test.mjs`: Electron 없이 테스트 가능한 순수 부분 `menuTemplate(models, onAppAction)`(→ `{label, submenu:[{label, accelerator, role?|click}]}`)을 내보내고, `edit.copy`가 `role: 'copy'`·`accelerator: 'Ctrl+C'`, `view.nav.dashboard`가 `click`인지 검사.
- [ ] **Step 2: 실패 확인 → 구현 → 통과 확인** — `node --test apps/shared/window-chrome.test.mjs`
- [ ] **Step 3: 셸 main 적용** — 두 창 생성에 `...chromeOptions(readTheme())`, `installHiddenMenu`, 기존 `setupAppMenu`·`Menu.setApplicationMenu` 제거, `registerMenuIpc`, `registerSharedProtocol`(개발 `apps/shared`, 설치본 `process.resourcesPath/shared`), `watchTheme` → 모든 창에 `applyOverlay` + `mapsUi` 테마 이벤트, `--show-dashboard` 처리.
- [ ] **Step 4: 셸 렌더러 적용** — `index.html` 맨 위 `<div id="maps-titlebar">` + `maps-shared://maps-theme.css`·`titlebar.css`, `<script type="module">`로 `mountTitlebar`. `styles.css`의 `--page-bg`/`--panel`/`--line`/`--text`/`--muted`/`--blue`를 `var(--maps-…)`로 연결(`--blue` → `--maps-primary`), `--shadow: none`, 폰트 `var(--maps-font-sans)`. 테마 토글은 `localStorage` 대신 `mapsUi.setTheme`, 반영은 `mapsUi.onTheme`.
- [ ] **Step 5: 검사·캡처** — `python tools/check_ui_menus.py`의 shell 항목 통과. CDP로 대시보드 라이트/다크 캡처, 메뉴 펼침 캡처. 단축키 `Ctrl+Z`가 검색창에서 동작하는지 CDP `Input.dispatchKeyEvent`로 확인.
- [ ] **Step 6: 사용자 확인 후 커밋** — 캡처를 보여주고 승인 → `git commit -m "feat(shell): 공통 타이틀바·메뉴·테마 적용"`

---

### Task 5: 시뮬 적용

**Files:**
- Modify: `apps/simulation/electron/shared.cjs`(`buildSimMenu` 제거 → `window-chrome.cjs` 사용), `apps/simulation/electron/main.cjs`, `apps/simulation/electron/preload.cjs`
- Modify: `apps/simulation/src/App.jsx`(`onMenuAction` 처리부, 상단 `top-bar` 인라인 색), `apps/simulation/src/styles.css`(`:root` 1~16행, `border-radius: 2px` 들), `apps/simulation/index.html`(구글 폰트 7~9행 삭제), `apps/simulation/vite.config.js`(`server.fs.allow: ['..', '../shared']`)

**Interfaces:**
- Consumes: Task 1·2·3, Task 4의 `window-chrome.cjs`와 `mapsUi` preload 이름.
- Produces: `App.jsx`의 `MENU_HANDLERS = { 'file.report', 'file.export.csv', 'file.export.json', 'file.state.save', 'file.dashboard.save', 'view.nav.dashboard', 'view.nav.prediction', 'view.theme.toggle' }` (`view.nav.simulation`은 현재 창 → `checkedId`). 이동: 셸이 띄운 창은 `mapsUi.invoke`로 셸에, 단독 실행은 기존 `desktopApi.close()`(대시보드)·`desktopApi.openPrediction()`.
- 다크 1차: `:root[data-theme="dark"]`에서 시뮬 변수(`--bg`, `--panel`, `--panel-secondary`, `--text`, `--text-muted`, `--line`)를 `--maps-*`에 연결. 화면 틀의 인라인 색(`top-bar` 버튼 등)만 변수로 교체. 3D·컬러맵·차트 안쪽 인라인 색은 `docs/superpowers/plans/dark-mode-phase2.md`(신규, 목록만)에 파일:행으로 기록.

- [ ] **Step 1: 실패 확인** — `python tools/check_ui_menus.py` → sim 항목 실패 목록
- [ ] **Step 2: 메뉴·창 적용** — 셸이 띄운 시뮬 창(`openSimulationWindow`)과 단독 실행 창 모두 `chromeOptions` + `installHiddenMenu(win,'sim',…)`, `mountTitlebar`는 `main.jsx`에서 `#root` 위에 별도 `#maps-titlebar`로 마운트(React 트리 밖). 기존 `menu-action` 액션 이름(`report:open` 등)은 새 ID로 교체.
- [ ] **Step 3: 테마·폰트·모서리** — `styles.css` `:root` 변수를 `--maps-*`로 연결, `--sans: var(--maps-font-sans)`, `--mono: var(--maps-font-mono)`, `2px` 모서리 → 버튼·입력 `var(--maps-radius-sm)`, 패널 `var(--maps-radius-lg)`. 구글 폰트 제거.
- [ ] **Step 4: 검사·빌드·캡처** — `python tools/check_ui_menus.py` sim 통과, `npx vite build` 통과, 셸에서 시뮬 창 열어 라이트/다크 캡처(3D 영역은 원래 색인 것이 정상). 오프라인 확인: `index.html`에 외부 URL이 없는지 `grep -c "googleapis" apps/simulation/index.html` → `0`.
- [ ] **Step 5: 사용자 확인 후 커밋** — `git commit -m "feat(sim): 공통 타이틀바·메뉴·테마, 화면 틀 다크모드"`

---

### Task 6: PyQt 적용

**Files:**
- Modify: `apps/prediction/src/gui/constants.py`(`LIGHT_QSS`/`DARK_QSS`를 토큰으로 생성하는 `build_qss(dark: bool) -> str`), `mixins/theme_mixin.py`(`_theme()`, `_apply_theme_colors`, `_toggle_theme`), `widgets/custom_titlebar.py`, `mixins/ui_setup_mixin.py`(메뉴 구성 204~222행, 다크 버튼 402행), `main_window.py`(`_dark_mode` 초기값 73행)
- Create: `apps/prediction/src/gui/test_titlebar_glyphs.py`

**Interfaces:**
- Consumes: Task 1 `theme_tokens.token`, Task 2 `theme_sync`, `menus.json`.
- Produces (`theme_tokens.py`에 추가): `load_menu_spec(path: pathlib.Path | None = None) -> dict` (`shared_dir()/menus.json`), `menus_for(spec: dict, app: str = 'pyqt', handled=lambda _id: True) -> list[dict]` (Task 3 `menusFor`와 같은 규칙: 다른 앱·`devOnly` 제거, 구분선 정리, 빈 메뉴 제거, `enabled`).
- Produces: `ui_setup_mixin.py`의 `MENU_HANDLERS = {'file.workspace.save': ..., 'file.workspace.open': ..., 'file.close': ..., 'edit.undo': ..., 'edit.redo': ..., 'edit.cut': ..., 'edit.copy': ..., 'edit.paste': ..., 'edit.selectAll': ..., 'view.nav.dashboard': ..., 'view.nav.simulation': ..., 'view.theme.toggle': ..., 'view.fullscreen': ..., 'help.guide': ..., 'help.about': ...}` (편집은 `QApplication.focusWidget()`의 `undo/redo/cut/copy/paste/selectAll`이 있으면 호출; 대시보드는 `AI_MAPS_SHELL_EXE`가 있으면 `subprocess.Popen([exe, '--show-dashboard'])` + `showMinimized()`, 없으면 비활성; 시뮬레이션은 기존 `_open_simulation_app`; `view.nav.prediction`은 현재 창 체크).
- Produces (`custom_titlebar.py`): `window_glyph_font() -> QFont` (`Segoe Fluent Icons`가 `QFontDatabase.families()`에 없으면 `Segoe MDL2 Assets`), 버튼 글자 `"\uE921"`(최소화), `"\uE922"`/`"\uE923"`(최대화/이전 크기, 상태에 따라), `"\uE8BB"`(닫기). 색은 토큰.
- 다크모드: 시작 시 `read_theme()`로 `_dark_mode` 결정, `ThemeWatcher.changed` → 테마 적용(토글 버튼 글자 포함). `_toggle_theme`은 `write_theme`만 하고 실제 적용은 감시 콜백에서(세 앱 같은 경로).
- QMenu 스타일: 스펙 6절 값으로 `QMenu{background:…;border:1px solid …;border-radius:6px;padding:4px} QMenu::item{padding:6px 24px 6px 12px} QMenu::item:selected{background:<menu-hover>} QMenu::separator{height:1px;background:<border>;margin:4px 0} QMenu::item:disabled{color:<text-muted>}`.

- [ ] **Step 1: 실패하는 테스트 작성** — `test_titlebar_glyphs.py`

```python
def test_glyph_font_falls_back_when_fluent_missing():
    fams = ["Segoe MDL2 Assets", "Malgun Gothic"]
    assert pick_glyph_family(fams) == "Segoe MDL2 Assets"
    assert pick_glyph_family(["Segoe Fluent Icons", "Segoe MDL2 Assets"]) == "Segoe Fluent Icons"

def test_pyqt_menus_have_no_empty_menu_and_match_spec():
    names = [m["label"] for m in menus_for(load_menu_spec(), "pyqt")]
    assert names == ["파일", "편집", "보기", "도움말"]
```

(`pick_glyph_family(families: list[str]) -> str`를 `custom_titlebar.py`에 둬서 폰트 DB 없이 테스트.)

- [ ] **Step 2: 실패 확인** — `python apps/prediction/src/gui/test_titlebar_glyphs.py`
- [ ] **Step 3: 구현(QSS 토큰화 → 타이틀바 → 메뉴 → 다크 동기화)** → 테스트 통과, `python apps/prediction/src/gui/test_theme_tokens.py`·`test_theme_sync.py` 재통과
- [ ] **Step 4: 검사·캡처** — `python tools/check_ui_theme.py`, `python tools/check_ui_menus.py` 전체 통과. 오프스크린 `MainWindow().grab()`으로 라이트/다크 캡처, 타이틀바 30px 잘라 셸·시뮬 캡처와 위아래로 붙인 비교 이미지 생성.
- [ ] **Step 5: 사용자 확인 후 커밋** — `git commit -m "feat(pyqt): 공통 테마 값·메뉴·창 버튼 아이콘, 다크모드 동기화"`

---

### Task 7: 패키징과 설치본 검증

**Files:**
- Modify: `apps/shell/package.json`(`extraResources`에 `{ "from": "../shared", "to": "shared", "filter": ["**/*", "!*.test.mjs", "!*-demo.html"] }`)
- Modify: `apps/prediction/scripts/maps.spec`(`datas`에 `(os.path.join(APP, "..", "shared"), "shared")`)

**Interfaces:**
- Consumes: 모든 이전 Task.

- [ ] **Step 1: 빌드** — `python apps/prediction/scripts/build_win.py` → `Done!`
- [ ] **Step 2: 설치본 확인** — `win-unpacked/resources/shared/maps-theme.css`와 `resources/main_app/_internal/shared/menus.json` 존재. `win-unpacked/MAPS.exe` 실행(설치된 MAPS가 꺼져 있는지 먼저 확인): 세 창 타이틀바 캡처, 셸에서 다크모드 전환 → PyQt·시뮬이 1초 안에 따라오는지(PyQt는 `psutil`로 창이 살아 있는지 + 캡처), 재시작 후 유지, 메뉴 이동 3종을 세 앱에서 각각.
- [ ] **Step 3: 오프라인 폰트** — 네트워크 없이도 시뮬 글꼴이 맑은 고딕인지 CDP로 `getComputedStyle(document.body).fontFamily` 확인.
- [ ] **Step 4: 최종 비교 이미지와 결과를 사용자에게 보고 → 승인 후 커밋·PR** — `git commit -m "build: 공통 UI 폴더를 설치본에 포함"`, master 대상 PR(본문에 비교 이미지·검사 결과·2차 다크모드 목록 링크).

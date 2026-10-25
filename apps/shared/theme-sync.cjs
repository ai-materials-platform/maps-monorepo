"use strict";
// 다크모드 동기화 — 셸·시뮬(Electron)과 PyQt(theme_sync.py)가 같은 파일 하나를 본다.
// 파일: %APPDATA%\MAPS\theme.json, 내용 {"theme": "light" | "dark"}
// 개발 모드와 설치본, 세 앱 모두 같은 경로를 쓰도록 Electron userData가 아니라 고정 경로를 쓴다.
const fs = require("node:fs");
const path = require("node:path");

const THEMES = new Set(["light", "dark"]);

function themeFile() {
  if (process.env.MAPS_THEME_FILE) return process.env.MAPS_THEME_FILE;
  const base = process.env.APPDATA || path.join(require("node:os").homedir(), ".config");
  return path.join(base, "MAPS", "theme.json");
}

// Windows는 다른 프로세스가 파일을 잡고 있으면 잠깐 EPERM·EBUSY를 낸다 → 몇 번 다시 시도
const LOCKED = new Set(["EPERM", "EBUSY", "EACCES"]);
const pause = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
function retry(fn) {
  for (let i = 0; ; i += 1) {
    try {
      return fn();
    } catch (e) {
      if (i >= 20 || !LOCKED.has(e.code)) throw e;
      pause(10);
    }
  }
}

// 비우고 다시 쓰면(writeFileSync) 그 사이 읽는 쪽이 빈 파일을 본다 → 공백으로 길이를 고정해 제자리에 덮어쓴다.
// (JSON 뒤 공백은 유효하다. 임시 파일+이름 바꾸기는 Windows에서 읽는 쪽이 막아 실패한다.)
const SIZE = 32;
function writeTheme(theme, file = themeFile()) {
  if (!THEMES.has(theme)) return;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const data = Buffer.from(JSON.stringify({ theme }).padEnd(SIZE), "utf8");
  retry(() => {
    const fd = fs.openSync(file, fs.existsSync(file) ? "r+" : "w");
    try {
      fs.writeSync(fd, data, 0, data.length, 0);
      fs.ftruncateSync(fd, data.length); // 예전 형식처럼 더 긴 파일이었을 때만 꼬리를 자른다
    } finally {
      fs.closeSync(fd);
    }
  });
}

// 없거나 값이 이상하면 라이트로 시작한다. 깨진 파일은 올바른 내용으로 다시 쓴다.
// 그래도 쓰는 순간과 겹칠 수 있어, 깨졌다고 보기 전에 몇 번 다시 읽는다(안 그러면 남이 'dark'를 쓰는 중에 라이트로 덮어쓴다).
function readTheme(file = themeFile()) {
  for (let attempt = 0; attempt < 5; attempt += 1) {
    let raw;
    try {
      raw = retry(() => fs.readFileSync(file, "utf8"));
    } catch (_) {
      return "light";
    }
    try {
      const theme = JSON.parse(raw).theme;
      return THEMES.has(theme) ? theme : resetToLight(file);
    } catch (_) {
      pause(20);
    }
  }
  return resetToLight(file);
}

function resetToLight(file) {
  try { writeTheme("light", file); } catch (_) {}
  return "light";
}

// 부모 폴더를 감시한다(파일을 새로 쓰면 파일 감시가 끊기는 에디터·OS가 있어서).
// fs.watch는 한 번 쓰기에도 이벤트를 여러 번 보내므로 디바운스하고, 값이 바뀔 때만 알린다.
function watchTheme(cb, file = themeFile()) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  let last = readTheme(file);
  let timer = null;
  const watcher = fs.watch(path.dirname(file), (_event, name) => {
    if (name && name !== path.basename(file)) return;
    clearTimeout(timer);
    timer = setTimeout(() => {
      const now = readTheme(file);
      if (now !== last) {
        last = now;
        cb(now);
      }
    }, 100);
  });
  return () => {
    clearTimeout(timer);
    watcher.close();
  };
}

module.exports = { themeFile, readTheme, writeTheme, watchTheme };

"""다크모드 동기화 — 셸·시뮬(apps/shared/theme-sync.cjs)과 같은 theme.json 하나를 본다.

파일: %APPDATA%\\MAPS\\theme.json, 내용 {"theme": "light" | "dark"}
"""
import json
import os
import time
from pathlib import Path

from PyQt6.QtCore import QFileSystemWatcher, QObject, QTimer, pyqtSignal

_THEMES = {"light", "dark"}


def theme_file() -> Path:
    if os.environ.get("MAPS_THEME_FILE"):
        return Path(os.environ["MAPS_THEME_FILE"])
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    return Path(base) / "MAPS" / "theme.json"


def _retry(fn):
    # Windows는 다른 프로세스가 파일을 잡고 있으면 잠깐 PermissionError를 낸다 → 몇 번 다시 시도
    for attempt in range(21):
        try:
            return fn()
        except PermissionError:
            if attempt == 20:
                raise
            time.sleep(0.01)


def write_theme(theme: str, path: Path | None = None) -> None:
    if theme not in _THEMES:
        return
    p = Path(path or theme_file())
    p.parent.mkdir(parents=True, exist_ok=True)
    _retry(lambda: p.write_text(json.dumps({"theme": theme}), encoding="utf-8"))


def read_theme(path: Path | None = None) -> str:
    """없거나 값이 이상하면 'light'. 깨진 파일은 올바른 내용으로 다시 쓴다.

    다른 앱이 쓰는 도중이면 반쪽 파일이 읽힐 수 있어, 깨졌다고 보기 전에 몇 번 다시 읽는다
    (apps/shared/theme-sync.cjs와 같은 규칙).
    """
    p = Path(path or theme_file())
    for _ in range(5):
        try:
            raw = _retry(lambda: p.read_text(encoding="utf-8"))
        except OSError:
            return "light"
        try:
            theme = json.loads(raw).get("theme")
        except (ValueError, AttributeError):
            time.sleep(0.02)
            continue
        return theme if theme in _THEMES else _reset_to_light(p)
    return _reset_to_light(p)


def _reset_to_light(p: Path) -> str:
    try:
        write_theme("light", p)
    except OSError:
        pass
    return "light"


class ThemeWatcher(QObject):
    """theme.json이 바뀌면 changed(theme)를 보낸다. 같은 값으로 다시 쓰면 보내지 않는다."""

    changed = pyqtSignal(str)

    def __init__(self, path: Path | None = None, parent=None):
        super().__init__(parent)
        self._path = Path(path or theme_file())
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._last = read_theme(self._path)
        self._debounce = QTimer(self, singleShot=True, interval=100, timeout=self._check)
        # 파일을 새로 쓰면 파일 감시가 끊길 수 있어 부모 폴더도 같이 본다
        self._fs = QFileSystemWatcher([str(self._path.parent)], self)
        self._fs.directoryChanged.connect(lambda _p: self._debounce.start())
        self._fs.fileChanged.connect(lambda _p: self._debounce.start())
        self._rewatch()

    def _rewatch(self):
        if self._path.exists() and str(self._path) not in self._fs.files():
            self._fs.addPath(str(self._path))

    def _check(self):
        self._rewatch()
        now = read_theme(self._path)
        if now != self._last:
            self._last = now
            self.changed.emit(now)

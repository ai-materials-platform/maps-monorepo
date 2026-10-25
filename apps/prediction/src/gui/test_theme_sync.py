"""theme.json 다크모드 동기화(PyQt 쪽) 확인.

실행: python apps/prediction/src/gui/test_theme_sync.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from PyQt6.QtCore import QCoreApplication, QTimer  # noqa: E402

from src.gui.theme_sync import ThemeWatcher, read_theme, write_theme  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="maps-theme-"))


def test_missing_broken_and_invalid_files_read_as_light():
    assert read_theme(TMP / "none" / "theme.json") == "light"
    broken = TMP / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert read_theme(broken) == "light"
    assert json.loads(broken.read_text(encoding="utf-8")) == {"theme": "light"}
    broken.write_text('{"theme": "purple"}', encoding="utf-8")
    assert read_theme(broken) == "light"


def test_watcher_emits_once_per_real_change():
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    f = TMP / "watch" / "theme.json"
    write_theme("light", f)
    seen: list[str] = []
    w = ThemeWatcher(f)
    w.changed.connect(seen.append)
    steps = [
        (100, lambda: (write_theme("dark", f), write_theme("dark", f))),
        (600, lambda: write_theme("light", f)),
        (1200, app.quit),
    ]
    for delay, fn in steps:
        QTimer.singleShot(delay, fn)
    app.exec()
    assert seen == ["dark", "light"], seen


if __name__ == "__main__":
    test_missing_broken_and_invalid_files_read_as_light()
    test_watcher_emits_once_per_real_change()
    print("ok - theme sync")

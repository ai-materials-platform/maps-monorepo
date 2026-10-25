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


def test_write_ignores_values_other_than_light_dark():
    f = TMP / "invalid.json"
    write_theme("dark", f)
    write_theme("purple", f)
    write_theme(None, f)
    assert read_theme(f) == "dark"


def test_reading_while_another_process_writes_never_resets_to_light():
    # 다른 앱(별도 프로세스)이 'dark'만 계속 쓰는 동안 읽는다 — 반쪽 파일을 깨짐으로 보고 라이트로 덮어쓰면 안 된다
    import subprocess
    import time

    f = TMP / "race.json"
    done = TMP / "race.done"
    write_theme("dark", f)
    writer = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "from src.gui.theme_sync import write_theme;"
        "[write_theme('dark', sys.argv[2]) for _ in range(1500)];"
        "open(sys.argv[3], 'w').write('1')"
    )
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    proc = subprocess.Popen([sys.executable, "-c", writer, root, str(f), str(done)], stderr=subprocess.PIPE)
    seen = {"light": 0, "dark": 0}
    while not done.exists() and proc.poll() is None:
        seen[read_theme(f)] += 1
        time.sleep(0.001)
    _, err = proc.communicate()
    assert not err, err.decode(errors="replace")
    assert seen["dark"] > 10, seen
    assert seen["light"] == 0, seen


if __name__ == "__main__":
    test_write_ignores_values_other_than_light_dark()
    test_reading_while_another_process_writes_never_resets_to_light()
    test_missing_broken_and_invalid_files_read_as_light()
    test_watcher_emits_once_per_real_change()
    print("ok - theme sync")

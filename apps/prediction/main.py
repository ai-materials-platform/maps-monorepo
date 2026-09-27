import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=".*InconsistentVersionWarning.*")
try:
    from sklearn.exceptions import InconsistentVersionWarning
    warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
except ImportError:
    pass
from src.gui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication


def _load_env():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and value and key not in os.environ:
                os.environ[key] = value


def _apply_rounded_corners(window):
    """Windows 11 DWM API로 네이티브 둥근 모서리 적용."""
    if sys.platform != "win32":
        return
    import ctypes
    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWCP_ROUND = 2  # 둥근 모서리
    try:
        hwnd = int(window.winId())
        pref = ctypes.c_int(DWMWCP_ROUND)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(pref),
            ctypes.sizeof(pref),
        )
    except Exception:
        pass


def main():
    _load_env()
    from src.gui.constants import LIGHT_QSS

    app = QApplication(sys.argv)
    app.setStyleSheet(LIGHT_QSS)

    window = MainWindow()
    _apply_rounded_corners(window)
    window._apply_theme_colors()
    window.show()

    ws_name = os.environ.get("AI_MAPS_WORKSPACE", "").strip()
    if ws_name:
        window._active_workspace_name = ws_name

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

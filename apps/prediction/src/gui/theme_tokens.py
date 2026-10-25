"""공통 디자인 값(apps/shared/maps-theme.css)을 PyQt에서 읽는다.

셸·시뮬은 같은 파일을 CSS로 바로 쓴다. 값을 바꾸려면 maps-theme.css만 고친다.
"""
import logging
import re
import sys
from functools import lru_cache
from pathlib import Path

_VAR = re.compile(r"--([\w-]+)\s*:\s*([^;]+);")
_BLOCK = re.compile(r"(:root(?:\[data-theme=\"dark\"\])?)\s*\{(.*?)\}", re.S)
_MISSING = "#FF00FF"  # 눈에 띄는 색: 없는 이름을 쓰면 화면에서 바로 보이게


def shared_dir() -> Path:
    """개발: apps/shared, PyInstaller 번들: sys._MEIPASS/shared."""
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle) / "shared"
    return Path(__file__).resolve().parents[3] / "shared"


@lru_cache(maxsize=None)
def load_tokens(path: Path | None = None) -> dict[str, dict[str, str]]:
    text = Path(path or shared_dir() / "maps-theme.css").read_text(encoding="utf-8")
    light: dict[str, str] = {}
    dark: dict[str, str] = {}
    for selector, body in _BLOCK.findall(text):
        target = dark if "dark" in selector else light
        target.update({k: v.strip() for k, v in _VAR.findall(body)})
    return {"light": light, "dark": {**light, **dark}}


def token(name: str, dark: bool) -> str:
    value = load_tokens()["dark" if dark else "light"].get(name)
    if value is None:
        logging.warning("maps-theme.css에 없는 디자인 값: %s", name)
        return _MISSING
    return value


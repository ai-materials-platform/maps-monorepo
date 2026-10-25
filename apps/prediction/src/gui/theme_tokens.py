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



def load_menu_spec(path: Path | None = None) -> dict:
    """세 앱 공통 메뉴 정의(apps/shared/menus.json)."""
    import json

    return json.loads(Path(path or shared_dir() / "menus.json").read_text(encoding="utf-8"))


def menus_for(spec: dict, app: str = "pyqt", handled=lambda _id: True) -> list[dict]:
    """apps/shared/menu-model.js의 menusFor와 같은 규칙: 다른 앱·devOnly 제거, 구분선 정리, 빈 메뉴 제거."""
    result = []
    for menu in spec["menus"]:
        items: list[dict] = []
        for item in menu["items"]:
            if item.get("separator"):
                if items and not items[-1].get("separator"):
                    items.append({"separator": True})
                continue
            if app not in item["apps"] or item.get("devOnly"):
                continue
            items.append({**item, "enabled": bool(handled(item["id"]))})
        while items and items[-1].get("separator"):
            items.pop()
        if items:
            result.append({"id": menu["id"], "label": menu["label"], "items": items})
    return result

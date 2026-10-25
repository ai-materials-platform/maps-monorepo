"""메뉴 검사: apps/shared/menus.json의 기능 ID마다, 그 항목을 보여주는 앱이 처리 함수를 갖고 있는지 확인한다.

처리 함수 위치:
- 역할 ID(복사·닫기 등 Electron main이 처리): apps/shared/window-chrome.cjs 의 ROLE_IDS 배열
- 앱별: MENU_HANDLERS = { ... } 블록의 키 (셸 renderer/app.js, 시뮬 src/App.jsx, PyQt mixins/ui_setup_mixin.py)
PyQt는 역할 ID를 직접 처리하므로 ROLE_IDS를 인정하지 않는다.

실행: python tools/check_ui_menus.py   (빠진 것이 있으면 목록을 출력하고 종료 코드 1)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "apps" / "shared" / "menus.json"
CHROME = ROOT / "apps" / "shared" / "window-chrome.cjs"
HANDLERS = {
    "shell": ROOT / "apps" / "shell" / "renderer" / "app.js",
    "sim": ROOT / "apps" / "simulation" / "src" / "App.jsx",
    "pyqt": ROOT / "apps" / "prediction" / "src" / "gui" / "mixins" / "ui_setup_mixin.py",
}
KEY = re.compile(r"""["']([\w.]+)["']\s*:""")


def block_keys(path: Path, name: str) -> set[str]:
    if not path.exists():
        return set()
    m = re.search(name + r"\s*=\s*[\{\[](.*?)[\}\]]", path.read_text(encoding="utf-8"), re.S)
    if not m:
        return set()
    if name == "ROLE_IDS":
        return set(re.findall(r"""["']([\w.]+)["']""", m.group(1)))
    return set(KEY.findall(m.group(1)))


def main() -> int:
    roles = block_keys(CHROME, "ROLE_IDS")
    handled = {app: block_keys(path, "MENU_HANDLERS") for app, path in HANDLERS.items()}
    problems = []
    for menu in json.loads(SPEC.read_text(encoding="utf-8"))["menus"]:
        for item in menu["items"]:
            if item.get("separator"):
                continue
            for app in item["apps"]:
                ok = item["id"] in handled[app] or (app != "pyqt" and item["id"] in roles)
                if not ok:
                    problems.append(f"{app}: {item['id']} ({item['label']}) 처리 함수 없음")
    if problems:
        print("\n".join(problems))
        return 1
    print("ok - menus")
    return 0


if __name__ == "__main__":
    sys.exit(main())

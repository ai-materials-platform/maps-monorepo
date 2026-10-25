"""공통 디자인 값 검사: 세 앱이 쓰는 --maps-* 이름이 apps/shared/maps-theme.css에 모두 있는지,
다크가 라이트에 없는 이름을 만들지 않았는지 확인한다.

실행: python tools/check_ui_theme.py   (문제가 있으면 목록을 출력하고 종료 코드 1)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "apps" / "shared" / "maps-theme.css"
SCAN = [ROOT / "apps" / "shell", ROOT / "apps" / "simulation" / "src", ROOT / "apps" / "simulation" / "electron",
        ROOT / "apps" / "prediction" / "src", ROOT / "apps" / "shared"]
SKIP = {"node_modules", "dist", "dist_electron", "dist_python", "__pycache__"}
EXTS = {".css", ".js", ".jsx", ".cjs", ".mjs", ".html", ".py"}
USE = re.compile(r"""--(maps-[\w-]+)|token\(\s*["'](maps-[\w-]+)["']""")


def defined() -> tuple[set[str], set[str]]:
    text = re.sub(r"/\*.*?\*/", "", THEME.read_text(encoding="utf-8"), flags=re.S)  # 주석 속 예시 제외
    light, _, dark = text.partition(':root[data-theme="dark"]')
    names = lambda s: set(re.findall(r"--(maps-[\w-]+)\s*:", s))
    return names(light), names(dark)


def used() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for base in SCAN:
        for f in base.rglob("*"):
            if f.suffix not in EXTS or SKIP & set(f.parts) or f == THEME or f.name.startswith("test_") or ".test." in f.name:
                continue
            for m in USE.finditer(f.read_text(encoding="utf-8", errors="ignore")):
                found.setdefault(m.group(1) or m.group(2), set()).add(str(f.relative_to(ROOT)))
    return found


def main() -> int:
    light, dark = defined()
    problems = [f"다크에만 있는 이름: --{n}" for n in sorted(dark - light)]
    for name, files in sorted(used().items()):
        if name not in light:
            problems.append(f"정의되지 않은 이름 --{name}: {', '.join(sorted(files))}")
    if problems:
        print("\n".join(problems))
        return 1
    print(f"ok - theme ({len(light)} names)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""PyQt 타이틀바 창 버튼 글꼴 고르기와 공통 메뉴(menus.json) 거르기를 확인한다.

실행: python apps/prediction/src/gui/test_titlebar_glyphs.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.gui.theme_tokens import load_menu_spec, menus_for  # noqa: E402
from src.gui.widgets.custom_titlebar import pick_glyph_family  # noqa: E402


def test_glyph_font_falls_back_when_fluent_missing():
    fams = ["Segoe MDL2 Assets", "Malgun Gothic"]
    assert pick_glyph_family(fams) == "Segoe MDL2 Assets"
    assert pick_glyph_family(["Segoe Fluent Icons", "Segoe MDL2 Assets"]) == "Segoe Fluent Icons"


def test_pyqt_menus_have_no_empty_menu_and_match_spec():
    names = [m["label"] for m in menus_for(load_menu_spec(), "pyqt")]
    assert names == ["파일", "편집", "보기", "도움말"]


def test_menus_for_matches_js_rules():
    # 셸 메뉴엔 시뮬 전용 항목·devOnly가 없고, 처리 못 하는 항목은 비활성 (apps/shared/menu-model.js와 같은 규칙)
    spec = load_menu_spec()
    flat = [i for m in menus_for(spec, "shell") for i in m["items"]]
    ids = [i.get("id") for i in flat]
    assert "file.report" not in ids and "view.devtools" not in ids
    pyqt = menus_for(spec, "pyqt", handled=lambda i: i != "view.nav.dashboard")
    view = next(m for m in pyqt if m["id"] == "view")["items"]
    assert next(i for i in view if i.get("id") == "view.nav.dashboard")["enabled"] is False
    for m in pyqt:
        seps = [bool(i.get("separator")) for i in m["items"]]
        assert not seps[0] and not seps[-1] and not any(a and b for a, b in zip(seps, seps[1:])), m["id"]


if __name__ == "__main__":
    test_glyph_font_falls_back_when_fluent_missing()
    test_pyqt_menus_have_no_empty_menu_and_match_spec()
    test_menus_for_matches_js_rules()
    print("ok - titlebar glyphs & menus")

"""공통 디자인 값(apps/shared/maps-theme.css)을 PyQt가 읽는지 확인한다.

실행: python apps/prediction/src/gui/test_theme_tokens.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.gui.theme_tokens import load_tokens, token  # noqa: E402


def test_light_and_dark_values_from_spec():
    t = load_tokens()
    assert t["light"]["maps-bg"] == "#F4F6F8"
    assert t["dark"]["maps-bg"] == "#1E1E1E"
    assert t["light"]["maps-titlebar-height"] == "30px"
    # 다크에 따로 적지 않은 값은 라이트 값으로 채운다
    assert t["dark"]["maps-font-sans"] == '"Malgun Gothic"'


def test_unknown_token_does_not_crash():
    assert token("maps-does-not-exist", dark=False) == "#FF00FF"


def test_simple_values_only():
    # Qt는 CSS 계산식·그라데이션을 이해하지 못한다
    for theme in load_tokens().values():
        for v in theme.values():
            assert not any(bad in v for bad in ("calc(", "var(", "gradient")), v


if __name__ == "__main__":
    test_light_and_dark_values_from_spec()
    test_unknown_token_does_not_crash()
    test_simple_values_only()
    print("ok - theme tokens")

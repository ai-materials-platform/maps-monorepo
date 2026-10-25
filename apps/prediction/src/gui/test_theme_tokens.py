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



def _contrast(a: str, b: str) -> float:
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted([lum(a), lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_blue_text_and_blue_buttons_are_readable_in_both_themes():
    # 파랑 하나로는 '어두운 바탕 위 파란 글자'와 '파란 버튼 위 흰 글자'를 둘 다 4.5:1로 못 맞춘다
    # → 글자용(maps-primary-text)과 버튼 바탕용(maps-primary)을 나눈다 (GitHub Primer·VS Code와 같은 방식)
    for name, theme in load_tokens().items():
        for surface in ("maps-bg", "maps-panel", "maps-panel-muted"):
            assert _contrast(theme["maps-primary-text"], theme[surface]) >= 4.5, (name, surface)
        assert _contrast("#FFFFFF", theme["maps-primary"]) >= 4.5, name


if __name__ == "__main__":
    test_blue_text_and_blue_buttons_are_readable_in_both_themes()
    test_light_and_dark_values_from_spec()
    test_unknown_token_does_not_crash()
    test_simple_values_only()
    print("ok - theme tokens")

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QToolButton, QWidget

from src.gui.theme_tokens import token
from src.gui.widgets.maps_logo import MAPSLogoWidget

# Windows 11 창 버튼 글꼴, 없으면(Windows 10) MDL2 — 셸·시뮬은 Electron titleBarOverlay가 같은 모양을 그린다
_GLYPH_FAMILIES = ("Segoe Fluent Icons", "Segoe MDL2 Assets")
GLYPH_MIN, GLYPH_MAX, GLYPH_RESTORE, GLYPH_CLOSE = "\uE921", "\uE922", "\uE923", "\uE8BB"


def pick_glyph_family(families: list[str]) -> str:
    return next((f for f in _GLYPH_FAMILIES if f in families), _GLYPH_FAMILIES[-1])


def window_glyph_font() -> QFont:
    font = QFont(pick_glyph_family(QFontDatabase.families()))
    font.setPixelSize(10)
    return font


class CustomTitleBar(QWidget):
    """OS 타이틀바 영역을 대체하는 커스텀 타이틀바.
    메뉴 버튼 / 앱 제목 / 창 컨트롤 버튼을 포함한다."""

    HEIGHT = 30

    def __init__(self, main_win, menus: list, title: str = "MAPS 물성 예측"):
        """
        menus: [("파일", QMenu), ("편집", QMenu), ...]
        """
        super().__init__(main_win)
        self._win = main_win
        self._drag_pos = None
        self.setFixedHeight(self.HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(0)

        # ── MAPS 로고 아이콘 ──────────────────────────────────────────────────
        logo = MAPSLogoWidget(size=24)
        layout.addWidget(logo)
        layout.addSpacing(4)

        # ── 메뉴 버튼 ─────────────────────────────────────────────────────────
        self._menu_buttons = []
        for name, menu in menus:
            btn = QToolButton()
            btn.setText(name)
            btn.setMenu(menu)
            btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(btn)
            self._menu_buttons.append(btn)

        # 셸("MAPS")·시뮬("MAPS 시뮬레이션")처럼 메뉴와 창 버튼 사이 가운데에 창 이름
        self._title = QLabel(title)
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # 끌어서 창 이동
        layout.addWidget(self._title, 1)

        # ── 창 컨트롤 버튼 (최소화 / 최대화·이전 크기 / 닫기) ──────────────────
        glyph_font = window_glyph_font()
        self._glyph_family = glyph_font.family()
        self._win_buttons = []
        for glyph, callback in [
            (GLYPH_MIN, main_win.showMinimized),
            (GLYPH_MAX, self._toggle_max),
            (GLYPH_CLOSE, main_win.close),
        ]:
            b = QPushButton(glyph)
            b.setFixedSize(46, self.HEIGHT)
            b.clicked.connect(callback)
            layout.addWidget(b)
            self._win_buttons.append(b)
        self._max_btn = self._win_buttons[1]
        main_win.installEventFilter(self)
        self.refresh_theme()

    def refresh_theme(self):
        """다크모드 전환 시 테마 적용 코드가 부른다 — 색은 전부 maps-theme.css."""
        dark = getattr(self._win, "_dark_mode", False)
        t = lambda name: token(name, dark)  # noqa: E731
        menu_style = (
            f"QToolButton{{background:transparent;color:{t('maps-menu-text')};border:none;"
            f"font-size:{t('maps-font-size')};font-weight:600;padding:4px 10px;border-radius:4px;}}"
            f"QToolButton:hover{{background:{t('maps-menu-hover')};color:{t('maps-text')};}}"
            "QToolButton::menu-indicator{image:none;width:0px;}"
        )
        for btn in self._menu_buttons:
            btn.setStyleSheet(menu_style)
            # InstantPopup은 스타일과 무관하게 화살표 폭(~11px)을 더 잡는다 → 글자 폭 + 좌우 여백 10px로 고정
            btn.ensurePolished()
            btn.setFixedWidth(btn.fontMetrics().horizontalAdvance(btn.text()) + 20)
        self._title.setStyleSheet(
            f"background:transparent;color:{t('maps-text-muted')};font-size:{t('maps-font-size')};")
        for b in self._win_buttons:
            close = b.text() == GLYPH_CLOSE
            b.setStyleSheet(
                # 전역 QSS의 font-family가 setFont를 덮으므로 글꼴도 여기서 지정
                f"QPushButton{{background:transparent;color:{t('maps-text')};border:none;border-radius:0;padding:0;"
                f"font-family:'{self._glyph_family}';font-size:10px;}}"
                f"QPushButton:hover{{background:{t('maps-danger') if close else t('maps-menu-hover')};"
                f"color:{'#FFFFFF' if close else t('maps-text')};}}"
            )
        self.update()

    def eventFilter(self, obj, event):
        # 최대화는 더블클릭·Win+↑·드래그 등 여러 길로 바뀌므로 창 상태 변화를 보고 아이콘을 맞춘다
        if obj is self._win and event.type() == QEvent.Type.WindowStateChange:
            self._max_btn.setText(GLYPH_RESTORE if self._win.isMaximized() else GLYPH_MAX)
        return False

    # ── 배경 그리기 ───────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        dark = getattr(self._win, "_dark_mode", False)
        bg = QColor(token("maps-titlebar-bg", dark))
        border = QColor(token("maps-titlebar-border", dark))
        p.fillRect(self.rect(), bg)
        # 하단 구분선
        p.fillRect(0, self.height() - 1, self.width(), 1, border)

    # ── 창 드래그 이동 ────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self._win.frameGeometry().topLeft()
            )
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            if self._win.isMaximized():
                self._win.showNormal()
            self._win.move(event.globalPosition().toPoint() - self._drag_pos)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self._toggle_max()
        event.accept()

    # ── 최대화 토글 ───────────────────────────────────────────────────────────

    def _toggle_max(self):
        if self._win.isMaximized():
            self._win.showNormal()
        else:
            self._win.showMaximized()

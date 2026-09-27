from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QToolButton, QWidget

from src.gui.widgets.maps_logo import MAPSLogoWidget


class CustomTitleBar(QWidget):
    """OS 타이틀바 영역을 대체하는 커스텀 타이틀바.
    메뉴 버튼 / 앱 제목 / 창 컨트롤 버튼을 포함한다."""

    HEIGHT = 30

    def __init__(self, main_win, menus: list):
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
        _style = (
            "QToolButton{background:transparent;color:#374151;border:none;"
            "font-size:11px;font-weight:600;padding:4px 10px;border-radius:4px;}"
            "QToolButton:hover{background:#F1F5F9;color:#111827;}"
            "QToolButton::menu-indicator{image:none;}"
        )
        for name, menu in menus:
            btn = QToolButton()
            btn.setText(name)
            btn.setMenu(menu)
            btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            btn.setStyleSheet(_style)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(btn)

        layout.addStretch()

        # ── 창 컨트롤 버튼 (─ □ ✕) ──────────────────────────────────────────
        for symbol, callback, hover_bg, hover_text in [
            ("─", main_win.showMinimized, "#E5E7EB", "#111827"),
            ("□", self._toggle_max,       "#E5E7EB", "#111827"),
            ("✕", main_win.close,         "#C42B1C", "#FFFFFF"),
        ]:
            b = QPushButton(symbol)
            b.setFixedSize(46, self.HEIGHT)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                f"QPushButton{{background:transparent;color:#6B7280;border:none;font-size:12px;}}"
                f"QPushButton:hover{{background:{hover_bg};color:{hover_text};}}"
            )
            b.clicked.connect(callback)
            layout.addWidget(b)

    # ── 배경 그리기 ───────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        dark = getattr(self._win, "_dark_mode", False)
        bg     = QColor("#1E1E1E") if dark else QColor("#FFFFFF")
        border = QColor("#3B4350") if dark else QColor("#C9D2DC")
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

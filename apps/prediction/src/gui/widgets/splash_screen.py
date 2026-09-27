from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .maps_logo import MAPSLogoWidget


class MAPSSplashScreen(QWidget):
    """앱 시작 시 표시되는 스플래시 스크린 (Excel/한글 스타일)."""

    _W, _H = 400, 360

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self._W + 24, self._H + 24)  # 여백: 그림자 공간
        self._center_on_screen()
        self._build_ui()

    # ── 위치 ──────────────────────────────────────────────────────
    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.x() + (screen.width() - self.width()) // 2
        y = screen.y() + (screen.height() - self.height()) // 2
        self.move(x, y)

    # ── UI 구성 ───────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)  # 그림자 여백
        outer.setSpacing(0)

        # 흰 카드 (그림자 대상)
        card = QWidget()
        card.setObjectName("splashCard")
        card.setStyleSheet(
            "#splashCard { background: #FFFFFF; border-radius: 10px; }"
        )
        card.setFixedSize(self._W, self._H)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 70))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        # ── 상단 콘텐츠 영역 ─────────────────────────────────────
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(40, 44, 40, 28)
        bl.setSpacing(0)

        # 로고
        logo_row = QWidget()
        logo_row.setStyleSheet("background: transparent;")
        logo_rl = QHBoxLayout(logo_row)
        logo_rl.setContentsMargins(0, 0, 0, 0)
        logo_rl.addStretch()
        logo = MAPSLogoWidget(size=100)
        logo.setStyleSheet("background: transparent;")
        logo_rl.addWidget(logo)
        logo_rl.addStretch()
        bl.addWidget(logo_row)
        bl.addSpacing(20)

        # 앱 이름
        name_lbl = QLabel("MAPS")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet(
            "font-size: 32px; font-weight: 800; color: #0F172A; "
            "letter-spacing: 3px; background: transparent;"
        )
        bl.addWidget(name_lbl)
        bl.addSpacing(6)

        # 풀네임 부제
        sub_lbl = QLabel("Microstructure & Alloy Prediction System")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setStyleSheet(
            "font-size: 11px; color: #64748B; letter-spacing: 0.5px; background: transparent;"
        )
        bl.addWidget(sub_lbl)
        bl.addStretch()

        cl.addWidget(body, 1)

        # ── 하단 상태 바 ─────────────────────────────────────────
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("border: none; border-top: 1px solid #E2E8F0;")
        divider.setFixedHeight(1)
        cl.addWidget(divider)

        footer = QWidget()
        footer.setStyleSheet(
            "background: #F8FAFC; border-bottom-left-radius: 10px; "
            "border-bottom-right-radius: 10px;"
        )
        footer.setFixedHeight(46)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(20, 0, 20, 0)

        self._status_lbl = QLabel("초기화 중...")
        self._status_lbl.setStyleSheet(
            "font-size: 11px; color: #94A3B8; background: transparent;"
        )
        fl.addWidget(self._status_lbl)
        fl.addStretch()

        brand_lbl = QLabel("© 2026  MAPS")
        brand_lbl.setStyleSheet(
            "font-size: 10px; color: #CBD5E1; background: transparent;"
        )
        fl.addWidget(brand_lbl)
        cl.addWidget(footer)

    # ── 공개 API ─────────────────────────────────────────────────
    def set_message(self, msg: str):
        """하단 상태 텍스트를 업데이트하고 화면을 즉시 갱신한다."""
        self._status_lbl.setText(msg)
        QApplication.processEvents()

    def finish(self, main_window: QWidget):
        """메인 윈도우가 준비되면 스플래시를 닫는다."""
        main_window.show()
        QApplication.processEvents()
        self.close()
